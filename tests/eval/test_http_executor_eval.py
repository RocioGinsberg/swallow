from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


pytestmark = pytest.mark.eval


def test_http_executor_eval_skeleton_collects() -> None:
    pytest.skip("Phase 46 S1 only adds the HTTP executor eval skeleton; scenarios land in later slices.")
