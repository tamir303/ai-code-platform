# Architecture & System Design

## 1. High-Level Architecture

The **On-Prem AI Code Platform** is packaged into an isolated multi-container topology fronted by an Nginx reverse proxy gateway. All external client, developer, and IDE traffic is routed through encrypted HTTPS endpoints (ports 80 and 443).

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                           External Clients & Developer Tools                            │
│                 (Web UI, curl, Continue.dev, VS Code, JetBrains, Cursor)                │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │ HTTPS (:443) / HTTP (:80 -> 301)
                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                Nginx Reverse Proxy Gateway                               │
│  - SSL Termination (TLS 1.2/1.3)          - Zero SSE Buffering (proxy_buffering off)     │
│  - Path-Based Reverse Routing             - Security Headers & WebSocket Proxy           │
└──────┬──────────────────────┬────────────────────────┬─────────────────────┬─────────────┘
       │ /api/v1/*, /docs,    │ /v1/* (OpenAI API),    │ /grafana/*          │ /metrics
       │ /health              │ /key/*                 │                     │
       ▼                      ▼                        ▼                     ▼
┌──────────────┐       ┌──────────────┐         ┌──────────────┐      ┌──────────────┐
│ FastAPI API  │       │   LiteLLM    │         │   Grafana    │      │  Prometheus  │
│  (:8080)     │       │ Proxy (:4000)│         │   (:3000)    │      │   (:9090)    │
└──────┬───────┘       └──────┬───────┘         └──────┬───────┘      └──────▲───────┘
       │                      │                        │                     │
       │                      │                        └──────────────┐      │ Scrapes
       │                      ▼                                       ▼      │ metrics
       │               ┌──────────────────────────────────────┐     ┌────────┴───────┐
       │               │        vLLM Inference Engine         │     │ Internal DBs   │
       │               │        (:8000 on NVIDIA GPU)         │     │ & Cache        │
       │               └──────────────────────────────────────┘     └────────────────┘
       │                                                              │
       ├──────────────────────────┤
       ▼                          ▼
┌──────────────┐           ┌──────────────┐
│  PostgreSQL  │           │    Redis     │
│   (:5432)    │           │   (:6379)    │
└──────────────┘           └──────────────┘
```

---

## 2. Nginx Gateway & Routing Specifications

Nginx serves as the single public gateway into the internal Docker network. Upstream service ports (`8080`, `4000`, `3000`, `5432`, `6379`, `9090`) are **never directly exposed** to the host in production.

### Path Routing Rules

```
                      ┌───► /api/v1/*   ───► backend:8080    (FastAPI Core REST & SSE)
                      ├───► /v1/*       ───► litellm:4000    (OpenAI API for IDEs)
                      ├───► /key/*      ───► litellm:4000    (Virtual Key Administration)
https://<host>/───────┼───► /grafana/*  ───► grafana:3000    (Observability Dashboard)
                      ├───► /health     ───► backend:8080    (Liveness / Health Check)
                      ├───► /docs       ───► backend:8080    (Swagger OpenAPI Specs)
                      ├───► /redoc      ───► backend:8080    (ReDoc Documentation)
                      └───► /metrics    ───► backend:8080    (Prometheus Metrics)
```

### Server-Sent Events (SSE) Buffering Optimization

Real-time code generation requires immediate token streaming without gateway delay. Nginx is configured specifically for low-latency streaming:

```nginx
location /api/v1/ {
    proxy_pass http://backend;

    # Critical SSE directives:
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding off;

    # Extended timeout for long code completions
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
}
```

---

## 3. Core Subsystems

### A. vLLM Inference Engine
- **Role:** High-throughput local LLM execution.
- **Hardware Integration:** Utilizes the **NVIDIA Container Toolkit** (`runtime: nvidia`) with configurable `GPU_COUNT`, `CUDA_DEVICE_ORDER=PCI_BUS_ID`, and PagedAttention for memory efficiency.
- **Health Check Probe:** Integrated Docker health check polls `/health` with a startup grace period of 120–180s.
- **Model Served:** Defaults to `Qwen/Qwen2.5-Coder-7B-Instruct` (parameterized via `VLLM_MODEL`).

### B. LiteLLM Proxy Gateway
- **Role:** Enterprise LLM multiplexer, policy enforcer, and token limiter.
- **Key Features:**
  - Emits virtual keys with custom RPM / TPM quotas.
  - Exposes standard `/v1/chat/completions` API compatible with Continue.dev, Cursor, and OpenAI client libraries.
  - Caches frequent prompts in Redis to minimize GPU load.
  - Emits Prometheus metrics for prompt/completion token usage.

### C. FastAPI Application Server
- **Architecture:** Layered design strictly decoupling routes, controllers, business services, and repositories via FastAPI Dependency Injection (`src/di/container.py`).
- **Lifecycle Management:** Database connection pools, schema initialization via Alembic `entrypoint.sh`, and cleanup handled inside FastAPI `lifespan`.
- **Global Error Handling:** Middleware intercepts unhandled exceptions, logs tracebacks, and outputs uniform JSON errors.

### D. PostgreSQL & Alembic
- **Role:** Primary transactional database for users, chat sessions, and message histories.
- **Migrations:** Automated on startup via `alembic upgrade head` inside container entrypoints.

### E. Observability (Prometheus & Grafana)
- **Scrape Targets:** FastAPI (`:8080/metrics`), LiteLLM (`:4000`), vLLM (`:8000`).
- **Grafana Subpath:** Served securely behind Nginx at `/grafana/` via `GF_SERVER_SERVE_FROM_SUB_PATH=true`.

---

## 4. Layered Application Design

```
                     HTTP / SSE Request
                             │
                             ▼
  ┌───────────────────────────────────────────────────────┐
  │                      API Routes                       │
  │      src/routes/{auth,chat,session,task}_routes.py    │
  └──────────────────────────┬────────────────────────────┘
                             │
                             ▼
  ┌───────────────────────────────────────────────────────┐
  │                     Controllers                       │
  │             src/controller/*_controller.py            │
  └──────────────────────────┬────────────────────────────┘
                             │
                             ▼
  ┌───────────────────────────────────────────────────────┐
  │                   Service Interfaces                  │
  │           src/services/interfaces/services.py         │
  └──────────────────────────┬────────────────────────────┘
                             │ (Dependency Injection)
                             ▼
  ┌───────────────────────────────────────────────────────┐
  │                 Service Implementations               │
  │         src/services/implementations/*_service.py     │
  └──────────────────────────┬────────────────────────────┘
                             │
                             ▼
  ┌───────────────────────────────────────────────────────┐
  │                  Repository Interfaces                │
  │          src/db/interfaces/repositories.py            │
  └──────────────────────────┬────────────────────────────┘
                             │ (Dependency Injection)
                             ▼
  ┌───────────────────────────────────────────────────────┐
  │                PostgreSQL Repositories                │
  │         src/db/repositories/*_repository.py           │
  └──────────────────────────┬────────────────────────────┘
                             │ (asyncpg / SQLAlchemy)
                             ▼
                      PostgreSQL 16
```

---

## 5. End-to-End Execution Flows

### 1. Interactive Streaming Chat (`POST /api/v1/chat`)

```
Client              Nginx               FastAPI            Postgres             LiteLLM               vLLM (GPU)
  │                   │                    │                   │                   │                      │
  │──POST /chat──────►│──proxy_pass───────►│                   │                   │                      │
  │   (X-API-Key)     │   (buffering off)  │──Authenticate────►│                   │                      │
  │                   │                    │──Get/Create Ses──►│                   │                      │
  │                   │                    │──Save User Msg───►│                   │                      │
  │                   │                    │──Stream Tokens───────────────────────►│──Forward to GPU─────►│
  │                   │                    │                   │                   │◄─Yield Tokens────────│
  │                   │◄──SSE Chunk────────│◄──Stream Token────│                   │                      │
  │◄──SSE Chunk───────│   (zero latency)   │                   │                   │                      │
  │   ...             │   ...              │                   │                   │                      │
  │                   │                    │──Save Assis Msg──►│                   │                      │
  │◄──is_done: true───│◄───────────────────│                   │                   │                      │
```

### 2. Continue.dev IDE Autocomplete / Chat (`POST /v1/chat/completions`)

```
IDE (Continue.dev)        Nginx                    LiteLLM                     vLLM (GPU)
       │                    │                         │                            │
       │──POST /v1/chat────►│──proxy_pass /v1/───────►│                            │
       │  (Bearer sk-...)   │  (buffering off)        │──Validate Key & Quota      │
       │                    │                         │──Forward OpenAI Payload───►│
       │                    │                         │◄─Stream Response Chunks────│
       │◄─OpenAI SSE Chunk──│◄─Forward SSE Chunk──────│                            │
```

## 6. Relational Entity Schema

```
┌───────────────────────────┐
│           users           │
├───────────────────────────┤
│ id: UUID (PK)             │
│ username: VARCHAR(50) [UQ]│
│ api_key: VARCHAR(100) [UQ]│
│ created_at: TIMESTAMP     │
└─────────────┬─────────────┘
              │ 1:N
              ├─────────────────────────────────────────┐
              │                                         │
              ▼ 1:N                                     ▼ 1:N
┌───────────────────────────┐             ┌───────────────────────────┐
│       chat_sessions       │             │        async_tasks        │
├───────────────────────────┤             ├───────────────────────────┤
│ id: UUID (PK)             │             │ id: VARCHAR(100) (PK)     │
│ user_id: UUID (FK)        │             │ user_id: UUID (FK)        │
│ title: VARCHAR(255)       │             │ task_type: VARCHAR(50)    │
│ created_at: TIMESTAMP     │             │ status: VARCHAR(30)       │
│ updated_at: TIMESTAMP     │             │ result: JSON              │
└─────────────┬─────────────┘             │ created_at: TIMESTAMP     │
              │ 1:N                       │ updated_at: TIMESTAMP     │
              ▼                           └───────────────────────────┘
┌───────────────────────────┐
│       chat_messages       │
├───────────────────────────┤
│ id: UUID (PK)             │
│ session_id: UUID (FK)     │
│ role: VARCHAR(20)         │
│ content: TEXT             │
│ created_at: TIMESTAMP     │
└───────────────────────────┘
```

---

## 7. Environment & Isolation Model (Dev vs Prod)

| Feature | Development (`docker-compose.dev.yaml`) | Production (`docker-compose.prod.yaml`) |
|---------|-----------------------------------------|----------------------------------------|
| **Entrypoint Gateway** | Nginx (`nginx.dev.conf`) | Nginx (`nginx.prod.conf`) |
| **SSL Configuration** | Self-signed generated via `generate-dev-certs.sh` | Production CA certificates mounted at `/opt/certs/` |
| **Domain Resolution** | `localhost` / `127.0.0.1` | Parameterized `${NGINX_HOST}` with `envsubst` |
| **Source Mounting** | Live reload (`./src`, `./alembic`) | Immutable container builds (no code mounts) |
| **Port Exposure** | Ports 80, 443 (Internal ports sealed) | Ports 80, 443 strictly |
| **Security Headers** | Basic CORS | HSTS, X-Frame-Options, XSS protection, nosniff |
| **GPU Allocation** | 88% memory allocation, 8k context | 92% memory allocation, 16k+ context |
| **Data Storage** | Local directory `./data/` | Host filesystem `/opt/data/` |
