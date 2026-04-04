import os
import sys

try:
    import winreg
except Exception:  # pragma: no cover
    winreg = None

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "DigitMaid"


def _build_startup_command():
    """Build command written to Windows Run key."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../"))
    run_py = os.path.join(project_root, "src", "core", "run.py")
    return f'"{sys.executable}" "{run_py}"'


def is_startup_enabled():
    if os.name != "nt" or winreg is None:
        return False

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(value and str(value).strip())
    except FileNotFoundError:
        return False
    except OSError:
        return False


def set_startup_enabled(enabled):
    """Enable/disable startup. Returns (ok, message)."""
    if os.name != "nt" or winreg is None:
        return False, "当前系统不支持开机自启动设置"

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                command = _build_startup_command()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
                return True, "已开启开机自启动"

            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
            return True, "已关闭开机自启动"
    except OSError as e:
        return False, f"设置开机自启动失败: {e}"
