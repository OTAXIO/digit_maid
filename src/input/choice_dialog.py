import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt

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

        # 提示文字
        self.info_label = QLabel("请选择截图要保存的位置：")
        self.info_label.setStyleSheet(f"font-size: 14px; color: {text_color}; border: none; background: transparent;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)

        # 按钮横向布局
        btn_layout = QHBoxLayout()
        
        def create_button(text, key_prefix):
            btn = QPushButton(text)
            # 在 yaml 中留空表示退回默认大小，如果用图可以改这里
            btn.setFixedSize(70, 30) 
            
            n_path = self.theme.get(f"{key_prefix}_normal", "")
            h_path = self.theme.get(f"{key_prefix}_hover", "")
            p_path = self.theme.get(f"{key_prefix}_pressed", "")
            
            valid_paths = {}
            for state, p in [("normal", n_path), ("hover", h_path), ("pressed", p_path)]:
                if p:
                    if not os.path.isabs(p):
                        p = os.path.join(root_dir, p)
                    if os.path.exists(p):
                        valid_paths[state] = p.replace("\\", "/")
                        
            # 如果提供了有效的 normal 状态图片，则应用图片样式
            if "normal" in valid_paths:
                bg_normal = f"border-image: url('{valid_paths['normal']}');"
                # 如果没提供 hover/pressed 状态，默认沿用 normal 的图
                bg_hover = f"border-image: url('{valid_paths.get('hover', valid_paths['normal'])}');"
                bg_pressed = f"border-image: url('{valid_paths.get('pressed', valid_paths['normal'])}');"
                
                # 如果用图就让默认的字变透明隐藏 (如果图自带字了) 或者让它继续显示
                btn.setStyleSheet(f"""
                    QPushButton {{
                        {bg_normal}
                        background: transparent;
                        color: transparent; 
                    }}
                    QPushButton:hover {{ {bg_hover} }}
                    QPushButton:pressed {{ {bg_pressed} }}
                """)
            else:
                # 默认苹果红样式
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ff3b30;
                        color: white;
                        border-radius: 10px;
                        padding: 5px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #ff5a51; }
                    QPushButton:pressed { background-color: #d32f27; }
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
