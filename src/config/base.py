"""Shared primitives for bounded, data-only configuration loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from src.config.restricted_yaml import RestrictedYamlError, load_restricted_mapping


MAX_CONFIG_BYTES = 256 * 1024


class ConfigError(ValueError):
    """Raised when a configuration file is unsafe or violates its schema."""


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    path = Path(path)
    try:
        with path.open("rb") as handle:
            raw_payload = handle.read(MAX_CONFIG_BYTES + 1)
        if len(raw_payload) > MAX_CONFIG_BYTES:
            raise ConfigError(f"配置文件过大: {path}（限制 {MAX_CONFIG_BYTES} bytes）")
        text = raw_payload.decode("utf-8")
        payload = load_restricted_mapping(text)
    except ConfigError:
        raise
    except (OSError, UnicodeError, RestrictedYamlError, RecursionError) as exc:
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
