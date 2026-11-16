#!/usr/bin/env python3
"""fitness-publish.py: the publishing assets of a finished fitness film, generated from the project's own records (nothing invented).

    .venv/bin/python scripts/fitness-publish.py <slug> [--out projects/<slug>/publish]

Writes metadata.json, description.md and thumbnail.png:
  titles        three options (the question the film answers, the finding as a statement, a myth-bust), each flagged with the claim id it rests on
  description   hook line, chapter markers from the storyboard (mm:ss), the sources from the dossier with their verification route, credits, the
                general-education line, hashtags by category
  platforms     what each target platform wants for this form, and whether the render already fits
  thumbnail     the poster frame with the title set on it (brand colours); the story-writer's chosen cover, if one exists, wins
  adaptations   which scenes could be cut into short-form posts (those with a number or a named study)
Only dossier claims and storyboard text are used, so the metadata cannot claim more than the film does.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = {
    "instagram-reels": {"aspect": "9:16", "max_sec": 90, "note": "cover text inside the central 4:5 crop; captions burned in"},
    "youtube-shorts": {"aspect": "9:16", "max_sec": 60, "note": "under 60 s to count as a Short; title <= 100 characters"},
    "youtube": {"aspect": "16:9", "max_sec": None, "note": "chapters need the first at 0:00 and at least three, each >= 10 s"},
    "linkedin": {"aspect": "1:1 or 16:9 or 9:16", "max_sec": 600, "note": "captions burned in; first 3 s carry the hook"},
}


def mmss(t: float) -> str:
    return f"{int(t) // 60}:{int(t) % 60:02d}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    pdir = ROOT / "projects" / a.slug
    out = Path(a.out) if a.out else pdir / "publish"
    out.mkdir(parents=True, exist_ok=True)
    project = json.loads((pdir / "project.json").read_text())
    brief = json.loads((pdir / "brief.json").read_text()) if (pdir / "brief.json").exists() else {}
    sb = json.loads((pdir / "storyboard.json").read_text())
    dossier = json.loads((pdir / "research" / "dossier.json").read_text()) if (pdir / "research" / "dossier.json").exists() else {}
    claims = {c["id"]: c for c in dossier.get("claims", [])}
    sources = {s["id"]: s for s in dossier.get("sources", [])}
    scenes = sb["scenes"]
    title = project.get("title") or brief.get("title") or a.slug
    myth = next((c for c in claims.values() if c.get("kind") == "myth"), None)
    finding = next((c for c in claims.values() if c.get("kind") not in ("myth", None) and len(c.get("claim", "")) <= 95), None)      # a title is never truncated mid-sentence
    titles = [{"text": title if title.endswith("?") else title + "?", "angle": "the question", "claim": None}]
    if finding:
        titles.append({"text": finding["claim"].rstrip("."), "angle": "the finding", "claim": finding["id"]})
    if myth:
        w = myth.get("wording") or myth["claim"]
        titles.append({"text": f"\"{w.rstrip('.')}\": is it true?"[:99], "angle": "the myth", "claim": myth["id"]})
    chapters = [(float(s["start_sec"]), s.get("title", s["id"])) for s in scenes]
    if chapters and chapters[0][0] > 0:
        chapters[0] = (0.0, chapters[0][1])
    refs = []
    for s in sources.values():
        refs.append(f"{s['citation']}  [verified via: {s.get('verified_via', 'unrecorded')}]")
    cats = brief.get("categories", ["fitness"])
    tags = ["#" + c.replace(" ", "") for c in cats] + ["#exerciseScience", "#Sinew", "#strengthTraining"]
    credits = ["Narration: synthetic voice (Kokoro), not a person.", "Sound: original, synthesised for this film (Sinew sound identity).", "Visuals: Tibi, the Sinew mascot; authored key poses, not motion capture.",
               "Runtime: Motion Lab studio (HyperFrames, Three.js)."]
    disclaimer = "General education, not medical advice. Motion shown is illustrative."
    desc = [brief.get("objective", title), ""]
    if len(scenes) >= 3:
        desc += ["Chapters"] + [f"{mmss(t)} {n}" for t, n in chapters] + [""]
    desc += ["Sources"] + refs + [""] + ["Credits"] + credits + ["", disclaimer, "", " ".join(tags)]
    dur = float(project.get("duration_sec", sb.get("duration_sec", 0)))
    fmt = project["formats"][0]
    plat = {}
    for p in brief.get("platforms", []):
        spec = PLATFORMS.get(p, {})
        ok = (spec.get("max_sec") is None or dur <= spec["max_sec"])
        plat[p] = {**spec, "film_sec": dur, "fits_length": ok, "render": f"{fmt['width']}x{fmt['height']}"}
    adapt = []
    for s in scenes:
        text = s.get("narration", "")
        if re.search(r"\d", text) or re.search(r"[A-Z][a-z]+ et al|study|trial", text):
            adapt.append({"scene": s["id"], "start": s["start_sec"], "end": s["end_sec"], "why": "carries a number or a named study: a self-contained 15-30 s clip with its own hook"})
    meta = {"slug": a.slug, "titles": titles, "chapters": [{"t": t, "title": n} for t, n in chapters], "references": refs, "credits": credits, "disclaimer": disclaimer, "hashtags": tags,
            "platforms": plat, "short_form_adaptations": adapt if project.get("type") != "short" and dur > 75 else [], "unverified": [k for k, s in sources.items() if not s.get("verified_via")]}
    (out / "metadata.json").write_text(json.dumps(meta, indent=1))
    (out / "description.md").write_text("\n".join(desc) + "\n")
    # thumbnail: the poster, with the title set on it
    poster = pdir / "poster.jpg"
    final = sorted((pdir / "renders").glob("*/final.mp4"))
    try:
        from PIL import Image, ImageDraw, ImageFont
        if final:
            t0 = min(float(scenes[0]["end_sec"]) - 0.5, float(scenes[0]["start_sec"]) + 1.8)
            tmp = out / "_frame.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(max(0.2, t0)), "-i", str(final[0]), "-frames:v", "1", str(tmp)], check=True)
            im = Image.open(tmp).convert("RGB")
            tmp.unlink()
        else:
            im = Image.open(poster).convert("RGB")
        w, h = im.size
        dr = ImageDraw.Draw(im, "RGBA")
        dr.rectangle([0, 0, w, int(h * 0.2)], fill=(246, 243, 236, 236))
        try:
            f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", int(h * 0.05))
        except OSError:
            f = ImageFont.load_default()
        words, lines, cur = title.split(), [], ""
        for wd in words:
            if len(cur) + len(wd) > 22:
                lines.append(cur.strip())
                cur = ""
            cur += wd + " "
        lines.append(cur.strip())
        y = int(h * 0.025)
        for ln in lines[:2]:
            dr.text((int(w * 0.06), y), ln, fill=(27, 29, 41), font=f)
            y += int(h * 0.06)
        dr.rectangle([int(w * 0.06), int(h * 0.185), int(w * 0.06) + int(w * 0.16), int(h * 0.19)], fill=(255, 178, 36))
        im.save(out / "thumbnail.png")
    except Exception as exc:  # pragma: no cover
        print("thumbnail skipped:", exc)
    print(f"publish assets for {a.slug}: {len(titles)} titles, {len(chapters)} chapters, {len(refs)} sources -> {out.relative_to(ROOT)}")
    for t in titles:
        print(f"  title ({t['angle']}): {t['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
