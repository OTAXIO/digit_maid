from PyQt6.QtWidgets import (
    QLineEdit,
    QDialog,
    QDoubleSpinBox,
)
from PyQt6.QtCore import Qt

from src.core.numeric import bounded_float, bounded_int
from src.ui.theme.dialogs import ThemedDialog


MAX_TEXT_INPUT_CHARS = 4096
MAX_DOUBLE_INPUT_ABS = 1.0e12
MAX_DOUBLE_INPUT_DECIMALS = 12

def get_text_input(parent_widget, title="输入", label="请输入内容:"):
    """
    弹出一个简单的文本输入对话框，获取用户输入。
    
    Args:
        parent_widget: 父窗口部件
        title (str): 对话框标题
        label (str): 输入框标签文字
        
    Returns:
        str: 用户输入的文本。如果用户取消，则返回 None。
    """
    dialog = ThemedDialog(title, label, parent_widget)
    editor = QLineEdit(dialog)
    editor.setMaxLength(MAX_TEXT_INPUT_CHARS)
    dialog.content_layout.addWidget(editor)
    dialog.add_action("取消", dialog.reject)
    dialog.add_action("确定", dialog.accept, primary=True)
    dialog.finish_layout()
    editor.setFocus()

    if dialog.exec() == QDialog.DialogCode.Accepted:
        text = editor.text().strip()
        if text:
            return text
    return None


def _normalize_double_input_options(value, min_value, max_value, decimals, step):
    minimum = bounded_float(
        min_value,
        default=0.0,
        minimum=-MAX_DOUBLE_INPUT_ABS,
        maximum=MAX_DOUBLE_INPUT_ABS,
    )
    maximum = bounded_float(
        max_value,
        default=10.0,
        minimum=-MAX_DOUBLE_INPUT_ABS,
        maximum=MAX_DOUBLE_INPUT_ABS,
    )
    if minimum > maximum:
        minimum, maximum = maximum, minimum

    decimal_places = bounded_int(
        decimals,
        default=1,
        minimum=0,
        maximum=MAX_DOUBLE_INPUT_DECIMALS,
    )
    step_value = bounded_float(
        step,
        default=max(10.0 ** (-decimal_places), 0.1),
        minimum=10.0 ** (-MAX_DOUBLE_INPUT_DECIMALS),
        maximum=MAX_DOUBLE_INPUT_ABS,
    )
    initial_value = bounded_float(
        value,
        default=minimum,
        minimum=minimum,
        maximum=maximum,
    )
    return initial_value, minimum, maximum, decimal_places, step_value


def get_double_input(
    parent_widget,
    title="输入数值",
    label="请输入数值:",
    value=1.0,
    min_value=0.0,
    max_value=10.0,
    decimals=1,
    step=0.1,
):
    """弹出一个自定义数值输入框，返回 float；取消时返回 None。"""
    value, min_value, max_value, decimals, step = _normalize_double_input_options(
        value,
        min_value,
        max_value,
        decimals,
        step,
    )
    dialog = ThemedDialog(title, label, parent_widget)

    spin = QDoubleSpinBox(dialog)
    spin.setDecimals(decimals)
    spin.setRange(min_value, max_value)
    spin.setSingleStep(step)
    spin.setValue(value)
    spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
    spin.selectAll()
    dialog.content_layout.addWidget(spin)
    dialog.add_action("取消", dialog.reject)
    dialog.add_action("确定", dialog.accept, primary=True)
    dialog.finish_layout()
    spin.setFocus()

    if dialog.exec() == QDialog.DialogCode.Accepted:
        value = spin.value()
        return round(value, decimals)
    return None
