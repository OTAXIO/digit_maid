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
    def assert_anchored(self, center, scale, positions, base_size=70):
        radii = [math.hypot(x + base_size * scale / 2 - center[0],
                            y + base_size * scale / 2 - center[1])
                 for x, y, _ in positions]
        for (x, y, angle), radius in zip(positions, radii):
            self.assertAlmostEqual(radius, radii[0], places=7)
            self.assertAlmostEqual(x + base_size * scale / 2,
                                   center[0] + radius * math.cos(angle), places=7)
            self.assertAlmostEqual(y + base_size * scale / 2,
                                   center[1] - radius * math.sin(angle), places=7)

    def test_buttons_fit_and_do_not_overlap_at_all_corners_and_scales(self):
        centers = ((0, 0), (800, 0), (0, 600), (800, 600), (400, 300),
                   (0, 300), (800, 300), (400, 0), (400, 600), (35, 550))
        for center in centers:
            for requested in (0.4, 0.83, 1.0, 4.0):
                for count in (1, 2, 5, 7):
                    for base_size in (70, 80):
                        with self.subTest(center=center, scale=requested, count=count, size=base_size):
                            scale, positions = radial_layout(center, (800, 600), count, requested, base_size)
                            self.assertGreaterEqual(scale, 0.4)
                            self.assertLessEqual(scale, requested)
                            self.assertEqual(len(positions), count)
                            self.assert_anchored(center, scale, positions, base_size)
                            diameter = base_size * scale
                            for x, y, angle in positions:
                                self.assertGreaterEqual(x, 11.999)
                                self.assertGreaterEqual(y, 11.999)
                                self.assertLessEqual(x + diameter, 788.001)
                                self.assertLessEqual(y + diameter, 588.001)
                            for i, first in enumerate(positions):
                                for second in positions[i + 1:]:
                                    self.assertGreaterEqual(math.hypot(first[0] - second[0], first[1] - second[1]), diameter)

    def test_spacious_layout_preserves_old_upper_semicircle_order(self):
        scale, positions = radial_layout((960, 800), (1920, 1080), 5)
        self.assertEqual(scale, 1.0)
        self.assertEqual([round(a, 7) for _, _, a in positions],
                         [round(math.pi - i * math.pi / 4, 7) for i in range(5)])
        self.assert_anchored((960, 800), scale, positions)

    def test_empty_menu_and_tiny_work_area_keep_safe_scale(self):
        self.assertEqual(radial_layout((0, 0), (800, 600), 0), (1.0, []))
        scale, positions = radial_layout((0, 0), (50, 50), 7, 4.0, 80)
        self.assertEqual(scale, 0.4)
        self.assert_anchored((0, 0), scale, positions, 80)


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
