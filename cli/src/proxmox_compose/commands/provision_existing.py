from pathlib import Path

import typer

from proxmox_compose.engines.ansible import run_ansible_playbook
from proxmox_compose.profiles import load_profile_env


def provision_existing_command(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Repository root that contains config/ansible.",
    ),
    profile: str = typer.Option(
        "default",
        "--profile",
        "-p",
        help="Profile from ~/.config/proxmox-compose/profiles.yml",
    ),
) -> None:
    """Converge already-existing hosts without creating new infra."""
    load_profile_env(profile)
    run_ansible_playbook(
        workspace / "config/ansible/playbooks/provision-existing.yml",
        workspace,
    )
