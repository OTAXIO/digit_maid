from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPainterPath, QFont

class SpeechBubble(QWidget):
    def __init__(self, text, target_widget):
        super().__init__(None) # 无父级，作为独立顶层窗口
        self.target = target_widget
        self.text = text
        
        # 设置窗口属性：无边框、置顶、透明背景
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 布局与内容
        layout = QVBoxLayout()
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        # 支持 HTML 格式 (比如标题加粗)
        self.label.setTextFormat(Qt.TextFormat.RichText) 
        self.label.setFont(QFont("Microsoft YaHei", 10))
        self.label.setStyleSheet("color: black;")
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        # 设置边距，底部留出空间给箭头
        # (left, top, right, bottom)
        layout.setContentsMargins(15, 15, 15, 30) 
        
        # 限制最大宽度，防止气泡太长
        self.setMaximumWidth(250)
        
        # 调整大小以适应文本
        self.adjustSize()
        
        # 定位到目标附近
        self.update_position()
        
        # 4秒后自动淡出或关闭
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.close)
        self.timer.start(4000)

    def update_position(self):
        if self.target:
            target_geo = self.target.frameGeometry()
            # 计算气泡位置：显示在目标的右上方
            # 这里的调整值 (margin) 可能需要根据视觉效果微调
            x = target_geo.x() + target_geo.width() // 2 + 10
            y = target_geo.y() - self.height() + 40
            self.move(int(x), int(y))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        arrow_height = 20 # 底部箭头区域的高度
        
        # 气泡主体区域
        rect = QRectF(0, 0, width, height - arrow_height)
        
        path = QPainterPath()
        path.addRoundedRect(rect, 15, 15) # 圆角矩形
        
        # 绘制小尾巴 (指向左下角)
        # 箭头起点 (在矩形底部边框上)
        arrow_start_x = 20
        path.moveTo(arrow_start_x, height - arrow_height)
        
        # 箭头尖端
        path.lineTo(arrow_start_x - 10, height)
        
        # 箭头终点 (在矩形底部边框上)
        path.lineTo(arrow_start_x + 15, height - arrow_height)
        
        # 合并路径会自动处理重叠部分
        
        # 填充白色
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        # 描边 (深灰色)
        painter.setPen(QPen(QColor(60, 60, 60), 2))
        
        painter.drawPath(path)

class DialogueSystem:
    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.current_bubble = None

    def show_message(self, title, content):
        # 如果之前有气泡，先关闭旧的
        if self.current_bubble:
            try:
                self.current_bubble.close()
            except:
                pass
        
        # 构建显示文本，标题加粗
        display_text = f"<b>{title}</b><br>{content}"
        
        self.current_bubble = SpeechBubble(display_text, self.parent)
        self.current_bubble.show()
