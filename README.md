# WhiteSwitcher

**把 VLESS 链接，轻松变成可导入的 Mihomo YAML。**

WhiteSwitcher 是面向 **Windows 10/11 家庭版及其他 x64 桌面版本** 的轻量、离线桌面转换器。

界面采用 **shadcn/ui Neutral 黑白灰视觉风格**：浅色主题默认，右上角可切换深色主题，所有按钮、边框、间距和图标统一为中性色。它是 Python/Tk 原生桌面 UI，对齐 shadcn 的视觉语言，**不内置 React 或 shadcn/ui 组件库**，从而保持免 WebView、免服务的运行形态。


> 一行一个 `vless://` 节点链接 → 自动识别 Reality / TLS / WS / gRPC / H2 / HTTP / XHTTP → 预览 → 复制或导出 `.yaml`。

## 下载并使用

1. 打开仓库的 **Actions → Test and build Windows client**，选择最新成功运行，下载 `WhiteSwitcher-Windows-x64` artifact 并解压；正式版本发布后也可直接从 **Releases** 下载 `WhiteSwitcher.exe`。
2. 双击 `WhiteSwitcher.exe` 启动，**无需预先安装 Python**。
3. 粘贴一个或多个 VLESS 链接（**每行一个**），选择“完整可导入配置”或“仅节点片段”。
4. 点击 **生成 / 刷新**，核对预览与转换诊断，再选择 **导出 .yaml**。
5. 在使用 **Mihomo / Clash Meta 内核** 的客户端中导入生成的完整配置。

**注意**：旧版 Clash 内核不支持 VLESS Reality 等协议。完整配置默认生成 `mixed-port: 7890`、`节点选择`、`自动选择` 组和 `MATCH,节点选择` 规则（默认所有匹配流量走节点选择组），可在导入后按需修改。若希望合并到现有配置，选择“仅节点片段”，手动合并 `proxies`。

## 核心特性

- **本地离线**：不请求在线转换 API、不上传 UUID/服务器/密钥、不开本地 Web 服务；没有自动更新和使用情况遥测。
- **批量转换**：多行解析，自动跳过相同链接，并为同名节点追加序号。
- **参数兼容**：`security=tls/reality/none`，`pbk/sid/sni/fp/flow/alpn`，`type=tcp/ws/grpc/http/h2/xhttp`，`encryption`、`packetEncoding`、`allowInsecure` 等。
- **稳健性**：非法 UUID、端口、缺少 Reality 公钥、无法可靠转换的传输选项会报错；未知参数只提示名称，不打印其值。允许有效行继续导出。
- **双用途**：Windows GUI + Python CLI，便于日后集成到个人工作流。

## 支持范围

| URI 字段 | Mihomo YAML |
| --- | --- |
| `security=tls / reality` | `tls`、`reality-opts` |
| `pbk` / `sid` | `public-key` / `short-id` |
| `sni` / `fp` | `servername` / `client-fingerprint` |
| `type=ws`, `host`, `path`, `ed`, `eh` | `network: ws`、`ws-opts` |
| `type=grpc`, `serviceName` | `network: grpc`、`grpc-opts` |
| `type=h2` / `http` | `h2-opts` / `http-opts` |
| `type=xhttp`, `path`, `host`, `mode` | `xhttp-opts` |
| `flow`, `alpn`, `packetEncoding`, `encryption` | 对应字段 |

**明确限制**：仅接受标准 `vless://UUID@host:port?...#name` 链接；不负责在线订阅下载、不自动修改其他客户端配置，也不会承诺所有自定义 Xray 扩展都能无损转换。`kcp/quic`、自定义 TCP `headerType` 及 XHTTP `extra` 等不兼容项会拒绝转换；未知参数显示提示。如果配置源启用了 Xray 最新的不兼容 Reality 握手实现，可能仍需调整服务端或内核版本。

协议字段参考：[Mihomo VLESS](https://wiki.metacubex.one/en/config/proxies/vless/) · [传输层](https://wiki.metacubex.one/en/config/proxies/transport/) · [TLS/Reality](https://wiki.metacubex.one/en/config/proxies/tls/)。

## 界面与主题

- 默认 **Neutral Light**：接近 shadcn/ui 默认原色调（纯白卡片、极浅灰背景、黑色主操作、细灰边框）。
- 点击右上角「深色模式」可切换 **Neutral Dark**，输入内容、YAML 预览和选择模式不丢失。
- 输入编辑器与 YAML 深灰代码面板均采用无衬线/等宽字体；转换警告也只使用黑白灰，不引入彩色状态。
- 全新黑白双向路由箭头 Logo 同时用于窗口和 Windows EXE 图标。
- 保持纯原生 Tk 运行：没有额外 WebView 或前端依赖。

## 本地开发

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m whiteswitcher
python -m unittest discover -s tests -v
```

命令行转换：

```powershell
python -m whiteswitcher --input links.txt --output clash.yaml --mode full
python -m whiteswitcher -i links.txt -o nodes.yaml --mode nodes
```

命令行退出码：`0` 全部成功；`1` 无有效节点或文件错误；`2` 部分节点失败、有效节点仍已导出。

Windows 单文件打包：

```powershell
python -m pip install -r requirements-build.txt
python scripts/make_icon.py
pyinstaller --noconfirm --clean --onefile --windowed --name WhiteSwitcher --icon build/WhiteSwitcher.ico --add-data "build/WhiteSwitcher.png;." run_gui.py
```

产物：`dist/WhiteSwitcher.exe`。`Actions` 会在 PR、主分支更新以及手动触发时运行测试，并在 Windows runner 上生成可下载的 EXE。只有推送 `v*` 标签时才会自动创建 Release。

## 设计取舍

Python 标准库 Tkinter + PyYAML + PyInstaller；构建时用 Pillow 生成黑白 ICO/PNG 图标（EXE 运行时不依赖 Pillow）。优先追求 **可维护、离线、无运行时安装、简单交付**。这是面向单一转换任务的工具，不引入复杂的前端工程、账号体系、代理服务器或多阶段 Spec 流程。

## 隐私说明

节点链接可能包含 UUID、Reality 公钥等敏感连接信息：请不要将真实节点信息贴到公开 Issue 或截图中。输入内容仅在程序内存中处理；仅在你主动点击“复制”或“导出”时写入剪贴板或指定文件。Windows 可能会记录剪贴板历史；使用后可手动清理。

## License

遵循仓库已有的 `LICENSE`。
