#!/usr/bin/env python3
"""
scripts/studio.py
Project lifecycle CLI for the Motion Lab creative studio (stdlib + jsonschema).

Subcommands:
  new <slug> --template <id> [--title T] [--style S] [--style-template T] [--formats a,b] [--category a,b]   scaffold from templates/projects/<id>/
  sync <slug> [--force]          copy the canonical runtime (src/studio/) into projects/<slug>/src/_studio/
  formats <slug> [--size 1080p]  write per-format entry files (src/index.<format>.html) from src/index.html
  upgrade <slug>... | --all [--keep-renders]   re-sync the runtime and regenerate entry files after a runtime or preset
                                 upgrade; renders it supersedes move to renders/history/<format>/<when>/ (out/ copies to out/archive/)
  renders [<slug>...] [--archive [--unstamped]]   render state per format (current, stale with the changed files,
                                 unstamped, missing); --archive moves stale renders to history
  validate <slug> [--json]       schema + cross-reference + composition checks (exit 1 on errors)
  build <slug> [--dry-run]       render every format with HyperFrames, mux audio, run QA gates; a stale render is
                                 moved to renders/history/ before it is rendered again, never overwritten
  captions <slug> [--timing words] [--grouping phrase]   caption cues from audio/timeline.json: approximate sentences, or measured word times
  words <slug> "<phrase>"        film time at which a phrase is spoken (from audio/words.json)
  script <slug> [--json]         pre-render script and story lint: timed sentence sheet, hook, rhythm, loop, asks, story table
  hook score|formulas            rank hook lines; list the hook formulas (specs/hook-formulas.json)
  review <slug> [--init]         creative-review rubric (qa/creative-review.json): create or summarise
  status <slug>                  which lifecycle artefacts exist and what comes next
  series new|add|show|list|validate   groups of projects: sequential parts or a themed collection (series/<slug>/series.json)
  style list|show|recommend|adopt|check   style templates: pick one per video, check a video against it, see which videos are behind

Projects without project.json are legacy technical explainers: `build` prints/runs the original
single-format plan (1280x720 landscape, index.html) so existing workflows keep working.
"""

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import resource
import shutil
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from html import escape as html_escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = REPO_ROOT / "projects"
SERIES_DIR = REPO_ROOT / "series"
OUT_DIR = REPO_ROOT / "out"
RUNTIME_DIR = REPO_ROOT / "src" / "studio"
TEMPLATES_DIR = REPO_ROOT / "templates" / "projects"
SPECS_DIR = REPO_ROOT / "specs"
SCRIPTS_DIR = REPO_ROOT / "scripts"
PRESETS_FILE = SPECS_DIR / "format-presets.json"
RUNTIME_DIRNAME = "_studio"
LOCK_NAME = "studio.lock.json"
QA_SCRIPT = REPO_ROOT / ".claude" / "skills" / "video-assembler" / "scripts" / "run-qa-gates.sh"

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
    ("arc", "Clear opening, progression and ending; the last frame holds long enough; the value claim lands by scene 2 and the film survives the delete test (docs/short-form-lessons.md)."),
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
    if candidate.is_dir() and ((candidate / "project.json").exists() or (candidate / "research.json").exists() or (candidate / "src").is_dir()):
        return candidate
    p = Path(slug_or_path)
    if p.is_dir():
        return p.resolve()
    # Search recursively under projects/ for matching folder name, path, or project.json slug
    for cand in sorted(PROJECTS_DIR.rglob("*")):
        if cand.is_dir() and ((cand / "project.json").exists() or (cand / "research.json").exists()):
            rel_path = cand.relative_to(PROJECTS_DIR).as_posix()
            if rel_path == slug_or_path or cand.name == slug_or_path:
                return cand
            if (cand / "project.json").exists():
                try:
                    data = json.loads((cand / "project.json").read_text(encoding="utf-8"))
                    if data.get("slug") == slug_or_path:
                        return cand
                except Exception:
                    pass
    raise SystemExit(f"Error: project '{slug_or_path}' not found under projects/.")


def presets() -> Dict[str, Any]:
    return load_json(PRESETS_FILE)


def runtime_version() -> str:
    text = (RUNTIME_DIR / "studio-core.js").read_text(encoding="utf-8")
    m = re.search(r"Studio\.version\s*=\s*'([^']+)'", text)
    return m.group(1) if m else "unknown"


def runtime_files() -> List[Path]:
    return sorted(p for p in RUNTIME_DIR.rglob("*") if p.is_file() and p.suffix in {".js", ".css"})


def ensure_schema_python() -> None:
    """Re-run the current command under python3.12 when this interpreter lacks jsonschema.

    Call it first thing, before any work: re-executing later would start the command over."""
    try:
        import jsonschema  # noqa: F401
        return
    except ImportError:
        pass
    py12 = shutil.which("python3.12") or "/opt/homebrew/bin/python3.12"
    if os.path.exists(py12) and os.path.realpath(sys.executable) != os.path.realpath(py12):
        os.execv(py12, [py12] + sys.argv)


def catalogue_records() -> Dict[str, Dict[str, Any]]:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import importlib
    # Loading records needs no jsonschema, and motion-catalogue's re-exec into python3.12 would restart this
    # command from the top (an upgrade or a build would run its first steps twice).
    previous = os.environ.get("MOTION_LAB_NO_REEXEC")
    os.environ["MOTION_LAB_NO_REEXEC"] = "1"
    try:
        mc = importlib.import_module("motion-catalogue")
    finally:
        if previous is None:
            os.environ.pop("MOTION_LAB_NO_REEXEC", None)
        else:
            os.environ["MOTION_LAB_NO_REEXEC"] = previous
    return mc.load_all_records()


def pipeline_module(name: str) -> Any:
    """Import a module from src/pipeline/ (pure Python helpers shared with the other scripts)."""
    pipeline = str(REPO_ROOT / "src" / "pipeline")
    if pipeline not in sys.path:
        sys.path.insert(0, pipeline)
    import importlib
    return importlib.import_module(name)


def style_templates_module() -> Any:
    return pipeline_module("style_templates")


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



# --------------------------------------------------------------------------- categories
def load_categories() -> Dict[str, Dict[str, Any]]:
    """Subject categories from specs/categories.json, keyed by id (order preserved)."""
    return {c["id"]: c for c in load_json(SPECS_DIR / "categories.json")["categories"]}


def unknown_categories(values: List[str]) -> List[str]:
    known = load_categories()
    return [v for v in values if v not in known]


def parse_category_arg(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    values = [c.strip() for c in raw.split(",") if c.strip()]
    bad = unknown_categories(values)
    if bad:
        raise SystemExit(f"Error: unknown category {bad}. Available: {', '.join(load_categories())}")
    return list(dict.fromkeys(values))


def load_video_types() -> Dict[str, Any]:
    """The three supported video types (specs/video-types.json) with their allowed duration windows."""
    spec = load_json(SPECS_DIR / "video-types.json")
    margin = float(spec["margin_sec"])
    types: Dict[str, Any] = {}
    for tid, t in spec["types"].items():
        lo = t["nominal_sec"]["min"]
        hi = t["nominal_sec"].get("max")
        types[tid] = {**t, "id": tid,
                      "window_sec": (max(0.0, lo - margin), None if hi is None else hi + margin)}
    return types


def describe_window(t: Dict[str, Any]) -> str:
    lo, hi = t["window_sec"]
    return f"{lo:g}s or more" if hi is None else f"{lo:g}-{hi:g}s"


def parse_video_type_arg(raw: Optional[str]) -> Dict[str, Any]:
    types = load_video_types()
    if raw not in types:
        raise SystemExit(f"Error: --type is required and must be one of: {', '.join(types)}. "
                         + "; ".join(f"{t['id']} = {t['name']} ({t['format']}, {describe_window(t)})" for t in types.values()))
    return types[raw]


def check_video_type(brief: Dict[str, Any], project: Dict[str, Any], rep: Report) -> None:
    """Hold a brief and its project to the declared video type: platform, format and duration window."""
    types = load_video_types()
    deliv = brief["deliverables"]
    vt = deliv.get("video_type")
    if vt is None:
        rep.warn("brief.deliverables.video_type is not set. Motion Lab produces only "
                 + ", ".join(f"{t['id']} ({describe_window(t)})" for t in types.values())
                 + "; set one (legacy brief: its length and platforms are not checked).")
        return
    t = types.get(vt)
    if t is None:
        rep.error(f"video_type '{vt}' is not one of {', '.join(types)} (specs/video-types.json).")
        return
    extra_platforms = [p for p in brief["platforms"] if p != t["platform"]]
    if t["platform"] not in brief["platforms"] or extra_platforms:
        rep.error(f"a {t['id']} is published on {t['platform']} only; brief platforms are {brief['platforms']}.")
    extra_formats = [f for f in deliv["formats"] if f != t["format"]]
    if extra_formats:
        rep.error(f"a {t['id']} is {t['format']} only; brief formats include {extra_formats}.")
    lo, hi = t["window_sec"]
    dur = deliv["duration_sec"]
    for key in ("min", "target", "max"):
        v = dur.get(key)
        if v is None:
            continue
        if v < lo - 1e-6 or (hi is not None and v > hi + 1e-6):
            rep.error(f"brief duration_sec.{key} {v:g}s is outside the {t['id']} window ({describe_window(t)}).")
    d = project["duration_sec"]
    if d < lo - 1e-6 or (hi is not None and d > hi + 1e-6):
        rep.error(f"project duration {d:g}s is outside the {t['id']} window ({describe_window(t)}): "
                  "change the length, or the video_type if this is really another type.")
    nom = t["nominal_sec"]
    if lo - 1e-6 <= d < nom["min"] or (nom.get("max") is not None and nom["max"] < d <= hi + 1e-6):
        rep.note(f"duration {d:g}s is inside the {t['id']} margin (nominal {nom['min']:g}"
                 + (f"-{nom['max']:g}" if nom.get("max") is not None else "+") + "s).")


def find_project(ref: str) -> Optional[Path]:
    """Like project_dir() but returns None instead of exiting."""
    try:
        return project_dir(ref)
    except SystemExit:
        return None



def style_category_mismatch(style: Optional[Dict[str, Any]], categories: List[str]) -> Optional[str]:
    """Warning text when a category-tagged style shares no category with the project; None otherwise.
    A style with no categories is general-purpose and never mismatches."""
    tagged = (style or {}).get("categories") or []
    if not tagged or set(tagged) & set(categories):
        return None
    return (f"style '{style['id']}' is tagged for {', '.join(tagged)}, "
            f"not for this project's {', '.join(categories)}. Fine if deliberate; otherwise pick a closer style.")


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
        vendored = lock.get("files", {})
        changed = sorted(f for f in set(canonical) | set(vendored) if canonical.get(f) != vendored.get(f))
        shown = ", ".join(changed[:4]) + (f" (+{len(changed) - 4} more)" if len(changed) > 4 else "")
        label = "same version label, " if lock.get("runtime_version") == runtime_version() else ""
        rep.warn(f"{pdir.name}: vendored runtime {lock.get('runtime_version')} is behind canonical src/studio ({runtime_version()}, {label}content differs in: {shown}); "
                 f"`python scripts/studio.py upgrade {pdir.name}` re-syncs it and moves the renders it supersedes to renders/{HISTORY_DIRNAME}/.")
    return rep


def cmd_sync(args: argparse.Namespace) -> int:
    pdir = project_dir(args.slug)
    base = pdir / "src" / RUNTIME_DIRNAME
    if lock_path(pdir).exists() and not args.force:
        integ = runtime_integrity(pdir)
        if any("edited in place" in e for e in integ.errors):
            print("Refusing to overwrite locally edited runtime files (use --force):\n  " + "\n  ".join(integ.errors))
            return 1
        if integ.ok and not integ.warnings and load_json(lock_path(pdir)).get("runtime_version") == runtime_version():
            # rewriting the lock would only change synced_on, and that alone would mark every render stale
            print(f"Studio runtime {runtime_version()} in {rel_path(base)} is already current.")
            return 0
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
    categories = parse_category_arg(getattr(args, "category", None))
    vtype = parse_video_type_arg(getattr(args, "video_type", None))
    if args.formats and [f.strip() for f in args.formats.split(",") if f.strip()] != [vtype["format"]]:
        raise SystemExit(f"Error: a {vtype['id']} is {vtype['format']} only; drop --formats or use --formats {vtype['format']}.")
    stpl = None
    if getattr(args, "style_template", None):
        stpl = records.get("style-templates", {}).get(args.style_template)
        if not stpl:
            raise SystemExit(f"Error: style template '{args.style_template}' not found. Available: {', '.join(records.get('style-templates', {}))}")
        if stpl.get("status") in {"blocked", "deprecated"}:
            raise SystemExit(f"Error: style template '{args.style_template}' is {stpl['status']}.")
    style = args.style or (stpl["look"]["style"] if stpl else None) or (trec or {}).get("default_style", "editorial-light")
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
    pre = presets()
    fid = vtype["format"]
    size = pre["formats"][fid]["default_size"]
    w, h = pre["formats"][fid]["sizes"][size]
    project["formats"] = [{"id": fid, "width": w, "height": h, "primary": True, "platform": vtype["platform"]}]
    project["duration_sec"] = vtype["target_sec"]
    project["style"] = style
    if stpl:
        project["style_template"] = {"id": stpl["id"], "version": stpl["version"]}
    write_json(pj, project)
    bj = pdir / "brief.json"
    brief = load_json(bj)
    nominal = vtype["nominal_sec"]
    brief["platforms"] = [vtype["platform"]]
    brief["deliverables"]["formats"] = [fid]
    brief["deliverables"] = {
        "video_type": vtype["id"],
        "formats": [fid],
        "duration_sec": {"min": nominal["min"], "target": vtype["target_sec"],
                         **({"max": nominal["max"]} if nominal.get("max") is not None else {})},
        **{k: v for k, v in brief["deliverables"].items() if k not in ("video_type", "formats", "duration_sec")},
    }
    if categories:
        brief = {**{k: v for k, v in brief.items() if k in ("spec_version", "slug", "title")},
                 "categories": categories,
                 **{k: v for k, v in brief.items() if k not in ("spec_version", "slug", "title")}}
    write_json(bj, brief)
    sbj = pdir / "storyboard.json"
    if sbj.exists():
        sb = load_json(sbj)
        sb["duration_sec"] = vtype["target_sec"]
        write_json(sbj, sb)
    html = (pdir / "src" / "index.html").read_text(encoding="utf-8")
    html = re.sub(r"_studio/styles/[a-z0-9-]+\.css", f"_studio/styles/{style}.css", html)
    html = re.sub(r'data-duration="[0-9.]+"', f'data-duration="{vtype["target_sec"]:g}"', html, count=1)
    (pdir / "src" / "index.html").write_text(html, encoding="utf-8", newline="\n")
    for sub in ("audio", "renders", "qa"):
        (pdir / sub).mkdir(exist_ok=True)
    cmd_sync(argparse.Namespace(slug=slug, force=True))
    cmd_formats(argparse.Namespace(slug=slug, size=None))
    print(f"\nScaffolded projects/{slug} as a {vtype['name']} ({fid}, target {vtype['target_sec']}s, "
          f"allowed {describe_window(vtype)}) from template '{args.template}' (style {style}"
          + (f", style template {stpl['id']} v{stpl['version']}" if stpl else "") + ").")
    if not stpl:
        print("Note: no style template. Once the brief is written: python scripts/studio.py style recommend " + slug)
    if categories:
        fit = style_category_mismatch(records["styles"].get(style), categories)
        if fit:
            print(f"Note: {fit}")
    else:
        print(f"Note: no category set. Add \"categories\" to brief.json (one or more of: {', '.join(load_categories())}) or re-run with --category.")
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
    for url in re.findall(r"<script\b[^>]*\bsrc\s*=\s*[\"'](https?://[^\"']+)", html, re.I):
        hint = f"{RUNTIME_DIRNAME}/vendor/gsap.min.js" if "gsap" in url.lower() else "a copy under src/"
        rep.warn(f"index.html: loads {url} over the network at render time (fails offline, not reproducible); use {hint}.")
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


STORY_SIGNED_FILES = ("beatmap.json", "storyboard.json", "src/narration.json")


def check_story_signoff(pdir: Path, rep: Report) -> None:
    """Phase-2 gate: the story-writer's verdict in qa/story-review.json, and whether the story changed after it.

    Warnings only, like the other story checks: a film can still be built, but the gap is visible.
    """
    if not any((pdir / rel).exists() for rel in STORY_SIGNED_FILES):
        return
    path = pdir / "qa" / "story-review.json"
    if not path.exists():
        rep.warn("story not signed off: qa/story-review.json is missing. Phase 3 (audio, visuals, sound) starts after "
                 "the story-writer verdict is 'complete' (.claude/skills/story-writer/SKILL.md).")
        return
    try:
        review = load_json(path)
    except (OSError, ValueError) as exc:
        rep.warn(f"qa/story-review.json is unreadable ({exc}).")
        return
    verdict = review.get("verdict")
    if verdict != "complete":
        open_reqs = [r.get("id", "?") for r in review.get("research_requests", [])
                     if r.get("blocking") and not r.get("answered")]
        extra = f"; open blocking research requests: {', '.join(open_reqs)}" if open_reqs else ""
        rep.warn(f"story-writer verdict is '{verdict}', not 'complete' (iteration {review.get('iteration', '?')}){extra}.")
        return
    changed = []
    for rel, digest in (review.get("signed") or {}).items():
        f = pdir / rel
        want = str(digest).split(":", 1)[-1].strip().lower()
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != want:
            changed.append(rel)
    if changed:
        rep.warn("story changed after the story-writer signed it off (" + ", ".join(changed) + "): run a story-writer "
                 "`review` pass before render.")
    elif not review.get("signed"):
        rep.warn("qa/story-review.json says 'complete' but records no `signed` hashes, so later edits cannot be detected.")


def check_creative_artefacts(pdir: Path, project: Dict[str, Any], records: Dict[str, Dict[str, Any]], rep: Report) -> None:
    """Optional creative-intelligence files (beatmap.json, design-profile.json, bakeoff, assets, motion QA).

    Every file is optional: a project without them validates exactly as before. When present they are checked
    against their specs; see specs/creative-intelligence-architecture.md."""
    import importlib.util
    pipe = str(REPO_ROOT / "src" / "pipeline")
    if pipe not in sys.path:
        sys.path.insert(0, pipe)
    bm_path = pdir / "beatmap.json"
    if bm_path.exists():
        try:
            spec = importlib.util.spec_from_file_location("beatmap_mod", REPO_ROOT / "scripts" / "beatmap.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            doc = load_json(bm_path)
            errs, warns = mod.check(doc, pdir)
            rep.errors += [f"beatmap.json: {e}" for e in errs]
            rep.warnings += [f"beatmap.json: {w}" for w in warns]
            ids = {b["id"] for b in doc.get("beats", [])}
            sbp = pdir / "storyboard.json"
            if sbp.exists():
                for s in load_json(sbp).get("scenes", []):
                    if s.get("beat_id") and s["beat_id"] not in ids:
                        rep.error(f"storyboard scene {s['id']} names beat_id {s['beat_id']!r} which is not in beatmap.json.")
        except Exception as exc:  # a broken optional file must not hide the rest of the report
            rep.warn(f"beatmap.json could not be checked: {exc}")
    dp = pdir / "design-profile.json"
    if dp.exists():
        try:
            import profiles as pf
            prof = load_json(dp)
            reg = pf.load_registry()
            errs = pf.schema_errors(prof)
            e2, w2 = pf.check_profile(prof, records.get("styles", {}), records.get("references", {}), records.get("reference-sources", {}), reg)
            rep.errors += [f"design-profile.json: {e}" for e in errs + e2]
            rep.warnings += [f"design-profile.json: {w}" for w in w2]
            if prof.get("style") and prof["style"] != project.get("style"):
                rep.warn(f"design-profile.json style {prof['style']!r} differs from project.json style {project.get('style')!r}.")
        except Exception as exc:
            rep.warn(f"design-profile.json could not be checked: {exc}")
    bo = pdir / "bakeoff" / "bakeoff.json"
    if bo.exists():
        rec = load_json(bo)
        if "decision" not in rec:
            rep.warn("bakeoff/bakeoff.json has no recorded decision (scripts/bakeoff.py decide).")
        elif not rec.get("distinctness", {}).get("distinct", True):
            rep.warn("the bake-off compared candidates that were not structurally distinct; its decision is weak evidence.")
    man = pdir / "src" / "assets" / "manifest.json"
    if man.exists():
        for name, rec in load_json(man).items():
            if not (pdir / "src" / "assets" / rec.get("file", "")).exists():
                rep.error(f"assets/manifest.json lists {name} but {rec.get('file')} is missing.")
    qa = pdir / "qa" / "motion" / "motion-qa.json"
    if qa.exists():
        s = load_json(qa).get("summary", {})
        if s.get("objective_failures"):
            rep.error(f"qa/motion/motion-qa.json records {s['objective_failures']} objective failure(s); re-run scripts/motion-qa.py after fixing.")
        else:
            rep.note(f"motion QA: {s.get('measured_warnings', 0)} measured warning(s), {s.get('waived', 0)} waiver(s); technical_pass is not a quality verdict.")


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
    is_nested = pdir.parent != PROJECTS_DIR
    valid_slugs = {pdir.name, f"{pdir.parent.name}/{pdir.name}", f"{pdir.parent.name}-{pdir.name}", project.get("slug", "")} if is_nested else {pdir.name}
    if project["slug"] not in valid_slugs:
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
        if brief["slug"] not in valid_slugs:
            rep.error(f"brief.json slug '{brief['slug']}' does not match folder '{slug}'.")
        cats = brief.get("categories")
        if not cats:
            rep.warn(f"brief has no categories; add one or more of: {', '.join(load_categories())}.")
        else:
            bad = unknown_categories(cats)
            if bad:
                rep.error(f"brief categories {bad} are not in specs/categories.json.")
            else:
                fit = style_category_mismatch(style, cats)
                if fit:
                    rep.warn(fit)
        for ser in series_containing(pdir):
            rep.note(f"part of series '{ser['slug']}' ({ser['kind']})")
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
        check_video_type(brief, project, rep)
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

    pin = project.get("style_template")
    if pin:
        stpl = records.get("style-templates", {}).get(pin["id"])
        if not stpl:
            rep.error(f"style template '{pin['id']}' is not registered (catalogue/data/style-templates/).")
        elif stpl.get("status") in {"blocked", "deprecated"}:
            rep.error(f"style template '{pin['id']}' is {stpl['status']}.")
        else:
            for level, msg in style_templates_module().check_project(pdir, project, brief, stpl):
                (rep.warn if level == "warn" else rep.note)(f"style template {pin['id']}: {msg}")
    else:
        rep.note("no style_template in project.json; run `python scripts/studio.py style recommend " + pdir.name + "`.")

    # Pre-render script and story lint (hook, rhythm, loop, asks, `why`). Warnings only; notes stay in `studio.py script`.
    for level, fid, msg in pipeline_module("scriptlint").script_report(pdir)["findings"]:
        if level == "warn":
            rep.warn(f"script ({fid}): {msg}")
    check_story_signoff(pdir, rep)

    audio = project["audio"]
    if audio["narration"]:
        if project["timing"]["source"] != "narration":
            rep.warn("Narration is on but timing.source is not 'narration'; scene times may drift from speech.")
        if not (pdir / "src" / "narration.json").exists():
            rep.error("audio.narration is true but src/narration.json is missing.")
        else:
            nar = pipeline_module("narration")
            state, reasons = nar.narration_state(pdir, nar.resolve_request(pdir, **narration_args(project)))
            if state == "stale":
                rep.warn("audio/narration-full.wav is stale (" + "; ".join(reasons) + "). `studio.py build` re-synthesises it and stops "
                         "if scene timing moves; run `python scripts/build-audio.py " + pdir.name + "` first and re-time the cues in src/.")
        tl_path = pdir / "audio" / "timeline.json"
        if tl_path.exists():
            total = load_json(tl_path).get("total_duration_sec") or load_json(tl_path).get("duration_sec")
            if total and float(total) > project["duration_sec"] + 1e-3:
                rep.error(f"narration runs {float(total):.2f}s but duration_sec is {project['duration_sec']}s; the mux cuts the speech at "
                          f"duration_sec. Raise duration_sec or shorten the script.")
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

    check_creative_artefacts(pdir, project, records, rep)
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
# --------------------------------------------------------------------------- build bookkeeping
STAMP_NAME = "visuals.stamp.json"
PARTIAL_NAME = "visuals.partial.mp4"
TIMINGS_LOG = REPO_ROOT / "logs" / "build-timings.jsonl"


HISTORY_DIRNAME = "history"


def render_inputs(pdir: Path, entry: Dict[str, Any]) -> Dict[str, str]:
    """{path under src/: sha256} for every file a format's visuals depend on.

    Other formats' generated index.<id>.html files and HyperFrames caches are excluded, so
    editing the portrait entry does not invalidate the landscape render.
    """
    src = pdir / "src"
    out = {}
    for f in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = f.relative_to(src)
        if ".hyperframes" in rel.parts or f.name.startswith("."):
            continue
        if rel.parent == Path(".") and f.name.startswith("index.") and f.name not in ("index.html", entry["file"]):
            continue
        out[rel.as_posix()] = sha256_file(f)
    return out


def render_fingerprint(pdir: Path, entry: Dict[str, Any], fps: int, quality: str,
                       inputs: Optional[Dict[str, str]] = None) -> str:
    """Hash of everything a format's visuals depend on: the composition tree plus render settings."""
    h = hashlib.sha256()
    h.update(f"{entry['id']}|{entry['file']}|{entry['width']}x{entry['height']}|{fps}|{quality}".encode())
    for rel, digest in (inputs if inputs is not None else render_inputs(pdir, entry)).items():
        h.update(rel.encode())
        h.update(digest.encode())
    return h.hexdigest()


def render_stamp_state(pdir: Path, fid: str, fingerprint: str) -> str:
    """'missing' (no render), 'unstamped' (render predates stamps), 'current' or 'stale'."""
    base = pdir / "renders" / fid
    if not (base / "visuals.mp4").exists():
        return "missing"
    stamp = base / STAMP_NAME
    if not stamp.exists():
        return "unstamped"
    try:
        return "current" if load_json(stamp).get("fingerprint") == fingerprint else "stale"
    except (OSError, ValueError):
        return "stale"


def write_render_stamp(pdir: Path, fid: str, fingerprint: str, inputs: Optional[Dict[str, str]] = None,
                       extra: Optional[Dict[str, Any]] = None) -> None:
    hf = ""
    try:
        hf = subprocess.run(["hyperframes", "--version"], capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    stamp = {
        "fingerprint": fingerprint,
        "hyperframes": hf,
        "rendered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if inputs is not None:
        stamp["inputs"] = inputs  # lets a later archive say which files made this render stale
    stamp.update(extra or {})
    write_json(pdir / "renders" / fid / STAMP_NAME, stamp)


def delivered_path(pdir: Path, project: Dict[str, Any], fid: str) -> Path:
    """Where `build` copies a format's finished file: out/<slug>-<format>.mp4."""
    deliv_slug = project.get("slug") or (f"{pdir.parent.name}-{pdir.name}" if pdir.parent != PROJECTS_DIR else pdir.name)
    return OUT_DIR / f"{deliv_slug}-{fid}.mp4"


def changed_inputs(old: Optional[Dict[str, str]], new: Optional[Dict[str, str]]) -> Optional[List[str]]:
    """Paths under src/ that differ between two input maps; None when either side is unknown."""
    if old is None or new is None:
        return None
    return sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))


def archive_render(pdir: Path, fid: str, reason: str, inputs: Optional[Dict[str, str]] = None) -> Optional[Path]:
    """Move a format's superseded render out of the way instead of overwriting it.

    renders/<fid>/{visuals.mp4, final.mp4, visuals.stamp.json} move to renders/history/<fid>/<when>/, and the
    delivered out/<slug>-<fid>.mp4 moves to out/archive/<slug>-<fid>.<when>.mp4. <when> is the old render's
    time (its stamp, else the file's mtime). A history.json beside them records the reason and, when the old
    stamp listed its inputs, which src/ files changed. Returns the history folder, or None when nothing to move.
    """
    base = pdir / "renders" / fid
    moving = [n for n in ("visuals.mp4", "final.mp4", STAMP_NAME, "visuals.prev.mp4") if (base / n).exists()]
    if not any(n.endswith(".mp4") for n in moving):
        return None
    stamp: Dict[str, Any] = {}
    if (base / STAMP_NAME).exists():
        try:
            stamp = load_json(base / STAMP_NAME)
        except (OSError, ValueError):
            stamp = {}
    video = base / ("visuals.mp4" if "visuals.mp4" in moving else "final.mp4")
    try:
        when = datetime.fromisoformat(stamp["rendered_at"]).astimezone(timezone.utc)
    except (KeyError, TypeError, ValueError):
        when = datetime.fromtimestamp(video.stat().st_mtime, timezone.utc)
    label = when.strftime("%Y%m%dT%H%M%SZ")
    dest = base.parent / HISTORY_DIRNAME / fid / label
    n = 1
    while dest.exists():
        n += 1
        dest = base.parent / HISTORY_DIRNAME / fid / f"{label}-{n}"
    dest.mkdir(parents=True)
    moved = {}
    for name in moving:
        shutil.move(str(base / name), str(dest / name))
        moved[name] = rel_path(base / name)
    project = load_json(pdir / "project.json") if (pdir / "project.json").exists() else {}
    out = delivered_path(pdir, project, fid)
    if out.exists():
        target = out.parent / "archive" / f"{out.stem}.{dest.name}{out.suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(out), str(target))
        moved[rel_path(target)] = rel_path(out)
    write_json(dest / "history.json", {
        "format": fid,
        "reason": reason,
        "archived_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rendered_at": stamp.get("rendered_at") or when.isoformat(timespec="seconds"),
        "fingerprint": stamp.get("fingerprint"),
        "changed_inputs": changed_inputs(stamp.get("inputs"), inputs),
        "moved_from": moved,
    })
    return dest


def render_states(pdir: Path, quality: Optional[str] = None) -> List[Dict[str, Any]]:
    """Per format: {format, state (missing|unstamped|current|stale), changed (src/ paths or None), inputs}."""
    project = load_json(pdir / "project.json")
    q = quality or project.get("quality", "looks")
    rows = []
    for entry in format_entries(project):
        inputs = render_inputs(pdir, entry)
        state = render_stamp_state(pdir, entry["id"], render_fingerprint(pdir, entry, project["fps"], q, inputs))
        changed = None
        if state == "stale":
            try:
                changed = changed_inputs(load_json(pdir / "renders" / entry["id"] / STAMP_NAME).get("inputs"), inputs)
            except (OSError, ValueError):
                pass
        rows.append({"format": entry["id"], "state": state, "changed": changed, "inputs": inputs})
    return rows


def render_lock(slug: str):
    """The render-host lock from scripts/session-guard.py (re-entrant when an ancestor holds it)."""
    spec = importlib.util.spec_from_file_location("session_guard", REPO_ROOT / "scripts" / "session-guard.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.acquire_lock(mod.RESOURCE_RENDER, slug=slug)


def max_process_rss_mb() -> float:
    """RSS of the largest single finished child so far (bytes on macOS, KB on Linux). Not a tree sum: Chrome helpers are not added up, so this under-reports the memory of a render."""
    raw = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return round(raw / (1024 * 1024 if sys.platform == "darwin" else 1024), 1)


def log_build_timings(slug: str, stages: List[Dict[str, Any]], ok: bool) -> None:
    """One JSON line per build in logs/build-timings.jsonl (gitignored): the only render-time record."""
    try:
        TIMINGS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with TIMINGS_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"slug": slug, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "ok": ok, "stages": stages}) + "\n")
    except OSError:
        pass


def narration_args(project: Dict[str, Any]) -> Dict[str, Any]:
    """project.json's narration settings as keyword arguments for narration.resolve_request."""
    a = project["audio"]
    return {"voice": a.get("voice"), "speed": a.get("speed"), "prosody": a.get("prosody"), "preset": a.get("prosody_preset")}


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
    # formats first: a preset or project.json change regenerates the entry files instead of failing validate
    steps.append({"stage": "formats", "cmd": [sys.executable, "scripts/studio.py", "formats", pdir.name], "cwd": "."})
    steps.append({"stage": "validate", "cmd": [sys.executable, "scripts/studio.py", "validate", pdir.name], "cwd": "."})
    if project["audio"]["narration"]:
        narr = [sys.executable, "scripts/build-audio.py", pdir.name]
        if project["audio"].get("voice"):
            narr += ["--voice", project["audio"]["voice"]]
        if project["audio"].get("speed"):
            narr += ["--speed", f"{project['audio']['speed']:g}"]
        if project["audio"].get("prosody"):
            narr += ["--prosody", project["audio"]["prosody"]]
        if project["audio"].get("prosody_preset"):
            narr += ["--preset", project["audio"]["prosody_preset"]]
        # skipped only when audio/timeline.json records the current script, voice, speed and prosody (see run_build_plan)
        steps.append({"stage": "narration", "cmd": narr, "cwd": ".", "narration_args": narration_args(project)})
    steps.append({"stage": "lint", "cmd": ["hyperframes", "lint", "."], "cwd": rel(pdir / "src")})
    target = project.get("audio", {}).get("loudness_target_lufs")
    tol = project.get("audio", {}).get("loudness_tolerance_lu", 2)
    for entry in format_entries(project):
        if only and entry["id"] not in only:
            continue
        fid = entry["id"]
        # render to a partial file and rename it on success, so a killed render never leaves a truncated visuals.mp4
        partial = f"../renders/{fid}/{PARTIAL_NAME}"
        inputs = render_inputs(pdir, entry)
        steps.append({"stage": f"render:{fid}", "cmd": ["hyperframes", "render", ".", "--composition", entry["file"], "--fps", str(project["fps"]), "--quality", q, "--low-memory-mode", "--output", partial], "cwd": rel(pdir / "src"), "requires_missing": rel(pdir / "renders" / fid / "visuals.mp4"),
                      "promote": [rel(pdir / "renders" / fid / PARTIAL_NAME), rel(pdir / "renders" / fid / "visuals.mp4")],
                      "fingerprint": render_fingerprint(pdir, entry, project["fps"], q, inputs), "inputs": inputs,
                      "fingerprint_of": {"entry": entry, "fps": project["fps"], "quality": q}})
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
            mix = ";".join(filters) + ";" + "".join(labels) + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=2"
            if target is not None:
                mix += f",loudnorm=I={target:g}:TP=-1.5:LRA=11,aresample=48000[aout]"  # loudnorm upsamples to 192 kHz; deliver 48 kHz
            else:
                mix += "[aout]"
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
        steps.append({"stage": f"deliver:{fid}", "cmd": ["copy", rel(pdir / "renders" / fid / "final.mp4"), rel(delivered_path(pdir, project, fid))], "cwd": "."})
    if any(s["stage"].startswith("deliver:") for s in steps):
        # poster.jpg = last non-black frame of the primary format's film; the catalogue shows it on the project's tile
        steps.append({"stage": "poster", "cmd": [sys.executable, "scripts/poster.py", rel(pdir), "--force"], "cwd": "."})
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
        with render_lock(pdir.name):
            return subprocess.run(plan[0]["cmd"], cwd=REPO_ROOT).returncode
    missing = [tool for tool in ("hyperframes", "ffmpeg", "ffprobe") if not shutil.which(tool)]
    if missing:
        print(f"Error: required tools not on PATH: {', '.join(missing)}. Use --dry-run to print the plan, or run on the render host.")
        return 1
    with render_lock(pdir.name):
        return run_build_plan(pdir, plan, allow_narration_shift=args.allow_narration_shift)


def run_build_plan(pdir: Path, plan: List[Dict[str, Any]], allow_narration_shift: bool = False) -> int:
    timings: List[Dict[str, Any]] = []
    for s in plan:
        cwd = REPO_ROOT / s["cwd"]
        old_timeline = None
        if s.get("requires") and not (REPO_ROOT / s["requires"]).exists():
            print(f"[skip] {s['stage']}: {s['requires']} not found")
            continue
        if s.get("narration_args") is not None:
            nar = pipeline_module("narration")
            state, reasons = nar.narration_state(pdir, nar.resolve_request(pdir, **s["narration_args"]))
            if state == "current":
                print(f"[skip] {s['stage']}: audio/narration-full.wav matches src/narration.json, voice and speed")
                continue
            if state == "unknown":
                print(f"[skip] {s['stage']}: audio/narration-full.wav reused unchecked ({reasons[0]}); "
                      f"`python scripts/build-audio.py {pdir.name} --force` re-synthesises it")
                continue
            print(f"[{state}] {s['stage']}: {'; '.join(reasons)}")
            if state == "stale" and (pdir / "audio" / "timeline.json").exists():
                old_timeline = load_json(pdir / "audio" / "timeline.json")
        elif s.get("fingerprint"):
            fid = s["stage"].split(":", 1)[1]
            if s.get("fingerprint_of"):  # earlier stages (formats) may have rewritten the entry file since the plan was made
                f = s["fingerprint_of"]
                s["inputs"] = render_inputs(pdir, f["entry"])
                s["fingerprint"] = render_fingerprint(pdir, f["entry"], f["fps"], f["quality"], s["inputs"])
            state = render_stamp_state(pdir, fid, s["fingerprint"])
            if state == "current":
                print(f"[skip] {s['stage']}: renders/{fid}/visuals.mp4 matches the current composition")
                continue
            if state == "unstamped":
                print(f"[skip] {s['stage']}: renders/{fid}/visuals.mp4 exists but has no build stamp, so it cannot be checked against the composition; "
                      f"`python scripts/studio.py renders {pdir.name} --archive --unstamped` moves it to renders/history/ and the next build re-renders")
                continue
            if state == "stale":
                dest = archive_render(pdir, fid, "stale at build", s.get("inputs"))
                print(f"[stale] {s['stage']}: composition, assets or settings changed since renders/{fid}/visuals.mp4 was rendered; "
                      f"previous render moved to {rel_path(dest) if dest else 'nowhere (nothing to move)'}; re-rendering")
        elif s.get("requires_missing") and (REPO_ROOT / s["requires_missing"]).exists():
            print(f"[skip] {s['stage']}: {s['requires_missing']} already exists")
            continue
        print(f"[{s['stage']}] " + " ".join(s["cmd"]))
        started = time.monotonic()
        if s["cmd"][0] == "copy":
            dst = REPO_ROOT / s["cmd"][2]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / s["cmd"][1], dst)
            continue
        if s["stage"].startswith("render:"):
            (pdir / "renders" / s["stage"].split(":", 1)[1]).mkdir(parents=True, exist_ok=True)
        if s.get("promote"):
            (REPO_ROOT / s["promote"][0]).unlink(missing_ok=True)  # a leftover from a killed render
        if s["stage"] == "lint":
            stashed = []
            for vf in cwd.glob("index.*.html"):
                if vf.name != "index.html":
                    tmp = vf.with_name("." + vf.name + ".lint-stash")
                    vf.rename(tmp)
                    stashed.append((tmp, vf))
            try:
                res = subprocess.run(s["cmd"], cwd=cwd, stdin=subprocess.DEVNULL)
            finally:
                for tmp, orig in stashed:
                    tmp.rename(orig)
        else:
            res = subprocess.run(s["cmd"], cwd=cwd, stdin=subprocess.DEVNULL)
        timings.append({"stage": s["stage"], "sec": round(time.monotonic() - started, 1), "exit": res.returncode, "max_process_rss_mb": max_process_rss_mb()})
        if res.returncode != 0:
            log_build_timings(pdir.name, timings, ok=False)
            print(f"Error: stage {s['stage']} failed with exit code {res.returncode}.")
            return res.returncode
        if s.get("promote"):
            src, dst = (REPO_ROOT / p for p in s["promote"])
            if not src.exists():
                log_build_timings(pdir.name, timings, ok=False)
                print(f"Error: stage {s['stage']} exited 0 but wrote no {s['promote'][0]}.")
                return 1
            src.replace(dst)
        if old_timeline is not None:
            fps = load_json(pdir / "project.json").get("fps", 30)
            shifts = pipeline_module("narration").scene_shifts(old_timeline, load_json(pdir / "audio" / "timeline.json"), 1.0 / fps)
            if shifts and not allow_narration_shift:
                log_build_timings(pdir.name, timings, ok=False)
                print("Error: the new narration moved scene timing, so cue times copied into src/ from the old audio/timeline.json "
                      "would play against the wrong words:\n  " + "\n  ".join(shifts) +
                      f"\nRe-time the composition (`studio.py words {pdir.name} \"<phrase>\"` gives film times), then build again; "
                      "pass --allow-narration-shift if the composition reads its times from the timeline. The previous audio is in audio/history/.")
                return 3
        if s.get("fingerprint"):
            write_render_stamp(pdir, s["stage"].split(":", 1)[1], s["fingerprint"], s.get("inputs"))
    log_build_timings(pdir.name, timings, ok=True)
    print("Build complete. Technical QA ran per format; creative review is separate: python scripts/studio.py review " + pdir.name)
    return 0


# --------------------------------------------------------------------------- render history and upgrades
def all_studio_projects() -> List[Path]:
    """Every studio project, including versioned ones one level down (projects/<group>/<version>/); never archive/."""
    found = list(PROJECTS_DIR.glob("*/project.json")) + list(PROJECTS_DIR.glob("*/*/project.json"))
    return sorted(p.parent for p in found if "archive" not in p.relative_to(PROJECTS_DIR).parts)


def project_label(pdir: Path) -> str:
    return pdir.relative_to(PROJECTS_DIR).as_posix() if PROJECTS_DIR in pdir.parents else pdir.name


def cmd_renders(args: argparse.Namespace) -> int:
    targets = [project_dir(s) for s in args.slugs] if args.slugs else all_studio_projects()
    moved = 0
    for pdir in targets:
        if not (pdir / "project.json").exists():
            print(f"{project_label(pdir)}: legacy project (no project.json); renders are not stamped")
            continue
        for row in render_states(pdir, args.quality):
            fid, state = row["format"], row["state"]
            note = ""
            if state == "stale" and row["changed"] is not None:
                shown = ", ".join(row["changed"][:4]) + (f" (+{len(row['changed']) - 4} more)" if len(row["changed"]) > 4 else "")
                note = f" (changed: {shown or 'render settings only'})"
            if args.archive and (state == "stale" or (state == "unstamped" and args.unstamped)):
                dest = archive_render(pdir, fid, f"{state}, archived by `studio.py renders --archive`", row["inputs"])
                if dest:
                    moved += 1
                    note += f" -> moved to {rel_path(dest)}"
            print(f"{project_label(pdir)} [{fid}]: {state}{note}")
    if args.archive:
        print(f"{moved} render(s) moved to renders/{HISTORY_DIRNAME}/; the next `studio.py build` renders them again.")
    return 0


def cmd_upgrade(args: argparse.Namespace) -> int:
    """Bring projects onto the current runtime and format presets, and move the renders that supersedes to history.

    An upgrade is never held back because it makes earlier videos stale: those videos move to
    renders/history/<format>/<when>/ (and out/archive/) with a history.json naming the change, and the next
    build renders the format again."""
    if not args.slugs and not args.all:
        raise SystemExit("Error: name one or more projects, or pass --all.")
    targets = [project_dir(s) for s in args.slugs] if args.slugs else all_studio_projects()
    failed = 0
    for pdir in targets:
        label = project_label(pdir)
        if not (pdir / "project.json").exists():
            print(f"{label}: legacy project, skipped")
            continue
        project = load_json(pdir / "project.json")
        entries = format_entries(project)
        before = {e["id"]: render_inputs(pdir, e) for e in entries}
        old_version = load_json(lock_path(pdir)).get("runtime_version") if lock_path(pdir).exists() else None
        with contextlib.redirect_stdout(io.StringIO()) as quiet:
            rc = cmd_sync(argparse.Namespace(slug=str(pdir), force=args.force))
        if rc != 0:
            failed += 1
            print(f"{label}: not upgraded. {quiet.getvalue().strip()}")
            continue
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                cmd_formats(argparse.Namespace(slug=str(pdir), size=None))
        except ValueError as exc:
            failed += 1
            print(f"{label}: runtime synced, but the format entry files could not be generated: {exc}")
            continue
        parts = []
        for e in entries:
            after = render_inputs(pdir, e)
            changed = changed_inputs(before[e["id"]], after) or []
            fp = render_fingerprint(pdir, e, project["fps"], project.get("quality", "looks"), after)
            state = render_stamp_state(pdir, e["id"], fp)
            if state == "current" or (not changed and state != "stale"):
                parts.append(f"{e['id']} {'changed, but its render already matches' if changed else 'unchanged'} ({state})")
                continue
            if args.keep_renders or state == "missing":
                parts.append(f"{e['id']} changed ({len(changed)} file(s)); render {state}")
                continue
            if state in ("stale", "unstamped"):
                dest = archive_render(pdir, e["id"], f"superseded by upgrade (runtime {old_version} -> {runtime_version()}; "
                                      f"changed: {', '.join(changed[:6]) or 'render settings'})", after)
                parts.append(f"{e['id']} changed ({len(changed)} file(s)); previous render moved to {rel_path(dest)}" if dest
                             else f"{e['id']} changed ({len(changed)} file(s))")
        errors = validate_project(pdir).errors
        tail = f"; validate: {len(errors)} error(s), first: {errors[0]}" if errors else ""
        print(f"{label}: runtime {old_version} -> {runtime_version()}; " + "; ".join(parts) + tail)
    print(f"{len(targets) - failed} of {len(targets)} project(s) upgraded. Re-render with `python scripts/studio.py build <slug>` (one at a time).")
    return 1 if failed else 0


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


def captions_approx(args: argparse.Namespace) -> int:
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


def transcribe_clip(clip: Path, slug: str, model: str) -> List[Dict[str, Any]]:
    """Word times for one narration clip from the local `hyperframes transcribe`, under the analysis lock.

    The recogniser writes transcript.json into --dir, so it gets a throwaway folder and the project stays clean."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix="studio-asr-") as tmp:
        cmd = [sys.executable, str(REPO_ROOT / "scripts" / "session-guard.py"), "run", "--slug", slug, "analysis", "--",
               "hyperframes", "transcribe", str(clip.resolve()), "--dir", tmp, "--json", "--no-runtime-install", "--model", model]
        r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        out = Path(tmp) / "transcript.json"
        if r.returncode != 0 or not out.exists():
            raise SystemExit(f"Error: transcription of {clip.name} failed.\n{(r.stderr or r.stdout)[-600:]}")
        return [{"text": w["text"], "start": w["start"], "end": w["end"]} for w in load_json(out)]


def cmd_captions(args: argparse.Namespace) -> int:
    """Captions from the narration. Default: approximate sentence cues. --timing words: measured word times."""
    # older callers pass only the slug, so every new option has a default
    timing, grouping = getattr(args, "timing", "approx"), getattr(args, "grouping", "sentence")
    model, max_words, retranscribe = getattr(args, "model", "small.en"), getattr(args, "max_words", 3), getattr(args, "retranscribe", False)
    if timing == "approx" and grouping == "sentence":
        return captions_approx(args)
    if timing == "approx":
        raise SystemExit("Error: phrase grouping needs measured word times; add --timing words.")
    pdir = project_dir(args.slug)
    tl_path = pdir / "audio" / "timeline.json"
    if not tl_path.exists():
        raise SystemExit("Error: audio/timeline.json not found; synthesise narration first (scripts/build-audio.py).")
    caps = pipeline_module("captions")
    timeline = load_json(tl_path)
    words_path = pdir / "audio" / "words.json"
    cached = load_json(words_path) if words_path.exists() else {}
    asr_all: Dict[str, Any] = {}
    clips: Dict[str, str] = {}
    scene_words: Dict[str, Any] = {}
    coverage: Dict[str, float] = {}
    cues: List[Dict[str, Any]] = []
    for sc in timeline["scenes"]:
        sid = sc["id"]
        clip = pdir / sc["clip_path"]
        if not clip.exists():
            raise SystemExit(f"Error: {clip} not found.")
        sha = sha256_file(clip)
        asr = cached.get("asr", {}).get(sid)
        if retranscribe or asr is None or cached.get("clips", {}).get(sid) != sha or cached.get("model") != model:
            print(f"  transcribing {sid} ({sc['duration_sec']:.1f}s) with {model} ...")
            asr = transcribe_clip(clip, pdir.name, model)
        asr_all[sid], clips[sid] = asr, sha
        tokens = caps.tokenize(sc["text"])
        local, cov = caps.align(tokens, asr, (0.0, float(sc["duration_sec"])))
        off = float(sc["start_time_sec"])
        film = [(a + off, b + off) for a, b in local]
        coverage[sid] = round(cov, 2)
        scene_words[sid] = [{"text": t["text"], "start": round(a, 3), "end": round(b, 3)} for t, (a, b) in zip(tokens, film)]
        if grouping == "phrase":
            cues += caps.phrases(tokens, film, max_words=max_words)
        else:
            cues += caps.sentence_cues(tokens, film)
    # Cache first: a problem below must not cost the transcription again.
    write_json(words_path, {"spec_version": 1, "engine": "hyperframes transcribe (whisper)", "model": model,
                            "note": "Word times in film seconds, aligned to the script text. `asr` is the raw recogniser output per scene clip; clips holds each clip's sha256 so unchanged scenes are not transcribed again.",
                            "scenes": scene_words, "asr": asr_all, "clips": clips, "coverage": coverage})
    problems = caps.check_cues(cues)
    if problems:
        raise SystemExit("Error: caption cues are inconsistent: " + "; ".join(problems[:3]))
    head = ("// GENERATED by scripts/studio.py captions --timing words from audio/words.json.\n"
            f"// Word times are measured ({model}) and aligned to the script; grouping: {grouping}.\n"
            "// Each cue carries its words, so Studio.comp.captions highlights the word being spoken.\n")
    (pdir / "src" / "captions.js").write_text(head + "window.STUDIO_CAPTIONS = " + json.dumps(cues, indent=2, ensure_ascii=False) + ";\n", encoding="utf-8", newline="\n")
    out = pdir / "captions"
    out.mkdir(exist_ok=True)
    lines = ["WEBVTT", ""]
    for i, c in enumerate(cues, 1):
        lines += [str(i), f"{vtt_time(c['start'])} --> {vtt_time(c['end'])}", c["text"], ""]
    (out / f"{pdir.name}.vtt").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    low = {k: v for k, v in coverage.items() if v < 0.8}
    print(f"Wrote {len(cues)} {grouping} cues with measured word times to src/captions.js, captions/{pdir.name}.vtt and audio/words.json")
    print("  recogniser match per scene: " + ", ".join(f"{k} {v:.0%}" for k, v in coverage.items()))
    if low:
        print(f"  WARN: scenes {', '.join(low)} matched under 80% of the script; unmatched words were interpolated. Listen to those scenes.")
    return 0


def cmd_words(args: argparse.Namespace) -> int:
    """Film time at which a phrase is spoken, to snap a storyboard beat or a visual to its noun."""
    pdir = project_dir(args.slug)
    wp = pdir / "audio" / "words.json"
    if not wp.exists():
        raise SystemExit("Error: audio/words.json not found; run `studio.py captions <slug> --timing words` first.")
    hits = pipeline_module("captions").word_index(load_json(wp)["scenes"], args.phrase)
    if not hits:
        print(f"'{args.phrase}' is not in the narration.")
        return 1
    for h in hits:
        print(f"{h['start']:7.2f}s - {h['end']:7.2f}s  scene {h['scene']}: {h['text']}")
    return 0


def cmd_script(args: argparse.Namespace) -> int:
    """Timed sentence sheet, hook and rhythm checks, and the story proposal table. Lint only: exit 0."""
    sl = pipeline_module("scriptlint")
    rep = sl.script_report(project_dir(args.slug), wps=args.wps)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(sl.render_text(rep, sheet=not args.no_sheet))
    return 0


def cmd_hook(args: argparse.Namespace) -> int:
    hk = pipeline_module("hooks")
    if args.hook_command == "formulas":
        for f in hk.formulas_for(args.category):
            print(f"{f['id']:<26} {f['name']}  [{', '.join(f.get('best_for', []))}]")
            print(f"    template: {f['template']}")
            print(f"    example:  {f['example']}")
            print(f"    fails when: {f['fails_when']}")
        return 0
    lines = list(args.lines)
    if args.file:
        lines += [ln.strip() for ln in Path(args.file).read_text(encoding="utf-8").splitlines() if ln.strip()]
    if args.slug:
        sl = pipeline_module("scriptlint")
        rows, _ = sl.sentence_rows(sl.load_inputs(project_dir(args.slug)), args.wps)
        if rows:
            lines.append(rows[0]["text"])
            print(f"(project hook = first sentence of {args.slug}: \"{rows[0]['text']}\")")
    if not lines:
        raise SystemExit("Error: give at least one hook line, --file, or --slug.")
    for i, r in enumerate(hk.rank(lines, args.wps), 1):
        print(f"{i}. {r['score']:3d}/100 {r['verdict']:<6} {r['spoken_sec']:.1f}s  {('formula: ' + r['formula']) if r['formula'] else 'no formula matched'}")
        print(f"   \"{r['text']}\"")
        print("   points: " + ", ".join(f"{k} {v:g}/{hk.WEIGHTS[k]}" for k, v in r["points"].items()))
        for n in r["notes"]:
            print(f"   - {n}")
    print("\nA lint, not a prediction: it catches greetings, preambles, vague lines and slow openings. "
          "Pick from three hooks written from different formulas (`studio.py hook formulas`).")
    return 0


# --------------------------------------------------------------------------- review
def cmd_poster(args: argparse.Namespace) -> int:
    """Poster (last non-black frame of the finished film) for one project, or every project with --all."""
    cmd = [sys.executable, str(SCRIPTS_DIR / "poster.py")]
    if args.all:
        cmd.append("--all")
    elif args.slug:
        cmd.append(str(project_dir(args.slug)))
    else:
        raise SystemExit("Error: name a project or pass --all.")
    if args.force:
        cmd.append("--force")
    return subprocess.run(cmd, stdin=subprocess.DEVNULL).returncode


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


# --------------------------------------------------------------------------- series
def series_dir(slug: str) -> Path:
    return SERIES_DIR / slug


def load_series(slug: str) -> Dict[str, Any]:
    path = series_dir(slug) / "series.json"
    if not path.exists():
        avail = ", ".join(sorted(p.parent.name for p in SERIES_DIR.glob("*/series.json"))) or "none"
        raise SystemExit(f"Error: series '{slug}' not found (series/{slug}/series.json). Available: {avail}")
    return load_json(path)


def all_series() -> List[Dict[str, Any]]:
    return [load_json(p) for p in sorted(SERIES_DIR.glob("*/series.json"))]


def series_containing(pdir: Path) -> List[Dict[str, Any]]:
    """Series whose members resolve to this project folder."""
    out = []
    for ser in all_series():
        if any(find_project(m["project"]) == pdir.resolve() for m in ser.get("members", [])):
            out.append(ser)
    return out


def member_video_type(m: Dict[str, Any]) -> Optional[str]:
    """A series member's video type: its brief's when the project exists, else the planned one."""
    pdir = find_project(m["project"])
    if pdir is not None and (pdir / "brief.json").exists():
        return load_json(pdir / "brief.json").get("deliverables", {}).get("video_type")
    return m.get("video_type")


def validate_series(ser: Dict[str, Any], folder: str) -> Report:
    rep = Report()
    for e in schema_errors(ser, SPECS_DIR / "series-spec.json"):
        rep.error(e)
    if rep.errors:
        return rep
    if ser["slug"] != folder:
        rep.error(f"series slug '{ser['slug']}' does not match folder 'series/{folder}'.")
    bad = unknown_categories(ser["categories"])
    if bad:
        rep.error(f"series categories {bad} are not in specs/categories.json.")
    records = catalogue_records()
    style = ser.get("style")
    if style and style not in records.get("styles", {}):
        rep.error(f"series style '{style}' is not registered (catalogue/data/styles/).")
    members = ser["members"]
    if not members:
        rep.warn("series has no members yet (series add).")
    refs = [m["project"] for m in members]
    if len(set(refs)) != len(refs):
        rep.error("a project is listed more than once.")
    if ser["kind"] == "sequential":
        parts = [m.get("part") for m in members]
        if any(p is None for p in parts):
            rep.error("every member of a sequential series needs a 'part' number.")
        else:
            if len(set(parts)) != len(parts):
                rep.error(f"part numbers repeat: {sorted(parts)}.")
            elif sorted(parts) != list(range(1, len(parts) + 1)):
                rep.warn(f"part numbers {sorted(parts)} are not 1..{len(parts)}; a part is missing or skipped.")
    else:
        if any("part" in m for m in members):
            rep.error("a collection has no order; remove 'part' from members (or make the series sequential).")
    for m in members:
        ref = m["project"]
        pdir = find_project(ref)
        if pdir is None:
            if m.get("status") == "planned":
                rep.note(f"{ref}: planned (no project folder yet).")
            else:
                rep.error(f"{ref}: no such project under projects/ (mark it status 'planned' if it is not started).")
            continue
        brief_path = pdir / "brief.json"
        if brief_path.exists():
            btype = load_json(brief_path).get("deliverables", {}).get("video_type")
            if m.get("video_type") and btype and m["video_type"] != btype:
                rep.warn(f"{ref}: series says video_type '{m['video_type']}', the brief says '{btype}'; the brief wins.")
            bcats = load_json(brief_path).get("categories") or []
            if bcats and not set(bcats) & set(ser["categories"]):
                rep.warn(f"{ref}: brief categories {bcats} share nothing with the series' {ser['categories']}.")
        pj = pdir / "project.json"
        if style and pj.exists():
            pstyle = load_json(pj).get("style")
            if pstyle != style:
                rep.warn(f"{ref}: uses style '{pstyle}', the series style is '{style}'.")
    return rep


def print_report(title: str, rep: Report) -> None:
    print("=" * 70)
    print(title)
    print("=" * 70)
    for i in rep.info:
        print(f"  [INFO] {i}")
    for w in rep.warnings:
        print(f"  [WARN] {w}")
    for e in rep.errors:
        print(f"  [FAIL] {e}")
    print("-" * 70)
    print("[PASS] Series is consistent." if rep.ok else f"[FAIL] {len(rep.errors)} error(s).")


def sorted_members(ser: Dict[str, Any]) -> List[Dict[str, Any]]:
    return sorted(ser["members"], key=lambda m: m.get("part", 0))


def cmd_series(args: argparse.Namespace) -> int:
    return SERIES_HANDLERS[args.series_command](args)


def cmd_series_new(args: argparse.Namespace) -> int:
    slug = args.slug
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        raise SystemExit("Error: slug must be kebab-case (a-z, 0-9, hyphens).")
    sdir = series_dir(slug)
    if sdir.exists():
        raise SystemExit(f"Error: {rel_path(sdir)} already exists.")
    cats = parse_category_arg(args.category)
    if not cats:
        raise SystemExit(f"Error: --category is required (one or more of: {', '.join(load_categories())}).")
    ser: Dict[str, Any] = {
        "spec_version": 1, "slug": slug, "title": args.title or slug.replace("-", " ").title(),
        "description": "TODO: the arc across parts, or the theme that ties the projects together.",
        "kind": args.kind, "categories": cats,
    }
    if args.style:
        ser["style"] = args.style
    ser["members"] = []
    write_json(sdir / "series.json", ser)
    print(f"Created {rel_path(sdir / 'series.json')} ({args.kind}, {', '.join(cats)}).")
    print(f"Next: python scripts/studio.py series add {slug} <project>" + (" [--part N]" if args.kind == "sequential" else ""))
    return 0


def cmd_series_add(args: argparse.Namespace) -> int:
    ser = load_series(args.series)
    if any(m["project"] == args.project for m in ser["members"]):
        raise SystemExit(f"Error: '{args.project}' is already in series '{args.series}'.")
    member: Dict[str, Any] = {"project": args.project}
    if ser["kind"] == "sequential":
        used = {m["part"] for m in ser["members"] if "part" in m}
        part = args.part or max(used, default=0) + 1
        if part in used:
            raise SystemExit(f"Error: part {part} is already taken in '{args.series}'.")
        member["part"] = part
    elif args.part:
        raise SystemExit("Error: --part only applies to a sequential series.")
    if args.title:
        member["title"] = args.title
    if args.planned:
        member["status"] = "planned"
    elif find_project(args.project) is None:
        raise SystemExit(f"Error: project '{args.project}' not found under projects/ (use --planned if it is not started).")
    if getattr(args, "video_type", None):
        member["video_type"] = args.video_type
    ser["members"].append(member)
    ser["members"] = sorted_members(ser) if ser["kind"] == "sequential" else ser["members"]
    write_json(series_dir(args.series) / "series.json", ser)
    where = f" as part {member['part']}" if "part" in member else ""
    print(f"Added {args.project} to {args.series}{where}.")
    return 0


def cmd_series_show(args: argparse.Namespace) -> int:
    ser = load_series(args.slug)
    print(f"{ser['title']}  [{ser['slug']}]  {ser['kind']}  categories: {', '.join(ser['categories'])}"
          + (f"  style: {ser['style']}" if ser.get("style") else ""))
    if ser.get("description"):
        print(f"  {ser['description']}")
    for i, m in enumerate(sorted_members(ser), 1):
        lead = f"part {m['part']}" if "part" in m else f"#{i}"
        print(f"  {lead:<8} {m['project']:<44} {member_video_type(m) or 'untyped':<10} {m.get('status', 'in-production'):<14} {m.get('title', '')}")
    if not ser["members"]:
        print("  (no members)")
    return 0


def cmd_series_list(args: argparse.Namespace) -> int:
    rows = all_series()
    if not rows:
        print("No series yet. Create one: python scripts/studio.py series new <slug> --kind sequential|collection --category <c>")
    for ser in rows:
        print(f"{ser['slug']:<32} {ser['kind']:<11} {len(ser['members'])} project(s)  {', '.join(ser['categories'])}")
    return 0


def cmd_series_validate(args: argparse.Namespace) -> int:
    slugs = [args.slug] if args.slug else [p.parent.name for p in sorted(SERIES_DIR.glob("*/series.json"))]
    if not slugs:
        print("No series to validate.")
        return 0
    worst = 0
    for slug in slugs:
        rep = validate_series(load_series(slug), slug)
        print_report(f"SERIES VALIDATION: {slug}", rep)
        worst = max(worst, 0 if rep.ok else 1)
    return worst


SERIES_HANDLERS = {
    "new": cmd_series_new, "add": cmd_series_add, "show": cmd_series_show,
    "list": cmd_series_list, "validate": cmd_series_validate,
}


# --------------------------------------------------------------------------- style templates
def studio_projects() -> List[Path]:
    """Every studio project (project.json present), top level of projects/ only."""
    return sorted(p.parent for p in PROJECTS_DIR.glob("*/project.json"))


def get_style_template(records: Dict[str, Dict[str, Any]], tid: str) -> Dict[str, Any]:
    tpl = records.get("style-templates", {}).get(tid)
    if not tpl:
        raise SystemExit(f"Error: style template '{tid}' not found. Available: {', '.join(records.get('style-templates', {})) or 'none'}")
    return tpl


def cmd_style(args: argparse.Namespace) -> int:
    return STYLE_HANDLERS[args.style_command](args)


def cmd_style_list(args: argparse.Namespace) -> int:
    records = catalogue_records()
    used: Dict[str, int] = {}
    for pdir in studio_projects():
        pin = load_json(pdir / "project.json").get("style_template")
        if pin:
            used[pin["id"]] = used.get(pin["id"], 0) + 1
    print(f"{'id':<20} {'ver':<4} {'visual job':<14} {'default style':<16} {'status':<13} {'categories':<28} projects")
    for tid, t in records.get("style-templates", {}).items():
        print(f"{tid:<20} v{t['version']:<3} {t['visual_job']['kind']:<14} {t['look']['style']:<16} {t['status']:<13} "
              f"{', '.join(t['selection']['categories']):<28} {used.get(tid, 0)}")
    return 0


def cmd_style_show(args: argparse.Namespace) -> int:
    t = get_style_template(catalogue_records(), args.id)
    print(f"{t['name']} [{t['id']}]  v{t['version']}  {t['status']}")
    print(t["summary"], "\n")
    print(f"Visual job:   {t['visual_job']['kind']}. The viewer leaves able to: {t['visual_job']['viewer_leaves_able_to']}")
    print(f"Hero:         {t['visual_job']['hero']}")
    print(f"Use when:     " + "\n              ".join(t["selection"]["use_when"]))
    print(f"Avoid when:   " + "\n              ".join(t["selection"]["avoid_when"]))
    look = t["look"]
    print(f"\nStyle:        {look['style']} (default)" + "".join(f"\n              {a['style']}: {a['when']}" for a in look.get("alternates", [])))
    if look.get("design_profile"):
        print(f"Profile:      {look['design_profile']}")
    print("\nScene grammar:")
    for sg in t["scene_grammar"]:
        print(f"  {sg['role']:<18} {sg['formula']}")
    m = t["motion"]
    print(f"\nMotion:       {m['signature']}\nAlive between events: {m['continuous_layer']}")
    r = t["rules"]
    print(f"\nRules (checked by `style check`): hook by {r['hook_within_sec']:g}s, beat gap <= {r['max_beat_gap_sec']:g}s, "
          f"scene <= {r['max_scene_sec']:g}s, <= {r['words_per_10s_max']:g} words per 10 s")
    print(f"Ending:       {r['ending']}")
    print("\nAnti-patterns:")
    for a in t["anti_patterns"]:
        print(f"  - {a['pattern']}  [{a['source']}]")
    if t.get("open_questions"):
        print("\nOpen questions:")
        for q in t["open_questions"]:
            print(f"  - {q}")
    print("\nRevisions:")
    for rv in t["revisions"]:
        print(f"  v{rv['version']} {rv['date']}  {rv['change']}  (why: {rv['reason']})")
    return 0


def _recommend_inputs(args: argparse.Namespace) -> Tuple[List[str], str, Optional[Path]]:
    cats = parse_category_arg(getattr(args, "category", None))
    text = getattr(args, "text", None) or ""
    pdir = project_dir(args.slug) if getattr(args, "slug", None) else None
    if pdir and (pdir / "brief.json").exists():
        brief = load_json(pdir / "brief.json")
        cats = cats or brief.get("categories", [])
        text = (text + " " + style_templates_module().brief_text(brief)).strip()
    if not cats and not text:
        raise SystemExit("Error: give a project slug with a brief, or --category and/or --text.")
    return cats, text, pdir


def cmd_style_recommend(args: argparse.Namespace) -> int:
    records = catalogue_records()
    cats, text, pdir = _recommend_inputs(args)
    ranked = style_templates_module().recommend(records, cats, text)
    print(f"Categories: {', '.join(cats) or '(none)'}" + (f"   project: {pdir.name}" if pdir else ""))
    if not any(r["score"] for r in ranked):
        print("No template matched by category or keyword. Decide by visual job:")
        for r in ranked:
            t = records["style-templates"][r["id"]]
            print(f"  {r['id']:<20} {t['visual_job']['viewer_leaves_able_to']}")
        return 0
    print(f"\n{'rank':<5}{'template':<20}{'job':<14}{'score':<7}why")
    for i, r in enumerate(ranked[:4], 1):
        print(f"{i:<5}{r['id']:<20}{r['job']:<14}{r['score']:<7}{'; '.join(r['why'])}")
    top = records["style-templates"][ranked[0]["id"]]
    print(f"\nTop pick: {top['name']}. Confirm by the visual job: the viewer should leave able to\n  \"{top['visual_job']['viewer_leaves_able_to']}\"")
    print("Do not use it when:\n  - " + "\n  - ".join(top["selection"]["avoid_when"]))
    if len(ranked) > 1 and ranked[0]["score"] - ranked[1]["score"] <= 1.5:
        print(f"\nClose call with {ranked[1]['id']} ({ranked[0]['score']} vs {ranked[1]['score']}): decide by the visual job above, not the score.")
    print("\nScores are keyword and category evidence only. Pin the choice with:")
    print(f"  python scripts/studio.py style adopt {pdir.name if pdir else '<slug>'} {ranked[0]['id']}")
    return 0


def cmd_style_adopt(args: argparse.Namespace) -> int:
    records = catalogue_records()
    tpl = get_style_template(records, args.template)
    if tpl.get("status") in {"blocked", "deprecated"}:
        raise SystemExit(f"Error: style template '{args.template}' is {tpl['status']}.")
    pdir = project_dir(args.slug)
    pj = pdir / "project.json"
    if not pj.exists():
        raise SystemExit("Error: legacy project (no project.json); style templates apply to studio projects.")
    project = load_json(pj)
    old = project.get("style_template")
    project["style_template"] = {"id": tpl["id"], "version": tpl["version"]}
    write_json(pj, project)
    if old and old["id"] == tpl["id"]:
        news = style_templates_module().revisions_since(tpl, old["version"])
        print(f"Re-pinned {pdir.name} to {tpl['id']} v{tpl['version']} (was v{old['version']}).")
        for r in news:
            print(f"  v{r['version']}: {r['change']}")
        if news:
            print("Re-pinning records that you reviewed these changes; it does not apply them. Run `style check` and revise the project.")
    else:
        print(f"{pdir.name} now follows {tpl['id']} v{tpl['version']}.")
    allowed = {tpl["look"]["style"]} | {a["style"] for a in tpl["look"].get("alternates", [])}
    if project["style"] not in allowed:
        print(f"Note: project style '{project['style']}' is not this template's default ('{tpl['look']['style']}') or a listed alternate.")
    return 0


def cmd_style_check(args: argparse.Namespace) -> int:
    records = catalogue_records()
    stm = style_templates_module()
    if args.slug:
        pdir = project_dir(args.slug)
        project = load_json(pdir / "project.json")
        brief = load_json(pdir / "brief.json") if (pdir / "brief.json").exists() else None
        pin = project.get("style_template")
        if not pin:
            print(f"{pdir.name} follows no style template. Run: python scripts/studio.py style recommend {pdir.name}")
            return 0
        tpl = get_style_template(records, pin["id"])
        print(f"{pdir.name} vs {tpl['id']} (pinned v{pin['version']}, current v{tpl['version']})")
        findings = stm.check_project(pdir, project, brief, tpl)
        for level, msg in findings:
            print(f"  [{level.upper()}] {msg}")
        if not findings:
            print("  Nothing to flag.")
        warns = sum(1 for lv, _ in findings if lv == "warn")
        print(f"{warns} warning(s). These are pre-render checks on the storyboard and narration; motion-qa and the creative review still apply.")
        return 1 if warns and args.strict else 0

    # Portfolio view: which videos follow which template, and which are behind.
    print(f"{'project':<36}{'template':<20}{'pinned':<8}{'current':<8}{'warnings':<9}note")
    behind = 0
    for pdir in studio_projects():
        project = load_json(pdir / "project.json")
        brief = load_json(pdir / "brief.json") if (pdir / "brief.json").exists() else None
        pin = project.get("style_template")
        if not pin:
            sug = ""
            if brief:
                ranked = stm.recommend(records, brief.get("categories", []), stm.brief_text(brief))
                if ranked and ranked[0]["score"]:
                    sug = f"suggested: {ranked[0]['id']}"
            print(f"{pdir.name:<36}{'-':<20}{'-':<8}{'-':<8}{'-':<9}{sug}")
            continue
        tpl = records.get("style-templates", {}).get(pin["id"])
        if not tpl:
            print(f"{pdir.name:<36}{pin['id']:<20}v{pin['version']:<7}{'?':<8}{'-':<9}template not registered")
            continue
        findings = stm.check_project(pdir, project, brief, tpl)
        warns = sum(1 for lv, _ in findings if lv == "warn")
        is_behind = pin["version"] < tpl["version"]
        behind += is_behind
        print(f"{pdir.name:<36}{tpl['id']:<20}v{pin['version']:<7}v{tpl['version']:<7}{warns:<9}{'BEHIND the template' if is_behind else ''}")
    if behind:
        print(f"\n{behind} project(s) behind. `style check <slug>` shows what changed; `style adopt <slug> <template>` re-pins after you revise.")
    return 0


STYLE_HANDLERS = {
    "list": cmd_style_list, "show": cmd_style_show, "recommend": cmd_style_recommend,
    "adopt": cmd_style_adopt, "check": cmd_style_check,
}


# --------------------------------------------------------------------------- status
def cmd_status(args: argparse.Namespace) -> int:
    pdir = project_dir(args.slug)
    studio = (pdir / "project.json").exists()
    rows = [
        ("brief.json", "Stage 0 creative brief + directions"),
        ("research.json", "Stage 0R research dossier (factual topics)"),
        ("beatmap.json", "Stage 1a narrative arc, beats and shots (optional)"),
        ("design-profile.json", "Stage 1b design profile / chosen direction (optional)"),
        ("bakeoff/bakeoff.json", "Stage 1b style bake-off record (optional)"),
        ("storyboard.json", "Stage 1 scene plan"),
        ("src/narration.json", "Stage 2 narration script"),
        ("audio/timeline.json", "Stage 3 measured narration timing"),
        ("src/index.html", "Stage 4 composition"),
        (f"src/{RUNTIME_DIRNAME}/{LOCK_NAME}", "Studio runtime vendored"),
        ("qa/frame-review/report.json", "Stage 9 frame review (scripts/frame-review.py)"),
        ("qa/motion/motion-qa.json", "Stage 9 motion QA report (scripts/motion-qa.py)"),
        ("qa/creative-review.json", "Stage 9 creative review rubric"),
        ("poster.jpg", "Poster: last non-black frame of the finished film (scripts/poster.py)"),
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
    p.add_argument("--style-template", dest="style_template", help="Style template id (catalogue/data/style-templates/); sets the default style and pins the project to it")
    p.add_argument("--type", dest="video_type", required=True, choices=list(load_video_types()),
                   help="Video type (specs/video-types.json): reel = Instagram reel 45-60s, long-reel = Instagram 60-180s, "
                        "youtube = over 180s; each +-15s. Sets the format, platform and length.")
    p.add_argument("--formats", help="Optional; must equal the type's format (portrait for reels, landscape for youtube)")
    p.add_argument("--category", help="Comma-separated subject categories (specs/categories.json); usually one, e.g. history,finance for a mixed piece")

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
    p.add_argument("--allow-narration-shift", action="store_true",
                   help="Keep going when re-synthesised narration moves scene timing (the composition must not hard-code cue times)")

    p = sub.add_parser("renders", help="Per-format render state (current, stale, unstamped, missing); --archive moves stale renders to renders/history/")
    p.add_argument("slugs", nargs="*", help="Projects (default: every studio project)")
    p.add_argument("--archive", action="store_true", help="Move stale renders (and their out/ copies) to history so the next build renders them again")
    p.add_argument("--unstamped", action="store_true", help="With --archive, also move renders that predate build stamps")
    p.add_argument("--quality", choices=["draft", "looks", "delivery"], help="Compare against this quality instead of project.json's")

    p = sub.add_parser("upgrade", help="Re-sync the runtime and regenerate format entry files; superseded renders move to renders/history/")
    p.add_argument("slugs", nargs="*")
    p.add_argument("--all", action="store_true", help="Every studio project, including versioned ones (projects/<group>/<version>/)")
    p.add_argument("--keep-renders", action="store_true", help="Leave superseded renders in place (build will still archive them before re-rendering)")
    p.add_argument("--force", action="store_true", help="Overwrite a vendored runtime that was edited in place")

    p = sub.add_parser("captions", help="Caption cues from narration: approximate sentences, or measured word times grouped into short phrases")
    p.add_argument("slug")
    p.add_argument("--timing", choices=["approx", "words"], default="approx", help="approx: split by character count (default). words: transcribe each narration clip locally and align the script to the measured word times")
    p.add_argument("--grouping", choices=["sentence", "phrase"], default="sentence", help="phrase: 1-3 word reel captions (needs --timing words)")
    p.add_argument("--max-words", dest="max_words", type=int, default=3, help="Words per phrase cue (default 3)")
    p.add_argument("--model", default="small.en", help="Whisper model for --timing words (default small.en)")
    p.add_argument("--retranscribe", action="store_true", help="Ignore the cache in audio/words.json")

    p = sub.add_parser("words", help="Film time at which a phrase is spoken (needs audio/words.json)")
    p.add_argument("slug")
    p.add_argument("phrase")

    p = sub.add_parser("script", help="Pre-render script and story lint: timed sentence sheet, hook, rhythm, loop, asks, and the story table")
    p.add_argument("slug")
    p.add_argument("--wps", type=float, default=2.9, help="Words per second used only when narration is not yet measured")
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-sheet", dest="no_sheet", action="store_true", help="Findings and story table only")

    p = sub.add_parser("hook", help="Score hook lines and list the hook formulas")
    hsub = p.add_subparsers(dest="hook_command", required=True)
    hp = hsub.add_parser("score", help="Rank hook lines (a lint for greetings, vagueness and slow openings; not a view predictor)")
    hp.add_argument("lines", nargs="*", help="Hook lines, quoted")
    hp.add_argument("--file", help="A text file with one hook per line")
    hp.add_argument("--slug", help="Also score this project's actual first sentence")
    hp.add_argument("--wps", type=float, default=2.9)
    hp = hsub.add_parser("formulas", help="List the hook formulas (specs/hook-formulas.json)")
    hp.add_argument("--category", help="Only formulas that suit this subject category")

    p = sub.add_parser("poster", help="Poster = the last non-black frame of the finished film (projects/<slug>/poster.jpg); build makes it automatically")
    p.add_argument("slug", nargs="?")
    p.add_argument("--all", action="store_true", help="every project and version")
    p.add_argument("--force", action="store_true", help="remake even if current")

    p = sub.add_parser("review", help="Creative review rubric")
    p.add_argument("slug")
    p.add_argument("--init", action="store_true")

    p = sub.add_parser("status", help="Lifecycle artefact checklist")
    p.add_argument("slug")

    p = sub.add_parser("series", help="Groups of projects: sequential parts or a themed collection")
    ssub = p.add_subparsers(dest="series_command", required=True)
    sp = ssub.add_parser("new", help="Create series/<slug>/series.json")
    sp.add_argument("slug")
    sp.add_argument("--kind", required=True, choices=["sequential", "collection"])
    sp.add_argument("--category", help="Comma-separated subject categories (required)")
    sp.add_argument("--title")
    sp.add_argument("--style", help="Optional shared style id")
    sp = ssub.add_parser("add", help="Add a project to a series")
    sp.add_argument("series")
    sp.add_argument("project", help="Project slug, folder name or projects/-relative path")
    sp.add_argument("--part", type=int, help="Part number (sequential; default: next free)")
    sp.add_argument("--title", help="Part title if different from the project's")
    sp.add_argument("--planned", action="store_true", help="Project folder does not exist yet")
    sp.add_argument("--type", dest="video_type", choices=list(load_video_types()), help="Planned video type, for a member with no project yet")
    sp = ssub.add_parser("show", help="Print one series and its members")
    sp.add_argument("slug")
    ssub.add_parser("list", help="List all series")
    sp = ssub.add_parser("validate", help="Validate one series, or all when no slug is given")
    sp.add_argument("slug", nargs="?")

    p = sub.add_parser("style", help="Style templates: choose one per video, check a video against it, see which are behind")
    stsub = p.add_subparsers(dest="style_command", required=True)
    stsub.add_parser("list", help="List style templates and how many projects follow each")
    sp = stsub.add_parser("show", help="Print one style template")
    sp.add_argument("id")
    sp = stsub.add_parser("recommend", help="Rank templates for a project's brief, or for --category / --text")
    sp.add_argument("slug", nargs="?")
    sp.add_argument("--category", help="Comma-separated subject categories (overrides the brief's)")
    sp.add_argument("--text", help="Free text describing the film; matched against template keywords")
    sp = stsub.add_parser("adopt", help="Pin a project to a template and its current version (also re-pins after a revision)")
    sp.add_argument("slug")
    sp.add_argument("template")
    sp = stsub.add_parser("check", help="Check one project against its template, or list every project's status when no slug is given")
    sp.add_argument("slug", nargs="?")
    sp.add_argument("--strict", action="store_true", help="Exit 1 when there are warnings (one project only)")

    args = parser.parse_args()
    handlers = {
        "series": cmd_series, "style": cmd_style, "script": cmd_script, "hook": cmd_hook, "words": cmd_words,
        "new": cmd_new, "sync": cmd_sync, "formats": cmd_formats, "validate": cmd_validate,
        "renders": cmd_renders, "upgrade": cmd_upgrade,
        "build": cmd_build, "captions": cmd_captions, "review": cmd_review, "status": cmd_status, "poster": cmd_poster,
    }
    if args.command not in handlers:
        parser.print_help()
        return 0
    return handlers[args.command](args)


if __name__ == "__main__":
    ensure_schema_python()
    sys.exit(main())
