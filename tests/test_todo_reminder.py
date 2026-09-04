import unittest
from datetime import datetime

from src.ui.todo_reminder import find_due_todos


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


if __name__ == "__main__":
    unittest.main()
