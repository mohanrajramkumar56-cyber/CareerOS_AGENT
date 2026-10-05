# ADR-004: Browser Automation

## Status
Accepted

## Context
Automating job applications requires controlled browser interaction with external career sites and ATS platforms.

## Decision
Use Playwright for browser automation. Sessions are isolated per application. Human takeover is triggered automatically on CAPTCHA, legal questions, payment requests, and auth challenges.

## Principles
- TEST_MODE=true by default — never submits real applications during tests
- One browser context per application session
- Screenshot captured at every pause/failure
- Never bypasses CAPTCHA, authentication, or anti-bot controls

## Consequences
- Headless Chromium required in production
- Browser sessions are resource-intensive (max 2 concurrent)
- Human takeover requires notification system to be working
