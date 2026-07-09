"""Playwright crawl — route-based, deterministic DOM + screenshot capture."""

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
    p = urlparse(url)
    return p.path or "/"


async def _label_screen(screen: ScreenInfo, structured: list) -> None:
    s = get_settings()
    if not s.crawl_llm_labeling or not (s.zai_api_key or s.groq_api_key or s.gemini_api_key):
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
        screen.label = data.get("label", "")
        screen.purpose = data.get("purpose", "")
        screen.primary_actions = data.get("primary_actions") or []
        screen.key_components = data.get("key_components") or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("screen label failed %s: %s", screen.url, exc)


def _parse_elements(page_html: str) -> list[InteractiveElement]:
    # Lightweight parse — full DOM kept separately; extract key controls only.
    elements: list[InteractiveElement] = []
    for tag, kind in (("button", "button"), ("a", "link"), ("input", "input")):
        if f"<{tag}" in page_html:
            elements.append(InteractiveElement(kind=kind, role=kind))
    return elements[:50]


async def crawl_app(req: CrawlRequest, progress: ProgressCb | None = None) -> CrawlResult:
    settings = get_settings()
    run_id = uuid.uuid4().hex[:12]
    artifact_dir = Path(settings.crawl_artifact_dir) / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    routes: list[RouteSpec] = req.routes or [RouteSpec(path="/")]
    if len(routes) > settings.crawl_max_screens:
        routes = routes[: settings.crawl_max_screens]

    screens: list[ScreenInfo] = []
    url_to_id: dict[str, str] = {}

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

        total = len(routes)
        for i, route in enumerate(routes):
            if progress:
                await progress(0.1 + 0.8 * (i / total), f"Crawling {route.path}")
            url = _resolve_url(req.base_url, route.path)
            sid = _screen_id(url)
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")

            html = await page.content()
            if len(html) > settings.crawl_max_dom_bytes:
                html = html[: settings.crawl_max_dom_bytes]

            shot = await page.screenshot(full_page=True)
            shot_path = artifact_dir / f"{sid.replace('/', '_') or 'root'}.png"
            shot_path.write_bytes(shot)

            a11y = await page.accessibility.snapshot() or {}
            a11y_path = artifact_dir / f"{sid.replace('/', '_') or 'root'}.a11y.json"
            a11y_path.write_text(json.dumps(a11y), encoding="utf-8")

            dom_path = artifact_dir / f"{sid.replace('/', '_') or 'root'}.html"
            dom_path.write_text(html, encoding="utf-8")

            structured = [{"tag": "document", "url": url, "title": await page.title()}]
            screen = ScreenInfo(
                screen_id=sid,
                url=url,
                title=await page.title(),
                authenticated=route.authenticated,
                interactive_count=len(_parse_elements(html)),
                dom_path=str(dom_path),
                screenshot_path=str(shot_path),
                a11y_path=str(a11y_path),
                screenshot_url=await store_screenshot(str(shot_path), shot),
                dom=html,
                a11y=json.dumps(a11y),
                elements=_parse_elements(html),
                structured_dom=structured,
            )
            await _label_screen(screen, structured)
            screens.append(screen)
            url_to_id[url] = sid

        await browser.close()

    transitions: list[Transition] = []
    known = {_resolve_url(req.base_url, r.path) for r in routes}
    for i, a in enumerate(screens):
        for b in screens[i + 1 :]:
            if b.url in known:
                transitions.append(
                    Transition(from_screen=a.screen_id, to_screen=b.screen_id, action="navigate")
                )

    return CrawlResult(
        run_id=run_id,
        base_url=req.base_url,
        artifact_dir=str(artifact_dir),
        screen_count=len(screens),
        screens=screens,
        transitions=transitions,
    )
