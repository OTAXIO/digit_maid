import os
import time
import random
import math

from PyQt6.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, QTimer, QSize, QSettings
from PyQt6.QtGui import QMovie, QTransform
import sys

# 导入分离后的UI模块
try:
    from .dialogue import DialogueSystem
    from .action import MaidActions
    from .menu_controller import OptionMenuController
except ImportError:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))
    if project_root not in sys.path:
        sys.path.append(project_root)
    from src.ui.dialogue import DialogueSystem
    from src.ui.action import MaidActions
    from src.ui.menu_controller import OptionMenuController

class MaidWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.is_macos = sys.platform == "darwin"

        # 素材未加载时的初始窗口大小（真实显示大小由 GIF 帧尺寸决定）
        self.default_maid_width = 85
        self.default_maid_height = 85
        
        self.initUI()
        self.offset = QPoint()
        
        # 资源目录
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        self.root_dir = root_dir
        self.current_action = "idle"

        # 统一管理菜单可见状态与操作权限
        self.menu_controller = OptionMenuController()
        
        # 初始化各个子系统
        self.dialogue_system = DialogueSystem(self)
        self.maid_actions = MaidActions(self, self.dialogue_system)

        # GIF 显示层
        self.maid_label = QLabel(self)
        self.maid_label.setStyleSheet("background: transparent;")
        self.maid_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.maid_label.setScaledContents(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.maid_label)

        # 动作配置
        self.anim_cfg = self._load_animation_config()
        self.current_movie = None
        self.current_loop = True
        self.menu_interact_mode = False
        self._flip_transform = QTransform().scale(-1, 1)
        self.base_render_scale = 0.5
        self.user_scale = 1.0
        self.min_user_scale = 0.2
        self.max_user_scale = 5.0
        self.scale_step = 0.1
        self._load_persisted_user_scale()
        self._source_frame_size = None
        self._custom_scale_adjusting = False
        self._custom_scale_backup = self.user_scale
        self._scale_preview_tip_timer = QTimer(self)
        self._scale_preview_tip_timer.setSingleShot(True)
        self._scale_preview_tip_timer.timeout.connect(self._on_scale_preview_stop)
        self._scale_preview_tip_delay_ms = 450

        # 空闲状态机：15秒无交互进入 sit，再15秒无交互进入 sleep
        self.inactivity_stage = 0
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.setSingleShot(True)
        self.inactivity_timer.timeout.connect(self._on_inactivity_timeout)
        self._inactivity_deadline = None

        # 闲置散步计时器
        self.wander_timer = QTimer(self)
        self.wander_timer.timeout.connect(self._on_wander_tick)
        self.wander_speed = 0

        # 拖拽松手后若离开底边，缓慢降落到底边
        self._is_falling = False
        self._fall_x = 0.0
        self._fall_y = 0.0
        self._fall_start_y = 0.0
        self._fall_distance = 1.0
        self._fall_tick = 0
        self._fall_vertical_speed = 1.0
        self._fall_vertical_accel = 0.03
        self._fall_vertical_max_speed = 2.6
        self._fall_sway_amplitude = 16.0
        self._fall_sway_speed = 0.22
        self._fall_sway_phase = 0.0
        self._fall_drift_speed = 0.0
        self._fall_timer = QTimer(self)
        self._fall_timer.timeout.connect(self._on_fall_tick)

        # 非 macOS 平台保持定时置顶，避免被全屏程序遮挡。
        # macOS 下不启用，防止一直压在其他应用上方影响操作。
        self.topmost_timer = QTimer(self)
        self.topmost_timer.timeout.connect(self._keep_on_top)
        if not self.is_macos:
            self.topmost_timer.start(1000)  # 每秒置顶一次，降低事件循环压力

        # 先播放 start 动画（若配置不存在则会在底层 fallback 到 idle 或返回 False）
        if not self.play_action("start", force_loop=False):
            self.play_action("idle")
            
        self._reset_inactivity_timer()

    def _keep_on_top(self):
        if self.is_macos:
            return
        # 仅提升Z轴顺序，不窃取焦点，避免影响用户打字
        self.raise_()

    def _is_menu_ui_active(self):
        if getattr(self, "menu_interact_mode", False):
            return True

        controller = getattr(self, "menu_controller", None)
        if controller is not None and controller.is_menu_open:
            return True

        if getattr(self, "_list_menu_open", False):
            return True

        actions = getattr(self, "maid_actions", None)
        if actions is None:
            return False

        circular_menu = getattr(actions, "circular_menu", None)
        if circular_menu is None:
            return False

        return bool(getattr(circular_menu, "isVisible", lambda: False)())

    def _operation_allowed(self, operation_name):
        controller = getattr(self, "menu_controller", None)
        if controller is None:
            return True
        return controller.allows(operation_name)

    def initUI(self):
        # ... (保持不变)
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if not self.is_macos:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 获取屏幕尺寸
        screen = QApplication.primaryScreen().availableGeometry()
        maid_width = self.default_maid_width
        maid_height = self.default_maid_height
        
        # 计算左下角位置 (加上一点边距)
        x = screen.left() + 100 
        y = screen.bottom() - maid_height + 10
        
        self.setGeometry(x, y, maid_width, maid_height)
        self.setWindowTitle('DigitMaid')

    def _load_animation_config(self):
        cfg_path = os.path.join(os.path.dirname(__file__), "maid_animations.yaml")
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                lines = [line.rstrip("\n") for line in f]

            cfg = {
                "base_dir": "resource/wisdel/皮肤素材/可用素材",
                "fall_mode": "smooth",
                "smooth_fall": True,
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

                if raw.startswith("fall_mode:"):
                    mode = raw.split(":", 1)[1].strip().lower()
                    if mode in ("smooth", "direct", "none"):
                        cfg["fall_mode"] = mode
                    continue

                if raw.startswith("smooth_fall:"):
                    value = raw.split(":", 1)[1].strip().lower()
                    cfg["smooth_fall"] = value in ("true", "1", "yes", "on")
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
        # 预览调节期间禁止切到 idle，避免任何遗漏路径触发待机动作
        if self._custom_scale_adjusting and action_name == "idle":
            return False

        # 空中不进入 idle，避免在未落地时提前触发待机计时
        if action_name == "idle" and self._get_fall_mode() != "none" and not self._is_at_bottom_boundary(tolerance=0):
            return False

        # 只要切换动作，就先暂停待机计时；如果是回到 idle，再重新开始计时
        self._stop_inactivity_timer(reset_stage=True)

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
            return False

        # 新增：允许在 yaml 里用逗号分隔配置多个动作，并在播放时随机抽取其中一个
        if isinstance(gif_file, str) and "," in gif_file:
            gif_file = random.choice([f.strip() for f in gif_file.split(",")])

        gif_path = os.path.join(self.root_dir, base_dir_rel, gif_file)
        if not os.path.exists(gif_path):
            print(f"动作素材不存在: {gif_path}")
            return False

        if self.current_movie is not None:
            try:
                self.current_movie.frameChanged.disconnect(self._on_frame_changed)
            except (TypeError, RuntimeError):
                pass
            self.current_movie.stop()
            self.current_movie.deleteLater()

        # 指定 parent 为 self，防止意外的垃圾回收崩溃
        movie = QMovie(gif_path, parent=self)
        movie.jumpToFrame(0)

        # 获取 GIF 原始像素，并按 base_render_scale * user_scale 进行缩放显示
        frame_size = movie.currentImage().size()
        if not frame_size.isEmpty():
            self._source_frame_size = QSize(frame_size.width(), frame_size.height())
            current_pos = self.pos()
            old_height = self.height()
            screen_geo = self.screen().availableGeometry()

            target_width, target_height = self._get_target_maid_size()
            
            # 保持桌宠的左下角不发生偏移（防止不同宽高且大小不一的动作导致位置乱跳）
            left_x = current_pos.x()
            bottom_y = current_pos.y() + old_height
            
            new_x = left_x
            new_y = bottom_y - target_height
            
            # 如果右下角超出屏幕则向左/向上挤
            if new_x + target_width > screen_geo.right():
                new_x = screen_geo.right() - target_width
            if new_y + target_height > screen_geo.bottom() + 10:
                new_y = screen_geo.bottom() + 10 - target_height
                
            # 兜底保证左上角不越界
            new_x = max(screen_geo.left(), new_x)
            new_y = max(screen_geo.top(), new_y)
            
            movie.setScaledSize(QSize(target_width, target_height))
            self.maid_label.setFixedSize(target_width, target_height)
            # 先刷新布局约束，再执行缩放和位移；否则从大动作切回小动作时
            # 可能只移动到新 y 而尺寸仍被旧约束卡住，出现“逐次下沉”。
            if self.layout() is not None:
                self.layout().activate()
            self.resize(target_width, target_height)
            self.move(new_x, new_y)
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
            self.maid_label.setMovie(movie)
            
        movie.start()
        
        if self.is_flipped:
            # 手动提取第一帧进行翻转并上屏
            pixmap = movie.currentPixmap()
            if not pixmap.isNull():
                self.maid_label.setPixmap(pixmap.transformed(self._flip_transform))
        
        # 只有在 idle 状态下才允许计时器流动
        if action_name == "idle" and hasattr(self, 'inactivity_timer'):
            self._reset_inactivity_timer()
            
        return True

    def _get_target_maid_size(self):
        if self._source_frame_size is not None and not self._source_frame_size.isEmpty():
            base_width = max(1, int(round(self._source_frame_size.width() * self.base_render_scale)))
            base_height = max(1, int(round(self._source_frame_size.height() * self.base_render_scale)))
        else:
            base_width = self.default_maid_width
            base_height = self.default_maid_height

        target_width = max(1, int(round(base_width * self.user_scale)))
        target_height = max(1, int(round(base_height * self.user_scale)))
        return target_width, target_height

    def _clamp_user_scale(self, value):
        return max(self.min_user_scale, min(self.max_user_scale, value))

    def _load_persisted_user_scale(self):
        settings = QSettings("DigitMaid", "DigitMaid")
        saved_value = settings.value("ui/user_scale", self.user_scale)
        try:
            saved_scale = float(saved_value)
        except (TypeError, ValueError):
            saved_scale = self.user_scale
        self.user_scale = self._clamp_user_scale(saved_scale)

    def _save_persisted_user_scale(self):
        settings = QSettings("DigitMaid", "DigitMaid")
        settings.setValue("ui/user_scale", float(self.user_scale))
        settings.sync()

    def begin_custom_scale_adjustment(self):
        if not self._custom_scale_adjusting:
            self._custom_scale_backup = float(self.user_scale)
        self._custom_scale_adjusting = True
        if hasattr(self, "menu_controller"):
            self.menu_controller.set_custom_scale_adjusting(True)
        self._scale_preview_tip_timer.stop()
        self.wander_timer.stop()
        self._stop_inactivity_timer(reset_stage=False)
        if self._is_falling:
            self._stop_fall()
        return True, f"当前预览倍率: {self.user_scale:.1f}"

    def confirm_custom_scale_adjustment(self):
        if not self._custom_scale_adjusting:
            return True, f"当前倍率: {self.user_scale:.1f}"
        self._custom_scale_adjusting = False
        if hasattr(self, "menu_controller"):
            self.menu_controller.set_custom_scale_adjusting(False)
        self._scale_preview_tip_timer.stop()
        self._custom_scale_backup = float(self.user_scale)
        self._save_persisted_user_scale()
        if not getattr(self, "menu_interact_mode", False) and self.current_action == "idle":
            self._reset_inactivity_timer()
        return True, f"已保存倍率: {self.user_scale:.1f}"

    def cancel_custom_scale_adjustment(self):
        if not self._custom_scale_adjusting:
            return True, "已取消（没有未保存的自定义调整）"

        self._custom_scale_adjusting = False
        if hasattr(self, "menu_controller"):
            self.menu_controller.set_custom_scale_adjusting(False)
        self._scale_preview_tip_timer.stop()
        backup = float(self._custom_scale_backup)
        ok, _ = self.set_maid_scale_factor(backup)
        if not getattr(self, "menu_interact_mode", False) and self.current_action == "idle":
            self._reset_inactivity_timer()
        if ok:
            return True, f"已恢复到未保存前的倍率: {self.user_scale:.1f}"
        return False, "恢复大小失败"

    def _schedule_scale_preview_tip(self):
        if not self._custom_scale_adjusting:
            return
        self._scale_preview_tip_timer.start(self._scale_preview_tip_delay_ms)

    def _on_scale_preview_stop(self):
        if not self._custom_scale_adjusting:
            return
        if hasattr(self, "dialogue_system"):
            self.dialogue_system.show_message("自定义大小", f"当前放大倍数: {self.user_scale:.1f}x")

    def adjust_scale_by_wheel_delta(self, delta):
        if not self._custom_scale_adjusting:
            return False

        if delta == 0:
            return False

        step_count = int(delta / 120)
        if step_count == 0:
            step_count = 1 if delta > 0 else -1

        old_scale = self.user_scale
        self.user_scale = self._clamp_user_scale(self.user_scale + step_count * self.scale_step)
        if self.user_scale == old_scale:
            return False

        if self._apply_user_scale_to_current_movie():
            self._sync_open_circular_menu_scale()
            self._schedule_scale_preview_tip()
            return True

        ok, _ = self.set_maid_scale_factor(self.user_scale)
        if ok:
            self._sync_open_circular_menu_scale()
            self._schedule_scale_preview_tip()
        return ok

    def _sync_open_circular_menu_scale(self):
        actions = getattr(self, "maid_actions", None)
        if actions is None:
            return
        menu = getattr(actions, "circular_menu", None)
        if menu is None:
            return
        if not getattr(menu, "isVisible", lambda: False)():
            return
        if hasattr(menu, "sync_menu_scale_from_maid"):
            menu.sync_menu_scale_from_maid()

    def set_maid_scale_factor(self, value):
        try:
            target_scale = float(value)
        except (TypeError, ValueError):
            return False, "请输入 0.2 到 5.0 之间的数字"

        self.user_scale = self._clamp_user_scale(target_scale)
        if self._apply_user_scale_to_current_movie():
            if not self._custom_scale_adjusting:
                self._save_persisted_user_scale()
            return True, f"当前缩放倍数: {self.user_scale:.2f}"

        # 没有当前动画时，也按默认尺寸缩放窗口，保持设置即时生效
        target_width, target_height = self._get_target_maid_size()
        current_pos = self.pos()
        old_height = self.height()
        screen_geo = self.screen().availableGeometry()

        left_x = current_pos.x()
        bottom_y = current_pos.y() + old_height
        new_x = left_x
        new_y = bottom_y - target_height

        if new_x + target_width > screen_geo.right():
            new_x = screen_geo.right() - target_width
        if new_y + target_height > screen_geo.bottom() + 10:
            new_y = screen_geo.bottom() + 10 - target_height

        new_x = max(screen_geo.left(), new_x)
        new_y = max(screen_geo.top(), new_y)

        self.maid_label.setFixedSize(target_width, target_height)
        if self.layout() is not None:
            self.layout().activate()
        self.resize(target_width, target_height)
        self.move(new_x, new_y)
        if not self._custom_scale_adjusting:
            self._save_persisted_user_scale()
        return True, f"当前缩放倍数: {self.user_scale:.2f}"

    def _apply_user_scale_to_current_movie(self):
        if self.current_movie is None:
            return False

        target_width, target_height = self._get_target_maid_size()

        current_pos = self.pos()
        old_height = self.height()
        screen_geo = self.screen().availableGeometry()

        left_x = current_pos.x()
        bottom_y = current_pos.y() + old_height
        new_x = left_x
        new_y = bottom_y - target_height

        if new_x + target_width > screen_geo.right():
            new_x = screen_geo.right() - target_width
        if new_y + target_height > screen_geo.bottom() + 10:
            new_y = screen_geo.bottom() + 10 - target_height

        new_x = max(screen_geo.left(), new_x)
        new_y = max(screen_geo.top(), new_y)

        self.current_movie.setScaledSize(QSize(target_width, target_height))
        self.maid_label.setFixedSize(target_width, target_height)
        if self.layout() is not None:
            self.layout().activate()
        self.resize(target_width, target_height)
        self.move(new_x, new_y)
        return True

    def _on_frame_changed(self, frame_number):
        sender_movie = self.sender()
        if sender_movie is None or sender_movie is not self.current_movie:
            return
            
        # 如果需要左右翻转，每帧渲染时手动更新 QLabel
        if getattr(self, "is_flipped", False):
            pixmap = sender_movie.currentPixmap()
            if not pixmap.isNull():
                self.maid_label.setPixmap(pixmap.transformed(self._flip_transform))
                
        # 检查是否到达最后一帧
        frame_count = sender_movie.frameCount()
        if frame_count <= 0:
            return
        if frame_number >= frame_count - 1:
            if not self.current_loop:
                sender_movie.stop()
                self._on_action_finished()

    def _on_action_finished(self):
        if self._custom_scale_adjusting:
            self._stop_inactivity_timer(reset_stage=True)
            self.wander_timer.stop()
            if self.current_action != "interact":
                self.play_action("interact", force_loop=True)
            elif self.current_movie is not None:
                self.current_movie.start()
            return

        # 菜单打开期间锁定为 interact，避免动作结束后误回 idle
        if self._is_menu_ui_active():
            self._stop_inactivity_timer(reset_stage=True)
            if self.current_action != "interact":
                self.play_action("interact", force_loop=True)
            elif self.current_movie is not None:
                self.current_movie.start()
            return

        # 下落阶段若动作结束，保持 fly 直到真正落地
        if self._is_falling and not self._is_at_bottom_boundary(tolerance=0):
            if self.current_action != "fly":
                self.play_action("fly", force_loop=True)
            return

        if self.current_loop:
            # 循环动作：重头继续播放
            if self.current_movie is not None:
                self.current_movie.start()
        else:
            if getattr(self, "is_dying", False):
                QApplication.instance().quit()
            else:
                # 非循环动作结束后回到 idle，play_action 内部会自动接管并重新启动计时器
                if self.current_action != "idle":
                    self.play_action("idle")

    def _on_wander_tick(self):
        controller = getattr(self, "menu_controller", None)
        if controller is not None and not controller.policy.allow_wander:
            self.wander_timer.stop()
            return

        if self._is_menu_ui_active():
            self.wander_timer.stop()
            return

        if self._custom_scale_adjusting:
            self.wander_timer.stop()
            return

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
                self.maid_label.setMovie(self.current_movie)
        elif new_x + self.width() > screen_geo.right() or new_x > start_x + 100:
            new_x = min(screen_geo.right() - self.width(), start_x + 100)
            self.wander_speed *= -1
            self.is_flipped = True
            if self.current_movie:
                pixmap = self.current_movie.currentPixmap()
                if not pixmap.isNull():
                    transform = QTransform().scale(-1, 1)
                    self.maid_label.setPixmap(pixmap.transformed(transform))
            
        self.move(new_x, self.y())

    def _reset_inactivity_timer(self):
        self.inactivity_stage = 0
        self._start_inactivity_timer(15000) # 15秒以后进入水平move

    def _start_inactivity_timer(self, duration_ms):
        controller = getattr(self, "menu_controller", None)
        if controller is not None and not controller.policy.allow_idle_timer:
            self._inactivity_deadline = None
            self.inactivity_timer.stop()
            return

        if self._is_menu_ui_active() or self._custom_scale_adjusting:
            self._inactivity_deadline = None
            self.inactivity_timer.stop()
            return

        self._inactivity_deadline = time.monotonic() + (duration_ms / 1000.0)
        self.inactivity_timer.start(duration_ms)

    def _stop_inactivity_timer(self, reset_stage=False):
        self.inactivity_timer.stop()
        self._inactivity_deadline = None
        if reset_stage:
            self.inactivity_stage = 0

    def _on_inactivity_timeout(self):
        if self._custom_scale_adjusting:
            self._stop_inactivity_timer(reset_stage=False)
            return

        # 防止计时器在临界点被 stop/restart 后仍触发陈旧 timeout，误打断当前动作
        deadline = self._inactivity_deadline
        if deadline is None:
            return

        if time.monotonic() + 0.05 < deadline:
            return

        self._inactivity_deadline = None

        # 菜单打开期间不进入 idle/sit/sleep 状态机，保持 interact
        if self._is_menu_ui_active():
            self._stop_inactivity_timer(reset_stage=True)
            if self.current_action != "interact":
                self.play_action("interact", force_loop=True)
            return

        if self.inactivity_stage == 0:
            # 15s无互动：播放 move 动作
            # 随机决定初次散步方向：-1为向左走，1为向右走
            direction = random.choice([-1, 1])
            self.wander_speed = direction * 2  # 速度可适度调整
            self.wander_start_x = self.x()     # 记录散步起点
            
            # 向左走(direction < 0)时进行翻转
            self.play_action("move", is_flipped=(direction < 0))
            self.inactivity_stage = 1
            self._start_inactivity_timer(15000) # 再15秒以后进入坐姿
            self.wander_timer.start(50)       # 开启散步定时器 (50ms)
        elif self.inactivity_stage == 1:
            # 停止散步
            self.wander_timer.stop()
            # 播放 sit
            self.move(self.x(), self.y() + 30)
            self.play_action("sit")
            self.inactivity_stage = 2
            self._start_inactivity_timer(15000) # 再15秒以后进入躺姿
        elif self.inactivity_stage == 2:
            # 播放 sleep
            self.move(self.x() - 10, self.y() + 20)
            self.play_action("sleep")
            self.inactivity_stage = 0
            self._start_inactivity_timer(45000)

    def _bottom_y_limit(self):
        screen_geo = self.screen().availableGeometry()
        return screen_geo.bottom() - self.height() + 10

    def _is_at_bottom_boundary(self, y=None, tolerance=1):
        if y is None:
            y = self.y()
        return y >= self._bottom_y_limit() - tolerance

    def _get_fall_mode(self):
        mode = str(self.anim_cfg.get("fall_mode", "")).strip().lower()
        if mode in ("smooth", "direct", "none"):
            return mode
        # 兼容旧配置 smooth_fall
        return "smooth" if self.anim_cfg.get("smooth_fall", True) else "direct"

    def _allow_air_interaction(self):
        return self._get_fall_mode() == "none"

    def _stop_fall(self):
        if self._fall_timer.isActive():
            self._fall_timer.stop()
        self._is_falling = False

    def _start_fall_to_bottom(self):
        if not self._operation_allowed("allow_fall"):
            self._stop_fall()
            return

        if self._custom_scale_adjusting:
            self._stop_fall()
            return

        mode = self._get_fall_mode()

        if mode == "none":
            # 不下坠模式：空中直接恢复 idle，并正常记录 idle 时间
            self._stop_fall()
            if self.current_action != "idle":
                self.play_action("idle")
            elif hasattr(self, 'inactivity_timer'):
                self._reset_inactivity_timer()
            return

        target_y = self._bottom_y_limit()
        if self.y() >= target_y:
            self.move(self.x(), target_y)
            self._stop_fall()
            if self.current_action != "idle":
                self.play_action("idle")
            return

        self._stop_fall()
        self._is_falling = True
        # 降落阶段不累计 idle 计时，落地后再回 idle 重置计时
        self._stop_inactivity_timer(reset_stage=True)
        if self.current_action != "fly":
            self.play_action("fly", force_loop=True)

        # 统一初始化下落坐标，具体下落模式由 smooth_fall 配置决定
        self._fall_x = float(self.x())
        self._fall_y = float(self.y())
        self._fall_start_y = self._fall_y
        self._fall_distance = max(1.0, float(target_y) - self._fall_start_y)
        self._fall_tick = 0

        if mode == "direct":
            # 非缓降：直落，不做横向摆动
            self._fall_vertical_speed = random.uniform(6.0, 9.0)
            self._fall_timer.start(16)
            return

        # 缓降：树叶式下落参数（左右摆动 + 轻微漂移 + 速度渐变）
        self._fall_vertical_speed = random.uniform(0.65, 1.15)
        self._fall_vertical_accel = random.uniform(0.02, 0.045)
        self._fall_vertical_max_speed = random.uniform(2.2, 3.0)
        self._fall_sway_amplitude = random.uniform(30.0, 50.0)
        self._fall_sway_speed = random.uniform(0.08, 0.14)
        self._fall_sway_phase = random.uniform(0.0, math.tau)
        self._fall_drift_speed = random.uniform(-0.12, 0.12)
        self._fall_timer.start(24)

    def _on_fall_tick(self):
        if not self._operation_allowed("allow_fall"):
            self._stop_fall()
            return

        if self._custom_scale_adjusting:
            self._stop_fall()
            return

        mode = self._get_fall_mode()

        if mode == "none":
            self._stop_fall()
            if self.current_action != "idle":
                self.play_action("idle")
            return

        target_y = self._bottom_y_limit()
        if self._fall_y >= target_y:
            self.move(self.x(), int(round(target_y)))
            if self._is_at_bottom_boundary(tolerance=0):
                self._stop_fall()
                self.play_action("idle")
            return

        if mode == "direct":
            # 非缓降：快速直落，落地后进入 idle
            self._fall_y = min(float(target_y), self._fall_y + self._fall_vertical_speed)
            self.move(self.x(), int(round(self._fall_y)))
            if self._fall_y >= target_y and self._is_at_bottom_boundary(tolerance=0):
                self._stop_fall()
                self.play_action("idle")
            return

        self._fall_tick += 1
        self._fall_vertical_speed = min(
            self._fall_vertical_max_speed,
            self._fall_vertical_speed + self._fall_vertical_accel,
        )
        self._fall_y = min(float(target_y), self._fall_y + self._fall_vertical_speed)

        progress = (self._fall_y - self._fall_start_y) / self._fall_distance
        progress = max(0.0, min(1.0, progress))
        damping = max(0.35, 1.0 - progress * 0.60)

        sway_main = math.sin(self._fall_sway_phase + self._fall_tick * self._fall_sway_speed)
        sway_flutter = math.sin(self._fall_sway_phase * 1.15 + self._fall_tick * (self._fall_sway_speed * 0.85))
        sway_x = (sway_main * self._fall_sway_amplitude + sway_flutter * 1.0) * damping

        self._fall_x += self._fall_drift_speed

        screen_geo = self.screen().availableGeometry()
        min_x = float(screen_geo.left())
        max_x = float(screen_geo.right() - self.width())

        target_x = self._fall_x + sway_x
        new_x = float(self.x()) * 0.70 + target_x * 0.30
        if new_x <= min_x:
            new_x = min_x
            self._fall_drift_speed = abs(self._fall_drift_speed) * 0.7 + 0.03
        elif new_x >= max_x:
            new_x = max_x
            self._fall_drift_speed = -abs(self._fall_drift_speed) * 0.7 - 0.03

        self._fall_x = min(max(self._fall_x, min_x), max_x)
        self.move(int(round(new_x)), int(round(self._fall_y)))

    def mousePressEvent(self, event):
        if self._custom_scale_adjusting:
            event.ignore()
            return

        if event.button() == Qt.MouseButton.LeftButton and not self._operation_allowed("allow_drag"):
            event.ignore()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            # 当左键点击(准备拖拽或点击)时，如果有气泡菜单则关闭
            if hasattr(self.maid_actions, "circular_menu") and self.maid_actions.circular_menu is not None:
                if getattr(self.maid_actions.circular_menu, "isVisible", lambda: False)():
                    self.maid_actions.circular_menu.close_menu()

            self.offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_dragging = False
            if self._is_falling:
                self._stop_fall()
                
            # 按下的瞬间暂停计时防挂机
            if self.current_action == "idle":
                self._stop_inactivity_timer()
              
        elif event.button() == Qt.MouseButton.RightButton:
            if not self._is_at_bottom_boundary() and not self._allow_air_interaction():
                return

            # 右击也可以关闭当前弹出的提示气泡
            self.dialogue_system.hide_dialogue()
            
            # 在 special 阶段忽略呼出菜单
            if self.current_action == "special":
                return
                
            # 菜单打开期间循环 interact
            self.menu_interact_mode = True
            # 菜单打开期间彻底停止 idle 计时与散步计时
            self._stop_inactivity_timer(reset_stage=True)
            self.wander_timer.stop()
            self.play_action("interact", force_loop=True)
            
            # 委托 action 模块处理右键菜单
            self.maid_actions.show_context_menu(event.globalPosition().toPoint())

    def mouseDoubleClickEvent(self, event):
        if self._custom_scale_adjusting:
            event.ignore()
            return

        if event.button() == Qt.MouseButton.LeftButton and not self._operation_allowed("allow_double_click"):
            event.ignore()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if not self._is_at_bottom_boundary() and not self._allow_air_interaction():
                return

            # 防止双击过快导致资源不停创建销毁引发闪退，增加0.5秒冷却
            current_time = time.time()
            if hasattr(self, '_last_double_click_time') and current_time - self._last_double_click_time < 0.5:
                return

            # 双击交互打断对话框
            self.dialogue_system.hide_dialogue()
            
            # 免疫 special 期间的双击操作
            if self.current_action == "special":
                return
                
            # 记录双击发生的时间，并在接下来的0.5秒内免疫按下鼠标的打断
            self._last_double_click_time = current_time
            self._is_double_click = True
            self.play_action("special", force_loop=False)
        else:
            super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        if self._custom_scale_adjusting:
            event.ignore()
            return

        if event.buttons() & Qt.MouseButton.LeftButton and not self._operation_allowed("allow_drag"):
            event.ignore()
            return

        if event.buttons() & Qt.MouseButton.LeftButton:
            # 拖拽时打断对话框
            self.dialogue_system.hide_dialogue()
                
            # 只有双击0.5秒后的拖动才被认为是真实的拖拽互动，立刻打断动作变为move
            if time.time() - getattr(self, '_last_double_click_time', 0) > 0.5:
                self._is_dragging = True
                
                # 计算拖拽位置
                new_pos = event.globalPosition().toPoint() - self.offset
                screen_geo = self.screen().availableGeometry()
                
                # 限制在屏幕范围内
                new_x = max(screen_geo.left(), min(new_pos.x(), screen_geo.right() - self.width()))
                new_y = max(screen_geo.top(), min(new_pos.y(), screen_geo.bottom() - self.height() + 10))
                
                # 判断水平移动方向，如果向左移动则翻转
                is_moving_left = new_x < self.pos().x()
                is_moving_right = new_x > self.pos().x()
                at_bottom = self._is_at_bottom_boundary(y=new_y)
                desired_action = "move" if at_bottom else "sweat"
                
                if self.current_action != desired_action:
                    self.play_action(desired_action, is_flipped=is_moving_left)
                else:
                    if is_moving_left and not getattr(self, "is_flipped", False):
                        self.play_action(desired_action, is_flipped=True)
                    elif is_moving_right and getattr(self, "is_flipped", False):
                        self.play_action(desired_action, is_flipped=False)
                
                self.move(new_x, new_y)

    def mouseReleaseEvent(self, event):
        if self._custom_scale_adjusting:
            event.ignore()
            return

        if event.button() == Qt.MouseButton.LeftButton and not self._operation_allowed("allow_drag"):
            self._is_dragging = False
            event.ignore()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            # 如果刚刚发生的是双击，这只是双击的鼠标松开事件，直接放行，不做任何打断
            if getattr(self, '_is_double_click', False):
                self._is_double_click = False
                return

            if getattr(self, '_is_dragging', False):
                self._is_dragging = False
                if self._is_at_bottom_boundary():
                    # 到达底边后恢复 idle
                    if self.current_action in ("move", "sweat", "fly"):
                        self.play_action("idle")
                else:
                    # 离开底边松手：使用 fly 缓慢降落
                    self._start_fall_to_bottom()
            else:
                # 单击松手时如果不在底边，也执行缓慢降落
                if not self._is_at_bottom_boundary():
                    self._start_fall_to_bottom()
                # 只是单击且没有拖动，恢复计时器（如果是从 idle 点下去的）
                elif self.current_action == "idle" and hasattr(self, 'inactivity_timer'):
                    self._reset_inactivity_timer()

    def wheelEvent(self, event):
        # 鼠标悬停在桌宠上滚轮缩放
        delta = event.angleDelta().y()
        if self.adjust_scale_by_wheel_delta(delta):
            event.accept()
            return

        super().wheelEvent(event)

    def force_on_top(self):
        """强制将窗口保持在屏幕最顶层"""
        # macOS 下避免主动抢焦点，防止影响其他应用操作。
        self.show()
        if self.is_macos:
            return

        # 使用 Qt 的方式进行窗口置顶，避免在 Windows 下重复 setWindowFlags 产生僵尸窗口句柄
        self.raise_()
        self.activateWindow()

    def resizeEvent(self, event):
        super().resizeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    maid = MaidWindow()
    maid.show()
    sys.exit(app.exec())

