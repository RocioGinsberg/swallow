from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from swallow.provider_router import route_metadata_store as route_metadata_store_module
from swallow.provider_router.completion_gateway import invoke_completion
from swallow.provider_router import route_policy as route_policy_module
from swallow.provider_router.route_reports import (
    build_route_capability_profiles_report,
    build_route_policy_report,
    build_route_registry_report,
    build_route_weights_report,
)
from swallow.provider_router import route_registry as route_registry_module
from swallow.provider_router import route_selection as route_selection_module
from swallow.truth_governance import sqlite_store
from swallow.knowledge_retrieval.dialect_data import DEFAULT_EXECUTOR, normalize_executor_name
from swallow.surface_tools.identity import local_actor
from swallow.orchestration.models import RouteCapabilities, RouteSelection, RouteSpec, TaskState, TaxonomyProfile, infer_task_family, utc_now
from swallow.surface_tools.paths import (
    route_capabilities_path,
    route_fallbacks_path,
    route_policy_path,
    route_registry_path,
    route_weights_path,
)


CAPABILITY_MATCH_FIELDS = (
    "execution_kind",
    "supports_tool_loop",
    "filesystem_access",
    "network_access",
    "deterministic",
    "resumable",
)

SUMMARY_FALLBACK_ROUTE_NAME = route_policy_module.SUMMARY_FALLBACK_ROUTE_NAME

ROUTE_MODE_ALIASES = route_policy_module.ROUTE_MODE_ALIASES

ROUTE_NAME_ALIASES = route_policy_module.ROUTE_NAME_ALIASES
ROUTE_MODE_TO_ROUTE_NAME = route_policy_module.ROUTE_MODE_TO_ROUTE_NAME
ROUTE_COMPLEXITY_BIAS_ROUTES = route_policy_module.ROUTE_COMPLEXITY_BIAS_ROUTES
ROUTE_STRATEGY_COMPLEXITY_HINTS = route_policy_module.ROUTE_STRATEGY_COMPLEXITY_HINTS
ROUTE_PARALLEL_INTENT_HINTS = route_policy_module.ROUTE_PARALLEL_INTENT_HINTS


def _sync_route_policy_exports() -> None:
    global SUMMARY_FALLBACK_ROUTE_NAME

    SUMMARY_FALLBACK_ROUTE_NAME = route_policy_module.SUMMARY_FALLBACK_ROUTE_NAME


def _registered_executor_name(raw_name: str | None) -> str:
    raw = (raw_name or "").strip().lower()
    normalized = normalize_executor_name(raw_name)
    if raw and normalized == DEFAULT_EXECUTOR and raw != DEFAULT_EXECUTOR:
        return raw
    return normalized


def _normalize_quality_weight(value: object) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, int | float):
        return max(float(value), 0.0)
    if isinstance(value, str):
        try:
            return max(float(value.strip()), 0.0)
        except ValueError:
            return 1.0
    return 1.0


def _sort_routes_by_quality(routes: Iterable[RouteSpec]) -> list[RouteSpec]:
    route_list = list(routes)
    return sorted(route_list, key=lambda route: (-route.quality_weight, route.name))


def _normalize_task_type(value: object) -> str:
    return str(value or "").strip().lower()


def _normalize_task_family_scores(scores: object) -> dict[str, float]:
    if not isinstance(scores, dict):
        return {}
    normalized: dict[str, float] = {}
    for task_type, raw_score in scores.items():
        normalized_task_type = _normalize_task_type(task_type)
        if not normalized_task_type:
            continue
        normalized[normalized_task_type] = round(_normalize_quality_weight(raw_score), 6)
    return normalized


def _normalize_unsupported_task_types(task_types: object) -> list[str]:
    if not isinstance(task_types, list):
        return []
    normalized = {_normalize_task_type(item) for item in task_types}
    normalized.discard("")
    return sorted(normalized)


def _normalize_route_capability_profile(profile: object) -> dict[str, object]:
    if not isinstance(profile, dict):
        return {"task_family_scores": {}, "unsupported_task_types": []}
    return {
        "task_family_scores": _normalize_task_family_scores(profile.get("task_family_scores", {})),
        "unsupported_task_types": _normalize_unsupported_task_types(profile.get("unsupported_task_types", [])),
    }


def _task_family_score(route: RouteSpec, task_family: str) -> float:
    normalized_task_family = _normalize_task_type(task_family)
    if not normalized_task_family:
        return 0.0
    return _normalize_quality_weight(route.task_family_scores.get(normalized_task_family, 0.0))


def _route_supports_task_family(route: RouteSpec, task_family: str) -> bool:
    normalized_task_family = _normalize_task_type(task_family)
    if not normalized_task_family:
        return True
    unsupported = {_normalize_task_type(item) for item in route.unsupported_task_types}
    return normalized_task_family not in unsupported


def _sort_routes_by_preference(routes: Iterable[RouteSpec], task_family: str = "") -> list[RouteSpec]:
    route_list = list(routes)
    return sorted(
        route_list,
        key=lambda route: (-_task_family_score(route, task_family), -route.quality_weight, route.name),
    )


def _filter_supported_task_family(routes: Iterable[RouteSpec], task_family: str) -> list[RouteSpec]:
    return [route for route in routes if _route_supports_task_family(route, task_family)]


class RouteRegistry:
    def __init__(self, routes: Iterable[RouteSpec] = ()) -> None:
        self._routes: dict[str, RouteSpec] = {}
        for route in routes:
            self.register(route)

    def register(self, route: RouteSpec) -> None:
        self._routes[route.name] = route

    def replace(self, routes: Iterable[RouteSpec]) -> None:
        self._routes = {}
        for route in routes:
            self.register(route)

    def get(self, route_name: str) -> RouteSpec:
        return self._routes[route_name]

    def maybe_get(self, route_name: str) -> RouteSpec | None:
        return self._routes.get(route_name)

    def values(self) -> tuple[RouteSpec, ...]:
        return tuple(self._routes.values())

    def route_for_mode(self, route_mode: str) -> RouteSpec | None:
        route_name = route_policy_module.ROUTE_MODE_TO_ROUTE_NAME.get(route_mode)
        return self.maybe_get(route_name) if route_name else None

    def route_for_executor(self, executor_name: str) -> RouteSpec:
        normalized_executor = normalize_executor_name(executor_name)
        mode_route = self.route_for_mode(normalized_executor)
        if mode_route is not None and _registered_executor_name(mode_route.executor_name) == normalized_executor:
            return mode_route
        for route in self.values():
            if _registered_executor_name(route.executor_name) == normalized_executor:
                return route
        summary = self.maybe_get(route_policy_module.SUMMARY_FALLBACK_ROUTE_NAME)
        if summary is not None:
            return summary
        return next(iter(self.values()))

    def candidate_routes(
        self,
        *,
        route_name_hint: str = "",
        executor_name: str = "",
        model_hint: str = "",
        executor_family: str = "",
        execution_site: str = "",
        required_capabilities: dict[str, object] | None = None,
        task_family: str = "",
    ) -> tuple[list[RouteSpec], str]:
        if route_name_hint:
            hinted = self.maybe_get(route_name_hint)
            if hinted is not None:
                supported_hinted = _filter_supported_task_family([hinted], task_family)
                if supported_hinted:
                    return supported_hinted, "exact_route_name"

        normalized_executor = normalize_executor_name(executor_name)
        exact_executor_matches = [
            route
            for route in self.values()
            if _registered_executor_name(route.executor_name) == normalized_executor
        ]
        if exact_executor_matches:
            exact_executor_matches = _filter_supported_task_family(exact_executor_matches, task_family)
            model_matches = _filter_supported_task_family(
                _filter_model_hint_matches(exact_executor_matches, model_hint),
                task_family,
            )
            if model_matches:
                return _sort_routes_by_preference(model_matches, task_family), "exact_executor_model_hint"
            if exact_executor_matches:
                return _sort_routes_by_preference(exact_executor_matches, task_family), "exact_executor"

        family_site_matches = [
            route
            for route in self.values()
            if route.executor_family == executor_family and route.execution_site == execution_site
        ]
        if family_site_matches:
            family_site_matches = _filter_supported_task_family(family_site_matches, task_family)
            capability_matches = _filter_capability_matches(family_site_matches, required_capabilities)
            if capability_matches:
                capability_matches = _filter_supported_task_family(capability_matches, task_family)
                if capability_matches:
                    return _sort_routes_by_preference(capability_matches, task_family), "family_site"
            if not required_capabilities:
                return _sort_routes_by_preference(family_site_matches, task_family), "family_site"

        capability_matches = _filter_capability_matches(self.values(), required_capabilities)
        if capability_matches:
            capability_matches = _filter_supported_task_family(capability_matches, task_family)
            if capability_matches:
                return _sort_routes_by_preference(capability_matches, task_family), "capability"

        summary_route = self.maybe_get(route_policy_module.SUMMARY_FALLBACK_ROUTE_NAME)
        if summary_route is not None and _route_supports_task_family(summary_route, task_family):
            return [summary_route], "summary_fallback"
        supported_routes = _filter_supported_task_family(self.values(), task_family)
        if supported_routes:
            return _sort_routes_by_preference(supported_routes, task_family), "no_match"
        return list(self.values()), "no_match"


def _filter_capability_matches(
    routes: Iterable[RouteSpec],
    required_capabilities: dict[str, object] | None,
) -> list[RouteSpec]:
    requirements = required_capabilities or {}
    if not requirements:
        return []

    matches: list[RouteSpec] = []
    for route in routes:
        if _route_matches_capabilities(route, requirements):
            matches.append(route)
    return matches


def _filter_model_hint_matches(routes: Iterable[RouteSpec], model_hint: str) -> list[RouteSpec]:
    requested_hint = (model_hint or "").strip().lower()
    if not requested_hint:
        return []

    matches: list[RouteSpec] = []
    for route in routes:
        route_hint = str(route.model_hint or "").strip().lower()
        if not route_hint:
            continue
        if route_hint == requested_hint or route_hint in requested_hint or requested_hint in route_hint:
            matches.append(route)
    return matches


def _route_matches_capabilities(route: RouteSpec, requirements: dict[str, object]) -> bool:
    has_requirement = False
    for field_name in CAPABILITY_MATCH_FIELDS:
        if field_name not in requirements:
            continue
        required = requirements[field_name]
        if required in {"", None}:
            continue
        has_requirement = True
        if getattr(route.capabilities, field_name) != required:
            return False
    return has_requirement


DEFAULT_ROUTE_REGISTRY_PATH = Path(__file__).with_name("routes.default.json")
DEFAULT_ROUTE_POLICY_PATH = Path(__file__).with_name("route_policy.default.json")
_ROUTE_SELECTION_POLICY_ID = "route_selection:global"
_ROUTE_SELECTION_POLICY_KIND = "route_selection"
_ROUTE_CAPABILITY_SCORES_KEY = "_task_family_scores"


def _coerce_string(value: object, *, default: str = "") -> str:
    return str(value if value is not None else default).strip()


def _coerce_bool(value: object, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _normalize_route_name_value(raw_name: object) -> str:
    normalized = str(raw_name or "").strip()
    if not normalized:
        return ""
    if normalized.endswith("-detached"):
        base_name = normalized[: -len("-detached")]
        return f"{ROUTE_NAME_ALIASES.get(base_name, base_name)}-detached"
    return ROUTE_NAME_ALIASES.get(normalized, normalized)


def _normalize_route_mode_value(raw_mode: object) -> str:
    normalized = str(raw_mode or "").strip().lower()
    return ROUTE_MODE_ALIASES.get(normalized, "auto")


def _normalize_hint_set(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def normalize_route_policy_payload(payload: object) -> dict[str, object]:
    return route_policy_module.normalize_route_policy_payload(payload)


def load_route_policy_from_path(path: Path) -> dict[str, object]:
    return route_policy_module.load_route_policy_from_path(path)


def load_default_route_policy() -> dict[str, object]:
    return route_policy_module.load_default_route_policy()


def _apply_route_policy_payload(route_policy: dict[str, object]) -> None:
    route_policy_module._apply_route_policy_payload(route_policy)
    _sync_route_policy_exports()


def _route_capabilities_from_dict(payload: object) -> RouteCapabilities:
    if not isinstance(payload, dict):
        payload = {}
    return RouteCapabilities(
        execution_kind=_coerce_string(payload.get("execution_kind"), default="unknown"),
        supports_tool_loop=_coerce_bool(payload.get("supports_tool_loop")),
        filesystem_access=_coerce_string(payload.get("filesystem_access"), default="none"),
        network_access=_coerce_string(payload.get("network_access"), default="none"),
        deterministic=_coerce_bool(payload.get("deterministic")),
        resumable=_coerce_bool(payload.get("resumable")),
    )


def _route_taxonomy_from_dict(payload: object) -> TaxonomyProfile:
    if not isinstance(payload, dict):
        payload = {}
    return TaxonomyProfile(
        system_role=_coerce_string(payload.get("system_role"), default="general-executor"),
        memory_authority=_coerce_string(payload.get("memory_authority"), default="task-state"),
    )


def route_spec_from_dict(payload: object) -> RouteSpec:
    return route_registry_module.route_spec_from_dict(payload)


def normalize_route_registry_payload(payload: object) -> dict[str, dict[str, object]]:
    return route_registry_module.normalize_route_registry_payload(payload)


def load_route_registry_from_path(path: Path) -> dict[str, dict[str, object]]:
    return route_registry_module.load_route_registry_from_path(path)


def load_default_route_registry() -> dict[str, dict[str, object]]:
    return route_registry_module.load_default_route_registry()


def _routes_from_registry_payload(payload: dict[str, dict[str, object]]) -> tuple[RouteSpec, ...]:
    return tuple(route_spec_from_dict(route_payload) for route_payload in payload.values())


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _json_object(payload: str | None) -> dict[str, object]:
    if not payload:
        return {}
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _json_list(payload: str | None) -> list[object]:
    if not payload:
        return []
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def _route_registry_row_count(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT COUNT(*) AS count FROM route_registry").fetchone()
    return int(row["count"] or 0) if row is not None else 0


def _route_policy_row_exists(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT 1 FROM policy_records WHERE policy_id = ?",
        (_ROUTE_SELECTION_POLICY_ID,),
    ).fetchone()
    return row is not None


def _route_row_values(route_name: str, route_payload: dict[str, object]) -> tuple[object, ...]:
    route = route_spec_from_dict({**route_payload, "name": route_name})
    normalized = route.to_dict()
    capabilities = dict(normalized.get("capabilities", {}))
    capabilities[_ROUTE_CAPABILITY_SCORES_KEY] = _normalize_task_family_scores(
        normalized.get("task_family_scores", {})
    )
    timestamp = utc_now()
    actor = local_actor()
    return (
        route.name,
        route.executor_family or "unknown",
        route.model_hint,
        route.dialect_hint or None,
        route.backend_kind,
        route.transport_kind or None,
        route.fallback_route_name or None,
        route.quality_weight,
        _json_dumps(_normalize_unsupported_task_types(normalized.get("unsupported_task_types", []))),
        _json_dumps(normalized.get("cost_profile", None)),
        timestamp,
        actor,
        _json_dumps(capabilities),
        _json_dumps(normalized.get("taxonomy", {})),
        route.execution_site,
        route.executor_family,
        route.executor_name,
        1 if route.remote_capable else 0,
    )


def _replace_route_registry_in_sqlite(
    connection: sqlite3.Connection,
    route_registry: object,
) -> dict[str, dict[str, object]]:
    normalized_registry = normalize_route_registry_payload(route_registry)
    route_ids = tuple(normalized_registry)
    if route_ids:
        placeholders = ", ".join("?" for _ in route_ids)
        connection.execute(f"DELETE FROM route_registry WHERE route_id NOT IN ({placeholders})", route_ids)
    else:
        connection.execute("DELETE FROM route_registry")
    connection.executemany(
        """
        INSERT INTO route_registry (
            route_id,
            model_family,
            model_hint,
            dialect_hint,
            backend_kind,
            transport_kind,
            fallback_route_id,
            quality_weight,
            unsupported_task_types,
            cost_profile,
            updated_at,
            updated_by,
            capabilities_json,
            taxonomy_json,
            execution_site,
            executor_family,
            executor_name,
            remote_capable
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(route_id) DO UPDATE SET
            model_family = excluded.model_family,
            model_hint = excluded.model_hint,
            dialect_hint = excluded.dialect_hint,
            backend_kind = excluded.backend_kind,
            transport_kind = excluded.transport_kind,
            fallback_route_id = excluded.fallback_route_id,
            quality_weight = excluded.quality_weight,
            unsupported_task_types = excluded.unsupported_task_types,
            cost_profile = excluded.cost_profile,
            updated_at = excluded.updated_at,
            updated_by = excluded.updated_by,
            capabilities_json = excluded.capabilities_json,
            taxonomy_json = excluded.taxonomy_json,
            execution_site = excluded.execution_site,
            executor_family = excluded.executor_family,
            executor_name = excluded.executor_name,
            remote_capable = excluded.remote_capable
        """,
        [_route_row_values(route_name, route_payload) for route_name, route_payload in normalized_registry.items()],
    )
    return normalized_registry


def _load_route_registry_from_sqlite(connection: sqlite3.Connection) -> dict[str, dict[str, object]]:
    rows = connection.execute("SELECT * FROM route_registry ORDER BY route_id").fetchall()
    if not rows:
        return {}
    payload: dict[str, dict[str, object]] = {}
    for row in rows:
        capabilities = _json_object(str(row["capabilities_json"] or "{}"))
        task_family_scores = _normalize_task_family_scores(capabilities.pop(_ROUTE_CAPABILITY_SCORES_KEY, {}))
        route_payload = {
            "name": str(row["route_id"]),
            "executor_name": str(row["executor_name"]),
            "backend_kind": str(row["backend_kind"]),
            "model_hint": str(row["model_hint"]),
            "dialect_hint": str(row["dialect_hint"] or ""),
            "fallback_route_name": str(row["fallback_route_id"] or ""),
            "quality_weight": _normalize_quality_weight(row["quality_weight"]),
            "task_family_scores": task_family_scores,
            "unsupported_task_types": _normalize_unsupported_task_types(_json_list(row["unsupported_task_types"])),
            "executor_family": str(row["executor_family"]),
            "execution_site": str(row["execution_site"]),
            "remote_capable": bool(int(row["remote_capable"] or 0)),
            "transport_kind": str(row["transport_kind"] or "local_process"),
            "capabilities": capabilities,
            "taxonomy": _json_object(str(row["taxonomy_json"] or "{}")),
        }
        payload[str(row["route_id"])] = route_payload
    return normalize_route_registry_payload(payload)


def _save_route_weights_to_sqlite(connection: sqlite3.Connection, weights: dict[str, float]) -> dict[str, float]:
    normalized_weights = {
        normalize_route_name(route_name): round(_normalize_quality_weight(weight), 6)
        for route_name, weight in sorted(weights.items())
        if normalize_route_name(route_name)
    }
    connection.execute(
        "UPDATE route_registry SET quality_weight = 1.0, updated_at = ?, updated_by = ?",
        (utc_now(), local_actor()),
    )
    for route_name, weight in normalized_weights.items():
        connection.execute(
            """
            UPDATE route_registry
            SET quality_weight = ?, updated_at = ?, updated_by = ?
            WHERE route_id = ?
            """,
            (weight, utc_now(), local_actor(), route_name),
        )
    return normalized_weights


def _load_route_weights_from_sqlite(connection: sqlite3.Connection) -> dict[str, float]:
    rows = connection.execute("SELECT route_id, quality_weight FROM route_registry ORDER BY route_id").fetchall()
    return {
        str(row["route_id"]): _normalize_quality_weight(row["quality_weight"])
        for row in rows
    }


def _capabilities_json_with_scores(raw_capabilities: str | None, scores: dict[str, float]) -> str:
    capabilities = _json_object(raw_capabilities)
    capabilities[_ROUTE_CAPABILITY_SCORES_KEY] = _normalize_task_family_scores(scores)
    return _json_dumps(capabilities)


def _save_route_capability_profiles_to_sqlite(
    connection: sqlite3.Connection,
    profiles: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    normalized_profiles = {
        normalize_route_name(route_name): _normalize_route_capability_profile(profile)
        for route_name, profile in sorted(profiles.items())
        if normalize_route_name(route_name)
    }
    rows = connection.execute("SELECT route_id, capabilities_json FROM route_registry").fetchall()
    timestamp = utc_now()
    actor = local_actor()
    for row in rows:
        connection.execute(
            """
            UPDATE route_registry
            SET capabilities_json = ?, unsupported_task_types = ?, updated_at = ?, updated_by = ?
            WHERE route_id = ?
            """,
            (
                _capabilities_json_with_scores(str(row["capabilities_json"] or "{}"), {}),
                _json_dumps([]),
                timestamp,
                actor,
                str(row["route_id"]),
            ),
        )
    for route_name, profile in normalized_profiles.items():
        row = connection.execute(
            "SELECT capabilities_json FROM route_registry WHERE route_id = ?",
            (route_name,),
        ).fetchone()
        if row is None:
            continue
        connection.execute(
            """
            UPDATE route_registry
            SET capabilities_json = ?, unsupported_task_types = ?, updated_at = ?, updated_by = ?
            WHERE route_id = ?
            """,
            (
                _capabilities_json_with_scores(
                    str(row["capabilities_json"] or "{}"),
                    _normalize_task_family_scores(profile.get("task_family_scores", {})),
                ),
                _json_dumps(_normalize_unsupported_task_types(profile.get("unsupported_task_types", []))),
                utc_now(),
                local_actor(),
                route_name,
            ),
        )
    return normalized_profiles


def _load_route_capability_profiles_from_sqlite(
    connection: sqlite3.Connection,
    *,
    include_empty: bool = False,
) -> dict[str, dict[str, object]]:
    rows = connection.execute(
        "SELECT route_id, capabilities_json, unsupported_task_types FROM route_registry ORDER BY route_id"
    ).fetchall()
    profiles: dict[str, dict[str, object]] = {}
    for row in rows:
        capabilities = _json_object(str(row["capabilities_json"] or "{}"))
        profile = {
            "task_family_scores": _normalize_task_family_scores(capabilities.get(_ROUTE_CAPABILITY_SCORES_KEY, {})),
            "unsupported_task_types": _normalize_unsupported_task_types(_json_list(row["unsupported_task_types"])),
        }
        if include_empty or profile["task_family_scores"] or profile["unsupported_task_types"]:
            profiles[str(row["route_id"])] = profile
    return profiles


def _save_route_selection_policy_to_sqlite(
    connection: sqlite3.Connection,
    route_policy: object,
) -> dict[str, object]:
    normalized_policy = normalize_route_policy_payload(route_policy)
    connection.execute(
        """
        INSERT INTO policy_records (
            policy_id, kind, scope, scope_value, payload, updated_at, updated_by
        )
        VALUES (?, ?, ?, NULL, ?, ?, ?)
        ON CONFLICT(policy_id) DO UPDATE SET
            kind = excluded.kind,
            scope = excluded.scope,
            scope_value = excluded.scope_value,
            payload = excluded.payload,
            updated_at = excluded.updated_at,
            updated_by = excluded.updated_by
        """,
        (
            _ROUTE_SELECTION_POLICY_ID,
            _ROUTE_SELECTION_POLICY_KIND,
            "global",
            _json_dumps(normalized_policy),
            utc_now(),
            local_actor(),
        ),
    )
    return normalized_policy


def _load_route_policy_from_sqlite(connection: sqlite3.Connection) -> dict[str, object]:
    row = connection.execute(
        "SELECT payload FROM policy_records WHERE policy_id = ?",
        (_ROUTE_SELECTION_POLICY_ID,),
    ).fetchone()
    if row is None:
        return {}
    try:
        return normalize_route_policy_payload(json.loads(str(row["payload"])))
    except (json.JSONDecodeError, ValueError):
        return load_default_route_policy()


def _run_sqlite_write(base_dir: Path, writer) -> None:
    connection = sqlite_store.get_connection(base_dir)
    if connection.in_transaction:
        writer(connection)
        return
    connection.execute("BEGIN IMMEDIATE")
    try:
        writer(connection)
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise


def _bootstrap_route_metadata_from_legacy_json(base_dir: Path) -> None:
    connection = sqlite_store.get_connection(base_dir)
    if _route_registry_row_count(connection) > 0:
        return
    connection.execute("BEGIN IMMEDIATE")
    try:
        if _route_registry_row_count(connection) > 0:
            connection.execute("COMMIT")
            return
        registry_path = route_registry_path(base_dir)
        registry_payload = (
            load_route_registry_from_path(registry_path)
            if registry_path.exists()
            else load_default_route_registry()
        )
        _replace_route_registry_in_sqlite(connection, registry_payload)

        weights_path = route_weights_path(base_dir)
        if weights_path.exists():
            try:
                raw_weights = json.loads(weights_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw_weights = {}
            if isinstance(raw_weights, dict):
                _save_route_weights_to_sqlite(connection, raw_weights)

        capabilities_path = route_capabilities_path(base_dir)
        if capabilities_path.exists():
            try:
                raw_profiles = json.loads(capabilities_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw_profiles = {}
            if isinstance(raw_profiles, dict):
                _save_route_capability_profiles_to_sqlite(connection, raw_profiles)
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise


def _bootstrap_route_policy_from_legacy_json(base_dir: Path) -> None:
    connection = sqlite_store.get_connection(base_dir)
    if _route_policy_row_exists(connection):
        return
    connection.execute("BEGIN IMMEDIATE")
    try:
        if _route_policy_row_exists(connection):
            connection.execute("COMMIT")
            return
        policy_path = route_policy_path(base_dir)
        policy_payload = (
            load_route_policy_from_path(policy_path)
            if policy_path.exists()
            else load_default_route_policy()
        )
        _save_route_selection_policy_to_sqlite(connection, policy_payload)
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise


def route_metadata_snapshot(base_dir: Path) -> dict[str, object]:
    return route_metadata_store_module.route_metadata_snapshot(base_dir)


def _build_default_route_registry() -> RouteRegistry:
    return RouteRegistry(_routes_from_registry_payload(load_default_route_registry()))


def current_route_registry(registry: RouteRegistry | None = None) -> dict[str, dict[str, object]]:
    active_registry = registry or ROUTE_REGISTRY
    return {route.name: route.to_dict() for route in active_registry.values()}


ROUTE_REGISTRY = _build_default_route_registry()
RouteRegistry = route_registry_module.RouteRegistry
ROUTE_REGISTRY = route_registry_module.ROUTE_REGISTRY
_apply_route_policy_payload(load_default_route_policy())
_BUILTIN_ROUTE_FALLBACKS = {route.name: route.fallback_route_name for route in ROUTE_REGISTRY.values()}


def build_detached_route(route: RouteSpec) -> RouteSpec:
    return route_selection_module.build_detached_route(route)


def normalize_route_mode(raw_mode: str | None) -> str:
    return _normalize_route_mode_value(raw_mode)


def normalize_route_name(raw_name: str | None) -> str:
    return _normalize_route_name_value(raw_name)


def load_route_registry(base_dir: Path) -> dict[str, dict[str, object]]:
    return route_metadata_store_module.load_route_registry(base_dir)


def load_route_policy(base_dir: Path) -> dict[str, object]:
    return route_metadata_store_module.load_route_policy(base_dir)


def save_route_registry(base_dir: Path, route_registry: object) -> Path:
    return route_metadata_store_module.save_route_registry(base_dir, route_registry)


def save_route_policy(base_dir: Path, route_policy: object) -> Path:
    return route_metadata_store_module.save_route_policy(base_dir, route_policy)


def apply_route_registry(base_dir: Path, registry: RouteRegistry | None = None) -> dict[str, dict[str, object]]:
    global _BUILTIN_ROUTE_FALLBACKS

    active_registry = registry or ROUTE_REGISTRY
    route_registry = load_route_registry(base_dir)
    active_registry.replace(_routes_from_registry_payload(route_registry))
    if active_registry is ROUTE_REGISTRY:
        _BUILTIN_ROUTE_FALLBACKS = {route.name: route.fallback_route_name for route in active_registry.values()}
    return current_route_registry(active_registry)


def apply_route_policy(base_dir: Path) -> dict[str, object]:
    applied = route_policy_module.apply_route_policy(base_dir)
    _sync_route_policy_exports()
    return applied


def current_route_policy() -> dict[str, object]:
    return route_policy_module.current_route_policy()


def load_route_weights(base_dir: Path) -> dict[str, float]:
    return route_metadata_store_module.load_route_weights(base_dir)


def save_route_weights(base_dir: Path, weights: dict[str, float]) -> Path:
    return route_metadata_store_module.save_route_weights(base_dir, weights)


def apply_route_weights(base_dir: Path, registry: RouteRegistry | None = None) -> dict[str, float]:
    active_registry = registry or ROUTE_REGISTRY
    persisted_weights = load_route_weights(base_dir)
    for route in active_registry.values():
        route.quality_weight = persisted_weights.get(route.name, 1.0)
    return {route.name: route.quality_weight for route in active_registry.values()}


def current_route_weights(registry: RouteRegistry | None = None) -> dict[str, float]:
    active_registry = registry or ROUTE_REGISTRY
    return {route.name: route.quality_weight for route in active_registry.values()}


def load_route_capability_profiles(base_dir: Path) -> dict[str, dict[str, object]]:
    return route_metadata_store_module.load_route_capability_profiles(base_dir)


def save_route_capability_profiles(base_dir: Path, profiles: dict[str, dict[str, object]]) -> Path:
    return route_metadata_store_module.save_route_capability_profiles(base_dir, profiles)


def apply_route_capability_profiles(base_dir: Path, registry: RouteRegistry | None = None) -> dict[str, dict[str, object]]:
    active_registry = registry or ROUTE_REGISTRY
    persisted_profiles = load_route_capability_profiles(base_dir)
    for route in active_registry.values():
        profile = persisted_profiles.get(route.name, {})
        route.task_family_scores = _normalize_task_family_scores(profile.get("task_family_scores", {}))
        route.unsupported_task_types = _normalize_unsupported_task_types(profile.get("unsupported_task_types", []))
    return current_route_capability_profiles(active_registry)


def current_route_capability_profiles(registry: RouteRegistry | None = None) -> dict[str, dict[str, object]]:
    active_registry = registry or ROUTE_REGISTRY
    return {
        route.name: {
            "task_family_scores": _normalize_task_family_scores(route.task_family_scores),
            "unsupported_task_types": _normalize_unsupported_task_types(route.unsupported_task_types),
        }
        for route in active_registry.values()
    }


def load_route_fallbacks(base_dir: Path) -> dict[str, str]:
    path = route_fallbacks_path(base_dir)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}

    fallbacks: dict[str, str] = {}
    for route_name, raw_fallback in payload.items():
        normalized_name = normalize_route_name(route_name)
        if not normalized_name:
            continue
        fallback_name = normalize_route_name(str(raw_fallback or ""))
        fallbacks[normalized_name] = fallback_name
    return fallbacks


def apply_route_fallbacks(base_dir: Path, registry: RouteRegistry | None = None) -> dict[str, str]:
    active_registry = registry or ROUTE_REGISTRY
    persisted_fallbacks = load_route_fallbacks(base_dir)
    known_routes = {route.name for route in active_registry.values()}
    baseline = (
        _BUILTIN_ROUTE_FALLBACKS
        if active_registry is ROUTE_REGISTRY
        else {route.name: route.fallback_route_name for route in active_registry.values()}
    )

    for route in active_registry.values():
        fallback_name = baseline.get(route.name, "")
        if route.name in persisted_fallbacks:
            configured_fallback = persisted_fallbacks[route.name]
            if not configured_fallback or configured_fallback in known_routes:
                fallback_name = configured_fallback
        route.fallback_route_name = fallback_name
    return {route.name: route.fallback_route_name for route in active_registry.values()}


def route_for_executor(executor_name: str) -> RouteSpec:
    return route_selection_module.route_for_executor(executor_name, registry=ROUTE_REGISTRY)


def route_for_mode(route_mode: str) -> RouteSpec | None:
    return route_selection_module.route_for_mode(route_mode, registry=ROUTE_REGISTRY)


def route_by_name(route_name: str) -> RouteSpec | None:
    return route_selection_module.route_by_name(route_name, registry=ROUTE_REGISTRY)


def lookup_route_by_name(route_name: str) -> RouteSpec | None:
    """Return static route metadata by name without performing route selection."""

    return route_selection_module.lookup_route_by_name(route_name, registry=ROUTE_REGISTRY)


def fallback_route_for(route_name: str) -> RouteSpec | None:
    return route_selection_module.fallback_route_for(route_name, registry=ROUTE_REGISTRY)


def resolve_fallback_chain(primary_route_name: str) -> tuple[str, ...]:
    """Return the static fallback route-name chain for a primary route."""

    return route_selection_module.resolve_fallback_chain(primary_route_name, registry=ROUTE_REGISTRY)


def _reason_with_strategy_match(base_reason: str, match_kind: str) -> str:
    return route_selection_module._reason_with_strategy_match(base_reason, match_kind)


def _resolve_complexity_hint(state: TaskState) -> str:
    return route_selection_module._resolve_complexity_hint(state)


def _apply_complexity_bias(candidates: list[RouteSpec], complexity_hint: str) -> list[RouteSpec]:
    return route_selection_module._apply_complexity_bias(candidates, complexity_hint)


def select_route(
    state: TaskState,
    executor_override: str | None = None,
    route_mode_override: str | None = None,
) -> RouteSelection:
    return route_selection_module.select_route(
        state,
        executor_override=executor_override,
        route_mode_override=route_mode_override,
        registry=ROUTE_REGISTRY,
    )
