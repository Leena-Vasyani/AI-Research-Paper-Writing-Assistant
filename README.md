# ResearchGen — Next.js + FastAPI

This repo now includes a FastAPI backend plus a Next.js UI (phase 4 of the migration plan). Streamlit remains intact for fallback.

## Structure

- `api/` — FastAPI backend wrapping existing agents
- `core_agents/` — Original Python agents (unchanged)
- `fine_tuning/` — Drafting agent
- `web/` — Next.js UI
- `research_paper.py` — Streamlit UI (legacy)

## Backend (FastAPI)

Install Python deps:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

Run API:

```powershell
& ".\.venv\Scripts\python.exe" -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
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

## Legacy Streamlit (optional)

```powershell
& ".\.venv\Scripts\python.exe" -m streamlit run research_paper.py
```

## Notes

- API order and summaries are unchanged; only the UI layer is different.
- You can keep Streamlit running during the migration.
