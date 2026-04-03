import math
from PyQt6.QtWidgets import QWidget, QPushButton, QApplication
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QPoint, QTimer
from PyQt6.QtGui import QPainter, QColor

class BubbleButton(QPushButton):
    def __init__(self, text, is_back=False, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(70, 70)
        
        if is_back:
            bg_color = "#cfcecd"
            border_color = "#c41c1c"
            hover_bg = "#8f8f8e"
            pressed_bg = "#444444"
        else:
            bg_color = "#c41c1c"
            border_color = "#cfcecd"
            hover_bg = "#e32424"
            pressed_bg = "#a81616"

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border-radius: 35px;
                font-weight: bold;
                border: 4px solid {border_color};
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
            }}
        """)

    def set_target_pos(self, x, y, angle):
        self.base_x = x
        self.base_y = y
        self.angle = angle

    def enterEvent(self, event):
        super().enterEvent(event)
        self.raise_()
        if hasattr(self, 'base_x') and hasattr(self, 'base_y') and hasattr(self, 'angle'):
            hover_x = self.base_x + 10 * math.cos(self.angle)
            hover_y = self.base_y - 10 * math.sin(self.angle)
            
            if hasattr(self, 'anim') and self.anim.state() == QPropertyAnimation.State.Running:
                # 初始展开动画还没完成，不要打断
                pass
            else:
                if hasattr(self, 'hover_anim') and self.hover_anim.state() == QPropertyAnimation.State.Running:
                    self.hover_anim.stop()
                if hasattr(self, 'leave_anim') and self.leave_anim.state() == QPropertyAnimation.State.Running:
                    self.leave_anim.stop()
                
                self.hover_anim = QPropertyAnimation(self, b"geometry")
                self.hover_anim.setDuration(100)
                self.hover_anim.setStartValue(self.geometry())
                self.hover_anim.setEndValue(QRect(int(hover_x), int(hover_y), self.width(), self.height()))
                self.hover_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
                self.hover_anim.start(QPropertyAnimation.DeletionPolicy.KeepWhenStopped)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if hasattr(self, 'base_x') and hasattr(self, 'base_y'):
            if hasattr(self, 'anim') and self.anim.state() == QPropertyAnimation.State.Running:
                pass
            else:
                if hasattr(self, 'hover_anim') and self.hover_anim.state() == QPropertyAnimation.State.Running:
                    self.hover_anim.stop()
                if hasattr(self, 'leave_anim') and self.leave_anim.state() == QPropertyAnimation.State.Running:
                    self.leave_anim.stop()
                    
                self.leave_anim = QPropertyAnimation(self, b"geometry")
                self.leave_anim.setDuration(100)
                self.leave_anim.setStartValue(self.geometry())
                self.leave_anim.setEndValue(QRect(int(self.base_x), int(self.base_y), self.width(), self.height()))
                self.leave_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
                self.leave_anim.start(QPropertyAnimation.DeletionPolicy.KeepWhenStopped)

class CircularMenuWidget(QWidget):
    def __init__(self, items, center_pos, on_close_callback=None, parent=None):
        """
        items: list of dicts. [{'label': 'name', 'action': callable or sub_items_list}]
        """
        super().__init__(None) # Independent window
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Cover the whole screen
        screen_geo = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen_geo)
        
        self.center_pos = center_pos
        self.on_close_callback = on_close_callback
        
        self.history = [] # Stack of (items, page_idx)
        self.current_items = items
        self.current_page = 0
        self.buttons = []
        
        self._build_menu()
        
    def _build_menu(self):
        # Clear old buttons
        for btn in self.buttons:
            btn.deleteLater()
        self.buttons.clear()
        
        R = 120 # Radius of the arc
        
        # Separate special items from regular ones
        regular_items = []
        exit_item = None
        for item in self.current_items:
            if item['label'] == '退出':
                exit_item = item
            else:
                regular_items.append(item)
                
        # Pagination logic
        page_items = []
        if len(regular_items) > 5:
            start_idx = 0
            for i in range(self.current_page):
                start_idx += 4 if i == 0 else 3
                
            items_left = len(regular_items) - start_idx
            
            if self.current_page == 0:
                page_items.extend(regular_items[start_idx : start_idx + 4])
                page_items.append({'label': '>', 'action': 'next_page'})
            else:
                page_items.append({'label': '<', 'action': 'prev_page'})
                if items_left > 4:
                    page_items.extend(regular_items[start_idx : start_idx + 3])
                    page_items.append({'label': '>', 'action': 'next_page'})
                else:
                    page_items.extend(regular_items[start_idx : start_idx + 4])
        else:
            page_items = regular_items.copy()
            
        display_items = []
        # Add 'Back' button if in sub-menu
        if self.history:
            display_items.append({'label': '返回', 'action': 'back'})
            
        display_items.extend(page_items)
        if exit_item:
            display_items.append(exit_item)
            
        n = len(display_items)
        if n == 1:
            angles = [math.pi / 2]
        else:
            # 智能判断可用的角度范围
            screen_geo = QApplication.primaryScreen().availableGeometry()
            margin = R + 45  # 半径 + 按钮半径(35) + 边距(10)
            
            can_up = (self.center_pos.y() - screen_geo.top()) >= margin
            can_down = (screen_geo.bottom() - self.center_pos.y()) >= margin
            can_left = (self.center_pos.x() - screen_geo.left()) >= margin
            can_right = (screen_geo.right() - self.center_pos.x()) >= margin
            
            if can_up and can_left and can_right:
                # 默认情况：上方半圆 180° 到 0°
                start_angle = math.pi
                sweep_angle = -math.pi
            elif not can_up and can_left and can_right:
                # 靠上：下方半圆 180° 到 360° (左到右)
                start_angle = math.pi
                sweep_angle = math.pi
            elif not can_left and can_up and can_down:
                # 靠左：右方半圆 90° 到 -90° (上到下)
                start_angle = math.pi / 2
                sweep_angle = -math.pi
            elif not can_right and can_up and can_down:
                # 靠右：左方半圆 90° 到 270° (上到下)
                start_angle = math.pi / 2
                sweep_angle = math.pi
            elif not can_up and not can_left:
                # 左上角：右下方 0° 到 -90° (右到下)
                start_angle = 0
                sweep_angle = -math.pi / 2
            elif not can_up and not can_right:
                # 右上角：左下方 180° 到 270° (左到下)
                start_angle = math.pi
                sweep_angle = math.pi / 2
            elif not can_down and not can_left:
                # 左下角：右上方 90° 到 0° (上到右)
                start_angle = math.pi / 2
                sweep_angle = -math.pi / 2
            elif not can_down and not can_right:
                # 右下角：左上方 90° 到 180° (上到左)
                start_angle = math.pi / 2
                sweep_angle = math.pi / 2
            elif not can_down and can_left and can_right:
                # 靠下：上方半圆 180° 到 0° (与默认相同)
                start_angle = math.pi
                sweep_angle = -math.pi
            else:
                # 兜底：上方半圆
                start_angle = math.pi
                sweep_angle = -math.pi
                
            angles = [start_angle + i * (sweep_angle / (n - 1)) for i in range(n)]
            
        for i, item in enumerate(display_items):
            is_special_btn = (item['label'] in ['返回', '退出', '<', '>'])
            btn = BubbleButton(item['label'], is_back=is_special_btn, parent=self)
            
            # Target position
            tar_x = self.center_pos.x() + R * math.cos(angles[i]) - btn.width() / 2
            tar_y = self.center_pos.y() - R * math.sin(angles[i]) - btn.height() / 2
            
            # Start position (center)
            start_x = self.center_pos.x() - btn.width() / 2
            start_y = self.center_pos.y() - btn.height() / 2
            
            btn.move(int(start_x), int(start_y))
            
            # Animation
            anim = QPropertyAnimation(btn, b"geometry")
            anim.setDuration(300)
            anim.setStartValue(QRect(int(start_x), int(start_y), btn.width(), btn.height()))
            anim.setEndValue(QRect(int(tar_x), int(tar_y), btn.width(), btn.height()))
            anim.setEasingCurve(QEasingCurve.Type.OutBack)
            anim.start(QPropertyAnimation.DeletionPolicy.KeepWhenStopped)
            
            # Save ref to keep anim alive? Not strictly necessary in PyQt but safe
            setattr(btn, 'anim', anim)
            btn.set_target_pos(tar_x, tar_y, angles[i])
            
            def make_callback(action_val):
                def cb():
                    if action_val == 'back':
                        self.current_items, self.current_page = self.history.pop()
                        self._build_menu()
                    elif action_val == 'next_page':
                        self.current_page += 1
                        self._build_menu()
                    elif action_val == 'prev_page':
                        self.current_page -= 1
                        self._build_menu()
                    elif isinstance(action_val, list):
                        # Enter sub-menu
                        self.history.append((self.current_items, self.current_page))
                        self.current_items = action_val
                        self.current_page = 0
                        self._build_menu()
                    elif callable(action_val):
                        # Execute and close
                        self.close_menu()
                        action_val()
                return cb
                
            btn.clicked.connect(make_callback(item['action']))
            btn.show()
            self.buttons.append(btn)
            
    def mousePressEvent(self, event):
        # Click outside closes the menu
        self.close_menu()
        
    def close_menu(self):
        if self.on_close_callback:
            self.on_close_callback()
        self.close()
