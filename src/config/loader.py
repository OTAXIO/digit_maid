"""Safe YAML loading plus schema validation for user-editable configuration."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

from src.config.restricted_yaml import RestrictedYamlError, load_restricted_mapping
from src.core.paths import config_path, resource_path, runtime_root


MAX_CONFIG_BYTES = 256 * 1024
MAX_APPS = 100
MAX_APP_CATEGORIES = 50
MAX_APP_CATEGORY_DEPTH = 4
MAX_TARGETS_PER_APP = 20
ALLOWED_FALL_MODES = {"smooth", "direct", "none"}
ALLOWED_IDLE_MODES = {"default", "sport", "lazy"}

DEFAULT_ANIMATION_CONFIG = {
    "base_dir": "resource/wisdel/皮肤素材/可用素材",
    "fall_mode": "smooth",
    "idle_mode": "default",
    "smooth_fall": True,
    "actions": {},
    "loops": {},
    "animations": {},
}


class ConfigError(ValueError):
    """Raised when a configuration file is unsafe or violates its schema."""


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
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

    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ConfigError(f"配置顶层必须是映射: {path}")
    return payload


def _clean_scalar(value: Any, *, max_chars: int = 4096) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned or len(cleaned) > max_chars or any(ord(char) < 32 for char in cleaned):
        return None
    return cleaned


def _clean_app_menu(
    raw_menu: Any,
    *,
    depth: int,
    counters: dict[str, int],
    seen_apps: set[str],
) -> dict[str, Any]:
    if not isinstance(raw_menu, dict):
        raise ConfigError("app_paths 及应用分类必须是映射")
    if depth > MAX_APP_CATEGORY_DEPTH:
        raise ConfigError(f"应用分类最多支持 {MAX_APP_CATEGORY_DEPTH} 层")

    menu: dict[str, Any] = {}
    for raw_name, raw_value in raw_menu.items():
        name = _clean_scalar(raw_name, max_chars=64)
        if name is None:
            continue

        if isinstance(raw_value, list):
            counters["apps"] += 1
            if counters["apps"] > MAX_APPS:
                raise ConfigError(f"应用数量不能超过 {MAX_APPS} 个")
            normalized_name = name.casefold()
            if normalized_name in seen_apps:
                raise ConfigError(f"应用名称不能重复: {name}")

            targets = []
            for raw_target in raw_value[:MAX_TARGETS_PER_APP]:
                target = _clean_scalar(raw_target)
                if target is not None:
                    targets.append(target)
            if targets:
                seen_apps.add(normalized_name)
                menu[name] = targets
            continue

        if isinstance(raw_value, dict):
            counters["categories"] += 1
            if counters["categories"] > MAX_APP_CATEGORIES:
                raise ConfigError(f"应用分类不能超过 {MAX_APP_CATEGORIES} 个")
            children = _clean_app_menu(
                raw_value,
                depth=depth + 1,
                counters=counters,
                seen_apps=seen_apps,
            )
            if children:
                menu[name] = children
    return menu


def load_app_menu(path: Optional[Path] = None) -> dict[str, Any]:
    """Return the validated APP menu tree from ``config/apps.yaml``."""

    source = path or config_path("apps.yaml")
    payload = _load_yaml_mapping(Path(source))
    raw_apps = payload.get("app_paths", {})
    return _clean_app_menu(
        raw_apps,
        depth=0,
        counters={"apps": 0, "categories": 0},
        seen_apps=set(),
    )


def _flatten_app_menu(menu: dict[str, Any]) -> dict[str, list[str]]:
    apps: dict[str, list[str]] = {}
    for name, value in menu.items():
        if isinstance(value, list):
            apps[name] = value
        elif isinstance(value, dict):
            apps.update(_flatten_app_menu(value))
    return apps


def load_app_paths(path: Optional[Path] = None) -> dict[str, list[str]]:
    """Return a flat launch allowlist while categories remain a UI concern."""

    return _flatten_app_menu(load_app_menu(path))


def _safe_animation_base_dir(raw_value: Any) -> str:
    value = _clean_scalar(raw_value) or DEFAULT_ANIMATION_CONFIG["base_dir"]
    relative = Path(value.replace("\\", "/"))
    if relative.is_absolute():
        return DEFAULT_ANIMATION_CONFIG["base_dir"]

    resolved = runtime_root().joinpath(relative).resolve()
    resource_root = resource_path().resolve()
    try:
        resolved.relative_to(resource_root)
    except ValueError:
        return DEFAULT_ANIMATION_CONFIG["base_dir"]
    return relative.as_posix()


def _clean_animation_files(raw_value: Any) -> Optional[str]:
    value = _clean_scalar(raw_value, max_chars=1024)
    if value is None:
        return None

    valid_names = []
    for candidate in value.split(","):
        name = candidate.strip()
        path = Path(name)
        if "/" in name or "\\" in name or path.name != name or path.suffix.casefold() != ".gif":
            continue
        valid_names.append(name)
    return ", ".join(valid_names) if valid_names else None


def load_animation_config(path: Optional[Path] = None) -> dict[str, Any]:
    source = path or config_path("maid_animations.yaml")
    payload = _load_yaml_mapping(Path(source))
    config = deepcopy(DEFAULT_ANIMATION_CONFIG)
    config["base_dir"] = _safe_animation_base_dir(payload.get("base_dir"))

    fall_mode = str(payload.get("fall_mode", "")).strip().casefold()
    if fall_mode in ALLOWED_FALL_MODES:
        config["fall_mode"] = fall_mode

    idle_mode = str(payload.get("idle_mode", "")).strip().casefold()
    if idle_mode in ALLOWED_IDLE_MODES:
        config["idle_mode"] = idle_mode

    smooth_fall = payload.get("smooth_fall")
    if isinstance(smooth_fall, bool):
        config["smooth_fall"] = smooth_fall

    raw_actions = payload.get("actions", {})
    if isinstance(raw_actions, dict):
        for raw_name, raw_files in raw_actions.items():
            name = _clean_scalar(raw_name, max_chars=64)
            files = _clean_animation_files(raw_files)
            if name is not None and files is not None:
                config["actions"][name] = files

    raw_loops = payload.get("loops", {})
    if isinstance(raw_loops, dict):
        for raw_name, raw_loop in raw_loops.items():
            name = _clean_scalar(raw_name, max_chars=64)
            if name is not None and isinstance(raw_loop, bool):
                config["loops"][name] = raw_loop

    raw_animations = payload.get("animations", {})
    if isinstance(raw_animations, dict):
        for raw_name, raw_animation in raw_animations.items():
            name = _clean_scalar(raw_name, max_chars=64)
            if name is None or not isinstance(raw_animation, dict):
                continue
            files = _clean_animation_files(raw_animation.get("file"))
            loop = raw_animation.get("loop")
            if files is not None:
                config["animations"][name] = {
                    "file": files,
                    "loop": loop if isinstance(loop, bool) else True,
                }
    return config


def load_dialog_theme(path: Optional[Path] = None) -> dict[str, str]:
    source = path or config_path("dialog_style.yaml")
    payload = _load_yaml_mapping(Path(source))
    theme: dict[str, str] = {}
    for raw_key, raw_value in payload.items():
        key = _clean_scalar(raw_key, max_chars=64)
        if key is None or isinstance(raw_value, (dict, list)) or raw_value is None:
            continue
        if isinstance(raw_value, bool):
            theme[key] = "true" if raw_value else "false"
        else:
            value = _clean_scalar(str(raw_value))
            if value is not None:
                theme[key] = value
    return theme
