import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.function import codex_status, startup
from src.services import app_launcher


class ServiceStabilityTests(unittest.TestCase):
    def test_launcher_rejects_oversized_name_before_loading_config(self):
        with patch.object(app_launcher, "load_launch_paths") as load_paths:
            result = app_launcher.open_application("x" * 65)
        self.assertIn("名称无效", result)
        load_paths.assert_not_called()

    def test_codex_process_display_count_is_bounded(self):
        processes = [
            {
                "pid": index + 1,
                "elapsed": "00:01",
                "cpu": 0.0,
                "mem": 0.0,
                "command": f"codex-{index}",
            }
            for index in range(25)
        ]
        with (
            patch.object(codex_status, "_load_bridge_status", return_value=None),
            patch.object(codex_status, "list_codex_processes", return_value=processes),
        ):
            _, content = codex_status.get_codex_status_message(max_processes=10**100)

        self.assertIn("另有 5 个进程未显示", content)

    def test_linux_startup_exec_rejects_line_injection(self):
        with self.assertRaises(ValueError):
            startup._desktop_exec_quote("/safe/path\nHidden=true")

    def test_linux_startup_exec_escapes_field_codes_and_reserved_chars(self):
        quoted = startup._desktop_exec_quote("/tmp/100% $value`name")
        self.assertEqual(quoted, '"/tmp/100%% \\$value\\`name"')

    def test_startup_file_replacement_is_atomic_and_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "nested", "digitmaid.desktop")
            startup._atomic_write_startup_file(path, "first")
            startup._atomic_write_startup_file(path, "second")

            self.assertEqual(startup._read_startup_file(path), "second")
            self.assertEqual(list(path.parent.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
