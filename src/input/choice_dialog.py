"""截图保存位置选择。返回值保持 desktop/default/none，供系统服务调用。"""

from src.ui.theme import load_dialog_theme  # 兼容旧扩展的导入入口。
from src.ui.theme.dialogs import ThemedDialog


class CustomChoiceDialog(ThemedDialog):
    def __init__(self, parent=None):
        super().__init__("保存这一刻", "选择截图的保存位置，或取消本次保存。", parent)
        self.choice = "none"
        self.add_action("不保存", self.on_cancel)
        self.add_action("图片目录", self.on_default)
        self.add_action("桌面", self.on_desktop, primary=True)
        self.finish_layout()

    def on_desktop(self):
        self.choice = "desktop"
        self.accept()

    def on_default(self):
        self.choice = "default"
        self.accept()

    def on_cancel(self):
        self.choice = "none"
        self.reject()


def ask_save_location(parent):
    """取消或 Esc 均返回 none，不触发文件写入。"""
    dialog = CustomChoiceDialog(parent)
    dialog.exec()
    return dialog.choice
