import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QApplication, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath

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
        
        text = self.text()
        rect = self.contentsRect()
        font = self.font()
        
        path = QPainterPath()
        fm = painter.fontMetrics()
        text_rect = fm.boundingRect(text)
        
        alignment = self.alignment()
        if alignment & Qt.AlignmentFlag.AlignCenter:
            x = rect.x() + (rect.width() - text_rect.width()) / 2.0
        elif alignment & Qt.AlignmentFlag.AlignRight:
            x = rect.x() + rect.width() - text_rect.width()
        else:
            x = rect.x()
            
        y = rect.y() + (rect.height() - fm.height()) / 2.0 + fm.ascent()
        
        path.addText(QPointF(x, y), font, text)
        
        # Draw stroke
        pen = QPen(QColor("black"))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawPath(path)
        
        # Draw fill
        painter.fillPath(path, QColor("white"))

class OutlineButton(QPushButton):
    def __init__(self, text, enable_outline=True, parent=None, **kwargs):
        super().__init__(text, parent, **kwargs)
        self.enable_outline = enable_outline
        
    def paintEvent(self, event):
        # 让父类先绘制背景 (包括 border-image 等)
        super().paintEvent(event)
        
        if not self.enable_outline:
            return
            
        # 自己再画一层描边文字
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        text = self.text()
        rect = self.rect()
        
        # 必须和 StyleSheet 中的字体设置保持一致
        font = self.font()
        
        path = QPainterPath()
        
        # 为了计算文字居中位置，我们需要获取字体的尺寸信息
        fm = painter.fontMetrics()
        text_rect = fm.boundingRect(text)
        
        # 将起点移动到中心
        x = (rect.width() - text_rect.width()) / 2.0
        y = (rect.height() + fm.ascent() - fm.descent()) / 2.0
        
        path.addText(QPointF(x, y), font, text)
        
        # 绘制黑色的粗边框（描边）
        pen = QPen(QColor("black"))
        pen.setWidth(3)  # 设置边框粗细为3像素，非常明显
        painter.setPen(pen)
        painter.drawPath(path)
        
        # 填充白色的实体文字
        painter.fillPath(path, QColor("white"))
        
        # 我们不再直接调用 drawText，全靠 PainterPath 画出描边效果

def load_dialog_theme():
    """解析简单的 YAML 文件读取对话框图片路径"""
    config_path = os.path.join(os.path.dirname(__file__), "dialog_style.yaml")
    theme = {}
    if not os.path.exists(config_path):
        return theme
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if ":" in stripped:
                    key, val = stripped.split(":", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if val:
                        theme[key] = val
    except Exception as e:
        print(f"读取 dialog_style.yaml 失败: {e}")
    return theme

class CustomChoiceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.choice = "none"

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setFixedSize(300, 150) # 可以根据你的素材长宽进行修改
        
        # 加载配置和根目录
        self.theme = load_dialog_theme()
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

        # 解析背景图
        bg_path = self.theme.get("background", "")
        if bg_path and not os.path.isabs(bg_path):
            bg_path = os.path.join(root_dir, bg_path)
            
        self.bg_label = QLabel(self)
        self.bg_label.setFixedSize(300, 150)
        
        # 如果背景图有效则应用，否则使用默认样式
        if bg_path and os.path.exists(bg_path):
            # 将反斜杠替换为正斜杠，防止 CSS 解析报错
            bg_url = bg_path.replace("\\", "/")
            self.bg_label.setStyleSheet(f"""
                QLabel {{
                    background-image: url("{bg_url}");
                    background-repeat: no-repeat;
                    background-position: left top;
                }}
            """)
            # 如果配置了图片，我们把默认提示文字设黑/隐藏
            text_color = "#333" 
        else:
            self.bg_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(250, 250, 250, 220);
                    border: 2px solid #ff3b30;
                    border-radius: 15px;
                }
            """)
            text_color = "#333"

        # 给文字和按钮建个布局层
        layout = QVBoxLayout(self.bg_label)
        layout.setContentsMargins(20, 20, 20, 20)

        # 读取黑边配置
        self.outline_button_text = str(self.theme.get("outline_button_text", "true")).lower() == "true"
        lbl_col = "transparent" if self.outline_button_text else text_color

        # 提示文字
        self.info_label = OutlineLabel("请选择截图要保存的位置：", enable_outline=self.outline_button_text)
        self.info_label.setStyleSheet(f"font-size: 14px; text-align: center; color: {lbl_col}; border: none; background: transparent;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)

        # 按钮横向布局
        btn_layout = QHBoxLayout()
        
        def create_button(text, key_prefix):
            btn = OutlineButton(text, enable_outline=self.outline_button_text)
            # 在 yaml 中留空表示退回默认大小，如果用图可以改这里
            btn.setFixedSize(70, 30) 
            
            n_path = self.theme.get(f"{key_prefix}_normal", "")
            h_path = self.theme.get(f"{key_prefix}_hover", "")
            p_path = self.theme.get(f"{key_prefix}_pressed", "")

            # 回退策略：未配置独立按钮贴图时，优先复用圆形菜单按钮贴图
            # 不保存按钮使用 quit 图，其余使用 select 图。
            fallback_key = "circular_btn_quit" if key_prefix == "btn_cancel" else "circular_btn_select"
            fallback_path = self.theme.get(fallback_key, "")
            if not n_path and fallback_path:
                n_path = fallback_path
            if not h_path and fallback_path:
                h_path = fallback_path
            if not p_path and fallback_path:
                p_path = fallback_path
            
            valid_paths = {}
            for state, p in [("normal", n_path), ("hover", h_path), ("pressed", p_path)]:
                if p:
                    p = os.path.normpath(p.replace("\\", "/"))
                    if not os.path.isabs(p):
                        p = os.path.join(root_dir, p)
                    p = os.path.normpath(p)
                    if os.path.exists(p):
                        valid_paths[state] = p.replace("\\", "/")
                        
            # 如果提供了有效的 normal 状态图片，则应用图片样式
            if "normal" in valid_paths:
                bg_normal = f"border-image: url('{valid_paths['normal']}');"
                # 如果没提供 hover/pressed 状态，默认沿用 normal 的图
                bg_hover = f"border-image: url('{valid_paths.get('hover', valid_paths['normal'])}');"
                bg_pressed = f"border-image: url('{valid_paths.get('pressed', valid_paths['normal'])}');"
                
                txt_col = "transparent" if self.outline_button_text else "white"
                
                # 如果用图，改为显示白色文字，并通过自定义 paintEvent 模拟黑边
                btn.setStyleSheet(f"""
                    OutlineButton {{
                        {bg_normal}
                        background: transparent;
                        color: {txt_col}; /* 为了让父类不要画字，由我们的 paintEvent 画 */
                        font-weight: bold;
                        font-size: 14px;
                    }}
                    OutlineButton:hover {{ {bg_hover} }}
                    OutlineButton:pressed {{ {bg_pressed} }}
                """)
            else:
                txt_col_def = "transparent" if self.outline_button_text else "white"
                # 默认苹果红样式
                btn.setStyleSheet(f"""
                    OutlineButton {{
                        background-color: #ff3b30;
                        color: {txt_col_def}; /* 为了一致，这里也隐藏原字 */
                        border-radius: 10px;
                        padding: 5px;
                        font-weight: bold;
                    }}
                    OutlineButton:hover {{ background-color: #ff5a51; }}
                    OutlineButton:pressed {{ background-color: #d32f27; }}
                """)
            return btn

        btn_desktop = create_button("桌面", "btn_desktop")
        btn_desktop.clicked.connect(self.on_desktop)

        btn_default = create_button("默认", "btn_default")
        btn_default.clicked.connect(self.on_default)

        btn_cancel = create_button("不保存", "btn_cancel")
        btn_cancel.clicked.connect(self.on_cancel)

        btn_layout.addWidget(btn_desktop)
        btn_layout.addWidget(btn_default)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def showEvent(self, event):
        super().showEvent(event)
        
        # 边界检测，防止超出屏幕
        screen_geo = QApplication.primaryScreen().availableGeometry()
        geo = self.frameGeometry()
        x, y = geo.x(), geo.y()
        
        if x + geo.width() > screen_geo.right():
            x = screen_geo.right() - geo.width()
        if x < screen_geo.left():
            x = screen_geo.left()
            
        if y + geo.height() > screen_geo.bottom():
            y = screen_geo.bottom() - geo.height()
        if y < screen_geo.top():
            y = screen_geo.top()
            
        self.move(int(x), int(y))

    def on_desktop(self):
        self.choice = "desktop"
        self.accept()

    def on_default(self):
        self.choice = "default"
        self.accept()

    def on_cancel(self):
        self.choice = "none"
        self.reject()

def ask_save_location(parent):
    """
    询问用户截图保存位置
    Returns:
        str: 'desktop', 'default', 'none'
    """
    dialog = CustomChoiceDialog(parent)
    dialog.exec()
    return dialog.choice
