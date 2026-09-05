# 开发与维护指南

本文按「要改什么，就去哪里」组织。运行入口保持 `python -m src`，打包仍使用 `src/core/run.py`；本次整理不改变个人待办数据的格式与路径规则。

## 依赖方向

```text
core.application → ui.maid_window → action / dialogue / todo_panel / todo_reminder
                                 ↓
input → ui.theme                 domain.todo / domain.reminders
menu  → domain-independent       function.todo_store → core.json_store
services → 操作系统边界           config → 受限 YAML 解析
```

`domain/` 不导入 Qt，不访问文件，也不弹窗。`theme/` 不调用业务控制器。`Others/` 中的工具和文档不参与桌宠启动；`.github/workflows/` 保留在 GitHub 要求的固定位置。

## 常见修改位置

| 修改目标 | 首选文件 | 责任边界 |
| --- | --- | --- |
| 统一配色与字体 | `src/ui/theme/__init__.py` | `Palette` 使用语义颜色；不要在窗口内新增近似色 |
| 卡片、输入、按钮样式 | `src/ui/theme/styles.py` | 公共 QSS；没有任务读写逻辑 |
| 截图／数值输入窗口骨架 | `src/ui/theme/dialogs.py` | 标题、内容区、操作区、屏幕避让 |
| 角色标记、阴影 | `src/ui/theme/widgets.py` | 复用现有素材，路径由 `resource_path` 定位 |
| 对话气泡 | `src/ui/dialogue.py` | 跟随位置、长消息滚动、计时器销毁 |
| 环形菜单按钮与交互 | `src/input/circular_menu.py` | 处理点击、动画和历史导航 |
| 菜单边界几何 | `src/menu/layout.py` | 无 Qt 的四方向半圆排版，防重叠与越界 |
| 每日任务交互 | `src/ui/todo_panel.py` | 列表／编辑切换、保存反馈和日期联动 |
| 任务卡片绘制 | `src/ui/todo_delegate.py` | 只读委托，不打开行内编辑器 |
| 日历标记 | `src/ui/todo_calendar.py` | 周末、今天、选中和有任务日期的颜色 |
| 时间／正文／排序规则 | `src/domain/todo.py` | 存储和界面共用一份规范化逻辑 |
| 临期窗口与倒计时 | `src/domain/reminders.py` | 纯计算，可独立测试 |
| 提醒窗口与计时器 | `src/ui/todo_reminder.py` | 只消费临期计算结果，不重复解析时间 |
| 待办持久化 | `src/function/todo_store.py` | 文件容量、原子写入、坏文件保留 |
| 系统应用与截图 | `src/services/` | 配置白名单、参数数组、文件系统边界 |
| 桌宠行为 | `src/ui/maid_window.py` | 动画、移动、缩放、边缘隐藏与桌面保护 |

旧的 `src.function.todo_store` 及 `src.ui.todo_reminder` 导入入口仍兼容；公共数据规则已经转到 `domain/`。`choice_dialog.load_dialog_theme` 也保留为兼容入口，新代码应从 `ui.theme` 导入。

## 关键状态约束

待办使用 `{ddl, text, completed}` 字典，其中 `completed` 只有布尔值 `true` 才代表完成。未完成事项按截止时间排序，完成事项排在后面。历史字符串格式在读取时规范化，JSON 外层仍是 `items_by_date`。

编辑页以「日期 + 当前排序索引」定位事项。保存内容后先重新排序，再更新索引，避免 DDL 改变后操作到另一项。完成按钮把编辑内容与状态合并为一次写入；失败时恢复内存快照，保留草稿并反馈错误。已完成任务的正文只读。

自动保存使用单次 600ms 定时器。返回列表、关闭和切换日期都会先尝试保存。提醒窗口在写完成状态之前先提交可见编辑页草稿，避免用新的磁盘状态刷新时吞掉未保存输入。由于尚未引入跨进程记录锁，不支持同时手工修改 JSON；应用自身有单实例限制。

提醒每 10 分钟触发；弹窗可一直保留。`p` 控制用户选择「稍后提醒」后的延迟。当天已超时未完成任务保留在提醒范围，历史逾期不永久锁住桌宠。桌面保护由 `MaidWindow.set_deadline_guard_active` 接收状态，UI 的展开／关闭不自行改写截止逻辑。

气泡是独立顶层窗口。`closeEvent` 必须停止跟随计时器和关闭计时器，再延迟销毁；旧气泡销毁回调只清除自身引用，不能清除后来创建的新气泡。长正文显示在可滚动区域，标题和正文在进入 HTML 之前做转义。

## 中文批注约定

- 模块开头用一句话写清职责与不负责的工作。
- 对保存回滚、排序后定位、窗口销毁、坐标转换等不直观的原因写中文注释。
- 不逐行翻译赋值语句；命名、单一职责与短函数优先于大量说明。
- 兼容入口注明保留原因，新增代码引用新的公共入口。
- 修改业务边界时，同时更新对应手册与回归测试。

## 新增一个工具

1. 系统能力放到 `src/services/`，参数校验与进程启动不要写在按钮回调里。
2. 在菜单动作映射中增加清楚的入口；仅启动外部程序时可直接编辑 `config/menu.yaml`。
3. 需要输入时复用 `ThemedDialog`，把内容控件加到 `content_layout`，通过 `add_action` 和 `finish_layout` 组装操作区。
4. 普通反馈交给 `DialogueSystem.show_message`；不要另建永久计时器。
5. 对写盘、外部启动和非法参数添加有意义的回归；样式尺寸用预览工具验证。

## 检查与界面实拍

从仓库根目录运行：

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests Others/tools
python Others/tools/preview_ui.py
git diff --check
```

预览使用真实 Qt 控件与内存样例；菜单与角色的总览图由这些控件合成，用于文档展示。脚本不会加载个人待办或启动外部应用。可用 `--output build/ui-preview` 输出到不提交的临时位置。Windows offscreen 不自动发现系统字体，所以脚本显式注册微软雅黑；Linux 可安装 Noto Sans CJK。

关键回归包括：非法 YAML/JSON、数值溢出、启动白名单、完成状态回滚、修改并完成的原子性、日期切换草稿保护、气泡生命周期、长消息滚动、菜单在四个角落与极端缩放下的间距。

## 打包与路径

```text
Others/packaging/windows/build_exe.bat
Others/packaging/macos/build_dmg.sh
Others/packaging/linux/build_linux_packages.sh
```

打包脚本定位仓库根目录再执行；spec 中的 `REPO_ROOT`、资源复制目标和程序入口必须一起维护。`theme/` 与 `domain/` 是普通 Python 模块，会由 PyInstaller 静态收集；QSS 保存在 Python 源码内，不增加运行时相对文件依赖。

`Others/docs/images/` 是文档实拍，`Others/tools/` 是预览生成器，都不应打进桌宠资源目录。`resource/` 仍只供角色动画与运行时图标使用。`config/` 始终位于资源根目录下，不能随文档整理挪进 `Others/`。

本地验证不能代替 macOS/Linux 的真实桌面验收；这些平台的打包结果仍需相应 runner 和桌面环境确认。Windows 的单文件 EXE 内嵌配置修改后需重新构建，用户待办 JSON 不应随发布包覆盖。
