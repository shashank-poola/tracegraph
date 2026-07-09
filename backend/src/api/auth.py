"""GitHub OAuth login, callback, session, and /me."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from src.config import get_settings
from src.core.deps import get_current_user
from src.services import auth as auth_service

logger = logging.getLogger("auth_routes")
router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/github/login")
async def github_login() -> RedirectResponse:
    try:
        return RedirectResponse(auth_service.login_url(), status_code=302)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/github/callback")
async def github_callback(code: str = "", state: str = "", error: str = "") -> RedirectResponse:
    settings = get_settings()
    if error:
        return RedirectResponse(f"{settings.frontend_origin}/login?error={error}")
    if not code or not state:
        raise HTTPException(400, "missing code or state")
    try:
        result = await auth_service.handle_callback(code, state)
    except (ValueError, RuntimeError) as exc:
        logger.warning("oauth callback failed: %s", exc)
        return RedirectResponse(f"{settings.frontend_origin}/login?error=oauth_failed")

    redirect = RedirectResponse(f"{settings.frontend_origin}/auth/callback", status_code=302)
    auth_service.set_session_cookie(redirect, result["session_token"])
    return redirect


@router.get("/me")
async def me(user: dict = Depends(get_current_user)) -> dict:
    return {"user": {k: user[k] for k in ("id", "login", "name", "email", "avatar_url")}}


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict[str, str]:
    auth_service.logout(request, response)
    return {"status": "logged_out"}


@router.get("/session")
async def session_info(request: Request) -> dict:
    user = auth_service.user_from_request(request)
    if not user:
        raise HTTPException(401, "not authenticated")
    return {"user": {k: user[k] for k in ("id", "login", "name", "email", "avatar_url")}}
