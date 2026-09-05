"""退出回归：真实 Qt 关闭事件、动画状态竞争、草稿保护与看门狗。"""

import os
import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QCoreApplication, QDate, QEvent, QTimer
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication, QMenu

from src.ui.maid_window import MaidWindow
from src.ui.todo_panel import TodoPanel
from src.ui.todo_reminder import DueTodo


class ShutdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        # 不读写用户待办，不改 QSettings；动画仍使用真实打包资源。
        for target in ("src.ui.todo_reminder.load_todo_items_by_date",
                       "src.ui.todo_panel.load_todo_items_by_date"):
            loader = patch(target, return_value={})
            loader.start()
            self.addCleanup(loader.stop)
        self.maid = MaidWindow()
        self.controller = self.maid.shutdown_controller

    def tearDown(self):
        self.controller.finished = True
        for timer in self.maid.findChildren(QTimer):
            timer.stop()
        self.maid.todo_reminder_manager.stop()
        self.maid.dialogue_system.hide_dialogue()
        if self.maid.current_movie is not None:
            self.maid.current_movie.stop()
        panel = self.maid.maid_actions.todo_panel
        if panel is not None:
            panel._allow_close = True
            panel.close()
        self.maid.close()
        self.maid.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_finish_has_priority_over_every_interaction_state(self):
        for flag in ("_edge_hidden", "_custom_scale_adjusting", "_keyboard_control_mode",
                     "menu_interact_mode", "_todo_panel_open", "_is_falling", "current_loop"):
            with self.subTest(flag=flag), patch.object(self.maid, flag, True), \
                 patch.object(QApplication, "quit") as quit_app, \
                 patch.object(self.maid, "play_action") as play:
                self.controller.finished = False
                self.maid.is_dying = True
                self.maid._on_action_finished()
                quit_app.assert_called_once_with()
                play.assert_not_called()

    def test_request_stops_competing_timers_and_rejects_late_actions(self):
        self.maid._is_falling = True
        self.maid._keyboard_control_mode = True
        self.maid._custom_scale_adjusting = True
        self.maid.menu_interact_mode = True
        for timer in self.maid.findChildren(QTimer):
            timer.start(10000)
        with patch.object(QApplication, "quit") as quit_app:
            self.assertTrue(self.maid.maid_actions.trigger_quit())
            self.assertTrue(self.maid.is_dying)
            self.assertFalse(self.maid.isEnabled())
            self.assertFalse(self.maid._is_falling)
            self.assertFalse(self.maid._keyboard_control_mode)
            self.assertFalse(self.maid._custom_scale_adjusting)
            self.assertEqual(self.maid.current_action, "die")
            self.assertTrue(self.controller.timer.isActive())
            for timer in self.maid.findChildren(QTimer):
                # QMovie 的内部帧计时器仍需运行，只有业务计时器必须停止。
                if timer is not self.controller.timer and timer.parent() is not self.maid.current_movie:
                    self.assertFalse(timer.isActive())
            for action in ("idle", "fly", "interact", "hide"):
                self.assertFalse(self.maid.play_action(action))
            self.maid.maid_actions.on_circular_menu_closed()
            self.maid.maid_actions.on_todo_panel_closed()
            self.assertEqual(self.maid.current_action, "die")
            self.assertFalse(self.maid._operation_allowed("allow_fall"))
            self.maid._on_action_finished()
            quit_app.assert_called_once_with()

    def test_missing_animation_exits_immediately(self):
        with patch.object(self.maid, "play_action", return_value=False), \
             patch.object(QApplication, "quit") as quit_app:
            self.assertTrue(self.maid.request_quit())
            quit_app.assert_called_once_with()
            self.assertFalse(self.controller.timer.isActive())

    def test_corrupt_animation_exits_immediately(self):
        with patch.object(self.maid, "play_action", return_value=True), \
             patch.object(self.maid.current_movie, "isValid", return_value=False), \
             patch.object(QApplication, "quit") as quit_app:
            self.maid.request_quit()
            quit_app.assert_called_once_with()

    def test_timeout_and_repeated_requests_finish_only_once(self):
        with patch.object(QApplication, "quit") as quit_app:
            self.maid.request_quit()
            self.maid.request_quit()
            self.controller.timer.timeout.emit()
            self.maid._on_action_finished()
            self.maid.request_quit()
            quit_app.assert_called_once_with()

    def test_animation_error_finishes_exit(self):
        with patch.object(QApplication, "quit") as quit_app:
            self.maid.request_quit()
            movie = self.maid.current_movie
            movie.error.emit(movie.lastError())
            quit_app.assert_called_once_with()

    def test_finished_signal_exits_when_frame_count_is_unknown(self):
        with patch.object(QApplication, "quit") as quit_app:
            self.maid.request_quit()
            movie = self.maid.current_movie
            with patch.object(movie, "frameCount", return_value=0):
                movie.frameChanged.emit(0)
                quit_app.assert_not_called()
                movie.finished.emit()
            quit_app.assert_called_once_with()

    def test_system_window_close_uses_same_exit_flow(self):
        event = QCloseEvent()
        with patch.object(self.maid, "request_quit") as request:
            self.maid.closeEvent(event)
            self.assertFalse(event.isAccepted())
            request.assert_called_once_with()
        self.controller.finished = True
        self.maid.closeEvent(event)
        self.assertTrue(event.isAccepted())

    def _open_editor(self):
        key = QDate.currentDate().toString("yyyy-MM-dd")
        items = {key: [{"ddl": "10:00", "text": "旧内容", "completed": False}]}
        with patch("src.ui.todo_panel.load_todo_items_by_date", return_value=items):
            panel = TodoPanel(parent=self.maid)
        self.maid.maid_actions.todo_panel = panel
        panel.show()
        panel._on_today_item_selected(panel.today_list.item(0))
        return panel

    def test_exit_saves_pending_editor_without_marking_it_complete(self):
        panel = self._open_editor()
        panel.task_editor.setPlainText("10:15 新内容")
        with patch("src.ui.todo_panel.save_todo_items_by_date", return_value=True) as save, \
             patch.object(QApplication, "quit"):
            self.assertTrue(self.maid.request_quit())
            save.assert_called_once()
            saved_task = next(iter(save.call_args.args[0].values()))[0]
            self.assertEqual(saved_task, {"ddl": "10:15", "text": "新内容", "completed": False})
            self.assertFalse(panel._edit_save_timer.isActive())
            self.assertFalse(panel.isVisible())
            self.assertTrue(panel._allow_close)

    def test_invalid_editor_and_save_failure_keep_app_editable_for_retry(self):
        panel = self._open_editor()
        with patch("src.ui.todo_panel.save_todo_items_by_date", return_value=False) as save, \
             patch.object(QApplication, "quit") as quit_app:
            panel.task_editor.setPlainText("99:99 非法时间")
            self.assertFalse(self.maid.request_quit())
            save.assert_not_called()
            panel.task_editor.setPlainText("10:15 未保存内容")
            self.assertFalse(self.maid.request_quit())
            save.assert_called_once()
            self.assertFalse(self.maid.is_dying)
            self.assertTrue(self.maid.isEnabled())
            self.assertTrue(panel.isVisible())
            self.assertFalse(panel._allow_close)
            self.assertEqual(panel.task_editor.toPlainText(), "10:15 未保存内容")
            quit_app.assert_not_called()
        with patch("src.ui.todo_panel.save_todo_items_by_date", return_value=True), \
             patch.object(QApplication, "quit"):
            self.assertTrue(self.maid.request_quit())

    def test_stopped_reminder_does_not_reopen_on_queued_check(self):
        manager = self.maid.todo_reminder_manager
        manager.stop()
        with patch("src.ui.todo_reminder.load_todo_items_by_date") as load:
            manager.check_now()
            load.assert_not_called()
        self.assertIsNone(manager._dialog)

    def test_real_qt_event_loop_exits_with_guarded_windows_and_nested_menu(self):
        # QApplication.quit 可能被 closeEvent.ignore 拒绝；Mock 无法覆盖该问题。
        # 每个场景使用独立进程，并在失败时返回非零码，而不是挂死整个测试。
        for scenario in ("normal", "reminder", "todo", "falling", "list-menu",
                         "circular-menu", "preview-close", "stalled", "system-close"):
            with self.subTest(scenario=scenario):
                result = subprocess.run(
                    [sys.executable, "-m", "tests.test_shutdown", "--probe", scenario],
                    cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=7,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def _run_exit_probe(scenario):
    app = QApplication([])
    with patch("src.ui.todo_reminder.load_todo_items_by_date", return_value={}), \
         patch("src.ui.todo_panel.load_todo_items_by_date", return_value={}):
        # 不排入初次检查，否则它会在退出请求之前清掉测试构造的提醒窗口。
        with patch("src.ui.todo_reminder.QTimer.singleShot"):
            maid = MaidWindow()
        maid.show()
        if scenario == "reminder":
            now = datetime.now()
            todo = DueTodo(now.date().isoformat(), "12:00", "保留的待办", now)
            maid.todo_reminder_manager._show_dialog([todo], now)
        elif scenario == "todo":
            maid.maid_actions.todo_panel = TodoPanel(parent=maid)
            maid.maid_actions.todo_panel.show()
            maid._todo_panel_open = True
        elif scenario == "falling":
            maid._is_falling = True
            maid._fall_timer.start(16)
        if scenario == "stalled":
            maid.shutdown_controller.EXIT_TIMEOUT_MS = 30
            maid.current_movie.stop()
            maid.play_action = lambda *_args, **_kwargs: True
        if scenario in ("circular-menu", "preview-close"):
            maid.maid_actions.show_circular_menu(maid.pos())
            if scenario == "preview-close":
                maid._custom_scale_adjusting = True
                maid.menu_controller.set_custom_scale_adjusting(True)
            else:
                menu = maid.maid_actions.circular_menu
                button = next(b for b in menu.buttons if b.text() == "关闭")
                QTimer.singleShot(0, button.click)
        if scenario == "list-menu":
            def click_quit():
                menu = next(w for w in app.topLevelWidgets() if isinstance(w, QMenu) and w.isVisible())
                next(a for a in menu.actions() if a.text() == "退出").trigger()
                menu.close()
            with patch("src.ui.action.load_dialog_theme", return_value={"menu_style": "default"}):
                QTimer.singleShot(20, click_quit)
                QTimer.singleShot(0, lambda: maid.maid_actions.show_context_menu(maid.pos()))
                QTimer.singleShot(4000, lambda: app.exit(97))
                return app.exec()
        if scenario != "circular-menu":
            QTimer.singleShot(0, maid.close if scenario in ("system-close", "preview-close") else maid.request_quit)
        QTimer.singleShot(4000, lambda: app.exit(97))
        return app.exec()


if __name__ == "__main__":
    if sys.argv[1:2] == ["--probe"]:
        raise SystemExit(_run_exit_probe(sys.argv[2]))
    unittest.main()
