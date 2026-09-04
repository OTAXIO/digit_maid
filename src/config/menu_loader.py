"""Schema validation for the configurable APP and TOOL menu tree."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from src.config.base import ConfigError, clean_scalar, load_yaml_mapping
from src.core.paths import config_path
from src.menu.model import BUILTIN_TOOL_ACTIONS, MenuConfig, MenuEntry


MAX_LAUNCHERS = 100
MAX_CATEGORIES = 50
MAX_MENU_DEPTH = 4
MAX_TARGETS_PER_LAUNCHER = 20


def load_menu_config(path: Optional[Path] = None) -> MenuConfig:
    """Load ``menu.yaml`` and validate both top-level menu sections."""

    source = Path(path) if path is not None else config_path("menu.yaml")
    payload = load_yaml_mapping(source)
    raw_sections = payload.get("menus")
    if not isinstance(raw_sections, dict):
        raise ConfigError("menus 必须是包含 APP 和 TOOL 的映射")

    raw_applications = raw_sections.get("APP", {})
    raw_tools = raw_sections.get("TOOL", {})
    counters = {"launchers": 0, "categories": 0}
    seen_launchers: set[str] = set()

    applications = _parse_entries(
        raw_applications,
        section="APP",
        depth=0,
        counters=counters,
        seen_launchers=seen_launchers,
    )
    tools = _parse_entries(
        raw_tools,
        section="TOOL",
        depth=0,
        counters=counters,
        seen_launchers=seen_launchers,
    )
    return MenuConfig(applications=applications, tools=tools)


def load_launch_paths(path: Optional[Path] = None) -> dict[str, list[str]]:
    """Return every configured APP/TOOL launcher as a flat safe allowlist."""

    return load_menu_config(path).launch_paths()


def load_app_paths(path: Optional[Path] = None) -> dict[str, list[str]]:
    """Backward-compatible alias for older callers."""

    return load_launch_paths(path)


def _parse_entries(
    raw_entries: Any,
    *,
    section: str,
    depth: int,
    counters: dict[str, int],
    seen_launchers: set[str],
) -> tuple[MenuEntry, ...]:
    if not isinstance(raw_entries, dict):
        raise ConfigError(f"{section} 菜单及其分类必须是映射")
    if depth > MAX_MENU_DEPTH:
        raise ConfigError(f"菜单分类最多支持 {MAX_MENU_DEPTH} 层")

    entries = []
    for raw_label, raw_value in raw_entries.items():
        label = clean_scalar(raw_label, max_chars=64)
        if label is None:
            continue

        if isinstance(raw_value, list):
            launcher = _parse_launcher(label, raw_value, counters, seen_launchers)
            if launcher is not None:
                entries.append(launcher)
            continue

        if not isinstance(raw_value, dict):
            continue

        leaf_keys = {key for key in raw_value if key in {"launch", "action"}}
        if leaf_keys:
            if len(leaf_keys) != 1 or len(raw_value) != 1:
                raise ConfigError(f"菜单项 {label} 必须且只能配置 launch 或 action")
            if "launch" in leaf_keys:
                launcher = _parse_launcher(
                    label,
                    raw_value["launch"],
                    counters,
                    seen_launchers,
                )
                if launcher is not None:
                    entries.append(launcher)
            else:
                if section != "TOOL":
                    raise ConfigError(f"内置 action 只能放在 TOOL 中: {label}")
                action_id = clean_scalar(raw_value["action"], max_chars=64)
                if action_id not in BUILTIN_TOOL_ACTIONS:
                    raise ConfigError(f"未知 TOOL action: {raw_value['action']}")
                entries.append(MenuEntry(label=label, action_id=action_id))
            continue

        counters["categories"] += 1
        if counters["categories"] > MAX_CATEGORIES:
            raise ConfigError(f"菜单分类不能超过 {MAX_CATEGORIES} 个")
        children = _parse_entries(
            raw_value,
            section=section,
            depth=depth + 1,
            counters=counters,
            seen_launchers=seen_launchers,
        )
        if children:
            entries.append(MenuEntry(label=label, children=children))
    return tuple(entries)


def _parse_launcher(
    label: str,
    raw_targets: Any,
    counters: dict[str, int],
    seen_launchers: set[str],
) -> Optional[MenuEntry]:
    if not isinstance(raw_targets, list):
        raise ConfigError(
            f"launch 必须是路径列表: {label}；每条路径应写成 '- 路径'（短横线后有空格）"
        )

    counters["launchers"] += 1
    if counters["launchers"] > MAX_LAUNCHERS:
        raise ConfigError(f"启动项不能超过 {MAX_LAUNCHERS} 个")

    normalized_label = label.casefold()
    if normalized_label in seen_launchers:
        raise ConfigError(f"启动项名称不能重复: {label}")

    if len(raw_targets) > MAX_TARGETS_PER_LAUNCHER:
        raise ConfigError(
            f"启动项 {label} 的候选路径不能超过 {MAX_TARGETS_PER_LAUNCHER} 条"
        )

    targets = []
    for raw_target in raw_targets:
        target = clean_scalar(raw_target)
        if target is not None:
            targets.append(target)
    if not targets:
        return None

    seen_launchers.add(normalized_label)
    return MenuEntry(label=label, launch_targets=tuple(targets))
