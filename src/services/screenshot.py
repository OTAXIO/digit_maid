"""Screenshot capture service with writable defaults and collision-safe names."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QStandardPaths
from PyQt6.QtWidgets import QApplication


def _default_screenshot_dir() -> Path:
    pictures = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.PicturesLocation
    )
    base = Path(pictures).expanduser() if pictures else Path.home() / "Pictures"
    return base / "DigitMaid" / "Screenshots"


def capture_screen_content(save_dir: Optional[str] = None) -> str:
    """Capture the primary screen and save it to a user-writable directory."""
    try:
        target_dir = Path(save_dir).expanduser() if save_dir else _default_screenshot_dir()
        target_dir.mkdir(parents=True, exist_ok=True)

        app = QApplication.instance()
        if app is None:
            return "截图失败: 找不到 QApplication 实例"
        screen = app.primaryScreen()
        if screen is None:
            return "截图失败: 找不到可用屏幕"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        destination = target_dir / f"screenshot_{timestamp}.png"
        pixmap = screen.grabWindow(0)
        if not pixmap.save(str(destination), "PNG"):
            return f"截图失败: 无法写入 {destination}"
        return f"屏幕已截图，保存为: {destination}"
    except (OSError, ValueError) as exc:
        return f"截图失败: {exc}"
