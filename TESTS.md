# Testing Guide & Architecture

This document details the test framework, testing philosophy, directory structure, and execution strategies for the **On-Prem AI Code Platform**.

---

## 1. Testing Philosophy & Tiered Pyramid

The testing strategy follows a tiered pyramid designed for high confidence, sub-second feedback loops, and zero external service dependencies during test execution:

```
                  ┌──────────────────────┐
                  │      E2E Tests       │   (7 tests)
                  │  Real vLLM/LiteLLM   │
                  ├──────────────────────┤
                  │  Integration Tests   │   (22 tests)
                  │ FastAPI + SQLite DB  │
                  ├──────────────────────┤
                  │      Unit Tests      │   (69 tests)
                  │ Pure Business Logic  │
                  └──────────────────────┘
```

1. **Unit Tests (`tests/unit/`)** — Fast, isolated tests for pure business logic. All database calls and HTTP requests to LiteLLM are mocked. No database or network connection required.
2. **Integration Tests (`tests/integration/`)** — Tests the full FastAPI HTTP routing, dependency injection container, database transaction lifecycle, and response serialization using an in-memory SQLite database (`aiosqlite`). External inference is mocked at the network boundary.
3. **End-to-End Tests (`tests/e2e/`)** — Simulates realistic multi-step user workflows (provisioning $\rightarrow$ identity validation $\rightarrow$ streaming chat sessions $\rightarrow$ autocomplete $\rightarrow$ teardown) and security error matrices. Unlike the tiers above, these call **real LiteLLM and vLLM** — they are the only place inference is not mocked, and they fail loudly rather than skipping when that stack is unavailable.

---

## 2. Directory Structure

All tests live outside `src/` in the top-level `tests/` directory:

```
tests/
├── __init__.py
├── conftest.py                      # Global fixtures, deterministic UUIDs, & entity models
├── unit/                            # Unit test suite (@pytest.mark.unit)
│   ├── __init__.py
│   ├── test_auth_service.py         # AuthService provision, key auth, 401/403 errors
│   ├── test_session_service.py      # SessionService list, detail, deletion, 404s
│   ├── test_chat_service.py         # ChatService session creation, auto-heal, SSE format
│   ├── test_autocomplete_service.py # AutocompleteService FIM prompt & /v1/completions call
│   ├── test_controllers.py          # Auth, Session, Chat, and Autocomplete controllers
│   ├── test_mappers.py              # EntityMapper model-to-schema transformations
│   ├── test_sse.py                  # SSE event serializer utility
│   ├── test_schemas.py              # Pydantic validation rules and schema constraints
│   ├── test_settings.py             # AppSettings parsing & dynamic URL generation
│   ├── test_di_container.py         # DI wiring not reachable via overridden fixtures
│   └── test_main.py                 # App lifespan & global exception handler
├── integration/                     # Integration test suite (@pytest.mark.integration)
│   ├── __init__.py
│   ├── conftest.py                  # In-memory async SQLite engine & client fixtures
│   ├── test_auth_routes.py          # /api/v1/auth/provision & /api/v1/auth/me
│   ├── test_session_routes.py       # /api/v1/sessions CRUD endpoints
│   ├── test_chat_routes.py          # /api/v1/chat SSE stream & message persistence
│   ├── test_autocomplete_routes.py  # /api/v1/autocomplete FIM completion endpoint
│   └── test_health.py               # /health endpoint verification
└── e2e/                             # End-to-End test suite (@pytest.mark.e2e)
    ├── __init__.py
    ├── conftest.py                  # E2E test client fixture
    ├── test_user_journey.py         # Complete provision -> chat -> autocomplete -> cleanup flow
    └── test_error_flows.py          # Unauthorized & 404 error matrices
```

---

## 3. Test Suites & Coverage Breakdown

### Suite Overview

| Suite | Marker | Focus Area | Test Count |
|-------|--------|------------|:----------:|
| **Unit** | `unit` | Business logic, edge cases, error branching, schema parsing | **69** |
| **Integration** | `integration` | API routes, status codes, dependency injection, DB queries, pagination | **22** |
| **E2E** | `e2e` | Multi-step client journeys, auth protection matrix | **7** |
| **Total** | | | **98 (100% pass rate)** |

> The **7 e2e tests require the live `vllm-test`/`litellm-test` stack** and fail
> fast if it is unreachable — see §5. The 91 unit + integration tests run
> standalone with no external services and are the source of the matrix below.

### Coverage Matrix

```
Name                                                 Stmts   Miss  Cover
------------------------------------------------------------------------
src/config/settings.py                                  35      0   100%
src/controller/auth_controller.py                       10      0   100%
src/controller/autocomplete_controller.py                8      0   100%
src/controller/chat_controller.py                       10      0   100%
src/controller/session_controller.py                    13      0   100%
src/db/connection.py                                     7      0   100%
src/db/interfaces/repositories.py                        5      0   100%
src/db/repositories/session_repository.py               47      0   100%
src/db/repositories/user_repository.py                  17      0   100%
src/di/container.py                                     45      0   100%
src/main.py                                             30      0   100%
src/models/entities.py                                  30      0   100%
src/routes/api.py                                       10      0   100%
src/routes/auth_routes.py                               12      0   100%
src/routes/autocomplete_routes.py                        9      0   100%
src/routes/chat_routes.py                                9      0   100%
src/routes/session_routes.py                            16      0   100%
src/schemas/autocomplete.py                              6      0   100%
src/schemas/chat.py                                      7      0   100%
src/schemas/session.py                                  10      0   100%
src/schemas/user.py                                      4      0   100%
src/services/implementations/auth_service.py            30      0   100%
src/services/implementations/autocomplete_service.py    29      0   100%
src/services/implementations/chat_service.py            51      0   100%
src/services/implementations/session_service.py         23      0   100%
src/services/interfaces/services.py                     12      0   100%
src/utils/mappers.py                                    15      0   100%
src/utils/sse.py                                         6      0   100%
------------------------------------------------------------------------
TOTAL                                                  508      0   100%
```

---

## 4. Running Tests Locally

### Prerequisites

Activate the virtual environment and ensure test dependencies are installed:

```bash
# Windows
.\venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

# Install test dependencies
pip install -r requirements.txt
```

### Running Test Commands

```bash
# Run everything that works without external services (91 tests, 100% coverage)
pytest tests/unit tests/integration -v

# Run by tier using pytest markers
pytest tests/unit/ -v -m unit
pytest tests/integration/ -v -m integration

# Run with coverage report in terminal
pytest tests/unit tests/integration --cov=src --cov-report=term-missing

# Run with HTML coverage report (generates htmlcov/index.html)
pytest tests/unit tests/integration --cov=src --cov-report=html
```

> **E2E tests are not runnable this way.** `pytest tests/e2e` calls real
> LiteLLM/vLLM and will fail immediately with
> `Live inference stack unreachable at ...` unless the Docker stack from §5 is
> up. This is deliberate — they fail loudly rather than skipping silently, so a
> green run never overstates what was actually verified. Use the Docker command
> in §5 to run the full suite including e2e.

---

## 5. Dockerized Testing Environment

An isolated, reproducible Docker Compose configuration is provided in [`docker-compose.test.yaml`](file:///c:/Users/tamir/Desktop/ai-code-platform/docker-compose.test.yaml).

### Architecture

```
              ┌─────────────────────────────────────────┐
              │         test-runner (pytest)            │
              │      FastAPI App + Test Suites          │
              └───┬──────────────┬──────────────┬───────┘
                  │              │              │
        (Postgres 5433)   (Redis 6380)   (LiteLLM 4000)
                  │              │              │
                  ▼              ▼              ▼
        ┌─────────────────┐ ┌───────────┐ ┌──────────────┐
        │  postgres-test  │ │redis-test │ │ litellm-test │
        │  (Postgres 16)  │ │  (Stack)  │ │   (proxy)    │
        │  tmpfs storage  │ └───────────┘ └──────┬───────┘
        └─────────────────┘                      │
                                          (vLLM 8000)
                                                 ▼
                                        ┌──────────────────┐
                                        │    vllm-test     │
                                        │ Qwen2.5-Coder-   │
                                        │ 0.5B-Instruct    │
                                        │    (CPU-only)    │
                                        └──────────────────┘
```

- **`postgres-test`**: Dedicated PostgreSQL 16 instance with automated healthcheck (`pg_isready`) and in-memory `tmpfs` volume for high I/O speed.
- **`redis-test`**: Isolated Redis Stack instance on port `6380`.
- **`vllm-test`**: Real vLLM OpenAI-compatible server built CPU-only from
  [`docker/vllm-cpu.Dockerfile`](docker/vllm-cpu.Dockerfile), serving
  `Qwen/Qwen2.5-Coder-0.5B-Instruct` under the name `qwen-coder`. Model weights
  are cached in the `hf_cache_test` volume so repeat runs skip the download.
  **First build compiles vLLM from source and is slow (tens of minutes);** the
  healthcheck allows a 300s `start_period` for CPU model load.
- **`litellm-test`**: LiteLLM proxy fronting `vllm-test`, configured by
  [`litellm/config.test.yaml`](litellm/config.test.yaml). This is what issues the
  real virtual API keys that e2e provisioning asserts against.
- **`test-runner`**: Runs `entrypoint.sh` (which executes `alembic upgrade head` migrations on the test database) followed by pytest.

Healthchecks are chained `vllm-test` → `litellm-test` → `test-runner`, so pytest
does not start until real inference is actually serving.

### Running Tests in Docker

```bash
# Execute entire test suite inside isolated Docker containers
docker compose -f docker-compose.test.yaml up --build --abort-on-container-exit --exit-code-from test-runner

# Tear down test containers and volumes
docker compose -f docker-compose.test.yaml down -v
```

---

## 6. Shared Fixtures & Utilities

Defined in [`tests/conftest.py`](file:///c:/Users/tamir/Desktop/ai-code-platform/tests/conftest.py) for reuse across all test files:

- **`mock_user_entity`**: Pre-instantiated `UserEntity` with fixed UUID `a1111111-1111-1111-1111-111111111111`, username `"testuser"`, and API key `"sk-test-key-abc123"`.
- **`mock_session_entity`**: Pre-instantiated `SessionEntity` linked to the test user.
- **`mock_message_entity`**: Pre-instantiated `MessageEntity` linked to the test session.

Integration tests in [`tests/integration/conftest.py`](file:///c:/Users/tamir/Desktop/ai-code-platform/tests/integration/conftest.py) provide:
- **`client`**: Unauthenticated `httpx.AsyncClient` wired to the FastAPI application with in-memory SQLite database.
- **`authenticated_client`**: `httpx.AsyncClient` with the `get_authenticated_user` dependency overridden to automatically authenticate requests.
- **`seeded_user`**: Inserts a test user into the in-memory database before the test runs.

---

## 7. Writing New Tests

When adding new features, follow these conventions:

1. **New Service Method**: Add unit tests in `tests/unit/test_<name>_service.py`. Mock all repository and external client interactions.
2. **New Endpoint**: Add integration tests in `tests/integration/test_<name>_routes.py`. Use `authenticated_client` for protected endpoints and test both 200/201 happy paths and 4xx error cases.
3. **New User Flow**: Add an end-to-end scenario in `tests/e2e/test_user_journey.py`.
4. **Markers**: Ensure every test file defines its marker at module level:
   ```python
   pytestmark = pytest.mark.unit         # for unit tests
   pytestmark = pytest.mark.integration  # for integration tests
   pytestmark = pytest.mark.e2e          # for e2e tests
   ```
