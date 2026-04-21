from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from urllib import error
from unittest.mock import MagicMock, patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.doctor import diagnose_local_stack, diagnose_sqlite_store, format_sqlite_doctor_result
from swallow.models import Event, TaskState
from swallow.store import append_event, save_state


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


class SqliteDoctorTest(unittest.TestCase):
    def test_diagnose_sqlite_store_reports_file_only_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": "file"}, clear=False):
                save_state(
                    base_dir,
                    TaskState(
                        task_id="legacy-task",
                        title="Legacy task",
                        goal="Retain file-only compatibility",
                        workspace_root=str(base_dir),
                        executor_name="local",
                    ),
                )
                append_event(
                    base_dir,
                    Event(
                        task_id="legacy-task",
                        event_type="task.created",
                        message="legacy",
                        payload={"status": "created"},
                    ),
                )

            exit_code, result = diagnose_sqlite_store(base_dir)
            formatted = format_sqlite_doctor_result(result)

        self.assertEqual(exit_code, 0)
        self.assertEqual(result.backend, "sqlite")
        self.assertFalse(result.db_exists)
        self.assertEqual(result.file_task_count, 1)
        self.assertEqual(result.file_only_task_count, 1)
        self.assertTrue(result.migration_recommended)
        self.assertIn("migration_recommended=yes", formatted)

    def test_diagnose_sqlite_store_reports_healthy_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": ""}, clear=False):
                save_state(
                    base_dir,
                    TaskState(
                        task_id="sqlite-task",
                        title="SQLite task",
                        goal="Persist state in SQLite",
                        workspace_root=str(base_dir),
                        executor_name="local",
                    ),
                )
                append_event(
                    base_dir,
                    Event(
                        task_id="sqlite-task",
                        event_type="task.created",
                        message="sqlite",
                        payload={"status": "created"},
                    ),
                )

            exit_code, result = diagnose_sqlite_store(base_dir)

        self.assertEqual(exit_code, 0)
        self.assertTrue(result.db_exists)
        self.assertTrue(result.schema_ok)
        self.assertTrue(result.integrity_ok)
        self.assertEqual(result.task_count, 1)
        self.assertEqual(result.event_count, 1)
        self.assertEqual(result.file_task_count, 1)
        self.assertEqual(result.file_only_task_count, 0)
        self.assertFalse(result.migration_recommended)

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
