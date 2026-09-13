# syntax=docker/dockerfile:1
# ── QA Orchestrator ───────────────────────────────────────────────────────────
# Python 3.11-slim + Playwright Chromium + Newman (API testing via Newman CLI)
# Phase 6 — server deployment image
FROM python:3.11-slim

WORKDIR /app

# OS dependencies:
#   - curl + ca-certificates: NodeSource setup script + HTTPS
#   - nodejs/npm: Newman (Postman collection runner)
#   - Playwright system deps are installed via 'playwright install --with-deps'
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g newman \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies first (layer cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browser binaries — shared path so any OS user can find them
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install chromium --with-deps

# Application code
COPY . .

# Pre-create writable runtime directories
RUN mkdir -p \
        outputs/e2e \
        outputs/reports \
        outputs/screenshots \
        outputs/attachments \
        memory/chromadb

# Non-root runtime user (security hardening)
RUN useradd -m -u 1000 qauser \
    && chown -R qauser:qauser /app /ms-playwright
USER qauser

ENTRYPOINT ["python", "run.py"]
