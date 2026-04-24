FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend ./backend
COPY api ./api
COPY core_agents ./core_agents
COPY fine_tuning ./fine_tuning
COPY data ./data

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]