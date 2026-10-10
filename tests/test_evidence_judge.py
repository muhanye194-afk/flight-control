import asyncio

from agent.contracts import (
    Hypothesis,
    HypothesisChallenge,
)
from agent.evidence_judge import run_evidence_judge
from agent.orchestrator import (
    create_investigation_state,
    run_specialist_agents,
)
from scenario_registry import (
    activate_scenario,
    get_active_incident,
    get_active_scenario_summary,
)


def main():
    activate_scenario("video_edge_routing")

    scenario = get_active_scenario_summary()

    state = create_investigation_state(
        scenario["scenario_id"],
        get_active_incident()
    )

    state = asyncio.run(
        run_specialist_agents(
            state,
            scenario["domain"]
        )
    )

    state.hypotheses = [
        Hypothesis(
            hypothesis_id="routing_misconfiguration",
            statement=(
                "近期 APAC 路由权重发布将流量导向了"
                "错误源站，导致视频播放失败。"
            ),
            supporting_evidence_ids=[
                "obs_metric_apac_playback_start_success_rate_percent",
                "change_b82d8e1",
                "obs_trace_trc_video_001_1"
            ],
            confidence=0.80
        ),
        Hypothesis(
            hypothesis_id="origin_cluster_failure",
            statement=(
                "APAC 源站集群本身发生了基础设施故障。"
            ),
            supporting_evidence_ids=[
                "obs_log_1",
                "obs_trace_trc_video_001_2"
            ],
            confidence=0.70
        )
    ]

    state.challenges = [
        HypothesisChallenge(
            hypothesis_id="routing_misconfiguration",
            verdict="supported"
        ),
        HypothesisChallenge(
            hypothesis_id="origin_cluster_failure",
            verdict="contradicted",
            concerns=[
                "源站健康度正常，错误更符合路由配置问题。"
            ],
            contradictory_evidence_ids=[
                "obs_log_1"
            ]
        )
    ]

    state = run_evidence_judge(state)

    print("选中的假设：", state.selected_hypothesis_id)

    for score in state.judge_scores:
        print(
            score.hypothesis_id,
            "最终分数：",
            score.final_score
        )

    assert (
        state.selected_hypothesis_id
        == "routing_misconfiguration"
    )

    print("Judge 离线测试通过。")


if __name__ == "__main__":
    main()