/*
 * Motion Lab studio runtime - explanation devices (src/studio/studio-explain.js)
 * Eleven devices measured in the reference corpus (catalogue/data/references/, docs/reference-playbook.md), chosen
 * by the narrator's job in docs/explanation-devices.md and specs/explanation-devices.json. Added 2026-11-28:
 *
 *   Studio.comp.equation(parent, {terms})          lay the whole equation out, reveal terms, ring the last  (equation-term-build)
 *   Studio.comp.slider(parent, {min, max, ...})     a dragged handle drives an input and an output readout   (slider-driven-counter)
 *   Studio.comp.tracePair(parent, {period, ...})    a point on a circle traces its height onto a graph       (linked-trace-projection)
 *   Studio.comp.simulation(parent, {events, ...})   gauge, event log, step chart and regime caption, one clock (live-simulation-trace)
 *   Studio.comp.barRace(parent, {names, frames})    bars re-rank over time with a large date label           (bar-chart-race)
 *   Studio.comp.progression(parent, {items, steps}) one stage, focus moves item to item, caption and tracker  (single-stage-progression)
 *   Studio.space.tour(tl, canvas, stops, opts)      camera frames panels on a large canvas, drifts, pulls back (canvas-camera-tour)
 *   Studio.fx.dip(tl, out, in, at, opts)            content leaves, the empty stage breathes, the next title  (empty-stage-dip)
 *   Studio.comp.copySlot(parent, versions)          copy swaps inside the narration pause before its phrase  (pause-locked-copy-swap)
 *   Studio.comp.ui.{input, button, toggle, cursor, notify}   generic UI demo widgets                          (ui-demo-micro-interactions)
 *   Studio.comp.headline(parent, data, {preset})    'pair': two-tone headline; 'build': centred word build   (two-tone-headline-pair, centred-word-build)
 *
 * Seek safety: each device keeps its state in one number (a proxy property whose setter redraws the device as a
 * pure function of that number) and tweens only that number, so any frame renders the same whichever way the
 * timeline reached it. State-changing methods must be called in time order: each tween starts where the
 * previous call left the number. Builders follow the compositions contract (create DOM in `parent`, return
 * handles plus methods that add tweens and return their end time). Sizes come from --u; colours from the style
 * tokens. Requires studio-core.js, studio-draw.js, studio-type.js, studio-motion.js and studio-compositions.js;
 * load it after studio-compositions.js (and after studio-film.js when a film uses both).
 */
(function (global) {
  'use strict';

  var Studio = global.Studio;
  if (!Studio || !Studio.comp || !Studio.space || !Studio.fx || !Studio.draw) throw new Error('studio-explain.js requires the other studio runtime files (load it after studio-compositions.js)');
  var C = Studio.comp, SP = Studio.space, FX = Studio.fx, D = Studio.draw;
  var SWITCH = 0.001;

  // ------------------------------------------------------------------ shared helpers
  var CSS = [
    '.st-eq{position:relative;display:inline-flex;align-items:baseline;gap:calc(var(--u)*0.6);white-space:nowrap;font-family:var(--font-display);font-weight:var(--fw-display,700);font-size:calc(var(--u)*7);color:var(--c-ink);}',
    '.st-eq-term{display:inline-block;position:relative;}',
    '.st-eq-ring{position:absolute;left:0;top:0;overflow:visible;pointer-events:none;}',
    '.st-slider{position:relative;display:flex;flex-direction:column;gap:calc(var(--u)*2.2);font-family:var(--font-text);color:var(--c-ink);}',
    '.st-slider-read{display:flex;justify-content:space-between;align-items:flex-end;gap:calc(var(--u)*3);}',
    '.st-slider-label{font-size:calc(var(--u)*2.6);color:var(--c-ink-2);letter-spacing:var(--track-kicker,0.08em);text-transform:uppercase;}',
    '.st-slider-in{font-family:var(--font-mono);font-size:calc(var(--u)*4);font-weight:700;}',
    '.st-slider-out{font-family:var(--font-display);font-size:calc(var(--u)*8);font-weight:var(--fw-display,800);color:var(--c-accent);line-height:1;}',
    '.st-slider-track{position:relative;height:calc(var(--u)*1.2);border-radius:999px;background:var(--c-rule);}',
    '.st-slider-fill{position:absolute;left:0;top:0;bottom:0;width:100%;border-radius:999px;background:var(--c-accent);transform-origin:0 50%;}',
    '.st-slider-handle{position:absolute;left:0;top:50%;width:calc(var(--u)*4);height:calc(var(--u)*4);margin:calc(var(--u)*-2) 0 0 calc(var(--u)*-2);border-radius:50%;background:var(--c-paper);border:calc(var(--u)*0.5) solid var(--c-accent);box-shadow:0 calc(var(--u)*0.4) calc(var(--u)*1.2) rgba(0,0,0,0.18);}',
    '.st-slider-caveat{align-self:flex-end;padding:calc(var(--u)*0.8) calc(var(--u)*1.6);border:calc(var(--u)*0.3) solid var(--c-accent-2);color:var(--c-accent-2);font-weight:700;font-size:calc(var(--u)*2.8);border-radius:calc(var(--u)*0.8);background:var(--c-paper);}',
    '.st-trace,.st-sim-chart{display:block;overflow:visible;}',
    '.st-sim{position:relative;display:grid;grid-template-columns:auto 1fr;grid-template-rows:auto minmax(0,1fr) auto;gap:calc(var(--u)*2.4) calc(var(--u)*5);font-family:var(--font-text);color:var(--c-ink);width:100%;height:100%;}',
    '.st-sim-gauge{display:flex;flex-direction:column;align-items:center;gap:calc(var(--u)*1);}',
    '.st-sim-count{font-family:var(--font-display);font-weight:800;font-size:calc(var(--u)*9);line-height:1;}',
    '.st-sim-stack{display:flex;flex-direction:column-reverse;gap:calc(var(--u)*0.4);}',
    '.st-sim-cell{width:calc(var(--u)*7);height:calc(var(--u)*1.4);border-radius:calc(var(--u)*0.3);background:var(--c-rule);}',
    '.st-sim-log{font-family:var(--font-mono);font-size:calc(var(--u)*2.6);display:flex;flex-direction:column;gap:calc(var(--u)*0.5);align-self:start;}',
    '.st-sim-row{display:grid;grid-template-columns:7ch 5ch 13ch 3ch;gap:calc(var(--u)*1.6);white-space:nowrap;height:1.3em;line-height:1.3em;}',
    '.st-sim-chartbox{grid-column:1 / span 2;min-height:calc(var(--u)*10);position:relative;}',
    '.st-sim-chart{position:absolute;left:0;top:0;}',
    '.st-sim-dot{display:inline-block;width:0.6em;height:0.6em;border-radius:50%;margin-right:0.45em;vertical-align:0.05em;}',
    '.st-sim-caption,.st-prog-caption{grid-column:1 / span 2;position:relative;font-size:calc(var(--u)*3.6);font-weight:600;min-height:1.3em;}',
    '.st-sim-caption span,.st-prog-caption span{position:absolute;left:0;top:0;white-space:nowrap;}',
    '.st-race{position:relative;width:100%;height:100%;font-family:var(--font-text);color:var(--c-ink);}',
    '.st-race-row{position:absolute;left:0;top:0;width:100%;display:flex;align-items:center;gap:calc(var(--u)*1.2);}',
    '.st-race-name{width:22%;text-align:right;font-weight:600;font-size:calc(var(--u)*2.8);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}',
    '.st-race-bar{height:70%;border-radius:calc(var(--u)*0.4);transform-origin:0 50%;}',
    '.st-race-val{font-family:var(--font-mono);font-size:calc(var(--u)*2.6);white-space:nowrap;}',
    '.st-race-date{position:absolute;right:0;bottom:0;font-family:var(--font-display);font-weight:800;font-size:calc(var(--u)*12);color:var(--c-ink);opacity:0.14;line-height:1;}',
    '.st-prog-ui{position:relative;display:flex;flex-direction:column;align-items:center;gap:calc(var(--u)*1.4);font-family:var(--font-text);color:var(--c-ink);}',
    '.st-prog-caption{width:100%;text-align:center;}',
    '.st-prog-caption span{left:50%;transform:translateX(-50%);}',
    '.st-prog-dots{display:flex;gap:calc(var(--u)*1);}',
    '.st-prog-dot{width:calc(var(--u)*1.6);height:calc(var(--u)*1.6);border-radius:50%;background:var(--c-rule);}',
    '.st-copyslot{display:grid;font-family:var(--font-text);color:var(--c-ink);}',
    '.st-copyslot>span{grid-area:1 / 1;}',
    '.st-ui-input{display:flex;align-items:center;min-width:calc(var(--u)*30);height:calc(var(--u)*6);padding:0 calc(var(--u)*1.8);border:calc(var(--u)*0.25) solid var(--c-rule);border-radius:calc(var(--u)*1);background:var(--c-paper);font-family:var(--font-text);font-size:calc(var(--u)*2.6);color:var(--c-ink);position:relative;white-space:pre;}',
    '.st-ui-ph{color:var(--c-ink-2);opacity:0.6;position:absolute;left:calc(var(--u)*1.8);}',
    '.st-ui-caret{display:inline-block;width:calc(var(--u)*0.25);height:1.1em;background:var(--c-accent);margin-left:1px;}',
    '.st-ui-button{display:inline-flex;align-items:center;justify-content:center;height:calc(var(--u)*6);padding:0 calc(var(--u)*3);border-radius:calc(var(--u)*1);background:var(--c-accent);color:var(--c-paper);font-family:var(--font-text);font-weight:700;font-size:calc(var(--u)*2.8);}',
    '.st-ui-toggle{position:relative;width:calc(var(--u)*8);height:calc(var(--u)*4.4);border-radius:999px;background:var(--c-rule);}',
    '.st-ui-knob{position:absolute;left:calc(var(--u)*0.4);top:calc(var(--u)*0.4);width:calc(var(--u)*3.6);height:calc(var(--u)*3.6);border-radius:50%;background:var(--c-paper);box-shadow:0 calc(var(--u)*0.2) calc(var(--u)*0.6) rgba(0,0,0,0.2);}',
    '.st-ui-cursor{position:absolute;left:0;top:0;width:calc(var(--u)*3.2);height:calc(var(--u)*3.2);pointer-events:none;z-index:50;}',
    '.st-ui-ripple{position:absolute;left:calc(var(--u)*-2);top:calc(var(--u)*-2);width:calc(var(--u)*4);height:calc(var(--u)*4);border-radius:50%;border:calc(var(--u)*0.3) solid var(--c-accent);}',
    '.st-ui-notify{display:flex;flex-direction:column;gap:calc(var(--u)*0.5);min-width:calc(var(--u)*30);padding:calc(var(--u)*1.6) calc(var(--u)*2);border-radius:calc(var(--u)*1.4);background:var(--c-paper);border:1px solid var(--c-rule);box-shadow:0 calc(var(--u)*0.8) calc(var(--u)*2.4) rgba(0,0,0,0.14);font-family:var(--font-text);color:var(--c-ink);}',
    '.st-ui-notify b{font-size:calc(var(--u)*3);}',
    '.st-ui-notify span{font-size:calc(var(--u)*2.6);color:var(--c-ink-2);}',
    '.st-hl{font-family:var(--font-display);font-weight:var(--fw-display,800);font-size:calc(var(--u)*6.4);line-height:1.08;letter-spacing:var(--track-display,-0.01em);color:var(--c-ink);}',
    '.st-hl-line{display:block;white-space:nowrap;}',
    '.st-hl-word{display:inline-block;}',
    '.st-hl-build{position:relative;width:100%;}',
    '.st-hl-build .st-hl-line{display:inline-block;}'
  ].join('\n');
  function injectCss() {
    if (document.getElementById('st-explain-css')) return;
    var s = document.createElement('style');
    s.id = 'st-explain-css';
    s.textContent = CSS;
    (document.head || document.documentElement).insertBefore(s, (document.head || document.documentElement).firstChild);
  }
  injectCss();

  function resolve(p) { return typeof p === 'string' ? document.querySelector(p) : p; }
  function withClass(base, o) { return base + (o && o.className ? ' ' + o.className : ''); }
  function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }
  function lerp(a, b, f) { return a + (b - a) * f; }
  function inOut(f) { return f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2; }
  function tok(name, fallback) { return Studio.token(name, fallback); }
  function warn(list, msg) { list.push(msg); if (global.console) global.console.warn('[studio] ' + msg); }

  /** Number formatter: {prefix, suffix, decimals, commas (true)}. */
  function formatter(f) {
    var o = f || {};
    return function (v) {
      var n = Number(v);
      if (isNaN(n)) n = 0;
      var s = n.toFixed(o.decimals || 0);
      if (o.commas !== false) {
        var p = s.split('.');
        p[0] = p[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        s = p.join('.');
      }
      return (o.prefix || '') + s + (o.suffix || '');
    };
  }

  /**
   * The seek-safe state holder every device uses: a proxy whose `v` setter calls render(v). go() chains a tween
   * from the value the previous go() left (immediateRender:false), so call it in time order.
   */
  function driver(v0, render) {
    var obj = {}, cur = v0;
    Object.defineProperty(obj, 'v', {
      get: function () { return cur; },
      set: function (x) { cur = x; render(x); },
      enumerable: true, configurable: true
    });
    obj.last = v0;
    obj.go = function (tl, to, at, dur, ease) {
      var d = Math.max(dur || 0, SWITCH);
      tl.fromTo(obj, { v: obj.last }, { v: to, duration: d, ease: ease || 'none', immediateRender: false }, at);
      obj.last = to;
      return at + d;
    };
    obj.v = v0;
    return obj;
  }

  /** Entrance of a whole device box: fade and a small rise. */
  function enterBox(tl, el, at, o) {
    var dur = (o && o.duration) || 0.5;
    tl.fromTo(el, { autoAlpha: 0, y: Studio.u(1.5) }, { autoAlpha: 1, y: 0, duration: dur, ease: 'power3.out', immediateRender: true }, at);
    return at + dur;
  }
  function exitBox(tl, el, at, o) {
    var dur = (o && o.duration) || 0.35;
    tl.fromTo(el, { autoAlpha: 1 }, { autoAlpha: 0, duration: dur, ease: 'power2.in', immediateRender: false }, at);
    return at + dur;
  }

  // ------------------------------------------------------------------ 1. equation term build
  /**
   * Equation laid out whole (so nothing reflows), terms revealed one by one, the final term ringed.
   * data.terms: list of strings or {text, tone ('accent'|'accent-2'|'muted'), className}. options: {rise (u, 0.8),
   * ringColor}. Returns {el, terms, show(tl, at), reveal(tl, i|[i], at, {duration 0.25}),
   * build(tl, times[]|{at, gap 0.6}), ring(tl, i, at, {duration 0.4, color}), exit(tl, at)}.
   * Reveal each term when the figure shows that part; terms that arrive before the figure read as a caption.
   */
  C.equation = function (parent, data, options) {
    var o = options || {};
    var el = Studio.el('div', withClass('st-eq', o), null, resolve(parent));
    var terms = (data.terms || []).map(function (t) {
      var d = typeof t === 'string' ? { text: t } : t;
      var s = Studio.el('span', 'st-eq-term' + (d.className ? ' ' + d.className : ''), d.text, el);
      if (d.tone === 'accent') s.style.color = 'var(--c-accent)';
      else if (d.tone === 'accent-2') s.style.color = 'var(--c-accent-2)';
      else if (d.tone === 'muted') s.style.color = 'var(--c-ink-2)';
      return s;
    });
    el.setAttribute('aria-label', terms.map(function (s) { return s.textContent; }).join(' '));
    var svg = Studio.svg('svg', { 'class': 'st-eq-ring', 'aria-hidden': 'true' }, el);
    var rise = Studio.u(o.rise === undefined ? 0.8 : o.rise);
    global.gsap.set(terms, { autoAlpha: 0 });
    var api = { el: el, terms: terms, rings: [] };
    api.show = function (tl, at) { return Studio.show(tl, el, at); };
    api.reveal = function (tl, i, at, opts) {
      var dur = (opts && opts.duration) || 0.25;
      var els = [].concat(i).map(function (k) { return terms[k]; });
      tl.fromTo(els, { autoAlpha: 0, y: rise }, { autoAlpha: 1, y: 0, duration: dur, ease: 'power2.out', immediateRender: true }, at);
      return at + dur;
    };
    api.build = function (tl, times) {
      var list = Array.isArray(times) ? times : terms.map(function (_, k) { return times.at + k * (times.gap === undefined ? 0.6 : times.gap); });
      var end = 0;
      list.forEach(function (t, k) { if (k < terms.length) end = api.reveal(tl, k, t); });
      return end;
    };
    api.ring = function (tl, i, at, opts) {
      var p = opts || {};
      var t = terms[i === undefined ? terms.length - 1 : i];
      var w = el.offsetWidth, h = el.offsetHeight;
      svg.setAttribute('width', w); svg.setAttribute('height', h);
      svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
      var cx = t.offsetLeft + t.offsetWidth / 2, cy = t.offsetTop + t.offsetHeight / 2;
      var path = Studio.svg('path', {
        d: D.loop(Studio.hash('eq' + i + t.textContent), cx, cy, t.offsetWidth / 2 + Studio.u(1.6), t.offsetHeight / 2 + Studio.u(0.8)),
        fill: 'none', stroke: p.color || o.ringColor || tok('--c-accent', '#d9483b'),
        'stroke-width': Studio.u(0.5), 'stroke-linecap': 'round'
      }, svg);
      api.rings.push(path);
      return D.stroke(tl, path, at, { duration: p.duration || 0.4, ease: 'power2.inOut' });
    };
    api.exit = function (tl, at) { return exitBox(tl, el, at); };
    return api;
  };

  // ------------------------------------------------------------------ 2. slider-driven counter
  /**
   * A handle dragged along a track drives an input readout and an output readout (output = data.map(v), or
   * v * data.scale). data: {min, max, value, step (1), input: {label, prefix, suffix, decimals}, output: {label,
   * prefix, suffix, decimals}, caveat}. Returns {el, enter(tl, at), drag(tl, at, {to, duration 1.7, settle 2,
   * ease}), caveat(tl, at), exit(tl, at)}. drag ends with `settle` small steps on the output, so the final number
   * lands rather than snaps; hold the end value at least 1 s so it can be read.
   */
  C.slider = function (parent, data, options) {
    var o = options || {};
    var d = data || {};
    var min = d.min === undefined ? 0 : d.min, max = d.max === undefined ? 100 : d.max;
    var step = d.step || 1;
    var map = d.map || function (v) { return v * (d.scale === undefined ? 1 : d.scale); };
    var fin = formatter(d.input), fout = formatter(d.output);
    var el = Studio.el('div', withClass('st-slider', o), null, resolve(parent));
    var read = Studio.el('div', 'st-slider-read', null, el);
    var inBox = Studio.el('div', null, null, read);
    Studio.el('div', 'st-slider-label', (d.input && d.input.label) || '', inBox);
    var inVal = Studio.el('div', 'st-slider-in', '', inBox);
    var outBox = Studio.el('div', null, null, read);
    outBox.style.textAlign = 'right';
    Studio.el('div', 'st-slider-label', (d.output && d.output.label) || '', outBox);
    var outVal = Studio.el('div', 'st-slider-out', '', outBox);
    var track = Studio.el('div', 'st-slider-track', null, el);
    var fill = Studio.el('div', 'st-slider-fill', null, track);
    var handle = Studio.el('div', 'st-slider-handle', null, track);
    var cav = d.caveat ? Studio.el('div', 'st-slider-caveat', d.caveat, el) : null;
    if (cav) global.gsap.set(cav, { autoAlpha: 0 });
    var trackW = track.offsetWidth;
    // During the settle steps the output shows settleValues[k - 1] instead of its mapped value; k = 0 releases it.
    var settleValues = [], settleK = 0, cur = d.value === undefined ? min : d.value;
    function renderOut() {
      outVal.textContent = settleK >= 1 && settleValues.length ? fout(settleValues[Math.min(settleValues.length, Math.round(settleK)) - 1]) : fout(map(Math.round(cur / step) * step));
    }
    var state = driver(cur, function (v) {
      cur = v;
      var pos = clamp((v - min) / (max - min || 1), 0, 1);
      fill.style.transform = 'scaleX(' + pos.toFixed(5) + ')';
      handle.style.transform = 'translateX(' + (pos * trackW).toFixed(2) + 'px)';
      inVal.textContent = fin(Math.round(v / step) * step);
      renderOut();
    });
    var settle = driver(0, function (k) { settleK = k; renderOut(); });
    var api = { el: el, handle: handle, input: inVal, output: outVal, caveatEl: cav };
    api.enter = function (tl, at) { return enterBox(tl, el, at); };
    api.drag = function (tl, at, opts) {
      var p = opts || {};
      var to = p.to === undefined ? max : p.to;
      var dur = p.duration || 1.7;
      var n = p.settle === undefined ? 2 : p.settle;
      var up = to >= state.last;
      if (settle.last !== 0) settle.go(tl, 0, at, SWITCH);
      var end = state.go(tl, to, at, dur, p.ease || 'power2.inOut');
      if (n > 0) {
        // the output reads a little short, then steps onto the real value (measured: $4,997 -> $4,999 -> $5,000);
        // the first step lands 0.1 s before the handle stops, while the eased output is still further away
        var target = map(Math.round(to / step) * step);
        var unit = Math.pow(10, -((d.output && d.output.decimals) || 0));
        var first = settleValues.length + 1;
        for (var k = n; k >= 0; k--) settleValues.push(target - (up ? 1 : -1) * unit * (k === n ? 3 : k));
        settle.go(tl, first, end - 0.1, SWITCH);
        for (var j = 1; j <= n; j++) settle.go(tl, first + j, end + 0.12 * j - 0.02, SWITCH);
        end = end + 0.12 * n;
      }
      tl.fromTo(outVal, { scale: 1 }, { scale: 1.06, duration: 0.09, ease: 'power1.out', immediateRender: false }, end);
      tl.fromTo(outVal, { scale: 1.06 }, { scale: 1, duration: 0.2, ease: 'back.out(3)', immediateRender: false }, end + 0.09);
      return end + 0.29;
    };
    api.caveat = function (tl, at) {
      if (!cav) return at;
      return FX.stamp(tl, cav, at, { fromScale: 1.5, rotate: -3, duration: 0.18 });
    };
    api.exit = function (tl, at) { return exitBox(tl, el, at); };
    return api;
  };

  // ------------------------------------------------------------------ 3. linked trace projection
  /**
   * A point turns round a circle while a guide line carries its height across to a graph that draws itself:
   * both are computed from one angle, so they can never drift apart. data: {cycles (1.5, how much graph fits),
   * period (2 s per turn), label}. options: {width, height (px; default the parent's box)}.
   * Returns {el, enter(tl, at), run(tl, at, {cycles, period}), exit(tl, at)}.
   */
  C.tracePair = function (parent, data, options) {
    var o = options || {};
    var d = data || {};
    var host = resolve(parent);
    var W = o.width || host.offsetWidth || Studio.u(120), H = o.height || host.offsetHeight || Studio.u(50);
    var cycles = d.cycles || 1.5, period = d.period || 2;
    var R = Math.min(H * 0.38, W * 0.16);
    var cx = R + Studio.u(2), cy = H / 2;
    var x0 = cx + R + Studio.u(6), x1 = W - Studio.u(2);
    var cycleW = (x1 - x0) / cycles;
    var ink = tok('--c-ink', '#1e293b'), rule = tok('--c-rule', '#cbd5e1'), acc = tok('--c-accent', '#d9483b'), acc2 = tok('--c-accent-2', '#1d4ed8');
    var sw = Studio.u(0.35);
    var svg = Studio.svg('svg', { 'class': withClass('st-trace', o), width: W, height: H, viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': d.label || 'A point on a circle traces a sine wave' }, host);
    var clipId = 'st-trace-clip-' + Studio.hash(String(W) + H + cycles + (d.label || '')) + '-' + (C.tracePair.count = (C.tracePair.count || 0) + 1);
    var defs = Studio.svg('defs', null, svg);
    var cp = Studio.svg('clipPath', { id: clipId }, defs);
    var clipRect = Studio.svg('rect', { x: x0 - sw, y: 0, width: 0, height: H }, cp);
    Studio.svg('line', { x1: x0, y1: cy, x2: x1, y2: cy, stroke: rule, 'stroke-width': sw }, svg);
    Studio.svg('line', { x1: x0, y1: cy - R - Studio.u(1), x2: x0, y2: cy + R + Studio.u(1), stroke: rule, 'stroke-width': sw }, svg);
    var circle = Studio.svg('circle', { cx: cx, cy: cy, r: R, fill: 'none', stroke: ink, 'stroke-width': sw }, svg);
    var pts = [], N = Math.max(60, Math.round(cycles * 120));
    for (var i = 0; i <= N; i++) {
      var th = (i / N) * cycles * Math.PI * 2;
      pts.push((i ? 'L' : 'M') + (x0 + th / (Math.PI * 2) * cycleW).toFixed(2) + ' ' + (cy - R * Math.sin(th)).toFixed(2));
    }
    Studio.svg('path', { d: pts.join(' '), fill: 'none', stroke: acc, 'stroke-width': Studio.u(0.55), 'stroke-linecap': 'round', 'clip-path': 'url(#' + clipId + ')' }, svg);
    var arc = Studio.svg('path', { fill: 'none', stroke: acc2, 'stroke-width': sw }, svg);
    var radius = Studio.svg('line', { x1: cx, y1: cy, stroke: ink, 'stroke-width': sw }, svg);
    var guide = Studio.svg('line', { stroke: acc2, 'stroke-width': sw, 'stroke-dasharray': Studio.u(0.8) + ' ' + Studio.u(0.6) }, svg);
    var dot = Studio.svg('circle', { r: Studio.u(1), fill: acc2 }, svg);
    var gdot = Studio.svg('circle', { r: Studio.u(1), fill: acc }, svg);
    var maxTh = cycles * Math.PI * 2;
    var state = driver(0, function (th) {
      var t = clamp(th, 0, maxTh);
      var px = cx + R * Math.cos(t), py = cy - R * Math.sin(t);
      var gx = x0 + t / (Math.PI * 2) * cycleW;
      radius.setAttribute('x2', px.toFixed(2)); radius.setAttribute('y2', py.toFixed(2));
      dot.setAttribute('cx', px.toFixed(2)); dot.setAttribute('cy', py.toFixed(2));
      gdot.setAttribute('cx', gx.toFixed(2)); gdot.setAttribute('cy', py.toFixed(2));
      guide.setAttribute('x1', px.toFixed(2)); guide.setAttribute('y1', py.toFixed(2));
      guide.setAttribute('x2', gx.toFixed(2)); guide.setAttribute('y2', py.toFixed(2));
      clipRect.setAttribute('width', Math.max(0, gx - x0 + sw).toFixed(2));
      var a = t % (Math.PI * 2), ar = R * 0.28;
      if (a < 1e-4) { arc.setAttribute('d', ''); return; }
      var ex = cx + ar * Math.cos(a), ey = cy - ar * Math.sin(a);
      arc.setAttribute('d', 'M' + (cx + ar).toFixed(2) + ' ' + cy.toFixed(2) + ' A' + ar.toFixed(2) + ' ' + ar.toFixed(2) + ' 0 ' + (a > Math.PI ? 1 : 0) + ' 0 ' + ex.toFixed(2) + ' ' + ey.toFixed(2));
    });
    var api = { el: svg, circle: circle, state: state, geometry: { cx: cx, cy: cy, R: R, x0: x0, cycleW: cycleW } };
    api.enter = function (tl, at) { return enterBox(tl, svg, at); };
    api.run = function (tl, at, opts) {
      var p = opts || {};
      var cyc = p.cycles === undefined ? cycles : p.cycles;
      var to = Math.min(maxTh, state.last + cyc * Math.PI * 2);
      var turns = (to - state.last) / (Math.PI * 2);
      return state.go(tl, to, at, turns * (p.period || period), 'none');
    };
    api.exit = function (tl, at) { return exitBox(tl, svg, at); };
    return api;
  };

  // ------------------------------------------------------------------ 4. live simulation trace
  /**
   * Seeded event script: phases [{from, to, rate (events/s), kind ('take'|'refill'), jitter (0..0.45), label}]
   * -> [{t, kind, label}] sorted by time. Same seed, same events.
   */
  C.simulationScript = function (seed, phases) {
    var r = Studio.rng(seed);
    var out = [];
    (phases || []).forEach(function (ph) {
      var gap = 1 / (ph.rate || 1), j = ph.jitter === undefined ? 0.25 : ph.jitter;
      for (var t = ph.from; t < ph.to - 1e-9; t += gap) {
        out.push({ t: +(t + (r() - 0.5) * 2 * j * gap * 0.5).toFixed(3), kind: ph.kind || 'take', label: ph.label });
      }
    });
    return out.sort(function (a, b) { return a.t - b.t; });
  };

  /**
   * One clock drives every view: a gauge (count and cell stack), an event log, a step chart with event ticks and
   * a regime caption swapped in place. data: {capacity (10), start (capacity), events [{t, kind 'take'|'refill',
   * label}], regimes [{t, text}], logRows (6), duration (seconds of simulated time), labels {ok, rejected,
   * refill}}. A 'take' at 0 is rejected (red). Returns {el, states, enter(tl, at), run(tl, at, {duration}),
   * exit(tl, at)}. More than about 10 events a second become unreadable: slow the clock or aggregate.
   */
  C.simulation = function (parent, data, options) {
    var o = options || {};
    var d = data || {};
    var cap = d.capacity || 10;
    var start = d.start === undefined ? cap : d.start;
    var events = (d.events || []).slice().sort(function (a, b) { return a.t - b.t; });
    var regimes = (d.regimes || []).slice().sort(function (a, b) { return a.t - b.t; });
    var dur = d.duration || (events.length ? events[events.length - 1].t + 1 : 10);
    var labels = d.labels || {};
    var rowsN = d.logRows || 6;
    // precompute the state after each event, so every view reads the same list
    var states = [], v = start;
    events.forEach(function (e, i) {
      var ok = true;
      if (e.kind === 'refill') v = Math.min(cap, v + (e.amount || 1));
      else if (v > 0) v = v - (e.amount || 1);
      else ok = false;
      states.push({ i: i, t: e.t, kind: e.kind, ok: ok, value: v, label: e.label });
    });
    var neg = tok('--c-negative', '#d9483b'), pos = tok('--c-positive', '#059669'), acc = tok('--c-accent', '#d9483b');
    var ink = tok('--c-ink', '#1e293b'), rule = tok('--c-rule', '#cbd5e1');
    var el = Studio.el('div', withClass('st-sim', o), null, resolve(parent));
    var gauge = Studio.el('div', 'st-sim-gauge', null, el);
    var count = Studio.el('div', 'st-sim-count', String(start), gauge);
    var stack = Studio.el('div', 'st-sim-stack', null, gauge);
    var cells = [];
    for (var c = 0; c < cap; c++) cells.push(Studio.el('div', 'st-sim-cell', null, stack));
    var log = Studio.el('div', 'st-sim-log', null, el);
    var rows = [];
    for (var r = 0; r < rowsN; r++) {
      var row = Studio.el('div', 'st-sim-row', null, log);
      rows.push({ el: row, t: Studio.el('span', null, '', row), id: Studio.el('span', null, '', row), out: Studio.el('span', null, '', row), rem: Studio.el('span', null, '', row) });
      var last = rows[rows.length - 1];
      last.dot = Studio.el('i', 'st-sim-dot', null, last.out);
      last.word = Studio.el('span', null, '', last.out);
    }
    var chartBox = Studio.el('div', 'st-sim-chartbox', null, el);
    // the chart fills its grid row unless options.chartHeight (u) fixes it
    var cw = chartBox.offsetWidth || Studio.u(100), ch = o.chartHeight ? Studio.u(o.chartHeight) : Math.max(Studio.u(10), chartBox.offsetHeight - 4);
    // the chart stretches to its grid row whatever the row settles at; strokes keep their width (non-scaling-stroke)
    var svg = Studio.svg('svg', { 'class': 'st-sim-chart', width: '100%', height: '100%', viewBox: '0 0 ' + cw + ' ' + ch, preserveAspectRatio: 'none', 'aria-hidden': 'true' }, chartBox);
    var clipId = 'st-sim-clip-' + (C.simulation.count = (C.simulation.count || 0) + 1);
    var clipRect = Studio.svg('rect', { x: 0, y: -2, width: 0, height: ch + 4 }, Studio.svg('clipPath', { id: clipId }, Studio.svg('defs', null, svg)));
    Studio.svg('line', { x1: 0, y1: ch, x2: cw, y2: ch, stroke: rule, 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke' }, svg);
    var X = function (t) { return (t / dur) * cw; }, Y = function (val) { return ch - (val / cap) * (ch - 2); };
    var dPath = 'M0 ' + Y(start).toFixed(2), last = start;
    states.forEach(function (s) { dPath += ' L' + X(s.t).toFixed(2) + ' ' + Y(last).toFixed(2) + ' L' + X(s.t).toFixed(2) + ' ' + Y(s.value).toFixed(2); last = s.value; });
    dPath += ' L' + cw + ' ' + Y(last).toFixed(2);
    var g = Studio.svg('g', { 'clip-path': 'url(#' + clipId + ')' }, svg);
    Studio.svg('path', { d: dPath, fill: 'none', stroke: acc, 'stroke-width': Studio.u(0.4), 'stroke-linejoin': 'round', 'vector-effect': 'non-scaling-stroke' }, g);
    states.forEach(function (s) {
      Studio.svg('line', { x1: X(s.t), y1: ch, x2: X(s.t), y2: ch - Studio.u(1), stroke: s.ok ? ink : neg, 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke' }, g);
    });
    var capEl = Studio.el('div', 'st-sim-caption', null, el);
    var capSpans = regimes.map(function (rg) { var s = Studio.el('span', null, rg.text, capEl); s.style.opacity = '0'; return s; });
    var fmtT = function (t) { return t.toFixed(2) + 's'; };
    var state = driver(0, function (now) {
      var k = 0;
      while (k < states.length && states[k].t <= now + 1e-9) k++;
      var val = k ? states[k - 1].value : start;
      count.textContent = String(val);
      count.style.color = val === 0 ? neg : ink;
      for (var q = 0; q < cap; q++) cells[q].style.background = q < val ? acc : rule;
      for (var rr = 0; rr < rowsN; rr++) {
        var s = states[k - rowsN + rr];
        var row = rows[rr];
        if (!s) { row.t.textContent = ''; row.id.textContent = ''; row.word.textContent = ''; row.dot.style.visibility = 'hidden'; row.rem.textContent = ''; continue; }
        row.t.textContent = fmtT(s.t);
        row.id.textContent = '#' + (s.i + 1);
        // outcome text stays in ink (contrast); the colour rides on the marker dot
        row.word.textContent = s.kind === 'refill' ? (labels.refill || '+1 refill') : (s.ok ? (labels.ok || 'allowed') : (labels.rejected || 'rejected'));
        row.word.style.fontWeight = s.ok ? '400' : '700';
        row.dot.style.visibility = 'visible';
        row.dot.style.background = s.kind === 'refill' ? acc : (s.ok ? pos : neg);
        row.rem.textContent = String(s.value);
        row.el.style.opacity = rr === rowsN - 1 ? '1' : String(0.45 + 0.55 * rr / Math.max(1, rowsN - 1));
      }
      clipRect.setAttribute('width', X(clamp(now, 0, dur)).toFixed(2));
      var cur = -1;
      for (var m = 0; m < regimes.length; m++) if (regimes[m].t <= now + 1e-9) cur = m;
      for (var n = 0; n < capSpans.length; n++) {
        capSpans[n].style.opacity = n === cur ? String(clamp((now - regimes[n].t) / 0.15, 0, 1)) : '0';
      }
    });
    var api = { el: el, states: states, state: state };
    api.enter = function (tl, at) { return enterBox(tl, el, at); };
    api.run = function (tl, at, opts) {
      var p = opts || {};
      return state.go(tl, dur, at, p.duration || dur, 'none');
    };
    api.exit = function (tl, at) { return exitBox(tl, el, at); };
    return api;
  };

  // ------------------------------------------------------------------ 5. bar chart race
  /**
   * Bars re-rank over time. data: {names [..], frames [{label, values [..]}], colors [..], scale ('frame' |
   * 'global'), format {prefix, suffix, decimals}}. options: {rows (7)}. Values move linearly within a step, ranks
   * with power2.inOut. Returns {el, enter(tl, at), play(tl, at, {from, to, step 0.3}), exit(tl, at)}.
   * Keep steps slow enough to read a swap (0.25-0.4 s); label every bar.
   */
  C.barRace = function (parent, data, options) {
    var o = options || {};
    var d = data || {};
    var names = d.names || [], frames = d.frames || [];
    var rowsN = o.rows || 7;
    var fmt = formatter(d.format);
    var palette = d.colors || ['--c-accent', '--c-accent-2', '--c-accent-3', '--c-positive', '--c-info', '--c-highlight', '--c-ink-2'];
    var el = Studio.el('div', withClass('st-race', o), null, resolve(parent));
    var H = el.offsetHeight || Studio.u(50);
    var rowH = H * 0.86 / rowsN;
    var date = Studio.el('div', 'st-race-date', frames.length ? frames[0].label : '', el);
    var barMaxW = (el.offsetWidth || Studio.u(100)) * 0.62;
    var bars = names.map(function (nm, i) {
      var row = Studio.el('div', 'st-race-row', null, el);
      row.style.height = rowH + 'px';
      var name = Studio.el('div', 'st-race-name', nm, row);
      var bar = Studio.el('div', 'st-race-bar', null, row);
      bar.style.width = barMaxW + 'px';
      var c = palette[i % palette.length];
      bar.style.background = c.indexOf('--') === 0 ? tok(c, '#888') : c;
      var val = Studio.el('div', 'st-race-val', '', row);
      return { row: row, name: name, bar: bar, val: val };
    });
    function ranks(f) {
      var vals = frames[f].values;
      var order = vals.map(function (_, i) { return i; }).sort(function (a, b) { return vals[b] - vals[a] || a - b; });
      var rk = [];
      order.forEach(function (idx, r) { rk[idx] = r; });
      return rk;
    }
    var rankCache = frames.map(function (_, f) { return ranks(f); });
    var maxCache = frames.map(function (fr) { return Math.max.apply(null, fr.values.concat([1e-9])); });
    var globalMax = Math.max.apply(null, maxCache.concat([1e-9]));
    var state = driver(0, function (v) {
      var f0 = clamp(Math.floor(v), 0, frames.length - 1), f1 = Math.min(frames.length - 1, f0 + 1);
      var fr = clamp(v - f0, 0, 1), fe = inOut(fr);
      var mx = d.scale === 'global' ? globalMax : lerp(maxCache[f0], maxCache[f1], fr);
      date.textContent = frames[clamp(Math.round(v), 0, frames.length - 1)].label;
      bars.forEach(function (b, i) {
        var val = lerp(frames[f0].values[i], frames[f1].values[i], fr);
        var rank = lerp(rankCache[f0][i], rankCache[f1][i], fe);
        b.row.style.transform = 'translateY(' + (rank * rowH).toFixed(2) + 'px)';
        b.row.style.opacity = String(clamp(rowsN - rank, 0, 1));
        b.bar.style.transform = 'scaleX(' + clamp(val / mx, 0, 1).toFixed(4) + ')';
        b.val.textContent = fmt(val);
        b.val.style.transform = 'translateX(' + ((clamp(val / mx, 0, 1) - 1) * barMaxW).toFixed(2) + 'px)';
      });
    });
    var api = { el: el, bars: bars, date: date, state: state };
    api.enter = function (tl, at) { return enterBox(tl, el, at); };
    api.play = function (tl, at, opts) {
      var p = opts || {};
      var from = p.from === undefined ? Math.round(state.last) : p.from;
      var to = p.to === undefined ? frames.length - 1 : p.to;
      var stepDur = p.step || 0.3;
      var t = at;
      if (Math.abs(from - state.last) > 1e-6) t = state.go(tl, from, t, SWITCH);
      for (var f = from + 1; f <= to; f++) t = state.go(tl, f, t, stepDur, 'none');
      return t;
    };
    api.exit = function (tl, at) { return exitBox(tl, el, at); };
    return api;
  };

  // ------------------------------------------------------------------ 6. single-stage progression
  /**
   * One persistent stage; each step moves the focus to one or more items (the rest dim), swaps a caption in place
   * and advances a tracker. data: {items [selector|element] (your own laid-out elements), steps [{focus i|[i],
   * caption}]}. options: {dim (0.28), scale (1.05), tracker (true)}. The ui (caption and dots) is built in
   * `parent`. Returns {el, enter(tl, at), to(tl, step, at, {duration 0.45}), exit(tl, at)}.
   * One change per step; name it in the caption.
   */
  C.progression = function (parent, data, options) {
    var o = options || {};
    var d = data || {};
    var items = Studio.all(d.items || []);
    var steps = d.steps || [];
    var dim = o.dim === undefined ? 0.28 : o.dim, big = o.scale === undefined ? 1.05 : o.scale;
    var el = Studio.el('div', withClass('st-prog-ui', o), null, resolve(parent));
    var cap = Studio.el('div', 'st-prog-caption', null, el);
    var spans = steps.map(function (s) { var sp = Studio.el('span', null, s.caption || '', cap); sp.style.opacity = '0'; return sp; });
    var dots = [];
    if (o.tracker !== false) {
      var dw = Studio.el('div', 'st-prog-dots', null, el);
      steps.forEach(function () { dots.push(Studio.el('div', 'st-prog-dot', null, dw)); });
    }
    var acc = tok('--c-accent', '#d9483b'), rule = tok('--c-rule', '#cbd5e1');
    var focusSets = steps.map(function (s) { return [].concat(s.focus === undefined ? [] : s.focus); });
    function focusOf(k, i) { return focusSets[k] && focusSets[k].indexOf(i) >= 0 ? 1 : 0; }
    var state = driver(0, function (v) {
      var k0 = clamp(Math.floor(v), 0, Math.max(0, steps.length - 1)), k1 = Math.min(steps.length - 1, k0 + 1);
      var f = clamp(v - k0, 0, 1);
      items.forEach(function (it, i) {
        var a = lerp(focusOf(k0, i), focusOf(k1, i), f);
        it.style.opacity = String(lerp(dim, 1, a));
        it.style.transform = 'scale(' + lerp(1, big, a).toFixed(4) + ')';
      });
      spans.forEach(function (sp, i) {
        var op = i === k0 ? 1 - clamp(f * 2, 0, 1) : (i === k1 && k1 !== k0 ? clamp(f * 2 - 1, 0, 1) : 0);
        sp.style.opacity = String(op);
      });
      dots.forEach(function (dt, i) { dt.style.background = i <= Math.round(v) ? acc : rule; dt.style.transform = 'scale(' + (i === Math.round(v) ? 1.35 : 1) + ')'; });
    });
    var api = { el: el, items: items, state: state };
    api.enter = function (tl, at) { return enterBox(tl, el, at); };
    api.to = function (tl, step, at, opts) {
      return state.go(tl, step, at, (opts && opts.duration) || 0.45, 'none');
    };
    api.exit = function (tl, at) { return exitBox(tl, el, at); };
    return api;
  };

  // ------------------------------------------------------------------ 7. canvas camera tour
  /**
   * Camera tour over a canvas laid out larger than the frame (`canvas` is positioned at the frame's top left;
   * its children are the panels). stops: [{target, at, pad (0.12), maxScale (2.5)}]: at each stop the camera
   * frames the target in `move` s (power2.inOut), then drifts in by `drift` (1.025) until the next stop.
   * options: {move 0.8, drift 1.025, start ('overview'|'first'), pullBack (time: frame the whole canvas)}.
   * Moves the camera, never the panels; hold at least 2 s per stop over text. Returns the end time.
   */
  SP.tour = function (tl, canvas, stops, options) {
    var o = options || {};
    var cv = resolve(canvas);
    var f = Studio.format;
    var move = o.move || 0.8, drift = o.drift === undefined ? 1.025 : o.drift;
    // panels cross the frame edge during a pan by design; frame-review skips its clip check inside this canvas
    cv.setAttribute('data-layout-allow-overflow', 'camera-tour');
    global.gsap.set(cv, { x: 0, y: 0, scale: 1, transformOrigin: '0 0' });
    function frameBox(bx, by, bw, bh, pad, maxScale) {
      var s = Math.min(f.width * (1 - 2 * pad) / bw, f.height * (1 - 2 * pad) / bh, maxScale);
      var cx = bx + bw / 2, cy = by + bh / 2;
      return { s: s, cx: cx, cy: cy, x: f.width / 2 - s * cx, y: f.height / 2 - s * cy };
    }
    function camFor(cam, k) { var s = cam.s * k; return { x: f.width / 2 - s * cam.cx, y: f.height / 2 - s * cam.cy, scale: s }; }
    var overview = frameBox(0, 0, cv.offsetWidth, cv.offsetHeight, 0.04, 10);
    var cams = stops.map(function (st) {
      var t = resolve(st.target);
      var x = 0, y = 0, n = t;
      while (n && n !== cv) { x += n.offsetLeft; y += n.offsetTop; n = n.offsetParent; }
      return frameBox(x, y, t.offsetWidth, t.offsetHeight, st.pad === undefined ? 0.12 : st.pad, st.maxScale || 2.5);
    });
    var cur = camFor(o.start === 'first' && cams.length ? cams[0] : overview, 1);
    global.gsap.set(cv, cur);
    var end = 0;
    stops.forEach(function (st, i) {
      var to = camFor(cams[i], 1);
      tl.fromTo(cv, { x: cur.x, y: cur.y, scale: cur.scale }, { x: to.x, y: to.y, scale: to.scale, duration: move, ease: 'power2.inOut', immediateRender: false }, st.at);
      var next = i + 1 < stops.length ? stops[i + 1].at : (o.pullBack !== undefined ? o.pullBack : st.at + move + (o.hold || 3));
      var holdDur = next - st.at - move;
      cur = to;
      if (holdDur > 0.05 && drift !== 1) {
        var dr = camFor(cams[i], drift);
        tl.fromTo(cv, { x: cur.x, y: cur.y, scale: cur.scale }, { x: dr.x, y: dr.y, scale: dr.scale, duration: holdDur, ease: 'sine.inOut', immediateRender: false }, st.at + move);
        cur = dr;
      }
      end = st.at + move + Math.max(0, holdDur);
    });
    if (o.pullBack !== undefined) {
      var ov = camFor(overview, 1);
      tl.fromTo(cv, { x: cur.x, y: cur.y, scale: cur.scale }, { x: ov.x, y: ov.y, scale: ov.scale, duration: o.pullDuration || 0.9, ease: 'power2.inOut', immediateRender: false }, o.pullBack);
      end = o.pullBack + (o.pullDuration || 0.9);
    }
    return end;
  };

  // ------------------------------------------------------------------ 8. empty-stage dip
  /**
   * Section turn: the outgoing content sinks and fades (exit 0.3 s, power2.in), the empty stage holds (0.25 s) while
   * the background keeps moving, and the incoming group is shown at `at`, which is when its title starts (snap it
   * to the first word of the next phrase so the dip sits in the narration pause). options: {exit 0.3, hold 0.25,
   * entrance ('rise' | 'none': the caller animates the title, e.g. typewriter)}. Warns when hold > 0.5 s.
   * Use at section turns only, never on every scene. Returns the end of the entrance.
   */
  FX.dip = function (tl, outTarget, inTarget, at, options) {
    var o = options || {};
    var exit = o.exit === undefined ? 0.3 : o.exit, hold = o.hold === undefined ? 0.25 : o.hold;
    if (hold > 0.5 && global.console) global.console.warn('[studio] fx.dip hold ' + hold + 's: over 0.5 s of empty stage under narration reads as a stall');
    var start = Math.max(0, at - hold - exit);
    tl.fromTo(outTarget, { autoAlpha: 1, y: 0 }, { autoAlpha: 0, y: Studio.u(1.6), duration: exit, ease: 'power2.in', immediateRender: false }, start);
    if (o.entrance === 'none') { Studio.show(tl, inTarget, at); return at; }
    tl.fromTo(inTarget, { autoAlpha: 0, y: Studio.u(1.6) }, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'power3.out', immediateRender: true }, at);
    return at + 0.4;
  };

  // ------------------------------------------------------------------ 9. pause-locked copy swap
  /**
   * One copy slot whose versions share a grid cell (no reflow). swap() times the change from the phrase that
   * names the new copy: the old version fades (0.18 s), the slot is empty (0.08 s), the new one fades in (0.14 s)
   * and is first visible `lead` (0.3 s) before phraseStart. Pass the measured words (audio/words.json shape:
   * [{start, end, word}]) and swap() checks the swap sits in a pause; problems go to api.warnings.
   * Returns {el, versions, warnings, enter(tl, i, at), swap(tl, i, phraseStart, {lead, fadeOut, gap, fadeIn,
   * words}), exit(tl, at)}.
   */
  C.copySlot = function (parent, versions, options) {
    var o = options || {};
    var el = Studio.el('div', withClass('st-copyslot', o), null, resolve(parent));
    var spans = (versions || []).map(function (t) { var s = Studio.el('span', null, t, el); return s; });
    global.gsap.set(spans, { autoAlpha: 0 });
    var api = { el: el, versions: spans, warnings: [] };
    var current = -1;
    api.enter = function (tl, i, at) {
      current = i;
      tl.fromTo(spans[i], { autoAlpha: 0, y: Studio.u(0.8) }, { autoAlpha: 1, y: 0, duration: 0.35, ease: 'power3.out', immediateRender: true }, at);
      return at + 0.35;
    };
    api.swap = function (tl, i, phraseStart, opts) {
      var p = opts || {};
      var lead = p.lead === undefined ? 0.3 : p.lead, fo = p.fadeOut === undefined ? 0.18 : p.fadeOut;
      var gap = p.gap === undefined ? 0.08 : p.gap, fi = p.fadeIn === undefined ? 0.14 : p.fadeIn;
      var inStart = phraseStart - lead, outStart = inStart - gap - fo;
      var words = p.words || o.words;
      if (words && words.length) {
        words.forEach(function (w) {
          if (w.end > outStart + 0.02 && w.start < inStart - 0.02) {
            warn(api.warnings, 'copySlot swap to "' + spans[i].textContent + '" (' + outStart.toFixed(2) + '-' + inStart.toFixed(2) + 's) overlaps the spoken word "' + w.word + '" (' + w.start.toFixed(2) + '-' + w.end.toFixed(2) + 's): start it in the pause before, or shorten the fades');
          }
        });
      }
      if (current >= 0) tl.fromTo(spans[current], { autoAlpha: 1 }, { autoAlpha: 0, duration: fo, ease: 'power1.in', immediateRender: false }, outStart);
      tl.fromTo(spans[i], { autoAlpha: 0 }, { autoAlpha: 1, duration: fi, ease: 'power1.out', immediateRender: true }, inStart);
      current = i;
      return inStart + fi;
    };
    api.exit = function (tl, at) { return exitBox(tl, el, at); };
    return api;
  };

  // ------------------------------------------------------------------ 10. UI demo widgets
  /**
   * Generic, unbranded interface widgets for "how it works" demos. Never copy a real product's interface.
   *   input(parent, {placeholder, text}) -> {el, type(tl, at, {cps 18}) }
   *   button(parent, {label})            -> {el, press(tl, at)}
   *   toggle(parent, {on})               -> {el, flip(tl, at, on)}
   *   cursor(layer)                      -> {el, enter(tl, at, {x, y}), moveTo(tl, target, at, {duration 0.7, dx, dy}), click(tl, at)}
   *                                         `layer` should be a full-frame layer; targets are measured as they render at `at`
   *   notify(parent, {title, body})      -> {el, enter(tl, at), exit(tl, at)}
   */
  C.ui = {
    input: function (parent, data, options) {
      var o = options || {};
      var d = data || {};
      var el = Studio.el('div', withClass('st-ui-input', o), null, resolve(parent));
      var ph = Studio.el('span', 'st-ui-ph', d.placeholder || '', el);
      var txt = Studio.el('span', 'st-ui-text', '', el);
      var caret = Studio.el('span', 'st-ui-caret', null, el);
      var text = d.text || '';
      el.setAttribute('aria-label', text || d.placeholder || '');
      var state = driver(0, function (n) {
        var k = clamp(Math.floor(n + 1e-6), 0, text.length);
        txt.textContent = text.slice(0, k);
        ph.style.opacity = k > 0 ? '0' : '';
        caret.style.opacity = n > 0 && n < text.length + 0.5 ? '1' : '0';
      });
      return {
        el: el, state: state,
        type: function (tl, at, opts) {
          var cps = (opts && opts.cps) || 18;
          var end = state.go(tl, text.length, at, text.length / cps, 'none');
          return state.go(tl, text.length + 1, end + 0.4, SWITCH);
        }
      };
    },
    button: function (parent, data, options) {
      var el = Studio.el('div', withClass('st-ui-button', options), (data && data.label) || 'OK', resolve(parent));
      return {
        el: el,
        press: function (tl, at) {
          tl.fromTo(el, { scale: 1 }, { scale: 0.94, duration: 0.08, ease: 'power2.out', immediateRender: false }, at);
          tl.fromTo(el, { scale: 0.94 }, { scale: 1, duration: 0.22, ease: 'back.out(3)', immediateRender: false }, at + 0.08);
          tl.fromTo(el, { filter: 'brightness(1)' }, { filter: 'brightness(1.15)', duration: 0.1, ease: 'none', yoyo: true, repeat: 1, immediateRender: false }, at);
          return at + 0.3;
        }
      };
    },
    toggle: function (parent, data, options) {
      var el = Studio.el('div', withClass('st-ui-toggle', options), null, resolve(parent));
      var knob = Studio.el('div', 'st-ui-knob', null, el);
      var acc = tok('--c-positive', '#059669'), rule = tok('--c-rule', '#cbd5e1');
      var travel = Studio.u(3.6);
      var state = driver(data && data.on ? 1 : 0, function (v) {
        knob.style.transform = 'translateX(' + (v * travel).toFixed(2) + 'px)';
        el.style.background = v >= 0.5 ? acc : rule;
      });
      return {
        el: el, state: state,
        flip: function (tl, at, on) {
          var to = on === undefined ? (state.last >= 0.5 ? 0 : 1) : (on ? 1 : 0);
          return state.go(tl, to, at, 0.25, 'power2.inOut');
        }
      };
    },
    cursor: function (layer, options) {
      var host = resolve(layer) || document.getElementById('root');
      var el = Studio.el('div', withClass('st-ui-cursor', options), null, host);
      var svg = Studio.svg('svg', { viewBox: '0 0 24 24', width: '100%', height: '100%', 'aria-hidden': 'true' }, el);
      Studio.svg('path', { d: 'M3 2 L3 19 L7.5 14.8 L10.6 21.6 L13.6 20.3 L10.6 13.6 L16.8 13.6 Z', fill: tok('--c-ink', '#1e293b'), stroke: tok('--c-paper', '#fff'), 'stroke-width': 1.4, 'stroke-linejoin': 'round' }, svg);
      var ripple = Studio.el('div', 'st-ui-ripple', null, el);
      global.gsap.set(el, { autoAlpha: 0, x: 0, y: 0 });
      global.gsap.set(ripple, { autoAlpha: 0 });
      var pos = { x: 0, y: 0 };
      var api = { el: el };
      api.enter = function (tl, at, p) {
        pos = { x: p.x, y: p.y };
        tl.fromTo(el, { autoAlpha: 0, x: pos.x, y: pos.y }, { autoAlpha: 1, x: pos.x, y: pos.y, duration: 0.25, ease: 'power1.out', immediateRender: true }, at);
        return at + 0.25;
      };
      api.moveTo = function (tl, target, at, opts) {
        var p = opts || {};
        var b = Studio.boxAt(tl, target, at), hb = Studio.boxAt(tl, host, at);
        var hk = host.offsetWidth ? hb.w / host.offsetWidth : 1;
        var to = { x: (b.cx - hb.x) / hk + Studio.u(p.dx || 0), y: (b.cy - hb.y) / hk + Studio.u(p.dy || 0) };
        var dur = p.duration || 0.7;
        // different eases on x and y bend the path into a hand-like arc
        tl.fromTo(el, { x: pos.x }, { x: to.x, duration: dur, ease: 'power2.inOut', immediateRender: false }, at);
        tl.fromTo(el, { y: pos.y }, { y: to.y, duration: dur, ease: 'power1.inOut', immediateRender: false }, at);
        pos = to;
        return at + dur;
      };
      api.click = function (tl, at) {
        tl.fromTo(el, { scale: 1 }, { scale: 0.85, duration: 0.07, ease: 'power2.out', immediateRender: false }, at);
        tl.fromTo(el, { scale: 0.85 }, { scale: 1, duration: 0.16, ease: 'back.out(2.5)', immediateRender: false }, at + 0.07);
        tl.fromTo(ripple, { autoAlpha: 0.9, scale: 0.4 }, { autoAlpha: 0, scale: 1.6, duration: 0.4, ease: 'power2.out', immediateRender: false }, at);
        return at + 0.4;
      };
      api.exit = function (tl, at) { return exitBox(tl, el, at, { duration: 0.25 }); };
      return api;
    },
    notify: function (parent, data, options) {
      var d = data || {};
      var el = Studio.el('div', withClass('st-ui-notify', options), null, resolve(parent));
      Studio.el('b', null, d.title || '', el);
      if (d.body) Studio.el('span', null, d.body, el);
      global.gsap.set(el, { autoAlpha: 0 });
      return {
        el: el,
        enter: function (tl, at) {
          tl.fromTo(el, { autoAlpha: 0, y: -Studio.u(3) }, { autoAlpha: 1, y: 0, duration: 0.45, ease: 'back.out(1.6)', immediateRender: true }, at);
          return at + 0.45;
        },
        exit: function (tl, at) {
          tl.fromTo(el, { autoAlpha: 1, y: 0 }, { autoAlpha: 0, y: -Studio.u(2), duration: 0.3, ease: 'power2.in', immediateRender: false }, at);
          return at + 0.3;
        }
      };
    }
  };

  // ------------------------------------------------------------------ 11. headlines: two-tone pair, centred word build
  /**
   * preset 'pair' (default): data {line1, line2}; line 2 in the accent (options.tone 'accent'|'muted'), same size;
   * words rise 0.08 s apart, line 2 starts `lineDelay` (0.3 s) after line 1 has finished staggering, or at
   * options.line2At. Warns when line 2 is longer than line 1 (it loses the punch).
   * preset 'build': data {text}; one centred line that grows word by word, the visible words staying centred.
   * Returns {el, words, enter(tl, at, {times[]}), warnings} ('build' also has word(tl, k, at)).
   */
  C.headline = function (parent, data, options) {
    var o = options || {};
    var d = data || {};
    var preset = o.preset || 'pair';
    var el = Studio.el('div', withClass('st-hl', o), null, resolve(parent));
    var api = { el: el, warnings: [] };
    var rise = Studio.u(1.2);
    function words(line, text) {
      return String(text || '').split(/\s+/).filter(Boolean).map(function (w, i, arr) {
        var s = Studio.el('span', 'st-hl-word', w, line);
        if (i < arr.length - 1) line.appendChild(document.createTextNode(' '));
        return s;
      });
    }
    if (preset === 'build') {
      el.classList.add('st-hl-build');
      el.style.textAlign = 'left';
      var line = Studio.el('span', 'st-hl-line', null, el);
      var ws = words(line, d.text);
      el.setAttribute('aria-label', d.text || '');
      global.gsap.set(ws, { autoAlpha: 0 });
      var W = el.offsetWidth;
      var xs = ws.map(function (w) { return (W - (w.offsetLeft + w.offsetWidth)) / 2; });
      var lineX = xs.length ? xs[0] : 0;
      global.gsap.set(line, { x: lineX });
      var shown = 0;
      api.words = ws;
      api.word = function (tl, k, at) {
        tl.fromTo(line, { x: lineX }, { x: xs[k], duration: 0.35, ease: 'power2.inOut', immediateRender: false }, at);
        lineX = xs[k];
        tl.fromTo(ws[k], { autoAlpha: 0, y: rise }, { autoAlpha: 1, y: 0, duration: 0.3, ease: 'power3.out', immediateRender: true }, at + 0.05);
        shown = k + 1;
        return at + 0.35;
      };
      api.enter = function (tl, at, opts) {
        var p = opts || {};
        var times = p.times || ws.map(function (_, k) { return at + k * (p.stagger || 0.35); });
        var end = at;
        for (var k = shown; k < ws.length; k++) end = api.word(tl, k, times[k] === undefined ? end : times[k]);
        return end;
      };
      return api;
    }
    var l1 = Studio.el('span', 'st-hl-line', null, el), l2 = Studio.el('span', 'st-hl-line', null, el);
    var w1 = words(l1, d.line1), w2 = words(l2, d.line2);
    l2.style.color = o.tone === 'muted' ? 'var(--c-ink-2)' : (o.color || 'var(--c-accent)');
    el.setAttribute('aria-label', (d.line1 || '') + ' ' + (d.line2 || ''));
    global.gsap.set(w1.concat(w2), { autoAlpha: 0 });
    if (w2.length > w1.length) warn(api.warnings, 'headline pair: line 2 ("' + d.line2 + '") is longer than line 1; it loses the punch');
    api.words = w1.concat(w2);
    api.enter = function (tl, at, opts) {
      var p = opts || {};
      var stagger = p.stagger === undefined ? 0.08 : p.stagger;
      tl.fromTo(w1, { autoAlpha: 0, y: rise }, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'power3.out', stagger: stagger, immediateRender: true }, at);
      var t2 = o.line2At !== undefined ? o.line2At : at + stagger * Math.max(0, w1.length - 1) + (o.lineDelay === undefined ? 0.3 : o.lineDelay);
      tl.fromTo(w2, { autoAlpha: 0, y: rise }, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'power3.out', stagger: stagger, immediateRender: true }, t2);
      return t2 + 0.4 + stagger * Math.max(0, w2.length - 1);
    };
    api.exit = function (tl, at) { return exitBox(tl, el, at); };
    return api;
  };
})(typeof window !== 'undefined' ? window : this);
