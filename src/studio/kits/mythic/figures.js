/*
 * Motion Lab mythic kit - figure library (src/studio/kits/mythic/figures.js)
 *
 * Jointed figures for shadow puppets and paper cut-outs, built from a shared skeleton with
 * geometry helpers, so every figure poses with the same part ids:
 *   standing (viewBox 200 x 400, profile facing right):
 *     pelvis > leg-back*, leg-front, garment, torso > arm-back* > hand-back > prop-back,
 *     head > headgear..., arm-front > hand-front > prop-front      (* drawn behind its parent)
 *   seated (viewBox 240 x 300, frontal): pedestal > emblem, legs, body > head > ...
 * Two builds share the skeleton: 'classic' (default) and 'heroic' (muscular classical ideal; '<id>-heroic'
 * or figureOptions {build: 'heroic'}). Load after mythic.js. Use with Studio.kit.mythic.puppet(parent, {figure: 'hanuman', look}) or
 * cutout(...). Each figure carries meta {name, tradition, emblems, check} for labels.
 *
 * These are stylised silhouettes for storytelling, not icons for worship. Every attribute was set
 * from the tradition packs (.claude/skills/mythic-tales/references/traditions/); a reviewer still
 * checks each figure against the telling the film follows (quality-rubric.md, gate 2).
 */
(function (global) {
  'use strict';

  var Studio = global.Studio || (global.Studio = {});
  var KIT = Studio.kit = Studio.kit || {};
  var M = KIT.mythic = KIT.mythic || {};
  var FIG = M.figures = M.figures || {};

  // ------------------------------------------------------------------ geometry
  function r2(n) { return Math.round(n * 100) / 100; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function d(polys) {
    return polys.map(function (pts) {
      return 'M' + pts.map(function (p) { return r2(p[0]) + ' ' + r2(p[1]); }).join('L') + 'Z';
    }).join(' ');
  }

  /** Catmull-Rom through the points (closed or open), `per` samples per segment. */
  function smooth(pts, closed, per) {
    per = per || 6;
    var n = pts.length, out = [];
    if (n < 3) return pts.slice();
    var get = function (i) { return closed ? pts[((i % n) + n) % n] : pts[Math.max(0, Math.min(n - 1, i))]; };
    var segs = closed ? n : n - 1;
    for (var i = 0; i < segs; i++) {
      var p0 = get(i - 1), p1 = get(i), p2 = get(i + 1), p3 = get(i + 2);
      for (var s = 0; s < per; s++) {
        var t = s / per, t2 = t * t, t3 = t2 * t;
        out.push([0, 1].map(function (k) {
          return 0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3);
        }));
      }
    }
    if (!closed) out.push(pts[n - 1].slice());
    return out;
  }

  /** Tapered tube with round caps along a (smoothed) centre line: limbs, tails, shafts, trunks. */
  function tube(ctrl, radii, opts) {
    var o = opts || {};
    var pts = ctrl.length > 2 && o.smooth !== false ? smooth(ctrl, false, o.per || 6) : ctrl;
    var n = pts.length, cap = o.cap === undefined ? 8 : o.cap;
    var rs = typeof radii === 'number' ? [radii] : radii;
    var rad = function (i) {
      if (rs.length === 1) return rs[0];
      var t = (n === 1 ? 0 : i / (n - 1)) * (rs.length - 1), k = Math.min(rs.length - 2, Math.floor(t));
      return lerp(rs[k], rs[k + 1], t - k);
    };
    var L = [], R = [], N = [], i, k;
    for (i = 0; i < n; i++) {
      var a = pts[Math.max(0, i - 1)], b = pts[Math.min(n - 1, i + 1)];
      var tx = b[0] - a[0], ty = b[1] - a[1], l = Math.sqrt(tx * tx + ty * ty) || 1;
      var nx = -ty / l, ny = tx / l, r = rad(i);
      L.push([pts[i][0] + nx * r, pts[i][1] + ny * r]);
      R.push([pts[i][0] - nx * r, pts[i][1] - ny * r]);
      N.push([nx, ny, r]);
    }
    var out = L.slice(), e = N[n - 1], pe = pts[n - 1], an = Math.atan2(e[1], e[0]);
    for (k = 1; k < cap; k++) out.push([pe[0] + Math.cos(an - Math.PI * k / cap) * e[2], pe[1] + Math.sin(an - Math.PI * k / cap) * e[2]]);
    out = out.concat(R.reverse());
    var s0 = N[0], ps = pts[0], as = Math.atan2(s0[1], s0[0]);
    for (k = 1; k < cap; k++) out.push([ps[0] + Math.cos(as + Math.PI - Math.PI * k / cap) * s0[2], ps[1] + Math.sin(as + Math.PI - Math.PI * k / cap) * s0[2]]);
    return out;
  }

  /** Ellipse (or arc of one) as points. */
  function ell(cx, cy, rx, ry, a0, a1, n) {
    var from = a0 === undefined ? 0 : a0, to = a1 === undefined ? Math.PI * 2 : a1, m = n || 36, out = [];
    var full = a0 === undefined;
    for (var i = 0; i < (full ? m : m + 1); i++) {
      var a = from + (to - from) * i / m;
      out.push([cx + Math.cos(a) * rx, cy + Math.sin(a) * ry]);
    }
    return out;
  }
  function mirror(pts, cx) { return pts.map(function (p) { return [2 * cx - p[0], p[1]]; }).reverse(); }
  function shift(pts, dx, dy) { return pts.map(function (p) { return [p[0] + dx, p[1] + dy]; }); }
  function scaleX(pts, cx, s) { return pts.map(function (p) { return [cx + (p[0] - cx) * s, p[1]]; }); }
  function blob(pts) { return smooth(pts, true, 5); }

  M.geom = { smooth: smooth, tube: tube, ell: ell, mirror: mirror, shift: shift, pathData: d };

  // ------------------------------------------------------------------ small glyphs (emblems, animals, birds)
  var GLYPH = {
    lion: function (cx, cy, s) {
      var P = [ell(cx - 0.02 * s, cy, 0.4 * s, 0.17 * s), ell(cx + 0.32 * s, cy - 0.12 * s, 0.2 * s, 0.24 * s), ell(cx + 0.46 * s, cy - 0.1 * s, 0.12 * s, 0.1 * s)];
      [-0.3, -0.14, 0.12, 0.26].forEach(function (x) { P.push(tube([[cx + x * s, cy + 0.08 * s], [cx + x * s, cy + 0.4 * s]], 0.045 * s, { cap: 4 })); });
      P.push(tube([[cx - 0.38 * s, cy - 0.04 * s], [cx - 0.58 * s, cy - 0.2 * s], [cx - 0.52 * s, cy - 0.38 * s]], [0.03 * s, 0.02 * s], { cap: 4 }));
      P.push(ell(cx - 0.52 * s, cy - 0.4 * s, 0.06 * s, 0.06 * s));
      return P;
    },
    bull: function (cx, cy, s) {
      var P = [ell(cx, cy, 0.4 * s, 0.19 * s), ell(cx + 0.16 * s, cy - 0.17 * s, 0.13 * s, 0.1 * s), ell(cx + 0.48 * s, cy - 0.06 * s, 0.12 * s, 0.1 * s)];
      P.push(tube([[cx + 0.44 * s, cy - 0.14 * s], [cx + 0.4 * s, cy - 0.28 * s], [cx + 0.46 * s, cy - 0.36 * s]], [0.035 * s, 0.015 * s], { cap: 4 }));
      P.push(tube([[cx + 0.54 * s, cy - 0.14 * s], [cx + 0.6 * s, cy - 0.28 * s], [cx + 0.56 * s, cy - 0.36 * s]], [0.035 * s, 0.015 * s], { cap: 4 }));
      [-0.28, -0.12, 0.14, 0.28].forEach(function (x) { P.push(tube([[cx + x * s, cy + 0.1 * s], [cx + x * s, cy + 0.42 * s]], 0.05 * s, { cap: 4 })); });
      P.push(tube([[cx - 0.38 * s, cy - 0.04 * s], [cx - 0.48 * s, cy + 0.2 * s]], 0.025 * s, { cap: 4 }));
      return P;
    },
    deer: function (cx, cy, s) {
      var P = [ell(cx, cy, 0.34 * s, 0.14 * s), tube([[cx + 0.26 * s, cy - 0.04 * s], [cx + 0.38 * s, cy - 0.36 * s]], [0.07 * s, 0.05 * s], { cap: 4 }), ell(cx + 0.45 * s, cy - 0.38 * s, 0.11 * s, 0.06 * s)];
      P.push(tube([[cx + 0.38 * s, cy - 0.42 * s], [cx + 0.34 * s, cy - 0.62 * s], [cx + 0.26 * s, cy - 0.72 * s]], 0.018 * s, { cap: 3 }));
      P.push(tube([[cx + 0.35 * s, cy - 0.56 * s], [cx + 0.44 * s, cy - 0.68 * s]], 0.016 * s, { cap: 3 }));
      [-0.26, -0.12, 0.12, 0.24].forEach(function (x) { P.push(tube([[cx + x * s, cy + 0.08 * s], [cx + x * s, cy + 0.46 * s]], 0.03 * s, { cap: 3 })); });
      return P;
    },
    conch: function (cx, cy, s) {
      return [blob([[cx - 0.42 * s, cy + 0.02 * s], [cx - 0.12 * s, cy - 0.28 * s], [cx + 0.3 * s, cy - 0.26 * s], [cx + 0.46 * s, cy], [cx + 0.3 * s, cy + 0.22 * s], [cx - 0.1 * s, cy + 0.26 * s]]),
        tube([[cx + 0.42 * s, cy - 0.06 * s], [cx + 0.56 * s, cy - 0.16 * s]], [0.06 * s, 0.03 * s], { cap: 4 })];
    },
    mouse: function (cx, cy, s) {
      return [blob([[cx - 0.36 * s, cy + 0.04 * s], [cx - 0.1 * s, cy - 0.2 * s], [cx + 0.26 * s, cy - 0.14 * s], [cx + 0.5 * s, cy + 0.04 * s], [cx + 0.26 * s, cy + 0.16 * s], [cx - 0.1 * s, cy + 0.2 * s]]),
        ell(cx + 0.18 * s, cy - 0.18 * s, 0.09 * s, 0.09 * s),
        tube([[cx - 0.34 * s, cy + 0.04 * s], [cx - 0.56 * s, cy - 0.06 * s], [cx - 0.66 * s, cy + 0.08 * s]], [0.025 * s, 0.012 * s], { cap: 3 })];
    },
    bird: function (cx, cy, s, dir) {
      var k = dir || 1;
      return [ell(cx, cy, 0.34 * s, 0.16 * s), ell(cx + 0.3 * s * k, cy - 0.12 * s, 0.13 * s, 0.12 * s),
        [[cx + 0.4 * s * k, cy - 0.16 * s], [cx + 0.6 * s * k, cy - 0.1 * s], [cx + 0.4 * s * k, cy - 0.06 * s]],
        [[cx - 0.26 * s * k, cy - 0.04 * s], [cx - 0.62 * s * k, cy + 0.02 * s], [cx - 0.3 * s * k, cy + 0.1 * s]],
        [[cx - 0.1 * s * k, cy - 0.08 * s], [cx - 0.3 * s * k, cy - 0.42 * s], [cx + 0.14 * s * k, cy - 0.08 * s]]];
    }
  };
  M.glyphs = GLYPH;

  // ------------------------------------------------------------------ standing body (profile, facing right)
  var J = {
    hip: [102, 206], waist: [102, 198], neck: [107, 104],
    shF: [114, 122], shB: [94, 120], elF: [127, 168], elB: [86, 168], wrF: [143, 198], wrB: [80, 200],
    hipF: [110, 214], hipB: [95, 214], knF: [115, 300], knB: [93, 300], anF: [118, 380], anB: [86, 382]
  };
  M.skeleton = J;

  var GARMENTS = {
    dhoti: { pts: [[83, 192], [121, 194], [128, 236], [127, 284], [117, 300], [107, 291], [98, 299], [86, 291], [79, 240]], detail: 'M104 202 L105 290 M113 203 L118 286 M84 204 Q102 212 121 206' },
    chiton: { pts: [[84, 190], [120, 192], [127, 250], [135, 372], [126, 388], [84, 388], [72, 372], [78, 252]], detail: 'M96 204 L90 382 M106 204 L106 384 M116 204 L124 382' },
    tunic: { pts: [[82, 184], [122, 186], [128, 240], [134, 302], [76, 302], [78, 240]], detail: 'M80 236 L128 236 M104 190 L104 298' },
    tiger: { pts: [[83, 192], [121, 194], [128, 236], [127, 284], [117, 300], [107, 291], [98, 299], [86, 291], [79, 240]], detail: 'M86 222 l8 4 M96 246 l9 3 M112 230 l8 5 M118 262 l6 4 M90 272 l8 4 M106 270 l7 5' }
  };

  function profileHead() {
    return d([blob([[99, 66], [110, 62], [121, 66], [125, 76], [131, 85], [125, 89], [124, 96], [115, 100], [104, 99], [97, 90], [96, 78]])]);
  }

  /**
   * Base standing figure. o {k (bulk), female, build ('classic' | 'heroic'), skin, skinBack, cloth,
   * torsoFill, garment, head (d), faceDetail}. Returns the part list; figures add headgear, props
   * and attributes to it. 'heroic' keeps every joint, so poses are shared between builds.
   */
  function standing(o) {
    if (o.build === 'heroic') return standingHeroic(o);
    var k = o.k || 1, cx = 102;
    var skin = o.skin || '--c-leather-ochre', back = o.skinBack || skin, cloth = o.cloth || '--c-leather-red';
    var g = GARMENTS[o.garment || 'dhoti'];
    var torso = o.female
      ? [[90, 116], [106, 108], [120, 116], [124, 134], [118, 160], [112, 184], [116, 200], [88, 200], [92, 184], [88, 160], [86, 136]]
      : [[88, 114], [104, 106], [121, 114], [127, 136], [123, 162], [116, 186], [119, 202], [86, 202], [88, 186], [84, 162], [84, 136]];
    var footB = tube([[80, 388], [100, 390]], [5.5, 3.2], { cap: 6 });
    var footF = tube([[114, 386], [136, 390]], [6, 3.4], { cap: 6 });
    return [
      { id: 'pelvis', pivot: J.hip, fill: cloth, d: d([blob(scaleX([[86, 198], [118, 198], [122, 214], [112, 226], [92, 226], [82, 214]], cx, k))]) },
      { id: 'leg-back', parent: 'pelvis', behind: true, pivot: J.hipB, fill: back, d: d([tube([J.hipB, J.knB, J.anB], [12 * k, 7.5 * k, 4.8 * k]), footB]) },
      { id: 'leg-front', parent: 'pelvis', pivot: J.hipF, fill: skin, d: d([tube([J.hipF, J.knF, J.anF], [13 * k, 8 * k, 5.2 * k]), footF]) },
      { id: 'garment', parent: 'pelvis', pivot: J.hip, fill: cloth, d: d([blob(scaleX(g.pts, cx, k))]), detail: g.detail },
      { id: 'torso', parent: 'pelvis', pivot: J.waist, fill: o.torsoFill || skin,
        d: d([blob(scaleX(torso, cx, k)), tube([[104, 116], [108, 96]], [7 * k, 6 * k])]),
        detail: o.female ? 'M96 122 Q108 134 120 122' : 'M96 120 Q108 136 121 122 M100 126 Q108 140 118 128' },
      { id: 'arm-back', parent: 'torso', behind: true, pivot: J.shB, fill: back, d: d([tube([J.shB, J.elB], [8 * k, 6 * k])]) },
      { id: 'hand-back', parent: 'arm-back', pivot: J.elB, rod: J.wrB, fill: back, d: d([tube([J.elB, J.wrB], [6 * k, 4.5 * k]), ell(J.wrB[0], J.wrB[1] + 6, 5 * k, 6.5 * k)]) },
      { id: 'head', parent: 'torso', pivot: J.neck, fill: skin, d: o.head || profileHead(), detail: o.faceDetail || 'M116 77 q3 -1.6 6 0 M117 93 q3 1 6 -1' },
      { id: 'arm-front', parent: 'torso', pivot: J.shF, fill: skin, d: d([tube([J.shF, J.elF], [8.5 * k, 6 * k])]), detail: 'M118 140 l9 -2' },
      { id: 'hand-front', parent: 'arm-front', pivot: J.elF, rod: J.wrF, fill: skin, d: d([tube([J.elF, J.wrF], [6 * k, 4.6 * k]), ell(J.wrF[0] + 3, J.wrF[1] + 4, 6 * k, 5.5 * k)]) }
    ];
  }

  /**
   * Heroic build: the classical ideal of the traditions' own sculpture (broad shoulders, deep chest,
   * narrow waist, defined limbs), on the same joints as the classic build. Women get an athletic,
   * strong build with covered torso detail only (no sexualised anatomy).
   */
  function standingHeroic(o) {
    var f = o.female ? 0.88 : 1;
    var k = 1 + ((o.k || 1) - 1) * 0.5, s = k * f, cx = 102;
    var skin = o.skin || '--c-leather-ochre', back = o.skinBack || skin, cloth = o.cloth || '--c-leather-red';
    var g = GARMENTS[o.garment || 'dhoti'];
    // V-taper: shoulders 76-132, waist 92-114 (classic: 84-127 and 88-116). Front of the chest faces right.
    var torso = o.female
      ? [[96, 110], [86, 116], [80, 126], [84, 146], [92, 166], [96, 184], [92, 202], [116, 202], [112, 184], [116, 166], [122, 148], [126, 128], [120, 114], [110, 108]]
      : [[97, 104], [84, 109], [71, 120], [72, 140], [81, 160], [92, 182], [88, 202], [118, 204], [114, 184], [120, 166], [131, 150], [137, 132], [131, 115], [117, 103]];
    var pelvis = o.female
      ? [[88, 198], [118, 198], [124, 214], [112, 228], [92, 228], [80, 214]]
      : [[88, 198], [116, 198], [120, 214], [112, 226], [92, 226], [84, 214]];
    var footB = tube([[80, 388], [101, 390]], [6, 3.4], { cap: 6 });
    var footF = tube([[114, 386], [137, 390]], [6.5, 3.6], { cap: 6 });
    // Limbs: control points put the belly of each muscle mid-segment (quad, calf, biceps, forearm).
    var legF = tube([J.hipF, [114, 252], J.knF, [120, 326], J.anF], [16 * s, 14.6 * s, 8.6 * s, 11.2 * s, 5.4 * s]);
    var legB = tube([J.hipB, [93, 252], J.knB, [89, 326], J.anB], [15 * s, 13.6 * s, 8.2 * s, 10.6 * s, 5.2 * s]);
    // The round shoulder cap of the upper-arm tube is the deltoid; no separate shape, so no stray outlines.
    var armF = [tube([[115, 124], [122, 142], J.elF], [14 * s, 12.8 * s, 7.4 * s], { cap: 12 })];
    var armB = [tube([[93, 122], [87, 142], J.elB], [13 * s, 11.6 * s, 7 * s], { cap: 12 })];
    var foreF = [tube([J.elF, [133, 177], J.wrF], [7.8 * s, 9.8 * s, 5.4 * s]), ell(J.wrF[0] + 3, J.wrF[1] + 4, 7.2 * s, 6.4 * s)];
    var foreB = [tube([J.elB, [82, 181], J.wrB], [7.4 * s, 9.2 * s, 5.2 * s]), ell(J.wrB[0], J.wrB[1] + 6, 6 * s, 7.4 * s)];
    // Bare torsos show the classical anatomy; a clothed torso (tunic, chiton) shows only the chest line.
    var clothed = o.torsoFill && o.torsoFill !== skin;
    var torsoDetail = o.female || clothed
      ? 'M92 118 Q104 124 118 116 M100 130 Q114 140 128 132'
      : 'M92 116 Q104 121 118 113 M100 124 Q118 146 132 136 M111 148 L112 190 M101 156 q10 3 20 -1 M101 168 q10 3 18 -1 M102 180 q8 2 14 -1 M84 140 l7 4 M86 150 l7 4 M92 174 q6 12 18 18';
    return [
      { id: 'pelvis', pivot: J.hip, fill: cloth, d: d([blob(scaleX(pelvis, cx, k))]) },
      { id: 'leg-back', parent: 'pelvis', behind: true, pivot: J.hipB, fill: back, d: d([legB, footB]) },
      { id: 'leg-front', parent: 'pelvis', pivot: J.hipF, fill: skin, d: d([legF, footF]), detail: 'M110 298 q6 4 11 0 M124 314 q5 16 0 34' },
      { id: 'garment', parent: 'pelvis', pivot: J.hip, fill: cloth, d: d([blob(scaleX(g.pts, cx, k))]), detail: g.detail },
      { id: 'torso', parent: 'pelvis', pivot: J.waist, fill: o.torsoFill || skin,
        d: d([blob(scaleX(torso, cx, k)), tube([[104, 118], [108, 96]], [10.5 * s, 8 * s])]),
        detail: torsoDetail },
      { id: 'arm-back', parent: 'torso', behind: true, pivot: J.shB, fill: back, d: d(armB) },
      { id: 'hand-back', parent: 'arm-back', pivot: J.elB, rod: J.wrB, fill: back, d: d(foreB) },
      { id: 'head', parent: 'torso', pivot: J.neck, fill: skin, d: o.head || profileHead(), detail: o.faceDetail || 'M116 77 q3 -1.6 6 0 M117 93 q3 1 6 -1' },
      { id: 'arm-front', parent: 'torso', pivot: J.shF, fill: skin, d: d(armF), detail: o.female ? 'M107 130 q9 5 17 0' : 'M107 129 q9 6 18 1 M122 138 q7 12 3 26' },
      { id: 'hand-front', parent: 'arm-front', pivot: J.elF, rod: J.wrF, fill: skin, d: d(foreF), detail: o.female ? '' : 'M130 174 q6 8 8 18' }
    ];
  }

  // Figures take {build}; meta records it and the id gains '-heroic'.
  function buildOf(opt) { return opt && opt.build === 'heroic' ? 'heroic' : 'classic'; }
  function figMeta(m, opt) {
    m.build = buildOf(opt);
    if (m.build === 'heroic') m.id = m.id + '-heroic';
    return m;
  }

  function add(parts, part) { parts.push(part); return parts; }
  function crown(tall) {
    var t = tall ? 1 : 0.62;
    return d([[[98, 70], [126, 70], [122, 70 - 18 * t], [117, 70 - 40 * t], [111, 70 - 64 * t], [105, 70 - 40 * t], [101, 70 - 18 * t]], ell(112, 70, 15, 4)]);
  }

  // ------------------------------------------------------------------ props
  var PROP = {
    bow: function (w) {
      var top = [w[0] - 2, w[1] - 104], bot = [w[0] - 2, w[1] + 96];
      return d([tube([top, [w[0] - 24, w[1] - 50], [w[0] - 28, w[1]], [w[0] - 24, w[1] + 48], bot], [1.6, 3.4, 3.6, 3.4, 1.6]), tube([top, bot], 0.7, { cap: 3 })]);
    },
    arrow: function (w) {
      return d([tube([[w[0] - 30, w[1] + 8], [w[0] + 46, w[1] - 6]], 1.2, { cap: 3 }), [[w[0] + 44, w[1] - 11], [w[0] + 58, w[1] - 8], [w[0] + 46, w[1] - 1]], [[w[0] - 30, w[1] + 8], [w[0] - 40, w[1] + 2], [w[0] - 36, w[1] + 9], [w[0] - 40, w[1] + 15]]]);
    },
    quiver: function () {
      return d([blob([[78, 112], [88, 106], [100, 168], [90, 172]]), [[80, 106], [76, 92], [84, 100]], [[86, 104], [86, 88], [90, 100]]]);
    },
    mace: function (w) {
      var top = [w[0] - 4, w[1] - 74];
      return d([tube([[w[0] + 1, w[1] + 22], top], 2.6), blob([[top[0], top[1] + 6], [top[0] + 13, top[1] - 6], [top[0] + 13, top[1] - 26], [top[0], top[1] - 38], [top[0] - 13, top[1] - 26], [top[0] - 13, top[1] - 6]]), ell(top[0], top[1] - 42, 4.5, 4.5), ell(w[0] + 1, w[1] + 24, 4, 4)]);
    },
    trident: function (w) {
      var y0 = w[1] - 150, x = w[0] + 1;
      return d([tube([[x, w[1] + 46], [x, y0]], 2.2),
        [[x - 3, y0 + 2], [x, y0 - 40], [x + 3, y0 + 2]],
        tube([[x - 2, y0 + 8], [x - 16, y0 - 2], [x - 14, y0 - 26]], [2.6, 2.2, 0.6], { cap: 3 }),
        tube([[x + 2, y0 + 8], [x + 16, y0 - 2], [x + 14, y0 - 26]], [2.6, 2.2, 0.6], { cap: 3 }),
        ell(x, y0 + 8, 9, 3)]);
    },
    damaru: function (w) {
      var x = w[0] + 9, y = w[1] - 126;
      return d([[[x - 6, y - 8], [x + 6, y - 8], [x + 1, y], [x + 6, y + 8], [x - 6, y + 8], [x - 1, y]]]);
    },
    spear: function (w, up) {
      var top = w[1] - (up || 168), x = w[0] + 1;
      return d([tube([[x, w[1] + 120], [x, top]], 2), blob([[x, top - 30], [x + 6, top - 10], [x, top + 4], [x - 6, top - 10]])]);
    },
    shield: function (w) {
      return d([ell(w[0] - 6, w[1] - 18, 30, 34, undefined, undefined, 48)]);
    }
  };
  M.props = PROP;

  // ------------------------------------------------------------------ standing figures
  FIG.rama = function (opt) {
    var parts = standing({ build: buildOf(opt), skin: '--c-leather-blue', cloth: '--c-leather-ochre' });
    add(parts, { id: 'quiver', parent: 'torso', behind: true, pivot: J.shB, fill: '--c-leather-red', d: PROP.quiver(), detail: 'M84 118 L94 166' });
    add(parts, { id: 'crown', parent: 'head', pivot: J.neck, fill: '--c-gold', d: crown(true), detail: 'M101 60 H123 M104 48 H120 M107 34 H117' });
    add(parts, { id: 'prop-back', parent: 'hand-back', pivot: J.wrB, fill: '--c-leather-red', d: PROP.bow(J.wrB) });
    add(parts, { id: 'prop-front', parent: 'hand-front', pivot: J.wrF, fill: '--c-gold', d: PROP.arrow(J.wrF) });
    return { viewBox: [200, 400], parts: parts,
      meta: figMeta({ id: 'rama', name: 'Rama', tradition: 'indian', emblems: ['bow', 'arrows', 'crown'], check: 'traditions/indian.md: bow and quiver, dark skin, crown (check)' }, opt) };
  };

  FIG.hanuman = function (opt) {
    var head = d([blob([[97, 70], [108, 63], [119, 66], [123, 74], [122, 82]]), blob([[116, 80], [128, 80], [136, 88], [134, 98], [124, 102], [114, 98]]), blob([[97, 70], [95, 84], [100, 98], [112, 104], [120, 100], [122, 82]]), ell(98, 80, 5.5, 6.5)]);
    var parts = standing({ build: buildOf(opt), k: 1.18, skin: '--c-leather-red', cloth: '--c-leather-ochre', head: head, faceDetail: 'M110 76 q3 -2 6 0 M122 97 q6 2 11 -2 M106 72 q8 -4 16 0 M127 85 l2 2' });
    add(parts, { id: 'tail', parent: 'pelvis', behind: true, pivot: [90, 204], fill: '--c-leather-red',
      d: d([tube([[90, 206], [68, 208], [52, 188], [50, 150], [60, 120], [76, 108], [86, 114], [82, 126]], [6, 5, 4.2, 3.6, 3, 2.6, 2, 1.4])]) });
    add(parts, { id: 'crown', parent: 'head', pivot: J.neck, fill: '--c-gold', d: crown(false), detail: 'M102 64 H122 M106 54 H118' });
    add(parts, { id: 'prop-front', parent: 'hand-front', pivot: J.wrF, fill: '--c-gold', d: PROP.mace(J.wrF), detail: 'M' + (J.wrF[0] - 14) + ' ' + (J.wrF[1] - 88) + ' h20 M' + (J.wrF[0] - 15) + ' ' + (J.wrF[1] - 100) + ' h22' });
    return { viewBox: [200, 400], parts: parts,
      meta: figMeta({ id: 'hanuman', name: 'Hanuman', tradition: 'indian', emblems: ['mace (gada)', 'tail', 'monkey face'], check: 'traditions/indian.md: mace, monkey face (check)' }, opt) };
  };

  FIG.shiva = function (opt) {
    var parts = standing({ build: buildOf(opt), skin: '--c-peacock', cloth: '--c-leather-ochre', garment: 'tiger', faceDetail: 'M116 77 q3 -1.6 6 0 M117 93 q3 1 6 -1 M114 68 l0 5' });
    add(parts, { id: 'locks', parent: 'head', behind: true, pivot: J.neck, fill: '--c-ink-2',
      d: d([tube([[100, 74], [90, 92], [86, 120]], [4, 2], { cap: 4 }), tube([[98, 80], [84, 100], [80, 126]], [3.6, 1.6], { cap: 4 }), tube([[102, 70], [94, 86], [94, 110]], [3.4, 1.6], { cap: 4 })]) });
    add(parts, { id: 'jata', parent: 'head', pivot: J.neck, fill: '--c-ink-2', d: d([ell(110, 62, 12, 9), ell(108, 48, 9, 12), ell(108, 34, 6, 7)]), detail: 'M101 50 q7 4 14 0 M102 60 q8 3 16 0' });
    add(parts, { id: 'moon', parent: 'jata', pivot: [118, 44], fill: '--c-gold-light', d: d([ell(120, 44, 7, 7, -Math.PI * 0.4, Math.PI * 1.1, 14).concat(ell(122, 42, 5.4, 5.4, Math.PI * 1.1, -Math.PI * 0.4, 14))]) });
    add(parts, { id: 'serpent', parent: 'torso', pivot: [106, 108], fill: '--c-malachite',
      d: d([tube([[94, 108], [104, 116], [116, 114], [122, 104], [121, 94]], [2.8, 2.6, 2.4, 2.2, 2]), ell(121, 90, 4.5, 5.5)]) });
    add(parts, { id: 'prop-front', parent: 'hand-front', pivot: J.wrF, fill: '--c-gold', d: PROP.trident(J.wrF) });
    add(parts, { id: 'damaru', parent: 'prop-front', pivot: J.wrF, fill: '--c-leather-red', d: PROP.damaru(J.wrF) });
    return { viewBox: [200, 400], parts: parts,
      meta: figMeta({ id: 'shiva', name: 'Shiva', tradition: 'indian', emblems: ['trident', 'crescent moon', 'serpent', 'matted locks', 'damaru'], check: 'traditions/indian.md: trident, serpent, crescent, matted locks (verified); damaru (check)' }, opt) };
  };

  FIG.athena = function (opt) {
    var parts = standing({ build: buildOf(opt), female: true, k: 0.92, skin: '--c-leather-ochre', cloth: '--c-leather-blue', torsoFill: '--c-leather-blue', garment: 'chiton', faceDetail: 'M116 78 q3 -1.6 6 0 M117 93 q3 1 5 -1' });
    add(parts, { id: 'hair', parent: 'head', behind: true, pivot: J.neck, fill: '--c-ink-2', d: d([ell(98, 92, 8, 9), tube([[98, 76], [94, 96], [96, 112]], [5, 3], { cap: 4 })]) });
    add(parts, { id: 'aegis', parent: 'torso', pivot: J.neck, fill: '--c-gold-light',
      d: d([blob([[90, 112], [106, 106], [122, 114], [124, 128], [116, 136], [106, 132], [96, 136], [88, 126]])]), detail: 'M92 130 l3 4 M100 134 l3 4 M108 133 l3 4 M116 133 l3 4 M106 116 a5 5 0 1 0 0.1 0' });
    add(parts, { id: 'helmet', parent: 'head', pivot: J.neck, fill: '--c-gold',
      d: d([ell(111, 72, 17, 13, Math.PI, Math.PI * 2, 24).concat([[128, 76], [94, 76]]), [[122, 64], [136, 68], [131, 76], [120, 74]]]), detail: 'M96 72 H126' });
    add(parts, { id: 'crest', parent: 'helmet', pivot: [110, 58], fill: '--c-leather-red', d: d([tube([[122, 60], [112, 44], [96, 40], [84, 50], [80, 70]], [2.5, 6, 7, 5, 1.6])]) });
    add(parts, { id: 'prop-back', parent: 'hand-back', pivot: J.wrB, fill: '--c-gold', d: PROP.shield(J.wrB), detail: 'M' + (J.wrB[0] - 6) + ' ' + (J.wrB[1] - 46) + ' a26 30 0 1 0 0.1 0' });
    add(parts, { id: 'prop-front', parent: 'hand-front', pivot: J.wrF, fill: '--c-gold', d: PROP.spear(J.wrF, 162) });
    return { viewBox: [200, 400], parts: parts,
      meta: figMeta({ id: 'athena', name: 'Athena', tradition: 'greek', emblems: ['helmet', 'spear', 'shield', 'aegis'], check: 'traditions/greek-roman.md: helmet, spear, aegis, owl (check on the object shown)' }, opt) };
  };

  FIG.odin = function (opt) {
    var parts = standing({ build: buildOf(opt), skin: '--c-leather-ochre', cloth: '--c-leather-blue', torsoFill: '--c-leather-blue', garment: 'tunic', faceDetail: 'M114 76 l8 2 M100 72 L126 84' });
    add(parts, { id: 'cloak', parent: 'pelvis', behind: true, pivot: J.hip, fill: '--c-leather-red', d: d([blob([[86, 108], [116, 108], [126, 180], [132, 300], [118, 342], [70, 344], [64, 300], [72, 180]])]), detail: 'M84 140 L76 330 M98 150 L98 336' });
    add(parts, { id: 'beard', parent: 'head', pivot: J.neck, fill: '--c-paper-2', d: d([blob([[104, 86], [126, 90], [124, 108], [114, 136], [106, 112], [100, 96]])]), detail: 'M110 96 L112 124 M118 96 L116 118' });
    add(parts, { id: 'hat', parent: 'head', pivot: J.neck, fill: '--c-ink-2', d: d([ell(111, 66, 29, 6), ell(110, 56, 14, 13, Math.PI, Math.PI * 2, 20).concat([[124, 64], [96, 64]])]) });
    add(parts, { id: 'raven-back', parent: 'torso', behind: true, pivot: [90, 104], fill: '--c-ink', d: d(GLYPH.bird(86, 98, 34, -1)) });
    add(parts, { id: 'raven-front', parent: 'torso', pivot: [118, 108], fill: '--c-ink', d: d(GLYPH.bird(124, 104, 36, 1)) });
    add(parts, { id: 'prop-front', parent: 'hand-front', pivot: J.wrF, fill: '--c-gold', d: PROP.spear(J.wrF, 172) });
    return { viewBox: [200, 400], parts: parts,
      meta: figMeta({ id: 'odin', name: 'Odin', tradition: 'norse', emblems: ['one eye', 'spear Gungnir', 'ravens Huginn and Muninn', 'wide hat'], check: 'traditions/norse.md: one eye, spear, ravens, hat and cloak' }, opt) };
  };

  // ------------------------------------------------------------------ seated figures (frontal)
  var CX = 120;
  function pedestal(o) {
    var outer = [[52, 262], [188, 262], [196, 270], [188, 280], [196, 296], [44, 296], [52, 280], [44, 270]];
    var hole = [[92, 268], [148, 268], [148, 292], [92, 292]].reverse();
    var parts = [{ id: 'pedestal', pivot: [CX, 280], fill: o.base || '--c-leather-ochre', rule: 'evenodd', d: d(o.emblem ? [outer, hole] : [outer]), detail: 'M52 280 H188' }];
    if (o.emblem) {
      var gly = GLYPH[o.emblem] ? GLYPH[o.emblem](CX + (o.emblem === 'mouse' ? 4 : 0), 284, 30) : [];
      parts.push({ id: 'emblem', parent: 'pedestal', pivot: [CX, 280], fill: o.emblemFill || '--c-ink', d: d(gly) });
    }
    if (o.lotus) {
      var petals = [];
      for (var i = 0; i < 10; i++) petals.push(blob([[60 + i * 13, 264], [66 + i * 13, 244], [72 + i * 13, 264]]));
      parts.push({ id: 'lotus', parent: 'pedestal', pivot: [CX, 256], fill: '--c-lotus', d: d(petals) });
    }
    return parts;
  }

  function seatedBody(o) {
    var skin = o.skin || '--c-gold-light';
    var legs = [[58, 250], [80, 232], [104, 226], [120, 234], [136, 226], [160, 232], [182, 250], [166, 262], [120, 258], [74, 262]];
    // Heroic: the 'lion-like' upper body of the classical image, broad shoulders and a narrow waist, kept smooth.
    var torso = o.heroic
      ? [[72, 136], [96, 122], [120, 119], [144, 122], [168, 136], [160, 168], [146, 204], [152, 238], [88, 238], [94, 204], [80, 168]]
      : [[82, 134], [100, 124], [120, 122], [140, 124], [158, 134], [154, 172], [144, 208], [150, 238], [90, 238], [96, 208], [86, 172]];
    var parts = [
      { id: 'legs', parent: 'pedestal', pivot: [CX, 246], fill: o.cloth || skin, d: d([blob(legs)]), detail: 'M92 238 q8 -6 16 0 M132 238 q8 -6 16 0' },
      { id: 'body', parent: 'pedestal', pivot: [CX, 238], fill: o.torsoFill || skin, d: d([blob(torso), tube([[CX, 128], [CX, 108]], o.heroic ? 10 : 8)]), detail: (o.chest || '') + (o.heroic && o.contour ? ' M96 150 q12 8 22 3 M122 153 q12 5 22 -3' : '') }
    ];
    return parts;
  }

  function seatedHead(o) {
    var ears = [tube([[101, 84], [99, 98], [100, 112]], [4, 3.4, 3], { cap: 4 }), tube([[139, 84], [141, 98], [140, 112]], [4, 3.4, 3], { cap: 4 })];
    return [
      { id: 'head', parent: 'body', pivot: [CX, 112], fill: o.skin || '--c-gold-light', d: d([ell(CX, 90, 18, 22)].concat(ears)), detail: 'M108 88 q5 3 9 0 M123 88 q5 3 9 0 M114 104 q6 3 12 0' },
      { id: 'hair', parent: 'head', pivot: [CX, 80], fill: o.hair || '--c-ink-2', d: d([ell(CX, 84, 19.5, 18, Math.PI, Math.PI * 2, 24).concat([[CX + 19.5, 86], [CX - 19.5, 86]]), ell(CX, 62, o.ushnisha || 8, (o.ushnisha || 8) * 0.9)]) }
    ];
  }

  // Seated arms: shoulder at x, then the forearm path; heroic arms start wider and carry more volume.
  function seatedArm(side, heroic, path, extra) {
    var sx = side < 0 ? (heroic ? 78 : 86) : (heroic ? 162 : 154), sy = heroic ? 138 : 136;
    var radii = heroic ? [11.5, 9.2, 7, 5.8, 5.2] : [9, 7, 6, 5.5, 5];
    return [tube([[sx, sy]].concat(path), radii)].concat(extra || []);
  }

  /**
   * Seated Tirthankara in meditation (dhyana), frontal, on a pedestal whose window carries the
   * lanchhana. o {emblem: 'lion' (Mahavira, default) | 'bull' (Rishabhanatha) | 'deer'
   * (Shantinatha) | 'conch' (Neminatha) | 'snake' (Parshvanatha: serpent hoods, no glyph),
   * chhatra (true)}. Never posed fighting or granting boons (traditions/jain-buddhist.md).
   */
  FIG.tirthankara = function (opt) {
    var o = opt || {}, emblem = o.emblem || 'lion', H = buildOf(o) === 'heroic';
    var names = { lion: 'Mahavira', bull: 'Rishabhanatha', deer: 'Shantinatha', conch: 'Neminatha', snake: 'Parshvanatha' };
    var parts = pedestal({ emblem: emblem === 'snake' ? null : emblem, base: '--c-leather-ochre', emblemFill: '--c-ink' });
    parts = parts.concat(seatedBody({ heroic: H, contour: true, skin: '--c-gold-light', chest: 'M120 146 l6 6 l-6 6 l-6 -6 z' }));
    if (emblem === 'snake') {
      var hoods = [];
      for (var i = 0; i < 7; i++) {
        var a = Math.PI * (1.12 + 0.76 * i / 6);
        hoods.push(ell(CX + Math.cos(a) * 34, 84 + Math.sin(a) * 40, 9, 12));
      }
      parts.push({ id: 'hoods', parent: 'body', behind: true, pivot: [CX, 110], fill: '--c-malachite', d: d(hoods.concat([tube([[CX, 120], [CX - 6, 80], [CX, 50]], [10, 12, 8])])) });
    }
    parts = parts.concat([
      { id: 'arm-left', parent: 'body', pivot: [H ? 78 : 86, 136], fill: '--c-gold-light', d: d(seatedArm(-1, H, [[H ? 70 : 78, 178], [H ? 80 : 86, 214], [104, 228], [116, 230]])) },
      { id: 'arm-right', parent: 'body', pivot: [H ? 162 : 154, 136], fill: '--c-gold-light', d: d(seatedArm(1, H, [[H ? 170 : 162, 178], [H ? 160 : 154, 214], [136, 228], [124, 230]])) },
      { id: 'hands', parent: 'body', pivot: [CX, 230], fill: '--c-gold-light', d: d([ell(CX, 230, 17, 7)]) }
    ]);
    parts = parts.concat(seatedHead({ skin: '--c-gold-light', ushnisha: 7 }));
    if (o.chhatra !== false) {
      parts.push({ id: 'chhatra', parent: 'pedestal', pivot: [CX, 40], fill: '--c-gold', d: d([ell(CX, 46, 34, 6.5), ell(CX, 36, 27, 5.5), ell(CX, 27, 20, 4.5), ell(CX, 18, 3.5, 3.5), tube([[CX, 22], [CX, 52]], 1.6, { cap: 3 })]), detail: 'M88 48 v4 M100 50 v4 M112 51 v4 M128 51 v4 M140 50 v4 M152 48 v4' });
    }
    return { viewBox: [240, 300], parts: parts,
      meta: figMeta({ id: 'tirthankara', name: names[emblem] || 'Tirthankara', tradition: 'jain', emblems: [emblem === 'snake' ? 'serpent hoods' : emblem + ' (lanchhana)', 'meditation (dhyana)', 'shrivatsa', 'triple umbrella'],
        check: 'traditions/jain-buddhist.md: lanchhana against one named source; say which sect the image follows' }, o) };
  };

  /** Seated Buddha touching the earth (bhumisparsha, the enlightenment), frontal, robe over the left shoulder. */
  FIG.buddha = function (opt) {
    var H = buildOf(opt) === 'heroic';
    var parts = pedestal({ lotus: true, base: '--c-leather-ochre' });
    parts = parts.concat(seatedBody({ heroic: H, skin: '--c-gold-light', cloth: '--c-saffron', torsoFill: '--c-saffron', chest: 'M154 132 Q120 170 92 214' }));
    parts = parts.concat([
      { id: 'arm-left', parent: 'body', pivot: [H ? 78 : 86, 136], fill: '--c-gold-light', d: d(seatedArm(-1, H, [[H ? 68 : 76, 180], [H ? 68 : 72, 214], [66, 240], [64, 256]], [ell(64, 262, H ? 6 : 5, H ? 8 : 7)])) },
      { id: 'arm-right', parent: 'body', pivot: [H ? 162 : 154, 136], fill: '--c-saffron', d: d(seatedArm(1, H, [[H ? 170 : 162, 178], [H ? 160 : 154, 214], [136, 228], [126, 230]], [ell(124, 231, 12, 6)])) }
    ]);
    parts = parts.concat(seatedHead({ skin: '--c-gold-light', ushnisha: 11 }));
    return { viewBox: [240, 300], parts: parts,
      meta: figMeta({ id: 'buddha', name: 'The Buddha', tradition: 'buddhist', emblems: ['earth-touching gesture (bhumisparsha)', 'ushnisha', 'robe', 'lotus seat'],
        check: 'traditions/jain-buddhist.md: not in an aniconic-period scene; keep high and whole' }, opt) };
  };

  /**
   * Seated Ganesha, frontal: elephant head, the right tusk broken (on the viewer's left), trunk
   * curling to the sweets (modak), four arms with axe, noose, broken tusk and the bowl, the mouse
   * on the pedestal.
   */
  FIG.ganesha = function (opt) {
    // Heroic keeps the belly (Lambodara, 'pot-bellied', is iconography) and adds chest, shoulders and arms.
    var H = buildOf(opt) === 'heroic', A = H ? [12, 9.6, 7.6] : [9, 7, 6], sw = H ? 8 : 0;
    var parts = pedestal({ emblem: 'mouse', lotus: true, base: '--c-leather-ochre', emblemFill: '--c-ink' });
    var skin = '--c-saffron';
    var legs = [[50, 252], [78, 226], [104, 222], [120, 232], [136, 222], [162, 226], [190, 252], [170, 264], [120, 260], [70, 264]];
    var torso = H
      ? [[66, 134], [94, 118], [120, 116], [146, 118], [174, 134], [170, 170], [160, 214], [168, 240], [72, 240], [80, 214], [70, 170]]
      : [[76, 132], [98, 120], [120, 118], [142, 120], [164, 132], [166, 170], [160, 214], [168, 240], [72, 240], [80, 214], [74, 170]];
    parts.push({ id: 'legs', parent: 'pedestal', pivot: [CX, 246], fill: '--c-leather-red', d: d([blob(legs)]), detail: 'M86 240 q10 -8 20 0 M134 240 q10 -8 20 0' });
    parts.push({ id: 'arm-ul', parent: 'pedestal', pivot: [82 - sw, 134], fill: skin, d: d([tube([[82 - sw, 134], [58, 128], [54, 102]], A), ell(54, 96, H ? 7.5 : 6.5, H ? 7.5 : 6.5)]) });
    parts.push({ id: 'axe', parent: 'arm-ul', pivot: [54, 96], fill: '--c-gold', d: d([tube([[54, 122], [54, 58]], 2.2), blob([[52, 58], [38, 50], [30, 64], [36, 78], [52, 72]])]) });
    parts.push({ id: 'arm-ur', parent: 'pedestal', pivot: [158 + sw, 134], fill: skin, d: d([tube([[158 + sw, 134], [182, 128], [186, 102]], A), ell(186, 96, H ? 7.5 : 6.5, H ? 7.5 : 6.5)]) });
    parts.push({ id: 'noose', parent: 'arm-ur', pivot: [186, 96], rule: 'evenodd', fill: '--c-gold', d: d([ell(192, 78, 12, 12), ell(192, 78, 9, 9).reverse(), tube([[188, 90], [186, 112]], 1.6, { cap: 3 })]) });
    parts.push({ id: 'body', parent: 'pedestal', pivot: [CX, 240], fill: skin, d: d([blob(torso), ell(CX, 196, 42, 36), tube([[CX, 124], [CX, 108]], 10)]), detail: H ? 'M90 146 q14 10 28 2 M122 148 q14 8 28 -2 M114 196 a5 5 0 1 0 0.1 0' : 'M100 148 q20 10 40 0 M114 196 a5 5 0 1 0 0.1 0' });
    parts.push({ id: 'arm-ll', parent: 'body', pivot: [84, 150], fill: skin, d: d([tube([[84 - sw, 150], [70 - sw * 0.5, 188], [86, 214]], A), ell(88, 216, H ? 8 : 7, H ? 7 : 6)]) });
    parts.push({ id: 'tusk', parent: 'arm-ll', pivot: [88, 216], fill: '--c-paper', d: d([tube([[90, 210], [100, 198]], [3, 1.4], { cap: 4 })]) });
    parts.push({ id: 'arm-lr', parent: 'body', pivot: [156, 150], fill: skin, d: d([tube([[156 + sw, 150], [170 + sw * 0.5, 188], [156, 214]], A), ell(152, 216, H ? 8 : 7, H ? 7 : 6)]) });
    parts.push({ id: 'modak', parent: 'arm-lr', pivot: [150, 214], fill: '--c-gold', d: d([ell(150, 210, 15, 7, 0, Math.PI, 14).concat([[135, 210]]), ell(142, 204, 5, 5), ell(150, 201, 5.5, 5.5), ell(158, 204, 5, 5)]) });
    parts.push({ id: 'ear-left', parent: 'body', pivot: [100, 80], fill: skin, d: d([blob([[100, 70], [78, 56], [58, 70], [56, 100], [70, 118], [94, 110], [102, 94]])]), detail: 'M72 76 q-6 14 4 30' });
    parts.push({ id: 'ear-right', parent: 'body', pivot: [140, 80], fill: skin, d: d([blob(mirror([[100, 70], [78, 56], [58, 70], [56, 100], [70, 118], [94, 110], [102, 94]], CX))]), detail: 'M168 76 q6 14 -4 30' });
    parts.push({ id: 'head', parent: 'body', pivot: [CX, 112], fill: skin, d: d([ell(CX, 84, 24, 26)]), detail: 'M106 82 q5 3 9 0 M125 82 q5 3 9 0 M120 64 v8' });
    parts.push({ id: 'trunk', parent: 'head', pivot: [CX, 100], fill: skin, d: d([tube([[CX, 98], [118, 126], [122, 150], [136, 166], [150, 160], [152, 150]], [11, 9, 7, 5, 4, 3])]), detail: 'M114 112 h10 M114 124 h9 M117 136 h8' });
    parts.push({ id: 'tusks', parent: 'head', pivot: [CX, 108], fill: '--c-paper', d: d([tube([[110, 106], [104, 113]], [3.6, 3], { cap: 4 }), tube([[130, 106], [140, 120], [148, 121]], [3.6, 2.4, 1])]) });
    parts.push({ id: 'crown', parent: 'head', pivot: [CX, 60], fill: '--c-gold', d: d([[[100, 66], [110, 42], [CX, 24], [130, 42], [140, 66]], ell(CX, 66, 21, 4)]), detail: 'M106 54 H134 M112 40 H128' });
    return { viewBox: [240, 300], parts: parts,
      meta: figMeta({ id: 'ganesha', name: 'Ganesha', tradition: 'indian', emblems: ['elephant head', 'broken tusk', 'modak', 'mouse', 'axe and noose'],
        check: 'traditions/indian.md: elephant head, broken tusk, modak, mouse (check); which tusk is broken varies by image' }, opt) };
  };

  M.figureIds = ['rama', 'hanuman', 'shiva', 'ganesha', 'athena', 'odin', 'tirthankara', 'buddha'];

  // Builds: 'classic' (default) and 'heroic' (muscular classical ideal). Every figure also answers
  // to '<id>-heroic' (e.g. puppet({figure: 'hanuman-heroic'})), the same as figureOptions {build: 'heroic'}.
  M.builds = ['classic', 'heroic'];
  M.heroicIds = M.figureIds.map(function (id) {
    FIG[id + '-heroic'] = function (opt) {
      var o = {}, k;
      for (k in opt) if (Object.prototype.hasOwnProperty.call(opt, k)) o[k] = opt[k];
      o.build = 'heroic';
      return FIG[id](o);
    };
    return id + '-heroic';
  });
})(typeof window !== 'undefined' ? window : this);
