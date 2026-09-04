"""Persistent DDL reminders and the desktop-visibility guard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Callable, Optional

from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.config import ConfigError, load_todo_reminder_config
from src.config.loader import DEFAULT_TODO_REMINDER_CONFIG
from src.function.todo_store import complete_todo_item, load_todo_items_by_date


@dataclass(frozen=True)
class DueTodo:
    date_key: str
    ddl: str
    text: str
    deadline: datetime


def find_due_todos(items_by_date, now: datetime, within_hours: float) -> list[DueTodo]:
    """Return today's overdue and upcoming tasks inside the requested window.

    Overdue items remain actionable until local midnight. Older dates are not
    carried forever, which prevents abandoned history from permanently locking
    the pet out of edge-hiding mode.
    """

    if not isinstance(items_by_date, dict):
        return []

    window_start = datetime.combine(now.date(), time.min)
    window_end = now + timedelta(hours=max(0.0, float(within_hours)))
    matches: list[DueTodo] = []

    for raw_date, raw_tasks in items_by_date.items():
        try:
            parsed_date = date.fromisoformat(str(raw_date).strip())
        except ValueError:
            continue
        if not isinstance(raw_tasks, list):
            continue

        for raw_task in raw_tasks:
            if not isinstance(raw_task, dict):
                continue
            ddl = str(raw_task.get("ddl", "")).strip()
            text_value = str(raw_task.get("text", "")).strip()
            if not ddl or not text_value:
                continue
            try:
                parsed_time = time.fromisoformat(ddl)
            except ValueError:
                continue

            deadline = datetime.combine(parsed_date, parsed_time)
            if window_start <= deadline <= window_end:
                matches.append(
                    DueTodo(
                        date_key=parsed_date.isoformat(),
                        ddl=parsed_time.strftime("%H:%M"),
                        text=text_value,
                        deadline=deadline,
                    )
                )

    matches.sort(key=lambda item: (item.deadline, item.text))
    return matches


def _remaining_text(deadline: datetime, now: datetime) -> str:
    seconds = int((deadline - now).total_seconds())
    minutes = max(1, (abs(seconds) + 59) // 60)
    hours, rest = divmod(minutes, 60)
    if hours:
        duration = f"{hours} 小时 {rest} 分钟" if rest else f"{hours} 小时"
    else:
        duration = f"{rest} 分钟"
    return f"已超时 {duration}" if seconds < 0 else f"还有 {duration}"


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
        self._snooze_minutes = int(snooze_minutes)
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
        self.card.setStyleSheet(
            """
            QFrame#reminder_card {
                background: #fffaf7;
                border: 1px solid #ead7d2;
                border-radius: 24px;
            }
            QFrame#reminder_card * {
                font-family: "PingFang SC", "Microsoft YaHei UI", sans-serif;
                color: #2d2321;
            }
            QLabel#eyebrow {
                color: #bf2b2b;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QLabel#reminder_title {
                color: #241c1a;
                font-size: 26px;
                font-weight: 700;
            }
            QLabel#reminder_subtitle {
                color: #806b66;
                font-size: 12px;
                font-weight: 400;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QFrame#urgent_item {
                background: #fff0ec;
                border: 2px solid #c62d2d;
                border-radius: 16px;
            }
            QFrame#queued_item {
                background: #ffffff;
                border: 1px solid #eadedb;
                border-radius: 14px;
            }
            QLabel#task_time {
                color: #c62d2d;
                font-size: 18px;
                font-weight: 700;
            }
            QLabel#task_text {
                color: #2d2321;
                font-size: 15px;
                font-weight: 600;
            }
            QLabel#task_remaining {
                color: #8c716b;
                font-size: 11px;
                font-weight: 400;
            }
            QPushButton {
                min-height: 42px;
                border-radius: 12px;
                padding: 0 18px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#complete_btn {
                color: #ffffff;
                background: #b82323;
                border: 1px solid #b82323;
            }
            QPushButton#complete_btn:hover { background: #cf3434; }
            QPushButton#complete_btn:pressed { background: #921b1b; }
            QPushButton#snooze_btn {
                color: #634d48;
                background: #f3e9e5;
                border: 1px solid #e7d6d1;
            }
            QPushButton#snooze_btn:hover { background: #eadbd6; }
            """
        )

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(55, 25, 22, 85))
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(26, 24, 26, 24)
        card_layout.setSpacing(8)

        eyebrow = QLabel("DDL REMINDER", self.card)
        eyebrow.setObjectName("eyebrow")
        card_layout.addWidget(eyebrow)

        title = QLabel("有一件事需要你", self.card)
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
        self._todos = list(todos)
        current_time = now or datetime.now()
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
        current_time = now or datetime.now()
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
        if complete_todo_item(todo.date_key, todo.ddl, todo.text):
            actions = getattr(self.maid_window, "maid_actions", None)
            panel = getattr(actions, "todo_panel", None) if actions is not None else None
            if panel is not None and panel.isVisible():
                panel.reload_data()

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
