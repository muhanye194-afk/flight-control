import json
from typing import Any, Dict, List

from rag.schemas import RetrievalResult

SYSTEM_PROMPT = """
You are the Incident Commander for a production payment system.

Your job is to investigate incidents using only the supplied live evidence
and retrieved internal knowledge.

Rules:
1. Separate observed facts from hypotheses.
2. Every root-cause claim must cite one or more retrieved sources.
3. If the evidence is insufficient, use status "needs_more_evidence".
4. Never claim that an action was executed.
5. Any production-changing action must require human approval.
6. Return valid JSON only. Follow the InvestigationReport structure exactly.
"""


def build_evidence_pack(
    incident: Dict[str, Any],
    rag_results: List[RetrievalResult]
) -> Dict[str, Any]:
    retrieved_knowledge = [
        {
            "citation": f"{result.chunk.source}#{result.chunk.section}",
            "title": result.chunk.title,
            "section": result.chunk.section,
            "content": result.chunk.content,
            "rrf_score": round(result.rrf_score, 5)
        }
        for result in rag_results
    ]

    return {
        "live_incident": incident,
        "retrieved_knowledge": retrieved_knowledge
    }


def build_investigation_messages(
    incident: Dict[str, Any],
    rag_results: List[RetrievalResult]
) -> List[Dict[str, str]]:
    evidence_pack = build_evidence_pack(incident, rag_results)

    user_prompt = (
        "Investigate the following payment incident. "
        "Use only this evidence pack.\n\n"
        + json.dumps(evidence_pack, ensure_ascii=False, indent=2)
    )

    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]