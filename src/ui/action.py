from PyQt6.QtWidgets import QMenu, QApplication
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtCore import QTimer, QObject, QEvent, QPoint
import os
from src.function import screen_shot, open_app, startup
from src.function.open_app import load_app_paths
from src.input import choice_dialog
from src.input.choice_dialog import load_dialog_theme
from src.input.circular_menu import CircularMenuWidget
from .menu_controller import OptionMenuController

class MaidActions:
    FALL_MODE_LABELS = {
        "smooth": "缓降飘落",
        "direct": "快速直落",
        "none": "不下坠",
    }
    IDLE_MODE_LABELS = {
        "default": "默认模式",
        "sport": "运动模式",
        "lazy": "懒惰模式",
    }

    def __init__(self, parent_widget, dialogue_system):
        self.parent = parent_widget
        self.dialogue = dialogue_system
        if not hasattr(self.parent, "menu_controller"):
            self.parent.menu_controller = OptionMenuController()
        if not hasattr(self.parent, "_list_menu_open"):
            self.parent._list_menu_open = False

    def _set_list_menu_open_state(self, is_open):
        is_open = bool(is_open)
        self.parent._list_menu_open = is_open
        controller = getattr(self.parent, "menu_controller", None)
        if controller is not None:
            controller.set_list_menu_open(is_open)

    def _set_circular_menu_open_state(self, is_open):
        controller = getattr(self.parent, "menu_controller", None)
        if controller is not None:
            controller.set_circular_menu_open(bool(is_open))

    def _get_maid_animation_cfg_path(self):
        return os.path.join(os.path.dirname(__file__), "maid_animations.yaml")

    def _get_current_fall_mode(self):
        anim_cfg = getattr(self.parent, "anim_cfg", {}) or {}
        mode = str(anim_cfg.get("fall_mode", "")).strip().lower()
        if mode in self.FALL_MODE_LABELS:
            return mode
        return "smooth" if anim_cfg.get("smooth_fall", True) else "direct"

    def _set_fall_mode(self, mode):
        mode = str(mode).strip().lower()
        if mode not in self.FALL_MODE_LABELS:
            return False

        cfg_path = self._get_maid_animation_cfg_path()
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            replaced = False
            for idx, line in enumerate(lines):
                if line.strip().startswith("fall_mode:"):
                    lines[idx] = f"fall_mode: {mode}\n"
                    replaced = True
                    break

            if not replaced:
                insert_at = 0
                for idx, line in enumerate(lines):
                    if line.strip().startswith("base_dir:"):
                        insert_at = idx + 1
                        break
                lines.insert(insert_at, f"fall_mode: {mode}\n")

            with open(cfg_path, "w", encoding="utf-8", newline="") as f:
                f.writelines(lines)
        except Exception as e:
            msg = f"设置下落模式失败: {e}"
            print(msg)
            self.dialogue.show_message("下落模式", msg)
            return False

        if hasattr(self.parent, "anim_cfg") and isinstance(self.parent.anim_cfg, dict):
            self.parent.anim_cfg["fall_mode"] = mode
            self.parent.anim_cfg["smooth_fall"] = (mode == "smooth")

        if mode == "none" and getattr(self.parent, "_is_falling", False):
            if hasattr(self.parent, "_stop_fall"):
                self.parent._stop_fall()
            self.parent.play_action("idle")

        self.dialogue.show_message("下落模式", f"已切换为: {self.FALL_MODE_LABELS[mode]}")
        return True

    def _get_current_idle_mode(self):
        anim_cfg = getattr(self.parent, "anim_cfg", {}) or {}
        mode = str(anim_cfg.get("idle_mode", "")).strip().lower()
        if mode in self.IDLE_MODE_LABELS:
            return mode
        return "default"

    def _set_idle_mode(self, mode):
        mode = str(mode).strip().lower()
        if mode not in self.IDLE_MODE_LABELS:
            return False

        cfg_path = self._get_maid_animation_cfg_path()
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            replaced = False
            for idx, line in enumerate(lines):
                if line.strip().startswith("idle_mode:"):
                    lines[idx] = f"idle_mode: {mode}\n"
                    replaced = True
                    break

            if not replaced:
                insert_at = 0
                for idx, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith("fall_mode:"):
                        insert_at = idx + 1
                        break
                    if stripped.startswith("base_dir:"):
                        insert_at = idx + 1
                lines.insert(insert_at, f"idle_mode: {mode}\n")

            with open(cfg_path, "w", encoding="utf-8", newline="") as f:
                f.writelines(lines)
        except Exception as e:
            msg = f"设置待机模式失败: {e}"
            print(msg)
            self.dialogue.show_message("待机模式", msg)
            return False

        if hasattr(self.parent, "anim_cfg") and isinstance(self.parent.anim_cfg, dict):
            self.parent.anim_cfg["idle_mode"] = mode

        # 切换待机模式后重置待机状态机，避免沿用旧模式的阶段与计时。
        if hasattr(self.parent, "wander_timer"):
            self.parent.wander_timer.stop()
        if hasattr(self.parent, "_stop_inactivity_timer"):
            self.parent._stop_inactivity_timer(reset_stage=True)

        if (
            not getattr(self.parent, "menu_interact_mode", False)
            and not getattr(self.parent, "_custom_scale_adjusting", False)
            and not getattr(self.parent, "_edge_hidden", False)
        ):
            self.parent.play_action("idle")

        self.dialogue.show_message("待机模式", f"已切换为: {self.IDLE_MODE_LABELS[mode]}")
        return True

    def _apply_maid_scale(self, scale_value, tip_prefix=""):
        if hasattr(self.parent, "set_maid_scale_factor"):
            ok, detail = self.parent.set_maid_scale_factor(scale_value)
        else:
            ok, detail = False, "当前窗口不支持缩放"

        if ok:
            msg = f"{tip_prefix}，{detail}" if tip_prefix else detail
            self.dialogue.show_message("大小调整", msg)
        else:
            self.dialogue.show_message("大小调整", detail or "调整大小失败")
        return ok

    def _set_custom_maid_scale(self):
        return self._start_custom_scale_adjustment()

    def _start_custom_scale_adjustment(self):
        if hasattr(self.parent, "begin_custom_scale_adjustment"):
            ok, detail = self.parent.begin_custom_scale_adjustment()
        else:
            ok, detail = False, "当前窗口不支持自定义滚轮调节"

        menu = getattr(self, "circular_menu", None)
        if ok and menu is not None and getattr(menu, "isVisible", lambda: False)():
            if hasattr(menu, "set_auto_close_enabled"):
                menu.set_auto_close_enabled(False)

        if ok:
            self.dialogue.show_message(
                "自定义大小",
                "请将鼠标移动到桌宠上使用滚轮调节大小，点击“保存”生效，点击“退出”取消。",
            )
        else:
            self.dialogue.show_message("自定义大小", detail)
        return ok

    def _confirm_custom_scale_adjustment(self):
        if hasattr(self.parent, "confirm_custom_scale_adjustment"):
            ok, detail = self.parent.confirm_custom_scale_adjustment()
        else:
            ok, detail = False, "当前窗口不支持确认自定义大小"

        menu = getattr(self, "circular_menu", None)
        if menu is not None and getattr(menu, "isVisible", lambda: False)():
            if hasattr(menu, "set_auto_close_enabled"):
                menu.set_auto_close_enabled(True)

        self.dialogue.show_message("自定义大小", detail)
        return ok

    def _cancel_custom_scale_adjustment(self):
        if hasattr(self.parent, "cancel_custom_scale_adjustment"):
            ok, detail = self.parent.cancel_custom_scale_adjustment()
        else:
            ok, detail = False, "当前窗口不支持取消自定义大小"

        menu = getattr(self, "circular_menu", None)
        if menu is not None and getattr(menu, "isVisible", lambda: False)():
            if hasattr(menu, "set_auto_close_enabled"):
                menu.set_auto_close_enabled(True)

        self.dialogue.show_message("自定义大小", detail)
        return ok

    def _get_circular_menu_center_point(self):
        current_center = self.parent.mapToGlobal(self.parent.rect().center())
        bottom_y = self.parent.y() + self.parent.height()

        source_size = getattr(self.parent, "_source_frame_size", None)
        base_render_scale = float(getattr(self.parent, "base_render_scale", 0.5))
        if source_size is not None and hasattr(source_size, "isEmpty") and not source_size.isEmpty():
            base_height = max(1, int(round(source_size.height() * base_render_scale)))
        else:
            base_height = max(1, int(getattr(self.parent, "default_maid_height", self.parent.height())))

        # 允许缩小时圆心随尺寸下移，但最低只到 0.4 倍对应的位置
        min_scale_for_center = 0.4
        min_center_y = int(round(bottom_y - (base_height * min_scale_for_center) / 2.0))
        center_y = min(current_center.y(), min_center_y)
        return QPoint(current_center.x(), center_y)

    def _menu_scale_from_maid_scale(self, maid_scale):
        try:
            scale = float(maid_scale)
        except (TypeError, ValueError):
            scale = 1.0

        # 放大时按 0.75 幅跟随；缩小时按 1:1 跟随，仅保留下限 0.4
        if scale >= 1.0:
            mapped = 1.0 + (scale - 1.0) * 0.75
        else:
            mapped = scale
        return max(0.4, mapped)

    def show_context_menu(self, global_pos):
        # 拦截：如果气泡菜单已经存在并且开着，重复右击则关闭它（相当于开关切换）
        if hasattr(self, "circular_menu") and self.circular_menu is not None:
            if getattr(self.circular_menu, "isVisible", lambda: False)():
                if getattr(self.parent, "_custom_scale_adjusting", False):
                    self.dialogue.show_message("自定义大小", "请先点击“保存”或“退出”结束调节。")
                    return
                self.circular_menu.close_menu()
                # 已经做了关闭动作，就可以返回了
                return
        
        theme = load_dialog_theme()
        menu_style = theme.get("menu_style", "list")

        if menu_style == "circular":
            self._set_list_menu_open_state(False)
            self.show_circular_menu(global_pos)
            return

        self._set_circular_menu_open_state(False)

        menu = QMenu(self.parent)
        scale = self._menu_scale_from_maid_scale(getattr(self.parent, "user_scale", 1.0))
        border_px = max(1, int(2 * scale))
        radius_px = max(6, int(10 * scale))
        menu_pad_px = max(2, int(5 * scale))
        item_vpad_px = max(2, int(5 * scale))
        item_hpad_px = max(8, int(20 * scale))
        item_radius_px = max(4, int(5 * scale))
        sep_h_px = max(1, int(2 * scale))
        sep_margin_v_px = max(2, int(5 * scale))
        sep_margin_h_px = max(4, int(10 * scale))
        font_px = max(12, int(14 * scale))

        menu_bg_css = "background-color: rgba(250, 250, 250, 220);"

        # 尝试应用 dialog_style.yaml 中的背景
        bg_path = theme.get("background", "")
        if bg_path:
            bg_path = os.path.normpath(bg_path.replace("\\", "/"))
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
            if not os.path.isabs(bg_path):
                bg_path = os.path.join(root_dir, bg_path)
            bg_path = os.path.normpath(bg_path)
            
            if os.path.exists(bg_path):
                bg_url = bg_path.replace("\\", "/")
                # 为 QMenu 及其子菜单设置统一样式
                menu_bg_css = (
                    f'background-image: url("{bg_url}");'
                    "background-repeat: no-repeat;"
                    "background-position: left top;"
                    "background-color: rgba(250, 250, 250, 220);"
                )

        menu_qss = f"""
            QMenu {{
                {menu_bg_css}
                border: {border_px}px solid #ff3b30;
                border-radius: {radius_px}px;
                padding: {menu_pad_px}px;
            }}
            QMenu::item {{
                padding: {item_vpad_px}px {item_hpad_px}px {item_vpad_px}px {item_hpad_px}px;
                color: #333;
                font-weight: bold;
                font-size: {font_px}px;
                border-radius: {item_radius_px}px;
            }}
            QMenu::item:selected {{
                background-color: #ff3b30;
                color: white;
            }}
            QMenu::separator {{
                height: {sep_h_px}px;
                background: #ff3b30;
                margin: {sep_margin_v_px}px {sep_margin_h_px}px {sep_margin_v_px}px {sep_margin_h_px}px;
            }}
        """
        # 设置当前菜单和子菜单的样式
        menu.setStyleSheet(menu_qss)

        # 打开常用软件子菜单
        app_menu = menu.addMenu("APP")
        
        apps = list(load_app_paths().keys())
        for app in apps:
            action = QAction(app, self.parent)
            action.triggered.connect(lambda checked, a=app: self.do_open_app(a))
            app_menu.addAction(action)

        menu.addSeparator()
        # 截图/识别屏幕
        action_screenshot = QAction('截图', self.parent)
        action_screenshot.triggered.connect(self.do_screenshot)
        menu.addAction(action_screenshot)

        settings_menu = menu.addMenu("设置")

        scale_menu = settings_menu.addMenu("大小调整")

        action_scale_reset = QAction('还原原大小', self.parent)
        action_scale_reset.triggered.connect(
            lambda checked: self._apply_maid_scale(1.0, "已还原原大小")
        )
        scale_menu.addAction(action_scale_reset)

        action_scale_up = QAction('放大1.5倍', self.parent)
        action_scale_up.triggered.connect(
            lambda checked: self._apply_maid_scale(1.5, "已放大到 1.5 倍")
        )
        scale_menu.addAction(action_scale_up)

        action_scale_down = QAction('缩小为0.6倍', self.parent)
        action_scale_down.triggered.connect(
            lambda checked: self._apply_maid_scale(0.6, "已缩小到 0.6 倍")
        )
        scale_menu.addAction(action_scale_down)

        custom_scale_menu = scale_menu.addMenu("自定义大小")

        def enter_custom_scale_mode():
            self._start_custom_scale_adjustment()
            # 自定义调节期间关闭“长时间无操作自动关闭”
            menu_timer.stop()

        custom_scale_menu.aboutToShow.connect(enter_custom_scale_mode)

        action_scale_custom_confirm = QAction('保存', self.parent)
        action_scale_custom_confirm.triggered.connect(lambda checked: self._confirm_custom_scale_adjustment())
        custom_scale_menu.addAction(action_scale_custom_confirm)

        action_scale_custom_cancel = QAction('返回', self.parent)
        action_scale_custom_cancel.triggered.connect(lambda checked: self._cancel_custom_scale_adjustment())
        custom_scale_menu.addAction(action_scale_custom_cancel)

        action_startup = QAction('开机自启动', self.parent)
        action_startup.setCheckable(True)
        action_startup.setChecked(startup.is_startup_enabled())
        action_startup.triggered.connect(lambda checked: self.toggle_startup(checked))
        settings_menu.addAction(action_startup)

        current_mode = self._get_current_fall_mode()
        current_mode_label = self.FALL_MODE_LABELS.get(current_mode, "缓降飘落")
        fall_mode_menu = settings_menu.addMenu(f"下落模式 ({current_mode_label})")
        fall_mode_group = QActionGroup(fall_mode_menu)
        fall_mode_group.setExclusive(True)
        for mode_key, mode_label in self.FALL_MODE_LABELS.items():
            mode_action = QAction(mode_label, self.parent)
            mode_action.setCheckable(True)
            mode_action.setChecked(mode_key == current_mode)
            mode_action.triggered.connect(lambda checked, m=mode_key: checked and self._set_fall_mode(m))
            fall_mode_group.addAction(mode_action)
            fall_mode_menu.addAction(mode_action)

        current_idle_mode = self._get_current_idle_mode()
        current_idle_mode_label = self.IDLE_MODE_LABELS.get(current_idle_mode, "默认模式")
        idle_mode_menu = settings_menu.addMenu(f"待机模式 ({current_idle_mode_label})")
        idle_mode_group = QActionGroup(idle_mode_menu)
        idle_mode_group.setExclusive(True)
        for mode_key, mode_label in self.IDLE_MODE_LABELS.items():
            mode_action = QAction(mode_label, self.parent)
            mode_action.setCheckable(True)
            mode_action.setChecked(mode_key == current_idle_mode)
            mode_action.triggered.connect(lambda checked, m=mode_key: checked and self._set_idle_mode(m))
            idle_mode_group.addAction(mode_action)
            idle_mode_menu.addAction(mode_action)
        
        action_quit = QAction('退出', self.parent)
        action_quit.triggered.connect(self.trigger_quit)
        menu.addAction(action_quit)

        # 添加 15 秒无操作自动关闭
        menu_timer = QTimer(self.parent)
        menu_timer.setSingleShot(True)
        menu_timer.timeout.connect(menu.close)
        
        class MenuEventFilter(QObject):
            def eventFilter(self, obj, event):
                # 记录可以视作操作或互动的事件
                if event.type() in (QEvent.Type.MouseMove, QEvent.Type.HoverMove, QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress, QEvent.Type.Wheel):
                    parent_widget = menu.parentWidget()
                    if parent_widget is not None and not getattr(parent_widget, "_custom_scale_adjusting", False):
                        menu_timer.start(20000)

                if event.type() == QEvent.Type.Wheel:
                    parent_widget = menu.parentWidget()
                    if parent_widget is not None and hasattr(parent_widget, "adjust_scale_by_wheel_delta"):
                        global_pos = event.globalPosition().toPoint()
                        local_pos = parent_widget.mapFromGlobal(global_pos)
                        if parent_widget.rect().contains(local_pos):
                            if parent_widget.adjust_scale_by_wheel_delta(event.angleDelta().y()):
                                event.accept()
                                return True
                return False
                
        menu_filter = MenuEventFilter(menu)
        menu.installEventFilter(menu_filter)
        menu_timer.start(15000)

        self._set_list_menu_open_state(True)
        try:
            menu.exec(global_pos)

            if getattr(self.parent, "_custom_scale_adjusting", False):
                # 预览态下若菜单意外关闭，不要回 idle；保持交互态，允许继续滚轮调节后再手动保存/退出
                self.parent.menu_interact_mode = True
                self.parent.play_action("interact", force_loop=True)
                if hasattr(self.parent, "force_on_top"):
                    self.parent.force_on_top()
                return

            # 阻塞调用结束，手动恢复桌宠的状态
            self.parent.menu_interact_mode = False
            self.parent.play_action("idle")
            if hasattr(self.parent, "force_on_top"):
                self.parent.force_on_top()
        finally:
            self._set_list_menu_open_state(False)

    def show_circular_menu(self, global_pos):
        """用半圆形菜单展开相同的选项"""
        apps = list(load_app_paths().keys())
        
        # 构造“打开软件”子菜单的数据
        game_apps = {"Steam","鹰角启动",}
        game_sub_items = [
            {'label': app, 'action': lambda a=app: self.do_open_app(a)}
            for app in apps if app in game_apps
        ]
        app_sub_items = [
            {'label': app, 'action': lambda a=app: self.do_open_app(a)}
            for app in apps
            if app != "v2rayN" and app not in game_apps
        ]
        if game_sub_items:
            app_sub_items.append({'label': "GAME", 'action': game_sub_items})

        screenshot_sub_items = [
            {'label': '存到桌面', 'action': lambda: self.do_circular_screenshot("desktop")},
            {'label': '存到默认', 'action': lambda: self.do_circular_screenshot("default")},
            {'label': '不保存', 'action': lambda: self.do_circular_screenshot("none")}
        ]

        current_mode = self._get_current_fall_mode()
        fall_mode_sub_items = [
            {
                'label': label,
                'text_color': "#e32e2e" if mode == current_mode else 'white',
                'action': lambda m=mode: self._set_fall_mode(m)
            }
            for mode, label in self.FALL_MODE_LABELS.items()
        ]

        current_idle_mode = self._get_current_idle_mode()
        idle_mode_sub_items = [
            {
                'label': label,
                'text_color': "#e32e2e" if mode == current_idle_mode else 'white',
                'action': lambda m=mode: self._set_idle_mode(m)
            }
            for mode, label in self.IDLE_MODE_LABELS.items()
        ]

        scale_sub_items = [
            {'label': '默认大小', 'action': lambda: self._apply_maid_scale(1.0, "已还原原大小")},
            {'label': '放大', 'action': lambda: self._apply_maid_scale(1.5, "已放大到 1.5 倍")},
            {'label': '缩小', 'action': lambda: self._apply_maid_scale(0.6, "已缩小到 0.6 倍")},
            {
                'label': '自定义大小',
                'action': [
                    {
                        'label': '返回',
                        'action': self._cancel_custom_scale_adjustment,
                        'close_before_action': False,
                    },
                     {
                        'label': '保存',
                        'action': self._confirm_custom_scale_adjustment,
                        'close_before_action': False,
                    },
                ],
                'on_enter': self._start_custom_scale_adjustment,
                'suppress_back': True,
            },
        ]

        # 构造顶层选项
        setting_label = [
            {'label': '大小调整', 'action': scale_sub_items},
            {'label': '下落模式', 'action': fall_mode_sub_items},
            {'label': '待机模式', 'action': idle_mode_sub_items},
            {'label': '关闭自启动' if startup.is_startup_enabled() else '开启自启动', 'action': self.toggle_startup},
        ]
        top_items = [
            {'label': 'APP', 'action': app_sub_items},
            {'label': '截图', 'action': screenshot_sub_items},
            {'label': "设置", 'action': setting_label},
            {'label': '关闭', 'action': self.trigger_quit}
        ]
        
        # 缩小时允许圆心下移，最低到 0.4 倍大小对应的位置
        center_point = self._get_circular_menu_center_point()
        
        # 实例化并显示全屏的透明菜单窗体
        self.circular_menu = CircularMenuWidget(
            items=top_items,
            center_pos=center_point,
            on_close_callback=lambda: self.on_circular_menu_closed(),
            menu_scale=self._menu_scale_from_maid_scale(getattr(self.parent, "user_scale", 1.0)),
            parent=self.parent
        )
        self.circular_menu.show()
        self._set_circular_menu_open_state(True)
        
    def on_circular_menu_closed(self):
        self._set_circular_menu_open_state(False)
        if getattr(self.parent, "_custom_scale_adjusting", False):
            # 预览进行中禁止通过关闭菜单回到 idle，必须走“保存/返回”完成事务
            self.parent.menu_interact_mode = True
            self.parent.play_action("interact", force_loop=True)
            if hasattr(self.parent, "force_on_top"):
                self.parent.force_on_top()
            return

        # 菜单关闭后恢复桌宠状态
        self.parent.menu_interact_mode = False
        self.parent.play_action("idle")
        if hasattr(self.parent, "force_on_top"):
            self.parent.force_on_top()

    def do_circular_screenshot(self, choice):
        self.parent.play_action("screenshot")
        
        save_path = None
        if choice == "desktop":
            save_path = os.path.join(os.path.expanduser("~"), "Desktop")
        elif choice == "default":
            # C:\Users\{user}\Pictures\Screenshots
            save_path = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
        elif choice == "none":
            self.dialogue.show_message("屏幕截图", "已取消截图保存")
            return

        print(f"正在识别屏幕... 保存到: {choice}")
        
        # 为了防止截图带上桌宠自己，先将桌宠隐藏
        self.parent.hide()
        
        def capture_and_restore():
            # 执行截图
            result = screen_shot.capture_screen_content(save_dir=save_path)
            
            # 截完图重新显示回来并置顶
            if hasattr(self.parent, "force_on_top"):
                self.parent.force_on_top()
            else:
                self.parent.show()
                self.parent.raise_()
                self.parent.activateWindow()
                
            print(result)
            self.dialogue.show_message("屏幕截图", result)
            
        # 使用 QTimer.singleShot 代替 time.sleep(0.2) 阻塞主线程，让系统彻底从屏幕上清理掉窗体残留视觉，并避免 Windows 把程序降级为假死
        QTimer.singleShot(300, capture_and_restore)

    def do_screenshot(self):
        self.parent.play_action("screenshot")
        # 1. 询问用户保存位置
        choice = choice_dialog.ask_save_location(self.parent)
        
        def get_windows_folder(folder_name, fallback):
            if os.name != 'nt':
                return fallback
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
                    path, _ = winreg.QueryValueEx(key, folder_name)
                    return os.path.expandvars(path)
            except Exception:
                return fallback
                
        save_path = None
        if choice == "desktop":
            save_path = get_windows_folder("Desktop", os.path.join(os.path.expanduser("~"), "Desktop"))
        elif choice == "default":
            my_pics = get_windows_folder("My Pictures", os.path.join(os.path.expanduser("~"), "Pictures"))
            save_path = os.path.join(my_pics, "Screenshots")
        elif choice == "none":
            self.dialogue.show_message("屏幕截图", "已取消截图保存")
            return

        print(f"正在识别屏幕... 保存到: {choice}")
        
        # 2. 为了防止截图带上桌宠自己，先将桌宠隐藏并刷新页面缓冲
        self.parent.hide()
        
        def capture_and_restore():
            # 执行截图
            result = screen_shot.capture_screen_content(save_dir=save_path)
            
            # 截完图重新显示回来并置顶
            if hasattr(self.parent, "force_on_top"):
                self.parent.force_on_top()
            else:
                self.parent.show()
                self.parent.raise_()
                self.parent.activateWindow()
            
            print(result)
            self.dialogue.show_message("屏幕截图", result)
            
        # 使用 QTimer.singleShot 代替 time.sleep(0.2)
        QTimer.singleShot(300, capture_and_restore)

    def trigger_quit(self):
        """播放退出动画后再退出程序"""
        if getattr(self.parent, "is_dying", False):
            return
            
        self.parent.is_dying = True
        
        # 尝试播放 die 动画，如果不成功（缺少配置或文件）则直接退出
        success = self.parent.play_action("die", force_loop=False)
        if not success:
            QApplication.instance().quit()

    def do_open_app(self, app_name):
        if app_name=="v2rayN":
            self.parent.play_action("open_app")
            print(f"正在启动 {app_name}...")
            result = open_app.open_application(app_name)
            print(result)
            self.dialogue.show_message("启动VPN", result)
        else:
            self.parent.play_action("open_app")
            print(f"正在启动 {app_name}...")
            result = open_app.open_application(app_name)
            print(result)
            self.dialogue.show_message("打开软件", result)

        if getattr(self.parent, "is_macos", False):
            # 目标应用激活后做一次可见性兜底，避免桌宠被系统判定为隐藏。
            self.parent.show()
            QTimer.singleShot(250, self.parent.show)

    def toggle_startup(self, enabled=None):
        if enabled is None:
            enabled = not startup.is_startup_enabled()

        ok, result = startup.set_startup_enabled(bool(enabled))
        print(result)
        self.dialogue.show_message("开机自启动", result)

        return ok

