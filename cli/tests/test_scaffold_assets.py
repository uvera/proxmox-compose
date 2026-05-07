from proxmox_compose.scaffold import SCAFFOLD_FILES
from proxmox_compose.scaffold.loader import load_scaffold_files


def test_scaffold_files_loads_from_package() -> None:
    files = load_scaffold_files()
    assert len(files) >= 40
    assert "infra/terraform/environments/homelab/main.tf" in files
    assert "config/ansible/ansible.cfg" in files


def test_scaffold_init_matches_loader() -> None:
    assert SCAFFOLD_FILES == load_scaffold_files()
