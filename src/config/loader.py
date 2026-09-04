"""Safe YAML loading plus schema validation for user-editable configuration."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

from src.config.base import ConfigError, clean_scalar, load_yaml_mapping
from src.core.paths import config_path, resource_path, runtime_root


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

DEFAULT_TODO_REMINDER_CONFIG = {
    "desktop_guard_hours": 2.0,
    "popup_reminder_hours": 1.0,
    "snooze_minutes": 30,
}


def _safe_animation_base_dir(raw_value: Any) -> str:
    value = clean_scalar(raw_value) or DEFAULT_ANIMATION_CONFIG["base_dir"]
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
    value = clean_scalar(raw_value, max_chars=1024)
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
    payload = load_yaml_mapping(Path(source))
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
            name = clean_scalar(raw_name, max_chars=64)
            files = _clean_animation_files(raw_files)
            if name is not None and files is not None:
                config["actions"][name] = files

    raw_loops = payload.get("loops", {})
    if isinstance(raw_loops, dict):
        for raw_name, raw_loop in raw_loops.items():
            name = clean_scalar(raw_name, max_chars=64)
            if name is not None and isinstance(raw_loop, bool):
                config["loops"][name] = raw_loop

    raw_animations = payload.get("animations", {})
    if isinstance(raw_animations, dict):
        for raw_name, raw_animation in raw_animations.items():
            name = clean_scalar(raw_name, max_chars=64)
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
    payload = load_yaml_mapping(Path(source))
    theme: dict[str, str] = {}
    for raw_key, raw_value in payload.items():
        key = clean_scalar(raw_key, max_chars=64)
        if key is None or isinstance(raw_value, (dict, list)) or raw_value is None:
            continue
        if isinstance(raw_value, bool):
            theme[key] = "true" if raw_value else "false"
        else:
            value = clean_scalar(str(raw_value))
            if value is not None:
                theme[key] = value
    return theme


def _bounded_number(value: Any, default: float, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    number = float(value)
    if number < minimum or number > maximum:
        return default
    return number


def load_todo_reminder_config(path: Optional[Path] = None) -> dict[str, Any]:
    """Load the three user-facing DDL reminder thresholds.

    Invalid individual values fall back independently so one typo does not
    disable the entire reminder service. Invalid YAML still raises ConfigError
    and is reported by the application bootstrap.
    """

    source = path or config_path("todo.yaml")
    payload = load_yaml_mapping(Path(source))
    config = deepcopy(DEFAULT_TODO_REMINDER_CONFIG)
    config["desktop_guard_hours"] = _bounded_number(
        payload.get("desktop_guard_hours"),
        config["desktop_guard_hours"],
        0.0,
        24.0 * 30,
    )
    config["popup_reminder_hours"] = _bounded_number(
        payload.get("popup_reminder_hours"),
        config["popup_reminder_hours"],
        0.0,
        24.0 * 30,
    )
    config["snooze_minutes"] = int(
        _bounded_number(
            payload.get("snooze_minutes"),
            float(config["snooze_minutes"]),
            1.0,
            24.0 * 60,
        )
    )
    return config
