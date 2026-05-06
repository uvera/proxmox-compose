from pathlib import Path

from proxmox_compose.engines.runner import run_command


def _common_cmd(playbook: Path, workspace: Path, ssh_key_path: Path | None = None) -> list[str]:
    workspace = workspace.resolve()
    playbook = playbook.resolve()
    command = [
        "ansible-playbook",
        "-i",
        str(workspace / "config/ansible/inventory/hosts.yml"),
        str(playbook),
    ]
    if ssh_key_path:
        command.extend(["--private-key", str(ssh_key_path)])
    return command


def run_ansible_check(playbook: Path, workspace: Path, ssh_key_path: Path | None = None) -> None:
    run_command(
        _common_cmd(playbook, workspace, ssh_key_path) + ["--check"],
        cwd=(workspace / "config/ansible").resolve(),
    )


def run_ansible_playbook(playbook: Path, workspace: Path, ssh_key_path: Path | None = None) -> None:
    run_command(
        _common_cmd(playbook, workspace, ssh_key_path),
        cwd=(workspace / "config/ansible").resolve(),
    )
