"""Build log target choices from Ansible-style inventory vars and optional SSH discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JournalTarget:
    unit: str


@dataclass(frozen=True)
class ComposeTarget:
    dest: str
    compose_file: str
    service: str | None = None


@dataclass(frozen=True)
class ContainerTarget:
    name: str


LogTarget = JournalTarget | ComposeTarget | ContainerTarget


def targets_from_inventory_vars(vars_layered: dict[str, Any]) -> list[LogTarget]:
    """Targets derivable purely from YAML (no SSH)."""
    out: list[LogTarget] = []

    svc_raw = vars_layered.get("lxc_systemd_services") or []
    if isinstance(svc_raw, list):
        for item in svc_raw:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                out.append(JournalTarget(name.strip()))

    apps_raw = vars_layered.get("vm_compose_apps") or []
    if isinstance(apps_raw, list):
        for item in apps_raw:
            if not isinstance(item, dict):
                continue
            dest = item.get("dest")
            if not isinstance(dest, str) or not dest.strip():
                continue
            cfn = item.get("compose_file_name")
            fname = cfn.strip() if isinstance(cfn, str) and cfn.strip() else "docker-compose.yaml"
            # Full stack logs (no single-service pick here)
            out.append(ComposeTarget(dest.strip(), fname, None))

    return out


def append_container_targets_from_lines(out: list[LogTarget], lines: str) -> None:
    for line in lines.splitlines():
        name = line.strip()
        if name:
            out.append(ContainerTarget(name))
