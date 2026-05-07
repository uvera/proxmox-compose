#!/usr/bin/env python3
"""Reconcile Tailscale Serve/Funnel with a desired JSON list (idempotent)."""
from __future__ import annotations

import json
import subprocess
import sys
from typing import Any


def run_tailscale(argv: list[str]) -> None:
    subprocess.run(["tailscale", *argv], check=True, text=True)


def load_json_cmd(argv: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        ["tailscale", *argv],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return {}
    raw = (proc.stdout or "").strip()
    if not raw:
        return {}
    return json.loads(raw)


def tcp_entry(tcp_map: dict[str, Any], port: int) -> dict[str, Any]:
    if not tcp_map:
        return {}
    key = str(port)
    entry = tcp_map.get(key)
    if isinstance(entry, dict):
        return entry
    # Some encodings may use int keys in JSON (non-standard but tolerate).
    entry = tcp_map.get(port)
    return entry if isinstance(entry, dict) else {}


def protocol_for_port(tcp_map: dict[str, Any], port: int) -> str:
    t = tcp_entry(tcp_map, port)
    if t.get("HTTPS"):
        return "https"
    if t.get("HTTP"):
        return "http"
    if t.get("TCPForward"):
        if t.get("TerminateTLS"):
            return "tls-terminated-tcp"
        return "tcp"
    return "https"


def normalize_mount(mount: str | None) -> str:
    m = (mount or "/").strip() or "/"
    if not m.startswith("/"):
        m = "/" + m
    return m.rstrip("/") or "/"


def canon_target(target: str) -> str:
    s = str(target).strip()
    if s.startswith("http://") or s.startswith("https://"):
        return s.rstrip("/") or s
    # "3300" or "127.0.0.1:3300"
    if s.isdigit():
        return f"http://127.0.0.1:{s}"
    if "://" not in s:
        return f"http://{s}".rstrip("/") or f"http://{s}"
    return s.rstrip("/") or s


def parse_current(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    allow = cfg.get("AllowFunnel") or {}
    web = cfg.get("Web") or {}
    tcp_map = cfg.get("TCP") or {}

    for hp, wsc in web.items():
        if not isinstance(wsc, dict):
            continue
        hp_s = str(hp)
        if ":" not in hp_s:
            continue
        port_s = hp_s.rsplit(":", 1)[-1]
        try:
            port = int(port_s)
        except ValueError:
            continue
        proto = protocol_for_port(tcp_map, port)
        funnel = bool(allow.get(hp_s) or allow.get(hp))
        handlers = wsc.get("Handlers") or {}
        if not isinstance(handlers, dict):
            continue
        for mount, h in handlers.items():
            if not isinstance(h, dict):
                continue
            proxy = h.get("Proxy")
            if not proxy:
                continue
            rules.append(
                {
                    "port": port,
                    "protocol": proto,
                    "mount": normalize_mount(str(mount)),
                    "target": canon_target(str(proxy)),
                    "funnel": funnel,
                }
            )

    # Raw TCP / TLS-terminated forwards without Web handlers are not represented
    # in Web; skip unless we add a second pass — v1 focuses on HTTP(S) Serve/Funnel.

    return rules


def normalize_desired(entry: dict[str, Any]) -> dict[str, Any] | None:
    if "port" not in entry:
        return None
    port = int(entry["port"])
    proto = str(entry.get("protocol") or "https").lower()
    if proto not in {"https", "http", "tcp", "tls-terminated-tcp"}:
        raise SystemExit(f"Unsupported protocol {proto!r} in tailscale_serve entry")
    mount = normalize_mount(entry.get("mount"))
    target = canon_target(str(entry.get("target") or ""))
    if not target:
        raise SystemExit("tailscale_serve entry missing target")
    funnel = bool(entry.get("funnel", False))
    if funnel and proto == "http":
        raise SystemExit("tailscale_serve: funnel: true does not support protocol: http (use https or tcp / tls-terminated-tcp)")
    return {
        "port": port,
        "protocol": proto,
        "mount": mount,
        "target": target,
        "funnel": funnel,
        "proxy_protocol": entry.get("proxy_protocol"),
    }


def rule_tuple(r: dict[str, Any]) -> tuple[Any, ...]:
    return (
        r["port"],
        r["protocol"],
        r["mount"],
        r["target"],
        r["funnel"],
    )


def build_add_cmd(r: dict[str, Any]) -> list[str]:
    tool = "funnel" if r["funnel"] else "serve"
    cmd: list[str] = [tool, "--bg", "--yes"]
    proxy_protocol = r.get("proxy_protocol")
    if proxy_protocol not in (None, ""):
        cmd.append(f"--proxy-protocol={int(proxy_protocol)}")

    proto = r["protocol"]
    port = int(r["port"])
    if proto == "https":
        cmd.append(f"--https={port}")
    elif proto == "http":
        cmd.append(f"--http={port}")
    elif proto == "tcp":
        cmd.append(f"--tcp={port}")
    elif proto == "tls-terminated-tcp":
        cmd.append(f"--tls-terminated-tcp={port}")
    else:  # pragma: no cover
        raise SystemExit(f"Unsupported protocol {proto!r}")

    mount = r["mount"]
    if mount and mount != "/":
        cmd.append(f"--set-path={mount}")

    target = r["target"]
    if proto in {"tcp", "tls-terminated-tcp"}:
        # Expect tcp://127.0.0.1:PORT style from Ansible; normalize if host gave bare port.
        if target.startswith("tcp://"):
            cmd.append(target)
        elif target.startswith("http://"):
            # strip accidental http prefix for tcp forwarder
            rest = target[len("http://") :]
            cmd.append(f"tcp://{rest}")
        else:
            cmd.append(f"tcp://{target}")
    else:
        cmd.append(target)
    return cmd


def build_remove_cmd(r: dict[str, Any]) -> list[str]:
    tool = "funnel" if r["funnel"] else "serve"
    cmd: list[str] = [tool, "--bg", "--yes"]
    proto = r["protocol"]
    port = int(r["port"])
    if proto == "https":
        cmd.append(f"--https={port}")
    elif proto == "http":
        cmd.append(f"--http={port}")
    elif proto == "tcp":
        cmd.append(f"--tcp={port}")
    elif proto == "tls-terminated-tcp":
        cmd.append(f"--tls-terminated-tcp={port}")
    mount = r["mount"]
    if mount and mount != "/":
        cmd.append(f"--set-path={mount}")
    cmd.append("off")
    return cmd


def has_serve_config(cfg: dict[str, Any]) -> bool:
    return bool(cfg.get("Web") or cfg.get("TCP") or cfg.get("AllowFunnel"))


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: reconcile_serve.py <desired.json>", file=sys.stderr)
        return 2

    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        desired_raw = json.load(f)

    if not isinstance(desired_raw, list):
        print("desired file must be a JSON list", file=sys.stderr)
        return 2

    desired: list[dict[str, Any]] = []
    for item in desired_raw:
        if not isinstance(item, dict):
            continue
        norm = normalize_desired(item)
        if norm:
            desired.append(norm)

    current_cfg = load_json_cmd(["serve", "status", "--json"])
    current = parse_current(current_cfg)

    cur_set = {rule_tuple(x) for x in current}
    des_set = {rule_tuple(x) for x in desired}

    changed = False

    if not desired:
        if has_serve_config(current_cfg):
            run_tailscale(["serve", "reset"])
            run_tailscale(["funnel", "reset"])
            changed = True
        out = {"changed": changed, "removed": len(current), "added": 0}
        print(json.dumps(out))
        return 0

    # Removals first (avoid port conflicts).
    for r in current:
        if rule_tuple(r) not in des_set:
            run_tailscale(build_remove_cmd(r))
            changed = True

    # Add / converge missing desired rules.
    fresh_cfg = load_json_cmd(["serve", "status", "--json"])
    fresh_rules = parse_current(fresh_cfg)
    fresh_set = {rule_tuple(x) for x in fresh_rules}

    added = 0
    for r in desired:
        if rule_tuple(r) not in fresh_set:
            run_tailscale(build_add_cmd(r))
            changed = True
            added += 1
            fresh_cfg = load_json_cmd(["serve", "status", "--json"])
            fresh_rules = parse_current(fresh_cfg)
            fresh_set = {rule_tuple(x) for x in fresh_rules}

    out = {"changed": changed, "removed": len(cur_set - des_set), "added": added}
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
