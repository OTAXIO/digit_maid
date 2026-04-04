import os
import time
import random

from PyQt6.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, QTimer, QSize
from PyQt6.QtGui import QMovie, QTransform
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
        self.pet_label.setScaledContents(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.pet_label)

        # 动作配置
        self.anim_cfg = self._load_animation_config()
        self.current_movie = None
        self.current_loop = True
        self.menu_interact_mode = False
        self.special_origin_pos = None

        # 空闲状态机：15秒无交互进入 sit，再15秒无交互进入 sleep
        self.inactivity_stage = 0
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.setSingleShot(True)
        self.inactivity_timer.timeout.connect(self._on_inactivity_timeout)

        # 闲置散步计时器
        self.wander_timer = QTimer(self)
        self.wander_timer.timeout.connect(self._on_wander_tick)
        self.wander_speed = 0

        self.play_action("idle")
        self._reset_inactivity_timer()

    def initUI(self):
        # ... (保持不变)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 获取屏幕尺寸
        screen = QApplication.primaryScreen().availableGeometry()
        pet_width = 85
        pet_height = 85
        
        # 计算左下角位置 (加上一点边距)
        x = screen.left() + 100 
        y = screen.bottom() - pet_height
        
        self.setGeometry(x, y, pet_width, pet_height)
        self.setWindowTitle('DigitMaid')

    def _load_animation_config(self):
        cfg_path = os.path.join(os.path.dirname(__file__), "pet_animations.yaml")
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                lines = [line.rstrip("\n") for line in f]

            cfg = {
                "base_dir": "resource/wisdel/皮肤素材/可用素材",
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

    def play_action(self, action_name, force_loop=None, is_flipped=None):
        # 只要切换动作，就先暂停待机计时；如果是回到 idle，再重新开始计时
        if hasattr(self, 'inactivity_timer'):
            self.inactivity_timer.stop()
            self.inactivity_stage = 0

        base_dir_rel = self.anim_cfg.get("base_dir", "resource/wisdel/皮肤素材/可用素材")
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

        # 新增：允许在 yaml 里用逗号分隔配置多个动作，并在播放时随机抽取其中一个
        if isinstance(gif_file, str) and "," in gif_file:
            gif_file = random.choice([f.strip() for f in gif_file.split(",")])

        gif_path = os.path.join(self.root_dir, base_dir_rel, gif_file)
        if not os.path.exists(gif_path):
            print(f"动作素材不存在: {gif_path}")
            return

        if self.current_movie is not None:
            self.current_movie.stop()

        movie = QMovie(gif_path)
        movie.jumpToFrame(0)

        # 获取 GIF 原始像素，缩放一倍显示
        frame_size = movie.currentImage().size()
        if not frame_size.isEmpty():
            current_pos = self.pos()
            screen_geo = self.screen().availableGeometry()
            
            target_width = frame_size.width() // 2
            target_height = frame_size.height() // 2
            
            # 尝试保持当前左上角，但如果右下角超出屏幕则向左/向上挤
            new_x = current_pos.x()
            new_y = current_pos.y()
            if new_x + target_width > screen_geo.right():
                new_x = screen_geo.right() - target_width
            if new_y + target_height > screen_geo.bottom():
                new_y = screen_geo.bottom() - target_height
                
            # 兜底保证左上角不越界
            new_x = max(screen_geo.left(), new_x)
            new_y = max(screen_geo.top(), new_y)
            
            movie.setScaledSize(QSize(target_width, target_height))
            self.pet_label.setFixedSize(target_width, target_height)
            self.setGeometry(new_x, new_y, target_width, target_height)
        if force_loop is None:
            self.current_loop = loop_value
        else:
            self.current_loop = force_loop

        # 使用 frameChanged 来手动控制播放结束（特别是带有内部无限循环的GIF）
        movie.frameChanged.connect(self._on_frame_changed)
        
        self.current_action = action_name
        self.current_movie = movie
        if is_flipped is not None:
            self.is_flipped = is_flipped
        else:
            self.is_flipped = getattr(self, "is_flipped", False)
        
        if not self.is_flipped:
            self.pet_label.setMovie(movie)
            
        movie.start()
        
        if self.is_flipped:
            # 手动提取第一帧进行翻转并上屏
            pixmap = movie.currentPixmap()
            if not pixmap.isNull():
                transform = QTransform().scale(-1, 1)
                self.pet_label.setPixmap(pixmap.transformed(transform))
        
        # 只有在 idle 状态下才允许计时器流动
        if action_name == "idle" and hasattr(self, 'inactivity_timer'):
            self._reset_inactivity_timer()

    def _on_frame_changed(self, frame_number):
        if self.current_movie is None:
            return
            
        # 如果需要左右翻转，每帧渲染时手动更新 QLabel
        if getattr(self, "is_flipped", False):
            pixmap = self.current_movie.currentPixmap()
            if not pixmap.isNull():
                transform = QTransform().scale(-1, 1)
                self.pet_label.setPixmap(pixmap.transformed(transform))
                
        # 检查是否到达最后一帧
        if frame_number >= self.current_movie.frameCount() - 1:
            if not self.current_loop:
                self.current_movie.stop()
                self._on_action_finished()

    def _on_action_finished(self):
        if self.current_loop:
            # 循环动作：重头继续播放
            if self.current_movie is not None:
                self.current_movie.start()
        else:
            # 非循环动作结束后回到 idle，play_action 内部会自动接管并重新启动计时器
            self.play_action("idle")

    def _on_wander_tick(self):
        if self.current_action != "move" or self.inactivity_stage != 1:
            self.wander_timer.stop()
            return

        new_x = self.x() + self.wander_speed
        screen_geo = self.screen().availableGeometry()
        
        start_x = getattr(self, 'wander_start_x', self.x())
        
        # 碰到屏幕边缘或者超出50像素则转身
        if new_x < screen_geo.left() or new_x < start_x - 100:
            new_x = max(screen_geo.left(), start_x - 100)
            self.wander_speed *= -1
            self.is_flipped = False
            if self.current_movie:
                self.pet_label.setMovie(self.current_movie)
        elif new_x + self.width() > screen_geo.right() or new_x > start_x + 100:
            new_x = min(screen_geo.right() - self.width(), start_x + 100)
            self.wander_speed *= -1
            self.is_flipped = True
            if self.current_movie:
                pixmap = self.current_movie.currentPixmap()
                if not pixmap.isNull():
                    transform = QTransform().scale(-1, 1)
                    self.pet_label.setPixmap(pixmap.transformed(transform))
            
        self.move(new_x, self.y())

    def _reset_inactivity_timer(self):
        self.inactivity_stage = 0
        self.inactivity_timer.start(15000)#15秒以后进入水平move

    def _on_inactivity_timeout(self):
        if self.inactivity_stage == 0:
            # 15s无互动：播放 move 动作
            # 随机决定初次散步方向：-1为向左走，1为向右走
            direction = random.choice([-1, 1])
            self.wander_speed = direction * 2  # 速度可适度调整
            self.wander_start_x = self.x()     # 记录散步起点
            
            # 向左走(direction < 0)时进行翻转
            self.play_action("move", is_flipped=(direction < 0))
            self.inactivity_stage = 1
            self.inactivity_timer.start(15000)#再15秒以后进入坐姿
            self.wander_timer.start(50)       # 开启散步定时器 (50ms)
        elif self.inactivity_stage == 1:
            # 停止散步
            self.wander_timer.stop()
            # 播放 sit
            self.move(self.x(), self.y() + 10)
            self.play_action("sit")
            self.inactivity_stage = 2
            self.inactivity_timer.start(15000)#再15秒以后进入躺姿
        elif self.inactivity_stage == 2:
            # 播放 sleep
            self.move(self.x() - 10, self.y() + 10)
            self.play_action("sleep")
            self.inactivity_stage = 0
            self.inactivity_timer.start(45000)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 当左键点击(准备拖拽或点击)时，如果有气泡菜单则关闭
            if hasattr(self.pet_actions, "circular_menu") and self.pet_actions.circular_menu is not None:
                if getattr(self.pet_actions.circular_menu, "isVisible", lambda: False)():
                    self.pet_actions.circular_menu.close_menu()

            self.offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_dragging = False
            
            # 打断准备阶段
            if getattr(self, '_is_preparing_special', False):
                self._is_preparing_special = False
                
            # 按下的瞬间暂停计时防挂机
            if self.current_action == "idle":
                self.inactivity_timer.stop()
              
        elif event.button() == Qt.MouseButton.RightButton:
            # 右击也可以关闭当前弹出的提示气泡
            self.dialogue_system.hide_dialogue()
            
            # 在 special 或者准备阶段忽略呼出菜单
            if self.current_action == "special" or getattr(self, '_is_preparing_special', False):
                return
                
            # 菜单打开期间循环 interact
            self.menu_interact_mode = True
            self.play_action("interact", force_loop=True)
            
            # 委托 action 模块处理右键菜单
            self.pet_actions.show_context_menu(event.globalPosition().toPoint())

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 双击交互打断对话框
            self.dialogue_system.hide_dialogue()
            
            # 免疫 special 期间的双击操作
            if self.current_action == "special":
                return
                
            # 记录双击发生的时间，并在接下来的0.5秒内免疫按下鼠标的打断
            self._last_double_click_time = time.time()
            self._is_double_click = True
            self.play_action("special", force_loop=False)
        else:
            super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            # 拖拽时打断对话框
            self.dialogue_system.hide_dialogue()
            
            # 如果处于特殊动作准备阶段（向右平移），只要用户一拖拽立马打断
            if getattr(self, '_is_preparing_special', False):
                self._is_preparing_special = False
                
            # 只有双击0.5秒后的拖动才被认为是真实的拖拽互动，立刻打断动作变为move
            if time.time() - getattr(self, '_last_double_click_time', 0) > 0.5:
                self._is_dragging = True
                
                # 计算拖拽位置
                new_pos = event.globalPosition().toPoint() - self.offset
                screen_geo = self.screen().availableGeometry()
                
                # 限制在屏幕范围内
                new_x = max(screen_geo.left(), min(new_pos.x(), screen_geo.right() - self.width()))
                new_y = max(screen_geo.top(), min(new_pos.y(), screen_geo.bottom() - self.height()))
                
                # 判断水平移动方向，如果向左移动则翻转
                is_moving_left = new_x < self.pos().x()
                is_moving_right = new_x > self.pos().x()
                
                if self.current_action != "move":
                    self.play_action("move", is_flipped=is_moving_left)
                else:
                    if is_moving_left and not getattr(self, "is_flipped", False):
                        self.play_action("move", is_flipped=True)
                    elif is_moving_right and getattr(self, "is_flipped", False):
                        self.play_action("move", is_flipped=False)
                
                self.move(new_x, new_y)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 如果刚刚发生的是双击，这只是双击的鼠标松开事件，直接放行，不做任何打断
            if getattr(self, '_is_double_click', False):
                self._is_double_click = False
                return

            if getattr(self, '_is_dragging', False):
                # 仅在拖拽结束时回到 idle
                if self.current_action == "move":
                    self.play_action("idle")
            else:
                # 只是单击且没有拖动，恢复计时器（如果是从 idle 点下去的）
                if self.current_action == "idle" and hasattr(self, 'inactivity_timer'):
                    self._reset_inactivity_timer()

    def force_on_top(self):
        """强制将窗口保持在屏幕最顶层"""
        # 使用 Qt 的方式进行窗口置顶，避免在 Windows 下重复 setWindowFlags 产生僵尸窗口句柄
        self.show()
        self.raise_()
        self.activateWindow()

    def resizeEvent(self, event):
        super().resizeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    pet = PetWindow()
    pet.show()
    sys.exit(app.exec())
