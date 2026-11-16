#!/usr/bin/env python3
"""fitness-clip.py: cut named clips out of a finished film, with honest metadata, and archive what they replace.

    .venv/bin/python scripts/fitness-clip.py projects/lab-3d-motion/renders/portrait/final.mp4 \\
        --cut 1-curl-3d:0:10.775 --cut 2-press-3d:10.775:20.825 --cut 3-raise-3d:20.825:32.55 \\
        --out out/lab-3d-review --title "Three lifts, one body" [--fps 30]

Each clip is re-encoded (frame-exact, H.264 yuv420p, AAC) at the film's frame rate, tagged with title and a comment that states the real
size and frame rate ("720x1280 · 30 fps"), so the metadata, the container's frame-rate fields and any label agree. A file the clip replaces is moved
to <out>/archive/<UTC stamp>/ first, never deleted. Verifies every clip with ffprobe (r_frame_rate == avg_frame_rate == --fps) and exits 1 if not.
Light job (ffmpeg re-encode of seconds of 720p): it is not a render, but it still goes through the host lock when one is held (session-guard).
"""
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)], capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("film")
    ap.add_argument("--cut", action="append", required=True, help="name:start:end (seconds)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--crf", type=int, default=17)
    a = ap.parse_args()
    film, out = Path(a.film), Path(a.out)
    if not film.exists():
        print(f"no such film: {film}")
        return 1
    src = probe(film)
    v = next(s for s in src["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in src["streams"])
    size = f"{v['width']}x{v['height']}"
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bad = 0
    for spec in a.cut:
        name, t0, t1 = spec.rsplit(":", 2)
        dst = out / f"{name}.mp4"
        if dst.exists():
            arch = out / "archive" / stamp
            arch.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(arch / dst.name))
        label = f"{size} · {a.fps:g} fps · cut {float(t0):.3f}-{float(t1):.3f} s of {film.name}"
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", t0, "-to", t1, "-i", str(film), "-r", f"{a.fps:g}", "-c:v", "libx264", "-crf", str(a.crf), "-pix_fmt", "yuv420p",
               "-preset", "medium", "-movflags", "+faststart", "-metadata", f"title={a.title or name}", "-metadata", f"comment={label}"]
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"] if has_audio else ["-an"]
        cmd.append(str(dst))
        subprocess.run(cmd, check=True)
        info = probe(dst)
        vs = next(s for s in info["streams"] if s["codec_type"] == "video")
        r, avg = Fraction(vs["r_frame_rate"]), Fraction(vs["avg_frame_rate"])
        ok = abs(float(r) - a.fps) < 0.01 and abs(float(avg) - a.fps) < 0.05
        dur = float(info["format"]["duration"])
        print(f"{'ok  ' if ok else 'FAIL'} {dst.relative_to(ROOT) if dst.is_relative_to(ROOT) else dst}  {vs['width']}x{vs['height']} r={r} avg={float(avg):.3f} {dur:.3f}s")
        bad += 0 if ok else 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
