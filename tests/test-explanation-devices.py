#!/usr/bin/env python3
"""Explanation devices: the device table (specs/explanation-devices.json) and the storyboard checks that
`studio.py validate` runs (src/pipeline/devices.py). Pure Python; no browser.

    python tests/test-explanation-devices.py
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "pipeline"))

import devices as dv  # noqa: E402

SPEC = dv.load_spec()
RUNTIME = "\n".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "src" / "studio").glob("studio-*.js")))


def scene(sid, start, job=None, did=None, narration="Words.", caps=None, out=None):
    s = {"id": sid, "title": sid, "start_sec": start, "end_sec": start + 5, "purpose": "p", "visual": "v",
         "capabilities": caps or [], "transition_out": {"type": "cut", **({"capability": out} if out else {})},
         "narration": narration}
    if job:
        s["device"] = {"job": job, "id": did}
    return s


def levels(findings, level):
    return [m for lv, m in findings if lv == level]


class SpecIntegrity(unittest.TestCase):
    def test_every_device_points_at_real_things(self):
        jobs = set(SPEC["jobs"])
        for d in SPEC["devices"]:
            with self.subTest(device=d["id"]):
                self.assertTrue((ROOT / "catalogue" / "data" / "references" / f"{d['technique']}.json").exists(), d["technique"])
                self.assertTrue((ROOT / d["golden"]).exists(), d["golden"])
                self.assertTrue(set(d["jobs"]) <= jobs, d["jobs"])
                last = d["api"].split(".")[-1]
                self.assertRegex(RUNTIME, r"\b(?:C|T|FX|SP|Studio|Studio\.comp)\." + re.escape(last) + r"\s*=", d["api"])

    def test_handbook_covers_every_job_device_and_cap(self):
        doc = (ROOT / "docs" / "explanation-devices.md").read_text(encoding="utf-8")
        for job in SPEC["jobs"]:
            self.assertIn(f"`{job}`", doc, job)
        for d in SPEC["devices"]:
            self.assertIn(f"`{d['id']}`", doc, d["id"])
        # the "Caps per film" list must say exactly what the spec enforces
        caps = {}
        for ids, n in re.findall(r"^\s+- ((?:`[a-z-]+`(?:, )?)+): (\d+)", doc, flags=re.M):
            for i in re.findall(r"`([a-z-]+)`", ids):
                caps[i] = int(n)
        self.assertEqual(caps, {d["id"]: d["max_per_film"] for d in SPEC["devices"]})

    def test_every_job_has_a_device(self):
        for job in SPEC["jobs"]:
            with self.subTest(job=job):
                self.assertTrue(dv.devices_for_job(SPEC, job), job)

    def test_golden_pages_call_the_devices_that_cite_them(self):
        for d in SPEC["devices"]:
            with self.subTest(device=d["id"]):
                html = (ROOT / d["golden"]).read_text(encoding="utf-8")
                self.assertRegex(html, dv.api_pattern(d["api"]), f"{d['golden']} never calls {d['api']}")

    def test_banned_techniques_and_capabilities_exist(self):
        ban = SPEC["not_under_narration"]
        for t in ban["techniques"]:
            self.assertTrue((ROOT / "catalogue" / "data" / "references" / f"{t}.json").exists(), t)
        caps = {p.stem for p in (ROOT / "catalogue" / "data").rglob("*.json") if "references" not in p.parts}
        for c in ban["capabilities"]:
            self.assertIn(c, caps)


class StoryboardChecks(unittest.TestCase):
    HTML = "var eq = C.equation('#eq', {terms: []}); S.space.tour(tl, '#c', []); C.ui.cursor('#l');"

    def test_good_choices_are_clean(self):
        sb = {"scenes": [scene("s1", 0, "build-up", "equation-build"), scene("s2", 5, "process-step", "canvas-tour"),
                         scene("s3", 10, "demo-interaction", "ui-demo")]}
        f = dv.check_storyboard_devices(sb, self.HTML, "short", SPEC)
        self.assertEqual([x for x in f if x[0] != "note"], [], f)

    def test_unknown_job_or_device_is_an_error(self):
        sb = {"scenes": [scene("s1", 0, "explain-stuff", "equation-build"), scene("s2", 5, "build-up", "wobble")]}
        errs = levels(dv.check_storyboard_devices(sb, self.HTML, "short", SPEC), "error")
        self.assertEqual(len(errs), 2, errs)
        self.assertIn("equation-build", errs[1])  # suggests the devices that do serve the job

    def test_device_for_the_wrong_job_warns_with_alternatives(self):
        sb = {"scenes": [scene("s1", 0, "rank-over-time", "equation-build")]}
        w = levels(dv.check_storyboard_devices(sb, self.HTML, "short", SPEC), "warn")
        self.assertTrue(any("bar-race" in m for m in w), w)

    def test_declared_but_never_called_warns(self):
        sb = {"scenes": [scene("s1", 0, "rank-over-time", "bar-race")]}
        w = levels(dv.check_storyboard_devices(sb, self.HTML, "short", SPEC), "warn")
        self.assertTrue(any("never calls Studio.comp.barRace" in m for m in w), w)
        self.assertFalse(levels(dv.check_storyboard_devices(sb, None, "short", SPEC), "warn"))  # no html yet: no claim

    def test_per_film_cap(self):
        sb = {"scenes": [scene("s1", 0, "rank-over-time", "bar-race"), scene("s2", 5, "rank-over-time", "bar-race")]}
        w = levels(dv.check_storyboard_devices(sb, "C.barRace(", "mid", SPEC), "warn")
        self.assertTrue(any("cap 1" in m for m in w), w)

    def test_flash_under_narration_warns_and_silence_is_fine(self):
        loud = {"scenes": [scene("s1", 0, out="flash-cut")]}
        quiet = {"scenes": [scene("s1", 0, out="flash-cut", narration="")]}
        self.assertTrue(levels(dv.check_storyboard_devices(loud, None, "short", SPEC), "warn"))
        self.assertFalse(levels(dv.check_storyboard_devices(quiet, None, "short", SPEC), "warn"))

    def test_too_many_distinct_devices_for_a_short(self):
        picks = [("hook-headline", "headline-pair"), ("build-up", "equation-build"), ("trace-cause", "slider"),
                 ("rank-over-time", "bar-race"), ("system-running", "simulation")]
        sb = {"scenes": [scene(f"s{i}", i * 5, j, d) for i, (j, d) in enumerate(picks)]}
        w = levels(dv.check_storyboard_devices(sb, None, "short", SPEC), "warn")
        self.assertTrue(any("5 distinct devices" in m for m in w), w)
        self.assertFalse(levels(dv.check_storyboard_devices(sb, None, "mid", SPEC), "warn"))

    def test_no_devices_is_only_a_note(self):
        f = dv.check_storyboard_devices({"scenes": [scene("s1", 0)]}, "", "short", SPEC)
        self.assertEqual([lv for lv, _ in f], ["note"])

    def test_storyboard_schema_accepts_the_device_field(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        schema = json.loads((ROOT / "specs" / "storyboard-spec.json").read_text(encoding="utf-8"))
        sub = dict(schema["definitions"]["scene"], definitions=schema["definitions"])
        s = scene("s1", 0, "build-up", "equation-build")
        s["device"]["why"] = "the figure shows each term"
        jsonschema.validate(s, sub)
        s["device"]["extra"] = 1
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(s, sub)


if __name__ == "__main__":
    unittest.main(verbosity=1)
