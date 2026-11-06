#!/usr/bin/env python3
"""Poster for a project: the last non-black frame of its finished film.

Every project folder (a studio project, or one version folder of a legacy project) gets
`poster.jpg` plus `poster.json` (which film and time it came from, and that film's length).
The catalogue (scripts/build-catalogue.py) shows the poster on each tile, and tags the tile by
the film's length from poster.json.

    python3 scripts/poster.py <slug|path> ...      # one or more projects (versions: slug/v1)
    python3 scripts/poster.py --all                # every project and version under projects/
    python3 scripts/poster.py --all --force        # redo posters that are already current
    python3 scripts/poster.py --video f.mp4 --out poster.jpg

`studio.py build` runs this after the render is delivered, and `build-project.sh` after the legacy
export, so a new project gets its poster without a separate step. A decode of the last seconds is
light, so it does not take the render lock.

The film is the current `renders/<format>/final.mp4` of the primary format, else the newest finished
film in `renders/history/` (`studio.py upgrade` moves superseded renders there), else the legacy
`renders/final.mp4`.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"
POSTER = "poster.jpg"
SIDECAR = "poster.json"
# signalstats YAVG of pure black is 16 in limited-range video; a frame counts as not black above this.
BLACK_YAVG = 20.0
TAIL_SEC = 10.0


def probe_duration(video: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def luma_samples(video: Path, start: float = 0.0) -> List[Tuple[float, float]]:
    """(time, mean luma) for every frame from `start`, decoded at the film's own frame rate."""
    cmd = ["ffmpeg", "-v", "error", "-nostdin"]
    if start > 0:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", str(video), "-an", "-vf", "signalstats,metadata=mode=print:file=-", "-f", "null", "-"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed on {video}: {res.stderr.strip()[:300]}")
    return parse_samples(res.stdout, start)


def parse_samples(text: str, offset: float = 0.0) -> List[Tuple[float, float]]:
    """Read ffmpeg's `metadata=print` output: a 'pts_time:' line, then 'lavfi.signalstats.YAVG=' per frame."""
    samples, t = [], None
    for line in text.splitlines():
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m:
            t = float(m.group(1)) + offset
            continue
        m = re.match(r"lavfi\.signalstats\.YAVG=([0-9.]+)", line.strip())
        if m and t is not None:
            samples.append((t, float(m.group(1))))
            t = None
    return samples


def last_non_black(samples: List[Tuple[float, float]], threshold: float = BLACK_YAVG) -> Optional[float]:
    """Time of the last frame whose mean luma is above `threshold`, or None when every frame is black."""
    for t, y in reversed(samples):
        if y > threshold:
            return t
    return None


def find_last_non_black(video: Path) -> Tuple[float, float]:
    """(time of the last non-black frame, film duration). Looks at the tail first, then the whole film."""
    dur = probe_duration(video)
    t = last_non_black(luma_samples(video, max(0.0, dur - TAIL_SEC)))
    if t is None and dur > TAIL_SEC:
        t = last_non_black(luma_samples(video))
    if t is None:
        raise RuntimeError(f"{video} has no non-black frame")
    return t, dur


def make_poster(video: Path, out: Path) -> dict:
    t, dur = find_last_non_black(video)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-nostdin", "-ss", f"{max(0.0, t - 0.005):.3f}", "-i", str(video),  # a hair early: a rounded-up -ss would skip the last frame
                    "-frames:v", "1", "-vf", "scale=out_range=full,format=yuvj420p", "-q:v", "2", str(out)], check=True)
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg wrote no frame from {video} at {t:.3f}s")
    w, h = (int(x) for x in subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(video)],
        capture_output=True, text=True, check=True).stdout.strip().split("x"))
    return {"time_sec": round(t, 3), "film_duration_sec": round(dur, 3), "width": w, "height": h}


def rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def primary_format(folder: Path) -> Optional[str]:
    try:
        formats = json.loads((folder / "project.json").read_text())["formats"]
    except (OSError, ValueError, KeyError):
        return None
    return next((f["id"] for f in formats if f.get("primary")), formats[0]["id"] if formats else None)


def find_film(folder: Path) -> Optional[Tuple[Path, Optional[str], bool]]:
    """(film, format, is_current) for a project folder, or None when nothing has been rendered."""
    renders = folder / "renders"
    want = primary_format(folder)
    current = [(p, p.parent.name) for p in sorted(renders.glob("*/final.mp4")) if p.parent.name != "history"]
    if (renders / "final.mp4").exists():
        current.append((renders / "final.mp4", None))
    history = []
    for p in sorted((renders / "history").glob("*/*/final.mp4")):
        history.append((p, p.parent.parent.name, p.parent.name))  # (film, format, timestamp)
    history.sort(key=lambda h: h[2], reverse=True)
    for pool, is_current in ((current, True), ([(p, f) for p, f, _ in history], False)):
        pick = next((c for c in pool if want and c[1] == want), pool[0] if pool else None)
        if pick:
            return pick[0], pick[1], is_current
    return None


def all_films(folder: Path) -> List[Tuple[Path, Optional[str], bool]]:
    """One finished film per format: (film, format, is_current), primary format first. The catalogue links these."""
    renders = folder / "renders"
    best = {}  # format -> (film, is_current)
    for p in sorted((renders / "history").glob("*/*/final.mp4"), key=lambda p: p.parent.name):
        best[p.parent.parent.name] = (p, False)  # newer timestamps overwrite older ones
    for p in sorted(renders.glob("*/final.mp4")):
        if p.parent.name != "history":
            best[p.parent.name] = (p, True)  # a current render beats history
    out = [(f, fmt, cur) for fmt, (f, cur) in best.items()]
    if (renders / "final.mp4").exists():
        out.append((renders / "final.mp4", None, True))
    want = primary_format(folder)
    return sorted(out, key=lambda x: (x[1] != want, x[1] or ""))


def project_folders() -> List[Path]:
    """Every folder that holds one film: a studio project, or a version folder of a legacy project."""
    out = []
    for folder in sorted(PROJECTS.iterdir()):
        if not folder.is_dir():
            continue
        if (folder / "project.json").exists():
            out.append(folder)
        else:
            out += [d for d in sorted(folder.iterdir()) if d.is_dir() and d.name != "archive" and ((d / "src").exists() or (d / "renders").exists())]
    return out


def resolve(ref: str) -> Path:
    for cand in (Path(ref), PROJECTS / ref, ROOT / ref):
        if cand.is_dir():
            return cand.resolve()
    raise SystemExit(f"Error: no project folder '{ref}' (a slug, or slug/version for a legacy project).")


def poster_is_current(folder: Path, film: Path) -> bool:
    try:
        meta = json.loads((folder / SIDECAR).read_text())
    except (OSError, ValueError):
        return False
    return (folder / POSTER).exists() and meta.get("source") == rel(film) and film.stat().st_mtime <= (folder / POSTER).stat().st_mtime + 1


def poster_for(folder: Path, force: bool = False) -> Optional[dict]:
    """Make folder/poster.jpg from its finished film. Returns the sidecar, or None when there is no film."""
    found = find_film(folder)
    if not found:
        print(f"  [skip] {rel(folder)}: no finished film (renders/<format>/final.mp4 or renders/history/)")
        return None
    film, fmt, current = found
    if not force and poster_is_current(folder, film):
        print(f"  [ok]   {rel(folder)}: poster is current")
        return json.loads((folder / SIDECAR).read_text())
    meta = make_poster(film, folder / POSTER)
    meta = {"source": rel(film), "format": fmt, "current_render": current, **meta, "created": date.today().isoformat()}
    (folder / SIDECAR).write_text(json.dumps(meta, indent=2) + "\n")
    print(f"  [made] {rel(folder / POSTER)}  from {meta['source']} at {meta['time_sec']}s of {meta['film_duration_sec']}s")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description="Poster = the last non-black frame of a project's finished film.")
    ap.add_argument("projects", nargs="*", help="slug, slug/version, or a folder path")
    ap.add_argument("--all", action="store_true", help="every project and version under projects/")
    ap.add_argument("--force", action="store_true", help="remake even when the poster is current")
    ap.add_argument("--video", help="poster for this one video instead (needs --out)")
    ap.add_argument("--out", help="with --video: where to write the image")
    args = ap.parse_args()
    if args.video:
        if not args.out:
            ap.error("--video needs --out")
        meta = make_poster(Path(args.video), Path(args.out))
        print(f"{args.out}: frame at {meta['time_sec']}s of {meta['film_duration_sec']}s")
        return 0
    folders = project_folders() if args.all else [resolve(r) for r in args.projects]
    if not folders:
        ap.error("name a project, or pass --all")
    made = failed = 0
    for folder in folders:
        try:
            made += bool(poster_for(folder, args.force))
        except (RuntimeError, subprocess.CalledProcessError, OSError) as exc:
            failed += 1
            print(f"  [FAIL] {rel(folder)}: {exc}", file=sys.stderr)
    print(f"{made} poster(s) ready, {failed} failed, {len(folders) - made - failed} without a film.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
