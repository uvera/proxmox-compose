from pathlib import Path

import typer
import yaml

from proxmox_compose.commands.inventory import sync_inventory
from proxmox_compose.engines.ansible import run_ansible_playbook
from proxmox_compose.workspace_context import prepare_run


def _group_hosts_count(inventory: dict, group: str) -> int:
    children = inventory.get("all", {}).get("children", {})
    hosts = children.get(group, {}).get("hosts", {})
    if isinstance(hosts, dict):
        return len(hosts)
    return 0


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
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Increase Ansible verbosity (-v shows task stdout, repeat for more).",
    ),
) -> None:
    """Converge already-existing hosts without creating new infra."""
    ctx = prepare_run(workspace, profile)
    sync_inventory(workspace=ctx.paths.workspace)
    hosts_file = ctx.paths.workspace / "config/ansible/inventory/hosts.yml"
    merged_inventory = yaml.safe_load(hosts_file.read_text()) or {}
    existing_hosts_count = _group_hosts_count(merged_inventory, "existing_hosts")
    existing_docker_vms_count = _group_hosts_count(merged_inventory, "existing_docker_vms")
    if existing_hosts_count + existing_docker_vms_count == 0:
        raise typer.BadParameter(
            "Merged inventory has no hosts in 'existing_hosts' or 'existing_docker_vms'. "
            "Add hosts to config/ansible/inventory/static.yml and retry."
        )

    run_ansible_playbook(
        ctx.paths.provision_existing_playbook,
        ctx.paths.workspace,
        ssh_key_path=ctx.ssh_key_path,
        verbosity=verbose,
    )
