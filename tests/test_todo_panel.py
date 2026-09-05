import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtCore import QDate, QTime, Qt
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
        # 固定选中工作日，避免测试运行当天恰逢周末时被选中态白字覆盖。
        panel.calendar.setSelectedDate(QDate(2026, 9, 2))
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
        self.assertIs(panel.daily_stack.currentWidget(), panel.task_editor_page)
        self.assertTrue(panel.task_editor.isReadOnly())
        self.assertEqual(panel.complete_btn.text(), "未完成")
        self.assertIn("未完成", panel.complete_btn.toolTip())
        self.assertEqual(panel.edit_state_badge.text(), "已完成")
        panel.deleteLater()

    def test_clicking_active_item_uses_the_whole_daily_editor(self):
        date_key = QDate.currentDate().toString("yyyy-MM-dd")
        items = {
            date_key: [{"ddl": "09:30", "text": "提交报告", "completed": False}]
        }
        with patch("src.ui.todo_panel.load_todo_items_by_date", return_value=items):
            panel = TodoPanel()

        panel._on_today_item_selected(panel.today_list.item(0))

        self.assertIs(panel.daily_stack.currentWidget(), panel.task_editor_page)
        self.assertTrue(panel.input_card.isHidden())
        self.assertFalse(panel.task_editor.isReadOnly())
        self.assertEqual(panel.task_editor.toPlainText(), "09:30 提交报告")
        self.assertEqual(panel.delete_btn.text(), "删除")
        self.assertEqual(panel.complete_btn.text(), "已完成")
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

    def test_failed_add_is_rolled_back_and_input_is_preserved(self):
        date_key = QDate.currentDate().toString("yyyy-MM-dd")
        with (
            patch("src.ui.todo_panel.load_todo_items_by_date", return_value={}),
            patch("src.ui.todo_panel.save_todo_items_by_date", return_value=False),
        ):
            panel = TodoPanel()
            panel.ddl_input.setText("09:30")
            panel.todo_input.setText("不能丢失的输入")
            panel._submit_todo_input()

        self.assertNotIn(date_key, panel.items_by_date)
        self.assertEqual(panel.todo_input.text(), "不能丢失的输入")
        self.assertIn("保存失败", panel.subtitle_label.text())
        panel.deleteLater()

    def test_complete_while_editing_is_saved_atomically(self):
        date_key = QDate.currentDate().toString("yyyy-MM-dd")
        items = {
            date_key: [{"ddl": "09:30", "text": "旧内容", "completed": False}]
        }
        with (
            patch("src.ui.todo_panel.load_todo_items_by_date", return_value=items),
            patch("src.ui.todo_panel.save_todo_items_by_date", return_value=True) as save,
        ):
            panel = TodoPanel()
            panel._on_today_item_selected(panel.today_list.item(0))
            QApplication.processEvents()
            panel.task_editor.setPlainText("10:15 新内容")
            panel.complete_btn.click()

        self.assertEqual(save.call_count, 1)
        self.assertEqual(
            panel.items_by_date[date_key],
            [{"ddl": "10:15", "text": "新内容", "completed": True}],
        )
        self.assertTrue(panel.task_editor.isReadOnly())
        self.assertEqual(panel.complete_btn.text(), "未完成")
        self.assertEqual(panel.edit_state_badge.text(), "已完成")
        self.assertIn("已标记为完成", panel.editor_hint.text())
        self.assertEqual(panel.subtitle_label.text(), "已标记为完成")
        panel.deleteLater()

    def test_restoring_completed_item_unlocks_editor_with_feedback(self):
        date_key = QDate.currentDate().toString("yyyy-MM-dd")
        items = {
            date_key: [{"ddl": "09:30", "text": "提交报告", "completed": True}]
        }
        with (
            patch("src.ui.todo_panel.load_todo_items_by_date", return_value=items),
            patch("src.ui.todo_panel.save_todo_items_by_date", return_value=True),
        ):
            panel = TodoPanel()
            panel._on_today_item_selected(panel.today_list.item(0))
            panel.complete_btn.click()

        self.assertFalse(panel.items_by_date[date_key][0]["completed"])
        self.assertFalse(panel.task_editor.isReadOnly())
        self.assertEqual(panel.complete_btn.text(), "已完成")
        self.assertEqual(panel.edit_state_badge.text(), "待完成")
        self.assertIn("已恢复为未完成", panel.editor_hint.text())
        panel.deleteLater()

    def test_failed_completion_toggle_rolls_back_and_shows_feedback(self):
        date_key = QDate.currentDate().toString("yyyy-MM-dd")
        items = {
            date_key: [{"ddl": "09:30", "text": "提交报告", "completed": False}]
        }
        with (
            patch("src.ui.todo_panel.load_todo_items_by_date", return_value=items),
            patch("src.ui.todo_panel.save_todo_items_by_date", return_value=False),
        ):
            panel = TodoPanel()
            panel._on_today_item_selected(panel.today_list.item(0))
            panel.complete_btn.click()

        self.assertFalse(panel.items_by_date[date_key][0]["completed"])
        self.assertFalse(panel.task_editor.isReadOnly())
        self.assertEqual(panel.complete_btn.text(), "已完成")
        self.assertIn("保存失败", panel.editor_hint.text())
        panel.deleteLater()

    def test_delete_button_removes_task_and_returns_to_list(self):
        date_key = QDate.currentDate().toString("yyyy-MM-dd")
        items = {
            date_key: [{"ddl": "09:30", "text": "提交报告", "completed": False}]
        }
        with (
            patch("src.ui.todo_panel.load_todo_items_by_date", return_value=items),
            patch("src.ui.todo_panel.save_todo_items_by_date", return_value=True),
        ):
            panel = TodoPanel()
            panel._on_today_item_selected(panel.today_list.item(0))
            panel.delete_btn.click()

        self.assertNotIn(date_key, panel.items_by_date)
        self.assertIs(panel.daily_stack.currentWidget(), panel.task_list_page)
        self.assertIn("已删除", panel.subtitle_label.text())
        panel.deleteLater()

    def test_back_button_saves_edit_and_returns_to_list(self):
        date_key = QDate.currentDate().toString("yyyy-MM-dd")
        items = {
            date_key: [{"ddl": "09:30", "text": "旧内容", "completed": False}]
        }
        with (
            patch("src.ui.todo_panel.load_todo_items_by_date", return_value=items),
            patch("src.ui.todo_panel.save_todo_items_by_date", return_value=True) as save,
        ):
            panel = TodoPanel()
            panel._on_today_item_selected(panel.today_list.item(0))
            panel.task_editor.setPlainText("10:15 新内容")
            panel.back_to_list_btn.click()

        self.assertEqual(save.call_count, 1)
        self.assertEqual(
            panel.items_by_date[date_key],
            [{"ddl": "10:15", "text": "新内容", "completed": False}],
        )
        self.assertIs(panel.daily_stack.currentWidget(), panel.task_list_page)
        panel.deleteLater()

    def test_changing_date_saves_draft_to_original_date(self):
        today = QDate.currentDate()
        date_key = today.toString("yyyy-MM-dd")
        items = {date_key: [{"ddl": "09:30", "text": "旧内容", "completed": False}]}
        with (
            patch("src.ui.todo_panel.load_todo_items_by_date", return_value=items),
            patch("src.ui.todo_panel.save_todo_items_by_date", return_value=True),
        ):
            panel = TodoPanel()
            panel._on_today_item_selected(panel.today_list.item(0))
            panel.task_editor.setPlainText("10:15 新内容")
            panel.calendar.setSelectedDate(today.addDays(1))
        self.assertEqual(panel.items_by_date[date_key][0]["text"], "新内容")
        self.assertNotIn(today.addDays(1).toString("yyyy-MM-dd"), panel.items_by_date)
        self.assertIs(panel.daily_stack.currentWidget(), panel.task_list_page)
        panel.deleteLater()

    def test_invalid_draft_keeps_editor_and_date_until_corrected(self):
        today = QDate.currentDate()
        date_key = today.toString("yyyy-MM-dd")
        items = {date_key: [{"ddl": "09:30", "text": "原内容", "completed": False}]}
        with (
            patch("src.ui.todo_panel.load_todo_items_by_date", return_value=items),
            patch("src.ui.todo_panel.save_todo_items_by_date") as save,
        ):
            panel = TodoPanel()
            panel._on_today_item_selected(panel.today_list.item(0))
            panel.task_editor.setPlainText("99:99 非法时间")
            panel.calendar.setSelectedDate(today.addDays(1))
            panel.complete_btn.click()
        save.assert_not_called()
        self.assertEqual(panel.calendar.selectedDate(), today)
        self.assertIs(panel.daily_stack.currentWidget(), panel.task_editor_page)
        self.assertFalse(panel.items_by_date[date_key][0]["completed"])
        panel.deleteLater()


if __name__ == "__main__":
    unittest.main()
