import os
import plistlib
import subprocess
import sys

try:
    import winreg
except Exception:  # pragma: no cover
    winreg = None

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "DigitMaid"
MAC_LABEL = "com.digitmaid.app"


def _is_windows():
    return os.name == "nt" and winreg is not None


def _is_macos():
    return sys.platform == "darwin"


def _project_root():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(current_dir, "../../"))


def _mac_launch_agent_path():
    return os.path.join(os.path.expanduser("~"), "Library", "LaunchAgents", f"{MAC_LABEL}.plist")


def _build_startup_program_args():
    if getattr(sys, "frozen", False):
        return [sys.executable]

    run_py = os.path.join(_project_root(), "src", "core", "run.py")
    return [sys.executable, run_py]


def _build_startup_command():
    """Build command written to Windows Run key."""
    args = _build_startup_program_args()
    return " ".join([f'"{arg}"' for arg in args])


def is_startup_enabled():
    if _is_windows():
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, APP_NAME)
                expected = _build_startup_command()
                return bool(value and str(value).strip().lower() == expected.lower())
        except FileNotFoundError:
            return False
        except OSError:
            return False

    if _is_macos():
        plist_path = _mac_launch_agent_path()
        if not os.path.exists(plist_path):
            return False

        try:
            with open(plist_path, "rb") as f:
                data = plistlib.load(f)
            args = data.get("ProgramArguments", [])
            return bool(data.get("Label") == MAC_LABEL and args == _build_startup_program_args())
        except Exception:
            return False

    return False


def set_startup_enabled(enabled):
    """Enable/disable startup. Returns (ok, message)."""
    if _is_windows():
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

    if _is_macos():
        plist_path = _mac_launch_agent_path()
        args = _build_startup_program_args()
        try:
            os.makedirs(os.path.dirname(plist_path), exist_ok=True)
            if enabled:
                plist_data = {
                    "Label": MAC_LABEL,
                    "ProgramArguments": args,
                    "RunAtLoad": True,
                    "KeepAlive": False,
                    "WorkingDirectory": _project_root(),
                }
                with open(plist_path, "wb") as f:
                    plistlib.dump(plist_data, f)

                subprocess.run(["launchctl", "unload", plist_path], check=False, capture_output=True)
                subprocess.run(["launchctl", "load", plist_path], check=False, capture_output=True)
                return True, "已开启开机自启动（macOS）"

            subprocess.run(["launchctl", "unload", plist_path], check=False, capture_output=True)
            if os.path.exists(plist_path):
                os.remove(plist_path)
            return True, "已关闭开机自启动（macOS）"
        except OSError as e:
            return False, f"设置开机自启动失败: {e}"

    return False, "当前系统不支持开机自启动设置"
