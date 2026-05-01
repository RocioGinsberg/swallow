from __future__ import annotations

from pathlib import Path

from swallow.provider_router import route_metadata_store
from swallow.provider_router.router import (
    load_default_route_policy,
    load_default_route_registry,
    load_route_capability_profiles,
    load_route_policy,
    load_route_registry,
    load_route_weights,
)


def test_route_metadata_store_matches_router_facade_round_trip(tmp_path: Path) -> None:
    default_registry = load_default_route_registry()
    route_metadata_store.save_route_registry(tmp_path, default_registry)

    assert route_metadata_store.load_route_registry(tmp_path) == default_registry
    assert load_route_registry(tmp_path) == default_registry

    route_metadata_store.save_route_policy(tmp_path, load_default_route_policy())
    route_metadata_store.save_route_weights(tmp_path, {"local-codex": 0.37})
    route_metadata_store.save_route_capability_profiles(
        tmp_path,
        {
            "local-codex": {
                "task_family_scores": {"execution": 0.84},
                "unsupported_task_types": ["review"],
            }
        },
    )

    assert route_metadata_store.load_route_policy(tmp_path) == load_default_route_policy()
    assert load_route_policy(tmp_path) == load_default_route_policy()
    assert route_metadata_store.load_route_weights(tmp_path)["local-codex"] == 0.37
    assert load_route_weights(tmp_path)["local-codex"] == 0.37
    assert route_metadata_store.load_route_capability_profiles(tmp_path)["local-codex"]["task_family_scores"]["execution"] == 0.84
    assert load_route_capability_profiles(tmp_path)["local-codex"]["unsupported_task_types"] == ["review"]


def test_route_metadata_snapshot_includes_all_metadata_sections(tmp_path: Path) -> None:
    route_metadata_store.save_route_registry(tmp_path, load_default_route_registry())
    route_metadata_store.save_route_policy(tmp_path, load_default_route_policy())
    route_metadata_store.save_route_weights(tmp_path, {"local-codex": 0.41})
    route_metadata_store.save_route_capability_profiles(
        tmp_path,
        {
            "local-codex": {
                "task_family_scores": {"review": 0.9},
                "unsupported_task_types": ["planning"],
            }
        },
    )

    snapshot = route_metadata_store.route_metadata_snapshot(tmp_path)

    assert snapshot["route_registry"]["local-codex"]["model_hint"] == load_default_route_registry()["local-codex"]["model_hint"]
    assert snapshot["route_policy"] == load_default_route_policy()
    assert snapshot["route_weights"]["local-codex"] == 0.41
    assert snapshot["route_capability_profiles"]["local-codex"]["unsupported_task_types"] == ["planning"]
