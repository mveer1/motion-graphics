#!/usr/bin/env python3
"""Build out/catalogue.html: every project grouped by topic category, plus a tab that
shows the backlog in docs/project-ideas.md.

Reads projects/*/ (brief.json, project.json, renders), specs/categories.json and
docs/project-ideas.md. Writes one self-contained HTML file next to the delivered videos so
the relative video links work. Runs anywhere; it only reads files (ffprobe is optional and
used for the runtime of legacy projects that have no project.json).

    python3 scripts/build-catalogue.py
"""

import html
import json
import re
import subprocess
import sys
from pathlib import Path

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
    "news": "#7a3e8e",
    "storytelling": "#b5456b",
}


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
    rendered = final.exists()
    return {
        "name": folder.name,
        "title": brief.get("title") or proj.get("title") or research.get("title") or folder.name,
        "objective": brief.get("objective") or dossier.get("pedagogy", {}).get("core_thesis") or "",
        "categories": brief.get("categories") or [],
        "formats": formats or [],
        "duration": duration,
        "style": proj.get("style") or "",
        "rendered": rendered,
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


def read_categories():
    data = load_json(ROOT / "specs" / "categories.json")
    return data["categories"]


def read_ideas(valid_ids):
    ideas, current = [], None
    for n, line in enumerate(IDEAS.read_text().splitlines(), 1):
        if line.startswith("## "):
            current = line[3:].strip()
            if current not in valid_ids:
                sys.exit(f"{IDEAS.name}:{n}: unknown category '{current}' (see specs/categories.json)")
        elif line.startswith("- "):
            m = re.match(r"- \*\*(.+?)\*\* — (.+)$", line)
            if not m or not current:
                sys.exit(f"{IDEAS.name}:{n}: expected '- **Title** — pitch' under a '## category' heading")
            title, pitch = m.groups()
            also = re.search(r"\s*\(also: ([a-z, ]+)\)\s*$", pitch)
            extra = [c.strip() for c in also.group(1).split(",")] if also else []
            if also:
                pitch = pitch[: also.start()]
            for c in extra:
                if c not in valid_ids:
                    sys.exit(f"{IDEAS.name}:{n}: unknown category '{c}' in (also: ...)")
            ideas.append({"title": title, "pitch": pitch.strip(), "categories": [current] + extra})
    return ideas


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


def project_card(p, cat_by_id):
    v = p["latest"]
    cats = p["categories"]
    attrs = f'data-cats="{" ".join(cats)}" style="--c:{COLORS[cats[0]]}"'
    meta = [runtime(v["duration"]), " · ".join(v["formats"]), v["style"]]
    meta_html = "".join(f"<span>{e(m)}</span>" for m in meta if m)
    status = "Rendered" if v["rendered"] else "In progress"
    status_cls = "status ok" if v["rendered"] else "status"
    if p["note"]:
        status, status_cls = "Benchmark", "status bench"
    tags = "".join(tag(cat_by_id, c, i == 0) for i, c in enumerate(cats))
    videos = "".join(f'<a href="{e(href)}">{e(label)}</a>' for label, href in p["videos"])
    videos_html = f'<div class="files"><span>Watch</span>{videos}</div>' if videos else ""
    obj = v["objective"] or p["note"]
    versions_html = ""
    if len(p["versions"]) > 1 or p["archived"]:
        rows = "".join(
            f'<li><b>{e(x["name"])}</b> {e(x["title"])}'
            f'<small>{e(" · ".join(s for s in [runtime(x["duration"]), x["style"]] if s))}</small></li>'
            for x in p["versions"]
        )
        arch = f'<li class="arch">+ {p["archived"]} archived</li>' if p["archived"] else ""
        versions_html = f'<details><summary>{len(p["versions"])} versions</summary><ul>{rows}{arch}</ul></details>'
    return f"""
      <article class="card item" {attrs}>
        <div class="card-head"><span class="{status_cls}">{status}</span><code>{e(p["slug"])}</code></div>
        <h3>{e(v["title"])}</h3>
        <p class="obj">{e(obj)}</p>
        <div class="meta">{meta_html}</div>
        <div class="tags">{tags}</div>
        {videos_html}
        {versions_html}
      </article>"""


def idea_card(i, cat_by_id):
    cats = i["categories"]
    tags = "".join(tag(cat_by_id, c, n == 0) for n, c in enumerate(cats))
    return f"""
      <article class="card idea item" data-cats="{" ".join(cats)}" style="--c:{COLORS[cats[0]]}">
        <h3>{e(i["title"])}</h3>
        <p class="obj">{e(i["pitch"])}</p>
        <div class="tags">{tags}</div>
      </article>"""


def chips(categories, counts, total):
    out = [f'<button class="chip on" data-cat="all">All <b>{total}</b></button>']
    for c in categories:
        if counts.get(c["id"]):
            out.append(
                f'<button class="chip" data-cat="{c["id"]}" style="--c:{COLORS[c["id"]]}">'
                f'{e(c["name"])} <b>{counts[c["id"]]}</b></button>'
            )
    return f'<div class="chips" role="group" aria-label="Filter by category">{"".join(out)}</div>'


def sections(categories, items, render, empty_msg):
    out = []
    for c in categories:
        mine = [x for x in items if x["categories"][0] == c["id"]]
        body = "".join(render(x) for x in mine) or f'<p class="empty">{e(empty_msg)}</p>'
        out.append(f"""
    <section class="group" data-group="{c["id"]}" style="--c:{COLORS[c["id"]]}">
      <header><h2><i></i>{e(c["name"])}</h2><p>{e(c["description"])}</p></header>
      <div class="grid">{body}</div>
    </section>""")
    return "".join(out)


def counts_for(items):
    counts = {}
    for x in items:
        for c in set(x["categories"]):
            counts[c] = counts.get(c, 0) + 1
    return counts


CSS = """
:root {
  --bg: #fbfbfa; --paper: #ffffff; --ink: #222222; --muted: #6b6760; --line: #e6e2da;
  --vermilion: #d9432b; --ultramarine: #2740c8; --emerald: #12805c;
  --font: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
  --mono: "SF Mono", Menlo, Consolas, monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { overflow-wrap: anywhere; background: var(--bg); color: var(--ink); font: 15px/1.5 var(--font); padding: 0 16px 64px; }
.wrap { max-width: 1180px; margin: 0 auto; }
.top { padding: 40px 0 8px; }
.eyebrow { font: 600 11px var(--mono); letter-spacing: .1em; text-transform: uppercase; color: var(--vermilion); }
h1 { font-size: clamp(28px, 5vw, 40px); letter-spacing: -.02em; margin: 6px 0 8px; }
.lead { color: var(--muted); max-width: 640px; }
.stats { display: flex; flex-wrap: wrap; gap: 8px 24px; margin-top: 18px; font-size: 13px; color: var(--muted); }
.stats b { color: var(--ink); font-size: 20px; margin-right: 4px; }
.tabs { display: flex; gap: 4px; margin: 28px 0 20px; border-bottom: 1px solid var(--line); }
.tab { font: 600 14px var(--font); padding: 10px 16px; border: 0; background: none; color: var(--muted);
  cursor: pointer; border-bottom: 3px solid transparent; margin-bottom: -1px; }
.tab:hover { color: var(--ink); }
.tab[aria-selected="true"] { color: var(--ink); border-bottom-color: var(--vermilion); }
.tab span { font: 500 12px var(--mono); color: var(--muted); margin-left: 6px; }
.panel[hidden] { display: none; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
.chip { font: 500 13px var(--font); padding: 6px 12px; border: 1px solid var(--line); border-radius: 99px;
  background: var(--paper); color: var(--ink); cursor: pointer; display: inline-flex; gap: 6px; align-items: center; }
.chip b { font: 500 11px var(--mono); color: var(--muted); }
.chip:hover { border-color: var(--ink); }
.chip.on { background: var(--ink); color: #fff; border-color: var(--ink); }
.chip.on b { color: #ddd; }
.chip:focus-visible, .tab:focus-visible, summary:focus-visible, a:focus-visible { outline: 2px solid var(--ultramarine); outline-offset: 2px; }
.group { margin-top: 36px; }
.group.hide { display: none; }
.group header { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 14px; margin-bottom: 14px; }
.group h2 { font-size: 20px; letter-spacing: -.01em; display: flex; align-items: center; gap: 10px; }
.group h2 i { width: 12px; height: 12px; border-radius: 50%; background: var(--c); display: inline-block; }
.group header p { color: var(--muted); font-size: 13px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.card { background: var(--paper); border: 1px solid var(--line); border-top: 4px solid var(--c);
  border-radius: 8px; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
.card.hide { display: none; }
.card-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.card code { font: 11px var(--mono); color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.status { font: 600 10px var(--mono); letter-spacing: .06em; text-transform: uppercase; padding: 2px 8px;
  border-radius: 99px; border: 1px solid var(--line); color: var(--muted); flex: none; }
.status.ok { color: var(--emerald); border-color: var(--emerald); }
.status.bench { color: var(--ultramarine); border-color: var(--ultramarine); }
.card h3 { font-size: 17px; line-height: 1.3; letter-spacing: -.01em; }
.obj { color: var(--muted); font-size: 13.5px; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
.idea .obj { -webkit-line-clamp: unset; display: block; }
.meta { display: flex; flex-wrap: wrap; gap: 4px 12px; font: 12px var(--mono); color: var(--ink); }
.tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: auto; }
.tag { font-size: 11.5px; padding: 2px 9px; border-radius: 99px; border: 1px solid var(--line); color: var(--ink); position: relative; padding-left: 20px; }
.tag::before { content: ""; position: absolute; left: 8px; top: 50%; width: 6px; height: 6px; margin-top: -3px; border-radius: 50%; background: var(--c); }
.tag.primary { background: #f5f3ef; font-weight: 600; }
.files { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; font-size: 12px; }
.files span { font: 600 10px var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.files a { color: var(--ultramarine); text-decoration: none; border-bottom: 1px solid currentColor; font-family: var(--mono); font-size: 11.5px; }
details { font-size: 13px; border-top: 1px solid var(--line); padding-top: 8px; }
summary { cursor: pointer; color: var(--muted); font: 500 12px var(--mono); }
details ul { list-style: none; margin-top: 8px; display: grid; gap: 6px; }
details li b { font: 600 11px var(--mono); margin-right: 6px; }
details li small { display: block; color: var(--muted); font: 11px var(--mono); }
details li.arch { color: var(--muted); font: 11px var(--mono); }
.empty { color: var(--muted); font-size: 13px; border: 1px dashed var(--line); border-radius: 8px; padding: 14px 16px; }
.note { margin: 6px 0 0; color: var(--muted); font-size: 13px; }
.note code { font: 12px var(--mono); background: #f5f3ef; padding: 1px 6px; border-radius: 4px; }
footer { margin-top: 56px; color: var(--muted); font-size: 12px; }
@media (max-width: 520px) { .grid { grid-template-columns: 1fr; } .tab { padding: 10px 10px; } }
"""

JS = """
const tabs = [...document.querySelectorAll('.tab')];
function show(id, remember) {
  tabs.forEach(t => t.setAttribute('aria-selected', String(t.dataset.panel === id)));
  document.querySelectorAll('.panel').forEach(p => { p.hidden = p.id !== id; });
  // '#tab-<id>' matches no element, so the browser never scrolls to it.
  if (remember) { try { history.replaceState(null, '', '#tab-' + id); } catch (_) {} }
}
tabs.forEach(t => t.addEventListener('click', () => show(t.dataset.panel, true)));
const start = location.hash.replace('#tab-', '');
show(tabs.some(t => t.dataset.panel === start) ? start : tabs[0].dataset.panel, false);

document.querySelectorAll('.panel').forEach(panel => {
  const chips = [...panel.querySelectorAll('.chip')];
  chips.forEach(chip => chip.addEventListener('click', () => {
    const cat = chip.dataset.cat;
    chips.forEach(c => c.classList.toggle('on', c === chip));
    panel.querySelectorAll('.item').forEach(i => {
      i.classList.toggle('hide', cat !== 'all' && !i.dataset.cats.split(' ').includes(cat));
    });
    panel.querySelectorAll('.group').forEach(g => {
      const visible = g.querySelector('.item:not(.hide)');
      g.classList.toggle('hide', cat !== 'all' ? !visible : false);
    });
  }));
});
"""


def build():
    categories = read_categories()
    cat_by_id = {c["id"]: c for c in categories}
    projects = read_projects()
    for p in projects:
        if not p["categories"]:
            sys.exit(f"{p['slug']}: no categories in brief.json and none in FALLBACK_CATEGORIES")
        for c in p["categories"]:
            if c not in cat_by_id:
                sys.exit(f"{p['slug']}: unknown category '{c}'")
    projects.sort(key=lambda p: p["latest"]["title"].lower())
    ideas = read_ideas(set(cat_by_id))

    p_counts, i_counts = counts_for(projects), counts_for(ideas)
    versions = sum(len(p["versions"]) + p["archived"] for p in projects)
    covered = sum(1 for c in categories if p_counts.get(c["id"]))

    catalogue = (
        chips(categories, p_counts, len(projects))
        + sections(categories, projects, lambda p: project_card(p, cat_by_id),
                   "No projects yet in this category. See the ideas tab.")
    )
    backlog = (
        '<p class="note">Read from <code>docs/project-ideas.md</code>. Edit that file and run '
        "<code>python3 scripts/build-catalogue.py</code> to refresh this tab.</p>"
        + chips(categories, i_counts, len(ideas))
        + sections(categories, ideas, lambda i: idea_card(i, cat_by_id), "No ideas yet in this category.")
    )
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Motion Lab Catalogue</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="eyebrow">Motion Lab</div>
    <h1>Project catalogue</h1>
    <p class="lead">Every project in <code>projects/</code>, grouped by its primary topic category, and the ideas queued up next. Filters also match a project's secondary categories.</p>
    <div class="stats">
      <div><b>{len(projects)}</b>projects</div>
      <div><b>{versions}</b>versions, including archived</div>
      <div><b>{covered}/{len(categories)}</b>categories covered</div>
      <div><b>{len(ideas)}</b>ideas queued</div>
    </div>
  </div>
  <div class="tabs" role="tablist">
    <button class="tab" role="tab" data-panel="catalogue" aria-selected="true">Catalogue<span>{len(projects)}</span></button>
    <button class="tab" role="tab" data-panel="ideas" aria-selected="false">Next ideas<span>{len(ideas)}</span></button>
  </div>
  <main>
    <div class="panel" id="catalogue" role="tabpanel">{catalogue}
    </div>
    <div class="panel" id="ideas" role="tabpanel" hidden>{backlog}
    </div>
  </main>
  <footer>Generated by scripts/build-catalogue.py from project folders and docs/project-ideas.md. Video links work when this file sits in out/ next to the renders.</footer>
</div>
<script>{JS}</script>
</body>
</html>
"""
    TARGET.write_text(page)
    print(f"wrote {TARGET.relative_to(ROOT)}: {len(projects)} projects, {len(ideas)} ideas")


if __name__ == "__main__":
    build()
