from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from swallow.orchestration.models import utc_now
from swallow.surface_tools.identity import local_actor
from swallow.surface_tools.paths import route_policy_path
from swallow.truth_governance import sqlite_store


DEFAULT_ROUTE_POLICY_PATH = Path(__file__).with_name("route_policy.default.json")
_ROUTE_SELECTION_POLICY_ID = "route_selection:global"
_ROUTE_SELECTION_POLICY_KIND = "route_selection"

ROUTE_MODE_ALIASES = {
    "": "auto",
    "auto": "auto",
    "live": "live",
    "http": "http",
    "deterministic": "deterministic",
    "detached": "detached",
    "offline": "offline",
    "summary": "summary",
}

ROUTE_NAME_ALIASES: dict[str, str] = {}
ROUTE_MODE_TO_ROUTE_NAME: dict[str, str] = {}
ROUTE_COMPLEXITY_BIAS_ROUTES: dict[str, str] = {}
ROUTE_STRATEGY_COMPLEXITY_HINTS: set[str] = set()
ROUTE_PARALLEL_INTENT_HINTS: set[str] = set()
SUMMARY_FALLBACK_ROUTE_NAME = ""


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
    if not isinstance(payload, dict):
        raise ValueError("Route policy metadata must be a JSON object.")

    raw_mode_routes = payload.get("route_mode_routes", {})
    if not isinstance(raw_mode_routes, dict):
        raise ValueError("route_mode_routes must be a JSON object.")
    route_mode_routes: dict[str, str] = {}
    for raw_mode, raw_route_name in raw_mode_routes.items():
        mode = _normalize_route_mode_value(raw_mode)
        route_name = _normalize_route_name_value(raw_route_name)
        if mode in {"", "auto", "detached"} or not route_name:
            continue
        route_mode_routes[mode] = route_name

    raw_complexity_routes = payload.get("complexity_bias_routes", {})
    if not isinstance(raw_complexity_routes, dict):
        raise ValueError("complexity_bias_routes must be a JSON object.")
    complexity_bias_routes = {
        str(raw_hint).strip().lower(): _normalize_route_name_value(raw_route_name)
        for raw_hint, raw_route_name in raw_complexity_routes.items()
        if str(raw_hint).strip() and _normalize_route_name_value(raw_route_name)
    }

    strategy_hints = _normalize_hint_set(payload.get("strategy_complexity_hints", []))
    parallel_hints = _normalize_hint_set(payload.get("parallel_intent_hints", []))
    summary_fallback = _normalize_route_name_value(payload.get("summary_fallback_route_name"))

    return {
        "route_mode_routes": dict(sorted(route_mode_routes.items())),
        "complexity_bias_routes": dict(sorted(complexity_bias_routes.items())),
        "strategy_complexity_hints": sorted(strategy_hints),
        "parallel_intent_hints": sorted(parallel_hints),
        "summary_fallback_route_name": summary_fallback,
    }


def load_route_policy_from_path(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return normalize_route_policy_payload(payload)


def load_default_route_policy() -> dict[str, object]:
    return load_route_policy_from_path(DEFAULT_ROUTE_POLICY_PATH)


def _apply_route_policy_payload(route_policy: dict[str, object]) -> None:
    global SUMMARY_FALLBACK_ROUTE_NAME

    normalized = normalize_route_policy_payload(route_policy)
    route_mode_routes = normalized.get("route_mode_routes", {})
    complexity_bias_routes = normalized.get("complexity_bias_routes", {})

    ROUTE_MODE_TO_ROUTE_NAME.clear()
    if isinstance(route_mode_routes, dict):
        ROUTE_MODE_TO_ROUTE_NAME.update(route_mode_routes)

    ROUTE_COMPLEXITY_BIAS_ROUTES.clear()
    if isinstance(complexity_bias_routes, dict):
        ROUTE_COMPLEXITY_BIAS_ROUTES.update(complexity_bias_routes)

    ROUTE_STRATEGY_COMPLEXITY_HINTS.clear()
    ROUTE_STRATEGY_COMPLEXITY_HINTS.update(normalized.get("strategy_complexity_hints", []))

    ROUTE_PARALLEL_INTENT_HINTS.clear()
    ROUTE_PARALLEL_INTENT_HINTS.update(normalized.get("parallel_intent_hints", []))

    SUMMARY_FALLBACK_ROUTE_NAME = str(normalized.get("summary_fallback_route_name", "") or "")


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
            json.dumps(normalized_policy, sort_keys=True, separators=(",", ":")),
            utc_now(),
            local_actor(),
        ),
    )
    return normalized_policy


def _route_policy_row_exists(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT 1 FROM policy_records WHERE policy_id = ?",
        (_ROUTE_SELECTION_POLICY_ID,),
    ).fetchone()
    return row is not None


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


def load_route_policy(base_dir: Path) -> dict[str, object]:
    _bootstrap_route_policy_from_legacy_json(base_dir)
    connection = sqlite_store.get_connection(base_dir)
    route_policy = _load_route_policy_from_sqlite(connection)
    if route_policy:
        return route_policy
    path = route_policy_path(base_dir)
    if path.exists():
        return load_route_policy_from_path(path)
    return load_default_route_policy()


def save_route_policy(base_dir: Path, route_policy: object) -> Path:
    path = route_policy_path(base_dir)
    _run_sqlite_write(base_dir, lambda connection: _save_route_selection_policy_to_sqlite(connection, route_policy))
    return path


def apply_route_policy(base_dir: Path) -> dict[str, object]:
    route_policy = load_route_policy(base_dir)
    _apply_route_policy_payload(route_policy)
    return current_route_policy()


def current_route_policy() -> dict[str, object]:
    return {
        "route_mode_routes": dict(sorted(ROUTE_MODE_TO_ROUTE_NAME.items())),
        "complexity_bias_routes": dict(sorted(ROUTE_COMPLEXITY_BIAS_ROUTES.items())),
        "strategy_complexity_hints": sorted(ROUTE_STRATEGY_COMPLEXITY_HINTS),
        "parallel_intent_hints": sorted(ROUTE_PARALLEL_INTENT_HINTS),
        "summary_fallback_route_name": SUMMARY_FALLBACK_ROUTE_NAME,
    }


def build_route_policy_report(base_dir: Path) -> str:
    route_policy = current_route_policy()
    lines = [
        "# Route Policy",
        "",
        f"- path: {route_policy_path(base_dir)}",
        f"- default_path: {DEFAULT_ROUTE_POLICY_PATH}",
        f"- summary_fallback_route_name: {route_policy['summary_fallback_route_name']}",
        "",
        "## Route Modes",
    ]
    route_mode_routes = route_policy["route_mode_routes"]
    if isinstance(route_mode_routes, dict) and route_mode_routes:
        for mode, route_name in sorted(route_mode_routes.items()):
            lines.append(f"- {mode}: {route_name}")
    else:
        lines.append("- none")
    lines.extend(["", "## Complexity Bias"])
    complexity_bias_routes = route_policy["complexity_bias_routes"]
    if isinstance(complexity_bias_routes, dict) and complexity_bias_routes:
        for hint, route_name in sorted(complexity_bias_routes.items()):
            lines.append(f"- {hint}: {route_name}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Strategy Complexity Hints",
            ", ".join(route_policy["strategy_complexity_hints"]) or "none",
            "",
            "## Parallel Intent Hints",
            ", ".join(route_policy["parallel_intent_hints"]) or "none",
        ]
    )
    return "\n".join(lines) + "\n"
