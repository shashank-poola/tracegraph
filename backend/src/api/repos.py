"""Dashboard API — user's GitHub repos, tracking, and PR list."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException

from src.core.deps import get_current_user
from src.services import github_app, github_repos, storage as db

logger = logging.getLogger("repos")
router = APIRouter(prefix="/repos", tags=["repos"])


@router.get("/profile")
async def profile(user: dict = Depends(get_current_user)) -> dict:
    token = user.get("access_token", "")
    if not token:
        raise HTTPException(401, "no GitHub token on session")
    gh_profile = await github_repos.get_authenticated_profile(token)
    gh_profile["tracked_count"] = len(db.list_tracked_repos(user["id"]))
    return gh_profile


@router.get("")
async def list_repos(user: dict = Depends(get_current_user)) -> dict:
    token = user.get("access_token", "")
    if not token:
        raise HTTPException(401, "no GitHub token on session")
    repos = await github_repos.list_user_repos(token)
    tracked = db.list_tracked_repos(user["id"])
    for r in repos:
        r["tracked"] = r["full_name"] in tracked
    return {"repos": repos, "tracked_count": len(tracked)}


@router.post("/{owner}/{repo}/track")
async def track(owner: str, repo: str, user: dict = Depends(get_current_user)) -> dict:
    db.track_repo(user["id"], f"{owner}/{repo}")
    return {"status": "tracked", "full_name": f"{owner}/{repo}"}


@router.delete("/{owner}/{repo}/track")
async def untrack(owner: str, repo: str, user: dict = Depends(get_current_user)) -> dict:
    db.untrack_repo(user["id"], f"{owner}/{repo}")
    return {"status": "untracked", "full_name": f"{owner}/{repo}"}


@router.get("/{owner}/{repo}/app-installed")
async def repo_app_installed(owner: str, repo: str, user: dict = Depends(get_current_user)) -> dict:
    _ = user
    full_name = f"{owner}/{repo}"
    installed = await github_app.repo_has_app_installed(full_name)
    return {"installed": installed, "required": github_app.app_install_configured()}


@router.get("/{owner}/{repo}")
async def repo_detail(owner: str, repo: str, user: dict = Depends(get_current_user)) -> dict:
    token = user.get("access_token", "")
    if not token:
        raise HTTPException(401, "no GitHub token on session")
    full_name = f"{owner}/{repo}"
    try:
        info, commits, prs = await asyncio.gather(
            github_repos.get_repo(token, full_name),
            github_repos.commit_count(token, full_name),
            github_repos.list_pull_requests(token, full_name),
        )
    except RuntimeError as exc:
        raise HTTPException(404, str(exc)) from exc

    ctx = db.get_repo_context(full_name, user_id=user["id"])
    info["commit_count"] = commits
    info["pull_request_count"] = len(prs)
    info["tracked"] = full_name in db.list_tracked_repos(user["id"])
    info["status"] = {
        "has_tree": ctx.get("tree") is not None,
        "has_crawl": ctx.get("crawl") is not None,
        "has_requirements": bool(ctx.get("requirements")),
        "has_graph": bool((ctx.get("tree") or {}).get("graph")),
    }
    return info


@router.get("/{owner}/{repo}/pulls")
async def repo_pulls(owner: str, repo: str, user: dict = Depends(get_current_user)) -> dict:
    token = user.get("access_token", "")
    if not token:
        raise HTTPException(401, "no GitHub token on session")
    full_name = f"{owner}/{repo}"
    try:
        prs = await github_repos.list_pull_requests(token, full_name)
    except RuntimeError as exc:
        raise HTTPException(404, str(exc)) from exc

    for pr in prs:
        review = db.get_pr_review(full_name, pr["number"], user_id=user["id"])
        pr["review"] = (
            {
                "verdict": review["verdict"],
                "risk": review["risk"],
                "good_enough": review["good_enough"],
                "summary": review["summary"],
                "comment_url": review["comment_url"],
            }
            if review
            else None
        )
    return {"pulls": prs}


@router.get("/{owner}/{repo}/tree")
async def repo_tree(owner: str, repo: str, user: dict = Depends(get_current_user)) -> dict:
    full_name = f"{owner}/{repo}"
    tree = db.get_repo_tree(full_name, user_id=user["id"])
    if not tree:
        raise HTTPException(404, "no knowledge graph for this repository")
    return tree


@router.get("/{owner}/{repo}/crawl")
async def repo_crawl(owner: str, repo: str, user: dict = Depends(get_current_user)) -> dict:
    full_name = f"{owner}/{repo}"
    result = db.get_crawl_result(full_name, user_id=user["id"])
    if not result:
        raise HTTPException(404, "no crawl result for this repository")
    return result


@router.get("/{owner}/{repo}/ingest")
async def repo_ingest(owner: str, repo: str, user: dict = Depends(get_current_user)) -> dict:
    full_name = f"{owner}/{repo}"
    result = db.get_ingest_result(full_name, user_id=user["id"])
    if not result:
        raise HTTPException(404, "no ingest result for this repository")
    return result


@router.get("/{owner}/{repo}/pulls/{number}")
async def repo_pull_detail(
    owner: str, repo: str, number: int, user: dict = Depends(get_current_user)
) -> dict:
    token = user.get("access_token", "")
    if not token:
        raise HTTPException(401, "no GitHub token on session")
    full_name = f"{owner}/{repo}"
    try:
        pr = await github_repos.get_pull_request(token, full_name, number)
    except RuntimeError as exc:
        raise HTTPException(404, str(exc)) from exc
    review = db.get_pr_review(full_name, number, user_id=user["id"])
    pr["review"] = (
        {
            "verdict": review["verdict"],
            "risk": review["risk"],
            "good_enough": review["good_enough"],
            "summary": review["summary"],
            "comment_url": review["comment_url"],
        }
        if review
        else None
    )
    return pr
