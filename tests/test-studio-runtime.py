#!/usr/bin/env python3
"""
tests/test-studio-runtime.py
Runs the studio runtime self-test page (tests/studio-runtime/index.html) in headless Chromium
and asserts every in-page check passed. Uses Python Playwright when it is installed, otherwise
tests/studio-runtime/run-page.mjs (puppeteer-core and the Chrome cached by the hyperframes
install, which the render host always has). Skips when neither browser path or the pinned GSAP
CDN script is available. It starts a browser: on the render host run it through
`scripts/session-guard.py run render -- python tests/test-studio-runtime.py`.
"""

import functools
import http.server
import importlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import threading
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

NODE_RUNNER = REPO_ROOT / "tests" / "studio-runtime" / "run-page.mjs"
HAS_NODE = bool(shutil.which("node")) and bool(shutil.which("hyperframes"))


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(root: Path):
    handler = functools.partial(QuietHandler, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


@unittest.skipUnless(HAS_PLAYWRIGHT or HAS_NODE, "neither playwright nor node + hyperframes is installed")
class TestStudioRuntime(unittest.TestCase):

    def results_via_playwright(self, url: str, viewport: dict):
        errors = []
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport=viewport)
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
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
        return results, errors

    def results_via_node(self, url: str, viewport: dict):
        res = subprocess.run(["node", str(NODE_RUNNER), url, "--width", str(viewport["width"]), "--height", str(viewport["height"])],
                             capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        if res.returncode != 0:
            self.skipTest(f"could not run the page in Chrome: {res.stderr.strip()[-300:]}")
        out = json.loads(res.stdout)
        if not out["gsap"]:
            self.skipTest("GSAP CDN script unavailable (offline?)")
        return out["results"], out["errors"]

    def run_page(self, page_path: str, viewport: dict, min_checks: int) -> None:
        server = serve(REPO_ROOT)
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/{page_path}"
            run = self.results_via_playwright if HAS_PLAYWRIGHT else self.results_via_node
            results, errors = run(url, viewport)
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

    def test_film_helper_checks(self):
        # studio-film.js and kits/fitness/stations.js (runtime 1.15.0); loads the vendored GSAP, so it runs offline
        self.run_page("tests/studio-runtime/film-helpers.html", {"width": 720, "height": 1280}, 73)

    def test_backlog_technique_checks(self):
        # runtime 1.17.0: fx.flash, fx.containerTransform, type.scramble, type.strike/strikeCorrect, subject caption lane
        self.run_page("tests/studio-runtime/backlog-techniques.html", {"width": 1280, "height": 720}, 36)

    def test_explanation_device_checks(self):
        # runtime 1.18.0: studio-explain.js (equation, slider, tracePair, simulation, barRace, progression, space.tour,
        # fx.dip, copySlot, ui widgets, headline pair/build), including seek-order independence
        self.run_page("tests/studio-runtime/explain-devices.html", {"width": 1280, "height": 720}, 63)


FITNESS_CAPTION_PRESET = {"id": "clean-plate", "enter": "fade", "roles": {
    "hook": {"lane": "mid", "scale": 1.15}, "body": {"lane": "lower", "scale": 1}, "outro": {"lane": "lower", "scale": 1}}}
FITNESS_FORMATS = {"portrait": (720, 1280, 45), "landscape": (1280, 720, 150)}


def fitness_caption_cues(duration: float) -> list:
    """Hook, short, two-line and three-line cues spread over the film (k scales the 45 s portrait timings)."""
    k = duration / 45
    lines = [("hook", "How deep should you squat?"), ("body", "Sit between your heels, knees over toes."),
             ("body", "Push the floor away, keep the ribs down and squeeze the glutes hard at the very top."),
             ("body", "Keep the elbows by the ribs."), ("outro", "Depth is a choice, not a rule.")]
    starts = (0.5, 14.0, 22.0, 30.5, 41.5)
    return [{"start": round(s * k, 2), "end": round(s * k + 3.0, 2), "text": t, "role": r} for s, (r, t) in zip(starts, lines)]


def audit_fitness_template(fmt: str, overrides: dict = None, inject: str = None, step: float = 0.5) -> list:
    """Build templates/projects/fitness-explainer in one format exactly as `studio.py new` + `formats` would (runtime
    served from src/studio/, captions injected in memory, nothing written to disk), seek the whole film every `step`
    seconds and collect Studio.kit.fitness.audit() findings: card text off its band or on the gym rail, captions over
    Tibi. overrides: {'template': html, '/src/studio/<file>': js} serves other versions (negative controls)."""
    from playwright.sync_api import sync_playwright
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    studio = importlib.import_module("studio")
    o = overrides or {}
    width, height, duration = FITNESS_FORMATS[fmt]
    src = o.get("template") or (REPO_ROOT / "templates" / "projects" / "fitness-explainer" / "src" / "index.html").read_text(encoding="utf-8")
    entry = studio.format_entries({"formats": [{"id": fmt, "width": width, "height": height, "primary": True}]})[0]
    html = (studio.render_variant(src, entry, 30, duration)
            .replace("{{STYLE}}", "sinew-lab").replace("{{TITLE}}", "Squat depth").replace("_studio/", "/src/studio/"))
    # the film's own fonts, as `frame-review.py --fonts google` loads them: system fallbacks wrap text differently
    # (the coordinator's sheets showed an orphan that system fonts hid); offline, the audit runs on system fonts
    spec = importlib.util.spec_from_file_location("frame_review", REPO_ROOT / "scripts" / "frame-review.py")
    fr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fr)
    fams = ("Outfit", "Inter", "JetBrains Mono")
    css = "\n".join(c for c in (fr.google_font_css(f) for f in fams) if c)
    if css:
        loads = ",".join(f"document.fonts.load('{w} 1em \"{f}\"')" for f in fams for w in ("400", "600", "700", "800"))
        html = re.sub(r"<head([^>]*)>", lambda m: f"<head{m.group(1)}><style>{css}</style><script>Promise.all([{loads}]).catch(()=>{{}});</script>", html, count=1)
    else:
        print(f"[fitness template audit] {fmt}: Google fonts unavailable; auditing with system fonts", file=sys.stderr)
    caps = f"window.STUDIO_CAPTION_PRESET={json.dumps(FITNESS_CAPTION_PRESET)};window.STUDIO_CAPTIONS={json.dumps(fitness_caption_cues(duration))};"
    server = serve(REPO_ROOT)
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda m: errors.append(f"console.error: {m.text}") if m.type == "error" else None)
            def fulfil(body, ctype):
                return lambda route: route.fulfill(body=body, content_type=ctype)
            page.route(origin + "/zz-fitness-template/index.html", fulfil(html, "text/html"))
            page.route(origin + "/zz-fitness-template/captions.js", fulfil(caps, "application/javascript"))
            for path, body in o.items():
                if path.startswith("/"):
                    page.route(origin + path, fulfil(body, "application/javascript"))
            page.goto(origin + "/zz-fitness-template/index.html", wait_until="load", timeout=30000)
            try:
                page.wait_for_function("() => !!(window.__timelines && window.__timelines.root)", timeout=30000, polling=100)
            except Exception as exc:
                raise AssertionError(f"{fmt}: the template never registered its timeline: {errors or exc}") from None
            if inject:
                page.add_script_tag(content=inject)
            found = page.evaluate("""(step) => {
                const tl = window.__timelines.root, out = [], seen = {};
                for (let t = 0; t <= tl.duration() + 1e-6; t += step) {
                  tl.seek(t);
                  for (const f of Studio.kit.fitness.audit()) {
                    const key = f.kind + '|' + f.text;
                    if (!seen[key]) { seen[key] = 1; out.push(Object.assign({ t: +t.toFixed(2) }, f)); }
                  }
                }
                return out;
            }""", step)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    if errors:
        raise AssertionError("page errors: " + "; ".join(errors))
    return found


@unittest.skipUnless(HAS_PLAYWRIGHT, "playwright is not installed")
class TestFitnessTemplateLayout(unittest.TestCase):
    """The fitness-explainer template as a new film gets it, seeked every 0.5 s: no exercise-card text leaves its
    header band or sits on the gym rail, and no caption (a three-line one included) covers Tibi."""

    def test_portrait_and_landscape_frames_are_clean(self):
        for fmt in FITNESS_FORMATS:
            found = audit_fitness_template(fmt)
            self.assertEqual(found, [], f"{fmt}: " + json.dumps(found[:6], indent=1))

    def test_floor_audit_catches_card_text_shrunk_with_the_card(self):
        # negative control: before 1.16.0 the portrait card fit shrank chips, cues, tip and swaps to 16.6-18.1 px
        path = REPO_ROOT / "src" / "studio" / "kits" / "fitness" / "stations.js"
        src = path.read_text(encoding="utf-8")
        anchor = "function floored(n) { return 'max(var(--sn-read-floor),calc(var(--u)*' + n + '))'; }"
        self.assertEqual(src.count(anchor), 1, "negative-control anchor moved")
        unfloored = src.replace(anchor, "function floored(n) { return 'calc(var(--u)*' + n + ')'; }")
        found = audit_fitness_template("portrait", {"/src/studio/kits/fitness/stations.js": unfloored})
        self.assertTrue([f for f in found if f["kind"] == "card-below-floor"], json.dumps(found[:6], indent=1))


FILM_HELPER_FILES = ("src/studio/studio-film.js", "src/studio/kits/fitness/stations.js", "src/studio/studio-explain.js")
WORDS_FIXTURE = {
    "s1": [{"text": "Push", "start": 1.0, "end": 1.3}, {"text": "the", "start": 1.3, "end": 1.45},
           {"text": "floor,", "start": 1.45, "end": 1.9}, {"text": "\u2014", "start": 1.9, "end": 1.95},
           {"text": "push-up", "start": 2.0, "end": 2.5}],
    "s2": [{"text": "PUSH", "start": 4.0, "end": 4.3}, {"text": "the", "start": 4.3, "end": 4.4},
           {"text": "Floor.", "start": 4.4, "end": 4.9}, {"text": "slowly", "start": 5.0, "end": 5.5}],
}


class TestFilmHelpersStatic(unittest.TestCase):
    """No browser: the determinism lint `studio.py validate` applies to compositions, run on the new runtime files,
    and word-cue parity between the page (Studio.cues.findAll) and `studio.py words` (captions.word_index)."""

    def test_film_helpers_pass_the_determinism_lint(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        studio = importlib.import_module("studio")
        for rel in FILM_HELPER_FILES:
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            for pattern, _severity, message in studio.BANNED_PATTERNS:
                self.assertIsNone(re.search(pattern, text), f"{rel}: {message}")
            for m in re.finditer(r"\.(from|to)\(\s*[^,]+,\s*\{[^}]*autoAlpha", text):
                self.fail(f"{rel}: {m.group(0)[:60]}... uses from()/to() for an entrance; use fromTo()")

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_word_cues_match_studio_words(self):
        sys.path.insert(0, str(REPO_ROOT / "src" / "pipeline"))
        captions = importlib.import_module("captions")
        phrases = ["push the floor", "push-up", "floor", "the floor slowly", "push", "floor push-up", "nothing here"]
        js = ("global.window=global;global.Studio={comp:{},space:{},type:{}};"
              "Studio.cues=function(m){var f=function(n,o){return m[n]+(o||0)};f.map=m;return f};"
              "Studio.rng=function(){return function(){return 0.5}};"
              "require('./src/studio/studio-film.js');"
              "const words=" + json.dumps({"scenes": WORDS_FIXTURE}) + ";"
              "const runs=Studio.cues.words(words);"
              "console.log(JSON.stringify(" + json.dumps(phrases) + ".map(p=>Studio.cues.findAll(p,runs))));")
        res = subprocess.run(["node", "-e", js], cwd=REPO_ROOT, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        self.assertEqual(res.returncode, 0, res.stderr)
        page = json.loads(res.stdout)
        for phrase, got in zip(phrases, page):
            want = sorted(captions.word_index(WORDS_FIXTURE, phrase), key=lambda h: h["start"])
            self.assertEqual([(h["scene"], h["start"], h["end"]) for h in got],
                             [(h["scene"], h["start"], h["end"]) for h in want], phrase)


if __name__ == "__main__":
    unittest.main()
