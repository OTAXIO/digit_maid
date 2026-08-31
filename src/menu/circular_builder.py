"""Convert menu-domain entries into CircularMenuWidget descriptors."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from src.menu.model import MenuEntry


def build_circular_items(
    entries: Sequence[MenuEntry],
    *,
    launch_handler: Callable[[str], Any],
    action_handlers: Mapping[str, Any],
) -> list[dict[str, Any]]:
    items = []
    for entry in entries:
        if entry.is_category:
            children = build_circular_items(
                entry.children,
                launch_handler=launch_handler,
                action_handlers=action_handlers,
            )
            if children:
                items.append({"label": entry.label, "action": children})
        elif entry.is_launcher:
            items.append(
                {
                    "label": entry.label,
                    "action": lambda name=entry.label: launch_handler(name),
                }
            )
        elif entry.is_action and entry.action_id in action_handlers:
            items.append({"label": entry.label, "action": action_handlers[entry.action_id]})
    return items
