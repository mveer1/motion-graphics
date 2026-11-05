#!/usr/bin/env python3
"""Revise one scene without re-rendering the whole film.

  scene-revise.py <slug> --scene s3 [--format landscape] [--pad 1.4] [--crf 14] [--dry-run] [--no-mux]

Renders only the time range of the scene (plus `--pad` seconds each side, because a transition centred on a
scene boundary reaches into its neighbours), splices that clip into renders/<format>/visuals.mp4 at exact frame
boundaries with ffmpeg, keeps the previous visuals as visuals.prev.mp4, and re-runs the studio's mux step.

After the splice it re-stamps renders/<format>/visuals.stamp.json for the edited composition (recording the
spliced range), so the mux build that follows reuses the spliced track instead of seeing a stale render and
re-rendering the whole film. It refuses when the runtime (src/_studio/) changed since the render: that touches
every scene.

What it does NOT do: the splice re-encodes the whole picture track once (so pixels outside the range are visually
identical but not bit-identical; the report prints the measured difference), and it cannot detect which scene a
code edit affected: you name the scene. If a change alters timing outside the padded range, do a full build.
Needs the render host (hyperframes, ffmpeg). One render at a time: the render runs under session-guard's lock.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "pipeline"))
PROJECTS = ROOT / "projects"


def load(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def project_dir(s: str) -> Path:
    if (PROJECTS / s).is_dir():
        return PROJECTS / s
    p = Path(s)
    if p.is_dir():
        return p.resolve()
    hits = [d for d in PROJECTS.glob(f"*/{s}") if d.is_dir()]
    if len(hits) == 1:
        return hits[0]
    sys.exit(f"error: project {s!r} not found")


def frames_of(path: Path) -> int:
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return int(r.stdout.strip())


def studio_module():
    spec = importlib.util.spec_from_file_location("studio", ROOT / "scripts" / "studio.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(cmd, cwd=None, guarded=False) -> int:
    if guarded:
        cmd = [sys.executable, str(ROOT / "scripts" / "session-guard.py"), "run", "render", "--"] + cmd
    print("$", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, cwd=cwd, stdin=subprocess.DEVNULL).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug"); ap.add_argument("--scene", required=True); ap.add_argument("--format")
    ap.add_argument("--pad", type=float, default=1.4); ap.add_argument("--crf", type=int, default=14)
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--no-mux", action="store_true")
    a = ap.parse_args()
    pdir = project_dir(a.slug)
    project, sb = load(pdir / "project.json"), load(pdir / "storyboard.json")
    scene = next((s for s in sb["scenes"] if s["id"] == a.scene), None)
    if not scene:
        sys.exit(f"error: scene {a.scene!r} not in storyboard: {[s['id'] for s in sb['scenes']]}")
    fmt = a.format or next((f["id"] for f in project["formats"] if f.get("primary")), project["formats"][0]["id"])
    studio = studio_module()
    entry = next(f for f in studio.format_entries(project) if f["id"] == fmt)
    quality = project.get("quality", "looks")
    fps = project["fps"]
    dur = project["duration_sec"]
    n_total = round(dur * fps)
    f0 = max(0, round((scene["start_sec"] - a.pad) * fps))
    f1 = min(n_total, round((scene["end_sec"] + a.pad) * fps))
    t0, t1 = f0 / fps, f1 / fps
    renders = pdir / "renders" / fmt
    visuals = renders / "visuals.mp4"
    seg = renders / "segments" / f"{a.scene}.mp4"
    comp = entry["file"]
    print(f"scene {a.scene}: {scene['start_sec']}-{scene['end_sec']} s; re-rendering {t0:.2f}-{t1:.2f} s (frames {f0}-{f1}) of {dur} s = {100 * (t1 - t0) / dur:.0f}% of the film")
    if a.dry_run:
        return 0
    if not visuals.exists():
        sys.exit(f"error: {visuals} does not exist; do a full build first")
    # an edit to index.html reaches index.<format>.html only through `formats`
    if run([sys.executable, str(ROOT / "scripts" / "studio.py"), "formats", pdir.name]) != 0:
        sys.exit("error: `studio.py formats` failed; visuals untouched")
    stamp_path = renders / studio.STAMP_NAME
    old_stamp = load(stamp_path) if stamp_path.exists() else {}
    inputs = studio.render_inputs(pdir, entry)
    changed = studio.changed_inputs(old_stamp.get("inputs"), inputs)
    if changed is None:
        sys.exit(f"error: {visuals} has no build stamp listing its inputs, so a splice cannot be checked; do a full build")
    if any(c.startswith(studio.RUNTIME_DIRNAME + "/") for c in changed):
        sys.exit(f"error: the runtime changed since this render ({', '.join(c for c in changed if c.startswith(studio.RUNTIME_DIRNAME + '/'))}); "
                 "that affects every scene: do a full build")
    print(f"changed since the render: {', '.join(changed) or 'nothing'}")
    seg.parent.mkdir(parents=True, exist_ok=True)
    if seg.exists():
        seg.unlink()
    rc = run(["hyperframes", "render", str((pdir / "src").resolve()), "--composition", comp, "--fps", str(fps), "--quality", quality, "--low-memory-mode",
              "--start", f"{t0:.4f}", "--end", f"{t1:.4f}", "--output", str(seg.resolve())], guarded=True)
    if rc != 0 or not seg.exists():
        sys.exit("error: partial render failed; visuals untouched")
    n_seg = frames_of(seg)
    if n_seg != f1 - f0:
        sys.exit(f"error: segment has {n_seg} frames, expected {f1 - f0}; visuals untouched (odd fps or an end-of-film clamp: do a full build)")
    new = renders / "visuals.new.mp4"
    parts = []
    fc = []
    if f0 > 0:
        fc.append(f"[0:v]trim=end_frame={f0},setpts=PTS-STARTPTS[a]"); parts.append("[a]")
    fc.append("[1:v]setpts=PTS-STARTPTS[b]"); parts.append("[b]")
    if f1 < n_total:
        fc.append(f"[0:v]trim=start_frame={f1},setpts=PTS-STARTPTS[c]"); parts.append("[c]")
    fc.append("".join(parts) + f"concat=n={len(parts)}:v=1:a=0,format=yuv420p[v]")
    rc = run(["ffmpeg", "-y", "-v", "error", "-i", str(visuals), "-i", str(seg), "-filter_complex", ";".join(fc), "-map", "[v]", "-r", str(fps), "-c:v", "libx264", "-crf", str(a.crf), "-preset", "slow", "-movflags", "+faststart", str(new)])
    if rc != 0 or not new.exists():
        sys.exit("error: splice failed; visuals untouched")
    if frames_of(new) != frames_of(visuals):
        new.unlink()
        sys.exit("error: spliced track has a different frame count; visuals untouched")
    prev = renders / "visuals.prev.mp4"
    if prev.exists():
        prev.unlink()
    shutil.move(str(visuals), str(prev))
    shutil.move(str(new), str(visuals))
    spliced = old_stamp.get("spliced", []) + [{"scene": a.scene, "frames": [f0, f1], "changed": changed,
                                                "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}]
    studio.write_render_stamp(pdir, fmt, studio.render_fingerprint(pdir, entry, fps, quality, inputs), inputs,
                              {"spliced": spliced})
    print(f"spliced. previous track kept at {prev.relative_to(ROOT)}; stamp updated so the mux build reuses this track")
    try:
        import numpy as np
        import videoscan as vs
        old, cur = vs.luma_stream(str(prev)).astype(np.float32), vs.luma_stream(str(visuals)).astype(np.float32)
        d = np.abs(old - cur).mean(axis=(1, 2))
        outside = np.concatenate([d[:f0], d[f1:]]) if f0 or f1 < len(d) else np.array([0.0])
        print(f"measured change outside the range: mean |luma diff| {outside.mean():.3f}/255, max {outside.max():.3f}; inside: mean {d[f0:f1].mean():.3f}, max {d[f0:f1].max():.3f}")
    except Exception as exc:  # verification is advisory
        print("note: verification skipped:", exc)
    if not a.no_mux:
        final = renders / "final.mp4"
        if final.exists():
            final.unlink()
        rc = run([sys.executable, str(ROOT / "scripts" / "studio.py"), "build", pdir.name, "--formats", fmt], guarded=True)
        if rc != 0:
            sys.exit("error: re-mux failed; the spliced visuals are in place")
    return 0


if __name__ == "__main__":
    sys.exit(main())
