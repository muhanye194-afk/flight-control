import os
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient
from openai import RateLimitError

from main import app


client = TestClient(app)


def main() -> None:
    scenarios_response = client.get("/api/scenarios")
    assert scenarios_response.status_code == 200

    scenarios_body = scenarios_response.json()
    assert len(scenarios_body["scenarios"]) == 4

    config_response = client.get("/api/config")
    assert config_response.status_code == 200
    config_body = config_response.json()
    assert config_body["model"]
    assert "OPENAI_API_KEY" not in config_body
    assert "self_improvement_available" in config_body

    dashboard_response = client.get("/dashboard/")
    assert dashboard_response.status_code == 200
    assert "Flight Control" in dashboard_response.text

    activate_response = client.post(
        "/api/scenarios/video_edge_routing/activate"
    )
    assert activate_response.status_code == 200

    incident_response = client.get("/api/incidents/active")
    assert incident_response.status_code == 200
    assert incident_response.json()["service"] == "edge-routing-service"

    activate_rs_response = client.post(
        "/api/scenarios/recommender_shilling_attack/activate"
    )
    assert activate_rs_response.status_code == 200

    long_horizon_response = client.post(
        "/api/recommender-safety/active/run",
        json={"horizon": 10, "inject_stale_evidence": True},
    )
    assert long_horizon_response.status_code == 200
    long_horizon_body = long_horizon_response.json()
    assert len(long_horizon_body["reasoning_steps"]) == 10
    assert long_horizon_body["reliability_metrics"][
        "recovery_success"
    ]

    benchmark_response = client.post(
        "/api/recommender-safety/benchmark",
        json={"horizons": [10, 20, 50], "episodes": 10, "seed": 7},
    )
    assert benchmark_response.status_code == 200
    assert len(benchmark_response.json()["rows"]) == 6

    strategies_response = client.get(
        "/api/self-improvement/strategies"
    )
    assert strategies_response.status_code == 200
    strategies_body = strategies_response.json()
    assert strategies_body["active_version_id"]
    assert not strategies_body["source_code_mutation_allowed"]

    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        improvement_response = client.post(
            "/api/self-improvement/run",
            json={"horizon": 10},
        )
    assert improvement_response.status_code == 400
    assert "real LLM" in improvement_response.json()["detail"]

    missing_run_response = client.get("/api/investigations/not_found")
    assert missing_run_response.status_code == 404

    rate_limit_error = RateLimitError(
        "credit limit reached",
        response=httpx.Response(
            429,
            request=httpx.Request(
                "POST",
                "https://api.openai.com/v1/responses",
            ),
        ),
        body=None,
    )

    with patch(
        "main.execute_active_investigation",
        new=AsyncMock(side_effect=rate_limit_error),
    ), patch("main.logger.warning"):
        rate_limit_response = client.post(
            "/api/investigations/active/run"
        )

    assert rate_limit_response.status_code == 429
    assert "billing" in rate_limit_response.json()["detail"].lower()

    print("FastAPI API 冒烟测试通过。")


if __name__ == "__main__":
    main()
