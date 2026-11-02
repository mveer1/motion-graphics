"""Streaming video measurement shared by design-dna.py and motion-qa.py.

Everything here is measurement with stated thresholds; none of it is a verdict. Decoding goes
through ffmpeg pipes at a tiny analysis size, so memory stays flat (a 90 s clip at 30 fps is
about 14 MB of luma) and only one ffmpeg process runs at a time.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

AW, AH = 96, 54


def _run(*args, **kw):
    """subprocess.run that never reads the caller's stdin (ffmpeg would otherwise swallow it)."""
    kw.setdefault("stdin", subprocess.DEVNULL)
    return subprocess.run(*args, **kw)


def _popen(*args, **kw):
    kw.setdefault("stdin", subprocess.DEVNULL)
    return subprocess.Popen(*args, **kw)


class ScanError(RuntimeError):
    pass


def have_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def probe(path: str) -> Dict:
    r = _run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                       capture_output=True, text=True)
    if r.returncode:
        raise ScanError(f"ffprobe cannot read {path}: {r.stderr.strip()[:200]}")
    j = json.loads(r.stdout)
    v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in j.get("streams", []) if s.get("codec_type") == "audio"), None)
    out: Dict = {"duration_sec": float(j.get("format", {}).get("duration", 0) or 0), "has_audio": a is not None}
    if v:
        num, _, den = (v.get("avg_frame_rate") or "0/1").partition("/")
        out.update(width=int(v["width"]), height=int(v["height"]), fps=round(float(num) / float(den or 1), 3) if float(den or 1) else 0.0,
                   codec=v.get("codec_name"), nb_frames=int(v["nb_frames"]) if str(v.get("nb_frames", "")).isdigit() else None)
        if not out["duration_sec"] and v.get("duration"):
            out["duration_sec"] = float(v["duration"])
    if a:
        out["audio"] = {"codec": a.get("codec_name"), "sample_rate": int(a.get("sample_rate", 0) or 0), "channels": a.get("channels")}
    return out


def luma_stream(path: str, fps: Optional[float] = None) -> np.ndarray:
    """All frames (or resampled to `fps`) as (N, AH, AW) uint8 luma, read through a pipe."""
    vf = ([f"fps={fps}"] if fps else []) + [f"scale={AW}:{AH}:flags=area", "format=gray"]
    p = _popen(["ffmpeg", "-v", "error", "-i", str(path), "-an", "-vf", ",".join(vf), "-f", "rawvideo", "-"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    size = AW * AH
    chunks: List[np.ndarray] = []
    while True:
        buf = p.stdout.read(size * 64)
        if not buf:
            break
        usable = len(buf) - (len(buf) % size)
        if usable:
            chunks.append(np.frombuffer(buf[:usable], dtype=np.uint8).reshape(-1, AH, AW).copy())
    p.wait()
    if not chunks:
        raise ScanError(f"no frames decoded from {path}")
    return np.concatenate(chunks)


def frame_metrics(frames: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Per-frame (mean |diff| to previous, luma correlation to previous). Index 0 is (0, 1)."""
    f = frames.astype(np.float32)
    n = len(f)
    diff = np.zeros(n, dtype=np.float32)
    corr = np.ones(n, dtype=np.float32)
    for i in range(1, n):
        a, b = f[i], f[i - 1]
        diff[i] = np.abs(a - b).mean()
        sa, sb = a.std(), b.std()
        if sa < 1e-3 and sb < 1e-3:
            corr[i] = 1.0 if abs(a.mean() - b.mean()) < 2 else 0.0
        elif sa < 1e-3 or sb < 1e-3:
            corr[i] = 0.0
        else:
            corr[i] = float(((a - a.mean()) * (b - b.mean())).mean() / (sa * sb))
    return diff, corr


def detect_cuts(diff: np.ndarray, corr: np.ndarray, min_gap: int = 3) -> List[int]:
    """Hard cuts: an isolated one-frame change, not an animation.

    A frame is a cut when its diff stands out from the neighbouring frames' diffs (ratio >= 2.5),
    is large in absolute terms (>= 5/255 on the 96x54 luma) and the picture is structurally
    different from the previous frame (correlation < 0.6). Fast pushes fail the correlation test.
    """
    n = len(diff)
    cand = []
    for i in range(2, n):
        before = float(np.median(diff[max(1, i - 4):i])) if i > 1 else 0.0
        after = float(np.median(diff[i + 1:i + 5])) if i + 1 < n else 0.0
        ratio = diff[i] / (max(before, after) + 0.3)
        if ratio >= 2.5 and diff[i] >= 5.0 and corr[i] < 0.6:
            cand.append((float(diff[i]), i))
    kept: List[int] = []
    for _, i in sorted(cand, reverse=True):
        if all(abs(i - k) > min_gap for k in kept):
            kept.append(i)
    return sorted(kept)


def runs_below(diff: np.ndarray, eps: float, min_len: int) -> List[Tuple[int, int]]:
    """(first, last) frame indices of runs whose diff to the previous frame is < eps and length >= min_len."""
    out, start = [], None
    for i in range(1, len(diff)):
        if diff[i] < eps:
            start = i if start is None else start
        elif start is not None:
            if i - start >= min_len:
                out.append((start - 1, i - 1))
            start = None
    if start is not None and len(diff) - start >= min_len:
        out.append((start - 1, len(diff) - 1))
    return out


def flat_runs(frames: np.ndarray, std_max: float = 1.5, range_max: int = 8, min_len: int = 4) -> List[Tuple[int, int]]:
    """Runs of consecutive frames that are one flat field (empty frames)."""
    flat = np.array([(f.std() < std_max) and (int(f.max()) - int(f.min()) < range_max) for f in frames])
    out, start = [], None
    for i, v in enumerate(flat):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_len:
                out.append((start, i - 1))
            start = None
    if start is not None and len(flat) - start >= min_len:
        out.append((start, len(flat) - 1))
    return out


def black_runs(frames: np.ndarray, mean_max: float = 2.0, min_len: int = 3, peak_max: Optional[int] = 24) -> List[Tuple[int, int]]:
    """Runs of (near-)black frames: mean luma <= mean_max and, when peak_max is given, no pixel brighter than peak_max.

    The defaults describe a TRUE black frame (a render or switching failure). Designed darkness has content
    (a plate, a label, a glow) and is found with peak_max=None and a larger mean_max (see motion-qa 'very-dark')."""
    flat = frames.reshape(len(frames), -1)
    dark = flat.mean(axis=1) <= mean_max
    if peak_max is not None:
        dark &= flat.max(axis=1) <= peak_max
    out, start = [], None
    for i, v in enumerate(dark):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_len:
                out.append((start, i - 1))
            start = None
    if start is not None and len(dark) - start >= min_len:
        out.append((start, len(dark) - 1))
    return out


def sample_frames(path: str, times: Sequence[float], out_dir: Path, width: int = 640) -> List[Path]:
    """Write one PNG per requested time (seek, single frame). Sequential; one ffmpeg at a time."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for k, t in enumerate(times):
        dst = out_dir / f"f{k:03d}.png"
        r = _run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", str(path), "-frames:v", "1",
                            "-vf", f"scale={width}:-2:flags=area", str(dst)], capture_output=True)
        if r.returncode == 0 and dst.exists():
            paths.append(dst)
    return paths


def contact_sheet(images: Sequence[Path], labels: Sequence[str], out: Path, cols: int = 4, thumb_w: int = 400) -> Path:
    from PIL import Image, ImageDraw

    ims = [Image.open(p).convert("RGB") for p in images]
    if not ims:
        raise ScanError("no frames for contact sheet")
    th = int(thumb_w * ims[0].height / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * (th + 18)), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for i, im in enumerate(ims):
        x, y = (i % cols) * thumb_w, (i // cols) * (th + 18)
        sheet.paste(im.resize((thumb_w, th), Image.LANCZOS), (x, y + 18))
        d.text((x + 6, y + 3), labels[i] if i < len(labels) else "", fill=(235, 235, 235))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=88)
    return out


def loudness(path: str) -> Optional[Dict]:
    """Integrated loudness, LRA and true peak via ffmpeg ebur128; None when there is no audio stream."""
    r = _run(["ffmpeg", "-nostats", "-i", str(path), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    txt = r.stderr
    m = txt.rfind("Summary:")
    if m < 0:
        return None
    tail = txt[m:]

    def grab(pat: str) -> Optional[float]:
        g = re.search(pat, tail)
        return float(g.group(1)) if g else None

    return {"integrated_lufs": grab(r"I:\s+(-?[\d.]+) LUFS"), "lra_lu": grab(r"LRA:\s+(-?[\d.]+) LU"),
            "true_peak_dbtp": grab(r"Peak:\s+(-?[\d.]+) dBFS")}


def silence_ranges(path: str, noise_db: float = -50.0, min_sec: float = 0.5) -> List[Tuple[float, float]]:
    r = _run(["ffmpeg", "-nostats", "-i", str(path), "-vn", "-af", f"silencedetect=noise={noise_db}dB:d={min_sec}", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", r.stderr)]
    dur = probe(path)["duration_sec"]
    out = []
    for i, s in enumerate(starts):
        out.append((max(0.0, s), ends[i] if i < len(ends) else dur))
    return out


def motion_summary(frames: np.ndarray, fps: float) -> Dict:
    """Descriptive numbers for a clip: motion energy, cut rhythm and static share (no judgement)."""
    diff, corr = frame_metrics(frames)
    cuts = detect_cuts(diff, corr)
    dur = len(frames) / fps if fps else 0.0
    edges = [0] + cuts + [len(frames)]
    shots = [(edges[i + 1] - edges[i]) / fps for i in range(len(edges) - 1)]
    body = diff[1:] if len(diff) > 1 else diff
    return {
        "frames": int(len(frames)), "duration_sec": round(dur, 3), "analysis_size": f"{AW}x{AH}",
        "motion_mean_luma_diff": round(float(body.mean()), 3), "motion_median": round(float(np.median(body)), 3),
        "motion_p90": round(float(np.percentile(body, 90)), 3),
        "static_share": round(float((body < 0.35).mean()), 4),
        "cuts": [round(c / fps, 3) for c in cuts], "cut_count": len(cuts),
        "cuts_per_min": round(len(cuts) / dur * 60, 2) if dur else 0.0,
        "shot_length_median_sec": round(float(np.median(shots)), 3) if shots else None,
        "shot_length_mean_sec": round(float(np.mean(shots)), 3) if shots else None,
    }


def lag_energy(frames: np.ndarray, start: int, end: int, lag: int, step: int = 3) -> float:
    """Mean |frame[i+lag] - frame[i]| over a stretch. Slow drift accumulates here while per-frame change stays tiny,
    so it separates 'alive but slow' from 'frozen' (calibration: frozen stretches measured 0.06-0.10 at a 0.5 s lag,
    slow drifts 0.9-1.9; see specs/creative-intelligence-report.md)."""
    f = frames.astype(np.float32)
    idx = range(max(0, start), max(start + 1, end - lag), step)
    vals = [float(np.abs(f[i + lag] - f[i]).mean()) for i in idx if i + lag < len(f)]
    return float(np.mean(vals)) if vals else 0.0
