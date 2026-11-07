from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.api import main
from src.pipeline.graph import complete_node
from src.pipeline.state import ContractReviewState, ReviewStatus


def test_errors_cannot_be_completed():
    state = ContractReviewState(errors=['Provider authentication failed'])
    assert complete_node(state)['status'] == ReviewStatus.FAILED
    assert complete_node(ContractReviewState())['status'] == ReviewStatus.PARTIAL
    assert complete_node(ContractReviewState(knowledge_status='grounded'))['status'] == ReviewStatus.SUCCESS
    assert complete_node(ContractReviewState(errors=['MODEL_TIMEOUT']))['status'] == ReviewStatus.TIMED_OUT


@pytest.mark.parametrize('upload', [False, True])
def test_failed_review_returns_error(monkeypatch, tmp_path, upload):
    state = ContractReviewState(status=ReviewStatus.FAILED, errors=['Provider failed'])
    runner = AsyncMock(return_value=state)
    monkeypatch.setattr(main, 'run_review', runner)
    client = TestClient(main.app)
    if upload:
        response = client.post('/api/v1/review/upload', files={'file': ('contract.txt', b'test')})
    else:
        response = client.post('/api/v1/review', json={'text': 'test'})
    assert response.status_code == 502
    assert 'review_id' in response.json()
    assert response.json()['status'] == 'failed'
    assert response.headers['cache-control'] == 'no-store'
