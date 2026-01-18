import os
import subprocess
import pyautogui
from datetime import datetime
import platform

def capture_screen_content(save_dir=None):
    """
    捕获当前屏幕并保存到指定文件夹
    Args:
        save_dir (str, optional): 保存目录。如果不传，默认保存到项目 resource 目录。
    """
    try:
        # 确定保存目录
        if save_dir:
            target_dir = save_dir
        else:
            # 获取 workspace 根目录（假设相对于当前文件位置）
            # src/function/__file__ -> src/function -> src -> root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(current_dir))
            target_dir = os.path.join(root_dir, "resource")
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(target_dir, filename)
        
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        
        return f"屏幕已截图，保存为: {filepath}"
    except Exception as e:
        return f"截图失败: {e}"
