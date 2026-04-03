import os

from PyQt6.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QMovie
import sys

# 导入分离后的UI模块
from .dialogue import DialogueSystem
from .action import PetActions

class PetWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        self.initUI()
        self.offset = QPoint()
        
        # 资源目录
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        self.root_dir = root_dir
        self.current_action = "idle"
        
        # 初始化各个子系统
        self.dialogue_system = DialogueSystem(self)
        self.pet_actions = PetActions(self, self.dialogue_system)

        # GIF 显示层
        self.pet_label = QLabel(self)
        self.pet_label.setStyleSheet("background: transparent;")
        self.pet_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pet_label)

        # 动作配置
        self.anim_cfg = self._load_animation_config()
        self.current_movie = None
        self.current_loop = True

        # 空闲状态机：30秒无交互进入 sit，再30秒无交互进入 sleep
        self.inactivity_stage = 0
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.setSingleShot(True)
        self.inactivity_timer.timeout.connect(self._on_inactivity_timeout)

        self.play_action("idle")
        self._reset_inactivity_timer()

    def initUI(self):
        # ... (保持不变)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 获取屏幕尺寸
        screen = QApplication.primaryScreen().availableGeometry()
        pet_width = 170
        pet_height = 170
        
        # 计算右下角位置 (减去一点边距)
        x = screen.width() - pet_width - 100 
        y = screen.height() - pet_height - 100
        
        self.setGeometry(x, y, pet_width, pet_height)
        self.setWindowTitle('DigitMaid')

    def _load_animation_config(self):
        cfg_path = os.path.join(os.path.dirname(__file__), "pet_animations.yaml")
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                lines = [line.rstrip("\n") for line in f]

            cfg = {
                "base_dir": "resource/wisdel/可用素材",
                "actions": {},
                "loops": {},
                # 向后兼容旧结构 animations: {action: {file, loop}}
                "animations": {},
            }
            current_action = None
            current_section = None

            for raw in lines:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue

                if raw.startswith("base_dir:"):
                    cfg["base_dir"] = raw.split(":", 1)[1].strip()
                    continue

                if line in ("actions:", "loops:", "animations:"):
                    current_section = line[:-1]
                    continue

                if not current_section:
                    continue

                # 新结构 actions/loops: "  key: value"
                if current_section in ("actions", "loops") and raw.startswith("  ") and ":" in line:
                    k, v = line.split(":", 1)
                    key = k.strip()
                    value = v.strip()
                    if current_section == "actions":
                        cfg["actions"][key] = value
                    else:
                        cfg["loops"][key] = (value.lower() == "true")
                    continue

                # 旧结构 animations:
                # action key, e.g. "  idle:"
                if current_section == "animations" and raw.startswith("  ") and raw.endswith(":") and not raw.startswith("    "):
                    current_action = line[:-1]
                    cfg["animations"][current_action] = {}
                    continue

                if current_section == "animations" and current_action and raw.startswith("    "):
                    if line.startswith("file:"):
                        cfg["animations"][current_action]["file"] = line.split(":", 1)[1].strip()
                    elif line.startswith("loop:"):
                        v = line.split(":", 1)[1].strip().lower()
                        cfg["animations"][current_action]["loop"] = (v == "true")

            return cfg
        except Exception as e:
            print(f"读取动作配置失败: {e}")
            return {}

    def play_action(self, action_name):
        base_dir_rel = self.anim_cfg.get("base_dir", "resource/wisdel/可用素材")
        actions = self.anim_cfg.get("actions", {})
        loops = self.anim_cfg.get("loops", {})

        # 优先使用新结构；如果没有则回退旧结构
        gif_file = actions.get(action_name) or actions.get("idle")
        loop_value = loops.get(action_name, loops.get("idle", True))

        if not gif_file:
            animations = self.anim_cfg.get("animations", {})
            action_cfg = animations.get(action_name) or animations.get("idle")
            if not action_cfg:
                return
            gif_file = action_cfg.get("file", "")
            loop_value = action_cfg.get("loop", True)

        if not gif_file:
            return

        gif_path = os.path.join(self.root_dir, base_dir_rel, gif_file)
        if not os.path.exists(gif_path):
            print(f"动作素材不存在: {gif_path}")
            return

        if self.current_movie is not None:
            self.current_movie.stop()

        movie = QMovie(gif_path)
        self.current_loop = loop_value
        movie.finished.connect(self._on_action_finished)

        self.current_action = action_name
        self.current_movie = movie
        self.pet_label.setMovie(movie)
        movie.start()

    def _on_action_finished(self):
        if self.current_loop:
            # 循环动作：重头继续播放
            if self.current_movie is not None:
                self.current_movie.start()
        else:
            # 非循环动作结束后回到 idle
            self.play_action("idle")

    def _reset_inactivity_timer(self):
        self.inactivity_stage = 0
        self.inactivity_timer.start(30000)

    def _on_inactivity_timeout(self):
        if self.inactivity_stage == 0:
            self.play_action("sit")
            self.inactivity_stage = 1
            self.inactivity_timer.start(30000)
        elif self.inactivity_stage == 1:
            self.play_action("sleep")
            self.inactivity_stage = 2

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            # 一旦被点击，立即回到 idle
            self.play_action("idle")
            self._reset_inactivity_timer()
            
        elif event.button() == Qt.MouseButton.RightButton:
            # 右键点击也视为交互，回到 idle
            self.play_action("idle")
            self._reset_inactivity_timer()
            # 委托 action 模块处理右键菜单
            self.pet_actions.show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            if self.current_action != "move":
                self.play_action("move")
            self._reset_inactivity_timer()
            self.move(event.globalPosition().toPoint() - self.offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.play_action("idle")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    pet = PetWindow()
    pet.show()
    sys.exit(app.exec())
