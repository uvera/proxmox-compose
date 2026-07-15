from pathlib import Path

import proxmox_compose.engines.ansible as ansible_engine


def test_run_ansible_playbook_adds_limit_argument(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    (workspace / "config/ansible/inventory").mkdir(parents=True)
    (workspace / "config/ansible/playbooks").mkdir(parents=True)
    (workspace / "config/ansible/inventory/hosts.yml").write_text("---\nall:\n  hosts: {}\n")
    playbook = workspace / "config/ansible/playbooks/post-provision.yml"
    playbook.write_text("---\n- hosts: all\n  gather_facts: false\n  tasks: []\n")

    captured: dict[str, object] = {}

    def fake_run_command(command: list[str], cwd: Path | None = None) -> None:
        captured["command"] = command
        captured["cwd"] = cwd

    monkeypatch.setattr(ansible_engine, "run_command", fake_run_command)

    ansible_engine.run_ansible_playbook(playbook, workspace, limit="app-1")

    cmd = captured["command"]
    assert isinstance(cmd, list)
    assert "--limit" in cmd
    assert cmd[cmd.index("--limit") + 1] == "app-1"


def test_run_ansible_playbook_adds_verbosity_flag(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    (workspace / "config/ansible/inventory").mkdir(parents=True)
    (workspace / "config/ansible/playbooks").mkdir(parents=True)
    (workspace / "config/ansible/inventory/hosts.yml").write_text("---\nall:\n  hosts: {}\n")
    playbook = workspace / "config/ansible/playbooks/post-provision.yml"
    playbook.write_text("---\n- hosts: all\n  gather_facts: false\n  tasks: []\n")

    captured: dict[str, object] = {}

    def fake_run_command(command: list[str], cwd: Path | None = None) -> None:
        captured["command"] = command

    monkeypatch.setattr(ansible_engine, "run_command", fake_run_command)

    ansible_engine.run_ansible_playbook(playbook, workspace, verbosity=2)

    cmd = captured["command"]
    assert isinstance(cmd, list)
    assert "-vv" in cmd


def test_run_ansible_playbook_omits_verbosity_flag_by_default(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    (workspace / "config/ansible/inventory").mkdir(parents=True)
    (workspace / "config/ansible/playbooks").mkdir(parents=True)
    (workspace / "config/ansible/inventory/hosts.yml").write_text("---\nall:\n  hosts: {}\n")
    playbook = workspace / "config/ansible/playbooks/post-provision.yml"
    playbook.write_text("---\n- hosts: all\n  gather_facts: false\n  tasks: []\n")

    captured: dict[str, object] = {}

    def fake_run_command(command: list[str], cwd: Path | None = None) -> None:
        captured["command"] = command

    monkeypatch.setattr(ansible_engine, "run_command", fake_run_command)

    ansible_engine.run_ansible_playbook(playbook, workspace)

    cmd = captured["command"]
    assert isinstance(cmd, list)
    assert not any(arg.startswith("-v") for arg in cmd)
