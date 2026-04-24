# Architecture Map

## Goal

Provide a quick, stable map of where core functionality lives after the backend + scripts cleanup.

## Top-Level Layout

- `backend/`: canonical Python backend code
- `api/`, `core_agents/`, `fine_tuning/`: compatibility import bridges to `backend/`
- `web/`: Next.js frontend
- `infra/`: deployment and runtime infrastructure
- `scripts/`: canonical operational script entrypoints
- `run.bat`, `research_paper.py`: root compatibility launchers
- `data/`: runtime persistence (RAG/session artifacts)
- `docs/features/`: detailed feature-level documentation
- `docs/agents/`: detailed backend agent/module documentation

## Backend

- `backend/api/main/__init__.py`: FastAPI app and routes
- `backend/api/schemas.py`: request/response models
- `backend/core_agents/`: query/retrieve/summarize/plagiarism/citation/RAG agents
- `backend/fine_tuning/`: drafting model training and inference

## Frontend

- `web/src/app/`: route pages
- `web/src/components/`: reusable UI components
- `web/src/lib/`: API client and shared frontend helpers

## Infrastructure

- `infra/docker/backend.Dockerfile`: production image for FastAPI backend
- `infra/docker/web.Dockerfile`: production image for Next.js frontend
- `infra/compose/docker-compose.yml`: full local/prod-like multi-service stack
- `infra/nginx/default.conf`: reverse proxy rules (`/` -> web, `/api` -> backend)

## Operational Scripts

- `scripts/run.bat`: menu launcher (Streamlit/FastAPI/Next.js)
- `scripts/research_paper.py`: legacy Streamlit interface

## Compatibility Notes

- Start backend with: `python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload`
- Legacy imports still work via bridge packages:
  - `from api.main import app`
  - `from core_agents.query_agent import ScientificQueryAgent`
  - `from fine_tuning.fine_tuned_drafting_agent import DraftingConfig`
