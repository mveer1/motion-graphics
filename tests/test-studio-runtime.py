#!/usr/bin/env python3
"""
tests/test-studio-runtime.py
Runs the studio runtime self-test page (tests/studio-runtime/index.html) in headless Chromium
via Playwright and asserts every in-page check passed. Skips when Playwright or the pinned GSAP
CDN script is unavailable.
"""

import functools
import http.server
import json
import threading
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(root: Path):
    handler = functools.partial(QuietHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


@unittest.skipUnless(HAS_PLAYWRIGHT, "playwright is not installed")
class TestStudioRuntime(unittest.TestCase):

    def run_page(self, page_path: str, viewport: dict, min_checks: int) -> None:
        server = serve(REPO_ROOT)
        errors = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport=viewport)
                page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
                page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
                url = f"http://127.0.0.1:{server.server_address[1]}/{page_path}"
                try:
                    page.goto(url, wait_until="load", timeout=30000)
                except Exception as exc:  # network or CDN unavailable
                    browser.close()
                    self.skipTest(f"could not load test page: {exc}")
                if not page.evaluate("() => !!window.gsap"):
                    browser.close()
                    self.skipTest("GSAP CDN script unavailable (offline?)")
                page.wait_for_function("() => window.__studioTestResults !== undefined", timeout=20000)
                results = page.evaluate("() => window.__studioTestResults")
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

        failed = [r for r in results if not r["ok"]]
        self.assertFalse(errors, "Browser errors:\n" + "\n".join(errors))
        self.assertGreaterEqual(len(results), min_checks, f"expected the full check list, got {len(results)}")
        self.assertFalse(failed, "Failed runtime checks:\n" + json.dumps(failed, indent=2))

    def test_runtime_self_checks(self):
        self.run_page("tests/studio-runtime/index.html", {"width": 720, "height": 1280}, 30)

    def test_reference_technique_checks(self):
        self.run_page("tests/studio-runtime/reference-techniques.html", {"width": 1280, "height": 720}, 40)


if __name__ == "__main__":
    unittest.main()
