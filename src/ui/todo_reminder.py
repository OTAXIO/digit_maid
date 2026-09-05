"""常驻 DDL 提醒与桌面保护调度；纯时间计算由 domain.reminders 提供。"""

from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import Callable, Optional

from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.config import ConfigError, load_todo_reminder_config
from src.config.loader import DEFAULT_TODO_REMINDER_CONFIG
from src.ui.theme.styles import REMINDER
from src.ui.theme.widgets import apply_shadow, keep_on_screen
from src.function.todo_store import (
    complete_todo_item,
    load_todo_items_by_date,
)


from src.domain.reminders import (
    DueTodo, find_due_todos, _remaining_text, MAX_SNOOZE_MINUTES,
)


class TodoReminderDialog(QWidget):
    """A non-expiring reminder with only complete and snooze decisions."""

    def __init__(
        self,
        snooze_minutes: int,
        on_complete: Callable[[DueTodo], None],
        on_snooze: Callable[[], None],
    ):
        super().__init__(None)
        self._allow_close = False
        self._todos: list[DueTodo] = []
        self._on_complete = on_complete
        self._on_snooze = on_snooze
        try:
            normalized_snooze = float(snooze_minutes)
        except (TypeError, ValueError, OverflowError):
            normalized_snooze = float(DEFAULT_TODO_REMINDER_CONFIG["snooze_minutes"])
        if not math.isfinite(normalized_snooze):
            normalized_snooze = float(DEFAULT_TODO_REMINDER_CONFIG["snooze_minutes"])
        self._snooze_minutes = max(
            1,
            min(int(normalized_snooze), MAX_SNOOZE_MINUTES),
        )
        self.setWindowTitle("Digit Maid · 待办提醒")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(500)
        self.setMinimumHeight(350)
        self.setMaximumHeight(620)
        self.resize(500, 430)
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)

        self.card = QFrame(self)
        self.card.setObjectName("reminder_card")
        self.card.setStyleSheet(REMINDER)
        apply_shadow(self.card)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(26, 24, 26, 24)
        card_layout.setSpacing(8)

        eyebrow = QLabel("VIVI  /  DEADLINE REMINDER", self.card)
        eyebrow.setObjectName("eyebrow")
        card_layout.addWidget(eyebrow)

        title = QLabel("博士，这件事快到时间啦", self.card)
        title.setObjectName("reminder_title")
        card_layout.addWidget(title)

        self.subtitle = QLabel("临近截止时间的待办会留在这里，直到你做出选择。", self.card)
        self.subtitle.setObjectName("reminder_subtitle")
        self.subtitle.setWordWrap(True)
        card_layout.addWidget(self.subtitle)
        card_layout.addSpacing(10)

        self.scroll = QScrollArea(self.card)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.items_host = QWidget(self.scroll)
        self.items_layout = QVBoxLayout(self.items_host)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(10)
        self.items_layout.addStretch(1)
        self.scroll.setWidget(self.items_host)
        card_layout.addWidget(self.scroll, 1)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.snooze_button = QPushButton(
            f"{self._snooze_minutes} 分钟后提醒", self.card
        )
        self.snooze_button.setObjectName("snooze_btn")
        self.snooze_button.clicked.connect(self._on_snooze_clicked)
        action_row.addWidget(self.snooze_button)

        self.complete_button = QPushButton("标记已完成", self.card)
        self.complete_button.setObjectName("complete_btn")
        self.complete_button.clicked.connect(self._on_complete_clicked)
        action_row.addWidget(self.complete_button)
        card_layout.addLayout(action_row)
        root_layout.addWidget(self.card)

    def set_todos(self, todos: list[DueTodo], now: Optional[datetime] = None):
        source_todos = todos if isinstance(todos, (list, tuple)) else ()
        self._todos = [todo for todo in source_todos if isinstance(todo, DueTodo)]
        current_time = now if isinstance(now, datetime) else datetime.now()
        count = len(self._todos)
        self.resize(500, min(620, 250 + max(1, min(count, 4)) * 84))
        self.subtitle.setText(
            f"共有 {count} 项临近 DDL。最紧急的一项已强调显示。"
            if count > 1
            else "这项待办已临近 DDL，请完成它或选择稍后提醒。"
        )

        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for index, todo in enumerate(self._todos):
            item_card = QFrame(self.items_host)
            item_card.setObjectName("urgent_item" if index == 0 else "queued_item")
            item_layout = QVBoxLayout(item_card)
            item_layout.setContentsMargins(16, 13, 16, 13)
            item_layout.setSpacing(4)

            time_label = QLabel(f"{todo.date_key}  ·  {todo.ddl}", item_card)
            time_label.setObjectName("task_time")
            item_layout.addWidget(time_label)

            text_label = QLabel(todo.text, item_card)
            # 待办正文是纯文本，避免 <...> 被 QLabel 自动识别为富文本。
            text_label.setTextFormat(Qt.TextFormat.PlainText)
            text_label.setObjectName("task_text")
            text_label.setWordWrap(True)
            item_layout.addWidget(text_label)

            remaining_label = QLabel(
                _remaining_text(todo.deadline, current_time), item_card
            )
            remaining_label.setObjectName("task_remaining")
            item_layout.addWidget(remaining_label)
            self.items_layout.addWidget(item_card)

        self.items_layout.addStretch(1)
        self.complete_button.setEnabled(bool(self._todos))

    def show_for_todos(self, todos: list[DueTodo], now: Optional[datetime] = None):
        self.set_todos(todos, now=now)
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(area.right() - self.width() - 28, area.top() + 28)
        self.show()
        keep_on_screen(self)
        self.raise_()
        self.activateWindow()

    def _on_complete_clicked(self):
        if self._todos:
            self._on_complete(self._todos[0])

    def _on_snooze_clicked(self):
        self._on_snooze()

    def allow_close(self):
        self._allow_close = True

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        app = QApplication.instance()
        app_closing = bool(app.closingDown()) if app is not None else False
        if not self._allow_close and not app_closing:
            event.ignore()
            return
        super().closeEvent(event)


class TodoReminderManager(QObject):
    CHECK_INTERVAL_MS = 30_000
    REGULAR_REMINDER_MINUTES = 10

    def __init__(self, maid_window):
        super().__init__(maid_window)
        self.maid_window = maid_window
        self._dialog: Optional[TodoReminderDialog] = None
        self._snoozed_until: Optional[datetime] = None
        self._next_regular_at: Optional[datetime] = None
        try:
            self.config = load_todo_reminder_config()
        except ConfigError as exc:
            print(f"读取 config/todo.yaml 失败，将使用默认值: {exc}")
            self.config = dict(DEFAULT_TODO_REMINDER_CONFIG)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_now)
        self.timer.start(self.CHECK_INTERVAL_MS)
        QTimer.singleShot(0, self.check_now)

    def check_now(self, now: Optional[datetime] = None):
        current_time = now if isinstance(now, datetime) else datetime.now()
        items_by_date = load_todo_items_by_date()

        guard_todos = find_due_todos(
            items_by_date,
            current_time,
            self.config["desktop_guard_hours"],
        )
        self.maid_window.set_deadline_guard_active(bool(guard_todos))

        reminder_todos = find_due_todos(
            items_by_date,
            current_time,
            self.config["popup_reminder_hours"],
        )
        if self._dialog is not None and self._dialog.isVisible():
            if reminder_todos:
                self._dialog.set_todos(reminder_todos, now=current_time)
                return
            self._close_dialog()
            self._next_regular_at = None

        if not reminder_todos:
            self._next_regular_at = None
            if self._snoozed_until is not None and current_time >= self._snoozed_until:
                self._snoozed_until = None
            return

        if self._snoozed_until is not None:
            if current_time < self._snoozed_until:
                return
            self._snoozed_until = None

        if self._next_regular_at is not None and current_time < self._next_regular_at:
            return

        self._show_dialog(reminder_todos, current_time)
        self._next_regular_at = current_time + timedelta(
            minutes=self.REGULAR_REMINDER_MINUTES
        )

    def _show_dialog(self, todos: list[DueTodo], now: datetime):
        if self._dialog is None:
            self._dialog = TodoReminderDialog(
                snooze_minutes=self.config["snooze_minutes"],
                on_complete=self._complete_urgent_todo,
                on_snooze=self._snooze,
            )
        self._dialog.show_for_todos(todos, now=now)

    def _complete_urgent_todo(self, todo: DueTodo):
        actions = getattr(self.maid_window, "maid_actions", None)
        panel = getattr(actions, "todo_panel", None) if actions is not None else None
        # 提醒窗口也会写同一份数据；先提交编辑草稿，防止刷新吞掉最后一次输入。
        if panel is not None and panel.isVisible() and not panel._save_current_editor():
            if self._dialog is not None:
                self._dialog.subtitle.setText("请先修正待办编辑中的内容，再标记完成。")
            return
        if complete_todo_item(todo.date_key, todo.ddl, todo.text):
            if panel is not None and panel.isVisible():
                panel.reload_data()
        else:
            if self._dialog is not None:
                self._dialog.subtitle.setText(
                    "未能保存完成状态，请检查数据目录权限后重试。"
                )
                self._dialog.raise_()
            return

        now = datetime.now()
        remaining = find_due_todos(
            load_todo_items_by_date(),
            now,
            self.config["popup_reminder_hours"],
        )
        if remaining and self._dialog is not None:
            self._dialog.set_todos(remaining, now=now)
        else:
            self._close_dialog()
        self.check_now(now=now)

    def _snooze(self):
        self._snoozed_until = datetime.now() + timedelta(
            minutes=self.config["snooze_minutes"]
        )
        self._close_dialog()

    def _close_dialog(self):
        if self._dialog is None:
            return
        self._dialog.allow_close()
        self._dialog.close()
        self._dialog.deleteLater()
        self._dialog = None
