#!/usr/bin/env python3
"""
tests/test-anatomy3d.py
The anatomy system and the fitness production tools:
  - scripts/anatomy3d-check.js passes for both bodies (watertight skin, nothing protrudes, layer order, soft masks, registration, deformation, colour language)
  - the checker really fails on the defects it exists for (a protruding muscle, a sticker-like hard-edged mask)
  - every 3D highlight is justified by assets/fitness/data/exercises.json (fitness.py check, the role audit)
  - every exercise's phaseMap tiles one rep and describes the motion (rig3d-check phase fidelity)
  - scripts/fitness-qa.py passes a clean clip and flags a frozen, black, mislabelled one; fitness-clip.py stamps honest frame-rate metadata
Needs node. Video tests need ffmpeg/numpy; locality needs existing Playwright/Pillow/Chrome.
Optional checks report a skip when their tools are absent.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
FFMPEG = shutil.which("ffmpeg")


def node(code):
    return subprocess.run([NODE, "-e", code], capture_output=True, text=True, cwd=ROOT)


PRELUDE = ("global.window=global;const w=console.warn;console.warn=()=>{};global.THREE=require('./src/studio/vendor/three.min.js');console.warn=w;global.Studio={};"
           "['brand','tibi3d','anatomy3d','exercises3d'].forEach(f=>require('./src/studio/kits/fitness/'+f+'.js'));const T3=Studio.kit.fitness.t3d;")

ANATOMY_DEFECTS = [
    ("shoulder-orb",
     "m.key = 'shoulder-envelope'; m.bone = 'chest'; m.axis = 'x'; m.region = 'arm' + m.side;\n        set(m, [sg * 68, 78, -2], [30, 12, 24], [0, 0, -sg * 30]);",
     "set(m, [0, -4, 0], [27, 27, 26]);",
     "shoulder crest", "both"),
    ("lat-lobe",
     "set(m, [sg * 28, -15, -33], [26, 85, 6], [0, 0, -sg * 18], fan);",
     "set(m, [sg * 66, -26, -33], [26, 62, 14], [0, 0, sg * 10]);",
     "surface relief", "both"),
    ("lat-elevation-bulge",
     "m.dyn = undefined; m.mask = [1, 10];",
     "m.dyn = 'lat'; m.mask = [1, 10];",
     "unsupported lat bulge", "both"),
    ("stale-normals",
     "if (shapeSig !== lastShape) { geo.computeVertexNormals(); if (corr) corr.normals(normalAttr.array); lastShape = shapeSig; }",
     "if (shapeSig !== lastShape) { lastShape = shapeSig; }",
     "morph normals are stale", "both"),
    ("additive-colour", "if (colorWeight[v7] > 0)", "if (false)",
     "linear RGB gamut", "both"),
    ("forearm-brachialis",
     "m.bone = 'sh' + m.side; m.layer = 2;\n        set(m, [sg * -3, -106, 14], [12, 29, 5]); m.mask = [2, 11];",
     "m.bone = 'el' + m.side; m.layer = 1;\n        set(m, [sg * -7, -22, 13], [13, 34, 11]); m.mask = [-1, 7];",
     "distal upper arm", "both"),
    ("open-skin", "var mesh = surfaceNets(G);",
     "var mesh = surfaceNets(G); mesh.idx.splice(0, 3);",
     "boundary edges", "both"),
    ("arm-garment", "var topFit = 1 - sstep(0.15, 0.5, armInfluence);",
     "var topFit = 1;",
     "arm-dominated vertices", "f"),
    ("serratus-slab",
     "set(m, [sg * 70, 2, 6], [4, 30, 15], [0, 0, -sg * 22], fan);",
     "set(m, [sg * 64, 6, 8], [10, 32, 9], [0, 0, sg * 20], fan);",
     "ledge on the flank or hip", "both"),
    ("glute-medius-shelf",
     "set(m, [sg * 50, 6, -26], [16, 30, 16], [0, 0, -sg * 15]);",
     "set(m, [sg * 52, 14, -26], [24, 30, 13], [0, 0, sg * -30]);",
     "ledge on the flank or hip", "f"),
    ("flat-leg-top",
     "[[-26, 20, 24, 0], [-14, 30, 32, 0], [0, 35, 35.5, 0], [30, 36, 36, 0],",
     "[[-26, 36, 36, 0], [30, 36, 36, 0],",
     "ledge on the flank or hip", "f"),
    # Known limits closed in anatomy 1.4.0: each restores the 1.3.0 behaviour in memory.
    ("glute-ball", "} else if (m.key === 'glute') {", "} else if (m.key === 'glute' && false) {",
     "a ball overhanging the thigh", "f"),
    ("effort-coverage-plate", "var muc = refined ? new Float32Array(n * NSLOT) : null;", "var muc = null;",
     "is a flat plate", "m"),
    ("stabiliser-through-white", "if (r.level === 1) r.mid.copy(r.rest).lerp(full, 0.4); else ", "",
     "pale block", "m"),
    ("garment-full-role",
     "r.fullC.copy(r.restC).lerp(full.clone().lerp(col3('#FFFFFF'), EFFORT.clothLift), EFFORT.cloth); "
     "r.midC.copy(r.restC).lerp(r.fullC, 0.4);",
     "r.fullC.copy(full); r.midC.copy(full).multiplyScalar(0.62);",
     "a saturated blob", "f"),
    ("cut-shows-inner-wall", "hideInnerWall: true,", "hideInnerWall: false,",
     "nested rings", "m"),
    ("inward-loft", "var flip = !!outward && dot(cross(ax, wd), td) > 0;", "var flip = false;",
     "wound inward", "f"),
    ("female-square-deltoid",
     "if (g === 'f') set(m, [sg * 5, -36, 0], [21, 38, 21], [0, 0, -sg * 8], capF);\n        else set(",
     "set(", "broad and square", "f"),
    ("shoulder-blend-narrow", "A.SHOULDER_BLEND = [-30, 60];", "A.SHOULDER_BLEND = [-6, 14];",
     "a ridge", "m"),
    # Round 2 (still anatomy 1.4.0): each restores the round-1 state in memory.
    ("thin-glute-fan", "gr * (0.6 + 0.4 * Math.exp(", "gr * (0.2 + 0.8 * Math.exp(",
     "surface is crumpled", "f"),
    ("centred-cut-hole", ", sweep: [0.54, 0.84] }", " }",
     "a coral loop around a hole", "m"),
    ("no-correctives", "pairs: [['shL', 'elL', 30, 50]", "pairs: [], unused: [['shL', 'elL', 30, 50]",
     "linear-blend crush", "f"),
    # 1.5.0: the hip mush now absorbs most of the squat stretch this smoothing fixed (3.81 without it, limit 4.0); the
    # hinge gate is what still catches its removal.
    ("no-hip-weight-smoothing", "passes: 12, xMax", "passes: 0, xMax",
     "a lumpy mass", "m"),
    # Round 3 (anatomy 1.5.0): each restores the 1.4.0 behaviour in memory.
    ("top-tint-ring", "var bustPrims = refined ? vol.filter", "var bustPrims = false ? vol.filter",
     "a ring around the bust", "f"),
    ("garment-grey-brown", "{ floor: 0.2, cloth: 0.65, clothLift: 0.15, peak: true }",
     "{ floor: 0.2, cloth: 0.6, clothLift: 0.3, peak: true }",
     "grey or brown smear", "m"),
    ("effort-peak-below-role", "clothLift: 0.15, peak: true }", "clothLift: 0.15, peak: false }",
     "never reaches the role colour", "f"),
    ("hinge-lbs-folds", "iterations: 40, rate: 0.5", "iterations: 0, rate: 0.5",
     "a lumpy mass", "m"),
    ("hinge-skinned-normals", "geo.computeVertexNormals(); if (corr) corr.normals(normalAttr.array);",
     "geo.computeVertexNormals();",
     "the toon bands draw lumps", "m"),
    # Round 3 phase B (anatomy 1.6.0, Tibi 0.8.0): the shoulder girdle.
    # The skin back on the 0.7.0 chest/arm weights while the girdle bones still move: the cap and armpit collapse again.
    ("no-girdle-weights", "girdle: profileSampling === 'distance' };", "girdle: false };",
     "the shoulder is crushed", "m"),
    # The girdle owning the whole back drags the lat out on elevation through the bones alone (no morph), which the pre-1.6.0
    # "any morph change" gate could not see.
    ("girdle-owns-the-back", "{ r: [50, 70, 70, 45, 40, 60], core: 0.7,", "{ r: [50, 70, 260, 45, 200, 60], core: 0.9,",
     "unsupported lat bulge", "m"),
    # A first trial let the girdle own the posterior axilla (70 behind the joint): a local flare under the arm overhead (4.9 units
    # at the 1.6.0 trial; with the field 70 below the joint it shows on the female body, max belly lift above 2.5).
    ("girdle-flares-the-posterior-axilla", "{ r: [50, 70, 70, 45, 40, 60],", "{ r: [50, 70, 70, 45, 70, 60],",
     "unsupported lat bulge", "f"),
    # The girdle field reaching 90 below the joint carries trunk skin off the ribcage overhead: wings beside the raised armpit.
    ("girdle-carries-the-flank", "{ r: [50, 70, 70, 45, 40, 60],", "{ r: [50, 70, 90, 45, 40, 60],",
     "wings under the raised arm", "m"),
    # The scapulothoracic-glide experiment flattens the lump behind the raised armpit but folds skin through skin (1.6% of rays at
    # the shoulder see back faces overhead); it is off by default and the inside-out gate must catch it if it is switched on.
    ("scapulothoracic-glide-on", "var GLIDE = A.GLIDE = { strength: 0,", "var GLIDE = A.GLIDE = { strength: 1,",
     "see the inside of the skin", "m"),
]


def mutated_anatomy_checker(before, after, gender="both", source_name="anatomy3d.js"):
    """Run the actual checker on in-memory source edits: one (before, after) pair, or a list of pairs as `before` with after=None."""
    pairs = before if after is None else [[before, after]]
    code = """
const fs=require('fs'), Module=require('module'), path=require('path');
const target=path.resolve('src/studio/kits/fitness', SOURCE_NAME);
const load=Module._extensions['.js'];
Module._extensions['.js']=function(mod,file) {
  if(file!==target) return load(mod,file);
  let source=fs.readFileSync(file,'utf8').replace(/\\r\\n/g,'\\n');
  for(const [before, after] of PAIRS) {
    if(source.split(before).length!==2) throw new Error('Negative-control anchor is not unique');
    source=source.replace(before,after);
  }
  mod._compile(source,file);
};
process.argv=['node','scripts/anatomy3d-check.js','--profile','distance','--gender',GENDER,'--json'];
require('./scripts/anatomy3d-check.js');
"""
    return node(code.replace("PAIRS", json.dumps(pairs)).replace("GENDER", json.dumps(gender))
                .replace("SOURCE_NAME", json.dumps(source_name)))


class StillCapture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "browser_stills", ROOT / "src" / "pipeline" / "browser_stills.py"
        )
        cls.browser = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.browser)

    def test_cutaway_locality_and_unclipped_negative_control(self):
        if importlib.util.find_spec("playwright") is None or importlib.util.find_spec("PIL") is None:
            self.skipTest("Needs existing Playwright and Pillow")
        try:
            self.browser.chrome()
        except FileNotFoundError as error:
            self.skipTest(str(error))
        with tempfile.TemporaryDirectory() as tmp:
            for control in (False, True):
                with self.subTest(unclipped_control=control):
                    out = Path(tmp) / ("control" if control else "corrected")
                    command = [sys.executable, str(ROOT / "scripts" / "rig3d-seek.py"),
                               "--set", "locality", "--out", str(out)]
                    if control:
                        command.append("--unclipped-control")
                    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1 if control else 0,
                                     result.stdout + result.stderr)
                    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
                    self.assertEqual(len(report["cases"]), 2)
                    for case in report["cases"]:
                        self.assertGreaterEqual(case["inside_changes"], 100)
                        if control:
                            self.assertGreater(case["outside_changes"], 0)
                            self.assertTrue(any("outside the projected cutaway bounds" in failure
                                                for failure in case["failures"]))
                        else:
                            self.assertEqual(case["outside_changes"], 0)

    def test_explicit_chrome_override_and_invalid_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "chrome with spaces.exe"
            executable.touch()
            with patch.dict(os.environ, {"CHROME": str(executable)}):
                self.assertEqual(self.browser.chrome(), str(executable.resolve()))
                executable.unlink()
                with self.assertRaisesRegex(FileNotFoundError, "CHROME"):
                    self.browser.chrome()

    def test_windows_and_mac_cache_layouts(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cache = home / ".cache" / "puppeteer" / "chrome-headless-shell"
            for platform, name in (
                ("win32", "chrome-headless-shell.exe"),
                ("darwin", "chrome-headless-shell"),
            ):
                with self.subTest(platform=platform):
                    executable = cache / platform / "binary folder" / name
                    executable.parent.mkdir(parents=True)
                    executable.touch()
                    with (
                        patch.dict(os.environ, {"CHROME": ""}),
                        patch.object(Path, "home", return_value=home),
                        patch.object(sys, "platform", platform),
                    ):
                        self.assertEqual(self.browser.chrome(), str(executable))

    def test_failed_capture_cannot_reuse_a_previous_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "cell.png"
            out.write_bytes(b"previous cell")
            failed = subprocess.CompletedProcess([], 1, "", "GPU failure")
            with patch.object(self.browser.subprocess, "run", return_value=failed):
                with self.assertRaisesRegex(RuntimeError, "GPU failure"):
                    self.browser.capture("chrome", Path(tmp) / "bench.html", "", out,
                                         40, 60, budget_ms=3000)
            self.assertFalse(out.exists())

    def test_incomplete_page_or_missing_image_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "cell.png"
            for dom, message in (
                ("<title>Loading</title>", "did not finish"),
                ("<title>ready</title>", "did not write a screenshot"),
            ):
                with self.subTest(dom=dom):
                    result = subprocess.CompletedProcess([], 0, dom, "")
                    with patch.object(self.browser.subprocess, "run", return_value=result):
                        with self.assertRaisesRegex(RuntimeError, message):
                            self.browser.capture("chrome", Path(tmp) / "bench.html", "", out,
                                                 40, 60, budget_ms=3000)

    def test_capture_encodes_paths_and_checks_image_dimensions(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "bench space #.html"
            out = Path(tmp) / "cell.png"
            image_size = (40, 60)

            def render(command, **kwargs):
                self.assertEqual(command[-1], page.resolve().as_uri() + "?w=40&h=60&g=f")
                self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
                self.assertIn("--dump-dom", command)
                Image.new("RGB", image_size).save(out)
                return subprocess.CompletedProcess(command, 0, "<title>ready</title>", "")

            with patch.object(self.browser.subprocess, "run", side_effect=render):
                self.browser.capture("chrome", page, "g=f", out, 40, 60, budget_ms=3000)
                image_size = (41, 60)
                with self.assertRaisesRegex(RuntimeError, "Wrong screenshot size"):
                    self.browser.capture("chrome", page, "g=f", out, 40, 60, budget_ms=3000)

    def test_matrix_report_rejects_changed_captures_and_unknown_reviews(self):
        spec = importlib.util.spec_from_file_location(
            "anatomy_bench", ROOT / "scripts" / "anatomy3d-bench.py"
        )
        bench = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bench)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            image = out / "cell.png"
            image.write_bytes(b"capture")
            report = {"at": "test", "profile": "legacy", "size": [40, 60], "sets": ["joints"],
                      "cases": [{"id": "joints-m-00", "body": "m", "label": "shoulder",
                                 "image": "cell.png", "image_sha256": hashlib.sha256(b"capture").hexdigest(),
                                 "status": "known-limit", "note": "Visual review pending."}]}
            bench.write_report(out, report)
            image.write_bytes(b"stale or replaced")
            with self.assertRaisesRegex(RuntimeError, "changed capture"):
                bench.write_report(out, report)
            review = out / "review.json"
            review.write_text(json.dumps({"other-case": {"status": "pass", "note": "wrong case"}}))
            with self.assertRaisesRegex(ValueError, "unknown cases"):
                bench.write_report(out, report, review)
            review.write_text(json.dumps({"joints-m-00": {
                "status": "pass", "note": "cannot replace evidence", "image": "other.png",
            }}))
            with self.assertRaisesRegex(ValueError, "only set status and note"):
                bench.write_report(out, report, review)
            image.write_bytes(b"capture")
            report["cases"][0]["query"] = "g=m&az=0&profile=legacy"
            baseline = json.loads(json.dumps(report))
            baseline["cases"][0]["query"] = "g=m&az=90&profile=legacy"
            baseline_path = out / "baseline.json"
            baseline_path.write_text(json.dumps(baseline))
            with self.assertRaisesRegex(ValueError, "pose/camera differs"):
                bench.write_report(out, report, baseline_path=baseline_path)


@unittest.skipUnless(NODE, "node not installed")
class Anatomy(unittest.TestCase):
    def test_corrected_default_and_legacy_cache_are_separate(self):
        r = node(PRELUDE + """
const out=[];
for(const gender of ['m','f']) {
  const st=T3.stage(null,{headless:true});
  const first=st.tibi({gender,profileSampling:'legacy'});
  const candidate=T3.scene(st,'curl',{gender,figId:'candidate',profileSampling:'distance'}).fig;
  const last=st.tibi({gender,profileSampling:'legacy'});
  const explicit=T3.stage(null,{headless:true}).tibi({gender,profileSampling:'distance'});
  out.push({
    legacyUnchanged:first.body.data===last.body.data,
    separate:first.body.data!==candidate.body.data,
    correctedDefault:st.tibi({gender}).body.data===candidate.body.data,
    candidateReused:candidate.body.data===explicit.body.data,
    independentArrays:candidate.body.geo.getAttribute('position').array!==explicit.body.geo.getAttribute('position').array
  });
}
let rejected=false;
try { T3.stage(null,{headless:true}).tibi({profileSampling:'unknown'}); }
catch(e) { rejected=/profileSampling/.test(e.message); }
console.log(JSON.stringify({out,rejected}));
""")
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(r.stdout)
        self.assertTrue(result["rejected"])
        for row in result["out"]:
            self.assertTrue(all(row.values()), row)

    def test_distance_profile_passes_actual_checker(self):
        r = subprocess.run(
            [NODE, str(ROOT / "scripts" / "anatomy3d-check.js"),
             "--profile", "distance", "--json"],
            capture_output=True, text=True, cwd=ROOT,
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for result in json.loads(r.stdout):
            station = result["stats"]["profileStations"]
            self.assertLessEqual(station["maxAbsDistance"], station["tolerance"])

    def test_profile_gate_rejects_legacy_sampling_in_actual_checker(self):
        r = mutated_anatomy_checker("o.profileSampling === 'distance'", "false")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        for result in json.loads(r.stdout):
            self.assertTrue(any("tube profile misses authored stations" in f
                                for f in result["failures"]), result)

    def test_integrated_gates_reject_actual_controlled_defects(self):
        source = ROOT / "src" / "studio" / "kits" / "fitness" / "anatomy3d.js"
        original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        for name, before, after, message, gender in ANATOMY_DEFECTS:
            with self.subTest(defect=name):
                result = mutated_anatomy_checker(before, after, gender)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                for row in json.loads(result.stdout):
                    self.assertTrue(any(message in failure for failure in row["failures"]), row)
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original_hash)

    def test_neutral_clearance_gate_rejects_forward_glued_arms(self):
        source = ROOT / "src" / "studio" / "kits" / "fitness" / "tibi3d.js"
        original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        result = mutated_anatomy_checker(
            "{ shL: 8, plL: 10, shR: 8, plR: 10 }",
            "{ shL: 6, plL: 70, shR: 6, plR: 70 }",
            source_name="tibi3d.js",
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for row in json.loads(result.stdout):
            self.assertTrue(any("neutral silhouette" in failure for failure in row["failures"]), row)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original_hash)

    def test_crush_gate_rejects_a_still_girdle(self):
        # Tibi 0.8.0 with the girdle held still and the soft-tissue frame on the bone is the 0.7.0 shoulder: the crush gate must bite.
        source = ROOT / "src" / "studio" / "kits" / "fitness" / "tibi3d.js"
        original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        result = mutated_anatomy_checker(
            [["rhythm: 0.42, plane: 35, follow: 0.6, elev: 12, protract: 18,", "rhythm: 0, plane: 35, follow: 0.6, elev: 0, protract: 0,"],
             ["tissue: { lag: 0.5,", "tissue: { lag: 0,"]],
            None, gender="m", source_name="tibi3d.js",
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for row in json.loads(result.stdout):
            crushed = [f for f in row["failures"] if "the shoulder is crushed" in f]
            self.assertTrue(any(f.startswith("acrossBody") for f in crushed), row["failures"])
            self.assertTrue(any(f.startswith("overhead175") for f in crushed), row["failures"])
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original_hash)

    def test_girdle_is_a_pure_function_of_the_pose(self):
        r = node(PRELUDE + """
const fig=T3.stage(null,{headless:true}).tibi({gender:'m'}), rows=[];
const read=()=>['gdL','gdR','axL','axR','shL','handL'].map(n=>{fig.root.updateMatrixWorld(true);return Array.from(fig.bone[n].matrixWorld.elements);});
const pose={shL:150,plL:60,elL:30,ikR:1,hxR:-60,hyR:180,hzR:80,pxR:-1,pyR:0,pzR:0};
fig.apply(pose); const a=read();
fig.apply({shL:20,shR:120,plR:120}); fig.apply(pose); const b=read();
let d=0; a.forEach((m,i)=>m.forEach((v,j)=>{d=Math.max(d,Math.abs(v-b[i][j]));}));
fig.apply({}); const rest=fig.bone.gdL.quaternion.toArray();
const gl=T3.stage(null,{headless:true}).tibi({gender:'m',profileSampling:'legacy'}); gl.apply(pose);
fig.apply(pose);
fig.root.updateMatrixWorld(true);
const ghRest=new THREE.Vector3(-fig.spec.shx, fig.spec.shy-150, -2).applyMatrix4(fig.bone.chest.matrixWorld), hand=fig.bone.handR.getWorldPosition(new THREE.Vector3());
const handErr=hand.sub(ghRest).sub(new THREE.Vector3(-60,180,80)).length();
console.log(JSON.stringify({d, rest, handErr, legacyStill: gl.bone.gdL.quaternion.toArray(), moved: fig.bone.gdR.userData.girdle}));
""")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["d"], 0)                                   # same pose, same matrices, whatever came before
        self.assertEqual(out["rest"][:3], [0, 0, 0])                    # neutral stance: the girdle coincides with the chest
        self.assertEqual(out["legacyStill"][:4], [0, 0, 0, 1])          # legacy profile: still girdle
        self.assertGreater(out["moved"]["up"], 10)                      # an IK arm overhead drives the girdle too
        self.assertLess(out["handErr"], 1e-6)                           # ...and its hand still lands exactly on the target

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

    def test_small_pose_changes_are_independent_of_seek_order(self):
        r = node(PRELUDE + """
const out={};
for(const gender of ['m','f']) {
  const f=T3.stage(null,{headless:true}).tibi({gender,id:'q'});
  f.roles({biceps:3});
  const target={'q.elL':100,'q.elR':100,'q.act.biceps':0.5};
  f.apply(target);
  const names=['position','color','colorC'];
  const expected=names.map(n=>f.body.geo.getAttribute(n).array.slice());
  f.apply({});
  f.apply({'q.elL':100.01,'q.elR':100.01,'q.act.biceps':0.50001});
  f.apply(target);
  out[gender]=names.map((n,i)=>f.body.geo.getAttribute(n).array.every((v,j)=>v===expected[i][j]));
}
console.log(JSON.stringify(out));
""")
        self.assertEqual(r.returncode, 0, r.stderr)
        for gender, equal in json.loads(r.stdout).items():
            self.assertEqual(equal, [True, True, True], gender)

    def test_crescent_shade_is_opt_in_and_reversible(self):
        # Prompt 05 look prototype (T3.anatomy.shade): crescent changes every toon program of the figure, including cutaway layers
        # built later, and 'toon' restores the default programs exactly; an unknown mode is rejected.
        r = node(PRELUDE + """
const st=T3.stage(null,{headless:true}), f=st.tibi({gender:'f'}), A=T3.anatomy, skin=f.body.skin.material;
const mats=[]; f.root.traverse(o=>{ if(o.material&&o.material.isMeshToonMaterial) mats.push(o.material); });
const before=mats.map(m=>[m.customProgramCacheKey(), m.onBeforeCompile]);
const fake=()=>({uniforms:{},vertexShader:'#include <common>\\n#include <begin_vertex>',fragmentShader:'#include <common>\\n#include <color_fragment>\\n#include <opaque_fragment>'});
A.shade(f,'crescent');
const sh=fake(); skin.onBeforeCompile(sh);
const on={keysDiffer:mats.every((m,i)=>m.customProgramCacheKey()!==before[i][0]), tone:!!f.body.geo.getAttribute('aTone'),
  planes:/outgoingLight = mix/.test(sh.fragmentShader)&&/aTone/.test(sh.vertexShader)};
f.body.ensureInner(); const innerCrescent=f.body.inner.materials.every(m=>!!m.userData.tibiShade);
A.shade(f,'toon');
const off={keysRestored:mats.every((m,i)=>m.customProgramCacheKey()===before[i][0]&&m.onBeforeCompile===before[i][1]),
  toneGone:!f.body.geo.getAttribute('aTone'), innerRestored:f.body.inner.materials.every(m=>!m.userData.tibiShade)};
let rejected=false; try { A.shade(f,'glossy'); } catch(e) { rejected=/Unknown Tibi shade/.test(e.message); }
console.log(JSON.stringify({on,innerCrescent,off,rejected}));
""")
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(r.stdout)
        self.assertTrue(all(result["on"].values()), result)
        self.assertTrue(result["innerCrescent"], result)
        self.assertTrue(all(result["off"].values()), result)
        self.assertTrue(result["rejected"])


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
