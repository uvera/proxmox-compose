from pathlib import Path

import typer

from proxmox_compose.commands.inventory import sync_inventory
from proxmox_compose.engines.ansible import run_ansible_playbook
from proxmox_compose.engines.terraform import run_terraform_apply
from proxmox_compose.workspace_context import prepare_run


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
    ctx = prepare_run(workspace, profile)
    run_terraform_apply(ctx.paths.terraform_homelab)
    sync_inventory(workspace=ctx.paths.workspace)
    run_ansible_playbook(
        ctx.paths.post_provision_playbook,
        ctx.paths.workspace,
        ssh_key_path=ctx.ssh_key_path,
    )
