## Plan: DigitMaid 全局触发 AI 对话面板

在保留现有桌宠动画与菜单逻辑的前提下，新增一个“可显示/可隐藏”的侧边 AI 对话面板：长按空格 1000ms 或中键单击触发开关；首次引导先选择 AI 供应商/模型，再输入 API Key 并落到 QSettings；有 Key 后走 OpenAI 兼容接口对话；保留最近 5 轮上下文；回复按 text/markdown/json 自动适配渲染。

### Steps
1. 阶段 A（已完成）：依赖与数据契约（阻塞后续）。
2. 已完成内容：新增运行依赖 `pynput`、`markdown`；定义统一消息结构（`role/content/render_type/timestamp`）与面板状态机（`hidden/inputting/requesting/error`）。
3. 阶段 B（已完成）：全局输入监听（依赖 A）。
4. 已完成内容：启动链路初始化全局监听桥，统一捕获空格按下/抬起与鼠标中键点击；空格长按 1000ms 去抖（按住只触发一次、抬起复位）；监听回调通过 Qt 信号切回主线程，禁止子线程直接改 UI。
5. 阶段 C（已完成）：供应商/模型选择、配置与 API 调用（依赖 A，可与阶段 D 并行）。
6. 已完成内容：建立 AI 配置服务并写入 QSettings（`ai/provider`、`ai/api_key`、`ai/base_url`、`ai/model`、`ai/context_rounds`）；支持内置供应商预设；调用 OpenAI 兼容 `chat/completions`；统一处理超时、鉴权失败、限流、服务异常与响应结构异常。
7. 阶段 D（已完成）：回复格式适配（依赖 A，可与阶段 C 并行）。
8. 已完成内容：响应格式化层支持 JSON 优先解析格式化、Markdown 转 HTML、纯文本兜底清洗（换行与基础非法标签过滤）。
9. 阶段 E（已完成）：侧边对话面板 UI（依赖 B/C/D）。
10. 已完成内容：新增独立顶层 AI 面板，包含历史消息区与输入区；Enter 提交、Shift+Enter 换行；请求中禁用输入，回复后恢复输入并自动聚焦；用户与 AI 独立文本块渲染；二次触发可隐藏。
11. 阶段 F（已完成）：主窗口集成与互斥策略（依赖 E）。
12. 已完成内容：主窗口集中管理 `toggle_ai_panel`；与短时气泡协同避免重叠；处理与菜单、自定义缩放模式等互斥边界；退出时优雅释放监听与请求线程。
13. 阶段 G（已完成）：打包与回归（依赖 B-F）。
14. 已完成内容：更新依赖与打包配置，补充 `hiddenimports`，验证源码运行链路一致性。
15. 阶段 H（已完成）：面板交互增强（依赖 E/F）。
16. 已完成内容：支持窗口四边/四角连续缩放；支持上下分区分割线拖拽；支持全屏自由拖动；支持 `Return` 回到桌宠侧边并恢复跟随。
17. 阶段 I（已完成）：面板布局持久化（依赖 H）。
18. 已完成内容：持久化面板宽高、分割比例、跟随模式、自由位置（`ai/panel_width`、`ai/panel_height`、`ai/panel_splitter_sizes`、`ai/panel_follow_anchor`、`ai/panel_pos_x`、`ai/panel_pos_y`）。
19. 阶段 J（已完成）：聊天功能总开关（依赖 F）。
20. 已完成内容：设置中新增聊天开关并持久化（`ai/enabled`）；关闭后阻止唤醒 AI 面板并可隐藏已打开面板。
21. 阶段 K（已完成）：面板内一站式配置入口（依赖 C/E）。
22. 已完成内容：聊天面板顶部“配置”按钮支持同窗编辑并保存供应商、模型、Base URL、API Key；切换供应商自动填充推荐 `base_url` 与默认模型。
23. 阶段 L（进行中）：文档与回归清单持续更新（依赖 A-K）。
24. 待补内容：将“Plan/Build/Verification”保持同步更新，补充 EXE 端到端回归记录与异常场景实测记录。

### Provider presets（Draft）
- 供应商选择顺序：先选供应商，再自动填充 base_url 和推荐模型，最后输入 Key。
- 供应商可选项：DeepSeek、OpenAI、Qwen、Doubao、Gemini。

| Provider | base_url（预置） | 默认模型（可改） |
|---|---|---|
| DeepSeek | https://api.deepseek.com | deepseek-chat |
| OpenAI | https://api.openai.com/v1 | gpt-4o-mini |
| Qwen | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-plus |
| Doubao | https://ark.cn-beijing.volces.com/api/v3 | doubao-1.5-pro-32k |
| Gemini | https://generativelanguage.googleapis.com/v1beta/openai | gemini-2.0-flash |

备注：Doubao 不同账号或地域下模型命名可能不同，若默认模型不可用，允许用户手动改 model 并保存。

### Relevant files
- [src/core/run.py](../core/run.py) — 启动时初始化/退出时释放全局监听生命周期
- [src/ui/maid_window.py](../ui/maid_window.py) — AI 面板开关入口、主线程事件分发、交互互斥
- [src/input/text_input.py](../input/text_input.py) — 扩展密钥输入交互（含回显策略）
- [src/ui/dialogue.py](../ui/dialogue.py) — 短时气泡与 AI 面板协同显示策略
- [src/input/circular_menu.py](../input/circular_menu.py) — 校验菜单状态下的触发与滚轮冲突
- [src/ui/menu_controller.py](../ui/menu_controller.py) — 补充 AI 面板相关权限策略（如需要）
- [src/ai](.) — 新增配置服务、OpenAI 兼容客户端、响应格式化模块
- [src/ui](../ui) — 新增 AI 对话面板模块
- [requirements.txt](../../requirements.txt) — 新增 pynput、markdown
- [DigitMaid.spec](../../DigitMaid.spec) — 校验打包依赖收集

### Verification
1. 启动后切到其他应用，长按空格 1000ms，确认可打开/隐藏面板（全局生效）。
2. 在其他应用中键单击，确认同样可打开/隐藏面板。
3. 清空 Key 后触发，确认先弹“供应商/模型选择”，再弹 API 输入；保存后下次不再重复输入。
4. 发送普通文本、Markdown、JSON 类型问题，确认三类渲染都可读且不溢出。
5. 连续超过 5 轮对话，确认请求只携带最近 5 轮上下文。
6. 断网、错误 Key、429 限流场景下，确认只提示错误不崩溃，且可继续下一轮。
7. 在圆形菜单打开、自定义缩放中反复触发，确认不死锁、不丢焦点、不影响原有交互。
8. 打包后运行 EXE，复测全局触发、Key 持久化、AI 对话与格式渲染。

### Decisions
- 已确认：OpenAI 兼容接口（base_url + model 可配置）。
- 已确认：首次引导流程为“先选供应商/模型，再输入 Key”。
- 已确认：内置供应商预设（DeepSeek / OpenAI / Qwen / Doubao / Gemini）及对应 base_url。
- 已确认：API Key 存 QSettings。
- 已确认：中键单击立即切换。
- 已确认：保留最近 5 轮上下文。
- 已确认：空格全局生效（应用失焦也可触发）。
- 范围内：文本问答、多轮上下文、markdown/json 适配、显示/隐藏切换。
- 范围外：语音输入、流式 token 打字机效果、跨设备同步配置。

如果你要微调（例如长按阈值、上下文轮数、错误提示风格），我会同步更新这份方案到执行级别的任务清单。

---

## Build（当前实现状态）

以下为截至当前版本已落地的功能构建描述。

### 1. 全局触发与生命周期
- 已接入全局输入监听桥（`pynput`），支持：
	- 空格长按 1000ms 触发（带去抖，按住只触发一次）
	- 鼠标中键单击触发
- 监听回调通过 Qt 信号切回主线程处理 UI。
- 程序退出时会释放全局监听与 AI 请求线程。

### 2. AI 配置与调用
- 已实现 OpenAI 兼容调用链路（`/chat/completions`）。
- 已支持供应商预设：DeepSeek / OpenAI / Qwen / Doubao / Gemini。
- 配置持久化到 QSettings（Windows 对应注册表）：
	- `ai/provider`
	- `ai/api_key`
	- `ai/base_url`
	- `ai/model`
	- `ai/context_rounds`
	- `ai/enabled`
- 已统一处理常见异常：超时、鉴权失败、429、服务端异常、响应结构异常。

### 3. 聊天面板能力
- 已新增独立 AI 侧边面板（顶层窗口，默认可跟随桌宠）。
- 已支持面板显示/隐藏开关。
- 已支持现代化 UI 样式（状态芯片、消息卡片、输入区、滚动条样式）。
- 已支持输入行为：
	- Enter 发送
	- Shift+Enter 换行
- 已支持请求态禁用输入，回复后自动恢复输入并聚焦。
- 已支持文本块分离渲染（用户/AI）。

### 4. 面板交互增强
- 已支持窗口自由缩放（四边+四角拖拽）。
- 已支持上下分区分割线拖拽（历史区/输入区可调比例）。
- 已支持全屏自由拖动（拖动标题区进入自由模式，不再跟随桌宠）。
- 已支持 Return 按钮回到桌宠侧边并恢复跟随。

### 5. 面板内配置入口（不走设置菜单）
- 顶部“配置”按钮已接入统一配置弹窗。
- 在一个弹窗内可同时修改并保存：
	- 供应商
	- 模型
	- Base URL
	- API Key（密码输入）
- 切换供应商时会自动填充推荐 `base_url` 与默认模型，可手动覆盖。

### 6. 持久化项（已实现）
- 面板尺寸：`ai/panel_width`、`ai/panel_height`
- 分割比例：`ai/panel_splitter_sizes`
- 跟随模式：`ai/panel_follow_anchor`
- 自由模式位置：`ai/panel_pos_x`、`ai/panel_pos_y`

### 7. 菜单侧配置（已实现）
- 设置中已增加“聊天”开关（开启/关闭），用于控制是否允许唤醒 AI 聊天框。
- 关闭时会拦截全局触发并可自动隐藏已打开面板。

### 8. 回复格式适配（已实现）
- JSON：优先解析并格式化展示。
- Markdown：识别后转为 HTML 展示。
- 纯文本：作为兜底并做基础清洗。

### 9. 依赖与打包（已更新）
- `requirements.txt` 已新增：`pynput`、`markdown`。
- `DigitMaid.spec` 已补充相关 `hiddenimports`。

### 10. 已知说明
- 当前 `api_key` 存储在 QSettings（Windows 注册表）中，为明文；若后续需要可升级为 Windows Credential Manager。
