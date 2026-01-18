import os
import subprocess
import pyautogui
from datetime import datetime
import platform

def capture_screen_content():
    """
    捕获当前屏幕并保存到 resource 文件夹
    """
    try:
        # 获取 workspace 根目录（假设相对于当前文件位置）
        # src/features/automation.py -> src/features -> src -> root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        resource_dir = os.path.join(root_dir, "resource")
        
        if not os.path.exists(resource_dir):
            os.makedirs(resource_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(resource_dir, filename)
        
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        
        return f"屏幕已截图，保存为: {filename}"
    except Exception as e:
        return f"截图失败: {e}"
