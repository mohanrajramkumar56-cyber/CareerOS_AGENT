"""
Diagnostic tests to find the root cause of authentication failures.
"""
import pytest
import uuid


@pytest.mark.asyncio
async def test_basic_registration_debug(client):
    """Debug what's wrong with registration"""
    
    # Try simple email first
    simple_email = "test@example.com"
    
    register_r = await client.post("/api/v1/auth/register", 
                                 json={"email": simple_email, "password": "test123"})
    
    print(f"Registration status: {register_r.status_code}")
    if register_r.status_code != 201:
        print(f"Registration error: {register_r.text}")
        return
    
    # Try login
    login_r = await client.post("/api/v1/auth/token",
                              data={"username": simple_email, "password": "test123"})
    
    print(f"Login status: {login_r.status_code}")
    if login_r.status_code != 200:
        print(f"Login error: {login_r.text}")
        return
    
    token = login_r.json()["access_token"]
    print(f"Token obtained: {token[:20]}...")
    
    # Try authenticated request
    headers = {"Authorization": f"Bearer {token}"}
    profile_r = await client.get("/api/v1/candidates/profile", headers=headers)
    print(f"Profile request status: {profile_r.status_code}")


@pytest.mark.asyncio  
async def test_uuid_email_issue(client):
    """Test if UUID in email causes validation issues"""
    
    # Test UUID email format that was failing
    uuid_email = f"test_{uuid.uuid4()}@example.com"
    
    register_r = await client.post("/api/v1/auth/register",
                                 json={"email": uuid_email, "password": "test123"})
    
    print(f"UUID email registration: {register_r.status_code}")
    if register_r.status_code != 201:
        print(f"UUID email error: {register_r.text}")


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test that health endpoint works"""
    health_r = await client.get("/health")
    print(f"Health status: {health_r.status_code}")
    if health_r.status_code == 200:
        print(f"Health response: {health_r.json()}")


@pytest.mark.asyncio
async def test_registration_validation_details(client):
    """Test registration with various invalid inputs to understand validation"""
    
    test_cases = [
        {"email": "", "password": "test123"},  # Empty email
        {"email": "invalid-email", "password": "test123"},  # Invalid email format
        {"email": "test@example.com", "password": ""},  # Empty password
        {"email": "test@example.com", "password": "123"},  # Short password
    ]
    
    for i, case in enumerate(test_cases):
        r = await client.post("/api/v1/auth/register", json=case)
        print(f"Test case {i+1}: {case} -> Status: {r.status_code}")
        if r.status_code == 422:
            print(f"  Validation error: {r.json()}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])