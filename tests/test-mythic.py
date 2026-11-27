#!/usr/bin/env python3
"""
tests/test-mythic.py
The mythic style onboarding: the mythic kit in headless Chromium (tests/mythic-kit/index.html:
every builder, seek determinism, entrance states, identical geometry on reload), the token
contract shared by the four mythic style systems, the kit's determinism lint, and the
scripts/myth-sources.py parsers on canned API responses (no network).

    python tests/test-mythic.py

The browser part skips without Python Playwright. On the render host run it through
`scripts/session-guard.py run render -- python tests/test-mythic.py`.
"""

import functools
import http.server
import importlib.util
import re
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "src" / "studio" / "kits" / "mythic" / "mythic.js"
KIT_FILES = [KIT, ROOT / "src" / "studio" / "kits" / "mythic" / "figures.js", ROOT / "src" / "studio" / "kits" / "mythic" / "figures-human.js"]
MYTHIC_STYLES = ["mythic-paper", "shadow-lantern", "painted-folio", "carved-relief"]
TOKEN_CONTRACT = [
    "paper", "paper-2", "ink", "ink-2", "rule", "accent", "accent-2", "accent-3", "gold", "gold-light", "lamp",
    "malachite", "sky", "lotus", "saffron", "peacock", "night", "shadow", "caption-ink", "caption-bg", "caption-hl",
    "leather-red", "leather-ochre", "leather-green", "leather-blue",
]

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

spec = importlib.util.spec_from_file_location("myth_sources", ROOT / "scripts" / "myth-sources.py")
ms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ms)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class TestStyleContract(unittest.TestCase):
    def test_every_mythic_style_defines_the_kit_tokens(self):
        for sid in MYTHIC_STYLES:
            css = (ROOT / "src" / "studio" / "styles" / f"{sid}.css").read_text(encoding="utf-8")
            defined = set(re.findall(r"--c-([a-z0-9-]+)\s*:", css))
            self.assertEqual(sorted(set(TOKEN_CONTRACT) - defined), [], sid)

    def test_kit_has_no_nondeterministic_calls(self):
        for path in KIT_FILES:
            src = path.read_text(encoding="utf-8")
            for pattern in (r"Math\.random\s*\(", r"Date\.now\s*\(|new\s+Date\s*\(|performance\.now\s*\(",
                            r"requestAnimationFrame\s*\(|setInterval\s*\(|setTimeout\s*\(", r"repeat\s*:\s*-1", r"\.play\s*\("):
                self.assertIsNone(re.search(pattern, src), f"{path.name}: {pattern}")


@unittest.skipUnless(HAS_PLAYWRIGHT, "playwright is not installed")
class TestMythicKitInBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(QuietHandler, directory=str(ROOT))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}/tests/mythic-kit/index.html"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def load(self):
        errors = []
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 720, "height": 1280})
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
            page.goto(self.url, wait_until="load", timeout=30000)
            page.wait_for_function("() => window.__mythicResults !== undefined", timeout=30000)
            out = page.evaluate("() => window.__mythicResults")
            browser.close()
        return out, errors

    def test_kit_builds_seeks_and_is_deterministic(self):
        first, errors = self.load()
        self.assertEqual(errors, [])
        failed = [f"{r['name']}: {r['detail']}" for r in first["results"] if not r["ok"]]
        self.assertEqual(failed, [])
        self.assertGreaterEqual(len(first["results"]), 16)
        second, _ = self.load()
        self.assertEqual(first["geometry"], second["geometry"], "seeded geometry changed between page loads")


class TestMythSourcesParsers(unittest.TestCase):
    def test_cma_keeps_cc0_with_images_only(self):
        payload = {"data": [
            {"id": 1, "accession_number": "2022.42", "share_license_status": "CC0", "title": "Lekythos: Athena",
             "creation_date": "500–485 BCE", "culture": ["Greek, Attic"], "url": "https://clevelandart.org/art/2022.42",
             "creators": [{"description": "Athena Painter (Greek)"}], "images": {"web": {"url": "https://x/2022.42_web.jpg"}}},
            {"id": 2, "share_license_status": "Copyrighted", "title": "Modern", "images": {"web": {"url": "https://x/b.jpg"}}},
            {"id": 3, "share_license_status": "CC0", "title": "No image", "images": None},
        ]}
        recs = ms.parse_cma(payload)
        self.assertEqual([r["id"] for r in recs], ["cma-2022.42"])
        self.assertEqual(recs[0]["license"], "CC0")
        self.assertIn("The Cleveland Museum of Art", recs[0]["attribution"])
        self.assertEqual(recs[0]["culture"], "Greek, Attic")

    def test_met_requires_public_domain_and_an_image(self):
        ok = {"objectID": 38158, "isPublicDomain": True, "primaryImageSmall": "https://images/x.jpg", "title": "Shiva",
              "culture": "", "period": "Pre-Angkor period", "objectDate": "mid-7th century", "objectURL": "https://met/38158"}
        self.assertEqual(ms.parse_met_object(ok)["culture"], "Pre-Angkor period")
        self.assertIsNone(ms.parse_met_object({**ok, "isPublicDomain": False}))
        self.assertIsNone(ms.parse_met_object({**ok, "primaryImageSmall": "", "primaryImage": ""}))

    def test_commons_drops_share_alike_scanned_books_and_strips_html(self):
        payload = {"query": {"pages": [
            {"pageid": 10, "index": 1, "title": "File:Krishna Govardhan.jpg", "imageinfo": [{
                "url": "https://u/full.jpg", "thumburl": "https://u/1600.jpg", "descriptionurl": "https://commons/File:K", "mime": "image/jpeg",
                "extmetadata": {"LicenseShortName": {"value": "Public domain"}, "Artist": {"value": "<a href='x'>Miskin</a>"},
                                "DateTimeOriginal": {"value": "ca. 1590<div style=\"display: none;\">date QS:P571</div>"}}}]},
            {"pageid": 11, "index": 2, "title": "File:Photo.jpg", "imageinfo": [{
                "url": "https://u/p.jpg", "mime": "image/jpeg", "extmetadata": {"LicenseShortName": {"value": "CC BY-SA 4.0"}}}]},
            {"pageid": 12, "index": 3, "title": "File:The Ramayana Canto 5.djvu", "imageinfo": [{
                "url": "https://u/r.djvu", "mime": "image/vnd.djvu", "extmetadata": {"LicenseShortName": {"value": "Public domain"}}}]},
        ]}}
        recs = ms.parse_commons(payload)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["url"], "https://u/1600.jpg")
        self.assertEqual(recs[0]["creator"], "Miskin")
        self.assertEqual(recs[0]["date"], "ca. 1590")
        self.assertEqual(recs[0]["title"], "Krishna Govardhan")

    def test_met_search_skips_objects_that_no_longer_resolve(self):
        import urllib.error

        def fake(url):
            if "/search" in url:
                return {"objectIDs": [1, 2]}
            if url.endswith("/1"):
                raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
            return {"objectID": 2, "isPublicDomain": True, "primaryImageSmall": "https://i/2.jpg", "title": "Odin", "objectURL": "u"}
        self.assertEqual([r["id"] for r in ms.search_met("Odin", 2, fetch=fake)], ["met-2"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
