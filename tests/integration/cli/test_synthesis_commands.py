from __future__ import annotations

from pathlib import Path

from swallow.surface_tools.mps_policy_store import read_mps_policy
from swallow.surface_tools.paths import mps_policy_path
from tests.helpers.cli_runner import run_cli


def test_synthesis_policy_set_writes_mps_policy(tmp_path: Path) -> None:
    result = run_cli(
        tmp_path,
        "synthesis",
        "policy",
        "set",
        "--kind",
        "mps_round_limit",
        "--value",
        "3",
    )

    result.assert_success()
    assert "mps_round_limit: 3" in result.stdout
    assert read_mps_policy(tmp_path, "mps_round_limit") == 3
    assert not mps_policy_path(tmp_path).exists()
