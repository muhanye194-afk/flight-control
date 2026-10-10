from typing import List, Literal

from pydantic import BaseModel


class Citation(BaseModel):
    source: str
    section: str
    excerpt: str
    rrf_score: float


class ProposedAction(BaseModel):
    action: str
    rationale: str
    risk_level: Literal["low", "medium", "high"]
    requires_human_approval: bool
    verification_plan: List[str]


class InvestigationReport(BaseModel):
    status: Literal[
        "investigated",
        "needs_more_evidence",
        "blocked"
    ]
    executive_summary: str
    root_cause: str
    confidence: Literal["low", "medium", "high"]
    evidence: List[str]
    citations: List[Citation]
    knowledge_gaps: List[str]
    proposed_actions: List[ProposedAction]