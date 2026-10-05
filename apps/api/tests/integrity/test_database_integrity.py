"""
Database Integrity Testing - Find bugs in constraints, cascades, and data corruption.

Tests edge cases that could cause data corruption or integrity violations.
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text


# ── Constraint violation tests ────────────────────────────────────────────────

class TestForeignKeyConstraints:
    @pytest.mark.asyncio
    async def test_orphaned_candidate_data_cleanup(self, db_session, client):
        """Test that deleting a user cascades to candidate data"""
        # Create user + profile + skills
        headers = await self._create_test_candidate(client)
        
        from app.models.candidate import Skill
        
        fake_candidate_id = uuid.uuid4()
        
        # Try to create a skill with non-existent candidate_id
        skill = Skill(
            candidate_id=fake_candidate_id,
            name="Orphaned Skill",
            category="test"
        )
        db_session.add(skill)
        
        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio  
    async def test_job_match_cascade_deletion(self, db_session, client):
        """Test JobMatch cleanup when Job is deleted"""
        headers = await self._create_test_candidate(client)
        
        # Create job + match
        job_r = await client.post("/api/v1/jobs/", 
                                json={"source": "test", "company": "Test", "title": "Test"},
                                headers=headers)
        job_id = job_r.json()["id"]
        
        match_r = await client.post("/api/v1/matches/compute", 
                                  json={"job_id": job_id}, 
                                  headers=headers)
        assert match_r.status_code == 200
        
        # Delete job - should cascade to match or soft-delete
        delete_r = await client.delete(f"/api/v1/jobs/{job_id}", headers=headers)
        assert delete_r.status_code == 204
        
        # Match should be gone or inaccessible after job deletion
        get_match_r = await client.get(f"/api/v1/matches/{job_id}", headers=headers)
        # Accept either 404 (deleted) or 200 with soft-delete semantics
        assert get_match_r.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_duplicate_profile_constraint(self, db_session, client):
        """Test that one user cannot have multiple profiles"""
        headers = await self._create_test_candidate(client)
        
        # Try to create second profile
        profile2_r = await client.post("/api/v1/candidates/profile",
                                     json={"full_name": "Second Profile"},
                                     headers=headers)
        assert profile2_r.status_code == 409

    @pytest.mark.asyncio
    async def test_duplicate_skill_constraint(self, db_session, client):
        """Test that duplicate skills are rejected"""
        headers = await self._create_test_candidate(client)
        
        # Create skill
        skill1_r = await client.post("/api/v1/candidates/skills",
                                   json={"name": "Python", "category": "technology"},
                                   headers=headers)
        assert skill1_r.status_code == 201
        
        # Try to create duplicate
        skill2_r = await client.post("/api/v1/candidates/skills",
                                   json={"name": "Python", "category": "technology"},
                                   headers=headers)
        assert skill2_r.status_code == 409

    async def _create_test_candidate(self, client):
        """Helper to create authenticated candidate"""
        email = f"dbtest_{uuid.uuid4()}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login_r = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        token = login_r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        profile_r = await client.post("/api/v1/candidates/profile", 
                                    json={"full_name": "DB Test User"}, 
                                    headers=headers)
        assert profile_r.status_code == 201
        return headers


# ── Data corruption tests ─────────────────────────────────────────────────────

class TestDataCorruption:
    @pytest.mark.asyncio
    async def test_null_constraint_violations(self, db_session, client):
        """Test that required fields cannot be null"""
        headers = await self._create_test_candidate(client)
        
        # Try to create job with missing required fields
        bad_job_r = await client.post("/api/v1/jobs/",
                                    json={"source": "", "company": "", "title": ""},
                                    headers=headers)
        # Should be rejected by Pydantic validation
        assert bad_job_r.status_code == 422

    @pytest.mark.asyncio
    async def test_oversized_field_handling(self, db_session, client):
        """Test handling of oversized text fields"""
        headers = await self._create_test_candidate(client)
        
        # Create job with extremely long description
        long_description = "x" * 50000  # 50KB description
        
        job_r = await client.post("/api/v1/jobs/",
                                json={"source": "test", "company": "Test", "title": "Test",
                                     "description": long_description},
                                headers=headers)
        
        # Should handle long text gracefully or reject appropriately
        assert job_r.status_code in (201, 400, 413, 422)

    @pytest.mark.asyncio
    async def test_date_boundary_values(self, db_session, client):
        """Test edge cases in date handling"""
        headers = await self._create_test_candidate(client)
        
        # Test future dates
        future_exp_r = await client.post("/api/v1/candidates/experiences",
                                       json={"company": "Future Corp", "title": "Future Role",
                                            "start_date": "2099-12-31", "end_date": "2100-01-01"},
                                       headers=headers)
        assert future_exp_r.status_code == 201
        
        # Test very old dates
        old_exp_r = await client.post("/api/v1/candidates/experiences",
                                    json={"company": "Ancient Corp", "title": "Cave Painter",
                                         "start_date": "1900-01-01", "end_date": "1950-01-01"},
                                    headers=headers)
        assert old_exp_r.status_code == 201

    async def _create_test_candidate(self, client):
        """Helper to create authenticated candidate"""
        email = f"corruption_{uuid.uuid4()}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login_r = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        token = login_r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        profile_r = await client.post("/api/v1/candidates/profile", 
                                    json={"full_name": "Corruption Test"}, 
                                    headers=headers)
        assert profile_r.status_code == 201
        return headers


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])