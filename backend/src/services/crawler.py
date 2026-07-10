"""Crawl: browser-use discovers screens and supplies cloud screenshots."""

from __future__ import annotations

import logging
import uuid
from typing import Awaitable, Callable
from urllib.parse import urljoin, urlparse

from src.config import get_settings
from src.core.llm import complete
from src.models.schemas import CrawlRequest, CrawlResult, RouteSpec, ScreenInfo, Transition
from src.services.browser_agent import AgentDiscovery, attach_screenshots, discover_screens
from src.services.screenshot import persist_screenshot_url

logger = logging.getLogger("crawler")
ProgressCb = Callable[[float, str], Awaitable[None]]
ScreenCb = Callable[[ScreenInfo], Awaitable[None]]

_LABEL_SYSTEM = (
    "Summarize this screen for a QA lead. Return ONLY JSON: "
    '{"label":"...","purpose":"...","primary_actions":["..."],"key_components":["..."]}'
)


def _resolve_url(base: str, path: str) -> str:
    return path if path.startswith("http") else urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def _screen_id(url: str) -> str:
    return urlparse(url).path or "/"


async def _label_screen(screen: ScreenInfo) -> None:
    settings = get_settings()
    if not settings.crawl_llm_labeling or screen.label:
        return
    if not (settings.zai_api_key or settings.groq_api_key or settings.gemini_api_key):
        return
    try:
        import json

        from src.core.json_util import extract_json

        structured = screen.structured_dom or [{"url": screen.url, "title": screen.title}]
        raw = await complete(
            [
                {"role": "system", "content": _LABEL_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"URL: {screen.url}\nTitle: {screen.title}\n"
                        f"DOM: {json.dumps(structured)[:6000]}"
                    ),
                },
            ],
            json_mode=True,
        )
        data = extract_json(raw)
        screen.label = data.get("label", screen.label)
        screen.purpose = data.get("purpose", screen.purpose)
        screen.primary_actions = data.get("primary_actions") or screen.primary_actions
        screen.key_components = data.get("key_components") or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("label failed %s: %s", screen.url, exc)


async def _persist_screen_shot(screen: ScreenInfo) -> None:
    if not screen.screenshot_url:
        return
    if screen.screenshot_url.startswith("data:"):
        return
    try:
        screen.screenshot_url = await persist_screenshot_url(screen.screenshot_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("screenshot persist failed %s: %s", screen.url, exc)


def _transitions(discovery: AgentDiscovery, screens: list[ScreenInfo]) -> list[Transition]:
    plan = discovery.plan
    url_to_sid = {s.url: s.screen_id for s in screens}
    out: list[Transition] = []

    for transition in plan.transitions:
        src = url_to_sid.get(transition.from_url)
        dst = url_to_sid.get(transition.to_url)
        if src and dst:
            out.append(
                Transition(from_screen=src, to_screen=dst, action=transition.action)
            )

    if not out and len(screens) > 1:
        for left, right in zip(screens, screens[1:]):
            out.append(
                Transition(
                    from_screen=left.screen_id,
                    to_screen=right.screen_id,
                    action="navigate",
                )
            )
    return out


def _screens_from_discovery(discovery: AgentDiscovery) -> list[ScreenInfo]:
    cap = get_settings().crawl_max_screens
    screens = [
        ScreenInfo(
            screen_id=_screen_id(screen.url),
            url=screen.url,
            title=screen.title,
            label=screen.label,
            purpose=screen.purpose,
            authenticated=screen.authenticated,
            primary_actions=screen.primary_actions,
            structured_dom=[{"url": screen.url, "title": screen.title}],
        )
        for screen in discovery.plan.screens[:cap]
    ]
    attach_screenshots(screens, discovery)
    return screens


def _route_only_screens(req: CrawlRequest) -> list[ScreenInfo]:
    routes: list[RouteSpec] = list(req.routes)
    if not routes:
        routes = [RouteSpec(path="/")]
    return [
        ScreenInfo(
            screen_id=_screen_id(_resolve_url(req.base_url, route.path)),
            url=_resolve_url(req.base_url, route.path),
            authenticated=route.authenticated,
            structured_dom=[{"url": _resolve_url(req.base_url, route.path)}],
        )
        for route in routes[: get_settings().crawl_max_screens]
    ]


async def _finalize_screens(
    screens: list[ScreenInfo],
    progress: ProgressCb | None,
    on_screen: ScreenCb | None,
) -> None:
    total = len(screens) or 1
    for index, screen in enumerate(screens, start=1):
        await _persist_screen_shot(screen)
        await _label_screen(screen)
        if on_screen:
            await on_screen(screen)
        if progress:
            await progress(0.2 + 0.7 * (index / total), f"Processed {screen.url}")


async def crawl_app(
    req: CrawlRequest,
    progress: ProgressCb | None = None,
    on_screen: ScreenCb | None = None,
) -> CrawlResult:
    settings = get_settings()
    run_id = uuid.uuid4().hex[:12]
    mode = (req.crawl_mode or "hybrid").lower()
    discovery: AgentDiscovery | None = None

    if mode in {"hybrid", "agent"}:
        if progress:
            await progress(0.05, "Agent exploring application")
        discovery = await discover_screens(req)

    if discovery and discovery.plan.screens:
        if progress:
            await progress(0.18, "Attaching cloud screenshots")
        screens = _screens_from_discovery(discovery)
        await _finalize_screens(screens, progress, on_screen)
        capture_note = ""
        if screens and not any(s.screenshot_url for s in screens):
            capture_note = (
                "Screens were discovered but browser-use did not return screenshot URLs "
                "for this session. Re-run the crawl or check your browser-use API quota."
            )
        return CrawlResult(
            run_id=run_id,
            base_url=req.base_url,
            screen_count=len(screens),
            screens=screens,
            transitions=_transitions(discovery, screens),
            capture_note=capture_note,
        )

    if progress:
        await progress(0.2, "Building route list")
    screens = _route_only_screens(req)
    await _finalize_screens(screens, progress, on_screen)
    return CrawlResult(
        run_id=run_id,
        base_url=req.base_url,
        screen_count=len(screens),
        screens=screens,
        transitions=[],
        capture_note=(
            "No browser-use discovery results — only explicit routes were recorded. "
            "Set BROWSER_USE_API_KEY to enable autonomous crawl with screenshots."
            if not settings.browser_use_api_key
            else "browser-use returned no screens for this application."
        ),
    )
