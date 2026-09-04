import tempfile
import unittest
from pathlib import Path

from src.config import ConfigError, load_launch_paths, load_menu_config


class MenuConfigTests(unittest.TestCase):
    def _write(self, directory: str, content: str) -> Path:
        path = Path(directory, "menu.yaml")
        path.write_text(content, encoding="utf-8")
        return path

    def test_app_and_tool_sections_are_distinct_and_nested(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                """
menus:
  APP:
    GAME:
      Steam:
        launch:
          - steam.exe
  TOOL:
    系统工具:
      截图:
        action: screenshot
    网络:
      VPN:
        launch:
          - vpn.exe
""",
            )
            config = load_menu_config(path)

            self.assertEqual(config.applications[0].label, "GAME")
            self.assertEqual(config.applications[0].children[0].label, "Steam")
            self.assertEqual(config.tools[0].children[0].action_id, "screenshot")
            self.assertEqual(config.tools[1].children[0].label, "VPN")
            self.assertEqual(
                load_launch_paths(path),
                {"Steam": ["steam.exe"], "VPN": ["vpn.exe"]},
            )

    def test_list_shorthand_is_supported_for_launchers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                """
menus:
  APP:
    Editor:
      - editor.exe
      - 123
  TOOL: {}
""",
            )
            self.assertEqual(load_launch_paths(path), {"Editor": ["editor.exe"]})

    def test_unknown_builtin_action_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                """
menus:
  APP: {}
  TOOL:
    危险操作:
      action: execute_anything
""",
            )
            with self.assertRaises(ConfigError):
                load_menu_config(path)

    def test_list_item_requires_space_after_dash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                """
menus:
  APP:
    MAA:
      ARK:
        launch:
          -E:\\MAA\\MAA.exe
  TOOL: {}
""",
            )
            with self.assertRaisesRegex(ConfigError, "第 7 行.*短横线后必须有空格"):
                load_menu_config(path)

    def test_builtin_action_cannot_be_placed_in_app(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                """
menus:
  APP:
    截图:
      action: screenshot
  TOOL: {}
""",
            )
            with self.assertRaises(ConfigError):
                load_menu_config(path)

    def test_launcher_names_must_be_unique_across_sections(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                """
menus:
  APP:
    VPN:
      launch:
        - app-vpn.exe
  TOOL:
    网络:
      vpn:
        launch:
          - tool-vpn.exe
""",
            )
            with self.assertRaises(ConfigError):
                load_menu_config(path)

    def test_launcher_candidate_count_is_rejected_instead_of_truncated(self):
        with tempfile.TemporaryDirectory() as directory:
            targets = "\n".join(f"          - app-{index}.exe" for index in range(21))
            path = self._write(
                directory,
                f"menus:\n  APP:\n    Editor:\n      launch:\n{targets}\n  TOOL: {{}}\n",
            )
            with self.assertRaisesRegex(ConfigError, "不能超过 20 条"):
                load_menu_config(path)

    def test_project_menu_contains_builtins_and_game_category(self):
        config = load_menu_config()
        self.assertIn("Steam", config.launch_paths())
        self.assertEqual(config.applications[-1].label, "GAME")
        action_ids = {entry.action_id for entry in config.iter_entries() if entry.is_action}
        self.assertEqual(
            action_ids,
            {"screenshot", "keyboard_control", "codex_status"},
        )


if __name__ == "__main__":
    unittest.main()
