"""Tests for proxmox-compose logs helpers."""

from pathlib import Path

import pytest
import shlex

from proxmox_compose.commands.logs import (
    build_compose_logs_remote_argv,
    build_compose_logs_shell_body,
    build_docker_logs_remote_argv,
    build_journalctl_remote_argv,
    build_remote_interactive_less_wrapper_argv,
    build_ssh_argv,
    flatten_inventory_hosts,
    load_hosts,
    quote_argv_for_shell,
    resolve_connection,
    wrap_shell_pipeline_in_less,
)


def test_flatten_inventory_hosts_flat_and_nested_merge() -> None:
    yaml_data = {
        "all": {
            "children": {
                "debian_lxcs": {
                    "hosts": {
                        "app1": {
                            "ansible_host": "10.0.1.10",
                            "ansible_user": "root",
                        }
                    },
                },
                "regional": {
                    "children": {
                        "debian_vms": {
                            "hosts": {
                                "app1": {"ansible_user": "debian"},  # later merge augments same host
                            }
                        }
                    },
                },
            }
        }
    }
    out = flatten_inventory_hosts(yaml_data)
    assert "app1" in out
    assert out["app1"]["ansible_host"] == "10.0.1.10"
    assert out["app1"]["ansible_user"] == "debian"


def test_resolve_connection_defaults() -> None:
    assert resolve_connection({}, "somename.example") == ("debian", "somename.example")
    assert resolve_connection({"ansible_host": "10.10.10.10"}, "h") == ("debian", "10.10.10.10")
    assert resolve_connection({"ansible_user": "alice", "ansible_host": "srv"}, "h") == ("alice", "srv")


def test_build_journalctl_remote_argv_full() -> None:
    argv = build_journalctl_remote_argv(
        "mysvc.service",
        use_sudo=True,
        follow=False,
        since="today",
        lines=50,
    )
    assert argv == ["sudo", "journalctl", "-u", "mysvc.service", "--since", "today", "-n", "50"]


def test_build_journalctl_remote_argv_follow_only() -> None:
    argv = build_journalctl_remote_argv(
        "foo",
        use_sudo=False,
        follow=True,
        since=None,
        lines=None,
    )
    assert argv == ["journalctl", "-u", "foo", "-f"]


def test_build_journalctl_remote_argv_no_pager() -> None:
    argv = build_journalctl_remote_argv(
        "svc",
        use_sudo=False,
        follow=False,
        since=None,
        lines=None,
        no_pager=True,
    )
    ju = argv.index("journalctl")
    assert argv[ju + 1] == "--no-pager"
    assert argv[ju + 2 : ju + 4] == ["-u", "svc"]


def test_build_compose_logs_remote_argv() -> None:
    argv = build_compose_logs_remote_argv(
        "/opt/frigate",
        "compose.yaml",
        service="core",
        follow=True,
    )
    assert argv[:4] == ["bash", "--norc", "--noprofile", "-c"]
    script = argv[4]
    assert "cd '/opt/frigate'" in script or "cd /opt/frigate" in script
    assert "docker compose" in script
    assert "'compose.yaml'" in script or "compose.yaml" in script
    assert " logs " in script or " logs" in script
    assert "'core'" in script or " core" in script
    assert "--follow" in script
    assert "docker-compose" in script


def test_build_compose_logs_no_service() -> None:
    argv = build_compose_logs_remote_argv(
        "/app",
        "docker-compose.yaml",
        service=None,
        follow=False,
    )
    assert argv[:4] == ["bash", "--norc", "--noprofile", "-c"]
    script = argv[4]
    assert "cd " in script and "/app" in script
    assert "docker compose" in script and " logs" in script
    assert "--follow" not in script


def test_build_docker_logs_remote_argv() -> None:
    assert build_docker_logs_remote_argv("pg", follow=False) == ["docker", "logs", "pg"]
    assert build_docker_logs_remote_argv("pg", follow=True) == ["docker", "logs", "-f", "pg"]


def test_build_ssh_argv_without_key_tty() -> None:
    argv = build_ssh_argv(
        user="root",
        ansible_host="10.0.0.5",
        ssh_key_path=None,
        allocate_tty=True,
    )
    assert argv == ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-t", "root@10.0.0.5"]


def test_build_ssh_argv_strict_skips_accept_new() -> None:
    argv = build_ssh_argv(
        user="root",
        ansible_host="10.0.0.5",
        ssh_key_path=None,
        allocate_tty=False,
        trust_new_hostkeys=False,
    )
    assert argv == ["ssh", "root@10.0.0.5"]


def test_build_ssh_argv_with_key_no_tty() -> None:
    key = Path("/tmp/id_ed25519")
    argv = build_ssh_argv(
        user="debian",
        ansible_host="v.local",
        ssh_key_path=key,
        allocate_tty=False,
    )
    assert argv == [
        "ssh",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "BatchMode=yes",
        "-i",
        "/tmp/id_ed25519",
        "debian@v.local",
    ]


def test_load_hosts_roundtrip_tmp(tmp_path: Path) -> None:
    inv_dir = tmp_path / "config" / "ansible" / "inventory"
    inv_dir.mkdir(parents=True)
    inv_file = inv_dir / "hosts.yml"
    inv_file.write_text(
        """
all:
  children:
    g:
      hosts:
        h:
          ansible_host: 192.168.1.99
          ansible_user: alice
"""
        ,
        encoding="utf-8",
    )
    hosts = load_hosts(tmp_path)
    assert hosts["h"]["ansible_host"] == "192.168.1.99"
    assert hosts["h"]["ansible_user"] == "alice"


def test_load_hosts_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError) as ei:
        load_hosts(tmp_path)
    expected = (tmp_path.resolve() / "config/ansible/inventory/hosts.yml").as_posix()
    assert ei.value.filename == expected


def test_flatten_inventory_hosts_empty_all() -> None:
    assert flatten_inventory_hosts({"all": {"children": {}}}) == {}
    assert flatten_inventory_hosts({}) == {}


def test_quote_argv_for_shell_quotes_spaces() -> None:
    quoted = quote_argv_for_shell(["journalctl", "-u", "a b"])
    assert quoted == "journalctl -u " + shlex.quote("a b")
    assert quoted == "journalctl -u 'a b'"


def test_build_remote_interactive_less_wrapper_argv_follow_follows_with_plus_f() -> None:
    bash_part = build_remote_interactive_less_wrapper_argv(
        ["journalctl", "--no-pager", "-u", "my.service", "-f"],
        follow=True,
    )
    script = bash_part[-1]
    assert bash_part[:-1] == ["bash", "--norc", "--noprofile", "-c"]
    assert "| env LESSOPEN= LESSECLOSE= PAGER= GIT_PAGER= LESS=-RXQ less " in script
    assert script.endswith("+F")
    log_prefix = quote_argv_for_shell(["journalctl", "--no-pager", "-u", "my.service", "-f"])
    assert script.startswith(log_prefix + " 2>&1 |")


def test_build_remote_interactive_less_wrapper_argv_snap_opens_plus_g() -> None:
    script = build_remote_interactive_less_wrapper_argv(["docker", "logs", "c1"], follow=False)[-1]
    assert "| env LESSOPEN= LESSECLOSE= PAGER= GIT_PAGER= LESS=-RXQ less " in script
    assert script.endswith("+G")


def test_interactive_compose_script_keeps_logs_subcommand() -> None:
    sh = build_compose_logs_shell_body(
        "/opt/frigate",
        "docker-compose.yaml",
        service=None,
        follow=True,
    )
    script = wrap_shell_pipeline_in_less(sh, follow=True)[-1]
    assert "cd " in script and "/opt/frigate" in script
    assert "docker compose" in script
    assert " logs" in script
    assert "--follow" in script
    assert "docker-compose" in script
    assert "LESS=-RXQ" in script
