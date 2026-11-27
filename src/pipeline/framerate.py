"""Frame-rate conversion planning: which in-between frames to synthesise, and how.

A 30 fps film has one picture every 33 ms. Lifting it to 60 fps (or 90, 120) means inventing the pictures
in between. There are three ways to do that, and none of them is right everywhere:

  copy   repeat the earlier frame. Exact for holds, cuts and authored stepped motion ("on twos"); adds no
         smoothness anywhere else.
  blend  mix the two neighbours by the phase. Exact for cross-dissolves and fades. On a move it shows a faint
         double image for one 60 fps frame, which reads as a little motion blur.
  mci    motion-compensated interpolation (FFmpeg minterpolate): moves blocks along estimated motion vectors.
         Best on moves of textured content. It tears or warps where motion is not rigid (particles,
         transparency, text crossing text, zoom-throughs).

The planner decides per source frame pair from evidence measured on the film itself, the leave-one-out probe:
drop every other frame, rebuild it with each method, and compare the result with the real frame. A method that
predicts the real in-between frames of this content well will predict the new ones well. The probe interpolates
across twice the real gap (15 -> 30 for a 30 fps film), so it is conservative: MCI is chosen only where it
clearly wins. Calibration: three workspace films on 2026-11-25 (see .claude/skills/frame-rate/references/).

A code-made studio film should not be interpolated at all when it can be re-rendered: HyperFrames samples the
GSAP timeline at any rate, so a native 60 fps render has real in-between frames. `audit_tweens` and
`scan_composition` support that path (what still strobes at the target rate, what is locked to 30 fps).

Pure Python + NumPy. FFmpeg I/O lives in scripts/frame-rate.py, so everything here is testable without it.
"""
from __future__ import annotations

import math
import re
from fractions import Fraction
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

import numpy as np

PLAN_VERSION = 1

ANALYSIS_LONG_SIDE = 192   # luma analysis size: 192x108 landscape, 108x192 portrait
PROBE_LONG_SIDE = 640      # minterpolate runs at this size in the probe (full size would cost a full conversion)
BLOCK = 8                  # block size for the worst-block error (tears are local, a mean hides them)

# Starting values, calibrated on three films (2026-11-25). Luma differences are on the 0-255 scale.
# Studio films have almost no true holds: no pair was bit-identical and 54-58% of pairs changed by 0.25 or less,
# but 70-80% of those accumulated over 10 frames (continuous drift, not a hold). Copying them would keep the
# 30 fps judder exactly where it shows most, on slow drifts, so a hold is only a pair too small to matter either way.
HOLD_EPS = 0.02            # mean |diff| at or below this: the pair is a hold
CUT_MIN_DIFF = 6.0         # a cut changes the picture by at least this much...
CUT_MAX_CORR = 0.6         # ...is structurally different from the previous frame...
CUT_RATIO = 2.5            # ...and stands out from the neighbouring pairs (a fast move does not)
CUT_RATIO_NEAR = 2.0       # or stands out from its two immediate neighbours while correlation < CUT_NEAR_CORR
CUT_NEAR_CORR = 0.4
WORST_WEIGHT = 0.25        # score = mean error + WORST_WEIGHT * p98 block error
MCI_MARGIN = 0.10          # MCI must beat blend by 10% (its failures look worse than a ghost)
COPY_MARGIN = 0.10         # copy must beat the best synthesis by 10% (prefer smoothness on a tie)
SMOOTH_PAIRS = 5           # score smoothing window, so the method does not flicker frame to frame
DISSOLVE_RATIO = 0.25      # blend error under 25% of the pair's change: a dissolve or fade
HARD_RATIO = 0.6           # best method still makes 60% of the copy error: hard content (particles, flicker)
STEP_MOTION_RUN = 1.5      # stepped cadence: median run of changing pairs at most this long...
STEP_HOLD_RUN = 3.0        # ...separated by holds of at most this many pairs...
STEP_MIN_RUNS = 3          # ...at least this many of each inside one second

METHODS = {"c": "copy", "b": "blend", "m": "mci"}
LABELS = {"h": "hold", "x": "cut", "s": "stepped", "d": "dissolve", "v": "motion", "k": "hard"}


# --------------------------------------------------------------------------- rates and frame mapping

def snap_rate(value: float) -> Fraction:
    """A measured rate as the rate it stands for: 29.97 -> 30000/1001, 59.94 -> 60000/1001, 30.0 -> 30."""
    if abs(value - round(value)) < 0.005:
        return Fraction(int(round(value)))
    ntsc = value * 1001 / 1000
    if abs(ntsc - round(ntsc)) < 0.01:
        return Fraction(int(round(ntsc)) * 1000, 1001)
    return Fraction(value).limit_denominator(1000)


def parse_rate(value: Any) -> Fraction:
    """'30', '30/1', '30000/1001', 29.97 or 60 as an exact Fraction."""
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        return snap_rate(value)
    s = str(value).strip()
    if "/" in s:
        num, den = s.split("/", 1)
        if float(den) == 0:
            raise ValueError(f"frame rate {value!r} has a zero denominator")
        return Fraction(int(num), int(den))
    return snap_rate(float(s)) if "." in s else Fraction(int(s))


def target_rate(source: Fraction, wanted: Any, exact: bool = False) -> Fraction:
    """The output rate. A whole target on an NTSC source (x/1001) stays in the NTSC family: 29.97 -> '60' gives
    59.94, so every source frame still lands on an output frame. exact=True keeps the literal value."""
    want = parse_rate(wanted)
    if not exact and source.denominator == 1001 and want.denominator == 1:
        return Fraction(want.numerator * 1000, 1001)
    return want


def rate_str(rate: Fraction) -> str:
    return str(rate.numerator) if rate.denominator == 1 else f"{rate.numerator}/{rate.denominator}"


def output_frame_count(n_src: int, src: Fraction, dst: Fraction) -> int:
    """Frames at the new rate covering the same duration (n_src / src seconds)."""
    return max(1, int(round(Fraction(n_src) * dst / src)))


def source_position(k: int, src: Fraction, dst: Fraction) -> Tuple[int, Fraction]:
    """Output frame k sits at time k/dst: source frame i plus a phase in [0, 1) towards frame i + 1."""
    p = Fraction(k) * src / dst
    i = p.numerator // p.denominator
    return i, p - i


# --------------------------------------------------------------------------- measurement

def block_p98(err: np.ndarray, block: int = BLOCK) -> float:
    """98th percentile of the per-block mean error: a tear or a ghost is local, so the mean alone hides it."""
    h, w = (err.shape[0] // block) * block, (err.shape[1] // block) * block
    if h == 0 or w == 0:
        return float(err.mean())
    b = err[:h, :w].reshape(h // block, block, w // block, block).mean(axis=(1, 3))
    return float(np.percentile(b, 98))


def pair_stats(a: np.ndarray, b: np.ndarray) -> Tuple[float, float]:
    """(mean |b - a|, luma correlation) of two float32 luma frames."""
    d = float(np.abs(b - a).mean())
    sa, sb = float(a.std()), float(b.std())
    if sa < 1e-3 and sb < 1e-3:
        corr = 1.0 if abs(float(a.mean()) - float(b.mean())) < 2 else 0.0
    elif sa < 1e-3 or sb < 1e-3:
        corr = 0.0
    else:
        corr = float(((a - a.mean()) * (b - b.mean())).mean() / (sa * sb))
    return d, corr


class Analyzer:
    """Streams frames (in order) and records pair statistics and leave-one-out errors.

    push(frame_j, mci_j): frame_j is the analysis luma of source frame j (float32); mci_j, when given, is the
    probe's reconstruction of frame j from frames j-1 and j+1 alone (only odd j are real reconstructions).
    Memory stays at three frames however long the film is.
    """

    def __init__(self) -> None:
        self.d: List[float] = []
        self.corr: List[float] = []
        self.loo: Dict[str, List[float]] = {k: [] for k in ("copy_mean", "copy_p98", "blend_mean", "blend_p98", "mci_mean", "mci_p98")}
        self._win: List[np.ndarray] = []
        self._mci: List[Optional[np.ndarray]] = []
        self.n = 0

    def push(self, frame: np.ndarray, mci: Optional[np.ndarray] = None) -> None:
        if self._win:
            d, c = pair_stats(self._win[-1], frame)
            self.d.append(d)
            self.corr.append(c)
        self._win.append(frame)
        self._mci.append(mci)
        if len(self._win) == 3:
            self._score_middle()
            self._win.pop(0)
            self._mci.pop(0)
        self.n += 1

    def _score_middle(self) -> None:
        a, x, c = self._win
        j = self.n - 1  # index of the middle frame
        while len(self.loo["copy_mean"]) < j:
            for k in self.loo:
                self.loo[k].append(math.nan)
        e_prev, e_next = np.abs(x - a), np.abs(x - c)
        e_copy = e_prev if e_prev.mean() <= e_next.mean() else e_next
        e_blend = np.abs(x - (a + c) * 0.5)
        self.loo["copy_mean"].append(float(e_copy.mean()))
        self.loo["copy_p98"].append(block_p98(e_copy))
        self.loo["blend_mean"].append(float(e_blend.mean()))
        self.loo["blend_p98"].append(block_p98(e_blend))
        m = self._mci[1]
        if m is not None and j % 2 == 1:
            e_m = np.abs(x - m)
            self.loo["mci_mean"].append(float(e_m.mean()))
            self.loo["mci_p98"].append(block_p98(e_m))
        else:
            self.loo["mci_mean"].append(math.nan)
            self.loo["mci_p98"].append(math.nan)

    def finish(self) -> Dict[str, np.ndarray]:
        for k in self.loo:
            while len(self.loo[k]) < self.n:
                self.loo[k].append(math.nan)
        out = {"d": np.array(self.d, dtype=np.float64), "corr": np.array(self.corr, dtype=np.float64)}
        out.update({k: np.array(v, dtype=np.float64) for k, v in self.loo.items()})
        return out


# --------------------------------------------------------------------------- classification

def detect_cuts(d: np.ndarray, corr: np.ndarray) -> np.ndarray:
    """Boolean per pair: a hard cut (an isolated one-frame change of picture), never interpolated across.

    Unlike videoscan.detect_cuts there is no minimum gap: a flash frame between two shots is two cuts, and
    both must be copied, not blended."""
    n = len(d)
    cut = np.zeros(n, dtype=bool)
    for p in range(n):
        if d[p] < CUT_MIN_DIFF:
            continue
        before = float(np.median(d[max(0, p - 4):p])) if p > 0 else 0.0
        after = float(np.median(d[p + 1:p + 5])) if p + 1 < n else 0.0
        far = d[p] / (max(before, after) + 0.3)
        near = d[p] / (max(d[p - 1] if p > 0 else 0.0, d[p + 1] if p + 1 < n else 0.0) + 0.3)
        if (corr[p] < CUT_MAX_CORR and far >= CUT_RATIO) or (corr[p] < CUT_NEAR_CORR and near >= CUT_RATIO_NEAR):
            cut[p] = True
    return cut


def shots(cut: np.ndarray) -> List[Tuple[int, int]]:
    """Pair-index ranges [a, b) between cut pairs (the cut pairs themselves belong to no shot)."""
    out, start = [], 0
    for p, c in enumerate(cut):
        if c:
            if p > start:
                out.append((start, p))
            start = p + 1
    if start < len(cut):
        out.append((start, len(cut)))
    return out


def _runs(flags: Sequence[bool]) -> Tuple[List[int], List[int]]:
    """Lengths of True runs and of False runs."""
    true_runs, false_runs, cur, length = [], [], None, 0
    for f in flags:
        if f == cur:
            length += 1
            continue
        if cur is not None:
            (true_runs if cur else false_runs).append(length)
        cur, length = f, 1
    if cur is not None:
        (true_runs if cur else false_runs).append(length)
    return true_runs, false_runs


def detect_stepped(d: np.ndarray, cut: np.ndarray, fps: float) -> np.ndarray:
    """Boolean per pair: inside authored stepped motion (on twos, boil, a 15 fps source in a 30 fps file).

    The signature is a regular alternation of one changing pair and short holds, at least three times inside
    one second. Staccato motion graphics (a hold, a 3-frame move, a hold) has longer motion runs and is not
    stepped. Interpolating stepped motion would smooth away a look someone chose, so it is copied."""
    hold = d <= HOLD_EPS
    out = np.zeros(len(d), dtype=bool)
    half = max(2, int(round(fps / 2)))
    for a, b in shots(cut):
        for p in range(a, b):
            lo, hi = max(a, p - half), min(b, p + half + 1)
            window = hold[lo:hi]
            if len(window) < 2 * STEP_MIN_RUNS:
                continue
            share = float(window.mean())
            if not 0.3 <= share <= 0.75:
                continue
            hold_runs, move_runs = _runs(window.tolist())
            if len(hold_runs) >= STEP_MIN_RUNS and len(move_runs) >= STEP_MIN_RUNS \
                    and float(np.median(move_runs)) <= STEP_MOTION_RUN and float(np.median(hold_runs)) <= STEP_HOLD_RUN:
                out[p] = True
    return out


def _smooth(values: np.ndarray, ranges: List[Tuple[int, int]], width: int = SMOOTH_PAIRS) -> np.ndarray:
    """NaN-aware centred moving average, never across a cut."""
    out = np.full(len(values), math.nan)
    half = width // 2
    for a, b in ranges:
        seg = values[a:b]
        ok = ~np.isnan(seg)
        csum = np.concatenate([[0.0], np.cumsum(np.where(ok, seg, 0.0))])
        ccnt = np.concatenate([[0], np.cumsum(ok)])
        for p in range(len(seg)):
            lo, hi = max(0, p - half), min(len(seg), p + half + 1)
            cnt = ccnt[hi] - ccnt[lo]
            if cnt:
                out[a + p] = (csum[hi] - csum[lo]) / cnt
    return out


def pair_evidence(metrics: Dict[str, np.ndarray], cut: np.ndarray, use_mci: bool) -> Dict[str, np.ndarray]:
    """Per pair (i, i+1): mean and score of each method from the leave-one-out tests of frames i and i+1.

    A test frame whose window spans a cut is skipped for its other pair (its blend mixes two shots). With the MCI
    probe only odd frames carry an MCI test, so all methods are judged on the same odd frames."""
    n_pairs = len(metrics["d"])
    out = {f"{m}_{k}": np.full(n_pairs, math.nan) for m in ("copy", "blend", "mci") for k in ("mean", "score")}
    for p in range(n_pairs):
        frames = []
        for j in (p, p + 1):
            if j - 1 < 0 or j >= n_pairs:      # frame j needs both pairs j-1 and j
                continue
            if cut[j - 1] or cut[j]:
                continue
            if use_mci and (j % 2 == 0 or math.isnan(metrics["mci_mean"][j])):
                continue
            frames.append(j)
        if not frames:
            continue
        for m in ("copy", "blend", "mci"):
            means = [metrics[f"{m}_mean"][j] for j in frames]
            p98s = [metrics[f"{m}_p98"][j] for j in frames]
            if any(math.isnan(v) for v in means):
                continue
            out[f"{m}_mean"][p] = float(np.mean(means))
            out[f"{m}_score"][p] = float(np.mean(means) + WORST_WEIGHT * np.mean(p98s))
    return out


def plan_pairs(metrics: Dict[str, np.ndarray], fps: float, use_mci: bool,
               force: Optional[str] = None) -> Dict[str, Any]:
    """Method and label per source pair. force: 'copy' | 'blend' | 'mci' applies one method to every pair that is
    not a hold, cut or stepped (the measured classes still win: a forced blend never mixes two shots)."""
    d, corr = metrics["d"], metrics["corr"]
    n = len(d)
    cut = detect_cuts(d, corr)
    stepped = detect_stepped(d, cut, fps)
    ev = pair_evidence(metrics, cut, use_mci)
    ranges = shots(cut)
    sm = {k: _smooth(v, ranges) for k, v in ev.items()}
    methods, labels = [], []
    forced = {"copy": "c", "blend": "b", "mci": "m"}.get(force or "")
    for p in range(n):
        fixed = "x" if cut[p] else "h" if d[p] <= HOLD_EPS else "s" if stepped[p] else None
        if fixed:
            methods.append("c")
            labels.append(fixed)
            continue
        sb, sx, sc = sm["blend_score"][p], sm["mci_score"][p], sm["copy_score"][p]
        choice, best, best_mean = "b", sb, sm["blend_mean"][p]
        if not math.isnan(sb):
            if use_mci and not math.isnan(sx) and sx < sb * (1 - MCI_MARGIN):
                choice, best, best_mean = "m", sx, sm["mci_mean"][p]
            if not math.isnan(sc) and sc < best * (1 - COPY_MARGIN):
                choice, best, best_mean = "c", sc, sm["copy_mean"][p]
        if forced:
            choice = forced
        label = "v"
        bm, cm = sm["blend_mean"][p], sm["copy_mean"][p]
        if not math.isnan(bm) and d[p] > 1.0 and bm < DISSOLVE_RATIO * d[p]:
            label = "d"
            if choice == "m" and not forced:
                choice = "b"  # no motion to compensate: MCI vectors would only fit noise, and blend is exact for a dissolve
        elif choice != "c" and not math.isnan(best_mean) and not math.isnan(cm) and d[p] > 2.0 and best_mean > HARD_RATIO * cm:
            label = "k"
        methods.append(choice)
        labels.append(label)
    return {"methods": "".join(methods), "labels": "".join(labels), "cut": cut, "stepped": stepped, "evidence": sm}


def segments(methods: str, labels: str, src_rate: Fraction) -> List[Dict[str, Any]]:
    """Run-length (label, method) segments in source time. A pair p spans [p/src, (p+1)/src)."""
    out: List[Dict[str, Any]] = []
    fps = float(src_rate)
    start = 0
    for p in range(1, len(methods) + 1):
        if p == len(methods) or methods[p] != methods[start] or labels[p] != labels[start]:
            out.append({"start_sec": round(start / fps, 3), "end_sec": round(p / fps, 3), "pairs": p - start,
                        "label": LABELS[labels[start]], "method": METHODS[methods[start]]})
            start = p
    return out


def summarise(methods: str, labels: str, n_src: int, src: Fraction, dst: Fraction, metrics: Dict[str, np.ndarray]) -> Dict[str, Any]:
    """What the plan does, in seconds and in output frames."""
    fps = float(src)
    k_total = output_frame_count(n_src, src, dst)
    made = {"source": 0, "copy": 0, "blend": 0, "mci": 0}
    for k in range(k_total):
        i, ph = source_position(k, src, dst)
        if ph == 0 or i + 1 >= n_src:
            made["source" if ph == 0 else "copy"] += 1
        else:
            made[METHODS[methods[i]]] += 1
    in_between = k_total - made["source"]
    by_label = {LABELS[c]: round(labels.count(c) / fps, 2) for c in LABELS if labels.count(c)}
    by_method = {METHODS[c]: round(methods.count(c) / fps, 2) for c in METHODS if methods.count(c)}
    d = metrics["d"]
    moving = d > HOLD_EPS
    return {
        "source_frames": n_src, "output_frames": k_total, "in_between_frames": in_between,
        "output_frames_by_method": made,
        "synthesised_share_of_in_between": round((made["blend"] + made["mci"]) / in_between, 3) if in_between else 0.0,
        "seconds_by_label": by_label, "seconds_by_method": by_method,
        "cuts": int(labels.count("x")), "moving_share": round(float(moving.mean()), 3) if len(d) else 0.0,
        "effective_source_fps": round(fps * float(moving.mean()), 2) if len(d) else 0.0,
    }


def review_moments(segs: List[Dict[str, Any]], limit: int = 6) -> List[Dict[str, Any]]:
    """Times to look at after converting: the longest stretch of each kind that is most likely to show an artefact."""
    want = [("motion", "mci"), ("hard", "mci"), ("hard", "blend"), ("motion", "blend"), ("dissolve", "blend"), ("cut", "copy"), ("stepped", "copy")]
    out = []
    for label, method in want:
        cands = [s for s in segs if s["label"] == label and s["method"] == method]
        if not cands:
            continue
        s = max(cands, key=lambda x: x["pairs"])
        out.append({"t": round((s["start_sec"] + s["end_sec"]) / 2, 3), "why": f"{label} / {method}", "segment": [s["start_sec"], s["end_sec"]]})
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------------------- synthesis

def blend_frames(a: np.ndarray, b: np.ndarray, phase: Fraction) -> np.ndarray:
    """(1 - phase) * a + phase * b on uint8 planes, rounded. Works on any packed layout (yuv420p is linear per plane)."""
    w = int(round(float(phase) * 256))
    if w <= 0:
        return a
    if w >= 256:
        return b
    return ((a.astype(np.uint16) * (256 - w) + b.astype(np.uint16) * w + 128) >> 8).astype(np.uint8)


def stitch(n_src: int, src: Fraction, dst: Fraction, methods: str,
           source: Iterator[np.ndarray], mci: Optional[Iterator[np.ndarray]],
           emit: Callable[[np.ndarray], None], progress: Optional[Callable[[int, int], None]] = None) -> Dict[str, int]:
    """Write every output frame in order. Integer-phase frames are the source frames themselves; the rest follow
    the plan. The MCI stream (already at the target rate, frame k at time k/dst) is consumed in step whether or
    not a frame is used; when it ends early (minterpolate stops before the last pair) blend takes over."""
    if len(methods) != max(0, n_src - 1):
        raise ValueError(f"plan has {len(methods)} pairs, film has {n_src} frames")
    k_total = output_frame_count(n_src, src, dst)
    cache: Dict[int, np.ndarray] = {}
    next_src = 0
    counts = {"source": 0, "copy": 0, "blend": 0, "mci": 0, "mci_fallback": 0}

    def frame(i: int) -> np.ndarray:
        nonlocal next_src
        while next_src <= i:
            try:
                cache[next_src] = next(source)
            except StopIteration:
                raise RuntimeError(f"source ended after {next_src} frames, expected {n_src}") from None
            next_src += 1
            for old in [x for x in cache if x < next_src - 2]:
                del cache[old]
        return cache[i]

    for k in range(k_total):
        m_frame = None
        if mci is not None:
            m_frame = next(mci, None)
            if m_frame is None:
                mci = None
        i, ph = source_position(k, src, dst)
        i = min(i, n_src - 1)
        if ph == 0:
            out, kind = frame(i), "source"
        elif i + 1 >= n_src:
            out, kind = frame(i), "copy"
        else:
            m = methods[i]
            if m == "c":
                out, kind = frame(i), "copy"
            elif m == "m" and m_frame is not None:
                out, kind = m_frame, "mci"
            else:
                a, b = frame(i), frame(i + 1)
                out, kind = blend_frames(a, b, ph), "blend"
                if m == "m":
                    counts["mci_fallback"] += 1
        counts[kind] += 1
        emit(out)
        if progress:
            progress(k + 1, k_total)
    return counts


# --------------------------------------------------------------------------- native path: authored motion

def _power(p: float, kind: str) -> Callable[[float], float]:
    if kind == "in":
        return lambda t: t ** p
    if kind == "out":
        return lambda t: 1 - (1 - t) ** p
    return lambda t: (2 * t) ** p / 2 if t < 0.5 else 1 - (2 * (1 - t)) ** p / 2


def _shape(fin: Callable[[float], float], kind: str) -> Callable[[float], float]:
    """Build out / inOut from an 'in' curve, the way GSAP does."""
    if kind == "in":
        return fin
    if kind == "out":
        return lambda t: 1 - fin(1 - t)
    return lambda t: fin(2 * t) / 2 if t < 0.5 else 1 - fin(2 * (1 - t)) / 2


def _bounce_out(t: float) -> float:
    n, d = 7.5625, 2.75
    if t < 1 / d:
        return n * t * t
    if t < 2 / d:
        t -= 1.5 / d
        return n * t * t + 0.75
    if t < 2.5 / d:
        t -= 2.25 / d
        return n * t * t + 0.9375
    t -= 2.625 / d
    return n * t * t + 0.984375


POWER_ALIASES = {"power0": 0, "linear": 0, "none": 0, "power1": 2, "quad": 2, "power2": 3, "cubic": 3,
                 "power3": 4, "quart": 4, "power4": 5, "quint": 5, "strong": 5}


def ease_fn(name: Optional[str]) -> Optional[Callable[[float], float]]:
    """A GSAP 3 ease by name ('power3.out', 'expo.inOut', 'back.out(1.7)', 'none'); None for steps() and custom eases.
    GSAP's default ease is power1.out."""
    e = (name or "power1.out").strip()
    if e.startswith("steps") or e == "custom":
        return None
    m = re.match(r"^([a-zA-Z]+[0-9]?)(?:\.(in|out|inOut))?(?:\(([^)]*)\))?$", e)
    if not m:
        return None
    base, kind, args = m.group(1), m.group(2) or "out", m.group(3)
    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", args or "")]
    if base in POWER_ALIASES:
        p = POWER_ALIASES[base]
        return (lambda t: t) if p == 0 else _power(p, kind)
    if base == "sine":
        return _shape(lambda t: 1 - math.cos(t * math.pi / 2), kind)
    if base == "expo":
        return _shape(lambda t: 0.0 if t == 0 else 2 ** (10 * (t - 1)), kind)
    if base == "circ":
        return _shape(lambda t: 1 - math.sqrt(max(0.0, 1 - t * t)), kind)
    if base == "back":
        s = nums[0] if nums else 1.70158
        return _shape(lambda t: t * t * ((s + 1) * t - s), kind)
    if base == "bounce":
        return _shape(lambda t: 1 - _bounce_out(1 - t), kind)
    if base == "elastic":
        amp = max(1.0, nums[0]) if nums else 1.0
        period = nums[1] if len(nums) > 1 else 0.3
        s = period / (2 * math.pi) * math.asin(1 / amp)
        return _shape(lambda t: 0.0 if t == 0 else 1.0 if t == 1 else -(amp * 2 ** (10 * (t - 1)) * math.sin(((t - 1) - s) * 2 * math.pi / period)), kind)
    return None


def peak_slope(name: Optional[str], samples: int = 2000) -> Optional[float]:
    """Largest |d ease / d t| on [0, 1]: how many times faster than linear the fastest moment is."""
    f = ease_fn(name)
    if f is None:
        return None
    prev, best = f(0.0), 0.0
    for s in range(1, samples + 1):
        t = s / samples
        cur = f(t)
        best = max(best, abs(cur - prev) * samples)
        prev = cur
    return best


# Leads, not verdicts. Starting values; see the skill reference for where they come from.
FAST_SHARE_PER_FRAME = 0.025   # peak travel above 2.5% of the frame's short side per frame strobes on a fast move
ROTATION_DEG_PER_FRAME = 6.0
SCALE_PER_FRAME = 0.04
FADE_PER_FRAME = 0.34          # opacity changing by more than a third per frame is a pop, not a fade
LINEAR_MOVE_MAX_SEC = 1.0      # a short linear move starts and stops at full speed

_REST = {"x": 0.0, "y": 0.0, "rotation": 0.0, "scale": 1.0, "scaleX": 1.0, "scaleY": 1.0, "opacity": 1.0, "autoAlpha": 1.0}


def _num(v: Any) -> Tuple[Optional[float], bool]:
    """(value, relative) for 12, '12px', '+=40', '-=8'. Percent and function values are not lengths: None."""
    if isinstance(v, bool) or v is None:
        return None, False
    if isinstance(v, (int, float)):
        return float(v), False
    s = str(v).strip()
    if s.endswith("%"):
        return None, False
    m = re.match(r"^([+\-]=)?\s*(-?\d+(?:\.\d+)?)", s)
    if not m:
        return None, False
    val = float(m.group(2))
    if m.group(1) == "-=":
        return -val, True
    return val, bool(m.group(1))


def tween_travel(t: Dict[str, Any]) -> Dict[str, Tuple[float, bool]]:
    """Per property: (absolute change over the tween, assumed). 'assumed' marks a start or end value that the dump
    does not hold (a to() from the element's current value, a from() to it); the rest value is assumed."""
    out = {}
    props, start_vals, kind = t.get("props") or {}, t.get("from") or {}, t.get("kind")
    for key in _REST:
        if kind == "from":
            a, rel = _num(props.get(key))
            if a is None or rel:
                continue
            out[key] = (abs(_REST[key] - a), True)
            continue
        b, rel = _num(props.get(key))
        if b is None:
            continue
        if rel:
            out[key] = (abs(b), False)
            continue
        a, _ = _num(start_vals.get(key))
        assumed = a is None
        out[key] = (abs(b - (_REST[key] if assumed else a)), assumed)
    return out


def audit_tweens(dump: Dict[str, Any], fps_from: float, fps_to: float) -> Dict[str, Any]:
    """Peak per-frame change of every authored move at the source and the target rate, and the leads that follow.

    The native render samples the timeline more often, so per-frame steps halve at 60 fps; what is still above
    the thresholds at the target rate strobes even there and wants motion blur, a longer move or a softer ease."""
    w, h = (dump.get("size") or [1280, 720])[:2]
    short = float(min(w, h)) or 720.0
    rows, findings = [], []
    for idx, t in enumerate(dump.get("tweens") or []):
        dur = float(t.get("dur") or 0)
        if dur <= 0 or t.get("kind") == "set":
            continue
        slope = peak_slope(t.get("ease"))
        if slope is None:
            continue
        repeat = t.get("repeat") or 0
        for key, (travel, assumed) in tween_travel(t).items():
            if travel <= 0:
                continue
            per_sec = slope * travel / dur
            if key in ("x", "y"):
                unit, limit = "px", FAST_SHARE_PER_FRAME * short
            elif key == "rotation":
                unit, limit = "deg", ROTATION_DEG_PER_FRAME
            elif key in ("opacity", "autoAlpha"):
                unit, limit = "alpha", FADE_PER_FRAME
            else:
                unit, limit = "scale", SCALE_PER_FRAME
            row = {"tween": idx, "label": t.get("label"), "t0": t.get("t0"), "dur": dur, "ease": t.get("ease") or "power1.out",
                   "prop": key, "travel": round(travel, 3), "unit": unit, "assumed_start": assumed,
                   "peak_per_frame_src": round(per_sec / fps_from, 3), "peak_per_frame_dst": round(per_sec / fps_to, 3),
                   "limit_per_frame": round(limit, 3)}
            rows.append(row)
            if row["peak_per_frame_dst"] > limit:
                kind = "fade-pop" if unit == "alpha" else "strobe"
                fix = ("lengthen the fade to at least 3 frames at the target rate" if unit == "alpha" else
                       "add motion blur (data-motion-blur on #root), lengthen the move or use a softer ease")
                findings.append({"id": f"{kind}-{idx}-{key}", "severity": "lead", "kind": kind, "t": t.get("t0"), "label": t.get("label"),
                                 "message": f"{key} peaks at {row['peak_per_frame_dst']:g} {unit}/frame at {fps_to:g} fps "
                                            f"({row['peak_per_frame_src']:g} at {fps_from:g}); limit {limit:.3g}. Fix: {fix}."})
            if key in ("x", "y") and (t.get("ease") in ("none", "linear")) and dur < LINEAR_MOVE_MAX_SEC and not repeat and travel >= 0.01 * short:
                findings.append({"id": f"linear-{idx}-{key}", "severity": "lead", "kind": "velocity-jump", "t": t.get("t0"), "label": t.get("label"),
                                 "message": f"a {dur:g} s linear {key} move starts and stops at full speed; at {fps_to:g} fps the jerk is easier to see. "
                                            "Use an eased move unless constant speed is the point."})
    rows.sort(key=lambda r: r["peak_per_frame_dst"] / (r["limit_per_frame"] or 1), reverse=True)
    return {"short_side": short, "fps_from": fps_from, "fps_to": fps_to, "measured": len(rows), "fastest": rows[:12], "findings": findings}


_VIDEO_RE = re.compile(r"<video\b[^>]*?\bsrc\s*=\s*\"([^\"]+)\"", re.I)
_STEP_RE = re.compile(r"steps\(\s*\d+\s*\)|SteppedEase|\.stepped\(|\bboil\s*:|\.flicker\(|\bsteps\s*:\s*(?:true|\d)")
_ROOT_RE = re.compile(r"<[^>]*\bid\s*=\s*\"root\"[^>]*>", re.I)
_FPS_REF_RE = re.compile(r"\bformat\.fps\b|\bStudio\.fps\b|getAttribute\(\s*['\"]data-fps")


def scan_composition(html: str) -> Dict[str, Any]:
    """What in a composition is tied to the frame rate: video layers, stepped motion, motion blur, fps lookups."""
    root = _ROOT_RE.search(html)
    blur = None
    if root:
        m = re.search(r"data-motion-blur\s*=\s*\"([^\"]*)\"", root.group(0))
        shutter = re.search(r"data-motion-blur-shutter\s*=\s*\"([^\"]*)\"", root.group(0))
        blur = {"value": m.group(1), "shutter": shutter.group(1) if shutter else None} if m else None
    lines = html.splitlines()

    def where(rx: "re.Pattern[str]") -> List[Dict[str, Any]]:
        return [{"line": n + 1, "text": ln.strip()[:120]} for n, ln in enumerate(lines) if rx.search(ln)]

    return {"videos": sorted(set(_VIDEO_RE.findall(html))), "stepped": where(_STEP_RE), "motion_blur": blur, "fps_refs": where(_FPS_REF_RE)}


def json_floats(values: Iterable[float], ndigits: int = 3) -> List[Optional[float]]:
    """JSON-safe list (NaN -> None)."""
    return [None if (v is None or (isinstance(v, float) and math.isnan(v))) else round(float(v), ndigits) for v in values]
