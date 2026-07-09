"""GitHub App auth + PR fetch + comment write-back."""

from __future__ import annotations

import logging
import re
import time
from functools import lru_cache

import httpx
import jwt

from src.config import get_settings

logger = logging.getLogger("github_app")
GH_API = "https://api.github.com"
MARKER_RE = re.compile(r"#(\d+)")


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
