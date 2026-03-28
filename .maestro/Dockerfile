FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_CACHE_DIR=/tmp/pip-cache \
    PYTHONPYCACHEPREFIX=/tmp/pycache \
    RUFF_CACHE_DIR=/tmp/ruff

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -e ".[dev]" \
    && chown -R appuser:appuser /app

USER appuser
