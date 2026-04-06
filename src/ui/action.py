from PyQt6.QtWidgets import QMenu, QApplication
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtCore import QTimer, QObject, QEvent
import os
from src.function import screen_shot, open_app, startup
from src.function.open_app import load_app_paths
from src.input import choice_dialog
from src.input.choice_dialog import load_dialog_theme
from src.input.circular_menu import CircularMenuWidget

class PetActions:
    FALL_MODE_LABELS = {
        "smooth": "缓降飘落",
        "direct": "快速直落",
        "none": "不下坠",
    }

    def __init__(self, parent_widget, dialogue_system):
        self.parent = parent_widget
        self.dialogue = dialogue_system

    def _get_pet_animation_cfg_path(self):
        return os.path.join(os.path.dirname(__file__), "pet_animations.yaml")

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

        cfg_path = self._get_pet_animation_cfg_path()
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

    def show_context_menu(self, global_pos):
        # 拦截：如果气泡菜单已经存在并且开着，重复右击则关闭它（相当于开关切换）
        if hasattr(self, "circular_menu") and self.circular_menu is not None:
            if getattr(self.circular_menu, "isVisible", lambda: False)():
                self.circular_menu.close_menu()
                # 已经做了关闭动作，就可以返回了
                return
        
        theme = load_dialog_theme()
        menu_style = theme.get("menu_style", "list")

        if menu_style == "circular":
            self.show_circular_menu(global_pos)
            return

        menu = QMenu(self.parent)
        scale = float(getattr(self.parent, "user_scale", 1.0))
        scale = max(0.5, min(2.5, scale))
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
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
            if not os.path.isabs(bg_path):
                bg_path = os.path.join(root_dir, bg_path)
            
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
                    menu_timer.start(20000)
                return False
                
        menu_filter = MenuEventFilter(menu)
        menu.installEventFilter(menu_filter)
        menu_timer.start(15000)

        menu.exec(global_pos)
        
        # 阻塞调用结束，手动恢复桌宠的状态
        self.parent.menu_interact_mode = False
        self.parent.play_action("idle")
        if hasattr(self.parent, "force_on_top"):
            self.parent.force_on_top()

    def show_circular_menu(self, global_pos):
        """用半圆形菜单展开相同的选项"""
        apps = list(load_app_paths().keys())
        
        # 构造“打开软件”子菜单的数据
        app_sub_items = [
            {'label': app, 'action': lambda a=app: self.do_open_app(a)} 
            for app in apps if app!="v2rayN"
        ]

        screenshot_sub_items = [
            {'label': '存到桌面', 'action': lambda: self.do_circular_screenshot("desktop")},
            {'label': '存到默认', 'action': lambda: self.do_circular_screenshot("default")},
            {'label': '不保存', 'action': lambda: self.do_circular_screenshot("none")}
        ]

        current_mode = self._get_current_fall_mode()
        fall_mode_sub_items = [
            {
                'label': label,
                'text_color': '#c41c1c' if mode == current_mode else 'white',
                'action': lambda m=mode: self._set_fall_mode(m)
            }
            for mode, label in self.FALL_MODE_LABELS.items()
        ]

        # 构造顶层选项
        setting_label = [
            {'label': '下落模式', 'action': fall_mode_sub_items},
            {'label': '关闭自启动' if startup.is_startup_enabled() else '开启自启动', 'action': self.toggle_startup},
        ]
        top_items = [
            {'label': 'APP', 'action': app_sub_items},
            {'label': '截图', 'action': screenshot_sub_items},
            {'label': "设置", 'action': setting_label},
            {'label': '退出', 'action': self.trigger_quit}
        ]
        
        # 把中心点设在桌宠的正上方一点或正中心
        center_point = self.parent.mapToGlobal(self.parent.rect().center())
        
        # 实例化并显示全屏的透明菜单窗体
        self.circular_menu = CircularMenuWidget(
            items=top_items,
            center_pos=center_point,
            on_close_callback=lambda: self.on_circular_menu_closed(),
            menu_scale=float(getattr(self.parent, "user_scale", 1.0)),
            parent=self.parent
        )
        self.circular_menu.show()
        
    def on_circular_menu_closed(self):
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

    def toggle_startup(self, enabled=None):
        if enabled is None:
            enabled = not startup.is_startup_enabled()

        ok, result = startup.set_startup_enabled(bool(enabled))
        print(result)
        self.dialogue.show_message("开机自启动", result)

        return ok
