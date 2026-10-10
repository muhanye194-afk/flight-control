from typing import Any, Dict, List, Optional

from agent.contracts import AgentFinding, AgentResult, EvidenceItem


def describe_metric_anomaly(
    metric_name: str,
    value: Any,
    metrics: Dict[str, Any]
) -> Optional[str]:
    if not isinstance(value, (int, float)):
        return None

    if "success_rate_percent" in metric_name and value < 95:
        return f"{metric_name}={value}，低于 95% 安全阈值"

    if "error_rate_percent" in metric_name and value > 5:
        return f"{metric_name}={value}，高于 5% 安全阈值"

    if "p95_latency_ms" in metric_name and value > 1000:
        return f"{metric_name}={value}ms，超过 1000ms 延迟阈值"

    if "hit_rate_percent" in metric_name and value < 80:
        return f"{metric_name}={value}，低于 80% 缓存命中阈值"

    if "cpu_percent" in metric_name and value > 85:
        return f"{metric_name}={value}，超过 85% CPU 阈值"

    if "health_percent" in metric_name and value < 95:
        return f"{metric_name}={value}，低于 95% 健康度阈值"

    if metric_name.endswith("_active_connections"):
        limit_name = metric_name.replace(
            "_active_connections",
            "_connection_limit"
        )
        limit = metrics.get(limit_name)

        if isinstance(limit, (int, float)) and value >= limit:
            return (
                f"{metric_name}={value}，"
                f"已达到连接上限 {limit_name}={limit}"
            )

    return None


def run_observability_agent(
    incident: Dict[str, Any]
) -> AgentResult:
    metrics = incident.get("metrics", {})
    logs = incident.get("logs", [])
    traces = incident.get("traces", [])

    evidence: List[EvidenceItem] = []

    for metric_name, value in metrics.items():
        observation = describe_metric_anomaly(
            metric_name,
            value,
            metrics
        )

        if observation is not None:
            evidence.append(
                EvidenceItem(
                    evidence_id=f"obs_metric_{metric_name}",
                    source_type="metric",
                    source_ref=f"metrics.{metric_name}",
                    observation=observation,
                    source_reliability=0.90
                )
            )

    for log_index, log in enumerate(logs):
        lowered_log = log.lower()

        if "error" in lowered_log:
            evidence.append(
                EvidenceItem(
                    evidence_id=f"obs_log_{log_index}",
                    source_type="log",
                    source_ref=f"logs[{log_index}]",
                    observation=log,
                    source_reliability=0.80
                )
            )

        elif "warn" in lowered_log:
            evidence.append(
                EvidenceItem(
                    evidence_id=f"obs_log_{log_index}",
                    source_type="log",
                    source_ref=f"logs[{log_index}]",
                    observation=log,
                    source_reliability=0.65
                )
            )

    for trace in traces:
        trace_id = trace.get("trace_id", "unknown_trace")

        for span_index, span in enumerate(trace.get("spans", [])):
            if span.get("status") != "error":
                continue

            service = span.get("service", "unknown_service")
            operation = span.get("operation", "unknown_operation")
            error = span.get("error", "unknown error")

            evidence.append(
                EvidenceItem(
                    evidence_id=(
                        f"obs_trace_{trace_id}_{span_index}"
                    ),
                    source_type="trace",
                    source_ref=f"{trace_id}.spans[{span_index}]",
                    observation=(
                        f"{service}.{operation} 失败：{error}"
                    ),
                    source_reliability=0.95
                )
            )

    evidence_ids = [
        item.evidence_id
        for item in evidence
    ]

    if evidence:
        status = "completed"
        summary = (
            f"已检查 {len(metrics)} 个指标、"
            f"{len(logs)} 条日志和 {len(traces)} 条链路，"
            f"提取到 {len(evidence)} 张异常证据卡。"
        )
    else:
        status = "needs_more_evidence"
        summary = "未发现足够的异常信号，需要补充监控数据。"

    finding = AgentFinding(
        agent_name="observability_agent",
        status=status,
        summary=summary,
        evidence_ids=evidence_ids
    )

    return AgentResult(
        agent_name="observability_agent",
        finding=finding,
        evidence=evidence,
        tool_trace=[
            {
                "tool": "get_metrics",
                "status": "completed"
            },
            {
                "tool": "search_logs",
                "status": "completed"
            },
            {
                "tool": "get_traces",
                "status": "completed"
            }
        ]
    )