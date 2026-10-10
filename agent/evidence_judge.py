from typing import Dict, List, Optional

from agent.contracts import (
    EvidenceItem,
    Hypothesis,
    HypothesisScore,
)
from agent.state import InvestigationState


SOURCE_TYPE_WEIGHTS: Dict[str, float] = {
    "trace": 1.00,
    "metric": 0.90,
    "change": 0.85,
    "rag": 0.80,
    "log": 0.75
}

VERDICT_PENALTIES: Dict[str, float] = {
    "supported": 0.00,
    "weak": 0.15,
    "insufficient_evidence": 0.25,
    "contradicted": 0.45
}


def clamp_score(value: float) -> float:
    return max(0.0, min(value, 1.0))


def get_producer_agent(
    evidence_id: str
) -> str:
    if evidence_id.startswith("obs_"):
        return "observability_agent"

    if evidence_id.startswith("change_"):
        return "change_agent"

    if evidence_id.startswith("rag_"):
        return "knowledge_agent"

    return "unknown_agent"


def get_freshness_factor(
    freshness_seconds: Optional[int]
) -> float:
    if freshness_seconds is None:
        return 1.0

    return max(
        0.40,
        1 - freshness_seconds / 7200
    )


def calculate_evidence_quality(
    item: EvidenceItem,
    state: InvestigationState
) -> float:
    source_weight = SOURCE_TYPE_WEIGHTS.get(
        item.source_type,
        0.60
    )

    producer_agent = get_producer_agent(
        item.evidence_id
    )

    producer_reliability = state.agent_reliability.get(
        producer_agent,
        0.60
    )

    freshness_factor = get_freshness_factor(
        item.freshness_seconds
    )

    return (
        item.source_reliability
        * source_weight
        * producer_reliability
        * freshness_factor
    )


def get_diversity_bonus(
    evidence: List[EvidenceItem]
) -> float:
    source_types = {
        item.source_type
        for item in evidence
    }

    if len(source_types) >= 3:
        return 0.05

    if len(source_types) == 2:
        return 0.03

    return 0.00


def score_hypothesis(
    hypothesis: Hypothesis,
    state: InvestigationState,
    evidence_by_id: Dict[str, EvidenceItem]
) -> HypothesisScore:
    supporting_items = [
        evidence_by_id[evidence_id]
        for evidence_id in hypothesis.supporting_evidence_ids
        if evidence_id in evidence_by_id
    ]

    missing_support_ids = [
        evidence_id
        for evidence_id in hypothesis.supporting_evidence_ids
        if evidence_id not in evidence_by_id
    ]

    evidence_qualities = [
        calculate_evidence_quality(
            item,
            state
        )
        for item in supporting_items
    ]

    evidence_support_score = min(
        sum(evidence_qualities) / 2.5,
        1.0
    )

    diversity_bonus = get_diversity_bonus(
        supporting_items
    )

    related_challenges = [
        challenge
        for challenge in state.challenges
        if challenge.hypothesis_id
        == hypothesis.hypothesis_id
    ]

    challenge_penalty = 0.0

    for challenge in related_challenges:
        challenge_penalty += VERDICT_PENALTIES.get(
            challenge.verdict,
            0.25
        )

        contradictory_items = [
            evidence_by_id[evidence_id]
            for evidence_id
            in challenge.contradictory_evidence_ids
            if evidence_id in evidence_by_id
        ]

        if contradictory_items:
            contradiction_quality = sum(
                calculate_evidence_quality(
                    item,
                    state
                )
                for item in contradictory_items
            ) / len(contradictory_items)

            challenge_penalty += (
                contradiction_quality * 0.15
            )

    challenge_penalty = min(
        challenge_penalty,
        1.0
    )

    final_score = clamp_score(
        0.20 * hypothesis.confidence
        + 0.70 * evidence_support_score
        + diversity_bonus
        - 0.50 * challenge_penalty
    )

    rationale = [
        (
            "LLM 初始置信度："
            f"{hypothesis.confidence:.2f}"
        ),
        (
            "有效支持证据："
            f"{len(supporting_items)} 张"
        ),
        (
            "加权证据支持分："
            f"{evidence_support_score:.2f}"
        ),
        (
            "跨来源证据奖励："
            f"{diversity_bonus:.2f}"
        ),
        (
            "Skeptic 反驳惩罚："
            f"{challenge_penalty:.2f}"
        )
    ]

    if missing_support_ids:
        rationale.append(
            "以下引用的证据 ID 不存在，"
            f"已忽略：{', '.join(missing_support_ids)}"
        )

    return HypothesisScore(
        hypothesis_id=hypothesis.hypothesis_id,
        prior_confidence=round(
            hypothesis.confidence,
            4
        ),
        evidence_support_score=round(
            evidence_support_score,
            4
        ),
        diversity_bonus=round(
            diversity_bonus,
            4
        ),
        challenge_penalty=round(
            challenge_penalty,
            4
        ),
        final_score=round(final_score, 4),
        supporting_evidence_count=len(
            supporting_items
        ),
        rationale=rationale
    )


def run_evidence_judge(
    state: InvestigationState
) -> InvestigationState:
    if not state.hypotheses:
        state.phase = "blocked"
        state.audit_log.append(
            "Evidence Judge 无法运行：没有根因假设。"
        )

        return state

    evidence_by_id = {
        item.evidence_id: item
        for item in state.evidence
    }

    scores = [
        score_hypothesis(
            hypothesis,
            state,
            evidence_by_id
        )
        for hypothesis in state.hypotheses
    ]

    state.judge_scores = sorted(
        scores,
        key=lambda score: score.final_score,
        reverse=True
    )

    best_score = state.judge_scores[0]

    if best_score.final_score < 0.45:
        state.phase = "blocked"
        state.audit_log.append(
            "Evidence Judge 阻止下结论："
            "最高假设分数低于 0.45。"
        )

        return state

    state.selected_hypothesis_id = (
        best_score.hypothesis_id
    )

    state.phase = "awaiting_approval"

    state.audit_log.append(
        "Evidence Judge 选择了假设 "
        f"{best_score.hypothesis_id}，"
        f"最终分数为 {best_score.final_score:.2f}。"
    )

    return state
