from __future__ import annotations

import json
from pathlib import Path

import pytest


FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "eval_golden"


def _load_json_fixture(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def eval_fixtures_root() -> Path:
    return FIXTURES_ROOT


@pytest.fixture
def ingestion_eval_cases(eval_fixtures_root: Path) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for fixture_name in ("chatgpt_golden.json", "claude_golden.json", "open_webui_golden.json"):
        case = _load_json_fixture(eval_fixtures_root / fixture_name)
        if isinstance(case, dict):
            cases.append(case)
    return cases
