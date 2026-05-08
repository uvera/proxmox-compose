from pathlib import Path
from typing import Any
import json

import typer
import yaml

from proxmox_compose.engines.runner import (
    CommandFailedError,
    CommandNotFoundError,
    run_command,
)


inventory_app = typer.Typer(help="Inventory utilities.")


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _terraform_outputs(workspace: Path) -> dict[str, Any]:
    tf_path = workspace / "infra/terraform/environments/homelab"
    if not tf_path.exists():
        return {}
    try:
        result = run_command(["terraform", "output", "-json"], cwd=tf_path, capture=True)
    except (CommandNotFoundError, CommandFailedError):
        return {}
    if not result.stdout.strip():
        return {}
    return json.loads(result.stdout)


def _generated_inventory_from_terraform(workspace: Path) -> dict[str, Any]:
    outputs = _terraform_outputs(workspace)
    vms = outputs.get("vms", {}).get("value", {})
    lxcs = outputs.get("debian_lxcs", {}).get("value", {})

    data: dict[str, Any] = {
        "all": {
            "children": {
                "debian_vms": {"hosts": {}},
                "fedora_vms": {"hosts": {}},
                "debian_lxcs": {"hosts": {}},
            }
        }
    }
    for vm_name, vm_meta in vms.items():
        host_meta = {
            "ansible_host": vm_meta.get("ansible_host", vm_name),
            "ansible_user": vm_meta.get("ansible_user", "debian"),
        }
        if vm_meta.get("os", "debian").lower() == "fedora":
            data["all"]["children"]["fedora_vms"]["hosts"][vm_name] = host_meta
        else:
            data["all"]["children"]["debian_vms"]["hosts"][vm_name] = host_meta

    for lxc_name, lxc_meta in lxcs.items():
        data["all"]["children"]["debian_lxcs"]["hosts"][lxc_name] = {
            "ansible_host": lxc_meta.get("ansible_host", lxc_name),
            "ansible_user": lxc_meta.get("ansible_user", "root"),
        }
    return data


def sync_inventory(workspace: Path) -> None:
    """Merge static inventory with generated inventory from Terraform outputs."""
    static_file = workspace / "config/ansible/inventory/static.yml"
    generated_file = workspace / "config/ansible/inventory/generated.yml"
    out_file = workspace / "config/ansible/inventory/hosts.yml"

    static_inventory = _read_yaml(static_file)
    generated_inventory = _generated_inventory_from_terraform(workspace)
    generated_file.parent.mkdir(parents=True, exist_ok=True)
    generated_file.write_text(yaml.safe_dump(generated_inventory, sort_keys=False))

    merged = {"all": {"children": {}}}
    merged["all"]["children"].update(static_inventory.get("all", {}).get("children", {}))
    merged["all"]["children"].update(generated_inventory.get("all", {}).get("children", {}))
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(yaml.safe_dump(merged, sort_keys=False))


@inventory_app.command("sync")
def inventory_sync_command(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Repository root that contains config/ansible.",
    ),
) -> None:
    """Regenerate merged Ansible inventory."""
    sync_inventory(workspace)
    typer.echo(f"Wrote merged inventory to {workspace / 'config/ansible/inventory/hosts.yml'}")
