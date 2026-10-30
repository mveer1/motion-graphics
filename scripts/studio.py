#!/usr/bin/env python3
"""
scripts/studio.py
Project lifecycle CLI for the Motion Lab creative studio (stdlib + jsonschema).

Subcommands:
  new <slug> --template <id> [--title T] [--style S] [--formats a,b]   scaffold from templates/projects/<id>/
  sync <slug> [--force]          copy the canonical runtime (src/studio/) into projects/<slug>/src/_studio/
  formats <slug> [--size 1080p]  write per-format entry files (src/index.<format>.html) from src/index.html
  validate <slug> [--json]       schema + cross-reference + composition checks (exit 1 on errors)
  build <slug> [--dry-run]       render every format with HyperFrames, mux audio, run QA gates
  captions <slug>                approximate caption cues from audio/timeline.json (src/captions.js + .vtt)
  review <slug> [--init]         creative-review rubric (qa/creative-review.json): create or summarise
  status <slug>                  which lifecycle artefacts exist and what comes next

Projects without project.json are legacy technical explainers: `build` prints/runs the original
single-format plan (1280x720 landscape, index.html) so existing workflows keep working.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from html import escape as html_escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = REPO_ROOT / "projects"
RUNTIME_DIR = REPO_ROOT / "src" / "studio"
TEMPLATES_DIR = REPO_ROOT / "templates" / "projects"
SPECS_DIR = REPO_ROOT / "specs"
PRESETS_FILE = SPECS_DIR / "format-presets.json"
RUNTIME_DIRNAME = "_studio"
LOCK_NAME = "studio.lock.json"
QA_SCRIPT = REPO_ROOT / ".agents" / "skills" / "video-assembler" / "scripts" / "run-qa-gates.sh"

# Families HyperFrames bundles and resolves by name (upstream docs: skills/hyperframes/references/format.md).
HF_BUNDLED_FONTS = {
    "inter", "montserrat", "outfit", "nunito", "oswald", "league gothic", "archivo black", "space mono",
    "ibm plex mono", "jetbrains mono", "eb garamond", "playfair display", "source code pro", "noto sans jp",
    "roboto", "open sans", "lato", "poppins",
}
GENERIC_FONTS = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "inherit", "initial", "unset"}
HF_SWAPPED_SYSTEM_FONTS = {"helvetica", "helvetica neue", "arial", "times", "times new roman", "menlo", "courier", "courier new"}

BANNED_PATTERNS = [
    (r"Math\.random\s*\(", "error", "Math.random() breaks deterministic rendering; use Studio.rng(seed)."),
    (r"Date\.now\s*\(|new\s+Date\s*\(|performance\.now\s*\(", "error", "Wall-clock time breaks seeking; derive everything from the timeline."),
    (r"requestAnimationFrame\s*\(|setInterval\s*\(|setTimeout\s*\(", "error", "Timers and rAF are not driven by the HyperFrames seek."),
    (r"repeat\s*:\s*-1", "error", "Infinite repeats never finish; compute a finite repeat count (Studio.cycles)."),
    (r"\.play\s*\(", "error", "Never play timelines or media; HyperFrames owns the playhead."),
    (r"gsap@3/|gsap@latest|gsap/latest", "warning", "Pin GSAP to an exact version (catalogue: gsap 3.12.5)."),
]

FORMAT_IDS = ("landscape", "portrait", "square")
CREATIVE_CRITERIA = [
    ("visual_hierarchy", "One clear focal point per beat; reading order is obvious."),
    ("typography", "Type roles are consistent; sizes respect the floor; no orphans or awkward breaks."),
    ("composition", "Layouts are intentional in every format (not stretched or cropped landscape)."),
    ("pacing", "Holds match reading time; rhythm varies; nothing drags or rushes."),
    ("readability", "All text is legible at delivery size with sufficient contrast."),
    ("colour_and_style", "Palette and texture follow the chosen style system and direction."),
    ("transitions", "Each transition carries meaning or continuity; none are decorative filler."),
    ("visual_language", "Motion vocabulary is consistent across scenes."),
    ("no_filler_motion", "No repetitive looping filler or motion without purpose."),
    ("no_dead_time", "No unintended static stretches; intentional holds are marked."),
    ("no_collisions", "No accidental overlaps, clipping or safe-area violations."),
    ("arc", "Clear opening, progression and ending; the last frame holds long enough."),
]


# --------------------------------------------------------------------------- helpers
class Report:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def note(self, msg: str) -> None:
        self.info.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings, "info": self.info}


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def sha256_file(path: Path) -> str:
    # Hash with LF line endings so Windows checkouts (autocrlf) and macOS agree.
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def rel_path(p: Path) -> str:
    """Workspace-relative POSIX path inside the repository, absolute POSIX path otherwise."""
    p = p.resolve()
    try:
        return p.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def project_dir(slug_or_path: str) -> Path:
    candidate = PROJECTS_DIR / slug_or_path
    if candidate.is_dir():
        return candidate
    p = Path(slug_or_path)
    if p.is_dir():
        return p.resolve()
    raise SystemExit(f"Error: project '{slug_or_path}' not found under projects/.")


def presets() -> Dict[str, Any]:
    return load_json(PRESETS_FILE)


def runtime_version() -> str:
    text = (RUNTIME_DIR / "studio-core.js").read_text(encoding="utf-8")
    m = re.search(r"Studio\.version\s*=\s*'([^']+)'", text)
    return m.group(1) if m else "unknown"


def runtime_files() -> List[Path]:
    return sorted(p for p in RUNTIME_DIR.rglob("*") if p.is_file() and p.suffix in {".js", ".css"})


def catalogue_records() -> Dict[str, Dict[str, Any]]:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import importlib
    mc = importlib.import_module("motion-catalogue")
    return mc.load_all_records()


def schema_errors(instance: Any, schema_path: Path) -> List[str]:
    try:
        import jsonschema
    except ImportError:
        return [f"jsonschema is not installed; cannot validate against {schema_path.name}"]
    schema = load_json(schema_path)
    validator = jsonschema.Draft7Validator(schema)
    out = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        loc = "/".join(str(x) for x in err.path) or "(root)"
        out.append(f"{schema_path.name}: {loc}: {err.message}")
    return out


# --------------------------------------------------------------------------- formats
ROOT_TAG_RE = re.compile(r"<(?P<tag>div|main|section)\b(?P<attrs>[^>]*?\bdata-composition-id\s*=\s*\"root\"[^>]*?)>", re.S)
ATTR_RE = re.compile(r"([\w:.-]+)(?:\s*=\s*\"([^\"]*)\")?")
FORMAT_STYLE_RE = re.compile(r"<style id=\"studio-format\">.*?</style>", re.S)
GENERATED_MARK = "<!-- GENERATED by scripts/studio.py formats"


def format_entries(project: Dict[str, Any], size: Optional[str] = None) -> List[Dict[str, Any]]:
    pre = presets()
    entries = []
    fmts = project["formats"]
    primary_ids = [f["id"] for f in fmts if f.get("primary")]
    primary = primary_ids[0] if primary_ids else fmts[0]["id"]
    for f in fmts:
        fid = f["id"]
        w, h = f["width"], f["height"]
        if size:
            w, h = pre["formats"][fid]["sizes"][size]
        safe = f.get("safe_area") or pre["formats"][fid]["safe_area"]
        entries.append({
            "id": fid,
            "width": w,
            "height": h,
            "primary": fid == primary,
            "safe": safe,
            "file": "index.html" if (fid == primary and not size) else (f"index.{fid}.html" if not size else f"index.{fid}-{size}.html"),
        })
    return entries


def format_style_block(entry: Dict[str, Any]) -> str:
    w, h = entry["width"], entry["height"]
    s = entry["safe"]
    unit = min(w, h) / 100
    vals = {
        "--w": f"{w}px", "--h": f"{h}px", "--u": f"{unit:g}px",
        "--safe-top": f"{round(s['top'] * h)}px", "--safe-right": f"{round(s['right'] * w)}px",
        "--safe-bottom": f"{round(s['bottom'] * h)}px", "--safe-left": f"{round(s['left'] * w)}px",
    }
    body = "".join(f"{k}:{v};" for k, v in vals.items())
    return f"<style id=\"studio-format\">:root{{{body}}}</style>"


def rewrite_root(html: str, entry: Dict[str, Any], fps: int, duration: float) -> str:
    m = ROOT_TAG_RE.search(html)
    if not m:
        raise ValueError('no element with data-composition-id="root" found')
    attrs = ATTR_RE.findall(m.group("attrs"))
    managed = {
        "data-format": entry["id"],
        "data-width": str(entry["width"]),
        "data-height": str(entry["height"]),
        "data-fps": str(fps),
        "data-duration": f"{duration:g}",
    }
    kept = [(k, v) for k, v in attrs if k not in managed and k not in ("id", "data-composition-id")]
    parts = ['id="root"', 'data-composition-id="root"'] + [f'{k}="{v}"' for k, v in managed.items()]
    parts += [f'{k}="{v}"' if v != "" else k for k, v in kept]
    tag = f"<{m.group('tag')} " + "\n     ".join(parts) + ">"
    html = html[:m.start()] + tag + html[m.end():]
    block = format_style_block(entry)
    if FORMAT_STYLE_RE.search(html):
        html = FORMAT_STYLE_RE.sub(lambda _: block, html, count=1)
    else:
        html = html.replace("</head>", f"  {block}\n</head>", 1)
    return html


def render_variant(source_html: str, entry: Dict[str, Any], fps: int, duration: float) -> str:
    html = rewrite_root(source_html, entry, fps, duration)
    if entry["file"] != "index.html":
        html = re.sub(r"^\s*" + re.escape(GENERATED_MARK) + r".*?-->\s*", "", html, flags=re.S)
        header = f"{GENERATED_MARK} from index.html (format: {entry['id']}, {entry['width']}x{entry['height']}). Edit index.html, not this file. -->\n"
        html = header + html
    return html


def cmd_formats(args: argparse.Namespace) -> int:
    pdir = project_dir(args.slug)
    project = load_json(pdir / "project.json")
    src = pdir / "src" / "index.html"
    source = src.read_text(encoding="utf-8")
    written = []
    for entry in format_entries(project, args.size):
        out = render_variant(source, entry, project["fps"], project["duration_sec"])
        target = pdir / "src" / entry["file"]
        if entry["file"] == "index.html":
            source = out
        target.write_text(out, encoding="utf-8", newline="\n")
        written.append(f"{entry['file']} ({entry['id']} {entry['width']}x{entry['height']})")
    print("Formats written:\n  " + "\n  ".join(written))
    return 0


def expected_variants(pdir: Path, project: Dict[str, Any]) -> Dict[str, str]:
    source = (pdir / "src" / "index.html").read_text(encoding="utf-8")
    out = {}
    for entry in format_entries(project):
        out[entry["file"]] = render_variant(source, entry, project["fps"], project["duration_sec"])
    return out


# --------------------------------------------------------------------------- runtime sync
def lock_path(pdir: Path) -> Path:
    return pdir / "src" / RUNTIME_DIRNAME / LOCK_NAME


def runtime_integrity(pdir: Path) -> Report:
    """Vendored runtime must match its lock (no local edits); being behind canonical is a warning."""
    rep = Report()
    lp = lock_path(pdir)
    if not lp.exists():
        rep.error(f"{pdir.name}: no runtime lock at src/{RUNTIME_DIRNAME}/{LOCK_NAME}; run `python scripts/studio.py sync {pdir.name}`.")
        return rep
    lock = load_json(lp)
    base = pdir / "src" / RUNTIME_DIRNAME
    for rel, digest in lock.get("files", {}).items():
        f = base / rel
        if not f.exists():
            rep.error(f"{pdir.name}: vendored runtime file missing: {rel}")
        elif sha256_file(f) != digest:
            rep.error(f"{pdir.name}: vendored runtime file edited in place: {rel} (edit src/studio/ and re-sync).")
    canonical = {p.relative_to(RUNTIME_DIR).as_posix(): sha256_file(p) for p in runtime_files()}
    if canonical != lock.get("files", {}):
        rep.warn(f"{pdir.name}: vendored runtime {lock.get('runtime_version')} differs from canonical src/studio ({runtime_version()}); re-sync when ready.")
    return rep


def cmd_sync(args: argparse.Namespace) -> int:
    pdir = project_dir(args.slug)
    base = pdir / "src" / RUNTIME_DIRNAME
    if lock_path(pdir).exists() and not args.force:
        integ = runtime_integrity(pdir)
        if any("edited in place" in e for e in integ.errors):
            print("Refusing to overwrite locally edited runtime files (use --force):\n  " + "\n  ".join(integ.errors))
            return 1
    if base.exists():
        shutil.rmtree(base)
    files = {}
    for src in runtime_files():
        rel = src.relative_to(RUNTIME_DIR)
        dst = base / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes().replace(b"\r\n", b"\n"))
        files[rel.as_posix()] = sha256_file(dst)
    write_json(lock_path(pdir), {
        "runtime_version": runtime_version(),
        "source": "src/studio",
        "synced_on": date.today().isoformat(),
        "files": files,
    })
    print(f"Synced studio runtime {runtime_version()} into {rel_path(base)} ({len(files)} files).")
    return 0


# --------------------------------------------------------------------------- new
TEXT_SUFFIXES = {".json", ".html", ".md", ".css", ".js", ".txt"}


def cmd_new(args: argparse.Namespace) -> int:
    slug = args.slug
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        raise SystemExit("Error: slug must be kebab-case (a-z, 0-9, hyphens).")
    tdir = TEMPLATES_DIR / args.template
    if not tdir.is_dir():
        avail = ", ".join(sorted(p.name for p in TEMPLATES_DIR.iterdir() if p.is_dir()))
        raise SystemExit(f"Error: template '{args.template}' not found. Available: {avail}")
    records = catalogue_records()
    trec = records.get("project-templates", {}).get(args.template)
    if trec and trec.get("status") in {"blocked", "deprecated", "proposed"}:
        raise SystemExit(f"Error: template '{args.template}' is {trec['status']} in the catalogue.")
    pdir = PROJECTS_DIR / slug
    if pdir.exists():
        raise SystemExit(f"Error: {rel_path(pdir)} already exists.")
    title = args.title or slug.replace("-", " ").title()
    style = args.style or (trec or {}).get("default_style", "editorial-light")
    if style not in records.get("styles", {}):
        raise SystemExit(f"Error: style '{style}' is not registered in catalogue/data/styles/.")
    subs = {"{{SLUG}}": slug, "{{TITLE}}": title, "{{STYLE}}": style, "{{DATE}}": date.today().isoformat()}
    escapers = {
        ".json": lambda v: json.dumps(v)[1:-1],
        ".html": lambda v: html_escape(v, quote=True),
    }
    for src in tdir.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(tdir)
        dst = pdir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in TEXT_SUFFIXES:
            text = src.read_text(encoding="utf-8")
            esc = escapers.get(src.suffix, lambda v: v)
            for k, v in subs.items():
                text = text.replace(k, esc(v))
            dst.write_text(text, encoding="utf-8", newline="\n")
        else:
            shutil.copyfile(src, dst)
    pj = pdir / "project.json"
    project = load_json(pj)
    if args.formats:
        pre = presets()
        wanted = [f.strip() for f in args.formats.split(",") if f.strip()]
        for fid in wanted:
            if fid not in FORMAT_IDS:
                raise SystemExit(f"Error: unknown format '{fid}'.")
        project["formats"] = []
        for i, fid in enumerate(wanted):
            size = pre["formats"][fid]["default_size"]
            w, h = pre["formats"][fid]["sizes"][size]
            project["formats"].append({"id": fid, "width": w, "height": h, "primary": i == 0})
    project["style"] = style
    write_json(pj, project)
    html = (pdir / "src" / "index.html").read_text(encoding="utf-8")
    html = re.sub(r"_studio/styles/[a-z0-9-]+\.css", f"_studio/styles/{style}.css", html)
    (pdir / "src" / "index.html").write_text(html, encoding="utf-8", newline="\n")
    for sub in ("audio", "renders", "qa"):
        (pdir / sub).mkdir(exist_ok=True)
    cmd_sync(argparse.Namespace(slug=slug, force=True))
    cmd_formats(argparse.Namespace(slug=slug, size=None))
    print(f"\nScaffolded projects/{slug} from template '{args.template}' (style {style}).")
    print("Next: fill brief.json (objective, audience, directions), then storyboard.json, then edit src/index.html.")
    print(f"      python scripts/studio.py validate {slug}")
    return 0


# --------------------------------------------------------------------------- validate
def font_families(text: str) -> List[str]:
    fams = []
    for decl in re.findall(r"font-family\s*:\s*([^;}{]+)", text):
        for part in decl.split(","):
            name = part.strip().strip("'\"").strip()
            if name and not name.startswith("var("):
                fams.append(name)
    return fams


def composition_scripts(html: str) -> str:
    """Inline script bodies only (external _studio files are linted at the source)."""
    return "\n".join(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S))


def lint_composition(pdir: Path, project: Optional[Dict[str, Any]], rep: Report) -> None:
    src = pdir / "src" / "index.html"
    if not src.exists():
        rep.error("src/index.html is missing.")
        return
    html = src.read_text(encoding="utf-8")
    scripts = composition_scripts(html)
    for pattern, severity, message in BANNED_PATTERNS:
        haystack = html if "gsap@" in pattern else scripts
        if re.search(pattern, haystack):
            (rep.error if severity == "error" else rep.warn)(f"index.html: {message}")
    if "__timelines" not in html and "Studio.build" not in html:
        rep.error("index.html never registers a timeline (window.__timelines or Studio.build).")
    declared_faces = {n.strip().strip("'\"").lower() for n in re.findall(r"@font-face\s*{[^}]*font-family\s*:\s*([^;]+);", html)}
    for fam in font_families(html):
        low = fam.lower()
        if low in GENERIC_FONTS or low in HF_BUNDLED_FONTS or low in declared_faces:
            continue
        if low in HF_SWAPPED_SYSTEM_FONTS:
            rep.note(f"index.html: font '{fam}' is swapped by HyperFrames for its nearest bundled family.")
        else:
            rep.warn(f"index.html: font '{fam}' is neither HyperFrames-bundled nor declared with @font-face (HyperFrames lint: font_family_without_font_face).")
    if project is None:
        return
    if f"{RUNTIME_DIRNAME}/studio-core.js" not in html:
        rep.warn("index.html does not load the studio runtime (_studio/studio-core.js).")
    style_href = f"{RUNTIME_DIRNAME}/styles/{project['style']}.css"
    if style_href not in html:
        rep.error(f"index.html does not load the project style ({style_href}).")
    m = ROOT_TAG_RE.search(html)
    if not m:
        rep.error('index.html has no root element with data-composition-id="root".')
        return
    attrs = dict(ATTR_RE.findall(m.group("attrs")))
    try:
        if abs(float(attrs.get("data-duration", "0")) - float(project["duration_sec"])) > 1e-3:
            rep.error(f"index.html data-duration {attrs.get('data-duration')} != project.json duration_sec {project['duration_sec']}; run `studio.py formats`.")
    except ValueError:
        rep.error("index.html data-duration is not a number.")
    try:
        expected = expected_variants(pdir, project)
    except ValueError as exc:
        rep.error(f"cannot generate format variants: {exc}")
        return
    for name, content in expected.items():
        f = pdir / "src" / name
        if not f.exists():
            rep.error(f"src/{name} is missing; run `python scripts/studio.py formats {pdir.name}`.")
        elif f.read_text(encoding="utf-8").replace("\r\n", "\n") != content.replace("\r\n", "\n"):
            rep.error(f"src/{name} is out of date with project.json/index.html; run `python scripts/studio.py formats {pdir.name}`.")


def capability_status(records: Dict[str, Dict[str, Any]], cap_id: str) -> Optional[Tuple[str, str]]:
    for coll in ("primitives", "effects", "recipes", "compositions", "libraries"):
        rec = records.get(coll, {}).get(cap_id)
        if rec:
            return coll, rec.get("status", "")
    return None


def validate_project(pdir: Path) -> Report:
    rep = Report()
    slug = pdir.name
    records = catalogue_records()
    pj = pdir / "project.json"
    if not pj.exists():
        rep.note("No project.json: legacy technical-explainer project (single 1280x720 landscape format).")
        if (pdir / "research.json").exists():
            rep.note("research.json present; validate it with scripts/validate-research.py.")
        lint_composition(pdir, None, rep)
        return rep

    project = load_json(pj)
    for e in schema_errors(project, SPECS_DIR / "video-spec.json"):
        rep.error(e)
    if rep.errors:
        return rep
    if project["slug"] != slug:
        rep.error(f"project.json slug '{project['slug']}' does not match folder '{slug}'.")
    ids = [f["id"] for f in project["formats"]]
    if len(set(ids)) != len(ids):
        rep.error("project.json lists a format more than once.")
    if sum(1 for f in project["formats"] if f.get("primary")) > 1:
        rep.error("project.json marks more than one primary format.")
    pre = presets()
    for f in project["formats"]:
        aspect = pre["formats"][f["id"]]["aspect"]
        aw, ah = (int(x) for x in aspect.split(":"))
        if f["width"] * ah != f["height"] * aw:
            rep.error(f"format {f['id']} {f['width']}x{f['height']} is not {aspect}.")
        if f["width"] % 2 or f["height"] % 2:
            rep.error(f"format {f['id']} needs even dimensions for H.264 yuv420p.")
        if f["width"] * f["height"] > 3840 * 2160:
            rep.error(f"format {f['id']} exceeds 4K.")
        elif f["width"] * f["height"] > 1920 * 1080:
            rep.warn(f"format {f['id']} is above 1080p; check memory on the 8 GB host (render one format at a time).")
    if project["fps"] == 60:
        rep.note("60 fps doubles frames to capture; keep --low-memory-mode and render formats sequentially.")
    style = records.get("styles", {}).get(project["style"])
    if not style:
        rep.error(f"style '{project['style']}' is not registered (catalogue/data/styles/).")
    elif style.get("status") in {"blocked", "deprecated"}:
        rep.error(f"style '{project['style']}' is {style['status']}.")
    template = records.get("project-templates", {}).get(project["template"])
    if not template:
        rep.error(f"template '{project['template']}' is not registered (catalogue/data/project-templates/).")

    brief_path = pdir / "brief.json"
    brief = None
    if not brief_path.exists():
        rep.error("brief.json is missing (Stage 0 creative brief).")
    else:
        brief = load_json(brief_path)
        for e in schema_errors(brief, SPECS_DIR / "brief-spec.json"):
            rep.error(e)
    if brief and not rep.errors:
        if brief["slug"] != slug:
            rep.error(f"brief.json slug '{brief['slug']}' does not match folder '{slug}'.")
        dirs = brief["creative_directions"]
        dir_ids = [d["id"] for d in dirs]
        if brief["selected_direction"] is None:
            rep.warn("No creative direction selected yet (brief.selected_direction is null).")
        elif brief["selected_direction"] not in dir_ids:
            rep.error(f"selected_direction '{brief['selected_direction']}' is not one of {dir_ids}.")
        if brief["complexity"] != "simple" and len(dirs) < 2:
            rep.warn("Standard/complex briefs should compare at least two creative directions.")
        for i in range(len(dirs)):
            for j in range(i + 1, len(dirs)):
                a, b = dirs[i], dirs[j]
                same = sum([
                    a["visual_identity"]["style_system"] == b["visual_identity"]["style_system"],
                    a["motion_language"]["personality"].strip().lower() == b["motion_language"]["personality"].strip().lower(),
                    a["composition"]["approach"].strip().lower() == b["composition"]["approach"].strip().lower(),
                ])
                if same >= 2:
                    rep.warn(f"Directions '{a['id']}' and '{b['id']}' share style, motion personality or composition approach; they may not be genuinely distinct.")
        for d in dirs:
            if d["visual_identity"]["style_system"] not in records.get("styles", {}):
                rep.warn(f"direction '{d['id']}' names unregistered style '{d['visual_identity']['style_system']}'.")
        techniques = records.get("references", {})
        for ref in brief.get("references", []):
            for tid in ref.get("technique_ids", []):
                tech = techniques.get(tid)
                if tech is None:
                    rep.error(f"brief reference cites unknown technique '{tid}' (catalogue/data/references/).")
                elif tech.get("implementation_state") in ("observed", "documented"):
                    rep.warn(f"brief cites technique '{tid}', which is only {tech['implementation_state']}: plan its implementation or an approximation.")
        chosen = next((d for d in dirs if d["id"] == brief["selected_direction"]), None)
        if chosen and chosen["visual_identity"]["style_system"] != project["style"]:
            rep.warn(f"project.json style '{project['style']}' differs from the chosen direction's style '{chosen['visual_identity']['style_system']}'.")
        missing_fmt = set(brief["deliverables"]["formats"]) - set(ids)
        if missing_fmt:
            rep.error(f"brief asks for formats {sorted(missing_fmt)} that project.json does not render.")
        dur = brief["deliverables"]["duration_sec"]
        if "max" in dur and project["duration_sec"] > dur["max"] + 1e-6:
            rep.error(f"duration {project['duration_sec']}s exceeds the brief's max {dur['max']}s.")
        if "min" in dur and project["duration_sec"] < dur["min"] - 1e-6:
            rep.error(f"duration {project['duration_sec']}s is below the brief's min {dur['min']}s.")
        if brief["research"]["required"]:
            rj = pdir / "research.json"
            if not rj.exists():
                rep.error("brief.research.required is true but research.json is missing (Stage 0R).")
            else:
                for e in schema_errors(load_json(rj), SPECS_DIR / "research-spec.json"):
                    rep.error(e)
        if brief["audio"]["narration"] == "required" and not project["audio"]["narration"]:
            rep.error("brief requires narration but project.json audio.narration is false.")
        if brief["audio"]["captions"] and not project["audio"]["captions"]:
            rep.error("brief asks for captions but project.json audio.captions is false.")

    needs_storyboard = (brief or {}).get("complexity") in {"standard", "complex"} or (template or {}).get("stages", {}).get("storyboard") == "required"
    sb_path = pdir / "storyboard.json"
    if sb_path.exists():
        sb = load_json(sb_path)
        errs = schema_errors(sb, SPECS_DIR / "storyboard-spec.json")
        for e in errs:
            rep.error(e)
        if not errs:
            check_storyboard(sb, project, brief, records, rep)
    elif needs_storyboard:
        rep.error("storyboard.json is missing (required for standard/complex briefs or this template).")

    audio = project["audio"]
    if audio["narration"]:
        if project["timing"]["source"] != "narration":
            rep.warn("Narration is on but timing.source is not 'narration'; scene times may drift from speech.")
        if not (pdir / "src" / "narration.json").exists():
            rep.error("audio.narration is true but src/narration.json is missing.")
    music = audio["music"]
    if music["enabled"]:
        if not music.get("file"):
            rep.error("audio.music.enabled but no music file is set.")
        elif not (pdir / music["file"]).exists():
            rep.warn(f"music file {music['file']} not found (generated assets may be gitignored).")
        if not music.get("license"):
            rep.error("audio.music.license is required: record the licence and attribution of the track.")
    if audio["captions"] and not (pdir / "src" / "captions.js").exists():
        rep.warn("captions are on but src/captions.js does not exist yet (`studio.py captions` or author cues).")

    integ = runtime_integrity(pdir)
    rep.errors += integ.errors
    rep.warnings += integ.warnings
    lint_composition(pdir, project, rep)
    return rep


def check_storyboard(sb: Dict[str, Any], project: Dict[str, Any], brief: Optional[Dict[str, Any]], records: Dict[str, Dict[str, Any]], rep: Report) -> None:
    if sb["slug"] != project["slug"]:
        rep.error("storyboard.json slug does not match the project.")
    if brief and brief.get("selected_direction") and sb["direction"] != brief["selected_direction"]:
        rep.error(f"storyboard direction '{sb['direction']}' is not the selected direction '{brief['selected_direction']}'.")
    if abs(sb["duration_sec"] - project["duration_sec"]) > 1e-3:
        rep.error(f"storyboard duration {sb['duration_sec']}s != project duration {project['duration_sec']}s.")
    scenes = sorted(sb["scenes"], key=lambda s: s["start_sec"])
    seen = set()
    prev_end = 0.0
    experimental = set()
    for s in scenes:
        if s["id"] in seen:
            rep.error(f"storyboard scene id '{s['id']}' is duplicated.")
        seen.add(s["id"])
        if s["end_sec"] <= s["start_sec"]:
            rep.error(f"scene '{s['id']}' ends before it starts.")
        if s["start_sec"] > prev_end + 0.05:
            rep.warn(f"gap of {s['start_sec'] - prev_end:.2f}s before scene '{s['id']}' (unplanned dead time?).")
        if s["start_sec"] < prev_end - 1.0:
            rep.warn(f"scene '{s['id']}' overlaps the previous scene by {prev_end - s['start_sec']:.2f}s.")
        prev_end = max(prev_end, s["end_sec"])
        caps = list(s["capabilities"])
        if s["transition_out"].get("capability"):
            caps.append(s["transition_out"]["capability"])
        for cap in caps:
            st = capability_status(records, cap)
            if not st:
                rep.error(f"scene '{s['id']}' uses unregistered capability '{cap}'.")
            elif st[1] in {"blocked", "deprecated"}:
                rep.error(f"scene '{s['id']}' uses {st[1]} capability '{cap}'.")
            elif st[1] == "proposed":
                rep.error(f"scene '{s['id']}' uses proposed (unimplemented) capability '{cap}'.")
            elif st[1] == "experimental":
                experimental.add(cap)
        words = sum(len(t.split()) for t in s.get("on_screen_text", []))
        floor = 0.5 + 0.3 * words if words else 0
        if words and (s["end_sec"] - s["start_sec"]) < floor * 0.75:
            rep.warn(f"scene '{s['id']}' shows {words} words in {s['end_sec'] - s['start_sec']:.1f}s (reading floor ~{floor * 0.75:.1f}s).")
    if abs(prev_end - project["duration_sec"]) > 0.05:
        rep.warn(f"storyboard scenes end at {prev_end:.2f}s but the project runs {project['duration_sec']}s.")
    if scenes and scenes[-1]["transition_out"]["type"] not in {"hold-end", "none", "cut", "crossfade"}:
        rep.warn("last scene ends on a transition; consider a held end frame (>= 2 s).")
    if experimental:
        rep.warn(f"uses experimental capabilities ({', '.join(sorted(experimental))}): fine for development, promote them before a client release (approval-policy.md).")


def cmd_validate(args: argparse.Namespace) -> int:
    pdir = project_dir(args.slug)
    rep = validate_project(pdir)
    if args.json:
        print(json.dumps(rep.as_dict(), indent=2))
    else:
        print("=" * 70)
        print(f"STUDIO PROJECT VALIDATION: {pdir.name}")
        print("=" * 70)
        for i in rep.info:
            print(f"  [INFO] {i}")
        for w in rep.warnings:
            print(f"  [WARN] {w}")
        for e in rep.errors:
            print(f"  [FAIL] {e}")
        print("-" * 70)
        print("[PASS] Project is consistent." if rep.ok else f"[FAIL] {len(rep.errors)} error(s).")
    return 0 if rep.ok else 1


# --------------------------------------------------------------------------- build
def build_plan(pdir: Path, quality: Optional[str], only: Optional[List[str]]) -> List[Dict[str, Any]]:
    """Ordered command plan. Each step: {stage, cmd (list), cwd, optional}."""
    rel = rel_path
    steps: List[Dict[str, Any]] = []
    pj = pdir / "project.json"
    if not pj.exists():
        # Legacy projects keep their original, unchanged orchestrator.
        cmd = ["bash", "scripts/build-project.sh", pdir.name]
        steps.append({"stage": "legacy-build", "cmd": cmd, "cwd": "."})
        return steps

    project = load_json(pj)
    q = quality or project.get("quality", "looks")
    steps.append({"stage": "validate", "cmd": [sys.executable, "scripts/studio.py", "validate", pdir.name], "cwd": "."})
    steps.append({"stage": "formats", "cmd": [sys.executable, "scripts/studio.py", "formats", pdir.name], "cwd": "."})
    if project["audio"]["narration"]:
        narr = [sys.executable, "scripts/build-audio.py", pdir.name]
        if project["audio"].get("voice"):
            narr += ["--voice", project["audio"]["voice"]]
        if project["audio"].get("speed"):
            narr += ["--speed", f"{project['audio']['speed']:g}"]
        steps.append({"stage": "narration", "cmd": narr, "cwd": ".", "requires_missing": rel(pdir / "audio" / "narration-full.wav")})
    steps.append({"stage": "lint", "cmd": ["hyperframes", "lint", "."], "cwd": rel(pdir / "src")})
    target = project.get("audio", {}).get("loudness_target_lufs")
    tol = project.get("audio", {}).get("loudness_tolerance_lu", 2)
    for entry in format_entries(project):
        if only and entry["id"] not in only:
            continue
        fid = entry["id"]
        visuals = f"../renders/{fid}/visuals.mp4"
        steps.append({"stage": f"render:{fid}", "cmd": ["hyperframes", "render", ".", "--composition", entry["file"], "--fps", str(project["fps"]), "--quality", q, "--low-memory-mode", "--output", visuals], "cwd": rel(pdir / "src")})
        inputs = ["-i", f"renders/{fid}/visuals.mp4"]
        filters, labels = [], []
        idx = 1
        if project["audio"]["narration"]:
            inputs += ["-i", "audio/narration-full.wav"]
            filters.append(f"[{idx}:a]volume=1.0[a{idx}]")
            labels.append(f"[a{idx}]")
            idx += 1
        music = project["audio"]["music"]
        if music["enabled"] and music.get("file"):
            inputs += ["-i", music["file"]]
            fade = music.get("fade_out_sec", 1.5)
            start = max(0.0, project["duration_sec"] - fade)
            filters.append(f"[{idx}:a]volume=0.6,afade=t=out:st={start:g}:d={fade:g}[a{idx}]")
            labels.append(f"[a{idx}]")
            idx += 1
        if project["audio"]["sfx"]:
            inputs += ["-i", "audio/sfx-track.wav"]
            filters.append(f"[{idx}:a]volume=0.85[a{idx}]")
            labels.append(f"[a{idx}]")
            idx += 1
        final = f"renders/{fid}/final.mp4"
        if labels:
            mix = ";".join(filters) + ";" + "".join(labels) + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=2[aout]"
            cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", mix, "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{project['duration_sec']:g}", final]
        else:
            cmd = ["ffmpeg", "-y", "-i", f"renders/{fid}/visuals.mp4", "-c", "copy", final]
        steps.append({"stage": f"mux:{fid}", "cmd": cmd, "cwd": rel(pdir)})
        qa = ["bash", rel(QA_SCRIPT), rel(pdir / "renders" / fid / "final.mp4"),
              "--expect-width", str(entry["width"]), "--expect-height", str(entry["height"]),
              "--expect-fps", str(project["fps"]), "--expect-duration", f"{project['duration_sec']:g}"]
        if labels and target is not None:
            qa += ["--expect-lufs", f"{target:g}", "--lufs-tolerance", f"{tol:g}"]
        if not labels:
            qa += ["--allow-silent"]
        steps.append({"stage": f"qa:{fid}", "cmd": qa, "cwd": "."})
        steps.append({"stage": f"deliver:{fid}", "cmd": ["copy", rel(pdir / "renders" / fid / "final.mp4"), f"out/{pdir.name}-{fid}.mp4"], "cwd": "."})
    return steps


def cmd_build(args: argparse.Namespace) -> int:
    pdir = project_dir(args.slug)
    only = [f.strip() for f in args.formats.split(",")] if args.formats else None
    plan = build_plan(pdir, args.quality, only)
    if args.dry_run:
        print(f"Build plan for {pdir.name} ({'studio' if (pdir / 'project.json').exists() else 'legacy'} project):")
        for i, s in enumerate(plan, 1):
            print(f"  {i:>2}. [{s['stage']}] (cwd {s['cwd']}) " + " ".join(s["cmd"]))
        return 0
    if plan[0]["stage"] == "legacy-build":
        return subprocess.run(plan[0]["cmd"], cwd=REPO_ROOT).returncode
    missing = [tool for tool in ("hyperframes", "ffmpeg", "ffprobe") if not shutil.which(tool)]
    if missing:
        print(f"Error: required tools not on PATH: {', '.join(missing)}. Use --dry-run to print the plan, or run on the render host.")
        return 1
    for s in plan:
        cwd = REPO_ROOT / s["cwd"]
        if s.get("requires") and not (REPO_ROOT / s["requires"]).exists():
            print(f"[skip] {s['stage']}: {s['requires']} not found")
            continue
        if s.get("requires_missing") and (REPO_ROOT / s["requires_missing"]).exists():
            print(f"[skip] {s['stage']}: {s['requires_missing']} already exists")
            continue
        print(f"[{s['stage']}] " + " ".join(s["cmd"]))
        if s["cmd"][0] == "copy":
            dst = REPO_ROOT / s["cmd"][2]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / s["cmd"][1], dst)
            continue
        if s["stage"].startswith("render:"):
            (pdir / "renders" / s["stage"].split(":", 1)[1]).mkdir(parents=True, exist_ok=True)
        res = subprocess.run(s["cmd"], cwd=cwd)
        if res.returncode != 0:
            print(f"Error: stage {s['stage']} failed with exit code {res.returncode}.")
            return res.returncode
    print("Build complete. Technical QA ran per format; creative review is separate: python scripts/studio.py review " + pdir.name)
    return 0


# --------------------------------------------------------------------------- captions
def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def vtt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def cmd_captions(args: argparse.Namespace) -> int:
    pdir = project_dir(args.slug)
    tl_path = pdir / "audio" / "timeline.json"
    if not tl_path.exists():
        raise SystemExit("Error: audio/timeline.json not found; synthesise narration first (scripts/build-audio.py).")
    timeline = load_json(tl_path)
    cues = []
    for sc in timeline["scenes"]:
        sentences = split_sentences(sc["text"])
        total = sum(len(s) for s in sentences) or 1
        t = sc["start_time_sec"]
        for s in sentences:
            d = sc["duration_sec"] * len(s) / total
            cues.append({"start": round(t, 3), "end": round(t + d, 3), "text": s})
            t += d
    js = "// GENERATED by scripts/studio.py captions from audio/timeline.json.\n// Sentence timing is proportional to character count (approximate); use `hyperframes transcribe` for word timing.\nwindow.STUDIO_CAPTIONS = " + json.dumps(cues, indent=2, ensure_ascii=False) + ";\n"
    (pdir / "src" / "captions.js").write_text(js, encoding="utf-8", newline="\n")
    out = pdir / "captions"
    out.mkdir(exist_ok=True)
    lines = ["WEBVTT", ""]
    for i, c in enumerate(cues, 1):
        lines += [str(i), f"{vtt_time(c['start'])} --> {vtt_time(c['end'])}", c["text"], ""]
    (out / f"{pdir.name}.vtt").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"Wrote {len(cues)} approximate cues to src/captions.js and captions/{pdir.name}.vtt")
    return 0


# --------------------------------------------------------------------------- review
def cmd_review(args: argparse.Namespace) -> int:
    pdir = project_dir(args.slug)
    path = pdir / "qa" / "creative-review.json"
    if args.init:
        if path.exists():
            print(f"{rel_path(path)} already exists.")
            return 0
        write_json(path, {
            "project": pdir.name,
            "reviewer": None,
            "reviewed_on": None,
            "renders_reviewed": [],
            "criteria": [{"id": cid, "question": q, "score": None, "notes": "", "evidence": []} for cid, q in CREATIVE_CRITERIA],
            "verdict": None,
            "pass_rule": "Every criterion scored 1-5 with evidence (frame or contact-sheet paths); all >= 3 and mean >= 3.5.",
        })
        print(f"Created {rel_path(path)}: score each criterion after inspecting frames.")
        return 0
    if not path.exists():
        print("No creative review yet. Create one with --init after rendering frames.")
        return 1
    review = load_json(path)
    scores = [c.get("score") for c in review["criteria"]]
    unscored = [c["id"] for c in review["criteria"] if not isinstance(c.get("score"), (int, float))]
    no_evidence = [c["id"] for c in review["criteria"] if not c.get("evidence")]
    print(f"Creative review for {pdir.name} (reviewer: {review.get('reviewer')}, {review.get('reviewed_on')})")
    for c in review["criteria"]:
        print(f"  {c['id']:<18} {c.get('score')!s:>4}  {c.get('notes', '')[:90]}")
    if unscored or no_evidence:
        print(f"[INCOMPLETE] unscored: {unscored or '-'}; without evidence: {no_evidence or '-'}")
        return 1
    mean = sum(scores) / len(scores)
    passed = min(scores) >= 3 and mean >= 3.5
    print(f"[{'PASS' if passed else 'FAIL'}] min {min(scores)}, mean {mean:.2f}")
    return 0 if passed else 1


# --------------------------------------------------------------------------- status
def cmd_status(args: argparse.Namespace) -> int:
    pdir = project_dir(args.slug)
    studio = (pdir / "project.json").exists()
    rows = [
        ("brief.json", "Stage 0 creative brief + directions"),
        ("research.json", "Stage 0R research dossier (factual topics)"),
        ("storyboard.json", "Stage 1 scene plan"),
        ("src/narration.json", "Stage 2 narration script"),
        ("audio/timeline.json", "Stage 3 measured narration timing"),
        ("src/index.html", "Stage 4 composition"),
        (f"src/{RUNTIME_DIRNAME}/{LOCK_NAME}", "Studio runtime vendored"),
        ("qa/frame-review/report.json", "Stage 9 frame review (scripts/frame-review.py)"),
        ("qa/creative-review.json", "Stage 9 creative review rubric"),
    ]
    print(f"{pdir.name}: {'studio' if studio else 'legacy'} project")
    for rel, label in rows:
        print(f"  [{'x' if (pdir / rel).exists() else ' '}] {rel:<34} {label}")
    if studio:
        project = load_json(pdir / "project.json")
        for e in format_entries(project):
            exists = (pdir / "src" / e["file"]).exists()
            print(f"  [{'x' if exists else ' '}] src/{e['file']:<30} format {e['id']} {e['width']}x{e['height']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Motion Lab creative studio project CLI")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("new", help="Scaffold a project from a project template")
    p.add_argument("slug")
    p.add_argument("--template", required=True)
    p.add_argument("--title")
    p.add_argument("--style")
    p.add_argument("--formats", help="Comma-separated formats; first is primary (default: template's project.json)")

    p = sub.add_parser("sync", help="Vendor the canonical runtime into the project")
    p.add_argument("slug")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("formats", help="Generate per-format entry files")
    p.add_argument("slug")
    p.add_argument("--size", choices=["720p", "1080p", "4k"], help="Write index.<format>-<size>.html variants at a preset size")

    p = sub.add_parser("validate", help="Validate brief, project, storyboard, runtime and composition")
    p.add_argument("slug")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("build", help="Render all formats, mux and run QA (or print the plan)")
    p.add_argument("slug")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--quality", choices=["draft", "looks", "delivery"])
    p.add_argument("--formats", help="Only these formats (comma-separated)")

    p = sub.add_parser("captions", help="Approximate caption cues from narration timing")
    p.add_argument("slug")

    p = sub.add_parser("review", help="Creative review rubric")
    p.add_argument("slug")
    p.add_argument("--init", action="store_true")

    p = sub.add_parser("status", help="Lifecycle artefact checklist")
    p.add_argument("slug")

    args = parser.parse_args()
    handlers = {
        "new": cmd_new, "sync": cmd_sync, "formats": cmd_formats, "validate": cmd_validate,
        "build": cmd_build, "captions": cmd_captions, "review": cmd_review, "status": cmd_status,
    }
    if args.command not in handlers:
        parser.print_help()
        return 0
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
