#!/usr/bin/env python3
"""Style bake-off: one representative beat, several structurally different treatments, measured distinctness.

  run <slug>     --beat beat.json --profiles a,b,c [--at 2.6] [--motion] [--reason "..."]
  decide <slug>  --chosen <profile-id> --rationale "..." --by user|creative-director-agent|user-approved-agent-proposal
                 [--scores scores.json] [--overrides "..."]
  list-archetypes

What it does (and does not):
  * Each candidate is a different composition archetype (src/pipeline/archetypes.py), built from the
    SAME beat content and the profile's style tokens, written as a HyperFrames composition.
  * Stills (and optionally short motion samples) are rendered with HyperFrames; one browser or render
    at a time, under scripts/session-guard.py's render lock.
  * Distinctness is MEASURED, with a control: the first archetype is re-rendered in a different style
    system. A re-skin changes colour and type but not structure, so its layout distance is the baseline
    that real alternatives must clear. If any pair does not, `distinct` is false and the bake-off compared
    re-skins and must be redone.
  * The decision is never automatic. `decide` records the director's choice and rationale, writes a
    project design profile (kind=project, extends the chosen registry profile) and links the evidence.

Run with .venv/bin/python (needs Pillow, NumPy, jsonschema; hyperframes on PATH).
"""
from __future__ import annotations

import argparse
import itertools
import json
import shutil
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "pipeline"))

import archetypes as arch  # noqa: E402
import colorscience as cs  # noqa: E402
import profiles as pf  # noqa: E402

RUNTIME = ROOT / "src" / "studio"
PROJECTS = ROOT / "projects"
SPEC = ROOT / "specs" / "bakeoff-spec.json"
COST = {"native": "low", "approximation": "medium", "additional-dependencies": "high", "resource-constrained": "high", "research-required": "high"}
CRITERIA = ["composition", "legibility", "visual-identity", "storytelling", "implementation-cost", "consistency-with-direction"]


def load_json(p: Path) -> Any:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p: Path, d: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def project_dir(s: str) -> Path:
    p = Path(s)
    if p.is_dir():
        return p
    if (PROJECTS / s).is_dir():
        return PROJECTS / s
    hits = [d for d in PROJECTS.glob(f"*/{s}") if d.is_dir()]
    if len(hits) == 1:
        return hits[0]
    sys.exit(f"error: project {s!r} not found")


def guarded(cmd: List[str], timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a heavy command under the render lock (one browser/render at a time), stdin closed."""
    full = [sys.executable, str(ROOT / "scripts" / "session-guard.py"), "run", "render", "--"] + cmd
    return subprocess.run(full, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)


def write_candidate(cdir: Path, archetype: str, beat: Dict[str, Any], style: str, duration: float) -> Path:
    (cdir / "_studio" / "styles").mkdir(parents=True, exist_ok=True)
    for f in ("studio-core.js", "studio-base.css"):
        shutil.copy2(RUNTIME / f, cdir / "_studio" / f)
    shutil.copy2(RUNTIME / "styles" / f"{style}.css", cdir / "_studio" / "styles" / f"{style}.css")
    (cdir / "index.html").write_text(arch.page(archetype, beat, style, duration), encoding="utf-8")
    return cdir / "index.html"


def snapshot(cdir: Path, t: float) -> Optional[Path]:
    out = cdir / "still"
    shutil.rmtree(out, ignore_errors=True)
    r = guarded(["hyperframes", "snapshot", str(cdir), "--at", str(t), "--no-end", "--output", str(out), "--timeout", "60000"])
    pngs = sorted(out.glob("*.png")) if out.exists() else []
    if r.returncode != 0 or not pngs:
        print(f"  snapshot failed for {cdir.name}: {(r.stderr or r.stdout)[-300:]}", file=sys.stderr)
        return None
    final = cdir / "still.png"
    shutil.copy2(pngs[0], final)
    return final


def dominant(rgb) -> List[str]:
    return [p["hex"] for p in cs.measure_palette(rgb, k=5)["palette"][:4]]


def palette_distance(a: List[str], b: List[str]) -> float:
    import numpy as np
    la = np.array([cs.srgb_to_lab(np.array(cs.hex_to_rgb(h))) for h in a])
    lb = np.array([cs.srgb_to_lab(np.array(cs.hex_to_rgb(h))) for h in b])
    d = cs.delta_e2000(la[:, None, :], lb[None, :, :])
    return float((d.min(axis=1).mean() + d.min(axis=0).mean()) / 2)


def measure_still(path: Path) -> Dict[str, Any]:
    rgb = cs.load_rgb(str(path))
    lm = cs.layout_map(rgb)
    h, w = rgb.shape[:2]
    import numpy as np
    flat = rgb.reshape(-1, 3)
    q = (flat // 8).astype(np.int64)
    key = q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2]
    vals, counts = np.unique(key, return_counts=True)
    mode = vals[counts.argmax()]
    mrgb = np.array([(mode // 1024) * 8 + 4, ((mode // 32) % 32) * 8 + 4, (mode % 32) * 8 + 4])
    diff = (cs.delta_e76(cs.srgb_to_lab(rgb.reshape(-1, 3)), cs.srgb_to_lab(mrgb)) > 6).reshape(h, w)
    ys, xs = np.where(diff)
    hero = float((xs.max() - xs.min()) * (ys.max() - ys.min()) / (w * h) * 100) if len(xs) else 0.0
    return {"layout_map": cs.ink_map(rgb), "lum_map": lm, "ink_coverage": round(float(diff.mean()), 4), "hero_area_pct": round(hero, 1),
            "dominant_colors": dominant(rgb), "layout_signature": "".join("%x" % min(15, int(v * 16)) for v in lm.flatten())[:144]}


def build_beat(args: argparse.Namespace, pdir: Path) -> Dict[str, Any]:
    b = load_json(Path(args.beat))
    for k in ("id", "headline", "message"):
        if k not in b:
            sys.exit(f"error: beat file needs {k!r}")
    return b


def cmd_run(a: argparse.Namespace) -> int:
    pdir = project_dir(a.slug)
    beat = build_beat(a, pdir)
    reg = pf.load_registry()
    ids = [x.strip() for x in a.profiles.split(",") if x.strip()]
    for pid in ids:
        if pid not in reg:
            sys.exit(f"error: unknown profile {pid!r}; registry: {', '.join(k for k, v in reg.items() if v['kind'] == 'registry')}")
        if not reg[pid].get("archetype") or reg[pid]["archetype"] not in arch.ARCHETYPES:
            sys.exit(f"error: profile {pid!r} has no usable archetype")
    if len(ids) < 2:
        sys.exit("error: a bake-off compares at least two candidates")
    bdir = pdir / "bakeoff"
    bdir.mkdir(exist_ok=True)
    write_json(bdir / "beat.json", beat)
    t0 = time.time()
    cands: List[Dict[str, Any]] = []
    maps: Dict[str, Any] = {}
    for pid in ids:
        p = reg[pid]
        cdir = bdir / pid
        write_candidate(cdir, p["archetype"], beat, p["style"], a.duration)
        print(f"[{pid}] archetype={p['archetype']} style={p['style']}")
        still = snapshot(cdir, a.at)
        if not still:
            continue
        m = measure_still(still)
        maps[pid] = m
        cands.append({"id": pid, "profile": pid, "archetype": p["archetype"], "composition": str((cdir / "index.html").relative_to(pdir)),
                      "still": str(still.relative_to(pdir)),
                      "metrics": {"ink_coverage": m["ink_coverage"], "hero_area_pct": m["hero_area_pct"], "dominant_colors": m["dominant_colors"], "layout_signature": m["layout_signature"]},
                      "implementation_cost": COST.get(p["rendering"]["feasibility"], "high"),
                      "cost_basis": f"feasibility={p['rendering']['feasibility']}; preferred assets: {', '.join(p['rendering']['preferred_asset_types'])}. {p['rendering'].get('resource_notes', '')}".strip(),
                      "risks": p["weaknesses"][:3]})
    if len(cands) < 2:
        sys.exit("error: fewer than two candidates rendered")

    # Control: the first archetype again in a different style system (a re-skin).
    first = reg[ids[0]]
    other = next((reg[i]["style"] for i in ids[1:] if reg[i]["style"] != first["style"]), None)
    control: Dict[str, Any] = {}
    if other:
        cdir = bdir / "_control-reskin"
        write_candidate(cdir, first["archetype"], beat, other, a.duration)
        st = snapshot(cdir, a.at)
        if st:
            cm = measure_still(st)
            control = {"archetype": first["archetype"], "styles": [first["style"], other],
                       "layout_distance": round(cs.structure_distance(maps[ids[0]]["layout_map"], cm["layout_map"]), 4)}
    layout, pal = {}, {}
    got = [c["id"] for c in cands]
    for x, y in itertools.combinations(got, 2):
        layout[f"{x}|{y}"] = round(cs.structure_distance(maps[x]["layout_map"], maps[y]["layout_map"]), 4)
        pal[f"{x}|{y}"] = round(palette_distance(maps[x]["dominant_colors"], maps[y]["dominant_colors"]), 1)
    threshold = round(max(control.get("layout_distance", 0.0) * 1.5, 0.03), 4)
    minld = min(layout.values())
    dist = {"layout_distance": layout, "palette_distance": pal, "min_layout_distance": minld, "threshold": threshold, "distinct": bool(minld >= threshold)}
    if control:
        dist["control_reskin"] = control

    # Comparison sheet built from the same stills that were measured (hyperframes compare does not apply
    # the snapshot path's font injection, so its sheet can show fallback fonts and mislead the choice).
    sheet = bdir / "sheet.png"
    try:
        from PIL import Image, ImageDraw
        ims = [Image.open(pdir / c["still"]).convert("RGB") for c in cands]
        cols = 3 if len(ims) > 4 else 2
        tw = 720
        th = int(tw * ims[0].height / ims[0].width)
        rows = (len(ims) + cols - 1) // cols
        sh = Image.new("RGB", (cols * tw, rows * (th + 28)), (24, 24, 24))
        d = ImageDraw.Draw(sh)
        for i, (im, c) in enumerate(zip(ims, cands)):
            x, y = (i % cols) * tw, (i // cols) * (th + 28)
            d.text((x + 8, y + 8), f"{i + 1}. {c['id']}  [{c['archetype']}]", fill=(235, 235, 235))
            sh.paste(im.resize((tw, th), Image.LANCZOS), (x, y + 28))
        sh.save(sheet)
    except Exception as exc:  # sheet is a convenience; the record and stills stand without it
        print("warning: sheet not written:", exc, file=sys.stderr)

    if a.motion:
        for c in cands:
            cdir = bdir / c["id"]
            out = cdir / "sample.mp4"
            r = guarded(["hyperframes", "render", str(cdir), "--fps", "30", "--quality", "draft", "--low-memory-mode", "--output", str(out)], timeout=900)
            if out.exists():
                c["motion_sample"] = str(out.relative_to(pdir))
            else:
                print(f"warning: motion sample failed for {c['id']}: {(r.stderr or r.stdout)[-200:]}", file=sys.stderr)

    rec = {"spec_version": 1, "slug": pdir.name, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "beat": {k: beat[k] for k in ("id", "headline", "message", "key_figure", "supporting", "series", "mood") if k in beat},
           "shortlist_reason": a.reason or "", "candidates": cands, "distinctness": dist, "criteria": CRITERIA}
    if sheet.exists():
        rec["sheet"] = str(sheet.relative_to(pdir))
    write_json(bdir / "bakeoff.json", rec)
    import jsonschema
    errs = [e.message for e in jsonschema.Draft7Validator(load_json(SPEC)).iter_errors(rec)]
    print(f"\n{len(cands)} candidates in {time.time() - t0:.0f}s; sheet: {rec.get('sheet', 'missing')}")
    print(f"layout distance min {minld} vs re-skin control {control.get('layout_distance', 'n/a')} (threshold {threshold}): {'DISTINCT' if dist['distinct'] else 'NOT DISTINCT: these are re-skins, redo'}")
    for k, v in sorted(layout.items(), key=lambda kv: kv[1])[:3]:
        print(f"  closest pair {k}: {v}")
    if errs:
        print("record does not match spec:", errs[:3])
        return 1
    print("next: look at the sheet, score candidates, then `bakeoff.py decide`")
    return 0 if dist["distinct"] else 3


def cmd_decide(a: argparse.Namespace) -> int:
    pdir = project_dir(a.slug)
    path = pdir / "bakeoff" / "bakeoff.json"
    rec = load_json(path)
    if a.chosen not in [c["id"] for c in rec["candidates"]]:
        sys.exit(f"error: {a.chosen!r} is not a candidate: {[c['id'] for c in rec['candidates']]}")
    if len(a.rationale) < 20:
        sys.exit("error: rationale must say why (at least 20 characters)")
    if a.scores:
        rec["scores"] = load_json(Path(a.scores))
    reg = pf.load_registry()
    base = reg[a.chosen]
    reg_ev = f"catalogue/data/design-profiles/{a.chosen}.json"
    lift = lambda n: pf.lift_strings(n, reg_ev)  # noqa: E731
    prof = {"id": f"{pdir.name}-direction".replace("_", "-").lower(), "name": f"{pdir.name} production direction", "profile_version": 1, "kind": "project", "status": "experimental",
            "summary": f"Production profile for {pdir.name}: {base['name']} chosen in a bake-off. {a.rationale}"[:600],
            "extends": a.chosen, "style": base["style"], "archetype": base.get("archetype"),
            "identity": {"mood": {"value": a.rationale[:200], "basis": "subjective", "confidence": "medium", "evidence": f"{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}#decision"},
                         "genre": lift(base["identity"]["genre"]), "visual_language": lift(base["identity"]["visual_language"]), "realism": lift(base["identity"]["realism"])},
            "design_system": lift(base["design_system"]), "motion": lift(base["motion"]), "audio_direction": lift(base["audio_direction"]), "rendering": base["rendering"],
            "techniques": base.get("techniques", []),
            "provenance": {"method": "Selected in a style bake-off; inherits the registry profile and records the choice.", "bakeoff": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path), "created_on": date.today().isoformat()},
            "scene_variants": [], "weaknesses": base["weaknesses"], "tags": base.get("tags", []) + ["project"]}
    prof_path = pdir / "design-profile.json"
    errs = pf.schema_errors(prof)
    e2, _ = pf.check_profile(prof)
    if errs or e2:
        sys.exit("error: derived profile invalid: " + "; ".join((errs + e2)[:3]))
    write_json(prof_path, prof)
    rec["decision"] = {"chosen": a.chosen, "rationale": a.rationale, "decided_by": a.by, "production_profile": str(prof_path.relative_to(ROOT)) if prof_path.is_relative_to(ROOT) else str(prof_path),
                       "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if a.overrides:
        rec["decision"]["overrides"] = a.overrides
    write_json(path, rec)
    print(f"decision recorded; production profile written to {rec['decision']['production_profile']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run"); p.add_argument("slug"); p.add_argument("--beat", required=True); p.add_argument("--profiles", required=True)
    p.add_argument("--at", type=float, default=2.6); p.add_argument("--duration", type=float, default=4.0); p.add_argument("--motion", action="store_true"); p.add_argument("--reason"); p.set_defaults(fn=cmd_run)
    p = sub.add_parser("decide"); p.add_argument("slug"); p.add_argument("--chosen", required=True); p.add_argument("--rationale", required=True)
    p.add_argument("--by", required=True, choices=["user", "creative-director-agent", "user-approved-agent-proposal"]); p.add_argument("--scores"); p.add_argument("--overrides"); p.set_defaults(fn=cmd_decide)
    p = sub.add_parser("list-archetypes"); p.set_defaults(fn=lambda a: print("\n".join(arch.ARCHETYPES)) or 0)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
