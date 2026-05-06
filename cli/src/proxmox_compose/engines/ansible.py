from pathlib import Path

from proxmox_compose.engines.runner import run_command


def _common_cmd(playbook: Path, workspace: Path) -> list[str]:
    return [
        "ansible-playbook",
        "-i",
        str(workspace / "config/ansible/inventory/hosts.yml"),
        str(playbook),
    ]


def run_ansible_check(playbook: Path, workspace: Path) -> None:
    run_command(
        _common_cmd(playbook, workspace) + ["--check"],
        cwd=workspace / "config/ansible",
    )


def run_ansible_playbook(playbook: Path, workspace: Path) -> None:
    run_command(_common_cmd(playbook, workspace), cwd=workspace / "config/ansible")
