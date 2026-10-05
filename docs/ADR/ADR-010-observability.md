# ADR-010: Observability

## Status
Accepted

## Context
Production CareerOS must be diagnosable. Agent runs, tool calls, model latency, and browser sessions all need visibility.

## Decision
Use OpenTelemetry for distributed tracing, Prometheus for metrics, and structlog for structured logging. All are open-source.

## Implementation
- OpenTelemetry SDK with OTLP export (compatible with Jaeger, Grafana Tempo)
- Prometheus metrics at /metrics endpoint
- structlog with JSON output and correlation IDs
- Every request tagged with X-Correlation-ID

## Planned Additions
- Grafana dashboards for key metrics
- Langfuse (open-source) for LLM observability
- Alert rules for: application failures, worker dead, model latency >5s

## Consequences
- No vendor lock-in — all open-source tooling
- OTEL_EXPORTER_OTLP_ENDPOINT must be configured in production
- Log volume may be high — structured format enables filtering
