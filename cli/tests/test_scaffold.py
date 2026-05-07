from pathlib import Path

from typer.testing import CliRunner

from proxmox_compose.cli import app


runner = CliRunner()


def test_scaffold_sync_overwrites_existing_files(tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    (workspace / ".git").mkdir(parents=True)
    target_file = workspace / "config/ansible/playbooks/post-provision.yml"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("outdated")

    result = runner.invoke(app, ["scaffold", "sync", "--workspace", str(workspace)])

    assert result.exit_code == 0, result.output
    assert target_file.exists()
    assert target_file.read_text() != "outdated"
    assert "Synchronized" in result.output


def test_scaffold_sync_can_skip_ai_files(tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    (workspace / ".git").mkdir(parents=True)
    docs_file = workspace / "docs/lxc-service-onboarding.md"
    docs_file.parent.mkdir(parents=True, exist_ok=True)
    docs_file.write_text("keep me")

    result = runner.invoke(
        app,
        ["scaffold", "sync", "--workspace", str(workspace), "--no-ai-files"],
    )

    assert result.exit_code == 0, result.output
    assert docs_file.read_text() == "keep me"
