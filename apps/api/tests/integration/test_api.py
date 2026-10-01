"""
Integration tests for API endpoints.
Uses in-memory SQLite via client fixture from conftest.
"""
from __future__ import annotations

import pytest
import pytest_asyncio


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "careeros-api"

    @pytest.mark.asyncio
    async def test_api_v1_system_health(self, client):
        response = await client.get("/api/v1/system/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_register_new_user(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "securepassword123",
                "full_name": "Test User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert "id" in data
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email_fails(self, client):
        payload = {
            "email": "duplicate@example.com",
            "password": "securepassword123",
        }
        r1 = await client.post("/api/v1/auth/register", json=payload)
        assert r1.status_code == 201

        r2 = await client.post("/api/v1/auth/register", json=payload)
        assert r2.status_code == 409

    @pytest.mark.asyncio
    async def test_login_returns_tokens(self, client):
        # Register first
        await client.post(
            "/api/v1/auth/register",
            json={"email": "login@example.com", "password": "securepassword123"},
        )
        # Login
        response = await client.post(
            "/api/v1/auth/token",
            data={"username": "login@example.com", "password": "securepassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password_fails(self, client):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "wrong@example.com", "password": "correctpassword"},
        )
        response = await client.post(
            "/api/v1/auth/token",
            data={"username": "wrong@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_requires_auth(self, client):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_with_valid_token(self, client):
        # Register + login
        await client.post(
            "/api/v1/auth/register",
            json={"email": "me@example.com", "password": "securepassword123"},
        )
        login_response = await client.post(
            "/api/v1/auth/token",
            data={"username": "me@example.com", "password": "securepassword123"},
        )
        token = login_response.json()["access_token"]

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "me@example.com"

    @pytest.mark.asyncio
    async def test_register_weak_password_fails(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "weak@example.com", "password": "short"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_email_fails(self, client):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "securepassword123"},
        )
        assert response.status_code == 422
