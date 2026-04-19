from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from urllib import error
from unittest.mock import MagicMock, patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.doctor import diagnose_local_stack


def _completed(args: list[str], returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr=stderr)


class LocalStackDoctorTest(unittest.TestCase):
    def test_diagnose_local_stack_marks_required_checks_pass(self) -> None:
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        response.__exit__.return_value = None

        runs = [
            _completed(["docker", "info"], stdout="Server Version: 26.0"),
            _completed(["docker", "ps"], stdout="new-api|Up 10 minutes\n"),
            _completed(["docker", "ps"], stdout="tensorzero|Up 10 minutes\n"),
            _completed(["docker", "ps"], stdout="postgres|Up 10 minutes\n"),
            _completed(["docker", "ps"], stdout="postgres|Up 10 minutes\n"),
            _completed(["docker", "exec"], stdout="vector\n"),
            _completed(["ping"], stdout="1 packets transmitted, 1 received"),
            _completed(["curl"], stdout="203.0.113.5"),
        ]

        with patch("swallow.doctor.subprocess.run", side_effect=runs):
            with patch("swallow.doctor.request.urlopen", return_value=response):
                exit_code, result = diagnose_local_stack()

        statuses = {check.name: check.status for check in result.checks}
        self.assertEqual(exit_code, 0)
        self.assertEqual(statuses["docker_daemon"], "pass")
        self.assertEqual(statuses["new_api_container"], "pass")
        self.assertEqual(statuses["tensorzero_container"], "pass")
        self.assertEqual(statuses["postgres_container"], "pass")
        self.assertEqual(statuses["pgvector_extension"], "pass")
        self.assertEqual(statuses["new_api_http"], "pass")
        self.assertEqual(statuses["new_api_endpoint"], "pass")
        self.assertEqual(statuses["wireguard_tunnel"], "pass")
        self.assertEqual(statuses["egress_proxy"], "pass")

    def test_diagnose_local_stack_treats_tensorzero_as_optional(self) -> None:
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        response.__exit__.return_value = None

        runs = [
            _completed(["docker", "info"], stdout="Server Version: 26.0"),
            _completed(["docker", "ps"], stdout="new-api|Up 10 minutes\n"),
            _completed(["docker", "ps"], stdout=""),
            _completed(["docker", "ps"], stdout="postgres|Up 10 minutes\n"),
            _completed(["docker", "ps"], stdout="postgres|Up 10 minutes\n"),
            _completed(["docker", "exec"], stdout="vector\n"),
            _completed(["ping"], stdout="1 packets transmitted, 1 received"),
            _completed(["curl"], stdout="203.0.113.5"),
        ]

        with patch("swallow.doctor.subprocess.run", side_effect=runs):
            with patch("swallow.doctor.request.urlopen", return_value=response):
                exit_code, result = diagnose_local_stack()

        statuses = {check.name: check.status for check in result.checks}
        self.assertEqual(exit_code, 0)
        self.assertEqual(statuses["tensorzero_container"], "skip")
        self.assertEqual(statuses["postgres_container"], "pass")
        self.assertEqual(statuses["new_api_endpoint"], "pass")

    def test_diagnose_local_stack_treats_auth_required_new_api_endpoint_as_reachable(self) -> None:
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        response.__exit__.return_value = None
        auth_required = error.HTTPError(
            url="http://localhost:3000/v1/models",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )

        runs = [
            _completed(["docker", "info"], stdout="Server Version: 26.0"),
            _completed(["docker", "ps"], stdout="new-api|Up 10 minutes\n"),
            _completed(["docker", "ps"], stdout=""),
            _completed(["docker", "ps"], stdout="postgres|Up 10 minutes\n"),
            _completed(["docker", "ps"], stdout="postgres|Up 10 minutes\n"),
            _completed(["docker", "exec"], stdout="vector\n"),
            _completed(["ping"], stdout="1 packets transmitted, 1 received"),
            _completed(["curl"], stdout="203.0.113.5"),
        ]

        with patch("swallow.doctor.subprocess.run", side_effect=runs):
            with patch("swallow.doctor.request.urlopen", side_effect=[response, auth_required]):
                exit_code, result = diagnose_local_stack()

        statuses = {check.name: check.status for check in result.checks}
        self.assertEqual(exit_code, 0)
        self.assertEqual(statuses["new_api_http"], "pass")
        self.assertEqual(statuses["new_api_endpoint"], "pass")


if __name__ == "__main__":
    unittest.main()
