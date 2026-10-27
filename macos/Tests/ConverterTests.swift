import XCTest
@testable import WhiteSwitcherCore

final class ConverterTests: XCTestCase {
    let uuid = "11111111-2222-4333-8444-555555555555"

    func testRealityVisionFullExport() throws {
        let link = "vless://\(uuid)@example.org:443?security=reality&pbk=publickey&sid=abcd&sni=www.example.com&fp=chrome&flow=xtls-rprx-vision&type=tcp#Tokyo"
        let result = WhiteSwitcherConverter.parse(link)
        XCTAssertEqual(result.proxies.count, 1)
        XCTAssertTrue(result.errors.isEmpty)
        let yaml = try WhiteSwitcherConverter.export(result, mode: .full)
        XCTAssertTrue(yaml.contains("reality-opts:"))
        XCTAssertTrue(yaml.contains("public-key: \"publickey\""))
        XCTAssertTrue(yaml.contains("client-fingerprint: \"chrome\""))
        XCTAssertTrue(yaml.contains("flow: \"xtls-rprx-vision\""))
        XCTAssertTrue(yaml.contains("MATCH,节点选择"))
        XCTAssertTrue(yaml.contains("proxy-groups:"))
    }

    func testWebSocketAndEarlyData() throws {
        let link = "vless://\(uuid)@ws.example:8443?security=tls&type=ws&host=cdn.example&path=%2Fchat%3Fid%3D1&ed=2048&eh=Sec-WebSocket-Protocol#%E8%8A%82%E7%82%B9"
        let result = WhiteSwitcherConverter.parse(link)
        XCTAssertTrue(result.errors.isEmpty)
        let yaml = try WhiteSwitcherConverter.export(result, mode: .nodes)
        XCTAssertTrue(yaml.contains("name: \"节点\""))
        XCTAssertTrue(yaml.contains("path: \"/chat?id=1\""))
        XCTAssertTrue(yaml.contains("max-early-data: 2048"))
        XCTAssertFalse(yaml.contains("proxy-groups:"))
    }

    func testGRPCXHTTPAndHTTPH2() throws {
        let links = [
            "vless://\(uuid)@a.com:443?type=grpc&serviceName=svc&authority=abc#grpc",
            "vless://\(uuid)@a.com:443?type=xhttp&path=%2Fapi&mode=stream-up&host=front.com#xhttp",
            "vless://\(uuid)@a.com:443?type=http&method=POST&host=front.com#http",
            "vless://\(uuid)@a.com:443?type=h2&host=front.com%2Cbackup.com#h2"
        ].joined(separator: "\n")
        let result = WhiteSwitcherConverter.parse(links)
        XCTAssertEqual(result.proxies.count, 4)
        XCTAssertEqual(result.warnings.count, 1)
        XCTAssertTrue(result.errors.isEmpty)
        let yaml = try WhiteSwitcherConverter.export(result, mode: .nodes)
        for key in ["grpc-opts:", "xhttp-opts:", "http-opts:", "h2-opts:"] { XCTAssertTrue(yaml.contains(key)) }
    }

    func testBatchDuplicatesAndSameName() throws {
        let one = "vless://\(uuid)@a.com:443#Same"
        let two = "vless://\(uuid)@b.com:443#Same"
        let result = WhiteSwitcherConverter.parse(one + "\n" + one + "\n" + two)
        XCTAssertEqual(result.total, 3)
        XCTAssertEqual(result.proxies.count, 2)
        XCTAssertEqual(result.warnings.count, 1)
        XCTAssertTrue(try WhiteSwitcherConverter.export(result, mode: .nodes).contains("Same (2)"))
    }

    func testInvalidLinksAndNonSupportedOptions() {
        let links = [
            "vless://not-a-uuid@example.org:443",
            "vless://\(uuid)@example.org:65536",
            "vless://\(uuid)@example.org:443?security=reality",
            "vless://\(uuid)@example.org:443?type=kcp",
            "vless://\(uuid)@example.org:443?extra=%7B%7D",
            "vless://\(uuid)@example.org:443?flow=xtls-rprx-vision&security=none",
            "vless://\(uuid)@example.org:443?udp=maybe",
            "vless://\(uuid)@example.org:443?packetEncoding=unknown",
            "vless://\(uuid)@example.org:443?type=ws&ed=foo",
            "vless://\(uuid)@example.org:443?bad=%ZZ"
        ].joined(separator: "\n")
        let result = WhiteSwitcherConverter.parse(links)
        XCTAssertEqual(result.proxies.count, 0)
        XCTAssertEqual(result.errors.count, 10)
        XCTAssertThrowsError(try WhiteSwitcherConverter.export(result, mode: .full))
    }

    func testSafeQuotingInjectionAndUnknownParams() throws {
        let link = "vless://\(uuid)@example.org:443?token=secret-value#true%3A%20%5B1%2C2%5D"
        let result = WhiteSwitcherConverter.parse(link)
        let yaml = try WhiteSwitcherConverter.export(result, mode: .nodes)
        XCTAssertTrue(yaml.contains("name: \"true: [1,2]\""))
        XCTAssertTrue(result.issues[0].message.contains("token"))
        XCTAssertFalse(result.issues[0].message.contains("secret-value"))
    }

    func testCompactUUIDAndIPv6() throws {
        let result = WhiteSwitcherConverter.parse("vless://11111111222243338444555555555555@[2001:db8::1]:443?security=tls#IPv6")
        XCTAssertTrue(result.errors.isEmpty, "\(result.errors.map(\.message))")
        let yaml = try WhiteSwitcherConverter.export(result, mode: .nodes)
        XCTAssertTrue(yaml.contains("uuid: \"11111111-2222-4333-8444-555555555555\""))
        XCTAssertTrue(yaml.contains("server:"))
    }

    func testWarningsForUnsupportedRealityExtra() {
        let result = WhiteSwitcherConverter.parse("vless://\(uuid)@example.org:443?security=reality&pbk=key&spx=%2Fsomepath")
        XCTAssertEqual(result.proxies.count, 1)
        XCTAssertTrue(result.warnings.contains(where: { $0.message.contains("spx") }))
    }
}
