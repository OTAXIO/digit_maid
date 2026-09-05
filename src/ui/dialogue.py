"""跟随桌宠的轻量对话卡片。负责排版与生命周期，不参与桌宠行为判断。"""

import html
import sys

from PyQt6 import sip
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QFont
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QScrollArea, QApplication

from src.core.numeric import bounded_float, bounded_int
from src.ui.theme import P, default_ui_font_family, load_dialog_theme
from src.ui.theme.styles import BASE
from src.ui.theme.widgets import keep_on_screen


DEFAULT_MESSAGE_DURATION_MS = 2000


class SpeechBubble(QWidget):
    def __init__(self, text, target_widget, duration_ms=DEFAULT_MESSAGE_DURATION_MS):
        super().__init__(None)
        self.target = target_widget
        self.ui_scale = 0.0
        self.theme = load_dialog_theme()
        self.arrow_side = "left"
        self.setWindowTitle("维维美 · 对话")
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if sys.platform != "darwin":
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(BASE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 15, 18, 29)
        layout.setSpacing(8)
        caption = QLabel("维维美  /  VIVI", self)
        caption.setProperty("role", "eyebrow")
        layout.addWidget(caption)
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { border: none; background: transparent; }")
        self.label = QLabel(text, self.scroll)
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.scroll.setWidget(self.label)
        layout.addWidget(self.scroll, 1)

        self.follow_timer = QTimer(self)
        self.follow_timer.timeout.connect(self._sync_with_target)
        self.follow_timer.start(80)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close)
        self.timer.start(bounded_int(duration_ms, default=DEFAULT_MESSAGE_DURATION_MS,
                                     minimum=1000, maximum=60000))
        self._sync_with_target(force=True)

    @staticmethod
    def _menu_scale_from_maid_scale(maid_scale):
        # 对话可读性独立于极端桌宠缩放，避免文字缩到不可读或遮满屏幕。
        return bounded_float(maid_scale, default=1.0, minimum=0.9, maximum=1.4)

    def _resolve_menu_center(self):
        if self.target is None or sip.isdeleted(self.target):
            return None
        actions = getattr(self.target, "maid_actions", None)
        if actions is not None and hasattr(actions, "_get_circular_menu_center_point"):
            return actions._get_circular_menu_center_point()
        return self.target.frameGeometry().center()

    def _sync_with_target(self, force=False):
        anchor = self._resolve_menu_center()
        if anchor is None:
            self.close()
            return
        screen = QApplication.screenAt(anchor) or self.target.screen()
        if screen is None:
            return
        area = screen.availableGeometry()
        scale = self._menu_scale_from_maid_scale(getattr(self.target, "user_scale", 1.0))
        width = min(int(290 * scale), max(160, area.width() - 24))
        if force or scale != self.ui_scale or width != self.width():
            self.ui_scale = scale
            font = QFont(default_ui_font_family())
            font.setPixelSize(round(13 * scale))
            self.label.setFont(font)
            self.setFixedWidth(width)
            self.label.setFixedWidth(width - 44)
            content_height = self.label.heightForWidth(width - 44)
            height = min(max(108, content_height + 78), max(108, int(area.height() * 0.48)))
            self.setFixedHeight(height)
            self.label.setMinimumHeight(content_height)

        # 有菜单时把气泡放到半径之外；无菜单时贴近角色头部，减少遮挡。
        menu = getattr(getattr(self.target, "maid_actions", None), "circular_menu", None)
        menu_visible = menu is not None and not sip.isdeleted(menu) and menu.isVisible()
        offset = int(155 * scale) if menu_visible else max(48, self.target.width() // 3)
        x = anchor.x() + offset
        self.arrow_side = "left"
        if x + self.width() > area.right():
            x = anchor.x() - offset - self.width()
            self.arrow_side = "right"
        self.move(x, anchor.y() - self.height() - 12)
        keep_on_screen(self, anchor)
        self.update()

    def update_position(self):
        self._sync_with_target()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = QPainterPath()
        body.addRoundedRect(QRectF(1, 1, self.width() - 2, self.height() - 15), 16, 16)
        tip = QPainterPath()
        x = self.width() - 30 if self.arrow_side == "right" else 30
        tip.moveTo(x - 7, self.height() - 16)
        tip.lineTo(x, self.height() - 3)
        tip.lineTo(x + 7, self.height() - 16)
        tip.closeSubpath()
        painter.setBrush(QColor(P.surface))
        outline = self.theme.get("outline_dialog_bubble") == "true"
        painter.setPen(QPen(QColor(P.charcoal if outline else P.line), 2 if outline else 1))
        painter.drawPath(body.united(tip))
        painter.setPen(QPen(QColor(P.accent), 2))
        painter.drawLine(18, 31, 44, 31)

    def closeEvent(self, event):
        # 隐藏顶层窗口不会自动停止 QTimer；关闭时同时停止跟随并销毁。
        self.follow_timer.stop()
        self.timer.stop()
        super().closeEvent(event)
        self.deleteLater()


class DialogueSystem:
    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.current_bubble = None

    def show_message(self, title, content, duration_ms=DEFAULT_MESSAGE_DURATION_MS):
        self.hide_dialogue()
        safe_title = html.escape(str(title)[:200])
        safe_content = html.escape(str(content)[:4096]).replace("\n", "<br>")
        text = f'<b>{safe_title}</b><br><span style="color:{P.muted}">{safe_content}</span>'
        bubble = SpeechBubble(text, self.parent, duration_ms=duration_ms)
        self.current_bubble = bubble
        bubble.destroyed.connect(lambda: self._clear_bubble(bubble))
        bubble.show()

    def _clear_bubble(self, bubble):
        # 旧气泡延迟销毁时，不能把刚创建的新气泡引用一起清掉。
        if self.current_bubble is bubble:
            self.current_bubble = None

    def hide_dialogue(self):
        bubble, self.current_bubble = self.current_bubble, None
        if bubble is not None and not sip.isdeleted(bubble):
            bubble.close()
