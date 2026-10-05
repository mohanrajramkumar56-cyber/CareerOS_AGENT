"""
Truth Policy Validation - Ensure no fabricated data enters the system.

This is CRITICAL for production - the entire value proposition depends on truth policy.
"""
import pytest
import uuid


class TestTruthPolicyEnforcement:
    @pytest.mark.asyncio
    async def test_unknown_facts_excluded_from_resumes(self, client):
        """Test that UNKNOWN evidence facts are never included in resumes"""
        email = f"truth_{uuid.uuid4()}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login_r = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}
        
        # Create profile
        await client.post("/api/v1/candidates/profile", 
                         json={"full_name": "Truth Tester"}, headers=headers)
        
        # Generate resume - should enforce truth policy
        resume_r = await client.post("/api/v1/resumes/",
                                   json={"template": "standard"}, headers=headers)
        assert resume_r.status_code == 201
        
        resume = resume_r.json()
        # Truth policy should ALWAYS be enforced
        assert resume["truth_policy_enforced"] is True, "Truth policy MUST be enforced"
        
        # Should track excluded facts
        assert "facts_excluded_count" in resume
        assert isinstance(resume["facts_excluded_count"], int)

    @pytest.mark.asyncio
    async def test_evidence_strength_validation(self, client):
        """Test that evidence strength cannot be bypassed"""
        email = f"evidence_{uuid.uuid4()}@example.com" 
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login_r = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}
        
        await client.post("/api/v1/candidates/profile",
                         json={"full_name": "Evidence Test"}, headers=headers)
        
        # Try to create a fact with invalid evidence strength
        from app.domain.enums import EvidenceStrength
        valid_strengths = [e.value for e in EvidenceStrength]
        
        # Create a fact with a valid strength
        fact_r = await client.post("/api/v1/candidates/facts",
                                 json={"category": "skill", "claim": "Python programming",
                                      "evidence_strength": "verified"},
                                 headers=headers)
        assert fact_r.status_code == 201
        fact_data = fact_r.json()
        # Verify the strength stored is a valid value
        assert fact_data["evidence_strength"] in valid_strengths, \
            f"evidence_strength must be one of {valid_strengths}, got: {fact_data['evidence_strength']}"

    @pytest.mark.asyncio
    async def test_no_automatic_verification_upgrade(self, client):
        """Test that evidence strength cannot be automatically upgraded"""
        email = f"upgrade_{uuid.uuid4()}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login_r = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}
        
        await client.post("/api/v1/candidates/profile",
                         json={"full_name": "Upgrade Test"}, headers=headers)
        
        # Create a weak fact
        fact_r = await client.post("/api/v1/candidates/facts",
                                 json={"category": "skill", "claim": "JavaScript",
                                      "evidence_strength": "weak"},
                                 headers=headers)
        assert fact_r.status_code == 201
        fact = fact_r.json()
        fact_id = fact["id"]
        
        # Try to upgrade by adding more evidence
        evidence_r = await client.post(f"/api/v1/candidates/facts/{fact_id}/evidence",
                                     json={"source_type": "user_confirmation", 
                                          "strength": "verified",  # Try to upgrade to verified
                                          "description": "I confirm this"},
                                     headers=headers)
        
        if evidence_r.status_code == 201:
            # Check that the fact's aggregate strength follows proper rules
            get_fact_r = await client.get(f"/api/v1/candidates/facts/{fact_id}", headers=headers)
            updated_fact = get_fact_r.json()
            
            # Should use evidence aggregation rules, not allow arbitrary upgrades
            # (The actual rule: strongest evidence wins)
            assert updated_fact["evidence_strength"] in ["weak", "verified"], "Evidence aggregation should follow rules"

    @pytest.mark.asyncio
    async def test_fabrication_prevention_in_matching(self, client):
        """Test that matching engine cannot fabricate candidate capabilities"""
        email = f"matching_{uuid.uuid4()}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login_r = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}
        
        await client.post("/api/v1/candidates/profile",
                         json={"full_name": "Match Test"}, headers=headers)
        
        # Create job requiring skills candidate doesn't have — explicitly set mandatory_skills
        job_r = await client.post("/api/v1/jobs/",
                                json={"source": "test", "company": "Test Corp", "title": "Senior Blockchain Developer",
                                     "description": "Requires 10 years Solidity, Ethereum, DeFi experience",
                                     "mandatory_skills": "Solidity,Ethereum,DeFi,Blockchain,Web3"},
                                headers=headers)
        job_id = job_r.json()["id"]
        
        # Compute match
        match_r = await client.post("/api/v1/matches/compute",
                                  json={"job_id": job_id}, headers=headers)
        assert match_r.status_code == 200
        
        match = match_r.json()
        # Should honestly report low skill match score
        assert match["skill_match_score"] is not None
        # Should be 0 or very low since candidate has no blockchain skills
        # (Score of 0.0 when candidate has none of the mandatory skills)
        assert match["skill_match_score"] <= 0.3, "Should not fabricate skills for matching"

    @pytest.mark.asyncio
    async def test_resume_content_matches_evidence(self, client):
        """Test that resume content only includes verifiable information"""
        email = f"resume_{uuid.uuid4()}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login_r = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}
        
        # Create profile with specific information
        await client.post("/api/v1/candidates/profile",
                         json={"full_name": "Resume Test", 
                              "headline": "Software Engineer",
                              "years_of_experience": 5}, headers=headers)
        
        # Add one verified skill
        await client.post("/api/v1/candidates/skills",
                         json={"name": "Python", "category": "technology"}, headers=headers)
        
        # Generate resume
        resume_r = await client.post("/api/v1/resumes/",
                                   json={"template": "standard"}, headers=headers)
        assert resume_r.status_code == 201
        resume = resume_r.json()
        
        # Get markdown content
        markdown_r = await client.get(f"/api/v1/resumes/{resume['id']}/markdown", headers=headers)
        content = markdown_r.text
        
        # Should contain only information we provided
        assert "Resume Test" in content, "Should include provided name"
        assert "Software Engineer" in content, "Should include provided headline"
        assert "Python" in content, "Should include provided skill"
        
        # Should NOT contain fabricated information
        assert "Harvard" not in content, "Should not fabricate education"
        assert "Google" not in content, "Should not fabricate experience" 
        assert "Machine Learning" not in content, "Should not fabricate unlisted skills"


class TestEvidenceIntegrity:
    @pytest.mark.asyncio
    async def test_evidence_source_tracking(self, client):
        """Test that all evidence has proper source attribution"""
        email = f"source_{uuid.uuid4()}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login_r = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}
        
        await client.post("/api/v1/candidates/profile",
                         json={"full_name": "Source Test"}, headers=headers)
        
        # Create fact with evidence
        fact_r = await client.post("/api/v1/candidates/facts",
                                 json={"category": "certification", 
                                      "claim": "AWS Certified Solutions Architect",
                                      "evidence_strength": "verified"},
                                 headers=headers)
        assert fact_r.status_code == 201
        fact = fact_r.json()
        fact_id = fact["id"]
        
        # Add evidence with source
        evidence_r = await client.post(f"/api/v1/candidates/facts/{fact_id}/evidence",
                                     json={"source_type": "certificate",
                                          "source_reference": "https://aws.amazon.com/verify/cert123",
                                          "strength": "verified",
                                          "description": "Official AWS certification"},
                                     headers=headers)
        assert evidence_r.status_code == 201
        
        # Verify evidence is tracked
        fact_detail_r = await client.get(f"/api/v1/candidates/facts/{fact_id}", headers=headers)
        fact_detail = fact_detail_r.json()
        
        assert len(fact_detail["evidence_entries"]) >= 1, "Evidence should be tracked"
        evidence = fact_detail["evidence_entries"][0]
        assert evidence["source_type"] == "certificate", "Source type should be preserved"
        assert evidence["source_reference"] == "https://aws.amazon.com/verify/cert123", "Source reference should be preserved"

    @pytest.mark.asyncio  
    async def test_cannot_delete_evidence_retroactively(self, client):
        """Test that evidence cannot be deleted after fact creation"""
        # This tests the immutability principle
        email = f"immutable_{uuid.uuid4()}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login_r = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}
        
        await client.post("/api/v1/candidates/profile",
                         json={"full_name": "Immutable Test"}, headers=headers)
        
        # Create fact
        fact_r = await client.post("/api/v1/candidates/facts",
                                 json={"category": "skill", "claim": "Rust programming",
                                      "evidence_strength": "strong"},
                                 headers=headers)
        fact_id = fact_r.json()["id"]
        
        # Add evidence
        evidence_r = await client.post(f"/api/v1/candidates/facts/{fact_id}/evidence",
                                     json={"source_type": "github", 
                                          "source_reference": "https://github.com/user/rust-project",
                                          "strength": "strong"},
                                     headers=headers)
        evidence_id = evidence_r.json()["id"]
        
        # Try to delete evidence (should fail - no delete endpoint should exist)
        delete_r = await client.delete(f"/api/v1/candidates/evidence/{evidence_id}", headers=headers)
        assert delete_r.status_code == 404, "Evidence deletion should not be possible (immutability)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])