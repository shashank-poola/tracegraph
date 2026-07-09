"""LLM descriptions per file — one JSON call per file, bounded concurrency."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from pydantic import BaseModel, Field, ValidationError

from src.config import get_settings
from src.core.json_util import extract_json
from src.core.llm import complete
from src.models.schemas import FileInfo, RepoTree

logger = logging.getLogger("describer")
ProgressCb = Callable[[float, str], Awaitable[None]]

_SYSTEM = (
    "You document a Python codebase. Return ONLY JSON:\n"
    '{"file_description":"...","symbols":[{"name":"...","description":"..."}]}\n'
    "Use exact symbol names provided. 1-2 sentences each."
)


class SymbolDescription(BaseModel):
    name: str
    description: str = ""


class FileDescription(BaseModel):
    file_description: str
    symbols: list[SymbolDescription] = Field(default_factory=list)


def _file_prompt(file: FileInfo, source: str) -> str:
    symbols = [f"- function {f.name}({', '.join(f.args)})" for f in file.functions]
    for c in file.classes:
        symbols.append(f"- class {c.name}")
        symbols += [f"- method {c.name}.{m.name}" for m in c.methods]
    return (
        f"File: {file.path}\nSymbols:\n" + ("\n".join(symbols) or "(none)") + f"\n\n```python\n{source[:8000]}\n```"
    )


def _apply(file: FileInfo, result: FileDescription) -> None:
    file.description = result.file_description
    by_name = {s.name: s.description for s in result.symbols}
    for fn in file.functions:
        fn.description = by_name.get(fn.name, fn.description)
    for cls in file.classes:
        cls.description = by_name.get(cls.name, cls.description)
        for m in cls.methods:
            m.description = by_name.get(f"{cls.name}.{m.name}") or by_name.get(m.name, m.description)


async def _describe_one(file: FileInfo, source: str, sem: asyncio.Semaphore) -> None:
    async with sem:
        try:
            raw = await complete(
                [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": _file_prompt(file, source)}],
                json_mode=True,
            )
            _apply(file, FileDescription.model_validate(extract_json(raw)))
        except (ValidationError, Exception) as exc:  # noqa: BLE001
            logger.warning("describe failed %s: %s", file.path, exc)
            file.description = file.description or f"(description unavailable)"


async def describe_tree(
    tree: RepoTree,
    sources: dict[str, str],
    progress: ProgressCb | None = None,
) -> RepoTree:
    settings = get_settings()
    if not (settings.zai_api_key or settings.groq_api_key or settings.gemini_api_key):
        tree.summary = "LLM descriptions skipped (no API key)."
        return tree

    sem = asyncio.Semaphore(settings.llm_concurrency)
    total = len(tree.files) or 1
    done = 0

    async def run(file: FileInfo) -> None:
        nonlocal done
        await _describe_one(file, sources.get(file.path, ""), sem)
        done += 1
        if progress:
            await progress(0.4 + 0.55 * (done / total), f"Described {file.path}")

    await asyncio.gather(*(run(f) for f in tree.files))
    if not tree.summary:
        n_fn = sum(len(f.functions) for f in tree.files)
        n_cls = sum(len(f.classes) for f in tree.files)
        tree.summary = f"{tree.python_file_count} Python files, {n_cls} classes, {n_fn} functions."
    return tree
