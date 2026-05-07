from dataclasses import dataclass


@dataclass(frozen=True)
class MenuOperationPolicy:
    allow_idle_timer: bool = True
    allow_wander: bool = True
    allow_drag: bool = True
    allow_double_click: bool = True
    allow_fall: bool = True


class OptionMenuController:
    """Tracks option-menu visibility and exposes operation permissions."""

    def __init__(self):
        self._list_menu_open = False
        self._circular_menu_open = False
        self._todo_panel_open = False
        self._custom_scale_adjusting = False

    def set_list_menu_open(self, is_open: bool):
        self._list_menu_open = bool(is_open)

    def set_circular_menu_open(self, is_open: bool):
        self._circular_menu_open = bool(is_open)

    def set_todo_panel_open(self, is_open: bool):
        self._todo_panel_open = bool(is_open)

    def set_custom_scale_adjusting(self, is_active: bool):
        self._custom_scale_adjusting = bool(is_active)

    @property
    def is_menu_open(self) -> bool:
        return self._list_menu_open or self._circular_menu_open

    @property
    def is_todo_panel_open(self) -> bool:
        return self._todo_panel_open

    @property
    def is_ui_locked(self) -> bool:
        return self.is_menu_open or self._todo_panel_open

    @property
    def policy(self) -> MenuOperationPolicy:
        if self._todo_panel_open:
            return MenuOperationPolicy(
                allow_idle_timer=False,
                allow_wander=False,
                allow_drag=False,
                allow_double_click=False,
                allow_fall=False,
            )

        if self._custom_scale_adjusting:
            return MenuOperationPolicy(
                allow_idle_timer=False,
                allow_wander=False,
                allow_drag=False,
                allow_double_click=False,
                allow_fall=False,
            )

        if self.is_menu_open:
            return MenuOperationPolicy(
                allow_idle_timer=False,
                allow_wander=False,
                # 菜单展开时允许拖拽，左键按下会先关闭菜单再进入移动流程。
                allow_drag=True,
                allow_double_click=False,
                allow_fall=False,
            )

        return MenuOperationPolicy()

    def allows(self, operation_name: str) -> bool:
        return bool(getattr(self.policy, operation_name, True))
