# syntax=docker/dockerfile:1.4
FROM python:3.12-slim AS builder

# Install uv from the Astral registry
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock /app

# Install dependencies (only, no project code)
RUN uv sync --frozen --no-install-project
RUN uv pip install "fastapi[standard]"   

# Copy application code
COPY src /app/src
COPY . /app/

# Final stage: minimal runtime image
FROM python:3.12-slim

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed dependencies and app from builder
COPY --from=builder /app /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --from=builder /app/.venv/lib/python3.12/site-packages /app/.venv/lib/python3.12/site-packages

# Expose port
EXPOSE 8000

# Run FastAPI app using uv
# CMD ["/app/.venv/bin/fastapi", "run", "/app/src/main.py", "--host", "0.0.0.0", "--port", "8000"]   
# uv run uvicorn src.main:app --host 0.0.0.0 --port 8000"
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]