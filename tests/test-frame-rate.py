#!/usr/bin/env python3
"""
tests/test-frame-rate.py
Frame-rate lifting (src/pipeline/framerate.py, scripts/frame-rate.py): rate maths, cut / hold / stepped detection,
the per-pair method choice, the stitcher, the authored-motion audit and, when FFmpeg is present, an end-to-end
ground-truth test: a synthetic 60 fps scene is decimated to 30 fps, lifted back, and its invented frames are
compared with the real ones. The end-to-end test uses a private lock directory, never the host lock.

    python tests/test-frame-rate.py
"""
import argparse
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "pipeline"))
import framerate as fr  # noqa: E402

CLI = REPO_ROOT / "scripts" / "frame-rate.py"
HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def load_cli():
    spec = importlib.util.spec_from_file_location("frame_rate_cli", CLI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def metrics_for(d, loo=None):
    """A metrics dict for plan_pairs: pair diffs d (N-1), correlation 0.95, and per-frame leave-one-out errors."""
    d = np.array(d, dtype=float)
    n = len(d) + 1
    m = {"d": d, "corr": np.full(len(d), 0.95)}
    for k in ("copy_mean", "copy_p98", "blend_mean", "blend_p98", "mci_mean", "mci_p98"):
        m[k] = np.full(n, math.nan)
    for j in range(1, n - 1):
        for k, v in (loo or {}).items():
            m[k][j] = v(j) if callable(v) else v
    return m


class RateTests(unittest.TestCase):
    def test_ntsc_rates_stay_exact(self):
        self.assertEqual(fr.parse_rate("30000/1001"), Fraction(30000, 1001))
        self.assertEqual(fr.parse_rate(29.97), Fraction(30000, 1001))
        self.assertEqual(fr.parse_rate("59.94"), Fraction(60000, 1001))
        self.assertEqual(fr.parse_rate("30"), 30)
        self.assertEqual(fr.target_rate(Fraction(30000, 1001), "60"), Fraction(60000, 1001))
        self.assertEqual(fr.target_rate(Fraction(30000, 1001), "60", exact=True), 60)
        self.assertEqual(fr.target_rate(Fraction(30), "120"), 120)

    def test_output_frames_cover_the_same_duration(self):
        self.assertEqual(fr.output_frame_count(120, Fraction(30), Fraction(60)), 240)
        self.assertEqual(fr.output_frame_count(120, Fraction(24), Fraction(60)), 300)
        self.assertEqual(fr.output_frame_count(90, Fraction(30), Fraction(120)), 360)

    def test_phases_for_whole_and_fractional_ratios(self):
        self.assertEqual([fr.source_position(k, Fraction(30), Fraction(60)) for k in range(4)],
                         [(0, 0), (0, Fraction(1, 2)), (1, 0), (1, Fraction(1, 2))])
        phases = [fr.source_position(k, Fraction(24), Fraction(60))[1] for k in range(5)]
        self.assertEqual(phases, [0, Fraction(2, 5), Fraction(4, 5), Fraction(1, 5), Fraction(3, 5)])
        self.assertEqual(fr.source_position(4, Fraction(30), Fraction(120)), (1, 0))


class DetectionTests(unittest.TestCase):
    def test_isolated_change_is_a_cut_and_a_fast_push_is_not(self):
        d = np.array([0.5] * 10 + [20.0] + [0.5] * 10 + [9, 10, 11, 10, 9] + [0.5] * 5)
        corr = np.full(len(d), 0.95)
        corr[10] = 0.1
        corr[21:26] = 0.7
        cut = fr.detect_cuts(d, corr)
        self.assertEqual(list(np.where(cut)[0]), [10])

    def test_a_flash_frame_is_two_cuts(self):
        d = np.array([0.4] * 8 + [30.0, 28.0] + [0.4] * 8)
        corr = np.full(len(d), 0.95)
        corr[8:10] = 0.05
        self.assertEqual(list(np.where(fr.detect_cuts(d, corr))[0]), [8, 9])

    def test_on_twos_is_stepped_but_staccato_and_drift_are_not(self):
        twos = np.array([0.0, 3.0] * 20)
        self.assertTrue(fr.detect_stepped(twos, np.zeros(len(twos), bool), 30).sum() > 30)
        staccato = np.array(([0.0] * 6 + [4.0] * 4) * 4)
        self.assertEqual(fr.detect_stepped(staccato, np.zeros(len(staccato), bool), 30).sum(), 0)
        drift = np.full(40, 0.1)
        self.assertEqual(fr.detect_stepped(drift, np.zeros(40, bool), 30).sum(), 0)


class PlanTests(unittest.TestCase):
    def plan(self, d, loo, use_mci=True, force=None):
        return fr.plan_pairs(metrics_for(d, loo), 30.0, use_mci=use_mci, force=force)

    def test_mci_wins_only_by_a_clear_margin(self):
        base = {"copy_mean": 3.0, "copy_p98": 9.0, "blend_mean": 1.0, "blend_p98": 4.0, "mci_p98": 3.0}
        clear = self.plan([2.0] * 12, dict(base, mci_mean=0.3))
        self.assertEqual(set(clear["methods"][2:-2]), {"m"})
        close = self.plan([2.0] * 12, dict(base, mci_mean=0.95, mci_p98=3.9))
        self.assertEqual(set(close["methods"][2:-2]), {"b"})
        no_probe = self.plan([2.0] * 12, dict(base, mci_mean=0.3), use_mci=False)
        self.assertNotIn("m", no_probe["methods"])

    def test_slow_drift_is_blended_not_held(self):
        p = self.plan([0.08] * 12, {"copy_mean": 0.08, "copy_p98": 0.2, "blend_mean": 0.03, "blend_p98": 0.1, "mci_mean": 0.03, "mci_p98": 0.1})
        self.assertNotIn("h", p["labels"])
        self.assertEqual(set(p["methods"]), {"b"})

    def test_holds_cuts_and_dissolves(self):
        d = [0.0] * 6 + [4.0] * 8
        p = self.plan(d, {"copy_mean": 4.0, "copy_p98": 6.0, "blend_mean": 0.2, "blend_p98": 0.5, "mci_mean": 0.6, "mci_p98": 1.0})
        self.assertEqual(p["labels"][:6], "hhhhhh")
        self.assertEqual(p["methods"][:6], "cccccc")
        self.assertIn("d", p["labels"][7:])
        # a dissolve is blended even when the probe scores MCI a little lower: there is no motion to compensate
        p = self.plan([4.0] * 12, {"copy_mean": 4.0, "copy_p98": 6.0, "blend_mean": 0.5, "blend_p98": 1.0, "mci_mean": 0.2, "mci_p98": 0.5})
        self.assertEqual(set(p["labels"][1:-1]), {"d"})
        self.assertEqual(set(p["methods"]), {"b"})
        m = metrics_for([0.5] * 5 + [25.0] + [0.5] * 5, {"copy_mean": 0.5, "copy_p98": 1, "blend_mean": 0.3, "blend_p98": 0.8,
                                                          "mci_mean": 0.3, "mci_p98": 0.8})
        m["corr"][5] = 0.1
        p = fr.plan_pairs(m, 30.0, use_mci=True, force="blend")
        self.assertEqual((p["labels"][5], p["methods"][5]), ("x", "c"))

    def test_copy_wins_when_repetition_predicts_best(self):
        p = self.plan([2.0] * 12, {"copy_mean": 0.1, "copy_p98": 0.3, "blend_mean": 1.0, "blend_p98": 3.0, "mci_mean": 0.9, "mci_p98": 3.0})
        self.assertEqual(set(p["methods"][2:-2]), {"c"})

    def test_segments_and_summary_account_for_every_output_frame(self):
        segs = fr.segments("bbcc", "vvhx", Fraction(30))
        self.assertEqual([(s["label"], s["method"], s["pairs"]) for s in segs], [("motion", "blend", 2), ("hold", "copy", 1), ("cut", "copy", 1)])
        s = fr.summarise("bbcc", "vvhx", 5, Fraction(30), Fraction(60), {"d": np.array([1, 1, 0, 9.0])})
        self.assertEqual(s["output_frames"], 10)
        self.assertEqual(s["output_frames_by_method"], {"source": 5, "copy": 3, "blend": 2, "mci": 0})


class AnalyzerTests(unittest.TestCase):
    def test_leave_one_out_errors_follow_the_motion(self):
        ana = fr.Analyzer()
        for j in range(8):
            f = np.zeros((18, 32), np.float32)
            if j >= 4:
                f[:, (j - 4) * 4:(j - 4) * 4 + 4] = 200.0  # a bar moving 4 px per frame from frame 4 on
            ana.push(f, f if j % 2 else None)
        m = ana.finish()
        self.assertEqual((len(m["d"]), len(m["blend_mean"])), (7, 8))
        self.assertEqual(m["blend_mean"][2], 0.0)
        self.assertGreater(m["blend_mean"][5], 0.0)
        self.assertEqual(m["mci_mean"][5], 0.0)
        self.assertTrue(math.isnan(m["mci_mean"][4]))
        self.assertTrue(math.isnan(m["blend_mean"][0]) and math.isnan(m["blend_mean"][7]))


class StitchTests(unittest.TestCase):
    def frames(self, values):
        return iter([np.full(6, v, np.uint8) for v in values])

    def test_every_output_frame_follows_the_plan(self):
        out = []
        counts = fr.stitch(4, Fraction(30), Fraction(60), "bcm", self.frames([0, 100, 200, 250]),
                           self.frames([0, 9, 9, 9, 9, 77, 9]), out.append)
        self.assertEqual([int(f[0]) for f in out], [0, 50, 100, 100, 200, 77, 250, 250])
        self.assertEqual(counts, {"source": 4, "copy": 2, "blend": 1, "mci": 1, "mci_fallback": 0})

    def test_a_short_mci_stream_falls_back_to_blend(self):
        out = []
        counts = fr.stitch(3, Fraction(30), Fraction(60), "mm", self.frames([0, 100, 200]), self.frames([0, 40]), out.append)
        self.assertEqual([int(f[0]) for f in out], [0, 40, 100, 150, 200, 200])
        self.assertEqual(counts["mci_fallback"], 1)

    def test_plan_and_film_must_agree(self):
        with self.assertRaises(ValueError):
            fr.stitch(4, Fraction(30), Fraction(60), "bb", self.frames([0] * 4), None, lambda f: None)

    def test_blend_is_exact_at_the_phase(self):
        a, b = np.full(4, 0, np.uint8), np.full(4, 200, np.uint8)
        self.assertEqual(int(fr.blend_frames(a, b, Fraction(1, 2))[0]), 100)
        self.assertEqual(int(fr.blend_frames(a, b, Fraction(1, 4))[0]), 50)
        self.assertIs(fr.blend_frames(a, b, Fraction(0)), a)


class AuthoredMotionTests(unittest.TestCase):
    def test_ease_slopes(self):
        self.assertAlmostEqual(fr.peak_slope("none"), 1.0, places=2)
        self.assertAlmostEqual(fr.peak_slope("power2.out"), 3.0, places=1)
        self.assertAlmostEqual(fr.peak_slope("power1.inOut"), 2.0, places=1)
        self.assertAlmostEqual(fr.peak_slope("sine.inOut"), math.pi / 2, places=2)
        self.assertIsNone(fr.peak_slope("steps(5)"))
        for name in ("power3.out", "expo.inOut", "circ.in", "back.out(1.7)", "bounce.out", "elastic.out(1, 0.3)", "sine"):
            f = fr.ease_fn(name)
            self.assertAlmostEqual(f(0.0), 0.0, places=3, msg=name)
            self.assertAlmostEqual(f(1.0), 1.0, places=3, msg=name)

    def test_audit_flags_fast_moves_and_short_linear_moves_only(self):
        dump = {"size": [1280, 720], "tweens": [
            {"t0": 1.0, "dur": 0.3, "kind": "fromTo", "ease": "power3.out", "props": {"x": 600}, "from": {"x": 0}, "label": "#card"},
            {"t0": 2.0, "dur": 6.0, "kind": "to", "ease": "sine.inOut", "props": {"x": "+=20"}, "from": {}, "label": "#bg"},
            {"t0": 3.0, "dur": 0.5, "kind": "to", "ease": "none", "props": {"y": 80}, "from": {"y": 0}, "label": "#tag"},
            {"t0": 4.0, "dur": 0.4, "kind": "from", "ease": "power2.out", "props": {"opacity": 0, "y": 20}, "from": {}, "label": "#title"},
        ]}
        rep = fr.audit_tweens(dump, 30, 60)
        kinds = {(f["kind"], f["label"]) for f in rep["findings"]}
        self.assertIn(("strobe", "#card"), kinds)
        self.assertIn(("velocity-jump", "#tag"), kinds)
        self.assertFalse(any(f["label"] == "#bg" for f in rep["findings"]))
        card = next(r for r in rep["fastest"] if r["label"] == "#card")
        self.assertAlmostEqual(card["peak_per_frame_dst"], 4 * 600 / 0.3 / 60, delta=0.5)
        self.assertAlmostEqual(card["peak_per_frame_src"], 2 * card["peak_per_frame_dst"], places=1)
        title = [r for r in rep["fastest"] if r["label"] == "#title"]
        self.assertTrue(all(r["assumed_start"] for r in title))

    def test_scan_finds_video_layers_stepped_motion_and_blur(self):
        html = ('<div id="root" data-fps="30" data-motion-blur="on" data-motion-blur-shutter="180">'
                '<video class="plate" src="plates/s1.portrait.mp4"></video></div>'
                "<script>tl.to(a, {x: 4, ease: 'steps(4)'}); const f = Studio.format.fps;</script>")
        s = fr.scan_composition(html)
        self.assertEqual(s["videos"], ["plates/s1.portrait.mp4"])
        self.assertEqual(s["motion_blur"], {"value": "on", "shutter": "180"})
        self.assertEqual(len(s["stepped"]), 1)
        self.assertEqual(len(s["fps_refs"]), 1)

    def test_audit_command_on_a_scratch_project(self):
        cli = load_cli()
        with tempfile.TemporaryDirectory() as tmp:
            pdir = Path(tmp) / "demo"
            (pdir / "src").mkdir(parents=True)
            (pdir / "qa" / "motion").mkdir(parents=True)
            (pdir / "project.json").write_text(json.dumps({"slug": "demo", "fps": 30, "duration_sec": 10,
                                                           "formats": [{"id": "landscape", "width": 1280, "height": 720, "primary": True}]}))
            (pdir / "src" / "index.html").write_text('<div id="root" data-fps="30"></div><script>tl.to(a,{x:3,ease:"steps(3)"})</script>')
            (pdir / "qa" / "motion" / "tweens.json").write_text(json.dumps({"size": [1280, 720], "tweens": [
                {"t0": 1.0, "dur": 0.25, "kind": "fromTo", "ease": "expo.out", "props": {"x": 900}, "from": {"x": 0}, "label": "#hero"}]}))
            cli.PROJECTS = Path(tmp)
            rc = cli.cmd_audit(argparse.Namespace(slug="demo", fps="60", apply=False))
            report = json.loads((pdir / "qa" / "frame-rate" / "audit-60fps.json").read_text())
            ids = {f["id"].split("-")[0] for f in report["findings"]}
            self.assertEqual(rc, 0)
            self.assertTrue({"motion", "stepped", "strobe", "cost"} <= ids, ids)
            rc = cli.cmd_audit(argparse.Namespace(slug="demo", fps="120", apply=False))
            self.assertEqual(rc, 1)


@unittest.skipUnless(HAVE_FFMPEG, "needs ffmpeg and ffprobe")
class EndToEndTests(unittest.TestCase):
    """A hold, a textured slide, a cut, a hold, a 1 s dissolve and a hold, made at 60 fps; the 30 fps copy is lifted back."""

    W, H = 192, 108

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="test-frame-rate-"))
        g = (f"color=c=0x203040:s={cls.W}x{cls.H}:r=60:d=2[bg];smptebars=s=64x36:r=60:d=2[bar];"
             "[bg][bar]overlay=x='if(lt(t,1),12,12+(t-1)*90)':y=36,format=yuv420p,settb=AVTB[A];"
             f"smptehdbars=s={cls.W}x{cls.H}:r=60:d=1.5,format=yuv420p,settb=AVTB[B];"
             f"color=c=0xF4EFE6:s={cls.W}x{cls.H}:r=60:d=1.5,drawgrid=w=24:h=24:t=2:c=0x1D4ED8,format=yuv420p,settb=AVTB[C];"
             "[B][C]xfade=transition=fade:duration=1:offset=0.5[BC];[A][BC]concat=n=2:v=1:a=0[v]")
        cls.truth, cls.src = cls.tmp / "truth60.mp4", cls.tmp / "src30.mp4"
        run = lambda c: subprocess.run(c, check=True, capture_output=True, stdin=subprocess.DEVNULL)  # noqa: E731
        run(["ffmpeg", "-v", "error", "-y", "-filter_complex", g, "-map", "[v]", "-c:v", "libx264", "-crf", "4", "-pix_fmt", "yuv420p", str(cls.truth)])
        run(["ffmpeg", "-v", "error", "-y", "-i", str(cls.truth), "-f", "lavfi", "-i", "sine=f=440:d=4", "-vf", "select='not(mod(n,2))',setpts=N/30/TB",
             "-r", "30", "-c:v", "libx264", "-crf", "8", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(cls.src)])
        env = dict(os.environ, MOTION_LAB_LOCK_DIR=str(cls.tmp / "locks"))
        cls.results = {}
        for method in ("auto", "copy"):
            out = cls.tmp / f"{method}60.mp4"
            r = subprocess.run([sys.executable, str(CLI), "convert", str(cls.src), "--fps", "60", "--method", method, "--out", str(out)],
                               capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
            cls.results[method] = (r, out, out.with_name(out.stem + ".fps-plan.json"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def luma(self, path):
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-an", "-vf", "format=gray", "-fps_mode", "passthrough", "-f", "rawvideo", "-"],
                           capture_output=True, stdin=subprocess.DEVNULL)
        a = np.frombuffer(r.stdout, np.uint8)
        return a.reshape(-1, self.H, self.W).astype(np.float32)

    def test_conversion_succeeds_and_keeps_duration_and_audio(self):
        r, out, plan_path = self.results["auto"]
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        plan = json.loads(plan_path.read_text())
        self.assertEqual((plan["source"]["frames"], plan["target"]["frames"]), (120, 240))
        v = plan["convert"]["verify"]
        self.assertTrue(v["ok"], v)
        self.assertEqual(v["frames"], 240)
        self.assertGreater(v["distinct_gain"], 1.8)

    def test_the_plan_reads_the_scene(self):
        plan = json.loads(self.results["auto"][2].read_text())
        labels, methods = plan["pairs"]["labels"], plan["pairs"]["methods"]
        self.assertEqual(labels.count("x"), 1)
        self.assertEqual(labels.index("x"), 59)              # the cut between source frames 59 and 60
        self.assertGreaterEqual(labels[:29].count("h"), 25)  # the opening hold
        self.assertIn("m", methods[31:58])                   # the textured slide is motion-compensated
        self.assertTrue(set(methods[78:102]) <= {"b"})       # the dissolve is blended

    def test_invented_frames_are_closer_to_the_truth_than_doubling(self):
        truth = self.luma(self.truth)
        auto, copy = self.luma(self.results["auto"][1]), self.luma(self.results["copy"][1])

        def err(f, a, b):
            return float(np.mean([np.abs(f[k] - truth[k]).mean() for k in range(a, b) if k % 2]))

        for name, (a, b) in {"slide": (62, 118), "dissolve": (152, 208)}.items():
            with self.subTest(region=name):
                self.assertLess(err(auto, a, b), 0.5 * err(copy, a, b))
        self.assertLess(err(auto, 1, 58), 0.1)               # the hold stays exact


if __name__ == "__main__":
    unittest.main(verbosity=2)
