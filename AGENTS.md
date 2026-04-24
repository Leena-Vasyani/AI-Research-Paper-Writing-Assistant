# Repository Guidelines

## Project Structure & Module Organization

- `backend/api/`: FastAPI entrypoint and request schemas (`backend/api/main/__init__.py`, `backend/api/schemas.py`).
- `backend/core_agents/`: domain agents (query, retrieval, summarization, drafting helpers, plagiarism, diagram, pseudocode).
- `backend/fine_tuning/`: model training and fine-tuned drafting logic.
- `api/`, `core_agents/`, `fine_tuning/`: compatibility import packages that forward to `backend/` paths.
- `scripts/`: canonical local launcher scripts (`scripts/run.bat`, `scripts/research_paper.py`).
- Root `run.bat` and `research_paper.py`: compatibility wrappers that delegate to `scripts/`.
- `docs/architecture-map.md`: high-level project map for contributors.
- `web/`: Next.js 16 + TypeScript frontend (`src/app` routes, `src/components` shared UI, `src/lib` API/types).
- Root docs (`README.md`, integration notes) describe migration and feature behavior.

## Build, Test, and Development Commands

- Python setup: `python -m pip install -r requirements.txt`
- Run backend: `python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload`
- Run frontend:
  - `cd web`
  - `npm install`
  - `npm run dev`
- Frontend quality checks:
  - `npm run lint` (ESLint for Next.js + TypeScript)
  - `npm run build` (production build validation)
- Optional launcher: `run.bat` (legacy Streamlit / API / frontend chooser).

## Coding Style & Naming Conventions

- Python: PEP 8 style, 4-space indentation, `snake_case` for functions/variables, `PascalCase` for classes.
- TypeScript/React: strict TypeScript (`web/tsconfig.json`), component files in `PascalCase` (e.g., `PageHeader.tsx`).
- App routes in `web/src/app` use descriptive kebab-case folders (e.g., `code-to-pseudocode`).
- Keep API contracts explicit with typed schema models and shared frontend types.

## Testing Guidelines

- A lightweight smoke test is available at `tests/test_smoke_imports.py`.
- Minimum pre-PR validation:
  - `npm run lint`
  - `npm run build`
  - Start API and confirm `GET /api/health` returns `{"status":"ok"}`.
- Optional quick backend structure check:
  - `python -m unittest tests.test_smoke_imports -v`
- For new backend logic, add `pytest` tests under a new `tests/` directory with names like `test_<module>.py`.

## Commit & Pull Request Guidelines

- Existing history favors short, task-focused subjects (examples: `fixed query agent`, `text to diagram`).
- Use imperative, scope-first messages moving forward, e.g., `api: add fallback for format endpoint`.
- PRs should include:
  - concise summary of behavior changes,
  - linked issue/task,
  - verification steps run locally,
  - UI screenshots/GIFs for `web/` changes.

## Security & Configuration Tips

- Use local env files for secrets; do not commit keys.
- Common variables: `GROQ_API_KEY`, `GEMINI_API_KEY`, `NEXT_PUBLIC_API_BASE`.
