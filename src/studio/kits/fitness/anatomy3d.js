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
 *             meshed once (surface nets) into ONE connected, closed skinned surface in an A-pose bind. Muscle
 *             definition is relief of that surface (a fillet, never a separate shape). Shorts are a colour region with a
 *             sub-4-unit hem step, not a second shell. Hands and head are in the same surface.
 *   2. ACTIVATION  each skin vertex stores the weight of the (up to four) muscles whose volume it lies on. A highlight is a
 *             colour delta on those vertices, so it follows the surface, blends with soft edges and moves with the skin.
 *             A bulge is a displacement of the same vertices along their normals (biceps swell, calf contracts).
 *   3. CUTAWAY  the same muscle table is lofted into internal muscle meshes (layer 1 superficial, layer 2 deep), plus
 *             tendons and bones (layer 3), every vertex pushed inside the skin by construction. A cut window is an
 *             ellipsoid in BIND space evaluated per fragment on the skin (and on layer 1), so it stays registered to the
 *             anatomy in any pose. Isolated mode offsets chosen muscles in bind space (before skinning) next to a ghosted body.
 *   4. TESTS  scripts/anatomy3d-check.js: closed connected skin, scoped containment/layer checks, shoulder contours and arm clearance.
 *             Connectivity does not prove a convincing silhouette or biomechanical accuracy; inspect normal and clay frames.
 *
 * Everything is deterministic (no Math.random, no clock). Everything except the three small shader patches runs in node.
 */
(function (global) {
  'use strict';
  var Studio = global.Studio || (global.Studio = {});
  var F = Studio.kit && Studio.kit.fitness, THREE = global.THREE, T3 = F && F.t3d;
  if (!T3) throw new Error('kits/fitness/anatomy3d.js needs tibi3d.js loaded first');
  // 1.4.0: flatter profiled gluteus maximus, shape-following effort colour and garment tint, cut shells hide their inside, narrower female deltoid, wider shoulder blend.
  //        + opt-in A.shade(fig, 'crescent') (2D-vs-3D look prototype; the default 'toon' path is unchanged).
  // 1.5.0: effort weights peak at 1 and garment tints keep the role's chroma; the top's tint reads through the bust (no ring); hip delta mush and true posed normals in a hinge; cloth/windows on rest positions.
  // 1.6.0: the skin around each shoulder shares the chest's weight with the girdle bone (gdL/gdR, Tibi 0.8.0): GIRDLE_WEIGHTS.
  var A = T3.anatomy = { version: '1.6.0' };
  var D2R = Math.PI / 180, C = T3.colors;

  // ------------------------------------------------------------------ look (state language: see character-guidelines.md)
  /*
   * External skin is cobalt. A working muscle glows on the SURFACE in its role colour (coral prime mover, marigold secondary,
   * pale cobalt stabiliser). Anything INSIDE the body uses a different, warm family so the viewer never confuses "this muscle is
   * working" with "this is what is under the skin": rosewood for muscle, ivory for tendon and bone, a cream section line where
   * the skin was cut. Only the muscle the film is about turns coral inside the cutaway.
   */
  var LOOK = A.look = {
    tone: 0.22, legacyTone: 0.5,
    crease: 0.10, legacyCrease: 0.24,
    interior: '#8B565A',                      // inside of the shell (connective tissue), seen only through a cut window: warm, never a navy void
    rim: '#F6EFE0',                           // the cut edge of the skin (a section line)
    muscle: '#C98A82', muscleDeep: '#A8645F', muscleShade: '#7C3F45',
    tendon: '#F3E7CF', bone: '#E3D5B6', boneShade: '#BFB08C'
  };
  var surfaceGradientMap = null;
  function surfaceGradient() {
    if (!surfaceGradientMap) {
      // Nearest-sampled four-band light hides shallow anatomy; soften the same toon language.
      surfaceGradientMap = new THREE.DataTexture(new Uint8Array([70, 70, 70, 70, 70, 70, 70, 70, 80, 100, 124, 150, 179, 207, 233, 255]), 16, 1, THREE.RedFormat);
      surfaceGradientMap.minFilter = surfaceGradientMap.magFilter = THREE.LinearFilter;
      surfaceGradientMap.generateMipmaps = false; surfaceGradientMap.needsUpdate = true;
    }
    return surfaceGradientMap;
  }

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
  function sampleKeys(keys, n, byDistance) {
    var out = [], m = keys.length;
    for (var i = 0; i < n; i++) {
      var u = n === 1 ? 0 : i / (n - 1) * (m - 1), k = Math.min(m - 2, Math.floor(u)), t = u - k, row = [];
      if (byDistance) {
        // The tube samples this LUT by physical distance; its authored stations are not evenly spaced.
        var s = keys[0][0] + (n === 1 ? 0 : i / (n - 1)) * (keys[m - 1][0] - keys[0][0]);
        k = 0; while (k < m - 2 && s > keys[k + 1][0]) k++;
        t = (s - keys[k][0]) / (keys[k + 1][0] - keys[k][0]); row.push(s);
      }
      for (var c = byDistance ? 1 : 0; c < keys[0].length; c++) row.push(catmull(keys[Math.max(0, k - 1)][c], keys[k][c], keys[k + 1][c], keys[Math.min(m - 1, k + 2)][c], t));
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
    var n = 48, s0 = rows[0][0], s1 = rows[rows.length - 1][0], lut = sampleKeys(rows, n, o.profileSampling === 'distance'), p = o.p || 2;
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
  function muscleSection(profile, u, pw) {
    if (!profile) {
      var r = Math.pow(Math.max(0, 1 - (2 * u - 1) * (2 * u - 1)), pw);
      return [r, r];
    }
    for (var i = 0; i < profile.length - 1; i++) {
      if (u <= profile[i + 1][0]) {
        var a = profile[i], b = profile[i + 1], t = sstep(a[0], b[0], u);
        return [lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
      }
    }
    return profile[profile.length - 1].slice(1);
  }
  function makeSpindle(Apt, Bpt, wd, td, rw, rt, pw, profile) {
    var d = [Bpt[0] - Apt[0], Bpt[1] - Apt[1], Bpt[2] - Apt[2]], L = Math.sqrt(dot(d, d)), ax = [d[0] / L, d[1] / L, d[2] / L], m = Math.max(rw, rt);
    var prim = { kind: 'spindle', A: Apt, B: Bpt, ax: ax, wd: wd, td: td, rw: rw, rt: rt, pw: pw, L: L,
      profile: profile,
      box: [Math.min(Apt[0], Bpt[0]) - m - 2, Math.min(Apt[1], Bpt[1]) - m - 2, Math.min(Apt[2], Bpt[2]) - m - 2, Math.max(Apt[0], Bpt[0]) + m + 2, Math.max(Apt[1], Bpt[1]) + m + 2, Math.max(Apt[2], Bpt[2]) + m + 2] };
    prim.u = function (x, y, z) { return clamp(((x - Apt[0]) * ax[0] + (y - Apt[1]) * ax[1] + (z - Apt[2]) * ax[2]) / L, 0, 1); };
    prim.f = function (x, y, z) {
      var vx = x - Apt[0], vy = y - Apt[1], vz = z - Apt[2], s = vx * ax[0] + vy * ax[1] + vz * ax[2];
      if (s <= 0) return Math.sqrt(vx * vx + vy * vy + vz * vz);
      if (s >= L) { var bx = x - Bpt[0], by = y - Bpt[1], bz = z - Bpt[2]; return Math.sqrt(bx * bx + by * by + bz * bz); }
      var u = s / L, q = 1 - (2 * u - 1) * (2 * u - 1), prof = Math.pow(q, pw); if (prof < 0.03) prof = 0.03;
      var px = vx - ax[0] * s, py = vy - ax[1] * s, pz = vz - ax[2] * s;
      var xw = px * wd[0] + py * wd[1] + pz * wd[2], zt = px * td[0] + py * td[1] + pz * td[2];
      if (profile) {
        var section = muscleSection(profile, u, pw);
        return ellipseD(xw, zt, rw * Math.max(0.03, section[0]), rt * Math.max(0.03, section[1]));
      }
      return ellipseD(xw, zt, rw * prof, rt * prof);
    };
    return prim;
  }
  /*
   * Effort colour (refined body). floor: share of a muscle's coverage tinted away from its belly; cloth: how far the shorts or top move
   * toward a lifted role colour (clothLift of white) at full effort: a subdued tint of the role on the garment, never the full colour
   * and never a darkened one. A straight lerp from the navy shorts to the pure role colour read as a dark-red stain at every soft edge.
   * 1.5.0: lift 0.3 -> 0.15 and cloth 0.6 -> 0.65. With 0.3 of white the tint kept only 42-53% of the role's chroma and rendered as a
   * dusky brown (prime, secondary) or a grey-white smear (stabiliser) on the navy; now 60-70%, still darker and greyer than the role.
   * peak: every muscle's effort weight is normalised so its belly reaches the role colour at full activation.
   */
  var EFFORT = A.EFFORT = { floor: 0.2, cloth: 0.65, clothLift: 0.15, peak: true };
  /** 0..1: how central a point is in a spindle's footprint (1 along the belly's mid-line, 0 beyond its width or past its tendinous ends). */
  function bellyAt(prim, x, y, z) {
    var vx = x - prim.A[0], vy = y - prim.A[1], vz = z - prim.A[2], ax = prim.ax, wd = prim.wd;
    var s = vx * ax[0] + vy * ax[1] + vz * ax[2], u = s / prim.L;
    if (!(u > 0 && u < 1)) return 0;
    var prof = Math.pow(1 - (2 * u - 1) * (2 * u - 1), prim.pw), section = prim.profile ? muscleSection(prim.profile, u, prim.pw) : [prof, prof];
    var xw = (vx - ax[0] * s) * wd[0] + (vy - ax[1] * s) * wd[1] + (vz - ax[2] * s) * wd[2];
    // 1.5.0: full colour within 45% of the half-width (was 30%): the saturated core covered too little of the belly to read at feed size
    return sstep(1.2, 0.45, Math.abs(xw) / Math.max(1e-3, prim.rw * section[0])) * sstep(0, 0.55, Math.min(1, section[1]));
  }
  A._bellyAt = bellyAt;

  // ------------------------------------------------------------------ cloth region (shorts, waistband, sports top): shared maths
  var CLOTH = { waist: 58, band: 50, hem: 92, lat: 62, topLo: 150, topHi: 206, topX: 80, thick: 3.4, topThickness: 1.0 };
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
  function coreSpecs(S, g, joints, profileSampling) {
    var ms = S.mscale, f = g === 'f' ? 0.95 : 1, out = [];
    var refined = profileSampling === 'distance';
    var tube = { profileSampling: profileSampling };
    var tr = S.torso.map(function (r) { return [r[0] + 50, r[1] * 0.93, r[2] * 0.93, 0, r[3]]; });          // s = y + 50 along +y, cx = 0, cz = r[3]
    out.push({ id: 'torso', region: 'torso', prim: makeTube([0, -50, 0], [0, 1, 0], [1, 0, 0], [0, 0, 1], tr, { p: 2.3, profileSampling: profileSampling }) });
    out.push({ id: 'neck', region: 'torso', prim: makeTube([0, 0, 0], [0, 1, 0], [1, 0, 0], [0, 0, 1], [[236, 22, 22, 0, 0], [262, 21, 21, 0, 0], [292, 20, 21, 0, 2]], tube) });
    out.push({ id: 'head', region: 'head', prim: makeSpindle([0, 275, 4], [0, 379, 4], [1, 0, 0], [0, 0, 1], 43, 46, 0.5) });
    ['L', 'R'].forEach(function (sd) {
      var sg = sd === 'L' ? 1 : -1, J = joints['sh' + sd], ax = nrm([sg * Math.sin(ARM_A * D2R), -Math.cos(ARM_A * D2R), 0]), wd = nrm([Math.cos(ARM_A * D2R), sg * Math.sin(ARM_A * D2R), 0]);
      var armRows = refined ?
        [[-4, 8, 14, 0], [0, 13, 20, 0], [15, 22, 25, 4], [40, 24, 25, 5], [80, 21, 24, 3], [110, 18, 20, 1], [134, 17.5, 17, 0], [166, 20, 19, 0], [208, 14, 13, 0], [244, 10.5, 10, 0]] :
        [[-10, 24, 24], [0, 25.5, 25], [50, 20.5, 19.5], [134, 17.5, 17], [170, 18.5, 17.5], [226, 11.5, 10.5], [244, 10.5, 10]];
      var ak = armRows.map(function (k) { return [k[0], k[1] * ms, k[2] * ms, sg * (k[3] || 0) * ms, 0]; });
      out.push({ id: 'arm' + sd, region: 'arm' + sd, prim: makeTube(J, ax, wd, [0, 0, 1], ak, tube) });
      var H = joints['hip' + sd], lx = nrm([sg * Math.sin(LEG_B * D2R), -Math.cos(LEG_B * D2R), 0]), lw = nrm([Math.cos(LEG_B * D2R), sg * Math.sin(LEG_B * D2R), 0]);
      var legRows = refined ?
        // Rounded top: a full-radius flat end above the hip joint left a shelf at the side of the shorts.
        [[-26, 20, 24, 0], [-14, 30, 32, 0], [0, 35, 35.5, 0], [30, 36, 36, 0], [100, 31, 33, 0], [178, 23.5, 24.5, 0], [228, 22, 26, -4], [300, 15.5, 16.5, -2], [344, 12.5, 13.5, 0]] :
        [[-26, 36, 36, 0], [30, 35, 35, 0], [100, 29, 29.5, 0], [178, 23.5, 24.5, 0], [215, 20.5, 22, 0], [300, 15.5, 16.5, 0], [344, 12.5, 13.5, 0]];
      var lk = legRows.map(function (k) { return [k[0], k[1] * f, k[2] * f, 0, k[3] * f]; });
      out.push({ id: 'leg' + sd, region: 'leg' + sd, prim: makeTube(H, lx, lw, [0, 0, 1], lk, tube) });
    });
    return out;
  }

  /*
   * THE MUSCLE TABLE. Authored in bone-local frames exactly as the old ellipsoids were, so existing activation sets
   * (act.biceps, act.glute, ...) keep their meaning. c = centre, r = radii (x, y, z), rot = euler degrees, axis = which local axis is
   * the muscle's length, pw = belly shape, mask = [full, fade] in units outside the volume (how far its tint reaches on the skin),
   * layer 1 = superficial, 2 = deep, region = whose weights it skins with. noVol: a colour patch only (face, hair).
   */
  function muscleTable(S, g, refined) {
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
    if (refined !== false) refineMuscles(L, S, g);
    return L;
  }
  A.muscleTable = muscleTable;

  /*
   * Broad fans and shallow continuous bands, not the legacy ellipsoid ornaments.
   * Qualitative sources: OpenStax A&P 2e, sections 11.4-11.6;
   * https://www.ncbi.nlm.nih.gov/sites/books/NBK537056/ (deltoid);
   * https://www.elsevier.com/resources/anatomy/muscular-system/muscles-of-upper-limb/brachialis-muscle/18221.
   * The matching notes in assets/fitness/data/muscles.json distinguish anatomy
   * facts from these original, illustrative rig dimensions.
   */
  function refineMuscles(list, S, g) {
    var ms = S.mscale;
    var lowerTraps = [];
    var fan = [[0, 0, 0], [0.15, 0.5, 0.45], [0.45, 1, 0.9], [0.75, 0.8, 1], [0.92, 0.3, 0.6], [1, 0, 0]];
    // Sample rounded ends below mesh-cell spacing; sparse zero-ended ramps made pointed caps.
    var cap = [];
    for (var step = 0; step <= 32; step++) {
      var u = step / 32, round = Math.sqrt(4 * u * (1 - u)), broad = sstep(0, 0.6, u);
      cap.push([u, round * (0.25 + 0.75 * broad), round * (0.45 + 0.55 * broad)]);
    }
    // Female deltoid: the male cap scaled by mscale read broad and square on her narrower frame. A rounder head that tapers longer
    // into the insertion (a narrow V, widest high on the cap).
    var capF = [];
    for (var fs = 0; fs <= 32; fs++) {
      var fu = fs / 32, fround = Math.sqrt(4 * fu * (1 - fu));
      capF.push([fu, fround * (0.15 + 0.85 * sstep(0.05, 0.85, fu)), fround * (0.4 + 0.6 * sstep(0, 0.75, fu))]);
    }
    // Sternal end (u 0) broad, lateral end converging toward the humerus, both rounded: the sparse ramp made a horn at the armpit.
    var chest = [];
    for (var cs = 0; cs <= 32; cs++) {
      var cu = cs / 32, blunt = Math.pow(4 * cu * (1 - cu), 0.35), converge = sstep(0.35, 1, cu);
      chest.push([cu, blunt * lerp(1, 0.45, converge), blunt * lerp(1, 0.6, converge)]);
    }
    // Gluteus maximus, u 0 at the femoral insertion (low, lateral) to 1 at the sacral origin (high, medial): a broad sheet,
    // thickest in the lower-middle belly, tapering into the insertion. The 21-unit ellipsoid read as a ball. The thickness floor
    // (0.6 of the belly) keeps the sheet's edges thicker than a mesh cell: at 0.2 they were 1-3 units thick, below the 3.5-unit
    // surface-nets cell, and meshed as jagged creases at the lateral hip and the gluteal fold.
    var gluteFan = [];
    for (var gs = 0; gs <= 32; gs++) {
      var gu = gs / 32, gr = Math.sqrt(4 * gu * (1 - gu));
      gluteFan.push([gu, Math.sqrt(gr) * lerp(0.35, 1, sstep(0.05, 0.6, gu)) * (1 - 0.2 * sstep(0.7, 1, gu)), gr * (0.6 + 0.4 * Math.exp(-Math.pow((gu - 0.48) / 0.28, 2)))]);
    }
    var calf = [[0, 0, 0], [0.2, 0.45, 0.6], [0.42, 0.85, 1], [0.72, 1, 1], [0.9, 0.65, 0.7], [1, 0, 0]];
    var rectus = [[0, 0, 0], [0.22, 0.7, 0.5], [0.36, 1, 1], [0.43, 1, 0.5],
      [0.53, 1, 1], [0.6, 1, 0.5], [0.7, 1, 1], [0.78, 0.95, 0.5], [0.88, 0.8, 0.7], [1, 0, 0]];
    function set(m, c, r, rot, profile) {
      m.c = c; m.r = r.map(function (v) { return v * ms; });
      if (rot) m.rot = rot;
      if (profile) m.profile = profile;
    }
    var absSeen = {};
    for (var i = list.length - 1; i >= 0; i--) {
      var m = list[i], sg = m.side === 'R' ? -1 : 1;
      if (m.key === 'shoulder-ball') {
        m.key = 'shoulder-envelope'; m.bone = 'chest'; m.axis = 'x'; m.region = 'arm' + m.side;
        set(m, [sg * 68, 78, -2], [30, 12, 24], [0, 0, -sg * 30]);
      } else if (m.key === 'abs') {
        if (absSeen[m.side]) { list.splice(i, 1); continue; }
        absSeen[m.side] = true;
        set(m, [sg * 14.5, 26, 36.5], [13, 70, 6], [0, 0, 0], rectus);
        m.mask = [1, 9];
      } else if (m.key === 'lat') {
        set(m, [sg * 28, -15, -33], [26, 85, 6], [0, 0, -sg * 18], fan);
        m.dyn = undefined; m.mask = [1, 10];
      } else if (m.key === 'pec') {
        var p = sg > 0 ? chest : chest.map(function (row) { return [1 - row[0], row[1], row[2]]; }).reverse();
        set(m, [sg * 37, 35, 35], [43, 28, 11], [-12, sg * 14, sg * 20], p);
        m.mask = [1, 9];
      } else if (m.key === 'erector') {
        set(m, [sg * 15, 8, -31], [10, 62, 7]); m.mask = [0, 8];
      } else if (m.key === 'oblique') {
        set(m, [sg * 46, 22, 8], [13, 50, 17], [0, 0, sg * -12], fan);
        m.mask = [1, 9];
      } else if (m.key === 'trap') {
        set(m, [sg * 26, 84, -22], [36, 20, 8], [0, 0, -sg * 28]);
        m.axis = 'x'; m.mask = [1, 10];
        var lower = Object.assign({}, m);
        set(lower, [sg * 16, 26, -32], [22, 70, 6], [0, 0, sg * 10], fan);
        lower.axis = 'y'; lowerTraps.push(lower);
      } else if (m.key === 'serratus') {
        // A thin sheet on the rib wall, tilted with the flank; the old 10-unit lateral slab left a ledge under the arm.
        set(m, [sg * 70, 2, 6], [4, 30, 15], [0, 0, -sg * 22], fan);
        m.mask = [1, 9];
      } else if (m.key === 'glute') {
        // Same sacrum-to-femur frame as before, a third thinner, profiled, with a wider fillet (blend) into the hip and thigh.
        set(m, [-sg * 9, -18, -38], [38, 44, 13], [0, sg * 12, sg * 32], gluteFan);
        m.mask = [1, 10]; m.blend = 14;
      } else if (m.key === 'glutemed') {
        // Deep, under the gluteus maximus; a 24-unit lateral egg ending at the waistband read as a hip shelf.
        set(m, [sg * 50, 6, -26], [16, 30, 16], [0, 0, -sg * 15]);
      } else if (m.key === 'delt-front' || m.key === 'delt-rear') {
        if (g === 'f') set(m, [sg * 3, -34, m.key === 'delt-front' ? 10 : -10], [16, 36, 13], [0, 0, -sg * 5], capF);
        else set(m, [sg * 3, -34, m.key === 'delt-front' ? 11 : -11], [19, 36, 15], [0, 0, -sg * 5], cap);
        m.mask = [1, 10];
      } else if (m.key === 'delt-side') {
        if (g === 'f') set(m, [sg * 5, -36, 0], [21, 38, 21], [0, 0, -sg * 8], capF);
        else set(m, [sg * 8, -36, 0], [28, 38, 25], [0, 0, -sg * 8], cap);
        m.mask = [1, 10];
      } else if (m.key === 'palm') {
        set(m, [sg * 3, -22, 0], [16, 24, 10]);
      } else if (m.key === 'fingers') {
        set(m, [sg * 3, -45, 4], [14, 17, 9]);
      } else if (m.key === 'thumb') {
        set(m, [-sg * 11, -19, 8], [5.5, 15, 6], [0, 0, -sg * 25]);
      } else if (m.key === 'biceps') {
        set(m, [0, -64, 21], [18, 47, 10]); m.mask = [0, 9];
      } else if (m.key === 'triceps') {
        set(m, [0, -64, -16], [19, 49, 12]); m.mask = [0, 9];
      } else if (m.key === 'brach') {
        m.bone = 'sh' + m.side; m.layer = 2;
        set(m, [sg * -3, -106, 14], [12, 29, 5]); m.mask = [2, 11];
      } else if (m.key === 'flexor' || m.key === 'extensor') {
        set(m, [0, -34, m.key === 'flexor' ? 8 : -8], [16, 45, 10]);
        m.mask = [1, 9];
      } else if (m.key === 'quad' && m.layer === 1) {
        if (m.c[0] === 0) set(m, [0, -80, 24], [16, 78, 13]);
        else if (m.c[0] * sg > 0) set(m, [sg * 18, -90, 12], [17, 74, 15]);
        else set(m, [-sg * 14, -128, 14], [14, 44, 13]);
        m.mask = [1, 10];
      } else if (m.key === 'hams') {
        set(m, [m.c[0], m.c[1], -19], [16, 79, 13]); m.mask = [1, 10];
      } else if (m.key === 'adductor') {
        set(m, [-sg * 16, -86, 2], [12, 64, 15]); m.mask = [1, 9];
      } else if (m.key === 'calf' && m.bone.indexOf('kn') === 0) {
        set(m, [m.c[0], m.c[1], -19], [m.r[0] / ms, m.r[1] / ms, 12], null, calf);
        m.mask = [1, 10];
      } else if (m.key === 'soleus') {
        set(m, [0, -94, -12], [24, 60, 8]); m.mask = [2, 12];
      } else if (m.key === 'tibant') {
        set(m, [sg * 8, -62, 11], [10, 62, 10]); m.mask = [1, 9];
      }
    }
    Array.prototype.push.apply(list, lowerTraps);
    function section(rows, y) {
      if (y <= rows[0][0]) return rows[0];
      for (var j = 0; j < rows.length - 1; j++) if (y <= rows[j + 1][0]) {
        var a = rows[j], b = rows[j + 1], t = (y - a[0]) / (b[0] - a[0]);
        return [y, lerp(a[1], b[1], t), lerp(a[2], b[2], t), lerp(a[3], b[3], t)];
      }
      return rows[rows.length - 1];
    }
    list.forEach(function (m) {
      if (m.tone) return;
      var origin = { hips: 0, spine: 70, chest: 150 }[m.bone];
      if (origin !== undefined) {
        var reference = section(T3.SPEC.m.torso, origin + m.c[1]), actual = section(S.torso, origin + m.c[1]);
        var sx = actual[1] / reference[1], sz = actual[2] / reference[2];
        m.c[0] *= sx; m.c[2] = actual[3] + (m.c[2] - reference[3]) * sz;
        m.r[0] *= sx / ms; m.r[2] *= sz / ms;
      } else {
        var scale = /^(sh|el|hand)/.test(m.bone) ? ms : g === 'f' ? 0.95 : 1;
        m.c[0] *= scale; m.c[2] *= scale;
      }
      if (!m.part) m.r[1] /= ms;
    });
  }

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
    var out = regionStops(region, x, y, z, ctx);
    return ctx.girdle ? girdleSplit(out, region, x, y, z, ctx) : out;
  }
  function regionStops(region, x, y, z, ctx) {
    if (region === 'torso') return blendStops(-y, TORSO_STOPS);
    if (region === 'head') return [['head', 1]];
    var sd = region.charAt(region.length - 1);
    if (region.indexOf('leg') === 0) return blendStops(-y, [[-34, 'hips'], [2, 'th' + sd], [164, 'th' + sd], [204, 'kn' + sd], [400, 'kn' + sd]]);
    var J = ctx.joints['sh' + sd], ax = ctx.armAxis[sd], s = (x - J[0]) * ax[0] + (y - J[1]) * ax[1] + (z - J[2]) * ax[2];
    return blendStops(s, (ctx.armStops || ARM_STOPS)[sd]);
  }
  function armStops(c0, c1) {
    var out = {};
    ['L', 'R'].forEach(function (sd) { out[sd] = [[c0, 'chest'], [c1, 'sh' + sd], [118, 'sh' + sd], [150, 'el' + sd], [226, 'el' + sd], [246, 'hand' + sd]]; });
    return out;
  }
  var ARM_STOPS = armStops(-6, 14);
  /*
   * Refined: the chest-to-arm blend spans the deltoid's medial end. Abduction closes the angle on top of the shoulder; over the old
   * 20-unit blend the deltoid end rotated up as a wall beside the still trapezius (the ridge at 90 degrees). A wider blend bends that
   * skin as a ramp.
   */
  var SHOULDER_BLEND = A.SHOULDER_BLEND = [-30, 60];
  var ARM_STOPS_REFINED = armStops(SHOULDER_BLEND[0], SHOULDER_BLEND[1]);
  /*
   * Refined (1.6.0): the shoulder girdle. The skin over the acromion, the root of the deltoid, the lateral pectoralis and the back of
   * the shoulder follows the scapula and clavicle (bones gdL/gdR, posed by tibi3d.js from the arm: T3.GIRDLE) instead of the chest
   * alone, so the arm's rotation is shared by two blends (chest to girdle, girdle to arm) and neither folds flat. The girdle takes a
   * share of whatever weight the chest had: 1 inside `core` of an ellipsoid around the glenohumeral joint (bind space, radii
   * r = [medial, lateral, below, above, behind, in front]) and 0 at its surface; the arm's own root (the deltoid, the axillary folds)
   * hangs from the girdle entirely. Near the joint the arm's weight is shared with the soft-tissue frame (axL/axR, which IS the humerus
   * near the bind pose and trails it overhead or across the body): `tissue` [s0, s1] fades that share out along the arm's axis, so the
   * upper arm below s1 follows the bone. Every split is of a weight whose two bones coincide in the neutral stance, so with the arms
   * down the skin is where it was. The lat below the armpit stays on the chest: the girdle moves it only as far as the scapula does.
   * `below` is 70: trunk skin the girdle carries rigidly lifts off the ribcage under a raised arm (seen as "wings" behind and beside
   * the armpit, and the female top flaring out); at 90 that lift reached 37/51 units (overhead / overhead abduction, 99th pct, male),
   * at 70 27/40, at 60 the armpit skin crushed back to 5.8 units from the joint centre (anatomy3d-check armpitLift, shoulderCrush).
   */
  var GIRDLE_WEIGHTS = A.GIRDLE_WEIGHTS = { r: [50, 70, 70, 45, 40, 60], core: 0.7, edge: 1, armRoot: 1, tissue: [10, 50], tissueMax: 0.8 };
  function girdleShare(sd, x, y, z, J) {
    var r = GIRDLE_WEIGHTS.r, u = (sd === 'L' ? 1 : -1) * (x - J[0]), v = y - J[1], w = z - J[2];
    u /= u < 0 ? r[0] : r[1]; v /= v < 0 ? r[2] : r[3]; w /= w < 0 ? r[4] : r[5];
    return 1 - sstep(GIRDLE_WEIGHTS.core, GIRDLE_WEIGHTS.edge, Math.sqrt(u * u + v * v + w * w));
  }
  function girdleSplit(list, region, x, y, z, ctx) {
    if (region === 'head' || region.indexOf('leg') === 0) return list;
    var arm = region !== 'torso', sd = arm ? region.charAt(region.length - 1) : (x >= 0 ? 'L' : 'R'), J = ctx.joints['sh' + sd];
    var k = girdleShare(sd, x, y, z, J), out = [], T = GIRDLE_WEIGHTS.tissue, e = 0;
    if (arm) {
      k = Math.max(k, GIRDLE_WEIGHTS.armRoot);
      var ax = ctx.armAxis[sd], s = (x - J[0]) * ax[0] + (y - J[1]) * ax[1] + (z - J[2]) * ax[2];
      e = GIRDLE_WEIGHTS.tissueMax * (1 - sstep(T[0], T[1], s));
    }
    for (var i = 0; i < list.length; i++) {
      var nm = list[i][0], w = list[i][1];
      if (nm === 'chest' && k > 1e-4) {
        if (k < 1 - 1e-4) out.push(['chest', w * (1 - k)]);
        out.push(['gd' + sd, w * k]);
      } else if (nm === 'sh' + sd && e > 1e-4) {
        out.push(['ax' + sd, w * e]); out.push(['sh' + sd, w * (1 - e)]);
      } else out.push(list[i]);
    }
    return out;
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
        var b = pr.box, kp = pr.k || k, m = kp + h;
        var i0 = Math.max(0, Math.floor((b[0] - m - ox) / h)), i1 = Math.min(nx - 1, Math.ceil((b[3] + m - ox) / h));
        var j0 = Math.max(0, Math.floor((b[1] - m - oy) / h)), j1 = Math.min(ny - 1, Math.ceil((b[4] + m - oy) / h));
        var k0 = Math.max(0, Math.floor((b[2] - m - oz) / h)), k1 = Math.min(nz - 1, Math.ceil((b[5] + m - oz) / h));
        for (var kk = k0; kk <= k1; kk++) for (var jj = j0; jj <= j1; jj++) {
          var row = (kk * ny + jj) * nx;
          for (var ii = i0; ii <= i1; ii++) { var d = pr.f(ox + ii * h, oy + jj * h, oz + kk * h); g[row + ii] = smin(g[row + ii], d, kp); }
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

  // ------------------------------------------------------------------ skin-weight smoothing at the hip (refined)
  /*
   * Refined: skin weights around the gluteal fold and crotch are diffused over the surface. Region votes switch from the torso's
   * hips weight to the leg's thigh weight within one or two cells at the fold, so a deep squat stretched those triangles 4.4 times
   * their bind area. Diffusion spreads the same bend over a wider band. Box in bind space: |x| < xMax, yMin < y < yMax.
   */
  var HIP_WEIGHTS = A.HIP_WEIGHTS = { passes: 12, xMax: 90, yMin: -120, yMax: 30, rate: 0.5 };
  function smoothWeights(si, sw, adj, P, n, o) {
    var inBox = new Uint8Array(n), list = [];
    for (var v = 0; v < n; v++) if (Math.abs(P[v * 3]) < o.xMax && P[v * 3 + 1] > o.yMin && P[v * 3 + 1] < o.yMax) { inBox[v] = 1; list.push(v); }
    var cur = new Map(), i, j;
    function dict(v) { var d = {}; for (j = 0; j < 4; j++) if (sw[v * 4 + j] > 0) d[si[v * 4 + j]] = (d[si[v * 4 + j]] || 0) + sw[v * 4 + j]; return d; }
    for (i = 0; i < n; i++) if (inBox[i]) cur.set(i, dict(i));
    for (var pass = 0; pass < o.passes; pass++) {
      var next = new Map();
      list.forEach(function (v) {
        var acc = {}, own = cur.get(v), l = adj[v], k;
        for (k in own) acc[k] = (1 - o.rate) * own[k];
        for (var q = 0; q < l.length; q++) {
          var nd = inBox[l[q]] ? cur.get(l[q]) : dict(l[q]);
          for (k in nd) acc[k] = (acc[k] || 0) + o.rate * nd[k] / l.length;
        }
        next.set(v, acc);
      });
      cur = next;
    }
    list.forEach(function (v) {
      var d = cur.get(v), names = Object.keys(d).sort(function (a, b) { return d[b] - d[a] || a - b; }).slice(0, 4), s = 0;
      names.forEach(function (k) { s += d[k]; });
      for (j = 0; j < 4; j++) { si[v * 4 + j] = j < names.length ? +names[j] : 0; sw[v * 4 + j] = j < names.length ? d[names[j]] / s : 0; }
    });
  }
  // ------------------------------------------------------------------ build the body data for a gender (cached: pure geometry, no THREE objects)
  var DATA = {};
  function isMask(m) { return !m.part && !m.tone; }
  /**
   * ctx: {S, g, joints: {shL, shR, hipL, hipR: [x,y,z] in bind space}, boneBind: {name: THREE.Matrix4 (root frame, A-pose bind)}, boneIndex}.
   * Returns the shared, immutable data of the skin; every figure copies the dynamic arrays.
   */
  A.buildData = function (ctx) {
    var profileSampling = ctx.profileSampling || 'distance';
    var key = ctx.g + (profileSampling === 'legacy' ? '' : ':' + profileSampling);
    if (DATA[key]) return DATA[key];
    var S = ctx.S, g = ctx.g, bb = ctx.boneBind, joints = ctx.joints, boneIdx = ctx.boneIndex;
    var armAxis = { L: nrm([Math.sin(ARM_A * D2R), -Math.cos(ARM_A * D2R), 0]), R: nrm([-Math.sin(ARM_A * D2R), -Math.cos(ARM_A * D2R), 0]) };
    var rctx = { joints: joints, armAxis: armAxis, armStops: profileSampling === 'distance' ? ARM_STOPS_REFINED : null, girdle: profileSampling === 'distance' };
    var cores = coreSpecs(S, g, joints, profileSampling), table = muscleTable(S, g, profileSampling === 'distance');
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
      m.prim = makeSpindle(m.A, m.B, wd, td, ri[1], ri[2], m.pw, m.profile);
      if (m.blend) m.prim.k = m.blend;
      m.region = m.region || regionOfBone(m.bone);
      m.local = m.c.slice();
    });
    var masked = table.filter(isMask), patches = table.filter(function (m) { return !!m.tone; });
    masked.forEach(function (m, i) { m.slot = i; });
    var vol = table.filter(function (m) { return !m.noVol; });
    var base = cores.map(function (c) { return c.prim; }), musPrims = vol.map(function (m) { return m.prim; });
    var hasTop = !!S.bust, hipL = joints.hipL, legAx = nrm([Math.sin(LEG_B * D2R), -Math.cos(LEG_B * D2R), 0]);
    var refined = profileSampling === 'distance', torsoCore = cores[0].prim;
    var armCores = cores.filter(function (c) { return c.region.indexOf('arm') === 0; });
    function topOwnerAt(x, y, z) {
      if (!hasTop) return 0;
      var armD = Math.min(armCores[0].prim.f(x, y, z), armCores[1].prim.f(x, y, z));
      return sstep(-3, 3, armD - torsoCore.f(x, y, z));
    }
    function topAt(x, y, z, soft) {
      var band = sstep(CLOTH.topLo - soft, CLOTH.topLo + soft, y) * sstep(CLOTH.topHi + soft, CLOTH.topHi - soft, y);
      return band ? band * topOwnerAt(x, y, z) : 0;
    }
    var clothFn = function (x, y, z) {
      return refined ? Math.max(clothAt(x, y, z, hipL, legAx, false, 3), topAt(x, y, z, 3) * CLOTH.topThickness / CLOTH.thick) :
        clothAt(x, y, z, hipL, legAx, hasTop, 3);
    };
    var all = base.concat(musPrims), b = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9];
    all.forEach(function (p) { for (var i = 0; i < 3; i++) { b[i] = Math.min(b[i], p.box[i]); b[i + 3] = Math.max(b[i + 3], p.box[i + 3]); } });
    b = [b[0] - 14, b[1] - 14, b[2] - 14, b[3] + 14, b[4] + 14, b[5] + 14];
    var H = ctx.cell || (refined ? 3.5 : 4.5);
    var G = evalGrid(base, musPrims, b, H, 16, 8, clothFn);
    var mesh = surfaceNets(G);
    relax(mesh, G, 2);
    var n = mesh.pos.length / 3;
    var NSLOT = 8, normals = new Float32Array(n * 3), cav = new Float32Array(n), mus = new Float32Array(n * NSLOT), muw = new Float32Array(n * NSLOT), toneMax = new Float32Array(n);
    var patchIdx = new Uint8Array(n), patchW = new Float32Array(n), si = new Uint16Array(n * 4), sw = new Float32Array(n * 4), uvw = new Float32Array(n), topMask = new Float32Array(n), topOwnership = new Float32Array(n);
    var regionIds = ['torso', 'head', 'armL', 'armR', 'legL', 'legR'], coreOfRegion = {};
    cores.forEach(function (c) { (coreOfRegion[c.region] = coreOfRegion[c.region] || []).push(c.prim); });
    vol.forEach(function (m) { (coreOfRegion[m.region] = coreOfRegion[m.region] || []).push(m.prim); });
    var covered = new Array(masked.length).fill(0), dReg = {};
    var W = masked.map(function () { return new Float32Array(n); }), PW = patches.map(function () { return new Float32Array(n); });
    /*
     * Refined, female: the bust (a part, never a muscle) lies over the pectoralis and pushed the top's surface up to ~18 units off it,
     * beyond the pec mask's fade, so the effort tint on the sports top was a ring with an untinted centre (a grey smear for a
     * stabiliser, a brown one for a prime mover). Where the bust is the outermost volume, a muscle's mask and effort weight are read at
     * the point projected back along the normal onto the body without the bust: the tint covers the muscle's footprint seen through
     * the garment, as the shorts already do over the glutes.
     */
    var bustPrims = refined ? vol.filter(function (m) { return m.key === 'bust'; }).map(function (m) { return m.prim; }) : [];
    var underPrims = bustPrims.length ? base.concat(vol.filter(function (m) { return m.key !== 'bust'; }).map(function (m) { return m.prim; })) : null;
    var probe = bustPrims.length ? new Float32Array(n * 3) : null;
    function underBust(x, y, z, nrmV, out) {
      var fb = 1e9, fo = 1e9, i;
      for (i = 0; i < bustPrims.length; i++) fb = Math.min(fb, bustPrims[i].f(x, y, z));
      out[0] = x; out[1] = y; out[2] = z;
      if (fb > 6) return;
      for (i = 0; i < underPrims.length; i++) { var bx = underPrims[i].box; if (x < bx[0] || y < bx[1] || z < bx[2] || x > bx[3] || y > bx[4] || z > bx[5]) continue; fo = Math.min(fo, underPrims[i].f(x, y, z)); }
      var depth = Math.min(40, Math.max(0, fo)) * sstep(2, -2, fb - fo);
      out[0] = x - nrmV[0] * depth; out[1] = y - nrmV[1] * depth; out[2] = z - nrmV[2] * depth;
    }
    var pq = [0, 0, 0];
    for (var v = 0; v < n; v++) {
      var x = mesh.pos[v * 3], y = mesh.pos[v * 3 + 1], z = mesh.pos[v * 3 + 2];
      var gr = gridGrad(G, x, y, z); normals[v * 3] = gr[0]; normals[v * 3 + 1] = gr[1]; normals[v * 3 + 2] = gr[2];
      if (probe) { underBust(x, y, z, gr, pq); probe[v * 3] = pq[0]; probe[v * 3 + 1] = pq[1]; probe[v * 3 + 2] = pq[2]; }
      var dmin = 1e9;
      for (var ri2 = 0; ri2 < regionIds.length; ri2++) {
        var r = regionIds[ri2], best = 1e9, list = coreOfRegion[r] || [];
        for (var q = 0; q < list.length; q++) { var d = list[q].f(x, y, z); if (d < best) best = d; }
        dReg[r] = best; if (best < dmin) dmin = best;
      }
      var acc = {};
      regionIds.forEach(function (r) {
        // Discard only negligible influences, not a visible 2% joint blend.
        var c = Math.exp(-(dReg[r] - dmin) / 6); if (c < (refined ? 1e-5 : 0.02)) return;
        var wl = regionWeights(r, x, y, z, rctx);
        for (var q = 0; q < wl.length; q++) acc[wl[q][0]] = (acc[wl[q][0]] || 0) + c * wl[q][1];
      });
      var names = Object.keys(acc).sort(function (p, q) { return acc[q] - acc[p]; }).slice(0, 4), ws = 0;
      names.forEach(function (nm) { ws += acc[nm]; });
      for (var q2 = 0; q2 < 4; q2++) { si[v * 4 + q2] = q2 < names.length ? boneIdx[names[q2]] : 0; sw[v * 4 + q2] = q2 < names.length ? acc[names[q2]] / ws : 0; }
      if (refined) {
        var armInfluence = 0;
        names.forEach(function (nm) { if (/^(sh|el|hand)[LR]$/.test(nm)) armInfluence += acc[nm] / ws; });
        var topFit = 1 - sstep(0.15, 0.5, armInfluence);
        topMask[v] = topAt(x, y, z, 0.9) * topFit;
        topOwnership[v] = topOwnerAt(x, y, z) * topFit;
      }
      var dsharp = dmin;
      for (var vi = 0; vi < vol.length; vi++) { var dv = vol[vi].prim.f(x, y, z); if (dv < dsharp) dsharp = dv; }
      cav[v] = clamp(dsharp / 3.2, 0, 1);
      var mx = probe ? probe[v * 3] : x, my = probe ? probe[v * 3 + 1] : y, mz = probe ? probe[v * 3 + 2] : z;
      for (var mi3 = 0; mi3 < masked.length; mi3++) { var m3 = masked[mi3]; W[mi3][v] = 1 - sstep(m3.mask[0], m3.mask[1], m3.prim.f(mx, my, mz)); }
      for (var pi = 0; pi < patches.length; pi++) PW[pi][v] = 1 - sstep(patches[pi].mask[0], patches[pi].mask[1], patches[pi].prim.f(x, y, z));
    }
    // Soft edges: a 4.5-unit mesh cannot ramp a tint over fewer than ~2 cells without a visible step, so diffuse every mask over the surface
    // (two passes of neighbour averaging widen each fade by about two cells and keep the muscle's shape).
    var adj = new Array(n), ii2, tt;
    for (ii2 = 0; ii2 < n; ii2++) adj[ii2] = [];
    for (tt = 0; tt < mesh.idx.length; tt += 3) for (var ee = 0; ee < 3; ee++) adj[mesh.idx[tt + ee]].push(mesh.idx[tt + (ee + 1) % 3]);
    if (refined && HIP_WEIGHTS.passes) smoothWeights(si, sw, adj, mesh.pos, n, HIP_WEIGHTS);
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
    // Effort colour weight (refined): the coverage mask shaped by the muscle itself, so a highlight is strongest along the belly and
    // fades across its width and into its tendons. Coverage alone tinted the whole footprint at full strength: a flat block on the abs
    // and a disc on the glutes.
    // Each muscle's effort weight peaks at exactly 1 (1.5.0): after the belly shaping and diffusion the peaks ranged 0.26 (adductor)
    // to 1, so full activation never reached the role colour on the female deltoids (0.48-0.71), traps, erectors or glutes.
    var WC = refined ? masked.map(function (m, i) {
      var arr = new Float32Array(n), pr = m.prim, Q = probe || mesh.pos;
      for (var vc = 0; vc < n; vc++) if (W[i][vc] > 0) arr[vc] = W[i][vc] * (EFFORT.floor + (1 - EFFORT.floor) * bellyAt(pr, Q[vc * 3], Q[vc * 3 + 1], Q[vc * 3 + 2]));
      var out = diffuse(arr, 3), peak = 0, k;
      for (k = 0; k < n; k++) if (out[k] > peak) peak = out[k];
      if (EFFORT.peak && peak > 0) for (k = 0; k < n; k++) out[k] = Math.min(1, out[k] / peak);
      return out;
    }) : null;
    var muc = refined ? new Float32Array(n * NSLOT) : null;
    var order = [];
    for (var v6 = 0; v6 < n; v6++) {
      var tm = 0; order.length = 0;
      for (var mi4 = 0; mi4 < masked.length; mi4++) { var wv = W[mi4][v6]; if (wv > tm) tm = wv; if (wv > 0.02) order.push(mi4); }
      toneMax[v6] = tm;
      order.sort(function (p, q) { return W[q][v6] - W[p][v6]; });
      for (var q3 = 0; q3 < NSLOT; q3++) { mus[v6 * NSLOT + q3] = q3 < order.length ? order[q3] : 0; muw[v6 * NSLOT + q3] = q3 < order.length ? W[order[q3]][v6] : 0; if (q3 < order.length && W[order[q3]][v6] > 0.5) covered[order[q3]]++; }
      if (muc) for (var q5 = 0; q5 < NSLOT && q5 < order.length; q5++) muc[v6 * NSLOT + q5] = WC[order[q5]][v6];
      for (var pj = 0; pj < patches.length; pj++) if (PW[pj][v6] > patchW[v6]) { patchW[v6] = PW[pj][v6]; patchIdx[v6] = pj + 1; }
    }
    var data = { key: key, profileSampling: profileSampling, topMask: topMask, topOwnership: topOwnership, G: G, mesh: mesh, n: n, normals: normals, cav: cav, mus: mus, muw: muw, muc: muc, toneMax: toneMax, patchIdx: patchIdx, patchW: patchW, skinIndex: si, skinWeight: sw,
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
  /** The same ramp from a vertex's own rest colour (linear RGB array, offset i3). */
  function vtxRamp(out, arr, i3, mid, full, a) {
    out.r = arr[i3]; out.g = arr[i3 + 1]; out.b = arr[i3 + 2];
    if (a <= 0) return out;
    a = Math.min(1, a);
    return a < 0.4 ? out.lerp(mid, a / 0.4) : out.copy(mid).lerp(full, (a - 0.4) / 0.6);
  }

  // ------------------------------------------------------------------ the skin shader patch (cloth edge, creases, cut windows, interior)
  var NWIN = 6;
  var SKIN_VERT_DECL = 'attribute vec3 colorC;\nattribute float aCav;\nvarying vec3 vColC;\nvarying float vCav;\nvarying vec3 vBind;\n';
  function skinFragmentDecl(refined) { return [
    'varying vec3 vColC; varying float vCav; varying vec3 vBind;' + (refined ? ' varying float vTop;' : ''),
    'uniform vec4 uCloth; uniform vec4 uTop; uniform vec3 uHip; uniform vec3 uLegAx; uniform vec3 uBand; uniform float uCrease;',
    'uniform vec3 uWc[' + NWIN + ']; uniform mat3 uWm[' + NWIN + ']; uniform vec4 uWo[' + NWIN + ']; uniform vec3 uInterior; uniform vec3 uRim; uniform float uRimW;',
    'float sstepF(float a, float b, float x) { float t = clamp((x - a) / (b - a), 0.0, 1.0); return t * t * (3.0 - 2.0 * t); }',
    'float clothMask(vec3 p) {',
    '  vec3 q = vec3(abs(p.x) - uHip.x, p.y - uHip.y, p.z - uHip.z); float s = dot(q, uLegAx); vec3 l = q - uLegAx * s; float lat = length(l);',
    '  float c = sstepF(uCloth.x + 0.9, uCloth.x - 0.9, p.y) * sstepF(uCloth.z + 0.9, uCloth.z - 0.9, s) * sstepF(uCloth.w + 15.0, uCloth.w + 13.0, lat);',
    refined ? '  c = max(c, vTop * uTop.w * sstepF(uTop.x - 0.9, uTop.x + 0.9, p.y) * sstepF(uTop.y + 0.9, uTop.y - 0.9, p.y));' :
      '  c = max(c, uTop.w * sstepF(uTop.x - 0.9, uTop.x + 0.9, p.y) * sstepF(uTop.y + 0.9, uTop.y - 0.9, p.y) * sstepF(uTop.z + 0.9, uTop.z - 0.9, abs(p.x)));',
    '  return c; }'
  ].join('\n') + '\n'; }
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

  // ------------------------------------------------------------------ opt-in crescent shading (2D-vs-3D look prototype, prompts 05 part 1)
  /*
   * The 2D Cobalt Sculpt paints flat planes: a fill, a crescent of shade on the side of every form away from a light fixed at the
   * screen's top left, no outlines. A.shade(fig, 'crescent') gives the 3D figure the same grammar, per fragment and relative to the
   * camera: the view-space normal's screen component toward the light (CRESCENT.light, the 2D master's light vector with y up)
   * picks a flat plane, never a gradient:
   *   tone plane    a muscle's own surface (toneMax >= toneAt)   base lifted toward white (plane, sRGB): the 2D "light" fill #4F75EC
   *   body          between and off the muscles                  the vertex colour itself (cobalt, effort, cloth), unlit
   *   light plane   the surface turns toward the light           base lifted further (lift)
   *   shade plane   the surface turns away from the light        base darkened by dark (0.24: STYLE.md's "a 24 % darkening")
   * The tone plane needs the per-vertex muscle weight, so the skin gets an aTone attribute (data.toneMax) while crescent is on (never
   * under the shorts or top: the skin patch's cloth mask clM gates it); the spark, ponytail, shoes and cutaway layers get the light/shade planes only.
   * Crease darkening, cut windows, cloth and activation are untouched (they set diffuseColor first). Opt-in only: A.shade(fig) or
   * A.shade(fig, 'toon') restores the default programs, which are byte-identical to a figure that never called it.
   * Thresholds were picked by eye (2026-11-23 sweep): below ~0.5 the planes break into islands on the surface-nets normals of the
   * shallow muscle relief; crisper per-muscle crescents would need a smoothed shading normal (not built).
   */
  var CRESCENT = A.CRESCENT = { light: [-0.62, 0.78], lightAt: 0.58, shadeAt: 0.52, soft: 0.06, lift: 0.30, dark: 0.24, toneAt: 0.55, toneSoft: 0.06, plane: 0.16 };
  A.SHADES = ['toon', 'crescent'];
  function crescentKey(tone) { var c = CRESCENT; return 'crescent' + (tone ? '-tone:' : ':') + [c.light[0], c.light[1], c.lightAt, c.shadeAt, c.soft, c.lift, c.dark, c.toneAt, c.toneSoft, c.plane].join(','); }
  function crescentChunk(tone) {
    var c = CRESCENT, l = Math.sqrt(c.light[0] * c.light[0] + c.light[1] * c.light[1]) || 1, f = function (x) { return (+x).toFixed(5); };
    return [
      '{ vec3 crN = normalize(normal); float crS = dot(crN.xy, vec2(' + f(c.light[0] / l) + ', ' + f(c.light[1] / l) + '));',
      '  vec3 crB = clamp(diffuseColor.rgb, 0.0, 1.0), crG = pow(crB, vec3(0.454545));',
      tone ? '  vec3 crP = mix(crB, pow(mix(crG, vec3(1.0), ' + f(c.plane) + '), vec3(2.2)), smoothstep(' + f(c.toneAt - c.toneSoft) + ', ' + f(c.toneAt + c.toneSoft) + ', vTone) * (1.0 - clM));' : '  vec3 crP = crB;',
      '  vec3 crL = pow(mix(crG, vec3(1.0), ' + f(c.lift) + (tone ? ' * (1.0 - 0.5 * clM)' : '') + '), vec3(2.2)), crD = pow(crG * ' + f(1 - c.dark) + ', vec3(2.2));',
      '  float crLm = smoothstep(' + f(c.lightAt - c.soft) + ', ' + f(c.lightAt + c.soft) + ', crS), crDm = smoothstep(' + f(c.shadeAt - c.soft) + ', ' + f(c.shadeAt + c.soft) + ', -crS);',
      '  outgoingLight = mix(mix(crP, crL, crLm), crD, crDm); }'
    ].join('\n') + '\n';
  }
  function crescentize(m, tone) {
    if (!m || !m.isMeshToonMaterial || m.userData.tibiShade) return;
    var prevCompile = m.onBeforeCompile, prevKey = m.customProgramCacheKey, ownCompile = m.hasOwnProperty('onBeforeCompile'), ownKey = m.hasOwnProperty('customProgramCacheKey');
    var baseKey = prevKey.call(m), key = crescentKey(tone), chunk = crescentChunk(tone);
    m.userData.tibiShade = { compile: ownCompile ? prevCompile : null, key: ownKey ? prevKey : null };
    m.onBeforeCompile = function (sh, renderer) {
      prevCompile.call(this, sh, renderer);
      if (tone) {
        sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nattribute float aTone; varying float vTone;')
          .replace('#include <begin_vertex>', '#include <begin_vertex>\n  vTone = aTone;');
        sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying float vTone;');
      }
      sh.fragmentShader = sh.fragmentShader.replace('#include <opaque_fragment>', chunk + '#include <opaque_fragment>');
    };
    m.customProgramCacheKey = function () { return baseKey + '|' + key; };
    m.needsUpdate = true;
  }
  function uncrescent(m) {
    var s = m && m.userData.tibiShade; if (!s) return;
    if (s.compile) m.onBeforeCompile = s.compile; else delete m.onBeforeCompile;
    if (s.key) m.customProgramCacheKey = s.key; else delete m.customProgramCacheKey;
    delete m.userData.tibiShade; m.needsUpdate = true;
  }
  function shadeTree(obj, mode, skin) {
    obj.traverse(function (o) {
      (Array.isArray(o.material) ? o.material : [o.material]).forEach(function (m) {
        if (!m) return;
        if (mode === 'crescent') crescentize(m, skin && o === skin); else uncrescent(m);
      });
    });
  }
  /**
   * A.shade(target, mode): mode 'toon' (default look) or 'crescent'. target is a figure from T3.tibi / stage.tibi (its whole root: skin,
   * spark, ponytail, shoes, and the cutaway layers when they are built later) or any Object3D (e.g. equipment). Returns target.
   */
  A.shade = function (target, mode) {
    mode = mode || 'toon';
    if (A.SHADES.indexOf(mode) < 0) throw new Error('Unknown Tibi shade: ' + mode + ' (use ' + A.SHADES.join(' or ') + ')');
    var obj = target && target.root && target.root.isObject3D ? target.root : target;
    if (!obj || !obj.isObject3D) throw new Error('T3.anatomy.shade needs a Tibi figure or a THREE.Object3D');
    var body = target.body && target.body.skin ? target.body : null;
    if (body) {
      body.shade = mode;
      if (mode === 'crescent' && !body.geo.getAttribute('aTone')) body.geo.setAttribute('aTone', new THREE.BufferAttribute(body.data.toneMax, 1));
      if (mode === 'toon' && body.geo.getAttribute('aTone')) body.geo.deleteAttribute('aTone');
    }
    shadeTree(obj, mode, body && body.skin);
    return target;
  };

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
    { name: 'glute', bone: 'hips', c: [34, -22, -50], r: [50, 56, 34], both: true, mirror: true, sweep: [0.54, 0.84] },   // sweep toward the medius (upper, lateral)
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
  /*
   * A loft is a hollow shell. Once a window cuts the superficial layer (open > 1), the far wall of that same muscle shows through
   * the hole as a second, smaller outline of the muscle, and the next wall a third: the "concentric rings" of the glute cutaway.
   * Inside an opened window the inside of a superficial shell is never drawn, so the hole shows the deep layer. Lofts are wound
   * outward (refined), so a back face is the inside. anatomy3d-check models the same rule (A.CUT) on rays through the window.
   */
  var CUT = A.CUT = { deepScale: 0.84, hideInnerWall: true, sweepSpan: 2.05, sweepEase: 1.5 };
  /*
   * Refined deep stage of a window with a sweep (the glute): open 1 -> 2 removes the superficial layer behind a straight edge that
   * travels across the window from the side of the deep muscle (sweep = in-plane direction in window coordinates), instead of a
   * hole growing from the centre. A centred hole left the gluteus maximus as a coral loop around it; the sweep leaves a solid belly
   * with a clean cut edge lying over the medius it uncovers. JS mirror of the shader rule (the checker uses it).
   */
  CUT.deep = function (q, o0, o1, sweep) {
    if (!(o1 > 0.001)) return false;
    var we = Math.sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2]);
    if (sweep && (sweep[0] || sweep[1])) return we < o0 && q[0] * sweep[0] + q[1] * sweep[1] > 1 - CUT.sweepSpan * Math.pow(o1, CUT.sweepEase);
    return we < o1 * CUT.deepScale;
  };
  var INNER_DEEP_REFINED = 'if (uLayer > 0.5 && uLayer < 1.5) { for (int wi = 0; wi < ' + NWIN + '; wi++) { if (uWo[wi].y > 0.001) { vec3 q = uWm[wi] * (vBind - uWc[wi]); float we = length(q);' +
    ' bool sw = abs(uWo[wi].z) + abs(uWo[wi].w) > 0.001;' +
    ' if (sw ? (we < uWo[wi].x && dot(q.xy, uWo[wi].zw) > 1.0 - ' + CUT.sweepSpan.toFixed(2) + ' * pow(uWo[wi].y, ' + CUT.sweepEase.toFixed(2) + ')) : we < uWo[wi].y * ' + CUT.deepScale.toFixed(2) + ') discard; } } }\n' +
    'diffuseColor.rgb *= 1.0 - uFibre * (0.5 + 0.5 * sin(vFib * 6.2831853 * 9.0));\n';
  var INNER_CUT_INSIDE = CUT.hideInnerWall ?
    'if (uLayer > 0.5 && uLayer < 1.5 && !gl_FrontFacing) { for (int wi = 0; wi < ' + NWIN + '; wi++) { if (uWo[wi].y > 0.001 && length(uWm[wi] * (vBind - uWc[wi])) < uWo[wi].x) discard; } }\n' : '';
  var INNER_WINDOW_CLIP = [
    'if (uWindowOnly > 0.5) {',
    '  bool inWindow = false;',
    '  for (int wi = 0; wi < ' + NWIN + '; wi++) {',
    '    if (uWo[wi].x > 0.001 && length(uWm[wi] * (vBind - uWc[wi])) < uWo[wi].x) inWindow = true;',
    '  }',
    '  if (!inWindow) discard;',
    '}'
  ].join('\n') + '\n';

  function loftSpindleGeo(prim, rows, seg, forceRw, forceRt, outward) {
    var pos = [], fib = [], idx = [], uu = [], A0 = prim.A, ax = prim.ax, wd = prim.wd, td = prim.td, L = prim.L, pw = prim.pw;
    var rw = forceRw || prim.rw, rt = forceRt || prim.rt;
    // The ring runs wd -> td; with a right-handed (ax, wd, td) the default winding faces inward.
    var flip = !!outward && dot(cross(ax, wd), td) > 0;
    for (var r = 0; r <= rows; r++) {
      var u = r / rows, qv = 1 - (2 * u - 1) * (2 * u - 1), prof = Math.pow(Math.max(qv, 0), pw);
      var section = prim.profile ? muscleSection(prim.profile, u, pw) : [prof, prof];
      for (var sg = 0; sg < seg; sg++) {
        var th = sg / seg * Math.PI * 2, cw = Math.cos(th) * rw * section[0], ct = Math.sin(th) * rt * section[1], s0 = u * L;
        pos.push(A0[0] + ax[0] * s0 + wd[0] * cw + td[0] * ct, A0[1] + ax[1] * s0 + wd[1] * cw + td[1] * ct, A0[2] + ax[2] * s0 + wd[2] * cw + td[2] * ct);
        fib.push(sg / seg); uu.push(u);
      }
    }
    for (var r2 = 0; r2 < rows; r2++) for (var s2 = 0; s2 < seg; s2++) {
      var a = r2 * seg + s2, b = r2 * seg + (s2 + 1) % seg, c = (r2 + 1) * seg + s2, d = (r2 + 1) * seg + (s2 + 1) % seg;
      if (flip) idx.push(a, b, c, b, d, c); else idx.push(a, c, b, b, c, d);
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
    var refined = data.profileSampling === 'distance';
    var rctx = { joints: data.joints, armAxis: data.armAxis, armStops: refined ? ARM_STOPS_REFINED : null, girdle: refined };
    var group = new THREE.Group(); group.name = 'inner'; root.add(group);
    var WU = body.uniforms;
    var innerMats = [];
    function innerMat(color, layer, fibre) {
      var m = T3.material(color, { side: THREE.DoubleSide });
      var U = { uOff: { value: new THREE.Vector3() }, uLayer: { value: layer }, uWindowOnly: { value: 0 }, uFibre: { value: layer === 3 ? 0 : (fibre === undefined ? 0.10 : fibre) }, uWc: WU.uWc, uWm: WU.uWm, uWo: WU.uWo };
      m.onBeforeCompile = function (sh) {
        for (var k in U) sh.uniforms[k] = U[k];
        sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\n' + INNER_VERT_DECL)
          .replace('#include <begin_vertex>', '#include <begin_vertex>\n  vFib = aFib; vBind = position; transformed += uOff;');
        sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\n' + INNER_FRAG_DECL + (refined ? 'uniform float uWindowOnly;\n' : ''))
          .replace('#include <color_fragment>', '#include <color_fragment>\n' + (refined ? INNER_WINDOW_CLIP + INNER_CUT_INSIDE + INNER_DEEP_REFINED : INNER_FRAG_BODY));
      };
      m.customProgramCacheKey = function () { return refined ? 'tibi-inner-4' : 'tibi-inner-1'; };
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
        var lo = loftSpindleGeo(m.prim, 14, 14, 0, 0, refined);
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
        wins.push({ name: w.name, side: s, c: cc, M: M, bone: bn, sweep: refined && w.sweep ? [w.sweep[0] * (w.mirror ? sg : 1), w.sweep[1]] : null });
      });
    });
    body.windowList = wins;
    body.inner = { group: group, meshes: meshes, materials: innerMats };
    group.visible = false;
    return body.inner;
  }

  // ------------------------------------------------------------------ pose-driven correctives (refined body)
  /*
   * Linear-blend skinning averages the two rigid positions of a blended vertex, so at a hinge of angle t a 50/50 vertex lands on the
   * chord at cos(t/2) of its distance from the joint: 0.26 at 150 degrees. The elbow and knee folded flat and the hip lost about 3%
   * of the body's volume at 120 degrees. The corrective is a deterministic function of the bone matrices: for each parent/child pair,
   * a vertex blended between them is moved back out to its rigid distance from the joint centre (the LBS direction is kept), and the
   * displacement is mapped into bind space through the inverse of its own blend matrix, so the GPU skinning lands it exactly there.
   * A joint with no relative rotation is skipped, so a pose that leaves a joint alone leaves its skin byte-identical.
   * Shoulder pairs (chest/sh) are deliberately absent: they move torso skin on arm elevation. Since 1.6.0 the shoulder is relieved by
   * the girdle and soft-tissue bones instead (GIRDLE_WEIGHTS; tibi3d.js GIRDLE), which move skin rigidly with the scapula.
   */
  var CORRECTIVE = A.CORRECTIVE = { pairs: [['shL', 'elL', 30, 50], ['shR', 'elR', 30, 50], ['thL', 'knL', 35, 55], ['thR', 'knR', 35, 55], ['hips', 'thL', 60, 90], ['hips', 'thR', 60, 90]], strength: 1, keep: 0.7, side: [-0.15, 0.35], minAngle: 1e-3, minWeight: 0.005 };
  /*
   * Refined: delta mush at the hip. In a deep hinge (deadlift floor, RDL bottom, squat) linear-blend skinning pulls the blended skin
   * of the buttock and gluteal fold onto the chord between the pelvis and the flexed thigh: the outer side lost 5-9% of the body's
   * volume, neighbouring rows overtook each other and folded (neighbour normals up to 175 degrees), and seen from behind the shorts
   * read as a lumpy, puffy mass. The mush smooths the posed region (iterations of Laplacian smoothing, the ring around it fixed) and
   * adds back each vertex's rest detail (its offset from the smoothed rest surface, stored in that surface's local frame), so the
   * relief of the glutes and the garment hem survive while the LBS folds do not. A pure function of the bone matrices, faded in by the
   * larger hip angle (on, degrees) so standing poses stay byte-identical; region = bind-space box |x| < box[0], box[1] < y < box[2],
   * faded over soft units at its edge and off the front of the hip (bind normal z from front[1] to front[0]): the groin crease is the
   * inner fold the pair corrective already holds open, and smoothing it pulled hip 120 to 0.60 of its radius.
   */
  var MUSH = A.MUSH = { box: [100, -140, 45], soft: 14, front: [0.55, 0.05], iterations: 40, rate: 0.5, on: [20, 50] };
  /*
   * Refined (1.6.0): scapulothoracic glide. The scapula slides over the ribcage; rotating the trunk skin it carries rigidly about the
   * glenohumeral joint lifted the skin behind and under the armpit off the ribs (a lump seen from behind, and the female top bulging
   * out under the raised arm). For trunk skin carried by the girdle or the soft-tissue frame, below the joint (`below`, units under
   * it) and nearer the torso core than the arm core (`trunk`), the posed point is read in the chest's bind frame and any rise above
   * its rest height over the torso core beyond `tol` is taken back along the core's normal. One-sided (it never pushes skin out), so
   * the lat cannot inflate; faded by the girdle weight (full at `full`). A pure function of the bone matrices.
   * OFF by default (strength 0): it flattens the lump, but the lump was covering arm-root skin, and pulling it back showed that
   * skin's inside (overhead abduction: 14% of rays at the shoulder hit back faces; spreading the pull to 8 rings changed nothing).
   * Kept as an experiment for the successor (known-limits/r3b-report.md); the lump behind the raised armpit remains a known limit.
   */
  var GLIDE = A.GLIDE = { strength: 0, tol: 0.5, below: [5, 25], trunk: [-8, 2], full: 0.2 };
  function mushSmooth(MD, P, S, T) {
    var reg = MD.reg, as = MD.adjStart, al = MD.adjList, rate = MD.cfg.rate, all = MD.all, i, v, k;
    for (i = 0; i < all.length; i++) { v = all[i]; S[v * 3] = P[v * 3]; S[v * 3 + 1] = P[v * 3 + 1]; S[v * 3 + 2] = P[v * 3 + 2]; }
    for (var it = 0; it < MD.cfg.iterations; it++) {
      for (i = 0; i < reg.length; i++) {
        v = reg[i];
        var sx = 0, sy = 0, sz = 0, cnt = as[i + 1] - as[i];
        for (k = as[i]; k < as[i + 1]; k++) { var u = al[k]; sx += S[u * 3]; sy += S[u * 3 + 1]; sz += S[u * 3 + 2]; }
        T[v * 3] = S[v * 3] + rate * (sx / cnt - S[v * 3]); T[v * 3 + 1] = S[v * 3 + 1] + rate * (sy / cnt - S[v * 3 + 1]); T[v * 3 + 2] = S[v * 3 + 2] + rate * (sz / cnt - S[v * 3 + 2]);
      }
      for (i = 0; i < reg.length; i++) { v = reg[i]; S[v * 3] = T[v * 3]; S[v * 3 + 1] = T[v * 3 + 1]; S[v * 3 + 2] = T[v * 3 + 2]; }
    }
  }
  /** Local frame of region vertex r on surface S: F = [tangent | bitangent | normal] (rows of three). */
  function mushFrame(MD, S, r, F) {
    var idx = MD.idx, v = MD.reg[r], nx = 0, ny = 0, nz = 0;
    for (var k = MD.faceStart[r]; k < MD.faceStart[r + 1]; k++) {
      var t = MD.faceList[k], a = idx[t] * 3, b = idx[t + 1] * 3, c = idx[t + 2] * 3;
      var ux = S[b] - S[a], uy = S[b + 1] - S[a + 1], uz = S[b + 2] - S[a + 2], wx = S[c] - S[a], wy = S[c + 1] - S[a + 1], wz = S[c + 2] - S[a + 2];
      nx += uy * wz - uz * wy; ny += uz * wx - ux * wz; nz += ux * wy - uy * wx;
    }
    var l = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1; nx /= l; ny /= l; nz /= l;
    var u0 = MD.adjList[MD.adjStart[r]], tx = S[u0 * 3] - S[v * 3], ty = S[u0 * 3 + 1] - S[v * 3 + 1], tz = S[u0 * 3 + 2] - S[v * 3 + 2], dn = tx * nx + ty * ny + tz * nz;
    tx -= dn * nx; ty -= dn * ny; tz -= dn * nz; l = Math.sqrt(tx * tx + ty * ty + tz * tz) || 1; tx /= l; ty /= l; tz /= l;
    F[0] = tx; F[1] = ty; F[2] = tz; F[3] = ny * tz - nz * ty; F[4] = nz * tx - nx * tz; F[5] = nx * ty - ny * tx; F[6] = nx; F[7] = ny; F[8] = nz;
  }
  /** Region, adjacency, incident faces and rest deltas of a delta mush: pure geometry, cached on the body data per name and setting. */
  function mushData(data, name, cfg, amtAt) {
    var key = name + JSON.stringify(cfg), slot = 'mush:' + name;
    if (data[slot] && data[slot].key === key) return data[slot];
    var n = data.n, P = data.mesh.pos, idx = data.mesh.idx, reg = [], amt = [], rindex = new Int32Array(n).fill(-1), v, k;
    for (v = 0; v < n; v++) {
      var am = amtAt(v, P);
      if (am !== null) { rindex[v] = reg.length; reg.push(v); amt.push(am); }
    }
    var nbr = reg.map(function () { return []; }), fcs = reg.map(function () { return []; });
    for (var t = 0; t < idx.length; t += 3) for (var e = 0; e < 3; e++) {
      var a = idx[t + e], b = idx[t + (e + 1) % 3];
      if (rindex[a] >= 0) { nbr[rindex[a]].push(b); fcs[rindex[a]].push(t); }
      if (rindex[b] >= 0) nbr[rindex[b]].push(a);
    }
    var adjStart = new Int32Array(reg.length + 1), faceStart = new Int32Array(reg.length + 1), adjList = [], faceList = [], ring = {};
    reg.forEach(function (rv, i) {
      var uniq = nbr[i].filter(function (x, j, arr) { return arr.indexOf(x) === j; }).sort(function (p, q) { return p - q; });
      uniq.forEach(function (x) { adjList.push(x); if (rindex[x] < 0) ring[x] = 1; });
      fcs[i].forEach(function (x) { faceList.push(x); });
      adjStart[i + 1] = adjList.length; faceStart[i + 1] = faceList.length;
    });
    var MD = { key: key, cfg: cfg, reg: new Int32Array(reg), amt: new Float32Array(amt), adjStart: adjStart, adjList: new Int32Array(adjList), faceStart: faceStart, faceList: new Int32Array(faceList), idx: idx };
    MD.all = new Int32Array(reg.concat(Object.keys(ring).map(Number).sort(function (p, q) { return p - q; })));
    var R = new Float64Array(n * 3), S = new Float64Array(n * 3), T = new Float64Array(n * 3), F = [0, 0, 0, 0, 0, 0, 0, 0, 0];
    for (k = 0; k < MD.all.length; k++) { v = MD.all[k]; R[v * 3] = P[v * 3]; R[v * 3 + 1] = P[v * 3 + 1]; R[v * 3 + 2] = P[v * 3 + 2]; }
    mushSmooth(MD, R, S, T);
    MD.D = new Float64Array(reg.length * 3);
    for (k = 0; k < reg.length; k++) {
      v = reg[k]; mushFrame(MD, S, k, F);
      var dx = P[v * 3] - S[v * 3], dy = P[v * 3 + 1] - S[v * 3 + 1], dz = P[v * 3 + 2] - S[v * 3 + 2];
      MD.D[k * 3] = dx * F[0] + dy * F[1] + dz * F[2]; MD.D[k * 3 + 1] = dx * F[3] + dy * F[4] + dz * F[5]; MD.D[k * 3 + 2] = dx * F[6] + dy * F[7] + dz * F[8];
    }
    data[slot] = MD;
    return MD;
  }
  function hipMushAt(data) {
    var B = MUSH.box;
    return function (v, P) {
      var d = Math.min(B[0] - Math.abs(P[v * 3]), P[v * 3 + 1] - B[1], B[2] - P[v * 3 + 1]);
      return d > 0 ? sstep(0, MUSH.soft, d) * sstep(MUSH.front[0], MUSH.front[1], data.normals[v * 3 + 2]) : null;
    };
  }
  function makeCorrective(skin, skeleton, boneIndex, data) {
    var n = data.n, si = data.skinIndex, sw = data.skinWeight, bones = skeleton.bones, nb = bones.length;
    var pairs = CORRECTIVE.pairs.map(function (pr) { return { p: boneIndex[pr[0]], c: boneIndex[pr[1]], near: pr[2], far: pr[3], outer: pr[4] || 0, verts: [], wp: [], wc: [], active: false, o: new THREE.Vector3(), yp: new THREE.Vector3(), yc: new THREE.Vector3(), bis: new THREE.Vector3() }; });
    var member = new Uint8Array(n), list = [];
    pairs.forEach(function (pr) {
      for (var v = 0; v < n; v++) {
        var wp = 0, wc = 0;
        for (var j = 0; j < 4; j++) { var b = si[v * 4 + j], w = sw[v * 4 + j]; if (b === pr.p) wp += w; else if (b === pr.c) wc += w; }
        if (wp >= CORRECTIVE.minWeight && wc >= CORRECTIVE.minWeight) { pr.verts.push(v); pr.wp.push(wp); pr.wc.push(wc); if (!member[v]) { member[v] = 1; list.push(v); } }
      }
    });
    var G = []; for (var i = 0; i < nb; i++) G.push(new THREE.Matrix4());
    var tmp = new THREE.Matrix4(), delta = new Float64Array(n * 3), any = false;
    function xf(e, x, y, z, out) { out[0] = e[0] * x + e[4] * y + e[8] * z + e[12]; out[1] = e[1] * x + e[5] * y + e[9] * z + e[13]; out[2] = e[2] * x + e[6] * y + e[10] * z + e[14]; }
    var rp = [0, 0, 0], rc = [0, 0, 0];
    // delta mush instances (refined): region, rest deltas and the bones whose matrices each reads (the hip; a list so a region can be added)
    var mushes = [], hipPairs = pairs.filter(function (pr) { return pr.p === boneIndex.hips; });
    if (MUSH.iterations) mushes.push({ MD: mushData(data, 'hip', MUSH, hipMushAt(data)), cfg: MUSH, angle: function () {
      var a = 0; hipPairs.forEach(function (pr) { a = Math.max(a, pr.ang / D2R); }); return a;
    } });
    var mP = mushes.length ? new Float64Array(n * 3) : null, mS = mushes.length ? new Float64Array(n * 3) : null, mT = mushes.length ? new Float64Array(n * 3) : null;
    mushes.forEach(function (mu) {
      var MD = mu.MD, seenBone = {};
      mu.on = 0; mu.bones = [];
      for (var mv = 0; mv < MD.all.length; mv++) for (var mj = 0; mj < 4; mj++) if (sw[MD.all[mv] * 4 + mj] > 0 && !seenBone[si[MD.all[mv] * 4 + mj]]) { seenBone[si[MD.all[mv] * 4 + mj]] = 1; mu.bones.push(si[MD.all[mv] * 4 + mj]); }
      mu.bones.sort(function (p, q) { return p - q; });
      for (var mr = 0; mr < MD.reg.length; mr++) if (!member[MD.reg[mr]]) { member[MD.reg[mr]] = 1; list.push(MD.reg[mr]); }
    });
    /**
     * After computeVertexNormals on the morphed bind mesh: inside a mush region the GPU's skinned normal (blend matrix times the bind
     * normal) of a strongly blended vertex points up to 150 degrees off the posed surface in a deep hinge, so the toon bands drew
     * lumps the geometry does not have. There the bind normal becomes M^-1 times the true posed normal, faded in like the mush.
     */
    function mushNormals(MD, mushOn, N) {
      var reg = MD.reg, idx = MD.idx, m = [0, 0, 0, 0, 0, 0, 0, 0, 0];
      for (var r = 0; r < reg.length; r++) {
        var v = reg[r], k = mushOn * MD.amt[r], nx = 0, ny = 0, nz = 0;
        if (!(k > 0)) continue;
        for (var q = MD.faceStart[r]; q < MD.faceStart[r + 1]; q++) {
          var t = MD.faceList[q], a = idx[t] * 3, b = idx[t + 1] * 3, c = idx[t + 2] * 3;
          var ux = mT[b] - mT[a], uy = mT[b + 1] - mT[a + 1], uz = mT[b + 2] - mT[a + 2], wx = mT[c] - mT[a], wy = mT[c + 1] - mT[a + 1], wz = mT[c + 2] - mT[a + 2];
          nx += uy * wz - uz * wy; ny += uz * wx - ux * wz; nz += ux * wy - uy * wx;
        }
        for (var i9 = 0; i9 < 9; i9++) m[i9] = 0;
        for (var j = 0; j < 4; j++) {
          var w = sw[v * 4 + j]; if (!w) continue;
          var e = G[si[v * 4 + j]].elements;
          m[0] += w * e[0]; m[1] += w * e[1]; m[2] += w * e[2]; m[3] += w * e[4]; m[4] += w * e[5]; m[5] += w * e[6]; m[6] += w * e[8]; m[7] += w * e[9]; m[8] += w * e[10];
        }
        var det = m[0] * (m[4] * m[8] - m[7] * m[5]) - m[3] * (m[1] * m[8] - m[7] * m[2]) + m[6] * (m[1] * m[5] - m[4] * m[2]);
        var l = Math.sqrt(nx * nx + ny * ny + nz * nz);
        if (Math.abs(det) < 1e-6 || !(l > 0)) continue;
        var ix = (nx * (m[4] * m[8] - m[7] * m[5]) - m[3] * (ny * m[8] - m[7] * nz) + m[6] * (ny * m[5] - m[4] * nz)) / det;
        var iy = (m[0] * (ny * m[8] - nz * m[7]) - nx * (m[1] * m[8] - m[7] * m[2]) + m[6] * (m[1] * nz - ny * m[2])) / det;
        var iz = (m[0] * (m[4] * nz - m[5] * ny) - m[3] * (m[1] * nz - ny * m[2]) + nx * (m[1] * m[5] - m[4] * m[2])) / det;
        var il = Math.sqrt(ix * ix + iy * iy + iz * iz) || 1;
        var ox = N[v * 3] + k * (ix / il - N[v * 3]), oy = N[v * 3 + 1] + k * (iy / il - N[v * 3 + 1]), oz = N[v * 3 + 2] + k * (iz / il - N[v * 3 + 2]);
        var ol = Math.sqrt(ox * ox + oy * oy + oz * oz) || 1;
        N[v * 3] = ox / ol; N[v * 3 + 1] = oy / ol; N[v * 3 + 2] = oz / ol;
      }
    }
    // scapulothoracic glide (1.6.0): trunk skin the girdle carries slides over the ribcage instead of lifting off it
    var glide = null, torsoPrim = data.cores[0].prim;
    if (GLIDE.strength && boneIndex.gdL !== undefined) {
      glide = { verts: [], h0: [], k: [], bones: [], on: false };
      var armPrims = data.cores.filter(function (c) { return c.region.indexOf('arm') === 0; }).map(function (c) { return c.prim; }), seenG = {};
      for (var gv = 0; gv < n; gv++) {
        var gw = 0;
        for (var gj = 0; gj < 4; gj++) { var gb = si[gv * 4 + gj]; if (gb === boneIndex.gdL || gb === boneIndex.gdR || gb === boneIndex.axL || gb === boneIndex.axR) gw += sw[gv * 4 + gj]; }
        if (gw < 0.02) continue;
        var gx = data.mesh.pos[gv * 3], gy = data.mesh.pos[gv * 3 + 1], gz = data.mesh.pos[gv * 3 + 2], J = data.joints[gx >= 0 ? 'shL' : 'shR'];
        var below = sstep(GLIDE.below[0], GLIDE.below[1], J[1] - gy), h0 = torsoPrim.f(gx, gy, gz);
        var trunk = sstep(GLIDE.trunk[0], GLIDE.trunk[1], Math.min(armPrims[0].f(gx, gy, gz), armPrims[1].f(gx, gy, gz)) - h0);
        var kk = below * trunk * Math.min(1, gw / GLIDE.full);
        if (!(kk > 1e-3)) continue;
        glide.verts.push(gv); glide.h0.push(h0); glide.k.push(kk);
        for (gj = 0; gj < 4; gj++) if (sw[gv * 4 + gj] > 0 && !seenG[si[gv * 4 + gj]]) { seenG[si[gv * 4 + gj]] = 1; glide.bones.push(si[gv * 4 + gj]); }
        if (!member[gv]) { member[gv] = 1; list.push(gv); }
      }
      glide.bones.sort(function (p, q) { return p - q; });
    }
    return {
      /** Update the root-relative bone matrices; returns an exact signature of the joint rotations the correctives depend on. */
      pose: function () {
        var out = [];
        for (var i = 0; i < nb; i++) G[i].multiplyMatrices(skin.bindMatrixInverse, tmp.multiplyMatrices(bones[i].matrixWorld, skeleton.boneInverses[i])).multiply(skin.bindMatrix);
        any = false;
        pairs.forEach(function (pr) {
          var a = G[pr.p].elements, b = G[pr.c].elements, tr = 0;
          // trace of Rp^T Rc: the relative rotation angle of the pair
          for (var r = 0; r < 3; r++) tr += a[r * 4] * b[r * 4] + a[r * 4 + 1] * b[r * 4 + 1] + a[r * 4 + 2] * b[r * 4 + 2];
          var ang = Math.acos(clamp((tr - 1) / 2, -1, 1));
          pr.ang = ang;
          pr.active = ang > CORRECTIVE.minAngle;
          if (pr.active) {
            any = true;
            tmp.multiplyMatrices(skin.bindMatrixInverse, bones[pr.c].matrixWorld);
            pr.o.set(0, 0, 0).applyMatrix4(tmp);
            // bone-local +y axes in geometry space (G's columns are bind-space axes, not the bones' own)
            pr.yc.setFromMatrixColumn(tmp, 1);
            pr.yp.setFromMatrixColumn(tmp.multiplyMatrices(skin.bindMatrixInverse, bones[pr.p].matrixWorld), 1);
            pr.bis.copy(pr.yp).normalize().sub(pr.yc.normalize()).normalize();
          }
          out.push(pr.active ? Array.prototype.join.call(a, ',') + ';' + Array.prototype.join.call(b, ',') : '0');
        });
        mushes.forEach(function (mu, mi) {
          mu.on = sstep(mu.cfg.on[0], mu.cfg.on[1], mu.angle());
          // a mush reads every bone that skins its region, so all of them belong in the exact signature
          if (mu.on > 0) { any = true; out.push((mi ? 'm' + mi : 'm') + mu.bones.map(function (bi) { return Array.prototype.join.call(G[bi].elements, ','); }).join(';')); }
        });
        if (glide) {
          // active only while a girdle has left the chest frame (rest and neutral stance: off, so they stay byte-identical)
          var c = G[boneIndex.chest].elements, dev = 0;
          [boneIndex.gdL, boneIndex.gdR].forEach(function (bi) {
            var e = G[bi].elements;
            for (var r = 0; r < 12; r++) dev = Math.max(dev, Math.abs(e[r] - c[r]) * 57.3);
            for (r = 12; r < 15; r++) dev = Math.max(dev, Math.abs(e[r] - c[r]));
          });
          glide.on = GLIDE.strength * sstep(0, 3, dev);
          if (glide.on > 0) { any = true; out.push('g' + glide.bones.map(function (bi) { return Array.prototype.join.call(G[bi].elements, ','); }).join(';')); }
        }
        return out.join('|');
      },
      apply: function (pos) {
        if (!any) return;
        delta.fill(0);
        pairs.forEach(function (pr) {
          if (!pr.active) return;
          var a = G[pr.p].elements, b = G[pr.c].elements, o = pr.o;
          // Inner side of the bend: toward the bisector of the parent's +y (back up its limb or trunk) and the child's -y (down its limb).
          var bx = pr.bis.x, by = pr.bis.y, bz = pr.bis.z;
          for (var k = 0; k < pr.verts.length; k++) {
            var v = pr.verts[k], wp = pr.wp[k], wc = pr.wc[k], ws = wp + wc, x = pos[v * 3], y = pos[v * 3 + 1], z = pos[v * 3 + 2];
            xf(a, x, y, z, rp); xf(b, x, y, z, rc);
            var qx = (wp * rp[0] + wc * rc[0]) / ws - o.x, qy = (wp * rp[1] + wc * rc[1]) / ws - o.y, qz = (wp * rp[2] + wc * rc[2]) / ws - o.z;
            var dq = Math.sqrt(qx * qx + qy * qy + qz * qz);
            if (dq < 1e-6) continue;
            // Only the compressed (inner) side is restored: on the outer side the arc is longer than the LBS chord, so restoring it
            // there stretches the skin over the knee and elbow points (squat stretch p999 rose from 4.4 to 6.4 when both sides were).
            var side = sstep(CORRECTIVE.side[0], CORRECTIVE.side[1], (qx * bx + qy * by + qz * bz) / dq);
            var keep = CORRECTIVE.keep * side + pr.outer * (1 - side);
            if (!keep) continue;
            var dt = (wp * Math.hypot(rp[0] - o.x, rp[1] - o.y, rp[2] - o.z) + wc * Math.hypot(rc[0] - o.x, rc[1] - o.y, rc[2] - o.z)) / ws;
            var f = CORRECTIVE.strength * ws * Math.max(0, keep * dt - dq) / dq * (1 - sstep(pr.near, pr.far, dt));
            delta[v * 3] += f * qx; delta[v * 3 + 1] += f * qy; delta[v * 3 + 2] += f * qz;
          }
        });
        mushes.forEach(function (mu) {
          if (!(mu.on > 0)) return;
          var MD = mu.MD, mushOn = mu.on;
          // posed positions (LBS plus the pair correctives) of the region and its fixed ring
          var all = MD.all, reg = MD.reg;
          for (var a1 = 0; a1 < all.length; a1++) {
            var u = all[a1], px = pos[u * 3], py = pos[u * 3 + 1], pz = pos[u * 3 + 2], sx = 0, sy = 0, sz = 0;
            for (var j1 = 0; j1 < 4; j1++) { var w1 = sw[u * 4 + j1]; if (!w1) continue; xf(G[si[u * 4 + j1]].elements, px, py, pz, rp); sx += w1 * rp[0]; sy += w1 * rp[1]; sz += w1 * rp[2]; }
            mP[u * 3] = sx + delta[u * 3]; mP[u * 3 + 1] = sy + delta[u * 3 + 1]; mP[u * 3 + 2] = sz + delta[u * 3 + 2];
          }
          mushSmooth(MD, mP, mS, mT);
          var F = [0, 0, 0, 0, 0, 0, 0, 0, 0];
          for (var a2 = 0; a2 < all.length; a2++) { var ua = all[a2]; mT[ua * 3] = mP[ua * 3]; mT[ua * 3 + 1] = mP[ua * 3 + 1]; mT[ua * 3 + 2] = mP[ua * 3 + 2]; }
          for (var r1 = 0; r1 < reg.length; r1++) {
            var vr = reg[r1], dd = MD.D, f1 = mushOn * MD.amt[r1];
            mushFrame(MD, mS, r1, F);
            for (var c1 = 0; c1 < 3; c1++) {
              var tgt = mS[vr * 3 + c1] + dd[r1 * 3] * F[c1] + dd[r1 * 3 + 1] * F[3 + c1] + dd[r1 * 3 + 2] * F[6 + c1];
              delta[vr * 3 + c1] += f1 * (tgt - mP[vr * 3 + c1]);
              mT[vr * 3 + c1] = mP[vr * 3 + c1] + f1 * (tgt - mP[vr * 3 + c1]);
            }
          }
        });
        if (glide && glide.on > 0) {
          var Ce = G[boneIndex.chest].elements, Ci = tmp.copy(G[boneIndex.chest]).invert().elements, gq = [0, 0, 0], gp = [0, 0, 0], eps = 0.75;
          for (var gk = 0; gk < glide.verts.length; gk++) {
            var gvv = glide.verts[gk], qx0 = pos[gvv * 3], qy0 = pos[gvv * 3 + 1], qz0 = pos[gvv * 3 + 2], lx = 0, ly = 0, lz = 0;
            for (var gj2 = 0; gj2 < 4; gj2++) { var gw2 = sw[gvv * 4 + gj2]; if (!gw2) continue; xf(G[si[gvv * 4 + gj2]].elements, qx0, qy0, qz0, rp); lx += gw2 * rp[0]; ly += gw2 * rp[1]; lz += gw2 * rp[2]; }
            lx += delta[gvv * 3]; ly += delta[gvv * 3 + 1]; lz += delta[gvv * 3 + 2];
            xf(Ci, lx, ly, lz, gq);                                       // the posed point in the chest's bind frame
            var hh = torsoPrim.f(gq[0], gq[1], gq[2]), excess = hh - glide.h0[gk] - GLIDE.tol;
            if (!(excess > 0)) continue;
            var nx2 = torsoPrim.f(gq[0] + eps, gq[1], gq[2]) - torsoPrim.f(gq[0] - eps, gq[1], gq[2]);
            var ny2 = torsoPrim.f(gq[0], gq[1] + eps, gq[2]) - torsoPrim.f(gq[0], gq[1] - eps, gq[2]);
            var nz2 = torsoPrim.f(gq[0], gq[1], gq[2] + eps) - torsoPrim.f(gq[0], gq[1], gq[2] - eps);
            var nl2 = Math.sqrt(nx2 * nx2 + ny2 * ny2 + nz2 * nz2);
            if (!(nl2 > 1e-9)) continue;
            var back = glide.on * glide.k[gk] * excess / nl2;
            xf(Ce, gq[0] - nx2 * back, gq[1] - ny2 * back, gq[2] - nz2 * back, gp);
            delta[gvv * 3] += gp[0] - lx; delta[gvv * 3 + 1] += gp[1] - ly; delta[gvv * 3 + 2] += gp[2] - lz;
          }
        }
        // displacement in posed space -> bind space through the inverse of the vertex's own blend matrix (linear part)
        for (var k2 = 0; k2 < list.length; k2++) {
          var v2 = list[k2], dx = delta[v2 * 3], dy = delta[v2 * 3 + 1], dz = delta[v2 * 3 + 2];
          if (!dx && !dy && !dz) continue;
          var m = [0, 0, 0, 0, 0, 0, 0, 0, 0];
          for (var j = 0; j < 4; j++) {
            var w = sw[v2 * 4 + j]; if (!w) continue;
            var e = G[si[v2 * 4 + j]].elements;
            m[0] += w * e[0]; m[1] += w * e[1]; m[2] += w * e[2]; m[3] += w * e[4]; m[4] += w * e[5]; m[5] += w * e[6]; m[6] += w * e[8]; m[7] += w * e[9]; m[8] += w * e[10];
          }
          // column-major 3x3 [c0 | c1 | c2]; solve m * d = delta by Cramer's rule
          var det = m[0] * (m[4] * m[8] - m[7] * m[5]) - m[3] * (m[1] * m[8] - m[7] * m[2]) + m[6] * (m[1] * m[5] - m[4] * m[2]);
          if (Math.abs(det) < 1e-6) continue;
          var ix = (dx * (m[4] * m[8] - m[7] * m[5]) - m[3] * (dy * m[8] - m[7] * dz) + m[6] * (dy * m[5] - m[4] * dz)) / det;
          var iy = (m[0] * (dy * m[8] - dz * m[7]) - dx * (m[1] * m[8] - m[7] * m[2]) + m[6] * (m[1] * dz - dy * m[2])) / det;
          var iz = (m[0] * (m[4] * dz - m[5] * dy) - m[3] * (m[1] * dz - dy * m[2]) + dx * (m[1] * m[5] - m[4] * m[2])) / det;
          pos[v2 * 3] += ix; pos[v2 * 3 + 1] += iy; pos[v2 * 3 + 2] += iz;
        }
      },
      /**
       * After computeVertexNormals on the morphed bind mesh: inside the mush region the GPU's skinned normal (blend matrix times the bind
       * normal) of a strongly blended vertex points up to 150 degrees off the posed surface in a deep hinge, so the toon bands drew
       * lumps the geometry does not have. There the bind normal becomes M^-1 times the true posed normal, faded in like the mush.
       */
      normals: function (N) {
        mushes.forEach(function (mu) { if (mu.on > 0) mushNormals(mu.MD, mu.on, N); });
      },
      pairs: pairs
    };
  }

  // ------------------------------------------------------------------ attach: build one figure's skin and muscle records
  /**
   * A.attach(ctx): ctx = {root, bone, bones, skeleton, S, g, joints, boneBind, boneIndex, skinColor}.
   * Returns {muscles, skin, update(R, p, pre), roles(acts), anchor(name), windows, setWindow(name, open0, open1)}.
   */
  A.attach = function (ctx) {
    var data = A.buildData(ctx), n = data.n, root = ctx.root, bone = ctx.bone, g = ctx.g;
    var refined = data.profileSampling === 'distance', tone = refined ? LOOK.tone : LOOK.legacyTone;
    var pos0 = new Float32Array(n * 3); for (var i = 0; i < n * 3; i++) pos0[i] = data.mesh.pos[i];
    var pos = new Float32Array(pos0), colS = new Float32Array(n * 3), colC = new Float32Array(n * 3);
    var skinCol = col3(C.skin), muscleCol = col3(C.muscle), toneCol = skinCol.clone().lerp(muscleCol, tone), shortCol = col3(C.short);
    var faceCol = col3(C.face), hairCol = col3(C.hair);
    var restS = new Float32Array(n * 3), restC = new Float32Array(n * 3), tmp = new THREE.Color();
    for (var v = 0; v < n; v++) {
      tmp.copy(skinCol).lerp(muscleCol, tone * data.toneMax[v]);
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
    var normalAttr = new THREE.BufferAttribute(refined ? new Float32Array(data.normals) : data.normals, 3);
    if (refined) normalAttr.setUsage(THREE.DynamicDrawUsage);
    geo.setAttribute('normal', normalAttr);
    if (refined) {
      geo.setAttribute('aTop', new THREE.BufferAttribute(data.topOwnership, 1));
      // Cloth, band and cut windows are evaluated on the REST position: correctives and the hip mush move the morphed bind position by
      // up to ~15 units, which slid the hem and showed skin through the shorts.
      geo.setAttribute('aRest', new THREE.BufferAttribute(pos0, 3));
    }
    geo.setAttribute('color', colAttr); geo.setAttribute('colorC', colCAttr);
    geo.setAttribute('aCav', new THREE.BufferAttribute(data.cav, 1));
    geo.setAttribute('skinIndex', new THREE.BufferAttribute(data.skinIndex, 4));
    geo.setAttribute('skinWeight', new THREE.BufferAttribute(data.skinWeight, 4));
    geo.setIndex(new THREE.BufferAttribute(new Uint32Array(data.mesh.idx), 1));
    var skinOptions = { vertexColors: true, side: THREE.DoubleSide };
    if (refined) skinOptions.gradientMap = surfaceGradient();
    var skinMat = T3.material('#FFFFFF', skinOptions);
    var WU = winUniforms();
    var U = { uCloth: { value: new THREE.Vector4(CLOTH.waist, CLOTH.band, CLOTH.hem, CLOTH.lat) }, uTop: { value: new THREE.Vector4(CLOTH.topLo, CLOTH.topHi, CLOTH.topX, data.hasTop ? 1 : 0) },
      uHip: { value: new THREE.Vector3(data.hipL[0], data.hipL[1], data.hipL[2]) }, uLegAx: { value: new THREE.Vector3(data.legAx[0], data.legAx[1], data.legAx[2]) },
      uBand: { value: col3(C.band) }, uCrease: { value: refined ? LOOK.crease : LOOK.legacyCrease }, uInterior: { value: col3(LOOK.interior) }, uRim: { value: col3(LOOK.rim) }, uRimW: { value: 0.045 },
      uWc: WU.uWc, uWm: WU.uWm, uWo: WU.uWo };
    skinMat.onBeforeCompile = function (sh) {
      for (var k in U) sh.uniforms[k] = U[k];
      sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\n' + SKIN_VERT_DECL + (refined ? 'attribute float aTop; varying float vTop; attribute vec3 aRest;\n' : ''))
        .replace('#include <begin_vertex>', '#include <begin_vertex>\n  vColC = colorC; vCav = aCav; ' + (refined ? 'vBind = aRest; vTop = aTop;' : 'vBind = position;'));
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\n' + skinFragmentDecl(refined))
        .replace('#include <color_fragment>', '#include <color_fragment>\n' + SKIN_FRAG_BODY);
    };
    skinMat.customProgramCacheKey = function () { return refined ? 'tibi-skin-integrated-3' : 'tibi-skin-1'; };
    var skin = new THREE.SkinnedMesh(geo, skinMat); skin.name = 'skin'; skin.frustumCulled = false;
    root.add(skin); skin.bind(ctx.skeleton, skin.matrixWorld);

    // ---- muscle records: one per table entry that can light up; vertex lists from the top-4 masks
    var recs = [];
    data.masked.forEach(function (m) {
      var local = m.local, rec = { key: m.key, side: m.side, bone: m.bone, spec: m, slot: m.slot, level: 0, act: 0, bulge: 0, local: local, layer: m.layer, cloth: !!m.cloth,
        color: new THREE.Color(), colorC: new THREE.Color(), rest: toneCol.clone(), restC: shortCol.clone(), vi: [], vw: [], vc: [], mid: new THREE.Color(), midC: new THREE.Color(), full: new THREE.Color(), fullC: new THREE.Color() };
      recs.push(rec);
    });
    for (var v2 = 0; v2 < n; v2++) for (var q = 0; q < 8; q++) { var w = data.muw[v2 * 8 + q]; if (w > 0.02) { var r = recs[data.mus[v2 * 8 + q]]; r.vi.push(v2); r.vw.push(w); r.vc.push(data.muc ? data.muc[v2 * 8 + q] : w); } }
    recs.forEach(function (r) {
      r.vi = new Int32Array(r.vi); r.vw = new Float32Array(r.vw); r.vc = new Float32Array(r.vc); r.color.copy(r.rest); r.colorC.copy(r.restC);
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
      if (!full) { r.full.copy(r.rest); r.mid.copy(r.rest); r.midC.copy(r.restC); r.fullC.copy(r.restC); return; }
      r.full.copy(full);
      if (!refined) {
        r.mid.copy(full).lerp(col3('#FFFFFF'), 0.32);                 // skin variant: through a pale tint of the role
        r.midC.copy(full).multiplyScalar(0.62);                       // under cloth: through a deep role colour (a pale tint flashed on the dark shorts)
        r.fullC.copy(full);
        return;
      }
      // Pale cobalt sits on cobalt: a straight ramp. Through white it flashed a pale block before reaching its own colour.
      if (r.level === 1) r.mid.copy(r.rest).lerp(full, 0.4); else r.mid.copy(full).lerp(col3('#FFFFFF'), 0.32);
      // Under cloth: one straight ramp to a subdued tint of the role. The deep mid read as a dark-red stain, the full colour as a blob.
      r.fullC.copy(r.restC).lerp(full.clone().lerp(col3('#FFFFFF'), EFFORT.clothLift), EFFORT.cloth); r.midC.copy(r.restC).lerp(r.fullC, 0.4);
    }
    recs.forEach(paint);
    var dynamics = {
      biceps: function (r, R) { return (refined ? 3.2 : 5.5) * flex(R, r.side); }, triceps: function (r, R) { return (refined ? -1.2 : -2.0) * flex(R, r.side); },
      lat: function (r, R) { return 5.5 * clamp(R('sh' + r.side) / 120, 0, 1); },
      calf: function (r, R) { var k = clamp(R('hl' + r.side) / 40, 0, 1); return (r.key === 'soleus' ? 2.2 : 4.2) * k; }
    };
    function flex(R, side) { return Math.min(150, Math.max(0, bone['el' + side].rotation.x * -1 / D2R)) / 150; }
    var lastSig = '', lastShape = '', colorWeight = refined ? new Float32Array(n) : null, tmpS = new THREE.Color(), tmpC = new THREE.Color();
    var corr = refined && CORRECTIVE.pairs.length ? makeCorrective(skin, ctx.skeleton, ctx.boneIndex, data) : null;
    var body = { data: data, skin: skin, muscles: recs, recs: recs, geo: geo, material: skinMat, uniforms: U, inner: null };

    body.ensureInner = function () { if (!body.inner) { buildInternal(body, ctx); if (body.shade === 'crescent') shadeTree(body.inner.group, 'crescent'); } return body.inner; };
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
        if (body.inner && body.inner.group.visible) {
          body.inner.group.visible = false; WU_clear();
          if (skinMat.transparent) skinMat.needsUpdate = true;
          skinMat.transparent = false; skinMat.opacity = 1; skinMat.depthWrite = true; skinMat.side = THREE.DoubleSide; lastView = '';
        }
        return;
      }
      body.ensureInner();
      var wl = body.windowList, slot = 0;
      WU_clear();
      wl.forEach(function (w) {
        var open = p[pre + 'cut.' + w.name + '@' + w.side]; if (open === undefined) open = p[pre + 'cut.' + w.name];
        if (!(open > 0.001) || slot >= NWIN) return;
        U.uWc.value[slot].copy(w.c); U.uWm.value[slot].copy(w.M); U.uWo.value[slot].set(Math.min(1, open), Math.max(0, Math.min(1, open - 1)), w.sweep ? w.sweep[0] : 0, w.sweep ? w.sweep[1] : 0); slot++;
      });
      body.inner.group.visible = true;
      // ghost skin: translucent, no depth write, front faces only (so the inside of the shell does not double-draw)
      var wasGhost = skinMat.transparent;
      skinMat.transparent = ghost > 0.001; skinMat.opacity = 1 - (skel > 0.001 ? 0.95 : 0.9) * ghost; skinMat.depthWrite = !(ghost > 0.3); skinMat.side = ghost > 0.001 ? THREE.FrontSide : THREE.DoubleSide;
      if (wasGhost !== skinMat.transparent) skinMat.needsUpdate = true;
      // What is drawn is chosen, never accidental: bones with a cut, with view.skel, or behind an isolated muscle on a ghosted body;
      // muscles with a cut window (only where it opens), view.layer (the whole muscle layer), or one at a time with iso.<muscle>.
      var showBones = wlist.length > 0 || skel > 0 || layerV > 0 || (anyIso && ghost > 0);
      var windowOnly = refined && wlist.length > 0 && skel <= 0 && layerV <= 0 && !(anyIso && ghost > 0);
      body.inner.materials.forEach(function (mat) { mat.userData.U.uWindowOnly.value = windowOnly ? 1 : 0; });
      body.inner.meshes.bones.forEach(function (b) { b.mesh.visible = showBones; });
      body.inner.meshes.tendons.forEach(function (b) { b.mesh.visible = showBones && skel <= 0.001; });
      var quadOpen = wlist.some(function (n) { return n.indexOf('quad') === 0; });
      body.inner.meshes.front.forEach(function (b) { b.mesh.visible = quadOpen || skel > 0 || layerV > 0; });
      body.inner.meshes.muscles.forEach(function (g2) {
        var iso = p[pre + 'iso.' + g2.key + '@' + g2.side]; if (iso === undefined) iso = p[pre + 'iso.' + g2.key]; iso = iso || 0;
        var sg = g2.side === 'R' ? -1 : 1;
        g2.mesh.visible = (wlist.length > 0 || layerV > 0 || iso > 0.001) && !(skel > 0.001 && layerV <= 0 && iso <= 0.001 && wlist.length === 0);
        g2.material.userData.U.uOff.value.set(sg * ISO_DIST * iso, 0, 0);
        g2.material.userData.U.uWindowOnly.value = refined && wlist.length > 0 && layerV <= 0 && iso <= 0.001 ? 1 : 0;
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
      var sig = [], shape = [];
      recs.forEach(function (r) {
        var amt = p[pre + 'act.' + r.key]; if (amt === undefined) amt = p[pre + 'act.' + r.key + '@' + r.side];
        r.act = amt === undefined ? 0 : amt;
        r.bulge = r.spec.dyn ? dynamics[r.spec.dyn](r, R) : 0;
        ramp(r.color, r.rest, r.mid, r.full, r.level ? r.act : 0);
        ramp(r.colorC, r.restC, r.midC, r.fullC, r.level ? r.act : 0);
        // Cache exact outputs: rounding keeps a neighbouring frame's geometry or colours on a seek.
        sig.push(r.color.r, r.color.g, r.color.b, r.colorC.r, r.colorC.g, r.colorC.b, r.bulge);
        shape.push(r.bulge);
      });
      views(R, p, pre);
      if (corr) { var cSig = corr.pose(); sig.push(cSig); shape.push(cSig); }
      var s = sig.join(',');
      if (s === lastSig) return false;
      lastSig = s;
      colS.set(restS); colC.set(restC); pos.set(pos0);
      if (refined) colorWeight.fill(0);
      recs.forEach(function (r) {
        var dr = r.color.r - r.rest.r, dg = r.color.g - r.rest.g, db = r.color.b - r.rest.b;
        var cr = r.colorC.r - r.restC.r, cg = r.colorC.g - r.restC.g, cb = r.colorC.b - r.restC.b;
        var colorOn = dr || dg || db || cr || cg || cb, vi = r.vi, vw = r.vw, vc = r.vc, nn = vi.length;
        if (refined && r.level) {
          // The spatial fade follows the same ramp as the activation (rest, pale role tint, role): a vertex at effort weight w shows
          // the colour of activation act * w. A straight blend from cobalt to coral read purple at every soft edge.
          for (var k = 0; k < nn; k++) {
            var vv = vi[k], v3 = vv * 3, w = vc[k];
            if (!(w > 0)) continue;
            colorWeight[vv] += w;
            vtxRamp(tmpS, restS, v3, r.mid, r.full, r.act * w);
            vtxRamp(tmpC, restC, v3, r.midC, r.fullC, r.act * w);
            colS[v3] += w * (tmpS.r - restS[v3]); colS[v3 + 1] += w * (tmpS.g - restS[v3 + 1]); colS[v3 + 2] += w * (tmpS.b - restS[v3 + 2]);
            colC[v3] += w * (tmpC.r - restC[v3]); colC[v3 + 1] += w * (tmpC.g - restC[v3 + 1]); colC[v3 + 2] += w * (tmpC.b - restC[v3 + 2]);
          }
        } else if (!refined && colorOn) {
          for (var k = 0; k < nn; k++) {
            var v3 = vi[k] * 3, w = vw[k];
            colS[v3] += w * dr; colS[v3 + 1] += w * dg; colS[v3 + 2] += w * db; colC[v3] += w * cr; colC[v3 + 1] += w * cg; colC[v3 + 2] += w * cb;
          }
        }
        if (r.bulge) for (var k2 = 0; k2 < nn; k2++) {
          var v4 = vi[k2] * 3, b = r.bulge * vw[k2];
          pos[v4] += data.normals[v4] * b; pos[v4 + 1] += data.normals[v4 + 1] * b; pos[v4 + 2] += data.normals[v4 + 2] * b;
        }
      });
      if (refined) {
        // Weighted mean of the overlapping muscles' colours (each already faded by its own weight): no clipping, no doubled slope.
        for (var v7 = 0; v7 < n; v7++) if (colorWeight[v7] > 0) {
          for (var channel = 0; channel < 3; channel++) {
            var ci = v7 * 3 + channel;
            colS[ci] = restS[ci] + (colS[ci] - restS[ci]) / colorWeight[v7];
            colC[ci] = restC[ci] + (colC[ci] - restC[ci]) / colorWeight[v7];
          }
        }
        if (corr) corr.apply(pos);
        var shapeSig = shape.join(',');
        if (shapeSig !== lastShape) { geo.computeVertexNormals(); if (corr) corr.normals(normalAttr.array); lastShape = shapeSig; }
      }
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
