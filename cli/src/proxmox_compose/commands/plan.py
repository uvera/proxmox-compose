from pathlib import Path

import typer

from proxmox_compose.commands.inventory import sync_inventory
from proxmox_compose.engines.ansible import run_ansible_check
from proxmox_compose.engines.terraform import run_terraform_plan
from proxmox_compose.profiles import get_profile_ssh_key, load_profile_env
from proxmox_compose.proxmox_auth import prompt_proxmox_otp


def plan_command(
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
    prompt_proxmox_otp_flag: bool = typer.Option(
        False,
        "--prompt-proxmox-otp",
        help="Prompt for Proxmox TOTP and set PROXMOX_VE_OTP (password auth with 2FA).",
    ),
) -> None:
    """Run Terraform plan and Ansible check mode."""
    load_profile_env(profile)
    if prompt_proxmox_otp_flag:
        try:
            prompt_proxmox_otp()
        except RuntimeError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc
    ssh_key_path = get_profile_ssh_key(profile)
    run_terraform_plan(workspace / "infra/terraform/environments/homelab")
    sync_inventory(workspace=workspace)
    run_ansible_check(
        workspace / "config/ansible/playbooks/post-provision.yml",
        workspace,
        ssh_key_path=ssh_key_path,
    )
