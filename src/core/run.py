import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

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

from src.ui.pet_window import PetWindow

def main():
    """
    Digit Maid 应用程序入口点
    """
    print(f"启动 Digit Maid... (Root: {project_root})")
    
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei"))
    
    # 创建并显示桌宠窗口
    pet = PetWindow()
    pet.show()
    
    print("桌宠已启动。右键点击桌宠可查看功能菜单。")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
