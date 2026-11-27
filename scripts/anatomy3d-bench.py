#!/usr/bin/env python3
"""anatomy3d-bench.py: reusable anatomical test scenes for the 3D Tibi, as contact sheets you LOOK at (the numeric tests are scripts/anatomy3d-check.js).

    python scripts/anatomy3d-bench.py [--set angles|poses|modes|all] [--gender m|f|both]
    python scripts/anatomy3d-bench.py --set matrix --gender both --out qa/anatomy3d-matrix
    python scripts/anatomy3d-bench.py --set regions --gender both --shade clay --out qa/anatomy3d-regions
    python scripts/anatomy3d-bench.py --set modes --gender both --shade crescent --out qa/anatomy3d-crescent
    python scripts/anatomy3d-bench.py --set review --gender both --profile distance --out qa/anatomy3d-review
    python scripts/anatomy3d-bench.py --set matrix --gender both --profile distance --out qa/anatomy3d-candidate --baseline qa/anatomy3d-matrix/report.json
    python scripts/anatomy3d-bench.py --out qa/anatomy3d-candidate --report-only --review review.json

  angles  the resting body from front, rear, left, right, two three-quarters and a close-up of shoulders, hips and knee (continuous silhouette, integrated
          muscle definition, shorts and hem, no detached shape from any side)
  poses   activation in squat bottom, curl top, lateral raise top, hip-thrust lockout, calf-raise top and standing, three-quarter and rear
          (highlights follow the surface through joint deformation; shoulders, hips, knees and ankles)
  modes   normal, activation, calf cutaway (skin out, then superficial layer out), glute cutaway, quad cutaway, isolated calf on a ghost body, muscle layer, skeleton
  girdle  shoulder close-ups: cross-body reach, overhead 175, abduction 90 with axial rotation, raised-arm lats, and the curl, raise, press,
          squat bar hold, overhead squat and push-up shoulders (round 3 phase B girdle; clay works)
--page <html> captures from a saved bench page (e.g. one that loads the pre-change kit) so before and after use identical cells.
Each cell is a headless-Chrome still of assets/fitness/lab3d/anatomy-bench.html (SwiftShader WebGL) under the host render lock. A sheet per set, labelled.
Acceptance (anatomy skill): fail the build if a muscle shape protrudes, looks like a sticker, a highlight leaves the surface, skin and muscle intersect, a deep
structure reads as superficial, or the colour language blurs; then fix, re-run anatomy3d-check.js, and look again.
"""
import argparse
import hashlib
import html
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "pipeline"))

from browser_stills import capture, chrome  # noqa: E402

LEGACY_SETS = ("angles", "poses", "modes")
MATRIX_SETS = ("orbit", "joints", "windows", "phases")
REVIEW_SETS = ("regions", *MATRIX_SETS, "modes")


PAGE = ROOT / "assets" / "fitness" / "lab3d" / "anatomy-bench.html"


def cell(ch, query, out, w, h, page=PAGE):
    capture(ch, page, query, Path(out), w, h, budget_ms=4500)


def sets(g):
    base = f"g={g}&dist=2300&ty=370"
    angles = [("front", f"{base}&az=0&el=4"), ("rear", f"{base}&az=180&el=4"), ("left", f"{base}&az=90&el=4"), ("right", f"{base}&az=270&el=4"),
              ("3/4 front", f"{base}&az=35&el=8"), ("3/4 rear", f"{base}&az=145&el=8"),
              ("close: shoulders", f"g={g}&az=25&el=6&dist=950&ty=520"), ("close: hips", f"g={g}&az=150&el=6&dist=1000&ty=330"), ("close: knee", f"g={g}&az=60&el=4&dist=900&ty=190")]
    acts = "acts=glute:3:1,quad:3:0.9,hams:2:0.7,calf:2:0.6,soleus:2:0.6,adductor:1:0.6"
    poses = [("squat bottom, side", f"g={g}&ex=squat&t=1.75&az=90&el=6&dist=2500&ty=400&{acts}"), ("squat bottom, rear", f"g={g}&ex=squat&t=1.75&az=160&el=8&dist=2500&ty=400&{acts}"),
             ("curl top", f"g={g}&ex=curl&t=1.45&az=35&el=8&dist=2300&ty=470&acts=biceps:3:1,brach:2:0.8,flexor:1:0.5"),
             ("lateral raise top", f"g={g}&ex=raise&t=1.6&az=20&el=8&dist=2500&ty=470&acts=delt-side:3:1,trap:2:0.7"),
             ("hip thrust lockout", f"g={g}&ex=hipthrust&t=1.5&az=60&el=14&dist=2300&tx=80&ty=230&acts=glute:3:1,hams:2:0.7"),
             ("calf raise top, rear", f"g={g}&ex=calfraise&t=1.4&az=170&el=8&dist=1500&ty=200&acts=calf:3:1,soleus:3:0.85"),
             ("press bottom", f"g={g}&ex=press&t=1.5&az=30&el=20&dist=2300&tx=-120&ty=230&acts=pec:3:1,triceps:2:0.8,delt-front:2:0.6")]
    modes = [("normal", f"{base}&az=30&el=8"), ("activation", f"{base}&az=150&el=8&{acts}"),
             ("calf cutaway 1", f"g={g}&az=165&el=8&dist=1200&ty=130&cut=calf:1&hi=calf:1"), ("calf cutaway 2", f"g={g}&az=165&el=8&dist=1200&ty=130&cut=calf:2&hi=soleus:1"),
             ("glute cutaway", f"g={g}&az=150&el=12&dist=1500&ty=300&cut=glute:1.6&hi=glute:1"), ("quad cutaway", f"g={g}&az=30&el=8&dist=1500&ty=230&cut=quad:1.6&hi=quad:1"),
             ("isolated calf, ghost", f"{base}&az=30&el=8&view=ghost:1&iso=calf:1,soleus:1&hi=calf:1,soleus:1"), ("muscle layer", f"{base}&az=20&el=6&view=ghost:1,layer:1"),
             ("skeleton", f"{base}&az=30&el=8&view=ghost:1,skel:1")]
    return {"angles": angles, "poses": poses, "modes": modes}


def matrix_sets(g):
    base = f"g={g}&id=audit-{g}"
    orbit = [(f"az {az} / el {el}", f"{base}&az={az}&el={el}&dist=2700&ty=380")
             for el in (-10, 10, 35, 65) for az in range(0, 360, 45)]
    upper = "az=25&el=10&dist=1250&ty=565"
    lower = "az=70&el=10&dist=1450&ty=330"
    poses = [
        ("A-pose", "p.shL=26&p.shR=26&p.plL=0&p.plR=0&p.elL=0&p.elR=0&p.ikLegL=0&p.ikLegR=0&p.haL=4&p.haR=4", upper),
        ("rest", "", upper),
        ("axial -90", "p.shL=90&p.plL=0&p.rtL=-90", upper),
        ("axial 0", "p.shL=90&p.plL=0&p.rtL=0", upper),
        ("axial +90", "p.shL=90&p.plL=0&p.rtL=90", upper),
        ("overhead 175", "p.shL=175&p.shR=175&p.plL=90&p.plR=90", "az=35&el=10&dist=2800&ty=450"),
        ("across body", "p.shL=90&p.plL=135&p.elL=95", upper),
        ("elbow 150", "p.shL=30&p.plL=30&p.elL=150", upper),
        ("knee 150", "p.ikLegL=0&p.hpL=100&p.knL=150", lower),
        ("hip 120", "p.ikLegL=0&p.hpL=120&p.knL=90", lower),
        ("trunk twist 45", "p.twist=45", "az=25&el=10&dist=1800&ty=480"),
        ("overhead squat", "ex=squat&t=1.75&p.ikL=0&p.ikR=0&p.shL=175&p.shR=175&p.plL=90&p.plR=90",
         "az=70&el=10&dist=2700&ty=420"),
    ]
    activation = "acts=delt-side:3:0.8,delt-front:2:0.6,biceps:3:0.8,triceps:2:0.6,quad:3:0.8,hams:2:0.6,abs:1:0.5"
    joints = [(f"{label} / {mode}", f"{base}&{pose}&{cam}&mode={mode}&{activation if mode == 'active' else ''}")
              for label, pose, cam in poses for mode in ("normal", "active")]
    windows = []
    for window, az, muscle in (("arm", 30, "biceps"), ("tri", 150, "triceps"), ("chest", 20, "pec")):
        for side in ("L", "R"):
            camera = az if side == "L" else (360 - az) % 360
            for level in (0.5, 1, 1.5, 2):
                windows.append((f"{window} {side} / open {level}",
                                f"{base}&az={camera}&el=10&dist=1350&ty=545&p.shL=35&p.shR=35&p.plL=0&p.plR=0"
                                f"&cut={window}@{side}:{level}&hi={muscle}@{side}:0.8"))
    phases = [(f"{exercise} / phase {phase + 1}",
               f"{base}&ex={exercise}&phase={phase}")
              for exercise in ("curl", "press", "raise", "squat", "squat-blocked",
                               "hipthrust", "calfraise", "seatedcalf")
              for phase in range(5)]
    return {"orbit": orbit, "joints": joints, "windows": windows, "phases": phases}


def region_set(g):
    base = f"g={g}&id=audit-{g}&mode=normal"
    shots = [
        ("head / front", "az=0&el=8&dist=700&ty=680"),
        ("head-neck / side", "az=90&el=8&dist=700&ty=660"),
        ("neck-trapezius / rear", "az=180&el=12&dist=800&ty=620"),
        ("shoulders / front", "az=0&el=10&dist=1000&ty=575"),
        ("shoulder / rotated", "az=35&el=10&dist=700&tx=80&ty=585&p.shL=90&p.plL=0&p.rtL=90"),
        ("shoulder / overhead rear", "az=145&el=10&dist=1100&ty=625&p.shL=175&p.plL=90"),
        ("chest / front", "az=0&el=10&dist=850&ty=540"),
        ("chest / three-quarter", "az=50&el=10&dist=850&ty=540"),
        ("back-lats / rear", "az=180&el=10&dist=1150&ty=505"),
        ("back-lats / three-quarter", "az=140&el=10&dist=1150&ty=505"),
        ("back-lats / side", "az=90&el=10&dist=1150&ty=505"),
        ("back-lats / raised arms", "az=160&el=10&dist=1300&ty=540&p.shL=90&p.shR=90&p.plL=0&p.plR=0"),
        ("abdomen / front", "az=0&el=8&dist=800&ty=470"),
        ("waist / side", "az=90&el=8&dist=800&ty=470"),
        ("upper arm / curl", "az=35&el=8&dist=850&tx=80&ty=525&p.shL=20&p.plL=60&p.elL=140"),
        ("elbow / deep flexion", "az=90&el=8&dist=750&tx=85&ty=500&p.shL=20&p.plL=60&p.elL=150"),
        ("forearm-wrist / front", "az=15&el=8&dist=750&tx=100&ty=415"),
        ("hand / side", "az=75&el=8&dist=500&tx=100&ty=350"),
        ("pelvis-glutes / rear", "az=160&el=8&dist=1050&ty=340"),
        ("hip / side", "az=90&el=8&dist=1050&ty=340"),
        ("thigh / front", "az=20&el=8&dist=1100&ty=260"),
        ("hamstrings / rear", "az=160&el=8&dist=1100&ty=260"),
        ("knee / side", "az=90&el=8&dist=850&ty=195"),
        ("knee / deep flexion", "az=70&el=10&dist=1400&ty=340&p.ikLegL=0&p.hpL=100&p.knL=150"),
        ("calves / rear", "az=180&el=8&dist=900&ty=115"),
        ("ankles / side", "az=90&el=8&dist=700&ty=80"),
        ("shoes / front three-quarter", "az=35&el=15&dist=700&ty=65"),
        ("heel / raised", "ex=calfraise&t=1.4&az=90&el=8&dist=850&ty=110"),
        ("body / prone geometry probe", "az=90&el=20&dist=2500&ty=75&tz=-40&p.pitch=90&p.y=70&p.ikLegL=0&p.ikLegR=0"),
    ]
    return [(label, f"{base}&{query}") for label, query in shots]


def write_report(out, report, review_path=None, baseline_path=None):
    reviews = json.loads(review_path.read_text(encoding="utf-8")) if review_path else {}
    ids = {row["id"] for row in report["cases"]}
    if reviews.keys() - ids:
        raise ValueError(f"Review names unknown cases: {sorted(reviews.keys() - ids)}")
    for case_id, review in reviews.items():
        if set(review) != {"status", "note"}:
            raise ValueError(f"Review may only set status and note: {case_id}")
        if review["status"] not in ("pass", "known-limit", "fail") or not isinstance(review["note"], str) or not review["note"].strip():
            raise ValueError(f"Review needs a status and evidence note: {case_id}")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path else None
    previous = {row["id"]: row for row in baseline["cases"]} if baseline else {}
    if baseline and (baseline["size"] != report["size"] or ids - previous.keys()):
        raise ValueError("Baseline must contain the same-size capture for every current case")
    cards = []
    for row in report["cases"]:
        image = out / row["image"]
        if not image.is_file() or hashlib.sha256(image.read_bytes()).hexdigest() != row["image_sha256"]:
            raise RuntimeError(f"Missing or changed capture: {image}")
        if row["id"] in reviews:
            row.update(reviews[row["id"]])
        before = ""
        if row["id"] in previous:
            old = previous[row["id"]]
            old_query = dict(parse_qsl(old["query"]))
            query = dict(parse_qsl(row["query"]))
            old_query.pop("profile", None)
            query.pop("profile", None)
            old_query.setdefault("shade", "normal")
            query.setdefault("shade", "normal")
            if old_query != query:
                raise ValueError(f"Baseline pose/camera differs: {row['id']}")
            old_image = baseline_path.parent / old["image"]
            if hashlib.sha256(old_image.read_bytes()).hexdigest() != old["image_sha256"]:
                raise RuntimeError(f"Changed baseline capture: {old_image}")
            row["baseline_status"] = old["status"]
            before_path = os.path.relpath(baseline_path.parent / old["image"], out)
            before_url = html.escape(Path(before_path).as_posix())
            before = (f'<figure><a href="{before_url}"><img loading="lazy" src="{before_url}" alt="Reference: {html.escape(row["label"])}"></a>'
                      f'<figcaption>{html.escape(baseline["profile"])} reference: {html.escape(old["status"].upper())}</figcaption></figure>')
        cards.append(
            f'<article id="{html.escape(row["id"])}"><h2>{html.escape(row["body"] + " / " + row["label"])}</h2>'
            f'<strong class="{row["status"]}">{row["status"].upper()}</strong>'
            f'<p>{html.escape(row["note"])}</p><div class="pair">{before}'
            f'<figure><a href="{html.escape(row["image"])}"><img loading="lazy" src="{html.escape(row["image"])}" alt="Current: {html.escape(row["label"])}"></a>'
            f'<figcaption>{html.escape(report["profile"])} / {html.escape(row["id"])}</figcaption></figure></div></article>'
        )
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    document = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Tibi 3D acceptance</title>
<style>body{margin:0;padding:32px;background:#F6F3EC;color:#1B1D29;font:16px system-ui}
header{max-width:950px;margin-bottom:32px}h1{font-size:38px}h2{font-size:18px}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:20px}
article{background:#fffaf2;border:1px solid #ddd6c9;border-radius:12px;padding:18px}
article p{min-height:44px}.pair{display:flex;gap:8px}figure{margin:0;flex:1;min-width:0}
img{width:100%;height:auto}figcaption{font-size:12px;margin:6px 0}.pass{color:#087a55}
.fail{color:#b23328}.known-limit{color:#8f5708}code{font-size:13px}</style>
<header><h1>Tibi / 3D acceptance</h1>
<p>Engineering and visual review, not human G3 anatomy approval. The integrated distance profile is the current 3D development body; legacy is retained only as a compatibility reference.</p>
<p>PASS applies only to the targeted visible condition named in the note. KNOWN-LIMIT means the stated issue remains or the view cannot settle it. Click either thumbnail for its full capture.</p>
"""
    def tally(rows):
        return ", ".join(f"{sum(r['status'] == s for r in rows)} {s}" for s in ("pass", "known-limit", "fail"))
    document += (f'<p>{html.escape(report["at"])} | {len(report["cases"])} captures | '
                 f'{html.escape(report["profile"])} profile | {report["size"]}</p>'
                 f'<p><strong>Current:</strong> {tally(report["cases"])}.'
                 + (f' <strong>{html.escape(baseline["profile"])} reference:</strong> {tally(baseline["cases"])}.' if baseline else '')
                 + '</p>'
                 f'<p>Sets: {html.escape(", ".join(report["sets"]))}. '
                 'Hip/twist values are diagnostic inputs, not clinical limits. Close-ups intentionally crop other body parts.</p>'
                 '<p>Not covered by this matrix: all camera/pose combinations, every lower-body cutaway, '
                 'every film overlay/layout, continuous collision detection, Mac or clinical accuracy. '
                 'Separate seek tests cover history and single/split contexts.</p></header><main>'
                 + "".join(cards) + "</main></html>")
    (out / "report.html").write_text(document, encoding="utf-8")


def girdle_set(g):
    """Shoulder girdle close-ups (round 3 phase B): the extreme arm poses and the exercises whose shoulders the girdle moves."""
    base = f"g={g}&id=audit-{g}&mode=normal"
    across = "p.shL=90&p.plL=135&p.elL=95"
    overhead = "p.shL=175&p.shR=175&p.plL=90&p.plR=90"
    abd = "p.shL=90&p.plL=0"
    shots = [
        ("across body / 3-4", f"{across}&az=60&el=15&dist=700&tx=88&ty=598"),
        ("across body / front", f"{across}&az=0&el=10&dist=800&tx=50&ty=590"),
        ("across body / above", f"{across}&az=20&el=55&dist=850&tx=50&ty=600"),
        ("overhead 175 / 3-4", f"{overhead}&az=30&el=5&dist=800&tx=88&ty=620"),
        ("overhead 175 / front", f"{overhead}&az=0&el=5&dist=1100&ty=660"),
        ("overhead 175 / side", f"{overhead}&az=90&el=5&dist=1100&ty=660"),
        ("overhead 175 / rear", f"{overhead}&az=150&el=10&dist=1100&ty=640"),
        ("abduction 90 / front", f"{abd}&az=0&el=10&dist=900&tx=80&ty=585"),
        ("abd 90 axial +90", f"{abd}&p.rtL=90&az=35&el=10&dist=700&tx=80&ty=585"),
        ("abd 90 axial -90", f"{abd}&p.rtL=-90&az=35&el=10&dist=700&tx=80&ty=585"),
        ("raised arms / rear lats", "p.shL=90&p.shR=90&p.plL=0&p.plR=0&az=160&el=10&dist=1300&ty=540"),
        ("neutral / shoulders front", "az=0&el=10&dist=1000&ty=575"),
        ("neutral / back", "az=180&el=10&dist=1150&ty=505"),
        ("curl top", "ex=curl&t=1.45&az=35&el=8&dist=1300&ty=520"),
        ("lateral raise top", "ex=raise&t=1.6&az=20&el=8&dist=1100&ty=520"),
        ("bench press bottom", "ex=press&t=1.5&az=30&el=20&dist=1400&tx=-120&ty=240"),
        ("squat bar hold", "ex=squat&t=1.75&az=35&el=10&dist=1500&ty=420"),
        ("squat bar hold / rear", "ex=squat&t=1.75&az=160&el=10&dist=1500&ty=420"),
        ("overhead squat", f"ex=squat&t=1.75&p.ikL=0&p.ikR=0&{overhead}&az=70&el=10&dist=2700&ty=420"),
        ("push-up bottom", "ex=push-up&phase=2&az=60&el=15&dist=1800&ty=200"),
    ]
    return [(label, f"{base}&{query}") for label, query in shots]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", default="all", choices=[*LEGACY_SETS, *MATRIX_SETS, "regions", "girdle", "all", "matrix", "review"])
    ap.add_argument("--gender", default="m", choices=["m", "f", "both"])
    ap.add_argument("--profile", default="distance", choices=["legacy", "distance"])
    ap.add_argument("--shade", default="normal", choices=["normal", "clay", "crescent"],
                    help="Neutral clay isolates surface geometry; not for cutaways or activation review. "
                         "crescent is the opt-in flat-plane look (T3.anatomy.shade); works with every set.")
    ap.add_argument("--out", default="qa/anatomy3d")
    ap.add_argument("--size", default="300x440")
    ap.add_argument("--review", type=Path, help="Per-case {status, note}; unreviewed cases are known-limit.")
    ap.add_argument("--baseline", type=Path, help="Reference report.json for side-by-side pictures.")
    ap.add_argument("--report-only", action="store_true", help="Apply a review to existing verified captures.")
    ap.add_argument("--page", type=Path, default=PAGE,
                    help="Alternative bench page, e.g. a saved copy that loads the pre-change kit, for identical "
                         "before/after captures (the report records its hash as an input).")
    a = ap.parse_args()
    out = ROOT / a.out
    page = a.page if a.page.is_absolute() else ROOT / a.page
    if not page.is_file():
        ap.error(f"--page not found: {page}")
    if a.report_only:
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        write_report(out, report, a.review, a.baseline)
        return 0
    from hostlock import heavy_lock
    from PIL import Image, ImageDraw
    w, h = (int(x) for x in a.size.split("x"))
    if w < 1 or h < 1:
        ap.error("--size must have positive dimensions")
    (out / "cells").mkdir(parents=True, exist_ok=True)
    ch = chrome()
    names = LEGACY_SETS if a.set == "all" else MATRIX_SETS if a.set == "matrix" else REVIEW_SETS if a.set == "review" else [a.set]
    if a.shade == "clay" and any(name in ("windows", "modes") for name in names):
        ap.error("Clay is a surface diagnostic, not a cutaway/mode rendering")
    inputs = ["src/studio/kits/fitness/" + name + ".js"
              for name in ("tibi3d", "anatomy3d", "exercises3d")]
    inputs += ["assets/fitness/lab3d/anatomy-bench.html", "scripts/anatomy3d-bench.py"]
    report = {"at": datetime.now(timezone.utc).isoformat(), "profile": a.profile, "shade": a.shade,
              "size": [w, h], "sets": list(names), "cases": [],
              "input_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in inputs}}
    if page != PAGE:
        report["page"] = page.as_posix()
        report["input_sha256"]["page"] = hashlib.sha256(page.read_bytes()).hexdigest()
    with heavy_lock("render", slug="anatomy3d-bench"):
        for gender in ("m", "f") if a.gender == "both" else (a.gender,):
            todo = {**sets(gender), **matrix_sets(gender), "regions": region_set(gender), "girdle": girdle_set(gender)}
            for name in names:
                cells = todo[name]
                cols = 8 if name == "orbit" else 4 if name in ("joints", "windows", "regions", "girdle") else 5
                cols = min(cols, len(cells))
                rows = (len(cells) + cols - 1) // cols
                sheet = Image.new("RGB", (w * cols, (h + 28) * rows), (246, 243, 236))
                dr = ImageDraw.Draw(sheet)
                for i, (label, query) in enumerate(cells):
                    case_id = f"{name}-{gender}-{i:02d}"
                    image_path = out / "cells" / f"{case_id}.png"
                    query += f"&profile={a.profile}&shade={a.shade}"
                    cell(ch, query, str(image_path), w, h, page)
                    with Image.open(image_path) as image:
                        sheet.paste(image.convert("RGB"), ((i % cols) * w, (i // cols) * (h + 28) + 28))
                    dr.text(((i % cols) * w + 8, (i // cols) * (h + 28) + 6), label, fill=(27, 29, 41))
                    report["cases"].append({
                        "id": case_id, "body": gender, "set": name, "label": label,
                        "query": query, "image": f"cells/{case_id}.png",
                        "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                        "status": "known-limit", "note": "Capture complete; visual review not yet recorded.",
                    })
                path = out / f"{name}-{gender}.png"
                sheet.save(path)
                print(path, flush=True)
    write_report(out, report, a.review, a.baseline)
    return 0


if __name__ == "__main__":
    sys.exit(main())
