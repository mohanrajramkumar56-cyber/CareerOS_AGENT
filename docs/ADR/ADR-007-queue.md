# ADR-007: Background Queue

## Status
Accepted

## Context
CareerOS requires background processing for job discovery, matching, resume generation, email processing, follow-ups, and browser automation.

## Decision
Use ARQ (Async Redis Queue) with Redis as the message broker. ARQ is lightweight, Python-native, and does not require Kafka-level infrastructure.

## Task Types
- run_matching — candidate × job scoring
- generate_resume — truth-validated resume generation
- process_email — email classification and correlation
- send_followup_email — scheduled follow-up delivery
- start_browser_session — application automation

## Consequences
- Redis required in all environments
- All tasks are idempotent by design
- Failed tasks logged to audit_logs
- No Kafka/RabbitMQ dependency at current scale
