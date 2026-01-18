from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt

class PetPainter:
    def paint(self, painter: QPainter, width: int, height: int, state: dict):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 画身体 (圆形)
        painter.setBrush(QBrush(QColor(100, 149, 237))) # CornflowerBlue
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, width, height)

        is_blinking = state.get("is_blinking", False)
        is_excited = state.get("is_excited", False)

        # 画眼睛
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        
        if is_blinking:
            # 闭眼
            painter.setBrush(QBrush(QColor(100, 149, 237))) # 身体颜色遮挡
            painter.setPen(QPen(QColor(0, 0, 0), 3))
            painter.drawLine(35, 55, 65, 55)
            painter.drawLine(85, 55, 115, 55)
        elif is_excited:
            # 开心 ( > < )
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 0, 0), 3))
            
            # 左眼
            painter.drawLine(35, 45, 65, 55)
            painter.drawLine(35, 65, 65, 55)
            
            # 右眼
            painter.drawLine(85, 55, 115, 45)
            painter.drawLine(85, 55, 115, 65)
        else:
            # 睁眼 (眼白)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(35, 40, 30, 30)
            painter.drawEllipse(85, 40, 30, 30)
            
            # 眼珠
            painter.setBrush(QBrush(QColor(0, 0, 0)))
            painter.drawEllipse(45, 48, 10, 10)
            painter.drawEllipse(95, 48, 10, 10)

        # 画嘴巴
        painter.setPen(QPen(QColor(0, 0, 0), 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(50, 70, 50, 30, 0, -180 * 16)
        
        # 画腮红
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 192, 203, 150))) # 粉色半透明
        painter.drawEllipse(20, 70, 20, 10)
        painter.drawEllipse(110, 70, 20, 10)
