import asyncio

from agent.orchestrator import (
    create_investigation_state,
    run_specialist_agents,
)
from scenario_registry import (
    activate_scenario,
    get_active_incident,
    get_active_scenario_summary,
)


SCENARIO_IDS = [
    "payment_connection_pool",
    "video_edge_routing",
    "feed_cache_cascade",
]


async def verify_scenario(scenario_id: str) -> None:
    activate_scenario(scenario_id)

    scenario = get_active_scenario_summary()
    incident = get_active_incident()

    state = create_investigation_state(
        scenario_id=scenario["scenario_id"],
        incident=incident,
    )

    result = await run_specialist_agents(
        state=state,
        domain=scenario["domain"],
    )

    agent_names = {finding.agent_name for finding in result.findings}

    assert result.phase == "generating_hypotheses"
    assert agent_names == {
        "observability_agent",
        "change_agent",
        "knowledge_agent",
    }
    assert len(result.evidence) > 0
    assert any(item.source_type == "rag" for item in result.evidence)

    print(
        f"✓ {scenario_id}: "
        f"{len(result.evidence)} 条证据，"
        f"{len(result.findings)} 个 Specialist Agent 正常工作"
    )


async def main() -> None:
    for scenario_id in SCENARIO_IDS:
        await verify_scenario(scenario_id)

    print("3 个场景的 Specialist Agent 回归测试全部通过。")


if __name__ == "__main__":
    asyncio.run(main())