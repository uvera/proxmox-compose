from pathlib import Path

import typer

from proxmox_compose.engines.ansible import run_ansible_check
from proxmox_compose.engines.terraform import run_terraform_plan
from proxmox_compose.profiles import load_profile_env


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
) -> None:
    """Run Terraform plan and Ansible check mode."""
    load_profile_env(profile)
    run_terraform_plan(workspace / "infra/terraform/environments/homelab")
    run_ansible_check(workspace / "config/ansible/playbooks/post-provision.yml", workspace)
