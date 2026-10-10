from typing import Any, Dict

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


DEMO_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "payment_connection_pool": {
        "hypothesis_id": "database_session_leak",
        "statement": (
            "最近代码变更引入数据库 session 泄漏，"
            "导致连接池被耗尽并引发支付服务异常。"
        ),
        "rollback_description": "回滚与数据库 session 生命周期相关的最近变更。",
        "verification_plan": [
            "数据库连接池使用率下降到安全阈值。",
            "支付成功率恢复到正常基线。",
            "错误日志中不再出现 connection pool exhausted。",
        ],
    },
    "video_edge_routing": {
        "hypothesis_id": "routing_misconfiguration",
        "statement": (
            "最近发布修改了 APAC 源站路由权重，"
            "使边缘服务选择了不存在路由的源站。"
        ),
        "rollback_description": "回滚最近发布的 APAC 源站路由权重变更。",
        "verification_plan": [
            "APAC 播放启动成功率恢复到 95% 以上。",
            "APAC Edge P95 延迟恢复到 800ms 以下。",
            "route_not_found 日志停止增长。",
        ],
    },
    "feed_cache_cascade": {
        "hypothesis_id": "cache_key_compatibility_failure",
        "statement": (
            "缓存 Key 迁移破坏了新旧版本兼容性，"
            "造成缓存未命中风暴并将请求级联到数据库。"
        ),
        "rollback_description": "回滚缓存 Key 迁移并恢复新旧 Key 兼容读取。",
        "verification_plan": [
            "Feed 缓存命中率恢复到 85% 以上。",
            "Feed 错误率恢复到 2% 以下。",
            "数据库超时和 Redis 队列压力停止增长。",
        ],
    },
}


def evidence_id_by_type(state, source_type: str) -> str:
    for item in state.evidence:
        if item.source_type == source_type:
            return item.evidence_id

    raise ValueError(f"Offline Demo 缺少 {source_type} 类型证据。")


async def run_offline_demo(
    scenario_id: str,
    incident: Dict[str, Any],
    domain: str,
):
    if scenario_id not in DEMO_SCENARIOS:
        raise ValueError(f"没有为场景 {scenario_id} 配置 Offline Demo。")

    config = DEMO_SCENARIOS[scenario_id]

    state = create_investigation_state(
        scenario_id=scenario_id,
        incident=incident,
    )

    # 真实运行三个免费 Specialist Agent。
    state = await run_specialist_agents(
        state=state,
        domain=domain,
    )

    metric_id = evidence_id_by_type(state, "metric")
    trace_id = evidence_id_by_type(state, "trace")
    change_id = evidence_id_by_type(state, "change")
    rag_id = evidence_id_by_type(state, "rag")
    log_id = evidence_id_by_type(state, "log")

    primary_hypothesis_id = config["hypothesis_id"]
    alternative_hypothesis_id = f"{scenario_id}_alternative"
    state.hypotheses = [
        Hypothesis(
            hypothesis_id=primary_hypothesis_id,
            statement=config["statement"],
            supporting_evidence_ids=[
                metric_id,
                trace_id,
                change_id,
                rag_id,
            ],
            confidence=0.80,
        ),
        Hypothesis(
            hypothesis_id=alternative_hypothesis_id,
            statement="仅被少量日志支持、缺少交叉验证的竞争性假设。",
            supporting_evidence_ids=[log_id],
            confidence=0.60,
        ),
    ]

    state.challenges = [
        HypothesisChallenge(
            hypothesis_id=primary_hypothesis_id,
            verdict="supported",
            concerns=[],
            missing_evidence=[],
            contradictory_evidence_ids=[],
        ),
        HypothesisChallenge(
            hypothesis_id=alternative_hypothesis_id,
            verdict="contradicted",
            concerns=[
                "该假设缺少指标、变更和知识库的独立交叉支持。"
            ],
            missing_evidence=[
                "需要更多独立来源确认该竞争性假设。"
            ],
            contradictory_evidence_ids=[metric_id],
        ),
    ]

    state = run_evidence_judge(state)

    state.proposed_actions = [
        RemediationAction(
            action_id="rollback_suspected_change",
            category="rollback",
            description=config["rollback_description"],
            rationale=(
                "Evidence Judge 已选择主要根因，"
                "但回滚属于高风险生产变更。"
            ),
            risk_level="high",
            requires_human_approval=True,
            verification_plan=config["verification_plan"],
        ),
        RemediationAction(
            action_id="observe_recovery_metrics",
            category="observe",
            description="持续观察核心业务成功率、错误率和延迟。",
            rationale="只读操作，不改变生产状态。",
            risk_level="low",
            requires_human_approval=False,
            verification_plan=[
                "连续 10 分钟观察关键指标趋势。",
            ],
        ),
    ]

    state = run_policy_guard(state)

    state.audit_log.append(
        "Offline Demo 完成：Specialist Agent、Evidence Judge 和 Policy Guard 已真实运行；"
        "假设与 Skeptic 结论来自演示夹具，未调用付费 LLM。"
    )

    return state