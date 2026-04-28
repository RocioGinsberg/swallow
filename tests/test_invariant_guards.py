from __future__ import annotations

import ast
from pathlib import Path

from swallow.router import route_by_name
from swallow.synthesis import _MPS_DEFAULT_HTTP_ROUTE, _route_is_path_a


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
            "save_mps_policy",
        },
        allowed_files={
            "src/swallow/governance.py",
            "src/swallow/store.py",
            "src/swallow/knowledge_store.py",
            "src/swallow/router.py",
            "src/swallow/consistency_audit.py",
            "src/swallow/mps_policy_store.py",
        },
    )

    assert violations == []


def test_mps_policy_writes_via_apply_proposal() -> None:
    violations = _find_protected_writer_uses(
        protected_names={"save_mps_policy"},
        allowed_files={
            "src/swallow/governance.py",
            "src/swallow/mps_policy_store.py",
        },
    )

    assert violations == []
    source = (SRC_ROOT / "mps_policy_store.py").read_text(encoding="utf-8")
    assert "mps_policy_path" in source
    assert '".swl"' not in source


def test_mps_no_chat_message_passing() -> None:
    tree = ast.parse((SRC_ROOT / "synthesis.py").read_text(encoding="utf-8"))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "messages":
            violations.append(f"keyword messages at line {node.lineno}")
        if isinstance(node, ast.Name) and node.id == "messages":
            violations.append(f"name messages at line {node.lineno}")

    assert violations == []


def test_synthesis_uses_provider_router() -> None:
    tree = ast.parse((SRC_ROOT / "synthesis.py").read_text(encoding="utf-8"))
    imported_names: set[str] = set()
    direct_route_spec_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "router":
            imported_names.update(alias.name for alias in node.names)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "RouteSpec":
                direct_route_spec_calls.append(f"RouteSpec at line {node.lineno}")

    assert {"route_by_name", "select_route"}.issubset(imported_names)
    assert direct_route_spec_calls == []


def test_mps_default_route_is_path_a() -> None:
    route = route_by_name(_MPS_DEFAULT_HTTP_ROUTE)

    assert route is not None
    assert _route_is_path_a(route)


def test_synthesis_clones_state_per_call() -> None:
    source = (SRC_ROOT / "synthesis.py").read_text(encoding="utf-8")

    assert "_participant_state_for_call" in source
    assert "replace(" in source
    assert "run_http_executor(transient_state" in source
    assert "run_http_executor(arbiter_state" in source


def test_synthesis_module_does_not_call_submit_staged_candidate() -> None:
    tree = ast.parse((SRC_ROOT / "synthesis.py").read_text(encoding="utf-8"))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "submit_staged_candidate":
                    violations.append(f"imports submit_staged_candidate at line {node.lineno}")
        if isinstance(node, ast.Call):
            func = node.func
            called_name = ""
            if isinstance(func, ast.Name):
                called_name = func.id
            elif isinstance(func, ast.Attribute):
                called_name = func.attr
            if called_name == "submit_staged_candidate":
                violations.append(f"calls submit_staged_candidate at line {node.lineno}")

    assert violations == []
