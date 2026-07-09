"""Connect Requirements + UI layers onto the Neo4j code subgraph."""

from __future__ import annotations

import logging

from neo4j import AsyncGraphDatabase
from pydantic import BaseModel, Field, ValidationError

from src.config import get_settings
from src.core.json_util import extract_json
from src.core.llm import complete

logger = logging.getLogger("graph_layers")

_REQS = """
MERGE (r:Repo {full_name: $full_name})
WITH r
UNWIND $reqs AS q
  MERGE (req:Requirement {key: q.key})
  SET req.req_id = q.req_id, req.full_name = $full_name, req.title = q.title,
      req.user_action = q.user_action, req.expected_outcome = q.expected_outcome,
      req.priority = q.priority, req.covered_by_ui = q.covered_by_ui,
      req.implemented_in_code = q.implemented_in_code
  MERGE (r)-[:SPECIFIES]->(req)
"""
_SCREENS = """
MERGE (r:Repo {full_name: $full_name})
WITH r
UNWIND $screens AS s
  MERGE (sc:Screen {key: s.key})
  SET sc.full_name = $full_name, sc.url = s.url, sc.title = s.title,
      sc.label = s.label, sc.authenticated = s.authenticated
  MERGE (r)-[:HAS_SCREEN]->(sc)
"""
_FLOWS = """
UNWIND $edges AS e
  MATCH (a:Screen {key: e.src})
  MATCH (b:Screen {key: e.dst})
  MERGE (a)-[:NAVIGATES_TO]->(b)
"""
_COVERED = """
UNWIND $rels AS x
  MATCH (req:Requirement {key: x.req_key})
  MATCH (sc:Screen {key: x.screen_key})
  MERGE (req)-[:COVERED_BY]->(sc)
"""
_IMPL = """
UNWIND $rels AS x
  MATCH (req:Requirement {key: x.req_key})
  MATCH (f:File {key: x.file_key})
  MERGE (req)-[:IMPLEMENTED_BY]->(f)
"""
_GAPS = """
UNWIND $reqs AS q
  MATCH (req:Requirement {key: q.key})
  WHERE q.covered_by_ui = false
  MERGE (g:CoverageGap {key: q.key + '::gap'})
    ON CREATE SET g.full_name = $full_name,
      g.reason = 'no captured UI exercises this requirement'
  MERGE (req)-[:MISSING_UI_COVERAGE]->(g)
"""

_MAP_SYSTEM = (
    "Map each requirement to screens (urls/labels) and code file paths. "
    'Return ONLY JSON: {"mappings":[{"req_id":"R1","covered_by_screens":["..."],'
    '"implemented_by_files":["..."]}]}. Empty lists when unknown.'
)


class ReqMapping(BaseModel):
    req_id: str
    covered_by_screens: list[str] = Field(default_factory=list)
    implemented_by_files: list[str] = Field(default_factory=list)


class LayerMapping(BaseModel):
    mappings: list[ReqMapping] = Field(default_factory=list)


def _screen_key(repo: str, screen_id: str) -> str:
    return f"{repo}::screen::{screen_id}"


async def connect_layers(
    full_name: str,
    requirements: list[dict],
    crawl: dict | None,
    code_file_paths: list[str],
) -> dict:
    settings = get_settings()
    if not settings.neo4j_uri:
        return {"skipped": "NEO4J_URI not configured"}
    if not requirements and not crawl:
        return {"skipped": "no requirements or crawl to connect"}

    repo = full_name
    raw_screens = (crawl or {}).get("screens", [])
    screen_payload = [
        {
            "key": _screen_key(repo, s.get("screen_id") or s.get("url", "")),
            "url": s.get("url", ""),
            "title": s.get("title", ""),
            "label": s.get("label", ""),
            "authenticated": bool(s.get("authenticated")),
        }
        for s in raw_screens
    ]
    screen_by_name = {}
    for s, p in zip(raw_screens, screen_payload):
        for name in (s.get("url"), s.get("label"), s.get("title")):
            if name:
                screen_by_name[name.strip()] = p["key"]

    files_set = set(code_file_paths)
    cover_rels: list[dict] = []
    impl_rels: list[dict] = []
    covered_ids: set[str] = set()
    implemented_ids: set[str] = set()

    if requirements and (settings.zai_api_key or settings.groq_api_key or settings.gemini_api_key):
        req_lines = "\n".join(f"- {r.get('req_id')}: {r.get('title')}" for r in requirements)
        screen_lines = "\n".join(f"- {p['label'] or p['url']}" for p in screen_payload) or "(none)"
        file_lines = "\n".join(f"- {p}" for p in code_file_paths[:200]) or "(none)"
        try:
            raw = await complete(
                [
                    {"role": "system", "content": _MAP_SYSTEM},
                    {
                        "role": "user",
                        "content": f"Requirements:\n{req_lines}\n\nScreens:\n{screen_lines}\n\nFiles:\n{file_lines}",
                    },
                ],
                json_mode=True,
            )
            mapping = LayerMapping.model_validate(extract_json(raw))
            by_id = {m.req_id: m for m in mapping.mappings}
            for r in requirements:
                rid = r.get("req_id")
                m = by_id.get(rid)
                if not m:
                    continue
                req_key = f"{repo}::req::{rid}"
                for name in m.covered_by_screens:
                    if key := screen_by_name.get(name.strip()):
                        cover_rels.append({"req_key": req_key, "screen_key": key})
                        covered_ids.add(rid)
                for path in m.implemented_by_files:
                    p = path.strip()
                    if p in files_set:
                        impl_rels.append({"req_key": req_key, "file_key": f"{repo}:{p}"})
                        implemented_ids.add(rid)
        except (ValidationError, ValueError) as exc:
            logger.warning("layer mapping failed: %s", exc)

    req_payload = [
        {
            "key": f"{repo}::req::{r.get('req_id')}",
            "req_id": r.get("req_id", ""),
            "title": r.get("title", ""),
            "user_action": r.get("user_action", ""),
            "expected_outcome": r.get("expected_outcome", ""),
            "priority": r.get("priority", ""),
            "covered_by_ui": r.get("req_id") in covered_ids,
            "implemented_in_code": r.get("req_id") in implemented_ids,
        }
        for r in requirements
    ]

    flow_edges = []
    for e in (crawl or {}).get("transitions") or (crawl or {}).get("edges") or []:
        src = e.get("from_screen") or e.get("from")
        dst = e.get("to_screen") or e.get("to")
        if src and dst:
            flow_edges.append({"src": _screen_key(repo, src), "dst": _screen_key(repo, dst)})

    auth = (settings.neo4j_username, settings.neo4j_password)
    db = settings.neo4j_database or "neo4j"
    nodes = rels = 0
    async with AsyncGraphDatabase.driver(settings.neo4j_uri, auth=auth) as driver:
        await driver.verify_connectivity()
        for query, params in [
            (_REQS, {"full_name": repo, "reqs": req_payload}),
            (_SCREENS, {"full_name": repo, "screens": screen_payload}),
            (_FLOWS, {"edges": flow_edges}),
            (_COVERED, {"rels": cover_rels}),
            (_IMPL, {"rels": impl_rels}),
            (_GAPS, {"full_name": repo, "reqs": req_payload}),
        ]:
            _, summary, _ = await driver.execute_query(query, database_=db, **params)
            nodes += summary.counters.nodes_created
            rels += summary.counters.relationships_created

    uncovered = [r["req_id"] for r in req_payload if not r["covered_by_ui"]]
    return {
        "requirements": len(req_payload),
        "screens": len(screen_payload),
        "covered_by_ui": sorted(covered_ids),
        "implemented_in_code": sorted(implemented_ids),
        "uncovered_requirements": uncovered,
        "nodes_created": nodes,
        "relationships_created": rels,
        "absence_query": (
            f'MATCH (r:Requirement {{full_name:"{repo}"}})-[:MISSING_UI_COVERAGE]->'
            "(:CoverageGap) RETURN r.req_id, r.title"
        ),
    }
