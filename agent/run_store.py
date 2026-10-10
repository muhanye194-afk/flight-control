from typing import Dict, List

from agent.state import InvestigationState


RUN_STORE: Dict[str, InvestigationState] = {}


def save_run(state: InvestigationState) -> InvestigationState:
    RUN_STORE[state.run_id] = state
    return state


def get_run(run_id: str) -> InvestigationState:
    if run_id not in RUN_STORE:
        raise KeyError(f"找不到 run：{run_id}")

    return RUN_STORE[run_id]


def approve_actions(
    run_id: str,
    action_ids: List[str],
    approver: str,
) -> InvestigationState:
    state = get_run(run_id)

    action_map = {
        action.action_id: action
        for action in state.proposed_actions
    }

    decision_map = {
        decision.action_id: decision
        for decision in state.policy_decisions
    }

    for action_id in action_ids:
        if action_id not in action_map:
            raise ValueError(f"找不到操作：{action_id}")

        decision = decision_map.get(action_id)

        if decision is None:
            raise ValueError(f"操作 {action_id} 缺少策略决策。")

        if decision.decision != "requires_approval":
            raise ValueError(
                f"操作 {action_id} 不需要人工审批，不能通过审批接口处理。"
            )

        if action_id not in state.approved_action_ids:
            state.approved_action_ids.append(action_id)

    approved_text = "、".join(action_ids)

    state.audit_log.append(
        f"{approver} 人工批准了操作：{approved_text}"
    )

    required_approval_action_ids = [
        decision.action_id
        for decision in state.policy_decisions
        if decision.decision == "requires_approval"
    ]

    all_required_actions_approved = all(
        action_id in state.approved_action_ids
        for action_id in required_approval_action_ids
    )

    if required_approval_action_ids and all_required_actions_approved:
        state.phase = "approved"
        state.human_approval_required = False

    return state