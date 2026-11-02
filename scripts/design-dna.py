#!/usr/bin/env python3
"""Design DNA: measure references, build and verify design profiles, query the visual knowledge base.

  measure   <image|video>          deterministic palette (+ motion, cuts, loudness for video) as JSON
  extract   <image|video>          an *extracted* profile: measured facts filled, everything else 'unknown'
  verify    <image> <profile|measurement.json>   colour fidelity of a render frame against a profile
  validate  [profile.json ...]     schema + provenance rules + cross-references (default: the registry)
  kb build                         faceted index of techniques, sources and profiles -> reference/design-kb/index.json
  kb query  --facet camera=push --text "..." --support native
  kb for-beat <beatmap.json> <beat-id>   ranked profiles and techniques for one beat

Measured numbers come from pixels and the container; qualitative fields are never filled by this
tool. An analyst (agent or human) looks at the contact sheet, then upgrades 'unknown' facts to
'inferred' or 'subjective' with a confidence. Run with .venv/bin/python (needs Pillow, NumPy, jsonschema).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "pipeline"))

import colorscience as cs  # noqa: E402
import profiles as pf  # noqa: E402

CAT = ROOT / "catalogue" / "data"
KB_DIR = ROOT / "reference" / "design-kb"
DNA_DIR = ROOT / "reference" / "design-dna"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


def load_json(p: Path) -> Any:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collection(name: str) -> Dict[str, Dict[str, Any]]:
    d = CAT / name
    return {load_json(f)["id"]: load_json(f) for f in sorted(d.glob("*.json"))} if d.exists() else {}


# ----------------------------------------------------------------------------- measure
def measure_image(path: Path, k: int) -> Dict[str, Any]:
    rgb = cs.load_rgb(str(path))
    m = cs.measure_palette(rgb, k=k, jpeg=path.suffix.lower() in (".jpg", ".jpeg"))
    m["source"] = {"file": path.name, "kind": "image", "sha256": sha256_file(path)}
    m["ink_coverage"] = round(cs.ink_coverage(rgb), 4)
    return m


def measure_video(path: Path, k: int, samples: int) -> Dict[str, Any]:
    import numpy as np
    import videoscan as vs

    if not vs.have_ffmpeg():
        sys.exit("error: ffmpeg/ffprobe not found; video measurement needs them")
    info = vs.probe(str(path))
    fps = info.get("fps") or 30.0
    frames = vs.luma_stream(str(path))
    motion = vs.motion_summary(frames, fps)
    del frames
    tmp = Path(tempfile.mkdtemp(prefix="dna-"))
    try:
        dur = info["duration_sec"]
        times = [dur * (i + 0.5) / samples for i in range(samples)]
        imgs = vs.sample_frames(str(path), times, tmp, width=480)
        arrays = [cs.load_rgb(str(p)) for p in imgs]
        pooled = np.concatenate([a.reshape(-1, 3) for a in arrays])
        side = int(len(pooled) ** 0.5)
        pooled_img = pooled[: side * side].reshape(side, side, 3)
        pal = cs.measure_palette(pooled_img, k=k)
        pal["measurement"]["pooled_from_frames"] = len(arrays)
        pal["measurement"]["sample_times_sec"] = [round(t, 2) for t in times]
        per_frame = [cs.measure_palette(a, k=4)["palette"][0] for a in arrays]
        out: Dict[str, Any] = {**pal, "source": {"file": path.name, "kind": "video", "sha256": sha256_file(path)},
                               "container": info, "motion": motion,
                               "background_hex_per_sample": [p["hex"] for p in per_frame]}
        if info.get("has_audio"):
            out["audio"] = {"loudness": vs.loudness(str(path))}
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cmd_measure(a: argparse.Namespace) -> int:
    p = Path(a.input).expanduser()
    if not p.exists():
        sys.exit(f"error: {p} not found")
    m = measure_image(p, a.k) if p.suffix.lower() in IMAGE_EXT else measure_video(p, a.k, a.samples)
    text = json.dumps(m, indent=2)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        print(text)
    return 0


# ----------------------------------------------------------------------------- extract
UNKNOWN = {"value": "not yet assessed", "basis": "unknown"}


def u() -> Dict[str, Any]:
    return dict(UNKNOWN)


def find_source_id(sha: str) -> Optional[str]:
    rid = f"ref-{sha[:10]}"
    return rid if (CAT / "reference-sources" / f"{rid}.json").exists() else None


def build_extracted_profile(m: Dict[str, Any], pid: str, name: str, ev_path: str) -> Dict[str, Any]:
    src = m["source"]
    ev = f"{ev_path}#palette"
    colors = [{"hex": c["hex"], "role": c["role"], "coverage": c["coverage"], "basis": "measured", "evidence": ev} for c in m["palette"]]
    ref = find_source_id(src["sha256"])
    prof: Dict[str, Any] = {
        "id": pid, "name": name, "profile_version": 1, "kind": "extracted", "status": "proposed",
        "summary": f"Extracted from {src['file']} ({src['kind']}). Palette and timing are measured; every other field is unknown until an analyst has looked at the frames.",
        "identity": {k: u() for k in ("mood", "genre", "visual_language", "realism")},
        "design_system": {
            "palette": {"colors": colors, "measurement": m["measurement"]},
            "typography": {"display": u()},
            "composition": {"principles": u()},
        },
        "motion": {
            "grammar": u(), "easing": {"entrances": u(), "exits": u()},
            "timing": {"pace": u()}, "transitions": {"vocabulary": [u()]}, "camera": {"language": u()},
        },
        "audio_direction": {"narration": u(), "music": u(), "sfx": u()},
        "rendering": {"strategy": "Not assessed.", "preferred_asset_types": ["programmatic"], "feasibility": "research-required"},
        "provenance": {"method": f"deterministic {src['kind']} measurement via scripts/design-dna.py extract", "created_on": date.today().isoformat(),
                       "notes": "Qualitative facts are unknown on purpose. Do not fill them from the palette."},
        "weaknesses": ["Unassessed: this profile has only measured properties."],
        "tags": ["extracted", src["kind"]],
    }
    if ref:
        prof["provenance"]["reference_sources"] = [ref]
    mo = m.get("motion")
    if mo:
        mev = f"{ev_path}#motion"
        prof["motion"]["timing"]["shot_length_sec"] = {"value": mo["shot_length_median_sec"], "unit": "s", "basis": "measured", "confidence": "medium", "evidence": mev,
                                                       "note": f"{mo['cut_count']} cuts in {mo['duration_sec']} s at {mo['analysis_size']} luma; soft transitions are not counted as cuts"}
        prof["motion"]["timing"]["pace"] = {"value": f"{mo['cuts_per_min']} hard cuts/min, median luma change {mo['motion_median']}/255 per frame, {mo['static_share']*100:.1f}% of frames static", "basis": "measured", "confidence": "medium", "evidence": mev}
    lou = (m.get("audio") or {}).get("loudness")
    if lou and lou.get("integrated_lufs") is not None:
        prof["audio_direction"]["measured"] = {"integrated_lufs": lou["integrated_lufs"], "lra_lu": lou["lra_lu"], "true_peak_dbtp": lou["true_peak_dbtp"], "evidence": f"{ev_path}#audio"}
    return prof



SUPPORT_ORDER = ["native", "approximation", "research-required", "additional-dependencies", "resource-constrained"]


def bridge_source(prof: Dict[str, Any], rid: str) -> int:
    """Copy the reference analyst's notes (observed / interpreted) into profile facts with honest bases.

    observed -> basis 'inferred' (an analyst's description of what was seen), interpreted -> 'subjective'.
    Confidence comes from the source record. Returns the number of facts filled.
    """
    src = load_json(CAT / "reference-sources" / f"{rid}.json")
    an, conf = src.get("analysis", {}), src.get("confidence", "medium")
    asp = an.get("aspects", {})
    base = f"catalogue/data/reference-sources/{rid}.json#analysis"

    def fact(text: str, basis: str, key: str) -> Dict[str, Any]:
        return {"value": text, "basis": basis, "confidence": conf, "evidence": f"{base}.{key}"}

    n = 0

    def put(container: Dict[str, Any], key: str, text: Optional[str], basis: str, ev: str) -> None:
        nonlocal n
        if text:
            container[key] = fact(text, basis, ev)
            n += 1

    def obs(a: str) -> Optional[str]:
        return asp.get(a, {}).get("observed")

    ds, mo, ident = prof["design_system"], prof["motion"], prof["identity"]
    put(ds["typography"], "display", obs("typography"), "inferred", "aspects.typography")
    put(ds["composition"], "principles", obs("composition"), "inferred", "aspects.composition")
    put(ds["composition"], "layering_and_depth", obs("depth_and_layering"), "inferred", "aspects.depth_and_layering")
    put(ds, "shape_language", obs("shapes_and_materials"), "inferred", "aspects.shapes_and_materials")
    put(ds, "texture", obs("texture_and_effects"), "inferred", "aspects.texture_and_effects")
    put(mo, "grammar", obs("motion"), "inferred", "aspects.motion")
    put(mo["camera"], "language", obs("camera"), "inferred", "aspects.camera")
    put(mo["easing"], "entrances", obs("easing"), "inferred", "aspects.easing")
    put(mo, "choreography", obs("timing_and_rhythm"), "inferred", "aspects.timing_and_rhythm")
    t = obs("transitions")
    if t:
        mo["transitions"]["vocabulary"] = [fact(t, "inferred", "aspects.transitions")]
        n += 1
    put(prof["audio_direction"], "music", obs("audio_and_sync"), "inferred", "aspects.audio_and_sync")
    put(ident, "visual_language", an.get("concept", {}).get("interpreted"), "subjective", "concept.interpreted")
    put(ident, "mood", an.get("communication_style", {}).get("interpreted"), "subjective", "communication_style.interpreted")
    put(ident, "editorial_approach", obs("visual_identity"), "inferred", "aspects.visual_identity")
    techs = [t for t in src.get("techniques", []) if isinstance(t, str)]
    known = collection("references")
    techs = [t for t in techs if t in known]
    if techs:
        prof["techniques"] = techs
        worst = max((SUPPORT_ORDER.index(tech_support(known[t])) if tech_support(known[t]) in SUPPORT_ORDER else 2 for t in techs), default=2)
        prof["rendering"]["feasibility"] = SUPPORT_ORDER[worst]
        prof["rendering"]["strategy"] = "Linked techniques: " + ", ".join(techs) + ". Feasibility is the worst support class among them."
    prof["weaknesses"] = [f"Analyst-listed difficulty: {d}" for d in an.get("difficult", [])] or prof["weaknesses"]
    prof["provenance"]["notes"] = "Palette, shot rhythm and loudness are measured by this tool; qualitative facts are the reference analyst's notes (observed -> inferred, interpreted -> subjective). Unlisted fields are unknown."
    prof["summary"] = (prof["summary"] + " Qualitative facts bridged from the analyst record " + rid + ".")[:900]
    return n


def cmd_extract(a: argparse.Namespace) -> int:
    import videoscan as vs

    p = Path(a.input).expanduser()
    m = measure_image(p, a.k) if p.suffix.lower() in IMAGE_EXT else measure_video(p, a.k, a.samples)
    pid = a.id or ("x-" + p.stem.lower().replace(" ", "-").replace("(", "").replace(")", "").replace("_", "-"))[:48]
    out_dir = Path(a.out_dir) if a.out_dir else DNA_DIR / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    if a.register:
        meas_path = pf.PROFILE_DIR / "measurements" / f"{pid}.json"
        prof_path = pf.PROFILE_DIR / f"{pid}.json"
        meas_path.parent.mkdir(parents=True, exist_ok=True)
        ev = str(meas_path.relative_to(ROOT))
    else:
        meas_path, prof_path = out_dir / "measurement.json", out_dir / "profile.json"
        ev = str(meas_path.relative_to(ROOT)) if out_dir.is_relative_to(ROOT) else "measurement.json"
    meas_path.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    prof = build_extracted_profile(m, pid, a.name or pid, ev)
    bridged = bridge_source(prof, prof["provenance"]["reference_sources"][0]) if prof["provenance"].get("reference_sources") else 0
    prof_path.write_text(json.dumps(prof, indent=2) + "\n", encoding="utf-8")
    if m["source"]["kind"] == "video" and vs.have_ffmpeg():
        info = m["container"]
        tmp = Path(tempfile.mkdtemp(prefix="dna-sheet-"))
        try:
            times = [info["duration_sec"] * (i + 0.5) / 12 for i in range(12)]
            imgs = vs.sample_frames(str(p), times, tmp, width=480)
            vs.contact_sheet(imgs, [f"{t:.1f}s" for t in times], out_dir / "contact-sheet.jpg", cols=4, thumb_w=360)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    errs = pf.schema_errors(prof)
    e2, w2 = pf.check_profile(prof)
    print(f"wrote {prof_path.relative_to(ROOT) if prof_path.is_relative_to(ROOT) else prof_path} + {meas_path.name}; {bridged} analyst facts bridged; sheet in {out_dir.relative_to(ROOT) if out_dir.is_relative_to(ROOT) else out_dir}")
    if errs or e2:
        print("profile is invalid:\n  " + "\n  ".join(errs + e2))
        return 1
    print(f"  palette: {', '.join(c['hex'] for c in m['palette'][:6])}")
    if m.get("motion"):
        mo = m["motion"]
        print(f"  motion: {mo['cut_count']} cuts, median shot {mo['shot_length_median_sec']} s, static {mo['static_share']*100:.1f}%")
    print("  qualitative fields: unknown (look at the contact sheet, then upgrade them with a stated basis)")
    return 0


# ----------------------------------------------------------------------------- verify
def cmd_verify(a: argparse.Namespace) -> int:
    rgb = cs.load_rgb(a.image)
    impl = cs.measure_palette(rgb, k=a.k, jpeg=a.image.lower().endswith((".jpg", ".jpeg")))
    spec = load_json(Path(a.profile))
    if "palette" in spec and isinstance(spec["palette"], list):
        ref = spec["palette"]
    else:
        ref = [c for c in spec["design_system"]["palette"]["colors"] if c.get("basis") in ("measured", "prescribed")]
        ref = [{"hex": c["hex"], "coverage": c.get("coverage", 0.0), "role": c["role"]} for c in ref]
    if not ref:
        sys.exit("error: profile has no measured or prescribed palette to verify against")
    res = cs.verify_against(ref, impl)
    res["implementation"] = {"file": a.image, "palette": impl["palette"]}
    print(json.dumps(res, indent=2))
    print(("PASS" if res["pass"] else "FAIL") + f": mean dE76 {res['mean_delta_e76']}, max dE76 {res['max_delta_e76']}, drift {res['coverage_drift']}", file=sys.stderr)
    return 0 if res["pass"] else 2


# ----------------------------------------------------------------------------- validate
def cmd_validate(a: argparse.Namespace) -> int:
    reg = pf.load_registry()
    styles, techs, srcs = collection("styles"), collection("references"), collection("reference-sources")
    files = [Path(f) for f in a.files] if a.files else sorted(pf.PROFILE_DIR.glob("*.json"))
    total_e = total_w = 0
    for f in files:
        prof = load_json(f)
        errs = pf.schema_errors(prof)
        e2, w2 = pf.check_profile(prof, styles, techs, srcs, reg)
        errs += e2
        total_e += len(errs)
        total_w += len(w2)
        status = "ok" if not errs else "FAIL"
        print(f"{status:4} {f.name}  ({prof.get('kind')}, {len(w2)} warnings)")
        for e in errs:
            print("     error:", e)
        for w in w2:
            print("     warn: ", w)
    print(f"\n{len(files)} profiles, {total_e} errors, {total_w} warnings")
    return 1 if total_e else 0


# ----------------------------------------------------------------------------- knowledge base
FACETS: Dict[str, List[str]] = {
    "camera": ["push", "pull", "pan", "tilt", "track", "parallax", "orbit", "dolly", "zoom", "drift", "rack", "turntable"],
    "transition": ["transition", "wipe", "cut", "dissolve", "crossfade", "match", "morph", "iris", "liquid", "curtain", "bloom", "shatter"],
    "typography": ["type", "text", "word", "letter", "kinetic", "title", "caption", "glyph", "headline"],
    "effects": ["glow", "bloom", "grain", "particle", "smear", "blur", "glitch", "shatter", "distort", "trail", "boil", "pulse"],
    "material": ["paper", "collage", "halftone", "texture", "grain", "glass", "chrome", "metal", "ink", "cut-out", "silhouette", "sticker"],
    "lighting": ["light", "glow", "shadow", "bloom", "lit", "gradient", "depth", "volumetric"],
    "composition": ["grid", "layout", "centred", "centered", "symmetry", "stage", "hud", "frame", "layer", "isometric", "collage"],
    "narrative": ["progression", "reveal", "build", "step", "sequence", "repetition", "bookend", "beat", "story", "tracker", "assembly"],
}


def facets_of(text: str) -> Dict[str, List[str]]:
    t = text.lower()
    return {f: sorted({w for w in ws if w in t}) for f, ws in FACETS.items() if any(w in t for w in ws)}


def tech_support(r: Dict[str, Any]) -> str:
    cap = r.get("capability") or {}
    if cap.get("support"):
        return cap["support"]
    return "native" if r.get("implemented_by") else "research-required"


def build_kb() -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    for rid, r in collection("references").items():
        txt = " ".join([r.get("name", ""), str(r.get("technique", "")), " ".join(r.get("tags", [])), json.dumps(r.get("decomposition", {}))])
        items.append({"kind": "technique", "id": rid, "name": r.get("name"), "status": r.get("status"), "support": tech_support(r),
                      "implemented_by": r.get("implemented_by", []), "facets": facets_of(txt), "text": txt[:600],
                      "sources": sorted({e.get("source_id") for e in (r.get("provenance") or []) if isinstance(e, dict) and e.get("source_id")})})
    for sid, s in collection("reference-sources").items():
        txt = " ".join([s.get("name", ""), " ".join(s.get("categories", [])), " ".join(s.get("tags", []))])
        auto = s.get("automated", {})
        items.append({"kind": "source", "id": sid, "name": s.get("name"), "status": s.get("status"), "categories": s.get("categories", []),
                      "facets": facets_of(txt), "techniques": s.get("techniques", []), "text": txt[:400],
                      "measured": {"duration_sec": s.get("media", {}).get("duration_sec"), "cuts": sum(1 for b in auto.get("boundaries", []) if b.get("kind") == "cut")}})
    for pid, p in pf.load_registry().items():
        vals = []
        for sec in pf.FACT_SECTIONS:
            for path, fct in pf.iter_facts(p.get(sec, {}), sec):
                vals.append(fct if isinstance(fct, str) else str(fct.get("value", "")))
        txt = " ".join(vals + p.get("tags", []))
        items.append({"kind": "profile", "id": pid, "name": p["name"], "status": p["status"], "support": p["rendering"]["feasibility"],
                      "style": p.get("style"), "profile_kind": p["kind"], "archetype": p.get("archetype"), "facets": facets_of(txt), "text": p["summary"],
                      "asset_types": p["rendering"]["preferred_asset_types"], "techniques": p.get("techniques", [])})
    return {"built_on": date.today().isoformat(), "derived": "facets are keyword-derived and not analyst-verified; use as retrieval, not as truth", "count": len(items), "items": items}


def score(item: Dict[str, Any], words: List[str]) -> int:
    blob = (item["name"] or "").lower() + " " + item.get("text", "").lower() + " " + " ".join(item.get("categories", []))
    return sum(blob.count(w) for w in words)


def cmd_kb(a: argparse.Namespace) -> int:
    if a.kbcmd == "build":
        kb = build_kb()
        KB_DIR.mkdir(parents=True, exist_ok=True)
        (KB_DIR / "index.json").write_text(json.dumps(kb, indent=1) + "\n", encoding="utf-8")
        by = {}
        for it in kb["items"]:
            by[it["kind"]] = by.get(it["kind"], 0) + 1
        print(f"built {KB_DIR / 'index.json'}: {by}")
        return 0
    kb = build_kb()  # cheap; avoids stale index
    items = kb["items"]
    if a.kbcmd == "query":
        for fv in a.facet or []:
            f, _, v = fv.partition("=")
            items = [i for i in items if (not v and f in i["facets"]) or any(v.lower() in w or w in v.lower() for w in i["facets"].get(f, []))]
        if a.support:
            items = [i for i in items if i.get("support") == a.support]
        if a.kind:
            items = [i for i in items if i["kind"] == a.kind]
        words = (a.text or "").lower().split()
        if words:
            items = sorted([i for i in items if score(i, words) > 0], key=lambda i: -score(i, words))
        for i in items[: a.limit]:
            print(f"{i['kind']:9} {i['id']:34} {str(i.get('support') or ''):22} {','.join(sorted(i['facets'])[:5])}")
        print(f"\n{len(items)} matches")
        return 0
    if a.kbcmd == "for-beat":
        bm = load_json(Path(a.beatmap))
        beat = next((b for b in bm["beats"] if b["id"] == a.beat), None)
        if not beat:
            sys.exit(f"error: beat {a.beat!r} not in {a.beatmap}")
        text = " ".join([beat["visual_concept"], beat.get("purpose", ""), beat.get("emotional_tone", ""), beat.get("implementation", "")]
                        + [s.get(k, "") for s in beat.get("shots", []) for k in ("composition", "camera_movement", "typography", "object_movement")])
        words = [w for w in text.lower().replace(",", " ").replace(".", " ").split() if len(w) > 3]
        ranked = sorted(items, key=lambda i: -score(i, words))
        for kind in ("profile", "technique"):
            print(f"-- {kind}s for beat {beat['id']}")
            for i in [x for x in ranked if x["kind"] == kind and score(x, words) > 0][:5]:
                print(f"   {i['id']:34} score {score(i, words):3}  support={i.get('support')}")
        return 0
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("measure"); p.add_argument("input"); p.add_argument("--k", type=int, default=8); p.add_argument("--samples", type=int, default=24); p.add_argument("--out"); p.set_defaults(fn=cmd_measure)
    p = sub.add_parser("extract"); p.add_argument("input"); p.add_argument("--id"); p.add_argument("--name"); p.add_argument("--k", type=int, default=8); p.add_argument("--samples", type=int, default=24); p.add_argument("--out-dir"); p.add_argument("--register", action="store_true", help="write profile + measurement into catalogue/data/design-profiles/"); p.set_defaults(fn=cmd_extract)
    p = sub.add_parser("verify"); p.add_argument("image"); p.add_argument("profile"); p.add_argument("--k", type=int, default=8); p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("validate"); p.add_argument("files", nargs="*"); p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("kb"); ks = p.add_subparsers(dest="kbcmd", required=True)
    ks.add_parser("build")
    q = ks.add_parser("query"); q.add_argument("--facet", action="append"); q.add_argument("--text"); q.add_argument("--support"); q.add_argument("--kind", choices=["technique", "source", "profile"]); q.add_argument("--limit", type=int, default=20)
    q = ks.add_parser("for-beat"); q.add_argument("beatmap"); q.add_argument("beat")
    p.set_defaults(fn=cmd_kb)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
