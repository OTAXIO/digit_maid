from PyQt6.QtWidgets import (
    QInputDialog,
    QLineEdit,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QDoubleSpinBox,
)
from PyQt6.QtCore import Qt

from src.core.numeric import bounded_float, bounded_int


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
    dialog = QInputDialog(parent_widget)
    dialog.setWindowTitle(str(title)[:200])
    dialog.setLabelText(str(label)[:500])
    dialog.setInputMode(QInputDialog.InputMode.TextInput)
    dialog.setTextEchoMode(QLineEdit.EchoMode.Normal)
    editor = dialog.findChild(QLineEdit)
    if editor is not None:
        editor.setMaxLength(MAX_TEXT_INPUT_CHARS)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        text = dialog.textValue().strip()
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
    dialog = QDialog(parent_widget)
    dialog.setWindowTitle(str(title)[:200])
    dialog.setModal(True)
    dialog.setMinimumWidth(360)
    dialog.setStyleSheet(
        """
        QDialog {
            background-color: rgba(255, 248, 245, 245);
            border: 2px solid #ff3b30;
            border-radius: 12px;
        }
        QLabel {
            color: #4a2b2b;
            font-size: 14px;
            font-weight: 700;
        }
        QDoubleSpinBox {
            background: white;
            border: 2px solid #ffb3ad;
            border-radius: 10px;
            padding: 8px 10px;
            font-size: 16px;
            font-weight: 700;
            color: #2b2b2b;
        }
        QPushButton {
            min-width: 96px;
            padding: 8px 14px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 700;
        }
        QPushButton#ok_btn {
            background-color: #ff3b30;
            color: white;
            border: none;
        }
        QPushButton#ok_btn:hover {
            background-color: #ff5a52;
        }
        QPushButton#cancel_btn {
            background-color: #f2e7e5;
            color: #6a4a4a;
            border: 1px solid #d7c2bf;
        }
        QPushButton#cancel_btn:hover {
            background-color: #eadedb;
        }
        """
    )

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(16, 16, 16, 14)
    layout.setSpacing(12)

    label_widget = QLabel(str(label)[:500], dialog)
    layout.addWidget(label_widget)

    spin = QDoubleSpinBox(dialog)
    spin.setDecimals(decimals)
    spin.setRange(min_value, max_value)
    spin.setSingleStep(step)
    spin.setValue(value)
    spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
    spin.selectAll()
    layout.addWidget(spin)

    btn_row = QHBoxLayout()
    btn_row.addStretch(1)

    cancel_btn = QPushButton("取消", dialog)
    cancel_btn.setObjectName("cancel_btn")
    cancel_btn.clicked.connect(dialog.reject)
    btn_row.addWidget(cancel_btn)

    ok_btn = QPushButton("确定", dialog)
    ok_btn.setObjectName("ok_btn")
    ok_btn.clicked.connect(dialog.accept)
    btn_row.addWidget(ok_btn)

    layout.addLayout(btn_row)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        value = spin.value()
        return round(value, decimals)
    return None
