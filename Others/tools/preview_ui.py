"""生成使用手册所需的界面实拍；全部数据均为内存样例，不读写个人待办。

从仓库根目录运行：python Others/tools/preview_ui.py
默认输出到 Others/docs/images/vivi-*.png，可用 --output 改为临时目录。
"""

import argparse
import os
from pathlib import Path
import sys
from unittest.mock import patch
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QDate, Qt, QPoint, QCoreApplication, QEvent
from PyQt6.QtGui import QFontDatabase, QFont, QPixmap, QPainter, QColor
from PyQt6.QtWidgets import QApplication, QLabel

from src.ui.theme import P, default_ui_font_family
from src.ui.todo_panel import TodoPanel
from src.ui.todo_reminder import TodoReminderDialog, DueTodo
from src.ui.dialogue import SpeechBubble
from src.input.choice_dialog import CustomChoiceDialog
from src.input.circular_menu import CircularMenuWidget


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "Others/docs/images")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    # Windows 的 offscreen 插件不枚举系统字体，显式注册以避免预览显示方框。
    if sys.platform == "win32":
        for name in ("msyh.ttc", "msyhbd.ttc"):
            font = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / name
            if font.is_file():
                QFontDatabase.addApplicationFont(str(font))
    app.setFont(QFont(default_ui_font_family(), 10))

    def capture(widget, name):
        widget.show()
        app.processEvents()
        path = args.output / f"vivi-{name}.png"
        if not widget.grab().save(str(path)):
            raise RuntimeError(f"无法写入预览：{path}")
        print(f"{path}  {widget.width()}x{widget.height()}")

    today = QDate.currentDate()
    key = today.toString("yyyy-MM-dd")
    tasks = {key: [
        {"ddl": "10:30", "text": "整理灵感，把今天最想做的事记下来", "completed": False},
        {"ddl": "14:00", "text": "完成项目界面，确认按钮与文字反馈", "completed": False},
        {"ddl": "18:30", "text": "关掉工作窗口，留一点时间给自己", "completed": False},
        {"ddl": "09:00", "text": "喝杯水，开启新的一天", "completed": True},
    ]}
    with patch("src.ui.todo_panel.load_todo_items_by_date", return_value=tasks), \
         patch("src.ui.todo_panel.save_todo_items_by_date", return_value=True):
        panel = TodoPanel()
        capture(panel, "todo")
        panel._on_today_item_selected(panel.today_list.item(1))
        capture(panel, "editor")
        panel.complete_btn.click()
        capture(panel, "completed")
        panel._leave_task_editor()
        panel._month_expanded = False
        panel.right_section.hide()
        panel.today_btn.hide()
        panel.expand_btn.setText("展开日历")
        panel.resize(panel.collapsed_width, panel.panel_height)
        capture(panel, "compact")
        panel._close_from_symbol()

    now = datetime.now().replace(second=0, microsecond=0)
    dialog = TodoReminderDialog(10, lambda todo: None, lambda: None)
    dialog.set_todos([DueTodo(key, "14:00", "完成项目界面，确认按钮与文字反馈", now)], now=now)
    capture(dialog, "reminder")
    dialog.allow_close()
    dialog.close()
    choice = CustomChoiceDialog()
    capture(choice, "choice")
    choice.reject()

    target = QLabel()
    target.setGeometry(260, 430, 160, 160)
    target.user_scale = 1.0
    bubble = SpeechBubble("<b>今天也要好好加油呀</b><br>我会替你盯着待办时间。忙完这件事，记得休息一下。", target, 60000)
    capture(bubble, "dialogue")

    items = [{"label": name, "action": lambda: None} for name in ("APP", "TOOL", "待办", "设置", "退出")]
    center = QPoint(360, 410)
    menu = CircularMenuWidget(items, center)
    menu.show()
    for button in menu.buttons:
        button.anim.stop()
        button.move(round(button.base_x), round(button.base_y))
    app.processEvents()
    canvas = QPixmap(720, 660)
    canvas.fill(QColor(P.canvas))
    painter = QPainter(canvas)
    portrait = QPixmap(str(ROOT / "resource/wisdel/皮肤素材/维什戴尔大人.png"))
    portrait = portrait.scaled(185, 185, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    painter.drawPixmap(center.x() - 92, center.y() - 10, portrait)
    painter.drawPixmap(0, 0, menu.grab())
    painter.drawPixmap(390, 64, bubble.grab())
    painter.end()
    canvas.save(str(args.output / "vivi-desktop.png"))
    menu.close_menu(True)
    bubble.close()
    target.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


if __name__ == "__main__":
    main()
