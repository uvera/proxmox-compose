from __future__ import annotations

from importlib import resources
from importlib.resources.abc import Traversable

LEGACY_EXCLUDED_PATHS = {"infra"}


def load_scaffold_files() -> dict[str, str]:
    """Load scaffold-managed file contents from the packaged scaffold_assets tree."""
    root = resources.files("proxmox_compose").joinpath("scaffold_assets")
    return _collect_files(root, prefix="")


def _collect_files(node: Traversable, *, prefix: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for child in sorted(node.iterdir(), key=lambda c: c.name):
        name = child.name
        rel = f"{prefix}/{name}" if prefix else name
        if any(rel == excluded or rel.startswith(f"{excluded}/") for excluded in LEGACY_EXCLUDED_PATHS):
            continue
        if child.is_dir():
            if name in {"__pycache__", ".git"}:
                continue
            result.update(_collect_files(child, prefix=rel))
            continue
        if name in {".gitkeep"}:
            continue
        if name.endswith(".pyc"):
            continue
        data = child.read_bytes()
        text = data.decode("utf-8")
        result[rel] = text.replace("\r\n", "\n")
    return result
