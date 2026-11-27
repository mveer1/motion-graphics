#!/usr/bin/env python3
"""
tests/test-visual-director.py
Engine routing, visual-plan checks, plate fingerprints, per-format plate sources and the build stage
(scripts/visual-director.py, studio.py hooks). Pure Python, except BlenderTemplateTests, which renders
every plate template for two tiny frames when Blender is installed (skipped otherwise, or with
MOTION_LAB_SKIP_BLENDER=1); it takes the host render lock.

    python tests/test-visual-director.py
"""
import importlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
studio = importlib.import_module("studio")
studio.ensure_schema_python()

spec = importlib.util.spec_from_file_location("visual_director", REPO_ROOT / "scripts" / "visual-director.py")
vd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vd)

PLATE_SCRIPT = "def build(lab, job):\n    lab.world('paper')\n    lab.camera()\n"


def scene(sid, visual, start=0.0, end=4.0, title="Scene"):
    return {"id": sid, "title": title, "start_sec": start, "end_sec": end, "purpose": "p", "visual": visual,
            "capabilities": [], "transition_out": {"type": "cut"}}


class RoutingTests(unittest.TestCase):
    def route(self, visual):
        return vd.route_scene(scene("s1", visual))[0]

    def test_light_transport_goes_to_blender(self):
        self.assertEqual(self.route("A photoreal glass torus with depth of field on a studio set."), "blender")
        self.assertEqual(self.route("Volumetric god rays cut through the haze."), "blender")

    def test_a_chart_about_water_stays_a_chart(self):
        self.assertEqual(self.route("A chart of refraction for water, glass and diamond."), "hyperframes")

    def test_subject_terms_alone_can_route_without_a_form(self):
        self.assertEqual(self.route("Fog rolls over the water."), "blender")

    def test_stylised_3d_goes_to_threejs(self):
        self.assertEqual(self.route("A low-poly 3d model on a turntable."), "threejs")

    def test_no_signal_and_weak_signal_stay_on_the_compositor(self):
        self.assertEqual(self.route("The end card holds."), "hyperframes")
        self.assertEqual(self.route("A single glass on the table."), "hyperframes")  # one subject term: under min_score

    def test_template_hints(self):
        self.assertEqual(vd.suggest_template(scene("s", "The banks collapse like dominoes")), "rigid-collapse")
        self.assertEqual(vd.suggest_template(scene("s", "A galaxy of particles")), "particle-field")
        self.assertEqual(vd.suggest_template(scene("s", "God rays through fog")), "light-shafts")
        self.assertEqual(vd.suggest_template(scene("s", "A photoreal coin")), "hero-orbit")


class ProjectCase(unittest.TestCase):
    """A minimal studio project in a temp folder: portrait + landscape, 10 s, 30 fps."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vd-test-"))
        self.pdir = self.tmp / "demo"
        (self.pdir / "src").mkdir(parents=True)
        self.project = {"slug": "demo", "fps": 30, "duration_sec": 10, "style": "editorial-light",
                        "formats": [{"id": "portrait", "width": 720, "height": 1280, "primary": True},
                                    {"id": "landscape", "width": 1280, "height": 720}]}
        self.write("project.json", self.project)
        self.write("storyboard.json", {"slug": "demo", "scenes": [
            scene("s1", "A photoreal glass orb with depth of field.", 0, 4),
            scene("s2", "A diagram of the light path with labels.", 4, 10)]})
        self.html('<video class="clip plate" src="plates/s1-plate.portrait.mp4" data-start="0" data-duration="4" muted></video>')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, rel, data):
        p = self.pdir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data) if not isinstance(data, str) else data, encoding="utf-8")

    def html(self, body):
        self.write("src/index.html", f'<html><head></head><body><div id="root" data-composition-id="root">{body}</div></body></html>')

    def plan(self, **plate):
        p = {"id": "s1-plate", "script": "blender/s1-plate.py", "scene": "s1", "start_sec": 0, "duration_sec": 4, "alpha": False}
        p.update(plate)
        mode = "plate-over" if p.get("alpha") else "plate-under"
        data = {"spec_version": "1.0.0", "slug": "demo", "decided_by": "director",
                "scenes": [{"scene": "s1", "engine": "blender", "mode": mode, "plates": [p["id"]], "reason": "light"},
                           {"scene": "s2", "engine": "hyperframes", "mode": "native", "reason": "diagram"}],
                "plates": [p]}
        self.write("visual-plan.json", data)
        return data


class DraftPlanTests(ProjectCase):
    def test_draft_routes_and_times_plates_from_the_storyboard(self):
        plan = vd.draft_plan(self.pdir)
        self.assertEqual([s["engine"] for s in plan["scenes"]], ["blender", "hyperframes"])
        self.assertEqual(plan["decided_by"], "heuristic")
        plate = plan["plates"][0]
        self.assertEqual((plate["id"], plate["start_sec"], plate["duration_sec"], plate["template"]), ("s1-plate", 0.0, 4.0, "hero-orbit"))
        self.assertEqual(studio.schema_errors(plan, vd.PLAN_SPEC), [])


class CheckTests(ProjectCase):
    def check(self):
        return vd.check_plan(self.pdir, self.project)

    def test_complete_plan_has_no_errors_and_reports_the_missing_render(self):
        self.plan()
        self.write("blender/s1-plate.py", PLATE_SCRIPT)
        errors, warnings = self.check()
        self.assertEqual(errors, [])
        self.assertTrue(any("not rendered yet" in w for w in warnings))
        self.assertFalse(any("heuristic draft" in w for w in warnings))

    def test_missing_script_is_an_error(self):
        self.plan()
        errors, _ = self.check()
        self.assertTrue(any("script blender/s1-plate.py is missing" in e for e in errors))

    def test_plate_over_needs_alpha_and_extension_must_match(self):
        self.plan()
        data = json.loads((self.pdir / "visual-plan.json").read_text())
        data["scenes"][0]["mode"] = "plate-over"
        self.write("visual-plan.json", data)
        self.write("blender/s1-plate.py", PLATE_SCRIPT)
        errors, _ = self.check()
        self.assertTrue(any("must be rendered with alpha" in e for e in errors))
        self.plan(alpha=True)
        errors, _ = self.check()
        self.assertTrue(any("delivered as .webm" in e for e in errors))

    def test_lint_rejects_nondeterminism_and_text(self):
        self.plan()
        self.write("blender/s1-plate.py", "import random, time\ndef build(lab, job):\n    x = random.random()\n"
                                          "    t = time.time()\n    bpy.data.curves.new('t', type='FONT')\n")
        errors, _ = self.check()
        joined = " ".join(errors)
        self.assertIn("module-level random", joined)
        self.assertIn("wall-clock", joined)
        self.assertIn("no text in plates", joined)
        self.write("blender/s1-plate.py", "def build(lab, job):\n    rng = lab.rng()\n    x = rng.random()  # random.random() in a comment is fine\n")
        errors, _ = self.check()
        self.assertEqual(errors, [])

    def test_plate_past_the_film_end_and_unknown_scene(self):
        self.plan(start_sec=8, duration_sec=4, scene="s9")
        self.write("blender/s1-plate.py", PLATE_SCRIPT)
        errors, _ = self.check()
        self.assertTrue(any("after the film" in e for e in errors))
        self.assertTrue(any("scene 's9'" in e for e in errors))

    def test_blender_scene_cannot_be_native_and_schema_errors_surface(self):
        data = self.plan()
        data["scenes"][0]["mode"] = "native"
        self.write("visual-plan.json", data)
        self.write("blender/s1-plate.py", PLATE_SCRIPT)
        errors, _ = self.check()
        self.assertTrue(any("Blender only makes plates" in e for e in errors))
        data["scenes"][0]["engine"] = "remotion"
        self.write("visual-plan.json", data)
        errors, _ = self.check()
        self.assertTrue(any("visual-plan-spec.json" in e for e in errors))

    def test_data_start_drift_and_unplaced_plate_warn(self):
        self.plan()
        self.write("blender/s1-plate.py", PLATE_SCRIPT)
        self.html('<video class="clip plate" src="plates/s1-plate.portrait.mp4" data-start="0.5" muted></video>')
        _, warnings = self.check()
        self.assertTrue(any("differs from the plan" in w for w in warnings))
        self.html("<div></div>")
        _, warnings = self.check()
        self.assertTrue(any("is not placed in src/index.html" in w for w in warnings))


class StudioHookTests(ProjectCase):
    def test_each_format_entry_loads_its_own_plate(self):
        source = (self.pdir / "src" / "index.html").read_text()
        land = next(e for e in studio.format_entries(self.project) if e["id"] == "landscape")
        html = studio.render_variant(source, land, 30, 10)
        self.assertIn('src="plates/s1-plate.landscape.mp4"', html)
        self.assertNotIn("s1-plate.portrait", html)
        self.assertIn("plates/a-b.square.webm", studio.retarget_plates('<video src="plates/a-b.portrait.webm">', "square"))

    def test_build_plan_renders_plates_before_lint_only_with_plates(self):
        project = dict(self.project, audio={"narration": False, "music": {"enabled": False}, "sfx": False, "captions": False})
        self.write("project.json", project)
        stages = [s["stage"] for s in studio.build_plan(self.pdir, None, None)]
        self.assertNotIn("plates", stages)
        self.plan()
        stages = [s["stage"] for s in studio.build_plan(self.pdir, None, None)]
        self.assertLess(stages.index("plates"), stages.index("lint"))
        self.assertLess(stages.index("plates"), stages.index("render:portrait"))

    def test_validate_reports_plan_problems(self):
        self.plan()
        rep = studio.Report()
        studio.check_visual_plan(self.pdir, self.project, rep)
        self.assertTrue(any(e.startswith("visual plan:") and "missing" in e for e in rep.errors))


class JobAndFingerprintTests(ProjectCase):
    def test_palette_comes_from_the_style_sheet(self):
        pal = vd.palette_for(self.project)
        self.assertEqual(pal["accent"].lower(), "#b8432a")
        self.assertIn("paper", pal)

    def test_fingerprint_tracks_inputs_but_not_local_paths(self):
        self.plan()
        self.write("blender/s1-plate.py", PLATE_SCRIPT)
        plate = json.loads((self.pdir / "visual-plan.json").read_text())["plates"][0]
        entry = studio.format_entries(self.project)[0]
        job = vd.make_job(self.pdir, self.project, plate, entry)
        base = vd.plate_fingerprint(self.pdir, job, "5.2.4")
        self.assertEqual(job["frames_dir"].split("/")[-4:], ["plates", "s1-plate", "portrait", "frames"])
        moved = dict(job, frames_dir="/elsewhere/frames", kit_dir="/elsewhere/kit")
        self.assertEqual(vd.plate_fingerprint(self.pdir, moved, "5.2.4"), base)
        self.assertNotEqual(vd.plate_fingerprint(self.pdir, dict(job, params={"shape": "cube"}), "5.2.4"), base)
        self.assertNotEqual(vd.plate_fingerprint(self.pdir, job, "5.3.0"), base)
        self.assertNotEqual(vd.plate_fingerprint(self.pdir, dict(job, alpha=True), "5.2.4"), base)

    def test_preview_job_is_marked(self):
        self.plan()
        plate = json.loads((self.pdir / "visual-plan.json").read_text())["plates"][0]
        job = vd.make_job(self.pdir, self.project, plate, studio.format_entries(self.project)[1], preview=True)
        self.assertEqual(job["preview"]["frame_step"], 6)
        self.assertTrue(job["frames_dir"].endswith("landscape/preview/frames"))

    def test_pinned_downloads_are_complete(self):
        bl = vd.engines()["blender"]
        for key in ("windows-x64", "macos-arm64", "linux-x64"):
            d = bl["downloads"][key]
            self.assertIn(bl["pinned_version"], d["url"])
            self.assertRegex(d["sha256"], r"^[0-9a-f]{64}$")


BLENDER = None if os.environ.get("MOTION_LAB_SKIP_BLENDER") else vd.find_blender()


@unittest.skipIf(BLENDER is None, "Blender not installed (or MOTION_LAB_SKIP_BLENDER set)")
class BlenderTemplateTests(unittest.TestCase):
    """Every template builds and renders two frames at 96x160 on the installed Blender."""

    def test_templates_render(self):
        templates = sorted(vd.PLATE_TEMPLATES_DIR.glob("*.py"))
        self.assertEqual({t.stem for t in templates}, {"hero-orbit", "particle-field", "rigid-collapse", "light-shafts"})
        palette = vd.palette_for({"style": "editorial-light"})
        work = Path(tempfile.mkdtemp(prefix="vd-blender-"))
        try:
            with studio.render_lock("test-visual-director"):
                for tmpl in templates:
                    for alpha in (False, True) if tmpl.stem == "hero-orbit" else (False,):
                        with self.subTest(template=tmpl.stem, alpha=alpha):
                            out = work / f"{tmpl.stem}-{alpha}"
                            job = {"plate": tmpl.stem, "format": "portrait", "width": 96, "height": 160, "fps": 10,
                                   "duration_sec": 0.2, "alpha": alpha, "engine": "eevee", "samples": 1,
                                   "params": {"count": 40} if tmpl.stem == "particle-field" else {},
                                   "palette": palette, "cues": {}, "kit_dir": vd.KIT_DIR.as_posix(),
                                   "script": tmpl.as_posix(), "frames_dir": (out / "frames").as_posix()}
                            (out / "frames").mkdir(parents=True)
                            vd.write_json(out / "job.json", job)
                            rc = vd.run_blender(BLENDER, out / "job.json", out / "blender.log", 2)
                            frames = sorted((out / "frames").glob("frame_*.png"))
                            self.assertEqual(rc, 0, (out / "blender.log").read_text(encoding="utf-8", errors="replace")[-2000:])
                            self.assertEqual(len(frames), 2)
                            done = json.loads((out / "done.json").read_text())
                            self.assertEqual(done["frames"], 2)
        finally:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
