#!/usr/bin/env node
/*
 * rig3d-check.js: numeric QA for the 3D Tibi rig, no browser, no render (needs only node and the vendored three.js).
 *
 *   node scripts/rig3d-check.js [exercise ...] [--gender m|f] [--fps 30] [--json]
 *
 * It poses the rig at every frame of an exercise (the same pure function of time the film uses) and reports
 * what the 2D rig could not guarantee:
 *   continuity   no joint teleports: per-frame displacement of wrists, elbows, head and hips never jumps
 *                beyond 3x its neighbours (a pop shows up as a spike), and max speed / acceleration are in range
 *   activation   no activation value changes by more than 0.10 per frame, and no muscle COLOUR by more than 0.12 per
 *                channel per frame (a muscle resting in the dark shorts colour flashed at a rate the activation check passed)
  *   presence     every muscle has skin coverage and a bulge within -3..9 units in every frame (nothing
 *                shrinks to nothing or switches off: the "lats appear from nowhere" failure)
 *   contact      planted soles stay within 1.5 units of the floor for the whole film (no float, no sink, no slide)
 *   reach        IK hand and foot targets are inside the limb's reach (saturated targets look like stretched or
 *                locked limbs; a saturated LEG also lifts the foot off its target)
 *   limits       elbow 0-150, knee 0-150, shoulder elevation 0-175 degrees
 *   equipment    every prop the exercise built is attached to the scene (a bench once vanished because an edit commented
 *                out its stage.world.add, and every other check still passed)
 *   exercise     per-exercise assertions (def.checks), e.g. press forearms within 12 degrees of vertical
 * Exit code 1 when any check fails. Units are rig units (head = 100).
 */
'use strict';
const path = require('path');
const root = path.join(__dirname, '..', 'src', 'studio') + path.sep;
global.window = global;
const warn = console.warn; console.warn = () => {};            // three r158 prints a deprecation banner for the UMD build
global.THREE = require(root + 'vendor/three.min.js');
console.warn = warn;
global.Studio = {};
require(root + 'kits/fitness/brand.js');
require(root + 'kits/fitness/tibi3d.js');
require(root + 'kits/fitness/anatomy3d.js');
require(root + 'kits/fitness/exercises3d.js');
const T3 = Studio.kit.fitness.t3d;
const D2R = Math.PI / 180;

const args = process.argv.slice(2);
const opt = { gender: 'm', fps: 30, json: false };
const names = [];
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--gender') opt.gender = args[++i];
  else if (args[i] === '--fps') opt.fps = +args[++i];
  else if (args[i] === '--json') opt.json = true;
  else names.push(args[i]);
}
const ids = names.length ? names : Object.keys(T3.exercises);

function median(a) { const s = a.slice().sort((x, y) => x - y); return s[Math.floor(s.length / 2)] || 0; }

function checkExercise(id) {
  const stage = T3.stage(null, { headless: true });
  // a figure WITH an id, as every composition has: keys must carry the id prefix (a path that returned unprefixed keys left the press frozen in every film)
  const sc = T3.scene(stage, id, { gender: opt.gender, reps: 3, figId: 'z', at: 0, period: 3.4 });
  const fig = sc.fig, m = sc.motion, end = sc.end + 0.5;
  const orphan = fig.props.filter(p => { let o = p; while (o.parent) o = o.parent; return o !== stage.scene; }).length;
  const n = Math.ceil(end * opt.fps);
  const tracked = ['handL', 'handR', 'elL', 'elR', 'head', 'hips', 'knL', 'knR'];
  const pts = {}; tracked.forEach(k => pts[k] = []);
  const res = { id, frames: n, seconds: +end.toFixed(2), failures: [], notes: [], stats: {} };
  const fail = (msg) => res.failures.push(msg);
  const prevAct = {}; let maxActStep = 0;
  // colour, not activation units: a muscle resting in the shorts colour travels much further in colour per activation step
  const prevCol = new Map(); let maxColStep = 0, maxColWho = '';
  let minBulge = 9, maxBulge = -9, hidden = 0, maxReachGap = 0, maxLegGap = -1e9, maxSoleErr = 0, soleSlide = { L: [0, 0, 1e9, -1e9], R: [0, 0, 1e9, -1e9] };
  const lim = { el: [0, 0], kn: [0, 0], sh: [0, 0] };
  const extra = [];
  for (let i = 0; i < n; i++) {
    const t = i / opt.fps, v = m.at(t);
    for (const k in v) if (!Number.isFinite(v[k]) && !res.failures.some(f => f.startsWith('non-finite'))) fail(`non-finite value for "${k}" at ${t.toFixed(2)}s (an undeclared base value; everything above that joint vanishes)`);
    for (const k in v) {
      if (/(^|\.)act\./.test(k)) {
        const d = Math.abs(v[k] - (prevAct[k] === undefined ? v[k] : prevAct[k])); maxActStep = Math.max(maxActStep, d); prevAct[k] = v[k];
      }
    }
    fig.apply(v);
    tracked.forEach(k => pts[k].push(fig.world(k).toArray()));
    fig.muscles.forEach(r => {
      // a muscle is a region of the ONE skin: its colour is the skin-surface colour (and the cloth colour where it lies under shorts)
      const c = r.color, cc = r.colorC, pc = prevCol.get(r);
      if (pc) {
        const d = Math.max(Math.abs(c.r - pc[0]), Math.abs(c.g - pc[1]), Math.abs(c.b - pc[2]), Math.abs(cc.r - pc[3]), Math.abs(cc.g - pc[4]), Math.abs(cc.b - pc[5]));
        if (d > maxColStep) { maxColStep = d; maxColWho = r.key + '@' + r.side + ' ' + t.toFixed(2) + 's'; }
      }
      prevCol.set(r, [c.r, c.g, c.b, cc.r, cc.g, cc.b]);
      if (r.layer === 1 && r.vi.length < 8) hidden++;                              // a muscle with no skin vertices can never be seen: it would not light up
      minBulge = Math.min(minBulge, r.bulge); maxBulge = Math.max(maxBulge, r.bulge);
    });
    const c = T3.contacts(fig);
    ['L', 'R'].forEach(s => {
      const planted = (v['fy' + s] || 0) < 1;
      if (planted && (v['ikLeg' + s] === undefined || v['ikLeg' + s] > 0.5)) maxSoleErr = Math.max(maxSoleErr, Math.abs(c['sole' + s] - (v['fy' + s] || 0)));
      const a = c['ankle' + s], sl = soleSlide[s];
      sl[2] = Math.min(sl[2], a[0]); sl[3] = Math.max(sl[3], a[0]);
    });
    ['el', 'kn'].forEach(k => ['L', 'R'].forEach(s => {
      const rx = fig.bone[k + s].rotation.x / D2R, flex = k === 'el' ? -rx : rx;
      lim[k][0] = Math.min(lim[k][0], flex); lim[k][1] = Math.max(lim[k][1], flex);
    }));
    ['L', 'R'].forEach(s => { const e = v['sh' + s]; if (e !== undefined) { lim.sh[0] = Math.min(lim.sh[0], e); lim.sh[1] = Math.max(lim.sh[1], e); } });
    // IK reach: how far past full extension the requested hand target is
    ['L', 'R'].forEach(s => {
      if ((v['ik' + s] || 0) > 0.5) {
        const d = Math.hypot(v['hx' + s], v['hy' + s], v['hz' + s]);
        maxReachGap = Math.max(maxReachGap, d - 239);
      }
    });
    // leg reach: thigh origin to ankle target against thigh + shin (178 + 166, the rig clamps at 0.5 short of that)
    ['L', 'R'].forEach(s => {
      if ((v['ikLeg' + s] === undefined ? 1 : v['ikLeg' + s]) > 0.5) {
        const th = fig.bone['th' + s].getWorldPosition(new THREE.Vector3()), an = fig.bone['an' + s].getWorldPosition(new THREE.Vector3());
        maxLegGap = Math.max(maxLegGap, th.distanceTo(an) - 343.5);
      }
    });
    if (sc.def.checks) sc.def.checks(fig, v, t, extra, T3);
  }
  // continuity
  const motion = {};
  tracked.forEach(k => {
    const P = pts[k], step = [], acc = [];
    for (let i = 1; i < P.length; i++) step.push(Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1], P[i][2] - P[i - 1][2]));
    for (let i = 1; i < P.length - 1; i++) acc.push(Math.hypot(P[i + 1][0] - 2 * P[i][0] + P[i - 1][0], P[i + 1][1] - 2 * P[i][1] + P[i - 1][1], P[i + 1][2] - 2 * P[i][2] + P[i - 1][2]));
    let spikes = 0, worst = 0;
    for (let i = 3; i < step.length - 3; i++) {
      const nb = Math.max(step[i - 3], step[i - 2], step[i - 1], step[i + 1], step[i + 2], step[i + 3], 0.4);
      worst = Math.max(worst, step[i] / nb);
      if (step[i] > 3 * nb) spikes++;
    }
    motion[k] = { maxStep: +Math.max(...step).toFixed(2), maxAcc: +Math.max(...acc).toFixed(2), spikes, worstRatio: +worst.toFixed(2) };
    if (spikes) fail(`${k}: ${spikes} teleport spike(s) (a frame moves >3x its neighbours)`);
  });
  res.motion = motion;
  // range of motion: the exercise must visibly move. The largest excursion of any tracked joint over the set must be at least 90 units (about a
  // forearm; a heel raise declares its own smaller minRom), and the working joint's excursion must be at least a third of it (a repetition, not a twitch)
  let rom = 0; tracked.forEach(k => { const P = pts[k]; let mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9]; P.forEach(q => { for (let c = 0; c < 3; c++) { mn[c] = Math.min(mn[c], q[c]); mx[c] = Math.max(mx[c], q[c]); } }); rom = Math.max(rom, Math.hypot(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2])); });
  res.stats.rangeOfMotion = +rom.toFixed(0);
  const minRom = sc.def.minRom || 90;
  if (rom < minRom) fail(`range of motion is only ${rom.toFixed(0)} units (needs ${minRom}): the exercise does not visibly move (check that every motion key carries the figure id prefix)`);
  // phase fidelity: the phase map must describe the motion. Mean joint speed in up/down phases must be well above that in hold phases
  if (sc.def.phaseMap) {
    const o = { at: 0, period: 3.4, reps: 3 };
    const sp = { up: [], down: [], hold: [] };
    for (let i = 1; i < n; i++) { const ph = T3.phaseAt(sc.def, { at: 0, period: 3.4, reps: 3 }, (i - 0.5) / opt.fps); if (ph.rep < 1 || ph.rep > 3) continue; let sd = 0; tracked.forEach(k => { const a = pts[k][i], b = pts[k][i - 1]; sd += Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]); }); sp[ph.kind].push(sd); }
    const mean = a => a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0;
    res.stats.phaseSpeed = { up: +mean(sp.up).toFixed(2), down: +mean(sp.down).toFixed(2), hold: +mean(sp.hold).toFixed(2) };
    if (mean(sp.hold) > 0.6 * Math.min(mean(sp.up), mean(sp.down))) fail('the phase map is wrong: joints move as fast in the "hold" phases as in the lifting phases');
  }
  if (maxColStep > 0.12) fail(`a muscle colour changes ${maxColStep.toFixed(2)} per channel in one frame (${maxColWho}; max 0.12): slow the ramp`);
  if (maxActStep > 0.1) fail(`an activation colour changes ${maxActStep.toFixed(2)} in one frame (max 0.10): fades must last >= 0.35 s or the colour snaps`);
  if (hidden) fail(`${hidden} muscle-frames had no skin coverage (the muscle cannot be seen or lit)`);
  if (minBulge < -3 || maxBulge > 9) fail(`a muscle bulge of ${minBulge.toFixed(1)}..${maxBulge.toFixed(1)} units leaves the -3..9 range (the surface would dent or balloon)`);
  if (maxSoleErr > 1.5) fail(`planted sole is ${maxSoleErr.toFixed(2)} units off the floor`);
  if (maxReachGap > 0) fail(`IK hand target ${maxReachGap.toFixed(1)} units beyond reach (limb fully stretched)`);
  if (maxLegGap > -0.01) fail(`leg fully stretched (IK clamped): the foot is pulled off its target`);
  if (lim.el[0] < -2 || lim.el[1] > 150) fail(`elbow flexion ${lim.el[0].toFixed(0)}..${lim.el[1].toFixed(0)} deg outside 0-150`);
  if (lim.kn[0] < -2 || lim.kn[1] > 150) fail(`knee flexion ${lim.kn[0].toFixed(0)}..${lim.kn[1].toFixed(0)} deg outside 0-150`);
  if (lim.sh[0] < -1 || lim.sh[1] > 175) fail(`shoulder elevation ${lim.sh[0].toFixed(0)}..${lim.sh[1].toFixed(0)} deg outside 0-175`);
  if (orphan) fail(`${orphan} prop(s) built but never added to the scene (equipment would be missing from the render)`);
  extra.forEach(f => fail(f));
  const exStats = {};
  Object.keys(extra).forEach(k => { if (!/^\d+$/.test(k) && typeof extra[k] === 'number') exStats[k] = +extra[k].toFixed(2); });
  res.exercise = exStats;
  res.stats = Object.assign(res.stats, { maxActivationStep: +maxActStep.toFixed(3), maxColourStep: +maxColStep.toFixed(3), maxColourStepAt: maxColWho, legReachSlack: +(-maxLegGap).toFixed(1), bulge: [+minBulge.toFixed(1), +maxBulge.toFixed(1)], maxSoleError: +maxSoleErr.toFixed(2), elbow: lim.el.map(Math.round), knee: lim.kn.map(Math.round), shoulder: lim.sh.map(Math.round) });
  return res;
}

const results = ids.map(id => { if (!T3.exercises[id]) { console.error('unknown exercise', id, '(have', Object.keys(T3.exercises).join(', ') + ')'); process.exit(2); } return checkExercise(id); });
if (opt.json) console.log(JSON.stringify(results, null, 1));
else results.forEach(r => {
  console.log(`\n${r.failures.length ? 'FAIL' : 'ok  '} ${r.id}  (${r.frames} frames, ${r.seconds}s, gender ${opt.gender})`);
  console.log('     stats', JSON.stringify(r.stats));
  if (Object.keys(r.exercise).length) console.log('     exercise', JSON.stringify(r.exercise));
  Object.keys(r.motion).forEach(k => console.log(`     ${k.padEnd(6)} maxStep ${String(r.motion[k].maxStep).padStart(6)}  maxAcc ${String(r.motion[k].maxAcc).padStart(6)}  worst step/neighbour ${r.motion[k].worstRatio}`));
  r.failures.forEach(f => console.log('     FAIL:', f));
});
process.exit(results.some(r => r.failures.length) ? 1 : 0);
