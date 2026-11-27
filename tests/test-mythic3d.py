#!/usr/bin/env python3
"""
tests/test-mythic3d.py
The 3D mythic figures (src/blender/mythic3d, scripts/mythic3d.py). Pure Python: option parsing and the
review-sheet layout. With Blender installed (skipped otherwise, or with MOTION_LAB_SKIP_BLENDER=1), every
figure is built without rendering under the host render lock and checked against its identity block
(.claude/skills/mythic-tales/references/figure-design.md section 4): each attribute in the right hand,
the given eye, the mount and the marks; nothing below the floor; and two builds give identical geometry.

    python tests/test-mythic3d.py
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
spec = importlib.util.spec_from_file_location("mythic3d_cli", REPO_ROOT / "scripts" / "mythic3d.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class CliTests(unittest.TestCase):
    def test_options_parse_per_figure(self):
        self.assertEqual(cli.parse_opts(["rama:tone=brown;attire=royal", "hanuman:form=dasa"]),
                         {"rama": {"tone": "brown", "attire": "royal"}, "hanuman": {"form": "dasa"}})

    def test_sheets_lay_out_turnarounds_and_the_gallery(self):
        from PIL import Image
        work = Path(tempfile.mkdtemp(prefix="m3d-sheets-"))
        try:
            for v in cli.TURN + ["hero"]:
                Image.new("RGB", (60, 80), (200, 180, 160)).save(work / f"rama-painted-{v}.png")
            Image.new("RGB", (60, 80)).save(work / "shiva-painted-hero.png")
            cli.sheets(argparse.Namespace(out=str(work)))
            turn = Image.open(work / "turnaround-rama-painted.png")
            self.assertEqual(turn.size, (60 * len(cli.TURN), 80 + 70))
            self.assertFalse((work / "turnaround-shiva-painted.png").exists(), "a figure without all five views gets no turnaround")
            self.assertTrue((work / "gallery-painted.png").exists())
            self.assertFalse((work / "gallery-bronze.png").exists())
        finally:
            shutil.rmtree(work, ignore_errors=True)


BLENDER = None if os.environ.get("MOTION_LAB_SKIP_BLENDER") else cli.find_blender()


def _key(name):
    return re.sub(r"\.\d{3}$", "", name)


@unittest.skipIf(BLENDER is None, "Blender not installed (or MOTION_LAB_SKIP_BLENDER set)")
class FigureBuildTests(unittest.TestCase):
    """Build every figure once (and Rama twice) without rendering, then check the reports."""

    @classmethod
    def setUpClass(cls):
        from pipeline.hostlock import heavy_lock
        cls.work = Path(tempfile.mkdtemp(prefix="m3d-check-"))
        cls.reports = {}
        jobs = [(f, f) for f in cli.FIGURES] + [("rama", "rama-again")]
        with heavy_lock("render", slug="test-mythic3d"):
            for fid, tag in jobs:
                out = cls.work / tag
                out.mkdir()
                job = {"figure": fid, "look": "painted", "out_dir": str(out), "views": [], "check": True, "width": 64, "height": 64}
                jp = out / "job.json"
                jp.write_text(json.dumps(job), encoding="utf-8")
                log = out / "blender.log"
                with open(log, "w", encoding="utf-8") as fh:
                    rc = subprocess.run([str(BLENDER), "-b", "--factory-startup", "--python-exit-code", "1", "--python",
                                         str(cli.KIT / "run.py"), "--", "--job", str(jp)], stdout=fh, stderr=subprocess.STDOUT,
                                        stdin=subprocess.DEVNULL).returncode
                rep = out / f"{fid}-painted-check.json"
                cls.reports[tag] = (rc, json.loads(rep.read_text(encoding="utf-8")) if rep.exists() else None,
                                    log.read_text(encoding="utf-8", errors="replace")[-3000:])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def report(self, tag):
        rc, rep, log = self.reports[tag]
        self.assertEqual(rc, 0, log)
        self.assertIsNotNone(rep, log)
        return rep

    def objs(self, tag):
        out = {}
        for name, o in self.report(tag)["objects"].items():
            out.setdefault(_key(name), []).append(o)
        return out

    def cx(self, tag, key):
        o = self.objs(tag)[key][0]
        return (o["min"][0] + o["max"][0]) / 2

    def test_every_figure_builds_with_a_skin_on_the_turntable_and_nothing_below_the_floor(self):
        for fid in cli.FIGURES:
            with self.subTest(figure=fid):
                rep = self.report(fid)
                self.assertTrue(any(k.endswith("-skin") for k in rep["objects"]), list(rep["objects"])[:8])
                low = {k: o["min"][2] for k, o in rep["objects"].items() if o["min"][2] < -0.005}
                self.assertEqual(low, {}, "below the floor")
                self.assertTrue(all(o["on_turntable"] for k, o in rep["objects"].items() if not k.startswith("glow")))

    def test_attributes_are_in_the_hands_the_identity_blocks_give(self):
        # The figure's right is -X (it faces -Y), its left +X.
        self.assertGreater(self.cx("rama", "kodanda"), 0.15)          # bow in the left hand
        self.assertLess(self.cx("rama", "shara"), -0.1)               # arrow in the right
        self.assertLess(self.cx("hanuman", "gada"), 0.0)              # gada on the right shoulder
        self.assertGreater(self.objs("hanuman")["puchha"][0]["max"][0], 0.3)   # the tail rises on his left
        self.assertGreater(self.cx("shiva", "trishula"), 0.15)        # trident in the left hand
        self.assertGreater(self.cx("shiva", "chandra"), 0.0)          # the crescent on his left
        self.assertLess(self.cx("shiva", "makara-kundala"), 0.0)
        self.assertGreater(self.cx("shiva", "patra-kundala"), 0.0)
        self.assertLess(self.cx("ganesha", "ankusha"), -0.15)         # goad upper right
        self.assertGreater(self.cx("ganesha", "pasha"), 0.15)         # noose upper left
        self.assertLess(self.cx("ganesha", "tusk-held"), 0.0)         # the broken tusk in the lower right
        self.assertGreater(self.cx("athena", "aspis"), 0.1)           # shield on the left arm
        self.assertLess(self.cx("odin", "gungnir"), 0.0)              # Gungnir in the right hand
        self.assertLess(self.cx("odin", "huginn"), 0.0)               # Huginn on the right shoulder
        self.assertGreater(self.cx("odin", "muninn"), 0.0)            # Muninn flies to the left hand

    def test_marks_mounts_and_haloes(self):
        g = self.objs("ganesha")
        tr, tl = g["tusk-r"][0], g["tusk-l"][0]
        span = lambda o: sum((o["max"][i] - o["min"][i]) ** 2 for i in range(3)) ** 0.5  # noqa: E731
        self.assertLess(span(tr), span(tl), "the right tusk is the broken one")
        self.assertIn("mouse", g)
        odin = self.objs("odin")
        self.assertIn("eye-l", odin)
        self.assertNotIn("eye-r", odin, "the eye given at Mimir's well is closed")
        athena = set(self.objs("athena"))
        self.assertFalse({k for k in athena if "ring" in k or k.startswith("halo") or "prabha" in k}, "Greek gods have no halo")
        jina, buddha = self.objs("tirthankara"), self.objs("buddha")
        self.assertIn("lion", jina)
        self.assertIn("chhatra", jina)
        top = lambda tag, objs: objs["curls"][0]["max"][2] - self.report(tag)["head"][2]  # noqa: E731
        self.assertGreater(top("buddha", buddha), top("tirthankara", jina) + 0.015, "the ushnisha is the Buddha's, never a Jina's")

    def test_two_builds_are_identical(self):
        self.assertEqual(self.report("rama")["digest"], self.report("rama-again")["digest"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
