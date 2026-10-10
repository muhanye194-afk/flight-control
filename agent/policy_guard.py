from typing import List

from agent.contracts import (
    PolicyDecision,
    RemediationAction,
)
from agent.state import InvestigationState


PRODUCTION_CHANGE_CATEGORIES = {
    "rollback",
    "config_change",
    "traffic_shift",
    "scale",
    "cache_invalidation",
    "code_fix"
}


def evaluate_action(
    action: RemediationAction
) -> PolicyDecision:
    if not action.verification_plan:
        return PolicyDecision(
            action_id=action.action_id,
            decision="blocked",
            reason="操作没有验证方案，禁止进入审批或执行阶段。"
        )

    if action.risk_level == "high":
        return PolicyDecision(
            action_id=action.action_id,
            decision="requires_approval",
            reason="高风险操作必须人工批准。"
        )

    if action.category in PRODUCTION_CHANGE_CATEGORIES:
        return PolicyDecision(
            action_id=action.action_id,
            decision="requires_approval",
            reason="生产环境变更必须人工批准。"
        )

    if action.requires_human_approval:
        return PolicyDecision(
            action_id=action.action_id,
            decision="requires_approval",
            reason="Planner 标记该操作需要人工批准。"
        )

    return PolicyDecision(
        action_id=action.action_id,
        decision="allowed",
        reason="低风险观察类操作可自动执行。"
    )


def run_policy_guard(
    state: InvestigationState
) -> InvestigationState:
    if not state.proposed_actions:
        state.phase = "blocked"
        state.audit_log.append(
            "Policy Guard 阻止流程：没有修复方案。"
        )

        return state

    decisions: List[PolicyDecision] = [
        evaluate_action(action)
        for action in state.proposed_actions
    ]

    state.policy_decisions = decisions

    blocked_actions = [
        decision
        for decision in decisions
        if decision.decision == "blocked"
    ]

    approval_actions = [
        decision
        for decision in decisions
        if decision.decision == "requires_approval"
    ]

    state.human_approval_required = bool(
        approval_actions
    )

    if blocked_actions:
        state.phase = "blocked"
        state.audit_log.append(
            f"Policy Guard 拦截了 "
            f"{len(blocked_actions)} 个不安全操作。"
        )

    elif approval_actions:
        state.phase = "awaiting_approval"
        state.audit_log.append(
            f"Policy Guard 要求人工审批 "
            f"{len(approval_actions)} 个生产操作。"
        )

    else:
        state.audit_log.append(
            "Policy Guard 允许全部低风险观察操作。"
        )

    return state