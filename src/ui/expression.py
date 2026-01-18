from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt

class PetPainter:
    # 基准尺寸（原始设计尺寸）
    BASE_SIZE = 150
    
    def paint(self, painter: QPainter, width: int, height: int, state: dict):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 计算缩放比例
        scale = min(width, height) / self.BASE_SIZE
        
        # 辅助函数：根据比例缩放坐标
        def s(value):
            return int(value * scale)

        # 画身体 (圆形)
        painter.setBrush(QBrush(QColor(100, 149, 237))) # CornflowerBlue
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, width, height)

        is_blinking = state.get("is_blinking", False)
        is_excited = state.get("is_excited", False)
        
        # 线条粗细也需要缩放
        line_width = max(1, s(3))

        # 画眼睛
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        
        if is_blinking:
            # 闭眼
            painter.setBrush(QBrush(QColor(100, 149, 237))) # 身体颜色遮挡
            painter.setPen(QPen(QColor(0, 0, 0), line_width))
            painter.drawLine(s(35), s(55), s(65), s(55))
            painter.drawLine(s(85), s(55), s(115), s(55))
        elif is_excited:
            # 开心 ( > < )
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 0, 0), line_width))
            
            # 左眼
            painter.drawLine(s(35), s(45), s(65), s(55))
            painter.drawLine(s(35), s(65), s(65), s(55))
            
            # 右眼
            painter.drawLine(s(85), s(55), s(115), s(45))
            painter.drawLine(s(85), s(55), s(115), s(65))
        else:
            # 睁眼 (眼白)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(s(35), s(40), s(30), s(30))
            painter.drawEllipse(s(85), s(40), s(30), s(30))
            
            # 眼珠
            painter.setBrush(QBrush(QColor(0, 0, 0)))
            painter.drawEllipse(s(45), s(48), s(10), s(10))
            painter.drawEllipse(s(95), s(48), s(10), s(10))

        # 画嘴巴
        painter.setPen(QPen(QColor(0, 0, 0), line_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(s(50), s(70), s(50), s(30), 0, -180 * 16)
        
        # 画腮红
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 192, 203, 150))) # 粉色半透明
        painter.drawEllipse(s(20), s(70), s(20), s(10))
        painter.drawEllipse(s(110), s(70), s(20), s(10))
