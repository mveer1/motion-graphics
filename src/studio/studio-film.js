/*
 * Motion Lab studio runtime - film helpers (src/studio/studio-film.js)
 * The pieces narrated films kept hand-coding (the cloud, Korea and fridge films each spent 620-730 lines on
 * them, the fitness films repeated the word-snapped cues), promoted into the runtime on 2026-11-24:
 *
 *   Studio.comp.kicker(parent, {text})            typed kicker: characters type on, a caret follows; type(i) retypes
 *   Studio.comp.captionBand(parent, cues, opts)    a caption plate the film owns: one band, cues swap inside it
 *   Studio.comp.stamp(parent, {text, sub, tone})   a bordered verdict stamp that slams on (Studio.fx.stamp)
 *   Studio.comp.tileGrid(parent, {count, ...})     a waffle grid whose tiles change state in a fixed or seeded order
 *   Studio.comp.stations(parent, stations, opts)   one layer per station (exercise, step, chapter), cross-faded
 *   Studio.type.counterRoll(parent, opts)          odometer digits that roll to each value, carry included
 *   Studio.space.sceneDrift(tl, scenes, opts)      per-scene camera drift, continuous across scenes on one stage
 *   Studio.cues.fromWords(spec, opts)              cue times snapped to measured spoken words
 *
 * Builders follow the compositions contract: they create DOM in `parent` and return handles plus methods that
 * add tweens and return their end time. Methods that change state (kicker.type, tileGrid.to, counterRoll.to)
 * must be called in time order: each tween starts from the state the previous call left. Sizes come from --u
 * and the --safe-* insets (studio-base.css, "film helpers"); per-format numbers go through Studio.pick.
 * Requires studio-core.js, studio-draw.js, studio-type.js, studio-motion.js and studio-compositions.js.
 */
(function (global) {
  'use strict';

  var Studio = global.Studio;
  if (!Studio || !Studio.comp || !Studio.space || !Studio.type) throw new Error('studio-film.js requires the other studio runtime files (load it after studio-compositions.js)');
  var C = Studio.comp, T = Studio.type, SP = Studio.space;
  var SWITCH = 0.001;

  function resolve(p) { return typeof p === 'string' ? document.querySelector(p) : p; }
  function withClass(base, o) { return base + (o && o.className ? ' ' + o.className : ''); }
  function own(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
  /** A per-format map ({landscape, portrait, square, default}) goes through Studio.pick; anything else is returned as is. */
  function perFormat(v) {
    if (v && typeof v === 'object' && !Array.isArray(v) && (own(v, 'landscape') || own(v, 'portrait') || own(v, 'square') || own(v, 'default'))) return Studio.pick(v);
    return v;
  }
  /** 'var(--c-accent)', '--c-accent' or a colour; GSAP cannot interpolate var(), so tokens are read once at build. */
  function colour(v, fallback) {
    if (!v) return fallback;
    var m = /^var\((--[^,)]+)(?:,\s*([^)]+))?\)$/.exec(v);
    if (m) return Studio.token(m[1], m[2] || fallback);
    if (v.indexOf('--') === 0) return Studio.token(v, fallback);
    return v;
  }
  /** x offset of `el` inside `box`, in box layout pixels (undoes any scale already set on an ancestor). */
  function localLeft(el, box) {
    var b = box.getBoundingClientRect(), r = el.getBoundingClientRect();
    var k = b.width > 0 ? box.offsetWidth / b.width : 1;
    return { left: (r.left - b.left) * k, right: (r.right - b.left) * k };
  }

  // ------------------------------------------------------------------ typed kicker
  /**
   * Typed kicker: a small label (scene number, place, date) types on character by character and a caret follows
   * the last typed character. data.text is a string or a list of labels; enter(tl, at) types the first,
   * type(tl, index, at) erases the current one and types another (call in time order). options: {cps (28),
   * caret (true), blink (2 blinks after each pass)}. The labels share one box, so the kicker never reflows.
   * Returns {el, versions, enter(tl, at), type(tl, index, at, {cps}), exit(tl, at)}.
   */
  C.kicker = function (parent, data, options) {
    var o = options || {};
    var texts = [].concat(data.text === undefined ? '' : data.text);
    var el = Studio.el('div', withClass('st-tkicker', o), null, resolve(parent));
    el.setAttribute('aria-label', texts.join(' / '));
    var box = Studio.el('span', 'st-tkicker-box', null, el);
    box.setAttribute('aria-hidden', 'true');
    var versions = texts.map(function (t) {
      var v = Studio.el('span', 'st-tkicker-text', t, box);
      return { el: v, chars: T.split(v, { type: 'chars' }).chars };
    });
    var caret = o.caret === false ? null : Studio.el('span', 'st-tkicker-caret', null, box);
    versions.forEach(function (v) {
      v.stops = [0].concat(v.chars.map(function (c) { return localLeft(c, box).right; }));
    });
    var cps = o.cps || 28;
    var blinks = o.blink === undefined ? 2 : o.blink;
    var current = -1, caretX = 0, pending = [];

    function moveCaret(tl, stops, at, step, backwards) {
      if (!caret) return;
      var n = stops.length - 1;
      for (var k = 0; k < n; k++) {
        var a = backwards ? stops[n - k] : stops[k], b = backwards ? stops[n - k - 1] : stops[k + 1];
        tl.fromTo(caret, { x: a }, { x: b, duration: SWITCH, ease: 'none', immediateRender: false }, at + k * step);
      }
      caretX = backwards ? stops[0] : stops[n];
    }
    function caretOn(tl, at) {
      if (!caret) return;
      // a new pass cancels the blink-out of the previous one, so the caret never flickers mid-word
      pending.forEach(function (tw) { if (tw.startTime() >= at - 1e-6) tl.remove(tw); });
      pending = [];
      tl.fromTo(caret, { autoAlpha: 0 }, { autoAlpha: 1, duration: SWITCH, ease: 'none', immediateRender: false }, at);
    }
    function caretOff(tl, at) {
      if (!caret) return at;
      var t = at;
      for (var i = 0; i < blinks; i++) {
        pending.push(tl.fromTo(caret, { autoAlpha: 1 }, { autoAlpha: 0, duration: SWITCH, ease: 'none', immediateRender: false }, t + 0.3).recent());
        pending.push(tl.fromTo(caret, { autoAlpha: 0 }, { autoAlpha: 1, duration: SWITCH, ease: 'none', immediateRender: false }, t + 0.6).recent());
        t += 0.6;
      }
      pending.push(tl.fromTo(caret, { autoAlpha: 1 }, { autoAlpha: 0, duration: SWITCH, ease: 'none', immediateRender: false }, t + 0.3).recent());
      return t + 0.3;
    }
    function typeIn(tl, i, at, rate) {
      var v = versions[i], step = 1 / rate;
      if (v.chars.length) tl.fromTo(v.chars, { autoAlpha: 0 }, { autoAlpha: 1, duration: SWITCH, ease: 'none', stagger: step, immediateRender: true }, at);
      caretOn(tl, at);
      moveCaret(tl, v.stops, at, step, false);
      current = i;
      var end = at + step * v.chars.length;
      caretOff(tl, end);
      return end;
    }
    function erase(tl, at, rate) {
      var v = versions[current], step = 1 / (rate * 2.5);
      if (v.chars.length) tl.fromTo(v.chars.slice().reverse(), { autoAlpha: 1 }, { autoAlpha: 0, duration: SWITCH, ease: 'none', stagger: step, immediateRender: false }, at);
      caretOn(tl, at);
      moveCaret(tl, v.stops, at, step, true);
      return at + step * v.chars.length;
    }
    if (caret) global.gsap.set(caret, { x: caretX, autoAlpha: 0 });
    return {
      el: el, versions: versions, caret: caret,
      enter: function (tl, at, eo) {
        Studio.show(tl, el, at);
        return typeIn(tl, 0, at, (eo && eo.cps) || cps);
      },
      type: function (tl, index, at, so) {
        if (index < 0 || index >= versions.length) throw new Error('Studio.comp.kicker: no label ' + index);
        var rate = (so && so.cps) || cps;
        var t = current >= 0 ? erase(tl, at, rate) + 0.08 : at;
        return typeIn(tl, index, t, rate);
      },
      exit: function (tl, at) {
        tl.fromTo(el, { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.3, ease: 'power1.in', immediateRender: false }, at);
        return at + 0.3;
      }
    };
  };

  // ------------------------------------------------------------------ caption band
  /**
   * Caption band: a plate the film owns at a fixed height (the cloud film's band), with cue texts swapping inside
   * it, instead of Studio.comp.captions' floating per-cue plates. cues: [{start, end, text, words?}] as written by
   * `studio.py captions` (window.STUDIO_CAPTIONS); a cue with measured words lights the word being spoken.
   * options: {band: {top, bottom} fractions of the frame height, or a per-format map of them (default: a strip
   * whose bottom edge is the safe bottom), full (true: edge to edge; false: inside the safe sides), enterAt,
   * hold (keep the plate after the last cue), highlight (true)}.
   * Texts carry class st-caption, so motion-qa waives them and the gap audit does not count them as picture
   * changes; declare the same fractions as the style template's rules.caption_band when the film draws it.
   * Returns {el, texts, band: {top, bottom}, schedule(tl) -> end time}.
   */
  C.captionBand = function (parent, cues, options) {
    var o = options || {};
    var f = Studio.format;
    var band = perFormat(o.band);
    if (!band) {
      var bottom = (f.height - f.safe.bottom) / f.height;
      band = { top: bottom - Studio.pick({ portrait: 0.102, landscape: 0.13, square: 0.11 }), bottom: bottom };
    }
    var el = Studio.el('div', withClass('st-capband', o), null, resolve(parent));
    el.setAttribute('data-layout-allow-caption-zone', '');
    el.style.top = (band.top * f.height).toFixed(1) + 'px';
    el.style.height = ((band.bottom - band.top) * f.height).toFixed(1) + 'px';
    if (o.full === false) { el.style.left = f.safe.left + 'px'; el.style.right = f.safe.right + 'px'; }
    var spans = [];
    var texts = cues.map(function (c, i) {
      var timed = o.highlight !== false && c.words && c.words.length;
      var p = Studio.el('p', 'st-caption st-capband-text', timed ? null : c.text, el);
      p.setAttribute('data-layout-allow-caption-zone', '');
      spans[i] = [];
      if (timed) {
        c.words.forEach(function (w, k) {
          if (k) p.appendChild(document.createTextNode(' '));
          var s = Studio.el('span', 'st-caption-word' + (w.em ? ' st-caption-em' : ''), w.text, p);
          spans[i].push(w.em ? null : s);
        });
      }
      return p;
    });
    return {
      el: el, texts: texts, band: { top: +band.top.toFixed(4), bottom: +band.bottom.toFixed(4) },
      schedule: function (tl) {
        if (!cues.length) return 0;
        var first = cues[0].start, last = cues[cues.length - 1].end;
        var enterAt = o.enterAt === undefined ? Math.max(0, first - 0.2) : o.enterAt;
        if (enterAt <= 0) global.gsap.set(el, { autoAlpha: 1 });
        else tl.fromTo(el, { autoAlpha: 0, scaleX: 0.97 }, { autoAlpha: 1, scaleX: 1, duration: 0.3, ease: 'power2.out', immediateRender: true }, enterAt);
        cues.forEach(function (c, i) {
          var fade = Math.min(0.12, (c.end - c.start) / 4);
          tl.fromTo(texts[i], { autoAlpha: 0, y: Studio.u(0.6) }, { autoAlpha: 1, y: 0, duration: fade * 1.5, ease: 'power2.out', immediateRender: true }, c.start);
          tl.fromTo(texts[i], { autoAlpha: 1 }, { autoAlpha: 0, duration: fade, ease: 'none', immediateRender: false }, c.end - fade);
          spans[i].forEach(function (s, k) {
            if (!s) return;
            var on = Math.max(c.start, c.words[k].start);
            var off = k + 1 < spans[i].length ? Math.max(on, c.words[k + 1].start) : c.end;
            var d = Math.min(0.06, (off - on) / 2);
            tl.fromTo(s, { '--st-hl': 0 }, { '--st-hl': 1, duration: d, ease: 'none', immediateRender: false }, on);
            if (k + 1 < spans[i].length) tl.fromTo(s, { '--st-hl': 1 }, { '--st-hl': 0, duration: d, ease: 'none', immediateRender: false }, off);
          });
        });
        if (o.hold) return last;
        tl.fromTo(el, { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.3, ease: 'power1.in', immediateRender: false }, last + 0.05);
        return last + 0.35;
      }
    };
  };

  // ------------------------------------------------------------------ stamp
  var TONES = { accent: '--c-accent', second: '--c-accent-2', third: '--c-accent-3', ink: '--c-ink', muted: '--c-ink-2', positive: '--c-positive', negative: '--c-negative' };
  /**
   * Stamp: a bordered, tilted verdict label ("CONFIRMED", "MYTH", "-18 C") centred on a point of its parent,
   * slammed on with Studio.fx.stamp. data: {text, sub (small second line), tone: accent|second|third|ink|muted|
   * positive|negative or a colour, x, y (centre as fractions of the parent, or a per-format map), rotate (-7 deg)}.
   * options: {shake (element to shake on impact, e.g. the scene), className}.
   * Returns {el, enter(tl, at), exit(tl, at)}.
   */
  C.stamp = function (parent, data, options) {
    var o = options || {};
    var host = resolve(parent);
    var pos = Studio.el('div', 'st-stamp-pos', null, host);
    var x = perFormat(data.x), y = perFormat(data.y);
    pos.style.left = ((x === undefined ? 0.5 : x) * 100) + '%';
    pos.style.top = ((y === undefined ? 0.5 : y) * 100) + '%';
    var el = Studio.el('div', withClass('st-stamp', o), null, pos);
    var tone = data.tone || 'accent';
    el.style.setProperty('--stamp-c', colour(TONES[tone] || tone, '#c8462b'));
    Studio.el('span', 'st-stamp-text', data.text, el);
    if (data.sub) Studio.el('span', 'st-stamp-sub', data.sub, el);
    var rotate = data.rotate === undefined ? -7 : data.rotate;
    global.gsap.set(el, { autoAlpha: 0, rotation: rotate });
    return {
      el: el,
      enter: function (tl, at, eo) {
        var e = eo || {};
        return Studio.fx.stamp(tl, el, at, { rotate: rotate, shake: e.shake || o.shake, duration: e.duration });
      },
      exit: function (tl, at) {
        tl.fromTo(el, { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.25, ease: 'power1.in', immediateRender: false }, at);
        return at + 0.25;
      }
    };
  };

  // ------------------------------------------------------------------ tile grid
  function tileOrder(n, cols, order, seed) {
    var idx = [];
    for (var i = 0; i < n; i++) idx.push(i);
    if (Array.isArray(order)) return order.slice();
    if (order === 'column') {
      var rows = Math.ceil(n / cols), out = [];
      for (var c = 0; c < cols; c++) for (var r = 0; r < rows; r++) if (r * cols + c < n) out.push(r * cols + c);
      return out;
    }
    if (order === 'centre' || order === 'center') {
      var rr = Math.ceil(n / cols), cx = (cols - 1) / 2, cy = (rr - 1) / 2;
      return idx.sort(function (a, b) {
        var da = Math.pow(a % cols - cx, 2) + Math.pow(Math.floor(a / cols) - cy, 2), db = Math.pow(b % cols - cx, 2) + Math.pow(Math.floor(b / cols) - cy, 2);
        return da - db || a - b;
      });
    }
    if (order === 'seeded') {
      var rnd = Studio.rng(seed || 7);
      for (var k = n - 1; k > 0; k--) { var j = Math.floor(rnd() * (k + 1)); var t = idx[k]; idx[k] = idx[j]; idx[j] = t; }
    }
    return idx;
  }
  /**
   * Tile grid (waffle): `count` tiles in `columns` columns (a number or per-format map) that change state.
   * data: {count, columns, states: {name: colour or token}, initial (state name), order: 'reading' | 'column' |
   * 'centre' | 'seeded' | [indices], seed}. to(tl, {stateA: n, stateB: m}, at, {stagger, duration}) makes the
   * first n tiles of the order stateA, the next m stateB and the rest the initial state; only tiles that change
   * animate, in order (call in time order). enter(tl, at) pops the tiles in along the order.
   * Returns {el, tiles, order, states, enter, to, counts() -> the counts after the last call, exit}.
   */
  C.tileGrid = function (parent, data, options) {
    var o = options || {};
    var n = data.count || 100;
    var cols = perFormat(data.columns) || 10;
    var el = Studio.el('div', withClass('st-tiles', o), null, resolve(parent));
    el.style.setProperty('--tg-cols', String(cols));
    if (data.gap !== undefined) el.style.setProperty('--tg-gap', 'calc(var(--u) * ' + data.gap + ')');
    if (data.round) el.setAttribute('data-round', '');
    var states = {};
    var defs = data.states || { off: '--c-rule', on: '--c-accent' };
    Object.keys(defs).forEach(function (k) { states[k] = colour(defs[k], '#999999'); });
    var initial = data.initial || Object.keys(states)[0];
    if (!own(states, initial)) throw new Error('Studio.comp.tileGrid: initial state "' + initial + '" is not in states');
    var tiles = [], state = [];
    for (var i = 0; i < n; i++) {
      var t = Studio.el('span', 'st-tile', null, el);
      t.style.backgroundColor = states[initial];
      tiles.push(t);
      state.push(initial);
    }
    var order = tileOrder(n, cols, data.order || 'reading', data.seed);
    var last = {};
    return {
      el: el, tiles: tiles, order: order, states: states,
      enter: function (tl, at, eo) {
        var stagger = (eo && eo.stagger) || Math.min(0.012, 1.2 / n);
        var ordered = order.map(function (k) { return tiles[k]; });
        tl.fromTo(ordered, { autoAlpha: 0, scale: 0.4 }, { autoAlpha: 1, scale: 1, duration: 0.35, ease: 'back.out(2)', stagger: stagger, immediateRender: true }, at);
        return at + 0.35 + stagger * (n - 1);
      },
      to: function (tl, counts, at, so) {
        var s = so || {};
        var want = [], k = 0;
        Object.keys(counts).forEach(function (name) {
          if (!own(states, name)) throw new Error('Studio.comp.tileGrid: unknown state "' + name + '"');
          for (var c = 0; c < counts[name] && k < n; c++, k++) want[order[k]] = name;
        });
        var changed = [];
        order.forEach(function (ti) {
          var target = want[ti] || initial;
          if (target !== state[ti]) changed.push({ tile: ti, from: state[ti], to: target });
        });
        var stagger = s.stagger === undefined ? Math.min(0.02, 1.0 / Math.max(1, changed.length)) : s.stagger;
        var dur = s.duration || 0.3;
        // one tween per (from, to) pair; the stagger function keeps the global order across the pairs
        var groups = {};
        changed.forEach(function (ch, j) {
          var key = ch.from + '>' + ch.to;
          (groups[key] = groups[key] || { from: ch.from, to: ch.to, els: [], delays: [] }).els.push(tiles[ch.tile]);
          groups[key].delays.push(j * stagger);
          state[ch.tile] = ch.to;
        });
        Object.keys(groups).forEach(function (key) {
          var g = groups[key];
          tl.fromTo(g.els, { backgroundColor: states[g.from] }, {
            backgroundColor: states[g.to], duration: dur, ease: 'power1.out', immediateRender: false,
            stagger: function (i) { return g.delays[i]; }
          }, at);
        });
        last = {};
        Object.keys(counts).forEach(function (name) { last[name] = counts[name]; });
        return at + dur + stagger * Math.max(0, changed.length - 1);
      },
      counts: function () { return last; },
      exit: function (tl, at) {
        tl.fromTo(el, { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.35, ease: 'power1.in', immediateRender: false }, at);
        return at + 0.35;
      }
    };
  };

  // ------------------------------------------------------------------ stations
  /**
   * Stations: one layer per station (an exercise, a step, a chapter), each visible in its own window and
   * cross-faded at the boundary with the next (zero-dip, centred on the boundary). parent is an element or a
   * list of elements; each station gets one layer in every parent (a <g> in an SVG parent, a div otherwise), so
   * the picture and its copy fade together. stations: [{id, start, end, build(layers, win, tl)}]; build adds the
   * station's own tweens inside win = {index, start, end, in, out} (in/out: when it is fully visible).
   * options: {fade (0.5), hold (true: the last station stays to the end), className}.
   * Returns {layers, windows, schedule(tl) -> end time}.
   */
  C.stations = function (parent, stations, options) {
    var o = options || {};
    var hosts = Studio.all(parent);
    var fade = o.fade === undefined ? 0.5 : o.fade;
    var layers = stations.map(function (st, i) {
      return hosts.map(function (h) {
        var isSvg = h.namespaceURI === 'http://www.w3.org/2000/svg';
        var l = isSvg ? Studio.svg('g', { 'class': 'st-station' }) : Studio.el('div', withClass('st-station', o));
        l.setAttribute('data-station', st.id || String(i));
        h.appendChild(l);
        global.gsap.set(l, { autoAlpha: 0 });
        return l;
      });
    });
    var windows = stations.map(function (st, i) {
      var prev = stations[i - 1], next = stations[i + 1];
      var joinIn = prev && Math.abs(prev.end - st.start) < 1e-3, joinOut = next && Math.abs(next.start - st.end) < 1e-3;
      return { index: i, id: st.id, start: st.start, end: st.end, in: joinIn ? st.start + fade / 2 : st.start, out: joinOut ? st.end - fade / 2 : st.end };
    });
    return {
      layers: layers, windows: windows,
      schedule: function (tl) {
        stations.forEach(function (st, i) {
          var prev = stations[i - 1];
          if (prev && Math.abs(prev.end - st.start) < 1e-3) Studio.crossfade(tl, layers[i - 1], layers[i], st.start, fade);
          else {
            if (prev) Studio.hide(tl, layers[i - 1], prev.end);
            Studio.show(tl, layers[i], st.start);
          }
          if (st.build) st.build(layers[i], windows[i], tl);
        });
        var lastSt = stations[stations.length - 1];
        if (!lastSt) return 0;
        if (o.hold === false) Studio.hide(tl, layers[layers.length - 1], lastSt.end);
        return lastSt.end;
      }
    };
  };

  // ------------------------------------------------------------------ counter roll
  /**
   * Odometer counter: one rolling digit column per place; lower places roll continuously and a higher place turns
   * over only while the place below passes from 9 to 0, like a mechanical counter. options: {value (start, 0),
   * digits (minimum integer places, 1), decimals (0), group (',' every three places; '' for none), prefix,
   * suffix, pad (false: leading zeros stay hidden), className}. The box is as wide as the largest value it is
   * sent to (tabular digits), so it never reflows. to(tl, value, at, {duration (1.2), ease}) - call in time order.
   * Seek-safe: GSAP tweens one number whose setter places the columns. Returns {el, to, value()}.
   */
  T.counterRoll = function (parent, options) {
    var o = options || {};
    var decimals = o.decimals || 0, scale = Math.pow(10, decimals);
    var group = o.group === undefined ? ',' : o.group;
    var el = Studio.el('span', withClass('st-odo', o), null, resolve(parent));
    if (o.prefix) Studio.el('span', 'st-odo-affix', o.prefix, el);
    var digitsBox = Studio.el('span', 'st-odo-digits', null, el);
    digitsBox.setAttribute('aria-hidden', 'true');
    if (o.suffix) Studio.el('span', 'st-odo-affix', o.suffix, el);
    var cols = [];                           // cols[p] is place p (0 = the last decimal or the units)
    function places(v) { var u = Math.round(Math.abs(v) * scale); return Math.max(String(u).length, (o.digits || 1) + decimals); }
    function addColumn() {
      var p = cols.length;
      var col = Studio.el('span', 'st-odo-col');
      var strip = Studio.el('span', 'st-odo-strip', null, col);
      for (var d = 0; d <= 10; d++) Studio.el('span', 'st-odo-cell', String(d % 10), strip);
      var sep = null;
      if (decimals && p === decimals) sep = Studio.el('span', 'st-odo-sep', '.');
      else if (group && p > decimals && (p - decimals) % 3 === 0) sep = Studio.el('span', 'st-odo-sep', group);
      if (sep) digitsBox.insertBefore(sep, digitsBox.firstChild);
      digitsBox.insertBefore(col, digitsBox.firstChild);
      cols.push({ col: col, strip: strip, sep: sep });
    }
    function ensure(v) { while (cols.length < places(v)) addColumn(); }
    var value = o.value || 0;
    function render(v) {
      var u = Math.max(0, Math.abs(v) * scale);
      var whole = Math.floor(u + 1e-9);
      for (var p = 0; p < cols.length; p++) {
        var unit = Math.pow(10, p);
        var digit = Math.floor(whole / unit) % 10;
        // carry: this place moves only while every place below it reads 9 and rolls over
        var below = u - Math.floor(u / unit) * unit;
        var carry = p === 0 ? u - whole : Math.max(0, below - (unit - 1));
        var pos = digit + carry;
        cols[p].strip.style.transform = 'translateY(' + (-pos).toFixed(4) + 'em)';
        var significant = o.pad || p <= decimals || u >= unit - 1e-9;
        var a = significant ? 1 : Math.max(0, Math.min(1, u - (unit - 1)));
        cols[p].col.style.opacity = String(a);
        if (cols[p].sep) cols[p].sep.style.opacity = String(o.pad || p <= decimals ? 1 : a);
      }
      value = v;
    }
    ensure(value);
    Object.defineProperty(el, '__stOdo', { get: function () { return value; }, set: render, configurable: true });
    render(value);
    var cursor = value;
    return {
      el: el,
      value: function () { return cursor; },
      to: function (tl, v, at, so) {
        var s = so || {};
        ensure(v);
        render(value);
        var dur = s.duration || 1.2;
        tl.fromTo(el, { __stOdo: cursor }, { __stOdo: v, duration: dur, ease: s.ease || 'power2.inOut', immediateRender: false }, at);
        cursor = v;
        return at + dur;
      }
    };
  };

  // ------------------------------------------------------------------ per-scene drift
  /**
   * Per-scene drift: a slow, linear camera drift on each scene's stage for the whole scene window, so a held
   * picture is never frozen. scenes: [{target, start, end}] (or one object). Consecutive windows on the same target
   * continue from where the last one stopped (scale alternates between 1 and 1 + amount, the offset wanders by a
   * seeded amount), so a stage shared by several scenes never jumps. options: {amount (0.035), travel (1.2 u),
   * seed (7), ease ('none'), origin}. Linear on purpose: the pre-render gap audit treats a linear tween of 4 s or
   * more as an ambient layer, so the drift keeps the frame alive without hiding a missing visual event.
   * Do not combine with Studio.space.camera on the same element (both own its transform). Returns the last end.
   */
  SP.sceneDrift = function (tl, scenes, options) {
    var o = options || {};
    var list = [].concat(scenes).slice().sort(function (a, b) { return a.start - b.start; });
    var amount = o.amount === undefined ? 0.035 : o.amount;
    var travel = Studio.u(o.travel === undefined ? 1.2 : o.travel);
    var rnd = Studio.rng(o.seed || 7);
    var at = [];
    var end = 0;
    list.forEach(function (sc) {
      var el = Studio.all(sc.target)[0];
      if (!el) throw new Error('Studio.space.sceneDrift: target not found');
      var rec = null;
      for (var i = 0; i < at.length; i++) if (at[i].el === el) rec = at[i];
      if (!rec) { rec = { el: el, scale: 1, x: 0, y: 0 }; at.push(rec); }
      var to = {
        scale: rec.scale > 1 + amount / 2 ? 1 : 1 + amount,
        x: (rnd() * 2 - 1) * travel,
        y: (rnd() * 2 - 1) * travel * 0.6
      };
      tl.fromTo(el, { scale: rec.scale, x: rec.x, y: rec.y, transformOrigin: o.origin || '50% 50%' },
        { scale: to.scale, x: to.x, y: to.y, duration: Math.max(0.1, sc.end - sc.start), ease: o.ease || 'none', immediateRender: false }, sc.start);
      rec.scale = to.scale; rec.x = to.x; rec.y = to.y;
      end = Math.max(end, sc.end);
    });
    return end;
  };

  // ------------------------------------------------------------------ word-snapped cues
  var CU = Studio.cues;
  /** Same normalisation as src/pipeline/captions.py norm(): lower case, letters and digits only. */
  CU.norm = function (s) { return String(s).toLowerCase().replace(/[^a-z0-9]/g, ''); };
  /**
   * Measured words as runs of [{text, start, end, scene?}]: from options.words (audio/words.json's object, its
   * `scenes` map, or a flat list), else window.STUDIO_WORDS, else the words inside window.STUDIO_CAPTIONS cues
   * (src/captions.js after `studio.py captions --timing words`). A phrase never matches across two runs.
   */
  CU.words = function (source) {
    var src = source === undefined ? (global.STUDIO_WORDS || null) : source;
    if (src && src.scenes) src = src.scenes;
    if (Array.isArray(src)) return src.length ? [src.slice()] : [];
    if (src && typeof src === 'object') {
      return Object.keys(src).map(function (sid) {
        return (src[sid] || []).map(function (w) { return { text: w.text, start: w.start, end: w.end, scene: sid }; });
      }).filter(function (r) { return r.length; });
    }
    var caps = global.STUDIO_CAPTIONS || [];
    var flat = [];
    caps.forEach(function (c) { (c.words || []).forEach(function (w) { flat.push({ text: w.text, start: w.start, end: w.end }); }); });
    return flat.length ? [flat] : [];
  };
  /** Every place a phrase is spoken: [{start, end, text, scene}] in film time (studio.py words, in the browser). */
  CU.findAll = function (phrase, runs) {
    var want = String(phrase).split(/\s+/).map(CU.norm).filter(Boolean);
    var hits = [];
    if (!want.length) return hits;
    (runs || CU.words()).forEach(function (ws) {
      var have = ws.map(function (w) { return CU.norm(w.text); });
      for (var i = 0; i + want.length <= have.length; i++) {
        var ok = true;
        for (var k = 0; k < want.length && ok; k++) ok = have[i + k] === want[k];
        if (ok) hits.push({ start: ws[i].start, end: ws[i + want.length - 1].end, scene: ws[i].scene, text: ws.slice(i, i + want.length).map(function (w) { return w.text; }).join(' ') });
      }
    });
    return hits.sort(function (a, b) { return a.start - b.start; });
  };
  /**
   * Cue times snapped to the measured words (the build_cues.py pattern, at build time in the page):
   *   var cue = Studio.cues.fromWords({
   *     s2: {say: 'push-up', fallback: 4.4},              // onset of the first "push-up"
   *     tip: {say: 'slow down', after: 's2', edge: 'end', offset: 0.1, fallback: 7},
   *     end: 16                                            // a plain number is a fixed time
   *   });
   *   cue('tip', -0.2)
   * Entry: a number, a phrase, or {say, nth (1), after (a cue name defined earlier or a time), within [a, b],
   * scene (words.json scene id), edge ('start' | 'end'), offset, fallback (seconds or a cue name)}.
   * With no measured words every cue takes its fallback (the film still builds before audio exists); a phrase
   * that is missing from measured words takes its fallback with a console warning, or throws with options.strict.
   * options: {words (see Studio.cues.words), strict}. Returns a Studio.cues accessor with .snapped (names timed
   * from words), .missing (names that fell back) and .source ('words' | 'none').
   */
  CU.fromWords = function (spec, options) {
    var o = options || {};
    var runs = CU.words(o.words);
    var have = runs.length > 0;
    var map = {}, snapped = [], missing = [];
    function timeOf(ref, name) {
      if (typeof ref === 'number') return ref;
      if (typeof ref === 'string' && own(map, ref)) return map[ref];
      throw new Error('Studio.cues.fromWords: cue "' + name + '" refers to "' + ref + '", which is not defined before it');
    }
    Object.keys(spec).forEach(function (name) {
      var e = spec[name];
      if (typeof e === 'number') { map[name] = e; return; }
      if (typeof e === 'string') e = { say: e };
      var t = null;
      if (have && e.say) {
        var after = e.after === undefined ? -Infinity : timeOf(e.after, name);
        var hits = CU.findAll(e.say, runs).filter(function (h) {
          return h.start >= after - 1e-6 && (!e.scene || h.scene === e.scene) && (!e.within || (h.start >= e.within[0] && h.start <= e.within[1]));
        });
        var hit = hits[(e.nth || 1) - 1];
        if (hit) { t = (e.edge === 'end' ? hit.end : hit.start) + (e.offset || 0); snapped.push(name); }
      }
      if (t === null) {
        if (e.fallback === undefined) throw new Error('Studio.cues.fromWords: "' + e.say + '" (cue ' + name + ') ' + (have ? 'is not in the measured words' : 'has no measured words') + ' and no fallback');
        if (have && e.say) {
          if (o.strict) throw new Error('Studio.cues.fromWords: "' + e.say + '" (cue ' + name + ') is not in the measured words');
          if (global.console) global.console.warn('[studio] cue ' + name + ': "' + e.say + '" is not in the measured words; using its fallback');
        }
        t = timeOf(e.fallback, name) + (typeof e.fallback === 'string' ? (e.offset || 0) : 0);
        missing.push(name);
      }
      map[name] = Math.max(0, t);
    });
    var fn = CU(map);
    fn.snapped = snapped;
    fn.missing = missing;
    fn.source = have ? 'words' : 'none';
    return fn;
  };
})(typeof window !== 'undefined' ? window : this);
