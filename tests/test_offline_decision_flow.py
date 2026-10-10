import asyncio

from agent.contracts import (
    Hypothesis,
    HypothesisChallenge,
    RemediationAction,
)
from agent.evidence_judge import run_evidence_judge
from agent.orchestrator import (
    create_investigation_state,
    run_specialist_agents,
)
from agent.policy_guard import run_policy_guard
from scenario_registry import (
    activate_scenario,
    get_active_incident,
    get_active_scenario_summary,
)


CASES = [
    ("payment_connection_pool", "database_session_leak"),
    ("video_edge_routing", "routing_misconfiguration"),
    ("feed_cache_cascade", "cache_key_compatibility_failure"),
]


def evidence_id_by_type(state, source_type: str) -> str:
    for item in state.evidence:
        if item.source_type == source_type:
            return item.evidence_id

    raise AssertionError(f"缺少 {source_type} 类型证据")


async def verify_decision_flow(
    scenario_id: str,
    expected_hypothesis_id: str,
) -> None:
    activate_scenario(scenario_id)

    scenario = get_active_scenario_summary()
    state = create_investigation_state(
        scenario_id=scenario["scenario_id"],
        incident=get_active_incident(),
    )

    state = await run_specialist_agents(
        state=state,
        domain=scenario["domain"],
    )

    metric_id = evidence_id_by_type(state, "metric")
    trace_id = evidence_id_by_type(state, "trace")
    change_id = evidence_id_by_type(state, "change")
    rag_id = evidence_id_by_type(state, "rag")
    log_id = evidence_id_by_type(state, "log")

    alternative_id = f"{scenario_id}_alternative"

    state.hypotheses = [
        Hypothesis(
            hypothesis_id=expected_hypothesis_id,
            statement="与指标、链路、变更和知识库证据一致的主要根因。",
            supporting_evidence_ids=[
                metric_id,
                trace_id,
                change_id,
                rag_id,
            ],
            confidence=0.80,
        ),
        Hypothesis(
            hypothesis_id=alternative_id,
            statement="仅由单条日志支持的竞争性假设。",
            supporting_evidence_ids=[log_id],
            confidence=0.60,
        ),
    ]

    state.challenges = [
        HypothesisChallenge(
            hypothesis_id=expected_hypothesis_id,
            verdict="supported",
            concerns=[],
            missing_evidence=[],
            contradictory_evidence_ids=[],
        ),
        HypothesisChallenge(
            hypothesis_id=alternative_id,
            verdict="contradicted",
            concerns=["缺少指标、变更和知识库的交叉支持。"],
            missing_evidence=["需要更多独立来源确认。"],
            contradictory_evidence_ids=[metric_id],
        ),
    ]

    state = run_evidence_judge(state)

    assert state.selected_hypothesis_id == expected_hypothesis_id

    state.proposed_actions = [
        RemediationAction(
            action_id="rollback_candidate_change",
            category="rollback",
            description="回滚与事故高度相关的最近生产变更。",
            rationale="该操作可能影响生产流量，必须人工确认。",
            risk_level="high",
            requires_human_approval=True,
            verification_plan=[
                "观察错误率是否下降。",
                "观察关键延迟是否恢复。",
            ],
        ),
        RemediationAction(
            action_id="observe_recovery_metrics",
            category="observe",
            description="持续观察错误率、延迟和关键业务成功率。",
            rationale="只读操作，不改变生产状态。",
            risk_level="low",
            requires_human_approval=False,
            verification_plan=[
                "连续 10 分钟检查核心指标。",
            ],
        ),
    ]

    state = run_policy_guard(state)

    decisions = {
        item.action_id: item.decision
        for item in state.policy_decisions
    }

    assert state.phase == "awaiting_approval"
    assert decisions["rollback_candidate_change"] == "requires_approval"
    assert decisions["observe_recovery_metrics"] == "allowed"

    print(
        f"✓ {scenario_id}: "
        f"Judge 选中 {state.selected_hypothesis_id}，"
        f"高风险操作已进入人工审批。"
    )


async def main() -> None:
    for scenario_id, expected_hypothesis_id in CASES:
        await verify_decision_flow(
            scenario_id=scenario_id,
            expected_hypothesis_id=expected_hypothesis_id,
        )

    print("3 个场景的离线决策闭环测试全部通过。")


if __name__ == "__main__":
    asyncio.run(main())