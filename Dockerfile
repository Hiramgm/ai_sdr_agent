FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md requirements.txt ./
COPY src ./src

RUN pip install --upgrade pip && pip install -e .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "ai_sdr.api:app", "--host", "0.0.0.0", "--port", "8000"]
