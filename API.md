# API Reference

The AI Code Platform is accessible over HTTPS through the unified Nginx gateway:

- **Platform Base URL:** `https://localhost/api/v1` (or `https://<NGINX_HOST>/api/v1`)
- **OpenAI Compatible Base URL:** `https://localhost/v1` (or `https://<NGINX_HOST>/v1`)

---

## Gateway Routing Overview

| Prefix / Path | Upstream Service | Protocol & Auth |
|---------------|------------------|-----------------|
| `/api/v1/*` | FastAPI Backend (`:8080`) | HTTPS (REST + SSE), `X-API-Key` header |
| `/v1/*` | LiteLLM Proxy (`:4000`) | HTTPS (OpenAI API), `Bearer <key>` or `Authorization` header |
| `/key/*` | LiteLLM Proxy (`:4000`) | HTTPS, Master Key (`Bearer <LITELLM_MASTER_KEY>`) |
| `/grafana/*` | Grafana (`:3000`) | HTTPS, Basic Auth / Cookie session |
| `/health` | FastAPI Backend (`:8080`) | HTTPS, Public |
| `/docs`, `/redoc` | FastAPI Backend (`:8080`) | HTTPS, Public |
| `/metrics` | FastAPI Backend (`:8080`) | HTTPS, Prometheus scrape format |

---

## 1. Authentication & Key Management

### Provision a User & Virtual Key

Creates a new user in PostgreSQL and provisions a virtual key in LiteLLM with pre-configured rate limits (RPM: 120, TPM: 200,000).

```http
POST /api/v1/auth/provision
Content-Type: application/json
```

**Request Body:**
```json
{
  "username": "developer-1"
}
```

**Response** `201 Created`:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "username": "developer-1",
  "api_key": "sk-your-virtual-api-key"
}
```

> **Security Note:** Store the generated `api_key` securely. It serves both as the `X-API-Key` header for the platform API and as the `Bearer` token for OpenAI-compatible tools like Continue.dev.

---

### Get Current User Profile

Retrieves profile and authentication metadata for the active API key.

```http
GET /api/v1/auth/me
X-API-Key: sk-your-virtual-api-key
```

**Response** `200 OK`:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "username": "developer-1",
  "api_key": "sk-your-virtual-api-key"
}
```

---

## 2. Platform Code Assistant (Streaming Chat)

### Stream Chat Response

Sends a prompt to the AI assistant with persistent multi-turn session tracking. Emits real-time tokens via Server-Sent Events (SSE). 

> **SSE Configuration:** Nginx is configured with `proxy_buffering off` and `chunked_transfer_encoding off` to guarantee zero-latency token delivery.

```http
POST /api/v1/chat
X-API-Key: sk-your-virtual-api-key
Content-Type: application/json
```

**Request Body:**
```json
{
  "message": "Write a thread-safe LRU Cache in Python using OrderedDict",
  "session_id": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | `string` | ✅ | User prompt or code instructions |
| `session_id` | `UUID \| null` | ❌ | Existing session ID to continue dialogue. When `null`, a new session is created. |

**Response Stream** `200 OK` (`Content-Type: text/event-stream`):
```
data: {"session_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901", "content": "from ", "is_done": false}

data: {"session_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901", "content": "collections import OrderedDict\nimport threading\n\n", "is_done": false}

data: {"session_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901", "content": "class LRUCache:\n", "is_done": false}

data: {"session_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901", "content": "", "is_done": true}
```

---

## 3. Chat Session Management

### List User Sessions

Retrieves all chat sessions associated with the authenticated user, sorted by last updated timestamp.

```http
GET /api/v1/sessions
X-API-Key: sk-your-virtual-api-key
```

**Response** `200 OK`:
```json
[
  {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "title": "Write a thread-safe LRU Cache in Python...",
    "created_at": "2026-08-18T09:00:00Z",
    "updated_at": "2026-08-18T09:05:30Z"
  }
]
```

---

### Get Session Detail & Message History

Fetches a specific session along with all historical messages in chronological order.

```http
GET /api/v1/sessions/{session_id}
X-API-Key: sk-your-virtual-api-key
```

**Response** `200 OK`:
```json
{
  "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "title": "Write a thread-safe LRU Cache in Python...",
  "created_at": "2026-08-18T09:00:00Z",
  "updated_at": "2026-08-18T09:05:30Z",
  "messages": [
    {
      "role": "user",
      "content": "Write a thread-safe LRU Cache in Python using OrderedDict",
      "created_at": "2026-08-18T09:00:00Z"
    },
    {
      "role": "assistant",
      "content": "Here is the thread-safe LRU Cache implementation:\n\n```python\nfrom collections import OrderedDict\n...",
      "created_at": "2026-08-18T09:00:05Z"
    }
  ]
}
```

---

### Delete Session

Permanently removes a session and cascades deletion to all associated messages.

```http
DELETE /api/v1/sessions/{session_id}
X-API-Key: sk-your-virtual-api-key
```

**Response** `204 No Content` (Empty Body)

---

## 4. Asynchronous Batch Code Review (Celery)

### Submit Batch Code Review Task

Submits multiple code files for deep asynchronous analysis. Evaluates AST complexity, concurrency safety, edge cases, and security vulnerabilities.

```http
POST /api/v1/tasks/code-review
X-API-Key: sk-your-virtual-api-key
Content-Type: application/json
```

**Request Body:**
```json
{
  "files": [
    {
      "filename": "database.py",
      "code": "def query_user(user_id):\n    return db.execute(f'SELECT * FROM users WHERE id = {user_id}')"
    },
    {
      "filename": "server.py",
      "code": "import subprocess\ndef ping_host(host):\n    subprocess.Popen('ping ' + host, shell=True)"
    }
  ]
}
```

**Response** `200 OK`:
```json
{
  "task_id": "8f7e6d5c-4b3a-2109-8765-fedcba098765",
  "status": "QUEUED",
  "result": null
}
```

---

### Poll Task Status & Results

Checks task execution status. Progress is tracked dynamically via Redis, and final results are automatically written back to PostgreSQL via Celery signals.

```http
GET /api/v1/tasks/{task_id}
X-API-Key: sk-your-virtual-api-key
```

**Response (In Progress):**
```json
{
  "task_id": "8f7e6d5c-4b3a-2109-8765-fedcba098765",
  "status": "PROGRESS",
  "result": {
    "current": 1,
    "total": 2,
    "file": "database.py"
  }
}
```

**Response (Completed):**
```json
{
  "task_id": "8f7e6d5c-4b3a-2109-8765-fedcba098765",
  "status": "SUCCESS",
  "result": {
    "status": "COMPLETED",
    "files_analyzed": [
      {
        "filename": "database.py",
        "review": "### Critical Vulnerability Detected\n- **SQL Injection**: Direct string interpolation in `db.execute`. Use parameterized queries.",
        "status": "success"
      },
      {
        "filename": "server.py",
        "review": "### Critical Security Issue\n- **Command Injection**: `shell=True` allows shell metacharacters. Use array-based arguments.",
        "status": "success"
      }
    ]
  }
}
```

---

## 5. OpenAI Compatible API (Continue.dev & IDEs)

Directly accessible via Nginx at `https://localhost/v1/*`.

### Chat Completions

```http
POST /v1/chat/completions
Authorization: Bearer sk-your-virtual-api-key
Content-Type: application/json
```

**Request Body:**
```json
{
  "model": "qwen-coder",
  "messages": [
    {"role": "system", "content": "You are an expert coder."},
    {"role": "user", "content": "Refactor this function to be async"}
  ],
  "stream": true,
  "temperature": 0.2
}
```

---

## 6. System & Infrastructure Endpoints

### Health Check

```http
GET /health
```

**Response** `200 OK`:
```json
{
  "status": "HEALTHY",
  "env": "dev"
}
```

### Prometheus Metrics

```http
GET /metrics
```

Returns standard OpenMetrics/Prometheus formatted time-series data.

---

## Error Codes Reference

| HTTP Status | Error Type | Cause |
|-------------|------------|-------|
| `400 Bad Request` | Bad Request | Malformed payload or validation error |
| `401 Unauthorized` | Unauthorized | Missing `X-API-Key` or `Bearer` authentication header |
| `403 Forbidden` | Forbidden | Invalid, expired, or rate-limited API key |
| `404 Not Found` | Not Found | Session, task, or resource not found |
| `422 Unprocessable Entity` | Schema Error | Pydantic model validation failure |
| `500 Internal Server Error` | Server Error | Unhandled exception (traceback logged, generic JSON returned) |
| `502 Bad Gateway` | Gateway Error | Upstream container (backend / vLLM / litellm) initializing or down |
