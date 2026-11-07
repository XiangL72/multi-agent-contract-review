from unittest.mock import patch

import pytest

from src.config import get_llm, settings


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch):
    for name, value in {
        'LLM_PROVIDER': 'auto', 'LLM_MODEL': '',
        'MINIMAX_API_KEY': '', 'OPENAI_API_KEY': '',
        'OPENAI_API_BASE': 'https://api.openai.com/v1',
    }.items():
        monkeypatch.setattr(settings, name, value)


def test_explicit_compatible_provider_ignores_minimax(monkeypatch):
    monkeypatch.setattr(settings, 'LLM_PROVIDER', 'openai')
    monkeypatch.setattr(settings, 'MINIMAX_API_KEY', 'stale-key')
    monkeypatch.setattr(settings, 'OPENAI_API_KEY', 'test-key')
    monkeypatch.setattr(settings, 'OPENAI_API_BASE', 'https://api.deepseek.com')
    monkeypatch.setattr(settings, 'LLM_MODEL', 'deepseek-flash')
    with patch('langchain_openai.ChatOpenAI') as client:
        get_llm()
    assert client.call_args.kwargs['model'] == 'deepseek-flash'
    assert client.call_args.kwargs['base_url'] == 'https://api.deepseek.com'
    assert client.call_args.kwargs['api_key'] == 'test-key'


def test_placeholder_does_not_select_minimax(monkeypatch):
    monkeypatch.setattr(settings, 'MINIMAX_API_KEY', 'your_minimax_api_key_here')
    monkeypatch.setattr(settings, 'OPENAI_API_KEY', 'test-key')
    with patch('langchain_openai.ChatOpenAI') as client:
        get_llm()
    assert client.call_args.kwargs['model'] == 'gpt-4o-mini'


def test_custom_endpoint_requires_model(monkeypatch):
    monkeypatch.setattr(settings, 'OPENAI_API_KEY', 'test-key')
    monkeypatch.setattr(settings, 'OPENAI_API_BASE', 'https://api.deepseek.com')
    with pytest.raises(ValueError, match='LLM_MODEL'):
        get_llm()


def test_missing_key():
    with pytest.raises(ValueError, match='API_KEY'):
        get_llm()
