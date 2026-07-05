import json
import os
from datetime import date, timedelta

from PyQt6.QtCore import QStandardPaths


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
    else:
        raw_text = str(item).strip().replace("：", ":")
        ddl = ""
        text = raw_text

        segments = raw_text.split(None, 1)
        if segments and ":" in segments[0]:
            parsed_ddl = _normalize_ddl_time(segments[0])
            if parsed_ddl:
                ddl = parsed_ddl
                text = segments[1].strip() if len(segments) > 1 else ""

    if not text:
        return None

    return {"ddl": ddl, "text": text}


def _task_sort_key(task):
    ddl = str(task.get("ddl", "")).strip()
    if ddl:
        try:
            hour_str, minute_str = ddl.split(":", 1)
            minute_of_day = int(hour_str) * 60 + int(minute_str)
            return (0, minute_of_day, task.get("text", ""))
        except ValueError:
            pass
    return (1, 24 * 60, task.get("text", ""))


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


def _normalize_items(items_by_date):
    normalized = {}
    if not isinstance(items_by_date, dict):
        return normalized

    for date_key, values in items_by_date.items():
        try:
            normalized_date = date.fromisoformat(str(date_key).strip()).isoformat()
        except ValueError:
            continue

        if isinstance(values, str):
            raw_items = [values]
        elif isinstance(values, list):
            raw_items = values
        else:
            continue

        cleaned_items = []
        for item in raw_items:
            normalized_item = _normalize_task_item(item)
            if normalized_item is not None:
                cleaned_items.append(normalized_item)

        if cleaned_items:
            normalized[normalized_date] = sorted(cleaned_items, key=_task_sort_key)

    return normalized


def save_todo_items_by_date(items_by_date):
    normalized = _normalize_items(items_by_date)
    payload = {"items_by_date": normalized}
    data_path = get_todo_data_path()
    try:
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def load_todo_items_by_date():
    data_path = get_todo_data_path()
    if not os.path.exists(data_path):
        default_items = _build_default_items()
        save_todo_items_by_date(default_items)
        return default_items

    try:
        with open(data_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        raw_items = payload.get("items_by_date", {})
        if isinstance(raw_items, dict):
            # 文件存在时允许返回空字典，避免用户清空待办后被默认模板覆盖。
            return _normalize_items(raw_items)
    except Exception:
        pass

    default_items = _build_default_items()
    save_todo_items_by_date(default_items)
    return default_items
