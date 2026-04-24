# ResearchGen — Next.js + FastAPI

This repo now includes a FastAPI backend plus a Next.js UI . Streamlit remains intact for fallback.

## Structure

- `backend/api/` — FastAPI backend wrapping existing agents
- `backend/core_agents/` — Python domain agents
- `backend/fine_tuning/` — Drafting and training logic
- `api/`, `core_agents/`, `fine_tuning/` — compatibility import packages
- `web/` — Next.js UI
- `infra/docker/` — backend/frontend Dockerfiles
- `infra/compose/` — docker compose stack definitions
- `infra/nginx/` — reverse proxy config for unified API + UI routing
- `scripts/research_paper.py` — Streamlit UI (legacy canonical path)
- `scripts/README.md` — launcher and local run guide
- `research_paper.py`, `run.bat` — compatibility launchers at repo root
- `docs/architecture-map.md` — quick project structure reference

## Backend (FastAPI)

Install Python deps:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

Run API:

```powershell
& ".\.venv\Scripts\python.exe" -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

- `GET http://localhost:8000/api/health`

## Frontend (Next.js)

Install Node deps:

```powershell
cd web
npm install
```

Run UI:

```powershell
npm run dev
```

Set API base URL in [web/.env.local](web/.env.local):

```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

For Docker + nginx deployment, use:

```
NEXT_PUBLIC_API_BASE=/api
```

## One-Command Docker Deployment

1. Create env files from templates:
	- `.env.example` -> `.env`
	- `web/.env.local.example` -> `web/.env.local`
2. Start full stack:

```powershell
npm run docker:up
```

3. Open app:
	- `http://localhost`

Stop stack:

```powershell
npm run docker:down
```

## Legacy Streamlit (optional)

```powershell
& ".\.venv\Scripts\python.exe" -m streamlit run scripts/research_paper.py
```

## Notes

- API order and summaries are unchanged; only the UI layer is different.
- You can keep Streamlit running during the migration.

## Smoke Checks

Run lightweight structure/import smoke tests:

```powershell
& ".\.venv\Scripts\python.exe" -m unittest tests.test_smoke_imports -v
```

## Universal Research Formatter

New tool in the Next.js UI:

- Live A4 preview with IEEE-style layout controls
- Groq-powered Quick Fix bar for layout tweaks
- LaTeX (.tex) export via latex.js

If you want AI Quick Fix enabled, set in your environment:

```
GROQ_API_KEY=your_key_here
```
