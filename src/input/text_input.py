from PyQt6.QtWidgets import (
    QInputDialog,
    QLineEdit,
    QComboBox,
    QDialog,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QDoubleSpinBox,
)
from PyQt6.QtCore import Qt

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
    text, ok = QInputDialog.getText(parent_widget, title, label, QLineEdit.EchoMode.Normal, "")
    
    if ok and text:
        return text.strip()
    return None


def get_secret_input(parent_widget, title="API Key", label="请输入密钥:"):
    """弹出密码回显输入框，返回去除首尾空格后的输入；取消时返回 None。"""
    text, ok = QInputDialog.getText(parent_widget, title, label, QLineEdit.EchoMode.Password, "")
    if ok and text:
        return text.strip()
    return None


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
    dialog = QDialog(parent_widget)
    dialog.setWindowTitle(title)
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

    label_widget = QLabel(label, dialog)
    layout.addWidget(label_widget)

    spin = QDoubleSpinBox(dialog)
    spin.setDecimals(max(0, int(decimals)))
    spin.setRange(float(min_value), float(max_value))
    spin.setSingleStep(float(step))
    clamped_value = max(float(min_value), min(float(max_value), float(value)))
    spin.setValue(clamped_value)
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
        return round(value, max(0, int(decimals)))
    return None


def get_ai_config_input(
    parent_widget,
    provider_presets,
    current_provider="",
    current_model="",
    current_base_url="",
    current_api_key="",
):
    """在单个对话框中编辑 AI 供应商、模型、Base URL 与 API Key。"""
    dialog = QDialog(parent_widget)
    dialog.setWindowTitle("AI 配置")
    dialog.setModal(True)
    dialog.setMinimumWidth(460)
    dialog.setStyleSheet(
        """
        QDialog {
            background-color: rgba(248, 250, 253, 247);
            border: 1px solid #bfd0e5;
            border-radius: 12px;
        }
        QLabel {
            color: #2f3f54;
            font-size: 13px;
            font-weight: 700;
        }
        QLineEdit, QComboBox {
            background: #ffffff;
            border: 1px solid #c9d8ea;
            border-radius: 8px;
            padding: 6px 8px;
            font-size: 13px;
            color: #1f2d3d;
        }
        QLineEdit:focus, QComboBox:focus {
            border: 1px solid #7ea7d7;
        }
        QPushButton {
            min-width: 96px;
            padding: 7px 12px;
            border-radius: 9px;
            font-size: 13px;
            font-weight: 700;
        }
        QPushButton#ok_btn {
            background-color: #2f6db2;
            color: white;
            border: none;
        }
        QPushButton#ok_btn:hover {
            background-color: #255d9b;
        }
        QPushButton#cancel_btn {
            background-color: #edf2f8;
            color: #4b6078;
            border: 1px solid #d4deea;
        }
        QPushButton#cancel_btn:hover {
            background-color: #e5edf7;
        }
        """
    )

    provider_list = list(provider_presets or [])
    if not provider_list:
        return None

    preset_map = {preset.name: preset for preset in provider_list}

    root = QVBoxLayout(dialog)
    root.setContentsMargins(14, 14, 14, 12)
    root.setSpacing(10)

    desc = QLabel("可在此修改供应商、模型、服务地址和 API Key", dialog)
    desc.setStyleSheet("font-size:12px; color:#5e7188; font-weight:500;")
    root.addWidget(desc)

    form = QFormLayout()
    form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
    form.setHorizontalSpacing(12)
    form.setVerticalSpacing(10)

    provider_combo = QComboBox(dialog)
    provider_combo.addItems([preset.name for preset in provider_list])
    form.addRow("供应商", provider_combo)

    model_edit = QLineEdit(dialog)
    model_edit.setPlaceholderText("例如 deepseek-chat")
    form.addRow("模型", model_edit)

    base_url_edit = QLineEdit(dialog)
    base_url_edit.setPlaceholderText("例如 https://api.deepseek.com")
    form.addRow("Base URL", base_url_edit)

    key_edit = QLineEdit(dialog)
    key_edit.setEchoMode(QLineEdit.EchoMode.Password)
    key_edit.setPlaceholderText("请输入 API Key")
    form.addRow("API Key", key_edit)

    root.addLayout(form)

    target_provider = current_provider if current_provider in preset_map else provider_list[0].name
    provider_combo.setCurrentText(target_provider)

    model_edit.setText(str(current_model or "").strip())
    base_url_edit.setText(str(current_base_url or "").strip())
    key_edit.setText(str(current_api_key or "").strip())

    def apply_provider_defaults(provider_name):
        preset = preset_map.get(provider_name)
        if preset is None:
            return
        base_url_edit.setText(preset.base_url)
        model_edit.setText(preset.default_model)

    provider_combo.currentTextChanged.connect(apply_provider_defaults)

    if not base_url_edit.text().strip() or not model_edit.text().strip():
        apply_provider_defaults(target_provider)

    tips = QLabel("提示：切换供应商会自动填充推荐 Base URL 与模型，可手动再改。", dialog)
    tips.setWordWrap(True)
    tips.setStyleSheet("font-size:12px; color:#667c95; font-weight:500;")
    root.addWidget(tips)

    btn_row = QHBoxLayout()
    btn_row.addStretch(1)

    cancel_btn = QPushButton("取消", dialog)
    cancel_btn.setObjectName("cancel_btn")
    cancel_btn.clicked.connect(dialog.reject)
    btn_row.addWidget(cancel_btn)

    ok_btn = QPushButton("保存", dialog)
    ok_btn.setObjectName("ok_btn")

    error_label = QLabel("", dialog)
    error_label.setWordWrap(True)
    error_label.setStyleSheet("font-size:12px; color:#b73434; font-weight:600;")
    root.addWidget(error_label)

    def on_accept():
        provider = provider_combo.currentText().strip()
        model = model_edit.text().strip()
        base_url = base_url_edit.text().strip()
        api_key = key_edit.text().strip()

        if not provider:
            error_label.setText("请选择供应商。")
            return
        if not model:
            error_label.setText("模型不能为空。")
            return
        if not base_url:
            error_label.setText("Base URL 不能为空。")
            return
        if not api_key:
            error_label.setText("API Key 不能为空。")
            return

        dialog._result = {
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "api_key": api_key,
        }
        dialog.accept()

    ok_btn.clicked.connect(on_accept)
    btn_row.addWidget(ok_btn)

    root.addLayout(btn_row)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return getattr(dialog, "_result", None)
    return None
