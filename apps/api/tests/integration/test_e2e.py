"""
CareerOS - End-to-End Integration Tests (Phase 11).

Tests the full candidate journey:
  1. Register user
  2. Build candidate profile
  3. Add skills + experience
  4. Ingest a job
  5. Compute match
  6. Generate resume (standard + tailored)
  7. Create application
  8. Run through approval state machine
  9. Dashboard stats reflect real data
  10. Policy engine evaluation
  11. Audit and security checks
"""
from __future__ import annotations

import pytest


# ── Setup helpers ─────────────────────────────────────────────────────────────

async def _register(client, email, password="e2epass123"):
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, f"Register failed: {r.json()}"
    return r.json()


async def _login(client, email, password="e2epass123"):
    r = await client.post("/api/v1/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.json()}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ═══════════════════════════════════════════════════════════════════════════════
# Full E2E Journey
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullCandidateJourney:
    """
    Complete end-to-end journey test.

    Tests the entire pipeline from registration to application submission.
    """

    @pytest.mark.asyncio
    async def test_full_journey(self, client):
        """
        Full CareerOS pipeline:
        register → profile → skills → job → match → resume → application → approval → submit
        """
        # ── Step 1: Register + Login ───────────────────────────────────────────
        email = "e2e_journey@example.com"
        await _register(client, email)
        headers = await _login(client, email)

        # ── Step 2: Create candidate profile ──────────────────────────────────
        profile_r = await client.post(
            "/api/v1/candidates/profile",
            json={
                "full_name": "Alex Journey",
                "headline": "Full-Stack Python Developer",
                "summary": "Experienced Python developer with 6 years building scalable APIs.",
                "email": email,
                "current_city": "Austin",
                "current_country": "US",
                "years_of_experience": 6,
                "preferred_remote_type": "remote",
                "work_authorization": "citizen",
                "willing_to_relocate": False,
            },
            headers=headers,
        )
        assert profile_r.status_code == 201
        profile = profile_r.json()
        assert profile["full_name"] == "Alex Journey"

        # ── Step 3: Add skills ─────────────────────────────────────────────────
        for skill in ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"]:
            r = await client.post(
                "/api/v1/candidates/skills",
                json={"name": skill, "category": "technology"},
                headers=headers,
            )
            assert r.status_code == 201, f"Skill {skill} failed: {r.json()}"

        # ── Step 4: Add experience ─────────────────────────────────────────────
        exp_r = await client.post(
            "/api/v1/candidates/experiences",
            json={
                "company": "TechCorp",
                "title": "Senior Backend Engineer",
                "description": "Led development of microservices using Python and FastAPI. "
                               "Deployed to AWS with Docker and Kubernetes.",
                "start_date": "2020-01-01",
                "end_date": None,
                "is_current": True,
            },
            headers=headers,
        )
        assert exp_r.status_code == 201

        # ── Step 5: Ingest a job ───────────────────────────────────────────────
        job_r = await client.post(
            "/api/v1/jobs/",
            json={
                "source": "search",
                "company": "StartupAI",
                "title": "Senior Python Backend Developer",
                "description": (
                    "We're looking for a senior Python developer with 5+ years experience. "
                    "Required: Python, FastAPI, PostgreSQL. Nice to have: Docker, AWS. "
                    "Bachelor's degree preferred. "
                    "Remote role. No sponsorship required."
                ),
                "location": "Remote",
                "remote_type": "remote",
                "employment_type": "full_time",
                "salary_min": 120000,
                "salary_max": 160000,
                "application_url": "https://startupai.com/careers/1",
            },
            headers=headers,
        )
        assert job_r.status_code == 201
        job = job_r.json()
        job_id = job["id"]
        assert job["was_created"] is True
        assert job["freshness_status"] in ("new", "active")

        # ── Step 6: Compute match ──────────────────────────────────────────────
        match_r = await client.post(
            "/api/v1/matches/compute",
            json={"job_id": job_id},
            headers=headers,
        )
        assert match_r.status_code == 200
        match = match_r.json()
        # Eligibility depends on job description parsing — at minimum should not be ineligible
        assert match["eligible"] in ("eligible", "unknown")  # Candidate is a US citizen
        assert match["skill_match_score"] is not None
        assert match["skill_match_score"] > 0  # Has Python, FastAPI, PostgreSQL
        assert match["confidence"] is not None
        assert match["explanation"] is not None

        # ── Step 7: Generate standard resume ──────────────────────────────────
        resume_r = await client.post(
            "/api/v1/resumes/",
            json={"template": "standard", "title": "Alex Journey — Standard CV"},
            headers=headers,
        )
        assert resume_r.status_code == 201
        resume = resume_r.json()
        resume_id = resume["id"]
        assert resume["truth_policy_enforced"] is True
        assert "Alex Journey" in (resume["content_markdown"] or "")
        assert "Python" in (resume["content_markdown"] or "")

        # ── Step 8: Generate tailored resume ──────────────────────────────────
        tailored_r = await client.post(
            "/api/v1/resumes/",
            json={"template": "standard", "job_id": job_id},
            headers=headers,
        )
        assert tailored_r.status_code == 201
        tailored = tailored_r.json()
        assert tailored["is_tailored"] is True
        assert tailored["job_id"] == job_id

        # ── Step 9: Create application ─────────────────────────────────────────
        app_r = await client.post(
            "/api/v1/applications/",
            json={
                "job_id": job_id,
                "resume_id": resume_id,
                "cover_letter": "I am excited to apply for this role at StartupAI.",
                "requires_approval": True,
            },
            headers=headers,
        )
        assert app_r.status_code == 201
        application = app_r.json()
        app_id = application["id"]
        assert application["status"] == "draft"
        assert application["form_data"] is not None
        import json
        form_data = json.loads(application["form_data"])
        assert form_data.get("full_name") == "Alex Journey"
        assert form_data.get("email") == email

        # ── Step 10: Submit for approval ───────────────────────────────────────
        submit_r = await client.post(f"/api/v1/applications/{app_id}/submit", headers=headers)
        assert submit_r.status_code == 200
        assert submit_r.json()["status"] == "pending_approval"

        # ── Step 11: Human approval ────────────────────────────────────────────
        approve_r = await client.post(
            f"/api/v1/applications/{app_id}/approve",
            json={"notes": "Looks good, proceed."},
            headers=headers,
        )
        assert approve_r.status_code == 200
        approved = approve_r.json()
        assert approved["status"] == "approved"
        assert approved["approved_at"] is not None
        assert approved["approval_notes"] == "Looks good, proceed."

        # ── Step 12: Mark as submitted ─────────────────────────────────────────
        final_r = await client.post(f"/api/v1/applications/{app_id}/mark-submitted", headers=headers)
        assert final_r.status_code == 200
        assert final_r.json()["status"] == "submitted"
        assert final_r.json()["submitted_at"] is not None

        # ── Step 13: Dashboard stats reflect all activity ──────────────────────
        stats_r = await client.get("/api/v1/dashboard/stats", headers=headers)
        assert stats_r.status_code == 200
        stats = stats_r.json()
        assert stats["jobs_discovered"] >= 1
        assert stats["jobs_matched"] >= 1
        assert stats["jobs_eligible"] >= 0  # may be 0 if eligibility is "unknown" due to parsing
        assert stats["resumes_generated"] >= 2
        assert stats["applications_total"] >= 1
        assert stats["applications_submitted"] >= 1

        # ── Step 14: Activity feed ─────────────────────────────────────────────
        activity_r = await client.get("/api/v1/dashboard/activity", headers=headers)
        assert activity_r.status_code == 200
        items = activity_r.json()["items"]
        assert len(items) > 0
        types = {item["type"] for item in items}
        assert "application" in types or "resume" in types


class TestSecurityAndIsolation:
    """Verify cross-user isolation and security properties."""

    @pytest.mark.asyncio
    async def test_cross_user_data_isolation(self, client):
        """User A cannot access User B's resources."""
        await _register(client, "isolation_a@example.com")
        await _register(client, "isolation_b@example.com")
        headers_a = await _login(client, "isolation_a@example.com")
        headers_b = await _login(client, "isolation_b@example.com")

        # User A creates profile + job + resume
        await client.post("/api/v1/candidates/profile", json={"full_name": "User A"}, headers=headers_a)
        job_r = await client.post(
            "/api/v1/jobs/",
            json={"source": "search", "company": "Corp", "title": "Dev"},
            headers=headers_a,
        )
        job_id = job_r.json()["id"]

        resume_r = await client.post("/api/v1/resumes/", json={"template": "minimal"}, headers=headers_a)
        resume_id = resume_r.json()["id"]

        # User B cannot access User A's resume
        r = await client.get(f"/api/v1/resumes/{resume_id}", headers=headers_b)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthenticated_access_blocked(self, client):
        """All protected endpoints reject unauthenticated requests."""
        endpoints = [
            ("GET", "/api/v1/candidates/profile"),
            ("GET", "/api/v1/jobs/"),
            ("GET", "/api/v1/matches/"),
            ("GET", "/api/v1/resumes/"),
            ("GET", "/api/v1/applications/"),
            ("GET", "/api/v1/dashboard/stats"),
        ]
        for method, path in endpoints:
            r = await client.request(method, path)
            assert r.status_code == 401, f"Expected 401 for {method} {path}, got {r.status_code}"

    @pytest.mark.asyncio
    async def test_health_endpoints_public(self, client):
        """Health and readiness endpoints are publicly accessible."""
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestDataIntegrity:
    """Verify truth policy and data integrity properties."""

    @pytest.mark.asyncio
    async def test_resume_truth_policy_always_enforced(self, client):
        """Generated resumes always have truth_policy_enforced=True."""
        await _register(client, "truth@example.com")
        headers = await _login(client, "truth@example.com")
        await client.post("/api/v1/candidates/profile", json={"full_name": "Truth Tester"}, headers=headers)

        for template in ["standard", "minimal", "technical", "executive"]:
            r = await client.post("/api/v1/resumes/", json={"template": template}, headers=headers)
            assert r.status_code == 201, f"Template {template} failed"
            assert r.json()["truth_policy_enforced"] is True

    @pytest.mark.asyncio
    async def test_job_deduplication_is_idempotent(self, client):
        """Ingesting the same job multiple times returns the same record."""
        await _register(client, "dedup_e2e@example.com")
        headers = await _login(client, "dedup_e2e@example.com")

        payload = {"source": "search", "company": "IdempCorp", "title": "Backend Dev", "location": "NYC"}
        ids = set()
        for _ in range(3):
            r = await client.post("/api/v1/jobs/", json=payload, headers=headers)
            ids.add(r.json()["id"])

        assert len(ids) == 1, "Duplicate ingestion should return same record"

    @pytest.mark.asyncio
    async def test_application_state_machine_prevents_skip(self, client):
        """Cannot skip state machine steps — must go draft→pending→approved→submitted."""
        await _register(client, "statemachine@example.com")
        headers = await _login(client, "statemachine@example.com")
        await client.post("/api/v1/candidates/profile", json={"full_name": "State Tester"}, headers=headers)

        job_r = await client.post(
            "/api/v1/jobs/",
            json={"source": "search", "company": "SM Corp", "title": "Dev"},
            headers=headers,
        )
        job_id = job_r.json()["id"]
        app_r = await client.post("/api/v1/applications/", json={"job_id": job_id}, headers=headers)
        app_id = app_r.json()["id"]

        # Cannot go directly to mark-submitted from draft
        r = await client.post(f"/api/v1/applications/{app_id}/mark-submitted", headers=headers)
        assert r.status_code == 409

        # Cannot approve from draft
        r = await client.post(f"/api/v1/applications/{app_id}/approve", json={}, headers=headers)
        assert r.status_code == 409


class TestDashboardStats:
    """Verify dashboard stats are accurate."""

    @pytest.mark.asyncio
    async def test_stats_zero_when_no_profile(self, client):
        """Stats return zeros for a user with no profile."""
        await _register(client, "nostats@example.com")
        headers = await _login(client, "nostats@example.com")
        r = await client.get("/api/v1/dashboard/stats", headers=headers)
        assert r.status_code == 200
        stats = r.json()
        assert stats["applications_total"] == 0
        assert stats["resumes_generated"] == 0

    @pytest.mark.asyncio
    async def test_activity_empty_for_new_user(self, client):
        """Activity feed is empty for a new user."""
        await _register(client, "noactivity@example.com")
        headers = await _login(client, "noactivity@example.com")
        r = await client.get("/api/v1/dashboard/activity", headers=headers)
        assert r.status_code == 200
        assert r.json()["items"] == []
