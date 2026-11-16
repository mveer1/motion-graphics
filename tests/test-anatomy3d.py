#!/usr/bin/env python3
"""
tests/test-anatomy3d.py
The anatomy system and the fitness production tools:
  - scripts/anatomy3d-check.js passes for both bodies (watertight skin, nothing protrudes, layer order, soft masks, registration, deformation, colour language)
  - the checker really fails on the defects it exists for (a protruding muscle, a sticker-like hard-edged mask)
  - every 3D highlight is justified by assets/fitness/data/exercises.json (fitness.py check, the role audit)
  - every exercise's phaseMap tiles one rep and describes the motion (rig3d-check phase fidelity)
  - scripts/fitness-qa.py passes a clean clip and flags a frozen, black, mislabelled one; fitness-clip.py stamps honest frame-rate metadata
Needs node. The video tests need ffmpeg and numpy (use .venv/bin/python); each skips what the host lacks.
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
FFMPEG = shutil.which("ffmpeg")


def node(code):
    return subprocess.run([NODE, "-e", code], capture_output=True, text=True, cwd=ROOT)


PRELUDE = ("global.window=global;const w=console.warn;console.warn=()=>{};global.THREE=require('./src/studio/vendor/three.min.js');console.warn=w;global.Studio={};"
           "['brand','tibi3d','anatomy3d','exercises3d'].forEach(f=>require('./src/studio/kits/fitness/'+f+'.js'));const T3=Studio.kit.fitness.t3d;")


@unittest.skipUnless(NODE, "node not installed")
class Anatomy(unittest.TestCase):
    def test_acceptance_tests_pass_for_both_bodies(self):
        r = subprocess.run([NODE, str(ROOT / "scripts" / "anatomy3d-check.js"), "--json"], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:] + r.stderr[-500:])
        for res in json.loads(r.stdout):
            self.assertEqual(res["failures"], [], res["gender"])
            self.assertEqual(res["stats"]["skin"]["components"], 1)

    def test_a_muscle_is_not_a_separate_object(self):
        # the old failure: one rigid mesh per muscle parented to a bone. Now the only skinned mesh in the body is the skin (plus the hidden inner group).
        r = node(PRELUDE + "const st=T3.stage(null,{headless:true});const f=st.tibi({});let muscleMeshes=0;f.root.traverse(o=>{if(o.isMesh&&/muscle|quad|glute|calf|biceps/i.test(o.name||'')&&!o.parent.name.match(/inner/))muscleMeshes++;});"
                  "console.log(JSON.stringify({muscleMeshes,records:f.muscles.length,skin:f.body.skin.name}))")
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(o["muscleMeshes"], 0)
        self.assertEqual(o["skin"], "skin")
        self.assertGreater(o["records"], 40)

    def test_checker_flags_a_protruding_inner_muscle(self):
        code = PRELUDE + ("const st=T3.stage(null,{headless:true});const f=st.tibi({});f.body.ensureInner();const G=f.body.data.G;const m=f.body.inner.meshes.muscles[0].mesh;"
                          "const pa=m.geometry.getAttribute('position');for(let i=0;i<pa.count;i++)pa.setXYZ(i,pa.getX(i)*1.6,pa.getY(i),pa.getZ(i)*1.6+60);"
                          "let mx=-1e9;for(let i=0;i<pa.count;i++)mx=Math.max(mx,T3.anatomy._gridAt(G,pa.getX(i),pa.getY(i),pa.getZ(i)));console.log(JSON.stringify({mx}))")
        r = node(code)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertGreater(json.loads(r.stdout.strip().splitlines()[-1])["mx"], -1.5)      # the same measure the checker uses would fail it

    def test_checker_flags_a_hard_edged_mask(self):
        code = PRELUDE + ("const st=T3.stage(null,{headless:true});const f=st.tibi({});const b=f.body,d=b.data;const r=b.muscles.find(x=>x.key==='quad'&&x.layer===1);"
                          "const n=d.n,bw=new Float32Array(n);for(let k=0;k<r.vi.length;k++)bw[r.vi[k]]=r.vw[k]>0.5?1:0;"            # binarise: a sticker's edge
                          "const adj=new Array(n).fill(0).map(()=>[]);for(let i=0;i<d.mesh.idx.length;i+=3)for(let e=0;e<3;e++)adj[d.mesh.idx[i+e]].push(d.mesh.idx[i+(e+1)%3]);"
                          "let j=0;for(let k=0;k<r.vi.length;k++){const v=r.vi[k];for(const u of adj[v])j=Math.max(j,Math.abs(bw[v]-bw[u]));}console.log(JSON.stringify({jump:j}))")
        r = node(code)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertGreater(json.loads(r.stdout.strip().splitlines()[-1])["jump"], 0.7)

    def test_highlights_are_defensible(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "fitness.py"), "check"], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stdout[-1500:])

    def test_phase_maps_tile_one_rep(self):
        r = node(PRELUDE + "const out={};for(const k in T3.exercises){const m=T3.exercises[k].phaseMap;let ok=m[0].a===0&&Math.abs(m[m.length-1].b-1)<1e-9;for(let i=1;i<m.length;i++)ok=ok&&Math.abs(m[i].a-m[i-1].b)<1e-9;out[k]=ok;}console.log(JSON.stringify(out))")
        self.assertEqual(r.returncode, 0, r.stderr)
        for k, ok in json.loads(r.stdout.strip().splitlines()[-1]).items():
            self.assertTrue(ok, k)

    def test_a_figure_with_an_id_really_moves(self):
        # the press froze in every film because its path callbacks returned unprefixed keys
        r = node(PRELUDE + "const st=T3.stage(null,{headless:true});const sc=T3.scene(st,'press',{figId:'zz',reps:2,period:3,at:0});const f=sc.fig;"
                  "const ys=[];for(let t=0;t<6;t+=0.1){f.apply(sc.motion.at(t));ys.push(f.world('handL').y);}console.log(JSON.stringify({range:Math.max(...ys)-Math.min(...ys)}))")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertGreater(json.loads(r.stdout.strip().splitlines()[-1])["range"], 120)


@unittest.skipUnless(FFMPEG, "ffmpeg not installed")
class Tools(unittest.TestCase):
    def _make(self, d, name, vf, r=30, extra=()):
        out = Path(d) / name
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", vf, "-r", str(r), "-pix_fmt", "yuv420p", *extra, str(out)], check=True)
        return out

    def run_qa(self, path, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "fitness-qa.py"), str(path), *args], capture_output=True, text=True, cwd=ROOT)

    def test_qa_flags_a_frozen_black_mislabelled_clip(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy missing: run with .venv/bin/python")
        with tempfile.TemporaryDirectory() as d:
            bad = self._make(d, "bad-60fps.mp4", "color=gray:s=180x320:d=4:r=24", r=24, extra=("-metadata", "comment=180x320 60 fps"))
            r = self.run_qa(bad, "--cuts", "0")
            self.assertEqual(r.returncode, 1, r.stdout)
            for word in ("frame rate", "60 fps", "frozen picture", "blank"):
                self.assertIn(word, r.stdout)

    def test_qa_passes_a_moving_clip(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("numpy missing: run with .venv/bin/python")
        with tempfile.TemporaryDirectory() as d:
            ok = Path(d) / "ok.mp4"                                  # a block gliding across a paper-coloured frame: deterministic, smooth motion from frame 0
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0xF6F3EC:s=180x320:d=4:r=30", "-f", "lavfi", "-i", "color=c=0x2F56E0:s=40x70:d=4:r=30",
                            "-filter_complex", "[0][1]overlay=x='10+t*34':y=110", "-pix_fmt", "yuv420p", str(ok)], check=True)
            r = self.run_qa(ok, "--cuts", "0", "--motion", "0.5")
            self.assertEqual(r.returncode, 0, r.stdout)

    def test_clip_tool_stamps_true_frame_rate_and_archives(self):
        with tempfile.TemporaryDirectory() as d:
            film = self._make(d, "film.mp4", "testsrc2=s=180x320:d=4:r=30")
            out = Path(d) / "clips"
            cmd = [sys.executable, str(ROOT / "scripts" / "fitness-clip.py"), str(film), "--cut", "a:0:2", "--out", str(out), "--title", "T"]
            self.assertEqual(subprocess.run(cmd, capture_output=True, text=True).returncode, 0)
            self.assertEqual(subprocess.run(cmd, capture_output=True, text=True).returncode, 0)          # again: the first file is archived, not overwritten
            self.assertEqual(len(list((out / "archive").glob("*/a.mp4"))), 1)
            tags = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", str(out / "a.mp4")], capture_output=True, text=True).stdout)["format"]["tags"]
            self.assertIn("30 fps", tags["comment"])


if __name__ == "__main__":
    unittest.main()
