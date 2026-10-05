# Security

This document describes the security model for CareerOS. It covers authentication, authorization, data isolation, secret management, and defensive measures.

---

## Authentication

CareerOS uses JWT (JSON Web Tokens) for stateless API authentication.

- Tokens are signed using a secret key (`JWT_SECRET_KEY` in `.env`)
- Token expiry is configurable (`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, default 30 minutes)
- Passwords are hashed with bcrypt before storage — plaintext passwords are never persisted
- There is no password recovery path that bypasses bcrypt verification
- Token refresh is handled via a separate `/auth/refresh` endpoint

All protected endpoints require a valid `Authorization: Bearer <token>` header. Requests without a valid token receive `401 Unauthorized`.

---

## Authorization

All resources (jobs, applications, resumes, emails, audit logs) are scoped to the authenticated user.

- Every database query filters by `candidate_id` or `user_id` tied to the token subject
- Cross-user data access is prevented at the query layer — there is no admin bypass path in the application code
- Resource ownership is verified before any read, write, or delete operation
- A user cannot enumerate other users' resources

---

## Prompt Injection Defense

CareerOS processes untrusted content (job descriptions, emails, web pages) through LLMs. The following controls are applied:

- Untrusted content is clearly delimited with structural markers in all prompts (e.g., `<job_description>`, `<email_body>`) to prevent instruction bleeding
- LLM outputs are validated against expected schemas before use — free-form LLM text never directly drives system actions
- Agents recommend; deterministic systems execute. An LLM cannot directly call tools, write files, submit forms, or send emails
- Prompt templates are version-controlled and reviewed as code
- Responses that fail schema validation are logged and the task is failed safely, not retried with relaxed validation

---

## Email Content Isolation

Incoming emails are treated as fully untrusted content.

- Email bodies are processed only inside isolated LLM classification calls
- Email content is never rendered as HTML in the UI without explicit sanitization
- Email addresses and links extracted from emails are not automatically acted upon — they require agent confirmation
- The email processing pipeline never executes attachments
- Extracted data is validated before being stored or used downstream

---

## Browser Isolation

Each browser automation session runs in a fully isolated Playwright browser context.

- One browser context per application session — no cookie or session state is shared between applications
- Browser contexts are destroyed after each session completes or fails
- `BROWSER_TEST_MODE=true` by default — no real form submissions occur unless explicitly disabled
- Human takeover is required for: CAPTCHA challenges, legal agreements, payment requests, and authentication challenges
- Screenshots are taken at pause points and stored via the authenticated artifact storage backend
- The browser automation worker never stores credentials in the browser profile

---

## Secret Management

- All secrets are stored in `.env` files and injected as environment variables at runtime
- `.env` is listed in `.gitignore` — it must never be committed to version control
- `.env.example` contains placeholder values only (no real secrets)
- Secrets required in production: `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `SECRET_KEY`, and optionally `OPENAI_API_KEY`, `SMTP_PASSWORD`, `S3_SECRET_ACCESS_KEY`
- In production, prefer a secrets manager (AWS Secrets Manager, HashiCorp Vault) over file-based `.env`
- Rotate `JWT_SECRET_KEY` if it is ever exposed — all active sessions will be invalidated

---

## Security Headers

The FastAPI application sets the following HTTP security headers on all responses:

| Header | Value |
|---|---|
| `Content-Security-Policy` | `default-src 'self'` (tightened per endpoint as needed) |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |

CORS is configured to allow only the frontend origin (`FRONTEND_URL` env var). Wildcard CORS origins are not permitted in production.

---

## Rate Limiting

API endpoints are rate-limited using a sliding window approach backed by Redis.

- Default limit: 100 requests per minute per authenticated user
- Auth endpoints (`/auth/login`, `/auth/register`): 10 requests per minute per IP
- Browser automation trigger endpoints: 5 concurrent sessions system-wide
- Rate limit responses return `429 Too Many Requests` with a `Retry-After` header

---

## Input Validation

All API request bodies are validated using Pydantic models before any business logic runs.

- Field types, lengths, and formats are enforced at the schema level
- Invalid requests are rejected with `422 Unprocessable Entity` before reaching the database or AI layer
- SQL injection is prevented by SQLAlchemy's parameterized queries — raw SQL strings are not used
- File uploads (resumes, attachments) are validated for MIME type and size before storage
- Path traversal is prevented by using UUIDs as filenames for all stored artifacts

---

## Dependency Security

- Python dependencies are pinned to exact versions in `requirements.txt`
- Node.js dependencies are pinned in `package-lock.json`
- `pip audit` and `npm audit` should be run before each release
- Dependabot (or equivalent) should be configured on the repository to surface CVEs in dependencies
- Base Docker images use specific digest pins in production to prevent supply-chain substitution

---

## Reporting Security Issues

Do not open a public GitHub issue for security vulnerabilities. Email the maintainers directly with a description of the issue, reproduction steps, and potential impact.
