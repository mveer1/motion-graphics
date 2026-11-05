#!/usr/bin/env python3
"""
tests/test-style-templates.py
Style templates (catalogue/data/style-templates/): schema, cross-references, selection, the
refinement loop (version pinning) and the pre-render project check. Needs jsonschema.

    python tests/test-style-templates.py
"""

import copy
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

if sys.executable != "/opt/homebrew/bin/python3.12":
    py12 = shutil.which("python3.12") or "/opt/homebrew/bin/python3.12"
    if os.path.exists(py12):
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            os.execv(py12, [py12] + sys.argv)

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src" / "pipeline"))
mc = importlib.import_module("motion-catalogue")
st = importlib.import_module("style_templates")

STUDIO = ROOT / "scripts" / "studio.py"
SCHEMA = json.loads((ROOT / "catalogue" / "schemas" / "style-template.schema.json").read_text())
CATEGORIES = {c["id"] for c in json.loads((ROOT / "specs" / "categories.json").read_text())["categories"]}
RECORDS = mc.load_all_records()
TEMPLATES = RECORDS["style-templates"]


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def make_project(root: Path, template: dict, *, pinned: int, scenes: list, narration: dict = None) -> Path:
    pdir = root / "p"
    write(pdir / "project.json", {"slug": "p", "style": template["look"]["style"],
                                  "style_template": {"id": template["id"], "version": pinned}})
    write(pdir / "storyboard.json", {"scenes": scenes})
    if narration:
        write(pdir / "src" / "narration.json", {"scenes": [{"id": k, "text": v} for k, v in narration.items()]})
    return pdir


class TestRecords(unittest.TestCase):
    def test_there_are_templates(self):
        self.assertGreaterEqual(len(TEMPLATES), 7)

    def test_every_record_matches_the_schema(self):
        for tid, tpl in TEMPLATES.items():
            errs = [e.message for e in jsonschema.Draft7Validator(SCHEMA).iter_errors(tpl)]
            self.assertEqual(errs, [], tid)

    def test_every_record_passes_semantic_checks(self):
        for tid, tpl in TEMPLATES.items():
            errors, _ = st.check_template(tpl, RECORDS, CATEGORIES)
            self.assertEqual(errors, [], tid)

    def test_every_category_has_a_template(self):
        served = {c for t in TEMPLATES.values() for c in t["selection"]["categories"]}
        self.assertEqual(CATEGORIES - served, set(), "add a template or list the category on one")

    def test_visual_jobs_are_distinct(self):
        jobs = [t["visual_job"]["kind"] for t in TEMPLATES.values()]
        self.assertEqual(len(jobs), len(set(jobs)))

    def test_default_styles_are_light(self):
        for tid, tpl in TEMPLATES.items():
            self.assertEqual(RECORDS["styles"][tpl["look"]["style"]]["mode"], "light", tid)

    def test_catalogue_validate_passes(self):
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "motion-catalogue.py"), "validate"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)


class TestCheckTemplateCatchesMistakes(unittest.TestCase):
    def setUp(self):
        self.tpl = copy.deepcopy(TEMPLATES["news-brief"])

    def errors(self):
        return st.check_template(self.tpl, RECORDS, CATEGORIES)[0]

    def test_version_must_match_newest_revision(self):
        self.tpl["version"] += 1
        self.assertTrue(any("does not match its newest revision" in e for e in self.errors()))

    def test_dark_default_is_rejected(self):
        self.tpl["look"]["style"] = "cinematic-dark"
        self.assertTrue(any("is dark" in e for e in self.errors()))

    def test_unknown_capability_is_rejected(self):
        self.tpl["scene_grammar"][0]["capabilities"] = ["not-a-capability"]
        self.assertTrue(any("unregistered capability" in e for e in self.errors()))

    def test_unknown_category_is_rejected(self):
        self.tpl["selection"]["categories"].append("nope")
        self.assertTrue(any("unknown category" in e for e in self.errors()))

    def test_approved_needs_evidence(self):
        self.tpl["status"] = "approved"
        self.assertTrue(any("approved without validation evidence" in e for e in self.errors()))


class TestRecommend(unittest.TestCase):
    def top(self, cats, text=""):
        return st.recommend(RECORDS, cats, text)[0]["id"]

    def test_each_primary_category_picks_its_template(self):
        expect = {"mathematics": "proof-canvas", "finance": "data-ledger", "history": "chronicle",
                  "storytelling": "storybook", "science": "science-atlas", "technology": "systems-blueprint",
                  "news": "news-brief"}
        for cat, tid in expect.items():
            self.assertEqual(self.top([cat]), tid, cat)

    def test_keywords_can_outweigh_a_secondary_category(self):
        text = "breaking: officials confirmed the outage after the fire; the report says the shutdown continues"
        self.assertEqual(self.top(["technology", "news"], text), "news-brief")

    def test_reasons_are_reported(self):
        top = st.recommend(RECORDS, ["finance"], "inflation and interest rate")[0]
        self.assertIn("category finance (primary)", top["why"])
        self.assertTrue(any(w.startswith("keywords:") for w in top["why"]))

    def test_no_evidence_scores_zero(self):
        self.assertTrue(all(r["score"] == 0 for r in st.recommend(RECORDS, [], "")))


class TestProjectCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.tpl = copy.deepcopy(TEMPLATES["news-brief"])

    def scene(self, **kw):
        base = {"id": "s1", "start_sec": 0, "end_sec": 10, "capabilities": [],
                "beats": [{"at_sec": t, "action": "x"} for t in (0.5, 2, 4, 6, 8)]}
        base.update(kw)
        return base

    def check(self, pinned=None, scenes=None, narration=None):
        pinned = self.tpl["version"] if pinned is None else pinned   # default: built against the current version
        pdir = make_project(self.tmp, self.tpl, pinned=pinned, scenes=scenes or [self.scene()], narration=narration)
        return st.check_project(pdir, json.loads((pdir / "project.json").read_text()), None, self.tpl)

    def warns(self, findings):
        return [m for lv, m in findings if lv == "warn"]

    def test_a_conforming_project_has_no_warnings(self):
        self.assertEqual(self.warns(self.check()), [])

    def test_refining_the_template_flags_projects_built_on_the_old_version(self):
        old = self.tpl["version"]
        self.tpl["version"] = old + 1
        self.tpl["revisions"].append({"version": old + 1, "date": "2026-11-04", "change": "Tighter beat gap", "reason": "test"})
        warns = self.warns(self.check(pinned=old))
        self.assertTrue(any(f"built against news-brief v{old}" in w and "Tighter beat gap" in w for w in warns), warns)
        self.assertEqual(self.warns(self.check(pinned=old + 1)), [])

    def test_gap_between_beats_is_flagged(self):
        sc = self.scene(beats=[{"at_sec": 0.5, "action": "a"}, {"at_sec": 6, "action": "b"}])
        self.assertTrue(any("no planned visual event" in w for w in self.warns(self.check(scenes=[sc]))))

    def test_tail_after_the_last_beat_counts(self):
        sc = self.scene(end_sec=12)
        self.assertTrue(any("no planned visual event" in w for w in self.warns(self.check(scenes=[sc]))))

    def test_late_hook_is_flagged(self):
        sc = self.scene(beats=[{"at_sec": t, "action": "x"} for t in (2.5, 4, 6, 8)])
        self.assertTrue(any("hook" in w for w in self.warns(self.check(scenes=[sc]))))

    def test_long_scene_without_beats_is_flagged(self):
        sc = {"id": "s1", "start_sec": 0, "end_sec": 20, "capabilities": []}
        self.assertTrue(any("has no beats" in w for w in self.warns(self.check(scenes=[sc]))))

    def test_over_budget_narration_is_flagged(self):
        words = " ".join(["word"] * 40)   # 40 words in 10 s against a budget of 27
        self.assertTrue(any("words per 10 s" in w for w in self.warns(self.check(narration={"s1": words}))))
        self.assertEqual(self.warns(self.check(narration={"s1": " ".join(["word"] * 20)})), [])

    def test_measured_clip_duration_beats_storyboard_span(self):
        pdir = make_project(self.tmp, self.tpl, pinned=self.tpl["version"], scenes=[self.scene()],
                            narration={"s1": " ".join(["word"] * 30)})
        write(pdir / "audio" / "timeline.json", {"scenes": [{"id": "s1", "duration_sec": 5.0}]})
        findings = st.check_project(pdir, json.loads((pdir / "project.json").read_text()), None, self.tpl)
        self.assertTrue(any("measured clips" in m for _, m in findings))

    def test_discouraged_capability_is_flagged(self):
        sc = self.scene(capabilities=["squash-bounce"])
        self.assertTrue(any("discourages" in w for w in self.warns(self.check(scenes=[sc]))))

    def portrait_project(self, scenes):
        pdir = make_project(self.tmp, self.tpl, pinned=self.tpl["version"], scenes=scenes)
        project = json.loads((pdir / "project.json").read_text())
        project["formats"] = [{"id": "portrait", "primary": True}]
        return pdir, project

    def test_long_cards_are_flagged_for_portrait_first_projects(self):
        self.assertIn("short_form", self.tpl["rules"])
        limit = self.tpl["rules"]["short_form"]["max_card_words"]
        sc = self.scene(on_screen_text=["SHORT CARD", " ".join(["word"] * (limit + 3))])
        pdir, project = self.portrait_project([sc])
        warns = self.warns(st.check_project(pdir, project, None, self.tpl))
        self.assertTrue(any("1 of 2 on-screen text items" in w for w in warns), warns)

    def test_cards_within_the_limit_pass(self):
        sc = self.scene(on_screen_text=["SUN 11 OCT", "FRANCE"])
        pdir, project = self.portrait_project([sc])
        self.assertEqual(self.warns(st.check_project(pdir, project, None, self.tpl)), [])

    def test_card_limit_is_not_applied_to_landscape_first_projects(self):
        sc = self.scene(on_screen_text=[" ".join(["word"] * 12)])
        pdir, project = self.portrait_project([sc])
        project["formats"] = [{"id": "landscape", "primary": True}, {"id": "portrait"}]
        self.assertEqual(self.warns(st.check_project(pdir, project, None, self.tpl)), [])

    def test_scene_relative_beats_are_read_as_such(self):
        sc = self.scene(start_sec=20, end_sec=30, beats=[{"at_sec": t, "action": "x"} for t in (0.5, 2, 4, 6, 8)])
        times, gap, relative = st.beat_gaps(sc)
        self.assertTrue(relative)
        self.assertAlmostEqual(times[0], 20.5)
        self.assertAlmostEqual(gap, 2.0)

    def test_film_time_beats_are_not_shifted(self):
        sc = self.scene(start_sec=20, end_sec=30, beats=[{"at_sec": t, "action": "x"} for t in (20.5, 22, 24, 26, 28)])
        self.assertFalse(st.beat_gaps(sc)[2])


class TestCli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(STUDIO), *args], capture_output=True, text=True, cwd=ROOT)

    def test_list_show_recommend(self):
        out = self.run_cli("style", "list")
        self.assertEqual(out.returncode, 0, out.stderr)
        for tid in TEMPLATES:
            self.assertIn(tid, out.stdout)
        out = self.run_cli("style", "show", "data-ledger")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("Anti-patterns", out.stdout)
        out = self.run_cli("style", "recommend", "--category", "finance", "--text", "inflation and the interest rate")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("data-ledger", out.stdout.split("Top pick")[0])

    def test_unknown_template_is_an_error(self):
        self.assertNotEqual(self.run_cli("style", "show", "nope").returncode, 0)

    def test_portfolio_check_runs(self):
        out = self.run_cli("style", "check")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("project", out.stdout.splitlines()[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
