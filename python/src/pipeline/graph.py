# Modified for the English text/TXT demo; scope and behavior are documented in README.md.
"""Fixed, serial four-stage contract review graph for one synchronous request."""

from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from ..agents.clause_extraction import ClauseExtractionAgent
from ..agents.risk_identification import RiskIdentificationAgent
from ..agents.compliance_check import ComplianceCheckAgent
from ..agents.suggestion import SuggestionAgent
from .state import ContractReviewState, ReviewStatus

logger = logging.getLogger(__name__)


def route_after_stage(state: ContractReviewState) -> Literal["next", "stop"]:
    return "stop" if state.failed_stage or state.errors else "next"


def complete_node(state: ContractReviewState) -> dict:
    if any("TOTAL_TIMEOUT" in error or "MODEL_TIMEOUT" in error for error in state.errors):
        return {"status": ReviewStatus.TIMED_OUT}
    if state.failed_stage == "suggestion":
        return {"status": ReviewStatus.PARTIAL}
    if state.failed_stage or state.errors:
        return {"status": ReviewStatus.FAILED}
    if state.knowledge_status != "grounded":
        return {"status": ReviewStatus.PARTIAL}
    logger.info("Review completed review_id=%s clauses=%d risks=%d compliance=%d suggestions=%d",
                state.review_id, len(state.clauses), len(state.risk_findings),
                len(state.compliance_findings), len(state.suggestions))
    return {"status": ReviewStatus.SUCCESS}


def build_review_graph() -> StateGraph:
    graph = StateGraph(ContractReviewState)
    graph.add_node("clause_extraction", ClauseExtractionAgent())
    graph.add_node("risk_identification", RiskIdentificationAgent())
    graph.add_node("compliance_check", ComplianceCheckAgent())
    graph.add_node("suggestion", SuggestionAgent())
    graph.add_node("complete", complete_node)
    graph.set_entry_point("clause_extraction")
    graph.add_conditional_edges("clause_extraction", route_after_stage,
                                {"next": "risk_identification", "stop": "complete"})
    graph.add_conditional_edges("risk_identification", route_after_stage,
                                {"next": "compliance_check", "stop": "complete"})
    graph.add_conditional_edges("compliance_check", route_after_stage,
                                {"next": "suggestion", "stop": "complete"})
    graph.add_edge("suggestion", "complete")
    graph.add_edge("complete", END)
    return graph


def create_review_pipeline():
    """Compile per request; no checkpoint or background execution in Phase 1."""
    return build_review_graph().compile()
