from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib import error, request

from .store import iter_file_task_ids, normalize_store_backend

DEFAULT_NEW_API_BASE_URL = "http://localhost:3000"


@dataclass(slots=True)
class DoctorResult:
    binary_found: bool
    launch_ok: bool
    executor_mode: str
    note_only_recommended: bool
    codex_bin: str
    details: str = ""


@dataclass(slots=True)
class LocalStackCheck:
    name: str
    status: str
    details: str = ""
    optional: bool = False


@dataclass(slots=True)
class LocalStackDoctorResult:
    checks: list[LocalStackCheck]


@dataclass(slots=True)
class SqliteDoctorResult:
    backend: str
    db_path: str
    db_exists: bool
    schema_ok: bool
    integrity_ok: bool
    task_count: int
    event_count: int
    file_task_count: int
    file_only_task_count: int
    migration_recommended: bool
    details: str = ""


def _run_command(args: list[str], *, timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )


def _command_details(completed: subprocess.CompletedProcess[str]) -> str:
    return (completed.stdout or completed.stderr or "").strip()


def _check_command_success(name: str, args: list[str], *, timeout: int = 10) -> LocalStackCheck:
    try:
        completed = _run_command(args, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return LocalStackCheck(name=name, status="fail", details=str(exc))
    return LocalStackCheck(
        name=name,
        status="pass" if completed.returncode == 0 else "fail",
        details=_command_details(completed),
    )


def _check_container_running(name: str, container_name: str, *, optional: bool = False) -> LocalStackCheck:
    try:
        completed = _run_command(
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}|{{.Status}}"],
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return LocalStackCheck(name=name, status="skip" if optional else "fail", details=str(exc), optional=optional)

    entries = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if completed.returncode != 0:
        return LocalStackCheck(
            name=name,
            status="skip" if optional else "fail",
            details=_command_details(completed),
            optional=optional,
        )
    if not entries:
        return LocalStackCheck(
            name=name,
            status="skip" if optional else "fail",
            details=f"Container '{container_name}' is not running.",
            optional=optional,
        )
    return LocalStackCheck(name=name, status="pass", details=entries[0], optional=optional)


def _check_http_endpoint(name: str, url: str, *, timeout: int = 5) -> LocalStackCheck:
    try:
        with request.urlopen(url, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            return LocalStackCheck(
                name=name,
                status="pass" if 200 <= int(status) < 300 else "fail",
                details=f"HTTP {status}",
            )
    except (error.URLError, TimeoutError, ValueError) as exc:
        return LocalStackCheck(name=name, status="fail", details=str(exc))


def resolve_new_api_base_url() -> str:
    configured = os.environ.get("AIWF_NEW_API_BASE_URL", DEFAULT_NEW_API_BASE_URL).strip()
    if not configured:
        return DEFAULT_NEW_API_BASE_URL
    return configured.rstrip("/")


def _check_new_api_endpoint(*, timeout: int = 5) -> LocalStackCheck:
    url = f"{resolve_new_api_base_url()}/v1/models"
    try:
        with request.urlopen(url, timeout=timeout) as response:
            status = int(getattr(response, "status", 200))
            return LocalStackCheck(
                name="new_api_endpoint",
                status="pass" if 200 <= status < 300 else "fail",
                details=f"HTTP {status} ({url})",
            )
    except error.HTTPError as exc:
        status = int(getattr(exc, "code", 0) or 0)
        reachable = status in {401, 403}
        return LocalStackCheck(
            name="new_api_endpoint",
            status="pass" if reachable else "fail",
            details=f"HTTP {status} ({url})",
        )
    except (error.URLError, TimeoutError, ValueError) as exc:
        return LocalStackCheck(name="new_api_endpoint", status="fail", details=str(exc))


def _check_pgvector_extension() -> LocalStackCheck:
    postgres_check = _check_container_running("postgres_container", "postgres")
    if postgres_check.status != "pass":
        return LocalStackCheck(
            name="pgvector_extension",
            status="skip",
            details="Postgres container is not running.",
            optional=True,
        )

    try:
        completed = _run_command(
            [
                "docker",
                "exec",
                "postgres",
                "psql",
                "-U",
                "postgres",
                "-d",
                "postgres",
                "-tAc",
                "SELECT extname FROM pg_extension WHERE extname = 'vector';",
            ],
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return LocalStackCheck(name="pgvector_extension", status="fail", details=str(exc))

    output = (completed.stdout or "").strip()
    if completed.returncode == 0 and output == "vector":
        return LocalStackCheck(name="pgvector_extension", status="pass", details="vector")
    return LocalStackCheck(
        name="pgvector_extension",
        status="fail",
        details=_command_details(completed) or "pgvector extension not enabled.",
    )


def diagnose_local_stack() -> tuple[int, LocalStackDoctorResult]:
    checks = [
        _check_command_success("docker_daemon", ["docker", "info"]),
        _check_container_running("new_api_container", "new-api"),
        _check_container_running("tensorzero_container", "tensorzero", optional=True),
        _check_container_running("postgres_container", "postgres"),
        _check_pgvector_extension(),
        _check_http_endpoint("new_api_http", "http://localhost:3000/api/status"),
        _check_new_api_endpoint(),
        _check_command_success("wireguard_tunnel", ["ping", "-c", "1", "-W", "2", "10.8.0.1"], timeout=5),
        _check_command_success(
            "egress_proxy",
            ["curl", "-x", "http://10.8.0.1:8888", "-s", "https://ifconfig.me"],
            timeout=10,
        ),
    ]
    exit_code = 0 if all(check.status in {"pass", "skip"} for check in checks if check.optional) and all(
        check.status == "pass" for check in checks if not check.optional
    ) else 1
    return exit_code, LocalStackDoctorResult(checks=checks)


def diagnose_sqlite_store(base_dir: Path) -> tuple[int, SqliteDoctorResult]:
    from .sqlite_store import SqliteTaskStore

    backend = normalize_store_backend(os.environ.get("SWALLOW_STORE_BACKEND", "sqlite"))
    store = SqliteTaskStore()
    health = store.database_health(base_dir)
    file_task_ids = iter_file_task_ids(base_dir)
    file_only_task_count = 0
    for task_id in file_task_ids:
        if not store.task_exists(base_dir, task_id) and store.event_count(base_dir, task_id) == 0:
            file_only_task_count += 1

    result = SqliteDoctorResult(
        backend=backend,
        db_path=str(health.get("db_path", "")),
        db_exists=bool(health.get("db_exists", False)),
        schema_ok=bool(health.get("schema_ok", False)),
        integrity_ok=bool(health.get("integrity_ok", False)),
        task_count=int(health.get("task_count", 0) or 0),
        event_count=int(health.get("event_count", 0) or 0),
        file_task_count=len(file_task_ids),
        file_only_task_count=file_only_task_count,
        migration_recommended=file_only_task_count > 0,
        details=str(health.get("details", "")).strip(),
    )
    exit_code = 1 if result.db_exists and (not result.schema_ok or not result.integrity_ok) else 0
    return exit_code, result


def diagnose_codex() -> tuple[int, DoctorResult]:
    executor_mode = os.environ.get("AIWF_EXECUTOR_MODE", "codex").strip().lower() or "codex"
    codex_bin = os.environ.get("AIWF_CODEX_BIN", "codex").strip() or "codex"
    resolved = shutil.which(codex_bin)
    if not resolved:
        return 1, DoctorResult(
            binary_found=False,
            launch_ok=False,
            executor_mode=executor_mode,
            note_only_recommended=True,
            codex_bin=codex_bin,
            details="Codex binary not found in PATH.",
        )

    try:
        completed = subprocess.run(
            [codex_bin, "--version"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, DoctorResult(
            binary_found=True,
            launch_ok=False,
            executor_mode=executor_mode,
            note_only_recommended=True,
            codex_bin=resolved,
            details=f"Codex launch check failed: {exc}",
        )

    launch_ok = completed.returncode == 0
    details = (completed.stdout or completed.stderr or "").strip()
    return (0 if launch_ok else 1), DoctorResult(
        binary_found=True,
        launch_ok=launch_ok,
        executor_mode=executor_mode,
        note_only_recommended=not launch_ok,
        codex_bin=resolved,
        details=details,
    )


def format_codex_doctor_result(result: DoctorResult) -> str:
    lines = [
        f"binary_found={'yes' if result.binary_found else 'no'}",
        f"launch_ok={'yes' if result.launch_ok else 'no'}",
        f"executor_mode={result.executor_mode}",
        f"note_only_recommended={'yes' if result.note_only_recommended else 'no'}",
    ]
    if result.details:
        lines.append(f"details={result.details}")
    return "\n".join(lines)


def format_local_stack_doctor_result(result: LocalStackDoctorResult) -> str:
    lines: list[str] = []
    for check in result.checks:
        lines.append(f"{check.name}={check.status}")
        if check.details:
            lines.append(f"{check.name}_details={check.details}")
    return "\n".join(lines)


def format_sqlite_doctor_result(result: SqliteDoctorResult) -> str:
    lines = [
        f"backend={result.backend}",
        f"db_path={result.db_path}",
        f"db_exists={'yes' if result.db_exists else 'no'}",
        f"schema_ok={'yes' if result.schema_ok else 'no'}",
        f"integrity_ok={'yes' if result.integrity_ok else 'no'}",
        f"task_count={result.task_count}",
        f"event_count={result.event_count}",
        f"file_task_count={result.file_task_count}",
        f"file_only_task_count={result.file_only_task_count}",
        f"migration_recommended={'yes' if result.migration_recommended else 'no'}",
    ]
    if result.details:
        lines.append(f"details={result.details}")
    return "\n".join(lines)
