"""Is a project's narration audio current with its script and voice settings?

audio/timeline.json is the record: scripts/build-audio.py writes the voice, speed, pause and every scene's text
into it, so comparing it with src/narration.json and the requested settings says whether narration-full.wav
was made from what the project now asks for. No numpy or Kokoro here, so studio.py validate can import it.

    req = resolve_request(pdir, speed=1.15, voice="am_adam")
    state, reasons = narration_state(pdir, req)   # missing | unknown | current | stale
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_VOICE = "am_adam"
DEFAULT_SPEED = 1.15
DEFAULT_PAUSE = 0.5


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_scenes(pdir: Path) -> List[Dict[str, str]]:
    """[{id, title, text}] from src/narration.json, else research.json's scene_blueprint (legacy)."""
    narration = pdir / "src" / "narration.json"
    if narration.exists():
        scenes = _load(narration).get("scenes", [])
    else:
        research = pdir / "research.json"
        blueprint = _load(research).get("scene_blueprint", []) if research.exists() else []
        scenes = [{"id": sb["scene_id"], "title": sb["title"], "text": sb.get("pedagogical_objective", "")}
                  for sb in blueprint]
    return [{"id": sc.get("id", f"s{i + 1}"), "title": sc.get("title", f"Scene {i + 1}"), "text": sc.get("text", "")}
            for i, sc in enumerate(scenes)]


def resolve_request(pdir: Path, speed: Optional[float] = None, voice: Optional[str] = None,
                    pause: Optional[float] = None) -> Dict[str, Any]:
    """What build-audio.py will synthesise: explicit arguments, then research.json acoustic_guidance, then defaults."""
    acoustic: Dict[str, Any] = {}
    research = pdir / "research.json"
    if research.exists():
        try:
            acoustic = _load(research).get("acoustic_guidance", {}) or {}
        except (OSError, ValueError):
            acoustic = {}
    return {
        "voice": voice or acoustic.get("recommended_voice") or DEFAULT_VOICE,
        "speed": float(speed if speed is not None else acoustic.get("speech_rate") or DEFAULT_SPEED),
        "pause": float(pause if pause is not None else acoustic.get("inter_scene_pause_sec", DEFAULT_PAUSE)),
        "scenes": load_scenes(pdir),
    }


def engine_label() -> str:
    """'kokoro <version>' without importing kokoro (loading it costs about 1.4 GB)."""
    try:
        from importlib.metadata import PackageNotFoundError, version
        return f"kokoro {version('kokoro')}"
    except PackageNotFoundError:
        return "kokoro unknown"


def scene_matches(old: Dict[str, Any], scene: Dict[str, str], timeline: Dict[str, Any], req: Dict[str, Any],
                  engine: Optional[str] = None) -> bool:
    """True when a timeline scene was synthesised from this text with this voice, speed and (if recorded) engine.

    The engine check keeps one film in one voice: after a Kokoro upgrade an edit re-makes every scene, not one."""
    if engine and timeline.get("engine") and timeline["engine"] != engine:
        return False
    return (old.get("id") == scene["id"] and old.get("text") == scene["text"]
            and timeline.get("voice") == req["voice"] and _same(timeline.get("speed"), req["speed"]))


def _same(a: Any, b: Any) -> bool:
    try:
        return abs(float(a) - float(b)) < 1e-6
    except (TypeError, ValueError):
        return False


def narration_state(pdir: Path, req: Dict[str, Any]) -> Tuple[str, List[str]]:
    """('missing' | 'unknown' | 'current' | 'stale', reasons).

    'unknown' means narration-full.wav exists but timeline.json does not record what made it (an older format),
    so it cannot be checked and is reused."""
    if not (pdir / "audio" / "narration-full.wav").exists():
        return "missing", ["audio/narration-full.wav does not exist"]
    tl_path = pdir / "audio" / "timeline.json"
    try:
        timeline = _load(tl_path)
    except (OSError, ValueError):
        return "unknown", ["audio/timeline.json is missing or unreadable"]
    old = timeline.get("scenes") or []
    if timeline.get("voice") is None or timeline.get("speed") is None or any("text" not in s for s in old):
        return "unknown", ["audio/timeline.json does not record the voice, speed and text it was made from"]
    reasons = []
    if timeline["voice"] != req["voice"]:
        reasons.append(f"voice {timeline['voice']} -> {req['voice']}")
    if not _same(timeline["speed"], req["speed"]):
        reasons.append(f"speed {timeline['speed']} -> {req['speed']:g}")
    if timeline.get("pause_sec") is not None and not _same(timeline["pause_sec"], req["pause"]):
        reasons.append(f"pause {timeline['pause_sec']} -> {req['pause']:g}")
    old_ids, new_ids = [s.get("id") for s in old], [s["id"] for s in req["scenes"]]
    if old_ids != new_ids:
        reasons.append(f"scenes {old_ids} -> {new_ids}")
    by_id = {s.get("id"): s for s in old}
    edited = [s["id"] for s in req["scenes"] if s["id"] in by_id and by_id[s["id"]].get("text") != s["text"]]
    if edited:
        reasons.append("text edited in " + ", ".join(edited))
    return ("stale" if reasons else "current"), reasons


def scene_shifts(old: Dict[str, Any], new: Dict[str, Any], tolerance: float) -> List[str]:
    """Scenes whose start or end moved by more than `tolerance` seconds between two timelines."""
    before = {s.get("id"): s for s in old.get("scenes") or []}
    shifts = []
    for s in new.get("scenes") or []:
        o = before.get(s["id"])
        if o is None:
            shifts.append(f"{s['id']} is new ({s['start_time_sec']:.2f}-{s['end_time_sec']:.2f} s)")
            continue
        ds = s["start_time_sec"] - o.get("start_time_sec", 0.0)
        de = s["end_time_sec"] - o.get("end_time_sec", o.get("start_time_sec", 0.0) + o.get("duration_sec", 0.0))
        if abs(ds) > tolerance or abs(de) > tolerance:
            shifts.append(f"{s['id']} start {ds:+.2f} s, end {de:+.2f} s")
    gone = [k for k in before if k not in {s["id"] for s in new.get("scenes") or []}]
    if gone:
        shifts.append("removed: " + ", ".join(gone))
    return shifts
