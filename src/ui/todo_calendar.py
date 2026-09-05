"""日历色彩标记，与待办编辑及数据持久化分开维护。"""

from datetime import date
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QTextCharFormat, QIcon
from PyQt6.QtWidgets import QCalendarWidget, QToolButton
from src.ui.theme import P


class TodoCalendar(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._marked_dates = []
        # 使用文字箭头，避免系统主题注入绿色导航图标破坏统一配色。
        for name, text in (("qt_calendar_prevmonth", "‹"), ("qt_calendar_nextmonth", "›")):
            button = self.findChild(QToolButton, name)
            if button is not None:
                button.setIcon(QIcon())
                button.setArrowType(Qt.ArrowType.NoArrow)
                button.setText(text)

    def refresh_marks(self, items_by_date):
        for marked_date in self._marked_dates:
            self.setDateTextFormat(marked_date, QTextCharFormat())
        self._marked_dates.clear()

        shown_year = self.yearShown()
        shown_month = self.monthShown()
        first_day = QDate(shown_year, shown_month, 1)
        if not first_day.isValid():
            return
        day_count = first_day.daysInMonth()

        # 日历可视网格里的“非本月”日期统一用浅灰底色。
        first_week_day = self.firstDayOfWeek()
        first_week_day_num = int(getattr(first_week_day, "value", first_week_day))
        leading_days = (first_day.dayOfWeek() - first_week_day_num + 7) % 7
        # QCalendarWidget 在 1 号恰好位于每周首列时，会额外显示上一周作为首行。
        if leading_days == 0:
            leading_days = 7
        grid_start = first_day.addDays(-leading_days)

        out_month_format = QTextCharFormat()
        out_month_format.setBackground(QColor(P.inset))
        out_month_format.setForeground(QColor(P.faint))

        for idx in range(42):
            qdate = grid_start.addDays(idx)
            if qdate.year() == shown_year and qdate.month() == shown_month:
                continue
            date_format = QTextCharFormat(out_month_format)
            if qdate.dayOfWeek() in (6, 7):
                date_format.setForeground(QColor(P.weekend))
            self.setDateTextFormat(qdate, date_format)
            self._marked_dates.append(qdate)

        month_light_format = QTextCharFormat()
        month_light_format.setBackground(QColor(P.surface))
        month_light_format.setForeground(QColor(P.ink))

        for day in range(1, day_count + 1):
            qdate = QDate(shown_year, shown_month, day)
            date_format = QTextCharFormat(month_light_format)
            if qdate.dayOfWeek() in (6, 7):
                date_format.setForeground(QColor(P.weekend))
            self.setDateTextFormat(qdate, date_format)
            self._marked_dates.append(qdate)

        task_format = QTextCharFormat()
        task_format.setBackground(QColor(P.accent_soft))
        task_format.setForeground(QColor(P.accent))

        for date_key, tasks in items_by_date.items():
            if not tasks:
                continue
            try:
                parsed = date.fromisoformat(date_key)
            except ValueError:
                continue

            if parsed.year != shown_year or parsed.month != shown_month:
                continue

            qdate = QDate(parsed.year, parsed.month, parsed.day)
            date_format = QTextCharFormat(task_format)
            if qdate.dayOfWeek() in (6, 7):
                date_format.setForeground(QColor(P.weekend))
            self.setDateTextFormat(qdate, date_format)
            self._marked_dates.append(qdate)

        today = QDate.currentDate()
        if today.year() == shown_year and today.month() == shown_month:
            today_format = QTextCharFormat()
            today_format.setBackground(QColor(P.amber_soft))
            today_format.setForeground(
                QColor(P.weekend if today.dayOfWeek() in (6, 7) else P.amber)
            )
            self.setDateTextFormat(today, today_format)
            self._marked_dates.append(today)

        selected = self.selectedDate()
        if selected.isValid():
            selected_format = QTextCharFormat()
            selected_format.setBackground(QColor(P.accent))
            selected_format.setForeground(QColor(P.white))
            self.setDateTextFormat(selected, selected_format)
            self._marked_dates.append(selected)
