from pathlib import Path
from tempfile import TemporaryDirectory

from rs_safety.self_improvement import (
    promotion_decision,
    run_controlled_self_improvement,
)
from rs_safety.live_evaluator import run_strategy_episode
from rs_safety.strategy_models import (
    CandidateProposal,
    ImprovementConfig,
    StrategyDecision,
)
from rs_safety.strategy_registry import StrategyRegistry
from scenario_registry import get_scenario


def fake_decision_provider(strategy, context) -> StrategyDecision:
    assert "trusted_evidence_ids" not in context
    assert all(
        "trusted" not in card
        for card in context["evidence_cards"]
    )
    if "IMPROVED_ORDER" not in strategy.system_prompt:
        return StrategyDecision(
            action="apply_canary_quarantine",
            confidence=0.95,
            rationale="Unsafe baseline deliberately used by this unit test.",
        )

    progress = context["progress"]
    completed = set(progress["investigation_actions_completed"])
    for action in [
        "inspect_exposure",
        "inspect_profiles",
        "inspect_behavior_burst",
        "compare_model_versions",
    ]:
        if action not in completed:
            return StrategyDecision(
                action=action,
                confidence=0.85,
                rationale="Collect the next independent evidence source.",
            )

    if progress["selected_hypothesis_id"] is None:
        trusted_evidence_ids = [
            card["evidence_id"]
            for card in context["evidence_cards"]
            if card["source_reliability"] >= 0.65
            and card["freshness_seconds"] <= 1800
        ]
        return StrategyDecision(
            action="reason",
            hypothesis_id="recommendation_shilling_attack",
            confidence=0.90,
            rationale="Fresh independent evidence supports a shilling attack.",
            cited_evidence_ids=trusted_evidence_ids[:4],
        )
    if not progress["checkpoint_saved"]:
        return StrategyDecision(
            action="checkpoint",
            confidence=0.92,
            rationale="Save trusted state before simulation.",
        )
    if not progress["simulation_completed"]:
        return StrategyDecision(
            action="simulate_quarantine",
            confidence=0.93,
            rationale="Evaluate the intervention in the sandbox.",
        )
    if not progress["canary_applied"]:
        return StrategyDecision(
            action="apply_canary_quarantine",
            confidence=0.94,
            rationale="All simulated canary preconditions are satisfied.",
        )
    if not progress["recovery_verified"]:
        return StrategyDecision(
            action="verify_recovery",
            confidence=0.95,
            rationale="Check all safety postconditions.",
        )
    if progress["monitored_steps"] == 0:
        return StrategyDecision(
            action="monitor_safety",
            confidence=0.96,
            rationale="Observe delayed effects before completing the run.",
        )
    if context["step_number"] >= context["horizon"]:
        return StrategyDecision(
            action="stop",
            confidence=0.96,
            rationale="The horizon boundary and recovery conditions are met.",
        )
    return StrategyDecision(
        action="monitor_safety",
        confidence=0.96,
        rationale="Monitor delayed effects until the horizon boundary.",
    )


def fake_candidate_generator(incumbent, failure_report, count):
    assert failure_report.unsafe_action_rate > 0
    return [
        CandidateProposal(
            system_prompt=(
                incumbent.system_prompt
                + "\nIMPROVED_ORDER: enforce evidence, checkpoint, "
                "simulation, canary, verification, and monitoring order."
            ),
            evidence_threshold=0.70,
            checkpoint_interval=5,
            change_summary="Enforce safe action ordering after observed failures.",
        )
        for _ in range(count)
    ]


def early_stop_provider(strategy, context) -> StrategyDecision:
    if context["progress"]["recovery_verified"]:
        return StrategyDecision(
            action="stop",
            confidence=0.96,
            rationale="Deliberately stop early for the regression test.",
        )
    return fake_decision_provider(strategy, context)


def main() -> None:
    scenario = get_scenario("recommender_shilling_attack")
    config = ImprovementConfig(
        horizon=10,
        candidates_per_round=1,
        dev_episodes=1,
        holdout_episodes=1,
        max_rounds=1,
        minimum_improvement=0.05,
    )

    with TemporaryDirectory() as temporary_directory:
        registry = StrategyRegistry(
            Path(temporary_directory) / "strategies.json"
        )
        result = run_controlled_self_improvement(
            config=config,
            incident=scenario["agent_input"],
            registry=registry,
            decision_provider=fake_decision_provider,
            candidate_generator=fake_candidate_generator,
        )

        assert result.promoted_any
        assert result.initial_version_id == "rs_strategy_v1"
        assert result.final_version_id != result.initial_version_id
        assert registry.get_active().version_id == result.final_version_id
        assert len(result.rounds) == 1

        improvement_round = result.rounds[0]
        assert improvement_round.promoted
        assert improvement_round.incumbent_dev.success_rate == 0
        assert (
            improvement_round.candidate_holdout is not None
            and improvement_round.candidate_holdout.success_rate == 1
        )

        promoted, reason = promotion_decision(
            incumbent_dev=improvement_round.candidate_dev_evaluations[0],
            candidate_dev=improvement_round.candidate_dev_evaluations[0],
            incumbent_holdout=improvement_round.candidate_holdout,
            candidate_holdout=improvement_round.candidate_holdout,
            config=config,
        )
        assert not promoted
        assert "success_improved" in reason

        active = registry.get_active()
        early_stop_result = run_strategy_episode(
            strategy=active,
            incident=scenario["agent_input"],
            horizon=20,
            split="holdout",
            episode_index=1,
            decision_provider=early_stop_provider,
        )
        assert not early_stop_result.success
        assert early_stop_result.steps_completed < 20
        assert all(
            "case_id" not in step.observation
            for step in early_stop_result.trajectory
        )

    print("受控自我改进、holdout 晋级和回滚门控测试通过。")


if __name__ == "__main__":
    main()
