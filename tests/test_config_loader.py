import tempfile
import unittest
from pathlib import Path

from src.config.loader import (
    ConfigError,
    load_animation_config,
    load_app_menu,
    load_app_paths,
    load_dialog_theme,
)


class ConfigLoaderTests(unittest.TestCase):
    def _write(self, directory: str, name: str, content: str) -> Path:
        path = Path(directory, name)
        path.write_text(content, encoding="utf-8")
        return path

    def test_application_schema_drops_invalid_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "apps.yaml",
                """
app_paths:
  Editor:
    - editor.exe
    - 123
  Empty: []
""",
            )
            self.assertEqual(load_app_paths(path), {"Editor": ["editor.exe"]})

    def test_unsafe_yaml_constructor_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "apps.yaml",
                "!!python/object/apply:os.system ['echo unsafe']",
            )
            with self.assertRaises(ConfigError):
                load_app_paths(path)

    def test_restricted_yaml_supports_project_scalar_subset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "apps.yaml",
                """
app_paths:
  Editor:
    - 'C:\\Program Files\\Editor\\editor.exe'
    - editor
  Disabled: []
""",
            )
            self.assertEqual(
                load_app_paths(path),
                {"Editor": [r"C:\Program Files\Editor\editor.exe", "editor"]},
            )

    def test_yaml_aliases_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "apps.yaml",
                "app_paths: &apps\n  Editor:\n    - editor.exe\ncopy: *apps\n",
            )
            with self.assertRaises(ConfigError):
                load_app_paths(path)

    def test_nested_app_categories_are_preserved_and_flattened(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "apps.yaml",
                """
app_paths:
  Editor:
    - editor.exe
  GAME:
    Steam:
      - steam.exe
    Launchers:
      Hypergryph:
        - launcher.exe
""",
            )
            self.assertEqual(
                load_app_menu(path),
                {
                    "Editor": ["editor.exe"],
                    "GAME": {
                        "Steam": ["steam.exe"],
                        "Launchers": {"Hypergryph": ["launcher.exe"]},
                    },
                },
            )
            self.assertEqual(
                load_app_paths(path),
                {
                    "Editor": ["editor.exe"],
                    "Steam": ["steam.exe"],
                    "Hypergryph": ["launcher.exe"],
                },
            )

    def test_duplicate_app_names_across_categories_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                directory,
                "apps.yaml",
                """
app_paths:
  常用:
    Steam:
      - steam.exe
  GAME:
    steam:
      - another-steam.exe
""",
            )
            with self.assertRaises(ConfigError):
                load_app_paths(path)

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


if __name__ == "__main__":
    unittest.main()
