from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath
from PyQt6.QtCore import Qt, QPointF

class OutlineLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        
    def paintEvent(self, event):
        # 让它可以用 PainterPath 画边框（适用于单行或简单多行纯文本）
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        text = self.text()
        rect = self.contentsRect()
        font = self.font()
        
        path = QPainterPath()
        
        # 处理带有换行符的简单多行纯文字（不解析HTML）
        lines = text.split('\n')
        fm = painter.fontMetrics()
        
        # 计算总体高度以居中
        line_height = fm.height()
        total_height = line_height * len(lines)
        
        start_y = rect.y() + (rect.height() - total_height) / 2.0 + fm.ascent()
        
        for i, line in enumerate(lines):
            text_rect = fm.boundingRect(line)
            # 计算居中（或者保持原本的 alignment，这里简单做水平居中，或者左对齐）
            alignment = self.alignment()
            if alignment & Qt.AlignmentFlag.AlignCenter:
                x = rect.x() + (rect.width() - text_rect.width()) / 2.0
            elif alignment & Qt.AlignmentFlag.AlignRight:
                x = rect.x() + rect.width() - text_rect.width()
            else:
                x = rect.x() # default Left Align
                
            y = start_y + i * line_height
            path.addText(QPointF(x, y), font, line)
            
        # Draw stroke
        pen = QPen(QColor("black"))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawPath(path)
        
        # Draw fill
        painter.fillPath(path, QColor("white"))
