from PyQt6.QtWidgets import QInputDialog, QLineEdit

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
