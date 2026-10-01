"""
CareerOS - ORM models registry.
Import all models here so Alembic auto-detects them.
"""
from app.models.user import User, UserSession

__all__ = [
    "User",
    "UserSession",
]
