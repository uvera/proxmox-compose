from pathlib import Path
import os
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


def load_profile_env(name: str) -> None:
    profile = get_profile(name)
    env_vars = profile.get("env", {})
    for key, value in env_vars.items():
        os.environ[key] = str(value)


def get_profile_ssh_key(name: str) -> Path | None:
    profile = get_profile(name)
    ssh_key_path = profile.get("ssh_key_path")
    if not ssh_key_path:
        return None
    return Path(str(ssh_key_path)).expanduser()
