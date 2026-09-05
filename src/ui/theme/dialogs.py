"""工具对话框的公共骨架：品牌标题、内容区与右下角操作区。"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from . import qss
from .styles import BASE
from .widgets import apply_shadow, character_badge, keep_on_screen


class ThemedDialog(QDialog):
    def __init__(self, title, description="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(str(title)[:200])
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(390)
        self.setStyleSheet(BASE + qss('''
            QFrame#dialog_card { background: $canvas; border: 1px solid $line; border-radius: 18px; }
        '''))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        card = QFrame(self)
        card.setObjectName("dialog_card")
        apply_shadow(card)
        outer.addWidget(card)
        self.content_layout = QVBoxLayout(card)
        self.content_layout.setContentsMargins(24, 22, 24, 22)
        self.content_layout.setSpacing(14)
        header = QHBoxLayout()
        header.addWidget(character_badge(card, 40))
        titles = QVBoxLayout()
        caption = QLabel("VIVI  /  DESKTOP COMPANION", card)
        caption.setProperty("role", "eyebrow")
        titles.addWidget(caption)
        heading = QLabel(str(title)[:200], card)
        heading.setTextFormat(Qt.TextFormat.PlainText)
        heading.setWordWrap(True)
        heading.setProperty("role", "title")
        titles.addWidget(heading)
        header.addLayout(titles, 1)
        self.content_layout.addLayout(header)
        self.info_label = QLabel(str(description)[:500], card)
        self.info_label.setTextFormat(Qt.TextFormat.PlainText)
        self.info_label.setWordWrap(True)
        self.info_label.setProperty("role", "muted")
        self.content_layout.addWidget(self.info_label)
        self.action_row = QHBoxLayout()
        self.action_row.setSpacing(8)
        self.action_row.addStretch(1)

    def add_action(self, text, callback, *, primary=False):
        button = QPushButton(text, self)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        if primary:
            button.setProperty("role", "primary")
            button.setDefault(True)
        button.clicked.connect(callback)
        self.action_row.addWidget(button)
        return button

    def finish_layout(self):
        self.content_layout.addLayout(self.action_row)

    def showEvent(self, event):
        super().showEvent(event)
        keep_on_screen(self)
