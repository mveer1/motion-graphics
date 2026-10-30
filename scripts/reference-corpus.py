#!/usr/bin/env python3
"""
scripts/reference-corpus.py
Reference corpus: ingest reference videos, measure them and prepare evidence for analysis.

The corpus is a set of user-supplied videos that stay OUTSIDE the repository. Each one gets a
stable content-derived ID (ref-<first 10 hex of SHA-256>) and a record in
catalogue/data/reference-sources/. Analysis artefacts (sampled frames, contact sheets, strips,
signal data) are a regenerable local cache under out/reference-analysis/<id>/ and are never
committed: they contain third-party imagery, possibly including brand marks.

What the tool does (measurement):            What it does not do (judgement):
  metadata from the MP4 boxes (no ffprobe)     describe concept, typography, easing, motifs
  SHA-256, duplicate detection by content      decide what a technique is or whether to build it
  adaptive scene/transition detection          clear rights or brand use
  contact sheets, transition and motion strips
  colour palette, static holds, activity
  audio envelope, onsets, tempo estimate, cut/onset alignment
The analyst (an agent using the reference-analyst skill, or a person) looks at the evidence and
writes the `analysis`, `techniques` and `rights` blocks; this tool only rewrites `media` and
`automated`, so re-running it never overwrites authored analysis.

Decoders: a Chromium-family browser with H.264 (Edge or Chrome via Playwright channels), or
FFmpeg on PATH. Playwright's bundled Chromium has no H.264 decoder.

Usage:
  python scripts/reference-corpus.py doctor [--file F]
  python scripts/reference-corpus.py ingest <file-or-dir>... [--dry-run]
  python scripts/reference-corpus.py analyze <ref-id>... | --pending | --all  [--force] [--backend auto|browser|ffmpeg]
  python scripts/reference-corpus.py strip <ref-id> --from 3.2 --to 4.4 [--fps 15]
  python scripts/reference-corpus.py status
  python scripts/reference-corpus.py locate <ref-id>
  python scripts/reference-corpus.py check --name "..." [--tags a,b] [--text "..."]
  python scripts/reference-corpus.py report [--backlog]
Files are found through --root DIR (repeatable) or MOTION_REFERENCE_ROOTS (os.pathsep list).
"""

import argparse
import base64
import datetime as _dt
import hashlib
import io
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "catalogue" / "data"
SOURCES_DIR = DATA_DIR / "reference-sources"
TECHNIQUES_DIR = DATA_DIR / "references"
SCHEMA_PATH = REPO_ROOT / "catalogue" / "schemas" / "reference-source.schema.json"
CACHE_DIR = REPO_ROOT / "out" / "reference-analysis"
ANALYZER_VERSION = "1.2"
VIDEO_EXTS = {".mp4", ".m4v", ".mov"}
ROOTS_ENV = "MOTION_REFERENCE_ROOTS"

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None
try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    Image = None


def today() -> str:
    return _dt.date.today().isoformat()


def rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(p)


# =============================================================================== MP4 probe
class Mp4Error(ValueError):
    pass


def _boxes(f, start: int, end: int):
    """Yield (type, payload_start, box_end) for boxes in [start, end)."""
    pos = start
    while pos + 8 <= end:
        f.seek(pos)
        hdr = f.read(8)
        if len(hdr) < 8:
            return
        size, typ = struct.unpack(">I4s", hdr)
        head = 8
        if size == 1:
            size = struct.unpack(">Q", f.read(8))[0]
            head = 16
        elif size == 0:
            size = end - pos
        if size < head or pos + size > end + 8:  # tolerate a few bytes of slack at file end
            raise Mp4Error(f"corrupt box '{typ!r}' at {pos}")
        yield typ.decode("latin-1"), pos + head, min(pos + size, end)
        pos += size


def _find(f, start, end, path: List[str]):
    for typ, ps, pe in _boxes(f, start, end):
        if typ == path[0]:
            if len(path) == 1:
                yield ps, pe
            else:
                skip = _meta_skip(f, ps) if typ == "meta" else 0
                yield from _find(f, ps + skip, pe, path[1:])


def _meta_skip(f, ps) -> int:
    """ISO 'meta' is a FullBox (4 bytes version/flags first); QuickTime 'meta' starts with children."""
    f.seek(ps + 4)
    return 0 if f.read(4) in (b"hdlr", b"ilst", b"xml ", b"keys") else 4


def _read(f, pos, n) -> bytes:
    f.seek(pos)
    return f.read(n)


def _fps_label(fps: float) -> float:
    for nominal in (23.976, 24, 25, 29.97, 30, 48, 50, 59.94, 60, 120):
        if abs(fps - nominal) < 0.01:
            return nominal
    return round(fps, 3)


def probe_mp4(path: Path) -> Dict[str, Any]:
    """Technical metadata from ISO-BMFF boxes. Raises Mp4Error when the file is unreadable."""
    size = path.stat().st_size
    out: Dict[str, Any] = {"container": "mp4", "bytes": size, "probe": "mp4-box-parser/1"}
    with open(path, "rb") as f:
        top = list(_boxes(f, 0, size))
        types = [t for t, _, _ in top]
        if "moov" not in types:
            raise Mp4Error("no 'moov' box (not an MP4/MOV file, or truncated)")
        for t, ps, pe in top:
            if t == "ftyp":
                d = _read(f, ps, min(pe - ps, 64))
                out["brand"] = d[:4].decode("latin-1").strip()
                out["compatible_brands"] = [d[i:i + 4].decode("latin-1").strip() for i in range(8, len(d) - 3, 4)]
        out["faststart"] = types.index("moov") < types.index("mdat") if "mdat" in types else None
        moov = next((ps, pe) for t, ps, pe in top if t == "moov")
        for ps, pe in _find(f, moov[0], moov[1], ["mvhd"]):
            d = _read(f, ps, 32)
            if d[0] == 1:
                ts, dur = struct.unpack(">IQ", _read(f, ps + 20, 12))
            else:
                ts, dur = struct.unpack(">II", d[12:20])
            out["duration_sec"] = round(dur / ts, 3) if ts else None
        for ps, pe in _find(f, moov[0], moov[1], ["udta", "meta", "ilst"]):
            for t, ips, ipe in _boxes(f, ps, pe):
                if t in ("\xa9too", "\xa9enc"):
                    for dt, dps, dpe in _boxes(f, ips, ipe):
                        if dt == "data":
                            out["encoder"] = _read(f, dps + 8, dpe - dps - 8).decode("utf-8", "replace")
        tracks = []
        for tps, tpe in _find(f, moov[0], moov[1], ["trak"]):
            tr: Dict[str, Any] = {}
            for ps, pe in _find(f, tps, tpe, ["mdia", "hdlr"]):
                tr["handler"] = _read(f, ps + 8, 4).decode("latin-1")
            for ps, pe in _find(f, tps, tpe, ["mdia", "mdhd"]):
                d = _read(f, ps, 32)
                if d[0] == 1:
                    ts, dur = struct.unpack(">IQ", _read(f, ps + 20, 12))
                else:
                    ts, dur = struct.unpack(">II", d[12:20])
                tr["timescale"], tr["duration_units"] = ts, dur
            stbl = list(_find(f, tps, tpe, ["mdia", "minf", "stbl"]))
            if not stbl:
                continue
            sps, spe = stbl[0]
            for ps, pe in _find(f, sps, spe, ["stsd"]):
                entries = list(_boxes(f, ps + 8, pe))
                if entries:
                    codec, eps, epe = entries[0]
                    tr["codec"] = codec
                    if tr.get("handler") == "vide":
                        w, h = struct.unpack(">HH", _read(f, eps + 24, 4))
                        tr["width"], tr["height"] = w, h
                        for ct, cps, cpe in _boxes(f, eps + 78, epe):
                            if ct == "avcC":
                                c = _read(f, cps, 4)
                                tr["codec_string"] = f"avc1.{c[1]:02x}{c[2]:02x}{c[3]:02x}"
                                tr["profile_idc"], tr["level_idc"] = c[1], c[3]
                    elif tr.get("handler") == "soun":
                        ch, bits = struct.unpack(">HH", _read(f, eps + 16, 4))
                        rate = struct.unpack(">I", _read(f, eps + 24, 4))[0] >> 16
                        tr["channels"], tr["sample_bits"], tr["sample_rate"] = ch, bits, rate
            for ps, pe in _find(f, sps, spe, ["stts"]):
                n = struct.unpack(">I", _read(f, ps + 4, 4))[0]
                raw = _read(f, ps + 8, 8 * n)
                pairs = [struct.unpack(">II", raw[i * 8:i * 8 + 8]) for i in range(n)]
                tr["sample_count"] = sum(c for c, _ in pairs)
                tr["stts_entries"] = n
                if pairs:
                    tr["main_delta"] = max(pairs, key=lambda p: p[0])[1]
            for ps, pe in _find(f, sps, spe, ["stsz"]):
                fixed, n = struct.unpack(">II", _read(f, ps + 4, 8))
                if fixed:
                    tr["payload_bytes"] = fixed * n
                else:
                    raw = _read(f, ps + 12, 4 * n)
                    tr["payload_bytes"] = sum(struct.unpack(f">{n}I", raw)) if n else 0
            for ps, pe in _find(f, sps, spe, ["stss"]):
                tr["keyframes"] = struct.unpack(">I", _read(f, ps + 4, 4))[0]
            tracks.append(tr)
    vid = next((t for t in tracks if t.get("handler") == "vide"), None)
    aud = next((t for t in tracks if t.get("handler") == "soun"), None)
    if not vid:
        raise Mp4Error("no video track")
    vdur = vid["duration_units"] / vid["timescale"] if vid.get("timescale") else out.get("duration_sec")
    out["duration_sec"] = round(vdur, 3) if vdur else out.get("duration_sec")
    out["width"], out["height"] = vid.get("width"), vid.get("height")
    out["video_codec"] = vid.get("codec_string") or vid.get("codec")
    out["frame_count"] = vid.get("sample_count")
    out["variable_frame_rate"] = (vid.get("stts_entries") or 1) > 2
    if out["variable_frame_rate"] and vid.get("sample_count") and vdur:
        out["fps"] = _fps_label(vid["sample_count"] / vdur)
        out["fps_exact"] = f"average of {vid['stts_entries']} timing runs"
    elif vid.get("main_delta") and vid.get("timescale"):
        out["fps"] = _fps_label(vid["timescale"] / vid["main_delta"])
        out["fps_exact"] = f"{vid['timescale']}/{vid['main_delta']}"
    elif vid.get("sample_count") and vdur:
        out["fps"] = _fps_label(vid["sample_count"] / vdur)
    if vid.get("payload_bytes") and vdur:
        out["video_kbps"] = round(vid["payload_bytes"] * 8 / vdur / 1000)
    if vid.get("keyframes") and vid.get("sample_count"):
        out["keyframes"] = vid["keyframes"]
    if aud:
        adur = aud["duration_units"] / aud["timescale"] if aud.get("timescale") else None
        out["audio"] = {
            "codec": aud.get("codec"),
            "sample_rate": aud.get("sample_rate") or aud.get("timescale"),
            "channels": aud.get("channels"),
            "duration_sec": round(adur, 3) if adur else None,
            "kbps": round(aud["payload_bytes"] * 8 / adur / 1000) if aud.get("payload_bytes") and adur else None,
        }
    else:
        out["audio"] = None
    if out.get("duration_sec"):
        out["overall_kbps"] = round(size * 8 / out["duration_sec"] / 1000)
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref_id_for(digest: str) -> str:
    return "ref-" + digest[:10]


# =============================================================================== records
def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_sources(sources_dir: Path = SOURCES_DIR) -> Dict[str, Dict[str, Any]]:
    out = {}
    if sources_dir.exists():
        for p in sorted(sources_dir.glob("*.json")):
            d = load_json(p)
            out[d["id"]] = d
    return out


def load_techniques(tech_dir: Path = TECHNIQUES_DIR) -> Dict[str, Dict[str, Any]]:
    out = {}
    if tech_dir.exists():
        for p in sorted(tech_dir.glob("*.json")):
            d = load_json(p)
            out[d["id"]] = d
    return out


def validate_source(record: Dict[str, Any]) -> List[str]:
    try:
        import jsonschema
    except ImportError:
        return []
    if not SCHEMA_PATH.exists():
        return [f"schema missing: {rel(SCHEMA_PATH)}"]
    v = jsonschema.Draft7Validator(load_json(SCHEMA_PATH))
    return [f"{'/'.join(str(x) for x in e.path) or '(root)'}: {e.message}" for e in v.iter_errors(record)]


def new_source_record(digest: str, path: Path, media: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": ref_id_for(digest),
        "name": f"Reference video {path.name}",
        "status": "proposed",
        "source": {
            "filename": path.name,
            "aliases": [],
            "sha256": digest,
            "bytes": media["bytes"],
            "location": "external: user reference folder (resolve with --root or MOTION_REFERENCE_ROOTS); never copied into the repository",
            "supplied_by": "user",
            "supplied_on": today(),
            "url": None,
            "creator": "unknown",
            "publisher": "unknown",
        },
        "rights": {
            "licence": "unknown",
            "usage": "inspiration-only",
            "attribution": "Unknown creator; supplied by the user as a private study reference.",
            "brand_assets": [],
            "notes": "Rights unverified. Study techniques only; never reuse footage, frames, logos, characters, UI or exact compositions.",
        },
        "media": media,
        "analysis": {"state": "pending"},
        "techniques": [],
        "related": {"effects": [], "compositions": [], "templates": [], "styles": []},
        "categories": [],
        "tags": ["reference-video"],
        "confidence": "low",
        "metadata": {"created_at": today(), "updated_at": today()},
    }


# =============================================================================== locating files
def reference_roots(extra: Optional[List[str]] = None) -> List[Path]:
    roots = [Path(r) for r in (extra or [])]
    env = os.environ.get(ROOTS_ENV, "")
    roots += [Path(r) for r in env.split(os.pathsep) if r.strip()]
    return [r for r in roots if r.is_dir()]


def iter_videos(paths: Iterable[str]) -> List[Path]:
    out = []
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            out += sorted(x for x in pp.iterdir() if x.is_file() and x.suffix.lower() in VIDEO_EXTS)
        elif pp.is_file():
            out.append(pp)
        else:
            print(f"[warn] not found: {p}")
    return out


def locate(record: Dict[str, Any], roots: List[Path], verify: bool = True) -> Optional[Path]:
    """Find the file for a record by filename (then aliases) in the roots; verify size and hash."""
    names = [record["source"]["filename"]] + list(record["source"].get("aliases", []))
    for root in roots:
        for name in names:
            cand = root / name
            if cand.is_file() and cand.stat().st_size == record["source"]["bytes"]:
                if not verify or sha256_file(cand) == record["source"]["sha256"]:
                    return cand
    # Renamed files: same size, same hash.
    for root in roots:
        for cand in root.iterdir():
            if cand.is_file() and cand.suffix.lower() in VIDEO_EXTS and cand.stat().st_size == record["source"]["bytes"]:
                if sha256_file(cand) == record["source"]["sha256"]:
                    return cand
    return None


# =============================================================================== ingest
def ingest(paths: List[Path], sources_dir: Path = SOURCES_DIR, dry_run: bool = False) -> List[Dict[str, Any]]:
    """Create or update source records. Never touches technique, effect or composition records."""
    existing = load_sources(sources_dir)
    by_hash = {r["source"]["sha256"]: r for r in existing.values()}
    results = []
    for path in paths:
        entry = {"file": str(path)}
        try:
            media = probe_mp4(path)
        except (Mp4Error, OSError, struct.error) as exc:
            entry.update({"action": "rejected", "reason": f"unreadable: {exc}"})
            results.append(entry)
            continue
        if not media.get("duration_sec") or not media.get("width"):
            entry.update({"action": "rejected", "reason": "no duration or frame size in the container"})
            results.append(entry)
            continue
        digest = sha256_file(path)
        rid = ref_id_for(digest)
        entry["id"] = rid
        rec = by_hash.get(digest)
        if rec is None:
            rec = new_source_record(digest, path, media)
            entry["action"] = "created"
        else:
            changed = False
            if path.name != rec["source"]["filename"] and path.name not in rec["source"].get("aliases", []):
                rec["source"].setdefault("aliases", []).append(path.name)
                changed = True
            if rec.get("media", {}).get("probe") != media["probe"] or rec.get("media") != media:
                rec["media"] = media
                changed = True
            entry["action"] = "updated (alias/metadata)" if changed else "unchanged (same content already registered)"
            if changed:
                rec["metadata"]["updated_at"] = today()
        errs = validate_source(rec)
        if errs:
            entry.update({"action": "invalid", "reason": "; ".join(errs[:3])})
        elif not dry_run and entry["action"] != "unchanged (same content already registered)":
            save_json(sources_dir / f"{rid}.json", rec)
        by_hash[digest] = rec
        entry["duration_sec"] = media["duration_sec"]
        entry["size"] = f"{media['width']}x{media['height']}@{media.get('fps')}"
        results.append(entry)
    return results


# =============================================================================== decoders
PAGE_HTML = r"""<!doctype html><html><body style="margin:0;background:#000">
<input type="file" id="f"><video id="v" muted playsinline preload="auto"></video><canvas id="c"></canvas>
<script>
const V = document.getElementById('v'), C = document.getElementById('c');
const X = C.getContext('2d', { willReadFrequently: true });
function b64(u8) { let s = ''; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); }
async function seek(t) {
  await new Promise((res) => {
    const done = () => { clearTimeout(timer); res(); };
    const timer = setTimeout(done, 4000);
    V.addEventListener('seeked', done, { once: true });
    V.currentTime = t;
  });
}
window.__open = async () => {
  V.src = URL.createObjectURL(document.getElementById('f').files[0]);
  await new Promise((res, rej) => { V.onloadeddata = res; V.onerror = () => rej(new Error('media error ' + (V.error && V.error.code))); });
  return { duration: V.duration, width: V.videoWidth, height: V.videoHeight };
};
window.__scan = async (times, w, h) => {
  C.width = w; C.height = h;
  const out = new Uint8Array(times.length * w * h * 3);
  for (let i = 0; i < times.length; i++) {
    await seek(times[i]);
    X.drawImage(V, 0, 0, w, h);
    const d = X.getImageData(0, 0, w, h).data;
    for (let p = 0, q = i * w * h * 3; p < d.length; p += 4) { out[q++] = d[p]; out[q++] = d[p + 1]; out[q++] = d[p + 2]; }
  }
  return b64(out);
};
window.__frames = async (times, w) => {
  const h = Math.round(w * V.videoHeight / V.videoWidth / 2) * 2;
  C.width = w; C.height = h;
  const out = [];
  for (const t of times) { await seek(t); X.drawImage(V, 0, 0, w, h); out.push(C.toDataURL('image/jpeg', 0.9)); }
  return out;
};
window.__audio = async (sr) => {
  const buf = await document.getElementById('f').files[0].arrayBuffer();
  let ab;
  try { ab = await new OfflineAudioContext(1, 1, sr).decodeAudioData(buf); } catch (e) { return { error: String(e) }; }
  const n = ab.length, ch = ab.numberOfChannels, mono = new Float32Array(n);
  for (let c = 0; c < ch; c++) { const d = ab.getChannelData(c); for (let i = 0; i < n; i++) mono[i] += d[i] / ch; }
  const pcm = new Int16Array(n);
  for (let i = 0; i < n; i++) pcm[i] = Math.max(-32768, Math.min(32767, Math.round(mono[i] * 32767)));
  return { sr: ab.sampleRate, channels: ch, n: n, pcm: b64(new Uint8Array(pcm.buffer)) };
};
window.__h264 = () => document.createElement('video').canPlayType('video/mp4; codecs="avc1.640028"');
</script></body></html>"""


class BrowserDecoder:
    """Decodes through a Chromium-family browser with proprietary codecs (Edge or Chrome)."""
    name = "browser"

    def __init__(self, channel: Optional[str] = None):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self.browser = None
        errors = []
        for ch in ([channel] if channel else ["msedge", "chrome"]):
            try:
                self.browser = self._pw.chromium.launch(channel=ch)
                self.channel = ch
                break
            except Exception as exc:  # channel not installed
                errors.append(f"{ch}: {str(exc).splitlines()[0]}")
        if self.browser is None:
            self._pw.stop()
            raise RuntimeError("no H.264-capable browser channel (" + "; ".join(errors) + ")")
        self.version = self.browser.version
        self.page = None

    def open(self, path: Path) -> Dict[str, Any]:
        if self.page:
            self.page.close()
        self.page = self.browser.new_page()
        self.page.set_content(PAGE_HTML)
        if not self.page.evaluate("window.__h264()"):
            raise RuntimeError(f"browser channel {self.channel} cannot decode H.264")
        self.page.set_input_files("#f", str(path))
        return self.page.evaluate("window.__open()")

    def scan(self, times: List[float], w: int, h: int):
        frames = []
        for i in range(0, len(times), 120):
            chunk = times[i:i + 120]
            raw = base64.b64decode(self.page.evaluate("([t,w,h]) => window.__scan(t,w,h)", [chunk, w, h]))
            frames.append(np.frombuffer(raw, dtype=np.uint8).reshape(len(chunk), h, w, 3))
        return np.concatenate(frames) if frames else np.zeros((0, h, w, 3), np.uint8)

    def frames(self, times: List[float], width: int) -> List["Image.Image"]:
        out = []
        for i in range(0, len(times), 24):
            for url in self.page.evaluate("([t,w]) => window.__frames(t,w)", [times[i:i + 24], width]):
                out.append(Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGB"))
        return out

    def audio(self, sr: int):
        res = self.page.evaluate("(sr) => window.__audio(sr)", sr)
        if res.get("error"):
            return None
        return np.frombuffer(base64.b64decode(res["pcm"]), dtype=np.int16).astype(np.float32) / 32768.0

    def close(self):
        try:
            if self.page:
                self.page.close()
            self.browser.close()
        finally:
            self._pw.stop()


class FfmpegDecoder:
    """FFmpeg pipes. Written for the macOS render host; not exercised on the Windows dev host."""
    name = "ffmpeg"

    def __init__(self):
        self.bin = shutil.which("ffmpeg")
        if not self.bin:
            raise RuntimeError("ffmpeg not on PATH")
        self.version = subprocess.run([self.bin, "-version"], capture_output=True, text=True).stdout.split("\n")[0]
        self.path = None
        self.channel = None

    def open(self, path: Path) -> Dict[str, Any]:
        self.path = path
        return {}

    def _run(self, args: List[str]) -> bytes:
        r = subprocess.run([self.bin, "-v", "error", "-nostdin"] + args, capture_output=True)
        if r.returncode:
            raise RuntimeError(r.stderr.decode("utf-8", "replace")[-400:])
        return r.stdout

    def scan(self, times: List[float], w: int, h: int):
        out = []
        for t in times:
            raw = self._run(["-ss", f"{t:.4f}", "-i", str(self.path), "-frames:v", "1", "-vf", f"scale={w}:{h}",
                             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
            out.append(np.frombuffer(raw[:w * h * 3], dtype=np.uint8).reshape(h, w, 3))
        return np.stack(out) if out else np.zeros((0, h, w, 3), np.uint8)

    def frames(self, times: List[float], width: int) -> List["Image.Image"]:
        out = []
        for t in times:
            png = self._run(["-ss", f"{t:.4f}", "-i", str(self.path), "-frames:v", "1", "-vf", f"scale={width}:-2",
                             "-f", "image2pipe", "-vcodec", "png", "-"])
            out.append(Image.open(io.BytesIO(png)).convert("RGB"))
        return out

    def audio(self, sr: int):
        try:
            raw = self._run(["-i", str(self.path), "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"])
        except RuntimeError:
            return None
        return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0 if raw else None

    def close(self):
        pass


def make_decoder(kind: str = "auto", channel: Optional[str] = None):
    errors = []
    order = ["browser", "ffmpeg"] if kind == "auto" else [kind]
    for k in order:
        try:
            return BrowserDecoder(channel) if k == "browser" else FfmpegDecoder()
        except Exception as exc:
            errors.append(f"{k}: {exc}")
    raise SystemExit("No usable decoder.\n  " + "\n  ".join(errors) +
                     "\nInstall Microsoft Edge or Google Chrome (Playwright channel), or FFmpeg with H.264.")


# =============================================================================== signal analysis
SCAN_W, SCAN_H = 96, 54


def frame_signatures(frames) -> Tuple[Any, Any, Any]:
    """Per frame: 64-bin colour histogram (normalised), 16x9 grey layout, mean luma (0..1)."""
    q = (frames // 64).astype(np.int32)
    idx = q[..., 0] * 16 + q[..., 1] * 4 + q[..., 2]
    hist = np.stack([np.bincount(i.ravel(), minlength=64) for i in idx]).astype(np.float32)
    hist /= hist.sum(axis=1, keepdims=True)
    grey = frames.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    n, h, w = grey.shape
    layout = grey[:, : h - h % 9, : w - w % 16].reshape(n, 9, h // 9, 16, w // 16).mean(axis=(2, 4)) / 255.0
    return hist, layout, grey.mean(axis=(1, 2)) / 255.0


def pair_distance(hist, layout, a, b) -> float:
    return float(0.5 * (0.5 * np.abs(hist[a] - hist[b]).sum()) + 0.5 * np.abs(layout[a] - layout[b]).mean() * 2.0)


def step_series(frames, hist, layout) -> Dict[str, Any]:
    n = len(frames)
    grey = frames.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    dist = np.zeros(n, np.float32)
    changed = np.zeros(n, np.float32)
    for i in range(1, n):
        dist[i] = pair_distance(hist, layout, i - 1, i)
        changed[i] = float((np.abs(grey[i] - grey[i - 1]) > 12).mean())
    return {"dist": dist, "changed": changed}


def local_peaks(values, times, threshold: float, min_gap: float) -> List[int]:
    cand = [i for i in range(1, len(values) - 1) if values[i] >= threshold and values[i] >= values[i - 1] and values[i] >= values[i + 1]]
    cand.sort(key=lambda i: -values[i])
    picked: List[int] = []
    for i in cand:
        if all(abs(times[i] - times[j]) >= min_gap for j in picked):
            picked.append(i)
    return sorted(picked)


def detect_boundaries(times: List[float], hist, layout, steps: Dict[str, Any], scan_fps: float) -> List[Dict[str, Any]]:
    """Cut candidates (single-step spikes) and soft boundaries (novelty peaks over +-0.5 s)."""
    n = len(times)
    dist = steps["dist"]
    out: List[Dict[str, Any]] = []
    # Hard cuts: the step distance dwarfs its neighbourhood.
    for i in range(1, n):
        lo, hi = max(1, i - int(scan_fps)), min(n, i + int(scan_fps) + 1)
        neigh = np.concatenate([dist[lo:i], dist[i + 1:hi]])
        base = float(np.median(neigh)) if len(neigh) else 0.0
        if dist[i] > 0.16 and dist[i] > 3.0 * base + 0.04:
            out.append({"index": i, "kind": "cut", "score": round(float(dist[i]), 3)})
    # Soft boundaries: content before vs after differs over a half-second window.
    k = max(1, int(round(0.5 * scan_fps)))
    nov = np.zeros(n, np.float32)
    for i in range(k, n - k):
        nov[i] = pair_distance(hist, layout, i - k, i + k)
    thr = max(0.14, float(np.median(nov)) + 2.5 * float(np.median(np.abs(nov - np.median(nov)))) )
    for i in local_peaks(nov, times, thr, 0.9):
        if not any(abs(times[i] - times[c["index"]]) < 0.6 for c in out):
            out.append({"index": i, "kind": "soft", "score": round(float(nov[i]), 3)})
    out.sort(key=lambda c: c["index"])
    return out


def refine_cut(decoder, t_prev: float, t_cur: float, fps: float, pad: int = 3,
               t_max: Optional[float] = None) -> Tuple[float, float, float]:
    """Frame-accurate boundary inside (t_prev, t_cur]: scan every frame (plus `pad` frames either side)
    and return (time, biggest single-frame distance, isolation). Isolation compares that frame step
    with its neighbours (+-2 steps) in mean pixel change: about 1 for a cut, near 0 for a dissolve or
    fast move, which spread the change over consecutive frames. Pixel change is used because colour
    histograms of flat backgrounds jump between bins during a dissolve and look like cuts."""
    f0, f1 = int(math.floor(t_prev * fps)), int(math.ceil(t_cur * fps))
    lo = max(0, f0 - pad)
    ts = [(k + 0.5) / fps for k in range(lo, f1 + pad + 1)]
    if t_max is not None:
        ts = [min(t, t_max) for t in ts]
    fr = decoder.scan(ts, SCAN_W, SCAN_H)
    h, l, _ = frame_signatures(fr)
    px = np.abs(np.diff(fr.astype(np.float32), axis=0)).mean(axis=(1, 2, 3)) / 255.0
    best, bi = 0.0, None
    for i in range(max(1, f0 + 1 - lo), min(len(ts), f1 + 1 - lo)):
        d = pair_distance(h, l, i - 1, i)
        if d > best:
            best, bi = d, i
    if bi is None:
        return t_cur, 0.0, 0.0
    step = float(px[bi - 1])
    nb = [float(px[j]) for j in range(bi - 3, bi + 2) if 0 <= j < len(px) and j != bi - 1]
    isolation = max(0.0, (step - max(nb)) / step) if step > 1e-6 and nb else 0.0
    return (lo + bi) / fps, best, isolation


def holds_from(times: List[float], changed, min_len: float = 0.6, eps: float = 0.003) -> List[List[float]]:
    out, start = [], None
    for i in range(1, len(times)):
        still = changed[i] < eps
        if still and start is None:
            start = times[i - 1]
        if not still and start is not None:
            if times[i - 1] - start >= min_len:
                out.append([round(start, 2), round(times[i - 1], 2)])
            start = None
    if start is not None and times[-1] - start >= min_len:
        out.append([round(start, 2), round(times[-1], 2)])
    return out


# =============================================================================== palette
def palette(images: List["Image.Image"], k: int = 6) -> List[Dict[str, Any]]:
    counts: Dict[Tuple[int, int, int], int] = {}
    for im in images:
        small = im.copy()
        small.thumbnail((160, 160))
        q = small.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
        pal = q.getpalette()
        for cnt, idx in q.getcolors():
            r, g, b = pal[idx * 3: idx * 3 + 3]
            key = (r // 16 * 16 + 8, g // 16 * 16 + 8, b // 16 * 16 + 8)
            counts[key] = counts.get(key, 0) + cnt
    total = sum(counts.values()) or 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:10]
    return [{"hex": "#%02x%02x%02x" % c, "share": round(n / total, 3)} for c, n in top]


# =============================================================================== audio
def analyse_audio(x, sr: int, cut_times: List[float], fps: float) -> Dict[str, Any]:
    n_fft, hop = 1024, 256
    if x is None or len(x) < n_fft * 2:
        return {"present": False}
    peak = float(np.max(np.abs(x)))
    if peak < 1e-4:
        return {"present": True, "silent": True, "peak_dbfs": round(20 * math.log10(peak + 1e-9), 1),
                "method": "decoded track is digital silence"}
    frames = np.lib.stride_tricks.sliding_window_view(x, n_fft)[::hop]
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    t = (np.arange(len(rms)) * hop + n_fft / 2) / sr
    voiced = db > -50
    win = np.hanning(n_fft).astype(np.float32)
    spec = np.abs(np.fft.rfft(frames * win, axis=1))
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    logspec = np.log1p(spec * 10)
    flux = np.maximum(0, np.diff(logspec, axis=0)).sum(axis=1)
    flux = np.concatenate([[0], flux])
    flux_n = flux / (np.max(flux) + 1e-9)
    # Onsets: peaks above a moving median plus a margin, at least 80 ms apart.
    m = 7
    med = np.array([np.median(flux_n[max(0, i - m): i + m + 1]) for i in range(len(flux_n))])
    min_gap = int(0.08 * sr / hop)
    onsets, last = [], -min_gap
    for i in range(1, len(flux_n) - 1):
        if flux_n[i] > med[i] + 0.08 and flux_n[i] >= flux_n[i - 1] and flux_n[i] >= flux_n[i + 1] and voiced[i] and i - last >= min_gap:
            onsets.append(float(t[i]))
            last = i
    # Tempo: autocorrelation of the onset envelope between 60 and 180 BPM.
    env = flux_n - flux_n.mean()
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    lag_rate = sr / hop
    lo, hi = int(lag_rate * 60 / 180), int(lag_rate * 60 / 60)
    tempo = None
    if hi < len(ac) and ac[0] > 0:
        lag = lo + int(np.argmax(ac[lo:hi]))
        strength = float(ac[lag] / ac[0])
        tempo = {"bpm": round(60 * lag_rate / lag, 1), "autocorr": round(strength, 2),
                 "confidence": "medium" if strength > 0.35 else "low"}
    centroid = (spec * freqs).sum(axis=1) / (spec.sum(axis=1) + 1e-9)
    band = lambda a, b: float(spec[:, (freqs >= a) & (freqs < b)].sum())
    total = band(0, sr / 2) + 1e-9
    # Envelope modulation in the syllable range (3-8 Hz) relative to 0.5-20 Hz: high for speech.
    envr = rms[voiced] if voiced.sum() > 64 else rms
    mod = np.abs(np.fft.rfft(envr - envr.mean()))
    mf = np.fft.rfftfreq(len(envr), hop / sr)
    syl = float(mod[(mf >= 3) & (mf <= 8)].sum() / (mod[(mf >= 0.5) & (mf <= 20)].sum() + 1e-9))
    dur = len(x) / sr
    rate = len(onsets) / dur if dur else 0
    edges = np.geomspace(60, sr / 2, 65)
    bands = [(freqs >= edges[i]) & (freqs < edges[i + 1]) for i in range(64)]
    sg = np.stack([spec[:, m].mean(axis=1) if m.any() else np.zeros(len(spec)) for m in bands], axis=1)
    sg = 20 * np.log10(sg + 1e-6)
    lo_db, hi_db = np.percentile(sg, 5), np.percentile(sg, 99.5)
    sg = np.clip((sg - lo_db) / max(1e-6, hi_db - lo_db), 0, 1)[:: max(1, len(sg) // 1600)]
    sync = None
    if cut_times and onsets:
        tol = max(2.0 / fps, 0.05)
        offs = [min(abs(c - o) for o in onsets) for c in cut_times]
        hit = sum(1 for d in offs if d <= tol) / len(offs)
        chance = 1 - math.exp(-rate * 2 * tol)
        sync = {"boundaries": len(cut_times), "tolerance_ms": round(tol * 1000), "near_onset": round(hit, 2),
                "chance_level": round(chance, 2), "median_offset_ms": round(float(np.median(offs)) * 1000)}
        if tempo and tempo["confidence"] != "low":
            period = 60.0 / tempo["bpm"]
            ons = np.array(onsets)
            phases = np.linspace(0, period, 48, endpoint=False)
            fit = [np.sum(np.cos(2 * np.pi * (ons - ph) / period)) for ph in phases]
            phase = float(phases[int(np.argmax(fit))])
            beat_off = [abs(((c - phase + period / 2) % period) - period / 2) for c in cut_times]
            sync["near_beat"] = round(sum(1 for d in beat_off if d <= 0.06) / len(beat_off), 2)
            sync["beat_chance_level"] = round(min(1.0, 0.12 / period), 2)
            sync["beat_phase_sec"] = round(phase, 3)
    return {
        "present": True,
        "peak_dbfs": round(20 * math.log10(peak + 1e-9), 1),
        "mean_dbfs_voiced": round(float(db[voiced].mean()), 1) if voiced.any() else None,
        "silence_ratio": round(1 - float(voiced.mean()), 2),
        "onsets": len(onsets),
        "onset_rate_per_sec": round(rate, 2),
        "onset_times": [round(o, 2) for o in onsets[:400]],
        "tempo_estimate": tempo,
        "spectral_centroid_hz": round(float(np.median(centroid[voiced])) if voiced.any() else 0),
        "band_share": {"low_lt_250": round(band(0, 250) / total, 2), "mid_250_2k": round(band(250, 2000) / total, 2),
                       "high_gt_2k": round(band(2000, sr / 2) / total, 2)},
        "syllabic_modulation_share": round(syl, 2),
        "boundary_onset_alignment": sync,
        "_envelope": {"t": t[::4].round(3).tolist(), "db": db[::4].round(1).tolist()},
        "_spectrogram": sg,
        "method": "signal features only (envelope, spectral flux onsets, autocorrelation tempo); not listened to, no transcription",
    }


# =============================================================================== sheets
def _font():
    try:
        from PIL import ImageFont
        return ImageFont.load_default(size=14)
    except Exception:
        from PIL import ImageFont
        return ImageFont.load_default()


def grid_sheet(images: List["Image.Image"], labels: List[str], title: str, out: Path, cols: int, cell_w: int) -> None:
    if not images:
        return
    w0, h0 = images[0].size
    cell_h = int(cell_w * h0 / w0)
    rows = math.ceil(len(images) / cols)
    pad, lab = 8, 18
    sheet = Image.new("RGB", (cols * (cell_w + pad) + pad, 34 + rows * (cell_h + lab + pad) + pad), (236, 233, 226))
    d = ImageDraw.Draw(sheet)
    f = _font()
    d.text((pad, 9), title, fill=(25, 22, 18), font=f)
    for i, (im, lb) in enumerate(zip(images, labels)):
        r, c = divmod(i, cols)
        x, y = pad + c * (cell_w + pad), 34 + r * (cell_h + lab + pad)
        sheet.paste(im.resize((cell_w, cell_h)), (x, y))
        d.text((x, y + cell_h + 2), lb, fill=(55, 50, 44), font=f)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=88)


def rows_sheet(rows: List[Tuple[str, List["Image.Image"], List[str]]], title: str, out: Path, cell_w: int) -> None:
    rows = [r for r in rows if r[1]]
    if not rows:
        return
    cols = max(len(r[1]) for r in rows)
    w0, h0 = rows[0][1][0].size
    cell_h = int(cell_w * h0 / w0)
    pad, lab, head = 6, 16, 20
    sheet = Image.new("RGB", (cols * (cell_w + pad) + pad, 34 + len(rows) * (head + cell_h + lab + pad) + pad), (236, 233, 226))
    d = ImageDraw.Draw(sheet)
    f = _font()
    d.text((pad, 9), title, fill=(25, 22, 18), font=f)
    y = 34
    for name, ims, labels in rows:
        d.text((pad, y + 2), name, fill=(150, 50, 30), font=f)
        y += head
        for c, (im, lb) in enumerate(zip(ims, labels)):
            x = pad + c * (cell_w + pad)
            sheet.paste(im.resize((cell_w, cell_h)), (x, y))
            d.text((x, y + cell_h + 1), lb, fill=(55, 50, 44), font=f)
        y += cell_h + lab + pad
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=88)


def audio_sheet(audio: Dict[str, Any], duration: float, boundaries: List[float], out: Path) -> None:
    env = audio.get("_envelope")
    if not env:
        return
    W, H, pad, SH = 1600, 260, 40, 200
    im = Image.new("RGB", (W, H + SH + 30), (248, 246, 240))
    d = ImageDraw.Draw(im)
    f = _font()
    x = lambda tt: pad + (W - 2 * pad) * tt / max(duration, 1e-6)
    y = lambda db: H - pad - (H - 2 * pad) * (max(-60.0, min(0.0, db)) + 60) / 60
    for s in range(0, int(duration) + 1):
        d.line([(x(s), pad), (x(s), H - pad)], fill=(225, 220, 210))
        if s % 5 == 0:
            d.text((x(s) - 6, H - pad + 6), f"{s}s", fill=(90, 85, 75), font=f)
    pts = [(x(tt), y(db)) for tt, db in zip(env["t"], env["db"])]
    if len(pts) > 1:
        d.line(pts, fill=(40, 70, 120), width=1)
    for o in audio.get("onset_times", []):
        d.line([(x(o), H - pad), (x(o), H - pad - 12)], fill=(60, 140, 80), width=1)
    for b in boundaries:
        d.line([(x(b), pad), (x(b), H - pad)], fill=(200, 60, 40), width=2)
    d.text((pad, 10), "audio envelope (dBFS, -60..0) | green ticks = onsets | red = visual boundaries", fill=(25, 22, 18), font=f)
    sg = audio.get("_spectrogram")
    if sg is not None and len(sg):
        top = H + 20
        vals = (255 - (np.asarray(sg).T[::-1] * 235)).astype(np.uint8)
        spec_im = Image.fromarray(vals, mode="L").resize((W - 2 * pad, SH)).convert("RGB")
        im.paste(spec_im, (pad, top))
        for b in boundaries:
            d.line([(x(b), top), (x(b), top + 8)], fill=(200, 60, 40), width=2)
        d.text((pad, top - 16), "spectrogram, log frequency 60 Hz (bottom) to 5.5 kHz (top); dark = energy", fill=(25, 22, 18), font=f)
    im.save(out)


# =============================================================================== analyse
def scan_rate(duration: float) -> float:
    """Coarse scan density: dense for short pieces, lighter for long ones (cuts are refined per frame)."""
    if duration <= 30:
        return 8.0
    if duration <= 90:
        return 6.0
    return 4.0


def analyse(record: Dict[str, Any], path: Path, decoder, cache_dir: Path = CACHE_DIR, log=print) -> Dict[str, Any]:
    media = record["media"]
    dur, fps = float(media["duration_sec"]), float(media.get("fps") or 30)
    last_frame_t = (int(math.floor(dur * fps)) - 0.5) / fps
    out_dir = cache_dir / record["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = decoder.open(path)
    rate = scan_rate(dur)
    times = [round(min(last_frame_t, (i + 0.5) / rate), 4) for i in range(int(dur * rate))]
    log(f"  scan {len(times)} frames at {rate:g} fps ({decoder.name})")
    fr = decoder.scan(times, SCAN_W, SCAN_H)
    hist, layout, luma = frame_signatures(fr)
    steps = step_series(fr, hist, layout)
    cands = detect_boundaries(times, hist, layout, steps, rate)
    boundaries: List[Dict[str, Any]] = []
    for c in cands:
        i = c["index"]
        if c["kind"] == "cut":
            t, score, isolation = refine_cut(decoder, times[i - 1], times[i], fps, t_max=last_frame_t)
            # A cut changes the picture in one isolated frame step. A small biggest step, or one with
            # equally large neighbours, was a dissolve, wipe or fast move.
            kind = "cut" if score >= 0.1 and isolation >= 0.5 else "soft"
            b = {"t": round(t, 3), "kind": kind, "score": round(score, 3), "isolation": round(isolation, 2)}
            if kind == "cut":
                b["frame"] = int(round(t * fps))
        else:
            b = {"t": round(times[i], 3), "kind": "soft", "score": c["score"]}
        # Cuts closer than 0.2 s are one cut; candidates inside one dissolve (up to 0.6 s) are one transition.
        near = [x for x in boundaries if abs(x["t"] - b["t"]) < (0.2 if x["kind"] == b["kind"] == "cut" else 0.6)]
        if near:
            keep = max(near + [b], key=lambda x: (x["kind"] == "cut", x["score"]))
            boundaries = [x for x in boundaries if x not in near] + [keep]
        else:
            boundaries.append(b)
    boundaries.sort(key=lambda x: x["t"])
    log(f"  boundaries: {sum(b['kind'] == 'cut' for b in boundaries)} cuts, {sum(b['kind'] == 'soft' for b in boundaries)} soft")
    edges = [0.0] + [b["t"] for b in boundaries] + [dur]
    scenes = []
    for k in range(len(edges) - 1):
        a, b = edges[k], edges[k + 1]
        if b - a < 0.25:
            continue
        idx = [i for i, t in enumerate(times) if a <= t < b]
        act = float(np.mean(steps["changed"][idx])) if idx else 0.0
        scenes.append({"index": len(scenes) + 1, "start": round(a, 2), "end": round(b, 2),
                       "duration": round(b - a, 2), "activity": round(act, 3),
                       "luma": round(float(np.mean(luma[idx])), 2) if idx else None})
    holds = holds_from(times, steps["changed"])
    # Representative times: scene middles (quartiles too for long scenes).
    reps = []
    for s in scenes:
        span = s["end"] - s["start"]
        picks = [0.5] if span < 4 else [0.25, 0.5, 0.75]
        reps += [round(s["start"] + span * p, 2) for p in picks]
    # Evidence images.
    n_over = int(min(64, max(16, round(dur / 0.75))))
    over_t = [round(min(last_frame_t, (i + 0.5) * dur / n_over), 3) for i in range(n_over)]
    log(f"  overview sheet: {n_over} frames")
    over = decoder.frames(over_t, 320)
    grid_sheet(over, [f"{t:.2f}s" for t in over_t], f"{record['id']}  {path.name}  {dur:.2f}s  overview ({n_over} evenly spaced frames)",
               out_dir / "overview.jpg", cols=8 if n_over > 40 else 6, cell_w=200 if n_over > 40 else 240)
    scene_rows = []
    for s in scenes[:40]:
        span = s["end"] - s["start"]
        ts = [round(min(last_frame_t, s["start"] + min(0.08, span / 4)), 3), round(s["start"] + span / 2, 3),
              round(min(last_frame_t, max(s["start"], s["end"] - min(0.08, span / 4))), 3)]
        scene_rows.append((f"scene {s['index']}  {s['start']:.2f}-{s['end']:.2f}s  activity {s['activity']:.3f}", decoder.frames(ts, 240), [f"{t:.2f}s" for t in ts]))
    rows_sheet(scene_rows, f"{record['id']} scenes (start / middle / end)", out_dir / "scenes.jpg", 240)
    trans_rows = []
    for b in boundaries[:16]:
        ts = [round(min(last_frame_t, max(0.0, b["t"] + (k - 5) * 2 / fps + 0.5 / fps)), 3) for k in range(11)]
        trans_rows.append((f"{b['kind']} @ {b['t']:.2f}s (score {b['score']})", decoder.frames(ts, 200), [f"{t:.2f}" for t in ts]))
    rows_sheet(trans_rows, f"{record['id']} transitions (every 2nd frame, -10..+10 frames)", out_dir / "transitions.jpg", 150)
    # Motion strips: the most active one-second windows that are not transitions.
    act = steps["changed"]
    win = int(rate)
    scores = [(float(np.mean(act[i:i + win])), times[i]) for i in range(0, max(1, len(times) - win))]
    picked: List[float] = []
    for sc, t0 in sorted(scores, reverse=True):
        if len(picked) >= 4 or sc < 0.01:
            break
        if all(abs(t0 - p) > 1.5 for p in picked) and all(abs(t0 + 0.5 - b["t"]) > 0.7 for b in boundaries):
            picked.append(t0)
    motion_rows = []
    for t0 in sorted(picked):
        ts = [round(min(last_frame_t, t0 + k / 10), 3) for k in range(12)]
        motion_rows.append((f"motion window {t0:.2f}-{t0 + 1.1:.2f}s (10 fps)", decoder.frames(ts, 200), [f"{t:.2f}" for t in ts]))
    rows_sheet(motion_rows, f"{record['id']} highest-activity windows", out_dir / "motion.jpg", 150)
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(exist_ok=True)
    for t, im in zip(reps[:60], decoder.frames(reps[:60], 640)):
        im.save(frames_dir / f"t{t:07.2f}.jpg", quality=90)
    pal = palette(over)
    audio = {"present": False}
    if media.get("audio"):
        log("  audio")
        x = decoder.audio(11025)
        audio = analyse_audio(x, 11025, [b["t"] for b in boundaries], fps) if x is not None else {"present": False, "note": "audio track could not be decoded"}
        if audio.get("present"):
            audio_sheet(audio, dur, [b["t"] for b in boundaries], out_dir / "audio.png")
    env = audio.pop("_envelope", None)
    audio.pop("_spectrogram", None)
    automated = {
        "analyzer": {"version": ANALYZER_VERSION, "decoder": decoder.name, "browser_channel": getattr(decoder, "channel", None),
                     "decoder_version": getattr(decoder, "version", None), "run_on": today()},
        "sampling": {"scan_fps": rate, "scan_frames": len(times), "scan_size": f"{SCAN_W}x{SCAN_H}",
                     "overview_frames": n_over, "cut_refinement": "every frame inside the coarse step",
                     "transition_strips": len(trans_rows), "motion_strips": len(motion_rows)},
        "boundaries": boundaries,
        "scenes": scenes,
        "static_holds": holds,
        "mean_activity": round(float(np.mean(act)), 3),
        "luma": {"mean": round(float(np.mean(luma)), 2), "dark_share": round(float(np.mean(luma < 0.25)), 2),
                 "light_share": round(float(np.mean(luma > 0.7)), 2)},
        "palette": pal,
        "representative_times": reps,
        "audio": audio,
        "artifacts": {"cache_dir": rel(out_dir), "overview": rel(out_dir / "overview.jpg"), "scenes": rel(out_dir / "scenes.jpg"),
                      "transitions": rel(out_dir / "transitions.jpg") if trans_rows else None,
                      "motion": rel(out_dir / "motion.jpg") if motion_rows else None,
                      "audio": rel(out_dir / "audio.png") if audio.get("present") else None,
                      "frames": rel(frames_dir), "tracked": False},
    }
    signal = {"times": times, "dist": steps["dist"].round(4).tolist(), "changed": steps["changed"].round(4).tolist(),
              "luma": luma.round(3).tolist(), "audio_envelope": env}
    save_json(out_dir / "signal.json", signal)
    save_json(out_dir / "analysis.json", {"id": record["id"], "sha256": record["source"]["sha256"], "file": path.name,
                                          "decoded": meta, "automated": automated})
    return automated


def strip(record: Dict[str, Any], path: Path, decoder, t0: float, t1: float, fps: float, width: int, cache_dir: Path = CACHE_DIR) -> Path:
    media = record["media"]
    vfps = float(media.get("fps") or 30)
    last = (int(math.floor(float(media["duration_sec"]) * vfps)) - 0.5) / vfps
    decoder.open(path)
    n = max(2, int(round((t1 - t0) * fps)) + 1)
    ts = [round(min(last, t0 + k / fps), 3) for k in range(n)]
    ims = decoder.frames(ts, width)
    out = cache_dir / record["id"] / "strips" / f"strip-{t0:06.2f}-{t1:06.2f}-{fps:g}fps.jpg"
    grid_sheet(ims, [f"{t:.2f}s" for t in ts], f"{record['id']} {t0:.2f}-{t1:.2f}s at {fps:g} fps", out, cols=min(8, n), cell_w=width)
    return out


# =============================================================================== duplicates check
STOP = set("a an and the of to in on for with by from into as at is are be or its it that this then than".split())


def tokens(*texts: str) -> set:
    words = set()
    for t in texts:
        for w in re.findall(r"[a-z0-9]+", (t or "").lower()):
            if w not in STOP and len(w) > 2:
                words.add(w[:-1] if w.endswith("s") and len(w) > 4 else w)
    return words


def similar_techniques(name: str, tags: List[str], text: str, techniques: Dict[str, Dict[str, Any]], effects: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    cand = tokens(name, text, " ".join(tags))
    out = []
    pools = [("technique", techniques), ("effect", effects)]
    for kind, pool in pools:
        for rid, r in pool.items():
            other = tokens(rid.replace("-", " "), r.get("name", ""), r.get("technique", ""), r.get("purpose", ""),
                           r.get("visual_intent", ""), " ".join(r.get("tags", [])))
            if not other or not cand:
                continue
            j = len(cand & other) / len(cand | other)
            cover = len(cand & other) / len(cand)
            score = round(0.5 * j + 0.5 * cover, 3)
            if score >= 0.2:
                out.append({"kind": kind, "id": rid, "score": score, "shared": sorted(cand & other)[:12]})
    return sorted(out, key=lambda r: -r["score"])[:10]


# =============================================================================== CLI
def cmd_doctor(args) -> int:
    print(f"python {sys.version.split()[0]}  numpy {'yes' if np is not None else 'NO'}  Pillow {'yes' if Image else 'NO'}")
    try:
        import jsonschema  # noqa: F401
        print("jsonschema yes")
    except ImportError:
        print("jsonschema NO (records are not schema-checked on write)")
    ok = False
    for ch in ("msedge", "chrome"):
        try:
            d = BrowserDecoder(ch)
            pg = d.browser.new_page()
            pg.set_content(PAGE_HTML)
            h264 = pg.evaluate("window.__h264()")
            print(f"browser channel {ch}: {d.version}  H.264={h264 or 'no'}")
            ok = ok or bool(h264)
            d.close()
        except Exception as exc:
            print(f"browser channel {ch}: unavailable ({str(exc).splitlines()[0][:90]})")
    ff = shutil.which("ffmpeg")
    if ff:
        dec = subprocess.run([ff, "-hide_banner", "-decoders"], capture_output=True, text=True).stdout
        has = " h264 " in dec
        print(f"ffmpeg {ff}: H.264 decoder={'yes' if has else 'no'}")
        ok = ok or has
    else:
        print("ffmpeg: not on PATH")
    if args.file:
        dec = make_decoder(args.backend, args.channel)
        meta = dec.open(Path(args.file))
        im = dec.frames([0.5], 160)[0]
        print(f"decode test {args.file}: {meta} frame {im.size} mean={sum(im.convert('L').getdata()) / (im.size[0] * im.size[1]):.1f}")
        dec.close()
    print("decoder available" if ok else "NO decoder with H.264 available")
    return 0 if ok else 1


def cmd_ingest(args) -> int:
    files = iter_videos(args.paths)
    if not files:
        print("No video files found.")
        return 1
    results = ingest(files, dry_run=args.dry_run)
    for r in results:
        print(f"{r.get('id', '-'):15} {r['action']:44} {Path(r['file']).name}  {r.get('size', '')} {r.get('duration_sec', '')}s {r.get('reason', '')}")
    bad = [r for r in results if r["action"] in ("rejected", "invalid")]
    print(f"\n{len(results) - len(bad)} accepted, {len(bad)} rejected{' (dry run: nothing written)' if args.dry_run else ''}.")
    if not args.dry_run and any(r["action"] == "created" for r in results):
        print("Next: python scripts/reference-corpus.py analyze --pending --root <folder>")
    return 1 if bad else 0


def _select(args, sources) -> List[Dict[str, Any]]:
    if getattr(args, "all", False):
        return list(sources.values())
    if getattr(args, "pending", False):
        out = []
        for r in sources.values():
            cached = CACHE_DIR / r["id"] / "analysis.json"
            fresh = cached.exists() and load_json(cached).get("sha256") == r["source"]["sha256"] and \
                load_json(cached).get("automated", {}).get("analyzer", {}).get("version") == ANALYZER_VERSION
            if not r.get("automated") or not fresh:
                out.append(r)
        return out
    missing = [i for i in args.ids if i not in sources]
    if missing:
        raise SystemExit(f"Unknown reference id(s): {', '.join(missing)}")
    return [sources[i] for i in args.ids]


def cmd_analyze(args) -> int:
    sources = load_sources()
    todo = _select(args, sources)
    if not todo:
        print("Nothing to analyse (all records have current automated analysis; use --force or ids).")
        return 0
    roots = reference_roots(args.root)
    dec = make_decoder(args.backend, args.channel)
    failed = 0
    try:
        for rec in todo:
            cached = CACHE_DIR / rec["id"] / "analysis.json"
            if not args.force and cached.exists() and rec.get("automated"):
                c = load_json(cached)
                if c.get("sha256") == rec["source"]["sha256"] and c.get("automated", {}).get("analyzer", {}).get("version") == ANALYZER_VERSION:
                    print(f"{rec['id']}: cached analysis is current (use --force to redo)")
                    continue
            path = locate(rec, roots)
            if not path:
                print(f"{rec['id']}: file '{rec['source']['filename']}' not found in roots {[str(r) for r in roots]}")
                failed += 1
                continue
            print(f"{rec['id']}: {path.name} {rec['media']['duration_sec']}s")
            started = _dt.datetime.now()
            auto = analyse(rec, path, dec)
            auto["analyzer"]["elapsed_sec"] = round((_dt.datetime.now() - started).total_seconds(), 1)
            print(f"  analysed in {auto['analyzer']['elapsed_sec']}s")
            rec["automated"] = auto
            if rec.get("analysis", {}).get("state") in (None, "pending"):
                rec["analysis"] = {"state": "automated"}
            rec["metadata"]["updated_at"] = today()
            errs = validate_source(rec)
            if errs:
                print(f"  [FAIL] record invalid after analysis: {errs[:3]}")
                failed += 1
                continue
            save_json(SOURCES_DIR / f"{rec['id']}.json", rec)
            print(f"  -> {auto['artifacts']['overview']} (+ scenes, transitions, motion, audio)")
    finally:
        dec.close()
    return 1 if failed else 0


def cmd_strip(args) -> int:
    sources = load_sources()
    if args.id not in sources:
        raise SystemExit(f"Unknown reference id {args.id}")
    rec = sources[args.id]
    path = locate(rec, reference_roots(args.root))
    if not path:
        raise SystemExit("file not found in roots")
    dec = make_decoder(args.backend, args.channel)
    try:
        out = strip(rec, path, dec, args.t0, args.t1, args.fps, args.width)
    finally:
        dec.close()
    print(rel(out))
    return 0


def cmd_status(args) -> int:
    sources = load_sources()
    techs = load_techniques()
    print(f"{'id':15} {'status':12} {'analysis':10} {'dur':>7} {'size':11} {'scenes':>6} {'tech':>4}  name")
    for r in sources.values():
        m = r["media"]
        sc = len(r.get("automated", {}).get("scenes", [])) if r.get("automated") else "-"
        print(f"{r['id']:15} {r['status']:12} {r.get('analysis', {}).get('state', '?'):10} {m['duration_sec']:7.2f} "
              f"{str(m['width']) + 'x' + str(m['height']):11} {sc:>6} {len(r.get('techniques', [])):>4}  {r['name'][:60]}")
    linked = {t["id"] for r in sources.values() for t in r.get("techniques", [])}
    print(f"\n{len(sources)} references, {len(techs)} technique records ({len(linked)} linked from references).")
    return 0


def cmd_locate(args) -> int:
    sources = load_sources()
    if args.id not in sources:
        raise SystemExit(f"Unknown reference id {args.id}")
    p = locate(sources[args.id], reference_roots(args.root))
    print(p if p else "not found (pass --root or set MOTION_REFERENCE_ROOTS)")
    return 0 if p else 1


def cmd_check(args) -> int:
    techniques = load_techniques()
    effects = {}
    eff_dir = DATA_DIR / "effects"
    for p in sorted(eff_dir.glob("*.json")):
        d = load_json(p)
        effects[d["id"]] = d
    tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
    hits = similar_techniques(args.name, tags, args.text or "", techniques, effects)
    if not hits:
        print("No similar technique or effect: likely a new pattern (still check by eye).")
        return 0
    print(f"{'score':>5}  {'kind':9} id  (shared terms)")
    for h in hits:
        flag = "  <- likely duplicate: extend this record instead" if h["score"] >= 0.5 else ""
        print(f"{h['score']:5.2f}  {h['kind']:9} {h['id']}  ({', '.join(h['shared'])}){flag}")
    return 0


SUPPORT_ORDER = ["native", "approximation", "additional-dependencies", "resource-constrained", "research-required"]


def cmd_report(args) -> int:
    sources = load_sources()
    techs = load_techniques()
    freq: Dict[str, int] = {}
    for r in sources.values():
        for t in r.get("techniques", []):
            freq[t["id"]] = freq.get(t["id"], 0) + 1
    rows = []
    for tid, t in techs.items():
        cap = t.get("capability", {})
        rows.append({"id": tid, "refs": freq.get(tid, 0), "state": t.get("implementation_state"),
                     "support": cap.get("support", "-"), "value": cap.get("priority", {}).get("creative_value"),
                     "cost": cap.get("priority", {}).get("cost"), "status": t.get("status")})
    if args.backlog:
        rows = [r for r in rows if r["state"] in ("observed", "documented") or r["support"] in SUPPORT_ORDER[2:]]
        rows.sort(key=lambda r: (-(r["value"] or 0) * max(1, r["refs"]) / max(1, r["cost"] or 3), r["id"]))
    else:
        rows.sort(key=lambda r: (-r["refs"], r["id"]))
    print(f"{'technique':34} {'refs':>4} {'state':12} {'support':24} {'value':>5} {'cost':>4} status")
    for r in rows:
        print(f"{r['id'][:34]:34} {r['refs']:>4} {str(r['state']):12} {r['support']:24} {str(r['value'] or '-'):>5} {str(r['cost'] or '-'):>4} {r['status']}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Reference corpus ingestion and evidence tool", formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("Usage:")[1] if "Usage:" in __doc__ else None)
    sub = ap.add_subparsers(dest="cmd")

    def common(p, decoder=True):
        p.add_argument("--root", action="append", help=f"folder holding reference files (repeatable; also ${ROOTS_ENV})")
        if decoder:
            p.add_argument("--backend", choices=["auto", "browser", "ffmpeg"], default="auto")
            p.add_argument("--channel", help="Playwright browser channel (msedge, chrome)")

    p = sub.add_parser("doctor", help="check decoders and dependencies")
    p.add_argument("--file")
    common(p)
    p = sub.add_parser("ingest", help="register reference files (metadata + hash, no analysis)")
    p.add_argument("paths", nargs="+")
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("analyze", help="automated evidence: scenes, sheets, strips, palette, audio")
    p.add_argument("ids", nargs="*")
    p.add_argument("--all", action="store_true")
    p.add_argument("--pending", action="store_true", help="only records without current automated analysis")
    p.add_argument("--force", action="store_true")
    common(p)
    p = sub.add_parser("strip", help="fine temporal strip of one interval")
    p.add_argument("id")
    p.add_argument("--from", dest="t0", type=float, required=True)
    p.add_argument("--to", dest="t1", type=float, required=True)
    p.add_argument("--fps", type=float, default=12)
    p.add_argument("--width", type=int, default=200)
    common(p)
    sub.add_parser("status", help="corpus table")
    p = sub.add_parser("locate", help="resolve a record to its file")
    p.add_argument("id")
    common(p, decoder=False)
    p = sub.add_parser("check", help="compare a candidate technique with existing technique and effect records")
    p.add_argument("--name", required=True)
    p.add_argument("--tags")
    p.add_argument("--text")
    p = sub.add_parser("report", help="technique frequency across the corpus; --backlog for unsupported work")
    p.add_argument("--backlog", action="store_true")
    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 0
    if args.cmd in ("analyze", "strip") and (np is None or Image is None):
        print("Error: analysis needs numpy and Pillow.")
        return 2
    if args.cmd == "analyze" and not (args.ids or args.all or args.pending):
        print("Give reference ids, --pending or --all.")
        return 2
    return {"doctor": cmd_doctor, "ingest": cmd_ingest, "analyze": cmd_analyze, "strip": cmd_strip, "status": cmd_status,
            "locate": cmd_locate, "check": cmd_check, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
