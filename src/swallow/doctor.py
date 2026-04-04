from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(slots=True)
class DoctorResult:
    binary_found: bool
    launch_ok: bool
    executor_mode: str
    note_only_recommended: bool
    codex_bin: str
    details: str = ""


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
