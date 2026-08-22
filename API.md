# API Reference

The AI Code Platform is accessible over HTTPS through the unified Nginx gateway:

- **Platform Base URL:** `https://localhost/api/v1` (or `https://<NGINX_HOST>/api/v1`)
- **OpenAI Compatible Base URL:** `https://localhost/v1` (or `https://<NGINX_HOST>/v1`)

---

## Gateway Routing Overview

| Prefix / Path | Upstream Service | Protocol & Auth |
|---------------|------------------|-----------------|
| `/api/v1/*` | FastAPI Backend (`:8080`) | HTTPS (REST + SSE), no authentication |
| `/v1/*` | LiteLLM Proxy (`:4000`) | HTTPS (OpenAI API), `Bearer <key>` or `Authorization` header |
| `/key/*` | LiteLLM Proxy (`:4000`) | HTTPS, Master Key (`Bearer <LITELLM_MASTER_KEY>`) |
| `/grafana/*` | Grafana (`:3000`) | HTTPS, Basic Auth / Cookie session |
| `/health` | FastAPI Backend (`:8080`) | HTTPS, Public |
| `/docs`, `/redoc` | FastAPI Backend (`:8080`) | HTTPS, Public |
| `/metrics` | FastAPI Backend (`:8080`) | HTTPS, Prometheus scrape format |

## 1. Platform Code Assistant (Streaming Chat)

### Stream Chat Response

Sends a prompt to the AI assistant with persistent multi-turn session tracking. Emits real-time tokens via Server-Sent Events (SSE). 

> **SSE Configuration:** Nginx is configured with `proxy_buffering off` and `chunked_transfer_encoding off` to guarantee zero-latency token delivery.

```http
POST /api/v1/chat
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

## 2. Chat Session Management

### List Sessions

Retrieves chat sessions associated with the authenticated user with pagination, sorted by last updated timestamp in descending order.

```http
GET /api/v1/sessions?limit=20&offset=0
```

**Query Parameters:**

| Parameter | Type | Default | Validation | Description |
|-----------|------|---------|------------|-------------|
| `limit` | `integer` | `20` | `1 <= limit <= 100` | Maximum number of sessions to return |
| `offset` | `integer` | `0` | `offset >= 0` | Number of sessions to skip for pagination |

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

Fetches a specific session along with a paginated slice of historical messages in chronological order.

```http
GET /api/v1/sessions/{session_id}?limit=50&offset=0
```

**Query Parameters:**

| Parameter | Type | Default | Validation | Description |
|-----------|------|---------|------------|-------------|
| `limit` | `integer` | `50` | `1 <= limit <= 100` | Maximum number of historical messages to return |
| `offset` | `integer` | `0` | `offset >= 0` | Number of messages to skip for pagination |

**Response** `200 OK`:
```json
{
  "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "title": "Write a thread-safe LRU Cache in Python...",
  "created_at": "2026-08-18T09:00:00Z",
  "updated_at": "2026-08-18T09:05:30Z",
  "total_messages": 2,
  "limit": 50,
  "offset": 0,
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
```

**Response** `204 No Content` (Empty Body)

## 3. OpenAI Compatible API (Continue.dev & IDEs)

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

## 4. System & Infrastructure Endpoints

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

## Authentication

The platform API (`/api/v1/*`) has **no authentication**. This is a single-user
local deployment: there is one implicit user and every session belongs to them.

The LiteLLM passthrough (`/v1/*`) is separate and still expects
`Authorization: Bearer <LITELLM_MASTER_KEY>` — that is LiteLLM's own auth, used
by Continue.dev and any other OpenAI-compatible client.

> Because `/api/v1/*` is unauthenticated, anything that can reach the gateway can
> read and delete all chat history. Keep the host's port 80/443 bound to
> localhost, or put a guard in front of it before exposing it to a network.

---

## Error Codes Reference

| HTTP Status | Error Type | Cause |
|-------------|------------|-------|
| `400 Bad Request` | Bad Request | Malformed payload or validation error |
| `404 Not Found` | Not Found | Session not found |
| `422 Unprocessable Entity` | Schema Error | Pydantic model validation failure |
| `500 Internal Server Error` | Server Error | Unhandled exception (traceback logged, generic JSON returned) |
| `502 Bad Gateway` | Gateway Error | Upstream container (backend / vLLM / litellm) initializing or down |
