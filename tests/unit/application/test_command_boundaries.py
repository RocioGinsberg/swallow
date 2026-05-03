from __future__ import annotations

import re
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "swallow"
COMMAND_MODULES = (
    "application/commands/proposals.py",
    "application/commands/meta_optimizer.py",
    "application/commands/route_metadata.py",
    "application/commands/policies.py",
    "application/commands/synthesis.py",
    "application/commands/knowledge.py",
    "application/commands/tasks.py",
)
MODULE_PRIVATE_WRITER_TOKENS = {
    "application/commands/proposals.py": (
        "route_metadata_store",
        "save_route_registry",
        "save_route_policy",
        "save_route_weights",
        "save_route_capability_profiles",
        "_apply_metadata_change",
    ),
    "application/commands/route_metadata.py": (
        "route_metadata_store",
        "save_route_registry",
        "save_route_policy",
        "save_route_weights",
        "save_route_capability_profiles",
        "_apply_metadata_change",
    ),
    "application/commands/policies.py": (
        "save_audit_trigger_policy",
        "save_mps_policy",
        "_apply_policy_change",
    ),
    "application/commands/synthesis.py": (),
    "application/commands/knowledge.py": (
        "append_canonical_record",
        "persist_wiki_entry_from_record",
        "_promote_canonical",
    ),
    "application/commands/tasks.py": (
        "save_state",
        "_promote_canonical",
        "_apply_metadata_change",
        "_apply_policy_change",
    ),
}
TASK_SQL_WRITE_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|REPLACE)\b", re.IGNORECASE)


def _source(relative_path: str) -> str:
    return (SRC_ROOT / relative_path).read_text(encoding="utf-8")


def _existing_command_modules() -> tuple[str, ...]:
    return COMMAND_MODULES


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
    for relative_path in _existing_command_modules():
        source = _source(relative_path)
        violations = [token for token in forbidden_tokens if token in source]
        assert violations == [], f"{relative_path} must not own terminal formatting: {violations}"


def test_command_modules_do_not_reference_private_writers_unless_explicitly_allowed() -> None:
    for relative_path in _existing_command_modules():
        source = _source(relative_path)
        forbidden_tokens = MODULE_PRIVATE_WRITER_TOKENS.get(relative_path, ())
        violations = [token for token in forbidden_tokens if token in source]
        assert violations == [], f"{relative_path} references private writer tokens: {violations}"


def test_task_command_module_does_not_embed_direct_sql_mutation_when_present() -> None:
    relative_path = "application/commands/tasks.py"
    path = SRC_ROOT / relative_path
    if not path.exists():
        return
    matches = sorted(set(TASK_SQL_WRITE_RE.findall(_source(relative_path))))
    assert matches == [], f"{relative_path} embeds direct SQL mutation strings: {matches}"


def test_proposal_commands_use_governance_boundary() -> None:
    source = _source("application/commands/proposals.py")

    assert "register_route_metadata_proposal(" in source
    assert "apply_proposal(" in source


def test_route_metadata_commands_use_governance_boundary_when_present() -> None:
    relative_path = "application/commands/route_metadata.py"
    if not (SRC_ROOT / relative_path).exists():
        return
    source = _source(relative_path)

    assert "register_route_metadata_proposal(" in source
    assert "apply_proposal(" in source


def test_policy_commands_use_governance_boundary_when_present() -> None:
    relative_path = "application/commands/policies.py"
    if not (SRC_ROOT / relative_path).exists():
        return
    source = _source(relative_path)

    assert "register_policy_proposal(" in source
    assert "register_mps_policy_proposal(" in source
    assert "apply_proposal(" in source


def test_m2_governance_apply_calls_moved_out_of_cli() -> None:
    source = _source("adapters/cli.py")

    assert "register_policy_proposal(" not in source
    assert "register_mps_policy_proposal(" not in source
    assert "register_route_metadata_proposal(" not in source


def test_knowledge_commands_use_governance_boundary_when_present() -> None:
    relative_path = "application/commands/knowledge.py"
    if not (SRC_ROOT / relative_path).exists():
        return
    source = _source(relative_path)

    assert "register_canonical_proposal(" in source
    assert "apply_proposal(" in source
    assert "decide_staged_knowledge(" in source
    assert "apply_relation_suggestions(" in source


def test_m3_knowledge_apply_call_moved_out_of_cli() -> None:
    source = _source("adapters/cli.py")

    assert "register_canonical_proposal(" not in source
    assert "ProposalTarget.CANONICAL_KNOWLEDGE" not in source


def test_task_commands_wrap_orchestrator_when_present() -> None:
    relative_path = "application/commands/tasks.py"
    if not (SRC_ROOT / relative_path).exists():
        return
    source = _source(relative_path)

    for token in (
        "create_task(",
        "run_task(",
        "acknowledge_task(",
        "update_task_planning_handoff(",
        "append_task_knowledge_capture(",
        "decide_task_knowledge(",
        "evaluate_task_canonical_reuse(",
        "run_consistency_audit(",
    ):
        assert token in source


def test_m4_task_write_calls_moved_out_of_cli() -> None:
    source = _source("adapters/cli.py")

    for token in (
        "create_task(",
        "run_task(",
        "acknowledge_task(",
        "update_task_planning_handoff(",
        "append_task_knowledge_capture(",
        "decide_task_knowledge(",
        "evaluate_task_canonical_reuse(",
        "run_consistency_audit(",
    ):
        assert token not in source
