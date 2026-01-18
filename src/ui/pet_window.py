from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QMenu, QApplication
from PyQt6.QtCore import Qt, QPoint, QSize, QTimer
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QAction, QCursor
import sys
import os

# 导入功能模块
# 为了方便导入，可以在这里临时添加一下路径，或者在 main 中处理
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.features import organizer, automation

class PetWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        self.initUI()
        self.offset = QPoint()
        
        # 简单状态：眨眼动画
        self.is_blinking = False
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.blink)
        self.blink_timer.start(3000) # 每3秒眨一次眼

    def initUI(self):
        # 设置无边框和置顶
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setGeometry(100, 100, 150, 150)
        self.setWindowTitle('DigitMaid')

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 画身体 (圆形)
        painter.setBrush(QBrush(QColor(100, 149, 237))) # CornflowerBlue
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 150, 150)

        # 画眼睛
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        if self.is_blinking:
            # 闭眼
            painter.setBrush(QBrush(QColor(100, 149, 237))) # 身体颜色遮挡
            painter.setPen(QPen(QColor(0, 0, 0), 3))
            painter.drawLine(35, 55, 65, 55)
            painter.drawLine(85, 55, 115, 55)
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

    def blink(self):
        self.is_blinking = True
        self.update()
        QTimer.singleShot(200, self.finish_blink)

    def finish_blink(self):
        self.is_blinking = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif event.button() == Qt.MouseButton.RightButton:
            self.showContextMenu(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.offset)

    def showContextMenu(self, event):
        menu = QMenu(self)
        
        # 整理桌面
        action_organize = QAction('整理桌面', self)
        action_organize.triggered.connect(self.do_organize)
        menu.addAction(action_organize)

        # 截图/识别屏幕
        action_screenshot = QAction('识别屏幕 (截图)', self)
        action_screenshot.triggered.connect(self.do_screenshot)
        menu.addAction(action_screenshot)

        # 打开常用软件子菜单
        app_menu = menu.addMenu("打开软件")
        
        apps = ["计算器", "记事本", "终端"]
        for app in apps:
            action = QAction(app, self)
            action.triggered.connect(lambda checked, a=app: self.do_open_app(a))
            app_menu.addAction(action)

        menu.addSeparator()
        
        action_quit = QAction('退出', self)
        action_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(action_quit)

        menu.exec(event.globalPosition().toPoint())

    def do_organize(self):
        print("正在整理桌面...")
        result = organizer.organize_desktop()
        print(result)

    def do_screenshot(self):
        print("正在识别屏幕...")
        result = automation.capture_screen_content()
        print(result)

    def do_open_app(self, app_name):
        print(f"正在打开 {app_name}...")
        result = automation.open_application(app_name)
        print(result)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    pet = PetWindow()
    pet.show()
    sys.exit(app.exec())
