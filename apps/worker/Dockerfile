FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.4 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
ENV PYTHONPATH=/app/src

CMD ["python", "-m", "worker.entrypoints.worker"]
