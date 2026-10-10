from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    evidence_id: str
    source_type: Literal["metric", "log", "trace", "change", "rag"]
    source_ref: str
    observation: str
    source_reliability: float = Field(ge=0, le=1)
    freshness_seconds: Optional[int] = None


class Hypothesis(BaseModel):
    hypothesis_id: str
    statement: str
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradicting_evidence_ids: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class HypothesisChallenge(BaseModel):
    hypothesis_id: str
    verdict: Literal[
        "supported",
        "weak",
        "contradicted",
        "insufficient_evidence"
    ]
    concerns: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    contradictory_evidence_ids: List[str] = Field(
        default_factory=list
    )


class HypothesisScore(BaseModel):
    hypothesis_id: str
    prior_confidence: float = Field(ge=0, le=1)
    evidence_support_score: float = Field(ge=0, le=1)
    diversity_bonus: float = Field(ge=0, le=1)
    challenge_penalty: float = Field(ge=0, le=1)
    final_score: float = Field(ge=0, le=1)
    supporting_evidence_count: int
    rationale: List[str] = Field(default_factory=list)

class RemediationAction(BaseModel):
    action_id: str
    category: Literal[
        "rollback",
        "config_change",
        "traffic_shift",
        "scale",
        "cache_invalidation",
        "code_fix",
        "observe"
    ]
    description: str
    rationale: str
    risk_level: Literal["low", "medium", "high"]
    requires_human_approval: bool
    verification_plan: List[str] = Field(
        default_factory=list
    )


class PolicyDecision(BaseModel):
    action_id: str
    decision: Literal[
        "allowed",
        "requires_approval",
        "blocked"
    ]
    reason: str

class AgentFinding(BaseModel):
    agent_name: str
    status: Literal["completed", "needs_more_evidence"]
    summary: str
    evidence_ids: List[str] = Field(default_factory=list)
    hypotheses: List[Hypothesis] = Field(default_factory=list)


class AgentResult(BaseModel):
    agent_name: str
    finding: AgentFinding
    evidence: List[EvidenceItem] = Field(default_factory=list)
    challenges: List[HypothesisChallenge] = Field(
        default_factory=list
    )
    tool_trace: List[Dict[str, str]] = Field(
        default_factory=list
    )
