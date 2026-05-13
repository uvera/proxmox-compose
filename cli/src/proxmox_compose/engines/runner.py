from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class CommandNotFoundError(RuntimeError):
    def __init__(self, command: list[str], cwd: Path | None) -> None:
        self.command = command
        self.cwd = cwd
        joined = " ".join(command)
        where = f" (cwd={cwd})" if cwd else ""
        super().__init__(f"Command not found: {joined}{where}")


class CommandFailedError(RuntimeError):
    def __init__(
        self,
        *,
        command: list[str],
        cwd: Path | None,
        exit_code: int,
        stdout: str | None,
        stderr: str | None,
    ) -> None:
        self.command = command
        self.cwd = cwd
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(
            _format_command_failure(
                command,
                cwd,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
            )
        )


def _format_command_failure(
    command: list[str],
    cwd: Path | None,
    *,
    exit_code: int,
    stdout: str | None,
    stderr: str | None,
) -> str:
    lines = [
        f"Command failed (exit_code={exit_code}): {' '.join(command)}",
    ]
    if cwd is not None:
        lines.append(f"cwd={cwd}")
    if stdout and stdout.strip():
        lines.append("\n--- stdout ---\n" + stdout.rstrip())
    if stderr and stderr.strip():
        lines.append("\n--- stderr ---\n" + stderr.rstrip())
    return "\n".join(lines)


def run_command(
    command: list[str],
    cwd: Path | None = None,
    *,
    capture: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Run a subprocess; on failure raise CommandFailedError (non-zero exit) or CommandNotFoundError.

    Use capture=False (default) to stream commands interactively.
    Use capture=True when you need stdout for downstream parsing.
    """
    kw: dict[str, Any] = {
        "cwd": str(cwd.resolve()) if cwd is not None else None,
        "env": env,
        "check": False,
        "text": True,
    }
    if capture:
        kw["capture_output"] = True
    try:
        completed = subprocess.run(command, **kw)
    except FileNotFoundError as exc:
        raise CommandNotFoundError(command, cwd) from exc
    if completed.returncode != 0:
        raise CommandFailedError(
            command=command,
            cwd=cwd,
            exit_code=completed.returncode,
            stdout=completed.stdout if capture else None,
            stderr=completed.stderr if capture else None,
        )
    return completed


def run_subprocess_capture(
    command: list[str],
    cwd: Path | None = None,
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Backward-compatible wrapper returning a CompletedProcess.

    Prefer `run_command(..., capture=True)` for new code.
    """
    return subprocess.run(
        command,
        cwd=str(cwd.resolve()) if cwd is not None else None,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
