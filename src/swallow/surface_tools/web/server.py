from __future__ import annotations

from pathlib import Path

from .api import create_fastapi_app


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def validate_loopback_host(host: str) -> str:
    normalized = host.strip()
    if normalized not in LOOPBACK_HOSTS:
        allowed = ", ".join(sorted(LOOPBACK_HOSTS))
        raise RuntimeError(f"Unauthenticated Web write surface refuses non-loopback host: {host}. Use one of: {allowed}.")
    return normalized


def serve_control_center(base_dir: Path, host: str = "127.0.0.1", port: int = 8037) -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Uvicorn is required for `swl serve`. Install `fastapi` and `uvicorn` to use the control center."
        ) from exc

    app = create_fastapi_app(base_dir)
    uvicorn.run(app, host=validate_loopback_host(host), port=port)
