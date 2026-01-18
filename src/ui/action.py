from PyQt6.QtWidgets import QMenu, QApplication
from PyQt6.QtGui import QAction
import sys
import os

# 导入功能模块
# 为了方便导入，可以在这里临时添加一下路径，或者在 main 中处理
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.function import organizer, screen_shot, open_app
from src.input import choice_dialog

class PetActions:
    def __init__(self, parent_widget, dialogue_system):
        self.parent = parent_widget
        self.dialogue = dialogue_system

    def show_context_menu(self, global_pos):
        menu = QMenu(self.parent)

        # 打开常用软件子菜单
        app_menu = menu.addMenu("打开软件")
        
        apps = ["计算器", "记事本", "终端", "网易云"]
        for app in apps:
            action = QAction(app, self.parent)
            action.triggered.connect(lambda checked, a=app: self.do_open_app(a))
            app_menu.addAction(action)

        menu.addSeparator()
        # 截图/识别屏幕
        action_screenshot = QAction('识别屏幕 (截图)', self.parent)
        action_screenshot.triggered.connect(self.do_screenshot)
        menu.addAction(action_screenshot)

        # 整理桌面
        action_organize = QAction('整理桌面', self.parent)
        action_organize.triggered.connect(self.do_organize)
        menu.addAction(action_organize)
        
        # 撤销整理
        action_undo = QAction('撤销整理', self.parent)
        action_undo.triggered.connect(self.do_undo_organize)
        # 如果没有可撤销的操作，禁用菜单项
        action_undo.setEnabled(organizer.can_undo())
        menu.addAction(action_undo)
        
        menu.addSeparator()
        
        action_quit = QAction('退出', self.parent)
        action_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(action_quit)

        menu.exec(global_pos)

    def do_organize(self):
        print("正在整理桌面...")
        result = organizer.organize_desktop()
        print(result)
        self.dialogue.show_message("桌面整理", result)

    def do_undo_organize(self):
        print("正在撤销整理...")
        result = organizer.undo_organize()
        print(result)
        self.dialogue.show_message("撤销整理", result)

    def do_screenshot(self):
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
        
        # 2. 执行截图
        # 为防止弹出框还在屏幕上，先隐藏自己或者延迟一下？
        # 一般 msg_box.exec() 也是阻塞的，结束后窗口就已经关闭了，所以直接截图应该没问题。
        result = screen_shot.capture_screen_content(save_dir=save_path)
        print(result)
        self.dialogue.show_message("屏幕截图", result)

    def do_open_app(self, app_name):
        print(f"正在打开 {app_name}...")
        result = open_app.open_application(app_name)
        print(result)
        self.dialogue.show_message("打开软件", result)
