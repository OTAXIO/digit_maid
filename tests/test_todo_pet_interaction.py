"""待办打开时允许桌宠移动，但菜单互斥与临期隐藏保护仍须生效。"""

from copy import deepcopy
from datetime import datetime
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, Qt, QTimer
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication

from src.ui.maid_window import MaidWindow
from src.ui.menu_controller import OptionMenuController


class TodoPetPolicyTests(unittest.TestCase):
    def test_todo_allows_manual_movement_but_not_menu_or_auto_wander(self):
        controller = OptionMenuController()
        controller.set_todo_panel_open(True)
        for permission in ("allow_drag", "allow_fall"):
            self.assertTrue(controller.allows(permission))
        for permission in ("allow_open_menu", "allow_idle_timer", "allow_wander", "allow_double_click"):
            self.assertFalse(controller.allows(permission))
        controller.set_todo_panel_open(False)
        self.assertTrue(controller.allows("allow_open_menu"))

    def test_scale_preview_stays_locked_if_states_overlap(self):
        controller = OptionMenuController()
        controller.set_custom_scale_adjusting(True)
        controller.set_todo_panel_open(True)
        self.assertFalse(controller.allows("allow_drag"))
        self.assertFalse(controller.allows("allow_fall"))


class TodoPetInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.stored = {}
        for target in ("src.ui.todo_panel.load_todo_items_by_date",
                       "src.ui.todo_reminder.load_todo_items_by_date"):
            loader = patch(target, side_effect=lambda: deepcopy(self.stored))
            loader.start()
            self.addCleanup(loader.stop)
        saver = patch("src.ui.todo_panel.save_todo_items_by_date", side_effect=self._save)
        saver.start()
        self.addCleanup(saver.stop)
        with patch("src.ui.todo_reminder.QTimer.singleShot"):
            self.maid = MaidWindow()
        self.maid.todo_reminder_manager.config["desktop_guard_hours"] = 2
        self.maid.anim_cfg["fall_mode"] = "smooth"
        self.maid.move(200, 150)
        self.maid.show()
        self.actions = self.maid.maid_actions
        self.assertTrue(self.actions.show_todo_panel())
        self.panel = self.actions.todo_panel

    def tearDown(self):
        self.maid.shutdown_controller.finished = True
        self.maid.todo_reminder_manager.stop()
        self.maid.dialogue_system.hide_dialogue()
        for timer in self.maid.findChildren(QTimer):
            timer.stop()
        self.maid.current_movie.stop()
        self.panel._edit_save_timer.stop()
        self.panel._allow_close = True
        self.panel.close()
        self.panel.deleteLater()
        self.maid.close()
        self.maid.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def _save(self, items):
        self.stored = deepcopy(items)
        return True

    def _mouse(self, kind, global_pos):
        local_pos = self.maid.mapFromGlobal(global_pos)
        event = QMouseEvent(
            kind, QPointF(local_pos), QPointF(global_pos),
            Qt.MouseButton.NoButton if kind == QEvent.Type.MouseMove else Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease else Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(self.maid, event)

    def _drag_to(self, top_left):
        grab_offset = QPoint(20, 20)
        self._mouse(QEvent.Type.MouseButtonPress, self.maid.pos() + grab_offset)
        self._mouse(QEvent.Type.MouseMove, top_left + grab_offset)
        self._mouse(QEvent.Type.MouseButtonRelease, top_left + grab_offset)

    def _due_items(self, completed=False):
        now = datetime.now()
        return {now.date().isoformat(): [{
            "ddl": now.strftime("%H:%M"), "text": "临期测试事项", "completed": completed,
        }]}

    def test_drag_moves_pet_without_moving_or_closing_todo_panel(self):
        panel_geometry = self.panel.geometry()
        original = self.maid.pos()
        self._drag_to(QPoint(350, 100))
        self.assertNotEqual(self.maid.pos(), original)
        self.assertEqual(self.maid.x(), 350)
        self.assertTrue(self.maid._is_falling)
        self.assertEqual(self.maid.current_action, "fly")
        self.assertTrue(self.panel.isVisible())
        self.assertEqual(self.panel.geometry(), panel_geometry)
        # 即使发生动作结束回调，待办的交互状态也不能替换下落动作。
        self.maid._on_action_finished()
        self.assertEqual(self.maid.current_action, "fly")

    def test_drag_to_either_edge_hides_and_click_wakes_without_unlocking_menu(self):
        area = self.maid.screen().availableGeometry()
        for side, x in (("left", area.left() - 100), ("right", area.right() + 100)):
            with self.subTest(side=side):
                self._drag_to(QPoint(x, area.top() + 100))
                self.assertTrue(self.maid._edge_hidden)
                self.assertEqual(self.maid._edge_hidden_side, side)
                self.assertEqual(self.maid.current_action, "hide")
                self.assertTrue(self.panel.isVisible())
                self.assertFalse(self.actions.can_open_menu())
                self._mouse(QEvent.Type.MouseButtonPress, self.maid.pos() + QPoint(10, 10))
                self.assertFalse(self.maid._edge_hidden)
                self.assertTrue(self.panel.isVisible())
                self.assertFalse(self.actions.can_open_menu())

    def test_new_due_task_blocks_hiding_before_next_regular_check(self):
        self.assertFalse(self.maid._deadline_guard_active)
        self.stored = self._due_items()
        self._drag_to(QPoint(-100, 100))
        self.assertTrue(self.maid._deadline_guard_active)
        self.assertFalse(self.maid._edge_hidden)
        self.assertTrue(self.panel.isVisible())
        # 保护只限制隐藏，不限制用户继续拖动。
        self._drag_to(QPoint(350, 100))
        self.assertEqual(self.maid.x(), 350)

    def test_saving_due_task_wakes_hidden_pet_without_popup_or_menu_unlock(self):
        self._drag_to(QPoint(-100, 100))
        self.assertTrue(self.maid._edge_hidden)
        self.panel.items_by_date = self._due_items()
        manager = self.maid.todo_reminder_manager
        with patch.object(manager, "_show_dialog") as popup:
            self.assertTrue(self.panel._persist_items())
            popup.assert_not_called()
        self.assertFalse(self.maid._edge_hidden)
        self.assertTrue(self.maid._deadline_guard_active)
        self.assertTrue(self.panel.isVisible())
        self.assertFalse(self.actions.can_open_menu())

    def test_completed_or_removed_due_task_releases_only_hidden_guard(self):
        for remaining in (self._due_items(completed=True), {}):
            self.panel.items_by_date = self._due_items()
            self.panel._persist_items()
            self.assertTrue(self.maid._deadline_guard_active)
            self.panel.items_by_date = remaining
            self.panel._persist_items()
            self.assertFalse(self.maid._deadline_guard_active)
            self._drag_to(QPoint(-100, 100))
            self.assertTrue(self.maid._edge_hidden)
            self.assertFalse(self.actions.can_open_menu())

    def test_drag_respects_selected_fall_mode(self):
        for mode in ("none", "direct", "smooth"):
            with self.subTest(mode=mode):
                self.maid.anim_cfg["fall_mode"] = mode
                self._drag_to(QPoint(350, 100))
                self.assertEqual(self.maid._is_falling, mode != "none")
                self.assertEqual(self.maid.current_action, "idle" if mode == "none" else "fly")
                self.assertTrue(self.panel.isVisible())

    def test_all_menu_entry_points_are_blocked_without_interrupting_motion(self):
        self._drag_to(QPoint(350, 100))
        with patch.object(self.maid, "play_action") as play, \
             patch("src.ui.action.QMenu") as list_menu, \
             patch("src.ui.action.CircularMenuWidget") as circular:
            self.assertFalse(self.maid._request_context_menu(self.maid.pos()))
            self.assertFalse(self.actions.show_context_menu(self.maid.pos()))
            self.assertFalse(self.actions.show_circular_menu(self.maid.pos()))
            play.assert_not_called()
            list_menu.assert_not_called()
            circular.assert_not_called()
        self.assertTrue(self.maid._is_falling)

    def test_successful_close_unlocks_menu_and_restores_idle_timer(self):
        self.maid.move(200, self.maid._bottom_y_limit())
        self.panel._close_from_symbol()
        self.assertFalse(self.panel.isVisible())
        self.assertFalse(self.maid._is_todo_panel_effectively_open())
        self.assertTrue(self.actions.can_open_menu())
        self.assertTrue(self.maid.inactivity_timer.isActive())

    def test_failed_close_keeps_menu_locked_but_drag_available(self):
        self.stored = self._due_items()
        self.panel.reload_data()
        self.panel._on_today_item_selected(self.panel.today_list.item(0))
        self.panel.task_editor.setPlainText("99:99 非法时间")
        self.panel._close_from_symbol()
        self.assertTrue(self.panel.isVisible())
        self.assertFalse(self.actions.can_open_menu())
        self.assertTrue(self.maid._operation_allowed("allow_drag"))

    def test_closing_panel_while_pet_is_hidden_does_not_wake_it(self):
        self._drag_to(QPoint(-100, 100))
        self.panel._close_from_symbol()
        self.assertFalse(self.panel.isVisible())
        self.assertTrue(self.maid._edge_hidden)
        self.assertEqual(self.maid.current_action, "hide")
        self.maid._wake_from_edge_hidden_mode()
        self.assertTrue(self.actions.can_open_menu())


if __name__ == "__main__":
    unittest.main()
