import AppKit
import Foundation
import SwiftUI
import UniformTypeIdentifiers

@MainActor
final class Workspace: ObservableObject {
    @Published var input = ""
    @Published var mode: WhiteSwitcherConverter.Mode = .full
    @Published private(set) var result = WhiteSwitcherConverter.parse("")
    @Published private(set) var preview = ""
    @Published var message: String? = nil

    var isReady: Bool { !result.proxies.isEmpty }

    func refresh() {
        result = WhiteSwitcherConverter.parse(input)
        preview = (try? WhiteSwitcherConverter.export(result, mode: mode)) ?? ""
    }

    func importLinks() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.plainText, .text]
        panel.allowsOtherFileTypes = true // .txt, .conf or exported link lists
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.message = "选择包含 VLESS 分享链接的 UTF-8 文本文件"
        guard panel.runModal() == .OK, let url = panel.url else { return }
        do {
            let contents = try String(contentsOf: url, encoding: .utf8)
            if input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                input = contents
            } else {
                input += "\n" + contents
            }
            refresh()
            message = nil
        } catch {
            message = "打开失败：请选择 UTF-8 文本文件（\(error.localizedDescription)）"
        }
    }

    func pasteLinks() {
        guard let text = NSPasteboard.general.string(forType: .string), !text.isEmpty else {
            message = "剪贴板没有可用的文本"
            return
        }
        input = input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? text : input + "\n" + text
        refresh()
        message = nil
    }

    func copyYAML() {
        guard isReady else { message = "请先输入有效的 VLESS 链接"; return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(preview, forType: .string)
        message = "YAML 已复制到剪贴板"
    }

    func exportYAML() {
        guard isReady else { message = "请先输入有效的 VLESS 链接"; return }
        let panel = NSSavePanel()
        panel.nameFieldStringValue = "whiteswitcher.yaml"
        panel.allowedContentTypes = [UTType(filenameExtension: "yaml") ?? .plainText]
        panel.canCreateDirectories = true
        panel.message = "保存 Mihomo YAML 配置"
        guard panel.runModal() == .OK, let url = panel.url else { return }
        do {
            // Atomic replacement avoids truncating a previous valid configuration.
            try preview.write(to: url, atomically: true, encoding: .utf8)
            message = "已保存：\(url.lastPathComponent)"
        } catch {
            message = "导出失败：\(error.localizedDescription)"
        }
    }

    func clearAll() {
        input = ""
        refresh()
        message = nil
    }
}

@main
struct WhiteSwitcherApp: App {
    @StateObject private var workspace = Workspace()

    var body: some Scene {
        WindowGroup("WhiteSwitcher") {
            ContentView()
                .environmentObject(workspace)
                .frame(minWidth: 860, minHeight: 560)
        }
        .defaultSize(width: 1120, height: 720)
        .windowToolbarStyle(.unified)
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("打开链接文本…") { workspace.importLinks() }
                    .keyboardShortcut("o", modifiers: [.command])
            }
            CommandGroup(replacing: .saveItem) {
                Button("导出 YAML…") { workspace.exportYAML() }
                    .keyboardShortcut("s", modifiers: [.command])
                    .disabled(!workspace.isReady)
            }
            CommandMenu("转换") {
                Button("生成配置") { workspace.refresh() }
                    .keyboardShortcut(.return, modifiers: [.command])
                Button("复制 YAML") { workspace.copyYAML() }
                    .keyboardShortcut("c", modifiers: [.command, .shift])
                    .disabled(!workspace.isReady)
                Divider()
                Button("从剪贴板添加链接") { workspace.pasteLinks() }
                    .keyboardShortcut("v", modifiers: [.command, .shift])
                Button("清空全部链接") { workspace.clearAll() }
            }
        }
    }
}
