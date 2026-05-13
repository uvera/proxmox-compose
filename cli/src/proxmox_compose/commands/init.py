from pathlib import Path

import typer
import yaml

from proxmox_compose.scaffold import SCAFFOLD_FILES


def _write(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _bootstrap_profiles() -> None:
    profiles_file = Path("~/.config/proxmox-compose/profiles.yml").expanduser()
    if profiles_file.exists():
        return
    profiles_file.parent.mkdir(parents=True, exist_ok=True)
    default_profile = {
        "profiles": {
            "default": {
                "ssh_key_path": None,
                "secret_env_commands": {},
                "env": {
                    "PROXMOX_ENDPOINT": "https://proxmox.local:8006/api2/json",
                    "PROXMOX_TOKEN_ID": "ansible@pve!proxmox-compose",
                    "PROXMOX_TOKEN_SECRET": "change-me",
                    "PROXMOX_INSECURE": "true",
                }
            }
        }
    }
    profiles_file.write_text(yaml.safe_dump(default_profile, sort_keys=False))


def init_command(
    path: Path = typer.Option(
        Path("."),
        "--path",
        help="Target repository path to initialize.",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing scaffold files."),
    no_ai_files: bool = typer.Option(
        False,
        "--no-ai-files",
        help="Do not generate .cursor/rules, AGENTS.md, CLAUDE.md and docs guides.",
    ),
    init_git: bool = typer.Option(
        False,
        "--init-git",
        help="Initialize a new git repository if one does not exist.",
    ),
) -> None:
    """Scaffold a Proxmox Compose repository."""
    target = path.resolve()
    target.mkdir(parents=True, exist_ok=True)

    if not (target / ".git").exists():
        if init_git:
            import subprocess

            subprocess.run(["git", "init"], cwd=target, check=True)
        else:
            raise typer.BadParameter(
                "Target path is not a git repository. Use --init-git or run git init first."
            )

    for relative_path, content in SCAFFOLD_FILES.items():
        if no_ai_files and (
            relative_path.startswith(".cursor/")
            or relative_path in {"AGENTS.md", "CLAUDE.md"}
            or relative_path.startswith("docs/")
        ):
            continue
        _write(target / relative_path, content, force)

    _bootstrap_profiles()
    typer.echo(f"Initialized Proxmox Compose repository at {target}")
