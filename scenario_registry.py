import copy
import json
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent
SCENARIOS_DIR = BASE_DIR / "scenarios"

_active_scenario_id = "payment_connection_pool"


def load_all_scenarios() -> Dict[str, Dict[str, Any]]:
    scenarios = {}

    for file_path in SCENARIOS_DIR.glob("*.json"):
        with file_path.open(encoding="utf-8") as file:
            scenario = json.load(file)

        scenario_id = scenario["scenario_id"]
        scenarios[scenario_id] = scenario

    return scenarios


def list_scenarios() -> List[Dict[str, str]]:
    scenarios = load_all_scenarios()

    return [
        {
            "scenario_id": scenario["scenario_id"],
            "title": scenario["title"],
            "domain": scenario["domain"],
            "severity": scenario["severity"]
        }
        for scenario in scenarios.values()
    ]


def get_scenario(scenario_id: str) -> Dict[str, Any]:
    scenarios = load_all_scenarios()

    if scenario_id not in scenarios:
        raise KeyError(f"未知场景：{scenario_id}")

    return copy.deepcopy(scenarios[scenario_id])


def get_active_scenario() -> Dict[str, Any]:
    return get_scenario(_active_scenario_id)


def activate_scenario(scenario_id: str) -> Dict[str, Any]:
    global _active_scenario_id

    get_scenario(scenario_id)
    _active_scenario_id = scenario_id

    return get_active_scenario()


def get_active_incident() -> Dict[str, Any]:
    scenario = get_active_scenario()

    return scenario["agent_input"]


def get_active_ground_truth() -> Dict[str, Any]:
    scenario = get_active_scenario()

    return scenario["ground_truth"]

def get_active_scenario_summary() -> Dict[str, str]:
    scenario = get_active_scenario()

    return {
        "scenario_id": scenario["scenario_id"],
        "title": scenario["title"],
        "domain": scenario["domain"],
        "severity": scenario["severity"]
    }