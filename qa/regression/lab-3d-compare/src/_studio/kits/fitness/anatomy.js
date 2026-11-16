/*
 * Motion Lab fitness kit - anatomy and physiology diagrams (src/studio/kits/fitness/anatomy.js)
 *
 * Self-contained SVG plates drawn in the Sinew style. Each builder draws into a parent <g> in a
 * local box (default 400 x 400, origin top-left), returns a handle with the parts and with
 * timeline methods that only add explicit fromTo tweens. Everything is original vector art
 * (no third-party anatomy files); structure was checked against the facts in OpenStax
 * Anatomy and Physiology 2e, ch. 10 (muscle tissue) and ch. 19-22 (CC BY-NC-SA 4.0: a factual
 * reference only; none of its figures or text are copied). These are
 * SCHEMATIC: counts of filaments, nuclei or myofibrils are illustrative, never data.
 *
 *   var A = Studio.kit.fitness.anatomy;
 *   var s = A.sarcomere(g, {x: 40, y: 120, width: 520});  s.contract(tl, 3.0, 0.8, 0.35);
 *   var c = A.crossSection(g, {cx: 200, cy: 200, r: 120});  c.grow(tl, 5, 2.5, 1.3);
 */
(function (global) {
  'use strict';

  var Studio = global.Studio || (global.Studio = {});
  var F = (Studio.kit = Studio.kit || {}).fitness = (Studio.kit.fitness || {});
  var P = F.palette;
  var A = F.anatomy = {};
  var blob = Studio.rig.blob, curve = Studio.rig.curve;
  function svg(tag, attrs, parent) { return Studio.svg(tag, attrs, parent); }
  function num(v) { return Math.round(v * 100) / 100; }
  function grp(parent, cls, x, y, s) {
    return svg('g', { 'class': cls, transform: 'translate(' + num(x || 0) + ' ' + num(y || 0) + ') scale(' + num(s || 1) + ')' }, parent);
  }

  // ------------------------------------------------------------------ whole muscle (biceps-like fusiform)
  /** A fusiform muscle with tendons, epimysium sheen and fascicle lines. Box 400 x 160, long axis on x. */
  A.muscle = function (parent, opts) {
    var o = opts || {};
    var g = grp(parent, 'an-muscle', o.x, o.y, o.scale);
    var tendonL = svg('path', { d: 'M0 80 C30 74 50 72 78 70 L78 90 C50 88 30 86 0 80 Z', fill: P.tendon, stroke: P.boneLine, 'stroke-width': 2 }, g);
    var tendonR = svg('path', { d: 'M400 80 C370 76 350 74 322 72 L322 88 C350 86 370 84 400 80 Z', fill: P.tendon, stroke: P.boneLine, 'stroke-width': 2 }, g);
    var belly = svg('path', { d: 'M74 80 C100 18 300 18 326 80 C300 142 100 142 74 80 Z', fill: P.muscle, stroke: P.muscleDeep, 'stroke-width': 2.6 }, g);
    var lines = [];
    for (var i = -3; i <= 3; i++) {
      lines.push(svg('path', { d: 'M' + num(96 + Math.abs(i) * 6) + ' ' + num(80 + i * 12) + ' Q200 ' + num(80 + i * 15.5) + ' ' + num(304 - Math.abs(i) * 6) + ' ' + num(80 + i * 12), fill: 'none', stroke: P.muscleLight, 'stroke-width': 1.6, opacity: 0.8 }, g));
    }
    svg('path', { d: 'M120 44 Q200 26 280 44', fill: 'none', stroke: '#FFFFFF', 'stroke-width': 4, 'stroke-linecap': 'round', opacity: 0.35 }, g);
    return { g: g, belly: belly, tendons: [tendonL, tendonR], lines: lines, box: [400, 160], focus: [200, 80] };
  };

  // ------------------------------------------------------------------ fascicle (bundle of fibres)
  /** A bundle of fibres wrapped in perimysium, seen cut at one end. Box 400 x 220. */
  A.fascicle = function (parent, opts) {
    var o = opts || {};
    var g = grp(parent, 'an-fascicle', o.x, o.y, o.scale);
    var fibres = [];
    var rng = Studio.rng(o.seed || 21);
    var rows = [[60, 0], [84, 0], [108, 0], [132, 0], [156, 0], [72, 1], [96, 1], [120, 1], [144, 1]];
    svg('path', { d: 'M20 40 L340 40 Q380 110 340 180 L20 180 Z', fill: '#FBE2DA', stroke: P.muscleDeep, 'stroke-width': 2 }, g);
    rows.forEach(function (r, i) {
      var y = r[0] + (r[1] ? 0 : 0);
      var f = svg('rect', { x: 26 + rng() * 6, y: y - 9, width: 300 + r[1] * 10, height: 18, rx: 9, fill: P.muscle, stroke: P.muscleDeep, 'stroke-width': 1.4 }, g);
      fibres.push(f);
      // faint striations
      for (var k = 0; k < 18; k++) svg('line', { x1: 44 + k * 16, x2: 44 + k * 16, y1: y - 7, y2: y + 7, stroke: P.muscleDeep, 'stroke-width': 1, opacity: 0.25 }, g);
    });
    // cut face: circles for fibre ends
    var ends = [];
    for (var a = 0; a < 9; a++) {
      var cx = 350 + (a % 3) * 0 + rng() * 6, cy = 60 + a * 14;
      ends.push(svg('circle', { cx: num(cx + (a % 2) * 12), cy: num(cy), r: 8, fill: P.muscleLight, stroke: P.muscleDeep, 'stroke-width': 1.2 }, g));
    }
    var sheath = svg('path', { d: 'M20 40 L340 40 Q380 110 340 180 L20 180', fill: 'none', stroke: P.ink, 'stroke-width': 2.4, 'stroke-dasharray': '2 6', 'stroke-linecap': 'round' }, g);
    return { g: g, fibres: fibres, ends: ends, sheath: sheath, box: [400, 220], focus: [180, 108] };
  };

  // ------------------------------------------------------------------ one muscle fibre (cell)
  /** One fibre (a muscle cell): striations, nuclei at the edge, myofibrils inside. Box 420 x 160. */
  A.fibre = function (parent, opts) {
    var o = opts || {};
    var g = grp(parent, 'an-fibre', o.x, o.y, o.scale);
    var body = svg('rect', { x: 0, y: 20, width: 420, height: 120, rx: 60, fill: P.muscle, stroke: P.muscleDeep, 'stroke-width': 2.4 }, g);
    var stripes = svg('g', {}, g);
    for (var i = 0; i < 26; i++) svg('rect', { x: 30 + i * 14.4, y: 26, width: 6, height: 108, fill: P.muscleDeep, opacity: 0.28 }, stripes);
    var myo = [];
    for (var r = 0; r < 5; r++) myo.push(svg('line', { x1: 40, x2: 380, y1: 44 + r * 18, y2: 44 + r * 18, stroke: P.muscleLight, 'stroke-width': 7, 'stroke-linecap': 'round', opacity: 0.55 }, g));
    var nuclei = [];
    [[70, 26], [190, 134], [300, 26], [360, 132], [130, 134]].forEach(function (n) {
      nuclei.push(svg('ellipse', { cx: n[0], cy: n[1], rx: 14, ry: 6, fill: P.violet, stroke: P.ink, 'stroke-width': 1.4 }, g));
    });
    return { g: g, body: body, myofibrils: myo, nuclei: nuclei, box: [420, 160], focus: [210, 80] };
  };

  // ------------------------------------------------------------------ myofibril
  /** A myofibril: a chain of sarcomeres (A band dark, I band light, Z lines). Box 460 x 80. */
  A.myofibril = function (parent, opts) {
    var o = opts || {};
    var g = grp(parent, 'an-myofibril', o.x, o.y, o.scale);
    var n = o.count || 5, w = 460 / n;
    svg('rect', { x: 0, y: 14, width: 460, height: 52, rx: 26, fill: '#FBD9CF', stroke: P.muscleDeep, 'stroke-width': 2 }, g);
    var units = [];
    for (var i = 0; i < n; i++) {
      var x = i * w;
      units.push(svg('rect', { x: x + w * 0.28, y: 16, width: w * 0.44, height: 48, fill: P.muscle, opacity: 0.85 }, g));
      svg('line', { x1: x, x2: x, y1: 12, y2: 68, stroke: P.ink, 'stroke-width': 3 }, g);
    }
    svg('line', { x1: 460, x2: 460, y1: 12, y2: 68, stroke: P.ink, 'stroke-width': 3 }, g);
    return { g: g, units: units, unitWidth: w, box: [460, 80], focus: [w * 2.5, 40] };
  };

  // ------------------------------------------------------------------ sarcomere with sliding filaments
  /**
   * One sarcomere: Z discs at both ends, thin (actin) filaments anchored to them, thick
   * (myosin) filaments in the middle with heads. contract(tl, at, dur, amount) slides the actin
   * toward the M line (amount = fraction of the gap closed, 0..1) and tilts the heads; relax()
   * reverses it. Box width x 200.
   */
  A.sarcomere = function (parent, opts) {
    var o = opts || {};
    var W = o.width || 520;
    var g = grp(parent, 'an-sarcomere', o.x, o.y, o.scale);
    var rows = [40, 80, 120, 160];
    var thickL = W * 0.26, thickR = W * 0.74;
    var left = svg('g', { 'class': 'an-z-left' }, g), right = svg('g', { 'class': 'an-z-right' }, g);
    var thick = svg('g', { 'class': 'an-thick' }, g);
    // myosin thick filaments + heads (heads are separate so they can stroke)
    var heads = [];
    rows.slice(0, 3).forEach(function (r, i) {
      var y = r + 20;
      svg('rect', { x: thickL, y: y - 6, width: thickR - thickL, height: 12, rx: 6, fill: P.violet, stroke: P.ink, 'stroke-width': 1.4 }, thick);
      for (var k = 0; k < 7; k++) {
        var side = k < 3.5 ? -1 : 1;
        var hx = thickL + 16 + k * ((thickR - thickL - 32) / 6);
        if (Math.abs(hx - W / 2) < 18) continue;
        [-1, 1].forEach(function (up) {
          var h = svg('path', { d: 'M0 0 L' + num(side * -10) + ' ' + num(up * -13), stroke: P.violet, 'stroke-width': 4, 'stroke-linecap': 'round', fill: 'none', transform: 'translate(' + num(hx) + ' ' + num(y + up * -6) + ') rotate(0)' }, thick);
          h.__base = { x: hx, y: y + up * -6, side: side, up: up };
          heads.push(h);
        });
      }
    });
    svg('line', { x1: W / 2, x2: W / 2, y1: 30, y2: 170, stroke: P.ink2, 'stroke-width': 2, 'stroke-dasharray': '4 5' }, thick);
    // thin filaments anchored to Z discs
    var actinLen = W * 0.36;
    [left, right].forEach(function (holder, sideIdx) {
      var dir = sideIdx === 0 ? 1 : -1;
      var zx = sideIdx === 0 ? 0 : W;
      svg('rect', { x: zx - 5, y: 16, width: 10, height: 168, rx: 4, fill: P.ink }, holder);
      rows.forEach(function (r) {
        var x0 = zx, x1 = zx + dir * actinLen;
        svg('line', { x1: x0, x2: x1, y1: r, y2: r, stroke: P.emerald, 'stroke-width': 6, 'stroke-linecap': 'round' }, holder);
        for (var b = 0; b < 9; b++) svg('circle', { cx: num(x0 + dir * (10 + b * actinLen / 9)), cy: r, r: 3.2, fill: '#0E7A53' }, holder);
      });
    });
    var state = 0;
    var gap = W / 2 - actinLen;
    function zT(side, amt) { return 'translate(' + num(side * amt * gap) + ' 0)'; }
    var handle = {
      g: g, width: W, heads: heads,
      /** Slide toward the M line by `amount` (0..1 of the gap), with heads pulling. */
      contract: function (tl, at, dur, amount) {
        var to = amount === undefined ? 0.7 : amount;
        tl.fromTo(left, { attr: { transform: zT(1, state) } }, { attr: { transform: zT(1, to) }, duration: dur, ease: 'power2.inOut', immediateRender: false }, at);
        tl.fromTo(right, { attr: { transform: zT(-1, state) } }, { attr: { transform: zT(-1, to) }, duration: dur, ease: 'power2.inOut', immediateRender: false }, at);
        // power strokes: heads tilt and recover a few times during the slide
        var strokes = Math.max(1, Math.round(dur / 0.3));
        heads.forEach(function (h, i) {
          var b = h.__base;
          var rest = 'translate(' + num(b.x) + ' ' + num(b.y) + ') rotate(0)';
          var pulled = 'translate(' + num(b.x) + ' ' + num(b.y) + ') rotate(' + num(b.side * b.up * 28) + ')';
          for (var s2 = 0; s2 < strokes; s2++) {
            var t0 = at + s2 * dur / strokes + (i % 3) * 0.03;
            tl.fromTo(h, { attr: { transform: rest } }, { attr: { transform: pulled }, duration: dur / strokes * 0.55, ease: 'power2.in', immediateRender: false }, t0);
            tl.fromTo(h, { attr: { transform: pulled } }, { attr: { transform: rest }, duration: dur / strokes * 0.4, ease: 'power1.out', immediateRender: false }, t0 + dur / strokes * 0.55);
          }
        });
        state = to;
        return at + dur;
      },
      relax: function (tl, at, dur) {
        tl.fromTo(left, { attr: { transform: zT(1, state) } }, { attr: { transform: zT(1, 0) }, duration: dur, ease: 'power2.inOut', immediateRender: false }, at);
        tl.fromTo(right, { attr: { transform: zT(-1, state) } }, { attr: { transform: zT(-1, 0) }, duration: dur, ease: 'power2.inOut', immediateRender: false }, at);
        state = 0;
        return at + dur;
      }
    };
    return handle;
  };

  // ------------------------------------------------------------------ fibre cross-section that grows
  /**
   * A muscle fibre cut across: membrane, myofibril dots, nuclei on the rim. grow(tl, at, dur, k)
   * scales the fibre to k times its radius and fades in extra protein dots in the new outer ring,
   * shown as "more contractile protein". Whether growth adds myofibrils or enlarges existing
   * ones is unresolved in humans (Jorgenson et al. 2020): label it neutrally.
   */
  A.crossSection = function (parent, opts) {
    var o = opts || {};
    var R = o.r || 110;
    var g = grp(parent, 'an-cross', o.cx, o.cy, 1);
    var inner = svg('g', { transform: 'scale(1)' }, g);
    var mem = svg('circle', { r: R, fill: '#FBD9CF', stroke: P.muscleDeep, 'stroke-width': 3 }, inner);
    var rng = Studio.rng(o.seed || 5);
    var dots = [], extra = [];
    var step = R / 7.2;
    for (var y = -R; y <= R; y += step) {
      for (var x = -R; x <= R; x += step) {
        var jx = x + (rng() - 0.5) * step * 0.35, jy = y + (rng() - 0.5) * step * 0.35;
        var d = Math.sqrt(jx * jx + jy * jy);
        if (d < R * 0.86) dots.push(svg('circle', { cx: num(jx), cy: num(jy), r: num(step * 0.34), fill: P.muscle }, inner));
      }
    }
    var newRing = svg('g', { opacity: 0 }, g);
    var K = o.growTo || 1.35;
    for (var a = 0; a < 46; a++) {
      var ang = a / 46 * Math.PI * 2 + rng() * 0.1;
      var rr = R * (0.9 + rng() * (K - 1) * 0.85);
      extra.push(svg('circle', { cx: num(Math.cos(ang) * rr), cy: num(Math.sin(ang) * rr), r: num(step * 0.34), fill: P.muscleLight, stroke: P.muscle, 'stroke-width': 1 }, newRing));
    }
    var nuclei = [];
    [0.4, 2.1, 3.9, 5.3].forEach(function (ang) {
      nuclei.push(svg('ellipse', { cx: num(Math.cos(ang) * R * 0.93), cy: num(Math.sin(ang) * R * 0.93), rx: 10, ry: 5.5, fill: P.violet, stroke: P.ink, 'stroke-width': 1.2, transform: 'rotate(' + num(ang * 57.3 + 90) + ' ' + num(Math.cos(ang) * R * 0.93) + ' ' + num(Math.sin(ang) * R * 0.93) + ')' }, inner));
    });
    var outline = svg('circle', { r: R, fill: 'none', stroke: P.muscleDeep, 'stroke-width': 3 }, g);
    var scale = 1;
    return {
      g: g, membrane: mem, dots: dots, extra: extra, nuclei: nuclei, outline: outline, r: R,
      grow: function (tl, at, dur, k) {
        var to = k || K;
        tl.fromTo(inner, { attr: { transform: 'scale(' + num(scale) + ')' } }, { attr: { transform: 'scale(' + num(1 + (to - 1) * 0.35) + ')' }, duration: dur, ease: 'power1.inOut', immediateRender: false }, at);
        tl.fromTo(outline, { attr: { r: num(R * scale) } }, { attr: { r: num(R * to) } , duration: dur, ease: 'power1.inOut', immediateRender: false }, at);
        tl.fromTo(newRing, { opacity: 0 }, { opacity: 1, duration: dur * 0.8, ease: 'power1.inOut', immediateRender: false }, at + dur * 0.2);
        tl.fromTo(extra, { attr: { r: 0 } }, { attr: { r: num(step * 0.34) }, duration: 0.35, ease: 'back.out(2)', stagger: dur * 0.7 / extra.length, immediateRender: false }, at + dur * 0.15);
        scale = to;
        return at + dur;
      }
    };
  };

  // ------------------------------------------------------------------ satellite cell donating a nucleus
  /** A small satellite cell under the fibre membrane; donate(tl, at) moves a nucleus into the fibre. */
  A.satelliteCell = function (parent, opts) {
    var o = opts || {};
    var g = grp(parent, 'an-satellite', o.x, o.y, o.scale);
    var cell = svg('ellipse', { cx: 0, cy: 0, rx: 26, ry: 14, fill: '#EDE4FF', stroke: P.violet, 'stroke-width': 2 }, g);
    var nuc = svg('ellipse', { cx: 0, cy: 0, rx: 11, ry: 6, fill: P.violet, stroke: P.ink, 'stroke-width': 1.2 }, g);
    return {
      g: g, cell: cell, nucleus: nuc,
      donate: function (tl, at, dx, dy) {
        tl.fromTo(nuc, { attr: { cx: 0, cy: 0 } }, { attr: { cx: dx || 0, cy: dy || -40 }, duration: 1.0, ease: 'power2.inOut', immediateRender: false }, at);
        tl.fromTo(cell, { attr: { rx: 26, ry: 14 } }, { attr: { rx: 20, ry: 10 }, duration: 1.0, ease: 'power2.inOut', immediateRender: false }, at);
        return at + 1.0;
      }
    };
  };

  // ------------------------------------------------------------------ mitochondrion and ATP
  /** A mitochondrion (outer membrane, cristae). emit(tl, at, n) releases ATP tokens. Box 240 x 120. */
  A.mitochondrion = function (parent, opts) {
    var o = opts || {};
    var g = grp(parent, 'an-mito', o.x, o.y, o.scale);
    svg('path', { d: 'M20 60 C20 14 220 14 220 60 C220 106 20 106 20 60 Z', fill: '#FFE3B0', stroke: P.sparkDeep, 'stroke-width': 3 }, g);
    var cr = 'M40 60';
    for (var i = 0; i < 7; i++) {
      var x = 50 + i * 24;
      cr += ' L' + x + ' ' + (i % 2 ? 34 : 86) + ' L' + (x + 12) + ' ' + (i % 2 ? 34 : 86) + ' L' + (x + 12) + ' 60';
    }
    svg('path', { d: cr + ' L200 60', fill: 'none', stroke: P.sparkDeep, 'stroke-width': 2.4, 'stroke-linejoin': 'round' }, g);
    var tokens = [];
    return {
      g: g,
      emit: function (tl, at, n, spread) {
        var rng = Studio.rng(o.seed || 3);
        for (var k = 0; k < (n || 6); k++) {
          var t = A.atp(g, { x: 120, y: 60, scale: 0.55 });
          var ang = -Math.PI / 2 + (rng() - 0.5) * 2.2, dist = (spread || 130) * (0.7 + rng() * 0.3);
          tokens.push(t);
          var start = at + k * 0.18;
          tl.fromTo(t.g, { attr: { transform: 'translate(120 60) scale(0.2)' }, opacity: 0 }, { attr: { transform: 'translate(' + num(120 + Math.cos(ang) * dist) + ' ' + num(60 + Math.sin(ang) * dist) + ') scale(0.55)' }, opacity: 1, duration: 0.8, ease: 'power2.out', immediateRender: true }, start);
        }
        return at + (n || 6) * 0.18 + 0.8;
      }
    };
  };
  /** An ATP token: adenosine disc with three phosphate beads. */
  A.atp = function (parent, opts) {
    var o = opts || {};
    var g = grp(parent, 'an-atp', o.x, o.y, o.scale);
    svg('circle', { cx: -22, cy: 0, r: 15, fill: P.spark, stroke: P.ink, 'stroke-width': 2 }, g);
    var beads = [];
    for (var i = 0; i < 3; i++) {
      svg('line', { x1: -8 + i * 18, x2: 2 + i * 18, y1: 0, y2: 0, stroke: P.ink, 'stroke-width': 2.4 }, g);
      beads.push(svg('circle', { cx: 8 + i * 18, cy: 0, r: 7, fill: P.emerald, stroke: P.ink, 'stroke-width': 1.6 }, g));
    }
    var label = svg('text', { x: -22, y: 5, 'text-anchor': 'middle', 'font-family': 'JetBrains Mono', 'font-weight': 700, 'font-size': 11, fill: P.ink }, g);
    label.textContent = 'A';
    return { g: g, beads: beads };
  };

  // ------------------------------------------------------------------ heart, lungs, alveolus
  /** A stylised four-chamber heart. beat(tl, from, to, bpm) adds finite squeeze cycles. Box 200 x 220. */
  A.heart = function (parent, opts) {
    var o = opts || {};
    var g = grp(parent, 'an-heart', o.x, o.y, o.scale);
    var pump = svg('g', { transform: 'translate(100 120) scale(1) translate(-100 -120)' }, g);
    svg('path', { d: 'M70 20 C70 0 96 0 96 20 L96 60 M120 30 C150 10 190 30 168 60', fill: 'none', stroke: P.oxy, 'stroke-width': 16, 'stroke-linecap': 'round' }, pump);
    svg('path', { d: 'M100 60 C40 30 0 90 30 140 C50 175 85 200 100 214 C115 200 150 175 170 140 C200 90 160 30 100 60 Z', fill: P.oxy, stroke: '#9E1E33', 'stroke-width': 3 }, pump);
    svg('path', { d: 'M100 70 C100 110 96 160 100 205', fill: 'none', stroke: '#9E1E33', 'stroke-width': 2.4 }, pump);
    svg('path', { d: 'M40 110 C70 104 130 104 160 110', fill: 'none', stroke: '#9E1E33', 'stroke-width': 2, opacity: 0.7 }, pump);
    svg('path', { d: 'M52 72 C34 96 34 128 58 146 L94 146 L94 76 Z', fill: P.deoxy, opacity: 0.5 }, pump);
    return {
      g: g, pump: pump,
      beat: function (tl, from, to, bpm) {
        var per = 60 / (bpm || 60);
        var n = Studio.cycles(from, to, per);
        for (var i = 0; i < n; i++) {
          var t = from + i * per;
          tl.fromTo(pump, { attr: { transform: 'translate(100 120) scale(1) translate(-100 -120)' } }, { attr: { transform: 'translate(100 120) scale(0.9) translate(-100 -120)' }, duration: per * 0.18, ease: 'power2.in', immediateRender: false }, t);
          tl.fromTo(pump, { attr: { transform: 'translate(100 120) scale(0.9) translate(-100 -120)' } }, { attr: { transform: 'translate(100 120) scale(1) translate(-100 -120)' }, duration: per * 0.4, ease: 'power2.out', immediateRender: false }, t + per * 0.18);
        }
        return from + n * per;
      }
    };
  };
  /** Stylised lungs with airway and diaphragm. breathe(tl, from, to, perMin). Box 260 x 240. */
  A.lungs = function (parent, opts) {
    var o = opts || {};
    var g = grp(parent, 'an-lungs', o.x, o.y, o.scale);
    svg('path', { d: 'M130 10 L130 70 M130 70 L96 96 M130 70 L164 96', fill: 'none', stroke: P.ink2, 'stroke-width': 10, 'stroke-linecap': 'round' }, g);
    var lobes = svg('g', { transform: 'translate(130 120) scale(1 1) translate(-130 -120)' }, g);
    svg('path', { d: 'M112 80 C70 70 30 120 30 180 C30 214 70 222 112 204 Z', fill: '#F7A5A5', stroke: '#B8444E', 'stroke-width': 3 }, lobes);
    svg('path', { d: 'M148 80 C190 70 230 120 230 180 C230 214 190 222 148 204 Z', fill: '#F7A5A5', stroke: '#B8444E', 'stroke-width': 3 }, lobes);
    var dia = svg('path', { d: 'M20 222 Q130 196 240 222', fill: 'none', stroke: P.muscle, 'stroke-width': 8, 'stroke-linecap': 'round' }, g);
    return {
      g: g, lobes: lobes, diaphragm: dia,
      breathe: function (tl, from, to, perMin) {
        var per = 60 / (perMin || 15);
        var n = Studio.cycles(from, to, per);
        var a = 'translate(130 120) scale(1 1) translate(-130 -120)', b = 'translate(130 120) scale(1.06 1.1) translate(-130 -120)';
        for (var i = 0; i < n; i++) {
          var t = from + i * per;
          tl.fromTo(lobes, { attr: { transform: a } }, { attr: { transform: b }, duration: per * 0.45, ease: 'sine.inOut', immediateRender: false }, t);
          tl.fromTo(dia, { attr: { d: 'M20 222 Q130 196 240 222' } }, { attr: { d: 'M20 230 Q130 222 240 230' }, duration: per * 0.45, ease: 'sine.inOut', immediateRender: false }, t);
          tl.fromTo(lobes, { attr: { transform: b } }, { attr: { transform: a }, duration: per * 0.55, ease: 'sine.inOut', immediateRender: false }, t + per * 0.45);
          tl.fromTo(dia, { attr: { d: 'M20 230 Q130 222 240 230' } }, { attr: { d: 'M20 222 Q130 196 240 222' }, duration: per * 0.55, ease: 'sine.inOut', immediateRender: false }, t + per * 0.45);
        }
        return from + n * per;
      }
    };
  };

  // ------------------------------------------------------------------ zoom ladder through scales
  /**
   * Scale ladder: show plates one after another as if zooming in through a lens, each with a
   * scale label (scale is always visible: science-atlas / body-lab rule).
   * levels = [{g, label, scale}] where g is a plate group already built at the same centre.
   * step(tl, from, to, at) zooms plate `from` up and away while `to` grows in from the focus.
   */
  A.zoomLadder = function (levels, opts) {
    var o = opts || {};
    var cx = o.cx || 0, cy = o.cy || 0;
    levels.forEach(function (lv, i) { if (i > 0) lv.g.setAttribute('opacity', 0); });
    function T(sv) { return 'translate(' + num(cx) + ' ' + num(cy) + ') scale(' + num(sv) + ') translate(' + num(-cx) + ' ' + num(-cy) + ')'; }
    return {
      levels: levels,
      step: function (tl, from, to, at, dur) {
        var d = dur || 1.1;
        var a = levels[from], b = levels[to];
        tl.fromTo(a.wrap, { attr: { transform: T(1) } }, { attr: { transform: T(o.zoom || 6) }, duration: d, ease: 'power3.in', immediateRender: false }, at);
        tl.fromTo(a.g, { opacity: 1 }, { opacity: 0, duration: d * 0.45, ease: 'power1.in', immediateRender: false }, at + d * 0.55);
        tl.fromTo(b.wrap, { attr: { transform: T(0.18) } }, { attr: { transform: T(1) }, duration: d, ease: 'power3.out', immediateRender: false }, at + d * 0.55);
        tl.fromTo(b.g, { opacity: 0 }, { opacity: 1, duration: d * 0.4, ease: 'power1.out', immediateRender: false }, at + d * 0.55);
        return at + d * 1.55;
      }
    };
  };
})(typeof window !== 'undefined' ? window : this);
