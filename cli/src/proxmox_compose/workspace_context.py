"""Shared workspace paths and profile-loaded SSH key for orchestration commands."""

from dataclasses import dataclass
from pathlib import Path

from proxmox_compose.profiles import get_profile_ssh_key, load_profile_env


@dataclass(frozen=True)
class WorkspacePaths:
    """Canonical paths under a proxmox-compose workspace root."""

    workspace: Path

    @property
    def post_provision_playbook(self) -> Path:
        return self.workspace / "config/ansible/playbooks/post-provision.yml"

    @property
    def provision_infra_playbook(self) -> Path:
        return self.workspace / "config/ansible/playbooks/provision-infra.yml"

    @property
    def provision_existing_playbook(self) -> Path:
        return self.workspace / "config/ansible/playbooks/provision-existing.yml"


@dataclass(frozen=True)
class WorkspaceRunContext:
    paths: WorkspacePaths
    profile: str
    ssh_key_path: Path | None


def prepare_run(workspace: Path, profile: str) -> WorkspaceRunContext:
    """Load profile env (including secret commands), then resolve SSH key path."""
    load_profile_env(profile)
    return WorkspaceRunContext(
        paths=WorkspacePaths(workspace),
        profile=profile,
        ssh_key_path=get_profile_ssh_key(profile),
    )
