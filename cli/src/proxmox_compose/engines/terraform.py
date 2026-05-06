from pathlib import Path

from proxmox_compose.engines.runner import run_command


def _init(path: Path) -> None:
    run_command(["terraform", "init"], cwd=path)


def run_terraform_plan(path: Path) -> None:
    _init(path)
    run_command(["terraform", "plan"], cwd=path)


def run_terraform_apply(path: Path) -> None:
    _init(path)
    run_command(["terraform", "apply", "-auto-approve"], cwd=path)
