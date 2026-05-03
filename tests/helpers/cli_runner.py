from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Callable


@dataclass(frozen=True, slots=True)
class CliRun:
    exit_code: int
    stdout: str
    stderr: str

    def assert_success(self) -> None:
        assert self.exit_code == 0, self.stderr or self.stdout


def run_cli(
    base_dir: Path,
    *args: str,
    main_func: Callable[[list[str]], int] | None = None,
) -> CliRun:
    from swallow.adapters.cli import main as cli_main

    runner = main_func or cli_main
    stdout = StringIO()
    stderr = StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = runner(["--base-dir", str(base_dir), *args])
    return CliRun(exit_code=exit_code, stdout=stdout.getvalue(), stderr=stderr.getvalue())
