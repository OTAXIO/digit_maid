"""日历色彩标记与单元格绘制，与待办编辑及数据持久化分开维护。"""

from datetime import date
from PyQt6.QtCore import QDate, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QIcon, QPalette
from PyQt6.QtWidgets import QCalendarWidget, QToolButton, QSpinBox, QWidget
from src.ui.theme import P, default_ui_font_family
from src.ui.theme.styles import CALENDAR_MONTH_MENU, CALENDAR_YEAR_EDITOR


class TodoCalendar(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._marked_dates = []
        # 日期 -> 是否仍有未完成事项；绘制时据此决定圆点颜色。
        self._task_dates = {}
        # 使用文字箭头，避免系统主题注入绿色导航图标破坏统一配色。
        for name, text in (("qt_calendar_prevmonth", "‹"), ("qt_calendar_nextmonth", "›")):
            button = self.findChild(QToolButton, name)
            if button is not None:
                button.setIcon(QIcon())
                button.setArrowType(Qt.ArrowType.NoArrow)
                button.setText(text)
        self._arrange_navigation_bar()

        header_format = QTextCharFormat()
        header_format.setForeground(QColor(P.muted))
        header_format.setFontPointSize(8.5)
        self.setHeaderTextFormat(header_format)

        # 月份使用独立 QMenu，年份使用内嵌 QSpinBox；它们不会完整继承
        # 日历网格的背景。显式设置两者，避免系统深色主题造成黑底深色字。
        month_button = self.findChild(QToolButton, "qt_calendar_monthbutton")
        year_editor = self.findChild(QSpinBox, "qt_calendar_yearedit")
        month_menu = month_button.menu() if month_button is not None else None
        for widget, style in ((month_menu, CALENDAR_MONTH_MENU), (year_editor, CALENDAR_YEAR_EDITOR)):
            if widget is None:
                continue
            palette = widget.palette()
            for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Base, QPalette.ColorRole.Button):
                palette.setColor(role, QColor(P.white))
            for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
                palette.setColor(role, QColor(P.ink))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(P.accent_soft))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(P.ink))
            widget.setPalette(palette)
            widget.setStyleSheet(style)

    def _arrange_navigation_bar(self):
        """把“年 月”作为标题靠左，翻页箭头并排靠右，替代 Qt 默认的分散布局。"""
        navigation = self.findChild(QWidget, "qt_calendar_navigationbar")
        layout = navigation.layout() if navigation is not None else None
        if layout is None:
            return
        buttons = {name: self.findChild(QToolButton, name) for name in (
            "qt_calendar_yearbutton", "qt_calendar_monthbutton",
            "qt_calendar_prevmonth", "qt_calendar_nextmonth")}
        if None in buttons.values():
            return
        while layout.count():
            layout.takeAt(0)
        layout.setContentsMargins(0, 0, 0, 6)
        layout.setSpacing(4)
        layout.addWidget(buttons["qt_calendar_yearbutton"])
        layout.addWidget(buttons["qt_calendar_monthbutton"])
        layout.addStretch(1)
        layout.addWidget(buttons["qt_calendar_prevmonth"])
        layout.addWidget(buttons["qt_calendar_nextmonth"])

    def refresh_marks(self, items_by_date):
        """文字颜色仍写入 dateTextFormat，形状与圆点由 paintCell 统一绘制。"""
        for marked_date in self._marked_dates:
            self.setDateTextFormat(marked_date, QTextCharFormat())
        self._marked_dates.clear()
        self._task_dates.clear()

        shown_year = self.yearShown()
        shown_month = self.monthShown()
        first_day = QDate(shown_year, shown_month, 1)
        if not first_day.isValid():
            return
        day_count = first_day.daysInMonth()

        first_week_day = self.firstDayOfWeek()
        first_week_day_num = int(getattr(first_week_day, "value", first_week_day))
        leading_days = (first_day.dayOfWeek() - first_week_day_num + 7) % 7
        # QCalendarWidget 在 1 号恰好位于每周首列时，会额外显示上一周作为首行。
        if leading_days == 0:
            leading_days = 7
        grid_start = first_day.addDays(-leading_days)

        # 非本月日期一律淡化，不再用灰色底条把网格切成几段。
        out_month_format = QTextCharFormat()
        out_month_format.setForeground(QColor(P.faint))
        for idx in range(42):
            qdate = grid_start.addDays(idx)
            if qdate.year() == shown_year and qdate.month() == shown_month:
                continue
            self.setDateTextFormat(qdate, out_month_format)
            self._marked_dates.append(qdate)

        for day in range(1, day_count + 1):
            qdate = QDate(shown_year, shown_month, day)
            date_format = QTextCharFormat()
            date_format.setForeground(QColor(P.weekend if qdate.dayOfWeek() in (6, 7) else P.ink))
            self.setDateTextFormat(qdate, date_format)
            self._marked_dates.append(qdate)

        for date_key, tasks in items_by_date.items():
            if not tasks:
                continue
            try:
                parsed = date.fromisoformat(date_key)
            except ValueError:
                continue
            qdate = QDate(parsed.year, parsed.month, parsed.day)
            self._task_dates[qdate] = any(
                not (isinstance(task, dict) and task.get("completed") is True) for task in tasks
            )

        today = QDate.currentDate()
        if today.year() == shown_year and today.month() == shown_month:
            today_format = QTextCharFormat()
            today_format.setForeground(QColor(P.weekend if today.dayOfWeek() in (6, 7) else P.amber))
            today_format.setFontWeight(QFont.Weight.DemiBold)
            self.setDateTextFormat(today, today_format)
        self.updateCells()

    def paintCell(self, painter, rect, qdate):
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        painter.fillRect(rect, QColor(P.surface))

        selected = qdate == self.selectedDate()
        is_today = qdate == QDate.currentDate()
        in_month = qdate.year() == self.yearShown() and qdate.month() == self.monthShown()
        text_format = self.dateTextFormat(qdate)

        width = min(rect.width() - 8, 36)
        height = min(rect.height() - 2, 34)
        pill = QRectF(rect.center().x() - width / 2 + 0.5, rect.center().y() - height / 2 + 0.5, width, height)
        if selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(P.accent))
            painter.drawRoundedRect(pill, 10, 10)
        elif is_today and in_month:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(P.amber_soft))
            painter.drawRoundedRect(pill, 10, 10)

        if selected:
            text_color = QColor(P.white)
        elif text_format.hasProperty(QTextCharFormat.Property.ForegroundBrush):
            text_color = text_format.foreground().color()
        else:
            text_color = QColor(P.ink if in_month else P.faint)
        font = QFont(default_ui_font_family())
        font.setPixelSize(13)
        if selected or is_today:
            font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(text_color)
        has_tasks = qdate in self._task_dates
        text_rect = pill.adjusted(0, 0, 0, -6) if has_tasks else pill
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, str(qdate.day()))

        if has_tasks:
            pending = self._task_dates[qdate]
            if selected:
                dot_color = QColor(P.white)
            else:
                dot_color = QColor(P.accent if pending else P.faint)
            if not in_month:
                dot_color.setAlpha(110)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(dot_color)
            painter.drawEllipse(QRectF(pill.center().x() - 2, pill.bottom() - 7, 4, 4))
        painter.restore()
