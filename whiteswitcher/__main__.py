"""Run desktop UI by default; CLI for automation."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import APP_VERSION, export_yaml, parse_links


def main() -> int:
    # Windows redirected consoles can default to a legacy ANSI code page.
    # Diagnostics include Chinese text; make CLI piping predictable.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="WhiteSwitcher — 离线 VLESS → Mihomo YAML 转换器")
    parser.add_argument("--input", "-i", type=Path, help="含 VLESS 链接的 UTF-8 文件")
    parser.add_argument("--output", "-o", type=Path, help="输出 YAML 文件")
    parser.add_argument("--mode", choices=("full", "nodes"), default="full")
    parser.add_argument("--version", action="version", version=APP_VERSION)
    args = parser.parse_args()
    if not args.input and not args.output:
        from .app import launch
        launch()
        return 0
    if not args.input or not args.output:
        parser.error("命令行模式需要同时提供 --input 和 --output")
    try:
        source = args.input.read_text(encoding="utf-8-sig")
        result = parse_links(source)
        for issue in result.issues:
            # Avoid printing secrets from the input URI; only report diagnostic messages.
            print(f"第 {issue.line} 行：{issue.message}", file=sys.stderr)
        if not result.proxies:
            print("没有可导出的有效节点", file=sys.stderr)
            return 1
        args.output.write_text(export_yaml(result.proxies, args.mode), encoding="utf-8")
        print(f"已导出 {len(result.proxies)} 个节点 → {args.output}")
        return 0 if not result.errors else 2
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"转换失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
