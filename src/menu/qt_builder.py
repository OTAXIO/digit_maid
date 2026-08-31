"""Render menu-domain entries into native Qt menus."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from PyQt6.QtGui import QAction

from src.menu.model import MenuEntry


def populate_qmenu(
    parent_menu,
    entries: Sequence[MenuEntry],
    *,
    action_parent,
    launch_handler: Callable[[str], Any],
    action_handlers: Mapping[str, Callable[[], Any]],
) -> None:
    for entry in entries:
        if entry.is_category:
            submenu = parent_menu.addMenu(entry.label)
            populate_qmenu(
                submenu,
                entry.children,
                action_parent=action_parent,
                launch_handler=launch_handler,
                action_handlers=action_handlers,
            )
            continue

        if entry.is_launcher:
            handler = lambda name=entry.label: launch_handler(name)
        elif entry.is_action and entry.action_id in action_handlers:
            handler = action_handlers[entry.action_id]
        else:
            continue

        action = QAction(entry.label, action_parent)
        action.triggered.connect(lambda checked, callback=handler: callback())
        parent_menu.addAction(action)
