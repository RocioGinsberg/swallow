from __future__ import annotations

from pathlib import Path

from ..router import (
    apply_route_capability_profiles,
    apply_route_weights,
    save_route_capability_profiles,
    save_route_weights,
)


class RouteRepo:
    def _apply_metadata_change(
        self,
        *,
        base_dir: Path,
        route_weights: dict[str, float] | None = None,
        route_capability_profiles: dict[str, dict[str, object]] | None = None,
    ) -> tuple[str, ...]:
        applied_writes: list[str] = []
        if route_weights is not None:
            save_route_weights(base_dir, route_weights)
            apply_route_weights(base_dir)
            applied_writes.append("route_weights")

        if route_capability_profiles is not None:
            save_route_capability_profiles(base_dir, route_capability_profiles)
            apply_route_capability_profiles(base_dir)
            applied_writes.append("route_capability_profiles")

        return tuple(applied_writes)
