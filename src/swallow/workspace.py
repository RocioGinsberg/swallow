from __future__ import annotations

import os
from pathlib import Path


def _workspace_base(base: Path | None = None) -> Path:
    if base is not None:
        return Path(base).resolve()
    swl_root = os.environ.get("SWL_ROOT", "").strip()
    if swl_root:
        return Path(swl_root).resolve()
    return Path.cwd().resolve()


def resolve_path(path: Path | str, *, base: Path | None = None) -> Path:
    target = Path(path)
    if target.is_absolute():
        return target.resolve()
    return (_workspace_base(base) / target).resolve()
