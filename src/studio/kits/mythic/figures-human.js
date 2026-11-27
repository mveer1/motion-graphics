/*
 * Motion Lab mythic kit - human figure build (src/studio/kits/mythic/figures-human.js)
 *
 * Front-view figures drawn on one proportion grid, with anatomy, faces, hair, dress and ornament
 * set from the tradition packs and the texts (.claude/skills/mythic-tales/references/figure-design.md
 * holds the research and the per-figure identity blocks). Load after mythic.js and figures.js.
 *
 *   Studio.kit.mythic.puppet(parent, {figure: 'rama-human', look: 'illustrated', h, x, y})
 *
 * Grid (viewBox 400 x 820, centre line x 200, ground y 790): 8 heads of 88-96 units, the classical
 * heroic canon and the dasa-tala ideal of Indian sculpture read in heads. Landmarks shared by every
 * standing figure, so later views (three-quarter, profile, back) line up with these:
 *   skull 84 · brows 121 · eyes 131 · nose 151 · chin 180 · shoulders 212 · nipples 262 ·
 *   navel 350 · crotch 440 · knees 596 · ankles 752 · soles 790.
 * Part ids (r = the figure's own right, the viewer's left): pelvis, leg-r, leg-l, torso, arm-r,
 * fore-r, hand-r, arm-l, fore-l, hand-l, head, then hair, dress, ornament and props.
 * Seated figures use a 400 x 560 box (pedestal top 470) with the same head size.
 *
 * Every part is a base shape plus painted layers (shadow, light, features), so the 'illustrated'
 * look shows the full drawing, 'paper' and 'painted' keep the layers, and 'silhouette' shows the
 * outline alone. Light comes from the viewer's upper left (the storyteller's lamp).
 * These are drawings for storytelling, not icons for worship; a reviewer checks each against the
 * telling a film follows (quality-rubric.md, gate 2).
 */
(function (global) {
  'use strict';

  var Studio = global.Studio || (global.Studio = {});
  var KIT = Studio.kit = Studio.kit || {};
  var M = KIT.mythic = KIT.mythic || {};
  var FIG = M.figures = M.figures || {};
  var CX = 200;
  var INK = '#2B1D14';

  // ------------------------------------------------------------------ geometry
  function f1(n) { return Math.round(n * 10) / 10; }

  /** Catmull-Rom spline through the points as cubic Beziers. A point [x, y, 1] is a sharp corner. */
  function bez(pts, closed, k) {
    var n = pts.length;
    if (n < 2) return '';
    var t = (k === undefined ? 1 : k) / 6;
    var get = function (i) { return closed ? pts[((i % n) + n) % n] : pts[Math.max(0, Math.min(n - 1, i))]; };
    var tan = function (i) {
      var p = get(i);
      if (p[2] || (!closed && (i <= 0 || i >= n - 1))) {
        if (p[2]) return [0, 0];
        var q = i <= 0 ? get(1) : get(n - 2);
        return i <= 0 ? [(q[0] - p[0]) * t, (q[1] - p[1]) * t] : [(p[0] - q[0]) * t, (p[1] - q[1]) * t];
      }
      var a = get(i - 1), b = get(i + 1);
      return [(b[0] - a[0]) * t, (b[1] - a[1]) * t];
    };
    var s = 'M' + f1(pts[0][0]) + ' ' + f1(pts[0][1]);
    var segs = closed ? n : n - 1;
    for (var i = 0; i < segs; i++) {
      var p1 = get(i), p2 = get(i + 1), m1 = tan(i), m2 = tan(i + 1);
      s += 'C' + f1(p1[0] + m1[0]) + ' ' + f1(p1[1] + m1[1]) + ' ' + f1(p2[0] - m2[0]) + ' ' + f1(p2[1] - m2[1]) + ' ' + f1(p2[0]) + ' ' + f1(p2[1]);
    }
    return closed ? s + 'Z' : s;
  }
  /** Offset points (x from the centre line) to the viewer's right (R) or mirrored to the left (L). */
  function R(pts, dx, dy) { return pts.map(function (p) { return [CX + p[0] + (dx || 0), p[1] + (dy || 0), p[2]]; }); }
  function L(pts, dx, dy) { return pts.map(function (p) { return [CX - p[0] - (dx || 0), p[1] + (dy || 0), p[2]]; }); }
  /** A closed shape symmetric about the centre line from its right half (axis top to axis bottom). */
  function sym(half) {
    var r = R(half), l = L(half.slice(1, -1)).reverse();
    return bez(r.concat(l), true);
  }
  /** The same closed shape on both sides. */
  function pair(half, k) { return bez(R(half), true, k) + ' ' + bez(L(half), true, k); }
  function pairOpen(half, k) { return bez(R(half), false, k) + ' ' + bez(L(half), false, k); }
  function closed(pts, k) { return bez(pts, true, k); }
  function open(pts, k) { return bez(pts, false, k); }
  function ellipse(cx, cy, rx, ry, rot) {
    var a = (rot || 0) * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
    var p1 = [cx - rx * c, cy - rx * s], p2 = [cx + rx * c, cy + rx * s];
    return 'M' + f1(p1[0]) + ' ' + f1(p1[1]) + 'A' + f1(rx) + ' ' + f1(ry) + ' ' + f1(rot || 0) + ' 1 0 ' + f1(p2[0]) + ' ' + f1(p2[1]) +
      'A' + f1(rx) + ' ' + f1(ry) + ' ' + f1(rot || 0) + ' 1 0 ' + f1(p1[0]) + ' ' + f1(p1[1]) + 'Z';
  }
  function circle(cx, cy, r) { return ellipse(cx, cy, r, r); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function mid(a, b, t) { return [lerp(a[0], b[0], t), lerp(a[1], b[1], t)]; }

  /** Position and unit direction at fraction t along a joint chain (directions blend near joints). */
  function along(J, t) {
    var lens = [], tot = 0, i;
    for (i = 0; i < J.length - 1; i++) { var l = Math.hypot(J[i + 1][0] - J[i][0], J[i + 1][1] - J[i][1]); lens.push(l); tot += l; }
    var target = Math.max(0, Math.min(1, t)) * tot, acc = 0;
    for (i = 0; i < lens.length; i++) {
      if (target <= acc + lens[i] || i === lens.length - 1) {
        var u = lens[i] ? (target - acc) / lens[i] : 0;
        var d = [(J[i + 1][0] - J[i][0]) / lens[i], (J[i + 1][1] - J[i][1]) / lens[i]];
        var blend = 0.18;
        if (u > 1 - blend && i < lens.length - 1) {
          var d2 = [(J[i + 2][0] - J[i + 1][0]) / lens[i + 1], (J[i + 2][1] - J[i + 1][1]) / lens[i + 1]], w = (u - (1 - blend)) / blend * 0.5;
          d = [lerp(d[0], d2[0], w), lerp(d[1], d2[1], w)];
        } else if (u < blend && i > 0) {
          var d0 = [(J[i][0] - J[i - 1][0]) / lens[i - 1], (J[i][1] - J[i - 1][1]) / lens[i - 1]], w0 = (blend - u) / blend * 0.5;
          d = [lerp(d[0], d0[0], w0), lerp(d[1], d0[1], w0)];
        }
        var dl = Math.hypot(d[0], d[1]) || 1;
        return { p: [lerp(J[i][0], J[i + 1][0], u), lerp(J[i][1], J[i + 1][1], u)], d: [d[0] / dl, d[1] / dl] };
      }
      acc += lens[i];
    }
    return { p: J[J.length - 1], d: [0, 1] };
  }

  /**
   * Muscled limb along a joint chain. st: [[t, outer, inner], ...] half-widths at fractions of the
   * chain; side +1 when the outer face is on the viewer's right of a downward limb, -1 otherwise.
   * o {startCap: true, endCap: true}. Returns the closed outline as points.
   */
  function limbPts(J, st, side, o) {
    o = o || {};
    var A = [], B = [];
    st.forEach(function (s) {
      var a = along(J, s[0]), n = [-a.d[1], a.d[0]];          // n points to the viewer's left of a downward limb
      var no = side > 0 ? [-n[0], -n[1]] : n;
      A.push([a.p[0] + no[0] * s[1], a.p[1] + no[1] * s[1]]);
      B.push([a.p[0] - no[0] * s[2], a.p[1] - no[1] * s[2]]);
    });
    var e = along(J, st[st.length - 1][0]), se = st[st.length - 1], st0 = along(J, st[0][0]), s0 = st[0];
    var pts = A.slice();
    if (o.endCap !== false) {
      var re = (se[1] + se[2]) / 2 * (o.endRound || 0.9);
      var ne = [-e.d[1], e.d[0]], noe = side > 0 ? [-ne[0], -ne[1]] : ne, off = (se[1] - se[2]) / 2;
      pts.push([e.p[0] + e.d[0] * re + noe[0] * off, e.p[1] + e.d[1] * re + noe[1] * off]);
    } else { pts[pts.length - 1] = pts[pts.length - 1].concat([1]); B[B.length - 1] = B[B.length - 1].concat([1]); }
    pts = pts.concat(B.slice().reverse());
    if (o.startCap !== false) {
      var rs = (s0[1] + s0[2]) / 2 * (o.startRound || 0.9);
      var ns = [-st0.d[1], st0.d[0]], nos = side > 0 ? [-ns[0], -ns[1]] : ns, offs = (s0[1] - s0[2]) / 2;
      pts.push([st0.p[0] - st0.d[0] * rs + nos[0] * offs, st0.p[1] - st0.d[1] * rs + nos[1] * offs]);
    } else { pts[pts.length - 1] = pts[pts.length - 1].concat([1]); pts[0] = pts[0].concat([1]); }
    return pts;
  }
  function limb(J, st, side, o) { return closed(limbPts(J, st, side, o)); }
  /** A strip hugging one face of a limb: shadow or light band. face 'outer'|'inner', w width. */
  function limbBand(J, st, side, face, w, t0, t1) {
    var P = [], Q = [];
    st.forEach(function (s) {
      if (s[0] < (t0 || 0) || s[0] > (t1 === undefined ? 1 : t1)) return;
      var a = along(J, s[0]), n = [-a.d[1], a.d[0]], no = side > 0 ? [-n[0], -n[1]] : n;
      var sg = face === 'outer' ? 1 : -1, r = face === 'outer' ? s[1] : s[2];
      P.push([a.p[0] + no[0] * sg * (r + 2), a.p[1] + no[1] * sg * (r + 2)]);
      Q.push([a.p[0] + no[0] * sg * (r - w * Math.min(1, r / 10)), a.p[1] + no[1] * sg * (r - w * Math.min(1, r / 10))]);
    });
    return closed(P.concat(Q.reverse()));
  }

  /** Two-bone IK in 2D: the elbow that joins shoulder s to wrist w with segment lengths a and b; bend 1 or -1. */
  function ik2(s, w, a, b, bend) {
    var dx = w[0] - s[0], dy = w[1] - s[1], d = Math.min(a + b - 0.01, Math.max(Math.abs(a - b) + 0.01, Math.hypot(dx, dy)));
    var ang = Math.atan2(dy, dx), cosA = (a * a + d * d - b * b) / (2 * a * d), off = Math.acos(Math.max(-1, Math.min(1, cosA))) * (bend || 1);
    return [s[0] + Math.cos(ang + off) * a, s[1] + Math.sin(ang + off) * a];
  }

  M.human = M.human || {};
  M.human.geom = { bez: bez, sym: sym, pair: pair, ellipse: ellipse, limb: limb, along: along, R: R, L: L, ik2: ik2 };

  // ------------------------------------------------------------------ palettes
  // sk base, sh shadow, dp deep shadow and creases, hl light, rim back light, lip, eye (iris).
  var SKIN = {
    // Valmiki's shyama: "dark", read in painting as cloud-dark blue; a deep slate, never a toy blue.
    'shyama-blue': { sk: '#4E6286', sh: '#3D4E6E', dp: '#2A3550', hl: '#6C82A8', rim: '#A9BCD8', lip: '#5A4560', eye: '#1B1414' },
    // The same complexion read literally as "dark brown" (Gita Press: "dark-brown complexion", 5.35.16).
    'shyama-brown': { sk: '#6E4B36', sh: '#5A3B29', dp: '#3E271A', hl: '#8C6449', rim: '#C49A78', lip: '#5A2E28', eye: '#1B1210' },
    // Hanuman: tawny-gold fur, a warm red face (Britannica: red-faced); see figure-design.md.
    'vanara-gold': { sk: '#C98B3E', sh: '#A86E2C', dp: '#7A4C1C', hl: '#E2AC5E', rim: '#F4D59A', lip: '#7E3A24', eye: '#2A1608' },
    'vanara-face': { sk: '#D7765A', sh: '#B85C44', dp: '#86402E', hl: '#EC9A7C', rim: '#F6C3A8', lip: '#7E3A24', eye: '#2A1608' },
    // Shiva: ash-smeared pale grey-blue body (vibhuti), the throat blue (Nilakantha).
    'ash': { sk: '#AFC0CC', sh: '#90A3B2', dp: '#64788A', hl: '#D3DEE6', rim: '#EEF4F8', lip: '#7C5A66', eye: '#1B1414' },
    'warm-gold': { sk: '#D9A35B', sh: '#BD8644', dp: '#8E5E2C', hl: '#EDC07E', rim: '#F8E0B0', lip: '#9A4F3A', eye: '#1E1410' },
    'olive': { sk: '#C99A72', sh: '#AE7F5A', dp: '#80583C', hl: '#E0B892', rim: '#F2D8BC', lip: '#9A5446', eye: '#3B4A52' },
    'weathered': { sk: '#D2A080', sh: '#B5835F', dp: '#855A3E', hl: '#E8BEA0', rim: '#F4DAC4', lip: '#94564A', eye: '#3E5260' },
    // Athena Parthenos had ivory flesh (Pausanias 1.24.5-7): a warm ivory, not a cold white.
    'ivory': { sk: '#E6C7A2', sh: '#CBA67F', dp: '#9A7552', hl: '#F4DEC2', rim: '#FBEEDC', lip: '#B0605A', eye: '#4E6E80' }
  };
  M.human.skins = SKIN;
  var HAIR = { black: { b: '#1F1817', s: '#120D0C', h: '#3E302C' }, grey: { b: '#A9A39A', s: '#7E776E', h: '#D6D0C6' } };

  // ------------------------------------------------------------------ body (front, standing)
  // Heroic male canon. b {k: bulk, waist, ajanu: arms reach the knees}.
  var BODY = {
    hero: { k: 1, sh: 88, waist: 54, lat: 78 },
    mighty: { k: 1.16, sh: 94, waist: 60, lat: 88 },
    yogi: { k: 0.95, sh: 86, waist: 50, lat: 74 },
    elder: { k: 0.98, sh: 84, waist: 60, lat: 74 },
    female: { k: 0.82, sh: 70, waist: 44, lat: 58 }
  };

  function torsoHalf(b, hips) {
    var k = b.k, s = b.sh;
    var top = [[0, 160], [19 * k, 162], [20 * k, 180], [30 * k + 2, 194], [52 * k, 201], [s - 12, 205], [s, 213], [s - 1, 236],
      [b.lat + 2, 252], [b.lat, 272], [b.lat - 5, 298], [b.waist + 8, 322], [b.waist, 340], [b.waist + 3, 358]];
    return hips
      ? top.concat([[b.waist + 9, 378], [b.waist + 14, 404], [b.waist + 18, 430], [40, 444], [0, 448]])
      : top.concat([[b.waist + 6, 376, 1], [0, 378]]);
  }

  /** Torso part: neck, chest, abdomen, with cel shading from a lamp on the viewer's upper left. */
  function torsoPart(P, b, o) {
    o = o || {};
    var k = b.k, s = b.sh, wst = b.waist;
    var base = sym(torsoHalf(b, o.hips));
    var lay = [];
    var bare = !o.covered;
    // Shadow side (viewer's right) and core shadow along the flank.
    lay.push({ clip: true, fill: P.sh, d: closed([[s + 6, 200], [s + 6, 460], [wst - 10, 460], [wst - 4, 400], [wst - 12, 340], [b.lat - 18, 290], [s - 18, 236], [s - 26, 214]]) });
    // Neck shadow under the chin and the jaw's cast shadow.
    lay.push({ clip: true, fill: P.sh, d: sym([[0, 158], [22 * k, 160], [21 * k, 176], [12 * k, 184], [0, 186]]) });
    lay.push({ clip: true, fill: P.dp, op: 0.55, d: sym([[0, 158], [20 * k, 160], [16 * k, 170], [0, 174]]) });
    if (bare) {
      // Pectorals: flat, squared lower edges rising to the armpit (a man's chest, not a rounded bust).
      lay.push({ clip: true, fill: P.sh, d: closed(R([[3, 256, 1], [20, 262], [42 * k, 266], [60 * k, 258], [s - 12, 236, 1], [s - 10, 248], [62 * k, 268], [42 * k, 275], [20, 271], [3, 266, 1]])) });
      lay.push({ clip: true, fill: P.sh, op: 0.7, d: closed(L([[3, 258, 1], [20, 263], [42 * k, 266], [60 * k, 258], [s - 14, 238, 1], [s - 12, 246], [60 * k, 264], [42 * k, 271], [20, 268], [3, 264, 1]])) });
      lay.push({ clip: true, stroke: P.dp, sw: 1, op: 0.35, d: pairOpen([[2, 214], [24, 210], [46 * k, 214], [s - 16, 228]]) });
      // Sternum groove, clavicles, collarbone pit.
      lay.push({ clip: true, stroke: P.dp, sw: 1.1, op: 0.5, d: open([[CX, 206], [CX, 252]]) });
      lay.push({ clip: true, stroke: P.dp, sw: 1.2, op: 0.45, d: pairOpen([[6, 203], [22, 200], [42 * k, 203], [58 * k, 205]]) });
      if (o.smooth) lay.push({ clip: true, fill: P.hl, op: 0.35, d: ellipse(CX - 24, 300, 18, 40) });
      lay.push({ clip: true, fill: P.hl, op: 0.55, d: closed(L([[8, 196], [30, 193], [54 * k, 198], [66 * k, 202], [50 * k, 200], [26, 199]])) });
      // Abdomen: rectus columns, tendinous lines, navel, obliques; deliberately soft (no bodybuilder grid).
      if (!o.smooth) {
        lay.push({ clip: true, stroke: P.dp, sw: 1, op: 0.38, d: open([[CX, 282], [CX, 344]]) });
        lay.push({ clip: true, stroke: P.dp, sw: 1, op: 0.3, d: pairOpen([[3, 301], [14, 298], [24, 302]]) + ' ' + pairOpen([[3, 322], [14, 320], [23, 324]]) });
        lay.push({ clip: true, stroke: P.dp, sw: 1, op: 0.3, d: pairOpen([[26, 286], [27, 312], [22, 340], [14, 362]]) });
        lay.push({ clip: true, stroke: P.dp, sw: 1, op: 0.35, d: pairOpen([[wst + 2, 330], [wst - 4, 356], [wst - 14, 384]]) });
        lay.push({ clip: true, fill: P.sh, d: closed(R([[4, 300], [24, 300], [26, 330], [18, 356], [4, 350]])), op: 0.35 });
      }
      lay.push({ clip: true, fill: P.dp, op: 0.7, d: ellipse(CX, 352, 3.2, 4.2) });
      // Lit flank and shoulder plane on the lamp side.
      lay.push({ clip: true, fill: P.hl, op: 0.5, d: closed(L([[s - 8, 212], [s - 2, 236], [b.lat - 2, 262], [b.lat - 8, 292], [wst + 4, 322], [wst - 2, 340], [wst - 9, 320], [b.lat - 16, 286], [b.lat - 14, 258], [s - 14, 230]])) });
      // Kambu-griva: the three conch lines of the neck in Indian sculpture.
      if (o.trivali !== false) lay.push({ clip: true, stroke: P.dp, sw: 0.9, op: 0.35, d: open([[CX - 14, 176], [CX, 179], [CX + 14, 176]]) + ' ' + open([[CX - 15, 183], [CX, 186], [CX + 15, 183]]) });
    }
    lay.push({ clip: true, stroke: P.rim, sw: 1.6, op: 0.55, d: open(R([[s + 1, 214], [s, 236], [b.lat + 1, 252], [b.lat - 1, 274], [b.lat - 6, 298], [wst + 7, 322]])) });
    return { id: 'torso', parent: 'pelvis', pivot: [CX, 340], fill: P.sk, d: base, layers: lay.concat(o.layers || []) };
  }

  var ARM = { upper: [[0, 18, 10], [0.14, 23, 13], [0.36, 19, 15], [0.58, 16, 15.5], [0.82, 12.5, 12], [1, 10.5, 10]],
    fore: [[0, 10.5, 10], [0.2, 13.5, 11], [0.46, 11.5, 9], [0.8, 7.6, 7], [1, 6.6, 6.2]] };
  function scaleSt(st, k) { return st.map(function (s) { return [s[0], s[1] * k, s[2] * k]; }); }

  /** Upper arm + forearm parts. side 'r' (viewer's left) or 'l'. J {s, e, w}. o {k, foreFront}. */
  function armParts(P, side, J, o) {
    o = o || {};
    var sg = side === 'l' ? 1 : -1, k = o.k || 1;
    var up = scaleSt(ARM.upper, k), fo = scaleSt(ARM.fore, k);
    var ja = [J.s, J.e], jf = [J.e, J.w];
    var lit = sg < 0 ? 'outer' : 'inner', dark = sg < 0 ? 'inner' : 'outer';
    var upLay = [
      { clip: true, fill: P.sh, d: limbBand(ja, up, sg, dark, 11) },
      { clip: true, fill: P.hl, op: 0.55, d: limbBand(ja, up, sg, lit, 6, 0.05, 0.7) },
      // Deltoid separation and the biceps edge.
      { clip: true, stroke: P.dp, sw: 1, op: 0.4, d: open([mid(J.s, J.e, 0.08).map(function (v, i) { return v + (i ? 0 : sg * 6); }), [lerp(J.s[0], J.e[0], 0.34) + sg * 12 * k, lerp(J.s[1], J.e[1], 0.34)], [lerp(J.s[0], J.e[0], 0.46) + sg * 17 * k, lerp(J.s[1], J.e[1], 0.46)]]) },
      { clip: true, stroke: P.rim, sw: 1.4, op: sg > 0 ? 0.5 : 0, d: limbEdge(ja, up, sg, 'outer') }
    ];
    var foLay = [
      { clip: true, fill: P.sh, d: limbBand(jf, fo, sg, dark, 8) },
      { clip: true, fill: P.hl, op: 0.5, d: limbBand(jf, fo, sg, lit, 4.5, 0.08, 0.6) },
      { clip: true, stroke: P.rim, sw: 1.3, op: sg > 0 ? 0.5 : 0, d: limbEdge(jf, fo, sg, 'outer') }
    ];
    var upId = (o.prefix || 'arm') + '-' + side, foId = (o.forePrefix || 'fore') + '-' + side;
    return [
      { id: upId, parent: o.parent || 'torso', behind: !!o.behind, pivot: J.s, fill: P.sk, d: limb(ja, up, sg), layers: upLay },
      { id: foId, parent: upId, behind: !o.foreFront, pivot: J.e, fill: P.sk, d: limb(jf, fo, sg, { startRound: 0.6 }), layers: foLay }
    ];
  }
  function limbEdge(J, st, side, face) {
    return open(st.map(function (s) {
      var a = along(J, s[0]), n = [-a.d[1], a.d[0]], no = side > 0 ? [-n[0], -n[1]] : n, sg = face === 'outer' ? 1 : -1, r = (face === 'outer' ? s[1] : s[2]) - 1.2;
      return [a.p[0] + no[0] * sg * r, a.p[1] + no[1] * sg * r];
    }).slice(1, -1));
  }

  /**
   * A calm figure's arm in one contour (rule 4: no seam at the elbow, no ball at the shoulder). The upper
   * part draws the whole arm, shoulder to wrist, with its ink edge left open at the shoulder so the arm
   * melts into the torso; the forearm part keeps its id and pivot (hands parent to it) but draws only a
   * light. For figures that hold a gesture (the Jina, the Buddha); arms that bend on screen use armParts.
   */
  function calmArm(P, side, J, o) {
    o = o || {};
    var sg = side === 'l' ? 1 : -1, k = o.k || 1;
    var up = scaleSt(ARM.upper, k), fo = scaleSt(ARM.fore, k);
    var Lu = Math.hypot(J.e[0] - J.s[0], J.e[1] - J.s[1]), Lf = Math.hypot(J.w[0] - J.e[0], J.w[1] - J.e[1]), tu = Lu / (Lu + Lf);
    var st = up.map(function (s) { return [s[0] * tu, s[1], s[2]]; }).concat(fo.slice(1).map(function (s) { return [tu + s[0] * (1 - tu), s[1], s[2]]; }));
    var ch = [J.s, J.e, J.w];
    var pts = limbPts(ch, st, sg, {});
    var lit = sg < 0 ? 'outer' : 'inner', dark = sg < 0 ? 'inner' : 'outer';
    var upId = (o.prefix || 'arm') + '-' + side, foId = (o.forePrefix || 'fore') + '-' + side;
    var lay = [
      { clip: true, fill: P.sh, d: limbBand(ch, st, sg, dark, 10) },
      { clip: true, fill: P.hl, op: 0.5, d: limbBand(ch, st, sg, lit, 5.5, 0.04, 0.85) },
      // The soft dip of the elbow and the deltoid's edge, drawn as shadow rather than as an outline.
      { clip: true, fill: P.sh, op: 0.35, d: ellipse(J.e[0] + sg * 3, J.e[1], 7, 12) },
      { clip: true, stroke: P.dp, sw: 0.9, op: 0.3, d: open([mid(J.s, J.e, 0.1).map(function (v, i) { return v + (i ? 0 : sg * 7); }), [lerp(J.s[0], J.e[0], 0.4) + sg * 13 * k, lerp(J.s[1], J.e[1], 0.4)]]) },
      { clip: true, stroke: P.rim, sw: 1.4, op: sg > 0 ? 0.5 : 0, d: limbEdge(ch, st, sg, 'outer') },
      { stroke: INK, sw: 1.25, op: 0.82, d: open(pts.slice(0, -1)) }
    ];
    return [
      { id: upId, parent: o.parent || 'torso', pivot: J.s, fill: P.sk, outline: false, d: closed(pts), layers: lay },
      { id: foId, parent: upId, pivot: J.e, fill: 'none', outline: false, d: limb([J.e, J.w], fo, sg, { startRound: 0.6 }),
        layers: [{ clip: true, fill: P.hl, op: 0.3, d: limbBand([J.e, J.w], fo, sg, lit, 4, 0.1, 0.6) }] }
    ];
  }

  var LEG = [[0, 30, 24], [0.12, 31, 24], [0.26, 29, 22], [0.38, 25, 21.5], [0.44, 21, 20], [0.48, 18.5, 17], [0.53, 18.5, 16.5],
    [0.6, 21, 20], [0.68, 19.5, 18], [0.79, 13.5, 12], [0.88, 9.6, 9], [0.915, 11, 10.5], [0.965, 15, 13], [1, 15.5, 13.5]];

  /** Leg from hip to toe in one contour (no seams at knee or ankle). */
  function legPart(P, side, x, o) {
    o = o || {};
    var sg = side === 'l' ? 1 : -1, k = o.k || 1;
    var J = [[CX + sg * 46, 430], [CX + sg * 41, 596], [CX + sg * 38, 752], [CX + sg * 42, 791]];
    var st = scaleSt(LEG, k);
    var lit = sg < 0 ? 'outer' : 'inner', dark = sg < 0 ? 'inner' : 'outer';
    var kn = J[1];
    var lay = [
      { clip: true, fill: P.sh, d: limbBand(J, st, sg, dark, 12) },
      { clip: true, fill: P.hl, op: 0.5, d: limbBand(J, st, sg, lit, 6, 0.1, 0.84) },
      // Kneecap and the shin line.
      { clip: true, stroke: P.dp, sw: 1, op: 0.45, d: open([[kn[0] - 9, kn[1] - 6], [kn[0], kn[1] - 13], [kn[0] + 9, kn[1] - 6]]) + ' ' + open([[kn[0] - 7, kn[1] + 10], [kn[0], kn[1] + 14], [kn[0] + 7, kn[1] + 10]]) },
      { clip: true, stroke: P.dp, sw: 0.9, op: 0.3, d: open([[kn[0] + sg * 2, kn[1] + 30], [J[2][0] + sg * 3, 700]]) },
      // Toes.
      { clip: true, stroke: P.dp, sw: 0.8, op: 0.55, d: [0, 1, 2, 3].map(function (i) { var tx = J[3][0] - sg * 9 + sg * i * 5.4; return open([[tx, 784], [tx + sg * 0.6, 791]]); }).join(' ') },
      { clip: true, fill: P.dp, op: 0.35, d: closed([[J[2][0] - 13, 789], [J[2][0] + sg * 4 + 18, 789], [J[2][0] + sg * 4 + 16, 794], [J[2][0] - 12, 794]]) }
    ];
    return { id: 'leg-' + side, parent: 'pelvis', behind: true, pivot: J[0], fill: P.sk, d: limb(J, st, sg, { startCap: false, endRound: 0.55 }), layers: lay };
  }

  // ------------------------------------------------------------------ hands
  /** Fist gripping a vertical shaft, seen from the thumb side. c centre, k size; o {id, parent}. */
  function fistPart(P, side, c, o) {
    o = o || {};
    var k = o.k || 1, sg = side === 'l' ? 1 : -1, x = c[0], y = c[1];
    var at = function (dx, dy) { return [x + dx * k, y + dy * k]; };
    var base = closed([at(-9, -13), at(2, -15), at(10, -12), at(12.5, -4), at(12.5, 6), at(10, 13.5), at(3, 16.5), at(-6, 15.5), at(-11.5, 10), at(-12.5, 0)]);
    var thumb = closed([at(-12, -6), at(-3, -10), at(5, -9.5), at(8.5, -5.5), at(4, -2), at(-5, -1), at(-11, -0.5)]);
    var lay = [
      { clip: true, fill: P.sh, d: closed([at(sg * 3, -18), at(sg * 16, -18), at(sg * 16, 20), at(sg * 2, 20), at(sg * 6, 4)]) },
      // Curled fingers stacked under the thumb, the knuckle line on the side.
      { clip: true, stroke: P.dp, sw: 0.9, op: 0.6, d: [1.5, 6.5, 11.5].map(function (dy) { return open([at(-10, dy), at(-2, dy + 1.6), at(8, dy + 0.6), at(12, dy - 1.4)]); }).join(' ') },
      { clip: true, stroke: P.dp, sw: 1, op: 0.45, d: open([at(11, -6), at(12.5, 2), at(11.5, 12)]) },
      { fill: P.sk, d: thumb }, { clip: thumb, fill: P.hl, op: 0.65, d: closed([at(-12, -8), at(4, -12), at(4, -6), at(-10, -3)]) },
      { stroke: INK, sw: 1, op: 0.75, d: thumb },
      { fill: P.hl, op: 0.6, d: ellipse(x + 5.4 * k, y - 6.6 * k, 2.4 * k, 1.6 * k, -10) }
    ];
    return { id: o.id || 'hand-' + side, parent: o.parent || 'fore-' + side, pivot: [x, y - 12 * k], fill: P.sk, d: base, layers: lay };
  }

  /** Open hand, palm to the viewer: raised (abhaya, "fear not") or, with o.down, lowered (varada, the boon). w wrist point. */
  function palmPart(P, side, w, o) {
    o = o || {};
    var k = o.k || 1, sg = side === 'l' ? 1 : -1, x = w[0], y = w[1];
    var Y = o.down ? function (v) { return 2 * y - v; } : function (v) { return v; };
    var tip = y - 46 * k;
    var pts = [[x - 9 * k, y], [x - 11 * k, y - 18 * k], [x - 11 * k, y - 26 * k], [x - 10 * k, tip + 8 * k], [x - 7 * k, tip + 1], [x - 2 * k, tip - 2], [x + 3 * k, tip], [x + 7 * k, tip + 4 * k],
      [x + 10 * k, tip + 12 * k], [x + 10 * k, y - 22 * k], [x + 17 * k, y - 26 * k], [x + 19 * k, y - 22 * k], [x + 12 * k, y - 10 * k], [x + 9 * k, y]];
    if (sg > 0) pts = pts.map(function (p) { return [2 * x - p[0], p[1]]; });
    pts = pts.map(function (p) { return [p[0], Y(p[1])]; });
    var lay = [
      { clip: true, stroke: P.dp, sw: 0.8, op: 0.5, d: [-4.5, 0, 4.5].map(function (dx) { return open([[x + dx * k, Y(tip + 6 * k)], [x + dx * k, Y(y - 26 * k)]]); }).join(' ') },
      { clip: true, stroke: P.dp, sw: 0.8, op: 0.45, d: open([[x - sg * 7 * k, Y(y - 16 * k)], [x + sg * 2 * k, Y(y - 10 * k)], [x + sg * 8 * k, Y(y - 12 * k)]]) },
      { clip: true, fill: P.lip || P.sh, op: 0.35, d: ellipse(x - sg * 1, Y(y - 14 * k), 7 * k, 6 * k) },
      { clip: true, fill: P.sh, op: 0.6, d: closed([[x + 4 * k, Y(tip + 2)], [x + 12 * k, Y(tip + 10)], [x + 12 * k, y], [x + 6 * k, y]]) }
    ];
    return { id: o.id || 'hand-' + side, parent: o.parent || 'fore-' + side, pivot: [x, y], fill: P.sk, d: closed(pts, 0.9), layers: lay };
  }

  // ------------------------------------------------------------------ head and face
  var HEAD = {
    hero: [[0, 84], [22, 87], [36, 96], [43, 110], [45, 126], [44, 142], [41, 153], [35, 164], [25, 173], [13, 179], [0, 181]],
    soft: [[0, 84], [22, 87], [36, 96], [43, 110], [45, 126], [44, 142], [40, 155], [33, 166], [22, 175], [11, 180], [0, 181]],
    broad: [[0, 82], [24, 85], [40, 95], [48, 110], [50, 126], [49, 142], [46, 154], [40, 166], [28, 176], [14, 181], [0, 182]],
    female: [[0, 86], [21, 89], [34, 98], [40, 112], [42, 126], [41, 141], [37, 154], [30, 166], [20, 175], [10, 180], [0, 181]],
    elder: [[0, 84], [22, 87], [37, 96], [44, 110], [46, 126], [45, 142], [42, 154], [36, 166], [26, 176], [13, 181], [0, 182]]
  };

  /**
   * Head part. o {shape, P (skin), eyes: 'open'|'lowered'|'closed-left', brow, smile, lobes (long earlobes),
   * tilak: 'vaishnava'|'tripundra'|null, thirdEye, beard (layers added by the figure), ears: false}.
   */
  function headPart(P, o) {
    o = o || {};
    var half = HEAD[o.shape || 'hero'];
    var lobe = o.lobes ? 18 : 0;
    var ear = [[42, 124], [49, 119], [53, 126], [53, 140], [49, 152 + lobe * 0.6], [47, 158 + lobe], [43, 158 + lobe * 0.8], [42, 150]];
    var base = sym(half) + (o.ears === false ? '' : ' ' + pair(ear));
    var lay = [];
    // Shadow side of the face, the eye sockets, under the nose, lip and chin.
    lay.push({ clip: true, fill: P.sh, d: closed(R([[30, 96], [41, 112], [44, 128], [42, 146], [36, 162], [25, 174], [13, 180], [22, 168], [32, 152], [36, 136], [34, 118], [26, 102]])) });
    lay.push({ clip: true, fill: P.sh, d: pair([[52, 124], [54, 140], [48, 160], [42, 160], [44, 134]]) });
    lay.push({ clip: true, fill: P.sh, op: 0.55, d: pair([[6, 125], [14, 121], [26, 121], [32, 126], [24, 125], [14, 126]]) });
    lay.push({ clip: true, fill: P.sh, d: closed(R([[2, 128], [6, 132], [8, 146], [10, 151], [4, 152], [3, 140]])) });
    lay.push({ clip: true, fill: P.sh, op: 0.7, d: sym([[0, 166], [6, 168.5], [9, 171], [0, 172.5]]) });
    lay.push({ clip: true, fill: P.hl, op: 0.6, d: closed(L([[8, 99], [22, 96], [32, 102], [26, 108], [12, 107]])) });
    lay.push({ clip: true, fill: P.hl, op: 0.3, d: closed(L([[20, 140], [32, 137], [38, 142], [30, 146]])) });
    lay.push({ clip: true, fill: P.hl, op: 0.6, d: closed([[CX - 2.6, 132], [CX - 0.6, 132], [CX - 0.6, 146], [CX - 3.6, 147]]) });
    // Ears: inner whorl.
    if (o.ears !== false) lay.push({ clip: true, stroke: P.dp, sw: 0.9, op: 0.55, d: pairOpen([[47, 128], [50, 132], [49, 142], [46, 148]]) });
    // Brows: tapered bows rising to the outer third.
    var browCol = o.browColour || '#1F1817';
    var BROW = {
      bow: [[5, 120], [11, 116], [20, 113.5], [29, 114.5], [35, 118, 1], [28, 117], [20, 116.5], [11, 119], [6, 122, 1]],
      level: [[5, 119], [11, 115.5], [20, 114], [29, 114.5], [36, 117, 1], [28, 117.4], [20, 117.2], [11, 118.6], [6, 121.6, 1]],
      fierce: [[4, 122], [11, 117], [20, 114], [29, 113], [36, 114.5, 1], [28, 116], [20, 117.6], [11, 120.4], [5, 125, 1]]
    };
    lay.push({ fill: browCol, d: pair(BROW[o.brow || 'bow']) });
    if (o.brow === 'fierce') lay.push({ clip: true, stroke: P.dp, sw: 1, op: 0.5, d: open([[CX - 4, 116], [CX - 2, 124]]) + ' ' + open([[CX + 4, 116], [CX + 2, 124]]) });
    // Eyes.
    var eyes = o.eyes || 'open';
    var eyeHalf = eyes === 'lowered'
      ? [[6, 132, 1], [12, 129.5], [19, 128.6], [26, 129.4], [32, 130.5, 1], [26, 132.6], [19, 133.4], [12, 133.2]]
      : [[6, 131.5, 1], [11, 127], [18, 125.2], [25, 125.6], [32.5, 127.6, 1], [26, 131.4], [19, 133.2], [12, 133.2]];
    var eyeR = closed(R(eyeHalf)), eyeL = closed(L(eyeHalf));
    [[eyeR, 1], [eyeL, -1]].forEach(function (e) {
      var sx = e[1], ex = CX + sx * 18.6;
      if (o.closedEye && ((o.closedEye === 'r' && sx < 0) || (o.closedEye === 'l' && sx > 0))) {
        // The eye given at Mimir's well: a sunken, closed lid and an old scar.
        lay.push({ fill: P.sh, d: ellipse(ex, 129, 15, 8) });
        lay.push({ stroke: INK, sw: 1.6, d: open([[CX + sx * 6, 130.5], [CX + sx * 18, 132.4], [CX + sx * 31, 129.6]]) });
        lay.push({ stroke: P.dp, sw: 1.3, op: 0.8, d: open([[CX + sx * 24, 112], [CX + sx * 20, 128], [CX + sx * 15, 146]]) });
        return;
      }
      lay.push({ fill: '#F1E9DC', d: e[0] });
      if (eyes === 'lowered') {
        lay.push({ clip: e[0], fill: P.eye, d: ellipse(ex, 133.4, 4.6, 4) });
      } else {
        var ix = ex - 0.8;
        lay.push({ clip: e[0], fill: o.iris || P.eye, d: circle(ix, 129.4, 4.8) });
        lay.push({ clip: e[0], fill: '#0D0907', d: circle(ix, 129.4, 2.2) });
        lay.push({ clip: e[0], fill: P.sh, op: 0.5, d: closed([[ex - 15, 120], [ex + 15, 120], [ex + 15, 128], [ex - 15, 128.5]]) });
        lay.push({ fill: '#FFF8EC', d: circle(ix - 1.6, 127.8, 1.05) });
        if (o.glowEye) lay.push({ fill: { radial: [[0, o.glowEye, 0.9], [1, o.glowEye, 0]], cx: ix, cy: 129.4, r: 16 }, d: circle(ix, 129.4, 16) });
      }
      // Upper lid with a kohl line that lifts at the outer corner (the lotus-petal eye).
      var up = eyeHalf.slice(0, 5).map(function (p) { return [CX + sx * p[0], p[1]]; });
      up.push([CX + sx * 35.4, up[4][1] - 2.4]);
      lay.push({ stroke: INK, sw: 2.1, d: open(up) });
      lay.push({ stroke: INK, sw: 0.8, op: 0.55, d: open(eyeHalf.slice(4).concat([eyeHalf[0]]).map(function (p) { return [CX + sx * p[0], p[1]]; })) });
      if (eyes !== 'lowered') lay.push({ stroke: P.dp, sw: 0.8, op: 0.35, d: open([[CX + sx * 12, 122.6], [CX + sx * 19, 121.6], [CX + sx * 26, 123]]) });
      else lay.push({ stroke: P.dp, sw: 0.9, op: 0.5, d: open([[CX + sx * 9, 126.4], [CX + sx * 19, 124.6], [CX + sx * 30, 127]]) });
    });
    // Nose: bridge shadow, wings and nostrils.
    lay.push({ stroke: P.dp, sw: 1, op: 0.5, d: open([[CX + 3, 129], [CX + 4.4, 142], [CX + 6.6, 148]]) });
    lay.push({ stroke: P.dp, sw: 1.2, op: 0.75, d: open([[CX - 9, 148.6], [CX - 7.6, 152.4], [CX - 3, 152.4], [CX, 153.8], [CX + 3, 152.4], [CX + 7.6, 152.4], [CX + 9, 148.6]]) });
    lay.push({ fill: P.dp, op: 0.7, d: ellipse(CX - 4.2, 151.6, 2, 1.1, -12) + ' ' + ellipse(CX + 4.2, 151.6, 2, 1.1, 12) });
    // Mouth: a full lower lip and a bowed upper lip; corners lift slightly (Rama 'speaks first with a smile').
    var sm = o.smile === undefined ? 1 : o.smile;
    var lipUp = [[-12.5, 162 - sm], [-6, 160], [-2, 159.4], [0, 160.2], [2, 159.4], [6, 160], [12.5, 162 - sm, 1], [6, 162.6], [0, 163], [-6, 162.6]];
    var lipLo = [[-11, 162.6], [0, 163], [11, 162.6, 1], [7, 167], [0, 168.6], [-7, 167]];
    lay.push({ fill: P.lip, d: closed(lipUp.map(function (p) { return [CX + p[0], p[1], p[2]]; })) });
    lay.push({ fill: P.lip, d: closed(lipLo.map(function (p) { return [CX + p[0], p[1], p[2]]; })) });
    lay.push({ fill: P.hl, op: 0.35, d: ellipse(CX - 2.5, 165.4, 4.4, 1.3) });
    lay.push({ stroke: INK, sw: 1.15, op: 0.85, d: open([[CX - 13, 161.6 - sm], [CX - 6, 162.4], [CX, 163], [CX + 6, 162.4], [CX + 13, 161.6 - sm]]) });
    // Marks on the brow.
    if (o.tilak === 'vaishnava') {
      lay.push({ stroke: '#F4EEDF', sw: 2.1, d: open([[CX - 5.4, 96], [CX - 5, 112], [CX - 2.6, 118], [CX, 119], [CX + 2.6, 118], [CX + 5, 112], [CX + 5.4, 96]]) });
      lay.push({ stroke: '#C8321F', sw: 2, d: open([[CX, 99], [CX, 116]]) });
    } else if (o.tilak === 'tripundra') {
      lay.push({ stroke: '#F2EEE6', sw: 2.4, d: [104, 109, 114].map(function (y) { return open([[CX - 24, y + 1.5], [CX, y], [CX + 24, y + 1.5]]); }).join(' ') });
    } else if (o.tilak === 'sindoor') {
      lay.push({ stroke: '#D23B1E', sw: 3.2, d: open([[CX, 100], [CX, 117]]) });
    } else if (o.tilak === 'urna') {
      lay.push({ fill: P.dp, op: 0.6, d: circle(CX, 121, 2) });
    } else if (o.tilak === 'jina') {
      // A Svetambara image's applied tilaka: a small gold lozenge on the brow (never the Buddha's urna).
      lay.push({ fill: GOLD.b, d: closed([[CX, 104, 1], [CX + 4, 110], [CX, 116, 1], [CX - 4, 110]]) });
      lay.push({ stroke: GOLD.s, sw: 0.8, d: closed([[CX, 104, 1], [CX + 4, 110], [CX, 116, 1], [CX - 4, 110]]) });
    }
    if (o.thirdEye) {
      lay.push({ fill: '#F1E9DC', d: closed([[CX, 101, 1], [CX + 2.8, 107.5], [CX, 114, 1], [CX - 2.8, 107.5]]) });
      lay.push({ fill: '#B8321F', d: ellipse(CX, 107.5, 1.3, 3) });
      lay.push({ stroke: INK, sw: 1, d: closed([[CX, 101, 1], [CX + 2.8, 107.5], [CX, 114, 1], [CX - 2.8, 107.5]]) });
    }
    lay.push({ clip: true, stroke: P.rim, sw: 1.5, op: 0.6, d: open(R([[36, 98], [43, 110], [45, 126], [44, 142], [40, 156]])) });
    return { id: 'head', parent: 'torso', pivot: [CX, 182], fill: P.sk, d: base, layers: lay.concat(o.layers || []) };
  }

  // ------------------------------------------------------------------ ornaments and dress helpers
  var GOLD = { b: '#C9962E', s: '#9A6C1C', h: '#F1D27A' };
  /** A gold band across a limb at fraction t of a chain (keyura armlet, kankana bracelet). */
  function band(J, st, sg, t, w) {
    var a = along(J, t - w), b = along(J, t + w), s = st.reduce(function (m, x) { return Math.abs(x[0] - t) < Math.abs(m[0] - t) ? x : m; });
    var n1 = [-a.d[1], a.d[0]], n2 = [-b.d[1], b.d[0]], r1 = Math.max(s[1], s[2]) + 1.6;
    return closed([[a.p[0] + n1[0] * r1, a.p[1] + n1[1] * r1, 1], [b.p[0] + n2[0] * r1, b.p[1] + n2[1] * r1, 1], [b.p[0] - n2[0] * r1, b.p[1] - n2[1] * r1, 1], [a.p[0] - n1[0] * r1, a.p[1] - n1[1] * r1, 1]]);
  }

  /** Dhoti: a draped lower garment with a pleated front fall. o {hem (y), colour {b, s, h}, fall}. */
  function dhotiPart(o) {
    var hem = o.hem || 640, C = o.colour, fall = o.fall === undefined ? 700 : o.fall, wd = o.wide || 0;
    var half = [[0, 340], [56, 338], [60 + wd * 0.3, 366], [66 + wd * 0.6, 402], [73 + wd, 444], [77 + wd, 510], [76 + wd, 590], [72 + wd, hem], [56, hem + 8], [36, hem + 2], [22, hem - 12], [10, hem - 26], [0, hem - 30]];
    var base = sym(half);
    var pleat = closed([[CX - 13, 352], [CX + 15, 352], [CX + 21, 460], [CX + 25, fall - 10], [CX + 17, fall + 2, 1], [CX + 10, fall - 6], [CX + 3, fall + 4, 1], [CX - 4, fall - 6], [CX - 11, fall + 4, 1], [CX - 18, fall - 10], [CX - 20, 460]]);
    var lay = [
      { clip: true, fill: C.s, d: closed(R([[34, 330], [82, 330], [82, hem + 12], [56, hem + 12], [62, 560], [58, 470], [46, 400]])) },
      { clip: true, fill: C.s, op: 0.8, d: closed([[CX - 28, 440], [CX + 28, 440], [CX + 22, hem + 10], [CX - 22, hem + 10]]) },
      { clip: true, fill: C.h, op: 0.6, d: closed(L([[46, 360], [66, 362], [72, 420], [76, 500], [70, 560], [62, 500], [56, 420]])) },
      { clip: true, stroke: C.s, sw: 1.4, d: [[-52, -60, -66], [-30, -36, -40], [34, 44, 52], [56, 66, 70]].map(function (xs) { return open([[CX + xs[0] * 0.9, 372], [CX + xs[1], 470], [CX + xs[2], hem - 4]]); }).join(' ') },
      { clip: true, stroke: INK, sw: 0.9, op: 0.35, d: open([[CX - 56, 396], [CX - 20, 418], [CX + 20, 418], [CX + 56, 396]]) }
    ];
    if (o.texture) lay = lay.concat(o.texture);
    return [
      { id: 'pelvis', pivot: [CX, 340], fill: C.b, d: base, layers: lay },
      { id: 'pleats', parent: 'pelvis', pivot: [CX, 352], fill: C.b, d: pleat, layers: [
        { clip: true, fill: C.s, d: closed([[CX + 4, 350], [CX + 18, 350], [CX + 28, fall + 6], [CX + 8, fall + 6]]) },
        { clip: true, stroke: C.s, sw: 1.2, d: open([[CX - 4, 356], [CX - 6, 480], [CX - 4, fall - 4]]) + ' ' + open([[CX + 6, 356], [CX + 8, 480], [CX + 10, fall - 4]]) },
        { clip: true, fill: C.h, op: 0.5, d: closed([[CX - 13, 352], [CX - 6, 352], [CX - 10, fall], [CX - 19, fall - 8]]) }
      ] }
    ];
  }

  /** Sacred thread (yajnopavita) from the left shoulder to the right hip, as a torso layer. */
  function threadLayers(col) {
    var path = open([[CX + 58, 202], [CX + 40, 232], [CX + 8, 280], [CX - 24, 322], [CX - 50, 352], [CX - 58, 372]]);
    return [{ clip: true, stroke: '#2B1D14', sw: 3.4, op: 0.22, d: path }, { clip: true, stroke: col || '#F1E7CF', sw: 2.2, d: path }];
  }

  /**
   * Girdle over the waist where the dhoti is tied (covers the torso's lower edge). o {style: 'cord'
   * (bark-fibre rope, forest) | 'sash' (silk with a jewelled clasp, royal) | 'belt' | 'serpent', colour, knot (-1|1)}.
   */
  function girdlePart(o) {
    o = o || {};
    var C = o.colour || { b: '#7A4A26', s: '#55321A', h: '#A8743F' }, kx = (o.knot || -1) * 30, w = o.w || 64;
    var lay = [], base;
    if (o.style === 'sash' || o.style === 'belt') {
      base = sym([[0, 342], [w - 6, 340], [w, 348], [w + 2, 366], [w - 4, 376], [0, 379]]);
      lay.push({ clip: true, fill: C.s, d: closed(R([[20, 330], [w + 8, 330], [w + 8, 386], [30, 386]])) });
      lay.push({ clip: true, stroke: C.h, sw: 1.2, op: 0.8, d: open([[CX - w, 350], [CX, 353], [CX + w, 350]]) + ' ' + open([[CX - w, 366], [CX, 370], [CX + w, 366]]) });
      if (o.style === 'sash') {
        lay.push({ fill: GOLD.b, d: ellipse(CX, 359, 12, 13) });
        lay.push({ fill: '#B8321F', d: ellipse(CX, 359, 5, 6) });
        lay.push({ stroke: GOLD.s, sw: 1.2, d: ellipse(CX, 359, 12, 13) });
      }
    } else {
      // Twisted cord: two rope turns with the knot to one side and the ends hanging.
      base = sym([[0, 343], [w - 4, 341], [w + 1, 349], [w + 2, 366], [w - 2, 375], [0, 378]]);
      lay.push({ clip: true, fill: C.s, d: closed(R([[24, 330], [w + 8, 330], [w + 8, 386], [34, 386]])) });
      var twists = [];
      for (var x = -w; x < w; x += 7) twists.push(open([[CX + x, 345], [CX + x + 5, 357]]) + ' ' + open([[CX + x + 1, 361], [CX + x + 6, 374]]));
      lay.push({ clip: true, stroke: C.h, sw: 1.1, op: 0.85, d: twists.join(' ') });
      lay.push({ clip: true, stroke: INK, sw: 1, op: 0.5, d: open([[CX - w, 359], [CX, 362], [CX + w, 359]]) });
    }
    var parts = [{ id: 'girdle', parent: 'torso', pivot: [CX, 360], fill: C.b, d: base, layers: lay }];
    if (o.ends !== false) {
      var ex = CX + kx;
      parts.push({ id: 'girdle-ends', parent: 'girdle', pivot: [ex, 362], fill: C.b,
        d: closed([[ex - 8, 356], [ex + 8, 356], [ex + 11, 422], [ex + 6, 452, 1], [ex + 2, 426], [ex - 2, 446, 1], [ex - 6, 422]]) + ' ' + ellipse(ex, 360, 10, 8),
        layers: [{ clip: true, fill: C.s, d: closed([[ex + 1, 352], [ex + 14, 352], [ex + 14, 460], [ex + 2, 460]]) }, { clip: true, stroke: C.h, sw: 1, op: 0.7, d: open([[ex - 4, 370], [ex - 3, 422]]) }] });
    }
    return parts;
  }

  /** Royal ornaments: kundala at the lobes, a haar necklace on the chest, keyura and kankana on the arms. */
  function jewelLayers(which, P, o) {
    o = o || {};
    if (which === 'haar') {
      var r = [], pearls = [];
      for (var i = 0; i <= 16; i++) { var t = i / 16, a = Math.PI * (0.06 + 0.88 * t); pearls.push(circle(CX - Math.cos(a) * 40, 198 + Math.sin(a) * (o.drop || 46), 2.6)); }
      r.push({ fill: '#F4ECDA', d: pearls.join(' ') });
      r.push({ fill: GOLD.b, d: closed([[CX, 236, 1], [CX + 9, 246], [CX, 260, 1], [CX - 9, 246]]) });
      r.push({ fill: '#B8321F', d: ellipse(CX, 247, 3.4, 5) });
      r.push({ stroke: GOLD.s, sw: 1, d: closed([[CX, 236, 1], [CX + 9, 246], [CX, 260, 1], [CX - 9, 246]]) });
      r.push({ stroke: GOLD.b, sw: 2.4, d: open([[CX - 30, 196], [CX - 22, 214], [CX, 222], [CX + 22, 214], [CX + 30, 196]]) });
      return r;
    }
    return [];
  }
  function kundalaPart(side, o) {
    o = o || {};
    var sg = side === 'l' ? 1 : -1, x = CX + sg * 48, y = o.y || 160, s = o.s || 1;
    var d = o.kind === 'hoop'
      ? ellipse(x, y + 9 * s, 7 * s, 9 * s) + ' ' + ellipse(x, y + 9 * s, 4.2 * s, 6 * s)
      : o.kind === 'disc' ? circle(x, y + 8 * s, 8 * s)
      : circle(x, y + 4 * s, 4.5 * s) + ' ' + closed([[x, y + 8 * s, 1], [x + 7 * s, y + 18 * s], [x, y + 30 * s, 1], [x - 7 * s, y + 18 * s]]);
    return { id: 'kundala-' + side, parent: o.parent || 'head', pivot: [x, y], fill: GOLD.b, rule: 'evenodd', d: d,
      layers: [{ fill: o.gem || '#B8321F', d: o.kind === 'hoop' ? '' : o.kind === 'disc' ? circle(x, y + 8 * s, 3.4 * s) : ellipse(x, y + 18 * s, 2.6 * s, 4.4 * s) },
        { stroke: GOLD.s, sw: 0.9, d: o.kind === 'disc' ? circle(x, y + 8 * s, 6 * s) : '' }] };
  }
  /** Keyura (upper-arm band with a leaf crest) and kankana (bracelet), clipped to the limb. */
  function armJewels(parts, side, J, o) {
    o = o || {};
    var sg = side === 'l' ? 1 : -1, k = o.k || 1;
    var arm = parts.filter(function (p) { return p.id === 'arm-' + side; })[0], fore = parts.filter(function (p) { return p.id === 'fore-' + side; })[0];
    var ST = o.hero ? ARMH : ARM;
    var ja = [J.s, J.e], jf = [J.e, J.w], up = scaleSt(ST.upper, k), fo = scaleSt(ST.fore, k);
    var c = along(ja, 0.3);
    arm.layers = arm.layers.concat([
      { clip: true, fill: GOLD.b, d: band(ja, up, sg, 0.3, 0.035) },
      { fill: GOLD.b, d: closed([[c.p[0] + sg * -2, c.p[1] - 13, 1], [c.p[0] + sg * 6, c.p[1] - 3], [c.p[0] + sg * 2, c.p[1] + 5, 1], [c.p[0] - sg * 6, c.p[1] - 1]]) },
      { fill: '#B8321F', d: ellipse(c.p[0] + sg * 1, c.p[1] - 3, 2, 3) }
    ]);
    fore.layers = fore.layers.concat([
      { clip: true, fill: GOLD.b, d: band(jf, fo, sg, 0.9, 0.05) },
      { clip: true, stroke: GOLD.s, sw: 0.9, d: open([along(jf, 0.9).p, along(jf, 0.9).p].map(function (p, i) { return [p[0] + (i ? 12 : -12), p[1]]; })) }
    ]);
  }

  function meta(m) { m.build = 'human'; m.view = 'front'; return m; }

  /**
   * Jata-mandala: matted locks coiled into a rounded knot on the crown and bound (Valmiki 2.52.69,
   * "a rounded mass of matted locks"). C hair colours; o {y offset, h height, w width, tie colour}.
   */
  function jataKnot(C, o) {
    o = o || {};
    var dy = o.y || 0, w = o.w || 28, top = (o.top !== undefined ? o.top : 10) + dy, bot = (o.bot !== undefined ? o.bot : 68) + dy, h = bot - top;
    var shape = closed([[CX - w + 2, bot], [CX - w - 2, bot - h * 0.3], [CX - w + 2, bot - h * 0.62], [CX - w * 0.55, top + h * 0.12], [CX - 4, top], [CX + w * 0.4, top + 2], [CX + w * 0.75, top + h * 0.2], [CX + w + 2, bot - h * 0.55], [CX + w + 2, bot - h * 0.25], [CX + w - 2, bot]]);
    var wraps = [], strands = [];
    for (var i = 1; i <= 4; i++) {
      var y = bot - 6 - i * h * 0.19, ww = w * (1 - Math.pow(i / 5, 2) * 0.55);
      wraps.push(open([[CX - ww, y + 3], [CX - ww * 0.4, y - 2.5], [CX + ww * 0.3, y - 2], [CX + ww, y + 4]]));
      for (var j = -2; j <= 2; j++) strands.push(open([[CX + j * ww * 0.36 - 3, y + 2], [CX + j * ww * 0.36 + 2, y - h * 0.08], [CX + j * ww * 0.36 + 4, y - h * 0.17]]));
    }
    return { id: 'jata', parent: 'hair', pivot: [CX, bot], fill: C.b, d: shape,
      layers: [
        { clip: true, fill: C.s, d: closed([[CX + 6, top - 4], [CX + w + 6, top], [CX + w + 6, bot + 4], [CX + 10, bot + 4], [CX + 14, bot - h * 0.5]]) },
        { clip: true, fill: C.h, op: 0.55, d: closed([[CX - w + 4, bot - 8], [CX - w + 2, bot - h * 0.55], [CX - w * 0.4, top + 10], [CX - w * 0.2, top + 16], [CX - w * 0.55, bot - h * 0.5], [CX - w * 0.5, bot - 10]]) },
        { clip: true, stroke: C.s, sw: 1.6, d: wraps.join(' ') },
        { clip: true, stroke: C.h, sw: 0.9, op: 0.6, d: strands.join(' ') },
        { fill: o.tie || '#7A4A26', d: closed([[CX - w + 2, bot - 7], [CX + w - 2, bot - 7], [CX + w - 3, bot + 1], [CX - w + 3, bot + 1]]) },
        { stroke: '#C9962E', sw: 0.9, op: 0.8, d: open([[CX - w + 3, bot - 3], [CX + w - 3, bot - 3]]) }
      ] };
  }

  /** Kirita-mukuta: the tall cylindrical crown of kings and of Vishnu's forms, in tiers to a finial. */
  function kiritaPart(o) {
    o = o || {};
    var b0 = o.base || 96, t0 = o.top === undefined ? 6 : o.top, wB = o.wB || 42, wT = o.wT || 30;
    var shape = closed([[CX - wB, b0, 1], [CX - wB + 2, b0 - 26], [CX - wT, t0 + 26], [CX - wT + 4, t0 + 12], [CX - 10, t0 + 2], [CX, t0 - 18, 1], [CX + 10, t0 + 2], [CX + wT - 4, t0 + 12], [CX + wT, t0 + 26], [CX + wB - 2, b0 - 26], [CX + wB, b0, 1]]);
    var tiers = [86, 70, 52, 34].map(function (y) { var ww = lerp(wT, wB, (y - t0) / (b0 - t0)) - 1; return open([[CX - ww, y], [CX, y + 3], [CX + ww, y]]); }).join(' ');
    var petals = [];
    for (var i = -3; i <= 3; i++) petals.push(closed([[CX + i * 10 - 4, 70], [CX + i * 10, 58, 1], [CX + i * 10 + 4, 70]]));
    return { id: 'crown', parent: 'hair', pivot: [CX, b0], fill: GOLD.b, d: shape,
      layers: [
        { clip: true, fill: GOLD.s, d: closed([[CX + 8, t0 - 30], [CX + wB + 6, t0], [CX + wB + 6, b0 + 4], [CX + 16, b0 + 4], [CX + 20, 40]]) },
        { clip: true, fill: GOLD.h, op: 0.6, d: closed([[CX - wB + 4, b0 - 4], [CX - wB + 6, b0 - 30], [CX - wT + 4, 30], [CX - wT + 10, 30], [CX - wB + 14, b0 - 30], [CX - wB + 12, b0 - 4]]) },
        { clip: true, stroke: GOLD.s, sw: 1.6, d: tiers },
        { clip: true, fill: GOLD.s, op: 0.55, d: petals.join(' ') },
        { fill: '#B8321F', d: ellipse(CX, 80, 5, 6) + ' ' + ellipse(CX - 24, 80, 3, 3.6) + ' ' + ellipse(CX + 24, 80, 3, 3.6) },
        { fill: '#2F6B4F', d: ellipse(CX, 45, 3.4, 4) },
        { stroke: GOLD.h, sw: 1, d: open([[CX - wB + 1, b0 - 3], [CX, b0], [CX + wB - 1, b0 - 3]]) }
      ] };
  }

  // ------------------------------------------------------------------ shared helpers (fur, ruff, vanara head, meander, ravens)
  /** Short fur strokes scattered along a limb chain (deterministic, from a fixed lattice). */
  function furStrokes(J, st, side, col, n) {
    var out = [];
    for (var i = 0; i < (n || 16); i++) {
      var t = 0.06 + 0.88 * (i / ((n || 16) - 1)), a = along(J, t), nn = [-a.d[1], a.d[0]];
      var s = st.reduce(function (m, x) { return Math.abs(x[0] - t) < Math.abs(m[0] - t) ? x : m; });
      [-0.55, 0.05, 0.6].forEach(function (f, j) {
        var r = f * (f < 0 ? s[2] : s[1]) * (side > 0 ? -1 : 1), off = ((i + j) % 3 - 1) * 2.2;
        var p = [a.p[0] + nn[0] * r + a.d[0] * off, a.p[1] + nn[1] * r + a.d[1] * off];
        out.push(open([p, [p[0] + a.d[0] * 6 + nn[0] * (j - 1) * 1.6, p[1] + a.d[1] * 6 + nn[1] * (j - 1) * 1.6]]));
      });
    }
    return { clip: true, stroke: col, sw: 0.9, op: 0.55, d: out.join(' ') };
  }

  /** Tufted ring for a fur ruff: alternating tufts between angles a0 and a1. cx, cy centre. */
  function tufts(cx, cy, rx, ry, n, depth, a0, a1) {
    var pts = [], from = a0 === undefined ? 0 : a0, to = a1 === undefined ? Math.PI * 2 : a1, full = a0 === undefined;
    var m = n * 2;
    for (var i = 0; i < (full ? m : m + 1); i++) {
      var a = from + (to - from) * i / m, k = i % 2 ? 1 - depth : 1;
      pts.push(i % 2 ? [cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k] : [cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k, 1]);
    }
    return pts;
  }

  /**
   * Vanara head, front: a fur-covered head with a bare face mask (eyes and muzzle), heavy brow,
   * flat broad nose, a full upper lip over a strong, slightly swollen jaw (hanu, "jaw": Kishkindha
   * 4.66.23-24), round ears and a fur ruff that frames the face. F fur palette, S face skin.
   */
  function vanaraHead(F, S, o) {
    o = o || {};
    var half = [[0, 80], [26, 83], [42, 94], [50, 112], [52, 130], [50, 148], [46, 164], [38, 178], [24, 188], [12, 192], [0, 193]];
    var ear = [[46, 108], [56, 100], [66, 106], [68, 122], [62, 136], [52, 138], [47, 128]];
    var base = sym(half) + ' ' + pair(ear);
    var mask = [[0, 106], [12, 104], [24, 106], [34, 114], [38, 126], [36, 140], [33, 152], [32, 166], [28, 180], [18, 188], [8, 191], [0, 191]];
    var lay = [];
    lay.push({ clip: true, fill: F.sh, d: closed(R([[30, 86], [48, 104], [53, 132], [49, 160], [38, 182], [24, 192], [30, 172], [40, 150], [42, 122], [36, 100]])) });
    lay.push({ clip: true, fill: S.sh, d: pair([[52, 106], [60, 106], [63, 120], [58, 132], [52, 130]]) });
    // The bare face.
    lay.push({ fill: S.sk, d: sym(mask) });
    lay.push({ clip: sym(mask), fill: S.sh, d: closed(R([[14, 104], [36, 112], [40, 140], [34, 168], [28, 186], [12, 192], [22, 172], [28, 148], [28, 124], [18, 110]])) });
    // Brow ridge and brows of fur.
    lay.push({ fill: S.dp, op: 0.55, d: sym([[0, 116], [10, 111], [22, 110], [33, 115], [35, 121], [24, 118], [12, 119], [0, 122]]) });
    lay.push({ fill: F.dp, d: pair(o.fierce ? [[3, 120], [12, 112], [24, 108], [34, 109], [39, 112, 1], [26, 111], [14, 116], [5, 124, 1]] : [[3, 114], [12, 108], [24, 107], [34, 111], [38, 116, 1], [26, 113], [14, 114], [5, 118, 1]]) });
    if (o.fierce) lay.push({ stroke: S.dp, sw: 1.2, op: 0.6, d: open([[CX - 5, 112], [CX - 2, 122]]) + ' ' + open([[CX + 5, 112], [CX + 2, 122]]) });
    // Eyes: deep-set, almond, warm amber; a level gaze.
    var eyeHalf = [[6, 128, 1], [11, 124], [18, 122.4], [25, 123.6], [30, 127, 1], [25, 130.6], [18, 131.8], [11, 131]];
    [1, -1].forEach(function (sx) {
      var pts = eyeHalf.map(function (p) { return [CX + sx * p[0], p[1], p[2]]; }), eye = closed(pts), ix = CX + sx * 17.6;
      lay.push({ fill: S.dp, op: 0.45, d: ellipse(CX + sx * 18, 127, 15, 9) });
      lay.push({ fill: '#EFE2C8', d: eye });
      lay.push({ clip: eye, fill: o.iris || '#8A5A1C', d: circle(ix, 127.4, 4.6) });
      lay.push({ clip: eye, fill: '#120B06', d: circle(ix, 127.4, 2.3) });
      lay.push({ fill: '#FFF6E6', d: circle(ix - 1.5, 125.8, 1) });
      lay.push({ stroke: INK, sw: 2, d: open(pts.slice(0, 5)) });
      lay.push({ stroke: INK, sw: 0.8, op: 0.55, d: open(pts.slice(4).concat([pts[0]])) });
    });
    // Nose: short, flat and broad, the nostrils open forward.
    lay.push({ fill: S.sh, d: sym([[0, 130], [5, 132], [9, 144], [13, 150], [11, 155], [0, 157]]) });
    lay.push({ fill: S.dp, d: ellipse(CX - 5.6, 151.4, 3.4, 2.2, -16) + ' ' + ellipse(CX + 5.6, 151.4, 3.4, 2.2, 16) });
    lay.push({ fill: S.hl, op: 0.55, d: ellipse(CX - 2, 142, 2.2, 4) });
    // Muzzle: the full upper lip, the mouth line, the strong jaw and chin.
    lay.push({ fill: S.hl, op: 0.4, d: sym([[0, 156], [14, 157], [24, 164], [22, 170], [0, 168]]) });
    lay.push({ stroke: S.dp, sw: 1, op: 0.6, d: open([[CX, 157], [CX, 166]]) });
    lay.push({ stroke: INK, sw: 1.4, d: open([[CX - 25, 168], [CX - 14, 172], [CX, 173], [CX + 14, 172], [CX + 25, 168]]) });
    lay.push({ fill: S.lip, op: 0.7, d: sym([[0, 173], [12, 172.6], [20, 171], [14, 177], [0, 179]]) });
    lay.push({ fill: S.sh, d: closed(R([[4, 182], [20, 180], [30, 176], [28, 184], [16, 190], [4, 191]])) });
    lay.push({ stroke: S.dp, sw: 1, op: 0.5, d: open([[CX + 26, 176], [CX + 31, 168], [CX + 32, 156]]) });
    // The jaw struck by Indra's thunderbolt (his left, the viewer's right): a soft swelling line.
    if (o.hanu !== false) lay.push({ stroke: S.dp, sw: 1.1, op: 0.4, d: open([[CX + 10, 186], [CX + 20, 184], [CX + 27, 178]]) });
    // Cheek fur along the mask edge.
    lay.push({ stroke: F.dp, sw: 1, op: 0.6, d: [0, 1, 2, 3, 4, 5, 6, 7].map(function (i) {
      var t = i / 7, y = 120 + t * 64, x = 36 - t * 10 + (i % 2) * 2;
      return open([[CX + x, y], [CX + x + 7, y + 4]]) + ' ' + open([[CX - x, y], [CX - x - 7, y + 4]]);
    }).join(' ') });
    lay.push({ clip: true, stroke: F.rim, sw: 1.5, op: 0.6, d: open(R([[42, 94], [50, 112], [52, 130], [50, 148]])) });
    return { id: 'head', parent: 'torso', pivot: [CX, 190], fill: F.sk, d: base, layers: lay };
  }

  /** Greek key (meander) as a stroke path along a band starting at x0, y centre, length w. */
  function meander(x0, y, w) {
    var s = '', u = 5, x = x0;
    while (x + 2 * u <= x0 + w) {
      s += 'M' + f1(x) + ' ' + f1(y + u) + 'V' + f1(y - u) + 'H' + f1(x + 2 * u) + 'V' + f1(y + u * 0.2) + 'H' + f1(x + u) + 'V' + f1(y - u * 0.3) + ' ';
      x += 2 * u + 1.6;
    }
    return s;
  }

  /** Raven perched, side view, facing dir (+1 right, -1 left). */
  function raven(x, y, s, dir) {
    var k = dir || 1, X = function (dx) { return x + dx * s * k; };
    return closed([[X(-30), y - 4], [X(-12), y - 14], [X(6), y - 16], [X(16), y - 26], [X(26), y - 28], [X(34), y - 24, 1], [X(44), y - 20, 1], [X(32), y - 16], [X(26), y - 8], [X(10), y + 2], [X(-8), y + 6], [X(-30), y + 8, 1], [X(-46), y + 14, 1], [X(-34), y + 2]]);
  }
  // ------------------------------------------------------------------ heroic build
  // Heroic proportions (figure-design.md section 7): broad shoulders (2.6-3 head-widths), a deep
  // V-taper, a thick neck and traps, the muscle groups drawn as cel shapes (pec crescent, deltoid cap,
  // biceps lens, abs implied 2 x 3 with one-sided shadow, oblique wedge, quad teardrop, calf bean), a
  // wide stance, the head scaled down about the chin (about 8-8.5 heads) and an aura behind that puts
  // a warm rim light on both edges. Heroism first, then accuracy: every attribute still follows the
  // identity blocks, but bodies are idealised beyond the texts.
  // Widths are half-widths in figure units; the measured results in head units (H) are in
  // figure-design.md section 8 (shoulders 2.3-2.6 H, waist about 1.2 H, hips 1.5-1.75 H; a titan wider).
  var HERO = {
    warrior: { neck: 22, trap: 42, sh: 88, lat: 82, waist: 50, k: 1.04, legK: 1, head: 0.86, hh: 97, hip: 36, stance: 56, inset: 24 },
    titan: { neck: 28, trap: 50, sh: 100, lat: 92, waist: 60, k: 1.18, legK: 1.12, head: 0.78, hh: 113, hip: 42, stance: 62, inset: 30 },
    ascetic: { neck: 21, trap: 40, sh: 86, lat: 79, waist: 47, k: 1, legK: 0.98, head: 0.86, hh: 97, hip: 35, stance: 52, inset: 23 },
    goddess: { neck: 16, trap: 30, sh: 68, lat: 60, waist: 43, k: 0.82, legK: 0.9, head: 0.9, hh: 95, hip: 36, stance: 48, inset: 23 },
    elder: { neck: 25, trap: 46, sh: 92, lat: 88, waist: 56, k: 1.06, legK: 1.02, head: 0.9, hh: 98, hip: 38, stance: 54, inset: 24 }
  };
  var ARMH = { upper: [[0, 24, 13], [0.1, 31, 17], [0.28, 27, 20], [0.5, 23, 22], [0.74, 16, 15], [1, 13, 12.5]],
    fore: [[0, 13.5, 12.5], [0.16, 18, 15], [0.38, 16, 12.5], [0.72, 10.5, 9], [1, 9, 8.5]] };
  var LEGH = [[0, 33, 26], [0.1, 35, 26], [0.24, 33, 25], [0.36, 29, 24], [0.44, 24, 22], [0.49, 20, 18], [0.54, 20, 18],
    [0.6, 26, 23], [0.67, 25, 21], [0.78, 16, 14], [0.87, 11, 10], [0.91, 12.5, 11.5], [0.96, 17, 14], [1, 17.5, 14.5]];

  /**
   * Arm joints for a heroic body: shoulder from the preset, the wrist toward a target, the elbow from
   * two-bone IK with upper arm 1.45 H and forearm 1.15 H (H = the drawn head height). pick 'out' (the
   * elbow away from the body, for hanging and crossing arms) or 'low' (the elbow below, raised hands).
   */
  function armJ(b, side, target, pick) {
    var sg = side === 'l' ? 1 : -1, Hd = b.head * b.hh, UL = 1.45 * Hd, FL = 1.15 * Hd;
    var sh = [CX + sg * (b.sh - b.inset), 224];
    var e1 = ik2(sh, target, UL, FL, 1), e2 = ik2(sh, target, UL, FL, -1);
    var e = pick === 'low' ? (e1[1] > e2[1] ? e1 : e2) : (sg * e1[0] > sg * e2[0] ? e1 : e2);
    var dx = target[0] - e[0], dy = target[1] - e[1], dl = Math.hypot(dx, dy) || 1;
    return { s: sh, e: e, w: [e[0] + dx / dl * FL, e[1] + dy / dl * FL] };
  }
  /** Where a fist sits: beyond the wrist along the forearm. */
  function fistAt(J, d) {
    var dx = J.w[0] - J.e[0], dy = J.w[1] - J.e[1], dl = Math.hypot(dx, dy) || 1;
    return [J.w[0] + dx / dl * d, J.w[1] + dy / dl * d];
  }

  /** Radii [outer, inner] of a station list at fraction t. */
  function stAt(st, t) {
    for (var i = 1; i < st.length; i++) {
      if (t <= st[i][0] || i === st.length - 1) {
        var a = st[i - 1], b = st[i], u = Math.max(0, Math.min(1, (t - a[0]) / ((b[0] - a[0]) || 1)));
        return [lerp(a[1], b[1], u), lerp(a[2], b[2], u)];
      }
    }
    return [st[0][1], st[0][2]];
  }
  /** A point on a limb: fraction t along the chain, f from -1 (inner edge) through 0 (centre) to 1 (outer edge). */
  function lp(J, st, sg, t, f) {
    var a = along(J, t), n = [-a.d[1], a.d[0]], no = sg > 0 ? [-n[0], -n[1]] : n, r = stAt(st, t), rr = f >= 0 ? f * r[0] : f * r[1];
    return [a.p[0] + no[0] * rr, a.p[1] + no[1] * rr];
  }
  function scaleAbout(s, cx, cy) { return 'matrix(' + s + ' 0 0 ' + s + ' ' + f1(cx * (1 - s)) + ' ' + f1(cy * (1 - s)) + ')'; }
  /** Scale the head (and its children) and the given head-space parts about the chin. */
  function heroHead(parts, s, ids) {
    var tf = scaleAbout(s, CX, 182);
    parts.forEach(function (p) { if (p.id === 'head' || (ids && ids.indexOf(p.id) >= 0)) p.tf = tf; });
  }

  function heroTorsoHalf(b) {
    var n = b.neck, s = b.sh;
    return [[0, 154], [n, 156], [n + 1, 172], [n + 12, 184], [b.trap + 6, 192], [s - 24, 199], [s - 8, 208], [s, 224], [s - 3, 242],
      [b.lat + 2, 258], [b.lat, 278], [b.lat - 10, 302], [b.waist + 10, 326], [b.waist, 344], [b.waist + 2, 362], [b.waist + 5, 378, 1], [0, 380]];
  }

  /** Heroic torso. o {covered (clothed: no muscle detail), glow (rim colour), layers}. */
  function heroTorso(P, b, o) {
    o = o || {};
    var n = b.neck, s = b.sh, w = b.waist, Lt = b.lat, g = o.glow || P.rim, lay = [];
    lay.push({ clip: true, fill: P.sh, d: closed([[CX + s + 10, 190], [CX + s + 10, 400], [CX + w - 4, 400], [CX + w - 10, 344], [CX + Lt - 22, 298], [CX + s - 26, 250], [CX + s - 34, 214], [CX + n + 10, 186]]) });
    lay.push({ clip: true, fill: P.sh, d: sym([[0, 154], [n + 1, 156], [n - 1, 172], [n * 0.5, 182], [0, 184]]) });
    lay.push({ clip: true, fill: P.dp, op: 0.5, d: sym([[0, 154], [n, 156], [n - 3, 166], [0, 170]]) });
    if (!o.covered) {
      // Trapezius light, the neck's tendons, the clavicles.
      lay.push({ clip: true, fill: P.hl, op: 0.6, d: closed(L([[n + 1, 174], [n + 14, 184], [s * 0.55, 196], [s * 0.6, 202], [n + 10, 194], [n - 2, 184]])) });
      lay.push({ clip: true, stroke: P.dp, sw: 1, op: 0.45, d: pairOpen([[n - 3, 160], [n * 0.6, 178], [8, 196]]) });
      lay.push({ clip: true, stroke: P.dp, sw: 1.3, op: 0.5, d: pairOpen([[6, 206], [26, 202], [s * 0.48, 206], [s * 0.74, 213]]) });
      // Pectorals: a hard crescent of shadow along the lower edge, lit upper planes.
      var edge = [[3, 270], [12, 280], [s * 0.36, 283], [s * 0.6, 273], [s * 0.8, 254], [s - 16, 236]];
      var inner = [[s - 22, 234], [s * 0.78, 246], [s * 0.6, 263], [s * 0.36, 272], [12, 269], [3, 259]];
      lay.push({ clip: true, fill: P.sh, d: closed(R(edge.concat(inner))) });
      lay.push({ clip: true, fill: P.sh, op: 0.7, d: closed(L(edge.concat(inner))) });
      lay.push({ clip: true, stroke: P.dp, sw: 1.5, op: 0.55, d: pairOpen(edge) });
      lay.push({ clip: true, fill: P.hl, op: 0.55, d: closed(L([[6, 212], [s * 0.42, 209], [s * 0.7, 218], [s * 0.62, 234], [s * 0.36, 246], [10, 242]])) });
      lay.push({ clip: true, fill: P.hl, op: 0.25, d: closed(R([[6, 214], [s * 0.36, 212], [s * 0.5, 220], [s * 0.3, 232], [8, 232]])) });
      lay.push({ clip: true, stroke: P.dp, sw: 1.1, op: 0.5, d: open([[CX, 210], [CX, 272]]) });
      // Lats and serratus on the shadow side, fainter on the lit side.
      lay.push({ clip: true, fill: P.dp, op: 0.35, d: closed(R([[s - 12, 240], [Lt + 2, 258], [Lt - 1, 282], [Lt - 12, 276], [s - 24, 252]])) });
      [0, 1, 2].forEach(function (i) {
        var tri = function (sx) { return closed([[CX + sx * (Lt - 12 - i * 3), 282 + i * 11, 1], [CX + sx * (Lt - 30 - i * 3), 287 + i * 11], [CX + sx * (Lt - 14 - i * 3), 292 + i * 11, 1]]); };
        lay.push({ clip: true, fill: P.dp, op: 0.4, d: tri(1) }, { clip: true, fill: P.dp, op: 0.18, d: tri(-1) });
      });
      // Abdomen: implied 2 x 3 blocks, shadow on the lower edge of each, light on the lamp side.
      lay.push({ clip: true, stroke: P.dp, sw: 1.1, op: 0.5, d: open([[CX, 286], [CX, 370]]) });
      lay.push({ clip: true, stroke: P.dp, sw: 1.1, op: 0.42, d: pairOpen([[30, 288], [31, 312], [27, 342], [18, 372]]) });
      [304, 326, 348].forEach(function (y, i) {
        lay.push({ clip: true, stroke: P.dp, sw: 1.1, op: 0.42, d: pairOpen([[2, y], [14, y - 2.5], [29, y + 1]]) });
        lay.push({ clip: true, fill: P.sh, op: 0.6, d: closed(R([[3, y - 6], [27, y - 5], [29, y + 1], [3, y]])) }, { clip: true, fill: P.sh, op: 0.32, d: closed(L([[3, y - 6], [27, y - 5], [29, y + 1], [3, y]])) });
        lay.push({ clip: true, fill: P.hl, op: 0.42, d: ellipse(CX - 15, y - 13, 9, 5) }, { clip: true, fill: P.hl, op: 0.18, d: ellipse(CX + 15, y - 13, 8, 4.5) });
      });
      lay.push({ clip: true, stroke: P.dp, sw: 1.1, op: 0.42, d: pairOpen([[Lt - 10, 302], [w + 10, 328], [w + 3, 348], [w - 6, 366]]) });
      lay.push({ clip: true, stroke: P.dp, sw: 1.2, op: 0.45, d: pairOpen([[w - 5, 350], [32, 370], [16, 380]]) });
      lay.push({ clip: true, fill: P.dp, op: 0.7, d: ellipse(CX, 358, 3.2, 4.4) });
      lay.push({ clip: true, fill: P.hl, op: 0.5, d: closed(L([[s - 10, 226], [s - 5, 242], [Lt - 2, 262], [Lt - 8, 296], [w + 6, 324], [w, 342], [w - 8, 322], [Lt - 18, 290], [Lt - 16, 262], [s - 16, 240]])) });
    }
    // Backlight from the aura: a warm rim on both edges, stronger on the shadow side.
    var rimPts = [[s + 1, 226], [s - 2, 242], [Lt + 1, 258], [Lt - 1, 280], [Lt - 10, 302], [w + 9, 326], [w + 1, 344]];
    lay.push({ clip: true, stroke: g, sw: 2.6, op: 0.8, d: open(R(rimPts)) }, { clip: true, stroke: g, sw: 1.8, op: 0.5, d: open(L(rimPts)) });
    lay.push({ clip: true, stroke: g, sw: 1.6, op: 0.5, d: pairOpen([[n + 2, 174], [n + 12, 184], [b.trap + 6, 192]]) });
    return { id: 'torso', parent: 'pelvis', pivot: [CX, 340], fill: P.sk, d: sym(heroTorsoHalf(b)), layers: lay.concat(o.layers || []) };
  }

  /** Heroic upper arm and forearm: deltoid cap, biceps lens, triceps edge, brachioradialis; rim light. */
  function heroArms(P, side, J, b, o) {
    o = o || {};
    var sg = side === 'l' ? 1 : -1, k = (o.k || 1) * b.k, g = o.glow || P.rim;
    var up = scaleSt(ARMH.upper, k), fo = scaleSt(ARMH.fore, k), ja = [J.s, J.e], jf = [J.e, J.w];
    var lit = sg < 0 ? 'outer' : 'inner', dark = sg < 0 ? 'inner' : 'outer', litK = sg < 0 ? 1 : 0.5;
    var U = function (t, f) { return lp(ja, up, sg, t, f); }, F = function (t, f) { return lp(jf, fo, sg, t, f); };
    var upLay = [
      { clip: true, fill: P.sh, d: limbBand(ja, up, sg, dark, 12) },
      { clip: true, fill: P.hl, op: 0.55, d: limbBand(ja, up, sg, lit, 7, 0.05, 0.72) },
      { clip: true, stroke: P.dp, sw: 1.3, op: 0.5, d: open([U(0.44, 1), U(0.3, 0.4), U(0.18, -0.2), U(0.1, -0.75)]) },
      { clip: true, fill: P.hl, op: 0.45 * litK, d: closed([U(0.03, 0.4), U(0.16, 0.92), U(0.3, 0.6), U(0.2, 0)]) },
      { clip: true, fill: P.hl, op: 0.5 * litK, d: closed([U(0.36, -0.2), U(0.5, -0.78), U(0.68, -0.5), U(0.56, 0.05)]) },
      { clip: true, stroke: P.dp, sw: 1.1, op: 0.45, d: open([U(0.62, -0.95), U(0.72, -0.4), U(0.8, 0.1)]) },
      { clip: true, stroke: P.dp, sw: 1, op: 0.35, d: open([U(0.46, 0.95), U(0.62, 0.62), U(0.8, 0.55)]) },
      { clip: true, stroke: g, sw: 2.2, op: 0.7, d: limbEdge(ja, up, sg, 'outer') }, { clip: true, stroke: g, sw: 1.4, op: 0.35, d: limbEdge(ja, up, sg, 'inner') }
    ];
    var foLay = [
      { clip: true, fill: P.sh, d: limbBand(jf, fo, sg, dark, 9) },
      { clip: true, fill: P.hl, op: 0.5, d: limbBand(jf, fo, sg, lit, 5, 0.08, 0.6) },
      { clip: true, stroke: P.dp, sw: 1.1, op: 0.45, d: open([F(0.05, 0.8), F(0.25, 0.5), F(0.55, -0.1), F(0.8, -0.3)]) },
      { clip: true, fill: P.hl, op: 0.4 * litK, d: closed([F(0.1, 0.7), F(0.3, 0.85), F(0.5, 0.2), F(0.25, 0.1)]) },
      { clip: true, stroke: g, sw: 2, op: 0.7, d: limbEdge(jf, fo, sg, 'outer') }
    ];
    var upId = (o.prefix || 'arm') + '-' + side, foId = (o.forePrefix || 'fore') + '-' + side;
    return [
      { id: upId, parent: o.parent || 'torso', behind: !!o.behind, pivot: J.s, fill: P.sk, d: limb(ja, up, sg), layers: upLay.concat(o.upLayers || []) },
      { id: foId, parent: upId, behind: !o.foreFront, pivot: J.e, fill: P.sk, d: limb(jf, fo, sg, { startRound: 0.6 }), layers: foLay.concat(o.foreLayers || []) }
    ];
  }

  /** Heroic leg on a wide stance: quad sweep and teardrop, kneecap, calf bean, shin; rim light. Returns the part with .J and .st. */
  function heroLeg(P, side, b, o) {
    o = o || {};
    var sg = side === 'l' ? 1 : -1, k = b.legK, g = o.glow || P.rim, hx = b.hip, ax = b.stance;
    var J = [[CX + sg * hx, 430], [CX + sg * (hx + (ax - hx) * 0.52), 598], [CX + sg * ax, 752], [CX + sg * (ax + 6), 791]];
    var st = scaleSt(LEGH, k), lit = sg < 0 ? 'outer' : 'inner', dark = sg < 0 ? 'inner' : 'outer';
    var Q = function (t, f) { return lp(J, st, sg, t, f); }, kn = Q(0.49, 0);
    var lay = [
      { clip: true, fill: P.sh, d: limbBand(J, st, sg, dark, 14) },
      { clip: true, fill: P.hl, op: 0.5, d: limbBand(J, st, sg, lit, 7, 0.08, 0.84) },
      { clip: true, fill: P.hl, op: 0.45, d: closed([Q(0.3, -0.5), Q(0.4, -0.95), Q(0.46, -0.78), Q(0.43, -0.25)]) },
      { clip: true, stroke: P.dp, sw: 1.2, op: 0.45, d: open([Q(0.3, -0.5), Q(0.4, -0.95)]) + ' ' + open([Q(0.06, 0.9), Q(0.24, 0.72), Q(0.43, 0.55)]) + ' ' + open([Q(0.05, -0.1), Q(0.36, 0.1)]) },
      { clip: true, stroke: P.dp, sw: 1.1, op: 0.5, d: open([[kn[0] - 10, kn[1] - 5], [kn[0], kn[1] - 13], [kn[0] + 10, kn[1] - 5]]) + ' ' + open([[kn[0] - 8, kn[1] + 10], [kn[0], kn[1] + 14], [kn[0] + 8, kn[1] + 10]]) },
      { clip: true, stroke: P.dp, sw: 1.1, op: 0.42, d: open([Q(0.56, -0.85), Q(0.64, -0.98), Q(0.73, -0.55)]) + ' ' + open([Q(0.56, 0.9), Q(0.62, 0.99), Q(0.71, 0.65)]) },
      { clip: true, stroke: P.dp, sw: 0.9, op: 0.3, d: open([Q(0.58, 0.15), Q(0.84, 0.1)]) },
      { clip: true, stroke: P.dp, sw: 0.8, op: 0.55, d: [0, 1, 2, 3].map(function (i) { var tx = J[3][0] - sg * 10 + sg * i * 6; return open([[tx, 784], [tx + sg * 0.6, 791]]); }).join(' ') },
      { clip: true, stroke: g, sw: 2.2, op: 0.7, d: limbEdge(J, st, sg, 'outer') }, { clip: true, stroke: g, sw: 1.4, op: 0.35, d: limbEdge(J, st, sg, 'inner') }
    ];
    var part = { id: 'leg-' + side, parent: 'pelvis', behind: true, pivot: J[0], fill: P.sk, d: limb(J, st, sg, { startCap: false, endRound: 0.55 }), layers: lay.concat(o.layers || []) };
    part.J = J; part.st = st;
    return part;
  }

  /** A wind-blown cloth streamer (uttariya, sash end, cloak edge) along a chain, tapering to a point. */
  function streamer(id, parent, chain, w0, C, o) {
    o = o || {};
    var st = chain.map(function (p, i) { var t = i / (chain.length - 1); return [t, w0 * (1 - t * 0.85) * (1 + 0.25 * Math.sin(t * Math.PI * 2)), w0 * (1 - t * 0.85)]; });
    var folds = [-0.45, 0.1, 0.55].map(function (f) { return open(chain.slice(0, -1).map(function (p, i) { return lp(chain, st, 1, i / (chain.length - 1), f); })); }).join(' ');
    return { id: id, parent: parent, behind: o.behind !== false, pivot: chain[0], fill: C.b, d: limb(chain, st, 1, { startRound: 0.4, endRound: 0.3 }),
      layers: [{ clip: true, fill: C.s, d: limbBand(chain, st, 1, 'inner', w0 * 0.9) }, { clip: true, stroke: C.s, sw: 1.1, op: 0.7, d: folds },
        { clip: true, stroke: C.h, sw: 1.4, op: 0.75, d: limbEdge(chain, st, 1, 'outer') }].concat(o.layers || []) };
  }
  /** Locks of hair streaming in the wind: n tapered ribbons from the head's sides, dir -1 (to the viewer's left) or 1. */
  function windLocks(C, dir, o) {
    o = o || {};
    var out = [], n = o.n || 5, len = o.len || 120;
    for (var i = 0; i < n; i++) {
      var y0 = 120 + i * 9, x0 = CX + dir * (34 + i * 2), wv = (i % 2 ? 8 : -6);
      var ch = [[x0, y0], [x0 + dir * len * 0.3, y0 + 30 + wv], [x0 + dir * len * 0.62, y0 + 54 - wv], [x0 + dir * len * (0.86 + i * 0.04), y0 + 70 + i * 6]];
      out.push(limb(ch, [[0, 7, 7], [0.5, 5.5, 5.5], [1, 1.4, 1.4]], 1, { endRound: 0.4 }));
    }
    return out.join(' ');
  }

  // ------------------------------------------------------------------ Rama (heroic)
  /**
   * Rama of the Valmiki Ramayana as a hero: the broad shoulders, deep chest and knee-long arms of
   * Bala 1.10 and Sundara 5.35 pushed to the heroic canon; the pose of the Chola bronzes (leaning on
   * the tall bow with the left hand, an arrow raised in the right, Harvard 1949.47 / V&A IS.10-1955),
   * a tejas aura of sun and rays; the Kodanda lacquered and gilded; an arrow glowing with tejas;
   * hair matted into the jata knot with locks blowing back. opts {tone: 'blue' | 'brown', attire:
   * 'forest' | 'royal'}.
   */
  FIG['rama-human'] = function (opt) {
    var o = opt || {};
    var P = SKIN[o.tone === 'brown' ? 'shyama-brown' : 'shyama-blue'], royal = o.attire === 'royal', b = HERO.warrior, glow = '#FFD98A';
    var cloth = royal ? { b: '#E2A62B', s: '#B97D16', h: '#F5CD6A' } : { b: '#A8743F', s: '#86562B', h: '#C99660' };
    var parts = M.auras.make('tejas', { cx: CX, cy: 150, r: 250 });
    var bark = royal ? null : [
      { clip: true, stroke: '#6E4524', sw: 0.9, op: 0.55, d: [-60, -44, -28, -12, 8, 24, 40, 56, 72].map(function (x, i) { return open([[CX + x, 360 + (i % 3) * 6], [CX + x + 3, 450], [CX + x + (i % 2 ? 5 : -2), 560]]); }).join(' ') },
      { clip: true, stroke: '#D7AE78', sw: 0.8, op: 0.45, d: [-52, -20, 16, 48].map(function (x) { return open([[CX + x, 380], [CX + x + 2, 500]]); }).join(' ') }
    ];
    parts = parts.concat(dhotiPart({ colour: cloth, hem: royal ? 600 : 540, fall: royal ? 676 : 616, wide: 0, texture: bark }));
    parts.push(heroLeg(P, 'r', b, { glow: glow }), heroLeg(P, 'l', b, { glow: glow }));
    // Uttariya, the upper cloth, streaming back in the wind from both shoulders.
    var ut = royal ? { b: '#B8321F', s: '#8A2316', h: '#E2735A' } : { b: '#C99660', s: '#A8743F', h: '#E6C08A' };
    parts.push(streamer('uttariya', 'pelvis', [[CX - 96, 212], [CX - 150, 262], [CX - 200, 290], [CX - 240, 284], [CX - 268, 262]], 21, ut));
    parts.push(streamer('uttariya-2', 'pelvis', [[CX - 70, 372], [CX - 130, 414], [CX - 184, 432], [CX - 228, 418]], 15, ut));
    var s = b.sh;
    parts.push(heroTorso(P, b, { glow: glow, layers: threadLayers().concat(royal ? jewelLayers('haar', P) : []).concat([
      { clip: true, fill: '#5B3A22', d: closed([[CX + s - 40, 196], [CX + s - 26, 198], [CX - b.waist - 4, 360], [CX - b.waist - 18, 352]]) },
      { clip: true, stroke: GOLD.b, sw: 1.1, op: 0.85, d: open([[CX + s - 33, 200], [CX - b.waist - 11, 354]]) }
    ]) }));
    parts = parts.concat(girdlePart(royal ? { style: 'sash', w: 58, colour: { b: '#9E2A22', s: '#76201A', h: '#D9564A' } } : { style: 'cord', w: 58 }));
    parts = parts.concat(M.weapons.place(M.weapons.tuna({ h: 240 }), { id: 'quiver', parent: 'torso', behind: true, at: [CX + 70, 250], angle: 24, scale: 1.15 }));
    // Right arm raised with the arrow; left arm reaching down to the planted bow.
    var JR = armJ(b, 'r', [CX - 142, 214], 'low');
    var JL = armJ(b, 'l', [CX + 100, 432], 'out');
    var fR = fistAt(JR, 12), fL = fistAt(JL, 14);
    parts = parts.concat(heroArms(P, 'r', JR, b, { glow: glow, foreFront: true }), heroArms(P, 'l', JL, b, { glow: glow }));
    if (royal) { armJewels(parts, 'r', JR, { k: b.k, hero: true }); armJewels(parts, 'l', JL, { k: b.k, hero: true }); }
    parts.push(fistPart(P, 'r', fR, { k: 1.25 }));
    parts.push(fistPart(P, 'l', fL, { k: 1.25 }));
    parts = parts.concat(M.weapons.place(M.weapons.shara({ len: 250, glow: true }), { id: 'arrow', parent: 'hand-r', behind: true, at: fR, angle: -4 }));
    parts = parts.concat(M.weapons.place(M.weapons.kodanda(), { id: 'bow', parent: 'hand-l', behind: true, at: [fL[0] + 4, fL[1]], scale: (782 - fL[1]) / 352 }));
    // Hair: long locks blowing back behind the shoulders, the jata knot on the crown.
    var hairC = HAIR.black;
    parts.push({ id: 'hair-back', parent: 'torso', behind: true, pivot: [CX, 160], fill: hairC.b,
      d: closed(R([[30, 128], [46, 140], [56, 176], [60, 210], [50, 222], [38, 196], [26, 160]])) + ' ' + windLocks(hairC, -1, { n: 5, len: 130 }),
      layers: [{ clip: true, stroke: hairC.h, sw: 1, op: 0.6, d: pairOpen([[38, 146], [50, 182], [54, 208]]) }] });
    parts.push(headPart(P, { tilak: 'vaishnava', smile: 0.6, brow: 'level' }));
    var capHalf = [[0, 66], [22, 68], [38, 78], [47, 96], [49, 116], [45, 130], [43, 122], [38, 108], [28, 100], [14, 97], [0, 98]];
    parts.push({ id: 'hair', parent: 'head', pivot: [CX, 110], fill: hairC.b, d: sym(capHalf),
      layers: [
        { clip: true, fill: hairC.h, op: 0.7, d: closed(L([[2, 70], [20, 72], [34, 82], [40, 96], [32, 90], [18, 82], [4, 80]])) },
        { clip: true, stroke: hairC.h, sw: 0.9, op: 0.7, d: [10, 22, 34].map(function (x) { return pairOpen([[2, 96], [x * 0.6, 84], [x, 72]]); }).join(' ') },
        { clip: true, stroke: glow, sw: 1.6, op: 0.6, d: open(R([[22, 68], [38, 78], [47, 96]])) }
      ] });
    if (!royal) parts.push(jataKnot(hairC, { top: 0, bot: 70, w: 30 }));
    else { parts.push(kiritaPart()); parts.push(kundalaPart('r'), kundalaPart('l')); }
    heroHead(parts, b.head, ['hair-back']);
    return { viewBox: [400, 820], parts: parts, headCentre: [CX, 182 - (182 - 128) * b.head],
      meta: meta({ id: 'rama-human', name: 'Rama', tradition: 'indian', heroic: true, emblems: ['great bow (Kodanda)', 'arrow of tejas and quiver', 'jata (tied-up matted hair)', 'dark (shyama) skin', 'Vaishnava tilak', 'tejas aura'],
        check: 'figure-design.md: Rama identity block (heroic); Valmiki 1.1.10 and 5.35 (body), 2.52 (jata), Chola bronzes (bow and raised arrow)' }) };
  };

  // ------------------------------------------------------------------ Hanuman (heroic)
  /**
   * Hanuman as Veera Hanuman: a titan's frame (the mountain-sized hero of Sundara 1.29) with the
   * vanara head, golden fur and a fierce, steady gaze; the great gada resting on his right shoulder,
   * the left fist on his hip, the tail raised in a counter-curve; a blazing agni aura. opts {form:
   * 'veera' (default) | 'dasa' (hands joined, no mace)}. The mace is later tradition.
   */
  FIG['hanuman-human'] = function (opt) {
    var o = opt || {}, dasa = o.form === 'dasa';
    var F = SKIN['vanara-gold'], S = SKIN['vanara-face'], b = HERO.titan, glow = '#FFC46A';
    var parts = M.auras.make('agni', { cx: CX, cy: 250, r: 300 });
    var cloth = { b: '#B7321F', s: '#8A2316', h: '#DE5A3E' };
    parts = parts.concat(dhotiPart({ colour: cloth, hem: 530, fall: 590, wide: 10, texture: [
      { clip: true, fill: GOLD.b, d: closed([[CX - 120, 508], [CX + 120, 508], [CX + 120, 540], [CX - 120, 540]]) },
      { clip: true, stroke: GOLD.s, sw: 1, d: open([[CX - 120, 512], [CX + 120, 512]]) }
    ] }));
    ['r', 'l'].forEach(function (side) {
      var lg = heroLeg(F, side, b, { glow: glow });
      lg.layers.push(furStrokes(lg.J.slice(0, 3), lg.st, side === 'l' ? 1 : -1, F.dp, 24));
      parts.push(lg);
    });
    // Tail: rises behind his left side in a counter-curve to the mace, curling at the tip.
    var tail = [[CX + 30, 420], [CX + 120, 476], [CX + 196, 440], [CX + 226, 330], [CX + 206, 220], [CX + 170, 150], [CX + 182, 84], [CX + 220, 66], [CX + 238, 92], [CX + 222, 112]];
    var tst = tail.map(function (p, i) { return [i / (tail.length - 1), 11 - i * 0.7, 11 - i * 0.7]; });
    parts.push({ id: 'tail', parent: 'pelvis', behind: true, pivot: [CX + 30, 420], fill: F.sk, d: limb(tail, tst, 1, { startCap: false }),
      layers: [{ clip: true, fill: F.sh, d: limbBand(tail, tst, 1, 'outer', 7) }, furStrokes(tail, tst, 1, F.dp, 34), { clip: true, stroke: glow, sw: 2, op: 0.6, d: limbEdge(tail, tst, 1, 'inner') }] });
    parts.push(heroTorso(F, b, { glow: glow, layers: [
      { clip: true, fill: F.hl, op: 0.42, d: sym([[0, 210], [36, 216], [56, 250], [44, 300], [30, 340], [0, 350]]) },
      { clip: true, stroke: F.dp, sw: 0.9, op: 0.4, d: [0, 1, 2, 3, 4, 5, 6, 7, 8].map(function (i) { var y = 222 + i * 14, x = 12 + (i % 3) * 11; return open([[CX - x, y], [CX - x - 3, y + 6]]) + ' ' + open([[CX + x, y], [CX + x + 3, y + 6]]); }).join(' ') }
    ].concat(threadLayers('#D9C38A')).concat([
      { fill: GOLD.b, d: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(function (i) { var a = Math.PI * (0.1 + 0.8 * i / 12); return circle(CX - Math.cos(a) * 40, 196 + Math.sin(a) * 34, 3); }).join(' ') },
      { fill: GOLD.b, d: closed([[CX, 228, 1], [CX + 8, 240], [CX, 252, 1], [CX - 8, 240]]) }, { fill: '#B8321F', d: ellipse(CX, 240, 3, 5) },
      { clip: true, fill: GOLD.b, d: closed([[CX - 90, 316], [CX + 90, 316], [CX + 90, 325], [CX - 90, 325]]) },
      { clip: true, stroke: GOLD.s, sw: 1, d: open([[CX - 90, 320.5], [CX + 90, 320.5]]) }
    ]) }));
    parts = parts.concat(girdlePart({ style: 'belt', colour: { b: '#8A2316', s: '#64180E', h: '#C9962E' }, w: 68, knot: -1 }));
    var s = b.sh, JR, JL;
    if (dasa) {
      JR = armJ(b, 'r', [CX - 20, 290], 'out');
      JL = armJ(b, 'l', [CX + 20, 290], 'out');
    } else {
      JR = armJ(b, 'r', [CX - 66, 330], 'out');
      JL = armJ(b, 'l', [CX + 84, 376], 'out');
    }
    var arms = heroArms(F, 'r', JR, b, { glow: glow, foreFront: true }).concat(heroArms(F, 'l', JL, b, { glow: glow, foreFront: true }));
    arms.forEach(function (ap) {
      var side = ap.id.slice(-1) === 'l' ? 1 : -1, JJ = side > 0 ? JL : JR, upper = ap.id.indexOf('arm') === 0;
      ap.layers.push(furStrokes(upper ? [JJ.s, JJ.e] : [JJ.e, JJ.w], scaleSt(upper ? ARMH.upper : ARMH.fore, b.k), side, F.dp, 12));
    });
    parts = parts.concat(arms);
    armJewels(parts, 'r', JR, { k: b.k, hero: true });
    armJewels(parts, 'l', JL, { k: b.k, hero: true });
    if (dasa) {
      parts.push({ id: 'hand-r', parent: 'fore-r', pivot: JR.w, fill: F.sk, d: closed([[CX - 1, 232, 1], [CX - 9, 242], [CX - 16, 268], [CX - 21, 296], [CX - 9, 306], [CX - 1, 302]]),
        layers: [{ clip: true, fill: F.hl, op: 0.6, d: closed([[CX - 1, 222], [CX - 7, 222], [CX - 12, 302], [CX - 1, 302]]) }] });
      parts.push({ id: 'hand-l', parent: 'fore-l', pivot: JL.w, fill: F.sk, d: closed([[CX + 1, 232, 1], [CX + 9, 242], [CX + 16, 268], [CX + 21, 296], [CX + 9, 306], [CX + 1, 302]]),
        layers: [{ clip: true, fill: F.sh, d: closed([[CX + 1, 222], [CX + 22, 222], [CX + 24, 302], [CX + 1, 302]]) }] });
    } else {
      var gR = fistAt(JR, 12), gL = fistAt(JL, 12);
      parts.push(fistPart(F, 'r', gR, { k: 1.4 }));
      parts.push(fistPart(F, 'l', gL, { k: 1.4 }));
      parts = parts.concat(M.weapons.place(M.weapons.gada({ shaft: 200, r: 58 }), { id: 'gada', parent: 'hand-r', behind: true, at: gR, angle: -22, scale: 0.95 }));
    }
    // Head: the ruff, the vanara head with a fierce gaze, curly hair, a crown and earrings.
    var ruff = tufts(CX, 178, 76, 70, 15, 0.14, Math.PI * 0.02, Math.PI * 0.98);
    parts.push({ id: 'ruff', parent: 'torso', pivot: [CX, 180], fill: F.sh, d: closed([[CX + 74, 120]].concat(ruff).concat([[CX - 74, 120]])),
      layers: [{ clip: true, fill: F.dp, op: 0.4, d: closed(R([[20, 196], [70, 160], [76, 200], [30, 244]])) }, { clip: true, stroke: glow, sw: 2, op: 0.5, d: open(L([[70, 150], [76, 190], [60, 230]])) }] });
    parts.push(vanaraHead(F, S, { fierce: true }));
    parts.push({ id: 'hair', parent: 'head', pivot: [CX, 100], fill: F.dp,
      d: closed(tufts(CX, 100, 48, 26, 9, 0.2, Math.PI, Math.PI * 2).concat([[CX + 44, 106], [CX + 30, 98], [CX, 94], [CX - 30, 98], [CX - 44, 106]])),
      layers: [{ clip: true, fill: F.sh, op: 0.6, d: closed(L([[0, 70], [40, 80], [44, 100], [10, 90]])) }] });
    var hk = kiritaPart({ base: 92, top: 30, wB: 42, wT: 32 });
    parts.push(hk);
    ['r', 'l'].forEach(function (side) {
      var sg = side === 'l' ? 1 : -1, x = CX + sg * 62, y = 136;
      parts.push({ id: 'kundala-' + side, parent: 'head', pivot: [x, y], fill: GOLD.b, rule: 'evenodd', d: ellipse(x, y + 9, 7.5, 9.5) + ' ' + ellipse(x, y + 9, 4.4, 6.2) });
    });
    heroHead(parts, b.head, ['ruff']);
    return { viewBox: [400, 820], parts: parts, headCentre: [CX, 182 - (182 - 140) * b.head],
      meta: meta({ id: 'hanuman-human', name: 'Hanuman', tradition: 'indian', heroic: true, emblems: dasa ? ['monkey face and tail', 'hands joined (anjali)', 'golden fur', 'agni aura'] : ['monkey face and tail', 'gada on the shoulder (later tradition)', 'fist on the hip', 'golden fur', 'agni aura'],
        check: 'figure-design.md: Hanuman identity block (heroic); Sundara 5.1.29 (mountain-sized), 5.31.19 (sun-like), Kishkindha 4.66.23 (jaw); gada on the shoulder from popular art' }) };
  };

  // ------------------------------------------------------------------ Shiva (heroic)
  /**
   * Shiva as the great ascetic-warrior: an ash-pale, lean and powerful body with the blue throat,
   * three eyes open in calm power, the jata-makuta with the crescent and the Ganga, matted locks
   * flying out like Nataraja's; the cobra; rudraksha; the tiger skin; the trishula planted in the left
   * hand with the damaru tied beneath its prongs; the right hand raised, fear not; a cosmic aura of
   * night and a ring of thirteen flames (the Chola prabhamandala).
   */
  FIG['shiva-human'] = function () {
    var P = SKIN.ash, b = HERO.ascetic, glow = '#FFD166', hairC = { b: '#3B2E2A', s: '#241B18', h: '#6A5850' };
    var tiger = { b: '#D9922E', s: '#B4731E', h: '#EDB55A' };
    var parts = M.auras.make('cosmic', { cx: CX, cy: 150, r: 236 });
    var stripes = [];
    for (var i = 0; i < 10; i++) {
      var x = -84 + i * 18, y0 = 360 + (i % 3) * 22;
      stripes.push(closed([[CX + x, y0], [CX + x + 10, y0 + 14], [CX + x + 4, y0 + 34, 1], [CX + x + 1, y0 + 16]]));
      stripes.push(closed([[CX + x + 6, y0 + 70], [CX + x + 16, y0 + 86], [CX + x + 9, y0 + 108, 1], [CX + x + 6, y0 + 88]]));
      stripes.push(closed([[CX + x - 2, y0 + 150], [CX + x + 8, y0 + 162], [CX + x + 2, y0 + 184, 1], [CX + x - 1, y0 + 166]]));
    }
    parts = parts.concat(dhotiPart({ colour: tiger, hem: 566, fall: 620, wide: 0, texture: [{ clip: true, fill: '#2B1D14', op: 0.85, d: stripes.join(' ') }] }));
    parts.push(heroLeg(P, 'r', b, { glow: glow }), heroLeg(P, 'l', b, { glow: glow }));
    parts.push({ id: 'paw', parent: 'pelvis', pivot: [CX - 30, 380], fill: tiger.b,
      d: closed([[CX - 40, 380], [CX - 22, 380], [CX - 20, 420], [CX - 12, 436], [CX - 14, 448], [CX - 26, 452], [CX - 40, 450], [CX - 46, 440], [CX - 40, 420]]),
      layers: [{ clip: true, fill: '#2B1D14', op: 0.85, d: closed([[CX - 42, 396], [CX - 22, 392], [CX - 26, 400], [CX - 42, 406]]) }, { clip: true, fill: tiger.h, op: 0.7, d: ellipse(CX - 28, 440, 12, 8) },
        { stroke: '#F4EEDF', sw: 1.3, d: open([[CX - 40, 449], [CX - 41, 457]]) + ' ' + open([[CX - 32, 452], [CX - 32, 460]]) + ' ' + open([[CX - 24, 451], [CX - 23, 459]]) + ' ' + open([[CX - 16, 446], [CX - 14, 453]]) }] });
    var beads = [], glints = [];
    for (var j = 0; j <= 24; j++) { var a = Math.PI * (0.04 + 0.92 * j / 24); beads.push(circle(CX - Math.cos(a) * 50, 196 + Math.sin(a) * 90, 3.2)); glints.push(circle(CX - Math.cos(a) * 50 - 1, 195 + Math.sin(a) * 90, 1.1)); }
    for (var j2 = 0; j2 <= 16; j2++) { var a2 = Math.PI * (0.08 + 0.84 * j2 / 16); beads.push(circle(CX - Math.cos(a2) * 36, 198 + Math.sin(a2) * 44, 2.8)); glints.push(circle(CX - Math.cos(a2) * 36 - 0.8, 197 + Math.sin(a2) * 44, 1)); }
    parts.push(heroTorso(P, b, { glow: glow, layers: [
      { clip: true, fill: '#3E5E8E', op: 0.8, d: sym([[0, 166], [b.neck - 2, 166], [b.neck, 180], [12, 190], [0, 192]]) }
    ].concat(threadLayers('#EFE4C8')).concat([{ fill: '#6B3A22', d: beads.join(' ') }, { fill: '#D9A25A', op: 0.6, d: glints.join(' ') }]) }));
    parts = parts.concat(girdlePart({ style: 'cord', colour: { b: '#8C5A2A', s: '#5E3B1A', h: '#C08A4A' }, w: 56, knot: 1 }));
    // Matted locks flying out on both sides like Nataraja's, behind the shoulders.
    var locks = [];
    for (var lk = 0; lk < 5; lk++) {
      [-1, 1].forEach(function (sx) {
        // Each lock leaves the head, waves twice and ends in a curl, fanning from level to downswept.
        var ang = (-0.42 + lk * 0.24), y0 = 116 + lk * 9, x0 = CX + sx * 36, L1 = 128 + (lk % 2) * 22;
        var dx = Math.cos(ang) * sx, dy = Math.sin(ang), nx = -dy * sx, ny = Math.cos(ang);
        var pt = function (t, wv) { return [x0 + dx * L1 * t + nx * wv, y0 + dy * L1 * t + ny * wv]; };
        locks.push(limb([pt(0, 0), pt(0.25, 9), pt(0.5, -8), pt(0.75, 8), pt(0.92, -2), pt(1, -12)], [[0, 7.5, 7.5], [0.5, 6, 6], [0.85, 3.6, 3.6], [1, 1.2, 1.2]], 1, { endRound: 0.4 }));
      });
    }
    parts.push({ id: 'hair-back', parent: 'torso', behind: true, pivot: [CX, 150], fill: hairC.b, d: locks.join(' '),
      layers: [{ clip: true, stroke: hairC.h, sw: 1, op: 0.6, d: pairOpen([[44, 130], [90, 120], [140, 110]]) + ' ' + pairOpen([[44, 150], [100, 160], [150, 176]]) }, { clip: true, fill: '#C9962E', op: 0.8, d: [0.4, 0.7].map(function (q) { return circle(CX - 36 - 100 * q, 140 - 10 * q, 3) + ' ' + circle(CX + 36 + 100 * q, 140 - 10 * q, 3); }).join(' ') }] });
    var s = b.sh;
    var JR = armJ(b, 'r', [CX - 128, 216], 'low');
    var JL = armJ(b, 'l', [CX + 98, 432], 'out');
    var tL = fistAt(JL, 14);
    var arms = heroArms(P, 'r', JR, b, { glow: glow, foreFront: true }).concat(heroArms(P, 'l', JL, b, { glow: glow }));
    arms.forEach(function (ap) {
      var side = ap.id.slice(-1) === 'l' ? 1 : -1, JJ = side > 0 ? JL : JR, upper = ap.id.indexOf('arm') === 0;
      var ch = upper ? [JJ.s, JJ.e] : [JJ.e, JJ.w], t = upper ? 0.32 : 0.86, aa = along(ch, t), n = [-aa.d[1], aa.d[0]], bb = [];
      for (var q = -2; q <= 2; q++) bb.push(circle(aa.p[0] + n[0] * q * 6, aa.p[1] + n[1] * q * 6, 3.1));
      ap.layers.push({ clip: true, fill: '#6B3A22', d: bb.join(' ') });
    });
    parts = parts.concat(arms);
    parts.push(palmPart(P, 'r', JR.w, { k: 1.25 }));
    parts.push(fistPart(P, 'l', tL, { k: 1.25 }));
    parts = parts.concat(M.weapons.place(M.weapons.trishula({ shaft: 300, butt: (788 - tL[1]) / 0.94 }), { id: 'trishula', parent: 'hand-l', behind: true, at: [tL[0] + 2, tL[1]], scale: 0.94 }));
    // The damaru hangs from the trishula: its position is in the trishula's own (origin) coordinates.
    parts = parts.concat(M.weapons.place(M.weapons.damaru({ size: 1.2 }), { id: 'damaru', parent: 'trishula', at: [16, -214] }));
    var coil = [[CX - 32, 198], [CX - 14, 214], [CX + 14, 214], [CX + 36, 198], [CX + 50, 180], [CX + 60, 160], [CX + 64, 140]];
    var cst = coil.map(function (p, ii) { return [ii / (coil.length - 1), 5.8, 5.8]; });
    parts.push(headPart(P, { tilak: 'tripundra', thirdEye: true, eyes: 'open', brow: 'level', smile: 0.4, lobes: true }));
    parts.push({ id: 'cobra', parent: 'torso', pivot: [CX, 200], fill: '#3F6B4A', d: limb(coil, cst, 1, { endCap: false }) + ' ' + closed([[CX + 52, 142], [CX + 58, 116], [CX + 66, 104], [CX + 78, 116], [CX + 82, 142], [CX + 72, 154], [CX + 58, 154]]),
      layers: [{ clip: true, fill: '#2C4E35', d: closed([[CX + 56, 118], [CX + 66, 106], [CX + 66, 152], [CX + 58, 152]]) }, { fill: '#E9D9A8', op: 0.8, d: closed([[CX + 62, 126], [CX + 66, 118], [CX + 71, 126], [CX + 69, 142], [CX + 64, 142]]) },
        { fill: INK, d: circle(CX + 62, 114, 1.5) + ' ' + circle(CX + 71, 114, 1.5) }, { clip: true, stroke: '#7FA07E', sw: 0.9, op: 0.7, d: open(coil) }] });
    parts.push({ id: 'hair', parent: 'head', pivot: [CX, 110], fill: hairC.b, d: sym([[0, 70], [24, 72], [40, 82], [48, 100], [49, 118], [45, 132], [43, 120], [36, 106], [24, 100], [12, 99], [0, 100]]),
      layers: [{ clip: true, stroke: hairC.h, sw: 0.9, op: 0.7, d: [10, 22, 34].map(function (x) { return pairOpen([[2, 99], [x * 0.6, 86], [x, 74]]); }).join(' ') }] });
    var jk = jataKnot(hairC, { top: -6, bot: 80, w: 36, tie: '#C9962E' });
    jk.layers.push({ fill: GOLD.b, d: [-26, -13, 0, 13, 26].map(function (x) { return circle(CX + x, 76, 2.4); }).join(' ') });
    parts.push(jk);
    parts.push({ id: 'moon', parent: 'jata', pivot: [CX + 32, 26], fill: '#F4EBCB', d: closed([[CX + 20, 4, 1], [CX + 42, 16], [CX + 50, 38], [CX + 36, 58, 1], [CX + 40, 38], [CX + 35, 20]]),
      layers: [{ stroke: '#C9B98A', sw: 0.9, d: open([[CX + 22, 7], [CX + 38, 22], [CX + 39, 52]]) }, { fill: { radial: [[0, '#FFFBEA', 0.8], [1, '#FFFBEA', 0]], cx: CX + 38, cy: 30, r: 30 }, d: circle(CX + 38, 30, 30) }] });
    parts.push({ id: 'ganga', parent: 'jata', pivot: [CX - 6, 0], fill: '#9CC3DA',
      d: closed([[CX - 2, 6], [CX + 6, 0], [CX - 4, -8], [CX - 20, -10], [CX - 38, -2], [CX - 52, 14], [CX - 60, 34], [CX - 50, 32], [CX - 40, 16], [CX - 28, 6], [CX - 14, 2], [CX - 6, 4]]),
      layers: [{ stroke: '#F4FAFC', sw: 1.1, op: 0.9, d: open([[CX + 2, 0], [CX - 12, -4], [CX - 30, 0], [CX - 46, 14], [CX - 54, 30]]) }] });
    parts.push(kundalaPart('r', { y: 154, s: 1.15 }), kundalaPart('l', { y: 156, s: 1.15, kind: 'disc' }));
    heroHead(parts, b.head, []);
    return { viewBox: [400, 820], parts: parts, headCentre: [CX, 182 - (182 - 120) * b.head],
      meta: meta({ id: 'shiva-human', name: 'Shiva', tradition: 'indian', heroic: true, emblems: ['trishula and damaru', 'crescent moon and Ganga in the jata', 'blue throat', 'third eye', 'cobra', 'tiger skin', 'ring of flames'],
        check: 'figure-design.md: Shiva identity block (heroic); Shiva Purana 1.20.52, Bhagavata 8.7.43, Chola Nataraja (13 flames, flying locks)' }) };
  };

  // ------------------------------------------------------------------ Athena (heroic)
  /**
   * Athena Promachos, "who fights in the front line": the spear raised overhead ready to strike (the
   * Acropolis Promachos statuettes), the great round shield forward on her left arm with the
   * gorgoneion, the aegis with its snakes, a tall-crested Attic helmet, the peplos blown back by the
   * wind, grey-blue eyes and a level, fearless gaze; athletic and strong, never sexualised; radiant light.
   */
  FIG['athena-human'] = function () {
    var P = SKIN.ivory, b = HERO.goddess, glow = '#FFE9B0';
    var robe = { b: '#EDE3CF', s: '#CDBE9F', h: '#FBF6EA' }, border = '#A8432F';
    var parts = M.auras.make('radiant', { cx: CX, cy: 170, r: 260 });
    var skirt = closed([[CX - 50, 328], [CX + 50, 328], [CX + 66, 380], [CX + 80, 480], [CX + 92, 600], [CX + 100, 720], [CX + 96, 780], [CX + 50, 786], [CX, 782], [CX - 60, 788], [CX - 120, 782], [CX - 150, 762, 1], [CX - 118, 700], [CX - 92, 600], [CX - 74, 480], [CX - 62, 380]]);
    parts.push({ id: 'pelvis', pivot: [CX, 340], fill: robe.b, d: skirt, layers: [
      { clip: true, fill: robe.s, d: closed([[CX + 24, 330], [CX + 120, 330], [CX + 120, 800], [CX + 44, 800], [CX + 52, 620], [CX + 40, 480]]) },
      { clip: true, fill: robe.h, op: 0.7, d: closed([[CX - 30, 420], [CX - 10, 420], [CX - 30, 600], [CX - 70, 780], [CX - 96, 780], [CX - 60, 600]]) },
      { clip: true, stroke: robe.s, sw: 1.6, d: [-64, -44, -24, -4, 16, 36, 56, 76].map(function (x, i) { return open([[CX + x * 0.7, 420], [CX + x * 0.95 - 10, 600], [CX + x * 1.1 - 30 - (x < 0 ? 20 : 0), 776]]); }).join(' ') },
      { clip: true, fill: border, d: closed([[CX - 160, 756], [CX + 110, 760], [CX + 110, 800], [CX - 160, 800]]) },
      { clip: true, stroke: '#E9C77A', sw: 1, d: meander(CX - 140, 773, 236) }
    ] });
    parts.push(heroLeg(P, 'r', b, { glow: glow }), heroLeg(P, 'l', b, { glow: glow }));
    parts.push(streamer('himation', 'pelvis', [[CX - 60, 210], [CX - 120, 280], [CX - 170, 330], [CX - 214, 344], [CX - 250, 330]], 16, { b: '#A8432F', s: '#7E2E20', h: '#D9725C' }));
    parts.push(heroTorso(P, b, { covered: true, glow: glow }));
    var over = closed([[CX - 58, 204], [CX, 214], [CX + 58, 204], [CX + 72, 222], [CX + 70, 262], [CX + 64, 300], [CX + 72, 360], [CX + 84, 410], [CX + 60, 420], [CX + 30, 410], [CX, 418], [CX - 40, 412], [CX - 86, 420], [CX - 110, 404, 1], [CX - 80, 360], [CX - 66, 300], [CX - 70, 262], [CX - 72, 222]]);
    parts.push({ id: 'peplos', parent: 'torso', pivot: [CX, 300], fill: robe.b, d: over, layers: [
      { clip: true, fill: robe.s, d: closed([[CX + 20, 200], [CX + 90, 200], [CX + 90, 430], [CX + 40, 430], [CX + 44, 330], [CX + 34, 250]]) },
      { clip: true, stroke: robe.s, sw: 1.4, d: [-50, -30, -10, 10, 30, 50].map(function (x) { return open([[CX + x * 0.7, 300], [CX + x - 4, 360], [CX + x * 1.2 - 12, 414]]); }).join(' ') },
      { clip: true, fill: border, d: closed([[CX - 120, 398], [CX + 90, 398], [CX + 90, 424], [CX - 120, 424]]) },
      { clip: true, stroke: '#E9C77A', sw: 1, d: meander(CX - 100, 410, 180) }
    ] });
    parts.push({ id: 'belt', parent: 'peplos', pivot: [CX, 334], fill: '#4F7A55', d: closed([[CX - 58, 328], [CX + 58, 328], [CX + 59, 338], [CX - 59, 338]]) + ' ' + ellipse(CX, 333, 9, 7),
      layers: [{ clip: true, stroke: '#2E5236', sw: 1, d: open([[CX - 58, 333], [CX - 30, 330], [CX - 10, 336], [CX + 10, 330], [CX + 30, 336], [CX + 58, 333]]) }] });
    var aeg = sym([[0, 198], [28, 194], [56, 198], [76, 214], [80, 238], [66, 258], [44, 270], [24, 282], [0, 288]]);
    var scales = [];
    for (var r = 0; r < 6; r++) for (var c = -7; c <= 7; c++) scales.push(open([[CX + c * 11 - 5 + (r % 2) * 5, 206 + r * 12], [CX + c * 11 + (r % 2) * 5, 211 + r * 12], [CX + c * 11 + 5 + (r % 2) * 5, 206 + r * 12]]));
    var fringe = [];
    for (var s2 = 0; s2 <= 12; s2++) { var tt = s2 / 12, px = lerp(-74, 74, tt), py = 252 + 34 * Math.sin(Math.PI * tt) - (Math.abs(px) > 54 ? 18 : 0); fringe.push(open([[CX + px, py], [CX + px - 3, py + 7], [CX + px + 2, py + 13], [CX + px - 1, py + 19]])); }
    parts.push({ id: 'aegis', parent: 'torso', pivot: [CX, 230], fill: '#C8A24C', d: aeg, layers: [
      { clip: true, fill: '#A6802E', d: closed(R([[16, 190], [90, 190], [90, 300], [10, 300], [30, 240]])) },
      { clip: true, stroke: '#8E6A22', sw: 0.9, op: 0.8, d: scales.join(' ') },
      { stroke: '#3F6B4A', sw: 2.4, d: fringe.join(' ') },
      { fill: '#E8CFA8', d: circle(CX, 246, 15) },
      { stroke: '#3F6B4A', sw: 1.7, d: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map(function (i) { var a = Math.PI * 2 * i / 10; return open([[CX + Math.cos(a) * 15, 246 + Math.sin(a) * 15], [CX + Math.cos(a + 0.2) * 21, 246 + Math.sin(a + 0.2) * 21]]); }).join(' ') },
      { fill: INK, d: ellipse(CX - 5, 243, 2, 2.4) + ' ' + ellipse(CX + 5, 243, 2, 2.4) + ' ' + ellipse(CX, 253, 4, 2.2) },
      { stroke: '#8E6A22', sw: 1, d: circle(CX, 246, 15) },
      { clip: true, stroke: glow, sw: 2, op: 0.7, d: open(L([[56, 198], [76, 214], [80, 238]])) }
    ] });
    // Right arm raised, the spear level overhead; left arm forward behind the great shield.
    var s = b.sh;
    var JR = armJ(b, 'r', [CX - 112, 92], 'out');
    var JL = armJ(b, 'l', [CX + 82, 434], 'out');
    var aR = fistAt(JR, 10), aL = fistAt(JL, 10);
    parts = parts.concat(heroArms(P, 'r', JR, b, { glow: glow, foreFront: true }), heroArms(P, 'l', JL, b, { glow: glow, foreFront: true }));
    armJewels(parts, 'r', JR, { k: b.k, hero: true });
    parts.push(fistPart(P, 'r', aR, { k: 1.05 }));
    parts.push(fistPart(P, 'l', aL, { k: 1.05 }));
    parts = parts.concat(M.weapons.place(M.weapons.dory({ up: 230, down: 110 }), { id: 'spear', parent: 'hand-r', behind: true, at: aR, angle: 84, scale: 0.86 }));
    parts = parts.concat(M.weapons.place(M.weapons.aspis({ r: 92 }), { id: 'shield', parent: 'hand-l', at: [aL[0] + 22, aL[1] + 8] }));
    // Hair flowing back under the helmet; head; the Attic helmet with a tall crest.
    var hairC = { b: '#4A3122', s: '#33211A', h: '#7A5638' };
    parts.push({ id: 'hair-back', parent: 'torso', behind: true, pivot: [CX, 170], fill: hairC.b,
      d: closed(R([[28, 120], [44, 140], [50, 190], [44, 232], [34, 236], [34, 190], [24, 150]])) + ' ' + windLocks(hairC, -1, { n: 6, len: 120 }) });
    parts.push(headPart(P, { shape: 'female', smile: 0, iris: '#56788A', browColour: '#4A3122', brow: 'level' }));
    parts.push({ id: 'hair', parent: 'head', pivot: [CX, 110], fill: hairC.b,
      d: sym([[0, 98], [10, 100], [22, 104], [34, 112], [40, 124], [44, 140], [40, 150], [36, 136], [28, 120], [16, 110], [4, 106], [0, 106]]),
      layers: [{ clip: true, stroke: hairC.h, sw: 1, op: 0.8, d: pairOpen([[4, 103], [18, 108], [30, 118], [38, 136]]) + ' ' + pairOpen([[8, 100], [24, 104], [36, 114], [42, 130]]) }] });
    var bronze = { b: '#C49A45', s: '#94702A', h: '#ECCB7E' };
    parts.push({ id: 'helmet', parent: 'head', pivot: [CX, 100], fill: bronze.b,
      d: sym([[0, 48], [26, 51], [42, 62], [50, 82], [50, 104], [42, 106], [30, 100], [14, 98], [0, 100]]) + ' ' + pair([[44, 86], [60, 78], [66, 92], [58, 104], [44, 104]]),
      layers: [{ clip: true, fill: bronze.s, d: closed(R([[14, 38], [60, 58], [66, 110], [30, 104], [26, 70]])) }, { clip: true, fill: bronze.h, op: 0.7, d: closed(L([[6, 52], [30, 56], [42, 70], [34, 72], [16, 60]])) },
        { clip: true, stroke: bronze.s, sw: 2, d: open([[CX - 50, 94], [CX - 30, 90], [CX, 88], [CX + 30, 90], [CX + 50, 94]]) },
        { stroke: '#E9C77A', sw: 1, d: open([[CX - 30, 78], [CX - 12, 70], [CX, 72], [CX + 12, 70], [CX + 30, 78]]) }, { fill: GOLD.b, d: closed([[CX - 9, 66], [CX, 58, 1], [CX + 9, 66], [CX, 74]]) }] });
    // The great crest sweeps back and up, blown by the wind.
    var crest = closed([[CX - 14, 58], [CX - 8, 22], [CX + 4, -8], [CX + 26, -28], [CX + 56, -34], [CX + 86, -26], [CX + 106, -6], [CX + 112, 22, 1], [CX + 92, 4], [CX + 66, -8], [CX + 40, -6], [CX + 22, 12], [CX + 14, 58]]);
    parts.push({ id: 'crest', parent: 'helmet', pivot: [CX, 56], fill: '#A8432F', d: crest,
      layers: [{ clip: true, fill: '#7E2E20', d: closed([[CX, 60], [CX + 30, -10], [CX + 120, -10], [CX + 120, 40]]) }, { clip: true, stroke: '#D9725C', sw: 1, op: 0.8, d: [0, 1, 2, 3, 4].map(function (i) { return open([[CX - 6 + i * 4, 56], [CX + 10 + i * 10, -10 - i * 3], [CX + 40 + i * 14, -22 + i * 2]]); }).join(' ') },
        { fill: bronze.b, d: closed([[CX - 16, 64], [CX + 16, 64], [CX + 12, 46], [CX - 12, 46]]) }] });
    heroHead(parts, b.head, ['hair-back']);
    return { viewBox: [400, 820], parts: parts, headCentre: [CX, 182 - (182 - 118) * b.head],
      meta: meta({ id: 'athena-human', name: 'Athena', tradition: 'greek', heroic: true, emblems: ['spear raised (Promachos)', 'shield with the gorgoneion', 'aegis', 'crested Attic helmet', 'peplos'],
        check: 'figure-design.md: Athena identity block (heroic); Promachos statuettes (Acropolis Museum), Pausanias 1.24.5-7, Iliad 5; the radiant light is artistic licence' }) };
  };

  // ------------------------------------------------------------------ Odin (heroic)
  /** Raven with spread wings in flight, facing dir. */
  function ravenFlying(x, y, s, dir) {
    var k = dir || 1, X = function (dx) { return x + dx * s * k; }, Y = function (dy) { return y + dy * s; };
    var body = closed([[X(-24), Y(4)], [X(-6), Y(-6)], [X(14), Y(-8)], [X(26), Y(-14)], [X(36), Y(-12), 1], [X(44), Y(-8), 1], [X(32), Y(-4)], [X(16), Y(6)], [X(-4), Y(10)], [X(-26), Y(16), 1], [X(-40), Y(22), 1], [X(-30), Y(8)]]);
    var wingUp = closed([[X(-6), Y(-4)], [X(-20), Y(-34)], [X(-30), Y(-62)], [X(-14), Y(-54)], [X(-4), Y(-60)], [X(6), Y(-48)], [X(16), Y(-50)], [X(14), Y(-26)], [X(8), Y(-6)]]);
    var wingDn = closed([[X(-2), Y(6)], [X(-22), Y(28)], [X(-46), Y(42)], [X(-30), Y(44)], [X(-24), Y(52)], [X(-8), Y(38)], [X(8), Y(30)], [X(10), Y(8)]]);
    return body + ' ' + wingUp + ' ' + wingDn;
  }

  /**
   * Odin the Allfather as a war-king and wanderer: a huge, old, broad-shouldered warrior (Volsunga
   * saga 3) with a long grey beard blown by the wind, the broad hat, one eye given at Mimir's well and
   * the other burning (Baleyg, "flaming-eyed"); the dark-blue hooded mantle and a great cloak spread by
   * the storm; Gungnir planted, its blade lit cold; Draupnir; Huginn on his shoulder and Muninn
   * flying to his raised hand; storm-light behind (no halo: the Norse sources give none).
   */
  FIG['odin-human'] = function () {
    var P = SKIN.weathered, b = HERO.elder, glow = '#DCE6F0';
    var tunic = { sk: '#7D6A52', sh: '#645440', dp: '#463A2C', hl: '#9A876C', rim: glow };
    var breeches = { sk: '#CDBF9F', sh: '#AE9F80', dp: '#7E7158', hl: '#E2D6BA', rim: glow };
    var cloak = { b: '#2F4468', s: '#22324E', h: '#46608A' };
    var parts = M.auras.make('storm', { cx: CX, cy: 220, r: 300 });
    var skirt = sym([[0, 334], [60, 332], [74, 380], [86, 450], [90, 520], [92, 590], [60, 600], [28, 594], [0, 600]]);
    parts.push({ id: 'pelvis', pivot: [CX, 340], fill: tunic.sk, d: skirt, layers: [
      { clip: true, fill: tunic.sh, d: closed(R([[24, 330], [100, 330], [100, 610], [44, 610], [50, 500], [40, 400]])) },
      { clip: true, stroke: tunic.dp, sw: 1.2, op: 0.6, d: [-50, -24, 2, 28, 54].map(function (x) { return open([[CX + x * 0.8, 400], [CX + x, 500], [CX + x * 1.1, 592]]); }).join(' ') },
      { clip: true, fill: '#8C3B2A', d: closed([[CX - 100, 576], [CX + 100, 576], [CX + 100, 602], [CX - 100, 602]]) },
      { clip: true, stroke: GOLD.b, sw: 1.2, d: open([[CX - 100, 580], [CX + 100, 580]]) }
    ] });
    // The great cloak, spread by the storm wind toward the viewer's left.
    var cloakD = closed([[CX - 60, 196], [CX + 60, 196], [CX + 120, 230], [CX + 150, 360], [CX + 168, 560], [CX + 176, 770], [CX + 120, 790], [CX + 60, 776], [CX, 790], [CX - 80, 780], [CX - 160, 792], [CX - 230, 760, 1], [CX - 214, 700], [CX - 250, 640, 1], [CX - 210, 590], [CX - 220, 480], [CX - 170, 340], [CX - 120, 230]]);
    parts.push({ id: 'cloak', parent: 'pelvis', behind: true, pivot: [CX, 210], fill: cloak.b, d: cloakD,
      layers: [{ clip: true, fill: cloak.s, d: closed([[CX + 40, 190], [CX + 200, 190], [CX + 200, 800], [CX + 70, 800], [CX + 100, 500], [CX + 80, 300]]) },
        { clip: true, fill: cloak.h, op: 0.6, d: closed([[CX - 130, 240], [CX - 110, 240], [CX - 150, 500], [CX - 200, 700], [CX - 214, 690], [CX - 180, 480]]) },
        { clip: true, stroke: cloak.s, sw: 1.6, d: [-180, -140, -100, 100, 140].map(function (x) { return open([[CX + x * 0.6, 300], [CX + x * 0.9, 560], [CX + x * 1.05, 770]]); }).join(' ') },
        { clip: true, stroke: glow, sw: 2.4, op: 0.6, d: open([[CX - 120, 230], [CX - 170, 340], [CX - 220, 480], [CX - 210, 590]]) }] });
    ['r', 'l'].forEach(function (side) {
      var lg = heroLeg(breeches, side, b, { glow: glow }), x = lg.J[1][0];
      lg.layers.push({ clip: true, stroke: '#6E5A40', sw: 2.2, d: [0, 1, 2, 3, 4, 5, 6].map(function (j) { var y = 612 + j * 20; return open([[x - 34, y], [x + 34, y + 14]]); }).join(' ') });
      lg.layers.push({ clip: true, fill: '#5A3E26', d: closed([[x - 50, 748], [x + 60, 748], [x + 60, 810], [x - 50, 810]]) });
      parts.push(lg);
    });
    parts.push(heroTorso(tunic, b, { covered: true, glow: glow, layers: [
      { clip: true, stroke: tunic.dp, sw: 1, op: 0.5, d: open([[CX - 30, 206], [CX, 236], [CX + 30, 206]]) + ' ' + open([[CX - 44, 260], [CX - 34, 330]]) + ' ' + open([[CX + 44, 260], [CX + 34, 330]]) }
    ] }));
    parts = parts.concat(girdlePart({ style: 'belt', colour: { b: '#4E3622', s: '#38261A', h: '#C9962E' }, w: 64, ends: false }));
    parts.push({ id: 'buckle', parent: 'girdle', pivot: [CX, 356], fill: GOLD.b, rule: 'evenodd', d: closed([[CX - 10, 342], [CX + 10, 342], [CX + 10, 372], [CX - 10, 372]]) + ' ' + closed([[CX - 5, 347], [CX + 5, 347], [CX + 5, 367], [CX - 5, 367]]) });
    var s = b.sh;
    parts.push({ id: 'mantle', parent: 'torso', pivot: [CX, 210], fill: cloak.b,
      d: sym([[0, 166], [34, 168], [70, 184], [s - 6, 206], [s + 8, 238], [s + 2, 266], [s - 16, 256], [70, 238], [44, 228], [24, 236], [12, 264], [0, 272]]),
      layers: [{ clip: true, fill: cloak.s, d: closed(R([[20, 160], [s + 20, 190], [s + 20, 280], [60, 240], [40, 210]])) }, { clip: true, fill: cloak.h, op: 0.6, d: closed(L([[30, 172], [76, 190], [100, 212], [76, 206], [40, 186]])) },
        { fill: GOLD.b, d: ellipse(CX - 28, 228, 9, 9) + ' ' + ellipse(CX + 28, 228, 9, 9) }, { stroke: GOLD.s, sw: 1.4, d: open([[CX - 28, 228], [CX + 28, 228]]) },
        { clip: true, stroke: glow, sw: 2, op: 0.6, d: open(L([[70, 184], [s - 6, 206], [s + 8, 238]])) }] });
    var JR = armJ(b, 'r', [CX - 100, 446], 'out');
    var JL = armJ(b, 'l', [CX + 212, 236], 'low');
    var oR = fistAt(JR, 14);
    parts = parts.concat(heroArms(tunic, 'r', JR, b, { glow: glow }), heroArms(tunic, 'l', JL, b, { glow: glow, foreFront: true }));
    var fl = parts.filter(function (p) { return p.id === 'fore-l'; })[0];
    fl.layers.push({ clip: true, fill: GOLD.b, d: band([JL.e, JL.w], scaleSt(ARMH.fore, b.k), 1, 0.5, 0.05) });
    parts.push(fistPart(P, 'r', oR, { k: 1.25 }));
    parts.push(palmPart(P, 'l', JL.w, { k: 1.25 }));
    parts = parts.concat(M.weapons.place(M.weapons.gungnir({ up: 290, down: (786 - oR[1]) / 0.85 - 18, glow: true }), { id: 'spear', parent: 'hand-r', behind: true, at: oR, scale: 0.85 }));
    var grey = HAIR.grey;
    parts.push({ id: 'hair-back', parent: 'torso', behind: true, pivot: [CX, 160], fill: grey.b,
      d: closed(R([[30, 120], [48, 140], [56, 186], [50, 214], [38, 200], [30, 160]])) + ' ' + windLocks(grey, -1, { n: 5, len: 110 }) });
    var head = headPart(P, { shape: 'elder', closedEye: 'r', smile: -0.6, iris: '#9FD3FF', glowEye: '#BFE4FF', browColour: '#9A948A', brow: 'fierce' });
    head.layers.push({ clip: true, stroke: P.dp, sw: 1, op: 0.55, d: open([[CX - 16, 104], [CX, 102], [CX + 16, 104]]) + ' ' + open([[CX - 12, 109], [CX, 108], [CX + 12, 109]]) + ' ' + pairOpen([[33, 132], [37, 138], [36, 144]]) });
    parts.push(head);
    // The beard streams in the same wind as the cloak.
    parts.push({ id: 'beard', parent: 'head', pivot: [CX, 170], fill: grey.b,
      d: closed([[CX - 44, 132], [CX - 40, 160], [CX - 26, 170], [CX - 12, 162], [CX, 166], [CX + 12, 162], [CX + 26, 170], [CX + 40, 160], [CX + 44, 132], [CX + 46, 182], [CX + 34, 232], [CX + 14, 282], [CX - 10, 316, 1], [CX - 18, 290], [CX - 40, 318, 1], [CX - 42, 284], [CX - 54, 236], [CX - 50, 182]]),
      layers: [{ clip: true, fill: grey.s, d: closed([[CX + 4, 160], [CX + 50, 140], [CX + 50, 330], [CX + 6, 330]]) }, { clip: true, fill: grey.h, op: 0.7, d: closed([[CX - 44, 170], [CX - 34, 172], [CX - 30, 260], [CX - 40, 250]]) },
        { clip: true, stroke: grey.s, sw: 1, op: 0.8, d: [-34, -20, -6, 8, 22, 34].map(function (x) { return open([[CX + x * 0.9, 176], [CX + x * 0.8 - 6, 240], [CX + x * 0.4 - 14, 300]]); }).join(' ') },
        { fill: grey.b, d: closed([[CX - 2, 156], [CX - 16, 157], [CX - 30, 168], [CX - 18, 166], [CX - 4, 162]]) + ' ' + closed([[CX + 2, 156], [CX + 16, 157], [CX + 28, 168], [CX + 18, 166], [CX + 4, 162]]) },
        { stroke: grey.s, sw: 1, d: open([[CX - 28, 167], [CX - 14, 159], [CX, 158], [CX + 14, 159], [CX + 26, 167]]) }] });
    parts.push({ id: 'hat', parent: 'head', pivot: [CX, 100], fill: '#3A3430',
      d: ellipse(CX - 4, 100, 88, 16, -4) + ' ' + closed([[CX - 44, 100], [CX - 42, 68], [CX - 28, 48], [CX - 4, 40], [CX + 20, 42], [CX + 38, 56], [CX + 46, 100]]),
      layers: [{ clip: true, fill: '#26211E', d: closed([[CX + 4, 30], [CX + 100, 60], [CX + 100, 124], [CX + 10, 124]]) }, { clip: true, fill: '#57504A', op: 0.7, d: closed([[CX - 86, 98], [CX - 30, 88], [CX - 30, 94], [CX - 76, 106]]) },
        { fill: '#5A3E26', d: closed([[CX - 44, 84], [CX + 46, 84], [CX + 46, 93], [CX - 44, 93]]) }, { clip: true, stroke: glow, sw: 1.8, op: 0.6, d: open([[CX - 90, 102], [CX - 40, 112], [CX + 40, 110], [CX + 86, 96]]) }] });
    head.layers.push({ fill: '#2B1D14', op: 0.22, d: closed([[CX - 44, 104], [CX + 44, 104], [CX + 44, 122], [CX, 126], [CX - 44, 120]]) });
    parts.push({ id: 'raven-r', parent: 'torso', pivot: [CX - s + 20, 200], fill: '#1C1A1E', d: raven(CX - s + 14, 194, 1.05, -1),
      layers: [{ stroke: '#4A4652', sw: 1, d: open([[CX - s + 30, 188], [CX - s + 10, 194], [CX - s - 6, 194]]) }, { fill: '#E9DCC4', d: circle(CX - s - 8, 168, 1.6) }] });
    parts.push({ id: 'raven-l', parent: 'hand-l', pivot: [CX + 232, 150], fill: '#1C1A1E', d: ravenFlying(CX + 232, 150, 1.1, -1),
      layers: [{ stroke: '#4A4652', sw: 1, d: open([[CX + 222, 112], [CX + 238, 96]]) + ' ' + open([[CX + 240, 178], [CX + 262, 190]]) }, { fill: '#E9DCC4', d: circle(CX + 196, 138, 1.6) }] });
    heroHead(parts, b.head, ['hair-back']);
    return { viewBox: [400, 820], parts: parts, headCentre: [CX, 182 - (182 - 130) * b.head],
      meta: meta({ id: 'odin-human', name: 'Odin', tradition: 'norse', heroic: true, emblems: ['one eye, the other burning', 'broad hat', 'dark-blue mantle and storm cloak', 'Gungnir', 'Huginn and Muninn', 'Draupnir'],
        check: 'figure-design.md: Odin identity block (heroic); Grimnismal, Volsunga saga 3, Voluspa 28, Sigrdrifumal 17; storm-light is artistic licence, no halo' }) };
  };

  // ------------------------------------------------------------------ seated figures (viewBox 400 x 640)
  // Head, neck and torso sit on the standing grid; the crossed legs replace the standing legs and the
  // lotus seat (top y 500) and plinth (to y 632) replace the ground.

  /** Halo behind the head: 'disc' (plain, Sarnath) or 'rays' (bhamandala with a ring). */
  function haloPart(o) {
    o = o || {};
    var cx = CX, cy = o.cy || 128, r = o.r || 76, lay = [];
    if (o.kind === 'rays') {
      var rays = [];
      for (var i = 0; i < 36; i++) { var a = Math.PI * 2 * i / 36; rays.push(open([[cx + Math.cos(a) * (r - 18), cy + Math.sin(a) * (r - 18)], [cx + Math.cos(a) * (r - 6), cy + Math.sin(a) * (r - 6)]])); }
      lay.push({ stroke: '#C9962E', sw: 1.2, op: 0.7, d: rays.join(' ') });
    }
    lay.push({ stroke: '#C9962E', sw: 2.2, d: circle(cx, cy, r - 2) });
    lay.push({ stroke: '#C9962E', sw: 1, op: 0.7, d: circle(cx, cy, r - 22) });
    return { id: 'halo', pivot: [cx, cy], fill: o.fill || '#F2DFAE', outline: false, d: circle(cx, cy, r), layers: lay };
  }

  /** Lotus seat over a moulded plinth; o {emblem: glyph id for a window in the plinth, mouse: true}. */
  function lotusSeat(o) {
    o = o || {};
    var lotus = { b: '#E2A39C', s: '#C2786F', h: '#F4CBC2' }, stone = { b: '#C49A5A', s: '#9C7840', h: '#E0BE84' };
    var plinth = closed([[CX - 150, 560, 1], [CX + 150, 560, 1], [CX + 150, 574, 1], [CX + 138, 574, 1], [CX + 138, 616, 1], [CX + 156, 616, 1], [CX + 156, 634, 1], [CX - 156, 634, 1], [CX - 156, 616, 1], [CX - 138, 616, 1], [CX - 138, 574, 1], [CX - 150, 574, 1]]);
    var lay = [
      { clip: true, fill: stone.s, d: closed([[CX + 60, 550], [CX + 170, 550], [CX + 170, 640], [CX + 80, 640]]) },
      { clip: true, fill: stone.h, op: 0.7, d: closed([[CX - 156, 616], [CX + 156, 616], [CX + 156, 620], [CX - 156, 620]]) + ' ' + closed([[CX - 150, 560], [CX + 150, 560], [CX + 150, 564], [CX - 150, 564]]) }
    ];
    if (o.emblem) {
      lay.push({ fill: '#5A3E26', d: closed([[CX - 34, 578, 1], [CX + 34, 578, 1], [CX + 34, 612, 1], [CX - 34, 612, 1]]) });
      var gl = M.glyphs && M.glyphs[o.emblem] ? M.geom.pathData(M.glyphs[o.emblem](CX + (o.emblem === 'mouse' ? 4 : 0), 600, 30)) : '';
      lay.push({ fill: GOLD.h, d: gl });
    }
    var parts = [{ id: 'pedestal', pivot: [CX, 600], fill: stone.b, d: plinth, layers: lay }];
    var up = [], down = [];
    for (var i = -7; i <= 7; i++) {
      var x = CX + i * 20;
      up.push(closed([[x - 11, 534], [x - 9, 516], [x, 500, 1], [x + 9, 516], [x + 11, 534]]));
      down.push(closed([[x - 11 + 10, 532], [x - 9 + 10, 548], [x + 10, 562, 1], [x + 9 + 10, 548], [x + 11 + 10, 532]]));
    }
    parts.push({ id: 'lotus', parent: 'pedestal', pivot: [CX, 532], fill: lotus.b,
      d: sym([[0, 504], [120, 504], [154, 520], [158, 534], [150, 552], [120, 562], [0, 562]]),
      layers: [{ clip: true, fill: lotus.s, d: down.join(' ') }, { clip: true, stroke: lotus.s, sw: 1, d: down.join(' ') }, { clip: true, fill: lotus.h, d: up.join(' ') }, { clip: true, stroke: lotus.s, sw: 1, d: up.join(' ') },
        { clip: true, fill: lotus.s, op: 0.5, d: closed([[CX + 40, 500], [CX + 170, 500], [CX + 170, 570], [CX + 60, 570]]) }] });
    return parts;
  }

  /** Legs crossed in padmasana, soles up. P skin, C cloth (null: bare), o {k width}. */
  function crossedLegs(P, C, o) {
    o = o || {};
    var k = o.k || 1, F = C || P;
    var half = [[0, 424], [44 * k, 420], [82 * k, 428], [114 * k, 446], [136 * k, 470], [144 * k, 494], [138 * k, 512], [112 * k, 522], [70 * k, 524], [30, 520], [0, 518]];
    var shin = closed([[CX - 140 * k, 494], [CX - 112 * k, 476], [CX - 60, 468], [CX, 466], [CX + 44, 462], [CX + 76, 456], [CX + 100, 458], [CX + 104, 470], [CX + 76, 478], [CX + 30, 484], [CX - 30, 490], [CX - 90 * k, 498], [CX - 126 * k, 510]]);
    var lay = [
      { clip: true, fill: F.sh, d: closed([[CX - 160, 500], [CX + 160, 500], [CX + 160, 530], [CX - 160, 530]]) },
      { clip: true, fill: F.sh, d: closed(R([[40, 420], [150, 420], [150, 520], [110, 500], [80, 450]])) },
      { clip: true, fill: F.hl, op: 0.5, d: closed(L([[60, 430], [110, 448], [130, 472], [112, 462], [70, 444]])) },
      { fill: F.sk, d: shin }, { clip: shin, fill: F.sh, d: closed([[CX - 140, 496], [CX + 110, 470], [CX + 110, 490], [CX - 140, 516]]) },
      { stroke: INK, sw: 1.4, op: 0.7, d: shin }
    ];
    if (C) lay.push({ clip: true, stroke: C.dp || C.s, sw: 1.1, op: 0.6, d: [-100, -60, 60, 100].map(function (x) { return open([[CX + x, 440], [CX + x * 1.1, 476], [CX + x * 1.15, 510]]); }).join(' ') });
    // Soles turned up on the thighs, toes outward.
    var sole = P.sole || '#D99A86';
    [[1, 466], [-1, 474]].forEach(function (f) {
      var sx = f[0], y = f[1];
      var d = closed([[CX + sx * 54, y + 4], [CX + sx * 70, y - 6], [CX + sx * 100, y - 8], [CX + sx * 118, y - 2], [CX + sx * 120, y + 6], [CX + sx * 100, y + 10], [CX + sx * 70, y + 12]]);
      lay.push({ fill: P.sk, d: d }, { clip: d, fill: sole, op: 0.85, d: closed([[CX + sx * 58, y + 2], [CX + sx * 72, y - 4], [CX + sx * 100, y - 5], [CX + sx * 114, y], [CX + sx * 100, y + 6], [CX + sx * 72, y + 8]]) },
        { stroke: INK, sw: 1.2, op: 0.7, d: d }, { stroke: P.dp, sw: 0.8, op: 0.6, d: [0, 1, 2, 3].map(function (i) { var x = CX + sx * (112 - i * 4); return open([[x, y - 4 + i], [x + sx * 3, y + 2 + i]]); }).join(' ') });
    });
    return { id: 'pelvis', parent: 'pedestal', pivot: [CX, 470], fill: F.sk, d: sym(half), layers: lay };
  }

  /** Dhyana: hands at rest in the lap, palms up, the right over the left, thumbs touching. */
  function dhyanaHands(P) {
    var lower = closed([[CX + 46, 440], [CX + 30, 446], [CX - 20, 452], [CX - 42, 456], [CX - 46, 462], [CX - 20, 467], [CX + 30, 465], [CX + 48, 456]]);
    var upper = closed([[CX - 48, 436], [CX - 30, 440], [CX + 20, 444], [CX + 42, 446], [CX + 46, 452], [CX + 20, 457], [CX - 30, 457], [CX - 50, 448]]);
    return { id: 'hands', parent: 'torso', pivot: [CX, 450], fill: P.sk, d: lower + ' ' + upper,
      layers: [{ clip: true, fill: P.sh, d: closed([[CX - 50, 456], [CX + 50, 452], [CX + 50, 470], [CX - 50, 470]]) },
        { fill: P.sk, d: upper }, { clip: upper, fill: P.lip, op: 0.25, d: ellipse(CX - 6, 448, 30, 6) },
        { stroke: INK, sw: 1.2, op: 0.75, d: upper },
        { stroke: P.dp, sw: 0.8, op: 0.55, d: [8, 18, 28].map(function (x) { return open([[CX + x, 446], [CX + x + 12, 449]]); }).join(' ') },
        { stroke: INK, sw: 1.2, op: 0.7, d: open([[CX - 16, 440], [CX - 6, 432], [CX + 6, 432], [CX + 16, 438]]) }] };
  }

  /** Cap of small curls (Jina: tiny and tight; Buddha: larger snail-shells and an ushnisha). */
  function curlCap(C, o) {
    o = o || {};
    var r = o.r || 2.6, cap = sym([[0, 74], [24, 76], [40, 86], [47, 102], [48, 120], [44, 126], [40, 112], [30, 104], [14, 101], [0, 101]]);
    var dots = [], spirals = [];
    for (var y = 82; y <= 122; y += r * 2.1) {
      var row = Math.round((y - 82) / (r * 2.1));
      for (var x = -48; x <= 48; x += r * 2.2) {
        var xx = x + (row % 2 ? r * 1.1 : 0);
        dots.push(circle(CX + xx, y, r * 0.95));
        spirals.push(open([[CX + xx - r * 0.5, y], [CX + xx, y - r * 0.5], [CX + xx + r * 0.4, y]]));
      }
    }
    var parts = [{ id: 'hair', parent: 'head', pivot: [CX, 100], fill: C.b, d: cap,
      layers: [{ clip: true, fill: C.h, op: 0.85, d: dots.join(' ') }, { clip: true, stroke: C.s, sw: 0.7, d: spirals.join(' ') }, { clip: true, fill: C.s, op: 0.5, d: closed(R([[14, 70], [60, 90], [60, 130], [36, 110]])) }] }];
    if (o.ushnisha) {
      var us = [], uss = [];
      for (var y2 = 54; y2 <= 78; y2 += r * 2.1) for (var x2 = -26; x2 <= 26; x2 += r * 2.2) { if (Math.pow(x2 / 28, 2) + Math.pow((y2 - 72) / 26, 2) < 1) { us.push(circle(CX + x2, y2, r * 0.95)); uss.push(open([[CX + x2 - r * 0.5, y2], [CX + x2, y2 - r * 0.5], [CX + x2 + r * 0.4, y2]])); } }
      parts.push({ id: 'ushnisha', parent: 'hair', behind: true, pivot: [CX, 78], fill: C.b, d: ellipse(CX, 70, 28, 24),
        layers: [{ clip: true, fill: C.h, op: 0.85, d: us.join(' ') }, { clip: true, stroke: C.s, sw: 0.7, d: uss.join(' ') }, { clip: true, fill: C.s, op: 0.5, d: closed([[CX + 6, 40], [CX + 34, 50], [CX + 34, 90], [CX + 10, 90]]) }] });
    }
    return parts;
  }

  var DHYANA = { r: { s: [CX - 86, 214], e: [CX - 110, 334], w: [CX - 42, 444] }, l: { s: [CX + 86, 214], e: [CX + 110, 334], w: [CX + 44, 442] } };

  /**
   * A seated Tirthankara in meditation (padmasana, dhyana): "hands hanging down to the knees, the
   * Shrivatsa on the breast, a placid look, naked, young and beautiful" (Brihat Samhita 57.45);
   * broad shoulders and a narrow waist, long ears, tiny curls with no ushnisha, the triple umbrella
   * and the halo; the lanchhana on the plinth is the only mark that tells one Jina from another.
   * opts {emblem: 'lion' (Mahavira, default) | 'bull' (Rishabhanatha) | 'deer' (Shantinatha) |
   * 'conch' (Neminatha) | 'snake' (Parshvanatha), sect: 'digambara' (default: unclothed, eyes
   * lowered) | 'svetambara' (open, inlaid eyes and a lower garment)}.
   */
  FIG['tirthankara-human'] = function (opt) {
    var o = opt || {}, emblem = o.emblem || 'lion', sve = o.sect === 'svetambara';
    var names = { lion: 'Mahavira', bull: 'Rishabhanatha', deer: 'Shantinatha', conch: 'Neminatha', snake: 'Parshvanatha' };
    var P = (emblem === 'conch' || emblem === 'snake') ? SKIN['shyama-blue'] : SKIN['warm-gold'];
    var b = { k: 1, sh: 92, waist: 50, lat: 76 };
    var parts = [haloPart({ kind: 'rays' })];
    if (emblem === 'snake') {
      var hoods = [];
      for (var i = 0; i < 7; i++) { var a = Math.PI * (1.08 + 0.84 * i / 6); hoods.push(ellipse(CX + Math.cos(a) * 62, 128 + Math.sin(a) * 74, 15, 20, (a - Math.PI * 1.5) * 57.3)); }
      parts.push({ id: 'hoods', pivot: [CX, 160], fill: '#3F6B4A', d: hoods.join(' ') });
    }
    parts = parts.concat(lotusSeat({ emblem: emblem === 'snake' ? null : emblem }));
    var cloth = sve ? { sk: '#EFE6D2', sh: '#D3C6A8', dp: '#A8987A', hl: '#FBF6EA', b: '#EFE6D2', s: '#D3C6A8' } : null;
    parts.push(crossedLegs(P, cloth));
    parts.push(torsoPart(P, b, { smooth: true, hips: true, layers: [
      // Shrivatsa: the four-lobed mark on the breast.
      { fill: P.dp, op: 0.55, d: closed([[CX, 236, 1], [CX + 4, 244], [CX + 12, 248, 1], [CX + 4, 252], [CX, 260, 1], [CX - 4, 252], [CX - 12, 248, 1], [CX - 4, 244]]) }
    ] }));
    parts = parts.concat(calmArm(P, 'r', DHYANA.r, { k: 1.08 }), calmArm(P, 'l', DHYANA.l, { k: 1.08 }));
    parts.push(dhyanaHands(P));
    parts.push(headPart(P, { eyes: sve ? 'open' : 'lowered', smile: 1, lobes: true, iris: sve ? '#141010' : undefined, tilak: sve ? 'jina' : null }));
    parts = parts.concat(curlCap({ b: '#1E1A1E', s: '#0F0C0F', h: '#3A3238' }, { r: 2.4 }));
    if (o.chhatra !== false) {
      var tiers = [[64, 56], [46, 44], [28, 32]], tierD = [], fringe = [];
      tiers.forEach(function (t) {
        tierD.push(closed([[CX - t[1], t[0] + 4], [CX - t[1] * 0.6, t[0] - 6], [CX, t[0] - 9], [CX + t[1] * 0.6, t[0] - 6], [CX + t[1], t[0] + 4], [CX, t[0] + 7]]));
        for (var x = -t[1] + 6; x <= t[1] - 6; x += 9) fringe.push(circle(CX + x, t[0] + 8, 1.8));
      });
      parts.push({ id: 'chhatra', parent: 'halo', pivot: [CX, 40], fill: GOLD.b, d: tierD.join(' ') + ' ' + circle(CX, 12, 4.5) + ' ' + closed([[CX - 1.5, 14], [CX + 1.5, 14], [CX + 1.5, 70], [CX - 1.5, 70]]),
        layers: [{ fill: '#F4ECDA', d: fringe.join(' ') }, { stroke: GOLD.s, sw: 1, d: tiers.map(function (t) { return open([[CX - t[1], t[0] + 4], [CX, t[0] + 7], [CX + t[1], t[0] + 4]]); }).join(' ') }] });
    }
    return { viewBox: [400, 640], parts: parts, headCentre: [200, 120],
      meta: meta({ id: 'tirthankara-human', name: names[emblem] || 'Tirthankara', tradition: 'jain', emblems: [(emblem === 'snake' ? 'serpent hoods' : emblem + ' (lanchhana)'), 'meditation (padmasana, dhyana)', 'shrivatsa', 'triple umbrella', 'long ears'],
        check: 'figure-design.md: Tirthankara identity block; Brihat Samhita 57.45; say which sect the image follows (' + (sve ? 'Svetambara' : 'Digambara') + ')' }) };
  };

  /**
   * The Buddha touching the earth (bhumisparsha, the moment of the enlightenment): golden skin
   * (DN 30), the ushnisha, the urna between the brows, curls turning to the right, long earlobes,
   * lowered eyes and a faint smile; the robe over the left shoulder with the right shoulder bare;
   * the right hand over the right knee reaching to the earth, the left in the lap; plain halo, lotus seat.
   */
  FIG['buddha-human'] = function () {
    var P = SKIN['warm-gold'], b = { k: 1, sh: 90, waist: 52, lat: 76 };
    var robe = { sk: '#C26A2A', sh: '#9E521C', dp: '#7A3C12', hl: '#DE8A44', rim: '#F0B070', b: '#C26A2A', s: '#9E521C' };
    var parts = [haloPart({ kind: 'disc', fill: '#F2E2B8' })];
    parts = parts.concat(lotusSeat({}));
    parts.push(crossedLegs(P, robe));
    // The upper robe across the body from the left shoulder, leaving the right shoulder and chest bare.
    parts.push(torsoPart(P, b, { smooth: true, hips: true, layers: [
      { clip: true, fill: robe.sk, d: closed([[CX + 120, 190], [CX + 30, 194], [CX - 10, 250], [CX - 50, 320], [CX - 70, 380], [CX + 120, 400]]) },
      { clip: true, fill: robe.sh, d: closed([[CX + 120, 190], [CX + 60, 196], [CX + 60, 400], [CX + 120, 400]]) },
      { clip: true, stroke: robe.dp, sw: 1.2, op: 0.6, d: [0, 1, 2, 3].map(function (i) { return open([[CX + 40 + i * 12, 200 + i * 6], [CX - 20 + i * 18, 300 + i * 12], [CX - 50 + i * 24, 380]]); }).join(' ') },
      { clip: true, stroke: robe.dp, sw: 1.6, d: open([[CX + 30, 194], [CX - 10, 250], [CX - 50, 320], [CX - 70, 380]]) },
      { clip: true, stroke: robe.hl, sw: 1.2, op: 0.8, d: open([[CX + 26, 198], [CX - 14, 252], [CX - 54, 322]]) }
    ] }));
    var JR = { s: [CX - 86, 214], e: [CX - 112, 334], w: [CX - 124, 456] };
    var arms = calmArm(P, 'r', JR, { k: 1.08 }).concat(calmArm(robe, 'l', DHYANA.l, { k: 1.12 }));
    parts = parts.concat(arms);
    // Right hand over the knee, the long fingers reaching down to touch the earth.
    parts.push({ id: 'hand-r', parent: 'fore-r', pivot: [CX - 124, 456], fill: P.sk,
      d: closed([[CX - 132, 450], [CX - 116, 450], [CX - 112, 470], [CX - 114, 500], [CX - 118, 516], [CX - 124, 518], [CX - 130, 512], [CX - 136, 492], [CX - 138, 470]]),
      layers: [{ clip: true, fill: P.sh, d: closed([[CX - 124, 446], [CX - 108, 446], [CX - 108, 520], [CX - 122, 520]]) },
        { clip: true, stroke: P.dp, sw: 0.8, op: 0.6, d: open([[CX - 130, 486], [CX - 128, 514]]) + ' ' + open([[CX - 124, 486], [CX - 123, 516]]) + ' ' + open([[CX - 118, 486], [CX - 118, 512]]) }] });
    parts.push({ id: 'hands', parent: 'torso', pivot: [CX + 10, 452], fill: P.sk,
      d: closed([[CX + 48, 440], [CX + 30, 446], [CX - 14, 450], [CX - 30, 454], [CX - 30, 462], [CX - 10, 466], [CX + 30, 464], [CX + 50, 456]]),
      layers: [{ clip: true, fill: P.lip, op: 0.25, d: ellipse(CX + 4, 456, 26, 5) }, { clip: true, stroke: P.dp, sw: 0.8, op: 0.55, d: [-20, -10, 0].map(function (x) { return open([[CX + x, 452], [CX + x - 10, 455]]); }).join(' ') }] });
    var head = headPart(P, { eyes: 'lowered', smile: 1.1, lobes: true, tilak: 'urna' });
    // The pierced, lengthened earlobes reach toward the shoulders.
    head.d = head.d + ' ' + pair([[44, 150], [49, 154], [51, 176], [47, 188], [43, 186], [42, 170]]);
    parts.push(head);
    parts = parts.concat(curlCap({ b: '#1E2533', s: '#10141E', h: '#3A465E' }, { r: 3.3, ushnisha: true }));
    return { viewBox: [400, 640], parts: parts, headCentre: [200, 118],
      meta: meta({ id: 'buddha-human', name: 'The Buddha', tradition: 'buddhist', emblems: ['earth-touching gesture (bhumisparsha)', 'ushnisha and urna', 'right-turning curls', 'robe over the left shoulder', 'lotus seat'],
        check: 'figure-design.md: Buddha identity block; DN 30 (golden skin, ushnisha, urna, long arms); not for an aniconic-period scene' }) };
  };

  // ------------------------------------------------------------------ Ganesha
  /**
   * Ganesha as the Ganapati Atharvashirsha sees him: "one-tusked, four-handed, bearing the noose
   * and the goad, the tusk and the boon-giving hand; the mouse on his banner; red, pot-bellied, with
   * winnowing-fan ears, clad in red". The trunk turns to his left to a modaka; a serpent is his
   * belt (as in the Met's Kalacuri Ganesha); he sits on a lotus with the mouse below.
   * opts {tone: 'red' (default, the text) | 'gold' (common in later images)}.
   */
  FIG['ganesha-human'] = function (opt) {
    var o = opt || {};
    var P = o.tone === 'gold' ? SKIN['warm-gold'] : { sk: '#C65A3E', sh: '#A6452E', dp: '#76301F', hl: '#DE7C5C', rim: '#F2B096', lip: '#7A2C1E', eye: '#1E1410', sole: '#E0A08A' };
    var cloth = { sk: '#8E1F2A', sh: '#6E1620', dp: '#4E0E16', hl: '#B23A44', rim: '#D4646C', b: '#8E1F2A', s: '#6E1620' };
    var glow = '#FFD98A', GB = { k: 1 };
    var parts = M.auras.make('lotus', { cx: CX, cy: 160, r: 236 }).concat(lotusSeat({ emblem: 'mouse' }));
    parts.push(crossedLegs(P, cloth, { k: 1.08 }));
    // Torso: broad shoulders over the great belly (Lambodara).
    // Heroic: broad, muscled shoulders and chest over the great belly (Lambodara is iconography, kept).
    var half = [[0, 164], [26, 166], [30, 182], [54, 194], [84, 202], [110, 214], [114, 238], [102, 264], [100, 296], [106, 340], [104, 384], [90, 420], [58, 442], [0, 448]];
    var belly = ellipse(CX, 372, 86, 76);
    parts.push({ id: 'torso', parent: 'pelvis', pivot: [CX, 420], fill: P.sk, d: sym(half), layers: [
      { clip: true, fill: P.sh, d: closed(R([[40, 190], [110, 200], [110, 460], [40, 460], [70, 300]])) },
      { clip: true, fill: P.sh, d: sym([[0, 160], [24, 162], [22, 180], [0, 186]]) },
      { clip: true, fill: P.hl, op: 0.55, d: ellipse(CX - 40, 336, 28, 44) },
      { clip: true, fill: P.sh, d: closed(R([[3, 250], [30, 262], [62, 256], [90, 238], [86, 232], [60, 246], [30, 252], [3, 242]])) },
      { clip: true, fill: P.sh, op: 0.7, d: closed(L([[3, 250], [30, 262], [62, 256], [90, 238], [86, 232], [60, 246], [30, 252], [3, 242]])) },
      { clip: true, stroke: P.dp, sw: 1.4, op: 0.5, d: pairOpen([[3, 250], [30, 262], [62, 256], [90, 238]]) },
      { clip: true, fill: P.hl, op: 0.5, d: closed(L([[6, 206], [40, 202], [80, 212], [70, 228], [36, 236], [8, 232]])) },
      { clip: true, stroke: glow, sw: 2.4, op: 0.75, d: open(R([[110, 214], [114, 238], [102, 264], [100, 296], [106, 340], [104, 384]])) },
      { clip: true, stroke: glow, sw: 1.6, op: 0.45, d: open(L([[110, 214], [114, 238], [102, 264], [100, 296], [106, 340], [104, 384]])) },
      { stroke: P.dp, sw: 1.2, op: 0.45, d: open([[CX - 80, 410], [CX - 40, 440], [CX + 40, 440], [CX + 80, 410]]) },
      { clip: true, fill: P.dp, op: 0.7, d: ellipse(CX, 370, 4.4, 5.4) },
      // The serpent belt around the belly, hood raised at the front.
      { clip: true, stroke: '#2C4E35', sw: 7, d: open([[CX - 100, 392], [CX - 50, 404], [CX, 408], [CX + 50, 404], [CX + 100, 392]]) },
      { clip: true, stroke: '#4F7A55', sw: 4.6, d: open([[CX - 100, 392], [CX - 50, 404], [CX, 408], [CX + 50, 404], [CX + 100, 392]]) },
      { fill: '#3F6B4A', d: closed([[CX - 9, 408], [CX - 12, 392], [CX - 6, 382], [CX, 380, 1], [CX + 6, 382], [CX + 12, 392], [CX + 9, 408]]) },
      { fill: '#E9D9A8', op: 0.8, d: closed([[CX - 3, 404], [CX - 5, 392], [CX, 386], [CX + 5, 392], [CX + 3, 404]]) },
      { fill: INK, d: circle(CX - 3.5, 386, 1.1) + ' ' + circle(CX + 3.5, 386, 1.1) },
      { fill: '#F4ECDA', d: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(function (i) { var a = Math.PI * (0.12 + 0.76 * i / 12); return circle(CX - Math.cos(a) * 40, 200 + Math.sin(a) * 44, 2.4); }).join(' ') }
    ].concat(threadLayers('#F1E7CF'))});
    parts.push({ id: 'belly-light', parent: 'torso', pivot: [CX, 372], fill: 'none', outline: false, d: 'M0 0Z', layers: [{ stroke: P.dp, sw: 1.2, op: 0.4, d: belly }] });
    // Upper arms rise behind the shoulders: goad (ankusha) in the right, noose (pasha) in the left.
    var UR = { s: [CX - 88, 224], e: [CX - 150, 262], w: [CX - 152, 184] }, UL = { s: [CX + 88, 224], e: [CX + 150, 262], w: [CX + 152, 184] };
    parts = parts.concat(heroArms(P, 'r', UR, GB, { prefix: 'arm2', forePrefix: 'fore2', behind: true, foreFront: true, k: 0.98, glow: glow }), heroArms(P, 'l', UL, GB, { prefix: 'arm2', forePrefix: 'fore2', behind: true, foreFront: true, k: 0.98, glow: glow }));
    parts.push(fistPart(P, 'r', [CX - 153, 170], { id: 'hand2-r', parent: 'fore2-r', k: 1.15 }), fistPart(P, 'l', [CX + 153, 170], { id: 'hand2-l', parent: 'fore2-l', k: 1.15 }));
    parts = parts.concat(M.weapons.place(M.weapons.ankusha({ shaft: 96 }), { id: 'ankusha', parent: 'hand2-r', behind: true, at: [CX - 153, 170], angle: -8, scale: 1.1 }));
    parts = parts.concat(M.weapons.place(M.weapons.pasha({ r: 26 }), { id: 'pasha', parent: 'hand2-l', at: [CX + 153, 160], angle: 10, scale: 1.15 }));
    // Lower arms: the broken tusk in the right hand, the left lowered in the boon gesture (varada).
    var LR = { s: [CX - 92, 222], e: [CX - 120, 330], w: [CX - 104, 420] }, LL = { s: [CX + 92, 222], e: [CX + 120, 330], w: [CX + 128, 420] };
    LR = { s: [CX - 100, 226], e: [CX - 132, 330], w: [CX - 106, 420] }; LL = { s: [CX + 100, 226], e: [CX + 132, 330], w: [CX + 128, 420] };
    parts = parts.concat(heroArms(P, 'r', LR, GB, { foreFront: true, k: 1.12, glow: glow }), heroArms(P, 'l', LL, GB, { foreFront: true, k: 1.12, glow: glow }));
    [['r', LR], ['l', LL]].forEach(function (s) { armJewels(parts, s[0], s[1], { k: 1.12, hero: true }); });
    parts.push(fistPart(P, 'r', [CX - 102, 434], { k: 1.1 }));
    parts.push({ id: 'tusk-held', parent: 'hand-r', pivot: [CX - 102, 434], fill: '#F1E7CF', d: closed([[CX - 106, 420], [CX - 98, 420], [CX - 88, 382], [CX - 84, 368, 1], [CX - 92, 380]]), layers: [{ stroke: '#C9B98A', sw: 0.8, d: open([[CX - 101, 418], [CX - 89, 380]]) }] });
    parts.push(palmPart(P, 'l', LL.w, { down: true, k: 1.15 }));
    // Head: twin domes of the brow, winnowing-fan ears, small kind eyes, the trunk to his left.
    var earHalf = [[44, 96], [70, 80], [104, 82], [124, 104], [128, 140], [118, 174], [96, 194], [70, 196], [54, 180], [46, 150]];
    parts.push({ id: 'ears', parent: 'torso', pivot: [CX, 130], fill: P.sk, d: pair(earHalf),
      layers: [{ clip: true, fill: P.lip, op: 0.25, d: pair([[52, 104], [74, 92], [100, 96], [114, 114], [116, 144], [106, 170], [88, 182], [66, 180], [56, 160]]) },
        { clip: true, fill: P.sh, d: closed(R([[44, 96], [70, 80], [104, 82], [124, 104], [128, 140], [118, 174], [96, 194], [100, 170], [108, 136], [96, 104], [66, 96]])) },
        { clip: true, stroke: P.dp, sw: 1, op: 0.45, d: pairOpen([[62, 100], [96, 98], [112, 130], [104, 166], [80, 184]]) },
        { clip: true, fill: GOLD.b, d: pair([[118, 104], [126, 104], [130, 140], [122, 176], [114, 176], [122, 140]]) }] });
    var headHalf = [[0, 76], [14, 70], [28, 72], [40, 82], [48, 100], [52, 122], [50, 142], [42, 158], [30, 168], [18, 172], [0, 174]];
    var trunk = [[CX, 150], [CX - 3, 194], [CX, 236], [CX + 10, 268], [CX + 30, 282], [CX + 48, 276], [CX + 54, 262]];
    var tst = [[0, 19, 19], [0.25, 15, 15], [0.5, 11, 11], [0.72, 8.5, 8.5], [0.88, 7, 7], [1, 6, 6]];
    var hd = { id: 'head', parent: 'torso', pivot: [CX, 176], fill: P.sk, d: sym(headHalf), layers: [
      { clip: true, fill: P.sh, d: closed(R([[24, 70], [50, 96], [54, 140], [40, 166], [24, 176], [32, 150], [36, 120], [30, 90]])) },
      { clip: true, fill: P.hl, op: 0.55, d: ellipse(CX - 18, 92, 13, 9) + ' ' + ellipse(CX + 16, 92, 11, 8) },
      { clip: true, stroke: P.dp, sw: 1, op: 0.4, d: open([[CX, 80], [CX, 104]]) },
      { stroke: '#F2EEE6', sw: 2.4, d: [100, 106, 112].map(function (y) { return open([[CX - 22, y + 1], [CX, y], [CX + 22, y + 1]]); }).join(' ') },
      { fill: '#C8321F', d: ellipse(CX, 106, 2.6, 3.4) }
    ] };
    [1, -1].forEach(function (sx) {
      var eye = closed([[CX + sx * 16, 128, 1], [CX + sx * 22, 123.6], [CX + sx * 30, 124], [CX + sx * 35, 127.6, 1], [CX + sx * 29, 130.6], [CX + sx * 22, 130.8]]);
      hd.layers.push({ fill: '#F1E9DC', d: eye }, { clip: eye, fill: P.eye, d: circle(CX + sx * 25, 127, 3.6) }, { fill: '#FFF8EC', d: circle(CX + sx * 24, 125.6, 0.9) },
        { stroke: INK, sw: 1.8, d: open([[CX + sx * 16, 128], [CX + sx * 22, 123.6], [CX + sx * 30, 124], [CX + sx * 37, 125.6]]) },
        { stroke: P.dp, sw: 1.6, d: open([[CX + sx * 14, 118], [CX + sx * 25, 113.6], [CX + sx * 36, 117]]) });
    });
    parts.push(hd);
    // Tusks: the right one broken short (it is in his hand), the left whole.
    parts.push({ id: 'tusks', parent: 'head', pivot: [CX, 166], fill: '#F1E7CF', d: closed([[CX - 26, 158], [CX - 16, 160], [CX - 20, 176], [CX - 26, 178, 1]]) + ' ' + closed([[CX + 16, 160], [CX + 26, 158], [CX + 34, 182], [CX + 42, 204], [CX + 40, 210, 1], [CX + 28, 192]]),
      layers: [{ stroke: '#C9B98A', sw: 0.8, d: open([[CX + 22, 166], [CX + 34, 196]]) }] });
    parts.push({ id: 'trunk', parent: 'head', pivot: [CX, 150], fill: P.sk, d: limb(trunk, tst, 1),
      layers: [{ clip: true, fill: P.sh, d: limbBand(trunk, tst, 1, 'outer', 8) }, { clip: true, fill: P.hl, op: 0.5, d: limbBand(trunk, tst, 1, 'inner', 5, 0, 0.6) },
        { clip: true, stroke: P.dp, sw: 0.9, op: 0.5, d: [0.15, 0.25, 0.35, 0.45, 0.55, 0.65].map(function (t) { var a = along(trunk, t), n = [-a.d[1], a.d[0]], w = 14 - t * 10; return open([[a.p[0] + n[0] * w, a.p[1] + n[1] * w], [a.p[0] + a.d[0] * 2, a.p[1] + a.d[1] * 2], [a.p[0] - n[0] * w, a.p[1] - n[1] * w]]); }).join(' ') }] });
    parts.push({ id: 'modaka', parent: 'trunk', pivot: [CX + 60, 262], fill: '#E8C27A', d: closed([[CX + 48, 264], [CX + 52, 250], [CX + 60, 238, 1], [CX + 68, 250], [CX + 72, 264], [CX + 60, 270]]),
      layers: [{ stroke: '#B88A3E', sw: 0.9, d: open([[CX + 60, 240], [CX + 56, 266]]) + ' ' + open([[CX + 60, 240], [CX + 66, 266]]) }] });
    var kp = kiritaPart({ base: 84, top: 0, wB: 38, wT: 26 });
    kp.parent = 'head';
    parts.push(kp);
    return { viewBox: [400, 640], parts: parts, headCentre: [200, 140],
      meta: meta({ id: 'ganesha-human', name: 'Ganesha', tradition: 'indian', emblems: ['elephant head', 'one tusk (Ekadanta)', 'noose and goad', 'boon gesture', 'modaka', 'mouse', 'serpent belt'],
        check: 'figure-design.md: Ganesha identity block; Ganapati Atharvashirsha (red, pot-bellied, winnow ears, noose, goad, tusk, boon, mouse); which tusk is broken varies by image' }) };
  };

  M.human.ids = ['rama-human', 'hanuman-human', 'shiva-human', 'ganesha-human', 'athena-human', 'odin-human', 'tirthankara-human', 'buddha-human'];
  M.human.parts = { armJ: armJ, fistAt: fistAt, HERO: HERO, torso: torsoPart, arms: armParts, calmArm: calmArm, leg: legPart, head: headPart, fist: fistPart, palm: palmPart, dhoti: dhotiPart, thread: threadLayers, band: band, BODY: BODY, ARM: ARM, LEG: LEG, HAIR: HAIR, GOLD: GOLD };
})(typeof window !== 'undefined' ? window : this);
