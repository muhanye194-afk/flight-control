from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from agent.contracts import (
    AgentFinding,
    AgentResult,
    EvidenceItem,
    Hypothesis,
)


def parse_timestamp(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except (AttributeError, ValueError):
        return None


def assess_temporal_correlation(
    deployed_at: str,
    alert_started_at: str
) -> Tuple[float, str]:
    deployed_time = parse_timestamp(deployed_at)
    alert_time = parse_timestamp(alert_started_at)

    if deployed_time is None or alert_time is None:
        return 0.60, "无法可靠计算发布时间与告警时间差"

    delta_seconds = (
        alert_time - deployed_time
    ).total_seconds()

    if 0 <= delta_seconds <= 900:
        return 0.95, "发布发生在告警前 15 分钟内"

    if 0 <= delta_seconds <= 3600:
        return 0.80, "发布发生在告警前 1 小时内"

    if delta_seconds > 3600:
        return 0.55, "发布距离告警较久，时间相关性较弱"

    return 0.35, "发布发生在告警后，不能解释本次故障"


def run_change_agent(
    incident: Dict[str, Any]
) -> AgentResult:
    changes = incident.get("recent_changes", [])
    alert = incident.get("alert", {})
    alert_started_at = alert.get("started_at", "")

    evidence: List[EvidenceItem] = []
    hypotheses: List[Hypothesis] = []

    for change in changes:
        commit = change.get("commit", "unknown_commit")
        message = change.get("message", "无变更说明")
        deployed_at = change.get("deployed_at", "")

        reliability, time_note = assess_temporal_correlation(
            deployed_at,
            alert_started_at
        )

        evidence_id = f"change_{commit}"

        evidence.append(
            EvidenceItem(
                evidence_id=evidence_id,
                source_type="change",
                source_ref=f"commit:{commit}",
                observation=(
                    f"变更 {commit}: {message}；{time_note}"
                ),
                source_reliability=reliability
            )
        )

        hypotheses.append(
            Hypothesis(
                hypothesis_id=f"hyp_change_{commit}",
                statement=(
                    f"变更 {commit}（{message}）"
                    "可能与本次故障存在时间相关性，"
                    "但仍需要指标、日志和链路证据验证因果关系。"
                ),
                supporting_evidence_ids=[evidence_id],
                confidence=round(reliability * 0.70, 2)
            )
        )

    evidence_ids = [
        item.evidence_id
        for item in evidence
    ]

    if evidence:
        status = "completed"
        summary = (
            f"检查到 {len(changes)} 次近期发布，"
            "已为每次发布计算与告警的时间相关性。"
        )
    else:
        status = "needs_more_evidence"
        summary = "没有近期发布记录，无法进行变更相关性分析。"

    finding = AgentFinding(
        agent_name="change_agent",
        status=status,
        summary=summary,
        evidence_ids=evidence_ids,
        hypotheses=hypotheses
    )

    return AgentResult(
        agent_name="change_agent",
        finding=finding,
        evidence=evidence,
        tool_trace=[
            {
                "tool": "get_recent_changes",
                "status": "completed"
            }
        ]
    )