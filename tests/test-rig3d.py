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
        for profile in ("legacy", "distance"):
            for g in ("m", "f"):
                r = node(["--gender", g, "--profile", profile, "--json"])
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                for ex in json.loads(r.stdout):
                    self.assertEqual(ex["failures"], [], f"{ex['id']} ({g}, {profile})")

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

    def test_direct_leg_pose_resets_previous_heel_lift(self):
        code = r"""
global.window=global;const warn=console.warn;console.warn=()=>{};
global.THREE=require('./src/studio/vendor/three.min.js');console.warn=warn;global.Studio={};
['brand','tibi3d','anatomy3d'].forEach(n=>require('./src/studio/kits/fitness/'+n+'.js'));
const T3=Studio.kit.fitness.t3d,out={};
for(const gender of ['m','f']) {
  const fig=T3.stage(null,{headless:true}).tibi({gender,id:'q'});
  const target={'q.ikLegL':0,'q.ikLegR':0};
  const toes=()=>['L','R'].map(s=>fig.bone['an'+s].children.find(c=>c.type==='Group').rotation.x);
  fig.apply(target);const expected=toes();
  fig.apply({'q.hlL':32,'q.hlR':24});fig.apply(target);
  out[gender]={expected,actual:toes()};
}
console.log(JSON.stringify(out));
"""
        r = node([], code)
        self.assertEqual(r.returncode, 0, r.stderr)
        for gender, row in json.loads(r.stdout).items():
            self.assertEqual(row["actual"], row["expected"], gender)

    def test_fitted_camera_is_checked_between_its_samples(self):
        # A fitter that samples only the start and end of a lateral raise frames the low arms and loses the raised ones.
        code = r"""
const fs=require('fs'),Module=require('module'),path=require('path');
const target=path.resolve('src/studio/kits/fitness/tibi3d.js'),load=Module._extensions['.js'];
Module._extensions['.js']=function(mod,file){
  if(file!==target) return load(mod,file);
  const src=fs.readFileSync(file,'utf8'),before='var n = fo.samples || 48';
  if(src.split(before).length!==2) throw new Error('anchor');
  mod._compile(src.replace(before,'var n = fo.samples || 2'),file);
};
process.argv=['node','scripts/rig3d-check.js','raise','--json'];
require('./scripts/rig3d-check.js');
"""
        r = node([], code)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertTrue(any("fitted camera still loses" in f for f in json.loads(r.stdout)[0]["failures"]))

    def test_bind_updates_visibility_before_the_current_render(self):
        code = r"""
global.window=global;const warn=console.warn;console.warn=()=>{};
global.THREE=require('./src/studio/vendor/three.min.js');console.warn=warn;global.Studio={};
['brand','tibi3d'].forEach(n=>require('./src/studio/kits/fitness/'+n+'.js'));
const T3=Studio.kit.fitness.t3d,frames=[],fig={visible:true,apply(){}};
const stage={cam:{},figures:[fig],render(beforeDraw){if(beforeDraw)beforeDraw();frames.push(fig.visible);}};
const draw=T3.bind({fromTo(){}},stage,T3.motion(),3,(_,t)=>{fig.visible=t<1;});
draw(2);draw(0);draw(0);console.log(JSON.stringify(frames));
"""
        r = node([], code)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [True, False, True, True])

    def test_split_projection_cameras_do_not_accumulate_children(self):
        code = r"""
global.window=global;const warn=console.warn;console.warn=()=>{};
global.THREE=require('./src/studio/vendor/three.min.js');console.warn=warn;global.Studio={};
['brand','tibi3d'].forEach(n=>require('./src/studio/kits/fitness/'+n+'.js'));
const T3=Studio.kit.fitness.t3d,stage=T3.stage(null,{headless:true});
stage.views=[{rect:[0,0,360,640],cam:{az:35,el:8,dist:2400,fov:26,tx:0,ty:380,tz:0},figs:[]}];
for(let i=0;i<40;i++)stage.render();
console.log(JSON.stringify({projection:stage.views[0].camera.children.length,lighting:stage.camera.children.length}));
"""
        r = node([], code)
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(r.stdout)
        self.assertEqual(result["projection"], 0)
        self.assertEqual(result["lighting"], 2)


def patched_check(patches, args):
    """Run rig3d-check.js with source replacements applied at load ({kit file: [(before, after), ...]}) and return (code, json)."""
    code = r"""
const fs=require('fs'),Module=require('module'),path=require('path');
const patches=JSON.parse(process.env.RIG_PATCHES),load=Module._extensions['.js'];
Module._extensions['.js']=function(mod,file){
  const rel=path.relative(process.cwd(),file).split(path.sep).join('/');
  if(!patches[rel]) return load(mod,file);
  let src=fs.readFileSync(file,'utf8');
  for(const [a,b] of patches[rel]){ if(src.split(a).length!==2) throw new Error('anchor not unique in '+rel+': '+a); src=src.replace(a,()=>b); }
  mod._compile(src,file);
};
process.argv=['node','scripts/rig3d-check.js'].concat(JSON.parse(process.env.RIG_ARGS));
require('./scripts/rig3d-check.js');
"""
    env = dict(__import__("os").environ, RIG_PATCHES=json.dumps(patches), RIG_ARGS=json.dumps(args + ["--json"]))
    r = subprocess.run([NODE, "-e", code], capture_output=True, text=True, cwd=ROOT, env=env)
    return r.returncode, (json.loads(r.stdout) if r.stdout.strip().startswith("[") else r.stdout + r.stderr)


TIBI = "src/studio/kits/fitness/tibi3d.js"
EXERCISES = "src/studio/kits/fitness/exercises3d.js"


@unittest.skipUnless(NODE, "node not installed")
class KnownLimitGates(unittest.TestCase):
    """Tibi 0.6.0 gates (ponytail, bench arch, foot roll) pass now and fail on the 0.5.0 behaviour, restored by a source patch."""

    def failures(self, patches, args):
        code, out = patched_check(patches, args)
        self.assertIsInstance(out, list, out)
        return code, {r["id"]: r["failures"] for r in out}

    def test_gates_pass_on_the_current_rig(self):
        code, f = self.failures({}, ["press", "squat-blocked", "foot-roll", "ponytail-follow-through", "--gender", "f"])
        self.assertEqual(code, 0, f)

    def test_ponytail_gates_bite_on_the_lean_only_tail(self):
        old = "if (ponyTail) { ponyTail.quaternion.identity(); ponyMount.rotation.set(0, 0, 0); pony.rotation.set(-0.25 * (R('lean') * D2R) - 0.06, 0, 0); }"
        # the whole 0.5.0 press: lean-only tail AND the flat back (with the arch's chin tuck the old tail happens to clear the pad)
        code, f = self.failures({TIBI: [("if (ponyTail) hair(p, R);", old)],
                                 EXERCISES: [("var arch = o.arch === undefined ? 22 : o.arch;", "var arch = 0;")]},
                                ["press", "squat-blocked", "ponytail-follow-through", "--gender", "f"])
        self.assertEqual(code, 1)
        self.assertTrue(any("does not lag" in x for x in f["ponytail-follow-through"]), f)
        self.assertTrue(any("into equipment" in x for x in f["press"]), f)            # the tail through the bench
        self.assertTrue(any("into the neck" in x for x in f["squat-blocked"]), f)     # the tail through the upper back

    def test_ponytail_seek_order_case_bites_on_carried_state(self):
        # a tail that carries anything from the previous frame (here a frame counter) must fail the seek-order case
        carried = ("if (ponyTail) { hair(p, R); ponyTail.userData.n = (ponyTail.userData.n || 0) + 1; "
                   "ponyTail.rotation.z += 0.001 * ponyTail.userData.n; ponyTail.updateMatrixWorld(true); }")
        code, f = self.failures({TIBI: [("if (ponyTail) hair(p, R);", carried)]}, ["squat", "--gender", "f"])
        self.assertEqual(code, 1)
        self.assertTrue(any("seek order" in x for x in f["squat"]), f)

    def test_bench_arch_gate_bites_on_a_flat_back(self):
        code, f = self.failures({EXERCISES: [("var arch = o.arch === undefined ? 22 : o.arch;", "var arch = 0;")]}, ["press"])
        self.assertEqual(code, 1)
        self.assertTrue(any("lower back" in x for x in f["press"]), f)
        self.assertTrue(any("do not rest on the pad" in x for x in f["press"]), f)

    def test_foot_roll_gates_bite_on_a_ball_hinge(self):
        code, f = self.failures({TIBI: [("if (hl < 0) {", "if (false) {"), ("TOE_MAX = 45;", "TOE_MAX = 1e9;"),
                                        ("var SHOE_BEND_LEN = 24;", "var SHOE_BEND_LEN = 0.01;")]}, ["foot-roll"])
        self.assertEqual(code, 1)
        msgs = " | ".join(f["foot-roll"])
        self.assertIn("heelStrike: the heel slides", msgs)                             # heel strike pivoted on the ball
        self.assertIn("toeOff: the sole bends", msgs)                                  # no toe-off: the toes bend past the joint limit
        self.assertIn("kinks", msgs)                                                    # a hinge, not a bending sole


@unittest.skipUnless(NODE, "node not installed")
class MotionFamily1Gates(unittest.TestCase):
    """Hinge, split stance and prone exercises (Tibi 0.7.0): each exercise-specific check fails when the parameter that makes the
    cue true is broken in the source (one run, four exercises), and the checker reads pose keys through the figure id."""

    def test_exercise_checks_bite_on_broken_parameters(self):
        code, out = patched_check({EXERCISES: [
            # deadlift: a rounding spine with the same bar path (the mistake variant's parameter, put into the correct lift)
            ("solver: { bottom: 98, arm: [-12, 6], phiShape: dlShape, gapTop: 2.5, gapBottom: 3, startBottom: true },",
             "solver: { bottom: 98, arm: [-12, 6], phiShape: dlShape, gapTop: 2.5, gapBottom: 3, startBottom: true, round: 28 },"),
            # push-up: hips sagging, and arms asked past their reach at the top (the revived IK reach gate)
            ("return buildPushup(X3['push-up'], stage, fig, m, o, {});", "return buildPushup(X3['push-up'], stage, fig, m, o, { sag: 14 });"),
            ("var dTop = 238.5,", "var dTop = 241,"),
            # split squat: the front shin driven far past vertical
            ("var SPLIT = { fx: 50, yaw: 4, stance: 360, zF: 200, hl: [26, 62], shinB: 10,", "var SPLIT = { fx: 50, yaw: 4, stance: 360, zF: 200, hl: [26, 62], shinB: 34,"),
            # plank: no breath, so the hold freezes
            ("breath: 1.6, handTilt: 22 }", "breath: 0, handTilt: 22 }"),
        ]}, ["deadlift", "push-up", "split-squat", "plank"])
        self.assertEqual(code, 1)
        self.assertIsInstance(out, list, out)
        f = {r["id"]: " | ".join(r["failures"]) for r in out}
        self.assertIn("the spine bends", f["deadlift"])
        self.assertIn("off the shoulder-ankle line", f["push-up"])
        self.assertIn("IK hand target", f["push-up"])
        self.assertIn("front shin", f["split-squat"])
        self.assertIn("the hold freezes", f["plank"])

    def test_mistake_variants_show_the_mistake_and_keep_the_rest(self):
        code, out = patched_check({}, ["deadlift-rounded", "push-up-sag", "split-squat-valgus"])
        self.assertEqual(code, 0, out)
        ex = {r["id"]: r["exercise"] for r in out}
        self.assertGreaterEqual(ex["deadlift-rounded"]["spineFlexAtFloor"], 20)        # the back visibly rounds at the floor
        self.assertLessEqual(ex["deadlift-rounded"]["barDrift"], 6)                     # on the same vertical bar path
        self.assertLessEqual(ex["push-up-sag"]["hipLineMin"], -15)                      # the hips drop under the line
        self.assertGreaterEqual(ex["split-squat-valgus"]["kneeInwardAtBottom"], 15)     # the front knee caves in
        # without its one parameter the variant shows nothing, and its own check says so
        code, out = patched_check({EXERCISES: [("merge(SPLIT, { kv: 12 })", "merge(SPLIT, { kv: 0 })")]}, ["split-squat-valgus"])
        self.assertEqual(code, 1)
        self.assertIn("knee-caves variant", " | ".join(out[0]["failures"]))

    def test_ponytail_hang_gates_bite_on_the_sliding_tail(self):
        # Round 2: the 0.7.0 first-round tail slid sideways off the nape (and stayed one rigid piece). Restore it: the upright tilt gate
        # fails on the squat, the face-down gravity and lateral gates on the plank. The current tail passes the same gates.
        slide = ("var hang = (function () { var over = -14 + 12 - th; if (over > 0) ps += 1.6 * over; ps = softClamp(ps, -PONY.psiMax, PONY.psiMax, 6); "
                 "var far = Math.max(0, Math.min(1, (-14 - th - 20) / 30)); far = far * far * (3 - 2 * far); var tm = -14 - 60 * far * Math.abs(ps) / PONY.psiMax; "
                 "return { th: softClamp(th, tm, PONY.thetaMax, 6), ps: ps, tmin: tm }; })(), tmin = PONY.thetaMin;")
        code, out = patched_check({TIBI: [("var hang = bodyHang(uSum, qPony), tmin = PONY.thetaMin;", slide),
                                          ("      tipHang(gSum);", "      ponyTip.quaternion.identity(); ponyTip.updateMatrixWorld(true);")]},
                                  ["squat", "plank", "--gender", "f"])
        self.assertEqual(code, 1)
        f = {r["id"]: " | ".join(r["failures"]) for r in out}
        self.assertIn("tilts", f["squat"])
        self.assertIn("off straight down while face down", f["plank"])
        self.assertIn("sticks out", f["plank"])
        code, out = patched_check({}, ["squat", "plank", "--gender", "f"])
        self.assertEqual(code, 0, out)


@unittest.skipUnless(NODE, "node not installed")
class MotionFamily2Gates(unittest.TestCase):
    """Machines, the barbell bench and the rack squat (2026-11-24): each exercise check fails when the parameter that makes its cue
    true is broken in the source, and each mistake variant measurably shows its mistake (and fails when its one parameter is undone)."""

    def test_exercise_checks_bite_on_broken_parameters(self):
        code, out = patched_check({EXERCISES: [
            # leg extension: the knee off the machine's pivot (the mistake variant's parameter, put into the correct exercise)
            ("return buildKneeMachine(X3['leg-extension'], stage, fig, m, o, merge(LEGEXT, {}));",
             "return buildKneeMachine(X3['leg-extension'], stage, fig, m, o, merge(LEGEXT, { pivot: [-14, -32] }));"),
            # leg curl: the return stops short of the stretch
            ("return buildKneeMachine(X3['leg-curl'], stage, fig, m, o, merge(LEGCURL, {}));",
             "return buildKneeMachine(X3['leg-curl'], stage, fig, m, o, merge(LEGCURL, { k0: 48 }));"),
            # leg press: knees snap straight, feet low on the platform (ankle past its range), the sole tilted off the platform, and the
            # pelvis rolling off the pad at the bottom (the "butt wink")
            ("var LEGPRESS = { sled: 45, recline: 25, seat: 35, hipY: 250, kTop: 12, kBot: 85, kBotRef: 85, rollPivot: 120, e: 80,",
             "var LEGPRESS = { sled: 45, recline: 25, seat: 35, hipY: 250, kTop: 2, kBot: 85, kBotRef: 85, rollPivot: 120, e: 80,"),
            ("fp = -(90 + cfg.sled);", "fp = -(75 + cfg.sled);"),
            ("k['mach.sled'] = s;", "k['mach.sled'] = s; k.pitch = pitch - 10 * s;"),
            # barbell bench: the wrist ahead of the elbow (forearm not vertical), the bar touching high on the chest with the elbows
            # flared, and the rack moved into the bar path
            ("r['hx' + sd] = wx;", "r['hx' + sd] = wx + 40;"),
            ("{ touch: 85, lockFlex: 15, lockX: 6, plate: 90, rackBack: 70 }", "{ touch: 20, lockFlex: 15, lockX: 6, plate: 90, rackBack: -10 }"),
            # rack squat: safety pins set above the bottom of the squat
            ("pin = rod(6, T3.colors.steel); setRod(pin, new V3m(x0 + sg * px, lo.y - 25, zF + 20), new V3m(x0 + sg * px, lo.y - 25, zB - 20));",
             "pin = rod(6, T3.colors.steel); setRod(pin, new V3m(x0 + sg * px, lo.y + 10, zF + 20), new V3m(x0 + sg * px, lo.y + 10, zB - 20));"),
            ("pinY: lo.y - 25,", "pinY: lo.y + 10,"),
        ]}, ["leg-extension", "leg-curl", "leg-press", "barbell-bench-press", "squat-rack"])
        self.assertEqual(code, 1)
        self.assertIsInstance(out, list, out)
        f = {r["id"]: " | ".join(r["failures"]) for r in out}
        self.assertIn("off the pivot", f["leg-extension"])
        self.assertIn("only extends to", f["leg-curl"])
        for msg in ("no hard snap", "off the platform", "the pelvis tilts", "the glutes are"):
            self.assertIn(msg, f["leg-press"])
        for msg in ("forearm leans", "elbow flare", "hits the rack"):
            self.assertIn(msg, f["barbell-bench-press"])
        self.assertIn("the bar touches the rack", f["squat-rack"])
        self.assertIn("safety pins are", f["squat-rack"])
        # leg press with the feet low on the platform (e 0): the ankle is driven past its range (run alone: the foot-pitch patch above
        # would offset the ankle angle)
        code, out = patched_check({EXERCISES: [("kBotRef: 85, rollPivot: 120, e: 80,", "kBotRef: 85, rollPivot: 120, e: 0,")]}, ["leg-press"])
        self.assertEqual(code, 1, out)
        self.assertIn("the ankle is at", " | ".join(out[0]["failures"]))
        # barbell bench touching high on the chest (touch 20) (run alone: the wrist-ahead patch above moves the hands 40 units toward
        # the feet, which on the 1.15.0 body puts the touch point back inside 40-120)
        code, out = patched_check({EXERCISES: [("{ touch: 85, lockFlex: 15, lockX: 6, plate: 90, rackBack: 70 }",
                                                "{ touch: 20, lockFlex: 15, lockX: 6, plate: 90, rackBack: 70 }")]}, ["barbell-bench-press"])
        self.assertEqual(code, 1, out)
        self.assertIn("the bar touches", " | ".join(out[0]["failures"]))

    def test_mistake_variants_show_the_mistake(self):
        code, out = patched_check({}, ["leg-extension-misaligned", "leg-curl-short", "leg-press-deep"])
        self.assertEqual(code, 0, out)
        ex = {r["id"]: r["exercise"] for r in out}
        self.assertGreaterEqual(ex["leg-extension-misaligned"]["kneeToPivotMax"], 20)   # the knee sits off the pivot
        self.assertGreaterEqual(ex["leg-extension-misaligned"]["rollerSlide"], 15)      # so the pad slides along the shin
        self.assertGreaterEqual(ex["leg-curl-short"]["kneeFlexMin"], 35)                # the return stops short of the stretch
        self.assertGreaterEqual(ex["leg-press-deep"]["pelvisTilt"], 8)                  # too deep: the pelvis rolls back
        self.assertGreaterEqual(ex["leg-press-deep"]["gluteGapMax"], 4)                 # and the hips leave the pad
        code, out = patched_check({EXERCISES: [("merge(LEGEXT, { pivot: [-14, -32] })", "merge(LEGEXT, { pivot: [0, 0] })"),
                                               ("merge(LEGCURL, { k0: 48 })", "merge(LEGCURL, { k0: 6 })"),
                                               ("merge(LEGPRESS, { kBot: 97 })", "merge(LEGPRESS, { kBot: 85 })")]},
                                  ["leg-extension-misaligned", "leg-curl-short", "leg-press-deep"])
        self.assertEqual(code, 1)
        f = {r["id"]: " | ".join(r["failures"]) for r in out}
        self.assertIn("the mistake is not visible", f["leg-extension-misaligned"])
        self.assertIn("the mistake is not visible", f["leg-curl-short"])
        self.assertIn("the mistake is not visible", f["leg-press-deep"])

    def test_bench_grip_roll_gate_bites_on_a_lockout_across_the_body(self):
        # With the bar exactly over the shoulder joints at lockout the arm lies in the plane across the body, the rig's hand roll
        # (gaz, wrapped to +-90 deg) is ambiguous, and on the legacy skin one hand flipped 180 deg. lockX 6 avoids it; 0 must fail.
        code, out = patched_check({EXERCISES: [("lockFlex: 15, lockX: 6,", "lockFlex: 15, lockX: 0,")]},
                                  ["barbell-bench-press", "--profile", "legacy"])
        self.assertEqual(code, 1, out)
        self.assertIn("flipped grip", " | ".join(out[0]["failures"]))

    def test_ponytail_clearance_counts_the_shoulder_girdle_skin(self):
        # Tibi 0.8.0's girdle bones (gdL/gdR) own the skin over the top of the shoulder (about 1070 vertices a side). Probe the
        # clearance gate with one tail point 4 units under the top of the left shoulder (the highest gdL-owned skin point at
        # x 70-74, z -3..5; calf raise, arms hanging): it must fail. (The pre-girdle bone list was blind to 56 of 358 points 4 units inside the girdle skin
        # at rest; in this exercise it still flags the probe, but against chest/neck skin with the wrong normal: 7-13 units.)
        probe = ("T3.skinScan(fig, ['gdL'], q => { if (Math.abs(q.x - 72) < 2 && Math.abs(q.z - 1) < 4 && (!fig.__top || q.y > fig.__top.y)) fig.__top = q.clone(); });"
                 " fig.__probe = fig.__top.clone().add(new THREE.Vector3(0, -4, 0)); fig.__top = null; const pen = ponyIntrusion(fig);")
        one = ("  (fig.__probe ? [null] : [fig.pony.tail, fig.pony.tip]).forEach(g => (g ? visit : (_g, f) => f(fig.__probe))(g, q => {")
        patches = [("const pen = ponyIntrusion(fig);", probe), ("  [fig.pony.tail, fig.pony.tip].forEach(g => visit(g, q => {", one)]
        code, out = patched_check({"scripts/rig3d-check.js": patches}, ["calfraise", "--gender", "f"])
        self.assertEqual(code, 1, out)
        self.assertIn("into the neck, back or shoulders", " | ".join(out[0]["failures"]))

    def test_tilted_pad_hair_gate_bites_without_supports(self):
        # The ponytail-in-equipment gate tests each prop mesh as an oriented box (2026-11-24; a world box flagged hair resting ON the
        # leg press's tilted back pad). It must still fail when the hair really goes into that pad: drop the pad's hair supports.
        # (the pad now ends below the hair, so first restore the 60-unit headrest past the crown, then drop its hair supports)
        long = ("var backLen = lamB[1] - lamB[0] - 60, backPad = padAt(bp, (lamB[0] + lamB[1]) / 2 - 40, backLen, 170, x0);",
                "var backLen = lamB[1] - lamB[0] + 70, backPad = padAt(bp, (lamB[0] + lamB[1]) / 2 + 25, backLen, 170, x0);")
        code, out = patched_check({EXERCISES: [long, ("restsOnPad(fig, backPad, 30);", "")]}, ["leg-press", "--gender", "f"])
        self.assertEqual(code, 1, out)
        self.assertIn("into equipment", " | ".join(out[0]["failures"]))


@unittest.skipUnless(NODE, "node not installed")
class MotionFamily3Gates(unittest.TestCase):
    """Pulls and presses on the shoulder girdle (2026-11-25): each exercise check fails when the parameter that makes its cue true is
    broken in the source, the checker's girdle-aware reach gate and hand-orientation gate bite, and each mistake variant shows its mistake
    (and fails when its one parameter is undone)."""

    def test_exercise_checks_bite_on_broken_parameters(self):
        code, out = patched_check({EXERCISES: [
            # overhead press: the wrist no longer held straight above the elbow
            ("merge2(k, chestArm(S, sd, elbowDriven(S, sd, uc, f), uc));",
             "merge2(k, chestArm(S, sd, elbowDriven(S, sd, uc, f.clone().add(new V3m(0, 0, 0.5)).normalize()), uc));"),
            # pulldown and pull-up: no blade depression (the elbows do all the work) and the bar stops well short of the chest
            ("var PULL = { grip: 1.6, barDrop: 32, chestGap: 3, reach: 238, lead: 0.26, depress: -8, retract: -8 };",
             "var PULL = { grip: 1.6, barDrop: 32, chestGap: 30, reach: 238, lead: 0.26, depress: 0, retract: -8 };"),
            # pull-up: no balance solve (the body stays upright instead of hanging under the bar)
            ("th = Math.atan(-(c0[1] - f0[1]) / (c0[0] - f0[0])) / D2R;", "th = 0;"),
            # cable row: no retraction at the squeeze, and the reach asked 4 units past the arm from the MOVED joint (girdle-aware reach gate)
            ("reach: 238, protract: 10, retract: -15, rock: 0, seatGap: 30 };", "reach: 242, protract: 10, retract: 0, rock: 0, seatGap: 30 };"),
            # one-arm row: the elbow pulled straight up past the shoulder instead of toward the hip
            ("reach: 237, toHip: 70, ribZ: 18, handOut: 20, twist: 0 };", "reach: 237, toHip: -20, ribZ: 18, handOut: 20, twist: 0 };"),
        ]}, ["overhead-press", "lat-pulldown", "pull-up", "seated-cable-row", "one-arm-row"])
        self.assertEqual(code, 1)
        self.assertIsInstance(out, list, out)
        f = {r["id"]: " | ".join(r["failures"]) for r in out}
        self.assertIn("the forearm leans", f["overhead-press"])
        for msg in ("do not lead the elbows", "from the upper chest"):
            self.assertIn(msg, f["lat-pulldown"])
        self.assertIn("centre of mass swings", f["pull-up"])
        for msg in ("units back (cue: shoulder blades together", "IK hand target"):
            self.assertIn(msg, f["seated-cable-row"])
        self.assertIn("toward the hip", f["one-arm-row"])

    def test_hand_orientation_gate_bites_on_the_old_roll_wrap(self):
        # Without garS the pull-up's bar-alignment roll wraps at +-90 deg and the hand turns a half turn in one frame (the fist jumped
        # 7 units, an overhand grip went underhand); positions alone did not see it. The current pull-up passes the same gate.
        code, out = patched_check({EXERCISES: [("headF: -8 * smooth(e), gaxL: 1, gaxR: 1, garL: 60, garR: -60,", "headF: -8 * smooth(e), gaxL: 1, gaxR: 1,")]}, ["pull-up"])
        self.assertEqual(code, 1, out)
        self.assertIn("orientation snap", " | ".join(out[0]["failures"]))

    def test_reach_gate_measures_from_the_moved_joint(self):
        # The pre-girdle measure |hx, hy, hz| from the REST joint fails a correct overhead press (the joint rises about 14 units,
        # the arm is 238 from it): put it back and the press must fail; the current gate passes it (test above: a real overreach fails).
        old = "maxReachGap = Math.max(maxReachGap, Math.hypot(P('hx' + s), P('hy' + s), P('hz' + s)) - 239);"
        new = "maxReachGap = Math.max(maxReachGap, target.distanceTo(fig.bone['sh' + s].getWorldPosition(new THREE.Vector3())) - 239);"
        code, out = patched_check({"scripts/rig3d-check.js": [(new, old)]}, ["overhead-press"])
        self.assertEqual(code, 1, out)
        self.assertIn("IK hand target", " | ".join(out[0]["failures"]))
        code, out = patched_check({}, ["overhead-press"])
        self.assertEqual(code, 0, out)

    def test_mistake_variants_show_the_mistake(self):
        ids = ["overhead-press-arch", "lat-pulldown-swing", "pull-up-short", "seated-cable-row-rock", "one-arm-row-twist"]
        code, out = patched_check({}, ids)
        self.assertEqual(code, 0, out)
        ex = {r["id"]: r["exercise"] for r in out}
        self.assertGreaterEqual(ex["overhead-press-arch"]["lumbarExtMax"], 10)        # the lower back arches
        self.assertGreaterEqual(ex["overhead-press-arch"]["lockoutForwardMax"], 25)   # and the press finishes forward
        self.assertGreaterEqual(ex["lat-pulldown-swing"]["trunkMove"], 15)           # the trunk swings back
        self.assertGreaterEqual(ex["pull-up-short"]["straightArmsWorstRep"], 40)     # never a full hang
        self.assertGreaterEqual(ex["seated-cable-row-rock"]["trunkMove"], 15)        # the trunk rocks
        self.assertGreaterEqual(ex["one-arm-row-twist"]["trunkRollMove"], 12)        # the torso twists open
        self.assertLessEqual(ex["one-arm-row-twist"]["palmSlide"], 1.5)               # while the support hand stays planted
        code, out = patched_check({EXERCISES: [("merge(OHP, { arch: 16, fwd: 0.24 })", "merge(OHP, { arch: 0, fwd: 0 })"),
                                               ("merge(PULLDOWN, { swing: 24 })", "merge(PULLDOWN, { swing: 0 })"),
                                               ("merge(PULLUP, { bottomE: 0.5 })", "merge(PULLUP, { bottomE: 0 })"),
                                               ("merge(CROW, { rock: 28 })", "merge(CROW, { rock: 0 })"),
                                               ("merge(ROW1, { garR: 0, twist: 22 })", "merge(ROW1, { garR: 0, twist: 0 })")]}, ids)
        self.assertEqual(code, 1)
        f = {r["id"]: " | ".join(r["failures"]) for r in out}
        for i in ids:
            self.assertIn("the mistake is not visible", f[i], i)


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
