from pathlib import Path
import subprocess


def run_command(command: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(command, cwd=cwd, check=False)
    if result.returncode != 0:
        joined = " ".join(command)
        raise RuntimeError(f"Command failed ({result.returncode}): {joined}")
