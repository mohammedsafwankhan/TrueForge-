# ==============================================================================
# STRANGER BUILDS 2026 - PRODUCTION DOCKERFILE
# Multi-Agent Autonomous Execution Engine with Fetch.ai ACP & ASI-1
# ==============================================================================

# Stage 1: Build & Dependency Resolution
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production Distroless/Slim Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Security: Create non-root system user
RUN groupadd -r agentgroup && useradd -r -g agentgroup -s /bin/bash agentuser

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source tree
COPY . .

# Ensure agent user owns application directory
RUN chown -R agentuser:agentgroup /app

USER agentuser

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AGENT_PORT=8000 \
    AGENT_NETWORK=testnet \
    AGENT_NAME=stranger_builds_primary_agent

EXPOSE 8000

# Container Healthcheck against REST health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "main.py"]
