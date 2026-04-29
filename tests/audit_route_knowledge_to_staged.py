from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from swallow.router import ROUTE_REGISTRY


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "swallow"
TEST_ROOT = REPO_ROOT / "tests"
BLOCKED_AUTHORITIES = {"canonical-write-forbidden", "staged-knowledge"}


@dataclass(frozen=True)
class RouteAuditRecord:
    source: str
    path: str
    line: int
    route_name: str
    executor_name: str
    executor_family: str
    taxonomy_role: str
    taxonomy_memory_authority: str


@dataclass(frozen=True)
class SpecialistAuthorityRecord:
    path: str
    line: int
    name: str
    value: str


@dataclass(frozen=True)
class RouteKnowledgeAudit:
    builtin_blocked_routes: list[RouteAuditRecord]
    static_route_specs_with_blocked_authority: list[RouteAuditRecord]
    specialist_blocked_authorities: list[SpecialistAuthorityRecord]
    route_knowledge_to_staged_call_sites: list[str]


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _constant_string(node: ast.AST | None) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def _keyword(call: ast.Call, name: str) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _extract_route_spec(path: Path, call: ast.Call) -> RouteAuditRecord | None:
    if _call_name(call.func) != "RouteSpec":
        return None
    taxonomy = _keyword(call, "taxonomy")
    taxonomy_role = ""
    taxonomy_memory_authority = ""
    if isinstance(taxonomy, ast.Call) and _call_name(taxonomy.func) == "TaxonomyProfile":
        taxonomy_role = _constant_string(_keyword(taxonomy, "system_role"))
        taxonomy_memory_authority = _constant_string(_keyword(taxonomy, "memory_authority"))
    if taxonomy_memory_authority not in BLOCKED_AUTHORITIES:
        return None
    rel_path = _relative(path)
    return RouteAuditRecord(
        source="production" if rel_path.startswith("src/") else "test",
        path=rel_path,
        line=call.lineno,
        route_name=_constant_string(_keyword(call, "name")),
        executor_name=_constant_string(_keyword(call, "executor_name")),
        executor_family=_constant_string(_keyword(call, "executor_family")),
        taxonomy_role=taxonomy_role,
        taxonomy_memory_authority=taxonomy_memory_authority,
    )


def _scan_route_specs() -> list[RouteAuditRecord]:
    records: list[RouteAuditRecord] = []
    for root in (SRC_ROOT, TEST_ROOT):
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=_relative(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    record = _extract_route_spec(path, node)
                    if record is not None:
                        records.append(record)
    return records


def _scan_specialist_authorities() -> list[SpecialistAuthorityRecord]:
    records: list[SpecialistAuthorityRecord] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=_relative(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            value = _constant_string(node.value)
            if value not in BLOCKED_AUTHORITIES:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.endswith("_MEMORY_AUTHORITY"):
                    records.append(
                        SpecialistAuthorityRecord(
                            path=_relative(path),
                            line=node.lineno,
                            name=target.id,
                            value=value,
                        )
                    )
    return records


def _builtin_blocked_routes() -> list[RouteAuditRecord]:
    records: list[RouteAuditRecord] = []
    for route in ROUTE_REGISTRY.values():
        authority = route.taxonomy.memory_authority
        if authority not in BLOCKED_AUTHORITIES:
            continue
        records.append(
            RouteAuditRecord(
                source="builtin",
                path="src/swallow/router.py",
                line=0,
                route_name=route.name,
                executor_name=route.executor_name,
                executor_family=route.executor_family,
                taxonomy_role=route.taxonomy.system_role,
                taxonomy_memory_authority=authority,
            )
        )
    return records


def _route_knowledge_to_staged_call_sites() -> list[str]:
    call_sites: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=_relative(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _call_name(node.func) == "_route_knowledge_to_staged":
                call_sites.append(f"{_relative(path)}:{node.lineno}")
    return call_sites


def run_audit() -> RouteKnowledgeAudit:
    return RouteKnowledgeAudit(
        builtin_blocked_routes=_builtin_blocked_routes(),
        static_route_specs_with_blocked_authority=_scan_route_specs(),
        specialist_blocked_authorities=_scan_specialist_authorities(),
        route_knowledge_to_staged_call_sites=_route_knowledge_to_staged_call_sites(),
    )


def main() -> None:
    audit = run_audit()
    payload: dict[str, Any] = asdict(audit)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
