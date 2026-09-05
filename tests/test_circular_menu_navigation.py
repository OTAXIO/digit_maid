import os
import math
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtCore import QPoint, QRect
    from PyQt6.QtWidgets import QApplication

    from src.input.circular_menu import CircularMenuWidget
    from src.menu.circular_builder import build_circular_items
    from src.menu.model import MenuEntry
except ImportError as exc:  # Linux runners may not provide Qt's optional EGL library.
    QApplication = None
    QT_IMPORT_ERROR = str(exc)
else:
    QT_IMPORT_ERROR = ""


@unittest.skipIf(QApplication is None, f"Qt runtime unavailable: {QT_IMPORT_ERROR}")
class CircularMenuNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _labels(widget):
        return {button.text().replace("\n", "") for button in widget.buttons}

    @staticmethod
    def _click(widget, label):
        button = next(
            button
            for button in widget.buttons
            if button.text().replace("\n", "") == label
        )
        button.click()
        QApplication.processEvents()

    def test_nested_yaml_categories_render_buttons_after_click(self):
        entries = (
            MenuEntry(
                label="GAME",
                children=(
                    MenuEntry(label="Steam", launch_targets=("steam.exe",)),
                    MenuEntry(
                        label="MAA",
                        children=(
                            MenuEntry(label="ARK", launch_targets=("maa.exe",)),
                            MenuEntry(label="END", launch_targets=("maa-end.exe",)),
                        ),
                    ),
                ),
            ),
        )
        items = build_circular_items(
            entries,
            launch_handler=lambda _name: None,
            action_handlers={},
        )
        screen = QApplication.primaryScreen().availableGeometry()
        widget = CircularMenuWidget(items, QPoint(screen.center()))
        self.addCleanup(widget.close_menu, True)

        self.assertEqual(self._labels(widget), {"GAME"})
        self._click(widget, "GAME")
        self.assertEqual(self._labels(widget), {"返回", "Steam", "MAA"})
        self._click(widget, "MAA")
        self.assertEqual(self._labels(widget), {"返回", "ARK", "END"})

    def test_edge_menu_keeps_pet_anchor_on_offset_screen_and_icon_fallback(self):
        # 模拟左侧副屏和顶部任务栏，验证全局坐标转局部坐标只发生一次。
        area = QRect(-1600, 40, 800, 600)
        screen = Mock()
        screen.availableGeometry.return_value = area
        items = [{'label': str(i), 'action': lambda: None} for i in range(5)]
        items.append({'label': '退出', 'action': lambda: None})
        for mode in ('default', 'image'):
            theme = {'circular_button_mode': mode,
                     'circular_btn_select': 'resource/button/select.png',
                     'circular_btn_quit': 'missing-test-icon.png'}
            with patch('src.input.circular_menu.QApplication.screenAt', return_value=screen), \
                 patch('src.input.circular_menu.load_dialog_theme', return_value=theme):
                for center in (QPoint(0, 0), QPoint(800, 0), QPoint(0, 600),
                               QPoint(800, 600), QPoint(25, 300)):
                    with self.subTest(mode=mode, center=center):
                        widget = CircularMenuWidget(items, area.topLeft() + center, menu_scale=0.83)
                        try:
                            self.assertEqual(widget._global_to_local(widget.center_pos), center)
                            if mode == 'image':
                                self.assertTrue(widget.buttons[0].image_mode)
                                self.assertFalse(widget.buttons[-1].image_mode)
                            radius = None
                            for button in widget.buttons:
                                button.anim.stop()
                                start = button.anim.startValue()
                                target = button.anim.endValue()
                                self.assertAlmostEqual(start.x() + start.width() / 2, center.x(), delta=1)
                                self.assertAlmostEqual(start.y() + start.height() / 2, center.y(), delta=1)
                                dx = button.base_x + button.width() / 2 - center.x()
                                dy = button.base_y + button.height() / 2 - center.y()
                                distance = math.hypot(dx, dy)
                                if radius is None:
                                    radius = distance
                                self.assertAlmostEqual(distance, radius, places=7)
                                self.assertAlmostEqual(dx, radius * math.cos(button.angle), places=7)
                                self.assertAlmostEqual(dy, -radius * math.sin(button.angle), places=7)
                                self.assertTrue(widget.rect().contains(target))
                        finally:
                            widget.close_menu(force=True)
                            widget.deleteLater()


if __name__ == "__main__":
    unittest.main()
