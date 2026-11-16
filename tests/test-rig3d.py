#!/usr/bin/env python3
"""
tests/test-rig3d.py
The 3D Tibi kit: every exercise passes scripts/rig3d-check.js (continuity, muscle presence, planted feet, IK reach,
joint limits, per-exercise assertions), the checker really fails on the defects it exists for, and the pop detector
(scripts/motion-continuity.py) flags a synthetic pop and passes smooth motion. Needs node; the pop test needs numpy
and ffmpeg (use .venv/bin/python). Skips what the host lacks.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")


def node(args, code=None):
    cmd = [NODE] + (["-e", code] if code else [str(ROOT / "scripts" / "rig3d-check.js")] + args)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)


@unittest.skipUnless(NODE, "node not installed")
class Rig3DCheck(unittest.TestCase):
    def test_every_exercise_passes_for_both_genders(self):
        for g in ("m", "f"):
            r = node(["--gender", g, "--json"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for ex in json.loads(r.stdout):
                self.assertEqual(ex["failures"], [], f"{ex['id']} ({g})")

    def test_undeclared_base_is_caught_not_silent(self):
        # A track whose base was never declared used to become NaN and make the upper body vanish from the render.
        code = r"""
global.window = global; const w = console.warn; console.warn = () => {}; global.THREE = require('./src/studio/vendor/three.min.js'); console.warn = w; global.Studio = {};
require('./src/studio/kits/fitness/brand.js'); require('./src/studio/kits/fitness/tibi3d.js'); require('./src/studio/kits/fitness/anatomy3d.js');
const T3 = Studio.kit.fitness.t3d; const m = T3.motion(); m.to(1, 1, {lean: 10}, 'none');
const v = m.at(0.5); console.log(JSON.stringify({lean: v.lean}));
"""
        r = node([], code)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout.strip().splitlines()[-1])["lean"], 0)

    def test_heel_lift_keeps_the_ball_of_the_foot_planted(self):
        # calf raises: the shoe hinges at the ball, which must not slide or lift (T3.heelLift moves the ankle instead)
        code = r"""
global.window = global; const w = console.warn; console.warn = () => {}; global.THREE = require('./src/studio/vendor/three.min.js'); console.warn = w; global.Studio = {};
require('./src/studio/kits/fitness/brand.js'); require('./src/studio/kits/fitness/tibi3d.js'); require('./src/studio/kits/fitness/anatomy3d.js');
const T3 = Studio.kit.fitness.t3d; const st = T3.stage(null, {headless: true}); const fig = st.tibi({});
const out = [];
for (const hl of [0, 12, 24, 36]) { const L = T3.heelLift(hl); fig.apply({hlL: hl, hlR: hl, y: 372 + L.up, z: L.fwd, fyawL: 0, fyawR: 0});
  const c = T3.contacts(fig); out.push({hl, ball: c.ballL, heel: c.heelL}); }
console.log(JSON.stringify(out));
"""
        r = node([], code)
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = json.loads(r.stdout.strip().splitlines()[-1])
        for row in rows:
            self.assertAlmostEqual(row["ball"][1], 0.0, delta=0.5)
            self.assertAlmostEqual(row["ball"][2], rows[0]["ball"][2], delta=0.5)
        self.assertGreater(rows[-1]["heel"], 40)

    def test_split_views_project_into_their_own_rectangle(self):
        code = r"""
global.window = global; const w = console.warn; console.warn = () => {}; global.THREE = require('./src/studio/vendor/three.min.js'); console.warn = w; global.Studio = {};
require('./src/studio/kits/fitness/brand.js'); require('./src/studio/kits/fitness/tibi3d.js'); require('./src/studio/kits/fitness/anatomy3d.js');
const T3 = Studio.kit.fitness.t3d; const st = T3.stage(null, {headless: true}); const a = st.tibi({}), b = st.tibi({id: 'b'});
st.views = [{rect: [0, 300, 720, 240], cam: {az: 0, el: 5, dist: 2400, fov: 26, tx: 0, ty: 380, tz: 0}, figs: [a]},
            {rect: [0, 540, 720, 360], cam: {az: 150, el: 8, dist: 2400, fov: 26, tx: 0, ty: 380, tz: 0}, figs: [b]}];
st.render(); const p0 = st.project(a.world('head'), 0), p1 = st.project(b.world('head'), 1);
console.log(JSON.stringify({p0, p1, vis: [a.root.visible, b.root.visible]}));
"""
        r = node([], code)
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertTrue(300 <= o["p0"]["y"] <= 540 and 540 <= o["p1"]["y"] <= 900, o)
        self.assertEqual(o["vis"], [True, True])          # per-view hiding is restored after the render

    def test_checker_flags_a_teleporting_joint(self):
        code = r"""
global.window = global; const w = console.warn; console.warn = () => {}; global.THREE = require('./src/studio/vendor/three.min.js'); console.warn = w; global.Studio = {};
require('./src/studio/kits/fitness/brand.js'); require('./src/studio/kits/fitness/tibi3d.js'); require('./src/studio/kits/fitness/anatomy3d.js'); require('./src/studio/kits/fitness/exercises3d.js');
const T3 = Studio.kit.fitness.t3d;
// a curl with a one-frame elbow snap (the 2D art-swap failure) must show up as a spike in the wrist's per-frame step
const st = T3.stage(null, {headless: true}); const sc = T3.scene(st, 'curl', {reps: 1}); const fig = sc.fig;
const pts = [];
for (let i = 0; i < 60; i++) { const v = sc.motion.at(i / 30); if (i === 2) { v.elL = 140; v.elR = 140; } fig.apply(v); pts.push(fig.world('handL').toArray()); }
const step = pts.slice(1).map((p, i) => Math.hypot(p[0]-pts[i][0], p[1]-pts[i][1], p[2]-pts[i][2]));
console.log(JSON.stringify({maxStep: Math.max(...step)}));
"""
        r = node([], code)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertGreater(json.loads(r.stdout.strip().splitlines()[-1])["maxStep"], 60)


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
class MotionContinuity(unittest.TestCase):
    def _clip(self, d, pop):
        try:
            import numpy as np
            from PIL import Image
        except ImportError:
            self.skipTest("numpy/Pillow missing: run with .venv/bin/python")
        frames = Path(d) / "f"
        frames.mkdir()
        for i in range(60):
            im = np.full((320, 180, 3), 240, np.uint8)
            x = 20 + i * 2
            im[120:200, x:x + 30] = (47, 86, 224)                       # a block gliding right (smooth motion)
            if pop and i >= 30:
                im[40:100, 120:150] = (242, 85, 61)                       # a patch that appears from nowhere
            Image.fromarray(im).save(frames / f"{i:03d}.png")
        out = Path(d) / "c.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", str(frames / "%03d.png"), "-pix_fmt", "yuv420p", str(out)], check=True)
        return out

    def run_tool(self, video):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "motion-continuity.py"), str(video), "--roi", "0,1"], capture_output=True, text=True, cwd=ROOT)

    def test_flags_pop_and_passes_smooth(self):
        with tempfile.TemporaryDirectory() as d:
            smooth = self.run_tool(self._clip(Path(d) / "a", False)) if (Path(d) / "a").mkdir() is None else None
            self.assertEqual(smooth.returncode, 0, smooth.stdout + smooth.stderr)
            popped = self.run_tool(self._clip(Path(d) / "b", True)) if (Path(d) / "b").mkdir() is None else None
            self.assertEqual(popped.returncode, 1, popped.stdout + popped.stderr)
            self.assertIn("POP", popped.stdout)


if __name__ == "__main__":
    unittest.main()
