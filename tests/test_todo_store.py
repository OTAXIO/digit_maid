import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.function import todo_store


class TodoStoreTests(unittest.TestCase):
    def test_save_and_load_normalized_items(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "todo.json")
            with patch.object(todo_store, "get_todo_data_path", return_value=str(path)):
                self.assertTrue(
                    todo_store.save_todo_items_by_date(
                        {"2026-08-31": [{"ddl": "9:05", "text": "  安全检查  "}]}
                    )
                )
                loaded = todo_store.load_todo_items_by_date()
            self.assertEqual(
                loaded,
                {"2026-08-31": [{"ddl": "09:05", "text": "安全检查"}]},
            )

    def test_corrupt_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "todo.json")
            original = "{not-json"
            path.write_text(original, encoding="utf-8")
            with patch.object(todo_store, "get_todo_data_path", return_value=str(path)):
                fallback = todo_store.load_todo_items_by_date()
            self.assertTrue(fallback)
            self.assertEqual(path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
