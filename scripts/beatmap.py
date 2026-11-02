#!/usr/bin/env python3
"""Narrative arc, beat map and shot plan: planning before production.

  arcs [--show ID]              list the arc library (specs/narrative-arcs.json) or print one arc
  init <slug> --arc ID          scaffold projects/<slug>/beatmap.json with one beat per arc stage (TODO markers)
  validate <slug|path>          schema + planning checks (purpose, takeaway, variety, asset strategy, claims)
  storyboard <slug> [--force]   derive storyboard.json scenes from the beat map (timing from audio/timeline.json when present)
  status <slug>                 beat table: stage, importance, duration, medium, transition

Planning checks produce errors (the plan cannot be executed) and warnings (leads worth a second look).
A warning is never a verdict: declare `intent` on a beat to record that a choice is deliberate.
Run with python3.12 or .venv/bin/python (needs jsonschema).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
ARCS_PATH = ROOT / "specs" / "narrative-arcs.json"
SPEC_PATH = ROOT / "specs" / "beatmap-spec.json"
PROJECTS = ROOT / "projects"
MEDIA_NEEDING_PROVIDER = {"generated-image", "generated-video"}


def load_json(p: Path) -> Any:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p: Path, data: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def arcs() -> Dict[str, Dict[str, Any]]:
    return {a["id"]: a for a in load_json(ARCS_PATH)["arcs"]}


def project_dir(slug_or_path: str) -> Path:
    p = Path(slug_or_path)
    if p.suffix == ".json":
        return p.parent
    if p.is_dir():
        return p
    cand = PROJECTS / slug_or_path
    if cand.is_dir():
        return cand
    # grouped layout: projects/<title>/<version>
    hits = [d for d in PROJECTS.glob(f"*/{slug_or_path}") if d.is_dir()]
    if len(hits) == 1:
        return hits[0]
    sys.exit(f"error: project {slug_or_path!r} not found under projects/")


def beatmap_path(slug_or_path: str) -> Path:
    p = Path(slug_or_path)
    return p if p.suffix == ".json" else project_dir(slug_or_path) / "beatmap.json"


# ----------------------------------------------------------------------------- arcs / init
def cmd_arcs(a: argparse.Namespace) -> int:
    lib = arcs()
    if a.show:
        arc = lib.get(a.show)
        if not arc:
            sys.exit(f"error: unknown arc {a.show!r}; try: {', '.join(lib)}")
        print(f"{arc['name']}  [{arc['id']}]  best for: {', '.join(arc['best_for'])}")
        for i, s in enumerate(arc["stages"], 1):
            print(f"  {i}. {s['id']:<18} ({s['function']}, {s['emotion']})  {s['guidance']}")
        print(f"  pitfall: {arc['pitfall']}")
        return 0
    for arc in lib.values():
        print(f"{arc['id']:<34} {' > '.join(s['id'] for s in arc['stages'])}")
    return 0


def cmd_init(a: argparse.Namespace) -> int:
    arc = arcs().get(a.arc)
    if not arc:
        sys.exit(f"error: unknown arc {a.arc!r}")
    pdir = project_dir(a.slug)
    path = pdir / "beatmap.json"
    if path.exists() and not a.force:
        sys.exit(f"error: {path} exists (use --force)")
    n = len(arc["stages"])
    total = a.duration or 60.0
    beats = []
    for s in arc["stages"]:
        beats.append({
            "id": s["id"], "stage": s["id"], "story_function": s["function"],
            "purpose": f"TODO: why the '{s['id']}' beat exists. {s['guidance']}",
            "viewer_takeaway": "TODO: what the viewer now knows or feels",
            "emotional_tone": s["emotion"], "target_duration_sec": round(total / n, 1),
            "visual_concept": "TODO: what the viewer SEES that carries the idea",
        })
    doc = {"spec_version": 1, "slug": pdir.name if not re.match(r"^v\d", pdir.name) else pdir.parent.name,
           "concept": {"logline": "TODO: one sentence the whole film is about", "viewer_change": "TODO: what the viewer knows or feels at the end that they did not at the start"},
           "arc": {"id": arc["id"], "stages": [s["id"] for s in arc["stages"]], "emotional_curve": [s["emotion"] for s in arc["stages"]]},
           "target_duration_sec": total, "beats": beats}
    write_json(path, doc)
    print(f"wrote {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path} ({n} beats from arc '{arc['id']}'); fill every TODO, then run validate")
    return 0


# ----------------------------------------------------------------------------- validate
def tokens(s: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", s.lower())}


def jaccard(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def check(doc: Dict[str, Any], pdir: Optional[Path]) -> Tuple[List[str], List[str]]:
    import jsonschema

    errs: List[str] = []
    warns: List[str] = []
    v = jsonschema.Draft7Validator(load_json(SPEC_PATH))
    for e in sorted(v.iter_errors(doc), key=lambda e: list(e.absolute_path)):
        errs.append(f"schema {'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message[:180]}")
    if errs:
        return errs, warns
    lib = arcs()
    arc = doc["arc"]
    beats = doc["beats"]
    ids = [b["id"] for b in beats]
    if len(ids) != len(set(ids)):
        errs.append("duplicate beat ids")
    if arc["id"] != "custom" and arc["id"] not in lib:
        errs.append(f"arc {arc['id']!r} is not in specs/narrative-arcs.json (use 'custom' and explain in arc.notes)")
    if arc["id"] in lib:
        known = {s["id"] for s in lib[arc["id"]]["stages"]}
        extra = [s for s in arc["stages"] if s not in known]
        if extra:
            warns.append(f"arc stages {extra} are not in library arc '{arc['id']}'; say why in arc.notes")
        missing = known - set(arc["stages"])
        if missing and not arc.get("notes"):
            warns.append(f"library stages {sorted(missing)} dropped without arc.notes")
    for b in beats:
        bid = b["id"]
        if b["stage"] not in arc["stages"]:
            errs.append(f"beat {bid}: stage {b['stage']!r} is not in arc.stages")
        blob = json.dumps(b)
        if "TODO" in blob:
            errs.append(f"beat {bid}: unresolved TODO")
        if b.get("narration") and jaccard(b["visual_concept"], b["narration"]) > 0.55:
            warns.append(f"beat {bid}: visual_concept restates the narration (token overlap {jaccard(b['visual_concept'], b['narration']):.2f}); describe what is SEEN, not what is said")
        sids = [s["id"] for s in b.get("shots", [])]
        if len(sids) != len(set(sids)):
            errs.append(f"beat {bid}: duplicate shot ids")
        for need in b.get("assets", []):
            if need.get("strategy") == "generate":
                if not need.get("fallback"):
                    errs.append(f"beat {bid}: asset '{need['role']}' is generated but names no fallback (a provider outage must not stop the film)")
            if need["medium"] in MEDIA_NEEDING_PROVIDER and need.get("strategy") == "build-in-code":
                errs.append(f"beat {bid}: asset '{need['role']}' is {need['medium']} but strategy is build-in-code")
            if need["medium"] in ("data-visualization", "typography") and need.get("strategy") == "generate":
                warns.append(f"beat {bid}: asset '{need['role']}' is {need['medium']}: deterministic code is usually more accurate than generation")
        if b.get("claims") and not doc["concept"].get("research"):
            warns.append(f"beat {bid}: states claims but concept.research names no dossier")
    # variety and emphasis
    anchors = sum(1 for b in beats if b.get("importance") == "anchor")
    if len(beats) >= 4 and anchors / len(beats) > 0.4:
        warns.append(f"{anchors}/{len(beats)} beats are marked anchor; emphasis is spent, not spread")
    comps = [s.get("composition", "").strip().lower() for b in beats for s in b.get("shots", []) if s.get("composition")]
    for c, n in Counter(comps).items():
        if n >= 3:
            warns.append(f"composition {c!r} is planned {n} times; vary it or declare why")
    cams = [s.get("camera_movement") for b in beats for s in b.get("shots", []) if s.get("camera_movement")]
    if len(cams) >= 5 and Counter(cams).most_common(1)[0][1] / len(cams) > 0.7:
        warns.append(f"camera movement {Counter(cams).most_common(1)[0][0]!r} is {Counter(cams).most_common(1)[0][1]}/{len(cams)} of planned shots")
    trans = [b["transition_in"]["type"] for b in beats[1:] if b.get("transition_in")]
    if len(trans) >= 4 and Counter(trans).most_common(1)[0][1] / len(trans) > 0.6:
        warns.append(f"transition {Counter(trans).most_common(1)[0][0]!r} is {Counter(trans).most_common(1)[0][1]}/{len(trans)} of planned seams")
    for b in beats[1:]:
        t = b.get("transition_in")
        if t and t["type"] in ("match-cut", "push", "wipe", "zoom-through") and not t.get("motivation"):
            warns.append(f"beat {b['id']}: {t['type']} transition without a stated motivation")
    tot = sum(b.get("target_duration_sec", 0) for b in beats)
    tgt = doc.get("target_duration_sec")
    if tgt and tot and abs(tot - tgt) / tgt > 0.1:
        warns.append(f"beat durations sum to {tot:.1f}s vs target {tgt:.1f}s")
    if doc.get("global_direction", {}).get("sound_design") is None:
        warns.append("no global_direction.sound_design: sound is part of the plan, not an afterthought")
    if pdir and (pdir / "research.json").exists():
        try:
            rs = load_json(pdir / "research.json")
            src_ids = {str(s.get("id", s.get("url", ""))) for s in rs.get("sources", rs.get("citations", [])) if isinstance(s, dict)}
            if src_ids:
                for b in beats:
                    for c in b.get("claims", []):
                        if c["source"] not in src_ids:
                            warns.append(f"beat {b['id']}: claim source {c['source']!r} not found in research.json sources")
        except (ValueError, OSError):
            pass
    return errs, warns


def cmd_validate(a: argparse.Namespace) -> int:
    path = beatmap_path(a.target)
    doc = load_json(path)
    errs, warns = check(doc, path.parent)
    for e in errs:
        print("error:", e)
    for w in warns:
        print("warn: ", w)
    print(f"{path.name}: {len(doc.get('beats', []))} beats, {len(errs)} errors, {len(warns)} warnings")
    return 1 if errs else 0


# ----------------------------------------------------------------------------- status / storyboard
def cmd_status(a: argparse.Namespace) -> int:
    doc = load_json(beatmap_path(a.target))
    print(f"{'beat':<18}{'stage':<18}{'imp':<11}{'sec':>5}  {'transition_in':<12}{'media'}")
    for b in doc["beats"]:
        media = ",".join(sorted({n["medium"] for n in b.get("assets", [])})) or "-"
        print(f"{b['id']:<18}{b['stage']:<18}{b.get('importance', '-'):<11}{b.get('target_duration_sec', 0):>5}  {(b.get('transition_in') or {}).get('type', '-'):<12}{media}")
    return 0


def beat_times(pdir: Path, beats: List[Dict[str, Any]], target: Optional[float] = None) -> Tuple[List[Tuple[float, float]], str]:
    tl = pdir / "audio" / "timeline.json"
    if tl.exists():
        try:
            t = load_json(tl)
            segs = t.get("scenes") or t.get("segments") or t.get("clips")
            if isinstance(segs, list) and len(segs) == len(beats):
                starts = [float(s.get("start_time_sec", s.get("start", s.get("start_sec", 0)))) for s in segs]
                last_end = float(segs[-1].get("end_time_sec", segs[-1].get("end", segs[-1].get("end_sec", 0))))
                total = max(last_end, float(target or 0))
                # scenes are contiguous: each runs until the next begins, the last until the film ends
                return [(starts[i], starts[i + 1] if i + 1 < len(starts) else total) for i in range(len(starts))], "audio/timeline.json"
        except (ValueError, OSError, TypeError):
            pass
    out, t0 = [], 0.0
    for b in beats:
        d = float(b.get("target_duration_sec", 4.0))
        out.append((round(t0, 3), round(t0 + d, 3)))
        t0 += d
    return out, "beat target durations (not measured)"


def cmd_storyboard(a: argparse.Namespace) -> int:
    pdir = project_dir(a.target)
    doc = load_json(pdir / "beatmap.json")
    errs, _ = check(doc, pdir)
    if errs:
        sys.exit("error: beatmap does not validate; fix it first:\n  " + "\n  ".join(errs))
    out = pdir / "storyboard.json"
    if out.exists() and not a.force:
        sys.exit(f"error: {out.name} exists (use --force)")
    brief = load_json(pdir / "brief.json") if (pdir / "brief.json").exists() else {}
    times, basis = beat_times(pdir, doc["beats"], doc.get("target_duration_sec"))
    scenes = []
    for i, (b, (s, e)) in enumerate(zip(doc["beats"], times)):
        nxt = doc["beats"][i + 1] if i + 1 < len(doc["beats"]) else None
        tr = (nxt or {}).get("transition_in") or {"type": "hold-end" if nxt is None else "crossfade"}
        scene = {"id": b["id"], "title": b["id"].replace("-", " ").title(), "start_sec": s, "end_sec": e, "purpose": b["purpose"],
                 "visual": b["visual_concept"], "capabilities": [], "beat_id": b["id"],
                 "transition_out": {k: v for k, v in {"type": tr["type"], "duration_sec": tr.get("duration_sec"), "continuity": tr.get("motivation")}.items() if v is not None}}
        if b.get("narration"):
            scene["narration"] = b["narration"]
        if b.get("style_variant"):
            scene["style_variant"] = b["style_variant"]
        if b.get("intent"):
            scene["intent"] = b["intent"]
        refs = [n["asset_id"] for n in b.get("assets", []) if n.get("asset_id")]
        if refs:
            scene["asset_refs"] = refs
        scenes.append(scene)
    sb = {"spec_version": 1, "slug": doc["slug"], "direction": brief.get("selected_direction", "set-direction"),
          "timing_source": "narration" if basis.startswith("audio") else "fixed", "duration_sec": times[-1][1], "scenes": scenes}
    write_json(out, sb)
    print(f"wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}: {len(scenes)} scenes, timing from {basis}")
    if sb["direction"] == "set-direction":
        print("note: no brief.json selected_direction found; set 'direction' to a brief.json creative_directions id; studio.py validate will flag it until you do")
    print("note: 'capabilities' is empty; fill catalogue ids from each beat's 'implementation' text")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("arcs"); p.add_argument("--show"); p.set_defaults(fn=cmd_arcs)
    p = sub.add_parser("init"); p.add_argument("slug"); p.add_argument("--arc", required=True); p.add_argument("--duration", type=float); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_init)
    p = sub.add_parser("validate"); p.add_argument("target"); p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("status"); p.add_argument("target"); p.set_defaults(fn=cmd_status)
    p = sub.add_parser("storyboard"); p.add_argument("target"); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_storyboard)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
