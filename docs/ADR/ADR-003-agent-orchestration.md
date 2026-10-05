# ADR-003: Agent Orchestration Architecture

## Status
Accepted

## Context
CareerOS requires multiple AI-assisted steps (job discovery, matching, resume generation, application automation, email classification). A single monolithic agent would be fragile, unauditable, and difficult to test.

## Decision
Use specialized, purpose-scoped agents rather than one general agent. Each agent operates through a controlled tool interface. Agents recommend — deterministic systems execute.

## Architecture
```
Career Orchestrator
├── Job Discovery Agent — discovers and normalizes jobs
├── Job Analysis Agent — extracts requirements
├── Candidate Intelligence Agent — manages evidence graph
├── Matching Agent — scores eligibility and fit
├── Resume Agent — generates truth-validated resumes
├── Application Agent — prepares and monitors applications
├── Email Intelligence Agent — classifies incoming email
├── Follow-up Agent — schedules follow-up messages
└── Notification Agent — delivers notifications
```

## Consequences
- Each agent is independently testable
- Failures are isolated
- Audit trail is per-agent-run
- LLMs cannot bypass the policy engine
