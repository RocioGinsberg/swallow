from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swallow.surface_tools.meta_optimizer import build_meta_optimizer_snapshot


pytestmark = pytest.mark.eval


SCENARIO_EXPECTATIONS = {
    "high_failure_rate": {
        "expected": [
            "Review route `local-codex`: failure rate is 67% over 3 executor events.",
            "Investigate repeated failure fingerprint `launch_error/launch_error` across routes: local-codex.",
        ],
        "forbidden": [
            "No immediate route, fallback, degradation, or cost anomalies crossed the current heuristic thresholds.",
        ],
    },
    "cost_spike": {
        "expected": [
            "Review route `api-claude-review`: average estimated cost is $0.27/task across 4 executor events.",
            "Compare cost for task_family `review`: route `api-claude-review` averages $0.27/task versus `local-summary-review` at $0.00/task.",
            "Watch cost trend on `api-claude-review`: recent estimated cost rose from $0.11 to $0.42 per executor event.",
        ],
        "forbidden": [],
    },
    "healthy_baseline": {
        "expected": [
            "No immediate route, fallback, degradation, or cost anomalies crossed the current heuristic thresholds.",
        ],
        "forbidden": [
            "Review route `local-summary`",
            "Investigate repeated failure fingerprint",
        ],
    },
}


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            records.append(json.loads(stripped))
    return records


def _write_scenario(base_dir: Path, name: str, records: list[dict[str, object]]) -> None:
    task_dir = base_dir / ".swl" / "tasks" / name
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "events.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def test_meta_optimizer_eval_scenarios_cover_expected_proposals(eval_fixtures_root: Path) -> None:
    scenarios_root = eval_fixtures_root / "meta_optimizer_scenarios"
    passed = 0
    total = 0

    for scenario_name, expectation in SCENARIO_EXPECTATIONS.items():
        total += 1
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            records = _load_jsonl(scenarios_root / f"{scenario_name}.jsonl")
            _write_scenario(base_dir, scenario_name, records)
            snapshot = build_meta_optimizer_snapshot(base_dir, last_n=100)
            proposals_blob = "\n".join(proposal.description for proposal in snapshot.proposals)

        scenario_ok = all(item in proposals_blob for item in expectation["expected"])
        scenario_ok = scenario_ok and all(item not in proposals_blob for item in expectation["forbidden"])
        if scenario_ok:
            passed += 1

    assert passed / total >= (2 / 3), f"proposal coverage {passed}/{total} fell below 2/3"
