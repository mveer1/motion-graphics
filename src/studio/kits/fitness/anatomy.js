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

  // ------------------------------------------------------------------ inside-the-body plates (2026-11-23)
  // Vascular tree, alveolus and joint sections use the Sinew inside language (STYLE.md): rosewood
  // for tissue and vessels, ivory for tendon, ligament and cartilage, bone and cream for bone and
  // cut edges, a dusk tone for oxygen-poor blood. Never the effort colours (coral, marigold, pale
  // cobalt): nothing here is "working". Every plate carries an "illustrative" tag; structure
  // follows OpenStax Anatomy and Physiology 2e (sections 9.4, 9.6, 20.1, 22.1; facts only, no
  // figure copied), see assets/fitness/manifest.json for the exact references.
  var IN = A.inside = {
    rose: '#C98A82', roseDeep: '#A8645F', roseLine: '#8E5650', ivory: '#F3E7CF', ivoryLine: '#C9B48C',
    bone: '#E3D5B6', boneLine: '#B39C72', cream: '#F6EFE0', dusk: '#6F5B70', duskLight: '#9B879A',
    fluid: '#EFD9D2', air: '#FBF8F1'
  };
  function label(g, s, x, y, o) {
    var e = o || {};
    var t = svg('text', { x: num(x), y: num(y), 'text-anchor': e.anchor || 'start', 'font-family': e.mono ? 'JetBrains Mono' : 'Inter', 'font-weight': e.w || 600, 'font-size': e.size || 15, fill: e.fill || P.ink }, g);
    t.textContent = s;
    return t;
  }
  function leader(g, x1, y1, x2, y2) {
    var l = svg('g', {}, g);
    svg('line', { x1: num(x1), y1: num(y1), x2: num(x2), y2: num(y2), stroke: P.ink2, 'stroke-width': 1.4 }, l);
    svg('circle', { cx: num(x2), cy: num(y2), r: 2.6, fill: P.ink }, l);
    return l;
  }
  // a name with a leader line that leaves from the side of the text facing its target (never through it)
  function named(g, list, s, x, y, lx, ly, anchor, size, from) {
    var sz = size || 15, w = s.length * sz * 0.54, an = anchor || 'start';
    var x0 = an === 'middle' ? x - w / 2 : (an === 'end' ? x - w : x), x1 = x0 + w;
    var ng = svg('g', {}, g);
    if (from) leader(ng, from[0], from[1], lx, ly);
    else if (lx > x1 + 2) leader(ng, x1 + 5, y - sz * 0.33, lx, ly);
    else if (lx < x0 - 2) leader(ng, x0 - 5, y - sz * 0.33, lx, ly);
    else leader(ng, Math.max(x0, Math.min(x1, lx)), ly > y ? y + 5 : y - sz - 2, lx, ly);
    label(ng, s, x, y, { anchor: an, size: sz, w: 700 });
    list.push(ng);
    return ng;
  }
  function tagIllustrative(g, x, y, text) {
    return label(g, text || 'ILLUSTRATIVE', x, y, { mono: true, size: 12, w: 500, fill: P.ink3 });
  }
  function pathOf(pts) { return 'M' + pts.map(function (p) { return num(p[0]) + ' ' + num(p[1]); }).join(' L'); }
  // a token travels a polyline at constant speed: one linear tween per leg, `period` per trip; with
  // `until` the trip is cut there (the last leg ends part-way), so nothing runs past the scene
  function travel(tl, el, pts, at, period, until) {
    var L = 0, seg = [];
    for (var i = 1; i < pts.length; i++) { var d = Math.sqrt(Math.pow(pts[i][0] - pts[i - 1][0], 2) + Math.pow(pts[i][1] - pts[i - 1][1], 2)); seg.push(d); L += d; }
    var t = at, end = until === undefined ? Infinity : until;
    for (var k = 1; k < pts.length && t < end - 1e-6; k++) {
      var dur = period * seg[k - 1] / L, q = pts[k];
      if (t + dur > end) { var f = (end - t) / dur; q = [pts[k - 1][0] + (pts[k][0] - pts[k - 1][0]) * f, pts[k - 1][1] + (pts[k][1] - pts[k - 1][1]) * f]; dur = end - t; }
      tl.fromTo(el, { attr: { transform: 'translate(' + num(pts[k - 1][0]) + ' ' + num(pts[k - 1][1]) + ')' } }, { attr: { transform: 'translate(' + num(q[0]) + ' ' + num(q[1]) + ')' }, duration: dur, ease: 'none', immediateRender: false }, t);
      t += dur;
    }
    return t;
  }
  // labels and leader groups appear one after another (progressive reveal for narration)
  function revealer(items) {
    items.forEach(function (it) { it.setAttribute('opacity', 0); });
    return function (tl, at, stagger) {
      var s = stagger === undefined ? 0.45 : stagger;
      items.forEach(function (it, i) { tl.fromTo(it, { opacity: 0 }, { opacity: 1, duration: 0.35, ease: 'power1.out', immediateRender: false }, at + i * s); });
      return at + items.length * s + 0.35;
    };
  }

  /**
   * A vascular tree: an artery branches into arterioles, a capillary bed, venules and a vein (with a
   * valve); inset cross-sections compare wall thickness. Box 600 x 340, flow left to right.
   * flow(tl, from, to, period) sends blood cells through (they turn from rosewood to dusk in the
   * capillaries, where oxygen is given off); labels(tl, at, stagger) reveals the names.
   * Facts: OpenStax A&P 2e 20.1 (arteries carry blood away from the heart and have thicker walls
   * and smaller lumens; veins have thinner walls, larger lumens and, in the limbs, valves).
   */
  A.vascularTree = function (parent, opts) {
    var o = opts || {};
    var g = grp(parent, 'an-vascular', o.x, o.y, o.scale);
    var cy = 140, rows = [-58, 0, 58];
    var paths = rows.map(function (dy) {
      return [[-10, cy], [120, cy], [180, cy + dy * 0.6], [235, cy + dy], [255, cy + dy - 8], [275, cy + dy + 8], [295, cy + dy - 8], [315, cy + dy + 8], [335, cy + dy],
        [390, cy + dy * 0.6], [450, cy], [610, cy]];
    });
    var vessels = svg('g', {}, g);
    // capillary bed: a fine mesh between the arteriole and venule ends
    var bed = svg('g', {}, vessels);
    rows.forEach(function (dy, i) {
      svg('path', { d: Studio.rig.curve(paths[i].slice(3, 9), 0.7), fill: 'none', stroke: IN.rose, 'stroke-width': 4, 'stroke-linecap': 'round' }, bed);
    });
    [[245, 268, 'M245 ' + (cy - 50) + ' C255 ' + (cy - 20) + ' 250 ' + (cy - 10) + ' 262 ' + cy], [300, 320, 'M298 ' + (cy - 4) + ' C306 ' + (cy + 20) + ' 300 ' + (cy + 34) + ' 312 ' + (cy + 54)],
      [270, 290, 'M276 ' + (cy + 6) + ' C284 ' + (cy - 20) + ' 280 ' + (cy - 34) + ' 290 ' + (cy - 54)], [320, 330, 'M318 ' + (cy - 54) + ' C326 ' + (cy - 30) + ' 322 ' + (cy - 14) + ' 332 ' + cy]
    ].forEach(function (c) { svg('path', { d: c[2], fill: 'none', stroke: IN.duskLight, 'stroke-width': 3, 'stroke-linecap': 'round', opacity: 0.9 }, bed); });
    // arterial side: thick wall (roseDeep) around a smaller lumen
    var art = svg('g', {}, vessels);
    svg('path', { d: 'M-10 ' + cy + ' L120 ' + cy, stroke: IN.roseDeep, 'stroke-width': 30, 'stroke-linecap': 'round', fill: 'none' }, art);
    rows.forEach(function (dy) { svg('path', { d: 'M118 ' + cy + ' Q170 ' + num(cy + dy * 0.5) + ' 238 ' + (cy + dy), stroke: IN.roseDeep, 'stroke-width': 13, 'stroke-linecap': 'round', fill: 'none' }, art); });
    svg('path', { d: 'M-10 ' + cy + ' L120 ' + cy, stroke: IN.rose, 'stroke-width': 13, 'stroke-linecap': 'round', fill: 'none' }, art);
    rows.forEach(function (dy) { svg('path', { d: 'M118 ' + cy + ' Q170 ' + num(cy + dy * 0.5) + ' 238 ' + (cy + dy), stroke: IN.rose, 'stroke-width': 5, 'stroke-linecap': 'round', fill: 'none' }, art); });
    // venous side: thin wall (dusk) around a larger lumen, one valve
    var ven = svg('g', {}, vessels);
    rows.forEach(function (dy) { svg('path', { d: 'M332 ' + (cy + dy) + ' Q400 ' + num(cy + dy * 0.5) + ' 452 ' + cy, stroke: IN.dusk, 'stroke-width': 14, 'stroke-linecap': 'round', fill: 'none' }, ven); });
    svg('path', { d: 'M450 ' + cy + ' L610 ' + cy, stroke: IN.dusk, 'stroke-width': 38, 'stroke-linecap': 'round', fill: 'none' }, ven);
    rows.forEach(function (dy) { svg('path', { d: 'M332 ' + (cy + dy) + ' Q400 ' + num(cy + dy * 0.5) + ' 452 ' + cy, stroke: IN.duskLight, 'stroke-width': 9, 'stroke-linecap': 'round', fill: 'none' }, ven); });
    svg('path', { d: 'M450 ' + cy + ' L610 ' + cy, stroke: IN.duskLight, 'stroke-width': 30, 'stroke-linecap': 'round', fill: 'none' }, ven);
    var valve = svg('g', {}, ven);
    svg('path', { d: 'M520 ' + (cy - 15) + ' Q540 ' + (cy - 6) + ' 552 ' + (cy - 1) + ' M520 ' + (cy + 15) + ' Q540 ' + (cy + 6) + ' 552 ' + (cy + 1), stroke: IN.cream, 'stroke-width': 3.4, fill: 'none', 'stroke-linecap': 'round' }, valve);
    // cells ride above the vessels
    var cells = svg('g', {}, g);
    // insets: artery vs vein cut across
    var insets = svg('g', {}, g);
    function inset(x, wall, lumenR, rx, col, light, name) {
      var ig = svg('g', { transform: 'translate(' + x + ' 272)' }, insets);
      svg('ellipse', { rx: num(lumenR + wall), ry: num((lumenR + wall) * rx), fill: col }, ig);
      svg('ellipse', { rx: num(lumenR), ry: num(lumenR * rx * 0.92), fill: light }, ig);
      label(ig, name, 0, 50, { anchor: 'middle', size: 13, w: 600, fill: P.ink2 });
      return ig;
    }
    var insA = inset(60, 13, 11, 1, IN.roseDeep, IN.rose, 'artery: thick wall');
    var insV = inset(540, 5, 22, 0.72, IN.dusk, IN.duskLight, 'vein: thin wall, wide lumen');
    var names = [];
    function name(s, x, y, lx, ly) { return named(g, names, s, x, y, lx, ly, 'middle', 16); }
    name('artery', 60, 92, 60, cy - 16);
    name('arterioles', 175, 40, 190, cy - 44);
    name('capillaries', 288, 30, 290, cy - 60);
    name('venules', 400, 40, 392, cy - 46);
    name('vein', 485, 92, 485, cy - 20);
    name('valve', 588, 92, 545, cy - 6);
    var tagEl = tagIllustrative(g, 0, 358, 'ILLUSTRATIVE · NOT TO SCALE');
    var legend = svg('g', { transform: 'translate(180 300)' }, g);
    svg('circle', { cx: 0, cy: -5, r: 7, fill: IN.roseDeep }, legend); label(legend, 'oxygen-rich', 12, 0, { size: 13 });
    svg('circle', { cx: 130, cy: -5, r: 7, fill: IN.dusk }, legend); label(legend, 'oxygen-poor', 142, 0, { size: 13 });
    return {
      g: g, vessels: vessels, capillaries: bed, valve: valve, insets: [insA, insV], names: names, tag: tagEl, legend: legend, paths: paths,
      labels: revealer(names),
      /** Blood cells through every branch from `from` to `to`; period = seconds per trip. Returns `to`. */
      flow: function (tl, from, to, period) {
        var per = period || 3.2, lanes = paths.length, per2 = per / 5;
        for (var lane = 0; lane < lanes; lane++) {
          for (var k = 0; k < 5; k++) {
            var cell = svg('g', { transform: 'translate(-20 ' + cy + ')', opacity: 0 }, cells);
            var disc = svg('ellipse', { rx: 6.5, ry: 4.5, fill: IN.roseDeep, stroke: IN.cream, 'stroke-width': 1.4 }, cell);
            var start = from + lane * per2 * 0.33 + k * per2;
            if (start >= to) continue;
            tl.fromTo(cell, { opacity: 0 }, { opacity: 1, duration: 0.2, immediateRender: false }, start);
            for (var t0 = start; t0 < to - 1e-6; t0 += per) {
              travel(tl, cell, paths[lane], t0, per, to);
              // oxygen given off in the capillary bed: rosewood -> dusk, reset at the next trip
              if (t0 + per * 0.6 <= to) tl.fromTo(disc, { attr: { fill: IN.roseDeep } }, { attr: { fill: IN.dusk }, duration: per * 0.18, ease: 'power1.inOut', immediateRender: false }, t0 + per * 0.42);
              if (t0 + per <= to) tl.fromTo(disc, { attr: { fill: IN.dusk } }, { attr: { fill: IN.roseDeep }, duration: 0.01, ease: 'none', immediateRender: false }, t0 + per - 0.01);
            }
          }
        }
        return to;
      }
    };
  };

  /**
   * One alveolus at a capillary: air comes down the bronchiole, oxygen crosses the thin respiratory
   * membrane into the blood and carbon dioxide crosses out. Box 520 x 360. exchange(tl, from, to,
   * period) moves the molecules; labels(tl, at, stagger) reveals the names.
   * Facts: OpenStax A&P 2e 22.1 (alveolus about 200 um across; type I cells form most of the
   * surface, type II cells secrete surfactant, alveolar macrophages roam the wall; the respiratory
   * membrane is about 0.5 um thick and gases cross it by simple diffusion).
   */
  A.alveolus = function (parent, opts) {
    var o = opts || {};
    var g = grp(parent, 'an-alveolus', o.x, o.y, o.scale);
    var C = [250, 190], R = 118;
    // bronchiole from the top left into the sac, neighbour alveoli behind
    svg('path', { d: 'M40 10 C80 40 120 70 170 96', fill: 'none', stroke: IN.rose, 'stroke-width': 46, 'stroke-linecap': 'round' }, g);
    svg('path', { d: 'M40 10 C80 40 120 70 170 96', fill: 'none', stroke: IN.air, 'stroke-width': 34, 'stroke-linecap': 'round' }, g);
    [[118, 228, 62], [390, 110, 58]].forEach(function (c) { svg('circle', { cx: c[0], cy: c[1], r: c[2], fill: IN.air, stroke: IN.rose, 'stroke-width': 5 }, g); });
    var sac = svg('circle', { cx: C[0], cy: C[1], r: R, fill: IN.air, stroke: IN.rose, 'stroke-width': 6 }, g);
    // capillary hugging the lower right of the wall
    var capD = 'M250 334 A144 144 0 0 0 392 196 A144 144 0 0 0 330 80';
    var cap = svg('g', {}, g);
    svg('path', { d: capD, fill: 'none', stroke: IN.roseDeep, 'stroke-width': 30, 'stroke-linecap': 'round' }, cap);
    svg('path', { d: capD, fill: 'none', stroke: IN.rose, 'stroke-width': 20, 'stroke-linecap': 'round' }, cap);
    // type II cell with surfactant, a macrophage on the wall
    var t2 = svg('g', {}, g);
    svg('path', { d: 'M150 232 C146 214 166 204 178 214 C190 224 182 246 166 246 C156 246 152 240 150 232 Z', fill: IN.cream, stroke: IN.roseLine, 'stroke-width': 2 }, t2);
    [[170, 222], [176, 232], [164, 236]].forEach(function (p) { svg('circle', { cx: p[0], cy: p[1], r: 2.6, fill: IN.ivoryLine }, t2); });
    var mac = svg('path', { d: 'M232 290 C222 280 236 268 248 274 C256 264 272 270 268 282 C280 288 272 302 260 300 C252 310 236 304 232 290 Z', fill: IN.ivory, stroke: IN.ivoryLine, 'stroke-width': 2 }, g);
    var mols = svg('g', {}, g);
    var names = [];
    function name(s, x, y, lx, ly, anchor) { return named(g, names, s, x, y, lx, ly, anchor); }
    name('alveolus (~200 \u00B5m)', 300, 40, 270, 76);
    name('capillary', 430, 300, 380, 268);
    name('respiratory membrane (~0.5 \u00B5m)', 410, 196, 368, 190);
    name('type II cell: surfactant', 20, 300, 158, 244);
    name('macrophage', 150, 346, 238, 300);
    name('type I cells line the wall', 20, 150, 136, 160);
    var tagEl = tagIllustrative(g, 380, 356, 'ILLUSTRATIVE · NOT TO SCALE');
    var legend = svg('g', { transform: 'translate(330 18)' }, g);
    svg('circle', { cx: 0, cy: -5, r: 7, fill: IN.cream, stroke: IN.roseDeep, 'stroke-width': 2.4 }, legend); label(legend, 'O\u2082', 12, 0, { size: 14, w: 700 });
    svg('circle', { cx: 60, cy: -5, r: 7, fill: P.ink2 }, legend); label(legend, 'CO\u2082', 72, 0, { size: 14, w: 700 });
    return {
      g: g, sac: sac, capillary: cap, typeII: t2, macrophage: mac, names: names, tag: tagEl, legend: legend,
      labels: revealer(names),
      /** Oxygen in from the airway and across into the blood, carbon dioxide out the other way. */
      exchange: function (tl, from, to, period) {
        var per = period || 3.0;
        var o2 = [[[60, 24], [130, 70], [220, 150], [300, 214], [352, 236], [372, 210], [366, 150], [340, 100]],
          [[70, 30], [150, 90], [240, 190], [312, 260], [330, 282], [296, 312], [260, 328]],
          [[80, 20], [160, 80], [250, 120], [330, 170], [364, 182], [372, 214], [354, 270]]];
        var co2 = [[[262, 330], [300, 312], [318, 288], [250, 230], [170, 110], [70, 30]],
          [[346, 110], [366, 150], [344, 172], [260, 140], [160, 80], [60, 20]]];
        function stream(set, fill, stroke, offset) {
          set.forEach(function (pts, i) {
            var m = svg('g', { transform: 'translate(' + pts[0][0] + ' ' + pts[0][1] + ')', opacity: 0 }, mols);
            svg('circle', { r: 7, fill: fill, stroke: stroke || 'none', 'stroke-width': 2.4 }, m);
            var start = from + offset + i * per / set.length;
            if (start >= to) return;
            tl.fromTo(m, { opacity: 0 }, { opacity: 1, duration: 0.25, immediateRender: false }, start);
            for (var t0 = start; t0 < to - 1e-6; t0 += per) travel(tl, m, pts, t0, per, to);
          });
        }
        stream(o2, IN.cream, IN.roseDeep, 0);
        stream(co2, P.ink2, null, per * 0.3);
        return to;
      }
    };
  };

  /**
   * A synovial joint cut open: 'knee' (side, front of the knee to the right), 'hip' or 'shoulder'
   * (from the front, the body's midline to the left). Bones in bone tone with ivory articular
   * cartilage, the capsule and synovial cavity, and the joint's own supports (menisci and cruciate
   * ligaments; acetabular labrum and ligament of the head of the femur; glenoid labrum, rotator
   * cuff tendon and subacromial bursa). Box 400 x 420. labels(tl, at, stagger) reveals the names;
   * isolate(tl, part, at, dur) dims everything but one part (part ids in handle.parts).
   * Facts: OpenStax A&P 2e 9.4 (synovial joint structure) and 9.6 (knee, hip, shoulder).
   */
  A.joint = function (parent, opts) {
    var o = opts || {};
    var kind = o.joint || 'knee';
    var g = grp(parent, 'an-joint an-joint-' + kind, o.x, o.y, o.scale);
    var parts = {}, names = [];
    function part(id) { var pg = svg('g', { 'class': 'an-part', 'data-part': id }, g); parts[id] = pg; return pg; }
    function name(s, x, y, lx, ly, anchor, from) { named(g, names, s, x, y, lx, ly, anchor, 15, from); }
    var B = { fill: IN.bone, stroke: IN.boneLine, 'stroke-width': 2.4 };
    var cart = { fill: 'none', stroke: IN.ivory, 'stroke-width': 9, 'stroke-linecap': 'round' };
    if (kind === 'knee') {
      var cap0 = part('capsule');
      svg('path', { d: 'M132 120 C110 200 112 270 140 320 L262 320 C300 280 316 200 296 120', fill: IN.fluid, stroke: IN.roseDeep, 'stroke-width': 3.4 }, cap0);
      var quad = part('quadriceps');
      svg('path', { d: 'M236 0 L300 0 L302 84 L272 104 Z', fill: IN.rose, stroke: IN.roseLine, 'stroke-width': 2 }, quad);
      svg('path', { d: 'M286 86 C288 100 286 114 282 134', stroke: IN.ivory, 'stroke-width': 16, 'stroke-linecap': 'round', fill: 'none' }, quad);
      var fem = part('femur');
      svg('path', { d: 'M150 0 L232 0 L238 118 C262 140 262 200 228 222 C204 238 168 236 148 216 C124 190 128 140 152 120 Z', fill: B.fill, stroke: B.stroke, 'stroke-width': B['stroke-width'] }, fem);
      var tib = part('tibia');
      svg('path', { d: 'M132 262 L270 262 C276 276 264 292 248 300 L240 420 L170 420 L162 300 C144 292 128 278 132 262 Z', fill: B.fill, stroke: B.stroke, 'stroke-width': B['stroke-width'] }, tib);
      var car = part('cartilage');
      svg('path', Object.assign({ d: 'M142 196 C150 228 196 240 228 222 C246 210 256 190 256 168' }, cart), car);
      svg('path', Object.assign({ d: 'M140 262 L262 262' }, cart), car);
      var men = part('menisci');
      svg('path', { d: 'M136 258 L170 258 L136 244 Z', fill: IN.ivory, stroke: IN.ivoryLine, 'stroke-width': 1.8 }, men);
      svg('path', { d: 'M266 258 L232 258 L268 242 Z', fill: IN.ivory, stroke: IN.ivoryLine, 'stroke-width': 1.8 }, men);
      var cru = part('cruciates');
      svg('path', { d: 'M222 258 L170 176', stroke: IN.ivoryLine, 'stroke-width': 9, 'stroke-linecap': 'round', fill: 'none' }, cru);
      svg('path', { d: 'M176 262 L214 184', stroke: IN.ivory, 'stroke-width': 9, 'stroke-linecap': 'round', fill: 'none' }, cru);
      var pat = part('patella');
      svg('ellipse', { cx: 282, cy: 172, rx: 22, ry: 40, fill: IN.bone, stroke: IN.boneLine, 'stroke-width': 2.4, transform: 'rotate(-8 282 172)' }, pat);
      var pl = part('patellar-ligament');
      svg('path', { d: 'M288 210 C292 244 276 280 258 304', stroke: IN.ivory, 'stroke-width': 10, 'stroke-linecap': 'round', fill: 'none' }, pl);
      name('femur', 20, 60, 150, 70);
      name('quadriceps and its tendon', 316, 60, 290, 104, 'start');
      name('patella', 330, 170, 304, 170);
      name('articular cartilage', 330, 236, 254, 196);
      name('patellar ligament', 300, 330, 276, 284);
      name('menisci', 20, 250, 140, 254);
      name('cruciate ligaments', 20, 210, 180, 200);
      name('synovial cavity', 20, 300, 136, 290);
      name('tibia', 20, 380, 168, 380);
    } else if (kind === 'hip') {
      var capH = part('capsule');
      svg('path', { d: 'M96 92 C150 60 250 76 290 140 C306 188 290 236 262 262 L196 286 C150 240 110 170 96 92 Z', fill: IN.fluid, stroke: IN.roseDeep, 'stroke-width': 5 }, capH);
      var pel = part('pelvis');
      svg('path', { d: 'M0 0 L250 0 C262 40 256 70 236 92 C214 72 186 64 158 66 C120 70 92 96 84 134 C80 160 90 186 104 204 L60 250 L0 250 Z', fill: B.fill, stroke: B.stroke, 'stroke-width': 2.4 }, pel);
      var femH = part('femur');
      svg('path', { d: 'M150 112 C186 84 236 100 246 142 C252 168 242 192 224 206 L280 260 C300 250 324 256 330 276 C338 300 322 320 310 330 L300 420 L232 420 L236 330 L180 246 C150 236 128 210 124 180 C120 150 130 126 150 112 Z', fill: B.fill, stroke: B.stroke, 'stroke-width': 2.4 }, femH);
      var carH = part('cartilage');
      svg('path', Object.assign({ d: 'M132 168 C126 124 166 94 208 98 C230 102 244 118 250 136' }, cart), carH);
      svg('path', Object.assign({ d: 'M100 170 C98 120 132 84 176 80 C206 78 226 88 240 100', 'stroke-width': 7 }, cart), carH);
      var lab = part('labrum');
      svg('path', { d: 'M232 88 L260 100 L240 112 Z M100 196 L84 214 L110 214 Z', fill: IN.ivory, stroke: IN.ivoryLine, 'stroke-width': 1.8 }, lab);
      var lt = part('ligament-of-head');
      svg('path', { d: 'M150 146 C134 140 120 132 110 124', stroke: IN.ivoryLine, 'stroke-width': 7, 'stroke-linecap': 'round', fill: 'none' }, lt);
      var ilio = part('iliofemoral');
      svg('path', { d: 'M260 70 C290 120 300 190 282 252', stroke: IN.ivoryLine, 'stroke-width': 10, 'stroke-linecap': 'round', fill: 'none', opacity: 0.9 }, ilio);
      name('hip bone (acetabulum)', 20, 30, 120, 80);
      name('acetabular labrum', 290, 60, 252, 98);
      name('head of femur', 300, 150, 230, 150);
      name('articular cartilage', 300, 120, 246, 132);
      name('ligament of the head', 20, 300, 124, 132);
      name('capsule (iliofemoral ligament)', 300, 230, 286, 222);
      name('femoral neck', 300, 290, 258, 236);
    } else {
      var acro = part('acromion');
      svg('path', { d: 'M40 30 C120 10 230 14 300 40 C306 54 296 64 282 66 C220 52 150 52 96 70 Z', fill: B.fill, stroke: B.stroke, 'stroke-width': 2.4 }, acro);
      var bur = part('bursa');
      svg('path', { d: 'M150 84 C190 70 240 72 268 86 C238 92 186 94 150 84 Z', fill: IN.fluid, stroke: IN.roseLine, 'stroke-width': 1.6 }, bur);
      var cuff = part('rotator-cuff');
      svg('path', { d: 'M0 80 C80 70 180 80 250 100 C290 112 310 140 312 168 L292 172 C284 140 260 124 230 118 C160 104 80 102 0 108 Z', fill: IN.rose, stroke: IN.roseLine, 'stroke-width': 2 }, cuff);
      svg('path', { d: 'M232 104 C270 112 300 136 310 170', stroke: IN.ivory, 'stroke-width': 9, 'stroke-linecap': 'round', fill: 'none' }, cuff);
      var capS = part('capsule');
      svg('path', { d: 'M110 126 C140 112 270 120 300 180 C318 240 292 300 248 318 C200 330 150 300 128 262 C112 230 104 170 110 126 Z', fill: IN.fluid, stroke: IN.roseDeep, 'stroke-width': 3 }, capS);
      var scap = part('scapula');
      svg('path', { d: 'M0 120 L96 132 C120 150 128 200 118 236 L96 252 L0 300 Z', fill: B.fill, stroke: B.stroke, 'stroke-width': 2.4 }, scap);
      var hum = part('humerus');
      svg('path', { d: 'M150 170 C160 124 236 120 270 156 C296 186 292 236 262 262 L262 420 L196 420 L196 268 C162 254 142 214 150 170 Z', fill: B.fill, stroke: B.stroke, 'stroke-width': 2.4 }, hum);
      var carS = part('cartilage');
      svg('path', Object.assign({ d: 'M150 176 C156 132 226 126 262 154' }, cart), carS);
      svg('path', Object.assign({ d: 'M120 160 C130 186 130 214 120 238', 'stroke-width': 7 }, cart), carS);
      var labS = part('labrum');
      svg('path', { d: 'M110 148 L128 156 L116 166 Z M110 250 L128 240 L118 230 Z', fill: IN.ivory, stroke: IN.ivoryLine, 'stroke-width': 1.8 }, labS);
      name('acromion', 320, 30, 290, 46);
      name('subacromial bursa', 320, 80, 258, 84);
      name('rotator cuff tendon', 320, 130, 300, 148);
      name('head of humerus', 320, 210, 260, 200);
      // the two glenoid names stack below the scapula; their leaders leave from opposite ends so they never cross
      name('glenoid labrum', 20, 345, 112, 250, 'start', [60, 329]);
      name('glenoid (shallow socket)', 20, 385, 124, 205, 'start', [222, 378]);
      name('loose capsule', 320, 300, 250, 306);
    }
    var tagEl = tagIllustrative(g, 0, 440, 'ILLUSTRATIVE · SCHEMATIC SECTION');
    return {
      g: g, joint: kind, parts: parts, names: names, tag: tagEl,
      labels: revealer(names),
      /** Dim every part except `id` to 25 % over dur, hold, and return them at `at + dur + hold`. */
      isolate: function (tl, id, at, dur, hold) {
        var d = dur || 0.4, h = hold === undefined ? 1.6 : hold;
        Object.keys(parts).forEach(function (k) {
          if (k === id) return;
          tl.fromTo(parts[k], { opacity: 1 }, { opacity: 0.25, duration: d, ease: 'power1.inOut', immediateRender: false }, at);
          tl.fromTo(parts[k], { opacity: 0.25 }, { opacity: 1, duration: d, ease: 'power1.inOut', immediateRender: false }, at + d + h);
        });
        return at + 2 * d + h;
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
