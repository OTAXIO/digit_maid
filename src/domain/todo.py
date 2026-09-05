"""待办纯数据规则：时间格式、内容边界、完成属性和排序，不依赖 Qt。"""

MAX_TODO_TEXT_CHARS = 500
MAX_TODOS_PER_DATE = 500
MAX_TODO_DATES = 3660
MAX_TOTAL_TODOS = 5000


def normalize_ddl(raw_ddl):
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


def normalize_task(item):
    if isinstance(item, dict):
        text = str(item.get("text", "")).strip()
        ddl = normalize_ddl(item.get("ddl", ""))
        completed = item.get("completed") is True
    else:
        raw_text = str(item).strip().replace("：", ":")
        ddl = ""
        text = raw_text
        completed = False

        segments = raw_text.split(None, 1)
        if segments and ":" in segments[0]:
            parsed_ddl = normalize_ddl(segments[0])
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


def task_sort_key(task):
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


def parse_editor_text(raw_text, fallback_ddl):
    """接受 HH:MM 正文；无时间前缀时保留旧时间，非法输入返回中文错误。"""
    text = str(raw_text).replace("\r", "\n").replace("\n", " ").strip()
    if any(ord(character) < 32 for character in text):
        return "", "", "待办不能包含控制字符"
    if not text:
        return "", "", "待办内容不能为空"

    normalized_text = text.replace("：", ":")
    segments = normalized_text.split(None, 1)
    if segments and ":" in segments[0]:
        normalized_ddl = normalize_ddl(segments[0])
        if not normalized_ddl:
            return "", "", "DDL 格式错误，请使用 HH:MM"

        content = segments[1].strip() if len(segments) > 1 else ""
        if not content:
            return "", "", "待办内容不能为空"
        if len(content) > MAX_TODO_TEXT_CHARS:
            return "", "", f"待办内容不能超过 {MAX_TODO_TEXT_CHARS} 个字符"

        return normalized_ddl, content, ""

    if len(normalized_text) > MAX_TODO_TEXT_CHARS:
        return "", "", f"待办内容不能超过 {MAX_TODO_TEXT_CHARS} 个字符"
    return fallback_ddl, normalized_text, ""
