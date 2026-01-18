import os
import shutil
from pathlib import Path

# 移动历史记录栈，每次整理操作保存一个列表
# 格式: [ [(原路径, 新路径), ...], [(原路径, 新路径), ...], ... ]
_move_history = []

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
    
    # 本次整理的移动记录
    current_moves = []
    moved_count = 0
    
    for filename in os.listdir(desktop_path):
        file_path = os.path.join(desktop_path, filename)
        
        # 跳过目录和自身产生的文件夹
        if os.path.isdir(file_path):
            continue
            
        file_extension = os.path.splitext(filename)[1].lower()
        
        for category, extensions in directories.items():
            if file_extension in extensions:
                category_path = os.path.join(desktop_path, category)
                if not os.path.exists(category_path):
                    os.makedirs(category_path)
                
                new_path = os.path.join(category_path, filename)
                try:
                    shutil.move(file_path, new_path)
                    # 记录移动操作 (原路径, 新路径)
                    current_moves.append((file_path, new_path))
                    print(f"移动 {filename} 到 {category}")
                    moved_count += 1
                except Exception as e:
                    print(f"移动 {filename} 失败: {e}")
                break
        
        # 如果没有匹配的分类，可以选择移动到 Others 或者不做处理
        # 这里为了安全起见，暂不做处理
    
    # 如果有移动操作，保存到历史记录
    if current_moves:
        _move_history.append(current_moves)
    
    return f"桌面整理完成，共移动 {moved_count} 个文件"

def undo_organize():
    """
    撤销上一次整理操作，将文件移回原位置。
    """
    if not _move_history:
        return "没有可撤销的操作"
    
    # 取出最近一次的移动记录
    last_moves = _move_history.pop()
    
    restored_count = 0
    failed_count = 0
    
    # 逆序恢复，确保文件按相反顺序移回
    for original_path, current_path in reversed(last_moves):
        try:
            if os.path.exists(current_path):
                # 确保原目录存在
                original_dir = os.path.dirname(original_path)
                if not os.path.exists(original_dir):
                    os.makedirs(original_dir)
                
                shutil.move(current_path, original_path)
                print(f"恢复 {os.path.basename(original_path)} 到桌面")
                restored_count += 1
            else:
                print(f"文件不存在，无法恢复: {current_path}")
                failed_count += 1
        except Exception as e:
            print(f"恢复失败: {e}")
            failed_count += 1
    
    # 清理空的分类文件夹
    _cleanup_empty_folders()
    
    if failed_count > 0:
        return f"撤销完成，恢复 {restored_count} 个文件，{failed_count} 个失败"
    return f"撤销完成，已恢复 {restored_count} 个文件"

def _cleanup_empty_folders():
    """
    清理桌面上空的分类文件夹
    """
    desktop_path = get_desktop_path()
    category_folders = ["Images", "Videos", "Documents", "Archives", "Audio", "Programming"]
    
    for folder in category_folders:
        folder_path = os.path.join(desktop_path, folder)
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            # 检查文件夹是否为空
            if not os.listdir(folder_path):
                try:
                    os.rmdir(folder_path)
                    print(f"已删除空文件夹: {folder}")
                except Exception as e:
                    print(f"删除空文件夹失败: {e}")

def can_undo():
    """
    检查是否有可撤销的操作
    """
    return len(_move_history) > 0

def get_undo_count():
    """
    获取可撤销的操作次数
    """
    return len(_move_history)
