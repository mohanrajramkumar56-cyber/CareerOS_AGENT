# ADR-008: Authentication

**Date:** 2026-10-01
**Status:** Accepted

## Context

CareerOS requires:
- User authentication for API access
- Secure token management
- Support for future OAuth integration
- Session revocation capability

## Decision

Use **JWT tokens** (access + refresh pattern) with **bcrypt** password hashing.

- Access tokens: short-lived (60 min default)
- Refresh tokens: stored server-side hash for revocation (30 days)
- Passwords: bcrypt with rounds=12
- JWT library: python-jose

## Rationale

- JWT is stateless for access tokens (scales horizontally)
- Refresh token stored server-side enables revocation
- bcrypt is the industry standard for password hashing
- python-jose is widely used and well-maintained

## Security Notes

- Tokens are signed with `JWT_SECRET` (must be ≥32 random bytes in production)
- Refresh tokens are hashed before storage (never store raw tokens)
- Session table enables logout/revocation
- `passlib` replaced with direct `bcrypt` (passlib 1.7.4 incompatible with bcrypt 4.x)

## Consequences

- Token rotation strategy needed for long-lived refresh tokens
- Future OAuth providers can be added alongside this system
- Token blacklisting can be added via Redis if needed

## Rejected Alternatives

- **Session cookies**: CSRF complexity, less suitable for API-first
- **API keys only**: No user identity model
- **OAuth only**: Need local identity for self-hosted deployments
