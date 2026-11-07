"""HTTP-independent entry point for one review run."""

from __future__ import annotations

import hashlib
import uuid
import asyncio

from ..harness.execution import ExecutionContext, reset_execution, set_execution
from .graph import create_review_pipeline
from .state import ContractReviewState, ReviewStatus

MAX_TEXT_CHARS = 15_000
MAX_TXT_BYTES = 65_536


class ReviewInputError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def validate_text(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ReviewInputError("EMPTY_TEXT", "Contract text must not be empty")
    if len(text) > MAX_TEXT_CHARS:
        raise ReviewInputError("TEXT_TOO_LONG", f"Contract text exceeds {MAX_TEXT_CHARS} characters")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def decode_txt(data: bytes) -> str:
    if len(data) > MAX_TXT_BYTES:
        raise ReviewInputError("FILE_TOO_LARGE", f"TXT file exceeds {MAX_TXT_BYTES} bytes")
    try:
        return validate_text(data.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise ReviewInputError("INVALID_UTF8", "TXT file must use UTF-8 encoding") from exc


async def run_review(text: str, *, review_id: str | None = None,
                     max_calls: int = 8) -> ContractReviewState:
    if not 1 <= max_calls <= 8:
        raise ValueError("max_calls must be between 1 and 8")
    normalized = validate_text(text)
    review_id = review_id or str(uuid.uuid4())
    initial = ContractReviewState(review_id=review_id, raw_text=normalized,
                                  document_hash=document_hash(normalized),
                                  status=ReviewStatus.IN_PROGRESS)
    pipeline = create_review_pipeline()
    context = ExecutionContext(max_calls=max_calls)
    token = set_execution(context)
    try:
        result = await asyncio.wait_for(
            pipeline.ainvoke(initial.model_dump(),
                             config={"configurable": {"thread_id": review_id}}),
            timeout=context.total_seconds,
        )
        state = ContractReviewState(**result)
    except asyncio.TimeoutError:
        state = initial.model_copy(update={"status": ReviewStatus.TIMED_OUT,
                                           "failed_stage": "runtime",
                                           "errors": ["TOTAL_TIMEOUT"]})
    except Exception:
        state = initial.model_copy(update={"status": ReviewStatus.FAILED,
                                           "failed_stage": "runtime",
                                           "errors": ["RUNTIME_ERROR"]})
    finally:
        reset_execution(token)
    state.diagnostics.extend(context.attempts)
    if state.raw_text != normalized:
        state.status = ReviewStatus.FAILED
        state.failed_stage = "validation"
        state.errors.append("Source text changed during review")
    return state


def document_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
