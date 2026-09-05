"""覆盖真实交互风险：菜单边缘排版、长对话与气泡定时器释放。"""

import math
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtWidgets import QApplication, QWidget

from src.menu.layout import radial_layout
from src.ui.dialogue import DialogueSystem, SpeechBubble


class RadialLayoutTests(unittest.TestCase):
    def test_buttons_fit_and_do_not_overlap_at_all_corners_and_scales(self):
        for center in ((0, 0), (800, 0), (0, 600), (800, 600), (400, 300)):
            for requested in (0.4, 1.0, 4.0):
                for count in (1, 5, 7):
                    scale, positions = radial_layout(center, (800, 600), count, requested)
                    diameter = 70 * scale
                    for x, y, angle in positions:
                        self.assertGreaterEqual(x, 0)
                        self.assertGreaterEqual(y, 0)
                        self.assertLessEqual(x + diameter, 800.001)
                        self.assertLessEqual(y + diameter, 600.001)
                    for i, first in enumerate(positions):
                        for second in positions[i + 1:]:
                            self.assertGreaterEqual(math.hypot(first[0] - second[0], first[1] - second[1]), diameter)


class SpeechBubbleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_closing_stops_timers_and_does_not_clear_new_bubble(self):
        target = QWidget()
        target.setGeometry(100, 250, 120, 120)
        system = DialogueSystem(target)
        with patch("src.ui.dialogue.load_dialog_theme", return_value={}):
            system.show_message("第一条", "测试")
            old = system.current_bubble
            system.show_message("第二条", "新提示")
            self.assertFalse(old.follow_timer.isActive())
            self.assertFalse(old.timer.isActive())
            current = system.current_bubble
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.assertIs(system.current_bubble, current)
            system.hide_dialogue()
        target.deleteLater()

    def test_long_message_is_scrollable_and_within_screen(self):
        target = QWidget()
        target.user_scale = 5.0
        area = self.app.primaryScreen().availableGeometry()
        target.setGeometry(area.right() - 60, area.bottom() - 100, 60, 100)
        with patch("src.ui.dialogue.load_dialog_theme", return_value={}):
            bubble = SpeechBubble("很长的消息<br>" * 100, target)
        bubble.show()
        self.app.processEvents()
        self.assertTrue(area.contains(bubble.geometry()))
        self.assertGreater(bubble.scroll.verticalScrollBar().maximum(), 0)
        bubble.close()
        target.deleteLater()
