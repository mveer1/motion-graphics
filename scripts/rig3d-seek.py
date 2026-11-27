#!/usr/bin/env python3
"""Compare Tibi seek parity, or cutaway locality; neither is anatomical approval.

    python scripts/rig3d-seek.py --out qa/rig3d-seek [--set all|skin|feet|scenes|modes|joints]
    python scripts/rig3d-seek.py --profile distance --out qa/rig3d-seek-candidate
    python scripts/rig3d-seek.py --set locality --out qa/cutaway-locality
    python scripts/rig3d-seek.py --out qa/rig3d-seek-after --baseline qa/rig3d-seek/report.json
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "pipeline"))

from browser_stills import chrome  # noqa: E402
from hostlock import heavy_lock  # noqa: E402

PRESETS = {
    "skin": ["skin"],
    "feet": ["foot"],
    "scenes": ["scene", "split-scene", "camera-cache"],
    "modes": ["mode-reset", "cutaway-ramp"],
    "joints": ["shoulder-twist", "overhead", "deep-flexion"],
}


def run(
    out: Path, selection: str, gender: str, baseline: Path | None, profile: str = "distance",
    unclipped_control: bool = False,
) -> int:
    from PIL import Image, ImageChops, ImageDraw
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    locality = selection == "locality"
    if locality:
        cases = ["cutaway-locality"]
    else:
        cases = [case for group in PRESETS.values() for case in group] if selection == "all" else PRESETS[selection]
    previous = json.loads(baseline.read_text(encoding="utf-8")) if baseline else None
    previous_rows = {row["id"]: row for row in previous["cases"]} if previous else {}
    rows, performance = [], {}
    width, height = 480, 640
    inputs = {name: hashlib.sha256((ROOT / "src" / "studio" / name).read_bytes()).hexdigest()
              for name in ("studio-core.js", "kits/fitness/tibi3d.js", "kits/fitness/anatomy3d.js")}
    with heavy_lock("render", slug="rig3d-seek"):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=chrome(), headless=True,
                args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader",
                      "--enable-unsafe-swiftshader", "--enable-precise-memory-info"],
            )
            try:
                for body in ("m", "f") if gender == "both" else (gender,):
                    for case in cases:
                        page = browser.new_page(viewport={"width": width, "height": height})
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))

                        def console_message(message):
                            if message.type == "error":
                                errors.append(message.text)

                        page.on("console", console_message)
                        try:
                            query = urlencode({"g": body, "case": case, "w": width,
                                               "h": height, "profile": profile,
                                               "unclipped": "1" if unclipped_control else "0"})
                            url = (ROOT / "assets" / "fitness" / "lab3d" / "seek-bench.html").as_uri()
                            page.goto(url + "?" + query, wait_until="load", timeout=90000)
                            if page.title() != "ready":
                                raise RuntimeError(f"Seek bench did not initialise: {body} {case}: {errors}")
                            before = page.evaluate("seekBench.reference()")
                            fresh = out / f"{body}-{case}-fresh.png"
                            page.screenshot(path=str(fresh))
                            after = page.evaluate("seekBench.revisit()")
                            revisited = out / f"{body}-{case}-revisited.png"
                            page.screenshot(path=str(revisited))
                            if errors:
                                raise RuntimeError(f"{body} {case}: {errors}")
                            with Image.open(fresh) as a, Image.open(revisited) as b:
                                a, b = a.convert("RGB"), b.convert("RGB")
                                diff = ImageChops.difference(a, b)
                                channels = diff.split()
                                mask = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
                                changed_pixels = width * height - mask.histogram()[0]
                                outside_changes, inside_changes = None, None
                                if locality:
                                    bounds = before["windowRoi"]
                                    if not (0 <= bounds[0] < bounds[2] <= width and 0 <= bounds[1] < bounds[3] <= height):
                                        raise RuntimeError(f"Invalid projected window bounds: {bounds}")
                                    outside = mask.copy()
                                    outside.paste(0, tuple(bounds))
                                    outside_changes = width * height - outside.histogram()[0]
                                    inside_changes = changed_pixels - outside_changes
                                sheet = Image.new("RGB", (width * 3, height + 24), (246, 243, 236))
                                draw = ImageDraw.Draw(sheet)
                                for index, (label, image) in enumerate((
                                    ("Skin-only opening" if locality else "Fresh target", a),
                                    ("Opening with internal anatomy" if locality else "Same target after another state", b),
                                    ("Pixel difference (not amplified)", diff),
                                )):
                                    draw.text((index * width + 8, 6), label, fill=(27, 29, 41))
                                    sheet.paste(image, (index * width, 24))
                                if locality:
                                    draw.rectangle((2 * width + bounds[0], 24 + bounds[1],
                                                    2 * width + bounds[2], 24 + bounds[3]),
                                                   outline=(255, 178, 36), width=2)
                                sheet_name = f"{body}-{case}.png"
                                sheet.save(out / sheet_name)
                                b.resize((120, 160), Image.Resampling.LANCZOS).save(
                                    out / f"{body}-{case}-thumb.png")
                            failures = []
                            if before != after:
                                failures.append("numeric state depends on seek history")
                            if locality and outside_changes:
                                failures.append(f"{outside_changes} pixels changed outside the projected cutaway bounds")
                            if locality and inside_changes < 100:
                                failures.append("No substantial internal anatomy appeared inside the opening")
                            if not locality and changed_pixels:
                                failures.append(f"{changed_pixels} pixels depend on seek history")
                            if after.get("projectionError", 0) > 1e-6:
                                failures.append("overlay projection is not from the rendered camera")
                            if any(after.get("projectionCameraChildren", [])):
                                failures.append("projection cameras retain copied scene objects")
                            row = {"id": f"{body}-{case}", "status": "fail" if failures else "pass",
                                   "failures": failures, "changed_pixels": changed_pixels,
                                   "reference": before, "revisited": after, "sheet": sheet_name}
                            if locality:
                                row.update(outside_changes=outside_changes, inside_changes=inside_changes,
                                           criterion="No internal rendering outside projected window bounds; visible anatomy inside.")
                            if row["id"] in previous_rows:
                                row["baseline_status"] = previous_rows[row["id"]]["status"]
                            rows.append(row)
                            if case == "skin":
                                performance[body] = page.evaluate("seekBench.measure()")
                            print(row["id"], row["status"], "; ".join(failures), flush=True)
                        finally:
                            page.close()
            finally:
                browser.close()
    report = {"at": datetime.now(timezone.utc).isoformat(), "set": selection, "profile": profile,
              "criterion": "No internal rendering outside projected window bounds; visible anatomy inside." if locality else
              "Identical same-host pixels, transforms and attribute fingerprints at the same target, regardless of history.",
              "not_checked": "Anatomy accuracy, complete pose matrix, Mac rendering, narration.",
              "size": [width, height], "input_sha256": inputs, "cases": rows, "performance": performance,
              "negative_control": "unclipped" if unclipped_control else None}
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    overview = Image.new("RGB", (6 * 160, ((len(rows) + 5) // 6) * 214), (246, 243, 236))
    draw = ImageDraw.Draw(overview)
    for i, row in enumerate(rows):
        x, y = (i % 6) * 160, (i // 6) * 214
        with Image.open(out / f"{row['id']}-thumb.png") as image:
            overview.paste(image, (x + 20, y + 38))
        draw.text((x + 8, y + 5), row["id"], fill=(27, 29, 41))
        draw.text((x + 8, y + 21), row["status"].upper(),
                  fill=(5, 110, 80) if row["status"] == "pass" else (170, 42, 32))
    overview.save(out / "overview.png")
    lines = ["# Tibi seek-order acceptance", "", report["at"], "", report["criterion"], "",
             "A pass is not human G3 approval. Uncovered anatomy/design quality is a known limit.", "",
             "![Current-state thumbnails](overview.png)", "",
             "| Case | Start state | Current state | Evidence |",
             "| --- | --- | --- | --- |"]
    for row in rows:
        lines.append(f"| {row['id']} | {row.get('baseline_status', 'not supplied')} | "
                     f"{row['status']} | [Fresh / revisited / difference]({row['sheet']}) |")
    lines += ["", "## Known limits", "", report["not_checked"], "",
              "## Performance", "", "Build and 60 warm pose/render/GPU-finish frames; "
              "10 warm-up frames; screenshot/encoding excluded.", "",
              "```json", json.dumps(performance, indent=2), "```", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return int(any(row["status"] == "fail" for row in rows))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "qa" / "rig3d-seek")
    parser.add_argument("--set", choices=["all", *PRESETS, "locality"], default="all")
    parser.add_argument("--gender", choices=["m", "f", "both"], default="both")
    parser.add_argument("--profile", choices=["legacy", "distance"], default="distance")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--unclipped-control", action="store_true",
                        help="Locality negative control: disable the inner window clip in memory.")
    args = parser.parse_args()
    if args.unclipped_control and args.set != "locality":
        parser.error("--unclipped-control requires --set locality")
    return run(args.out.resolve(), args.set, args.gender, args.baseline, args.profile,
               args.unclipped_control)


if __name__ == "__main__":
    sys.exit(main())
