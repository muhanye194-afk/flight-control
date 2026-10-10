import json
from typing import Dict, List, Optional

from pydantic import BaseModel

from agent.contracts import (
    Hypothesis,
    HypothesisScore,
    RemediationAction,
)
from agent.llm_client import parse_structured_response
from agent.state import InvestigationState


SYSTEM_PROMPT = """
You are a production remediation planner.

Create a safe remediation plan for the selected incident hypothesis.

Rules:
1. Use only the supplied hypothesis, evidence cards, and Judge score.
2. Return 2 to 4 ordered remediation actions.
3. Never claim that an action has already been executed.
4. Every production-changing category must set
   requires_human_approval to true.
5. Every action must include a concrete verification_plan.
6. Prefer rollback, canary, staged validation, and observability.
7. Do not invent infrastructure, permissions, or recovery results.
8. Return only data matching the required JSON schema.
"""


class RemediationPlan(BaseModel):
    actions: List[RemediationAction]


def find_selected_hypothesis(
    state: InvestigationState
) -> Hypothesis:
    for hypothesis in state.hypotheses:
        if (
            hypothesis.hypothesis_id
            == state.selected_hypothesis_id
        ):
            return hypothesis

    raise RuntimeError("找不到 Judge 选中的根因假设。")


def find_selected_score(
    state: InvestigationState
) -> Optional[HypothesisScore]:
    for score in state.judge_scores:
        if score.hypothesis_id == state.selected_hypothesis_id:
            return score

    return None


def build_planning_messages(
    state: InvestigationState
) -> List[Dict[str, str]]:
    hypothesis = find_selected_hypothesis(state)
    score = find_selected_score(state)

    payload = {
        "selected_hypothesis": hypothesis.model_dump(),
        "judge_score": (
            score.model_dump()
            if score is not None
            else None
        ),
        "evidence_cards": [
            item.model_dump()
            for item in state.evidence
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


def run_remediation_planner(
    state: InvestigationState
) -> List[RemediationAction]:
    if state.selected_hypothesis_id is None:
        raise RuntimeError(
            "Judge 尚未选择根因，不能生成修复计划。"
        )

    messages = build_planning_messages(state)

    plan = parse_structured_response(
        messages,
        RemediationPlan
    )

    if not 2 <= len(plan.actions) <= 4:
        raise RuntimeError(
            "Remediation Planner 必须返回 2 到 4 个操作。"
        )

    return plan.actions