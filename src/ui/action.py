from PyQt6.QtWidgets import QMenu, QApplication
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QTimer
import sys
import os
import time

# 导入功能模块
# 为了方便导入，可以在这里临时添加一下路径，或者在 main 中处理
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.function import screen_shot, open_app
from src.function.open_app import load_app_paths
from src.function import startup
from src.input import choice_dialog
from src.input.choice_dialog import load_dialog_theme
from src.input.circular_menu import CircularMenuWidget

class PetActions:
    def __init__(self, parent_widget, dialogue_system):
        self.parent = parent_widget
        self.dialogue = dialogue_system

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

        # 尝试应用 dialog_style.yaml 中的背景
        theme = load_dialog_theme()
        bg_path = theme.get("background", "")
        if bg_path:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
            if not os.path.isabs(bg_path):
                bg_path = os.path.join(root_dir, bg_path)
            
            if os.path.exists(bg_path):
                bg_url = bg_path.replace("\\", "/")
                # 为 QMenu 及其子菜单设置统一样式
                menu_qss = f"""
                    QMenu {{
                        background-image: url("{bg_url}");
                        background-repeat: no-repeat;
                        background-position: left top;
                        background-color: rgba(250, 250, 250, 220); 
                        border: 2px solid #ff3b30;
                        border-radius: 10px;
                        padding: 5px;
                    }}
                    QMenu::item {{
                        padding: 5px 20px 5px 20px;
                        color: #333;
                        font-weight: bold;
                        border-radius: 5px;
                    }}
                    QMenu::item:selected {{
                        background-color: #ff3b30;
                        color: white;
                    }}
                    QMenu::separator {{
                        height: 2px;
                        background: #ff3b30;
                        margin: 5px 10px 5px 10px;
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

        action_startup = QAction('开机自启动', self.parent)
        action_startup.setCheckable(True)
        action_startup.setChecked(startup.is_startup_enabled())
        action_startup.triggered.connect(lambda checked: self.toggle_startup(checked))
        menu.addAction(action_startup)
        
        action_quit = QAction('退出', self.parent)
        action_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(action_quit)

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
            for app in apps
        ]

        screenshot_sub_items = [
            {'label': '存到桌面', 'action': lambda: self.do_circular_screenshot("desktop")},
            {'label': '存到默认', 'action': lambda: self.do_circular_screenshot("default")},
            {'label': '不保存', 'action': lambda: self.do_circular_screenshot("none")}
        ]

        # 构造顶层选项
        setting_label = [{'label': '关闭自启动' if startup.is_startup_enabled() else '开启自启动','action': self.toggle_startup}]
        top_items = [
            {'label': 'APP', 'action': app_sub_items},
            {'label': '截图', 'action': screenshot_sub_items},
            {'label': "设置", 'action': setting_label},
            {'label': '退出', 'action': QApplication.instance().quit}
        ]
        
        # 把中心点设在桌宠的正上方一点或正中心
        center_x = self.parent.x() + self.parent.width() // 2
        center_y = self.parent.y() + self.parent.height() // 2
        center_point = self.parent.mapToGlobal(self.parent.rect().center())
        
        # 实例化并显示全屏的透明菜单窗体
        self.circular_menu = CircularMenuWidget(
            items=top_items,
            center_pos=center_point,
            on_close_callback=lambda: self.on_circular_menu_closed(),
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

    def do_open_app(self, app_name):
        self.parent.play_action("open_app")
        print(f"正在打开 {app_name}...")
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
