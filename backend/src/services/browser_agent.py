"""browser-use cloud agent — screen discovery and cloud screenshots."""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from src.config import get_settings
from src.models.schemas import CrawlRequest, LoginConfig

logger = logging.getLogger("browser_agent")

_URL_RE = re.compile(r"https?://[^\s'\"<>]+")


class AgentScreen(BaseModel):
    url: str
    title: str = ""
    label: str = ""
    purpose: str = ""
    authenticated: bool = False
    primary_actions: list[str] = Field(default_factory=list)


class AgentTransition(BaseModel):
    from_url: str
    to_url: str
    action: str = "navigate"


class AgentCrawlPlan(BaseModel):
    screens: list[AgentScreen] = Field(default_factory=list)
    transitions: list[AgentTransition] = Field(default_factory=list)
    summary: str = ""


class AgentDiscovery(BaseModel):
    """browser-use session output plus cloud screenshot URLs from agent steps."""

    plan: AgentCrawlPlan
    session_id: str = ""
    screenshots_by_url: dict[str, str] = Field(default_factory=dict)
    screenshots_ordered: list[str] = Field(default_factory=list)


def _login_hint(login: LoginConfig | None) -> str:
    if not login:
        return ""
    return (
        f"First log in at {login.login_url} with username '{login.username}' "
        f"and password '{login.password}', then continue exploring authenticated areas."
    )


def _task(req: CrawlRequest) -> str:
    settings = get_settings()
    routes_hint = ""
    if req.routes:
        paths = ", ".join(r.path for r in req.routes)
        routes_hint = f" Must include these paths if reachable: {paths}."
    return (
        f"You are a QA explorer mapping a web application for test coverage.\n"
        f"Start at {req.base_url}. {_login_hint(req.login)}\n"
        f"Discover up to {settings.crawl_max_screens} distinct screens the product user would see. "
        f"Click through main user flows (navigation, forms, checkout, etc.).{routes_hint}\n"
        "For each screen return: absolute url, page title, short label, purpose, "
        "whether it requires auth, and primary_actions (buttons/links a user would click).\n"
        "Also record transitions: from_url, to_url, action taken."
    )


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc.lower()}{path}"


def _extract_url(text: str) -> str:
    if not text:
        return ""
    match = _URL_RE.search(text)
    if not match:
        return ""
    return match.group(0).rstrip(".,);]")


async def _collect_session_screenshots(client: object, session_id: str) -> tuple[dict[str, str], list[str]]:
    """Pull screenshot_url from each browser-use session message."""
    by_url: dict[str, str] = {}
    ordered: list[str] = []

    after: str | None = None
    while True:
        resp = await client.sessions.messages(session_id, after=after, limit=100)  # type: ignore[attr-defined]
        if not resp.messages:
            break

        for message in resp.messages:
            shot = message.screenshot_url
            if not shot:
                continue
            ordered.append(shot)
            hint = _extract_url(message.data) or _extract_url(message.summary or "")
            if hint:
                by_url[normalize_url(hint)] = shot

        if not resp.has_more:
            break
        after = str(resp.messages[-1].id)

    session = await client.sessions.get(session_id)  # type: ignore[attr-defined]
    if session.screenshot_url and not ordered:
        ordered.append(session.screenshot_url)

    return by_url, ordered


def attach_screenshots(screens: list, discovery: AgentDiscovery) -> None:
    """Map cloud screenshot URLs onto discovered screens."""
    used: set[str] = set()
    for index, screen in enumerate(screens):
        if screen.screenshot_url:
            continue
        key = normalize_url(screen.url)
        shot = discovery.screenshots_by_url.get(key)
        if shot and key not in used:
            screen.screenshot_url = shot
            used.add(key)
        elif index < len(discovery.screenshots_ordered):
            screen.screenshot_url = discovery.screenshots_ordered[index]


async def discover_screens(req: CrawlRequest) -> AgentDiscovery | None:
    """Run browser-use agent; return plan plus cloud screenshot URLs. None if no API key."""
    settings = get_settings()
    if not settings.browser_use_api_key:
        logger.warning("BROWSER_USE_API_KEY not set — skipping agent discovery")
        return None

    try:
        from browser_use_sdk.v3 import AsyncBrowserUse
    except ImportError:
        logger.warning("browser-use-sdk not installed")
        return None

    client = AsyncBrowserUse(api_key=settings.browser_use_api_key)
    logger.info("browser-use agent starting for %s", req.base_url)
    result = await client.run(
        _task(req),
        output_schema=AgentCrawlPlan,
        max_cost_usd=settings.crawl_agent_max_cost_usd,
    )
    plan = result.output
    if isinstance(plan, dict):
        plan = AgentCrawlPlan.model_validate(plan)

    session_id = str(result.id)
    by_url, ordered = await _collect_session_screenshots(client, session_id)
    logger.info(
        "browser-use found %d screens, %d transitions, %d screenshots",
        len(plan.screens),
        len(plan.transitions),
        len(ordered),
    )
    return AgentDiscovery(
        plan=plan,
        session_id=session_id,
        screenshots_by_url=by_url,
        screenshots_ordered=ordered,
    )
