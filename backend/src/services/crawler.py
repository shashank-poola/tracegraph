"""Crawler (UI layer) — powered by the browser-use cloud SDK.

For each route the user supplies, browser-use navigates to the page (logging in
first when the route is authenticated), captures a screenshot, and returns a
structured summary. Streamlit-style SPAs that share one URL but expose sidebar
navigation are expanded into one capture per sidebar view.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import uuid
from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import urldefrag, urljoin, urlparse

from pydantic import BaseModel

from src.config import get_settings
from src.models.schemas import (
    CrawlRequest,
    CrawlResult,
    InteractiveElement,
    RouteSpec,
    ScreenInfo,
    Transition,
)
from src.services.screenshot import download_presigned_screenshot

logger = logging.getLogger("crawler")

ProgressCb = Callable[[float, str], Awaitable[None]]
ScreenCb = Callable[[ScreenInfo], Awaitable[None]]

_NAV_SPLIT = re.compile(r",|\band\b", re.IGNORECASE)


class _BULink(BaseModel):
    text: str = ""
    href: str = ""


class _BUScreen(BaseModel):
    title: str = ""
    label: str = ""
    purpose: str = ""
    primary_actions: list[str] = []
    key_components: list[str] = []
    links: list[_BULink] = []


def _norm_url(url: str) -> str:
    clean, _frag = urldefrag(url)
    if clean.endswith("/") and len(urlparse(clean).path) > 1:
        clean = clean[:-1]
    return clean


def _screen_id(url: str, elements: list[InteractiveElement]) -> str:
    sig = "|".join(sorted(f"{e.kind}:{e.text}" for e in elements))
    raw = f"{_norm_url(url)}::{sig}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _view_screen_id(url: str, view_label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", view_label.lower()).strip("-") or "view"
    raw = f"{_norm_url(url)}::sidebar::{slug}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _login_prefix(route: RouteSpec, req: CrawlRequest) -> str:
    if not route.authenticated or req.login is None:
        return ""
    return (
        f"First log in at {req.login.login_url} using username "
        f"'{req.login.username}' and password '{req.login.password}'. Then "
    )


def _task_prompt(url: str, route: RouteSpec, req: CrawlRequest) -> str:
    return (
        f"{_login_prefix(route, req)}go to {url} and analyze ONLY that page "
        "(do not click into other pages). Return the page title, a 3-6 word label, "
        "a one-sentence purpose, the primary user actions, the key UI components, "
        "and every navigation link visible on the page with its visible text and href. "
        "If sidebar or tab navigation exposes other views at the same URL, list each "
        "view name in primary_actions as 'Navigate: <view name>'."
    )


def _sidebar_view_prompt(url: str, view_label: str, route: RouteSpec, req: CrawlRequest) -> str:
    return (
        f"{_login_prefix(route, req)}go to {url}, open the sidebar navigation, select "
        f"'{view_label}', and analyze ONLY that view (do not explore other views). "
        "Return the page title, a 3-6 word label, a one-sentence purpose, the primary "
        "user actions, the key UI components, and every navigation link on this view."
    )


def _extract_sidebar_views(screen: ScreenInfo) -> list[str]:
    """Parse sidebar view names from browser-use metadata (Streamlit SPAs)."""
    found: list[str] = []
    seen: set[str] = set()

    def add(label: str) -> None:
        label = label.strip(" .")
        if not label or len(label) > 60:
            return
        key = label.lower()
        if key in seen:
            return
        seen.add(key)
        found.append(label)

    for text in screen.primary_actions + screen.key_components:
        lower = text.lower()
        if "navigate" not in lower and "sidebar" not in lower:
            continue
        match = re.search(r"between\s+(.+?)\s+via", text, re.IGNORECASE)
        chunk = match.group(1) if match else text
        chunk = re.sub(r"^navigate:?\s*", "", chunk, flags=re.IGNORECASE)
        chunk = re.sub(r"\s+via\s+.*$", "", chunk, flags=re.IGNORECASE)
        for part in _NAV_SPLIT.split(chunk):
            part = re.sub(r"^(the\s+)?", "", part.strip(), flags=re.IGNORECASE)
            add(part)

    current = (screen.label or "").lower()
    return [label for label in found if label.lower() not in current or len(found) == 1]


class Crawler:
    def __init__(
        self,
        req: CrawlRequest,
        run_dir: Path,
        on_screen: ScreenCb | None = None,
    ):
        self.req = req
        self.run_dir = run_dir
        self.on_screen = on_screen
        self.settings = get_settings()
        self.screens: dict[str, ScreenInfo] = {}
        self.screen_order: list[str] = []
        self.transitions: list[Transition] = []
        self.route_errors: list[str] = []

    async def run(self, progress: ProgressCb | None = None) -> CrawlResult:
        from browser_use_sdk.v3 import AsyncBrowserUse

        if not self.settings.browser_use_api_key:
            raise RuntimeError(
                "BROWSER_USE_API_KEY is not set — get a key at "
                "https://cloud.browser-use.com/settings?tab=api-keys"
            )

        if progress:
            await progress(0.05, "Starting browser-use session")

        client = AsyncBrowserUse(api_key=self.settings.browser_use_api_key)
        routes = self.req.routes or [RouteSpec(path="/")]
        sem = asyncio.Semaphore(self.settings.crawl_browseruse_concurrency)
        pending_views: list[tuple[str, str, RouteSpec]] = []
        done = 0
        total_steps = len(routes)

        async def one(route: RouteSpec) -> None:
            nonlocal done
            step = done + 1
            if progress:
                await progress(
                    0.08 + 0.35 * (step - 1) / max(total_steps, 1),
                    f"Capturing route {route.path or '/'} ({step}/{total_steps})",
                )
            async with sem:
                screen = await self._crawl_route(client, route, progress, step, total_steps)
            done += 1
            if screen is not None:
                await self._add_screen(screen)
                for label in _extract_sidebar_views(screen):
                    pending_views.append((screen.url, label, route))

        try:
            await asyncio.gather(*(one(r) for r in routes))

            unique_views: list[tuple[str, str, RouteSpec]] = []
            seen_labels: set[str] = set()
            for url, label, route in pending_views:
                key = label.lower()
                if key in seen_labels:
                    continue
                seen_labels.add(key)
                unique_views.append((url, label, route))

            view_total = len(unique_views)
            for index, (url, label, route) in enumerate(unique_views, start=1):
                if progress:
                    await progress(
                        0.45 + 0.4 * (index - 1) / max(view_total, 1),
                        f"Capturing sidebar view '{label}' ({index}/{view_total})",
                    )
                screen = await self._crawl_sidebar_view(client, url, label, route)
                if screen is not None:
                    await self._add_screen(screen)

            if progress:
                await progress(0.92, "Building screen graph")
        finally:
            await client.close()

        self._build_relationships()
        self._build_sidebar_flow()

        screens = list(self.screens.values())
        capture_note = ""
        if not screens and self.route_errors:
            capture_note = self.route_errors[0]
        elif screens and not any(s.screenshot_url for s in screens):
            capture_note = (
                "Screens were captured but browser-use screenshot images could not be "
                "downloaded. Re-run the crawl or check your browser-use API plan and quota."
            )

        result = CrawlResult(
            run_id=self.run_dir.name,
            base_url=self.req.base_url,
            artifact_dir=str(self.run_dir),
            screen_count=len(screens),
            screens=screens,
            transitions=self.transitions,
            capture_note=capture_note,
        )
        (self.run_dir / "manifest.json").write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )
        logger.info(
            "crawl %s done: %d screens, %d edges",
            self.run_dir.name,
            result.screen_count,
            len(result.transitions),
        )
        return result

    async def _add_screen(self, screen: ScreenInfo) -> None:
        if screen.screen_id in self.screens:
            return
        self.screens[screen.screen_id] = screen
        self.screen_order.append(screen.screen_id)
        if self.on_screen:
            await self.on_screen(screen)

    async def _run_browser_use(self, client, task: str, context: str) -> object | None:
        try:
            return await client.run(
                task,
                output_schema=_BUScreen,
                max_cost_usd=self.settings.crawl_agent_max_cost_usd,
            )
        except Exception as exc:  # noqa: BLE001
            message = str(exc) or type(exc).__name__
            logger.warning("browser-use run failed %s: %s", context, message)
            self.route_errors.append(message)
            return None

    async def _crawl_route(
        self,
        client,
        route: RouteSpec,
        progress: ProgressCb | None,
        step: int,
        total: int,
    ) -> ScreenInfo | None:
        url = urljoin(self.req.base_url, route.path)
        task = _task_prompt(url, route, self.req)
        logger.info("crawl route START %s (auth=%s)", url, route.authenticated)
        if progress:
            await progress(
                0.1 + 0.35 * (step - 1) / max(total, 1),
                f"browser-use visiting {route.path or '/'}…",
            )
        res = await self._run_browser_use(client, task, url)
        if res is None:
            return None
        return await self._screen_from_result(res, url, route, sid_factory=_screen_id)

    async def _crawl_sidebar_view(
        self,
        client,
        url: str,
        view_label: str,
        route: RouteSpec,
    ) -> ScreenInfo | None:
        sid = _view_screen_id(url, view_label)
        if sid in self.screens:
            return None
        task = _sidebar_view_prompt(url, view_label, route, self.req)
        logger.info("crawl sidebar START %s view=%r", url, view_label)
        res = await self._run_browser_use(client, task, f"{url}#{view_label}")
        if res is None:
            return None

        def sid_factory(page_url: str, elements: list[InteractiveElement]) -> str:
            return _view_screen_id(page_url, view_label)

        return await self._screen_from_result(res, url, route, sid_factory=sid_factory)

    async def _screen_from_result(
        self,
        res,
        url: str,
        route: RouteSpec,
        *,
        sid_factory: Callable[[str, list[InteractiveElement]], str],
    ) -> ScreenInfo | None:
        out: _BUScreen = res.output or _BUScreen()
        elements = [
            InteractiveElement(kind="link", text=(link.text or "")[:120], href=link.href)
            for link in out.links
            if link.text or link.href
        ]
        sid = sid_factory(url, elements)
        if sid in self.screens:
            return None

        screenshot_url = await download_presigned_screenshot(
            getattr(res, "screenshot_url", None)
        )
        logger.info(
            "crawl OK %s — label=%r, screenshot=%s",
            url,
            out.label,
            "yes" if screenshot_url else "no",
        )
        return ScreenInfo(
            screen_id=sid,
            url=url,
            title=out.title,
            authenticated=route.authenticated,
            interactive_count=len(elements),
            screenshot_url=screenshot_url,
            elements=elements,
            label=out.label[:80] or out.title[:80],
            purpose=out.purpose,
            primary_actions=[action.strip() for action in out.primary_actions][:8],
            key_components=[component.strip() for component in out.key_components][:10],
            structured_dom=[{"url": url, "title": out.title, "label": out.label}],
        )

    def _build_relationships(self) -> None:
        by_url = {_norm_url(screen.url): screen.screen_id for screen in self.screens.values()}
        seen: set[tuple[str, str]] = set()
        for screen in self.screens.values():
            for element in screen.elements:
                if not element.href:
                    continue
                target = by_url.get(_norm_url(urljoin(screen.url, element.href)))
                if not target or target == screen.screen_id or (screen.screen_id, target) in seen:
                    continue
                seen.add((screen.screen_id, target))
                self.transitions.append(
                    Transition(
                        from_screen=screen.screen_id,
                        to_screen=target,
                        action="link",
                        element_text=element.text,
                        selector=element.selector,
                    )
                )

    def _build_sidebar_flow(self) -> None:
        if self.transitions:
            return
        seen: set[tuple[str, str]] = set()
        for left, right in zip(self.screen_order, self.screen_order[1:]):
            key = (left, right)
            if key in seen:
                continue
            seen.add(key)
            self.transitions.append(
                Transition(
                    from_screen=left,
                    to_screen=right,
                    action="sidebar navigate",
                )
            )


async def crawl_app(
    req: CrawlRequest,
    progress: ProgressCb | None = None,
    on_screen: ScreenCb | None = None,
) -> CrawlResult:
    settings = get_settings()
    run_id = uuid.uuid4().hex[:12]
    run_dir = Path(settings.crawl_artifact_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if not settings.browser_use_api_key:
        routes = req.routes or [RouteSpec(path="/")]
        screens = [
            ScreenInfo(
                screen_id=_norm_url(urljoin(req.base_url, route.path)),
                url=urljoin(req.base_url, route.path),
                authenticated=route.authenticated,
                structured_dom=[{"url": urljoin(req.base_url, route.path)}],
            )
            for route in routes[: settings.crawl_max_screens]
        ]
        return CrawlResult(
            run_id=run_id,
            base_url=req.base_url,
            artifact_dir=str(run_dir),
            screen_count=len(screens),
            screens=screens,
            transitions=[],
            capture_note=(
                "Set BROWSER_USE_API_KEY to enable browser-use crawl with screenshots."
            ),
        )

    logger.info(
        "crawl %s START base=%s routes=%d (browser-use)",
        run_id,
        req.base_url,
        len(req.routes or [RouteSpec(path="/")]),
    )
    return await Crawler(req, run_dir, on_screen).run(progress)
