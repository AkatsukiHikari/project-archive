FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy dependency files first (for layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev group, no editable install)
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY . .

# Install the project itself
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

# Default: run FastAPI server. Override in docker-compose for Celery.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
