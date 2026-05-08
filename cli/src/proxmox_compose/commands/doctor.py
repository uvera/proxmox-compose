import shutil
from pathlib import Path

import typer

from proxmox_compose.profiles import (
    DEFAULT_PROFILE_FILE,
    get_profile,
    get_profile_secret_env_commands,
    get_profile_ssh_key,
    get_proxmox_auth_method,
)

REQUIRED_BINARIES = ["terraform", "ansible-playbook", "git"]


def _binary_checks() -> tuple[list[str], list[str]]:
    ok: list[str] = []
    missing: list[str] = []
    for binary in REQUIRED_BINARIES:
        if shutil.which(binary):
            ok.append(binary)
        else:
            missing.append(binary)
    return ok, missing


def _required_proxmox_env_keys(auth_method: str) -> list[str]:
    if auth_method == "password":
        return [
            "TF_VAR_proxmox_endpoint",
            "TF_VAR_proxmox_username",
            "TF_VAR_proxmox_password",
        ]
    return [
        "TF_VAR_proxmox_endpoint",
        "TF_VAR_proxmox_token_id",
        "TF_VAR_proxmox_token_secret",
    ]


def _profile_checks(
    profile: str,
    auth_method: str,
) -> tuple[list[str], list[str], bool]:
    profile_data = get_profile(profile)
    env_vars = profile_data.get("env", {})
    secret_env_commands = get_profile_secret_env_commands(profile)
    required_keys = _required_proxmox_env_keys(auth_method)
    missing = [
        key
        for key in required_keys
        if not env_vars.get(key) and not secret_env_commands.get(key)
    ]
    ok = [key for key in required_keys if key not in missing]
    return ok, missing, bool(profile_data)


def doctor_command(
    profile: str = typer.Option(
        "default",
        "--profile",
        "-p",
        help="Profile from ~/.config/proxmox-compose/profiles.yml",
    ),
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Repository root to verify required files.",
    ),
) -> None:
    """Check local prerequisites and profile completeness."""
    typer.echo("== proxmox-compose doctor ==")

    ok_bins, missing_bins = _binary_checks()
    typer.echo("\nBinaries:")
    for binary in ok_bins:
        typer.echo(f"  [ok] {binary}")
    for binary in missing_bins:
        typer.echo(f"  [missing] {binary}")

    typer.echo(f"\nProfiles file: {DEFAULT_PROFILE_FILE}")
    if DEFAULT_PROFILE_FILE.exists():
        typer.echo("  [ok] profiles file exists")
    else:
        typer.echo("  [missing] profiles file does not exist")

    profile_config_error: str | None = None
    auth_method_display: str | None = None
    try:
        auth_method_display = get_proxmox_auth_method(profile)
    except ValueError as exc:
        profile_config_error = str(exc)

    if profile_config_error:
        ok_vars, missing_vars, profile_exists = [], [], bool(get_profile(profile))
    else:
        assert auth_method_display is not None
        ok_vars, missing_vars, profile_exists = _profile_checks(profile, auth_method_display)
    typer.echo(f"\nProfile '{profile}':")
    if profile_exists:
        typer.echo("  [ok] profile exists")
    else:
        typer.echo("  [missing] profile does not exist")
    if profile_config_error:
        typer.echo(f"  [error] {profile_config_error}")
    else:
        typer.echo(f"  [ok] proxmox_auth_method={auth_method_display}")
    for key in ok_vars:
        typer.echo(f"  [ok] {key}")
    for key in missing_vars:
        typer.echo(f"  [missing] {key}")

    ssh_key_path = get_profile_ssh_key(profile)
    if ssh_key_path:
        if ssh_key_path.exists():
            typer.echo(f"  [ok] ssh_key_path={ssh_key_path}")
        else:
            typer.echo(f"  [missing] ssh_key_path={ssh_key_path} (file not found)")
            missing_vars.append("ssh_key_path")

    required_paths = [
        workspace / "infra/terraform/environments/homelab/main.tf",
        workspace / "config/ansible/playbooks/post-provision.yml",
        workspace / "config/ansible/inventory/static.yml",
    ]
    typer.echo("\nWorkspace files:")
    missing_files: list[Path] = []
    for required_path in required_paths:
        if required_path.exists():
            typer.echo(f"  [ok] {required_path}")
        else:
            missing_files.append(required_path)
            typer.echo(f"  [missing] {required_path}")

    has_errors = bool(
        missing_bins
        or missing_vars
        or missing_files
        or not profile_exists
        or profile_config_error
    )
    if has_errors:
        raise typer.Exit(code=1)
