/*
 * Motion Lab fitness kit - one body, three layers (src/studio/kits/fitness/anatomy3d.js)
 * Needs tibi3d.js (and so three.js r158 and brand.js) loaded first. Builds Tibi's anatomy for T3.tibi().
 *
 * WHY THIS EXISTS (2026-11-13, the "detached muscle" review). tibi3d.js 0.2 drew a plain skinned mannequin and then
 * parented one rigid ellipsoid per muscle to the bones. An ellipsoid cannot blend into skin: it floated as a raised red
 * sticker on the glutes, quads and calves, and it did not deform with the body. The structure was wrong, not the colour.
 *
 * THE MODEL NOW. There is ONE table of muscles (MUSCLES below). Everything else is derived from it, so a new exercise
 * never invents another external object:
 *   1. SKIN   the core limbs and trunk (cores) plus every muscle volume are smooth-unioned as signed-distance fields and
 *             meshed once (surface nets) into ONE continuous, watertight skinned surface in an A-pose bind. Muscle
 *             definition is relief of that surface (a fillet, never a separate shape). Shorts are a colour region with a
 *             sub-4-unit hem step, not a second shell. Hands and head are in the same surface.
 *   2. ACTIVATION  each skin vertex stores the weight of the (up to four) muscles whose volume it lies on. A highlight is a
 *             colour delta on those vertices, so it follows the surface, blends with soft edges and moves with the skin.
 *             A bulge is a displacement of the same vertices along their normals (biceps swell, calf contracts).
 *   3. CUTAWAY  the same muscle table is lofted into internal muscle meshes (layer 1 superficial, layer 2 deep), plus
 *             tendons and bones (layer 3), every vertex pushed inside the skin by construction. A cut window is an
 *             ellipsoid in BIND space evaluated per fragment on the skin (and on layer 1), so it stays registered to the
 *             anatomy in any pose. Isolated mode offsets chosen muscles in bind space (before skinning) next to a ghosted body.
 *   4. TESTS  scripts/anatomy3d-check.js: watertight skin, nothing protrudes, layer order along a ray, mask coverage, no drift.
 *
 * Everything is deterministic (no Math.random, no clock). Everything except the three small shader patches runs in node.
 */
(function (global) {
  'use strict';
  var Studio = global.Studio || (global.Studio = {});
  var F = Studio.kit && Studio.kit.fitness, THREE = global.THREE, T3 = F && F.t3d;
  if (!T3) throw new Error('kits/fitness/anatomy3d.js needs tibi3d.js loaded first');
  var A = T3.anatomy = { version: '1.0.0' };
  var D2R = Math.PI / 180, C = T3.colors;

  // ------------------------------------------------------------------ look (state language: see character-guidelines.md)
  /*
   * External skin is cobalt. A working muscle glows on the SURFACE in its role colour (coral prime mover, marigold secondary,
   * pale cobalt stabiliser). Anything INSIDE the body uses a different, warm family so the viewer never confuses "this muscle is
   * working" with "this is what is under the skin": rosewood for muscle, ivory for tendon and bone, a cream section line where
   * the skin was cut. Only the muscle the film is about turns coral inside the cutaway.
   */
  var LOOK = A.look = {
    tone: 0.5,                                // how far a muscle region at rest leans from skin toward muscle cobalt (0 = none)
    crease: 0.24,                             // darkening in the fillets between muscles (definition without separate shapes)
    interior: '#8B565A',                      // inside of the shell (connective tissue), seen only through a cut window: warm, never a navy void
    rim: '#F6EFE0',                           // the cut edge of the skin (a section line)
    muscle: '#C98A82', muscleDeep: '#A8645F', muscleShade: '#7C3F45',
    tendon: '#F3E7CF', bone: '#E3D5B6', boneShade: '#BFB08C'
  };

  // ------------------------------------------------------------------ small vector helpers (plain arrays: fast and node-safe)
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
  function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
  function nrm(v) { var l = Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function clamp(x, a, b) { return x < a ? a : x > b ? b : x; }
  function sstep(a, b, x) { var t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); }
  /** Orthonormal frame from an axis and two hints: [ax, wd, td] with wd ~ hint1, td ~ hint2. */
  function frame(ax, h1, h2) {
    var a = nrm(ax), d = dot(h1, a), w = nrm([h1[0] - a[0] * d, h1[1] - a[1] * d, h1[2] - a[2] * d]);
    var t = [h2[0] - a[0] * dot(h2, a) - w[0] * dot(h2, w), h2[1] - a[1] * dot(h2, a) - w[1] * dot(h2, w), h2[2] - a[2] * dot(h2, a) - w[2] * dot(h2, w)];
    return [a, w, nrm(t)];
  }
  function catmull(p0, p1, p2, p3, t) {
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t);
  }
  function sampleKeys(keys, n) {
    var out = [], m = keys.length;
    for (var i = 0; i < n; i++) {
      var u = n === 1 ? 0 : i / (n - 1) * (m - 1), k = Math.min(m - 2, Math.floor(u)), t = u - k, row = [];
      for (var c = 0; c < keys[0].length; c++) row.push(catmull(keys[Math.max(0, k - 1)][c], keys[k][c], keys[k + 1][c], keys[Math.min(m - 1, k + 2)][c], t));
      out.push(row);
    }
    return out;
  }
  function smin(a, b, k) { var h = Math.max(k - Math.abs(a - b), 0) / k; return Math.min(a, b) - h * h * k * 0.25; }
  /** First-order signed distance to an axis-aligned ellipse (a, b) at (x, z): accurate near the contour, linear far away. */
  function ellipseD(x, z, a, b) {
    var e2 = x * x / (a * a) + z * z / (b * b);
    if (e2 < 1e-10) return -Math.min(a, b);
    var e = Math.sqrt(e2), g = Math.sqrt(x * x / (a * a * a * a) + z * z / (b * b * b * b)) / e;
    return (e - 1) / g;
  }

  // ------------------------------------------------------------------ SDF primitives (bind space)
  /**
   * Tube along an axis: rows [[s, rx, rz, cx, cz], ...] (s = distance from A0 along ax; rx along wd, rz along td; centre offsets).
   * Catmull-Rom between rows. o.p > 2 squares the section (the trunk). Round caps.
   */
  function makeTube(A0, ax, wd, td, rows, o) {
    o = o || {};
    var n = 48, s0 = rows[0][0], s1 = rows[rows.length - 1][0], lut = sampleKeys(rows, n), p = o.p || 2;
    var maxR = 0;
    rows.forEach(function (r) { maxR = Math.max(maxR, r[1] + Math.abs(r[3] || 0), r[2] + Math.abs(r[4] || 0)); });
    var P0 = [A0[0] + ax[0] * s0, A0[1] + ax[1] * s0, A0[2] + ax[2] * s0], P1 = [A0[0] + ax[0] * s1, A0[1] + ax[1] * s1, A0[2] + ax[2] * s1];
    var prim = { kind: 'tube', box: [Math.min(P0[0], P1[0]) - maxR - 2, Math.min(P0[1], P1[1]) - maxR - 2, Math.min(P0[2], P1[2]) - maxR - 2,
                                     Math.max(P0[0], P1[0]) + maxR + 2, Math.max(P0[1], P1[1]) + maxR + 2, Math.max(P0[2], P1[2]) + maxR + 2], A: P0, B: P1, ax: ax };
    prim.f = function (x, y, z) {
      var vx = x - A0[0], vy = y - A0[1], vz = z - A0[2];
      var s = vx * ax[0] + vy * ax[1] + vz * ax[2];
      var t = clamp((s - s0) / (s1 - s0), 0, 1) * (n - 1), i0 = Math.min(n - 2, Math.floor(t)), f = t - i0, a = lut[i0], b = lut[i0 + 1];
      var rx = a[1] + (b[1] - a[1]) * f, rz = a[2] + (b[2] - a[2]) * f, cx = a[3] + (b[3] - a[3]) * f, cz = a[4] + (b[4] - a[4]) * f;
      var px = vx - ax[0] * s, py = vy - ax[1] * s, pz = vz - ax[2] * s;
      var xw = px * wd[0] + py * wd[1] + pz * wd[2] - cx, zt = px * td[0] + py * td[1] + pz * td[2] - cz;
      var dr;
      if (p === 2) dr = ellipseD(xw, zt, rx, rz);
      else {
        var e = Math.pow(Math.pow(Math.abs(xw) / rx, p) + Math.pow(Math.abs(zt) / rz, p), 1 / p);
        dr = (e - 1) * Math.min(rx, rz) * 0.9;
      }
      var da = Math.max(s0 - s, s - s1);
      var ox = Math.max(dr, 0), oy = Math.max(da, 0);
      return Math.sqrt(ox * ox + oy * oy) + Math.min(Math.max(dr, da), 0);
    };
    return prim;
  }
  /**
   * Spindle: a muscle belly from A to B. Radius profile (1-(2u-1)^2)^pw along the axis: pw 0.5 is an exact ellipsoid, smaller is
   * fuller (a blocky belly), larger tapers to a point (a tendinous end). rw across wd, rt across td.
   */
  function makeSpindle(Apt, Bpt, wd, td, rw, rt, pw) {
    var d = [Bpt[0] - Apt[0], Bpt[1] - Apt[1], Bpt[2] - Apt[2]], L = Math.sqrt(dot(d, d)), ax = [d[0] / L, d[1] / L, d[2] / L], m = Math.max(rw, rt);
    var prim = { kind: 'spindle', A: Apt, B: Bpt, ax: ax, wd: wd, td: td, rw: rw, rt: rt, pw: pw, L: L,
      box: [Math.min(Apt[0], Bpt[0]) - m - 2, Math.min(Apt[1], Bpt[1]) - m - 2, Math.min(Apt[2], Bpt[2]) - m - 2, Math.max(Apt[0], Bpt[0]) + m + 2, Math.max(Apt[1], Bpt[1]) + m + 2, Math.max(Apt[2], Bpt[2]) + m + 2] };
    prim.u = function (x, y, z) { return clamp(((x - Apt[0]) * ax[0] + (y - Apt[1]) * ax[1] + (z - Apt[2]) * ax[2]) / L, 0, 1); };
    prim.f = function (x, y, z) {
      var vx = x - Apt[0], vy = y - Apt[1], vz = z - Apt[2], s = vx * ax[0] + vy * ax[1] + vz * ax[2];
      if (s <= 0) return Math.sqrt(vx * vx + vy * vy + vz * vz);
      if (s >= L) { var bx = x - Bpt[0], by = y - Bpt[1], bz = z - Bpt[2]; return Math.sqrt(bx * bx + by * by + bz * bz); }
      var u = s / L, q = 1 - (2 * u - 1) * (2 * u - 1), prof = Math.pow(q, pw); if (prof < 0.03) prof = 0.03;
      var px = vx - ax[0] * s, py = vy - ax[1] * s, pz = vz - ax[2] * s;
      var xw = px * wd[0] + py * wd[1] + pz * wd[2], zt = px * td[0] + py * td[1] + pz * td[2];
      return ellipseD(xw, zt, rw * prof, rt * prof);
    };
    return prim;
  }

  // ------------------------------------------------------------------ cloth region (shorts, waistband, sports top): shared maths
  var CLOTH = { waist: 58, band: 50, hem: 92, lat: 62, topLo: 150, topHi: 206, topX: 80, thick: 3.4 };
  A.CLOTH = CLOTH;
  /** 0..1 membership of the garment at a bind-space point (hx, hy = the left hip joint, ax = left leg axis). Symmetric in x. */
  function clothAt(x, y, z, hip, ax, hasTop, soft) {
    var q0 = Math.abs(x) - hip[0], q1 = y - hip[1], q2 = z - hip[2];
    var s = q0 * ax[0] + q1 * ax[1] + q2 * ax[2];
    var lx = q0 - ax[0] * s, ly = q1 - ax[1] * s, lz = q2 - ax[2] * s, lat = Math.sqrt(lx * lx + ly * ly + lz * lz);
    var c = sstep(CLOTH.waist + soft, CLOTH.waist - soft, y) * sstep(CLOTH.hem + soft, CLOTH.hem - soft, s) * sstep(CLOTH.lat + 14 + soft, CLOTH.lat + 14 - soft, lat);
    if (hasTop) c = Math.max(c, sstep(CLOTH.topLo - soft, CLOTH.topLo + soft, y) * sstep(CLOTH.topHi + soft, CLOTH.topHi - soft, y) * sstep(CLOTH.topX + soft, CLOTH.topX - soft, Math.abs(x)));
    return c;
  }

  // ------------------------------------------------------------------ the body (bind pose, A-pose) from the specs
  var ARM_A = 26, LEG_B = 4;                       // bind pose: arms 26 deg and legs 4 deg out, so nothing fuses at the armpit or crotch
  A.BIND = { arm: ARM_A, leg: LEG_B };

  /** Core tubes (trunk, neck, arms, legs): the body WITHOUT muscle relief. Muscles add to these, they do not replace them. */
  function coreSpecs(S, g, joints) {
    var ms = S.mscale, f = g === 'f' ? 0.95 : 1, out = [];
    var tr = S.torso.map(function (r) { return [r[0] + 50, r[1] * 0.93, r[2] * 0.93, 0, r[3]]; });          // s = y + 50 along +y, cx = 0, cz = r[3]
    out.push({ id: 'torso', region: 'torso', prim: makeTube([0, -50, 0], [0, 1, 0], [1, 0, 0], [0, 0, 1], tr, { p: 2.3 }) });
    out.push({ id: 'neck', region: 'torso', prim: makeTube([0, 0, 0], [0, 1, 0], [1, 0, 0], [0, 0, 1], [[236, 22, 22, 0, 0], [262, 21, 21, 0, 0], [292, 20, 21, 0, 2]], {}) });
    out.push({ id: 'head', region: 'head', prim: makeSpindle([0, 275, 4], [0, 379, 4], [1, 0, 0], [0, 0, 1], 43, 46, 0.5) });
    ['L', 'R'].forEach(function (sd) {
      var sg = sd === 'L' ? 1 : -1, J = joints['sh' + sd], ax = nrm([sg * Math.sin(ARM_A * D2R), -Math.cos(ARM_A * D2R), 0]), wd = nrm([Math.cos(ARM_A * D2R), sg * Math.sin(ARM_A * D2R), 0]);
      var ak = [[-10, 24, 24], [0, 25.5, 25], [50, 20.5, 19.5], [134, 17.5, 17], [170, 18.5, 17.5], [226, 11.5, 10.5], [244, 10.5, 10]].map(function (k) { return [k[0], k[1] * ms, k[2] * ms, 0, 0]; });
      out.push({ id: 'arm' + sd, region: 'arm' + sd, prim: makeTube(J, ax, wd, [0, 0, 1], ak, {}) });
      var H = joints['hip' + sd], lx = nrm([sg * Math.sin(LEG_B * D2R), -Math.cos(LEG_B * D2R), 0]), lw = nrm([Math.cos(LEG_B * D2R), sg * Math.sin(LEG_B * D2R), 0]);
      var lk = [[-26, 36, 36], [30, 35, 35], [100, 29, 29.5], [178, 23.5, 24.5], [215, 20.5, 22], [300, 15.5, 16.5], [344, 12.5, 13.5]].map(function (k) { return [k[0], k[1] * f, k[2] * f, 0, 0]; });
      out.push({ id: 'leg' + sd, region: 'leg' + sd, prim: makeTube(H, lx, lw, [0, 0, 1], lk, {}) });
    });
    return out;
  }

  /*
   * THE MUSCLE TABLE. Authored in bone-local frames exactly as the old ellipsoids were, so existing activation sets
   * (act.biceps, act.glute, ...) keep their meaning. c = centre, r = radii (x, y, z), rot = euler degrees, axis = which local axis is
   * the muscle's length, pw = belly shape, mask = [full, fade] in units outside the volume (how far its tint reaches on the skin),
   * layer 1 = superficial, 2 = deep, region = whose weights it skins with. noVol: a colour patch only (face, hair).
   */
  function muscleTable(S, g) {
    var MS = S.mscale, L = [];
    function E(key, side, bone, c, r, rot, o) {
      o = o || {};
      L.push({ key: key, side: side, bone: bone, c: c, r: [r[0] * MS, r[1] * MS, r[2] * MS], rot: rot || [0, 0, 0], axis: o.axis || 'y', pw: o.pw || 0.5,
        mask: o.mask || [-1, 7], layer: o.layer || 1, region: o.region, tone: o.tone, noVol: o.noVol, part: o.part, dyn: o.dyn, cloth: o.cloth, inset: o.inset });
    }
    function both(fn) { fn('L', 1); fn('R', -1); }
    both(function (s, sg) {
      // chest, back, trunk (bone frames: chest origin is 150 above the hips, spine 70)
      E('pec', s, 'chest', [sg * 38, 36, 38], [40, 27, 17], [0, sg * -10, sg * -12], { axis: 'x', mask: [-1, 8] });
      E('serratus', s, 'chest', [sg * 74, 6, 8], [11, 30, 14], [0, 0, sg * 14], { mask: [-1, 6] });
      E('lat', s, 'chest', [sg * 66, -26, -33], [26, 62, 14], [0, 0, sg * 10], { dyn: 'lat', mask: [-1, 9] });
      E('trap', s, 'chest', [sg * 26, 84, -20], [36, 20, 18], [0, 0, sg * -28], { axis: 'x', mask: [-1, 8] });
      E('erector', s, 'spine', [sg * 15, 10, -37], [11, 52, 9], null, { mask: [-1, 5] });
      E('oblique', s, 'spine', [sg * 52, 22, 10], [14, 40, 22], [0, 0, sg * -12], { mask: [-1, 6] });
      // thigh
      // quadriceps: rectus femoris down the front, vastus lateralis outside, vastus medialis as the teardrop low on the inside
      E('quad', s, 'th' + s, [0, -80, 26], [18, 80, 18], null, { pw: 0.45, mask: [0, 9] });
      E('quad', s, 'th' + s, [sg * 19, -90, 14], [18, 76, 20], null, { pw: 0.45, mask: [0, 9] });
      E('quad', s, 'th' + s, [-sg * 15, -124, 16], [16, 50, 18], null, { pw: 0.5, mask: [0, 9] });
      E('quad', s, 'th' + s, [0, -94, 9], [21, 68, 15], null, { pw: 0.5, layer: 2, mask: [3, 12] });          // vastus intermedius: deep, under the rectus femoris
      // hamstrings: biceps femoris (outside) and the semis (inside)
      E('hams', s, 'th' + s, [sg * 12, -84, -24], [19, 80, 19], null, { pw: 0.45, mask: [0, 9] });
      E('hams', s, 'th' + s, [-sg * 14, -82, -23], [18, 78, 19], null, { pw: 0.45, mask: [0, 9] });
      // gluteus maximus is a fan from the sacrum (high, medial) to the femur (low, lateral): a flat sheet, not a ball. Medius sits deeper at the hip.
      E('glute', s, 'th' + s, [-sg * 9, -18, -38], [34, 44, 21], [10, sg * 12, sg * 32], { mask: [0, 10], cloth: true, pw: 0.45 });
      E('glutemed', s, 'hips', [sg * 52, 14, -26], [24, 30, 13], [0, 0, sg * -30], { region: 'leg' + s, layer: 2, mask: [2, 9] });
      E('adductor', s, 'th' + s, [-sg * 21, -96, 4], [15, 62, 21], [0, 0, sg * -6], { mask: [0, 8] });
      // lower leg: triceps surae is two heads of the gastrocnemius (superficial, crosses the knee) over the deeper soleus (does not)
      E('soleus', s, 'kn' + s, [0, -98, -13], [30, 50, 16.5], null, { layer: 2, dyn: 'calf', mask: [2, 12] });
      E('calf', s, 'kn' + s, [-sg * 9, -54, -21], [17.5, 56, 19.5], null, { dyn: 'calf', mask: [0, 8], pw: 0.45 });
      E('calf', s, 'kn' + s, [sg * 10, -46, -20], [16.5, 47, 18.5], null, { dyn: 'calf', mask: [0, 8], pw: 0.45 });
      // both heads arise on the femur ABOVE the knee: that is why the gastrocnemius is taut with a straight knee and slack with a bent one
      E('calf', s, 'th' + s, [-sg * 8, -160, -19], [9, 22, 9], null, { dyn: 'calf', mask: [0, 5], pw: 0.55 });
      E('calf', s, 'th' + s, [sg * 9, -160, -19], [9, 22, 9], null, { dyn: 'calf', mask: [0, 5], pw: 0.55 });
      E('tibant', s, 'kn' + s, [0, -62, 15], [15, 62, 13], null, { mask: [0, 6], pw: 0.55 });
      // shoulder, arm
      // deltoid: three heads that taper into the arm at the deltoid tuberosity (a V, not an egg)
      E('delt-front', s, 'sh' + s, [sg * 6, -34, 15], [21, 52, 17], null, { pw: 0.66, mask: [-1, 7] });
      E('delt-side', s, 'sh' + s, [sg * 16, -32, 0], [19, 52, 25], null, { pw: 0.66, mask: [-1, 7] });
      E('delt-rear', s, 'sh' + s, [sg * 6, -34, -15], [21, 50, 17], null, { pw: 0.66, mask: [-1, 7] });
      E('biceps', s, 'sh' + s, [0, -66, 19], [20, 46, 17], null, { dyn: 'biceps', mask: [-1, 7], pw: 0.55 });
      E('triceps', s, 'sh' + s, [0, -62, -19], [21, 50, 18], null, { dyn: 'triceps', mask: [-1, 7] });
      E('brach', s, 'el' + s, [sg * -7, -22, 13], [13, 34, 11], null, { mask: [-1, 6] });
      E('flexor', s, 'el' + s, [0, -34, 10], [18, 46, 14], null, { mask: [-1, 6] });
      E('extensor', s, 'el' + s, [0, -34, -10], [18, 46, 14], null, { mask: [-1, 6] });
      // abs: flat, blocky tiles (low relief, not round bumps)
      [[80, 15], [104, 15], [128, 13]].forEach(function (row, i) { E('abs', s, 'spine', [sg * 13.5, row[0] - 70, 40 + i * 1.6], [13.5, 11, 7], null, { mask: [-1, 7], pw: 0.36 }); });
      if (S.bust) E('bust', s, 'chest', [sg * 30, 36, 38], [28, 22, 18], null, { part: true });
      // joint masses and extremities: not muscles, but part of the same continuous skin (they carry weights, never activation)
      E('shoulder-ball', s, 'sh' + s, [0, -4, 0], [27, 27, 26], null, { part: true });
      E('palm', s, 'hand' + s, [0, -24, 0], [19, 24, 12], null, { part: true, region: 'arm' + s });
      E('fingers', s, 'hand' + s, [0, -46, 6], [16, 15, 11], null, { part: true, region: 'arm' + s });
      E('thumb', s, 'hand' + s, [-sg * 17, -26, 8], [7, 15, 7], [0, 0, -sg * 14], { part: true, region: 'arm' + s });
    });
    E('face', null, 'head', [0, 44, 22], [33, 38, 26], null, { tone: C.face, noVol: true, mask: [-2, 9] });
    if (g === 'f') E('hair', null, 'head', [0, 76, -6], [41, 30, 42], null, { tone: C.hair, noVol: false, mask: [-1, 3] });
    return L;
  }
  A.muscleTable = muscleTable;

  // region weights: t ascending, stops [[t, bone], ...]
  function blendStops(t, stops) {
    if (t <= stops[0][0]) return [[stops[0][1], 1]];
    for (var i = 0; i < stops.length - 1; i++) {
      var a = stops[i], b = stops[i + 1];
      if (t <= b[0]) { var u = (t - a[0]) / (b[0] - a[0]); u = u * u * (3 - 2 * u); return u < 0.001 ? [[a[1], 1]] : u > 0.999 ? [[b[1], 1]] : [[a[1], 1 - u], [b[1], u]]; }
    }
    return [[stops[stops.length - 1][1], 1]];
  }
  var TORSO_STOPS = [[-262, 'neck'], [-236, 'neck'], [-212, 'chest'], [-150, 'chest'], [-112, 'spine'], [-68, 'spine'], [-28, 'hips'], [60, 'hips']];
  function regionWeights(region, x, y, z, ctx) {
    if (region === 'torso') return blendStops(-y, TORSO_STOPS);
    if (region === 'head') return [['head', 1]];
    var sd = region.charAt(region.length - 1);
    if (region.indexOf('leg') === 0) return blendStops(-y, [[-34, 'hips'], [2, 'th' + sd], [164, 'th' + sd], [204, 'kn' + sd], [400, 'kn' + sd]]);
    var J = ctx.joints['sh' + sd], ax = ctx.armAxis[sd], s = (x - J[0]) * ax[0] + (y - J[1]) * ax[1] + (z - J[2]) * ax[2];
    return blendStops(s, [[-6, 'chest'], [14, 'sh' + sd], [118, 'sh' + sd], [150, 'el' + sd], [226, 'el' + sd], [246, 'hand' + sd]]);
  }
  function regionOfBone(bone) {
    var sd = bone.charAt(bone.length - 1);
    if (bone === 'head') return 'head';
    if (/^(sh|el|hand)[LR]$/.test(bone)) return 'arm' + sd;
    if (/^(th|kn|an)[LR]$/.test(bone)) return 'leg' + sd;
    return 'torso';
  }

  // ------------------------------------------------------------------ SDF grid and surface nets
  function evalGrid(base, mus, bounds, h, kb, km, cloth) {
    var nx = Math.ceil((bounds[3] - bounds[0]) / h) + 1, ny = Math.ceil((bounds[4] - bounds[1]) / h) + 1, nz = Math.ceil((bounds[5] - bounds[2]) / h) + 1;
    var g = new Float32Array(nx * ny * nz).fill(1000), ox = bounds[0], oy = bounds[1], oz = bounds[2];
    function splat(list, k) {
      list.forEach(function (pr) {
        var b = pr.box, m = k + h;
        var i0 = Math.max(0, Math.floor((b[0] - m - ox) / h)), i1 = Math.min(nx - 1, Math.ceil((b[3] + m - ox) / h));
        var j0 = Math.max(0, Math.floor((b[1] - m - oy) / h)), j1 = Math.min(ny - 1, Math.ceil((b[4] + m - oy) / h));
        var k0 = Math.max(0, Math.floor((b[2] - m - oz) / h)), k1 = Math.min(nz - 1, Math.ceil((b[5] + m - oz) / h));
        for (var kk = k0; kk <= k1; kk++) for (var jj = j0; jj <= j1; jj++) {
          var row = (kk * ny + jj) * nx;
          for (var ii = i0; ii <= i1; ii++) { var d = pr.f(ox + ii * h, oy + jj * h, oz + kk * h); g[row + ii] = smin(g[row + ii], d, k); }
        }
      });
    }
    splat(base, kb); splat(mus, km);
    if (cloth) for (var kk = 0; kk < nz; kk++) for (var jj = 0; jj < ny; jj++) for (var ii = 0; ii < nx; ii++) {
      var idx = (kk * ny + jj) * nx + ii;
      if (g[idx] < 6 && g[idx] > -12) g[idx] -= CLOTH.thick * cloth(ox + ii * h, oy + jj * h, oz + kk * h);
    }
    return { g: g, nx: nx, ny: ny, nz: nz, ox: ox, oy: oy, oz: oz, h: h };
  }
  function gridAt(G, x, y, z) {
    var fx = (x - G.ox) / G.h, fy = (y - G.oy) / G.h, fz = (z - G.oz) / G.h;
    var i = clamp(Math.floor(fx), 0, G.nx - 2), j = clamp(Math.floor(fy), 0, G.ny - 2), k = clamp(Math.floor(fz), 0, G.nz - 2);
    var tx = clamp(fx - i, 0, 1), ty = clamp(fy - j, 0, 1), tz = clamp(fz - k, 0, 1), g = G.g, nx = G.nx, ny = G.ny;
    var b = (k * ny + j) * nx + i, s1 = nx, s2 = nx * ny;
    var c00 = g[b] * (1 - tx) + g[b + 1] * tx, c10 = g[b + s1] * (1 - tx) + g[b + s1 + 1] * tx;
    var c01 = g[b + s2] * (1 - tx) + g[b + s2 + 1] * tx, c11 = g[b + s2 + s1] * (1 - tx) + g[b + s2 + s1 + 1] * tx;
    return (c00 * (1 - ty) + c10 * ty) * (1 - tz) + (c01 * (1 - ty) + c11 * ty) * tz;
  }
  function gridGrad(G, x, y, z) {
    var e = G.h * 0.6;
    var gx = gridAt(G, x + e, y, z) - gridAt(G, x - e, y, z), gy = gridAt(G, x, y + e, z) - gridAt(G, x, y - e, z), gz = gridAt(G, x, y, z + e) - gridAt(G, x, y, z - e);
    var l = Math.sqrt(gx * gx + gy * gy + gz * gz) || 1;
    return [gx / l, gy / l, gz / l];
  }
  A._gridAt = gridAt; A._gridGrad = gridGrad;

  /** Naive surface nets: one vertex per sign-changing cell, a quad per sign-changing edge. Returns {pos, idx}. */
  function surfaceNets(G) {
    var nx = G.nx, ny = G.ny, nz = G.nz, g = G.g, h = G.h, cx = nx - 1, cy = ny - 1, cz = nz - 1;
    var cell = new Int32Array(cx * cy * cz).fill(-1), pos = [];
    var cornerOff = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1], [1, 1, 1]];
    var edges = [[0, 1], [2, 3], [4, 5], [6, 7], [0, 2], [1, 3], [4, 6], [5, 7], [0, 4], [1, 5], [2, 6], [3, 7]];
    var val = new Float32Array(8);
    for (var k = 0; k < cz; k++) for (var j = 0; j < cy; j++) for (var i = 0; i < cx; i++) {
      var mask = 0;
      for (var c = 0; c < 8; c++) { var o = cornerOff[c]; val[c] = g[((k + o[2]) * ny + (j + o[1])) * nx + i + o[0]]; if (val[c] < 0) mask |= 1 << c; }
      if (mask === 0 || mask === 255) continue;
      var sx = 0, sy = 0, sz = 0, cnt = 0;
      for (var e = 0; e < 12; e++) {
        var a = edges[e][0], b = edges[e][1];
        if ((val[a] < 0) === (val[b] < 0)) continue;
        var t = val[a] / (val[a] - val[b]), oa = cornerOff[a], ob = cornerOff[b];
        sx += oa[0] + (ob[0] - oa[0]) * t; sy += oa[1] + (ob[1] - oa[1]) * t; sz += oa[2] + (ob[2] - oa[2]) * t; cnt++;
      }
      cell[(k * cy + j) * cx + i] = pos.length / 3;
      pos.push(G.ox + (i + sx / cnt) * h, G.oy + (j + sy / cnt) * h, G.oz + (k + sz / cnt) * h);
    }
    var idx = [];
    function quad(a, b, c, d, flip) {
      if (a < 0 || b < 0 || c < 0 || d < 0) return;
      // split on the shorter diagonal
      var dAC = dist2(a, c), dBD = dist2(b, d);
      var q = dAC <= dBD ? [a, b, c, a, c, d] : [a, b, d, b, c, d];
      if (flip) { var t0 = q[1]; q[1] = q[2]; q[2] = t0; t0 = q[4]; q[4] = q[5]; q[5] = t0; }
      idx.push(q[0], q[1], q[2], q[3], q[4], q[5]);
    }
    function dist2(a, b) { var dx = pos[a * 3] - pos[b * 3], dy = pos[a * 3 + 1] - pos[b * 3 + 1], dz = pos[a * 3 + 2] - pos[b * 3 + 2]; return dx * dx + dy * dy + dz * dz; }
    function C_(i, j, k) { return (i < 0 || j < 0 || k < 0 || i >= cx || j >= cy || k >= cz) ? -1 : cell[(k * cy + j) * cx + i]; }
    for (var k2 = 1; k2 < nz - 1; k2++) for (var j2 = 1; j2 < ny - 1; j2++) for (var i2 = 1; i2 < nx - 1; i2++) {
      var v0 = g[(k2 * ny + j2) * nx + i2], in0 = v0 < 0;
      if ((g[(k2 * ny + j2) * nx + i2 + 1] < 0) !== in0) quad(C_(i2, j2 - 1, k2 - 1), C_(i2, j2, k2 - 1), C_(i2, j2, k2), C_(i2, j2 - 1, k2), !in0);
      if ((g[(k2 * ny + j2 + 1) * nx + i2] < 0) !== in0) quad(C_(i2 - 1, j2, k2 - 1), C_(i2 - 1, j2, k2), C_(i2, j2, k2), C_(i2, j2, k2 - 1), !in0);
      if ((g[((k2 + 1) * ny + j2) * nx + i2] < 0) !== in0) quad(C_(i2 - 1, j2 - 1, k2), C_(i2, j2 - 1, k2), C_(i2, j2, k2), C_(i2 - 1, j2, k2), !in0);
    }
    return { pos: pos, idx: idx };
  }

  /** Laplacian smoothing (keeps the contour: each pass is followed by a pull back onto the zero set of the grid). */
  function relax(mesh, G, passes) {
    var pos = mesh.pos, idx = mesh.idx, n = pos.length / 3, adj = new Array(n);
    for (var i = 0; i < n; i++) adj[i] = [];
    for (var t = 0; t < idx.length; t += 3) for (var e = 0; e < 3; e++) { var a = idx[t + e], b = idx[t + (e + 1) % 3]; adj[a].push(b); adj[b].push(a); }
    for (var p = 0; p < passes; p++) {
      var nxt = new Float64Array(pos.length);
      for (var v = 0; v < n; v++) {
        var l = adj[v], sx = 0, sy = 0, sz = 0; if (!l.length) { nxt[v * 3] = pos[v * 3]; nxt[v * 3 + 1] = pos[v * 3 + 1]; nxt[v * 3 + 2] = pos[v * 3 + 2]; continue; }
        for (var q = 0; q < l.length; q++) { sx += pos[l[q] * 3]; sy += pos[l[q] * 3 + 1]; sz += pos[l[q] * 3 + 2]; }
        nxt[v * 3] = lerp(pos[v * 3], sx / l.length, 0.55); nxt[v * 3 + 1] = lerp(pos[v * 3 + 1], sy / l.length, 0.55); nxt[v * 3 + 2] = lerp(pos[v * 3 + 2], sz / l.length, 0.55);
      }
      for (var v2 = 0; v2 < n; v2++) {
        var x = nxt[v2 * 3], y = nxt[v2 * 3 + 1], z = nxt[v2 * 3 + 2], d = gridAt(G, x, y, z), gr = gridGrad(G, x, y, z);
        pos[v2 * 3] = x - gr[0] * d; pos[v2 * 3 + 1] = y - gr[1] * d; pos[v2 * 3 + 2] = z - gr[2] * d;
      }
    }
  }

  // ------------------------------------------------------------------ build the body data for a gender (cached: pure geometry, no THREE objects)
  var DATA = {};
  function isMask(m) { return !m.part && !m.tone; }
  /**
   * ctx: {S, g, joints: {shL, shR, hipL, hipR: [x,y,z] in bind space}, boneBind: {name: THREE.Matrix4 (root frame, A-pose bind)}, boneIndex}.
   * Returns the shared, immutable data of the skin; every figure copies the dynamic arrays.
   */
  A.buildData = function (ctx) {
    var key = ctx.g;
    if (DATA[key]) return DATA[key];
    var S = ctx.S, g = ctx.g, bb = ctx.boneBind, joints = ctx.joints, boneIdx = ctx.boneIndex;
    var armAxis = { L: nrm([Math.sin(ARM_A * D2R), -Math.cos(ARM_A * D2R), 0]), R: nrm([-Math.sin(ARM_A * D2R), -Math.cos(ARM_A * D2R), 0]) };
    var rctx = { joints: joints, armAxis: armAxis };
    var cores = coreSpecs(S, g, joints), table = muscleTable(S, g);
    var V3 = THREE.Vector3;
    table.forEach(function (m, mi) {
      m.index = mi;
      var mb = bb[m.bone], rot = new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(m.rot[0] * D2R, m.rot[1] * D2R, m.rot[2] * D2R, 'XYZ'));
      var ex = new V3(1, 0, 0).applyMatrix4(rot), ey = new V3(0, 1, 0).applyMatrix4(rot), ez = new V3(0, 0, 1).applyMatrix4(rot);
      var axes = { x: [ex, ey, ez], y: [ey, ex, ez], z: [ez, ex, ey] }[m.axis];
      var ri = { x: [m.r[0], m.r[1], m.r[2]], y: [m.r[1], m.r[0], m.r[2]], z: [m.r[2], m.r[0], m.r[1]] }[m.axis];
      var cB = new V3(m.c[0], m.c[1], m.c[2]).applyMatrix4(mb), rotOnly = new THREE.Matrix3().setFromMatrix4(mb);
      function dir(v) { return v.clone().applyMatrix3(rotOnly).normalize().toArray(); }
      var ax = dir(axes[0]), wd = dir(axes[1]), td = dir(axes[2]), half = ri[0];
      m.A = [cB.x - ax[0] * half, cB.y - ax[1] * half, cB.z - ax[2] * half];
      m.B = [cB.x + ax[0] * half, cB.y + ax[1] * half, cB.z + ax[2] * half];
      m.center = [cB.x, cB.y, cB.z]; m.rw = ri[1]; m.rt = ri[2]; m.ax = ax; m.wd = wd; m.td = td;
      m.prim = makeSpindle(m.A, m.B, wd, td, ri[1], ri[2], m.pw);
      m.region = m.region || regionOfBone(m.bone);
      m.local = m.c.slice();
    });
    var masked = table.filter(isMask), patches = table.filter(function (m) { return !!m.tone; });
    masked.forEach(function (m, i) { m.slot = i; });
    var vol = table.filter(function (m) { return !m.noVol; });
    var base = cores.map(function (c) { return c.prim; }), musPrims = vol.map(function (m) { return m.prim; });
    var hasTop = !!S.bust, hipL = joints.hipL, legAx = nrm([Math.sin(LEG_B * D2R), -Math.cos(LEG_B * D2R), 0]);
    var clothFn = function (x, y, z) { return clothAt(x, y, z, hipL, legAx, hasTop, 3); };
    var all = base.concat(musPrims), b = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9];
    all.forEach(function (p) { for (var i = 0; i < 3; i++) { b[i] = Math.min(b[i], p.box[i]); b[i + 3] = Math.max(b[i + 3], p.box[i + 3]); } });
    b = [b[0] - 14, b[1] - 14, b[2] - 14, b[3] + 14, b[4] + 14, b[5] + 14];
    var H = ctx.cell || 4.5;
    var G = evalGrid(base, musPrims, b, H, 16, 8, clothFn);
    var mesh = surfaceNets(G);
    relax(mesh, G, 2);
    var n = mesh.pos.length / 3;
    var NSLOT = 8, normals = new Float32Array(n * 3), cav = new Float32Array(n), mus = new Float32Array(n * NSLOT), muw = new Float32Array(n * NSLOT), toneMax = new Float32Array(n);
    var patchIdx = new Uint8Array(n), patchW = new Float32Array(n), si = new Uint16Array(n * 4), sw = new Float32Array(n * 4), uvw = new Float32Array(n);
    var regionIds = ['torso', 'head', 'armL', 'armR', 'legL', 'legR'], coreOfRegion = {};
    cores.forEach(function (c) { (coreOfRegion[c.region] = coreOfRegion[c.region] || []).push(c.prim); });
    vol.forEach(function (m) { (coreOfRegion[m.region] = coreOfRegion[m.region] || []).push(m.prim); });
    var covered = new Array(masked.length).fill(0), dReg = {};
    var W = masked.map(function () { return new Float32Array(n); }), PW = patches.map(function () { return new Float32Array(n); });
    for (var v = 0; v < n; v++) {
      var x = mesh.pos[v * 3], y = mesh.pos[v * 3 + 1], z = mesh.pos[v * 3 + 2];
      var gr = gridGrad(G, x, y, z); normals[v * 3] = gr[0]; normals[v * 3 + 1] = gr[1]; normals[v * 3 + 2] = gr[2];
      var dmin = 1e9;
      for (var ri2 = 0; ri2 < regionIds.length; ri2++) {
        var r = regionIds[ri2], best = 1e9, list = coreOfRegion[r] || [];
        for (var q = 0; q < list.length; q++) { var d = list[q].f(x, y, z); if (d < best) best = d; }
        dReg[r] = best; if (best < dmin) dmin = best;
      }
      var acc = {};
      regionIds.forEach(function (r) {
        var c = Math.exp(-(dReg[r] - dmin) / 6); if (c < 0.02) return;
        var wl = regionWeights(r, x, y, z, rctx);
        for (var q = 0; q < wl.length; q++) acc[wl[q][0]] = (acc[wl[q][0]] || 0) + c * wl[q][1];
      });
      var names = Object.keys(acc).sort(function (p, q) { return acc[q] - acc[p]; }).slice(0, 4), ws = 0;
      names.forEach(function (nm) { ws += acc[nm]; });
      for (var q2 = 0; q2 < 4; q2++) { si[v * 4 + q2] = q2 < names.length ? boneIdx[names[q2]] : 0; sw[v * 4 + q2] = q2 < names.length ? acc[names[q2]] / ws : 0; }
      var dsharp = dmin;
      for (var vi = 0; vi < vol.length; vi++) { var dv = vol[vi].prim.f(x, y, z); if (dv < dsharp) dsharp = dv; }
      cav[v] = clamp(dsharp / 3.2, 0, 1);
      for (var mi3 = 0; mi3 < masked.length; mi3++) { var m3 = masked[mi3]; W[mi3][v] = 1 - sstep(m3.mask[0], m3.mask[1], m3.prim.f(x, y, z)); }
      for (var pi = 0; pi < patches.length; pi++) PW[pi][v] = 1 - sstep(patches[pi].mask[0], patches[pi].mask[1], patches[pi].prim.f(x, y, z));
    }
    // Soft edges: a 4.5-unit mesh cannot ramp a tint over fewer than ~2 cells without a visible step, so diffuse every mask over the surface
    // (two passes of neighbour averaging widen each fade by about two cells and keep the muscle's shape).
    var adj = new Array(n), ii2, tt;
    for (ii2 = 0; ii2 < n; ii2++) adj[ii2] = [];
    for (tt = 0; tt < mesh.idx.length; tt += 3) for (var ee = 0; ee < 3; ee++) adj[mesh.idx[tt + ee]].push(mesh.idx[tt + (ee + 1) % 3]);
    function diffuse(arr, passes) {
      var cur = arr, nxt = new Float32Array(n);
      for (var ps = 0; ps < passes; ps++) {
        for (var vv = 0; vv < n; vv++) { var l = adj[vv], sum = 0; for (var kk = 0; kk < l.length; kk++) sum += cur[l[kk]]; nxt[vv] = l.length ? 0.45 * cur[vv] + 0.55 * sum / l.length : cur[vv]; }
        var sw2 = cur; cur = nxt; nxt = sw2;
      }
      return cur;
    }
    for (var di = 0; di < W.length; di++) W[di] = diffuse(W[di], 3);
    for (var dj = 0; dj < PW.length; dj++) PW[dj] = diffuse(PW[dj], 2);
    var order = [];
    for (var v6 = 0; v6 < n; v6++) {
      var tm = 0; order.length = 0;
      for (var mi4 = 0; mi4 < masked.length; mi4++) { var wv = W[mi4][v6]; if (wv > tm) tm = wv; if (wv > 0.02) order.push(mi4); }
      toneMax[v6] = tm;
      order.sort(function (p, q) { return W[q][v6] - W[p][v6]; });
      for (var q3 = 0; q3 < NSLOT; q3++) { mus[v6 * NSLOT + q3] = q3 < order.length ? order[q3] : 0; muw[v6 * NSLOT + q3] = q3 < order.length ? W[order[q3]][v6] : 0; if (q3 < order.length && W[order[q3]][v6] > 0.5) covered[order[q3]]++; }
      for (var pj = 0; pj < patches.length; pj++) if (PW[pj][v6] > patchW[v6]) { patchW[v6] = PW[pj][v6]; patchIdx[v6] = pj + 1; }
    }
    var data = { key: key, G: G, mesh: mesh, n: n, normals: normals, cav: cav, mus: mus, muw: muw, toneMax: toneMax, patchIdx: patchIdx, patchW: patchW, skinIndex: si, skinWeight: sw,
      table: table, masked: masked, patches: patches, vol: vol, cores: cores, covered: covered, hasTop: hasTop, hipL: hipL, legAx: legAx, armAxis: armAxis, joints: joints, S: S, g: g };
    DATA[key] = data;
    return data;
  };
  A._data = DATA;

  // ------------------------------------------------------------------ colour ramps (the same language as the 2D rig and the old 3D one)
  var ROLE_COLOR = { 1: C.stab, 2: C.second, 3: C.prime };
  function col3(hex) { return new THREE.Color(hex); }
  /** Colour of a muscle region at activation a (0..1): rest -> pale tint of the role -> role (blue straight to coral goes muddy purple). */
  function ramp(out, rest, mid, full, a) {
    if (a <= 0) return out.copy(rest);
    a = Math.min(1, a);
    return a < 0.4 ? out.copy(rest).lerp(mid, a / 0.4) : out.copy(mid).lerp(full, (a - 0.4) / 0.6);
  }

  // ------------------------------------------------------------------ the skin shader patch (cloth edge, creases, cut windows, interior)
  var NWIN = 6;
  var SKIN_VERT_DECL = 'attribute vec3 colorC;\nattribute float aCav;\nvarying vec3 vColC;\nvarying float vCav;\nvarying vec3 vBind;\n';
  var SKIN_FRAG_DECL = [
    'varying vec3 vColC; varying float vCav; varying vec3 vBind;',
    'uniform vec4 uCloth; uniform vec4 uTop; uniform vec3 uHip; uniform vec3 uLegAx; uniform vec3 uBand; uniform float uCrease;',
    'uniform vec3 uWc[' + NWIN + ']; uniform mat3 uWm[' + NWIN + ']; uniform vec4 uWo[' + NWIN + ']; uniform vec3 uInterior; uniform vec3 uRim; uniform float uRimW;',
    'float sstepF(float a, float b, float x) { float t = clamp((x - a) / (b - a), 0.0, 1.0); return t * t * (3.0 - 2.0 * t); }',
    'float clothMask(vec3 p) {',
    '  vec3 q = vec3(abs(p.x) - uHip.x, p.y - uHip.y, p.z - uHip.z); float s = dot(q, uLegAx); vec3 l = q - uLegAx * s; float lat = length(l);',
    '  float c = sstepF(uCloth.x + 0.9, uCloth.x - 0.9, p.y) * sstepF(uCloth.z + 0.9, uCloth.z - 0.9, s) * sstepF(uCloth.w + 15.0, uCloth.w + 13.0, lat);',
    '  c = max(c, uTop.w * sstepF(uTop.x - 0.9, uTop.x + 0.9, p.y) * sstepF(uTop.y + 0.9, uTop.y - 0.9, p.y) * sstepF(uTop.z + 0.9, uTop.z - 0.9, abs(p.x)));',
    '  return c; }'
  ].join('\n') + '\n';
  var SKIN_FRAG_BODY = [
    'float clM = clothMask(vBind);',
    'diffuseColor.rgb = mix(vColor.rgb, vColC, clM);',
    'float bandM = clM * sstepF(uCloth.y - 0.9, uCloth.y + 0.9, vBind.y) * step(vBind.y, uCloth.x + 1.0);',
    'diffuseColor.rgb = mix(diffuseColor.rgb, uBand, bandM);',
    'diffuseColor.rgb *= 1.0 - uCrease * vCav;',
    'for (int wi = 0; wi < ' + NWIN + '; wi++) {',
    '  if (uWo[wi].x > 0.001) { float we = length(uWm[wi] * (vBind - uWc[wi]));',
    '    if (we < uWo[wi].x) discard;',
    '    else if (we < uWo[wi].x + uRimW) diffuseColor.rgb = uRim; } }',
    'if (!gl_FrontFacing) diffuseColor.rgb = uInterior;'
  ].join('\n') + '\n';

  /** Window records are ellipsoids in bind space: centre + a rotation matrix that includes 1/radii (so length(M (p - c)) < 1 is inside). */
  function winUniforms(W) {
    var U = { uWc: { value: [] }, uWm: { value: [] }, uWo: { value: [] } };
    for (var i = 0; i < NWIN; i++) { U.uWc.value.push(new THREE.Vector3()); U.uWm.value.push(new THREE.Matrix3()); U.uWo.value.push(new THREE.Vector4()); }
    return U;
  }

  // ------------------------------------------------------------------ internal layers: muscles, tendons, bones (built lazily, only when a view needs them)
  /*
   * Windows are ellipsoids in BIND space (name, bone-local centre, radii). A window opens in two stages with one number:
   *   open 0 -> 1   the skin (and the shorts) dissolve inside it, a cream section line marks the cut edge
   *   open 1 -> 2   the superficial muscles (layer 1) dissolve too, which exposes the deep layer (soleus under the gastrocnemius)
   * They are evaluated per fragment on bind-space positions, so a window stays on its anatomy in every pose.
   */
  var WINDOWS = [
    { name: 'calf', bone: 'kn', c: [0, -58, -24], r: [52, 94, 34], both: true },          // starts above the knee: the gastrocnemius arises on the femur
    { name: 'glute', bone: 'hips', c: [34, -22, -50], r: [50, 56, 34], both: true, mirror: true },
    { name: 'quad', bone: 'th', c: [2, -104, 36], r: [44, 84, 34], both: true },
    { name: 'hams', bone: 'th', c: [0, -104, -38], r: [44, 84, 34], both: true },
    { name: 'arm', bone: 'sh', c: [0, -72, 22], r: [36, 62, 32], both: true },
    { name: 'tri', bone: 'sh', c: [0, -72, -22], r: [36, 62, 32], both: true },
    { name: 'chest', bone: 'chest', c: [38, 40, 44], r: [54, 44, 32], both: true, mirror: true }
  ];
  A.WINDOWS = WINDOWS;
  /** Bones and tendons: rigid (a bone never bends), authored in bone-local frames. a/b = [bone, x, y, z]. */
  function innerSpecs(S, g) {
    var out = [];
    function bone(id, side, b0, a, b, rw, rt, pw, kind, o) { out.push(Object.assign({ id: id, side: side, kind: kind || 'bone', a: [b0].concat(a), b: [b0].concat(b), rw: rw, rt: rt, pw: pw, rigid: b0 }, o || {})); }
    ['L', 'R'].forEach(function (s) {
      var sg = s === 'L' ? 1 : -1, ms = S.mscale;
      bone('femur', s, 'th' + s, [0, -4, 0], [0, -176, 0], 10.5, 10.5, 0.14);
      bone('femur-head', s, 'th' + s, [-sg * 22, 4, 0], [0, -6, 0], 11, 11, 0.5);
      bone('condyles', s, 'kn' + s, [0, 6, -4], [0, -10, -4], 17, 14, 0.5);
      bone('tibia', s, 'kn' + s, [0, -8, 2], [0, -160, 0], 10.5, 11, 0.18);
      bone('fibula', s, 'kn' + s, [sg * 13, -14, -4], [sg * 12, -150, -5], 4.5, 5, 0.2);
      bone('patella', s, 'kn' + s, [0, 14, 26], [0, -4, 26], 10, 5, 0.5, 'bone', { win: 'quad' });
      bone('calcaneus', s, 'an' + s, [0, -8, -12], [0, -24, -22], 11, 10, 0.4);
      bone('humerus', s, 'sh' + s, [0, -2, 0], [0, -132, 0], 8.5 * ms, 8.5 * ms, 0.14);
      bone('forearm', s, 'el' + s, [0, -4, 0], [0, -102, 0], 6.5 * ms, 7 * ms, 0.2);
      bone('clavicle', s, 'chest', [sg * 8, 98, 18], [sg * 80, 88, 2], 5, 5, 0.3);
      bone('iliac', s, 'hips', [sg * 30, 40, -6], [sg * 50, -10, -2], 15, 22, 0.35);
      bone('patellar-tendon', s, 'kn' + s, [0, -4, 26], [0, -36, 21], 6.5, 3.5, 0.25, 'tendon', { win: 'quad' });
      bone('achilles', s, 'kn' + s, [0, -92, -22], [0, -158, -20], 7.5, 5, 0.28, 'tendon', { blend: ['kn' + s, 'an' + s, 0.55, 1], b: ['an' + s, 0, -22, -22] });
    });
    bone('sacrum', null, 'hips', [0, 34, -26], [0, -6, -22], 18, 10, 0.4);
    for (var i = 0; i < 9; i++) bone('vertebra' + i, null, i < 3 ? 'hips' : i < 6 ? 'spine' : 'chest', [0, 36 + i * 24 - (i < 3 ? 0 : i < 6 ? 70 : 150), -26], [0, 36 + i * 24 - (i < 3 ? 0 : i < 6 ? 70 : 150) + 11, -26], 11, 9, 0.5);
    return out;
  }
  var INNER_VERT_DECL = 'attribute float aFib;\nvarying float vFib;\nvarying vec3 vBind;\nuniform vec3 uOff;\n';
  var INNER_FRAG_DECL = [
    'varying float vFib; varying vec3 vBind; uniform float uLayer; uniform float uFibre;',
    'uniform vec3 uWc[' + NWIN + ']; uniform mat3 uWm[' + NWIN + ']; uniform vec4 uWo[' + NWIN + '];'
  ].join('\n') + '\n';
  var INNER_FRAG_BODY = [
    'if (uLayer > 0.5 && uLayer < 1.5) { for (int wi = 0; wi < ' + NWIN + '; wi++) { if (uWo[wi].y > 0.001) { float we = length(uWm[wi] * (vBind - uWc[wi])); if (we < uWo[wi].y * 0.84) discard; } } }',
    'diffuseColor.rgb *= 1.0 - uFibre * (0.5 + 0.5 * sin(vFib * 6.2831853 * 9.0));'
  ].join('\n') + '\n';

  function loftSpindleGeo(prim, rows, seg, forceRw, forceRt) {
    var pos = [], fib = [], idx = [], uu = [], A0 = prim.A, ax = prim.ax, wd = prim.wd, td = prim.td, L = prim.L, pw = prim.pw;
    var rw = forceRw || prim.rw, rt = forceRt || prim.rt;
    for (var r = 0; r <= rows; r++) {
      var u = r / rows, qv = 1 - (2 * u - 1) * (2 * u - 1), prof = Math.pow(Math.max(qv, 0), pw);
      for (var sg = 0; sg < seg; sg++) {
        var th = sg / seg * Math.PI * 2, cw = Math.cos(th) * rw * prof, ct = Math.sin(th) * rt * prof, s0 = u * L;
        pos.push(A0[0] + ax[0] * s0 + wd[0] * cw + td[0] * ct, A0[1] + ax[1] * s0 + wd[1] * cw + td[1] * ct, A0[2] + ax[2] * s0 + wd[2] * cw + td[2] * ct);
        fib.push(sg / seg); uu.push(u);
      }
    }
    for (var r2 = 0; r2 < rows; r2++) for (var s2 = 0; s2 < seg; s2++) {
      var a = r2 * seg + s2, b = r2 * seg + (s2 + 1) % seg, c = (r2 + 1) * seg + s2, d = (r2 + 1) * seg + (s2 + 1) % seg;
      idx.push(a, c, b, b, c, d);
    }
    return { pos: pos, fib: fib, u: uu, idx: idx };
  }
  /** Pull every point inside the skin envelope: the skin SDF must be <= -inset there. This is what makes "muscle outside the skin" impossible. */
  function fitInside(G, pos, inset) {
    for (var i = 0; i < pos.length; i += 3) {
      for (var it = 0; it < 4; it++) {
        var d = gridAt(G, pos[i], pos[i + 1], pos[i + 2]);
        if (d <= -inset) break;
        var gr = gridGrad(G, pos[i], pos[i + 1], pos[i + 2]), k = d + inset;
        pos[i] -= gr[0] * k; pos[i + 1] -= gr[1] * k; pos[i + 2] -= gr[2] * k;
      }
    }
  }

  function buildInternal(body, ctx) {
    var data = body.data, G = data.G, bb = ctx.boneBind, boneIdx = ctx.boneIndex, bone = ctx.bone, root = ctx.root, S = ctx.S, V3 = THREE.Vector3;
    var rctx = { joints: data.joints, armAxis: data.armAxis };
    var group = new THREE.Group(); group.name = 'inner'; root.add(group);
    var WU = body.uniforms;
    var innerMats = [];
    function innerMat(color, layer, fibre) {
      var m = T3.material(color, { side: THREE.DoubleSide });
      var U = { uOff: { value: new THREE.Vector3() }, uLayer: { value: layer }, uFibre: { value: layer === 3 ? 0 : (fibre === undefined ? 0.10 : fibre) }, uWc: WU.uWc, uWm: WU.uWm, uWo: WU.uWo };
      m.onBeforeCompile = function (sh) {
        for (var k in U) sh.uniforms[k] = U[k];
        sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\n' + INNER_VERT_DECL)
          .replace('#include <begin_vertex>', '#include <begin_vertex>\n  vFib = aFib; vBind = position; transformed += uOff;');
        sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\n' + INNER_FRAG_DECL)
          .replace('#include <color_fragment>', '#include <color_fragment>\n' + INNER_FRAG_BODY);
      };
      m.customProgramCacheKey = function () { return 'tibi-inner-1'; };
      m.userData.U = U; innerMats.push(m);
      return m;
    }
    function makeMesh(parts, material, name) {
      // parts: [{pos, fib, idx, si, sw}] merged into one skinned mesh
      var P = [], Fb = [], I = [], SI = [], SW = [], off = 0;
      parts.forEach(function (pt) {
        for (var i = 0; i < pt.pos.length; i++) P.push(pt.pos[i]);
        for (var j = 0; j < pt.fib.length; j++) Fb.push(pt.fib[j]);
        for (var k = 0; k < pt.idx.length; k++) I.push(pt.idx[k] + off);
        for (var q = 0; q < pt.si.length; q++) { SI.push(pt.si[q]); SW.push(pt.sw[q]); }
        off += pt.pos.length / 3;
      });
      var geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
      geo.setAttribute('aFib', new THREE.Float32BufferAttribute(Fb, 1));
      geo.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(SI, 4)); geo.setAttribute('skinWeight', new THREE.Float32BufferAttribute(SW, 4));
      geo.setIndex(I); geo.computeVertexNormals();
      var mesh = new THREE.SkinnedMesh(geo, material); mesh.name = name; mesh.frustumCulled = false; group.add(mesh); mesh.bind(ctx.skeleton, mesh.matrixWorld);
      return mesh;
    }
    function weightsFor(pos, fn) {
      var n = pos.length / 3, si = [], sw = [];
      for (var i = 0; i < n; i++) {
        var wl = fn(i, pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]).slice().sort(function (a, b) { return b[1] - a[1]; });
        for (var q = 0; q < 4; q++) { si.push(q < wl.length ? boneIdx[wl[q][0]] : 0); sw.push(q < wl.length ? wl[q][1] : 0); }
      }
      return { si: si, sw: sw };
    }
    var meshes = { muscles: [], bones: [], tendons: [] };
    // ---- muscles: one mesh per (key, side), loft of the table's own spindle, pulled inside the skin
    var byKey = {};
    data.masked.forEach(function (m) { var k = m.key + '@' + (m.side || '') + '@' + m.layer; (byKey[k] = byKey[k] || []).push(m); });
    body.groups = {};
    Object.keys(byKey).forEach(function (k) {
      var list = byKey[k], first = list[0], layer = first.layer;
      var parts = list.map(function (m) {
        var lo = loftSpindleGeo(m.prim, 14, 14);
        fitInside(G, lo.pos, layer === 1 ? 2.6 : 5);
        var w = weightsFor(lo.pos, function (i, x, y, z) { return regionWeights(m.region, x, y, z, rctx); });
        lo.si = w.si; lo.sw = w.sw; return lo;
      });
      var flat = /^(glute|glutemed|pec|lat|trap|oblique|serratus)$/.test(first.key);          // flat fans: stripes converge into rings at the poles, so none
      var mat0 = innerMat(layer === 1 ? LOOK.muscle : LOOK.muscleDeep, layer, flat ? 0 : 0.10);
      var mesh = makeMesh(parts, mat0, 'muscle-' + k);
      var grp = { key: first.key, side: first.side, layer: layer, mesh: mesh, material: mat0, base: new THREE.Color(layer === 1 ? LOOK.muscle : LOOK.muscleDeep), recs: [], offDir: null };
      body.groups[k] = grp; meshes.muscles.push(grp);
    });
    body.recs.forEach(function (r) { var g2 = body.groups[r.key + '@' + (r.side || '') + '@' + r.layer]; if (g2) g2.recs.push(r); });
    // ---- bones and tendons
    var specs = innerSpecs(S, ctx.g), boneMat = innerMat(LOOK.bone, 3), tendonMat = innerMat(LOOK.tendon, 3);
    var boneParts = [], tendonParts = [], frontParts = [];
    specs.forEach(function (sp) {
      var ba = bb[sp.a[0]], bb2 = bb[sp.b[0]];
      var A0 = new V3(sp.a[1], sp.a[2], sp.a[3]).applyMatrix4(ba), B0 = new V3(sp.b[1], sp.b[2], sp.b[3]).applyMatrix4(bb2);
      var axv = B0.clone().sub(A0).normalize();
      var rot = new THREE.Matrix3().setFromMatrix4(ba);
      var wd = new V3(1, 0, 0).applyMatrix3(rot), td = new V3(0, 0, 1).applyMatrix3(rot);
      var fr = frame(axv.toArray(), wd.toArray(), td.toArray());
      var prim = makeSpindle(A0.toArray(), B0.toArray(), fr[1], fr[2], sp.rw, sp.rt, sp.pw);
      var lo = loftSpindleGeo(prim, 10, 12);
      fitInside(G, lo.pos, 2.5);
      var w = weightsFor(lo.pos, function (i) {
        if (sp.blend) { var u = lo.u[i], t = sstep(sp.blend[2], sp.blend[3], u); return [[sp.blend[0], 1 - t], [sp.blend[1], t]]; }
        return [[sp.rigid, 1]];
      });
      lo.si = w.si; lo.sw = w.sw;
      (sp.win ? frontParts : sp.kind === 'tendon' ? tendonParts : boneParts).push(lo);
    });
    // ribs: seven flattened rings on the chest bone
    var ribLo = [];
    for (var ri = 0; ri < 7; ri++) {
      var yy = 150 + 8 + ri * 14, wr = 54 - Math.abs(ri - 2) * 3.4 - (ri > 3 ? (ri - 3) * 2.5 : 0), geo = new THREE.TorusGeometry(1, 0.075, 8, 28), pa = geo.getAttribute('position'), pos = [], fib = [], idx = [];
      for (var vv = 0; vv < pa.count; vv++) { var tx = pa.getX(vv), ty = pa.getY(vv), tz = pa.getZ(vv); pos.push(tx * wr * 1.05, yy + tz * 20, ty * wr * 0.66 - 2); fib.push((vv % 8) / 8); }
      var ia = geo.getIndex(); for (var ii = 0; ii < ia.count; ii++) idx.push(ia.getX(ii));
      var rl = { pos: pos, fib: fib, idx: idx }; fitInside(G, rl.pos, 4);
      rl.si = []; rl.sw = []; for (var q4 = 0; q4 < pos.length / 3; q4++) { rl.si.push(boneIdx.chest, 0, 0, 0); rl.sw.push(1, 0, 0, 0); }
      ribLo.push(rl);
    }
    boneParts = boneParts.concat(ribLo);
    meshes.bones.push({ mesh: makeMesh(boneParts, boneMat, 'bones'), material: boneMat });
    meshes.tendons.push({ mesh: makeMesh(tendonParts, tendonMat, 'tendons'), material: tendonMat });
    // the kneecap and its tendon belong to the FRONT of the knee: they show only when the quad window is open (or in skeleton/layer views)
    meshes.front = [{ mesh: makeMesh(frontParts, innerMat(LOOK.bone, 3), 'knee-front') }];
    // ---- windows in bind space
    var wins = [];
    WINDOWS.forEach(function (w) {
      ['L', 'R'].forEach(function (s) {
        var sg = s === 'L' ? 1 : -1, bn = /^(sh|th|kn)$/.test(w.bone) ? w.bone + s : w.bone;
        var cc = new V3(w.c[0] * (w.mirror ? sg : 1), w.c[1], w.c[2]).applyMatrix4(bb[bn]), rot = new THREE.Matrix3().setFromMatrix4(bb[bn]);
        var e = rot.elements, rr = w.r;
        // rows of M are the window axes (bone frame axes in bind space) divided by the radii
        var M = new THREE.Matrix3().set(e[0] / rr[0], e[1] / rr[0], e[2] / rr[0], e[3] / rr[1], e[4] / rr[1], e[5] / rr[1], e[6] / rr[2], e[7] / rr[2], e[8] / rr[2]);
        wins.push({ name: w.name, side: s, c: cc, M: M, bone: bn });
      });
    });
    body.windowList = wins;
    body.inner = { group: group, meshes: meshes, materials: innerMats };
    group.visible = false;
    return body.inner;
  }

  // ------------------------------------------------------------------ attach: build one figure's skin and muscle records
  /**
   * A.attach(ctx): ctx = {root, bone, bones, skeleton, S, g, joints, boneBind, boneIndex, skinColor}.
   * Returns {muscles, skin, update(R, p, pre), roles(acts), anchor(name), windows, setWindow(name, open0, open1)}.
   */
  A.attach = function (ctx) {
    var data = A.buildData(ctx), n = data.n, root = ctx.root, bone = ctx.bone, g = ctx.g;
    var pos0 = new Float32Array(n * 3); for (var i = 0; i < n * 3; i++) pos0[i] = data.mesh.pos[i];
    var pos = new Float32Array(pos0), colS = new Float32Array(n * 3), colC = new Float32Array(n * 3);
    var skinCol = col3(C.skin), muscleCol = col3(C.muscle), toneCol = skinCol.clone().lerp(muscleCol, LOOK.tone), shortCol = col3(C.short);
    var faceCol = col3(C.face), hairCol = col3(C.hair);
    var restS = new Float32Array(n * 3), restC = new Float32Array(n * 3), tmp = new THREE.Color();
    for (var v = 0; v < n; v++) {
      tmp.copy(skinCol).lerp(muscleCol, LOOK.tone * data.toneMax[v]);
      var pi = data.patchIdx[v];
      if (pi) { var pc = data.patches[pi - 1].tone; tmp.lerp(pc === C.face ? faceCol : pc === C.hair ? hairCol : col3(pc), data.patchW[v]); }
      restS[v * 3] = tmp.r; restS[v * 3 + 1] = tmp.g; restS[v * 3 + 2] = tmp.b;
      restC[v * 3] = shortCol.r; restC[v * 3 + 1] = shortCol.g; restC[v * 3 + 2] = shortCol.b;
    }
    colS.set(restS); colC.set(restC);
    var geo = new THREE.BufferGeometry();
    var posAttr = new THREE.BufferAttribute(pos, 3), colAttr = new THREE.BufferAttribute(colS, 3), colCAttr = new THREE.BufferAttribute(colC, 3);
    posAttr.setUsage(THREE.DynamicDrawUsage); colAttr.setUsage(THREE.DynamicDrawUsage); colCAttr.setUsage(THREE.DynamicDrawUsage);
    geo.setAttribute('position', posAttr);
    geo.setAttribute('normal', new THREE.BufferAttribute(data.normals, 3));
    geo.setAttribute('color', colAttr); geo.setAttribute('colorC', colCAttr);
    geo.setAttribute('aCav', new THREE.BufferAttribute(data.cav, 1));
    geo.setAttribute('skinIndex', new THREE.BufferAttribute(data.skinIndex, 4));
    geo.setAttribute('skinWeight', new THREE.BufferAttribute(data.skinWeight, 4));
    geo.setIndex(new THREE.BufferAttribute(new Uint32Array(data.mesh.idx), 1));
    var skinMat = T3.material('#FFFFFF', { vertexColors: true, side: THREE.DoubleSide });
    var WU = winUniforms();
    var U = { uCloth: { value: new THREE.Vector4(CLOTH.waist, CLOTH.band, CLOTH.hem, CLOTH.lat) }, uTop: { value: new THREE.Vector4(CLOTH.topLo, CLOTH.topHi, CLOTH.topX, data.hasTop ? 1 : 0) },
      uHip: { value: new THREE.Vector3(data.hipL[0], data.hipL[1], data.hipL[2]) }, uLegAx: { value: new THREE.Vector3(data.legAx[0], data.legAx[1], data.legAx[2]) },
      uBand: { value: col3(C.band) }, uCrease: { value: LOOK.crease }, uInterior: { value: col3(LOOK.interior) }, uRim: { value: col3(LOOK.rim) }, uRimW: { value: 0.045 },
      uWc: WU.uWc, uWm: WU.uWm, uWo: WU.uWo };
    skinMat.onBeforeCompile = function (sh) {
      for (var k in U) sh.uniforms[k] = U[k];
      sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\n' + SKIN_VERT_DECL)
        .replace('#include <begin_vertex>', '#include <begin_vertex>\n  vColC = colorC; vCav = aCav; vBind = position;');
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\n' + SKIN_FRAG_DECL)
        .replace('#include <color_fragment>', '#include <color_fragment>\n' + SKIN_FRAG_BODY);
    };
    skinMat.customProgramCacheKey = function () { return 'tibi-skin-1'; };
    var skin = new THREE.SkinnedMesh(geo, skinMat); skin.name = 'skin'; skin.frustumCulled = false;
    root.add(skin); skin.bind(ctx.skeleton, skin.matrixWorld);

    // ---- muscle records: one per table entry that can light up; vertex lists from the top-4 masks
    var recs = [];
    data.masked.forEach(function (m) {
      var local = m.local, rec = { key: m.key, side: m.side, bone: m.bone, spec: m, slot: m.slot, level: 0, act: 0, bulge: 0, local: local, layer: m.layer, cloth: !!m.cloth,
        color: new THREE.Color(), colorC: new THREE.Color(), rest: toneCol.clone(), restC: shortCol.clone(), vi: [], vw: [], mid: new THREE.Color(), midC: new THREE.Color(), full: new THREE.Color() };
      recs.push(rec);
    });
    for (var v2 = 0; v2 < n; v2++) for (var q = 0; q < 8; q++) { var w = data.muw[v2 * 8 + q]; if (w > 0.02) { var r = recs[data.mus[v2 * 8 + q]]; r.vi.push(v2); r.vw.push(w); } }
    recs.forEach(function (r) {
      r.vi = new Int32Array(r.vi); r.vw = new Float32Array(r.vw); r.color.copy(r.rest); r.colorC.copy(r.restC);
      // anchor = the surface vertex nearest the weighted centre of the muscle's skin region (it rides the skin, so a label pinned to it stays ON the muscle)
      var cx = 0, cy = 0, cz = 0, cw = 0, k;
      for (k = 0; k < r.vi.length; k++) { var vv = r.vi[k] * 3, ww = r.vw[k]; cx += pos0[vv] * ww; cy += pos0[vv + 1] * ww; cz += pos0[vv + 2] * ww; cw += ww; }
      cx /= cw || 1; cy /= cw || 1; cz /= cw || 1;
      var bestD = 1e18; r.anchorVertex = r.vi.length ? r.vi[0] : 0;
      for (k = 0; k < r.vi.length; k++) { var v5 = r.vi[k] * 3; if (r.vw[k] < 0.6) continue; var dd = (pos0[v5] - cx) * (pos0[v5] - cx) + (pos0[v5 + 1] - cy) * (pos0[v5 + 1] - cy) + (pos0[v5 + 2] - cz) * (pos0[v5 + 2] - cz); if (dd < bestD) { bestD = dd; r.anchorVertex = r.vi[k]; } }
      var inv = new THREE.Matrix4().copy(ctx.boneBind[r.bone]).invert();
      r.aLocal = new THREE.Vector3().fromArray(r.spec.A).applyMatrix4(inv); r.bLocal = new THREE.Vector3().fromArray(r.spec.B).applyMatrix4(inv);
    });
    function paint(r) {
      var full = r.level ? col3(ROLE_COLOR[r.level]) : null;
      if (!full) { r.full.copy(r.rest); r.mid.copy(r.rest); r.midC.copy(r.restC); return; }
      r.full.copy(full);
      r.mid.copy(full).lerp(col3('#FFFFFF'), 0.32);                 // skin variant: through a pale tint of the role
      r.midC.copy(full).multiplyScalar(0.62);                       // under cloth: through a deep role colour (a pale tint flashed on the dark shorts)
    }
    recs.forEach(paint);
    var dynamics = {
      biceps: function (r, R) { return 5.5 * flex(R, r.side); }, triceps: function (r, R) { return -2.0 * flex(R, r.side); },
      lat: function (r, R) { return 5.5 * clamp(R('sh' + r.side) / 120, 0, 1); },
      calf: function (r, R) { var k = clamp(R('hl' + r.side) / 40, 0, 1); return (r.key === 'soleus' ? 2.2 : 4.2) * k; }
    };
    function flex(R, side) { return Math.min(150, Math.max(0, bone['el' + side].rotation.x * -1 / D2R)) / 150; }
    var lastSig = '';
    var body = { data: data, skin: skin, muscles: recs, recs: recs, geo: geo, material: skinMat, uniforms: U, inner: null };

    body.ensureInner = function () { if (!body.inner) buildInternal(body, ctx); return body.inner; };
    /**
     * Views (pure functions of the pose dictionary, so they animate like any other track): cut.<window>[@L|@R] 0 closed, 1 skin out, 2 superficial
     * muscle out; hi.<muscle> highlights one muscle inside the body (view.effort 1 lets activation colour it instead); view.ghost 0..1 fades the skin; view.layer 1 shows the whole muscle layer; view.skel 1 shows bones only; iso.<muscle> floats one muscle
     * beside its place (use with view.ghost so the body is still there).
     */
    var ISO_DIST = 150, lastView = '';
    function views(R, p, pre) {
      var ghost = p[pre + 'view.ghost'] || 0, skel = p[pre + 'view.skel'] || 0, anyIso = false, wlist = [], k;
      for (k in p) {
        if (k.indexOf(pre + 'cut.') === 0 && p[k] > 0.001) wlist.push(k.slice((pre + 'cut.').length));
        if (k.indexOf(pre + 'iso.') === 0 && p[k] > 0.001) anyIso = true;
      }
      var layerV = p[pre + 'view.layer'] || 0, need = wlist.length > 0 || ghost > 0 || skel > 0 || anyIso || layerV > 0;
      if (!need) {
        if (body.inner && body.inner.group.visible) { body.inner.group.visible = false; WU_clear(); skinMat.transparent = false; skinMat.opacity = 1; skinMat.depthWrite = true; skinMat.side = THREE.DoubleSide; lastView = ''; }
        return;
      }
      body.ensureInner();
      var wl = body.windowList, slot = 0;
      WU_clear();
      wl.forEach(function (w) {
        var open = p[pre + 'cut.' + w.name + '@' + w.side]; if (open === undefined) open = p[pre + 'cut.' + w.name];
        if (!(open > 0.001) || slot >= NWIN) return;
        U.uWc.value[slot].copy(w.c); U.uWm.value[slot].copy(w.M); U.uWo.value[slot].set(Math.min(1, open), Math.max(0, Math.min(1, open - 1)), 0, 0); slot++;
      });
      body.inner.group.visible = true;
      // ghost skin: translucent, no depth write, front faces only (so the inside of the shell does not double-draw)
      var wasGhost = skinMat.transparent;
      skinMat.transparent = ghost > 0.001; skinMat.opacity = 1 - (skel > 0.001 ? 0.95 : 0.9) * ghost; skinMat.depthWrite = !(ghost > 0.3); skinMat.side = ghost > 0.001 ? THREE.FrontSide : THREE.DoubleSide;
      if (wasGhost !== skinMat.transparent) skinMat.needsUpdate = true;
      // What is drawn is chosen, never accidental: bones with a cut, with view.skel, or behind an isolated muscle on a ghosted body;
      // muscles with a cut window (only where it opens), view.layer (the whole muscle layer), or one at a time with iso.<muscle>.
      var showBones = wlist.length > 0 || skel > 0 || layerV > 0 || (anyIso && ghost > 0);
      body.inner.meshes.bones.forEach(function (b) { b.mesh.visible = showBones; });
      body.inner.meshes.tendons.forEach(function (b) { b.mesh.visible = showBones && skel <= 0.001; });
      var quadOpen = wlist.some(function (n) { return n.indexOf('quad') === 0; });
      body.inner.meshes.front.forEach(function (b) { b.mesh.visible = quadOpen || skel > 0 || layerV > 0; });
      body.inner.meshes.muscles.forEach(function (g2) {
        var iso = p[pre + 'iso.' + g2.key + '@' + g2.side]; if (iso === undefined) iso = p[pre + 'iso.' + g2.key]; iso = iso || 0;
        var sg = g2.side === 'R' ? -1 : 1;
        g2.mesh.visible = (wlist.length > 0 || layerV > 0 || iso > 0.001) && !(skel > 0.001 && layerV <= 0 && iso <= 0.001 && wlist.length === 0);
        g2.material.userData.U.uOff.value.set(sg * ISO_DIST * iso, 0, 0);
        // Inside the body colour means one thing at a time. A muscle is highlighted ONLY when asked (hi.<muscle>, coral), or when the film opts in
        // to showing effort under the skin (view.effort 1: the role colour follows the muscle's activation). Otherwise the anatomy stays calm
        // rosewood, so a lesson about structure never inherits the effort colours of the exercise running under it.
        var hi = p[pre + 'hi.' + g2.key + '@' + g2.side]; if (hi === undefined) hi = p[pre + 'hi.' + g2.key]; hi = hi || 0;
        var effort = p[pre + 'view.effort'] || 0, act = g2.recs.length ? g2.recs[0].act : 0, lv = g2.recs.length ? g2.recs[0].level : 0;
        var prime = col3(ROLE_COLOR[3]);
        if (hi > 0.001) ramp(g2.material.color, g2.base, prime.clone().lerp(col3('#FFFFFF'), 0.32), prime, hi);
        else if (effort > 0.001 && lv && act > 0) ramp(g2.material.color, g2.base, col3(ROLE_COLOR[lv]).lerp(col3('#FFFFFF'), 0.32), col3(ROLE_COLOR[lv]), act * effort);
        else g2.material.color.copy(g2.base);
      });
    }
    function WU_clear() { for (var i = 0; i < NWIN; i++) U.uWo.value[i].set(0, 0, 0, 0); }
    body.update = function (R, p, pre) {
      var sig = [];
      recs.forEach(function (r) {
        var amt = p[pre + 'act.' + r.key]; if (amt === undefined) amt = p[pre + 'act.' + r.key + '@' + r.side];
        r.act = amt === undefined ? 0 : amt;
        r.bulge = r.spec.dyn ? dynamics[r.spec.dyn](r, R) : 0;
        ramp(r.color, r.rest, r.mid, r.full, r.level ? r.act : 0);
        ramp(r.colorC, r.restC, r.midC, r.full, r.level ? r.act : 0);
        sig.push(r.color.r.toFixed(3), r.color.g.toFixed(3), r.colorC.r.toFixed(3), r.bulge.toFixed(2));
      });
      views(R, p, pre);
      var s = sig.join(',');
      if (s === lastSig) return false;
      lastSig = s;
      colS.set(restS); colC.set(restC); pos.set(pos0);
      recs.forEach(function (r) {
        var dr = r.color.r - r.rest.r, dg = r.color.g - r.rest.g, db = r.color.b - r.rest.b;
        var cr = r.colorC.r - r.restC.r, cg = r.colorC.g - r.restC.g, cb = r.colorC.b - r.restC.b;
        var colorOn = dr || dg || db || cr || cg || cb, vi = r.vi, vw = r.vw, nn = vi.length;
        if (colorOn) for (var k = 0; k < nn; k++) {
          var v3 = vi[k] * 3, w = vw[k];
          colS[v3] += w * dr; colS[v3 + 1] += w * dg; colS[v3 + 2] += w * db; colC[v3] += w * cr; colC[v3 + 1] += w * cg; colC[v3 + 2] += w * cb;
        }
        if (r.bulge) for (var k2 = 0; k2 < nn; k2++) {
          var v4 = vi[k2] * 3, b = r.bulge * vw[k2];
          pos[v4] += data.normals[v4] * b; pos[v4 + 1] += data.normals[v4 + 1] * b; pos[v4 + 2] += data.normals[v4 + 2] * b;
        }
      });
      colAttr.needsUpdate = true; colCAttr.needsUpdate = true; posAttr.needsUpdate = true;
      return true;
    };
    body.roles = function (acts) {
      recs.forEach(function (r) {
        var lv = acts[r.key] || acts[r.key + '@' + r.side] || 0;
        if (!lv && /^delt-/.test(r.key)) lv = acts.delt || 0;
        if (!lv && r.key === 'brach' && acts.brachialis) lv = acts.brachialis;
        r.level = lv; paint(r);
      });
      lastSig = '';
    };
    /** World position (root frame) of the skin surface at a muscle's anchor vertex: pins ride the skin, through bulges and joint deformation. */
    var skinTmp = new THREE.Vector3();
    body.surfacePoint = function (rec, out) {
      skinTmp.set(posAttr.getX(rec.anchorVertex), posAttr.getY(rec.anchorVertex), posAttr.getZ(rec.anchorVertex));
      skin.applyBoneTransform(rec.anchorVertex, skinTmp);
      return out.copy(skinTmp).applyMatrix4(skin.matrixWorld);
    };
    /** Bone-local anchor of a named muscle ('biceps@L'): the record. The film overlays pin labels to it. */
    body.anchorOf = function (name) {
      var k = name.split('@')[0], sd = name.split('@')[1];
      for (var i = 0; i < recs.length; i++) if (recs[i].key === k && (!sd || recs[i].side === sd)) return recs[i];
      return null;
    };
    return body;
  };
})(typeof window !== 'undefined' ? window : globalThis);
