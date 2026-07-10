"""HTTP API — thin routing layer."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from src.config import get_settings
from src.core.deps import get_optional_user
from src.models.schemas import (
    AnalyzeRequest,
    CrawlRequest,
    GraphConnectRequest,
    GraphInfo,
    GraphRequest,
    IngestRequest,
    JobCreated,
    JobStatus,
    ReasonRequest,
)
from src.services.graph import build_knowledge_graph
from src.services.graph_layers import connect_layers
from src.services.github_app import record_installation_webhook
from src.services.jobs import (
    create_analyze_job,
    create_crawl_job,
    create_ingest_job,
    run_analyze_job,
    run_crawl_job,
    run_ingest_job,
    run_reason_job,
    store,
)
from src.services.pr_review import RepoContext

logger = logging.getLogger("routes")
router = APIRouter()


def _verify_signature(secret: str, body: bytes, header: str | None) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/analyze", response_model=JobCreated)
async def analyze(
    req: AnalyzeRequest,
    user: dict | None = Depends(get_optional_user),
) -> JobCreated:
    token = req.token or (user or {}).get("access_token", "")
    if not token:
        raise HTTPException(401, "login via /auth/github/login or pass token")
    user_id = (user or {}).get("id", "")
    status = create_analyze_job(req.full_name)
    asyncio.create_task(
        run_analyze_job(status.job_id, token, req.full_name, req.ref, req.build_graph, user_id)
    )
    return JobCreated(job_id=status.job_id, state=status.state)


@router.get("/jobs/{job_id}", response_model=JobStatus)
@router.get("/analyze/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str) -> JobStatus:
    """Poll any job (analyze, crawl, or ingest). ``/analyze/{id}`` kept for compatibility."""
    status = store.get(job_id)
    if not status:
        raise HTTPException(404, "job not found or expired")
    return status


@router.post("/graph", response_model=GraphInfo)
async def graph(req: GraphRequest) -> GraphInfo:
    result = await build_knowledge_graph(req.tree)
    if result is None:
        raise HTTPException(503, "Neo4j not configured")
    return result


@router.post("/graph/connect")
async def graph_connect(
    req: GraphConnectRequest,
    user: dict | None = Depends(get_optional_user),
) -> dict:
    user_id = (user or {}).get("id", "")
    ctx = RepoContext.from_request(req.full_name, req.tree, req.crawl, req.requirements, user_id)
    paths = [f.get("path", "") for f in (ctx.tree or {}).get("files", [])]
    return await connect_layers(req.full_name, ctx.requirements, ctx.crawl, paths)


@router.post("/crawl", response_model=JobCreated)
async def crawl(
    req: CrawlRequest,
    user: dict | None = Depends(get_optional_user),
) -> JobCreated:
    if not req.base_url:
        raise HTTPException(400, "missing base_url")
    user_id = (user or {}).get("id", "")
    status = create_crawl_job(req.full_name or None)
    asyncio.create_task(run_crawl_job(status.job_id, req, user_id))
    return JobCreated(job_id=status.job_id, state=status.state)


@router.post("/ingest", response_model=JobCreated)
async def ingest(
    req: IngestRequest,
    user: dict | None = Depends(get_optional_user),
) -> JobCreated:
    if not req.source:
        raise HTTPException(400, "missing source")
    if not req.token and req.source_type in {"github_repo", "github_readme"}:
        req.token = (user or {}).get("access_token", "")
    user_id = (user or {}).get("id", "")
    status = create_ingest_job(req.full_name or None)
    asyncio.create_task(run_ingest_job(status.job_id, req, user_id))
    return JobCreated(job_id=status.job_id, state=status.state)


@router.post("/reason", status_code=202)
async def reason(
    req: ReasonRequest,
    user: dict | None = Depends(get_optional_user),
) -> dict[str, str]:
    user_id = (user or {}).get("id", "")
    ctx = RepoContext.from_request(req.full_name, req.tree, req.crawl, req.requirements, user_id)
    asyncio.create_task(run_reason_job(req.full_name, req.pr_number, ctx))
    return {"status": "accepted", "repo": req.full_name, "pr": str(req.pr_number)}


@router.post("/webhook/github", status_code=202)
async def github_webhook(request: Request) -> dict[str, str]:
    settings = get_settings()
    if not settings.github_webhook_secret:
        logger.warning("webhook rejected: GITHUB_WEBHOOK_SECRET not configured")
        raise HTTPException(503, "webhook not configured")
    raw = await request.body()
    if not _verify_signature(settings.github_webhook_secret, raw, request.headers.get("X-Hub-Signature-256")):
        logger.warning("webhook rejected: invalid signature")
        raise HTTPException(401, "invalid signature")
    event = request.headers.get("X-GitHub-Event", "")
    logger.info("webhook received event=%s bytes=%d", event, len(raw))
    if event == "ping":
        return {"status": "pong"}
    payload = json.loads(raw)
    if event == "installation":
        record_installation_webhook(payload.get("installation") or {}, action=payload.get("action", ""))
        return {"status": "ok", "event": event, "action": payload.get("action", "")}
    if event != "pull_request":
        logger.info("webhook ignored event=%s", event)
        return {"status": "ignored", "event": event}
    action = payload.get("action", "")
    if action not in {"opened", "reopened", "synchronize", "ready_for_review"}:
        logger.info("webhook ignored pull_request action=%s", action)
        return {"status": "ignored", "action": action}
    full_name = payload["repository"]["full_name"]
    number = payload["pull_request"]["number"]
    logger.info("webhook accepted pull_request %s#%s action=%s", full_name, number, action)
    asyncio.create_task(run_reason_job(full_name, number))
    return {"status": "accepted", "repo": full_name, "pr": str(number)}
