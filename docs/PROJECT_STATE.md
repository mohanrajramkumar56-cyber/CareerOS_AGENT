# CareerOS — Project State

**Last Updated:** 2026-10-01

---

## Current Phase: PHASE 1 — CANDIDATE INTELLIGENCE (Complete)

---

## What Is Built

### Phase 0 — Foundation ✅
- [x] Monorepo structure, `.env.example`, `.gitignore`
- [x] Docker Compose (production + development)
- [x] PostgreSQL init with uuid-ossp, pgcrypto, vector extensions
- [x] GitHub Actions CI (API tests, frontend build, security scan)
- [x] FastAPI application with CORS, correlation IDs, Prometheus metrics
- [x] JWT authentication (access + refresh tokens, bcrypt)
- [x] User + UserSession ORM models
- [x] Alembic migration setup
- [x] Next.js 14 frontend with dashboard layout
- [x] Health `/health`, readiness `/ready`, metrics `/metrics` endpoints
- [x] 22 tests, 71.93% coverage

### Phase 1 — Candidate Intelligence ✅

#### Domain Layer
- [x] `EvidenceStrength` enum: VERIFIED / STRONG / MODERATE / WEAK / UNKNOWN
- [x] `FactCategory` enum: skill, experience, education, project, certification, achievement, technology, responsibility, language, publication, volunteer
- [x] `EvidenceSourceType` enum: resume, work_history, project, git_repository, portfolio, certificate, uploaded_document, user_confirmation, linkedin, github, external_link
- [x] Evidence validation rules (deterministic, no LLM)
- [x] `validate_evidence()` — returns strength + errors + warnings
- [x] `can_claim_be_used()` — enforces truth policy
- [x] `requires_human_review()` — flags weak evidence
- [x] `classify_gap()` — skill_gap vs representation_gap
- [x] `_aggregate_strength()` — strongest-evidence wins

#### ORM Models
- [x] `CandidateProfile` — identity, contact, location, preferences, authorization
- [x] `Education` — institution, degree, field, dates, GPA
- [x] `Experience` — company, title, dates, duration_months computed
- [x] `Skill` — name, category, proficiency, unique per candidate
- [x] `Project` — name, description, URLs, technologies
- [x] `Certification` — name, issuer, dates, credential URL
- [x] `Achievement` — title, description, issuer, date
- [x] `CandidateFact` — claim, category, evidence_strength aggregate
- [x] `Evidence` — source_type, source_reference, strength, status

#### Alembic Migration
- [x] `0001_initial_schema.py` — all 11 tables with indexes, FKs, constraints

#### Pydantic Schemas
- [x] Create/Update/Response schemas for all 9 entities
- [x] `CandidateProfileFull` — nested full profile response
- [x] `CandidateFactCreate` — fact + evidence in one request
- [x] Salary fields excluded from default response (privacy)

#### Service Layer
- [x] Profile CRUD (create, get by user, full load with eager joins, update)
- [x] Education, Experience, Skill, Project, Certification, Achievement CRUD
- [x] `create_fact()` — creates fact + evidence, computes aggregate strength
- [x] `add_evidence_to_fact()` — recomputes aggregate on each addition
- [x] Soft delete for all entities
- [x] Duration months computed automatically for Experience

#### API Endpoints (31 routes)
- [x] `POST/GET/PUT /candidates/profile` — profile management
- [x] `GET /candidates/profile/full` — nested full profile
- [x] `POST/GET/PUT/DELETE /candidates/education/{id}` — 4 routes
- [x] `POST/GET/PUT/DELETE /candidates/experiences/{id}` — 4 routes
- [x] `POST/GET/DELETE /candidates/skills/{id}` — 3 routes
- [x] `POST/GET/PUT/DELETE /candidates/projects/{id}` — 4 routes
- [x] `POST/GET/DELETE /candidates/certifications/{id}` — 3 routes
- [x] `POST/GET/DELETE /candidates/achievements/{id}` — 3 routes
- [x] `POST/GET /candidates/facts` + `GET/POST /candidates/facts/{id}` + `POST /candidates/facts/{id}/evidence` — 5 routes

#### Security
- [x] All candidate routes require authentication
- [x] Resource scoped to owning user — cross-user access returns 404
- [x] Duplicate profile returns 409
- [x] Duplicate skill returns 409

#### Tests
- [x] 35 unit tests — evidence domain logic (all cases)
- [x] 34 integration tests — all candidate API endpoints
- [x] Cross-user isolation tested
- [x] Truth policy enforced: UNKNOWN facts created correctly
- [x] Evidence strength upgrade on adding evidence tested
- [x] **91 total tests, 75.14% coverage**

#### Frontend (Phase 1)
- [x] Profile page with identity, skills with evidence badges, evidence facts
- [x] EvidenceBadge component showing strength visually
- [x] Truth policy warning banner for UNKNOWN facts
- [x] Jobs page skeleton (Phase 2 placeholder)
- [x] Applications page skeleton (Phase 5 placeholder)
- [x] API client utility (`lib/api.ts`)

---

## What Is NOT Yet Built

| Phase | Status |
|-------|--------|
| Phase 2: Job Intelligence | Pending |
| Phase 3: Matching Engine | Pending |
| Phase 4: Resume Engine | Pending |
| Phase 5: Application Engine | Pending |
| Phase 6: Policy + Security | Pending |
| Phase 7: Email + Follow-up | Pending |
| Phase 8: Dashboard (full) | Pending |
| Phase 9: Observability | Pending |
| Phase 10: Production Hardening | Pending |
| Phase 11: End-to-End Validation | Pending |

---

## Phase 1 Definition of Done ✅

- [x] Candidate can be fully represented with verified structured evidence
- [x] Evidence graph enforces truth policy (UNKNOWN ≠ usable)
- [x] All sub-resources (education, experience, skills, projects, certs, achievements) persist and are retrievable
- [x] Cross-user isolation enforced
- [x] 91 tests passing, 75.14% coverage (≥70% threshold)
- [x] Frontend profile page renders evidence strength visually
- [x] Alembic migration ready for real PostgreSQL deployment
