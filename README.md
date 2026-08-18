# On-Prem AI Code Platform

A fully self-hosted, GPU-accelerated AI coding assistant platform powered by **vLLM**, **LiteLLM**, **FastAPI**, and **Nginx**. Designed for engineering teams requiring private, on-premise LLM inference with zero data leakage, complete IDE compatibility (e.g. Continue.dev, Cursor), and enterprise-grade observability.

## Features

- **Nginx Gateway & Path Routing** — Unified HTTPS entry point (80/443) with SSL and zero direct exposure of internal microservices.
- **SSE Streaming with Buffering Disabled** — High-throughput real-time token streaming with `proxy_buffering off` and chunked transfer optimizations.
- **IDE & Continue.dev Native Support** — Direct OpenAI-compatible endpoint at `/v1` backed by LiteLLM virtual keys.
- **FastAPI Code Assistant & Session Management** — Full conversation history, multi-session management, and task tracking at `/api/v1`.
- **Batch Code Review** — Asynchronous Celery workers for AST complexity, concurrency safety, and vulnerability analysis.
- **On-Prem GPU Inference** — High-performance vLLM engine serving Qwen2.5-Coder (or any Hugging Face model) via NVIDIA Container Toolkit.
- **Key & Quota Management** — Provision scoped API keys with RPM/TPM limits and usage quotas.
- **Alembic Database Migrations** — Managed relational database lifecycle for PostgreSQL with asyncpg.
- **Full Observability Suite** — Built-in Prometheus metrics and pre-configured Grafana dashboards at `/grafana/`.

---

## Tech Stack

| Layer | Technology | Role |
|-------|-----------|------|
| **Reverse Proxy / Gateway** | Nginx 1.27 (Alpine) | SSL termination, path routing, SSE buffering control, security headers |
| **Inference Engine** | vLLM (OpenAI-compatible) | High-throughput GPU inference with PagedAttention |
| **LLM Gateway** | LiteLLM | Key management, rate limiting, model routing, caching |
| **Backend API** | FastAPI + Uvicorn | Session orchestration, chat history, async job management |
| **Task Queue** | Celery + Redis | Asynchronous batch code analysis workers |
| **Database** | PostgreSQL 16 + asyncpg | Persistent data store for users, sessions, messages, and tasks |
| **Database Migrations** | Alembic | Version-controlled schema migrations |
| **Cache & Broker** | Redis Stack | Task broker, result backend, and LLM cache |
| **Monitoring** | Prometheus + Grafana | Metrics collection and observability dashboards |
| **Hardware Layer** | NVIDIA Container Toolkit | GPU passthrough and CUDA device management |

---

## Architecture & Gateway Path Routing

All external traffic flows through Nginx on ports **80 (HTTP redirect)** and **443 (HTTPS)**:

```
                          Client / IDE (Continue.dev) / Browser
                                            │
                                            ▼
                                  ┌───────────────────┐
                                  │   Nginx (443 SSL) │
                                  └─────────┬─────────┘
                                            │
               ┌────────────────────────────┼────────────────────────────┐
               │                            │                            │
               ▼                            ▼                            ▼
  /api/v1/* (SSE unbuffered)    /v1/* (OpenAI-compatible)        /grafana/* (Subpath)
  /docs, /health, /metrics             /key/*                     /grafana/api/*
               │                            │                            │
               ▼                            ▼                            ▼
      ┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
      │   FastAPI API   │          │  LiteLLM Proxy  │          │     Grafana     │
      │    (:8080)      │          │     (:4000)     │          │     (:3000)     │
      └────────┬────────┘          └────────┬────────┘          └─────────────────┘
               │                            │
               ├────────────────────────────┘
               ▼
      ┌─────────────────┐
      │   vLLM Engine   │ (:8000 on GPU)
      └─────────────────┘
```

| Path | Destination | Purpose |
|------|-------------|---------|
| `https://<host>/api/v1/*` | FastAPI (`backend:8080`) | Chat streaming, session history, batch review tasks, auth |
| `https://<host>/v1/*` | LiteLLM (`litellm:4000`) | OpenAI-compatible endpoint for IDEs (Continue.dev, Cursor) |
| `https://<host>/key/*` | LiteLLM (`litellm:4000`) | Key generation and usage administration |
| `https://<host>/grafana/` | Grafana (`grafana:3000`) | Monitoring dashboards and alerts |
| `https://<host>/health` | FastAPI (`backend:8080`) | System health check |
| `https://<host>/docs` | FastAPI (`backend:8080`) | Interactive Swagger API documentation |
| `https://<host>/metrics` | FastAPI (`backend:8080`) | Prometheus metrics endpoint |

---

## Prerequisites

- **Host OS:** Linux (Ubuntu 20.04/22.04/24.04 recommended)
- **NVIDIA GPU:** ≥16 GB VRAM (24 GB+ recommended for large context windows)
- **NVIDIA Driver:** Installed on host (`nvidia-smi` functioning)
- **Docker Engine:** ≥ 24.0
- **Docker Compose:** ≥ 2.20
- **NVIDIA Container Toolkit:** Installed & configured

---

## Quick Start (Development)

```bash
# 1. Clone the repository
git clone <repo-url> && cd ai-code-platform

# 2. Install NVIDIA Container Toolkit on host (one-time)
sudo ./scripts/setup-nvidia-toolkit.sh

# 3. Generate self-signed SSL certificates for dev Nginx
chmod +x scripts/*.sh
./scripts/generate-dev-certs.sh

# 4. Configure environment
cp .env.example .env.dev
# Edit .env.dev and specify HF_TOKEN, passwords, and GPU settings

# 5. Launch the complete platform stack
docker compose -f docker-compose.dev.yaml --env-file .env.dev up -d

# 6. Monitor vLLM initialization
docker compose -f docker-compose.dev.yaml logs -f vllm
```

---

## Provisioning Keys & Connecting IDEs

### 1. Provision a User & API Key
```bash
curl -k -X POST https://localhost/api/v1/auth/provision \
  -H "Content-Type: application/json" \
  -d '{"username": "developer-1"}'
```
*Output:*
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "username": "developer-1",
  "api_key": "sk-your-virtual-key"
}
```

### 2. Configure Continue.dev (`~/.continue/config.json`)
Connect your IDE directly to your on-prem platform:
```json
{
  "models": [
    {
      "title": "On-Prem Qwen Coder",
      "provider": "openai",
      "model": "qwen-coder",
      "apiBase": "https://localhost/v1",
      "apiKey": "sk-your-virtual-key"
    }
  ],
  "tabAutocompleteModel": {
    "title": "On-Prem Autocomplete",
    "provider": "openai",
    "model": "qwen-coder",
    "apiBase": "https://localhost/v1",
    "apiKey": "sk-your-virtual-key"
  }
}
```

### 3. Test Platform Chat Endpoint
```bash
curl -k -X POST https://localhost/api/v1/chat \
  -H "X-API-Key: sk-your-virtual-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "Write a concurrent worker pool in Go"}'
```

---

## Service URLs (via Nginx Gateway)

| Component | URL | Auth Required |
|-----------|-----|---------------|
| **FastAPI REST API** | `https://localhost/api/v1` | `X-API-Key` header |
| **OpenAI Compatible API** | `https://localhost/v1` | `Bearer <key>` header |
| **Interactive Docs (Swagger)** | `https://localhost/docs` | None |
| **Interactive Docs (ReDoc)** | `https://localhost/redoc` | None |
| **System Health** | `https://localhost/health` | None |
| **Grafana Dashboard** | `https://localhost/grafana/` | Basic Auth (`admin` / `$GRAFANA_ADMIN_PASSWORD`) |
| **Prometheus Metrics** | `https://localhost/metrics` | None (Internal / Protected in Prod) |

---

## Database Migrations (Alembic)

Database schema migrations run automatically on container startup through `entrypoint.sh`. For manual migration workflows:

```bash
# Generate a new migration revision
docker compose -f docker-compose.dev.yaml exec backend alembic revision --autogenerate -m "add_column_name"

# Apply all pending migrations
docker compose -f docker-compose.dev.yaml exec backend alembic upgrade head

# Rollback one migration
docker compose -f docker-compose.dev.yaml exec backend alembic downgrade -1

# Show current migration revision
docker compose -f docker-compose.dev.yaml exec backend alembic current
```

---

## Production Deployment

### 1. Configure Production Environment
```bash
cp .env.example .env.prod
# Configure NGINX_HOST (e.g. ai.company.internal), secure passwords, and GPU utilization
```

### 2. Set Up Production SSL Certificates
Place valid SSL certificates in `/opt/certs/`:
- `/opt/certs/fullchain.pem`
- `/opt/certs/privkey.pem`

### 3. Launch Production Stack
```bash
docker compose -f docker-compose.prod.yaml --env-file .env.prod up -d
```

### Production Hardening Highlights:
- **Port Isolation:** Only ports 80 & 443 are exposed. Database, Redis, Celery, and internal API services are sealed inside the Docker network.
- **HTTP/2 & HSTS:** Enforced via `nginx.prod.conf`.
- **Dynamic Domain Substitution:** Nginx configuration uses `envsubst` to dynamically populate `NGINX_HOST`.
- **Production Workers:** Celery worker concurrency scaled to 8 workers.
- **Dedicated Data Volumes:** Persistent data mounted under `/opt/data/`.

---

## Diagnostics & GPU Validation

Verify complete GPU passthrough and driver health at any time:
```bash
./scripts/validate-gpu.sh
```

---

## Documentation Links

- **[API Reference (API.md)](API.md)** — Complete endpoint specifications, schemas, error codes, and SSE streaming payload details.
- **[System Architecture (ARCHITECTURE.md)](ARCHITECTURE.md)** — Deep dive into service interactions, Nginx buffering control, layered design, and data models.