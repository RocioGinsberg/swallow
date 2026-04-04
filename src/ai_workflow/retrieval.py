from __future__ import annotations

import re
from pathlib import Path

from .models import RetrievalItem


TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".sh",
}


def retrieve_context(workspace_root: Path, query: str, limit: int = 8) -> list[RetrievalItem]:
    tokens = [token for token in re.split(r"[^a-zA-Z0-9]+", query.lower()) if len(token) > 2]
    items: list[RetrievalItem] = []

    for path in sorted(workspace_root.rglob("*")):
        if not path.is_file():
            continue
        if ".swl" in path.parts or ".git" in path.parts:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        haystack = f"{path.name}\n{text[:4000]}".lower()
        score = sum(haystack.count(token) for token in tokens)
        if score <= 0:
            continue

        source_type = "notes" if path.suffix.lower() == ".md" else "repo"
        preview = " ".join(text.split())[:220]
        items.append(
            RetrievalItem(
                path=str(path.relative_to(workspace_root)),
                source_type=source_type,
                score=score,
                preview=preview,
            )
        )

    items.sort(key=lambda item: (-item.score, item.path))
    return items[:limit]
