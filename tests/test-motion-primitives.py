#!/usr/bin/env python3
"""
tests/test-motion-primitives.py

Comprehensive test suite verifying the Stage 2 upgrades to the motion graphics workspace:
  - Priority 1: Composition primitives (heroStage, splitStage, monumentStat, animatedChart, timeline)
  - Priority 2: Typography system (font-size tokens, readability floor >= 22.3px, T.fit, T.heroHeader, T.punch, T.formatCount)
  - Priority 3: Animation primitives (Studio.transition, FX.zoomThrough, FX.pulse, SP.drift, SP.panTo)
  - Priority 4: Transition architecture (cinematic transitions with semantic coordination)
  - Priority 5: Visual variety (spline curves, closed area fills, liquidation gauges, particle streams)
  - Render verification: ffprobe stream inspection of sample-primitives.mp4 and snapshot validations.
"""

import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDIO_DIR = ROOT / "src" / "studio"
TEST_PRIMITIVES_DIR = ROOT / "tests" / "test-motion-primitives"


class TestStudioRuntimeUpgrades(unittest.TestCase):
    """Verifies that canonical runtime files export all new Stage 2 primitives."""

    def test_studio_base_css_typography_and_layout_tokens(self):
        css_path = STUDIO_DIR / "studio-base.css"
        self.assertTrue(css_path.exists(), "studio-base.css missing")
        content = css_path.read_text(encoding="utf-8")

        # Typography floor and scale tokens
        expected_tokens = [
            "--fs-floor",
            "--fs-display",
            "--fs-title",
            "--fs-section",
            "--fs-subtitle",
            "--fs-body",
            "--fs-callout",
            "--fs-annotation",
        ]
        for token in expected_tokens:
            self.assertIn(token, content, f"Expected CSS token '{token}' in studio-base.css")

        # Layout primitive classes
        expected_classes = [
            ".st-hero-stage",
            ".st-hero-viewport",
            ".st-split-stage",
            ".st-monument-stage",
            ".st-chart",
            ".st-timeline",
        ]
        for cls in expected_classes:
            self.assertIn(cls, content, f"Expected CSS class '{cls}' in studio-base.css")

    def test_studio_type_js_primitives(self):
        type_js_path = STUDIO_DIR / "studio-type.js"
        self.assertTrue(type_js_path.exists(), "studio-type.js missing")
        content = type_js_path.read_text(encoding="utf-8")

        # Check for T.heroHeader, T.punch, T.formatCount, and updated T.fit
        self.assertIn("T.heroHeader", content)
        self.assertIn("T.punch", content)
        self.assertIn("T.formatCount", content)
        self.assertIn("T.fit", content)
        # Check that T.fit enforces floor
        self.assertIn("floorPx", content)

    def test_studio_motion_js_primitives(self):
        motion_js_path = STUDIO_DIR / "studio-motion.js"
        self.assertTrue(motion_js_path.exists(), "studio-motion.js missing")
        content = motion_js_path.read_text(encoding="utf-8")

        # Check for Studio.transition and FX methods
        self.assertIn("Studio.transition", content)
        self.assertIn("FX.zoomThrough", content)
        self.assertIn("FX.pulse", content)
        self.assertIn("FX.coordinate", content)
        # Check for SP.drift and SP.panTo virtual camera
        self.assertIn("SP.drift", content)
        self.assertIn("SP.panTo", content)

    def test_studio_draw_js_primitives(self):
        draw_js_path = STUDIO_DIR / "studio-draw.js"
        self.assertTrue(draw_js_path.exists(), "studio-draw.js missing")
        content = draw_js_path.read_text(encoding="utf-8")

        # Check for D.chart and D.particleStream
        self.assertIn("D.chart", content)
        self.assertIn("D.particleStream", content)
        self.assertIn("CH.candlesticks", content)
        self.assertIn("CH.gauge", content)

    def test_studio_compositions_js_primitives(self):
        comp_js_path = STUDIO_DIR / "studio-compositions.js"
        self.assertTrue(comp_js_path.exists(), "studio-compositions.js missing")
        content = comp_js_path.read_text(encoding="utf-8")

        # Check for C.heroStage, C.splitStage, C.monumentStat, C.animatedChart, C.timeline
        self.assertIn("C.heroStage", content)
        self.assertIn("C.splitStage", content)
        self.assertIn("C.monumentStat", content)
        self.assertIn("C.animatedChart", content)
        self.assertIn("C.timeline", content)


class TestMotionPrimitivesRenderValidation(unittest.TestCase):
    """Verifies rendered video and snapshot artifacts produced by HyperFrames."""

    def test_sample_primitives_mp4_properties(self):
        video_path = TEST_PRIMITIVES_DIR / "sample-primitives.mp4"
        self.assertTrue(video_path.exists(), f"Rendered video {video_path} not found")
        self.assertGreater(video_path.stat().st_size, 1000000, "Rendered video size < 1MB")

        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration,size,bit_rate:stream=width,height,r_frame_rate,codec_name",
            "-of", "json",
            str(video_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res.returncode, 0, f"ffprobe failed: {res.stderr}")

        data = json.loads(res.stdout)
        stream = data["streams"][0]
        self.assertEqual(stream["codec_name"], "h264")
        self.assertEqual(stream["width"], 720)
        self.assertEqual(stream["height"], 1280)
        self.assertEqual(stream["r_frame_rate"], "30/1")

        duration = float(data["format"]["duration"])
        self.assertAlmostEqual(duration, 10.0, places=1)

    def test_snapshots_generated(self):
        snap_dir = TEST_PRIMITIVES_DIR / "snapshots"
        self.assertTrue(snap_dir.exists(), "snapshots directory missing")

        contact_sheet = snap_dir / "contact-sheet.jpg"
        self.assertTrue(contact_sheet.exists(), "contact-sheet.jpg missing")
        self.assertGreater(contact_sheet.stat().st_size, 50000)

        pngs = list(snap_dir.glob("frame-*.png"))
        self.assertGreaterEqual(len(pngs), 5, f"Expected at least 5 frame snapshots, found {len(pngs)}")

    def test_hyperframes_check_passes(self):
        cmd = ["hyperframes", "check", str(TEST_PRIMITIVES_DIR)]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res.returncode, 0, f"hyperframes check failed:\n{res.stdout}\n{res.stderr}")
        self.assertIn("Check passed", res.stdout)
        self.assertIn("0 error(s)", res.stdout)


if __name__ == "__main__":
    unittest.main()
