"""GitHub OAuth + session management (backend-owned auth)."""

from __future__ import annotations

import logging
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import Request, Response

from src.config import get_settings
from src.services import storage as db

logger = logging.getLogger("auth")

GH_AUTHORIZE = "https://github.com/login/oauth/authorize"
GH_TOKEN = "https://github.com/login/oauth/access_token"
GH_API = "https://api.github.com"
SCOPES = "read:user user:email repo"
COOKIE_NAME = "tracegraph_session"


def _oauth_configured() -> bool:
    s = get_settings()
    return bool(s.github_oauth_client_id and s.github_oauth_client_secret)


def login_url() -> str:
    s = get_settings()
    if not _oauth_configured():
        raise RuntimeError("GitHub OAuth not configured (GITHUB_OAUTH_CLIENT_ID/SECRET)")
    state = secrets.token_urlsafe(32)
    db.save_oauth_state(state)
    params = {
        "client_id": s.github_oauth_client_id,
        "redirect_uri": s.github_oauth_callback_url,
        "scope": SCOPES,
        "state": state,
    }
    return f"{GH_AUTHORIZE}?{urlencode(params)}"


async def handle_callback(code: str, state: str) -> dict[str, Any]:
    if not db.pop_oauth_state(state):
        raise ValueError("invalid or expired OAuth state")

    s = get_settings()
    async with httpx.AsyncClient(timeout=30) as client:
        token_resp = await client.post(
            GH_TOKEN,
            headers={"Accept": "application/json"},
            json={
                "client_id": s.github_oauth_client_id,
                "client_secret": s.github_oauth_client_secret,
                "code": code,
                "redirect_uri": s.github_oauth_callback_url,
            },
        )
        if token_resp.status_code != 200:
            raise RuntimeError(f"token exchange failed ({token_resp.status_code})")
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise RuntimeError(token_data.get("error_description", "no access_token"))

        user_resp = await client.get(
            f"{GH_API}/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        if user_resp.status_code != 200:
            raise RuntimeError(f"user fetch failed ({user_resp.status_code})")
        gh_user = user_resp.json()

        email = gh_user.get("email")
        if not email:
            emails_resp = await client.get(
                f"{GH_API}/user/emails",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
            )
            if emails_resp.status_code == 200:
                for item in emails_resp.json():
                    if item.get("primary"):
                        email = item.get("email")
                        break

    user = db.upsert_user(
        github_id=gh_user["id"],
        login=gh_user["login"],
        name=gh_user.get("name") or gh_user["login"],
        email=email or "",
        avatar_url=gh_user.get("avatar_url") or "",
    )
    db.save_oauth_account(
        user_id=user["id"],
        access_token=access_token,
        scope=token_data.get("scope", SCOPES),
    )
    session = db.create_session(user["id"])
    return {"user": public_user(user), "session_token": session["token"], "expires_at": session["expires_at"]}


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "login": user["login"],
        "name": user["name"],
        "email": user["email"],
        "avatar_url": user["avatar_url"],
    }


def user_from_request(request: Request) -> dict[str, Any] | None:
    token = _token_from_request(request)
    if not token:
        return None
    session = db.get_session(token)
    if not session:
        return None
    user = db.get_user(session["user_id"])
    if not user:
        return None
    account = db.get_oauth_account(user["id"], "github")
    return {
        **public_user(user),
        "access_token": account["access_token"] if account else "",
    }


def _token_from_request(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return request.cookies.get(COOKIE_NAME)


def set_session_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=s.oauth_cookie_secure,
        samesite="lax",
        max_age=s.session_ttl_seconds,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def logout(request: Request, response: Response) -> None:
    token = _token_from_request(request)
    if token:
        db.delete_session(token)
    clear_session_cookie(response)
