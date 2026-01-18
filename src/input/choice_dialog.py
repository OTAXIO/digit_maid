from PyQt6.QtWidgets import QMessageBox

def ask_save_location(parent):
    """
    询问用户截图保存位置
    Returns:
        str: 'desktop', 'default', 'none'
    """
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle("截图保存")
    msg_box.setText("请选择截图保存的位置：")
    
    # 添加按钮
    btn_desktop = msg_box.addButton("桌面", QMessageBox.ButtonRole.ActionRole)
    btn_default = msg_box.addButton("默认", QMessageBox.ButtonRole.ActionRole)
    btn_cancel = msg_box.addButton("不保存", QMessageBox.ButtonRole.RejectRole)
    
    msg_box.exec()
    
    clicked_button = msg_box.clickedButton()
    
    if clicked_button == btn_desktop:
        return "desktop"
    elif clicked_button == btn_default:
        return "default"
    else:
        return "none"
