"""Optional workspace-level YAML (`.proxmox-compose.yml`) for CLI defaults."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Prefer dotfile; fallback filename for repos that avoid dot-prefix.
WORKSPACE_MANIFEST_NAMES = (".proxmox-compose.yml", "proxmox-compose.yml")


def load_workspace_manifest(workspace: Path) -> dict[str, Any]:
    workspace = workspace.resolve()
    for name in WORKSPACE_MANIFEST_NAMES:
        path = workspace / name
        if not path.is_file():
            continue
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    return {}


def manifest_logs_section(manifest: dict[str, Any]) -> dict[str, Any]:
    logs = manifest.get("logs")
    return logs if isinstance(logs, dict) else {}


def load_layered_ansible_defaults(workspace: Path, inventory_host: str) -> dict[str, Any]:
    """Shallow-merge group_vars/all/main.yml then host_vars/<host>.{yml,yaml}.

    Mirrors common single-homelab layout; does not load every Ansible group layering.
    """
    merged: dict[str, Any] = {}
    inv = workspace / "config/ansible/inventory"
    gv = inv / "group_vars/all/main.yml"
    if gv.is_file():
        data = yaml.safe_load(gv.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            merged.update(data)
    for ext in (".yml", ".yaml"):
        hv = inv / "host_vars" / f"{inventory_host}{ext}"
        if hv.is_file():
            data = yaml.safe_load(hv.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                merged.update(data)
            break
    return merged


def contains_jinja(value: Any) -> bool:
    if isinstance(value, str):
        return "{{" in value or "{%" in value
    return False


@dataclass
class ResolvedLogsBackend:
    unit: str | None = None
    compose_dest: str | None = None
    compose_file: str | None = None
    service: str | None = None
    container: str | None = None


def _backend_count(b: ResolvedLogsBackend) -> int:
    n = 0
    if b.unit is not None:
        n += 1
    if b.compose_dest is not None:
        n += 1
    if b.container is not None:
        n += 1
    return n


def infer_logs_backend_from_vars(layered: dict[str, Any]) -> ResolvedLogsBackend | None:
    """If inventory vars point to exactly one log target, return it; else None.

    Returns None when ambiguous, empty, or when critical fields use Jinja (cannot evaluate locally).
    """
    services_raw = layered.get("lxc_systemd_services") or []
    apps_raw = layered.get("vm_compose_apps") or []
    if not isinstance(services_raw, list):
        services_raw = []
    if not isinstance(apps_raw, list):
        apps_raw = []

    services: list[dict[str, Any]] = []
    for item in services_raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or name.strip() == "":
            continue
        if contains_jinja(name):
            return None
        services.append(item)

    apps: list[dict[str, Any]] = []
    for item in apps_raw:
        if not isinstance(item, dict):
            continue
        dest = item.get("dest")
        if not isinstance(dest, str) or dest.strip() == "":
            continue
        if contains_jinja(dest):
            return None
        cfn = item.get("compose_file_name")
        if cfn is not None and contains_jinja(cfn):
            return None
        apps.append(item)

    n_s, n_a = len(services), len(apps)
    if n_s >= 1 and n_a >= 1:
        return None
    if n_s > 1 or n_a > 1:
        return None
    if n_s == 1:
        return ResolvedLogsBackend(unit=services[0]["name"])
    if n_a == 1:
        app = apps[0]
        fname = app.get("compose_file_name")
        file_guess = fname if isinstance(fname, str) and fname.strip() else "docker-compose.yaml"
        return ResolvedLogsBackend(compose_dest=app["dest"], compose_file=file_guess, service=None)
    return None


def backend_from_manifest_logs(logs: dict[str, Any]) -> ResolvedLogsBackend:
    def s(key: str) -> str | None:
        v = logs.get(key)
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            return str(v)
        return v

    return ResolvedLogsBackend(
        unit=s("unit"),
        compose_dest=s("compose_dest"),
        compose_file=s("compose_file"),
        service=s("service"),
        container=s("container"),
    )


def merge_logs_backend(
    *,
    cli_unit: str | None,
    cli_compose_dest: str | None,
    cli_compose_file: str | None,
    cli_service: str | None,
    cli_container: str | None,
    manifest_logs: ResolvedLogsBackend,
    inferred: ResolvedLogsBackend | None,
) -> ResolvedLogsBackend:
    """Resolve backend: explicit CLI picks one spine; otherwise manifest, then inferred vars."""
    inf = inferred or ResolvedLogsBackend()
    cli_pick = ResolvedLogsBackend(
        unit=cli_unit,
        compose_dest=cli_compose_dest,
        container=cli_container,
    )
    n_cli = _backend_count(cli_pick)
    if n_cli == 1:
        if cli_pick.unit is not None:
            return ResolvedLogsBackend(unit=cli_pick.unit)
        if cli_pick.container is not None:
            return ResolvedLogsBackend(container=cli_pick.container)
        cf = (
            cli_compose_file or manifest_logs.compose_file or inf.compose_file or "docker-compose.yaml"
        )
        svc = cli_service or manifest_logs.service or inf.service
        return ResolvedLogsBackend(
            compose_dest=cli_pick.compose_dest,
            compose_file=cf,
            service=svc,
        )
    if n_cli > 1:
        return cli_pick

    out = ResolvedLogsBackend(
        unit=manifest_logs.unit or inf.unit,
        compose_dest=manifest_logs.compose_dest or inf.compose_dest,
        compose_file=None,
        service=manifest_logs.service or inf.service,
        container=manifest_logs.container or inf.container,
    )
    if out.compose_dest:
        out.compose_file = (
            cli_compose_file or manifest_logs.compose_file or inf.compose_file or "docker-compose.yaml"
        )
    return out


def resolve_default_inventory_host(host_arg: str | None, merged_hosts: dict[str, Any], manifest_host: str | None) -> str:
    if host_arg:
        return host_arg
    mh = manifest_host.strip() if isinstance(manifest_host, str) else None
    if mh:
        return mh
    keys = sorted(merged_hosts.keys())
    if len(keys) == 1:
        return keys[0]
    known = ", ".join(keys) if keys else "(none)"
    raise ValueError(
        "Pass HOST (e.g. one of: "
        + known
        + "), set logs.host in .proxmox-compose.yml or proxmox-compose.yml, or reduce to exactly one "
        "inventory host (currently "
        f"{len(keys)}). Run inventory sync if hosts.yml is stale."
    )


def normalized_backend(backend: ResolvedLogsBackend) -> ResolvedLogsBackend:
    """Compose-related fields only apply when ``compose_dest`` is set."""
    if backend.compose_dest:
        return ResolvedLogsBackend(
            unit=backend.unit,
            compose_dest=backend.compose_dest,
            compose_file=backend.compose_file,
            service=backend.service,
            container=backend.container,
        )
    return ResolvedLogsBackend(unit=backend.unit, container=backend.container)


def validate_single_backend(backend: ResolvedLogsBackend) -> None:
    b = normalized_backend(backend)
    n = _backend_count(b)
    if n == 0:
        raise ValueError(
            "Define a logs target: pass --unit, --compose-dest, or --container; "
            "or set logs: in .proxmox-compose.yml; "
            "or add a single lxc_systemd_services or vm_compose_apps entry for this host in inventory vars."
        )
    if n > 1:
        raise ValueError(
            "Multiple log backends configured; pass only one of --unit, --compose-dest, or --container "
            "(or set a single logs.* backend in .proxmox-compose.yml)."
        )
