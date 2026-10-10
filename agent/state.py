from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from agent.contracts import (
    AgentFinding,
    EvidenceItem,
    Hypothesis,
    HypothesisChallenge,
    HypothesisScore,
    PolicyDecision,
    RemediationAction,
)


class InvestigationState(BaseModel):
    run_id: str
    scenario_id: str
    incident: Dict[str, Any]

    phase: Literal[
        "intake",
        "gathering_evidence",
        "generating_hypotheses",
        "challenging",
        "judging",
        "awaiting_approval",
        "approved",
        "verified",
        "blocked",
    ] = "intake"

    evidence: List[EvidenceItem] = Field(default_factory=list)
    findings: List[AgentFinding] = Field(default_factory=list)

    hypotheses: List[Hypothesis] = Field(default_factory=list)
    challenges: List[HypothesisChallenge] = Field(default_factory=list)
    judge_scores: List[HypothesisScore] = Field(default_factory=list)

    proposed_actions: List[RemediationAction] = Field(default_factory=list)
    policy_decisions: List[PolicyDecision] = Field(default_factory=list)

    agent_reliability: Dict[str, float] = Field(default_factory=dict)

    selected_hypothesis_id: Optional[str] = None

    tool_trace: List[Dict[str, str]] = Field(default_factory=list)
    audit_log: List[str] = Field(default_factory=list)

    human_approval_required: bool = True
    approved_action_ids: List[str] = Field(default_factory=list)