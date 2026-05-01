from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from swallow.orchestration.models import utc_now
from swallow.provider_router import route_policy as route_policy_module
from swallow.provider_router import route_registry as route_registry_module
from swallow.surface_tools.identity import local_actor
from swallow.surface_tools.paths import route_capabilities_path, route_policy_path, route_registry_path, route_weights_path
from swallow.truth_governance import sqlite_store


DEFAULT_ROUTE_REGISTRY_PATH = route_registry_module.DEFAULT_ROUTE_REGISTRY_PATH
DEFAULT_ROUTE_POLICY_PATH = route_policy_module.DEFAULT_ROUTE_POLICY_PATH
_ROUTE_SELECTION_POLICY_ID = "route_selection:global"
_ROUTE_SELECTION_POLICY_KIND = "route_selection"
_ROUTE_CAPABILITY_SCORES_KEY = "_task_family_scores"


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
    route = route_registry_module.route_spec_from_dict({**route_payload, "name": route_name})
    normalized = route.to_dict()
    capabilities = dict(normalized.get("capabilities", {}))
    capabilities[_ROUTE_CAPABILITY_SCORES_KEY] = route_registry_module._normalize_task_family_scores(
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
        _json_dumps(route_registry_module._normalize_unsupported_task_types(normalized.get("unsupported_task_types", []))),
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
    normalized_registry = route_registry_module.normalize_route_registry_payload(route_registry)
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
        task_family_scores = route_registry_module._normalize_task_family_scores(capabilities.pop(_ROUTE_CAPABILITY_SCORES_KEY, {}))
        route_payload = {
            "name": str(row["route_id"]),
            "executor_name": str(row["executor_name"]),
            "backend_kind": str(row["backend_kind"]),
            "model_hint": str(row["model_hint"]),
            "dialect_hint": str(row["dialect_hint"] or ""),
            "fallback_route_name": str(row["fallback_route_id"] or ""),
            "quality_weight": route_registry_module._normalize_quality_weight(row["quality_weight"]),
            "task_family_scores": task_family_scores,
            "unsupported_task_types": route_registry_module._normalize_unsupported_task_types(_json_list(row["unsupported_task_types"])),
            "executor_family": str(row["executor_family"]),
            "execution_site": str(row["execution_site"]),
            "remote_capable": bool(int(row["remote_capable"] or 0)),
            "transport_kind": str(row["transport_kind"] or "local_process"),
            "capabilities": capabilities,
            "taxonomy": _json_object(str(row["taxonomy_json"] or "{}")),
        }
        payload[str(row["route_id"])] = route_payload
    return route_registry_module.normalize_route_registry_payload(payload)


def _save_route_weights_to_sqlite(connection: sqlite3.Connection, weights: dict[str, float]) -> dict[str, float]:
    normalized_weights = {
        route_policy_module._normalize_route_name_value(route_name): round(route_registry_module._normalize_quality_weight(weight), 6)
        for route_name, weight in sorted(weights.items())
        if route_policy_module._normalize_route_name_value(route_name)
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
        str(row["route_id"]): route_registry_module._normalize_quality_weight(row["quality_weight"])
        for row in rows
    }


def _capabilities_json_with_scores(raw_capabilities: str | None, scores: dict[str, float]) -> str:
    capabilities = _json_object(raw_capabilities)
    capabilities[_ROUTE_CAPABILITY_SCORES_KEY] = route_registry_module._normalize_task_family_scores(scores)
    return _json_dumps(capabilities)


def _save_route_capability_profiles_to_sqlite(
    connection: sqlite3.Connection,
    profiles: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    normalized_profiles = {
        route_policy_module._normalize_route_name_value(route_name): route_registry_module._normalize_route_capability_profile(profile)
        for route_name, profile in sorted(profiles.items())
        if route_policy_module._normalize_route_name_value(route_name)
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
                    route_registry_module._normalize_task_family_scores(profile.get("task_family_scores", {})),
                ),
                _json_dumps(route_registry_module._normalize_unsupported_task_types(profile.get("unsupported_task_types", []))),
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
            "task_family_scores": route_registry_module._normalize_task_family_scores(capabilities.get(_ROUTE_CAPABILITY_SCORES_KEY, {})),
            "unsupported_task_types": route_registry_module._normalize_unsupported_task_types(_json_list(row["unsupported_task_types"])),
        }
        if include_empty or profile["task_family_scores"] or profile["unsupported_task_types"]:
            profiles[str(row["route_id"])] = profile
    return profiles


def _save_route_selection_policy_to_sqlite(
    connection: sqlite3.Connection,
    route_policy: object,
) -> dict[str, object]:
    normalized_policy = route_policy_module.normalize_route_policy_payload(route_policy)
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
        return route_policy_module.normalize_route_policy_payload(json.loads(str(row["payload"])))
    except (json.JSONDecodeError, ValueError):
        return route_policy_module.load_default_route_policy()


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
            route_registry_module.load_route_registry_from_path(registry_path)
            if registry_path.exists()
            else route_registry_module.load_default_route_registry()
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
            route_policy_module.load_route_policy_from_path(policy_path)
            if policy_path.exists()
            else route_policy_module.load_default_route_policy()
        )
        _save_route_selection_policy_to_sqlite(connection, policy_payload)
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise


def load_route_registry(base_dir: Path) -> dict[str, dict[str, object]]:
    _bootstrap_route_metadata_from_legacy_json(base_dir)
    connection = sqlite_store.get_connection(base_dir)
    route_registry = _load_route_registry_from_sqlite(connection)
    if route_registry:
        return route_registry
    path = route_registry_path(base_dir)
    if path.exists():
        return route_registry_module.load_route_registry_from_path(path)
    return route_registry_module.load_default_route_registry()


def save_route_registry(base_dir: Path, route_registry: object) -> Path:
    path = route_registry_path(base_dir)
    _run_sqlite_write(base_dir, lambda connection: _replace_route_registry_in_sqlite(connection, route_registry))
    return path


def load_route_policy(base_dir: Path) -> dict[str, object]:
    _bootstrap_route_policy_from_legacy_json(base_dir)
    connection = sqlite_store.get_connection(base_dir)
    route_policy = _load_route_policy_from_sqlite(connection)
    if route_policy:
        return route_policy
    path = route_policy_path(base_dir)
    if path.exists():
        return route_policy_module.load_route_policy_from_path(path)
    return route_policy_module.load_default_route_policy()


def persist_route_policy(base_dir: Path, route_policy: object) -> Path:
    path = route_policy_path(base_dir)
    _run_sqlite_write(base_dir, lambda connection: _save_route_selection_policy_to_sqlite(connection, route_policy))
    return path


def save_route_policy(base_dir: Path, route_policy: object) -> Path:
    return persist_route_policy(base_dir, route_policy)


def load_route_weights(base_dir: Path) -> dict[str, float]:
    _bootstrap_route_metadata_from_legacy_json(base_dir)
    connection = sqlite_store.get_connection(base_dir)
    return _load_route_weights_from_sqlite(connection)


def save_route_weights(base_dir: Path, weights: dict[str, float]) -> Path:
    path = route_weights_path(base_dir)
    _bootstrap_route_metadata_from_legacy_json(base_dir)
    _run_sqlite_write(base_dir, lambda connection: _save_route_weights_to_sqlite(connection, weights))
    return path


def load_route_capability_profiles(base_dir: Path) -> dict[str, dict[str, object]]:
    _bootstrap_route_metadata_from_legacy_json(base_dir)
    connection = sqlite_store.get_connection(base_dir)
    return _load_route_capability_profiles_from_sqlite(connection, include_empty=False)


def save_route_capability_profiles(base_dir: Path, profiles: dict[str, dict[str, object]]) -> Path:
    path = route_capabilities_path(base_dir)
    _bootstrap_route_metadata_from_legacy_json(base_dir)
    _run_sqlite_write(base_dir, lambda connection: _save_route_capability_profiles_to_sqlite(connection, profiles))
    return path


def route_metadata_snapshot(base_dir: Path) -> dict[str, object]:
    connection = sqlite_store.get_connection(base_dir)
    _bootstrap_route_metadata_from_legacy_json(base_dir)
    _bootstrap_route_policy_from_legacy_json(base_dir)
    return {
        "route_registry": _load_route_registry_from_sqlite(connection),
        "route_policy": _load_route_policy_from_sqlite(connection),
        "route_weights": _load_route_weights_from_sqlite(connection),
        "route_capability_profiles": _load_route_capability_profiles_from_sqlite(connection, include_empty=False),
    }
