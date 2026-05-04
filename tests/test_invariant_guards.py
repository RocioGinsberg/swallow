from __future__ import annotations

import ast
import re
import sqlite3
from pathlib import Path

import pytest

import swallow.provider_router.router as router
from swallow.application.infrastructure.identity import local_actor
from swallow.application.infrastructure.paths import artifacts_dir
from swallow.provider_router.router import route_by_name
from swallow.truth_governance.sqlite_store import APPEND_ONLY_TABLES, SqliteTaskStore
from swallow.truth_governance.store import write_artifact
from swallow.orchestration.synthesis import _MPS_DEFAULT_HTTP_ROUTE, _route_is_path_a


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
    "src/swallow/orchestration/executor.py",
    "src/swallow/orchestration/validator.py",
    "src/swallow/orchestration/validator_agent.py",
    "src/swallow/application/services/librarian_executor.py",
    "src/swallow/application/services/literature_specialist.py",
    "src/swallow/application/services/quality_reviewer.py",
    "src/swallow/application/services/consistency_reviewer.py",
    "src/swallow/application/services/meta_optimizer.py",
    "src/swallow/application/services/meta_optimizer_agent.py",
    "src/swallow/knowledge_retrieval/_internal_ingestion_pipeline.py",
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
    "apply_proposal",
    "create_task",
    "run_task",
    "save_state",
    "submit_staged_candidate",
    "write_artifact",
}
HARNESS_HELPER_EVENT_MODULES = {
    "src/swallow/orchestration/retrieval_flow.py",
    "src/swallow/orchestration/execution_attempts.py",
    "src/swallow/orchestration/artifact_writer.py",
    "src/swallow/orchestration/task_report.py",
}
HARNESS_HELPER_ALLOWED_EVENT_KINDS = {
    "retrieval.completed",
    "executor.completed",
    "executor.failed",
    "compatibility.completed",
    "execution_fit.completed",
    "knowledge_policy.completed",
    "validation.completed",
    "retry_policy.completed",
    "execution_budget_policy.completed",
    "stop_policy.completed",
    "checkpoint_snapshot.completed",
    "artifacts.written",
}
HARNESS_HELPER_ALLOWED_EVENT_CONSTANTS = {
    "EVENT_RETRIEVAL_COMPLETED",
    "EVENT_EXECUTOR_COMPLETED",
    "EVENT_EXECUTOR_FAILED",
}
HARNESS_HELPER_DISALLOWED_EVENT_KINDS = {
    "state_transitioned",
    "entered_waiting_human",
}
KNOWLEDGE_RETRIEVAL_PACKAGE = "swallow.knowledge_retrieval"
KNOWLEDGE_PLANE_MODULE = "swallow.knowledge_retrieval.knowledge_plane"
KNOWLEDGE_RAW_MATERIAL_MODULE = "swallow.knowledge_retrieval.raw_material"
KNOWLEDGE_RAW_MATERIAL_ALLOWED_FILES = {
    "src/swallow/application/services/librarian_executor.py",
}
WIKI_COMPILER_MODULE = "src/swallow/application/services/wiki_compiler.py"
WIKI_COMMAND_MODULE = "src/swallow/application/commands/wiki.py"
WIKI_COMPILER_FORBIDDEN_CALLS = {
    "append_canonical_record",
    "append_event",
    "apply_proposal",
    "persist_wiki_entry_from_record",
    "save_audit_trigger_policy",
    "save_mps_policy",
    "save_route_capability_profiles",
    "save_route_policy",
    "save_route_registry",
    "save_route_weights",
    "save_state",
    "submit_staged_candidate",
}
HTTP_KNOWLEDGE_QUERY_CALLS = {
    "build_canonical_knowledge_payload",
    "build_knowledge_detail_payload",
    "build_knowledge_relations_payload",
    "build_staged_knowledge_payload",
    "build_wiki_knowledge_payload",
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


def _event_type_refs(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.IfExp):
        return _event_type_refs(node.body) | _event_type_refs(node.orelse)
    return set()


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
    production callers must go through `swallow.truth_governance.governance.apply_proposal`.
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


def _knowledge_plane_import_boundary_violation(rel_path: str, imported_module: str, lineno: int) -> str:
    if not imported_module.startswith(KNOWLEDGE_RETRIEVAL_PACKAGE):
        return ""
    if rel_path.startswith("src/swallow/knowledge_retrieval/"):
        return ""
    if imported_module == KNOWLEDGE_PLANE_MODULE:
        return ""
    if imported_module == KNOWLEDGE_RAW_MATERIAL_MODULE and rel_path in KNOWLEDGE_RAW_MATERIAL_ALLOWED_FILES:
        return ""
    if imported_module == KNOWLEDGE_RAW_MATERIAL_MODULE:
        return f"{rel_path}:{lineno} imports raw_material outside its storage-boundary allowlist"
    return f"{rel_path}:{lineno} imports {imported_module}; use {KNOWLEDGE_PLANE_MODULE}"


def _knowledge_plane_import_boundary_violations_for_tree(tree: ast.AST, rel_path: str) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                violation = _knowledge_plane_import_boundary_violation(rel_path, alias.name, node.lineno)
                if violation:
                    violations.append(violation)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules: list[str]
            if node.module == KNOWLEDGE_RETRIEVAL_PACKAGE:
                modules = [
                    f"{node.module}.{alias.name}" if alias.name != "*" else node.module
                    for alias in node.names
                ]
            else:
                modules = [node.module]
            for module in modules:
                violation = _knowledge_plane_import_boundary_violation(rel_path, module, node.lineno)
                if violation:
                    violations.append(violation)
    return violations


def _knowledge_plane_import_boundary_violations_for_source(source: str, rel_path: str) -> list[str]:
    return _knowledge_plane_import_boundary_violations_for_tree(ast.parse(source), rel_path)


def _function_named(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Function not found: {name}")


def _fastapi_route_path(decorator: ast.AST, method: str) -> str:
    if not isinstance(decorator, ast.Call):
        return ""
    if not isinstance(decorator.func, ast.Attribute) or decorator.func.attr != method:
        return ""
    if not decorator.args:
        return ""
    path_arg = decorator.args[0]
    if isinstance(path_arg, ast.Constant) and isinstance(path_arg.value, str):
        return path_arg.value
    return ""


def test_knowledge_plane_import_boundary_guard_rejects_internal_import_fixture() -> None:
    violations = _knowledge_plane_import_boundary_violations_for_source(
        "from swallow.knowledge_retrieval._internal_knowledge_store import load_task_knowledge_view\n",
        "src/swallow/application/commands/example.py",
    )

    assert violations == [
        "src/swallow/application/commands/example.py:1 imports "
        "swallow.knowledge_retrieval._internal_knowledge_store; use "
        "swallow.knowledge_retrieval.knowledge_plane"
    ]


def test_knowledge_plane_import_boundary_guard_rejects_facade_covered_import_fixture() -> None:
    violations = _knowledge_plane_import_boundary_violations_for_source(
        "from swallow.knowledge_retrieval.retrieval import retrieve_context\n",
        "src/swallow/orchestration/example.py",
    )

    assert violations == [
        "src/swallow/orchestration/example.py:1 imports "
        "swallow.knowledge_retrieval.retrieval; use swallow.knowledge_retrieval.knowledge_plane"
    ]


def test_knowledge_plane_import_boundary_guard_allows_facade_and_raw_material_exception_fixture() -> None:
    facade_violations = _knowledge_plane_import_boundary_violations_for_source(
        "from swallow.knowledge_retrieval.knowledge_plane import retrieve_knowledge_context\n",
        "src/swallow/orchestration/example.py",
    )
    raw_material_violations = _knowledge_plane_import_boundary_violations_for_source(
        "from swallow.knowledge_retrieval.raw_material import FilesystemRawMaterialStore\n",
        "src/swallow/application/services/librarian_executor.py",
    )

    assert facade_violations == []
    assert raw_material_violations == []


def test_knowledge_plane_public_boundary_imports() -> None:
    violations: list[str] = []
    for path in _src_py_files():
        rel_path = _relative(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
        violations.extend(_knowledge_plane_import_boundary_violations_for_tree(tree, rel_path))

    assert violations == []


def test_wiki_compiler_agent_boundary_propose_only() -> None:
    rel_path = WIKI_COMPILER_MODULE
    tree = ast.parse((REPO_ROOT / rel_path).read_text(encoding="utf-8"), filename=rel_path)
    violations: list[str] = []
    provider_router_imports: set[str] = set()
    knowledge_plane_imports: set[str] = set()
    calls: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"httpx", "openai", "anthropic"}:
                    violations.append(f"{rel_path}:{node.lineno} imports provider/client module {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "swallow.provider_router.agent_llm":
                provider_router_imports.update(alias.name for alias in node.names)
            if node.module == KNOWLEDGE_PLANE_MODULE:
                knowledge_plane_imports.update(alias.name for alias in node.names)
            if node.module and node.module.startswith("swallow.knowledge_retrieval._internal"):
                violations.append(f"{rel_path}:{node.lineno} imports knowledge internal module {node.module}")
            for alias in node.names:
                if alias.name in WIKI_COMPILER_FORBIDDEN_CALLS:
                    violations.append(f"{rel_path}:{node.lineno} imports {alias.name}")
        elif isinstance(node, ast.Call):
            called_name = _call_name(node)
            calls.add(called_name)
            if called_name in WIKI_COMPILER_FORBIDDEN_CALLS:
                violations.append(f"{rel_path}:{node.lineno} calls {called_name}")

    assert "call_agent_llm" in provider_router_imports
    assert "extract_json_object" in provider_router_imports
    assert "submit_staged_knowledge" in knowledge_plane_imports
    assert "call_agent_llm" in calls
    assert "submit_staged_knowledge" in calls
    assert violations == []


def test_wiki_compiler_refresh_evidence_updates_parser_version_anchor() -> None:
    rel_path = WIKI_COMMAND_MODULE
    tree = ast.parse((REPO_ROOT / rel_path).read_text(encoding="utf-8"), filename=rel_path)
    function = _function_named(tree, "refresh_wiki_evidence_command")
    function_strings = set(_constant_strings(function))
    result_call_keywords: set[str] = set()

    for node in ast.walk(function):
        if isinstance(node, ast.Call) and _call_name(node) == "EvidenceRefreshCommandResult":
            result_call_keywords.update(keyword.arg or "" for keyword in node.keywords)

    assert "refresh-evidence requires --span or --heading-path." in function_strings
    assert {"content_hash", "parser_version", "span", "heading_path"} <= function_strings
    assert {"content_hash", "parser_version", "span", "heading_path"} <= result_call_keywords


def test_http_knowledge_routes_only_call_application_queries() -> None:
    rel_path = "src/swallow/adapters/http/api.py"
    tree = ast.parse((REPO_ROOT / rel_path).read_text(encoding="utf-8"), filename=rel_path)
    violations: list[str] = []
    knowledge_get_routes: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("swallow.knowledge_retrieval"):
                violations.append(f"{rel_path}:{node.lineno} imports {module}; use application.queries.knowledge")
            if module in {"swallow.truth_governance.sqlite_store", "swallow.application.infrastructure.paths"}:
                violations.append(f"{rel_path}:{node.lineno} imports lower-layer path/store module {module}")
        if not isinstance(node, ast.FunctionDef):
            continue
        route_paths = [
            _fastapi_route_path(decorator, "get")
            for decorator in node.decorator_list
        ]
        route_paths = [path for path in route_paths if path.startswith("/api/knowledge")]
        if not route_paths:
            continue
        knowledge_get_routes.extend(route_paths)
        calls = {_call_name(call) for call in ast.walk(node) if isinstance(call, ast.Call)}
        if not calls & HTTP_KNOWLEDGE_QUERY_CALLS:
            violations.append(f"{rel_path}:{node.lineno} route {route_paths[0]} does not call application query")
        lower_layer_calls = calls & {"load_task_knowledge_view", "list_staged_knowledge", "list_knowledge_relations"}
        for call_name in sorted(lower_layer_calls):
            violations.append(f"{rel_path}:{node.lineno} route {route_paths[0]} calls lower-layer {call_name}")

    assert set(knowledge_get_routes) == {
        "/api/knowledge/wiki",
        "/api/knowledge/canonical",
        "/api/knowledge/staged",
        "/api/knowledge/{object_id}",
        "/api/knowledge/{object_id}/relations",
    }
    assert violations == []


def test_knowledge_relation_metadata_types_cover_design_modes() -> None:
    from swallow.knowledge_retrieval.knowledge_plane import KNOWLEDGE_RELATION_TYPES
    from swallow.application.services.wiki_compiler import WIKI_COMPILER_METADATA_RELATION_TYPES

    design_metadata_types = {
        "supersedes",
        "refines",
        "contradicts",
        "refers_to",
        "derived_from",
    }
    legacy_relation_types = {"cites", "extends", "related_to"}

    assert set(WIKI_COMPILER_METADATA_RELATION_TYPES) == design_metadata_types
    assert {"refines", "contradicts"} <= set(KNOWLEDGE_RELATION_TYPES)
    assert legacy_relation_types <= set(KNOWLEDGE_RELATION_TYPES)
    assert "derived_from" not in KNOWLEDGE_RELATION_TYPES
    assert "supersedes" not in KNOWLEDGE_RELATION_TYPES
    assert "refers_to" not in KNOWLEDGE_RELATION_TYPES


def test_canonical_write_only_via_apply_proposal() -> None:
    violations = _find_protected_writer_uses(
        protected_names={
            "append_canonical_record",
            "mark_canonical_records_superseded_by_targets",
            "persist_wiki_entry_from_record",
        },
        allowed_files={
            "src/swallow/truth_governance/truth/knowledge.py",
            "src/swallow/truth_governance/store.py",
            "src/swallow/knowledge_retrieval/knowledge_plane.py",  # facade wrapper; governance still owns promotion
            "src/swallow/knowledge_retrieval/_internal_knowledge_store.py",
        },
    )

    assert violations == []


def test_route_metadata_writes_only_via_apply_proposal() -> None:
    """Route metadata writes are owned by the physical store and called by RouteRepo.

    `provider_router/router.py` remains allowlisted only as a legacy
    compatibility facade exposing wrapper functions for older imports; it is
    not the canonical physical writer owner.
    """

    protected_writers = {
        "save_route_registry",
        "save_route_policy",
        "save_route_weights",
        "save_route_capability_profiles",
    }
    route_repo_tree = ast.parse(
        (SRC_ROOT / "truth_governance" / "truth" / "route.py").read_text(encoding="utf-8"),
        filename="src/swallow/truth_governance/truth/route.py",
    )
    route_metadata_store_imports = {
        alias.name
        for node in ast.walk(route_repo_tree)
        if isinstance(node, ast.ImportFrom) and node.module == "swallow.provider_router.route_metadata_store"
        for alias in node.names
    }
    assert protected_writers <= route_metadata_store_imports

    violations = _find_protected_writer_uses(
        protected_names=protected_writers,
        allowed_files={
            "src/swallow/provider_router/route_metadata_store.py",  # physical route metadata writer owner
            "src/swallow/provider_router/router.py",  # legacy compatibility facade wrappers
            "src/swallow/truth_governance/truth/route.py",  # governance repository caller
        },
    )

    assert violations == []


def test_no_hardcoded_local_actor_outside_identity_module() -> None:
    violations: list[str] = []
    for path in _src_py_files():
        rel_path = _relative(path)
        if rel_path == "src/swallow/application/infrastructure/identity.py":
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
        if rel_path == "src/swallow/application/infrastructure/workspace.py":
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
            "mark_canonical_records_superseded_by_targets",
            "persist_wiki_entry_from_record",
            "save_route_registry",
            "save_route_policy",
            "save_route_weights",
            "save_route_capability_profiles",
            "save_audit_trigger_policy",
            "save_mps_policy",
        },
        allowed_files={
            "src/swallow/truth_governance/store.py",
            "src/swallow/knowledge_retrieval/knowledge_plane.py",  # facade wrapper; governance still owns promotion
            "src/swallow/knowledge_retrieval/_internal_knowledge_store.py",
            "src/swallow/provider_router/route_metadata_store.py",  # physical route metadata writer owner
            "src/swallow/provider_router/router.py",  # legacy compatibility facade wrappers
            "src/swallow/application/services/consistency_audit.py",
            "src/swallow/application/services/mps_policy_store.py",
            "src/swallow/truth_governance/truth/knowledge.py",
            "src/swallow/truth_governance/truth/route.py",
            "src/swallow/truth_governance/truth/policy.py",
        },
    )

    assert violations == []


def test_mps_policy_writes_via_apply_proposal() -> None:
    violations = _find_protected_writer_uses(
        protected_names={"save_mps_policy"},
        allowed_files={
            "src/swallow/application/services/mps_policy_store.py",
            "src/swallow/truth_governance/truth/policy.py",
        },
    )

    assert violations == []
    source = (SRC_ROOT / "application" / "services" / "mps_policy_store.py").read_text(encoding="utf-8")
    assert "mps_policy_path" in source
    assert '".swl"' not in source


def test_canonical_and_policy_handlers_own_repository_write_methods() -> None:
    violations = _find_protected_writer_uses(
        protected_names={"_promote_canonical", "_apply_policy_change"},
        allowed_files={
            "src/swallow/truth_governance/apply_canonical.py",
            "src/swallow/truth_governance/apply_policy.py",
        },
    )

    assert violations == []


def test_route_metadata_handler_owns_repository_write_methods() -> None:
    violations = _find_protected_writer_uses(
        protected_names={"_apply_metadata_change"},
        allowed_files={"src/swallow/truth_governance/apply_route_metadata.py"},
    )

    assert violations == []


def test_no_module_outside_governance_imports_store_writes() -> None:
    protected_imports = {
        "append_canonical_record",
        "mark_canonical_records_superseded_by_targets",
        "persist_wiki_entry_from_record",
        "save_route_weights",
        "save_route_registry",
        "save_route_policy",
        "save_route_capability_profiles",
        "save_audit_trigger_policy",
        "save_mps_policy",
    }
    allowed_files = {
        "src/swallow/application/services/consistency_audit.py",
        "src/swallow/knowledge_retrieval/_internal_knowledge_store.py",
        "src/swallow/application/services/mps_policy_store.py",
        "src/swallow/provider_router/route_metadata_store.py",
        "src/swallow/provider_router/router.py",
        "src/swallow/truth_governance/store.py",
        "src/swallow/truth_governance/truth/knowledge.py",
        "src/swallow/truth_governance/truth/policy.py",
        "src/swallow/truth_governance/truth/route.py",
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
        "src/swallow/orchestration/orchestrator.py",
        "src/swallow/truth_governance/sqlite_store.py",
        "src/swallow/truth_governance/store.py",
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


def test_harness_helper_modules_only_emit_allowlisted_event_kinds() -> None:
    """Harness-sourced helper modules may append telemetry events, never state-advance events."""

    violations: list[str] = []
    for rel_path in sorted(HARNESS_HELPER_EVENT_MODULES):
        path = REPO_ROOT / rel_path
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
        source_strings = set(_constant_strings(tree))
        disallowed_strings = source_strings & HARNESS_HELPER_DISALLOWED_EVENT_KINDS
        for event_kind in sorted(disallowed_strings):
            violations.append(f"{rel_path} references disallowed event kind {event_kind}")

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _call_name(node) != "Event":
                continue
            event_type_nodes = [keyword.value for keyword in node.keywords if keyword.arg == "event_type"]
            if not event_type_nodes:
                violations.append(f"{rel_path}:{node.lineno} constructs Event without explicit event_type")
                continue
            for ref in _event_type_refs(event_type_nodes[0]):
                if ref in HARNESS_HELPER_ALLOWED_EVENT_KINDS or ref in HARNESS_HELPER_ALLOWED_EVENT_CONSTANTS:
                    continue
                violations.append(f"{rel_path}:{node.lineno} emits non-allowlisted event type {ref}")

    assert violations == []


def test_validator_returns_verdict_only() -> None:
    """Validator code may construct verdicts but must not write Truth directly."""

    validator_files = {
        "src/swallow/orchestration/validator.py",
        "src/swallow/orchestration/validator_agent.py",
        "src/swallow/application/services/consistency_reviewer.py",
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
                    if "route_override_hint" in _target_names(target) and rel_path != "src/swallow/adapters/cli.py":
                        violations.append(f"{rel_path}:{node.lineno} writes route_override_hint")
            elif isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg == "executor_override" and rel_path not in {
                        "src/swallow/adapters/cli.py",
                        "src/swallow/application/commands/route_metadata.py",
                        "src/swallow/adapters/cli_commands/route.py",
                        "src/swallow/provider_router/router.py",
                    }:
                        violations.append(f"{rel_path}:{keyword.lineno} sets executor_override")
                    if keyword.arg == "route_mode_override" and rel_path not in {
                        "src/swallow/adapters/cli.py",
                        "src/swallow/application/commands/route_metadata.py",
                        "src/swallow/adapters/cli_commands/route.py",
                        "src/swallow/orchestration/orchestrator.py",
                        "src/swallow/provider_router/router.py",
                    }:
                        violations.append(f"{rel_path}:{keyword.lineno} sets route_mode_override")

    assert violations == []


def test_path_b_does_not_call_provider_router() -> None:
    """Path B executor code may consume route metadata, but must not perform route selection."""

    assert hasattr(router, "fallback_route_for")
    selection_calls = {"select_route", "route_by_name", "fallback_route_for", "route_for_mode"}
    path = SRC_ROOT / "orchestration" / "executor.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=_relative(path))
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported = {alias.name for alias in node.names}
            if node.module in {"router", "swallow.provider_router.router"} and imported & selection_calls:
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
        if rel_path == "src/swallow/provider_router/_http_helpers.py":
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
                        if rel_path != "src/swallow/provider_router/completion_gateway.py" or current_function != "invoke_completion":
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
        "route_change_log": (
            """
            INSERT INTO route_change_log (
                change_id, target_kind, target_id, action, timestamp, actor
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("route-change-guard", "route_registry", "local-summary", "upsert", "2026-01-01T00:00:00+00:00", local_actor()),
            "UPDATE route_change_log SET action = 'mutated' WHERE change_id = 'route-change-guard'",
            "DELETE FROM route_change_log WHERE change_id = 'route-change-guard'",
        ),
        "policy_change_log": (
            """
            INSERT INTO policy_change_log (
                change_id, target_kind, target_id, action, timestamp, actor
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("policy-change-guard", "audit_trigger_policy", "audit_trigger:global", "upsert", "2026-01-01T00:00:00+00:00", local_actor()),
            "UPDATE policy_change_log SET action = 'mutated' WHERE change_id = 'policy-change-guard'",
            "DELETE FROM policy_change_log WHERE change_id = 'policy-change-guard'",
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
    for path in sorted((SRC_ROOT / "adapters" / "http").rglob("*.py")):
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
    tree = ast.parse((SRC_ROOT / "orchestration" / "synthesis.py").read_text(encoding="utf-8"))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "messages":
            violations.append(f"keyword messages at line {node.lineno}")
        if isinstance(node, ast.Name) and node.id == "messages":
            violations.append(f"name messages at line {node.lineno}")

    assert violations == []


def test_synthesis_uses_provider_router() -> None:
    tree = ast.parse((SRC_ROOT / "orchestration" / "synthesis.py").read_text(encoding="utf-8"))
    imported_names: set[str] = set()
    direct_route_spec_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in {"router", "swallow.provider_router.router"}:
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
    source = (SRC_ROOT / "orchestration" / "synthesis.py").read_text(encoding="utf-8")

    assert "_participant_state_for_call" in source
    assert "replace(" in source
    assert "run_http_executor(transient_state" in source
    assert "run_http_executor(arbiter_state" in source


def test_synthesis_module_does_not_call_submit_staged_candidate() -> None:
    tree = ast.parse((SRC_ROOT / "orchestration" / "synthesis.py").read_text(encoding="utf-8"))
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
