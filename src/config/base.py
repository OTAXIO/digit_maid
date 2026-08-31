"""Shared primitives for bounded, data-only configuration loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from src.config.restricted_yaml import RestrictedYamlError, load_restricted_mapping


MAX_CONFIG_BYTES = 256 * 1024


class ConfigError(ValueError):
    """Raised when a configuration file is unsafe or violates its schema."""


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ConfigError(f"无法读取配置 {path}: {exc}") from exc

    if size > MAX_CONFIG_BYTES:
        raise ConfigError(f"配置文件过大: {path} ({size} bytes)")

    try:
        payload = load_restricted_mapping(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, RestrictedYamlError) as exc:
        raise ConfigError(f"YAML 配置无效 {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ConfigError(f"配置顶层必须是映射: {path}")
    return payload


def clean_scalar(value: Any, *, max_chars: int = 4096) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned or len(cleaned) > max_chars or any(ord(char) < 32 for char in cleaned):
        return None
    return cleaned
