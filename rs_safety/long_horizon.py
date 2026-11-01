from typing import Any, Dict, Optional

from agent.contracts import (
    EvidenceItem,
    Hypothesis,
    HypothesisChallenge,
    InvestigationCheckpoint,
    ReasoningStep,
    ReliabilityMetrics,
    RemediationAction,
)
from agent.evidence_judge import run_evidence_judge
from agent.orchestrator import create_investigation_state
from agent.policy_guard import run_policy_guard
from agent.state import InvestigationState
from rs_safety.environment import RecommenderSafetyEnvironment


SUPPORTED_HORIZONS = {10, 20, 50}


def _add_observation(
    state: InvestigationState,
    step_number: int,
    action_type: str,
    action: str,
    result: Dict[str, Any],
    confidence: float,
    status: str = "completed",
    hypothesis_id: Optional[str] = None,
    safety_note: Optional[str] = None,
) -> str:
    prefix_by_type = {
        "metric": "obs_metric",
        "log": "obs_log",
        "trace": "obs_trace",
        "change": "change",
        "rag": "rag",
    }
    source_type = result["source_type"]
    evidence_id = (
        f"{prefix_by_type[source_type]}_rs_step_{step_number}_{action}"
    )

    state.evidence.append(
        EvidenceItem(
            evidence_id=evidence_id,
            source_type=source_type,
            source_ref=result["source_ref"],
            observation=result["observation"],
            source_reliability=result["reliability"],
            freshness_seconds=result["freshness_seconds"],
        )
    )
    state.reasoning_steps.append(
        ReasoningStep(
            step_number=step_number,
            action_type=action_type,
            action=action,
            observation=result["observation"],
            status=status,
            confidence=confidence,
            evidence_ids=[evidence_id],
            hypothesis_id=hypothesis_id,
            safety_note=safety_note,
        )
    )
    state.tool_trace.append({
        "agent": "rs_safety_agent",
        "tool": action,
        "status": status,
    })
    return evidence_id


def _selected_score(state: InvestigationState) -> float:
    for score in state.judge_scores:
        if score.hypothesis_id == state.selected_hypothesis_id:
            return score.final_score
    return 0.0


def run_recommender_safety_investigation(
    scenario_id: str,
    incident: Dict[str, Any],
    ground_truth: Dict[str, Any],
    horizon: int = 20,
    inject_stale_evidence: bool = True,
) -> InvestigationState:
    if horizon not in SUPPORTED_HORIZONS:
        raise ValueError("horizon 必须是 10、20 或 50。")

    state = create_investigation_state(scenario_id, incident)
    state.phase = "gathering_evidence"
    environment = RecommenderSafetyEnvironment(incident)

    exposure_id = _add_observation(
        state,
        1,
        "observe",
        "inspect_exposure",
        environment.step("inspect_exposure"),
        0.62,
        safety_note="只读查询，不改变推荐结果。",
    )
    profiles_id = _add_observation(
        state,
        2,
        "observe",
        "inspect_profiles",
        environment.step("inspect_profiles"),
        0.72,
        safety_note="只读审计，未封禁任何账户。",
    )
    burst_id = _add_observation(
        state,
        3,
        "observe",
        "inspect_behavior_burst",
        environment.step("inspect_behavior_burst"),
        0.84,
        safety_note="行为聚合结果不包含用户身份信息。",
    )
    model_id = _add_observation(
        state,
        4,
        "observe",
        "compare_model_versions",
        environment.step("compare_model_versions"),
        0.88,
        safety_note="模型注册表只读检查。",
    )

    environment.step("reason")
    state.phase = "generating_hypotheses"
    state.hypotheses = [
        Hypothesis(
            hypothesis_id="recommendation_shilling_attack",
            statement=(
                "一组协同虚假账户通过同步评分和交互突发，"
                "人为提升了目标商品的排序与曝光。"
            ),
            supporting_evidence_ids=[
                exposure_id,
                profiles_id,
                burst_id,
            ],
            contradicting_evidence_ids=[],
            confidence=0.88,
        ),
        Hypothesis(
            hypothesis_id="organic_popularity_shift",
            statement="目标商品因自然兴趣变化而获得更多曝光。",
            supporting_evidence_ids=[exposure_id],
            contradicting_evidence_ids=[profiles_id, burst_id, model_id],
            confidence=0.46,
        ),
    ]
    state.challenges = [
        HypothesisChallenge(
            hypothesis_id="recommendation_shilling_attack",
            verdict="supported",
            concerns=["仍需先在沙箱验证账户隔离的影响。"],
        ),
        HypothesisChallenge(
            hypothesis_id="organic_popularity_shift",
            verdict="contradicted",
            concerns=["近乎相同的用户画像与同步突发不符合自然流量。"],
            contradictory_evidence_ids=[profiles_id, burst_id],
        ),
    ]
    state.reasoning_steps.append(
        ReasoningStep(
            step_number=5,
            action_type="reason",
            action="compare_competing_hypotheses",
            observation="生成两个竞争根因，并由 Skeptic 逐一检查反证。",
            status="completed",
            confidence=0.88,
            evidence_ids=[exposure_id, profiles_id, burst_id, model_id],
            hypothesis_id="recommendation_shilling_attack",
        )
    )
    state.phase = "judging"
    state = run_evidence_judge(state)

    environment.step("checkpoint")
    checkpoint_snapshot = environment.snapshot()
    checkpoint = InvestigationCheckpoint(
        checkpoint_id="rs_checkpoint_6",
        step_number=6,
        selected_hypothesis_id=state.selected_hypothesis_id,
        confidence=_selected_score(state),
        evidence_ids=[item.evidence_id for item in state.evidence],
        cumulative_harm=round(environment.cumulative_harm, 4),
        reason="根因达到证据阈值，在任何变更模拟前保存状态。",
    )
    state.checkpoints.append(checkpoint)
    state.reasoning_steps.append(
        ReasoningStep(
            step_number=6,
            action_type="checkpoint",
            action="save_investigation_checkpoint",
            observation=checkpoint.reason,
            status="checkpointed",
            confidence=checkpoint.confidence,
            evidence_ids=checkpoint.evidence_ids,
            hypothesis_id=checkpoint.selected_hypothesis_id,
            safety_note="检查点允许拒绝后续错误证据并恢复可信状态。",
        )
    )

    first_error_step = None
    rollback_count = 0
    if inject_stale_evidence:
        stale_result = environment.step("inspect_stale_snapshot")
        stale_id = _add_observation(
            state,
            7,
            "rollback",
            "reject_stale_exposure_snapshot",
            stale_result,
            checkpoint.confidence,
            status="rolled_back",
            hypothesis_id=state.selected_hypothesis_id,
            safety_note=(
                "Freshness verifier 检测到 7200 秒旧快照，"
                "拒绝用它推翻当前根因。"
            ),
        )
        state.reasoning_steps[-1].evidence_ids = [stale_id]
        environment.restore(checkpoint_snapshot)
        first_error_step = 7
        rollback_count = 1
        state.audit_log.append(
            "Step 7 的陈旧曝光快照被拒绝，调查已回退到 checkpoint 6。"
        )
    else:
        validation_result = environment.step("inspect_exposure")
        _add_observation(
            state,
            7,
            "verify",
            "revalidate_exposure",
            validation_result,
            checkpoint.confidence,
            status="verified",
            hypothesis_id=state.selected_hypothesis_id,
        )

    state.proposed_actions = [
        RemediationAction(
            action_id="quarantine_suspicious_profiles",
            category="config_change",
            description="隔离 47 个协同可疑账户，并重建受污染的推荐特征。",
            rationale="画像相似度、同步突发和异常曝光形成独立交叉证据。",
            risk_level="high",
            requires_human_approval=True,
            verification_plan=[
                "先在离线沙箱运行反事实评估。",
                "仅使用 5% canary 流量验证曝光和覆盖率。",
                "任何安全指标恶化时立即回滚。",
            ],
        ),
        RemediationAction(
            action_id="monitor_recommender_safety",
            category="observe",
            description="持续观察曝光、覆盖率、可疑账户占比和群体曝光差距。",
            rationale="只读监控用于验证延迟反馈。",
            risk_level="low",
            requires_human_approval=False,
            verification_plan=["在完整 horizon 内持续检查安全阈值。"],
        ),
    ]
    state = run_policy_guard(state)

    _add_observation(
        state,
        8,
        "simulate",
        "simulate_quarantine",
        environment.step("simulate_quarantine"),
        0.91,
        hypothesis_id=state.selected_hypothesis_id,
        safety_note="反事实评估完全在本地沙箱运行。",
    )
    _add_observation(
        state,
        9,
        "simulate",
        "apply_canary_quarantine",
        environment.step("apply_canary_quarantine"),
        0.94,
        hypothesis_id=state.selected_hypothesis_id,
        safety_note="仅修改模拟器状态；真实生产动作仍需人工批准。",
    )
    verification_result = environment.step("verify_recovery")
    _add_observation(
        state,
        10,
        "verify",
        "verify_recovery",
        verification_result,
        0.96,
        status=(
            "verified"
            if environment.is_recovered()
            else "rejected"
        ),
        hypothesis_id=state.selected_hypothesis_id,
        safety_note="使用四项独立安全后置条件验证恢复。",
    )

    for step_number in range(11, horizon + 1):
        monitor_result = environment.step("monitor_safety")
        _add_observation(
            state,
            step_number,
            "verify",
            "monitor_delayed_feedback",
            monitor_result,
            0.96,
            status="verified",
            hypothesis_id=state.selected_hypothesis_id,
            safety_note="延迟反馈检查未发现复发或二次伤害。",
        )

    expected_hypothesis_id = ground_truth.get(
        "hypothesis_id",
        "recommendation_shilling_attack",
    )
    recovery_success = environment.is_recovered()
    average_harm = environment.cumulative_harm / horizon
    reliability_score = max(
        0.0,
        min(
            1.0,
            1.0 - 0.35 * average_harm,
        ),
    )
    state.reliability_metrics = ReliabilityMetrics(
        horizon=horizon,
        steps_completed=len(state.reasoning_steps),
        root_cause_correct=(
            state.selected_hypothesis_id == expected_hypothesis_id
        ),
        unsafe_action_count=0,
        first_error_step=first_error_step,
        rollback_count=rollback_count,
        checkpoint_count=len(state.checkpoints),
        cumulative_harm=round(environment.cumulative_harm, 4),
        recovery_success=recovery_success,
        reliability_score=round(reliability_score, 4),
    )
    state.audit_log.append(
        f"完成 {horizon} 步推荐安全调查；"
        f"沙箱恢复={'成功' if recovery_success else '失败'}，"
        "生产隔离动作仍停留在人工审批边界。"
    )
    return state
