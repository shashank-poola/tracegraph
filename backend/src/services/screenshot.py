"""Encode screenshots as data: URIs for frontend persistence."""

from __future__ import annotations

import base64

import httpx


def to_data_uri(data: bytes, content_type: str = "image/png") -> str:
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{content_type};base64,{b64}"


async def download_presigned_screenshot(url: str | None) -> str:
    """Download a browser-use presigned screenshot URL into a data: URI.

    Presigned URLs expire in ~5 minutes. Returns an empty string on failure.
    """
    if not url:
        return ""
    if url.startswith("data:"):
        return url

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return ""
        content_type = resp.headers.get("content-type", "image/png").split(";")[0]
        return to_data_uri(resp.content, content_type)
    except Exception:  # noqa: BLE001
        return ""
