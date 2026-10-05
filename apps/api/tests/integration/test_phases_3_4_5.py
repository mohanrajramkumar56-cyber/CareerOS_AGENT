"""
Integration tests for Phase 3 (Matching), Phase 4 (Resume), Phase 5 (Application).
"""
from __future__ import annotations

import pytest


# ── Shared helpers ─────────────────────────────────────────────────────────────

async def _register_and_login(client, email, password="testpass123"):
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    return login.json()["access_token"]


async def _auth_headers(client, email, password="testpass123"):
    token = await _register_and_login(client, email, password)
    return {"Authorization": f"Bearer {token}"}


async def _setup_candidate_and_job(client, email):
    """Full setup: register, create profile, ingest job. Returns (headers, job_id)."""
    headers = await _auth_headers(client, email)

    await client.post(
        "/api/v1/candidates/profile",
        json={
            "full_name": "Test User",
            "headline": "Python Developer",
            "current_country": "US",
            "years_of_experience": 5,
            "preferred_remote_type": "remote",
            "work_authorization": "citizen",
        },
        headers=headers,
    )

    await client.post(
        "/api/v1/candidates/skills",
        json={"name": "Python", "category": "technology", "proficiency": "expert"},
        headers=headers,
    )

    job_r = await client.post(
        "/api/v1/jobs/",
        json={
            "source": "search",
            "company": "TestCo",
            "title": "Python Backend Developer",
            "description": "Requires Python, FastAPI. Nice to have: Docker.",
            "remote_type": "remote",
            "employment_type": "full_time",
            "application_url": "https://testco.com/jobs/1",
        },
        headers=headers,
    )
    job_id = job_r.json()["id"]
    return headers, job_id


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: Matching Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestMatchingEngine:
    @pytest.mark.asyncio
    async def test_compute_match(self, client):
        headers, job_id = await _setup_candidate_and_job(client, "m1@example.com")
        r = await client.post(
            "/api/v1/matches/compute",
            json={"job_id": job_id},
            headers=headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert "eligible" in data
        assert "skill_match_score" in data
        assert "confidence" in data
        assert "explanation" in data
        assert data["job_id"] == job_id

    @pytest.mark.asyncio
    async def test_compute_match_no_profile_returns_404(self, client):
        headers = await _auth_headers(client, "m2@example.com")
        r = await client.post(
            "/api/v1/matches/compute",
            json={"job_id": "00000000-0000-0000-0000-000000000001"},
            headers=headers,
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_compute_match_bad_job_returns_404(self, client):
        headers, _ = await _setup_candidate_and_job(client, "m3@example.com")
        r = await client.post(
            "/api/v1/matches/compute",
            json={"job_id": "00000000-0000-0000-0000-000000000099"},
            headers=headers,
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_list_matches(self, client):
        headers, job_id = await _setup_candidate_and_job(client, "m4@example.com")
        # Compute a match first
        await client.post("/api/v1/matches/compute", json={"job_id": job_id}, headers=headers)
        r = await client.get("/api/v1/matches/", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "matches" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_match_by_job_id(self, client):
        headers, job_id = await _setup_candidate_and_job(client, "m5@example.com")
        await client.post("/api/v1/matches/compute", json={"job_id": job_id}, headers=headers)
        r = await client.get(f"/api/v1/matches/{job_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["job_id"] == job_id

    @pytest.mark.asyncio
    async def test_batch_compute_matches(self, client):
        headers, job_id = await _setup_candidate_and_job(client, "m6@example.com")
        r = await client.post(
            "/api/v1/matches/batch",
            json=[{"job_id": job_id}],
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["computed"] == 1

    @pytest.mark.asyncio
    async def test_match_requires_auth(self, client):
        r = await client.post("/api/v1/matches/compute", json={"job_id": "00000000-0000-0000-0000-000000000000"})
        assert r.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4: Resume Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestResumeEngine:
    @pytest.mark.asyncio
    async def test_generate_resume(self, client):
        headers, job_id = await _setup_candidate_and_job(client, "r1@example.com")
        r = await client.post(
            "/api/v1/resumes/",
            json={"template": "standard"},
            headers=headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["template"] == "standard"
        assert data["truth_policy_enforced"] is True
        assert data["content_markdown"] is not None
        assert "Test User" in (data["content_markdown"] or "")

    @pytest.mark.asyncio
    async def test_generate_tailored_resume(self, client):
        headers, job_id = await _setup_candidate_and_job(client, "r2@example.com")
        r = await client.post(
            "/api/v1/resumes/",
            json={"template": "standard", "job_id": job_id},
            headers=headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["is_tailored"] is True
        assert data["job_id"] == job_id

    @pytest.mark.asyncio
    async def test_generate_resume_invalid_template(self, client):
        headers, _ = await _setup_candidate_and_job(client, "r3@example.com")
        r = await client.post(
            "/api/v1/resumes/",
            json={"template": "invalid_template"},
            headers=headers,
        )
        assert r.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_list_resumes(self, client):
        headers, _ = await _setup_candidate_and_job(client, "r4@example.com")
        await client.post("/api/v1/resumes/", json={"template": "minimal"}, headers=headers)
        r = await client.get("/api/v1/resumes/", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert len(data["resumes"]) >= 1

    @pytest.mark.asyncio
    async def test_get_resume_by_id(self, client):
        headers, _ = await _setup_candidate_and_job(client, "r5@example.com")
        create_r = await client.post("/api/v1/resumes/", json={"template": "technical"}, headers=headers)
        resume_id = create_r.json()["id"]
        r = await client.get(f"/api/v1/resumes/{resume_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["id"] == resume_id

    @pytest.mark.asyncio
    async def test_get_resume_markdown(self, client):
        headers, _ = await _setup_candidate_and_job(client, "r6@example.com")
        create_r = await client.post("/api/v1/resumes/", json={"template": "standard"}, headers=headers)
        resume_id = create_r.json()["id"]
        r = await client.get(f"/api/v1/resumes/{resume_id}/markdown", headers=headers)
        assert r.status_code == 200
        assert "Test User" in r.text

    @pytest.mark.asyncio
    async def test_delete_resume(self, client):
        headers, _ = await _setup_candidate_and_job(client, "r7@example.com")
        create_r = await client.post("/api/v1/resumes/", json={"template": "executive"}, headers=headers)
        resume_id = create_r.json()["id"]
        r = await client.delete(f"/api/v1/resumes/{resume_id}", headers=headers)
        assert r.status_code == 204
        get_r = await client.get(f"/api/v1/resumes/{resume_id}", headers=headers)
        assert get_r.status_code == 404

    @pytest.mark.asyncio
    async def test_resume_requires_auth(self, client):
        r = await client.post("/api/v1/resumes/", json={"template": "standard"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_resume_cross_user_isolation(self, client):
        headers1, _ = await _setup_candidate_and_job(client, "r8a@example.com")
        headers2, _ = await _setup_candidate_and_job(client, "r8b@example.com")
        create_r = await client.post("/api/v1/resumes/", json={"template": "standard"}, headers=headers1)
        resume_id = create_r.json()["id"]
        # User 2 cannot access user 1's resume
        r = await client.get(f"/api/v1/resumes/{resume_id}", headers=headers2)
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 5: Application Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestApplicationEngine:
    @pytest.mark.asyncio
    async def test_create_application(self, client):
        headers, job_id = await _setup_candidate_and_job(client, "a1@example.com")
        r = await client.post(
            "/api/v1/applications/",
            json={"job_id": job_id, "cover_letter": "I am very interested."},
            headers=headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "draft"
        assert data["job_id"] == job_id
        assert data["form_data"] is not None  # Auto-filled

    @pytest.mark.asyncio
    async def test_create_duplicate_application_rejected(self, client):
        headers, job_id = await _setup_candidate_and_job(client, "a2@example.com")
        await client.post("/api/v1/applications/", json={"job_id": job_id}, headers=headers)
        r2 = await client.post("/api/v1/applications/", json={"job_id": job_id}, headers=headers)
        assert r2.status_code == 409

    @pytest.mark.asyncio
    async def test_list_applications(self, client):
        headers, job_id = await _setup_candidate_and_job(client, "a3@example.com")
        await client.post("/api/v1/applications/", json={"job_id": job_id}, headers=headers)
        r = await client.get("/api/v1/applications/", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_application_state_machine_full_flow(self, client):
        headers, job_id = await _setup_candidate_and_job(client, "a4@example.com")
        create_r = await client.post("/api/v1/applications/", json={"job_id": job_id}, headers=headers)
        app_id = create_r.json()["id"]

        # draft → pending_approval
        r = await client.post(f"/api/v1/applications/{app_id}/submit", headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "pending_approval"

        # pending_approval → approved
        r = await client.post(f"/api/v1/applications/{app_id}/approve", json={}, headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

        # approved → submitted
        r = await client.post(f"/api/v1/applications/{app_id}/mark-submitted", headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "submitted"

    @pytest.mark.asyncio
    async def test_application_invalid_transition_rejected(self, client):
        headers, job_id = await _setup_candidate_and_job(client, "a5@example.com")
        create_r = await client.post("/api/v1/applications/", json={"job_id": job_id}, headers=headers)
        app_id = create_r.json()["id"]
        # Can't approve a draft (must go through pending first)
        r = await client.post(f"/api/v1/applications/{app_id}/approve", json={}, headers=headers)
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_withdraw_application(self, client):
        headers, job_id = await _setup_candidate_and_job(client, "a6@example.com")
        create_r = await client.post("/api/v1/applications/", json={"job_id": job_id}, headers=headers)
        app_id = create_r.json()["id"]
        r = await client.post(f"/api/v1/applications/{app_id}/withdraw", headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "withdrawn"

    @pytest.mark.asyncio
    async def test_delete_draft_application(self, client):
        headers, job_id = await _setup_candidate_and_job(client, "a7@example.com")
        create_r = await client.post("/api/v1/applications/", json={"job_id": job_id}, headers=headers)
        app_id = create_r.json()["id"]
        r = await client.delete(f"/api/v1/applications/{app_id}", headers=headers)
        assert r.status_code == 204

    @pytest.mark.asyncio
    async def test_application_requires_auth(self, client):
        r = await client.post("/api/v1/applications/", json={"job_id": "00000000-0000-0000-0000-000000000000"})
        assert r.status_code == 401
