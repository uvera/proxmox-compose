from pathlib import Path

import yaml

from proxmox_compose.commands.inventory import sync_inventory


def test_inventory_sync_infers_groups_from_host_vars(tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    inventory_dir = workspace / "config/ansible/inventory"
    (inventory_dir / "host_vars").mkdir(parents=True)
    (inventory_dir / "static.yml").write_text("all:\n  children: {}\n", encoding="utf-8")
    (inventory_dir / "host_vars/vm1.yml").write_text(
        yaml.safe_dump(
            {
                "proxmox_compose_host_kind": "vm",
                "proxmox_compose_host_os": "fedora",
                "ansible_host": "10.0.0.11",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (inventory_dir / "host_vars/lxc1.yml").write_text(
        yaml.safe_dump(
            {
                "proxmox_compose_host_kind": "lxc",
                "ansible_host": "10.0.0.12",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    sync_inventory(workspace)

    merged = yaml.safe_load((inventory_dir / "hosts.yml").read_text()) or {}
    fedora_hosts = merged["all"]["children"]["fedora_vms"]["hosts"]
    lxc_hosts = merged["all"]["children"]["debian_lxcs"]["hosts"]
    assert fedora_hosts["vm1"]["ansible_host"] == "10.0.0.11"
    assert lxc_hosts["lxc1"]["ansible_user"] == "root"


def test_inventory_sync_preserves_static_group_entries(tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    inventory_dir = workspace / "config/ansible/inventory"
    (inventory_dir / "host_vars").mkdir(parents=True)
    (inventory_dir / "static.yml").write_text(
        yaml.safe_dump(
            {
                "all": {
                    "children": {
                        "existing_hosts": {
                            "hosts": {"legacy": {"ansible_host": "10.0.0.99"}},
                            "vars": {"maintenance_window": "sunday"},
                        }
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    sync_inventory(workspace)

    merged = yaml.safe_load((inventory_dir / "hosts.yml").read_text()) or {}
    assert merged["all"]["children"]["existing_hosts"]["vars"]["maintenance_window"] == "sunday"
    assert merged["all"]["children"]["existing_hosts"]["hosts"]["legacy"]["ansible_host"] == "10.0.0.99"
