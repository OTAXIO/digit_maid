"""公共控件与页面样式。改颜色请到 theme/__init__.py，改布局请到窗口类。"""

from . import qss


BASE = qss('''
    QWidget { font-family: "$font"; font-size: 13px; color: $ink; }
    QLabel { background: transparent; border: none; }
    QLabel[role="eyebrow"] { color: $accent; font-size: 10px; font-weight: 600; letter-spacing: 2px; }
    QLabel[role="title"] { color: $ink; font-size: 24px; font-weight: 600; }
    QLabel[role="muted"] { color: $muted; font-size: 12px; }
    QPushButton { background: $surface; color: $ink; border: 1px solid $line;
        border-radius: 10px; padding: 8px 14px; min-height: 20px; font-weight: 500; }
    QPushButton:hover { background: $inset; border-color: $faint; }
    QPushButton:pressed { background: $line; }
    QPushButton:focus { border-color: $accent; }
    QPushButton:disabled { background: $inset; color: $faint; border-color: $line; }
    QPushButton[role="primary"], QPushButton#ok_btn { background: $accent; color: $white; border-color: $accent; }
    QPushButton[role="primary"]:hover, QPushButton#ok_btn:hover { background: $accent_hover; }
    QPushButton[role="primary"]:pressed, QPushButton#ok_btn:pressed { background: $accent_pressed; }
    QLineEdit, QTextEdit, QDoubleSpinBox { background: $surface; border: 1px solid $line;
        border-radius: 10px; padding: 10px; color: $ink;
        selection-background-color: $accent_soft; selection-color: $ink; }
    QLineEdit:focus, QTextEdit:focus, QDoubleSpinBox:focus { border-color: $accent; background: $white; }
    QScrollBar:vertical { background: transparent; width: 6px; margin: 3px 0; }
    QScrollBar::handle:vertical { background: $line; border-radius: 3px; min-height: 24px; }
    QScrollBar::handle:vertical:hover { background: $faint; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
    QToolTip { background: $charcoal; color: $surface; border: none; padding: 6px; }
''')


TODO = BASE + qss('''
    QFrame#todo_card { background: $canvas; border: 1px solid $line; border-radius: 22px; }
    QLabel#title_label { font-size: 26px; font-weight: 600; color: $ink; }
    QLabel#subtitle_label, QLabel#month_caption, QLabel#editor_hint { color: $muted; font-size: 11px; }
    QLabel#section_title { font-size: 14px; font-weight: 600; }
    QLabel#daily_summary { color: $muted; font-size: 11px; padding-bottom: 4px; }
    QFrame#section_card { background: $surface; border: 1px solid $line; border-radius: 16px; }
    QPushButton#close_btn { color: $muted; background: transparent; border: none;
        border-radius: 9px; min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px;
        padding: 0; font-size: 21px; }
    QPushButton#close_btn:hover { background: $accent_soft; color: $accent; }
    QPushButton#secondary_btn { font-size: 11px; padding: 6px 10px; }
    QPushButton#todo_page_btn { font-size: 11px; padding: 3px 10px; min-height: 20px; }
    QLabel#todo_page_label { color: $muted; font-size: 11px; min-width: 40px; qproperty-alignment: AlignCenter; }
    QListWidget { background: transparent; border: none; padding: 2px; outline: 0; }
    QListWidget::item { padding: 9px 10px; margin: 3px 0; background: $canvas;
        border: 1px solid $canvas; border-radius: 9px; }
    QListWidget::item:hover { border-color: $line; background: $inset; }
    QListWidget::item:selected { background: $accent_soft; color: $accent; border-color: $accent; }
    QFrame#input_card { background: $inset; border: none; border-radius: 12px; }
    QLineEdit#ddl_input { min-width: 54px; max-width: 54px; padding: 10px 6px; }
    QFrame#task_editor_page { background: transparent; border: none; }
    QLabel#editor_state_badge { color: $accent; background: $accent_soft; border-radius: 7px;
        padding: 4px 9px; font-size: 11px; font-weight: 600; }
    QLabel#editor_state_badge[completed="true"] { color: $completed; background: $completed_bg; }
    QLabel#editor_hint[error="true"] { color: $accent; }
    QTextEdit#task_editor { background: $canvas; border: 1px solid $line;
        border-radius: 12px; padding: 14px; font-size: 15px; }
    QTextEdit#task_editor:focus { border-color: $accent; background: $white; }
    QTextEdit#task_editor[completed="true"] { background: $completed_bg; color: $completed;
        border-color: $line; text-decoration: line-through; }
    QPushButton#back_to_list_btn { background: transparent; border: none; color: $muted;
        padding: 4px 6px; font-size: 11px; }
    QPushButton#back_to_list_btn:hover { color: $accent; background: $accent_soft; }
    QPushButton#delete_task_btn, QPushButton#complete_task_btn { min-height: 24px; }
    QPushButton#delete_task_btn { color: $accent; }
    QPushButton#delete_task_btn:hover { background: $accent_soft; }
    QPushButton#complete_task_btn { background: $accent; border-color: $accent; color: $white; }
    QPushButton#complete_task_btn:hover { background: $accent_hover; }
    QPushButton#complete_task_btn[completed="true"] { color: $ink; background: $completed_bg; border-color: $line; }
    QPushButton#complete_task_btn[completed="true"]:hover { background: $inset; }
    QPushButton#icon_action_btn { background: $charcoal; color: $white; border: none;
        min-width: 32px; max-width: 32px; min-height: 36px; max-height: 36px; padding: 0; font-size: 22px; }
    QPushButton#icon_action_btn:hover { background: $accent; }
    QCalendarWidget { background: transparent; border: none; }
    QCalendarWidget QWidget { alternate-background-color: $surface; }
    QCalendarWidget QToolButton { color: $ink; background: transparent; border: none;
        padding: 4px 10px; font-size: 12px; font-weight: 500; }
    QCalendarWidget QToolButton:hover { background: $inset; border-radius: 7px; }
    QCalendarWidget QToolButton#qt_calendar_prevmonth, QCalendarWidget QToolButton#qt_calendar_nextmonth {
        min-width: 24px; max-width: 24px; padding: 4px 0; }
    QCalendarWidget QToolButton#qt_calendar_monthbutton, QCalendarWidget QToolButton#qt_calendar_yearbutton {
        min-width: 64px; padding: 4px 14px 4px 6px; }
    QCalendarWidget QAbstractItemView:enabled { color: $ink; background: $surface;
        selection-background-color: $accent; selection-color: $white; outline: 0; }
    QCalendarWidget QWidget#qt_calendar_navigationbar { background: $surface; }
''')


REMINDER = BASE + qss('''
    QFrame#reminder_card { background: $canvas; border: 1px solid $line; border-radius: 20px; }
    QLabel#eyebrow { color: $accent; font-size: 10px; font-weight: 600; letter-spacing: 2px; }
    QLabel#reminder_title { font-size: 25px; font-weight: 600; }
    QLabel#reminder_subtitle { color: $muted; font-size: 12px; }
    QScrollArea, QScrollArea > QWidget > QWidget { border: none; background: transparent; }
    QFrame#urgent_item { background: $amber_soft; border: 1px solid $line;
        border-left: 4px solid $accent; border-radius: 12px; }
    QFrame#queued_item { background: $surface; border: 1px solid $line; border-radius: 12px; }
    QLabel#task_time { color: $accent; font-size: 14px; font-weight: 600; }
    QLabel#task_text { font-size: 15px; font-weight: 500; }
    QLabel#task_remaining { color: $amber; font-size: 11px; }
    QPushButton#complete_btn { color: $white; background: $accent; border-color: $accent; }
    QPushButton#complete_btn:hover { background: $accent_hover; }
    QPushButton#complete_btn:disabled { background: $inset; color: $faint; border-color: $line; }
''')


def list_menu_style(scale=1.0):
    """列表菜单与圆形菜单共享色板，尺寸仍跟随原有缩放设置。"""
    return BASE + qss('''
        QMenu { background: $surface; border: 1px solid $line; border-radius: 12px; padding: 6px; }
        QMenu::item { padding: ${vertical}px ${horizontal}px; font-size: ${size}px; border-radius: 7px; }
        QMenu::item:selected { background: $accent_soft; color: $accent; }
        QMenu::separator { height: 1px; background: $line; margin: 5px 10px; }
    ''', vertical=max(5, int(6 * scale)), horizontal=max(14, int(18 * scale)), size=max(12, int(13 * scale)))
