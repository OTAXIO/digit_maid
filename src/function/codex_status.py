import csv
import math
import os
import platform
import subprocess
from datetime import datetime

from PyQt6.QtCore import QStandardPaths

from src.core.json_store import JsonStoreError, read_json_file
from src.core.numeric import bounded_int


MAX_COMMAND_CHARS = 92
MAX_STATUS_FILE_BYTES = 256 * 1024


def _app_data_dir():
    data_dir = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    if not data_dir:
        data_dir = os.path.join(os.path.expanduser("~"), ".digitmaid")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_bridge_status_path():
    """Path used by external Codex helpers to publish richer task status."""
    configured = os.environ.get("DIGITMAID_CODEX_STATUS_PATH", "").strip()
    if configured:
        return os.path.expanduser(configured)
    return os.path.join(_app_data_dir(), "codex_status.json")


def _truncate(text, max_chars=MAX_COMMAND_CHARS):
    max_chars = bounded_int(max_chars, default=MAX_COMMAND_CHARS, minimum=0, maximum=4096)
    text = " ".join(str(text).split())
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return f"{text[: max_chars - 3]}..."


def _format_updated_at(raw_value, fallback_mtime=None):
    if raw_value:
        return _truncate(raw_value, 64)
    if fallback_mtime is not None:
        try:
            return datetime.fromtimestamp(fallback_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except (OSError, OverflowError, ValueError):
            pass
    return "未知"


def _process_metric(raw_value, *, maximum):
    try:
        value = float(raw_value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(value, maximum))


def _load_bridge_status():
    try:
        path = get_bridge_status_path()
    except OSError as exc:
        return {
            "title": "Codex连接",
            "content": f"状态目录不可用: {_truncate(exc, 120)}",
        }
    if not os.path.exists(path):
        return None

    try:
        payload = read_json_file(path, max_bytes=MAX_STATUS_FILE_BYTES)
    except JsonStoreError as e:
        return {
            "title": "Codex连接",
            "content": f"状态桥接文件读取失败: {e}",
        }

    if not isinstance(payload, dict):
        return None

    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = None
    task = payload.get("task") or payload.get("objective") or payload.get("title") or "未命名任务"
    status = payload.get("status") or payload.get("state") or "运行中"
    step = payload.get("step") or payload.get("current_step") or payload.get("message") or ""
    detail = payload.get("detail") or payload.get("summary") or ""
    updated_at = _format_updated_at(payload.get("updated_at"), fallback_mtime=mtime)

    lines = [
        f"任务: {_truncate(task, 48)}",
        f"状态: {_truncate(status, 48)}",
    ]
    if step:
        lines.append(f"步骤: {_truncate(step, 56)}")
    if detail:
        lines.append(f"说明: {_truncate(detail, 72)}")
    lines.append(f"更新: {updated_at}")

    return {
        "title": "Codex连接",
        "content": "\n".join(lines),
    }


def _is_codex_process(command):
    lower = command.lower()
    if "codex_status" in lower:
        return False
    return "codex" in lower


def _list_codex_processes_posix():
    result = subprocess.run(
        ["ps", "-axo", "pid=,etime=,pcpu=,pmem=,command="],
        check=True,
        capture_output=True,
        text=True,
        timeout=3,
    )

    current_pid = os.getpid()
    processes = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 4)
        if len(parts) < 5:
            continue

        pid_raw, elapsed, cpu_raw, mem_raw, command = parts
        try:
            pid = int(pid_raw)
        except ValueError:
            continue

        if pid == current_pid or not _is_codex_process(command):
            continue

        if pid <= 0:
            continue
        cpu = _process_metric(cpu_raw, maximum=100_000.0)
        mem = _process_metric(mem_raw, maximum=100.0)

        processes.append(
            {
                "pid": pid,
                "elapsed": elapsed,
                "cpu": cpu,
                "mem": mem,
                "command": _truncate(command),
            }
        )

    processes.sort(key=lambda item: (item["cpu"], item["mem"]), reverse=True)
    return processes


def _list_codex_processes_windows():
    powershell_script = (
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,Name,CommandLine | "
        "ConvertTo-Csv -NoTypeInformation"
    )
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                powershell_script,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        processes = []
        for row in csv.DictReader(result.stdout.splitlines()):
            command = row.get("CommandLine") or row.get("Name") or ""
            if not _is_codex_process(command):
                continue
            try:
                pid = int(row.get("ProcessId") or 0)
            except ValueError:
                continue
            if pid <= 0:
                continue
            processes.append(
                {
                    "pid": pid,
                    "elapsed": "-",
                    "cpu": 0.0,
                    "mem": 0.0,
                    "command": _truncate(command),
                }
            )
        return processes
    except Exception:
        pass

    result = subprocess.run(
        ["tasklist", "/FO", "CSV", "/NH"],
        check=True,
        capture_output=True,
        text=True,
        timeout=3,
    )

    processes = []
    for fields in csv.reader(result.stdout.splitlines()):
        if len(fields) < 2:
            continue
        name, pid_raw = fields[0], fields[1]
        command = name
        if not _is_codex_process(command):
            continue
        try:
            pid = int(pid_raw)
        except ValueError:
            continue
        if pid <= 0:
            continue
        processes.append(
            {
                "pid": pid,
                "elapsed": "-",
                "cpu": 0.0,
                "mem": 0.0,
                "command": _truncate(command),
            }
        )
    return processes


def list_codex_processes():
    system = platform.system()
    if system in ("Darwin", "Linux"):
        return _list_codex_processes_posix()
    if system == "Windows":
        return _list_codex_processes_windows()
    return []


def get_codex_status_message(max_processes=4):
    try:
        bridge_status = _load_bridge_status()
    except Exception as exc:
        return "Codex连接", f"读取状态失败: {_truncate(exc, 120)}"
    if bridge_status is not None:
        return bridge_status["title"], bridge_status["content"]

    try:
        processes = list_codex_processes()
    except Exception as e:
        return "Codex进程", f"读取进程失败: {e}"

    if not processes:
        return (
            "Codex进程",
            "未发现正在运行的 Codex 相关进程。\n如需显示任务进度，可让 Codex 写入状态桥接文件。",
        )

    max_processes = bounded_int(max_processes, default=4, minimum=1, maximum=20)
    shown = processes[:max_processes]
    lines = [f"发现 {len(processes)} 个 Codex 相关进程"]
    for process in shown:
        lines.append(
            f"PID {process['pid']}  运行 {process['elapsed']}  "
            f"CPU {process['cpu']:.1f}%  MEM {process['mem']:.1f}%"
        )
        lines.append(process["command"])

    if len(processes) > len(shown):
        lines.append(f"另有 {len(processes) - len(shown)} 个进程未显示")

    return "Codex进程", "\n".join(lines)
