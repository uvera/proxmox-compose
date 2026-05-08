from pathlib import Path
import os
import shlex
import subprocess
from typing import Any

import yaml


DEFAULT_PROFILE_FILE = Path("~/.config/proxmox-compose/profiles.yml").expanduser()


def _load_profile_file() -> dict[str, Any]:
    if not DEFAULT_PROFILE_FILE.exists():
        return {}
    return yaml.safe_load(DEFAULT_PROFILE_FILE.read_text()) or {}


def get_profile(name: str) -> dict[str, Any]:
    data = _load_profile_file()
    return data.get("profiles", {}).get(name, {})


def get_profile_secret_env_commands(name: str) -> dict[str, Any]:
    profile = get_profile(name)
    commands = profile.get("secret_env_commands", {})
    if isinstance(commands, dict):
        return commands
    return {}


def _resolve_secret_command(command_spec: Any) -> str:
    if isinstance(command_spec, list):
        command = [str(part) for part in command_spec]
    else:
        command = shlex.split(str(command_spec))
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        joined = " ".join(command)
        stderr = result.stderr.strip()
        raise RuntimeError(f"Failed to resolve secret command ({joined}): {stderr}")
    return result.stdout.strip()


def load_profile_env(name: str) -> None:
    profile = get_profile(name)
    env_vars = profile.get("env", {})
    for key, value in env_vars.items():
        os.environ[key] = str(value)

    secret_env_commands = get_profile_secret_env_commands(name)
    for key, command_spec in secret_env_commands.items():
        os.environ[str(key)] = _resolve_secret_command(command_spec)


def get_profile_ssh_key(name: str) -> Path | None:
    profile = get_profile(name)
    ssh_key_path = profile.get("ssh_key_path")
    if not ssh_key_path:
        return None
    return Path(str(ssh_key_path)).expanduser()


def get_proxmox_auth_method(name: str) -> str:
    profile = get_profile(name)
    raw = profile.get("proxmox_auth_method", "api_token")
    if raw is None or raw == "":
        return "api_token"
    method = str(raw).strip()
    if method not in ("api_token", "password"):
        raise ValueError(
            f"profiles.{name}.proxmox_auth_method must be 'api_token' or 'password', got {raw!r}"
        )
    return method
