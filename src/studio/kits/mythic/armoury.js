/*
 * Motion Lab mythic kit - armoury: weapons, held attributes and auras (src/studio/kits/mythic/armoury.js)
 *
 * Every weapon is drawn ONCE at its own origin, the grip, pointing up (-y), in figure units (the
 * 400 x 820 human grid). A figure places it with M.weapons.place(spec, {id, parent, at, angle,
 * scale}), which returns parts whose `tf` moves the drawing into the hand; posing still rotates the
 * hand. Load after mythic.js, figures.js and figures-human.js (it reuses M.human.geom).
 *
 *   var bow = M.weapons.kodanda();                         // spec {d, fill, layers, extra}
 *   parts = parts.concat(M.weapons.place(bow, {id: 'bow', parent: 'hand-l', at: [338, 446]}));
 *   parts = M.auras.make('tejas', {cx: 200, cy: 150, r: 230}).concat(parts);   // aura first: deepest
 *
 * Forms follow the research in .claude/skills/mythic-tales/references/figure-design.md section 6
 * (weapon iconography) and are drawn for heroic legibility: big readable silhouettes, gold on the
 * sacred parts, light from the viewer's upper left. Deterministic: no randomness anywhere.
 */
(function (global) {
  'use strict';

  var Studio = global.Studio || (global.Studio = {});
  var KIT = Studio.kit = Studio.kit || {};
  var M = KIT.mythic = KIT.mythic || {};
  if (!M.human || !M.human.geom) throw new Error('kits/mythic/armoury.js: load figures-human.js first');
  var G = M.human.geom;
  var INK = '#2B1D14';

  // ------------------------------------------------------------------ helpers (origin-centred)
  function f1(n) { return Math.round(n * 10) / 10; }
  function C(pts, k) { return G.bez(pts, true, k); }
  function O(pts, k) { return G.bez(pts, false, k); }
  function E(cx, cy, rx, ry, rot) { return G.ellipse(cx, cy, rx, ry, rot); }
  function circ(cx, cy, r) { return E(cx, cy, r, r); }
  /** Closed shape symmetric about x = 0 from its right half (axis top to axis bottom). */
  function S(half, k) {
    var r = half, l = half.slice(1, -1).map(function (p) { return [-p[0], p[1], p[2]]; }).reverse();
    return C(r.concat(l), k);
  }
  function mx(pts) { return pts.map(function (p) { return [-p[0], p[1], p[2]]; }); }
  function rect(x0, y0, x1, y1) { return C([[x0, y0, 1], [x1, y0, 1], [x1, y1, 1], [x0, y1, 1]]); }
  /** Tapered ribbon along a chain: widths w0 -> w1 (both sides), for bow limbs, prongs, ribbons. */
  function ribbon(chain, w0, w1, wm) {
    var n = chain.length, st = chain.map(function (p, i) {
      var t = i / (n - 1), w = wm === undefined ? w0 + (w1 - w0) * t : (t < 0.5 ? w0 + (wm - w0) * t * 2 : wm + (w1 - wm) * (t - 0.5) * 2);
      return [t, w, w];
    });
    return G.limb(chain, st, 1, { startRound: 0.7, endRound: 0.7 });
  }
  function rows(n, f) { var out = []; for (var i = 0; i < n; i++) out.push(f(i)); return out.join(' '); }

  var GOLD = { b: '#C9962E', s: '#9A6C1C', h: '#F3D57E', d: '#6E4A10' };
  var STEEL = { b: '#9AA6AE', s: '#66727C', h: '#E2EAEE', d: '#3E4850' };
  var BRONZE = { b: '#BC8B3C', s: '#8C6222', h: '#ECC57C', d: '#5E3E12' };
  var WOOD = { b: '#6B4426', s: '#4A2E18', h: '#946A44', d: '#2E1A0C' };
  var RED = { b: '#A8321F', s: '#7A2216', h: '#D85A40' };
  var IVORY = { b: '#EFE4CC', s: '#CDBE9C', h: '#FFF8EA' };
  var WP = { gold: GOLD, steel: STEEL, bronze: BRONZE, wood: WOOD, red: RED, ivory: IVORY };

  /** Shading for a body of colour c whose right edge is at x1 (light from the upper left). */
  function shadeRight(c, x0, x1, y0, y1) { return { clip: true, fill: c.s, d: C([[x0, y0 - 10], [x1 + 20, y0 - 10], [x1 + 20, y1 + 10], [x0, y1 + 10]]) }; }

  // ------------------------------------------------------------------ Indian weapons and attributes
  var W = {};

  /**
   * Kodanda: Rama's great bow. A tall composite recurve, lacquered red and gold, gold makara-curl
   * tips, a bound grip; the string drawn taut. Grip at the origin, height about 2 x 360.
   */
  W.kodanda = function (o) {
    o = o || {};
    var s = o.size || 1, H = 352 * s;
    var up = [[2, -16], [8, -70], [18, -150], [22, -230], [16, -292], [2, -332], [-14, -350]].map(function (p) { return [p[0] * s, p[1] * s]; });
    var chain = up.slice().reverse().map(function (p) { return [p[0], p[1]]; }).concat(up.map(function (p) { return [p[0], -p[1]]; }));
    var body = G.limb(chain, chain.map(function (p, i) {
      var t = i / (chain.length - 1), w = 2.6 + 5.2 * Math.sin(Math.PI * t) + (Math.abs(t - 0.5) < 0.06 ? 2.4 : 0);
      return [t, w, w];
    }), 1, { startRound: 0.6, endRound: 0.6 });
    var tip = function (sy) { var p = up[up.length - 1], y = p[1] * sy; return circ(p[0] - 2 * s, y + sy * -2 * s, 6.4 * s) + ' ' + O([[p[0] + 4 * s, y], [p[0] - 4 * s, y - sy * 10 * s], [p[0] - 14 * s, y - sy * 6 * s], [p[0] - 12 * s, y + sy * 4 * s]]); };
    var bands = [-0.92, -0.62, -0.32, 0.32, 0.62, 0.92].map(function (f) {
      var idx = Math.round((f + 1) / 2 * (chain.length - 1)), p = chain[idx];
      return rect(p[0] - 12 * s, p[1] - 4 * s, p[0] + 14 * s, p[1] + 4 * s);
    }).join(' ');
    var strX = up[up.length - 1][0] - 2 * s;
    return { fill: RED.b, d: body,
      layers: [
        { stroke: IVORY.h, sw: 1.6, d: O([[strX, -H + 4], [strX, H - 4]]) },
        { clip: true, fill: RED.s, d: C(chain.map(function (p) { return [p[0] + 2 * s, p[1]]; }).concat(chain.slice().reverse().map(function (p) { return [p[0] + 30 * s, p[1]]; }))) },
        { clip: true, stroke: GOLD.h, sw: 1.4, d: O(chain.map(function (p) { return [p[0] - 2.4 * s, p[1]]; })) },
        { clip: true, fill: GOLD.b, d: bands },
        { clip: true, stroke: GOLD.s, sw: 0.8, d: bands },
        // The bound grip.
        { fill: '#5A2A1A', d: rect(-6 * s, -26 * s, 12 * s, 26 * s) },
        { stroke: GOLD.b, sw: 1.2, d: rows(9, function (i) { var y = (-24 + i * 6) * s; return O([[-6 * s, y], [12 * s, y + 4 * s]]); }) },
        { fill: GOLD.b, d: rect(-8 * s, -32 * s, 14 * s, -24 * s) + ' ' + rect(-8 * s, 24 * s, 14 * s, 32 * s) },
        { fill: GOLD.b, d: tip(1) + ' ' + tip(-1) }, { stroke: GOLD.d, sw: 1, d: tip(1) + ' ' + tip(-1) },
        { fill: RED.h, d: circ(up[up.length - 1][0] - 2 * s, -H, 2.2 * s) + ' ' + circ(up[up.length - 1][0] - 2 * s, H, 2.2 * s) }
      ] };
  };

  /** A divine arrow (shara) with a leaf-shaped gold head; glow: true wraps the head in light (tejas). */
  W.shara = function (o) {
    o = o || {};
    var L = o.len || 300, top = -L * 0.62, bot = L * 0.38;
    var head = C([[0, top - 46, 1], [11, top - 22], [7, top - 4], [2, top + 2], [-2, top + 2], [-7, top - 4], [-11, top - 22]]);
    var vane = function (sx) { return C([[sx * 1.5, bot - 52], [sx * 11, bot - 44], [sx * 12, bot - 8, 1], [sx * 1.5, bot - 14]]); };
    var lay = [];
    if (o.glow) lay.push({ fill: { radial: [[0, '#FFF6D8', 0.95], [0.45, '#FFD36A', 0.55], [1, '#FFB547', 0]], cx: 0, cy: top - 22, r: 46 }, d: E(0, top - 22, 46, 54) });
    lay.push({ fill: GOLD.b, d: head }, { fill: GOLD.h, d: C([[0, top - 44, 1], [-9, top - 22], [-5, top - 4], [0, top - 2]]) }, { stroke: GOLD.d, sw: 1, d: head },
      { stroke: GOLD.s, sw: 1, d: O([[0, top - 40], [0, top]]) },
      { fill: GOLD.b, d: rect(-3, top, 3, top + 10) },
      { fill: '#F1E7CF', d: vane(-1) }, { fill: RED.b, d: vane(1) }, { stroke: INK, sw: 0.8, op: 0.6, d: vane(-1) + ' ' + vane(1) },
      { stroke: RED.s, sw: 0.9, d: rows(4, function (i) { var y = bot - 46 + i * 10; return O([[-10, y + 4], [-2, y]]) + ' ' + O([[2, y], [10, y + 4]]); }) },
      { fill: GOLD.b, d: rect(-3, bot - 2, 3, bot + 6) });
    return { fill: '#7A5432', d: rect(-1.8, top + 6, 1.8, bot), layers: lay };
  };

  /** Quiver (tuna) with arrow fletchings, gold bands and a tassel; extra part 'arrows' sits behind. */
  W.tuna = function (o) {
    o = o || {};
    var h = o.h || 230, w = o.w || 20;
    var body = C([[-w, -h * 0.5, 1], [w, -h * 0.5, 1], [w * 0.86, h * 0.5], [0, h * 0.5 + 8], [-w * 0.86, h * 0.5]]);
    var fl = rows(6, function (i) { var x = -w + 4 + i * (2 * w - 8) / 5, y = -h * 0.5 - 30 - (i % 2) * 10; return C([[x - 5, y + 34], [x - 6, y + 8], [x, y, 1], [x + 6, y + 8], [x + 5, y + 34]]); });
    return { fill: '#7A3A22', d: body,
      layers: [
        shadeRight({ s: '#5A2614' }, w * 0.2, w, -h * 0.5, h * 0.5 + 10),
        { clip: true, fill: '#9A5232', op: 0.8, d: rect(-w, -h * 0.5, -w * 0.5, h * 0.5) },
        { clip: true, fill: GOLD.b, d: rect(-w - 2, -h * 0.5, w + 2, -h * 0.5 + 14) + ' ' + rect(-w - 2, -6, w + 2, 6) + ' ' + rect(-w - 2, h * 0.5 - 18, w + 2, h * 0.5 + 10) },
        { clip: true, stroke: GOLD.s, sw: 1, d: rows(5, function (i) { var x = -w + 4 + i * (2 * w - 8) / 4; return O([[x, -h * 0.5 + 2], [x, -h * 0.5 + 12]]); }) },
        { clip: true, stroke: GOLD.h, sw: 1, d: O([[-w * 0.7, -h * 0.4], [-w * 0.6, h * 0.4]]) },
        { fill: RED.b, d: circ(0, 0, 5) }
      ],
      extra: [{ suffix: 'arrows', behind: true, fill: '#F1E7CF', d: fl, layers: [{ clip: true, fill: RED.b, d: rect(-w, -h * 0.5 - 60, 0, -h * 0.5) }, { stroke: INK, sw: 0.7, op: 0.6, d: fl }] }] };
  };

  /**
   * Gada: Hanuman's mace. A great fluted gold head (ribs as meridians), a jewelled equator band, a
   * lotus collar and a crown finial; a long banded shaft with a red grip and a pommel. Grip at the
   * origin (lower shaft); the head's centre is at y = -(shaft + 62).
   */
  W.gada = function (o) {
    o = o || {};
    var sh = o.shaft || 250, rx = o.r || 54, ry = rx * 1.12, cy = -sh - ry + 6, s = rx / 54;
    var head = E(0, cy, rx, ry);
    var ribs = [-0.82, -0.56, -0.28, 0, 0.28, 0.56, 0.82].map(function (q) {
      var pts = [];
      for (var i = 0; i <= 12; i++) { var ph = -Math.PI / 2 + Math.PI * i / 12; pts.push([rx * q * Math.cos(ph), cy + ry * Math.sin(ph)]); }
      return O(pts);
    }).join(' ');
    var eq = function (dy, ry2) { var pts = []; for (var i = 0; i <= 16; i++) { var a = Math.PI * i / 16; pts.push([-rx * Math.cos(a), cy + dy + ry2 * Math.sin(a)]); } return pts; };
    var band = C(eq(-8 * s, 10 * s).concat(eq(8 * s, 10 * s).reverse()));
    var jewels = [-0.7, -0.35, 0, 0.35, 0.7].map(function (q) { return E(rx * q * 0.98, cy + 10 * s * Math.sqrt(1 - q * q), 4 * s * Math.sqrt(1 - q * q * 0.6), 5 * s); }).join(' ');
    var collarTop = cy + ry - 10 * s;
    var collar = C([[-22 * s, collarTop], [22 * s, collarTop], [14 * s, collarTop + 22 * s], [8 * s, collarTop + 30 * s], [-8 * s, collarTop + 30 * s], [-14 * s, collarTop + 22 * s]]);
    var petals = rows(5, function (i) { var x = (-16 + i * 8) * s; return C([[x - 5 * s, collarTop + 2], [x, collarTop + 18 * s, 1], [x + 5 * s, collarTop + 2]]); });
    var top = cy - ry;
    var finial = C([[0, top - 44 * s, 1], [7 * s, top - 30 * s], [9 * s, top - 18 * s], [16 * s, top - 10 * s], [18 * s, top + 4], [-18 * s, top + 4], [-16 * s, top - 10 * s], [-9 * s, top - 18 * s], [-7 * s, top - 30 * s]]);
    var shaft = C([[-6, collarTop + 28 * s], [6, collarTop + 28 * s], [7.5, 58], [-7.5, 58]]);
    var pommel = circ(0, 68, 11) + ' ' + C([[0, 96, 1], [6, 76], [-6, 76]]);
    return { fill: GOLD.b, d: head + ' ' + collar + ' ' + finial + ' ' + shaft + ' ' + pommel,
      layers: [
        { clip: true, fill: GOLD.s, d: E(rx * 0.34, cy + ry * 0.1, rx * 0.86, ry * 1.02) + ' ' + rect(0.5, collarTop, 30, 110) },
        { clip: true, fill: GOLD.d, op: 0.45, d: E(rx * 0.62, cy + ry * 0.24, rx * 0.5, ry * 0.8) },
        { clip: true, stroke: GOLD.d, sw: 1.6, op: 0.75, d: ribs },
        { clip: true, stroke: GOLD.h, sw: 1.2, op: 0.7, d: [-0.7, -0.42].map(function (q) { var pts = []; for (var i = 2; i <= 10; i++) { var ph = -Math.PI / 2 + Math.PI * i / 12; pts.push([rx * q * Math.cos(ph) + 2, cy + ry * Math.sin(ph)]); } return O(pts); }).join(' ') },
        { clip: true, fill: '#FFF3C4', op: 0.85, d: E(-rx * 0.42, cy - ry * 0.42, rx * 0.16, ry * 0.2, -25) },
        { fill: GOLD.b, d: band }, { clip: band, fill: GOLD.s, d: rect(0, cy - 30, rx + 4, cy + 30) }, { stroke: GOLD.d, sw: 1.1, d: band },
        { fill: RED.b, d: jewels }, { fill: '#FFD9C8', op: 0.8, d: [-0.7, -0.35, 0, 0.35, 0.7].map(function (q) { return circ(rx * q * 0.98 - 1.4, cy + 10 * s * Math.sqrt(1 - q * q) - 1.6, 1.2); }).join(' ') },
        { fill: GOLD.h, op: 0.7, d: petals }, { stroke: GOLD.d, sw: 0.9, d: petals },
        { stroke: GOLD.d, sw: 1, d: finial }, { fill: RED.b, d: circ(0, top - 14 * s, 3.6 * s) },
        // Shaft bands, the spiral grip binding and the pommel.
        { clip: true, fill: GOLD.d, op: 0.5, d: rows(5, function (i) { var y = collarTop + 50 * s + i * (sh - 60 * s) / 5; return rect(-9, y, 9, y + 6); }) },
        { fill: RED.b, d: rect(-7.6, -22, 7.6, 30) }, { stroke: RED.h, sw: 1.2, d: rows(7, function (i) { var y = -20 + i * 7.4; return O([[-7.6, y + 5], [7.6, y]]); }) },
        { fill: GOLD.b, d: rect(-9, -28, 9, -20) + ' ' + rect(-9, 30, 9, 38) }
      ] };
  };

  /**
   * Trishula: Shiva's trident. A leaf-bladed centre prong and two side prongs that sweep out and
   * curl up like flames from a crescent; a gold kalasha socket; red ribbons; a long iron shaft.
   * Grip at the origin; the prongs top out near y = -(shaft + 180).
   */
  W.trishula = function (o) {
    o = o || {};
    var sh = o.shaft || 300, b0 = -sh, butt = o.butt === undefined ? 330 : o.butt;
    var centre = C([[0, b0 - 176, 1], [9, b0 - 150], [12, b0 - 118], [8, b0 - 92], [10, b0 - 66], [6, b0 - 44], [-6, b0 - 44], [-10, b0 - 66], [-8, b0 - 92], [-12, b0 - 118], [-9, b0 - 150]]);
    var side = function (sx) {
      var ch = [[sx * 10, b0 - 46], [sx * 34, b0 - 50], [sx * 52, b0 - 70], [sx * 56, b0 - 100], [sx * 50, b0 - 132], [sx * 38, b0 - 152]];
      return ribbon(ch, 8, 1.4, 7.4) + ' ' + C([[sx * 50, b0 - 108], [sx * 62, b0 - 112], [sx * 54, b0 - 96]]);
    };
    var crescent = ribbon([[-46, b0 - 62], [-30, b0 - 44], [0, b0 - 36], [30, b0 - 44], [46, b0 - 62]], 3, 3, 8);
    var kal = C([[-14, b0 - 40], [14, b0 - 40], [18, b0 - 26], [10, b0 - 10], [12, b0 + 6], [-12, b0 + 6], [-10, b0 - 10], [-18, b0 - 26]]);
    var shaft = rect(-3.6, b0, 3.6, butt);
    var steel = centre + ' ' + side(1) + ' ' + side(-1) + ' ' + crescent;
    var rib = function (sx) { return C([[sx * 4, b0 - 22], [sx * 26, b0 - 4], [sx * 40, b0 + 34], [sx * 30, b0 + 70, 1], [sx * 28, b0 + 34], [sx * 14, b0 + 6]]); };
    return { fill: STEEL.b, d: steel + ' ' + shaft,
      layers: [
        { clip: true, fill: STEEL.s, d: rect(0.6, b0 - 200, 80, butt + 10) },
        { clip: true, fill: STEEL.h, op: 0.8, d: C([[-1, b0 - 170], [-8, b0 - 140], [-9, b0 - 110], [-5, b0 - 60], [-1, b0 - 50]]) + ' ' + O([[-48, b0 - 70], [-52, b0 - 100], [-46, b0 - 128]]) },
        { stroke: STEEL.d, sw: 1, d: O([[0, b0 - 168], [0, b0 - 50]]) },
        { fill: '#3E4850', d: rect(-3.6, b0 + 40, 3.6, butt) },
        { fill: GOLD.b, d: rows(4, function (i) { var y = b0 + 60 + i * (butt - b0 - 90) / 3; return rect(-5.4, y, 5.4, y + 7); }) },
        { fill: RED.b, d: rib(1) + ' ' + rib(-1) }, { clip: rib(1) + ' ' + rib(-1), fill: RED.s, d: rect(0, b0 - 30, 60, b0 + 80) },
        { fill: GOLD.b, d: kal }, { clip: kal, fill: GOLD.s, d: rect(1, b0 - 50, 30, b0 + 10) }, { stroke: GOLD.d, sw: 1, d: kal },
        { fill: GOLD.h, d: E(-4, b0 - 26, 4, 6) }, { fill: RED.b, d: circ(0, b0 - 18, 3.6) }
      ] };
  };

  /** Damaru: the hourglass drum, its cord and two striker beads. Centre at the origin. */
  W.damaru = function (o) {
    o = o || {};
    var s = o.size || 1, hw = 20 * s, hh = 22 * s;
    var body = C([[-hw, -hh, 1], [hw, -hh, 1], [3 * s, 0], [hw, hh, 1], [-hw, hh, 1], [-3 * s, 0]]);
    return { fill: RED.b, d: body,
      layers: [
        { clip: true, fill: RED.s, d: rect(0, -hh - 2, hw + 2, hh + 2) },
        { fill: IVORY.b, d: E(0, -hh, hw, 4.6 * s) + ' ' + E(0, hh, hw, 4.6 * s) }, { stroke: INK, sw: 0.9, d: E(0, -hh, hw, 4.6 * s) + ' ' + E(0, hh, hw, 4.6 * s) },
        { stroke: IVORY.h, sw: 1, d: O([[-hw + 3, -hh + 4], [hw - 3, hh - 4]]) + ' ' + O([[hw - 3, -hh + 4], [-hw + 3, hh - 4]]) },
        { fill: GOLD.b, d: rect(-5 * s, -3 * s, 5 * s, 3 * s) },
        { stroke: '#7A4A26', sw: 1.2, d: O([[4 * s, 0], [18 * s, 6 * s], [28 * s, 14 * s]]) + ' ' + O([[-4 * s, 0], [-18 * s, 6 * s], [-28 * s, 12 * s]]) },
        { fill: '#3B2618', d: circ(29 * s, 15 * s, 3.4 * s) + ' ' + circ(-29 * s, 13 * s, 3.4 * s) },
        { stroke: RED.b, sw: 2, d: O([[0, 3 * s], [-4 * s, 20 * s], [2 * s, 36 * s]]) }
      ] };
  };

  /** Ankusha: the goad, a spike and a back-curving hook on a short gold shaft. Grip at the origin. */
  W.ankusha = function (o) {
    o = o || {};
    var sh = o.shaft || 90;
    var spike = C([[0, -sh - 64, 1], [5, -sh - 36], [5, -sh - 8], [-5, -sh - 8], [-5, -sh - 36]]);
    var hook = ribbon([[-4, -sh - 22], [-22, -sh - 30], [-34, -sh - 18], [-34, -sh + 2], [-24, -sh + 14]], 5, 1.2, 4.6);
    var knob = E(0, -sh - 4, 9, 7);
    var shaft = rect(-3.6, -sh, 3.6, 40) + ' ' + circ(0, 46, 7);
    return { fill: GOLD.b, d: spike + ' ' + hook + ' ' + knob + ' ' + shaft,
      layers: [{ clip: true, fill: GOLD.s, d: rect(0.5, -sh - 80, 40, 60) }, { clip: true, fill: GOLD.h, op: 0.8, d: C([[-1, -sh - 60], [-4, -sh - 36], [-1, -sh - 10]]) },
        { fill: RED.b, d: circ(0, -sh - 4, 3.4) }, { stroke: GOLD.d, sw: 1, d: rows(4, function (i) { var y = -sh + 18 + i * 26; return O([[-4, y], [4, y + 3]]); }) }] };
  };

  /** Pasha: the noose, a looped rope with a knot and a tassel. Knot at the origin. */
  W.pasha = function (o) {
    o = o || {};
    var r = o.r || 24, cy = -r - 10;
    var loop = E(0, cy, r, r * 1.2) + ' ' + E(0, cy, r - 5, r * 1.2 - 5);
    var tail = ribbon([[0, -6], [8, 16], [2, 40], [10, 62]], 3, 2.2);
    return { fill: '#C9962E', rule: 'evenodd', d: loop + ' ' + tail + ' ' + E(0, -4, 8, 7) + ' ' + C([[10, 58], [18, 84, 1], [4, 84, 1]]),
      layers: [{ stroke: '#8A6420', sw: 0.9, d: rows(18, function (i) { var a = Math.PI * 2 * i / 18; return O([[Math.cos(a) * (r - 5), cy + Math.sin(a) * (r * 1.2 - 5)], [Math.cos(a + 0.22) * r, cy + Math.sin(a + 0.22) * r * 1.2]]); }) },
        { fill: RED.b, d: C([[10, 60], [18, 86, 1], [4, 86, 1]]) }] };
  };

  /** Parashu: the axe, a crescent blade with a back spike. Grip at the origin. */
  W.parashu = function (o) {
    o = o || {};
    var sh = o.shaft || 150, s = o.size || 1;
    var blade = C([[4, -sh - 6], [26 * s, -sh - 30 * s], [46 * s, -sh - 40 * s, 1], [42 * s, -sh - 8 * s], [46 * s, -sh + 24 * s, 1], [26 * s, -sh + 16 * s], [4, -sh + 8]]);
    var spike = C([[-4, -sh - 6], [-24 * s, -sh - 2], [-4, -sh + 4]]);
    return { fill: STEEL.b, d: blade + ' ' + spike + ' ' + rect(-3.6, -sh - 14, 3.6, 50),
      layers: [{ clip: true, fill: STEEL.s, d: rect(-60, -sh + 2, 70, 60) }, { clip: true, fill: STEEL.h, d: O([[42 * s, -sh - 34 * s], [38 * s, -sh - 8 * s], [42 * s, -sh + 18 * s]]) },
        { fill: WOOD.b, d: rect(-3.6, -sh + 10, 3.6, 50) }, { fill: GOLD.b, d: rect(-5.4, -sh - 16, 5.4, -sh + 12) }] };
  };

  /** Sudarshana chakra: a serrated spinning disc with spokes and flame tips. Centre at the origin. */
  W.chakra = function (o) {
    o = o || {};
    var r = o.r || 46, n = 24, pts = [];
    for (var i = 0; i < n * 2; i++) { var a = Math.PI * i / n, rr = i % 2 ? r * 0.84 : r; pts.push([Math.cos(a) * rr, Math.sin(a) * rr, i % 2 ? 0 : 1]); }
    var disc = C(pts) + ' ' + circ(0, 0, r * 0.5);
    var spokes = rows(8, function (i) { var a = Math.PI * i / 4; return O([[Math.cos(a) * r * 0.16, Math.sin(a) * r * 0.16], [Math.cos(a) * r * 0.5, Math.sin(a) * r * 0.5]]); });
    return { fill: GOLD.b, rule: 'evenodd', d: disc + ' ' + circ(0, 0, r * 0.16),
      layers: [{ fill: { radial: [[0, '#FFF3C4', 0.9], [1, '#FFB547', 0]], cx: 0, cy: 0, r: r * 1.5 }, d: circ(0, 0, r * 1.5) },
        { clip: true, fill: GOLD.s, d: rect(0, -r - 4, r + 4, r + 4) }, { stroke: GOLD.d, sw: 1.6, d: spokes }, { stroke: GOLD.d, sw: 1, d: circ(0, 0, r * 0.72) },
        { fill: RED.b, d: circ(0, 0, r * 0.1) }] };
  };

  /** Shankha: the conch, spiral to the top, lip to the right. Centre at the origin. */
  W.shankha = function (o) {
    o = o || {};
    var s = o.size || 1;
    var shell = C([[-10 * s, -34 * s, 1], [6 * s, -28 * s], [20 * s, -12 * s], [26 * s, 10 * s], [18 * s, 30 * s], [4 * s, 38 * s, 1], [-10 * s, 26 * s], [-16 * s, 4 * s], [-16 * s, -18 * s]]);
    return { fill: IVORY.b, d: shell,
      layers: [{ clip: true, fill: IVORY.s, d: rect(4 * s, -40 * s, 40 * s, 40 * s) }, { stroke: IVORY.s, sw: 1.2, d: rows(4, function (i) { var y = (-22 + i * 10) * s; return O([[-14 * s, y], [0, y + 4 * s], [18 * s, y - 2 * s]]); }) },
        { fill: '#E9B8A6', d: C([[6 * s, -8 * s], [20 * s, 6 * s], [12 * s, 28 * s], [4 * s, 12 * s]]) }, { fill: GOLD.b, d: rect(-14 * s, -36 * s, -4 * s, -30 * s) }] };
  };

  /** Vajra: the double-ended thunderbolt (Indra), five prongs at each end. Centre at the origin. */
  W.vajra = function (o) {
    o = o || {};
    var s = o.size || 1, L = 60 * s;
    var end = function (sy) {
      var p = [];
      [-1, -0.5, 0.5, 1].forEach(function (q) { p.push(ribbon([[q * 4 * s, sy * 12 * s], [q * 18 * s, sy * 30 * s], [q * 10 * s, sy * (L - 6 * s)], [0, sy * L]], 2.6 * s, 1, 3 * s)); });
      p.push(C([[0, sy * (L + 6 * s), 1], [3 * s, sy * 20 * s], [-3 * s, sy * 20 * s]]));
      return p.join(' ');
    };
    return { fill: GOLD.b, d: end(-1) + ' ' + end(1) + ' ' + E(0, 0, 9 * s, 8 * s) + ' ' + E(0, -12 * s, 10 * s, 4 * s) + ' ' + E(0, 12 * s, 10 * s, 4 * s),
      layers: [{ clip: true, fill: GOLD.s, d: rect(0.5, -L - 10, L, L + 10) }, { fill: RED.b, d: circ(0, 0, 3.6 * s) }] };
  };

  /** Khadga: a straight broad sword. Grip at the origin. */
  W.khadga = function (o) {
    o = o || {};
    var L = o.len || 220;
    var blade = C([[-8, -18], [8, -18], [11, -L * 0.8], [6, -L, 1], [-10, -L + 10], [-11, -L * 0.8]]);
    return { fill: STEEL.b, d: blade + ' ' + rect(-22, -18, 22, -10) + ' ' + rect(-4, -10, 4, 26) + ' ' + circ(0, 32, 7),
      layers: [{ clip: true, fill: STEEL.s, d: rect(0, -L - 4, 20, -18) }, { stroke: STEEL.d, sw: 1, d: O([[0, -24], [0, -L + 14]]) },
        { fill: GOLD.b, d: rect(-22, -18, 22, -10) + ' ' + circ(0, 32, 7) }, { fill: RED.b, d: rect(-4, -10, 4, 26) }] };
  };

  /** Venu: Krishna's flute, held level; the origin at its centre. */
  W.venu = function (o) {
    o = o || {};
    var L = o.len || 150;
    return { fill: '#C9A060', d: rect(-L / 2, -4, L / 2, 4),
      layers: [{ clip: true, fill: '#A27E42', d: rect(-L / 2, 0, L / 2, 5) }, { fill: '#3B2618', d: rows(6, function (i) { return E(-L / 2 + 30 + i * 14, -0.5, 2.2, 1.6); }) },
        { fill: GOLD.b, d: rect(-L / 2, -4.6, -L / 2 + 6, 4.6) + ' ' + rect(L / 2 - 6, -4.6, L / 2, 4.6) }] };
  };

  /** Padma: a held lotus on its stalk. Grip at the origin. */
  W.padma = function (o) {
    o = o || {};
    var st = o.stalk || 70, cy = -st - 16;
    var petals = [-2, -1, 0, 1, 2].map(function (i) { return C([[i * 9, cy + 16], [i * 13 - 9, cy - 8], [i * 12, cy - 26 + Math.abs(i) * 6, 1], [i * 13 + 9, cy - 8]]); }).join(' ');
    return { fill: '#E8A3A0', d: petals + ' ' + ribbon([[0, 30], [3, -st / 2], [0, cy + 14]], 2.4, 2.4),
      layers: [{ fill: '#4F7A55', d: ribbon([[0, 30], [3, -st / 2], [0, cy + 14]], 2.4, 2.4) }, { stroke: '#B8645E', sw: 0.9, d: petals }, { fill: '#F6CFC9', op: 0.8, d: C([[-2, cy + 14], [-8, cy - 6], [0, cy - 26, 1], [2, cy - 4]]) }] };
  };

  // ------------------------------------------------------------------ Greek and Norse
  /** Dory: a hoplite spear, leaf blade with a midrib, socket, ash shaft, sauroter butt-spike. Grip at the origin. */
  W.dory = function (o) {
    o = o || {};
    var up = o.up || 520, down = o.down || 300, B = BRONZE;
    var blade = C([[0, -up - 92, 1], [12, -up - 52], [10, -up - 22], [5, -up - 6], [-5, -up - 6], [-10, -up - 22], [-12, -up - 52]]);
    var socket = C([[-5, -up - 8], [5, -up - 8], [4.2, -up + 20], [-4.2, -up + 20]]);
    var saur = C([[-4.4, down - 50], [4.4, down - 50], [3, down - 6], [0, down + 10, 1], [-3, down - 6]]);
    return { fill: '#8C6440', d: blade + ' ' + socket + ' ' + rect(-3, -up + 18, 3, down - 48) + ' ' + saur,
      layers: [{ fill: B.b, d: blade + ' ' + socket + ' ' + saur }, { clip: blade, fill: B.s, d: rect(0, -up - 100, 20, -up) }, { clip: blade, fill: B.h, d: C([[0, -up - 88], [-9, -up - 52], [-4, -up - 10], [-1, -up - 10]]) },
        { stroke: B.d, sw: 1, d: O([[0, -up - 86], [0, -up - 8]]) }, { clip: true, fill: WOOD.s, op: 0.5, d: rect(0.5, -up + 20, 6, down - 48) },
        { stroke: B.d, sw: 0.9, d: blade + ' ' + saur }, { fill: B.b, d: rect(-3.6, -2, 3.6, 18) }] };
  };

  /**
   * Aspis: the round hoplite shield seen face on, bronze rim with a meander band, a field with
   * concentric rings and the gorgoneion (Athena Parthenos) at the centre. Centre at the origin.
   */
  W.aspis = function (o) {
    o = o || {};
    var r = o.r || 110, field = o.field || '#2F4C6E', B = BRONZE;
    var mean = '';
    for (var i = 0; i < 28; i++) { var a = Math.PI * 2 * i / 28, a2 = a + Math.PI * 2 / 28 * 0.6, r1 = r - 13, r2 = r - 5; mean += O([[Math.cos(a) * r1, Math.sin(a) * r1], [Math.cos(a) * r2, Math.sin(a) * r2], [Math.cos(a2) * r2, Math.sin(a2) * r2], [Math.cos(a2) * (r1 + 3), Math.sin(a2) * (r1 + 3)]], 0) + ' '; }
    var snakes = rows(12, function (i) { var a = Math.PI * 2 * i / 12, c = Math.cos(a), s = Math.sin(a); return O([[c * 20, s * 22], [c * 26 - s * 4, s * 28 + c * 4], [c * 30 + s * 3, s * 33 - c * 3], [c * 35, s * 37]]); });
    return { fill: B.b, d: circ(0, 0, r),
      layers: [
        { fill: field, d: circ(0, 0, r - 18) }, { clip: circ(0, 0, r - 18), fill: '#24405E', d: C([[r * 0.1, -r], [r, -r], [r, r], [r * 0.2, r], [r * 0.6, 0]]) },
        { stroke: B.b, sw: 1.4, op: 0.55, d: circ(0, 0, r * 0.62) + ' ' + circ(0, 0, r * 0.44) },
        { clip: true, fill: B.s, d: C([[r * 0.2, -r - 4], [r + 4, -r - 4], [r + 4, r + 4], [r * 0.3, r + 4], [r * 0.95, 0]]) },
        { stroke: B.d, sw: 1, d: mean },
        { clip: true, fill: B.h, op: 0.55, d: C([[-r * 0.98, -r * 0.1], [-r * 0.7, -r * 0.7], [-r * 0.1, -r * 0.98], [-r * 0.1, -r * 0.88], [-r * 0.64, -r * 0.6], [-r * 0.88, -r * 0.08]]) },
        // Gorgoneion: a round face, wide eyes, snakes for hair.
        { stroke: '#3F6B4A', sw: 2.4, d: snakes }, { fill: '#E8CFA8', d: E(0, 0, 21, 23) }, { clip: E(0, 0, 21, 23), fill: '#C9A67C', d: rect(2, -24, 24, 24) },
        { fill: INK, d: E(-7, -4, 3, 3.6) + ' ' + E(7, -4, 3, 3.6) + ' ' + E(0, 11, 6, 3.4) },
        { stroke: INK, sw: 1, d: O([[-12, -11], [-6, -13], [-2, -10]]) + ' ' + O([[2, -10], [6, -13], [12, -11]]) },
        { stroke: B.d, sw: 1.2, d: circ(0, 0, r - 18) + ' ' + E(0, 0, 21, 23) }
      ] };
  };

  /**
   * Gungnir: Odin's spear (Skaldskaparmal: made by the sons of Ivaldi; runes cut on its point,
   * Sigrdrifumal 17). A long pattern-welded leaf blade with a fuller and incised knotwork, winged
   * lugs at a gold-bound socket, a dark ash shaft. Grip at the origin. No hate-appropriated runes.
   */
  W.gungnir = function (o) {
    o = o || {};
    var up = o.up || 470, down = o.down || 330, S2 = STEEL;
    var base = -up;
    var blade = C([[0, base - 196, 1], [14, base - 150], [18, base - 96], [14, base - 48], [7, base - 20], [-7, base - 20], [-14, base - 48], [-18, base - 96], [-14, base - 150]]);
    var socket = C([[-7, base - 22], [7, base - 22], [6, base + 34], [-6, base + 34]]);
    var wings = C([[-6, base + 8], [-24, base + 2], [-22, base + 16], [-6, base + 18]]) + ' ' + C([[6, base + 8], [24, base + 2], [22, base + 16], [6, base + 18]]);
    var weld = rows(5, function (i) { var y = base - 160 + i * 26; return O([[-6, y], [-2, y - 6], [2, y], [6, y - 6]]); });
    var marks = rows(4, function (i) { var y = base - 136 + i * 22; return O([[-2.4, y], [-2.4, y + 12]]) + ' ' + O([[-2.4, y + 3], [2.4, y + 8]]); });
    var glow = o.glow ? [{ fill: { radial: [[0, '#F2F8FF', 0.9], [0.5, '#B8D8F4', 0.5], [1, '#8CB4DC', 0]], cx: 0, cy: base - 100, r: 90 }, d: E(0, base - 100, 60, 120) }] : [];
    return { fill: S2.b, d: blade + ' ' + socket + ' ' + wings + ' ' + rect(-3.6, base + 32, 3.6, down) + ' ' + C([[-4, down], [4, down], [0, down + 18, 1]]),
      layers: glow.concat([
        { clip: blade, fill: S2.s, d: rect(0, base - 200, 30, base) }, { clip: blade, fill: S2.h, d: C([[0, base - 190], [-12, base - 120], [-12, base - 60], [-2, base - 24]]) },
        { clip: blade, stroke: S2.d, sw: 1, op: 0.45, d: weld },
        { fill: '#3E4850', d: C([[0, base - 176], [3, base - 120], [3, base - 34], [-3, base - 34], [-3, base - 120]]) },
        { stroke: GOLD.h, sw: 1.1, d: marks },
        { stroke: S2.d, sw: 1, d: blade },
        { fill: WOOD.d, d: rect(-3.6, base + 32, 3.6, down) }, { clip: true, fill: '#5A4030', d: rect(-3.6, base + 32, -1, down) },
        { fill: GOLD.b, d: rect(-7.4, base - 4, 7.4, base + 4) + ' ' + rect(-7, base + 24, 7, base + 34) + ' ' + rect(-5, -24, 5, -18) + ' ' + rect(-5, 20, 5, 26) },
        { stroke: GOLD.d, sw: 0.9, d: O([[-6, base + 12], [6, base + 18]]) + ' ' + O([[-6, base + 18], [6, base + 12]]) }
      ]) };
  };

  /** Mjolnir: Thor's hammer, a flared head and a short handle with a thong (Skaldskaparmal 35). Grip at the origin. */
  W.mjolnir = function (o) {
    o = o || {};
    var head = C([[-58, -96, 1], [58, -96, 1], [50, -70], [62, -40, 1], [-62, -40, 1], [-50, -70]]);
    return { fill: STEEL.s, d: head + ' ' + rect(-7, -42, 7, 36) + ' ' + E(0, 52, 9, 14),
      layers: [{ clip: head, fill: STEEL.b, d: rect(-70, -100, 10, -36) }, { clip: head, fill: STEEL.h, d: rect(-60, -96, 40, -88) },
        { stroke: GOLD.b, sw: 1.4, d: O([[-30, -80], [-18, -60], [0, -76], [18, -60], [30, -80]]) + ' ' + circ(0, -68, 7) },
        { fill: WOOD.b, d: rect(-7, -42, 7, 36) }, { stroke: '#C9A060', sw: 1.2, d: rows(8, function (i) { var y = -36 + i * 8.6; return O([[-7, y + 5], [7, y]]); }) },
        { stroke: '#5A3E26', sw: 2.2, d: O([[0, 64], [-14, 86], [4, 96]]) }] };
  };

  /** Keraunos: Zeus's thunderbolt as Greek art draws it, a spindle with forked zigzag flames at both ends. */
  W.keraunos = function (o) {
    o = o || {};
    var s = o.size || 1;
    var end = function (sy) {
      return [-1, 0, 1].map(function (q) {
        var x = q * 14 * s;
        return C([[q * 4 * s, sy * 16 * s], [x + 6 * s, sy * 34 * s], [x - 6 * s, sy * 44 * s], [x + 8 * s, sy * 60 * s], [x + q * 6 * s, sy * (82 - Math.abs(q) * 10) * s, 1], [x - 2 * s, sy * 58 * s], [x - 14 * s, sy * 46 * s], [x - 4 * s, sy * 34 * s], [q * 4 * s - 4 * s, sy * 16 * s]]);
      }).join(' ');
    };
    return { fill: GOLD.b, d: end(-1) + ' ' + end(1) + ' ' + E(0, 0, 8 * s, 18 * s),
      layers: [{ fill: { radial: [[0, '#FFF6D8', 0.85], [1, '#9CC3FF', 0]], cx: 0, cy: 0, r: 100 * s }, d: circ(0, 0, 100 * s) },
        { clip: true, fill: GOLD.s, d: rect(0.5, -100, 60, 100) }, { stroke: GOLD.d, sw: 1, d: O([[-8 * s, -6 * s], [8 * s, 6 * s]]) + ' ' + O([[-8 * s, 6 * s], [8 * s, -6 * s]]) }] };
  };

  // ------------------------------------------------------------------ placement
  /**
   * Place a weapon spec in a figure: o {id, parent, at: [x, y] (the grip in figure units), angle
   * (degrees, clockwise from upright), scale, flip (mirror left-right), behind, pivot}. Returns the
   * part list (the weapon and its extras). The pivot defaults to the grip.
   */
  function place(spec, o) {
    o = o || {};
    var at = o.at || [0, 0], sc = o.scale || 1;
    var tf = 'translate(' + f1(at[0]) + ' ' + f1(at[1]) + ') rotate(' + f1(o.angle || 0) + ') scale(' + (o.flip ? -sc : sc) + ' ' + sc + ')';
    var main = { id: o.id, parent: o.parent, behind: !!o.behind, pivot: o.pivot || at, tf: tf, fill: spec.fill, d: spec.d, rule: spec.rule, layers: spec.layers, sw: o.sw || 0.8 };
    var out = [main];
    (spec.extra || []).forEach(function (x) {
      out.push({ id: o.id + '-' + x.suffix, parent: o.id, behind: !!x.behind, pivot: at, fill: x.fill, d: x.d, rule: x.rule, layers: x.layers, sw: 0.7 });
    });
    return out;
  }

  M.weapons = W;
  W.place = place;
  W.palettes = WP;
  W.ids = ['kodanda', 'shara', 'tuna', 'gada', 'trishula', 'damaru', 'ankusha', 'pasha', 'parashu', 'chakra', 'shankha', 'vajra', 'khadga', 'venu', 'padma', 'dory', 'aspis', 'gungnir', 'mjolnir', 'keraunos'];

  // ------------------------------------------------------------------ auras
  /**
   * Auras behind a figure (kept in every look). make(kind, {cx, cy, r}) returns parts drawn first
   * (deepest): 'aura' (the glow), 'aura-ring' and 'aura-rays' (children, rotatable about the centre:
   * M.turn on p.part('aura-rays')). Kinds:
   *   tejas   - Rama: a sun disc, long and short rays and a fine gold ring (radiance, tejas)
   *   agni    - Hanuman: a blaze of flame tongues around a hot glow
   *   cosmic  - Shiva: a night-blue disc with stars inside a ring of fire (Nataraja's prabha)
   *   lotus   - Ganesha: a gold glow, a lotus-petal mandala and short rays
   *   radiant - Athena: white-gold light and fine long rays (no ring: Greek gods have no halo)
   *   storm   - Odin: a cold storm-light with wind arcs
   *   calm    - a quiet plain disc (seated teachers)
   */
  function flames(cx, cy, r0, r1, n, phase) {
    var pts = [];
    for (var i = 0; i < n; i++) {
      var a = Math.PI * 2 * (i + (phase || 0)) / n, b = Math.PI * 2 * (i + 0.5 + (phase || 0)) / n, c = Math.PI * 2 * (i + 1 + (phase || 0)) / n;
      var tip = r1 * (i % 3 === 0 ? 1 : i % 3 === 1 ? 0.86 : 0.93);
      pts.push([cx + Math.cos(a) * r0, cy + Math.sin(a) * r0, 1]);
      pts.push([cx + Math.cos(a + (b - a) * 0.6) * (r0 + (tip - r0) * 0.55), cy + Math.sin(a + (b - a) * 0.6) * (r0 + (tip - r0) * 0.55)]);
      pts.push([cx + Math.cos(b + (c - b) * 0.3) * tip, cy + Math.sin(b + (c - b) * 0.3) * tip, 1]);
      pts.push([cx + Math.cos(b + (c - b) * 0.55) * (r0 + (tip - r0) * 0.5), cy + Math.sin(b + (c - b) * 0.55) * (r0 + (tip - r0) * 0.5)]);
    }
    return C(pts, 0.8);
  }
  function rays(cx, cy, r0, r1, n, w, alt) {
    return rows(n, function (i) {
      var a = Math.PI * 2 * i / n, L = alt && i % 2 ? r0 + (r1 - r0) * 0.62 : r1, ww = (alt && i % 2 ? w * 0.7 : w) / r0;
      return C([[cx + Math.cos(a - ww) * r0, cy + Math.sin(a - ww) * r0, 1], [cx + Math.cos(a) * L, cy + Math.sin(a) * L, 1], [cx + Math.cos(a + ww) * r0, cy + Math.sin(a + ww) * r0, 1]]);
    });
  }
  var AURA = {
    tejas: { glow: [[0, '#FFF7DC', 0.95], [0.42, '#FFE08A', 0.75], [0.72, '#F6B94E', 0.32], [1, '#F2A93C', 0]], ray: '#E9A93A', ring: '#C9962E' },
    agni: { glow: [[0, '#FFF0C8', 0.95], [0.38, '#FFC05A', 0.8], [0.7, '#F0743A', 0.42], [1, '#E0502A', 0]], flame: ['#E4572E', '#F59A3A', '#FFD166'] },
    cosmic: { glow: [[0, '#4A4C8E', 0.95], [0.6, '#2E3268', 0.92], [0.86, '#3E3A72', 0.6], [1, '#5B4B8A', 0]], flame: ['#E4572E', '#F59A3A', '#FFD166'] },
    lotus: { glow: [[0, '#FFF4D6', 0.95], [0.5, '#FFD98A', 0.6], [1, '#F3B35A', 0]], petal: '#E8A3A0', ray: '#E9A93A' },
    radiant: { glow: [[0, '#FFFFFF', 0.95], [0.45, '#FFF1C8', 0.7], [0.8, '#F8DA92', 0.25], [1, '#F2C46A', 0]], ray: '#F0C86A' },
    storm: { glow: [[0, '#E6EEF6', 0.9], [0.5, '#B8C8DC', 0.6], [0.85, '#7C8EA8', 0.22], [1, '#5E6E88', 0]], wind: '#7C8EA8' },
    calm: { glow: [[0, '#FFF6DE', 0.9], [0.7, '#F6DFA8', 0.5], [1, '#F2D08A', 0]] }
  };
  function makeAura(kind, o) {
    o = o || {};
    var A = AURA[kind] || AURA.tejas, cx = o.cx === undefined ? 200 : o.cx, cy = o.cy === undefined ? 200 : o.cy, r = o.r || 220;
    var glow = { radial: A.glow, cx: cx, cy: cy, r: r };
    var parts = [{ id: 'aura', keep: true, outline: false, pivot: [cx, cy], fill: glow, d: circ(cx, cy, r), layers: [] }];
    var ring = { id: 'aura-ring', parent: 'aura', keep: true, outline: false, pivot: [cx, cy], fill: 'none', d: 'M0 0Z', layers: [] };
    var ry = { id: 'aura-rays', parent: 'aura', behind: true, keep: true, outline: false, pivot: [cx, cy], fill: 'none', d: 'M0 0Z', layers: [] };
    if (kind === 'tejas') {
      ry.layers.push({ fill: A.ray, op: 0.42, d: rays(cx, cy, r * 0.42, r * 0.98, 24, 9, true) });
      ring.layers.push({ stroke: A.ring, sw: 2.4, op: 0.85, d: circ(cx, cy, r * 0.46) }, { stroke: A.ring, sw: 1, op: 0.6, d: circ(cx, cy, r * 0.5) },
        { fill: A.ring, op: 0.7, d: rows(24, function (i) { var a = Math.PI * 2 * i / 24; return circ(cx + Math.cos(a) * r * 0.48, cy + Math.sin(a) * r * 0.48, 2.2); }) });
    } else if (kind === 'agni') {
      ry.layers.push({ fill: A.flame[0], op: 0.75, d: flames(cx, cy, r * 0.5, r * 0.98, 22, 0) }, { fill: A.flame[1], op: 0.8, d: flames(cx, cy, r * 0.46, r * 0.84, 22, 0.5) }, { fill: A.flame[2], op: 0.7, d: flames(cx, cy, r * 0.42, r * 0.66, 22, 0.25) });
    } else if (kind === 'cosmic') {
      var stars = '';
      for (var i = 0; i < 46; i++) { var a = i * 2.399963, rr = r * 0.66 * Math.sqrt((i + 0.5) / 46); stars += circ(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr, i % 7 === 0 ? 2.2 : 1.1) + ' '; }
      parts[0].layers.push({ fill: '#F4EEDF', op: 0.85, d: stars });
      // Thirteen tongues of flame on the ring, as on the Chola Nataraja prabhavali (Salar Jung Museum).
      ring.layers.push({ fill: A.flame[0], op: 0.9, d: flames(cx, cy, r * 0.7, r * 0.98, 13, 0) + ' ' + circ(cx, cy, r * 0.68), rule: 'evenodd' },
        { fill: A.flame[1], d: flames(cx, cy, r * 0.7, r * 0.88, 13, 0.5) + ' ' + circ(cx, cy, r * 0.69), rule: 'evenodd' },
        { fill: A.flame[2], op: 0.9, d: flames(cx, cy, r * 0.7, r * 0.8, 26, 0.25) + ' ' + circ(cx, cy, r * 0.695), rule: 'evenodd' },
        { stroke: '#FFD166', sw: 2.4, d: circ(cx, cy, r * 0.71) });
    } else if (kind === 'lotus') {
      var pet = rows(16, function (i) {
        var a = Math.PI * 2 * i / 16, c = Math.cos(a), s = Math.sin(a), r0 = r * 0.46, r1 = r * 0.7, w = r * 0.09;
        return C([[cx + c * r0 - s * w, cy + s * r0 + c * w], [cx + c * (r0 + r1) / 2 - s * w * 1.2, cy + s * (r0 + r1) / 2 + c * w * 1.2], [cx + c * r1, cy + s * r1, 1], [cx + c * (r0 + r1) / 2 + s * w * 1.2, cy + s * (r0 + r1) / 2 - c * w * 1.2], [cx + c * r0 + s * w, cy + s * r0 - c * w]]);
      });
      ry.layers.push({ fill: A.ray, op: 0.35, d: rays(cx, cy, r * 0.7, r * 0.98, 32, 5, true) });
      ring.layers.push({ fill: A.petal, op: 0.55, d: pet }, { stroke: '#C2786F', sw: 1, op: 0.7, d: pet }, { stroke: '#C9962E', sw: 2, op: 0.8, d: circ(cx, cy, r * 0.45) });
    } else if (kind === 'radiant') {
      ry.layers.push({ fill: A.ray, op: 0.4, d: rays(cx, cy, r * 0.3, r, 48, 3.4, true) });
    } else if (kind === 'storm') {
      var arcs = '';
      for (var k = 0; k < 9; k++) {
        var a0 = k * 0.698 + 0.3, rr0 = r * (0.5 + (k % 3) * 0.14), pts = [];
        for (var j = 0; j <= 8; j++) { var t = a0 + j * 0.16; pts.push([cx + Math.cos(t) * rr0 * (1 + j * 0.025), cy + Math.sin(t) * rr0 * 0.8 * (1 + j * 0.025)]); }
        arcs += O(pts) + ' ';
      }
      ry.layers.push({ stroke: A.wind, sw: 2.2, op: 0.55, d: arcs });
    } else if (kind === 'calm') {
      ring.layers.push({ stroke: '#C9962E', sw: 1.6, op: 0.7, d: circ(cx, cy, r * 0.62) });
    }
    return parts.concat([ry, ring]);
  }
  M.auras = { make: makeAura, kinds: Object.keys(AURA), palettes: AURA, flames: flames, rays: rays };
})(typeof window !== 'undefined' ? window : this);
