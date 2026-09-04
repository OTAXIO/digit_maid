import tempfile
import unittest
from pathlib import Path

from src.core.json_store import JsonStoreError, atomic_write_json, read_json_file


class JsonStoreTests(unittest.TestCase):
    def test_atomic_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "state.json")
            payload = {"message": "你好", "items": [1, 2, 3]}
            atomic_write_json(path, payload)
            self.assertEqual(read_json_file(path, max_bytes=1024), payload)
            self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_size_limit_is_enforced_before_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "large.json")
            path.write_text('"' + ("x" * 100) + '"', encoding="utf-8")
            with self.assertRaises(JsonStoreError):
                read_json_file(path, max_bytes=32)

    def test_malformed_json_has_a_domain_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "broken.json")
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(JsonStoreError):
                read_json_file(path, max_bytes=1024)

    def test_invalid_size_limits_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "state.json")
            path.write_text("{}", encoding="utf-8")
            for invalid_limit in (0, -1, True, 1.5):
                with self.subTest(limit=invalid_limit):
                    with self.assertRaises(JsonStoreError):
                        read_json_file(path, max_bytes=invalid_limit)

    def test_oversized_atomic_write_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "state.json")
            atomic_write_json(path, {"state": "old"})

            with self.assertRaises(JsonStoreError):
                atomic_write_json(path, {"state": "x" * 100}, max_bytes=32)

            self.assertEqual(read_json_file(path, max_bytes=1024), {"state": "old"})

    def test_pathological_json_depth_has_a_domain_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "deep.json")
            path.write_text("[" * 1500 + "]" * 1500, encoding="utf-8")
            with self.assertRaises(JsonStoreError):
                read_json_file(path, max_bytes=4096)

    def test_oversized_integer_has_a_domain_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "integer.json")
            path.write_text("1" * 5000, encoding="utf-8")
            with self.assertRaises(JsonStoreError):
                read_json_file(path, max_bytes=8192)


if __name__ == "__main__":
    unittest.main()
