from datetime import date
import os
import sys

from PyQt6.QtCore import QDate, QEvent, QPoint, QRect, QSize, Qt, QTimer, QPropertyAnimation
from PyQt6.QtGui import QColor, QFont, QIcon, QTextCharFormat, QCursor
from PyQt6.QtWidgets import (
    QAbstractItemDelegate,
    QAbstractItemView,
    QApplication,
    QCalendarWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.function.todo_store import load_todo_items_by_date, save_todo_items_by_date


def _default_ui_font_family():
    if sys.platform == "darwin":
        return "PingFang SC"
    return "Microsoft YaHei"


class TodoPanel(QWidget):
    def __init__(self, on_close_callback=None, parent=None):
        super().__init__(None)
        self.owner_widget = parent
        self.on_close_callback = on_close_callback
        self.items_by_date = {}
        self._marked_dates = []
        self._month_expanded = True
        self._allow_close = False
        self._dragging = False
        self._drag_offset = QPoint()
        self._drag_handles = []
        self._fold_anim = None
        self._editing_index = None
        self._suppress_item_changed = False

        self.expanded_width = 860
        self.collapsed_width = 300
        self.panel_height = 520
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(self.collapsed_width, self.panel_height)
        self.setMaximumSize(self.expanded_width, self.panel_height)
        self.resize(self.expanded_width, self.panel_height)

        self._build_ui()
        self.reload_data()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame(self)
        card.setObjectName("todo_card")
        card_style = (
            """
            QFrame#todo_card {
                background-color: #ffffff;
                border: 4px solid #c41c1c;
                border-radius: 18px;
            }
            QFrame#todo_card * {
                font-family: "__UI_FONT_FAMILY__";
                font-weight: 700;
            }
            QLabel#title_label {
                color: #2f2220;
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#subtitle_label {
                color: #7a5b55;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#section_title {
                color: #3f2c28;
                font-size: 15px;
                font-weight: 700;
            }
            QLabel#month_caption {
                color: #8a6259;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton#close_btn {
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
                border: none;
                border-radius: 15px;
                background-color: #c41c1c;
                color: white;
                font-size: 17px;
                font-weight: 800;
            }
            QPushButton#close_btn:hover {
                background-color: #c41c1c;
            }
            QPushButton#close_btn:pressed {
                background-color: #c41c1c;
            }
            QPushButton#expand_btn {
                border: 2px solid #c41c1c;
                border-radius: 10px;
                background-color: #ffffff;
                color: #5f3d37;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#expand_btn:hover {
                background-color: #c41c1c;
            }
            QListWidget {
                background-color: #ffffff;
                border: 2px solid #c41c1c;
                border-radius: 12px;
                padding: 6px;
                font-size: 13px;
                color: #2f2220;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background-color: #c41c1c;
                color: #2f2220;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 2px solid #c41c1c;
                border-radius: 10px;
                padding: 7px 9px;
                color: #2f2220;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid #c41c1c;
            }
            QPushButton#icon_action_btn {
                min-width: 34px;
                max-width: 34px;
                min-height: 34px;
                max-height: 34px;
                border: none;
                border-radius: 8px;
                background: transparent;
            }
            QPushButton#icon_action_btn:hover {
                background-color: rgba(196, 28, 28, 30);
            }
            QCalendarWidget {
                background-color: #ffffff;
                border: 2px solid #ffd2cd;
                border-radius: 12px;
            }
            QCalendarWidget QWidget {
                alternate-background-color: #ffffff;
            }
            QCalendarWidget QToolButton {
                color: #523834;
                font-size: 14px;
                font-weight: 700;
                border: none;
                min-width: 24px;
                min-height: 24px;
                padding: 0px 10px;
            }
            QCalendarWidget QToolButton#qt_calendar_prevmonth,
            QCalendarWidget QToolButton#qt_calendar_nextmonth {
                min-width: 26px;
                max-width: 26px;
                padding: 0;
            }
            QCalendarWidget QToolButton#qt_calendar_monthbutton,
            QCalendarWidget QToolButton#qt_calendar_yearbutton {
                min-width: 88px;
                padding: 0 18px 0 8px;
                text-align: center;
            }
            QCalendarWidget QToolButton#qt_calendar_monthbutton::menu-indicator {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                right: 6px;
                top: 0px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: #3a2b28;
                background-color: #ffffff;
                selection-background-color: #ffe36e;
                selection-color: #5b4300;
                outline: 0;
            }
            /* 新增：强化日历所有子部件背景为白色 */
            QCalendarWidget QAbstractItemView {
                background-color: #ffffff;
                alternate-background-color: #ffffff;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #ffffff;
            }
            QCalendarWidget QToolButton {
                background-color: transparent;
            }
            """
        )
        card.setStyleSheet(card_style.replace("__UI_FONT_FAMILY__", _default_ui_font_family()))

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(14)

        self.header_area = QWidget(card)
        header_layout = QHBoxLayout(self.header_area)
        header_layout.setContentsMargins(0, 0, 0, 0)
        title_column = QVBoxLayout()
        title_column.setSpacing(2)

        title_label = QLabel("待办", card)
        title_label.setObjectName("title_label")
        title_column.addWidget(title_label)

        self.subtitle_label = QLabel("今日与本月计划", card)
        self.subtitle_label.setObjectName("subtitle_label")
        title_column.addWidget(self.subtitle_label)

        header_layout.addLayout(title_column)
        header_layout.addStretch(1)

        self.expand_btn = QPushButton("收起日历", card)
        self.expand_btn.setObjectName("expand_btn")
        self.expand_btn.clicked.connect(self._toggle_month_section)
        header_layout.addWidget(self.expand_btn)

        close_btn = QPushButton("×", card)
        close_btn.setObjectName("close_btn")
        close_btn.clicked.connect(self._close_from_symbol)
        header_layout.addWidget(close_btn)

        card_layout.addWidget(self.header_area)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(14)

        left_section = QFrame(card)
        left_section.setStyleSheet("QFrame { border: none; background: transparent; }")
        left_layout = QVBoxLayout(left_section)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.left_title = QLabel("每日任务", left_section)
        self.left_title.setObjectName("section_title")
        left_layout.addWidget(self.left_title)

        self.today_list = QListWidget(left_section)
        self.today_list.setViewportMargins(34, 0, 0, 0)
        self.today_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.today_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.today_list.itemClicked.connect(self._on_today_item_selected)
        self.today_list.itemChanged.connect(self._on_today_item_changed)
        self.today_list.itemDelegate().closeEditor.connect(self._on_today_editor_closed)
        self.today_list.itemSelectionChanged.connect(self._position_selected_delete_button)
        self.today_list.verticalScrollBar().valueChanged.connect(self._position_selected_delete_button)
        self.today_list.horizontalScrollBar().valueChanged.connect(self._position_selected_delete_button)
        self.today_list.viewport().installEventFilter(self)
        left_layout.addWidget(self.today_list, 1)

        self.delete_btn = QPushButton("", self.today_list)
        self.delete_btn.setObjectName("icon_action_btn")
        # self.delete_btn.setToolTip("删除当前选中事项")
        self.delete_btn.clicked.connect(self._delete_selected_item)
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.hide()
        self._apply_icon_button(self.delete_btn, "delete.png")

        input_action_row = QHBoxLayout()
        input_action_row.setSpacing(8)

        self.todo_input = QLineEdit(left_section)
        self.todo_input.setPlaceholderText("输入当日待办")
        self.todo_input.returnPressed.connect(self._submit_todo_input)
        input_action_row.addWidget(self.todo_input, 1)

        self.upload_btn = QPushButton("", left_section)
        self.upload_btn.setObjectName("icon_action_btn")
        self.upload_btn.setToolTip("上传新增事项")
        self.upload_btn.clicked.connect(self._submit_todo_input)
        self._apply_icon_button(self.upload_btn, "upload.png")
        input_action_row.addWidget(self.upload_btn)

        left_layout.addLayout(input_action_row)

        content_layout.addWidget(left_section, 1)

        self.right_section = QFrame(card)
        self.right_section.setStyleSheet("QFrame { border: none; background: transparent; }")
        right_layout = QVBoxLayout(self.right_section)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        month_title = QLabel("本月日历", self.right_section)
        month_title.setObjectName("section_title")
        right_layout.addWidget(month_title)

        self.calendar = QCalendarWidget(self.right_section)
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self.calendar.setHorizontalHeaderFormat(
            QCalendarWidget.HorizontalHeaderFormat.ShortDayNames
        )
        self.calendar.currentPageChanged.connect(self._on_calendar_page_changed)
        self.calendar.selectionChanged.connect(self._on_calendar_selection_changed)
        right_layout.addWidget(self.calendar)

        self.month_section = QWidget(self.right_section)
        month_section_layout = QVBoxLayout(self.month_section)
        month_section_layout.setContentsMargins(0, 0, 0, 0)
        month_section_layout.setSpacing(6)

        self.month_caption = QLabel("本月待办", self.month_section)
        self.month_caption.setObjectName("month_caption")
        month_section_layout.addWidget(self.month_caption)

        self.month_list = QListWidget(self.month_section)
        self.month_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        month_section_layout.addWidget(self.month_list)

        right_layout.addWidget(self.month_section, 1)

        content_layout.addWidget(self.right_section, 1)

        card_layout.addLayout(content_layout, 1)
        root_layout.addWidget(card)

        self._drag_handles = [self.header_area, title_label, self.subtitle_label]
        for handle in self._drag_handles:
            handle.installEventFilter(self)

    def _toggle_month_section(self):
        self._month_expanded = not self._month_expanded
        target_width = self.expanded_width if self._month_expanded else self.collapsed_width

        if self._month_expanded:
            self.right_section.setVisible(True)

        def _after_fold():
            if not self._month_expanded:
                self.right_section.setVisible(False)

        self._animate_width_to(target_width, on_finished=_after_fold)
        self.expand_btn.setText("收起日历" if self._month_expanded else "展开日历")

    def _resolve_screen_geometry(self, probe_point=None):
        if probe_point is None:
            probe_point = self.frameGeometry().center()

        screen = QApplication.screenAt(probe_point)
        if screen is None:
            screen = self.screen()
        if screen is None and self.owner_widget is not None:
            screen = self.owner_widget.screen()
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return QRect(0, 0, 1, 1)
        return screen.availableGeometry()

    def _clamp_top_left(self, top_left, width=None, height=None, reference_point=None):
        if width is None:
            width = self.width()
        if height is None:
            height = self.height()

        if reference_point is not None:
            probe = reference_point
        else:
            probe = QPoint(top_left.x() + width // 2, top_left.y() + height // 2)
        screen_geo = self._resolve_screen_geometry(probe)
        x = max(screen_geo.left(), min(top_left.x(), screen_geo.right() - width + 1))
        y = max(screen_geo.top(), min(top_left.y(), screen_geo.bottom() - height + 1))
        return QPoint(x, y)

    def keep_inside_screen(self, reference_point=None):
        current_top_left = self.pos()
        clamped = self._clamp_top_left(current_top_left, reference_point=reference_point)
        if clamped != current_top_left:
            self.move(clamped)

    def _start_drag(self, global_pos):
        self._dragging = True
        self._drag_offset = global_pos - self.frameGeometry().topLeft()
        mouse_grabber_getter = getattr(QWidget, "mouseGrabber", None)
        current_grabber = mouse_grabber_getter() if callable(mouse_grabber_getter) else None
        if current_grabber is not self:
            self.grabMouse()

    def _stop_drag(self):
        self._dragging = False
        mouse_grabber_getter = getattr(QWidget, "mouseGrabber", None)
        current_grabber = mouse_grabber_getter() if callable(mouse_grabber_getter) else None
        if current_grabber is self:
            self.releaseMouse()

    def _animate_width_to(self, target_width, on_finished=None):
        start_geo = self.geometry()
        clamped_top_left = self._clamp_top_left(start_geo.topLeft(), width=target_width, height=self.panel_height)
        end_geo = QRect(clamped_top_left.x(), clamped_top_left.y(), target_width, self.panel_height)

        if self._fold_anim is not None and self._fold_anim.state() == QPropertyAnimation.State.Running:
            self._fold_anim.stop()

        self._fold_anim = QPropertyAnimation(self, b"geometry", self)
        self._fold_anim.setDuration(180)
        self._fold_anim.setStartValue(start_geo)
        self._fold_anim.setEndValue(end_geo)
        if callable(on_finished):
            self._fold_anim.finished.connect(on_finished)
        self._fold_anim.start()

    def _persist_items(self):
        return save_todo_items_by_date(self.items_by_date)

    def _resolve_button_icon(self, filename):
        icon_path = os.path.join(self.root_dir, "resource", "button", filename)
        return icon_path if os.path.exists(icon_path) else None

    def _apply_icon_button(self, button, filename):
        icon_path = self._resolve_button_icon(filename)
        if icon_path:
            button.setText("")
            button.setIcon(QIcon(icon_path))
            button.setIconSize(QSize(20, 20))
            return

        button.setText(filename.split(".")[0])

    def _clear_editing_state(self, clear_input=False, clear_selection=True):
        self._editing_index = None
        if clear_selection:
            self.today_list.clearSelection()
            self.today_list.setCurrentRow(-1)
        self._position_selected_delete_button()
        if clear_input:
            self.todo_input.clear()

    def _position_selected_delete_button(self):
        if not hasattr(self, "delete_btn"):
            return

        today_items = self.items_by_date.get(self._selected_date_key(), [])
        selected_items = self.today_list.selectedItems()
        if not selected_items:
            self.delete_btn.hide()
            return

        item = selected_items[0]
        current_row = self.today_list.row(item)
        if current_row < 0 or current_row >= len(today_items):
            self.delete_btn.hide()
            return

        rect = self.today_list.visualItemRect(item)
        if not rect.isValid() or rect.height() <= 0:
            self.delete_btn.hide()
            return

        viewport_geo = self.today_list.viewport().geometry()
        if rect.bottom() < 0 or rect.top() > viewport_geo.height():
            self.delete_btn.hide()
            return

        x = max(4, viewport_geo.left() - self.delete_btn.width() - 4)
        y = viewport_geo.top() + rect.top() + max(0, (rect.height() - self.delete_btn.height()) // 2)
        self.delete_btn.move(x, y)
        self.delete_btn.raise_()
        self.delete_btn.show()

    def _set_status_text(self, text):
        self.subtitle_label.setText(text)

    def _selected_date_qdate(self):
        selected = self.calendar.selectedDate()
        if selected.isValid():
            return selected
        return QDate.currentDate()

    def _selected_date_key(self):
        return self._selected_date_qdate().toString("yyyy-MM-dd")

    def _sync_daily_section_caption(self):
        selected = self._selected_date_qdate()
        self.left_title.setText(f"每日任务 ({selected.toString('yyyy-MM-dd')})")
        self.todo_input.setPlaceholderText(
            f"输入 {selected.toString('MM-dd')} 待办"
        )

    def _submit_todo_input(self):
        text = self.todo_input.text().strip()
        if not text:
            self._set_status_text("请输入待办内容")
            return

        today_items = self.items_by_date.setdefault(self._selected_date_key(), [])
        today_items.append(text)
        status_text = "已新增事项"

        self.todo_input.clear()
        self._persist_items()
        self._refresh_today_list()
        self._refresh_calendar_marks()
        self._refresh_month_list()
        self._set_status_text(status_text)
        self._clear_editing_state(clear_input=False)

    def _delete_selected_item(self):
        today_items = self.items_by_date.get(self._selected_date_key(), [])
        if not today_items:
            self._clear_editing_state(clear_input=True)
            return

        selected_items = self.today_list.selectedItems()
        if selected_items:
            index = self.today_list.row(selected_items[0])
        else:
            index = self.today_list.currentRow()

        if index is None or index < 0 or index >= len(today_items):
            self._set_status_text("请先点击一条事项后再删除")
            return

        today_key = self._selected_date_key()

        today_items.pop(index)
        if not today_items:
            self.items_by_date.pop(today_key, None)

        self.todo_input.clear()
        self._persist_items()
        self._refresh_today_list()
        self._refresh_calendar_marks()
        self._refresh_month_list()
        self._clear_editing_state(clear_input=True)
        self._set_status_text("已删除事项")

    def _on_today_item_selected(self, item):
        index = self.today_list.row(item)
        today_items = self.items_by_date.get(self._selected_date_key(), [])
        if 0 <= index < len(today_items):
            self._editing_index = index
            self._position_selected_delete_button()
            self.today_list.editItem(item)
            QTimer.singleShot(0, self._bind_today_inline_editor)
            self._set_status_text("已进入列表内编辑")

    def _bind_today_inline_editor(self):
        editor = self.today_list.findChild(QLineEdit)
        if editor is None:
            return

        try:
            editor.returnPressed.disconnect(self._on_today_editor_return_pressed)
        except TypeError:
            pass
        editor.returnPressed.connect(self._on_today_editor_return_pressed)

    def _on_today_editor_return_pressed(self):
        self._finish_today_inline_edit(save=True, clear_selection=True)

    def _finish_today_inline_edit(self, save=True, clear_selection=True):
        editor = self.today_list.findChild(QLineEdit)
        if editor is not None:
            delegate = self.today_list.itemDelegate()
            if save:
                delegate.commitData.emit(editor)
            delegate.closeEditor.emit(editor, QAbstractItemDelegate.EndEditHint.NoHint)

        self._clear_editing_state(clear_input=False, clear_selection=clear_selection)
        self._set_status_text("已退出编辑模式")

    def _on_today_item_changed(self, item):
        if self._suppress_item_changed:
            return

        index = self.today_list.row(item)
        today_items = self.items_by_date.get(self._selected_date_key(), [])
        if index < 0 or index >= len(today_items):
            return

        new_text = item.text().strip()
        if not new_text:
            self._suppress_item_changed = True
            item.setText(today_items[index])
            self._suppress_item_changed = False
            self._set_status_text("待办内容不能为空")
            return

        if new_text == today_items[index]:
            return

        today_items[index] = new_text
        self._persist_items()
        self._refresh_calendar_marks()
        self._refresh_month_list()
        self._set_status_text("已保存修改")

    def _on_today_editor_closed(self, *_):
        self._editing_index = None
        self._position_selected_delete_button()

    def _today_key(self):
        return date.today().isoformat()

    def _month_entries(self, year, month):
        entries = []
        for date_key, tasks in self.items_by_date.items():
            try:
                parsed = date.fromisoformat(date_key)
            except ValueError:
                continue
            if parsed.year == year and parsed.month == month and tasks:
                entries.append((parsed, tasks))
        entries.sort(key=lambda x: x[0])
        return entries

    def _refresh_today_list(self):
        self.today_list.clear()
        today_items = self.items_by_date.get(self._selected_date_key(), [])

        if not today_items:
            placeholder = QListWidgetItem("该日期暂无待办")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.today_list.addItem(placeholder)
            self._clear_editing_state(clear_input=True)
            return

        self._suppress_item_changed = True
        for task in today_items:
            item = QListWidgetItem(task)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable
            )
            self.today_list.addItem(item)
        self._suppress_item_changed = False
        self._position_selected_delete_button()

    def _refresh_month_caption(self):
        year = self.calendar.yearShown()
        month = self.calendar.monthShown()
        self.month_caption.setText(f"{year}年{month}月待办")

    def _refresh_month_list(self):
        self.month_list.clear()
        year = self.calendar.yearShown()
        month = self.calendar.monthShown()
        entries = self._month_entries(year, month)

        if not entries:
            placeholder = QListWidgetItem("本月暂无待办")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.month_list.addItem(placeholder)
            return

        for day, tasks in entries:
            for task in tasks:
                self.month_list.addItem(f"{day.day:02d}日  {task}")

    def _refresh_calendar_marks(self):
        for marked_date in self._marked_dates:
            self.calendar.setDateTextFormat(marked_date, QTextCharFormat())
        self._marked_dates.clear()

        shown_year = self.calendar.yearShown()
        shown_month = self.calendar.monthShown()
        first_day = QDate(shown_year, shown_month, 1)
        if not first_day.isValid():
            return
        day_count = first_day.daysInMonth()

        # 日历可视网格里的“非本月”日期统一用浅灰底色。
        first_week_day = self.calendar.firstDayOfWeek()
        first_week_day_num = int(getattr(first_week_day, "value", first_week_day))
        leading_days = (first_day.dayOfWeek() - first_week_day_num + 7) % 7
        grid_start = first_day.addDays(-leading_days)

        out_month_format = QTextCharFormat()
        out_month_format.setBackground(QColor("#f1f1f1"))
        out_month_format.setForeground(QColor("#2f2220"))

        for idx in range(42):
            qdate = grid_start.addDays(idx)
            if qdate.year() == shown_year and qdate.month() == shown_month:
                continue
            self.calendar.setDateTextFormat(qdate, out_month_format)
            self._marked_dates.append(qdate)

        month_light_format = QTextCharFormat()
        month_light_format.setBackground(QColor("#fff1ef"))
        month_light_format.setForeground(QColor("#2f2220"))

        for day in range(1, day_count + 1):
            qdate = QDate(shown_year, shown_month, day)
            self.calendar.setDateTextFormat(qdate, month_light_format)
            self._marked_dates.append(qdate)

        task_format = QTextCharFormat()
        task_format.setBackground(QColor("#ffcdc8"))
        task_format.setForeground(QColor("#2f2220"))

        for date_key, tasks in self.items_by_date.items():
            if not tasks:
                continue
            try:
                parsed = date.fromisoformat(date_key)
            except ValueError:
                continue

            if parsed.year != shown_year or parsed.month != shown_month:
                continue

            qdate = QDate(parsed.year, parsed.month, parsed.day)
            self.calendar.setDateTextFormat(qdate, task_format)
            self._marked_dates.append(qdate)

        today = QDate.currentDate()
        if today.year() == shown_year and today.month() == shown_month:
            today_format = QTextCharFormat()
            today_format.setBackground(QColor("#ff9a91"))
            today_format.setForeground(QColor("#2f2220"))
            self.calendar.setDateTextFormat(today, today_format)
            self._marked_dates.append(today)

        selected = self.calendar.selectedDate()
        if selected.isValid():
            selected_format = QTextCharFormat()
            selected_format.setBackground(QColor("#ffe36e"))
            selected_format.setForeground(QColor("#2f2220"))
            self.calendar.setDateTextFormat(selected, selected_format)
            self._marked_dates.append(selected)

    def _on_calendar_page_changed(self, year, month):
        self._refresh_month_caption()
        self._refresh_month_list()
        self._refresh_calendar_marks()

    def _on_calendar_selection_changed(self):
        selected = self.calendar.selectedDate()
        self._clear_editing_state(clear_input=True)
        self._sync_daily_section_caption()
        self._refresh_today_list()
        self._refresh_calendar_marks()
        self.subtitle_label.setText(f"选中日期: {selected.toString('yyyy-MM-dd')}（已与月份待办同步）")

    def reload_data(self):
        self.items_by_date = load_todo_items_by_date()
        self._clear_editing_state(clear_input=True)
        self._refresh_today_list()
        self._refresh_calendar_marks()
        self._refresh_month_caption()
        self._refresh_month_list()
        self.calendar.setSelectedDate(QDate.currentDate())
        self._sync_daily_section_caption()
        self._refresh_today_list()
        if self._month_expanded:
            self.resize(self.expanded_width, self.panel_height)
            self.right_section.setVisible(True)
            self.expand_btn.setText("收起日历")
        else:
            self.resize(self.collapsed_width, self.panel_height)
            self.right_section.setVisible(False)
            self.expand_btn.setText("展开日历")

    def _close_from_symbol(self):
        self._stop_drag()
        if callable(self.on_close_callback):
            self.on_close_callback()
        self._allow_close = True
        self.close()
        self._allow_close = False

    def eventFilter(self, obj, event):
        if obj is self.today_list.viewport():
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                pos = event.position().toPoint()
                if self.today_list.itemAt(pos) is None:
                    editor = self.today_list.findChild(QLineEdit)
                    if editor is not None:
                        self._finish_today_inline_edit(save=True, clear_selection=True)

        if obj in self._drag_handles:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._start_drag(event.globalPosition().toPoint())
                event.accept()
                return True

            if event.type() == QEvent.Type.MouseMove and self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
                new_top_left = event.globalPosition().toPoint() - self._drag_offset
                clamped = self._clamp_top_left(new_top_left, reference_point=event.globalPosition().toPoint())
                self.move(clamped)
                event.accept()
                return True

            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._stop_drag()
                event.accept()
                return True

        return super().eventFilter(obj, event)

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            new_top_left = event.globalPosition().toPoint() - self._drag_offset
            clamped = self._clamp_top_left(new_top_left, reference_point=event.globalPosition().toPoint())
            self.move(clamped)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._stop_drag()
        super().mouseReleaseEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.keep_inside_screen(reference_point=QCursor.pos())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self._stop_drag()
        app = QApplication.instance()
        app_closing = bool(app.closingDown()) if app is not None else False
        if not self._allow_close and not app_closing:
            event.ignore()
            return
        super().closeEvent(event)