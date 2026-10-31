"""只读任务卡片绘制；编辑始终在独立整页编辑器中进行。"""

from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QColor, QFont, QPen
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle

from src.ui.theme import P, default_ui_font_family


class TodoItemDelegate(QStyledItemDelegate):
    # 月度列表附带的日期信息：{"day", "weekday", "is_today", "show_date"}。
    DAY_ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None, *, compact=False):
        super().__init__(parent)
        self.compact = compact

    def sizeHint(self, option, index):
        return QSize(0, 42 if self.compact else 62)

    def paint(self, painter, option, index):
        task = index.data(Qt.ItemDataRole.UserRole)
        if not isinstance(task, dict):
            super().paint(painter, option, index)
            return
        completed = task.get("completed") is True
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        if self.compact:
            self._paint_month_row(painter, option.rect, task, index.data(self.DAY_ROLE), completed, hovered)
            painter.restore()
            return
        rect = option.rect.adjusted(1, 3, -1, -3)
        # 红色透明度只作用于背景和边框，正文始终保持不透明，保证可读性。
        background = QColor(P.completed_bg if completed else P.accent)
        border = QColor(P.line if completed else P.accent)
        if not completed:
            background.setAlpha(42 if selected else 34 if hovered else 24)
            border.setAlpha(255 if selected else 128 if hovered else 90)
        painter.setPen(QPen(border))
        painter.setBrush(background)
        painter.drawRoundedRect(rect, 10, 10)
        font = QFont(default_ui_font_family())
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(QColor(P.completed if completed else P.accent))
        header_rect = QRect(rect.left() + 12, rect.top() + 5, rect.width() - 24, 20)
        painter.drawText(header_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         task.get("ddl") or "未设时间")
        painter.setPen(QColor(P.completed if completed else P.muted))
        painter.drawText(header_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                         "已完成" if completed else "待完成")
        font.setPixelSize(13)
        font.setWeight(QFont.Weight.Normal)
        font.setStrikeOut(completed)
        painter.setFont(font)
        painter.setPen(QColor(P.completed if completed else P.ink))
        text = painter.fontMetrics().elidedText(task.get("text", ""), Qt.TextElideMode.ElideRight,
                                               max(1, rect.width() - 24))
        painter.drawText(QRect(rect.left() + 12, rect.top() + 30, rect.width() - 24, 25),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        painter.restore()

    @staticmethod
    def _paint_month_row(painter, row_rect, task, day_info, completed, hovered):
        """月度列表：左侧日期列按天分组，右侧轻量卡片显示时间与事项。"""
        rect = row_rect.adjusted(0, 2, -2, -2)
        date_width = 40
        if isinstance(day_info, dict) and day_info.get("show_date"):
            font = QFont(default_ui_font_family())
            font.setPixelSize(15)
            font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.setPen(QColor(P.accent if day_info.get("is_today") else P.ink))
            painter.drawText(QRect(rect.left(), rect.top() + 2, date_width, 20),
                             Qt.AlignmentFlag.AlignCenter, str(day_info.get("day", "")))
            font.setPixelSize(10)
            font.setWeight(QFont.Weight.Normal)
            painter.setFont(font)
            painter.setPen(QColor(P.accent if day_info.get("is_today") else P.muted))
            painter.drawText(QRect(rect.left(), rect.top() + 22, date_width, 14),
                             Qt.AlignmentFlag.AlignCenter, day_info.get("weekday", ""))

        card = rect.adjusted(date_width + 4, 0, 0, 0)
        background = QColor(P.inset if hovered else P.completed_bg if completed else P.canvas)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(card, 9, 9)
        if not completed:
            painter.setBrush(QColor(P.accent))
            painter.drawRoundedRect(QRect(card.left() + 6, card.top() + 10, 3, card.height() - 20), 1.5, 1.5)

        font = QFont(default_ui_font_family())
        font.setPixelSize(12)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(QColor(P.faint if completed else P.accent))
        time_rect = QRect(card.left() + 16, card.top(), 42, card.height())
        painter.drawText(time_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         task.get("ddl") or "--:--")

        font.setPixelSize(13)
        font.setWeight(QFont.Weight.Normal)
        font.setStrikeOut(completed)
        painter.setFont(font)
        painter.setPen(QColor(P.completed if completed else P.ink))
        text_rect = QRect(time_rect.right() + 6, card.top(), card.right() - time_rect.right() - 16, card.height())
        text = painter.fontMetrics().elidedText(task.get("text", ""), Qt.TextElideMode.ElideRight,
                                               max(1, text_rect.width()))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
