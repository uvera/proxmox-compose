from pathlib import Path

import proxmox_compose.profiles as profiles_module


def test_load_profile_env_with_secret_command_string(monkeypatch, tmp_path: Path) -> None:
    profile_file = tmp_path / "profiles.yml"
    profile_file.write_text(
        """profiles:
  default:
    env:
      PROXMOX_ENDPOINT: https://proxmox.local:8006/api2/json
    secret_env_commands:
      PROXMOX_TOKEN_SECRET: "python -c 'print(\\\"secret\\\")'"
"""
    )
    monkeypatch.setattr(profiles_module, "DEFAULT_PROFILE_FILE", profile_file)

    profiles_module.load_profile_env("default")

    assert profiles_module.os.environ["PROXMOX_ENDPOINT"] == "https://proxmox.local:8006/api2/json"
    assert profiles_module.os.environ["PROXMOX_TOKEN_SECRET"] == "secret"


def test_load_profile_env_with_secret_command_list(monkeypatch, tmp_path: Path) -> None:
    profile_file = tmp_path / "profiles.yml"
    profile_file.write_text(
        """profiles:
  default:
    secret_env_commands:
      PROXMOX_TOKEN_SECRET:
        - python
        - -c
        - print("secret-list")
"""
    )
    monkeypatch.setattr(profiles_module, "DEFAULT_PROFILE_FILE", profile_file)

    profiles_module.load_profile_env("default")

    assert profiles_module.os.environ["PROXMOX_TOKEN_SECRET"] == "secret-list"
