from __future__ import annotations

from pathlib import Path

from .api import create_fastapi_app


def serve_control_center(base_dir: Path, host: str = "127.0.0.1", port: int = 8037) -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Uvicorn is required for `swl serve`. Install `fastapi` and `uvicorn` to use the control center."
        ) from exc

    app = create_fastapi_app(base_dir)
    uvicorn.run(app, host=host, port=port)
