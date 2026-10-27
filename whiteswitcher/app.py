"""Lightweight native desktop interface. No browser, server or telemetry."""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from .core import APP_VERSION, export_yaml, parse_links

BG = "#F4F6FB"
WHITE = "#FFFFFF"
INK = "#172137"
MUTED = "#6D7690"
ACCENT = "#6554DF"
ACCENT_HOVER = "#5140C8"
BORDER = "#DFE4EF"
DARK = "#19233C"
GOOD = "#15956E"
BAD = "#D14B57"


def _dpi_awareness() -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


class WhiteSwitcherApp:
    def __init__(self) -> None:
        _dpi_awareness()
        self.root = tk.Tk()
        self.root.title(f"WhiteSwitcher {APP_VERSION} · VLESS → Mihomo")
        self.root.geometry("1150x750")
        self.root.minsize(950, 620)
        self.root.configure(bg=BG)
        self.mode = tk.StringVar(value="full")
        self.status = tk.StringVar(value="等待输入 · 所有转换操作均在本机完成")
        self.summary = tk.StringVar(value="等待转换")
        self.current_yaml = ""
        self.last_text = None
        self.last_mode = None
        self._layout()
        self._bind_shortcuts()

    def _label(self, parent: tk.Misc, value: str, size: int = 10, bold: bool = False,
               fg: str = INK, bg: str = WHITE, **kwargs) -> tk.Label:
        font = ("Segoe UI", size, "bold" if bold else "normal")
        return tk.Label(parent, text=value, font=font, fg=fg, bg=bg, **kwargs)

    def _button(self, parent: tk.Misc, title: str, handler, *, primary: bool = False) -> tk.Button:
        normal, hover, foreground = ((ACCENT, ACCENT_HOVER, WHITE) if primary
                                      else ("#EDF0F9", "#E0E5F2", INK))
        btn = tk.Button(parent, text=title, command=handler,
                        font=("Segoe UI", 10, "bold"), bg=normal, fg=foreground,
                        activebackground=hover, activeforeground=foreground,
                        cursor="hand2", relief="flat", borderwidth=0, padx=17, pady=10)
        btn.bind("<Enter>", lambda _: btn.configure(bg=hover))
        btn.bind("<Leave>", lambda _: btn.configure(bg=normal))
        return btn

    def _card(self, parent: tk.Misc) -> tk.Frame:
        outer = tk.Frame(parent, bg=WHITE, highlightbackground=BORDER,
                         highlightthickness=1, bd=0)
        return outer

    def _layout(self) -> None:
        masthead = tk.Frame(self.root, bg=DARK, height=110)
        masthead.pack(fill="x")
        masthead.pack_propagate(False)
        heading = tk.Frame(masthead, bg=DARK)
        heading.pack(fill="x", padx=32, pady=20)
        logo = tk.Label(heading, text="W", font=("Segoe UI", 28, "bold"), fg=WHITE,
                        bg=ACCENT, width=2, height=1)
        logo.pack(side="left", padx=(0, 18))
        titles = tk.Frame(heading, bg=DARK)
        titles.pack(side="left", anchor="w")
        self._label(titles, "WhiteSwitcher", 19, True, WHITE, DARK).pack(anchor="w")
        self._label(titles, "VLESS 链接 → Mihomo / Clash Meta 配置", 10,
                    fg="#AFBAD5", bg=DARK).pack(anchor="w", pady=(3, 0))
        badge = tk.Label(heading, text="100% 本地离线  ·  Windows x64", bg="#2B3756",
                         fg="#D2DCFB", font=("Segoe UI", 9, "bold"), padx=13, pady=8)
        badge.pack(side="right")

        stage = tk.Frame(self.root, bg=BG)
        stage.pack(expand=True, fill="both", padx=26, pady=(22, 12))
        stage.grid_columnconfigure(0, weight=5, uniform="stage")
        stage.grid_columnconfigure(1, weight=6, uniform="stage")
        stage.grid_rowconfigure(0, weight=1)

        left = self._card(stage)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)
        left.grid_rowconfigure(5, weight=1)
        self._label(left, "01   输入 VLESS 节点", 13, True).grid(
            row=0, column=0, sticky="w", padx=21, pady=(20, 5))
        self._label(left, "每行一个链接 · 支持多节点 · 自动去重及重名处理", 9, fg=MUTED).grid(
            row=1, column=0, sticky="w", padx=21, pady=(0, 12))
        input_shell = tk.Frame(left, bg=BORDER, padx=1, pady=1)
        input_shell.grid(row=2, column=0, sticky="nsew", padx=21)
        self.input_box = tk.Text(input_shell, wrap="char", undo=True, borderwidth=0,
                                 relief="flat", bg="#FBFCFF", fg=INK,
                                 insertbackground=INK, selectbackground="#D5CDFD",
                                 font=("Consolas", 10), padx=14, pady=14,
                                 height=12, width=42)
        scroll = tk.Scrollbar(input_shell, command=self.input_box.yview)
        self.input_box.config(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.input_box.pack(side="left", expand=True, fill="both")
        row = tk.Frame(left, bg=WHITE)
        row.grid(row=3, column=0, sticky="ew", padx=21, pady=(12, 16))
        self._button(row, "粘贴剪贴板", self._paste).pack(side="left", padx=(0, 8))
        self._button(row, "导入 .txt", self._import_file).pack(side="left", padx=(0, 8))
        self._button(row, "清空", self._clear).pack(side="right")
        tk.Frame(left, bg=BORDER, height=1).grid(row=4, column=0, sticky="ew", padx=21)
        issue_frame = tk.Frame(left, bg=WHITE)
        issue_frame.grid(row=5, column=0, sticky="nsew", padx=21, pady=(15, 18))
        issue_frame.grid_columnconfigure(0, weight=1)
        issue_frame.grid_rowconfigure(1, weight=1)
        self._label(issue_frame, "转换诊断", 10, True).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.issue_box = tk.Text(issue_frame, height=5, state="disabled", relief="flat",
                                 bg="#F7F8FC", fg=MUTED, font=("Segoe UI", 9),
                                 wrap="word", padx=11, pady=10, borderwidth=0)
        self.issue_box.grid(row=1, column=0, sticky="nsew")
        self._set_issues("有效节点及参数检查结果将在此处显示。")

        right = self._card(stage)
        right.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(3, weight=1)
        self._label(right, "02   生成 YAML 配置", 13, True).grid(
            row=0, column=0, sticky="w", padx=21, pady=(20, 5))
        mode_bar = tk.Frame(right, bg=WHITE)
        mode_bar.grid(row=1, column=0, sticky="w", padx=21, pady=(6, 13))
        for label, value in (("完整可导入配置", "full"), ("仅节点片段", "nodes")):
            tk.Radiobutton(mode_bar, text=label, variable=self.mode, value=value,
                           command=self._invalidate, bg=WHITE, fg=INK,
                           activebackground=WHITE, selectcolor=WHITE,
                           font=("Segoe UI", 10), padx=6).pack(side="left", padx=(0, 14))
        self._label(right, "默认生成节点选择、自动测速与 MATCH 规则", 9, fg=MUTED).grid(
            row=2, column=0, sticky="w", padx=21, pady=(0, 9))
        output_shell = tk.Frame(right, bg=BORDER, padx=1, pady=1)
        output_shell.grid(row=3, column=0, sticky="nsew", padx=21)
        self.output_box = tk.Text(output_shell, state="disabled", wrap="none", relief="flat",
                                  bg="#FAFBFE", fg="#34405B", borderwidth=0,
                                  font=("Consolas", 10), padx=14, pady=14,
                                  width=55, height=16)
        yscroll = tk.Scrollbar(output_shell, command=self.output_box.yview)
        xscroll = tk.Scrollbar(output_shell, command=self.output_box.xview, orient="horizontal")
        self.output_box.config(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")
        self.output_box.pack(side="left", fill="both", expand=True)
        actions = tk.Frame(right, bg=WHITE)
        actions.grid(row=4, column=0, sticky="ew", padx=21, pady=(15, 8))
        self._button(actions, "生成 / 刷新", self._generate, primary=True).pack(side="left", padx=(0, 8))
        self._button(actions, "复制 YAML", self._copy).pack(side="left", padx=(0, 8))
        self._button(actions, "导出 .yaml", self._export).pack(side="right")
        self._label(right, "等待转换", 9, fg=GOOD, textvariable=self.summary).grid(
            row=5, column=0, sticky="w", padx=21, pady=(1, 18))

        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill="x", padx=28, pady=(0, 14))
        self._label(footer, "仅支持 Mihomo / Clash Meta 内核；Reality 等扩展不适用于旧版 Clash。",
                    9, fg=MUTED, bg=BG).pack(side="left")
        self._label(footer, "WhiteSwitcher v" + APP_VERSION, 9, fg=MUTED, bg=BG).pack(side="right")
        status_bar = tk.Frame(self.root, bg="#E7EAF4", height=30)
        status_bar.pack(fill="x", side="bottom")
        self._label(status_bar, "●  ", 9, fg=GOOD, bg="#E7EAF4").pack(side="left", padx=(17, 0))
        self._label(status_bar, "", 9, fg="#50607A", bg="#E7EAF4",
                    textvariable=self.status).pack(side="left", pady=6)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-Return>", lambda _: self._generate())
        self.root.bind("<Control-s>", lambda _: self._export())
        self.root.bind("<Control-Shift-C>", lambda _: self._copy())

    def _set_issues(self, value: str) -> None:
        self.issue_box.configure(state="normal")
        self.issue_box.delete("1.0", "end")
        self.issue_box.insert("1.0", value)
        self.issue_box.configure(state="disabled")

    def _invalidate(self) -> None:
        self.current_yaml = ""
        self.last_text = None
        self.last_mode = None
        self.summary.set("配置选项已更改 · 请重新生成")

    def _paste(self) -> None:
        try:
            value = self.root.clipboard_get()
        except tk.TclError:
            messagebox.showinfo("剪贴板为空", "请先复制 VLESS 链接。", parent=self.root)
            return
        if self.input_box.get("1.0", "end-1c").strip():
            self.input_box.insert("end", "\n" + value)
        else:
            self.input_box.insert("1.0", value)
        self._invalidate()
        self.status.set("链接已粘贴；点击“生成 / 刷新”开始本地转换")

    def _import_file(self) -> None:
        path = filedialog.askopenfilename(title="导入包含 VLESS 链接的文本",
                                          filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
                                          parent=self.root)
        if not path:
            return
        try:
            data = Path(path).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            messagebox.showerror("导入失败", str(exc), parent=self.root)
            return
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", data)
        self._invalidate()
        self.status.set("已导入文本文件（仅本地读取）")

    def _clear(self) -> None:
        self.input_box.delete("1.0", "end")
        self._show_preview("")
        self._set_issues("有效节点及参数检查结果将在此处显示。")
        self._invalidate()
        self.summary.set("等待转换")
        self.status.set("已清空输入和预览")

    def _show_preview(self, value: str) -> None:
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")
        self.output_box.insert("1.0", value)
        self.output_box.configure(state="disabled")

    def _generate(self) -> bool:
        source = self.input_box.get("1.0", "end-1c")
        selected = self.mode.get()
        result = parse_links(source)
        if not result.proxies:
            self._invalidate()
            self._show_preview("")
            self._set_issues("\n".join(f"第 {issue.line} 行：{issue.message}" for issue in result.issues)
                             or "未找到 VLESS 链接。每行粘贴一个以 vless:// 开头的链接。")
            self.summary.set("未找到有效节点")
            self.status.set("转换失败：请检查输入内容")
            return False
        self.current_yaml = export_yaml(result.proxies, selected)
        self.last_text = source
        self.last_mode = selected
        self._show_preview(self.current_yaml)
        issues = [f"第 {issue.line} 行 · {'提示' if issue.warning else '错误'}：{issue.message}"
                  for issue in result.issues]
        self._set_issues("\n".join(issues) if issues else "所有节点参数检查通过，没有发现问题。")
        self.summary.set(f"✓ 已生成 {len(result.proxies)} 个节点  ·  {len(result.errors)} 个错误  ·  {len(result.warnings)} 个提示")
        self.status.set("YAML 已生成。原始节点链接不会上传或发送到任何服务器。")
        return True

    def _ensure_fresh(self) -> bool:
        source = self.input_box.get("1.0", "end-1c")
        if self.current_yaml and self.last_text == source and self.last_mode == self.mode.get():
            return True
        return self._generate()

    def _copy(self) -> None:
        if not self._ensure_fresh():
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.current_yaml)
        self.root.update()
        self.status.set("YAML 已复制到剪贴板")

    def _export(self) -> None:
        if not self._ensure_fresh():
            return
        filename = "whiteswitcher.yaml" if self.mode.get() == "full" else "whiteswitcher-nodes.yaml"
        path = filedialog.asksaveasfilename(title="保存 Mihomo YAML 配置", defaultextension=".yaml",
                                            initialfile=filename,
                                            filetypes=[("YAML 配置", "*.yaml"), ("YML 配置", "*.yml")],
                                            parent=self.root)
        if not path:
            return
        try:
            Path(path).write_text(self.current_yaml, encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("导出失败", str(exc), parent=self.root)
            return
        self.status.set("已保存 YAML 文件到所选位置")
        messagebox.showinfo("导出成功", "Mihomo YAML 已保存。\n可在支持 Mihomo 内核的客户端中导入。",
                            parent=self.root)

    def run(self) -> None:
        self.root.mainloop()


def launch() -> None:
    WhiteSwitcherApp().run()
