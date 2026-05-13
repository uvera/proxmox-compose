from pathlib import Path
from typing import Any

import typer
import yaml

inventory_app = typer.Typer(help="Inventory utilities.")
INVENTORY_GROUPS = (
    "debian_vms",
    "fedora_vms",
    "debian_lxcs",
    "existing_hosts",
    "existing_docker_vms",
)


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _read_host_vars(inventory_dir: Path) -> dict[str, dict[str, Any]]:
    host_vars_dir = inventory_dir / "host_vars"
    if not host_vars_dir.exists():
        return {}

    data: dict[str, dict[str, Any]] = {}
    for host_file in sorted(host_vars_dir.glob("*.yml")):
        name = host_file.name
        # Keep scaffold examples in-place but inert until renamed/copied to a real hostname.
        if name.startswith("example_") or name.endswith(".example.yml"):
            continue
        parsed = yaml.safe_load(host_file.read_text()) or {}
        if not isinstance(parsed, dict):
            continue
        data[host_file.stem] = parsed
    return data


def _default_user_for_group(group: str) -> str:
    if group == "debian_lxcs":
        return "root"
    if group == "fedora_vms":
        return "fedora"
    return "debian"


def _candidate_group(host_vars: dict[str, Any]) -> str | None:
    explicit_group = str(host_vars.get("proxmox_compose_inventory_group", "")).strip()
    if explicit_group in INVENTORY_GROUPS:
        return explicit_group

    host_kind = str(host_vars.get("proxmox_compose_host_kind", "")).strip().lower()
    host_os = str(host_vars.get("proxmox_compose_host_os", "")).strip().lower()
    if host_kind == "lxc":
        return "debian_lxcs"
    if host_kind == "existing":
        return "existing_hosts"
    if host_kind == "existing_docker_vm":
        return "existing_docker_vms"
    if host_kind == "vm":
        return "fedora_vms" if host_os == "fedora" else "debian_vms"
    return None


def _empty_generated_inventory() -> dict[str, Any]:
    return {
        "all": {
            "children": {group: {"hosts": {}} for group in INVENTORY_GROUPS},
        }
    }


def _generated_inventory_from_ansible(workspace: Path) -> dict[str, Any]:
    inventory_dir = workspace / "config/ansible/inventory"
    static_inventory = _read_yaml(inventory_dir / "static.yml")
    host_vars_map = _read_host_vars(inventory_dir)
    data = _empty_generated_inventory()

    children = static_inventory.get("all", {}).get("children", {})
    for group in INVENTORY_GROUPS:
        static_hosts = children.get(group, {}).get("hosts", {})
        if isinstance(static_hosts, dict):
            data["all"]["children"][group]["hosts"].update(static_hosts)

    for host, host_vars in host_vars_map.items():
        group = _candidate_group(host_vars)
        if not group:
            continue
        data["all"]["children"][group]["hosts"][host] = {
            "ansible_host": str(host_vars.get("ansible_host", host)),
            "ansible_user": str(host_vars.get("ansible_user", _default_user_for_group(group))),
        }

    return data


def sync_inventory(workspace: Path) -> None:
    """Merge static inventory with generated inventory from Ansible metadata."""
    static_file = workspace / "config/ansible/inventory/static.yml"
    generated_file = workspace / "config/ansible/inventory/generated.yml"
    out_file = workspace / "config/ansible/inventory/hosts.yml"

    static_inventory = _read_yaml(static_file)
    generated_inventory = _generated_inventory_from_ansible(workspace)
    generated_file.parent.mkdir(parents=True, exist_ok=True)
    generated_file.write_text(yaml.safe_dump(generated_inventory, sort_keys=False))

    merged = {"all": {"children": {}}}
    merged["all"]["children"].update(static_inventory.get("all", {}).get("children", {}))
    for group, group_data in generated_inventory.get("all", {}).get("children", {}).items():
        merged_group = merged["all"]["children"].setdefault(group, {})
        if not isinstance(merged_group, dict):
            merged_group = {}
            merged["all"]["children"][group] = merged_group

        existing_hosts = merged_group.get("hosts", {})
        if not isinstance(existing_hosts, dict):
            existing_hosts = {}
        generated_hosts = group_data.get("hosts", {})
        if not isinstance(generated_hosts, dict):
            generated_hosts = {}
        merged_group["hosts"] = {**existing_hosts, **generated_hosts}

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
