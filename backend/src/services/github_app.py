"""GitHub App auth + install checks + PR fetch + comment write-back."""

from __future__ import annotations

import logging
import re
import time
from functools import lru_cache
from typing import Any

import httpx
import jwt

from src.config import get_settings
from src.services import storage as db

logger = logging.getLogger("github_app")
GH_API = "https://api.github.com"
MARKER_RE = re.compile(r"#(\d+)")


def _app_credentials_configured() -> bool:
    s = get_settings()
    if not s.github_app_id:
        return False
    if s.github_app_private_key:
        return True
    path = (s.github_app_private_key_path or "").strip()
    return bool(path)


def app_install_configured() -> bool:
    return _app_credentials_configured()


_resolved_slug: str | None = None


async def resolve_app_slug() -> str:
    global _resolved_slug
    s = get_settings()
    if s.github_app_slug:
        return s.github_app_slug
    if _resolved_slug:
        return _resolved_slug
    if not _app_credentials_configured():
        raise RuntimeError("GitHub App not configured (GITHUB_APP_ID + private key)")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{GH_API}/app", headers=_app_headers())
    if resp.status_code != 200:
        raise RuntimeError(
            f"failed to resolve app slug from GitHub ({resp.status_code}). "
            "Set GITHUB_APP_SLUG in backend/.env"
        )
    data = resp.json()
    slug = data.get("slug") or ""
    if not slug:
        html_url = data.get("html_url", "")
        slug = html_url.rstrip("/").split("/")[-1] if html_url else ""
    if not slug:
        raise RuntimeError("could not resolve app slug — set GITHUB_APP_SLUG in backend/.env")
    _resolved_slug = slug
    return slug


async def install_page_url() -> str:
    slug = await resolve_app_slug()
    return f"https://github.com/apps/{slug}/installations/new"


async def user_has_app_installed(access_token: str, *, user_login: str = "") -> bool:
    s = get_settings()
    if not s.github_app_id:
        return True

    if user_login and db.has_github_installation_for_login(user_login):
        return True

    if user_login and await _installation_exists_for_login(user_login):
        return True

    if not access_token:
        return False

    target = int(s.github_app_id)
    async with httpx.AsyncClient(timeout=30) as client:
        page = 1
        while True:
            resp = await client.get(
                f"{GH_API}/user/installations",
                headers=_token_headers(access_token),
                params={"per_page": 100, "page": page},
            )
            if resp.status_code != 200:
                logger.warning("user installations fetch failed (%s)", resp.status_code)
                return bool(user_login and db.has_github_installation_for_login(user_login))
            batch = resp.json().get("installations", [])
            for inst in batch:
                if inst.get("app_id") == target:
                    db.save_github_installation(
                        installation_id=int(inst["id"]),
                        account_login=(inst.get("account") or {}).get("login", ""),
                        account_type=(inst.get("account") or {}).get("type", ""),
                    )
                    return True
            if len(batch) < 100:
                break
            page += 1
    return bool(user_login and db.has_github_installation_for_login(user_login))


async def _installation_exists_for_login(user_login: str) -> bool:
    login = user_login.lower()
    async with httpx.AsyncClient(timeout=30) as client:
        page = 1
        while True:
            resp = await client.get(
                f"{GH_API}/app/installations",
                headers=_app_headers(),
                params={"per_page": 100, "page": page},
            )
            if resp.status_code != 200:
                logger.warning("app installations list failed (%s)", resp.status_code)
                return False
            batch = resp.json()
            if not isinstance(batch, list):
                batch = []
            for inst in batch:
                account = inst.get("account") or {}
                if (account.get("login") or "").lower() == login:
                    user = db.get_user_by_login(user_login)
                    db.save_github_installation(
                        installation_id=int(inst["id"]),
                        account_login=account.get("login", ""),
                        account_type=account.get("type", ""),
                        user_id=user["id"] if user else "",
                    )
                    return True
            link = resp.headers.get("Link", "")
            if 'rel="next"' not in link:
                break
            page += 1
    return False


async def confirm_user_installation(
    user_login: str,
    installation_id: int | None,
    *,
    access_token: str = "",
) -> bool:
    if installation_id:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{GH_API}/app/installations/{installation_id}",
                headers=_app_headers(),
            )
            if resp.status_code == 200:
                inst = resp.json()
                account = inst.get("account") or {}
                if (account.get("login") or "").lower() == user_login.lower():
                    user = db.get_user_by_login(user_login)
                    db.save_github_installation(
                        installation_id=int(inst["id"]),
                        account_login=account.get("login", ""),
                        account_type=account.get("type", ""),
                        user_id=user["id"] if user else "",
                    )
                    return True
    return await user_has_app_installed(access_token, user_login=user_login)


async def installation_status_for_user(
    access_token: str,
    *,
    user_login: str = "",
    installation_id: int | None = None,
) -> dict[str, Any]:
    if not app_install_configured():
        return {"required": False, "installed": True}
    if installation_id and user_login:
        await confirm_user_installation(user_login, installation_id, access_token=access_token)
    installed = await user_has_app_installed(access_token, user_login=user_login)
    return {"required": True, "installed": installed}


async def repo_has_app_installed(full_name: str) -> bool:
    if not app_install_configured():
        return True
    owner, repo = full_name.split("/", 1)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{GH_API}/repos/{owner}/{repo}/installation",
            headers=_app_headers(),
        )
        return resp.status_code == 200


def record_installation_webhook(installation: dict, *, action: str) -> None:
    installation_id = installation.get("id")
    if not installation_id:
        return
    account = installation.get("account") or {}
    if action == "deleted":
        db.delete_github_installation(int(installation_id))
        return
    if action in {"created", "added", "new_permissions_accepted"}:
        db.save_github_installation(
            installation_id=int(installation_id),
            account_login=account.get("login", ""),
            account_type=account.get("type", ""),
        )


@lru_cache
def _private_key() -> str:
    s = get_settings()
    if s.github_app_private_key:
        return s.github_app_private_key
    path = s.github_app_private_key_path
    if not path:
        raise RuntimeError("GitHub App private key not configured")
    if path.strip().startswith("-----BEGIN"):
        return path
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def app_jwt() -> str:
    s = get_settings()
    if not s.github_app_id:
        raise RuntimeError("GITHUB_APP_ID not configured")
    now = int(time.time())
    return jwt.encode(
        {"iat": now - 60, "exp": now + 600, "iss": s.github_app_id},
        _private_key(),
        algorithm="RS256",
    )


def _app_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {app_jwt()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "tracegraph-app",
    }


async def installation_token(full_name: str) -> str:
    owner, repo = full_name.split("/", 1)
    async with httpx.AsyncClient(timeout=30) as client:
        inst = await client.get(
            f"{GH_API}/repos/{owner}/{repo}/installation", headers=_app_headers()
        )
        if inst.status_code != 200:
            raise RuntimeError(f"App not installed on {full_name} ({inst.status_code})")
        tok = await client.post(
            f"{GH_API}/app/installations/{inst.json()['id']}/access_tokens",
            headers=_app_headers(),
        )
        if tok.status_code != 201:
            raise RuntimeError(f"installation token failed ({tok.status_code})")
        return tok.json()["token"]


def _token_headers(token: str, accept: str = "application/vnd.github+json") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "tracegraph",
    }


class PRContext:
    def __init__(
        self,
        full_name: str,
        number: int,
        title: str,
        body: str,
        head_sha: str,
        base_ref: str,
        head_ref: str,
        diff: str,
        changed_files: list[str],
        issues: list[dict],
        author: str = "",
        state: str = "open",
        url: str = "",
    ):
        self.full_name = full_name
        self.number = number
        self.title = title
        self.body = body
        self.head_sha = head_sha
        self.base_ref = base_ref
        self.head_ref = head_ref
        self.diff = diff
        self.changed_files = changed_files
        self.issues = issues
        self.author = author
        self.state = state
        self.url = url


async def fetch_pr_context(token: str, full_name: str, number: int) -> PRContext:
    owner, repo = full_name.split("/", 1)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        meta_r, diff_r, files_r = await _gather(
            client,
            (f"{GH_API}/repos/{owner}/{repo}/pulls/{number}", _token_headers(token)),
            (
                f"{GH_API}/repos/{owner}/{repo}/pulls/{number}",
                _token_headers(token, "application/vnd.github.v3.diff"),
            ),
            (
                f"{GH_API}/repos/{owner}/{repo}/pulls/{number}/files?per_page=100",
                _token_headers(token),
            ),
        )
        if meta_r.status_code != 200:
            raise RuntimeError(f"PR fetch failed ({meta_r.status_code})")
        meta = meta_r.json()
        diff = diff_r.text if diff_r.status_code == 200 else ""
        changed = [f["filename"] for f in files_r.json()] if files_r.status_code == 200 else []

        issues: list[dict] = []
        for n in sorted({int(x) for x in MARKER_RE.findall(meta.get("body") or "")}):
            ir = await client.get(
                f"{GH_API}/repos/{owner}/{repo}/issues/{n}", headers=_token_headers(token)
            )
            if ir.status_code == 200:
                j = ir.json()
                if "pull_request" not in j:
                    issues.append({"number": j["number"], "title": j["title"], "body": j.get("body") or ""})

    state = "merged" if meta.get("merged_at") else meta.get("state", "open")
    return PRContext(
        full_name=full_name,
        number=number,
        title=meta.get("title", ""),
        body=meta.get("body") or "",
        head_sha=meta["head"]["sha"],
        base_ref=meta["base"]["ref"],
        head_ref=meta["head"]["ref"],
        diff=diff,
        changed_files=changed,
        issues=issues,
        author=(meta.get("user") or {}).get("login", ""),
        state=state,
        url=meta.get("html_url", ""),
    )


async def _gather(client: httpx.AsyncClient, *reqs):
    import asyncio

    return await asyncio.gather(*(client.get(url, headers=h) for url, h in reqs))


async def upsert_pr_comment(token: str, full_name: str, number: int, body: str, marker: str) -> str:
    owner, repo = full_name.split("/", 1)
    base = f"{GH_API}/repos/{owner}/{repo}/issues/{number}/comments"
    async with httpx.AsyncClient(timeout=30) as client:
        existing = await client.get(f"{base}?per_page=100", headers=_token_headers(token))
        if existing.status_code == 200:
            for c in existing.json():
                if marker in (c.get("body") or ""):
                    patch = await client.patch(
                        f"{GH_API}/repos/{owner}/{repo}/issues/comments/{c['id']}",
                        headers=_token_headers(token),
                        json={"body": body},
                    )
                    if patch.status_code == 200:
                        return patch.json().get("html_url", "")
                    break
        resp = await client.post(base, headers=_token_headers(token), json={"body": body})
        if resp.status_code != 201:
            raise RuntimeError(f"comment post failed ({resp.status_code})")
        return resp.json().get("html_url", "")
