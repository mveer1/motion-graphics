"""Motion-variety and tween-conflict analysis of a composition's GSAP timeline.

`scripts/tween-probe.mjs` dumps every tween (start, duration, ease, from/to values, target) from the paused
timeline without rendering. This module reads that dump and answers two questions a person cannot answer by
eye across 90 seconds of motion:

  1. Variety. Does every scene enter the same way, at the same speed, on the same ease? Uniform motion reads
     as a template. Rules adapted from HeyGen's hyperframes-creative `motion-principles.md` (Apache-2.0):
     vary eases, vary speed, vary entry direction, use `.out` to enter and `.in` to leave, enter more slowly
     than you exit, and do not start a scene on its cut.
  2. Conflicts. Two tweens that animate the same property of the same element at the same time overwrite each
     other, so one of them silently loses.

All findings are MEASURED leads against stated thresholds, never verdicts (specs/qa-report-spec.json). The
thresholds are starting values adopted from that source and calibrated here only against three films, so each
finding carries its numbers. Linear eases ('none') are treated as deliberate drift and left out of the variety
counts. Pure Python, no browser needed to test.
"""
from __future__ import annotations

import re
import statistics
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

OPACITY = {"opacity", "autoAlpha"}
TRANSFORM = {"x", "y", "xPercent", "yPercent", "scale", "scaleX", "scaleY", "rotation", "rotationX", "rotationY", "skewX", "skewY", "z"}
REVEAL = {"clipPath", "strokeDashoffset", "strokeDasharray", "drawSVG", "width", "height", "maskPosition", "scaleX", "scaleY"}
ALIAS = {"opacity": "opacity", "autoAlpha": "opacity", "visibility": "opacity"}
LINEAR = {"none", "linear", None}

# Starting values (adopted-unverified except where a calibration is named).
MIN_ENTRANCES_FILM = 12          # below this a film has too few entrances to judge
MIN_RECIPES_SCENE = 4
EASE_SHARE_WARN = 0.75           # one ease on 75% or more of a scene's distinct entrance recipes
EASE_DISTINCT_FILM = 2           # a whole film that uses two eases or fewer for entrances
DIRECTION_SHARE_WARN = 0.70
SPEED_SPREAD_WARN = 1.5          # slowest scene's median entrance vs the fastest scene's
DURATION_SPREAD_WARN = 2.0       # film-level p90/p10 of entrance durations
OVERLAP_MIN_SEC = 0.12           # four frames at 30 fps: a fade-out starting 0.05 s before a fade-in ends is a hand-off, not a fight
SCENE_PRE_ROLL = 0.4             # an entrance may start this much before its scene's cut (crossfade pre-roll)
START_ON_CUT_SEC = 0.03


def to_num(v: Any) -> Optional[float]:
    """Leading number of a GSAP value ('+=40', '12px', '-50%', 0.4) or None."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.match(r"^\s*([+\-]=)?\s*(-?\d+(?:\.\d+)?)", str(v))
    if not m:
        return None
    val = float(m.group(2))
    return -val if m.group(1) == "-=" else val


def prop_group(name: str) -> Optional[str]:
    """Canonical property name for conflict detection. Non-visual helpers (`__n` counters, attr, fills) return None."""
    if name.startswith("__") or name in {"attr", "fill", "stroke", "color", "backgroundColor", "stopColor", "textContent", "innerHTML"}:
        return None
    return ALIAS.get(name, name)


def split_ease(ease: Optional[str]) -> Tuple[str, Optional[str]]:
    """('power3', 'out') for 'power3.out'; ('steps(24)', None); ('none', None)."""
    e = ease or "power1.out"
    m = re.match(r"^(.*)\.(in|out|inOut)$", e)
    return (m.group(1), m.group(2)) if m else (e, None)


def opacity_of(d: Dict[str, Any]) -> Optional[float]:
    for k in OPACITY:
        if k in d and to_num(d[k]) is not None:
            return to_num(d[k])
    return None


def role(t: Dict[str, Any]) -> Optional[str]:
    """'entrance', 'exit' or None for a tween. Frame-covering targets are scene transitions, not element motion."""
    if t.get("cover") or t["dur"] <= 0 or t["kind"] == "set":
        return None
    to_op, from_op = opacity_of(t["props"]), opacity_of(t.get("from") or {})
    if t["kind"] == "from":  # vars hold the FROM state
        return "entrance" if to_op is not None and to_op <= 0.1 else None
    if from_op is not None and from_op <= 0.1 and (to_op is None or to_op >= 0.5):
        return "entrance"
    if to_op is not None and to_op <= 0.05 and (from_op is None or from_op >= 0.5):
        return "exit"
    if t["kind"] == "to" and to_op is not None and to_op >= 0.5:
        return "entrance"
    return None


def direction(t: Dict[str, Any]) -> str:
    """How an entrance arrives: from-below, from-above, from-left, from-right, scale-up, reveal, fade or other."""
    src = t["props"] if t["kind"] == "from" else (t.get("from") or {})
    keys = {k for k in list(src) + list(t["props"]) if not k.startswith("__")}
    dy = to_num(src.get("y", src.get("yPercent")))
    dx = to_num(src.get("x", src.get("xPercent")))
    sc = to_num(src.get("scale"))
    if dy and abs(dy) >= abs(dx or 0):
        return "from-below" if dy > 0 else "from-above"
    if dx:
        return "from-right" if dx > 0 else "from-left"
    if sc is not None and sc < 0.98:
        return "scale-up"
    if keys & REVEAL:
        return "reveal"
    if keys <= OPACITY | {"visibility"}:
        return "fade"
    return "other"


def scene_of(t0: float, scenes: List[Dict[str, Any]]) -> Optional[str]:
    if not scenes:
        return None
    owner = None
    for s in scenes:
        if s["start_sec"] <= t0 + SCENE_PRE_ROLL:
            owner = s["id"]
    return owner


def analyse(tweens: List[Dict[str, Any]], scenes: List[Dict[str, Any]], waivers: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Findings as dicts {id, severity, message, evidence, beat?, range?}. severity is 'warn' or 'note'."""
    out: List[Dict[str, Any]] = []
    for t in tweens:
        t["role"] = role(t)
        t["scene"] = scene_of(t["t0"], scenes)
    ent = [t for t in tweens if t["role"] == "entrance"]
    ex = [t for t in tweens if t["role"] == "exit"]
    shaped = [t for t in ent if t["ease"] not in LINEAR]

    def recipe(t: Dict[str, Any]) -> Tuple:
        return (t["kind"], t["ease"], round(t["dur"], 2), tuple(sorted(set(t["props"]) | set(t.get("from") or {}))), direction(t))

    # ---- variety, per scene: one ease carrying most of a scene's distinct entrance recipes
    by_scene: Dict[str, List[Dict[str, Any]]] = {}
    for t in shaped:
        by_scene.setdefault(t["scene"] or "film", []).append(t)
    mono = []
    for sid, ts in by_scene.items():
        recipes = {recipe(t) for t in ts}
        if len(recipes) < MIN_RECIPES_SCENE:
            continue
        eases = Counter(r[1] for r in recipes)
        top, n = eases.most_common(1)[0]
        if n / len(recipes) >= EASE_SHARE_WARN:
            mono.append((sid, top, n, len(recipes)))
    if mono:
        shown = "; ".join(f"{s}: {n} of {m} on {e}" for s, e, n, m in mono[:6])
        out.append({"id": "ease-monotony", "severity": "warn" if len(mono) >= max(2, len(by_scene) // 2) else "note",
                    "message": f"{len(mono)} scene(s) put {int(EASE_SHARE_WARN * 100)}% or more of their distinct entrance recipes on one ease ({shown}). Entrance ease carries tone: confident, dreamy and playful are different eases.",
                    "evidence": {"scenes": [m[0] for m in mono], "threshold_share": EASE_SHARE_WARN, "min_recipes": MIN_RECIPES_SCENE}})

    # ---- variety, whole film
    if len(shaped) >= MIN_ENTRANCES_FILM:
        film_eases = Counter(t["ease"] or "power1.out" for t in shaped)
        if len(film_eases) <= EASE_DISTINCT_FILM:
            out.append({"id": "ease-variety", "severity": "warn", "message": f"the whole film enters on {len(film_eases)} ease(s) ({', '.join(film_eases)}) across {len(shaped)} entrances.",
                        "evidence": {"eases": dict(film_eases)}})
        durs = sorted(t["dur"] for t in shaped)
        p10, p90 = durs[int(0.1 * (len(durs) - 1))], durs[int(0.9 * (len(durs) - 1))]
        if p10 > 0 and p90 / p10 < DURATION_SPREAD_WARN:
            out.append({"id": "duration-uniformity", "severity": "warn", "message": f"entrance durations barely vary: the slow end is {p90 / p10:.1f}x the fast end ({p10:.2f}s to {p90:.2f}s over {len(durs)} entrances). Speed carries weight; let a scene breathe or snap.",
                        "evidence": {"p10_sec": p10, "p90_sec": p90, "ratio": round(p90 / p10, 2), "threshold": DURATION_SPREAD_WARN}})
        med = {sid: statistics.median(t["dur"] for t in ts) for sid, ts in by_scene.items() if len(ts) >= 3}
        if len(med) >= 3:
            lo, hi = min(med.values()), max(med.values())
            if lo > 0 and hi / lo < SPEED_SPREAD_WARN:
                out.append({"id": "scene-speed-uniformity", "severity": "note", "message": f"every scene enters at nearly the same speed: slowest scene median {hi:.2f}s vs fastest {lo:.2f}s ({hi / lo:.1f}x, threshold {SPEED_SPREAD_WARN}x).",
                            "evidence": {"scene_medians": {k: round(v, 2) for k, v in med.items()}}})
        dirs = Counter(direction(t) for t in {recipe(t): t for t in shaped}.values())
        total = sum(dirs.values())
        if total >= 8:
            top, n = dirs.most_common(1)[0]
            if n / total >= DIRECTION_SHARE_WARN and top not in {"other"}:
                out.append({"id": "entrance-direction", "severity": "warn", "message": f"{n} of {total} distinct entrance recipes arrive the same way ({top}). Vary the direction: from the side, from scale, a reveal, a fade.",
                            "evidence": {"directions": dict(dirs)}})

    # ---- ease direction
    bad_in = [t for t in ent if split_ease(t["ease"])[1] == "in"]
    if bad_in:
        labels = ", ".join(sorted({t["label"] for t in bad_in})[:5])
        out.append({"id": "entrance-ease-in", "severity": "note", "message": f"{len(bad_in)} entrance tween(s) use an ease-in ({labels}), which starts slowly and feels sluggish. Use .out to enter.",
                    "evidence": {"count": len(bad_in), "first_t_sec": min(t['t0'] for t in bad_in)}})
    bad_out = [t for t in ex if split_ease(t["ease"])[1] == "out"]
    if len(bad_out) >= 3:
        out.append({"id": "exit-ease-out", "severity": "note", "message": f"{len(bad_out)} element exits use an ease-out, which feels reluctant. Use .in to leave.",
                    "evidence": {"count": len(bad_out)}})

    # ---- entrance longer than exit
    if len(ent) >= 5 and len(ex) >= 5:
        me, mx = statistics.median(t["dur"] for t in ent), statistics.median(t["dur"] for t in ex)
        if mx > me * 1.05:
            out.append({"id": "exit-slower-than-entrance", "severity": "note", "message": f"element exits (median {mx:.2f}s) are slower than entrances (median {me:.2f}s). Things should take longer to arrive than to leave.",
                        "evidence": {"entrance_median_sec": round(me, 2), "exit_median_sec": round(mx, 2)}})

    # ---- start on the cut
    if scenes:
        first: Dict[str, float] = {}
        for t in sorted(ent, key=lambda x: x["t0"]):
            first.setdefault(t["scene"] or "film", t["t0"])
        starts = {s["id"]: s["start_sec"] for s in scenes}
        on_cut = [sid for sid, t0 in first.items() if sid in starts and abs(t0 - starts[sid]) <= START_ON_CUT_SEC]
        if len(on_cut) >= max(3, len(starts) // 2):
            out.append({"id": "start-on-cut", "severity": "note", "message": f"{len(on_cut)} of {len(starts)} scenes begin their first entrance exactly on the scene cut ({', '.join(on_cut[:6])}). A 0.1-0.3 s offset feels less like a jump cut.",
                        "evidence": {"scenes": on_cut}})

    # ---- conflicts: same property of the same element animated at the same time
    live = [t for t in tweens if t["dur"] > 0 and t["target"] and t["kind"] != "set"]
    by_target: Dict[int, List[Dict[str, Any]]] = {}
    for t in live:
        by_target.setdefault(t["target"], []).append(t)
    conflicts: List[Tuple[Dict[str, Any], Dict[str, Any], float, str]] = []
    transform_mix: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for ts in by_target.values():
        ts = sorted(ts, key=lambda x: x["t0"])
        for i, a in enumerate(ts):
            a_end = a["t0"] + a["dur"] * (1 + max(a["repeat"], 0))
            for b in ts[i + 1:]:
                if b["t0"] >= a_end - OVERLAP_MIN_SEC:
                    break
                ov = min(a_end, b["t0"] + b["dur"] * (1 + max(b["repeat"], 0))) - b["t0"]
                if ov <= OVERLAP_MIN_SEC:
                    continue
                pa = {g for k in a["props"] if (g := prop_group(k))}
                pb = {g for k in b["props"] if (g := prop_group(k))}
                shared = pa & pb
                if shared:
                    conflicts.append((a, b, ov, ",".join(sorted(shared))))
                elif (pa | pb) & TRANSFORM and (a["kind"] == "from" or b["kind"] == "from") and (pa & TRANSFORM) and (pb & TRANSFORM):
                    transform_mix.append((a, b))
    if conflicts:
        worst = sorted(conflicts, key=lambda c: -c[2])[:4]
        shown = "; ".join(f"{a['label']} {p} at {b['t0']:.1f}s overlaps by {ov:.2f}s" for a, b, ov, p in worst)
        out.append({"id": "tween-conflict", "severity": "warn", "message": f"{len(conflicts)} pair(s) of tweens animate the same property of one element at the same time, so one overwrites the other ({shown}). Put the second on a parent or child wrapper, or make them sequential.",
                    "evidence": {"pairs": len(conflicts), "first_t_sec": min(b['t0'] for _, b, _, _ in conflicts), "examples": [{"label": a["label"], "prop": p, "t_sec": b["t0"], "overlap_sec": round(ov, 2)} for a, b, ov, p in worst]}})
    if transform_mix:
        a, b = transform_mix[0]
        out.append({"id": "tween-transform-overlap", "severity": "note", "message": f"{len(transform_mix)} element(s) run a from() entrance and a different transform tween together (first: {a['label']} at {b['t0']:.1f}s). The reference guidance says this can leave the element hidden or off-screen; split the entrance onto a parent wrapper if it does. Unverified on this runtime.",
                    "evidence": {"count": len(transform_mix)}})

    for f in out:
        if waivers and f["id"] in waivers:
            f["waived"] = waivers[f["id"]]
    return out


def summarise(tweens: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Counts a report can quote without repeating the whole dump."""
    roles = Counter(t.get("role") or role(t) or "other" for t in tweens)
    eases = Counter(t["ease"] or "power1.out" for t in tweens if (t.get("role") or role(t)) == "entrance")
    return {"tweens": len(tweens), "entrances": roles["entrance"], "exits": roles["exit"], "entrance_eases": dict(eases.most_common(8))}
