from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.helpers.cli_runner import CliRun
from tests.helpers.workspace import read_json_lines, task_artifacts_root


def assert_cli_success(result: CliRun, *, stderr: str = "") -> None:
    result.assert_success()
    assert result.stderr == stderr


def assert_file_exists(path: Path) -> Path:
    assert path.exists(), f"Expected file to exist: {path}"
    return path


def assert_artifact_exists(base_dir: Path, task_id: str, relative_path: str | Path) -> Path:
    return assert_file_exists(task_artifacts_root(base_dir, task_id) / relative_path)


def assert_jsonl_event_kind(path: Path, event_kind: str) -> dict[str, Any]:
    for event in read_json_lines(path):
        if event.get("event_type") == event_kind or event.get("kind") == event_kind:
            return event
    raise AssertionError(f"Expected event kind {event_kind!r} in {path}")
