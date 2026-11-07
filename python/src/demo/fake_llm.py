"""A deterministic, synthetic model substitute for a control-flow demo."""

from __future__ import annotations

import json
import re
from types import SimpleNamespace


class DemoLLM:
    def invoke(self, messages, **kwargs):
        system = messages[0].content
        user = messages[-1].content
        if "STAGE: EXTRACTION" in system:
            text = user.split(":\n\n", 1)[1]
            payload = {"contract_type": "purchase_contract", "clauses": [
                {"title": "Synthetic clause", "content": text, "category": "other"}], "entities": []}
        elif "STAGE: RISK" in system:
            clause_id = re.search(r"Clause ID: ([^\]]+)", user).group(1)
            risky = bool(re.search(r"\bunlimited liability\b", user, re.I)) and not bool(re.search(r"does not assume unlimited liability", user, re.I))
            payload = {"findings": ([{"clause_id": clause_id, "risk_level": "high",
                                      "risk_type": "unlimited_liability", "description": "Synthetic risk candidate",
                                      "rationale": "Offline simulation only"}] if risky else []),
                       "overall_risk_level": "high" if risky else "none", "risk_summary": "Offline simulation only"}
        elif "STAGE: COMPLIANCE" in system:
            findings = []
            if "not agreed" in user.casefold() and "civil-code-510|" in user:
                from ..retrieval.knowledge import KnowledgeStore
                chunk = next(c for c in KnowledgeStore.load().chunks if c.chunk_id == "civil-code-510")
                clause_id = re.search(r"\[Clause ID: ([^\]]+)\]", user).group(1)
                findings.append({"clause_id": clause_id, "status": "needs_review",
                                 "regulation": chunk.title,
                                 "issue": "Offline example: the price needs clarification.",
                                 "recommendation": "Agree a clear price before relying on this draft.",
                                 "citations": [{"chunk_id": chunk.chunk_id,
                                                "source_version": chunk.source_version,
                                                "quote": chunk.text}]})
            payload = {"findings": findings, "missing_clauses": [], "overall_compliance": "needs_review"}
        elif "STAGE: SUGGESTION" in system:
            clause_id = re.search(r"Clause ID=([^\n]+)", user).group(1)
            original = re.search(r"Clause content: .*?: (.*?)\n(?:Risk|Issue):", user, re.DOTALL).group(1)
            payload = {"suggestions": [{"clause_id": clause_id, "original_text": original,
                                        "suggested_text": original + " (example revision)", "reason": "Offline example",
                                        "priority": "high"}]}
        else:
            raise AssertionError("Unknown demo prompt")
        return SimpleNamespace(content=json.dumps(payload, ensure_ascii=False))


def install_demo_model() -> None:
    from ..agents import clause_extraction, compliance_check, risk_identification, suggestion
    fake = DemoLLM()
    for module in (clause_extraction, compliance_check, risk_identification, suggestion):
        module.get_llm = lambda fake=fake: fake
