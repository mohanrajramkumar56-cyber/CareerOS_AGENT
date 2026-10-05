# Data Retention

This document describes what data CareerOS stores, how long it is retained, how deletion works, and user rights regarding their data.

---

## What Data Is Stored

| Data type | Where stored | Description |
|---|---|---|
| Candidate profile | PostgreSQL | Name, contact details, preferences, skills |
| Evidence items | PostgreSQL | Work history, credentials, certificates, achievements |
| Job postings | PostgreSQL | Discovered and normalized job listings |
| Match results | PostgreSQL | Eligibility and fit scores per candidate × job |
| Applications | PostgreSQL | Application state, history, and correspondence |
| Resumes | PostgreSQL + artifact storage | Generated resume metadata and PDF/DOCX files |
| Emails | PostgreSQL | Classified incoming emails linked to applications |
| Browser screenshots | Artifact storage | Screenshots captured during automation sessions |
| Audit logs | PostgreSQL | Immutable record of all system and agent actions |
| Structured logs | Log aggregation system | Application-level request and error logs |

---

## Retention Policies

### Audit logs — Permanent

Audit logs are immutable by design. They record every agent action, policy decision, and user-triggered event. They are never automatically deleted. This ensures that the history of any automated action (including application submissions) can always be reviewed.

Deletion of audit logs requires a manual database operation by a system administrator and must not be done without the user's explicit request and confirmation.

### Emails — 90 days (unless linked to active application)

Processed emails are retained for 90 days from the date they were received. Emails that are linked to an active or pending job application are retained until the application reaches a terminal state (hired, rejected, withdrawn, or abandoned), after which the standard 90-day window applies from the terminal date.

### Browser screenshots — 30 days

Screenshots captured during browser automation sessions are retained for 30 days. After 30 days they are eligible for deletion from artifact storage. Screenshots linked to an open support issue or under active review are exempt until the issue is resolved.

### Resume artifacts — 1 year, or until deleted by user

Generated resume PDF and DOCX files are retained for 1 year from the generation date. Users may delete individual resume artifacts at any time via the UI or API. Deleting a candidate profile cascades to all resume artifacts owned by that profile.

### Application-level log records — 1 year

Structured application log records in the log aggregation system are retained on a 30-day rolling window in standard deployments. Operators may configure a longer retention period in their log aggregation service (CloudWatch, Loki, Datadog, etc.) independently of this policy.

### Candidate profile and all owned data

A soft-deleted candidate profile is retained in the database for 30 days to allow recovery, then permanently purged. Permanent deletion cascades to all data owned by that profile: evidence items, match results, applications, resumes, emails, and browser screenshots. Audit logs referencing the deleted candidate are anonymized (candidate ID replaced with a tombstone value) rather than deleted, to preserve the integrity of the audit trail.

---

## Deletion

### User-initiated deletion

Users may delete their account (candidate profile) at any time. This triggers:

1. Soft-delete on the candidate profile record
2. Immediate revocation of all active sessions
3. Queuing of a cascading hard-delete job to run after the 30-day grace period
4. Deletion of resume artifact files from storage (immediate, not deferred)

Individual data items (specific resumes, specific emails, specific applications) can also be deleted independently without deleting the entire account.

### Automated cleanup

Automated retention enforcement (purging screenshots after 30 days, purging expired emails, etc.) is **not yet implemented**. These operations are currently performed manually.

Automated cleanup is on the backlog. Until it is implemented, operators should run periodic cleanup queries against the database and artifact storage to enforce the policies above.

---

## GDPR and Data Subject Rights

CareerOS is designed to support data subject rights under GDPR and similar regulations.

### Right to access (data export)
Users may request a full export of all data held about them. The export covers: profile, evidence, jobs, applications, resumes, and emails. Browser screenshots and audit logs are included on request.

**Current status**: Export must be prepared manually by an administrator via database query. A self-service export endpoint is on the backlog.

### Right to erasure (right to be forgotten)
Users may request deletion of all their data. Follow the user-initiated deletion process above. Audit logs are anonymized rather than deleted (preserving system integrity while removing the link to the individual).

**Current status**: Account deletion via the API cascades to owned data as described. The 30-day deferred purge is enforced manually.

### Right to rectification
Users may update their profile and evidence items at any time through the UI or API. Changes to evidence items trigger re-validation of any resumes generated from that evidence.

### Data portability
Exported data is provided in JSON format (structured data) and original file format (resume PDFs, DOCX files).

---

## Implementation Status

| Policy | Status |
|---|---|
| Soft-delete on profile with cascade | Implemented |
| Immediate resume artifact deletion on request | Implemented |
| 30-day deferred hard-delete after soft-delete | Manual — automated purge on backlog |
| 90-day email expiry | Manual — automated purge on backlog |
| 30-day screenshot expiry | Manual — automated purge on backlog |
| 1-year resume artifact expiry | Manual — automated purge on backlog |
| Self-service data export endpoint | On backlog |
| Audit log anonymization on profile deletion | On backlog |
