import os
import subprocess
import pyautogui
from datetime import datetime
import platform

def open_application(app_name):
    """
    根据名称打开应用程序。
    简单的名称匹配。
    """
    app_name = app_name.lower()
    system = platform.system()
    
    try:
        if system == "Windows":
            if "calc" in app_name or "计算器" in app_name:
                subprocess.Popen("calc.exe")
                return "已打开计算器"
            elif "notepad" in app_name or "记事本" in app_name:
                subprocess.Popen("notepad.exe")
                return "已打开记事本"
            elif "cmd" in app_name or "终端" in app_name:
                subprocess.Popen("cmd.exe")
                return "已打开命令行"
            elif "explorer" in app_name or "资源管理器" in app_name:
                subprocess.Popen("explorer.exe")
                return "已打开资源管理器"
            elif "网易云" in app_name or "music" in app_name:
                try:
                    # 尝试直接通过注册的名称启动
                    subprocess.Popen("cloudmusic.exe") 
                    return "已打开网易云音乐"
                except FileNotFoundError:
                    # 尝试常见安装路径
                    common_paths = [
                        r"C:\Program Files (x86)\Netease\CloudMusic\cloudmusic.exe",
                        r"C:\Program Files\Netease\CloudMusic\cloudmusic.exe",
                        r"D:\Program Files (x86)\Netease\CloudMusic\cloudmusic.exe",
                        r"C:\Netease\CloudMusic\cloudmusic.exe"
                    ]
                    for path in common_paths:
                        if os.path.exists(path):
                            subprocess.Popen(path)
                            return "已打开网易云音乐"
                    return "未找到网易云音乐，请确认安装位置"
            else:
                # 尝试直接运行命令
                try:
                    subprocess.Popen(app_name)
                    return f"尝试启动 {app_name}"
                except FileNotFoundError:
                    return f"找不到应用: {app_name}"
        else:
            return "当前仅支持 Windows 系统的简单应用启动"
            
    except Exception as e:
        return f"启动失败: {e}"

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
