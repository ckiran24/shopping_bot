"""Opt-in live browser checks against the public SauceDemo test site."""

import json
import os
from pathlib import Path
import sys
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import bot
from playwright.sync_api import sync_playwright


class LiveCheckoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        options = {"headless": True}
        if os.environ.get("SAUCE_BROWSER_PATH"):
            options["executable_path"] = os.environ["SAUCE_BROWSER_PATH"]
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        if proxy:
            options["proxy"] = {"server": proxy}
        cls.browser = cls.playwright.chromium.launch(**options)
        cls.password = os.environ.get("SAUCE_PASSWORD")
        if not cls.password:
            page = cls.browser.new_page()
            try:
                page.goto(bot.SITE)
                panel = page.locator(".login_password")
                panel.wait_for()
                lines = [line.strip() for line in panel.inner_text().splitlines()
                         if line.strip() and "Password for all users:" not in line]
                if len(lines) != 1:
                    raise ValueError("Unexpected public password panel; no credential guessed")
                cls.password = lines[0]
            finally:
                page.close()
        cls.output = ROOT / "outputs" / "live_checks"
        cls.output.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def run_input(self, name, items):
        directory = self.output / name
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "input.json"
        path.write_text(json.dumps({"items": items,
            "customer": {"first_name": "Ada", "last_name": "Lovelace", "zip": "94105"}}))
        command = [sys.executable, str(ROOT / "bot.py"), "--input", str(path), "--output-dir", str(directory)]
        if os.environ.get("SAUCE_BROWSER_PATH"):
            command += ["--browser-path", os.environ["SAUCE_BROWSER_PATH"]]
        environment = dict(os.environ, SAUCE_USERNAME="standard_user", SAUCE_PASSWORD=self.password)
        process = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=180)
        code = process.returncode
        return code, json.loads((directory / "result.json").read_text()), directory

    def test_case_insensitive_matching(self):
        code, result, directory = self.run_input("case_insensitive",
            ["sauce labs backpack", "SAUCE LABS ONESIE", "Sauce Labs Water Bottle"])
        self.assertEqual(code, 0, result["error"])
        self.assertEqual(result["missing_items"], ["Sauce Labs Water Bottle"])
        self.assertEqual(result["order_totals"]["item_total"], 37.98)
        self.assertTrue((directory / result["confirmation_file"]).read_bytes().startswith(b"%PDF"))

    def test_all_missing_fails_without_order(self):
        code, result, directory = self.run_input("all_missing", ["Unknown A", "Unknown B"])
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["missing_items"], ["Unknown A", "Unknown B"])
        self.assertIn("no order placed", result["error"])
        self.assertIsNone(result["order_totals"])
        self.assertFalse((directory / "confirmation.pdf").exists())
        self.assertEqual(len(json.loads((directory / "products.json").read_text())), 6)

    def test_mismatch_stops_before_finish(self):
        page = self.browser.new_page()
        directory = self.output / "injected_mismatch"
        directory.mkdir(parents=True, exist_ok=True)
        result = {"missing_items": [], "purchased_items": []}
        # Deliberately change only this test page's displayed subtotal. This is
        # fault injection, not an observed failure of the public website.
        page.add_init_script("""
            const observer = new MutationObserver(() => {
                const subtotal = document.querySelector('[data-test="subtotal-label"]');
                if (subtotal) {
                    subtotal.textContent = 'Item total: $0.01';
                    observer.disconnect();
                }
            });
            observer.observe(document, {childList: true, subtree: true});
        """)
        try:
            page.set_default_timeout(60000)
            bot.expect.set_options(timeout=60000)
            with self.assertRaisesRegex(ValueError, "Item total mismatch"):
                bot.shop(page, ["Sauce Labs Backpack"],
                    {"first_name": "Ada", "last_name": "Lovelace", "zip": "94105"},
                    "standard_user", self.password, directory, result)
            self.assertTrue(page.url.endswith("checkout-step-two.html"))
            self.assertTrue(page.locator('[data-test="finish"]').is_visible())
            self.assertFalse((directory / "confirmation.pdf").exists())
        finally:
            page.close()


if __name__ == "__main__":
    unittest.main()
