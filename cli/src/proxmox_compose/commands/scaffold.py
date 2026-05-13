from pathlib import Path

import typer

from proxmox_compose.scaffold import SCAFFOLD_FILES

LEGACY_SCAFFOLD_DIRS = ("infra",)


scaffold_app = typer.Typer(help="Scaffold utilities.")


def _prune_legacy_paths(target: Path) -> int:
    removed = 0
    for relative in LEGACY_SCAFFOLD_DIRS:
        legacy_dir = (target / relative).resolve()
        if not legacy_dir.exists() or not legacy_dir.is_dir():
            continue
        for child in sorted(legacy_dir.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
                removed += 1
            elif child.is_dir():
                try:
                    child.rmdir()
                except OSError:
                    pass
        try:
            legacy_dir.rmdir()
            removed += 1
        except OSError:
            pass

        # Clean up empty parent folders (for example infra/).
        parent = legacy_dir.parent
        while parent != target and parent.exists():
            try:
                parent.rmdir()
                removed += 1
            except OSError:
                break
            parent = parent.parent
    return removed


@scaffold_app.command("sync")
def scaffold_sync_command(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Repository root that contains scaffold-managed files.",
    ),
    no_ai_files: bool = typer.Option(
        False,
        "--no-ai-files",
        help="Skip .cursor/rules, AGENTS.md, CLAUDE.md and docs guides.",
    ),
) -> None:
    """Overwrite scaffold-managed files with latest templates."""
    target = workspace.resolve()
    written = 0
    removed = _prune_legacy_paths(target)

    for relative_path, content in SCAFFOLD_FILES.items():
        if no_ai_files and (
            relative_path.startswith(".cursor/")
            or relative_path in {"AGENTS.md", "CLAUDE.md"}
            or relative_path.startswith("docs/")
        ):
            continue

        destination = target / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)
        written += 1

    typer.echo(f"Synchronized {written} scaffold files in {target} (removed {removed} legacy paths)")
