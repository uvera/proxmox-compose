from pathlib import Path

import proxmox_compose.commands.apply as apply_module
from proxmox_compose.workspace_context import WorkspacePaths, WorkspaceRunContext


def _fake_context(workspace: Path) -> WorkspaceRunContext:
    return WorkspaceRunContext(
        paths=WorkspacePaths(workspace),
        profile="default",
        ssh_key_path=None,
    )


def test_apply_command_runs_full_flow(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    calls: dict[str, object] = {}

    monkeypatch.setattr(apply_module, "prepare_run", lambda _ws, _profile: _fake_context(workspace))
    monkeypatch.setattr(
        apply_module,
        "run_terraform_apply",
        lambda path: calls.__setitem__("terraform_path", path),
    )
    monkeypatch.setattr(
        apply_module,
        "sync_inventory",
        lambda workspace: calls.__setitem__("sync_workspace", workspace),
    )

    def _record_ansible(
        playbook: Path,
        ws: Path,
        ssh_key_path: Path | None = None,
        limit: str | None = None,
    ) -> None:
        calls["ansible"] = {
            "playbook": playbook,
            "workspace": ws,
            "ssh_key_path": ssh_key_path,
            "limit": limit,
        }

    monkeypatch.setattr(apply_module, "run_ansible_playbook", _record_ansible)

    apply_module.apply_command(workspace=workspace, profile="default", host=None)

    assert calls["terraform_path"] == workspace / "infra/terraform/environments/homelab"
    assert calls["sync_workspace"] == workspace
    assert calls["ansible"] == {
        "playbook": workspace / "config/ansible/playbooks/post-provision.yml",
        "workspace": workspace,
        "ssh_key_path": None,
        "limit": None,
    }


def test_apply_command_passes_host_limit_to_ansible(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    calls: dict[str, object] = {}

    monkeypatch.setattr(apply_module, "prepare_run", lambda _ws, _profile: _fake_context(workspace))
    monkeypatch.setattr(apply_module, "run_terraform_apply", lambda _path: None)
    monkeypatch.setattr(apply_module, "sync_inventory", lambda workspace: None)

    def _record_ansible(
        playbook: Path,
        ws: Path,
        ssh_key_path: Path | None = None,
        limit: str | None = None,
    ) -> None:
        calls["limit"] = limit
        calls["playbook"] = playbook
        calls["workspace"] = ws

    monkeypatch.setattr(apply_module, "run_ansible_playbook", _record_ansible)

    apply_module.apply_command(workspace=workspace, profile="default", host="app-1")

    assert calls["limit"] == "app-1"
    assert calls["playbook"] == workspace / "config/ansible/playbooks/post-provision.yml"
    assert calls["workspace"] == workspace
