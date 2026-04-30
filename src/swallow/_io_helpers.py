from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def read_json_strict(path: Path) -> Any:
    """Read JSON; raise FileNotFoundError if missing and JSONDecodeError if malformed."""
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_or_empty(path: Path) -> dict[str, object]:
    """Read a JSON object; return {} if missing and raise JSONDecodeError if malformed."""
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return dict(payload) if isinstance(payload, dict) else {}


def read_json_list_or_empty(path: Path) -> list[object]:
    """Read a JSON list; return [] if missing and raise JSONDecodeError if malformed."""
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload) if isinstance(payload, list) else []


def read_json_lines_or_empty(path: Path) -> list[dict[str, object]]:
    """Read JSONL; return [] if missing, and skip malformed or non-dict lines with a warning."""
    if not path.exists():
        return []
    records: list[dict[str, object]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            logger.warning(
                "skipping malformed jsonl line",
                extra={"jsonl_path": str(path), "line_no": line_no, "error": str(exc)},
            )
            continue
        if not isinstance(payload, dict):
            logger.warning(
                "skipping non-dict jsonl line",
                extra={"jsonl_path": str(path), "line_no": line_no},
            )
            continue
        records.append(payload)
    return records


def read_json_lines_strict_or_empty(path: Path) -> list[dict[str, object]]:
    """Read JSONL; return [] if missing, and raise JSONDecodeError if any line is malformed."""
    if not path.exists():
        return []
    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            records.append(payload)
    return records
