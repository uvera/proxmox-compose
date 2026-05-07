from pathlib import Path

from typer.testing import CliRunner

import proxmox_compose.commands.vault as vault_module
from proxmox_compose.cli import app

runner = CliRunner()


def _workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "repo"
    (ws / "config/ansible").mkdir(parents=True)
    return ws


def test_vault_edit_existing_file(monkeypatch, tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    vault_file = ws / "config/ansible/inventory/group_vars/all/vault.yml"
    vault_file.parent.mkdir(parents=True, exist_ok=True)
    vault_file.write_text("$ANSIBLE_VAULT;1.1;AES256\n")
    calls: list[tuple[list[str], Path | None]] = []

    def _fake_run(command: list[str], cwd: Path | None = None) -> None:
        calls.append((command, cwd))

    monkeypatch.setattr(vault_module, "run_command", _fake_run)
    result = runner.invoke(app, ["vault", "edit", "--workspace", str(ws)])

    assert result.exit_code == 0, result.output
    assert calls == [
        (
            ["ansible-vault", "edit", str(vault_file.resolve())],
            (ws / "config/ansible").resolve(),
        )
    ]


def test_vault_edit_creates_file_when_missing(monkeypatch, tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    vault_file = ws / "config/ansible/inventory/group_vars/all/vault.yml"
    calls: list[tuple[list[str], Path | None]] = []

    def _fake_run(command: list[str], cwd: Path | None = None) -> None:
        calls.append((command, cwd))

    monkeypatch.setattr(vault_module, "run_command", _fake_run)
    result = runner.invoke(app, ["vault", "edit", "--workspace", str(ws)])

    assert result.exit_code == 0, result.output
    assert vault_file.parent.exists()
    assert calls == [
        (
            ["ansible-vault", "create", str(vault_file.resolve())],
            (ws / "config/ansible").resolve(),
        )
    ]


def test_vault_edit_fails_without_create_if_missing(monkeypatch, tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    calls: list[tuple[list[str], Path | None]] = []

    def _fake_run(command: list[str], cwd: Path | None = None) -> None:
        calls.append((command, cwd))

    monkeypatch.setattr(vault_module, "run_command", _fake_run)
    result = runner.invoke(
        app,
        ["vault", "edit", "--workspace", str(ws), "--no-create-if-missing"],
    )

    assert result.exit_code == 2, result.output
    assert "Vault file not found" in result.output
    assert calls == []


def test_vault_edit_defaults_to_legacy_file_when_present(monkeypatch, tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    legacy_file = ws / "config/ansible/group_vars/all/vault.yml"
    legacy_file.parent.mkdir(parents=True, exist_ok=True)
    legacy_file.write_text("$ANSIBLE_VAULT;1.1;AES256\n")
    calls: list[tuple[list[str], Path | None]] = []

    def _fake_run(command: list[str], cwd: Path | None = None) -> None:
        calls.append((command, cwd))

    monkeypatch.setattr(vault_module, "run_command", _fake_run)
    result = runner.invoke(app, ["vault", "edit", "--workspace", str(ws)])

    assert result.exit_code == 0, result.output
    assert calls == [
        (
            ["ansible-vault", "edit", str(legacy_file.resolve())],
            (ws / "config/ansible").resolve(),
        )
    ]
