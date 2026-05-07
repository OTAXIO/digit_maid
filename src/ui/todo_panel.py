from datetime import date
import os
import sys

from PyQt6.QtCore import QDate, QEvent, QPoint, QRect, QSize, Qt, QTime, QTimer, QPropertyAnimation
from PyQt6.QtGui import QColor, QFont, QIcon, QTextCharFormat, QCursor, QTextOption
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
    QTextEdit,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from src.function.todo_store import load_todo_items_by_date, save_todo_items_by_date


def _default_ui_font_family():
    if sys.platform == "darwin":
        return "PingFang SC"
    return "Microsoft YaHei"


class _TodoItemEditDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QTextEdit(parent)
        editor.setAcceptRichText(False)
        editor.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        editor.setTabChangesFocus(True)
        editor.setFrameShape(QFrame.Shape.NoFrame)
        editor.setAutoFillBackground(True)
        editor.viewport().setAutoFillBackground(True)
        editor.setStyleSheet(
            "QTextEdit {"
            "background-color: #ffffff;"
            "color: #2f2220;"
            "border: 2px solid #c41c1c;"
            "border-radius: 6px;"
            "padding: 2px 4px;"
            "}"
        )
        return editor

    def setEditorData(self, editor, index):
        editor.setPlainText(str(index.data(Qt.ItemDataRole.EditRole) or ""))
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        editor.setTextCursor(cursor)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.toPlainText(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        rect = option.rect.adjusted(2, 2, -2, -2)
        min_height = 56
        if rect.height() < min_height:
            grow = min_height - rect.height()
            rect = QRect(rect.left(), max(0, rect.top() - grow // 2), rect.width(), min_height)
        editor.setGeometry(rect)

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        if option.state & QStyle.StateFlag.State_Editing:
            opt.text = ""
            opt.state &= ~QStyle.StateFlag.State_Selected

        widget = opt.widget
        style = widget.style() if widget is not None else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget)

    def eventFilter(self, obj, event):
        if isinstance(obj, QTextEdit) and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    return super().eventFilter(obj, event)
                self.commitData.emit(obj)
                self.closeEditor.emit(obj, QAbstractItemDelegate.EndEditHint.NoHint)
                return True

        return super().eventFilter(obj, event)


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
        self._drag_border_margin = 10
        self._fold_anim = None
        self._editing_index = None
        self._last_editing_index = None
        self._suppress_item_changed = False
        self._today_page_size = 6
        self._today_page_index = 0
        self._today_visible_indexes = []
        self._delete_slot_visible = False

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
            QPushButton#expand_btn,
            QPushButton#today_btn {
                border: 2px solid #c41c1c;
                border-radius: 10px;
                background-color: #ffffff;
                color: #5f3d37;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#expand_btn:hover,
            QPushButton#today_btn:hover {
                background-color: #c41c1c;
            }
            QPushButton#todo_page_btn {
                border: 2px solid #c41c1c;
                border-radius: 8px;
                background-color: #ffffff;
                color: #5f3d37;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 700;
                min-height: 24px;
            }
            QPushButton#todo_page_btn:hover {
                background-color: #c41c1c;
            }
            QPushButton#todo_page_btn:disabled {
                border-color: #e4c0bb;
                color: #bf9e98;
                background-color: #fff8f7;
            }
            QLabel#todo_page_label {
                color: #8a6259;
                font-size: 12px;
                font-weight: 700;
                min-width: 52px;
                max-width: 52px;
                qproperty-alignment: AlignCenter;
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
            QLineEdit#ddl_input {
                min-width: 82px;
                max-width: 82px;
                padding: 7px 6px;
                text-align: center;
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

        self.today_btn = QPushButton("回到今天", card)
        self.today_btn.setObjectName("today_btn")
        self.today_btn.clicked.connect(self._go_to_today)
        header_layout.addWidget(self.today_btn)

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
        self.today_list.setViewportMargins(0, 0, 0, 0)
        self.today_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.today_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.today_list.setWordWrap(True)
        self.today_list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.today_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.today_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.today_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        self._today_item_delegate = _TodoItemEditDelegate(self.today_list)
        self.today_list.setItemDelegate(self._today_item_delegate)

        self.today_list.itemClicked.connect(self._on_today_item_selected)
        self.today_list.itemChanged.connect(self._on_today_item_changed)
        self.today_list.itemDelegate().closeEditor.connect(self._on_today_editor_closed)
        self.today_list.itemSelectionChanged.connect(self._position_selected_delete_button)
        self.today_list.verticalScrollBar().valueChanged.connect(self._position_selected_delete_button)
        self.today_list.horizontalScrollBar().valueChanged.connect(self._position_selected_delete_button)
        self.today_list.viewport().installEventFilter(self)
        left_layout.addWidget(self.today_list, 1)

        page_row = QHBoxLayout()
        page_row.setContentsMargins(0, 0, 0, 0)
        page_row.setSpacing(6)

        self.prev_page_btn = QPushButton("上一页", left_section)
        self.prev_page_btn.setObjectName("todo_page_btn")
        self.prev_page_btn.clicked.connect(self._go_prev_today_page)
        page_row.addWidget(self.prev_page_btn)

        self.today_page_label = QLabel("1/1", left_section)
        self.today_page_label.setObjectName("todo_page_label")
        page_row.addWidget(self.today_page_label)

        self.next_page_btn = QPushButton("下一页", left_section)
        self.next_page_btn.setObjectName("todo_page_btn")
        self.next_page_btn.clicked.connect(self._go_next_today_page)
        page_row.addWidget(self.next_page_btn)

        page_row.addStretch(1)
        left_layout.addLayout(page_row)

        self.delete_btn = QPushButton("", self.today_list)
        self.delete_btn.setObjectName("icon_action_btn")
        # self.delete_btn.setToolTip("删除当前选中事项")
        self.delete_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.delete_btn.pressed.connect(self._delete_selected_item)
        self.delete_btn.clicked.connect(self._delete_selected_item)
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.hide()
        self._apply_icon_button(self.delete_btn, "delete.png")

        input_action_row = QHBoxLayout()
        input_action_row.setSpacing(8)

        self.ddl_input = QLineEdit(left_section)
        self.ddl_input.setObjectName("ddl_input")
        self.ddl_input.setPlaceholderText("DDL HH:MM")
        self.ddl_input.setText(self._default_ddl_text())
        self.ddl_input.returnPressed.connect(self._submit_todo_input)
        input_action_row.addWidget(self.ddl_input)

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
        self._last_editing_index = None
        if clear_selection:
            self.today_list.clearSelection()
            self.today_list.setCurrentRow(-1)
        self._set_delete_slot_visible(False)
        self._position_selected_delete_button()
        if clear_input:
            self.todo_input.clear()
            if hasattr(self, "ddl_input"):
                self.ddl_input.setText(self._default_ddl_text())

    def _set_delete_slot_visible(self, visible):
        if not hasattr(self, "today_list"):
            return

        target_visible = bool(visible)
        if self._delete_slot_visible == target_visible:
            return

        left_margin = 34 if target_visible else 0
        self.today_list.setViewportMargins(left_margin, 0, 0, 0)
        self._delete_slot_visible = target_visible
        self._update_today_item_size_hints()

    def _position_selected_delete_button(self):
        if not hasattr(self, "delete_btn"):
            return

        if self._editing_index is None:
            self._set_delete_slot_visible(False)
            self.delete_btn.hide()
            return

        today_items = self._ensure_date_items(self._selected_date_key())
        if self._editing_index not in self._today_visible_indexes:
            self._set_delete_slot_visible(False)
            self.delete_btn.hide()
            return

        current_row = self._today_visible_indexes.index(self._editing_index)
        item = self.today_list.item(current_row)
        if item is None:
            self._set_delete_slot_visible(False)
            self.delete_btn.hide()
            return

        model_index = self._visible_row_to_model_index(current_row)
        if model_index < 0 or model_index >= len(today_items):
            self._set_delete_slot_visible(False)
            self.delete_btn.hide()
            return

        self._set_delete_slot_visible(True)

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

    def _position_today_inline_editor(self, editor=None):
        if editor is None:
            editor = self.today_list.findChild(QTextEdit)
            if editor is None:
                editor = self.today_list.findChild(QLineEdit)
        if editor is None:
            return

        target_item = None
        if self._editing_index is not None and self._editing_index in self._today_visible_indexes:
            target_row = self._today_visible_indexes.index(self._editing_index)
            target_item = self.today_list.item(target_row)
        if target_item is None:
            selected_items = self.today_list.selectedItems()
            if selected_items:
                target_item = selected_items[0]
            else:
                current_row = self.today_list.currentRow()
                if 0 <= current_row < self.today_list.count():
                    target_item = self.today_list.item(current_row)

        if target_item is None:
            return

        item_rect = self.today_list.visualItemRect(target_item)
        if not item_rect.isValid() or item_rect.height() <= 0:
            return

        editor_width = max(120, self.today_list.viewport().width() - 4)
        if isinstance(editor, QTextEdit):
            editor.viewport().setAutoFillBackground(True)
            editor_height = max(34, item_rect.height() - 4)
        else:
            editor_height = min(max(30, editor.sizeHint().height() + 6), max(30, item_rect.height() - 4))

        y = item_rect.top() + max(0, (item_rect.height() - editor_height) // 2)
        editor.setGeometry(2, y, editor_width, editor_height)
        editor.raise_()

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
        return "00:00"

    def _normalize_ddl_text(self, raw_text):
        text = str(raw_text).strip().replace("：", ":")
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

    def _split_prefixed_ddl(self, raw_text):
        text = str(raw_text).strip().replace("：", ":")
        if not text:
            return "", ""

        segments = text.split(None, 1)
        if segments and ":" in segments[0]:
            normalized_ddl = self._normalize_ddl_text(segments[0])
            if normalized_ddl:
                content = segments[1].strip() if len(segments) > 1 else ""
                return normalized_ddl, content

        return "", text

    def _normalize_task_item(self, task):
        if isinstance(task, dict):
            ddl = self._normalize_ddl_text(task.get("ddl", ""))
            text = str(task.get("text", "")).strip()
            return {"ddl": ddl, "text": text}

        ddl, text = self._split_prefixed_ddl(task)
        return {"ddl": ddl, "text": text}

    def _task_sort_key(self, task):
        normalized_task = self._normalize_task_item(task)
        ddl = normalized_task["ddl"]
        if ddl:
            try:
                hour_str, minute_str = ddl.split(":", 1)
                minute_of_day = int(hour_str) * 60 + int(minute_str)
                return (0, minute_of_day, normalized_task["text"])
            except ValueError:
                pass

        return (1, 24 * 60, normalized_task["text"])

    def _normalize_task_list(self, raw_items):
        if isinstance(raw_items, list):
            source_items = raw_items
        elif raw_items is None:
            source_items = []
        else:
            source_items = [raw_items]

        normalized_items = []
        for raw_item in source_items:
            task = self._normalize_task_item(raw_item)
            if task["text"]:
                normalized_items.append(task)

        normalized_items.sort(key=self._task_sort_key)
        return normalized_items

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

        available_width = max(80, self.today_list.viewport().width() - 16)
        fm = self.today_list.fontMetrics()

        for idx in range(self.today_list.count()):
            item = self.today_list.item(idx)
            if item is None:
                continue

            text_rect = fm.boundingRect(
                QRect(0, 0, available_width, 1000),
                Qt.TextFlag.TextWordWrap,
                item.text(),
            )
            target_height = max(34, text_rect.height() + 14)
            item.setSizeHint(QSize(0, target_height))

    def _display_task_text(self, task):
        normalized_task = self._normalize_task_item(task)
        ddl_text = normalized_task["ddl"] if normalized_task["ddl"] else "--:--"
        return f"{ddl_text}  {normalized_task['text']}"

    def _parse_editor_text(self, raw_text, fallback_ddl):
        text = str(raw_text).replace("\r", "\n").replace("\n", " ").strip()
        if not text:
            return "", "", "待办内容不能为空"

        normalized_text = text.replace("：", ":")
        segments = normalized_text.split(None, 1)
        if segments and ":" in segments[0]:
            normalized_ddl = self._normalize_ddl_text(segments[0])
            if not normalized_ddl:
                return "", "", "DDL 格式错误，请使用 HH:MM"

            content = segments[1].strip() if len(segments) > 1 else ""
            if not content:
                return "", "", "待办内容不能为空"

            return normalized_ddl, content, ""

        return fallback_ddl, normalized_text, ""

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
        today_items = self.items_by_date.setdefault(today_key, [])
        today_items.append({"ddl": ddl_text, "text": text})
        normalized_today_items = self._ensure_date_items(today_key)
        for idx, task in enumerate(normalized_today_items):
            if task.get("ddl") == ddl_text and task.get("text") == text:
                self._jump_to_today_index(idx)
                break
        status_text = "已新增事项"

        self.todo_input.clear()
        self.ddl_input.setText(self._default_ddl_text())
        self._persist_items()
        self._refresh_today_list()
        self._refresh_calendar_marks()
        self._refresh_month_list()
        self._set_status_text(status_text)
        self._clear_editing_state(clear_input=False)

    def _delete_selected_item(self):
        today_key = self._selected_date_key()
        today_items = self._ensure_date_items(today_key)
        if not today_items:
            self._clear_editing_state(clear_input=True)
            return

        index = None
        if self._editing_index is not None and 0 <= self._editing_index < len(today_items):
            index = self._editing_index
        elif self._last_editing_index is not None and 0 <= self._last_editing_index < len(today_items):
            index = self._last_editing_index
        else:
            selected_items = self.today_list.selectedItems()
            if selected_items:
                row = self.today_list.row(selected_items[0])
            else:
                row = self.today_list.currentRow()

            index = self._visible_row_to_model_index(row)

        if index is None or index < 0 or index >= len(today_items):
            self._set_status_text("请先点击一条事项后再删除")
            return

        today_items.pop(index)
        if not today_items:
            self.items_by_date.pop(today_key, None)
        else:
            self.items_by_date[today_key] = sorted(today_items, key=self._task_sort_key)
        self._last_editing_index = None

        self.todo_input.clear()
        self._persist_items()
        self._refresh_today_list()
        self._refresh_calendar_marks()
        self._refresh_month_list()
        self._clear_editing_state(clear_input=True)
        self._set_status_text("已删除事项")

    def _on_today_item_selected(self, item):
        row = self.today_list.row(item)
        index = self._visible_row_to_model_index(row)
        today_items = self._ensure_date_items(self._selected_date_key())
        if 0 <= index < len(today_items):
            self.today_list.setCurrentItem(item)
            item.setSelected(True)
            self._editing_index = index
            self._last_editing_index = index
            self._position_selected_delete_button()
            self.today_list.editItem(item)
            QTimer.singleShot(0, self._position_selected_delete_button)
            QTimer.singleShot(0, self._bind_today_inline_editor)
            self._set_status_text("已进入编辑（可输入 HH:MM 后空格修改 DDL）")

    def _bind_today_inline_editor(self):
        editor = self.today_list.findChild(QTextEdit)
        if editor is not None:
            self._position_today_inline_editor(editor)
            return

        editor = self.today_list.findChild(QLineEdit)
        if editor is None:
            return

        try:
            editor.returnPressed.disconnect(self._on_today_editor_return_pressed)
        except TypeError:
            pass
        editor.returnPressed.connect(self._on_today_editor_return_pressed)
        self._position_today_inline_editor(editor)

    def _on_today_editor_return_pressed(self):
        self._finish_today_inline_edit(save=True, clear_selection=True)

    def _finish_today_inline_edit(self, save=True, clear_selection=True):
        editor = self.today_list.findChild(QTextEdit)
        if editor is None:
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

        today_key = self._selected_date_key()
        row = self.today_list.row(item)
        index = self._visible_row_to_model_index(row)
        today_items = self._ensure_date_items(today_key)
        if index < 0 or index >= len(today_items):
            return

        old_task = self._normalize_task_item(today_items[index])
        new_ddl, new_text, error_text = self._parse_editor_text(item.text(), old_task["ddl"])
        if error_text:
            self._suppress_item_changed = True
            item.setText(self._display_task_text(old_task))
            self._suppress_item_changed = False
            self._set_status_text(error_text)
            return

        updated_task = {"ddl": new_ddl, "text": new_text}
        if updated_task == old_task:
            if item.text() != self._display_task_text(old_task):
                self._suppress_item_changed = True
                item.setText(self._display_task_text(old_task))
                self._suppress_item_changed = False
            return

        today_items[index] = updated_task
        today_items.sort(key=self._task_sort_key)
        self.items_by_date[today_key] = today_items
        for idx, task in enumerate(today_items):
            if task == updated_task:
                self._jump_to_today_index(idx)
                break
        self._persist_items()
        self._refresh_today_list()
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

        self._suppress_item_changed = True
        for model_index in range(start, end):
            task = today_items[model_index]
            item = QListWidgetItem(self._display_task_text(task))
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable
            )
            self.today_list.addItem(item)
            self._today_visible_indexes.append(model_index)
        self._suppress_item_changed = False

        self._update_today_item_size_hints()
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
                normalized_task = self._normalize_task_item(task)
                ddl_text = normalized_task["ddl"] if normalized_task["ddl"] else "--:--"
                self.month_list.addItem(f"{day.day:02d}日  {ddl_text}  {normalized_task['text']}")

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
        # QCalendarWidget 在 1 号恰好位于每周首列时，会额外显示上一周作为首行。
        if leading_days == 0:
            leading_days = 7
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
        self._today_page_index = 0
        self._clear_editing_state(clear_input=True)
        self._sync_daily_section_caption()
        self._refresh_today_list()
        self._refresh_calendar_marks()
        self.subtitle_label.setText(f"选中日期: {selected.toString('yyyy-MM-dd')}（已与月份待办同步）")

    def reload_data(self):
        self.items_by_date = load_todo_items_by_date()
        normalized_items = {}
        for date_key, tasks in list(self.items_by_date.items()):
            normalized_tasks = self._normalize_task_list(tasks)
            if normalized_tasks:
                normalized_items[date_key] = normalized_tasks
        self.items_by_date = normalized_items
        self._today_page_index = 0
        self._today_visible_indexes = []

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
        self.today_btn.setVisible(self._month_expanded)

    def _close_from_symbol(self):
        self._stop_drag()
        if callable(self.on_close_callback):
            self.on_close_callback()
        self._allow_close = True
        self.close()
        self._allow_close = False

    def eventFilter(self, obj, event):
        if obj is self.today_list.viewport():
            if event.type() == QEvent.Type.Resize:
                self._update_today_item_size_hints()
                self._position_today_inline_editor()
                self._position_selected_delete_button()

            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                pos = event.position().toPoint()
                if self.today_list.itemAt(pos) is None:
                    editor = self.today_list.findChild(QTextEdit)
                    if editor is None:
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