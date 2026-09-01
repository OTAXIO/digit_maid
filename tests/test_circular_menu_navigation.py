import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtCore import QPoint
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


if __name__ == "__main__":
    unittest.main()
