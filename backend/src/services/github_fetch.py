"""Download repo tarballs and doc files from GitHub."""

from __future__ import annotations

import io
import tarfile

import httpx

from src.config import get_settings

GH_API = "https://api.github.com"
_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "tracegraph",
}


class FetchResult:
    def __init__(self, sources: dict[str, str], total_file_count: int):
        self.sources = sources
        self.total_file_count = total_file_count


def _strip_root(name: str) -> str:
    parts = name.split("/", 1)
    return parts[1] if len(parts) == 2 else name


async def _download_tarball(token: str, full_name: str, ref: str) -> bytes:
    ref_path = f"/{ref}" if ref else ""
    url = f"{GH_API}/repos/{full_name}/tarball{ref_path}"
    headers = {**_HEADERS, "Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"tarball fetch failed ({resp.status_code}) for {full_name}")
        return resp.content


async def download_tarball(token: str, full_name: str, ref: str) -> FetchResult:
    settings = get_settings()
    data = await _download_tarball(token, full_name, ref)
    sources: dict[str, str] = {}
    total = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            total += 1
            rel = _strip_root(member.name)
            if not rel.endswith(".py") or member.size > settings.max_file_bytes:
                continue
            if len(sources) >= settings.max_python_files:
                continue
            fh = tar.extractfile(member)
            if fh:
                sources[rel] = fh.read().decode("utf-8", errors="replace")
                fh.close()
    return FetchResult(sources=sources, total_file_count=total)


async def download_doc_files(
    token: str,
    full_name: str,
    ref: str,
    exts: tuple[str, ...] = (".md", ".vdk"),
) -> dict[str, str]:
    settings = get_settings()
    data = await _download_tarball(token, full_name, ref)
    docs: dict[str, str] = {}
    lower = tuple(e.lower() for e in exts)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            rel = _strip_root(member.name)
            if not rel.lower().endswith(lower) or member.size > settings.max_file_bytes:
                continue
            fh = tar.extractfile(member)
            if fh:
                docs[rel] = fh.read().decode("utf-8", errors="replace")
                fh.close()
    return docs
