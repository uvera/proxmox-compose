from pathlib import Path

import typer

from proxmox_compose.commands.inventory import sync_inventory
from proxmox_compose.engines.ansible import run_ansible_check
from proxmox_compose.workspace_context import prepare_run


def plan_command(
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
    """Run Ansible check mode for infra provisioning and post-provision flows."""
    ctx = prepare_run(workspace, profile)
    sync_inventory(workspace=ctx.paths.workspace)
    run_ansible_check(
        ctx.paths.provision_infra_playbook,
        ctx.paths.workspace,
        ssh_key_path=ctx.ssh_key_path,
    )
    run_ansible_check(
        ctx.paths.post_provision_playbook,
        ctx.paths.workspace,
        ssh_key_path=ctx.ssh_key_path,
    )
