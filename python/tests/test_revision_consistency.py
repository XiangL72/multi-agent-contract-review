"""Offline regressions from fictional trial output; no provider calls."""
import json
from types import SimpleNamespace
import pytest
from src.agents.risk_identification import RiskIdentificationAgent
from src.agents.suggestion import SuggestionAgent, PROPOSAL_NOTICE
from src.harness.errors import ReviewStageError
from src.pipeline.state import Clause, ContractReviewState, RiskFinding, RiskLevel


def fake(payload):
    return SimpleNamespace(invoke=lambda *a, **k: SimpleNamespace(content=json.dumps(payload)))


def clause(text):
    return Clause(id='c1', title='Terms', content=text, start=0, end=len(text))


def risk_agent():
    agent = RiskIdentificationAgent()
    agent.llm = fake({'findings': [{'clause_id': 'c1', 'risk_type': 'unlimited_liability',
                                  'risk_level': 'medium', 'description': 'Candidate concern'}]})
    return agent


@pytest.mark.parametrize('text', [
    'Breach liability is capped at the purchase price.',
    "The seller's liability is limited to CNY 1000.",
    'Liability shall not exceed the contract price.',
    'The seller does not assume unlimited liability.',
])
def test_capped_or_negated_liability_cannot_be_labelled_unlimited(text):
    with pytest.raises(ReviewStageError) as exc:
        risk_agent()._llm_analysis([clause(text)])
    assert exc.value.code == 'RISK_CATEGORY_CONTRADICTION'


def test_contradiction_marks_stage_failed_instead_of_false_success():
    c = clause('Breach liability is capped at the purchase price.')
    result = risk_agent()(ContractReviewState(raw_text=c.content, clauses=[c]))
    assert result['failed_stage'] == 'risk'
    assert not result['risk_findings']
    assert result['errors'][0].startswith('RISK_CATEGORY_CONTRADICTION:')


@pytest.mark.parametrize('text', [
    'The seller assumes unlimited liability for all losses.',
    'The seller is capped at the price; the buyer assumes unlimited liability.',
])
def test_positive_uncapped_obligation_is_not_hidden_by_another_cap(text):
    assert len(risk_agent()._llm_analysis([clause(text)])) == 1


def generate(original, proposed):
    agent = SuggestionAgent()
    agent.llm = fake({'suggestions': [{'clause_id': 'c1', 'suggested_text': proposed,
                                    'reason': 'Clarify the terms', 'priority': 'medium'}]})
    c = clause(original)
    finding = RiskFinding(clause_id=c.id, risk_type='vague_terms', risk_level=RiskLevel.MEDIUM,
                          description='Candidate ambiguity')
    return agent, c, finding


@pytest.mark.parametrize('original,proposed', [
    ('The buyer purchases one unit of Model E equipment.', 'The buyer purchases [quantity] units of Model E equipment.'),
    ('The price is CNY 1000.', 'The price is CNY [amount].'),
    ('Delivery within 15 days.', 'Delivery within 30 days.'),
    ('Delivery within 15 days.', 'Delivery within 15 months.'),
    ('The price is CNY 1000.', 'The price is USD 1000.'),
    ('Quality shall conform to specification E-1.', 'Quality shall conform to [specification].'),
])
def test_known_numeric_or_quantity_values_cannot_be_silently_removed(original, proposed):
    agent, c, finding = generate(original, proposed)
    with pytest.raises(ReviewStageError) as exc:
        agent._generate_suggestions([c], [finding], [])
    assert exc.value.code == 'SUGGESTION_FACT_LOSS'


def test_fact_loss_produces_explicit_failed_suggestion_stage():
    agent, c, finding = generate('The buyer purchases one unit.', 'The buyer purchases [quantity] units.')
    result = agent(ContractReviewState(raw_text=c.content, clauses=[c], risk_findings=[finding]))
    assert result['failed_stage'] == 'suggestion'
    assert result['version_diff'] == 'Generation failed'
    assert result['errors'][0].startswith('SUGGESTION_FACT_LOSS:')
    assert all('[quantity]' not in s.suggested_text for s in result['suggestions'])


def test_preserved_values_and_thousands_formatting_are_accepted_with_disclosure():
    agent, c, finding = generate('The price is CNY 1000, due within 30 days.',
                               'The price is CNY 1,000, due within 30 days by [proposed payment channel].')
    result = agent._generate_suggestions([c], [finding], [])[0]
    assert result.original_text == c.content
    assert result.reason.startswith(PROPOSAL_NOTICE)


def test_graph_reports_partial_for_changed_payment_period(monkeypatch):
    import asyncio
    from tests.test_workflow_baseline import FakeLLM
    from src.agents import clause_extraction, risk_identification, compliance_check, suggestion
    from src.pipeline.runner import run_review
    from src.pipeline.state import ReviewStatus
    from src.retrieval.knowledge import KnowledgeChunk, KnowledgeStore
    chunk = KnowledgeChunk.from_dict({
        'chunk_id': 'test-price', 'source': 'fixture', 'title': 'Test knowledge',
        'text': 'The price may be agreed by both parties.', 'url': 'https://example.invalid/test',
        'jurisdiction': 'CN-mainland', 'effective_from': '2021-01-01', 'effective_to': None,
        'source_version': 'test-v1', 'retrieved_at': '2026-10-21',
        'review_status': 'reviewed', 'keywords': ['price'],
    })
    monkeypatch.setattr(KnowledgeStore, 'load', classmethod(lambda cls: KnowledgeStore([chunk])))
    fake_model = FakeLLM()  # Retain the original 30-to-20-day response as a negative case.
    for module in (clause_extraction, risk_identification, compliance_check, suggestion):
        monkeypatch.setattr(module, 'get_llm', lambda: fake_model)
    result = asyncio.run(run_review('1. Payment\nThe price is CNY 1000, payable within 30 days after delivery.'))
    assert result.status == ReviewStatus.PARTIAL
    assert result.failed_stage == 'suggestion'
    assert any(error.startswith('SUGGESTION_FACT_LOSS:') for error in result.errors)
    assert len(fake_model.calls) == 4
