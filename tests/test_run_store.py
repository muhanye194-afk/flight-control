from agent.contracts import (
    PolicyDecision,
    RemediationAction,
)
from agent.run_store import (
    approve_actions,
    get_run,
    save_run,
)
from agent.state import InvestigationState


def main() -> None:
    state = InvestigationState(
        run_id="approval_demo_001",
        scenario_id="video_edge_routing",
        incident={},
    )

    state.proposed_actions = [
        RemediationAction(
            action_id="rollback_routing",
            category="rollback",
            description="回滚最近发布的 APAC 源站路由权重变更。",
            rationale="该操作会影响生产流量，必须人工确认。",
            risk_level="high",
            requires_human_approval=True,
            verification_plan=[
                "观察 APAC 播放成功率。",
                "观察 route_not_found 错误是否停止增长。",
            ],
        ),
    ]

    state.policy_decisions = [
        PolicyDecision(
            action_id="rollback_routing",
            decision="requires_approval",
            reason="回滚属于高风险生产变更。",
        ),
    ]

    save_run(state)

    approved_state = approve_actions(
        run_id="approval_demo_001",
        action_ids=["rollback_routing"],
        approver="muhanye",
    )

    loaded_state = get_run("approval_demo_001")

    assert "rollback_routing" in approved_state.approved_action_ids
    assert loaded_state.run_id == "approval_demo_001"
    assert loaded_state.phase == "approved"
    assert loaded_state.human_approval_required is False
    assert "muhanye 人工批准了操作" in approved_state.audit_log[-1]

    print("muhanye 人工批准了操作：rollback_routing")
    print("Run Store approval test passed.")


if __name__ == "__main__":
    main()