import pytest

from src.harness.execution import (
    BudgetedLLM, ExecutionContext, ModelCallError, classify_error, reset_execution, set_execution,
)


class RateLimitError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class FakeClient:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = 0
        self.timeouts = []

    def invoke(self, messages, **kwargs):
        self.calls += 1
        self.timeouts.append(kwargs.get("timeout"))
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        return result


def test_retry_is_bounded_and_counted(monkeypatch):
    monkeypatch.setattr("src.harness.execution.time.sleep", lambda _: None)
    context = ExecutionContext(max_calls=2)
    token = set_execution(context)
    try:
        client = FakeClient([RateLimitError("sensitive response"), "ok"])
        assert BudgetedLLM(client, "risk").invoke([]) == "ok"
    finally:
        reset_execution(token)
    assert client.calls == context.calls_used == 2
    assert all(0 < timeout <= 30 for timeout in client.timeouts)
    assert [row["status"] for row in context.attempts] == ["failed", "success"]
    assert "sensitive response" not in str(context.attempts)


def test_budget_stops_second_request(monkeypatch):
    monkeypatch.setattr("src.harness.execution.time.sleep", lambda _: None)
    context = ExecutionContext(max_calls=1)
    token = set_execution(context)
    try:
        client = FakeClient([RateLimitError("limited"), "unexpected"])
        with pytest.raises(ModelCallError, match="BUDGET_EXCEEDED"):
            BudgetedLLM(client, "compliance").invoke([])
    finally:
        reset_execution(token)
    assert client.calls == 1


def test_authentication_does_not_retry():
    context = ExecutionContext()
    token = set_execution(context)
    try:
        client = FakeClient([AuthenticationError("secret")])
        with pytest.raises(ModelCallError, match="AUTHENTICATION"):
            BudgetedLLM(client, "extraction").invoke([])
    finally:
        reset_execution(token)
    assert client.calls == context.calls_used == 1


def test_expired_deadline_prevents_request():
    context = ExecutionContext(total_seconds=1, started=0)
    token = set_execution(context)
    try:
        client = FakeClient(["unexpected"])
        with pytest.raises(ModelCallError, match="TOTAL_TIMEOUT"):
            BudgetedLLM(client, "suggestion").invoke([])
    finally:
        reset_execution(token)
    assert client.calls == 0


class APIStatusError(Exception):
    def __init__(self, status_code):
        self.status_code = status_code


def test_http_status_retry_policy():
    assert classify_error(APIStatusError(400)) == ("PROVIDER_REJECTED", False)
    assert classify_error(APIStatusError(401)) == ("AUTHENTICATION", False)
    assert classify_error(APIStatusError(429)) == ("RATE_LIMIT", True)
    assert classify_error(APIStatusError(503)) == ("PROVIDER_ERROR", True)


def test_remaining_deadline_caps_provider_timeout():
    context = ExecutionContext(total_seconds=2, per_call_seconds=30)
    token = set_execution(context)
    try:
        client = FakeClient(["ok"])
        BudgetedLLM(client, "risk").invoke([])
    finally:
        reset_execution(token)
    assert client.timeouts[0] <= 2
