from pathlib import Path

import typer

from proxmox_compose.scaffold import SCAFFOLD_FILES


scaffold_app = typer.Typer(help="Scaffold utilities.")


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

    typer.echo(f"Synchronized {written} scaffold files in {target}")
