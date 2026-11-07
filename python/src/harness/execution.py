"""Per-run request budget, bounded retry, and sanitized attempt diagnostics."""

from __future__ import annotations

import contextvars
import hashlib
import time
from dataclasses import dataclass, field


class ModelCallError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass
class ExecutionContext:
    max_calls: int = 8
    total_seconds: float = 120.0
    per_call_seconds: float = 30.0
    max_retries: int = 1
    started: float = field(default_factory=time.monotonic)
    calls_used: int = 0
    attempts: list[dict] = field(default_factory=list)

    def remaining(self) -> float:
        return self.total_seconds - (time.monotonic() - self.started)


_current: contextvars.ContextVar[ExecutionContext | None] = contextvars.ContextVar("review_execution", default=None)


def set_execution(context: ExecutionContext):
    return _current.set(context)


def reset_execution(token) -> None:
    _current.reset(token)


def current_execution() -> ExecutionContext | None:
    return _current.get()


def classify_error(exc: Exception) -> tuple[str, bool]:
    name = type(exc).__name__.lower()
    status_code = getattr(exc, "status_code", None)
    if status_code in (401, 403):
        return "AUTHENTICATION", False
    if status_code == 429:
        return "RATE_LIMIT", True
    if isinstance(status_code, int):
        return ("PROVIDER_ERROR", True) if status_code >= 500 else ("PROVIDER_REJECTED", False)
    if "authentication" in name or "permission" in name:
        return "AUTHENTICATION", False
    if "ratelimit" in name or "rate_limit" in name:
        return "RATE_LIMIT", True
    if "timeout" in name:
        return "MODEL_TIMEOUT", True
    if "connection" in name:
        return "NETWORK", True
    if "apierror" in name or "internalserver" in name:
        return "PROVIDER_ERROR", True
    return "MODEL_ERROR", False


class BudgetedLLM:
    def __init__(self, client, stage: str):
        self.client = client
        self.stage = stage

    def invoke(self, messages):
        context = current_execution()
        if context is None:
            # Direct agent unit tests can use fakes without a Runner; production goes through Runner.
            return self.client.invoke(messages)
        for attempt in range(context.max_retries + 1):
            if context.remaining() <= 0:
                raise ModelCallError("TOTAL_TIMEOUT")
            if context.calls_used >= context.max_calls:
                raise ModelCallError("BUDGET_EXCEEDED")
            timeout = min(context.per_call_seconds, context.remaining())
            if timeout <= 0:
                raise ModelCallError("TOTAL_TIMEOUT")
            context.calls_used += 1  # Count attempted provider requests, including failures.
            started = time.monotonic()
            prompt_text = str(messages[0].content) if messages else ""
            prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:12]
            try:
                response = self.client.invoke(messages, timeout=timeout)
                usage = getattr(response, "usage_metadata", None)
                metadata = getattr(response, "response_metadata", None)
                model = metadata.get("model_name") if isinstance(metadata, dict) else None
                model = model or getattr(self.client, "model_name", None)
                context.attempts.append({"stage": self.stage, "attempt": attempt + 1, "status": "success",
                                         "duration_seconds": round(time.monotonic() - started, 3),
                                         "calls_used": context.calls_used, "timeout_seconds": round(timeout, 3),
                                         "usage": usage if isinstance(usage, dict) else None,
                                         "model": model, "prompt_hash": prompt_hash})
                return response
            except Exception as exc:
                code, retryable = classify_error(exc)
                context.attempts.append({"stage": self.stage, "attempt": attempt + 1, "status": "failed",
                                         "error_code": code, "retryable": retryable,
                                         "duration_seconds": round(time.monotonic() - started, 3),
                                         "calls_used": context.calls_used, "timeout_seconds": round(timeout, 3),
                                         "model": getattr(self.client, "model_name", None),
                                         "prompt_hash": prompt_hash, "usage": None})
                if not retryable or attempt >= context.max_retries:
                    raise ModelCallError(code) from exc
                remaining = context.remaining()
                if remaining <= 0:
                    raise ModelCallError("TOTAL_TIMEOUT") from exc
                time.sleep(min(0.5 * 2**attempt, max(0, remaining)))
        raise AssertionError("unreachable")
