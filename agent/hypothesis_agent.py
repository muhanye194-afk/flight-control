import json
from typing import Any, Dict, List

from pydantic import BaseModel

from agent.contracts import (
    AgentFinding,
    AgentResult,
    EvidenceItem,
    Hypothesis,
)
from agent.llm_client import parse_structured_response


SYSTEM_PROMPT = """
You are a production incident hypothesis analyst.

Use only the supplied incident details and evidence cards.

Rules:
1. Generate exactly 2 or 3 competing root-cause hypotheses.
2. A hypothesis is not a confirmed fact.
3. Every hypothesis must reference only evidence_id values that exist
   in the supplied evidence cards.
4. Do not invent metrics, logs, deployments, documents, or trace data.
5. Put counterevidence in contradicting_evidence_ids when applicable.
6. confidence must be between 0 and 1.
7. Do not propose remediation actions.
8. Return only data matching the required JSON schema.
"""


class HypothesisSet(BaseModel):
    hypotheses: List[Hypothesis]


def build_hypothesis_messages(
    incident: Dict[str, Any],
    evidence: List[EvidenceItem]
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


def run_hypothesis_agent(
    incident: Dict[str, Any],
    evidence: List[EvidenceItem]
) -> AgentResult:
    if not evidence:
        finding = AgentFinding(
            agent_name="hypothesis_agent",
            status="needs_more_evidence",
            summary="没有证据卡，无法生成可验证的根因假设。"
        )

        return AgentResult(
            agent_name="hypothesis_agent",
            finding=finding
        )

    messages = build_hypothesis_messages(
        incident,
        evidence
    )

    hypothesis_set = parse_structured_response(
        messages,
        HypothesisSet
    )

    if not 2 <= len(hypothesis_set.hypotheses) <= 3:
        raise RuntimeError(
            "Hypothesis Agent 必须返回 2 到 3 个竞争假设。"
        )

    evidence_ids = [
        evidence_id
        for hypothesis in hypothesis_set.hypotheses
        for evidence_id in hypothesis.supporting_evidence_ids
    ]

    finding = AgentFinding(
        agent_name="hypothesis_agent",
        status="completed",
        summary=(
            f"基于 {len(evidence)} 张证据卡生成了 "
            f"{len(hypothesis_set.hypotheses)} 个竞争假设。"
        ),
        evidence_ids=evidence_ids,
        hypotheses=hypothesis_set.hypotheses
    )

    return AgentResult(
        agent_name="hypothesis_agent",
        finding=finding,
        tool_trace=[
            {
                "tool": "llm_structured_hypothesis_generation",
                "status": "completed"
            }
        ]
    )