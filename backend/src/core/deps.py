"""FastAPI dependencies — session auth."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from src.services import auth as auth_service


async def get_current_user(request: Request) -> dict:
    """Require a valid session; returns user row + github access_token."""
    user = auth_service.user_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="not authenticated")
    return user


async def get_optional_user(request: Request) -> dict | None:
    return auth_service.user_from_request(request)
