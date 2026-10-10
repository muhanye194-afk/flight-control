from functools import lru_cache
from typing import Any, Dict, List, Optional

from agent.contracts import (
    AgentFinding,
    AgentResult,
    EvidenceItem,
)
from rag.retriever import HybridRetriever, build_retriever


@lru_cache(maxsize=1)
def get_retriever() -> HybridRetriever:
    return build_retriever()


def build_knowledge_query(
    incident: Dict[str, Any],
    domain: Optional[str] = None
) -> str:
    logs = incident.get("logs", [])
    changes = incident.get("recent_changes", [])
    traces = incident.get("traces", [])

    trace_errors = [
        span.get("error", "")
        for trace in traces
        for span in trace.get("spans", [])
        if span.get("status") == "error"
    ]

    change_messages = [
        change.get("message", "")
        for change in changes
    ]

    alert = incident.get("alert", {})

    return " ".join([
        domain or "",
        incident.get("service", ""),
        alert.get("title", ""),
        *logs,
        *change_messages,
        *trace_errors
    ])


def get_document_reliability(
    document_type: str
) -> float:
    reliability_by_type = {
        "runbooks": 0.88,
        "postmortems": 0.92,
        "architecture": 0.82,
        "policies": 0.95
    }

    return reliability_by_type.get(document_type, 0.70)


def run_knowledge_agent(
    incident: Dict[str, Any],
    domain: Optional[str] = None,
    top_k: int = 3
) -> AgentResult:
    query = build_knowledge_query(
        incident,
        domain
    )

    retriever = get_retriever()

    results = retriever.search(
        query,
        top_k=top_k,
        domain=domain
    )

    evidence: List[EvidenceItem] = []

    for index, result in enumerate(results, start=1):
        chunk = result.chunk
        evidence_id = f"rag_{index}_{chunk.chunk_id}"

        excerpt = chunk.content.replace("\n", " ")[:400]

        evidence.append(
            EvidenceItem(
                evidence_id=evidence_id,
                source_type="rag",
                source_ref=f"{chunk.source}#{chunk.section}",
                observation=(
                    f"《{chunk.title}》 / {chunk.section}："
                    f"{excerpt} "
                    f"(RRF 检索分数：{result.rrf_score:.5f})"
                ),
                source_reliability=get_document_reliability(
                    chunk.document_type
                )
            )
        )

    evidence_ids = [
        item.evidence_id
        for item in evidence
    ]

    if evidence:
        status = "completed"
        summary = (
            f"Hybrid RAG 在 {domain or '全领域'} 知识库中"
            f"检索到 {len(evidence)} 张知识证据卡，"
            "每张卡都保留了文档出处与段落位置。"
        )
    else:
        status = "needs_more_evidence"
        summary = "知识库未检索到相关资料，需要补充 Runbook 或历史复盘。"

    finding = AgentFinding(
        agent_name="knowledge_agent",
        status=status,
        summary=summary,
        evidence_ids=evidence_ids
    )

    return AgentResult(
        agent_name="knowledge_agent",
        finding=finding,
        evidence=evidence,
        tool_trace=[
            {
                "tool": "hybrid_rag_search",
                "status": "completed"
            },
            {
                "tool": "domain_filter",
                "status": domain or "not_applied"
            }
        ]
    )