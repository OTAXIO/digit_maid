import math
import sys

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
        self.use_image_buttons = self.theme.get("circular_button_mode", "default").lower() == "image"
        self.ui_scale = 1.0
        self.menu_radius = 120
        self.arrow_height = 20
        self.corner_radius = 25
        self.arrow_start_x = 20
        self.arrow_tip_dx = 10
        self.arrow_end_dx = 15
        
        # macOS 下避免始终置顶，防止影响切换到其他应用。
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if sys.platform != "darwin":
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
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
        
        # 先按当前缩放同步样式与位置
        self._sync_with_target(force=True)

        # 跟随桌宠与菜单实时更新位置/尺寸
        self.follow_timer = QTimer(self)
        self.follow_timer.timeout.connect(self._sync_with_target)
        self.follow_timer.start(33)
        
        # 2秒后自动淡出或关闭
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.close)
        self.timer.start(2000)

    @staticmethod
    def _menu_scale_from_maid_scale(maid_scale):
        try:
            scale = float(maid_scale)
        except (TypeError, ValueError):
            scale = 1.0

        if scale >= 1.0:
            mapped = 1.0 + (scale - 1.0) * 0.75
        else:
            mapped = scale
        return max(0.4, mapped)

    def _resolve_ui_scale(self):
        if self.target is None:
            return 1.0
        return self._menu_scale_from_maid_scale(getattr(self.target, "user_scale", 1.0))

    def _compute_menu_radius(self, ui_scale):
        btn_half = max(14, int((80 if self.use_image_buttons else 70) * ui_scale / 2))
        radius = max(48, int(120 * ui_scale))

        return radius

    def _apply_scaled_style(self, ui_scale, force=False):
        ui_scale = max(0.4, float(ui_scale))
        if not force and abs(ui_scale - self.ui_scale) <= 1e-6:
            return False

        self.ui_scale = ui_scale

        font_px = max(6, int(round(10 * self.ui_scale)))
        self.label.setFont(QFont("Microsoft YaHei", font_px))

        max_width = max(100, int(round(250 * self.ui_scale)))
        self.setMaximumWidth(max_width)

        margin_lr = max(6, int(round(15 * self.ui_scale)))
        margin_top = margin_lr
        margin_bottom = max(12, int(round(30 * self.ui_scale)))
        self.layout().setContentsMargins(margin_lr, margin_top, margin_lr, margin_bottom)

        self.arrow_height = max(12, int(round(20 * self.ui_scale)))
        self.corner_radius = max(14, int(round(25 * self.ui_scale)))
        self.arrow_start_x = max(10, int(round(20 * self.ui_scale)))
        self.arrow_tip_dx = max(6, int(round(10 * self.ui_scale)))
        self.arrow_end_dx = max(8, int(round(15 * self.ui_scale)))

        self.adjustSize()
        self.update()
        return True

    def _resolve_menu_center(self):
        if self.target is None:
            return None

        actions = getattr(self.target, "maid_actions", None)
        if actions is not None and hasattr(actions, "_get_circular_menu_center_point"):
            try:
                return actions._get_circular_menu_center_point()
            except Exception:
                pass

        return self.target.frameGeometry().center()

    def _sync_with_target(self, force=False):
        ui_scale = self._resolve_ui_scale()
        style_changed = self._apply_scaled_style(ui_scale, force=force)

        new_radius = self._compute_menu_radius(self.ui_scale)
        if force or style_changed or new_radius != self.menu_radius:
            self.menu_radius = new_radius

        self.update_position()

    def update_position(self):
        if self.target:
            anchor_point = self._resolve_menu_center()
            if anchor_point is None:
                return

            screen_geo = QApplication.primaryScreen().availableGeometry()

            # 跟随菜单缩放半径外扩，使气泡与菜单选项保持同向联动
            x = anchor_point.x() + int(round(self.menu_radius * 0.45))
            y = anchor_point.y() - self.height() - int(round(self.menu_radius * 0.15))
            
            # 边界检测
            if x + self.width() > screen_geo.right():
                x = anchor_point.x() - self.width() - int(round(self.menu_radius * 0.45))
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
        arrow_height = self.arrow_height # 底部箭头区域的高度
        
        # 气泡主体区域
        rect = QRectF(0, 0, width, height - arrow_height)
        
        path = QPainterPath()
        path.addRoundedRect(rect, self.corner_radius, self.corner_radius) # 增加圆角半径使其更加圆润
        
        # 绘制小尾巴 (指向左下角)
        # 箭头起点 (在矩形底部边框上)
        arrow_start_x = self.arrow_start_x
        path.moveTo(arrow_start_x, height - arrow_height)
        
        # 箭头尖端
        path.lineTo(arrow_start_x - self.arrow_tip_dx, height)
        
        # 箭头终点 (在矩形底部边框上)
        path.lineTo(arrow_start_x + self.arrow_end_dx, height - arrow_height)
        
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

    def hide_dialogue(self):
        if self.current_bubble:
            try:
                self.current_bubble.close()
                self.current_bubble = None
            except:
                pass

