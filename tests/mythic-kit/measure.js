/*
 * tests/mythic-kit/measure.js - measure a drawn human figure against the figure canon.
 *
 * Reads landmarks off the rendered geometry (part bounding boxes and point-in-fill row scans),
 * expressed in head units (H = skull top to chin), and compares them with the canon in
 * .claude/skills/mythic-tales/references/figure-design.md section 8 (Loomis, "Figure Drawing for
 * All It's Worth": nipples 2H, navel 3H, crotch 4H from the top; elbows on the navel line; wrist
 * just below the crotch; shoulders 2 1/3 H; waist a little over 1H; hips 1.5H). QA only: never
 * loaded by a composition. Used by proportions.html (overlay sheet) and index.html (tests).
 */
(function (global) {
  'use strict';

  // Targets per body type: [min, max]. Vertical values are head units from the skull top.
  var CANON = {
    male: { heads: [8, 8.8], nipple: [1.9, 2.15], waist: [2.7, 3.1], elbow: [2.75, 3.25], crotch: [3.9, 4.25], knee: [5.8, 6.4], wrist: [3.9, 4.4],
      shoulderW: [2.3, 2.6], waistW: [1.05, 1.3], hipW: [1.45, 1.75] },
    titan: { heads: [7.4, 8.2], nipple: [1.85, 2.15], waist: [2.65, 3.05], elbow: [2.7, 3.25], crotch: [3.7, 4.15], knee: [5.4, 6.1], wrist: [3.7, 4.3],
      shoulderW: [2.45, 3.0], waistW: [1.25, 1.55], hipW: [1.6, 1.95] },
    female: { heads: [7.8, 8.6], nipple: [1.9, 2.2], waist: [2.65, 3.05], elbow: [2.7, 3.2], crotch: [3.9, 4.25], knee: [5.8, 6.4], wrist: [3.9, 4.4],
      shoulderW: [1.9, 2.2], waistW: [0.95, 1.2], hipW: [1.45, 1.75] }
  };

  function baseOf(pup, id) {
    var outer = pup.part(id);
    if (!outer) return null;
    var host = outer.querySelector(':scope > g[transform]') || outer;
    return host.querySelector(':scope > path');
  }
  /** Bounding box of a part's own shape in viewBox units (transforms included). */
  function box(pup, id) {
    var el = baseOf(pup, id);
    if (!el) return null;
    var r = el.getBoundingClientRect(), inv = pup.art.getScreenCTM().inverse();
    var a = new DOMPoint(r.left, r.top).matrixTransform(inv), b = new DOMPoint(r.right, r.bottom).matrixTransform(inv);
    return { x0: a.x, y0: a.y, x1: b.x, y1: b.y };
  }
  /** Leftmost and rightmost filled x at height y across the given parts (viewBox units). */
  function row(pup, ids, y, step, xmin, xmax) {
    var ctm = pup.art.getScreenCTM(), els = ids.map(function (id) { return baseOf(pup, id); }).filter(Boolean);
    var invs = els.map(function (el) { return el.getScreenCTM().inverse(); });
    var lo = null, hi = null;
    for (var x = xmin === undefined ? -100 : xmin; x <= (xmax === undefined ? 500 : xmax); x += step || 1) {
      var sp = new DOMPoint(x, y).matrixTransform(ctm);
      for (var i = 0; i < els.length; i++) {
        if (els[i].isPointInFill(sp.matrixTransform(invs[i]))) { if (lo === null) lo = x; hi = x; break; }
      }
    }
    return lo === null ? null : { x0: lo, x1: hi, w: hi - lo };
  }

  /** Measure a standing human puppet. type 'male' | 'titan' | 'female'. */
  function measure(pup, type) {
    var head = box(pup, 'head'), H = head.y1 - head.y0, top = head.y0;
    var legs = ['leg-r', 'leg-l'].map(function (id) { return box(pup, id); });
    var sole = Math.max(legs[0].y1, legs[1].y1);
    var u = function (y) { return (y - top) / H; };
    var crotchY = pup.pivots['leg-r'][1] + 10;
    var res = { H: H, top: top, sole: sole, heads: (sole - top) / H, crotch: u(crotchY) };
    // Shoulder width, deltoid to deltoid: the outer edges of torso + upper arm close to each shoulder
    // joint (within 0.6 H outward), so the measure holds in any pose (raised, folded or hanging arms).
    var jR = pup.pivots['arm-r'], jL = pup.pivots['arm-l'], sw = 0;
    for (var dy = -4; dy <= 16; dy += 4) {
      var rr = row(pup, ['torso', 'arm-r'], jR[1] + dy, 1, jR[0] - 0.6 * H, jR[0]);
      var rl = row(pup, ['torso', 'arm-l'], jL[1] + dy, 1, jL[0], jL[0] + 0.6 * H);
      if (rr && rl && rl.x1 - rr.x0 > sw) sw = rl.x1 - rr.x0;
    }
    res.shoulderW = sw / H;
    // Waist: the narrowest torso row between 2.4H and 3.3H.
    var best = null, tb = box(pup, 'torso'), yEnd = Math.min(top + 3.3 * H, tb.y1 - 10);
    for (var y = top + 2.4 * H; y <= yEnd; y += 2) { var r2 = row(pup, ['torso'], y, 1); if (r2 && (!best || r2.w < best.w)) best = { y: y, w: r2.w }; }
    res.waist = best ? u(best.y) : null; res.waistW = best ? best.w / H : null;
    // Nipples: the bottom of the pectoral shadow is not measurable from the outline; use the declared line.
    res.nipple = u(pup.meta.landmarks ? pup.meta.landmarks.nipple : 266);
    // Hips: width of both thighs (and the pelvis if it is skin) just below the crotch.
    var hr = row(pup, ['leg-r', 'leg-l'], crotchY + 0.1 * H, 1);
    res.hipW = hr ? hr.w / H : null;
    // Knee: the narrowest leg row in the middle of the leg (right leg).
    var kb = null, L = sole - crotchY;
    for (var yk = crotchY + 0.38 * L; yk <= crotchY + 0.62 * L; yk += 2) { var rk = row(pup, ['leg-r'], yk, 1); if (rk && (!kb || rk.w < kb.w)) kb = { y: yk, w: rk.w }; }
    res.knee = kb ? u(kb.y) : null;
    // Elbows and wrists from the joints (hanging arms only; a raised arm is reported, not judged).
    ['r', 'l'].forEach(function (s) {
      var e = pup.pivots['fore-' + s], w = pup.pivots['hand-' + s];
      res['elbow-' + s] = e ? u(e[1]) : null;
      res['wrist-' + s] = w ? u(w[1]) : null;
      res['raised-' + s] = !!(e && w && w[1] < e[1]);
    });
    var C = CANON[type || 'male'], issues = [];
    function judge(key, val) {
      if (val === null || val === undefined || !C[key]) return;
      if (val < C[key][0] - 1e-6 || val > C[key][1] + 1e-6) issues.push(key + ' ' + val.toFixed(2) + ' (canon ' + C[key][0] + '-' + C[key][1] + ')');
    }
    ['heads', 'crotch', 'knee', 'waist', 'shoulderW', 'waistW', 'hipW'].forEach(function (k) { judge(k, res[k]); });
    ['r', 'l'].forEach(function (s) {
      // Only an arm hanging at the side is judged against the elbow and wrist lines.
      var e = pup.pivots['fore-' + s], w = pup.pivots['hand-' + s], sh = pup.pivots['arm-' + s];
      // Hanging: the whole arm runs down (shoulder to wrist mostly vertical) and is nearly straight.
      var hanging = e && w && sh && (w[1] - sh[1]) > 0.85 * Math.hypot(w[0] - sh[0], w[1] - sh[1]) && (w[1] - e[1]) > 0.75 * Math.hypot(w[0] - e[0], w[1] - e[1]);
      if (hanging) {
        judge('elbow', res['elbow-' + s]); judge('wrist', res['wrist-' + s]);
      }
    });
    res.issues = issues;
    return res;
  }

  global.FigureMeasure = { measure: measure, row: row, box: box, CANON: CANON };
})(window);
