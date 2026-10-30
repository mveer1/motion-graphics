/*
 * Motion Lab studio runtime - motion (src/studio/studio-motion.js)
 * Scene transitions (wipe, iris, push, shape cover, liquid, match cut, mask reveal), 2.5D depth
 * and camera moves, object assembly, rhythm helpers and paper/grain texture.
 * Requires studio-core.js and studio-draw.js.
 */
(function (global) {
  'use strict';

  var Studio = global.Studio;
  if (!Studio || !Studio.draw) throw new Error('studio-motion.js requires studio-core.js and studio-draw.js');
  var FX = Studio.fx = {};
  var SP = Studio.space = {};
  var RH = Studio.rhythm = {};
  var TX = Studio.texture = {};

  function first(target) {
    return Studio.all(target)[0];
  }

  function overlayLayer() {
    var root = document.getElementById('root');
    var layer = root.querySelector(':scope > .st-overlay');
    if (!layer) {
      layer = Studio.el('div', 'st-overlay');
      layer.setAttribute('aria-hidden', 'true');
      layer.setAttribute('data-layout-ignore', '');
      root.appendChild(layer);
    }
    return layer;
  }

  /** Overlay element that starts hidden inline, so rewinding any tween leaves it hidden. */
  function overlayElement(tag, className) {
    var el = tag === 'svg' ? Studio.svg('svg', { 'class': className }) : Studio.el(tag, className);
    el.style.opacity = '0';
    el.style.visibility = 'hidden';
    overlayLayer().appendChild(el);
    return el;
  }

  var INSET_FROM = {
    left: 'inset(0% 100% 0% 0%)',
    right: 'inset(0% 0% 0% 100%)',
    top: 'inset(0% 0% 100% 0%)',
    bottom: 'inset(100% 0% 0% 0%)',
    center: 'inset(50% 50% 50% 50%)'
  };
  var INSET_OPEN = 'inset(0% 0% 0% 0%)';

  /** Element-level mask reveal from an edge (or the centre). Entrance: hidden until `at`. */
  FX.reveal = function (tl, target, at, options) {
    var o = options || {};
    var dur = o.duration || 0.8;
    var stagger = o.stagger || 0;
    tl.fromTo(target, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.001, ease: 'none', stagger: stagger }, at);
    tl.fromTo(target,
      { clipPath: INSET_FROM[o.from || 'left'] },
      { clipPath: INSET_OPEN, duration: dur, ease: o.ease || 'power3.inOut', stagger: stagger },
      at);
    return at + dur + stagger * Math.max(0, Studio.all(target).length - 1);
  };

  /**
   * Directional wipe between scenes. The incoming scene is revealed from `from` edge; an optional
   * coloured edge bar rides the wipe front. Returns the end time.
   */
  FX.wipe = function (tl, outTarget, inTarget, at, options) {
    var o = options || {};
    var from = o.from || 'left';
    var dur = o.duration || 0.9;
    var ease = o.ease || 'power3.inOut';
    Studio.show(tl, inTarget, at);
    tl.fromTo(inTarget,
      { clipPath: INSET_FROM[from] },
      { clipPath: INSET_OPEN, duration: dur, ease: ease, immediateRender: false },
      at);
    if (o.edge) {
      var f = Studio.format;
      var bar = overlayElement('div', 'st-wipe-edge');
      bar.style.background = o.edge;
      var thick = Studio.u(o.edgeWidth || 1.2);
      var horizontal = from === 'left' || from === 'right';
      bar.style.width = horizontal ? thick + 'px' : f.width + 'px';
      bar.style.height = horizontal ? f.height + 'px' : thick + 'px';
      var startPos = { left: -thick, right: f.width, top: -thick, bottom: f.height }[from];
      var endPos = { left: f.width, right: -thick, top: f.height, bottom: -thick }[from];
      var axis = horizontal ? 'x' : 'y';
      var a = {}, b = { duration: dur, ease: ease, immediateRender: false };
      a[axis] = startPos;
      b[axis] = endPos;
      Studio.show(tl, bar, at);
      tl.fromTo(bar, a, b, at);
      Studio.hide(tl, bar, at + dur);
    }
    Studio.hide(tl, outTarget, at + dur);
    return at + dur;
  };

  /** Iris (circle) opening on the incoming scene, centred at (cx%, cy%). */
  FX.iris = function (tl, outTarget, inTarget, at, options) {
    var o = options || {};
    var dur = o.duration || 0.9;
    var c = (o.cx === undefined ? 50 : o.cx) + '% ' + (o.cy === undefined ? 50 : o.cy) + '%';
    Studio.show(tl, inTarget, at);
    tl.fromTo(inTarget,
      { clipPath: 'circle(0% at ' + c + ')' },
      { clipPath: 'circle(150% at ' + c + ')', duration: dur, ease: o.ease || 'power2.inOut', immediateRender: false },
      at);
    Studio.hide(tl, outTarget, at + dur);
    return at + dur;
  };

  /** Push: the incoming scene shoves the outgoing one off frame. */
  FX.push = function (tl, outTarget, inTarget, at, options) {
    var o = options || {};
    var f = Studio.format;
    var dur = o.duration || 0.8;
    var ease = o.ease || 'power3.inOut';
    var dir = o.from || 'right';
    var axis = (dir === 'left' || dir === 'right') ? 'x' : 'y';
    var span = axis === 'x' ? f.width : f.height;
    var sign = (dir === 'right' || dir === 'bottom') ? 1 : -1;
    var inFrom = {}, inTo = { duration: dur, ease: ease, immediateRender: false };
    inFrom[axis] = sign * span;
    inTo[axis] = 0;
    var outFrom = {}, outTo = { duration: dur, ease: ease, immediateRender: false };
    outFrom[axis] = 0;
    outTo[axis] = -sign * span;
    Studio.show(tl, inTarget, at);
    tl.fromTo(inTarget, inFrom, inTo, at);
    tl.fromTo(outTarget, outFrom, outTo, at);
    Studio.hide(tl, outTarget, at + dur);
    return at + dur;
  };

  /**
   * Shape transition: a shape grows from (x, y) to cover the frame in `color`, the scenes swap
   * underneath, then the shape shrinks into (exitX, exitY). Positions in px.
   */
  FX.shapeCover = function (tl, outTarget, inTarget, at, options) {
    var o = options || {};
    var f = Studio.format;
    var dur = o.duration || 1.1;
    var half = dur / 2;
    var x = o.x === undefined ? f.width / 2 : o.x;
    var y = o.y === undefined ? f.height / 2 : o.y;
    var ex = o.exitX === undefined ? x : o.exitX;
    var ey = o.exitY === undefined ? y : o.exitY;
    var diag = Math.sqrt(f.width * f.width + f.height * f.height);
    var size = diag * 2.2;
    var shape = overlayElement('div', 'st-cover-shape');
    shape.style.width = size + 'px';
    shape.style.height = size + 'px';
    shape.style.left = (x - size / 2) + 'px';
    shape.style.top = (y - size / 2) + 'px';
    shape.style.background = o.color || Studio.token('--c-accent', '#c8462b');
    shape.style.borderRadius = o.square ? '0' : '50%';
    Studio.show(tl, shape, at);
    tl.fromTo(shape, { scale: 0, x: 0, y: 0 }, { scale: 1, duration: half, ease: o.easeIn || 'power3.in', immediateRender: false }, at);
    Studio.cut(tl, outTarget, inTarget, at + half);
    tl.fromTo(shape, { scale: 1, x: 0, y: 0 }, { scale: 0, x: ex - x, y: ey - y, duration: half, ease: o.easeOut || 'power3.out', immediateRender: false }, at + half);
    Studio.hide(tl, shape, at + dur);
    return at + dur;
  };

  /**
   * Liquid transition: a wavy surface rises to fill the frame in `color`; scenes swap when it is
   * full. mode 'drain' lets the liquid fall away to reveal the new scene; mode 'become' keeps the
   * colour (give the incoming scene the same background) and hides the overlay after the swap.
   */
  FX.liquid = function (tl, outTarget, inTarget, at, options) {
    var o = options || {};
    var f = Studio.format;
    var dur = o.duration || 1.4;
    var steps = o.steps || 6;
    var seed = o.seed || 5;
    var svg = overlayElement('svg', 'st-liquid');
    svg.setAttribute('width', f.width);
    svg.setAttribute('height', f.height);
    svg.setAttribute('viewBox', '0 0 ' + f.width + ' ' + f.height);
    svg.setAttribute('preserveAspectRatio', 'none');
    var amp = (o.amplitude || 0.035) * f.height;
    var shape = function (level, i) {
      return Studio.draw.wave(seed, { width: f.width, height: f.height, level: level, phase: i * 0.37, amplitude: amp, points: 10 });
    };
    var path = Studio.svg('path', { d: shape(1.1, 0), fill: o.color || Studio.token('--c-accent', '#c8462b') }, svg);
    var rise = o.mode === 'become' ? dur * 0.8 : dur / 2;
    var stepDur = rise / steps;
    var prev = shape(1.1, 0);
    Studio.show(tl, svg, at);
    for (var i = 1; i <= steps; i++) {
      var level = 1.1 - (1.25 * i) / steps;
      var next = shape(level, i);
      tl.fromTo(path, { attr: { d: prev } }, { attr: { d: next }, duration: stepDur, ease: i === 1 ? 'power1.in' : 'none', immediateRender: false }, at + (i - 1) * stepDur);
      prev = next;
    }
    Studio.cut(tl, outTarget, inTarget, at + rise);
    if (o.mode === 'become') {
      Studio.hide(tl, svg, at + rise + 0.001);
      return at + rise;
    }
    var drain = dur - rise;
    for (var j = 1; j <= steps; j++) {
      var lv = -0.15 + (1.3 * j) / steps;
      var nx = shape(lv, steps + j);
      tl.fromTo(path, { attr: { d: prev } }, { attr: { d: nx }, duration: drain / steps, ease: j === steps ? 'power1.out' : 'none', immediateRender: false }, at + rise + (j - 1) * (drain / steps));
      prev = nx;
    }
    Studio.hide(tl, svg, at + dur);
    return at + dur;
  };

  function layoutBox(el) {
    var root = document.getElementById('root');
    var x = 0, y = 0, n = el;
    while (n && n !== root) {
      x += n.offsetLeft || 0;
      y += n.offsetTop || 0;
      n = n.offsetParent;
    }
    return { x: x, y: y, w: el.offsetWidth, h: el.offsetHeight };
  }

  /**
   * Match cut: hard cut between scenes while `toEl` starts exactly where `fromEl` was (position and
   * scale) and settles into its own place. Measures layout boxes, so call it before adding other
   * transform tweens to `toEl`. Both elements should be HTML elements (wrap SVG art in a div).
   */
  FX.matchCut = function (tl, fromEl, toEl, outTarget, inTarget, at, options) {
    var o = options || {};
    var a = layoutBox(first(fromEl)), b = layoutBox(first(toEl));
    var s = b.w ? a.w / b.w : 1;
    var dx = (a.x + a.w / 2) - (b.x + b.w / 2);
    var dy = (a.y + a.h / 2) - (b.y + b.h / 2);
    var dur = o.duration || 0.9;
    Studio.cut(tl, outTarget, inTarget, at);
    tl.fromTo(first(toEl), { x: dx, y: dy, scale: s, transformOrigin: '50% 50%' }, { x: 0, y: 0, scale: 1, duration: dur, ease: o.ease || 'power3.inOut', immediateRender: false }, at);
    return at + dur;
  };

  // ------------------------------------------------------------------ 2.5D space
  // Depth tokens follow the epic-design skill: data-depth 0 (far) .. 5 (near).
  var DEPTH_FACTOR = [0.1, 0.25, 0.45, 0.7, 1.0, 1.2];

  SP.factor = function (el) {
    var d = parseInt(el.getAttribute('data-depth'), 10);
    if (isNaN(d)) d = 4;
    return DEPTH_FACTOR[Math.max(0, Math.min(5, d))];
  };

  /**
   * Camera move over a stage of [data-depth] layers: pan (x, y in px) and push (scale) are
   * applied per layer in proportion to depth, giving parallax. Consecutive calls chain from the
   * previous camera state.
   */
  SP.camera = function (tl, stage, at, options) {
    var o = options || {};
    var st = first(stage);
    var prev = st.__studioCam || { x: 0, y: 0, scale: 1, rotation: 0 };
    var next = {
      x: o.x === undefined ? prev.x : o.x,
      y: o.y === undefined ? prev.y : o.y,
      scale: o.scale === undefined ? prev.scale : o.scale,
      rotation: o.rotation === undefined ? prev.rotation : o.rotation
    };
    var firstMove = !st.__studioCam;
    var dur = o.duration || 2;
    Studio.all('[data-depth]', st).forEach(function (layer) {
      var k = SP.factor(layer);
      tl.fromTo(layer,
        { x: -prev.x * k, y: -prev.y * k, scale: 1 + (prev.scale - 1) * k, rotation: prev.rotation * k },
        { x: -next.x * k, y: -next.y * k, scale: 1 + (next.scale - 1) * k, rotation: next.rotation * k, duration: dur, ease: o.ease || 'power2.inOut', immediateRender: firstMove },
        at);
    });
    st.__studioCam = next;
    return at + dur;
  };

  /** Gentle seeded float for ambient life between `from` and `to` (finite repeats, seek-safe, starts at rest). */
  SP.float = function (tl, targets, from, to, options) {
    var o = options || {};
    Studio.all(targets).forEach(function (el, i) {
      var r = Studio.rng((o.seed || 3) + i * 101);
      var period = (o.period || 3) * (0.8 + r() * 0.4);
      var amp = Studio.u(o.amplitude || 0.8) * (0.6 + r() * 0.4);
      var reps = Math.max(1, Math.floor((to - from) / (period / 2)));
      tl.fromTo(el, { y: 0 }, { y: -amp, duration: period / 2, ease: 'sine.inOut', repeat: reps - 1, yoyo: true, immediateRender: false }, from);
    });
    return to;
  };

  /** Pieces fly in from seeded scattered offsets and settle (object assembly). Entrance. */
  SP.assemble = function (tl, parts, at, options) {
    var o = options || {};
    var els = Studio.all(parts);
    var r = Studio.rng(o.seed || 21);
    var spread = Studio.u(o.spread || 30);
    var offs = els.map(function () {
      return { x: (r() * 2 - 1) * spread, y: (r() * 2 - 1) * spread, rot: (r() * 2 - 1) * (o.rotate === undefined ? 40 : o.rotate) };
    });
    var dur = o.duration || 0.9;
    var stagger = o.stagger === undefined ? 0.06 : o.stagger;
    tl.fromTo(els,
      { x: function (i) { return offs[i].x; }, y: function (i) { return offs[i].y; }, rotation: function (i) { return offs[i].rot; }, scale: 0.6, autoAlpha: 0 },
      { x: 0, y: 0, rotation: 0, scale: 1, autoAlpha: 1, duration: dur, ease: o.ease || 'back.out(1.4)', stagger: stagger },
      at);
    return at + dur + stagger * Math.max(0, els.length - 1);
  };

  /** Reverse of assemble (exit). */
  SP.disassemble = function (tl, parts, at, options) {
    var o = options || {};
    var els = Studio.all(parts);
    var r = Studio.rng((o.seed || 21) + 7);
    var spread = Studio.u(o.spread || 30);
    var dur = o.duration || 0.6;
    var stagger = o.stagger === undefined ? 0.04 : o.stagger;
    tl.fromTo(els,
      { x: 0, y: 0, rotation: 0, autoAlpha: 1 },
      {
        x: function () { return (r() * 2 - 1) * spread; },
        y: function () { return (r() * 2 - 1) * spread; },
        rotation: function () { return (r() * 2 - 1) * 40; },
        autoAlpha: 0, duration: dur, ease: o.ease || 'power2.in', stagger: stagger, immediateRender: false
      },
      at);
    return at + dur + stagger * Math.max(0, els.length - 1);
  };

  /** Paper-like pop entrance: slight overshoot and a settling tilt. */
  SP.pop = function (tl, targets, at, options) {
    var o = options || {};
    var els = Studio.all(targets);
    var r = Studio.rng(o.seed || 13);
    var tilt = els.map(function () { return (r() * 2 - 1) * (o.tilt === undefined ? 6 : o.tilt); });
    var dur = o.duration || 0.6;
    var stagger = o.stagger === undefined ? 0.08 : o.stagger;
    tl.fromTo(els,
      { scale: o.fromScale || 0.4, rotation: function (i) { return tilt[i] * 2; }, autoAlpha: 0 },
      { scale: 1, rotation: function (i) { return tilt[i] * 0.25; }, autoAlpha: 1, duration: dur, ease: 'back.out(' + (o.overshoot || 1.8) + ')', stagger: stagger },
      at);
    return at + dur + stagger * Math.max(0, els.length - 1);
  };

  // ------------------------------------------------------------------ rhythm
  /** Beat times for a steady tempo: grid(bpm, {offset, count, subdivision}). */
  RH.grid = function (bpm, options) {
    var o = options || {};
    var beat = 60 / bpm / (o.subdivision || 1);
    var out = [];
    for (var i = 0; i < (o.count || 16); i++) out.push(Math.round(((o.offset || 0) + i * beat) * 1000) / 1000);
    return out;
  };

  /** First beat at or after t (or t itself when no beat follows). */
  RH.snap = function (t, beats) {
    for (var i = 0; i < beats.length; i++) if (beats[i] >= t - 1e-6) return beats[i];
    return t;
  };

  /** Short scale pulse on each beat (emphasis; does not render early). */
  RH.pulse = function (tl, targets, beats, options) {
    var o = options || {};
    beats.forEach(function (b) {
      tl.fromTo(targets, { scale: o.scale || 1.06 }, { scale: 1, duration: o.duration || 0.2, ease: o.ease || 'power2.out', immediateRender: false }, b);
    });
    return beats.length ? beats[beats.length - 1] + (o.duration || 0.2) : 0;
  };

  // ------------------------------------------------------------------ texture
  /** Inject shared SVG filters once: #st-deckle (torn paper edge) and #st-rough (cut edge). */
  TX.defs = function () {
    var existing = document.getElementById('st-texture-defs');
    if (existing) return existing;
    var svg = Studio.svg('svg', { id: 'st-texture-defs', width: 0, height: 0, 'aria-hidden': 'true', style: 'position:absolute;width:0;height:0' });
    var defs = Studio.svg('defs', null, svg);
    var deckle = Studio.svg('filter', { id: 'st-deckle', x: '-5%', y: '-5%', width: '110%', height: '110%' }, defs);
    Studio.svg('feTurbulence', { type: 'fractalNoise', baseFrequency: '0.045', numOctaves: '3', seed: '4', result: 'n' }, deckle);
    Studio.svg('feDisplacementMap', { 'in': 'SourceGraphic', in2: 'n', scale: '7', xChannelSelector: 'R', yChannelSelector: 'G' }, deckle);
    var rough = Studio.svg('filter', { id: 'st-rough', x: '-3%', y: '-3%', width: '106%', height: '106%' }, defs);
    Studio.svg('feTurbulence', { type: 'turbulence', baseFrequency: '0.02', numOctaves: '2', seed: '9', result: 'n' }, rough);
    Studio.svg('feDisplacementMap', { 'in': 'SourceGraphic', in2: 'n', scale: '3', xChannelSelector: 'R', yChannelSelector: 'G' }, rough);
    document.body.insertBefore(svg, document.body.firstChild);
    return svg;
  };

  /**
   * Film/paper grain overlay: `layers` static noise tiles with different seeds. With
   * options.boil = {from, to, fps} the visible tile steps at a fixed rate (hand-made "boil"),
   * which stays deterministic because each step is an explicit tween.
   */
  TX.grain = function (tl, options) {
    var o = options || {};
    var f = Studio.format;
    var count = o.boil ? (o.layers || 3) : 1;
    var holder = Studio.el('div', 'st-grain', null, overlayLayer());
    holder.style.opacity = String(o.opacity === undefined ? 0.07 : o.opacity);
    var tiles = [];
    for (var i = 0; i < count; i++) {
      var svg = Studio.svg('svg', { width: f.width, height: f.height, 'class': 'st-grain-tile', 'aria-hidden': 'true' }, holder);
      var filt = Studio.svg('filter', { id: 'st-grain-' + i }, svg);
      Studio.svg('feTurbulence', { type: 'fractalNoise', baseFrequency: String(o.frequency || 0.9), numOctaves: '2', seed: String((o.seed || 1) + i * 17), stitchTiles: 'stitch' }, filt);
      Studio.svg('feColorMatrix', { type: 'saturate', values: '0' }, filt);
      Studio.svg('rect', { width: '100%', height: '100%', filter: 'url(#st-grain-' + i + ')' }, svg);
      if (i > 0) svg.style.visibility = 'hidden';
      tiles.push(svg);
    }
    if (o.boil && tl) {
      var step = 1 / (o.boil.fps || 8);
      var n = Math.floor((o.boil.to - o.boil.from) / step);
      for (var k = 1; k <= n; k++) {
        var t = o.boil.from + k * step;
        var cur = tiles[k % count], prev = tiles[(k - 1) % count];
        tl.fromTo(prev, { visibility: 'visible' }, { visibility: 'hidden', duration: 0.001, immediateRender: false }, t);
        tl.fromTo(cur, { visibility: 'hidden' }, { visibility: 'visible', duration: 0.001, immediateRender: false }, t);
      }
    }
    return holder;
  };
})(typeof window !== 'undefined' ? window : this);
