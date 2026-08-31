import unittest
from unittest.mock import patch

from src.services import app_launcher


class AppLauncherTests(unittest.TestCase):
    def test_only_exact_configured_names_are_allowed(self):
        apps = {"Editor": ["editor.exe"]}
        with (
            patch.object(app_launcher, "load_app_paths", return_value=apps),
            patch.object(app_launcher.platform, "system", return_value="Windows"),
            patch.object(app_launcher, "_launch_windows_app") as launch,
        ):
            message = app_launcher.open_application("Editor --malicious-argument")
        self.assertIn("未配置应用", message)
        launch.assert_not_called()

    def test_configured_target_is_launched_without_shell(self):
        apps = {"Editor": ["missing.exe", "editor.exe"]}
        with (
            patch.object(app_launcher, "load_app_paths", return_value=apps),
            patch.object(app_launcher.platform, "system", return_value="Windows"),
            patch.object(
                app_launcher,
                "_launch_windows_app",
                side_effect=[FileNotFoundError, None],
            ) as launch,
        ):
            message = app_launcher.open_application("editor")
        self.assertEqual(message, "已启动Editor")
        self.assertEqual(launch.call_count, 2)

    def test_unsupported_platform_does_not_launch(self):
        with (
            patch.object(app_launcher, "load_app_paths", return_value={"Editor": ["editor"]}),
            patch.object(app_launcher.platform, "system", return_value="Plan9"),
        ):
            self.assertIn("暂不支持", app_launcher.open_application("Editor"))


if __name__ == "__main__":
    unittest.main()
