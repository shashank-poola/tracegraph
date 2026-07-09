"""Hybrid crawl: browser-use agent discovers screens, Playwright captures artifacts."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

from src.config import get_settings
from src.core.llm import complete
from src.models.schemas import (
    CrawlRequest,
    CrawlResult,
    InteractiveElement,
    RouteSpec,
    ScreenInfo,
    Transition,
)
from src.services.browser_agent import AgentCrawlPlan, AgentScreen, discover_screens
from src.services.screenshot import store_screenshot

logger = logging.getLogger("crawler")
ProgressCb = Callable[[float, str], Awaitable[None]]

_LABEL_SYSTEM = (
    "Summarize this screen for a QA lead. Return ONLY JSON: "
    '{"label":"...","purpose":"...","primary_actions":["..."],"key_components":["..."]}'
)


def _resolve_url(base: str, path: str) -> str:
    return path if path.startswith("http") else urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def _screen_id(url: str) -> str:
    return urlparse(url).path or "/"


def _parse_elements(html: str) -> list[InteractiveElement]:
    out: list[InteractiveElement] = []
    for tag, kind in (("button", "button"), ("a", "link"), ("input", "input")):
        if f"<{tag}" in html:
            out.append(InteractiveElement(kind=kind, role=kind))
    return out[:50]


async def _label_screen(screen: ScreenInfo, structured: list) -> None:
    s = get_settings()
    if not s.crawl_llm_labeling or screen.label:
        return
    if not (s.zai_api_key or s.groq_api_key or s.gemini_api_key):
        return
    try:
        from src.core.json_util import extract_json

        raw = await complete(
            [
                {"role": "system", "content": _LABEL_SYSTEM},
                {"role": "user", "content": f"URL: {screen.url}\nTitle: {screen.title}\nDOM: {json.dumps(structured)[:6000]}"},
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


def _targets_from_request(req: CrawlRequest, plan: AgentCrawlPlan | None) -> list[tuple[str, bool, AgentScreen | None]]:
    """(url, authenticated, agent_metadata) list to capture."""
    seen: set[str] = set()
    targets: list[tuple[str, bool, AgentScreen | None]] = []

    def add(url: str, auth: bool = False, meta: AgentScreen | None = None) -> None:
        if url and url not in seen:
            seen.add(url)
            targets.append((url, auth, meta))

    if plan:
        for s in plan.screens:
            add(s.url, s.authenticated, s)

    for route in req.routes:
        add(_resolve_url(req.base_url, route.path), route.authenticated)

    if not targets:
        add(req.base_url.rstrip("/") + "/" if not req.base_url.endswith("/") else req.base_url)

    cap = get_settings().crawl_max_screens
    return targets[:cap]


async def _playwright_capture(
    req: CrawlRequest,
    targets: list[tuple[str, bool, AgentScreen | None]],
    artifact_dir: Path,
    progress: ProgressCb | None,
) -> list[ScreenInfo]:
    settings = get_settings()
    screens: list[ScreenInfo] = []
    total = len(targets)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=settings.crawl_headless)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(settings.crawl_nav_timeout_ms)

        if req.login:
            lg = req.login
            await page.goto(lg.login_url)
            await page.fill(lg.username_selector, lg.username)
            await page.fill(lg.password_selector, lg.password)
            await page.click(lg.submit_selector)
            await page.wait_for_load_state("networkidle")

        for i, (url, auth, meta) in enumerate(targets):
            if progress:
                await progress(0.2 + 0.7 * (i / max(total, 1)), f"Capturing {url}")
            sid = _screen_id(url)
            try:
                await page.goto(url)
                await page.wait_for_load_state("domcontentloaded")
            except Exception as exc:  # noqa: BLE001
                logger.warning("goto failed %s: %s", url, exc)
                continue

            html = (await page.content())[: settings.crawl_max_dom_bytes]
            shot = await page.screenshot(full_page=True)
            safe = sid.replace("/", "_") or "root"
            shot_path = artifact_dir / f"{safe}.png"
            shot_path.write_bytes(shot)
            a11y = await page.accessibility.snapshot() or {}
            a11y_path = artifact_dir / f"{safe}.a11y.json"
            a11y_path.write_text(json.dumps(a11y), encoding="utf-8")
            dom_path = artifact_dir / f"{safe}.html"
            dom_path.write_text(html, encoding="utf-8")

            structured = [{"tag": "document", "url": url, "title": await page.title()}]
            screen = ScreenInfo(
                screen_id=sid,
                url=url,
                title=meta.title if meta and meta.title else await page.title(),
                authenticated=meta.authenticated if meta else auth,
                interactive_count=len(_parse_elements(html)),
                dom_path=str(dom_path),
                screenshot_path=str(shot_path),
                a11y_path=str(a11y_path),
                screenshot_url=await store_screenshot(str(shot_path), shot),
                dom=html,
                a11y=json.dumps(a11y),
                elements=_parse_elements(html),
                structured_dom=structured,
                label=meta.label if meta else "",
                purpose=meta.purpose if meta else "",
                primary_actions=meta.primary_actions if meta else [],
            )
            await _label_screen(screen, structured)
            screens.append(screen)

        await browser.close()
    return screens


def _transitions(
    req: CrawlRequest,
    plan: AgentCrawlPlan | None,
    screens: list[ScreenInfo],
) -> list[Transition]:
    url_to_sid = {s.url: s.screen_id for s in screens}
    out: list[Transition] = []

    if plan:
        for t in plan.transitions:
            src = url_to_sid.get(t.from_url)
            dst = url_to_sid.get(t.to_url)
            if src and dst:
                out.append(Transition(from_screen=src, to_screen=dst, action=t.action))

    # Fallback: sequential route order
    if not out and len(screens) > 1:
        for a, b in zip(screens, screens[1:]):
            out.append(Transition(from_screen=a.screen_id, to_screen=b.screen_id, action="navigate"))
    return out


async def _agent_only_result(req: CrawlRequest, plan: AgentCrawlPlan, run_id: str) -> CrawlResult:
    """When Playwright pass skipped — map agent output directly to ScreenInfo."""
    screens = [
        ScreenInfo(
            screen_id=_screen_id(s.url),
            url=s.url,
            title=s.title,
            label=s.label,
            purpose=s.purpose,
            authenticated=s.authenticated,
            primary_actions=s.primary_actions,
            structured_dom=[{"url": s.url, "title": s.title}],
        )
        for s in plan.screens[: get_settings().crawl_max_screens]
    ]
    transitions = _transitions(req, plan, screens)
    return CrawlResult(
        run_id=run_id,
        base_url=req.base_url,
        screen_count=len(screens),
        screens=screens,
        transitions=transitions,
    )


async def crawl_app(req: CrawlRequest, progress: ProgressCb | None = None) -> CrawlResult:
    settings = get_settings()
    run_id = uuid.uuid4().hex[:12]
    artifact_dir = Path(settings.crawl_artifact_dir) / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    mode = (req.crawl_mode or "hybrid").lower()
    plan: AgentCrawlPlan | None = None

    if mode in {"hybrid", "agent"}:
        if progress:
            await progress(0.05, "Agent exploring application")
        plan = await discover_screens(req)

    if mode == "agent" and plan:
        if progress:
            await progress(1.0, "Agent crawl complete")
        result = await _agent_only_result(req, plan, run_id)
        result.artifact_dir = str(artifact_dir)
        return result

    targets = _targets_from_request(req, plan)
    if progress:
        await progress(0.15, f"Playwright capturing {len(targets)} screens")
    screens = await _playwright_capture(req, targets, artifact_dir, progress)

    return CrawlResult(
        run_id=run_id,
        base_url=req.base_url,
        artifact_dir=str(artifact_dir),
        screen_count=len(screens),
        screens=screens,
        transitions=_transitions(req, plan, screens),
    )
