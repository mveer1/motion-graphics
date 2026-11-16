#!/usr/bin/env python3
"""Render one format of a long film in segments, then join them into a single silent picture track.

  render-segments.py <slug> --output <visuals.partial.mp4> [--format landscape] [--segment-sec 90]
                     [--quality looks] [--dry-run] [--keep]

Why: a 12-minute film is 21,600 frames from one headless-Chrome session on an 8 GB machine, and an interrupted
render loses all of it. Here each segment (about 90 s, cut at a scene edge where one is near) is its own
`hyperframes render --start --end` run, so Chrome restarts between segments, every finished segment is a
checkpoint in renders/<format>/chunks/, and a build that was killed (or ran out of memory) resumes at the first
unfinished segment instead of frame 0. The segments are joined with an ffmpeg stream copy and the frame count of
the joined file is checked against duration_sec * fps.

`studio.py build` calls this in place of a single `hyperframes render` when the film is longer than
`render_segments.above_sec` in specs/video-types.json, then promotes and stamps the output exactly as before.
Segments are only reused while the render fingerprint (every file under src/ plus the render settings) is
unchanged; any edit to the composition discards them, because a code edit cannot be traced to one scene.
To revise one scene of a finished film, use scene-revise.py. Needs the render host (hyperframes, ffmpeg);
takes the host render lock itself, re-entrant under `studio.py build`.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "pipeline"))
import segments as seg  # noqa: E402


def studio_module():
    spec = importlib.util.spec_from_file_location("studio", ROOT / "scripts" / "studio.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def frames_of(path: Path) -> int:
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0", str(path)], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    try:
        return int(r.stdout.strip())
    except ValueError:
        return -1


def render_config(studio) -> dict:
    return load(studio.SPECS_DIR / "video-types.json").get("render_segments", {"above_sec": 180, "segment_sec": 90})


def run_segment(pdir: Path, entry: dict, fps: int, quality: str, a: int, b: int, out: Path) -> int:
    cmd = ["hyperframes", "render", ".", "--composition", entry["file"], "--fps", str(fps), "--quality", quality, "--low-memory-mode",
           "--start", f"{a / fps:.4f}", "--end", f"{b / fps:.4f}", "--output", str(out.resolve())]
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=pdir / "src", stdin=subprocess.DEVNULL).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--format")
    ap.add_argument("--output", help="joined picture track (default renders/<format>/visuals.partial.mp4)")
    ap.add_argument("--segment-sec", type=float)
    ap.add_argument("--quality")
    ap.add_argument("--dry-run", action="store_true", help="print the segment plan and exit")
    ap.add_argument("--keep", action="store_true", help="keep the segment files after a successful join")
    a = ap.parse_args()

    studio = studio_module()
    pdir = studio.project_dir(a.slug)
    project = load(pdir / "project.json")
    fmt = a.format or next((f["id"] for f in project["formats"] if f.get("primary")), project["formats"][0]["id"])
    entry = next((f for f in studio.format_entries(project) if f["id"] == fmt), None)
    if entry is None:
        sys.exit(f"error: {pdir.name} has no format {fmt!r}")
    fps = int(project["fps"])
    if fps not in (24, 25, 30, 60):
        sys.exit(f"error: segment rendering needs a whole frame rate of 24, 25, 30 or 60 (project fps is {fps})")
    quality = a.quality or project.get("quality", "looks")
    cfg = render_config(studio)
    total = int(round(project["duration_sec"] * fps))
    sbj = pdir / "storyboard.json"
    edges = seg.boundaries_of(load(sbj) if sbj.exists() else None)
    plan = seg.plan_segments(total, fps, a.segment_sec or cfg["segment_sec"], edges)
    renders = pdir / "renders" / fmt
    chunks = renders / "chunks"
    out = Path(a.output) if a.output else renders / studio.PARTIAL_NAME
    if not out.is_absolute():
        out = ROOT / out

    print(f"{pdir.name} {fmt}: {total} frames ({project['duration_sec']:g} s at {fps} fps) in {len(plan)} segment(s)")
    for i, (x, y) in enumerate(plan):
        print(f"  {seg.segment_name(i)}  {x / fps:8.2f}-{y / fps:8.2f} s  {y - x} frames")
    if a.dry_run:
        return 0
    missing = [t for t in ("hyperframes", "ffmpeg", "ffprobe") if not shutil.which(t)]
    if missing:
        sys.exit(f"error: required tools not on PATH: {', '.join(missing)}. Run on the render host, or use --dry-run.")

    with studio.render_lock(pdir.name):
        fingerprint = studio.render_fingerprint(pdir, entry, fps, quality)
        state_path = chunks / "chunks.json"
        state = load(state_path) if state_path.exists() else {}
        if state and (state.get("fingerprint") != fingerprint or not seg.plan_matches(state.get("segments", []), plan)):
            print("[chunks] the composition, settings or segment plan changed since the last attempt; starting again")
            shutil.rmtree(chunks)
            state = {}
        chunks.mkdir(parents=True, exist_ok=True)
        if not state:
            state = {"fingerprint": fingerprint, "fps": fps, "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     "segments": [{**r, "done": False} for r in seg.plan_record(plan)]}
            state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        for i, (x, y) in enumerate(plan):
            rec = state["segments"][i]
            path = chunks / seg.segment_name(i)
            if rec.get("done") and path.exists() and frames_of(path) == y - x:
                print(f"[skip] {path.name}: finished in an earlier attempt")
                continue
            partial = path.with_name(path.stem + ".partial.mp4")
            partial.unlink(missing_ok=True)
            t0 = time.monotonic()
            rc = run_segment(pdir, entry, fps, quality, x, y, partial)
            if rc != 0 or not partial.exists():
                print(f"error: {path.name} failed (exit {rc}); finished segments are kept in {studio.rel_path(chunks)}, re-run the build to resume")
                return rc or 1
            n = frames_of(partial)
            if n != y - x:
                partial.unlink(missing_ok=True)
                print(f"error: {path.name} has {n} frames, expected {y - x}; not used. Re-run the build to retry this segment")
                return 1
            partial.replace(path)
            rec.update({"done": True, "sec": round(time.monotonic() - t0, 1)})
            state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
            print(f"[done] {path.name} in {rec['sec']} s ({i + 1}/{len(plan)})", flush=True)

        listing = chunks / "concat.txt"
        listing.write_text("".join(f"file '{(chunks / seg.segment_name(i)).resolve().as_posix()}'\n" for i in range(len(plan))), encoding="utf-8")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.unlink(missing_ok=True)
        rc = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy",
                             "-movflags", "+faststart", str(out)], stdin=subprocess.DEVNULL).returncode
        if rc != 0 or not out.exists():
            print("error: joining the segments failed; the segments are kept, re-run the build to try again")
            return rc or 1
        n = frames_of(out)
        if n != total:
            out.unlink(missing_ok=True)
            print(f"error: the joined track has {n} frames, expected {total}; segments kept in {studio.rel_path(chunks)}")
            return 1
        print(f"[joined] {studio.rel_path(out)}: {n} frames from {len(plan)} segments")
        if not a.keep:
            shutil.rmtree(chunks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
