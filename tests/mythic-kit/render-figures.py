#!/usr/bin/env python3
"""
tests/mythic-kit/render-figures.py - screenshot the mythic figure library and motif review pages
for a person to look at (not a test). Writes PNGs to --out (default projects/_mythic-figures/, gitignored).

    python tests/mythic-kit/render-figures.py [--out DIR]
    python tests/mythic-kit/render-figures.py --ids krishna-human,rama-human:attire=royal [--look silhouette] [--name krishna]

--ids renders only a sheet of those human figures (id or id:option=value;option=value), the way the
mythic-figure-designer skill reviews a new figure; --look picks the look (illustrated by default).
"""
import argparse
import functools
import http.server
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def sheet_height(rows, H=760, Z=280, pad=110):
    """Height that shows every row of figures-human.html, its head close-ups included (the page lays a row
    out as pad + H + 60 + Z + 40; the close-up box starts H + 52 below the row's top)."""
    return pad + (rows - 1) * (H + 60 + Z + 40 + pad) + H + 52 + Z + 24


PAGES = {
    "figures": ("tests/mythic-kit/figures.html", 1680, 1260),
    "figures-heroic": ("tests/mythic-kit/figures.html?build=heroic", 1680, 1260),
    "figures-compare": ("tests/mythic-kit/figures.html?build=compare", 1680, 1260),
    "motifs": ("tests/mythic-kit/motifs.html", 1280, 900),
    "figures-human": ("tests/mythic-kit/figures-human.html?cols=4&H=760&Z=280&pad=110", 1800, sheet_height(2)),
    "figures-human-variants": ("tests/mythic-kit/figures-human.html?ids=rama-human:tone=brown,rama-human:attire=royal,hanuman-human:form=dasa,"
                               "ganesha-human:tone=gold,tirthankara-human:sect=svetambara,tirthankara-human:emblem=snake&cols=3&H=760&Z=280&pad=110", 1800, sheet_height(2)),
    "figures-human-paper": ("tests/mythic-kit/figures-human.html?cols=4&H=760&Z=280&look=paper&grid=0&pad=110", 1800, sheet_height(2)),
    # The silhouette test reads the outline only; head close-ups in solid black say nothing, so Z=0 drops them.
    "figures-human-silhouette": ("tests/mythic-kit/figures-human.html?cols=4&H=760&Z=0&look=silhouette&grid=0&pad=110", 1800, sheet_height(2, Z=0)),
    "armoury": ("tests/mythic-kit/armoury.html", 1800, 1300),
    "proportions": ("tests/mythic-kit/proportions.html", 1800, 1300),
}


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "projects" / "_mythic-figures"), help="default is under projects/ (gitignored)")
    ap.add_argument("--ids", help="only a sheet of these human figures, e.g. krishna-human,rama-human:attire=royal")
    ap.add_argument("--look", default="illustrated", help="look for --ids: illustrated|paper|painted|leather|silhouette")
    ap.add_argument("--name", help="file name for the --ids sheet (default: figure-<first id>)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            pages = PAGES
            if a.ids:
                n = len(a.ids.split(","))
                cols = min(4, n)
                rows = (n + cols - 1) // cols
                name = a.name or "figure-" + a.ids.split(",")[0].split(":")[0]
                pages = {name: (f"tests/mythic-kit/figures-human.html?ids={a.ids}&cols={cols}&H=760&Z={0 if a.look == 'silhouette' else 280}&pad=110&look={a.look}",
                                1800, sheet_height(rows, Z=0 if a.look == "silhouette" else 280))}
            for name, (page_path, w, h) in pages.items():
                if not (ROOT / page_path.split("?")[0]).exists():
                    continue
                page = browser.new_page(viewport={"width": w, "height": h})
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(f"http://127.0.0.1:{srv.server_address[1]}/{page_path}")
                page.wait_for_function("() => document.getElementById('root').getAttribute('data-studio-ready') === 'true' || document.getElementById('root').getAttribute('data-studio-error')")
                err = page.evaluate("() => document.getElementById('root').getAttribute('data-studio-error')")
                page.screenshot(path=str(out / f"{name}.png"))
                print(f"{name}: {out / (name + '.png')}" + (f"  ERROR {err}" if err else "") + (f"  page errors: {errors}" if errors else ""))
                page.close()
            browser.close()
    finally:
        srv.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
