# Digit Maid (数字女仆)
## A Virtual Maid on your PC

The aim of this project is to create a virtual maid that can help you with various tasks on your computer, such as organizing files, managing schedules, and providing reminders, all wrapped in a cute, interactive desktop companion.

---

## 🌟 当前实现功能 (Implemented Features)

- **互动式桌宠 UI**: 基于 \PyQt6\ 构建的无边框透明窗口，支持鼠标自由拖拽。
- **自定义右键菜单**: 全新设计的环形动画菜单（支持灵活的分页、多级子菜单和边缘防遮挡）。
- **对话提示气泡**: 与 UI 风格统一（红黑配色）的独立信息反馈气泡。
- **打开常用软件**: 根据配置文件动态按需拉起独立程序的子进程，防止卡顿。
- **屏幕截图工具**: 一键隐藏唤醒、截取屏幕并可选择保存位置。
- **完善的异步支持**: 使用现代 GUI 事件循环与异步定时器，保证桌宠状态始终平稳，不受子任务生命周期影响。
- **待办面板**: 独立浮窗，支持日历标记、今日分页、DDL 排序与行内编辑。
- **键盘控制移动**: 菜单开启控制模式，支持键盘方向移动与上下浮动。

---

## 🚀 快速开始 (Getting Started)

### 📥 下载与安装指南
详细下载、安装说明请查看：[DOWNLOAD_GUIDE.md](./DOWNLOAD_GUIDE.md)

### 1. 环境准备 (Environment Setup)
推荐使用 Python 3.10+ 环境。安装项目运行必须的底层依赖（部分 AI 和视觉组件后续实装）：
```bash
pip install PyQt6 PyYAML
```

### 2. 运行程序
```bash
python src/core/run.py
```

---

## 🧭 使用指南 (Usage Tips)

### 🎮 控制移动 (Keyboard Control)
- 入口：右键菜单 -> TOOL -> 控制移动，或环形菜单 -> TOOL -> 控制移动。
- 按键：A / D 或 ← / → 水平移动；W / ↑ / 空格 上升；S / ↓ 快速下落；Esc 退出。
- 提示：控制模式会暂停闲置动作，退出后自动恢复。

### 📝 待办面板 (Todo Panel)
- 入口：右键菜单 -> 待办，或环形菜单 -> 待办。
- 新增：DDL 输入 `HH:MM` + 内容，按回车或点击上传按钮。
- 编辑/删除：点击条目进入行内编辑，回车保存；选中后出现删除按钮。
- 日历：可切换日期查看当日任务；“回到今天”快速回到当天；“收起日历/展开日历”切换视图。

---

## 📂 项目结构 (Project Structure)

```text
dmaid/
├── resource/                   # 图片、音效等静态资源存放目录
└── src/
    ├── core/
    │   └── run.py              # 程序主入口 (Main Entry Point)
    ├── function/
    │   ├── apps.yaml           # App启动路径配置文件
    │   ├── open_app.py         # 应用程序拉起逻辑
    │   ├── screen_shot.py      # 屏幕截图相关逻辑
    │   └── organizer.py        # 桌面整理逻辑（待增强）
    ├── input/
    │   ├── circular_menu.py    # 环形动画菜单 UI 组件
    │   └── choice_dialog.py    # 弹窗式选择对话框逻辑
    └── ui/
        ├── maid_window.py       # 桌宠主界面及交互事件
        ├── action.py           # 菜单及功能绑定控制器
        └── dialogue.py         # 提示气泡 UI 组件
```

---

## 🛠️ 自定义配置指南

### 如何添加新的应用程序到菜单？
所有的软件启动选项都是通过 `src/function/apps.yaml` 动态加载的。不需要修改代码，只需按以下格式往 YAML 文件中添加内容：

```yaml
app_paths:
  你的软件名称:
    - calc.exe
    - 软件全路径或环境变量命令
    - C:\Program Files (x86)\Example\app.exe
```

保存后，右键点击桌宠展开菜单即可自动在
APP一栏中看到新配置的软件！如果你配置的软件数量超过了 5 个，环形菜单还会自动开启分页功能 (`<` 和 `>`) 供你翻页。

---

## 📦 计划集成的能力 (Planned Capabilities)
以下库为项目后续计划及 AI/自动化领域的演进设计参考：
- **语音处理**: `SpeechRecognition`, `whisper` (OpenAI), `pyttsx3`
- **语音唤醒**: `porcupine`, `webrtcvad`
- **系统监控与自动化**: `psutil`, `keyboard`
- **AI 视觉交互**: `ultralytics` (YOLO), `pytesseract` (OCR), `paddlepaddle`

---

## 🔄 近期更新 (Recent Updates)

- **待办面板上线**: 新增独立浮窗，支持日历标记、DDL 排序、今日分页与行内编辑。
- **控制移动增强**: 增加键盘控制移动（A/D 或 ←/→，W/↑/空格 上升，S/↓ 下落，Esc 退出）。
- **待机模式切换**: 默认/运动/懒惰三档待机策略，并支持记忆上次选择。
- **下落模式记忆**: 切换下落模式后自动保存，下次启动保持一致。