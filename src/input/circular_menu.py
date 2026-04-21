import math
import os
from PyQt6.QtWidgets import QWidget, QPushButton, QApplication
from PyQt6.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QPoint, QTimer, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath

from .choice_dialog import load_dialog_theme

class BubbleButton(QPushButton):
    def __init__(self, text, is_back=False, icon_path=None, ui_scale=1.0, text_color="white", parent=None):
        super().__init__(text, parent)
        self.image_mode = False
        self.text_color = text_color or "white"
        # 按菜单缩放比例缩放按钮，缩小时下限为 0.4
        self.ui_scale = max(0.4, float(ui_scale))
        self.default_size = max(28, int(70 * self.ui_scale))
        self.image_size = max(32, int(80 * self.ui_scale))
        self.text_hover_size = max(self.default_size, int(self.default_size * 1.08))
        self.image_hover_size = max(self.image_size, int(self.image_size * 1.05))
        self.setFixedSize(self.default_size, self.default_size)
        
        # 加载描边配置
        theme = load_dialog_theme()
        self.enable_outline = str(theme.get("outline_button_text", "true")).lower() == "true"

        if icon_path and os.path.exists(icon_path):
            self.image_mode = True
            self.setFixedSize(self.image_size, self.image_size)
            bg_url = icon_path.replace("\\", "/")
            display_color = "transparent" if self.enable_outline else self.text_color
            font_px = max(7, int(15 * self.ui_scale))
            self.setStyleSheet(f"""
                QPushButton {{
                    border-image: url('{bg_url}');
                    border: none;
                    color: {display_color};
                    font-weight: bold;
                    font-size: {font_px}px;
                }}
            """)
            return

        if is_back:
            bg_color = "#cfcecd"
            border_color = "#c41c1c"
            hover_bg = "#8f8f8e"
            pressed_bg = "#444444"
        else:
            bg_color = "#c41c1c"
            border_color = "black"
            hover_bg = "#e32424"
            pressed_bg = "#a81616"

        radius_px = max(8, self.default_size // 2)
        border_px = max(2, int(4 * self.ui_scale))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {self.text_color};
                border-radius: {radius_px}px;
                font-weight: bold;
                border: {border_px}px solid {border_color};
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
            }}
        """)

    def hitButton(self, pos):
        # 根据当前按钮尺寸动态判定点击区域，避免缩放后命中范围不准确
        cx = self.width() / 2
        cy = self.height() / 2
        dx = pos.x() - cx
        dy = pos.y() - cy

        hit_r = min(self.width(), self.height()) / 2
        return (dx * dx + dy * dy) <= (hit_r * hit_r)

    def set_target_pos(self, x, y, angle):
        self.base_x = x
        self.base_y = y
        self.angle = angle

    def enterEvent(self, event):
        if self.parent() and hasattr(self.parent(), 'inactivity_timer'):
            auto_close_enabled = bool(getattr(self.parent(), 'auto_close_enabled', True))
            if auto_close_enabled:
                self.parent().inactivity_timer.start(15000)
        super().enterEvent(event)
        self.raise_()
        if hasattr(self, 'base_x') and hasattr(self, 'base_y') and hasattr(self, 'angle'):
            shift_dist = max(2, int((5 if self.image_mode else 10) * self.ui_scale))
            hover_x = self.base_x + shift_dist * math.cos(self.angle)
            hover_y = self.base_y - shift_dist * math.sin(self.angle)

            target_w = self.image_hover_size if self.image_mode else self.text_hover_size
            target_h = target_w

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
                self.hover_anim.setEndValue(QRect(int(hover_x), int(hover_y), target_w, target_h))
                self.hover_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
                self.hover_anim.start(QPropertyAnimation.DeletionPolicy.KeepWhenStopped)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if hasattr(self, 'base_x') and hasattr(self, 'base_y'):
            target_w = self.image_size if self.image_mode else self.default_size
            target_h = target_w

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
                self.leave_anim.setEndValue(QRect(int(self.base_x), int(self.base_y), target_w, target_h))
                self.leave_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
                self.leave_anim.start(QPropertyAnimation.DeletionPolicy.KeepWhenStopped)

    def paintEvent(self, event):
        super().paintEvent(event)
        
        if getattr(self, "image_mode", False) and getattr(self, "enable_outline", False):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            text = self.text()
            rect = self.rect()
            font = self.font()
            
            path = QPainterPath()
            fm = painter.fontMetrics()
            lines = text.splitlines() if text else [""]
            if not lines:
                lines = [""]
            
            # 由于之前有 padding-top: 50px，我们把文字依然画到底部中间位置
            # 高度是 80，底部的空间大约是从 45 到 80。
            padding_top = max(20, int(45 * self.ui_scale))
            area_height = rect.height() - padding_top

            line_height = fm.height()
            total_height = line_height * len(lines)
            start_y = padding_top + (area_height - total_height) / 2.0 + fm.ascent()

            for idx, line in enumerate(lines):
                line_width = fm.horizontalAdvance(line)
                x = (rect.width() - line_width) / 2.0
                y = start_y + idx * line_height
                path.addText(QPointF(x, y), font, line)
            
            pen = QPen(QColor("black"))
            pen.setWidth(max(1, int(3 * self.ui_scale)))
            painter.setPen(pen)
            painter.drawPath(path)
            
            painter.fillPath(path, QColor(self.text_color))

class CircularMenuWidget(QWidget):
    def __init__(self, items, center_pos, on_close_callback=None, menu_scale=1.0, parent=None):
        """
        items: list of dicts. [{'label': 'name', 'action': callable or sub_items_list}]
        """
        super().__init__(None) # Independent window
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        self.center_pos = center_pos
        self.on_close_callback = on_close_callback
        # 菜单可随桌宠缩小，最小 0.4
        self.menu_scale = max(0.4, float(menu_scale))
        self.maid_widget = parent
        self._sync_overlay_geometry()

        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        self.theme = load_dialog_theme()
        self.use_image_buttons = self.theme.get("circular_button_mode", "default").lower() == "image"
        self.select_btn_path = self._resolve_theme_path(self.theme.get("circular_btn_select", ""))
        self.quit_btn_path = self._resolve_theme_path(self.theme.get("circular_btn_quit", ""))
        
        self.history = [] # Stack of (items, page_idx)
        self.suppress_auto_back = False
        self.current_items = items
        self.current_page = 0
        self.buttons = []
        self._force_close = False
        
        # 15秒无操作自动关闭
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.setSingleShot(True)
        self.inactivity_timer.timeout.connect(self.close_menu)
        self.auto_close_enabled = True
        self.inactivity_timer.start(15000)
        
        self._build_menu()

    def _resolve_screen_geometry_for_point(self, global_point):
        screen = QApplication.screenAt(global_point)
        if screen is None and self.maid_widget is not None:
            screen = self.maid_widget.screen()
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return QRect(0, 0, 1, 1)
        return screen.availableGeometry()

    def _sync_overlay_geometry(self):
        target_geo = self._resolve_screen_geometry_for_point(self.center_pos)
        if self.geometry() != target_geo:
            self.setGeometry(target_geo)

    def _center_pos_local(self):
        geo = self.geometry()
        return QPoint(self.center_pos.x() - geo.x(), self.center_pos.y() - geo.y())

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

    def sync_menu_scale_from_maid(self):
        if self.maid_widget is None:
            return False

        new_scale = self._menu_scale_from_maid_scale(getattr(self.maid_widget, 'user_scale', 1.0))
        actions = getattr(self.maid_widget, 'maid_actions', None)
        if actions is not None and hasattr(actions, '_get_circular_menu_center_point'):
            new_center = actions._get_circular_menu_center_point()
        else:
            new_center = self.maid_widget.mapToGlobal(self.maid_widget.rect().center())

        scale_unchanged = abs(new_scale - self.menu_scale) <= 1e-6
        center_unchanged = (new_center == self.center_pos)
        if scale_unchanged and center_unchanged:
            return False

        self.menu_scale = new_scale
        self.center_pos = new_center
        self._sync_overlay_geometry()
        self._build_menu()
        return True

    def set_auto_close_enabled(self, enabled):
        self.auto_close_enabled = bool(enabled)
        if self.auto_close_enabled:
            self.inactivity_timer.start(15000)
        else:
            self.inactivity_timer.stop()

    def _is_preview_adjusting(self):
        return self.maid_widget is not None and getattr(self.maid_widget, '_custom_scale_adjusting', False)

    def _resolve_theme_path(self, path_val):
        if not path_val:
            return None
        path_val = path_val.strip().strip("'\"")
        if not path_val:
            return None
        # Accept both Windows and POSIX separators from YAML config.
        path_val = os.path.normpath(path_val.replace("\\", "/"))
        if not os.path.isabs(path_val):
            path_val = os.path.join(self.root_dir, path_val)
        path_val = os.path.normpath(path_val)
        return path_val if os.path.exists(path_val) else None
        
    def _build_menu(self):
        # Clear old buttons
        for btn in self.buttons:
            btn.deleteLater()
        self.buttons.clear()
        
        btn_half = max(14, int((80 if self.use_image_buttons else 70) * self.menu_scale / 2))
        base_r = max(48, int(120 * self.menu_scale))
        
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
        if self.history and not self.suppress_auto_back:
            display_items.append({'label': '返回', 'action': 'back'})
            
        display_items.extend(page_items)
        if exit_item:
            display_items.append(exit_item)
            
        n = len(display_items)
        if n == 1:
            angles = [math.pi / 2]
            R = base_r
        else:
            # 始终保持 180 度扇形，并根据可用空间自动选择朝向与半径。
            screen_geo = self.geometry()
            top_space = self.center_pos.y() - screen_geo.top()
            bottom_space = screen_geo.bottom() - self.center_pos.y()
            left_space = self.center_pos.x() - screen_geo.left()
            right_space = screen_geo.right() - self.center_pos.x()

            # 每个方向都保持 180°，只改变起始角与方向。
            # format: (start_angle, sweep_angle, radial_space, tangent_a, tangent_b)
            orientations = [
                (math.pi, -math.pi, top_space, left_space, right_space),          # 上半圆
                (math.pi, math.pi, bottom_space, left_space, right_space),         # 下半圆
                (math.pi / 2, -math.pi, right_space, top_space, bottom_space),     # 右半圆
                (math.pi / 2, math.pi, left_space, top_space, bottom_space),       # 左半圆
            ]

            margin = btn_half + 10

            def usable_radius(orientation):
                _, _, radial, tangential_a, tangential_b = orientation
                return min(radial, tangential_a, tangential_b) - margin

            # 先选可完整容纳 base_r 的方向；若都不满足，退化到可用半径最大的方向。
            fit_candidates = [o for o in orientations if usable_radius(o) >= base_r]
            if fit_candidates:
                chosen = max(fit_candidates, key=usable_radius)
                R = base_r
            else:
                chosen = max(orientations, key=usable_radius)
                R = max(24, int(usable_radius(chosen)))

            start_angle, sweep_angle, *_ = chosen
            angles = [start_angle + i * (sweep_angle / (n - 1)) for i in range(n)]

        local_center = self._center_pos_local()
            
        for i, item in enumerate(display_items):
            is_special_btn = (item['label'] in ['返回', '退出', '<', '>'])
            text_color = item.get('text_color', 'white')
            icon_path = None
            if self.use_image_buttons:
                if is_special_btn:
                    icon_path = self.quit_btn_path
                else:
                    icon_path = self.select_btn_path

            btn = BubbleButton(
                item['label'],
                is_back=is_special_btn,
                icon_path=icon_path,
                ui_scale=self.menu_scale,
                text_color=text_color,
                parent=self
            )
            
            # Target position
            tar_x = local_center.x() + R * math.cos(angles[i]) - btn.width() / 2
            tar_y = local_center.y() - R * math.sin(angles[i]) - btn.height() / 2
            
            # Start position (center)
            start_x = local_center.x() - btn.width() / 2
            start_y = local_center.y() - btn.height() / 2
            
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
            
            def make_callback(item_meta):
                def cb():
                    action_val = item_meta.get('action')
                    close_before_action = bool(item_meta.get('close_before_action', True))
                    close_after_action = bool(item_meta.get('close_after_action', True))
                    if action_val == 'back':
                        if not self.history:
                            return
                        self.current_items, self.current_page, self.suppress_auto_back = self.history.pop()
                        self._build_menu()
                    elif action_val == 'next_page':
                        self.current_page += 1
                        self._build_menu()
                    elif action_val == 'prev_page':
                        self.current_page -= 1
                        self._build_menu()
                    elif isinstance(action_val, list):
                        # Enter sub-menu
                        on_enter = item_meta.get('on_enter')
                        if callable(on_enter):
                            on_enter()
                        self.history.append((self.current_items, self.current_page, self.suppress_auto_back))
                        self.current_items = action_val
                        self.current_page = 0
                        self.suppress_auto_back = bool(item_meta.get('suppress_back', False))
                        self._build_menu()
                    elif callable(action_val):
                        # Execute with configurable close timing
                        if close_before_action:
                            self.close_menu()
                            action_val()
                        else:
                            action_val()
                            if close_after_action:
                                self.close_menu()
                return cb
                
            btn.clicked.connect(make_callback(item))
            btn.show()
            self.buttons.append(btn)
            
    def mousePressEvent(self, event):
        if self.maid_widget is not None and getattr(self.maid_widget, '_custom_scale_adjusting', False):
            event.accept()
            return
        # Click outside closes the menu
        self.close_menu()
        
    def mouseMoveEvent(self, event):
        if self.auto_close_enabled:
            self.inactivity_timer.start(15000)
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        if self.maid_widget is not None and hasattr(self.maid_widget, 'adjust_scale_by_wheel_delta'):
            global_pos = self.mapToGlobal(event.position().toPoint())
            local_pos = self.maid_widget.mapFromGlobal(global_pos)
            if self.maid_widget.rect().contains(local_pos):
                if self.maid_widget.adjust_scale_by_wheel_delta(event.angleDelta().y()):
                    if getattr(self.maid_widget, '_custom_scale_adjusting', False):
                        self.sync_menu_scale_from_maid()
                    if self.auto_close_enabled:
                        self.inactivity_timer.start(15000)
                    event.accept()
                    return
        super().wheelEvent(event)
        
    def closeEvent(self, event):
        app = QApplication.instance()
        app_closing = bool(app.closingDown()) if app is not None else False
        if self._is_preview_adjusting() and not self._force_close and not app_closing:
            event.ignore()
            return
        super().closeEvent(event)

    def close_menu(self, force=False):
        if self._is_preview_adjusting() and not force:
            return
        if self.on_close_callback:
            self.on_close_callback()
        self._force_close = True
        self.close()
        self._force_close = False

