"""Tolerant JSON extraction from LLM responses."""

from __future__ import annotations

import json
import re

_FENCE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


def extract_json(content: str) -> dict:
    text = content.strip()
    if m := _FENCE.search(text):
        text = m.group(1).strip()
    elif not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start != -1:
            text = text[start : end + 1]
    return json.loads(text)
