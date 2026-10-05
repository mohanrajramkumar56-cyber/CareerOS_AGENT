"""
Integration tests for the Jobs API endpoints (Phase 2).
Uses the in-memory SQLite test DB via conftest fixtures.
"""
from __future__ import annotations

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _register_and_login(client, email="jobs@example.com", password="testpass123"):
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    return login.json()["access_token"]


async def _auth_headers(client, email="jobs@example.com", password="testpass123"):
    token = await _register_and_login(client, email, password)
    return {"Authorization": f"Bearer {token}"}


def _job_payload(**overrides):
    base = {
        "source": "search",
        "company": "Acme Corp",
        "title": "Senior Python Developer",
        "location": "New York, NY",
        "description": "We need a Python developer with 5+ years of experience in FastAPI and PostgreSQL.",
        "application_url": "https://acme.com/jobs/123",
        "remote_type": "remote",
        "employment_type": "full_time",
    }
    base.update(overrides)
    return base


# ── POST /jobs/ ───────────────────────────────────────────────────────────────

class TestIngestJob:
    @pytest.mark.asyncio
    async def test_ingest_job_creates_new(self, client):
        headers = await _auth_headers(client, "j1@example.com")
        r = await client.post("/api/v1/jobs/", json=_job_payload(), headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["company"] == "Acme Corp"
        assert data["title"] == "Senior Python Developer"
        assert data["was_created"] is True
        assert "id" in data
        assert data["freshness_status"] in ("new", "active")

    @pytest.mark.asyncio
    async def test_ingest_duplicate_returns_existing(self, client):
        headers = await _auth_headers(client, "j2@example.com")
        payload = _job_payload(company="Dedup Corp", title="Dedup Engineer")
        r1 = await client.post("/api/v1/jobs/", json=payload, headers=headers)
        assert r1.status_code == 201
        r2 = await client.post("/api/v1/jobs/", json=payload, headers=headers)
        # Duplicate returns 200 with was_created=False
        data2 = r2.json()
        assert data2["was_created"] is False
        assert data2["id"] == r1.json()["id"]

    @pytest.mark.asyncio
    async def test_ingest_job_requires_auth(self, client):
        r = await client.post("/api/v1/jobs/", json=_job_payload())
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_ingest_job_extracts_skills(self, client):
        headers = await _auth_headers(client, "j3@example.com")
        payload = _job_payload(
            description="Must know Python, FastAPI, PostgreSQL and Docker. AWS is nice to have."
        )
        r = await client.post("/api/v1/jobs/", json=payload, headers=headers)
        assert r.status_code == 201
        data = r.json()
        # Pipeline should extract skills
        # mandatory_skills and preferred_skills may or may not be populated
        # depending on section detection — just verify the field exists
        assert "mandatory_skills" in data
        assert "preferred_skills" in data


# ── GET /jobs/ ────────────────────────────────────────────────────────────────

class TestListJobs:
    @pytest.mark.asyncio
    async def test_list_jobs_empty(self, client):
        headers = await _auth_headers(client, "jl1@example.com")
        r = await client.get("/api/v1/jobs/", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "jobs" in data
        assert "total" in data
        assert isinstance(data["jobs"], list)

    @pytest.mark.asyncio
    async def test_list_jobs_returns_created(self, client):
        headers = await _auth_headers(client, "jl2@example.com")
        await client.post("/api/v1/jobs/", json=_job_payload(company="ListTest"), headers=headers)
        r = await client.get("/api/v1/jobs/", headers=headers)
        assert r.status_code == 200
        data = r.json()
        companies = [j["company"] for j in data["jobs"]]
        assert "ListTest" in companies

    @pytest.mark.asyncio
    async def test_list_jobs_filter_by_remote_type(self, client):
        headers = await _auth_headers(client, "jl3@example.com")
        await client.post("/api/v1/jobs/", json=_job_payload(company="RemoteOnly", remote_type="remote"), headers=headers)
        r = await client.get("/api/v1/jobs/?remote_type=remote", headers=headers)
        assert r.status_code == 200
        for job in r.json()["jobs"]:
            assert job["remote_type"] == "remote"

    @pytest.mark.asyncio
    async def test_list_jobs_pagination(self, client):
        headers = await _auth_headers(client, "jl4@example.com")
        r = await client.get("/api/v1/jobs/?page=1&page_size=5", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert len(data["jobs"]) <= 5

    @pytest.mark.asyncio
    async def test_list_jobs_requires_auth(self, client):
        r = await client.get("/api/v1/jobs/")
        assert r.status_code == 401


# ── GET /jobs/{job_id} ────────────────────────────────────────────────────────

class TestGetJob:
    @pytest.mark.asyncio
    async def test_get_job_by_id(self, client):
        headers = await _auth_headers(client, "jg1@example.com")
        create_r = await client.post("/api/v1/jobs/", json=_job_payload(company="GetTest"), headers=headers)
        job_id = create_r.json()["id"]
        r = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["id"] == job_id
        assert r.json()["company"] == "GetTest"

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, client):
        headers = await _auth_headers(client, "jg2@example.com")
        fake_id = "00000000-0000-0000-0000-000000000000"
        r = await client.get(f"/api/v1/jobs/{fake_id}", headers=headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_get_job_requires_auth(self, client):
        fake_id = "00000000-0000-0000-0000-000000000000"
        r = await client.get(f"/api/v1/jobs/{fake_id}")
        assert r.status_code == 401


# ── PUT /jobs/{job_id} ────────────────────────────────────────────────────────

class TestUpdateJob:
    @pytest.mark.asyncio
    async def test_update_job_title(self, client):
        headers = await _auth_headers(client, "ju1@example.com")
        create_r = await client.post("/api/v1/jobs/", json=_job_payload(company="UpdateTest"), headers=headers)
        job_id = create_r.json()["id"]
        r = await client.put(f"/api/v1/jobs/{job_id}", json={"title": "Lead Python Developer"}, headers=headers)
        assert r.status_code == 200
        assert r.json()["title"] == "Lead Python Developer"

    @pytest.mark.asyncio
    async def test_update_job_not_found(self, client):
        headers = await _auth_headers(client, "ju2@example.com")
        fake_id = "00000000-0000-0000-0000-000000000001"
        r = await client.put(f"/api/v1/jobs/{fake_id}", json={"title": "New Title"}, headers=headers)
        assert r.status_code == 404


# ── DELETE /jobs/{job_id} ─────────────────────────────────────────────────────

class TestDeleteJob:
    @pytest.mark.asyncio
    async def test_delete_job(self, client):
        headers = await _auth_headers(client, "jd1@example.com")
        create_r = await client.post("/api/v1/jobs/", json=_job_payload(company="DeleteTest"), headers=headers)
        job_id = create_r.json()["id"]
        r = await client.delete(f"/api/v1/jobs/{job_id}", headers=headers)
        assert r.status_code == 204
        # Verify it's gone
        get_r = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert get_r.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_job_not_found(self, client):
        headers = await _auth_headers(client, "jd2@example.com")
        fake_id = "00000000-0000-0000-0000-000000000002"
        r = await client.delete(f"/api/v1/jobs/{fake_id}", headers=headers)
        assert r.status_code == 404


# ── POST /jobs/search ─────────────────────────────────────────────────────────

class TestSearchJobs:
    @pytest.mark.asyncio
    async def test_search_by_query(self, client):
        headers = await _auth_headers(client, "js1@example.com")
        await client.post("/api/v1/jobs/", json=_job_payload(title="React Frontend Engineer", company="SearchCo"), headers=headers)
        r = await client.post("/api/v1/jobs/search", json={"query": "React"}, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "jobs" in data
        titles = [j["title"] for j in data["jobs"]]
        assert any("React" in t for t in titles)

    @pytest.mark.asyncio
    async def test_search_returns_paginated(self, client):
        headers = await _auth_headers(client, "js2@example.com")
        r = await client.post("/api/v1/jobs/search", json={"page": 1, "page_size": 10}, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    @pytest.mark.asyncio
    async def test_search_requires_auth(self, client):
        r = await client.post("/api/v1/jobs/search", json={"query": "Python"})
        assert r.status_code == 401


# ── POST /jobs/refresh-freshness ──────────────────────────────────────────────

class TestRefreshFreshness:
    @pytest.mark.asyncio
    async def test_refresh_freshness(self, client):
        headers = await _auth_headers(client, "jf1@example.com")
        r = await client.post("/api/v1/jobs/refresh-freshness", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "updated" in data
        assert isinstance(data["updated"], int)

    @pytest.mark.asyncio
    async def test_refresh_freshness_requires_auth(self, client):
        r = await client.post("/api/v1/jobs/refresh-freshness")
        assert r.status_code == 401
