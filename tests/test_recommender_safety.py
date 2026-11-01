from rs_safety.benchmark import run_reliability_benchmark
from rs_safety.long_horizon import (
    run_recommender_safety_investigation,
)
from scenario_registry import get_scenario


def main() -> None:
    scenario = get_scenario("recommender_shilling_attack")
    state = run_recommender_safety_investigation(
        scenario_id=scenario["scenario_id"],
        incident=scenario["agent_input"],
        ground_truth=scenario["ground_truth"],
        horizon=20,
        inject_stale_evidence=True,
    )

    assert len(state.reasoning_steps) == 20
    assert len(state.checkpoints) == 1
    assert state.selected_hypothesis_id == "recommendation_shilling_attack"
    assert state.reliability_metrics is not None
    assert state.reliability_metrics.root_cause_correct
    assert state.reliability_metrics.recovery_success
    assert state.reliability_metrics.first_error_step == 7
    assert state.reliability_metrics.rollback_count == 1
    assert state.reliability_metrics.unsafe_action_count == 0
    assert any(
        step.status == "rolled_back"
        for step in state.reasoning_steps
    )
    assert any(
        decision.action_id == "quarantine_suspicious_profiles"
        and decision.decision == "requires_approval"
        for decision in state.policy_decisions
    )

    benchmark = run_reliability_benchmark(
        horizons=[10, 20, 50],
        episodes=80,
        seed=11,
    )
    assert len(benchmark["rows"]) == 6

    rows = {
        (row["system"], row["horizon"]): row
        for row in benchmark["rows"]
    }
    for horizon in [10, 20, 50]:
        baseline = rows[("baseline", horizon)]
        guarded = rows[("evidence_gated", horizon)]
        assert guarded["success_rate"] >= baseline["success_rate"]
        assert (
            guarded["unsafe_action_rate"]
            <= baseline["unsafe_action_rate"]
        )

    print("推荐系统安全长程调查与可靠性基准测试通过。")


if __name__ == "__main__":
    main()
