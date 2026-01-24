@echo off
echo 1. Run Streamlit (legacy)
echo 2. Run FastAPI backend
echo 3. Run Next.js frontend
set /p choice=Select option: 

if "%choice%"=="1" (
	call venv\Scripts\activate
	streamlit run research_paper.py
)

if "%choice%"=="2" (
	call venv\Scripts\activate
	python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
)

if "%choice%"=="3" (
	cd web
	npm run dev
)

pause