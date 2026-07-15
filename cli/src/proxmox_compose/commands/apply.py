from pathlib import Path

import typer

from proxmox_compose.commands.inventory import sync_inventory
from proxmox_compose.engines.ansible import run_ansible_playbook
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
    host: str | None = typer.Option(
        None,
        "--host",
        "-H",
        help="Limit post-provision Ansible convergence to a host pattern.",
    ),
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Increase Ansible verbosity (-v shows task stdout, repeat for more).",
    ),
) -> None:
    """Run inventory sync plus Ansible provisioning/convergence."""
    ctx = prepare_run(workspace, profile)
    sync_inventory(workspace=ctx.paths.workspace)
    run_ansible_playbook(
        ctx.paths.provision_infra_playbook,
        ctx.paths.workspace,
        ssh_key_path=ctx.ssh_key_path,
        verbosity=verbose,
    )
    run_ansible_playbook(
        ctx.paths.post_provision_playbook,
        ctx.paths.workspace,
        ssh_key_path=ctx.ssh_key_path,
        limit=host,
        verbosity=verbose,
    )
