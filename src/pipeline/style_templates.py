"""Style template helpers shared by scripts/studio.py and scripts/motion-catalogue.py.

A style template (catalogue/data/style-templates/) is a versioned contract for one kind of
visual job. This module holds the semantic rules the JSON schema cannot express:

  check_template   cross-references and internal consistency of one template record
  recommend        rank templates for a brief (categories plus keyword evidence)
  check_project    how a project measures up to the template it subscribes to, before any render
  revisions_since  what changed in a template after a version a project was built against

Everything here is read-only and needs no render host.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "catalogue" / "schemas" / "style-template.schema.json"
CAPABILITY_COLLECTIONS = ("primitives", "effects", "recipes", "compositions")

# (level, message). Levels: "warn" needs a decision, "note" is information.
Finding = Tuple[str, str]


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def capability_ids(records: Dict[str, Dict[str, Any]]) -> set:
    ids: set = set()
    for coll in CAPABILITY_COLLECTIONS:
        ids.update(records.get(coll, {}))
    return ids


def check_template(tpl: Dict[str, Any], records: Dict[str, Dict[str, Any]],
                   category_ids: set, projects_dir: Optional[Path] = None) -> Tuple[List[str], List[str]]:
    """Errors and warnings for one template record (the schema has already passed)."""
    errors: List[str] = []
    warnings: List[str] = []
    tid = tpl["id"]
    styles = records.get("styles", {})
    profiles = records.get("design-profiles", {})

    versions = [r["version"] for r in tpl["revisions"]]
    if versions != sorted(set(versions)):
        errors.append(f"'{tid}' revisions must be strictly increasing by version (got {versions}).")
    if tpl["version"] != max(versions):
        errors.append(f"'{tid}' version {tpl['version']} does not match its newest revision {max(versions)}.")

    default = tpl["look"]["style"]
    allowed = {default}
    if default not in styles:
        errors.append(f"'{tid}' default style '{default}' is not registered.")
    elif styles[default].get("mode") != "light":
        errors.append(f"'{tid}' default style '{default}' is {styles[default].get('mode')}; the workspace default is light. "
                      "Put dark styles under look.alternates with a `when`.")
    for alt in tpl["look"].get("alternates", []):
        allowed.add(alt["style"])
        if alt["style"] not in styles:
            errors.append(f"'{tid}' alternate style '{alt['style']}' is not registered.")
    for sid in allowed & set(styles):
        if styles[sid].get("status") in ("blocked", "deprecated"):
            errors.append(f"'{tid}' uses {styles[sid]['status']} style '{sid}'.")

    prof_id = tpl["look"].get("design_profile")
    if prof_id:
        prof = profiles.get(prof_id)
        if not prof:
            errors.append(f"'{tid}' design profile '{prof_id}' is not registered.")
        elif prof.get("style") and prof["style"] not in allowed:
            warnings.append(f"'{tid}' profile '{prof_id}' is implemented by style '{prof['style']}', which is neither the default nor an alternate.")

    for cat in tpl["selection"]["categories"]:
        if cat not in category_ids:
            errors.append(f"'{tid}' lists unknown category '{cat}' (specs/categories.json).")

    caps = capability_ids(records)
    used = [(s["role"], c) for s in tpl["scene_grammar"] for c in s.get("capabilities", [])]
    used += [("motion", c) for k in ("preferred_capabilities", "discouraged_capabilities") for c in tpl["motion"].get(k, [])]
    for where, cap in used:
        if cap not in caps:
            errors.append(f"'{tid}' ({where}) names unregistered capability '{cap}'.")
    both = set(tpl["motion"].get("preferred_capabilities", [])) & set(tpl["motion"].get("discouraged_capabilities", []))
    if both:
        errors.append(f"'{tid}' both prefers and discourages {sorted(both)}.")

    roles = [s["role"] for s in tpl["scene_grammar"]]
    if len(roles) != len(set(roles)):
        errors.append(f"'{tid}' scene_grammar repeats a role.")
    if tpl["rules"]["max_beat_gap_sec"] > 3.0:
        warnings.append(f"'{tid}' max_beat_gap_sec {tpl['rules']['max_beat_gap_sec']} is over the 2-3 s the anti-laziness rule allows (CLAUDE.md).")
    if tpl["rules"]["max_beat_gap_sec"] > tpl["rules"]["max_scene_sec"]:
        errors.append(f"'{tid}' max_beat_gap_sec exceeds max_scene_sec.")

    if tpl["status"] == "approved":
        if not tpl.get("validation", {}).get("evidence"):
            errors.append(f"'{tid}' is approved without validation evidence.")
        if not tpl.get("reference_projects"):
            errors.append(f"'{tid}' is approved but lists no reference projects.")

    if projects_dir is not None:
        for ref in tpl.get("reference_projects", []):
            if not (projects_dir / ref["project"]).exists():
                warnings.append(f"'{tid}' reference project '{ref['project']}' is not in this checkout.")
    return errors, warnings


# --------------------------------------------------------------------------- selection
def brief_text(brief: Dict[str, Any]) -> str:
    """The words of a brief that say what the film is about and how it should feel."""
    parts = [brief.get("title", ""), brief.get("objective", "")]
    msg = brief.get("message", {})
    parts += [msg.get("core_message", "")] + list(msg.get("key_points", []))
    parts += list(brief.get("tone", {}).get("keywords", []))
    return " ".join(p for p in parts if p).lower()


def recommend(records: Dict[str, Dict[str, Any]], categories: List[str], text: str = "",
              formats: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Rank the usable templates for a brief. Heuristic: categories (first is primary) plus keyword
    hits. The result lists its reasons so the ranking can be overruled with eyes open."""
    text = text.lower()
    ranked = []
    for tid, tpl in records.get("style-templates", {}).items():
        if tpl.get("status") in ("blocked", "deprecated"):
            continue
        score = 0.0
        why: List[str] = []
        cats = tpl["selection"]["categories"]
        for i, c in enumerate(categories):
            if c in cats:
                pts = 3.0 if i == 0 else 1.5
                score += pts
                why.append(f"category {c}" + (" (primary)" if i == 0 else ""))
        hits = [k for k in tpl["selection"]["keywords"] if re.search(r"(?<![a-z0-9])" + re.escape(k.lower()) + r"(?![a-z0-9])", text)]
        if hits:
            score += min(len(hits), 6)
            why.append("keywords: " + ", ".join(hits[:6]))
        ranked.append({"id": tid, "name": tpl["name"], "score": round(score, 1), "why": why,
                       "job": tpl["visual_job"]["kind"], "status": tpl["status"]})
    ranked.sort(key=lambda r: (-r["score"], r["id"]))
    return ranked


# --------------------------------------------------------------------------- refinement loop
def revisions_since(tpl: Dict[str, Any], pinned: int) -> List[Dict[str, Any]]:
    return [r for r in tpl["revisions"] if r["version"] > pinned]


# --------------------------------------------------------------------------- project check
def _words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’.-]*", text or ""))


def is_portrait_first(project: Dict[str, Any]) -> bool:
    """Portrait is the only or the primary format (docs/VISION.md: portrait is the default deliverable)."""
    fmts = project.get("formats", [])
    ids = [f["id"] for f in fmts]
    primary = next((f["id"] for f in fmts if f.get("primary")), ids[0] if ids else None)
    return ids == ["portrait"] or primary == "portrait"


def _scene_durations(pdir: Path, scenes: List[Dict[str, Any]]) -> Tuple[Dict[str, float], str]:
    """Measured clip duration per scene id from audio/timeline.json when it exists, else the storyboard span."""
    tl = pdir / "audio" / "timeline.json"
    if tl.exists():
        try:
            measured = {s["id"]: float(s["duration_sec"]) for s in load_json(tl).get("scenes", []) if "duration_sec" in s}
            if measured:
                return measured, "measured clips (audio/timeline.json)"
        except (ValueError, KeyError, TypeError):
            pass
    return {s["id"]: s["end_sec"] - s["start_sec"] for s in scenes}, "storyboard span (narration not yet measured)"


def beat_gaps(scene: Dict[str, Any]) -> Tuple[List[float], float, bool]:
    """(beat times as absolute film seconds, longest gap, beats were scene-relative).

    storyboard-spec does not say whether at_sec is film time or scene time. Korea and cloud use film
    time; fridge restarts at 0 in every scene. A scene whose first beat falls before its own start can
    only be scene-relative, so it is shifted."""
    start, end = scene["start_sec"], scene["end_sec"]
    times = sorted(b["at_sec"] for b in scene.get("beats", []))
    relative = bool(times) and start > 0.5 and times[0] < start - 0.05
    if relative:
        times = [t + start for t in times]
    marks = [start] + [t for t in times if start <= t <= end] + [end]
    gap = max(b - a for a, b in zip(marks, marks[1:]))
    return times, gap, relative


def check_project(pdir: Path, project: Dict[str, Any], brief: Optional[Dict[str, Any]],
                  tpl: Dict[str, Any], category_ids: Optional[set] = None) -> List[Finding]:
    """Compare a project with the template it subscribes to. Static only: nothing is rendered."""
    out: List[Finding] = []
    tid, rules = tpl["id"], tpl["rules"]
    pin = project.get("style_template", {})

    pinned = pin.get("version")
    if pinned is not None and pinned < tpl["version"]:
        news = "; ".join(f"v{r['version']}: {r['change']}" for r in revisions_since(tpl, pinned))
        out.append(("warn", f"built against {tid} v{pinned}, template is now v{tpl['version']}. Since then: {news}"))
    elif pinned is not None and pinned > tpl["version"]:
        out.append(("warn", f"pinned to {tid} v{pinned} but the template is only v{tpl['version']}."))

    allowed = {tpl["look"]["style"]} | {a["style"] for a in tpl["look"].get("alternates", [])}
    if project.get("style") not in allowed:
        out.append(("warn", f"style '{project.get('style')}' is not the template's default ('{tpl['look']['style']}') "
                            f"or a listed alternate ({', '.join(sorted(allowed - {tpl['look']['style']})) or 'none'}). Fine if deliberate."))
    elif project.get("style") != tpl["look"]["style"]:
        alt = next(a for a in tpl["look"]["alternates"] if a["style"] == project["style"])
        out.append(("note", f"uses alternate style '{alt['style']}' (template says: {alt['when']})"))

    if brief and brief.get("categories") and not set(brief["categories"]) & set(tpl["selection"]["categories"]):
        out.append(("note", f"brief categories {brief['categories']} share nothing with the template's {tpl['selection']['categories']}; "
                            f"the test is the visual job: {tpl['visual_job']['viewer_leaves_able_to']}"))

    sb_path = pdir / "storyboard.json"
    if not sb_path.exists():
        out.append(("note", "no storyboard.json yet; pacing rules cannot be checked."))
        return out
    sb = load_json(sb_path)
    scenes = sorted(sb.get("scenes", []), key=lambda s: s["start_sec"])
    durations, dur_src = _scene_durations(pdir, scenes)

    narration: Dict[str, str] = {}
    nj = pdir / "src" / "narration.json"
    if nj.exists():
        narration = {s["id"]: s.get("text", "") for s in load_json(nj).get("scenes", [])}

    discouraged = set(tpl["motion"].get("discouraged_capabilities", []))
    no_beats, relative_scenes = [], []

    short_form = rules.get("short_form")
    if short_form and is_portrait_first(project):
        limit = short_form["max_card_words"]
        long_cards = [(sc["id"], t) for sc in scenes for t in sc.get("on_screen_text", []) if _words(t) > limit]
        total_cards = sum(len(sc.get("on_screen_text", [])) for sc in scenes)
        if long_cards:
            shown = "; ".join(f"{sid}: \"{t[:42]}\" ({_words(t)})" for sid, t in long_cards[:3])
            out.append(("warn", f"{len(long_cards)} of {total_cards} on-screen text items run over {limit} words ({shown}). "
                                "A card is read at arm's length before the viewer is listening; shorten it or split it across beats."))
    for i, sc in enumerate(scenes):
        sid, span = sc["id"], sc["end_sec"] - sc["start_sec"]
        if span > rules["max_scene_sec"] + 1e-6 and not sc.get("beats"):
            out.append(("warn", f"scene {sid} runs {span:.1f}s, over this template's {rules['max_scene_sec']:g}s and has no beats. Split it or plan beats."))

        text = narration.get(sid) or sc.get("narration", "")
        dur = durations.get(sid)
        if text and dur:
            per10 = _words(text) / dur * 10
            if per10 > rules["words_per_10s_max"] + 1e-6:
                out.append(("warn", f"scene {sid} narration is {per10:.0f} words per 10 s over {dur:.1f}s ({dur_src}); "
                                    f"budget {rules['words_per_10s_max']:g}. Cut words, do not raise the speed."))

        if sc.get("beats"):
            times, gap, rel = beat_gaps(sc)
            if rel:
                relative_scenes.append(sid)
            if gap > rules["max_beat_gap_sec"] + 1e-6:
                out.append(("warn", f"scene {sid} has a {gap:.1f}s stretch with no planned visual event (limit {rules['max_beat_gap_sec']:g}s). Add a beat."))
            if i == 0 and times and times[0] - sc["start_sec"] > rules["hook_within_sec"] + 1e-6:
                out.append(("warn", f"first beat lands at {times[0]:.1f}s; this template wants the hook by {rules['hook_within_sec']:g}s."))
        elif span > rules["max_beat_gap_sec"]:
            no_beats.append(sid)

        for cap in sc.get("capabilities", []):
            if cap in discouraged:
                out.append(("warn", f"scene {sid} uses '{cap}', which this template discourages."))

    if no_beats:
        out.append(("note", f"scenes {', '.join(no_beats)} have no beats, so the gap rule ({rules['max_beat_gap_sec']:g}s) cannot be checked before the render. "
                            "Add storyboard beats (film time) for each planned visual event."))
    if relative_scenes:
        out.append(("note", f"scenes {', '.join(relative_scenes)} have beats in scene time; most storyboards use film time. Read as scene-relative."))
    return out
