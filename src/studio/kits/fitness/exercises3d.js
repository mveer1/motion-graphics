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
      var bench = EQ.bench({ x: -190, z: 0, y: benchTop, w: 135, l: 560, yaw: 90 }); stage.world.add(bench); fig.props.push(bench);
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
    // numeric assertions run by scripts/rig3d-check.js: forearms stay within 12 degrees of vertical (coaching cue: stacked wrist over elbow)
    checks: function (fig, v, t, out) {
      ['L', 'R'].forEach(function (s) {
        var e = fig.world('el' + s), h = fig.world('hand' + s);
        var ang = Math.acos(Math.max(-1, Math.min(1, (h.y - e.y) / (h.distanceTo(e) || 1)))) * 180 / Math.PI;
        out.maxTilt = Math.max(out.maxTilt || 0, ang);
        var tag = 'forearm tilt exceeds 12 deg from vertical (cue: wrist stacked over elbow)';
        if (ang > 12 && out.indexOf(tag) < 0) out.push(tag);
      });
    }
  };

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
    var bar = EQ.barbell({ half: 330, plate: 46 }); fig.bone.chest.add(bar); bar.position.set(0, 86, -47);
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
    return end;
  }
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
      var bench = EQ.bench({ x: x0 - 64 - 70, z: z0, y: benchTop, w: 140, l: 520, yaw: 0 }); stage.world.add(bench); fig.props.push(bench);
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

  /** Build one exercise on a stage: returns {fig, motion, end, def}. cam: optional shot name from def.shots. */
  T3.scene = function (stage, id, o) {
    o = o || {};
    var def = X3[id]; if (!def) throw new Error('unknown 3D exercise ' + id);
    var fig = stage.tibi({ gender: o.gender || 'm', id: o.figId || '' });
    var m = o.motion || T3.motion();
    var end = def.build(stage, fig, m, o);
    var cam = def.camera, c = stage.cam;
    c.tx = cam.target.tx; c.ty = cam.target.ty; c.tz = cam.target.tz; c.dist = cam.dist; c.fov = cam.fov;
    if (o.shot && def.shots[o.shot]) { c.az = def.shots[o.shot].az; c.el = def.shots[o.shot].el; }
    return { fig: fig, motion: m, end: end, def: def };
  };
})(typeof window !== 'undefined' ? window : globalThis);
