from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt

class DialogueSystem:
    def __init__(self, parent_widget):
        self.parent = parent_widget

    def show_message(self, title, content):
        msg = QMessageBox(self.parent)
        msg.setWindowTitle(title)
        msg.setText(content)
        # 确保弹窗也在最上层，避免被其他窗口遮挡
        msg.setWindowFlags(msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        msg.exec()
