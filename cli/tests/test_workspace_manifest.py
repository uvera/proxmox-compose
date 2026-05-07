"""Tests for workspace manifest and logs default resolution."""

from pathlib import Path

import pytest
import yaml

from proxmox_compose.workspace_manifest import (
    ResolvedLogsBackend,
    backend_from_manifest_logs,
    infer_logs_backend_from_vars,
    load_layered_ansible_defaults,
    merge_logs_backend,
    resolve_default_inventory_host,
    validate_single_backend,
)


def test_resolve_default_inventory_host_explicit() -> None:
    assert resolve_default_inventory_host("h1", {"h1": {}, "h2": {}}, None) == "h1"


def test_resolve_default_inventory_host_manifest() -> None:
    assert resolve_default_inventory_host(None, {"a": {}, "b": {}}, "b") == "b"


def test_resolve_default_inventory_host_single() -> None:
    assert resolve_default_inventory_host(None, {"only": {}}, None) == "only"


def test_resolve_default_inventory_host_requires_disambiguation() -> None:
    with pytest.raises(ValueError, match="Pass HOST"):
        resolve_default_inventory_host(None, {"a": {}, "b": {}}, None)
    with pytest.raises(ValueError, match="example"):
        resolve_default_inventory_host(None, {"example": {}, "other": {}}, None)


def test_infer_single_systemd_unit() -> None:
    got = infer_logs_backend_from_vars(
        {"lxc_systemd_services": [{"name": "myapp", "exec_start": "/bin/true"}], "vm_compose_apps": []}
    )
    assert got is not None and got.unit == "myapp"


def test_infer_single_compose_app() -> None:
    got = infer_logs_backend_from_vars(
        {
            "lxc_systemd_services": [],
            "vm_compose_apps": [{"dest": "/opt/x", "compose_file_name": "compose.yaml"}],
        }
    )
    assert got is not None
    assert got.compose_dest == "/opt/x"
    assert got.compose_file == "compose.yaml"


def test_infer_ambiguous_two_units() -> None:
    assert (
        infer_logs_backend_from_vars(
            {
                "lxc_systemd_services": [
                    {"name": "a", "exec_start": "x"},
                    {"name": "b", "exec_start": "y"},
                ],
            }
        )
        is None
    )


def test_infer_jinja_skips() -> None:
    assert infer_logs_backend_from_vars({"lxc_systemd_services": [{"name": "{{ x }}", "exec_start": "y"}]}) is None


def test_merge_cli_unit_ignores_manifest_compose() -> None:
    m = ResolvedLogsBackend(unit=None, compose_dest="/opt/z", compose_file=None, service=None, container=None)
    inf = ResolvedLogsBackend(unit="inferred.service")
    out = merge_logs_backend(
        cli_unit="cli.service",
        cli_compose_dest=None,
        cli_compose_file=None,
        cli_service=None,
        cli_container=None,
        manifest_logs=m,
        inferred=inf,
    )
    assert out.unit == "cli.service"
    assert out.compose_dest is None


def test_merge_no_cli_uses_manifest_over_infer() -> None:
    m = ResolvedLogsBackend(unit="manifest.service")
    inf = ResolvedLogsBackend(unit="infer.service")
    out = merge_logs_backend(
        cli_unit=None,
        cli_compose_dest=None,
        cli_compose_file=None,
        cli_service=None,
        cli_container=None,
        manifest_logs=m,
        inferred=inf,
    )
    assert out.unit == "manifest.service"


def test_load_layered_ansible_defaults_order(tmp_path: Path) -> None:
    inv = tmp_path / "config/ansible/inventory"
    (inv / "group_vars/all").mkdir(parents=True)
    (inv / "host_vars").mkdir(parents=True)
    (inv / "group_vars/all/main.yml").write_text(
        yaml.safe_dump({"lxc_systemd_services": [{"name": "group", "exec_start": "x"}]}),
        encoding="utf-8",
    )
    (inv / "host_vars/h1.yml").write_text(
        yaml.safe_dump({"lxc_systemd_services": [{"name": "host", "exec_start": "y"}]}),
        encoding="utf-8",
    )
    merged = load_layered_ansible_defaults(tmp_path, "h1")
    assert merged["lxc_systemd_services"][0]["name"] == "host"


def test_backend_from_manifest_logs() -> None:
    b = backend_from_manifest_logs({"host": "x", "unit": "u.service", "compose_dest": "/a"})
    assert b.unit == "u.service" and b.compose_dest == "/a"


def test_validate_rejects_zero_or_two_backends() -> None:
    validate_single_backend(ResolvedLogsBackend(unit="a"))
    with pytest.raises(ValueError, match="Define a logs target"):
        validate_single_backend(ResolvedLogsBackend())
    with pytest.raises(ValueError, match="Multiple log backends"):
        validate_single_backend(ResolvedLogsBackend(unit="a", compose_dest="/b"))
