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
from swallow.store import append_event, save_knowledge_objects, save_state


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

        with patch.dict("os.environ", {"SWL_API_KEY": "doctor-test-key"}, clear=False):
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
        self.assertEqual(statuses["embedding_api_endpoint"], "pass")
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
        self.assertIn("recommendation=Run `swl migrate`", formatted)
        self.assertIn("knowledge_schema_ok=no", formatted)
        self.assertIn("knowledge_migration_recommended=no", formatted)

    def test_diagnose_sqlite_store_reports_file_only_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            with patch.dict("os.environ", {"SWALLOW_STORE_BACKEND": "file"}, clear=False):
                save_knowledge_objects(
                    base_dir,
                    "legacy-knowledge-task",
                    [
                        {
                            "object_id": "knowledge-0001",
                            "text": "Legacy knowledge.",
                            "stage": "verified",
                            "evidence_status": "artifact_backed",
                            "artifact_ref": ".swl/tasks/legacy-knowledge-task/artifacts/evidence.md",
                        }
                    ],
                )

            exit_code, result = diagnose_sqlite_store(base_dir)
            formatted = format_sqlite_doctor_result(result)

        self.assertEqual(exit_code, 0)
        self.assertEqual(result.file_knowledge_task_count, 1)
        self.assertEqual(result.file_only_knowledge_task_count, 1)
        self.assertTrue(result.knowledge_migration_recommended)
        self.assertIn("file_knowledge_task_count=1", formatted)
        self.assertIn("knowledge_migration_recommended=yes", formatted)
        self.assertIn("knowledge_recommendation=Run `swl knowledge migrate`", formatted)

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
                save_knowledge_objects(
                    base_dir,
                    "sqlite-task",
                    [
                        {
                            "object_id": "knowledge-0001",
                            "text": "SQLite knowledge.",
                            "stage": "verified",
                            "evidence_status": "artifact_backed",
                            "artifact_ref": ".swl/tasks/sqlite-task/artifacts/evidence.md",
                        }
                    ],
                )

            exit_code, result = diagnose_sqlite_store(base_dir)

        self.assertEqual(exit_code, 0)
        self.assertTrue(result.db_exists)
        self.assertTrue(result.schema_ok)
        self.assertTrue(result.knowledge_schema_ok)
        self.assertTrue(result.integrity_ok)
        self.assertEqual(result.task_count, 1)
        self.assertEqual(result.event_count, 1)
        self.assertEqual(result.knowledge_evidence_count, 1)
        self.assertEqual(result.knowledge_wiki_count, 0)
        self.assertEqual(result.file_task_count, 1)
        self.assertEqual(result.file_only_task_count, 0)
        self.assertEqual(result.file_knowledge_task_count, 1)
        self.assertEqual(result.file_only_knowledge_task_count, 0)
        self.assertFalse(result.migration_recommended)
        self.assertFalse(result.knowledge_migration_recommended)

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

        with patch.dict("os.environ", {"SWL_API_KEY": "doctor-test-key"}, clear=False):
            with patch("swallow.doctor.subprocess.run", side_effect=runs):
                with patch("swallow.doctor.request.urlopen", return_value=response):
                    exit_code, result = diagnose_local_stack()

        statuses = {check.name: check.status for check in result.checks}
        self.assertEqual(exit_code, 0)
        self.assertEqual(statuses["tensorzero_container"], "skip")
        self.assertEqual(statuses["postgres_container"], "pass")
        self.assertEqual(statuses["new_api_endpoint"], "pass")
        self.assertEqual(statuses["embedding_api_endpoint"], "pass")

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

        with patch.dict("os.environ", {"SWL_API_KEY": "doctor-test-key"}, clear=False):
            with patch("swallow.doctor.subprocess.run", side_effect=runs):
                with patch("swallow.doctor.request.urlopen", side_effect=[response, auth_required, response]):
                    exit_code, result = diagnose_local_stack()

        statuses = {check.name: check.status for check in result.checks}
        self.assertEqual(exit_code, 0)
        self.assertEqual(statuses["new_api_http"], "pass")
        self.assertEqual(statuses["new_api_endpoint"], "pass")
        self.assertEqual(statuses["embedding_api_endpoint"], "pass")

    def test_diagnose_local_stack_reports_embedding_probe_failure(self) -> None:
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        response.__exit__.return_value = None
        embedding_failure = error.HTTPError(
            url="http://localhost:3000/v1/embeddings",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=None,
        )

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

        with patch.dict("os.environ", {"SWL_API_KEY": "doctor-test-key"}, clear=False):
            with patch("swallow.doctor.subprocess.run", side_effect=runs):
                with patch("swallow.doctor.request.urlopen", side_effect=[response, response, embedding_failure]):
                    exit_code, result = diagnose_local_stack()

        statuses = {check.name: check.status for check in result.checks}
        self.assertEqual(exit_code, 1)
        self.assertEqual(statuses["embedding_api_endpoint"], "fail")


if __name__ == "__main__":
    unittest.main()
