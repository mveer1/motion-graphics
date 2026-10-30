#!/usr/bin/env python3
"""
tests/reference-derived/benchmark.py
Preview-capture benchmark for the reference-derived test compositions: seeks every frame at the
composition's fps in Playwright Chromium and takes a JPEG screenshot (no encoding), recording build
time, ms per frame and the peak working set of the headless Chromium processes.

This measures the preview path on the current host. It is not a HyperFrames render and not the
Apple M2 render host; record results as such.

Usage: python tests/reference-derived/benchmark.py [name | repo-relative .html ...] [--every N] [--out FILE]
"""

import argparse
import functools
import http.server
import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def chromium_working_set_mb() -> float:
    """Sum of resident memory of Playwright's headless Chromium processes (MB)."""
    try:
        if os.name == "nt":
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq chrome-headless-shell.exe", "/FO", "CSV", "/NH"],
                                 capture_output=True, text=True, timeout=10).stdout
            kb = [int(re.sub(r"[^0-9]", "", row.split('","')[-1])) for row in out.strip().splitlines() if row.startswith('"')]
            return sum(kb) / 1024
        out = subprocess.run(["ps", "-axo", "rss=,comm="], capture_output=True, text=True, timeout=10).stdout
        return sum(int(line.split()[0]) for line in out.splitlines() if "headless" in line.lower() and "chrom" in line.lower()) / 1024
    except (OSError, ValueError, subprocess.SubprocessError):
        return -1.0


def root_attrs(html: str) -> dict:
    m = re.search(r"<div[^>]*data-composition-id[^>]*>", html)
    return dict(re.findall(r'(data-[\w-]+)="([^"]*)"', m.group(0))) if m else {}


def bench(page, base: str, name: str, every: int) -> dict:
    rel = name.replace("\\", "/") if name.endswith(".html") else f"tests/reference-derived/{name}/index.html"
    html = (REPO_ROOT / rel).read_text(encoding="utf-8")
    a = root_attrs(html)
    w, h, fps, dur = int(a["data-width"]), int(a["data-height"]), int(a.get("data-fps", 30)), float(a["data-duration"])
    page.set_viewport_size({"width": w, "height": h})
    t0 = time.perf_counter()
    page.goto(f"{base}/{rel}", wait_until="load", timeout=60000)
    page.wait_for_function("() => !!(window.__timelines && window.__timelines.root) || !!document.querySelector('[data-studio-error]')", timeout=30000)
    build_ms = (time.perf_counter() - t0) * 1000
    err = page.evaluate("() => { const e = document.querySelector('[data-studio-error]'); return e ? e.getAttribute('data-studio-error') : null; }")
    if err:
        return {"name": name, "error": err}
    frames = int(dur * fps)
    peak = chromium_working_set_mb()
    times = []
    for k in range(frames):
        t = k / fps
        s = time.perf_counter()
        page.evaluate("(t) => { const tl = window.__timelines.root; tl.pause(); tl.seek(t); }", t)
        page.screenshot(type="jpeg", quality=80)
        times.append((time.perf_counter() - s) * 1000)
        if k % every == 0:
            peak = max(peak, chromium_working_set_mb())
    times.sort()
    return {
        "name": name, "size": f"{w}x{h}", "fps": fps, "duration_sec": dur, "frames": frames,
        "build_ms": round(build_ms), "ms_per_frame_median": round(times[len(times) // 2], 1),
        "ms_per_frame_p95": round(times[int(len(times) * 0.95)], 1), "ms_per_frame_max": round(times[-1], 1),
        "capture_sec_total": round(sum(times) / 1000, 1), "peak_chromium_mb": round(peak),
        "dom_nodes": page.evaluate("() => document.getElementsByTagName('*').length"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("names", nargs="*", help="test folders, or repo-relative .html files (default: all test folders)")
    ap.add_argument("--every", type=int, default=15, help="sample memory every N frames")
    ap.add_argument("--out", default=str(HERE / "benchmark.json"))
    args = ap.parse_args()
    if sync_playwright is None:
        print("playwright is not installed")
        return 2
    names = args.names or sorted(p.name for p in HERE.iterdir() if (p / "index.html").exists())
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(REPO_ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for name in names:
                page = browser.new_page()
                r = bench(page, f"http://127.0.0.1:{srv.server_address[1]}", name, args.every)
                page.close()
                print(json.dumps(r))
                results.append(r)
            version = browser.version
            browser.close()
    finally:
        srv.shutdown()
    report = {"host": f"{platform.system()} {platform.release()} {platform.machine()}", "renderer": f"Playwright Chromium {version} (preview capture: seek + JPEG screenshot, no encode)",
              "date": time.strftime("%Y-%m-%d"), "note": "Not a HyperFrames render and not the Apple M2 render host.", "results": results}
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
