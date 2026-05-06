from pathlib import Path

from typer.testing import CliRunner

from proxmox_compose.cli import app


runner = CliRunner()


def test_init_scaffolds_git_repo_and_core_files(tmp_path: Path) -> None:
    target = tmp_path / "homelab"
    result = runner.invoke(app, ["init", "--path", str(target), "--init-git"])

    assert result.exit_code == 0, result.output
    assert (target / ".git").exists()
    assert (target / "infra/terraform/environments/homelab/providers.tf").exists()
    assert (target / "config/ansible/playbooks/post-provision.yml").exists()
    assert (target / ".cursor/rules/proxmox-compose.mdc").exists()
    assert (target / "AGENTS.md").exists()
    assert (target / "CLAUDE.md").exists()


def test_init_can_skip_ai_files(tmp_path: Path) -> None:
    target = tmp_path / "without-ai"
    result = runner.invoke(
        app,
        ["init", "--path", str(target), "--init-git", "--no-ai-files"],
    )

    assert result.exit_code == 0, result.output
    assert not (target / ".cursor/rules/proxmox-compose.mdc").exists()
    assert not (target / "AGENTS.md").exists()
    assert not (target / "CLAUDE.md").exists()
