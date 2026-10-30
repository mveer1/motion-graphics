#!/usr/bin/env python3
"""
tests/test-reference-corpus.py
Tests for the reference corpus (scripts/reference-corpus.py) and the technique knowledge base
(catalogue/data/references + reference-sources, rules in scripts/motion-catalogue.py).

1. Pure-Python MP4 probe on synthetic files (ISO and QuickTime 'meta'; non-MP4 data rejected).
2. Content-hash IDs; a renamed copy becomes an alias, not a duplicate; ingest writes only source
   records; locate() finds a renamed file by size and hash.
3. Measurement helpers on synthetic signals: hard cut vs soft transition, static holds, tempo and
   cut-to-onset alignment of a click track.
4. Knowledge-base honesty rules (evidence, approval, provenance, links, timestamps, hashes, rights).
5. Retrieval: word-prefix matching, support/category filters, recommend for a brief.
6. The committed corpus records match their schema.
Decoding real video needs a browser with H.264 or FFmpeg and is exercised by `doctor`/`analyze`.
"""

import copy
import importlib
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
corpus = importlib.import_module("reference-corpus")
catalogue = importlib.import_module("motion-catalogue")

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None
try:
    import jsonschema  # noqa: F401
    HAS_JSONSCHEMA = True
except ImportError:  # pragma: no cover
    HAS_JSONSCHEMA = False


# ------------------------------------------------------------------ synthetic MP4
def box(typ: str, payload: bytes) -> bytes:
    return struct.pack(">I4s", 8 + len(payload), typ.encode("latin-1")) + payload


def full_box(typ: str, payload: bytes, version: int = 0) -> bytes:
    return box(typ, struct.pack(">I", version << 24) + payload)


def media_header(timescale: int, duration: int) -> bytes:
    return struct.pack(">IIII", 0, 0, timescale, duration) + b"\0" * 80


def track(handler: str, timescale: int, duration: int, entry: bytes, count: int, delta: int, size: int, keyframes: int = 0) -> bytes:
    stbl = full_box("stsd", struct.pack(">I", 1) + entry)
    stbl += full_box("stts", struct.pack(">III", 1, count, delta))
    stbl += full_box("stsz", struct.pack(">II", size, count))
    if keyframes:
        stbl += full_box("stss", struct.pack(">I", keyframes) + b"".join(struct.pack(">I", 1 + 30 * i) for i in range(keyframes)))
    hdlr = full_box("hdlr", b"\0\0\0\0" + handler.encode("latin-1") + b"\0" * 12 + b"t\0")
    mdia = box("mdia", full_box("mdhd", struct.pack(">IIII", 0, 0, timescale, duration) + b"\0\0\0\0") + hdlr + box("minf", box("stbl", stbl)))
    return box("trak", mdia)


def avc1_entry(width: int, height: int) -> bytes:
    body = b"\0" * 6 + struct.pack(">H", 1) + b"\0" * 16 + struct.pack(">HH", width, height)
    body += struct.pack(">II", 0x00480000, 0x00480000) + b"\0" * 4 + struct.pack(">H", 1) + b"\0" * 32 + struct.pack(">Hh", 24, -1)
    assert len(body) == 78
    return box("avc1", body + box("avcC", bytes([1, 0x64, 0x00, 0x1F]) + b"\xff\xe1"))


def mp4a_entry(channels: int, rate: int) -> bytes:
    body = b"\0" * 6 + struct.pack(">H", 1) + b"\0" * 8 + struct.pack(">HHHHI", channels, 16, 0, 0, rate << 16)
    return box("mp4a", body)


def synthetic_mp4(encoder: str = "Lavf-test", quicktime_meta: bool = False, faststart: bool = True) -> bytes:
    """2 s, 320x180 H.264 at 30 fps (15360/512) plus 48 kHz stereo AAC; payload sizes are fixed."""
    video = track("vide", 15360, 30720, avc1_entry(320, 180), 60, 512, 1000, keyframes=2)
    audio = track("soun", 48000, 96000, mp4a_entry(2, 48000), 94, 1024, 300)
    data = box("data", struct.pack(">II", 1, 0) + encoder.encode("utf-8"))
    ilst = box("ilst", box("\xa9too", data))
    hdlr = full_box("hdlr", b"\0\0\0\0mdirappl" + b"\0" * 9)
    meta = box("meta", hdlr + ilst) if quicktime_meta else full_box("meta", hdlr + ilst)
    moov = box("moov", full_box("mvhd", media_header(1000, 2000)) + video + audio + box("udta", meta))
    ftyp = box("ftyp", b"isom" + struct.pack(">I", 512) + b"isomiso2avc1mp41")
    mdat = box("mdat", b"\0" * 64)
    return ftyp + (moov + mdat if faststart else mdat + moov)


class SyntheticDecoder:
    """Decoder stand-in: flat frames whose colour is colour_at(frame centre time); refuses seeks past the end."""
    name = "synthetic"

    def __init__(self, fps, colour_at, duration):
        self.fps, self.colour_at, self.duration = fps, colour_at, duration

    def open(self, path):
        return {}

    def frame(self, t, w, h):
        if t > self.duration:
            raise AssertionError(f"seek past the end: {t}")
        a = np.zeros((h, w, 3), np.float32)
        a[:] = self.colour_at((int(t * self.fps) + 0.5) / self.fps)
        return a.round().astype(np.uint8)

    def scan(self, times, w, h):
        return np.stack([self.frame(t, w, h) for t in times])

    def frames(self, times, width):
        from PIL import Image
        return [Image.fromarray(self.frame(t, width, int(width * 9 / 16))) for t in times]

    def audio(self, sr):
        return None

    def close(self):
        pass


class TestMp4Probe(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="refcorpus-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name: str, data: bytes) -> Path:
        p = self.tmp / name
        p.write_bytes(data)
        return p

    def test_probe_reads_tracks_timing_and_encoder(self):
        m = corpus.probe_mp4(self.write("clip.mp4", synthetic_mp4()))
        self.assertEqual((m["width"], m["height"]), (320, 180))
        self.assertEqual(m["duration_sec"], 2.0)
        self.assertEqual(m["fps"], 30)
        self.assertEqual(m["fps_exact"], "15360/512")
        self.assertEqual(m["frame_count"], 60)
        self.assertFalse(m["variable_frame_rate"])
        self.assertEqual(m["video_codec"], "avc1.64001f")
        self.assertEqual(m["video_kbps"], 240)
        self.assertEqual(m["keyframes"], 2)
        self.assertEqual(m["brand"], "isom")
        self.assertIn("avc1", m["compatible_brands"])
        self.assertTrue(m["faststart"])
        self.assertEqual(m["encoder"], "Lavf-test")
        self.assertEqual(m["audio"]["sample_rate"], 48000)
        self.assertEqual(m["audio"]["channels"], 2)
        self.assertEqual(m["audio"]["duration_sec"], 2.0)

    def test_probe_handles_quicktime_meta_and_moov_at_end(self):
        m = corpus.probe_mp4(self.write("qt.mov", synthetic_mp4(encoder="QT enc", quicktime_meta=True, faststart=False)))
        self.assertEqual(m["encoder"], "QT enc")
        self.assertFalse(m["faststart"])
        self.assertEqual(m["fps"], 30)

    def test_probe_rejects_non_mp4(self):
        with self.assertRaises(corpus.Mp4Error):
            corpus.probe_mp4(self.write("fake.mp4", b"\0\0\0\x10junkjunkjunkjunk" * 4))


class TestIngest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="refcorpus-"))
        self.videos = self.tmp / "videos"
        self.videos.mkdir()
        self.sources = self.tmp / "sources"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_content_id_alias_and_no_duplicates(self):
        a = self.videos / "first name.mp4"
        a.write_bytes(synthetic_mp4())
        digest = corpus.sha256_file(a)
        first = corpus.ingest([a], sources_dir=self.sources)
        self.assertEqual(first[0]["action"], "created", first)
        rid = first[0]["id"]
        self.assertEqual(rid, "ref-" + digest[:10])
        b = self.videos / "renamed copy.mp4"
        shutil.copyfile(a, b)
        second = corpus.ingest([b], sources_dir=self.sources)
        self.assertEqual(second[0]["id"], rid)
        self.assertTrue(second[0]["action"].startswith("updated"), second)
        third = corpus.ingest([a], sources_dir=self.sources)
        self.assertTrue(third[0]["action"].startswith("unchanged"), third)
        files = sorted(p.name for p in self.sources.iterdir())
        self.assertEqual(files, [f"{rid}.json"], "one record per content hash, nothing else written")
        rec = json.loads((self.sources / f"{rid}.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["source"]["filename"], "first name.mp4")
        self.assertEqual(rec["source"]["aliases"], ["renamed copy.mp4"])
        self.assertEqual(rec["analysis"]["state"], "pending")
        self.assertEqual(rec["rights"]["usage"], "inspiration-only")
        self.assertNotIn(str(self.tmp), json.dumps(rec), "records must not store absolute paths")
        if HAS_JSONSCHEMA:
            self.assertEqual(corpus.validate_source(rec), [])

    def test_ingest_rejects_unreadable_and_dry_run_writes_nothing(self):
        bad = self.videos / "broken.mp4"
        bad.write_bytes(b"not a video at all" * 10)
        good = self.videos / "ok.mp4"
        good.write_bytes(synthetic_mp4())
        res = corpus.ingest([bad, good], sources_dir=self.sources, dry_run=True)
        self.assertEqual(res[0]["action"], "rejected")
        self.assertEqual(res[1]["action"], "created")
        self.assertFalse(self.sources.exists() and any(self.sources.iterdir()), "dry run must not write records")

    def test_locate_finds_renamed_file_by_hash(self):
        a = self.videos / "orig.mp4"
        a.write_bytes(synthetic_mp4())
        rec = corpus.new_source_record(corpus.sha256_file(a), a, corpus.probe_mp4(a))
        self.assertEqual(corpus.locate(rec, [self.videos]), a)
        moved = self.videos / "somebody renamed it.mp4"
        a.rename(moved)
        self.assertEqual(corpus.locate(rec, [self.videos]), moved)
        moved.write_bytes(synthetic_mp4(encoder="different"))
        self.assertIsNone(corpus.locate(rec, [self.videos]), "a file with other content must not match")


@unittest.skipUnless(np is not None, "numpy is not installed")
class TestMeasurements(unittest.TestCase):

    @staticmethod
    def frames(n_a: int, n_blend: int, n_b: int):
        h, w = corpus.SCAN_H, corpus.SCAN_W
        a = np.zeros((h, w, 3), np.float32)
        a[:, w // 2:] = 255
        b = 255 - a
        seq = [a] * n_a + [a + (b - a) * (k / n_blend) for k in range(1, n_blend)] + [b] * n_b
        return np.stack(seq).round().astype(np.uint8)

    def boundaries(self, frames, fps=8.0):
        times = [i / fps for i in range(len(frames))]
        hist, layout, _ = corpus.frame_signatures(frames)
        steps = corpus.step_series(frames, hist, layout)
        return corpus.detect_boundaries(times, hist, layout, steps, fps), steps, times

    def test_hard_cut_is_a_cut(self):
        found, _, _ = self.boundaries(self.frames(40, 1, 40))
        self.assertEqual([(b["kind"], b["index"]) for b in found], [("cut", 40)])

    def run_pipeline(self, colour_at, duration=6.0, fps=30):
        tmp = Path(tempfile.mkdtemp(prefix="refcorpus-"))
        try:
            rec = {"id": "ref-synthetic", "source": {"sha256": "0" * 64}, "media": {"duration_sec": duration, "fps": fps, "audio": None}}
            auto = corpus.analyse(rec, Path("synthetic.mp4"), SyntheticDecoder(fps, colour_at, duration), cache_dir=tmp, log=lambda *a: None)
            self.assertTrue((tmp / "ref-synthetic" / "overview.jpg").exists())
            return [(b["kind"], b["t"]) for b in auto["boundaries"]]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_pipeline_separates_cuts_from_dissolves(self):
        red, cream, navy = np.array([200, 40, 30.]), np.array([244, 239, 230.]), np.array([20, 30, 80.])
        for d in (0.25, 0.5, 1.0):
            def colour(t, d=d):
                if t < 2.0:
                    return red
                if t < 4.0:
                    return cream
                return cream + (navy - cream) * min(1.0, max(0.0, (t - 4.0) / d))
            found = self.run_pipeline(colour)
            self.assertEqual([k for k, _ in found], ["cut", "soft"], f"dissolve {d}s: {found}")
            self.assertAlmostEqual(found[0][1], 2.0, delta=1 / 30)
            self.assertTrue(4.0 <= found[1][1] <= 4.0 + d, f"dissolve {d}s: {found}")

    def test_pipeline_keeps_fast_montage_cuts(self):
        seq = [np.array(c, float) for c in ([200, 40, 30], [244, 239, 230], [20, 30, 80], [240, 200, 60])]
        found = self.run_pipeline(lambda t: seq[0] if t < 5.0 else seq[int((t - 5.0) / 0.3) % 4])
        self.assertEqual([k for k, _ in found], ["cut"] * 3, found)
        for (_, t), want in zip(found, (5.3, 5.6, 5.9)):
            self.assertAlmostEqual(t, want, delta=1 / 30)

    def test_holds_cover_static_stretches_only(self):
        _, steps, times = self.boundaries(self.frames(40, 1, 40))
        holds = corpus.holds_from(times, steps["changed"])
        self.assertEqual(len(holds), 2, holds)
        self.assertLessEqual(holds[0][1], 39 / 8 + 0.01)
        self.assertGreaterEqual(holds[1][0], 40 / 8 - 0.01)

    def test_click_track_tempo_and_cut_alignment(self):
        sr = 22050
        x = np.zeros(sr * 8, np.float32)
        click = (np.hanning(220) * np.sin(np.arange(220) * 0.6)).astype(np.float32)
        beats = [0.25 + 0.5 * i for i in range(15)]
        for t in beats:
            i = int(t * sr)
            x[i:i + 220] += click
        on_beat = corpus.analyse_audio(x, sr, beats[2:10], 30.0)
        self.assertTrue(on_beat["present"])
        self.assertAlmostEqual(on_beat["tempo_estimate"]["bpm"], 120, delta=3)
        self.assertGreaterEqual(on_beat["onsets"], 13)
        self.assertEqual(on_beat["boundary_onset_alignment"]["near_onset"], 1.0)
        off_beat = corpus.analyse_audio(x, sr, [t + 0.25 for t in beats[2:10]], 30.0)
        self.assertEqual(off_beat["boundary_onset_alignment"]["near_onset"], 0.0)
        silent = corpus.analyse_audio(np.zeros(sr * 2, np.float32), sr, [], 30.0)
        self.assertTrue(silent.get("silent"))


# ------------------------------------------------------------------ knowledge-base rules
SRC_ID = "ref-0123456789"


def base_records():
    src = {
        "id": SRC_ID, "status": "experimental",
        "source": {"sha256": "0123456789" + "ab" * 27},
        "media": {"duration_sec": 10.0},
        "analysis": {"state": "inspected", "inspected_on": "2026-10-30", "method": "contact sheets",
                     "concept": {"observed": "o", "interpreted": "i", "confidence": "medium"}},
        "automated": {"analyzer": {"version": corpus.ANALYZER_VERSION}},
        "rights": {"usage": "inspiration-only", "brand_assets": [{"kind": "logo", "policy": "exclude"}]},
        "techniques": [{"id": "demo-technique", "timestamps": [1.0]}],
        "related": {},
    }
    tech = {
        "id": "demo-technique", "status": "experimental", "source": {"inspected": True},
        "implementation_state": "implemented",
        "validation": {"state": "preview", "evidence": [
            {"kind": "runtime-test", "path": "tests/test-studio-runtime.py", "result": "pass", "date": "2026-10-30"}]},
        "provenance": [{"source_id": SRC_ID, "timestamps": [1.0], "observed": "o"}],
        "capability": {"support": "native", "compatible_components": ["fx-a"], "resources": {"basis": "estimated"}},
        "related": {},
    }
    return {"references": {"demo-technique": tech}, "reference-sources": {SRC_ID: src},
            "effects": {"fx-a": {"id": "fx-a"}}, "compositions": {}, "project-templates": {}, "styles": {}}


class TestKnowledgeBaseRules(unittest.TestCase):

    def check(self, mutate=None):
        records = base_records()
        if mutate:
            mutate(records["references"]["demo-technique"], records["reference-sources"][SRC_ID], records)
        all_ids = {rid: coll for coll, items in records.items() for rid in items}
        errors, warnings = [], []
        catalogue.validate_knowledge_base(records, all_ids, errors, warnings)
        return errors, warnings

    def assertFlags(self, mutate, needle, kind="error"):
        errors, warnings = self.check(mutate)
        pool = errors if kind == "error" else warnings
        self.assertTrue(any(needle in m for m in pool), f"expected {kind} containing '{needle}', got errors={errors} warnings={warnings}")

    def test_consistent_records_pass(self):
        self.assertEqual(self.check(), ([], []))

    def test_validation_needs_evidence(self):
        self.assertFlags(lambda t, s, r: t["validation"].update(evidence=[]), "without evidence")

    def test_validation_needs_an_implementation(self):
        self.assertFlags(lambda t, s, r: t.update(implementation_state="documented"), "only documented")

    def test_approval_needs_a_render(self):
        self.assertFlags(lambda t, s, r: t.update(status="approved"), "without render-host validation")

    def test_provenance_needs_inspection(self):
        self.assertFlags(lambda t, s, r: t["source"].update(inspected=False), "source.inspected is false")
        self.assertFlags(lambda t, s, r: s["analysis"].update(state="automated"), "has not been inspected")
        self.assertFlags(lambda t, s, r: s["analysis"].update(state="automated"), "is experimental but its analysis is only")

    def test_provenance_must_resolve_and_fit_the_duration(self):
        self.assertFlags(lambda t, s, r: t["provenance"][0].update(source_id="ref-ffffffffff"), "unknown reference source")
        self.assertFlags(lambda t, s, r: t["provenance"][0].update(timestamps=[42.0]), "beyond the end")
        self.assertFlags(lambda t, s, r: s["techniques"][0].update(timestamps=[42.0]), "timestamp beyond")

    def test_links_are_two_way(self):
        self.assertFlags(lambda t, s, r: s.update(techniques=[]), "does not list technique", kind="warning")
        self.assertFlags(lambda t, s, r: t.update(provenance=[]), "does not cite reference source", kind="warning")

    def test_resources_components_hashes_and_rights(self):
        self.assertFlags(lambda t, s, r: t["capability"]["resources"].update(basis="measured"), "without measurements")
        self.assertFlags(lambda t, s, r: t["capability"].update(compatible_components=["no-such-effect"]), "unknown component")
        self.assertFlags(lambda t, s, r: s["source"].update(sha256="f" * 64), "does not match its content hash")
        self.assertFlags(lambda t, s, r: s["rights"]["brand_assets"][0].update(policy="authorised"), "authorises brand assets")
        self.assertFlags(lambda t, s, r: s.update(status="approved"), "before a person reviews")


# ------------------------------------------------------------------ retrieval and committed records
class TestRetrievalAndRecords(unittest.TestCase):

    def cli(self, *args):
        out = subprocess.run([sys.executable, str(SCRIPTS_DIR / "motion-catalogue.py"), *args],
                             capture_output=True, text=True, encoding="utf-8", cwd=REPO_ROOT, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout

    def test_word_prefix_matching_and_phrases(self):
        self.assertFalse(catalogue.has_term("light", "highlight sweep"))
        self.assertTrue(catalogue.has_term("light", "light theme"))
        self.assertTrue(catalogue.has_term("transition", "transitions"))
        self.assertEqual(catalogue.query_tokens("light-theme reveals"), ["light theme", "reveal"])

    def test_support_and_category_filters(self):
        deps = json.loads(self.cli("search", "--type", "technique", "--support", "additional-dependencies", "-f", "json"))
        self.assertIn("rendered-3d-objects", [r["id"] for r in deps])
        kinetic = json.loads(self.cli("search", "--type", "source", "--category", "kinetic-typography", "-f", "json"))
        self.assertGreaterEqual(len(kinetic), 3)
        self.assertTrue(all(r["id"].startswith("ref-") for r in kinetic))

    def test_recommend_for_the_demo_brief(self):
        brief = REPO_ROOT / "projects" / "paper-plane-field-notes" / "brief.json"
        if not brief.exists():
            self.skipTest("demo project not present")
        rec = catalogue.recommend(catalogue.brief_text(brief), limit=8)
        ids = [r["id"] for r in rec["techniques"]]
        self.assertTrue({"step-progress-tracker", "pen-led-stroke"} & set(ids), ids)
        sources = catalogue.load_all_records()["reference-sources"]
        for r in rec["techniques"]:
            for p in r["precedents"]:
                self.assertIn(p["source"], sources)
        self.assertIn("inspiration-only", rec["note"])
        implemented = catalogue.recommend("word beat kinetic typography", limit=20, include_unimplemented=False)
        self.assertTrue(all(r["lifecycle"] not in ("observed", "specified") for r in implemented["techniques"]))

    @unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema is not installed")
    def test_committed_sources_match_schema_and_hash(self):
        sources = corpus.load_sources()
        for sid, rec in sources.items():
            self.assertEqual(corpus.validate_source(rec), [], sid)
            self.assertEqual(sid, corpus.ref_id_for(rec["source"]["sha256"]))
            self.assertNotRegex(json.dumps(rec["source"]), r"[A-Za-z]:\\\\|/Users/|/home/", f"{sid} stores an absolute path")

    def test_inspiration_only_sources_exclude_brand_assets(self):
        for sid, rec in corpus.load_sources().items():
            if rec["rights"]["usage"] == "inspiration-only":
                for b in rec["rights"].get("brand_assets", []):
                    self.assertEqual(b["policy"], "exclude", sid)


if __name__ == "__main__":
    unittest.main()
