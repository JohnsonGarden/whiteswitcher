import SwiftUI
import AppKit

private extension Color {
    static var subtleBorder: Color { Color(nsColor: .separatorColor).opacity(0.65) }
    static var mutedForeground: Color { Color(nsColor: .secondaryLabelColor) }
}

struct ContentView: View {
    @EnvironmentObject private var workspace: Workspace
    @State private var showDiagnostics = true
    @FocusState private var focusInput: Bool

    var body: some View {
        NavigationSplitView {
            sidebar
                .navigationSplitViewColumnWidth(min: 330, ideal: 405, max: 530)
        } detail: {
            detail
        }
        .navigationTitle("WhiteSwitcher")
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                Button("从剪贴板添加", systemImage: "doc.on.clipboard") {
                    workspace.pasteLinks()
                }
                .help("从剪贴板添加 VLESS 链接")

                Button("导出 YAML", systemImage: "square.and.arrow.up") {
                    workspace.exportYAML()
                }
                .disabled(!workspace.isReady)
                .help("将配置保存为 .yaml（⌘S）")
            }
        }
        .onChange(of: workspace.input) { _, _ in workspace.refresh() }
        .onChange(of: workspace.mode) { _, _ in workspace.refresh() }
    }

    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 5) {
                Label("VLESS 链接", systemImage: "link")
                    .font(.headline)
                Text("粘贴或导入分享链接，每行一个。所有转换均在本机离线完成。")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            ZStack(alignment: .topLeading) {
                TextEditor(text: $workspace.input)
                    .focused($focusInput)
                    .font(.system(size: 12, design: .monospaced))
                    .scrollContentBackground(.hidden)
                    .padding(7)
                    .accessibilityLabel("VLESS 分享链接输入区域")
                if workspace.input.isEmpty {
                    Text("vless://UUID@server:443?...#节点名称")
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundStyle(.tertiary)
                        .padding(.leading, 12)
                        .padding(.top, 15)
                        .allowsHitTesting(false)
                }
            }
            .frame(minHeight: 220)
            .background(Color(nsColor: .textBackgroundColor), in: RoundedRectangle(cornerRadius: 10))
            .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color.subtleBorder, lineWidth: 1))

            HStack(spacing: 8) {
                Button("打开文件…", systemImage: "folder") { workspace.importLinks() }
                    .help("打开 UTF-8 链接文本（⌘O）")
                Button("粘贴", systemImage: "doc.on.clipboard") { workspace.pasteLinks() }
                Spacer(minLength: 4)
                Button("清空") { workspace.clearAll(); focusInput = true }
                    .disabled(workspace.input.isEmpty)
            }
            .buttonStyle(.bordered)

            Divider()

            VStack(alignment: .leading, spacing: 10) {
                Text("导出格式")
                    .font(.subheadline.weight(.medium))
                Picker("导出格式", selection: $workspace.mode) {
                    ForEach(WhiteSwitcherConverter.Mode.allCases) { mode in
                        Text(mode.label).tag(mode)
                    }
                }
                .labelsHidden()
                .pickerStyle(.segmented)
                Text(workspace.mode == .full
                     ? "包含节点、节点选择、自动测速与 MATCH 规则，可作为独立配置导入。"
                     : "只输出 proxies 节点列表，适合手动合并到已有配置。")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack(spacing: 8) {
                metric("有效节点", count: workspace.result.proxies.count)
                metric("错误", count: workspace.result.errors.count)
                metric("警告", count: workspace.result.warnings.count)
            }
            Spacer(minLength: 0)
            HStack {
                Image(systemName: "lock.shield")
                    .accessibilityHidden(true)
                Text("纯离线 · 不上传链接 · Apple Silicon")
            }
            .font(.caption2)
            .foregroundStyle(.secondary)
        }
        .padding(20)
    }

    private func metric(_ title: String, count: Int) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(String(count)).font(.title3.monospacedDigit().weight(.semibold))
            Text(title).font(.caption2).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 9)
        .padding(.horizontal, 10)
        .background(Color(nsColor: .textBackgroundColor), in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.subtleBorder, lineWidth: 1))
    }

    private var detail: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .center) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("YAML 预览")
                        .font(.title3.weight(.semibold))
                    Text("Mihomo / Clash Meta 兼容配置")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Button("生成", systemImage: "arrow.triangle.2.circlepath") { workspace.refresh() }
                    .help("重新生成（⌘↩）")
                Button("复制 YAML", systemImage: "doc.on.doc") { workspace.copyYAML() }
                    .disabled(!workspace.isReady)
                    .help("复制结果（⇧⌘C）")
                    .buttonStyle(.borderedProminent)
                    .tint(.primary)
            }
            .padding(.bottom, 14)

            Group {
                if workspace.preview.isEmpty {
                    ContentUnavailableView("尚无可预览的配置", systemImage: "curlybraces.square",
                                           description: Text("左侧粘贴 VLESS 链接后，这里会自动生成 YAML。"))
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    ScrollView([.vertical, .horizontal]) {
                        Text(workspace.preview)
                            .font(.system(size: 12, design: .monospaced))
                            .textSelection(.enabled)
                            .frame(maxWidth: .infinity, alignment: .topLeading)
                            .padding(17)
                            .accessibilityLabel("生成的 YAML 配置")
                    }
                    .background(Color(nsColor: .textBackgroundColor))
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color.subtleBorder, lineWidth: 1))

            if !workspace.result.issues.isEmpty {
                DisclosureGroup(isExpanded: $showDiagnostics) {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 7) {
                            ForEach(workspace.result.issues) { issue in
                                HStack(alignment: .firstTextBaseline, spacing: 8) {
                                    Image(systemName: issue.warning ? "exclamationmark.triangle" : "xmark.circle")
                                        .foregroundStyle(.secondary)
                                    Text("第 \(issue.line) 行 · \(issue.message)")
                                        .textSelection(.enabled)
                                }
                                .font(.caption)
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .frame(maxHeight: 120)
                    .padding(.top, 7)
                } label: {
                    Text("转换诊断 · \(workspace.result.issues.count) 条")
                        .font(.subheadline.weight(.medium))
                }
                .padding(.top, 13)
            }
            if let message = workspace.message {
                Text(message)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding(.top, 9)
                    .accessibilityAddTraits(.updatesFrequently)
            }
        }
        .padding(22)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
