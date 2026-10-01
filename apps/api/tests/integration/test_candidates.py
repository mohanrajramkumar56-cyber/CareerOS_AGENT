"""
Integration tests for the Candidate API endpoints.
Uses the in-memory SQLite test DB via conftest fixtures.
"""
from __future__ import annotations

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _register_and_login(client, email="cand@example.com", password="testpassword123"):
    """Register a user and return a valid auth token."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    login = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    return login.json()["access_token"]


async def _auth_headers(client, email="cand@example.com", password="testpassword123"):
    token = await _register_and_login(client, email, password)
    return {"Authorization": f"Bearer {token}"}


async def _create_profile(client, headers):
    """Create a minimal candidate profile and return the response."""
    return await client.post(
        "/api/v1/candidates/profile",
        json={
            "full_name": "Jane Doe",
            "headline": "Senior Software Engineer",
            "current_country": "US",
            "years_of_experience": 7,
            "preferred_remote_type": "remote",
        },
        headers=headers,
    )


# ── Profile tests ─────────────────────────────────────────────────────────────

class TestCandidateProfile:
    @pytest.mark.asyncio
    async def test_create_profile(self, client):
        headers = await _auth_headers(client, "cp1@example.com")
        r = await _create_profile(client, headers)
        assert r.status_code == 201
        data = r.json()
        assert data["full_name"] == "Jane Doe"
        assert data["years_of_experience"] == 7
        assert data["preferred_remote_type"] == "remote"
        assert "id" in data
        assert "hashed_password" not in str(data)

    @pytest.mark.asyncio
    async def test_create_duplicate_profile_fails(self, client):
        headers = await _auth_headers(client, "cp2@example.com")
        await _create_profile(client, headers)
        r2 = await _create_profile(client, headers)
        assert r2.status_code == 409

    @pytest.mark.asyncio
    async def test_get_profile(self, client):
        headers = await _auth_headers(client, "cp3@example.com")
        await _create_profile(client, headers)
        r = await client.get("/api/v1/candidates/profile", headers=headers)
        assert r.status_code == 200
        assert r.json()["full_name"] == "Jane Doe"

    @pytest.mark.asyncio
    async def test_get_profile_not_found(self, client):
        headers = await _auth_headers(client, "cp4@example.com")
        r = await client.get("/api/v1/candidates/profile", headers=headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_update_profile(self, client):
        headers = await _auth_headers(client, "cp5@example.com")
        await _create_profile(client, headers)
        r = await client.put(
            "/api/v1/candidates/profile",
            json={"headline": "Staff Engineer", "years_of_experience": 10},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["headline"] == "Staff Engineer"
        assert r.json()["years_of_experience"] == 10

    @pytest.mark.asyncio
    async def test_get_full_profile(self, client):
        headers = await _auth_headers(client, "cp6@example.com")
        await _create_profile(client, headers)
        r = await client.get("/api/v1/candidates/profile/full", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "education" in data
        assert "experiences" in data
        assert "skills" in data
        assert "projects" in data
        assert "facts" in data

    @pytest.mark.asyncio
    async def test_profile_requires_auth(self, client):
        r = await client.get("/api/v1/candidates/profile")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_salary_not_exposed_by_default(self, client):
        headers = await _auth_headers(client, "cp7@example.com")
        await client.post(
            "/api/v1/candidates/profile",
            json={"full_name": "Secret", "salary_min_usd": 150000},
            headers=headers,
        )
        r = await client.get("/api/v1/candidates/profile", headers=headers)
        # Salary fields not in CandidateProfileResponse schema
        assert "salary_min_usd" not in r.json()


# ── Education tests ───────────────────────────────────────────────────────────

class TestEducation:
    @pytest.mark.asyncio
    async def test_create_education(self, client):
        headers = await _auth_headers(client, "edu1@example.com")
        await _create_profile(client, headers)
        r = await client.post(
            "/api/v1/candidates/education",
            json={
                "institution": "MIT",
                "degree": "B.Sc.",
                "field_of_study": "Computer Science",
                "start_date": "2015-09-01",
                "end_date": "2019-06-01",
            },
            headers=headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["institution"] == "MIT"
        assert data["degree"] == "B.Sc."

    @pytest.mark.asyncio
    async def test_list_education(self, client):
        headers = await _auth_headers(client, "edu2@example.com")
        await _create_profile(client, headers)
        await client.post(
            "/api/v1/candidates/education",
            json={"institution": "Stanford", "degree": "M.Sc."},
            headers=headers,
        )
        r = await client.get("/api/v1/candidates/education", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) == 1

    @pytest.mark.asyncio
    async def test_update_education(self, client):
        headers = await _auth_headers(client, "edu3@example.com")
        await _create_profile(client, headers)
        create_r = await client.post(
            "/api/v1/candidates/education",
            json={"institution": "Harvard"},
            headers=headers,
        )
        edu_id = create_r.json()["id"]
        r = await client.put(
            f"/api/v1/candidates/education/{edu_id}",
            json={"gpa": "3.9"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["gpa"] == "3.9"

    @pytest.mark.asyncio
    async def test_delete_education(self, client):
        headers = await _auth_headers(client, "edu4@example.com")
        await _create_profile(client, headers)
        create_r = await client.post(
            "/api/v1/candidates/education",
            json={"institution": "Yale"},
            headers=headers,
        )
        edu_id = create_r.json()["id"]
        r = await client.delete(
            f"/api/v1/candidates/education/{edu_id}", headers=headers
        )
        assert r.status_code == 204
        # Verify it's gone
        list_r = await client.get("/api/v1/candidates/education", headers=headers)
        assert len(list_r.json()) == 0

    @pytest.mark.asyncio
    async def test_education_requires_profile(self, client):
        headers = await _auth_headers(client, "edu5@example.com")
        r = await client.post(
            "/api/v1/candidates/education",
            json={"institution": "MIT"},
            headers=headers,
        )
        assert r.status_code == 404


# ── Experience tests ──────────────────────────────────────────────────────────

class TestExperience:
    @pytest.mark.asyncio
    async def test_create_experience(self, client):
        headers = await _auth_headers(client, "exp1@example.com")
        await _create_profile(client, headers)
        r = await client.post(
            "/api/v1/candidates/experiences",
            json={
                "company": "Acme Corp",
                "title": "Senior Engineer",
                "start_date": "2020-01-01",
                "end_date": "2023-06-01",
                "employment_type": "full_time",
            },
            headers=headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["company"] == "Acme Corp"
        assert data["employment_type"] == "full_time"
        # duration_months should be computed
        assert data["duration_months"] is not None
        assert data["duration_months"] > 0

    @pytest.mark.asyncio
    async def test_list_experiences(self, client):
        headers = await _auth_headers(client, "exp2@example.com")
        await _create_profile(client, headers)
        await client.post(
            "/api/v1/candidates/experiences",
            json={"company": "BigCo", "title": "Engineer"},
            headers=headers,
        )
        r = await client.get("/api/v1/candidates/experiences", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) == 1

    @pytest.mark.asyncio
    async def test_delete_experience(self, client):
        headers = await _auth_headers(client, "exp3@example.com")
        await _create_profile(client, headers)
        create_r = await client.post(
            "/api/v1/candidates/experiences",
            json={"company": "StartupXYZ", "title": "CTO"},
            headers=headers,
        )
        exp_id = create_r.json()["id"]
        r = await client.delete(
            f"/api/v1/candidates/experiences/{exp_id}", headers=headers
        )
        assert r.status_code == 204


# ── Skills tests ──────────────────────────────────────────────────────────────

class TestSkills:
    @pytest.mark.asyncio
    async def test_create_skill(self, client):
        headers = await _auth_headers(client, "sk1@example.com")
        await _create_profile(client, headers)
        r = await client.post(
            "/api/v1/candidates/skills",
            json={
                "name": "Python",
                "category": "programming_language",
                "proficiency_level": "expert",
                "years_of_experience": 8,
                "is_primary": True,
            },
            headers=headers,
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Python"

    @pytest.mark.asyncio
    async def test_duplicate_skill_fails(self, client):
        headers = await _auth_headers(client, "sk2@example.com")
        await _create_profile(client, headers)
        await client.post(
            "/api/v1/candidates/skills",
            json={"name": "Go"},
            headers=headers,
        )
        r = await client.post(
            "/api/v1/candidates/skills",
            json={"name": "Go"},
            headers=headers,
        )
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_list_skills(self, client):
        headers = await _auth_headers(client, "sk3@example.com")
        await _create_profile(client, headers)
        for skill in ["Python", "Go", "Rust"]:
            await client.post(
                "/api/v1/candidates/skills", json={"name": skill}, headers=headers
            )
        r = await client.get("/api/v1/candidates/skills", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) == 3

    @pytest.mark.asyncio
    async def test_delete_skill(self, client):
        headers = await _auth_headers(client, "sk4@example.com")
        await _create_profile(client, headers)
        create_r = await client.post(
            "/api/v1/candidates/skills", json={"name": "COBOL"}, headers=headers
        )
        skill_id = create_r.json()["id"]
        r = await client.delete(
            f"/api/v1/candidates/skills/{skill_id}", headers=headers
        )
        assert r.status_code == 204


# ── Projects tests ────────────────────────────────────────────────────────────

class TestProjects:
    @pytest.mark.asyncio
    async def test_create_project(self, client):
        headers = await _auth_headers(client, "proj1@example.com")
        await _create_profile(client, headers)
        r = await client.post(
            "/api/v1/candidates/projects",
            json={
                "name": "CareerOS",
                "description": "Autonomous AI career platform",
                "repository_url": "https://github.com/user/careeros",
                "technologies": "Python,FastAPI,PostgreSQL",
            },
            headers=headers,
        )
        assert r.status_code == 201
        assert r.json()["name"] == "CareerOS"

    @pytest.mark.asyncio
    async def test_list_projects(self, client):
        headers = await _auth_headers(client, "proj2@example.com")
        await _create_profile(client, headers)
        await client.post(
            "/api/v1/candidates/projects",
            json={"name": "My Blog"},
            headers=headers,
        )
        r = await client.get("/api/v1/candidates/projects", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) == 1


# ── Evidence Graph tests ──────────────────────────────────────────────────────

class TestEvidenceFacts:
    @pytest.mark.asyncio
    async def test_create_fact_without_evidence_is_unknown(self, client):
        headers = await _auth_headers(client, "fact1@example.com")
        await _create_profile(client, headers)
        r = await client.post(
            "/api/v1/candidates/facts",
            json={
                "category": "skill",
                "claim": "Knows Kubernetes",
                "evidence": [],
            },
            headers=headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["evidence_strength"] == "unknown"
        assert data["category"] == "skill"

    @pytest.mark.asyncio
    async def test_create_fact_with_verified_evidence(self, client):
        headers = await _auth_headers(client, "fact2@example.com")
        await _create_profile(client, headers)
        r = await client.post(
            "/api/v1/candidates/facts",
            json={
                "category": "certification",
                "claim": "AWS Certified Solutions Architect",
                "normalized_value": "AWS-SAA",
                "evidence": [
                    {
                        "source_type": "certificate",
                        "source_reference": "https://aws.amazon.com/verify/abc123",
                        "description": "AWS cert verification link",
                    }
                ],
            },
            headers=headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["evidence_strength"] == "verified"
        assert len(data["evidence_entries"]) == 1

    @pytest.mark.asyncio
    async def test_create_fact_with_github_evidence_is_verified(self, client):
        headers = await _auth_headers(client, "fact3@example.com")
        await _create_profile(client, headers)
        r = await client.post(
            "/api/v1/candidates/facts",
            json={
                "category": "skill",
                "claim": "Python development",
                "normalized_value": "Python",
                "evidence": [
                    {
                        "source_type": "github",
                        "source_reference": "https://github.com/user/python-projects",
                    }
                ],
            },
            headers=headers,
        )
        assert r.status_code == 201
        assert r.json()["evidence_strength"] == "verified"

    @pytest.mark.asyncio
    async def test_list_facts(self, client):
        headers = await _auth_headers(client, "fact4@example.com")
        await _create_profile(client, headers)
        for claim in ["Python", "Go", "Docker"]:
            await client.post(
                "/api/v1/candidates/facts",
                json={"category": "skill", "claim": claim},
                headers=headers,
            )
        r = await client.get("/api/v1/candidates/facts", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) == 3

    @pytest.mark.asyncio
    async def test_filter_facts_by_category(self, client):
        headers = await _auth_headers(client, "fact5@example.com")
        await _create_profile(client, headers)
        await client.post(
            "/api/v1/candidates/facts",
            json={"category": "skill", "claim": "Python"},
            headers=headers,
        )
        await client.post(
            "/api/v1/candidates/facts",
            json={"category": "education", "claim": "B.Sc. CS from MIT"},
            headers=headers,
        )
        r = await client.get(
            "/api/v1/candidates/facts?category=skill", headers=headers
        )
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["category"] == "skill"

    @pytest.mark.asyncio
    async def test_get_single_fact(self, client):
        headers = await _auth_headers(client, "fact6@example.com")
        await _create_profile(client, headers)
        create_r = await client.post(
            "/api/v1/candidates/facts",
            json={"category": "skill", "claim": "FastAPI"},
            headers=headers,
        )
        fact_id = create_r.json()["id"]
        r = await client.get(f"/api/v1/candidates/facts/{fact_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["claim"] == "FastAPI"

    @pytest.mark.asyncio
    async def test_add_evidence_to_existing_fact(self, client):
        headers = await _auth_headers(client, "fact7@example.com")
        await _create_profile(client, headers)
        # Create fact without evidence
        create_r = await client.post(
            "/api/v1/candidates/facts",
            json={"category": "skill", "claim": "Terraform"},
            headers=headers,
        )
        fact_id = create_r.json()["id"]
        assert create_r.json()["evidence_strength"] == "unknown"

        # Add strong evidence
        ev_r = await client.post(
            f"/api/v1/candidates/facts/{fact_id}/evidence",
            json={
                "source_type": "github",
                "source_reference": "https://github.com/user/infra",
            },
            headers=headers,
        )
        assert ev_r.status_code == 201
        assert ev_r.json()["strength"] == "verified"

        # Verify aggregate strength updated
        fact_r = await client.get(
            f"/api/v1/candidates/facts/{fact_id}", headers=headers
        )
        assert fact_r.json()["evidence_strength"] == "verified"

    @pytest.mark.asyncio
    async def test_cross_user_fact_isolation(self, client):
        """User A cannot access User B's facts."""
        headers_a = await _auth_headers(client, "isola@example.com")
        headers_b = await _auth_headers(client, "isolb@example.com")
        await _create_profile(client, headers_a)
        await _create_profile(client, headers_b)

        create_r = await client.post(
            "/api/v1/candidates/facts",
            json={"category": "skill", "claim": "Secret skill"},
            headers=headers_a,
        )
        fact_id = create_r.json()["id"]

        # User B tries to access User A's fact
        r = await client.get(
            f"/api/v1/candidates/facts/{fact_id}", headers=headers_b
        )
        assert r.status_code == 404


# ── Cross-user isolation tests ────────────────────────────────────────────────

class TestCrossUserIsolation:
    @pytest.mark.asyncio
    async def test_user_cannot_see_other_users_profile(self, client):
        headers_a = await _auth_headers(client, "iso2a@example.com")
        headers_b = await _auth_headers(client, "iso2b@example.com")
        await _create_profile(client, headers_a)

        # User B has no profile, user A's profile is not accessible
        r = await client.get("/api/v1/candidates/profile", headers=headers_b)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_education_scoped_to_user(self, client):
        headers_a = await _auth_headers(client, "iso3a@example.com")
        headers_b = await _auth_headers(client, "iso3b@example.com")
        await _create_profile(client, headers_a)
        await _create_profile(client, headers_b)

        # A creates education
        create_r = await client.post(
            "/api/v1/candidates/education",
            json={"institution": "MIT"},
            headers=headers_a,
        )
        edu_id = create_r.json()["id"]

        # B tries to delete A's education
        r = await client.delete(
            f"/api/v1/candidates/education/{edu_id}", headers=headers_b
        )
        assert r.status_code == 404
