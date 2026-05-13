from pathlib import Path

from typer.testing import CliRunner

import proxmox_compose.commands.doctor as doctor_module
import proxmox_compose.profiles as profiles_module
from proxmox_compose.cli import app


runner = CliRunner()


def _workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "repo"
    (ws / "config/ansible/playbooks").mkdir(parents=True)
    (ws / "config/ansible/playbooks/provision-infra.yml").write_text("- hosts: localhost")
    (ws / "config/ansible/playbooks/post-provision.yml").write_text("- hosts: all")
    (ws / "config/ansible/inventory").mkdir(parents=True)
    (ws / "config/ansible/inventory/static.yml").write_text("all: {}")
    return ws


def test_doctor_ok(monkeypatch, tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    profile_file = tmp_path / "profiles.yml"
    profile_file.write_text(
        """profiles:
  default:
    env:
      PROXMOX_ENDPOINT: https://proxmox.local:8006/api2/json
      PROXMOX_TOKEN_ID: ansible@pve!proxmox-compose
    secret_env_commands:
      PROXMOX_TOKEN_SECRET: "python -c 'print(\\\"secret\\\")'"
"""
    )
    monkeypatch.setattr(doctor_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(profiles_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(doctor_module.shutil, "which", lambda _: "/usr/bin/fake")

    result = runner.invoke(app, ["doctor", "--workspace", str(ws)])
    assert result.exit_code == 0, result.output
    assert "[ok] ansible-playbook" in result.output
    assert "[ok] PROXMOX_ENDPOINT" in result.output
    assert "Proxmox API token" in result.output


def test_doctor_fails_when_missing_binary(monkeypatch, tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    profile_file = tmp_path / "profiles.yml"
    profile_file.write_text(
        """profiles:
  default:
    env:
      PROXMOX_ENDPOINT: https://proxmox.local:8006/api2/json
      PROXMOX_TOKEN_ID: ansible@pve!proxmox-compose
    secret_env_commands:
      PROXMOX_TOKEN_SECRET: "python -c 'print(\\\"secret\\\")'"
"""
    )
    monkeypatch.setattr(doctor_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(profiles_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(
        doctor_module.shutil,
        "which",
        lambda binary: None if binary == "ansible-playbook" else "/usr/bin/fake",
    )

    result = runner.invoke(app, ["doctor", "--workspace", str(ws)])
    assert result.exit_code == 1
    assert "[missing] ansible-playbook" in result.output


def test_doctor_ok_with_secret_token_command(monkeypatch, tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    profile_file = tmp_path / "profiles.yml"
    profile_file.write_text(
        """profiles:
  default:
    secret_env_commands:
      PROXMOX_TOKEN_SECRET: "pass homelab/proxmox_token_secret"
    env:
      PROXMOX_ENDPOINT: https://proxmox.local:8006/api2/json
      PROXMOX_TOKEN_ID: ansible@pve!proxmox-compose
"""
    )
    monkeypatch.setattr(doctor_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(profiles_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(doctor_module.shutil, "which", lambda _: "/usr/bin/fake")

    result = runner.invoke(app, ["doctor", "--workspace", str(ws)])
    assert result.exit_code == 0, result.output
    assert "[ok] PROXMOX_TOKEN_SECRET" in result.output


def test_doctor_accepts_legacy_tf_var_profile_keys(monkeypatch, tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    profile_file = tmp_path / "profiles.yml"
    profile_file.write_text(
        """profiles:
  default:
    env:
      TF_VAR_proxmox_endpoint: https://proxmox.local:8006/api2/json
      TF_VAR_proxmox_token_id: terraform@pve!legacy
    secret_env_commands:
      TF_VAR_proxmox_token_secret: "python -c 'print(\\\"secret\\\")'"
"""
    )
    monkeypatch.setattr(doctor_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(profiles_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(doctor_module.shutil, "which", lambda _: "/usr/bin/fake")

    result = runner.invoke(app, ["doctor", "--workspace", str(ws)])
    assert result.exit_code == 0, result.output
    assert "[ok] PROXMOX_ENDPOINT (via TF_VAR_proxmox_endpoint)" in result.output


def test_doctor_fails_with_legacy_proxmox_auth_method(monkeypatch, tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    profile_file = tmp_path / "profiles.yml"
    profile_file.write_text(
        """profiles:
  default:
    proxmox_auth_method: ldap
    env:
      PROXMOX_ENDPOINT: https://proxmox.local:8006/api2/json
      PROXMOX_TOKEN_ID: ansible@pve!proxmox-compose
    secret_env_commands:
      PROXMOX_TOKEN_SECRET: "python -c 'print(\\\"secret\\\")'"
"""
    )
    monkeypatch.setattr(doctor_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(profiles_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(doctor_module.shutil, "which", lambda _: "/usr/bin/fake")

    result = runner.invoke(app, ["doctor", "--workspace", str(ws)])
    assert result.exit_code == 1
    assert "[error]" in result.output
    assert "proxmox_auth_method" in result.output


def test_doctor_fails_without_token_secret(monkeypatch, tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    profile_file = tmp_path / "profiles.yml"
    profile_file.write_text(
        """profiles:
  default:
    env:
      PROXMOX_ENDPOINT: https://proxmox.local:8006/api2/json
      PROXMOX_TOKEN_ID: ansible@pve!proxmox-compose
"""
    )
    monkeypatch.setattr(doctor_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(profiles_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(doctor_module.shutil, "which", lambda _: "/usr/bin/fake")

    result = runner.invoke(app, ["doctor", "--workspace", str(ws)])
    assert result.exit_code == 1
    assert "[missing] PROXMOX_TOKEN_SECRET" in result.output
