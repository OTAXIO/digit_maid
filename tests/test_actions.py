import unittest
from unittest.mock import Mock, patch

try:
    from src.ui.action import MaidActions, codex_status
except ImportError as exc:  # Linux runners may not provide Qt's optional EGL library.
    MaidActions = None
    codex_status = None
    QT_IMPORT_ERROR = str(exc)
else:
    QT_IMPORT_ERROR = ""


class _Parent:
    def __init__(self):
        self.play_action = Mock()


@unittest.skipIf(MaidActions is None, f"Qt runtime unavailable: {QT_IMPORT_ERROR}")
class MaidActionsTests(unittest.TestCase):
    def setUp(self):
        self.parent = _Parent()
        self.dialogue = Mock()
        self.actions = MaidActions(self.parent, self.dialogue)

    def test_codex_status_uses_extended_display_duration(self):
        with patch.object(
            codex_status,
            "get_codex_status_message",
            return_value=("Codex", "运行中"),
        ):
            self.assertTrue(self.actions.show_codex_status())

        self.dialogue.show_message.assert_called_once_with(
            "Codex",
            "运行中",
            duration_ms=8000,
        )

    def test_circular_app_items_follow_nested_config(self):
        items = self.actions._build_circular_app_items(
            {
                "Editor": ["editor.exe"],
                "GAME": {
                    "Steam": ["steam.exe"],
                    "鹰角启动": ["launcher.exe"],
                },
            }
        )

        self.assertEqual([item["label"] for item in items], ["Editor", "GAME"])
        game_items = items[1]["action"]
        self.assertEqual([item["label"] for item in game_items], ["Steam", "鹰角启动"])


if __name__ == "__main__":
    unittest.main()
