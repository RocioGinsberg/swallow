from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "swallow"


def _src_py_files() -> list[Path]:
    return sorted(path for path in SRC_ROOT.rglob("*.py") if path.is_file())


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _find_protected_writer_uses(*, protected_names: set[str], allowed_files: set[str]) -> list[str]:
    """Scan production code for direct protected writer imports/calls.

    Phase 61 guards canonical knowledge / route metadata / policy main writes.
    Tests are not scanned because fixture setup may call low-level store helpers
    directly. The bottom-layer definition files are whitelisted; all other
    production callers must go through `swallow.governance.apply_proposal`.
    """

    violations: list[str] = []
    for path in _src_py_files():
        rel_path = _relative(path)
        if rel_path in allowed_files:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in protected_names:
                        violations.append(f"{rel_path}:{node.lineno} imports {alias.name}")
            elif isinstance(node, ast.Call):
                func = node.func
                called_name = ""
                if isinstance(func, ast.Name):
                    called_name = func.id
                elif isinstance(func, ast.Attribute):
                    called_name = func.attr
                if called_name in protected_names:
                    violations.append(f"{rel_path}:{node.lineno} calls {called_name}")
    return violations


def test_canonical_write_only_via_apply_proposal() -> None:
    violations = _find_protected_writer_uses(
        protected_names={"append_canonical_record", "persist_wiki_entry_from_record"},
        allowed_files={
            "src/swallow/governance.py",
            "src/swallow/store.py",
            "src/swallow/knowledge_store.py",
        },
    )

    assert violations == []


def test_route_metadata_writes_only_via_apply_proposal() -> None:
    violations = _find_protected_writer_uses(
        protected_names={"save_route_weights", "save_route_capability_profiles"},
        allowed_files={
            "src/swallow/governance.py",
            "src/swallow/router.py",
        },
    )

    assert violations == []


def test_only_apply_proposal_calls_private_writers() -> None:
    """Aggregate Phase 61 guard for canonical / route / policy main writer calls.

    DATA_MODEL §4.1 describes future Repository-private methods. Until that
    abstraction exists, this test guards the current physical writer functions
    selected by Phase 61 design_decision §E / §F.
    """

    violations = _find_protected_writer_uses(
        protected_names={
            "append_canonical_record",
            "persist_wiki_entry_from_record",
            "save_route_weights",
            "save_route_capability_profiles",
            "save_audit_trigger_policy",
        },
        allowed_files={
            "src/swallow/governance.py",
            "src/swallow/store.py",
            "src/swallow/knowledge_store.py",
            "src/swallow/router.py",
            "src/swallow/consistency_audit.py",
        },
    )

    assert violations == []
