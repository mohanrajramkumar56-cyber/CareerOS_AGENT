"""
CareerOS - SearchAdapter.

Adapter for aggregated job search engines (LinkedIn, Indeed, etc. public APIs).

This is a stub implementation. Production use requires:
- API credentials
- Parsing different result formats per search engine
- Deduplication with content hash
- Source attribution
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from adapters.job_base import JobSourceAdapter


class SearchAdapter(JobSourceAdapter):
    """
    Adapter for job search aggregator APIs.

    Providers can be: indeed, serpapi, jsearch, custom.
    """

    source_name: str = "search"
    source_id: str = "default"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.provider = config.get("provider", "custom")
        self.api_key = config.get("api_key", "")

    async def discovery(
        self, *, query: Optional[str] = None, location: Optional[str] = None, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Discover jobs via search API.

        Applies rate limiting, deduplication hints, and query normalization.
        """
        # Stub: In production, this would:
        # 1. Build search query from query + location
        # 2. Hit API endpoint with proper auth
        # 3. Parse and return normalized results

        return [
            {
                "source_job_id": f"search-{i}",
                "title": f"Senior Software Engineer ({i})",
                "company": f"Tech Company {i}",
                "location": location or "Remote",
                "source_url": f"https://example.com/jobs/{i}",
                "description": f"Job {i}: We are seeking a skilled engineer.",
                "requirements": "BS/MS in CS, 3+ years experience",
                "posted_at": "2026-10-01T00:00:00Z",
            }
            for i in range(1, 6)
        ]

    async def extract(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured data from search result."""
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
        }
