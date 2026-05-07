"""Tests for log target extraction (no Textual)."""

from proxmox_compose.tui.logs_targets import (
    ComposeTarget,
    ContainerTarget,
    JournalTarget,
    append_container_targets_from_lines,
    targets_from_inventory_vars,
)


def test_targets_from_inventory_vars_journal_and_compose() -> None:
    layered = {
        "lxc_systemd_services": [
            {"name": ""},
            {"unexpected": 1},
            {"name": "myservice.service"},
            {"name": "another"},
        ],
        "vm_compose_apps": [
            {},
            {"dest": ""},
            {"dest": "/srv/app", "compose_file_name": "compose.yaml"},
            {"dest": "/bare"},
        ],
    }
    got = targets_from_inventory_vars(layered)
    assert JournalTarget("myservice.service") in got
    assert JournalTarget("another") in got
    assert ComposeTarget("/srv/app", "compose.yaml", None) in got
    assert ComposeTarget("/bare", "docker-compose.yaml", None) in got


def test_append_container_targets_from_lines_skips_blanks() -> None:
    base: list = []
    append_container_targets_from_lines(
        base,
        "\n  foo  \n\nbar\n",
    )
    assert ContainerTarget("foo") in base
    assert ContainerTarget("bar") in base
