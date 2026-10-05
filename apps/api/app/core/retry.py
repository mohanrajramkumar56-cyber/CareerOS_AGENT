"""
CareerOS retry and circuit breaker utilities.
Use these decorators on all external service calls.
"""
from __future__ import annotations
import logging

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    RetryError,
)

logger = logging.getLogger(__name__)


def external_call_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    retryable_exceptions: tuple = (Exception,),
):
    """Decorator: retry external calls with exponential backoff + jitter."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(retryable_exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


# Pre-configured retry for HTTP calls
http_retry = external_call_retry(max_attempts=3, min_wait=0.5, max_wait=5.0)

# Pre-configured retry for database operations
db_retry = external_call_retry(max_attempts=2, min_wait=0.1, max_wait=1.0)

# Pre-configured retry for email operations
email_retry = external_call_retry(max_attempts=3, min_wait=1.0, max_wait=30.0)
