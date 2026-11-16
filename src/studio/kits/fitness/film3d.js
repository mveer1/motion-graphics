/*
 * Motion Lab fitness kit - 3D film helpers (src/studio/kits/fitness/film3d.js). Needs tibi3d.js and studio-core.js.
 * Written for the first narrated 3D films (lower body, 2026-11-12). Load after exercises3d.js.
 *
 * Everything that follows the 3D skeleton (joint pins, a dashed bar line, a muscle line) is updated in T3.bind's
 * onFrame(values, t) from the same pure function of time that poses Tibi, so it stays deterministic under seeking.
 * Static brand pieces (title card, badge, citation, end card) keep using graphics.js with GSAP tweens.
 *
 *   var FX = T3.film;
 *   var ov = FX.overlay(rootEl);                       // SVG 720x1280 above the canvas, below the captions
 *   var pin = FX.pin(ov, {text: 'Knee', color: '#F2553D'});
 *   ... onFrame: pin.set(stage.project(fig.world('knL')), FX.win(t, 3.2, 8.0));
 *   var ln = FX.line(ov, {dash: '10 8', color: '#1B1D29'}); ln.set([p1, p2], alpha);
 *   FX.shot(m, at, dur, {az, el, dist, tx, ty, tz, fov}, ease)    // camera moves as motion tracks (cut: dur 0)
 *   FX.show(fig, t, [[a, b], ...])                     // figure visible inside any window
 */
(function (global) {
  'use strict';
  var Studio = global.Studio || (global.Studio = {});
  var F = Studio.kit && Studio.kit.fitness, T3 = F && F.t3d;
  if (!T3) throw new Error('kits/fitness/film3d.js needs tibi3d.js loaded first');
  var P = F.palette || {};
  var NS = 'http://www.w3.org/2000/svg';
  var FX = T3.film = {};
  var FONT_D = "'Outfit', 'Inter', sans-serif", FONT_M = "'JetBrains Mono', monospace";

  function el(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function r2(v) { return Math.round(v * 10) / 10; }

  /** Opacity window: 0 before a, fades in over `fin`, holds, fades out over `fout` ending at b. Pure function of t. */
  FX.win = function (t, a, b, fin, fout) {
    fin = fin === undefined ? 0.35 : fin; fout = fout === undefined ? 0.35 : fout;
    if (t <= a || t >= b) return 0;
    var i = fin > 0 ? Math.min(1, (t - a) / fin) : 1, o = fout > 0 ? Math.min(1, (b - t) / fout) : 1;
    var x = Math.min(i, o); return x * x * (3 - 2 * x);
  };
  /** 0..1 progress of t through [a, b], eased (sine.inOut). */
  FX.prog = function (t, a, b) {
    var x = Math.max(0, Math.min(1, (t - a) / (b - a)));
    return -(Math.cos(Math.PI * x) - 1) / 2;
  };

  /** The SVG overlay: a 720x1280 (or w x h) layer over the WebGL canvas. Append it before the captions are built. */
  FX.overlay = function (root, o) {
    o = o || {};
    var w = o.width || 720, h = o.height || 1280;
    var s = el('svg', { viewBox: '0 0 ' + w + ' ' + h, width: w, height: h, 'aria-hidden': 'true' });
    s.style.cssText = 'position:absolute;left:0;top:0;width:' + w + 'px;height:' + h + 'px;overflow:visible;pointer-events:none';
    root.appendChild(s);
    return s;
  };

  /** A joint pin: ringed dot on the point, label pill offset from it. set(p {x,y}, alpha). */
  FX.pin = function (parent, o) {
    o = o || {};
    var g = el('g', { opacity: 0 }, parent), col = o.color || P.ink || '#1B1D29';
    var dx = o.dx === undefined ? 30 : o.dx, dy = o.dy === undefined ? -46 : o.dy, size = o.size || 24;
    var lead = el('line', { stroke: col, 'stroke-width': 2.4, 'stroke-linecap': 'round' }, g);
    var ring = el('circle', { r: 11, fill: 'rgba(255,255,255,0.75)', stroke: col, 'stroke-width': 3.2 }, g);
    var lab = el('g', {}, g);
    // o.center: the label sits centred on (point + dy), e.g. a tag over a head (a side-anchored tag clipped at the frame edge)
    var w = (o.text || '').length * size * 0.56 + size * 1.1;
    var bx = function (ww) { return o.center ? -ww / 2 : dx < 0 ? -ww : 0; };
    var bg = el('rect', { x: bx(w), y: -size * 0.95, width: w, height: size * 1.55, rx: size * 0.5, fill: col }, lab);
    var tx = el('text', { x: bx(w) + w / 2, y: size * 0.18, 'text-anchor': 'middle', 'font-family': FONT_D, 'font-weight': 700, 'font-size': size, fill: o.ink || '#FFFFFF' }, lab);
    tx.textContent = o.text || '';
    if (o.center) { dx = 0; ring.setAttribute('r', 0); lead.setAttribute('stroke-width', 0); }
    var curW = w;
    return {
      g: g,
      text: function (s) { tx.textContent = s; curW = s.length * size * 0.56 + size * 1.1; bg.setAttribute('width', curW); bg.setAttribute('x', bx(curW)); tx.setAttribute('x', bx(curW) + curW / 2); },
      /** set(p, alpha[, dx, dy]): dx/dy override the offsets for this frame, so one pin can serve several exercises (a negative dx puts the label left of the point). */
      set: function (p, a, odx, ody) {
        g.setAttribute('opacity', r2(a * 100) / 100);
        if (a <= 0) return;
        var ddx = odx === undefined ? dx : odx, ddy = ody === undefined ? dy : ody;
        if (odx !== undefined && !o.center) { var sh = ddx < 0 ? -curW : 0; bg.setAttribute('x', sh); tx.setAttribute('x', sh + curW / 2); }
        ring.setAttribute('cx', r2(p.x)); ring.setAttribute('cy', r2(p.y));
        lead.setAttribute('x1', r2(p.x)); lead.setAttribute('y1', r2(p.y));
        lead.setAttribute('x2', r2(p.x + ddx * 0.8)); lead.setAttribute('y2', r2(p.y + ddy + size * 0.3));
        lab.setAttribute('transform', 'translate(' + r2(p.x + ddx) + ' ' + r2(p.y + ddy) + ')');
      }
    };
  };

  /**
   * A surface-EMG sensor, drawn as a SENSOR (visual language for measurements, 2026-11-13):
   *   - an electrode pair ON the skin at the projected point (a sensor reads the electrical signal under it, not a whole muscle),
   *   - a lead wire to a small card,
   *   - a trace card: the signal as a GRAPH, labelled illustrative (the shape is synthetic; only the relative amplitude is the claim).
   * set(p {x,y}, alpha, t, amp 0..1): amp scales the trace (higher vs lower reading); the waveform is a pure function of t.
   * Never use a muscle-shaped object for this: an electrode is not a muscle and a trace is not anatomy.
   */
  FX.sensor = function (parent, o) {
    o = o || {};
    var g = el('g', { opacity: 0 }, parent), col = o.color || '#1B1D29', cw = o.cardW || 124, ch = o.cardH || 62, dx = o.dx === undefined ? 40 : o.dx, dy = o.dy === undefined ? 40 : o.dy;
    var wire = el('path', { fill: 'none', stroke: col, 'stroke-width': 2.2, 'stroke-linecap': 'round', 'stroke-dasharray': '1 0' }, g);
    var e1 = el('circle', { r: 7.5, fill: '#FFFFFF', stroke: col, 'stroke-width': 2.8 }, g), e2 = el('circle', { r: 7.5, fill: '#FFFFFF', stroke: col, 'stroke-width': 2.8 }, g);
    var d1 = el('circle', { r: 2.4, fill: col }, g), d2 = el('circle', { r: 2.4, fill: col }, g);
    var card = el('g', {}, g);
    el('rect', { x: 0, y: 0, width: cw, height: ch, rx: 10, fill: 'rgba(255,255,255,0.95)', stroke: col, 'stroke-width': 2 }, card);
    el('line', { x1: 8, x2: cw - 8, y1: ch * 0.55, y2: ch * 0.55, stroke: '#C9CCD8', 'stroke-width': 1, 'stroke-dasharray': '3 3' }, card);
    var trace = el('path', { fill: 'none', stroke: col, 'stroke-width': 2.2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, card);
    var lab = el('text', { x: cw - 8, y: ch - 6, 'text-anchor': 'end', 'font-family': FONT_M, 'font-weight': 600, 'font-size': 11, fill: '#4A4E60' }, card);
    lab.textContent = o.label || 'illustrative';
    if (o.title) { var tt = el('text', { x: 9, y: 17, 'font-family': FONT_D, 'font-weight': 800, 'font-size': 15, fill: col }, card); tt.textContent = o.title; }
    return {
      g: g,
      set: function (p, a, t, amp) {
        g.setAttribute('opacity', r2(a * 100) / 100);
        if (a <= 0) return;
        var x1 = p.x - 8, x2 = p.x + 8, y1 = p.y, y2 = p.y + 1;
        e1.setAttribute('cx', r2(x1)); e1.setAttribute('cy', r2(y1)); e2.setAttribute('cx', r2(x2)); e2.setAttribute('cy', r2(y2));
        d1.setAttribute('cx', r2(x1)); d1.setAttribute('cy', r2(y1)); d2.setAttribute('cx', r2(x2)); d2.setAttribute('cy', r2(y2));
        var cx = p.x + dx, cy = p.y + dy;
        wire.setAttribute('d', 'M' + r2(p.x) + ' ' + r2(p.y + 8) + ' Q' + r2(p.x) + ' ' + r2(cy + ch / 2) + ' ' + r2(cx) + ' ' + r2(cy + ch / 2));
        card.setAttribute('transform', 'translate(' + r2(cx) + ' ' + r2(cy) + ')');
        var pts = [], N = 34, A = ch * 0.27 * Math.max(0.05, Math.min(1, amp === undefined ? 1 : amp));
        for (var i = 0; i < N; i++) {
          var u = i / (N - 1), ph = 2 * Math.PI * (u * 5 + t * 1.3);
          var y = ch * 0.55 + A * (0.62 * Math.sin(ph) + 0.38 * Math.sin(2.7 * ph + 1.3) * Math.sin(2 * Math.PI * (u * 1.7 + t * 0.6)));
          pts.push((8 + u * (cw - 16)).toFixed(1) + ' ' + y.toFixed(1));
        }
        trace.setAttribute('d', 'M' + pts.join(' L'));
      }
    };
  };

  /** A small state chip: a coloured dot and text. Used to say where the viewer is looking ("Under the skin", "On the skin"). set(p, alpha). */
  FX.chip = function (parent, o) {
    o = o || {};
    var g = el('g', { opacity: 0 }, parent), size = o.size || 19, w = (o.text || '').length * size * 0.54 + size * 2.6;
    el('rect', { x: 0, y: -size * 0.95, width: w, height: size * 1.7, rx: size * 0.85, fill: o.fill || 'rgba(255,255,255,0.94)', stroke: o.color || '#7C3F45', 'stroke-width': 2 }, g);
    el('circle', { cx: size * 0.9, cy: -size * 0.1, r: size * 0.32, fill: o.color || '#7C3F45' }, g);
    var t = el('text', { x: size * 1.55, y: size * 0.18, 'font-family': FONT_D, 'font-weight': 700, 'font-size': size, fill: '#1B1D29' }, g); t.textContent = o.text || '';
    return { g: g, w: w, set: function (p, a) { g.setAttribute('opacity', r2(a * 100) / 100); if (a > 0) g.setAttribute('transform', 'translate(' + r2(p.x) + ' ' + r2(p.y) + ')'); } };
  };

  // ------------------------------------------------------------------ instructional overlays (2026-11-13): phases, reps, tempo, angle, trail, cue
  var KIND_COLOR = { up: '#F2553D', down: '#FFB224', hold: '#8A8D9C' };
  /**
   * The rep HUD: "REP 2 / 3", the phase pill (colour = what the muscle is doing: coral shortening, marigold lengthening, grey holding) and a
   * tempo bar whose segments are the phases of ONE rep, drawn to scale, with a playhead. Every value is a pure function of t.
   *   var hud = FX.hud(ov, {x: 48, y: 1010, width: 624, def: T3.exercises.curl, o: {at, period, reps}});   hud.set(t, alpha);
   */
  FX.hud = function (parent, o) {
    var g = el('g', { opacity: 0 }, parent), W = o.width || 620, x0 = o.x || 48, y0 = o.y || 1000, map = o.def.phaseMap;
    var hasNote = o.note !== false;
    var panel = el('rect', { x: x0 - 16, y: y0 - 44, width: W + 32, height: hasNote ? 118 : 90, rx: 18, fill: 'rgba(255,255,255,0.94)', stroke: '#1B1D29', 'stroke-width': 2 }, g);
    var rep = el('text', { x: x0, y: y0 - 10, 'font-family': FONT_M, 'font-weight': 700, 'font-size': 22, fill: '#1B1D29' }, g);
    var pillG = el('g', {}, g), pillBg = el('rect', { x: 0, y: -26, width: 100, height: 38, rx: 19, fill: '#8A8D9C' }, pillG);
    var pillTx = el('text', { x: 16, y: 0, 'font-family': FONT_D, 'font-weight': 800, 'font-size': 24, fill: '#FFFFFF' }, pillG);
    var bar = el('g', { transform: 'translate(' + x0 + ' ' + (y0 + 20) + ')' }, g), segs = [], acc = 0;
    map.forEach(function (p) {
      var w = (p.b - p.a) * W, r = el('rect', { x: p.a * W, y: 0, width: Math.max(2, w - 2), height: 14, rx: 4, fill: KIND_COLOR[p.kind] || '#8A8D9C', opacity: 0.35 }, bar);
      segs.push({ el: r, a: p.a, b: p.b });
    });
    var head = el('rect', { x: 0, y: -6, width: 5, height: 26, rx: 2.5, fill: '#1B1D29' }, bar);
    if (hasNote) {
      var tag = el('text', { x: x0 + W, y: y0 + 62, 'text-anchor': 'end', 'font-family': FONT_M, 'font-weight': 500, 'font-size': 13, fill: '#4A4E60' }, g);
      tag.textContent = o.note || 'one rep, to scale · illustrative tempo';
    }
    return {
      g: g,
      set: function (t, a) {
        g.setAttribute('opacity', r2(a * 100) / 100);
        if (a <= 0) return;
        var ph = T3.phaseAt(o.def, o.o, t), per = o.o.period, f = ph.rep < 1 || ph.rep > o.o.n ? (ph.rep < 1 ? 0 : 1) : ((t - (o.o.at || 0)) / per - (ph.rep - 1));
        rep.textContent = 'REP ' + Math.max(1, Math.min(ph.rep, ph.n)) + ' / ' + ph.n;
        var w = Math.max(96, ph.label.length * 14 + 34);
        pillBg.setAttribute('width', w); pillBg.setAttribute('fill', KIND_COLOR[ph.kind] || '#8A8D9C');
        pillTx.textContent = ph.label; pillG.setAttribute('transform', 'translate(' + (x0 + W - w) + ' ' + (y0 - 8) + ')');
        segs.forEach(function (sg) { sg.el.setAttribute('opacity', f >= sg.a && f < sg.b && ph.rep >= 1 && ph.rep <= o.o.n ? 1 : 0.35); });
        head.setAttribute('x', r2(Math.max(0, Math.min(1, f)) * W - 2.5));
      }
    };
  };

  /** A joint-angle indicator: two short rays, an arc and the number. set(joint {x,y}, a {x,y}, c {x,y}, alpha, degrees, label). Screen-space, true angle supplied. */
  FX.angle = function (parent, o) {
    o = o || {};
    var g = el('g', { opacity: 0 }, parent), col = o.color || '#1B1D29', R = o.radius || 54;
    var r1 = el('line', { stroke: col, 'stroke-width': 3, 'stroke-linecap': 'round', 'stroke-dasharray': '2 7' }, g), r2l = el('line', { stroke: col, 'stroke-width': 3, 'stroke-linecap': 'round', 'stroke-dasharray': '2 7' }, g);
    var arc = el('path', { fill: 'rgba(255,255,255,0.55)', stroke: col, 'stroke-width': 3.4 }, g);
    var txt = el('text', { 'font-family': FONT_D, 'font-weight': 800, 'font-size': o.size || 30, fill: col, 'paint-order': 'stroke', stroke: '#F6F3EC', 'stroke-width': 6, 'stroke-linejoin': 'round' }, g);
    var sub = el('text', { 'font-family': FONT_M, 'font-weight': 600, 'font-size': 12, fill: '#4A4E60' }, g);
    return {
      g: g,
      set: function (j, a, c, alpha, deg, label) {
        g.setAttribute('opacity', r2(alpha * 100) / 100);
        if (alpha <= 0) return;
        var a1 = Math.atan2(a.y - j.y, a.x - j.x), a2 = Math.atan2(c.y - j.y, c.x - j.x), d = a2 - a1;
        while (d > Math.PI) d -= 2 * Math.PI; while (d < -Math.PI) d += 2 * Math.PI;
        var p1 = { x: j.x + R * Math.cos(a1), y: j.y + R * Math.sin(a1) }, p2 = { x: j.x + R * Math.cos(a1 + d), y: j.y + R * Math.sin(a1 + d) };
        r1.setAttribute('x1', r2(j.x)); r1.setAttribute('y1', r2(j.y)); r1.setAttribute('x2', r2(j.x + 1.5 * R * Math.cos(a1))); r1.setAttribute('y2', r2(j.y + 1.5 * R * Math.sin(a1)));
        r2l.setAttribute('x1', r2(j.x)); r2l.setAttribute('y1', r2(j.y)); r2l.setAttribute('x2', r2(j.x + 1.5 * R * Math.cos(a1 + d))); r2l.setAttribute('y2', r2(j.y + 1.5 * R * Math.sin(a1 + d)));
        arc.setAttribute('d', 'M' + r2(j.x) + ' ' + r2(j.y) + ' L' + r2(p1.x) + ' ' + r2(p1.y) + ' A' + R + ' ' + R + ' 0 0 ' + (d > 0 ? 1 : 0) + ' ' + r2(p2.x) + ' ' + r2(p2.y) + ' Z');
        var mid = a1 + d / 2;
        txt.setAttribute('x', r2(j.x + (R + 18) * Math.cos(mid) - 2)); txt.setAttribute('y', r2(j.y + (R + 18) * Math.sin(mid) + 10));
        txt.textContent = Math.round(deg) + '°';
        sub.setAttribute('x', r2(j.x + (R + 18) * Math.cos(mid))); sub.setAttribute('y', r2(j.y + (R + 18) * Math.sin(mid) + 26)); sub.textContent = label || 'illustrative';
      }
    };
  };

  /** A movement trail: the path a joint or a dumbbell travels (3D points sampled once, projected every frame) and a dot where it is now. */
  FX.trail = function (parent, o) {
    o = o || {};
    var g = el('g', { opacity: 0 }, parent), col = o.color || '#2F56E0';
    var path = el('path', { fill: 'none', stroke: col, 'stroke-width': o.width || 4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-dasharray': o.dash || '3 9', opacity: 0.8 }, g);
    var dot = el('circle', { r: o.dotR || 9, fill: col, stroke: '#FFFFFF', 'stroke-width': 3 }, g);
    return {
      g: g,
      /** pts: projected {x,y} list of the whole path; cur: the {x,y} of the tracked point now. */
      set: function (pts, cur, alpha) {
        g.setAttribute('opacity', r2(alpha * 100) / 100);
        if (alpha <= 0) return;
        path.setAttribute('d', pts.map(function (p, i) { return (i ? 'L' : 'M') + r2(p.x) + ' ' + r2(p.y); }).join(' '));
        dot.setAttribute('cx', r2(cur.x)); dot.setAttribute('cy', r2(cur.y));
      }
    };
  };

  /** A coaching cue card: the exercise-specific message that matches what the body is doing now. set(text, alpha). */
  FX.cue = function (parent, o) {
    o = o || {};
    var g = el('g', { opacity: 0 }, parent), x = o.x === undefined ? 360 : o.x, y = o.y || 190, size = o.size || 34;
    var bg = el('rect', { y: -size * 1.0, height: size * 1.55, rx: size * 0.5, fill: o.fill || '#1B1D29' }, g);
    var tx = el('text', { 'text-anchor': 'middle', 'font-family': FONT_D, 'font-weight': 800, 'font-size': size, fill: o.ink || '#FFFFFF' }, g);
    return {
      g: g,
      set: function (text, alpha) {
        g.setAttribute('opacity', r2(alpha * 100) / 100);
        if (alpha <= 0 || text === undefined) return;
        if (tx.textContent !== text) {
          tx.textContent = text; var w = text.length * size * 0.54 + size * 1.5;
          bg.setAttribute('width', w); bg.setAttribute('x', -w / 2); tx.setAttribute('x', 0);
        }
        g.setAttribute('transform', 'translate(' + x + ' ' + y + ')');
      }
    };
  };

  /** A projected polyline (bar line, muscle line, toe line). set([{x,y}, ...], alpha, draw 0..1). */
  FX.line = function (parent, o) {
    o = o || {};
    var g = el('g', { opacity: 0 }, parent);
    var path = el('path', { fill: 'none', stroke: o.color || '#1B1D29', 'stroke-width': o.width || 4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, g);
    if (o.dash) path.setAttribute('stroke-dasharray', o.dash);
    var dots = (o.dots ? [0, 1, 2, 3] : []).map(function () { return el('circle', { r: o.dotR || 7, fill: o.color || '#1B1D29', stroke: '#FFFFFF', 'stroke-width': 2.5 }, g); });
    var label = null;
    if (o.text) {
      label = el('text', { 'font-family': o.mono ? FONT_M : FONT_D, 'font-weight': 700, 'font-size': o.size || 22, fill: o.color || '#1B1D29', 'text-anchor': o.anchor || 'start' }, g);
      label.textContent = o.text;
    }
    return {
      g: g, path: path, label: label,
      set: function (pts, a, draw) {
        g.setAttribute('opacity', r2(a * 100) / 100);
        if (a <= 0 || !pts.length) return;
        if (draw !== undefined && draw < 1 && pts.length === 2) {
          pts = [pts[0], { x: pts[0].x + (pts[1].x - pts[0].x) * draw, y: pts[0].y + (pts[1].y - pts[0].y) * draw }];
        }
        path.setAttribute('d', pts.map(function (p, i) { return (i ? 'L' : 'M') + r2(p.x) + ' ' + r2(p.y); }).join(' '));
        dots.forEach(function (d, i) { var p = pts[i]; d.setAttribute('opacity', p ? 1 : 0); if (p) { d.setAttribute('cx', r2(p.x)); d.setAttribute('cy', r2(p.y)); } });
        if (label) { var q = pts[o.labelAt === undefined ? pts.length - 1 : o.labelAt]; label.setAttribute('x', r2(q.x + (o.lx || 12))); label.setAttribute('y', r2(q.y + (o.ly || 8))); }
      }
    };
  };

  /** Camera move as motion tracks (cut when dur <= 0). Declares bases on first use so nothing reads undefined. */
  FX.shot = function (m, at, dur, c, ease) {
    var v = {};
    ['az', 'el', 'dist', 'fov', 'tx', 'ty', 'tz'].forEach(function (k) { if (c[k] !== undefined) v['cam.' + k] = c[k]; });
    m.to(at, dur > 0 ? dur : 0.0001, v, dur > 0 ? (ease || 'sine.inOut') : 'none');
    return at + Math.max(0, dur);
  };
  /** Base camera for frame 0. */
  FX.camera = function (m, c) {
    var v = {};
    ['az', 'el', 'dist', 'fov', 'tx', 'ty', 'tz'].forEach(function (k) { if (c[k] !== undefined) v['cam.' + k] = c[k]; });
    m.base(v);
  };
  /** Figure visibility from windows [[a, b], ...] (cuts happen on frames; a figure and its props switch together). */
  FX.show = function (fig, t, wins) {
    var on = false;
    for (var i = 0; i < wins.length; i++) if (t >= wins[i][0] && t < wins[i][1]) { on = true; break; }
    fig.setVisible(on);
    return on;
  };

  /**
   * A measured-number bar panel (static, GSAP-revealed): rows [{label, value, color, note}], max, unit.
   * Only plot numbers that are in the dossier; the panel prints the unit and the source under it.
   */
  FX.bars = function (parent, o) {
    var g = el('g', { opacity: 0, transform: 'translate(' + (o.x || 0) + ' ' + (o.y || 0) + ')' }, parent);
    var w = o.width || 560, rowH = o.rowH || 50, lab = o.labelW || 170;
    var bgp = el('rect', { x: -18, y: -58, width: w + 36, height: (o.rows.length * rowH) + 88 + (o.foot ? 26 : 0), rx: 18, fill: 'rgba(255,255,255,0.92)', stroke: '#1B1D29', 'stroke-width': 2 }, g);
    var title = el('text', { x: 0, y: -22, 'font-family': FONT_D, 'font-weight': 800, 'font-size': 24, fill: '#1B1D29' }, g); title.textContent = o.title || '';
    var bars = [], vals = [];
    o.rows.forEach(function (r, i) {
      var y = i * rowH + 6;
      var t1 = el('text', { x: 0, y: y + 24, 'font-family': FONT_D, 'font-weight': 700, 'font-size': 20, fill: '#1B1D29' }, g); t1.textContent = r.label;
      var full = (w - lab - 70) * r.value / o.max;
      var b = el('rect', { x: lab, y: y + 4, width: 0, height: rowH - 18, rx: 7, fill: r.color || '#2F56E0' }, g);
      var v = el('text', { x: lab + 8, y: y + 25, 'font-family': FONT_M, 'font-weight': 700, 'font-size': 19, fill: '#1B1D29', opacity: 0 }, g);
      v.textContent = r.text || String(r.value);
      bars.push({ el: b, full: Math.max(4, full) }); vals.push({ el: v, x: lab + Math.max(4, full) + 10 });
    });
    if (o.foot) { var ft = el('text', { x: 0, y: o.rows.length * rowH + 22, 'font-family': FONT_M, 'font-weight': 500, 'font-size': 15, fill: '#4A4E60' }, g); ft.textContent = o.foot; }
    return {
      g: g,
      /** step: seconds between rows, or an array of absolute reveal times (one per row, to snap rows to spoken words). */
      show: function (tl, at, step) {
        step = step || 0.35;
        var when = function (i) { return Array.isArray(step) ? step[i] : at + 0.2 + i * step; };
        tl.fromTo(g, { opacity: 0 }, { opacity: 1, duration: 0.3, immediateRender: true }, at);
        bars.forEach(function (b, i) {
          tl.fromTo(b.el, { attr: { width: 0 } }, { attr: { width: r2(b.full) }, duration: 0.6, ease: 'power2.out', immediateRender: true }, when(i));
          vals[i].el.setAttribute('x', r2(vals[i].x));
          tl.fromTo(vals[i].el, { opacity: 0 }, { opacity: 1, duration: 0.25, immediateRender: true }, when(i) + 0.4);
        });
        return when(bars.length - 1) + 0.6;
      },
      hide: function (tl, at) { tl.fromTo(g, { opacity: 1 }, { opacity: 0, duration: 0.3, immediateRender: false }, at); return at + 0.3; }
    };
  };
})(typeof window !== 'undefined' ? window : globalThis);
