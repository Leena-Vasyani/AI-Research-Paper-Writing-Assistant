@echo off
set "ROOT_DIR=%~dp0.."
pushd "%ROOT_DIR%"

set "PYTHON_EXE=.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

echo 1. Run Streamlit (legacy)
echo 2. Run FastAPI backend
echo 3. Run Next.js frontend
echo 4. Run Docker deployment stack
set /p choice=Select option: 

if "%choice%"=="1" (
	"%PYTHON_EXE%" -m streamlit run scripts\research_paper.py
)

if "%choice%"=="2" (
	"%PYTHON_EXE%" -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
)

if "%choice%"=="3" (
	cd web
	npm run dev
)

if "%choice%"=="4" (
	docker compose -f infra\compose\docker-compose.yml up --build
)

popd
pause