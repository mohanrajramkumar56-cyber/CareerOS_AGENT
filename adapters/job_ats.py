"""
CareerOS - ATSAdapter.

Adapter for connecting to Applicant Tracking Systems via API.

Supports:
- Greenhouse
- Lever
- Workday
- Custom ATS endpoints

This is a stub implementation. Production use requires:
- API credentials (API key, OAuth token, etc.)
- Proper authentication handling
- Rate limiting per ATS provider
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from adapters.job_base import JobSourceAdapter


class ATSAdapter(JobSourceAdapter):
    """
    Adapter for ATS (Applicant Tracking System) job feeds.

    Supports multiple ATS providers via unified interface.
    """

    source_name: str = "ats"
    source_id: str = "default"

    SUPPORTED_PROVIDERS = {"greenhouse", "lever", "workday", "custom"}

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.provider = config.get("provider", "custom")
        self.api_url = config.get("api_url", "")
        self.api_key = config.get("api_key", "")

        if self.provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported ATS provider: {self.provider}. "
                f"Supported: {self.SUPPORTED_PROVIDERS}"
            )

    async def discovery(
        self, *, query: Optional[str] = None, location: Optional[str] = None, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Discover jobs from ATS via API.

        Returns raw job data from ATS JSON endpoint.
        """
        # Stub: In production, this would:
        # 1. Authenticate with ATS API
        # 2. Query /jobs endpoint with optional filters
        # 3. Parse JSON response
        # 4. Return job listings

        return [
            {
                "source_job_id": f"ats-{self.provider}-{i}",
                "title": "ATS Sample Job",
                "company": "ATS Company",
                "location": "Remote",
                "source_url": f"{self.api_url}/jobs/{i}",
                "description": "Sample job from ATS",
                "requirements": "2+ years experience required",
                "posted_at": "2026-10-01T00:00:00Z",
            }
            for i in range(1, 6)
        ]

    async def extract(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured data from ATS job."""
        return {
            "source_job_id": raw_job.get("source_job_id"),
            "title": raw_job.get("title"),
            "company": raw_job.get("company"),
            "location": raw_job.get("location"),
            "source_url": raw_job.get("source_url"),
            "description": raw_job.get("description"),
            "requirements": raw_job.get("requirements"),
            "posted_at": raw_job.get("posted_at"),
            "application_url": raw_job.get("application_url"),
        }

    def get_provenance(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Return provenance for audit."""
        return {
            "source": self.source_name,
            "provider": self.provider,
            "source_job_id": job_data.get("source_job_id"),
            "discovered_at": job_data.get("discovered_at"),
            "api_url": self.api_url,
        }
