#!/usr/bin/env python3
"""
mythic3d.py - render the 3D mythic figures (src/blender/mythic3d) and lay out review sheets.

    python scripts/mythic3d.py list
    python scripts/mythic3d.py render [--figures rama,shiva|all] [--look painted|bronze|both]
                                      [--views hero,front,q3,profile,q3back,back,head] [--opt rama:tone=brown]
                                      [--samples 48] [--size 900x1200] [--tag name] [--out DIR] [--no-sheets]
    python scripts/mythic3d.py sheets [--out DIR]

Each figure is built procedurally in Blender (metaball skin, sculpt, paint, dress, armoury, aura) from its
identity block in .claude/skills/mythic-tales/references/figure-design.md section 4 and rendered on the
warm paper studio: a hero shot (low three-quarter angle), the five-view turnaround (front, three-quarter,
profile, three-quarter back, back) and a head close-up. One Blender process per figure, under the host
render lock (one heavy job at a time). Output goes to projects/_mythic-figures/3d/ (gitignored):
<figure>-<look>-<view>.png, <figure>-<look>.json, turnaround-<figure>-<look>.png, gallery-<look>.png.
These are review renders and reference turnarounds, not film plates (plates carry no text and go through
scripts/visual-director.py).
"""

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "src" / "blender" / "mythic3d"
OUT = ROOT / "projects" / "_mythic-figures" / "3d"
sys.path.insert(0, str(ROOT / "src"))

FIGURES = {
    "rama": "Rama (Valmiki; forest years)",
    "hanuman": "Hanuman (Veera form)",
    "shiva": "Shiva",
    "ganesha": "Ganesha",
    "athena": "Athena (Promachos)",
    "odin": "Odin (Grimnir)",
    "tirthankara": "Mahavira (Digambara)",
    "buddha": "The Buddha (bhumisparsha)",
}
TURN = ["front", "q3", "profile", "q3back", "back"]
DEFAULT_VIEWS = ["hero"] + TURN + ["head"]


def find_blender():
    spec = importlib.util.spec_from_file_location("visual_director", ROOT / "scripts" / "visual-director.py")
    vd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vd)
    return vd.find_blender()


def parse_opts(items):
    out = {}
    for item in items or []:
        fid, _, kv = item.partition(":")
        for pair in kv.split(";"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                out.setdefault(fid, {})[k] = v
    return out


def render(args):
    from pipeline.hostlock import heavy_lock

    blender = find_blender()
    if not blender:
        print("Blender not found: python scripts/visual-director.py install-blender", file=sys.stderr)
        return 2
    figs = list(FIGURES) if args.figures in (None, "all") else [f.strip() for f in args.figures.split(",")]
    looks = ["painted", "bronze"] if args.look == "both" else [args.look]
    views = args.views.split(",") if args.views else DEFAULT_VIEWS
    opts = parse_opts(args.opt)
    w, h = (int(x) for x in args.size.lower().split("x"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs_dir = out / "_jobs"
    jobs_dir.mkdir(exist_ok=True)
    failed = []
    with heavy_lock("render", slug="_mythic-figures"):
        for fid in figs:
            for look in looks:
                job = {"figure": fid, "look": look, "options": opts.get(fid, {}), "out_dir": str(out), "views": views,
                       "width": w, "height": h, "samples": args.samples, "engine": args.engine, "tag": args.tag}
                jp = jobs_dir / f"{fid}-{look}{'-' + args.tag if args.tag else ''}.json"
                jp.write_text(json.dumps(job, indent=2), encoding="utf-8")
                log = jobs_dir / (jp.stem + ".log")
                t0 = time.time()
                with open(log, "w", encoding="utf-8") as lf:
                    rc = subprocess.run([str(blender), "-b", "--factory-startup", "--python-exit-code", "1",
                                         "--python", str(KIT / "run.py"), "--", "--job", str(jp)],
                                        stdout=lf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL).returncode
                status = "ok" if rc == 0 else f"FAILED (exit {rc}, log {log})"
                print(f"{fid} [{look}] {status} in {time.time() - t0:.0f} s")
                if rc:
                    failed.append(fid)
    if not args.no_sheets:
        sheets(argparse.Namespace(out=str(out)))
    return 1 if failed else 0


def sheets(args):
    from PIL import Image, ImageDraw, ImageFont

    out = Path(args.out)
    try:
        font = ImageFont.truetype("georgia.ttf", 30)
        small = ImageFont.truetype("georgia.ttf", 22)
    except OSError:
        font = small = ImageFont.load_default()
    paper = (244, 239, 230)
    ink = (40, 30, 24)
    made = []
    for look in ("painted", "bronze"):
        heroes = []
        for fid, name in FIGURES.items():
            frames = [out / f"{fid}-{look}-{v}.png" for v in TURN]
            if all(p.exists() for p in frames):
                ims = [Image.open(p).convert("RGB") for p in frames]
                tw = sum(i.width for i in ims)
                th = max(i.height for i in ims)
                sheet = Image.new("RGB", (tw, th + 70), paper)
                x = 0
                d = ImageDraw.Draw(sheet)
                for v, im in zip(TURN, ims):
                    sheet.paste(im, (x, 70))
                    d.text((x + 16, 40), {"q3": "three-quarter", "q3back": "three-quarter back"}.get(v, v), fill=ink, font=small)
                    x += im.width
                d.text((16, 6), f"{name}  |  {look}", fill=ink, font=font)
                p = out / f"turnaround-{fid}-{look}.png"
                sheet.save(p)
                made.append(p)
            hp = out / f"{fid}-{look}-hero.png"
            if hp.exists():
                heroes.append((name, Image.open(hp).convert("RGB")))
        if heroes:
            cols = 4
            cw, ch = 540, 675
            rows = (len(heroes) + cols - 1) // cols
            g = Image.new("RGB", (cols * cw, rows * (ch + 46)), paper)
            d = ImageDraw.Draw(g)
            for i, (name, im) in enumerate(heroes):
                im = im.resize((cw, ch), Image.LANCZOS)
                x, y = (i % cols) * cw, (i // cols) * (ch + 46)
                g.paste(im, (x, y))
                d.text((x + 14, y + ch + 8), name, fill=ink, font=small)
            p = out / f"gallery-{look}.png"
            g.save(p)
            made.append(p)
    for p in made:
        print(p)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    r = sub.add_parser("render")
    r.add_argument("--figures", default="all")
    r.add_argument("--look", default="painted", choices=["painted", "bronze", "both"])
    r.add_argument("--views")
    r.add_argument("--opt", action="append", help="figure:key=value;key=value (e.g. rama:tone=brown)")
    r.add_argument("--samples", type=int, default=48)
    r.add_argument("--size", default="900x1200")
    r.add_argument("--engine", default="eevee", choices=["eevee", "cycles"])
    r.add_argument("--tag")
    r.add_argument("--out", default=str(OUT))
    r.add_argument("--no-sheets", action="store_true")
    s = sub.add_parser("sheets")
    s.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    if a.cmd == "list":
        for fid, name in FIGURES.items():
            print(f"{fid:12s} {name}")
        return 0
    return render(a) if a.cmd == "render" else sheets(a)


if __name__ == "__main__":
    raise SystemExit(main())
