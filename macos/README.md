# WhiteSwitcher for macOS

独立原生 **SwiftUI** 客户端，不使用 Tk、WebView、Electron 或 Python 运行时。面向 **macOS 14+ Apple Silicon（M1 及更新）**。

## 使用

1. 在 GitHub Actions 的 **Test and build macOS app** 成功记录中下载 `WhiteSwitcher-macOS-AppleSilicon`。
2. 解压 ZIP，将 `WhiteSwitcher.app` 拖入“应用程序”，或打开 DMG 将应用拖入“应用程序”。
3. 粘贴 VLESS 链接（一行一个），自动解析，检查诊断消息，导出 `.yaml`。
4. 使用 Mihomo / Clash Meta 内核的代理客户端导入 YAML；“完整配置”包含节点选择与 MATCH 规则；“仅节点”适合手动合并。

## macOS 原生体验

- SwiftUI 系统窗口、标准可折叠侧边栏、标准系统工具栏，支持系统深色模式和动态文字颜色
- SF Symbols 图标、NSOpenPanel / NSSavePanel、本地 UTF-8 文件导入/原子导出
- 系统菜单与快捷键：**⌘O** 打开、**⌘S** 导出、**⌘↩** 生成、**⇧⌘C** 复制结果、**⇧⌘V** 粘贴链接
- 无网络权限需求，转换全程在本地内存中执行，不存储 VLESS UUID、密钥或历史链接

## 开发

```bash
cd macos
swift test
```

GUI 需要 macOS/Xcode SDK。原生 `.app` 和 `.dmg` 在 GitHub Actions macOS runner 中编译（`macos-15`，ARM64 target），无需在 Linux 上模拟 macOS GUI。源码 `Core/Converter.swift` 是 Windows Python 转换规则的 Swift 移植，两端各自保持轻依赖，实现用测试检查行为一致。

**签名限制：** 当前流水线只做 ad-hoc 签名，**没有 Apple Developer ID 签名和 Apple 公证**。初次打开可能被 Gatekeeper 拦截；确认下载源可信后，在 Finder 中右键应用点“打开”，或者在“系统设置 → 隐私与安全性”允许打开。不会建议关闭 Gatekeeper 全局防护。正式对外发行需要 Developer ID 证书和 notarization。

**范围限制：** 转换器只负责生成 YAML，不提供节点连通性测试，也不配置系统代理；Reality 服务端与 Mihomo 内核版本的兼容性仍需最终客户端验证。密码和节点密钥请勿放在公开 Issue 或截图中。

## v1.1.1 界面修复

- 使用原生 HSplitView 取代 NavigationSplitView：取消额外的左侧导航占位和标题栏布局干扰。
- 左侧输入区域有固定宽度约束（325–455pt），整栏可滚动，内容随窗口高度变化，防止左上角越界。
- YAML 预览标题及按钮在窄窗口下自适应重新布局；窗口采用 macOS 系统统一工具栏。
- 对照 [`UI-QA.md`](UI-QA.md) 进行真实 macOS 桌面验收。CI 编译通过不等于视觉测试通过。
