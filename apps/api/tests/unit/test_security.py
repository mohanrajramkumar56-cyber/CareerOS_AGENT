"""
Unit tests for security module: password hashing, JWT tokens.
"""
from __future__ import annotations

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_access_token,
    verify_password,
    decode_token,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("mysecretpassword")
        assert hashed != "mysecretpassword"
        assert len(hashed) > 20

    def test_correct_password_verifies(self):
        hashed = hash_password("mysecretpassword")
        assert verify_password("mysecretpassword", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("mysecretpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_hash_is_bcrypt(self):
        hashed = hash_password("test")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_two_hashes_of_same_password_differ(self):
        """bcrypt uses a random salt, so hashes must differ."""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2


class TestJWTTokens:
    def test_access_token_created(self):
        token = create_access_token("user-123")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_access_token_verify_returns_subject(self):
        token = create_access_token("user-123")
        subject = verify_access_token(token)
        assert subject == "user-123"

    def test_refresh_token_type_not_access(self):
        """Refresh token must not pass as access token."""
        token = create_refresh_token("user-123")
        subject = verify_access_token(token)
        assert subject is None

    def test_tampered_token_returns_none(self):
        token = create_access_token("user-123")
        tampered = token[:-5] + "XXXXX"
        subject = verify_access_token(tampered)
        assert subject is None

    def test_garbage_token_returns_none(self):
        subject = verify_access_token("not.a.token")
        assert subject is None

    def test_empty_token_returns_none(self):
        subject = verify_access_token("")
        assert subject is None

    def test_decode_token_returns_correct_sub(self):
        token = create_access_token("user-abc")
        payload = decode_token(token)
        assert payload["sub"] == "user-abc"
        assert payload["type"] == "access"
