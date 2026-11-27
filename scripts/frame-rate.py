#!/usr/bin/env python3
"""scripts/frame-rate.py: lift a 30 fps film to 60 fps (or 90, 120) and say how every gap was filled.

Two paths (skill: .claude/skills/frame-rate/SKILL.md):
  native   a studio project re-rendered at the new rate. HyperFrames samples the GSAP timeline at any rate, so
           every in-between frame is real. `audit <slug>` lists what still strobes or stays at 30 fps first.
  convert  any finished film (legacy explainers, archived renders, plates, external clips): measured, per-gap
           synthesis. `analyse` runs the leave-one-out probe and writes the plan; `convert` follows it.

    python scripts/frame-rate.py doctor
    python scripts/frame-rate.py audit <slug> [--fps 60] [--apply]
    python scripts/frame-rate.py analyse <film.mp4|slug> [--fps 60] [--fast] [--format portrait]
    python scripts/frame-rate.py convert <film.mp4|slug> [--fps 60] [--method auto|blend|mci|copy] [--out film-60.mp4]
    python scripts/frame-rate.py verify <film-60.mp4> [--source film.mp4]
    python scripts/frame-rate.py sheet <film-60.mp4> [--plan plan.json] [--at 3.2,7.5]

The probe (analyse) takes the host analysis lock and convert the render lock: one heavy job at a time on 8 GB.
Nothing here overwrites its input; output is written to a .partial file and renamed only on success.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "pipeline"))
sys.path.insert(0, str(ROOT / "src"))
import framerate as fr  # noqa: E402

from pipeline.hostlock import heavy_lock  # noqa: E402

PROJECTS = ROOT / "projects"
OUT = ROOT / "out"
MP4_AUDIO = {"aac", "mp3", "alac", "opus", "ac3", "eac3", "flac"}
MCI_FILTER = "minterpolate=fps={rate}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none"

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")  # the lock prints emoji; a cp1252 pipe must not crash the job
    except (AttributeError, ValueError):
        pass


def rel(p: Path) -> str:
    try:
        return Path(p).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def need_ffmpeg() -> None:
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        sys.exit("error: ffmpeg and ffprobe are required on PATH (frame-rate.py doctor)")


def run(cmd: List[str], **kw) -> subprocess.CompletedProcess:
    kw.setdefault("stdin", subprocess.DEVNULL)
    return subprocess.run(cmd, **kw)


# --------------------------------------------------------------------------- probing and decoding

def probe(path: Path) -> Dict[str, Any]:
    r = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"error: ffprobe cannot read {path}: {r.stderr.strip()[:300]}")
    j = json.loads(r.stdout)
    v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in j.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not v:
        sys.exit(f"error: {path} has no video stream")
    rate = fr.parse_rate(v.get("r_frame_rate") or "0/1")
    avg = fr.parse_rate(v.get("avg_frame_rate") or "0/1") if (v.get("avg_frame_rate") or "0/1") != "0/0" else rate
    nb = int(v["nb_frames"]) if str(v.get("nb_frames", "")).isdigit() else None
    dur = float(v.get("duration") or j.get("format", {}).get("duration") or 0)
    vfr = bool(avg and rate and abs(float(avg) - float(rate)) / float(rate) > 0.001)
    if vfr and avg:
        rate = fr.snap_rate(float(avg))
    info = {"width": int(v["width"]), "height": int(v["height"]), "rate": rate, "vfr": vfr, "frames": nb, "frames_in_header": nb is not None,
            "duration_sec": dur,
            "pix_fmt": v.get("pix_fmt"), "codec": v.get("codec_name"),
            "color": {k: v[k] for k in ("color_space", "color_primaries", "color_transfer", "color_range") if v.get(k) and v[k] != "unknown"},
            "has_audio": a is not None, "audio_codec": a.get("codec_name") if a else None}
    if info["frames"] is None and dur and rate:
        info["frames"] = int(round(dur * float(rate)))
    return info


def sizes(w: int, h: int, long_side: int) -> Tuple[int, int]:
    if w >= h:
        return long_side, max(2, int(round(long_side * h / w / 2)) * 2)
    return max(2, int(round(long_side * w / h / 2)) * 2), long_side


def decode(path: Path, info: Dict[str, Any], filters: List[str], pix_fmt: str) -> subprocess.Popen:
    """Raw frames on stdout, one per source frame (a VFR source is first made constant at its average rate)."""
    chain = ([f"fps={fr.rate_str(info['rate'])}"] if info["vfr"] else []) + filters
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-map", "0:v:0", "-an", "-sn", "-dn"]
    if chain:
        cmd += ["-vf", ",".join(chain)]
    cmd += ["-fps_mode", "passthrough", "-pix_fmt", pix_fmt, "-f", "rawvideo", "-"]
    return subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)


def frames_of(proc: subprocess.Popen, nbytes: int, shape: Optional[Tuple[int, ...]] = None, as_float: bool = False) -> Iterator[np.ndarray]:
    while True:
        chunks, got = [], 0
        while got < nbytes:
            b = proc.stdout.read(nbytes - got)
            if not b:
                break
            chunks.append(b)
            got += len(b)
        if got < nbytes:
            return
        a = np.frombuffer(b"".join(chunks), dtype=np.uint8)
        if shape:
            a = a.reshape(shape)
        yield a.astype(np.float32) if as_float else a


def finish(proc: Optional[subprocess.Popen]) -> None:
    if proc is None:
        return
    try:
        proc.stdout.close()
    except (OSError, AttributeError, ValueError):
        pass
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- inputs and outputs

def rate_label(rate: Fraction) -> str:
    return f"{round(float(rate), 2):g}"


def resolve_input(arg: str, fmt: Optional[str]) -> Tuple[Path, Optional[str], Optional[str]]:
    """A file, or a studio project slug (its current finished film for the format, else the newest archived one)."""
    p = Path(arg)
    if p.is_file():
        return p.resolve(), None, None
    pdir = PROJECTS / arg
    pj = pdir / "project.json"
    if not pj.exists():
        sys.exit(f"error: {arg} is neither a file nor a studio project (projects/<slug>/project.json)")
    project = json.loads(pj.read_text(encoding="utf-8"))
    ids = [f["id"] for f in project.get("formats", [])]
    fid = fmt or next((f["id"] for f in project.get("formats", []) if f.get("primary")), ids[0] if ids else None)
    if fid not in ids:
        sys.exit(f"error: {arg} has no format '{fid}' (has {', '.join(ids)})")
    cands = [pdir / "renders" / fid / "final.mp4", OUT / f"{project.get('slug', arg)}-{fid}.mp4"]
    hist = sorted((pdir / "renders" / "history" / fid).glob("*/final.mp4"), key=lambda x: x.parent.name, reverse=True)
    for c in cands + hist:
        if c.exists():
            if c in hist:
                print(f"note: no current render of {arg} {fid}; using the newest archived one ({rel(c)})")
            return c.resolve(), arg, fid
    sys.exit(f"error: {arg} {fid} has no finished film yet (studio.py build); pass a file instead")


def default_paths(src: Path, slug: Optional[str], fid: Optional[str], dst: Fraction, out: Optional[str]) -> Tuple[Path, Path]:
    """(output film, plan json)."""
    lab = rate_label(dst)
    if out:
        o = Path(out).resolve()
        return o, o.with_name(o.stem + ".fps-plan.json")
    if slug:
        pdir = PROJECTS / slug
        return pdir / "renders" / fid / "hfr" / f"final-{lab}fps.mp4", pdir / "qa" / "frame-rate" / f"{fid}-{lab}fps.plan.json"
    return src.with_name(f"{src.stem}-{lab}fps.mp4"), src.with_name(f"{src.stem}-{lab}fps.fps-plan.json")


# --------------------------------------------------------------------------- analyse

def analyse_film(src: Path, info: Dict[str, Any], dst: Fraction, use_probe: bool, slug: Optional[str]) -> Dict[str, Any]:
    aw, ah = sizes(info["width"], info["height"], fr.ANALYSIS_LONG_SIDE)
    pw, ph = sizes(info["width"], info["height"], min(fr.PROBE_LONG_SIDE, max(info["width"], info["height"])))
    chain = [f"scale={pw}:{ph}:flags=area", f"scale={aw}:{ah}:flags=area", "format=gray"]
    src_rate = info["rate"]
    t0 = time.time()
    ana = fr.Analyzer()
    ref = decode(src, info, chain, "gray")
    mci = None
    if use_probe:
        n, d = src_rate.numerator, src_rate.denominator
        probe_chain = [f"scale={pw}:{ph}:flags=area", "select='not(mod(n\\,2))'", f"setpts=N*{2 * d}/{n}/TB",
                       MCI_FILTER.format(rate=fr.rate_str(src_rate)), f"scale={aw}:{ah}:flags=area", "format=gray"]
        mci = decode(src, info, probe_chain, "gray")
    try:
        mci_frames = frames_of(mci, aw * ah, (ah, aw), True) if mci else None
        for f in frames_of(ref, aw * ah, (ah, aw), True):
            m = next(mci_frames, None) if mci_frames is not None else None
            ana.push(f, m)
            if ana.n % 600 == 0:
                print(f"  analysed {ana.n} frames ({ana.n / max(1e-6, time.time() - t0):.0f}/s)", flush=True)
    finally:
        finish(ref)
        finish(mci)
    if ana.n < 3:
        sys.exit(f"error: only {ana.n} frames decoded from {src}")
    metrics = ana.finish()
    plan = fr.plan_pairs(metrics, float(src_rate), use_mci=use_probe)
    segs = fr.segments(plan["methods"], plan["labels"], src_rate)
    moving = [j for j in range(1, ana.n - 1) if metrics["d"][j - 1] > fr.HOLD_EPS or metrics["d"][j] > fr.HOLD_EPS]
    probe_err = {}
    for m in ("copy", "blend", "mci"):
        vals = [metrics[f"{m}_mean"][j] for j in moving if j % 2 == 1 and not np.isnan(metrics[f"{m}_mean"][j])]
        if vals:
            probe_err[m] = round(float(np.mean(vals)), 3)
    return {
        "tool": "frame-rate", "plan_version": fr.PLAN_VERSION, "created_at": now(),
        "source": {"path": rel(src), "sha256": sha256(src), "bytes": src.stat().st_size, "width": info["width"], "height": info["height"],
                   "rate": fr.rate_str(src_rate), "vfr": info["vfr"], "frames": ana.n, "duration_sec": round(ana.n / float(src_rate), 4),
                   "has_audio": info["has_audio"], "slug": slug},
        "target": {"rate": fr.rate_str(dst), "frames": fr.output_frame_count(ana.n, src_rate, dst)},
        "analysis": {"size": [aw, ah], "probe": "leave-one-out mci+blend+copy" if use_probe else "leave-one-out blend+copy (fast)",
                     "probe_size": [pw, ph], "seconds": round(time.time() - t0, 1),
                     "thresholds": {k: getattr(fr, k) for k in ("HOLD_EPS", "CUT_MIN_DIFF", "CUT_MAX_CORR", "CUT_RATIO", "WORST_WEIGHT",
                                                                 "MCI_MARGIN", "COPY_MARGIN", "SMOOTH_PAIRS", "DISSOLVE_RATIO", "HARD_RATIO")}},
        "probe_error_moving": probe_err,
        "summary": fr.summarise(plan["methods"], plan["labels"], ana.n, src_rate, dst, metrics),
        "pairs": {"methods": plan["methods"], "labels": plan["labels"], "legend": {"methods": fr.METHODS, "labels": fr.LABELS}},
        "segments": segs,
        "review": fr.review_moments(segs),
    }


def print_plan(plan: Dict[str, Any], path: Path) -> None:
    s, src, tgt = plan["summary"], plan["source"], plan["target"]
    print(f"\n{src['path']}: {src['frames']} frames at {src['rate']} fps -> {tgt['frames']} frames at {tgt['rate']} fps")
    print(f"  probe: {plan['analysis']['probe']} ({plan['analysis']['seconds']} s); held-out error on moving frames: "
          + ", ".join(f"{k} {v}" for k, v in plan["probe_error_moving"].items()))
    print("  seconds by kind:   " + ", ".join(f"{k} {v}" for k, v in s["seconds_by_label"].items()))
    print("  seconds by method: " + ", ".join(f"{k} {v}" for k, v in s["seconds_by_method"].items()))
    mb = s["output_frames_by_method"]
    print(f"  in-between frames: {s['in_between_frames']} (blend {mb['blend']}, mci {mb['mci']}, copy {mb['copy']}); "
          f"synthesised share {s['synthesised_share_of_in_between']:.0%}; {s['cuts']} cut(s)")
    if s["effective_source_fps"] < 0.75 * float(fr.parse_rate(src["rate"])):
        print(f"  note: only {s['moving_share']:.0%} of source pairs change (about {s['effective_source_fps']} distinct frames per second)")
    if plan["review"]:
        print("  look at: " + "; ".join(f"{r['t']} s ({r['why']})" for r in plan["review"]))
    print(f"  plan: {rel(path)}")


def plan_matches(plan: Dict[str, Any], src: Path, dst: Fraction) -> bool:
    try:
        return (plan.get("plan_version") == fr.PLAN_VERSION and plan["source"]["bytes"] == src.stat().st_size
                and plan["source"]["sha256"] == sha256(src) and fr.parse_rate(plan["target"]["rate"]) == dst)
    except (KeyError, OSError, ValueError):
        return False


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def cmd_analyse(a: argparse.Namespace) -> int:
    need_ffmpeg()
    src, slug, fid = resolve_input(a.input, a.format)
    info = probe(src)
    dst = fr.target_rate(info["rate"], a.fps, a.exact)
    check_rates(info["rate"], dst)
    plan_path = Path(a.out).resolve() if a.out else default_paths(src, slug, fid, dst, None)[1]
    if a.fast:
        plan = analyse_film(src, info, dst, False, slug)
    else:
        with heavy_lock("analysis", slug=slug or src.stem):
            plan = analyse_film(src, info, dst, True, slug)
    write_json(plan_path, plan)
    print_plan(plan, plan_path)
    return 0


def check_rates(src: Fraction, dst: Fraction) -> None:
    if dst <= src:
        sys.exit(f"error: target {fr.rate_str(dst)} fps is not above the source's {fr.rate_str(src)} fps")
    if dst > 240:
        sys.exit("error: targets above 240 fps are not supported")
    if dst > 60:
        print(f"note: {rate_label(dst)} fps is above what YouTube, Instagram and TikTok deliver (60); keep it for high-refresh screens")


# --------------------------------------------------------------------------- convert

def encoder_cmd(info: Dict[str, Any], src: Path, dst: Fraction, out: Path, crf: int, preset: str) -> List[str]:
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", f"{info['width']}x{info['height']}",
           "-framerate", fr.rate_str(dst), "-i", "-", "-i", str(src), "-map", "0:v:0", "-map", "1:a?",
           "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p"]
    flags = {"color_space": "-colorspace", "color_primaries": "-color_primaries", "color_transfer": "-color_trc", "color_range": "-color_range"}
    for k, v in info["color"].items():
        cmd += [flags[k], v]
    if info["has_audio"]:
        cmd += ["-c:a", "copy"] if info["audio_codec"] in MP4_AUDIO else ["-c:a", "aac", "-b:a", "192k"]
    return cmd + ["-movflags", "+faststart", "-f", "mp4", str(out)]


def apply_force(plan: Dict[str, Any], method: str) -> str:
    """One method on every measured pair; holds, cuts and stepped stretches keep their copy."""
    char = {"copy": "c", "blend": "b", "mci": "m"}[method]
    return "".join(char if lab in "vdk" else m for m, lab in zip(plan["pairs"]["methods"], plan["pairs"]["labels"]))


def convert_film(src: Path, info: Dict[str, Any], plan: Dict[str, Any], methods: str, out: Path, crf: int, preset: str) -> Dict[str, Any]:
    if info["width"] % 2 or info["height"] % 2:
        sys.exit(f"error: {info['width']}x{info['height']} is odd; H.264 yuv420p needs even dimensions")
    src_rate, dst = info["rate"], fr.parse_rate(plan["target"]["rate"])
    n_src = plan["source"]["frames"]
    w, h = info["width"], info["height"]
    nbytes = w * h * 3 // 2
    out.parent.mkdir(parents=True, exist_ok=True)
    partial = out.with_name(out.stem + ".partial.mp4")
    log = tempfile.NamedTemporaryFile(prefix="frame-rate-", suffix=".log", delete=False)
    log.close()
    t0 = time.time()
    source = decode(src, info, [], "yuv420p")
    mci = decode(src, info, [MCI_FILTER.format(rate=fr.rate_str(dst))], "yuv420p") if "m" in methods else None
    with open(log.name, "wb") as logf:
        enc = subprocess.Popen(encoder_cmd(info, src, dst, partial, crf, preset), stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=logf)
        last = [0.0]

        def emit(frame: np.ndarray) -> None:
            enc.stdin.write(memoryview(np.ascontiguousarray(frame)))

        def progress(k: int, total: int) -> None:
            if time.time() - last[0] > 10 or k == total:
                last[0] = time.time()
                el = time.time() - t0
                print(f"  {k}/{total} frames ({k / max(el, 1e-6):.1f}/s, {el:.0f} s)", flush=True)

        try:
            src_iter = frames_of(source, nbytes)
            counts = fr.stitch(n_src, src_rate, dst, methods, src_iter,
                               frames_of(mci, nbytes) if mci else None, emit, progress)
            extra = sum(1 for _ in src_iter)
            enc.stdin.close()
            rc = enc.wait()
        except (BrokenPipeError, OSError, RuntimeError) as exc:
            enc.kill()
            enc.wait()
            msg = Path(log.name).read_text(encoding="utf-8", errors="replace")[-1500:]
            partial.unlink(missing_ok=True)
            sys.exit(f"error: conversion failed: {exc}\n{msg}")
        finally:
            finish(source)
            finish(mci)
    if rc:
        msg = Path(log.name).read_text(encoding="utf-8", errors="replace")[-1500:]
        partial.unlink(missing_ok=True)
        sys.exit(f"error: encoder exited {rc}\n{msg}")
    os.unlink(log.name)
    if extra:
        print(f"warning: the source decoded {extra} more frame(s) than the plan holds; the plan was made from a different decode")
    os.replace(partial, out)
    return {"output": rel(out), "seconds": round(time.time() - t0, 1), "frames_written": sum(v for k, v in counts.items() if k != "mci_fallback"),
            "by_method": counts, "encoder": {"codec": "libx264", "crf": crf, "preset": preset, "audio": "copy" if info["audio_codec"] in MP4_AUDIO else "aac"}}


def cmd_convert(a: argparse.Namespace) -> int:
    need_ffmpeg()
    src, slug, fid = resolve_input(a.input, a.format)
    info = probe(src)
    dst = fr.target_rate(info["rate"], a.fps, a.exact)
    check_rates(info["rate"], dst)
    out, plan_path = default_paths(src, slug, fid, dst, a.out)
    if out.resolve() == src.resolve():
        sys.exit("error: --out must not be the input film")
    plan = None
    if plan_path.exists() and not a.reanalyse:
        cand = json.loads(plan_path.read_text(encoding="utf-8"))
        if plan_matches(cand, src, dst):
            plan = cand
            print(f"using plan {rel(plan_path)}")
    if plan is None:
        if a.fast or a.method != "auto":
            plan = analyse_film(src, info, dst, False, slug)
        else:
            with heavy_lock("analysis", slug=slug or src.stem):
                plan = analyse_film(src, info, dst, True, slug)
        write_json(plan_path, plan)
    print_plan(plan, plan_path)
    methods = plan["pairs"]["methods"] if a.method == "auto" else apply_force(plan, a.method)
    with heavy_lock("render", slug=slug or src.stem):
        result = convert_film(src, info, plan, methods, out, a.crf, a.preset)
    result["method"] = a.method
    if a.method != "auto":
        result["methods_used"] = methods
    result["verify"] = verify_film(out, src, quiet=False)
    plan["convert"] = result
    write_json(plan_path, plan)
    print(f"\nwrote {rel(out)} in {result['seconds']} s; report in {rel(plan_path)}")
    if slug:
        print(f"  deliver by copying it over out/{slug}-{fid}.mp4 only after looking at it: "
              f"python scripts/frame-rate.py sheet {rel(out)} --plan {rel(plan_path)}")
    return 0 if result["verify"]["ok"] else 1


# --------------------------------------------------------------------------- verify and sheet

def distinct_rate(path: Path, info: Dict[str, Any]) -> Tuple[float, int]:
    """Distinct frames per second: pairs that change by more than a hold. A duplicate-padded '60 fps' reads about 30."""
    aw, ah = sizes(info["width"], info["height"], fr.ANALYSIS_LONG_SIDE)
    proc = decode(path, info, [f"scale={aw}:{ah}:flags=area", "format=gray"], "gray")
    prev, moving, n = None, 0, 0
    try:
        for f in frames_of(proc, aw * ah, (ah, aw), True):
            if prev is not None and float(np.abs(f - prev).mean()) > fr.HOLD_EPS:
                moving += 1
            prev = f
            n += 1
    finally:
        finish(proc)
    return (moving / max(1, n - 1)) * float(info["rate"]), n


def verify_film(out: Path, src: Optional[Path], quiet: bool = True) -> Dict[str, Any]:
    """Hard checks decide ok; 'smoother' is reported, not enforced (a film of holds and stepped motion gains little, by design)."""
    o = probe(out)
    checks: List[Dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str, hard: bool = True) -> None:
        checks.append({"check": name, "ok": ok, "detail": detail, "hard": hard})

    eff_out, n_out = distinct_rate(out, o)
    if o["frames_in_header"]:
        check("frame-count", o["frames"] == n_out, f"header {o['frames']}, decoded {n_out}")
    res: Dict[str, Any] = {"film": rel(out), "rate": fr.rate_str(o["rate"]), "frames": n_out, "duration_sec": round(n_out / float(o["rate"]), 4),
                           "distinct_fps": round(eff_out, 2)}
    if src:
        s = probe(src)
        eff_src, n_src = distinct_rate(src, s)
        want = fr.output_frame_count(n_src, s["rate"], o["rate"])
        check("frames-for-duration", n_out == want, f"{n_out} frames, {want} expected for {n_src} at {fr.rate_str(s['rate'])} fps")
        d_src, d_out = n_src / float(s["rate"]), n_out / float(o["rate"])
        check("duration", abs(d_src - d_out) <= 1 / float(s["rate"]), f"{d_out:.4f} s vs source {d_src:.4f} s")
        check("audio", o["has_audio"] == s["has_audio"], f"output {'has' if o['has_audio'] else 'no'} audio, source {'has' if s['has_audio'] else 'no'}")
        check("size", (o["width"], o["height"]) == (s["width"], s["height"]), f"{o['width']}x{o['height']} vs {s['width']}x{s['height']}")
        gain = eff_out / eff_src if eff_src else 0.0
        res.update(source_distinct_fps=round(eff_src, 2), distinct_gain=round(gain, 2))
        check("smoother", eff_out > eff_src * 1.05 or eff_src < 1.0,
              f"{eff_out:.1f} distinct frames/s vs {eff_src:.1f} in the source ({gain:.2f}x)", hard=False)
    res["checks"] = checks
    res["ok"] = all(c["ok"] for c in checks if c["hard"])
    if not quiet:
        print(f"\nverify {res['film']}: {res['rate']} fps, {res['frames']} frames, {res['distinct_fps']} distinct frames/s")
        for c in checks:
            tag = "PASS" if c["ok"] else ("FAIL" if c["hard"] else "NOTE")
            print(f"  [{tag}] {c['check']}: {c['detail']}")
    return res


def cmd_verify(a: argparse.Namespace) -> int:
    need_ffmpeg()
    res = verify_film(Path(a.film).resolve(), Path(a.source).resolve() if a.source else None, quiet=False)
    return 0 if res["ok"] else 1


def method_at(plan: Optional[Dict[str, Any]], k: int, dst: Fraction) -> str:
    if not plan:
        return ""
    src = fr.parse_rate(plan["source"]["rate"])
    i, ph = fr.source_position(k, src, dst)
    methods = (plan.get("convert") or {}).get("methods_used") or plan["pairs"]["methods"]
    if ph == 0:
        return "source"
    if i >= len(methods):
        return "copy"
    return fr.METHODS[methods[i]]


def cmd_sheet(a: argparse.Namespace) -> int:
    """Strips of consecutive output frames around chosen moments, labelled with how each frame was made. Look at them."""
    need_ffmpeg()
    film = Path(a.film).resolve()
    info = probe(film)
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8")) if a.plan else None
    times = [float(x) for x in a.at.split(",")] if a.at else [r["t"] for r in (plan or {}).get("review", [])]
    if not times:
        sys.exit("error: give --at t1,t2 or a --plan with review moments")
    rate = info["rate"]
    tw = a.width
    th = int(round(tw * info["height"] / info["width"] / 2)) * 2
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        sys.exit("error: sheet needs Pillow (the .venv has it)")
    strips = []
    with tempfile.TemporaryDirectory(prefix="fps-sheet-") as tmp:
        for row, t in enumerate(times):
            k0 = max(0, int(round(t * float(rate))) - a.frames // 2)
            pat = Path(tmp) / f"r{row}_%03d.png"
            run(["ffmpeg", "-v", "error", "-y", "-i", str(film), "-vf",
                 f"select='between(n\\,{k0}\\,{k0 + a.frames - 1})',scale={tw}:{th}:flags=lanczos", "-fps_mode", "passthrough", str(pat)],
                capture_output=True)
            imgs = sorted(Path(tmp).glob(f"r{row}_*.png"))
            strips.append((t, k0, [Image.open(p).convert("RGB") for p in imgs]))
    cols = max(len(s[2]) for s in strips) or 1
    sheet = Image.new("RGB", (cols * (tw + 4) + 4, len(strips) * (th + 22) + 4), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for r, (t, k0, imgs) in enumerate(strips):
        y = 4 + r * (th + 22)
        for c, im in enumerate(imgs):
            x = 4 + c * (tw + 4)
            sheet.paste(im, (x, y + 18))
            k = k0 + c
            d.text((x + 2, y + 2), f"{k / float(rate):.3f}s {method_at(plan, k, rate)}", fill=(235, 235, 235))
    out = Path(a.out).resolve() if a.out else (Path(a.plan).with_name(Path(a.plan).stem + ".sheet.png") if a.plan else film.with_suffix(".sheet.png"))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"wrote {rel(out)} ({len(strips)} strip(s) of {cols} frames). Look for tearing on mci frames and ghosting on blend frames.")
    return 0


# --------------------------------------------------------------------------- native path: audit a studio project

def cmd_audit(a: argparse.Namespace) -> int:
    pdir = PROJECTS / a.slug
    pj = pdir / "project.json"
    if not pj.exists():
        sys.exit(f"error: {a.slug} is not a studio project (no project.json); lift its finished film with `convert` instead")
    project = json.loads(pj.read_text(encoding="utf-8"))
    src_fps = float(project.get("fps", 30))
    dst = fr.parse_rate(a.fps)
    allowed = json.loads((ROOT / "specs" / "format-presets.json").read_text(encoding="utf-8"))["fps"]["allowed"]
    findings: List[Dict[str, Any]] = []

    def add(severity: str, fid: str, message: str, **extra: Any) -> None:
        findings.append({"id": fid, "severity": severity, "message": message, **extra})

    if float(dst) <= src_fps:
        add("note", "already", f"the project already renders at {src_fps:g} fps")
    if dst.denominator != 1 or int(dst) not in allowed:
        add("error", "rate-not-allowed",
            f"studio projects render at {', '.join(map(str, allowed))} fps (specs/video-spec.json). For {rate_label(dst)} fps render natively "
            f"at 60, then `frame-rate.py convert {a.slug} --fps {rate_label(dst)}` (60 -> 120 halves every gap), or change the schema (owner decision).")
    src_dir = pdir / "src"
    pages = [p for p in sorted(src_dir.glob("*.html")) if not re.match(r"index\.(landscape|portrait|square)", p.name)]
    scanned = {"pages": [rel(p) for p in pages], "videos": [], "stepped": [], "fps_refs": [], "motion_blur": None}
    for page in pages:
        scan = fr.scan_composition(page.read_text(encoding="utf-8", errors="replace"))
        scanned["stepped"] += [dict(s, page=page.name) for s in scan["stepped"]]
        scanned["fps_refs"] += [dict(s, page=page.name) for s in scan["fps_refs"]]
        if page.name == "index.html":
            scanned["motion_blur"] = scan["motion_blur"]
        for v in scan["videos"]:
            stem = re.sub(r"\.(landscape|portrait|square)(?=\.[a-z0-9]+$)", "", v)
            files = [src_dir / v] + [src_dir / re.sub(r"(\.[a-z0-9]+)$", rf".{f['id']}\1", stem) for f in project.get("formats", [])]
            for f in dict.fromkeys(files):
                if f.exists() and rel(f) not in [x["file"] for x in scanned["videos"]]:
                    rate = probe(f)["rate"] if shutil.which("ffprobe") else None
                    scanned["videos"].append({"file": rel(f), "fps": fr.rate_str(rate) if rate else None})
                    if rate is not None and rate < dst:
                        add("warn", f"video-{f.name}",
                            f"{rel(f)} is {rate_label(rate)} fps: in a {rate_label(dst)} fps film each of its frames shows "
                            f"{float(dst / rate):.3g} times (judder inside the layer). Plates re-render at the project rate (their stamp "
                            f"holds the fps): after --apply run `python scripts/visual-director.py render {a.slug}` on a host with Blender. "
                            "Without Blender, `frame-rate.py convert` the plate to a new file and point the layer at it.")
    if scanned["stepped"]:
        add("note", "stepped", f"{len(scanned['stepped'])} stepped-motion use(s) (steps(), boil, stepped poses, lamp flicker): they are time-based and "
            "stay stepped at the new rate, as designed.", where=scanned["stepped"][:8])
    if scanned["fps_refs"]:
        add("warn", "reads-fps", "the composition reads the frame rate; check that logic still holds at the new rate", where=scanned["fps_refs"][:8])
    blur = scanned["motion_blur"]
    if not blur:
        add("lead", "motion-blur", "no page motion blur: HyperFrames smears fast movers along their path with data-motion-blur=\"on\" "
            "(data-motion-blur-shutter 180-240) on #root. Experimental in this workspace: run `hyperframes check`, then look at the frames.")
    else:
        add("note", "motion-blur", f"page motion blur is '{blur['value']}' (shutter {blur['shutter'] or 'default 240'})")
    dump_path = pdir / "qa" / "motion" / "tweens.json"
    tween_report = None
    if dump_path.exists():
        tween_report = fr.audit_tweens(json.loads(dump_path.read_text(encoding="utf-8")), src_fps, float(dst))
        findings += tween_report["findings"]
    else:
        add("note", "no-tween-dump", f"no {rel(dump_path)}: run `python scripts/studio.py script {a.slug} --probe` (browser, render lock), then audit again "
            "to see which moves still strobe at the new rate")
    dur = float(project.get("duration_sec", 0))
    nfmt = len(project.get("formats", []))
    add("note", "cost", f"{int(round(dur * float(dst)))} frames per format to capture instead of {int(round(dur * src_fps))} "
        f"({nfmt} format(s)); the current renders go stale and move to renders/history/ on the next build")
    report = {"tool": "frame-rate", "kind": "native-audit", "created_at": now(), "slug": a.slug, "fps_from": src_fps, "fps_to": fr.rate_str(dst),
              "scanned": scanned, "tweens": tween_report, "findings": findings}
    out = pdir / "qa" / "frame-rate" / f"audit-{rate_label(dst)}fps.json"
    write_json(out, report)
    order = {"error": 0, "warn": 1, "lead": 2, "note": 3}
    print(f"{a.slug}: native {src_fps:g} -> {rate_label(dst)} fps audit")
    for f in sorted(findings, key=lambda x: order[x["severity"]]):
        print(f"  [{f['severity'].upper()}] {f['message']}")
    if tween_report:
        print(f"  {tween_report['measured']} authored moves measured; fastest at {rate_label(dst)} fps:")
        for r in tween_report["fastest"][:5]:
            print(f"    t={r['t0']} {r['label']} {r['prop']} {r['ease']} {r['dur']}s: {r['peak_per_frame_dst']} {r['unit']}/frame "
                  f"(limit {r['limit_per_frame']}, {r['peak_per_frame_src']} at {src_fps:g} fps)")
    print(f"  report: {rel(out)}")
    errors = [f for f in findings if f["severity"] == "error"]
    if a.apply:
        if errors:
            print("not applied: fix the errors first")
            return 1
        if float(dst) > src_fps:
            project["fps"] = int(dst)
            pj.write_text(json.dumps(project, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            rc = run([sys.executable, str(ROOT / "scripts" / "studio.py"), "formats", a.slug]).returncode
            if rc:
                print(f"error: studio.py formats {a.slug} exited {rc}")
                return rc
            print(f"applied: project.json fps = {int(dst)}; entry files regenerated. Next: python scripts/studio.py validate {a.slug}, "
                  f"python scripts/frame-review.py {a.slug} --fonts google, then on the render host python scripts/studio.py build {a.slug}")
    return 1 if errors else 0


# --------------------------------------------------------------------------- doctor

def cmd_doctor(_: argparse.Namespace) -> int:
    ok = True
    for tool in ("ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        print(f"  {tool:12s} {path or 'MISSING'}")
        ok &= bool(path)
    if shutil.which("ffmpeg"):
        v = run(["ffmpeg", "-hide_banner", "-version"], capture_output=True, text=True).stdout.splitlines()[:1]
        print(f"  {'version':12s} {v[0] if v else '?'}")
        filters = run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
        for flt in ("minterpolate", "select", "scale"):
            has = re.search(rf"\s{flt}\s", filters) is not None
            print(f"  {flt:12s} {'yes' if has else 'MISSING'}")
            ok &= has
    print(f"  {'numpy':12s} {np.__version__}")
    try:
        import PIL
        print(f"  {'pillow':12s} {PIL.__version__} (sheet)")
    except ImportError:
        print(f"  {'pillow':12s} missing (only `sheet` needs it)")
    hf = shutil.which("hyperframes")
    print(f"  {'hyperframes':12s} {hf or 'missing (native re-render happens on the render host)'}")
    print("ready" if ok else "not ready: install ffmpeg with minterpolate")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="tools this host has").set_defaults(fn=cmd_doctor)

    p = sub.add_parser("audit", help="native path: what a studio project needs before it renders at the new rate")
    p.add_argument("slug")
    p.add_argument("--fps", default="60")
    p.add_argument("--apply", action="store_true", help="set project.json fps and regenerate the entry files")
    p.set_defaults(fn=cmd_audit)

    for name, fn, hlp in (("analyse", cmd_analyse, "measure the film and write the per-gap plan"),
                          ("convert", cmd_convert, "analyse if needed, then write the lifted film")):
        p = sub.add_parser(name, help=hlp)
        p.add_argument("input", help="a film, or a studio project slug")
        p.add_argument("--fps", default="60", help="target rate: 60, 90, 120, 60000/1001 (default 60)")
        p.add_argument("--exact", action="store_true", help="keep a whole target on an NTSC source (no 59.94 for 60)")
        p.add_argument("--format", help="project format (default: the primary one)")
        p.add_argument("--fast", action="store_true", help="skip the MCI probe: blend and copy only, no motion estimation")
        p.add_argument("--out", help="convert: the output film (plan beside it); analyse: the plan file")
        if name == "convert":
            p.add_argument("--method", choices=("auto", "blend", "mci", "copy"), default="auto",
                           help="auto follows the plan; the others force one method on measured pairs (holds, cuts and stepped stay copied)")
            p.add_argument("--crf", type=int, default=16, help="x264 CRF (16 matches the HyperFrames 'looks' quality)")
            p.add_argument("--preset", default="slow")
            p.add_argument("--reanalyse", action="store_true", help="ignore a matching plan on disk")
        p.set_defaults(fn=fn)

    p = sub.add_parser("verify", help="frame count, duration, audio and distinct frames per second of a lifted film")
    p.add_argument("film")
    p.add_argument("--source")
    p.set_defaults(fn=cmd_verify)

    p = sub.add_parser("sheet", help="contact strips of consecutive output frames, labelled by how each was made")
    p.add_argument("film")
    p.add_argument("--plan")
    p.add_argument("--at", help="comma-separated seconds (default: the plan's review moments)")
    p.add_argument("--frames", type=int, default=6)
    p.add_argument("--width", type=int, default=300)
    p.add_argument("--out")
    p.set_defaults(fn=cmd_sheet)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
