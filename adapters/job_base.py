"""
CareerOS - JobSourceAdapter base class.

All job source adapters (CareerSiteAdapter, ATSAdapter, SearchAdapter, etc.)
inherit from this base class to ensure consistent interface and behavior.
"""
from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)


class JobSourceAdapter(ABC):
    """
    Abstract base class for all job source adapters.

    Adapters must implement:
    - discovery: Find job listings
    - extract: Parse raw HTML/JSON into structured data
    - normalize: Standardize fields to CareerOS schema
    - get_provenance: Return source metadata for audit
    - retry: Configurable retry strategy
    - rate_limit: Source-specific rate limiting
    - error_handling: Graceful degradation on errors
    - source_identification: Unique identifier for the source

    Security policy:
    - Never bypass CAPTCHA, authentication, or access controls
    - Respect robots.txt and terms of service
    - Implement proper rate limiting
    - Log all scraping activity
    """

    source_name: str = "abstract"
    source_id: str = "abstract"

    # Rate limiting (requests per time window)
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 3600  # 1 hour

    # Retry configuration
    max_retries: int = 3
    retry_wait_min: float = 1.0
    retry_wait_max: float = 60.0

    # Timeout for external requests
    request_timeout: int = 30

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.last_request_time: float = 0
        self.request_count: int = 0
        self.window_start: float = time.time()

    def _check_rate_limit(self) -> None:
        """Check and enforce rate limits for this source."""
        now = time.time()
        if now - self.window_start > self.rate_limit_window_seconds:
            self.request_count = 0
            self.window_start = now

        if self.request_count >= self.rate_limit_requests:
            raise RateLimitExceeded(
                f"Rate limit exceeded for {self.source_name}: "
                f"{self.rate_limit_requests} requests per {self.rate_limit_window_seconds}s"
            )
        self.request_count += 1
        self.last_request_time = now

    @abstractmethod
    async def discovery(
        self, *, query: Optional[str] = None, location: Optional[str] = None, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Discover job listings from the source.

        Should return raw job data in source-specific format.
        Implements rate limiting and retry logic.
        """
        raise NotImplementedError

    @abstractmethod
    async def extract(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured job data from raw source format.

        Returns normalized intermediate format.
        """
        raise NotImplementedError

    async def normalize(self, extracted_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize extracted job to CareerOS schema.

        Base implementation: returns extracted data as-is.
        Subclasses should override for specific normalization rules.
        """
        normalized = {
            "source": self.source_name,
            "source_job_id": extracted_job.get("source_job_id"),
            "source_url": extracted_job.get("source_url"),
            "company": extracted_job.get("company", "Unknown"),
            "title": extracted_job.get("title", "Unknown"),
            "location": extracted_job.get("location"),
            "remote_type": extracted_job.get("remote_type"),
            "employment_type": extracted_job.get("employment_type"),
            "salary_min": extracted_job.get("salary_min"),
            "salary_max": extracted_job.get("salary_max"),
            "salary_currency": extracted_job.get("salary_currency", "USD"),
            "salary_period": extracted_job.get("salary_period"),
            "description": extracted_job.get("description"),
            "responsibilities": extracted_job.get("responsibilities"),
            "requirements": extracted_job.get("requirements"),
            "mandatory_skills": extracted_job.get("mandatory_skills"),
            "preferred_skills": extracted_job.get("preferred_skills"),
            "education_requirements": extracted_job.get("education_requirements"),
            "experience_requirements": extracted_job.get("experience_requirements"),
            "certifications": extracted_job.get("certifications"),
            "work_authorization_required": extracted_job.get(
                "work_authorization_required"
            ),
            "sponsorship_required": extracted_job.get("sponsorship_required"),
            "application_url": extracted_job.get("application_url"),
            "posted_at": extracted_job.get("posted_at"),
            "expires_at": extracted_job.get("expires_at"),
        }

        # Compute content hash for deduplication
        content_string = (
            f"{normalized['company']}|{normalized['title']}|{normalized.get('location', '')}"
        )
        normalized["content_hash"] = hashlib.sha256(
            content_string.encode("utf-8")
        ).hexdigest()

        return normalized

    @abstractmethod
    def get_provenance(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return provenance/metadata about the job source.

        Used for audit and debugging.
        """
        raise NotImplementedError

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(
            multiplier=1, min=self.retry_wait_min, max=self.retry_wait_max
        ),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    async def _retryable_request(self, *args, **kwargs) -> Any:
        """Internal method with automatic retry on network errors."""
        raise NotImplementedError

    def should_retry(self, exception: Exception) -> bool:
        """Determine if an exception should trigger a retry."""
        return isinstance(exception, (ConnectionError, TimeoutError))

    def handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """
        Handle errors gracefully.

        Logs error and optionally updates job status.
        """
        raise NotImplementedError

    def source_identification(self) -> str:
        """Return a unique identifier for this source."""
        return f"{self.source_name}:{self.source_id}"


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded for a source."""

    pass


class ExtractionError(Exception):
    """Raised when job extraction fails."""

    pass


class AuthenticationError(Exception):
    """Raised when authentication is required but not provided."""

    pass
