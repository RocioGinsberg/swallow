from __future__ import annotations

import json
from pathlib import Path

from swallow.surface_tools.paths import route_policy_path


DEFAULT_ROUTE_POLICY_PATH = Path(__file__).with_name("route_policy.default.json")

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


def load_route_policy(base_dir: Path) -> dict[str, object]:
    from swallow.provider_router import route_metadata_store as route_metadata_store_module

    return route_metadata_store_module.load_route_policy(base_dir)


def save_route_policy(base_dir: Path, route_policy: object) -> Path:
    from swallow.provider_router import route_metadata_store as route_metadata_store_module

    return route_metadata_store_module.persist_route_policy(base_dir, route_policy)


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
