"""只读任务卡片绘制；编辑始终在独立整页编辑器中进行。"""

from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QColor, QFont, QPen
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle

from src.ui.theme import P, default_ui_font_family


class TodoItemDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(0, 62)

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
        rect = option.rect.adjusted(1, 3, -1, -3)
        painter.setPen(QPen(QColor(P.accent if selected else P.line if hovered else P.canvas)))
        painter.setBrush(QColor(P.completed_bg if completed else P.accent_soft if selected else P.canvas))
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
