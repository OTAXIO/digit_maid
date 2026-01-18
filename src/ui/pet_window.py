from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QPainter
import sys

# 导入分离后的UI模块
from .dialogue import DialogueSystem
from .action import PetActions
from .expression import PetPainter

class PetWindow(QWidget):
    # 缩放限制
    MIN_SIZE = 80
    MAX_SIZE = 300
    SCALE_STEP = 10
    
    def __init__(self):
        super().__init__()
        
        self.initUI()
        self.offset = QPoint()
        
        # 当前尺寸
        self.pet_size = 150
        
        # 简单状态
        self.is_blinking = False
        self.is_excited = False
        
        # 初始化各个子系统
        self.dialogue_system = DialogueSystem(self)
        self.pet_actions = PetActions(self, self.dialogue_system)
        self.pet_painter = PetPainter()

        # 眨眼动画定时器
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.blink)
        self.blink_timer.start(3000) # 每3秒眨一次眼

    def initUI(self):
        # ... (保持不变)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 获取屏幕尺寸
        screen = QApplication.primaryScreen().availableGeometry()
        pet_width = 150
        pet_height = 150
        
        # 计算右下角位置 (减去一点边距)
        x = screen.width() - pet_width - 100 
        y = screen.height() - pet_height - 100
        
        self.setGeometry(x, y, pet_width, pet_height)
        self.setWindowTitle('DigitMaid')

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 收集当前状态传输给绘制器
        current_state = {
            "is_blinking": self.is_blinking,
            "is_excited": self.is_excited
        }
        
        self.pet_painter.paint(painter, self.width(), self.height(), current_state)

    def blink(self):
        self.is_blinking = True
        self.update()
        QTimer.singleShot(200, self.finish_blink)

    def finish_blink(self):
        self.is_blinking = False
        self.update()

    def restore_expression(self):
        self.is_excited = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            
            # 点击反馈：变成开心表情
            self.is_excited = True
            self.update()
            QTimer.singleShot(800, self.restore_expression)
            
        elif event.button() == Qt.MouseButton.RightButton:
            # 委托 action 模块处理右键菜单
            self.pet_actions.show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.offset)

    def wheelEvent(self, event):
        """鼠标滚轮缩放桌宠"""
        # 获取滚轮滚动方向
        delta = event.angleDelta().y()
        
        if delta > 0:
            # 向上滚动，放大
            new_size = min(self.pet_size + self.SCALE_STEP, self.MAX_SIZE)
        else:
            # 向下滚动，缩小
            new_size = max(self.pet_size - self.SCALE_STEP, self.MIN_SIZE)
        
        if new_size != self.pet_size:
            # 计算中心点，保持缩放时中心不变
            old_center = self.geometry().center()
            
            self.pet_size = new_size
            self.setFixedSize(new_size, new_size)
            
            # 重新定位，使中心点保持不变
            new_x = old_center.x() - new_size // 2
            new_y = old_center.y() - new_size // 2
            self.move(new_x, new_y)
            
            self.update()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    pet = PetWindow()
    pet.show()
    sys.exit(app.exec())
