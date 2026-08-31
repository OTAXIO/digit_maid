"""Bounded and atomic JSON file helpers."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional, Union


class JsonStoreError(ValueError):
    """Raised when a JSON file is missing, too large, or malformed."""


def read_json_file(path: Union[os.PathLike[str], str], *, max_bytes: int) -> Any:
    source = Path(path)
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise JsonStoreError(f"无法读取文件: {exc}") from exc

    if size > max_bytes:
        raise JsonStoreError(f"文件过大（{size} bytes，限制 {max_bytes} bytes）")

    try:
        with source.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise JsonStoreError(f"JSON 格式无效: {exc}") from exc


def atomic_write_json(path: Union[os.PathLike[str], str], payload: Any) -> None:
    """Write JSON next to its destination and atomically replace the old file."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Optional[Path] = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, destination)
    except Exception:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
