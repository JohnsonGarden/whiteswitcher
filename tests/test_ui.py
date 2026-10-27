"""Optional GUI smoke tests for a real or virtual Tk desktop."""
import os
import unittest

from whiteswitcher.app import PALETTES


class ThemeTokenTests(unittest.TestCase):
    def test_palettes_are_grayscale(self):
        for mode, palette in PALETTES.items():
            with self.subTest(theme=mode):
                for role, hex_color in palette.items():
                    with self.subTest(role=role):
                        value = hex_color.removeprefix("#")
                        self.assertEqual(len(value), 6)
                        rgb = [int(value[i:i+2], 16) for i in (0, 2, 4)]
                        # Neutral/Zinc grays may have a subtle cool undertone.
                        self.assertLessEqual(max(rgb) - min(rgb), 10)


@unittest.skipUnless(os.environ.get("WHITESWITCHER_GUI_TEST") == "1",
                     "GUI smoke test requires a real or virtual display")
class GuiSmokeTests(unittest.TestCase):
    def test_theme_switch_preserves_input_preview_and_mode(self):
        from whiteswitcher.app import WhiteSwitcherApp
        app = WhiteSwitcherApp()
        try:
            example = "vless://a05b7cb0-7d5d-4c33-b812-4bd0f1fe73bf@example.com:443?security=tls#Example"
            app.input_box.insert("1.0", example)
            self.assertTrue(app._generate())
            app.root.update()
            self.assertIn("name: Example", app.current_yaml)
            rendered = app.current_yaml
            app._toggle_theme()
            app.root.update()
            self.assertEqual(app.theme, "dark")
            self.assertEqual(app.current_yaml, rendered)
            self.assertEqual(app.input_box.get("1.0", "end-1c"), example)
            self.assertEqual(app.output_box.get("1.0", "end-1c"), rendered)
            app.mode.set("nodes")
            self.assertTrue(app._generate())
            self.assertNotIn("proxy-groups:", app.current_yaml)
            app._toggle_theme()
            app.root.update()
            self.assertEqual(app.mode.get(), "nodes")
            self.assertEqual(app.theme, "light")
        finally:
            app.root.destroy()

    def test_errors_shown_without_exporting_invalid_yaml(self):
        from whiteswitcher.app import WhiteSwitcherApp
        app = WhiteSwitcherApp()
        try:
            app.input_box.insert("1.0", "vless://wrong@host:443")
            self.assertFalse(app._generate())
            app.root.update()
            self.assertEqual(app.current_yaml, "")
            self.assertTrue(app.issue_box.get("1.0", "end-1c"))
        finally:
            app.root.destroy()


if __name__ == "__main__":
    unittest.main()
