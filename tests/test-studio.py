#!/usr/bin/env python3
"""
tests/test-studio.py
Tests for scripts/studio.py (project lifecycle CLI), the per-format QA expectations in
run-qa-gates.sh and the build-project.sh delegation. Runs without HyperFrames or FFmpeg:
the QA-gate tests put stub ffprobe/ffmpeg executables first on PATH and need bash
(Git Bash on Windows); they are skipped when bash is unavailable.

    python tests/test-studio.py
"""

import argparse
import importlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
studio = importlib.import_module("studio")
studio.ensure_schema_python()  # validate needs jsonschema; switch interpreters now, before any test runs

CHAI = studio.project_dir("masala-chai/v1-recipe")
LEGACY = studio.project_dir("neural-network-learning/v1-baseline")
QA_SCRIPT = REPO_ROOT / ".claude" / "skills" / "video-assembler" / "scripts" / "run-qa-gates.sh"
BUILD_SH = REPO_ROOT / "scripts" / "build-project.sh"


def find_bash():
    """Git Bash on Windows (never WSL's System32 bash), plain bash elsewhere."""
    if os.name != "nt":
        return shutil.which("bash")
    candidates = []
    git = shutil.which("git")
    if git:
        root = Path(git).resolve().parents[1]
        candidates += [root / "bin" / "bash.exe", root / "usr" / "bin" / "bash.exe"]
    candidates.append(Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe")
    for c in candidates:
        if c.exists():
            return str(c)
    return None


BASH = find_bash()


def posix(p) -> str:
    return str(p).replace("\\", "/")


def copy_project(src: Path, parent: Path) -> Path:
    dst = parent / src.name
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("frame-review"))
    return dst


class StudioCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    # ---------------------------------------------------------------- validation
    def test_representative_project_validates(self):
        rep = studio.validate_project(CHAI)
        self.assertEqual(rep.errors, [])
        self.assertTrue(any("experimental capabilities" in w for w in rep.warnings))

    def test_legacy_project_is_recognised(self):
        rep = studio.validate_project(LEGACY)
        self.assertTrue(any("legacy" in i for i in rep.info))

    def test_stale_format_files_are_detected(self):
        pdir = copy_project(CHAI, self.tmpdir)
        index = pdir / "src" / "index.html"
        index.write_text(index.read_text(encoding="utf-8") + "\n<!-- edited -->\n", encoding="utf-8", newline="\n")
        rep = studio.validate_project(pdir)
        self.assertTrue(any("out of date" in e for e in rep.errors), rep.errors)
        studio.cmd_formats(argparse.Namespace(slug=str(pdir), size=None))
        self.assertFalse(any("out of date" in e for e in studio.validate_project(pdir).errors))

    def test_banned_patterns_are_errors(self):
        pdir = copy_project(CHAI, self.tmpdir)
        index = pdir / "src" / "index.html"
        html = index.read_text(encoding="utf-8").replace("var r2 =", "var jitter = Math.random();\n  var r2 =", 1)
        index.write_text(html, encoding="utf-8", newline="\n")
        rep = studio.validate_project(pdir)
        self.assertTrue(any("Math.random" in e for e in rep.errors), rep.errors)

    def test_gsap_is_vendored_and_network_scripts_warn(self):
        self.assertIn('src="_studio/vendor/gsap.min.js"', (CHAI / "src" / "index.html").read_text(encoding="utf-8"))
        self.assertTrue((CHAI / "src" / "_studio" / "vendor" / "gsap.min.js").exists(), "studio.py sync copies the vendored GSAP")
        pdir = copy_project(CHAI, self.tmpdir)
        index = pdir / "src" / "index.html"
        cdn = "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"
        index.write_text(index.read_text(encoding="utf-8").replace("_studio/vendor/gsap.min.js", cdn), encoding="utf-8", newline="\n")
        rep = studio.validate_project(pdir)
        self.assertTrue(any(cdn in w and "_studio/vendor/gsap.min.js" in w for w in rep.warnings), rep.warnings)

    def test_runtime_lock_detects_local_edit(self):
        pdir = copy_project(CHAI, self.tmpdir)
        core = pdir / "src" / "_studio" / "studio-core.js"
        core.write_text(core.read_text(encoding="utf-8") + "\n// local hack\n", encoding="utf-8", newline="\n")
        rep = studio.runtime_integrity(pdir)
        self.assertTrue(any("edited in place" in e for e in rep.errors), rep.errors)
        self.assertEqual(studio.cmd_sync(argparse.Namespace(slug=str(pdir), force=False)), 1)
        self.assertEqual(studio.cmd_sync(argparse.Namespace(slug=str(pdir), force=True)), 0)
        self.assertEqual(studio.runtime_integrity(pdir).errors, [])

    # ---------------------------------------------------------------- formats
    def test_format_entries_follow_presets(self):
        project = json.loads((CHAI / "project.json").read_text(encoding="utf-8"))
        entries = {e["id"]: e for e in studio.format_entries(project)}
        self.assertEqual((entries["landscape"]["width"], entries["landscape"]["height"]), (1280, 720))
        self.assertEqual((entries["portrait"]["width"], entries["portrait"]["height"]), (720, 1280))
        self.assertEqual((entries["square"]["width"], entries["square"]["height"]), (1080, 1080))
        self.assertEqual(entries["landscape"]["file"], "index.html")
        big = {e["id"]: e for e in studio.format_entries(project, "1080p")}
        self.assertEqual((big["portrait"]["width"], big["portrait"]["height"]), (1080, 1920))
        self.assertEqual(big["portrait"]["file"], "index.portrait-1080p.html")

    def test_generated_variant_rewrites_root_and_layout_vars(self):
        variant = (CHAI / "src" / "index.portrait.html").read_text(encoding="utf-8")
        self.assertTrue(variant.startswith(studio.GENERATED_MARK))
        self.assertIn('data-format="portrait"', variant)
        self.assertIn('data-width="720"', variant)
        self.assertIn('data-height="1280"', variant)
        self.assertIn("--w:720px;--h:1280px;--u:7.2px;", variant)
        self.assertEqual(variant.count('data-composition-id="root"'), 1)

    # ---------------------------------------------------------------- scaffolding
    def test_every_template_scaffolds_and_validates(self):
        original = studio.PROJECTS_DIR
        studio.PROJECTS_DIR = self.tmpdir
        try:
            records = studio.catalogue_records()["project-templates"]
            for tdir in sorted(p for p in studio.TEMPLATES_DIR.iterdir() if p.is_dir()):
                with self.subTest(template=tdir.name):
                    self.assertIn(tdir.name, records, "template folder must be registered")
                    slug = f"scratch-{tdir.name}"
                    studio.cmd_new(argparse.Namespace(slug=slug, template=tdir.name, title="Scratch & <Test>", style=None, formats=None))
                    pdir = self.tmpdir / slug
                    project = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
                    self.assertEqual(project["slug"], slug)
                    self.assertIn("Scratch &amp; &lt;Test&gt;", (pdir / "src" / "index.html").read_text(encoding="utf-8"))
                    rep = studio.validate_project(pdir)
                    self.assertEqual(rep.errors, [], f"{tdir.name}: {rep.errors}")
        finally:
            studio.PROJECTS_DIR = original

    def test_new_rejects_bad_slug_and_unknown_template(self):
        with self.assertRaises(SystemExit):
            studio.cmd_new(argparse.Namespace(slug="Bad Slug", template="illustrated-explainer", title=None, style=None, formats=None))
        with self.assertRaises(SystemExit):
            studio.cmd_new(argparse.Namespace(slug="ok-slug", template="no-such-template", title=None, style=None, formats=None))

    # ---------------------------------------------------------------- build plans
    def test_studio_build_plan_covers_every_format(self):
        plan = studio.build_plan(CHAI, None, None)
        stages = [s["stage"] for s in plan]
        for fid, entry in (("landscape", "index.html"), ("portrait", "index.portrait.html"), ("square", "index.square.html")):
            self.assertIn(f"render:{fid}", stages)
            render = next(s for s in plan if s["stage"] == f"render:{fid}")
            self.assertIn("--low-memory-mode", render["cmd"])
            self.assertEqual(render["cmd"][render["cmd"].index("--composition") + 1], entry)
            qa = next(s for s in plan if s["stage"] == f"qa:{fid}")
            self.assertIn("--allow-silent", qa["cmd"], "silent deliverable must not fail loudness")
        self.assertNotIn("narration", stages)

    def test_legacy_build_plan_delegates_to_original_orchestrator(self):
        plan = studio.build_plan(LEGACY, None, None)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["cmd"], ["bash", "scripts/build-project.sh", LEGACY.name])

    def test_narrated_plan_passes_voice_speed_and_loudness(self):
        pdir = copy_project(CHAI, self.tmpdir)
        project = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
        project["audio"].update(narration=True, voice="af_bella", speed=1.1, loudness_target_lufs=-16, loudness_tolerance_lu=1.5)
        (pdir / "project.json").write_text(json.dumps(project), encoding="utf-8")
        plan = studio.build_plan(pdir, None, ["portrait"])
        narr = next(s for s in plan if s["stage"] == "narration")
        self.assertEqual(narr["cmd"][-4:], ["--voice", "af_bella", "--speed", "1.1"])
        qa = next(s for s in plan if s["stage"] == "qa:portrait")
        self.assertIn("--expect-lufs", qa["cmd"])
        self.assertNotIn("--allow-silent", qa["cmd"])
        self.assertFalse(any(s["stage"].endswith(":landscape") for s in plan))

    # ---------------------------------------------------------------- captions & review
    def test_captions_from_measured_timeline(self):
        pdir = self.tmpdir / "cap-demo"
        (pdir / "audio").mkdir(parents=True)
        (pdir / "src").mkdir()
        timeline = {"scenes": [
            {"id": "s1", "text": "First sentence here. Second one!", "start_time_sec": 0.0, "duration_sec": 4.0},
            {"id": "s2", "text": "Only one sentence.", "start_time_sec": 4.5, "duration_sec": 2.0},
        ]}
        (pdir / "audio" / "timeline.json").write_text(json.dumps(timeline), encoding="utf-8")
        self.assertEqual(studio.cmd_captions(argparse.Namespace(slug=str(pdir))), 0)
        js = (pdir / "src" / "captions.js").read_text(encoding="utf-8")
        cues = json.loads(js.split("window.STUDIO_CAPTIONS = ", 1)[1].rstrip().rstrip(";"))
        self.assertEqual([c["text"] for c in cues], ["First sentence here.", "Second one!", "Only one sentence."])
        self.assertAlmostEqual(cues[1]["end"], 4.0, places=2)
        self.assertEqual(cues[2]["start"], 4.5)
        vtt = (pdir / "captions" / "cap-demo.vtt").read_text(encoding="utf-8")
        self.assertTrue(vtt.startswith("WEBVTT"))
        self.assertIn("00:00:04.500 --> 00:00:06.500", vtt)

    def test_creative_review_of_representative_project_passes(self):
        self.assertEqual(studio.cmd_review(argparse.Namespace(slug=str(CHAI), init=False)), 0)


    # ---------------------------------------------------------------- categories and series
    def _scaffold(self, slug, **kw):
        ns = dict(slug=slug, template="illustrated-explainer", title=None, style=None, formats=None, category=None)
        ns.update(kw)
        studio.cmd_new(argparse.Namespace(**ns))
        return self.tmpdir / slug

    def test_new_writes_multiple_categories_into_brief(self):
        original = studio.PROJECTS_DIR
        studio.PROJECTS_DIR = self.tmpdir
        try:
            pdir = self._scaffold("cat-multi", category="history,finance")
            brief = json.loads((pdir / "brief.json").read_text(encoding="utf-8"))
            self.assertEqual(brief["categories"], ["history", "finance"])
            self.assertEqual(studio.validate_project(pdir).errors, [])
            with self.assertRaises(SystemExit):
                self._scaffold("cat-bad", category="cooking")
        finally:
            studio.PROJECTS_DIR = original

    def test_missing_category_warns_and_style_mismatch_warns(self):
        original = studio.PROJECTS_DIR
        studio.PROJECTS_DIR = self.tmpdir
        try:
            plain = studio.validate_project(self._scaffold("cat-none"))
            self.assertTrue(any("no categories" in w for w in plain.warnings))
            odd = studio.validate_project(self._scaffold("cat-odd", category="science", style="archival"))
            self.assertTrue(any("archival" in w and "tagged for" in w for w in odd.warnings))
            fine = studio.validate_project(self._scaffold("cat-fine", category="history", style="archival"))
            self.assertFalse(any("tagged for" in w for w in fine.warnings))
            general = studio.validate_project(self._scaffold("cat-gen", category="science", style="editorial-light"))
            self.assertFalse(any("tagged for" in w for w in general.warnings))
        finally:
            studio.PROJECTS_DIR = original

    def test_category_list_and_style_tags_are_consistent(self):
        ids = list(studio.load_categories())
        self.assertEqual(len(ids), len(set(ids)))
        for sid, rec in studio.catalogue_records()["styles"].items():
            self.assertEqual(studio.unknown_categories(rec.get("categories", [])), [], sid)

    def test_series_sequential_and_collection_rules(self):
        orig_p, orig_s = studio.PROJECTS_DIR, studio.SERIES_DIR
        studio.PROJECTS_DIR, studio.SERIES_DIR = self.tmpdir / "projects", self.tmpdir / "series"
        studio.PROJECTS_DIR.mkdir()
        try:
            self._scaffold_in_projects("part-one", "history")
            self._scaffold_in_projects("part-two", "finance")
            studio.cmd_series_new(argparse.Namespace(slug="saga", kind="sequential", category="history", title=None, style=None))
            studio.cmd_series_add(argparse.Namespace(series="saga", project="part-one", part=None, title=None, planned=False))
            studio.cmd_series_add(argparse.Namespace(series="saga", project="part-two", part=None, title=None, planned=False))
            studio.cmd_series_add(argparse.Namespace(series="saga", project="part-three", part=None, title=None, planned=True))
            ser = studio.load_series("saga")
            self.assertEqual([m["part"] for m in ser["members"]], [1, 2, 3])
            rep = studio.validate_series(ser, "saga")
            self.assertEqual(rep.errors, [])
            self.assertTrue(any("part-two" in w for w in rep.warnings), "brief categories outside the series should warn")
            with self.assertRaises(SystemExit):  # a real project that does not exist must be marked planned
                studio.cmd_series_add(argparse.Namespace(series="saga", project="ghost", part=None, title=None, planned=False))
            ser["members"][1]["part"] = 1
            self.assertTrue(any("repeat" in e for e in studio.validate_series(ser, "saga").errors))
            coll = {"spec_version": 1, "slug": "themed", "title": "Themed", "kind": "collection",
                    "categories": ["history", "finance"], "members": [{"project": "part-one", "part": 1}]}
            self.assertTrue(any("no order" in e for e in studio.validate_series(coll, "themed").errors))
            coll["members"] = [{"project": "part-one"}, {"project": "part-two"}]
            self.assertEqual(studio.validate_series(coll, "themed").errors, [])
        finally:
            studio.PROJECTS_DIR, studio.SERIES_DIR = orig_p, orig_s

    def _scaffold_in_projects(self, slug, category):
        studio.cmd_new(argparse.Namespace(slug=slug, template="illustrated-explainer", title=None, style=None,
                                          formats=None, category=category))


@unittest.skipUnless(BASH, "bash not available")
class ShellScriptTests(unittest.TestCase):
    FFPROBE = """#!/usr/bin/env bash
if [[ "$*" == *"format=duration,size,bit_rate"* ]]; then
  echo '{"format":{"duration":"'"$STUB_DUR"'","size":"1048576","bit_rate":"800000"}}'
  exit 0
fi
audio=''
if [[ "${STUB_AUDIO:-0}" == 1 ]]; then
  audio=',{"index":1,"codec_type":"audio","codec_name":"aac","duration":"'"$STUB_DUR"'"}'
fi
echo '{"streams":[{"index":0,"codec_type":"video","codec_name":"h264","width":'"$STUB_W"',"height":'"$STUB_H"',"r_frame_rate":"'"$STUB_FPS"'/1","duration":"'"$STUB_DUR"'"}'"$audio"'],"format":{"duration":"'"$STUB_DUR"'"}}'
"""
    FFMPEG = """#!/usr/bin/env bash
if [[ "$*" == *ebur128* ]]; then
  printf '[Parsed_ebur128_0 @ 0x0] Summary:\\n\\n  Integrated loudness:\\n    I:         %s LUFS\\n    Threshold: -26.0 LUFS\\n\\n  Loudness range:\\n    LRA:         4.0 LU\\n' "$STUB_LUFS" >&2
fi
exit 0
"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.stubs = Path(self.tmp.name) / "bin"
        self.stubs.mkdir()
        for name, body in (("ffprobe", self.FFPROBE), ("ffmpeg", self.FFMPEG)):
            path = self.stubs / name
            path.write_text(body, encoding="utf-8", newline="\n")
            path.chmod(0o755)
        self.video = Path(self.tmp.name) / "final.mp4"
        self.video.write_bytes(b"")

    def tearDown(self):
        self.tmp.cleanup()

    def run_qa(self, *flags, audio=False, w=1280, h=720, fps=30, dur=31.0, lufs=-16.0):
        env = dict(os.environ, STUB_AUDIO="1" if audio else "0", STUB_W=str(w), STUB_H=str(h), STUB_FPS=str(fps),
                   STUB_DUR=f"{dur}", STUB_LUFS=f"{lufs}", PYTHON_BIN=posix(sys.executable))
        env["PATH"] = str(self.stubs) + os.pathsep + env.get("PATH", "")
        res = subprocess.run([BASH, posix(QA_SCRIPT), posix(self.video), *flags], env=env, capture_output=True,
                             text=True, encoding="utf-8", errors="replace")
        return res.returncode, res.stdout + res.stderr

    def test_scripts_parse(self):
        for script in (QA_SCRIPT, BUILD_SH, REPO_ROOT / "scripts" / "build-all.sh", REPO_ROOT / "scripts" / "render.sh"):
            res = subprocess.run([BASH, "-n", posix(script)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"{script.name}: {res.stderr}")

    def test_expectations_pass(self):
        code, out = self.run_qa("--expect-width", "1280", "--expect-height", "720", "--expect-fps", "30",
                                "--expect-duration", "31", "--expect-lufs", "-16", "--lufs-tolerance", "1", audio=True)
        self.assertEqual(code, 0, out)
        self.assertIn("Within target", out)

    def test_wrong_format_fails(self):
        code, out = self.run_qa("--expect-width", "720", "--expect-height", "1280", "--expect-duration", "31", "--allow-silent")
        self.assertEqual(code, 2, out)
        self.assertIn("Width 1280 != expected 720", out)

    def test_duration_and_fps_mismatch_fail(self):
        code, out = self.run_qa("--expect-fps", "60", "--expect-duration", "20", "--allow-silent")
        self.assertEqual(code, 2, out)
        self.assertIn("Frame rate 30 != expected 60", out)
        self.assertIn("Duration 31.000s differs", out)

    def test_loudness_outside_target_fails(self):
        code, out = self.run_qa("--expect-lufs", "-16", "--lufs-tolerance", "1", audio=True, lufs=-23.5)
        self.assertEqual(code, 2, out)
        self.assertIn("-23.5 LUFS is outside", out)

    def test_silent_video(self):
        code, out = self.run_qa("--expect-width", "1280", "--allow-silent")
        self.assertEqual(code, 0, out)
        self.assertIn("silent deliverable allowed", out)
        code, out = self.run_qa("--expect-width", "1280")
        self.assertEqual(code, 2, out)
        code, out = self.run_qa()
        self.assertEqual(code, 0, "legacy mode without expectations stays informational:\n" + out)

    def test_build_project_delegates_studio_projects(self):
        fake_py = self.stubs / "fakepython"
        fake_py.write_text('#!/usr/bin/env bash\necho "FAKEPY $*"\n', encoding="utf-8", newline="\n")
        fake_py.chmod(0o755)
        env = dict(os.environ, PYTHON_BIN=posix(fake_py))
        chai_slug = CHAI.relative_to(REPO_ROOT / "projects").as_posix()
        res = subprocess.run([BASH, posix(BUILD_SH), chai_slug], env=env, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", cwd=REPO_ROOT)
        out = res.stdout + res.stderr
        self.assertEqual(res.returncode, 0, out)
        self.assertIn("delegating to the multi-format studio build", out)
        self.assertRegex(out, rf"FAKEPY .*scripts/studio\.py build {re.escape(chai_slug)}")


SESSION_GUARD = REPO_ROOT / "scripts" / "session-guard.py"


class BuildBookkeepingTests(unittest.TestCase):
    """Render stamps, 48 kHz delivery audio and the shared render lock."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_loudnorm_mix_is_resampled_to_48k(self):
        pdir = copy_project(CHAI, self.tmpdir)
        project = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
        project["audio"].update(narration=True, loudness_target_lufs=-16)
        (pdir / "project.json").write_text(json.dumps(project), encoding="utf-8")
        plan = studio.build_plan(pdir, None, ["portrait"])
        mux = next(s for s in plan if s["stage"] == "mux:portrait")
        graph = mux["cmd"][mux["cmd"].index("-filter_complex") + 1]
        self.assertRegex(graph, r"loudnorm=[^\[]*,aresample=48000\[aout\]")

    def _first_render(self, pdir):
        project = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
        entry = studio.format_entries(project)[0]
        q = project.get("quality", "looks")
        return entry, studio.render_fingerprint(pdir, entry, project["fps"], q), (project["fps"], q)

    def test_render_stamp_detects_stale_and_unstamped_renders(self):
        pdir = copy_project(CHAI, self.tmpdir)
        shutil.rmtree(pdir / "renders", ignore_errors=True)
        entry, fp, _ = self._first_render(pdir)
        fid = entry["id"]
        self.assertEqual(studio.render_stamp_state(pdir, fid, fp), "missing")
        (pdir / "renders" / fid).mkdir(parents=True)
        (pdir / "renders" / fid / "visuals.mp4").write_bytes(b"x")
        self.assertEqual(studio.render_stamp_state(pdir, fid, fp), "unstamped")
        studio.write_render_stamp(pdir, fid, fp)
        self.assertEqual(studio.render_stamp_state(pdir, fid, fp), "current")
        index = pdir / "src" / entry["file"]
        index.write_text(index.read_text(encoding="utf-8") + "\n<!-- edit -->\n", encoding="utf-8")
        _, fp2, _ = self._first_render(pdir)
        self.assertNotEqual(fp, fp2)
        self.assertEqual(studio.render_stamp_state(pdir, fid, fp), "current")
        self.assertEqual(studio.render_stamp_state(pdir, fid, fp2), "stale")

    def _fake_render(self, pdir, fid, payload=b"old"):
        base = pdir / "renders" / fid
        base.mkdir(parents=True, exist_ok=True)
        (base / "visuals.mp4").write_bytes(payload)
        (base / "final.mp4").write_bytes(payload + b"-final")

    def _isolated_out(self):
        """Point delivered files at a temp out/ so no test touches the real deliverables."""
        out = self.tmpdir / "out"
        out.mkdir(exist_ok=True)
        old = studio.OUT_DIR
        studio.OUT_DIR = out
        self.addCleanup(setattr, studio, "OUT_DIR", old)
        return out

    def test_stale_render_moves_to_history_with_the_changed_files(self):
        out = self._isolated_out()
        pdir = copy_project(CHAI, self.tmpdir)
        shutil.rmtree(pdir / "renders", ignore_errors=True)
        entry, _, (fps, q) = self._first_render(pdir)
        fid = entry["id"]
        inputs = studio.render_inputs(pdir, entry)
        self._fake_render(pdir, fid)
        studio.write_render_stamp(pdir, fid, studio.render_fingerprint(pdir, entry, fps, q, inputs), inputs)
        project = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
        delivered = studio.delivered_path(pdir, project, fid)
        self.assertEqual(delivered.parent, out)
        delivered.write_bytes(b"old-final")
        core = pdir / "src" / "_studio" / "studio-core.js"
        core.write_text(core.read_text(encoding="utf-8") + "\n// upgraded\n", encoding="utf-8")
        rows = {r["format"]: r for r in studio.render_states(pdir)}
        self.assertEqual(rows[fid]["state"], "stale")
        self.assertEqual(rows[fid]["changed"], ["_studio/studio-core.js"])

        dest = studio.archive_render(pdir, fid, "test", rows[fid]["inputs"])
        self.assertEqual(dest.parent, pdir / "renders" / "history" / fid)
        self.assertEqual((dest / "visuals.mp4").read_bytes(), b"old")
        self.assertTrue((dest / "final.mp4").exists() and (dest / studio.STAMP_NAME).exists())
        self.assertFalse((pdir / "renders" / fid / "visuals.mp4").exists(), "the stale render must leave the working slot")
        self.assertFalse(delivered.exists(), "the stale deliverable must leave out/")
        self.assertEqual((out / "archive" / f"{delivered.stem}.{dest.name}.mp4").read_bytes(), b"old-final")
        hist = json.loads((dest / "history.json").read_text(encoding="utf-8"))
        self.assertEqual(hist["changed_inputs"], ["_studio/studio-core.js"])
        self.assertEqual(hist["reason"], "test")
        self.assertEqual(studio.render_stamp_state(pdir, fid, "anything"), "missing")
        # a second archive of the same render time never overwrites the first
        self._fake_render(pdir, fid, b"again")
        shutil.copy(dest / studio.STAMP_NAME, pdir / "renders" / fid / studio.STAMP_NAME)
        dest2 = studio.archive_render(pdir, fid, "test", None)
        self.assertNotEqual(dest2, dest)
        self.assertEqual((dest / "visuals.mp4").read_bytes(), b"old")
        self.assertIsNone(studio.archive_render(pdir, fid, "nothing left", None))

    def test_build_archives_a_stale_render_before_rendering_again(self):
        self._isolated_out()
        pdir = copy_project(CHAI, self.tmpdir)
        shutil.rmtree(pdir / "renders", ignore_errors=True)
        entry, _, (fps, q) = self._first_render(pdir)
        fid = entry["id"]
        self._fake_render(pdir, fid)
        studio.write_render_stamp(pdir, fid, "an-older-fingerprint", {})
        render = next(s for s in studio.build_plan(pdir, None, [fid]) if s["stage"] == f"render:{fid}")
        fake = dict(render, cmd=[sys.executable, "-c", "open('../renders/%s/%s', 'wb').write(b'new')" % (fid, studio.PARTIAL_NAME)])
        self.assertEqual(studio.run_build_plan(pdir, [fake]), 0)
        self.assertEqual((pdir / "renders" / fid / "visuals.mp4").read_bytes(), b"new")
        history = list((pdir / "renders" / "history" / fid).iterdir())
        self.assertEqual(len(history), 1)
        self.assertEqual((history[0] / "visuals.mp4").read_bytes(), b"old")
        stamp = json.loads((pdir / "renders" / fid / studio.STAMP_NAME).read_text(encoding="utf-8"))
        self.assertEqual(stamp["inputs"], studio.render_inputs(pdir, entry))
        self.assertEqual(studio.render_stamp_state(pdir, fid, studio.render_fingerprint(pdir, entry, fps, q)), "current")

    def test_build_regenerates_format_files_before_validating(self):
        stages = [s["stage"] for s in studio.build_plan(CHAI, None, None)]
        self.assertLess(stages.index("formats"), stages.index("validate"))

    def test_upgrade_resyncs_regenerates_and_moves_superseded_renders(self):
        self._isolated_out()
        pdir = copy_project(CHAI, self.tmpdir)
        shutil.rmtree(pdir / "renders", ignore_errors=True)
        project = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
        entries = studio.format_entries(project)
        stamped, unstamped = entries[0], entries[1]
        # an older runtime in the project, as after a canonical src/studio upgrade; both renders were made with it
        core = pdir / "src" / "_studio" / "studio-core.js"
        core.write_text(core.read_text(encoding="utf-8").replace("Studio.version = '", "Studio.version = 'old-"), encoding="utf-8")
        lock = json.loads(studio.lock_path(pdir).read_text(encoding="utf-8"))
        lock["files"]["studio-core.js"] = studio.sha256_file(core)
        lock["runtime_version"] = "old"
        studio.lock_path(pdir).write_text(json.dumps(lock), encoding="utf-8")
        self._fake_render(pdir, stamped["id"])
        inputs = studio.render_inputs(pdir, stamped)
        studio.write_render_stamp(pdir, stamped["id"], studio.render_fingerprint(pdir, stamped, project["fps"], project.get("quality", "looks"), inputs), inputs)
        self._fake_render(pdir, unstamped["id"])
        rc = studio.cmd_upgrade(argparse.Namespace(slugs=[str(pdir)], all=False, keep_renders=False, force=False))
        self.assertEqual(rc, 0)
        self.assertFalse(studio.runtime_integrity(pdir).warnings, "project should be on the canonical runtime")
        self.assertFalse(studio.validate_project(pdir).errors)
        for e in (stamped, unstamped):
            self.assertFalse((pdir / "renders" / e["id"] / "visuals.mp4").exists(), f"{e['id']} render was superseded")
            hist = next((pdir / "renders" / "history" / e["id"]).iterdir())
            self.assertIn("superseded by upgrade", json.loads((hist / "history.json").read_text(encoding="utf-8"))["reason"])
        stamped_hist = next((pdir / "renders" / "history" / stamped["id"]).iterdir())
        self.assertIn("_studio/studio-core.js", json.loads((stamped_hist / "history.json").read_text(encoding="utf-8"))["changed_inputs"])
        # a second upgrade is a no-op: nothing changes, so the lock and the renders stay as they are
        before = studio.lock_path(pdir).read_text(encoding="utf-8")
        self._fake_render(pdir, stamped["id"], b"fresh")
        inputs = studio.render_inputs(pdir, stamped)
        studio.write_render_stamp(pdir, stamped["id"], studio.render_fingerprint(pdir, stamped, project["fps"], project.get("quality", "looks"), inputs), inputs)
        self.assertEqual(studio.cmd_upgrade(argparse.Namespace(slugs=[str(pdir)], all=False, keep_renders=False, force=False)), 0)
        self.assertEqual(studio.lock_path(pdir).read_text(encoding="utf-8"), before)
        self.assertEqual((pdir / "renders" / stamped["id"] / "visuals.mp4").read_bytes(), b"fresh")

    def test_renders_archive_moves_only_what_was_asked(self):
        self._isolated_out()
        pdir = copy_project(CHAI, self.tmpdir)
        shutil.rmtree(pdir / "renders", ignore_errors=True)
        project = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
        a, b = studio.format_entries(project)[:2]
        self._fake_render(pdir, a["id"])
        studio.write_render_stamp(pdir, a["id"], "stale-one", {})
        self._fake_render(pdir, b["id"])  # unstamped
        studio.cmd_renders(argparse.Namespace(slugs=[str(pdir)], archive=True, unstamped=False, quality=None))
        self.assertFalse((pdir / "renders" / a["id"] / "visuals.mp4").exists())
        self.assertTrue((pdir / "renders" / b["id"] / "visuals.mp4").exists(), "unstamped renders stay without --unstamped")
        studio.cmd_renders(argparse.Namespace(slugs=[str(pdir)], archive=True, unstamped=True, quality=None))
        self.assertFalse((pdir / "renders" / b["id"] / "visuals.mp4").exists())

    def test_fingerprint_ignores_other_formats_and_caches(self):
        pdir = copy_project(CHAI, self.tmpdir)
        entry, fp, _ = self._first_render(pdir)
        other = "index.square.html" if entry["file"] != "index.square.html" else "index.portrait.html"
        (pdir / "src" / other).write_text("<html>changed</html>", encoding="utf-8")
        (pdir / "src" / ".hyperframes").mkdir(exist_ok=True)
        (pdir / "src" / ".hyperframes" / "cache.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self._first_render(pdir)[1], fp)

    def _guard(self, env_extra, code):
        env = {k: v for k, v in os.environ.items() if k != "MOTION_LAB_LOCKS_HELD"}
        env.update(env_extra)
        return subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, cwd=REPO_ROOT, timeout=60)

    def test_render_lock_is_reentrant_for_child_processes_but_excludes_others(self):
        lock_dir = str(self.tmpdir / "locks")
        probe = (
            "import importlib.util as u;"
            f"s=u.spec_from_file_location('g', r'{SESSION_GUARD}');m=u.module_from_spec(s);s.loader.exec_module(m);"
            "import sys\n"
            "try:\n"
            "    with m.acquire_lock('render', slug='probe', timeout_sec=1, poll_interval=0.2): print('GOT')\n"
            "except TimeoutError: print('BUSY')\n"
        )
        holder = (
            "import importlib.util as u,subprocess,sys;"
            f"s=u.spec_from_file_location('g', r'{SESSION_GUARD}');m=u.module_from_spec(s);s.loader.exec_module(m);"
            "import os\n"
            "with m.acquire_lock('render', slug='holder'):\n"
            f"    child=subprocess.run([sys.executable,'-c',{probe!r}],capture_output=True,text=True)\n"
            "    print('CHILD', 'GOT' if 'GOT' in child.stdout else 'BUSY')\n"
            f"    env={{k:v for k,v in os.environ.items() if k!='MOTION_LAB_LOCKS_HELD'}}\n"
            f"    other=subprocess.run([sys.executable,'-c',{probe!r}],capture_output=True,text=True,env=env)\n"
            "    print('OTHER', 'GOT' if 'GOT' in other.stdout else 'BUSY')\n"
        )
        res = self._guard({"MOTION_LAB_LOCK_DIR": lock_dir}, holder)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("CHILD GOT", res.stdout)
        self.assertIn("OTHER BUSY", res.stdout)

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_worktree_resolves_to_the_main_checkout_lock_dir(self):
        main = self.tmpdir / "main"
        (main / "scripts").mkdir(parents=True)
        shutil.copyfile(SESSION_GUARD, main / "scripts" / "session-guard.py")
        git = lambda *a, cwd=main: subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a], cwd=cwd, capture_output=True, text=True)
        git("init", "-q")
        git("add", ".")
        self.assertEqual(git("commit", "-q", "-m", "init").returncode, 0)
        wt = self.tmpdir / "wt"
        self.assertEqual(git("worktree", "add", "-q", "-b", "s", str(wt)).returncode, 0)
        code = "import importlib.util as u;s=u.spec_from_file_location('g','scripts/session-guard.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.LOCK_DIR)"
        env = {k: v for k, v in os.environ.items() if k != "MOTION_LAB_LOCK_DIR"}
        out = lambda cwd: Path(subprocess.run([sys.executable, "-c", code], cwd=cwd, env=env, capture_output=True, text=True).stdout.strip()).resolve()
        self.assertEqual(out(wt), (main / ".locks").resolve())
        self.assertEqual(out(main), (main / ".locks").resolve())

    def test_render_goes_to_a_partial_file_and_only_a_finished_one_becomes_visuals(self):
        self._isolated_out()
        pdir = copy_project(CHAI, self.tmpdir)
        shutil.rmtree(pdir / "renders", ignore_errors=True)
        entry, _, _ = self._first_render(pdir)
        fid = entry["id"]
        render = next(s for s in studio.build_plan(pdir, None, [fid]) if s["stage"] == f"render:{fid}")
        self.assertIn(f"../renders/{fid}/{studio.PARTIAL_NAME}", render["cmd"])
        killed = dict(render, cmd=[sys.executable, "-c", "open('../renders/%s/%s', 'wb').write(b'half'); raise SystemExit(1)" % (fid, studio.PARTIAL_NAME)])
        self.assertEqual(studio.run_build_plan(pdir, [killed]), 1)
        self.assertEqual(studio.render_stamp_state(pdir, fid, render["fingerprint"]), "missing", "a failed render must not leave a visuals.mp4 to reuse")
        silent = dict(render, cmd=[sys.executable, "-c", "pass"])
        self.assertEqual(studio.run_build_plan(pdir, [silent]), 1)
        self.assertFalse((pdir / "renders" / fid / "visuals.mp4").exists())


def write_wav(path: Path, seconds: float, rate: int = 24000) -> None:
    import wave
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))


class NarrationCurrencyTests(unittest.TestCase):
    """Narration is re-synthesised when its script or voice changes, and a timing shift stops the build."""

    SCENES = [{"id": "s1", "title": "One", "text": "First line."}, {"id": "s2", "title": "Two", "text": "Second line, a bit longer."}]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)
        self.pdir = copy_project(CHAI, self.tmpdir)
        shutil.rmtree(self.pdir / "audio", ignore_errors=True)
        project = json.loads((self.pdir / "project.json").read_text(encoding="utf-8"))
        project["audio"].update(narration=True, voice="am_adam", speed=1.15)
        (self.pdir / "project.json").write_text(json.dumps(project), encoding="utf-8")
        self.write_script(self.SCENES)
        self.nar = studio.pipeline_module("narration")

    def tearDown(self):
        self.tmp.cleanup()

    def write_script(self, scenes):
        (self.pdir / "src" / "narration.json").write_text(json.dumps({"scenes": scenes}), encoding="utf-8")

    def request(self):
        return self.nar.resolve_request(self.pdir, speed=1.15, voice="am_adam")

    def build_audio_module(self):
        """scripts/build-audio.py with a stand-in Kokoro whose clips last 0.05 s per character."""
        import types

        import numpy as np
        calls = []

        class FakePipeline:
            def __init__(self, lang_code):
                pass

            def __call__(self, text, voice, speed):
                calls.append(text)
                samples = np.zeros(int(24000 * 0.05 * len(text)), dtype=np.float32)
                yield types.SimpleNamespace(audio=types.SimpleNamespace(numpy=lambda: samples))

        fake = types.ModuleType("kokoro")
        fake.KPipeline = FakePipeline
        self.addCleanup(sys.modules.pop, "kokoro", None)
        sys.modules["kokoro"] = fake
        spec = importlib.util.spec_from_file_location("build_audio", REPO_ROOT / "scripts" / "build-audio.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, calls

    def test_build_audio_reuses_unchanged_scenes_and_keeps_what_it_replaces(self):
        mod, calls = self.build_audio_module()
        mod.build_audio(self.pdir, speed_override=1.15, voice_override="am_adam")
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.nar.narration_state(self.pdir, self.request())[0], "current")
        mod.build_audio(self.pdir, speed_override=1.15, voice_override="am_adam")
        self.assertEqual(len(calls), 2, "an unchanged script must not load Kokoro again")
        self.assertFalse((self.pdir / "audio" / "history").exists())

        self.write_script([self.SCENES[0], dict(self.SCENES[1], text="Second line, rewritten and longer still.")])
        state, reasons = self.nar.narration_state(self.pdir, self.request())
        self.assertEqual((state, reasons), ("stale", ["text edited in s2"]))
        mod.build_audio(self.pdir, speed_override=1.15, voice_override="am_adam")
        self.assertEqual(calls[2:], ["Second line, rewritten and longer still."], "only the edited scene is re-synthesised")
        kept = list((self.pdir / "audio" / "history").iterdir())
        self.assertEqual(len(kept), 1)
        self.assertEqual(sorted(p.name for p in kept[0].iterdir()), ["narration-full.wav", "s2.wav", "timeline.json"])
        self.assertEqual(self.nar.narration_state(self.pdir, self.request())[0], "current")

        tl = self.pdir / "audio" / "timeline.json"
        tl.write_text(json.dumps(dict(json.loads(tl.read_text(encoding="utf-8")), engine="kokoro 0.0.1")), encoding="utf-8")
        mod.build_audio(self.pdir, speed_override=1.15, voice_override="am_adam")
        self.assertEqual(len(calls), 5, "clips from another engine version are all re-made, so the film keeps one voice")
        self.assertEqual(len(list((self.pdir / "audio" / "history").iterdir())), 2)

    def test_smart_prosody_is_opt_in_and_switching_remakes_every_scene(self):
        mod, calls = self.build_audio_module()
        smart_calls = []

        def fake_smart(pipe, text, out_wav, voice, speed, preset):
            smart_calls.append((text, preset))
            write_wav(out_wav, 0.07 * len(text))
            return mod.read_pcm(out_wav)

        mod.synth_smart = fake_smart
        mod.build_audio(self.pdir, speed_override=1.15, voice_override="am_adam")
        self.assertEqual((len(calls), smart_calls), (2, []), "raw stays the default")

        project = json.loads((self.pdir / "project.json").read_text(encoding="utf-8"))
        project["audio"].update(prosody="smart", prosody_preset="documentary")
        (self.pdir / "project.json").write_text(json.dumps(project), encoding="utf-8")
        narr = next(s for s in studio.build_plan(self.pdir, None, None) if s["stage"] == "narration")
        self.assertEqual(narr["cmd"][-4:], ["--prosody", "smart", "--preset", "documentary"])
        state, reasons = self.nar.narration_state(self.pdir, self.nar.resolve_request(self.pdir, **narr["narration_args"]))
        self.assertEqual((state, reasons), ("stale", ["prosody raw -> smart:documentary"]))

        mod.build_audio(self.pdir, speed_override=1.15, voice_override="am_adam", prosody="smart", preset="documentary")
        self.assertEqual([p for _, p in smart_calls], ["documentary", "documentary"], "every scene is re-made, so the film keeps one delivery")
        tl = json.loads((self.pdir / "audio" / "timeline.json").read_text(encoding="utf-8"))
        self.assertEqual(tl["prosody"], "smart:documentary")
        self.assertEqual(self.nar.narration_state(self.pdir, self.nar.resolve_request(self.pdir, **narr["narration_args"]))[0], "current")

    def test_state_reports_voice_speed_scene_changes_and_old_formats(self):
        self.assertEqual(self.nar.narration_state(self.pdir, self.request())[0], "missing")
        write_wav(self.pdir / "audio" / "narration-full.wav", 1.0)
        timeline = {"voice": "am_adam", "speed": 1.15, "pause_sec": 0.5,
                    "scenes": [dict(s, start_time_sec=0.0, end_time_sec=1.0) for s in self.SCENES]}
        (self.pdir / "audio" / "timeline.json").write_text(json.dumps(timeline), encoding="utf-8")
        self.assertEqual(self.nar.narration_state(self.pdir, self.request()), ("current", []))
        state, reasons = self.nar.narration_state(self.pdir, self.nar.resolve_request(self.pdir, speed=1.0, voice="af_bella"))
        self.assertEqual(state, "stale")
        self.assertEqual(reasons, ["voice am_adam -> af_bella", "speed 1.15 -> 1"])
        self.write_script(self.SCENES[:1])
        self.assertIn("scenes ['s1', 's2'] -> ['s1']", self.nar.narration_state(self.pdir, self.request())[1])
        (self.pdir / "audio" / "timeline.json").write_text(json.dumps({"scenes": [{"id": "s1", "start_time_sec": 0}]}), encoding="utf-8")
        self.assertEqual(self.nar.narration_state(self.pdir, self.request())[0], "unknown")

    def _timeline(self, s2_end):
        return {"voice": "am_adam", "speed": 1.15, "pause_sec": 0.5, "total_duration_sec": s2_end,
                "scenes": [dict(self.SCENES[0], start_time_sec=0.0, end_time_sec=2.0, duration_sec=2.0),
                           dict(self.SCENES[1], start_time_sec=2.5, end_time_sec=s2_end, duration_sec=s2_end - 2.5)]}

    def _narration_step(self, writes_timeline=None, exit_code=0):
        step = next(s for s in studio.build_plan(self.pdir, None, None) if s["stage"] == "narration")
        code = "import json,sys\n"
        if writes_timeline is not None:
            code += f"open({str(self.pdir / 'audio' / 'timeline.json')!r}, 'w').write({json.dumps(writes_timeline)!r})\n"
        code += f"sys.exit({exit_code})"
        return dict(step, cmd=[sys.executable, "-c", code])

    def test_build_skips_current_narration_and_stops_when_new_narration_moves_timing(self):
        write_wav(self.pdir / "audio" / "narration-full.wav", 5.0)
        (self.pdir / "audio" / "timeline.json").write_text(json.dumps(self._timeline(5.0)), encoding="utf-8")
        self.assertEqual(studio.run_build_plan(self.pdir, [self._narration_step(exit_code=9)]), 0, "current narration is not re-made")

        self.write_script([self.SCENES[0], dict(self.SCENES[1], text="Second line, now different.")])
        moved = dict(self._timeline(6.2), scenes=[self._timeline(6.2)["scenes"][0], dict(self._timeline(6.2)["scenes"][1], text="Second line, now different.")])
        self.assertEqual(studio.run_build_plan(self.pdir, [self._narration_step(moved)]), 3, "a timing shift must stop the build")
        (self.pdir / "audio" / "timeline.json").write_text(json.dumps(self._timeline(5.0)), encoding="utf-8")
        self.assertEqual(studio.run_build_plan(self.pdir, [self._narration_step(moved)], allow_narration_shift=True), 0)
        (self.pdir / "audio" / "timeline.json").write_text(json.dumps(self._timeline(5.0)), encoding="utf-8")
        same = dict(self._timeline(5.0), scenes=moved["scenes"][:1] + [dict(moved["scenes"][1], end_time_sec=5.0)])
        self.assertEqual(studio.run_build_plan(self.pdir, [self._narration_step(same)]), 0, "a text edit that keeps timing goes on")

    def test_validate_flags_stale_narration_and_speech_longer_than_the_film(self):
        project = json.loads((self.pdir / "project.json").read_text(encoding="utf-8"))
        write_wav(self.pdir / "audio" / "narration-full.wav", 1.0)
        (self.pdir / "audio" / "timeline.json").write_text(json.dumps(self._timeline(project["duration_sec"] + 1.5)), encoding="utf-8")
        self.write_script([self.SCENES[0], dict(self.SCENES[1], text="Changed.")])
        rep = studio.validate_project(self.pdir)
        self.assertTrue(any("cuts the speech" in e for e in rep.errors), rep.errors)
        self.assertTrue(any("narration-full.wav is stale" in w for w in rep.warnings), rep.warnings)


@unittest.skipIf(sys.platform == "win32", "session-guard uses fcntl locks (macOS/Linux render host)")
class SessionGuardTests(unittest.TestCase):
    """Many parallel sessions, one heavy job at a time: shared host lock, FIFO queue, teardown, worktree lifecycle."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)
        self.locks = self.tmpdir / "locks"
        self.env = {k: v for k, v in os.environ.items() if k not in ("MOTION_LAB_LOCKS_HELD", "MOTION_LAB_LOCK_DIR")}
        self.env.update(MOTION_LAB_LOCK_DIR=str(self.locks), MOTION_LAB_LOCK_POLL="0.1")
        self.procs = []

    def tearDown(self):
        for proc in self.procs:
            if proc.poll() is None:
                proc.terminate()  # the guard kills its own job tree on SIGTERM
                try:
                    proc.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            if proc.stdout:
                proc.stdout.close()
        self.tmp.cleanup()

    def guard(self, *args, env=None, wait=True, **kw):
        cmd = [sys.executable, str(SESSION_GUARD), *args]
        if not wait:
            proc = subprocess.Popen(cmd, env=env or self.env, cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.procs.append(proc)
            return proc
        return subprocess.run(cmd, env=env or self.env, cwd=REPO_ROOT, capture_output=True, text=True, timeout=60, **kw)

    def wait_for(self, predicate, timeout=10.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return True
            time.sleep(0.05)
        return False

    def holder(self, resource="render", seconds=60):
        """A session holding the host lock; returns once it really holds it."""
        proc = self.guard("run", "--slug", "holder", resource, "--", sys.executable, "-c", f"import time; time.sleep({seconds})", wait=False)
        self.assertTrue(self.wait_for(lambda: (self.locks / "heavy.json").exists()), "holder never acquired the lock")
        return proc

    def test_tts_and_render_exclude_each_other(self):
        self.holder("render")
        probe = self.guard("run", "--slug", "probe", "tts", "--", "true", env=dict(self.env, MOTION_LAB_LOCK_TIMEOUT="1"))
        self.assertEqual(probe.returncode, 75, probe.stdout + probe.stderr)
        self.assertIn("Timed out", probe.stderr)

    def test_same_job_tree_is_reentrant_across_resources(self):
        code = (
            "import importlib.util as u;"
            f"s=u.spec_from_file_location('g', r'{SESSION_GUARD}');m=u.module_from_spec(s);s.loader.exec_module(m)\n"
            "with m.acquire_lock('tts', slug='inner', timeout_sec=1, poll_interval=0.1): print('INNER-OK')\n"
        )
        res = self.guard("run", "--slug", "outer", "render", "--", sys.executable, "-c", code)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("INNER-OK", res.stdout)

    def test_waiters_are_served_first_come_first_served(self):
        order = self.tmpdir / "order.txt"
        holder = self.holder()
        waiters = []
        for i in range(1, 5):
            waiters.append(self.guard("run", "--slug", f"w{i}", "render", "--", sys.executable, "-c",
                                      f"open(r'{order}', 'a').write('w{i}\\n')", wait=False))
            self.assertTrue(self.wait_for(lambda n=i: len(list((self.locks / "queue").glob("*.ticket"))) == n), "waiter never queued")
        holder.terminate()
        holder.wait(timeout=20)
        for w in waiters:
            w.wait(timeout=30)
        self.assertEqual(order.read_text().split(), ["w1", "w2", "w3", "w4"])

    def test_dead_waiter_does_not_block_the_queue(self):
        holder = self.holder()
        queue = self.locks / "queue"
        queue.mkdir(exist_ok=True)
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        stale = queue / f"{1:020d}-{dead.pid}-heavy.ticket"
        stale.write_text("{}")  # oldest ticket, owner gone
        waiter = self.guard("run", "--slug", "next", "render", "--", "true", wait=False)
        self.assertTrue(self.wait_for(lambda: not stale.exists()), "dead waiter's ticket was not pruned while the holder still runs")
        self.assertEqual(len(list(queue.glob("*.ticket"))), 1, "only the live waiter should be queued")
        self.assertIsNone(waiter.poll(), "waiter must still be waiting for the holder")
        holder.terminate()
        holder.wait(timeout=20)
        self.assertEqual(waiter.wait(timeout=30), 0, waiter.stdout.read())
        self.assertEqual(list(queue.glob("*.ticket")), [])

    def test_sigterm_kills_the_whole_job_tree_before_freeing_the_lock(self):
        pidfile = self.tmpdir / "grandchild.pid"
        job = self.tmpdir / "job.py"
        job.write_text(
            "import subprocess, sys, time\n"
            "gc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'], start_new_session=True)\n"  # detached, like Chrome
            f"open(r'{pidfile}', 'w').write(str(gc.pid))\n"
            "time.sleep(120)\n", encoding="utf-8")
        guard = self.guard("run", "--slug", "victim", "render", "--", sys.executable, str(job), wait=False)
        self.assertTrue(self.wait_for(lambda: pidfile.exists() and pidfile.read_text()), "job never started")
        grandchild = int(pidfile.read_text())
        os.kill(guard.pid, signal.SIGTERM)
        guard.wait(timeout=30)

        def dead(pid):
            try:
                os.kill(pid, 0)
                return False
            except OSError:
                return True
        self.assertTrue(self.wait_for(lambda: dead(grandchild)), "detached grandchild survived the guard (orphaned job)")
        nxt = self.guard("run", "--slug", "next", "tts", "--", "true", env=dict(self.env, MOTION_LAB_LOCK_TIMEOUT="5"))
        self.assertEqual(nxt.returncode, 0, nxt.stdout + nxt.stderr)

    def test_older_sessions_per_resource_lock_still_excludes_same_resource(self):
        """A worktree made before the unified lock locks only render.lock; a new render must wait for it."""
        import fcntl
        self.locks.mkdir(parents=True, exist_ok=True)
        old_style = os.open(str(self.locks / "render.lock"), os.O_CREAT | os.O_RDWR)
        fcntl.flock(old_style, fcntl.LOCK_EX)
        try:
            env = dict(self.env, MOTION_LAB_LOCK_TIMEOUT="1")
            blocked = self.guard("run", "--slug", "new", "render", "--", "true", env=env)
            self.assertEqual(blocked.returncode, 75, blocked.stdout + blocked.stderr)
            self.assertIn("older session", blocked.stdout + blocked.stderr)
            other = self.guard("run", "--slug", "new", "tts", "--", "true", env=env)
            self.assertEqual(other.returncode, 0, "only the same resource is held back, as before the unification")
        finally:
            os.close(old_style)
        after = self.guard("run", "--slug", "new", "render", "--", "true", env=dict(self.env, MOTION_LAB_LOCK_TIMEOUT="5"))
        self.assertEqual(after.returncode, 0, after.stdout + after.stderr)
        self.assertFalse(any((self.locks / "queue").glob("*.ticket")), "a timed-out job must not leave a queue ticket")

    def test_status_reports_holder_and_queue(self):
        self.holder("render")
        self.guard("run", "--slug", "second", "tts", "--", "true", wait=False)
        self.assertTrue(self.wait_for(lambda: any((self.locks / "queue").glob("*.ticket"))))
        out = self.guard("status").stdout
        self.assertIn("BUSY", out)
        self.assertIn("render for project 'holder'", out)
        self.assertIn("tts for 'second'", out)

    def test_hostlock_helper_is_reentrant_under_the_guard(self):
        code = (
            f"import sys; sys.path.insert(0, r'{REPO_ROOT / 'src'}')\n"
            "from pipeline.hostlock import heavy_lock\n"
            "with heavy_lock('tts', slug='x'): print('HELPER-OK')\n"
        )
        res = self.guard("run", "--slug", "outer", "render", "--", sys.executable, "-c", code)
        self.assertIn("HELPER-OK", res.stdout)
        alone = subprocess.run([sys.executable, "-c", code], env=self.env, capture_output=True, text=True, timeout=30)
        self.assertIn("HELPER-OK", alone.stdout, alone.stdout + alone.stderr)

    # ----- worktree lifecycle, in a throwaway repo so the real one is never touched
    def make_repo(self):
        main = self.tmpdir / "main"
        (main / "scripts").mkdir(parents=True)
        shutil.copyfile(SESSION_GUARD, main / "scripts" / "session-guard.py")
        (main / ".gitignore").write_text("renders/\n*.wav\nout/*.mp4\n.locks/\n.worktrees/\n__pycache__/\nlogs/\n.venv\n")
        (main / "shared.txt").write_text("base\n")
        (main / "projects" / "p").mkdir(parents=True)
        (main / "projects" / "p" / "brief.json").write_text("{}")
        self.git_env = dict(self.env, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        self.git_env.pop("MOTION_LAB_LOCK_DIR")
        self.git(main, "init", "-q")
        self.git(main, "add", ".")
        self.git(main, "commit", "-q", "-m", "init")
        return main

    def git(self, cwd, *args):
        res = subprocess.run(["git", *args], cwd=cwd, env=self.git_env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"git {args}: {res.stdout}{res.stderr}")
        return res.stdout

    def repo_guard(self, main, *args):
        return subprocess.run([sys.executable, "scripts/session-guard.py", *args], cwd=main, env=self.git_env, capture_output=True, text=True, timeout=60)

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_session_end_copies_renders_and_audio_back_to_main_before_removing_the_worktree(self):
        main = self.make_repo()
        (main / "logs").mkdir()
        (main / "logs" / "build-timings.jsonl").write_text('{"a": 1}\n')
        self.assertEqual(self.repo_guard(main, "session-start", "p").returncode, 0)
        wt = main / ".worktrees" / "p"
        files = {"projects/p/renders/portrait/final.mp4": b"RENDER", "projects/p/audio/s1.wav": b"WAV", "out/p-portrait.mp4": b"OUT"}
        for rel, data in files.items():
            (wt / rel).parent.mkdir(parents=True, exist_ok=True)
            (wt / rel).write_bytes(data)
        (wt / "scripts" / "__pycache__").mkdir()
        (wt / "scripts" / "__pycache__" / "x.pyc").write_bytes(b"cache")
        (wt / "logs").mkdir()
        (wt / "logs" / "build-timings.jsonl").write_text('{"a": 1}\n{"b": 2}\n')
        main_render = main / "projects/p/renders/portrait/final.mp4"
        main_render.parent.mkdir(parents=True)
        main_render.write_bytes(b"OLDER MAIN RENDER")

        res = self.repo_guard(main, "session-end", "p")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertFalse(wt.exists())
        self.assertEqual((main / "projects/p/audio/s1.wav").read_bytes(), b"WAV")
        self.assertEqual((main / "out/p-portrait.mp4").read_bytes(), b"OUT")
        self.assertEqual(main_render.read_bytes(), b"OLDER MAIN RENDER", "an existing, different file in main must not be overwritten")
        self.assertEqual(Path(str(main_render) + ".session-p").read_bytes(), b"RENDER")
        self.assertFalse((main / "scripts" / "__pycache__" / "x.pyc").exists(), "caches are not session output")
        self.assertEqual((main / "logs" / "build-timings.jsonl").read_text().splitlines(), ['{"a": 1}', '{"b": 2}'])

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_session_end_merge_refuses_conflicts_and_leaves_everything_untouched(self):
        main = self.make_repo()
        self.assertEqual(self.repo_guard(main, "session-start", "p").returncode, 0)
        wt = main / ".worktrees" / "p"
        (wt / "shared.txt").write_text("session edit\n")
        self.git(wt, "commit", "-qam", "session")
        (main / "shared.txt").write_text("main edit\n")
        self.git(main, "commit", "-qam", "main")
        head = self.git(main, "rev-parse", "HEAD")

        res = self.repo_guard(main, "session-end", "p", "--merge")
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("shared.txt", res.stderr)
        self.assertTrue(wt.exists(), "worktree must be kept when the merge would conflict")
        self.assertEqual(self.git(main, "rev-parse", "HEAD"), head)
        self.assertEqual((main / "shared.txt").read_text(), "main edit\n")

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_session_end_merge_succeeds_and_session_list_reports_the_session(self):
        main = self.make_repo()
        self.assertEqual(self.repo_guard(main, "session-start", "p").returncode, 0)
        wt = main / ".worktrees" / "p"
        (wt / "projects" / "p" / "storyboard.json").write_text("{}")
        self.git(wt, "add", ".")
        self.git(wt, "commit", "-qm", "storyboard")
        listing = self.repo_guard(main, "session-list").stdout
        self.assertIn("p   [session/p]", listing)
        self.assertIn("1 commit(s) ahead", listing)
        self.assertIn("merge conflicts with", listing)

        res = self.repo_guard(main, "session-end", "p", "--merge")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertTrue((main / "projects" / "p" / "storyboard.json").exists())
        self.assertFalse(wt.exists())

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_session_start_warns_about_uncommitted_tooling(self):
        main = self.make_repo()
        (main / "scripts" / "new-tool.py").write_text("print('hi')\n")
        res = self.repo_guard(main, "session-start", "p")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("uncommitted tooling change", res.stdout)
        self.assertIn("scripts/new-tool.py", res.stdout)
        self.assertEqual(self.repo_guard(main, "session-start", "bad/slug").returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
