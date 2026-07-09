"""SQLite persistence: jobs + the three knowledge-graph artifact layers.

Tables
------
jobs            — async job lifecycle (analyze / crawl / ingest)
repo_trees      — code layer (AST RepoTree JSON), keyed by owner/repo
crawl_results   — UI layer (CrawlResult JSON), keyed by owner/repo
ingest_results  — requirements layer (IngestResult JSON), keyed by owner/repo

The frontend may still cache for display; the backend is the source of truth
for /reason and /graph/connect (no giant payloads on every request).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import get_settings

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS jobs (
    job_id      TEXT PRIMARY KEY,
    kind        TEXT NOT NULL CHECK (kind IN ('analyze', 'crawl', 'ingest')),
    state       TEXT NOT NULL DEFAULT 'pending'
                CHECK (state IN ('pending', 'running', 'done', 'error')),
    progress    REAL NOT NULL DEFAULT 0,
    message     TEXT NOT NULL DEFAULT '',
    error       TEXT,
    full_name   TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    expires_at  TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state);
CREATE INDEX IF NOT EXISTS idx_jobs_full_name ON jobs(full_name);

CREATE TABLE IF NOT EXISTS repo_trees (
    full_name   TEXT PRIMARY KEY,
    ref         TEXT NOT NULL DEFAULT '',
    tree_json   TEXT NOT NULL,
    job_id      TEXT REFERENCES jobs(job_id) ON DELETE SET NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crawl_results (
    full_name    TEXT PRIMARY KEY,
    base_url     TEXT NOT NULL,
    result_json  TEXT NOT NULL,
    job_id       TEXT REFERENCES jobs(job_id) ON DELETE SET NULL,
    updated_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_crawl_base_url ON crawl_results(base_url);

CREATE TABLE IF NOT EXISTS ingest_results (
    full_name    TEXT PRIMARY KEY,
    source       TEXT NOT NULL,
    source_type  TEXT NOT NULL DEFAULT 'url',
    result_json  TEXT NOT NULL,
    job_id       TEXT REFERENCES jobs(job_id) ON DELETE SET NULL,
    updated_at  TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_path() -> Path:
    path = Path(get_settings().sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


def create_job(kind: str, *, full_name: str | None = None) -> dict[str, Any]:
    job_id = str(uuid.uuid4())
    now = _now()
    ttl = get_settings().job_ttl_seconds
    expires = (
        datetime.now(timezone.utc).timestamp() + ttl
        if ttl > 0
        else None
    )
    expires_at = (
        datetime.fromtimestamp(expires, tz=timezone.utc).isoformat()
        if expires
        else None
    )
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO jobs (job_id, kind, state, full_name, created_at, updated_at, expires_at)
            VALUES (?, ?, 'pending', ?, ?, ?, ?)
            """,
            (job_id, kind, full_name, now, now, expires_at),
        )
    return get_job(job_id)  # type: ignore[return-value]


def get_job(job_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    return dict(row) if row else None


def update_job(
    job_id: str,
    *,
    state: str | None = None,
    progress: float | None = None,
    message: str | None = None,
    error: str | None = None,
) -> dict[str, Any] | None:
    fields: list[str] = ["updated_at = ?"]
    values: list[Any] = [_now()]
    if state is not None:
        fields.append("state = ?")
        values.append(state)
    if progress is not None:
        fields.append("progress = ?")
        values.append(progress)
    if message is not None:
        fields.append("message = ?")
        values.append(message)
    if error is not None:
        fields.append("error = ?")
        values.append(error)
    values.append(job_id)
    with _connect() as conn:
        conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE job_id = ?", values)
    return get_job(job_id)


def delete_expired_jobs() -> int:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM jobs WHERE expires_at IS NOT NULL AND expires_at < ?",
            (_now(),),
        )
        return cur.rowcount


# ---------------------------------------------------------------------------
# Code layer — repo AST trees
# ---------------------------------------------------------------------------


def save_repo_tree(
    full_name: str,
    tree: dict[str, Any],
    *,
    ref: str = "",
    job_id: str | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO repo_trees (full_name, ref, tree_json, job_id, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(full_name) DO UPDATE SET
                ref = excluded.ref,
                tree_json = excluded.tree_json,
                job_id = excluded.job_id,
                updated_at = excluded.updated_at
            """,
            (full_name, ref, json.dumps(tree), job_id, _now()),
        )


def get_repo_tree(full_name: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT tree_json FROM repo_trees WHERE full_name = ?", (full_name,)
        ).fetchone()
    return json.loads(row["tree_json"]) if row else None


# ---------------------------------------------------------------------------
# UI layer — crawl results
# ---------------------------------------------------------------------------


def save_crawl_result(
    full_name: str,
    base_url: str,
    result: dict[str, Any],
    *,
    job_id: str | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO crawl_results (full_name, base_url, result_json, job_id, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(full_name) DO UPDATE SET
                base_url = excluded.base_url,
                result_json = excluded.result_json,
                job_id = excluded.job_id,
                updated_at = excluded.updated_at
            """,
            (full_name, base_url, json.dumps(result), job_id, _now()),
        )


def get_crawl_result(full_name: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT result_json FROM crawl_results WHERE full_name = ?", (full_name,)
        ).fetchone()
    return json.loads(row["result_json"]) if row else None


# ---------------------------------------------------------------------------
# Requirements layer — ingest results
# ---------------------------------------------------------------------------


def save_ingest_result(
    full_name: str,
    source: str,
    source_type: str,
    result: dict[str, Any],
    *,
    job_id: str | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ingest_results
                (full_name, source, source_type, result_json, job_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(full_name) DO UPDATE SET
                source = excluded.source,
                source_type = excluded.source_type,
                result_json = excluded.result_json,
                job_id = excluded.job_id,
                updated_at = excluded.updated_at
            """,
            (full_name, source, source_type, json.dumps(result), job_id, _now()),
        )


def get_ingest_result(full_name: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT result_json FROM ingest_results WHERE full_name = ?", (full_name,)
        ).fetchone()
    return json.loads(row["result_json"]) if row else None


def get_ingest_requirements(full_name: str) -> list[dict[str, Any]]:
    """Return just the requirements list for graph/reason layers."""
    result = get_ingest_result(full_name)
    if not result:
        return []
    return result.get("requirements") or []


# ---------------------------------------------------------------------------
# All three layers — used by /graph/connect and /reason
# ---------------------------------------------------------------------------


def get_repo_context(full_name: str) -> dict[str, Any]:
    """Load code + UI + requirements artifacts for one repo."""
    return {
        "full_name": full_name,
        "tree": get_repo_tree(full_name),
        "crawl": get_crawl_result(full_name),
        "requirements": get_ingest_requirements(full_name),
    }
