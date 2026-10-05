"""
CareerOS - OpenTelemetry Observability (Phase 9).

Provides:
- Trace spans for all service functions
- Structured log enrichment with trace/span IDs
- Metric recording helpers
- Context propagation utilities

Auto-instruments FastAPI and SQLAlchemy.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import structlog
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

log = structlog.get_logger(__name__)

_tracer: Optional[trace.Tracer] = None
_provider: Optional[TracerProvider] = None


def setup_telemetry(
    service_name: str = "careeros-api",
    service_version: str = "0.1.0",
    otlp_endpoint: Optional[str] = None,
    enable_console: bool = False,
) -> TracerProvider:
    """
    Configure OpenTelemetry tracing.

    If OTLP endpoint is set, exports to an OTLP collector.
    Falls back to console exporter in development.
    """
    global _tracer, _provider

    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })

    provider = TracerProvider(resource=resource)

    # OTLP exporter (production)
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            log.info("otel.otlp_exporter_configured", endpoint=otlp_endpoint)
        except Exception as e:
            log.warning("otel.otlp_exporter_failed", error=str(e))
            enable_console = True

    # Console exporter (development / fallback)
    if enable_console:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _provider = provider
    _tracer = trace.get_tracer(service_name, service_version)

    log.info("otel.tracing_configured", service=service_name, version=service_version)
    return provider


def instrument_fastapi(app) -> None:
    """Instrument a FastAPI app with OpenTelemetry traces."""
    try:
        FastAPIInstrumentor.instrument_app(app)
        log.info("otel.fastapi_instrumented")
    except Exception as e:
        log.warning("otel.fastapi_instrumentation_failed", error=str(e))


def instrument_sqlalchemy(engine) -> None:
    """Instrument SQLAlchemy engine with OpenTelemetry traces."""
    try:
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
        log.info("otel.sqlalchemy_instrumented")
    except Exception as e:
        log.warning("otel.sqlalchemy_instrumentation_failed", error=str(e))


def get_tracer(name: str = "careeros") -> trace.Tracer:
    """Get the configured tracer, or a no-op tracer if not initialized."""
    return trace.get_tracer(name)


def enrich_log_with_trace_context(event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    structlog processor that adds OTel trace/span IDs to log records.

    Add to structlog processor chain.
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


def create_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Context manager that creates a named trace span."""
    tracer = get_tracer()
    span = tracer.start_span(name)
    if attributes:
        for k, v in attributes.items():
            span.set_attribute(k, str(v))
    return trace.use_span(span, end_on_exit=True)
