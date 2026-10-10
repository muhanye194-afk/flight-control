import asyncio
from typing import Dict
from uuid import uuid4

from agent.change_agent import run_change_agent
from agent.contracts import AgentResult
from agent.evidence_judge import run_evidence_judge
from agent.hypothesis_agent import run_hypothesis_agent
from agent.knowledge_agent import run_knowledge_agent
from agent.observability_agent import run_observability_agent
from agent.policy_guard import run_policy_guard
from agent.remediation_agent import run_remediation_planner
from agent.skeptic_agent import run_skeptic_agent
from agent.state import InvestigationState


AGENT_BASE_RELIABILITY: Dict[str, float] = {
    "observability_agent": 0.90,
    "change_agent": 0.75,
    "knowledge_agent": 0.85,
    "hypothesis_agent": 0.80,
    "skeptic_agent": 0.85
}


def create_investigation_state(
    scenario_id: str,
    incident: dict
) -> InvestigationState:
    return InvestigationState(
        run_id=str(uuid4()),
        scenario_id=scenario_id,
        incident=incident,
        agent_reliability=AGENT_BASE_RELIABILITY.copy()
    )


def merge_agent_result(
    state: InvestigationState,
    result: AgentResult
) -> None:
    state.evidence.extend(result.evidence)
    state.findings.append(result.finding)
    state.hypotheses.extend(
        result.finding.hypotheses
    )
    state.challenges.extend(result.challenges)

    for tool_call in result.tool_trace:
        state.tool_trace.append({
            "agent": result.agent_name,
            **tool_call
        })

    state.audit_log.append(
        f"{result.agent_name} 完成："
        f"{result.finding.status}"
    )


async def run_specialist_agents(
    state: InvestigationState,
    domain: str
) -> InvestigationState:
    state.phase = "gathering_evidence"

    tasks = [
        asyncio.to_thread(
            run_observability_agent,
            state.incident
        ),
        asyncio.to_thread(
            run_change_agent,
            state.incident
        ),
        asyncio.to_thread(
            run_knowledge_agent,
            state.incident,
            domain
        )
    ]

    results = await asyncio.gather(*tasks)

    for result in results:
        merge_agent_result(state, result)

    state.phase = "generating_hypotheses"

    state.audit_log.append(
        "Incident Commander 已并行汇总全部专业 Agent 的结果。"
    )

    return state


async def run_investigation(
    state: InvestigationState,
    domain: str
) -> InvestigationState:
    state = await run_specialist_agents(
        state,
        domain
    )

    hypothesis_result = await asyncio.to_thread(
        run_hypothesis_agent,
        state.incident,
        state.evidence
    )

    merge_agent_result(
        state,
        hypothesis_result
    )

    state.phase = "challenging"

    skeptic_result = await asyncio.to_thread(
        run_skeptic_agent,
        state.incident,
        state.evidence,
        state.hypotheses
    )

    merge_agent_result(
        state,
        skeptic_result
    )

    state.phase = "judging"

    state = run_evidence_judge(state)

    if state.selected_hypothesis_id is None:
        state.audit_log.append(
            "没有假设达到安全阈值，停止修复规划。"
        )

        return state

    state.proposed_actions = await asyncio.to_thread(
        run_remediation_planner,
        state
    )

    state.audit_log.append(
        "Remediation Planner 已生成修复方案，"
        "交由 Policy Guard 审查。"
    )

    state = run_policy_guard(state)

    return state