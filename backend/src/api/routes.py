"""HTTP API — thin routing layer."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, HTTPException, Request

from src.config import get_settings
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
    RepoTree,
)
from src.services.graph import build_knowledge_graph
from src.services.graph_layers import connect_layers
from src.services.jobs import (
    create_analyze_job,
    create_crawl_job,
    create_ingest_job,
    run_crawl_job,
    run_ingest_job,
    run_job,
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
async def analyze(req: AnalyzeRequest) -> JobCreated:
    if not req.token:
        raise HTTPException(400, "missing token")
    status = create_analyze_job(req.full_name)
    asyncio.create_task(run_job(status.job_id, req.token, req.full_name, req.ref, req.build_graph))
    return JobCreated(job_id=status.job_id, state=status.state)


@router.get("/analyze/{job_id}", response_model=JobStatus)
async def get_status(job_id: str) -> JobStatus:
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
async def graph_connect(req: GraphConnectRequest) -> dict:
    ctx = RepoContext.from_request(req.full_name, req.tree, req.crawl, req.requirements)
    paths = [f.get("path", "") for f in (ctx.tree or {}).get("files", [])]
    return await connect_layers(req.full_name, ctx.requirements, ctx.crawl, paths)


@router.post("/crawl", response_model=JobCreated)
async def crawl(req: CrawlRequest) -> JobCreated:
    if not req.base_url:
        raise HTTPException(400, "missing base_url")
    status = create_crawl_job(req.full_name or None)
    asyncio.create_task(run_crawl_job(status.job_id, req))
    return JobCreated(job_id=status.job_id, state=status.state)


@router.post("/ingest", response_model=JobCreated)
async def ingest(req: IngestRequest) -> JobCreated:
    if not req.source:
        raise HTTPException(400, "missing source")
    status = create_ingest_job(req.full_name or None)
    asyncio.create_task(run_ingest_job(status.job_id, req))
    return JobCreated(job_id=status.job_id, state=status.state)


@router.post("/reason", status_code=202)
async def reason(req: ReasonRequest) -> dict[str, str]:
    ctx = RepoContext.from_request(req.full_name, req.tree, req.crawl, req.requirements)
    asyncio.create_task(run_reason_job(req.full_name, req.pr_number, ctx))
    return {"status": "accepted", "repo": req.full_name, "pr": str(req.pr_number)}


@router.post("/webhook/github", status_code=202)
async def github_webhook(request: Request) -> dict[str, str]:
    settings = get_settings()
    if not settings.github_webhook_secret:
        raise HTTPException(503, "webhook not configured")
    raw = await request.body()
    if not _verify_signature(settings.github_webhook_secret, raw, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(401, "invalid signature")
    event = request.headers.get("X-GitHub-Event", "")
    if event == "ping":
        return {"status": "pong"}
    if event != "pull_request":
        return {"status": "ignored", "event": event}
    payload = json.loads(raw)
    action = payload.get("action", "")
    if action not in {"opened", "reopened", "synchronize", "ready_for_review"}:
        return {"status": "ignored", "action": action}
    full_name = payload["repository"]["full_name"]
    number = payload["pull_request"]["number"]
    asyncio.create_task(run_reason_job(full_name, number))
    return {"status": "accepted", "repo": full_name, "pr": str(number)}
