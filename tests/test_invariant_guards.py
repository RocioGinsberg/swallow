from __future__ import annotations

import ast
import re
import sqlite3
from pathlib import Path

import pytest

import swallow.router as router
from swallow.identity import local_actor
from swallow.paths import artifacts_dir
from swallow.router import route_by_name
from swallow.sqlite_store import APPEND_ONLY_TABLES, SqliteTaskStore
from swallow.store import write_artifact
from swallow.synthesis import _MPS_DEFAULT_HTTP_ROUTE, _route_is_path_a


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "swallow"
ACTOR_SEMANTIC_KWARGS = frozenset(
    {
        "actor",
        "actor_name",
        "actor_id",
        "submitted_by",
        "performed_by",
        "created_by",
        "updated_by",
        "modified_by",
        "deleted_by",
        "requested_by",
        "approved_by",
        "reviewed_by",
        "applied_by",
        "committed_by",
        "authored_by",
        "signed_by",
        "initiated_by",
        "caller",
        "owner",
        "owner_id",
        "user",
        "user_id",
        "username",
        "principal",
        "principal_id",
        "operator",
        "operator_id",
        "originator",
        "agent",
        "agent_id",
        "executor_name",
    }
)
LOCAL_EXECUTOR_IDENTITY_CALLS = {"ExecutorResult", "RouteSpec"}
EXECUTION_PLANE_FILES = {
    "src/swallow/executor.py",
    "src/swallow/validator.py",
    "src/swallow/validator_agent.py",
    "src/swallow/librarian_executor.py",
    "src/swallow/literature_specialist.py",
    "src/swallow/quality_reviewer.py",
    "src/swallow/consistency_reviewer.py",
    "src/swallow/meta_optimizer.py",
    "src/swallow/ingestion/pipeline.py",
}
TASK_STATE_WRITE_CALLS = {"save_state"}
TASK_SQL_WRITE_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|REPLACE)\s+(?:INTO\s+)?(?:tasks|task_records)\b", re.IGNORECASE)
LOCAL_IDENTITY_CALLS = {
    "gethostname",
    "getfqdn",
    "getuser",
    "getlogin",
    "getnode",
    "expanduser",
    "home",
    "local_actor",
}
ID_TARGET_TOKENS = {
    "id",
    "task_id",
    "event_id",
    "telemetry_id",
    "change_id",
    "route_id",
    "policy_id",
    "proposal_id",
    "canonical_id",
    "staged_id",
    "evidence_id",
    "wiki_id",
}
TRUTH_WRITE_CALLS = {
    "append_event",
    "apply_atomic_text_updates",
    "apply_proposal",
    "save_state",
    "save_validation",
    "submit_staged_candidate",
    "write_artifact",
}
UI_FORBIDDEN_WRITE_CALLS = {
    "append_canonical_record",
    "append_event",
    "append_knowledge_decision",
    "apply_atomic_text_updates",
    "save_state",
    "submit_staged_candidate",
    "write_artifact",
}


def _src_py_files() -> list[Path]:
    return sorted(path for path in SRC_ROOT.rglob("*.py") if path.is_file())


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _call_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _target_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Attribute):
        return [target.attr]
    if isinstance(target, ast.Subscript):
        names = _target_names(target.value)
        key = target.slice
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            names.append(key.value)
        return names
    if isinstance(target, ast.Tuple | ast.List):
        names: list[str] = []
        for item in target.elts:
            names.extend(_target_names(item))
        return names
    return []


def _constant_strings(node: ast.AST) -> list[str]:
    return [item.value for item in ast.walk(node) if isinstance(item, ast.Constant) and isinstance(item.value, str)]


def _is_id_target(name: str) -> bool:
    lowered = name.lower()
    return lowered in ID_TARGET_TOKENS or lowered.endswith("_id") or lowered.endswith("id")


def _is_allowed_local_executor_identity(call: ast.Call, keyword: ast.keyword) -> bool:
    return keyword.arg == "executor_name" and _call_name(call) in LOCAL_EXECUTOR_IDENTITY_CALLS


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
            "src/swallow/truth/knowledge.py",
            "src/swallow/store.py",
            "src/swallow/knowledge_store.py",
        },
    )

    assert violations == []


def test_route_metadata_writes_only_via_apply_proposal() -> None:
    violations = _find_protected_writer_uses(
        protected_names={"save_route_registry", "save_route_weights", "save_route_capability_profiles"},
        allowed_files={
            "src/swallow/truth/route.py",
            "src/swallow/router.py",
        },
    )

    assert violations == []


def test_no_hardcoded_local_actor_outside_identity_module() -> None:
    violations: list[str] = []
    for path in _src_py_files():
        rel_path = _relative(path)
        if rel_path == "src/swallow/identity.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg not in ACTOR_SEMANTIC_KWARGS:
                    continue
                if _is_allowed_local_executor_identity(node, keyword):
                    continue
                if isinstance(keyword.value, ast.Constant) and keyword.value.value == "local":
                    violations.append(f"{rel_path}:{keyword.lineno} {keyword.arg}='local'")

    assert local_actor() == "local"
    assert violations == []


def test_no_absolute_path_in_truth_writes() -> None:
    violations: list[str] = []
    for path in _src_py_files():
        rel_path = _relative(path)
        if rel_path == "src/swallow/workspace.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr in {"resolve", "absolute"}:
                violations.append(f"{rel_path}:{node.lineno} calls Path.{node.func.attr}()")

    assert violations == []


def test_only_apply_proposal_calls_private_writers() -> None:
    """Aggregate Phase 61 guard for canonical / route / policy main writer calls.

    The physical store writers are now reachable only from Repository modules.
    Governance enters those repositories from `apply_proposal`; production code
    outside the Repository layer must not import or call the physical writers.
    """

    violations = _find_protected_writer_uses(
        protected_names={
            "append_canonical_record",
            "persist_wiki_entry_from_record",
            "save_route_registry",
            "save_route_weights",
            "save_route_capability_profiles",
            "save_audit_trigger_policy",
            "save_mps_policy",
        },
        allowed_files={
            "src/swallow/store.py",
            "src/swallow/knowledge_store.py",
            "src/swallow/router.py",
            "src/swallow/consistency_audit.py",
            "src/swallow/mps_policy_store.py",
            "src/swallow/truth/knowledge.py",
            "src/swallow/truth/route.py",
            "src/swallow/truth/policy.py",
        },
    )

    assert violations == []


def test_mps_policy_writes_via_apply_proposal() -> None:
    violations = _find_protected_writer_uses(
        protected_names={"save_mps_policy"},
        allowed_files={
            "src/swallow/mps_policy_store.py",
            "src/swallow/truth/policy.py",
        },
    )

    assert violations == []
    source = (SRC_ROOT / "mps_policy_store.py").read_text(encoding="utf-8")
    assert "mps_policy_path" in source
    assert '".swl"' not in source


def test_only_governance_calls_repository_write_methods() -> None:
    violations = _find_protected_writer_uses(
        protected_names={"_promote_canonical", "_apply_metadata_change", "_apply_policy_change"},
        allowed_files={"src/swallow/governance.py"},
    )

    assert violations == []


def test_no_module_outside_governance_imports_store_writes() -> None:
    protected_imports = {
        "append_canonical_record",
        "persist_wiki_entry_from_record",
        "save_route_weights",
        "save_route_registry",
        "save_route_capability_profiles",
        "save_audit_trigger_policy",
        "save_mps_policy",
    }
    allowed_files = {
        "src/swallow/consistency_audit.py",
        "src/swallow/knowledge_store.py",
        "src/swallow/mps_policy_store.py",
        "src/swallow/router.py",
        "src/swallow/store.py",
        "src/swallow/truth/knowledge.py",
        "src/swallow/truth/policy.py",
        "src/swallow/truth/route.py",
    }
    violations: list[str] = []
    for path in _src_py_files():
        rel_path = _relative(path)
        if rel_path in allowed_files:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            for alias in node.names:
                if alias.name in protected_imports:
                    violations.append(f"{rel_path}:{node.lineno} imports {alias.name}")

    assert violations == []


def test_no_executor_can_write_task_table_directly() -> None:
    """Execution-plane modules must not persist task state or write task tables."""

    violations: list[str] = []
    for path in _src_py_files():
        rel_path = _relative(path)
        if rel_path not in EXECUTION_PLANE_FILES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in TASK_STATE_WRITE_CALLS:
                        violations.append(f"{rel_path}:{node.lineno} imports {alias.name}")
            elif isinstance(node, ast.Call) and _call_name(node) in TASK_STATE_WRITE_CALLS:
                violations.append(f"{rel_path}:{node.lineno} calls {_call_name(node)}")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and TASK_SQL_WRITE_RE.search(node.value):
                violations.append(f"{rel_path}:{node.lineno} contains direct task-table write SQL")

    assert violations == []


def test_state_transitions_only_via_orchestrator() -> None:
    """Task state persistence is limited to the store layer and Orchestrator."""

    allowed_files = {
        "src/swallow/orchestrator.py",
        "src/swallow/sqlite_store.py",
        "src/swallow/store.py",
    }
    violations: list[str] = []
    for path in _src_py_files():
        rel_path = _relative(path)
        if rel_path in allowed_files:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "save_state":
                        violations.append(f"{rel_path}:{node.lineno} imports save_state")
            elif isinstance(node, ast.Call) and _call_name(node) == "save_state":
                violations.append(f"{rel_path}:{node.lineno} calls save_state")

    assert violations == []


def test_validator_returns_verdict_only() -> None:
    """Validator code may construct verdicts but must not write Truth directly."""

    validator_files = {
        "src/swallow/validator.py",
        "src/swallow/validator_agent.py",
        "src/swallow/consistency_reviewer.py",
    }
    violations: list[str] = []
    verdict_returns: list[str] = []
    for path in _src_py_files():
        rel_path = _relative(path)
        if rel_path not in validator_files:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in TRUTH_WRITE_CALLS:
                        violations.append(f"{rel_path}:{node.lineno} imports {alias.name}")
            elif isinstance(node, ast.Call):
                called_name = _call_name(node)
                if called_name in TRUTH_WRITE_CALLS:
                    violations.append(f"{rel_path}:{node.lineno} calls {called_name}")
                if called_name in {"ValidationResult", "ExecutorResult"}:
                    verdict_returns.append(f"{rel_path}:{node.lineno} returns {called_name}")

    assert violations == []
    assert verdict_returns


def test_route_override_only_set_by_operator() -> None:
    """Route override setters must stay in CLI/operator entry points."""

    violations: list[str] = []
    for path in _src_py_files():
        rel_path = _relative(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign | ast.AnnAssign):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if "route_override_hint" in _target_names(target) and rel_path != "src/swallow/cli.py":
                        violations.append(f"{rel_path}:{node.lineno} writes route_override_hint")
            elif isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg == "executor_override" and rel_path not in {
                        "src/swallow/cli.py",
                        "src/swallow/router.py",
                    }:
                        violations.append(f"{rel_path}:{keyword.lineno} sets executor_override")
                    if keyword.arg == "route_mode_override" and rel_path not in {
                        "src/swallow/cli.py",
                        "src/swallow/orchestrator.py",
                        "src/swallow/router.py",
                    }:
                        violations.append(f"{rel_path}:{keyword.lineno} sets route_mode_override")

    assert violations == []


def test_path_b_does_not_call_provider_router() -> None:
    """Path B executor code may consume route metadata, but must not perform route selection."""

    assert hasattr(router, "fallback_route_for")
    selection_calls = {"select_route", "route_by_name", "fallback_route_for", "route_for_mode"}
    path = SRC_ROOT / "executor.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=_relative(path))
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported = {alias.name for alias in node.names}
            if node.module == "router" and imported & selection_calls:
                for name in sorted(imported & selection_calls):
                    violations.append(f"{_relative(path)}:{node.lineno} imports Provider Router selection function {name}")
        elif isinstance(node, ast.Call) and _call_name(node) in selection_calls:
            violations.append(
                f"{_relative(path)}:{node.lineno} calls Provider Router selection function {_call_name(node)}"
            )

    assert violations == []


def _is_httpx_client_constructor(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"Client", "AsyncClient"}
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "httpx"
    )


def _collect_httpx_client_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_httpx_client_constructor(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and _is_httpx_client_constructor(node.value):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.With | ast.AsyncWith):
            for item in node.items:
                if _is_httpx_client_constructor(item.context_expr) and isinstance(item.optional_vars, ast.Name):
                    names.add(item.optional_vars.id)
    return names


def _chat_completion_url_expression(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return "/chat/completions" in node.value
    return isinstance(node, ast.Call) and _call_name(node) == "resolve_new_api_chat_completions_url"


def _post_call_url_arg(call: ast.Call) -> ast.AST | None:
    if call.args:
        return call.args[0]
    for keyword in call.keywords:
        if keyword.arg == "url":
            return keyword.value
    return None


def _is_httpx_post_call(call: ast.Call, httpx_client_names: set[str]) -> bool:
    if not isinstance(call.func, ast.Attribute) or call.func.attr != "post":
        return False
    receiver = call.func.value
    if isinstance(receiver, ast.Name):
        return receiver.id == "httpx" or receiver.id in httpx_client_names
    return False


def test_specialist_internal_llm_calls_go_through_router() -> None:
    """Chat-completion HTTP calls must go through Provider Router; embeddings and other HTTP are out of scope."""

    assert hasattr(router, "invoke_completion")
    violations: list[str] = []

    for path in _src_py_files():
        rel_path = _relative(path)
        if rel_path == "src/swallow/_http_helpers.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
        httpx_client_names = _collect_httpx_client_names(tree)
        function_stack: list[str] = []

        class Visitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                function_stack.append(node.name)
                self.generic_visit(node)
                function_stack.pop()

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                function_stack.append(node.name)
                self.generic_visit(node)
                function_stack.pop()

            def visit_Call(self, node: ast.Call) -> None:
                if _is_httpx_post_call(node, httpx_client_names):
                    url_arg = _post_call_url_arg(node)
                    if url_arg is not None and _chat_completion_url_expression(url_arg):
                        current_function = function_stack[-1] if function_stack else ""
                        if rel_path != "src/swallow/router.py" or current_function != "invoke_completion":
                            violations.append(f"{rel_path}:{node.lineno} calls chat-completion HTTP directly")
                self.generic_visit(node)

        Visitor().visit(tree)

    assert violations == []


def test_all_ids_are_global_unique_no_local_identity() -> None:
    """ID construction must not include hostname, user, actor, or local paths."""

    violations: list[str] = []
    for path in _src_py_files():
        rel_path = _relative(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign | ast.AnnAssign):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if not any(_is_id_target(name) for target in targets for name in _target_names(target)):
                    continue
                for call in (item for item in ast.walk(node) if isinstance(item, ast.Call)):
                    if _call_name(call) in LOCAL_IDENTITY_CALLS:
                        violations.append(f"{rel_path}:{call.lineno} builds id from {_call_name(call)}")
                for value in _constant_strings(node):
                    if "{hostname}" in value or "{user}" in value or "{workspace_root}" in value:
                        violations.append(f"{rel_path}:{node.lineno} embeds local identity template in id")

    assert violations == []


def test_event_log_has_actor_field(tmp_path: Path) -> None:
    connection = SqliteTaskStore()._connect(tmp_path)
    try:
        columns = {
            str(row["name"]): row
            for row in connection.execute("PRAGMA table_info(event_log)").fetchall()
        }
    finally:
        connection.close()

    assert "actor" in columns
    assert int(columns["actor"]["notnull"]) == 1
    assert str(columns["actor"]["dflt_value"]).strip("'\"") == local_actor()


def test_no_foreign_key_across_namespaces(tmp_path: Path) -> None:
    """Current schema uses no FK constraints, a strict superset of no cross-namespace FK."""

    connection = SqliteTaskStore()._connect(tmp_path)
    try:
        tables = [
            str(row["name"])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        ]
        foreign_keys = {
            table: connection.execute(f"PRAGMA foreign_key_list({table})").fetchall()
            for table in tables
        }
    finally:
        connection.close()

    assert {table: rows for table, rows in foreign_keys.items() if rows} == {}


def test_append_only_tables_reject_update_and_delete(tmp_path: Path) -> None:
    insert_sql = {
        "event_log": (
            "INSERT INTO event_log (event_id, timestamp, actor, kind, payload) VALUES (?, ?, ?, ?, ?)",
            ("event-guard", "2026-01-01T00:00:00+00:00", local_actor(), "guard", "{}"),
            "UPDATE event_log SET kind = 'mutated' WHERE event_id = 'event-guard'",
            "DELETE FROM event_log WHERE event_id = 'event-guard'",
        ),
        "event_telemetry": (
            """
            INSERT INTO event_telemetry (
                telemetry_id, task_id, executor_id, logical_path, timestamp, actor
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("telemetry-guard", "task-guard", "executor-guard", "A", "2026-01-01T00:00:00+00:00", local_actor()),
            "UPDATE event_telemetry SET logical_path = 'B' WHERE telemetry_id = 'telemetry-guard'",
            "DELETE FROM event_telemetry WHERE telemetry_id = 'telemetry-guard'",
        ),
        "route_health": (
            "INSERT INTO route_health (health_id, route_id, timestamp, status) VALUES (?, ?, ?, ?)",
            ("health-guard", "route-guard", "2026-01-01T00:00:00+00:00", "healthy"),
            "UPDATE route_health SET status = 'down' WHERE health_id = 'health-guard'",
            "DELETE FROM route_health WHERE health_id = 'health-guard'",
        ),
        "know_change_log": (
            """
            INSERT INTO know_change_log (
                change_id, target_kind, target_id, action, timestamp, actor
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("change-guard", "canonical", "canonical-guard", "promote", "2026-01-01T00:00:00+00:00", local_actor()),
            "UPDATE know_change_log SET action = 'mutated' WHERE change_id = 'change-guard'",
            "DELETE FROM know_change_log WHERE change_id = 'change-guard'",
        ),
    }
    assert set(APPEND_ONLY_TABLES) == set(insert_sql)

    connection = SqliteTaskStore()._connect(tmp_path)
    try:
        for table, (insert_statement, params, update_statement, delete_statement) in insert_sql.items():
            connection.execute(insert_statement, params)
            connection.commit()
            with pytest.raises(sqlite3.IntegrityError, match=f"{table} is append-only"):
                connection.execute(update_statement)
            connection.rollback()
            with pytest.raises(sqlite3.IntegrityError, match=f"{table} is append-only"):
                connection.execute(delete_statement)
            connection.rollback()
    finally:
        connection.close()


def test_artifact_path_resolved_from_id_only(tmp_path: Path) -> None:
    artifact_path = write_artifact(tmp_path, "task-guard", "summary.md", "ok")

    assert artifact_path == artifacts_dir(tmp_path, "task-guard") / "summary.md"
    with pytest.raises(ValueError):
        write_artifact(tmp_path, "task-guard", "../escape.md", "no")
    with pytest.raises(ValueError):
        write_artifact(tmp_path, "task-guard", "/tmp/escape.md", "no")


def test_ui_backend_only_calls_governance_functions() -> None:
    violations: list[str] = []
    for path in sorted((SRC_ROOT / "web").rglob("*.py")):
        rel_path = _relative(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in UI_FORBIDDEN_WRITE_CALLS:
                        violations.append(f"{rel_path}:{node.lineno} imports {alias.name}")
            elif isinstance(node, ast.Call) and _call_name(node) in UI_FORBIDDEN_WRITE_CALLS:
                violations.append(f"{rel_path}:{node.lineno} calls {_call_name(node)}")

    assert violations == []


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
