#!/usr/bin/env python3
"""fitness-animatic.py: a rough preview of a fitness film before (or between) full renders, plus a pacing lint that catches story problems early.

    .venv/bin/python scripts/fitness-animatic.py <slug> [--no-snapshots] [--wps 3.3] [--max-gap 2.5]

Reads projects/<slug>/storyboard.json (scenes, times, narration, planned beats). With snapshots (default) it asks HyperFrames for two real frames per
scene from the CURRENT composition (scene start + 0.4 s and the middle), under the host render lock, and lays them out with the narration, the planned visual
and the measured pace on one sheet: qa/animatic/animatic.png. A draft composition is enough: the point is to see the shot list, the order and the rhythm.
The pacing lint (qa/animatic/animatic.json) reports, per scene: words per second against --wps, the longest stretch with no planned visual event against
--max-gap, a hook beat inside the first second, and scenes shorter than 2 s. Warnings only; a human decides. Exit 0 unless the storyboard is unreadable.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--no-snapshots", action="store_true")
    ap.add_argument("--wps", type=float, default=3.3, help="words per second above which narration is rushed")
    ap.add_argument("--max-gap", type=float, default=2.5, help="longest allowed stretch without a planned visual event (anti-laziness rule)")
    a = ap.parse_args()
    pdir = ROOT / "projects" / a.slug
    sb_path = pdir / "storyboard.json"
    if not sb_path.exists():
        print(f"no storyboard at {sb_path.relative_to(ROOT)}")
        return 1
    sb = json.loads(sb_path.read_text())
    scenes = sb["scenes"]
    out = pdir / "qa" / "animatic"
    out.mkdir(parents=True, exist_ok=True)
    report = {"slug": a.slug, "duration_sec": sb.get("duration_sec"), "scenes": [], "warnings": []}
    warn = report["warnings"].append
    for i, sc in enumerate(scenes):
        t0, t1 = float(sc["start_sec"]), float(sc["end_sec"])
        words = len(re.findall(r"[A-Za-z0-9']+", sc.get("narration", "")))
        beats = sorted(float(b["at_sec"]) for b in sc.get("beats", []))
        marks = [t0] + beats + [t1]
        gap = max(marks[j + 1] - marks[j] for j in range(len(marks) - 1))
        wps = words / max(0.1, t1 - t0)
        row = {"id": sc["id"], "start": t0, "end": t1, "seconds": round(t1 - t0, 2), "words": words, "wps": round(wps, 2), "longest_gap_s": round(gap, 2), "beats": len(beats)}
        report["scenes"].append(row)
        if wps > a.wps:
            warn(f"{sc['id']}: {wps:.1f} words/s is above {a.wps:g} (rushed narration; cut words, do not raise the speed)")
        if gap > a.max_gap:
            warn(f"{sc['id']}: {gap:.1f} s with no planned visual event (limit {a.max_gap:g}); add a beat or a camera move")
        if t1 - t0 < 2.0:
            warn(f"{sc['id']}: only {t1 - t0:.1f} s long")
        if i == 0 and (not beats or beats[0] - t0 > 1.0):
            warn(f"{sc['id']}: no visual event in the first second (the hook must act on frame 0)")
    shots = []
    if not a.no_snapshots:
        times = []
        for sc in scenes:
            t0, t1 = float(sc["start_sec"]), float(sc["end_sec"])
            times += [round(t0 + 0.4, 2), round((t0 + t1) / 2, 2)]
        src = pdir / "src"
        arg = ",".join(str(t) for t in times)
        snap = out / "snap"
        subprocess.run(["python3.12", "scripts/session-guard.py", "run", "--slug", a.slug, "--cwd", str(src.relative_to(ROOT)), "render", "--", "hyperframes", "snapshot", ".",
                        "--at", arg, "--output", str(snap.resolve()), "--no-end"], cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True)
        shots = sorted(snap.glob("frame-*.png"))
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow missing: run with .venv/bin/python to get the sheet")
        shots = []
    if shots and len(shots) >= 2 * len(scenes):
        W, rowh, tw = 1400, 340, 190
        sheet = Image.new("RGB", (W, rowh * len(scenes)), (246, 243, 236))
        dr = ImageDraw.Draw(sheet)
        try:
            fb = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 19)
            fs = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15)
        except OSError:
            fb = fs = ImageFont.load_default()
        for i, sc in enumerate(scenes):
            y = i * rowh
            for k in range(2):
                im = Image.open(shots[2 * i + k]).convert("RGB")
                im.thumbnail((tw, rowh - 20))
                sheet.paste(im, (14 + k * (tw + 10), y + 10))
            x0 = 14 + 2 * (tw + 10) + 14
            r = report["scenes"][i]
            dr.text((x0, y + 12), f"{sc['id']}  {r['start']:.1f}-{r['end']:.1f} s  ({r['seconds']} s)   {r['words']} words = {r['wps']} w/s   longest gap {r['longest_gap_s']} s", fill=(27, 29, 41), font=fb)
            def wrap(t, width=108):
                out_l, cur = [], ""
                for w in t.split():
                    if len(cur) + len(w) > width:
                        out_l.append(cur.rstrip())
                        cur = ""
                    cur += w + " "
                out_l.append(cur.rstrip())
                return out_l
            lines = wrap("NARRATION  " + sc.get("narration", "")) + [""] + wrap("VISUAL  " + sc.get("visual", "")[:420])
            ty = y + 48
            for ln in lines[:13]:
                dr.text((x0, ty), ln, fill=(74, 78, 96), font=fs)
                ty += 20
            dr.line([(0, y + rowh - 1), (W, y + rowh - 1)], fill=(200, 200, 210))
        sheet.save(out / "animatic.png")
        report["sheet"] = str((out / "animatic.png").relative_to(ROOT))
    (out / "animatic.json").write_text(json.dumps(report, indent=1))
    (pdir / "qa" / "animatic.json").write_text(json.dumps(report, indent=1))
    print(f"animatic: {len(scenes)} scene(s), {len(report['warnings'])} pacing warning(s)" + (f", sheet {report.get('sheet')}" if report.get("sheet") else ""))
    for w in report["warnings"]:
        print("  WARN " + w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
