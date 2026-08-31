"""Allowlisted, cross-platform application launching."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Optional, Tuple

from src.config import ConfigError, load_app_paths as _load_app_paths


_WINDOWS_CONSOLE_APPS = {"cmd.exe", "powershell.exe", "pwsh.exe"}


def load_app_paths() -> dict[str, list[str]]:
    try:
        return _load_app_paths()
    except ConfigError as exc:
        print(f"读取 apps.yaml 失败: {exc}")
        return {}


def _is_windows_path(value: str) -> bool:
    return "\\" in value or (len(value) > 1 and value[1] == ":")


def _is_macos_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return normalized.endswith(".app") or normalized.startswith("/Applications/")


def _launch_windows_app(target: str) -> None:
    if _is_windows_path(target):
        resolved = target if os.path.isfile(target) else None
    else:
        resolved = shutil.which(target)
    if resolved is None:
        raise FileNotFoundError(target)

    executable_name = os.path.basename(resolved).casefold()
    flags = (
        subprocess.CREATE_NEW_CONSOLE
        if executable_name in _WINDOWS_CONSOLE_APPS
        else subprocess.DETACHED_PROCESS
    )
    subprocess.Popen([resolved], creationflags=flags, shell=False)


def _launch_macos_app(target: str) -> None:
    if not _is_macos_path(target) or not os.path.exists(target):
        raise FileNotFoundError(target)
    subprocess.run(["open", target], check=True, capture_output=True, timeout=10)


def _launch_linux_app(target: str) -> None:
    if _is_windows_path(target) or _is_macos_path(target):
        raise FileNotFoundError(target)
    resolved = target if os.path.isfile(target) and os.access(target, os.X_OK) else shutil.which(target)
    if resolved is None:
        raise FileNotFoundError(target)
    subprocess.Popen([resolved], start_new_session=True, shell=False)


def _find_configured_app(
    app_name: str, apps: dict[str, list[str]]
) -> Optional[Tuple[str, list[str]]]:
    requested = app_name.strip().casefold()
    for configured_name, targets in apps.items():
        if configured_name.casefold() == requested:
            return configured_name, targets
    return None


def open_application(app_name: str) -> str:
    """Launch only an exact app name from ``config/apps.yaml``."""
    if not isinstance(app_name, str) or not app_name.strip():
        return "应用名称不能为空"

    configured = _find_configured_app(app_name, load_app_paths())
    if configured is None:
        return f"未配置应用: {app_name}（已阻止直接执行任意命令）"

    configured_name, targets = configured
    system = platform.system()
    launcher = {
        "Windows": _launch_windows_app,
        "Darwin": _launch_macos_app,
        "Linux": _launch_linux_app,
    }.get(system)
    if launcher is None:
        return "当前系统暂不支持应用启动"

    for target in targets:
        try:
            launcher(target)
            return f"已启动{configured_name}"
        except (FileNotFoundError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
    return f"未找到{configured_name}，请确认 config/apps.yaml 中的安装位置"
