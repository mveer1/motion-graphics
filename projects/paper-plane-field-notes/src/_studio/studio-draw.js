/*
 * Motion Lab studio runtime - drawing (src/studio/studio-draw.js)
 * Stroke drawing, line-art reveals, procedural hand-drawn lines, morph-compatible blob and
 * wave paths, organic deformation and seeded particles. Requires studio-core.js.
 */
(function (global) {
  'use strict';

  var Studio = global.Studio;
  if (!Studio) throw new Error('studio-draw.js requires studio-core.js');
  var D = Studio.draw = {};

  function fmt(n) { return (Math.round(n * 100) / 100).toString(); }

  /** Total stroke length of an SVG geometry element. */
  D.length = function (el) {
    return el && el.getTotalLength ? el.getTotalLength() : 0;
  };

  /**
   * Hide strokes by dashing them to their own length. `slack` (e.g. 0.3) lengthens the dash so a
   * stroke that later morphs into a longer variant stays fully drawn. Safe to call twice.
   */
  D.prepare = function (targets, slack) {
    Studio.all(targets).forEach(function (p) {
      if (p.__studioLen) return;
      var len = Math.ceil(D.length(p) * (1 + (slack || 0))) + 2;
      p.__studioLen = len;
      p.style.strokeDasharray = len + ' ' + len;
      p.style.strokeDashoffset = String(len);
    });
  };

  /**
   * Draw strokes on. Duration is either fixed (o.duration) or proportional to length at
   * o.speed px/s, clamped to [o.min, o.max], which reads as a steady pen.
   * Returns the time the last stroke finishes.
   */
  D.stroke = function (tl, targets, at, options) {
    var o = options || {};
    var els = Studio.all(targets);
    D.prepare(els, o.slack);
    var stagger = o.stagger === undefined ? 0.08 : o.stagger;
    var ease = o.ease || 'power2.inOut';
    var t = at, end = at;
    els.forEach(function (p, i) {
      var len = p.__studioLen;
      var dur = o.duration || Math.min(o.max || 1.6, Math.max(o.min || 0.25, len / (o.speed || 900)));
      var start = o.sequential ? t : at + i * stagger;
      tl.fromTo(p, { strokeDashoffset: len }, { strokeDashoffset: 0, duration: dur, ease: ease }, start);
      t = start + dur;
      end = Math.max(end, start + dur);
    });
    return end;
  };

  /** Erase strokes (reverse of stroke). Uses immediateRender:false so earlier draws stay intact. */
  D.erase = function (tl, targets, at, options) {
    var o = options || {};
    var els = Studio.all(targets);
    D.prepare(els);
    var dur = o.duration || 0.5;
    els.forEach(function (p, i) {
      tl.fromTo(p, { strokeDashoffset: 0 }, { strokeDashoffset: -p.__studioLen, duration: dur, ease: o.ease || 'power2.in', immediateRender: false }, at + i * (o.stagger || 0));
    });
    return at + dur + (els.length - 1) * (o.stagger || 0);
  };

  function isStroked(el) {
    if (el.hasAttribute('data-no-draw')) return false;
    var s = global.getComputedStyle(el);
    return s.stroke && s.stroke !== 'none' && parseFloat(s.strokeWidth) > 0;
  }

  /**
   * Line-art reveal: draw every stroked shape in a group in reading order, then fade in
   * elements marked data-fill. order: 'document' | 'left-right' | 'top-down'.
   */
  D.lineArt = function (tl, group, at, options) {
    var o = options || {};
    var root = typeof group === 'string' ? document.querySelector(group) : group;
    var shapes = Studio.all('path, line, polyline, polygon, circle, ellipse, rect', root).filter(isStroked);
    if (o.order === 'left-right' || o.order === 'top-down') {
      var key = o.order === 'left-right' ? 'x' : 'y';
      shapes = shapes.map(function (el) { return { el: el, b: el.getBBox() }; })
        .sort(function (a, b) { return a.b[key] - b.b[key]; })
        .map(function (r) { return r.el; });
    }
    var end = D.stroke(tl, shapes, at, {
      speed: o.speed || 700,
      stagger: o.stagger === undefined ? 0.12 : o.stagger,
      min: o.min || 0.3,
      max: o.max || 1.4,
      ease: o.ease || 'power1.inOut'
    });
    var fills = Studio.all('[data-fill]', root);
    if (fills.length) {
      tl.fromTo(fills, { autoAlpha: 0 }, { autoAlpha: 1, duration: o.fillDuration || 0.5, ease: 'power1.out', stagger: 0.06 }, end - (o.fillOverlap === undefined ? 0.3 : o.fillOverlap));
      end += 0.2;
    }
    return end;
  };

  /** Hand-drawn line between two points as a path `d` with seeded wobble. */
  D.handLine = function (seed, x1, y1, x2, y2, options) {
    var o = options || {};
    var n = o.segments || 6;
    var jitter = o.jitter === undefined ? 0.012 : o.jitter;
    var r = Studio.rng(seed);
    var dx = x2 - x1, dy = y2 - y1;
    var len = Math.sqrt(dx * dx + dy * dy) || 1;
    var nx = -dy / len, ny = dx / len;
    var pts = [];
    for (var i = 0; i <= n; i++) {
      var t = i / n;
      var off = (i === 0 || i === n) ? 0 : (r() * 2 - 1) * jitter * len;
      pts.push([x1 + dx * t + nx * off, y1 + dy * t + ny * off]);
    }
    var d = 'M' + fmt(pts[0][0]) + ' ' + fmt(pts[0][1]);
    for (var j = 1; j < pts.length; j++) {
      var mx = (pts[j - 1][0] + pts[j][0]) / 2, my = (pts[j - 1][1] + pts[j][1]) / 2;
      d += ' Q' + fmt(pts[j - 1][0]) + ' ' + fmt(pts[j - 1][1]) + ' ' + fmt(mx) + ' ' + fmt(my);
    }
    d += ' L' + fmt(pts[n][0]) + ' ' + fmt(pts[n][1]);
    return d;
  };

  function closedCurve(pts, tension) {
    var k = (tension === undefined ? 1 : tension) / 6;
    var n = pts.length;
    var d = 'M' + fmt(pts[0][0]) + ' ' + fmt(pts[0][1]);
    for (var i = 0; i < n; i++) {
      var p0 = pts[(i - 1 + n) % n], p1 = pts[i], p2 = pts[(i + 1) % n], p3 = pts[(i + 2) % n];
      var c1x = p1[0] + (p2[0] - p0[0]) * k, c1y = p1[1] + (p2[1] - p0[1]) * k;
      var c2x = p2[0] - (p3[0] - p1[0]) * k, c2y = p2[1] - (p3[1] - p1[1]) * k;
      d += ' C' + fmt(c1x) + ' ' + fmt(c1y) + ' ' + fmt(c2x) + ' ' + fmt(c2y) + ' ' + fmt(p2[0]) + ' ' + fmt(p2[1]);
    }
    return d + ' Z';
  }

  /**
   * Organic closed blob. Every blob with the same `points` count has the same command
   * structure, so any two can be morphed with D.morph. `phase` shifts the noise for variants.
   */
  D.blob = function (seed, options) {
    var o = options || {};
    var n = o.points || 8;
    var cx = o.cx || 0, cy = o.cy || 0, r = o.r || 100;
    var rx = o.rx || r, ry = o.ry || r;
    var wobble = o.wobble === undefined ? 0.16 : o.wobble;
    var noise = Studio.noise1(seed);
    var phase = o.phase || 0;
    var pts = [];
    for (var i = 0; i < n; i++) {
      var a = (i / n) * Math.PI * 2 + (o.rotate || 0);
      var k = 1 + wobble * noise(i * 1.7 + phase * 3.1);
      pts.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]);
    }
    return closedCurve(pts, o.tension);
  };

  /**
   * Filled region under a smooth wavy edge (liquid surface). The edge runs across the frame at
   * `level` (0 = top, 1 = bottom of height). Same structure for all levels and phases.
   */
  D.wave = function (seed, options) {
    var o = options || {};
    var w = o.width, h = o.height;
    var n = o.points || 10;
    var amp = o.amplitude === undefined ? 0.03 * h : o.amplitude;
    var noise = Studio.noise1(seed);
    var y0 = (o.level === undefined ? 0.5 : o.level) * h;
    var phase = o.phase || 0;
    var pts = [];
    for (var i = 0; i <= n; i++) {
      var x = (i / n) * w;
      var y = y0 + amp * (Math.sin(i * 0.9 + phase * 2.4) * 0.6 + noise(i * 0.8 + phase * 2) * 0.4);
      pts.push([x, y]);
    }
    var below = o.fill === 'above' ? -h * 0.05 : h * 1.05;
    var d = 'M' + fmt(-w * 0.05) + ' ' + fmt(below) + ' L' + fmt(-w * 0.05) + ' ' + fmt(pts[0][1]);
    for (var j = 0; j < pts.length - 1; j++) {
      var p0 = pts[Math.max(0, j - 1)], p1 = pts[j], p2 = pts[j + 1], p3 = pts[Math.min(pts.length - 1, j + 2)];
      var c1x = p1[0] + (p2[0] - p0[0]) / 6, c1y = p1[1] + (p2[1] - p0[1]) / 6;
      var c2x = p2[0] - (p3[0] - p1[0]) / 6, c2y = p2[1] - (p3[1] - p1[1]) / 6;
      d += ' C' + fmt(c1x) + ' ' + fmt(c1y) + ' ' + fmt(c2x) + ' ' + fmt(c2y) + ' ' + fmt(p2[0]) + ' ' + fmt(p2[1]);
    }
    d += ' L' + fmt(w * 1.05) + ' ' + fmt(pts[n][1]) + ' L' + fmt(w * 1.05) + ' ' + fmt(below) + ' Z';
    return d;
  };

  function signature(d) {
    var letters = (d.match(/[a-zA-Z]/g) || []).join('');
    var nums = (d.match(/-?\d*\.?\d+(?:e[-+]?\d+)?/gi) || []).length;
    return letters + '#' + nums;
  }

  /** True when two path strings have the same commands and number count (GSAP core can tween them). */
  D.compatible = function (a, b) { return signature(a) === signature(b); };

  /** Morph a path between structurally compatible shapes (GSAP core string interpolation). */
  D.morph = function (tl, path, toD, at, options) {
    var o = options || {};
    var el = typeof path === 'string' ? document.querySelector(path) : path;
    var fromD = o.from || el.getAttribute('d');
    if (!D.compatible(fromD, toD)) {
      throw new Error('Studio.draw.morph: incompatible paths (' + signature(fromD) + ' vs ' + signature(toD) + '). Generate both with Studio.draw.blob/wave or resample them.');
    }
    tl.fromTo(el, { attr: { d: fromD } }, { attr: { d: toD }, duration: o.duration || 0.8, ease: o.ease || 'power2.inOut', immediateRender: false }, at);
    return at + (o.duration || 0.8);
  };

  /**
   * Organic deformation: morph through seeded variants between `from` and `to`, ending on the
   * starting shape so the motion can loop. make(phase) must return compatible path strings, and
   * the path must already show make(0) at `from` (set it at build or end the previous morph on it).
   */
  D.wobble = function (tl, path, from, to, make, options) {
    var o = options || {};
    var el = typeof path === 'string' ? document.querySelector(path) : path;
    var period = o.period || 1.2;
    var steps = Math.max(1, Math.floor((to - from) / period));
    var first = make(0);
    var prev = first;
    for (var i = 1; i <= steps; i++) {
      var next = i === steps ? first : make(i);
      tl.fromTo(el, { attr: { d: prev } }, { attr: { d: next }, duration: period, ease: o.ease || 'sine.inOut', immediateRender: false }, from + (i - 1) * period);
      prev = next;
    }
    return from + steps * period;
  };

  /** Marching dashes for a fixed interval (dash pattern comes from CSS stroke-dasharray). */
  D.march = function (tl, targets, from, to, options) {
    var o = options || {};
    var distance = (o.speed || 40) * (to - from);
    tl.fromTo(Studio.all(targets), { strokeDashoffset: 0 }, { strokeDashoffset: o.reverse ? distance : -distance, duration: to - from, ease: 'none', immediateRender: false }, from);
    return to;
  };

  /**
   * Seeded particles inside a box. Returns [{el, x, y, r, seed}] so callers can animate them.
   * Elements are SVG circles appended to `svgParent`.
   */
  D.particles = function (svgParent, count, seed, options) {
    var o = options || {};
    var r = Studio.rng(seed);
    var box = o.box || { x: 0, y: 0, width: 100, height: 100 };
    var out = [];
    for (var i = 0; i < count; i++) {
      var p = {
        x: box.x + r() * box.width,
        y: box.y + r() * box.height,
        r: (o.minR || 2) + r() * ((o.maxR || 5) - (o.minR || 2)),
        seed: Math.floor(r() * 1e9)
      };
      p.el = Studio.svg('circle', { cx: fmt(p.x), cy: fmt(p.y), r: fmt(p.r), 'class': o.className || 'st-particle' }, svgParent);
      if (o.fill) p.el.setAttribute('fill', o.fill);
      out.push(p);
    }
    return out;
  };

  /** Let particles fall/drift from their seeded start by (dx, dy) with seeded variation. */
  D.drift = function (tl, particles, from, to, options) {
    var o = options || {};
    particles.forEach(function (p) {
      var r = Studio.rng(p.seed);
      var delay = r() * (o.spread || 0.6);
      var dur = Math.max(0.2, (to - from) - delay);
      var dx = (o.dx || 0) + (r() * 2 - 1) * (o.jitterX || 0);
      var dy = (o.dy || 0) * (0.7 + r() * 0.6);
      var fade = Math.min(0.3, dur / 4);
      tl.fromTo(p.el, { x: 0, y: 0 }, { x: dx, y: dy, duration: dur, ease: o.ease || 'power1.in' }, from + delay);
      tl.fromTo(p.el, { autoAlpha: 0 }, { autoAlpha: 1, duration: fade, ease: 'none' }, from + delay);
      if (o.fadeOut !== false) {
        tl.fromTo(p.el, { autoAlpha: 1 }, { autoAlpha: 0, duration: fade, ease: 'none', immediateRender: false }, from + delay + dur - fade);
      }
    });
    return to;
  };

  // ------------------------------------------------------------------ morph-ready shapes
  function samplePolygon(verts, n) {
    var segs = [], total = 0;
    for (var i = 0; i < verts.length; i++) {
      var a = verts[i], b = verts[(i + 1) % verts.length];
      var l = Math.sqrt((b[0] - a[0]) * (b[0] - a[0]) + (b[1] - a[1]) * (b[1] - a[1]));
      segs.push({ a: a, b: b, l: l, start: total });
      total += l;
    }
    var out = [], s = 0;
    for (var k = 0; k < n; k++) {
      var target = (k / n) * total;
      while (s < segs.length - 1 && segs[s].start + segs[s].l < target) s++;
      var g = segs[s], f = g.l ? (target - g.start) / g.l : 0;
      out.push([g.a[0] + (g.b[0] - g.a[0]) * f, g.a[1] + (g.b[1] - g.a[1]) * f]);
    }
    return out;
  }

  function startAtTop(pts, cx, cy) {
    var best = 0, bestD = Infinity;
    for (var i = 0; i < pts.length; i++) {
      var a = Math.atan2(pts[i][1] - cy, pts[i][0] - cx) + Math.PI / 2;
      var d = Math.abs(Math.atan2(Math.sin(a), Math.cos(a)));
      if (d < bestD - 1e-9) { bestD = d; best = i; }
    }
    return pts.slice(best).concat(pts.slice(0, best));
  }

  /**
   * Morph-ready closed shape: kind 'circle' | 'polygon' | 'star' | 'rect' | 'poly'. Shapes with the
   * same `points` count share one command structure (M, L..., Z), start at the top and run clockwise,
   * so any two morph with D.morph without twisting. options: {cx, cy, r, rx, ry (circle),
   * sides (polygon), spikes, inner (star), w, h (rect), verts ([[x, y], ...] clockwise, poly),
   * rotate (deg, default -90), points (48)}. For poly the centre defaults to the vertex centroid.
   */
  D.shape = function (kind, options) {
    var o = options || {};
    var n = o.points || 48;
    var cx = o.cx || 0, cy = o.cy || 0, r = o.r || 100;
    var rot = (o.rotate === undefined ? -90 : o.rotate) * Math.PI / 180;
    var pts = [], verts = [], i;
    if (kind === 'circle') {
      for (i = 0; i < n; i++) {
        var a = -Math.PI / 2 + (i / n) * Math.PI * 2;
        pts.push([cx + Math.cos(a) * (o.rx || r), cy + Math.sin(a) * (o.ry || r)]);
      }
    } else {
      if (kind === 'polygon') {
        var sides = o.sides || 3;
        for (i = 0; i < sides; i++) verts.push([cx + Math.cos(rot + (i / sides) * Math.PI * 2) * r, cy + Math.sin(rot + (i / sides) * Math.PI * 2) * r]);
      } else if (kind === 'star') {
        var spikes = o.spikes || 5, inner = o.inner === undefined ? 0.45 : o.inner;
        for (i = 0; i < spikes * 2; i++) {
          var ang = rot + (i / (spikes * 2)) * Math.PI * 2, rr = i % 2 ? r * inner : r;
          verts.push([cx + Math.cos(ang) * rr, cy + Math.sin(ang) * rr]);
        }
      } else if (kind === 'rect') {
        var hw = (o.w || r * 2) / 2, hh = (o.h || r * 2) / 2;
        verts = [[cx - hw, cy - hh], [cx + hw, cy - hh], [cx + hw, cy + hh], [cx - hw, cy + hh]];
      } else if (kind === 'poly') {
        if (!o.verts || o.verts.length < 3) throw new Error('Studio.draw.shape: poly needs options.verts with 3 or more [x, y] points');
        verts = o.verts.map(function (v) { return [v[0], v[1]]; });
        if (o.cx === undefined && o.cy === undefined) {
          cx = verts.reduce(function (s, v) { return s + v[0]; }, 0) / verts.length;
          cy = verts.reduce(function (s, v) { return s + v[1]; }, 0) / verts.length;
        }
      } else {
        throw new Error('Studio.draw.shape: unknown kind "' + kind + '"');
      }
      pts = startAtTop(samplePolygon(verts, n), cx, cy);
    }
    var d = 'M' + fmt(pts[0][0]) + ' ' + fmt(pts[0][1]);
    for (i = 1; i < pts.length; i++) d += ' L' + fmt(pts[i][0]) + ' ' + fmt(pts[i][1]);
    return d + ' Z';
  };

  /**
   * Morph through compatible shapes in order: `duration` per morph, `hold` between morphs. The path
   * must already show shapes[0]. Returns the time the last morph ends.
   */
  D.morphChain = function (tl, path, shapes, at, options) {
    var o = options || {};
    var dur = o.duration || 0.7, hold = o.hold === undefined ? 0.4 : o.hold;
    var t = at;
    for (var i = 1; i < shapes.length; i++) {
      D.morph(tl, path, shapes[i], t, { from: shapes[i - 1], duration: dur, ease: o.ease || 'power3.inOut' });
      t += dur + (i < shapes.length - 1 ? hold : 0);
    }
    return t;
  };

  // ------------------------------------------------------------------ pen-led strokes
  function invertEase(E, y) {
    var lo = 0, hi = 1;
    for (var i = 0; i < 40; i++) {
      var mid = (lo + hi) / 2;
      if (E(mid) < y) lo = mid; else hi = mid;
    }
    return (lo + hi) / 2;
  }

  /**
   * Pen-led stroke: the path draws on while a dot rides its tip at the same eased progress, so the
   * line reads as made by a moving point. The dot is a circle created after the path (class
   * st-pen-dot) unless options.dot is given; it is also stored as path.__penDot. Expects a monotonic
   * ease. options: {duration | speed (px/s), min, max, ease, dot, dotRadius, dotColor, keepDot, samples}
   */
  D.pen = function (tl, path, at, options) {
    var o = options || {};
    var el = typeof path === 'string' ? document.querySelector(path) : path;
    if (!el) throw new Error('Studio.draw.pen: path not found');
    D.prepare(el, o.slack);
    var L = D.length(el), len = el.__studioLen;
    var dur = o.duration || Math.min(o.max || 2.4, Math.max(o.min || 0.4, L / (o.speed || 600)));
    var ease = o.ease || 'power2.inOut';
    tl.fromTo(el, { strokeDashoffset: len }, { strokeDashoffset: len - L, duration: dur, ease: ease }, at);
    var dot = o.dot ? (typeof o.dot === 'string' ? document.querySelector(o.dot) : o.dot) : null;
    if (!dot) {
      var sw = parseFloat(global.getComputedStyle(el).strokeWidth) || 4;
      dot = Studio.svg('circle', { r: fmt(o.dotRadius || sw * 1.6), 'class': 'st-pen-dot' });
      if (o.dotColor) dot.setAttribute('fill', o.dotColor);
      if (el.getAttribute('transform')) dot.setAttribute('transform', el.getAttribute('transform'));
      el.parentNode.insertBefore(dot, el.nextSibling);
    }
    el.__penDot = dot;
    // Sample evenly in time (slow ease ends) and in arc length (fast middle) so linear steps stay on the tip.
    var K = o.samples || Math.max(12, Math.min(72, Math.round(L / 14)));
    var N = Math.max(1, Math.ceil(dur * (o.rate || 60)));
    var E = global.gsap.parseEase(ease);
    var us = [], i;
    for (i = 0; i <= N; i++) us.push(i / N);
    for (i = 1; i < K; i++) us.push(invertEase(E, i / K));
    us.sort(function (a, b) { return a - b; });
    var pts = [], ts = [];
    us.forEach(function (u) {
      if (ts.length && u - ts[ts.length - 1] < 1e-6) return;
      var p = el.getPointAtLength(L * Math.max(0, Math.min(1, E(u))));
      ts.push(u);
      pts.push([p.x, p.y]);
    });
    dot.setAttribute('cx', fmt(pts[0][0]));
    dot.setAttribute('cy', fmt(pts[0][1]));
    tl.fromTo(dot, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.001, ease: 'none', immediateRender: true }, at);
    for (var j = 1; j < ts.length; j++) {
      tl.fromTo(dot, { attr: { cx: pts[j - 1][0], cy: pts[j - 1][1] } },
        { attr: { cx: pts[j][0], cy: pts[j][1] }, duration: (ts[j] - ts[j - 1]) * dur, ease: 'none', immediateRender: false }, at + ts[j - 1] * dur);
    }
    if (o.keepDot === false) {
      tl.fromTo(dot, { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.2, ease: 'power1.in', immediateRender: false }, at + dur);
    }
    return at + dur;
  };

  function smoothPath(pts) {
    var d = 'M' + fmt(pts[0][0]) + ' ' + fmt(pts[0][1]);
    for (var j = 1; j < pts.length; j++) {
      var mx = (pts[j - 1][0] + pts[j][0]) / 2, my = (pts[j - 1][1] + pts[j][1]) / 2;
      d += ' Q' + fmt(pts[j - 1][0]) + ' ' + fmt(pts[j - 1][1]) + ' ' + fmt(mx) + ' ' + fmt(my);
    }
    return d + ' L' + fmt(pts[pts.length - 1][0]) + ' ' + fmt(pts[pts.length - 1][1]);
  }

  /** Hand-drawn loop around (cx, cy): a quick pen ellipse that overshoots its start (seeded). */
  D.loop = function (seed, cx, cy, rx, ry, options) {
    var o = options || {};
    var r = Studio.rng(seed);
    var n = o.segments || 20, turns = o.turns || 1.12;
    var jitter = o.jitter === undefined ? 0.05 : o.jitter, drift = o.drift === undefined ? 0.1 : o.drift;
    var a0 = (o.start === undefined ? -2.3 : o.start) + (r() - 0.5) * 0.4;
    var pts = [];
    for (var i = 0; i <= n; i++) {
      var a = a0 + (i / n) * Math.PI * 2 * turns;
      var k = 1 + (r() * 2 - 1) * jitter + (i / n - 0.5) * drift;
      pts.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]);
    }
    return smoothPath(pts);
  };

  // ------------------------------------------------------------------ layers, connectors, grids
  /** Full-frame SVG layer in #root pixel space (viewBox = frame) for connectors and annotations. */
  D.layer = function (parent, className) {
    var f = Studio.format;
    var host = parent ? (typeof parent === 'string' ? document.querySelector(parent) : parent) : document.getElementById('root');
    return Studio.svg('svg', {
      'class': 'st-layer-svg' + (className ? ' ' + className : ''), width: f.width, height: f.height,
      viewBox: '0 0 ' + f.width + ' ' + f.height, 'aria-hidden': 'true'
    }, host);
  };

  /**
   * Connector from element a to element b, measured as they render at `at` (Studio.boxAt): a cubic
   * curve leaving the facing edges, drawn on from `at`, with an optional arrowhead. `svg` is a
   * full-frame layer (D.layer). options: {axis 'x'|'y', bend (0..1), gap (px), arrow, dashed,
   * className, duration, ease}. Returns the end time.
   */
  D.connect = function (tl, svg, a, b, at, options) {
    var o = options || {};
    var A = Studio.boxAt(tl, a, at), B = Studio.boxAt(tl, b, at);
    var gap = o.gap === undefined ? Studio.u(1) : o.gap;
    var dx = B.cx - A.cx, dy = B.cy - A.cy;
    var horizontal = o.axis ? o.axis === 'x' : Math.abs(dx) >= Math.abs(dy);
    var p1, p2, n1, n2, s;
    if (horizontal) {
      s = dx >= 0 ? 1 : -1;
      p1 = [A.cx + s * (A.w / 2 + gap), A.cy];
      p2 = [B.cx - s * (B.w / 2 + gap), B.cy];
      n1 = [s, 0]; n2 = [-s, 0];
    } else {
      s = dy >= 0 ? 1 : -1;
      p1 = [A.cx, A.cy + s * (A.h / 2 + gap)];
      p2 = [B.cx, B.cy - s * (B.h / 2 + gap)];
      n1 = [0, s]; n2 = [0, -s];
    }
    var dist = Math.sqrt((p2[0] - p1[0]) * (p2[0] - p1[0]) + (p2[1] - p1[1]) * (p2[1] - p1[1]));
    var bend = (o.bend === undefined ? 0.45 : o.bend) * dist;
    var c2 = [p2[0] + n2[0] * bend, p2[1] + n2[1] * bend];
    var d = 'M' + fmt(p1[0]) + ' ' + fmt(p1[1]) + ' C' + fmt(p1[0] + n1[0] * bend) + ' ' + fmt(p1[1] + n1[1] * bend) +
      ' ' + fmt(c2[0]) + ' ' + fmt(c2[1]) + ' ' + fmt(p2[0]) + ' ' + fmt(p2[1]);
    var cls = 'st-connector' + (o.dashed ? ' st-connector-dashed' : '') + (o.className ? ' ' + o.className : '');
    var path = Studio.svg('path', { d: d, 'class': cls, fill: 'none' }, svg);
    var end;
    if (o.dashed) {
      tl.fromTo(path, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.3, ease: 'power1.out', immediateRender: true }, at);
      end = at + 0.3;
    } else {
      end = D.stroke(tl, path, at, { duration: o.duration || Math.min(1.2, Math.max(0.35, dist / 900)), ease: o.ease || 'power2.inOut' });
    }
    if (o.arrow !== false) {
      var hl = o.head || Studio.u(1.6);
      var ang = Math.atan2(p2[1] - c2[1], p2[0] - c2[0]);
      var h1 = [p2[0] - hl * Math.cos(ang - 0.5), p2[1] - hl * Math.sin(ang - 0.5)];
      var h2 = [p2[0] - hl * Math.cos(ang + 0.5), p2[1] - hl * Math.sin(ang + 0.5)];
      var head = Studio.svg('path', {
        d: 'M' + fmt(h1[0]) + ' ' + fmt(h1[1]) + ' L' + fmt(p2[0]) + ' ' + fmt(p2[1]) + ' L' + fmt(h2[0]) + ' ' + fmt(h2[1]),
        'class': 'st-connector st-connector-head' + (o.className ? ' ' + o.className : ''), fill: 'none'
      }, svg);
      end = D.stroke(tl, head, end - 0.05, { duration: 0.18, ease: 'power1.out' });
    }
    return end;
  };

  /**
   * Grid of cells (divs) filling a positioned `parent`, row-major. options.truchet = seed fills each
   * cell with a quarter-arc tile at a seeded 0/90 degree start (cell.__baseRot) for pattern waves.
   */
  D.grid = function (parent, rows, cols, options) {
    var o = options || {};
    var host = typeof parent === 'string' ? document.querySelector(parent) : parent;
    var g = Studio.el('div', 'st-grid' + (o.className ? ' ' + o.className : ''), null, host);
    g.style.gridTemplateColumns = 'repeat(' + cols + ', 1fr)';
    g.style.gridTemplateRows = 'repeat(' + rows + ', 1fr)';
    if (o.gap !== undefined) g.style.gap = o.gap + 'px';
    var cells = [];
    var r = o.truchet !== undefined ? Studio.rng(o.truchet) : null;
    for (var i = 0; i < rows * cols; i++) {
      var c = Studio.el('div', 'st-grid-cell', null, g);
      if (r) {
        c.innerHTML = '<svg class="st-truchet" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">' +
          '<path d="M50 0 A50 50 0 0 1 0 50 M100 50 A50 50 0 0 0 50 100"></path></svg>';
        c.__baseRot = r() < 0.5 ? 0 : 90;
        global.gsap.set(c, { rotation: c.__baseRot });
      }
      cells.push(c);
    }
    g.__grid = [rows, cols];
    return cells;
  };
})(typeof window !== 'undefined' ? window : this);
