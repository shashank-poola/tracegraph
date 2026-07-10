"""Encode screenshots as data: URIs for frontend persistence."""

from __future__ import annotations

import base64

import httpx


async def store_screenshot(path: str, data: bytes, content_type: str = "image/png") -> str:
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{content_type};base64,{b64}"


async def persist_screenshot_url(url: str) -> str:
    """Download a cloud screenshot URL and return a data: URI for SQLite storage."""
    if not url:
        return ""
    if url.startswith("data:"):
        return url

    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(url, headers={"User-Agent": "tracegraph"})
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/png").split(";")[0]
        return await store_screenshot(url, resp.content, content_type)
