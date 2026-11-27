#!/usr/bin/env python3
"""
scripts/visual-director.py: engine routing and Blender plates for Motion Lab films.

HyperFrames is always the compositor. A scene is drawn natively (HyperFrames: SVG, DOM, Canvas, or
Three.js inside the page) or gets a Blender plate: an offline 3D render (opaque MP4 or alpha WebM in
src/plates/) that the composition places as a timed <video>. The plan lives in
projects/<slug>/visual-plan.json (specs/visual-plan-spec.json); engines and routing signals live in
specs/visual-engines.json. The visual-director skill and subagent own the decisions; this CLI drafts,
checks and renders.

Usage:
    python scripts/visual-director.py engines                      # engine registry and routing summary
    python scripts/visual-director.py doctor                       # which engines this host can run
    python scripts/visual-director.py templates                    # Blender plate templates
    python scripts/visual-director.py plan <slug> [--write [--force]]
    python scripts/visual-director.py add-plate <slug> <plate-id> --template hero-orbit [--scene s2] [--alpha]
    python scripts/visual-director.py check <slug>
    python scripts/visual-director.py render <slug> [--plate ID] [--format F] [--preview] [--force] [--dry-run]
    python scripts/visual-director.py install-blender [--dry-run]

`render` takes the host render lock (one heavy job at a time) and skips plates whose stamp is current.
"""

import argparse
import hashlib
import importlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
SPECS_DIR = REPO_ROOT / "specs"
KIT_DIR = REPO_ROOT / "src" / "blender"
PLATE_TEMPLATES_DIR = REPO_ROOT / "templates" / "blender" / "plates"
STYLES_DIR = REPO_ROOT / "src" / "studio" / "styles"
ENGINES_FILE = SPECS_DIR / "visual-engines.json"
PLAN_SPEC = SPECS_DIR / "visual-plan-spec.json"
PLAN_NAME = "visual-plan.json"
FORMAT_IDS = ("landscape", "portrait", "square")
PLATE_MODES = ("plate-full", "plate-under", "plate-over")
ENCODE = {
    False: ("mp4", ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]),
    True: ("webm", ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-crf", "24", "-b:v", "0", "-row-mt", "1",
                    "-auto-alt-ref", "0"]),
}

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def studio_module():
    return importlib.import_module("studio")


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def engines() -> Dict[str, Any]:
    return load_json(ENGINES_FILE)


def sha256_text(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


# --------------------------------------------------------------------------- Blender discovery
def install_root() -> Path:
    system = platform.system()
    if system == "Windows":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Programs" / "Blender"
    if system == "Darwin":
        return Path.home() / "Applications"
    return Path.home() / ".local" / "opt"


def platform_key() -> Optional[str]:
    system, machine = platform.system(), platform.machine().lower()
    if system == "Windows" and machine in ("amd64", "x86_64"):
        return "windows-x64"
    if system == "Darwin" and machine == "arm64":
        return "macos-arm64"
    if system == "Linux" and machine in ("x86_64", "amd64"):
        return "linux-x64"
    return None


def blender_candidates() -> List[Path]:
    out: List[Path] = []
    for var in ("MOTION_LAB_BLENDER", "BLENDER_BIN"):
        if os.environ.get(var):
            out.append(Path(os.environ[var]))
    on_path = shutil.which("blender")
    if on_path:
        out.append(Path(on_path))
    root = install_root()
    system = platform.system()
    if system == "Windows":
        out += sorted(root.glob("blender-*/blender.exe"), reverse=True)
        pf = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Blender Foundation"
        out += sorted(pf.glob("Blender*/blender.exe"), reverse=True)
    elif system == "Darwin":
        out += sorted(root.glob("Blender*.app/Contents/MacOS/Blender"), reverse=True)
        out.append(Path("/Applications/Blender.app/Contents/MacOS/Blender"))
    else:
        out += sorted(root.glob("blender-*/blender"), reverse=True)
    return out


def find_blender(explicit: Optional[str] = None) -> Optional[Path]:
    for cand in ([Path(explicit)] if explicit else []) + blender_candidates():
        if cand.is_file():
            return cand
    return None


_VERSION_CACHE: Dict[str, str] = {}


def blender_version(binary: Path) -> str:
    key = str(binary)
    if key not in _VERSION_CACHE:
        try:
            out = subprocess.run([key, "--version"], capture_output=True, text=True, timeout=120,
                                 stdin=subprocess.DEVNULL).stdout
        except (OSError, subprocess.SubprocessError):
            out = ""
        m = re.search(r"Blender\s+(\d+\.\d+(?:\.\d+)?)", out)
        _VERSION_CACHE[key] = m.group(1) if m else "unknown"
    return _VERSION_CACHE[key]


# --------------------------------------------------------------------------- palette
def palette_for(project: Dict[str, Any]) -> Dict[str, str]:
    """Palette roles from the project's style sheet: --c-accent -> 'accent' (hex and rgb() values only)."""
    style = project.get("style") or "editorial-light"
    css = STYLES_DIR / f"{style}.css"
    if not css.exists():
        css = STYLES_DIR / "editorial-light.css"
    text = css.read_text(encoding="utf-8")
    root = re.search(r":root\s*\{(.*?)\}", text, re.S)
    roles: Dict[str, str] = {}
    for name, value in re.findall(r"--c-([\w-]+)\s*:\s*([^;]+);", root.group(1) if root else text):
        value = value.strip()
        if re.match(r"^#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$", value) or value.startswith("rgb"):
            roles[name] = value
    return roles


# --------------------------------------------------------------------------- routing
def scene_text(scene: Dict[str, Any]) -> str:
    parts: List[str] = [str(scene.get("title", "")), str(scene.get("visual", ""))]
    layout = scene.get("layout")
    if isinstance(layout, dict):
        parts += [str(v) for v in layout.values()]
    elif layout:
        parts.append(str(layout))
    parts += [str(b.get("action", "")) for b in scene.get("beats") or [] if isinstance(b, dict)]
    parts += [json.dumps(c) if not isinstance(c, str) else c for c in scene.get("capabilities") or []]
    parts += [json.dumps(a) if not isinstance(a, str) else a for a in scene.get("asset_refs") or []]
    return " ".join(parts).lower()


def match_terms(text: str, terms: List[str]) -> List[str]:
    return [t for t in terms if re.search(r"(?<![a-z0-9])" + re.escape(t.lower()) + r"(?![a-z0-9])", text)]


def route_scene(scene: Dict[str, Any], registry: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, int], List[str]]:
    """(engine, scores, matched terms of the winner). Ties and weak matches stay on the cheaper engine.

    Treatment terms always count; subject terms count only when the scene names no 2D form (a chart of
    water is a chart)."""
    routing = (registry or engines())["routing"]
    text = scene_text(scene)
    form_engine = routing.get("form_engine", "hyperframes")
    has_form = bool(match_terms(text, routing["signals"].get(form_engine, {}).get("terms", [])))
    scores: Dict[str, int] = {}
    matched: Dict[str, List[str]] = {}
    for engine, sig in routing["signals"].items():
        hits = match_terms(text, sig["terms"])
        score = int(sig.get("weight", 1)) * len(hits)
        if sig.get("subject_terms") and not has_form:
            subject_hits = match_terms(text, sig["subject_terms"])
            hits += subject_hits
            score += int(sig.get("subject_weight", 1)) * len(subject_hits)
        matched[engine] = hits
        scores[engine] = score
    order = ["hyperframes", "threejs", "blender"]  # cheapest first wins a tie
    best = max(order, key=lambda e: (scores.get(e, 0), -order.index(e)))
    if best != "hyperframes" and scores[best] < int(routing.get("min_score", 2)):
        best = "hyperframes"
    return best, scores, matched.get(best, [])


TEMPLATE_HINTS = [
    ("rigid-collapse", ["rigid body", "collapse", "shatter", "debris", "domino", "topple", "crash"]),
    ("particle-field", ["particle", "particles", "galaxy", "swarm", "dust", "sparks", "stars", "constellation"]),
    ("light-shafts", ["god rays", "light shafts", "fog", "mist", "haze", "volumetric", "smoke"]),
]


def suggest_template(scene: Dict[str, Any]) -> str:
    text = scene_text(scene)
    for name, terms in TEMPLATE_HINTS:
        if match_terms(text, terms):
            return name
    return "hero-orbit"


def plate_id_for(scene_id: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", f"{scene_id}-plate".lower()).strip("-")


def draft_plan(pdir: Path) -> Dict[str, Any]:
    project = load_json(pdir / "project.json")
    sb_path = pdir / "storyboard.json"
    if not sb_path.exists():
        raise SystemExit(f"{pdir.name}: storyboard.json is missing; the visual director routes storyboard scenes "
                         "(phase 2 must sign off first).")
    registry = engines()
    plan: Dict[str, Any] = {"spec_version": "1.0.0", "slug": project["slug"], "decided_by": "heuristic",
                            "scenes": [], "plates": []}
    for sc in load_json(sb_path).get("scenes", []):
        engine, scores, hits = route_scene(sc, registry)
        entry: Dict[str, Any] = {"scene": sc["id"], "engine": engine, "mode": "native", "signals": hits}
        if engine == "blender":
            pid = plate_id_for(sc["id"])
            template = suggest_template(sc)
            entry.update({"mode": "plate-under", "plates": [pid],
                          "reason": f"routing signals {', '.join(hits)}: light, simulation or camera depth the page cannot fake",
                          "overlay": "titles, labels and numbers stay in HyperFrames above the plate"})
            plan["plates"].append({
                "id": pid, "script": f"blender/{pid}.py", "template": template, "scene": sc["id"],
                "start_sec": float(sc["start_sec"]), "duration_sec": round(float(sc["end_sec"]) - float(sc["start_sec"]), 3),
                "alpha": False, "engine": "eevee",
            })
        elif engine == "threejs":
            entry["reason"] = f"routing signals {', '.join(hits)}: stylised 3D with labels tracked in the page"
        else:
            entry["reason"] = ("2D, type, diagram or chart work: the compositor draws it" if hits else
                               "no 3D signal: HyperFrames is the default")
        plan["scenes"].append(entry)
    return plan


# --------------------------------------------------------------------------- plate files
def plate_ext(plate: Dict[str, Any]) -> str:
    return ENCODE[bool(plate.get("alpha"))][0]


def plate_output(pdir: Path, plate: Dict[str, Any], fid: str) -> Path:
    return pdir / "src" / "plates" / f"{plate['id']}.{fid}.{plate_ext(plate)}"


def plate_workdir(pdir: Path, plate_id: str, fid: str, preview: bool = False) -> Path:
    base = pdir / "renders" / "plates" / plate_id / fid
    return base / "preview" if preview else base


def plate_formats(project: Dict[str, Any], plate: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries = studio_module().format_entries(project)
    wanted = plate.get("formats")
    return [e for e in entries if not wanted or e["id"] in wanted]


def make_job(pdir: Path, project: Dict[str, Any], plate: Dict[str, Any], entry: Dict[str, Any],
             preview: bool = False) -> Dict[str, Any]:
    defaults = engines()["plate_defaults"]
    engine = plate.get("engine", defaults["engine"])
    job = {
        "plate": plate["id"],
        "format": entry["id"],
        "width": entry["width"],
        "height": entry["height"],
        "fps": int(project["fps"]),
        "duration_sec": float(plate["duration_sec"]),
        "alpha": bool(plate.get("alpha")),
        "engine": engine,
        "samples": int(plate.get("samples") or defaults["samples"][engine if engine in defaults["samples"] else "eevee"]),
        "view_transform": defaults.get("view_transform", "Standard"),
        "palette": palette_for(project),
        "cues": plate.get("cues") or {},
        "params": plate.get("params") or {},
        "kit_dir": KIT_DIR.as_posix(),
        "script": (pdir / plate["script"]).resolve().as_posix(),
        "frames_dir": (plate_workdir(pdir, plate["id"], entry["id"], preview) / "frames").resolve().as_posix(),
    }
    if "seed" in plate:
        job["seed"] = int(plate["seed"])
    if preview:
        job["preview"] = dict(defaults["preview"])
    return job


def plate_fingerprint(pdir: Path, job: Dict[str, Any], blender: str) -> str:
    """Hash of everything a plate's pixels depend on: kit, script, job (minus local paths), Blender version, codec."""
    h = hashlib.sha256()
    for f in (KIT_DIR / "mlab.py", KIT_DIR / "run_plate.py", Path(job["script"])):
        h.update(f.name.encode())
        h.update(sha256_text(f.read_bytes()).encode() if f.exists() else b"missing")
    stable = {k: v for k, v in job.items() if k not in ("kit_dir", "script", "frames_dir")}
    h.update(json.dumps(stable, sort_keys=True).encode())
    h.update(blender.encode())
    h.update(json.dumps(ENCODE[bool(job["alpha"])]).encode())
    return h.hexdigest()


def plate_state(pdir: Path, plate: Dict[str, Any], entry: Dict[str, Any], fingerprint: Optional[str]) -> str:
    """'missing' | 'current' | 'stale' | 'unknown' (no Blender here to compute the fingerprint)."""
    out = plate_output(pdir, plate, entry["id"])
    if not out.exists():
        return "missing"
    stamp = plate_workdir(pdir, plate["id"], entry["id"]) / "stamp.json"
    if fingerprint is None:
        return "unknown"
    if not stamp.exists():
        return "stale"
    try:
        return "current" if load_json(stamp).get("fingerprint") == fingerprint else "stale"
    except (OSError, ValueError):
        return "stale"


# --------------------------------------------------------------------------- check
LINT_RULES = [
    (r"(?<![\w.])random\.(random|uniform|randint|randrange|choice|choices|shuffle|gauss|sample)\s*\(", "error",
     "module-level random breaks determinism; use rng = lab.rng() and rng.random()"),
    (r"(np|numpy)\.random\.(rand|randn|random|randint|choice|seed|shuffle)\s*\(", "error",
     "numpy's global random state breaks determinism; use lab.rng()"),
    (r"time\.time\s*\(|time\.perf_counter\s*\(|datetime\.now\s*\(", "error", "wall-clock time breaks determinism"),
    (r"type\s*=\s*['\"]FONT['\"]|text_add\s*\(|\.body\s*=", "error",
     "no text in plates: words, numbers and labels belong to the HyperFrames layer"),
    (r"bpy\.ops\.render\.", "error", "build() builds the scene only; run_plate.py renders"),
    (r"scene\.frame_(start|end)\s*=|render\.resolution_[xy]\s*=|render\.fps\s*=", "warning",
     "the job sets size, fps and frame range; use lab.f(t) and lab.pick()"),
]


def lint_plate_script(path: Path) -> List[Tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    code = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
    return [(level, f"{path.name}: {msg}") for pat, level, msg in LINT_RULES if re.search(pat, code)]


def video_tags(html: str) -> List[Dict[str, str]]:
    tags = []
    for m in re.finditer(r"<video\b([^>]*)>", html, re.I):
        tags.append({k.lower(): v for k, v in re.findall(r"([\w:-]+)\s*=\s*\"([^\"]*)\"", m.group(1))})
    return tags


def check_plan(pdir: Path, project: Optional[Dict[str, Any]] = None, blender: Optional[str] = None) -> Tuple[List[str], List[str]]:
    """(errors, warnings) for projects/<slug>/visual-plan.json. A project without a plan has nothing to check."""
    errors: List[str] = []
    warnings: List[str] = []
    path = pdir / PLAN_NAME
    if not path.exists():
        return errors, warnings
    try:
        plan = load_json(path)
    except (OSError, ValueError) as exc:
        return [f"{PLAN_NAME} is not valid JSON ({exc})"], warnings
    st = studio_module()
    errors += st.schema_errors(plan, PLAN_SPEC)
    if errors:
        return errors, warnings
    project = project or load_json(pdir / "project.json")
    if plan["slug"] != project.get("slug"):
        errors.append(f"{PLAN_NAME}: slug '{plan['slug']}' does not match project.json ('{project.get('slug')}')")
    if plan.get("decided_by") != "director":
        warnings.append(f"{PLAN_NAME} is a heuristic draft: the visual director has not decided every scene "
                        "(set decided_by to 'director' once reviewed)")
    plates = {p["id"]: p for p in plan["plates"]}
    if len(plates) != len(plan["plates"]):
        errors.append(f"{PLAN_NAME}: plate ids are not unique")
    sb_path = pdir / "storyboard.json"
    sb_ids: List[str] = []
    if sb_path.exists():
        sb_ids = [s["id"] for s in load_json(sb_path).get("scenes", [])]
        planned = {s["scene"] for s in plan["scenes"]}
        for sid in sb_ids:
            if sid not in planned:
                warnings.append(f"{PLAN_NAME}: storyboard scene {sid} has no engine decision")
        for sid in planned - set(sb_ids):
            errors.append(f"{PLAN_NAME}: scene '{sid}' is not in storyboard.json")
    used = set()
    for s in plan["scenes"]:
        ids = s.get("plates") or []
        used.update(ids)
        if s["mode"] in PLATE_MODES:
            if s["engine"] != "blender":
                errors.append(f"{PLAN_NAME}: scene {s['scene']} uses {s['mode']} but engine '{s['engine']}' makes no plates")
            if not ids:
                errors.append(f"{PLAN_NAME}: scene {s['scene']} uses {s['mode']} but lists no plates")
        elif s["engine"] == "blender":
            errors.append(f"{PLAN_NAME}: scene {s['scene']} routes to blender with mode 'native'; Blender only makes plates")
        for pid in ids:
            if pid not in plates:
                errors.append(f"{PLAN_NAME}: scene {s['scene']} names plate '{pid}', which is not in plates[]")
            elif s["mode"] == "plate-over" and not plates[pid].get("alpha"):
                errors.append(f"{PLAN_NAME}: plate '{pid}' sits over the page (plate-over) and must be rendered with alpha")
    duration = float(project["duration_sec"])
    fps = int(project["fps"])
    html_path = pdir / "src" / "index.html"
    html = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
    tags = video_tags(html)
    project_fmts = {e["id"] for e in st.format_entries(project)}
    for pid, plate in plates.items():
        if pid not in used:
            warnings.append(f"{PLAN_NAME}: plate '{pid}' is used by no scene")
        script = pdir / plate["script"]
        if not script.exists():
            errors.append(f"plate '{pid}': script {plate['script']} is missing "
                          f"(`visual-director.py add-plate {project['slug']} {pid} --template hero-orbit` starts one)")
        else:
            for level, msg in lint_plate_script(script):
                (errors if level == "error" else warnings).append(f"plate '{pid}': {msg}")
        if plate["start_sec"] + plate["duration_sec"] > duration + 1.0 / fps:
            errors.append(f"plate '{pid}' ends at {plate['start_sec'] + plate['duration_sec']:.2f}s, after the film ({duration:g}s)")
        for fid in plate.get("formats") or []:
            if fid not in project_fmts:
                errors.append(f"plate '{pid}' lists format '{fid}', which project.json does not render")
        if sb_ids and plate.get("scene") and plate["scene"] not in sb_ids:
            errors.append(f"plate '{pid}' belongs to scene '{plate['scene']}', which is not in storyboard.json")
        refs = [t for t in tags if re.search(rf"(^|/)plates/{re.escape(pid)}\.({'|'.join(FORMAT_IDS)})\.(mp4|webm)$", t.get("src", ""))]
        if not refs:
            warnings.append(f"plate '{pid}' is not placed in src/index.html (<video class=\"clip plate\" "
                            f"src=\"plates/{pid}.<format>.{plate_ext(plate)}\" data-start=... muted>)")
        for t in refs:
            if not t["src"].endswith("." + plate_ext(plate)):
                errors.append(f"plate '{pid}': index.html loads {t['src']} but the plate is delivered as "
                              f".{plate_ext(plate)} ({'alpha' if plate.get('alpha') else 'opaque'})")
            try:
                if abs(float(t.get("data-start", "nan")) - plate["start_sec"]) > 1.0 / fps:
                    warnings.append(f"plate '{pid}': <video> data-start {t.get('data-start')} differs from the plan's "
                                    f"start_sec {plate['start_sec']:g}")
            except ValueError:
                warnings.append(f"plate '{pid}': its <video> has no numeric data-start")
        for entry in plate_formats(project, plate):
            fp = None
            if blender and script.exists():
                fp = plate_fingerprint(pdir, make_job(pdir, project, plate, entry), blender)
            state = plate_state(pdir, plate, entry, fp)
            if state == "missing":
                warnings.append(f"plate '{pid}' ({entry['id']}) is not rendered yet: "
                                f"`python scripts/visual-director.py render {project['slug']} --plate {pid}`")
            elif state == "stale":
                warnings.append(f"plate '{pid}' ({entry['id']}) is stale (its script, kit, job or Blender changed); "
                                "`studio.py build` re-renders it")
    return errors, warnings


# --------------------------------------------------------------------------- render
def contact_sheet(frames_dir: Path, out: Path, ffmpeg: str) -> None:
    frames = sorted(frames_dir.glob("frame_*.png"))
    if not frames:
        return
    cols = min(4, len(frames))
    rows = (len(frames) + cols - 1) // cols
    lst = frames_dir.parent / "frames.txt"
    lst.write_text("".join(f"file '{f.as_posix()}'\n" for f in frames), encoding="utf-8")
    subprocess.run([ffmpeg, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-vf", f"tile={cols}x{rows}:padding=6:margin=6:color=white", "-frames:v", "1", "-update", "1", str(out)],
                   check=True, stdin=subprocess.DEVNULL)


def run_blender(blender: Path, job_path: Path, log_path: Path, expected: int) -> int:
    cmd = [str(blender), "-b", "--factory-startup", "--python-exit-code", "1",
           "--python", str(KIT_DIR / "run_plate.py"), "--", "--job", str(job_path)]
    saved = 0
    with open(log_path, "w", encoding="utf-8") as log, subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace") as proc:
        assert proc.stdout is not None
        for line in proc.stdout:
            log.write(line)
            if "Saved:" in line:
                saved += 1
                if saved == 1 or saved % 15 == 0 or saved == expected:
                    print(f"    frame {saved}/{expected}", flush=True)
            elif line.startswith(("Traceback", "Error", "[mlab]")) or "Error:" in line:
                print("    " + line.rstrip(), flush=True)
        return proc.wait()


def render_one(pdir: Path, project: Dict[str, Any], plate: Dict[str, Any], entry: Dict[str, Any], blender: Path,
               ffmpeg: str, preview: bool, force: bool, dry_run: bool) -> str:
    version = blender_version(blender)
    job = make_job(pdir, project, plate, entry, preview)
    fingerprint = plate_fingerprint(pdir, job, version)
    label = f"{plate['id']} ({entry['id']} {entry['width']}x{entry['height']}{', preview' if preview else ''})"
    if not preview and not force and plate_state(pdir, plate, entry, fingerprint) == "current":
        print(f"[skip] {label}: current")
        return "current"
    work = plate_workdir(pdir, plate["id"], entry["id"], preview)
    frames_dir = Path(job["frames_dir"])
    if dry_run:
        print(f"[plan] {label}: blender {version} -> {frames_dir} -> "
              f"{'contact.png' if preview else plate_output(pdir, plate, entry['id']).relative_to(pdir).as_posix()}")
        return "planned"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)
    job_path = work / "job.json"
    write_json(job_path, job)
    step = int(job.get("preview", {}).get("frame_step", 1))
    total = max(1, int(round(job["duration_sec"] * job["fps"])))
    expected = len(range(1, total + 1, step))
    print(f"[render] {label}: Blender {version}, {job['engine']}, {expected} frames")
    rc = run_blender(blender, job_path, work / "blender.log", expected)
    rendered = sorted(frames_dir.glob("frame_*.png"))
    if rc != 0 or len(rendered) != expected:
        raise SystemExit(f"plate {label} failed (exit {rc}, {len(rendered)}/{expected} frames); "
                         f"log: {(work / 'blender.log').as_posix()}")
    if preview:
        contact_sheet(frames_dir, work / "contact.png", ffmpeg)
        print(f"[ok] {label}: {(work / 'contact.png').as_posix()}")
        return "preview"
    ext, codec = ENCODE[bool(plate.get("alpha"))]
    encoded = work / f"plate.{ext}"
    subprocess.run([ffmpeg, "-y", "-v", "error", "-framerate", str(job["fps"]), "-start_number", "1",
                    "-i", str(frames_dir / "frame_%05d.png"), "-frames:v", str(total), *codec, "-an", str(encoded)],
                   check=True, stdin=subprocess.DEVNULL)
    out = plate_output(pdir, plate, entry["id"])
    out.parent.mkdir(parents=True, exist_ok=True)
    os.replace(encoded, out)
    done = load_json(work / "done.json") if (work / "done.json").exists() else {}
    write_json(work / "stamp.json", {
        "fingerprint": fingerprint, "output": out.relative_to(pdir).as_posix(), "frames": total,
        "blender": version, "engine": done.get("engine"), "device": done.get("device"),
        "render_seconds": done.get("seconds"), "rendered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    print(f"[ok] {label}: {out.relative_to(pdir).as_posix()} ({total} frames, {done.get('seconds', '?')} s in Blender)")
    return "rendered"


# --------------------------------------------------------------------------- commands
def load_plan(pdir: Path) -> Dict[str, Any]:
    path = pdir / PLAN_NAME
    if not path.exists():
        raise SystemExit(f"{pdir.name}: no {PLAN_NAME}; draft one with `python scripts/visual-director.py plan {pdir.name} --write`")
    return load_json(path)


def cmd_engines(args: argparse.Namespace) -> int:
    reg = engines()
    print(f"Compositor: {reg['compositor']} (every film is a HyperFrames composition; other engines make plates)\n")
    for eid, e in reg["engines"].items():
        print(f"{eid}  [{e['status']}]  {e['name']}\n  role: {e['role']}\n  cost: {e['cost']}")
        for item in e["best_for"]:
            print(f"   - {item}")
        print()
    print("Not adopted:")
    for eid, e in reg["not_adopted"].items():
        print(f"  {eid} [{e['decision']}]: {e['reason']}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    reg = engines()
    pinned = reg["blender"]["pinned_version"]
    rows = []
    hf = shutil.which("hyperframes")
    hf_v = ""
    if hf:
        try:
            hf_v = subprocess.run([hf, "--version"], capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL,
                                  shell=platform.system() == "Windows").stdout.strip()
        except (OSError, subprocess.SubprocessError):
            hf_v = "?"
    rows.append(("hyperframes", "ok" if hf else "missing", f"{hf_v} {hf or ''}".strip()))
    three = REPO_ROOT / "src" / "studio" / "vendor" / "three.min.js"
    rows.append(("threejs", "ok" if three.exists() else "missing", "vendored r158 (runs inside HyperFrames)"))
    bl = find_blender(args.blender)
    if bl:
        v = blender_version(bl)
        rows.append(("blender", "ok" if v == pinned else f"version {v} (pinned {pinned})", f"{v} {bl}"))
    else:
        rows.append(("blender", "missing", f"`python scripts/visual-director.py install-blender` (pinned {pinned})"))
    ff = shutil.which("ffmpeg")
    rows.append(("ffmpeg", "ok" if ff else "missing", ff or "needed to encode plates"))
    width = max(len(r[0]) for r in rows)
    for name, state, detail in rows:
        print(f"{name.ljust(width)}  {state:<28} {detail}")
    return 0 if bl and ff and hf else 1


def cmd_templates(args: argparse.Namespace) -> int:
    for path in sorted(PLATE_TEMPLATES_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        m = re.search(r'"""\s*(.*?)\n\s*\n', text, re.S)
        summary = " ".join((m.group(1) if m else "").split())
        print(f"{path.stem}\n  {summary}\n")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    pdir = studio_module().project_dir(args.slug)
    plan = draft_plan(pdir)
    print(f"{'scene':<8} {'engine':<12} {'mode':<12} signals")
    for s in plan["scenes"]:
        print(f"{s['scene']:<8} {s['engine']:<12} {s['mode']:<12} {', '.join(s.get('signals') or []) or '-'}")
    for p in plan["plates"]:
        print(f"  plate {p['id']}: template {p['template']}, {p['start_sec']:g}s +{p['duration_sec']:g}s")
    if not args.write:
        print(f"\nDraft only. `--write` saves {PLAN_NAME} and copies plate templates into blender/.")
        return 0
    target = pdir / PLAN_NAME
    if target.exists() and not args.force:
        raise SystemExit(f"{target.relative_to(pdir).as_posix()} exists; the director may have edited it. Use --force to replace it.")
    write_json(target, plan)
    for p in plan["plates"]:
        script = pdir / p["script"]
        if not script.exists():
            script.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PLATE_TEMPLATES_DIR / f"{p['template']}.py", script)
    print(f"\nWrote {PLAN_NAME} ({len(plan['plates'])} plate(s)). Review every scene, then set decided_by to 'director'.")
    return 0


def cmd_add_plate(args: argparse.Namespace) -> int:
    pdir = studio_module().project_dir(args.slug)
    project = load_json(pdir / "project.json")
    tmpl = PLATE_TEMPLATES_DIR / f"{args.template}.py"
    if not tmpl.exists():
        raise SystemExit(f"unknown template '{args.template}' (see `visual-director.py templates`)")
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", args.plate):
        raise SystemExit("plate id must be lower-case kebab-case")
    path = pdir / PLAN_NAME
    plan = load_json(path) if path.exists() else {"spec_version": "1.0.0", "slug": project["slug"],
                                                    "decided_by": "director", "scenes": [], "plates": []}
    if any(p["id"] == args.plate for p in plan["plates"]):
        raise SystemExit(f"plate '{args.plate}' is already in {PLAN_NAME}")
    start, duration = args.start, args.duration
    if args.scene and (start is None or duration is None) and (pdir / "storyboard.json").exists():
        sc = next((s for s in load_json(pdir / "storyboard.json").get("scenes", []) if s["id"] == args.scene), None)
        if sc is None:
            raise SystemExit(f"scene '{args.scene}' is not in storyboard.json")
        start = float(sc["start_sec"]) if start is None else start
        duration = round(float(sc["end_sec"]) - float(sc["start_sec"]), 3) if duration is None else duration
    if start is None or duration is None:
        raise SystemExit("give --scene (with a storyboard) or both --start and --duration")
    plate = {"id": args.plate, "script": f"blender/{args.plate}.py", "template": args.template,
             "start_sec": float(start), "duration_sec": float(duration), "alpha": bool(args.alpha), "engine": args.engine}
    if args.scene:
        plate["scene"] = args.scene
        decision = next((s for s in plan["scenes"] if s["scene"] == args.scene), None)
        if decision is None:
            decision = {"scene": args.scene, "engine": "blender", "mode": "plate-over" if args.alpha else "plate-under",
                        "plates": [], "reason": "set by the visual director"}
            plan["scenes"].append(decision)
        decision["engine"] = "blender"
        if decision["mode"] == "native":
            decision["mode"] = "plate-over" if args.alpha else "plate-under"
        decision.setdefault("plates", []).append(args.plate)
    plan["plates"].append(plate)
    write_json(path, plan)
    script = pdir / plate["script"]
    if not script.exists():
        script.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tmpl, script)
    print(f"Added plate '{args.plate}' ({args.template}, {plate['start_sec']:g}s +{plate['duration_sec']:g}s, "
          f"{'alpha WebM' if args.alpha else 'opaque MP4'}); script {plate['script']}")
    print(f'Place it in src/index.html: <video class="clip plate" src="plates/{args.plate}.<format>.'
          f'{plate_ext(plate)}" data-start="{plate["start_sec"]:g}" data-duration="{plate["duration_sec"]:g}" muted playsinline></video>')
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    pdir = studio_module().project_dir(args.slug)
    if not (pdir / PLAN_NAME).exists():
        print(f"{pdir.name}: no {PLAN_NAME} (every scene is HyperFrames-native).")
        return 0
    bl = find_blender(args.blender)
    errors, warnings = check_plan(pdir, blender=blender_version(bl) if bl else None)
    for w in warnings:
        print(f"[WARN] {w}")
    for e in errors:
        print(f"[FAIL] {e}")
    print(f"{pdir.name}: {len(errors)} error(s), {len(warnings)} warning(s)" + ("" if bl else " (no Blender here: staleness unknown)"))
    return 1 if errors else 0


def cmd_render(args: argparse.Namespace) -> int:
    st = studio_module()
    pdir = st.project_dir(args.slug)
    plan = load_plan(pdir)
    project = load_json(pdir / "project.json")
    errors, _ = check_plan(pdir, project)
    hard = [e for e in errors if "is not placed" not in e]
    if hard:
        for e in hard:
            print(f"[FAIL] {e}")
        return 1
    plates = [p for p in plan["plates"] if not args.plate or p["id"] == args.plate]
    if args.plate and not plates:
        raise SystemExit(f"plate '{args.plate}' is not in {PLAN_NAME}")
    if not plates:
        print("No plates in the plan.")
        return 0
    blender = find_blender(args.blender)
    ffmpeg = shutil.which("ffmpeg")
    jobs = [(p, e) for p in plates for e in plate_formats(project, p) if not args.format or e["id"] == args.format]
    if not blender or not ffmpeg:
        missing = [n for n, v in (("blender", blender), ("ffmpeg", ffmpeg)) if not v]
        if not args.force and not args.preview and all(plate_output(pdir, p, e["id"]).exists() for p, e in jobs):
            print(f"[warn] {', '.join(missing)} not found: using the existing plates in src/plates/ unchecked "
                  "(their staleness needs Blender to compute)")
            return 0
        raise SystemExit(f"cannot render plates: {', '.join(missing)} not found "
                         "(`python scripts/visual-director.py doctor`; `install-blender` installs the pinned build)")
    pinned = engines()["blender"]["pinned_version"]
    if blender_version(blender) != pinned:
        print(f"[warn] Blender {blender_version(blender)} at {blender} is not the pinned {pinned}; plates may differ between hosts")
    if args.dry_run:
        for p, e in jobs:
            render_one(pdir, project, p, e, blender, ffmpeg, args.preview, args.force, True)
        return 0
    results = []
    with st.render_lock(pdir.name):
        for p, e in jobs:
            results.append(render_one(pdir, project, p, e, blender, ffmpeg, args.preview, args.force, False))
    print(f"Plates: {results.count('rendered')} rendered, {results.count('current')} current, "
          f"{results.count('preview')} preview(s)")
    return 0


def cmd_install_blender(args: argparse.Namespace) -> int:
    spec = engines()["blender"]
    version = spec["pinned_version"]
    key = platform_key()
    if key is None or key not in spec["downloads"]:
        raise SystemExit(f"no pinned Blender build for {platform.system()} {platform.machine()}")
    existing = find_blender()
    if existing and blender_version(existing) == version and not args.force:
        print(f"Blender {version} is already installed: {existing}")
        return 0
    dl = spec["downloads"][key]
    root = install_root()
    archive = root / dl["url"].rsplit("/", 1)[1]
    print(f"Blender {version} ({spec['series']}) for {key}\n  from   {dl['url']}\n  sha256 {dl['sha256']}\n  into   {root}")
    if args.dry_run:
        return 0
    root.mkdir(parents=True, exist_ok=True)
    if not archive.exists() or sha256_file(archive) != dl["sha256"]:
        print("  downloading ...", flush=True)
        tmp = archive.with_suffix(archive.suffix + ".part")
        with urllib.request.urlopen(dl["url"], timeout=60) as resp, open(tmp, "wb") as fh:
            shutil.copyfileobj(resp, fh, length=1 << 20)
        os.replace(tmp, archive)
    digest = sha256_file(archive)
    if digest != dl["sha256"]:
        archive.unlink()
        raise SystemExit(f"checksum mismatch ({digest}); the download was removed")
    print("  checksum ok")
    if key == "windows-x64":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(root)
    elif key == "linux-x64":
        with tarfile.open(archive) as tf:
            tf.extractall(root, filter="data")
    else:
        mount = Path(tempfile.mkdtemp(prefix="blender-dmg-"))
        subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", str(mount), str(archive)], check=True)
        try:
            app = root / f"Blender-{version}.app"
            if app.exists():
                shutil.rmtree(app)
            subprocess.run(["ditto", str(mount / "Blender.app"), str(app)], check=True)
        finally:
            subprocess.run(["hdiutil", "detach", str(mount)], check=False)
    found = find_blender()
    print(f"Installed: {found} (Blender {blender_version(found) if found else '?'})")
    return 0 if found else 1


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Visual director: engine routing and Blender plates")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("engines", help="Engine registry, roles and the engines not adopted")
    sp = sub.add_parser("doctor", help="Which engines this host can run")
    sp.add_argument("--blender", help="Path to a Blender executable")
    sub.add_parser("templates", help="Blender plate templates")
    sp = sub.add_parser("plan", help="Draft per-scene engine decisions from storyboard.json")
    sp.add_argument("slug")
    sp.add_argument("--write", action="store_true", help=f"Save {PLAN_NAME} and copy plate templates into blender/")
    sp.add_argument("--force", action="store_true", help=f"Replace an existing {PLAN_NAME}")
    sp = sub.add_parser("add-plate", help="Add a Blender plate to the plan from a template")
    sp.add_argument("slug")
    sp.add_argument("plate")
    sp.add_argument("--template", default="hero-orbit")
    sp.add_argument("--scene")
    sp.add_argument("--start", type=float)
    sp.add_argument("--duration", type=float)
    sp.add_argument("--alpha", action="store_true", help="Transparent plate (VP9 WebM with alpha)")
    sp.add_argument("--engine", choices=["eevee", "cycles", "workbench"], default="eevee")
    sp = sub.add_parser("check", help=f"Validate {PLAN_NAME}, plate scripts and plate renders")
    sp.add_argument("slug")
    sp.add_argument("--blender")
    sp = sub.add_parser("render", help="Render Blender plates (takes the host render lock)")
    sp.add_argument("slug")
    sp.add_argument("--plate")
    sp.add_argument("--format", choices=FORMAT_IDS)
    sp.add_argument("--preview", action="store_true", help="Every 6th frame at half size and low samples -> contact.png")
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--blender")
    sp = sub.add_parser("install-blender", help="Download the pinned Blender build, verify SHA-256, unpack it")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--force", action="store_true")
    args = p.parse_args(argv)
    return {
        "engines": cmd_engines, "doctor": cmd_doctor, "templates": cmd_templates, "plan": cmd_plan,
        "add-plate": cmd_add_plate, "check": cmd_check, "render": cmd_render, "install-blender": cmd_install_blender,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
