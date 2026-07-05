import csv
import json
import os
import platform
import subprocess
from datetime import datetime

from PyQt6.QtCore import QStandardPaths


MAX_COMMAND_CHARS = 92


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
    text = " ".join(str(text).split())
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return f"{text[: max_chars - 3]}..."


def _format_updated_at(raw_value, fallback_mtime=None):
    if raw_value:
        return str(raw_value)
    if fallback_mtime:
        return datetime.fromtimestamp(fallback_mtime).strftime("%Y-%m-%d %H:%M:%S")
    return "未知"


def _load_bridge_status():
    path = get_bridge_status_path()
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        return {
            "title": "Codex连接",
            "content": f"状态桥接文件读取失败: {e}",
        }

    if not isinstance(payload, dict):
        return None

    mtime = os.path.getmtime(path)
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

        try:
            cpu = float(cpu_raw)
        except ValueError:
            cpu = 0.0
        try:
            mem = float(mem_raw)
        except ValueError:
            mem = 0.0

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
    bridge_status = _load_bridge_status()
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
