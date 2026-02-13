# Repository Guidelines

## Project Structure & Module Organization
- `api/`: FastAPI entrypoint and request schemas (`api/main/__init__.py`, `api/schemas.py`).
- `core_agents/`: domain agents (query, retrieval, summarization, drafting helpers, plagiarism, diagram, pseudocode).
- `fine_tuning/`: model training and fine-tuned drafting logic.
- `web/`: Next.js 16 + TypeScript frontend (`src/app` routes, `src/components` shared UI, `src/lib` API/types).
- Root docs (`README.md`, integration notes) describe migration and feature behavior.

## Build, Test, and Development Commands
- Python setup: `python -m pip install -r requirements.txt`
- Run backend: `python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`
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
- No dedicated automated test suite is currently checked in.
- Minimum pre-PR validation:
  - `npm run lint`
  - `npm run build`
  - Start API and confirm `GET /api/health` returns `{"status":"ok"}`.
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
