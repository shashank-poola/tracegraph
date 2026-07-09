"""Encode screenshots as data: URIs for frontend persistence."""

from __future__ import annotations

import base64


async def store_screenshot(path: str, data: bytes, content_type: str = "image/png") -> str:
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{content_type};base64,{b64}"
