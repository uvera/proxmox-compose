from pathlib import Path

import typer

from proxmox_compose.commands.inventory import sync_inventory
from proxmox_compose.engines.ansible import run_ansible_playbook
from proxmox_compose.engines.terraform import run_terraform_apply
from proxmox_compose.profiles import get_profile_ssh_key, load_profile_env


def apply_command(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Repository root that contains infra/ and config/.",
    ),
    profile: str = typer.Option(
        "default",
        "--profile",
        "-p",
        help="Profile from ~/.config/proxmox-compose/profiles.yml",
    ),
) -> None:
    """Run Terraform apply, inventory sync, and Ansible convergence."""
    load_profile_env(profile)
    ssh_key_path = get_profile_ssh_key(profile)
    tf_env = workspace / "infra/terraform/environments/homelab"
    run_terraform_apply(tf_env)
    sync_inventory(workspace=workspace)
    run_ansible_playbook(
        workspace / "config/ansible/playbooks/post-provision.yml",
        workspace,
        ssh_key_path=ssh_key_path,
    )
