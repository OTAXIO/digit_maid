"""Qt application bootstrap separated from the command-line entry point."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import Optional

from PyQt6.QtCore import QSharedMemory
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QApplication

from src.core.paths import resource_path, runtime_root
from src.ui.maid_window import MaidWindow
from src.ui.theme import default_ui_font_family


SINGLE_INSTANCE_KEY = "DigitMaid.Singleton"


def acquire_single_instance_lock() -> Optional[QSharedMemory]:
    """Return a live lock, or ``None`` when another instance owns it."""
    lock = QSharedMemory(SINGLE_INSTANCE_KEY)
    if lock.attach():
        lock.detach()
    if not lock.create(1):
        return None
    return lock


def create_application(argv: Optional[Sequence[str]] = None) -> QApplication:
    app = QApplication(list(argv) if argv is not None else sys.argv)
    ui_font = QFont(default_ui_font_family(), 10)
    # 正文使用常规字重，标题与操作按钮由主题显式强调。
    ui_font.setBold(False)
    app.setFont(ui_font)

    icon = resource_path("wisdel", "皮肤素材", "维什戴尔大人.png")
    if icon.is_file():
        app.setWindowIcon(QIcon(str(icon)))
    return app


def run(argv: Optional[Sequence[str]] = None) -> int:
    print(f"启动 Digit Maid... (Root: {runtime_root()})")
    app = create_application(argv)

    instance_lock = acquire_single_instance_lock()
    if instance_lock is None:
        print("Digit Maid 已在运行，本次启动已取消。")
        return 0

    # Keep both the shared-memory lock and main window alive for the app lifetime.
    app._instance_lock = instance_lock
    app._maid_window = MaidWindow()
    app._maid_window.show()
    print("桌宠已启动。右键点击桌宠可查看功能菜单。")
    return app.exec()
