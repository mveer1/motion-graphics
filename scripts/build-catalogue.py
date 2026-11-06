#!/usr/bin/env python3
"""Build out/catalogue.html: every project grouped by topic category, plus a tab that
shows the backlog in docs/project-ideas.md.

Reads projects/*/ (brief.json, project.json, renders), specs/categories.json,
specs/video-types.json (reel, long-reel, youtube; a second filter row and a badge on every tile)
and docs/project-ideas.md. Writes one self-contained HTML file next to the delivered videos so
the relative video links work. Runs anywhere; it only reads files (ffprobe is optional and
used for the runtime of legacy projects that have no project.json).

    python3 scripts/build-catalogue.py
"""

import hashlib
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from poster import POSTER, SIDECAR, all_films, find_film  # noqa: E402  (scripts/poster.py)

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"
OUT = ROOT / "out"
IDEAS = ROOT / "docs" / "project-ideas.md"
TARGET = OUT / "catalogue.html"

# Legacy projects have no brief.json, so their categories live here until the TODO.md item
# "Backfill categories in the brief.json of existing projects" is done.
FALLBACK_CATEGORIES = {
    "btree-database-indexing": ["technology"],
    "distributed-consensus-raft": ["technology"],
    "neural-network-learning": ["technology"],
    "china-market-crash": ["finance", "history"],
    "masala-chai": ["science"],
    "paper-plane-field-notes": ["science"],
}
NOTES = {
    "motion-quality-v1-baseline": "Pipeline benchmark: template-driven baseline.",
    "motion-quality-v2-directed": "Pipeline benchmark: the same topic after creative direction.",
}
# Accent per category (dots and bars only; text stays charcoal for contrast).
COLORS = {
    "technology": "#2740c8",
    "finance": "#12805c",
    "science": "#d99a1a",
    "history": "#d9432b",
    "mathematics": "#2b2b2b",
    "news": "#0f7c8a",
    "storytelling": "#b5456b",
}


# Accent per video type (specs/video-types.json). Every project gets one: its brief's video_type,
# else the type its finished film's length falls in (type_for).
TYPE_COLORS = {"reel": "#d9432b", "long-reel": "#2740c8", "youtube": "#12805c"}
# Progress, read from the files on disk: a stage (no finished film / finished film / finished film and a
# passing creative review) plus a flag "rerender" when the only finished film is a superseded one in renders/history/.
PROGRESS = [
    ("in-production", "In production", "#9a958b", "No finished film yet"),
    ("rendered", "Rendered", "#2740c8", "A finished film exists; no passing creative review yet"),
    ("reviewed", "Reviewed", "#12805c", "A finished film and a passing creative review (qa/creative-review.json)"),
    ("rerender", "Re-render due", "#d99a1a", "The finished film is superseded (it sits in renders/history/); the runtime or composition has moved on"),
]
PROGRESS_BY_ID = {p[0]: p for p in PROGRESS}


def load_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def probe_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=20,
        ).stdout.strip()
        return float(out)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def read_version(folder):
    """One project folder (or one version folder) -> display record."""
    brief, proj = load_json(folder / "brief.json"), load_json(folder / "project.json")
    dossier = load_json(folder / "research.json")
    research = dossier.get("metadata", {})
    renders = folder / "renders"
    formats = proj.get("formats") and [f["id"] for f in proj["formats"]]
    if not formats and renders.is_dir():
        formats = sorted(d.name for d in renders.iterdir() if (d / "final.mp4").exists())
    duration = proj.get("duration_sec")
    final = next(iter(sorted(renders.glob("*/final.mp4"))), renders / "final.mp4")
    if duration is None and final.exists():
        duration = probe_duration(final)
    found = find_film(folder)
    films = [{"href": quote(os.path.relpath(f, OUT).replace(os.sep, "/")), "format": fmt, "current": cur,
              "sec": None} for f, fmt, cur in all_films(folder)]
    sidecar = load_json(folder / SIDECAR) if (folder / POSTER).exists() else {}
    film_sec = sidecar.get("film_duration_sec") or (duration if duration else None)
    review = load_json(folder / "qa" / "creative-review.json")
    scores = [c["score"] for c in review.get("criteria", []) if isinstance(c.get("score"), (int, float))]
    passed = review.get("verdict") == "pass" and bool(scores)
    progress = "in-production" if not found else ("reviewed" if passed else "rendered")
    rerender = bool(found) and not found[2]
    return {
        "films": films,
        "poster": (folder / POSTER) if (folder / POSTER).exists() else None,
        "film_sec": film_sec,
        "review_mean": round(sum(scores) / len(scores), 1) if passed else None,
        "progress": progress,
        "rerender": rerender,
        "declared_type": brief.get("deliverables", {}).get("video_type"),
        "name": folder.name,
        "title": brief.get("title") or proj.get("title") or research.get("title") or folder.name,
        "objective": brief.get("objective") or dossier.get("pedagogy", {}).get("core_thesis") or "",
        "categories": brief.get("categories") or [],
        "formats": formats or [],
        "duration": duration,
        "style": proj.get("style") or "",
    }


def read_projects():
    records = []
    for folder in sorted(PROJECTS.iterdir()):
        if not folder.is_dir():
            continue
        slug = folder.name
        if (folder / "project.json").exists():
            versions = [read_version(folder)]
            versions[0]["name"] = "single version"
            archived = 0
        else:
            subs = [d for d in sorted(folder.iterdir()) if d.is_dir() and d.name != "archive"]
            versions = [read_version(d) for d in subs if (d / "src").exists() or (d / "renders").exists()]
            archive = folder / "archive"
            archived = sum(1 for d in archive.iterdir() if d.is_dir()) if archive.is_dir() else 0
        if not versions:
            continue
        latest = versions[-1]
        cats = latest["categories"] or FALLBACK_CATEGORIES.get(slug, [])
        records.append({
            "slug": slug,
            "latest": latest,
            "versions": versions,
            "archived": archived,
            "categories": cats,
            "videos": find_videos(slug),
            "note": NOTES.get(slug, ""),
        })
    return records


def find_videos(slug):
    """Delivered files in out/: <slug>-<format>.mp4, or out/<slug>/*.mp4 for versioned projects."""
    files = sorted(OUT.glob(f"{slug}-*.mp4")) + sorted((OUT / slug).glob("*.mp4"))
    return [(f.stem, f.relative_to(OUT).as_posix()) for f in files]


def read_video_types():
    """The three supported types in spec order, with a short badge label."""
    spec = load_json(ROOT / "specs" / "video-types.json")
    margin = spec.get("margin_sec", 0)
    shorts = {"reel": "Reel", "long-reel": "Long reel", "youtube": "YouTube"}
    out = []
    for tid, t in spec["types"].items():
        lo, hi = t["nominal_sec"]["min"], t["nominal_sec"].get("max")
        out.append({"id": tid, "name": t["name"], "short": shorts.get(tid, t["name"]), "format": t["format"],
                    "nominal": f"{lo}+ s" if hi is None else f"{lo}-{hi} s", "max": hi, "margin": margin})
    return out


def type_for(v, types):
    """(type id, derived). The brief's video_type when it has one, else by the film's length:
    up to a reel's 60 s -> reel (anything under 45 s is a short reel), up to 180 s -> long reel, longer -> YouTube."""
    ids = {t["id"] for t in types}
    if v["declared_type"] in ids:
        return v["declared_type"], False
    sec = v["film_sec"] or 0
    for t in types:
        if t["max"] is None or sec <= t["max"]:
            return t["id"], True
    return types[-1]["id"], True


def read_categories():
    data = load_json(ROOT / "specs" / "categories.json")
    return data["categories"]


def read_ideas(valid_ids, valid_types):
    """docs/project-ideas.md -> (preamble, ideas). One bullet per idea:
    - **Title** — pitch (also: id, id) [length]   (also is optional; the length tag is required)."""
    ideas, current, preamble, seen_heading = [], None, [], False
    for n, line in enumerate(IDEAS.read_text().splitlines(), 1):
        if line.startswith("## "):
            seen_heading = True
            current = line[3:].strip()
            if current not in valid_ids:
                sys.exit(f"{IDEAS.name}:{n}: unknown category '{current}' (see specs/categories.json)")
        elif line.startswith("- "):
            m = re.match(r"- \*\*(.+?)\*\* — (.+)$", line)
            if not m or not current:
                sys.exit(f"{IDEAS.name}:{n}: expected '- **Title** — pitch' under a '## category' heading")
            title, pitch = m.groups()
            length = re.search(r"\s*\[([a-z-]+)\]\s*$", pitch)
            if not length or length.group(1) not in valid_types:
                sys.exit(f"{IDEAS.name}:{n}: end the bullet with a length tag, one of {', '.join('[' + t + ']' for t in valid_types)}")
            pitch = pitch[: length.start()]
            also = re.search(r"\s*\(also: ([a-z, ]+)\)\s*$", pitch)
            extra = [c.strip() for c in also.group(1).split(",")] if also else []
            if also:
                pitch = pitch[: also.start()]
            for c in extra:
                if c not in valid_ids:
                    sys.exit(f"{IDEAS.name}:{n}: unknown category '{c}' in (also: ...)")
            ideas.append({"id": f"s{len(ideas)}", "title": title, "pitch": pitch.strip(), "topic": current,
                          "also": extra, "type": length.group(1)})
        elif not seen_heading:
            preamble.append(line)
    return "\n".join(preamble).rstrip() + "\n", ideas


e = html.escape


def runtime(sec):
    if not sec:
        return ""
    sec = round(sec)
    return f"{sec // 60}:{sec % 60:02d}"


def tag(cat_by_id, cid, primary=False):
    cat = cat_by_id[cid]
    cls = "tag primary" if primary else "tag"
    return f'<span class="{cls}" style="--c:{COLORS[cid]}">{e(cat["name"])}</span>'


def project_card(p, cat_by_id, type_by_id):
    cat_order = {cid: i for i, cid in enumerate(cat_by_id)}
    prog_order = {pid: i for i, (pid, *_rest) in enumerate(PROGRESS)}
    v = p["latest"]
    cats = p["categories"]
    vt, derived = p["type"], p["type_derived"]
    t = type_by_id[vt]
    prog = PROGRESS_BY_ID[v["progress"]]
    qtext = e(f'{v["title"]} {p["slug"]} {v["objective"] or p["note"]}'.lower())
    attrs = (f'data-cats="{" ".join(cats)}" data-types="{vt}" data-progress="{v["progress"]}{" rerender" if v["rerender"] else ""}" '
             f'data-q="{qtext}" data-title="{e(v["title"].lower())}" data-topic="{cat_order.get(cats[0], 99)}" '
             f'data-len="{round(v["film_sec"] or 0)}" data-prog="{prog_order[v["progress"]] * 2 + (1 if v["rerender"] else 0)}" '
             f'style="--c:{COLORS[cats[0]]}"')
    type_hint = f'{t["name"]}' + (f' (tagged by its {runtime(v["film_sec"])} length)' if derived else " (set in the brief)")
    if derived and v["film_sec"] and v["film_sec"] < 45:
        type_hint += ", shorter than the 45 s a reel normally runs"
    poster = ""
    if v["poster"]:
        src = e(os.path.relpath(v["poster"], OUT).replace(os.sep, "/"))
        film = v["films"][0]["href"] if v["films"] else src
        poster = (f'<a class="poster" href="{film}" target="_blank" rel="noopener" style="--img:url(\'{src}\')" '
                  f'title="Play the film (opens in a new tab)">'
                  f'<img src="{src}" alt="Poster for {e(v["title"])}" loading="lazy"><span class="play">▶</span></a>')
    else:
        poster = '<div class="poster none" title="No finished film, so no poster yet">no poster yet</div>'
    rerender = f'<span class="stale" title="{e(PROGRESS_BY_ID["rerender"][3])}">↻ re-render</span>' if v["rerender"] else ""
    review = f'<span class="score" title="Creative review passed, mean score {v["review_mean"]}">★ {v["review_mean"]:g}</span>' if v["review_mean"] else ""
    length = f'<span class="len">{runtime(v["film_sec"])}</span>' if v["film_sec"] else ""
    meta = [" · ".join(v["formats"])]
    meta_html = "".join(f"<span>{e(m)}</span>" for m in meta if m)
    tags = "".join(tag(cat_by_id, c, i == 0) for i, c in enumerate(cats))
    def short(label):
        rest = label[len(p["slug"]):].lstrip("-") if label.startswith(p["slug"]) else label
        return rest or label
    if v["films"]:
        videos = "".join(
            f'<a href="{f["href"]}" target="_blank" rel="noopener" title="{"Current render" if f["current"] else "Finished film (superseded; the next build makes a new one)"}">'
            f'▶ {e(f["format"] or "film")}{"" if f["current"] else " (old)"}</a>' for f in v["films"])
    else:  # nothing in renders/: fall back to any file delivered to out/
        videos = "".join(f'<a href="{e(href)}" title="{e(label)}">▶ {e(short(label))}</a>' for label, href in p["videos"])
    videos_html = f'<div class="files">{videos}</div>' if videos else ""
    obj = v["objective"] or p["note"]
    versions_html = ""
    if len(p["versions"]) > 1 or p["archived"]:
        rows = "".join(
            f'<li><b>{e(x["name"])}</b> {e(x["title"])}'
            f'<small>{e(" · ".join(s for s in [runtime(x["film_sec"]), x["style"]] if s))}</small></li>'
            for x in p["versions"]
        )
        arch = f'<li class="arch">+ {p["archived"]} archived</li>' if p["archived"] else ""
        versions_html = f'<details><summary>{len(p["versions"])} versions</summary><ul>{rows}{arch}</ul></details>'
    return f"""
      <article class="card item" {attrs} title="{e(p["slug"])}: {e(obj)}">
        <div class="pwrap">{poster}
          <span class="vt" style="--t:{TYPE_COLORS[vt]}" title="{e(type_hint)}">{e(t["short"])}{"*" if derived else ""}</span>{length}
        </div>
        <div class="prog" style="--p:{prog[2]}" title="{e(prog[3])}"><i></i>{e(prog[1])}{rerender}{review}</div>
        <h3>{e(v["title"])}</h3>
        <div class="meta">{meta_html}</div>
        <div class="tags">{tags}</div>
        {videos_html}
        {versions_html}
      </article>"""


def type_chips(types, counts, total):
    out = [f'<button class="chip on" data-type="all">All types <b>{total}</b></button>']
    for t in types:
        out.append(f'<button class="chip typechip" data-type="{t["id"]}" style="--c:{TYPE_COLORS[t["id"]]}" '
                   f'title="{e(t["format"])}, {e(t["nominal"])}, +-{t["margin"]:g} s">{e(t["name"])} <b>{counts.get(t["id"], 0)}</b></button>')
    return f'<div class="chips" role="group" aria-label="Filter by video type">{"".join(out)}</div>'


def progress_chips(counts, total):
    out = [f'<button class="chip on" data-progress="all">All progress <b>{total}</b></button>']
    for pid, name, color, hint in PROGRESS:
        out.append(f'<button class="chip typechip" data-progress="{pid}" style="--c:{color}" title="{e(hint)}">{e(name)} <b>{counts.get(pid, 0)}</b></button>')
    return f'<div class="chips" role="group" aria-label="Filter by progress">{"".join(out)}</div>'


def chips(categories, counts, total):
    out = [f'<button class="chip on" data-cat="all">All topics <b>{total}</b></button>']
    for c in categories:
        if counts.get(c["id"]):
            out.append(
                f'<button class="chip" data-cat="{c["id"]}" style="--c:{COLORS[c["id"]]}">'
                f'<i class="cdot"></i>{e(c["name"])} <b>{counts[c["id"]]}</b></button>'
            )
    return f'<div class="chips" role="group" aria-label="Filter by category">{"".join(out)}</div>'


def counts_for(items):
    counts = {}
    for x in items:
        for c in set(x["categories"]):
            counts[c] = counts.get(c, 0) + 1
    return counts


CSS = r"""
:root {
  --bg: #fbfbfa; --paper: #ffffff; --ink: #1d1d1b; --muted: #6b6760; --line: #e6e2da; --line-2: #cfc9bd;
  --sheet: #f5f3ef; --accent: #2740c8; --emerald: #12805c; --amber: #b87a0c; --danger: #c23a22;
  --bar-h: 52px; --r: 6px;
  --m-in: 140ms; --m-out: 200ms; --m-press: 90ms; --m-image: 600ms; --ease: cubic-bezier(.2, .8, .2, 1);
  --font: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
  --mono: "SF Mono", Menlo, Consolas, monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { scrollbar-gutter: stable; }
body { overflow-wrap: anywhere; background: var(--bg); color: var(--ink); font: 14px/1.45 var(--font); font-variant-numeric: tabular-nums; }
button, input, select, textarea { font: inherit; color: inherit; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.wrap { width: 100%; max-width: 2400px; margin: 0 auto; padding: 0 24px; }

/* top bar: one row, no hero */
.bar { position: sticky; top: 0; z-index: 30; height: var(--bar-h); background: var(--bg); border-bottom: 1px solid var(--line); }
.bar-in { height: 100%; display: flex; align-items: center; gap: 28px; }
.brand { font-weight: 700; letter-spacing: -.01em; font-size: 15px; white-space: nowrap; }
.tabs { display: flex; gap: 2px; height: 100%; }
.tab { position: relative; display: flex; align-items: center; gap: 7px; padding: 0 14px; border: 0; background: none; cursor: pointer; color: var(--muted); font-weight: 600; font-size: 14px; transition: color var(--m-in) var(--ease); }
.tab span { font: 500 11px var(--mono); color: var(--muted); }
.tab::after { content: ""; position: absolute; left: 14px; right: 14px; bottom: -1px; height: 2px; background: var(--ink); transform: scaleX(0); transform-origin: left; transition: transform var(--m-out) var(--ease); }
.tab:hover { color: var(--ink); }
.tab:hover::after { transform: scaleX(1); }
.tab[aria-selected="true"] { color: var(--ink); }
.tab[aria-selected="true"]::after { transform: scaleX(1); background: var(--accent); }
.stats { margin-left: auto; display: flex; flex-wrap: wrap; gap: 2px 16px; justify-content: flex-end; font: 12px var(--mono); color: var(--muted); }
.stats b { color: var(--ink); font-weight: 600; margin-right: 4px; }
.stats i { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 5px; background: var(--c); }
.panel[hidden] { display: none; }

/* buttons: one style. hover steps the fill and lifts 1px; press sinks 1px */
.btn { display: inline-flex; align-items: center; gap: 6px; height: 30px; padding: 0 12px; border: 1px solid var(--line-2); border-radius: var(--r); background: var(--paper); cursor: pointer; font-size: 12.5px; font-weight: 600; white-space: nowrap; transition: background-color var(--m-out) var(--ease), border-color var(--m-out) var(--ease), transform var(--m-out) var(--ease); }
.btn.primary { background: var(--ink); border-color: var(--ink); color: #fff; }
@media (hover: hover) and (pointer: fine) {
  .btn:hover { background: #f1eee8; border-color: var(--ink); transform: translateY(-1px); transition-duration: var(--m-in); }
  .btn.primary:hover { background: #3a3a37; }
}
.btn:active { transform: translateY(1px) scale(.985); transition-duration: var(--m-press); }
.field { height: 30px; padding: 0 10px; border: 1px solid var(--line-2); border-radius: var(--r); background: var(--paper); font-size: 13px; transition: border-color var(--m-in) var(--ease), box-shadow var(--m-in) var(--ease); }
.field:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(39, 64, 200, .14); }
input.field { width: 220px; }

/* catalogue toolbar */
.tools { position: sticky; top: var(--bar-h); z-index: 20; background: var(--bg); padding: 10px 0 8px; display: flex; flex-wrap: wrap; align-items: center; gap: 8px 22px; border-bottom: 1px solid var(--line); }
.fgroup { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.flabel { font: 600 10px var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin-right: 2px; }
.chip { font-size: 12px; font-weight: 500; padding: 3px 10px; border: 1px solid var(--line); border-radius: 99px; background: var(--paper); cursor: pointer; display: inline-flex; gap: 6px; align-items: center; transition: background-color var(--m-out) var(--ease), border-color var(--m-out) var(--ease), transform var(--m-out) var(--ease); }
.chip b { font: 500 10.5px var(--mono); color: var(--muted); }
@media (hover: hover) and (pointer: fine) { .chip:hover { border-color: var(--ink); transform: translateY(-1px); transition-duration: var(--m-in); } }
.chip:active { transform: translateY(1px) scale(.985); transition-duration: var(--m-press); }
.chip.on { background: var(--ink); color: #fff; border-color: var(--ink); }
.chip.on b { color: #ddd; }
.chip.typechip.on { background: var(--c); border-color: var(--c); }
.chip.typechip.on b { color: #fff; }

.chip .cdot { width: 8px; height: 8px; border-radius: 50%; background: var(--c); flex: none; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(172px, 1fr)); gap: 12px; margin-top: 14px; }

/* project tiles: poster first */
.card { position: relative; background: color-mix(in srgb, var(--c) 5%, #fff); border: 1px solid color-mix(in srgb, var(--c) 22%, var(--line)); border-top: 4px solid var(--c); border-radius: var(--r); padding: 9px 10px 10px; display: flex; flex-direction: column; gap: 6px; min-width: 0; transition: transform 180ms var(--ease), border-color var(--m-out) var(--ease), box-shadow 180ms var(--ease); }
.card.hide { display: none; }
@media (hover: hover) and (pointer: fine) {
  .card:hover { transform: translateY(-2px); border-color: var(--line-2); border-top-color: var(--c); box-shadow: 0 8px 24px rgba(29, 29, 27, .09); }
  .card:hover .poster img { transform: scale(1.03); }
}
.pwrap { position: relative; }
.poster { display: block; position: relative; aspect-ratio: 1 / 1; overflow: hidden; border-radius: 4px; background: #f1eee8; border: 1px solid var(--line); }
.poster::before { content: ""; position: absolute; inset: -12px; background: var(--img) center / cover; filter: blur(14px) saturate(.85); opacity: .5; }
.poster img { position: relative; width: 100%; height: 100%; object-fit: contain; display: block; transition: transform var(--m-image) var(--ease); }
.poster.none { display: grid; place-items: center; color: var(--muted); font: 10.5px var(--mono); }
.poster.none::before { display: none; }
.play { position: absolute; left: 6px; bottom: 6px; width: 22px; height: 22px; border-radius: 50%; background: rgba(20, 20, 20, .78); color: #fff; display: grid; place-items: center; font-size: 9px; padding-left: 1px; pointer-events: none; }
.vt { position: absolute; top: 6px; left: 6px; font: 700 9px var(--mono); letter-spacing: .05em; text-transform: uppercase; color: #fff; background: var(--t); padding: 2px 7px; border-radius: 99px; box-shadow: 0 1px 3px rgba(0, 0, 0, .25); }
.len { position: absolute; right: 6px; bottom: 6px; font: 600 10.5px var(--mono); color: #fff; background: rgba(20, 20, 20, .78); padding: 1px 6px; border-radius: 4px; }
.prog { display: flex; flex-wrap: wrap; align-items: center; gap: 2px 6px; white-space: nowrap; font: 600 10.5px var(--mono); }
.prog i { width: 8px; height: 8px; border-radius: 50%; background: var(--p); flex: none; }
.stale { color: var(--amber); font-weight: 600; }
.score { margin-left: auto; color: var(--emerald); font-weight: 700; }
.card h3 { font-size: 13.5px; line-height: 1.25; letter-spacing: -.005em; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.meta { display: flex; flex-wrap: wrap; gap: 2px 8px; font: 10.5px var(--mono); color: var(--muted); }
.tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: auto; }
.tag { position: relative; font-size: 10px; padding: 1px 7px 1px 15px; border-radius: 99px; border: 1px solid var(--line); }
.tag::before { content: ""; position: absolute; left: 6px; top: 50%; width: 5px; height: 5px; margin-top: -2.5px; border-radius: 50%; background: var(--c); }
.tag.primary { background: color-mix(in srgb, var(--c) 14%, #fff); border-color: color-mix(in srgb, var(--c) 40%, var(--line)); font-weight: 600; }
.files { display: flex; flex-wrap: wrap; gap: 4px 10px; font: 11px var(--mono); }
.files a { color: var(--accent); text-decoration: none; background: linear-gradient(currentColor, currentColor) left bottom / 0 1px no-repeat, linear-gradient(var(--line-2), var(--line-2)) left bottom / 100% 1px no-repeat; padding-bottom: 1px; transition: background-size var(--m-out) var(--ease); }
.files a:hover { background-size: 100% 1px, 100% 1px; }
details { font-size: 12px; border-top: 1px solid var(--line); padding-top: 5px; }
summary { cursor: pointer; color: var(--muted); font: 500 10.5px var(--mono); }
details ul { list-style: none; margin-top: 8px; display: grid; gap: 6px; }
details li b { font: 600 11px var(--mono); margin-right: 6px; }
details li small { display: block; color: var(--muted); font: 11px var(--mono); }
details li.arch { color: var(--muted); font: 11px var(--mono); }
.empty { color: var(--muted); font-size: 13px; border: 1px dashed var(--line-2); border-radius: var(--r); padding: 14px 16px; margin-top: 18px; }
.empty[hidden] { display: none; }
footer { margin: 36px 0 28px; color: var(--muted); font-size: 12px; }

/* ideas workbook */
.wb { display: flex; flex-direction: column; height: calc(100dvh - var(--bar-h) - 24px); min-height: 420px; margin-top: 12px; border: 1px solid var(--line-2); border-radius: var(--r); background: var(--paper); overflow: hidden; }
.wb-tools { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 8px 10px; border-bottom: 1px solid var(--line); }
.wb-tools .sp { flex: 1; }
.wb-status { font: 11.5px var(--mono); color: var(--muted); }
.wb-status.dirty { color: var(--amber); }
.wb-grid { flex: 1; overflow: auto; }
.wb table { border-collapse: separate; border-spacing: 0; width: 100%; min-width: 920px; table-layout: fixed; }
.wb th { position: sticky; top: 0; z-index: 2; background: var(--sheet); text-align: left; font: 600 11px var(--mono); letter-spacing: .04em; text-transform: uppercase; color: var(--muted); padding: 7px 10px; border-bottom: 1px solid var(--line-2); border-right: 1px solid var(--line); user-select: none; white-space: nowrap; }
.wb th.sortable { cursor: pointer; }
.wb th.sortable:hover { color: var(--ink); }
.wb th .arr { margin-left: 4px; color: var(--accent); }
.wb td { position: relative; vertical-align: top; padding: 0; border-bottom: 1px solid var(--line); border-right: 1px solid var(--line); }
.wb td.n { text-align: center; font: 11px var(--mono); color: var(--muted); background: var(--sheet); padding-top: 11px; }
.wb tr:hover td:not(.n) { background: #fcfbf9; }
.cell { padding: 9px 10px; min-height: 38px; outline: none; white-space: pre-wrap; line-height: 1.4; }
.cell:empty::before { content: attr(data-ph); color: #a8a39a; }
.cell:focus, .wb td select:focus, .also-btn:focus-visible { outline: none; box-shadow: inset 0 0 0 2px var(--accent); background: #fff; }
.wb tr.bad .c-title .cell { box-shadow: inset 0 0 0 1px var(--danger); }
.wb td select { appearance: none; width: 100%; height: 100%; min-height: 38px; border: 0; background: transparent url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M1 1l4 4 4-4' fill='none' stroke='%236b6760' stroke-width='1.5'/%3E%3C/svg%3E") right 9px center no-repeat; padding: 9px 24px 9px 26px; cursor: pointer; }
.wb td.dot::before { content: ""; position: absolute; left: 10px; top: 16px; width: 8px; height: 8px; border-radius: 50%; background: var(--c); pointer-events: none; }
.also-btn { display: flex; flex-wrap: wrap; gap: 3px 10px; width: 100%; min-height: 38px; padding: 9px 10px; border: 0; background: transparent; cursor: pointer; text-align: left; font-size: 12.5px; }
.also-btn .dim { color: #a8a39a; }
.dotname { position: relative; padding-left: 12px; white-space: nowrap; }
.dotname::before { content: ""; position: absolute; left: 0; top: 50%; width: 7px; height: 7px; margin-top: -3.5px; border-radius: 50%; background: var(--c); }
.x { width: 100%; height: 38px; border: 0; background: none; color: #a8a39a; font-size: 17px; cursor: pointer; transition: color var(--m-in) var(--ease), background-color var(--m-in) var(--ease); }
.x:hover { color: var(--danger); background: #fbeeea; }
.addrow td { padding: 0; }
.addrow button { width: 100%; padding: 10px 12px; border: 0; background: none; text-align: left; color: var(--muted); font-weight: 600; cursor: pointer; transition: color var(--m-in) var(--ease), background-color var(--m-in) var(--ease); }
.addrow button:hover { color: var(--ink); background: #fcfbf9; }
.sheets { display: flex; align-items: stretch; gap: 0; background: var(--sheet); border-top: 1px solid var(--line-2); }
.sheet { position: relative; display: flex; align-items: center; gap: 7px; padding: 9px 16px; border: 0; border-right: 1px solid var(--line-2); background: none; cursor: pointer; font-weight: 600; font-size: 12.5px; color: var(--muted); transition: color var(--m-in) var(--ease), background-color var(--m-in) var(--ease); }
.sheet i { width: 8px; height: 8px; border-radius: 50%; background: var(--c, var(--ink)); }
.sheet b { font: 500 11px var(--mono); }
.sheet:hover { color: var(--ink); background: #efece5; }
.sheet[aria-selected="true"] { background: var(--paper); color: var(--ink); box-shadow: inset 0 2px 0 var(--c, var(--ink)); }
.sheets .hint { margin-left: auto; align-self: center; padding: 0 14px; font: 11px var(--mono); color: var(--muted); }
#pop { position: fixed; z-index: 60; min-width: 200px; padding: 6px; background: var(--paper); border: 1px solid var(--line-2); border-radius: var(--r); box-shadow: 0 8px 24px rgba(29, 29, 27, .14); }
#pop[hidden] { display: none; }
#pop label { display: flex; align-items: center; gap: 8px; padding: 5px 8px; border-radius: 4px; cursor: pointer; font-size: 13px; }
#pop label:hover { background: var(--sheet); }
#pop input { accent-color: var(--accent); }
.toast { position: fixed; left: 50%; bottom: 22px; transform: translateX(-50%); z-index: 70; display: flex; gap: 14px; align-items: center; padding: 9px 14px; background: var(--ink); color: #fff; border-radius: var(--r); font-size: 13px; box-shadow: 0 8px 24px rgba(0, 0, 0, .25); }
.toast[hidden] { display: none; }
.toast button { background: none; border: 0; color: #fff; font-weight: 700; text-decoration: underline; cursor: pointer; }
dialog { margin: auto; padding: 18px; width: min(560px, 92vw); border: 1px solid var(--line-2); border-radius: 10px; box-shadow: 0 16px 48px rgba(0, 0, 0, .22); }
dialog::backdrop { background: rgba(29, 29, 27, .35); }
dialog h3 { font-size: 15px; margin-bottom: 6px; }
dialog p { color: var(--muted); font-size: 12.5px; margin-bottom: 10px; }
dialog textarea { width: 100%; height: 180px; padding: 8px 10px; border: 1px solid var(--line-2); border-radius: var(--r); font: 12px var(--mono); resize: vertical; }
dialog .row { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
@media (max-width: 720px) { .wrap { padding: 0 14px; } .stats { display: none; } input.field { width: 150px; } .grid { grid-template-columns: repeat(2, 1fr); } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { transition-property: color, background-color, border-color, opacity !important; transition-duration: 1ms !important; } .card:hover, .chip:hover, .btn:hover { transform: none; } }
"""

JS = r"""
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

/* tabs */
const tabs = $$('.tab');
function show(id, remember) {
  tabs.forEach(t => t.setAttribute('aria-selected', String(t.dataset.panel === id)));
  $$('.panel').forEach(p => { p.hidden = p.id !== id; });
  if (remember) { try { history.replaceState(null, '', '#tab-' + id); } catch (_) {} }
}
tabs.forEach(t => t.addEventListener('click', () => show(t.dataset.panel, true)));
const start = location.hash.replace('#tab-', '');
show(tabs.some(t => t.dataset.panel === start) ? start : tabs[0].dataset.panel, false);

/* catalogue filters: type, progress, topic and a text search, combined */
(() => {
  const panel = $('#catalogue');
  const state = { cat: 'all', type: 'all', progress: 'all', q: '' };
  const apply = () => {
    $$('.item', panel).forEach(i => {
      const ok = (state.cat === 'all' || i.dataset.cats.split(' ').includes(state.cat))
        && (state.type === 'all' || i.dataset.types === state.type)
        && (state.progress === 'all' || i.dataset.progress.split(' ').includes(state.progress))
        && (!state.q || i.dataset.q.includes(state.q));
      i.classList.toggle('hide', !ok);
    });
    $('.nomatch', panel).hidden = !!$('.item:not(.hide)', panel);
  };
  [['cat', '[data-cat]'], ['type', '[data-type]'], ['progress', '[data-progress]']].forEach(([key, sel]) => {
    const chips = $$('.chip' + sel, panel);
    chips.forEach(chip => chip.addEventListener('click', () => {
      state[key] = chip.dataset[key];
      chips.forEach(c => c.classList.toggle('on', c === chip));
      apply();
    }));
  });
  const tiles = $('#tiles'), orig = $$('.item', tiles);
  const byTitle = (a, b) => a.dataset.title.localeCompare(b.dataset.title);
  const keys = {
    topic: (a, b) => a.dataset.topic - b.dataset.topic || byTitle(a, b),
    title: byTitle,
    'len-asc': (a, b) => a.dataset.len - b.dataset.len || byTitle(a, b),
    'len-desc': (a, b) => b.dataset.len - a.dataset.len || byTitle(a, b),
    prog: (a, b) => a.dataset.prog - b.dataset.prog || byTitle(a, b),
  };
  $('#sort').addEventListener('change', ev => { tiles.append(...[...orig].sort(keys[ev.target.value])); });
  $('.search', panel).addEventListener('input', ev => { state.q = ev.target.value.trim().toLowerCase(); apply(); });
})();

/* ideas workbook: an editable sheet, kept in this browser, exported back to docs/project-ideas.md */
(() => {
  const seed = JSON.parse($('#ideas-seed').textContent);
  const cats = seed.categories, types = seed.types;
  const catById = Object.fromEntries(cats.map(c => [c.id, c]));
  const typeById = Object.fromEntries(types.map(t => [t.id, t]));
  const catIdx = id => cats.findIndex(c => c.id === id);
  const typeIdx = id => types.findIndex(t => t.id === id);
  const KEY = 'motionlab.ideas.' + seed.hash;   // a rebuilt page with a changed ideas file starts from that file
  let storageOk = true;
  const read = () => { try { const t = localStorage.getItem(KEY); return t ? JSON.parse(t) : null; } catch (_) { storageOk = false; return null; } };
  let saveTimer = 0;
  const save = () => { clearTimeout(saveTimer); saveTimer = setTimeout(() => { try { localStorage.setItem(KEY, JSON.stringify(rows)); } catch (_) { storageOk = false; status(); } }, 200); };
  let rows = read() || seed.ideas.map(x => ({ ...x, also: [...x.also] }));
  let uid = 0;
  const newId = () => 'n' + Date.now().toString(36) + (uid++);
  let sheet = 'all', topic = 'all', q = '', sort = { key: null, dir: 1 };
  const root = $('#ideas'), tbody = $('#wb-body'), tabsEl = $('#sheets');

  function el(tag, props = {}, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
      if (k === 'class') n.className = v; else if (k === 'text') n.textContent = v;
      else if (k.startsWith('on')) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v);
    }
    kids.forEach(c => n.append(c));
    return n;
  }

  /* which rows, in what order */
  const visible = () => rows.filter(r =>
    (sheet === 'all' || r.type === sheet) &&
    (topic === 'all' || r.topic === topic || r.also.includes(topic)) &&
    (!q || (r.title + ' ' + r.pitch + ' ' + catById[r.topic].name).toLowerCase().includes(q)));
  function ordered(list, lastId) {
    const base = new Map(rows.map((r, i) => [r.id, i]));
    const cmp = (a, b) => {
      if (sort.key) {
        const f = sort.key;
        const va = f === 'topic' ? catIdx(a.topic) : f === 'type' ? typeIdx(a.type) : a[f].toLowerCase();
        const vb = f === 'topic' ? catIdx(b.topic) : f === 'type' ? typeIdx(b.type) : b[f].toLowerCase();
        if (va < vb) return -sort.dir; if (va > vb) return sort.dir;
      } else {
        const d = (sheet === 'all' ? typeIdx(a.type) - typeIdx(b.type) : 0) || catIdx(a.topic) - catIdx(b.topic);
        if (d) return d;
      }
      return base.get(a.id) - base.get(b.id);
    };
    const rest = list.filter(r => r.id !== lastId).sort(cmp);
    const last = list.find(r => r.id === lastId);
    return last ? [...rest, last] : rest;
  }

  /* cells */
  function textCell(tr, r, f, label, ph) {
    const d = el('div', { class: 'cell', contenteditable: 'plaintext-only', role: 'textbox', 'aria-label': label, 'data-f': f, 'data-ph': ph, spellcheck: 'true' });
    d.textContent = r[f];
    d.addEventListener('input', () => { r[f] = d.textContent.replace(/\s*\n+\s*/g, ' '); tr.classList.toggle('bad', !r.title.trim()); changed(); });
    d.addEventListener('paste', ev => { ev.preventDefault(); document.execCommand('insertText', false, (ev.clipboardData.getData('text/plain') || '').replace(/\s*\n+\s*/g, ' ')); });
    d.addEventListener('keydown', ev => {
      if (ev.key === 'Enter') { ev.preventDefault(); const next = tr.nextElementSibling && $('.cell[data-f="' + f + '"]', tr.nextElementSibling); next ? next.focus() : d.blur(); }
      if (ev.key === 'Escape') { d.textContent = r[f]; d.blur(); }
    });
    return d;
  }
  function selectCell(td, r, f, options, label) {
    const s = el('select', { 'aria-label': label });
    options.forEach(o => s.append(el('option', { value: o.id, text: o.name })));
    s.value = r[f];
    const paint = () => td.style.setProperty('--c', (f === 'type' ? typeById : catById)[r[f]].color);
    paint();
    s.addEventListener('change', () => { r[f] = s.value; if (f === 'topic') r.also = r.also.filter(a => a !== r.topic); paint(); if (f === 'topic') td.parentElement._paintAlso(); changed(); });
    td.append(s);
  }
  const pop = $('#pop');
  function closePop() { pop.hidden = true; pop._for = null; }
  function openPop(r, btn, paint) {
    if (pop._for === r.id) return closePop();
    pop.replaceChildren(...cats.filter(c => c.id !== r.topic).map(c => {
      const cb = el('input', { type: 'checkbox' }); cb.checked = r.also.includes(c.id);
      cb.addEventListener('change', () => { r.also = cats.map(x => x.id).filter(id => id !== r.topic && (id === c.id ? cb.checked : r.also.includes(id))); paint(); changed(); });
      return el('label', {}, cb, el('span', { class: 'dotname', style: '--c:' + c.color, text: c.name }));
    }));
    const b = btn.getBoundingClientRect();
    pop.hidden = false; pop._for = r.id;
    pop.style.left = Math.min(b.left, innerWidth - pop.offsetWidth - 8) + 'px';
    pop.style.top = Math.min(b.bottom + 2, innerHeight - pop.offsetHeight - 8) + 'px';
  }
  document.addEventListener('mousedown', ev => { if (!pop.hidden && !pop.contains(ev.target) && !ev.target.closest('.also-btn')) closePop(); });
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape') closePop(); });
  $('.wb-grid').addEventListener('scroll', closePop);

  function rowEl(r) {
    const tr = el('tr', { 'data-id': r.id });
    tr.classList.toggle('bad', !r.title.trim());
    const tdN = el('td', { class: 'n' });
    const tdTitle = el('td', { class: 'c-title' }); tdTitle.append(textCell(tr, r, 'title', 'Idea title', 'Idea title'));
    const tdPitch = el('td'); tdPitch.append(textCell(tr, r, 'pitch', 'One-line pitch', 'One-line pitch'));
    const tdTopic = el('td', { class: 'dot' }); selectCell(tdTopic, r, 'topic', cats, 'Topic');
    const tdType = el('td', { class: 'dot' }); selectCell(tdType, r, 'type', types.map(t => ({ id: t.id, name: t.short + ' · ' + t.nominal, color: t.color })), 'Video length');
    const tdAlso = el('td');
    const btn = el('button', { class: 'also-btn', type: 'button', 'aria-haspopup': 'true', 'aria-label': 'Secondary topics' });
    const paint = () => {
      btn.replaceChildren(...(r.also.length ? r.also.map(a => el('span', { class: 'dotname', style: '--c:' + catById[a].color, text: catById[a].name })) : [el('span', { class: 'dim', text: 'none' })]));
    };
    paint(); tr._paintAlso = () => { paint(); if (pop._for === r.id) closePop(); };
    btn.addEventListener('click', () => openPop(r, btn, paint));
    tdAlso.append(btn);
    const tdX = el('td'); tdX.append(el('button', { class: 'x', type: 'button', 'aria-label': 'Delete idea', title: 'Delete this idea', text: '×', onclick: () => remove(r.id) }));
    tr.append(tdN, tdTitle, tdPitch, tdTopic, tdType, tdAlso, tdX);
    return tr;
  }

  function render(lastId) {
    closePop();
    const list = ordered(visible(), lastId);
    tbody.replaceChildren(...list.map(rowEl));
    const add = el('tr', { class: 'addrow' }, el('td', { colspan: 7 }, el('button', { type: 'button', text: '+ Add idea', onclick: () => addRow() })));
    tbody.append(add);
    renumber(); counts();
    $$('th.sortable', root).forEach(th => { const a = $('.arr', th); a.textContent = sort.key === th.dataset.sort ? (sort.dir > 0 ? '▲' : '▼') : ''; });
  }
  const renumber = () => $$('tr[data-id] td.n', tbody).forEach((td, i) => { td.textContent = i + 1; });

  function counts() {
    const n = t => rows.filter(r => t === 'all' || r.type === t).length;
    $$('.sheet', tabsEl).forEach(b => { $('b', b).textContent = n(b.dataset.sheet); b.setAttribute('aria-selected', String(b.dataset.sheet === sheet)); });
    const tab = $('.tab[data-panel="ideas"] span'); if (tab) tab.textContent = rows.length;
    status();
  }
  function status() {
    const seedBy = new Map(seed.ideas.map(x => [x.id, x]));
    const sig = r => [r.title, r.pitch, r.topic, r.type, r.also.join(',')].join('|');
    const added = rows.filter(r => !seedBy.has(r.id)).length;
    const removed = seed.ideas.filter(x => !rows.some(r => r.id === x.id)).length;
    const edited = rows.filter(r => seedBy.has(r.id) && sig(r) !== sig(seedBy.get(r.id))).length;
    const el_ = $('#wb-status');
    const parts = [added && '+' + added + ' added', edited && edited + ' edited', removed && removed + ' removed'].filter(Boolean);
    el_.classList.toggle('dirty', parts.length > 0);
    el_.textContent = (parts.length ? parts.join(' · ') + ' · not in the workspace yet: Download .md and save it over docs/project-ideas.md' : 'Matches docs/project-ideas.md')
      + (storageOk ? '' : ' · this browser will not keep edits across reloads, so download before closing');
  }
  const changed = () => { save(); counts(); };

  /* add, delete, undo */
  function addRow(preset = {}) {
    const r = { id: newId(), title: '', pitch: '', topic: topic !== 'all' ? topic : 'technology', also: [], type: sheet !== 'all' ? sheet : 'reel', ...preset };
    rows.push(r); save(); render(r.id);
    const tr = $('tr[data-id="' + r.id + '"]', tbody);
    if (tr) { tr.scrollIntoView({ block: 'nearest' }); $('.cell', tr).focus(); }
    return r;
  }
  let toastTimer = 0;
  function toast(msg, undo) {
    const t = $('#toast'); t.replaceChildren(el('span', { text: msg }), ...(undo ? [el('button', { type: 'button', text: 'Undo', onclick: () => { undo(); t.hidden = true; } })] : []));
    t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 7000);
  }
  function remove(id) {
    const i = rows.findIndex(r => r.id === id); if (i < 0) return;
    const [r] = rows.splice(i, 1);
    const tr = $('tr[data-id="' + id + '"]', tbody); if (tr) tr.remove();
    renumber(); changed();
    toast('Deleted "' + (r.title.trim() || 'untitled idea') + '"', () => { rows.splice(i, 0, r); save(); render(); });
  }

  /* export and import */
  const named = id => (typeById[id] || {}).name;
  function exportMd() {
    const by = id => rows.filter(r => r.topic === id && r.title.trim());
    const body = cats.filter(c => by(c.id).length).map(c => '## ' + c.id + '\n' + by(c.id).map(r =>
      '- **' + r.title.replace(/\*\*/g, '*').trim() + '** — ' + (r.pitch.replace(/\s+/g, ' ').trim() || 'TODO: one-line pitch')
      + (r.also.length ? ' (also: ' + r.also.join(', ') + ')' : '') + ' [' + r.type + ']').join('\n')).join('\n\n');
    return seed.preamble.trimEnd() + '\n\n' + body + '\n';
  }
  const grid = () => [['Idea', 'Pitch', 'Topic', 'Length', 'Also']].concat(rows.filter(r => r.title.trim()).map(r =>
    [r.title, r.pitch, catById[r.topic].name, named(r.type), r.also.map(a => catById[a].name).join(', ')]));
  const csv = () => grid().map(row => row.map(c => '"' + String(c).replace(/"/g, '""') + '"').join(',')).join('\r\n') + '\r\n';
  function download(name, text, mime) {
    const a = el('a', { href: URL.createObjectURL(new Blob([text], { type: mime })), download: name });
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  async function copy(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (_) {
      const ta = el('textarea', { style: 'position:fixed;opacity:0' }); ta.value = text; document.body.append(ta); ta.select();
      const ok = document.execCommand('copy'); ta.remove(); return ok;
    }
  }
  const norm = s => s.toLowerCase().replace(/[^a-z0-9]+/g, '');
  const findCat = s => cats.find(c => norm(c.id) === norm(s) || norm(c.name) === norm(s) || norm(c.name).startsWith(norm(s)) && norm(s).length > 3);
  const findType = s => types.find(t => norm(t.id) === norm(s) || norm(t.name) === norm(s) || norm(t.short) === norm(s)) || (/youtube|long.?form/i.test(s) ? typeById.youtube : /long/i.test(s) ? typeById['long-reel'] : /reel|short/i.test(s) ? typeById.reel : null);
  function pasteRows(text) {
    const lines = text.split(/\r?\n/).filter(l => l.trim());
    if (lines.length && /^idea\b/i.test(lines[0].split('\t')[0])) lines.shift();
    let n = 0;
    lines.forEach(l => {
      const [title = '', pitch = '', t = '', len = '', also = ''] = l.split('\t').map(s => s.trim());
      if (!title) return;
      const c = findCat(t), ty = findType(len);
      rows.push({ id: newId(), title, pitch, topic: c ? c.id : (topic !== 'all' ? topic : 'technology'), type: ty ? ty.id : (sheet !== 'all' ? sheet : 'reel'),
        also: also.split(/[,;]/).map(s => findCat(s.trim())).filter(x => x && (!c || x.id !== c.id)).map(x => x.id) });
      n++;
    });
    save(); render(); toast(n ? 'Added ' + n + ' idea' + (n === 1 ? '' : 's') + ' from the pasted rows' : 'No rows found: paste tab-separated columns Idea, Pitch, Topic, Length, Also');
  }

  /* wiring */
  $$('.sheet', tabsEl).forEach(b => b.addEventListener('click', () => { sheet = b.dataset.sheet; render(); }));
  $('#wb-topic').addEventListener('change', ev => { topic = ev.target.value; render(); });
  $('#wb-q').addEventListener('input', ev => { q = ev.target.value.trim().toLowerCase(); render(); });
  $$('th.sortable', root).forEach(th => th.addEventListener('click', () => {
    const k = th.dataset.sort; sort = sort.key === k ? (sort.dir > 0 ? { key: k, dir: -1 } : { key: null, dir: 1 }) : { key: k, dir: 1 }; render();
  }));
  $('#wb-add').addEventListener('click', () => addRow());
  $('#wb-md').addEventListener('click', () => { download('project-ideas.md', exportMd(), 'text/markdown'); toast('Saved project-ideas.md: replace docs/project-ideas.md with it, then rebuild the catalogue'); });
  $('#wb-csv').addEventListener('click', () => download('project-ideas.csv', csv(), 'text/csv'));
  $('#wb-copy').addEventListener('click', async () => { const ok = await copy(grid().map(r => r.join('\t')).join('\n')); toast(ok ? 'Copied the sheet: paste it into Excel or Google Sheets' : 'Copy was blocked by the browser'); });
  const dlg = $('#paste');
  $('#wb-paste').addEventListener('click', () => { $('textarea', dlg).value = ''; dlg.showModal(); $('textarea', dlg).focus(); });
  $('#paste-go').addEventListener('click', () => { pasteRows($('textarea', dlg).value); dlg.close(); });
  $('#paste-cancel').addEventListener('click', () => dlg.close());
  $('#wb-reset').addEventListener('click', () => {
    if (!confirm('Discard every edit made in this browser and go back to docs/project-ideas.md?')) return;
    rows = seed.ideas.map(x => ({ ...x, also: [...x.also] })); try { localStorage.removeItem(KEY); } catch (_) {} render(); toast('Back to docs/project-ideas.md');
  });
  window.__ideas = { rows: () => rows, exportMd };   // handle for tests
  render();
})();
"""


def type_label(t):
    return f"{t['name']} ({t['nominal']})"


def build():
    categories = read_categories()
    cat_by_id = {c["id"]: c for c in categories}
    types = read_video_types()
    type_by_id = {t["id"]: t for t in types}
    projects = read_projects()
    for p in projects:
        if not p["categories"]:
            sys.exit(f"{p['slug']}: no categories in brief.json and none in FALLBACK_CATEGORIES")
        for c in p["categories"]:
            if c not in cat_by_id:
                sys.exit(f"{p['slug']}: unknown category '{c}'")
    projects.sort(key=lambda p: (list(cat_by_id).index(p["categories"][0]), p["latest"]["title"].lower()))
    preamble, ideas = read_ideas(set(cat_by_id), {t["id"] for t in types})

    p_counts = counts_for(projects)
    t_counts, g_counts = {}, {}
    for p in projects:
        p["type"], p["type_derived"] = type_for(p["latest"], types)
        t_counts[p["type"]] = t_counts.get(p["type"], 0) + 1
        for key in (p["latest"]["progress"], "rerender" if p["latest"]["rerender"] else None):
            if key:
                g_counts[key] = g_counts.get(key, 0) + 1

    def group(label, chips_html):
        return f'<div class="fgroup"><span class="flabel">{label}</span>{chips_html}</div>'

    def strip_wrapper(html_):  # chip rows come wrapped in a div; the toolbar supplies its own
        return re.sub(r'^<div class="chips"[^>]*>|</div>$', "", html_)

    catalogue = (
        '<div class="tools">'
        '<input class="field search" type="search" placeholder="Search projects" aria-label="Search projects">'
        + '<select class="field" id="sort" aria-label="Sort projects">'
          '<option value="topic">Sort: topic</option><option value="title">Sort: A to Z</option>'
          '<option value="len-asc">Sort: shortest first</option><option value="len-desc">Sort: longest first</option>'
          '<option value="prog">Sort: progress</option></select>'
        + group("Type", strip_wrapper(type_chips(types, t_counts, len(projects))))
        + group("Progress", strip_wrapper(progress_chips(g_counts, len(projects))))
        + group("Topic", strip_wrapper(chips(categories, p_counts, len(projects))))
        + '</div>'
        + '<p class="empty nomatch" hidden>No projects match these filters.</p>'
        + '<div class="grid" id="tiles">' + "".join(project_card(p, cat_by_id, type_by_id) for p in projects) + '</div>'
        + '<footer>Poster = the last non-black frame of the film. Type: the brief\'s video_type, else by the film\'s length (* = by length). '
          'Generated by scripts/build-catalogue.py.</footer>'
    )

    seed = {
        "categories": [{"id": c["id"], "name": c["name"], "color": COLORS[c["id"]]} for c in categories],
        "types": [{"id": t["id"], "name": t["name"], "short": t["short"], "nominal": t["nominal"], "color": TYPE_COLORS[t["id"]]} for t in types],
        "ideas": ideas,
        "preamble": preamble,
        "hash": hashlib.sha1(IDEAS.read_bytes()).hexdigest()[:8],
    }
    seed_json = json.dumps(seed, ensure_ascii=False).replace("</", "<\\/")
    sheet_tabs = (
        '<button class="sheet" role="tab" data-sheet="all" aria-selected="true">All ideas <b>0</b></button>'
        + "".join(
            f'<button class="sheet" role="tab" data-sheet="{t["id"]}" style="--c:{TYPE_COLORS[t["id"]]}" title="{e(t["format"])}, {e(t["nominal"])}, +-{t["margin"]:g} s">'
            f'<i></i>{e(t["name"])} <b>0</b></button>' for t in types)
        + '<span class="hint">Click a cell to edit. Enter moves down, Esc undoes. Sheets split the ideas by video length.</span>'
    )
    topic_opts = '<option value="all">All topics</option>' + "".join(f'<option value="{c["id"]}">{e(c["name"])}</option>' for c in categories)
    workbook = f"""
    <div class="wb">
      <div class="wb-tools">
        <button class="btn primary" id="wb-add" type="button">+ Add idea</button>
        <button class="btn" id="wb-paste" type="button" title="Paste rows copied from Excel or Google Sheets">Paste rows</button>
        <select class="field" id="wb-topic" aria-label="Filter by topic">{topic_opts}</select>
        <input class="field" id="wb-q" type="search" placeholder="Search ideas" aria-label="Search ideas">
        <span class="sp"></span>
        <span class="wb-status" id="wb-status"></span>
        <button class="btn" id="wb-copy" type="button" title="Copy the sheet as tab-separated text">Copy for Excel</button>
        <button class="btn" id="wb-csv" type="button">Download .csv</button>
        <button class="btn" id="wb-md" type="button" title="Saves docs/project-ideas.md in its own format">Download .md</button>
        <button class="btn" id="wb-reset" type="button" title="Throw away this browser's edits">Reset</button>
      </div>
      <div class="wb-grid">
        <table>
          <colgroup><col style="width:46px"><col style="width:22%"><col><col style="width:210px"><col style="width:190px"><col style="width:190px"><col style="width:42px"></colgroup>
          <thead><tr><th>#</th><th class="sortable" data-sort="title">Idea<span class="arr"></span></th><th class="sortable" data-sort="pitch">Pitch<span class="arr"></span></th><th class="sortable" data-sort="topic">Topic<span class="arr"></span></th><th class="sortable" data-sort="type">Length<span class="arr"></span></th><th>Also in</th><th></th></tr></thead>
          <tbody id="wb-body"></tbody>
        </table>
      </div>
      <div class="sheets" id="sheets" role="tablist" aria-label="Sheets by video length">{sheet_tabs}</div>
    </div>
    <div id="pop" hidden role="dialog" aria-label="Secondary topics"></div>
    <div id="toast" class="toast" hidden role="status"></div>
    <dialog id="paste"><h3>Paste rows from Excel</h3>
      <p>Columns, tab-separated: Idea, Pitch, Topic, Length, Also. Topic and Length can be names or ids; blank ones use the current sheet and topic.</p>
      <textarea aria-label="Rows to paste" placeholder="Idea&#9;Pitch&#9;Topic&#9;Length&#9;Also"></textarea>
      <div class="row"><button class="btn" id="paste-cancel" type="button">Cancel</button><button class="btn primary" id="paste-go" type="button">Add rows</button></div>
    </dialog>"""

    stats = (f'<span><b>{len(projects)}</b>projects</span>'
             + "".join(f'<span><i style="--c:{TYPE_COLORS[t["id"]]}"></i><b>{t_counts.get(t["id"], 0)}</b>{e(t["short"])}</span>' for t in types))
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Motion Lab catalogue</title>
<style>{CSS}</style>
</head>
<body>
<header class="bar"><div class="wrap bar-in">
  <div class="brand">Motion Lab</div>
  <div class="tabs" role="tablist">
    <button class="tab" role="tab" data-panel="catalogue" aria-selected="true">Catalogue <span>{len(projects)}</span></button>
    <button class="tab" role="tab" data-panel="ideas" aria-selected="false">Ideas <span>{len(ideas)}</span></button>
  </div>
  <div class="stats">{stats}</div>
</div></header>
<main class="wrap">
  <div class="panel" id="catalogue" role="tabpanel">{catalogue}
  </div>
  <div class="panel" id="ideas" role="tabpanel" hidden>{workbook}
  </div>
</main>
<script type="application/json" id="ideas-seed">{seed_json}</script>
<script>{JS}</script>
</body>
</html>
"""
    TARGET.write_text(page)
    print(f"wrote {TARGET.relative_to(ROOT)}: {len(projects)} projects, {len(ideas)} ideas")


if __name__ == "__main__":
    build()
