import unittest
from unittest.mock import Mock, patch

try:
    from src.ui.action import MaidActions, codex_status
    from src.config import ConfigError
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

    def test_vpn_launcher_uses_tool_dialogue(self):
        with patch.object(
            self.actions,
            "_open_configured_launcher",
            return_value="已启动v2rayN",
        ) as launch:
            result = self.actions.do_open_tool("v2rayN")

        self.assertEqual(result, "已启动v2rayN")
        launch.assert_called_once_with("v2rayN", "启动VPN")

    def test_menu_config_error_is_visible_in_dialogue(self):
        with patch("src.ui.action.load_menu_config", side_effect=ConfigError("第 7 行有误")):
            config = self.actions._read_menu_config()

        self.assertEqual(config.applications, ())
        self.assertEqual(config.tools, ())
        self.dialogue.show_message.assert_called_once_with(
            "菜单配置错误",
            "请检查 config/menu.yaml：第 7 行有误",
            duration_ms=10000,
        )


if __name__ == "__main__":
    unittest.main()
