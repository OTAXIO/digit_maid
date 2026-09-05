"""统一桌宠退出流程：先保护待办草稿，再停止交互，最后结束 Qt 事件循环。"""

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication


class ShutdownController(QObject):
    # GIF 损坏、不报告总帧数或永不结束时，也不能永久卡在退出状态。
    EXIT_TIMEOUT_MS = 3000

    def __init__(self, maid):
        super().__init__(maid)
        self.maid = maid
        self.finished = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.finish)

    def request_quit(self):
        if self.finished:
            return True
        if self.maid.is_dying:
            # 重复退出直接结束动画，不再像旧逻辑一样无反馈地忽略请求。
            self.finish()
            return True

        actions = self.maid.maid_actions
        panel = actions.todo_panel
        if panel is not None and not panel.prepare_for_shutdown():
            # 写盘失败或草稿不合法时保留编辑现场，不能静默丢失用户修改。
            panel.show()
            panel.raise_()
            panel.activateWindow()
            self.maid.dialogue_system.show_message(
                "暂未退出", "待办修改尚未保存，请修正编辑内容或保存问题后再退出。"
            )
            return False

        self.maid.is_dying = True
        self.maid.setEnabled(False)
        self.maid._stop_inactivity_timer(reset_stage=True)
        self.maid._stop_fall()
        self.maid._keyboard_control_mode = False
        self.maid._custom_scale_adjusting = False
        self.maid.menu_interact_mode = False
        # 停止包含子系统在内的计时器；退出看门狗在清理完毕后单独启动。
        for timer in self.maid.findChildren(QTimer):
            timer.stop()

        manager = getattr(self.maid, "todo_reminder_manager", None)
        if manager is not None:
            manager.stop()
        self.maid.dialogue_system.hide_dialogue()
        menu = getattr(actions, "circular_menu", None)
        if menu is not None:
            menu.inactivity_timer.stop()
            menu.close_menu(force=True)
        if panel is not None:
            panel.close()

        # 必须在播放前启动：首帧/解码错误可能同步触发动画结束。
        self.timer.start(self.EXIT_TIMEOUT_MS)
        if not self.maid.play_action("die", force_loop=False):
            self.finish()
            return True
        movie = self.maid.current_movie
        if movie is None or not movie.isValid():
            self.finish()
        elif not self.finished:
            # frameChanged 负责无限循环 GIF 的单次播放，这两个信号覆盖
            # 总帧数未知的有限动画，以及播放途中出现的解码错误。
            movie.finished.connect(self.finish)
            movie.error.connect(self.finish)
        return True

    def finish(self, *_signal_args):
        if self.finished or not self.maid.is_dying:
            return
        self.finished = True
        self.timer.stop()
        if self.maid.current_movie is not None:
            self.maid.current_movie.stop()
        self.maid.hide()
        app = QApplication.instance()
        if app is not None:
            # 不使用强杀进程；待办/提醒窗口已经显式允许关闭，不会否决 quit。
            app.quit()
