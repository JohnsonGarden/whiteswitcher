import Foundation

/// Port of the Windows converter's documented VLESS-to-Mihomo behavior.
/// No HTTP requests, subprocesses, telemetry or persisted node credentials.
public enum WhiteSwitcherConverter {
    public enum Mode: String, CaseIterable, Identifiable {
        case full, nodes
        public var id: String { rawValue }
        public var label: String { self == .full ? "完整配置" : "仅节点" }
    }

    public struct Issue: Identifiable {
        public let id = UUID()
        public let line: Int
        public let message: String
        public let warning: Bool
    }

    public struct Result {
        public let proxies: [YAMLValue]
        public let issues: [Issue]
        public let total: Int
        public var errors: [Issue] { issues.filter { !$0.warning } }
        public var warnings: [Issue] { issues.filter { $0.warning } }
    }

    public struct ConversionError: LocalizedError {
        public let reason: String
        public var errorDescription: String? { reason }
        init(_ reason: String) { self.reason = reason }
    }

    private static let supported = Set(["tcp", "ws", "grpc", "http", "h2", "xhttp"])
    private static let known = Set([
        "security", "type", "sni", "servername", "fp", "fingerprint", "alpn",
        "flow", "encryption", "pbk", "publickey", "sid", "shortid", "host",
        "path", "servicename", "mode", "allowinsecure", "insecure", "udp",
        "packetencoding", "ed", "earlydata", "eh", "earlydataheadername",
        "headertype", "method", "authority", "extra", "spx", "seed"
    ])

    public static func parse(_ raw: String) -> Result {
        var proxies: [YAMLValue] = []
        var issues: [Issue] = []
        var usedLinks = Set<String>()
        var usedNames = Set<String>()
        var total = 0
        // Keep trailing empty lines harmless; line numbers are stable for diagnostics.
        for (index, line) in raw.components(separatedBy: .newlines).enumerated() {
            let text = line.trimmingCharacters(in: .whitespacesAndNewlines)
            if text.isEmpty || text.hasPrefix("#") { continue }
            total += 1
            if !usedLinks.insert(text).inserted {
                issues.append(Issue(line: index + 1, message: "重复链接，已跳过", warning: true))
                continue
            }
            do {
                let (proxy, name, warnings) = try parseLink(text)
                var finalName = name
                var number = 2
                while usedNames.contains(finalName) {
                    finalName = "\(name) (\(number))"
                    number += 1
                }
                usedNames.insert(finalName)
                var updated = proxy
                updated[0] = ("name", .text(finalName))
                proxies.append(.object(updated))
                issues += warnings.map { Issue(line: index + 1, message: $0, warning: true) }
            } catch let error as ConversionError {
                issues.append(Issue(line: index + 1, message: error.reason, warning: false))
            } catch {
                issues.append(Issue(line: index + 1, message: "无法解析链接", warning: false))
            }
        }
        return Result(proxies: proxies, issues: issues, total: total)
    }

    public static func export(_ result: Result, mode: Mode) throws -> String {
        guard !result.proxies.isEmpty else { throw ConversionError("至少需要一个有效节点") }
        var fields: [(String, YAMLValue)] = []
        if mode == .full {
            fields += [
                ("mixed-port", .integer(7890)),
                ("allow-lan", .boolean(false)),
                ("mode", .text("rule")),
                ("log-level", .text("warning")),
                ("ipv6", .boolean(false))
            ]
        }
        fields.append(("proxies", .array(result.proxies)))
        if mode == .full {
            let names = result.proxies.compactMap { node -> String? in
                guard case let .object(fields) = node else { return nil }
                guard let first = fields.first, case let .text(name) = first.1 else { return nil }
                return name
            }
            fields.append(("proxy-groups", .array([
                .object([("name", .text("节点选择")), ("type", .text("select")),
                         ("proxies", .array((["自动选择"] + names + ["DIRECT"]).map(YAMLValue.text)))]),
                .object([("name", .text("自动选择")), ("type", .text("url-test")),
                         ("proxies", .array(names.map(YAMLValue.text))),
                         ("url", .text("https://www.gstatic.com/generate_204")),
                         ("interval", .integer(300))])
            ])))
            fields.append(("rules", .array([.text("MATCH,节点选择")])))
        }
        return "# WhiteSwitcher · Offline VLESS to Mihomo converter\n" + YAMLWriter.encode(.object(fields))
    }

    private static func parseLink(_ raw: String) throws -> ([(String, YAMLValue)], String, [String]) {
        guard !raw.unicodeScalars.contains(where: { $0.value < 32 || $0.value == 127 }) else {
            throw ConversionError("链接包含控制字符")
        }
        guard !hasInvalidPercent(raw), let uri = URLComponents(string: raw),
              uri.scheme?.lowercased() == "vless" else {
            throw ConversionError("仅支持格式正确的 vless:// 链接")
        }
        guard uri.password == nil, let user = uri.user,
              let uuid = normalizedUUID(user) else {
            throw ConversionError("UUID 格式无效，或用户信息格式错误")
        }
        guard let host = uri.host, !host.isEmpty,
              !host.unicodeScalars.contains(where: { $0.value < 32 || $0.value == 127 }),
              !host.contains(where: { $0.isWhitespace }) else {
            throw ConversionError("服务器地址缺失或无效")
        }
        guard let port = uri.port, (1...65535).contains(port) else {
            throw ConversionError("端口必须在 1–65535 之间")
        }
        var params: [String: String] = [:]
        if let query = uri.percentEncodedQuery, !query.isEmpty {
            let pairs = query.split(separator: "&", omittingEmptySubsequences: false)
            guard pairs.count <= 100 else { throw ConversionError("查询参数过多") }
            for pair in pairs {
                let parts = pair.split(separator: "=", maxSplits: 1, omittingEmptySubsequences: false)
                func decode(_ value: Substring) throws -> String {
                    guard let decoded = String(value).replacingOccurrences(of: "+", with: " ").removingPercentEncoding else {
                        throw ConversionError("查询参数百分号编码有误")
                    }
                    return decoded
                }
                let key = try decode(parts[0]).lowercased()
                let value = try decode(parts.count > 1 ? parts[1] : "")
                params[key] = value // Match Python parse_qsl last duplicate wins.
            }
        }
        func first(_ keys: String...) -> String {
            for key in keys where params[key] != nil { return params[key]! }
            return ""
        }
        func csv(_ value: String) -> [YAMLValue] {
            value.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }
                .filter { !$0.isEmpty }.map(YAMLValue.text)
        }
        var warnings = Set(params.keys.filter { !known.contains($0) }
            .sorted().map { "未识别参数 \($0)，已忽略" })
        for key in ["spx", "seed"] where !(params[key] ?? "").isEmpty {
            warnings.insert("\(key) 扩展参数未映射到 Mihomo")
        }
        let transport = first("type").lowercased().isEmpty ? "tcp" : first("type").lowercased()
        guard supported.contains(transport) else { throw ConversionError("暂不支持传输类型 \(transport)") }
        guard ["", "none"].contains(first("headertype")) else {
            throw ConversionError("暂不支持自定义 TCP headerType")
        }
        guard first("extra").isEmpty else { throw ConversionError("XHTTP extra 等扩展配置无法可靠转换") }

        let publicKey = first("pbk", "publickey")
        var security = first("security").lowercased()
        if security.isEmpty {
            security = !publicKey.isEmpty ? "reality" : (first("sni", "servername").isEmpty ? "none" : "tls")
        }
        guard ["none", "tls", "reality"].contains(security) else {
            throw ConversionError("暂不支持 security=\(security)")
        }
        guard !(security == "reality" && publicKey.isEmpty) else { throw ConversionError("Reality 缺少 pbk 公钥") }
        guard publicKey.isEmpty || security == "reality" else {
            throw ConversionError("存在 Reality 公钥，但 security 不是 reality")
        }
        let flow = first("flow")
        guard security != "none" || flow.isEmpty else { throw ConversionError("flow 要求 TLS/Reality") }
        guard flow.isEmpty || flow == "xtls-rprx-vision" else { throw ConversionError("不支持的 flow：\(flow)") }

        let rawName = (uri.fragment ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        let cleaned = rawName.unicodeScalars.map { scalar -> String in
            scalar.value < 32 || scalar.value == 127 ? " " : String(scalar)
        }.joined().trimmingCharacters(in: .whitespacesAndNewlines)
        let fallbackName = "\(host):\(port)"
        let name = String((cleaned.isEmpty ? fallbackName : cleaned).prefix(90))
        var fields: [(String, YAMLValue)] = [
            ("name", .text(name)), ("type", .text("vless")),
            ("server", .text(host)), ("port", .integer(port)),
            ("uuid", .text(uuid)), ("udp", .boolean(try parseBool(params["udp"] ?? "true", "udp")))
        ]
        if security != "none" { fields.append(("tls", .boolean(true))) }
        if !first("sni", "servername").isEmpty { fields.append(("servername", .text(first("sni", "servername")))) }
        if !first("fp", "fingerprint").isEmpty { fields.append(("client-fingerprint", .text(first("fp", "fingerprint")))) }
        if !first("alpn").isEmpty { fields.append(("alpn", .array(csv(first("alpn"))))) }
        if !flow.isEmpty { fields.append(("flow", .text(flow))) }
        let encryption = first("encryption")
        if !encryption.isEmpty && encryption.lowercased() != "none" { fields.append(("encryption", .text(encryption))) }
        let packetEncoding = first("packetencoding")
        if !packetEncoding.isEmpty {
            guard ["xudp", "packetaddr"].contains(packetEncoding) else {
                throw ConversionError("packetEncoding 只能为 xudp 或 packetaddr")
            }
            fields.append(("packet-encoding", .text(packetEncoding)))
        }
        for name in ["allowinsecure", "insecure"] where params[name] != nil {
            fields.append(("skip-cert-verify", .boolean(try parseBool(params[name]!, name))))
            break
        }
        if security == "reality" {
            var opts: [(String, YAMLValue)] = [("public-key", .text(publicKey))]
            let shortID = first("sid", "shortid")
            if !shortID.isEmpty { opts.append(("short-id", .text(shortID))) }
            fields.append(("reality-opts", .object(opts)))
        }
        let path = first("path").isEmpty ? "/" : first("path")
        let transportHost = first("host")
        switch transport {
        case "ws":
            var opts: [(String, YAMLValue)] = [("path", .text(path))]
            if !transportHost.isEmpty { opts.append(("headers", .object([("Host", .text(transportHost))]))) }
            let earlyData = first("ed", "earlydata")
            if !earlyData.isEmpty {
                guard let size = Int(earlyData), (0...Int(Int32.max)).contains(size) else {
                    throw ConversionError("Early Data 必须是非负整数")
                }
                opts.append(("max-early-data", .integer(size)))
                opts.append(("early-data-header-name", .text(first("eh", "earlydataheadername").isEmpty ? "Sec-WebSocket-Protocol" : first("eh", "earlydataheadername"))))
            }
            fields += [("network", .text("ws")), ("ws-opts", .object(opts))]
        case "grpc":
            fields += [("network", .text("grpc")),
                       ("grpc-opts", .object([("grpc-service-name", .text(first("servicename")))]))]
            if params["authority"] != nil { warnings.insert("gRPC authority 没有等价的通用 Mihomo 字段，已忽略") }
        case "h2":
            var opts: [(String, YAMLValue)] = [("path", .text(path))]
            if !transportHost.isEmpty { opts.append(("host", .array(csv(transportHost)))) }
            fields += [("network", .text("h2")), ("h2-opts", .object(opts))]
        case "http":
            var opts: [(String, YAMLValue)] = [
                ("method", .text(first("method").isEmpty ? "GET" : first("method"))),
                ("path", .array([.text(path)]))
            ]
            if !transportHost.isEmpty { opts.append(("headers", .object([("Host", .array(csv(transportHost)))]))) }
            fields += [("network", .text("http")), ("http-opts", .object(opts))]
        case "xhttp":
            var opts: [(String, YAMLValue)] = [("path", .text(path))]
            if !transportHost.isEmpty { opts.append(("host", .text(transportHost))) }
            let mode = first("mode")
            if !mode.isEmpty {
                guard ["auto", "stream-one", "stream-up", "packet-up"].contains(mode) else {
                    throw ConversionError("未知 XHTTP mode=\(mode)")
                }
                opts.append(("mode", .text(mode)))
            }
            fields += [("network", .text("xhttp")), ("xhttp-opts", .object(opts))]
        default: break
        }
        return (fields, name, warnings.sorted())
    }

    private static func parseBool(_ raw: String, _ label: String) throws -> Bool {
        switch raw.lowercased() {
        case "1", "true", "yes": return true
        case "0", "false", "no": return false
        default: throw ConversionError("\(label) 必须是 true/false 或 1/0")
        }
    }

    private static func hasInvalidPercent(_ value: String) -> Bool {
        let chars = Array(value.utf8)
        for (i, byte) in chars.enumerated() where byte == 37 {
            guard i + 2 < chars.count,
                  (chars[i + 1] >= 48 && chars[i + 1] <= 57 || chars[i + 1] >= 65 && chars[i + 1] <= 70 || chars[i + 1] >= 97 && chars[i + 1] <= 102),
                  (chars[i + 2] >= 48 && chars[i + 2] <= 57 || chars[i + 2] >= 65 && chars[i + 2] <= 70 || chars[i + 2] >= 97 && chars[i + 2] <= 102) else { return true }
        }
        return false
    }

    private static func normalizedUUID(_ user: String) -> String? {
        if let uuid = UUID(uuidString: user) { return uuid.uuidString.lowercased() }
        let compact = user.replacingOccurrences(of: "-", with: "")
        guard compact.count == 32 && compact.allSatisfy({ $0.isHexDigit }) else { return nil }
        let chars = Array(compact)
        let dashed = String(chars[0..<8]) + "-" + String(chars[8..<12]) + "-" + String(chars[12..<16]) + "-" + String(chars[16..<20]) + "-" + String(chars[20..<32])
        return UUID(uuidString: dashed)?.uuidString.lowercased()
    }
}

public indirect enum YAMLValue {
    case text(String)
    case integer(Int)
    case boolean(Bool)
    case object([(String, YAMLValue)])
    case array([YAMLValue])
}

public enum YAMLWriter {
    public static func encode(_ value: YAMLValue) -> String { render(value, indent: 0) }

    private static func scalar(_ value: YAMLValue) -> String? {
        switch value {
        case .text(let text):
            // JSON strings are valid YAML 1.2 strings; quoting avoids accidental booleans,
            // aliases, directives, delimiters or multiline injection from link names.
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.withoutEscapingSlashes]
            let data = try! encoder.encode(text)
            return String(decoding: data, as: UTF8.self)
        case .integer(let number): return String(number)
        case .boolean(let bool): return bool ? "true" : "false"
        default: return nil
        }
    }

    private static func render(_ value: YAMLValue, indent: Int) -> String {
        let pad = String(repeating: " ", count: indent)
        switch value {
        case .object(let pairs):
            if pairs.isEmpty { return pad + "{}\n" }
            return pairs.map { key, item -> String in
                if let scalar = scalar(item) { return "\(pad)\(key): \(scalar)\n" }
                switch item {
                case .array(let list) where list.isEmpty: return "\(pad)\(key): []\n"
                case .object(let nested) where nested.isEmpty: return "\(pad)\(key): {}\n"
                default: return "\(pad)\(key):\n" + render(item, indent: indent + 2)
                }
            }.joined()
        case .array(let list):
            if list.isEmpty { return pad + "[]\n" }
            return list.map { item -> String in
                if let scalar = scalar(item) { return "\(pad)- \(scalar)\n" }
                if case .object(let pairs) = item, let first = pairs.first {
                    let firstLine = render(.object([first]), indent: 0).trimmingCharacters(in: .newlines)
                    let rest = Array(pairs.dropFirst())
                    return "\(pad)- \(firstLine)\n" + (rest.isEmpty ? "" : render(.object(rest), indent: indent + 2))
                }
                return "\(pad)-\n" + render(item, indent: indent + 2)
            }.joined()
        default: return pad + (scalar(value) ?? "null") + "\n"
        }
    }
}
