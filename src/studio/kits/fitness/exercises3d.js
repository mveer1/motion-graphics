/*
 * Motion Lab fitness kit - 3D exercise library for Tibi (src/studio/kits/fitness/exercises3d.js)
 * Needs tibi3d.js. Each exercise authors its motion as tracks on a T3.motion (pure functions of time),
 * builds its equipment from Tibi's own joints, and ships the camera that shows the movement best.
 *
 * Kinematics are CONCEPTUAL (authored key poses), never motion capture. Label them "illustrative".
 *
 * Authoring rules learned from the 2D rig's pops (see .claude/skills/fitness/references/motion-3d.md):
 *  - ONE continuous parameter set per movement. No art swaps, no visibility switches, no thresholds.
 *  - Reps are loops of key poses with eased moves AND short holds; eases differ going up and down.
 *  - Planted contacts (feet, a bench) are targets, not hand-tuned angles.
 *  - Activation is intensity 0..1 on muscles that always exist.
 */
(function (global) {
  'use strict';
  var Studio = global.Studio || (global.Studio = {});
  var F = Studio.kit.fitness, T3 = F && F.t3d;
  if (!T3) throw new Error('kits/fitness/exercises3d.js needs tibi3d.js loaded first');
  var X3 = T3.exercises = {};
  var EQ = T3.equipment;

  function sym(o) { var r = {}; for (var k in o) { r[k + 'L'] = o[k]; r[k + 'R'] = o[k]; } return r; }
  function merge() { var r = {}; for (var i = 0; i < arguments.length; i++) for (var k in arguments[i]) r[k] = arguments[i][k]; return r; }
  function pref(p, o) { if (!p) return o; var r = {}; for (var k in o) r[p + k] = o[k]; return r; }
  T3.sym = sym;
  /**
   * Activation envelope for a set: every muscle rises over 1.0 s as the set starts, dips to 75% around each rep boundary
   * (least load) and eases off over 1.2 s after the last rep. Fades are never shorter than ~0.3 s: a 0.2 s fade read as a
   * colour snap in the first 3D press (found by scripts/motion-continuity.py). peaks: {muscleKey: 0..1}.
   */
  function envelope(m, p, peaks, at, per, reps) {
    Object.keys(peaks).forEach(function (k) {
      var key = p + 'act.' + k, pk = peaks[k], v = {};
      m.base((v[key] = 0, v));
      var a = {}; a[key] = pk; m.to(at, 1.0, a, 'sine.inOut');      // 1.0 s: at 0.6 s a colour moved 0.17 per frame (a flash on dark cloth)
      for (var r = 1; r < reps; r++) {
        var lo = {}, hi = {}; lo[key] = pk * 0.75; hi[key] = pk;
        m.to(at + r * per - 0.3 * per, 0.3 * per, lo, 'sine.inOut');
        m.to(at + r * per, 0.3 * per, hi, 'sine.inOut');
      }
      var z = {}; z[key] = 0; m.to(at + reps * per - 0.1, 1.2, z, 'sine.inOut');
    });
  }
  T3.envelope = envelope;
  function norm3(v) { var l = Math.hypot(v[0], v[1], v[2]); return [v[0] / l, v[1] / l, v[2] / l]; }
  function slerp3(a, b, s) {
    var d = Math.max(-1, Math.min(1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2])), th = Math.acos(d), sn = Math.sin(th) || 1;
    var wa = Math.sin((1 - s) * th) / sn, wb = Math.sin(s * th) / sn;
    return [wa * a[0] + wb * b[0], wa * a[1] + wb * b[1], wa * a[2] + wb * b[2]];
  }
  function merge2(into, o) { for (var k in o) into[k] = o[k]; return into; }
  /** Register a bench's pad (and its top cap) as a surface the hair can rest on but never sink into (fig.supports). */
  function restsOn(fig, bench) {
    if (!fig.supports) return;
    bench.updateWorldMatrix(true, true);
    fig.supports.push(new THREE.Box3().setFromObject(bench.children[0]).union(new THREE.Box3().setFromObject(bench.children[1])));
  }
  T3.restsOn = restsOn;

  /**
   * Lowest posed skin point (world y) over the vertices whose strongest bone is one of `bones` and whose world position passes
   * `keep(v)` (e.g. "over the bench pad"). Reads the current pose; used to rest a body on a surface and by rig3d-check.
   */
  T3.skinLow = function (fig, bones, keep) {
    var skin = fig.body.skin, geo = skin.geometry, pa = geo.getAttribute('position');
    if (!fig._domBone) {
      var si = geo.getAttribute('skinIndex'), sw = geo.getAttribute('skinWeight'), dom = new Int16Array(pa.count);
      for (var i = 0; i < pa.count; i++) {
        var best = 0, bw = -1;
        for (var k = 0; k < 4; k++) { var w = sw.getComponent(i, k); if (w > bw) { bw = w; best = si.getComponent(i, k); } }
        dom[i] = best;
      }
      fig._domBone = dom;
    }
    var want = {}, names = skin.skeleton.bones.map(function (b) { return b.name; });
    names.forEach(function (n, i) { if (bones.indexOf(n) >= 0) want[i] = true; });
    fig.root.updateMatrixWorld(true); skin.skeleton.update();
    var v = new THREE.Vector3(), low = Infinity, at = null;
    for (var j = 0; j < pa.count; j++) {
      if (!want[fig._domBone[j]]) continue;
      v.fromBufferAttribute(pa, j); skin.applyBoneTransform(j, v); v.applyMatrix4(skin.matrixWorld);
      if (keep && !keep(v)) continue;
      if (v.y < low) { low = v.y; at = v.clone(); }
    }
    return { y: low, at: at };
  };
  /** The press bench pad footprint (world): over it the back rests, beyond it the head would hang. */
  function overPressBench(v) { return Math.abs(v.z) < 60 && v.x > -468 && v.x < 88; }
  T3.overPressBench = overPressBench;
  /**
   * Solve the arched supine pose: lean = -arch; the pelvis tilt (pitch -90 + a) that puts the glutes 1 unit deeper into the pad
   * than the shoulder blades, the height y that rests the shoulder blades 2.5 into it, and the neck flexion that rests the back of
   * the head 1 into it. Two passes, because the leg IK (feet planted) moves the glute skin a little with the height.
   */
  function solveArch(fig, p, base, top, arch) {
    var q = merge(base, { lean: -arch }), lows, held = fig.supports ? fig.supports.splice(0) : [];   // hair resting is not needed here
    function measure(a, y, nf) {
      q.pitch = -90 + a; q.y = y; q.neckF = nf;
      fig.apply(pref(p, q));
      return { glute: T3.skinLow(fig, ['hips'], overPressBench).y, back: T3.skinLow(fig, ['chest', 'neck'], overPressBench).y, head: T3.skinLow(fig, ['head'], overPressBench).y };
    }
    var a = 0, y = base.y, nf = 0;
    for (var pass = 0; pass < 2; pass++) {
      var lo = 0, hi = arch * 2;
      for (var i = 0; i < 16; i++) { a = (lo + hi) / 2; lows = measure(a, y, nf); if (lows.glute - lows.back > -1) lo = a; else hi = a; }
      a = (lo + hi) / 2; lows = measure(a, y, nf);
      y += (top - 2.5) - lows.back;
      lo = -10; hi = 40;
      for (i = 0; i < 16; i++) { nf = (lo + hi) / 2; lows = measure(a, y, nf); if (lows.head < top - 1) lo = nf; else hi = nf; }
      nf = (lo + hi) / 2;
    }
    if (fig.supports) Array.prototype.push.apply(fig.supports, held);
    fig.apply({});
    return { pitch: -90 + a, lean: -arch, y: y, neckF: nf };
  }
  T3.solveArch = solveArch;

  /*
   * PHASE MACHINE (2026-11-13). Every rep is a list of named phases as fractions of the rep period, in the SAME timing the exercise's
   * build() uses, so a HUD, a 2D comparison rig or a script can ask "what is the lifter doing at time t" without guessing:
   *   id:  setup | start | eccentric | end-range | concentric | lockout | reset      kind: 'down' (lengthening) | 'up' (shortening) | 'hold'
   * Some exercises have fewer phases (a calf raise has no lockout, a hip thrust starts at the bottom); each says so in its own phaseMap.
   * T3.phaseAt(def, {at, period, reps}, t) -> {rep (1-based, 0 before the set, reps+1 after), n, id, kind, label, k (0..1 inside the phase), cue}.
   */
  T3.phaseAt = function (def, o, t) {
    var per = o.period, n = o.reps, at = o.at || 0, map = def.phaseMap;
    if (t < at) return { rep: 0, n: n, id: 'setup', kind: 'hold', label: 'Set up', k: 0, cue: '' };
    var r = Math.floor((t - at) / per);
    if (r >= n) return { rep: n, n: n, id: 'reset', kind: 'hold', label: 'Reset', k: 1, cue: '' };
    var f = (t - at - r * per) / per;
    for (var i = 0; i < map.length; i++) if (f >= map[i].a && f < map[i].b) return { rep: r + 1, n: n, id: map[i].id, kind: map[i].kind, label: map[i].label, k: (f - map[i].a) / (map[i].b - map[i].a), cue: map[i].cue || '' };
    return { rep: r + 1, n: n, id: 'reset', kind: 'hold', label: 'Reset', k: 0, cue: '' };
  };
  /** The same map with absolute seconds for the first rep: lets a 2D rig or an editor snap its own moves to the 3D timing. */
  T3.phaseTimes = function (def, o, rep) {
    var t0 = (o.at || 0) + (rep || 0) * o.period;
    return def.phaseMap.map(function (p) { return { id: p.id, kind: p.kind, label: p.label, t0: t0 + p.a * o.period, t1: t0 + p.b * o.period }; });
  };
  /** True joint angle in degrees at b between a and c (names, functions of the figure, or Vector3): elbow flexion = 180 - this. */
  T3.pt = function (fig, p) { return typeof p === 'function' ? p(fig) : p && p.isVector3 ? p : fig.world(p); };       // a name, a function(fig) or a Vector3
  T3.jointAngle = function (fig, a, b, c) {
    var A = T3.pt(fig, a), B = T3.pt(fig, b), C = T3.pt(fig, c), u = A.clone().sub(B).normalize(), v = C.clone().sub(B).normalize();
    return Math.acos(Math.max(-1, Math.min(1, u.dot(v)))) * 180 / Math.PI;
  };
  /** Positions of a world point over [t0, t1] (a movement trail). Samples the pure-function pose, then restores it. */
  T3.trail = function (fig, motion, pointFn, t0, t1, dt) {
    var pts = [], i;
    for (var t = t0; t <= t1 + 1e-6; t += dt || 0.05) { fig.apply(motion.at(t)); pts.push(pointFn(fig).clone()); }
    fig.apply(motion.at(t0));
    return pts;
  };

  // ---------------------------------------------------------------- standing dumbbell curl
  X3.curl = {
    id: 'curl', name: 'Standing dumbbell curl', knowledge: 'dumbbell-curl', acts: { biceps: 3, brach: 2, flexor: 1, 'delt-front': 1, abs: 1 },
    phaseMap: [{ id: 'start', kind: 'hold', label: 'Start', a: 0, b: 0.04, cue: 'Elbows by the ribs' }, { id: 'concentric', kind: 'up', label: 'Curl up', a: 0.04, b: 0.36, cue: 'Only the forearm moves' },
      { id: 'end-range', kind: 'hold', label: 'Squeeze', a: 0.36, b: 0.46, cue: 'Squeeze the biceps' }, { id: 'eccentric', kind: 'down', label: 'Lower slowly', a: 0.46, b: 0.88, cue: 'Control the way down' },
      { id: 'reset', kind: 'hold', label: 'Straight arms', a: 0.88, b: 1.0, cue: 'Full extension' }],
    shots: { front: { az: 12, el: 8 }, three: { az: 38, el: 10 }, side: { az: 90, el: 6 }, back: { az: 180, el: 8 } },
    build: function (stage, fig, m, o) {
      o = o || {};
      var p = fig.id ? fig.id + '.' : '', at = o.at || 0, reps = o.reps || 3, per = o.period || 3.2;
      var x0 = o.x || 0, z0 = o.z || 0;
      var dbs = [EQ.dumbbell(1), EQ.dumbbell(1)]; fig.hold('L', dbs[0]); fig.hold('R', dbs[1]);
      fig.roles(X3.curl.acts);
      var stance = { fxL: x0 + 50, fzL: z0, fyawL: 8, fxR: x0 - 50, fzR: z0, fyawR: -8, x: x0, y: 370, z: z0 };
      var low = merge(sym({ sh: 6, pl: 66, el: 6, wr: -4 }), { lean: 0 });
      var high = merge(sym({ sh: 15, pl: 82, el: 144, wr: 14 }), { lean: -3 });
      m.base(pref(p, merge(stance, low)));
      var end = m.cycle(at, per, reps, [
        { at: 0.04, v: null },
        { at: 0.36, v: pref(p, high), ease: 'power1.inOut' },
        { at: 0.46, v: null },
        { at: 0.88, v: pref(p, low), ease: 'sine.inOut' },
        { at: 1.0, v: null }
      ]);
      // activation: ramps in with the lift, holds through the squeeze, eases off on the way down
      envelope(m, p, { biceps: 1, brach: 0.85, flexor: 0.5, 'delt-front': 0.45, abs: 0.4 }, at, per, reps);
      return end;
    },
    camera: { target: { tx: 0, ty: 420, tz: 0 }, dist: 2050, fov: 26 }
  };

  // ---------------------------------------------------------------- supine dumbbell bench press
  X3.press = {
    id: 'press', name: 'Dumbbell bench press', knowledge: 'dumbbell-bench-press',
    phaseMap: [{ id: 'lockout', kind: 'hold', label: 'Lockout', a: 0, b: 0.04, cue: 'Wrists over elbows' }, { id: 'eccentric', kind: 'down', label: 'Lower', a: 0.04, b: 0.46, cue: 'Forearms stay vertical' },
      { id: 'end-range', kind: 'hold', label: 'Bottom', a: 0.46, b: 0.52, cue: 'Feel the chest stretch' }, { id: 'concentric', kind: 'up', label: 'Press', a: 0.52, b: 0.90, cue: 'Drive the dumbbells up' },
      { id: 'lockout2', kind: 'hold', label: 'Lockout', a: 0.90, b: 1.0, cue: 'Shoulder blades stay down' }],
    acts: { pec: 3, triceps: 2, 'delt-front': 2, serratus: 1, abs: 1 },
    shots: { three: { az: 38, el: 24 }, side: { az: 0, el: 8 }, foot: { az: 90, el: 14 }, headEnd: { az: 270, el: 16 }, above: { az: 20, el: 68 } },
    build: function (stage, fig, m, o) {
      o = o || {};
      var p = fig.id ? fig.id + '.' : '', at = o.at || 0, reps = o.reps || 3, per = o.period || 3.4;
      var benchTop = 175;
      var bench = EQ.bench({ x: -190, z: 0, y: benchTop, w: 135, l: 560, yaw: 90 }); stage.world.add(bench); fig.props.push(bench); restsOn(fig, bench);
      var dbs = [EQ.dumbbell(1), EQ.dumbbell(1)]; fig.hold('L', dbs[0]); fig.hold('R', dbs[1]);
      fig.roles(X3.press.acts);
      // lying on the back, head to -x: pitch -90 puts the front up, yaw 90 turns the head toward -x. The lifter's left side is world -z.
      var lie = { x: 0, y: benchTop + 47, z: 0, pitch: -90, yaw: 90, lean: 0,
        fxL: 150, fzL: -62, fyawL: 90, fxR: 150, fzR: 62, fyawR: 90, kfL: 14, kfR: 14,
        ikL: 1, ikR: 1, gazL: 1, gazR: 1, wrL: 0, wrR: 0 };
      // The press path is built, not interpolated: the ELBOW sweeps an arc around the shoulder (from 45 deg off the torso line, just
      // below the bench, to nearly overhead) and the wrist is held exactly one forearm above it, so the forearm is vertical at every
      // frame and the dumbbell path is the natural arc. The elbow is also the IK pole. Hand targets are world offsets from the shoulder.
      var uB = norm3([0.68, -0.27, 0.68]), uT = norm3([0.07, 0.99, 0.12]);
      function arm(s) {                                    // s: 0 = bottom, 1 = lockout
        var u = slerp3(uB, uT, s), r = {};
        ['L', 'R'].forEach(function (sd) {
          var z = sd === 'L' ? -u[2] : u[2];                 // lifter's left is world -z
          r['hx' + sd] = 134 * u[0]; r['hy' + sd] = 134 * u[1] + 102; r['hz' + sd] = 134 * z;
          r['px' + sd] = u[0]; r['py' + sd] = u[1]; r['pz' + sd] = z;
        });
        return r;
      }
      // A modest, natural arch (illustrative, not a powerlifting arch): the spine extends by `arch` degrees (lean < 0) and the pelvis
      // tilts forward by the angle that keeps the glutes and the shoulder blades both on the pad, so the lower back lifts off it.
      // Solved from the posed skin (glutes 3.5, shoulder blades 2.5 and the back of the head 1 unit into the pad), not by eye.
      var arch = o.arch === undefined ? 22 : o.arch;
      if (arch) merge2(lie, solveArch(fig, p, merge(lie, arm(1)), benchTop, arch));
      m.base(pref(p, merge(lie, arm(1))));
      var end = at;
      for (var r0 = 0; r0 < reps; r0++) {
        var t0 = at + r0 * per;
        m.path(t0 + 0.04 * per, 0.42 * per, function (e) { return pref(p, arm(1 - e)); }, 'sine.inOut');      // controlled lowering (keys carry the figure id, or a figure with an id never moves)
        m.path(t0 + 0.52 * per, 0.38 * per, function (e) { return pref(p, arm(e)); }, 'power2.inOut');          // drive up
        end = t0 + per;
      }
      envelope(m, p, { pec: 1, triceps: 0.9, 'delt-front': 0.6, serratus: 0.5, abs: 0.4 }, at, per, reps);
      return end;
    },
    camera: { target: { tx: -120, ty: 260, tz: 0 }, dist: 1750, fov: 28 },
    // numeric assertions run by scripts/rig3d-check.js: forearms stay within 12 degrees of vertical (coaching cue: stacked wrist over elbow);
    // the body rests on the pad with a natural arch: glutes, shoulder blades and the back of the head on it (within 6 units into the
    // pad, never more than 1.5 above it) and the lower back lifted 8-30 units off it (the flat 0.5.0 back: lower back 2.3 (m) / 5.0 (f)
    // off the pad, upper back floating 1.7 / 4.2 and the head 5.1 / 4.0 above it)
    checks: function (fig, v, t, out) {
      ['L', 'R'].forEach(function (s) {
        var e = fig.world('el' + s), h = fig.world('hand' + s);
        var ang = Math.acos(Math.max(-1, Math.min(1, (h.y - e.y) / (h.distanceTo(e) || 1)))) * 180 / Math.PI;
        out.maxTilt = Math.max(out.maxTilt || 0, ang);
        var tag = 'forearm tilt exceeds 12 deg from vertical (cue: wrist stacked over elbow)';
        if (ang > 12 && out.indexOf(tag) < 0) out.push(tag);
      });
      benchRest(fig, out);
    }
  };
  /** Glutes, shoulder blades and head rest on the press bench pad (-6..+1.5) with a natural arch (lower back 8-30 off the pad). */
  function benchRest(fig, out) {
    var top = 175, rest = [['glutes', ['hips']], ['shoulder blades', ['chest', 'neck']], ['head', ['head']]];
    rest.forEach(function (r) {
      var d = T3.skinLow(fig, r[1], overPressBench).y - top, k = r[0] === 'glutes' ? 'gluteRest' : r[0] === 'head' ? 'headRest' : 'backRest';
      out[k] = out[k] === undefined ? d : (Math.abs(d) > Math.abs(out[k]) ? d : out[k]);
      var tag = 'bench press: the ' + r[0] + ' do not rest on the pad (' + d.toFixed(1) + ' units; -6..+1.5)';
      if ((d < -6 || d > 1.5) && !out.some(function (x) { return x.indexOf('the ' + r[0] + ' do not rest') >= 0; })) out.push(tag);
    });
    var gap = T3.skinLow(fig, ['spine'], overPressBench).y - top;
    out.lumbarGap = out.lumbarGap === undefined ? gap : Math.min(out.lumbarGap, gap);
    out.lumbarGapMax = Math.max(out.lumbarGapMax || -1e9, gap);
    if ((gap < 8 || gap > 30) && !out.some(function (x) { return x.indexOf('lower back') >= 0; })) out.push('bench press: the lower back is ' + gap.toFixed(1) + ' units off the pad (natural arch 8-30)');
  }
  T3.benchRest = benchRest;

  // ---------------------------------------------------------------- standing lateral raise (the move that made lats pop in 2D)
  X3.raise = {
    id: 'raise', name: 'Lateral raise', knowledge: 'lateral-raise',
    phaseMap: [{ id: 'start', kind: 'hold', label: 'Start', a: 0, b: 0.04, cue: 'Soft elbows' }, { id: 'concentric', kind: 'up', label: 'Raise', a: 0.04, b: 0.46, cue: 'Lead with the elbows' },
      { id: 'end-range', kind: 'hold', label: 'Shoulder height', a: 0.46, b: 0.54, cue: 'Stop at shoulder height' }, { id: 'eccentric', kind: 'down', label: 'Lower slowly', a: 0.54, b: 0.92, cue: 'Do not drop them' },
      { id: 'reset', kind: 'hold', label: 'Reset', a: 0.92, b: 1.0, cue: '' }],
    acts: { 'delt-side': 3, trap: 2, 'delt-front': 1, serratus: 1 },      // no lat: it is not a recognised stabiliser of the lateral raise (assets/fitness/data/exercises.json)
    shots: { front: { az: 8, el: 8 }, three: { az: 35, el: 10 }, back: { az: 180, el: 8 }, backThree: { az: 148, el: 14 } },
    build: function (stage, fig, m, o) {
      o = o || {};
      var p = fig.id ? fig.id + '.' : '', at = o.at || 0, reps = o.reps || 3, per = o.period || 3.4;
      var dbs = [EQ.dumbbell(0.8), EQ.dumbbell(0.8)]; fig.hold('L', dbs[0]); fig.hold('R', dbs[1]);
      fig.roles(X3.raise.acts);
      var stance = { fxL: 48, fzL: 0, fyawL: 6, fxR: -48, fzR: 0, fyawR: -6, x: 0, y: 370, z: 0, lean: 0, gazL: 1, gazR: 1 };
      var low = sym({ sh: 5, pl: 22, el: 14, wr: 0 }), high = sym({ sh: 88, pl: 14, el: 16, wr: -6 });
      m.base(pref(p, merge(stance, low)));
      var end = m.cycle(at, per, reps, [
        { at: 0.04, v: null },
        { at: 0.46, v: pref(p, merge(high, { lean: 3 })), ease: 'power1.inOut' },
        { at: 0.54, v: null },
        { at: 0.92, v: pref(p, merge(low, { lean: 0 })), ease: 'sine.inOut' },
        { at: 1.0, v: null }
      ]);
      envelope(m, p, { 'delt-side': 1, trap: 0.7, 'delt-front': 0.4, serratus: 0.4 }, at, per, reps);
      return end;
    },
    camera: { target: { tx: 0, ty: 420, tz: 0 }, dist: 2050, fov: 26 }
  };

  // ================================================================ LOWER BODY (2026-11-12)
  // Shared geometry. The root is the pelvis (hip joint height); thighs hang from (+-40, -6, 0) in its frame; thigh 178, shin 166,
  // ankle 26 above the sole. Trunk angle phi is split as root pitch (pelvis, k) plus spine lean (1 - k), as applyPose spreads lean
  // 0.4 spine / 0.6 chest. Every pose below is solved from contacts (feet, bar, bench), never hand-tuned per frame.
  var D2R = Math.PI / 180, THREE = global.THREE;
  /** [dy, dz] of a point given in the CHEST frame (ly up the trunk, lz forward) from the root, for root pitch and lean (degrees). */
  function trunkPt(pitch, lean, ly, lz) {
    var a1 = pitch * D2R, a2 = (pitch + 0.4 * lean) * D2R, a3 = (pitch + lean) * D2R;
    return [70 * Math.cos(a1) + 80 * Math.cos(a2) + ly * Math.cos(a3) - lz * Math.sin(a3),
            70 * Math.sin(a1) + 80 * Math.sin(a2) + ly * Math.sin(a3) + lz * Math.cos(a3)];
  }
  T3.trunkPt = trunkPt;
  function smooth(x) { x = Math.max(0, Math.min(1, x)); return x * x * (3 - 2 * x); }
  function lerp(a, b, s) { return a + (b - a) * s; }
  /** A rep driven by one 0..1 parameter through an exact path: lower (sine), short hold, drive (power2), short hold. */
  function reps(m, at, per, count, fn, o) {
    o = o || {};
    var dn = o.down || [0.04, 0.46], up = o.up || [0.54, 0.90];
    for (var r = 0; r < count; r++) {
      var t0 = at + r * per;
      m.path(t0 + dn[0] * per, (dn[1] - dn[0]) * per, function (e) { return fn(e); }, o.downEase || 'sine.inOut');
      m.path(t0 + up[0] * per, (up[1] - up[0]) * per, function (e) { return fn(1 - e); }, o.upEase || 'power2.inOut');
    }
    return at + count * per;
  }
  T3.reps = reps;

  // ---------------------------------------------------------------- barbell back squat (and the knees-blocked variant)
  /*
   * s = depth 0..1. The shin tilts forward from 5 deg to `shin` deg along the foot, the thigh from 5 deg to `thigh` deg off
   * vertical (88 = parallel); the hip follows from the leg lengths. The trunk angle is SOLVED so the bar stays over the
   * midfoot (bar z target slides from its standing spot to `barZ`), which is what makes the blocked squat lean further:
   * the knees cannot travel, the hips go back, and the trunk must tip to keep the bar balanced. Illustrative, not mocap.
   */
  function squatSolver(cfg) {
    var fx = cfg.fx || 62, yaw = cfg.yaw || 14, k = 0.72;
    var BAR = [86, -47];                                                    // bar on the upper traps, chest frame
    function hipAt(s) {
      var ths = lerp(5, cfg.shin, s) * D2R, tht = lerp(5, cfg.thigh || 88, s) * D2R;
      var kf = 166 * Math.sin(ths), ky = 26 + 166 * Math.cos(ths);
      var kx = fx + kf * Math.sin(yaw * D2R), dx = kx - 40, Ls = Math.sqrt(178 * 178 - dx * dx);
      return { y: ky + Ls * Math.cos(tht), z: kf * Math.cos(yaw * D2R) - Ls * Math.sin(tht), knee: [ky, kf * Math.cos(yaw * D2R)] };
    }
    function barZ(phi, hip) { var p = trunkPt(k * phi, (1 - k) * phi, BAR[0], BAR[1]); return hip.z + 6 * Math.sin(k * phi * D2R) + p[1]; }
    var hip0 = hipAt(0), z0 = barZ(cfg.stand || 4, hip0);
    function solvePhi(s, hip) {
      var target = lerp(z0, cfg.barZ === undefined ? 8 : cfg.barZ, smooth(s)), lo = 0, hi = 75;
      for (var i = 0; i < 40; i++) { var mid = (lo + hi) / 2; if (barZ(mid, hip) < target) lo = mid; else hi = mid; }
      return Math.max(cfg.stand || 4, (lo + hi) / 2);
    }
    // Knee pole: a fixed turn-out only puts the knee over the foot when the knee travels far forward (the blocked squat
    // splayed 59 units). Solve the turn-out kf each frame so the plane (hip, ankle, pole) contains the DESIGNED knee,
    // which sits on the line of the foot: tan kf = -n.z / n.x with n = u x d in the pelvis frame (left leg; right mirrors).
    function kneeTurn(s, pitch, rootY, rootZ) {
      var ths = lerp(5, cfg.shin, s) * D2R, kfw = 166 * Math.sin(ths), yw = yaw * D2R;
      var c = Math.cos(-pitch * D2R), sn = Math.sin(-pitch * D2R);
      function loc(x, y, z) { var yy = y - rootY, zz = z - rootZ; return [x, yy * c - zz * sn, yy * sn + zz * c]; }
      var hj = [40, -6, 0], an = loc(fx, 26, 0), kn = loc(fx + kfw * Math.sin(yw), 26 + 166 * Math.cos(ths), kfw * Math.cos(yw));
      var u = [an[0] - hj[0], an[1] - hj[1], an[2] - hj[2]], d = [kn[0] - hj[0], kn[1] - hj[1], kn[2] - hj[2]];
      var n = [u[1] * d[2] - u[2] * d[1], u[2] * d[0] - u[0] * d[2], u[0] * d[1] - u[1] * d[0]];
      var kf = Math.atan2(-n[2], n[0]) / D2R;
      if (kf > 90) kf -= 180; else if (kf < -90) kf += 180;
      return kf;
    }
    return function pose(s) {
      var hip = hipAt(s), phi = solvePhi(s, hip), pitch = k * phi, lean = (1 - k) * phi;
      // the thigh origin sits 6 below the root in the pelvis frame: put the ROOT where that origin lands on the solved hip
      var y = hip.y + 6 * Math.cos(pitch * D2R), z = hip.z + 6 * Math.sin(pitch * D2R);
      // near-straight legs make the solved pole meaningless (u and d almost parallel): blend from the toe angle as the knee bends
      var kf = lerp(yaw, kneeTurn(s, pitch, y, z), smooth(s / 0.3));
      return { y: y, z: z, pitch: pitch, lean: lean, neckF: -0.62 * phi, headF: -0.1 * phi, kf: kf,
        _phi: phi, _bar: barZ(phi, hip), _hip: hip };
    };
  }
  T3.squatSolver = squatSolver;
  function buildSquat(def, stage, fig, m, o, cfg) {
    o = o || {};
    var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 3, per = o.period || 3.6;
    var x0 = o.x || 0, z0 = o.z || 0, fx = 62, yaw = 14;
    var bar = EQ.barbell({ half: cfg.barHalf || 330, plate: 46 }); fig.bone.chest.add(bar); bar.position.set(0, 86, -47);
    if (cfg.board) { var bd = EQ.board({ x: x0, z: z0 + 112, w: 300, h: 300, opacity: 0.5 }); stage.world.add(bd); fig.props.push(bd); }
    fig.roles(def.acts);
    var solve = squatSolver(cfg);
    // hands on the bar, chest frame: grip just outside the shoulders, elbows down and back
    var arms = {};
    ['L', 'R'].forEach(function (sd) {
      var sg = sd === 'L' ? 1 : -1;
      arms['ik' + sd] = 1; arms['ikc' + sd] = 1; arms['gax' + sd] = 1;
      arms['hx' + sd] = sg * 80; arms['hy' + sd] = 86 - 78 - 20; arms['hz' + sd] = -47 + 2 + 6;
      arms['px' + sd] = sg * 0.35; arms['py' + sd] = -1; arms['pz' + sd] = -0.7;
    });
    var feet = { fxL: x0 + fx, fzL: z0, fyawL: yaw, kfL: yaw, fxR: x0 - fx, fzR: z0, fyawR: -yaw, kfR: yaw };
    function at_(s) { var q = solve(s); return pref(p, { x: x0, y: q.y, z: z0 + q.z, pitch: q.pitch, lean: q.lean, neckF: q.neckF, headF: q.headF, kfL: q.kf, kfR: q.kf }); }
    m.base(pref(p, merge(feet, arms)));
    m.base(at_(0));
    var end = reps(m, at, per, n, at_);
    envelope(m, p, o.peaks || def.peaks, at, per, n);          // o.peaks: a film can dim or brighten a muscle (e.g. measured EMG order)
    fig.solve = solve;
    if (cfg.rack) fig.rack = squatRack(stage, fig, function (s) { return merge(pref(p, merge(feet, arms)), at_(s)); }, bar, x0, z0, cfg.barHalf || 330);
    return end;
  }
  /*
   * A power rack around a back squat (motion family 2, 2026-11-24), built from the solved bar path: four posts just inside the collars
   * and well outside the hands, J-hooks on the front posts a little below the standing bar (the lifter walked back from them), safety
   * pins through the posts just below the bar's lowest point. Nothing in it moves; rig3d-check (def.checks) proves the bar and the hands
   * never touch it and the pins sit below the bottom.
   */
  function squatRack(stage, fig, poseAt, bar, x0, z0, half) {
    var lo = { y: Infinity }, top = null, w = new V3m(), handX = 0;
    for (var i = 0; i <= 24; i++) {
      fig.apply(poseAt(i / 24)); bar.getWorldPosition(w);
      if (w.y < lo.y) lo = { y: w.y, z: w.z };
      if (i === 0) top = { y: w.y, z: w.z };
      handX = Math.max(handX, Math.abs(fistPoint(fig, 'L').x - x0), Math.abs(fistPoint(fig, 'R').x - x0));
    }
    fig.apply({});
    var g = new THREE.Group(), steelS = T3.colors.steelShade, px = Math.min(half * 0.66 - 2 - 22, handX + 40), zF = z0 + 110, zB = z0 - 165, H = top.y + 170;
    [-1, 1].forEach(function (sg) {
      [zF, zB].forEach(function (z) { var post = box(16, H, 16, steelS); post.position.set(x0 + sg * px, H / 2, z); g.add(post); });
      var rail = box(20, 10, zF - zB + 60, steelS); rail.position.set(x0 + sg * px, 5, (zF + zB) / 2); g.add(rail);
      var hook = box(14, 8, 26, T3.colors.steel); hook.position.set(x0 + sg * px, top.y - 18, zF - 20); g.add(hook);
      var lip = box(14, 16, 6, T3.colors.steel); lip.position.set(x0 + sg * px, top.y - 10, zF - 31); g.add(lip);
      var pin = rod(6, T3.colors.steel); setRod(pin, new V3m(x0 + sg * px, lo.y - 25, zF + 20), new V3m(x0 + sg * px, lo.y - 25, zB - 20)); g.add(pin);
    });
    [zF, zB].forEach(function (z) { var cap = box(2 * px + 16, 14, 16, steelS); cap.position.set(x0, H, z); g.add(cap); });
    addProp(stage, fig, g);
    return { group: g, bar: bar, post: px, pinY: lo.y - 25, hookY: top.y - 18, barTop: top.y, barLow: lo.y, half: half };
  }
  /** Rack checks: the bar (whole length, radius 6) and the fists never touch the rack; the pins sit 8-40 under the bar at the bottom; the hooks 5-30 under the standing bar. */
  function squatRackChecks(fig, v, t, out) {
    var R = fig.rack, w = new V3m(), q = new V3m(), ax = new V3m(), qq = new THREE.Quaternion(), bb = new THREE.Box3(), bar = R.bar;
    bar.getWorldPosition(w); bar.getWorldQuaternion(qq); ax.set(1, 0, 0).applyQuaternion(qq);
    var worst = Infinity, hand = Infinity, F = [fistPoint(fig, 'L'), fistPoint(fig, 'R')];
    R.group.updateMatrixWorld(true);
    R.group.children.forEach(function (o) {
      bb.setFromObject(o);
      for (var k = -R.half; k <= R.half; k += 10) worst = Math.min(worst, bb.distanceToPoint(q.copy(w).addScaledVector(ax, k)) - 6);
      F.forEach(function (f) { hand = Math.min(hand, bb.distanceToPoint(f) - 12); });
    });
    out.rackClearance = Math.min(out.rackClearance === undefined ? Infinity : out.rackClearance, worst);
    out.handRackClearance = Math.min(out.handRackClearance === undefined ? Infinity : out.handRackClearance, hand);
    if (worst < 1) flagOnce(out, 'rack squat: the bar touches the rack (' + worst.toFixed(1) + ' units)');
    if (hand < 2) flagOnce(out, 'rack squat: a hand touches a rack post (' + hand.toFixed(1) + ' units)');
    if (!out._r) {
      Object.defineProperty(out, '_r', { value: true });
      out.pinUnderBottom = R.barLow - 6 - (R.pinY + 6); out.hookUnderStanding = R.barTop - (R.hookY + 4);
      if (out.pinUnderBottom < 8 || out.pinUnderBottom > 40) flagOnce(out, 'rack squat: the safety pins are ' + out.pinUnderBottom.toFixed(0) + ' units under the bar at the bottom (8-40)');
      if (out.hookUnderStanding < 5 || out.hookUnderStanding > 30) flagOnce(out, 'rack squat: the J-hooks are ' + out.hookUnderStanding.toFixed(0) + ' units under the standing bar (5-30)');
    }
  }
  T3.squatRackChecks = squatRackChecks;
  X3.squat = {
    id: 'squat', name: 'Barbell back squat', knowledge: 'back-squat',
    phaseMap: [{ id: 'start', kind: 'hold', label: 'Standing', a: 0, b: 0.04 }, { id: 'eccentric', kind: 'down', label: 'Descend', a: 0.04, b: 0.46 }, { id: 'end-range', kind: 'hold', label: 'Bottom', a: 0.46, b: 0.54 },
      { id: 'concentric', kind: 'up', label: 'Stand up', a: 0.54, b: 0.90 }, { id: 'lockout', kind: 'hold', label: 'Lockout', a: 0.90, b: 1.0 }],
    acts: { quad: 3, glute: 3, adductor: 2, erector: 1, abs: 1, soleus: 1, calf: 1 },
    peaks: { quad: 1, glute: 0.9, adductor: 0.7, erector: 0.5, abs: 0.4, soleus: 0.35, calf: 0.3 },
    shots: { side: { az: 90, el: 6 }, three: { az: 52, el: 10 }, front: { az: 14, el: 8 }, back: { az: 160, el: 10 }, sideHigh: { az: 90, el: 24 } },
    build: function (stage, fig, m, o) { return buildSquat(X3.squat, stage, fig, m, o, { shin: 40, thigh: 88, barZ: 8 }); },
    camera: { target: { tx: 0, ty: 400, tz: 0 }, dist: 2500, fov: 26 },
    checks: function (fig, v, t, out) { kneeTrack(fig, v, out); }
  };
  X3['squat-blocked'] = {
    id: 'squat-blocked', name: 'Back squat, knees blocked at the toes', knowledge: 'back-squat', phaseMap: X3.squat.phaseMap, acts: X3.squat.acts, peaks: X3.squat.peaks, shots: X3.squat.shots,
    build: function (stage, fig, m, o) { return buildSquat(X3['squat-blocked'], stage, fig, m, o, { shin: 17, thigh: 88, barZ: 8, board: true }); },
    camera: X3.squat.camera,
    // the point of the variant: no part of the knee may pass the board (front face of the kneecap at joint + 27)
    checks: function (fig, v, t, out) {
      kneeTrack(fig, v, out);
      ['L', 'R'].forEach(function (s) {
        var kz = fig.point('kn' + s, 0, 0, 27).z;
        out.maxKneeZ = Math.max(out.maxKneeZ || -1e9, kz);
        var tag = 'blocked squat: kneecap passes the board at z=108';
        if (kz > 108 && out.indexOf(tag) < 0) out.push(tag);
      });
    }
  };
  // the back squat in a power rack (same solver and motion as X3.squat; a longer bar so the posts fit between the hands and the collars)
  X3['squat-rack'] = {
    id: 'squat-rack', name: 'Barbell back squat in a power rack', knowledge: 'back-squat', phaseMap: X3.squat.phaseMap, acts: X3.squat.acts, peaks: X3.squat.peaks,
    shots: { side: { az: 90, el: 6 }, three: { az: 52, el: 10 }, front: { az: 14, el: 8 }, back: { az: 160, el: 10 }, sideHigh: { az: 90, el: 24 } },
    build: function (stage, fig, m, o) { return buildSquat(X3['squat-rack'], stage, fig, m, o, { shin: 40, thigh: 88, barZ: 8, rack: true, barHalf: 380 }); },
    camera: X3.squat.camera,
    checks: function (fig, v, t, out) { kneeTrack(fig, v, out); squatRackChecks(fig, v, t, out); }
  };
  /** Knees track over the feet: the knee stays within 26 units of the vertical plane through the ankle along the foot. */
  function kneeTrack(fig, v, out) {
    ['L', 'R'].forEach(function (s) {
      var kn = fig.world('kn' + s), an = fig.world('an' + s), yw = (v[(fig.id ? fig.id + '.' : '') + 'fyaw' + s] || 0) * D2R;
      var lat = (kn.x - an.x) * Math.cos(yw) - (kn.z - an.z) * Math.sin(yw);
      out.maxKneeOff = Math.max(out.maxKneeOff || 0, Math.abs(lat));
      var tag = 'knee drifts more than 26 units off the line of the foot (knees should track over the toes)';
      if (Math.abs(lat) > 26 && out.indexOf(tag) < 0) out.push(tag);
    });
  }
  T3.kneeTrack = kneeTrack;

  // ---------------------------------------------------------------- barbell hip thrust (upper back on a bench)
  /*
   * b = trunk angle above horizontal (30 at the bottom, 0 at lockout). The shoulder-blade contact (chest frame 0, 45, -46)
   * is pinned to the bench edge E, so the hips rise on an arc around it; the feet stay planted (shins vertical at the top).
   * The bar sits across the hip crease (child of the pelvis); the hands hold it through chest-frame IK.
   */
  X3.hipthrust = {
    id: 'hipthrust', name: 'Barbell hip thrust', knowledge: 'hip-thrust',
    phaseMap: [{ id: 'start', kind: 'hold', label: 'Bottom', a: 0, b: 0.06 }, { id: 'concentric', kind: 'up', label: 'Drive up', a: 0.06, b: 0.42 }, { id: 'lockout', kind: 'hold', label: 'Squeeze', a: 0.42, b: 0.52 },
      { id: 'eccentric', kind: 'down', label: 'Lower', a: 0.52, b: 0.96 }, { id: 'reset', kind: 'hold', label: 'Reset', a: 0.96, b: 1.0 }],
    acts: { glute: 3, hams: 2, quad: 2, adductor: 1, erector: 1, abs: 1 },
    peaks: { glute: 1, hams: 0.6, quad: 0.55, adductor: 0.4, erector: 0.4, abs: 0.35 },
    shots: { side: { az: 0, el: 6 }, three: { az: 32, el: 16 }, foot: { az: 75, el: 18 }, high: { az: 20, el: 48 }, back: { az: 300, el: 18 } },
    build: function (stage, fig, m, o) {
      o = o || {};
      var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 3, per = o.period || 3.4;
      var x0 = o.x || 0, z0 = o.z || 0, benchTop = 182, E = new THREE.Vector3(x0 - 64, benchTop + 6, z0);
      var bench = EQ.bench({ x: x0 - 64 - 70, z: z0, y: benchTop, w: 140, l: 520, yaw: 0 }); stage.world.add(bench); fig.props.push(bench); restsOn(fig, bench);
      var bar = EQ.barbell({ half: 330, plate: 46 }); fig.bone.hips.add(bar); bar.position.set(0, -8, 64);
      fig.roles(X3.hipthrust.acts);
      var CONTACT = new THREE.Vector3(0, 150 + 45, -46), eul = new THREE.Euler(0, 0, 0, 'YXZ');
      var feetX = x0 + (o.footX || 300);
      function pose(s) {                                                   // s: 0 = lockout, 1 = bottom
        var b = lerp(0, 30, s);
        eul.set((-90 + b) * D2R, 90 * D2R, 0, 'YXZ');
        var c = CONTACT.clone().applyEuler(eul), r = E.clone().sub(c);
        return pref(p, { x: r.x, y: r.y, z: r.z, pitch: -90 + b, neckF: lerp(34, 20, s) });
      }
      var arms = {};
      var grip = new THREE.Vector3(), sh = new THREE.Vector3();
      ['L', 'R'].forEach(function (sd) {
        var sg = sd === 'L' ? 1 : -1;
        grip.set(sg * 112, -150 - 8, 64 + 2); sh.set(sg * 88, 78, -2);
        var wv = grip.clone().add(sh.clone().sub(grip).normalize().multiplyScalar(24)).sub(sh);
        arms['ik' + sd] = 1; arms['ikc' + sd] = 1; arms['hx' + sd] = wv.x; arms['hy' + sd] = wv.y; arms['hz' + sd] = wv.z;
        arms['px' + sd] = sg; arms['py' + sd] = 0.1; arms['pz' + sd] = -0.5; arms['gaz' + sd] = 1;
      });
      // lifter's left is world -z here (yaw 90): feet at the sides of the hips, toes out a little
      var feet = { fxL: feetX, fzL: z0 - 64, fyawL: 97, kfL: 7, fxR: feetX, fzR: z0 + 64, fyawR: 83, kfR: 7, yaw: 90, lean: 0, headF: 0 };
      m.base(pref(p, merge(feet, arms)));
      // start seated at the bottom, then reps from the bottom: drive up (power2), hold the squeeze, lower (sine)
      m.base(pose(1));
      var end = at;
      for (var r0 = 0; r0 < n; r0++) {
        var t0 = at + r0 * per;
        m.path(t0 + 0.06 * per, 0.36 * per, function (e) { return pose(1 - e); }, 'power2.inOut');
        m.path(t0 + 0.52 * per, 0.44 * per, function (e) { return pose(e); }, 'sine.inOut');
        end = t0 + per;
      }
      envelope(m, p, o.peaks || X3.hipthrust.peaks, at, per, n);
      fig.pose = pose;
      return end;
    },
    camera: { target: { tx: 80, ty: 230, tz: 0 }, dist: 2300, fov: 27 },
    checks: function (fig, v, t, out) {
      // lockout cue: hips level with the shoulders, shins near vertical (within 20 deg) at the top
      var p = fig.id ? fig.id + '.' : '';
      if (Math.abs(v[p + 'pitch'] + 90) < 0.5) {
        ['L', 'R'].forEach(function (s) {
          var k = fig.world('kn' + s), a = fig.world('an' + s);
          var ang = Math.atan2(Math.hypot(k.x - a.x, k.z - a.z), k.y - a.y) / D2R;
          out.topShin = Math.max(out.topShin || 0, ang);
          var tag = 'hip thrust lockout: shins more than 20 deg off vertical';
          if (ang > 20 && out.indexOf(tag) < 0) out.push(tag);
        });
      }
    }
  };

  // ---------------------------------------------------------------- calf raises: standing (knee straight) and seated (knee 90)
  /*
   * h = heel lift 0..1 (0..hmax deg). The ankle target moves so the BALL of the foot stays put (T3.heelLift), the toe box
   * stays flat, the shoe bends at the ball. Standing: the whole body rises and shifts forward over the balls. Seated: the
   * pelvis stays on the bench, the knee rises with the ankle, and the load sits on the knees.
   * The gastrocnemius crosses the knee (origin on the femur above it), the soleus does not: with the knee at 90 deg the
   * gastrocnemius is short and slack. fig.gastroLine() gives its origin, knee-back and heel points for the overlay.
   */
  function gastroLine(fig, s) {
    return [fig.point('th' + s, 0, -158, -22), fig.point('kn' + s, 0, -8, -30), fig.point('an' + s, 0, -4, -30)];
  }
  T3.gastroLine = gastroLine;
  X3.calfraise = {
    // only the triceps surae lights: the films are about the calf, and stabiliser tints on the shorts read as grey blobs
    id: 'calfraise', name: 'Standing calf raise', knowledge: 'calf-raise', minRom: 30,
    phaseMap: [{ id: 'start', kind: 'hold', label: 'Heels down', a: 0, b: 0.08 }, { id: 'concentric', kind: 'up', label: 'Rise', a: 0.08, b: 0.46 }, { id: 'end-range', kind: 'hold', label: 'Top', a: 0.46, b: 0.56 },
      { id: 'eccentric', kind: 'down', label: 'Lower', a: 0.56, b: 0.94 }, { id: 'reset', kind: 'hold', label: 'Heels down', a: 0.94, b: 1.0 }],
    acts: { calf: 3, soleus: 3 },
    peaks: { calf: 1, soleus: 0.85 },
    shots: { side: { az: 90, el: 6 }, back: { az: 180, el: 8 }, backThree: { az: 140, el: 10 }, three: { az: 45, el: 8 }, low: { az: 120, el: 2 } },
    build: function (stage, fig, m, o) {
      o = o || {};
      var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 3, per = o.period || 3.0, hmax = o.hmax || 36;
      var x0 = o.x || 0, z0 = o.z || 0;
      var dbs = [EQ.dumbbell(1), EQ.dumbbell(1)]; fig.hold('L', dbs[0]); fig.hold('R', dbs[1]);
      fig.roles(X3.calfraise.acts);
      var stance = { fxL: x0 + 44, fzL: z0, fyawL: 5, kfL: 5, fxR: x0 - 44, fzR: z0, fyawR: -5, kfR: 5, lean: 0, gaxL: 0, gazL: 1, gaxR: 0, gazR: 1 };
      var arms = sym({ sh: 4, pl: 40, el: 8, wr: 0, rt: 0 });
      function pose(h) {
        var hl = hmax * h, lift = T3.heelLift(hl);
        return pref(p, { hlL: hl, hlR: hl, x: x0, y: 372 + lift.up, z: z0 + lift.fwd, neckF: 0 });
      }
      m.base(pref(p, merge(stance, arms)));
      m.base(pose(0));
      // reps() runs fn(0 -> 1) then fn(1 -> 0): here that is the raise (power2, concentric) then the slower lowering (sine)
      var end = reps(m, at, per, n, pose, { down: [0.08, 0.46], up: [0.56, 0.94], downEase: 'power2.inOut', upEase: 'sine.inOut' });
      envelope(m, p, o.peaks || X3.calfraise.peaks, at, per, n);
      fig.pose = pose;
      return end;
    },
    camera: { target: { tx: 0, ty: 330, tz: 0 }, dist: 2300, fov: 26 },
    checks: heelChecks
  };
  X3.seatedcalf = {
    id: 'seatedcalf', name: 'Seated calf raise', knowledge: 'seated-calf-raise', minRom: 24,
    phaseMap: [{ id: 'start', kind: 'hold', label: 'Heels down', a: 0, b: 0.08 }, { id: 'concentric', kind: 'up', label: 'Rise', a: 0.08, b: 0.46 }, { id: 'end-range', kind: 'hold', label: 'Top', a: 0.46, b: 0.56 },
      { id: 'eccentric', kind: 'down', label: 'Lower', a: 0.56, b: 0.94 }, { id: 'reset', kind: 'hold', label: 'Heels down', a: 0.94, b: 1.0 }],
    acts: { soleus: 3, calf: 2 },
    peaks: { soleus: 1, calf: 0.45 },
    shots: { side: { az: 90, el: 8 }, three: { az: 50, el: 12 }, back: { az: 160, el: 12 }, low: { az: 115, el: 3 } },
    build: function (stage, fig, m, o) {
      o = o || {};
      var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 3, per = o.period || 3.0, hmax = o.hmax || 36;
      var x0 = o.x || 0, z0 = o.z || 0, hipY = 198, fx = 52, fz = 168;
      // the bench ends under mid-thigh, so the calves stay in view from the side
      var bench = EQ.bench({ x: x0, z: z0 - 30, y: hipY - 50, w: 190, l: 250 }); stage.world.add(bench); fig.props.push(bench);
      fig.roles(X3.seatedcalf.acts);
      // one dumbbell along each thigh, just above the knee (child of the thigh, so it rides up with the knee)
      var dbs = {};
      ['L', 'R'].forEach(function (s) { var d = EQ.dumbbell(0.9); d.rotation.z = Math.PI / 2; d.position.set(0, -132, 50); fig.bone['th' + s].add(d); dbs[s] = d; });
      var lean = 8, base = { x: x0, y: hipY + 6, z: z0, pitch: 0, lean: lean, neckF: 4,
        fxL: x0 + fx, fzL: z0 + fz, fyawL: 4, kfL: 4, fxR: x0 - fx, fzR: z0 + fz, fyawR: -4, kfR: 4 };
      // hands on the dumbbells: the knee is solved exactly as the rig's leg IK does, so the hands follow the rising knee
      var hipJ = {}, A = 178, Bn = 166;
      function kneeFrame(s, ankle) {
        var sg = s === 'L' ? 1 : -1, hj = new THREE.Vector3(x0 + sg * 40, hipY, z0);
        var rel = ankle.clone().sub(hj), d = rel.length(), dd = Math.min(A + Bn - 0.5, d), u = rel.clone().normalize();
        var beta = Math.acos(Math.max(-1, Math.min(1, (A * A + dd * dd - Bn * Bn) / (2 * A * dd))));
        var kf = 4 * D2R, pole = new THREE.Vector3(Math.sin(kf) * sg, 0, Math.cos(kf)); pole.addScaledVector(u, -pole.dot(u)).normalize();
        var upper = u.clone().multiplyScalar(Math.cos(beta)).addScaledVector(pole, Math.sin(beta)).normalize();
        var fore = rel.clone().multiplyScalar(dd / d).addScaledVector(upper, -A).normalize();
        var up = fore.clone().addScaledVector(upper, -fore.dot(upper)).normalize().multiplyScalar(-1);
        return { hip: hj, upper: upper, up: up };
      }
      function pose(h) {
        var hl = hmax * h, lift = T3.heelLift(hl), out = { hlL: hl, hlR: hl };
        ['L', 'R'].forEach(function (s) {
          var sg = s === 'L' ? 1 : -1, yw = sg * 4 * D2R;
          var ankle = new THREE.Vector3(x0 + sg * fx + lift.fwd * Math.sin(yw), 26 + lift.up, z0 + fz + lift.fwd * Math.cos(yw));
          var kfm = kneeFrame(s, ankle);
          var db = kfm.hip.clone().addScaledVector(kfm.upper, 132).addScaledVector(kfm.up, 50);
          var wrist = db.clone().addScaledVector(kfm.up, 24).addScaledVector(kfm.upper, -6);
          var shp = trunkPt(0, lean, 78, -2), shoulder = new THREE.Vector3(x0 + sg * 88, hipY + 6 + shp[0], z0 + shp[1]);
          var off = wrist.sub(shoulder);
          out['hx' + s] = off.x; out['hy' + s] = off.y; out['hz' + s] = off.z;
        });
        return pref(p, out);
      }
      var arms = {};
      ['L', 'R'].forEach(function (sd) { var sg = sd === 'L' ? 1 : -1; arms['ik' + sd] = 1; arms['px' + sd] = sg * 0.8; arms['py' + sd] = -0.2; arms['pz' + sd] = -0.4; arms['gaz' + sd] = 1; });
      m.base(pref(p, merge(base, arms)));
      m.base(pose(0));
      var end = reps(m, at, per, n, pose, { down: [0.08, 0.46], up: [0.56, 0.94], downEase: 'power2.inOut', upEase: 'sine.inOut' });
      envelope(m, p, o.peaks || X3.seatedcalf.peaks, at, per, n);
      fig.pose = pose;
      return end;
    },
    camera: { target: { tx: 0, ty: 260, tz: 80 }, dist: 2200, fov: 26 },
    checks: heelChecks
  };
  /** Heel-lift exercises: the ball of each foot never slides or lifts (1.5 units), and the heel really rises at the top. */
  function heelChecks(fig, v, t, out) {
    var c = T3.contacts(fig);
    out.balls = out.balls || {};
    ['L', 'R'].forEach(function (s) {
      var b = c['ball' + s], r = out.balls[s] || (out.balls[s] = { x0: b[0], z0: b[2], drift: 0, maxHeel: -1e9 });
      r.drift = Math.max(r.drift, Math.hypot(b[0] - r.x0, b[2] - r.z0));
      r.maxHeel = Math.max(r.maxHeel, c['heel' + s]);
      out.ballDrift = Math.max(out.ballDrift || 0, r.drift); out.maxHeelLift = Math.max(out.maxHeelLift || 0, r.maxHeel);
      var tag = 'ball of the foot slides or lifts by more than 1.5 units during the heel lift';
      if ((r.drift > 1.5 || Math.abs(b[1]) > 1.5) && out.indexOf(tag) < 0) out.push(tag);
    });
  }
  T3.heelChecks = heelChecks;

  // ================================================================ SHARED MEASURES (2026-11-23)
  /** Whole-body centre of mass (world), segment fractions after Winter (2009) applied to Tibi's joints. Illustrative. */
  T3.com = function (fig) {
    var c = new THREE.Vector3(), w = 0;
    function add(v, m) { c.addScaledVector(v, m); w += m; }
    function mid(a, b, f) { return fig.world(a).clone().lerp(fig.world(b), f); }
    add(fig.point('head', 0, 50, 4), 0.081);
    add(mid('hips', 'neck', 0.5), 0.497);
    ['L', 'R'].forEach(function (s) {
      add(mid('sh' + s, 'el' + s, 0.436), 0.028); add(mid('el' + s, 'hand' + s, 0.68), 0.022);
      add(mid('th' + s, 'kn' + s, 0.433), 0.1); add(mid('kn' + s, 'an' + s, 0.433), 0.0465); add(fig.point('an' + s, 0, -15, 30), 0.0145);
    });
    return c.multiplyScalar(1 / w);
  };
  /** Spine flexion (deg): the angle between the pelvis and chest bones' long axes, the "pelvis-to-chest segment angle" of a flat back. */
  T3.spineFlex = function (fig) {
    fig.root.updateMatrixWorld(true);
    var a = new THREE.Vector3(0, 1, 0).transformDirection(fig.bone.hips.matrixWorld), b = new THREE.Vector3(0, 1, 0).transformDirection(fig.bone.chest.matrixWorld);
    var lat = new THREE.Vector3(1, 0, 0).transformDirection(fig.bone.hips.matrixWorld), ang = Math.acos(Math.max(-1, Math.min(1, a.dot(b)))) / D2R;
    return new THREE.Vector3().crossVectors(a, b).dot(lat) >= 0 ? ang : -ang;        // + = flexion (rounding), - = extension
  };
  /** Trunk angle from vertical (deg) of the hip-to-shoulder chord in the sagittal plane: + forward. */
  T3.trunkAngle = function (fig) {
    var h = fig.world('hips'), s = fig.world('shL').clone().add(fig.world('shR')).multiplyScalar(0.5);
    return Math.atan2(s.z - h.z, s.y - h.y) / D2R;
  };
  var LEGBONES = ['thL', 'thR', 'knL', 'knR'];
  /**
   * Horizontal gap (units, along +z) from a bar (centre b, radius r) to the front of the legs at the bar's height: the front-most posed
   * leg skin point within 4 units of the bar's y and inside |x| < xMax. Negative: the bar is inside the legs. Infinity: no leg there.
   */
  T3.barLegGap = function (fig, b, r, xMax) {
    var skin = fig.body.skin, geo = skin.geometry, pa = geo.getAttribute('position');
    T3.skinLow(fig, LEGBONES, function () { return false; });                       // builds fig._domBone once
    var names = skin.skeleton.bones.map(function (x) { return x.name; }), want = {};
    names.forEach(function (n, i) { if (LEGBONES.indexOf(n) >= 0) want[i] = true; });
    fig.root.updateMatrixWorld(true); skin.skeleton.update();
    var v = new THREE.Vector3(), front = -Infinity;
    for (var j = 0; j < pa.count; j++) {
      if (!want[fig._domBone[j]]) continue;
      v.fromBufferAttribute(pa, j); skin.applyBoneTransform(j, v); v.applyMatrix4(skin.matrixWorld);
      if (Math.abs(v.y - b.y) > 4 || Math.abs(v.x) > (xMax || 100)) continue;
      if (v.z > front) front = v.z;
    }
    return front === -Infinity ? Infinity : b.z - (r || 6) - front;
  };

  // ================================================================ HIP HINGE (2026-11-23): deadlift, Romanian deadlift
  /*
   * hingeSolver(cfg) -> pose(s), s = 0 standing tall (lockout) .. 1 bottom. The BAR is the constraint: it travels a vertical line over
   * the midfoot (z = cfg.barZ, plus cfg.drift * s for a bar-drift mistake) from the lockout height to cfg.bottom. The arms hang from the
   * shoulders to the bar at arm(s) degrees (+ = shoulder ahead of the bar), so the bar fixes the shoulder. The KNEE follows a schedule,
   * knee(s) = lerp(kTop, kBot, kshape(s)) degrees of flexion (deadlift: the knees extend first off the floor; RDL: soft knees), and the
   * trunk angle phi is SOLVED so the two-link leg (thigh 178, shin 166) from the hip to the planted ankle has exactly that bend: the
   * hips go back exactly as far as the bar, the arms and the knees allow, never a hand-posed frame. phi splits into pelvis pitch and
   * spine flexion round * s^0.8 (0: the spine stays neutral and the whole hinge is at the hip; the rounded-back mistake changes only
   * `round`). The knee points along the foot (pose key kw). Solved once: the lockout bar height that leaves the knees `slack` short of
   * straight (with phi 0, trunk vertical), the lockout arm angle that rests the bar on the thighs (gapTop) and the bottom knee bend that
   * brings the shins (RDL: the thighs) to the bar (gapBottom), against a front-of-leg profile measured from Tibi's skin (shin 14-23,
   * kneecap 30, thigh 36-44 units in front of the bone axis). Illustrative, not mocap.
   */
  function legFront(y, A, K, H) {
    if (y < K[0]) {
      var rs = 14 + 9 * Math.min(1, Math.max(0, (y - 26) / 80));             // shin, blending into the kneecap over the last 40 units
      return A[1] + (y - A[0]) * (K[1] - A[1]) / (K[0] - A[0]) + lerp(rs, 30, smooth((y - K[0] + 40) / 40));
    }
    var f = Math.max(0, Math.min(1, (y - K[0]) / (H[0] - K[0])));
    return K[1] + f * (H[1] - K[1]) + lerp(30, 44, Math.min(1, f * 1.5));
  }
  function hingeSolver(cfg) {
    var Lsh = 166, Lth = Math.sqrt(178 * 178 - (cfg.fx - 40) * (cfg.fx - 40)), A = [26, 0], MAXD = Lth + Lsh - 0.5;
    var reach = cfg.reach || Math.sqrt(262.8 * 262.8 - cfg.dxs * cfg.dxs);  // shoulder to bar (sagittal): wrist 238.8 off the shoulder (soft elbows) + the fist
    function geo(Y, a, phi, s) {
      var lean = (cfg.round || 0) * Math.pow(s, 0.8), pitch = phi - lean, bz = cfg.barZ + (cfg.drift || 0) * s;
      var S = [Y + reach * Math.cos(a * D2R), bz + reach * Math.sin(a * D2R)];
      var t = trunkPt(pitch, lean, cfg.ly, -2), pr = pitch * D2R;
      var H = [S[0] - t[0] - 6 * Math.cos(pr), S[1] - t[1] - 6 * Math.sin(pr)];
      var d = Math.hypot(H[0] - A[0], H[1] - A[1]), dd = Math.min(d, MAXD);
      var u = [(A[0] - H[0]) / d, (A[1] - H[1]) / d], b = Math.acos(Math.max(-1, Math.min(1, (Lth * Lth + dd * dd - Lsh * Lsh) / (2 * Lth * dd))));
      var n = [-u[1], u[0]]; if (n[1] < 0) n = [-n[0], -n[1]];               // the knee bends forward
      var K = [H[0] + Lth * (u[0] * Math.cos(b) + n[0] * Math.sin(b)), H[1] + Lth * (u[1] * Math.cos(b) + n[1] * Math.sin(b))];
      var kflex = 180 - Math.acos(Math.max(-1, Math.min(1, (Lth * Lth + Lsh * Lsh - dd * dd) / (2 * Lth * Lsh)))) / D2R;
      return { S: S, H: H, K: K, d: d, kflex: kflex, pitch: pitch, lean: lean, phi: phi, barY: Y, barZ: bz, clear: bz - 6 - legFront(Y, A, K, H) };
    }
    // the trunk angle that gives the knee bend kf: more trunk angle moves the hip back and up, away from the ankle (a straighter knee)
    function phiFor(Y, a, kf, s) {
      var lo = -15, hi = 89;
      for (var i = 0; i < 44; i++) { var mid = (lo + hi) / 2, g = geo(Y, a, mid, s); if (g.d > MAXD || g.kflex < kf) hi = mid; else lo = mid; }
      return (lo + hi) / 2;
    }
    function topFor(a) {                                                     // lockout bar height: trunk vertical, knees `slack` short of straight
      var lo = 250, hi = 430;
      for (var i = 0; i < 40; i++) { var mid = (lo + hi) / 2; if (geo(mid, a, 0, 0).d > Lth + Lsh - cfg.slack) hi = mid; else lo = mid; }
      return (lo + hi) / 2;
    }
    // the designed bar-to-leg clearance at depth s, plus a correction measured on the real skin (buildHinge: cfg.gapCorr at 9 depths)
    function gapAt(s) {
      var g = lerp(cfg.gapTop, cfg.gapBottom, s), C = cfg.gapCorr;
      if (C) { var x = s * (C.length - 1), i = Math.min(C.length - 2, Math.floor(x)); g += lerp(C[i], C[i + 1], x - i); }
      return g;
    }
    var aTop = cfg.arm[0];
    if (cfg.gapTop !== undefined) {                                          // lockout: the bar rests on the thighs
      var lo = -30, hi = 10;
      for (var i = 0; i < 30; i++) { var mid = (lo + hi) / 2; if (geo(topFor(mid), mid, 0, 0).clear > gapAt(0)) lo = mid; else hi = mid; }
      aTop = (lo + hi) / 2;
    }
    var top = topFor(aTop), kTop = geo(top, aTop, 0, 0).kflex;
    // bottom: the knee bend that brings the shins (RDL: the thighs) to the bar with the arms at arm[1]
    var lo2 = kTop, hi2 = 140;
    for (var j = 0; j < 40; j++) { var m2 = (lo2 + hi2) / 2, g = geo(cfg.bottom, cfg.arm[1], phiFor(cfg.bottom, cfg.arm[1], m2, 1), 1); if (g.clear < gapAt(1)) hi2 = m2; else lo2 = m2; }
    var kBot = (lo2 + hi2) / 2, kshape = cfg.kshape || function (s) { return s; };
    // In between, the knee follows its schedule and the ARMS find the legs: the arm angle that keeps the bar touching the legs (gap)
    // with that knee bend (shoulders further ahead of the bar bring the hips forward and the thighs to the bar; real lifters pull the
    // bar back into the legs). Tabulated once on 64 depths and interpolated (Catmull-Rom): pose(s) stays a pure function of s.
    // cfg.phiShape instead prescribes the trunk angle (phi = bottom angle * phiShape(s)) and the knee follows from the contact.
    var phiB = geo(cfg.bottom, cfg.arm[1], phiFor(cfg.bottom, cfg.arm[1], kBot, 1), 1).phi;
    function phiOf(Y, a, kf, s) { return cfg.phiShape ? phiB * cfg.phiShape(s) : phiFor(Y, a, kf, s); }
    // the root is FOLLOWED from the lockout down (near lockout the legs are almost straight and other roots, or none, lie a few degrees
    // away): scan outward from the last arm angle for the nearest sign change, then bisect
    function alphaFor(Y, kf, gap, s, prev) {
      function f(a) { var g = geo(Y, a, phiOf(Y, a, kf, s), s); return g.d >= MAXD - 0.2 ? NaN : g.clear - gap; }
      var f0 = f(prev);
      for (var st = 0.25; st <= 30; st += 0.25) {
        for (var sg = -1; sg <= 1; sg += 2) {
          var a1 = prev + sg * (st - 0.25), a2 = prev + sg * st, f1 = st === 0.25 ? f0 : f(a1), f2 = f(a2);
          if (f1 === f1 && f2 === f2 && (f1 <= 0) !== (f2 <= 0)) {
            var lo = a1, hi = a2, flo = f1;
            for (var i = 0; i < 30; i++) { var mid = (lo + hi) / 2, fm = f(mid); if (fm !== fm) break; if ((fm <= 0) === (flo <= 0)) { lo = mid; flo = fm; } else hi = mid; }
            return (lo + hi) / 2;
          }
        }
      }
      return prev;
    }
    var N = 64, TA = [], TP = [];
    for (var i2 = 0; i2 <= N; i2++) {
      var s2 = i2 / N, Y2 = lerp(top, cfg.bottom, s2), kf2 = lerp(kTop, kBot, kshape(s2));
      TA[i2] = i2 === 0 ? aTop : i2 === N ? cfg.arm[1] : alphaFor(Y2, kf2, gapAt(s2), s2, TA[i2 - 1]);
      TP[i2] = i2 === 0 ? 0 : phiOf(Y2, TA[i2], kf2, s2);
    }
    function cr(T, s) {
      var x = Math.max(0, Math.min(1, s)) * N, i = Math.min(N - 1, Math.floor(x)), f = x - i;
      var p0 = T[Math.max(0, i - 1)], p1 = T[i], p2 = T[i + 1], p3 = T[Math.min(N, i + 2)];
      return 0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (-p0 + 3 * p1 - 3 * p2 + p3) * f * f * f);
    }
    function pose(s) { var g = geo(lerp(top, cfg.bottom, s), cr(TA, s), cr(TP, s), s); g.s = s; g.arm = cr(TA, s); return g; }
    pose.kBot = kBot; pose.arms = TA; pose.phis = TP;    pose.top = top; pose.armTop = aTop; pose.kTop = kTop;
    return pose;
  }  T3.hingeSolver = hingeSolver;
  function buildHinge(def, stage, fig, m, o, cfg) {
    o = o || {};
    var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 3, per = o.period || def.period;
    var x0 = o.x || 0, z0 = o.z || 0, fx = 50, yaw = 8, S = fig.spec, grip = S.shx + 20;
    var barZ = (T3.HEEL.z + T3.TIP.z) / 2 * Math.cos(yaw * D2R);              // over the middle of the shoe
    var cfg0 = merge({ ly: S.shy - 150, dxs: grip - S.shx, fx: fx, barZ: barZ, slack: 1.5 }, cfg), solve;
    // the bar rides the left hand (its centre on the midline); the right hand grips the same bar through IK
    var bar = EQ.barbell({ half: 330, plate: cfg.plate || 98 }), holder = new THREE.Group();
    holder.add(bar); bar.position.x = -grip; fig.hold('L', holder); fig.bar = bar;
    fig.roles(def.acts);
    var feet = { fxL: x0 + fx, fzL: z0, fyawL: yaw, kwL: 1, fxR: x0 - fx, fzR: z0, fyawR: -yaw, kwR: 1 };
    var arms = { ikL: 1, ikR: 1, gaxL: 1, gaxR: 1, wrL: 0, wrR: 0, pxL: 0.25, pyL: 0, pzL: -1, pxR: -0.25, pyR: 0, pzR: -1 };
    // The wrist stays 238.8 from the shoulder (soft elbows, never locked: the IK reach gate). The bar sits in the fist, `a` along the
    // arm and `c` across it, both MEASURED on the posed figure (two passes), so the wrist is aimed to land the real bar centre on the
    // designed one and the solver uses the real shoulder-to-bar distance. Translating the wrist instead changed the elbow bend and
    // threw the bar 4 units the other way.
    var arm = { a: 262.8, c: 0 }, X = new THREE.Vector3(1, 0, 0), sh = new THREE.Vector3(), bp = new THREE.Vector3(), u = new THREE.Vector3(), nU = new THREE.Vector3();
    function wrist(Sv, Bv) {
      var r = Math.hypot(arm.a, arm.c);
      u.copy(Bv).sub(Sv).normalize(); nU.crossVectors(X, u).normalize();
      return u.multiplyScalar(arm.a / r).addScaledVector(nU, -arm.c / r).multiplyScalar(238.8);
    }
    function at_(s) {
      var g = solve(s), pr = g.pitch * D2R, q = { x: x0, y: g.H[0] + 6 * Math.cos(pr), z: z0 + g.H[1] + 6 * Math.sin(pr), pitch: g.pitch, lean: g.lean,
        neckF: -(cfg.neck === undefined ? 0.3 : cfg.neck) * g.phi, headF: 0 };
      ['L', 'R'].forEach(function (sd) {
        var sg = sd === 'L' ? 1 : -1;
        sh.set(sg * S.shx, g.S[0], g.S[1]); bp.set(sg * grip, g.barY, g.barZ);
        var wv = wrist(sh, bp);
        q['hx' + sd] = wv.x; q['hy' + sd] = wv.y; q['hz' + sd] = wv.z;
      });
      return pref(p, q);
    }
    var base = pref(p, merge(feet, arms)), held = fig.supports ? fig.supports.splice(0) : [];
    for (var pass = 0; pass < 3; pass++) {
      var r3 = Math.hypot(arm.a, arm.c);
      solve = hingeSolver(merge(cfg0, { reach: Math.sqrt(r3 * r3 - cfg0.dxs * cfg0.dxs) }));
      if (pass === 2) break;
      var sa = 0, sc = 0;
      [0, 0.5, 1].forEach(function (s) {
        fig.apply(merge(base, at_(s)));
        var Sw = fig.world('shL'), w = fig.world('handL').sub(Sw).normalize(), e = bar.getWorldPosition(new THREE.Vector3()).setX(grip).sub(Sw);
        sa += e.dot(w) / 3; sc += e.dot(new THREE.Vector3().crossVectors(X, w).normalize()) / 3;
      });
      arm = { a: sa, c: sc };
    }
    // The front-of-leg profile in the solver is a fixed estimate; the real skin differs (between bodies and skin profiles by up to
    // 6 units). Measure the bar-to-leg gap on the posed skin at 9 depths and correct the designed clearance (two passes).
    var GS = [0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1], corr = GS.map(function () { return 0; }), r4 = Math.hypot(arm.a, arm.c);
    for (var gp = 0; gp < 2; gp++) {
      GS.forEach(function (s, i) {
        fig.apply(merge(base, at_(s)));
        var b = bar.getWorldPosition(new THREE.Vector3()), gm = T3.barLegGap(fig, b, 6, grip - 12);
        if (gm !== Infinity) corr[i] += lerp(cfg0.gapTop, cfg0.gapBottom, s) - gm;
      });
      solve = hingeSolver(merge(cfg0, { reach: Math.sqrt(r4 * r4 - cfg0.dxs * cfg0.dxs), gapCorr: corr.slice() }));
    }
    if (fig.supports) Array.prototype.push.apply(fig.supports, held);
    fig.apply({});    m.base(pref(p, merge(feet, arms)));
    m.base(at_(cfg.startBottom ? 1 : 0));
    var end = reps(m, at, per, n, cfg.startBottom ? function (s) { return at_(1 - s); } : at_, def.rhythm);
    envelope(m, p, o.peaks || def.peaks, at, per, n);
    fig.solve = solve; fig.pose = at_; fig.hinge = { barZ: barZ, grip: grip, startBottom: !!cfg.startBottom, def: def, clock: { at: at, period: per, reps: n } };
    return end;
  }
  /*
   * Hinge checks (cue_checks in exercises.json): the bar's real centre (it rides the hand) stays on a vertical line over the midfoot;
   * the bar is never inside the legs and stays close to them; the spine (pelvis-to-chest angle) stays neutral; the trunk ends vertical,
   * never past it; the body + bar centre of mass stays over the foot. lim overrides the limits for a variant.
   */
  function hingeChecks(fig, v, t, out, lim) {
    lim = merge({ drift: 6, mid: 8, gapMin: -1.5, gapMax: 30, spine: 5, lean: -3, lock: 4 }, lim || {});
    var b = fig.bar.getWorldPosition(new THREE.Vector3()), mz = 0;
    ['L', 'R'].forEach(function (s) { mz += fig.point('an' + s, 0, -26, (T3.HEEL.z + T3.TIP.z) / 2).z / 2; });
    out.barZ = out.barZ || [Infinity, -Infinity]; out.barZ[0] = Math.min(out.barZ[0], b.z); out.barZ[1] = Math.max(out.barZ[1], b.z);
    out.barDrift = out.barZ[1] - out.barZ[0]; out.barToMidfoot = Math.max(out.barToMidfoot || 0, Math.abs(b.z - mz));
    function flag(tag) { var k = tag.replace(/-?[\d.]+/g, '#'); if (!out.some(function (x) { return x.replace(/-?[\d.]+/g, '#') === k; })) out.push(tag); }   // one line per kind, the first value
    if (out.barDrift > lim.drift) flag('hinge: the bar drifts ' + out.barDrift.toFixed(1) + ' units off its vertical line (max ' + lim.drift + '; cue: bar over the midfoot)');
    if (Math.abs(b.z - mz) > lim.mid) flag('hinge: the bar is more than ' + lim.mid + ' units from the midfoot');
    var gap = T3.barLegGap(fig, b, 6, fig.hinge.grip - 12);
    if (gap !== Infinity) {
      out.barGapMin = Math.min(out.barGapMin === undefined ? Infinity : out.barGapMin, gap);
      out.barGapMax = Math.max(out.barGapMax === undefined ? -Infinity : out.barGapMax, gap);
      if (gap < lim.gapMin) flag('hinge: the bar passes into the legs (' + gap.toFixed(1) + ' units)');
      if (gap > lim.gapMax) flag('hinge: the bar is ' + gap.toFixed(0) + ' units off the legs (cue: close to the legs; max ' + lim.gapMax + ')');
    }
    var sf = T3.spineFlex(fig), ta = T3.trunkAngle(fig);
    out.spineFlexMax = Math.max(out.spineFlexMax === undefined ? -Infinity : out.spineFlexMax, sf);
    out.trunkMin = Math.min(out.trunkMin === undefined ? Infinity : out.trunkMin, ta);
    out.trunkMax = Math.max(out.trunkMax === undefined ? -Infinity : out.trunkMax, ta);
    if (lim.spine !== null && Math.abs(sf) > lim.spine) flag('hinge: the spine bends ' + sf.toFixed(1) + ' deg between pelvis and chest (cue: back flat; max ' + lim.spine + ')');
    if (ta < lim.lean) flag('hinge: the trunk leans back past vertical (' + ta.toFixed(1) + ' deg; cue: stand tall, no lean back)');
    var ph = T3.phaseAt(fig.hinge.def, fig.hinge.clock, t);
    if (ph.id === 'lockout' && ph.rep >= 1 && ph.rep <= fig.hinge.clock.reps) {
      out.trunkAtLockout = Math.max(out.trunkAtLockout || 0, Math.abs(ta));
      if (Math.abs(ta) > lim.lock) flag('hinge: the trunk is ' + ta.toFixed(1) + ' deg off vertical at lockout (cue: stand tall; max ' + lim.lock + ')');
    }
    // body + bar (illustrative load: the body's own mass) over the foot: between the heel and the ball
    var c = T3.com(fig).add(b).multiplyScalar(0.5), heel = 0, ball = 0;
    ['L', 'R'].forEach(function (s) { heel += fig.point('an' + s, 0, -26, T3.HEEL.z).z / 2; ball += fig.point('an' + s, 0, -26, T3.BALL.z).z / 2; });
    var rel = (c.z - heel) / (ball - heel);
    out.comOverFoot = out.comOverFoot || [Infinity, -Infinity]; out.comOverFoot[0] = Math.min(out.comOverFoot[0], rel); out.comOverFoot[1] = Math.max(out.comOverFoot[1], rel);
    out.comHeelToBallMin = out.comOverFoot[0]; out.comHeelToBallMax = out.comOverFoot[1];
    if (rel < 0.1 || rel > 0.9) flag('hinge: body + bar centre of mass leaves the foot (' + rel.toFixed(2) + ' of heel-to-ball)');
  }
  T3.hingeChecks = hingeChecks;
  // the deadlift's knees extend first off the floor (the trunk angle barely changes: hips and shoulders rise together), the hips after
  function dlShape(s) { return 1 - Math.pow(1 - s, 2.3); }
  var DL_PHASES = [{ id: 'start', kind: 'hold', label: 'Set', a: 0, b: 0.08, cue: 'Bar over the midfoot' }, { id: 'concentric', kind: 'up', label: 'Pull', a: 0.08, b: 0.44, cue: 'Push the floor away' },
    { id: 'lockout', kind: 'hold', label: 'Lockout', a: 0.44, b: 0.54, cue: 'Stand tall' }, { id: 'eccentric', kind: 'down', label: 'Lower', a: 0.54, b: 0.94, cue: 'Hips back, bar close' },
    { id: 'reset', kind: 'hold', label: 'Floor', a: 0.94, b: 1.0, cue: 'Dead stop' }];
  // reps() runs fn(0 -> 1) then fn(1 -> 0); the deadlift starts on the floor, so its fn maps 0 = floor: the pull is power2, the lowering sine
  var DL_RHYTHM = { down: [0.08, 0.44], up: [0.54, 0.94], downEase: 'power2.inOut', upEase: 'sine.inOut' };
  function dlChecks(lim) {
    return function (fig, v, t, out) {
      hingeChecks(fig, v, t, out, lim);
      // hips and shoulders rise together: from the floor until the bar passes the knees the trunk angle changes by less than 15 deg
      var b = fig.bar.getWorldPosition(new THREE.Vector3()), kn = (fig.world('knL').y + fig.world('knR').y) / 2, ta = T3.trunkAngle(fig);
      if (b.y < kn + 20) {
        out.trunkBelowKnee = out.trunkBelowKnee || [Infinity, -Infinity];
        out.trunkBelowKnee[0] = Math.min(out.trunkBelowKnee[0], ta); out.trunkBelowKnee[1] = Math.max(out.trunkBelowKnee[1], ta);
        out.trunkChangeBelowKnee = out.trunkBelowKnee[1] - out.trunkBelowKnee[0];
        var tag = 'deadlift: the trunk angle changes more than 15 deg before the bar passes the knees (cue: hips and shoulders rise together)';
        if (out.trunkBelowKnee[1] - out.trunkBelowKnee[0] > 15 && out.indexOf(tag) < 0) out.push(tag);
      }
    };
  }
  X3.deadlift = {
    id: 'deadlift', name: 'Conventional barbell deadlift', knowledge: 'deadlift', period: 3.8,
    phaseMap: DL_PHASES, rhythm: DL_RHYTHM,
    acts: { glute: 3, hams: 3, quad: 3, erector: 2, adductor: 2, trap: 1, flexor: 1, abs: 1 },
    peaks: { glute: 0.9, hams: 0.85, quad: 0.8, erector: 0.7, adductor: 0.5, trap: 0.4, flexor: 0.4, abs: 0.35 },
    // side at az 72 (rule 12: the near plate stays clear of the head), the shins and bar from the front three-quarter
    shots: { side: { az: 72, el: 6 }, three: { az: 38, el: 10 }, front: { az: 10, el: 8 }, back: { az: 160, el: 10 }, backThree: { az: 130, el: 14 } },
    build: function (stage, fig, m, o) { return buildHinge(X3.deadlift, stage, fig, m, o, X3.deadlift.solver); },
    solver: { bottom: 98, arm: [-12, 6], phiShape: dlShape, gapTop: 2.5, gapBottom: 3, startBottom: true },
    camera: { target: { tx: 0, ty: 330, tz: 0 }, dist: 2500, fov: 26 },
    checks: dlChecks({})
  };
  // the mistake (exercises.json deadlift error "back-rounds"): the same solver and bar path, only the spine flexes 28 deg at the floor
  X3['deadlift-rounded'] = {
    id: 'deadlift-rounded', name: 'Deadlift, back rounded (mistake)', knowledge: 'deadlift', mistake: 'back-rounds', period: 3.8,
    phaseMap: DL_PHASES, rhythm: DL_RHYTHM, acts: X3.deadlift.acts, peaks: X3.deadlift.peaks, shots: X3.deadlift.shots,
    build: function (stage, fig, m, o) { return buildHinge(X3['deadlift-rounded'], stage, fig, m, o, X3['deadlift-rounded'].solver); },
    solver: merge(X3.deadlift.solver, { round: 28 }),
    camera: X3.deadlift.camera,
    // the variant must SHOW the mistake: the spine flexes at least 20 deg at the floor; everything else holds as in the correct lift
    checks: function (fig, v, t, out) {
      dlChecks({ spine: null })(fig, v, t, out);
      var ph = T3.phaseAt(fig.hinge.def, fig.hinge.clock, t), tag = 'rounded-back variant: the spine flexes under 20 deg at the floor (the mistake is not visible)';
      if ((ph.id === 'start' || ph.id === 'reset') && ph.rep >= 1 && ph.rep <= fig.hinge.clock.reps) {
        var sf = T3.spineFlex(fig);
        out.spineFlexAtFloor = Math.min(out.spineFlexAtFloor === undefined ? Infinity : out.spineFlexAtFloor, sf);
        if (sf < 20 && out.indexOf(tag) < 0) out.push(tag);
      }
    }
  };
  X3['romanian-deadlift'] = {
    id: 'romanian-deadlift', name: 'Romanian deadlift', knowledge: 'romanian-deadlift', period: 3.9,
    phaseMap: [{ id: 'start', kind: 'hold', label: 'Stand tall', a: 0, b: 0.04, cue: 'Soft knees' }, { id: 'eccentric', kind: 'down', label: 'Hips back', a: 0.04, b: 0.54, cue: 'Bar slides down the thighs' },
      { id: 'end-range', kind: 'hold', label: 'Bottom', a: 0.54, b: 0.62, cue: 'Back stays flat' }, { id: 'concentric', kind: 'up', label: 'Hips forward', a: 0.62, b: 0.92, cue: 'Stand tall' },
      { id: 'lockout', kind: 'hold', label: 'Lockout', a: 0.92, b: 1.0, cue: '' }],
    rhythm: { down: [0.04, 0.54], up: [0.62, 0.92] },
    acts: { hams: 3, glute: 3, erector: 2, adductor: 2, quad: 1, trap: 1, flexor: 1 },
    peaks: { hams: 1, glute: 0.8, erector: 0.6, adductor: 0.45, quad: 0.3, trap: 0.35, flexor: 0.4 },
    shots: X3.deadlift.shots,
    build: function (stage, fig, m, o) { return buildHinge(X3['romanian-deadlift'], stage, fig, m, o, X3['romanian-deadlift'].solver); },
    solver: { bottom: 200, arm: [-12, 12], kshape: function (s) { return s * s; }, gapTop: 2.5, gapBottom: 2.5, slack: 6, plate: 98 },
    camera: X3.deadlift.camera,
    checks: function (fig, v, t, out) {
      hingeChecks(fig, v, t, out, {});
      // soft knees that barely move: the knee joint travels little and the knee never bends like a squat
      ['L', 'R'].forEach(function (s) {
        var k = fig.world('kn' + s), fl = 180 - T3.jointAngle(fig, 'th' + s, 'kn' + s, 'an' + s);
        out.kneeZ = out.kneeZ || [Infinity, -Infinity]; out.kneeZ[0] = Math.min(out.kneeZ[0], k.z); out.kneeZ[1] = Math.max(out.kneeZ[1], k.z);
        out.kneeFlex = out.kneeFlex || [Infinity, -Infinity]; out.kneeFlex[0] = Math.min(out.kneeFlex[0], fl); out.kneeFlex[1] = Math.max(out.kneeFlex[1], fl);
      });
      out.kneeTravel = out.kneeZ[1] - out.kneeZ[0]; out.kneeFlexMax = out.kneeFlex[1]; out.kneeFlexMin = out.kneeFlex[0];
      var tag = 'RDL: the knees travel more than 35 units (cue: soft knees that barely move)', tag2 = 'RDL: the knee bends more than 20 deg past its start (cue: soft knees that barely move; it turns into a squat)';
      if (out.kneeZ[1] - out.kneeZ[0] > 35 && out.indexOf(tag) < 0) out.push(tag);
      if (out.kneeFlex[1] - out.kneeFlex[0] > 20 && out.indexOf(tag2) < 0) out.push(tag2);
    }
  };

  // ================================================================ SPLIT STANCE (2026-11-23): split squat, forward lunge
  /*
   * splitSolver(cfg) -> pose(s), s = 0 top .. 1 bottom of a split stance: the front foot (left) flat with its ankle at zF, the back foot
   * (right) on its ball (flat-ankle target zB = zF - stance), the feet cfg.fx either side of the midline (hip-width "train tracks").
   * The pelvis drops STRAIGHT DOWN at hipZ (cue: drop straight down) from yTop (the straighter leg `slack` short of straight) to yBot,
   * where the back knee stops cfg.kneeY above the floor (joint; the skin gap is measured after the build). The back heel rises with
   * depth (hl, the ball stays planted through T3.footRoll and rolls onto the toe tip past the toe-joint limit). hipZ is SOLVED so the
   * front shin ends cfg.shinB degrees forward of vertical (cue: front shin near vertical). Both knees point along their feet (kw).
   * Sagittal two-link legs with the lateral offset folded into the thigh length, as the hinge does. Illustrative, not mocap.
   */
  function splitSolver(cfg) {
    var Lt = Math.sqrt(178 * 178 - (cfg.fx - 40) * (cfg.fx - 40)), Ls = 166, MAX = Lt + Ls - 0.5, yw = cfg.yaw * D2R;
    var zF = cfg.zF, zB = cfg.zF - cfg.stance, pr = cfg.pitch * D2R;
    function backAnkle(hl) { var r = T3.footRoll(hl, 0); return [26 + r.up, zB + r.fwd * Math.cos(yw)]; }
    function knee(H, A) {
      var d = Math.hypot(A[0] - H[0], A[1] - H[1]), dd = Math.min(d, MAX), u = [(A[0] - H[0]) / d, (A[1] - H[1]) / d];
      var b = Math.acos(Math.max(-1, Math.min(1, (Lt * Lt + dd * dd - Ls * Ls) / (2 * Lt * dd)))), n = [-u[1], u[0]];
      if (n[1] < 0) n = [-n[0], -n[1]];
      return { K: [H[0] + Lt * (u[0] * Math.cos(b) + n[0] * Math.sin(b)), H[1] + Lt * (u[1] * Math.cos(b) + n[1] * Math.sin(b))], d: d };
    }
    function hl(s) { return lerp(cfg.hl[0], cfg.hl[1], s); }
    function legs(y, z, s) {
      var H = [y - 6 * Math.cos(pr), z - 6 * Math.sin(pr)], Ab = backAnkle(hl(s)), f = knee(H, [26, zF]), b = knee(H, Ab);
      return { H: H, Kf: f.K, df: f.d, Kb: b.K, db: b.d, Ab: Ab, shin: Math.atan2(f.K[1] - zF, f.K[0] - 26) / D2R };
    }
    function bisect(fn, lo, hi, n) { for (var i = 0; i < (n || 40); i++) { var mid = (lo + hi) / 2; if (fn(mid)) hi = mid; else lo = mid; } return (lo + hi) / 2; }
    function yBotFor(z) { return bisect(function (y) { return legs(y, z, 1).Kb[0] > cfg.kneeY; }, 120, 380); }
    var hipZ = bisect(function (z) { return legs(yBotFor(z), z, 1).shin > cfg.shinB; }, zB, zF);
    var yBot = yBotFor(hipZ) + (cfg.yAdjust || 0);
    var yTop = bisect(function (y) { var g = legs(y, hipZ, 0); return Math.max(g.df, g.db) > Lt + Ls - cfg.slack; }, yBot, 420);
    function pose(s) { var y = lerp(yTop, yBot, s), g = legs(y, hipZ, s); g.y = y; g.z = hipZ; g.hl = hl(s); g.s = s; return g; }
    pose.hipZ = hipZ; pose.yTop = yTop; pose.yBot = yBot; pose.zF = zF; pose.zB = zB;
    return pose;
  }
  T3.splitSolver = splitSolver;
  var SPLIT = { fx: 50, yaw: 4, stance: 360, zF: 200, hl: [26, 62], shinB: 10, kneeY: 30, slack: 3, pitch: 4, lean: 3, kneeGap: 8 };
  /** Dumbbells at the sides: the wrists hang straight below the shoulders (world offsets), so they stay vertical when the trunk tips. */
  function sideDumbbells(fig) {
    var dbs = [EQ.dumbbell(0.9), EQ.dumbbell(0.9)]; fig.hold('L', dbs[0]); fig.hold('R', dbs[1]);
    var a = {}, ox = 118 - fig.spec.shx;
    ['L', 'R'].forEach(function (sd) {
      var sg = sd === 'L' ? 1 : -1;
      a['ik' + sd] = 1; a['hx' + sd] = sg * ox; a['hy' + sd] = -Math.sqrt(236 * 236 - ox * ox); a['hz' + sd] = 2;
      a['px' + sd] = sg * 0.3; a['py' + sd] = 0; a['pz' + sd] = -1; a['gaz' + sd] = 1; a['wr' + sd] = 0;
    });
    return a;
  }
  /**
   * Split-stance build. o.x/o.z place the stance; the split squat starts in the stance, the lunge starts standing with both feet at
   * the back foot's spot and steps the left foot forward. Back-knee clearance is measured on the posed skin and yBot corrected (two
   * passes) so the knee stops cfg.kneeGap above the floor.
   */
  function buildSplit(def, stage, fig, m, o, cfg) {
    o = o || {};
    var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 3, per = o.period || def.period;
    var x0 = o.x || 0, z0 = o.z || 0;
    fig.roles(def.acts);
    var arms = sideDumbbells(fig);
    var solve = splitSolver(cfg), held = fig.supports ? fig.supports.splice(0) : [];
    function stanceKeys(s, wFront) {
      var g = solve(s), k = { x: x0, y: g.y + 0, z: z0 + g.z, pitch: cfg.pitch, lean: cfg.lean, neckF: -cfg.pitch - cfg.lean,
        fxL: x0 + cfg.fx, fzL: z0 + solve.zF, fyL: 0, fyawL: cfg.yaw, hlL: 0, kwL: 1,
        fxR: x0 - cfg.fx, fzR: z0 + solve.zB, fyR: 0, fyawR: -cfg.yaw, hlR: g.hl, kwR: 1, kvL: (cfg.kv || 0) * smooth(s) };
      return k;
    }
    // back-knee clearance on the skin: correct yBot so the lowest knee skin sits kneeGap above the floor
    var base = merge(arms, { ikLegL: 1, ikLegR: 1 });
    for (var pass = 0; pass < 2; pass++) {
      fig.apply(pref(p, merge(base, stanceKeys(1))));
      var low = T3.skinLow(fig, ['knR', 'thR']).y;
      cfg = merge(cfg, { yAdjust: (cfg.yAdjust || 0) + cfg.kneeGap - low });
      solve = splitSolver(cfg);
    }
    if (fig.supports) Array.prototype.push.apply(fig.supports, held);
    fig.apply({});
    fig.solve = solve; fig.split = { def: def, clock: { at: at, period: per, reps: n }, cfg: cfg, x0: x0, z0: z0 };
    m.base(pref(p, base));
    if (!cfg.step) {
      m.base(pref(p, stanceKeys(0)));
      var end = reps(m, at, per, n, function (s) { return pref(p, stanceKeys(s)); }, def.rhythm);
      envelope(m, p, o.peaks || def.peaks, at, per, n);
      fig.pose = function (s) { return pref(p, stanceKeys(s)); };
      return end;
    }
    return lungeTimeline(def, fig, m, o, cfg, solve, stanceKeys, p, at, per, n);
  }
  /*
   * Forward lunge: one rep = step out (the left foot peels heel-first off the floor, swings forward 30 units high and lands HEEL first:
   * heel rocker, T3.footRoll with hl < 0, then rolls flat), drop straight down, hold, drive up, step back (the foot lifts flat and swings
   * home). The back foot rolls up onto its ball as the hips travel forward. Every value is a function of one eased progress per phase.
   */
  function lungeTimeline(def, fig, m, o, cfg, solve, stanceKeys, p, at, per, n) {
    var x0 = o.x || 0, z0 = o.z || 0, F = def.phaseFrac;
    var stand = { x: x0, y: cfg.standY, z: z0 + solve.zB, pitch: 0, lean: 0, neckF: 0,
      fxL: x0 + cfg.fx, fzL: z0 + solve.zB, fyL: 0, fyawL: cfg.yaw, hlL: 0, kwL: 1,
      fxR: x0 - cfg.fx, fzR: z0 + solve.zB, fyR: 0, fyawR: -cfg.yaw, hlR: 0, kwR: 1 };
    var top = stanceKeys(0);
    function mix(a, b, w) { var r = {}; for (var k in b) r[k] = typeof b[k] === 'number' && typeof a[k] === 'number' ? lerp(a[k], b[k], w) : b[k]; return r; }
    // the pelvis never rises above what both legs can reach (2 units short of straight), blended with a soft minimum so it stays smooth
    var LMAX = Math.sqrt(178 * 178 - (cfg.fx - 40) * (cfg.fx - 40)) + 166 - 2;
    function reachCap(b) {
      var cap = Infinity;
      ['L', 'R'].forEach(function (s) {
        var sg = s === 'L' ? 1 : -1, r = T3.footRoll(b['hl' + s], 0), yw = b['fyaw' + s] * D2R;
        var ay = b['fy' + s] + 26 + r.up, az = b['fz' + s] + r.fwd * Math.cos(yw), ax = b['fx' + s] + r.fwd * Math.sin(yw);
        var dx = ax - (b.x + sg * 40), dz = az - (b.z - 6 * Math.sin(b.pitch * D2R));
        cap = Math.min(cap, ay + Math.sqrt(Math.max(0, LMAX * LMAX - dx * dx - dz * dz)) + 6 * Math.cos(b.pitch * D2R));
      });
      var k = 3; b.y = -k * Math.log(Math.exp(-b.y / k) + Math.exp(-cap / k));
      return b;
    }
    // out: w 0..1 from standing to the top of the split stance; the front foot's own profile rides on top of the pelvis blend
    function stepOut(w) {
      // the pelvis travels forward with the step and drops only as the foot lands (dropping first reads as a squat before the step)
      var b = mix(stand, top, smooth((w - 0.1) / 0.9)), q = Math.max(0, Math.min(1, (w - 0.12) / 0.76));
      b.y = lerp(stand.y, top.y, smooth((w - 0.45) / 0.55));
      b.fzL = lerp(z0 + solve.zB, z0 + solve.zF, smooth(q)); b.fyL = 30 * Math.pow(Math.sin(Math.PI * q), 2);
      b.hlL = w < 0.12 ? 16 * smooth(w / 0.12) : lerp(16, -14, smooth(q));
      b.hlR = top.hlR * smooth(w);
      return pref(p, reachCap(b));
    }
    function stepBack(r) {                                                // r 0..1 from the split top back to standing
      var b = mix(top, stand, smooth(r / 0.9)), q = Math.max(0, Math.min(1, r / 0.88));
      b.y = lerp(top.y, stand.y, smooth(r / 0.55));                      // rise off the front foot first, then bring it home
      b.fzL = lerp(z0 + solve.zF, z0 + solve.zB, smooth(q)); b.fyL = 30 * Math.pow(Math.sin(Math.PI * q), 2);
      b.hlL = 10 * Math.sin(Math.PI * q); b.hlR = top.hlR * (1 - smooth(r));
      return pref(p, reachCap(b));
    }
    function down(s) { var k = stanceKeys(s); k.hlL = -14 * (1 - smooth(s / 0.35)); return pref(p, reachCap(k)); }   // heel strike rolls flat
    function rise(s) { return pref(p, reachCap(stanceKeys(s))); }
    m.base(pref(p, reachCap(merge(stand, {}))));
    for (var r0 = 0; r0 < n; r0++) {
      var t0 = at + r0 * per;
      // eccentric: step out then drop (one eased progress, split at F.split)
      m.path(t0 + F.down[0] * per, (F.down[1] - F.down[0]) * per, function (e) { return e < F.split ? stepOut(e / F.split) : down((e - F.split) / (1 - F.split)); }, 'sine.inOut');
      m.path(t0 + F.up[0] * per, (F.up[1] - F.up[0]) * per, function (e) { return e < F.rise ? rise(1 - e / F.rise) : stepBack((e - F.rise) / (1 - F.rise)); }, 'power2.inOut');
    }
    envelope(m, p, o.peaks || def.peaks, at, per, n);
    fig.pose = function (s) { return down(s); };
    fig.step = { out: stepOut, back: stepBack };
    return at + n * per;
  }
  /*
   * Split-stance checks (exercises.json cue_checks): front shin angle at the bottom within [0, 25] deg forward (near vertical to slightly
   * forward); the front knee over the line of the foot (15 units); the trunk within 12 deg of vertical; the feet hip-width apart side to
   * side (>= 80 between ankles) and planted (the front ankle and the back ball never slide); the back knee stops 2-25 units above the
   * floor; the hips drop straight down at the bottom (hip z within 3 units through the last 40% of the descent); the centre of mass
   * stays over the base (between the back ball and the front toe tip). Lunge: only while both feet are down.
   */
  function splitChecks(fig, v, t, out) {
    var S = fig.split, ph = T3.phaseAt(S.def, S.clock, t), inSet = ph.rep >= 1 && ph.rep <= S.clock.reps, pre = fig.id ? fig.id + '.' : '';
    function flag(tag) { var k = tag.replace(/-?[\d.]+/g, '#'); if (!out.some(function (x) { return x.replace(/-?[\d.]+/g, '#') === k; })) out.push(tag); }
    var front = (v[pre + 'fyL'] || 0) < 0.5 && Math.abs((v[pre + 'fzL'] || 0) - (S.z0 + fig.solve.zF)) < 0.5;     // the front foot is down in the stance
    if (!front) return;
    var kn = fig.world('knL'), an = fig.world('anL'), shin = Math.atan2(kn.z - an.z, kn.y - an.y) / D2R;
    var d = fig.solve(1), atBottom = inSet && ph.id === 'end-range';
    if (atBottom) {
      out.frontShinBottom = out.frontShinBottom === undefined ? shin : Math.max(out.frontShinBottom, shin);
      if (shin < 0 || shin > 25) flag('split stance: front shin ' + shin.toFixed(1) + ' deg from vertical at the bottom (cue: near vertical to slightly forward, 0-25)');
      var low = T3.skinLow(fig, ['knR', 'thR']).y;
      out.backKneeGap = low;
      if (low < 2 || low > 25) flag('split stance: the back knee stops ' + low.toFixed(1) + ' units above the floor (2-25: just above, never touching)');
    }
    var tmp = { maxKneeOff: out.frontKneeOff || 0 }, yw = (v[pre + 'fyawL'] || 0) * D2R, lat = (kn.x - an.x) * Math.cos(yw) - (kn.z - an.z) * Math.sin(yw);
    out.frontKneeOff = Math.max(tmp.maxKneeOff, Math.abs(lat));
    out.frontKneeLat = Math.min(out.frontKneeLat === undefined ? Infinity : out.frontKneeLat, lat);
    if (S.def.kneeLimit !== null && Math.abs(lat) > 15) flag('split stance: the front knee drifts ' + lat.toFixed(1) + ' units off the line of the foot (cue: knee in line with the toes)');
    var ta = T3.trunkAngle(fig);
    out.trunkMax = Math.max(out.trunkMax === undefined ? -Infinity : out.trunkMax, Math.abs(ta));
    if (Math.abs(ta) > 12) flag('split stance: the trunk is ' + ta.toFixed(1) + ' deg off vertical (cue: stay tall)');
    var c = T3.contacts(fig), width = Math.abs(c.ankleL[0] - c.ankleR[0]);
    out.footWidth = Math.min(out.footWidth === undefined ? Infinity : out.footWidth, width);
    if (width < 80) flag('split stance: the feet are ' + width.toFixed(0) + ' units apart side to side (cue: hip-width, not a tightrope; min 80)');
    var ball = c.tipR, ak = fig.point('anL', 0, T3.HEEL.y, T3.HEEL.z).toArray();          // the back toe tip and the front heel never move
    if (!out._ref) Object.defineProperty(out, '_ref', { value: { ball: ball, ak: ak }, enumerable: false });
    var slide = Math.max(Math.hypot(ball[0] - out._ref.ball[0], ball[2] - out._ref.ball[2]), Math.hypot(ak[0] - out._ref.ak[0], ak[2] - out._ref.ak[2]));
    out.footSlide = Math.max(out.footSlide || 0, slide);
    if (slide > 1.5) flag('split stance: a planted foot slides ' + slide.toFixed(1) + ' units (front heel or back toe tip)');
    if (inSet && ph.id === 'eccentric' && ph.k > (S.def.dropFrom || 0.6)) {
      var hz = fig.world('hips').z;
      if (!out._hz) Object.defineProperty(out, '_hz', { value: [hz, hz], enumerable: false, writable: true });
      out._hz = [Math.min(out._hz[0], hz), Math.max(out._hz[1], hz)]; out.hipDriftBottom = out._hz[1] - out._hz[0];
      if (out.hipDriftBottom > 3) flag('split stance: the hips travel ' + out.hipDriftBottom.toFixed(1) + ' units forward or back near the bottom (cue: drop straight down)');
    }
    var com = T3.com(fig), tip = c.tipL[2], rel = (com.z - ball[2]) / (tip - ball[2]);
    out.comOverBase = out.comOverBase || [Infinity, -Infinity]; out.comOverBase[0] = Math.min(out.comOverBase[0], rel); out.comOverBase[1] = Math.max(out.comOverBase[1], rel);
    out.comBaseMin = out.comOverBase[0]; out.comBaseMax = out.comOverBase[1];
    if (rel < 0.05 || rel > 0.95) flag('split stance: the centre of mass leaves the base (' + rel.toFixed(2) + ' of back ball to front toe)');
  }
  T3.splitChecks = splitChecks;
  // the mistake (exercises.json split-squat error "knee-caves"): the same solver, only the front knee's pole turns 12 deg toward the
  // midline as the hips drop (pose key kvL), so the knee collapses inward over the arch

  X3['split-squat'] = {
    id: 'split-squat', name: 'Split squat', knowledge: 'split-squat', period: 3.2,
    phaseMap: [{ id: 'start', kind: 'hold', label: 'Tall', a: 0, b: 0.05, cue: 'Feet hip-width, like train tracks' }, { id: 'eccentric', kind: 'down', label: 'Lower', a: 0.05, b: 0.50, cue: 'Back knee straight down' },
      { id: 'end-range', kind: 'hold', label: 'Bottom', a: 0.50, b: 0.57, cue: 'Front foot flat' }, { id: 'concentric', kind: 'up', label: 'Drive up', a: 0.57, b: 0.90, cue: 'Push through the front foot' },
      { id: 'lockout', kind: 'hold', label: 'Top', a: 0.90, b: 1.0, cue: '' }],
    rhythm: { down: [0.05, 0.50], up: [0.57, 0.90] },
    acts: { quad: 3, glute: 3, hams: 2, glutemed: 1, adductor: 1, erector: 1, flexor: 1 },
    peaks: { quad: 1, glute: 0.85, hams: 0.5, glutemed: 0.4, adductor: 0.35, erector: 0.35, flexor: 0.3 },
    shots: { side: { az: 90, el: 6 }, three: { az: 40, el: 10 }, front: { az: 8, el: 8 }, back: { az: 180, el: 8 }, backThree: { az: 140, el: 12 } },
    build: function (stage, fig, m, o) { return buildSplit(X3['split-squat'], stage, fig, m, o, merge(SPLIT, {})); },
    camera: { target: { tx: 0, ty: 360, tz: 40 }, dist: 2500, fov: 26 },
    checks: splitChecks
  };
  X3['split-squat-valgus'] = {
    id: 'split-squat-valgus', name: 'Split squat, front knee caving in (mistake)', knowledge: 'split-squat', mistake: 'knee-caves', period: 3.2, kneeLimit: null,
    phaseMap: X3['split-squat'].phaseMap, rhythm: X3['split-squat'].rhythm, acts: X3['split-squat'].acts, peaks: X3['split-squat'].peaks,
    shots: { front: { az: 8, el: 8 }, three: { az: 40, el: 10 }, side: { az: 90, el: 6 }, back: { az: 180, el: 8 }, frontLow: { az: 0, el: 2 } },
    build: function (stage, fig, m, o) { return buildSplit(X3['split-squat-valgus'], stage, fig, m, o, merge(SPLIT, { kv: 12 })); },
    camera: X3['split-squat'].camera,
    // the variant must SHOW the mistake: at the bottom the front knee sits at least 15 units inside the line of the foot
    checks: function (fig, v, t, out) {
      splitChecks(fig, v, t, out);
      var S = fig.split, ph = T3.phaseAt(S.def, S.clock, t), tag = 'knee-caves variant: the front knee stays within 15 units of the foot line at the bottom (the mistake is not visible)';
      if (ph.id === 'end-range' && ph.rep >= 1 && ph.rep <= S.clock.reps) {
        var kn = fig.world('knL'), an = fig.world('anL'), yw = (v[(fig.id ? fig.id + '.' : '') + 'fyawL'] || 0) * D2R, lat = (kn.x - an.x) * Math.cos(yw) - (kn.z - an.z) * Math.sin(yw);
        out.kneeInwardAtBottom = Math.max(out.kneeInwardAtBottom || 0, -lat);
        if (-lat < 15 && out.indexOf(tag) < 0) out.push(tag);
      }
    }
  };
  X3['forward-lunge'] = {
    id: 'forward-lunge', name: 'Forward lunge', knowledge: 'forward-lunge', period: 4.0, dropFrom: 0.8,
    // eccentric = step out + drop (F.split of it is the step); concentric = drive up + step back (F.rise of it is the rise)
    phaseFrac: { down: [0.04, 0.50], up: [0.56, 0.94], split: 0.5, rise: 0.45 },
    phaseMap: [{ id: 'start', kind: 'hold', label: 'Stand tall', a: 0, b: 0.04, cue: '' }, { id: 'eccentric', kind: 'down', label: 'Step and lower', a: 0.04, b: 0.50, cue: 'Land heel first, drop straight down' },
      { id: 'end-range', kind: 'hold', label: 'Bottom', a: 0.50, b: 0.56, cue: 'Whole front foot planted' }, { id: 'concentric', kind: 'up', label: 'Push back', a: 0.56, b: 0.94, cue: 'Push through the front foot' },
      { id: 'reset', kind: 'hold', label: 'Feet together', a: 0.94, b: 1.0, cue: '' }],
    acts: X3['split-squat'].acts, peaks: X3['split-squat'].peaks, shots: X3['split-squat'].shots,
    build: function (stage, fig, m, o) { return buildSplit(X3['forward-lunge'], stage, fig, m, o, merge(SPLIT, { step: true, standY: 373 })); },
    camera: X3['split-squat'].camera,
    checks: splitChecks
  };

  // ================================================================ PRONE (2026-11-23): push-up (and hips sagging), plank on a mat
  /** A thin exercise mat on the floor (Cobalt Sculpt: one plane in the pad colour). o: {x, z, w, l, h}; length along z. */
  EQ.mat = function (o) {
    o = o || {};
    var g = new THREE.Group(), h = o.h || 4;
    var slab = new THREE.Mesh(new THREE.BoxGeometry(o.w || 190, h, o.l || 620), T3.material(T3.colors.pad)); slab.position.y = h / 2; g.add(slab);
    g.position.set(o.x || 0, 0, o.z || 0); g.userData.top = h;
    return g;
  };
  /*
   * proneSolver(cfg): the body as a chain from the planted toes to the shoulders, in the sagittal (y, z) plane, head toward +z.
   * chain(beta, k, sag): the leg chord rises beta degrees from the ankle; the ankle follows from the toe tip (fixed at cfg.tipZ) and the
   * foot's pitch hl = 90 - beta + cfg.pf (the foot rolls on its tip past the toe-joint limit, T3.footRoll); the knee bends k degrees;
   * the trunk chord rises beta + sag (sag > 0: the hips drop below the line, the hips-sagging mistake), the lower back taking
   * arch * sag of it as extension. betaFor(Sy) solves the body angle that puts the shoulders at height Sy: the push-up is a lever
   * rotating about the toes, and its depth is the shoulder height. Illustrative, not mocap.
   */
  function proneSolver(cfg) {
    var Lt = Math.sqrt(178 * 178 - (cfg.fx - 40) * (cfg.fx - 40)), Ls = 166;
    function chord(k) { return Math.sqrt(Lt * Lt + Ls * Ls + 2 * Lt * Ls * Math.cos(k * D2R)); }
    function V(p, lean) { var t = trunkPt(p, lean, cfg.ly, -2); return [6 * Math.cos(p * D2R) + t[0], 6 * Math.sin(p * D2R) + t[1]]; }
    function pitchFor(theta, lean) {                                         // the pelvis pitch whose trunk chord rises theta degrees toward +z
      var lo = -40, hi = 160;
      for (var i = 0; i < 44; i++) { var mid = (lo + hi) / 2, v = V(mid, lean); if (Math.atan2(v[0], v[1]) / D2R > theta) lo = mid; else hi = mid; }
      return (lo + hi) / 2;
    }
    function chain(beta, k, sag, hlSet) {
      var hl = hlSet === undefined ? 90 - beta + cfg.pf : hlSet, r = T3.footRoll(hl, 0), A = [cfg.fy + 26 + r.up, cfg.tipZ - T3.TIP.z + r.fwd];
      var d = chord(k), H = [A[0] + d * Math.sin(beta * D2R), A[1] + d * Math.cos(beta * D2R)];
      var lean = -(cfg.arch || 0) * sag, p = pitchFor(beta + sag, lean), v = V(p, lean);
      return { A: A, H: H, S: [H[0] + v[0], H[1] + v[1]], R: [H[0] + 6 * Math.cos(p * D2R), H[1] + 6 * Math.sin(p * D2R)], p: p, lean: lean, hl: hl, beta: beta, k: k, sag: sag };
    }
    function betaFor(Sy, k, sag, hlSet) {
      var lo = -15, hi = 70;
      for (var i = 0; i < 44; i++) { var mid = (lo + hi) / 2; if (chain(mid, k, sag, hlSet).S[0] > Sy) hi = mid; else lo = mid; }
      return (lo + hi) / 2;
    }
    return { chain: chain, betaFor: betaFor, at: function (Sy, k, sag, hlSet) { return chain(betaFor(Sy, k, sag, hlSet), k, sag, hlSet); } };
  }
  T3.proneSolver = proneSolver;
  /** Prone pose keys from a chain: root, trunk, the toes (tip planted), knees bending toward the floor. */
  function proneKeys(c, cfg, x0, z0) {
    return { x: x0, y: c.R[0], z: z0 + c.R[1], pitch: c.p, lean: c.lean, neckF: cfg.neck || 0, headF: 0, yaw: 0, roll: 0,
      fxL: x0 + cfg.fx, fzL: z0 + cfg.tipZ - T3.TIP.z, fyL: cfg.fy, fyawL: 0, hlL: c.hl, kfL: 0, kwL: 0,
      fxR: x0 - cfg.fx, fzR: z0 + cfg.tipZ - T3.TIP.z, fyR: cfg.fy, fyawR: 0, hlR: c.hl, kfR: 0, kwR: 0 };
  }
  /** Signed distance (units) of the hip joint from the shoulder-to-ankle line, in the sagittal plane: < 0 sags, > 0 pikes. */
  T3.hipLine = function (fig) {
    var s = fig.world('shL').add(fig.world('shR')).multiplyScalar(0.5), a = fig.world('anL').add(fig.world('anR')).multiplyScalar(0.5);
    var h = fig.world('thL').add(fig.world('thR')).multiplyScalar(0.5);
    var dz = s.z - a.z, dy = s.y - a.y, L = Math.hypot(dz, dy);
    return ((h.y - a.y) * dz - (h.z - a.z) * dy) / L;
  };
  /**
   * Wrist keys that lay a palm flat (palm down, fingers forward and `tilt` deg down) for a world shoulder S, wrist W and elbow pole: the
   * elbow is solved exactly as the rig's arm IK solves it, the forearm frame follows (x = the elbow axis), and the wrist flexion
   * and forearm roll are read off it (the hand cannot deviate sideways, so the hand axis is the nearest one in the forearm's plane).
   */
  function palmFrame(S, W, poleW, tilt) {
    var d = W.clone().sub(S), dl = d.length(), dd = Math.min(239.5, Math.max(28.5, dl)), u = d.clone().divideScalar(dl);
    var pole = poleW.clone().addScaledVector(u, -poleW.dot(u)).normalize();
    var be = Math.acos(Math.max(-1, Math.min(1, (134 * 134 + dd * dd - 106 * 106) / (2 * 134 * dd))));
    var E = S.clone().addScaledVector(u.clone().multiplyScalar(Math.cos(be)).addScaledVector(pole, Math.sin(be)).normalize(), 134);
    var up = E.clone().sub(S).normalize(), fo = W.clone().sub(E).normalize();
    var zU = fo.clone().addScaledVector(up, -fo.dot(up)).normalize(), xF = new THREE.Vector3().crossVectors(up.clone().negate(), zU).normalize();
    var yF = E.clone().sub(W).normalize(), zF = new THREE.Vector3().crossVectors(xF, yF).normalize();
    var dh = new THREE.Vector3(0, -Math.sin(tilt * D2R), Math.cos(tilt * D2R)), wr = Math.atan2(dh.dot(zF), -dh.dot(yF));
    var w2 = yF.clone().multiplyScalar(Math.sin(wr)).addScaledVector(zF, Math.cos(wr)), g = new THREE.Vector3(0, -1, 0);
    var pr = Math.atan2(g.dot(xF), g.dot(w2));
    // lowest point of the hand (palm and finger ellipsoids of the skin, anatomy3d.js) in this frame: keeps a planted palm planted
    var L = yF.clone().multiplyScalar(-Math.cos(wr)).addScaledVector(zF, Math.sin(wr)), N = xF.clone().multiplyScalar(Math.sin(pr)).addScaledVector(w2, Math.cos(pr));
    var Xh = new THREE.Vector3().crossVectors(L, N).normalize();
    var P = W.clone().addScaledVector(L, 24), Fc = W.clone().addScaledVector(L, 46).addScaledVector(N, 6);
    var low = Math.min(P.y - Math.hypot(19 * Xh.y, 24 * L.y, 12 * N.y), Fc.y - Math.hypot(16 * Xh.y, 15 * L.y, 11 * N.y));
    return { wr: wr / D2R, pr: pr / D2R, low: low };
  }
  function palmFlat(sd, S, W, poleW, tilt, lowTarget) {
    if (lowTarget !== undefined) {                                       // the tilt that keeps the hand's lowest point where it was planted
      var lo = -30, hi = 75;
      for (var i = 0; i < 30; i++) { var mid = (lo + hi) / 2; if (palmFrame(S, W, poleW, mid).low > lowTarget) lo = mid; else hi = mid; }
      tilt = (lo + hi) / 2;
    }
    var f = palmFrame(S, W, poleW, tilt), r = {};
    r['wr' + sd] = f.wr; r['pr' + sd] = (sd === 'L' ? 1 : -1) * f.pr;
    return r;
  }
  T3.palmFrame = palmFrame;
  T3.palmFlat = palmFlat;
  function flagOnce(out, tag) { var k = tag.replace(/-?[\d.]+/g, '#'); if (!out.some(function (x) { return x.replace(/-?[\d.]+/g, '#') === k; })) out.push(tag); }
  function range(out, key, v) { var r = out[key] || (out[key] = [Infinity, -Infinity]); r[0] = Math.min(r[0], v); r[1] = Math.max(r[1], v); return r; }

  /*
   * Push-up: hands planted just outside the shoulders and under them at the top; the depth is the shoulder height, from arms long
   * (wrist 238.5 off the shoulder, soft elbows) to the elbow at cfg.elbow degrees; the body rotates about the toes as one line. The
   * wrist height is measured on the posed skin (the palm rests on the floor). The elbows point back and out (about 45 deg from the
   * trunk, not flared). cfg.sag > 0 makes the hips-sagging mistake with the same solver.
   */
  function buildPushup(def, stage, fig, m, o, cfg) {
    o = o || {};
    var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 3, per = o.period || def.period, x0 = o.x || 0, z0 = o.z || 0, S = fig.spec;
    cfg = merge({ fx: 45, tipZ: -380, fy: 0, pf: 8, knee: 8, ly: S.shy - 150, elbow: 140, neck: -12, sag: 0, arch: 0.5, wrist: 16, handOut: 28 }, cfg);
    fig.roles(def.acts);
    var sol = proneSolver(cfg), hx = S.shx + cfg.handOut, wy = cfg.wrist, wz = 0, palmLow;
    function sag(s) { return cfg.sag * smooth(s); }                      // the mistake grows with depth (worst at the bottom)
    function arms(c, wyS) {
      var a = {};
      ['L', 'R'].forEach(function (sd) {
        var sg = sd === 'L' ? 1 : -1;
        a['ik' + sd] = 1; a['hx' + sd] = sg * (hx - S.shx); a['hy' + sd] = wyS - c.S[0]; a['hz' + sd] = z0 + wz - (z0 + c.S[1]);
        a['px' + sd] = sg * 0.62; a['py' + sd] = 0.35; a['pz' + sd] = -0.7; a['gax' + sd] = 0;
        merge2(a, palmFlat(sd, new THREE.Vector3(sg * S.shx, c.S[0], c.S[1]), new THREE.Vector3(sg * hx, wyS, wz), new THREE.Vector3(sg * 0.62, 0.35, -0.7), 15, palmLow));
      });
      return a;
    }
    var yTop, yBot;
    function solveDepth() {
      // top: wrist 238.5 from the shoulder; bottom: the elbow at cfg.elbow degrees (wrist-shoulder distance from the arm lengths)
      var dTop = 238.5, dBot = Math.sqrt(134 * 134 + 106 * 106 - 2 * 134 * 106 * Math.cos((180 - cfg.elbow) * D2R));
      function dist(Sy, s) { var c = sol.at(Sy, cfg.knee, sag(s)); return Math.hypot(hx - S.shx, wy - c.S[0], wz - c.S[1]); }
      function solveY(dd, s) { var lo = wy, hi = wy + 300; for (var i = 0; i < 44; i++) { var mid = (lo + hi) / 2; if (dist(mid, s) > dd) hi = mid; else lo = mid; } return (lo + hi) / 2; }
      wz = sol.at(wy + dTop, cfg.knee, 0).S[1] + (cfg.handFwd || 0);
      for (var it = 0; it < 3; it++) { yTop = solveY(dTop, 0); wz = sol.at(yTop, cfg.knee, 0).S[1] + (cfg.handFwd || 0); }
      yBot = solveY(dBot, 1);
      var c0 = sol.at(yTop, cfg.knee, 0);
      palmLow = palmFrame(new THREE.Vector3(S.shx, c0.S[0], c0.S[1]), new THREE.Vector3(hx, wy, wz), new THREE.Vector3(0.62, 0.35, -0.7), 15).low;
    }
    function keys(s) {
      var c = sol.at(lerp(yTop, yBot, s), cfg.knee, sag(s));
      return pref(p, merge(proneKeys(c, cfg, x0, z0), arms(c, wy + corrAt(s))));
    }
    // the palm rests on the floor: wrist height measured on the posed skin (lowest hand point 0.5 above the floor), two passes
    var held = fig.supports ? fig.supports.splice(0) : [], corr = [0, 0, 0, 0, 0];
    // depth correction of the wrist height, measured on the posed skin at five depths (rule 28): the palm model in palmFrame is an
    // analytic approximation of the hand, and an arm or hand change in the rig moved the real palm up to 2 units into the floor at
    // depth (2026-11-24, with the shoulder-girdle work in progress). Blended with smoothstep between samples, so it stays C1 in s.
    function corrAt(s) { var x = Math.max(0, Math.min(1, s)) * 4, k = Math.min(3, Math.floor(x)), f = smooth(x - k); return corr[k] + (corr[k + 1] - corr[k]) * f; }
    for (var pass = 0; pass < 3; pass++) {
      solveDepth();
      fig.apply(keys(0));
      wy += 0.5 - Math.min(T3.skinLow(fig, ['handL']).y, T3.skinLow(fig, ['handR']).y);
    }
    solveDepth();
    for (var cp = 0; cp < 2; cp++) for (var k = 0; k <= 4; k++) { fig.apply(keys(k / 4)); corr[k] += 0.5 - Math.min(T3.skinLow(fig, ['handL']).y, T3.skinLow(fig, ['handR']).y); }
    if (fig.supports) Array.prototype.push.apply(fig.supports, held);
    fig.apply({});
    m.base(keys(0));
    var end = reps(m, at, per, n, keys, def.rhythm);
    envelope(m, p, o.peaks || def.peaks, at, per, n);
    fig.pose = keys; fig.prone = { def: def, clock: { at: at, period: per, reps: n }, cfg: cfg, hand: [hx, wy, z0 + wz] };
    return end;
  }
  function pushupChecks(fig, v, t, out, lim) {
    lim = merge({ line: 8, sagMin: null }, lim || {});
    var P = fig.prone, ph = T3.phaseAt(P.def, P.clock, t), inSet = ph.rep >= 1 && ph.rep <= P.clock.reps;
    var hl = T3.hipLine(fig);
    range(out, 'hipLine', hl); out.hipLineMin = out.hipLine[0]; out.hipLineMax = out.hipLine[1];
    if (lim.line !== null && Math.abs(hl) > lim.line) flagOnce(out, 'push-up: the hips are ' + hl.toFixed(1) + ' units off the shoulder-ankle line (cue: one straight line head to heels; max ' + lim.line + ')');
    ['L', 'R'].forEach(function (s) {
      var w = fig.world('hand' + s), sh = fig.world('sh' + s), e = fig.world('el' + s);
      if (!out['_w' + s]) Object.defineProperty(out, '_w' + s, { value: w.clone() });
      var slide = Math.hypot(w.x - out['_w' + s].x, w.z - out['_w' + s].z);
      out.handSlide = Math.max(out.handSlide || 0, slide);
      if (slide > 1.5) flagOnce(out, 'push-up: a planted hand slides ' + slide.toFixed(1) + ' units');
      if (inSet && (ph.id === 'lockout' || ph.id === 'start')) {
        out.handUnderShoulder = Math.max(out.handUnderShoulder || 0, Math.abs(w.z - sh.z));
        var outx = Math.abs(w.x) - Math.abs(sh.x);
        range(out, 'handOutside', outx); out.handOutsideMin = out.handOutside[0]; out.handOutsideMax = out.handOutside[1];
        if (Math.abs(w.z - sh.z) > 12) flagOnce(out, 'push-up: at the top the hand is ' + (w.z - sh.z).toFixed(1) + ' units from under the shoulder (cue: hands under the shoulders; max 12)');
        if (outx < 5 || outx > 45) flagOnce(out, 'push-up: the hands are ' + outx.toFixed(0) + ' units outside the shoulders (cue: just outside shoulder width, 5-45)');
      }
      if (inSet && ph.id === 'end-range') {
        // elbow flare: the upper arm's angle from the body's long axis, seen from above (0 tucked, 90 straight out to the side)
        var fl = Math.atan2(Math.abs(e.x - sh.x), Math.abs(e.z - sh.z)) / D2R;
        range(out, 'elbowFlare', fl); out.elbowFlareMax = out.elbowFlare[1];
        if (fl > 60) flagOnce(out, 'push-up: the elbows flare ' + fl.toFixed(0) + ' deg from the trunk (cue: angled back, not straight out; max 60)');
        var ef = 180 - T3.jointAngle(fig, 'sh' + s, 'el' + s, 'hand' + s);
        range(out, 'elbowAtBottom', ef); out.elbowAtBottomMin = out.elbowAtBottom[0];
        if (ef < 90) flagOnce(out, 'push-up: the elbows only bend ' + ef.toFixed(0) + ' deg at the bottom (a half rep)');
      }
    });
    var hand = Math.min(T3.skinLow(fig, ['handL']).y, T3.skinLow(fig, ['handR']).y);
    range(out, 'handOnFloor', hand); out.handLowMin = out.handOnFloor[0]; out.handLowMax = out.handOnFloor[1];
    if (hand < -1.5 || hand > 3) flagOnce(out, 'push-up: the hands are ' + hand.toFixed(1) + ' units off the floor (palms planted)');
    if (lim.sagMin !== null && inSet && ph.id === 'end-range') {
      if (hl > lim.sagMin) flagOnce(out, 'hips-sag variant: the hips only drop ' + (-hl).toFixed(1) + ' units below the line at the bottom (the mistake is not visible; needs ' + (-lim.sagMin) + ')');
    }
  }
  T3.pushupChecks = pushupChecks;
  var PU_PHASES = [{ id: 'lockout', kind: 'hold', label: 'Top', a: 0, b: 0.05, cue: 'Hands under the shoulders' }, { id: 'eccentric', kind: 'down', label: 'Lower', a: 0.05, b: 0.47, cue: 'Elbows angled back' },
    { id: 'end-range', kind: 'hold', label: 'Bottom', a: 0.47, b: 0.53, cue: 'Body one straight line' }, { id: 'concentric', kind: 'up', label: 'Push', a: 0.53, b: 0.88, cue: 'Push the floor away' },
    { id: 'lockout', kind: 'hold', label: 'Top', a: 0.88, b: 1.0, cue: '' }];
  X3['push-up'] = {
    id: 'push-up', name: 'Push-up', knowledge: 'push-up', period: 3.0, phaseMap: PU_PHASES,
    rhythm: { down: [0.05, 0.47], up: [0.53, 0.88] },
    acts: { pec: 3, triceps: 3, 'delt-front': 3, serratus: 2, abs: 2, oblique: 1 },
    peaks: { pec: 1, triceps: 0.9, 'delt-front': 0.7, serratus: 0.5, abs: 0.45, oblique: 0.35 },
    shots: { side: { az: 90, el: 8 }, three: { az: 45, el: 14 }, front: { az: 10, el: 12 }, back: { az: 180, el: 12 }, low: { az: 75, el: 2 }, above: { az: 30, el: 60 } },
    build: function (stage, fig, m, o) { return buildPushup(X3['push-up'], stage, fig, m, o, {}); },
    camera: { target: { tx: 0, ty: 150, tz: -120 }, dist: 2300, fov: 26 },
    checks: function (fig, v, t, out) { pushupChecks(fig, v, t, out, {}); }
  };
  // the mistake (exercises.json push-up error "hips-sag"): the same solver, only the hips drop 14 deg below the line at depth
  X3['push-up-sag'] = {
    id: 'push-up-sag', name: 'Push-up, hips sagging (mistake)', knowledge: 'push-up', mistake: 'hips-sag', period: 3.0, phaseMap: PU_PHASES,
    rhythm: X3['push-up'].rhythm, acts: X3['push-up'].acts, peaks: X3['push-up'].peaks, shots: X3['push-up'].shots,
    build: function (stage, fig, m, o) { return buildPushup(X3['push-up-sag'], stage, fig, m, o, { sag: 14 }); },
    camera: X3['push-up'].camera,
    checks: function (fig, v, t, out) { pushupChecks(fig, v, t, out, { line: null, sagMin: -15 }); }
  };

  /*
   * Plank on the forearms: elbows planted under the shoulders on a mat (the forearm resting on it, measured on the skin), toes on the
   * mat. One rep = knees down (rest), lift into one line (the knee straightens and the hips rise into line about the planted toes and
   * forearms), HOLD with steady breathing, lower the knees. The hold is never frozen: the breath (a 3.2 s cycle of 0.9 deg of thoracic
   * extension, the shoulders held over the elbows) keeps a subtle, pure-of-time motion, so the frame always lives.
   */
  function buildPlank(def, stage, fig, m, o, cfg) {
    o = o || {};
    var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 1, per = o.period || def.period, x0 = o.x || 0, z0 = o.z || 0, S = fig.spec;
    cfg = merge({ fx: 42, fy: 4, pf: 6, knee: 8, ly: S.shy - 150, neck: -10, sag: 0, arch: 0, elbowY: 22, kneeGap: 1, breath: 1.6, handTilt: 22 }, cfg);
    fig.roles(def.acts);
    cfg.tipZ = 0;
    var sol = proneSolver(cfg), Sy, Sz, tipZ = 0, kDown = 90, hlP = 80, hlK = 80, palmLow;
    function arms(c) {
      var a = {};
      ['L', 'R'].forEach(function (sd) {
        var sg = sd === 'L' ? 1 : -1;
        // the elbow straight under the shoulder (upper arm 134 vertical), the forearm along the mat toward +z, palm down
        a['ik' + sd] = 1; a['hx' + sd] = -sg * 6; a['hy' + sd] = cfg.elbowY - c.S[0] + 4; a['hz' + sd] = Sz + Math.sqrt(106 * 106 - 52) - c.S[1];
        a['px' + sd] = 0; a['py' + sd] = -1; a['pz' + sd] = -0.15; a['gax' + sd] = 0;
        merge2(a, palmFlat(sd, new THREE.Vector3(sg * S.shx, c.S[0], c.S[1]), new THREE.Vector3(sg * S.shx - sg * 6, cfg.elbowY + 4, Sz + Math.sqrt(106 * 106 - 52)), new THREE.Vector3(0, -1, -0.15), cfg.handTilt, palmLow));
      });
      return a;
    }

    // the shoulders: over the elbows, the elbow on the mat (cfg.elbowY, corrected on the skin below); the toes: placed so the straight
    // plank fits between them; kneeling: the knee bend that puts the knee kneeGap above the mat (measured on the skin)
    function place() {
      Sy = cfg.elbowY + 134; cfg.tipZ = 0; sol = proneSolver(cfg);
      var c = sol.at(Sy, cfg.knee, 0);
      tipZ = -c.S[1]; Sz = 0; cfg.tipZ = tipZ; hlP = c.hl;               // shoulders at z0: the toes behind
      sol = proneSolver(cfg);
    }
    // kneeling: the foot pitch that keeps the shoulders over the elbows (the ankle turns about the planted toes as the knees come down)
    function hlKneel(k) { var lo = 20, hi = 150; for (var i = 0; i < 40; i++) { var mid = (lo + hi) / 2; if (sol.at(Sy, k, 0, mid).S[1] > Sz) hi = mid; else lo = mid; } return (lo + hi) / 2; }
    function keys(s, br) {
      var k = lerp(kDown, cfg.knee, s), hl = lerp(hlK, hlP, smooth(s)), beta = sol.betaFor(Sy, k, 0, hl), c = sol.chain(beta, k, 0, hl);
      if (br) {                                                          // breath: thoracic extension, the shoulder kept over the elbow by the pelvis
        var lean = -br, th = Math.atan2(c.S[0] - c.H[0], c.S[1] - c.H[1]) / D2R;
        var pv = (function () { var lo = c.p - 10, hi = c.p + 10; for (var i = 0; i < 40; i++) { var mid = (lo + hi) / 2, t2 = trunkPt(mid, lean, cfg.ly, -2); if (Math.atan2(6 * Math.cos(mid * D2R) + t2[0], 6 * Math.sin(mid * D2R) + t2[1]) / D2R > th) lo = mid; else hi = mid; } return (lo + hi) / 2; })();
        c.p = pv; c.lean = lean; c.R = [c.H[0] + 6 * Math.cos(pv * D2R), c.H[1] + 6 * Math.sin(pv * D2R)];
      }
      var kk = merge(proneKeys(c, cfg, x0, z0), arms(c));
      if (br) kk.headF = -3 * br / cfg.breath;                           // the head rides the breath a little (lifts on the inhale)
      return pref(p, kk);
    }
    var held = fig.supports ? fig.supports.splice(0) : [];
    place();
    for (var pass = 0; pass < 2; pass++) {                              // the forearm rests on the mat: lowest forearm skin 0.5 into it
      fig.apply(keys(1, 0));
      var low = Math.min(T3.skinLow(fig, ['elL']).y, T3.skinLow(fig, ['elR']).y);
      cfg.elbowY += cfg.fy - 0.5 - low; place();
    }
    // the palms rest on the mat: the analytic hand low that puts the skin 0.5 into it, kept for every frame (the forearm barely moves)
    fig.apply(keys(1, 0));
    var cP = sol.at(Sy, cfg.knee, 0), skinHand = Math.min(T3.skinLow(fig, ['handL']).y, T3.skinLow(fig, ['handR']).y);
    palmLow = palmFrame(new THREE.Vector3(S.shx, cP.S[0], cP.S[1]), new THREE.Vector3(S.shx - 6, cfg.elbowY + 4, Sz + Math.sqrt(106 * 106 - 52)), new THREE.Vector3(0, -1, -0.15), cfg.handTilt).low + cfg.fy - 0.5 - skinHand;
    var lo = cfg.knee + 5, hi = 150;                                     // kneeling: the knee comes down to the mat
    for (var j = 0; j < 24; j++) {
      kDown = (lo + hi) / 2; hlK = hlKneel(kDown); fig.apply(keys(0, 0));
      if (T3.skinLow(fig, ['knL', 'thL']).y > cfg.fy + cfg.kneeGap) lo = kDown; else hi = kDown;
    }
    kDown = (lo + hi) / 2; hlK = hlKneel(kDown);
    // the mat runs from behind the toes to past the hands
    var mat = EQ.mat({ x: x0, z: z0 + (tipZ - 60 + 230) / 2, w: 210, l: 230 - (tipZ - 60), h: cfg.fy }); stage.world.add(mat); fig.props.push(mat);
    if (fig.supports) Array.prototype.push.apply(fig.supports, held);
    fig.apply({});
    var F = def.phaseFrac;
    m.base(keys(0, 0));
    for (var r0 = 0; r0 < n; r0++) {
      var t0 = at + r0 * per, hold0 = t0 + F.up[1] * per, holdDur = (F.down[0] - F.up[1]) * per;
      m.path(t0 + F.up[0] * per, (F.up[1] - F.up[0]) * per, function (e) { return keys(e, 0); }, 'power2.inOut');
      // the hold breathes: linear clock inside the path, a sine breath that starts and ends at rest (whole cycles fitted to the hold)
      (function (d0) {
        var cycles = Math.max(1, Math.round(d0 / 3.2));
        m.path(hold0, d0, function (e) { return keys(1, cfg.breath * Math.pow(Math.sin(Math.PI * cycles * e), 2)); }, 'none');
      })(holdDur);
      m.path(t0 + F.down[0] * per, (F.down[1] - F.down[0]) * per, function (e) { return keys(1 - e, 0); }, 'sine.inOut');
    }
    // activation: rises over 1.0 s as the body lifts into line, holds, fades over 1.2 s as the knees come down (each rep)
    Object.keys(o.peaks || def.peaks).forEach(function (k) {
      var key = p + 'act.' + k, pk = (o.peaks || def.peaks)[k], z = {}, u = {};
      m.base((z[key] = 0, z)); u[key] = pk;
      for (var r1 = 0; r1 < n; r1++) { var t1 = at + r1 * per; m.to(t1 + F.up[0] * per, 1.0, u, 'sine.inOut'); m.to(t1 + F.down[0] * per, 1.2, z, 'sine.inOut'); }
    });
    fig.pose = function (s) { return keys(s, 0); }; fig.prone = { def: def, clock: { at: at, period: per, reps: n }, cfg: cfg, mat: mat, kDown: kDown };
    return at + n * per;
  }
  function plankChecks(fig, v, t, out) {
    var P = fig.prone, ph = T3.phaseAt(P.def, P.clock, t), hold = ph.id === 'hold' && ph.rep >= 1 && ph.rep <= P.clock.reps, top = P.cfg.fy;
    var c = T3.contacts(fig);
    ['L', 'R'].forEach(function (s) {
      var err = Math.abs(c['sole' + s] - top);
      out.toesOnMat = Math.max(out.toesOnMat || 0, err);
      if (err > 1.5) flagOnce(out, 'plank: the toes are ' + err.toFixed(1) + ' units off the mat');
      if (!hold) return;
      var e = fig.world('el' + s), sh = fig.world('sh' + s), dz = Math.abs(e.z - sh.z), dx = Math.abs(e.x - sh.x);
      out.elbowUnderShoulder = Math.max(out.elbowUnderShoulder || 0, Math.hypot(dx, dz));
      if (Math.hypot(dx, dz) > 12) flagOnce(out, 'plank: the elbow is ' + Math.hypot(dx, dz).toFixed(1) + ' units from under the shoulder (cue: elbows under the shoulders; max 12)');
    });
    if (hold) {
      var hl = T3.hipLine(fig);
      range(out, 'hipLine', hl); out.hipLineMin = out.hipLine[0]; out.hipLineMax = out.hipLine[1];
      if (Math.abs(hl) > 8) flagOnce(out, 'plank: the hips are ' + hl.toFixed(1) + ' units off the shoulder-ankle line (cue: one straight line; sag < 0, pike > 0; max 8)');
      var fa = Math.min(T3.skinLow(fig, ['elL']).y, T3.skinLow(fig, ['elR']).y) - top;
      range(out, 'forearmOnMat', fa); out.forearmLowMin = out.forearmOnMat[0]; out.forearmLowMax = out.forearmOnMat[1];
      if (fa < -1.5 || fa > 2) flagOnce(out, 'plank: the forearms are ' + fa.toFixed(1) + ' units off the mat');
      // never frozen: the crown travels at least 0.4 units over every 1 s of the hold (the breath)
      var hd = fig.point('head', 0, 60, 0), q = out._heads || Object.defineProperty(out, '_heads', { value: [] })._heads;
      q.push([t, hd.x, hd.y, hd.z]);
      while (q.length && q[0][0] < t - 1.0) q.shift();
      if (q.length > 25) {
        var span = 0; q.forEach(function (a) { span = Math.max(span, Math.hypot(a[1] - hd.x, a[2] - hd.y, a[3] - hd.z)); });
        out.holdMotionMin = Math.min(out.holdMotionMin === undefined ? Infinity : out.holdMotionMin, span);
        if (span < 0.4) flagOnce(out, 'plank: the hold freezes (the crown moves ' + span.toFixed(2) + ' units in 1 s; the breath must keep it alive)');
      }
    } else if (out._heads) out._heads.length = 0;
  }
  T3.plankChecks = plankChecks;
  X3.plank = {
    id: 'plank', name: 'Forearm plank', knowledge: 'plank', period: 8.0, minRom: 60,
    phaseFrac: { up: [0.05, 0.17], down: [0.85, 0.97] },
    phaseMap: [{ id: 'start', kind: 'hold', label: 'Knees down', a: 0, b: 0.05, cue: 'Elbows under the shoulders' }, { id: 'concentric', kind: 'up', label: 'Lift into line', a: 0.05, b: 0.17, cue: 'One straight line' },
      { id: 'hold', kind: 'hold', label: 'Hold', a: 0.17, b: 0.85, cue: 'Breathe steadily' }, { id: 'eccentric', kind: 'down', label: 'Knees down', a: 0.85, b: 0.97, cue: '' },
      { id: 'reset', kind: 'hold', label: 'Rest', a: 0.97, b: 1.0, cue: '' }],
    acts: { abs: 3, oblique: 3, erector: 1, glute: 1, quad: 1 },
    peaks: { abs: 1, oblique: 0.85, erector: 0.4, glute: 0.4, quad: 0.35 },
    shots: { side: { az: 90, el: 8 }, low: { az: 90, el: 1 }, three: { az: 40, el: 14 }, front: { az: 12, el: 12 }, back: { az: 180, el: 14 }, above: { az: 30, el: 62 } },
    build: function (stage, fig, m, o) { return buildPlank(X3.plank, stage, fig, m, o, {}); },
    camera: { target: { tx: 0, ty: 120, tz: -150 }, dist: 2300, fov: 26 },
    checks: plankChecks
  };

  // ================================================================ MACHINES AND CABLES (2026-11-24, motion family 2)
  /*
   * Seated machines. The body is posed first and the machine is built AROUND it from its joints and its measured skin (rule 28): the seat
   * top under the lowest glute/thigh skin, the back pad on the plane the back skin touches, the lever's pivot on the knee joint, the roller
   * where it meets the shin skin, the handles in the fists. Legs are direct-angle (FK) chains solved exactly (T3.legFK), so a knee stays on a
   * pivot or a sole on a sled whatever the pelvis does (the IK pole lies along the thigh when the hip is flexed 90 deg or more). Machine
   * parts (lever, sled, cable, weight stack) are posed after every fig.apply from keys the motion carries (`mach.<k>`, figure-prefixed),
   * so they are pure functions of the same dictionary as the body. Illustrative, not mocap.
   */
  var V3m = THREE.Vector3;
  function mkey(pose, p, k, d) { var v = pose[p + k]; return v === undefined ? d : v; }
  /** Pose machine parts after every fig.apply (T3.bind poses each figure, then draws; the checker and the fitter call fig.apply too). */
  function afterApply(fig, fn) { var ap = fig.apply; fig.apply = function (pose) { ap(pose); fn(pose || {}); }; }
  /** Every posed skin vertex whose strongest bone is one of `bones`: fn(v) with v in world units (v is reused; clone to keep it). */
  function skinScan(fig, bones, fn) {
    T3.skinLow(fig, bones.slice(0, 1), function () { return false; });            // builds fig._domBone once
    var skin = fig.body.skin, pa = skin.geometry.getAttribute('position'), want = {}, v = new V3m();
    skin.skeleton.bones.forEach(function (b, i) { if (bones.indexOf(b.name) >= 0) want[i] = true; });
    fig.root.updateMatrixWorld(true); skin.skeleton.update();
    for (var j = 0; j < pa.count; j++) {
      if (!want[fig._domBone[j]]) continue;
      v.fromBufferAttribute(pa, j); skin.applyBoneTransform(j, v); v.applyMatrix4(skin.matrixWorld); fn(v);
    }
  }
  T3.skinScan = skinScan;
  /** Gap (units) from a roller (axis along x through C, radius r, spanning x0..x1) to the skin of `bones`; < 0: the roller sinks in. */
  function rollerGap(fig, bones, C, r, x0, x1) {
    var g = Infinity;
    skinScan(fig, bones, function (v) { if (v.x < x0 || v.x > x1) return; var d = Math.hypot(v.y - C.y, v.z - C.z) - r; if (d < g) g = d; });
    return g;
  }
  T3.rollerGap = rollerGap;
  /** Smallest signed distance of the skin of `bones` from the plane through P with unit normal n (keep(v) filters); < 0: inside the pad. */
  function planeGap(fig, bones, P, n, keep) {
    var g = Infinity;
    skinScan(fig, bones, function (v) { if (keep && !keep(v)) return; var d = (v.x - P.x) * n.x + (v.y - P.y) * n.y + (v.z - P.z) * n.z; if (d < g) g = d; });
    return g;
  }
  T3.planeGap = planeGap;
  function rootMatrix(R) {
    return new THREE.Matrix4().compose(new V3m(R.x || 0, R.y, R.z || 0),
      new THREE.Quaternion().setFromEuler(new THREE.Euler((R.pitch || 0) * D2R, (R.yaw || 0) * D2R, (R.roll || 0) * D2R, 'YXZ')), new V3m(1, 1, 1));
  }
  /**
   * Direct-angle leg that puts the ankle joint exactly at world point A for a root pose R ({x, y, z, pitch, yaw, roll}): returns
   * {hp, ha, kn, an, K} (degrees; K = the knee joint in the world). The thigh's Euler (XYZ: -hp, 0, +-ha) and the knee hinge fix the plane
   * the knee bends in, so the knee is found on the circle of possible knees where that plane contains the ankle (nearest to the sagittal
   * solution that bends forward). footPitch (deg, about x, + toes down, the sense of hl) gives the ankle angle that sets the sole.
   */
  function legFK(R, sd, A, footPitch) {
    var sg = sd === 'L' ? 1 : -1, M = rootMatrix(R), Mi = M.clone().invert(), L1 = 178, L2 = 166;
    var O = new V3m(sg * 40, -6, 0), d = A.clone().applyMatrix4(Mi).sub(O), D = d.length();
    var Dc = Math.min(L1 + L2 - 0.5, Math.max(Math.abs(L1 - L2) + 0.5, D)), dh = d.clone().divideScalar(D || 1);
    var a1 = (L1 * L1 - L2 * L2 + Dc * Dc) / (2 * Dc), rr = Math.sqrt(Math.max(0, L1 * L1 - a1 * a1));
    var Rth = new THREE.Matrix4(), Rx = new THREE.Matrix4(), Rz = new THREE.Matrix4(), sl = new V3m();
    function at(e1, e2, phi) {
      var k = dh.clone().multiplyScalar(a1).addScaledVector(e1, rr * Math.cos(phi)).addScaledVector(e2, rr * Math.sin(phi));
      var t = k.clone().divideScalar(L1), ha = Math.asin(Math.max(-1, Math.min(1, sg * t.x))), th = Math.atan2(-t.z, -t.y);
      Rth.multiplyMatrices(Rx.makeRotationX(th), Rz.makeRotationZ(sg * ha));
      sl.copy(dh).multiplyScalar(Dc).sub(k).normalize().applyMatrix4(new THREE.Matrix4().copy(Rth).transpose());
      return { f: sl.x, kn: Math.atan2(-sl.z, -sl.y), ha: ha, th: th, k: k };
    }
    var n0 = new V3m(0, -dh.z, dh.y); if (n0.lengthSq() < 1e-8) n0.set(0, 0, 1); n0.normalize();
    var best = null;
    [n0, n0.clone().negate()].forEach(function (e1) {
      var e2 = new V3m().crossVectors(dh, e1).normalize(), g0 = at(e1, e2, 0);
      if (g0.kn <= 0) return;
      var lo = null, hi = null;
      for (var st = 1; st <= 80 && lo === null; st++) {
        for (var s2 = -1; s2 <= 1; s2 += 2) {
          var a = s2 * (st - 1) * D2R, b = s2 * st * D2R, fa = at(e1, e2, a).f, fb = at(e1, e2, b).f;
          if ((fa <= 0) !== (fb <= 0)) { lo = a; hi = b; break; }
        }
      }
      if (lo === null) { lo = hi = 0; }
      var flo = at(e1, e2, lo).f;
      for (var i = 0; i < 40; i++) { var mid = (lo + hi) / 2, fm = at(e1, e2, mid).f; if ((fm <= 0) === (flo <= 0)) { lo = mid; flo = fm; } else hi = mid; }
      var g = at(e1, e2, (lo + hi) / 2);
      if (g.kn > 0 && (!best || Math.abs(g.f) < Math.abs(best.f))) best = g;
    });
    var r = { hp: -best.th / D2R, ha: best.ha / D2R, kn: best.kn / D2R, K: best.k.clone().add(O).applyMatrix4(M), an: 0 };
    if (footPitch !== undefined) {
      var q = new THREE.Quaternion().setFromRotationMatrix(M).multiply(new THREE.Quaternion().setFromRotationMatrix(Rth))
        .multiply(new THREE.Quaternion().setFromAxisAngle(new V3m(1, 0, 0), best.kn));
      var up = new V3m(0, Math.cos(footPitch * D2R), Math.sin(footPitch * D2R)).applyQuaternion(q.invert());
      r.an = Math.atan2(up.z, up.y) / D2R;
    }
    return r;
  }
  T3.legFK = legFK;
  /** Keys of a direct-angle leg (both sides from one solve each). */
  function legKeys(R, sides, footPitch) {
    var k = {};
    Object.keys(sides).forEach(function (sd) {
      var g = legFK(R, sd, sides[sd], footPitch);
      k['ikLeg' + sd] = 0; k['hp' + sd] = g.hp; k['ha' + sd] = g.ha; k['kn' + sd] = g.kn; k['an' + sd] = g.an;
    });
    return k;
  }
  T3.legKeys = legKeys;

  // ---- simple machine parts (Cobalt Sculpt: flat planes, steel and pad colours, nothing that outshines the body)
  function box(w, h, d, color) { return new THREE.Mesh(new THREE.BoxGeometry(w, h, d), T3.material(color)); }
  /** A rod (cylinder) of radius r between world points A and B; setRod moves it (its geometry is a unit-height cylinder along y). */
  function rod(r, color) { var m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 1, 14), T3.material(color)); m.userData.rod = true; return m; }
  function setRod(m, A, B) {
    var d = B.clone().sub(A), L = d.length();
    m.position.copy(A).addScaledVector(d, 0.5); m.scale.set(1, Math.max(L, 0.01), 1);
    m.quaternion.setFromUnitVectors(new V3m(0, 1, 0), L > 1e-6 ? d.divideScalar(L) : new V3m(0, 1, 0));
  }
  T3.setRod = setRod;
  function disc(r, w, color) { var m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, w, 28), T3.material(color)); m.rotation.z = Math.PI / 2; return m; }
  EQ.box = box; EQ.rod = rod; EQ.disc = disc;
  /**
   * A weight stack in a frame: n plates (h each) between two guide rods, the top `moving` plates rise by `rise` (stack.set(rise)).
   * o: {x, z, n, moving, w, d, h, frameH, yaw}; stack.top(rise) is the world point where the cable meets the top plate.
   */
  EQ.stack = function (o) {
    o = o || {};
    var g = new THREE.Group(), n = o.n || 12, mv = o.moving || 5, w = o.w || 120, dp = o.d || 70, h = o.h || 15, H = o.frameH || 900;
    var base = box(w + 60, 12, dp + 60, T3.colors.steelShade); base.position.y = 6; g.add(base);
    [-1, 1].forEach(function (sd) {
      var post = box(14, H, 14, T3.colors.steelShade); post.position.set(sd * (w / 2 + 22), H / 2, 0); g.add(post);
      var guide = rod(3, T3.colors.steel); setRod(guide, new V3m(sd * (w / 2 - 14), 12, 0), new V3m(sd * (w / 2 - 14), H - 40, 0)); g.add(guide);
    });
    var cap = box(w + 58, 14, 26, T3.colors.steelShade); cap.position.set(0, H, 0); g.add(cap);
    var plates = [];
    for (var i = 0; i < n; i++) {
      var pl = box(w, h - 2, dp, i % 2 ? T3.colors.plate : T3.colors.plateFace); pl.position.y = 12 + i * h + h / 2; g.add(pl); plates.push(pl);
    }
    var pin = rod(4, T3.colors.steel); g.add(pin);
    g.position.set(o.x || 0, 0, o.z || 0); g.rotation.y = (o.yaw || 0) * D2R;
    var y0 = 12 + n * h;
    g.userData.stack = {
      set: function (rise) {
        rise = Math.max(0, rise);
        for (var j = n - mv; j < n; j++) plates[j].position.y = 12 + j * h + h / 2 + rise;
        setRod(pin, new V3m(0, 12 + (n - mv) * h + rise - 4, 0), new V3m(0, y0 + rise + 14, 0));
      },
      top: function (rise) { g.updateMatrixWorld(true); return new V3m(0, y0 + Math.max(0, rise) + 14, 0).applyMatrix4(g.matrixWorld); },
      height: H
    };
    g.userData.stack.set(0);
    return g;
  };
  /** Add a prop to the stage and to the figure (props are framed, audited for orphans and hidden with the figure). */
  function addProp(stage, fig, obj) { stage.world.add(obj); fig.props.push(obj); return obj; }

  /*
   * Seated base pose (leg extension, leg curl, lat pulldown): root at hip height y, pelvis pitch p (< 0 reclines onto the back pad), the
   * head kept level. Returns the keys; the seat and back pad are then built under the posed skin (seatFromSkin, backFromSkin).
   */
  function seatFromSkin(fig, p, keepZ) {
    var low = Infinity, zs = [Infinity, -Infinity];
    skinScan(fig, ['hips', 'thL', 'thR'], function (v) { if (keepZ && !keepZ(v.z)) return; if (v.y < low) low = v.y; });
    skinScan(fig, ['hips'], function (v) { zs[0] = Math.min(zs[0], v.z); zs[1] = Math.max(zs[1], v.z); });
    return { top: low + 1.5, zBack: zs[0] };
  }
  /** The back pad plane (normal = the trunk's forward direction for pelvis pitch p): the plane 1 unit into the rear-most back skin. */
  function backFromSkin(fig, pitch, yMin) {
    var n = new V3m(0, -Math.sin(pitch * D2R), Math.cos(pitch * D2R)), low = Infinity, at = null;
    skinScan(fig, ['spine', 'chest'], function (v) { if (v.y < yMin) return; var d = v.y * n.y + v.z * n.z; if (d < low) { low = d; at = v.clone(); } });
    return { n: n, d: low + 1, at: at };
  }
  /** A pad (box) whose front face lies on the plane n.x = d (normal in the y-z plane), centred at height yc, length len up the pad. */
  function padOnPlane(pl, yc, len, w, color) {
    var g = new THREE.Group(), th = 34, up = new V3m(0, pl.n.z, -pl.n.y);           // up the pad, in the plane
    var pad = box(w, len, th, color || T3.colors.pad); pad.position.z = -th / 2; g.add(pad);
    var cap = box(w - 14, len - 14, 6, T3.colors.padTop); cap.position.z = -2; g.add(cap);
    // the plane point at height yc: (y, z) with y*ny + z*nz = d, y = yc
    var zc = (pl.d - yc * pl.n.y) / pl.n.z;
    g.position.set(0, yc, zc); g.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(new V3m(1, 0, 0), up, pl.n));
    g.userData.len = len;
    return g;
  }
  /** Handles: grips (short rods along z) placed exactly where the fists are in the posed body. */
  function fistPoint(fig, sd) { return fig.point('hand' + sd, 0, -24, 4); }

  /*
   * KNEE MACHINES (leg extension, seated leg curl). The pelvis and thighs are fixed on the seat (the thighs horizontal: hp = 90 + pitch);
   * only the knee moves, kn(s), s = 0 start .. 1 end of the concentric. The lever turns about a pivot on the knee joint (cue: knee lined
   * up with the pivot) and its roller rides the shin `Lp` down from the knee, in front of the shin (extension) or behind it (curl); the
   * roller offset is solved on the posed skin at three knee angles (roller just touching the skin). cfg.pivot (y, z offset from the
   * knee) is the pivot-misaligned mistake: the lever then turns about its own axis and the roller is solved to stay on the shin, so it
   * slides along it.
   */
  function buildKneeMachine(def, stage, fig, m, o, cfg) {
    o = o || {};
    var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 3, per = o.period || def.period || 3.4, x0 = o.x || 0, z0 = o.z || 0;
    var pitch = cfg.pitch, hp = 90 + pitch, back = cfg.side === 'back', Lp = cfg.Lp, rr = 22, sgn = back ? -1 : 1;
    fig.roles(def.acts);
    var held = fig.supports ? fig.supports.splice(0) : [];
    var root = { x: x0, y: cfg.hipY, z: z0, pitch: pitch, lean: 0, neckF: -pitch * 0.8, headF: -pitch * 0.2, yaw: 0, roll: 0 };
    function kn(s) { return lerp(cfg.k0, cfg.k1, s); }
    function legs(k) { var r = {}; ['L', 'R'].forEach(function (sd) { r['ikLeg' + sd] = 0; r['hp' + sd] = hp; r['ha' + sd] = 0; r['kn' + sd] = k; r['an' + sd] = cfg.ankle; }); return r; }
    // arms: the hands rest on handles beside the seat (the handle grips are built in the fists afterwards)
    var arms = {};
    ['L', 'R'].forEach(function (sd) {
      var sg = sd === 'L' ? 1 : -1;
      arms['ik' + sd] = 1; arms['hx' + sd] = sg * 28; arms['hy' + sd] = -196; arms['hz' + sd] = 38 + cfg.handZ; arms['px' + sd] = sg * 0.6; arms['py' + sd] = 0; arms['pz' + sd] = -0.8; arms['gaz' + sd] = 1;
    });
    var base = merge(root, arms);
    fig.apply(pref(p, merge(base, legs(kn(0)))));
    var K = fig.world('knL').clone(); K.x = x0;                                      // the knee axis (both knees share y and z)
    var P = K.clone().add(new V3m(0, (cfg.pivot || [0, 0])[0], (cfg.pivot || [0, 0])[1]));
    function shinDir(k) { var r = (pitch - hp + k) * D2R; return { s: new V3m(0, -Math.cos(r), -Math.sin(r)), f: new V3m(0, -Math.sin(r), Math.cos(r)), r: r }; }
    // roller offset from the shin axis (front +, back -), solved on the skin at three knee angles: the roller just touches (gap 0.5)
    var KS = [cfg.k0, (cfg.k0 + cfg.k1) / 2, cfg.k1], OFF = [];
    KS.forEach(function (k) {
      fig.apply(pref(p, merge(base, legs(k))));
      var sd = shinDir(k), off = sgn * 50;
      for (var it = 0; it < 4; it++) {
        var C = K.clone().addScaledVector(sd.s, Lp).addScaledVector(sd.f, off);
        var g = rollerGap(fig, ['knL', 'knR', 'anL', 'anR'], C, rr, x0 - 90, x0 + 90);
        off += sgn * (0.5 - g);
      }
      OFF.push(off);
    });
    function offAt(k) {                                                              // quadratic through the three samples
      var a = KS[0], b = KS[1], c = KS[2];
      return OFF[0] * (k - b) * (k - c) / ((a - b) * (a - c)) + OFF[1] * (k - a) * (k - c) / ((b - a) * (b - c)) + OFF[2] * (k - a) * (k - b) / ((c - a) * (c - b));
    }
    // the lever angle: aligned, the shin's own angle; misaligned, the angle about P that keeps the roller centre offAt(k) from the shin
    // axis (the roller rides the shin as the two axes disagree)
    function lever(k) {
      var sd = shinDir(k);
      if (!cfg.pivot) return { a: sd.r, C: K.clone().addScaledVector(sd.s, Lp).addScaledVector(sd.f, offAt(k)) };
      var off0 = offAt(k), arm = new V3m(0, -Lp, OFF[0]);
      function Cof(a) { return P.clone().add(arm.clone().applyAxisAngle(new V3m(1, 0, 0), a)); }
      function fn(a) { return (Cof(a).sub(K)).dot(sd.f) - off0; }
      var lo = sd.r - 1.2, hi = sd.r + 1.2, flo = fn(lo);
      for (var i = 0; i < 50; i++) { var mid = (lo + hi) / 2, fm = fn(mid); if ((fm <= 0) === (flo <= 0)) { lo = mid; flo = fm; } else hi = mid; }
      var a = (lo + hi) / 2;
      return { a: a, C: Cof(a) };
    }
    // the seat (under the glutes and thighs, ending short of the knee so the calves clear it) and the back pad (on the back skin)
    fig.apply(pref(p, merge(base, legs(kn(0)))));
    var seat = seatFromSkin(fig, pitch, function (z) { return z < K.z - cfg.seatGap; });
    var bp = backFromSkin(fig, pitch, seat.top + 30);
    var mach = new THREE.Group();
    var seatLen = K.z - cfg.seatGap - (seat.zBack - 30), seatPad = new THREE.Group();
    var sp = box(170, 34, seatLen, T3.colors.pad); sp.position.y = -17; seatPad.add(sp);
    var sc = box(156, 6, seatLen - 14, T3.colors.padTop); sc.position.y = -2; seatPad.add(sc);
    seatPad.position.set(x0, seat.top, K.z - cfg.seatGap - seatLen / 2); mach.add(seatPad);
    var backPad = padOnPlane(bp, seat.top + 150, 300, 170); backPad.position.x = x0; mach.add(backPad);
    var col = box(46, seat.top - 34, 46, T3.colors.steelShade); col.position.set(x0, (seat.top - 34) / 2, seatPad.position.z); mach.add(col);
    var foot = box(190, 10, seatLen + 220, T3.colors.steelShade); foot.position.set(x0, 5, seatPad.position.z + 40); mach.add(foot);
    var hubX = x0 - 112, post = box(30, P.y, 30, T3.colors.steelShade); post.position.set(hubX, P.y / 2, P.z); mach.add(post);
    var hub = disc(24, 26, T3.colors.steel); hub.position.set(hubX, P.y, P.z); mach.add(hub);
    // lever: pivot group at P, local -y down the arm; the roller across both shins; a plate horn opposite the arm (the load)
    var lev = new THREE.Group(); lev.position.copy(P); mach.add(lev);
    var armBar = rod(7, T3.colors.steel); lev.add(armBar);
    var roll = disc(rr, 176, T3.colors.pad); lev.add(roll);
    var rollEnd = disc(9, 190, T3.colors.steel); lev.add(rollEnd);
    var horn = rod(6, T3.colors.steel); lev.add(horn);
    var plate = disc(46, 15, T3.colors.plate); lev.add(plate); var plateF = disc(28, 16, T3.colors.plateFace); lev.add(plateF);
    // handles in the fists, on short posts from the seat
    ['L', 'R'].forEach(function (sd) {
      var F = fistPoint(fig, sd), grip = rod(6, T3.colors.pad); setRod(grip, F.clone().add(new V3m(0, 0, -22)), F.clone().add(new V3m(0, 0, 22))); mach.add(grip);
      var stem = rod(5, T3.colors.steelShade); setRod(stem, F.clone().add(new V3m(0, 0, -22)), new V3m(F.x, seat.top - 20, F.z - 22)); mach.add(stem);
    });
    // seated leg curl: a thigh (lap) pad rests on top of both thighs just above the knees and holds them down (the thighs never move,
    // so it is static); it sits 1 unit into the highest thigh skin of the band at the start pose
    var lap = null;
    if (cfg.lapPad) {
      var lr = 22, zc = K.z - cfg.lapPad, topY = -Infinity;
      skinScan(fig, ['thL', 'thR'], function (v) { if (Math.abs(v.z - zc) < lr && Math.abs(v.x - x0) < 90) { var h = v.y + Math.sqrt(Math.max(0, lr * lr - (v.z - zc) * (v.z - zc))) - lr; if (h > topY) topY = h; } });
      lap = { C: new V3m(x0, topY + lr - 1, zc), r: lr };
      var lapRoll = disc(lr, 176, T3.colors.pad); lapRoll.position.copy(lap.C); mach.add(lapRoll);
      var lapEnd = disc(8, 196, T3.colors.steel); lapEnd.position.copy(lap.C); mach.add(lapEnd);
      [-1, 1].forEach(function (sg) { var arm = rod(6, T3.colors.steelShade); setRod(arm, new V3m(x0 + sg * 98, lap.C.y, zc), new V3m(x0 + sg * 98, seat.top - 24, zc)); mach.add(arm); });
    }
    addProp(stage, fig, mach);
    var A0 = null;
    function poseLever(k) {
      var L = lever(k);
      if (cfg.pivot) {
        // the roller rests ON the posed shin skin: secant search on the lever angle for a 0.5-unit gap (the shin's radius varies along it)
        var arm0 = new V3m(0, -Lp, OFF[0]), Cof = function (a) { return P.clone().add(arm0.clone().applyAxisAngle(new V3m(1, 0, 0), a)); };
        var gapOf = function (a) { return rollerGap(fig, ['knL', 'knR', 'anL', 'anR'], Cof(a), rr, x0 - 90, x0 + 90) - 0.5; };
        var a0 = L.a, a1 = L.a + sgn * 0.02, g0 = gapOf(a0), g1 = gapOf(a1);
        for (var it = 0; it < 6 && Math.abs(g1) > 0.02 && g1 !== g0; it++) { var a2 = a1 - g1 * (a1 - a0) / (g1 - g0); a0 = a1; g0 = g1; a1 = Math.max(L.a - 0.6, Math.min(L.a + 0.6, a2)); g1 = gapOf(a1); }
        L = { a: a1, C: Cof(a1) };
      }
      var C = L.C.clone().sub(P), a = L.a;
      if (A0 === null) A0 = a;
      lev.rotation.set(0, 0, 0);
      // local frame of the lever: unrotated, then the whole group turns by a about x
      var Cl = C.clone().applyAxisAngle(new V3m(1, 0, 0), -a);
      setRod(armBar, new V3m(hubX - x0 + 6, 0, 0), new V3m(hubX - x0 + 6, Cl.y, Cl.z));
      roll.position.set(0, Cl.y, Cl.z); rollEnd.position.set(0, Cl.y, Cl.z);
      setRod(horn, new V3m(hubX - x0 - 10, 0, 0), new V3m(hubX - x0 - 10, 70, -sgn * 46));
      plate.position.set(hubX - x0 - 34, 70, -sgn * 46); plateF.position.set(hubX - x0 - 43, 70, -sgn * 46);
      lev.rotation.x = a;
      lev.userData.C = L.C; lev.userData.a = a;
    }
    afterApply(fig, function (pose) { poseLever(mkey(pose, p, 'kn' + 'L', kn(0))); });
    if (fig.supports) Array.prototype.push.apply(fig.supports, held);
    fig.apply({});
    function keys(s) { return pref(p, legs(kn(s))); }
    m.base(pref(p, base)); m.base(keys(0));
    var end = reps(m, at, per, n, keys, def.rhythm);
    envelope(m, p, o.peaks || def.peaks, at, per, n);
    fig.pose = keys;
    fig.machine = { def: def, clock: { at: at, period: per, reps: n }, cfg: cfg, K: K, P: P, lever: lev, seatTop: seat.top, back: bp, roller: rr, Lp: Lp, shinDir: shinDir, hp: hp, pitch: pitch, lap: lap };
    return end;
  }
  /*
   * Knee-machine checks (exercises.json cue_checks): the knee joint stays on the pivot axis (within 3 units; the misaligned variant must
   * sit off it); the thigh does not move (its angle within 2 deg); the roller touches the shin (gap -2..3 units) and does not slide along
   * it (contact station within 6 units; the misaligned variant slides); the glutes stay on the seat and the back on its pad; the leg
   * curl's thigh pad stays on the thighs (-2.5..3); the knee
   * reaches the stretch each rep (curl) or nearly straight (extension); a top hold of at least 0.3 s and an eccentric longer than the
   * concentric in the phase map.
   */
  function kneeMachineChecks(fig, v, t, out, lim) {
    lim = merge({ pivot: 3, slide: 6, kneeMin: null, kneeMax: null }, lim || {});
    var M = fig.machine, ph = T3.phaseAt(M.def, M.clock, t), inSet = ph.rep >= 1 && ph.rep <= M.clock.reps;
    ['L', 'R'].forEach(function (s) {
      var k = fig.world('kn' + s), d = Math.hypot(k.y - M.P.y, k.z - M.P.z);
      range(out, 'kneeToPivot', d); out.kneeToPivotMax = out.kneeToPivot[1];
      if (lim.pivot !== null && d > lim.pivot) flagOnce(out, 'knee machine: the knee joint is ' + d.toFixed(1) + ' units off the pivot (cue: knee lined up with the pivot; max ' + lim.pivot + ')');
      var th = fig.world('th' + s), u = k.clone().sub(th), ang = Math.atan2(u.y, u.z) / D2R;
      range(out, 'thighAngle', ang); out.thighMove = out.thighAngle[1] - out.thighAngle[0];
      if (out.thighMove > 2) flagOnce(out, 'knee machine: the thigh moves ' + out.thighMove.toFixed(1) + ' deg (cue: only the knee moves; max 2)');
      var fl = 180 - T3.jointAngle(fig, 'th' + s, 'kn' + s, 'an' + s);
      range(out, 'kneeFlex', fl); out.kneeFlexMin = out.kneeFlex[0]; out.kneeFlexMax = out.kneeFlex[1];
    });
    var C = M.lever.userData.C, gap = rollerGap(fig, ['knL', 'knR', 'anL', 'anR'], C, M.roller, -90 + (fig.root.position.x || 0), 90 + (fig.root.position.x || 0));
    range(out, 'rollerGap', gap); out.rollerGapMin = out.rollerGap[0]; out.rollerGapMax = out.rollerGap[1];
    if (gap < -2 || gap > 3) flagOnce(out, 'knee machine: the roller is ' + gap.toFixed(1) + ' units off the shin (it must ride the shin: -2..3)');
    var k0 = fig.world('knL'), sd = M.shinDir(mkey(v, fig.id ? fig.id + '.' : '', 'knL', 0)), st = C.clone().sub(k0).dot(sd.s);
    range(out, 'rollerStation', st); out.rollerSlide = out.rollerStation[1] - out.rollerStation[0];
    if (lim.slide !== null && out.rollerSlide > lim.slide) flagOnce(out, 'knee machine: the roller slides ' + out.rollerSlide.toFixed(1) + ' units along the shin (the knee is off the pivot; max ' + lim.slide + ')');
    var g = T3.skinLow(fig, ['hips', 'thL', 'thR'], function (q) { return q.z < M.K.z - M.cfg.seatGap; }).y - M.seatTop;
    range(out, 'seatGap', g);
    if (g < -4 || g > 2) flagOnce(out, 'knee machine: the glutes are ' + g.toFixed(1) + ' units off the seat (hips stay down)');
    if (M.lap) {
      var x0 = fig.root.position.x || 0, lg = rollerGap(fig, ['thL', 'thR'], M.lap.C, M.lap.r, x0 - 90, x0 + 90);
      range(out, 'lapGap', lg); out.lapGapMin = out.lapGap[0]; out.lapGapMax = out.lapGap[1];
      if (lg < -2.5 || lg > 3) flagOnce(out, 'knee machine: the thigh pad is ' + lg.toFixed(1) + ' units off the thighs (it holds them down: -2.5..3)');
    }
    // every rep reaches the extended end (the stretch of a curl, nearly straight in an extension): the least knee flexion per rep
    var rm = out._repMin || Object.defineProperty(out, '_repMin', { value: {} })._repMin, fl0 = 180 - T3.jointAngle(fig, 'thL', 'knL', 'anL');
    if (inSet) rm[ph.rep] = Math.min(rm[ph.rep] === undefined ? Infinity : rm[ph.rep], fl0);
    if (t >= M.clock.at + M.clock.reps * M.clock.period && !out._repDone) {
      Object.defineProperty(out, '_repDone', { value: true });
      var worst = -Infinity; Object.keys(rm).forEach(function (r) { worst = Math.max(worst, rm[r]); });
      out.kneeExtendedWorstRep = worst;
      if (lim.kneeMin !== null && worst > lim.kneeMin) flagOnce(out, 'knee machine: a rep only extends to ' + worst.toFixed(0) + ' deg of knee flexion (cue: full extension each rep; needs ' + lim.kneeMin + ')');
    }
    if (!out._def) {
      Object.defineProperty(out, '_def', { value: true });
      var map = M.def.phaseMap, dur = function (kind) { var s = 0; map.forEach(function (q) { if (q.kind === kind) s += (q.b - q.a) * M.clock.period; }); return s; };
      var top = 0; map.forEach(function (q) { if (q.id === 'end-range') top = (q.b - q.a) * M.clock.period; });
      out.topHold = top; out.eccentricS = dur('down'); out.concentricS = dur('up');
      if (M.def.topHold && top < M.def.topHold) flagOnce(out, 'knee machine: the hold at the end range is ' + top.toFixed(2) + ' s (cue: pause; needs ' + M.def.topHold + ')');
      if (out.eccentricS <= out.concentricS) flagOnce(out, 'knee machine: the lowering is not slower than the lift (' + out.eccentricS.toFixed(2) + ' vs ' + out.concentricS.toFixed(2) + ' s)');
    }
  }
  T3.kneeMachineChecks = kneeMachineChecks;
  var LEGEXT_PHASES = [{ id: 'start', kind: 'hold', label: 'Bottom', a: 0, b: 0.03, cue: 'Knee lined up with the pivot' }, { id: 'concentric', kind: 'up', label: 'Extend', a: 0.03, b: 0.32, cue: 'Straighten smoothly' },
    { id: 'end-range', kind: 'hold', label: 'Pause', a: 0.32, b: 0.44, cue: 'Pause at the top' }, { id: 'eccentric', kind: 'down', label: 'Lower', a: 0.44, b: 0.97, cue: 'Lower under control' },
    { id: 'reset', kind: 'hold', label: 'Bottom', a: 0.97, b: 1.0, cue: '' }];
  var LEGEXT = { side: 'front', pitch: -12, hipY: 262, k0: 90, k1: 8, Lp: 134, ankle: -8, seatGap: 34, handZ: 0 };
  X3['leg-extension'] = {
    id: 'leg-extension', name: 'Leg extension (machine)', knowledge: 'leg-extension', period: 3.4, topHold: 0.3, phaseMap: LEGEXT_PHASES, track: ['anL', 'anR'],
    // reps() runs fn(0 -> 1) then fn(1 -> 0): here 0 = knees bent, so the drive up is power2 (concentric) and the lowering sine
    rhythm: { down: [0.03, 0.32], up: [0.44, 0.97], downEase: 'power2.inOut', upEase: 'sine.inOut' },
    acts: { quad: 3 }, peaks: { quad: 1 },
    shots: { side: { az: 90, el: 6 }, three: { az: 40, el: 10 }, front: { az: 12, el: 8 }, back: { az: 160, el: 12 }, low: { az: 70, el: 2 } },
    build: function (stage, fig, m, o) { return buildKneeMachine(X3['leg-extension'], stage, fig, m, o, merge(LEGEXT, {})); },
    camera: { target: { tx: 0, ty: 330, tz: 120 }, dist: 2500, fov: 26 },
    checks: function (fig, v, t, out) { kneeMachineChecks(fig, v, t, out, { kneeMin: 12 }); }
  };
  // the mistake (exercises.json leg-extension error "pivot-misaligned"): the same machine, its pivot 32 units behind and 14 below the knee
  X3['leg-extension-misaligned'] = {
    id: 'leg-extension-misaligned', name: 'Leg extension, knee off the pivot (mistake)', knowledge: 'leg-extension', mistake: 'pivot-misaligned', period: 3.4, topHold: 0.3, track: ['anL', 'anR'],
    phaseMap: LEGEXT_PHASES, rhythm: X3['leg-extension'].rhythm, acts: X3['leg-extension'].acts, peaks: X3['leg-extension'].peaks, shots: X3['leg-extension'].shots,
    build: function (stage, fig, m, o) { return buildKneeMachine(X3['leg-extension-misaligned'], stage, fig, m, o, merge(LEGEXT, { pivot: [-14, -32] })); },
    camera: X3['leg-extension'].camera,
    // the variant must SHOW the mistake: the knee sits at least 20 units off the pivot and the roller slides at least 15 units on the shin
    checks: function (fig, v, t, out) {
      kneeMachineChecks(fig, v, t, out, { pivot: null, slide: null, kneeMin: 12 });
      if (out.kneeToPivot[0] < 20) flagOnce(out, 'pivot-misaligned variant: the knee is within 20 units of the pivot (the mistake is not visible)');
      if (t > 1 && out.rollerSlide < 15) flagOnce(out, 'pivot-misaligned variant: the roller slides under 15 units on the shin (the mistake is not visible)');
    }
  };
  var LEGCURL_PHASES = [{ id: 'start', kind: 'hold', label: 'Stretch', a: 0, b: 0.045, cue: 'Knee lined up with the pivot' }, { id: 'concentric', kind: 'up', label: 'Curl', a: 0.045, b: 0.33, cue: 'Pull the pad under the seat' },
    { id: 'end-range', kind: 'hold', label: 'Squeeze', a: 0.33, b: 0.39, cue: 'Thigh stays still' }, { id: 'eccentric', kind: 'down', label: 'Return', a: 0.39, b: 0.955, cue: 'All the way to the stretch' },
    { id: 'reset', kind: 'hold', label: 'Stretch', a: 0.955, b: 1.0, cue: '' }];
  var LEGCURL = { side: 'back', pitch: -16, hipY: 262, k0: 6, k1: 108, Lp: 128, ankle: -6, seatGap: 46, handZ: 0, lapPad: 62 };
  X3['leg-curl'] = {
    id: 'leg-curl', name: 'Seated leg curl (machine)', knowledge: 'leg-curl', period: 3.4, phaseMap: LEGCURL_PHASES, track: ['anL', 'anR'],
    rhythm: { down: [0.045, 0.33], up: [0.39, 0.955], downEase: 'power2.inOut', upEase: 'sine.inOut' },
    acts: { hams: 3, calf: 2 }, peaks: { hams: 1, calf: 0.45 },
    shots: { side: { az: 90, el: 6 }, three: { az: 40, el: 10 }, front: { az: 12, el: 8 }, back: { az: 160, el: 12 }, low: { az: 110, el: 2 } },
    build: function (stage, fig, m, o) { return buildKneeMachine(X3['leg-curl'], stage, fig, m, o, merge(LEGCURL, {})); },
    camera: { target: { tx: 0, ty: 300, tz: 120 }, dist: 2500, fov: 26 },
    checks: function (fig, v, t, out) { kneeMachineChecks(fig, v, t, out, { kneeMin: 12 }); }
  };
  // the mistake (exercises.json leg-curl error "short-range"): the same machine, the return stops at 48 deg instead of the full stretch
  X3['leg-curl-short'] = {
    id: 'leg-curl-short', name: 'Seated leg curl, short return (mistake)', knowledge: 'leg-curl', mistake: 'short-range', period: 3.4, phaseMap: LEGCURL_PHASES, track: ['anL', 'anR'],
    rhythm: X3['leg-curl'].rhythm, acts: X3['leg-curl'].acts, peaks: X3['leg-curl'].peaks, shots: X3['leg-curl'].shots,
    build: function (stage, fig, m, o) { return buildKneeMachine(X3['leg-curl-short'], stage, fig, m, o, merge(LEGCURL, { k0: 48 })); },
    camera: X3['leg-curl'].camera,
    checks: function (fig, v, t, out) {
      kneeMachineChecks(fig, v, t, out, {});
      if (out.kneeFlex[0] < 35) flagOnce(out, 'short-range variant: the knee extends past 35 deg (the mistake is not visible)');
    }
  };

  // ================================================================ LEG PRESS (45-degree sled; motion family 2, 2026-11-24)
  /*
   * The pelvis lies still on a reclined seat (root pitch = cfg.pitch; the trunk cfg.recline deg above the horizontal) and the feet ride a
   * platform on a sled that runs along d, cfg.sled deg above the horizontal. One parameter s (0 = top, soft knees; 1 = bottom) moves the
   * sled linearly along d; each ankle is then exactly A(s) = hip + L(s) d + e t + w x, where t is "up the platform" (toward the toes)
   * and L(s) comes from the knee flexion wanted at the two ends (cfg.kTop, cfg.kBot). The legs are direct-angle chains solved to those
   * ankles with the sole flat on the platform (T3.legFK, foot pitch -(90 + sled)). e (feet high on the platform) is chosen so the ankle
   * stays in a physiological range: about 10 deg of plantar flexion at the top and 25 deg of dorsiflexion at the bottom. The seat and
   * the back pad are built on the posed skin (rule 28); the platform face passes through the soles. Pose key `mach.sled` (figure-
   * prefixed) carries s, so the sled is a pure function of the same dictionary as the body. Illustrative, not mocap.
   */
  /** A pad (box, 34 thick) whose face lies on the plane {n, d} (n in the y-z plane), centred at in-plane coordinate lam along up. */
  function padAt(pl, lam, len, w, x) {
    var g = new THREE.Group(), th = 34, up = new V3m(0, pl.n.z, -pl.n.y);
    var pad = box(w, len, th, T3.colors.pad); pad.position.z = -th / 2; g.add(pad);
    var cap = box(w - 14, len - 14, 6, T3.colors.padTop); cap.position.z = -2; g.add(cap);
    g.position.copy(pl.n).multiplyScalar(pl.d).addScaledVector(up, lam); g.position.x = x;
    g.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(new V3m(1, 0, 0), up, pl.n));
    g.userData.len = len; g.userData.w = w;
    return g;
  }
  /** Register a tilted pad as hair supports: thin slices along its length, so each box hugs the slanted face (an AABB of the whole pad would float the hair). */
  function restsOnPad(fig, pad, slices) {
    if (!fig.supports) return;
    pad.updateWorldMatrix(true, true);
    var L = pad.userData.len, w = pad.userData.w;
    for (var i = 0; i < slices; i++) {
      var a = -L / 2 + i * L / slices, b = a + L / slices, pts = [];
      [a, b].forEach(function (y) { [-w / 2, w / 2].forEach(function (x) { [-34, 1].forEach(function (z) { pts.push(new V3m(x, y, z).applyMatrix4(pad.matrixWorld)); }); }); });
      fig.supports.push(new THREE.Box3().setFromPoints(pts));
    }
  }
  function legPressLen(k, w, e) {                                                  // hip-to-ankle distance along d for knee flexion k
    var D2 = 178 * 178 + 166 * 166 + 2 * 178 * 166 * Math.cos(k * D2R);
    return Math.sqrt(Math.max(0, D2 - w * w - e * e));
  }
  function buildLegPress(def, stage, fig, m, o, cfg) {
    o = o || {};
    var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 3, per = o.period || def.period || 3.6, x0 = o.x || 0, z0 = o.z || 0;
    var al = cfg.sled * D2R, d = new V3m(0, Math.sin(al), Math.cos(al)), tv = new V3m(0, Math.cos(al), -Math.sin(al)), fp = -(90 + cfg.sled);
    var pitch = -(90 - cfg.recline);
    fig.roles(def.acts);
    var held = fig.supports ? fig.supports.splice(0) : [];
    var R = { x: x0, y: cfg.hipY, z: z0, pitch: pitch, yaw: 0, roll: 0 }, MR = rootMatrix(R);
    var base = merge(R, { lean: 0, neckF: cfg.neckF, headF: cfg.headF });
    ['L', 'R'].forEach(function (sd) {                                              // hands on the handles beside the seat (chest frame)
      var sg = sd === 'L' ? 1 : -1;
      base['ik' + sd] = 1; base['ikc' + sd] = 1; base['hx' + sd] = sg * 34; base['hy' + sd] = -212; base['hz' + sd] = 30;
      base['px' + sd] = sg * 0.8; base['py' + sd] = 0; base['pz' + sd] = -0.6; base['gaz' + sd] = 1;
    });
    var H = { L: new V3m(40, -6, 0).applyMatrix4(MR), R: new V3m(-40, -6, 0).applyMatrix4(MR) };
    var Ltop = legPressLen(cfg.kTop, cfg.w, cfg.e), Lbot = legPressLen(cfg.kBot, cfg.w, cfg.e);
    function ankleL(sd, L) { return H[sd].clone().addScaledVector(d, L).addScaledVector(tv, cfg.e).add(new V3m((sd === 'L' ? 1 : -1) * cfg.w, 0, 0)); }
    function ankle(sd, s) { return ankleL(sd, lerp(Ltop, Lbot, s)); }
    function legsAt(Rs, L) { return legKeys(Rs, { L: ankleL('L', L), R: ankleL('R', L) }, fp); }
    // The hip's flexion limit: the hip flexion (relative to the pelvis) at the correct exercise's own bottom (cfg.kBotRef). Past it
    // the range has to come from the pelvis: it ROLLS back on the pad (posterior tilt about the pad contact at the lumbar spine,
    // P0, so the root moves with it and the buttocks lift off) and the lumbar spine flexes (lean, solved on the posed skin at build so
    // the upper back stays on its pad). In the correct exercise (kBot = kBotRef) the limit is never reached and the tilt is exactly 0;
    // the mistake variant changes only kBot.
    var hpMax = legsAt(R, legPressLen(cfg.kBotRef, cfg.w, cfg.e)).hpL + 1e-6, P0 = null, LEAN = null;
    function rolled(t) {
      if (!t || !P0) return R;
      var a = -t * D2R, y = R.y - P0.y, z = R.z - P0.z;
      return merge(R, { y: P0.y + y * Math.cos(a) - z * Math.sin(a), z: P0.z + y * Math.sin(a) + z * Math.cos(a), pitch: pitch - t });
    }
    function tiltAt(L) {
      if (!P0 || legsAt(R, L).hpL <= hpMax) return 0;
      var lo = 0, hi = 45;
      for (var i = 0; i < 26; i++) { var mid = (lo + hi) / 2; if (legsAt(rolled(mid), L).hpL > hpMax) lo = mid; else hi = mid; }
      return hi;
    }
    function leanAt(s) {
      if (!LEAN) return 0;
      var x = Math.max(0, Math.min(1, s)) * (LEAN.length - 1), k = Math.min(LEAN.length - 2, Math.floor(x)), f = smooth(x - k);
      return LEAN[k] + (LEAN[k + 1] - LEAN[k]) * f;
    }
    function keys(s) {
      var L = lerp(Ltop, Lbot, s), t = tiltAt(L), Rs = rolled(t), k = legsAt(Rs, L);
      k.x = Rs.x; k.y = Rs.y; k.z = Rs.z; k.pitch = Rs.pitch; k.lean = t ? leanAt(s) : 0;
      k['mach.sled'] = s;
      return pref(p, k);
    }
    // the platform at sled position s: its face (normal -d, toward the lifter) passes through the soles, 26 below the ankles along d
    function face(s) { var a = ankle('L', s).add(ankle('R', s)).multiplyScalar(0.5); return { c: a.clone().addScaledVector(d, 26).addScaledVector(tv, 35), k: a.dot(d) + 26 }; }
    fig.apply(merge(pref(p, base), keys(0)));
    // back pad: the common tangent plane of the glutes and the upper back (a straight pad touches both bumps, the lower back may clear
    // it), 1 unit into the skin; the seat (rising toward the feet at cfg.seat deg) 1.5 units into the lowest glute skin. Pads span the
    // skin they carry.
    var G = [], B = [];
    skinScan(fig, ['hips'], function (v) { G.push(v.y, v.z); });
    skinScan(fig, ['chest'], function (v) { B.push(v.y, v.z); });
    function sup(P, th) { var ny = Math.cos(th * D2R), nz = Math.sin(th * D2R), lo = Infinity; for (var i = 0; i < P.length; i += 2) lo = Math.min(lo, P[i] * ny + P[i + 1] * nz); return lo; }
    function tg(th) { return sup(G, th) - sup(B, th); }
    var th0 = cfg.recline, lo = null, hi = null;
    for (var st = 0; st <= 30 && lo === null; st++) [-1, 1].forEach(function (sg) { if (lo !== null) return; var a = th0 + sg * st, b = th0 + sg * (st + 1); if ((tg(a) <= 0) !== (tg(b) <= 0)) { lo = a; hi = b; } });
    if (lo === null) { lo = hi = th0; }
    for (var it = 0; it < 30; it++) { var mid = (lo + hi) / 2; if ((tg(mid) <= 0) === (tg(lo) <= 0)) lo = mid; else hi = mid; }
    var thB = (lo + hi) / 2, bp = { n: new V3m(0, Math.cos(thB * D2R), Math.sin(thB * D2R)), d: Math.min(sup(G, thB), sup(B, thB)) + 1, tilt: thB };
    var upB = new V3m(0, bp.n.z, -bp.n.y), lamB = [Infinity, -Infinity];
    skinScan(fig, ['hips', 'spine', 'chest', 'neck', 'head'], function (v) { if (v.dot(bp.n) - bp.d < 40) { var l = v.dot(upB); lamB[0] = Math.min(lamB[0], l); lamB[1] = Math.max(lamB[1], l); } });
    // the rolling pivot: on the back pad's face, cfg.rollPivot up the pad from the hip joint (the lumbar spine); then, if this
    // exercise goes past the hip limit, the lumbar flexion that keeps the upper back on its pad, solved on the skin at 9 depths
    var Q = new V3m(x0, R.y, R.z).addScaledVector(upB, cfg.rollPivot); P0 = Q.addScaledVector(bp.n, bp.d - Q.dot(bp.n));
    if (tiltAt(Lbot) > 0) {
      LEAN = [];
      for (var li = 0; li <= 8; li++) {
        var sl = li / 8, Ll = lerp(Ltop, Lbot, sl), tl = tiltAt(Ll);
        if (!tl) { LEAN.push(0); continue; }
        var Rl = rolled(tl), kl = legsAt(Rl, Ll), llo = -tl, lhi = 2 * tl;
        kl.x = Rl.x; kl.y = Rl.y; kl.z = Rl.z; kl.pitch = Rl.pitch;
        for (var lj = 0; lj < 18; lj++) {
          kl.lean = (llo + lhi) / 2; fig.apply(merge(pref(p, base), pref(p, kl)));
          if (planeGap(fig, ['chest'], bp.n.clone().multiplyScalar(bp.d), bp.n) < -1) llo = kl.lean; else lhi = kl.lean;
        }
        LEAN.push((llo + lhi) / 2);
      }
      fig.apply(merge(pref(p, base), keys(0)));
    }
    var sa = cfg.seat * D2R, sp = { n: new V3m(0, Math.cos(sa), -Math.sin(sa)), d: Infinity }, upS = new V3m(0, sp.n.z, -sp.n.y), lamS = [Infinity, -Infinity];
    skinScan(fig, ['hips', 'thL', 'thR'], function (v) { sp.d = Math.min(sp.d, v.dot(sp.n)); });
    sp.d += 1.5;
    skinScan(fig, ['hips', 'thL', 'thR'], function (v) { if (v.dot(sp.n) - sp.d < 12) { var l = v.dot(upS); lamS[0] = Math.min(lamS[0], l); lamS[1] = Math.max(lamS[1], l); } });
    var mach = new THREE.Group();
    // the back pad ends near the back of the head (70 below the crown) so the hair hangs past its top edge with gravity; with a
    // headrest past the crown the solver laid the tail UP the slope on it (2026-11-24; the hair cannot slide along a tilted support)
    var backLen = lamB[1] - lamB[0] - 60, backPad = padAt(bp, (lamB[0] + lamB[1]) / 2 - 40, backLen, 170, x0); mach.add(backPad);
    var seatLen = lamS[1] - lamS[0] + 90, seatPad = padAt(sp, (lamS[0] - 60 + lamS[1] + 30) / 2, seatLen, 170, x0); mach.add(seatPad);   // upS points back: the seat reaches 60 forward under the thighs
    // frame under the pads: two posts to a floor rail
    var steelS = T3.colors.steelShade, F = face(0), Fb = face(1);
    [backPad, seatPad].forEach(function (pd) {
      var c = pd.position.clone().addScaledVector(new V3m(0, 0, 1).applyQuaternion(pd.quaternion), -34);
      var post = box(40, Math.max(10, c.y), 40, steelS); post.position.set(x0, c.y / 2, c.z); mach.add(post);
    });
    // sled: the platform (face on the plane), a carriage behind it with two plate horns, riding two rails along d
    var sled = new THREE.Group(); mach.add(sled);
    var plat = box(330, 300, 18, T3.colors.steel); plat.position.z = 9; sled.add(plat);
    var plTop = box(344, 314, 8, T3.colors.steelShade); plTop.position.z = 22; sled.add(plTop);
    var carr = box(200, 220, 40, steelS); carr.position.set(0, -20, 38); sled.add(carr);
    // plate horns below the platform's lower edge, so a side view sees the feet on the platform (rule 12: never hide the contact)
    [-1, 1].forEach(function (sg) {
      var horn = rod(8, T3.colors.steel); setRod(horn, new V3m(sg * 100, -190, 50), new V3m(sg * 250, -190, 50)); sled.add(horn);
      for (var i = 0; i < 2; i++) { var pl = disc(70 - 12 * i, 16, i ? T3.colors.plateFace : T3.colors.plate); pl.position.set(sg * (172 + i * 18), -190, 50); sled.add(pl); }
      var shoe = box(26, 70, 26, steelS); shoe.position.set(sg * 125, -60, 30); sled.add(shoe);
    });
    var hornBar = box(200, 26, 26, steelS); hornBar.position.set(0, -170, 45); sled.add(hornBar);
    var basis = new THREE.Matrix4().makeBasis(new V3m(1, 0, 0), tv, d);
    sled.quaternion.setFromRotationMatrix(basis);
    // rails: through the carriage shoes' path, from below the bottom position to above the top
    [-1, 1].forEach(function (sg) {
      var off = new V3m(sg * 125, 0, 0).addScaledVector(tv, -60).addScaledVector(d, 30 - 13);
      var a = Fb.c.clone().add(off).addScaledVector(d, -90), b = F.c.clone().add(off).addScaledVector(d, 160);
      var rail = rod(9, steelS); setRod(rail, a, b); mach.add(rail);
      [a, b].forEach(function (q) { var leg = box(22, Math.max(10, q.y), 22, steelS); leg.position.set(q.x, q.y / 2, q.z); mach.add(leg); });
    });
    var zA = Math.min(seatPad.position.z, backPad.position.z) - 120, zB = F.c.z + 160 * d.z + 60;
    var floor = box(300, 12, zB - zA, steelS); floor.position.set(x0, 6, (zA + zB) / 2); mach.add(floor);
    // handles in the fists
    ['L', 'R'].forEach(function (sd) {
      var Fp = fistPoint(fig, sd), grip = rod(6, T3.colors.pad); setRod(grip, Fp.clone().add(new V3m(0, 0, -22)), Fp.clone().add(new V3m(0, 0, 22))); mach.add(grip);
      var stem = rod(5, steelS); setRod(stem, Fp.clone().add(new V3m(0, 0, -22)), new V3m(Fp.x, Math.max(20, Fp.y - 120), Fp.z - 22)); mach.add(stem);
    });
    addProp(stage, fig, mach);
    function poseSled(s) { var f = face(s); sled.position.copy(f.c); sled.userData.s = s; sled.userData.k = f.k; }
    afterApply(fig, function (pose) { poseSled(mkey(pose, p, 'mach.sled', 0)); });
    if (fig.supports) { Array.prototype.push.apply(fig.supports, held); restsOnPad(fig, backPad, 30); }
    fig.apply({});
    m.base(pref(p, base)); m.base(keys(0));
    var end = reps(m, at, per, n, keys, def.rhythm);
    envelope(m, p, o.peaks || def.peaks, at, per, n);
    fig.pose = keys;
    fig.machine = { def: def, clock: { at: at, period: per, reps: n }, cfg: cfg, d: d, tv: tv, face: face, sled: sled, back: bp, seat: sp, hip: H, pitch: pitch };
    return end;
  }
  /*
   * Leg-press checks (exercises.json cue_checks): the glutes stay on the seat and the back on its pad (-4..2 units) and the pelvis does
   * not tilt (within 1 deg of its start); each knee stays within 10 units of the hip-to-toe line in the front view; heel AND ball on the
   * platform (-1.5..1.5) without sliding on it (1.5); the knees stop short of straight at the top (>= 8 deg) and reach >= 80 deg at the
   * bottom; the ankle stays between 20 deg plantar flexion and 30 deg dorsiflexion.
   */
  function legPressChecks(fig, v, t, out, lim) {
    lim = merge({ kneeLine: 10, kneeTop: 8, kneeBot: 80, glute: true, tilt: 1, ankle: 30, slide: 1.5 }, lim || {});
    var M = fig.machine, pre = fig.id ? fig.id + '.' : '', s = mkey(v, pre, 'mach.sled', 0), f = M.face(s), d = M.d;
    var bpP = M.back.n.clone().multiplyScalar(M.back.d), g1 = planeGap(fig, ['hips'], bpP, M.back.n), g2 = planeGap(fig, ['chest'], bpP, M.back.n);
    var g3 = planeGap(fig, ['hips', 'thL', 'thR'], M.seat.n.clone().multiplyScalar(M.seat.d), M.seat.n);
    range(out, 'gluteGap', g1); range(out, 'backGap', g2); range(out, 'seatGap', g3);
    var g4 = planeGap(fig, ['spine'], bpP, M.back.n); range(out, 'lumbarGap', g4); out.lumbarGapMin = out.lumbarGap[0]; out.lumbarGapMax = out.lumbarGap[1];
    out.gluteGapMin = out.gluteGap[0]; out.gluteGapMax = out.gluteGap[1]; out.backGapMin = out.backGap[0]; out.backGapMax = out.backGap[1]; out.seatGapMin = out.seatGap[0]; out.seatGapMax = out.seatGap[1];
    if (g1 < -4 || (lim.glute && g1 > 2)) flagOnce(out, 'leg press: the glutes are ' + g1.toFixed(1) + ' units off the back pad (hips stay on the pad: -4..2)');
    if (g2 < -4 || g2 > 2) flagOnce(out, 'leg press: the upper back is ' + g2.toFixed(1) + ' units off its pad (-4..2)');
    if (g3 < -4) flagOnce(out, 'leg press: the glutes or thighs sink ' + (-g3).toFixed(1) + ' units into the seat (max 4)');
    var q = new THREE.Quaternion(); fig.bone.hips.getWorldQuaternion(q);
    if (!out._q0) Object.defineProperty(out, '_q0', { value: q.clone() });
    var tilt = 2 * Math.acos(Math.min(1, Math.abs(q.dot(out._q0)))) / D2R;
    out.pelvisTilt = Math.max(out.pelvisTilt || 0, tilt);
    if (lim.tilt !== null && tilt > lim.tilt) flagOnce(out, 'leg press: the pelvis tilts ' + tilt.toFixed(1) + ' deg (cue: hips stay on the pad, no tuck; max ' + lim.tilt + ')');
    ['L', 'R'].forEach(function (sd) {
      var hj = fig.world('th' + sd), K = fig.world('kn' + sd), A = fig.world('an' + sd);
      var T = new V3m(0, T3.TIP.y - T3.BALL.y, T3.TIP.z - T3.BALL.z).applyMatrix4(fig.toes[sd].matrixWorld);
      var u = new V3m(0, T.y - hj.y, T.z - hj.z), lam = u.dot(new V3m(0, K.y - hj.y, K.z - hj.z)) / u.lengthSq(), off = K.x - lerp(hj.x, T.x, lam);
      out.kneeLine = Math.max(out.kneeLine || 0, Math.abs(off));
      if (Math.abs(off) > lim.kneeLine) flagOnce(out, 'leg press: a knee is ' + off.toFixed(1) + ' units off the hip-to-toe line (knees in line with the toes; max ' + lim.kneeLine + ')');
      var aw = fig.bone['an' + sd].matrixWorld, heel = new V3m(0, T3.HEEL.y, T3.HEEL.z).applyMatrix4(aw), ball = new V3m(0, T3.BALL.y, T3.BALL.z).applyMatrix4(aw);
      [['heel', heel], ['ball', ball]].forEach(function (h) {
        var gap = f.k - h[1].dot(d);
        range(out, h[0] + 'Gap', gap); out[h[0] + 'GapMin'] = out[h[0] + 'Gap'][0]; out[h[0] + 'GapMax'] = out[h[0] + 'Gap'][1];
        if (Math.abs(gap) > 1.5) flagOnce(out, 'leg press: the ' + h[0] + ' is ' + gap.toFixed(1) + ' units off the platform (whole foot on the platform: -1.5..1.5)');
      });
      var rel = heel.clone().sub(f.c), st = [rel.x, rel.dot(M.tv)];
      var k0 = 'slide' + sd; if (!out['_' + k0]) Object.defineProperty(out, '_' + k0, { value: st });
      var sl = Math.hypot(st[0] - out['_' + k0][0], st[1] - out['_' + k0][1]); out.footSlide = Math.max(out.footSlide || 0, sl);
      if (sl > lim.slide) flagOnce(out, 'leg press: a foot slides ' + sl.toFixed(1) + ' units on the platform (max ' + lim.slide + ')');
      var fl = 180 - T3.jointAngle(fig, 'th' + sd, 'kn' + sd, 'an' + sd);
      range(out, 'kneeFlex', fl); out.kneeFlexMin = out.kneeFlex[0]; out.kneeFlexMax = out.kneeFlex[1];
      var shin = K.clone().sub(A).normalize(), up = new V3m(0, 1, 0).transformDirection(aw), toe = new V3m(0, 0, 1).transformDirection(aw);
      var dors = Math.atan2(shin.dot(toe), shin.dot(up)) / D2R;
      range(out, 'ankleDorsi', dors); out.ankleDorsiMin = out.ankleDorsi[0]; out.ankleDorsiMax = out.ankleDorsi[1];
      if (dors < -20 || dors > lim.ankle) flagOnce(out, 'leg press: the ankle is at ' + dors.toFixed(0) + ' deg (plantar -20 .. dorsiflexion ' + lim.ankle + ')');
    });
    if (t >= M.clock.at + M.clock.reps * M.clock.period && !out._done) {
      Object.defineProperty(out, '_done', { value: true });
      if (lim.kneeTop !== null && out.kneeFlex[0] < lim.kneeTop) flagOnce(out, 'leg press: the knees straighten to ' + out.kneeFlex[0].toFixed(0) + ' deg (no hard snap at the top; stop at ' + lim.kneeTop + ' or more)');
      if (lim.kneeBot !== null && out.kneeFlex[1] < lim.kneeBot) flagOnce(out, 'leg press: the knees only bend to ' + out.kneeFlex[1].toFixed(0) + ' deg at the bottom (needs ' + lim.kneeBot + ')');
    }
  }
  T3.legPressChecks = legPressChecks;
  X3['leg-press'] = {
    id: 'leg-press', name: 'Leg press (45-degree sled)', knowledge: 'leg-press', period: 3.6, track: ['anL', 'anR'],
    phaseMap: [{ id: 'lockout', kind: 'hold', label: 'Top', a: 0, b: 0.04, cue: 'Soft knees at the top' }, { id: 'eccentric', kind: 'down', label: 'Lower', a: 0.04, b: 0.48, cue: 'Lower under control' },
      { id: 'end-range', kind: 'hold', label: 'Bottom', a: 0.48, b: 0.54, cue: 'Hips stay on the pad' }, { id: 'concentric', kind: 'up', label: 'Press', a: 0.54, b: 0.90, cue: 'Press through the whole foot' },
      { id: 'lockout2', kind: 'hold', label: 'Top', a: 0.90, b: 1.0, cue: 'Do not lock the knees' }],
    rhythm: { down: [0.04, 0.48], up: [0.54, 0.90] },
    acts: { quad: 3, glute: 3, adductor: 2, hams: 1, calf: 1 }, peaks: { quad: 1, glute: 0.85, adductor: 0.6, hams: 0.3, calf: 0.3 },
    shots: { side: { az: 90, el: 6 }, three: { az: 55, el: 14 }, high: { az: 75, el: 45 }, back: { az: 150, el: 16 }, otherSide: { az: 270, el: 8 } },
    build: function (stage, fig, m, o) { return buildLegPress(X3['leg-press'], stage, fig, m, o, LEGPRESS); },
    camera: { target: { tx: 0, ty: 420, tz: 120 }, dist: 2800, fov: 26 },
    checks: function (fig, v, t, out) { legPressChecks(fig, v, t, out); }
  };
  var LEGPRESS = { sled: 45, recline: 25, seat: 35, hipY: 250, kTop: 12, kBot: 85, kBotRef: 85, rollPivot: 120, e: 80, w: 12, neckF: 8, headF: 2 };
  // the mistake (exercises.json leg-press error "pelvis-lifts"): the same machine and solver, lowered deeper (knee 97 instead of 85; with the rolling pelvis the knee ends near 105);
  // past the hip's flexion at the correct bottom the pelvis rolls back and the lower back peels off the pad
  X3['leg-press-deep'] = {
    id: 'leg-press-deep', name: 'Leg press, too deep: lower back off the pad (mistake)', knowledge: 'leg-press', mistake: 'pelvis-lifts', period: 3.6,
    track: ['anL', 'anR'], phaseMap: X3['leg-press'].phaseMap, rhythm: X3['leg-press'].rhythm, acts: X3['leg-press'].acts, peaks: X3['leg-press'].peaks,
    shots: X3['leg-press'].shots,
    build: function (stage, fig, m, o) { return buildLegPress(X3['leg-press-deep'], stage, fig, m, o, merge(LEGPRESS, { kBot: 97 })); },
    camera: X3['leg-press'].camera,
    // the variant must SHOW the mistake: the pelvis rolls back at least 8 deg and the hips (pelvis skin) leave the back pad by at least 4 units; the lumbar skin gap is reported (it lifts 5-8 on the distance skin but not on the legacy skin)
    checks: function (fig, v, t, out) {
      legPressChecks(fig, v, t, out, { glute: false, tilt: null, ankle: 40, slide: 2.5 });   // too deep: the ankle and the foot's yaw go past the correct exercise's ranges too
      if (t >= fig.machine.clock.at + fig.machine.clock.reps * fig.machine.clock.period && !out._mv) {
        Object.defineProperty(out, '_mv', { value: true });
        if ((out.pelvisTilt || 0) < 8) flagOnce(out, 'pelvis-lifts variant: the pelvis rolls back only ' + (out.pelvisTilt || 0).toFixed(1) + ' deg (the mistake is not visible; needs 8)');
        if (out.gluteGap[1] < 4) flagOnce(out, 'pelvis-lifts variant: the hips stay within ' + out.gluteGap[1].toFixed(1) + ' units of the pad (the mistake is not visible; needs 4)');
      }
    }
  };

  // ================================================================ BARBELL BENCH PRESS (motion family 2, 2026-11-24)
  /*
   * The dumbbell press's lying pose and arch (solveArch), a straight bar in both fists. One parameter s (0 = lockout, 1 = bar on the
   * chest). The WRIST is driven, relative to the shoulder: its offset toward the feet runs linearly from 0 (bar over the shoulders) to
   * the touch point, its distance from the shoulder linearly from R_top (elbows cfg.lockFlex deg short of straight) to R_bottom, and its
   * distance outside the shoulder is a CONSTANT c (a rigid bar cannot change its grip). The elbow is then solved exactly (134 and 106
   * from shoulder and wrist, in the same side-view plane as the wrist, on the outer branch), so the forearm is vertical in the side
   * view at every frame and the elbow bend changes monotonically (interpolating the upper-arm direction instead let the arm straighten
   * past the IK reach early in the descent). The bottom is solved from the contact, not chosen: the bar touches the lower chest
   * cfg.touch units toward the feet from the shoulder (measured on the posed skin, 3 passes) with the forearm vertical from the front
   * too, so c, the grip width and the elbow flare FOLLOW from the body (about 45 deg here). The bar is posed after every fig.apply at
   * the midpoint of the two fists, so it is always in the hands, whatever the shoulder rig does. Uprights with J-hooks stand at the head
   * end, clear of the bar path. Illustrative.
   */
  function buildBenchBarbell(def, stage, fig, m, o, cfg) {
    o = o || {};
    var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 3, per = o.period || def.period || 3.4, benchTop = 175;
    var bench = EQ.bench({ x: -190, z: 0, y: benchTop, w: 135, l: 560, yaw: 90 }); addProp(stage, fig, bench); restsOn(fig, bench);
    var bar = EQ.barbell({ half: 380, plate: cfg.plate }); addProp(stage, fig, bar);
    fig.roles(def.acts);
    var lie = { x: 0, y: benchTop + 47, z: 0, pitch: -90, yaw: 90, lean: 0, fxL: 150, fzL: -62, fyawL: 90, fxR: 150, fzR: 62, fyawR: 90, kfL: 14, kfR: 14,
      ikL: 1, ikR: 1, gazL: 1, gazR: 1, wrL: 0, wrR: 0 };
    var FA = 106, UA = 134, c = 90, xB = 80, rB = 150, x0 = cfg.lockX;
    var rT = Math.sqrt(UA * UA + FA * FA + 2 * UA * FA * Math.cos(cfg.lockFlex * D2R));
    function arm(s) {                                                  // s: 0 = lockout, 1 = bottom; lifter's left is world -z
      // lockX > 0: at lockout the bar sits a little toward the feet of the shoulder joint, so the arm is never exactly in the plane
      // across the body, where the rig's hand roll (gaz, wrapped to +-90 deg) is ambiguous and one hand flipped 180 deg (legacy skin)
      var wx = lerp(x0, xB, s), R = lerp(rT, rB, s), wy = Math.sqrt(Math.max(0, R * R - wx * wx - c * c));
      // elbow in the plane x = wx: on the circle of radius sqrt(UA^2 - wx^2) round the shoulder and FA from the wrist (wy, c)
      var rA = Math.sqrt(Math.max(0, UA * UA - wx * wx)), dd = Math.hypot(wy, c), a = (rA * rA - FA * FA + dd * dd) / (2 * dd), h = Math.sqrt(Math.max(0, rA * rA - a * a));
      var ey = a * wy / dd + h * c / dd, ez = a * c / dd - h * wy / dd;                 // the branch with wy*ez - c*ey < 0 ... checked below
      if (wy * ez - c * ey < 0) { ey = a * wy / dd - h * c / dd; ez = a * c / dd + h * wy / dd; }   // keep the outer branch (elbow outside the shoulder-wrist line)
      var r = {};
      ['L', 'R'].forEach(function (sd) {
        var sg = sd === 'L' ? -1 : 1;
        r['hx' + sd] = wx; r['hy' + sd] = wy; r['hz' + sd] = sg * c;
        r['px' + sd] = wx / UA; r['py' + sd] = ey / UA; r['pz' + sd] = sg * ez / UA;
      });
      return r;
    }
    function fists() { return [fistPoint(fig, 'L'), fistPoint(fig, 'R')]; }
    function poseBar() {
      var F = fists(), mid = F[0].clone().add(F[1]).multiplyScalar(0.5), dir = F[1].clone().sub(F[0]).normalize();
      bar.position.copy(mid); bar.quaternion.setFromUnitVectors(new V3m(1, 0, 0), dir); bar.updateMatrixWorld(true);
      return mid;
    }
    var arch = (o.arch === undefined) ? 22 : o.arch;                    // (written differently from the press: tests patch that line)
    if (arch) merge2(lie, solveArch(fig, p, merge(lie, arm(0)), benchTop, arch));
    // the contact at the bottom, measured on the posed skin: chest top under the bar; the bar centre 1 unit into it (bar radius 6)
    var hB = null, S = null, touchX = null;
    for (var pass = 0; pass < 3; pass++) {
      fig.apply(pref(p, merge(lie, arm(1))));
      S = new V3m().setFromMatrixPosition(fig.bone.shL.matrixWorld); touchX = S.x + cfg.touch;
      var top = -Infinity, Bm = poseBar(), wy = new V3m().setFromMatrixPosition(fig.bone.handL.matrixWorld).y;
      skinScan(fig, ['chest', 'spine'], function (v) { if (Math.abs(v.x - touchX) < 8 && Math.abs(v.z) < 60 && v.y > top) top = v.y; });
      var barY = top + 6 - 1, fistUp = Bm.y - wy;                     // fist centre above the wrist joint
      hB = barY - fistUp - FA - S.y;                                    // the elbow's height below the shoulder at the bottom
      var ux = cfg.touch / UA, uy = hB / UA, uo = Math.sqrt(Math.max(0.01, 1 - ux * ux - uy * uy));
      c = UA * uo; xB = cfg.touch; rB = Math.hypot(xB, hB + FA, c);      // the wrist straight above the elbow at the bottom
    }
    m.base(pref(p, merge(lie, arm(0))));
    function keys(s) { return pref(p, arm(s)); }
    var end = reps(m, at, per, n, keys, def.rhythm);
    envelope(m, p, o.peaks || def.peaks, at, per, n);
    // rack: two uprights with J-hooks at the head end; the bar would rest on the hooks a little below and behind the lockout
    fig.apply(pref(p, merge(lie, arm(0))));
    var lock = poseBar(), rack = new THREE.Group(), steelS = T3.colors.steelShade, zU = Math.abs(fists()[0].z) + 46;
    [-1, 1].forEach(function (sg) {
      var up = box(16, lock.y + 60, 16, steelS); up.position.set(lock.x - cfg.rackBack, (lock.y + 60) / 2, sg * zU); rack.add(up);
      var foot = box(30, 10, 120, steelS); foot.position.set(lock.x - cfg.rackBack, 5, sg * zU); rack.add(foot);
      var hook = box(26, 8, 14, T3.colors.steel); hook.position.set(lock.x - cfg.rackBack + 18, lock.y - 14, sg * zU); rack.add(hook);
      var lip = box(6, 16, 14, T3.colors.steel); lip.position.set(lock.x - cfg.rackBack + 29, lock.y - 6, sg * zU); rack.add(lip);
    });
    addProp(stage, fig, rack);
    afterApply(fig, function () { poseBar(); });
    fig.apply({});
    fig.pose = keys;
    fig.bench = { def: def, clock: { at: at, period: per, reps: n }, bar: bar, rack: rack, shoulder: S, touchX: touchX, grip: 2 * (S.z < 0 ? -S.z : S.z) + 2 * c, shoulderW: 2 * Math.abs(S.z), c: c };
    return end;
  }
  /*
   * Barbell bench checks (exercises.json cue_checks): forearms vertical under the bar (side view, every frame; front view at the bottom)
   * within 12 deg; the bar touches the chest at the bottom (gap -2..3) between 40 and 120 units toward the feet from the shoulder and
   * finishes over the shoulders (within 15); glutes, shoulder blades and head on the pad and a natural arch (the dumbbell press checks);
   * elbow flare at the bottom 30-75 deg; wrists straight (hand within 15 deg of the forearm line); the bar level; the bar never touches
   * the uprights or hooks; a grip 1.4-2.3x the shoulder-joint width.
   */
  function benchBarbellChecks(fig, v, t, out) {
    var B = fig.bench, ph = T3.phaseAt(B.def, B.clock, t), bar = B.bar.position;
    benchRest(fig, out);
    ['L', 'R'].forEach(function (s) {
      var e = fig.world('el' + s), h = new V3m().setFromMatrixPosition(fig.bone['hand' + s].matrixWorld), sh = new V3m().setFromMatrixPosition(fig.bone['sh' + s].matrixWorld);
      var side = Math.atan2(Math.abs(h.x - e.x), h.y - e.y) / D2R, front = Math.atan2(Math.abs(h.z - e.z), h.y - e.y) / D2R;
      out.forearmSide = Math.max(out.forearmSide || 0, side);
      if (side > 12) flagOnce(out, 'barbell bench: the forearm leans ' + side.toFixed(0) + ' deg in the side view (cue: forearms vertical under the bar; max 12)');
      if (ph.id === 'end-range') {
        out.forearmFrontBottom = Math.max(out.forearmFrontBottom || 0, front);
        if (front > 12) flagOnce(out, 'barbell bench: at the bottom the forearm leans ' + front.toFixed(0) + ' deg in the front view (max 12)');
        var ua = e.clone().sub(sh), flare = Math.atan2(Math.abs(ua.z), ua.x) / D2R;
        range(out, 'flareBottom', flare); out.flareBottomMin = out.flareBottom[0]; out.flareBottomMax = out.flareBottom[1];
        if (flare < 30 || flare > 75) flagOnce(out, 'barbell bench: elbow flare ' + flare.toFixed(0) + ' deg at the bottom (30-75; 90 is the flare mistake)');
      }
      var fa = h.clone().sub(e).normalize(), hd = fig.point('hand' + s, 0, -24, 0).sub(h).normalize(), wr = Math.acos(Math.max(-1, Math.min(1, fa.dot(hd)))) / D2R;
      out.wristBend = Math.max(out.wristBend || 0, wr);
      if (wr > 15) flagOnce(out, 'barbell bench: the wrist bends ' + wr.toFixed(0) + ' deg (cue: wrists straight, stacked over the elbow; max 15)');
    });
    var F = [fistPoint(fig, 'L'), fistPoint(fig, 'R')], lvl = Math.abs(F[0].y - F[1].y) + Math.abs(F[0].x - F[1].x);
    out.barTilt = Math.max(out.barTilt || 0, lvl);
    if (lvl > 1) flagOnce(out, 'barbell bench: the bar is not level (' + lvl.toFixed(1) + ' units between the hands)');
    // the two hands roll as mirror images (an overhand grip on both); a 180-deg flip of one hand keeps the bar aligned but is wrong
    var roll = Math.abs(fig.bone.handL.rotation.y + fig.bone.handR.rotation.y) / D2R;
    out.handRollMismatch = Math.max(out.handRollMismatch || 0, roll);
    if (roll > 15) flagOnce(out, 'barbell bench: one hand is rolled ' + roll.toFixed(0) + ' deg off the mirror of the other (a flipped grip)');
    if (ph.id === 'end-range') {
      var top = -Infinity; skinScan(fig, ['chest', 'spine'], function (q) { if (Math.abs(q.x - bar.x) < 8 && Math.abs(q.z) < 60 && q.y > top) top = q.y; });
      var gap = bar.y - 6 - top, dx = bar.x - B.shoulder.x;
      range(out, 'chestGap', gap); out.chestGapMin = out.chestGap[0]; out.chestGapMax = out.chestGap[1]; out.touchFromShoulder = dx;
      if (gap < -2 || gap > 3) flagOnce(out, 'barbell bench: at the bottom the bar is ' + gap.toFixed(1) + ' units off the chest (touch, no bounce: -2..3)');
      if (dx < 40 || dx > 120) flagOnce(out, 'barbell bench: the bar touches ' + dx.toFixed(0) + ' units from the shoulder (lower chest: 40-120)');
    }
    if (ph.id === 'lockout' || ph.id === 'lockout2') {
      var lx = Math.abs(bar.x - B.shoulder.x); out.lockoutOverShoulder = Math.max(out.lockoutOverShoulder || 0, lx);
      if (lx > 15) flagOnce(out, 'barbell bench: at lockout the bar is ' + lx.toFixed(0) + ' units from over the shoulders (max 15)');
    }
    // the bar (radius 6, whole length) never enters an upright or a hook
    B.rack.updateMatrixWorld(true);
    var axis = new V3m(1, 0, 0).applyQuaternion(B.bar.quaternion), worst = Infinity, bb = new THREE.Box3();
    B.rack.children.forEach(function (o) {
      bb.setFromObject(o);
      for (var k = -380; k <= 380; k += 10) { var q = bar.clone().addScaledVector(axis, k); worst = Math.min(worst, bb.distanceToPoint(q) - 6); }
    });
    out.rackClearance = Math.min(out.rackClearance === undefined ? Infinity : out.rackClearance, worst);
    if (worst < 1) flagOnce(out, 'barbell bench: the bar hits the rack (' + worst.toFixed(1) + ' units)');
    if (!out._g) {
      Object.defineProperty(out, '_g', { value: true });
      out.gripToShoulder = B.grip / B.shoulderW;
      if (out.gripToShoulder < 1.4 || out.gripToShoulder > 2.3) flagOnce(out, 'barbell bench: the grip is ' + out.gripToShoulder.toFixed(2) + 'x the shoulder width (1.4-2.3)');
    }
  }
  T3.benchBarbellChecks = benchBarbellChecks;
  X3['barbell-bench-press'] = {
    id: 'barbell-bench-press', name: 'Barbell bench press', knowledge: 'barbell-bench-press', period: 3.4,
    phaseMap: [{ id: 'lockout', kind: 'hold', label: 'Lockout', a: 0, b: 0.04, cue: 'Bar over the shoulders' }, { id: 'eccentric', kind: 'down', label: 'Lower', a: 0.04, b: 0.46, cue: 'Forearms vertical under the bar' },
      { id: 'end-range', kind: 'hold', label: 'Touch', a: 0.46, b: 0.52, cue: 'Touch the lower chest, no bounce' }, { id: 'concentric', kind: 'up', label: 'Press', a: 0.52, b: 0.90, cue: 'Press up and back over the shoulders' },
      { id: 'lockout2', kind: 'hold', label: 'Lockout', a: 0.90, b: 1.0, cue: 'Shoulder blades back and down' }],
    rhythm: { down: [0.04, 0.46], up: [0.52, 0.90] },
    acts: { pec: 3, triceps: 3, 'delt-front': 2, biceps: 1 }, peaks: { pec: 1, triceps: 0.9, 'delt-front': 0.6, biceps: 0.25 },
    // side: az 0 looks along the bar, where the near plate (radius 90, a real 20 kg plate) covers the chest at the bottom at el 8-28;
    // from el 45 the near plate drops below the bench line and the bar on the lower chest is in full view (2026-11-24 candidates:
    // el 28, el 45, az 25, az 335, az 20 el 30). Forearm verticality reads best from `foot`.
    shots: { three: { az: 38, el: 24 }, side: { az: 0, el: 45 }, foot: { az: 90, el: 14 }, headEnd: { az: 270, el: 16 }, above: { az: 20, el: 68 } },
    build: function (stage, fig, m, o) { return buildBenchBarbell(X3['barbell-bench-press'], stage, fig, m, o, { touch: 85, lockFlex: 15, lockX: 6, plate: 90, rackBack: 70 }); },
    camera: { target: { tx: -120, ty: 280, tz: 0 }, dist: 2000, fov: 28 },
    checks: benchBarbellChecks
  };

  // ================================================================ PULLS AND PRESSES ON THE SHOULDER GIRDLE (motion family 3, 2026-11-25)
  /*
   * Overhead press, lat pulldown, pull-up, seated cable row and one-arm row. Their cues live at the shoulder's extremes (overhead, a
   * hang, blades pinched or reaching), so the arms are solved in the CHEST frame (ikcS = 1) against the glenohumeral joint where the
   * girdle (Tibi 0.8.0) will put it. T3.girdleJoint predicts that joint exactly: it replays the rig's own first IK pass from the rest
   * joint and T3.girdle (checked against the posed rig: 0.000 units, both bodies and sides, any trunk pose and blade keys). So an arm
   * length is measured from the MOVED joint (a straight arm stays straight overhead, where the joint rises up to 15 units), a forearm
   * can be held exactly vertical, and the blade keys (gpS retraction -, protraction +; geS depression -) can carry a cue without the
   * hand target running out of reach. Illustrative, not mocap.
   */
  function ghRest(S, sd) { return new V3m((sd === 'L' ? 1 : -1) * S.shx, S.shy - 150, -2); }
  /** The rig's arm IK elbow (upper arm 134, forearm 106) for joint J, wrist W and elbow pole (same frame for all three). */
  function elbowAt(J, W, pole) {
    var d = W.clone().sub(J), dl = d.length(), dd = Math.min(239.5, Math.max(28.5, dl)), u = d.clone().divideScalar(dl || 1);
    var pl = pole.clone().addScaledVector(u, -pole.dot(u)).normalize();
    var be = Math.acos(Math.max(-1, Math.min(1, (134 * 134 + dd * dd - 106 * 106) / (2 * 134 * dd))));
    return J.clone().addScaledVector(u.clone().multiplyScalar(Math.cos(be)).addScaledVector(pl, Math.sin(be)).normalize(), 134);
  }
  /** Where the girdle puts side sd's glenohumeral joint (chest frame) for a chest-frame wrist target W, pole and blade keys gp/ge. */
  function girdleJoint(S, sd, W, pole, gp, ge) {
    var sg = sd === 'L' ? 1 : -1, rest = ghRest(S, sd);
    if (S.noGirdle) return { J: rest.clone(), rest: rest, girdle: null };          // legacy profile: the girdle never moves
    var u = elbowAt(rest, W, pole).sub(rest).divideScalar(134);
    var g = T3.girdle(new V3m(sg * u.x, u.y, u.z), S, gp || 0, ge || 0), off = g.off.clone(); off.x *= sg;
    return { J: rest.clone().add(off), rest: rest, girdle: g };
  }
  T3.girdleJoint = girdleJoint;
  /** The spec the arm solvers use for a figure: its own, flagged when its profile keeps the girdle still (legacy). */
  function armSpec(fig) { var s = Object.create(fig.spec); s.noGirdle = fig.girdleOn === false; return s; }
  T3.elbowAt = elbowAt;
  /** Chest-frame arm keys (ikcS = 1): wrist W and pole in the chest frame, blade keys gp/ge. */
  function chestArm(S, sd, W, pole, gp, ge) {
    var rest = ghRest(S, sd), r = {};
    r['ik' + sd] = 1; r['ikc' + sd] = 1; r['hx' + sd] = W.x - rest.x; r['hy' + sd] = W.y - rest.y; r['hz' + sd] = W.z - rest.z;
    r['px' + sd] = pole.x; r['py' + sd] = pole.y; r['pz' + sd] = pole.z; r['gp' + sd] = gp || 0; r['ge' + sd] = ge || 0;
    return r;
  }
  /** Wrist (chest frame) at `len` from the MOVED joint, along unit direction dir from it (fixed point: the joint depends on the wrist). */
  function reachFromJoint(S, sd, dir, len, pole, gp, ge) {
    var W = ghRest(S, sd).addScaledVector(dir, len);
    for (var i = 0; i < 6; i++) W = girdleJoint(S, sd, W, pole, gp, ge).J.addScaledVector(dir, len);
    return W;
  }
  /** Wrist (chest frame) for an elbow direction u (unit) and a forearm direction f (unit), both from the MOVED joint. */
  function elbowDriven(S, sd, u, f, gp, ge) {
    var W = ghRest(S, sd).addScaledVector(u, 134).addScaledVector(f, 106);
    for (var i = 0; i < 6; i++) W = girdleJoint(S, sd, W, u, gp, ge).J.addScaledVector(u, 134).addScaledVector(f, 106);
    return W;
  }
  /** A world direction expressed in the chest frame of a trunk tipped forward by a degrees (pitch + lean, no yaw, twist or bend). */
  function worldToChest(v, a) { return v.clone().applyAxisAngle(new V3m(1, 0, 0), -a * D2R); }
  function chestToWorld(v, a) { return v.clone().applyAxisAngle(new V3m(1, 0, 0), a * D2R); }
  T3.worldToChest = worldToChest;
  /** Sagittal trunk angle (deg, + forward) of the chest bone's up axis; and the lumbar extension (deg, + arched) between pelvis and chest. */
  function trunkAngle(fig) { var q = new THREE.Quaternion().setFromRotationMatrix(fig.bone.chest.matrixWorld), u = new V3m(0, 1, 0).applyQuaternion(q); return Math.atan2(u.z, u.y) / D2R; }
  function lumbarExt(fig) {
    var qh = new THREE.Quaternion().setFromRotationMatrix(fig.bone.hips.matrixWorld), qc = new THREE.Quaternion().setFromRotationMatrix(fig.bone.chest.matrixWorld);
    var uh = new V3m(0, 1, 0).applyQuaternion(qh), uc = new V3m(0, 1, 0).applyQuaternion(qc);
    return (Math.atan2(uh.z, uh.y) - Math.atan2(uc.z, uc.y)) / D2R;
  }
  T3.trunkAngle = trunkAngle; T3.lumbarExt = lumbarExt;
  /** World position of side sd's (moved) glenohumeral joint. */
  function jointW(fig, sd) { return new V3m().setFromMatrixPosition(fig.bone['sh' + sd].matrixWorld); }
  function wristW(fig, sd) { return new V3m().setFromMatrixPosition(fig.bone['hand' + sd].matrixWorld); }
  /**
   * Least distance from the posed skin of `bones` to the given objects (equipment never enters the body). Each mesh is tested in its own
   * frame against its geometry's box (a world box of a rotated dumbbell covers air beside the plates, rule 35).
   */
  function propToSkin(fig, objs, bones, keep) {
    var parts = [];
    objs.forEach(function (o) { o.updateMatrixWorld(true); o.traverse(function (c) { if (!c.isMesh) return; c.geometry.computeBoundingBox(); parts.push({ inv: new THREE.Matrix4().copy(c.matrixWorld).invert(), box: c.geometry.boundingBox, s: new V3m().setFromMatrixScale(c.matrixWorld) }); }); });
    var d = Infinity, q = new V3m();
    skinScan(fig, bones, function (v) {
      if (keep && !keep(v)) return;
      for (var i = 0; i < parts.length; i++) { q.copy(v).applyMatrix4(parts[i].inv); var k = parts[i].box.distanceToPoint(q) * Math.min(parts[i].s.x, parts[i].s.y, parts[i].s.z); if (k < d) d = k; }
    });
    return d;
  }
  T3.propToSkin = propToSkin;
  /** Once per run: the phase-map timing rule (a slower lowering than lift) for an exercise with a clock. */
  function tempoRule(out, def, per, name) {
    if (out._tempo) return;
    Object.defineProperty(out, '_tempo', { value: true });
    var dur = function (kind) { var s = 0; def.phaseMap.forEach(function (q) { if (q.kind === kind) s += (q.b - q.a) * per; }); return s; };
    out.eccentricS = dur('down'); out.concentricS = dur('up');
    if (out.eccentricS <= out.concentricS) flagOnce(out, name + ': the lowering is not slower than the lift (' + out.eccentricS.toFixed(2) + ' vs ' + out.concentricS.toFixed(2) + ' s)');
  }

  // ---------------------------------------------------------------- seated dumbbell overhead press
  /*
   * Upright bench (seat and back pad built under the posed skin: seatFromSkin, backFromSkin), feet planted (IK, knees aimed along the
   * feet: kwS). One parameter s (0 = dumbbells at shoulder height, 1 = lockout). The ELBOW direction sweeps from 20 deg below the
   * horizontal in the scapular plane (30 deg forward of the frontal plane) to 15 deg short of straight overhead, and the wrist is held
   * exactly one forearm above the elbow in the WORLD (elbowDriven, from the moved joint), so the forearm is vertical at every frame and
   * the arms lock out 15 deg short of straight (wrist 238 from the moved joint, inside the 239 reach). The girdle lifts the joint by
   * itself overhead (upward rotation and clavicle elevation): no blade key. cfg.arch > 0 is the mistake (exercises.json
   * lower-back-arch): the pelvis tips forward by arch/2 and the lumbar spine extends by arch as the dumbbells rise, the trunk leans back
   * by arch/2 and the dumbbells finish in front of the shoulders; the hips slide forward on the seat so the shoulder blades stay on the pad.
   */
  var OHP = { hipY: 262, pitch: 0, footZ: 168, fx: 72, seatGap: 34, bottom: [0.814, -0.342, 0.47], top: [0.259, 0.966, 0.0], fwd: 0, arch: 0 };
  function buildOverheadPress(def, stage, fig, m, o, cfg) {
    o = o || {};
    var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 3, per = o.period || def.period || 3.4, x0 = o.x || 0, z0 = o.z || 0, S = armSpec(fig);
    fig.roles(def.acts);
    var dbs = [EQ.dumbbell(0.9), EQ.dumbbell(0.9)]; fig.hold('L', dbs[0]); fig.hold('R', dbs[1]);
    var held = fig.supports ? fig.supports.splice(0) : [];
    var uB = norm3(cfg.bottom), uT = norm3([cfg.top[0], cfg.top[1], cfg.top[2] + cfg.fwd]), slide = [0, 0, 0];
    function trunk(s) { var a = cfg.arch * smooth(s); return { pitch: cfg.pitch + 0.5 * a, lean: -a }; }
    function slideAt(s) { var a = slide[0], b = slide[1], c = slide[2]; return a * (1 - s) * (1 - 2 * s) + 4 * b * s * (1 - s) + c * s * (2 * s - 1); }
    function keys(s) {
      var tr = trunk(s), ca = tr.pitch + tr.lean, f = worldToChest(new V3m(0, 1, 0), ca);
      var u = slerp3(uB, uT, s), k = { x: x0, y: cfg.hipY, z: z0 + slideAt(s), pitch: tr.pitch, lean: tr.lean, neckF: -0.8 * ca, headF: -0.2 * ca, gaxL: 1, gaxR: 1, garL: 60, garR: -60, wrL: 0, wrR: 0 };
      ['L', 'R'].forEach(function (sd) {
        var sg = sd === 'L' ? 1 : -1, uc = worldToChest(new V3m(sg * u[0], u[1], u[2]), ca);
        merge2(k, chestArm(S, sd, elbowDriven(S, sd, uc, f), uc));
        k['fx' + sd] = x0 + sg * cfg.fx; k['fz' + sd] = z0 + cfg.footZ; k['fyaw' + sd] = sg * 10; k['kw' + sd] = 1; k['ikLeg' + sd] = 1;
      });
      return pref(p, k);
    }
    fig.apply(keys(0));
    var K = fig.world('knL'), seat = seatFromSkin(fig, cfg.pitch, function (z) { return z < K.z - cfg.seatGap; });
    var bp = backFromSkin(fig, cfg.pitch, seat.top + 150);
    // the arch variant: slide the hips forward so the shoulder blades stay on the pad (back skin 1 unit into it at s = 0, 0.5 and 1)
    if (cfg.arch) for (var it = 0; it < 3; it++) [0, 0.5, 1].forEach(function (s, i) {
      fig.apply(keys(s));
      slide[i] += -1 - planeGap(fig, ['chest'], new V3m(0, 0, bp.d / bp.n.z), bp.n, function (v) { return v.y > seat.top + 220; });
    });
    var mach = new THREE.Group(), seatLen = K.z - cfg.seatGap - (seat.zBack - 40);
    var sp = box(190, 34, seatLen, T3.colors.pad); sp.position.set(x0, seat.top - 17, K.z - cfg.seatGap - seatLen / 2); mach.add(sp);
    var sc = box(176, 6, seatLen - 14, T3.colors.padTop); sc.position.set(x0, seat.top - 2, sp.position.z); mach.add(sc);
    // the back pad ends 40 below the shoulder joints: the shoulder blades still rest on it and the ponytail hangs past its top edge
    var padTop = restJointW(fig, 'L').y - 40, backPad = padOnPlane(bp, (padTop + seat.top + 40) / 2, padTop - seat.top - 40, 200); backPad.position.x = x0; mach.add(backPad);
    var col = box(46, seat.top - 34, 46, T3.colors.steelShade); col.position.set(x0, (seat.top - 34) / 2, sp.position.z); mach.add(col);
    var foot = box(220, 10, 120, T3.colors.steelShade); foot.position.set(x0, 5, sp.position.z); mach.add(foot);
    var strut = box(30, seat.top + 330, 30, T3.colors.steelShade); strut.position.set(x0, (seat.top + 330) / 2, bp.at.z - 50); mach.add(strut);
    var brace = box(30, 30, Math.abs(bp.at.z - 50 - sp.position.z), T3.colors.steelShade); brace.position.set(x0, 40, (bp.at.z - 50 + sp.position.z) / 2); mach.add(brace);
    addProp(stage, fig, mach);
    if (fig.supports) Array.prototype.push.apply(fig.supports, held);
    fig.apply({});
    m.base(keys(0));
    var end = reps(m, at, per, n, keys, def.rhythm);
    envelope(m, p, o.peaks || def.peaks, at, per, n);
    fig.pose = keys;
    fig.ohp = { def: def, clock: { at: at, period: per, reps: n }, cfg: cfg, seatTop: seat.top, kneeZ: K.z, back: bp, dumbbells: dbs };
    return end;
  }
  /*
   * Overhead press checks (exercises.json cue_checks): forearms within 12 deg of vertical (front and side views) at every frame; at the
   * bottom the dumbbell handles between shoulder and ear height (10-120 units above the moved joint); at lockout the elbows within 22 deg
   * of straight with the wrists over the shoulders (within 25 units fore-aft: "overhead, not forward"); the glutes on the seat and the
   * shoulder blades on the pad; the trunk still (lumbar extension within 3 deg of its start: "ribs down"); the dumbbells never touch the
   * head; a slower lowering than press. lim.arch: the arch variant must show its mistake (extension and a forward finish).
   */
  function ohpChecks(fig, v, t, out, lim) {
    lim = merge({ trunk: 3, over: 25, back: true, arch: null }, lim || {});
    var H = fig.ohp, ph = T3.phaseAt(H.def, H.clock, t), inSet = ph.rep >= 1 && ph.rep <= H.clock.reps, name = 'overhead press';
    ['L', 'R'].forEach(function (s) {
      var e = fig.world('el' + s), h = wristW(fig, s), J = jointW(fig, s);
      var side = Math.atan2(Math.abs(h.z - e.z), h.y - e.y) / D2R, front = Math.atan2(Math.abs(h.x - e.x), h.y - e.y) / D2R;
      out.forearmTilt = Math.max(out.forearmTilt || 0, side, front);
      if (Math.max(side, front) > 12) flagOnce(out, name + ': the forearm leans ' + Math.max(side, front).toFixed(0) + ' deg off vertical (cue: forearms vertical; max 12)');
      if (inSet && (ph.id === 'start' || ph.id === 'reset')) {
        var hy = fistPoint(fig, s).y - J.y; range(out, 'handleAboveShoulder', hy); out.handleAboveShoulderMin = out.handleAboveShoulder[0]; out.handleAboveShoulderMax = out.handleAboveShoulder[1];
        if (hy < 10 || hy > 120) flagOnce(out, name + ': at the bottom the dumbbell is ' + hy.toFixed(0) + ' units above the shoulder joint (shoulder to ear height: 10-120)');
      }
      if (inSet && ph.id === 'end-range') {
        var ef = 180 - T3.jointAngle(fig, 'sh' + s, 'el' + s, 'hand' + s), fw = h.z - J.z;
        range(out, 'lockoutElbow', ef); out.lockoutElbowMax = out.lockoutElbow[1];
        range(out, 'lockoutForward', fw); out.lockoutForwardMax = out.lockoutForward[1];
        if (ef > 22) flagOnce(out, name + ': at lockout the elbow is still bent ' + ef.toFixed(0) + ' deg (cue: arms nearly straight overhead; max 22)');
        if (lim.over !== null && Math.abs(fw) > lim.over) flagOnce(out, name + ': at lockout the wrist is ' + fw.toFixed(0) + ' units in front of the shoulder (cue: overhead, not forward; max ' + lim.over + ')');
      }
    });
    var g = T3.skinLow(fig, ['hips', 'thL', 'thR'], function (q) { return q.z < H.kneeZ - H.cfg.seatGap; }).y - H.seatTop;
    range(out, 'seatGap', g); out.seatGapMin = out.seatGap[0]; out.seatGapMax = out.seatGap[1];
    if (g < -4 || g > 2) flagOnce(out, name + ': the glutes are ' + g.toFixed(1) + ' units off the seat (-4..2)');
    var bg = planeGap(fig, ['chest'], new V3m(0, 0, H.back.d / H.back.n.z), H.back.n, function (q) { return q.y > H.seatTop + 220; });
    range(out, 'backGap', bg); out.backGapMin = out.backGap[0]; out.backGapMax = out.backGap[1];
    if (lim.back && (bg < -4 || bg > 2)) flagOnce(out, name + ': the shoulder blades are ' + bg.toFixed(1) + ' units off the back pad (-4..2)');
    var le = lumbarExt(fig);
    if (out._le0 === undefined) Object.defineProperty(out, '_le0', { value: le, writable: true });
    var dle = le - out._le0; range(out, 'lumbarExt', dle); out.lumbarExtMax = out.lumbarExt[1];
    if (lim.trunk !== null && Math.abs(dle) > lim.trunk) flagOnce(out, name + ': the lower back arches ' + dle.toFixed(1) + ' deg (cue: ribs down; max ' + lim.trunk + ')');
    var hd = propToSkin(fig, H.dumbbells, ['head', 'neck']);
    out.headClearance = Math.min(out.headClearance === undefined ? Infinity : out.headClearance, hd);
    if (hd < 3) flagOnce(out, name + ': a dumbbell comes within ' + hd.toFixed(1) + ' units of the head (min 3)');
    tempoRule(out, H.def, H.clock.period, name);
    if (lim.arch !== null && t >= H.clock.at + H.clock.reps * H.clock.period && !out._mv) {
      Object.defineProperty(out, '_mv', { value: true });
      if ((out.lumbarExtMax || 0) < lim.arch) flagOnce(out, 'lower-back-arch variant: the lower back arches only ' + (out.lumbarExtMax || 0).toFixed(1) + ' deg (the mistake is not visible; needs ' + lim.arch + ')');
      if ((out.lockoutForwardMax || 0) < 25) flagOnce(out, 'lower-back-arch variant: the dumbbells finish only ' + (out.lockoutForwardMax || 0).toFixed(0) + ' units in front of the shoulders (the mistake is not visible; needs 25)');
    }
  }
  T3.ohpChecks = ohpChecks;
  var OHP_PHASES = [{ id: 'start', kind: 'hold', label: 'Shoulder height', a: 0, b: 0.04, cue: 'Forearms vertical' }, { id: 'concentric', kind: 'up', label: 'Press', a: 0.04, b: 0.40, cue: 'Press straight up' },
    { id: 'end-range', kind: 'hold', label: 'Lockout', a: 0.40, b: 0.50, cue: 'Ribs down, arms long' }, { id: 'eccentric', kind: 'down', label: 'Lower', a: 0.50, b: 0.94, cue: 'Lower to shoulder height' },
    { id: 'reset', kind: 'hold', label: 'Shoulder height', a: 0.94, b: 1.0, cue: '' }];
  var PRESS_RHYTHM = { down: [0.04, 0.40], up: [0.50, 0.94], downEase: 'power2.inOut', upEase: 'sine.inOut' };
  X3['overhead-press'] = {
    id: 'overhead-press', name: 'Seated dumbbell overhead press', knowledge: 'overhead-press', period: 3.4, phaseMap: OHP_PHASES, rhythm: PRESS_RHYTHM,
    acts: { 'delt-front': 3, triceps: 3, 'delt-side': 2, trap: 2, serratus: 1, pec: 1 }, peaks: { 'delt-front': 1, triceps: 0.85, 'delt-side': 0.7, trap: 0.5, serratus: 0.4, pec: 0.25 },
    shots: { front: { az: 8, el: 8 }, three: { az: 35, el: 12 }, side: { az: 90, el: 6 }, high: { az: 25, el: 35 } },
    build: function (stage, fig, m, o) { return buildOverheadPress(X3['overhead-press'], stage, fig, m, o, merge(OHP, {})); },
    camera: { target: { tx: 0, ty: 520, tz: 40 }, dist: 2100, fov: 26 },
    checks: function (fig, v, t, out) { ohpChecks(fig, v, t, out, {}); }
  };
  X3['overhead-press-arch'] = {
    id: 'overhead-press-arch', name: 'Overhead press, lower back arching (mistake)', knowledge: 'overhead-press', mistake: 'lower-back-arch', period: 3.4, phaseMap: OHP_PHASES, rhythm: PRESS_RHYTHM,
    acts: X3['overhead-press'].acts, peaks: X3['overhead-press'].peaks, shots: X3['overhead-press'].shots,
    build: function (stage, fig, m, o) { return buildOverheadPress(X3['overhead-press-arch'], stage, fig, m, o, merge(OHP, { arch: 16, fwd: 0.24 })); },
    camera: X3['overhead-press'].camera,
    checks: function (fig, v, t, out) { ohpChecks(fig, v, t, out, { trunk: null, over: null, back: true, arch: 10 }); }
  };

  // ---------------------------------------------------------------- lat pulldown and pull-up (one arm path)
  /*
   * Both pull a bar from straight arms overhead to the upper chest, so they share one arm path in the CHEST frame. The wrists run on a
   * straight line (direction upC; in the pulldown the world vertical for its trunk angle, so the cable hangs plumb) from the bottom B,
   * calibrated on the posed skin so the bar in the fists sits cfg.chestGap in front of the upper chest at cfg.barDrop below the joint, up
   * to where the arm is soft-straight from the MOVED joint (cfg.reach 238: elbows 15 deg short of straight). e = 0 (top) .. 1 (bottom).
   * The blades lead: over e 0..cfg.lead the blade is drawn down (geS 0 -> cfg.depress) with the arm still straight (the wrists come down
   * the line exactly as far as the falling joint lets them, the length solved at each depression), and only then do the elbows bend
   * (wrists down the line to B, smoothstep) while the blades draw back (gpS 0 -> cfg.retract). Elbows point out and back (pole). Grip:
   * wrists cfg.grip x the joint half-width out from the midline, so the grip is about 1.5x the shoulder-joint width.
   */
  function pullPath(S, cfg, upC, B) {
    var pole = {}, Bs = {};
    ['L', 'R'].forEach(function (sd) { var sg = sd === 'L' ? 1 : -1; pole[sd] = new V3m(sg * 0.7, -1, -0.45).normalize(); Bs[sd] = new V3m(sg * B.x, B.y, B.z); });
    function straight(sd, gp, ge) {                                   // line parameter where the wrist is cfg.reach from the moved joint
      var lo = 0, hi = 420;
      for (var i = 0; i < 40; i++) { var mid = (lo + hi) / 2, W = Bs[sd].clone().addScaledVector(upC, mid); if (W.distanceTo(girdleJoint(S, sd, W, pole[sd], gp, ge).J) > cfg.reach) hi = mid; else lo = mid; }
      return (lo + hi) / 2;
    }
    var lamD = straight('L', 0, cfg.depress), lamT = straight('L', 0, 0);
    function at(e) {
      var r = {}, lead = cfg.lead, d = smooth(e / lead), k = smooth((e - lead) / (1 - lead)), ge = cfg.depress * d, gp = cfg.retract * k;
      ['L', 'R'].forEach(function (sd) {
        var lam = e <= lead ? straight(sd, 0, ge) : lamD * (1 - k);
        r[sd] = { W: Bs[sd].clone().addScaledVector(upC, lam), pole: pole[sd], gp: gp, ge: ge, lam: lam };
      });
      return r;
    }
    return { at: at, lamTop: lamT, lamD: lamD, pole: pole };
  }
  function pullArms(S, q) { var k = {}; ['L', 'R'].forEach(function (sd) { merge2(k, chestArm(S, sd, q[sd].W, q[sd].pole, q[sd].gp, q[sd].ge)); }); return k; }
  /** A lat bar: straight centre with ends bent down 18 deg; local x along the bar, centred. */
  EQ.latBar = function (half) {
    var g = new THREE.Group(), straightHalf = half - 70, c = rod(5.5, T3.colors.steel);
    setRod(c, new V3m(-straightHalf, 0, 0), new V3m(straightHalf, 0, 0)); g.add(c);
    [-1, 1].forEach(function (sg) {
      var e = rod(5.5, T3.colors.steel); setRod(e, new V3m(sg * straightHalf, 0, 0), new V3m(sg * (straightHalf + 70 * Math.cos(18 * D2R)), -70 * Math.sin(18 * D2R), 0)); g.add(e);
      var grip = rod(7.5, T3.colors.pad); setRod(grip, new V3m(sg * (straightHalf + 18), -6, 0), new V3m(sg * (straightHalf + 64), -20, 0)); g.add(grip);
    });
    var ring = disc(9, 16, T3.colors.steelShade); g.add(ring);
    return g;
  };
  /** Bar centre and axis from the fists, in chest-frame coordinates of the current pose (calibration). */
  function fistsInChest(fig) {
    var inv = new THREE.Matrix4().copy(fig.bone.chest.matrixWorld).invert(), a = fistPoint(fig, 'L').applyMatrix4(inv), b = fistPoint(fig, 'R').applyMatrix4(inv);
    return a.add(b).multiplyScalar(0.5);
  }
  /** Front-most chest skin (chest frame) within 10 units of height y and 40 of the midline. */
  function chestFront(fig, y) {
    var inv = new THREE.Matrix4().copy(fig.bone.chest.matrixWorld).invert(), z = -Infinity, q = new V3m();
    skinScan(fig, ['chest'], function (v) { q.copy(v).applyMatrix4(inv); if (Math.abs(q.x) < 40 && Math.abs(q.y - y) < 10 && q.z > z) z = q.z; });
    return z;
  }
  /** Calibrate the bottom wrist B (chest frame) so the bar in the fists sits gap in front of the chest skin at barDrop below the joint. */
  function calibratePullBottom(fig, S, cfg, keysAtBottom) {
    var B = new V3m(S.shx * cfg.grip, S.shy - 150 - cfg.barDrop - 22, 60), yBar = S.shy - 150 - cfg.barDrop;
    for (var pass = 0; pass < 4; pass++) {
      fig.apply(keysAtBottom(B));
      var F = fistsInChest(fig), front = chestFront(fig, F.y);
      B.z += (front + 6 + cfg.chestGap) - F.z; B.y += yBar - F.y;
    }
    return B;
  }
  var PULL = { grip: 1.6, barDrop: 32, chestGap: 3, reach: 238, lead: 0.26, depress: -8, retract: -8 };

  /*
   * LAT PULLDOWN: seated (seat under the posed skin, a thigh roller 1 unit into the thighs above the knees, feet planted), the trunk
   * leaning back cfg.pitch + cfg.lean (about 14 deg) and still. The bar is posed in the fists after every fig.apply; its cable hangs
   * plumb to a pulley over the top position, runs forward over a boom and down to a weight stack in front and to the lifter's right
   * (clear of the front view), whose top plates rise by exactly the bar's travel. cfg.swing > 0 is the swing-back mistake: the trunk
   * rocks back by `swing` degrees as the bar comes down (the arm path rides the trunk, so the bar swings with it).
   */
  function buildPulldown(def, stage, fig, m, o, cfg) {
    o = o || {};
    var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 3, per = o.period || def.period || 3.6, x0 = o.x || 0, z0 = o.z || 0, S = armSpec(fig);
    fig.roles(def.acts);
    var held = fig.supports ? fig.supports.splice(0) : [];
    var a0 = cfg.pitch + cfg.lean, upC = worldToChest(new V3m(0, 1, 0), a0), path = null;
    function trunk(e) { var sw = cfg.swing * smooth(e); return { pitch: cfg.pitch - 0.6 * sw, lean: cfg.lean - 0.4 * sw }; }
    function body(e) {
      var tr = trunk(e), ca = tr.pitch + tr.lean, k = { x: x0, y: cfg.hipY, z: z0, pitch: tr.pitch, lean: tr.lean, neckF: -0.7 * ca, headF: -0.2 * ca, gaxL: 1, gaxR: 1, garL: 60, garR: -60, wrL: 0, wrR: 0 };
      ['L', 'R'].forEach(function (sd) { var sg = sd === 'L' ? 1 : -1; k['fx' + sd] = x0 + sg * cfg.fx; k['fz' + sd] = z0 + cfg.footZ; k['fyaw' + sd] = sg * 10; k['kw' + sd] = 1; k['ikLeg' + sd] = 1; });
      return k;
    }
    var B = calibratePullBottom(fig, S, cfg, function (Bt) {
      var q = pullPath(S, cfg, upC, Bt).at(1); return pref(p, merge(body(0), pullArms(S, q)));
    });
    path = pullPath(S, cfg, upC, B);
    // the swing variant keeps the bar path plumb under the pulley while the trunk rocks back (the path is re-aimed for each trunk angle)
    function pathAt(e) { if (!cfg.swing) return path.at(e); var tr = trunk(e); return pullPath(S, cfg, worldToChest(new V3m(0, 1, 0), tr.pitch + tr.lean), B).at(e); }
    function keys(e) { return pref(p, merge(body(e), pullArms(S, pathAt(e)))); }
    var bar = EQ.latBar(cfg.barHalf); addProp(stage, fig, bar);
    function fists() { return [fistPoint(fig, 'L'), fistPoint(fig, 'R')]; }
    function poseBar() {
      var F = fists(), mid = F[0].clone().add(F[1]).multiplyScalar(0.5), dir = F[0].clone().sub(F[1]).normalize();
      bar.position.copy(mid); bar.quaternion.setFromUnitVectors(new V3m(1, 0, 0), dir); bar.updateMatrixWorld(true);
      return mid;
    }
    // seat, thigh roller and the frame, from the posed skin at the top
    fig.apply(keys(0));
    var top = poseBar().clone(), K = fig.world('knL'), seat = seatFromSkin(fig, cfg.pitch, function (z) { return z < K.z - cfg.seatGap; });
    var lr = 24, zc = K.z - cfg.lapBack, topY = -Infinity;
    skinScan(fig, ['thL', 'thR'], function (v) { if (Math.abs(v.z - zc) < lr && Math.abs(v.x - x0) < 95) { var h = v.y + Math.sqrt(Math.max(0, lr * lr - (v.z - zc) * (v.z - zc))) - lr; if (h > topY) topY = h; } });
    var lap = { C: new V3m(x0, topY + lr - 1, zc), r: lr };
    var mach = new THREE.Group(), steelS = T3.colors.steelShade, seatLen = K.z - cfg.seatGap - (seat.zBack - 30);
    var sp = box(180, 34, seatLen, T3.colors.pad); sp.position.set(x0, seat.top - 17, K.z - cfg.seatGap - seatLen / 2); mach.add(sp);
    var sc = box(166, 6, seatLen - 14, T3.colors.padTop); sc.position.set(x0, seat.top - 2, sp.position.z); mach.add(sc);
    var col = box(46, seat.top - 34, 46, steelS); col.position.set(x0, (seat.top - 34) / 2, sp.position.z); mach.add(col);
    var lapRoll = disc(lr, 190, T3.colors.pad); lapRoll.position.copy(lap.C); mach.add(lapRoll);
    var lapEnd = disc(8, 210, T3.colors.steel); lapEnd.position.copy(lap.C); mach.add(lapEnd);
    [-1, 1].forEach(function (sg) { var arm = rod(6, steelS); setRod(arm, new V3m(x0 + sg * 105, lap.C.y, zc), new V3m(x0 + sg * 105, seat.top - 24, zc)); mach.add(arm); });
    var xs = x0 - cfg.stackX, zs = z0 + cfg.stackZ, yP = top.y + cfg.pulleyUp;
    var stack = EQ.stack({ x: xs, z: zs, n: 14, moving: 6, frameH: yP + 30 }); mach.add(stack);
    var P1 = new V3m(top.x, yP, top.z), P2 = new V3m(xs, yP, zs);
    var boom = box(30, 24, 30, steelS); mach.add(boom);
    (function () { var d = P1.clone().sub(P2), L = d.length(); boom.scale.set(1, 1, L / 30); boom.position.copy(P1).add(P2).multiplyScalar(0.5).add(new V3m(0, 26, 0)); boom.lookAt(P1.clone().add(new V3m(0, 26, 0))); })();
    var pul1 = disc(16, 12, T3.colors.steel); pul1.position.copy(P1); pul1.rotation.set(0, 0, 0); mach.add(pul1);
    var pul2 = disc(16, 12, T3.colors.steel); pul2.position.copy(P2); mach.add(pul2);
    var cableA = rod(1.6, T3.colors.charcoal || T3.colors.steelShade), cableB = rod(1.6, T3.colors.charcoal || T3.colors.steelShade), cableC = rod(1.6, T3.colors.charcoal || T3.colors.steelShade);
    mach.add(cableA); mach.add(cableB); mach.add(cableC);
    addProp(stage, fig, mach);
    function poseMachine() {
      var mid = poseBar(), rise = Math.max(0, top.y - mid.y);
      stack.userData.stack.set(rise);
      setRod(cableA, mid.clone().add(new V3m(0, 9, 0)), P1); setRod(cableB, P1, P2); setRod(cableC, P2, stack.userData.stack.top(rise));
    }
    afterApply(fig, function () { poseMachine(); });
    if (fig.supports) Array.prototype.push.apply(fig.supports, held);
    fig.apply({});
    m.base(keys(0));
    var end = reps(m, at, per, n, keys, def.rhythm);
    envelope(m, p, o.peaks || def.peaks, at, per, n);
    fig.pose = keys;
    fig.pull = { def: def, clock: { at: at, period: per, reps: n }, cfg: cfg, bar: bar, top: top, seatTop: seat.top, kneeZ: K.z, lap: lap, path: path, stack: stack, P1: P1 };
    return end;
  }
  /*
   * Pull checks shared by the pulldown and the pull-up (exercises.json cue_checks): the bar stays in front of the face (it never comes
   * within 4 units of the head and passes the head's height in front of its centre plane); at the bottom (end-range) the bar is within
   * 12 units of the upper chest; each rep returns to straight arms (elbows within 20 deg of straight at the top); the blades lead (the
   * depression has started at least 0.15 s before the elbows bend 5 deg); the elbows come down beside the ribs (at least 60 below the
   * joint at the bottom); the bar level; a slower return than pull.
   */
  function pullChecks(fig, v, t, out, name, lim) {
    var P = fig.pull, ph = T3.phaseAt(P.def, P.clock, t), inSet = ph.rep >= 1 && ph.rep <= P.clock.reps, bar = P.bar.position, p = fig.id ? fig.id + '.' : '';
    var F = [fistPoint(fig, 'L'), fistPoint(fig, 'R')], lvl = Math.abs(F[0].y - F[1].y);
    out.barTilt = Math.max(out.barTilt || 0, lvl);
    if (lvl > 1.5) flagOnce(out, name + ': the bar is not level (' + lvl.toFixed(1) + ' units between the hands)');
    // the bar against the head: clearance from the bar's centre straight to the head skin (bar radius 5.5), and the side it passes on
    var head = fig.world('head'), hd = Infinity, axis = new V3m(1, 0, 0).applyQuaternion(P.bar.quaternion);
    skinScan(fig, ['head', 'neck'], function (q) { var r = q.clone().sub(bar), along = r.dot(axis); if (Math.abs(along) > 120) return; var d = r.addScaledVector(axis, -along).length() - 5.5; if (d < hd) hd = d; });
    out.headClearance = Math.min(out.headClearance === undefined ? Infinity : out.headClearance, hd);
    if (hd < 4) flagOnce(out, name + ': the bar comes within ' + hd.toFixed(1) + ' units of the head (min 4)');
    var hf = fig.bone.head.matrixWorld, fwd = new V3m(0, 0, 1).transformDirection(hf), rel = bar.clone().sub(head);
    if (Math.abs(rel.y) < 90) { var side = rel.dot(fwd); out.barBeforeFaceMin = Math.min(out.barBeforeFaceMin === undefined ? Infinity : out.barBeforeFaceMin, side);
      if (lim.front && side < 0) flagOnce(out, name + ': the bar passes behind the head (cue: bar in front of the face)'); }
    ['L', 'R'].forEach(function (s) {
      var ef = 180 - T3.jointAngle(fig, 'sh' + s, 'el' + s, 'hand' + s), J = jointW(fig, s), e = fig.world('el' + s);
      range(out, 'elbowFlex', ef); out.elbowFlexMax = out.elbowFlex[1];
      if (ef > 145) flagOnce(out, name + ': the elbow bends ' + ef.toFixed(0) + ' deg (max 145)');
      if (inSet && (ph.id === 'start' || ph.id === 'reset')) {
        var rt = out._top || Object.defineProperty(out, '_top', { value: {} })._top; rt[ph.rep] = Math.max(rt[ph.rep] === undefined ? -Infinity : rt[ph.rep], ef);
      }
      if (inSet && ph.id === 'end-range') { var drop = J.y - e.y; range(out, 'elbowDrop', drop); out.elbowDropMin = out.elbowDrop[0];
        if (drop < 60) flagOnce(out, name + ': at the bottom the elbow is only ' + drop.toFixed(0) + ' units below the shoulder (cue: elbows down to the ribs; needs 60)'); }
    });
    if (inSet && ph.id === 'end-range' && lim.chest) {
      var front = -Infinity, inv = new THREE.Matrix4().copy(fig.bone.chest.matrixWorld).invert(), bl = bar.clone().applyMatrix4(inv), q2 = new V3m();
      skinScan(fig, ['chest'], function (q) { q2.copy(q).applyMatrix4(inv); if (Math.abs(q2.x) < 40 && Math.abs(q2.y - bl.y) < 10 && q2.z > front) front = q2.z; });
      var gap = bl.z - 6 - front; range(out, 'chestGap', gap); out.chestGapMin = out.chestGap[0]; out.chestGapMax = out.chestGap[1];
      if (gap < -2 || gap > 12) flagOnce(out, name + ': at the bottom the bar is ' + gap.toFixed(1) + ' units from the upper chest (cue: bar to the upper chest; -2..12)');
    }
    // blades first: per rep, the time the depression passes 2 deg and the time the elbow has bent 5 deg past its straight value
    if (inSet && ph.id === 'concentric') {
      var lead = out._lead || Object.defineProperty(out, '_lead', { value: {} })._lead, L = lead[ph.rep] || (lead[ph.rep] = {});
      var ge = v[p + 'geL'] || 0, efl = 180 - T3.jointAngle(fig, 'shL', 'elL', 'handL');
      if (L.e0 === undefined) L.e0 = efl;
      if (L.tDep === undefined && ge < -2) L.tDep = t;
      if (L.tEl === undefined && efl > L.e0 + 5) L.tEl = t;
    }
    if (t >= P.clock.at + P.clock.reps * P.clock.period && !out._fin) {
      Object.defineProperty(out, '_fin', { value: true });
      var worst = -Infinity; Object.keys(out._top || {}).forEach(function (r) { worst = Math.max(worst, out._top[r]); });
      out.straightArmsWorstRep = worst;
      if (lim.straight !== null && worst > lim.straight) flagOnce(out, name + ': a rep only returns to ' + worst.toFixed(0) + ' deg of elbow bend (cue: straight arms at the top; max ' + lim.straight + ')');
      var lead2 = Infinity; Object.keys(out._lead || {}).forEach(function (r) { var L = out._lead[r]; lead2 = Math.min(lead2, (L.tEl === undefined ? Infinity : L.tEl) - (L.tDep === undefined ? Infinity : L.tDep)); });
      out.bladeLeadS = lead2;
      if (lim.lead && !(lead2 >= 0.15)) flagOnce(out, name + ': the shoulder blades do not lead the elbows (' + (isFinite(lead2) ? lead2.toFixed(2) : 'no depression') + ' s; cue: blades down first; needs 0.15)');
    }
    tempoRule(out, P.def, P.clock.period, name);
  }
  function pulldownChecks(fig, v, t, out, lim) {
    lim = merge({ trunk: 3, straight: 20, lead: true, chest: true, front: true, swing: null }, lim || {});
    var P = fig.pull, name = 'lat pulldown';
    pullChecks(fig, v, t, out, name, lim);
    var ta = trunkAngle(fig); range(out, 'trunk', ta); out.trunkMove = out.trunk[1] - out.trunk[0];
    if (lim.trunk !== null && out.trunkMove > lim.trunk) flagOnce(out, name + ': the trunk rocks ' + out.trunkMove.toFixed(1) + ' deg (cue: trunk nearly still; max ' + lim.trunk + ')');
    var g = T3.skinLow(fig, ['hips', 'thL', 'thR'], function (q) { return q.z < P.kneeZ - P.cfg.seatGap; }).y - P.seatTop;
    range(out, 'seatGap', g); out.seatGapMin = out.seatGap[0]; out.seatGapMax = out.seatGap[1];
    if (g < -4 || g > 2) flagOnce(out, name + ': the glutes are ' + g.toFixed(1) + ' units off the seat (-4..2)');
    var x0 = fig.root.position.x || 0, lg = rollerGap(fig, ['thL', 'thR'], P.lap.C, P.lap.r, x0 - 95, x0 + 95);
    range(out, 'lapGap', lg); out.lapGapMin = out.lapGap[0]; out.lapGapMax = out.lapGap[1];
    if (lg < -2.5 || lg > 3) flagOnce(out, name + ': the thigh pad is ' + lg.toFixed(1) + ' units off the thighs (thighs locked under the pad: -2.5..3)');
    var cab = P.bar.position.clone().sub(P.P1), plumb = Math.atan2(Math.hypot(cab.x, cab.z), -cab.y) / D2R;
    out.cableTilt = Math.max(out.cableTilt || 0, plumb);
    if (lim.swing === null && plumb > 6) flagOnce(out, name + ': the cable leans ' + plumb.toFixed(1) + ' deg off plumb (the bar path is not under the pulley; max 6)');
    if (lim.swing !== null && t >= P.clock.at + P.clock.reps * P.clock.period && !out._sw) {
      Object.defineProperty(out, '_sw', { value: true });
      if (out.trunkMove < lim.swing) flagOnce(out, 'swing-back variant: the trunk rocks only ' + out.trunkMove.toFixed(1) + ' deg (the mistake is not visible; needs ' + lim.swing + ')');
    }
  }
  T3.pulldownChecks = pulldownChecks;
  var PULLDOWN_PHASES = [{ id: 'start', kind: 'hold', label: 'Arms straight', a: 0, b: 0.04, cue: 'Thighs locked, chest up' }, { id: 'concentric', kind: 'up', label: 'Pull', a: 0.04, b: 0.40, cue: 'Blades down, then elbows to the ribs' },
    { id: 'end-range', kind: 'hold', label: 'Bar to chest', a: 0.40, b: 0.48, cue: 'Bar to the upper chest' }, { id: 'eccentric', kind: 'down', label: 'Return', a: 0.48, b: 0.94, cue: 'Return to straight arms' },
    { id: 'reset', kind: 'hold', label: 'Arms straight', a: 0.94, b: 1.0, cue: '' }];
  var PULL_RHYTHM = { down: [0.04, 0.40], up: [0.48, 0.94], downEase: 'power2.inOut', upEase: 'sine.inOut' };
  var PULLDOWN = merge(PULL, { pitch: -8, lean: -6, hipY: 262, fx: 72, footZ: 160, seatGap: 34, lapBack: 46, barHalf: 300, stackX: 300, stackZ: 330, pulleyUp: 150, swing: 0 });
  X3['lat-pulldown'] = {
    id: 'lat-pulldown', name: 'Lat pulldown (cable)', knowledge: 'lat-pulldown', period: 3.6, phaseMap: PULLDOWN_PHASES, rhythm: PULL_RHYTHM,
    acts: { lat: 3, biceps: 2, brach: 2, trap: 2, 'delt-rear': 2, triceps: 1, flexor: 1 }, peaks: { lat: 1, biceps: 0.6, brach: 0.5, trap: 0.5, 'delt-rear': 0.5, triceps: 0.3, flexor: 0.4 },
    shots: { back: { az: 180, el: 10 }, backThree: { az: 145, el: 16 }, side: { az: 90, el: 6 }, three: { az: 35, el: 10 } },
    build: function (stage, fig, m, o) { return buildPulldown(X3['lat-pulldown'], stage, fig, m, o, merge(PULLDOWN, {})); },
    camera: { target: { tx: 0, ty: 560, tz: 0 }, dist: 2300, fov: 26 },
    checks: function (fig, v, t, out) { pulldownChecks(fig, v, t, out, {}); }
  };
  X3['lat-pulldown-swing'] = {
    id: 'lat-pulldown-swing', name: 'Lat pulldown, swinging the trunk back (mistake)', knowledge: 'lat-pulldown', mistake: 'swing-back', period: 3.6, phaseMap: PULLDOWN_PHASES, rhythm: PULL_RHYTHM,
    acts: X3['lat-pulldown'].acts, peaks: X3['lat-pulldown'].peaks, shots: X3['lat-pulldown'].shots,
    build: function (stage, fig, m, o) { return buildPulldown(X3['lat-pulldown-swing'], stage, fig, m, o, merge(PULLDOWN, { swing: 24 })); },
    camera: X3['lat-pulldown'].camera,
    checks: function (fig, v, t, out) { pulldownChecks(fig, v, t, out, { trunk: null, chest: false, swing: 15 }); }
  };

  /*
   * PULL-UP: the same arm path, the bar fixed on a frame and the BODY moving. Balance solves the body: for each of 9 samples of e the
   * figure is posed at the origin, its fists and a centre of mass (weighted bone positions: pelvis and thighs, chest and arms, head,
   * knees, ankles) are measured, and the root pitch that puts the centre of mass straight under the bar is exact for a rigid rotation
   * (tan p = -dz / dy); two passes (the hand roll that keeps the bar along x depends a little on the pitch). The root then follows
   * from the fists (root = bar - fists), interpolated between the samples (Catmull-Rom), so the fists stay on the bar and the body
   * hangs under it: no swing unless a mistake asks for one. Legs hang slightly bent (FK). cfg.bottomE > 0 is the short-range mistake:
   * the reps turn round at e = bottomE (half-bent arms), never reaching a full hang.
   */
  var COM_W = [['hips', 0.42], ['chest', 0.30], ['head', 0.08], ['knL', 0.05], ['knR', 0.05], ['anL', 0.05], ['anR', 0.05]];
  function comOf(fig) { var c = new V3m(); COM_W.forEach(function (w) { c.addScaledVector(fig.world(w[0]), w[1]); }); return c; }
  T3.comOf = comOf;
  function buildPullup(def, stage, fig, m, o, cfg) {
    o = o || {};
    var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 3, per = o.period || def.period || 3.6, x0 = o.x || 0, z0 = o.z || 0, S = armSpec(fig);
    fig.roles(def.acts);
    var held = fig.supports ? fig.supports.splice(0) : [];
    var upC = worldToChest(new V3m(0, 1, 0), cfg.lean), legs = {};
    ['L', 'R'].forEach(function (sd) { legs['ikLeg' + sd] = 0; legs['hp' + sd] = cfg.hip; legs['ha' + sd] = 3; legs['kn' + sd] = cfg.knee; legs['an' + sd] = cfg.ankle; });
    function body0(pitch, e) { var k = merge(legs, { x: 0, y: 0, z: 0, pitch: pitch, lean: cfg.lean, neckF: -0.5 * (pitch + cfg.lean) - 6 * smooth(e), headF: -8 * smooth(e), gaxL: 1, gaxR: 1, garL: 60, garR: -60, wrL: 0, wrR: 0 }); return k; }
    var B = calibratePullBottom(fig, S, cfg, function (Bt) { return pref(p, merge(body0(0, 1), pullArms(S, pullPath(S, cfg, upC, Bt).at(1)))); });
    var path = pullPath(S, cfg, upC, B), N = 12, SAMP = [];
    // wrist of side L relative to the root, from the trunk chain (spine 70 above the root, chest 80 above the spine; lean split 0.4 / 0.6)
    function wristRel(th, W) {
      var c = new V3m(0, 80, 0).applyAxisAngle(new V3m(1, 0, 0), 0.4 * cfg.lean * D2R).add(new V3m(0, 70, 0));
      return c.add(W.clone().applyAxisAngle(new V3m(1, 0, 0), cfg.lean * D2R)).applyAxisAngle(new V3m(1, 0, 0), th * D2R);
    }
    function wristMid(th, e) { var q = path.at(e); return wristRel(th, q.L.W).add(wristRel(th, q.R.W)).multiplyScalar(0.5); }
    for (var i = 0; i <= N; i++) {
      var e = i / N, arms = pullArms(S, path.at(e)), th = 0, F, C;
      for (var pass = 0; pass < 2; pass++) {
        fig.apply(pref(p, merge(body0(th, e), arms)));
        F = fistPoint(fig, 'L').add(fistPoint(fig, 'R')).multiplyScalar(0.5); C = comOf(fig);
        // F and C are root-frame points rotated by the current pitch th: undo it, then solve the pitch that stacks C under F
        var r = function (v) { var c = Math.cos(-th * D2R), s = Math.sin(-th * D2R); return [v.y * c - v.z * s, v.y * s + v.z * c]; };
        var f0 = r(F), c0 = r(C);
        th = Math.atan(-(c0[1] - f0[1]) / (c0[0] - f0[0])) / D2R;
      }
      fig.apply(pref(p, merge(body0(th, e), arms)));
      // only the small hand offset (fist minus the analytic wrist) is interpolated: the 240-unit arm is exact at every frame
      F = fistPoint(fig, 'L').add(fistPoint(fig, 'R')).multiplyScalar(0.5).sub(wristMid(th, e));
      SAMP.push({ th: th, fy: F.y, fz: F.z, fx: F.x });
    }
    function cr(k, x) {                                                // Catmull-Rom through the samples of field k at e = x
      var u = Math.max(0, Math.min(1, x)) * N, j = Math.min(N - 1, Math.floor(u)), f = u - j;
      var a = SAMP[Math.max(0, j - 1)][k], b = SAMP[j][k], c = SAMP[j + 1][k], d = SAMP[Math.min(N, j + 2)][k];
      return 0.5 * ((2 * b) + (-a + c) * f + (2 * a - 5 * b + 4 * c - d) * f * f + (-a + 3 * b - 3 * c + d) * f * f * f);
    }
    // the bar: high enough that the soles clear the floor by cfg.floorGap at the full hang
    fig.apply(pref(p, merge(body0(SAMP[0].th, 0), pullArms(S, path.at(0)))));
    var c0 = T3.contacts(fig), lowSole = Math.min(c0.soleL, c0.soleR, T3.skinLow(fig, ['anL', 'anR', 'knL', 'knR']).y);
    var barY = cfg.floorGap - (lowSole - (SAMP[0].fy + wristMid(SAMP[0].th, 0).y)), barZ = z0, half = S.shx * cfg.grip + 120;
    function keys(s) {
      var e = lerp(cfg.bottomE, 1, s), th = cr('th', e), k = merge(body0(th, e), pullArms(S, path.at(e))), w = wristMid(th, e);
      k.x = x0 - cr('fx', e) - w.x; k.y = barY - cr('fy', e) - w.y; k.z = barZ - cr('fz', e) - w.z;
      return pref(p, k);
    }
    var frame = new THREE.Group(), steelS = T3.colors.steelShade, bar = rod(6, T3.colors.steel);
    setRod(bar, new V3m(x0 - half, barY, barZ), new V3m(x0 + half, barY, barZ)); frame.add(bar);
    [-1, 1].forEach(function (sg) {
      var post = box(22, barY + 40, 22, steelS); post.position.set(x0 + sg * (half + 11), (barY + 40) / 2, barZ); frame.add(post);
      var foot = box(30, 12, 300, steelS); foot.position.set(x0 + sg * (half + 11), 6, barZ); frame.add(foot);
      var cap = box(30, 14, 34, steelS); cap.position.set(x0 + sg * (half + 11), barY + 40, barZ); frame.add(cap);
    });
    addProp(stage, fig, frame);
    if (fig.supports) Array.prototype.push.apply(fig.supports, held);
    fig.apply({});
    m.base(keys(0));
    var end = reps(m, at, per, n, keys, def.rhythm);
    envelope(m, p, o.peaks || def.peaks, at, per, n);
    fig.pose = keys;
    fig.pull = { def: def, clock: { at: at, period: per, reps: n }, cfg: cfg, bar: { position: new V3m(x0, barY, barZ), quaternion: new THREE.Quaternion() }, barY: barY, barZ: barZ, path: path, frame: frame };
    return end;
  }
  /*
   * Pull-up checks on top of pullChecks: the fists stay on the bar (within 2.5 units of its axis); the centre of mass stays under the
   * bar (within 6 units fore-aft: no swing); every rep starts from a full hang (in pullChecks: straight arms) and the chin clears the
   * bar at the top (the lowest chin skin above the bar's top); the feet never come within 20 units of the floor.
   */
  function pullupChecks(fig, v, t, out, lim) {
    lim = merge({ straight: 20, lead: true, chest: true, front: true, chin: true, range: null }, lim || {});
    var P = fig.pull, ph = T3.phaseAt(P.def, P.clock, t), inSet = ph.rep >= 1 && ph.rep <= P.clock.reps, name = 'pull-up';
    pullChecks(fig, v, t, out, name, lim);
    ['L', 'R'].forEach(function (s) {
      var f = fistPoint(fig, s), d = Math.hypot(f.y - P.barY, f.z - P.barZ);
      out.fistOffBar = Math.max(out.fistOffBar || 0, d);
      if (d > 2.5) flagOnce(out, name + ': a hand is ' + d.toFixed(1) + ' units off the bar (max 2.5)');
    });
    var c = comOf(fig), dz = c.z - P.barZ; range(out, 'comUnderBar', dz); out.comSwing = Math.max(Math.abs(out.comUnderBar[0]), Math.abs(out.comUnderBar[1]));
    if (out.comSwing > 6) flagOnce(out, name + ': the centre of mass swings ' + out.comSwing.toFixed(1) + ' units from under the bar (max 6)');
    var cc = T3.contacts(fig), low = Math.min(cc.soleL, cc.soleR);
    out.feetAboveFloor = Math.min(out.feetAboveFloor === undefined ? Infinity : out.feetAboveFloor, low);
    if (low < 20) flagOnce(out, name + ': the feet come within ' + low.toFixed(1) + ' units of the floor (min 20)');
    if (inSet && ph.id === 'end-range') {
      var hf = fig.bone.head.matrixWorld, inv = new THREE.Matrix4().copy(hf).invert(), chin = Infinity, q = new V3m();
      skinScan(fig, ['head'], function (w) { q.copy(w).applyMatrix4(inv); if (q.z > 20 && Math.abs(q.x) < 25 && w.y < chin) chin = w.y; });
      var over = chin - (P.barY + 6); range(out, 'chinOverBar', over); out.chinOverBarMin = out.chinOverBar[0];
      if (lim.chin && over < 0) flagOnce(out, name + ': at the top the chin is ' + (-over).toFixed(1) + ' units below the bar (cue: chin clears the bar)');
    }
    if (lim.range !== null && t >= P.clock.at + P.clock.reps * P.clock.period && !out._rg) {
      Object.defineProperty(out, '_rg', { value: true });
      if ((out.straightArmsWorstRep || 0) < lim.range) flagOnce(out, 'short-range variant: the arms straighten to ' + (out.straightArmsWorstRep || 0).toFixed(0) + ' deg at the bottom (the mistake is not visible; needs ' + lim.range + ')');
    }
  }
  T3.pullupChecks = pullupChecks;
  var PULLUP_PHASES = [{ id: 'start', kind: 'hold', label: 'Dead hang', a: 0, b: 0.06, cue: 'Blades gently down' }, { id: 'concentric', kind: 'up', label: 'Pull', a: 0.06, b: 0.42, cue: 'Elbows down to the ribs' },
    { id: 'end-range', kind: 'hold', label: 'Chin over the bar', a: 0.42, b: 0.52, cue: 'Chin clears the bar' }, { id: 'eccentric', kind: 'down', label: 'Lower', a: 0.52, b: 0.94, cue: 'Lower to a full hang' },
    { id: 'reset', kind: 'hold', label: 'Dead hang', a: 0.94, b: 1.0, cue: '' }];
  var PULLUP = merge(PULL, { lean: -10, hip: 12, knee: 34, ankle: 22, floorGap: 60, bottomE: 0, depress: -6 });
  X3['pull-up'] = {
    id: 'pull-up', name: 'Pull-up', knowledge: 'pull-up', period: 3.6, phaseMap: PULLUP_PHASES, rhythm: { down: [0.06, 0.42], up: [0.52, 0.94], downEase: 'power2.inOut', upEase: 'sine.inOut' },
    acts: { lat: 3, biceps: 3, brach: 3, trap: 2, 'delt-rear': 2, flexor: 1 }, peaks: { lat: 1, biceps: 0.8, brach: 0.7, trap: 0.5, 'delt-rear': 0.5, flexor: 0.5 },
    // side: az 90 looks along the bar and the near post covers the body (rule 12): az 70
    shots: { back: { az: 180, el: 8 }, backThree: { az: 145, el: 12 }, side: { az: 70, el: 4 }, three: { az: 35, el: 8 } },
    build: function (stage, fig, m, o) { return buildPullup(X3['pull-up'], stage, fig, m, o, merge(PULLUP, {})); },
    camera: { target: { tx: 0, ty: 760, tz: 0 }, dist: 2600, fov: 26 },
    checks: function (fig, v, t, out) { pullupChecks(fig, v, t, out, {}); }
  };
  X3['pull-up-short'] = {
    id: 'pull-up-short', name: 'Pull-up, cutting the range short (mistake)', knowledge: 'pull-up', mistake: 'short-range', period: 3.6, phaseMap: PULLUP_PHASES, rhythm: X3['pull-up'].rhythm,
    acts: X3['pull-up'].acts, peaks: X3['pull-up'].peaks, shots: X3['pull-up'].shots,
    build: function (stage, fig, m, o) { return buildPullup(X3['pull-up-short'], stage, fig, m, o, merge(PULLUP, { bottomE: 0.5 })); },
    camera: X3['pull-up'].camera,
    checks: function (fig, v, t, out) { pullupChecks(fig, v, t, out, { straight: null, lead: false, range: 40 }); }
  };

  // ---------------------------------------------------------------- seated cable row
  /*
   * Seated on a low row bench, feet on an angled foot plate, knees soft (direct-angle legs solved so the ankles sit exactly where the
   * soles meet the plate: T3.legFK; the plate is built in the ankle's own frame, so it lies flat on the soles). Trunk upright and still.
   * A neutral-grip V-handle (grips vertical: gayS) on a horizontal cable. One parameter s (0 = the reach, 1 = the squeeze): the wrists run
   * on a straight horizontal line from the reach, soft-straight from the MOVED joint (cfg.reach) with the blades protracted (gpS
   * cfg.protract: "let the shoulder blades reach forward"), to the end, calibrated on the skin so the handle sits cfg.ribGap in front of
   * the lower ribs, with the blades retracted (gpS cfg.retract) and no shrug. Elbows close to the trunk (pole down and back). The handle is
   * posed from the fists after every fig.apply; the cable runs level to a pulley post in front of the plate, up and over to a stack whose
   * plates rise by the handle's travel. cfg.rock > 0 is the trunk-rock mistake: the trunk leans forward at the reach and back at the end.
   */
  var CROW = { hipY: 250, legBend: 24, ankleDrop: 44, footPitch: -68, handX: 22, handleY: -52, ribGap: 8, reach: 238, protract: 10, retract: -15, rock: 0, seatGap: 30 };
  function buildCableRow(def, stage, fig, m, o, cfg) {
    o = o || {};
    var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 3, per = o.period || def.period || 3.6, x0 = o.x || 0, z0 = o.z || 0, S = armSpec(fig);
    fig.roles(def.acts);
    var held = fig.supports ? fig.supports.splice(0) : [];
    // ankles: in front of the hips, legBend deg of knee flexion, ankleDrop below the hip joint
    var L1 = 178, L2 = 166, dHA = Math.sqrt(L1 * L1 + L2 * L2 + 2 * L1 * L2 * Math.cos(cfg.legBend * D2R));
    var hipJ = cfg.hipY - 6, aY = hipJ - cfg.ankleDrop, aZ = z0 + Math.sqrt(dHA * dHA - cfg.ankleDrop * cfg.ankleDrop);
    var ank = { L: new V3m(x0 + 52, aY, aZ), R: new V3m(x0 - 52, aY, aZ) };
    function trunk(s) { var r = cfg.rock ? cfg.rock * (0.55 - smooth(s)) : 0; return { pitch: r, lean: 0 }; }
    var pole = {}; ['L', 'R'].forEach(function (sd) { pole[sd] = new V3m((sd === 'L' ? 1 : -1) * 0.3, -1, -0.45).normalize(); });
    var Wend = { L: new V3m(cfg.handX, cfg.handleY, 70), R: new V3m(-cfg.handX, cfg.handleY, 70) }, zReach = 200;
    function reachZ(sd) {
      var lo = Wend[sd].z, hi = Wend[sd].z + 400;
      for (var i = 0; i < 40; i++) { var mid = (lo + hi) / 2, W = new V3m(Wend[sd].x, Wend[sd].y, mid); if (W.distanceTo(girdleJoint(S, sd, W, pole[sd], cfg.protract, 0).J) > cfg.reach) hi = mid; else lo = mid; }
      return (lo + hi) / 2;
    }
    function body(s) {
      var tr = trunk(s), R = { x: x0, y: cfg.hipY, z: z0, pitch: tr.pitch, yaw: 0, roll: 0 };
      var k = merge({ x: x0, y: cfg.hipY, z: z0, pitch: tr.pitch, lean: tr.lean, neckF: -0.8 * tr.pitch, headF: -0.2 * tr.pitch, gayL: 1, gayR: 1, garL: -90, garR: 90, wrL: 0, wrR: 0 }, legKeys(R, ank, cfg.footPitch));
      return k;
    }
    function arms(s) {
      var k = {}, gp = lerp(cfg.protract, cfg.retract, smooth(s));
      ['L', 'R'].forEach(function (sd) { var W = new V3m(Wend[sd].x, Wend[sd].y, lerp(zReach, Wend[sd].z, s)); merge2(k, chestArm(S, sd, W, pole[sd], gp, 0)); });
      return k;
    }
    function keys(s) { return pref(p, merge(body(s), arms(s))); }
    // the end point: the handle (between the fists) ribGap in front of the lower-rib skin at its own height
    for (var pass = 0; pass < 4; pass++) {
      zReach = reachZ('L');
      fig.apply(keys(1));
      var Fm = fistsInChest(fig), front = -Infinity, inv = new THREE.Matrix4().copy(fig.bone.chest.matrixWorld).invert(), q = new V3m();
      skinScan(fig, ['chest', 'spine'], function (v) { q.copy(v).applyMatrix4(inv); if (Math.abs(q.x) < 40 && Math.abs(q.y - Fm.y) < 10 && q.z > front) front = q.z; });
      var dz = (front + cfg.ribGap) - Fm.z, dy = cfg.handleY - Fm.y;
      ['L', 'R'].forEach(function (sd) { Wend[sd].z += dz; Wend[sd].y += dy; });
    }
    zReach = reachZ('L');
    var handle = new THREE.Group(), grips = [rod(6, T3.colors.pad), rod(6, T3.colors.pad)], vL = rod(4.5, T3.colors.steel), vR = rod(4.5, T3.colors.steel);
    grips.forEach(function (g) { handle.add(g); }); handle.add(vL); handle.add(vR); addProp(stage, fig, handle);
    function handAxis(sd) { return new V3m(1, 0, 0).transformDirection(fig.bone['hand' + sd].matrixWorld); }
    function poseHandle() {
      var F = [fistPoint(fig, 'L'), fistPoint(fig, 'R')], apex = F[0].clone().add(F[1]).multiplyScalar(0.5).add(new V3m(0, 0, 70));
      [0, 1].forEach(function (i) { var ax = handAxis(i ? 'R' : 'L'); setRod(grips[i], F[i].clone().addScaledVector(ax, -26), F[i].clone().addScaledVector(ax, 26)); });
      setRod(vL, F[0], apex); setRod(vR, F[1], apex);
      handle.userData.apex = apex; handle.updateMatrixWorld(true);
      return apex;
    }
    // bench, foot plate and the machine, from the posed body at the reach
    fig.apply(keys(0));
    var A0 = poseHandle().clone(), seat = seatFromSkin(fig, 0, function (z) { return z < z0 + 120; });
    var mach = new THREE.Group(), steelS = T3.colors.steelShade;
    var seatBack = seat.zBack - 30, seatFront = z0 + 150, sp = box(170, 34, seatFront - seatBack, T3.colors.pad); sp.position.set(x0, seat.top - 17, (seatFront + seatBack) / 2); mach.add(sp);
    var sc = box(156, 6, seatFront - seatBack - 14, T3.colors.padTop); sc.position.set(x0, seat.top - 2, sp.position.z); mach.add(sc);
    var beamEnd = aZ + 60, beam = box(60, 40, beamEnd - seatBack, steelS); beam.position.set(x0, 20, (beamEnd + seatBack) / 2); mach.add(beam);
    var leg = box(40, seat.top - 34 - 40, 40, steelS); leg.position.set(x0, 40 + (seat.top - 74) / 2, sp.position.z); mach.add(leg);
    // the foot plate in the left ankle's frame: its face on the soles (ankle-frame y = -26), wide enough for both feet
    fig.bone.anL.updateWorldMatrix(true, false);
    var plate = box(220, 10, 190, T3.colors.steel), qA = new THREE.Quaternion().setFromRotationMatrix(fig.bone.anL.matrixWorld);
    plate.quaternion.copy(qA); plate.position.copy(new V3m(0, -31, 30).applyMatrix4(fig.bone.anL.matrixWorld)); plate.position.x = x0; mach.add(plate);
    var plateStrut = rod(8, steelS); setRod(plateStrut, plate.position.clone().add(new V3m(0, 0, 40)), new V3m(x0, 40, plate.position.z + 60)); mach.add(plateStrut);
    var zPost = Math.max(A0.z, aZ + 120) + 160, Pp = new V3m(x0, A0.y, zPost), Pt = new V3m(x0, A0.y + 520, zPost), zs = zPost + 110;
    var post = box(40, Pt.y + 40, 40, steelS); post.position.set(x0, (Pt.y + 40) / 2, zPost + 24); mach.add(post);
    var pulA = disc(16, 12, T3.colors.steel); pulA.position.copy(Pp); mach.add(pulA);
    var pulB = disc(16, 12, T3.colors.steel); pulB.position.copy(Pt); mach.add(pulB);
    var stack = EQ.stack({ x: x0, z: zs, n: 12, moving: 5, frameH: Pt.y + 30 }); mach.add(stack);
    var Ps = new V3m(x0, Pt.y, zs), pulC = disc(16, 12, T3.colors.steel); pulC.position.copy(Ps); mach.add(pulC);
    var top = box(40, 24, zs - zPost + 40, steelS); top.position.set(x0, Pt.y + 26, (zs + zPost) / 2); mach.add(top);
    var cA = rod(1.6, steelS), cB = rod(1.6, steelS), cC = rod(1.6, steelS), cD = rod(1.6, steelS); [cA, cB, cC, cD].forEach(function (c) { mach.add(c); });
    addProp(stage, fig, mach);
    function poseMachine() {
      var apex = poseHandle(), rise = Math.max(0, A0.z - apex.z);
      stack.userData.stack.set(rise);
      setRod(cA, apex, Pp); setRod(cB, Pp, Pt); setRod(cC, Pt, Ps); setRod(cD, Ps, stack.userData.stack.top(rise));
    }
    afterApply(fig, function () { poseMachine(); });
    if (fig.supports) Array.prototype.push.apply(fig.supports, held);
    fig.apply({});
    m.base(keys(0));
    var end = reps(m, at, per, n, keys, def.rhythm);
    envelope(m, p, o.peaks || def.peaks, at, per, n);
    fig.pose = keys;
    fig.row = { def: def, clock: { at: at, period: per, reps: n }, cfg: cfg, handle: handle, seatTop: seat.top, plate: plate, A0: A0, pulley: Pp };
    return end;
  }
  /** World position of side sd's REST glenohumeral joint (the chest frame's ghRest), for blade travel. */
  function restJointW(fig, sd) { return ghRest(fig.spec, sd).applyMatrix4(fig.bone.chest.matrixWorld); }
  T3.restJointW = restJointW;
  /*
   * Cable row checks (exercises.json cue_checks): the trunk still (within 3 deg); the handle path within 10 deg of horizontal; the
   * elbows close (at most 30 units outside the shoulder joints); at the squeeze the blades retracted (the joint at least 6 units behind
   * its rest place) and never shrugged (at most 3 above it); arms long at the reach (elbows within 20 deg of straight); the handle to the
   * lower ribs (0-20 units in front of the skin); glutes on the seat and soles on the plate; a slower return than pull.
   */
  function cableRowChecks(fig, v, t, out, lim) {
    lim = merge({ trunk: 3, rock: null }, lim || {});
    var R = fig.row, ph = T3.phaseAt(R.def, R.clock, t), inSet = ph.rep >= 1 && ph.rep <= R.clock.reps, name = 'seated cable row', apex = R.handle.userData.apex;
    var ta = trunkAngle(fig); range(out, 'trunk', ta); out.trunkMove = out.trunk[1] - out.trunk[0];
    if (lim.trunk !== null && out.trunkMove > lim.trunk) flagOnce(out, name + ': the trunk rocks ' + out.trunkMove.toFixed(1) + ' deg (cue: trunk still; max ' + lim.trunk + ')');
    range(out, 'handleY', apex.y); range(out, 'handleZ', apex.z);
    if (t >= R.clock.at + R.clock.reps * R.clock.period && !out._hs) {
      Object.defineProperty(out, '_hs', { value: true });
      var slope = Math.atan2(out.handleY[1] - out.handleY[0], Math.max(1, out.handleZ[1] - out.handleZ[0])) / D2R; out.handleSlope = slope;
      if (lim.rock === null && slope > 10) flagOnce(out, name + ': the handle path is ' + slope.toFixed(0) + ' deg off horizontal (max 10)');
    }
    ['L', 'R'].forEach(function (s) {
      var e = fig.world('el' + s), J = jointW(fig, s), J0 = restJointW(fig, s), x0 = fig.root.position.x || 0, wide = Math.abs(e.x - x0) - Math.abs(J.x - x0);
      out.elbowOut = Math.max(out.elbowOut || -Infinity, wide);
      if (wide > 30) flagOnce(out, name + ': the elbow flares ' + wide.toFixed(0) + ' units outside the shoulder (cue: elbows close; max 30)');
      var up = J.y - J0.y; out.shrug = Math.max(out.shrug || -Infinity, up);
      if (up > 3) flagOnce(out, name + ': the shoulder rises ' + up.toFixed(1) + ' units (cue: blades back and down, not up; max 3)');
      if (inSet && ph.id === 'end-range') { var back = J0.z - J.z; range(out, 'retraction', back); out.retractionMin = out.retraction[0];
        if (back < 6) flagOnce(out, name + ': at the squeeze the blade is only ' + back.toFixed(1) + ' units back (cue: shoulder blades together; needs 6)'); }
      if (inSet && (ph.id === 'start' || ph.id === 'reset')) { var ef = 180 - T3.jointAngle(fig, 'sh' + s, 'el' + s, 'hand' + s); range(out, 'reachElbow', ef); out.reachElbowMax = out.reachElbow[1];
        if (ef > 20) flagOnce(out, name + ': at the reach the elbow is bent ' + ef.toFixed(0) + ' deg (arms long; max 20)'); }
    });
    if (inSet && ph.id === 'end-range') {
      var inv = new THREE.Matrix4().copy(fig.bone.chest.matrixWorld).invert(), F = fistsInChest(fig), front = -Infinity, q = new V3m();
      skinScan(fig, ['chest', 'spine'], function (w) { q.copy(w).applyMatrix4(inv); if (Math.abs(q.x) < 40 && Math.abs(q.y - F.y) < 10 && q.z > front) front = q.z; });
      var gap = F.z - front; range(out, 'ribGap', gap); out.ribGapMin = out.ribGap[0]; out.ribGapMax = out.ribGap[1];
      if (gap < 0 || gap > 20) flagOnce(out, name + ': at the squeeze the handle is ' + gap.toFixed(1) + ' units from the ribs (cue: to the lower ribs; 0-20)');
    }
    var g = T3.skinLow(fig, ['hips', 'thL', 'thR'], function (q2) { return q2.z < (fig.root.position.z || 0) + 120; }).y - R.seatTop;
    range(out, 'seatGap', g); out.seatGapMin = out.seatGap[0]; out.seatGapMax = out.seatGap[1];
    if (g < -4 || g > 2) flagOnce(out, name + ': the glutes are ' + g.toFixed(1) + ' units off the seat (-4..2)');
    // soles on the plate: heel and ball of both feet within 2 units of the plate face (plate centre 5 under its face, along its normal)
    var nP = new V3m(0, 1, 0).applyQuaternion(R.plate.quaternion), face = R.plate.position.clone().addScaledVector(nP, 5), c = T3.contacts(fig), worst = 0;
    ['L', 'R'].forEach(function (s) {
      var a = fig.bone['an' + s]; a.updateWorldMatrix(true, false);
      [T3.HEEL, T3.BALL].forEach(function (pt) { var w = new V3m(0, pt.y, pt.z).applyMatrix4(a.matrixWorld), d = w.sub(face).dot(nP); if (Math.abs(d) > Math.abs(worst)) worst = d; });
    });
    out.soleToPlate = Math.max(out.soleToPlate || 0, Math.abs(worst));
    if (Math.abs(worst) > 2) flagOnce(out, name + ': a sole is ' + worst.toFixed(1) + ' units off the foot plate (max 2)');
    tempoRule(out, R.def, R.clock.period, name);
    if (lim.rock !== null && t >= R.clock.at + R.clock.reps * R.clock.period && !out._rk) {
      Object.defineProperty(out, '_rk', { value: true });
      if (out.trunkMove < lim.rock) flagOnce(out, 'trunk-rock variant: the trunk rocks only ' + out.trunkMove.toFixed(1) + ' deg (the mistake is not visible; needs ' + lim.rock + ')');
    }
  }
  T3.cableRowChecks = cableRowChecks;
  var CROW_PHASES = [{ id: 'start', kind: 'hold', label: 'Reach', a: 0, b: 0.04, cue: 'Sit tall, knees soft' }, { id: 'concentric', kind: 'up', label: 'Row', a: 0.04, b: 0.38, cue: 'Handle to the lower ribs, elbows close' },
    { id: 'end-range', kind: 'hold', label: 'Squeeze', a: 0.38, b: 0.48, cue: 'Shoulder blades together' }, { id: 'eccentric', kind: 'down', label: 'Reach', a: 0.48, b: 0.94, cue: 'Reach forward under control' },
    { id: 'reset', kind: 'hold', label: 'Reach', a: 0.94, b: 1.0, cue: '' }];
  var ROW_RHYTHM = { down: [0.04, 0.38], up: [0.48, 0.94], downEase: 'power2.inOut', upEase: 'sine.inOut' };
  X3['seated-cable-row'] = {
    id: 'seated-cable-row', name: 'Seated cable row', knowledge: 'seated-cable-row', period: 3.6, phaseMap: CROW_PHASES, rhythm: ROW_RHYTHM,
    acts: { lat: 3, trap: 3, 'delt-rear': 2, biceps: 2, brach: 2, erector: 1, flexor: 1 }, peaks: { lat: 1, trap: 0.85, 'delt-rear': 0.6, biceps: 0.55, brach: 0.45, erector: 0.35, flexor: 0.4 },
    shots: { side: { az: 90, el: 8 }, three: { az: 125, el: 14 }, back: { az: 180, el: 14 }, high: { az: 150, el: 40 } },
    build: function (stage, fig, m, o) { return buildCableRow(X3['seated-cable-row'], stage, fig, m, o, merge(CROW, {})); },
    camera: { target: { tx: 0, ty: 420, tz: 150 }, dist: 2300, fov: 26 },
    checks: function (fig, v, t, out) { cableRowChecks(fig, v, t, out, {}); }
  };
  X3['seated-cable-row-rock'] = {
    id: 'seated-cable-row-rock', name: 'Seated cable row, rocking the trunk (mistake)', knowledge: 'seated-cable-row', mistake: 'trunk-rock', period: 3.6, phaseMap: CROW_PHASES, rhythm: ROW_RHYTHM,
    acts: X3['seated-cable-row'].acts, peaks: X3['seated-cable-row'].peaks, shots: X3['seated-cable-row'].shots,
    build: function (stage, fig, m, o) { return buildCableRow(X3['seated-cable-row-rock'], stage, fig, m, o, merge(CROW, { rock: 28 })); },
    camera: X3['seated-cable-row'].camera,
    checks: function (fig, v, t, out) { cableRowChecks(fig, v, t, out, { trunk: null, rock: 15 }); }
  };

  // ---------------------------------------------------------------- one-arm dumbbell row
  /*
   * Left knee and left hand on a flat bench, right foot on the floor, trunk near horizontal (pelvis pitch cfg.pitch, spine lean cfg.lean)
   * and still; the right arm rows. Contacts are solved on the posed skin: the root height puts the left knee 1 unit into the pad (the
   * thigh hangs straight down from the hip, the shin lies back along the pad: T3.legFK to an ankle just off the bench's end, so the foot
   * hangs clear), and the left wrist height puts the palm 0.5 on the pad (palmFlat from the rest joint, as the rig keeps a planted hand's
   * orientation). The working arm is solved in the chest frame: from a hang straight down (soft-straight from the MOVED joint, blade
   * protracted cfg.protract: "shoulder blade moving with the arm") along a straight line to the wrist beside the lower ribs, cfg.toHip
   * toward the hip ("elbow toward the hip, not straight up") with the blade retracted (cfg.retract). Neutral grip (handle along the trunk:
   * gazS). cfg.twist > 0 is the torso-twist mistake: the trunk twists open toward the working side as the weight comes up; the support
   * hand stays planted (its target follows the twisting shoulder, sampled at 9 points and interpolated).
   */
  var ROW1 = { benchTop: 150, pitch: 78, lean: 10, hipX: 40, footX: -78, footZ: 40, protract: 8, retract: -12, reach: 237, toHip: 70, ribZ: 18, handOut: 20, twist: 0 };
  function buildOneArmRow(def, stage, fig, m, o, cfg) {
    o = o || {};
    var p = fig.id ? fig.id + '.' : '', at = o.at || 0, n = o.reps || 3, per = o.period || def.period || 3.4, x0 = o.x || 0, z0 = o.z || 0, S = armSpec(fig), top = cfg.benchTop;
    fig.roles(def.acts);
    var held = fig.supports ? fig.supports.splice(0) : [];
    var db = EQ.dumbbell(1); fig.hold('R', db);
    var a = cfg.pitch + cfg.lean, rootY = top + 220, ankY = top + 18, kneeZ = z0;
    function trunk(s) { return { pitch: cfg.pitch, lean: cfg.lean, twist: -cfg.twist * smooth(s) }; }
    function legs(s, ry) {
      var tr = trunk(s), R = { x: x0, y: ry, z: z0, pitch: tr.pitch, yaw: 0, roll: 0 };
      var A = new V3m(x0 + cfg.hipX, ankY, kneeZ - 165), k = legKeys(R, { L: A });
      k.anL = 10;
      k.ikLegR = 1; k.fxR = x0 + cfg.footX; k.fzR = z0 + cfg.footZ; k.fyawR = -12; k.kwR = 1;
      return k;
    }
    function bodyKeys(s, ry) { var tr = trunk(s); return merge({ x: x0, y: ry, z: z0, pitch: tr.pitch, lean: tr.lean, twist: tr.twist, neckF: -6, headF: -10, gazR: 1, garR: cfg.garR, wrR: 0 }, legs(s, ry)); }
    // root height: the left knee skin 1 unit into the pad
    for (var it = 0; it < 4; it++) { fig.apply(pref(p, bodyKeys(0, rootY))); rootY += (top - 1) - T3.skinLow(fig, ['knL'], function (v) { return v.z > z0 - 120; }).y; }
    // the support hand: under the shoulder and a little ahead, palm flat on the pad (wrist height solved on the skin)
    fig.apply(pref(p, bodyKeys(0, rootY)));
    var J0 = restJointW(fig, 'L'), Wsup = new V3m(J0.x + 12, top + 16, J0.z + 14), poleS = new V3m(0.5, 0, -1).normalize(), restS = [], NS = 8;
    function supportKeys(rest) {
      var k = { ikL: 1, ikcL: 0, hxL: Wsup.x - rest.x, hyL: Wsup.y - rest.y, hzL: Wsup.z - rest.z, pxL: poleS.x, pyL: poleS.y, pzL: poleS.z, gaxL: 0 };
      return merge2(k, palmFlat('L', rest, Wsup, poleS, 0, palmLow));
    }
    var palmLow;
    for (var i = 0; i <= (cfg.twist ? NS : 0); i++) { fig.apply(pref(p, bodyKeys(i / NS, rootY))); restS.push(restJointW(fig, 'L')); }
    function restAt(s) {
      if (!cfg.twist) return restS[0];
      var u = Math.max(0, Math.min(1, s)) * NS, j = Math.min(NS - 1, Math.floor(u)), f = u - j, r = new V3m();
      ['x', 'y', 'z'].forEach(function (c) { var A = restS[Math.max(0, j - 1)][c], B = restS[j][c], C = restS[j + 1][c], D = restS[Math.min(NS, j + 2)][c];
        r[c] = 0.5 * ((2 * B) + (-A + C) * f + (2 * A - 5 * B + 4 * C - D) * f * f + (-A + 3 * B - 3 * C + D) * f * f * f); });
      return r;
    }
    palmLow = palmFrame(restS[0], Wsup, poleS, 10).low;
    // working arm (right), chest frame: world down for this trunk, the head end is chest +y
    var downC = worldToChest(new V3m(0, -1, 0), a), poleW = new V3m(-0.08, -0.5, -1).normalize();
    var dirB = downC.clone().addScaledVector(new V3m(0, 1, 0), 0.08).normalize(), Wb = reachFromJoint(S, 'R', dirB, cfg.reach, poleW, cfg.protract, 0);
    var Wt = new V3m(-(S.shx + cfg.handOut), S.shy - 150 - cfg.toHip, cfg.ribZ);
    function armR(s) { var W = Wb.clone().lerp(Wt, s); return chestArm(S, 'R', W, poleW, lerp(cfg.protract, cfg.retract, smooth(s)), 0); }
    function keys(s) { return pref(p, merge(bodyKeys(s, rootY), supportKeys(restAt(s)), armR(s))); }
    // wrist height of the planted palm, on the skin (0.5 above the pad), three passes (the palm model's lowest point moves with the wrist)
    for (var pass = 0; pass < 3; pass++) { palmLow = palmFrame(restS[0], Wsup, poleS, 10).low; fig.apply(keys(0)); Wsup.y += (top + 0.5) - T3.skinLow(fig, ['handL']).y; }
    palmLow = palmFrame(restS[0], Wsup, poleS, 10).low;
    fig.apply(keys(0));
    var K = fig.world('knL'), H = fig.world('handL'), zEnd = kneeZ - 165 + 6, zFront = H.z + 70;
    var bench = EQ.bench({ x: x0 + 62, z: (zEnd + zFront) / 2, y: top, w: 130, l: zFront - zEnd }); addProp(stage, fig, bench);
    if (fig.supports) { held.forEach(function (b) { fig.supports.push(b); }); restsOn(fig, bench); }
    fig.apply({});
    m.base(keys(0));
    var end = reps(m, at, per, n, keys, def.rhythm);
    envelope(m, p, o.peaks || def.peaks, at, per, n);
    fig.pose = keys;
    fig.row1 = { def: def, clock: { at: at, period: per, reps: n }, cfg: cfg, bench: bench, top: top, dumbbell: db, hand0: null };
    return end;
  }
  /*
   * One-arm row checks (exercises.json cue_checks): the trunk still (its roll about its long axis and its pitch within 3 deg) and the
   * hips level (within 6 deg); the back flat (the shoulder-hip line within 25 deg of horizontal); the support palm on the pad (-1.5..3) and
   * not sliding (1.5) and the support knee on it (-2.5..3); a full stretch at the bottom (elbow within 20 deg of straight); at the top
   * the elbow driven toward the hip (at least 40 behind the shoulder, not below the trunk's side by more than 30, within 35 of the body
   * line); the dumbbell clear of the floor, the bench and the trunk and legs; a slower lowering than pull.
   */
  function oneArmRowChecks(fig, v, t, out, lim) {
    lim = merge({ roll: 3, twist: null }, lim || {});
    var R = fig.row1, ph = T3.phaseAt(R.def, R.clock, t), inSet = ph.rep >= 1 && ph.rep <= R.clock.reps, name = 'one-arm row';
    var xc = new V3m(1, 0, 0).transformDirection(fig.bone.chest.matrixWorld), xh = new V3m(1, 0, 0).transformDirection(fig.bone.hips.matrixWorld);
    var roll = Math.asin(Math.max(-1, Math.min(1, xc.y))) / D2R, hipRoll = Math.asin(Math.max(-1, Math.min(1, xh.y))) / D2R;
    range(out, 'trunkRoll', roll); out.trunkRollMove = out.trunkRoll[1] - out.trunkRoll[0];
    if (lim.roll !== null && out.trunkRollMove > lim.roll) flagOnce(out, name + ': the trunk twists ' + out.trunkRollMove.toFixed(1) + ' deg (cue: no twisting; max ' + lim.roll + ')');
    out.hipRollMax = Math.max(out.hipRollMax || 0, Math.abs(hipRoll));
    if (Math.abs(hipRoll) > 6) flagOnce(out, name + ': the hips tilt ' + hipRoll.toFixed(1) + ' deg (cue: hips level; max 6)');
    var sm = jointW(fig, 'L').add(jointW(fig, 'R')).multiplyScalar(0.5), hm = fig.world('thL').add(fig.world('thR')).multiplyScalar(0.5), d = sm.clone().sub(hm);
    var line = Math.atan2(Math.abs(d.y), Math.hypot(d.x, d.z)) / D2R; out.backLineMax = Math.max(out.backLineMax || 0, line);
    if (line > 25) flagOnce(out, name + ': the back is ' + line.toFixed(0) + ' deg off horizontal (cue: back flat; max 25)');
    var hand = T3.skinLow(fig, ['handL']).y - R.top; range(out, 'palmOnPad', hand); out.palmOnPadMin = out.palmOnPad[0]; out.palmOnPadMax = out.palmOnPad[1];
    if (hand < -1.5 || hand > 3) flagOnce(out, name + ': the support palm is ' + hand.toFixed(1) + ' units off the pad (-1.5..3)');
    var w = wristW(fig, 'L'); if (!out._w0) Object.defineProperty(out, '_w0', { value: w.clone() });
    var slide = Math.hypot(w.x - out._w0.x, w.z - out._w0.z); out.palmSlide = Math.max(out.palmSlide || 0, slide);
    if (slide > 1.5) flagOnce(out, name + ': the support hand slides ' + slide.toFixed(1) + ' units');
    var kn = T3.skinLow(fig, ['knL']).y - R.top; range(out, 'kneeOnPad', kn); out.kneeOnPadMin = out.kneeOnPad[0]; out.kneeOnPadMax = out.kneeOnPad[1];
    if (kn < -2.5 || kn > 3) flagOnce(out, name + ': the support knee is ' + kn.toFixed(1) + ' units off the pad (-2.5..3)');
    var J = jointW(fig, 'R'), e = fig.world('elR');
    if (inSet && (ph.id === 'start' || ph.id === 'reset')) { var ef = 180 - T3.jointAngle(fig, 'shR', 'elR', 'handR'); range(out, 'stretchElbow', ef); out.stretchElbowMax = out.stretchElbow[1];
      if (ef > 20) flagOnce(out, name + ': at the bottom the elbow is bent ' + ef.toFixed(0) + ' deg (cue: full stretch; max 20)'); }
    if (inSet && ph.id === 'end-range') {
      var back = J.z - e.z, low = J.y - e.y, wide = Math.abs(e.x - J.x);
      range(out, 'elbowTowardHip', back); out.elbowTowardHipMin = out.elbowTowardHip[0];
      out.elbowBelowShoulderMax = Math.max(out.elbowBelowShoulderMax || -Infinity, low); out.elbowWideMax = Math.max(out.elbowWideMax || 0, wide);
      if (back < 40) flagOnce(out, name + ': at the top the elbow is only ' + back.toFixed(0) + ' units toward the hip (cue: elbow toward the hip; needs 40)');
      if (low > 30) flagOnce(out, name + ': at the top the elbow stays ' + low.toFixed(0) + ' units below the shoulder (it should rise past the trunk; max 30)');
      if (wide > 35) flagOnce(out, name + ': at the top the elbow flares ' + wide.toFixed(0) + ' units out (max 35)');
    }
    R.dumbbell.updateMatrixWorld(true);
    var bb = new THREE.Box3().setFromObject(R.dumbbell), floor = bb.min.y; out.dumbbellAboveFloor = Math.min(out.dumbbellAboveFloor === undefined ? Infinity : out.dumbbellAboveFloor, floor);
    if (floor < 3) flagOnce(out, name + ': the dumbbell comes within ' + floor.toFixed(1) + ' units of the floor (min 3)');
    var bd = new THREE.Box3().setFromObject(R.bench), gapB = bb.intersectsBox(bd) ? -1 : 1; if (gapB < 0) flagOnce(out, name + ': the dumbbell hits the bench');
    var body = propToSkin(fig, [R.dumbbell], ['hips', 'spine', 'chest', 'thL', 'thR', 'knL', 'knR']); out.dumbbellToBody = Math.min(out.dumbbellToBody === undefined ? Infinity : out.dumbbellToBody, body);
    if (body < 1) flagOnce(out, name + ': the dumbbell comes within ' + body.toFixed(1) + ' units of the body (min 1)');
    tempoRule(out, R.def, R.clock.period, name);
    if (lim.twist !== null && t >= R.clock.at + R.clock.reps * R.clock.period && !out._tw) {
      Object.defineProperty(out, '_tw', { value: true });
      if (out.trunkRollMove < lim.twist) flagOnce(out, 'torso-twist variant: the trunk twists only ' + out.trunkRollMove.toFixed(1) + ' deg (the mistake is not visible; needs ' + lim.twist + ')');
    }
  }
  T3.oneArmRowChecks = oneArmRowChecks;
  var ROW1_PHASES = [{ id: 'start', kind: 'hold', label: 'Stretch', a: 0, b: 0.04, cue: 'Back flat, hips level' }, { id: 'concentric', kind: 'up', label: 'Row', a: 0.04, b: 0.40, cue: 'Elbow toward the hip' },
    { id: 'end-range', kind: 'hold', label: 'Top', a: 0.40, b: 0.48, cue: 'Blade moves with the arm' }, { id: 'eccentric', kind: 'down', label: 'Lower', a: 0.48, b: 0.94, cue: 'Full stretch, no twisting' },
    { id: 'reset', kind: 'hold', label: 'Stretch', a: 0.94, b: 1.0, cue: '' }];
  X3['one-arm-row'] = {
    id: 'one-arm-row', name: 'One-arm dumbbell row', knowledge: 'one-arm-row', period: 3.4, phaseMap: ROW1_PHASES, rhythm: { down: [0.04, 0.40], up: [0.48, 0.94], downEase: 'power2.inOut', upEase: 'sine.inOut' },
    // the working side only (lifter's right): the support arm holds still and must not light up
    acts: { 'lat@R': 3, 'trap@R': 3, 'delt-rear@R': 2, 'biceps@R': 2, 'brach@R': 2, erector: 1, 'flexor@R': 1 }, peaks: { 'lat@R': 1, 'trap@R': 0.8, 'delt-rear@R': 0.6, 'biceps@R': 0.55, 'brach@R': 0.45, erector: 0.35, 'flexor@R': 0.4 },
        shots: { side: { az: 270, el: 10 }, three: { az: 225, el: 18 }, front: { az: 330, el: 14 }, back: { az: 160, el: 30 } },
    build: function (stage, fig, m, o) { return buildOneArmRow(X3['one-arm-row'], stage, fig, m, o, merge(ROW1, { garR: 0 })); },
    camera: { target: { tx: 0, ty: 330, tz: 60 }, dist: 2300, fov: 26 },
    checks: function (fig, v, t, out) { oneArmRowChecks(fig, v, t, out, {}); }
  };
  X3['one-arm-row-twist'] = {
    id: 'one-arm-row-twist', name: 'One-arm row, twisting the torso (mistake)', knowledge: 'one-arm-row', mistake: 'torso-twist', period: 3.4, phaseMap: ROW1_PHASES, rhythm: X3['one-arm-row'].rhythm,
    acts: X3['one-arm-row'].acts, peaks: X3['one-arm-row'].peaks, shots: X3['one-arm-row'].shots,
    build: function (stage, fig, m, o) { return buildOneArmRow(X3['one-arm-row-twist'], stage, fig, m, o, merge(ROW1, { garR: 0, twist: 22 })); },
    camera: X3['one-arm-row'].camera,
    checks: function (fig, v, t, out) { oneArmRowChecks(fig, v, t, out, { roll: null, twist: 12 }); }
  };

  /** Build one exercise on a stage: returns {fig, motion, end, def}. cam: optional shot name from def.shots; fit: true or stage.fit options. */
  T3.scene = function (stage, id, o) {
    o = o || {};
    var def = X3[id]; if (!def) throw new Error('unknown 3D exercise ' + id);
    var fig = stage.tibi({ gender: o.gender || 'm', id: o.figId || '', profileSampling: o.profileSampling });
    var m = o.motion || T3.motion();
    var end = def.build(stage, fig, m, o);
    var cam = def.camera, c = stage.cam;
    c.tx = cam.target.tx; c.ty = cam.target.ty; c.tz = cam.target.tz; c.dist = cam.dist; c.fov = cam.fov;
    if (o.shot && def.shots[o.shot]) { c.az = def.shots[o.shot].az; c.el = def.shots[o.shot].el; }
    var sc = { fig: fig, motion: m, end: end, def: def };
    if (o.fit) sc.fit = T3.fitScene(stage, sc, o.fit === true ? {} : o.fit);
    return sc;
  };
})(typeof window !== 'undefined' ? window : globalThis);
