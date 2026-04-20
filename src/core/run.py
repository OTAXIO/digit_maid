import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import QSharedMemory

# 调整 Python 路径以确保可以从 src 导入模块
if getattr(sys, 'frozen', False):
    # 当被 PyInstaller 打包时，资源会被解压到 sys._MEIPASS
    project_root = sys._MEIPASS
else:
    # 正常 Python 环境下的路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))

if project_root not in sys.path:
    sys.path.append(project_root)

from src.ui.maid_window import MaidWindow


def _resolve_resource_path(*parts):
    """Resolve a resource path in both dev and PyInstaller runtime."""
    return os.path.join(project_root, *parts)


def _acquire_single_instance_lock():
    """Return a live shared memory lock object; return None if another instance is running."""
    lock = QSharedMemory("DigitMaid.Singleton")

    # 如果共享内存已经存在，说明可能已有实例在运行。
    # attach + detach 可清理潜在的孤儿句柄，再尝试 create 做最终判定。
    if lock.attach():
        lock.detach()

    if not lock.create(1):
        return None

    return lock


def _default_ui_font_family():
    """Choose a UI font family by platform."""
    if sys.platform == "darwin":
        return "PingFang SC"
    return "Microsoft YaHei"

def main():
    """
    Digit Maid 应用程序入口点
    """
    print(f"启动 Digit Maid... (Root: {project_root})")
    
    app = QApplication(sys.argv)
    app.setFont(QFont(_default_ui_font_family()))

    icon_path = _resolve_resource_path("resource", "wisdel", "皮肤素材", "维什戴尔大人.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    instance_lock = _acquire_single_instance_lock()
    if instance_lock is None:
        print("Digit Maid 已在运行，本次启动已取消。")
        return 0

    # 将锁绑定到 QApplication 生命周期，防止被 GC 提前释放。
    app._instance_lock = instance_lock
    
    # 创建并显示桌宠窗口
    maid = MaidWindow()
    maid.show()
    
    print("桌宠已启动。右键点击桌宠可查看功能菜单。")
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())

