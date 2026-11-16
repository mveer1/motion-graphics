#!/usr/bin/env python3
"""rig3d-stills.py: contact sheet of the 3D Tibi from several camera angles and moments, in seconds.

    .venv/bin/python scripts/rig3d-stills.py curl --shots front,three,side,back --times 0,1.0 [--gender m|f]
                     [--size 360x480] [--out qa/rig3d/curl.png] [--extra "az=70&el=40"]

Rows are moments (film seconds inside the exercise's own timeline), columns are camera shots (the exercise's `shots`
table in kits/fitness/exercises3d.js, or raw az/el through --extra). Renders with the headless Chrome HyperFrames
installed (SwiftShader WebGL, a few seconds per cell) via assets/fitness/lab3d/still.html, under the host render lock.
Look at the sheet: posture, contact, equipment and activation are judged by eye; scripts/rig3d-check.js judges the numbers.
"""
import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "pipeline"))


def chrome() -> str:
    hits = sorted(glob.glob(os.path.expanduser("~/.cache/puppeteer/chrome-headless-shell/*/*/chrome-headless-shell")))
    if not hits:
        sys.exit("no headless Chrome found under ~/.cache/puppeteer (install HyperFrames first)")
    return hits[-1]


def cell(ch: str, query: str, out: str, w: int, h: int) -> None:
    url = f"file://{ROOT}/assets/fitness/lab3d/still.html?w={w}&h={h}&{query}"
    r = subprocess.run([ch, "--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                        f"--screenshot={out}", f"--window-size={w},{h}", "--virtual-time-budget=3000", "--hide-scrollbars", url],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if "written" not in r.stderr:
        print(r.stderr[-400:])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("exercise")
    ap.add_argument("--shots", default="front,three,side,back")
    ap.add_argument("--times", default="0")
    ap.add_argument("--gender", default="m")
    ap.add_argument("--size", default="360x480")
    ap.add_argument("--extra", default="")
    ap.add_argument("--out")
    a = ap.parse_args()
    from hostlock import heavy_lock
    from PIL import Image
    w, h = (int(x) for x in a.size.split("x"))
    shots, times = a.shots.split(","), [float(t) for t in a.times.split(",")]
    out = Path(a.out) if a.out else ROOT / "qa" / "rig3d" / f"{a.exercise}-{a.gender}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (w * len(shots), h * len(times)), (246, 243, 236))
    ch = chrome()
    tmp = out.with_suffix(".cell.png")
    with heavy_lock("render", slug="rig3d-stills"):
        for r, t in enumerate(times):
            for c, s in enumerate(shots):
                q = f"ex={a.exercise}&g={a.gender}&t={t}&shot={s}" + (("&" + a.extra) if a.extra else "")
                cell(ch, q, str(tmp), w, h)
                if tmp.exists():
                    sheet.paste(Image.open(tmp).convert("RGB"), (c * w, r * h))
    tmp.unlink(missing_ok=True)
    sheet.save(out)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
