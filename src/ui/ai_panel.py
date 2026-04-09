from __future__ import annotations

import html
from datetime import datetime

from PyQt6.QtCore import QPoint, Qt, QSettings, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QColor

from src.ai.models import ChatMessage, PanelState


class _SubmitTextEdit(QTextEdit):
    submit_requested = pyqtSignal()

    def keyPressEvent(self, event):
        if (
            event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        ):
            self.submit_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class _ResizeHandle(QWidget):
    def __init__(self, parent, edges, cursor_shape):
        super().__init__(parent)
        self._edges = edges
        self.setCursor(cursor_shape)
        self.setMouseTracking(True)
        self.setStyleSheet("background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            window_handle = self.window().windowHandle()
            if window_handle is not None and window_handle.startSystemResize(self._edges):
                event.accept()
                return
        super().mousePressEvent(event)


class _DragHeader(QFrame):
    def __init__(self, panel, parent=None):
        super().__init__(parent)
        self._panel = panel
        self._dragging = False
        self._drag_offset = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self._panel.frameGeometry().topLeft()
            self._panel._on_panel_drag_started()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            next_pos = event.globalPosition().toPoint() - self._drag_offset
            self._panel._move_panel_free(next_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._panel._on_panel_drag_finished()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class AIChatPanel(QWidget):
    submit_requested = pyqtSignal(str)
    edit_config_requested = pyqtSignal()
    state_changed = pyqtSignal(str)
    visibility_changed = pyqtSignal(bool)

    def __init__(self, anchor_widget=None):
        super().__init__(None)
        self.anchor_widget = anchor_widget
        self.state = PanelState.HIDDEN.value
        self._settings = QSettings("DigitMaid", "DigitMaid")
        self._follow_anchor = True
        self._layout_restored = False
        self._restoring_layout = False

        self._persist_timer = QTimer(self)
        self._persist_timer.setSingleShot(True)
        self._persist_timer.timeout.connect(self._persist_panel_layout)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setMinimumSize(360, 420)
        self.resize(420, 560)

        self._build_ui()
        self._init_resize_handles()

        self.follow_timer = QTimer(self)
        self.follow_timer.timeout.connect(self._reposition_to_anchor)
        self.follow_timer.start(50)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 4px 0 4px 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(127, 146, 171, 130);
                border-radius: 4px;
                min-height: 36px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
                border: none;
            }
            """
        )

        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("aiPanelFrame")
        self.main_frame.setStyleSheet(
            """
            QFrame#aiPanelFrame {
                background-color: rgba(246, 249, 253, 244);
                border: 1px solid rgba(185, 202, 222, 220);
                border-radius: 18px;
            }
            """
        )
        root.addWidget(self.main_frame)

        shadow = QGraphicsDropShadowEffect(self.main_frame)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 9)
        shadow.setColor(QColor(20, 36, 62, 46))
        self.main_frame.setGraphicsEffect(shadow)

        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(14, 14, 14, 14)
        frame_layout.setSpacing(10)

        self.header = _DragHeader(self, self.main_frame)
        self.header.setStyleSheet("background: transparent;")
        self.header.setCursor(Qt.CursorShape.SizeAllCursor)
        title_row = QHBoxLayout(self.header)
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        self.title_label = QLabel("AI 对话", self.main_frame)
        self.title_label.setStyleSheet("font-size: 17px; font-weight: 700; color: #172338;")
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        title_row.addWidget(self.title_label)
        title_row.addStretch(1)

        self.state_chip = QLabel("输入", self.main_frame)
        self.state_chip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        title_row.addWidget(self.state_chip)

        self.config_btn = QPushButton("配置", self.main_frame)
        self.config_btn.setObjectName("configBtn")
        self.config_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.config_btn.setFixedHeight(24)
        self.config_btn.setStyleSheet(
            "QPushButton#configBtn {"
            "background: #f2f6fc;"
            "color: #2e4f79;"
            "border: 1px solid #d5e0ef;"
            "border-radius: 10px;"
            "padding: 2px 10px;"
            "font-size: 12px;"
            "font-weight: 700;"
            "}"
            "QPushButton#configBtn:hover { background: #e7eef8; }"
        )
        self.config_btn.clicked.connect(self.edit_config_requested.emit)
        title_row.addWidget(self.config_btn)

        self.return_btn = QPushButton("Return", self.main_frame)
        self.return_btn.setObjectName("returnBtn")
        self.return_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.return_btn.setFixedHeight(24)
        self.return_btn.setStyleSheet(
            "QPushButton#returnBtn {"
            "background: #eaf2fc;"
            "color: #214f86;"
            "border: 1px solid #c8d9ef;"
            "border-radius: 10px;"
            "padding: 2px 10px;"
            "font-size: 12px;"
            "font-weight: 700;"
            "}"
            "QPushButton#returnBtn:hover { background: #dbe9fa; }"
            "QPushButton#returnBtn:disabled { background: #f2f5f9; color: #9ca9bb; border-color: #dce3ec; }"
        )
        self.return_btn.clicked.connect(self._on_return_clicked)
        title_row.addWidget(self.return_btn)

        close_btn = QPushButton("×", self.main_frame)
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(
            "QPushButton#closeBtn {"
            "background: #ff6f61;"
            "color: #ffffff;"
            "border: none;"
            "border-radius: 12px;"
            "font-weight: 700;"
            "font-size: 13px;"
            "}"
            "QPushButton#closeBtn:hover { background: #eb5c4f; }"
        )
        close_btn.clicked.connect(self.hide_panel)
        title_row.addWidget(close_btn)

        frame_layout.addWidget(self.header)

        self.splitter = QSplitter(Qt.Orientation.Vertical, self.main_frame)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(10)
        self.splitter.setStyleSheet(
            """
            QSplitter::handle:vertical {
                background: transparent;
                margin: 0 12px;
                border-top: 1px solid rgba(156, 171, 190, 170);
                border-bottom: 1px solid rgba(255, 255, 255, 120);
            }
            QSplitter::handle:vertical:hover {
                border-top: 1px solid rgba(96, 132, 173, 225);
            }
            """
        )

        self.history_panel = QFrame(self.splitter)
        self.history_panel.setObjectName("historyPanel")
        self.history_panel.setStyleSheet(
            "QFrame#historyPanel {"
            "background: rgba(255, 255, 255, 168);"
            "border: 1px solid rgba(211, 222, 235, 205);"
            "border-radius: 12px;"
            "}"
        )
        self.history_panel.setMinimumHeight(150)
        history_panel_layout = QVBoxLayout(self.history_panel)
        history_panel_layout.setContentsMargins(4, 4, 4, 4)
        history_panel_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self.history_panel)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; }")

        self.history_widget = QWidget(self.scroll_area)
        self.history_layout = QVBoxLayout(self.history_widget)
        self.history_layout.setContentsMargins(2, 2, 2, 2)
        self.history_layout.setSpacing(10)
        self.history_layout.addStretch(1)
        self.scroll_area.setWidget(self.history_widget)
        history_panel_layout.addWidget(self.scroll_area)

        self.bottom_panel = QFrame(self.splitter)
        self.bottom_panel.setObjectName("bottomPanel")
        self.bottom_panel.setStyleSheet("QFrame#bottomPanel { background: transparent; border: none; }")
        self.bottom_panel.setMinimumHeight(140)
        bottom_layout = QVBoxLayout(self.bottom_panel)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(8)

        self.status_label = QLabel("", self.bottom_panel)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color:#566173; font-size:12px;")
        bottom_layout.addWidget(self.status_label)

        input_wrap = QFrame(self.bottom_panel)
        input_wrap.setObjectName("inputWrap")
        input_wrap.setStyleSheet(
            "QFrame#inputWrap {"
            "background: rgba(255, 255, 255, 238);"
            "border: 1px solid rgba(196, 211, 230, 220);"
            "border-radius: 14px;"
            "}"
        )
        input_layout = QVBoxLayout(input_wrap)
        input_layout.setContentsMargins(10, 10, 10, 10)
        input_layout.setSpacing(6)

        self.input_edit = _SubmitTextEdit(input_wrap)
        self.input_edit.setPlaceholderText("输入问题，Enter 发送，Shift+Enter 换行")
        self.input_edit.setMinimumHeight(96)
        self.input_edit.setStyleSheet(
            "QTextEdit {"
            "background: #f8fbff;"
            "border: 1px solid #d7e2ef;"
            "border-radius: 10px;"
            "padding: 9px 10px;"
            "color: #1a2433;"
            "font-size: 13px;"
            "selection-background-color: #c7dbff;"
            "selection-color: #132034;"
            "}"
            "QTextEdit:focus {"
            "border: 1px solid #82a9d8;"
            "background: #fbfdff;"
            "}"
        )
        self.input_edit.submit_requested.connect(self._emit_submit)
        input_layout.addWidget(self.input_edit)

        input_row = QHBoxLayout()
        input_row.addStretch(1)

        self.send_btn = QPushButton("发送", input_wrap)
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet(
            "QPushButton#sendBtn {"
            "background: #2f6db2;"
            "color: white;"
            "border: none;"
            "border-radius: 10px;"
            "padding: 8px 16px;"
            "font-weight: 700;"
            "font-size: 13px;"
            "}"
            "QPushButton#sendBtn:hover { background: #255d9b; }"
            "QPushButton#sendBtn:disabled { background: #a9bbd1; color: #edf2f7; }"
        )
        self.send_btn.clicked.connect(self._emit_submit)
        input_row.addWidget(self.send_btn)

        input_layout.addLayout(input_row)
        bottom_layout.addWidget(input_wrap)

        self.splitter.addWidget(self.history_panel)
        self.splitter.addWidget(self.bottom_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        frame_layout.addWidget(self.splitter, 1)

        self._set_state_chip("输入", "#e1f4e9", "#1f6a3c", "#c1e6cf")
        self._sync_anchor_controls()

    def set_model_name(self, model_name: str):
        model_text = (model_name or "").strip()
        if not model_text:
            model_text = "未设置"

        if hasattr(self, "config_btn"):
            self.config_btn.setToolTip(f"当前模型: {model_text}\\n点击可修改模型/Base URL/API Key")

    def set_anchor_widget(self, anchor_widget):
        self.anchor_widget = anchor_widget

    def show_panel(self):
        if not self._layout_restored:
            self._restore_panel_layout()
            self._layout_restored = True

        if not self.isVisible():
            self.show()
            self.raise_()
            self.activateWindow()
            self.visibility_changed.emit(True)
        self.set_state(PanelState.INPUTTING.value)
        if self._follow_anchor:
            self._reposition_to_anchor(force=True)
        else:
            self._ensure_panel_visible()
        self.focus_input()

    def hide_panel(self):
        if self.isVisible():
            self._persist_panel_layout()
            self.hide()
            self.visibility_changed.emit(False)
        self.set_state(PanelState.HIDDEN.value)

    def set_state(self, state: str, message: str = ""):
        self.state = state

        if state == PanelState.REQUESTING.value:
            self._set_state_chip("请求中", "#ffeec8", "#8a5d11", "#f0d9a0")
            self._set_input_enabled(False)
            self.status_label.setText(message or "正在等待 AI 回复...")
        elif state == PanelState.ERROR.value:
            self._set_state_chip("错误", "#f9d4d4", "#902525", "#efbcbc")
            self._set_input_enabled(True)
            self.status_label.setText(message)
        elif state == PanelState.HIDDEN.value:
            self._set_state_chip("隐藏", "#e9edf3", "#58647a", "#d3dce8")
            self._set_input_enabled(True)
            self.status_label.setText("")
        else:
            self._set_state_chip("输入", "#e1f4e9", "#1f6a3c", "#c1e6cf")
            self._set_input_enabled(True)
            self.status_label.setText(message)

        self.state_changed.emit(state)

    def append_message(self, message: ChatMessage, rendered_html: str | None = None):
        card = QFrame(self.history_widget)
        is_user = message.role == "user"
        role_name = "你" if is_user else "AI"

        card.setStyleSheet(
            "QFrame {"
            + (
                "background: rgba(239, 247, 255, 235); border:1px solid #cadef6;"
                if is_user
                else "background: rgba(255, 249, 242, 235); border:1px solid #f0ddca;"
            )
            + "border-radius:12px;}"
        )

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(11, 8, 11, 8)
        card_layout.setSpacing(4)

        header = QLabel(f"{role_name} · {self._format_timestamp(message.timestamp)}", card)
        header.setStyleSheet("font-size:11px; color:#6a7689; font-weight:700;")
        card_layout.addWidget(header)

        content = QLabel(card)
        content.setWordWrap(True)
        content.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        content.setOpenExternalLinks(True)
        content.setStyleSheet("font-size:13px; color:#1c2735; line-height:1.5;")

        if rendered_html:
            content.setTextFormat(Qt.TextFormat.RichText)
            content.setText(
                "<div style='color:#1c2735; line-height:1.5;'>"
                + rendered_html
                + "</div>"
            )
        else:
            content.setTextFormat(Qt.TextFormat.RichText)
            safe = html.escape(message.content).replace("\n", "<br>")
            content.setText("<div style='color:#1c2735; line-height:1.5;'>" + safe + "</div>")

        card_layout.addWidget(content)

        insert_index = max(0, self.history_layout.count() - 1)
        self.history_layout.insertWidget(insert_index, card)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def focus_input(self):
        if self.isVisible() and self.input_edit.isEnabled():
            self.input_edit.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def clear_history(self):
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def closeEvent(self, event):
        self.hide_panel()
        event.ignore()

    def _emit_submit(self):
        if not self.input_edit.isEnabled():
            return

        text = self.input_edit.toPlainText().strip()
        if not text:
            return

        self.input_edit.clear()
        self.submit_requested.emit(text)

    def _set_input_enabled(self, enabled: bool):
        self.input_edit.setEnabled(bool(enabled))
        self.send_btn.setEnabled(bool(enabled))

    def _set_state_chip(self, text: str, bg: str, fg: str, border: str):
        self.state_chip.setText(text)
        self.state_chip.setStyleSheet(
            "QLabel {"
            f"background: {bg};"
            f"color: {fg};"
            f"border: 1px solid {border};"
            "border-radius: 10px;"
            "padding: 2px 8px;"
            "font-size: 11px;"
            "font-weight: 700;"
            "}"
        )

    def _scroll_to_bottom(self):
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _apply_default_splitter_sizes(self):
        if not hasattr(self, "splitter"):
            return

        total_height = max(320, self.height() - 60)
        top = int(total_height * 0.62)
        bottom = max(140, total_height - top)
        self.splitter.setSizes([top, bottom])

    def _on_splitter_moved(self, _pos, _index):
        self._schedule_layout_persist()

    def _schedule_layout_persist(self):
        if self._restoring_layout:
            return
        self._persist_timer.start(220)

    def _persist_panel_layout(self):
        if self._restoring_layout:
            return

        self._settings.setValue("ai/panel_width", int(self.width()))
        self._settings.setValue("ai/panel_height", int(self.height()))
        self._settings.setValue("ai/panel_follow_anchor", bool(self._follow_anchor))

        if not self._follow_anchor:
            self._settings.setValue("ai/panel_pos_x", int(self.x()))
            self._settings.setValue("ai/panel_pos_y", int(self.y()))

        splitter_sizes = self.splitter.sizes()
        if len(splitter_sizes) >= 2:
            self._settings.setValue(
                "ai/panel_splitter_sizes",
                [int(splitter_sizes[0]), int(splitter_sizes[1])],
            )

        self._settings.sync()

    def _restore_panel_layout(self):
        self._restoring_layout = True
        try:
            screen_geo = QApplication.primaryScreen().availableGeometry()

            width = self._to_int(self._settings.value("ai/panel_width"), self.width())
            height = self._to_int(self._settings.value("ai/panel_height"), self.height())

            max_width = max(self.minimumWidth(), screen_geo.width() - 10)
            max_height = max(self.minimumHeight(), screen_geo.height() - 10)

            width = max(self.minimumWidth(), min(width, max_width))
            height = max(self.minimumHeight(), min(height, max_height))
            self.resize(width, height)

            self._follow_anchor = self._to_bool(self._settings.value("ai/panel_follow_anchor", True), True)
            if not self._follow_anchor:
                pos_x = self._to_int(self._settings.value("ai/panel_pos_x"), self.x())
                pos_y = self._to_int(self._settings.value("ai/panel_pos_y"), self.y())
                self.move(self._clamp_top_left(QPoint(pos_x, pos_y)))

            saved_sizes = self._settings.value("ai/panel_splitter_sizes", None)
            splitter_sizes = self._parse_splitter_sizes(saved_sizes)
            if splitter_sizes is not None:
                top = max(self.history_panel.minimumHeight(), splitter_sizes[0])
                bottom = max(self.bottom_panel.minimumHeight(), splitter_sizes[1])
                self.splitter.setSizes([top, bottom])
            else:
                self._apply_default_splitter_sizes()
        finally:
            self._restoring_layout = False
            self._sync_anchor_controls()

    @staticmethod
    def _to_int(value, default_value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default_value)

    @staticmethod
    def _parse_splitter_sizes(saved_value):
        if isinstance(saved_value, (list, tuple)) and len(saved_value) >= 2:
            try:
                return [int(saved_value[0]), int(saved_value[1])]
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _to_bool(value, default_value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            low = value.strip().lower()
            if low in ("1", "true", "yes", "on"):
                return True
            if low in ("0", "false", "no", "off"):
                return False
        try:
            return bool(int(value))
        except (TypeError, ValueError):
            return bool(default_value)

    def _reposition_to_anchor(self, force=False):
        if not self.isVisible() or self.anchor_widget is None:
            return

        if not self._follow_anchor and not force:
            return

        anchor_geo = self.anchor_widget.frameGeometry()
        screen_geo = QApplication.primaryScreen().availableGeometry()
        margin = 16

        x = anchor_geo.right() + margin
        if x + self.width() > screen_geo.right():
            x = anchor_geo.left() - self.width() - margin

        if x < screen_geo.left():
            x = max(screen_geo.left(), screen_geo.right() - self.width() - margin)

        y = anchor_geo.bottom() - self.height() + 18
        y = max(screen_geo.top() + 10, min(y, screen_geo.bottom() - self.height() - 10))

        self.move(int(x), int(y))

    def _ensure_panel_visible(self):
        self.move(self._clamp_top_left(self.pos()))

    def _clamp_top_left(self, desired_pos):
        target_point = QPoint(int(desired_pos.x()), int(desired_pos.y()))
        center_point = QPoint(target_point.x() + self.width() // 2, target_point.y() + self.height() // 2)

        screen = QApplication.screenAt(center_point)
        if screen is None:
            screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry()

        min_x = screen_geo.left()
        min_y = screen_geo.top()
        max_x = max(min_x, screen_geo.right() - self.width())
        max_y = max(min_y, screen_geo.bottom() - self.height())

        return QPoint(
            max(min_x, min(target_point.x(), max_x)),
            max(min_y, min(target_point.y(), max_y)),
        )

    def _on_panel_drag_started(self):
        if self._follow_anchor:
            self._follow_anchor = False
            self._sync_anchor_controls()

    def _move_panel_free(self, desired_pos):
        self.move(self._clamp_top_left(desired_pos))

    def _on_panel_drag_finished(self):
        self._schedule_layout_persist()

    def _on_return_clicked(self):
        self._follow_anchor = True
        self._sync_anchor_controls()
        if self.isVisible():
            self._reposition_to_anchor(force=True)
        self._schedule_layout_persist()

    def _sync_anchor_controls(self):
        if hasattr(self, "return_btn"):
            self.return_btn.setEnabled(not self._follow_anchor)

    @staticmethod
    def _format_timestamp(value: str) -> str:
        if not value:
            return datetime.now().strftime("%H:%M:%S")
        try:
            dt = datetime.fromisoformat(value)
            return dt.strftime("%H:%M:%S")
        except ValueError:
            return value

    def _init_resize_handles(self):
        self._resize_handle_thickness = 6
        self._resize_corner_size = 14
        self._resize_handles = {
            "left": _ResizeHandle(self, Qt.Edge.LeftEdge, Qt.CursorShape.SizeHorCursor),
            "right": _ResizeHandle(self, Qt.Edge.RightEdge, Qt.CursorShape.SizeHorCursor),
            "top": _ResizeHandle(self, Qt.Edge.TopEdge, Qt.CursorShape.SizeVerCursor),
            "bottom": _ResizeHandle(self, Qt.Edge.BottomEdge, Qt.CursorShape.SizeVerCursor),
            "top_left": _ResizeHandle(
                self,
                Qt.Edge.TopEdge | Qt.Edge.LeftEdge,
                Qt.CursorShape.SizeFDiagCursor,
            ),
            "top_right": _ResizeHandle(
                self,
                Qt.Edge.TopEdge | Qt.Edge.RightEdge,
                Qt.CursorShape.SizeBDiagCursor,
            ),
            "bottom_left": _ResizeHandle(
                self,
                Qt.Edge.BottomEdge | Qt.Edge.LeftEdge,
                Qt.CursorShape.SizeBDiagCursor,
            ),
            "bottom_right": _ResizeHandle(
                self,
                Qt.Edge.BottomEdge | Qt.Edge.RightEdge,
                Qt.CursorShape.SizeFDiagCursor,
            ),
        }

        for handle in self._resize_handles.values():
            handle.raise_()

        self._layout_resize_handles()

    def _layout_resize_handles(self):
        handles = getattr(self, "_resize_handles", None)
        if not handles:
            return

        w = self.width()
        h = self.height()
        t = self._resize_handle_thickness
        c = self._resize_corner_size

        handles["left"].setGeometry(0, c, t, max(1, h - 2 * c))
        handles["right"].setGeometry(max(0, w - t), c, t, max(1, h - 2 * c))
        handles["top"].setGeometry(c, 0, max(1, w - 2 * c), t)
        handles["bottom"].setGeometry(c, max(0, h - t), max(1, w - 2 * c), t)

        handles["top_left"].setGeometry(0, 0, c, c)
        handles["top_right"].setGeometry(max(0, w - c), 0, c, c)
        handles["bottom_left"].setGeometry(0, max(0, h - c), c, c)
        handles["bottom_right"].setGeometry(max(0, w - c), max(0, h - c), c, c)

        for handle in handles.values():
            handle.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_resize_handles()
        if self.isVisible():
            self._schedule_layout_persist()

    def moveEvent(self, event):
        super().moveEvent(event)
        if self.isVisible() and not self._follow_anchor:
            self._schedule_layout_persist()
