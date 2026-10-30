"""Backward-compatible import for the auth-free local-profile router."""

from app.api.member2.local import router

__all__ = ["router"]
