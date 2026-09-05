"""DDL 时间窗口与倒计时文案，不涉及定时器、窗口或文件写入。"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import math

from .todo import MAX_TODO_TEXT_CHARS


MAX_REMINDER_WINDOW_HOURS = 24.0 * 30
MAX_SNOOZE_MINUTES = 24 * 60


@dataclass(frozen=True)
class DueTodo:
    date_key: str
    ddl: str
    text: str
    deadline: datetime


def find_due_todos(items_by_date, now: datetime, within_hours: float) -> list[DueTodo]:
    """当天逾期事项与时间窗内的未来事项参与提醒，历史逾期不永久锁住桌宠。"""

    if not isinstance(items_by_date, dict) or not isinstance(now, datetime):
        return []

    try:
        reminder_hours = float(within_hours)
    except (TypeError, ValueError, OverflowError):
        return []
    if not math.isfinite(reminder_hours):
        return []
    reminder_hours = max(0.0, min(reminder_hours, MAX_REMINDER_WINDOW_HOURS))

    window_start = datetime.combine(now.date(), time.min).replace(tzinfo=now.tzinfo)
    try:
        window_end = now + timedelta(hours=reminder_hours)
    except OverflowError:
        window_end = datetime.max.replace(tzinfo=now.tzinfo)
    matches: list[DueTodo] = []

    for raw_date, raw_tasks in items_by_date.items():
        try:
            parsed_date = date.fromisoformat(str(raw_date).strip())
        except ValueError:
            continue
        if not isinstance(raw_tasks, list):
            continue

        for raw_task in raw_tasks:
            if not isinstance(raw_task, dict):
                continue
            if raw_task.get("completed") is True:
                continue
            ddl = str(raw_task.get("ddl", "")).strip()
            text_value = str(raw_task.get("text", "")).strip()
            if (
                len(ddl) != 5
                or ddl[2] != ":"
                or not ddl[:2].isdigit()
                or not ddl[3:].isdigit()
                or not text_value
                or len(text_value) > MAX_TODO_TEXT_CHARS
                or any(ord(character) < 32 for character in text_value)
            ):
                continue
            try:
                parsed_time = time(int(ddl[:2]), int(ddl[3:]))
            except (ValueError, OverflowError):
                continue

            deadline = datetime.combine(parsed_date, parsed_time).replace(tzinfo=now.tzinfo)
            if window_start <= deadline <= window_end:
                matches.append(
                    DueTodo(
                        date_key=parsed_date.isoformat(),
                        ddl=parsed_time.strftime("%H:%M"),
                        text=text_value,
                        deadline=deadline,
                    )
                )

    matches.sort(key=lambda item: (item.deadline, item.text))
    return matches


def _remaining_text(deadline: datetime, now: datetime) -> str:
    seconds = int((deadline - now).total_seconds())
    minutes = max(1, (abs(seconds) + 59) // 60)
    hours, rest = divmod(minutes, 60)
    if hours:
        duration = f"{hours} 小时 {rest} 分钟" if rest else f"{hours} 小时"
    else:
        duration = f"{rest} 分钟"
    return f"已超时 {duration}" if seconds < 0 else f"还有 {duration}"
