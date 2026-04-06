import os
import subprocess
import platform

_APP_PATH_CACHE = {
    "mtime": None,
    "data": {},
}

_WINDOWS_CONSOLE_APPS = {
    "cmd.exe",
    "powershell.exe",
    "pwsh.exe",
}


def _launch_windows_app(target):
    """Launch app safely on Windows, keeping console apps visible."""
    exe_name = os.path.basename(target).lower()

    # 控制台程序需要新建控制台窗口，不能用 DETACHED_PROCESS。
    if exe_name in _WINDOWS_CONSOLE_APPS:
        subprocess.Popen([target], creationflags=subprocess.CREATE_NEW_CONSOLE, shell=False)
        return

    subprocess.Popen([target], creationflags=subprocess.DETACHED_PROCESS, shell=False)

def load_app_paths():
    """解析简单的 YAML 文件读取应用路径配置"""
    config_path = os.path.join(os.path.dirname(__file__), "apps.yaml")
    apps = {}
    if not os.path.exists(config_path):
        _APP_PATH_CACHE["mtime"] = None
        _APP_PATH_CACHE["data"] = {}
        return apps

    mtime = os.path.getmtime(config_path)
    if _APP_PATH_CACHE["mtime"] == mtime:
        return _APP_PATH_CACHE["data"]
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            current_app = None
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or stripped == "app_paths:":
                    continue
                # 解析 key: (缩进2格)
                if line.startswith("  ") and not line.startswith("    "):
                    current_app = stripped.replace(":", "").strip()
                    apps[current_app] = []
                # 解析 value: (缩进4格的 - )
                elif line.startswith("    - ") and current_app is not None:
                    # 获取破折号后面的路径并去除两端空格和引号
                    path = stripped[2:].strip().strip("'\"")
                    apps[current_app].append(path)
    except Exception as e:
        print(f"读取 apps.yaml 失败: {e}")

    _APP_PATH_CACHE["mtime"] = mtime
    _APP_PATH_CACHE["data"] = apps
    return apps

def open_application(app_name):
    """
    根据名称打开应用程序。
    从 apps.yaml 中读取配置。
    """
    app_name = app_name.lower()
    system = platform.system()
    
    try:
        if system == "Windows":
            app_configs = load_app_paths()
            
            # 遍历配置文件中的关键词
            for keyword, paths in app_configs.items():
                if keyword.lower() in app_name:
                    for path in paths:
                        # 对于不需要完整路径的系统命令（如 calc.exe等），直接尝试启动
                        if os.path.exists(path) or "\\" not in path:
                            try:
                                _launch_windows_app(path)
                                return f"已启动{keyword}"
                            except FileNotFoundError:
                                continue
                    return f"未找到{keyword}，请确认 apps.yaml 中的安装位置"
            
            # 如果配置文件中没找到，尝试直接运行命令
            try:
                _launch_windows_app(app_name)
                return f"尝试启动 {app_name}"
            except FileNotFoundError:
                return f"找不到应用: {app_name}"
        else:
            return "当前仅支持 Windows 系统的简单应用启动"
            
    except Exception as e:
        return f"启动失败: {e}"
