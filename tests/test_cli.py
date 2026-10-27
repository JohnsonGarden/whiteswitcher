import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

UUID = "a05b7cb0-7d5d-4c33-b812-4bd0f1fe73bf"


class CliTests(unittest.TestCase):
    def test_cli_export(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            target = Path(root) / "output.yaml"
            source.write_text(f"vless://{UUID}@my.host:443?security=tls#test", encoding="utf-8")
            process = subprocess.run([sys.executable, "-m", "whiteswitcher", "-i", str(source), "-o", str(target)],
                                     capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(yaml.safe_load(target.read_text(encoding="utf-8"))["proxies"][0]["name"], "test")

    def test_cli_partial_errors_returns_2_with_valid_yaml(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            target = Path(root) / "output.yaml"
            source.write_text(f"bad://link\nvless://{UUID}@my.host:443#test", encoding="utf-8")
            process = subprocess.run([sys.executable, "-m", "whiteswitcher", "-i", str(source), "-o", str(target),
                                      "--mode", "nodes"], capture_output=True, text=True)
            self.assertEqual(process.returncode, 2)
            self.assertTrue(target.exists())
            self.assertEqual(len(yaml.safe_load(target.read_text(encoding="utf-8"))["proxies"]), 1)


if __name__ == "__main__":
    unittest.main()
