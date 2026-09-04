import os
import plistlib
import subprocess
import sys
import tempfile

from src.core.paths import runtime_root, runtime_path

try:
    import winreg
except Exception:  # pragma: no cover
    winreg = None

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "DigitMaid"
MAC_LABEL = "com.digitmaid.app"
LINUX_DESKTOP_FILE = "digitmaid.desktop"
MAX_STARTUP_FILE_BYTES = 64 * 1024
STARTUP_COMMAND_TIMEOUT_SECONDS = 10


def _is_windows():
    return os.name == "nt" and winreg is not None


def _is_macos():
    return sys.platform == "darwin"


def _is_linux():
    return sys.platform.startswith("linux")


def _project_root():
    return str(runtime_root())


def _mac_launch_agent_path():
    return os.path.join(os.path.expanduser("~"), "Library", "LaunchAgents", f"{MAC_LABEL}.plist")


def _linux_autostart_path():
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if not config_home:
        config_home = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(config_home, "autostart", LINUX_DESKTOP_FILE)


def _build_startup_program_args():
    if getattr(sys, "frozen", False):
        return [sys.executable]

    return [sys.executable, str(runtime_path("src", "core", "run.py"))]


def _build_startup_command():
    """Build command written to Windows Run key."""
    return subprocess.list2cmdline(_build_startup_program_args())


def _desktop_exec_quote(arg):
    arg = str(arg)
    if not arg or any(ord(character) < 32 or ord(character) == 127 for character in arg):
        raise ValueError("启动命令路径包含非法控制字符")
    arg = arg.replace("%", "%%")
    if any(ch.isspace() or ch in '\\"`$' for ch in arg):
        escaped = (
            arg.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("`", "\\`")
            .replace("$", "\\$")
        )
        return f'"{escaped}"'
    return arg


def _build_linux_exec_command():
    return " ".join(_desktop_exec_quote(arg) for arg in _build_startup_program_args())


def _read_startup_file(path, *, binary=False):
    with open(path, "rb") as handle:
        payload = handle.read(MAX_STARTUP_FILE_BYTES + 1)
    if len(payload) > MAX_STARTUP_FILE_BYTES:
        raise ValueError("自启动配置文件过大")
    return payload if binary else payload.decode("utf-8")


def _atomic_write_startup_file(path, payload):
    destination_dir = os.path.dirname(path)
    os.makedirs(destination_dir, exist_ok=True)
    data = payload if isinstance(payload, bytes) else str(payload).encode("utf-8")
    if len(data) > MAX_STARTUP_FILE_BYTES:
        raise ValueError("自启动配置文件过大")

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination_dir,
            prefix=f".{os.path.basename(path)}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                os.remove(temporary_path)
            except OSError:
                pass


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
            data = plistlib.loads(_read_startup_file(plist_path, binary=True))
            args = data.get("ProgramArguments", [])
            return bool(data.get("Label") == MAC_LABEL and args == _build_startup_program_args())
        except Exception:
            return False

    if _is_linux():
        desktop_path = _linux_autostart_path()
        if not os.path.exists(desktop_path):
            return False

        try:
            content = _read_startup_file(desktop_path)
            lines = {line.strip() for line in content.splitlines()}
            return (
                "Name=DigitMaid" in lines
                and f"Exec={_build_linux_exec_command()}" in lines
                and "X-GNOME-Autostart-enabled=true" in lines
            )
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
            if enabled:
                plist_data = {
                    "Label": MAC_LABEL,
                    "ProgramArguments": args,
                    "RunAtLoad": True,
                    "KeepAlive": False,
                    "WorkingDirectory": _project_root(),
                }
                _atomic_write_startup_file(plist_path, plistlib.dumps(plist_data))

                subprocess.run(
                    ["launchctl", "unload", plist_path],
                    check=False,
                    capture_output=True,
                    timeout=STARTUP_COMMAND_TIMEOUT_SECONDS,
                )
                subprocess.run(
                    ["launchctl", "load", plist_path],
                    check=True,
                    capture_output=True,
                    timeout=STARTUP_COMMAND_TIMEOUT_SECONDS,
                )
                return True, "已开启开机自启动（macOS）"

            subprocess.run(
                ["launchctl", "unload", plist_path],
                check=False,
                capture_output=True,
                timeout=STARTUP_COMMAND_TIMEOUT_SECONDS,
            )
            if os.path.exists(plist_path):
                os.remove(plist_path)
            return True, "已关闭开机自启动（macOS）"
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            return False, f"设置开机自启动失败: {e}"

    if _is_linux():
        desktop_path = _linux_autostart_path()
        try:
            if enabled:
                desktop_content = "\n".join(
                    [
                        "[Desktop Entry]",
                        "Type=Application",
                        "Name=DigitMaid",
                        "Comment=Start DigitMaid desktop companion",
                        f"Exec={_build_linux_exec_command()}",
                        "Terminal=false",
                        "X-GNOME-Autostart-enabled=true",
                        "",
                    ]
                )
                _atomic_write_startup_file(desktop_path, desktop_content)
                return True, "已开启开机自启动（Linux）"

            if os.path.exists(desktop_path):
                os.remove(desktop_path)
            return True, "已关闭开机自启动（Linux）"
        except (OSError, ValueError) as e:
            return False, f"设置开机自启动失败: {e}"

    return False, "当前系统不支持开机自启动设置"
