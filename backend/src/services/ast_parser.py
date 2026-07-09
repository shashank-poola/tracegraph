"""Parse fetched Python sources into a RepoTree."""

from __future__ import annotations

import ast
import warnings

from src.core.tree import extract_imports, extract_symbols
from src.models.schemas import FileInfo, RepoTree


def parse_file(path: str, source: str) -> FileInfo:
    loc = source.count("\n") + 1
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            module = ast.parse(source)
    except SyntaxError as exc:
        return FileInfo(path=path, loc=loc, parsed=False, parse_error=f"{exc.msg} (line {exc.lineno})")

    functions, classes = extract_symbols(module)
    records = extract_imports(module)
    display = [("." * r.level + r.module) if r.module else "." * r.level for r in records]
    return FileInfo(
        path=path,
        loc=loc,
        parsed=True,
        imports=display,
        import_records=records,
        functions=functions,
        classes=classes,
    )


def build_tree(full_name: str, ref: str, sources: dict[str, str], total_file_count: int) -> RepoTree:
    files = [parse_file(p, s) for p, s in sorted(sources.items())]
    return RepoTree(
        full_name=full_name,
        ref=ref,
        file_count=total_file_count,
        python_file_count=len(files),
        files=files,
    )
