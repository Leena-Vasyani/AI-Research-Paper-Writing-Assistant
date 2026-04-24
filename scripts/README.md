# Scripts Guide

This folder contains canonical operational entrypoints for local development.

## Canonical Scripts

- run.bat: Interactive launcher for Streamlit, FastAPI, and Next.js
- research_paper.py: Legacy Streamlit UI entrypoint

## How To Run

From repository root:

1. Run launcher menu:
   - run.bat

2. Run Streamlit directly:
   - .venv\Scripts\python.exe -m streamlit run scripts\research_paper.py

3. Run FastAPI backend directly:
   - .venv\Scripts\python.exe -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

4. Run frontend directly:
   - cd web
   - npm run dev

5. Run full Docker deployment stack:
   - docker compose -f infra/compose/docker-compose.yml up --build

6. Use root workspace scripts (recommended):
   - npm run api:dev
   - npm run web:dev
   - npm run docker:up

## Compatibility Notes

- Root run.bat delegates to scripts/run.bat.
- Root research_paper.py delegates to scripts/research_paper.py.
- Existing root-level workflows continue to work during migration.
