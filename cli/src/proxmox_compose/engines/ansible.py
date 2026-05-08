from pathlib import Path

from proxmox_compose.engines.runner import run_command


def _common_cmd(
    playbook: Path,
    workspace: Path,
    ssh_key_path: Path | None = None,
    limit: str | None = None,
) -> list[str]:
    workspace = workspace.resolve()
    playbook = playbook.resolve()
    command = [
        "ansible-playbook",
        "-i",
        str(workspace / "config/ansible/inventory/hosts.yml"),
        str(playbook),
    ]
    if ssh_key_path:
        command.extend(["--private-key", str(ssh_key_path)])
    if limit:
        command.extend(["--limit", limit])
    return command


def _with_vault_password_file(command: list[str]) -> tuple[list[str], callable]:
    """
    If the user provides ANSIBLE_VAULT_PASSWORD (often via profiles.yml secret_env_commands),
    generate a temporary executable vault password script and pass it to ansible-playbook.

    We intentionally *don't* write the password to disk; the script prints it from the env.
    """
    import os
    import tempfile

    if os.environ.get("ANSIBLE_VAULT_PASSWORD_FILE") or os.environ.get("ANSIBLE_VAULT_PASSWORD_FILE") == "":
        return command, lambda: None

    if not os.environ.get("ANSIBLE_VAULT_PASSWORD"):
        return command, lambda: None

    fd, path = tempfile.mkstemp(prefix="proxmox-compose-vault-pass-", text=True)
    os.close(fd)

    script = """#!/usr/bin/env bash
set -euo pipefail
printf '%s' "${ANSIBLE_VAULT_PASSWORD:?missing ANSIBLE_VAULT_PASSWORD}"
"""
    p = Path(path)
    p.write_text(script)
    p.chmod(0o700)

    # Prefer explicit CLI flag so we don't mutate process env globally.
    new_command = command + ["--vault-password-file", str(p)]

    def cleanup() -> None:
        try:
            p.unlink(missing_ok=True)
        except TypeError:
            # Python < 3.8 compatibility (shouldn't happen here, but keep safe).
            try:
                if p.exists():
                    p.unlink()
            except FileNotFoundError:
                pass

    return new_command, cleanup


def run_ansible_check(
    playbook: Path,
    workspace: Path,
    ssh_key_path: Path | None = None,
    limit: str | None = None,
) -> None:
    cmd, cleanup = _with_vault_password_file(
        _common_cmd(playbook, workspace, ssh_key_path, limit=limit) + ["--check"]
    )
    try:
        run_command(
            cmd,
            cwd=(workspace / "config/ansible").resolve(),
        )
    finally:
        cleanup()


def run_ansible_playbook(
    playbook: Path,
    workspace: Path,
    ssh_key_path: Path | None = None,
    limit: str | None = None,
) -> None:
    cmd, cleanup = _with_vault_password_file(
        _common_cmd(playbook, workspace, ssh_key_path, limit=limit)
    )
    try:
        run_command(
            cmd,
            cwd=(workspace / "config/ansible").resolve(),
        )
    finally:
        cleanup()
