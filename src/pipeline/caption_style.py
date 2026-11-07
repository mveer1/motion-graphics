"""Caption design: pick a preset for a film, give every cue a role and a lane, and lint the result.

The design system lives in specs/caption-presets.json (presets, the style map, lanes, roles) and is explained
in docs/caption-design.md. This module is the pure-Python half of it:

  load_spec        read specs/caption-presets.json
  pick_preset      pinned id, else the style map, else the fallback
  video_type_of    reel / long-reel / youtube from the brief, else from the project's length and format
  resolve          the small object written to src/captions.js as window.STUDIO_CAPTION_PRESET
  annotate         add a role (hook / body / outro), an optional lane and emphasis flags to cues
  lint_cues        warnings for cues that will not fit the preset in the film's format

The runtime (src/studio/studio-compositions.js, Studio.comp.captions) and the CSS in studio-base.css do the
drawing; they must agree with the numbers here, and tests/test-short-form.py checks that they do.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

SPEC_PATH = Path(__file__).resolve().parents[2] / "specs" / "caption-presets.json"
LANES = ("lower", "mid", "upper")
EMPHASIS_RE = re.compile(r"[0-9$€£¥%]")
# Portrait cue length, and landscape cue length, above which a cue no longer fits two lines at preset size.
MAX_CHARS_PORTRAIT = 44
MAX_CHARS_WIDE = 90


def load_spec(path: Optional[Path] = None) -> Dict[str, Any]:
    return json.loads((path or SPEC_PATH).read_text(encoding="utf-8"))


def pick_preset(style: Optional[str], pinned: Optional[str] = None, spec: Optional[Dict[str, Any]] = None) -> str:
    """Pinned preset id (project.json audio.caption_preset or --preset) wins, then the style map, then the fallback."""
    spec = spec or load_spec()
    if pinned:
        if pinned not in spec["presets"]:
            raise ValueError(f"unknown caption preset '{pinned}'; known: {', '.join(spec['presets'])}")
        return pinned
    return spec["style_map"].get(style or "", spec["fallback_preset"])


def video_type_of(brief: Optional[Dict[str, Any]], duration_sec: float, fmt: str) -> str:
    vt = ((brief or {}).get("deliverables") or {}).get("video_type")
    if vt in ("reel", "long-reel", "youtube"):
        return vt
    if fmt == "landscape" or duration_sec > 180:
        return "youtube"
    return "reel" if duration_sec <= 60 else "long-reel"


def type_defaults(vtype: str, spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    spec = spec or load_spec()
    return spec["type_defaults"].get(vtype, spec["type_defaults"]["reel"])


def lane_for(role: str, fmt: str, spec: Dict[str, Any]) -> str:
    lane = spec["roles"][role]["lane"][fmt]
    return lane if lane in spec["lanes"][fmt] else "lower"


def resolve(style: Optional[str], fmt: str, pinned: Optional[str] = None, spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """What the runtime needs for one film: the preset id and, for each role, the lane and size scale in this format."""
    spec = spec or load_spec()
    pid = pick_preset(style, pinned, spec)
    p = spec["presets"][pid]
    return {
        "id": pid,
        "format": fmt,
        "enter": p["enter"],
        "roles": {r: {"lane": lane_for(r, fmt, spec), "scale": spec["roles"][r]["scale"]} for r in ("hook", "body", "outro")},
    }


def is_emphasis(word: str) -> bool:
    return bool(EMPHASIS_RE.search(word))


def annotate(cues: List[Dict[str, Any]], *, fmt: str, scene_spans: Sequence[Dict[str, Any]],
             storyboard_scenes: Optional[Sequence[Dict[str, Any]]] = None, spec: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Give each cue a role and, where the storyboard asks, a lane; flag emphasised words. Edits cues in place.

    scene_spans: [{"start": s, "end": e}] in film seconds, in order (the narration timeline); the last one is the outro.
    storyboard_scenes: storyboard.json scenes; a scene with `caption_lane` moves every cue whose middle falls in it."""
    spec = spec or load_spec()
    hook_end = float(spec["roles"]["hook"]["window_sec"])
    last_start = scene_spans[-1]["start"] if len(scene_spans) > 1 else None
    for c in cues:
        if c["start"] < hook_end:
            c["role"] = "hook"
        elif last_start is not None and c["start"] >= last_start - 1e-6:
            c["role"] = "outro"
        else:
            c["role"] = "body"
        mid = (c["start"] + c["end"]) / 2
        for sc in storyboard_scenes or []:
            lane = sc.get("caption_lane")
            if lane and sc["start_sec"] <= mid < sc["end_sec"]:
                if lane not in spec["lanes"][fmt]:
                    lane = "lower"  # a lane this format does not have (mid on landscape)
                c["lane"] = lane
                break
        for w in c.get("words", []):
            if is_emphasis(w["text"]):
                w["em"] = True
            else:
                w.pop("em", None)
    return cues


def lint_cues(cues: Sequence[Dict[str, Any]], fmt: str, preset: Optional[Dict[str, Any]] = None,
              spec: Optional[Dict[str, Any]] = None) -> List[str]:
    """Warnings for a cue list; empty when it fits. Pure text checks: pixel contrast and overflow are frame-review's job."""
    spec = spec or load_spec()
    warns: List[str] = []
    limit = MAX_CHARS_PORTRAIT if fmt == "portrait" else MAX_CHARS_WIDE
    long_cues = [c for c in cues if len(c["text"]) > limit]
    if long_cues:
        c = long_cues[0]
        warns.append(f"{len(long_cues)} caption cue(s) are over {limit} characters, which will not fit two lines in {fmt} "
                     f"(first: {c['start']:.1f}s, {len(c['text'])} characters). Use phrase grouping or shorten the line.")
    lanes = []
    for c in cues:
        role = c.get("role", "body")
        lane = c.get("lane") or (preset["roles"][role]["lane"] if preset else lane_for(role, fmt, spec))
        if lane not in lanes:
            lanes.append(lane)
    if len(lanes) > 2:
        warns.append(f"captions use {len(lanes)} lanes ({', '.join(lanes)}); keep to two so the eye is not hunting.")
    if cues and fmt == "portrait" and cues[0].get("role") == "hook" and cues[0]["start"] > 1.5:
        warns.append(f"the first caption appears at {cues[0]['start']:.1f}s; the hook runs without one.")
    return warns
