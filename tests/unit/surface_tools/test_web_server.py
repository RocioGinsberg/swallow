from __future__ import annotations

import pytest

from swallow.surface_tools.web.server import validate_loopback_host


def test_validate_loopback_host_accepts_loopback_aliases() -> None:
    assert validate_loopback_host("127.0.0.1") == "127.0.0.1"
    assert validate_loopback_host("localhost") == "localhost"
    assert validate_loopback_host("::1") == "::1"


def test_validate_loopback_host_rejects_lan_binding() -> None:
    with pytest.raises(RuntimeError, match="refuses non-loopback host"):
        validate_loopback_host("0.0.0.0")
