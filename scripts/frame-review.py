#!/usr/bin/env python3
"""
scripts/frame-review.py
Preview-grade visual QA for HyperFrames compositions, in headless Chromium via Playwright.

It seeks the registered GSAP timeline (never plays it), captures sample frames per format, builds
contact sheets (per format and a cross-format matrix) and audits each frame:

  errors    page/console errors, failed or 4xx/5xx requests, studio build errors, missing timeline,
            text outside the frame, persistent text collisions
  warnings  text below the size floor, text outside the safe area (studio projects), short reading
            time, dead stretches (> 3 s without change), first frame empty, blank frames, low contrast

Opt-out attributes follow HyperFrames `check`: data-layout-ignore, data-layout-allow-overflow,
data-layout-bleed, data-layout-allow-overlap, data-layout-allow-caption-zone; data-hold marks an
intentional static hold. This tool does not replace `hyperframes check` / `snapshot` on the render
host: fonts, Chromium version and GPU path differ, and nothing is encoded.

Usage:
  python scripts/frame-review.py <project-slug | path/to/index.html> [--formats a,b] [--samples 12]
         [--at 0,1.5] [--scan-fps 5] [--fonts system|google] [--out DIR] [--strict] [--json]
"""

import argparse
import functools
import http.server
import importlib
import json
import math
import re
import sys
import threading
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

try:
    from PIL import Image, ImageDraw, ImageStat
except ImportError:  # pragma: no cover
    Image = None

TEXT_FLOOR = 0.026     # HyperFrames text_below_floor: 2.6% of the short side
READING_SIZE = 30 / 1080  # HyperFrames line_unread applies to lines >= 30 px at 1080
DEAD_STRETCH_SEC = 3.0

AUDIT_JS = r"""
(args) => {
  const root = document.getElementById('root') || document.querySelector('[data-composition-id]');
  const W = args.width, H = args.height;
  const has = (el, attr) => !!el.closest('[' + attr + ']');
  const effOpacity = (el) => {
    let o = 1, n = el;
    while (n && n.nodeType === 1) {
      const s = getComputedStyle(n);
      if (s.display === 'none') return 0;
      o *= parseFloat(s.opacity);
      if (n === root) break;
      n = n.parentElement;
    }
    return o;
  };
  const parseClip = (cp, rect) => {
    if (!cp || cp === 'none') return null;
    let m = cp.match(/^inset\(([^)]*)\)/);
    if (m) {
      const v = m[1].split(/\s+/).map(x => x.endsWith('%') ? parseFloat(x) / 100 : null);
      if (v.some(x => x === null)) return null;
      const [t, r, b, l] = v.length === 4 ? v : (v.length === 2 ? [v[0], v[1], v[0], v[1]] : (v.length === 3 ? [v[0], v[1], v[2], v[1]] : [v[0], v[0], v[0], v[0]]));
      return { x: rect.x + rect.width * l, y: rect.y + rect.height * t, width: Math.max(0, rect.width * (1 - l - r)), height: Math.max(0, rect.height * (1 - t - b)) };
    }
    m = cp.match(/^circle\(\s*([\d.]+)%/);
    if (m && parseFloat(m[1]) === 0) return { x: rect.x, y: rect.y, width: 0, height: 0 };
    return null;
  };
  const intersect = (a, b) => {
    const x = Math.max(a.x, b.x), y = Math.max(a.y, b.y);
    const r = Math.min(a.x + a.width, b.x + b.width), btm = Math.min(a.y + a.height, b.y + b.height);
    return { x, y, width: Math.max(0, r - x), height: Math.max(0, btm - y) };
  };
  const visibleRect = (el) => {
    let r = el.getBoundingClientRect();
    let rect = { x: r.x, y: r.y, width: r.width, height: r.height };
    let n = el.parentElement;
    while (n && n !== root.parentElement) {
      const s = getComputedStyle(n);
      const nr = n.getBoundingClientRect();
      const box = { x: nr.x, y: nr.y, width: nr.width, height: nr.height };
      if (s.overflow !== 'visible' && n !== root) rect = intersect(rect, box);
      const clip = parseClip(s.clipPath, box);
      if (clip) rect = intersect(rect, clip);
      n = n.parentElement;
    }
    const own = parseClip(getComputedStyle(el).clipPath, { x: r.x, y: r.y, width: r.width, height: r.height });
    if (own) rect = intersect(rect, own);
    return rect;
  };
  const isVisible = (el) => {
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || effOpacity(el) < 0.5) return false;
    const vr = visibleRect(el);
    return vr.width * vr.height > 4;
  };
  const blocks = [];
  root.querySelectorAll('*').forEach((el) => {
    if (has(el, 'data-layout-ignore') || el.closest('svg defs, style, script, title')) return;
    const splitParent = el.hasAttribute('aria-label') && el.querySelector('.st-word');
    const inSplit = !splitParent && el.closest('[aria-label]') && el.closest('[aria-label]').querySelector('.st-word');
    if (inSplit) return;
    let direct = false;
    for (const n of el.childNodes) { if (n.nodeType === 3 && n.nodeValue.trim()) { direct = true; break; } }
    if (!splitParent && !direct) return;
    if (!splitParent && el.closest('[aria-hidden="true"]')) return;
    if (!el.dataset.frId) el.dataset.frId = 'b' + (window.__frSeq = (window.__frSeq || 0) + 1);
    blocks.push({ el, split: !!splitParent });
  });
  const out = [];
  for (const b of blocks) {
    const el = b.el;
    const s = getComputedStyle(el);
    let visible, rect;
    if (b.split) {
      const words = Array.from(el.querySelectorAll('.st-word'));
      const vis = words.filter(isVisible);
      visible = words.length > 0 && vis.length / words.length >= 0.5 && getComputedStyle(el).visibility !== 'hidden';
      const rs = vis.map(w => visibleRect(w));
      if (rs.length) {
        const x = Math.min(...rs.map(r => r.x)), y = Math.min(...rs.map(r => r.y));
        const r2 = Math.max(...rs.map(r => r.x + r.width)), b2 = Math.max(...rs.map(r => r.y + r.height));
        rect = { x, y, width: r2 - x, height: b2 - y };
      } else rect = { x: 0, y: 0, width: 0, height: 0 };
    } else {
      visible = isVisible(el);
      rect = visibleRect(el);
    }
    if (!visible) { out.push({ id: el.dataset.frId, visible: false }); continue; }
    const raw = el.getBoundingClientRect();
    const text = (el.getAttribute('aria-label') || el.textContent || '').replace(/\s+/g, ' ').trim();
    out.push({
      id: el.dataset.frId,
      visible: true,
      tag: el.tagName.toLowerCase(),
      cls: (el.getAttribute('class') || '').toString().slice(0, 60),
      text: text.slice(0, 80),
      words: text ? text.split(' ').length : 0,
      fontSize: parseFloat(s.fontSize) * (el instanceof SVGElement && el.getScreenCTM && el.getScreenCTM() ? Math.hypot(el.getScreenCTM().a, el.getScreenCTM().b) : 1),
      fontWeight: parseInt(s.fontWeight, 10) || 400,
      color: s.color,
      rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
      raw: { x: raw.x, y: raw.y, width: raw.width, height: raw.height },
      allowOverflow: has(el, 'data-layout-allow-overflow') || has(el, 'data-layout-bleed'),
      allowOverlap: el.hasAttribute('data-layout-allow-overlap'),
      allowCaption: has(el, 'data-layout-allow-caption-zone'),
      hold: has(el, 'data-hold')
    });
  }
  const holdVisible = Array.from(root.querySelectorAll('[data-hold]')).some(isVisible);
  return { blocks: out, holdVisible };
}
"""

GOOGLE_FAMILIES = {
    "inter": "Inter", "playfair display": "Playfair Display", "eb garamond": "EB Garamond",
    "archivo black": "Archivo Black", "nunito": "Nunito", "oswald": "Oswald", "jetbrains mono": "JetBrains Mono",
    "ibm plex mono": "IBM Plex Mono", "space mono": "Space Mono", "montserrat": "Montserrat", "outfit": "Outfit",
    "league gothic": "League Gothic", "source code pro": "Source Code Pro", "roboto": "Roboto",
    "open sans": "Open Sans", "lato": "Lato", "poppins": "Poppins",
}


# --------------------------------------------------------------------------- helpers
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(directory: Path) -> http.server.ThreadingHTTPServer:
    handler = functools.partial(QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def parse_rgb(css: str) -> Optional[Tuple[int, int, int]]:
    m = re.match(r"rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)", css or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def luminance(rgb: Tuple[float, float, float]) -> float:
    def ch(c: float) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(rgb[0]) + 0.7152 * ch(rgb[1]) + 0.0722 * ch(rgb[2])


def contrast(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def estimate_background(img, rect: Dict[str, float], text_rgb: Tuple[int, int, int]) -> Optional[Tuple[float, float, float]]:
    W, H = img.size
    x0, y0 = max(0, int(rect["x"])), max(0, int(rect["y"]))
    x1, y1 = min(W, int(rect["x"] + rect["width"])), min(H, int(rect["y"] + rect["height"]))
    if x1 - x0 < 3 or y1 - y0 < 3:
        return None
    crop = img.crop((x0, y0, x1, y1)).convert("RGB")
    crop.thumbnail((80, 80))
    raw = crop.tobytes()
    pixels = [(raw[i], raw[i + 1], raw[i + 2]) for i in range(0, len(raw), 3)]
    far = [p for p in pixels if sum((p[i] - text_rgb[i]) ** 2 for i in range(3)) > 70 ** 2]
    if len(far) < 8:
        return None
    far.sort(key=lambda p: luminance(p))
    return far[len(far) // 2]


def read_root_attrs(html: str) -> Dict[str, str]:
    m = re.search(r"<(?:div|main|section)\b([^>]*?\bdata-composition-id\s*=\s*\"[^\"]+\"[^>]*?)>", html, re.S)
    if not m:
        return {}
    return dict(re.findall(r"([\w:.-]+)\s*=\s*\"([^\"]*)\"", m.group(1)))


def used_google_families(html: str, src_dir: Path) -> List[str]:
    texts = [html]
    for href in re.findall(r"<link[^>]+href=\"([^\"]+\.css)\"", html):
        p = (src_dir / href).resolve()
        if p.exists():
            texts.append(p.read_text(encoding="utf-8", errors="ignore"))
    fams = set()
    for t in texts:
        for decl in re.findall(r"font-family\s*:\s*([^;}{]+)", t):
            for part in decl.split(","):
                name = part.strip().strip("'\"").lower()
                if name in GOOGLE_FAMILIES:
                    fams.add(GOOGLE_FAMILIES[name])
        for decl in re.findall(r"--font-[a-z-]+\s*:\s*([^;}{]+)", t):
            for part in decl.split(","):
                name = part.strip().strip("'\"").lower()
                if name in GOOGLE_FAMILIES:
                    fams.add(GOOGLE_FAMILIES[name])
    return sorted(fams)


_FONT_CSS_CACHE: Dict[str, Optional[str]] = {}


def google_font_css(family: str) -> Optional[str]:
    if family in _FONT_CSS_CACHE:
        return _FONT_CSS_CACHE[family]
    fam = family.replace(" ", "+")
    candidates = [
        f"family={fam}:ital,wght@0,100..900;1,100..900",
        f"family={fam}:wght@100..900",
        f"family={fam}:ital,wght@0,400;0,700;1,400;1,700",
        f"family={fam}:wght@400;700",
        f"family={fam}",
    ]
    css = None
    for q in candidates:
        url = f"https://fonts.googleapis.com/css2?{q}&display=block"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"})
            with urllib.request.urlopen(req, timeout=15) as r:
                css = r.read().decode("utf-8")
            break
        except Exception:
            continue
    _FONT_CSS_CACHE[family] = css
    return css


# --------------------------------------------------------------------------- entries
def resolve_entries(target: str, formats: Optional[List[str]]) -> Tuple[Path, Optional[Path], List[Dict[str, Any]]]:
    """Returns (src_dir, project_dir or None, entries[{id, file, width, height, safe, studio}])."""
    p = Path(target)
    pdir = REPO_ROOT / "projects" / target
    if pdir.is_dir() or (p.is_dir() and (p / "src").is_dir()):
        pdir = pdir if pdir.is_dir() else p.resolve()
        src = pdir / "src"
        if (pdir / "project.json").exists():
            studio = importlib.import_module("studio")
            project = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
            expected = studio.expected_variants(pdir, project)
            stale = [name for name, content in expected.items()
                     if not (src / name).exists() or (src / name).read_text(encoding="utf-8").replace("\r\n", "\n") != content.replace("\r\n", "\n")]
            if stale:
                raise SystemExit(f"Error: format entry files out of date: {', '.join(stale)}. Run: python scripts/studio.py formats {pdir.name}")
            entries = []
            for e in studio.format_entries(project):
                if formats and e["id"] not in formats:
                    continue
                entries.append({"id": e["id"], "file": e["file"], "width": e["width"], "height": e["height"], "safe": e["safe"], "studio": True})
            return src, pdir, entries
        attrs = read_root_attrs((src / "index.html").read_text(encoding="utf-8"))
        w, h = int(attrs.get("data-width", 1280)), int(attrs.get("data-height", 720))
        fid = "landscape" if w > h else ("portrait" if w < h else "square")
        return src, pdir, [{"id": fid, "file": "index.html", "width": w, "height": h, "safe": None, "studio": False}]
    if p.is_file():
        attrs = read_root_attrs(p.read_text(encoding="utf-8"))
        w, h = int(attrs.get("data-width", 1280)), int(attrs.get("data-height", 720))
        fid = attrs.get("data-format") or ("landscape" if w > h else ("portrait" if w < h else "square"))
        return p.resolve().parent, None, [{"id": fid, "file": p.name, "width": w, "height": h, "safe": None, "studio": False}]
    raise SystemExit(f"Error: '{target}' is neither a project under projects/ nor an HTML file.")


# --------------------------------------------------------------------------- review
def review_entry(browser, base_url: str, src_dir: Path, entry: Dict[str, Any], times: List[float], scan_fps: float,
                 fonts: str, out_dir: Path) -> Dict[str, Any]:
    W, H = entry["width"], entry["height"]
    short = min(W, H)
    findings: List[Dict[str, Any]] = []

    def add(code: str, severity: str, message: str, t: Optional[float] = None, block: Optional[Dict[str, Any]] = None):
        f = {"code": code, "severity": severity, "message": message}
        if t is not None:
            f["time"] = round(t, 3)
        if block:
            f["text"] = block.get("text")
            f["class"] = block.get("cls")
        findings.append(f)

    context = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=1)
    page = context.new_page()
    console_errors: List[str] = []
    page.on("pageerror", lambda e: console_errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: console_errors.append(f"console.error: {m.text}") if m.type == "error" else None)
    failed: List[str] = []
    page.on("requestfailed", lambda r: failed.append(f"{r.url} ({r.failure})"))
    page.on("response", lambda r: failed.append(f"{r.url} (HTTP {r.status})") if r.status >= 400 else None)

    html_path = src_dir / entry["file"]
    html = html_path.read_text(encoding="utf-8")
    if fonts == "google":
        fams = used_google_families(html, src_dir)
        css = "\n".join(c for c in (google_font_css(f) for f in fams) if c)
        loads = ",".join(f"document.fonts.load('{w} 1em \"{f}\"')" for f in fams for w in ("400", "700", "italic 400"))
        inject = f"<style id=\"frame-review-fonts\">{css}</style><script>Promise.all([{loads}]).catch(()=>{{}});</script>"
        injected = re.sub(r"<head([^>]*)>", lambda m: f"<head{m.group(1)}>{inject}", html, count=1)
        url_path = f"{base_url}/{entry['file']}"
        page.route(url_path, lambda route: route.fulfill(status=200, content_type="text/html; charset=utf-8", body=injected))

    page.goto(f"{base_url}/{entry['file']}", wait_until="load", timeout=60000)
    comp_id = read_root_attrs(html).get("data-composition-id", "root")
    try:
        page.wait_for_function(
            "(id) => !!((window.__timelines && window.__timelines[id]) || document.querySelector('[data-studio-error]'))",
            arg=comp_id, timeout=25000)
    except Exception:
        add("timeline_missing", "error", f"window.__timelines['{comp_id}'] was never registered.")
    studio_error = page.evaluate("() => { const e = document.querySelector('[data-studio-error]'); return e ? e.getAttribute('data-studio-error') : null; }")
    if studio_error:
        add("studio_build_error", "error", studio_error)
    has_tl = page.evaluate("(id) => !!(window.__timelines && window.__timelines[id])", comp_id)
    duration = float(read_root_attrs(html).get("data-duration", "0") or 0)
    fps = int(read_root_attrs(html).get("data-fps", "30") or 30)
    report: Dict[str, Any] = {"format": entry["id"], "file": entry["file"], "width": W, "height": H, "duration": duration, "fps": fps}
    if not has_tl:
        report.update({"findings": findings, "frames": [], "console": console_errors, "failed_requests": failed})
        context.close()
        return report

    tl_dur = page.evaluate("(id) => window.__timelines[id].duration()", comp_id)
    report["timeline_duration"] = round(tl_dur, 3)
    if duration and tl_dur > duration + 0.05:
        add("timeline_past_end", "warning", f"timeline runs {tl_dur:.2f}s but data-duration is {duration:g}s; the tail never renders.")

    def seek(t: float) -> float:
        frame = max(0, min(int(round(t * fps)), int(math.floor(duration * fps)) - 1))
        tq = frame / fps
        page.evaluate("([id, t]) => { const tl = window.__timelines[id]; tl.pause(); tl.seek(t); }", [comp_id, tq])
        return tq

    safe = entry.get("safe")
    safe_rect = None
    if safe:
        safe_rect = {"x": safe["left"] * W, "y": safe["top"] * H, "x2": W - safe["right"] * W, "y2": H - safe["bottom"] * H}

    fmt_dir = out_dir / entry["id"]
    fmt_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    floor_px = TEXT_FLOOR * short
    for i, t in enumerate(times):
        tq = seek(t)
        shot = fmt_dir / f"f{i:02d}-t{tq:06.2f}.png"
        page.screenshot(path=str(shot))
        audit = page.evaluate(AUDIT_JS, {"width": W, "height": H})
        img = Image.open(shot).convert("RGB") if Image else None
        vis = [b for b in audit["blocks"] if b["visible"]]
        for b in vis:
            r = b["rect"]
            if not b["allowOverflow"]:
                raw = b["raw"]
                if raw["x"] < -2 or raw["y"] < -2 or raw["x"] + raw["width"] > W + 2 or raw["y"] + raw["height"] > H + 2:
                    if r["width"] * r["height"] < raw["width"] * raw["height"] * 0.98:
                        add("text_clipped_by_frame", "error", "visible text is cut off by the frame edge", tq, b)
            if b["fontSize"] < floor_px - 0.5:
                add("text_below_floor", "warning", f"{b['fontSize']:.1f}px text is under the {floor_px:.1f}px floor (2.6% of {short}px)", tq, b)
            if safe_rect and not b["allowOverflow"] and not b["allowCaption"]:
                if r["x"] < safe_rect["x"] - 2 or r["y"] < safe_rect["y"] - 2 or r["x"] + r["width"] > safe_rect["x2"] + 2 or r["y"] + r["height"] > safe_rect["y2"] + 2:
                    add("outside_safe_area", "warning", "text extends outside the format's safe area", tq, b)
            rgb = parse_rgb(b["color"])
            if img is not None and rgb:
                bg = estimate_background(img, r, rgb)
                if bg is not None:
                    ratio = contrast(rgb, bg)
                    large = b["fontSize"] >= 24 or (b["fontSize"] >= 18.66 and b["fontWeight"] >= 700)
                    need = 3.0 if large else 4.5
                    if ratio < need:
                        add("low_contrast", "warning", f"estimated contrast {ratio:.1f}:1 < {need}:1", tq, b)
        for a_i in range(len(vis)):
            for b_i in range(a_i + 1, len(vis)):
                a, b = vis[a_i], vis[b_i]
                if a["allowOverlap"] or b["allowOverlap"]:
                    continue
                ra, rb = a["rect"], b["rect"]
                ix = max(0, min(ra["x"] + ra["width"], rb["x"] + rb["width"]) - max(ra["x"], rb["x"]))
                iy = max(0, min(ra["y"] + ra["height"], rb["y"] + rb["height"]) - max(ra["y"], rb["y"]))
                small = min(ra["width"] * ra["height"], rb["width"] * rb["height"])
                if small > 0 and ix * iy / small > 0.15:
                    findings.append({"code": "_overlap_sample", "severity": "info", "time": round(tq, 3), "a": a["text"], "b": b["text"], "pair": f"{a['id']}|{b['id']}"})
        frames.append({"time": round(tq, 3), "path": shot.relative_to(REPO_ROOT).as_posix() if shot.is_relative_to(REPO_ROOT) else str(shot), "visible_text": [b["text"] for b in vis]})

    # Persistent overlaps become errors; single-sample overlaps (transitions in flight) stay info.
    pairs: Dict[str, List[Dict[str, Any]]] = {}
    for f in [f for f in findings if f["code"] == "_overlap_sample"]:
        pairs.setdefault(f["pair"], []).append(f)
    findings[:] = [f for f in findings if f["code"] != "_overlap_sample"]
    for pair, hits in pairs.items():
        sev = "error" if len(hits) >= 2 else "info"
        add("text_overlap", sev, f"'{hits[0]['a']}' overlaps '{hits[0]['b']}' in {len(hits)} sampled frame(s)", hits[0]["time"])

    # Motion scan: dead stretches, blank frames, reading time.
    step = 1.0 / scan_fps
    n_scan = int(math.floor(duration / step)) + 1 if duration else 0
    prev = None
    static_start = None
    dead: List[Tuple[float, float]] = []
    visible_spans: Dict[str, List[float]] = {}
    block_meta: Dict[str, Dict[str, Any]] = {}
    blank: List[float] = []
    for k in range(n_scan):
        tq = seek(k * step)
        png = page.screenshot(type="jpeg", quality=60)
        audit = page.evaluate(AUDIT_JS, {"width": W, "height": H})
        for b in audit["blocks"]:
            if b["visible"]:
                visible_spans.setdefault(b["id"], []).append(tq)
                block_meta.setdefault(b["id"], b)
        if Image:
            import io
            im = Image.open(io.BytesIO(png)).convert("L")
            im.thumbnail((320, 320))
            stat = ImageStat.Stat(im)
            if stat.stddev[0] < 1.5 and 0 < tq < duration - step:
                blank.append(tq)
            if k == 0 and stat.stddev[0] < 1.5:
                add("first_frame_empty", "warning", "frame 0 shows only the background (social thumbnails use the first frame)", 0.0)
            cur = im.tobytes()
            if prev is not None:
                # Seeked frames are deterministic, so any pixel moving > 10 levels is real change.
                changed = sum(1 for a, b in zip(cur, prev) if abs(a - b) > 10)
                moving = changed >= 4 or audit["holdVisible"]
                if not moving and static_start is None:
                    static_start = tq - step
                if moving and static_start is not None:
                    dead.append((static_start, tq - step))
                    static_start = None
            prev = cur
    if static_start is not None:
        dead.append((static_start, duration))
    for a, b in dead:
        if b - a > DEAD_STRETCH_SEC and a < duration - DEAD_STRETCH_SEC:
            add("dead_stretch", "warning", f"nothing changes for {b - a:.1f}s ({a:.1f}s to {b:.1f}s)", a)
    if blank:
        add("blank_frames", "warning", f"{len(blank)} scanned frame(s) are a flat colour (first at {blank[0]:.2f}s)", blank[0])
    reading_px = READING_SIZE * short
    last_t = (n_scan - 1) * step if n_scan else 0
    for bid, ts in visible_spans.items():
        meta = block_meta[bid]
        if meta["fontSize"] < reading_px or not meta["words"]:
            continue
        spans, start, last = [], ts[0], ts[0]
        for t in ts[1:]:
            if t - last > step * 1.5:
                spans.append((start, last + step))
                start = t
            last = t
        spans.append((start, last + step))
        words = meta["words"]
        floor = 0.4 if words <= 2 else 0.75 * (0.5 + 0.3 * words)
        for a, b in spans:
            ends_film = b >= last_t
            need = 2.0 if ends_film else floor
            if b - a + 1e-6 < need:
                add("line_unread", "warning", f"{words}-word text visible {b - a:.1f}s (needs ~{need:.1f}s)", a, meta)

    for msg in console_errors:
        add("console_error", "error", msg)
    for msg in failed:
        add("request_failed", "error", msg)

    report.update({"frames": frames, "findings": findings, "console": console_errors, "failed_requests": failed,
                   "dead_stretches": [[round(a, 2), round(b, 2)] for a, b in dead if b - a > DEAD_STRETCH_SEC]})
    context.close()
    return report


def dedupe(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for f in findings:
        key = (f["code"], f.get("text") or "", f["message"].split(" in ")[0] if f["code"] == "text_overlap" else f.get("message"))
        if f["code"] in {"text_below_floor", "outside_safe_area", "low_contrast", "text_clipped_by_frame"}:
            key = (f["code"], f.get("text") or "", "")
        if key in seen:
            seen[key]["count"] = seen[key].get("count", 1) + 1
        else:
            seen[key] = dict(f)
    out = []
    for f in seen.values():
        # A size/contrast/safe-area finding seen in one sampled frame only is likely mid-transition.
        if f["code"] in {"low_contrast", "outside_safe_area"} and f.get("count", 1) < 2:
            f["severity"] = "info"
        out.append(f)
    return out


# --------------------------------------------------------------------------- sheets
def contact_sheet(frames: List[Dict[str, Any]], out: Path, title: str, cols: int = 4, cell_w: int = 360) -> None:
    if not Image or not frames:
        return
    imgs = [Image.open(REPO_ROOT / f["path"] if not Path(f["path"]).is_absolute() else f["path"]).convert("RGB") for f in frames]
    w0, h0 = imgs[0].size
    cell_h = int(cell_w * h0 / w0)
    rows = math.ceil(len(imgs) / cols)
    pad, label = 10, 22
    sheet = Image.new("RGB", (cols * (cell_w + pad) + pad, 36 + rows * (cell_h + label + pad) + pad), (238, 234, 226))
    draw = ImageDraw.Draw(sheet)
    draw.text((pad, 10), title, fill=(30, 27, 22))
    for i, (im, f) in enumerate(zip(imgs, frames)):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = 36 + r * (cell_h + label + pad)
        sheet.paste(im.resize((cell_w, cell_h)), (x, y))
        draw.text((x, y + cell_h + 4), f"t = {f['time']:.2f}s", fill=(60, 55, 48))
    sheet.save(out)


def matrix_sheet(reports: List[Dict[str, Any]], out: Path, cell_h: int = 240) -> None:
    if not Image or len(reports) < 2:
        return
    n = min(len(r["frames"]) for r in reports)
    widths = [int(cell_h * r["width"] / r["height"]) for r in reports]
    pad, label = 10, 18
    W = pad + sum(w + pad for w in widths) + 70
    H = 30 + n * (cell_h + pad) + pad
    sheet = Image.new("RGB", (W, H), (238, 234, 226))
    draw = ImageDraw.Draw(sheet)
    x = 70 + pad
    for r, w in zip(reports, widths):
        draw.text((x, 10), f"{r['format']} {r['width']}x{r['height']}", fill=(30, 27, 22))
        x += w + pad
    for i in range(n):
        y = 30 + i * (cell_h + pad)
        draw.text((pad, y + cell_h // 2), f"{reports[0]['frames'][i]['time']:.2f}s", fill=(60, 55, 48))
        x = 70 + pad
        for r, w in zip(reports, widths):
            im = Image.open(REPO_ROOT / r["frames"][i]["path"]).convert("RGB").resize((w, cell_h))
            sheet.paste(im, (x, y))
            x += w + pad
    sheet.save(out)


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description="Preview-grade frame review for HyperFrames compositions")
    ap.add_argument("target", help="project slug under projects/ or a path to an HTML composition")
    ap.add_argument("--formats", help="comma-separated subset of formats (studio projects)")
    ap.add_argument("--samples", type=int, default=12, help="evenly spaced review frames per format")
    ap.add_argument("--at", help="explicit comma-separated sample times (seconds)")
    ap.add_argument("--scan-fps", type=float, default=5.0, help="motion/reading scan rate")
    ap.add_argument("--fonts", choices=["system", "google"], default="system",
                    help="google: inject the HyperFrames-bundled families from Google Fonts (network) for closer typography")
    ap.add_argument("--out", help="output directory (default: <project>/qa/frame-review)")
    ap.add_argument("--serve-root", help="serve this ancestor folder instead of the composition's folder, so relative assets above it "
                                         "resolve (e.g. '.' for test pages that load ../../../src/studio)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ap.add_argument("--json", action="store_true", help="print the JSON report")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if sync_playwright is None or Image is None:
        print("Error: frame-review needs the 'playwright' (with Chromium) and 'Pillow' Python packages.")
        return 2

    formats = [f.strip() for f in args.formats.split(",")] if args.formats else None
    src_dir, pdir, entries = resolve_entries(args.target, formats)
    if not entries:
        print("Error: no matching formats.")
        return 2
    out_dir = Path(args.out).resolve() if args.out else ((pdir / "qa" / "frame-review") if pdir else (src_dir / "frame-review"))
    out_dir.mkdir(parents=True, exist_ok=True)

    first_html = (src_dir / entries[0]["file"]).read_text(encoding="utf-8")
    duration = float(read_root_attrs(first_html).get("data-duration", "0") or 0)
    if args.at:
        times = [float(x) for x in args.at.split(",") if x.strip()]
    else:
        n = max(2, args.samples)
        end = max(0.0, duration - 1.0 / 30)
        times = [round(end * i / (n - 1), 3) for i in range(n)]

    server = serve(src_dir)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    if args.serve_root:
        root = Path(args.serve_root).resolve()
        if not src_dir.resolve().is_relative_to(root):
            print(f"Error: --serve-root {root} does not contain {src_dir}.")
            return 2
        server.shutdown()
        server = serve(root)
        prefix = src_dir.resolve().relative_to(root).as_posix()
        base_url = f"http://127.0.0.1:{server.server_address[1]}" + (f"/{prefix}" if prefix not in ("", ".") else "")
    reports = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for entry in entries:
                print(f"[frame-review] {entry['id']} {entry['width']}x{entry['height']} ({entry['file']})", flush=True)
                rep = review_entry(browser, base_url, src_dir, entry, times, args.scan_fps, args.fonts, out_dir)
                rep["findings"] = dedupe(rep["findings"])
                sheet = out_dir / f"contact-{entry['id']}.png"
                contact_sheet(rep["frames"], sheet, f"{entry['id']} {entry['width']}x{entry['height']} - {entry['file']}")
                rep["contact_sheet"] = sheet.relative_to(REPO_ROOT).as_posix() if sheet.is_relative_to(REPO_ROOT) else str(sheet)
                reports.append(rep)
            browser.close()
    finally:
        server.shutdown()

    matrix = out_dir / "contact-matrix.png"
    matrix_sheet(reports, matrix)
    errors = sum(1 for r in reports for f in r["findings"] if f["severity"] == "error")
    warnings = sum(1 for r in reports for f in r["findings"] if f["severity"] == "warning")
    summary = {
        "target": args.target,
        "fonts": args.fonts,
        "renderer": "playwright-chromium (preview-grade; not the HyperFrames render path)",
        "sample_times": times,
        "formats": reports,
        "matrix": matrix.relative_to(REPO_ROOT).as_posix() if matrix.exists() and matrix.is_relative_to(REPO_ROOT) else None,
        "errors": errors,
        "warnings": warnings,
        "passed": errors == 0 and (warnings == 0 or not args.strict),
    }
    (out_dir / "report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        for r in reports:
            print(f"\n== {r['format']} {r['width']}x{r['height']} ({r['file']}) timeline {r.get('timeline_duration', 'n/a')}s / data-duration {r['duration']}s")
            for f in sorted(r["findings"], key=lambda f: ({"error": 0, "warning": 1, "info": 2}[f["severity"]], f.get("time", 0))):
                where = f" @{f['time']:.2f}s" if "time" in f else ""
                count = f" x{f['count']}" if f.get("count", 1) > 1 else ""
                text = f" [{f['text']}]" if f.get("text") else ""
                print(f"  {f['severity'].upper():7} {f['code']}{where}{count}: {f['message']}{text}")
            print(f"  sheet: {r.get('contact_sheet')}")
        if summary["matrix"]:
            print(f"\nCross-format matrix: {summary['matrix']}")
        print(f"\n{'PASS' if summary['passed'] else 'FAIL'}: {errors} error(s), {warnings} warning(s). Report: {(out_dir / 'report.json').as_posix()}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
