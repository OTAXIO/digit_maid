import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtCore import QDate, QTime, Qt
    from PyQt6.QtWidgets import QApplication, QTextEdit

    from src.ui.todo_panel import TodoPanel, WEEKEND_TEXT_COLOR
except (ImportError, OSError) as exc:  # pragma: no cover - exercised by Qt-less CI only
    QApplication = None
    QT_IMPORT_ERROR = exc
else:
    QT_IMPORT_ERROR = None


@unittest.skipIf(QApplication is None, f"Qt runtime unavailable: {QT_IMPORT_ERROR}")
class TodoPanelStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_weekend_headers_and_dates_use_dark_red(self):
        with patch("src.ui.todo_panel.load_todo_items_by_date", return_value={}):
            panel = TodoPanel()
        panel.calendar.setCurrentPage(2026, 9)
        panel._refresh_calendar_marks()

        expected = WEEKEND_TEXT_COLOR
        self.assertEqual(
            panel.calendar.weekdayTextFormat(Qt.DayOfWeek.Saturday)
            .foreground()
            .color()
            .name(),
            expected,
        )
        self.assertEqual(
            panel.calendar.weekdayTextFormat(Qt.DayOfWeek.Sunday)
            .foreground()
            .color()
            .name(),
            expected,
        )
        self.assertEqual(
            panel.calendar.dateTextFormat(QDate(2026, 9, 5))
            .foreground()
            .color()
            .name(),
            expected,
        )
        self.assertEqual(
            panel.calendar.dateTextFormat(QDate(2026, 9, 6))
            .foreground()
            .color()
            .name(),
            expected,
        )
        panel.deleteLater()

    def test_default_ddl_uses_current_time(self):
        expected_before = QTime.currentTime().toString("HH:mm")
        with patch("src.ui.todo_panel.load_todo_items_by_date", return_value={}):
            panel = TodoPanel()
        expected_after = QTime.currentTime().toString("HH:mm")

        self.assertIn(panel.ddl_input.text(), {expected_before, expected_after})
        panel.deleteLater()

    def test_completed_item_is_styled_and_not_editable(self):
        items = {
            QDate.currentDate().toString("yyyy-MM-dd"): [
                {
                    "ddl": "09:30",
                    "text": "已整理报告",
                    "completed": True,
                }
            ]
        }
        with patch("src.ui.todo_panel.load_todo_items_by_date", return_value=items):
            panel = TodoPanel()

        completed_item = panel.today_list.item(0)
        self.assertTrue(completed_item.font().strikeOut())
        self.assertFalse(completed_item.flags() & Qt.ItemFlag.ItemIsEditable)

        panel._on_today_item_selected(completed_item)
        self.assertEqual(panel.complete_btn.text(), "↩")
        self.assertIn("未完成", panel.complete_btn.toolTip())
        self.assertIsNone(panel.today_list.findChild(QTextEdit))
        panel.deleteLater()

    def test_completion_toggle_keeps_task_and_changes_its_state(self):
        date_key = QDate.currentDate().toString("yyyy-MM-dd")
        items = {
            date_key: [
                {"ddl": "09:30", "text": "提交报告", "completed": False}
            ]
        }
        with (
            patch("src.ui.todo_panel.load_todo_items_by_date", return_value=items),
            patch("src.ui.todo_panel.save_todo_items_by_date", return_value=True),
        ):
            panel = TodoPanel()
            panel._editing_index = 0
            panel._last_editing_index = 0
            panel._toggle_selected_completion()

        tasks = panel.items_by_date[date_key]
        self.assertEqual(len(tasks), 1)
        self.assertTrue(tasks[0]["completed"])
        panel.deleteLater()


if __name__ == "__main__":
    unittest.main()
