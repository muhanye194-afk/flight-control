import logging
import os
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAIError,
    RateLimitError,
)
from pydantic import BaseModel

from agent.demo_mode import run_offline_demo
from agent.llm_client import MODEL_NAME
from agent.orchestrator import (
    create_investigation_state,
    run_investigation,
)
from agent.run_store import (
    approve_actions,
    get_run,
    save_run,
)
from incident_tools import load_incident
from scenario_registry import (
    activate_scenario,
    get_active_scenario_summary,
    list_scenarios,
)


BASE_DIR = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)


app = FastAPI(
    title="Flight Control API",
    description="Multi-Agent Reliability Operating System",
)

app.mount(
    "/dashboard",
    StaticFiles(directory=BASE_DIR / "dashboard", html=True),
    name="dashboard",
)


class ApprovalRequest(BaseModel):
    action_ids: List[str]
    approver: str


def format_investigation_result(state):
    return {
        "run_id": state.run_id,
        "scenario_id": state.scenario_id,
        "phase": state.phase,
        "selected_hypothesis_id": state.selected_hypothesis_id,
        "findings": [
            finding.model_dump()
            for finding in state.findings
        ],
        "evidence": [
            item.model_dump()
            for item in state.evidence
        ],
        "hypotheses": [
            item.model_dump()
            for item in state.hypotheses
        ],
        "challenges": [
            item.model_dump()
            for item in state.challenges
        ],
        "judge_scores": [
            item.model_dump()
            for item in state.judge_scores
        ],
        "proposed_actions": [
            item.model_dump()
            for item in state.proposed_actions
        ],
        "policy_decisions": [
            item.model_dump()
            for item in state.policy_decisions
        ],
        "human_approval_required": state.human_approval_required,
        "approved_action_ids": state.approved_action_ids,
        "tool_trace": state.tool_trace,
        "audit_log": state.audit_log,
    }


async def execute_active_investigation():
    scenario = get_active_scenario_summary()

    state = create_investigation_state(
        scenario_id=scenario["scenario_id"],
        incident=load_incident(),
    )

    result = await run_investigation(
        state=state,
        domain=scenario["domain"],
    )

    save_run(result)

    return format_investigation_result(result)


@app.get("/")
def home():
    return {
        "message": "Flight Control API is running.",
        "dashboard": "/dashboard",
        "swagger_docs": "/docs",
        "active_scenario": get_active_scenario_summary(),
    }


@app.get("/api/config")
def get_public_config():
    """Expose safe runtime metadata without returning credentials."""
    return {
        "model": MODEL_NAME,
        "live_analysis_available": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.get("/api/scenarios")
def get_scenarios():
    return {
        "active_scenario": get_active_scenario_summary(),
        "scenarios": list_scenarios(),
    }


@app.post("/api/scenarios/{scenario_id}/activate")
def activate_scenario_endpoint(scenario_id: str):
    try:
        active_scenario = activate_scenario(scenario_id)

        return {
            "message": "场景已切换",
            "active_scenario": {
                "scenario_id": active_scenario["scenario_id"],
                "title": active_scenario["title"],
                "domain": active_scenario["domain"],
                "severity": active_scenario["severity"],
            },
        }
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"场景不存在：{scenario_id}",
        )


@app.get("/api/incidents/active")
def get_active_incident():
    return load_incident()


@app.get("/api/incidents/payment", deprecated=True)
def get_payment_incident():
    return load_incident()


@app.post("/api/investigations/active/run")
async def run_active_investigation():
    try:
        response = await execute_active_investigation()
        response["execution_mode"] = "live_gpt"
        response["model"] = MODEL_NAME
        return response
    except AuthenticationError as error:
        logger.warning("OpenAI authentication failed")
        raise HTTPException(
            status_code=502,
            detail="OpenAI authentication failed. Check the configured API key.",
        ) from error
    except RateLimitError as error:
        logger.warning("OpenAI rate or credit limit reached")
        raise HTTPException(
            status_code=429,
            detail="OpenAI rate or credit limit reached. Try again later or check billing.",
        ) from error
    except (APIConnectionError, APITimeoutError) as error:
        logger.warning("OpenAI connection failed")
        raise HTTPException(
            status_code=503,
            detail="OpenAI is temporarily unreachable. Please retry shortly.",
        ) from error
    except OpenAIError as error:
        logger.exception("OpenAI request failed")
        raise HTTPException(
            status_code=502,
            detail="The live GPT analysis failed before a result was produced.",
        ) from error


@app.post("/api/demo/active-decision")
async def run_active_offline_demo():
    scenario = get_active_scenario_summary()

    try:
        state = await run_offline_demo(
            scenario_id=scenario["scenario_id"],
            incident=load_incident(),
            domain=scenario["domain"],
        )

        save_run(state)

        response = format_investigation_result(state)
        response["execution_mode"] = "offline_demo"

        return response
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@app.get("/api/investigations/{run_id}")
def get_investigation(run_id: str):
    try:
        state = get_run(run_id)
        return format_investigation_result(state)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"找不到 investigation run：{run_id}",
        )


@app.post("/api/investigations/{run_id}/approve")
def approve_investigation_actions(
    run_id: str,
    request: ApprovalRequest,
):
    try:
        state = approve_actions(
            run_id=run_id,
            action_ids=request.action_ids,
            approver=request.approver,
        )

        return format_investigation_result(state)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"找不到 investigation run：{run_id}",
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@app.post("/api/incidents/active/investigate", deprecated=True)
async def investigate_active_incident():
    return await execute_active_investigation()


@app.post("/api/incidents/payment/investigate", deprecated=True)
async def investigate_payment_incident():
    return await execute_active_investigation()
