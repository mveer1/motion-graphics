#!/usr/bin/env node
/*
 * rig3d-check.js: numeric QA for the 3D Tibi rig, no browser, no render (needs only node and the vendored three.js).
 *
 *   node scripts/rig3d-check.js [exercise ...] [--gender m|f] [--profile legacy|distance] [--fps 30] [--json]
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
 *   exercise     per-exercise assertions (def.checks), e.g. press forearms within 12 degrees of vertical, the press back resting on the
 *                pad with a natural arch (glutes, shoulder blades and head on it, lower back 8-30 units off it)
 *   framing      (distance profile) every shot, fitted on a 720x1280 stage by T3.fitScene's own samples, keeps the posed body and
 *                equipment in frame at 8 fps between those samples (a NaN fit fails)
 *   ponytail     (female) the tail never sinks into the neck, back or shoulders (1.0) or into equipment (1.5), and the same t after
 *                different seek histories gives the identical tail transform
 * Cost (2026-11-24, Windows): most of the run is fig.apply itself (anatomy3d.js body.update: the hip delta mush and the posed normals,
 * about 60 ms per frame). The framing check builds each exercise once (it built two scenes per shot until 2026-11-24) and the ponytail
 * body search uses a 30-unit grid; both give identical results to the old code (checked on five exercises, female, JSON equal).
 * Rig-wide (with the full suite, or by name):
 *   foot-roll    heel rocker keeps the heel planted, a deep heel lift rolls onto the toe tip at the toe-joint limit, tf rolls the contact
 *                to the tip, and the sole's underside is one surface with no gap and no kink (max 14 deg between 3-unit stations)
 *   ponytail-follow-through   (female suite) the tail lags a head turn, swings past rest after it stops, settles, and answers a nod
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
const opt = { gender: 'm', profileSampling: 'distance', fps: 30, json: false };
const names = [];
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--gender') opt.gender = args[++i];
  else if (args[i] === '--profile') opt.profileSampling = args[++i];
  else if (args[i] === '--fps') opt.fps = +args[++i];
  else if (args[i] === '--json') opt.json = true;
  else names.push(args[i]);
}
const GLOBAL = ['foot-roll', 'ponytail-follow-through'];
const ids = names.length ? names.filter(n => GLOBAL.indexOf(n) < 0) : Object.keys(T3.exercises);
const globals = names.length ? names.filter(n => GLOBAL.indexOf(n) >= 0) : GLOBAL;

function median(a) { const s = a.slice().sort((x, y) => x - y); return s[Math.floor(s.length / 2)] || 0; }

function checkExercise(id) {
  const stage = T3.stage(null, { headless: true });
  // a figure WITH an id, as every composition has: keys must carry the id prefix (a path that returned unprefixed keys left the press frozen in every film)
  const sc = T3.scene(stage, id, { gender: opt.gender, reps: 3, figId: 'z', at: 0, period: 3.4, profileSampling: opt.profileSampling });
  const fig = sc.fig, m = sc.motion, end = sc.end + 0.5;
  const orphan = fig.props.filter(p => { let o = p; while (o.parent) o = o.parent; return o !== stage.scene; }).length;
  const n = Math.ceil(end * opt.fps);
  // def.track adds joints that carry an exercise's motion when none of the defaults move (a knee machine moves only the shin)
  const tracked = ['handL', 'handR', 'elL', 'elR', 'head', 'hips', 'knL', 'knR'].concat(sc.def.track || []);
  const pts = {}; tracked.forEach(k => pts[k] = []);
  const res = { id, profileSampling: opt.profileSampling, frames: n, seconds: +end.toFixed(2), failures: [], notes: [], stats: {} };
  const fail = (msg) => res.failures.push(msg);
  const prevAct = {}; let maxActStep = 0;
  // colour, not activation units: a muscle resting in the shorts colour travels much further in colour per activation step
  const prevCol = new Map(); let maxColStep = 0, maxColWho = '';
  const previousSkin = opt.profileSampling === 'distance' ?
    { color: new Float32Array(fig.body.geo.getAttribute('color').array.length),
      colorC: new Float32Array(fig.body.geo.getAttribute('colorC').array.length) } : null;
  let maxSkinColourStep = 0;
  let minBulge = 9, maxBulge = -9, hidden = 0, maxReachGap = 0, maxLegGap = -1e9, maxSoleErr = 0, soleSlide = { L: [0, 0, 1e9, -1e9], R: [0, 0, 1e9, -1e9] };
  const lim = { el: [0, 0], kn: [0, 0], sh: [0, 0] };
  const extra = [];
  const ponyStats = { body: -Infinity, props: -Infinity, theta: [Infinity, -Infinity], tilt: 0, gravity: 0, lateral: 0 }, ponyTip = [];
  // rest glenohumeral joints in the chest frame (the neutral stance is below the girdle's onset, so the girdle bones sit at rest)
  fig.apply({});
  const restGH = { L: fig.bone.gdL.position.clone(), R: fig.bone.gdR.position.clone() };
  const handQ = { L: [], R: [] };
  for (let i = 0; i < n; i++) {
    const t = i / opt.fps, v = m.at(t);
    // pose keys carry the figure id ('z.'): read them through it (unprefixed reads silently skipped the reach, shoulder and lifted-foot logic)
    const P = k => v['z.' + k] !== undefined ? v['z.' + k] : v[k];
    for (const k in v) if (!Number.isFinite(v[k]) && !res.failures.some(f => f.startsWith('non-finite'))) fail(`non-finite value for "${k}" at ${t.toFixed(2)}s (an undeclared base value; everything above that joint vanishes)`);
    for (const k in v) {
      if (/(^|\.)act\./.test(k)) {
        const d = Math.abs(v[k] - (prevAct[k] === undefined ? v[k] : prevAct[k])); maxActStep = Math.max(maxActStep, d); prevAct[k] = v[k];
      }
    }
    fig.apply(v);
    ['L', 'R'].forEach(s => handQ[s].push(new THREE.Quaternion().setFromRotationMatrix(fig.bone['hand' + s].matrixWorld)));
    if (previousSkin) {
      for (const name of ['color', 'colorC']) {
        const current = fig.body.geo.getAttribute(name).array, previous = previousSkin[name];
        if (i) for (let k = 0; k < current.length; k++) maxSkinColourStep = Math.max(maxSkinColourStep, Math.abs(current[k] - previous[k]));
        previous.set(current);
      }
    }
    tracked.forEach(k => pts[k].push(fig.world(k).toArray()));
    if (fig.pony) ponyTip.push(T3.PONY.rest.clone().multiplyScalar(T3.PONY.tipLen).applyMatrix4(fig.pony.tip.matrixWorld).toArray());   // the free end's tip
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
      const planted = (P('fy' + s) || 0) < 1;
      if (planted && (P('ikLeg' + s) === undefined || P('ikLeg' + s) > 0.5)) maxSoleErr = Math.max(maxSoleErr, Math.abs(c['sole' + s] - (P('fy' + s) || 0)));
      const a = c['ankle' + s], sl = soleSlide[s];
      sl[2] = Math.min(sl[2], a[0]); sl[3] = Math.max(sl[3], a[0]);
    });
    ['el', 'kn'].forEach(k => ['L', 'R'].forEach(s => {
      const rx = fig.bone[k + s].rotation.x / D2R, flex = k === 'el' ? -rx : rx;
      lim[k][0] = Math.min(lim[k][0], flex); lim[k][1] = Math.max(lim[k][1], flex);
    }));
    ['L', 'R'].forEach(s => { const e = (P('ik' + s) || 0) > 0.5 ? undefined : P('sh' + s); if (e !== undefined) { lim.sh[0] = Math.min(lim.sh[0], e); lim.sh[1] = Math.max(lim.sh[1], e); } });
    // IK reach: how far past full extension the requested hand target is, from the joint where the girdle PUT it. The target is an
    // offset from the rest joint (world axes, or chest axes with ikcS); since Tibi 0.8.0 the joint moves (up to 15 units overhead, away
    // from the hand when a blade is depressed or retracted), so |hx, hy, hz| alone is wrong both ways (2026-11-25)
    ['L', 'R'].forEach(s => {
      if ((P('ik' + s) || 0) > 0.5) {
        const chest = fig.bone.chest.matrixWorld, t = new THREE.Vector3(P('hx' + s), P('hy' + s), P('hz' + s));
        if ((P('ikc' + s) || 0) > 0.5) t.applyQuaternion(new THREE.Quaternion().setFromRotationMatrix(chest));
        const target = restGH[s].clone().applyMatrix4(chest).add(t);
        maxReachGap = Math.max(maxReachGap, target.distanceTo(fig.bone['sh' + s].getWorldPosition(new THREE.Vector3())) - 239);
      }
    });
    // leg reach: thigh origin to ankle target against thigh + shin (178 + 166, the rig clamps at 0.5 short of that)
    ['L', 'R'].forEach(s => {
      if ((P('ikLeg' + s) === undefined ? 1 : P('ikLeg' + s)) > 0.5) {
        const th = fig.bone['th' + s].getWorldPosition(new THREE.Vector3()), an = fig.bone['an' + s].getWorldPosition(new THREE.Vector3());
        maxLegGap = Math.max(maxLegGap, th.distanceTo(an) - 343.5);
      }
    });
    if (sc.def.checks) sc.def.checks(fig, v, t, extra, T3);
    if (fig.pony && i % 6 === 0) {
      const pen = ponyIntrusion(fig);
      ponyStats.body = Math.max(ponyStats.body, pen.body); ponyStats.props = Math.max(ponyStats.props, pen.props);
      ponyStats.theta = [Math.min(ponyStats.theta[0], fig.pony.tail.userData.theta), Math.max(ponyStats.theta[1], fig.pony.tail.userData.theta)];
    }
    if (fig.pony) {
      const h = ponyHang(fig);
      if (h.upright) ponyStats.tilt = Math.max(ponyStats.tilt, Math.abs(h.tilt));
      if (h.faceDown && !h.supported) { ponyStats.gravity = Math.max(ponyStats.gravity, h.gravity); ponyStats.lateral = Math.max(ponyStats.lateral, h.lateral); }
    }
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
  // hand orientation: positions alone missed a held bar's hand rolling a half turn in one frame (the bar-alignment roll wrapping at
  // +-90 deg, 2026-11-25): the hand's world rotation per frame must not spike beyond 3x its neighbours (and 6 deg)
  ['L', 'R'].forEach(s => {
    const Q = handQ[s], step = [];
    for (let i = 1; i < Q.length; i++) step.push(Q[i].angleTo(Q[i - 1]) / D2R);
    let spikes = 0, worst = 0;
    for (let i = 3; i < step.length - 3; i++) {
      const nb = Math.max(step[i - 3], step[i - 2], step[i - 1], step[i + 1], step[i + 2], step[i + 3], 2);
      worst = Math.max(worst, step[i] / nb);
      if (step[i] > 3 * nb && step[i] > 6) spikes++;
    }
    motion['handTurn' + s] = { maxStep: +Math.max(0, ...step).toFixed(2), maxAcc: 0, spikes, worstRatio: +worst.toFixed(2) };
    if (spikes) fail(`hand${s}: ${spikes} orientation snap(s) (the hand turns >3x its neighbours in one frame: a flipped grip)`);
  });
  if (ponyTip.length) {
    // the tail tip moves smoothly too: no frame jumps beyond 3x its neighbours (a support or limit that flips sides would pop)
    const step = []; for (let i = 1; i < ponyTip.length; i++) step.push(Math.hypot(ponyTip[i][0] - ponyTip[i - 1][0], ponyTip[i][1] - ponyTip[i - 1][1], ponyTip[i][2] - ponyTip[i - 1][2]));
    let spikes = 0, worst = 0;
    for (let i = 3; i < step.length - 3; i++) { const nb = Math.max(step[i - 3], step[i - 2], step[i - 1], step[i + 1], step[i + 2], step[i + 3], 0.4); worst = Math.max(worst, step[i] / nb); if (step[i] > 3 * nb) spikes++; }
    res.motion.ponyTip = { maxStep: +Math.max(...step).toFixed(2), maxAcc: 0, spikes, worstRatio: +worst.toFixed(2) };
    if (spikes) fail(`ponytail tip: ${spikes} teleport spike(s)`);
  }
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
  if (maxSkinColourStep > 0.12) fail(`composited skin colour changes ${maxSkinColourStep.toFixed(2)} per channel in one frame (max 0.12)`);
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
  res.stats = Object.assign(res.stats, { maxActivationStep: +maxActStep.toFixed(3), maxColourStep: +maxColStep.toFixed(3), maxSkinColourStep: +maxSkinColourStep.toFixed(3), maxColourStepAt: maxColWho, legReachSlack: +(-maxLegGap).toFixed(1), bulge: [+minBulge.toFixed(1), +maxBulge.toFixed(1)], maxSoleError: +maxSoleErr.toFixed(2), elbow: lim.el.map(Math.round), knee: lim.kn.map(Math.round), shoulder: lim.sh.map(Math.round) });
  const toeAngles = () => ['L', 'R'].map(side => fig.bone['an' + side].children.find(c => c.isGroup).rotation.x);
  const directLegs = { 'z.ikLegL': 0, 'z.ikLegR': 0 };
  fig.apply({});
  fig.apply(directLegs);
  const toeRest = toeAngles();
  fig.apply({ 'z.hlL': 32, 'z.hlR': 24 });
  fig.apply(directLegs);
  const toeDelta = Math.max(...toeAngles().map((value, i) => Math.abs(value - toeRest[i])));
  res.stats.directLegSeekDelta = toeDelta;
  if (toeDelta > 0) fail(`toe rotation retains ${toeDelta} radians of an earlier heel lift after an IK-to-FK seek`);
  if (fig.pony) {
    res.stats.ponytail = { bodyIntrusion: +Math.max(-99, ponyStats.body).toFixed(2), propIntrusion: +Math.max(0, ponyStats.props).toFixed(2), theta: ponyStats.theta.map(x => +x.toFixed(1)) };
    if (ponyStats.body > 1.0) fail(`ponytail sinks ${ponyStats.body.toFixed(1)} units into the neck, back or shoulders (max 1.0)`);
    if (ponyStats.props > 1.5) fail(`ponytail or knot sinks ${ponyStats.props.toFixed(1)} units into equipment (max 1.5)`);
    // the tail HANGS: upright, it barely tilts sideways (the 0.6.0 hang); face down and free (not resting on a pad or the floor), it
    // points within PONY_GRAVITY of straight down and its tip stays within PONY_LATERAL of the head's midplane (past the cheek, not out
    // like a flag). Limits: the hang target itself is 70% gravity + 30% the head-fixed rest direction (up to ~25 deg off gravity) plus
    // the deflection round the head (measured 13-36 deg on the 0.7.0 jointed tail; the 0.7.0 sliding tail: 64-69). The head's half-width
    // is 44 and the free end's radius 13.5: a tail hanging past the cheek has its tip about 58 from the midplane, so 66 allows 8 units of
    // air (measured 54-62; the sliding 0.7.0 flag: 71-72).
    Object.assign(res.stats.ponytail, { uprightTiltDeg: +ponyStats.tilt.toFixed(2), faceDownGravityDeg: +ponyStats.gravity.toFixed(1), faceDownLateral: +ponyStats.lateral.toFixed(1) });
    if (ponyStats.tilt > PONY_TILT) fail(`ponytail tilts ${ponyStats.tilt.toFixed(1)} deg sideways while upright (max ${PONY_TILT}; the 0.6.0 hang is straight)`);
    if (ponyStats.gravity > PONY_GRAVITY) fail(`ponytail points ${ponyStats.gravity.toFixed(0)} deg off straight down while face down (max ${PONY_GRAVITY}): it does not hang`);
    if (ponyStats.lateral > PONY_LATERAL) fail(`ponytail tip sticks out ${ponyStats.lateral.toFixed(0)} units from the head's midplane while face down (max ${PONY_LATERAL})`);
    // seek order: the same t after different seek histories gives the identical tail transform (the tail looks back along the motion,
    // it never carries state from the previous frame)
    const tailAt = () => { fig.root.updateMatrixWorld(true); return Array.from(fig.pony.tail.matrixWorld.elements).concat(Array.from(fig.pony.mount.matrixWorld.elements), Array.from(fig.pony.tip.matrixWorld.elements)); };
    let worstSeek = 0;
    for (const ts of [0.9, sc.end * 0.5, sc.end - 0.2]) {
      for (let k = 0; k <= Math.floor(ts * opt.fps); k++) fig.apply(m.at(k / opt.fps));
      fig.apply(m.at(ts));
      const a = tailAt();
      fig.apply(m.at(sc.end)); fig.apply(m.at(ts)); const b = tailAt();
      fig.apply(m.at(0)); fig.apply(m.at(ts * 0.37)); fig.apply(m.at(ts)); const c = tailAt();
      a.forEach((x, j) => { worstSeek = Math.max(worstSeek, Math.abs(x - b[j]), Math.abs(x - c[j])); });
    }
    res.stats.ponytail.seekOrderDelta = worstSeek;
    if (worstSeek > 0) fail(`ponytail transform depends on seek order (max element difference ${worstSeek})`);
  }
  if (opt.profileSampling === 'distance') checkFraming(id, res, fail);
  return res;
}

// Every shot, fitted on a portrait stage, must keep the posed body and equipment inside the frame at every sampled frame,
// not only at the fitter's own samples. The fixed def.camera is reported, not failed: films solve their own cameras.
// The motion does not depend on the shot, so the scene is built ONCE (reps 1, the exercise's own period) and the posed frame points are
// sampled once: the 8 fps check samples here, and the fitter's own samples recorded while T3.fitScene fits the first shot (whatever
// sampling it uses). Every other shot is fitted by the same stage.fit on those recorded points, so each fit is exactly what T3.fitScene
// would return for that shot; only the camera moves between shots.
// (Until 2026-11-24 each shot built two fresh scenes and re-posed the set four times: 10 figure builds per exercise, most of the run.)
function checkFraming(id, res, fail) {
  const W = 720, H = 1280, fps = 8, q = new THREE.Vector3(), def = T3.exercises[id];
  const stage = T3.stage(null, { headless: true, width: W, height: H });
  const sc = T3.scene(stage, id, { gender: opt.gender, reps: 1, profileSampling: opt.profileSampling });
  const checkPts = [];
  for (let i = 0, n = Math.ceil(sc.end * fps); i <= n; i++) { sc.fig.apply(sc.motion.at(i / fps)); Array.prototype.push.apply(checkPts, T3.framePoints(sc.fig, 8)); }
  sc.fig.apply(sc.motion.at(0));
  const c = stage.cam, cam0 = { az: c.az, el: c.el };
  const setShot = shot => {
    c.tx = def.camera.target.tx; c.ty = def.camera.target.ty; c.tz = def.camera.target.tz; c.dist = def.camera.dist; c.fov = def.camera.fov;
    c.az = def.shots[shot] ? def.shots[shot].az : cam0.az; c.el = def.shots[shot] ? def.shots[shot].el : cam0.el;
  };
  const out = () => {
    stage.place();
    let worst = 0;
    for (const p of checkPts) {
      q.copy(p).project(stage.camera);
      const x = (q.x * 0.5 + 0.5) * W, y = (1 - (q.y * 0.5 + 0.5)) * H;
      worst = Math.max(worst, -x, -y, x - W, y - H);
    }
    return worst;
  };
  let fitPts = null;
  res.stats.framing = {};
  Object.keys(def.shots).forEach(shot => {
    setShot(shot); const fixed = out();
    setShot(shot);
    let fit;
    if (!fitPts) {
      const fp = T3.framePoints; fitPts = [];
      T3.framePoints = function () { const r = fp.apply(this, arguments); Array.prototype.push.apply(fitPts, r); return r; };
      try { fit = T3.fitScene(stage, sc, { margin: 0.04 }); } finally { T3.framePoints = fp; }
    } else fit = stage.fit(fitPts, { margin: 0.04 });
    const fitted = out();
    res.stats.framing[shot] = { defaultCameraOutPx: +Math.max(0, fixed).toFixed(1), fittedOutPx: +Math.max(0, fitted).toFixed(1), fittedDist: Math.round(fit.dist) };
    if (!(fitted <= 0)) fail(`shot "${shot}": the fitted camera still loses ${fitted.toFixed(1)} px of body or equipment between its samples`);   // NaN fails too
  });
}

// ---------------------------------------------------------------- ponytail, foot roll and sole (runtime Tibi 0.6.0)
// gdL/gdR (shoulder girdle: scapula and clavicle, Tibi 0.8.0) and axL/axR own the skin over the shoulder top: about 1070 vertices per side
// that the clearance search skipped until 2026-11-24, so a tail through the top of the shoulder read as clear.
const BODY_BONES = ['neck', 'chest', 'spine', 'shL', 'shR', 'hips', 'gdL', 'gdR', 'axL', 'axR'];
const MTP_LIMIT = 45;                   // degrees of toe (metatarsophalangeal) extension a shoe may bend before the foot rolls onto the tip
/** Posed skin points with posed normals for the neck, trunk and shoulders: [x, y, z, nx, ny, nz]. */
function bodySurface(fig) {
  const skin = fig.body.skin, geo = skin.geometry, si = geo.getAttribute('skinIndex'), sw = geo.getAttribute('skinWeight');
  const pa = geo.getAttribute('position'), na = geo.getAttribute('normal'), bones = skin.skeleton.bones;
  fig.root.updateMatrixWorld(true); skin.skeleton.update();
  const mats = bones.map((b, i) => new THREE.Matrix4().multiplyMatrices(b.matrixWorld, skin.skeleton.boneInverses[i]));
  const want = bones.map(b => BODY_BONES.indexOf(b.name) >= 0), out = [];
  const M = new THREE.Matrix4(), v = new THREE.Vector3(), n = new THREE.Vector3(), N3 = new THREE.Matrix3();
  for (let i = 0; i < pa.count; i++) {
    let best = 0, bw = -1;
    for (let k = 0; k < 4; k++) { const w = sw.getComponent(i, k); if (w > bw) { bw = w; best = si.getComponent(i, k); } }
    if (!want[best]) continue;
    const e = M.elements; e.fill(0);
    for (let k = 0; k < 4; k++) { const w = sw.getComponent(i, k); if (!w) continue; const me = mats[si.getComponent(i, k)].elements; for (let j = 0; j < 16; j++) e[j] += w * me[j]; }
    M.premultiply(skin.bindMatrixInverse).multiply(skin.bindMatrix).premultiply(skin.matrixWorld);
    v.fromBufferAttribute(pa, i).applyMatrix4(M);
    n.fromBufferAttribute(na, i).applyMatrix3(N3.getNormalMatrix(M)).normalize();
    out.push([v.x, v.y, v.z, n.x, n.y, n.z]);
  }
  return out;
}
const PONY_TILT = 3, PONY_GRAVITY = 50, PONY_LATERAL = 66;
/**
 * The tail's hang against gravity: upright (the head's up axis within 35 deg of vertical) -> sideways tilt of the tail axis out of the
 * head's midplane (deg); face down (the face looks 30 deg or more below the horizon) -> angle between the tail axis and straight down,
 * and the tip's distance from the head's midplane. supported: the tail rests on a pad or the floor (the hair solver's own flag).
 */
function ponyHang(fig) {
  fig.root.updateMatrixWorld(true);
  const m = fig.bone.head.matrixWorld, up = new THREE.Vector3(0, 1, 0).transformDirection(m), face = new THREE.Vector3(0, 0, 1).transformDirection(m), side = new THREE.Vector3(1, 0, 0).transformDirection(m);
  const dir = g => T3.PONY.rest.clone().applyQuaternion(new THREE.Quaternion().setFromRotationMatrix(g.matrixWorld));
  const A = dir(fig.pony.tail), D = dir(fig.pony.tip);                                     // root piece and free end
  const tip = new THREE.Vector3().setFromMatrixPosition(fig.pony.tip.matrixWorld).addScaledVector(D, T3.PONY.tipLen);
  const centre = fig.point('head', 0, 54, 3);
  const tilt = v => Math.asin(Math.max(-1, Math.min(1, v.dot(side)))) / D2R;
  return { upright: up.y > Math.cos(35 * D2R), faceDown: -face.y >= 0.5, supported: !!fig.pony.tail.userData.supported || !!fig.pony.tip.userData.rested,
    tilt: Math.abs(tilt(A)) > Math.abs(tilt(D)) ? tilt(A) : tilt(D), gravity: Math.acos(Math.max(-1, Math.min(1, -D.y))) / D2R,
    lateral: Math.abs(tip.clone().sub(centre).dot(side)) };
}
/**
 * How deep the ponytail goes into the body (tail vertices behind the nearest neck/trunk/shoulder skin point, along its normal)
 * and into equipment (tail and knot vertices inside a prop mesh's box). Units; <= 0 means clear.
 */
function ponyIntrusion(fig) {
  const pts = bodySurface(fig), v = new THREE.Vector3(), lq = new THREE.Vector3();
  let body = -Infinity, props = -Infinity;
  // Each prop mesh is tested as its own oriented box (its geometry's bounding box in its local frame; depths in world units through the
  // mesh's scale). For an axis-aligned mesh this is the world box the check used before 2026-11-24; for a tilted pad (the leg press's
  // back pad) the world box also covered the air above the slanted face, so hair resting ON the pad read as 20 units "into" it.
  const boxes = [];
  fig.props.forEach(p => { p.updateWorldMatrix(true, true); p.traverse(o => {
    if (!o.isMesh) return;
    if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
    boxes.push({ inv: o.matrixWorld.clone().invert(), bb: o.geometry.boundingBox, s: new THREE.Vector3().setFromMatrixScale(o.matrixWorld) });
  }); });
  const visit = (group, f) => { group.updateMatrixWorld(true); group.children.forEach(m => { if (!m.isMesh) return; const pa = m.geometry.getAttribute('position'); for (let i = 0; i < pa.count; i++) f(v.fromBufferAttribute(pa, i).applyMatrix4(m.matrixWorld)); }); };
  const inProps = q => boxes.forEach(b => {
    lq.copy(q).applyMatrix4(b.inv);
    if (!b.bb.containsPoint(lq)) return;
    const m = b.bb.min, M = b.bb.max, s = b.s;
    props = Math.max(props, Math.min((lq.x - m.x) * s.x, (M.x - lq.x) * s.x, (lq.y - m.y) * s.y, (M.y - lq.y) * s.y, (lq.z - m.z) * s.z, (M.z - lq.z) * s.z));
  });
  // Only a nearest skin point closer than 30 units counts, so the search runs over a 30-unit grid (the 27 cells around the vertex hold
  // every point within 30). Candidates are scanned in the original point order with a strict "<", so the chosen point, and the result,
  // are identical to a scan over all points (2026-11-24: the full scan was about 12% of a female exercise's check).
  const G = 30, cells = new Map(), key = (a, b, c) => a + ',' + b + ',' + c;
  pts.forEach((p, i) => { const k = key(Math.floor(p[0] / G), Math.floor(p[1] / G), Math.floor(p[2] / G)); let l = cells.get(k); if (!l) cells.set(k, l = []); l.push(i); });
  [fig.pony.tail, fig.pony.tip].forEach(g => visit(g, q => {
    let bd = Infinity, bp = null;
    const cx = Math.floor(q.x / G), cy = Math.floor(q.y / G), cz = Math.floor(q.z / G), cand = [];
    for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) for (let c = -1; c <= 1; c++) { const l = cells.get(key(cx + a, cy + b, cz + c)); if (l) for (const i of l) cand.push(i); }
    cand.sort((x, y) => x - y);
    for (const i of cand) { const p = pts[i], d = (q.x - p[0]) ** 2 + (q.y - p[1]) ** 2 + (q.z - p[2]) ** 2; if (d < bd) { bd = d; bp = p; } }
    if (bp && bd < 900) body = Math.max(body, -((q.x - bp[0]) * bp[3] + (q.y - bp[1]) * bp[4] + (q.z - bp[2]) * bp[5]));
    inProps(q);
  }));
  visit(fig.pony.knot, inProps);
  return { body, props };
}

/**
 * Follow-through: a head turn and a nod, then holds. The tail must lag the head while it moves, swing past its rest hang after the
 * head stops, and settle; measured against the static hang of the same pose (the same dictionary without its motion history).
 * The 0.5.0 tail was a fixed function of trunk lean: zero lag, zero follow-through.
 */
function checkFollowThrough() {
  const res = { id: 'ponytail-follow-through', failures: [], stats: {} };
  const stage = T3.stage(null, { headless: true }), fig = stage.tibi({ gender: 'f', id: 'z', profileSampling: opt.profileSampling });
  const m = T3.motion();
  m.base({ 'z.headY': 0, 'z.neckF': 0 });
  m.to(0.5, 0.3, { 'z.headY': 45 }, 'power2.inOut');
  m.to(2.2, 0.3, { 'z.neckF': 30 }, 'power2.inOut');
  m.to(3.6, 0.3, { 'z.neckF': 0, 'z.headY': 0 }, 'power2.inOut');
  // the tail's hang in the HEAD frame, read from the posed objects (any tail rig, old or new): [pitch toward the back, side swing]
  const qh = new THREE.Quaternion(), qt = new THREE.Quaternion(), d = new THREE.Vector3();
  const hang = () => {
    fig.root.updateMatrixWorld(true);
    fig.bone.head.getWorldQuaternion(qh); fig.pony.tail.getWorldQuaternion(qt);
    d.copy(T3.PONY.rest).applyQuaternion(qt).applyQuaternion(qh.invert());
    return [Math.atan2(-d.z, -d.y) / D2R, Math.asin(Math.max(-1, Math.min(1, d.x))) / D2R];
  };
  const dev = t => {
    const v = m.at(t);
    fig.apply(Object.assign({}, v)); const st = hang();
    fig.apply(v); const dy = hang();
    return [dy[0] - st[0], dy[1] - st[1]];
  };
  const series = []; for (let i = 0; i <= 5.5 * 30; i++) series.push([i / 30].concat(dev(i / 30)));
  const mag = r => Math.hypot(r[1], r[2]);
  const win = (a, b) => series.filter(r => r[0] >= a && r[0] <= b);
  // turn: lag while moving; after the stop the side swing reverses sign (follow-through past the rest hang), then settles
  const lag = Math.max(...win(0.5, 0.8).map(mag)), lagSide = win(0.5, 0.8).reduce((a, r) => Math.abs(r[2]) > Math.abs(a) ? r[2] : a, 0);
  const over = Math.max(...win(0.8, 1.8).map(r => -Math.sign(lagSide) * r[2]));
  const settle = Math.max(...win(2.0, 2.2).map(mag));
  const nod = Math.max(...win(2.2, 3.2).map(mag)), end = Math.max(...win(5.2, 5.5).map(mag));
  res.stats = { lagDeg: +lag.toFixed(2), overshootDeg: +over.toFixed(2), settledDeg: +settle.toFixed(3), nodDeg: +nod.toFixed(2), restDeg: +end.toFixed(3) };
  if (lag < 3) res.failures.push(`ponytail does not lag a 45 deg head turn (max ${lag.toFixed(2)} deg from the static hang; needs 3)`);
  if (over < 1) res.failures.push(`ponytail has no follow-through after the head stops (swings ${over.toFixed(2)} deg past rest; needs 1)`);
  if (settle > 1 || end > 0.5) res.failures.push(`ponytail does not settle (${settle.toFixed(2)} deg 1.2 s after the turn, ${end.toFixed(2)} at rest)`);
  if (nod < 2) res.failures.push(`ponytail does not respond to a nod (${nod.toFixed(2)} deg)`);
  return res;
}

/**
 * Foot roll and the bending sole. Heel rocker (hl < 0) keeps the heel planted, a deep heel lift rolls onto the toe tip once the sole
 * bend reaches TOE_MAX, an explicit tf rolls the contact to the tip, and the sole's underside stays one smooth, unbroken surface:
 * cast rays up through it along the foot and no station between heel and tip may miss it or turn more than 14 deg from its neighbour.
 */
function checkFootRoll() {
  const res = { id: 'foot-roll', failures: [], stats: {} };
  const stage = T3.stage(null, { headless: true }), fig = stage.tibi({ gender: opt.gender, profileSampling: opt.profileSampling });
  const pose = (hl, tf) => { const r = T3.footRoll(hl, tf); fig.apply({ hlL: hl, tfL: tf, hlR: hl, tfR: tf, fyawL: 0, fyawR: 0, y: 372 + r.up, z: r.fwd }); return T3.contacts(fig); };
  const flat = pose(0, 0);
  const cases = [['heelStrike', -15, 0, 'heel'], ['heelLift', 36, 0, 'ball'], ['toeOff', 62, 0, 'tip'], ['tipRoll', 30, 14, 'tip']];
  cases.forEach(([name, hl, tf, pivot]) => {
    const c = pose(hl, tf), bend = -fig.toes.L.rotation.x / D2R;
    let drift, lift;
    if (pivot === 'heel') {
      const a = fig.bone.anL.matrixWorld, h = new THREE.Vector3(0, T3.HEEL.y, T3.HEEL.z).applyMatrix4(a);
      const h0 = (() => { pose(0, 0); return new THREE.Vector3(0, T3.HEEL.y, T3.HEEL.z).applyMatrix4(fig.bone.anL.matrixWorld); })();
      drift = Math.hypot(h.x - h0.x, h.z - h0.z); lift = h.y; pose(hl, tf);
      res.stats[name] = { heelDrift: +drift.toFixed(2), heelY: +lift.toFixed(2), tipY: +c.tipL[1].toFixed(1), bend: +bend.toFixed(1) };
      if (drift > 0.5 || Math.abs(lift) > 0.5) res.failures.push(`${name}: the heel slides ${drift.toFixed(1)} or leaves the floor by ${lift.toFixed(1)} (heel rocker)`);
      if (c.tipL[1] < 15) res.failures.push(`${name}: toes not up (${c.tipL[1].toFixed(1)})`);
    } else {
      const ref = pivot === 'ball' ? flat.ballL : flat.tipL, q = pivot === 'ball' ? c.ballL : c.tipL;
      drift = Math.hypot(q[0] - ref[0], q[2] - ref[2]); lift = q[1];
      res.stats[name] = { [pivot + 'Drift']: +drift.toFixed(2), [pivot + 'Y']: +lift.toFixed(2), bend: +bend.toFixed(1), sole: +c.soleL.toFixed(2) };
      if (drift > 0.5 || Math.abs(lift) > 0.5) res.failures.push(`${name}: the ${pivot} slides ${drift.toFixed(1)} or leaves the floor by ${lift.toFixed(1)}`);
      if (c.soleL < -0.5) res.failures.push(`${name}: part of the sole contact sinks ${(-c.soleL).toFixed(1)} below the floor`);
    }
    if (bend > MTP_LIMIT + 0.01) res.failures.push(`${name}: the sole bends ${bend.toFixed(0)} deg at the ball (toe joint limit ${MTP_LIMIT})`);
  });
  // the underside of the sole at bends up to 40 deg: one surface, no gap, no kink
  const soles = []; fig.bone.anL.traverse(o => { if (o.isMesh && o.name === 'sole') soles.push(o); });
  const ray = new THREE.Raycaster(), up = new THREE.Vector3(), o = new THREE.Vector3(), fwd = new THREE.Vector3();
  let worstTurn = 0, gaps = 0;
  [10, 24, 36, 40].forEach(hl => {
    pose(hl, 0); fig.root.updateMatrixWorld(true);
    const a = fig.bone.anL.matrixWorld, heel = new THREE.Vector3(0, -26, -22).applyMatrix4(a), tip = new THREE.Vector3(0, T3.TIP.y - T3.BALL.y, T3.TIP.z - T3.BALL.z - 4).applyMatrix4(fig.toes.L.matrixWorld);
    fwd.subVectors(tip, heel); fwd.y = 0; const len = fwd.length(); fwd.normalize();
    // rays across the foot's up axis (perpendicular to the floor line from heel to tip): the underside profile, station by station
    const prof = [];
    for (let s = 0; s <= len; s += 3) {
      o.copy(heel).addScaledVector(fwd, s); o.y = -200; ray.set(o, up.set(0, 1, 0)); ray.far = 400;
      const hit = ray.intersectObjects(soles, false)[0];
      if (!hit) { gaps++; continue; }
      prof.push([s, hit.point.y]);
    }
    for (let i = 2; i < prof.length; i++) {
      const s1 = Math.atan2(prof[i - 1][1] - prof[i - 2][1], prof[i - 1][0] - prof[i - 2][0]), s2 = Math.atan2(prof[i][1] - prof[i - 1][1], prof[i][0] - prof[i - 1][0]);
      worstTurn = Math.max(worstTurn, Math.abs(s2 - s1) / D2R);
    }
  });
  res.stats.sole = { pieces: soles.length, maxTurnDeg: +worstTurn.toFixed(1), gapStations: gaps };
  if (gaps) res.failures.push(`the sole has ${gaps} gap station(s) between heel and tip`);
  if (worstTurn > 14) res.failures.push(`the sole's underside kinks ${worstTurn.toFixed(0)} deg between neighbouring stations at the ball (a hinge, not a bend; max 14)`);
  return res;
}

const results = ids.map(id => { if (!T3.exercises[id]) { console.error('unknown exercise', id, '(have', Object.keys(T3.exercises).join(', ') + ')'); process.exit(2); } return checkExercise(id); });
if (globals.indexOf('foot-roll') >= 0) results.push(Object.assign({ exercise: {}, motion: {} }, checkFootRoll()));
// the follow-through needs the figure with the ponytail: it runs in the female suite, or by name
if (globals.indexOf('ponytail-follow-through') >= 0 && (opt.gender === 'f' || names.length)) results.push(Object.assign({ exercise: {}, motion: {} }, checkFollowThrough()));
if (opt.json) console.log(JSON.stringify(results, null, 1));
else results.forEach(r => {
  const head = r.frames ? `(${r.frames} frames, ${r.seconds}s, gender ${opt.gender})` : `(rig-wide, gender ${opt.gender})`;
  console.log(`\n${r.failures.length ? 'FAIL' : 'ok  '} ${r.id}  ${head}`);
  console.log('     stats', JSON.stringify(r.stats));
  if (Object.keys(r.exercise).length) console.log('     exercise', JSON.stringify(r.exercise));
  Object.keys(r.motion).forEach(k => console.log(`     ${k.padEnd(6)} maxStep ${String(r.motion[k].maxStep).padStart(6)}  maxAcc ${String(r.motion[k].maxAcc).padStart(6)}  worst step/neighbour ${r.motion[k].worstRatio}`));
  r.failures.forEach(f => console.log('     FAIL:', f));
});
process.exit(results.some(r => r.failures.length) ? 1 : 0);
