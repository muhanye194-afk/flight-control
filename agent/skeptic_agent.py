import json
from typing import Any, Dict, List

from pydantic import BaseModel

from agent.contracts import (
    AgentFinding,
    AgentResult,
    EvidenceItem,
    Hypothesis,
    HypothesisChallenge,
)
from agent.llm_client import parse_structured_response


SYSTEM_PROMPT = """
You are the Skeptic Agent in a production incident system.

Your task is to challenge root-cause hypotheses using only the supplied
evidence cards.

Rules:
1. Review every supplied hypothesis exactly once.
2. Do not invent evidence, metrics, logs, deployments, or documents.
3. A hypothesis is "contradicted" only when supplied evidence directly
   conflicts with it.
4. Use "weak" when evidence is relevant but not enough to establish cause.
5. Use "insufficient_evidence" when key evidence is missing.
6. contradictory_evidence_ids must only contain supplied evidence_id values.
7. Identify missing evidence that would change confidence.
8. Do not propose remediation actions.
9. Return only data matching the required JSON schema.
"""


class SkepticReview(BaseModel):
    challenges: List[HypothesisChallenge]


def build_skeptic_messages(
    incident: Dict[str, Any],
    evidence: List[EvidenceItem],
    hypotheses: List[Hypothesis]
) -> List[Dict[str, str]]:
    alert = incident.get("alert", {})

    payload = {
        "incident_summary": {
            "service": incident.get("service", ""),
            "alert_title": alert.get("title", ""),
            "severity": alert.get("severity", "")
        },
        "evidence_cards": [
            item.model_dump()
            for item in evidence
        ],
        "hypotheses_to_review": [
            hypothesis.model_dump()
            for hypothesis in hypotheses
        ]
    }

    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": json.dumps(
                payload,
                ensure_ascii=False,
                indent=2
            )
        }
    ]


def run_skeptic_agent(
    incident: Dict[str, Any],
    evidence: List[EvidenceItem],
    hypotheses: List[Hypothesis]
) -> AgentResult:
    if not hypotheses:
        finding = AgentFinding(
            agent_name="skeptic_agent",
            status="needs_more_evidence",
            summary="没有待审查假设，无法执行反驳审查。"
        )

        return AgentResult(
            agent_name="skeptic_agent",
            finding=finding
        )

    messages = build_skeptic_messages(
        incident,
        evidence,
        hypotheses
    )

    review = parse_structured_response(
        messages,
        SkepticReview
    )

    expected_ids = {
        hypothesis.hypothesis_id
        for hypothesis in hypotheses
    }

    reviewed_ids = {
        challenge.hypothesis_id
        for challenge in review.challenges
    }

    if reviewed_ids != expected_ids:
        raise RuntimeError(
            "Skeptic Agent 必须逐一审查全部假设，"
            "且不能生成未知假设 ID。"
        )

    evidence_ids = [
        evidence_id
        for challenge in review.challenges
        for evidence_id in challenge.contradictory_evidence_ids
    ]

    verdict_counts = {
        verdict: sum(
            challenge.verdict == verdict
            for challenge in review.challenges
        )
        for verdict in [
            "supported",
            "weak",
            "contradicted",
            "insufficient_evidence"
        ]
    }

    finding = AgentFinding(
        agent_name="skeptic_agent",
        status="completed",
        summary=(
            f"已审查 {len(review.challenges)} 个假设；"
            f"支持 {verdict_counts['supported']} 个，"
            f"证据不足 {verdict_counts['insufficient_evidence']} 个，"
            f"较弱 {verdict_counts['weak']} 个，"
            f"被反驳 {verdict_counts['contradicted']} 个。"
        ),
        evidence_ids=evidence_ids
    )

    return AgentResult(
        agent_name="skeptic_agent",
        finding=finding,
        challenges=review.challenges,
        tool_trace=[
            {
                "tool": "llm_structured_skeptic_review",
                "status": "completed"
            }
        ]
    )