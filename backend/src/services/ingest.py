"""Ingest PRD/README/spec into structured requirements."""

from __future__ import annotations

import logging
import re

import httpx

from src.config import get_settings
from src.core.json_util import extract_json
from src.core.llm import complete
from src.models.schemas import IngestRequest, IngestResult, Requirement

logger = logging.getLogger("ingest")
GH_API = "https://api.github.com"
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)

_REQ_SYSTEM = (
    "Turn product documentation into testable requirements for a QA lead. "
    'Return ONLY JSON: {"requirements":[{"title":"...","description":"...",'
    '"user_action":"...","expected_outcome":"..."}]}. '
    "Plain English, no code jargon. Skip non user-facing sections."
)
_OVERVIEW_SYSTEM = (
    "Write a product overview in markdown for a non-technical QA lead. "
    "Cover what the product does, main features, and typical user journeys."
)


async def _fetch_source(req: IngestRequest) -> str:
    if req.source_type == "text":
        return req.source
    if req.source_type == "github_readme":
        headers = {"Accept": "application/vnd.github.raw+json", "User-Agent": "tracegraph"}
        if req.token:
            headers["Authorization"] = f"Bearer {req.token}"
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(f"{GH_API}/repos/{req.source}/readme", headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"README fetch failed ({resp.status_code})")
            return resp.text
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(req.source, headers={"User-Agent": "tracegraph"})
        if resp.status_code != 200:
            raise RuntimeError(f"doc fetch failed ({resp.status_code})")
        return resp.text


def _split_sections(md: str) -> list[tuple[str, str]]:
    matches = list(_HEADING.finditer(md))
    if not matches:
        return [("Document", md.strip())]
    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        start, end = m.end(), matches[i + 1].start() if i + 1 < len(matches) else len(md)
        body = md[start:end].strip()
        if body:
            out.append((m.group(2).strip(), body))
    return out


def _has_llm() -> bool:
    s = get_settings()
    return bool(s.zai_api_key or s.groq_api_key or s.gemini_api_key)


async def _extract_requirements(heading: str, body: str) -> list[Requirement]:
    if not _has_llm():
        return [Requirement(req_id="", title=heading, source_anchor=heading)]
    try:
        raw = await complete(
            [
                {"role": "system", "content": _REQ_SYSTEM},
                {"role": "user", "content": f"Section: {heading}\n\n{body[:8000]}"},
            ],
            json_mode=True,
            temperature=0.1,
        )
        data = extract_json(raw)
        return [
            Requirement(
                req_id="",
                title=r.get("title", "").strip() or heading,
                description=r.get("description", "").strip(),
                user_action=r.get("user_action", "").strip(),
                expected_outcome=r.get("expected_outcome", "").strip(),
                source_anchor=heading,
            )
            for r in data.get("requirements", [])
        ]
    except Exception as exc:  # noqa: BLE001
        logger.warning("requirement extract failed %r: %s", heading, exc)
        return []


async def _generate_overview(raw: str, files: list[str]) -> str:
    if not _has_llm():
        return ""
    try:
        prefix = f"Doc files: {', '.join(files)}\n\n" if files else ""
        return await complete(
            [{"role": "system", "content": _OVERVIEW_SYSTEM}, {"role": "user", "content": prefix + raw[:16000]}],
            temperature=0.2,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("overview failed: %s", exc)
        return ""


async def _fetch_repo_docs(req: IngestRequest) -> tuple[str, list[str]]:
    from src.services.github_fetch import download_doc_files

    docs = await download_doc_files(req.token, req.source, "", (".md", ".vdk"))
    files = sorted(docs.keys())
    if not files:
        raise RuntimeError(f"No .md/.vdk files in {req.source}")
    return "\n\n".join(f"# {p}\n\n{docs[p]}" for p in files), files


async def ingest_doc(req: IngestRequest) -> IngestResult:
    files: list[str] = []
    if req.source_type == "github_repo":
        raw, files = await _fetch_repo_docs(req)
    else:
        raw = await _fetch_source(req)

    requirements: list[Requirement] = []
    for heading, body in _split_sections(raw):
        requirements.extend(await _extract_requirements(heading, body))
    for i, r in enumerate(requirements, start=1):
        r.req_id = f"R{i}"

    return IngestResult(
        source=req.source,
        source_type=req.source_type,
        requirement_count=len(requirements),
        requirements=requirements,
        overview=await _generate_overview(raw, files),
        excerpt=raw[:1000],
        files=files,
    )
