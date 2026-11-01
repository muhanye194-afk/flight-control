# Flight Control

[![CI](https://github.com/muhanye194-afk/flight-control/actions/workflows/ci.yml/badge.svg)](https://github.com/muhanye194-afk/flight-control/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.9%2B-335f70)
[![License: MIT](https://img.shields.io/badge/License-MIT-397254.svg)](LICENSE)

An evidence-first incident response workspace for investigating simulated P1 outages with specialist agents, structured GPT analysis, deterministic scoring, and human approval gates.

Flight Control is designed as a reliability engineering portfolio project—not a general-purpose chatbot. It separates observed evidence from generated hypotheses and never executes production-changing actions automatically.

## What it demonstrates

- Four incident scenarios covering payments, video edge routing, feed caching, and recommender-system shilling attacks.
- Parallel specialist review of metrics, logs, traces, recent changes, and runbooks.
- Domain-scoped hybrid retrieval so unrelated operational knowledge does not leak between scenarios.
- GPT-5.6 structured outputs for competing hypotheses, skeptical review, and remediation planning.
- A deterministic Evidence Judge that scores source quality, diversity, reliability, and counter-evidence.
- A Policy Guard that blocks unsafe actions and routes high-risk changes to named human approval.
- A responsive dashboard with both live GPT analysis and a no-cost offline demo.
- A deterministic long-horizon recommender-safety loop with 10, 20, or 50 reasoning steps, checkpoint rollback, sandbox canary actions, and delayed-feedback verification.
- A seeded reliability benchmark comparing an unguarded baseline with evidence-gated execution across different reasoning horizons.

## Engineering decisions

- **The model proposes; code decides.** GPT generates hypotheses, challenges, and remediation candidates, while a deterministic judge and policy layer make the final routing decisions.
- **Every claim points back to evidence.** Structured outputs must reference evidence IDs already collected by specialist agents; unknown IDs are rejected instead of silently accepted.
- **Live and deterministic paths stay separate.** The live path demonstrates model reasoning, while the offline path keeps interviews, development, and CI repeatable without API spend.
- **Production changes stop at an approval boundary.** The demo records a named approval but never connects to production infrastructure or executes a proposed change.

## Decision flow

```mermaid
flowchart LR
    A[P1 scenario] --> B[Incident Commander]
    B --> C1[Observability]
    B --> C2[Change Intelligence]
    B --> C3[Knowledge Retrieval]
    C1 --> D[Evidence Pool]
    C2 --> D
    C3 --> D
    D --> E[GPT Hypothesis Agent]
    E --> F[GPT Skeptic]
    F --> G[Evidence Judge]
    G --> H[GPT Remediation Planner]
    H --> I[Policy Guard]
    I -->|read only| J[Allowed]
    I -->|production change| K[Human approval]
```

## Run locally

Requires Python 3.9 or newer.

```bash
git clone https://github.com/muhanye194-afk/flight-control.git
cd flight-control
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add an OpenAI API key to `.env` for live analysis:

```dotenv
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.6-sol
OPENAI_TIMEOUT_SECONDS=90
OPENAI_MAX_RETRIES=2
```

Start the API and dashboard:

```bash
python -m uvicorn main:app --reload --port 8001
```

Then open [http://127.0.0.1:8001/dashboard/](http://127.0.0.1:8001/dashboard/).

- **Run GPT analysis** makes live API calls and uses paid API credits.
- **Run offline demo** exercises the complete evidence, scoring, policy, and approval flow without an API call.
- Select **Coordinated Shilling Attack**, choose a horizon, and run **RS safety loop** to inspect the step-by-step trajectory and automatic stale-evidence rollback.
- **Compare horizons** runs seeded fault-injection diagnostics locally. These simulated results demonstrate the evaluation harness and are not claims about live-model performance.

## Recommender safety mode

The recommender scenario turns the one-pass incident workflow into an explicit action/observation loop. The agent inspects exposure, suspicious profiles, interaction bursts, and model history; compares competing hypotheses; saves a checkpoint; rejects a deliberately stale snapshot; evaluates a profile-quarantine action in a sandbox; applies a simulated 5% canary; and verifies four safety postconditions over the selected horizon.

The simulator tracks:

- target-item exposure;
- catalog coverage;
- suspicious-profile ratio;
- group exposure gap;
- cumulative harm, rollbacks, unsafe actions, and recovery success.

No account, recommendation model, or production service is connected or changed. The real quarantine proposal remains behind the existing named-human approval boundary.

The `.env` file is ignored by Git. Never commit or paste an API key into source code.

## Tests

The regression suite is intentionally runnable without `pytest` or an OpenAI key:

```bash
python tests/run_all.py
```

It covers specialist agents, evidence scoring, policy enforcement, run storage, deterministic embeddings, the offline decision flow, and API smoke checks. GitHub Actions runs the same suite on every push and pull request.

## API highlights

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/scenarios` | List scenarios and the active selection |
| `POST` | `/api/scenarios/{id}/activate` | Switch the active local scenario |
| `POST` | `/api/investigations/active/run` | Run the live GPT investigation |
| `POST` | `/api/demo/active-decision` | Run the deterministic offline demo |
| `POST` | `/api/recommender-safety/active/run` | Run a 10, 20, or 50-step RS safety investigation |
| `POST` | `/api/recommender-safety/benchmark` | Compare seeded baseline and evidence-gated reliability |
| `POST` | `/api/investigations/{run_id}/approve` | Record a named human approval |
| `GET` | `/docs` | OpenAPI documentation |

## Safety boundaries

This repository uses simulated incidents and local scenario data. Generated remediation remains advisory. The Policy Guard can allow read-only observation, require approval for risky changes, or block unsafe proposals; it does not connect to or mutate production infrastructure.

## Current scope and trade-offs

This is a portfolio and research prototype with production-inspired boundaries, not a deployed incident-management service. Investigation runs and approvals are stored in memory, the API has no user authentication, and the scenarios use local fixtures and a deterministic recommender simulator rather than live telemetry. The reliability benchmark uses seeded fault injection; empirical claims about LLM reliability require repeated live-model experiments and confidence intervals. A production version would add durable storage, role-based access, secrets management, observability, calibrated model evaluations, and integrations with incident and deployment systems.

## Project structure

```text
agent/            specialist agents, judge, policy guard, and orchestration
dashboard/        dependency-free dashboard
knowledge_base/   runbooks, architecture notes, and postmortems
rag/              hybrid retrieval pipeline
rs_safety/        sequential RS simulator and reliability benchmark
scenarios/        isolated incident fixtures
tests/            regression and API smoke tests
main.py           FastAPI application
```

Built with FastAPI, Pydantic, the OpenAI Responses API, BM25, sentence-transformers, and vanilla HTML/CSS/JavaScript.
