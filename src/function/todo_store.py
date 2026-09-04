import os
from datetime import date, timedelta

from PyQt6.QtCore import QStandardPaths

from src.core.json_store import JsonStoreError, atomic_write_json, read_json_file


MAX_TODO_FILE_BYTES = 2 * 1024 * 1024
MAX_TODO_TEXT_CHARS = 500
MAX_TODOS_PER_DATE = 500
MAX_TODO_DATES = 3660
MAX_TOTAL_TODOS = 5000


class TodoDataLimitError(ValueError):
    """Raised when an attempted save exceeds the supported todo data limits."""


def _normalize_ddl_time(raw_ddl):
    if raw_ddl is None:
        return ""

    text = str(raw_ddl).strip().replace("：", ":")
    if not text:
        return ""

    parts = text.split(":")
    if len(parts) != 2:
        return ""

    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return ""

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return ""

    return f"{hour:02d}:{minute:02d}"


def _normalize_task_item(item):
    if isinstance(item, dict):
        text = str(item.get("text", "")).strip()
        ddl = _normalize_ddl_time(item.get("ddl", ""))
        completed = item.get("completed") is True
    else:
        raw_text = str(item).strip().replace("：", ":")
        ddl = ""
        text = raw_text
        completed = False

        segments = raw_text.split(None, 1)
        if segments and ":" in segments[0]:
            parsed_ddl = _normalize_ddl_time(segments[0])
            if parsed_ddl:
                ddl = parsed_ddl
                text = segments[1].strip() if len(segments) > 1 else ""

    if (
        not text
        or len(text) > MAX_TODO_TEXT_CHARS
        or any(ord(character) < 32 for character in text)
    ):
        return None

    return {"ddl": ddl, "text": text, "completed": completed}


def _task_sort_key(task):
    completion_rank = 1 if task.get("completed") is True else 0
    ddl = str(task.get("ddl", "")).strip()
    if ddl:
        try:
            hour_str, minute_str = ddl.split(":", 1)
            minute_of_day = int(hour_str) * 60 + int(minute_str)
            return (completion_rank, 0, minute_of_day, task.get("text", ""))
        except ValueError:
            pass
    return (completion_rank, 1, 24 * 60, task.get("text", ""))


def _get_app_data_dir():
    data_dir = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    if not data_dir:
        data_dir = os.path.join(os.path.expanduser("~"), ".digitmaid")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_todo_data_path():
    return os.path.join(_get_app_data_dir(), "todo_items.json")


def _build_default_items():
    today = date.today()
    items = {}

    def add_items(target_date, task_list):
        key = target_date.isoformat()
        bucket = items.setdefault(key, [])
        for task in task_list:
            normalized = _normalize_task_item(task)
            if normalized is not None:
                bucket.append(normalized)

    add_items(
        today,
        [
            "整理今天最重要的三件事",
            "补充水分并按时休息",
            "收尾后做10分钟复盘",
        ],
    )
    add_items(today + timedelta(days=1), ["检查明天日程准备情况"])
    add_items(today + timedelta(days=3), ["整理桌面和下载目录"])

    first_day = today.replace(day=1)
    if first_day != today:
        add_items(first_day, ["拆分本月目标并标记优先级"])

    return items


def _normalize_items(items_by_date, *, strict_limits=False):
    normalized = {}
    if not isinstance(items_by_date, dict):
        if strict_limits:
            raise TodoDataLimitError("待办数据必须按日期组织")
        return normalized

    total_items = 0
    for date_index, (date_key, values) in enumerate(items_by_date.items()):
        if date_index >= MAX_TODO_DATES:
            if strict_limits:
                raise TodoDataLimitError(f"待办日期不能超过 {MAX_TODO_DATES} 个")
            break

        raw_date_key = str(date_key).strip()
        if len(raw_date_key) != 10:
            if strict_limits:
                raise TodoDataLimitError(f"待办日期无效: {raw_date_key[:32]}")
            continue
        try:
            normalized_date = date.fromisoformat(raw_date_key).isoformat()
        except ValueError:
            if strict_limits:
                raise TodoDataLimitError(f"待办日期无效: {raw_date_key[:32]}")
            continue

        if strict_limits and normalized_date in normalized:
            raise TodoDataLimitError(f"待办日期重复: {normalized_date}")

        if isinstance(values, str):
            raw_items = [values]
        elif isinstance(values, list):
            raw_items = values
        else:
            if strict_limits:
                raise TodoDataLimitError(f"{normalized_date} 的待办必须是列表")
            continue

        existing_items = normalized.get(normalized_date, [])
        available_slots = MAX_TODOS_PER_DATE - len(existing_items)
        if len(raw_items) > available_slots:
            if strict_limits:
                raise TodoDataLimitError(
                    f"单日待办不能超过 {MAX_TODOS_PER_DATE} 项"
                )
            raw_items = raw_items[:available_slots]

        cleaned_items = []
        for item in raw_items:
            normalized_item = _normalize_task_item(item)
            if normalized_item is None:
                if strict_limits:
                    raise TodoDataLimitError(f"{normalized_date} 包含无效待办")
                continue
            if total_items >= MAX_TOTAL_TODOS:
                if strict_limits:
                    raise TodoDataLimitError(
                        f"待办总数不能超过 {MAX_TOTAL_TODOS} 项"
                    )
                return normalized
            cleaned_items.append(normalized_item)
            total_items += 1

        if cleaned_items:
            normalized[normalized_date] = sorted(
                [*existing_items, *cleaned_items],
                key=_task_sort_key,
            )

    return normalized


def save_todo_items_by_date(items_by_date):
    try:
        normalized = _normalize_items(items_by_date, strict_limits=True)
        payload = {"items_by_date": normalized}
        data_path = get_todo_data_path()
        atomic_write_json(data_path, payload, max_bytes=MAX_TODO_FILE_BYTES)
        return True
    except (JsonStoreError, OSError, TypeError, ValueError):
        return False


def load_todo_items_by_date():
    try:
        data_path = get_todo_data_path()
    except OSError:
        return _build_default_items()
    if not os.path.exists(data_path):
        default_items = _build_default_items()
        save_todo_items_by_date(default_items)
        return default_items

    try:
        payload = read_json_file(data_path, max_bytes=MAX_TODO_FILE_BYTES)
        if isinstance(payload, dict) and isinstance(payload.get("items_by_date", {}), dict):
            # 文件存在时允许返回空字典，避免用户清空待办后被默认模板覆盖。
            return _normalize_items(payload.get("items_by_date", {}))
    except JsonStoreError:
        pass

    # 保留损坏或过大的原文件供用户恢复，不用默认模板覆盖它。
    default_items = _build_default_items()
    return default_items


def complete_todo_item(date_key, ddl, text):
    """Mark one exact active item completed without deleting its content."""

    return set_todo_item_completed(date_key, ddl, text, completed=True)


def set_todo_item_completed(date_key, ddl, text, *, completed):
    """Update the completed state of one matching item and persist it."""

    items_by_date = load_todo_items_by_date()
    raw_date = str(date_key).strip()
    if len(raw_date) != 10:
        return False
    try:
        normalized_date = date.fromisoformat(raw_date).isoformat()
    except ValueError:
        return False
    normalized_target = _normalize_task_item({"ddl": ddl, "text": text})
    if normalized_target is None:
        return False

    tasks = list(items_by_date.get(normalized_date, []))
    for index, raw_task in enumerate(tasks):
        normalized_task = _normalize_task_item(raw_task)
        if normalized_task is None:
            continue
        if (
            normalized_task["ddl"] != normalized_target["ddl"]
            or normalized_task["text"] != normalized_target["text"]
            or normalized_task["completed"] is bool(completed)
        ):
            continue
        tasks[index] = {
            "ddl": normalized_task["ddl"],
            "text": normalized_task["text"],
            "completed": bool(completed),
        }
        items_by_date[normalized_date] = tasks
        return save_todo_items_by_date(items_by_date)
    return False
