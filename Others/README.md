# Others

这里集中存放不参与 Digit Maid 运行时功能的发布、平台适配与文档素材：

- `packaging/windows/`：Windows EXE 的 PyInstaller spec、构建脚本与图标。
- `packaging/macos/`：macOS app/DMG 的 spec 与构建脚本。
- `packaging/linux/`：Linux bundle、DEB、RPM 的 spec 与构建脚本。
- `docs/`：安装说明及 Markdown 展示图片。
- `tools/`：仅用于手册的界面预览工具，不参与桌宠运行。

阅读入口：[中文使用手册](docs/USER_GUIDE.md)、[开发维护指南](docs/ARCHITECTURE.md)。

所有构建脚本都会先定位并切换到仓库根目录，因此既可以从根目录调用，也可以在脚本所在目录调用。运行时的 `src/`、`config/` 和 `resource/` 路径没有改变；三个 spec 仍将完整的 `config/` 与 `resource/` 打入发布包。

发布流水线入口仍保留在 `.github/workflows/release-build.yml`，这是 GitHub Actions 要求的固定发现路径；流水线中的实际构建入口均已指向本目录。
