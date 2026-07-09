"""LLM client: GLM → Groq GPT-OSS → Gemini fallback."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


async def complete(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    json_mode: bool = False,
) -> str:
    """Try each configured provider in order; raise on total failure."""
    cfg = get_settings()
    errors: list[str] = []

    openai_providers = [
        ("glm", cfg.zai_api_key, f"{cfg.zai_base_url.rstrip('/')}/chat/completions", cfg.zai_model),
        ("groq", cfg.groq_api_key, "https://api.groq.com/openai/v1/chat/completions", cfg.groq_model),
    ]
    for name, key, url, model in openai_providers:
        if not key:
            continue
        try:
            body: dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature}
            if json_mode:
                body["response_format"] = {"type": "json_object"}
            async with httpx.AsyncClient(timeout=cfg.llm_timeout_seconds) as client:
                resp = await client.post(url, headers={"Authorization": f"Bearer {key}"}, json=body)
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"]
            if text and text.strip():
                return text
        except Exception as exc:  # noqa: BLE001
            logger.warning("llm %s failed: %s", name, exc)
            errors.append(f"{name}: {exc}")

    if cfg.gemini_api_key:
        try:
            return await _gemini(messages, temperature, json_mode)
        except Exception as exc:  # noqa: BLE001
            logger.warning("llm gemini failed: %s", exc)
            errors.append(f"gemini: {exc}")

    raise RuntimeError("; ".join(errors) if errors else "no LLM provider configured")


async def complete_json(messages: list[dict[str, str]], **kwargs: Any) -> Any:
    raw = await complete(messages, json_mode=True, **kwargs)
    text = raw.strip()
    if m := _JSON_FENCE.search(text):
        text = m.group(1).strip()
    elif not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start != -1:
            text = text[start : end + 1]
    return json.loads(text)


async def _gemini(messages: list[dict[str, str]], temperature: float, json_mode: bool) -> str:
    cfg = get_settings()
    system: list[str] = []
    contents: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("role") == "system":
            system.append(msg.get("content", ""))
        else:
            role = "model" if msg.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

    body: dict[str, Any] = {
        "contents": contents,
        "generationConfig": {"temperature": temperature},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": "\n\n".join(system)}]}
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{cfg.gemini_model}:generateContent"
    async with httpx.AsyncClient(timeout=cfg.llm_timeout_seconds) as client:
        resp = await client.post(url, params={"key": cfg.gemini_api_key}, json=body)
        resp.raise_for_status()
        parts = resp.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts)
