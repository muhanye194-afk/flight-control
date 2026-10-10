from typing import Any, Dict, List, Optional

from scenario_registry import get_active_incident


def load_incident() -> Dict[str, Any]:
    return get_active_incident()


def get_metrics() -> Dict[str, Any]:
    return load_incident()["metrics"]


def search_logs(keyword: Optional[str] = None) -> List[str]:
    logs = load_incident()["logs"]

    if keyword is None:
        return logs

    return [log for log in logs if keyword.lower() in log.lower()]


def get_recent_changes() -> List[Dict[str, str]]:
    return load_incident()["recent_changes"]


def get_traces() -> List[Dict[str, Any]]:
    return load_incident()["traces"]