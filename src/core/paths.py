"""Centralized paths for source and PyInstaller runtimes."""

from __future__ import annotations

import sys
from pathlib import Path


def runtime_root() -> Path:
    """Return the directory that contains bundled resources and configuration."""
    if getattr(sys, "frozen", False):
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            return Path(bundle_root).resolve()
    return Path(__file__).resolve().parents[2]


def runtime_path(*parts: str) -> Path:
    return runtime_root().joinpath(*parts)


def resource_path(*parts: str) -> Path:
    return runtime_path("resource", *parts)


def config_path(filename: str) -> Path:
    if Path(filename).name != filename:
        raise ValueError("config filename must not contain path separators")
    return runtime_path("config", filename)
