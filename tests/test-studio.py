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
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
studio = importlib.import_module("studio")

CHAI = REPO_ROOT / "projects" / "masala-chai-recipe"
LEGACY = REPO_ROOT / "projects" / "benchmark-neural-network"
QA_SCRIPT = REPO_ROOT / ".agents" / "skills" / "video-assembler" / "scripts" / "run-qa-gates.sh"
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
        res = subprocess.run([BASH, posix(BUILD_SH), CHAI.name], env=env, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", cwd=REPO_ROOT)
        out = res.stdout + res.stderr
        self.assertEqual(res.returncode, 0, out)
        self.assertIn("delegating to the multi-format studio build", out)
        self.assertRegex(out, r"FAKEPY \S*scripts/studio\.py build masala-chai-recipe")


if __name__ == "__main__":
    unittest.main(verbosity=2)
