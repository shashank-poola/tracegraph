"""SQLite persistence: jobs + the three knowledge-graph artifact layers + PR reviews.

Tables
------
jobs            — async job lifecycle (analyze / crawl / ingest)
repo_trees      — code layer (AST RepoTree JSON), keyed by owner/repo
crawl_results   — UI layer (CrawlResult JSON), keyed by owner/repo
ingest_results  — requirements layer (IngestResult JSON), keyed by owner/repo
pr_reviews      — blast-radius verdicts from /reason and webhooks
users/sessions/oauth_* — backend GitHub OAuth

The frontend may still cache for display; the backend is the source of truth
for /reason and /graph/connect (no giant payloads on every request).
"""

from __future__ import annotations

import json
import secrets
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
    user_id     TEXT NOT NULL DEFAULT '',
    full_name   TEXT NOT NULL,
    ref         TEXT NOT NULL DEFAULT '',
    tree_json   TEXT NOT NULL,
    job_id      TEXT REFERENCES jobs(job_id) ON DELETE SET NULL,
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (user_id, full_name)
);

CREATE TABLE IF NOT EXISTS crawl_results (
    user_id      TEXT NOT NULL DEFAULT '',
    full_name    TEXT NOT NULL,
    base_url     TEXT NOT NULL,
    result_json  TEXT NOT NULL,
    job_id       TEXT REFERENCES jobs(job_id) ON DELETE SET NULL,
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (user_id, full_name)
);

CREATE INDEX IF NOT EXISTS idx_crawl_base_url ON crawl_results(base_url);

CREATE TABLE IF NOT EXISTS ingest_results (
    user_id      TEXT NOT NULL DEFAULT '',
    full_name    TEXT NOT NULL,
    source       TEXT NOT NULL,
    source_type  TEXT NOT NULL DEFAULT 'url',
    result_json  TEXT NOT NULL,
    job_id       TEXT REFERENCES jobs(job_id) ON DELETE SET NULL,
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (user_id, full_name)
);

CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    github_id   INTEGER UNIQUE NOT NULL,
    login       TEXT NOT NULL,
    name        TEXT NOT NULL DEFAULT '',
    email       TEXT NOT NULL DEFAULT '',
    avatar_url  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token       TEXT UNIQUE NOT NULL,
    expires_at  TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);

CREATE TABLE IF NOT EXISTS oauth_accounts (
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider        TEXT NOT NULL DEFAULT 'github',
    access_token    TEXT NOT NULL,
    refresh_token   TEXT,
    scope           TEXT NOT NULL DEFAULT '',
    token_expires_at TEXT,
    updated_at      TEXT NOT NULL,
    PRIMARY KEY (user_id, provider)
);

CREATE TABLE IF NOT EXISTS oauth_states (
    state       TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pr_reviews (
    user_id         TEXT NOT NULL DEFAULT '',
    full_name       TEXT NOT NULL,
    pr_number       INTEGER NOT NULL,
    head_sha        TEXT NOT NULL DEFAULT '',
    pr_title        TEXT NOT NULL DEFAULT '',
    verdict         TEXT NOT NULL DEFAULT 'comment',
    risk            TEXT NOT NULL DEFAULT 'low',
    good_enough     INTEGER NOT NULL DEFAULT 0,
    summary         TEXT NOT NULL DEFAULT '',
    verdict_json    TEXT NOT NULL,
    comment_url     TEXT,
    comment_body    TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    PRIMARY KEY (user_id, full_name, pr_number)
);

CREATE INDEX IF NOT EXISTS idx_pr_reviews_repo ON pr_reviews(full_name);

CREATE TABLE IF NOT EXISTS tracked_repos (
    user_id     TEXT NOT NULL,
    full_name   TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (user_id, full_name)
);

CREATE TABLE IF NOT EXISTS github_installations (
    installation_id INTEGER PRIMARY KEY,
    account_login   TEXT NOT NULL DEFAULT '',
    account_type    TEXT NOT NULL DEFAULT '',
    user_id         TEXT,
    installed_at    TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_github_installations_login
    ON github_installations(account_login);
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
    user_id: str = "",
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO repo_trees (user_id, full_name, ref, tree_json, job_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, full_name) DO UPDATE SET
                ref = excluded.ref,
                tree_json = excluded.tree_json,
                job_id = excluded.job_id,
                updated_at = excluded.updated_at
            """,
            (user_id, full_name, ref, json.dumps(tree), job_id, _now()),
        )


def get_repo_tree(full_name: str, *, user_id: str = "") -> dict[str, Any] | None:
    """Load a saved AST tree.

    When ``user_id`` is empty (webhook / system callers), return the most recently
    updated tree for the repo across all users so PR reviews still see dashboard data.
    """
    with _connect() as conn:
        if user_id:
            row = conn.execute(
                "SELECT tree_json FROM repo_trees WHERE user_id = ? AND full_name = ?",
                (user_id, full_name),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT tree_json FROM repo_trees
                WHERE full_name = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (full_name,),
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
    user_id: str = "",
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO crawl_results (user_id, full_name, base_url, result_json, job_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, full_name) DO UPDATE SET
                base_url = excluded.base_url,
                result_json = excluded.result_json,
                job_id = excluded.job_id,
                updated_at = excluded.updated_at
            """,
            (user_id, full_name, base_url, json.dumps(result), job_id, _now()),
        )


def get_crawl_result(full_name: str, *, user_id: str = "") -> dict[str, Any] | None:
    with _connect() as conn:
        if user_id:
            row = conn.execute(
                "SELECT result_json FROM crawl_results WHERE user_id = ? AND full_name = ?",
                (user_id, full_name),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT result_json FROM crawl_results
                WHERE full_name = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (full_name,),
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
    user_id: str = "",
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ingest_results
                (user_id, full_name, source, source_type, result_json, job_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, full_name) DO UPDATE SET
                source = excluded.source,
                source_type = excluded.source_type,
                result_json = excluded.result_json,
                job_id = excluded.job_id,
                updated_at = excluded.updated_at
            """,
            (user_id, full_name, source, source_type, json.dumps(result), job_id, _now()),
        )


def get_ingest_result(full_name: str, *, user_id: str = "") -> dict[str, Any] | None:
    with _connect() as conn:
        if user_id:
            row = conn.execute(
                "SELECT result_json FROM ingest_results WHERE user_id = ? AND full_name = ?",
                (user_id, full_name),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT result_json FROM ingest_results
                WHERE full_name = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (full_name,),
            ).fetchone()
    return json.loads(row["result_json"]) if row else None


def get_ingest_requirements(full_name: str, *, user_id: str = "") -> list[dict[str, Any]]:
    result = get_ingest_result(full_name, user_id=user_id)
    if not result:
        return []
    return result.get("requirements") or []


def get_repo_context(full_name: str, *, user_id: str = "") -> dict[str, Any]:
    return {
        "full_name": full_name,
        "tree": get_repo_tree(full_name, user_id=user_id),
        "crawl": get_crawl_result(full_name, user_id=user_id),
        "requirements": get_ingest_requirements(full_name, user_id=user_id),
    }


# ---------------------------------------------------------------------------
# PR reviews — blast-radius persistence
# ---------------------------------------------------------------------------


def save_pr_review(
    full_name: str,
    pr_number: int,
    *,
    head_sha: str = "",
    pr_title: str = "",
    verdict: str = "comment",
    risk: str = "low",
    good_enough: bool = False,
    summary: str = "",
    verdict_json: dict[str, Any],
    comment_url: str | None = None,
    comment_body: str | None = None,
    user_id: str = "",
) -> dict[str, Any]:
    now = _now()
    with _connect() as conn:
        existing = conn.execute(
            """
            SELECT created_at FROM pr_reviews
            WHERE user_id = ? AND full_name = ? AND pr_number = ?
            """,
            (user_id, full_name, pr_number),
        ).fetchone()
        created_at = existing["created_at"] if existing else now
        conn.execute(
            """
            INSERT INTO pr_reviews (
                user_id, full_name, pr_number, head_sha, pr_title,
                verdict, risk, good_enough, summary, verdict_json,
                comment_url, comment_body, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, full_name, pr_number) DO UPDATE SET
                head_sha = excluded.head_sha,
                pr_title = excluded.pr_title,
                verdict = excluded.verdict,
                risk = excluded.risk,
                good_enough = excluded.good_enough,
                summary = excluded.summary,
                verdict_json = excluded.verdict_json,
                comment_url = excluded.comment_url,
                comment_body = excluded.comment_body,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                full_name,
                pr_number,
                head_sha,
                pr_title,
                verdict,
                risk,
                int(good_enough),
                summary,
                json.dumps(verdict_json),
                comment_url,
                comment_body,
                created_at,
                now,
            ),
        )
    return get_pr_review(full_name, pr_number, user_id=user_id)  # type: ignore[return-value]


def get_pr_review(
    full_name: str,
    pr_number: int,
    *,
    user_id: str = "",
) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM pr_reviews
            WHERE user_id = ? AND full_name = ? AND pr_number = ?
            """,
            (user_id, full_name, pr_number),
        ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["good_enough"] = bool(data["good_enough"])
    data["verdict_json"] = json.loads(data["verdict_json"])
    return data


def list_pr_reviews(
    *,
    full_name: str | None = None,
    user_id: str = "",
    limit: int = 50,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM pr_reviews WHERE user_id = ?"
    params: list[Any] = [user_id]
    if full_name:
        query += " AND full_name = ?"
        params.append(full_name)
    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        data = dict(row)
        data["good_enough"] = bool(data["good_enough"])
        data["verdict_json"] = json.loads(data["verdict_json"])
        out.append(data)
    return out


# ---------------------------------------------------------------------------
# Tracked repos — dashboard favorites
# ---------------------------------------------------------------------------


def track_repo(user_id: str, full_name: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO tracked_repos (user_id, full_name, created_at) VALUES (?, ?, ?)",
            (user_id, full_name, _now()),
        )


def untrack_repo(user_id: str, full_name: str) -> None:
    with _connect() as conn:
        conn.execute(
            "DELETE FROM tracked_repos WHERE user_id = ? AND full_name = ?",
            (user_id, full_name),
        )


def list_tracked_repos(user_id: str) -> set[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT full_name FROM tracked_repos WHERE user_id = ?", (user_id,)
        ).fetchall()
    return {row["full_name"] for row in rows}


# ---------------------------------------------------------------------------
# Auth — users, sessions, OAuth
# ---------------------------------------------------------------------------


def upsert_user(
    *,
    github_id: int,
    login: str,
    name: str,
    email: str,
    avatar_url: str,
) -> dict[str, Any]:
    now = _now()
    with _connect() as conn:
        row = conn.execute("SELECT id FROM users WHERE github_id = ?", (github_id,)).fetchone()
        if row:
            user_id = row["id"]
            conn.execute(
                """
                UPDATE users SET login=?, name=?, email=?, avatar_url=?, updated_at=?
                WHERE id=?
                """,
                (login, name, email, avatar_url, now, user_id),
            )
        else:
            user_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO users (id, github_id, login, name, email, avatar_url, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, github_id, login, name, email, avatar_url, now, now),
            )
    return get_user(user_id)  # type: ignore[return-value]


def get_user(user_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def save_oauth_account(
    *,
    user_id: str,
    access_token: str,
    scope: str = "",
    refresh_token: str | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO oauth_accounts (user_id, provider, access_token, refresh_token, scope, updated_at)
            VALUES (?, 'github', ?, ?, ?, ?)
            ON CONFLICT(user_id, provider) DO UPDATE SET
                access_token = excluded.access_token,
                refresh_token = excluded.refresh_token,
                scope = excluded.scope,
                updated_at = excluded.updated_at
            """,
            (user_id, access_token, refresh_token, scope, _now()),
        )


def get_oauth_account(user_id: str, provider: str = "github") -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM oauth_accounts WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        ).fetchone()
    return dict(row) if row else None


def create_session(user_id: str) -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(48)
    now = _now()
    ttl = get_settings().session_ttl_seconds
    expires = datetime.fromtimestamp(
        datetime.now(timezone.utc).timestamp() + ttl, tz=timezone.utc
    ).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO sessions (id, user_id, token, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, user_id, token, expires, now),
        )
    return {"id": session_id, "token": token, "expires_at": expires, "user_id": user_id}


def get_session(token: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE token = ? AND expires_at > ?",
            (token, _now()),
        ).fetchone()
    return dict(row) if row else None


def delete_session(token: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def save_oauth_state(state: str) -> None:
    now = _now()
    expires = datetime.fromtimestamp(
        datetime.now(timezone.utc).timestamp() + 600, tz=timezone.utc
    ).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO oauth_states (state, created_at, expires_at) VALUES (?, ?, ?)",
            (state, now, expires),
        )


def pop_oauth_state(state: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT state FROM oauth_states WHERE state = ? AND expires_at > ?",
            (state, _now()),
        ).fetchone()
        if not row:
            return False
        conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        return True


def get_user_by_login(login: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE login = ?", (login,)).fetchone()
    return dict(row) if row else None


def save_github_installation(
    *,
    installation_id: int,
    account_login: str = "",
    account_type: str = "",
    user_id: str = "",
) -> None:
    now = _now()
    if not user_id and account_login:
        user = get_user_by_login(account_login)
        user_id = user["id"] if user else ""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO github_installations (
                installation_id, account_login, account_type, user_id, installed_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(installation_id) DO UPDATE SET
                account_login = excluded.account_login,
                account_type = excluded.account_type,
                user_id = CASE
                    WHEN excluded.user_id != '' THEN excluded.user_id
                    ELSE github_installations.user_id
                END,
                updated_at = excluded.updated_at
            """,
            (installation_id, account_login, account_type, user_id, now, now),
        )


def delete_github_installation(installation_id: int) -> None:
    with _connect() as conn:
        conn.execute(
            "DELETE FROM github_installations WHERE installation_id = ?",
            (installation_id,),
        )


def has_any_github_installation() -> bool:
    """True if at least one GitHub App installation is recorded locally."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT installation_id FROM github_installations LIMIT 1"
        ).fetchone()
    return row is not None


# Backwards-compatible alias — the app id was never used for filtering.
def has_github_installation_for_app(_app_id: int) -> bool:
    return has_any_github_installation()


def has_github_installation_for_login(login: str) -> bool:
    if not login:
        return False
    with _connect() as conn:
        row = conn.execute(
            "SELECT installation_id FROM github_installations WHERE lower(account_login) = lower(?)",
            (login,),
        ).fetchone()
    return row is not None
