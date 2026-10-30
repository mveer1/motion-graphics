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
})(typeof window !== 'undefined' ? window : this);
