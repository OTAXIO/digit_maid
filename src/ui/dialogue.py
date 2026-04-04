from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPainterPath, QFont, QTextDocument

from src.input.choice_dialog import load_dialog_theme

class OutlineLabel(QLabel):
    def __init__(self, text="", enable_outline=True, parent=None):
        super().__init__(text, parent)
        self.enable_outline = enable_outline

    def paintEvent(self, event):
        if not self.enable_outline:
            super().paintEvent(event)
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        doc = QTextDocument()
        doc.setDocumentMargin(0)
        doc.setDefaultFont(self.font())
        doc.setTextWidth(self.width())
        
        # 将原有的 HTML 文本重新包裹为黑色，来作为底本渲染描边边缘
        text = self.text()
        doc.setHtml(f"<div style='color: black;'>{text}</div>")
        
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx == 0 and dy == 0:
                    continue
                painter.save()
                painter.translate(dx, dy)
                doc.drawContents(painter)
                painter.restore()
                
        # 还原白色作为最顶层的内容
        doc.setHtml(f"<div style='color: white;'>{text}</div>")
        doc.drawContents(painter)

class SpeechBubble(QWidget):
    def __init__(self, text, target_widget):
        super().__init__(None) # 无父级，作为独立顶层窗口
        self.target = target_widget
        self.text = text
        
        self.theme = load_dialog_theme()
        self.outline_dialog_text = str(self.theme.get("outline_dialog_text", "false")).lower() == "true"
        self.outline_dialog_bubble = str(self.theme.get("outline_dialog_bubble", "false")).lower() == "true"
        
        # 设置窗口属性：无边框、置顶、透明背景
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 布局与内容
        layout = QVBoxLayout()
        self.label = OutlineLabel(text, enable_outline=self.outline_dialog_text)
        self.label.setWordWrap(True)
        # 支持 HTML 格式 (比如标题加粗)
        self.label.setTextFormat(Qt.TextFormat.RichText) 
        self.label.setFont(QFont("Microsoft YaHei", 10))
        
        if self.outline_dialog_text:
            self.label.setStyleSheet("color: transparent;") # 隐藏自带的字，只保留自定义边框文字
        else:
            self.label.setStyleSheet("color: white;")
            
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
            screen_geo = QApplication.primaryScreen().availableGeometry()
            
            # 计算气泡位置：显示在目标的右上方
            # 这里的调整值 (margin) 可能需要根据视觉效果微调
            x = target_geo.x() + target_geo.width() // 2 + 10
            y = target_geo.y() - self.height() + 40
            
            # 边界检测
            if x + self.width() > screen_geo.right():
                x = screen_geo.right() - self.width()
            if x < screen_geo.left():
                x = screen_geo.left()
                
            if y + self.height() > screen_geo.bottom():
                y = screen_geo.bottom() - self.height()
            if y < screen_geo.top():
                y = screen_geo.top()
                
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
        path.addRoundedRect(rect, 25, 25) # 增加圆角半径使其更加圆润
        
        # 绘制小尾巴 (指向左下角)
        # 箭头起点 (在矩形底部边框上)
        arrow_start_x = 20
        path.moveTo(arrow_start_x, height - arrow_height)
        
        # 箭头尖端
        path.lineTo(arrow_start_x - 10, height)
        
        # 箭头终点 (在矩形底部边框上)
        path.lineTo(arrow_start_x + 15, height - arrow_height)
        
        # 合并路径会自动处理重叠部分
        
        # 使用和圆形菜单一致的深红色背景
        painter.setBrush(QBrush(QColor("#c41c1c")))
        if getattr(self, "outline_dialog_bubble", False):
            # 使用黑色描边
            painter.setPen(QPen(QColor(0, 0, 0), 3))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        
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
