"""Job store + async pipelines.

Live progress lives in memory for fast polling. Job metadata is also written to
SQLite so completed work can be listed later. Polling a job after process restart
returns 404 — that is intentional for the local/dev model.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from src.config import get_settings
from src.models.schemas import (
    CrawlRequest,
    CrawlResult,
    IngestRequest,
    JobState,
    JobStatus,
    ScreenInfo,
)
from src.services import storage as db
from src.services.ast_parser import build_tree
from src.services.crawler import crawl_app
from src.services.describer import describe_tree
from src.services.github_app import fetch_pr_context, installation_token, upsert_pr_comment
from src.services.github_fetch import download_tarball
from src.services.graph import build_knowledge_graph
from src.services.ingest import ingest_doc
from src.services.pr_review import MARK_BEGIN, RepoContext, render_comment, review_pr

logger = logging.getLogger("jobs")

ProgressFn = Callable[[float, str], Awaitable[None]]


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobStatus] = {}
        self._created: dict[str, float] = {}

    def get(self, job_id: str) -> JobStatus | None:
        return self._jobs.get(job_id)

    def put(self, status: JobStatus) -> None:
        self._jobs[status.job_id] = status
        self._created[status.job_id] = time.time()
        self._evict()

    def _evict(self) -> None:
        ttl = get_settings().job_ttl_seconds
        now = time.time()
        for jid in [j for j, t in self._created.items() if now - t > ttl]:
            self._jobs.pop(jid, None)
            self._created.pop(jid, None)
        db.delete_expired_jobs()


store = JobStore()


def create_job(kind: str, full_name: str | None = None) -> JobStatus:
    row = db.create_job(kind, full_name=full_name)
    status = JobStatus(job_id=row["job_id"], state=JobState.pending, message="queued")
    store.put(status)
    return status


def create_analyze_job(full_name: str | None = None) -> JobStatus:
    return create_job("analyze", full_name)


def create_crawl_job(full_name: str | None = None) -> JobStatus:
    return create_job("crawl", full_name)


def create_ingest_job(full_name: str | None = None) -> JobStatus:
    return create_job("ingest", full_name)


def _bind_progress(status: JobStatus, job_id: str) -> ProgressFn:
    async def progress(value: float, message: str) -> None:
        status.state = JobState.running
        status.progress = round(min(max(value, 0.0), 1.0), 3)
        status.message = message
        db.update_job(job_id, progress=status.progress, message=message, state="running")

    return progress


def _fail(status: JobStatus, job_id: str, exc: BaseException) -> None:
    status.state = JobState.error
    status.error = str(exc) or type(exc).__name__
    status.message = "failed"
    db.update_job(job_id, state="error", error=status.error, message="failed")


async def run_analyze_job(
    job_id: str,
    token: str,
    full_name: str,
    ref: str,
    build_graph: bool = True,
    user_id: str = "",
) -> None:
    status = store.get(job_id)
    if not status:
        return

    progress = _bind_progress(status, job_id)
    try:
        await progress(0.05, "Fetching repository")
        fetched = await download_tarball(token, full_name, ref)
        del token

        await progress(0.35, "Parsing AST")
        tree = build_tree(full_name, ref, fetched.sources, fetched.total_file_count)
        await progress(0.4, "Describing files")
        tree = await describe_tree(tree, fetched.sources, progress)

        if build_graph:
            await progress(0.96, "Building Neo4j graph")
            try:
                tree.graph = await build_knowledge_graph(tree)
            except Exception as exc:  # noqa: BLE001
                logger.exception("graph failed: %s", exc)
                status.message = f"graph step failed: {exc}"

        status.result = tree
        status.state = JobState.done
        status.progress = 1.0
        if not status.message.startswith("graph step failed"):
            status.message = "complete"
        db.save_repo_tree(full_name, tree.model_dump(), ref=ref, job_id=job_id, user_id=user_id)
        db.update_job(job_id, state="done", progress=1.0, message=status.message)
    except Exception as exc:  # noqa: BLE001
        logger.exception("analyze job failed: %s", exc)
        _fail(status, job_id, exc)


# Backwards-compatible alias used by older imports / tests
run_job = run_analyze_job


async def run_crawl_job(job_id: str, req: CrawlRequest, user_id: str = "") -> None:
    status = store.get(job_id)
    if not status:
        return

    progress = _bind_progress(status, job_id)
    captured: list[ScreenInfo] = []

    async def on_screen(screen: ScreenInfo) -> None:
        # Surface each screen as it is captured so polling clients can render a live feed.
        captured.append(screen)
        status.crawl_result = CrawlResult(
            run_id=job_id,
            base_url=req.base_url,
            screen_count=len(captured),
            screens=list(captured),
        )

    try:
        await progress(0.02, "Starting crawl")
        result = await crawl_app(req, progress, on_screen)
        status.crawl_result = result
        if result.screen_count == 0 and result.capture_note:
            status.state = JobState.error
            status.error = result.capture_note
            status.progress = 1.0
            status.message = "crawl failed"
            db.update_job(
                job_id,
                state="error",
                error=result.capture_note,
                message="crawl failed",
                progress=1.0,
            )
            return
        status.state = JobState.done
        status.progress = 1.0
        status.message = f"crawled {result.screen_count} screens"
        if req.full_name:
            db.save_crawl_result(
                req.full_name, req.base_url, result.model_dump(), job_id=job_id, user_id=user_id
            )
        db.update_job(job_id, state="done", progress=1.0, message=status.message)
    except Exception as exc:  # noqa: BLE001
        logger.exception("crawl failed: %s", exc)
        _fail(status, job_id, exc)


async def run_ingest_job(job_id: str, req: IngestRequest, user_id: str = "") -> None:
    status = store.get(job_id)
    if not status:
        return

    progress = _bind_progress(status, job_id)
    try:
        await progress(0.02, "Fetch documentation")
        result = await ingest_doc(req, progress)
        status.ingest_result = result
        status.state = JobState.done
        status.progress = 1.0
        status.message = f"extracted {result.requirement_count} requirements"
        key = req.full_name or req.source
        db.save_ingest_result(
            key, req.source, req.source_type, result.model_dump(), job_id=job_id, user_id=user_id
        )
        db.update_job(job_id, state="done", progress=1.0, message=status.message)
    except Exception as exc:  # noqa: BLE001
        logger.exception("ingest failed: %s", exc)
        _fail(status, job_id, exc)


async def run_reason_job(full_name: str, pr_number: int, ctx: RepoContext | None = None) -> None:
    try:
        if ctx is None:
            # Webhooks have no session user — load the newest artifacts for this repo.
            ctx = RepoContext.from_storage(full_name, user_id="")
        token = await installation_token(full_name)
        pr = await fetch_pr_context(token, full_name, pr_number)
        verdict, tree = await review_pr(token, pr, ctx)
        graph_url = tree.graph.console_url if tree and tree.graph else None
        body = render_comment(pr, verdict, ctx, graph_url)
        url = await upsert_pr_comment(token, full_name, pr_number, body, MARK_BEGIN)
        db.save_pr_review(
            full_name,
            pr_number,
            head_sha=pr.head_sha,
            pr_title=pr.title,
            verdict=verdict.verdict,
            risk=verdict.risk,
            good_enough=verdict.good_enough,
            summary=verdict.summary,
            verdict_json=verdict.model_dump(),
            comment_url=url,
            comment_body=body,
            user_id=ctx.user_id if ctx else "",
        )
        logger.info("reason done %s#%d verdict=%s url=%s", full_name, pr_number, verdict.verdict, url)
    except Exception as exc:  # noqa: BLE001
        logger.exception("reason failed %s#%d: %s", full_name, pr_number, exc)
