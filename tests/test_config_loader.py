import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import (
    ConfigError,
    load_animation_config,
    load_dialog_theme,
    load_todo_reminder_config,
)


class ConfigLoaderTests(unittest.TestCase):
    def _write(self, directory: str, name: str, content: str) -> Path:
        path = Path(directory, name)
        path.write_text(content, encoding="utf-8")
        return path

    def test_unsafe_yaml_constructor_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "theme.yaml",
                "!!python/object/apply:os.system ['echo unsafe']",
            )
            with self.assertRaises(ConfigError):
                load_dialog_theme(path)

    def test_yaml_aliases_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "theme.yaml",
                "theme: &base\n  menu_style: circular\ncopy: *base\n",
            )
            with self.assertRaises(ConfigError):
                load_dialog_theme(path)

    def test_duplicate_yaml_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "theme.yaml",
                "menu_style: list\nmenu_style: circular\n",
            )
            with self.assertRaisesRegex(ConfigError, "键名重复"):
                load_dialog_theme(path)

    def test_non_finite_yaml_numbers_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "todo.yaml",
                "desktop_guard_hours: 1.0e999\n",
            )
            with self.assertRaisesRegex(ConfigError, "有限值"):
                load_todo_reminder_config(path)

    def test_excessive_yaml_nesting_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            lines = [f"{'  ' * depth}level_{depth}:" for depth in range(35)]
            lines.append(f"{'  ' * 35}value: true")
            path = self._write(directory, "deep.yaml", "\n".join(lines))
            with self.assertRaisesRegex(ConfigError, "嵌套过深"):
                load_dialog_theme(path)

    def test_oversized_config_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(directory, "large.yaml", "key: " + "x" * (256 * 1024))
            with self.assertRaisesRegex(ConfigError, "配置文件过大"):
                load_dialog_theme(path)

    def test_animation_paths_are_confined_to_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "animations.yaml",
                """
base_dir: ../../private
fall_mode: direct
idle_mode: lazy
actions:
  idle: relax.gif
  unsafe: ../secret.gif
loops:
  idle: true
""",
            )
            config = load_animation_config(path)
            self.assertEqual(config["base_dir"], "resource/wisdel/皮肤素材/可用素材")
            self.assertEqual(config["fall_mode"], "direct")
            self.assertEqual(config["idle_mode"], "lazy")
            self.assertEqual(config["actions"], {"idle": "relax.gif"})
            self.assertTrue(config["loops"]["idle"])

    def test_theme_values_are_normalized(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "theme.yaml",
                "outline_button_text: true\nmenu_style: circular\nnested:\n  ignored: true\n",
            )
            self.assertEqual(
                load_dialog_theme(path),
                {"outline_button_text": "true", "menu_style": "circular"},
            )

    def test_todo_reminder_values_are_bounded_independently(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "todo.yaml",
                "desktop_guard_hours: 3.5\npopup_reminder_hours: -1\nsnooze_minutes: 45\n",
            )
            self.assertEqual(
                load_todo_reminder_config(path),
                {
                    "desktop_guard_hours": 3.5,
                    "popup_reminder_hours": 1.0,
                    "snooze_minutes": 45,
                },
            )

    def test_programmatic_nan_reminder_value_uses_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "todo.yaml",
                "desktop_guard_hours: 2\npopup_reminder_hours: 1\nsnooze_minutes: 30\n",
            )
            with patch(
                "src.config.loader.load_yaml_mapping",
                return_value={"desktop_guard_hours": float("nan")},
            ):
                config = load_todo_reminder_config(path)
            self.assertEqual(config["desktop_guard_hours"], 2.0)


if __name__ == "__main__":
    unittest.main()
