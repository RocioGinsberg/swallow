from __future__ import annotations

from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "swallow"
COMMAND_MODULES = (
    "application/commands/proposals.py",
    "application/commands/meta_optimizer.py",
)


def _source(relative_path: str) -> str:
    return (SRC_ROOT / relative_path).read_text(encoding="utf-8")


def test_application_command_modules_do_not_format_terminal_output() -> None:
    forbidden_tokens = (
        "import argparse",
        "from argparse",
        "import click",
        "from click",
        "import rich",
        "from rich",
        "\\033[",
        "\\x1b[",
        "print(",
        "sys.stdout",
        "sys.stderr",
    )
    for relative_path in COMMAND_MODULES:
        source = _source(relative_path)
        violations = [token for token in forbidden_tokens if token in source]
        assert violations == [], f"{relative_path} must not own terminal formatting: {violations}"


def test_proposal_commands_use_governance_boundary_not_route_store_writers() -> None:
    source = _source("application/commands/proposals.py")

    assert "register_route_metadata_proposal(" in source
    assert "apply_proposal(" in source

    forbidden_tokens = (
        "route_metadata_store",
        "save_route_registry",
        "save_route_policy",
        "save_route_weights",
        "save_route_capability_profiles",
        "_apply_metadata_change",
    )
    violations = [token for token in forbidden_tokens if token in source]
    assert violations == []
