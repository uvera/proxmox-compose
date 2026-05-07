"""Textual explorer: pick host/target, stream remote logs via SSH."""

from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Label, ListItem, ListView, RichLog, Static

from proxmox_compose.commands.logs import (
    build_compose_logs_shell_body,
    build_docker_logs_remote_argv,
    build_journalctl_remote_argv,
    build_ssh_argv,
    compose_logs_bash_argv,
    resolve_connection,
)
from proxmox_compose.profiles import get_profile_ssh_key
from proxmox_compose.tui.logs_targets import (
    ComposeTarget,
    ContainerTarget,
    JournalTarget,
    LogTarget,
    append_container_targets_from_lines,
    targets_from_inventory_vars,
)
from proxmox_compose.workspace_manifest import load_layered_ansible_defaults


def _label_text(item: ListItem) -> str:
    """Plain text for a ``ListItem`` child (Static/Label use ``.content`` in current Textual)."""
    for w in item.children:
        if isinstance(w, Static):
            raw = getattr(w, "content", None)
            if raw is not None:
                return str(raw).strip()
            # Older Textual: some widgets exposed `.renderable`
            legacy = getattr(w, "renderable", None)
            if legacy is not None:
                return str(legacy).strip()
    return ""


def _target_choice_label(target: LogTarget) -> str:
    if isinstance(target, JournalTarget):
        return f"[journal] {target.unit}"
    if isinstance(target, ComposeTarget):
        svc = f" service={target.service}" if target.service else ""
        return f"[compose] {target.dest} file={target.compose_file}{svc}"
    return f"[container] {target.name}"


def plain_target_title(target: LogTarget) -> str:
    raw = (
        _target_choice_label(target)
        .replace("[journal]", "journal:")
        .replace("[compose]", "compose:")
        .replace("[container]", "container:")
    )
    return raw.replace("[", "").replace("]", "")


def _ssh_discovery_argv(
    *,
    user: str,
    ansible_host: str,
    ssh_key_path: Path | None,
    trust_new_hostkeys: bool,
) -> list[str]:
    ssh = build_ssh_argv(
        user=user,
        ansible_host=ansible_host,
        ssh_key_path=ssh_key_path,
        allocate_tty=False,
        trust_new_hostkeys=trust_new_hostkeys,
    )
    # Include stopped containers so you can attach to crashed ones too.
    return ssh + ["docker", "ps", "-a", "--format", "{{.Names}}"]


def _discovery_container_names(full_ssh: list[str]) -> tuple[int, str]:
    try:
        r = subprocess.run(
            full_ssh,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "timeout listing docker containers"


@dataclass
class LogsExplorerCtx:
    workspace: Path
    profile: str
    merged_hosts: dict[str, dict[str, Any]]
    strict_host_keys: bool
    use_sudo_journal: bool


class PickHostModal(ModalScreen[str | None]):
    """Choose inventory hostname."""

    BINDINGS = [Binding("escape", "cancel", "Back", show=False)]

    def __init__(self, hostnames: list[str]) -> None:
        super().__init__()
        self.hostnames = hostnames

    def compose(self) -> ComposeResult:
        with Vertical(classes="explorer-dialog"):
            yield Label("Hosts (↑/↓ Enter) — Esc to quit · merged inventory")
            if not self.hostnames:
                yield Static("No hosts in merged hosts.yml.")
            else:
                yield ListView(
                    *[ListItem(Label(name)) for name in self.hostnames],
                    id="host_lv",
                    initial_index=0,
                )

    def action_cancel(self) -> None:
        self.dismiss(None)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        txt = _label_text(event.item)
        self.dismiss(txt or None)


class PickTargetModal(ModalScreen[LogTarget | None]):
    """Pick journal / compose / discovered container."""

    BINDINGS = [Binding("escape", "cancel", "Back", show=False)]

    def __init__(
        self,
        *,
        host: str,
        targets: list[LogTarget],
    ) -> None:
        super().__init__()
        self.host = host
        self.targets = targets

    def compose(self) -> ComposeResult:
        with Vertical(classes="explorer-dialog"):
            yield Label(f"Log targets on [b]{self.host}[/b] (↑/↓ Enter · Esc back)")
            if not self.targets:
                yield Static(
                    "No targets from inventory and container discovery returned nothing.\n"
                    "Add lxc_systemd_services / vm_compose_apps in host/group vars, "
                    "or ensure Docker responds over SSH.",
                )
            else:
                yield ListView(
                    *[ListItem(Label(_target_choice_label(t))) for t in self.targets],
                    id="tgt_lv",
                    initial_index=0,
                )

    def action_cancel(self) -> None:
        self.dismiss(None)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.index
        if 0 <= idx < len(self.targets):
            self.dismiss(self.targets[idx])
        else:
            self.dismiss(None)


class StreamLogModal(ModalScreen[None]):
    """SSH stream into RichLog."""

    BINDINGS = [
        Binding("escape", "stop", "Stop"),
        Binding("q", "stop", "Stop"),
    ]

    AUTO_FOCUS = "#log_out"

    def __init__(
        self,
        *,
        title: str,
        ssh_argv: list[str],
    ) -> None:
        super().__init__()
        self._title_text = title
        self._ssh_argv = ssh_argv
        self._proc: subprocess.Popen[bytes] | None = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="explorer-stream"):
            yield Label(self._title_text)
            yield RichLog(
                id="log_out",
                wrap=True,
                highlight=False,
                markup=False,
                auto_scroll=True,
            )
            yield Static("Esc / q closes stream · stops remote tail")

    def on_mount(self) -> None:
        try:
            self._proc = subprocess.Popen(
                self._ssh_argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                shell=False,
            )
        except OSError as exc:
            self.query_one("#log_out", RichLog).write(f"spawn failed: {exc}\n")
            return

        threading.Thread(target=self._read_stdout_thread, daemon=True).start()

    def _paste_line(self, line: str) -> None:
        self.query_one("#log_out", RichLog).write(line)

    def _read_stdout_thread(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            self.app.call_from_thread(self._paste_line, "no stdout from ssh subprocess\n")
            return
        try:
            for raw in proc.stdout:
                if isinstance(raw, bytes):
                    line = raw.decode(errors="replace").rstrip("\n\r")
                else:
                    line = str(raw).rstrip("\n\r")
                self.app.call_from_thread(self._paste_line, line + "\n")
        except Exception as exc:
            self.app.call_from_thread(self._paste_line, f"\n[stream reader error] {exc}\n")

    def action_stop(self) -> None:
        proc = self._proc
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        self.dismiss()

    def on_unmount(self) -> None:
        proc = self._proc
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()


class LogsExplorerApp(App[None]):
    """Host → target → streamed logs loop."""

    CSS = """
    .explorer-dialog { width: 84; padding: 1 2; }
    .explorer-stream { width: 96; padding: 1 2; }
    StreamLogModal RichLog {
        height: 24;
        border: solid $accent;
        min-height: 14;
        width: 1fr;
    }
    PickHostModal, PickTargetModal, StreamLogModal {
        align: center middle;
    }
    """

    BINDINGS = [
        Binding("escape", "try_quit", "Quit explorer", priority=True),
        Binding("ctrl+c", "try_quit", "Quit explorer", priority=True),
    ]

    def __init__(self, ctx: LogsExplorerCtx) -> None:
        super().__init__()
        self.ctx = ctx
        ssh_key = get_profile_ssh_key(ctx.profile)
        self._ssh_key_path = ssh_key
        self._trust = not ctx.strict_host_keys

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Vertical(
            Static(
                "[b]Logs explorer[/b] (Textual UI) · merged inventory hosts + Ansible vars + Docker names"
            ),
            classes="explorer-main-msg",
        )
        yield Footer()

    def action_try_quit(self) -> None:
        self.exit()

    def on_mount(self) -> None:
        # @work replaces this with a sync starter that schedules the async body;
        # do not pass it to run_worker again (that would run the starter as work).
        self._browse_loop()

    @work(exclusive=True)
    async def _browse_loop(self) -> None:
        names = sorted(self.ctx.merged_hosts.keys())
        if not names:
            self.exit(message="Merged inventory has no hosts.")
            return
        while True:
            host = await self.push_screen_wait(PickHostModal(names))
            if not host:
                self.exit()
                return
            if host not in self.ctx.merged_hosts:
                continue
            hvars = self.ctx.merged_hosts[host]
            user, ansible_host = resolve_connection(hvars, host)
            layered = load_layered_ansible_defaults(self.ctx.workspace, host)
            targets = targets_from_inventory_vars(layered)

            disco = _ssh_discovery_argv(
                user=user,
                ansible_host=ansible_host,
                ssh_key_path=self._ssh_key_path,
                trust_new_hostkeys=self._trust,
            )
            code, out = _discovery_container_names(disco)
            if code == 0:
                append_container_targets_from_lines(targets, out)

            tgt = await self.push_screen_wait(PickTargetModal(host=host, targets=targets))
            if tgt is None:
                continue

            ssh_base = build_ssh_argv(
                user=user,
                ansible_host=ansible_host,
                ssh_key_path=self._ssh_key_path,
                allocate_tty=False,
                trust_new_hostkeys=self._trust,
            )
            remote = _remote_argv_for_target(
                tgt,
                follow=True,
                use_sudo=self.ctx.use_sudo_journal,
            )
            cmd = ssh_base + remote
            title = f"SSH → {user}@{ansible_host} — {plain_target_title(tgt)}"
            await self.push_screen_wait(StreamLogModal(title=title, ssh_argv=cmd))


def _remote_argv_for_target(
    target: LogTarget,
    *,
    follow: bool,
    use_sudo: bool,
) -> list[str]:
    if isinstance(target, JournalTarget):
        return build_journalctl_remote_argv(
            target.unit,
            use_sudo=use_sudo,
            follow=follow,
            since=None,
            lines=None,
            no_pager=True,
        )
    if isinstance(target, ComposeTarget):
        shell = build_compose_logs_shell_body(
            target.dest,
            target.compose_file,
            service=target.service,
            follow=follow,
        )
        return compose_logs_bash_argv(shell)
    return build_docker_logs_remote_argv(target.name, follow=follow)


def run_logs_explorer(
    *,
    workspace: Path,
    profile: str,
    merged_hosts: dict[str, dict[str, Any]],
    strict_host_keys: bool,
    use_sudo_journal: bool,
) -> None:
    ctx = LogsExplorerCtx(
        workspace=workspace.resolve(),
        profile=profile,
        merged_hosts=merged_hosts,
        strict_host_keys=strict_host_keys,
        use_sudo_journal=use_sudo_journal,
    )
    LogsExplorerApp(ctx).run()
