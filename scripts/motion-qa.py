#!/usr/bin/env python3
"""Motion QA: surface problems with numbers, never certify quality.

  video <file.mp4>        [--project SLUG] [--expect-size WxH] [--expect-fps N] [--expect-duration S] [--expect-audio] [--lufs -16]
  composition <index.html|SLUG> [--format landscape|portrait|square]
  project <SLUG> [--video file.mp4] [--format F]      both of the above, plus the critique pack
  critique-pack <SLUG> --video file.mp4               contact sheet, seam strips and per-beat questions only

Findings fall into three classes that are never blurred (specs/qa-report-spec.json):
  objective   a spec or decode failure: the file is wrong (wrong size, no audio when required, black gap)
  measured    a number against a stated threshold: a LEAD to look at, never a verdict
  judgment    artistic questions a script cannot answer: emitted as prompts for a critic (model or human)
A finding can be waived only by a recorded intent (storyboard scene `intent`, a declared capability such as
frame-hud or caption-band); waived findings stay in the report with the waiver named.
`technical_pass` means: no objective failure and every check that was required actually ran. It says nothing
about whether the film is good. Exit status is 1 only for objective failures.

Thresholds are starting values, mostly drawn from this workspace's own measurements (see the report); where a
number comes from Motionmaxxing's unreproduced corpus it says so. Run with .venv/bin/python.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "pipeline"))

import numpy as np  # noqa: E402

import colorscience as cs  # noqa: E402
import videoscan as vs  # noqa: E402

TOOL = {"name": "motion-qa", "version": "1.0"}
PRESETS = json.loads((ROOT / "specs" / "format-presets.json").read_text())
SAME_STRUCTURE = 0.05      # ink-map distance below which two frames share one composition (re-skin control measured 0.023; unrelated >= 0.15)
STATIC_WARN_SEC, STATIC_NOTE_SEC = 2.0, 1.2
CORNER = (0.2, 0.14)       # x fraction, y fraction defining corner zones (HUD-label heuristic)


def load_json(p: Path) -> Any:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def project_dir(s: str) -> Path:
    p = Path(s)
    if p.is_dir():
        return p
    if (ROOT / "projects" / s).is_dir():
        return ROOT / "projects" / s
    hits = [d for d in (ROOT / "projects").glob(f"*/{s}") if d.is_dir()]
    if len(hits) == 1:
        return hits[0]
    sys.exit(f"error: project {s!r} not found")


class Report:
    def __init__(self, target: Dict[str, Any]):
        self.target, self.findings, self.checks, self.artifacts, self.prompts = target, [], [], {}, []
        self.expect: Dict[str, Any] = {}

    def check(self, cid: str, status: str, reason: str = "", elapsed: float = 0.0) -> None:
        c = {"id": cid, "status": status}
        if reason:
            c["reason"] = reason
        if elapsed:
            c["elapsed_sec"] = round(elapsed, 2)
        self.checks.append(c)

    def add(self, fid: str, cls: str, sev: str, msg: str, evidence: Optional[Dict[str, Any]] = None, t: Optional[float] = None,
            rng: Optional[Tuple[float, float]] = None, beat: Optional[str] = None, suggestion: Optional[str] = None,
            waivers: Optional[Dict[str, str]] = None) -> None:
        f: Dict[str, Any] = {"id": fid, "class": cls, "severity": sev, "message": msg}
        if evidence:
            f["evidence"] = evidence
        if t is not None:
            f["t_sec"] = round(t, 3)
        if rng:
            f["range_sec"] = [round(rng[0], 3), round(rng[1], 3)]
        if beat:
            f["beat"] = beat
        if suggestion:
            f["suggestion"] = suggestion
        if waivers and fid in waivers:
            f["waived_by"] = {"intent": waivers[fid].split("@")[0], "source": waivers[fid].split("@")[1] if "@" in waivers[fid] else "storyboard"}
        self.findings.append(f)

    def doc(self) -> Dict[str, Any]:
        live = [f for f in self.findings if "waived_by" not in f]
        obj = sum(1 for f in live if f["class"] == "objective" and f["severity"] == "fail")
        required_missing = [c for c in self.checks if c["status"] != "ran" and c.get("required")]
        out = {"spec_version": 1, "target": self.target, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tool": {**TOOL, "host": "darwin"},
               "expectations": self.expect, "checks_run": [{k: v for k, v in c.items() if k != "required"} for c in self.checks], "findings": self.findings,
               "summary": {"objective_failures": obj, "measured_warnings": sum(1 for f in live if f["class"] == "measured" and f["severity"] == "warn"),
                           "judgment_questions": sum(1 for f in live if f["class"] == "judgment"), "waived": len(self.findings) - len(live),
                           "technical_pass": bool(obj == 0 and not required_missing)}}
        if self.artifacts:
            out["artifacts"] = self.artifacts
        if self.prompts:
            out["critique_prompts"] = self.prompts
        return out


# ---------------------------------------------------------------------------------------------- context
class Context:
    """Everything the checks may know about intent: storyboard scenes, waivers, narration windows, expectations."""

    def __init__(self, pdir: Optional[Path], fmt: Optional[str]):
        self.pdir, self.fmt = pdir, fmt
        self.scenes: List[Dict[str, Any]] = []
        self.caps: Dict[str, set] = {}
        self.intent: Dict[str, str] = {}
        self.narr: List[Tuple[float, float, str, str]] = []
        self.project: Dict[str, Any] = {}
        if not pdir:
            return
        if (pdir / "project.json").exists():
            self.project = load_json(pdir / "project.json")
        if (pdir / "storyboard.json").exists():
            self.scenes = load_json(pdir / "storyboard.json")["scenes"]
            for s in self.scenes:
                self.caps[s["id"]] = set(s.get("capabilities", []))
                if s.get("intent"):
                    self.intent[s["id"]] = s["intent"]
        tl = pdir / "audio" / "timeline.json"
        if tl.exists():
            for s in load_json(tl).get("scenes", []):
                self.narr.append((s["start_time_sec"], s["end_time_sec"], s["id"], s.get("text", "")))

    def scene_at(self, t: float) -> Optional[Dict[str, Any]]:
        for s in self.scenes:
            if s["start_sec"] <= t < s["end_sec"]:
                return s
        return None

    def narrating(self, t0: float, t1: float) -> bool:
        return any(a < t1 and b > t0 for a, b, _, _ in self.narr) if self.narr else False

    def size_for(self, fmt: Optional[str]) -> Tuple[int, int]:
        fmt = fmt or self.fmt
        for f in self.project.get("formats", []):
            if f["id"] == fmt or (fmt is None and f.get("primary")):
                return f["width"], f["height"]
        return PRESETS["formats"].get(fmt or "landscape", PRESETS["formats"]["landscape"])["sizes"]["720p"]


def waiver_map(ctx: Context, scene_ids: List[str]) -> Dict[str, str]:
    w: Dict[str, str] = {}
    caps = set().union(*[ctx.caps.get(s, set()) for s in scene_ids]) if scene_ids else set()
    if "frame-hud" in caps:
        w["hud-label"] = "capability:frame-hud@storyboard"
    if caps & {"progress-stepper", "step-header"}:
        w["chapter-counter"] = "capability:progress-stepper@storyboard"
    if "caption-band" in caps:
        w["text-echoes-narration"] = "capability:caption-band@storyboard"
    return w


# ---------------------------------------------------------------------------------------------- video checks
def video_checks(rep: Report, ctx: Context, path: Path, a: argparse.Namespace) -> Optional[Dict[str, Any]]:
    t0 = time.time()
    if not vs.have_ffmpeg():
        rep.check("video-decode", "unavailable", "ffmpeg/ffprobe not found", 0)
        rep.checks[-1]["required"] = True
        return None
    try:
        info = vs.probe(str(path))
        frames = vs.luma_stream(str(path))
    except vs.ScanError as e:
        rep.add("decode", "objective", "fail", f"cannot decode: {e}")
        rep.check("video-decode", "ran", "", time.time() - t0)
        return None
    rep.check("video-decode", "ran", "", time.time() - t0)
    fps = info.get("fps") or 30.0
    n = len(frames)
    dur = n / fps
    rep.target["sha256"] = vs_sha(path)
    # --- spec
    exp_w, exp_h = (a.expect_size.split("x") if a.expect_size else (None, None))
    if not a.expect_size and ctx.pdir:
        w, h = ctx.size_for(a.format)
        exp_w, exp_h = str(w), str(h)
    exp_fps = a.expect_fps or ctx.project.get("fps")
    exp_dur = a.expect_duration or ctx.project.get("duration_sec")
    rep.expect = {k: v for k, v in {"width": exp_w and int(exp_w), "height": exp_h and int(exp_h), "fps": exp_fps, "duration_sec": exp_dur,
                                    "audio": bool(a.expect_audio)}.items() if v not in (None, False)}
    if exp_w and (info["width"], info["height"]) != (int(exp_w), int(exp_h)):
        rep.add("size", "objective", "fail", f"{info['width']}x{info['height']} but {exp_w}x{exp_h} expected", {"actual": [info["width"], info["height"]]})
    if exp_fps and abs(fps - float(exp_fps)) > 0.01:
        rep.add("fps", "objective", "fail", f"{fps} fps but {exp_fps} expected")
    if exp_dur and abs(dur - float(exp_dur)) > 0.15:
        rep.add("duration", "objective", "fail", f"{dur:.2f}s but {float(exp_dur):.2f}s expected (tolerance 0.15 s)", {"frames": n, "fps": fps})
    rep.check("spec-compliance", "ran")
    # --- black / dark / flat
    diff, corr = vs.frame_metrics(frames)
    true_black = vs.black_runs(frames)
    for s, e in true_black:
        a_, b_ = s / fps, (e + 1) / fps
        edge = s == 0 or e >= n - 1
        if not edge and b_ - a_ >= 0.2:
            rep.add("black-gap", "objective", "fail", f"{b_ - a_:.2f}s of true black (mean luma <= 2, no pixel above 24) inside the film", {"mean_luma_max": 2, "peak_max": 24}, rng=(a_, b_), suggestion="a scene switch or opacity chain left nothing visible")
        elif edge and b_ - a_ >= 0.5:
            rep.add("black-edge", "measured", "warn", f"{b_ - a_:.2f}s of true black at the {'start' if s == 0 else 'end'}", rng=(a_, b_))
    for s, e in vs.black_runs(frames, 8.0, 3, None):
        a_, b_ = s / fps, (e + 1) / fps
        if b_ - a_ >= 1.5 and not any(s2 <= s and e <= e2 for s2, e2 in true_black):
            sc = ctx.scene_at((a_ + b_) / 2)
            w = {"very-dark": f"intent:dark@storyboard"} if (sc and ctx.intent.get(sc["id"]) == "dark") else None
            rep.add("very-dark", "measured", "warn", f"{b_ - a_:.1f}s where the whole frame is very dark (mean luma <= 8/255)", {"mean_luma_max": 8, "min_sec": 1.5}, rng=(a_, b_), beat=sc["id"] if sc else None,
                    suggestion="check it reads on a phone in daylight; declare intent: dark if the darkness is the point", waivers=w)
    for s, e in vs.flat_runs(frames, 1.5, 8, 4):
        a_, b_ = s / fps, (e + 1) / fps
        if not any(s2 <= s and e <= e2 for s2, e2 in vs.black_runs(frames, 8.0, 3, None)):
            rep.add("flat-frame", "measured", "warn", f"{b_ - a_:.2f}s of one flat field (nothing drawn)", {"luma_std_max": 1.5}, rng=(a_, b_))
    rep.check("black-and-flat-frames", "ran")
    # --- static holds: low per-frame change AND low accumulated change (a slow drift is alive, not frozen)
    motion = vs.motion_summary(frames, fps)
    LAG = max(2, int(0.5 * fps))
    ALIVE, FROZEN = 0.8, 0.3
    for s, e in vs.runs_below(diff, 0.35, int(1.2 * fps)):
        a_, b_ = s / fps, (e + 1) / fps
        length = b_ - a_
        if length < STATIC_NOTE_SEC:
            continue
        lag_e = vs.lag_energy(frames, s, e, LAG)
        sc = ctx.scene_at((a_ + b_) / 2)
        narr_known = bool(ctx.narr)
        narr = ctx.narrating(a_, b_) if narr_known else bool(info["has_audio"])  # unknown narration + an audio track: assume it may be speaking
        end_hold = e >= n - 2
        ev = {"mean_diff_max": 0.35, "lag_0.5s_energy": round(lag_e, 3), "alive_above": ALIVE, "frozen_below": FROZEN, "narration_overlap": narr, "narration_known": narr_known,
              "calibration": "frozen stretches measured 0.06-0.10, slow drifts 0.9-1.9"}
        if lag_e >= ALIVE:
            if length >= STATIC_WARN_SEC:
                rep.add("slow-drift", "measured", "note", f"{length:.1f}s of slow drift (per-frame change tiny, but the picture moves: lag energy {lag_e:.2f})", ev, rng=(a_, b_), beat=sc["id"] if sc else None)
            continue
        sev = "warn" if (length >= STATIC_WARN_SEC and narr and not end_hold) else "note"
        kind = "frozen" if lag_e < FROZEN else "low-energy"
        w = {}
        if sc and ctx.intent.get(sc["id"]) in ("still", "minimal"):
            w["static-hold"] = f"intent:{ctx.intent[sc['id']]}@storyboard"
        rep.add("static-hold", "measured", sev, f"picture {kind} for {length:.2f}s" + ((" while narration speaks" if narr_known else " with an audio track playing (narration map unknown)") if narr else "") + (" at the end of the film" if end_hold else ""),
                ev, rng=(a_, b_), beat=sc["id"] if sc else None,
                suggestion="keep one living element (drift, light, a counter) or declare intent: still", waivers=w)
    rep.check("static-holds", "ran")
    # --- repeated composition: one mid-scene frame per scene (or per detected shot)
    spans = [(s["start_sec"], s["end_sec"], s["id"]) for s in ctx.scenes] if ctx.scenes else []
    if not spans:
        cuts = [0.0] + [c / fps for c in vs.detect_cuts(diff, corr)] + [dur]
        spans = [(cuts[i], cuts[i + 1], f"shot{i + 1}") for i in range(len(cuts) - 1) if cuts[i + 1] - cuts[i] > 0.5]
    if len(spans) < 6 and not ctx.scenes:  # hard cuts alone under-sample soft-transition films: use even slices instead
        k = max(6, min(12, int(dur // 4)))
        spans = [(dur * i / k, dur * (i + 1) / k, f"t{dur * i / k:.0f}s") for i in range(k)]
    tmp = Path(tempfile.mkdtemp(prefix="mqa-"))
    sheet_frames, labels, maps = [], [], []
    try:
        times = [(a_ + b_) / 2 for a_, b_, _ in spans if b_ - a_ > 0.3]
        ids = [i for a_, b_, i in spans if b_ - a_ > 0.3]
        pngs = vs.sample_frames(str(path), times, tmp, 480) if times else []
        for p_, i, t in zip(pngs, ids, times):
            maps.append(cs.ink_map(cs.load_rgb(str(p_), 480)))
            sheet_frames.append(p_); labels.append(f"{i} {t:.1f}s")
        if len(maps) >= 3:
            n_ = len(maps)
            D = np.array([[cs.structure_distance(maps[i], maps[j]) for j in range(n_)] for i in range(n_)])
            groups, seen = [], set()
            for i in range(n_):
                if i in seen:
                    continue
                g = [j for j in range(n_) if D[i, j] < SAME_STRUCTURE]
                if len(g) >= 3:
                    groups.append(g)
                    seen.update(g)
            for g in groups:
                gid = [ids[j] for j in g]
                share = len(g) / n_
                rep.add("repeat-composition", "measured", "warn" if share >= 0.5 or len(g) >= 4 else "note",
                        f"{len(g)} of {n_} scenes share one composition ({', '.join(gid)})", {"ink_map_distance_below": SAME_STRUCTURE, "calibration": "re-skin control 0.023, unrelated layouts >= 0.15"},
                        suggestion="vary hero position, scale and structure, or declare the repetition as a deliberate system")
            rep.check("repeated-composition", "ran")
        else:
            rep.check("repeated-composition", "skipped", "fewer than three scenes or shots")
        if sheet_frames:
            out_dir = (ctx.pdir / "qa" / "motion") if ctx.pdir else path.parent
            out_dir.mkdir(parents=True, exist_ok=True)
            sheet = vs.contact_sheet(sheet_frames, labels, out_dir / "scene-sheet.jpg", cols=4, thumb_w=360)
            rep.artifacts["scene_sheet"] = str(sheet.relative_to(ROOT)) if sheet.is_relative_to(ROOT) else str(sheet)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    # --- seams and scene durations (planning evidence)
    types = [s.get("transition_out", {}).get("type") for s in ctx.scenes[:-1]] if ctx.scenes else []
    if len(types) >= 4:
        top, cnt = Counter(types).most_common(1)[0]
        if cnt / len(types) > 0.6:
            rep.add("repeat-transition", "measured", "warn", f"transition '{top}' used at {cnt} of {len(types)} scene boundaries", {"types": types},
                    suggestion="vary the seam or state why one device is the film's system")
        rep.check("transition-variety", "ran")
    else:
        rep.check("transition-variety", "skipped", "storyboard missing or fewer than five scenes")
    if ctx.scenes:
        durs = [s["end_sec"] - s["start_sec"] for s in ctx.scenes]
        for s, d in zip(ctx.scenes, durs):
            if d < 1.0 or d > 20:
                rep.add("scene-duration", "measured", "note", f"scene {s['id']} lasts {d:.1f}s", {"seconds": round(d, 2)}, beat=s["id"])
        rep.check("scene-durations", "ran")
    # --- end hold and motion summary (descriptive)
    trailing = 0
    for i in range(n - 1, 0, -1):
        if diff[i] < 0.35:
            trailing += 1
        else:
            break
    if trailing / fps > 1.4:
        rep.add("end-hold", "measured", "note", f"the picture is unchanged for the last {trailing / fps:.1f}s", {"threshold_sec": 1.4, "source": "Motionmaxxing G3, adopted-unverified"})
    rep.add("motion-energy", "measured", "note", f"median frame-to-frame luma change {motion['motion_median']}/255, {motion['static_share'] * 100:.0f}% of frames static, median shot {motion['shot_length_median_sec']}s",
            {k: motion[k] for k in ("motion_mean_luma_diff", "motion_median", "motion_p90", "static_share", "cut_count", "cuts_per_min")})
    # --- audio
    t1 = time.time()
    if info["has_audio"]:
        lou = vs.loudness(str(path)) or {}
        tgt = a.lufs if a.lufs is not None else ctx.project.get("audio", {}).get("loudness_target_lufs", -16)
        tol = ctx.project.get("audio", {}).get("loudness_tolerance_lu", 2)
        i_ = lou.get("integrated_lufs")
        if i_ is not None and abs(i_ - tgt) > tol:
            rep.add("loudness", "measured", "warn", f"integrated loudness {i_} LUFS vs target {tgt} +/- {tol}", lou)
        if lou.get("true_peak_dbtp") is not None and lou["true_peak_dbtp"] > -1.0:
            rep.add("true-peak", "measured", "warn", f"true peak {lou['true_peak_dbtp']} dBTP exceeds -1.0", lou)
        sil = vs.silence_ranges(str(path), -50.0, 0.5)
        if sil and sil[-1][1] >= info["duration_sec"] - 0.05 and sil[-1][1] - sil[-1][0] > 0.5:
            rep.add("silent-tail", "measured", "note", f"{sil[-1][1] - sil[-1][0]:.1f}s of silence at the end", rng=sil[-1])
        mid = [s for s in sil if s[0] > 0.3 and s[1] < info["duration_sec"] - 0.3 and s[1] - s[0] > 1.5]
        for s in mid:
            rep.add("audio-gap", "measured", "note", f"{s[1] - s[0]:.1f}s of silence mid-film", rng=s)
        if abs(info["duration_sec"] - dur) > 0.15 and exp_dur:
            rep.add("av-length", "measured", "warn", f"video {dur:.2f}s vs container {info['duration_sec']:.2f}s")
        rep.check("audio-levels", "ran", "", time.time() - t1)
    else:
        if a.expect_audio or ctx.project.get("audio", {}).get("narration"):
            rep.add("audio-missing", "objective", "fail", "no audio stream, but audio is required by the project or --expect-audio")
        rep.check("audio-levels", "ran" if (a.expect_audio or ctx.project.get("audio", {}).get("narration")) else "skipped", "" if (a.expect_audio or ctx.project.get("audio", {}).get("narration")) else "no audio stream and none required")
    rep.check("audio-cut-alignment", "skipped", "not implemented: no onset detector is wired in (hyperframes audio could supply onsets)")
    return {"fps": fps, "duration": dur, "spans": spans, "info": info}


def vs_sha(p: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


# ---------------------------------------------------------------------------------------------- composition checks
def probe(index: Path, times: List[float], size: Tuple[int, int]) -> Optional[Dict[str, Any]]:
    cmd = [sys.executable, str(ROOT / "scripts" / "session-guard.py"), "run", "render", "--", "node", str(ROOT / "scripts" / "dom-probe.mjs"), str(index),
           "--times", ",".join(f"{t:.3f}" for t in times), "--width", str(size[0]), "--height", str(size[1])]
    r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=300)
    for line in r.stdout.splitlines():
        if line.startswith("{"):
            return json.loads(line)
    sys.stderr.write((r.stderr or r.stdout)[-400:])
    return None


def rgb_of(css: str) -> Optional[Tuple[int, int, int]]:
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)", css or "")
    if not m or (m.group(4) is not None and float(m.group(4)) < 0.5):
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def occupancy(items: List[Dict[str, Any]], w: float, h: float, cols: int = 32, rows: int = 18) -> np.ndarray:
    """Per-cell fraction of the frame covered by content boxes (text, shapes, media), 0..1.

    Coverage-weighted rather than 'any touch': a large sheet and a small label must not look alike.
    Full-frame backgrounds and transparent shapes are not content."""
    g = np.zeros((rows, cols))
    cw, ch = w / cols, h / rows
    for it in items:
        if it["k"] in ("shape", "media") and it["w"] > 0.9 * w and it["h"] > 0.9 * h:
            continue  # full-frame ground (a texture image counts like a background colour)
        if it["k"] == "shape" and it["bg"].startswith("rgba(") and ",0)" in it["bg"].replace(" ", ""):
            continue
        x0, x1 = max(0.0, it["x"]), min(w, it["x"] + it["w"])
        y0, y1 = max(0.0, it["y"]), min(h, it["y"] + it["h"])
        if x1 <= x0 or y1 <= y0:
            continue
        for r in range(int(y0 // ch), min(rows, int(y1 // ch) + 1)):
            oy = min(y1, (r + 1) * ch) - max(y0, r * ch)
            if oy <= 0:
                continue
            for c in range(int(x0 // cw), min(cols, int(x1 // cw) + 1)):
                ox = min(x1, (c + 1) * cw) - max(x0, c * cw)
                if ox > 0:
                    g[r, c] += ox * oy / (cw * ch)
    return np.minimum(g, 1.0)


def composition_checks(rep: Report, ctx: Context, index: Path, fmt: str, narr_scenes: List[Dict[str, Any]], duration_hint: Optional[float]) -> None:
    t0 = time.time()
    size = ctx.size_for(fmt)
    if ctx.scenes:
        times, labels = [], []
        for s in ctx.scenes:
            d = s["end_sec"] - s["start_sec"]
            for f in (0.4, 0.8):
                times.append(round(s["start_sec"] + f * d, 3)); labels.append(s["id"])
    else:
        d = duration_hint or 10.0
        times = [round(d * (i + 0.5) / 8, 3) for i in range(8)]; labels = [None] * 8
    res = probe(index, times, size)
    if not res:
        rep.check("dom-probe", "unavailable", "browser probe failed (puppeteer-core inside the hyperframes install, or the cached Chrome, missing)")
        rep.checks[-1]["required"] = True
        return
    rep.check("dom-probe", "ran", f"{len(times)} samples", time.time() - t0)
    if res.get("errors"):
        rep.add("page-errors", "objective", "fail", f"{len(res['errors'])} JavaScript error(s) while loading: {res['errors'][0]}")
    W, H = res["size"]
    short = min(W, H)
    floor = PRESETS["text_floor_fraction"] * short
    safe = PRESETS["formats"].get(fmt, PRESETS["formats"]["landscape"])["safe_area"]
    per_scene: Dict[str, List[Dict[str, Any]]] = {}
    for smp, lab in zip(res["samples"], labels):
        per_scene.setdefault(lab or f"t{smp['t']}", []).append(smp)
    wv = waiver_map(ctx, [l for l in labels if l])
    # per-sample checks
    seen_small, seen_out, seen_hud, seen_counter, seen_overlap, seen_contrast = set(), set(), set(), set(), set(), set()
    for smp, lab in zip(res["samples"], labels):
        smp["items"] = [i for i in smp["items"] if i["k"] != "text" or re.search(r"[A-Za-z0-9]", i["text"])]  # emoji-only glyphs are not type
        texts = [i for i in smp["items"] if i["k"] == "text"]
        shapes = [i for i in smp["items"] if i["k"] != "text"]
        sc_w = waiver_map(ctx, [lab] if lab else [])
        for it in texts:
            key = it["text"][:40]
            if it["fs"] < floor - 0.01 and key not in seen_small:
                seen_small.add(key)
                rep.add("text-size-floor", "measured", "warn", f"text '{key}' is {it['fs']:.1f}px = {it['fs'] / short * 100:.1f}% of the short side (floor {PRESETS['text_floor_fraction'] * 100:.1f}%)",
                        {"font_px": round(it["fs"], 1), "floor_px": round(floor, 1)}, t=smp["t"], beat=lab, waivers=sc_w)
            if (it["x"] < -2 or it["y"] < -2 or it["x"] + it["w"] > W + 2 or it["y"] + it["h"] > H + 2) and key not in seen_out:
                seen_out.add(key)
                rep.add("text-outside-frame", "measured", "warn", f"text '{key}' extends past the frame edge", {"box": [round(it[k]) for k in ("x", "y", "w", "h")]}, t=smp["t"], beat=lab, waivers=sc_w)
            corner = (it["x"] + it["w"] / 2 < CORNER[0] * W or it["x"] + it["w"] / 2 > (1 - CORNER[0]) * W) and (it["y"] + it["h"] / 2 < CORNER[1] * H or it["y"] + it["h"] / 2 > (1 - CORNER[1]) * H)
            if corner and it["fs"] <= 0.04 * H and key not in seen_hud:
                seen_hud.add(key)
                rep.add("hud-label", "measured", "warn", f"small text '{key}' sits in a corner ({it['fs'] / H * 100:.1f}% of height): HUD-style label", {"fs_px": round(it["fs"], 1)}, t=smp["t"], beat=lab,
                        suggestion="keep it only if it carries information the narration does not", waivers={**wv, **sc_w})
            if re.search(r"^\s*(0?\d{1,2}\s*/\s*\d{1,2}|(step|chapter|part|scene)\s*\d+(\s*(of|/)\s*\d+)?|0\d)\s*$", it["text"], re.I) and key not in seen_counter:
                seen_counter.add(key)
                rep.add("chapter-counter", "measured", "warn", f"counter-style label '{key}'", t=smp["t"], beat=lab, suggestion="legitimate in a stepped tutorial; declare progress-stepper", waivers={**wv, **sc_w})
        # overlaps between text boxes
        def ink(it):  # glyph rects are LINE boxes (ascent + descent); ink sits in roughly the central 72% of the line height
            return {**it, "y": it["y"] + 0.14 * it["h"], "h": 0.72 * it["h"]}
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                a_, b_ = ink(texts[i]), ink(texts[j])
                ox = min(a_["x"] + a_["w"], b_["x"] + b_["w"]) - max(a_["x"], b_["x"])
                oy = min(a_["y"] + a_["h"], b_["y"] + b_["h"]) - max(a_["y"], b_["y"])
                if ox > 4 and oy > 4:
                    small = min(a_["w"] * a_["h"], b_["w"] * b_["h"])
                    if ox * oy / small > 0.25:
                        key = (a_["text"][:20], b_["text"][:20])
                        if key not in seen_overlap:
                            seen_overlap.add(key)
                            rep.add("text-collision", "measured", "warn", f"'{a_['text'][:28]}' overlaps '{b_['text'][:28]}' ({ox * oy / small * 100:.0f}% of the smaller box)", {"overlap_px": [round(ox), round(oy)]}, t=smp["t"], beat=lab, waivers=sc_w)
        # contrast against the smallest opaque painted shape under the text centre
        for it in texts:
            cx, cy = it["x"] + it["w"] / 2, it["y"] + it["h"] / 2
            under = [s for s in shapes if s["k"] == "shape" and s["x"] <= cx <= s["x"] + s["w"] and s["y"] <= cy <= s["y"] + s["h"] and rgb_of(s["bg"]) and not s.get("gradient") and s["op"] >= 0.9]
            on_media = [s for s in shapes if s["k"] == "media" and s["tag"] in ("img", "video", "canvas") and s["x"] <= cx <= s["x"] + s["w"] and s["y"] <= cy <= s["y"] + s["h"] and s["w"] * s["h"] > 0.01 * W * H]
            fg = rgb_of(it["color"])
            if on_media and fg:
                continue  # the background is an image: a contrast ratio against whatever lies behind it would be invented
            if under and fg:
                bg = rgb_of(min(under, key=lambda s: s["w"] * s["h"])["bg"])
                ratio = cs.contrast_ratio(fg, bg)
                large = it["fs"] >= 0.035 * short or (it["fs"] >= 0.026 * short and int(it["fw"] or 400) >= 700)
                need = 3.0 if large else 4.5
                key = it["text"][:40]
                if ratio < need and key not in seen_contrast:
                    seen_contrast.add(key)
                    rep.add("low-contrast", "measured", "warn", f"'{key}' contrast {ratio:.1f}:1 (needs {need}:1 at this size); estimated against the nearest flat background shape", {"ratio": round(ratio, 2), "estimated": True}, t=smp["t"], beat=lab, waivers=sc_w)
    # per-scene structural checks
    sigs: Dict[str, np.ndarray] = {}
    left_head = []
    cards, lows, grads = [], [], []
    for lab, smps in per_scene.items():
        smp = smps[-1]
        texts = [i for i in smp["items"] if i["k"] == "text"]
        shapes = [i for i in smp["items"] if i["k"] != "text"]
        g = occupancy(smp["items"], W, H)
        sigs[lab] = g
        occ = float(g.mean())
        intent = ctx.intent.get(lab)
        if occ < 0.30:
            rep.add("low-occupancy", "measured", "warn", f"content covers {occ * 100:.0f}% of the frame", {"occupancy": round(occ, 3), "grid": "32x18"}, t=smp["t"], beat=lab,
                    suggestion="enlarge the subject or declare intent: minimal", waivers={"low-occupancy": f"intent:{intent}@storyboard"} if intent in ("minimal", "still") else None)
        if texts:
            head = max(texts, key=lambda i: i["fs"])
            others = [i for i in smp["items"] if i is not head and i["k"] != "text" or (i["k"] == "text" and i is not head and i["fs"] < head["fs"] * 0.8)]
            right_area = sum(min(i["w"], W) * min(i["h"], H) for i in others if i["x"] > 0.5 * W and not (i["k"] == "shape" and i["w"] > 0.9 * W))
            if head["x"] < 0.2 * W and head["y"] < 0.4 * H and head["x"] + head["w"] < 0.62 * W and right_area > 0.18 * W * H:
                left_head.append(lab)
        cs_ = [s for s in shapes if s["k"] == "shape" and s["radius"] >= 8 and (s["shadow"] or s["border"]) and 0.008 * W * H < s["w"] * s["h"] < 0.5 * W * H and s["op"] >= 0.5]
        has_text_in = [c for c in cs_ if any(c["x"] <= t_["x"] and t_["x"] + t_["w"] <= c["x"] + c["w"] + 4 and c["y"] <= t_["y"] and t_["y"] + t_["h"] <= c["y"] + c["h"] + 4 for t_ in texts)]
        if len(has_text_in) >= 3:
            cards.append(lab)
        full = [s for s in shapes if s["k"] == "shape" and s["w"] > 0.9 * W and s["h"] > 0.9 * H]
        if any(s["gradient"] for s in full) and not [s for s in shapes if s["k"] == "media" and s["w"] * s["h"] > 0.3 * W * H]:
            grads.append(lab)
    n_sc = len([k for k in per_scene if not k.startswith("t")])
    nn = len(per_scene)
    if nn >= 3 and len(left_head) >= max(3, int(0.6 * nn + 0.5)):
        rep.add("left-headline-right-content", "measured", "warn", f"{len(left_head)} of {nn} scenes use a left headline with content on the right ({', '.join(left_head)})", {"scenes": left_head},
                suggestion="a deck layout when repeated; vary hero placement or declare it the system")
    if nn >= 2 and len(cards) >= max(2, nn // 2):
        rep.add("card-pile", "measured", "warn", f"{len(cards)} of {nn} scenes build the picture from 3 or more rounded cards with text inside ({', '.join(cards)})", {"scenes": cards},
                suggestion="cards read as a dashboard; consider one connected picture")
    if grads:
        rep.add("gradient-background", "measured", "note", f"full-frame gradient with no texture or imagery layer in {len(grads)} scene(s) ({', '.join(grads[:5])})", {"scenes": grads})
    labs = list(sigs)
    if len(labs) >= 3:
        D = np.array([[float(np.abs(sigs[a_] - sigs[b_]).mean()) for b_ in labs] for a_ in labs])
        seen = set()
        for i in range(len(labs)):
            if i in seen:
                continue
            g = [j for j in range(len(labs)) if D[i, j] < 0.05]
            if len(g) >= 3:
                seen.update(g)
                rep.add("repeat-layout-dom", "measured", "warn" if len(g) / len(labs) >= 0.5 else "note", f"{len(g)} of {len(labs)} scenes occupy nearly the same regions of the frame ({', '.join(labs[j] for j in g)})",
                        {"coverage_distance_below": 0.05, "grid": "32x18", "calibration": "same threshold as the rendered-frame check"})
    # text that merely repeats the narration
    if ctx.narr:
        nar = {i: txt for _, _, i, txt in ctx.narr}
        for lab, smps in per_scene.items():
            if lab in nar:
                on = " ".join(i["text"] for i in smps[-1]["items"] if i["k"] == "text")
                ta = set(re.findall(r"[a-z]{4,}", on.lower())); tb = set(re.findall(r"[a-z]{4,}", nar[lab].lower()))
                if len(ta) >= 6 and ta and tb and len(ta & tb) / len(ta) > 0.7:
                    rep.add("text-echoes-narration", "measured", "warn", f"on-screen text in {lab} repeats {len(ta & tb) / len(ta) * 100:.0f}% of its own words from the narration", {"scene": lab},
                            beat=lab, suggestion="show what is said instead of captioning it, unless this is a caption band", waivers=wv)
    rep.check("composition-lint", "ran")


# ---------------------------------------------------------------------------------------------- critique pack
def critique_pack(rep: Report, ctx: Context, video: Path, spans: List[Tuple[float, float, str]], fps: float) -> None:
    out_dir = (ctx.pdir / "qa" / "motion") if ctx.pdir else video.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="mqa-seam-"))
    try:
        times, labels = [], []
        for a_, b_, i in spans[1:]:
            for k, dt in enumerate((-2 / fps, 0.0, 3 / fps, 0.5)):
                times.append(max(0.0, a_ + dt)); labels.append(f"{i} {'seam' if k < 3 else '+0.5s'} {a_ + dt:.2f}s")
        pngs = vs.sample_frames(str(video), times, tmp, 320)
        if pngs:
            p = vs.contact_sheet(pngs, labels, out_dir / "seams.jpg", cols=4, thumb_w=320)
            rep.artifacts["seams"] = str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    rep.prompts = [
        "Describe each frame on the scene sheet in one sentence before judging: what is on screen, what is the hero, would it pass as a slide?",
        "Does each beat make the viewer see the idea, or only read a description of it? Name the visual event that carries it.",
        "Is emphasis spent or spread? Which beat is the point of the film, and does it get the hardest visual work?",
        "At each seam (seams.jpg): what carries the eye across the transition (shape, position, colour, motion)? Is the transition motivated or decorative?",
        "Is stillness anywhere designed (a reason you can state) or accidental? Is any motion decoration with no job?",
        "Does the sound support pacing, with silence before what matters? (listen; the audio-cut-alignment check did not run)",
        "Does the ending feel designed, and does it end smaller or quieter than it began?",
    ]
    tmpl = {"video": str(video), "generated_for": "human or model critic; fill after looking at scene-sheet.jpg and seams.jpg and watching the film",
            "beats": [{"beat": i, "span_sec": [round(a_, 2), round(b_, 2)], "frame_description": "", "hero": "", "reads_as_slide": None, "seam_in": "", "scores": {c: None for c in ("composition", "hierarchy", "motion", "transition", "story", "sound")}, "evidence": ""} for a_, b_, i in spans],
            "overall": {"strongest": "", "weakest": "", "would_change_first": ""},
            "note": "Scores are 1-5 with a stated reason. This file is never auto-filled and never auto-passed."}
    p = out_dir / "critique.template.json"
    p.write_text(json.dumps(tmpl, indent=2) + "\n", encoding="utf-8")
    rep.artifacts["critique_template"] = str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
    # per-scene judgment findings (no verdict, just the questions that matter for this beat)
    for a_, b_, i in spans:
        sc = next((s for s in ctx.scenes if s["id"] == i), None)
        if sc:
            rep.add("beat-question", "judgment", "question", f"{i}: does the picture show '{sc['visual'][:90]}' and does it deliver '{sc['purpose'][:90]}'?", beat=i, rng=(a_, b_))


# ---------------------------------------------------------------------------------------------- commands
def finish(rep: Report, out: Optional[Path]) -> int:
    doc = rep.doc()
    import jsonschema
    errs = [e.message for e in jsonschema.Draft7Validator(load_json(ROOT / "specs" / "qa-report-spec.json")).iter_errors(doc)]
    if errs:
        print("internal error: report does not match its spec:", errs[:3], file=sys.stderr)
        return 3
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    s = doc["summary"]
    live = [f for f in doc["findings"] if "waived_by" not in f and f["severity"] in ("fail", "warn")]
    for f in live:
        where = f" @{f['t_sec']}s" if "t_sec" in f else (f" {f['range_sec'][0]}-{f['range_sec'][1]}s" if "range_sec" in f else "")
        print(f"[{f['class']:<9}] {f['severity'].upper():<4} {f['id']}{where}: {f['message']}")
    for f in doc["findings"]:
        if "waived_by" in f:
            print(f"[waived   ] {f['id']}: {f['message']}  (waived by {f['waived_by']['intent']})")
    skipped = [c for c in doc["checks_run"] if c["status"] != "ran"]
    for c in skipped:
        print(f"[check {c['status']}] {c['id']}: {c.get('reason', '')}")
    print(f"\nobjective failures {s['objective_failures']} | measured warnings {s['measured_warnings']} | judgment questions {s['judgment_questions']} | waived {s['waived']} | technical_pass={s['technical_pass']}")
    print("technical_pass is not a quality verdict: look at the sheets and run the critique.")
    if out:
        print("report:", out.relative_to(ROOT) if out.is_relative_to(ROOT) else out)
    return 1 if s["objective_failures"] else 0


def resolve_index(arg: str, fmt: Optional[str]) -> Tuple[Path, Optional[Path]]:
    p = Path(arg)
    if p.suffix == ".html":
        return p.resolve(), None
    pdir = project_dir(arg)
    name = f"index.{fmt}.html" if fmt and (pdir / "src" / f"index.{fmt}.html").exists() else "index.html"
    return pdir / "src" / name, pdir


def cmd_video(a: argparse.Namespace) -> int:
    pdir = project_dir(a.project) if a.project else None
    ctx = Context(pdir, a.format)
    rep = Report({"kind": "video", "path": str(a.file), **({"slug": pdir.name} if pdir else {}), **({"format": a.format} if a.format else {})})
    r = video_checks(rep, ctx, Path(a.file), a)
    if r and a.pack:
        critique_pack(rep, ctx, Path(a.file), r["spans"], r["fps"])
    return finish(rep, Path(a.out) if a.out else (pdir / "qa" / "motion" / "video-qa.json" if pdir else None))


def cmd_composition(a: argparse.Namespace) -> int:
    index, pdir = resolve_index(a.target, a.format)
    fmt = a.format or "landscape"
    ctx = Context(pdir, fmt)
    rep = Report({"kind": "composition", "path": str(index), **({"slug": pdir.name} if pdir else {}), "format": fmt})
    dur = None
    m = re.search(r'data-duration="([\d.]+)"', index.read_text(encoding="utf-8"))
    if m:
        dur = float(m.group(1))
    composition_checks(rep, ctx, index, fmt, ctx.scenes, dur)
    return finish(rep, Path(a.out) if a.out else (pdir / "qa" / "motion" / "composition-qa.json" if pdir else None))


def cmd_project(a: argparse.Namespace) -> int:
    pdir = project_dir(a.target)
    fmt = a.format or next((f["id"] for f in load_json(pdir / "project.json").get("formats", []) if f.get("primary")), "landscape") if (pdir / "project.json").exists() else (a.format or "landscape")
    ctx = Context(pdir, fmt)
    rep = Report({"kind": "project", "path": str(pdir.relative_to(ROOT)) if pdir.is_relative_to(ROOT) else str(pdir), "slug": pdir.name, "format": fmt})
    index, _ = resolve_index(a.target, fmt)
    m = re.search(r'data-duration="([\d.]+)"', index.read_text(encoding="utf-8"))
    composition_checks(rep, ctx, index, fmt, ctx.scenes, float(m.group(1)) if m else None)
    video = Path(a.video) if a.video else next(iter(sorted((pdir / "renders" / fmt).glob("final.mp4"))), None) if (pdir / "renders" / fmt).exists() else None
    if video and video.exists():
        ns = argparse.Namespace(expect_size=None, expect_fps=None, expect_duration=None, expect_audio=a.expect_audio, lufs=None, format=fmt)
        r = video_checks(rep, ctx, video, ns)
        if r:
            critique_pack(rep, ctx, video, r["spans"], r["fps"])
    else:
        rep.check("video-qa", "skipped", "no rendered video supplied or found under renders/<format>/final.mp4")
    return finish(rep, Path(a.out) if a.out else pdir / "qa" / "motion" / "motion-qa.json")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("video"); p.add_argument("file"); p.add_argument("--project"); p.add_argument("--format"); p.add_argument("--expect-size"); p.add_argument("--expect-fps", type=float)
    p.add_argument("--expect-duration", type=float); p.add_argument("--expect-audio", action="store_true"); p.add_argument("--lufs", type=float); p.add_argument("--pack", action="store_true"); p.add_argument("--out"); p.set_defaults(fn=cmd_video)
    p = sub.add_parser("composition"); p.add_argument("target"); p.add_argument("--format"); p.add_argument("--out"); p.set_defaults(fn=cmd_composition)
    p = sub.add_parser("project"); p.add_argument("target"); p.add_argument("--video"); p.add_argument("--format"); p.add_argument("--expect-audio", action="store_true"); p.add_argument("--out"); p.set_defaults(fn=cmd_project)
    p = sub.add_parser("critique-pack"); p.add_argument("target"); p.add_argument("--video", required=True); p.add_argument("--format"); p.set_defaults(fn=lambda a: cmd_project(argparse.Namespace(target=a.target, video=a.video, format=a.format, expect_audio=False, out=None)))
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
