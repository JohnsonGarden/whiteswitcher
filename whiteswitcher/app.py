"""WhiteSwitcher desktop UI — monochrome, shadcn-inspired native controls.

No browser engine, HTTP server, usage tracking, or GUI runtime dependencies.
The project deliberately borrows shadcn/ui's *neutral visual language*; it
is a Tk desktop program, not a web app and does not claim to embed shadcn/ui.
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from tkinter import font as tkfont

from .core import APP_VERSION, export_yaml, parse_links

# Neutral theme token names mirror shadcn/ui's semantic roles.  No accent hues.
PALETTES = {
    "light": {
        "background": "#FAFAFA", "foreground": "#0A0A0A", "card": "#FFFFFF",
        "card_foreground": "#171717", "muted": "#737373", "muted_surface": "#F5F5F5",
        "border": "#E5E5E5", "primary": "#171717", "primary_hover": "#404040",
        "primary_text": "#FAFAFA", "outline_hover": "#F5F5F5",
        "editor": "#FAFAFA", "editor_fg": "#262626", "selection": "#D4D4D4",
        "code": "#18181B", "code_fg": "#E4E4E7", "code_border": "#27272A",
        "code_subtle": "#A1A1AA", "code_selection": "#52525B",
    },
    "dark": {
        "background": "#09090B", "foreground": "#FAFAFA", "card": "#121214",
        "card_foreground": "#FAFAFA", "muted": "#A1A1AA", "muted_surface": "#1C1C1F",
        "border": "#303036", "primary": "#FAFAFA", "primary_hover": "#D4D4D8",
        "primary_text": "#18181B", "outline_hover": "#252528",
        "editor": "#151517", "editor_fg": "#E4E4E7", "selection": "#52525B",
        "code": "#09090B", "code_fg": "#E4E4E7", "code_border": "#303036",
        "code_subtle": "#A1A1AA", "code_selection": "#52525B",
    },
}


def _dpi_awareness() -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


def _round_rect(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float,
                r: int, *, fill: str, outline: str = "", width: int = 1, tag: str = "shape") -> None:
    """Draw an antialias-friendly rounded polygon without Pillow at runtime."""
    r = max(0, min(r, int((x2 - x1) / 2), int((y2 - y1) / 2)))
    pts = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
           x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
           x1, y2, x1, y2-r, x1, y1+r, x1, y1]
    canvas.create_polygon(pts, smooth=True, splinesteps=24, fill=fill,
                          outline=outline, width=width, tags=tag)


def _icon(canvas: tk.Canvas, name: str, x: float, y: float,
          color: str, size: float = 17) -> None:
    """A small consistent set of 24x24 stroke icons (Lucide-like, no emoji fonts)."""
    unit = size / 24

    def line(*coords: float, width: float = 1.85) -> None:
        p = []
        for i, v in enumerate(coords):
            p.append((x if i % 2 == 0 else y) + v * unit)
        canvas.create_line(*p, fill=color, width=width * unit,
                           capstyle="round", joinstyle="round")

    def rect(x1: float, y1: float, x2: float, y2: float, radius: int = 0) -> None:
        if radius:
            _round_rect(canvas, x+x1*unit, y+y1*unit, x+x2*unit, y+y2*unit,
                        max(1, int(radius*unit)), fill="", outline=color,
                        width=max(1, int(1.8*unit)), tag="glyph")
        else:
            canvas.create_rectangle(x+x1*unit, y+y1*unit, x+x2*unit, y+y2*unit,
                                    fill="", outline=color, width=max(1, int(1.8*unit)))

    if name == "switch":
        line(4, 7, 20, 7, 16, 3)
        line(20, 7, 16, 11)
        line(20, 17, 4, 17, 8, 13)
        line(4, 17, 8, 21)
    elif name == "clipboard":
        rect(5, 5, 19, 22, 2)
        rect(9, 2, 15, 7, 2)
    elif name == "upload":
        line(12, 16, 12, 3, 7, 8)
        line(12, 3, 17, 8)
        line(4, 17, 4, 21, 20, 21, 20, 17)
    elif name == "trash":
        line(4, 6, 20, 6)
        line(8, 6, 9, 21, 15, 21, 16, 6)
        line(9, 6, 9, 4, 15, 4, 15, 6)
        line(10, 10, 10, 17)
        line(14, 10, 14, 17)
    elif name == "refresh":
        line(20, 7, 20, 3, 16, 3)
        line(20, 3, 17, 6)
        line(20, 10, 18, 6, 14, 4, 9, 4, 5, 7)
        line(4, 17, 4, 21, 8, 21)
        line(4, 21, 7, 18)
        line(4, 14, 6, 18, 10, 20, 15, 20, 19, 17)
    elif name == "copy":
        rect(8, 8, 20, 21, 2)
        line(4, 17, 4, 4, 16, 4)
    elif name == "download":
        line(12, 3, 12, 16, 7, 11)
        line(12, 16, 17, 11)
        line(4, 18, 4, 21, 20, 21, 20, 18)
    elif name == "arrow":
        line(4, 12, 20, 12, 14, 6)
        line(20, 12, 14, 18)
    elif name == "check":
        line(4, 12, 10, 18, 20, 6, width=2.4)
    elif name == "lock":
        rect(5, 10, 19, 21, 2)
        line(8, 10, 8, 7, 9, 4, 12, 3, 15, 4, 16, 7, 16, 10)
    elif name == "moon":
        line(19, 14, 16, 18, 11, 19, 6, 16, 4, 11, 6, 6, 10, 4, 9, 8, 12, 12, 17, 14, 19, 14)
    elif name == "sun":
        canvas.create_oval(x+8*unit, y+8*unit, x+16*unit, y+16*unit,
                           outline=color, width=1.75*unit)
        for a,b,c,d in [(12,2,12,5),(12,19,12,22),(2,12,5,12),(19,12,22,12),
                        (5,5,7,7),(17,17,19,19),(5,19,7,17),(17,7,19,5)]:
            line(a,b,c,d)
    elif name == "file":
        line(13, 3, 5, 3, 5, 21, 19, 21, 19, 9, 13, 3, 13, 9, 19, 9)
        line(9, 14, 15, 14)
        line(9, 17, 15, 17)


class RoundedSurface(tk.Canvas):
    """Canvas border with a normal Frame child: responsive native widget content."""
    def __init__(self, parent, colors: dict, *, fill: str | None = None,
                 border: str | None = None, radius: int = 12, inset: int = 20):
        self.colors = colors
        self.fill_color = fill or colors["card"]
        self.border_color = border or colors["border"]
        self.radius = radius
        self.inset = inset
        super().__init__(parent, bg=parent.cget("bg"), highlightthickness=0, bd=0)
        self.body = tk.Frame(self, bg=self.fill_color)
        self.child_id = self.create_window((inset, inset), anchor="nw", window=self.body)
        self.bind("<Configure>", self._resize)

    def _resize(self, _event=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        self.delete("shape")
        _round_rect(self, 1, 1, w-2, h-2, self.radius, fill=self.fill_color,
                    outline=self.border_color, tag="shape")
        self.tag_lower("shape")
        self.itemconfigure(self.child_id, width=max(1, w - 2*self.inset),
                           height=max(1, h - 2*self.inset))


class FlatButton(tk.Canvas):
    """Accessible click/keyboard native button with monochrome rounded border."""
    def __init__(self, parent, label: str, command, colors: dict, *,
                 kind: str = "outline", icon: str | None = None,
                 height: int = 38, compact: bool = False):
        self.colors = colors
        self.kind = kind
        self.label = label
        self.action = command
        self.icon_name = icon
        self.over = False
        self.compact = compact
        self.font_obj = tkfont.Font(family="Microsoft YaHei UI" if sys.platform == "win32" else "Noto Sans CJK SC",
                                   size=9, weight="bold" if kind == "primary" else "normal")
        pad = 14 if compact else 17
        width = self.font_obj.measure(label) + 2*pad + (21 if icon else 0)
        super().__init__(parent, width=width, height=height, bd=0,
                         bg=parent.cget("bg"), highlightthickness=0,
                         cursor="hand2", takefocus=1)
        self.bind("<Enter>", lambda _: self._hover(True))
        self.bind("<Leave>", lambda _: self._hover(False))
        self.bind("<Button-1>", lambda _: self.action())
        self.bind("<Return>", lambda _: self.action())
        self.bind("<space>", lambda _: self.action())
        self.bind("<FocusIn>", lambda _: self._draw())
        self.bind("<FocusOut>", lambda _: self._draw())
        self._draw()

    def _hover(self, on: bool):
        self.over = on
        self._draw()

    def _draw(self):
        self.delete("all")
        c = self.colors
        width, height = int(self.cget("width")), int(self.cget("height"))
        if self.kind == "primary":
            bg = c["primary_hover"] if self.over else c["primary"]
            fg, border = c["primary_text"], bg
        elif self.kind == "ghost":
            bg = c["outline_hover"] if self.over else c["card"]
            fg, border = c["foreground"], bg
        else:
            bg = c["outline_hover"] if self.over else c["card"]
            fg, border = c["foreground"], c["border"]
        _round_rect(self, 1, 1, width-2, height-2, 8, fill=bg, outline=border)
        text_w = self.font_obj.measure(self.label)
        content_w = text_w + (21 if self.icon_name else 0)
        left = (width-content_w)/2
        if self.icon_name:
            _icon(self, self.icon_name, left, (height-16)/2, fg, 16)
            left += 21
        self.create_text(left, height/2, anchor="w", text=self.label,
                         font=self.font_obj, fill=fg)
        if self.focus_get() is self:
            _round_rect(self, 3, 3, width-4, height-4, 7, fill="", outline=c["muted"])


class ModeTabs(tk.Canvas):
    def __init__(self, parent, variable: tk.StringVar, on_change, colors: dict):
        self.c = colors
        self.variable = variable
        self.on_change = on_change
        super().__init__(parent, width=244, height=38, bg=parent.cget("bg"),
                         bd=0, highlightthickness=0, cursor="hand2")
        self.bind("<Button-1>", self._clicked)
        self._draw()

    def _clicked(self, event):
        self.variable.set("full" if event.x < 122 else "nodes")
        self._draw()
        self.on_change()

    def _draw(self):
        self.delete("all")
        c = self.c
        _round_rect(self, 0, 0, 244, 38, 9, fill=c["muted_surface"])
        left = 3 if self.variable.get() == "full" else 122
        _round_rect(self, left, 3, left+119, 35, 7, fill=c["card"], outline=c["border"])
        font = ("Microsoft YaHei UI" if sys.platform == "win32" else "Noto Sans CJK SC", 9)
        for x, label, mode in ((62, "完整配置", "full"), (182, "仅节点", "nodes")):
            self.create_text(x, 19, text=label, font=font,
                             fill=c["foreground"] if mode == self.variable.get() else c["muted"])


class WhiteSwitcherApp:
    def __init__(self) -> None:
        _dpi_awareness()
        self.root = tk.Tk()
        self.root.title(f"WhiteSwitcher {APP_VERSION}  ·  VLESS → Mihomo")
        self.root.geometry("1180x760")
        self.root.minsize(1020, 650)
        self.theme = "light"
        self.mode = tk.StringVar(value="full")
        self.status = tk.StringVar(value="所有操作仅在本机完成，不会上传链接或密钥。")
        self.summary = tk.StringVar(value="就绪 · 等待生成")
        self.diagnostics = "参数检查结果将在生成后显示。"
        self.current_yaml = ""
        self.last_text: str | None = None
        self.last_mode: str | None = None
        self._load_icon()
        self._layout()
        self._bind_shortcuts()

    def _load_icon(self):
        try:
            base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
            image = base / "WhiteSwitcher.png"
            if image.exists():
                self._window_icon = tk.PhotoImage(file=str(image))
                self.root.iconphoto(True, self._window_icon)
        except (OSError, tk.TclError):
            pass

    def _text(self, parent, text: str = "", size: int = 10, *, bold: bool = False,
              color: str = "foreground", bg: str | None = None, **kwargs):
        font = ("Microsoft YaHei UI" if sys.platform == "win32" else "Noto Sans CJK SC",
                size, "bold" if bold else "normal")
        return tk.Label(parent, text=text, font=font,
                        fg=self.c.get(color, color), bg=bg or parent.cget("bg"), **kwargs)

    def _action(self, parent, text, command, kind="outline", icon=None, **kwargs):
        return FlatButton(parent, text, command, self.c, kind=kind, icon=icon, **kwargs)

    def _layout(self):
        c = self.c = PALETTES[self.theme]
        root = self.root
        root.configure(bg=c["background"])
        for widget in root.winfo_children():
            widget.destroy()

        # Header / brand
        header = tk.Frame(root, bg=c["card"], height=76)
        header.pack(fill="x")
        header.pack_propagate(False)
        inside = tk.Frame(header, bg=c["card"])
        inside.pack(fill="both", expand=True, padx=31, pady=16)
        mark = tk.Canvas(inside, width=42, height=42, bg=c["card"], highlightthickness=0)
        mark.pack(side="left")
        _round_rect(mark, 0, 0, 42, 42, 11, fill=c["primary"])
        _icon(mark, "switch", 8, 8, c["primary_text"], 26)
        brand = tk.Frame(inside, bg=c["card"])
        brand.pack(side="left", padx=(13, 0))
        self._text(brand, "WhiteSwitcher", 14, bold=True).pack(anchor="w")
        self._text(brand, "VLESS  /  MIHOMO", 8, color="muted").pack(anchor="w", pady=(1, 0))

        tools = tk.Frame(inside, bg=c["card"])
        tools.pack(side="right", anchor="center")
        self._action(tools, "深色模式" if self.theme == "light" else "浅色模式",
                     self._toggle_theme, "ghost", "moon" if self.theme == "light" else "sun",
                     compact=True).pack(side="right", padx=(12, 0))
        self._text(tools, "●  100% 离线运行", 9, color="muted").pack(side="right", padx=10)
        tk.Frame(root, bg=c["border"], height=1).pack(fill="x")

        # Page header
        hero = tk.Frame(root, bg=c["background"])
        hero.pack(fill="x", padx=31, pady=(24, 20))
        heading = tk.Frame(hero, bg=c["background"])
        heading.pack(side="left")
        self._text(heading, "将 VLESS 链接转换为 YAML", 21, bold=True).pack(anchor="w")
        self._text(heading, "粘贴节点链接，生成 Mihomo / Clash Meta 可导入的配置文件。",
                   10, color="muted").pack(anchor="w", pady=(6, 0))
        tag = tk.Frame(hero, bg=c["muted_surface"], padx=12, pady=7)
        tag.pack(side="right", anchor="s", pady=(0, 5))
        self._text(tag, "REALITY  ·  TLS  ·  WS  ·  GRPC", 8, color="muted",
                   bg=c["muted_surface"]).pack()

        # Two responsive cards
        stage = tk.Frame(root, bg=c["background"])
        stage.pack(fill="both", expand=True, padx=31, pady=(0, 19))
        stage.grid_columnconfigure(0, weight=1, uniform="cards")
        stage.grid_columnconfigure(1, weight=1, uniform="cards")
        stage.grid_rowconfigure(0, weight=1)
        left = RoundedSurface(stage, c, inset=21)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        right = RoundedSurface(stage, c, inset=21)
        right.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        self._left_card(left.body)
        self._right_card(right.body)

        # Footer; no colored status bar, version sits on the same baseline.
        footer = tk.Frame(root, bg=c["background"])
        footer.pack(fill="x", padx=32, pady=(0, 15))
        self._text(footer, "", 9, color="muted", textvariable=self.status).pack(side="left")
        self._text(footer, f"WhiteSwitcher  v{APP_VERSION}", 9,
                   color="muted").pack(side="right")
        self._text(footer, "Ctrl + Enter 生成   ·   Ctrl + S 导出", 9,
                   color="muted").pack(side="right", padx=(0, 38))

    def _left_card(self, parent):
        c = self.c
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)
        heading = tk.Frame(parent, bg=c["card"])
        heading.grid(row=0, column=0, sticky="ew")
        self._text(heading, "01", 9, bold=True, color="muted").pack(side="left", padx=(0, 11))
        self._text(heading, "VLESS 链接", 12, bold=True).pack(side="left")
        self._text(heading, "INPUT", 8, color="muted").pack(side="right")
        self._text(parent, "支持多个节点 · 每行一条链接 · 自动去重", 9,
                   color="muted").grid(row=1, column=0, sticky="w", pady=(7, 17))

        editor_shell = RoundedSurface(parent, c, fill=c["editor"], radius=9, inset=11)
        editor_shell.grid(row=2, column=0, sticky="nsew")
        editor_shell.body.grid_rowconfigure(0, weight=1)
        editor_shell.body.grid_columnconfigure(0, weight=1)
        self.input_box = tk.Text(editor_shell.body, bg=c["editor"], fg=c["editor_fg"],
                                 insertbackground=c["foreground"], selectbackground=c["selection"],
                                 relief="flat", bd=0, undo=True, wrap="char", width=30, height=11,
                                 font=("Consolas" if sys.platform == "win32" else "Noto Sans Mono CJK SC", 10),
                                 padx=7, pady=7, highlightthickness=0, spacing2=3)
        self.input_box.grid(row=0, column=0, sticky="nsew")
        self.input_box.bind("<<Modified>>", self._modified)
        self.placeholder = self._text(editor_shell.body, "vless://uuid@server:443?...", 10,
                                      color="muted", bg=c["editor"], cursor="xterm")
        self.placeholder.place(x=8, y=9)
        self.placeholder.bind("<Button-1>", lambda _: self.input_box.focus_set())
        self.input_box.edit_modified(False)

        actions = tk.Frame(parent, bg=c["card"])
        actions.grid(row=3, column=0, sticky="ew", pady=(13, 15))
        self._action(actions, "粘贴链接", self._paste, "outline", "clipboard", compact=True).pack(
            side="left", padx=(0, 7))
        self._action(actions, "导入 TXT", self._import_file, "outline", "upload", compact=True).pack(side="left")
        self._action(actions, "清空", self._clear, "ghost", "trash", compact=True).pack(side="right")

        tk.Frame(parent, bg=c["border"], height=1).grid(row=4, column=0, sticky="ew")
        diag_header = tk.Frame(parent, bg=c["card"])
        diag_header.grid(row=5, column=0, sticky="ew", pady=(14, 8))
        self._text(diag_header, "转换诊断", 10, bold=True).pack(side="left")
        self._text(diag_header, "VALIDATION", 8, color="muted").pack(side="right")
        issues_shell = RoundedSurface(parent, c, fill=c["muted_surface"],
                                      border=c["muted_surface"], radius=8, inset=10)
        issues_shell.grid(row=6, column=0, sticky="nsew", ipady=0)
        issues_shell.configure(height=82)
        parent.grid_rowconfigure(6, minsize=82)
        self.issue_box = tk.Text(issues_shell.body, height=3, wrap="word", bg=c["muted_surface"],
                                 fg=c["muted"], relief="flat", bd=0, padx=5, pady=4,
                                 highlightthickness=0, state="disabled",
                                 font=("Microsoft YaHei UI" if sys.platform == "win32" else "Noto Sans CJK SC", 9))
        self.issue_box.pack(fill="both", expand=True)
        self._set_issues(self.diagnostics)

    def _right_card(self, parent):
        c = self.c
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(3, weight=1)
        heading = tk.Frame(parent, bg=c["card"])
        heading.grid(row=0, column=0, sticky="ew")
        self._text(heading, "02", 9, bold=True, color="muted").pack(side="left", padx=(0, 11))
        self._text(heading, "Mihomo 配置", 12, bold=True).pack(side="left")
        self._text(heading, "OUTPUT", 8, color="muted").pack(side="right")

        options = tk.Frame(parent, bg=c["card"])
        options.grid(row=1, column=0, sticky="ew", pady=(16, 13))
        ModeTabs(options, self.mode, self._invalidate, c).pack(side="left")
        self._text(options, "YAML", 9, color="muted").pack(side="right")
        self._text(parent, "完整配置包含节点选择、自动测速与 MATCH 规则", 9,
                   color="muted").grid(row=2, column=0, sticky="w", pady=(0, 12))

        code_panel = RoundedSurface(parent, c, fill=c["code"], border=c["code_border"],
                                    radius=10, inset=10)
        code_panel.grid(row=3, column=0, sticky="nsew")
        code_panel.body.grid_columnconfigure(0, weight=1)
        code_panel.body.grid_rowconfigure(1, weight=1)
        code_head = tk.Frame(code_panel.body, bg=c["code"])
        code_head.grid(row=0, column=0, sticky="ew", padx=8, pady=(5, 11))
        dot = tk.Canvas(code_head, width=8, height=8, bg=c["code"], highlightthickness=0)
        dot.create_oval(0, 0, 7, 7, fill=c["code_subtle"], outline="")
        dot.pack(side="left", padx=(0, 9))
        self._text(code_head, "whiteswitcher.yaml", 9,
                   color=c["code_subtle"], bg=c["code"]).pack(side="left")
        self._text(code_head, "UTF-8", 8,
                   color=c["code_subtle"], bg=c["code"]).pack(side="right")
        self.output_box = tk.Text(code_panel.body, state="disabled", wrap="none", bd=0,
                                  relief="flat", highlightthickness=0, bg=c["code"], fg=c["code_fg"],
                                  insertbackground=c["code_fg"], selectbackground=c["code_selection"],
                                  font=("Consolas" if sys.platform == "win32" else "Noto Sans Mono CJK SC", 10),
                                  padx=8, pady=7, width=42, height=13, spacing2=2)
        self.output_box.grid(row=1, column=0, sticky="nsew")
        scroll = tk.Scrollbar(code_panel.body, command=self.output_box.yview, width=9,
                              bg=c["code_border"], troughcolor=c["code"],
                              relief="flat", bd=0, highlightthickness=0,
                              activebackground=c["code_subtle"])
        scroll.grid(row=1, column=1, sticky="ns")
        self.output_box.config(yscrollcommand=scroll.set)
        self.output_box.tag_configure("comment", foreground=c["code_subtle"])
        self.output_hint = self._text(code_panel.body, "生成后将在这里预览 YAML 配置", 9,
                                      color=c["code_subtle"], bg=c["code"])
        self.output_hint.place(x=17, y=77)

        actions = tk.Frame(parent, bg=c["card"])
        actions.grid(row=4, column=0, sticky="ew", pady=(15, 8))
        self._action(actions, "生成 YAML", self._generate, "primary", "arrow", compact=True).pack(
            side="left", padx=(0, 7))
        self._action(actions, "复制", self._copy, "outline", "copy", compact=True).pack(
            side="left", padx=(0, 7))
        self._action(actions, "导出 .yaml", self._export, "outline", "download", compact=True).pack(
            side="right")
        self._text(parent, "", 9, color="muted", textvariable=self.summary).grid(
            row=5, column=0, sticky="w", pady=(2, 1))

    def _toggle_theme(self):
        saved_input = self.input_box.get("1.0", "end-1c")
        saved_output = self.current_yaml
        self.theme = "dark" if self.theme == "light" else "light"
        self._layout()
        if saved_input:
            self.input_box.insert("1.0", saved_input)
            self.placeholder.place_forget()
        self._show_preview(saved_output)
        self.input_box.edit_modified(False)

    def _modified(self, _event=None):
        if not self.input_box.edit_modified():
            return
        self.input_box.edit_modified(False)
        if self.input_box.get("1.0", "end-1c").strip():
            self.placeholder.place_forget()
        else:
            self.placeholder.place(x=8, y=9)
        self._invalidate()

    def _bind_shortcuts(self):
        self.root.bind("<Control-Return>", lambda _: self._generate())
        self.root.bind("<Control-s>", lambda _: self._export())
        self.root.bind("<Control-Shift-C>", lambda _: self._copy())

    def _set_issues(self, value):
        self.diagnostics = value
        self.issue_box.configure(state="normal")
        self.issue_box.delete("1.0", "end")
        self.issue_box.insert("1.0", value)
        self.issue_box.configure(state="disabled")

    def _invalidate(self):
        self.current_yaml = ""
        self.last_text = None
        self.last_mode = None
        self.summary.set("配置已更改 · 请生成 YAML")

    def _paste(self):
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
        self.status.set("链接已粘贴")

    def _import_file(self):
        path = filedialog.askopenfilename(title="导入 VLESS 文本", filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
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

    def _clear(self):
        self.input_box.delete("1.0", "end")
        self._show_preview("")
        self._set_issues("参数检查结果将在生成后显示。")
        self._invalidate()
        self.summary.set("就绪 · 等待生成")

    def _show_preview(self, value):
        if value:
            self.output_hint.place_forget()
        else:
            self.output_hint.place(x=17, y=77)
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")
        self.output_box.insert("1.0", value)
        # Syntax highlighting stays strictly grayscale.
        for i, line in enumerate(value.splitlines(), start=1):
            if line.lstrip().startswith("#"):
                self.output_box.tag_add("comment", f"{i}.0", f"{i}.end")
        self.output_box.configure(state="disabled")

    def _generate(self):
        source = self.input_box.get("1.0", "end-1c")
        # Clear Tk Text's dirty flag before queued <<Modified>> events can
        # accidentally invalidate a newly generated preview.
        self.input_box.edit_modified(False)
        selected = self.mode.get()
        result = parse_links(source)
        if not result.proxies:
            self._invalidate()
            self._show_preview("")
            self._set_issues("\n".join(f"第 {x.line} 行：{x.message}" for x in result.issues)
                             or "未找到 VLESS 链接。每行粘贴一个 vless:// 链接。")
            self.summary.set("未发现有效节点 · 请检查输入")
            self.status.set("未生成配置 · 请检查 VLESS 输入")
            return False
        self.current_yaml = export_yaml(result.proxies, selected)
        self.last_text = source
        self.last_mode = selected
        self._show_preview(self.current_yaml)
        issues = [f"第 {x.line} 行 · {'提示' if x.warning else '错误'}：{x.message}" for x in result.issues]
        self._set_issues("\n".join(issues) if issues else "✓  所有节点参数均通过校验，没有发现问题。")
        self.summary.set(f"✓  {len(result.proxies)} 个节点   ·   {len(result.errors)} 个错误   ·   {len(result.warnings)} 个提示")
        self.status.set("YAML 已生成 · 所有转换均在本机完成")
        return True

    def _ensure_fresh(self):
        source = self.input_box.get("1.0", "end-1c")
        if self.current_yaml and self.last_text == source and self.last_mode == self.mode.get():
            return True
        return self._generate()

    def _copy(self):
        if not self._ensure_fresh():
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.current_yaml)
        self.root.update()
        self.summary.set("✓  YAML 已复制到剪贴板")
        self.status.set("配置已复制；请注意系统剪贴板历史")

    def _export(self):
        if not self._ensure_fresh():
            return
        filename = "whiteswitcher.yaml" if self.mode.get() == "full" else "whiteswitcher-nodes.yaml"
        path = filedialog.asksaveasfilename(title="保存 Mihomo YAML", defaultextension=".yaml",
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
        self.summary.set("✓  YAML 文件已保存")
        self.status.set("配置文件已写入所选位置")
        messagebox.showinfo("导出成功", "Mihomo YAML 已保存。\n可在支持 Mihomo 内核的客户端中导入。", parent=self.root)

    def run(self):
        self.root.mainloop()


def launch():
    WhiteSwitcherApp().run()
