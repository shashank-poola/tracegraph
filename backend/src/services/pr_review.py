"""PR blast-radius reasoning across Requirements + UI + Code layers."""

from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field, ValidationError

from src.config import get_settings
from src.core.json_util import extract_json
from src.core.llm import complete
from src.models.schemas import RepoTree
from src.services import storage as db
from src.services.ast_parser import build_tree
from src.services.describer import describe_tree
from src.services.github_app import PRContext
from src.services.github_fetch import download_tarball

logger = logging.getLogger("pr_review")

MARK_BEGIN = "<!-- tracegraph:begin -->"
MARK_END = "<!-- tracegraph:end -->"


class RepoContext:
  def __init__(
    self,
    tree: dict | None = None,
    crawl: dict | None = None,
    requirements: list[dict] | None = None,
  ):
    self.tree = tree
    self.crawl = crawl
    self.requirements = requirements or []

  @classmethod
  def from_storage(cls, full_name: str) -> "RepoContext":
    ctx = db.get_repo_context(full_name)
    return cls(tree=ctx.get("tree"), crawl=ctx.get("crawl"), requirements=ctx.get("requirements") or [])

  @classmethod
  def from_request(cls, full_name: str, tree=None, crawl=None, requirements=None) -> "RepoContext":
    stored = db.get_repo_context(full_name)
    return cls(
      tree=tree if tree is not None else stored.get("tree"),
      crawl=crawl if crawl is not None else stored.get("crawl"),
      requirements=requirements if requirements is not None else (stored.get("requirements") or []),
    )


class PRVerdict(BaseModel):
  verdict: str
  summary: str
  good_enough: bool
  risk: str = "low"
  changes_made: list[str] = Field(default_factory=list)
  ui_at_risk: list[str] = Field(default_factory=list)
  flows_affected: list[str] = Field(default_factory=list)
  requirements_at_risk: list[str] = Field(default_factory=list)
  issues_addressed: list[str] = Field(default_factory=list)
  suggestions: list[str] = Field(default_factory=list)


_SYSTEM = (
  "You are a testing-intelligence system. Given a PR and three layers — "
  "REQUIREMENTS (intended), DOM/UI (crawl), CODE (AST + graph) — produce "
  "blast radius for a QA lead who knows the product but not code. "
  "Call out requirements with no UI coverage (absence). "
  'Return ONLY JSON: {"verdict":"approve|request_changes|comment","summary":"...",'
  '"good_enough":true,"risk":"low|medium|high","changes_made":[],"ui_at_risk":[],'
  '"flows_affected":[],"requirements_at_risk":[],"issues_addressed":[],"suggestions":[]}'
)


def _bullets(items: list[str]) -> str:
  return "\n".join(f"- {x}" for x in items) if items else "_none_"


def _tree_digest(tree: RepoTree, changed: list[str]) -> str:
  changed_set = set(changed)
  lines = [f"Repo: {tree.full_name} — {tree.summary}"]
  for f in tree.files:
    if f.path not in changed_set:
      continue
    lines.append(f"\n### {f.path} — {f.description}")
    for fn in f.functions:
      lines.append(f"  - fn {fn.name}: {fn.description}")
    for c in f.classes:
      lines.append(f"  - class {c.name}: {c.description}")
  return "\n".join(lines)


def _graph_block(tree: RepoTree) -> str:
  g = tree.graph
  if not g:
    return "(no knowledge graph)"
  return f"Graph: {g.nodes_written} nodes, {g.relationships_written} rels. Console: {g.console_url}"


def _crawl_block(crawl: dict | None) -> str:
  if not crawl:
    return "(no crawl on record)"
  lines = [f"Crawl {crawl.get('base_url')} — {crawl.get('screen_count', 0)} screens:"]
  for s in (crawl.get("screens") or [])[:40]:
    lines.append(f"- {s.get('label') or s.get('title') or s.get('url')}")
  return "\n".join(lines)


def _requirements_block(requirements: list[dict]) -> str:
  if not requirements:
    return "(no ingested requirements)"
  return "\n".join(f"- [{r.get('req_id')}] {r.get('title')}" for r in requirements[:40])


def _issues_block(pr: PRContext) -> str:
  if not pr.issues:
    return "(no linked issues)"
  return "\n".join(f"- #{i['number']} {i['title']}" for i in pr.issues)


async def _resolve_tree(token: str, pr: PRContext, ctx: RepoContext) -> RepoTree | None:
  if ctx.tree:
    try:
      return RepoTree.model_validate(ctx.tree)
    except ValidationError as exc:
      logger.warning("cached tree invalid: %s", exc)
  try:
    fetched = await download_tarball(token, pr.full_name, pr.head_sha)
    tree = build_tree(pr.full_name, pr.head_sha, fetched.sources, fetched.total_file_count)
    return await describe_tree(tree, fetched.sources)
  except Exception as exc:  # noqa: BLE001
    logger.warning("live AST unavailable: %s", exc)
    return None


async def review_pr(token: str, pr: PRContext, ctx: RepoContext) -> tuple[PRVerdict, RepoTree | None]:
  tree = await _resolve_tree(token, pr, ctx)
  diff = pr.diff[: get_settings().max_file_bytes]
  human = (
    f"PR #{pr.number}: {pr.title}\n{pr.body or ''}\n\n"
    f"Issues:\n{_issues_block(pr)}\n\n"
    f"Changed: {', '.join(pr.changed_files)}\n\n"
    f"REQUIREMENTS:\n{_requirements_block(ctx.requirements)}\n\n"
    f"DOM/UI:\n{_crawl_block(ctx.crawl)}\n\n"
    f"CODE:\n{_tree_digest(tree, pr.changed_files) if tree else '(unavailable)'}\n\n"
    f"{_graph_block(tree) if tree else ''}\n\n"
    f"```diff\n{diff}\n```"
  )
  try:
    raw = await complete([{"role": "system", "content": _SYSTEM}, {"role": "user", "content": human}], json_mode=True)
    verdict = PRVerdict.model_validate(extract_json(raw))
  except (ValidationError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
    logger.warning("review parse failed: %s", exc)
    verdict = PRVerdict(
      verdict="comment",
      summary="Blast-radius analysis could not be structured.",
      good_enough=False,
      risk="medium",
      suggestions=["Re-run with full repo context (analyze + crawl + ingest)."],
    )
  return verdict, tree


_EMOJI = {"low": "🟢", "medium": "🟡", "high": "🔴"}
_VERDICT = {
  "approve": "✅ Looks good to merge",
  "request_changes": "🛑 Changes requested",
  "comment": "💬 Review notes",
}


def render_comment(pr: PRContext, v: PRVerdict, ctx: RepoContext, graph_url: str | None) -> str:
  layers = [
    "✅ Requirements" if ctx.requirements else "⚪ Requirements",
    f"✅ DOM/UI ({ctx.crawl.get('screen_count', 0)} screens)" if ctx.crawl else "⚪ DOM/UI",
    "✅ Code" if ctx.tree else "⚪ Code",
  ]
  parts = [
    MARK_BEGIN,
    "## 🔍 TraceGraph blast-radius report",
    f"**{_VERDICT.get(v.verdict, v.verdict)}** · risk {_EMOJI.get(v.risk, '')} **{v.risk}**",
    "",
    v.summary,
    "",
    "### UI at risk",
    _bullets(v.ui_at_risk),
    "",
    "### Flows affected",
    _bullets(v.flows_affected),
    "",
    "### Requirements losing coverage",
    _bullets(v.requirements_at_risk),
    "",
    "### What changed",
    _bullets(v.changes_made),
    "",
    "### Suggestions",
    _bullets(v.suggestions),
  ]
  if graph_url:
    parts += ["", f"[Knowledge graph]({graph_url})"]
  parts += ["", f"<sub>Layers: {' · '.join(layers)}</sub>", MARK_END]
  return "\n".join(parts)
