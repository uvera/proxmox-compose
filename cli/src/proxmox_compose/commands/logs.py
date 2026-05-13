"""Stream remote logs via SSH using merged Ansible inventory and profile SSH keys."""

from __future__ import annotations

import errno
import os
import shlex
from pathlib import Path, PurePosixPath
from typing import Any

import typer
import yaml

from proxmox_compose.profiles import get_profile_ssh_key
from proxmox_compose.workspace_manifest import (
    backend_from_manifest_logs,
    infer_logs_backend_from_vars,
    load_layered_ansible_defaults,
    load_workspace_manifest,
    manifest_logs_section,
    merge_logs_backend,
    resolve_default_inventory_host,
    validate_single_backend,
)


def flatten_inventory_hosts(inventory_yaml: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Map inventory hostname → host vars by walking nested ``all.children``.

    Duplicate hostnames in multiple groups shallow-merge vars (later overrides earlier).
    """
    out: dict[str, dict[str, Any]] = {}
    all_root = inventory_yaml.get("all")
    if not isinstance(all_root, dict):
        return out

    def walk_branch(branch: dict[str, Any]) -> None:
        hosts_section = branch.get("hosts") or {}
        if isinstance(hosts_section, dict):
            for hostname, vars_map in hosts_section.items():
                if not isinstance(hostname, str) or hostname == "":
                    continue
                if not isinstance(vars_map, dict):
                    vars_map = {}
                merged = dict(out.get(hostname, {}))
                merged.update(vars_map)
                out[hostname] = merged

        children = branch.get("children") or {}
        if not isinstance(children, dict):
            return
        for child in children.values():
            if isinstance(child, dict):
                walk_branch(child)

    walk_branch(all_root)
    return out


def resolve_connection(vars_map: dict[str, Any], inventory_name: str) -> tuple[str, str]:
    """Return (ansible_user, ansible_host) with sensible defaults."""
    user = vars_map.get("ansible_user") or vars_map.get("ansible_ssh_user") or ""
    ansible_host_any = vars_map.get("ansible_host")
    ansible_host_str = inventory_name if ansible_host_any in (None, "") else str(ansible_host_any)
    if not user:
        user = "root" if ansible_host_str.startswith("127.") else "debian"
    return str(user), ansible_host_str


def load_hosts(workspace: Path) -> dict[str, dict[str, Any]]:
    hosts_path = workspace / "config/ansible/inventory/hosts.yml"
    if not hosts_path.is_file():
        raise FileNotFoundError(errno.ENOENT, "Merged Ansible inventory not found", str(hosts_path))
    loaded = yaml.safe_load(hosts_path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        return {}
    return flatten_inventory_hosts(loaded)


def build_journalctl_remote_argv(
    unit: str,
    *,
    use_sudo: bool,
    follow: bool,
    since: str | None,
    lines: int | None,
    no_pager: bool = False,
) -> list[str]:
    cmd: list[str] = []
    if use_sudo:
        cmd.append("sudo")
    cmd.append("journalctl")
    if no_pager:
        cmd.append("--no-pager")
    cmd.extend(["-u", unit])
    if since:
        cmd.extend(["--since", since])
    if lines is not None:
        cmd.extend(["-n", str(lines)])
    if follow:
        cmd.append("-f")
    return cmd


def build_compose_logs_remote_argv(
    dest: str,
    compose_file: str,
    *,
    service: str | None,
    follow: bool,
) -> list[str]:
    """Run compose logs inside ``dest`` via bash (Compose v2 plugin or hyphenated fallback)."""
    body = build_compose_logs_shell_body(dest, compose_file, service=service, follow=follow)
    return compose_logs_bash_argv(body)


def _compose_workdir_and_file(dest: str, compose_file: str) -> tuple[str, str]:
    cf_p = PurePosixPath(compose_file.strip())
    if cf_p.is_absolute():
        return str(cf_p.parent), cf_p.name
    return dest.rstrip("/"), compose_file.strip()


def build_compose_logs_shell_body(
    dest: str,
    compose_file: str,
    *,
    service: str | None,
    follow: bool,
) -> str:
    workdir, file_arg = _compose_workdir_and_file(dest, compose_file)
    dq = shlex.quote(workdir)
    fq = shlex.quote(file_arg)
    svc = ""
    if service:
        svc = " " + shlex.quote(service)
    follow_flag = " --follow" if follow else ""
    v2_cmd = f"docker compose --file {fq} logs{follow_flag}{svc}"
    v1_cmd = f"docker-compose --file {fq} logs{follow_flag}{svc}"
    return (
        f"cd {dq} || {{ echo 'proxmox-compose logs: cannot cd into' {dq} >&2; exit 1; }}; "
        f"if docker compose version >/dev/null 2>&1; then "
        f"{v2_cmd}; "
        "elif command -v docker-compose >/dev/null 2>&1; then "
        f"{v1_cmd}; "
        'else '
        "echo 'proxmox-compose logs: need docker compose plugin (docker compose) or docker-compose binary on the host.' >&2; "
        "exit 127; fi"
    )


def compose_logs_bash_argv(shell_body: str) -> list[str]:
    """Run a bash snippet remotely (Compose uses this instead of splitting docker argv for ssh)."""
    return ["bash", "--norc", "--noprofile", "-c", shell_body]


def build_docker_logs_remote_argv(
    container: str,
    *,
    follow: bool,
) -> list[str]:
    cmd = ["docker", "logs"]
    if follow:
        cmd.append("-f")
    cmd.append(container)
    return cmd


def build_ssh_argv(
    *,
    user: str,
    ansible_host: str,
    ssh_key_path: Path | None,
    allocate_tty: bool,
    trust_new_hostkeys: bool = True,
) -> list[str]:
    argv: list[str] = ["ssh"]
    # With profile keys we use BatchMode=yes (non-interactive). Without this, connections to hosts
    # not yet in known_hosts fail with "Host key verification failed" instead of prompting.
    if trust_new_hostkeys:
        argv.extend(["-o", "StrictHostKeyChecking=accept-new"])
    if allocate_tty:
        argv.append("-t")
    if ssh_key_path is not None:
        argv.extend(["-o", "BatchMode=yes", "-i", str(ssh_key_path)])
    argv.append(f"{user}@{ansible_host}")
    return argv


def quote_argv_for_shell(argv: list[str]) -> str:
    """Concatenate argv into one shell-safe command prefix (no wrapping shell)."""
    return " ".join(shlex.quote(a) for a in argv)


def wrap_shell_pipeline_in_less(shell_body: str, *, follow: bool) -> list[str]:
    """Run ``shell_body`` (bash-safe snippet / one pipeline stage) piped into ``less``.

    Do not put ``LESS=-RF`` (the trailing ``F`` is quit-if-one-screen) — it clashes with ``less``'s
    ``+F`` follow command and can yield bogus pager behavior and swallowed Docker output.
    """
    less_open_arg = "+F" if follow else "+G"
    script = (
        f"{shell_body} 2>&1 | env LESSOPEN= LESSECLOSE= PAGER= GIT_PAGER= LESS=-RXQ "
        f"less {shlex.quote(less_open_arg)}"
    )
    return ["bash", "--norc", "--noprofile", "-c", script]


def build_remote_interactive_less_wrapper_argv(log_argv: list[str], follow: bool) -> list[str]:
    """Pipe a simple argv-based command into less (journald / ``docker logs``)."""
    return wrap_shell_pipeline_in_less(quote_argv_for_shell(log_argv), follow=follow)


def _count_backends(unit: Any, compose_dest: Any, container: Any) -> tuple[int, str | None]:
    selected: list[str] = []
    if unit is not None:
        selected.append("--unit")
    if compose_dest is not None:
        selected.append("--compose-dest")
    if container is not None:
        selected.append("--container")
    return len(selected), ", ".join(selected) if selected else ""


def logs_command(
    host: str | None = typer.Argument(
        default=None,
        metavar="[HOST]",
        help="Inventory hostname (merged hosts.yml); omitted uses .proxmox-compose.yml or exactly one inventory host.",
    ),
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Homelab repo root containing config/ansible/ (not an inventory HOST name).",
    ),
    profile: str = typer.Option(
        "default",
        "--profile",
        "-p",
        help="Profile from ~/.config/proxmox-compose/profiles.yml",
    ),
    unit: str | None = typer.Option(None, "--unit", help="Stream journalctl for systemd unit."),
    compose_dest: str | None = typer.Option(None, "--compose-dest", help="Docker Compose project directory on host."),
    compose_file: str | None = typer.Option(
        None,
        "--compose-file",
        help="Compose file relative to project directory (default docker-compose.yaml or inferred from inventory).",
    ),
    service: str | None = typer.Option(
        None,
        "--service",
        help="Optional compose service name (used with --compose-dest).",
    ),
    container: str | None = typer.Option(None, "--container", help="Stream docker logs for container name/id."),
    follow: bool = typer.Option(
        True,
        "--follow/--no-follow",
        "-f",
        help="Follow log output (journalctl/docker -f); disable for one-shot tail.",
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Journal only: forwarded to journalctl --since.",
    ),
    lines: int | None = typer.Option(
        None,
        "--lines",
        "-n",
        help="Journal only: forwarded as journalctl -n.",
    ),
    use_sudo: bool = typer.Option(
        False,
        "--sudo",
        help="Journal only: run sudo journalctl (when needed for privileged logs).",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-I",
        help="Browse logs with less on remote (TTY): scroll, /search. Uses less +G or +F with --follow. Requires bash+less.",
    ),
    strict_host_keys: bool = typer.Option(
        False,
        "--strict-host-keys",
        help=(
            "Do not pass StrictHostKeyChecking=accept-new (SSH default). "
            "Use if you prefer strict known_hosts (first connect may still fail with BatchMode + profile key)."
        ),
    ),
) -> None:
    """Stream logs on a remote host over SSH using merged inventory + profile SSH settings."""
    n_backends, backend_list = _count_backends(unit, compose_dest, container)
    if n_backends > 1:
        raise typer.BadParameter(
            f"Choose only one backend flag; got: {backend_list}",
            param_hint="backend",
        )

    ssh_key_path = get_profile_ssh_key(profile)
    workspace_r = workspace.resolve()

    manifest = load_workspace_manifest(workspace_r)
    logs_sec = manifest_logs_section(manifest)
    manifest_backend = backend_from_manifest_logs(logs_sec)

    try:
        merged = load_hosts(workspace_r)
    except FileNotFoundError as exc:
        path_hint = exc.filename if exc.filename is not None else str(workspace_r / "config/ansible/inventory/hosts.yml")
        raise typer.BadParameter(
            f"Merged inventory not found ({path_hint}). Run proxmox-compose inventory sync "
            f"--workspace {workspace_r}",
            param_hint=str(path_hint),
        ) from exc

    mh_raw = logs_sec.get("host")
    mh_str = mh_raw.strip() if isinstance(mh_raw, str) else None
    try:
        resolved_host = resolve_default_inventory_host(host, merged, mh_str)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="HOST") from exc

    vars_map = merged.get(resolved_host)
    if vars_map is None:
        hosts_path = workspace_r / "config/ansible/inventory/hosts.yml"
        known = ", ".join(sorted(merged.keys())) if merged else "(none)"
        empty_inv = ""
        if not merged:
            empty_inv = (
                "\n\nMerged inventory defines no hosts. Add entries under "
                "config/ansible/inventory/static.yml or host_vars metadata, then run:\n"
                f"  proxmox-compose inventory sync --workspace {workspace_r}"
            )
        raise typer.BadParameter(
            f"Host {resolved_host!r} not in merged inventory ({hosts_path}).\n"
            f"Known hosts: {known}.{empty_inv}\n\n"
            "After changing inventory, sync again.",
            param_hint="HOST",
        )

    layered = load_layered_ansible_defaults(workspace_r, resolved_host)
    inferred = infer_logs_backend_from_vars(layered)

    try:
        merged_backend = merge_logs_backend(
            cli_unit=unit,
            cli_compose_dest=compose_dest,
            cli_compose_file=compose_file,
            cli_service=service,
            cli_container=container,
            manifest_logs=manifest_backend,
            inferred=inferred,
        )
        validate_single_backend(merged_backend)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="backend") from exc

    eff_unit = merged_backend.unit
    eff_compose_dest = merged_backend.compose_dest
    eff_compose_file = merged_backend.compose_file or "docker-compose.yaml"
    eff_service = merged_backend.service
    eff_container = merged_backend.container

    user, ansible_host = resolve_connection(vars_map, resolved_host)

    allocate_tty = interactive or follow
    compose_shell: str | None = None
    if eff_unit is not None:
        remote = build_journalctl_remote_argv(
            eff_unit,
            use_sudo=use_sudo,
            follow=follow,
            since=since,
            lines=lines,
            no_pager=interactive,
        )
    elif eff_compose_dest is not None:
        compose_shell = build_compose_logs_shell_body(
            eff_compose_dest,
            eff_compose_file,
            service=eff_service,
            follow=follow,
        )
        remote = compose_logs_bash_argv(compose_shell)
    else:
        assert eff_container is not None
        remote = build_docker_logs_remote_argv(eff_container, follow=follow)

    ssh_argv = build_ssh_argv(
        user=user,
        ansible_host=ansible_host,
        ssh_key_path=ssh_key_path,
        allocate_tty=allocate_tty,
        trust_new_hostkeys=not strict_host_keys,
    )
    if interactive:
        if compose_shell is not None:
            remote = wrap_shell_pipeline_in_less(compose_shell, follow=follow)
        else:
            remote = build_remote_interactive_less_wrapper_argv(remote, follow=follow)
    full = ssh_argv + remote
    os.execvp("ssh", full)
