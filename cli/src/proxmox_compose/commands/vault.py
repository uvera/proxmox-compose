from pathlib import Path

import typer

from proxmox_compose.engines.runner import run_command

vault_app = typer.Typer(help="Ansible Vault helpers.")
DEFAULT_VAULT_FILE = Path("config/ansible/inventory/group_vars/all/vault.yml")
LEGACY_VAULT_FILE = Path("config/ansible/group_vars/all/vault.yml")


@vault_app.command("edit")
def vault_edit_command(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Repository root that contains config/ansible.",
    ),
    vault_file: Path = typer.Option(
        DEFAULT_VAULT_FILE,
        "--file",
        help="Vault file path (relative to workspace by default).",
    ),
    create_if_missing: bool = typer.Option(
        True,
        "--create-if-missing/--no-create-if-missing",
        help="Create encrypted vault file when it does not exist.",
    ),
) -> None:
    """Edit the shared Ansible Vault file used by this workspace."""
    ws = workspace.resolve()
    ansible_dir = (ws / "config/ansible").resolve()
    if not ansible_dir.exists():
        raise typer.BadParameter(f"Ansible directory not found: {ansible_dir}")

    if vault_file.is_absolute():
        target_file = vault_file.resolve()
    else:
        default_target = (ws / vault_file).resolve()
        legacy_target = (ws / LEGACY_VAULT_FILE).resolve()
        if vault_file == DEFAULT_VAULT_FILE and not default_target.exists() and legacy_target.exists():
            target_file = legacy_target
        else:
            target_file = default_target
    if target_file.exists() and target_file.is_dir():
        raise typer.BadParameter(f"Vault path points to a directory: {target_file}")

    if target_file.exists():
        run_command(["ansible-vault", "edit", str(target_file)], cwd=ansible_dir)
        return

    if not create_if_missing:
        raise typer.BadParameter(
            f"Vault file not found: {target_file}. Use --create-if-missing to create it."
        )

    target_file.parent.mkdir(parents=True, exist_ok=True)
    run_command(["ansible-vault", "create", str(target_file)], cwd=ansible_dir)
