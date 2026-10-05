# Testing

This document describes the test structure, how to run tests, coverage requirements, and guidelines for writing new tests.

---

## Test Structure

Tests live in two locations:

```
apps/api/tests/          # Backend (Python / pytest)
apps/web/tests/          # Frontend E2E (Playwright / TypeScript)
```

### Backend test categories

| Directory / marker | What it covers |
|---|---|
| `tests/unit/` | Individual functions and classes in isolation |
| `tests/integration/` | Multiple components together (DB, queue, storage) |
| `tests/security/` | Auth bypasses, injection attempts, cross-user access |
| `tests/truth_policy/` | Truth policy enforcement — fabrication must be rejected |
| `tests/load/` | Throughput and latency benchmarks under concurrent load |
| `tests/e2e/` (backend) | Full request-to-database flows via the API |

### Frontend E2E

```
apps/web/tests/e2e/      # Playwright browser tests for critical user flows
```

---

## Running Tests

### Backend

```bash
cd apps/api

# Install dependencies (first time)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Unix:
source .venv/bin/activate

pip install -r requirements.txt aiosqlite

# Run all tests with coverage
pytest tests/ --cov=app --cov-report=term-missing

# Run a specific category
pytest tests/unit/
pytest tests/integration/
pytest tests/security/
pytest tests/truth_policy/

# Run with verbose output
pytest tests/ -v

# Run a single test file
pytest tests/unit/test_matching.py
```

SQLite (`aiosqlite`) is used as the test database — no PostgreSQL instance required to run the test suite.

### Frontend E2E

```bash
cd apps/web

npm install
npx playwright install  # first time only — installs browsers

# Run all E2E tests
npm run test:e2e

# Run with UI (headed mode)
npm run test:e2e -- --headed

# Run a specific spec
npx playwright test tests/e2e/auth.spec.ts
```

---

## Coverage Requirement

The minimum coverage threshold is **70%** for the backend.

Coverage is enforced in CI. A pull request that drops overall coverage below 70% will fail the coverage gate.

To check coverage locally:

```bash
pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=70
```

---

## Test Categories in Detail

### unit
- Pure function tests with no I/O
- Model validation logic, scoring algorithms, prompt builders, utility functions
- Must not hit the database, Redis, or any external service
- Should be fast — all unit tests should complete in under 5 seconds total

### integration
- Tests that exercise the database, Redis, or the queue together
- Use the test SQLite database (configured automatically via fixtures)
- May use mocked versions of Ollama / OpenAI responses
- Cover: CRUD operations, cascade deletes, queue task dispatch and execution

### security
- Attempt authentication bypass, token forgery, and cross-user access
- Verify that rate limiting triggers correctly
- Test prompt injection payloads in job description and email inputs
- Verify CORS headers, security headers, and input validation rejection

### truth_policy
- Verify that the Resume Agent rejects fabricated claims
- Verify that every generated resume bullet traces back to evidence in the evidence graph
- Verify that the truth validation step cannot be bypassed by LLM output

### load
- Measure throughput and latency under concurrent requests
- Run with `pytest-benchmark` or `locust` (see `tests/load/`)
- Not run in standard CI — triggered manually or in a dedicated load environment

### e2e (backend)
- Full HTTP request flows through the FastAPI application
- Use `TestClient` or `AsyncClient` from `httpx`
- Cover: registration, login, job creation, matching trigger, resume generation trigger

---

## Key Test Files

| File | What it tests |
|---|---|
| `tests/unit/test_matching.py` | Eligibility scoring and match ranking logic |
| `tests/unit/test_truth_policy.py` | Truth validation functions in isolation |
| `tests/integration/test_jobs_api.py` | Job CRUD via the REST API |
| `tests/integration/test_resume_generation.py` | Resume generation pipeline with mock LLM |
| `tests/security/test_auth.py` | JWT validation, token expiry, cross-user access |
| `tests/security/test_prompt_injection.py` | Injection payloads in untrusted content fields |
| `tests/truth_policy/test_fabrication_rejection.py` | End-to-end truth policy enforcement |
| `apps/web/tests/e2e/auth.spec.ts` | Login, registration, and session management |
| `apps/web/tests/e2e/dashboard.spec.ts` | Dashboard rendering and navigation |

---

## Writing New Tests

### Backend

1. Place the test in the appropriate category directory (`unit/`, `integration/`, `security/`, etc.)
2. Name the file `test_<feature>.py`
3. Use pytest fixtures defined in `tests/conftest.py` for database sessions, test clients, and authenticated users
4. Mock all external services (Ollama, OpenAI, SMTP) using `pytest-mock` or `unittest.mock`
5. Never use real external services — tests must pass with no network access
6. Follow Arrange / Act / Assert structure in each test function

```python
async def test_matching_rejects_ineligible_candidate(db_session, test_candidate, test_job):
    # Arrange
    test_job.requires_clearance = True
    test_candidate.has_clearance = False

    # Act
    result = await run_matching(db_session, test_candidate.id, test_job.id)

    # Assert
    assert result.eligible is False
    assert result.score == 0
```

### Frontend E2E

1. Add specs to `apps/web/tests/e2e/`
2. Use the `page` fixture from Playwright
3. Target elements by accessible role or `data-testid` attributes — never by CSS class names
4. Stub API responses using Playwright's `page.route()` for tests that should not hit a live backend
5. For tests that require a live backend, use the test environment (`TEST_BASE_URL`)

---

## External Services in Tests

**Never use real external services in tests.** This is a firm rule.

- **Database**: Use SQLite via `aiosqlite` (configured in `conftest.py`)
- **Redis**: Use `fakeredis` for unit and integration tests
- **Ollama / OpenAI**: Mock at the `ModelRouter` interface boundary
- **SMTP**: Use a mock SMTP server (e.g., `aiosmtpd` in test mode)
- **S3**: Use the `LocalStorage` backend or `moto` for S3 mocking
- **Browser / Playwright**: Run with `BROWSER_TEST_MODE=true` — no real form submissions

Tests that require real infrastructure (database migrations, actual Ollama responses) belong in a dedicated staging environment, not the standard test suite.
