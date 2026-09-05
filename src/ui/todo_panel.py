"""待办交互控制：列表、整页编辑和日历联动；样式统一在 ui.theme。"""

from datetime import date
from copy import deepcopy

from PyQt6.QtCore import QDate, QEvent, QLocale, QPoint, QRect, QSize, Qt, QTime, QTimer, QPropertyAnimation
from PyQt6.QtGui import QBrush, QColor, QTextCharFormat, QCursor, QTextOption
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.domain.todo import normalize_ddl, normalize_task, task_sort_key, parse_editor_text
from src.ui.theme import P
from src.ui.theme.styles import TODO
from src.ui.theme.widgets import character_badge, apply_shadow
from src.ui.todo_delegate import TodoItemDelegate
from src.ui.todo_calendar import TodoCalendar
from src.function.todo_store import (
    MAX_TODO_DATES,
    MAX_TODO_TEXT_CHARS,
    MAX_TODOS_PER_DATE,
    MAX_TOTAL_TODOS,
    load_todo_items_by_date,
    save_todo_items_by_date,
)


WEEKEND_TEXT_COLOR = P.weekend
MAX_TODO_EDITOR_CHARS = MAX_TODO_TEXT_CHARS + 16


class TodoPanel(QWidget):
    def __init__(self, on_close_callback=None, parent=None):
        super().__init__(None)
        self.owner_widget = parent
        self.on_close_callback = on_close_callback
        self.items_by_date = {}
        self._month_expanded = True
        self._allow_close = False
        self._dragging = False
        self._drag_offset = QPoint()
        self._drag_handles = []
        self._drag_border_margin = 10
        self._fold_anim = None
        self._editing_index = None
        self._editing_date_key = None
        self._last_editing_index = None
        self._editor_populating = False
        self._edit_save_timer = QTimer(self)
        self._edit_save_timer.setSingleShot(True)
        self._edit_save_timer.setInterval(600)
        self._edit_save_timer.timeout.connect(self._save_current_editor)
        self._today_page_size = 4
        self._today_page_index = 0
        self._today_visible_indexes = []

        self.expanded_width = 940
        self.collapsed_width = 440
        self.panel_height = 620

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("维维美 · 待办手账")
        self.setMinimumSize(self.collapsed_width, self.panel_height)
        self.setMaximumSize(self.expanded_width, self.panel_height)
        self.resize(self.expanded_width, self.panel_height)

        self._build_ui()
        self.reload_data()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)

        card = QFrame(self)
        card.setObjectName("todo_card")
        card.setStyleSheet(TODO)
        apply_shadow(card)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 22, 24, 24)
        card_layout.setSpacing(18)

        self.header_area = QWidget(card)
        header_layout = QHBoxLayout(self.header_area)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        close_btn = QPushButton("×", card)
        close_btn.setObjectName("close_btn")
        close_btn.setToolTip("关闭待办")
        close_btn.clicked.connect(self._close_from_symbol)
        header_layout.addWidget(character_badge(card, 46))

        title_column = QVBoxLayout()
        title_column.setSpacing(2)

        brand_label = QLabel("VIVI  /  DAILY COMPANION", card)
        brand_label.setProperty("role", "eyebrow")
        title_column.addWidget(brand_label)

        title_label = QLabel("待办手账", card)
        title_label.setObjectName("title_label")
        title_column.addWidget(title_label)

        self.subtitle_label = QLabel("今日与本月计划", card)
        self.subtitle_label.setObjectName("subtitle_label")
        self.subtitle_label.setWordWrap(True)
        title_column.addWidget(self.subtitle_label)

        header_layout.addLayout(title_column)
        header_layout.addStretch(1)

        self.expand_btn = QPushButton("收起日历", card)
        self.expand_btn.setObjectName("secondary_btn")
        self.expand_btn.clicked.connect(self._toggle_month_section)
        header_layout.addWidget(self.expand_btn)

        self.today_btn = QPushButton("回到今天", card)
        self.today_btn.setObjectName("secondary_btn")
        self.today_btn.clicked.connect(self._go_to_today)
        header_layout.addWidget(self.today_btn)
        header_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignTop)

        card_layout.addWidget(self.header_area)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(14)

        left_section = QFrame(card)
        left_section.setObjectName("section_card")
        left_layout = QVBoxLayout(left_section)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(10)

        self.left_title = QLabel("每日任务", left_section)
        self.left_title.setObjectName("section_title")
        left_layout.addWidget(self.left_title)

        self.daily_summary = QLabel(left_section)
        self.daily_summary.setObjectName("daily_summary")
        left_layout.addWidget(self.daily_summary)

        self.daily_stack = QStackedWidget(left_section)

        self.task_list_page = QWidget(self.daily_stack)
        list_page_layout = QVBoxLayout(self.task_list_page)
        list_page_layout.setContentsMargins(0, 0, 0, 0)
        list_page_layout.setSpacing(8)

        self.today_list = QListWidget(self.task_list_page)
        self.today_list.setViewportMargins(0, 0, 0, 0)
        self.today_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.today_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.today_list.setWordWrap(True)
        self.today_list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.today_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.today_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.today_list.setAccessibleName("每日任务，点击进入编辑")
        self.today_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.today_list.setItemDelegate(TodoItemDelegate(self.today_list))
        self.today_list.setMouseTracking(True)

        self.today_list.itemClicked.connect(self._on_today_item_selected)
        self.today_list.viewport().installEventFilter(self)
        list_page_layout.addWidget(self.today_list, 1)

        page_row = QHBoxLayout()
        page_row.setContentsMargins(0, 0, 0, 0)
        page_row.setSpacing(6)

        self.prev_page_btn = QPushButton("上一页", self.task_list_page)
        self.prev_page_btn.setObjectName("todo_page_btn")
        self.prev_page_btn.clicked.connect(self._go_prev_today_page)
        page_row.addWidget(self.prev_page_btn)

        self.today_page_label = QLabel("1/1", self.task_list_page)
        self.today_page_label.setObjectName("todo_page_label")
        page_row.addWidget(self.today_page_label)

        self.next_page_btn = QPushButton("下一页", self.task_list_page)
        self.next_page_btn.setObjectName("todo_page_btn")
        self.next_page_btn.clicked.connect(self._go_next_today_page)
        page_row.addWidget(self.next_page_btn)

        page_row.addStretch(1)
        list_page_layout.addLayout(page_row)
        self.daily_stack.addWidget(self.task_list_page)

        self.task_editor_page = QFrame(self.daily_stack)
        self.task_editor_page.setObjectName("task_editor_page")
        editor_layout = QVBoxLayout(self.task_editor_page)
        editor_layout.setContentsMargins(12, 12, 12, 12)
        editor_layout.setSpacing(10)

        editor_header = QHBoxLayout()
        editor_header.setContentsMargins(0, 0, 0, 0)
        self.edit_state_badge = QLabel("待完成", self.task_editor_page)
        self.edit_state_badge.setObjectName("editor_state_badge")
        editor_header.addWidget(self.edit_state_badge)
        editor_header.addStretch(1)
        self.back_to_list_btn = QPushButton("← 返回列表", self.task_editor_page)
        self.back_to_list_btn.setObjectName("back_to_list_btn")
        self.back_to_list_btn.clicked.connect(self._leave_task_editor)
        editor_header.addWidget(self.back_to_list_btn)
        editor_layout.addLayout(editor_header)

        self.task_editor = QTextEdit(self.task_editor_page)
        self.task_editor.setObjectName("task_editor")
        self.task_editor.setAcceptRichText(False)
        self.task_editor.setWordWrapMode(
            QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere
        )
        self.task_editor.setPlaceholderText("输入 HH:MM 和待办内容")
        self.task_editor.setAccessibleName("任务时间与内容")
        self.task_editor.setTabChangesFocus(True)
        self.task_editor.textChanged.connect(self._on_task_editor_text_changed)
        editor_layout.addWidget(self.task_editor, 1)

        self.editor_hint = QLabel(
            "修改会自动保存；时间格式为 HH:MM。",
            self.task_editor_page,
        )
        self.editor_hint.setObjectName("editor_hint")
        self.editor_hint.setWordWrap(True)
        editor_layout.addWidget(self.editor_hint)

        editor_actions = QHBoxLayout()
        editor_actions.setContentsMargins(0, 0, 0, 0)
        editor_actions.setSpacing(9)

        self.delete_btn = QPushButton("删除", self.task_editor_page)
        self.delete_btn.setObjectName("delete_task_btn")
        self.delete_btn.setToolTip("删除当前事项")
        self.delete_btn.clicked.connect(self._delete_selected_item)
        editor_actions.addWidget(self.delete_btn, 1)

        self.complete_btn = QPushButton("已完成", self.task_editor_page)
        self.complete_btn.setObjectName("complete_task_btn")
        self.complete_btn.setToolTip("标记为已完成")
        self.complete_btn.clicked.connect(self._toggle_selected_completion)
        editor_actions.addWidget(self.complete_btn, 1)
        editor_layout.addLayout(editor_actions)

        self.daily_stack.addWidget(self.task_editor_page)
        self.daily_stack.setCurrentWidget(self.task_list_page)
        left_layout.addWidget(self.daily_stack, 1)

        self.input_card = QFrame(left_section)
        self.input_card.setObjectName("input_card")
        input_action_row = QHBoxLayout(self.input_card)
        input_action_row.setContentsMargins(7, 7, 7, 7)
        input_action_row.setSpacing(8)

        self.ddl_input = QLineEdit(left_section)
        self.ddl_input.setObjectName("ddl_input")
        self.ddl_input.setPlaceholderText("DDL HH:MM")
        self.ddl_input.setText(self._default_ddl_text())
        self.ddl_input.returnPressed.connect(self._submit_todo_input)
        self.ddl_input.setMaxLength(5)
        input_action_row.addWidget(self.ddl_input)

        self.todo_input = QLineEdit(left_section)
        self.todo_input.setObjectName("todo_input")
        self.todo_input.setPlaceholderText("输入当日待办")
        self.todo_input.returnPressed.connect(self._submit_todo_input)
        self.todo_input.setMaxLength(MAX_TODO_TEXT_CHARS)
        input_action_row.addWidget(self.todo_input, 1)

        self.upload_btn = QPushButton("+", left_section)
        self.upload_btn.setObjectName("icon_action_btn")
        self.upload_btn.setToolTip("添加事项（回车）")
        self.upload_btn.setAccessibleName("添加事项")
        self.upload_btn.clicked.connect(self._submit_todo_input)
        input_action_row.addWidget(self.upload_btn)

        left_layout.addWidget(self.input_card)

        content_layout.addWidget(left_section, 1)

        self.right_section = QFrame(card)
        self.right_section.setObjectName("section_card")
        right_layout = QVBoxLayout(self.right_section)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(10)

        month_title = QLabel("本月日历", self.right_section)
        month_title.setObjectName("section_title")
        right_layout.addWidget(month_title)

        self.calendar = TodoCalendar(self.right_section)
        self.calendar.setLocale(QLocale(QLocale.Language.Chinese, QLocale.Country.China))
        self.calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(
            TodoCalendar.VerticalHeaderFormat.NoVerticalHeader
        )
        self.calendar.setHorizontalHeaderFormat(
            TodoCalendar.HorizontalHeaderFormat.ShortDayNames
        )
        weekend_format = QTextCharFormat()
        weekend_format.setForeground(QColor(WEEKEND_TEXT_COLOR))
        self.calendar.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, weekend_format)
        self.calendar.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, weekend_format)
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
        self.month_list.setWordWrap(True)
        self.month_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
        self.today_btn.setVisible(self._month_expanded)

    def _go_to_today(self):
        today = QDate.currentDate()
        self.calendar.setCurrentPage(today.year(), today.month())
        self.calendar.setSelectedDate(today)

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

    def _is_border_drag(self, local_pos):
        margin = self._drag_border_margin
        rect = self.rect()
        if rect.width() <= margin * 2 or rect.height() <= margin * 2:
            return False
        return (
            local_pos.x() <= margin
            or local_pos.x() >= rect.width() - margin - 1
            or local_pos.y() <= margin
            or local_pos.y() >= rect.height() - margin - 1
        )

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

    def _clear_editing_state(self, clear_input=False, clear_selection=True):
        self._edit_save_timer.stop()
        self._editing_index = None
        self._editing_date_key = None
        self._last_editing_index = None
        if clear_selection:
            self.today_list.clearSelection()
            self.today_list.setCurrentRow(-1)
        if hasattr(self, "daily_stack"):
            self.daily_stack.setCurrentWidget(self.task_list_page)
        if hasattr(self, "input_card"):
            self.input_card.show()
        if hasattr(self, "left_title") and hasattr(self, "calendar"):
            self._sync_daily_section_caption()
        if clear_input:
            self.todo_input.clear()
            if hasattr(self, "ddl_input"):
                self.ddl_input.setText(self._default_ddl_text())

    @staticmethod
    def _refresh_dynamic_style(widget):
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def _set_editor_feedback(self, message, *, error=False):
        self.editor_hint.setText(message)
        self.editor_hint.setProperty("error", bool(error))
        self._refresh_dynamic_style(self.editor_hint)

    def _apply_task_editor_state(self, task, *, feedback=None):
        completed = task.get("completed") is True
        self.task_editor.setReadOnly(completed)
        self.task_editor.setProperty("completed", completed)
        self.complete_btn.setProperty("completed", completed)
        self.edit_state_badge.setProperty("completed", completed)
        self.complete_btn.setText("未完成" if completed else "已完成")
        self.complete_btn.setToolTip(
            "恢复为未完成" if completed else "保存修改并标记为已完成"
        )
        self.edit_state_badge.setText("已完成" if completed else "待完成")
        self._refresh_dynamic_style(self.task_editor)
        self._refresh_dynamic_style(self.complete_btn)
        self._refresh_dynamic_style(self.edit_state_badge)

        if feedback is not None:
            self._set_editor_feedback(feedback)
        elif completed:
            self._set_editor_feedback("内容已锁定；可删除或恢复为未完成。")
        else:
            self._set_editor_feedback("修改会自动保存；时间格式为 HH:MM。")

    def _open_task_editor(self, date_key, index):
        tasks = self._ensure_date_items(date_key)
        if index < 0 or index >= len(tasks):
            self._set_status_text("未能定位当前事项，请重新选择")
            return False

        task = self._normalize_task_item(tasks[index])
        self._edit_save_timer.stop()
        self._editing_date_key = date_key
        self._editing_index = index
        self._last_editing_index = index

        editor_text = f"{task['ddl']} {task['text']}" if task["ddl"] else task["text"]
        self._editor_populating = True
        self.task_editor.setPlainText(editor_text)
        cursor = self.task_editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.task_editor.setTextCursor(cursor)
        self._editor_populating = False

        self._apply_task_editor_state(task)
        self.daily_stack.setCurrentWidget(self.task_editor_page)
        self.input_card.hide()
        self.left_title.setText(f"编辑任务 · {date_key}")
        self._set_status_text(
            "已完成事项只能删除或恢复为未完成"
            if task["completed"]
            else "正在编辑，修改会自动保存"
        )
        if not task["completed"]:
            QTimer.singleShot(0, self.task_editor.setFocus)
        return True

    def _on_task_editor_text_changed(self):
        if self._editor_populating or self.task_editor.isReadOnly():
            return

        text = self.task_editor.toPlainText()
        if len(text) > MAX_TODO_EDITOR_CHARS:
            self._editor_populating = True
            self.task_editor.setPlainText(text[:MAX_TODO_EDITOR_CHARS])
            cursor = self.task_editor.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.task_editor.setTextCursor(cursor)
            self._editor_populating = False
            self._set_editor_feedback(
                f"输入已限制为 {MAX_TODO_TEXT_CHARS} 个正文字符。",
                error=True,
            )
        else:
            self._set_editor_feedback("正在输入…")
        self._edit_save_timer.start()

    def _save_current_editor(self):
        self._edit_save_timer.stop()
        date_key = self._editing_date_key
        index = self._editing_index
        if date_key is None or index is None:
            return True

        tasks = self._ensure_date_items(date_key)
        if index < 0 or index >= len(tasks):
            self._set_editor_feedback("事项已发生变化，请返回列表后重新选择。", error=True)
            return False

        old_task = self._normalize_task_item(tasks[index])
        if old_task["completed"]:
            return True

        new_ddl, new_text, error_text = self._parse_editor_text(
            self.task_editor.toPlainText(),
            old_task["ddl"],
        )
        if error_text:
            self._set_editor_feedback(error_text, error=True)
            self._set_status_text(error_text)
            return False

        updated_task = {"ddl": new_ddl, "text": new_text, "completed": False}
        if updated_task == old_task:
            self._set_editor_feedback("没有未保存的修改。")
            return True

        previous_items = deepcopy(self.items_by_date)
        tasks[index] = updated_task
        tasks.sort(key=self._task_sort_key)
        self.items_by_date[date_key] = tasks
        new_index = next(
            (task_index for task_index, task in enumerate(tasks) if task is updated_task),
            index,
        )
        self._editing_index = new_index
        self._last_editing_index = new_index

        if not self._persist_items():
            self.items_by_date = previous_items
            self._editing_index = index
            self._last_editing_index = index
            self._set_editor_feedback("保存失败，请检查数据目录权限后重试。", error=True)
            self._set_status_text("保存失败，修改未生效")
            return False

        # 切换日期期间只刷新数据标记；空的新日期不能清除旧编辑上下文。
        if self._selected_date_key() == date_key:
            self._refresh_today_list()
        self._refresh_calendar_marks()
        self._refresh_month_list()
        self._set_editor_feedback("修改已自动保存")
        self._set_status_text("修改已保存")
        return True

    def _leave_task_editor(self, _checked=False, *, save=True):
        if save and not self._save_current_editor():
            return False
        self._clear_editing_state(clear_input=False, clear_selection=True)
        self._refresh_today_list()
        self._set_status_text("已返回任务列表")
        return True

    def _set_status_text(self, text):
        self.subtitle_label.setText(text)

    def _selected_date_qdate(self):
        selected = self.calendar.selectedDate()
        if selected.isValid():
            return selected
        return QDate.currentDate()

    def _selected_date_key(self):
        return self._selected_date_qdate().toString("yyyy-MM-dd")

    def _default_ddl_text(self):
        return QTime.currentTime().toString("HH:mm")

    # 保留原方法名作为兼容入口，数据规则只在 domain.todo 中维护一份。
    _normalize_ddl_text = staticmethod(normalize_ddl)
    _task_sort_key = staticmethod(task_sort_key)
    _parse_editor_text = staticmethod(parse_editor_text)

    @staticmethod
    def _normalize_task_item(task):
        return normalize_task(task) or {"ddl": "", "text": "", "completed": False}

    @staticmethod
    def _normalize_task_list(raw_items):
        source = raw_items if isinstance(raw_items, list) else ([] if raw_items is None else [raw_items])
        items = [task for raw in source if (task := normalize_task(raw)) is not None]
        return sorted(items, key=task_sort_key)

    def _ensure_date_items(self, date_key):
        normalized_items = self._normalize_task_list(self.items_by_date.get(date_key, []))
        if normalized_items:
            self.items_by_date[date_key] = normalized_items
        else:
            self.items_by_date.pop(date_key, None)
        return normalized_items

    def _visible_row_to_model_index(self, row):
        if row < 0 or row >= len(self._today_visible_indexes):
            return -1
        return self._today_visible_indexes[row]

    def _total_today_pages(self, total_items):
        if total_items <= 0:
            return 1
        return (total_items + self._today_page_size - 1) // self._today_page_size

    def _jump_to_today_index(self, model_index):
        if model_index is None or model_index < 0:
            self._today_page_index = 0
            return
        self._today_page_index = model_index // self._today_page_size

    def _update_today_pagination_state(self, total_items):
        total_pages = self._total_today_pages(total_items)
        self._today_page_index = max(0, min(self._today_page_index, total_pages - 1))

        self.today_page_label.setText(f"{self._today_page_index + 1}/{total_pages}")
        self.prev_page_btn.setEnabled(total_items > 0 and self._today_page_index > 0)
        self.next_page_btn.setEnabled(total_items > 0 and self._today_page_index < total_pages - 1)

    def _go_prev_today_page(self):
        if self._today_page_index <= 0:
            return
        self._today_page_index -= 1
        self._clear_editing_state(clear_input=False, clear_selection=True)
        self._refresh_today_list()

    def _go_next_today_page(self):
        today_items = self._ensure_date_items(self._selected_date_key())
        total_pages = self._total_today_pages(len(today_items))
        if self._today_page_index >= total_pages - 1:
            return
        self._today_page_index += 1
        self._clear_editing_state(clear_input=False, clear_selection=True)
        self._refresh_today_list()

    def _update_today_item_size_hints(self):
        if self.today_list.count() <= 0:
            return

        for index in range(self.today_list.count()):
            self.today_list.item(index).setSizeHint(QSize(0, 62))

    def _display_task_text(self, task):
        normalized_task = self._normalize_task_item(task)
        ddl_text = normalized_task["ddl"] if normalized_task["ddl"] else "--:--"
        prefix = "已完成 · " if normalized_task["completed"] else ""
        return f"{prefix}{ddl_text}  {normalized_task['text']}"


    def _sync_daily_section_caption(self):
        selected = self._selected_date_qdate()
        self.left_title.setText(f"每日任务 ({selected.toString('yyyy-MM-dd')})")
        self.ddl_input.setPlaceholderText("DDL HH:MM")
        self.todo_input.setPlaceholderText(
            f"输入 {selected.toString('MM-dd')} 待办"
        )

    def _submit_todo_input(self):
        ddl_text = self._normalize_ddl_text(self.ddl_input.text())
        if not ddl_text:
            self._set_status_text("请输入合法 DDL（HH:MM）")
            return

        text = self.todo_input.text().strip()
        if not text:
            self._set_status_text("请输入待办内容")
            return

        today_key = self._selected_date_key()
        existing_items = self.items_by_date.get(today_key, [])
        if isinstance(existing_items, list) and len(existing_items) >= MAX_TODOS_PER_DATE:
            self._set_status_text(f"单日最多添加 {MAX_TODOS_PER_DATE} 项待办")
            return
        if sum(
            len(items) for items in self.items_by_date.values() if isinstance(items, list)
        ) >= MAX_TOTAL_TODOS:
            self._set_status_text(f"待办总数不能超过 {MAX_TOTAL_TODOS} 项")
            return
        if today_key not in self.items_by_date and len(self.items_by_date) >= MAX_TODO_DATES:
            self._set_status_text(f"待办日期不能超过 {MAX_TODO_DATES} 个")
            return

        previous_items = deepcopy(self.items_by_date)
        today_items = self.items_by_date.setdefault(today_key, [])
        today_items.append({"ddl": ddl_text, "text": text, "completed": False})
        normalized_today_items = self._ensure_date_items(today_key)
        for idx, task in enumerate(normalized_today_items):
            if task.get("ddl") == ddl_text and task.get("text") == text:
                self._jump_to_today_index(idx)
                break
        status_text = "已新增事项"

        if not self._persist_items():
            self.items_by_date = previous_items
            self._refresh_today_list()
            self._refresh_calendar_marks()
            self._refresh_month_list()
            self.ddl_input.setText(ddl_text)
            self.todo_input.setText(text)
            self._set_status_text("保存失败，待办未新增，请检查数据目录权限")
            return

        self.todo_input.clear()
        self.ddl_input.setText(self._default_ddl_text())
        self._refresh_today_list()
        self._refresh_calendar_marks()
        self._refresh_month_list()
        self._set_status_text(status_text)
        self._clear_editing_state(clear_input=False)

    def _selected_model_index(self, today_items):
        if (
            self._editing_index is not None
            and 0 <= self._editing_index < len(today_items)
        ):
            return self._editing_index
        if (
            self._last_editing_index is not None
            and 0 <= self._last_editing_index < len(today_items)
        ):
            return self._last_editing_index

        selected_items = self.today_list.selectedItems()
        row = (
            self.today_list.row(selected_items[0])
            if selected_items
            else self.today_list.currentRow()
        )
        return self._visible_row_to_model_index(row)

    def _current_task_context(self):
        date_key = self._editing_date_key or self._selected_date_key()
        today_items = self._ensure_date_items(date_key)
        if self._editing_date_key is not None:
            index = self._editing_index if self._editing_index is not None else -1
        else:
            index = self._selected_model_index(today_items)
        return date_key, today_items, index

    def _toggle_selected_completion(self):
        self._edit_save_timer.stop()
        today_key, today_items, index = self._current_task_context()
        if index < 0 or index >= len(today_items):
            self._set_status_text("请先选择一条事项")
            return

        original_task = self._normalize_task_item(today_items[index])
        previous_items = deepcopy(self.items_by_date)
        task = dict(original_task)
        editor_is_open = (
            self._editing_date_key is not None
            and self.daily_stack.currentWidget() is self.task_editor_page
        )
        if editor_is_open and not original_task["completed"]:
            parsed_ddl, parsed_text, error_text = self._parse_editor_text(
                self.task_editor.toPlainText(),
                original_task["ddl"],
            )
            if error_text:
                self._set_editor_feedback(error_text, error=True)
                self._set_status_text(error_text)
                return
            task["ddl"] = parsed_ddl
            task["text"] = parsed_text

        task["completed"] = not task["completed"]
        today_items[index] = task
        today_items.sort(key=self._task_sort_key)
        self.items_by_date[today_key] = today_items
        new_index = next(
            (task_index for task_index, item in enumerate(today_items) if item is task),
            index,
        )
        if not self._persist_items():
            self.items_by_date = previous_items
            self._editing_index = index
            self._last_editing_index = index
            self._refresh_today_list()
            self._refresh_calendar_marks()
            self._refresh_month_list()
            if editor_is_open:
                self._apply_task_editor_state(original_task)
                self._set_editor_feedback("保存失败，完成状态未改变。", error=True)
            self._set_status_text("保存失败，完成状态未改变")
            return

        self._editing_index = new_index
        self._last_editing_index = new_index
        self._refresh_today_list()
        self._refresh_calendar_marks()
        self._refresh_month_list()
        feedback = "已标记为完成" if task["completed"] else "已恢复为未完成"
        if editor_is_open:
            self._apply_task_editor_state(task, feedback=feedback)
            if not task["completed"]:
                QTimer.singleShot(0, self.task_editor.setFocus)
        self._set_status_text(feedback)

    def _delete_selected_item(self):
        self._edit_save_timer.stop()
        today_key, today_items, index = self._current_task_context()
        if not today_items:
            self._clear_editing_state(clear_input=False)
            return

        if index < 0 or index >= len(today_items):
            self._set_status_text("请先点击一条事项后再删除")
            return

        previous_items = deepcopy(self.items_by_date)
        today_items.pop(index)
        if not today_items:
            self.items_by_date.pop(today_key, None)
        else:
            self.items_by_date[today_key] = sorted(today_items, key=self._task_sort_key)
        self._last_editing_index = None

        if not self._persist_items():
            self.items_by_date = previous_items
            self._refresh_today_list()
            self._refresh_calendar_marks()
            self._refresh_month_list()
            if self._editing_date_key is not None:
                self._set_editor_feedback("保存失败，事项未删除。", error=True)
            self._set_status_text("保存失败，事项未删除")
            return

        self._clear_editing_state(clear_input=False)
        self._refresh_today_list()
        self._refresh_calendar_marks()
        self._refresh_month_list()
        self._set_status_text("已删除事项")

    def _on_today_item_selected(self, item):
        row = self.today_list.row(item)
        index = self._visible_row_to_model_index(row)
        if index >= 0:
            self._open_task_editor(self._selected_date_key(), index)

    def _today_key(self):
        return date.today().isoformat()

    def _month_entries(self, year, month):
        entries = []
        for date_key, tasks in list(self.items_by_date.items()):
            try:
                parsed = date.fromisoformat(date_key)
            except ValueError:
                continue

            normalized_tasks = self._normalize_task_list(tasks)
            if parsed.year == year and parsed.month == month and normalized_tasks:
                entries.append((parsed, normalized_tasks))
        entries.sort(key=lambda x: x[0])
        return entries

    def _refresh_today_list(self):
        self.today_list.clear()
        self._today_visible_indexes = []
        today_items = self._ensure_date_items(self._selected_date_key())
        total_items = len(today_items)
        completed_count = sum(task.get("completed") is True for task in today_items)
        self.daily_summary.setText(
            f"{total_items - completed_count:02d} 项待完成    /    {completed_count:02d} 项已完成"
            if total_items else "今天的空白，留给值得做的事。"
        )
        self._update_today_pagination_state(total_items)

        if not today_items:
            placeholder = QListWidgetItem("该日期暂无待办")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.today_list.addItem(placeholder)
            self._update_today_item_size_hints()
            self._clear_editing_state(clear_input=True)
            return

        start = self._today_page_index * self._today_page_size
        end = min(total_items, start + self._today_page_size)

        for model_index in range(start, end):
            task = self._normalize_task_item(today_items[model_index])
            item = QListWidgetItem(self._display_task_text(task))
            item.setData(Qt.ItemDataRole.UserRole, task)
            item.setToolTip(self._display_task_text(task))
            flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            item.setFlags(flags)
            if task["completed"]:
                completed_font = item.font()
                completed_font.setStrikeOut(True)
                item.setFont(completed_font)
                item.setForeground(QBrush(QColor(P.completed)))
                item.setBackground(QBrush(QColor(P.completed_bg)))
            self.today_list.addItem(item)
            self._today_visible_indexes.append(model_index)

        self._update_today_item_size_hints()

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
                normalized_task = self._normalize_task_item(task)
                ddl_text = normalized_task["ddl"] if normalized_task["ddl"] else "--:--"
                prefix = "已完成 · " if normalized_task["completed"] else ""
                item = QListWidgetItem(
                    f"{prefix}{day.day:02d}日  {ddl_text}  {normalized_task['text']}"
                )
                if normalized_task["completed"]:
                    completed_font = item.font()
                    completed_font.setStrikeOut(True)
                    item.setFont(completed_font)
                    item.setForeground(QBrush(QColor(P.completed)))
                self.month_list.addItem(item)

    def _refresh_calendar_marks(self):
        self.calendar.refresh_marks(self.items_by_date)

    def _on_calendar_page_changed(self, year, month):
        self._refresh_month_caption()
        self._refresh_month_list()
        self._refresh_calendar_marks()

    def _on_calendar_selection_changed(self):
        previous_editor_date = self._editing_date_key
        if previous_editor_date is not None and not self._save_current_editor():
            previous_qdate = QDate.fromString(previous_editor_date, "yyyy-MM-dd")
            if previous_qdate.isValid():
                self.calendar.blockSignals(True)
                self.calendar.setSelectedDate(previous_qdate)
                self.calendar.blockSignals(False)
                self._refresh_calendar_marks()
            self._set_status_text("修改尚未保存，请修正后再切换日期")
            return

        selected = self.calendar.selectedDate()
        self._today_page_index = 0
        self._clear_editing_state(clear_input=True)
        self._sync_daily_section_caption()
        self._refresh_today_list()
        self._refresh_calendar_marks()
        self.subtitle_label.setText(f"选中日期: {selected.toString('yyyy-MM-dd')}（已与月份待办同步）")

    def reload_data(self):
        self.items_by_date = load_todo_items_by_date()
        self.calendar.blockSignals(True)
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.blockSignals(False)
        normalized_items = {}
        for date_key, tasks in list(self.items_by_date.items()):
            normalized_tasks = self._normalize_task_list(tasks)
            if normalized_tasks:
                normalized_items[date_key] = normalized_tasks
        self.items_by_date = normalized_items
        self._today_page_index = 0
        self._today_visible_indexes = []

        self._clear_editing_state(clear_input=True)
        self._sync_daily_section_caption()
        self._refresh_today_list()
        self._refresh_calendar_marks()
        self._refresh_month_caption()
        self._refresh_month_list()
        self._set_status_text("今日与本月计划")
        if self._month_expanded:
            self.resize(self.expanded_width, self.panel_height)
            self.right_section.setVisible(True)
            self.expand_btn.setText("收起日历")
        else:
            self.resize(self.collapsed_width, self.panel_height)
            self.right_section.setVisible(False)
            self.expand_btn.setText("展开日历")
        self.today_btn.setVisible(self._month_expanded)

    def _close_from_symbol(self):
        self._stop_drag()
        if self._editing_date_key is not None and not self._save_current_editor():
            self._set_status_text("修改尚未保存，请修正后再关闭")
            return
        if callable(self.on_close_callback):
            self.on_close_callback()
        self._allow_close = True
        self.close()
        self._allow_close = False

    def eventFilter(self, obj, event):
        if obj is self.today_list.viewport():
            if event.type() == QEvent.Type.Resize:
                self._update_today_item_size_hints()

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

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_border_drag(event.position().toPoint()):
            self._start_drag(event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._stop_drag()
        super().mouseReleaseEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.keep_inside_screen(reference_point=QCursor.pos())
        if self._editing_date_key is not None and not self.task_editor.isReadOnly():
            QTimer.singleShot(0, self.task_editor.setFocus)
        else:
            QTimer.singleShot(0, self.todo_input.setFocus)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self._editing_date_key is not None:
                self._leave_task_editor(save=True)
            else:
                self._close_from_symbol()
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
