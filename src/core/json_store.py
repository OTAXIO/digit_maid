"""Bounded and atomic JSON file helpers."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional, Union


class JsonStoreError(ValueError):
    """Raised when a JSON file is missing, too large, or malformed."""


MAX_JSON_LIMIT_BYTES = 64 * 1024 * 1024
MAX_JSON_NESTING_DEPTH = 128


def _validate_byte_limit(max_bytes: int) -> int:
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int):
        raise JsonStoreError("文件大小限制必须是整数")
    if max_bytes <= 0 or max_bytes > MAX_JSON_LIMIT_BYTES:
        raise JsonStoreError(
            f"文件大小限制必须在 1 到 {MAX_JSON_LIMIT_BYTES} bytes 之间"
        )
    return max_bytes


def _validate_json_nesting(raw_payload: bytes) -> None:
    depth = 0
    in_string = False
    escaped = False
    for character in raw_payload:
        if in_string:
            if escaped:
                escaped = False
            elif character == 0x5C:  # backslash
                escaped = True
            elif character == 0x22:  # double quote
                in_string = False
            continue

        if character == 0x22:
            in_string = True
        elif character in (0x5B, 0x7B):  # [ or {
            depth += 1
            if depth > MAX_JSON_NESTING_DEPTH:
                raise JsonStoreError(
                    f"JSON 嵌套过深（限制 {MAX_JSON_NESTING_DEPTH} 层）"
                )
        elif character in (0x5D, 0x7D):  # ] or }
            depth = max(0, depth - 1)


def read_json_file(path: Union[os.PathLike[str], str], *, max_bytes: int) -> Any:
    max_bytes = _validate_byte_limit(max_bytes)
    source = Path(path)
    try:
        with source.open("rb") as handle:
            raw_payload = handle.read(max_bytes + 1)
        if len(raw_payload) > max_bytes:
            raise JsonStoreError(f"文件过大（限制 {max_bytes} bytes）")
        _validate_json_nesting(raw_payload)
        return json.loads(raw_payload.decode("utf-8"))
    except JsonStoreError:
        raise
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise JsonStoreError(f"JSON 格式无效: {exc}") from exc


def atomic_write_json(
    path: Union[os.PathLike[str], str],
    payload: Any,
    *,
    max_bytes: Optional[int] = None,
) -> None:
    """Write JSON next to its destination and atomically replace the old file."""
    if max_bytes is not None:
        max_bytes = _validate_byte_limit(max_bytes)
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
        if max_bytes is not None:
            payload_size = temporary_path.stat().st_size
            if payload_size > max_bytes:
                raise JsonStoreError(
                    f"JSON 数据过大（{payload_size} bytes，限制 {max_bytes} bytes）"
                )
        os.replace(temporary_path, destination)
    except Exception:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
