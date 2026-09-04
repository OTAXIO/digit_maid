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
                {
                    "2026-08-31": [
                        {"ddl": "09:05", "text": "安全检查", "completed": False}
                    ]
                },
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

    def test_complete_marks_only_one_matching_item(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "todo.json")
            with patch.object(todo_store, "get_todo_data_path", return_value=str(path)):
                todo_store.save_todo_items_by_date(
                    {
                        "2026-09-04": [
                            {"ddl": "09:30", "text": "提交报告"},
                            {"ddl": "09:30", "text": "提交报告"},
                            {"ddl": "10:00", "text": "整理记录"},
                        ]
                    }
                )
                self.assertTrue(
                    todo_store.complete_todo_item("2026-09-04", "09:30", "提交报告")
                )
                loaded = todo_store.load_todo_items_by_date()

            self.assertEqual(
                loaded,
                {
                    "2026-09-04": [
                        {"ddl": "09:30", "text": "提交报告", "completed": False},
                        {"ddl": "10:00", "text": "整理记录", "completed": False},
                        {"ddl": "09:30", "text": "提交报告", "completed": True},
                    ]
                },
            )

            with patch.object(todo_store, "get_todo_data_path", return_value=str(path)):
                self.assertTrue(
                    todo_store.set_todo_item_completed(
                        "2026-09-04", "09:30", "提交报告", completed=False
                    )
                )
                restored = todo_store.load_todo_items_by_date()
            self.assertTrue(all(not task["completed"] for task in restored["2026-09-04"]))

    def test_invalid_save_does_not_replace_existing_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "todo.json")
            with patch.object(todo_store, "get_todo_data_path", return_value=str(path)):
                self.assertTrue(
                    todo_store.save_todo_items_by_date(
                        {"2026-09-04": [{"ddl": "09:30", "text": "原事项"}]}
                    )
                )
                self.assertFalse(
                    todo_store.save_todo_items_by_date(
                        {
                            "2026-09-04": [
                                {
                                    "ddl": "09:30",
                                    "text": "x" * (todo_store.MAX_TODO_TEXT_CHARS + 1),
                                }
                            ]
                        }
                    )
                )
                loaded = todo_store.load_todo_items_by_date()

            self.assertEqual(loaded["2026-09-04"][0]["text"], "原事项")

    def test_completion_rejects_invalid_date(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "todo.json")
            with patch.object(todo_store, "get_todo_data_path", return_value=str(path)):
                self.assertFalse(
                    todo_store.complete_todo_item("not-a-date", "09:30", "事项")
                )


if __name__ == "__main__":
    unittest.main()
