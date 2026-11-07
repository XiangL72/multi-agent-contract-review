# Modified for the English text/TXT demo; scope and behavior are documented in README.md.
"""Shared schemas for a fixed, request-local four-agent workflow."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class RiskLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NEEDS_REVIEW = "needs_review"


class ClauseCategory(str, Enum):
    PAYMENT = "payment"
    LIABILITY = "liability"
    CONFIDENTIALITY = "confidentiality"
    TERMINATION = "termination"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    DISPUTE_RESOLUTION = "dispute_resolution"
    FORCE_MAJEURE = "force_majeure"
    WARRANTY = "warranty"
    INDEMNIFICATION = "indemnification"
    GOVERNING_LAW = "governing_law"
    OTHER = "other"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    TIMED_OUT = "timed_out"

class ContractEntity(BaseModel):
    """Contract entity."""
    entity_type: str = Field(description="Entity type: party_a, party_b, amount, date, subject")
    value: str = Field(description="Entity value")
    location: str = Field(default="", description="Location in the document")


class Clause(BaseModel):
    """Clause."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = Field(description="Clause title")
    content: str = Field(description="Clause content")
    category: ClauseCategory = Field(default=ClauseCategory.OTHER)
    section_number: str = Field(default="", description="Section number")
    entities: list[ContractEntity] = Field(default_factory=list)
    start: int | None = None
    end: int | None = None


class EvidenceSpan(BaseModel):
    start: int
    end: int
    quote: str


class RiskFinding(BaseModel):
    """Risk finding."""
    clause_id: str = Field(description="Associated clause ID")
    risk_level: RiskLevel = Field(description="Risk level")
    risk_type: str = Field(description="Risk type")
    description: str = Field(description="Risk description")
    buyer_impact: str = Field(default="", description="Buyer impact")
    seller_impact: str = Field(default="", description="Seller impact")
    rationale: str = Field(default="", description="Reasoning")
    evidence: EvidenceSpan | None = None


class ComplianceFinding(BaseModel):
    """Compliance finding."""
    clause_id: str = Field(description="Associated clause ID")
    status: ComplianceStatus = Field(description="Compliance status")
    regulation: str = Field(description="Supporting source")
    issue: str = Field(description="Candidate compliance issue")
    recommendation: str = Field(default="", description="Recommendation")
    evidence: EvidenceSpan | None = None
    knowledge_citations: list[dict] = Field(default_factory=list)


class Suggestion(BaseModel):
    """Suggestion."""
    clause_id: str = Field(description="Associated clause ID")
    original_text: str = Field(description="Original text")
    suggested_text: str = Field(description="Proposed revised text")
    reason: str = Field(description="Reason for revision")
    priority: RiskLevel = Field(description="Priority")
    kind: str = "revision"

class ContractReviewState(BaseModel):
    """Request-local state shared by the four agents."""

    review_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: ReviewStatus = Field(default=ReviewStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.now)

    raw_text: str = Field(default="", description="Original contract text")
    document_hash: str = Field(default="", description="SHA-256 of normalized text")
    jurisdiction: str = "CN-mainland"
    as_of_date: str = "2026-10-20"

    clauses: list[Clause] = Field(default_factory=list)
    entities: list[ContractEntity] = Field(default_factory=list)
    contract_type: str = Field(default="", description="Contract type")

    risk_findings: list[RiskFinding] = Field(default_factory=list)
    overall_risk_level: RiskLevel = Field(default=RiskLevel.NONE)
    risk_summary: str = Field(default="")

    compliance_findings: list[ComplianceFinding] = Field(default_factory=list)
    overall_compliance: ComplianceStatus = Field(default=ComplianceStatus.NEEDS_REVIEW)
    missing_clauses: list[str] = Field(default_factory=list)
    knowledge_status: str = "not_checked"
    knowledge_version: str = ""

    suggestions: list[Suggestion] = Field(default_factory=list)
    version_diff: str = Field(default="", description="Unified text diff")

    errors: list[str] = Field(default_factory=list)
    failed_stage: str = ""
    diagnostics: list[dict] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
