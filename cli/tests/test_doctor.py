from pathlib import Path

from typer.testing import CliRunner

import proxmox_compose.commands.doctor as doctor_module
import proxmox_compose.profiles as profiles_module
from proxmox_compose.cli import app


runner = CliRunner()


def _workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "repo"
    (ws / "infra/terraform/environments/homelab").mkdir(parents=True)
    (ws / "infra/terraform/environments/homelab/main.tf").write_text("module \"x\" {}")
    (ws / "config/ansible/playbooks").mkdir(parents=True)
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
      TF_VAR_proxmox_endpoint: https://proxmox.local:8006/api2/json
      TF_VAR_proxmox_token_id: terraform@pve!proxmox-compose
    secret_env_commands:
      TF_VAR_proxmox_token_secret: "python -c 'print(\\\"secret\\\")'"
"""
    )
    monkeypatch.setattr(doctor_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(profiles_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(doctor_module.shutil, "which", lambda _: "/usr/bin/fake")

    result = runner.invoke(app, ["doctor", "--workspace", str(ws)])
    assert result.exit_code == 0, result.output
    assert "[ok] terraform" in result.output
    assert "[ok] TF_VAR_proxmox_endpoint" in result.output
    assert "Proxmox API token" in result.output


def test_doctor_fails_when_missing_binary(monkeypatch, tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    profile_file = tmp_path / "profiles.yml"
    profile_file.write_text(
        """profiles:
  default:
    env:
      TF_VAR_proxmox_endpoint: https://proxmox.local:8006/api2/json
      TF_VAR_proxmox_token_id: terraform@pve!proxmox-compose
    secret_env_commands:
      TF_VAR_proxmox_token_secret: "python -c 'print(\\\"secret\\\")'"
"""
    )
    monkeypatch.setattr(doctor_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(profiles_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(
        doctor_module.shutil,
        "which",
        lambda binary: None if binary == "terraform" else "/usr/bin/fake",
    )

    result = runner.invoke(app, ["doctor", "--workspace", str(ws)])
    assert result.exit_code == 1
    assert "[missing] terraform" in result.output


def test_doctor_ok_with_secret_token_command(monkeypatch, tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    profile_file = tmp_path / "profiles.yml"
    profile_file.write_text(
        """profiles:
  default:
    secret_env_commands:
      TF_VAR_proxmox_token_secret: "pass homelab/proxmox_token_secret"
    env:
      TF_VAR_proxmox_endpoint: https://proxmox.local:8006/api2/json
      TF_VAR_proxmox_token_id: terraform@pve!proxmox-compose
"""
    )
    monkeypatch.setattr(doctor_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(profiles_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(doctor_module.shutil, "which", lambda _: "/usr/bin/fake")

    result = runner.invoke(app, ["doctor", "--workspace", str(ws)])
    assert result.exit_code == 0, result.output
    assert "[ok] TF_VAR_proxmox_token_secret" in result.output


def test_doctor_fails_with_legacy_proxmox_auth_method(monkeypatch, tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    profile_file = tmp_path / "profiles.yml"
    profile_file.write_text(
        """profiles:
  default:
    proxmox_auth_method: ldap
    env:
      TF_VAR_proxmox_endpoint: https://proxmox.local:8006/api2/json
      TF_VAR_proxmox_token_id: terraform@pve!proxmox-compose
    secret_env_commands:
      TF_VAR_proxmox_token_secret: "python -c 'print(\\\"secret\\\")'"
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
      TF_VAR_proxmox_endpoint: https://proxmox.local:8006/api2/json
      TF_VAR_proxmox_token_id: terraform@pve!proxmox-compose
"""
    )
    monkeypatch.setattr(doctor_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(profiles_module, "DEFAULT_PROFILE_FILE", profile_file)
    monkeypatch.setattr(doctor_module.shutil, "which", lambda _: "/usr/bin/fake")

    result = runner.invoke(app, ["doctor", "--workspace", str(ws)])
    assert result.exit_code == 1
    assert "[missing] TF_VAR_proxmox_token_secret" in result.output
