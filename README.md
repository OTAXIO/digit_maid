# Digit Maid（数字女仆）

Digit Maid 是一个基于 PyQt6 的跨平台桌面伴侣。它以无边框透明窗口显示桌宠，并提供环形菜单、应用启动、截图、待办、键盘移动、开机自启动和 Codex 状态查看等功能。

## 功能概览

- 透明桌宠窗口：拖拽、缩放、置顶、贴边隐藏和多种动作动画。
- 环形/列表菜单：分页、多级子菜单和屏幕边缘避让。
- 待办面板：按日期保存、DDL 排序、日历标记、分页及行内编辑。
- 安全启动应用：只允许启动 `config/apps.yaml` 中明确配置的程序。
- 屏幕截图：保存到桌面、图片目录或用户选择的位置。
- 行为模式：缓降、直落、不下坠，以及默认、运动、懒惰三种待机模式。
- 系统集成：Windows、macOS、Linux 开机自启动与跨平台打包。
- Codex 状态：读取本地状态桥接文件或查看正在运行的 Codex 进程。

## 环境要求

- Python 3.9 或更高版本
- Windows 10/11、macOS 或主流 Linux 桌面环境

安装依赖：

```bash
python -m pip install -r requirements.txt
```

当前唯一运行依赖是 PyQt6。项目内置了只支持映射、标量和标量列表的受限 YAML 解析器，因此不再要求安装 PyYAML，也不会执行 YAML 标签、引用或 Python 对象构造器。

## 运行

推荐从仓库根目录以模块方式启动：

```bash
python -m src
```

为兼容旧脚本和 PyInstaller，也可以运行：

```bash
python src/core/run.py
```

程序使用共享内存锁限制为单实例；如果 Digit Maid 已在运行，第二次启动会直接退出。

安装包的下载与使用说明见 [DOWNLOAD_GUIDE.md](./DOWNLOAD_GUIDE.md)。

## 使用说明

### 菜单与移动

- 右键桌宠打开菜单。
- 在 `TOOL -> 控制移动` 中进入键盘控制。
- `A/D` 或 `←/→` 水平移动，`W/↑/空格` 上升，`S/↓` 快速下落，`Esc` 退出控制。
- 在设置中可以修改桌宠大小、下落模式、待机模式、置顶状态和开机自启动。

### 待办面板

- 从菜单选择“待办”。
- 输入 `HH:MM` 和内容后按回车或上传按钮新增任务。
- 点击任务可行内编辑；选中任务后可删除。
- 日历支持按日查看、月份汇总以及“回到今天”。

待办保存在系统应用数据目录下的 `todo_items.json`。写入采用临时文件加原子替换，异常中断不会覆盖原文件；损坏或超大文件也会保留，方便手动恢复。

### Codex 状态桥接

默认状态文件为系统应用数据目录下的 `codex_status.json`。也可在启动 Digit Maid 前设置：

```bash
# PowerShell
$env:DIGITMAID_CODEX_STATUS_PATH = "D:\path\to\codex_status.json"

# bash/zsh
export DIGITMAID_CODEX_STATUS_PATH="/path/to/codex_status.json"
```

状态文件示例：

```json
{
  "task": "更新桌宠",
  "status": "运行中",
  "step": "执行测试",
  "detail": "安全检查已完成",
  "updated_at": "2026-08-31 12:00:00"
}
```

## 配置

所有可编辑配置集中在 `config/`：

- `apps.yaml`：允许启动的应用及不同系统下的候选路径。
- `maid_animations.yaml`：动作素材、循环方式、下落和待机默认值。
- `dialog_style.yaml`：菜单、按钮和对话气泡的样式素材。

### 添加应用

编辑 `config/apps.yaml`：

```yaml
app_paths:
  我的编辑器:
    - 'C:\Program Files\Editor\editor.exe'
    - /Applications/Editor.app
    - editor
```

应用名称必须与菜单项精确匹配。程序不会再把未配置的文本当作命令执行；候选路径也不会通过 shell 解释。每次打开菜单都会重新读取配置，修改后无需改代码。

### 修改动画

动画素材必须位于仓库的 `resource/` 目录内，动作文件必须为不含路径分隔符的 `.gif` 文件名：

```yaml
base_dir: resource/wisdel/皮肤素材/可用素材
fall_mode: smooth
idle_mode: default

actions:
  idle: relax.gif
  special: special0.gif, special1.gif

loops:
  idle: true
  special: false
```

用户在界面中修改的下落、待机和缩放设置会通过 `QSettings` 保存，并优先于配置文件默认值。

## 项目结构

```text
dmaid/
├── config/                    # 经安全校验的 YAML 配置
├── resource/                  # GIF、图片和按钮素材
├── scripts/                   # Linux 打包脚本
├── src/
│   ├── ai/                    # 本地对话占位实现
│   ├── config/                # YAML 加载和配置结构校验
│   ├── core/                  # 启动、运行时路径、原子 JSON 存储
│   ├── function/              # 待办、自启动、Codex 等功能及兼容入口
│   ├── input/                 # 环形菜单与输入对话框
│   ├── services/              # 应用启动、截图等系统边界服务
│   ├── ui/                    # 桌宠窗口、动作控制、对话和待办 UI
│   └── __main__.py            # `python -m src` 入口
├── tests/                     # 配置、安全边界和持久化测试
├── DigitMaid*.spec            # PyInstaller 多平台配置
└── requirements.txt
```

入口保持轻量：`src/core/run.py` 只负责脚本兼容，Qt 初始化和单实例生命周期位于 `src/core/application.py`，路径解析位于 `src/core/paths.py`。UI 不再自行解析 YAML，也不直接负责系统进程启动。

## 开发与测试

运行全部测试：

```bash
python -m unittest discover -s tests -v
```

检查所有 Python 文件能否编译：

```bash
python -m compileall -q src tests
```

在无图形界面的 Linux CI 中使用：

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
```

GitHub Actions 会在 `main`、`OTAXIO` 推送及拉取请求上运行编译和测试。带仓库写权限与 API 密钥的 AI 工作流只允许仓库所有者、成员或协作者触发，并设置了运行超时。

## 安全设计

- 应用启动采用配置白名单、精确名称匹配、参数列表和 `shell=False`。
- YAML 使用项目内置的受限解析器，拒绝标签、引用、复杂值和对象构造，并限制文件大小、应用数量、路径和字段类型。
- 动画路径被限制在 `resource/` 下，阻止通过 `../` 读取任意位置的素材。
- 待办和 Codex 状态 JSON 在解析前检查大小；待办通过原子替换写入。
- GitHub AI 工作流拒绝外部用户通过 Issue 或 PR 评论触发密钥作业。

配置文件仍属于本地可信管理面：修改 `apps.yaml` 等同于显式允许 Digit Maid 启动其中列出的程序。

## 打包

Windows：

```bat
build_exe.bat
```

macOS：

```bash
chmod +x build_dmg.sh
./build_dmg.sh
```

Linux DEB/RPM：

```bash
chmod +x scripts/build_linux_packages.sh
scripts/build_linux_packages.sh
```

三个 PyInstaller spec 都会把 `resource/` 和 `config/` 一并打包。发布工作流支持 Windows x86_64、macOS Apple Silicon 和 Linux x86_64。

## 本次重构摘要

- 修复已提交到动画配置中的 Git 冲突标记。
- 拆分启动、路径、配置、存储和系统服务层。
- 阻止未配置应用造成的任意命令执行入口。
- 加固 YAML/JSON 读取、截图写入和 GitHub AI 工作流。
- 增加自动化测试与 CI，并同步更新跨平台打包配置。
