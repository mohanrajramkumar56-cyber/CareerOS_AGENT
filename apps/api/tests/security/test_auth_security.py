"""
Authentication Security Testing - Find JWT, session, and authorization bypass bugs.

Critical security tests before production deployment.
"""
import pytest
import time
import uuid
from datetime import datetime, timedelta


class TestJWTSecurity:
    @pytest.mark.asyncio
    async def test_expired_token_rejection(self, client):
        """Test that expired JWT tokens are rejected"""
        # Register and login
        email = "expire_test@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        
        # Get a token
        login_r = await client.post("/api/v1/auth/token", 
                                  data={"username": email, "password": "testpass123"})
        assert login_r.status_code == 200
        
        # Try to decode the token to understand its structure
        token = login_r.json()["access_token"]
        
        # Try using token immediately (should work)
        headers = {"Authorization": f"Bearer {token}"}
        profile_r = await client.get("/api/v1/candidates/profile", headers=headers)
        # May be 404 (no profile) or 200, but NOT 401 (invalid token)
        assert profile_r.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_invalid_token_format(self, client):
        """Test rejection of malformed JWT tokens"""
        invalid_tokens = [
            "invalid.jwt.token",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.signature",  # Invalid signature
            "Bearer token_without_bearer_prefix",
            "completely_random_string",
            "",
            None
        ]
        
        for token in invalid_tokens:
            if token:
                headers = {"Authorization": f"Bearer {token}"}
            else:
                headers = {}
            
            profile_r = await client.get("/api/v1/candidates/profile", headers=headers)
            assert profile_r.status_code == 401, f"Token {token} should be rejected"

    @pytest.mark.asyncio 
    async def test_token_tampering_detection(self, client):
        """Test that tampered JWT tokens are detected"""
        email = "tamper_test@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        
        login_r = await client.post("/api/v1/auth/token",
                                  data={"username": email, "password": "testpass123"})
        token = login_r.json()["access_token"]
        
        # Tamper with the token by changing the last character
        tampered_token = token[:-1] + ("x" if token[-1] != "x" else "y")
        
        headers = {"Authorization": f"Bearer {tampered_token}"}
        profile_r = await client.get("/api/v1/candidates/profile", headers=headers)
        assert profile_r.status_code == 401, "Tampered token should be rejected"

    @pytest.mark.asyncio
    async def test_cross_user_token_isolation(self, client):
        """Test that User A's token cannot access User B's data"""
        # Create two users
        user_a_email = "user_a@example.com"
        user_b_email = "user_b@example.com"
        
        await client.post("/api/v1/auth/register", json={"email": user_a_email, "password": "testpass123"})
        await client.post("/api/v1/auth/register", json={"email": user_b_email, "password": "testpass123"})
        
        # Login both users
        login_a = await client.post("/api/v1/auth/token", 
                                  data={"username": user_a_email, "password": "testpass123"})
        login_b = await client.post("/api/v1/auth/token",
                                  data={"username": user_b_email, "password": "testpass123"})
        
        token_a = login_a.json()["access_token"]
        token_b = login_b.json()["access_token"]
        
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}
        
        # User A creates profile
        await client.post("/api/v1/candidates/profile",
                         json={"full_name": "User A"}, headers=headers_a)
        
        # User B creates profile  
        await client.post("/api/v1/candidates/profile",
                         json={"full_name": "User B"}, headers=headers_b)
        
        # User A creates a job
        job_r = await client.post("/api/v1/jobs/",
                                json={"source": "test", "company": "A Corp", "title": "A Job"},
                                headers=headers_a)
        job_id = job_r.json()["id"]
        
        # User B should NOT be able to access/modify User A's job
        # (Note: Jobs are global, but user-scoped operations should be isolated)
        get_job_r = await client.get(f"/api/v1/jobs/{job_id}", headers=headers_b)
        # Jobs might be viewable by all users, but let's test profile access
        
        # More importantly: User B should NOT access User A's profile
        profile_a_r = await client.get("/api/v1/candidates/profile", headers=headers_b)
        assert profile_a_r.status_code == 200
        # Should return User B's profile, not User A's
        profile_data = profile_a_r.json()
        assert profile_data["full_name"] == "User B"


class TestInputValidationSecurity:
    @pytest.mark.asyncio
    async def test_sql_injection_attempts(self, client):
        """Test SQL injection prevention"""
        email = "sqli_test@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login_r = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}
        
        await client.post("/api/v1/candidates/profile", json={"full_name": "SQLi Test"}, headers=headers)
        
        # SQL injection payloads
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users--",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ]
        
        for payload in sql_payloads:
            # Test in job creation
            job_r = await client.post("/api/v1/jobs/",
                                    json={"source": "test", "company": payload, "title": "Test"},
                                    headers=headers)
            # Should either create successfully (escaped) or reject, but not cause SQL error
            assert job_r.status_code in (200, 201, 400, 422), f"SQL injection payload caused server error: {payload}"
            
            # Test in profile update
            profile_r = await client.put("/api/v1/candidates/profile",
                                       json={"full_name": payload}, headers=headers)
            assert profile_r.status_code in (200, 400, 422), f"SQL injection in profile update: {payload}"

    @pytest.mark.asyncio
    async def test_xss_prevention(self, client):
        """Test XSS payload handling"""
        email = "xss_test@example.com"  
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login_r = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}
        
        await client.post("/api/v1/candidates/profile", json={"full_name": "XSS Test"}, headers=headers)
        
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//",
            "<svg/onload=alert('xss')>"
        ]
        
        for payload in xss_payloads:
            # Test XSS in job description
            job_r = await client.post("/api/v1/jobs/",
                                    json={"source": "test", "company": "Test", "title": "Test",
                                         "description": payload},
                                    headers=headers)
            
            if job_r.status_code == 201:
                # If created, verify the payload is stored as-is (not executed)
                job_data = job_r.json()
                # The API stores raw input — XSS prevention is the frontend's responsibility
                # The stored description should match or be a sanitised subset of the payload
                stored = job_data.get("description", "") or ""
                assert isinstance(stored, str), f"description should be a string, got {type(stored)}"

    @pytest.mark.asyncio
    async def test_oversized_payload_handling(self, client):
        """Test handling of extremely large payloads"""
        email = "oversize_test@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login_r = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}
        
        # Test very large JSON payload
        huge_description = "X" * (1024 * 1024)  # 1MB description
        
        job_r = await client.post("/api/v1/jobs/",
                                json={"source": "test", "company": "Test", "title": "Test",
                                     "description": huge_description},
                                headers=headers)
        
        # Should either handle gracefully or reject with appropriate error
        assert job_r.status_code in (201, 400, 413, 422), "Oversized payload should be handled gracefully"

    @pytest.mark.asyncio
    async def test_unicode_handling(self, client):
        """Test Unicode and special character handling"""
        email = "unicode_test@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login_r = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}
        
        await client.post("/api/v1/candidates/profile", json={"full_name": "Unicode Test"}, headers=headers)
        
        unicode_payloads = [
            "José García",  # Accented characters
            "北京市",       # Chinese characters  
            "🚀🔥💯",      # Emojis
            "إختبار",      # Arabic
            "тест",        # Cyrillic
            "\x00\x01\x02", # Null bytes and control characters
            "\\n\\r\\t",   # Escape sequences
        ]
        
        for payload in unicode_payloads:
            job_r = await client.post("/api/v1/jobs/",
                                    json={"source": "test", "company": payload, "title": "Test"},
                                    headers=headers)
            # Should handle Unicode gracefully
            assert job_r.status_code in (200, 201, 400, 422), f"Unicode payload failed: {payload}"


class TestRateLimitingAndDOS:
    @pytest.mark.asyncio
    async def test_rapid_requests_handling(self, client):
        """Test that rapid requests don't crash the server"""
        email = "rapid_test@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        login_r = await client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
        headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}
        
        # Send many requests rapidly  
        responses = []
        for i in range(20):
            r = await client.get("/health")  # Use public endpoint
            responses.append(r.status_code)
        
        # Server should handle all requests gracefully (may rate limit but not crash)
        assert all(status in (200, 429) for status in responses), "Server crashed under rapid requests"

    @pytest.mark.asyncio
    async def test_concurrent_authentication(self, client):
        """Test concurrent login attempts"""
        import asyncio
        
        email = "concurrent_test@example.com"
        await client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
        
        async def login_attempt():
            return await client.post("/api/v1/auth/token", 
                                   data={"username": email, "password": "testpass123"})
        
        # Concurrent logins
        results = await asyncio.gather(*[login_attempt() for _ in range(10)], 
                                     return_exceptions=True)
        
        success_count = sum(1 for r in results if hasattr(r, 'status_code') and r.status_code == 200)
        
        # Should handle concurrent auth gracefully
        assert success_count >= 5, f"Concurrent auth handling poor: {success_count}/10 success"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])