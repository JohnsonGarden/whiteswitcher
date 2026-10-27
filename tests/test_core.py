import unittest
from urllib.parse import quote

import yaml

from whiteswitcher.core import LinkError, build_config, export_yaml, parse_links, parse_vless_link

UUID = "a05b7cb0-7d5d-4c33-b812-4bd0f1fe73bf"
BASE = f"vless://{UUID}@edge.example.com:443"


class ParsingTests(unittest.TestCase):
    def test_reality_vision_mapping(self):
        link = (BASE + "?encryption=none&security=reality&sni=www.microsoft.com&fp=chrome"
                "&pbk=publicKey123&sid=a1b2&flow=xtls-rprx-vision&type=tcp#US%20Reality")
        proxy, warnings = parse_vless_link(link)
        self.assertFalse(warnings)
        self.assertEqual(proxy["name"], "US Reality")
        self.assertEqual(proxy["server"], "edge.example.com")
        self.assertEqual(proxy["client-fingerprint"], "chrome")
        self.assertEqual(proxy["reality-opts"], {"public-key": "publicKey123", "short-id": "a1b2"})
        self.assertEqual(proxy["flow"], "xtls-rprx-vision")
        self.assertNotIn("network", proxy)
        self.assertNotIn("encryption", proxy)

    def test_websocket_tls_path_and_host(self):
        path = quote("/connection?token=abc", safe="")
        proxy, _ = parse_vless_link(BASE + f"?type=ws&security=tls&host=cdn.example.org&path={path}#HK")
        self.assertEqual(proxy["ws-opts"], {"path": "/connection?token=abc", "headers": {"Host": "cdn.example.org"}})
        self.assertEqual(proxy["network"], "ws")
        self.assertTrue(proxy["tls"])

    def test_ws_early_data(self):
        proxy, _ = parse_vless_link(BASE + "?type=ws&ed=2048&eh=X-Header")
        self.assertEqual(proxy["ws-opts"]["max-early-data"], 2048)
        self.assertEqual(proxy["ws-opts"]["early-data-header-name"], "X-Header")

    def test_grpc_http_h2_xhttp(self):
        grpc, _ = parse_vless_link(BASE + "?type=grpc&serviceName=my_service")
        self.assertEqual(grpc["grpc-opts"]["grpc-service-name"], "my_service")
        http, _ = parse_vless_link(BASE + "?type=http&path=%2Ffoo&host=a.com,b.com")
        self.assertEqual(http["http-opts"]["path"], ["/foo"])
        h2, _ = parse_vless_link(BASE + "?type=h2&host=cdn.org&path=%2Fh2")
        self.assertEqual(h2["h2-opts"]["host"], ["cdn.org"])
        xhttp, _ = parse_vless_link(BASE + "?type=xhttp&mode=stream-up&path=%2Fx&host=cdn.org")
        self.assertEqual(xhttp["xhttp-opts"], {"path": "/x", "host": "cdn.org", "mode": "stream-up"})

    def test_ipv6_unicode_name_and_yaml_safety(self):
        link = f"vless://{UUID}@[2001:db8::1]:2083?security=tls#%E8%8A%82%E7%82%B9%3A%20%23%201"
        proxy, _ = parse_vless_link(link)
        self.assertEqual(proxy["server"], "2001:db8::1")
        self.assertEqual(proxy["name"], "节点: # 1")
        loaded = yaml.safe_load(export_yaml([proxy]))
        self.assertEqual(loaded["proxies"][0]["name"], "节点: # 1")

    def test_batch_errors_duplicates_and_unique_names(self):
        data = "\n".join([BASE + "#Same", BASE + "#Same", BASE + "#Same%20", "bad://foo", BASE + "#Other"])
        result = parse_links(data)
        self.assertEqual(len(result.proxies), 3)
        self.assertEqual(result.proxies[1]["name"], "Same (2)")
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(result.total, 5)

    def test_no_links(self):
        self.assertEqual(parse_links("\n# description\n").proxies, [])
        with self.assertRaisesRegex(ValueError, "有效节点"):
            export_yaml([])

    def test_invalid_and_unsupported_links(self):
        cases = [
            "vless://bad@edge.example.com:443", BASE.replace(":443", ":0"),
            BASE + "?security=reality", BASE + "?type=kcp", BASE + "?security=none&flow=xtls-rprx-vision",
            BASE + "?type=tcp&headerType=http", BASE + "?type=xhttp&extra=%7B%7D",
            BASE + "?allowInsecure=maybe", BASE + "?type=ws&ed=-3", BASE + "?path=%XX",
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(LinkError):
                parse_vless_link(case)

    def test_extra_params_warns_without_echoing_secret(self):
        proxy, warnings = parse_vless_link(BASE + "?security=tls&customPassword=topsecret")
        self.assertEqual(proxy["type"], "vless")
        self.assertEqual(len(warnings), 1)
        self.assertNotIn("topsecret", warnings[0])

    def test_full_config_references_existing_groups(self):
        proxies = parse_links(BASE + "#A\n" + BASE + "#B").proxies
        config = yaml.safe_load(export_yaml(proxies))
        self.assertEqual(config["mixed-port"], 7890)
        self.assertEqual(len(config["proxy-groups"]), 2)
        self.assertEqual(config["proxy-groups"][1]["proxies"], ["A", "B"])
        self.assertEqual(config["rules"], ["MATCH,节点选择"])
        self.assertEqual(set(config["proxy-groups"][0]["proxies"]), {"自动选择", "A", "B", "DIRECT"})

    def test_nodes_mode_only_exports_proxies(self):
        proxies = parse_links(BASE).proxies
        self.assertEqual(list(yaml.safe_load(export_yaml(proxies, "nodes"))), ["proxies"])
        self.assertEqual(build_config(proxies, "nodes"), {"proxies": proxies})

    def test_encryption_alpn_udp_packet_encoding(self):
        proxy, _ = parse_vless_link(BASE + "?security=tls&encryption=custom.foo&alpn=h2%2Chttp%2F1.1&udp=0&packetEncoding=xudp")
        self.assertEqual(proxy["encryption"], "custom.foo")
        self.assertEqual(proxy["alpn"], ["h2", "http/1.1"])
        self.assertFalse(proxy["udp"])
        self.assertEqual(proxy["packet-encoding"], "xudp")


if __name__ == "__main__":
    unittest.main()
