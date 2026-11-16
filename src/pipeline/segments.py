"""Segment plan for rendering a long film in pieces (used by scripts/render-segments.py).

A 12-minute film is 21,600 frames from one headless-Chrome session on an 8 GB machine, and a crash at minute 11
loses all of it. Rendering in segments of about 90 s bounds each Chrome session, makes every finished segment a
checkpoint, and lets an interrupted build resume. Segments are whole frames, contiguous, and cut at a scene edge
where one is close enough, so a cut falls where the picture already changes.

  plan_segments   frames -> [(start_frame, end_frame)], end exclusive
  boundaries_of   scene / chapter edges (seconds) from a storyboard
  plan_matches    does a recorded plan still equal the planned one

Pure Python; no browser, no ffmpeg.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Tuple


def boundaries_of(storyboard: Dict[str, Any] | None) -> List[float]:
    """Sorted unique scene and chapter edges in seconds. Chapter edges are scene edges by validate's rule."""
    edges: set = set()
    for sc in (storyboard or {}).get("scenes", []):
        edges.add(round(float(sc["start_sec"]), 3))
        edges.add(round(float(sc["end_sec"]), 3))
    for ch in (storyboard or {}).get("chapters", []):
        edges.add(round(float(ch["start_sec"]), 3))
        edges.add(round(float(ch["end_sec"]), 3))
    return sorted(edges)


def plan_segments(total_frames: int, fps: int, segment_sec: float,
                  boundaries_sec: Sequence[float] = (), flex: float = 0.35) -> List[Tuple[int, int]]:
    """Cut `total_frames` into contiguous (start, end) frame ranges of about `segment_sec` each.

    From the cursor, the cut goes to the scene edge nearest to cursor + segment_sec if it lies within +-flex of the
    target; otherwise to the target frame itself. The last segment never falls under half a target: a short
    remainder is merged into the one before. Always covers [0, total_frames) exactly."""
    if total_frames <= 0:
        return []
    target = max(1, int(round(segment_sec * fps)))
    edge_frames = sorted({int(round(b * fps)) for b in boundaries_sec if 0 < b * fps < total_frames})
    cuts: List[int] = []
    cursor = 0
    while total_frames - cursor > target * (1 + flex):
        ideal = cursor + target
        lo, hi = cursor + int(target * (1 - flex)), cursor + int(target * (1 + flex))
        near = [f for f in edge_frames if lo <= f <= hi]
        cut = min(near, key=lambda f: abs(f - ideal)) if near else ideal
        cuts.append(cut)
        cursor = cut
    points = [0] + cuts + [total_frames]
    if len(points) > 2 and points[-1] - points[-2] < target // 2:
        del points[-2]
    return list(zip(points[:-1], points[1:]))


def segment_name(i: int) -> str:
    return f"seg-{i + 1:03d}.mp4"


def plan_record(plan: Iterable[Tuple[int, int]]) -> List[Dict[str, int]]:
    return [{"i": i, "start_frame": a, "end_frame": b, "frames": b - a} for i, (a, b) in enumerate(plan)]


def plan_matches(recorded: Sequence[Dict[str, Any]], plan: Sequence[Tuple[int, int]]) -> bool:
    return [(r["start_frame"], r["end_frame"]) for r in recorded] == list(plan)
