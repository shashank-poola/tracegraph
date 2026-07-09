"""GitHub API — user's own repos, repo detail, PR list, commit count.

Uses the user's OAuth access_token (session-scoped), not the GitHub App.
Powers the dashboard: repo list, repo detail header, and the PR panel.
"""

from __future__ import annotations

import re

import httpx

GH_API = "https://api.github.com"
_LAST_PAGE_RE = re.compile(r'[?&]page=(\d+)[^>]*>;\s*rel="last"')


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "tracegraph",
    }


def _shape_repo(r: dict) -> dict:
    return {
        "full_name": r["full_name"],
        "name": r["name"],
        "owner": r["owner"]["login"],
        "description": r.get("description") or "",
        "private": bool(r.get("private")),
        "language": r.get("language") or "",
        "stargazers_count": r.get("stargazers_count", 0),
        "forks_count": r.get("forks_count", 0),
        "default_branch": r.get("default_branch") or "main",
        "html_url": r.get("html_url", ""),
        "updated_at": r.get("updated_at") or "",
    }


_CONTRIB_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
  }
}
"""


async def get_contribution_calendar(token: str, login: str) -> dict:
    """Last ~52 weeks of contribution days for the profile heatmap."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{GH_API}/graphql",
            headers=_headers(token),
            json={"query": _CONTRIB_QUERY, "variables": {"login": login}},
        )
        if resp.status_code != 200:
            return {"total": 0, "days": []}
        data = resp.json()
        cal = (
            (data.get("data") or {})
            .get("user", {})
            .get("contributionsCollection", {})
            .get("contributionCalendar", {})
        )
        days: list[dict] = []
        for week in cal.get("weeks") or []:
            for day in week.get("contributionDays") or []:
                days.append(
                    {
                        "date": day.get("date", ""),
                        "count": day.get("contributionCount", 0),
                    }
                )
        return {
            "total": cal.get("totalContributions", 0),
            "days": days[-371:],  # ~53 weeks max grid width
        }


async def get_authenticated_profile(token: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{GH_API}/user", headers=_headers(token))
        if resp.status_code != 200:
            raise RuntimeError(f"profile fetch failed ({resp.status_code})")
        u = resp.json()
        login = u.get("login", "")
        contributions = await get_contribution_calendar(token, login)
        return {
            "login": login,
            "name": u.get("name") or login,
            "avatar_url": u.get("avatar_url", ""),
            "bio": u.get("bio") or "",
            "location": u.get("location") or "",
            "html_url": u.get("html_url", ""),
            "public_repos": u.get("public_repos", 0),
            "followers": u.get("followers", 0),
            "following": u.get("following", 0),
            "contributions": contributions,
        }


async def list_user_repos(token: str, *, max_pages: int = 3) -> list[dict]:
    repos: list[dict] = []
    async with httpx.AsyncClient(timeout=30) as client:
        for page in range(1, max_pages + 1):
            resp = await client.get(
                f"{GH_API}/user/repos",
                headers=_headers(token),
                params={"per_page": 100, "page": page, "sort": "updated", "affiliation": "owner,collaborator"},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"repo list failed ({resp.status_code})")
            batch = resp.json()
            repos.extend(_shape_repo(r) for r in batch)
            if len(batch) < 100:
                break
    return repos


async def get_repo(token: str, full_name: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{GH_API}/repos/{full_name}", headers=_headers(token))
        if resp.status_code != 200:
            raise RuntimeError(f"repo fetch failed ({resp.status_code}) for {full_name}")
        return _shape_repo(resp.json())


async def commit_count(token: str, full_name: str, ref: str = "") -> int:
    params = {"per_page": 1}
    if ref:
        params["sha"] = ref
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{GH_API}/repos/{full_name}/commits", headers=_headers(token), params=params
        )
        if resp.status_code != 200:
            return 0
        link = resp.headers.get("Link", "")
        match = _LAST_PAGE_RE.search(link)
        if match:
            return int(match.group(1))
        return len(resp.json())


async def list_pull_requests(token: str, full_name: str, *, state: str = "all") -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{GH_API}/repos/{full_name}/pulls",
            headers=_headers(token),
            params={"state": state, "per_page": 30, "sort": "updated", "direction": "desc"},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"PR list failed ({resp.status_code}) for {full_name}")
        return [
            {
                "number": pr["number"],
                "title": pr["title"],
                "state": "merged" if pr.get("merged_at") else pr.get("state", "open"),
                "author": (pr.get("user") or {}).get("login", ""),
                "html_url": pr.get("html_url", ""),
                "created_at": pr.get("created_at", ""),
                "updated_at": pr.get("updated_at", ""),
                "head_sha": (pr.get("head") or {}).get("sha", ""),
            }
            for pr in resp.json()
        ]
