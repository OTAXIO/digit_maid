import unittest

from src.menu.circular_builder import build_circular_items
from src.menu.model import MenuEntry


class CircularMenuBuilderTests(unittest.TestCase):
    def test_categories_launchers_and_actions_keep_their_roles(self):
        launched = []
        screenshot_items = [{"label": "保存", "action": lambda: None}]
        entries = (
            MenuEntry(
                label="网络",
                children=(MenuEntry(label="VPN", launch_targets=("vpn.exe",)),),
            ),
            MenuEntry(label="截图", action_id="screenshot"),
        )

        items = build_circular_items(
            entries,
            launch_handler=launched.append,
            action_handlers={"screenshot": screenshot_items},
        )

        self.assertEqual([item["label"] for item in items], ["网络", "截图"])
        self.assertEqual(items[1]["action"], screenshot_items)
        items[0]["action"][0]["action"]()
        self.assertEqual(launched, ["VPN"])


if __name__ == "__main__":
    unittest.main()
