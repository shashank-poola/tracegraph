"""browser-use cloud agent — autonomous screen discovery."""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from src.config import get_settings
from src.models.schemas import CrawlRequest, LoginConfig

logger = logging.getLogger("browser_agent")


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


async def discover_screens(req: CrawlRequest) -> AgentCrawlPlan | None:
    """Run browser-use agent to autonomously map screens + flows. None if no API key."""
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
    logger.info(
        "browser-use found %d screens, %d transitions",
        len(plan.screens),
        len(plan.transitions),
    )
    return plan
