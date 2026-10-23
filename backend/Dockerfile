FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/workspace/backend

WORKDIR /workspace

COPY backend/app/requirements.txt /workspace/backend/app/requirements.txt
RUN pip install --upgrade pip && pip install -r /workspace/backend/app/requirements.txt

COPY backend/app /workspace/backend/app
COPY ml /workspace/ml

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "/workspace/backend", "--host", "0.0.0.0", "--port", "8000"]
