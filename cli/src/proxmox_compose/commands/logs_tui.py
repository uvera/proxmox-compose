"""Textual-based log explorer."""

from pathlib import Path

import typer

from proxmox_compose.commands.logs import load_hosts
from proxmox_compose.tui.logs_explorer import run_logs_explorer


def logs_tui_command(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Homelab repo root containing config/ansible/",
    ),
    profile: str = typer.Option(
        "default",
        "--profile",
        "-p",
        help="Profile from ~/.config/proxmox-compose/profiles.yml",
    ),
    strict_host_keys: bool = typer.Option(
        False,
        "--strict-host-keys",
        help="Do not use StrictHostKeyChecking=accept-new (same semantics as proxmox-compose logs).",
    ),
    use_sudo_journal: bool = typer.Option(
        False,
        "--sudo",
        help="Use sudo journalctl for systemd units (same semantics as proxmox-compose logs).",
    ),
) -> None:
    """Pick hosts and log targets interactively (Python/Textual UI), then stream SSH logs."""
    workspace_r = workspace.resolve()
    try:
        merged = load_hosts(workspace_r)
    except FileNotFoundError as exc:
        path = exc.filename or str(workspace_r / "config/ansible/inventory/hosts.yml")
        typer.secho(
            f"Merged inventory not found ({path}). "
            f"Run proxmox-compose inventory sync --workspace {workspace_r}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1) from exc

    run_logs_explorer(
        workspace=workspace_r,
        profile=profile,
        merged_hosts=merged,
        strict_host_keys=strict_host_keys,
        use_sudo_journal=use_sudo_journal,
    )
