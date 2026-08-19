# Live E2E Testing Against Real vLLM/LiteLLM + Autocomplete Feature

## Context

The current e2e suite (`tests/e2e/test_user_journey.py`) simulates the full user
journey (provision → auth → chat → sessions → tasks → cleanup) but mocks every
call to LiteLLM at the `httpx.AsyncClient` boundary. `docker-compose.test.yaml`
only runs `postgres-test` and `redis-test` — there is no LiteLLM or vLLM in the
test stack at all. Overall coverage sits at 91% (`pytest --cov=src`), with real
gaps in `worker/celery_app.py` (45%), `worker/tasks.py` (26%),
`db/repositories/task_repository.py` (70%), `db/repositories/user_repository.py`
(82%), `di/container.py` (96%), `main.py` (76%), and `chat_service.py` (94%).
`TESTS.md`'s coverage table is stale — it omits the `worker/` package entirely.

There is also no autocomplete feature anywhere in the codebase today. The only
async task is `batch_code_review` (Celery-based, reviews whole files).

## Goals

1. Add a real autocomplete feature (new backend capability, not just tests).
2. Make e2e tests hit **real** LiteLLM + vLLM for both the chat-session flow
   and the new autocomplete flow — no mocking of the inference call itself.
3. Reach 100% statement coverage across `src/`.

## Non-goals

- No changes to the async Celery `batch_code_review` task's behavior.
- No production/dev compose changes — `docker-compose.dev.yaml` and
  `docker-compose.prod.yaml` are untouched; only `docker-compose.test.yaml`
  gains live inference services.
- No UI/IDE integration work (Continue.dev config etc.) — this is
  backend + tests only.

## 1. Autocomplete feature

**Endpoint:** `POST /api/v1/autocomplete`, synchronous, `X-API-Key` auth,
mirrors the existing chat endpoint's structure but returns a single JSON
response (no SSE).

**Schemas** (`src/schemas/autocomplete.py`):

```python
class AutocompleteRequest(BaseModel):
    prefix: str
    suffix: str = ""
    language: str | None = None

class AutocompleteResponse(BaseModel):
    completion: str
```

**Service** (`src/services/implementations/autocomplete_service.py`):
builds a fill-in-the-middle prompt using Qwen2.5-Coder's native FIM tokens:

```
<|fim_prefix|>{prefix}<|fim_suffix|>{suffix}<|fim_middle|>
```

and calls `POST {LITELLM_URL}/v1/completions` (the raw completions endpoint —
not `/v1/chat/completions`, so no chat template is applied) with:

```json
{"model": "<DEFAULT_CODE_MODEL>", "prompt": "<fim prompt>", "max_tokens": 128, "temperature": 0.1}
```

Response is parsed from `choices[0].text`. Same `Authorization: Bearer
{user.api_key}` pattern as `ChatService`.

**Wiring**, following the exact pattern chat/session/task already use:
- `IAutocompleteService` added to `src/services/interfaces/services.py`
- `AutocompleteController` in `src/controller/`
- `autocomplete_routes.py` mounted into `src/routes/api.py`
- `get_autocomplete_service` / `get_autocomplete_controller` added to
  `src/di/container.py`

## 2. Live test infrastructure

`docker-compose.test.yaml` gains two new services:

- **`vllm-test`** — real vLLM OpenAI-compatible server, CPU-only, serving
  `Qwen/Qwen2.5-Coder-0.5B-Instruct` (small enough for CPU inference in a test
  run). vLLM's public `vllm/vllm-openai` image is CUDA-only, so this needs a
  CPU-specific image — either a custom `docker/vllm-cpu.Dockerfile` built from
  vLLM's own `docker/Dockerfile.cpu` path, or a pinned vLLM release with a
  working CPU wheel (`VLLM_TARGET_DEVICE=cpu`). This is the one open technical
  risk in the plan: the exact CPU build approach will be validated during
  implementation, and the vLLM version pinned to whichever is confirmed
  working — it stays real vLLM either way, never a substitute inference
  server.
- **`litellm-test`** — same `ghcr.io/berriai/litellm` image as
  `docker-compose.dev.yaml`, config pointing at `vllm-test:8000` (new
  `litellm/config.test.yaml` if the model base/name needs to differ from the
  prod config).
- Chained healthchecks: `vllm-test` → `litellm-test` → `test-runner`, with a
  generous `start_period` (CPU model load is slow) — `service_healthy`
  conditions throughout, same style as `postgres-test`/`redis-test` today.
- `test-runner` gets `LITELLM_URL=http://litellm-test:4000` and a real
  `LITELLM_MASTER_KEY` in its environment, replacing today's fully-mocked
  values.
- Model weights cached in a volume (mirroring dev's `./data/hf_cache`) so
  repeated local runs skip re-downloading.

**Reachability is a hard requirement, not optional:** if `vllm-test`/
`litellm-test` are not reachable when the live e2e tests run (e.g. someone
runs `pytest tests/e2e` outside Docker), those tests **fail** with a clear
connection error — they do not silently skip. `docker compose -f
docker-compose.test.yaml up --build --abort-on-container-exit
--exit-code-from test-runner` remains the supported way to get a fully-passing,
100%-coverage run.

## 3. E2E test changes

- `tests/e2e/test_user_journey.py`: remove the `httpx.AsyncClient` mock on the
  chat step so the request flows through real LiteLLM → real vLLM and streams
  real SSE tokens; assertions check response well-formedness and non-empty
  content (exact text isn't assertable against a real model). The auth
  provisioning step (`POST /api/v1/auth/provision`, which calls LiteLLM's
  `/key/generate`) also drops its mock, so the whole
  provision → auth → chat chain is real end-to-end.
- A new step is added to the same journey: `POST /api/v1/autocomplete` with a
  real prefix/suffix, asserting a real non-empty `completion` string comes
  back.
- `tests/e2e/conftest.py`: add a startup check that hits LiteLLM's health
  endpoint and raises immediately with a clear message if unreachable, rather
  than failing deep inside a test with a bare connection-refused trace.
- Celery/task steps in the same journey stay mocked — out of scope here.

## 4. Coverage gap closure (→ 100%)

| File | Gap | Plan |
|---|---|---|
| `db/repositories/task_repository.py` | `update_status` untested | New unit test: found/not-found task, `result=None` vs dict |
| `db/repositories/user_repository.py` | `create` untested | New unit test |
| `di/container.py` | `get_task_repository` untested | Cover via existing/new task route test path |
| `main.py` | lifespan shutdown, global exception handler untested | Integration test hitting a route that raises, plus app-shutdown assertion |
| `services/implementations/chat_service.py` | malformed-chunk skip branch, JSON-parse-exception branch | Extend `test_chat_service.py` with malformed SSE input |
| `worker/celery_app.py` | signal handlers / `_sync_update_task_status` (45%) | New `tests/unit/test_celery_app.py`, mock `psycopg2` |
| `worker/tasks.py` | `batch_code_review_task` has no unit test (26%) | New `tests/unit/test_worker_tasks.py`, mock `httpx.Client` |
| new autocomplete code | n/a (doesn't exist yet) | Full unit + integration coverage as written |

**Exception:** `main.py`'s `if __name__ == "__main__": uvicorn.run(...)` guard
is excluded via `# pragma: no cover` — standard practice for a script
entrypoint that isn't meaningfully unit-testable without spawning a real
process.

## Testing strategy summary

- **Unit** (`tests/unit/`): new tests for `task_repository`, `user_repository`,
  `celery_app`, `worker/tasks`, `autocomplete_service`, plus edge-case
  additions to `chat_service`. Everything here stays mocked at the network/DB
  boundary, per existing convention.
- **Integration** (`tests/integration/`): new `test_autocomplete_routes.py`
  following the existing pattern (mocked LiteLLM at the network boundary,
  real in-memory SQLite).
- **E2E** (`tests/e2e/`): the one place real LiteLLM/vLLM calls happen, wired
  through the new `docker-compose.test.yaml` services.
