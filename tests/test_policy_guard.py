from agent.contracts import RemediationAction
from agent.policy_guard import run_policy_guard
from agent.state import InvestigationState


def main():
    state = InvestigationState(
        run_id="policy_guard_demo",
        scenario_id="video_edge_routing",
        incident={}
    )

    state.proposed_actions = [
        RemediationAction(
            action_id="rollback_routing",
            category="rollback",
            description="回滚 APAC 路由配置",
            rationale="恢复上一稳定版本",
            risk_level="high",
            requires_human_approval=True,
            verification_plan=[
                "验证 APAC 播放成功率恢复至 95%"
            ]
        ),
        RemediationAction(
            action_id="observe_metrics",
            category="observe",
            description="持续观察播放成功率和错误日志",
            rationale="确认修复效果",
            risk_level="low",
            requires_human_approval=False,
            verification_plan=[
                "持续观察 15 分钟"
            ]
        ),
        RemediationAction(
            action_id="unsafe_config_change",
            category="config_change",
            description="直接修改生产源站配置",
            rationale="尝试恢复路由",
            risk_level="medium",
            requires_human_approval=False,
            verification_plan=[]
        )
    ]

    state = run_policy_guard(state)

    for decision in state.policy_decisions:
        print(
            decision.action_id,
            "→",
            decision.decision,
            "：",
            decision.reason
        )

    decisions = {
        decision.action_id: decision.decision
        for decision in state.policy_decisions
    }

    assert decisions["rollback_routing"] == "requires_approval"
    assert decisions["observe_metrics"] == "allowed"
    assert decisions["unsafe_config_change"] == "blocked"
    assert state.phase == "blocked"

    print("Policy Guard 离线测试通过。")


if __name__ == "__main__":
    main()