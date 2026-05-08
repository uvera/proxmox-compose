from __future__ import annotations

from pathlib import Path
import os

import proxmox_compose.engines.ansible as ansible_engine


def test_ansible_vault_password_injects_temp_vault_file(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    (workspace / "config/ansible/inventory").mkdir(parents=True)
    (workspace / "config/ansible/playbooks").mkdir(parents=True)
    (workspace / "config/ansible/inventory/hosts.yml").write_text("---\nall:\n  hosts: {}\n")
    playbook = workspace / "config/ansible/playbooks/post-provision.yml"
    playbook.write_text("---\n- hosts: all\n  gather_facts: false\n  tasks: []\n")

    monkeypatch.setenv("ANSIBLE_VAULT_PASSWORD", "secret-from-env")
    monkeypatch.delenv("ANSIBLE_VAULT_PASSWORD_FILE", raising=False)

    captured: dict[str, object] = {}

    def fake_run_command(command: list[str], cwd: Path | None = None) -> None:
        captured["command"] = command
        captured["cwd"] = cwd
        # Ensure the generated temp script exists *during* execution.
        idx = command.index("--vault-password-file")
        vault_file = Path(command[idx + 1])
        assert vault_file.exists()
        assert os.access(vault_file, os.X_OK)

    monkeypatch.setattr(ansible_engine, "run_command", fake_run_command)

    ansible_engine.run_ansible_playbook(playbook, workspace)

    cmd = captured["command"]
    assert isinstance(cmd, list)
    assert "--vault-password-file" in cmd

    # Ensure the temp script is cleaned up after the run.
    idx = cmd.index("--vault-password-file")
    vault_file = Path(cmd[idx + 1])
    assert not vault_file.exists()


def test_ansible_vault_password_does_not_override_password_file(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    (workspace / "config/ansible/inventory").mkdir(parents=True)
    (workspace / "config/ansible/playbooks").mkdir(parents=True)
    (workspace / "config/ansible/inventory/hosts.yml").write_text("---\nall:\n  hosts: {}\n")
    playbook = workspace / "config/ansible/playbooks/post-provision.yml"
    playbook.write_text("---\n- hosts: all\n  gather_facts: false\n  tasks: []\n")

    monkeypatch.setenv("ANSIBLE_VAULT_PASSWORD", "secret-from-env")
    monkeypatch.setenv("ANSIBLE_VAULT_PASSWORD_FILE", "/some/existing/path")

    captured: dict[str, object] = {}

    def fake_run_command(command: list[str], cwd: Path | None = None) -> None:
        captured["command"] = command

    monkeypatch.setattr(ansible_engine, "run_command", fake_run_command)

    ansible_engine.run_ansible_playbook(playbook, workspace)

    cmd = captured["command"]
    assert isinstance(cmd, list)
    assert "--vault-password-file" not in cmd

