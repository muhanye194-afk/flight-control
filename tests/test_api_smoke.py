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
    assert len(scenarios_body["scenarios"]) == 3

    config_response = client.get("/api/config")
    assert config_response.status_code == 200
    config_body = config_response.json()
    assert config_body["model"]
    assert "OPENAI_API_KEY" not in config_body

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
