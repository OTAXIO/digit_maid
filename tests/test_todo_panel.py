import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtCore import QDate, Qt
    from PyQt6.QtWidgets import QApplication

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


if __name__ == "__main__":
    unittest.main()
