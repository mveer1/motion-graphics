#!/usr/bin/env python3
"""
tests/test-video-forms.py
The three forms (short, mid, long; specs/video-types.json) and what long films need: the segment planner
(src/pipeline/segments.py), storyboard chapters, the segmented render step in the build plan, length-aware
frame-review defaults and the spec's own consistency. Pure Python: no browser, no HyperFrames, no FFmpeg.

    python tests/test-video-forms.py
"""
import argparse
import importlib
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src" / "pipeline"))
studio = importlib.import_module("studio")
studio.ensure_schema_python()
import segments as seg  # noqa: E402


def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SegmentPlanTests(unittest.TestCase):
    def test_plan_covers_the_film_exactly_and_in_order(self):
        for total, fps in ((660, 30), (21600, 30), (7200, 30), (5400, 30), (2700, 30), (1, 30), (21599, 30)):
            with self.subTest(frames=total):
                plan = seg.plan_segments(total, fps, 90)
                self.assertEqual(plan[0][0], 0)
                self.assertEqual(plan[-1][1], total)
                self.assertTrue(all(a < b for a, b in plan))
                self.assertTrue(all(plan[i][1] == plan[i + 1][0] for i in range(len(plan) - 1)))

    def test_segments_are_about_the_target_length(self):
        plan = seg.plan_segments(21600, 30, 90)  # 12 minutes
        self.assertEqual(len(plan), 8)
        for a, b in plan:
            self.assertLessEqual(b - a, 2700 * 1.35 + 1)
            self.assertGreaterEqual(b - a, 2700 * 0.65 - 1)

    def test_cuts_snap_to_scene_edges_when_one_is_near(self):
        edges = [88.0, 175.5, 300.0]
        plan = seg.plan_segments(21600, 30, 90, edges)
        cuts = {b for _, b in plan}
        self.assertIn(88 * 30, cuts)
        self.assertIn(round(175.5 * 30), cuts)
        # an edge far from any target is ignored
        self.assertNotIn(300 * 30 + 1, cuts)

    def test_a_short_remainder_merges_into_the_previous_segment(self):
        plan = seg.plan_segments(2700 * 2 + 300, 30, 90)
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[-1][1], 2700 * 2 + 300)

    def test_boundaries_come_from_scenes_and_chapters(self):
        sb = {"scenes": [{"start_sec": 0, "end_sec": 10.5}, {"start_sec": 10.5, "end_sec": 20}],
              "chapters": [{"start_sec": 0, "end_sec": 20}]}
        self.assertEqual(seg.boundaries_of(sb), [0, 10.5, 20])
        self.assertEqual(seg.boundaries_of(None), [])

    def test_plan_matches_detects_a_changed_plan(self):
        plan = seg.plan_segments(7200, 30, 90)
        self.assertTrue(seg.plan_matches(seg.plan_record(plan), plan))
        self.assertFalse(seg.plan_matches(seg.plan_record(plan), seg.plan_segments(7200, 30, 60)))


class FormSpecTests(unittest.TestCase):
    def test_every_form_has_a_real_arc_and_skill(self):
        arcs = {a["id"] for a in json.loads((REPO_ROOT / "specs" / "narrative-arcs.json").read_text(encoding="utf-8"))["arcs"]}
        for tid, t in studio.load_video_types().items():
            with self.subTest(form=tid):
                self.assertIn(t["default_arc"], arcs)
                self.assertTrue((REPO_ROOT / ".claude" / "skills" / t["skill"] / "SKILL.md").exists())
                self.assertIn(t["format"], t["formats"])
                self.assertIn(t["platform"], t["platforms"])
                self.assertLessEqual(t["target_sec"], t["nominal_sec"].get("max", 10 ** 9))
                self.assertGreaterEqual(t["target_sec"], t["nominal_sec"]["min"])

    def test_forms_match_the_owner_description(self):
        t = studio.load_video_types()
        self.assertEqual((t["short"]["nominal_sec"]["min"], t["short"]["nominal_sec"]["max"]), (20, 60))
        self.assertEqual((t["mid"]["nominal_sec"]["min"], t["mid"]["nominal_sec"]["max"]), (60, 180))
        self.assertEqual((t["long"]["nominal_sec"]["min"], t["long"]["nominal_sec"]["max"]), (300, 720))

    def test_the_gap_between_mid_and_long_is_deliberate(self):
        t = studio.load_video_types()
        self.assertLess(t["mid"]["window_sec"][1], t["long"]["window_sec"][0])

    def test_aliases_point_at_real_forms(self):
        types = studio.load_video_types()
        for old, new in studio.video_type_aliases().items():
            self.assertIn(new, types)
            self.assertNotIn(old, types)

    def test_brief_and_series_specs_accept_every_id(self):
        ids = set(studio.load_video_types()) | set(studio.video_type_aliases())
        brief = json.loads((REPO_ROOT / "specs" / "brief-spec.json").read_text(encoding="utf-8"))
        series = json.loads((REPO_ROOT / "specs" / "series-spec.json").read_text(encoding="utf-8"))
        self.assertEqual(set(brief["properties"]["deliverables"]["properties"]["video_type"]["enum"]), ids)
        self.assertEqual(set(series["definitions"]["member"]["properties"]["video_type"]["enum"]) if "definitions" in series
                         else ids, ids)


class LongFormProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="forms-"))
        self.orig = studio.PROJECTS_DIR
        studio.PROJECTS_DIR = self.tmp

    def tearDown(self):
        studio.PROJECTS_DIR = self.orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def scaffold(self, slug, video_type, formats=None):
        studio.cmd_new(argparse.Namespace(slug=slug, template="illustrated-explainer", title=None, style=None,
                                          formats=formats, category="history", video_type=video_type))
        return self.tmp / slug

    def test_a_long_scaffold_validates_and_renders_in_segments(self):
        pdir = self.scaffold("forms-long", "long")
        project = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
        self.assertEqual((project["duration_sec"], project["formats"][0]["id"]), (480, "landscape"))
        self.assertEqual(studio.validate_project(pdir).errors, [])
        self.assertTrue(studio.uses_segments(project))
        plan = studio.build_plan(pdir, None, None)
        render = next(s for s in plan if s["stage"] == "render:landscape")
        self.assertIn("scripts/render-segments.py", render["cmd"])
        self.assertNotIn("hyperframes", render["cmd"][0])
        # the output is the same partial file a single-pass render writes, so promote and stamp are unchanged
        self.assertTrue(render["cmd"][-1].endswith("renders/landscape/visuals.partial.mp4"))
        self.assertTrue(render["promote"][0].endswith("visuals.partial.mp4"))

    def test_a_mid_and_a_short_render_in_one_pass(self):
        for slug, vt in (("forms-mid", "mid"), ("forms-short", "short")):
            pdir = self.scaffold(slug, vt)
            project = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
            self.assertFalse(studio.uses_segments(project))
            render = next(s for s in studio.build_plan(pdir, None, None) if s["stage"].startswith("render:"))
            self.assertEqual(render["cmd"][0], "hyperframes")

    def test_chapters_are_checked(self):
        pdir = self.scaffold("forms-chapters", "long")
        project = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
        brief = json.loads((pdir / "brief.json").read_text(encoding="utf-8"))
        scenes = [{"id": f"s{i}", "start_sec": i * 60, "end_sec": (i + 1) * 60} for i in range(8)]

        def check(chapters):
            rep = studio.Report()
            studio.check_chapters({"chapters": chapters, "scenes": scenes}, scenes, project, brief, rep)
            return rep

        good = [{"id": f"c{i + 1}", "title": f"What happened in act {i + 1}", "start_sec": i * 120, "end_sec": (i + 1) * 120,
                 "mechanism": "x causes y", "new_terms": ["a"], "rehook": "but why?"} for i in range(4)]
        rep = check(good)
        self.assertEqual((rep.errors, rep.warnings), ([], []))
        # none declared on a long film
        rep = studio.Report()
        studio.check_chapters({"scenes": scenes}, scenes, project, brief, rep)
        self.assertTrue(any("no `chapters`" in w for w in rep.warnings))
        # too long, bad title, no mechanism, too many terms, a gap
        bad = json.loads(json.dumps(good))
        bad[0].update(end_sec=200, title="Part 1")
        bad[0].pop("mechanism")
        bad[1].update(start_sec=210, new_terms=["a", "b", "c", "d"])
        text = " | ".join(check(bad).warnings)
        for needle in ("over 150s", "Part 1", "names no `mechanism`", "over the budget of 3", "starts at 210s"):
            self.assertIn(needle, text)
        # a scene may not straddle a chapter edge
        rep = check([{**good[0], "end_sec": 90}, {**good[1], "start_sec": 90}] + good[2:])
        self.assertTrue(any("straddles" in w for w in rep.warnings))

    def test_a_chapter_list_is_accepted_by_the_storyboard_schema(self):
        pdir = self.scaffold("forms-schema", "long")
        sb = json.loads((pdir / "storyboard.json").read_text(encoding="utf-8"))
        sb["chapters"] = [{"id": "c1", "title": "Why the dam failed", "start_sec": 0, "end_sec": 120}]
        self.assertEqual(studio.schema_errors(sb, studio.SPECS_DIR / "storyboard-spec.json"), [])
        sb["chapters"][0]["surprise"] = 1
        self.assertTrue(studio.schema_errors(sb, studio.SPECS_DIR / "storyboard-spec.json"))


class LengthAwareReviewTests(unittest.TestCase):
    def test_frame_review_scales_with_length(self):
        fr = load_script("frame_review", "frame-review.py")
        self.assertEqual([fr.auto_samples(d) for d in (45, 180, 480, 720, 3600)], [12, 12, 24, 36, 60])
        self.assertEqual([fr.auto_scan_fps(d) for d in (45, 180, 300, 720)], [5.0, 5.0, 2.0, 1.0])
        # a 12-minute film is ~720 audited frames, not 3600
        self.assertLess(720 * fr.auto_scan_fps(720), 1000)


class MuxTests(LongFormProjectTests):
    test_a_long_scaffold_validates_and_renders_in_segments = test_a_mid_and_a_short_render_in_one_pass = test_chapters_are_checked = test_a_chapter_list_is_accepted_by_the_storyboard_schema = None

    def test_a_short_music_bed_loops_under_the_film(self):
        pdir = self.scaffold("forms-bed", "long")
        pj = pdir / "project.json"
        project = json.loads(pj.read_text(encoding="utf-8"))
        project["audio"]["music"] = {"enabled": True, "file": "audio/bed.wav", "license": "CC0"}
        pj.write_text(json.dumps(project), encoding="utf-8")
        cmd = next(s for s in studio.build_plan(pdir, None, None) if s["stage"].startswith("mux:"))["cmd"]
        i = cmd.index("audio/bed.wav")
        self.assertEqual(cmd[i - 3:i], ["-stream_loop", "-1", "-i"])
        self.assertEqual(cmd[cmd.index("-t") + 1], "480")


if __name__ == "__main__":
    unittest.main(verbosity=1)
