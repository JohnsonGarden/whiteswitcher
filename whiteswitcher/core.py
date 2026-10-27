"""Offline VLESS URI -> Mihomo YAML conversion (no network access)."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, unquote, urlsplit

import yaml

APP_VERSION = "1.0.0"
SUPPORTED_TRANSPORTS = {"tcp", "ws", "grpc", "http", "h2", "xhttp"}
KNOWN_PARAMS = {
    "security", "type", "sni", "servername", "fp", "fingerprint", "alpn",
    "flow", "encryption", "pbk", "publickey", "sid", "shortid", "host",
    "path", "servicename", "mode", "allowinsecure", "insecure", "udp",
    "packetencoding", "ed", "earlydata", "eh", "earlydataheadername",
    "headertype", "method", "authority", "extra", "spx", "seed",
}
INVALID_PERCENT = re.compile(r"%(?![0-9a-fA-F]{2})")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class LinkError(ValueError):
    """Actionable error for an invalid or unsupported VLESS link."""


@dataclass
class ParseIssue:
    line: int
    message: str
    warning: bool = False


@dataclass
class ParseResult:
    proxies: list[dict] = field(default_factory=list)
    issues: list[ParseIssue] = field(default_factory=list)
    total: int = 0

    @property
    def errors(self) -> list[ParseIssue]:
        return [issue for issue in self.issues if not issue.warning]

    @property
    def warnings(self) -> list[ParseIssue]:
        return [issue for issue in self.issues if issue.warning]


def _bool(value: str, label: str) -> bool:
    if value.lower() in {"1", "true", "yes"}:
        return True
    if value.lower() in {"0", "false", "no"}:
        return False
    raise LinkError(f"{label} 必须是 true/false 或 1/0")


def _positive_int(value: str, label: str, *, maximum: int = 65535) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise LinkError(f"{label} 必须是整数") from exc
    if not 0 <= result <= maximum:
        raise LinkError(f"{label} 超出允许范围 0–{maximum}")
    return result


def _query(link: str) -> dict[str, str]:
    try:
        pairs = parse_qsl(urlsplit(link).query, keep_blank_values=True, max_num_fields=100)
    except ValueError as exc:
        raise LinkError("查询参数过多或格式有误") from exc
    # Keep the last value in the case of duplicated query keys.
    return {key.lower(): val for key, val in pairs}


def _first(params: dict[str, str], *keys: str) -> str:
    for key in keys:
        if key in params:
            return params[key]
    return ""


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_vless_link(link: str) -> tuple[dict, list[str]]:
    """Parse one VLESS URI; return a Mihomo proxy and non-fatal warnings."""
    link = link.strip()
    if INVALID_PERCENT.search(link):
        raise LinkError("URL 包含无效的百分号编码")
    if CONTROL.search(link):
        raise LinkError("链接包含控制字符")
    try:
        uri = urlsplit(link)
        if uri.scheme.lower() != "vless":
            raise LinkError("仅支持 vless:// 链接")
        if uri.password is not None:
            raise LinkError("用户信息格式错误：VLESS 应使用 UUID@服务器")
        raw_uuid = unquote(uri.username or "")
        try:
            user_id = str(uuid.UUID(raw_uuid))
        except (ValueError, AttributeError) as exc:
            raise LinkError("UUID 格式无效") from exc
        server = uri.hostname or ""
        port = uri.port
    except LinkError:
        raise
    except ValueError as exc:
        raise LinkError("服务器地址或端口格式无效") from exc

    if not server or CONTROL.search(server) or any(ch.isspace() for ch in server):
        raise LinkError("服务器地址缺失或无效")
    if not port or not 1 <= port <= 65535:
        raise LinkError("端口必须在 1–65535 之间")

    params = _query(link)
    warnings: list[str] = []
    for key in sorted(set(params) - KNOWN_PARAMS):
        warnings.append(f"未识别参数 {key}，已忽略")
    for key in ("spx", "seed"):
        if params.get(key):
            warnings.append(f"{key} 扩展参数未映射到 Mihomo")

    transport = _first(params, "type").lower() or "tcp"
    if transport not in SUPPORTED_TRANSPORTS:
        raise LinkError(f"暂不支持传输类型 {transport}，未生成可能失效的节点")
    if _first(params, "headertype") not in {"", "none"}:
        raise LinkError("暂不支持自定义 TCP headerType，避免生成无法连接的节点")
    if "extra" in params and params["extra"]:
        raise LinkError("XHTTP extra 等扩展配置无法可靠转换，请使用可展开参数的标准链接")

    security = _first(params, "security").lower()
    public_key = _first(params, "pbk", "publickey")
    if not security:
        security = "reality" if public_key else ("tls" if _first(params, "sni", "servername") else "none")
    if security not in {"none", "tls", "reality"}:
        raise LinkError(f"暂不支持 security={security}")
    if security == "reality" and not public_key:
        raise LinkError("Reality 缺少 pbk 公钥")
    if public_key and security != "reality":
        raise LinkError("存在 Reality 公钥，但 security 不是 reality")
    if security == "none" and _first(params, "flow"):
        raise LinkError("flow 要求 TLS/Reality，但链接中未启用")

    name = unquote(uri.fragment).strip() if uri.fragment else ""
    name = CONTROL.sub(" ", name).strip() or f"{server}:{port}"
    if len(name) > 90:
        name = name[:90].rstrip()

    proxy: dict = {
        "name": name,
        "type": "vless",
        "server": server,
        "port": port,
        "uuid": user_id,
        "udp": True,
    }
    if "udp" in params:
        proxy["udp"] = _bool(params["udp"], "udp")
    if security != "none":
        proxy["tls"] = True
    if (sni := _first(params, "sni", "servername")):
        proxy["servername"] = sni
    if (fingerprint := _first(params, "fp", "fingerprint")):
        proxy["client-fingerprint"] = fingerprint
    if (alpn := _first(params, "alpn")):
        proxy["alpn"] = _split_csv(alpn)
    if (flow := _first(params, "flow")):
        if flow not in {"xtls-rprx-vision"}:
            raise LinkError(f"不支持的 flow：{flow}")
        proxy["flow"] = flow
    if (encoding := _first(params, "encryption")) and encoding.lower() != "none":
        proxy["encryption"] = encoding
    if (packet_encoding := _first(params, "packetencoding")):
        if packet_encoding not in {"xudp", "packetaddr"}:
            raise LinkError("packetEncoding 只能为 xudp 或 packetaddr")
        proxy["packet-encoding"] = packet_encoding
    for field_name in ("allowinsecure", "insecure"):
        if field_name in params:
            proxy["skip-cert-verify"] = _bool(params[field_name], field_name)
            break
    if security == "reality":
        opts = {"public-key": public_key}
        if (short_id := _first(params, "sid", "shortid")):
            opts["short-id"] = short_id
        proxy["reality-opts"] = opts

    host = _first(params, "host")
    path = _first(params, "path") or "/"
    if transport == "ws":
        options: dict = {"path": path}
        if host:
            options["headers"] = {"Host": host}
        if (early_data := _first(params, "ed", "earlydata")):
            options["max-early-data"] = _positive_int(early_data, "Early Data", maximum=2147483647)
            options["early-data-header-name"] = _first(params, "eh", "earlydataheadername") or "Sec-WebSocket-Protocol"
        proxy.update({"network": "ws", "ws-opts": options})
    elif transport == "grpc":
        options = {"grpc-service-name": _first(params, "servicename")}
        proxy.update({"network": "grpc", "grpc-opts": options})
        if "authority" in params:
            warnings.append("gRPC authority 没有等价的通用 Mihomo 字段，已忽略")
    elif transport == "h2":
        options = {"path": path}
        if host:
            options["host"] = _split_csv(host)
        proxy.update({"network": "h2", "h2-opts": options})
    elif transport == "http":
        options = {"method": _first(params, "method") or "GET", "path": [path]}
        if host:
            options["headers"] = {"Host": _split_csv(host)}
        proxy.update({"network": "http", "http-opts": options})
    elif transport == "xhttp":
        options = {"path": path}
        if host:
            options["host"] = host
        if (mode := _first(params, "mode")):
            if mode not in {"auto", "stream-one", "stream-up", "packet-up"}:
                raise LinkError(f"未知 XHTTP mode={mode}")
            options["mode"] = mode
        proxy.update({"network": "xhttp", "xhttp-opts": options})
    return proxy, warnings


def parse_links(text: str) -> ParseResult:
    result = ParseResult()
    seen_links: set[str] = set()
    used_names: set[str] = set()
    for line_number, raw in enumerate(text.splitlines(), 1):
        link = raw.strip()
        if not link or link.startswith("#"):
            continue
        result.total += 1
        if link in seen_links:
            result.issues.append(ParseIssue(line_number, "重复链接，已跳过", True))
            continue
        seen_links.add(link)
        try:
            proxy, warnings = parse_vless_link(link)
        except LinkError as exc:
            result.issues.append(ParseIssue(line_number, str(exc)))
            continue
        base_name = proxy["name"]
        name = base_name
        suffix = 2
        while name in used_names:
            name = f"{base_name} ({suffix})"
            suffix += 1
        proxy["name"] = name
        used_names.add(name)
        result.proxies.append(proxy)
        for warning in warnings:
            result.issues.append(ParseIssue(line_number, warning, True))
    return result


class _IndentedDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow=flow, indentless=False)


def build_config(proxies: list[dict], mode: str = "full") -> dict:
    if not proxies:
        raise ValueError("至少需要一个有效节点")
    if mode not in {"full", "nodes"}:
        raise ValueError("导出模式必须为 full 或 nodes")
    if mode == "nodes":
        return {"proxies": proxies}
    names = [proxy["name"] for proxy in proxies]
    return {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "warning",
        "ipv6": False,
        "proxies": proxies,
        "proxy-groups": [
            {"name": "节点选择", "type": "select", "proxies": ["自动选择", *names, "DIRECT"]},
            {"name": "自动选择", "type": "url-test", "proxies": names,
             "url": "https://www.gstatic.com/generate_204", "interval": 300},
        ],
        "rules": ["MATCH,节点选择"],
    }


def export_yaml(proxies: list[dict], mode: str = "full") -> str:
    config = build_config(proxies, mode)
    return ("# WhiteSwitcher · Offline VLESS to Mihomo converter\n"
            + yaml.dump(config, Dumper=_IndentedDumper, allow_unicode=True,
                        sort_keys=False, width=120, default_flow_style=False))
