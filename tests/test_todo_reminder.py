import math
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from PyQt6.QtCore import QCoreApplication, QObject

from src.ui.todo_reminder import TodoReminderManager, find_due_todos


class TodoReminderTests(unittest.TestCase):
    def test_due_window_includes_today_overdue_and_upcoming(self):
        now = datetime(2026, 9, 4, 10, 0)
        items = {
            "2026-09-03": [{"ddl": "23:59", "text": "旧事项"}],
            "2026-09-04": [
                {"ddl": "09:50", "text": "已超时"},
                {"ddl": "10:45", "text": "即将到期"},
                {"ddl": "10:15", "text": "已经完成", "completed": True},
                {"ddl": "12:01", "text": "窗口外"},
                {"ddl": "bad", "text": "无效时间"},
            ],
        }

        due = find_due_todos(items, now, within_hours=2)

        self.assertEqual([item.text for item in due], ["已超时", "即将到期"])

    def test_due_window_sorts_by_deadline(self):
        now = datetime(2026, 9, 4, 10, 0)
        items = {
            "2026-09-04": [
                {"ddl": "10:40", "text": "第二项"},
                {"ddl": "10:20", "text": "第一项"},
            ]
        }

        due = find_due_todos(items, now, within_hours=1)

        self.assertEqual([item.ddl for item in due], ["10:20", "10:40"])

    def test_invalid_or_overflowing_windows_do_not_crash(self):
        now = datetime.max.replace(hour=10, minute=0)
        items = {now.date().isoformat(): [{"ddl": "10:01", "text": "事项"}]}

        self.assertEqual(find_due_todos(items, now, within_hours=math.nan), [])
        self.assertEqual(find_due_todos(items, now, within_hours=10**1000), [])

    def test_timezone_qualified_ddl_is_rejected(self):
        now = datetime(2026, 9, 4, 10, 0)
        items = {
            "2026-09-04": [{"ddl": "10:30+08:00", "text": "非法时区时间"}]
        }
        self.assertEqual(find_due_todos(items, now, within_hours=1), [])

    def test_visible_dialog_closes_when_no_due_items_remain(self):
        app = QCoreApplication.instance() or QCoreApplication([])
        parent = QObject()
        parent.set_deadline_guard_active = Mock()
        with (
            patch("src.ui.todo_reminder.load_todo_reminder_config", return_value={
                "desktop_guard_hours": 2.0,
                "popup_reminder_hours": 1.0,
                "snooze_minutes": 30,
            }),
            patch("src.ui.todo_reminder.QTimer.singleShot"),
        ):
            manager = TodoReminderManager(parent)
        manager.timer.stop()
        dialog = Mock()
        dialog.isVisible.return_value = True
        manager._dialog = dialog

        with patch("src.ui.todo_reminder.load_todo_items_by_date", return_value={}):
            manager.check_now(now=datetime(2026, 9, 4, 10, 0))

        dialog.allow_close.assert_called_once_with()
        dialog.close.assert_called_once_with()
        dialog.deleteLater.assert_called_once_with()
        self.assertIsNone(manager._dialog)
        self.assertIsNotNone(app)


if __name__ == "__main__":
    unittest.main()
