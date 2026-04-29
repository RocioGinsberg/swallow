from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "swallow"

NO_SKIP_GUARDS = (
    "test_no_executor_can_write_task_table_directly",
    "test_state_transitions_only_via_orchestrator",
    "test_validator_returns_verdict_only",
    "test_path_b_does_not_call_provider_router",
    "test_specialist_internal_llm_calls_go_through_router",
    "test_canonical_write_only_via_apply_proposal",
    "test_only_apply_proposal_calls_private_writers",
    "test_route_metadata_writes_only_via_apply_proposal",
)


@dataclass(frozen=True)
class AuditFinding:
    path: str
    line: int
    detail: str


@dataclass(frozen=True)
class GuardAudit:
    guard: str
    status: str
    findings: list[AuditFinding]


def _src_py_files() -> list[Path]:
    return sorted(path for path in SRC_ROOT.rglob("*.py") if path.is_file())


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=_relative(path))


def _called_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _imported_names(node: ast.ImportFrom) -> set[str]:
    return {alias.name for alias in node.names}


def _find_protected_writer_uses(*, protected_names: set[str], allowed_files: set[str]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for path in _src_py_files():
        rel_path = _relative(path)
        if rel_path in allowed_files:
            continue
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in protected_names:
                        findings.append(AuditFinding(rel_path, node.lineno, f"imports {alias.name}"))
            elif isinstance(node, ast.Call):
                called_name = _called_name(node)
                if called_name in protected_names:
                    findings.append(AuditFinding(rel_path, node.lineno, f"calls {called_name}"))
    return findings


def _audit_task_table_direct_writes() -> list[AuditFinding]:
    allowed_files = {
        "src/swallow/orchestrator.py",
        "src/swallow/store.py",
        "src/swallow/sqlite_store.py",
        "src/swallow/cli.py",
    }
    protected_calls = {"save_state", "create_task"}
    findings = _find_protected_writer_uses(protected_names=protected_calls, allowed_files=allowed_files)

    for path in _src_py_files():
        rel_path = _relative(path)
        if rel_path in allowed_files:
            continue
        source = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(source.splitlines(), start=1):
            normalized = line.strip().upper()
            if "INSERT INTO TASKS" in normalized or "UPDATE TASKS" in normalized or "DELETE FROM TASKS" in normalized:
                findings.append(AuditFinding(rel_path, lineno, line.strip()))
    return findings


def _audit_state_transitions() -> list[AuditFinding]:
    allowed_files = {"src/swallow/orchestrator.py"}
    state_variable_names = {"state", "task_state", "artifact_state"}
    transition_fields = {
        "status",
        "phase",
        "execution_phase",
        "executor_status",
        "execution_lifecycle",
        "last_phase_checkpoint_at",
    }
    findings: list[AuditFinding] = []
    for path in _src_py_files():
        rel_path = _relative(path)
        if rel_path in allowed_files:
            continue
        for node in ast.walk(_parse(path)):
            if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id in state_variable_names
                    and target.attr in transition_fields
                ):
                    findings.append(AuditFinding(rel_path, target.lineno, f"assigns state-like field {target.attr}"))
    return findings


def _audit_validator_verdict_only() -> list[AuditFinding]:
    path = SRC_ROOT / "validator_agent.py"
    rel_path = _relative(path)
    forbidden_calls = {
        "save_state",
        "append_event",
        "write_artifact",
        "submit_staged_candidate",
        "apply_proposal",
        "register_canonical_proposal",
        "register_route_metadata_proposal",
        "register_policy_proposal",
    }
    findings: list[AuditFinding] = []
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Call) and _called_name(node) in forbidden_calls:
            findings.append(AuditFinding(rel_path, node.lineno, f"calls {_called_name(node)}"))
    findings.extend(
        finding
        for finding in _audit_state_transitions()
        if finding.path == rel_path
    )
    return findings


def _audit_path_b_provider_router_calls() -> list[AuditFinding]:
    path = SRC_ROOT / "executor.py"
    rel_path = _relative(path)
    router_names = {
        "select_route",
        "route_by_name",
        "fallback_route_for",
        "route_for_executor",
        "apply_route_weights",
        "apply_route_capability_profiles",
    }
    findings: list[AuditFinding] = []
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.ImportFrom) and node.module == "router":
            for name in sorted(_imported_names(node) & router_names):
                findings.append(AuditFinding(rel_path, node.lineno, f"imports router provider function {name}"))
        if isinstance(node, ast.Call) and _called_name(node) in router_names:
            findings.append(AuditFinding(rel_path, node.lineno, f"calls router provider function {_called_name(node)}"))
    return findings


def _audit_specialist_internal_llm_router() -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    specialist_files = [
        SRC_ROOT / "agent_llm.py",
        SRC_ROOT / "literature_specialist.py",
        SRC_ROOT / "quality_reviewer.py",
        SRC_ROOT / "meta_optimizer.py",
        SRC_ROOT / "librarian_executor.py",
        SRC_ROOT / "ingestion_specialist.py",
        SRC_ROOT / "consistency_reviewer.py",
    ]
    for path in specialist_files:
        if not path.exists():
            continue
        rel_path = _relative(path)
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.ImportFrom) and node.module == "agent_llm":
                if "call_agent_llm" in _imported_names(node):
                    findings.append(AuditFinding(rel_path, node.lineno, "imports call_agent_llm"))
            if isinstance(node, ast.Call):
                called_name = _called_name(node)
                if called_name == "call_agent_llm":
                    findings.append(AuditFinding(rel_path, node.lineno, "calls call_agent_llm"))
                if rel_path == "src/swallow/agent_llm.py" and called_name == "post":
                    findings.append(AuditFinding(rel_path, node.lineno, "calls httpx.post directly"))
    return findings


def run_audit() -> list[GuardAudit]:
    guard_to_findings = {
        "test_no_executor_can_write_task_table_directly": _audit_task_table_direct_writes(),
        "test_state_transitions_only_via_orchestrator": _audit_state_transitions(),
        "test_validator_returns_verdict_only": _audit_validator_verdict_only(),
        "test_path_b_does_not_call_provider_router": _audit_path_b_provider_router_calls(),
        "test_specialist_internal_llm_calls_go_through_router": _audit_specialist_internal_llm_router(),
        "test_canonical_write_only_via_apply_proposal": _find_protected_writer_uses(
            protected_names={"append_canonical_record", "persist_wiki_entry_from_record"},
            allowed_files={
                "src/swallow/governance.py",
                "src/swallow/store.py",
                "src/swallow/knowledge_store.py",
            },
        ),
        "test_only_apply_proposal_calls_private_writers": _find_protected_writer_uses(
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
        ),
        "test_route_metadata_writes_only_via_apply_proposal": _find_protected_writer_uses(
            protected_names={"save_route_weights", "save_route_capability_profiles"},
            allowed_files={
                "src/swallow/governance.py",
                "src/swallow/router.py",
            },
        ),
    }
    audits: list[GuardAudit] = []
    for guard_name in NO_SKIP_GUARDS:
        findings = guard_to_findings[guard_name]
        audits.append(
            GuardAudit(
                guard=guard_name,
                status="red" if findings else "green",
                findings=findings,
            )
        )
    return audits


def main() -> None:
    print(json.dumps([asdict(audit) for audit in run_audit()], indent=2))


if __name__ == "__main__":
    main()
