#!/usr/bin/env python3
"""anatomy3d-bench.py: reusable anatomical test scenes for the 3D Tibi, as contact sheets you LOOK at (the numeric tests are scripts/anatomy3d-check.js).

    .venv/bin/python scripts/anatomy3d-bench.py [--set angles|poses|modes|all] [--gender m|f] [--out qa/anatomy3d] [--size 300x440]

  angles  the resting body from front, rear, left, right, two three-quarters and a close-up of shoulders, hips and knee (continuous silhouette, integrated
          muscle definition, shorts and hem, no detached shape from any side)
  poses   activation in squat bottom, curl top, lateral raise top, hip-thrust lockout, calf-raise top and standing, three-quarter and rear
          (highlights follow the surface through joint deformation; shoulders, hips, knees and ankles)
  modes   normal, activation, calf cutaway (skin out, then superficial layer out), glute cutaway, quad cutaway, isolated calf on a ghost body, muscle layer, skeleton
Each cell is a headless-Chrome still of assets/fitness/lab3d/anatomy-bench.html (SwiftShader WebGL) under the host render lock. A sheet per set, labelled.
Acceptance (anatomy skill): fail the build if a muscle shape protrudes, looks like a sticker, a highlight leaves the surface, skin and muscle intersect, a deep
structure reads as superficial, or the colour language blurs; then fix, re-run anatomy3d-check.js, and look again.
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


def cell(ch, query, out, w, h):
    url = f"file://{ROOT}/assets/fitness/lab3d/anatomy-bench.html?w={w}&h={h}&{query}"
    subprocess.run([ch, "--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", f"--screenshot={out}", f"--window-size={w},{h}",
                    "--virtual-time-budget=4500", "--hide-scrollbars", url], capture_output=True, text=True, stdin=subprocess.DEVNULL)


def sets(g):
    base = f"g={g}&dist=2300&ty=370"
    angles = [("front", f"{base}&az=0&el=4"), ("rear", f"{base}&az=180&el=4"), ("left", f"{base}&az=90&el=4"), ("right", f"{base}&az=270&el=4"),
              ("3/4 front", f"{base}&az=35&el=8"), ("3/4 rear", f"{base}&az=145&el=8"),
              ("close: shoulders", f"g={g}&az=25&el=6&dist=950&ty=520"), ("close: hips", f"g={g}&az=150&el=6&dist=1000&ty=330"), ("close: knee", f"g={g}&az=60&el=4&dist=900&ty=190")]
    acts = "acts=glute:3:1,quad:3:0.9,hams:2:0.7,calf:2:0.6,soleus:2:0.6,adductor:1:0.6"
    poses = [("squat bottom, side", f"g={g}&ex=squat&t=1.75&az=90&el=6&dist=2500&ty=400&{acts}"), ("squat bottom, rear", f"g={g}&ex=squat&t=1.75&az=160&el=8&dist=2500&ty=400&{acts}"),
             ("curl top", f"g={g}&ex=curl&t=1.45&az=35&el=8&dist=2300&ty=470&acts=biceps:3:1,brach:2:0.8,flexor:1:0.5"),
             ("lateral raise top", f"g={g}&ex=raise&t=1.6&az=20&el=8&dist=2500&ty=470&acts=delt-side:3:1,trap:2:0.7"),
             ("hip thrust lockout", f"g={g}&ex=hipthrust&t=1.5&az=60&el=14&dist=2300&tx=80&ty=230&acts=glute:3:1,hams:2:0.7"),
             ("calf raise top, rear", f"g={g}&ex=calfraise&t=1.4&az=170&el=8&dist=1500&ty=200&acts=calf:3:1,soleus:3:0.85"),
             ("press bottom", f"g={g}&ex=press&t=1.5&az=30&el=20&dist=2300&tx=-120&ty=230&acts=pec:3:1,triceps:2:0.8,delt-front:2:0.6")]
    modes = [("normal", f"{base}&az=30&el=8"), ("activation", f"{base}&az=150&el=8&{acts}"),
             ("calf cutaway 1", f"g={g}&az=165&el=8&dist=1200&ty=130&cut=calf:1&hi=calf:1"), ("calf cutaway 2", f"g={g}&az=165&el=8&dist=1200&ty=130&cut=calf:2&hi=soleus:1"),
             ("glute cutaway", f"g={g}&az=150&el=12&dist=1500&ty=300&cut=glute:1.6&hi=glute:1"), ("quad cutaway", f"g={g}&az=30&el=8&dist=1500&ty=230&cut=quad:1.6&hi=quad:1"),
             ("isolated calf, ghost", f"{base}&az=30&el=8&view=ghost:1&iso=calf:1,soleus:1&hi=calf:1,soleus:1"), ("muscle layer", f"{base}&az=20&el=6&view=ghost:1,layer:1"),
             ("skeleton", f"{base}&az=30&el=8&view=ghost:1,skel:1")]
    return {"angles": angles, "poses": poses, "modes": modes}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", default="all", choices=["angles", "poses", "modes", "all"])
    ap.add_argument("--gender", default="m")
    ap.add_argument("--out", default="qa/anatomy3d")
    ap.add_argument("--size", default="300x440")
    a = ap.parse_args()
    from hostlock import heavy_lock
    from PIL import Image, ImageDraw
    w, h = (int(x) for x in a.size.split("x"))
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    ch = chrome()
    todo = sets(a.gender)
    names = list(todo) if a.set == "all" else [a.set]
    with heavy_lock("render", slug="anatomy3d-bench"):
        for name in names:
            cells = todo[name]
            cols = min(len(cells), 5 if name != "angles" else 5)
            rows = (len(cells) + cols - 1) // cols
            sheet = Image.new("RGB", (w * cols, (h + 22) * rows), (246, 243, 236))
            dr = ImageDraw.Draw(sheet)
            tmp = out / "cell.png"
            for i, (label, q) in enumerate(cells):
                cell(ch, q, str(tmp), w, h)
                if tmp.exists():
                    sheet.paste(Image.open(tmp).convert("RGB"), ((i % cols) * w, (i // cols) * (h + 22) + 22))
                dr.text(((i % cols) * w + 8, (i // cols) * (h + 22) + 4), label, fill=(27, 29, 41))
            tmp.unlink(missing_ok=True)
            path = out / f"{name}-{a.gender}.png"
            sheet.save(path)
            print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
