"""UI-independent menu domain model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional


BUILTIN_TOOL_ACTIONS = frozenset({"screenshot", "keyboard_control", "codex_status"})


@dataclass(frozen=True)
class MenuEntry:
    """One category, configured launcher, or built-in action."""

    label: str
    children: tuple["MenuEntry", ...] = ()
    launch_targets: tuple[str, ...] = ()
    action_id: Optional[str] = None

    @property
    def is_category(self) -> bool:
        return bool(self.children)

    @property
    def is_launcher(self) -> bool:
        return bool(self.launch_targets)

    @property
    def is_action(self) -> bool:
        return self.action_id is not None


@dataclass(frozen=True)
class MenuConfig:
    """Validated APP and TOOL menu sections."""

    applications: tuple[MenuEntry, ...] = ()
    tools: tuple[MenuEntry, ...] = ()

    def iter_entries(self) -> Iterator[MenuEntry]:
        yield from _walk_entries(self.applications)
        yield from _walk_entries(self.tools)

    def launch_paths(self) -> dict[str, list[str]]:
        return {
            entry.label: list(entry.launch_targets)
            for entry in self.iter_entries()
            if entry.is_launcher
        }


def _walk_entries(entries: tuple[MenuEntry, ...]) -> Iterator[MenuEntry]:
    for entry in entries:
        yield entry
        if entry.children:
            yield from _walk_entries(entry.children)
