from pathlib import Path

import typer
import yaml

from proxmox_compose.commands.inventory import sync_inventory
from proxmox_compose.engines.ansible import run_ansible_playbook
from proxmox_compose.profiles import get_profile_ssh_key, load_profile_env


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
) -> None:
    """Converge already-existing hosts without creating new infra."""
    load_profile_env(profile)
    sync_inventory(workspace=workspace)
    hosts_file = workspace / "config/ansible/inventory/hosts.yml"
    merged_inventory = yaml.safe_load(hosts_file.read_text()) or {}
    existing_hosts_count = _group_hosts_count(merged_inventory, "existing_hosts")
    existing_docker_vms_count = _group_hosts_count(merged_inventory, "existing_docker_vms")
    if existing_hosts_count + existing_docker_vms_count == 0:
        raise typer.BadParameter(
            "Merged inventory has no hosts in 'existing_hosts' or 'existing_docker_vms'. "
            "Add hosts to config/ansible/inventory/static.yml and retry."
        )

    ssh_key_path = get_profile_ssh_key(profile)
    run_ansible_playbook(
        workspace / "config/ansible/playbooks/provision-existing.yml",
        workspace,
        ssh_key_path=ssh_key_path,
    )
