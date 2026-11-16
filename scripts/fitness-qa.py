#!/usr/bin/env python3
"""fitness-qa.py: automated render diagnostics for a finished fitness film or clip. Objective checks only: they can fail a render, they can never pass its teaching.

    .venv/bin/python scripts/fitness-qa.py out/lab-3d-review/1-curl-3d.mp4 [more.mp4 ...] [--fps 30] [--expect-audio] [--period 2.9]
            [--cuts N] [--allow-hold 1.5] [--json qa/fitness-render-qa/] [--loudness -16]

What it measures (ffmpeg + numpy; no browser):
  container   h264 yuv420p, r_frame_rate == avg_frame_rate == --fps, frame count against duration, video/audio duration within 0.12 s (A/V sync),
              frame-rate tokens in the title/comment metadata and in the file name must say the real rate, no decode errors
  frozen      freezedetect: a still stretch longer than --allow-hold s (the last 2.5 s are exempt: end cards hold) = narration over a static frame
  black/blank black frames (blackdetect) and near-uniform frames (sampled), anywhere
  start       frame 0 must not be black/blank, and must not jump: the 0.2 s after it may not change more than 4x the film's typical step (a stale pose snapping in)
  cuts        scene cuts (select scene>0.30); --cuts N asserts the count (a single-exercise clip has none: an orbit is not a cut)
  motion      the share of seconds in the picture's centre that visibly move (an exercise that does not move fails here)
  rhythm      with --period P, the dominant repetition period of the motion energy must be within 12% of P (the reps really repeat on the tempo)
  loudness    integrated loudness within --tolerance LU of --loudness when there is audio
Not covered (needs the DOM or a human): text outside safe areas, overlapping labels, anatomical accuracy. frame-review.py / hyperframes snapshot + the
creative and fitness rubrics own those; do not read a pass here as approval of the film.
Exit 1 when any check fails.
"""
import argparse
import json
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(p):
    r = sh(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(p)])
    return json.loads(r.stdout)


def gray_frames(p, fps, w=108, start=None, frames=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(start)] if start else []) + ["-i", str(p), "-vf", f"fps={fps},scale={w}:-2,format=gray"] + (["-frames:v", str(frames)] if frames else []) + ["-f", "rawvideo", "-"]
    r = subprocess.run(cmd, capture_output=True)
    pr = probe(p)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    h = int(round(int(v["height"]) * w / int(v["width"]) / 2) * 2)
    a = np.frombuffer(r.stdout, np.uint8)
    n = a.size // (w * h)
    return a[: n * w * h].reshape(n, h, w).astype(np.float32)


def check(path: Path, o) -> dict:
    res = {"file": str(path), "failures": [], "notes": [], "stats": {}}
    bad = res["failures"].append
    info = probe(path)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"]["duration"])
    r, avg = Fraction(v["r_frame_rate"]), Fraction(v["avg_frame_rate"])
    res["stats"]["container"] = {"codec": v["codec_name"], "pix_fmt": v.get("pix_fmt"), "size": f"{v['width']}x{v['height']}", "r_frame_rate": str(r), "avg_frame_rate": f"{float(avg):.3f}",
                                 "duration": round(dur, 3), "audio": bool(a)}
    if v["codec_name"] != "h264" or v.get("pix_fmt") != "yuv420p":
        bad(f"encoding is {v['codec_name']} {v.get('pix_fmt')} (expected h264 yuv420p)")
    if abs(float(r) - o.fps) > 0.01 or abs(float(avg) - o.fps) > 0.05:
        bad(f"frame rate: r_frame_rate {r}, avg {float(avg):.3f}, expected {o.fps:g}")
    nb = int(v.get("nb_frames") or 0)
    if nb and abs(nb - dur * o.fps) > 2.5:
        bad(f"frame count {nb} does not match {dur:.3f} s at {o.fps:g} fps ({dur * o.fps:.1f})")
    tags = " ".join(str(x) for x in (info["format"].get("tags") or {}).values()) + " " + path.name
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*fps", tags, re.I):
        if abs(float(m.group(1)) - o.fps) > 0.01:
            bad(f"metadata or file name says {m.group(0)} but the film is {o.fps:g} fps")
    if o.expect_audio and not a:
        bad("no audio stream (this production needs sound)")
    if a:
        da = float(a.get("duration") or dur)
        res["stats"]["container"]["audio_duration"] = round(da, 3)
        if abs(da - float(v.get("duration") or dur)) > 0.12:
            bad(f"A/V sync: audio {da:.3f} s vs video {float(v.get('duration') or dur):.3f} s")
    dec = sh(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"]).stderr.strip()
    if dec:
        bad("decode errors: " + dec.splitlines()[0][:120])

    # frozen stretches
    fz = sh(["ffmpeg", "-i", str(path), "-vf", "freezedetect=n=-58dB:d=0.8", "-an", "-f", "null", "-"]).stderr
    starts = [float(x) for x in re.findall(r"freeze_start: ([0-9.]+)", fz)]
    ends = [float(x) for x in re.findall(r"freeze_end: ([0-9.]+)", fz)]
    holds = []
    for i, s0 in enumerate(starts):
        e0 = ends[i] if i < len(ends) else dur
        holds.append((round(s0, 2), round(e0, 2)))
    bad_holds = [h for h in holds if (h[1] - h[0]) > o.allow_hold and h[0] < dur - 2.5]
    res["stats"]["frozen"] = {"intervals": holds, "over_limit": bad_holds}
    for h in bad_holds:
        bad(f"frozen picture {h[0]}-{h[1]} s ({h[1] - h[0]:.1f} s > {o.allow_hold:g} s): narration over a static frame")

    # black and blank
    bl = sh(["ffmpeg", "-i", str(path), "-vf", "blackdetect=d=0.15:pix_th=0.08", "-an", "-f", "null", "-"]).stderr
    blacks = re.findall(r"black_start:([0-9.]+) black_end:([0-9.]+)", bl)
    res["stats"]["black"] = blacks
    if blacks:
        bad(f"black frames at {', '.join(b[0] + '-' + b[1] + ' s' for b in blacks)}")
    F = gray_frames(path, 10)
    res["stats"]["sampled_frames"] = int(F.shape[0])
    flat = [round(i / 10, 1) for i in range(F.shape[0]) if F[i].std() < 2.0]
    if flat:
        bad(f"blank (uniform) frames at {flat[:6]} s")

    # first frame and the jump after it
    G = gray_frames(path, o.fps, frames=12)
    if G.shape[0] >= 8:
        if G[0].std() < 2.0:
            bad("frame 0 is blank or black")
        h0, w0 = G[0].shape
        roi = (slice(int(h0 * 0.27), int(h0 * 0.68)), slice(int(w0 * 0.1), int(w0 * 0.9)))      # above the caption band: a caption popping in when speech starts is design, not a stale pose
        step = [np.abs(G[i][roi] - G[i - 1][roi]).mean() for i in range(1, G.shape[0])]
        j = np.abs(G[6][roi] - G[0][roi]).mean()
        typical = max(0.3, float(np.median(np.abs(np.diff(F[:, roi[0], roi[1]], axis=0)).mean(axis=(1, 2)))) / 3) if F.shape[0] > 3 else 0.3
        res["stats"]["start"] = {"change_first_0.2s": round(float(j), 2), "typical_3_frame_step": round(typical, 2)}
        if j > 4 * typical + 1.5 and j > 3.0:
            bad(f"frame 0 jumps: the next 0.2 s change {j:.1f} vs a typical {typical:.1f} (a stale pose snapping to the start pose?)")

    # cuts
    cu = sh(["ffmpeg", "-i", str(path), "-vf", "select='gt(scene,0.30)',metadata=print:file=-", "-an", "-f", "null", "-"])
    cuts = [round(float(x), 2) for x in re.findall(r"pts_time:([0-9.]+)", cu.stdout + cu.stderr)]
    res["stats"]["cuts"] = cuts
    if o.cuts is not None and len(cuts) != o.cuts:
        bad(f"{len(cuts)} scene cut(s) at {cuts} but {o.cuts} expected")

    # motion presence and rhythm (centre of the picture, 10 fps)
    h1, w1 = F.shape[1], F.shape[2]
    c = F[:, int(h1 * 0.27):int(h1 * 0.68), int(w1 * 0.1):int(w1 * 0.9)]      # above the caption band (captions change every ~1.7 s and would drown the reps)
    energy = np.abs(np.diff(c, axis=0)).mean(axis=(1, 2))
    if energy.size > 20:
        sec = [energy[i:i + 10].mean() for i in range(5, energy.size - 5, 10)]
        moving = sum(1 for x in sec if x > 0.25) / max(1, len(sec))
        res["stats"]["motion"] = {"share_of_seconds_moving": round(moving, 2)}
        if moving < o.motion:
            bad(f"only {moving:.0%} of the seconds show motion (needs {o.motion:.0%}): the exercise barely moves")
        if o.period:
            e = energy - energy.mean()
            ac = np.correlate(e, e, "full")[e.size - 1:]
            lo, hi = int(o.period * 10 * 0.6), min(ac.size - 1, int(o.period * 10 * 1.4))
            if hi > lo + 2:
                lag = (int(np.argmax(ac[lo:hi])) + lo) / 10
                res["stats"]["rhythm"] = {"dominant_period_s": lag, "expected": o.period}
                if abs(lag - o.period) > 0.12 * o.period:
                    bad(f"repetition period {lag:.1f} s but the tempo is {o.period:g} s")

    # loudness
    if a:
        eb = sh(["ffmpeg", "-i", str(path), "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"]).stderr
        m = re.findall(r"I:\s+(-?[0-9.]+) LUFS", eb)
        if m:
            lufs = float(m[-1])
            res["stats"]["loudness_lufs"] = lufs
            if abs(lufs - o.loudness) > o.tolerance:
                bad(f"integrated loudness {lufs:.1f} LUFS is outside {o.loudness:g} +/- {o.tolerance:g}")
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--expect-audio", action="store_true")
    ap.add_argument("--period", type=float, default=None)
    ap.add_argument("--cuts", type=int, default=None)
    ap.add_argument("--allow-hold", type=float, default=1.5)
    ap.add_argument("--motion", type=float, default=0.85)
    ap.add_argument("--loudness", type=float, default=-16.0)
    ap.add_argument("--tolerance", type=float, default=2.0)
    ap.add_argument("--json", default=None, help="directory to write <name>.json reports into")
    o = ap.parse_args()
    results = [check(Path(p), o) for p in o.videos]
    for r in results:
        print(f"{'FAIL' if r['failures'] else 'ok  '} {r['file']}")
        c = r["stats"]["container"]
        print(f"     {c['size']} {c['r_frame_rate']} fps {c['duration']} s audio={c['audio']}  frozen={len(r['stats']['frozen']['over_limit'])} cuts={len(r['stats']['cuts'])} "
              f"motion={r['stats'].get('motion', {}).get('share_of_seconds_moving')} lufs={r['stats'].get('loudness_lufs')}")
        for f in r["failures"]:
            print("     FAIL:", f)
        if o.json:
            Path(o.json).mkdir(parents=True, exist_ok=True)
            (Path(o.json) / (Path(r["file"]).stem + ".json")).write_text(json.dumps(r, indent=1))
    return 1 if any(r["failures"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
