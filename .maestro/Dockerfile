FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends make git && rm -rf /var/lib/apt/lists/*

RUN useradd -u 1000 -m coder

WORKDIR /workspace

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]" || true

COPY . .

RUN pip install --no-cache-dir -e ".[dev]"
