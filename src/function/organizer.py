import os
import shutil
from pathlib import Path

def get_desktop_path():
    return os.path.join(os.path.expanduser("~"), "Desktop")

def organize_desktop():
    """
    整理桌面文件，将其分类移动到文件夹中。
    注意：这仅作为演示，实际使用请谨慎。
    """
    desktop_path = get_desktop_path()
    
    # 定义分类规则
    directories = {
        "Images": [".jpeg", ".jpg", ".tiff", ".gif", ".bmp", ".png", ".bpg", "svg", ".heif", ".psd"],
        "Videos": [".avi", ".flv", ".wmv", ".mov", ".mp4", ".webm", ".vob", ".mng", ".qt", ".mpg", ".mpeg", ".3gp"],
        "Documents": [".oxps", ".epub", ".pages", ".docx", ".doc", ".fdf", ".ods", ".odt", ".pwi", ".xsn", ".xps", ".dotx", ".docm", ".dox", ".rvg", ".rtf", ".rtfd", ".wpd", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf", ".txt", ".md"],
        "Archives": [".a", ".ar", ".cpio", ".iso", ".tar", ".gz", ".rz", ".7z", ".dmg", ".rar", ".xar", ".zip"],
        "Audio": [".aac", ".aa", ".aac", ".dvf", ".m4a", ".m4b", ".m4p", ".mp3", ".msv", "ogg", "oga", ".raw", ".vox", ".wav", ".wma"],
        "Programming": [".py", ".java", ".cpp", ".c", ".html", ".css", ".js", ".json", ".xml"]
    }

    print(f"开始整理桌面: {desktop_path}")
    
    for filename in os.listdir(desktop_path):
        file_path = os.path.join(desktop_path, filename)
        
        # 跳过目录和自身产生的文件夹
        if os.path.isdir(file_path):
            continue
            
        file_extension = os.path.splitext(filename)[1].lower()
        
        moved = False
        for category, extensions in directories.items():
            if file_extension in extensions:
                category_path = os.path.join(desktop_path, category)
                if not os.path.exists(category_path):
                    os.makedirs(category_path)
                
                try:
                    shutil.move(file_path, os.path.join(category_path, filename))
                    print(f"移动 {filename} 到 {category}")
                    moved = True
                except Exception as e:
                    print(f"移动 {filename} 失败: {e}")
                break
        
        # 如果没有匹配的分类，可以选择移动到 Others 或者不做处理
        # 这里为了安全起见，暂不做处理
    
    return "桌面整理完成"
