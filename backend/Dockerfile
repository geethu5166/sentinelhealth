# ── Stage 1: Builder ──
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv==0.4.18

# Copy dependency manifests first for layer caching
COPY pyproject.toml uv.lock* ./

# Install dependencies into a virtual environment
RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv pip install --no-cache -r pyproject.toml

# ── Stage 2: Runtime ──
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime system dependencies (curl for healthchecks, libpq for postgres)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Activate virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application code
COPY . .

# Create non-root user
RUN groupadd --gid 1001 sentinel && \
    useradd --uid 1001 --gid sentinel --shell /bin/bash --create-home sentinel && \
    chown -R sentinel:sentinel /app

USER sentinel

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
