# Digit Maid · 维维美桌面伴侣

基于 PyQt6 的跨平台桌宠，沿用明日方舟维什戴尔愚人节皮肤素材。统一的银白、炭黑与深红界面，把桌宠互动、工具操作和每日待办收在一起。

![桌宠菜单与对话预览](Others/docs/images/vivi-desktop.png)

## 开始使用

需要 Python 3.9+ 和桌面图形环境。在仓库根目录运行：

```bash
python -m pip install -r requirements.txt
python -m src
```

右键桌宠打开菜单：APP 启动应用，TOOL 提供截图和键盘控制，「待办」管理每日计划，「设置」调整缩放和行为。程序通过共享内存锁保持单实例。

- [完整中文使用手册](Others/docs/USER_GUIDE.md)：安装、操作、配置、备份与故障排查。
- [安装包下载指南](Others/docs/DOWNLOAD_GUIDE.md)：Windows、macOS 和 Linux 的安装方式。
- [开发维护指南](Others/docs/ARCHITECTURE.md)：目录职责、扩展方法、中文批注约定、测试与打包。

## 待办手账

任务卡片区分时间、正文与完成状态。点击后进入整页编辑，底部提供删除和完成／未完成切换；完成后保留任务并锁定正文。编辑会自动保存，失败时显示错误并保留输入。

![待办手账](Others/docs/images/vivi-todo.png)

临近 DDL 会唤回桌宠并禁止侧栏隐藏，提醒只提供「标记已完成」和「p 分钟后提醒」。阈值集中在根目录 [config/todo.yaml](config/todo.yaml)，默认 n=2 小时、m=1 小时、p=30 分钟；具体行为和打包后的配置位置见使用手册。

## 目录导航

```text
config/              可编辑 YAML 配置
resource/            桌宠运行时动画和图片
src/
  core/              启动、路径、数值边界、JSON 原子存储
  config/            受限 YAML 解析与结构校验
  domain/            待办规范化、排序与 DDL 时间窗口
  menu/              菜单模型、构建器、屏幕边界排版
  services/          应用启动与截图系统服务
  function/          待办存储、自启动、Codex 状态及兼容入口
  input/             输入对话框与菜单交互
  ui/                桌宠、对话、待办与提醒
    theme/           统一色板、QSS、窗口骨架与公共控件
Others/
  docs/              手册与界面实拍
  packaging/         Windows / macOS / Linux 打包与适配
  tools/             文档用界面预览工具
tests/               业务、持久化、布局与交互回归
```

## 开发验证

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests Others/tools
python Others/tools/preview_ui.py
```

预览工具只使用内存样例，不读取或修改个人待办；输出放在 `Others/docs/images/`。Linux CI 可设置 `QT_QPA_PLATFORM=offscreen`。

运行依赖只有 PyQt6。YAML 使用受限解析器，外部启动项必须在菜单白名单内；待办 JSON 有容量限制，并以原子替换方式保存。更多边界说明见维护指南。

角色与游戏相关美术权益归原权利方所有。本项目及预览图为非官方二次创作，不代表官方产品。
