"""可复用的品牌标记、阴影和窗口边界工具，避免每个窗口重复拼装。"""

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QGraphicsDropShadowEffect

from src.core.paths import resource_path
from . import P


def character_badge(parent=None, size=44):
    label = QLabel(parent)
    label.setFixedSize(size, size)
    pixmap = QPixmap(str(resource_path("wisdel", "皮肤素材", "维什戴尔大人.png")))
    if not pixmap.isNull():
        label.setPixmap(pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation))
    label.setAccessibleName("维维美")
    return label


def apply_shadow(widget, blur=28, offset=7):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, offset)
    color = QColor(P.charcoal)
    color.setAlpha(42)
    effect.setColor(color)
    widget.setGraphicsEffect(effect)


def keep_on_screen(widget, anchor=None):
    """按窗口所在屏幕的工作区夹取坐标，兼容副屏的负坐标。"""
    screen = QApplication.screenAt(anchor or widget.frameGeometry().center()) or widget.screen()
    if screen is None:
        return
    area = screen.availableGeometry()
    widget.move(QPoint(
        max(area.left(), min(widget.x(), area.right() - widget.width() + 1)),
        max(area.top(), min(widget.y(), area.bottom() - widget.height() + 1)),
    ))
