/*
 * Motion Lab fitness kit - film layout, exercise cards and stations (src/studio/kits/fitness/stations.js).
 * Needs the studio runtime (with studio-film.js), brand.js, sculpt.js, exercises.js; graphics.js and library.js
 * are used when loaded (evidence-grade colours, exercise and muscle names). The 3D station path needs
 * tibi3d.js, anatomy3d.js and exercises3d.js on the page as well.
 *
 * Lessons from the upper-body-workout film (2026-11-09), folded into the runtime on 2026-11-24:
 *   F.layout()                       the fitness bands per format: portrait header to the rail at y 340, Tibi the hero
 *                                    below it (about 40 % of the frame), floor at y 870, the caption lane under the
 *                                    floor (882-980 of 1280); landscape and square put the card column left of the
 *                                    stage. Every rect is {x, y, w, h, left, top, right, bottom} in px.
 *   F.place(el, rect)                position an element absolutely on a rect.
 *   F.captionLane(captions)          keep Studio.comp.captions inside the caption lane: never over Tibi or the card.
 *   F.audit()                        what is wrong on screen right now: card text off its band or on the rail,
 *                                    a caption over the hero (used by tests/test-studio-runtime.py on the template).
 *   F.cardData(id, extra)            card data from the exercise library (name, prime and secondary muscles) plus extra.
 *   F.exerciseCard(parent, data)     the per-exercise card: number, name, muscle chips, cues, tip with evidence grade
 *                                    and source line, swaps. Parts reveal progressively (snap them to spoken words).
 *   F.stations(host, list, options)  the per-station Tibi pattern: one station per exercise (its own Tibi, reps that
 *                                    fill the window, activation, its card), cross-faded into the next.
 */
(function (global) {
  'use strict';

  var Studio = global.Studio || (global.Studio = {});
  var F = (Studio.kit = Studio.kit || {}).fitness = (Studio.kit.fitness || {});
  if (!Studio.comp || !Studio.comp.stations) throw new Error('kits/fitness/stations.js needs studio-film.js loaded first');
  if (!F.sculpt || !F.exercise) throw new Error('kits/fitness/stations.js needs sculpt.js and exercises.js loaded first');
  var P = F.palette || {};
  var STAND_HEIGHT = 422;          // sculpt scale 1: sole to crown, rig units
  var LIE_LENGTH = 560;            // a prone or supine Tibi at scale 1, head to heel (approximate, with equipment)

  function own(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
  function rect(x0, y0, x1, y1) {
    return { x: x0, y: y0, w: x1 - x0, h: y1 - y0, left: x0, top: y0, right: x1, bottom: y1, cx: (x0 + x1) / 2, cy: (y0 + y1) / 2 };
  }

  /**
   * The fitness bands for the current format, every rect {x, y, w, h, left, top, right, bottom, cx, cy} in px.
   * Portrait (slot mode): header (title, card) from the safe top to the rail at 26.6 % (y 340 of 1280); stage below
   * the rail with Tibi as the hero (figureHeight: 92 % of rail to floor, about 40 % of the frame); floor line at 68 %
   * (y 870); the caption lane from just under the floor to the safe bottom (y 882-980), so a caption never covers
   * Tibi. Landscape and square (stack mode): a card column left (to 42 % / 46 % of the width) that ends above the
   * floor line, the stage right, the caption lane under the floor across the frame; the rail runs only behind the stage.
   * rail {x, y}: where the gym's chair rail goes (G.env.gym railX / railY), never through card text.
   * options: stageTop, floorAt (portrait fractions), split, stageBottom (landscape and square fractions).
   */
  F.layout = function (options) {
    var o = options || {};
    var f = Studio.format, W = f.width, H = f.height, s = f.safe;
    var capBottom = H - s.bottom, gap = Studio.u(1.6);
    var out;
    if (f.isPortrait) {
      var hb = (o.stageTop || 0.266) * H, fl = (o.floorAt || 0.68) * H;
      out = {
        format: f.id, mode: 'slot',
        header: rect(s.left, s.top, W - s.right, hb - Studio.u(1.6)),
        stage: rect(0, hb, W, fl + gap),
        captions: rect(s.left, fl + gap, W - s.right, capBottom),
        floor: fl,
        rail: { x: 0, y: hb },
        figureHeight: (fl - hb) * 0.92
      };
    } else {
      var split = (o.split || Studio.pick({ landscape: 0.42, square: 0.46 })) * W;
      var stageBottom = (o.stageBottom || Studio.pick({ landscape: 0.84, square: 0.80 })) * H;
      var floor = s.top + (stageBottom - s.top) * 0.93;
      var stage = rect(split, s.top, W - s.right, stageBottom);
      out = {
        format: f.id, mode: 'stack',
        // the card column ends above the floor line: the gym floor is dark, the card's ink is not
        header: rect(s.left, s.top, split - Studio.u(2), floor - Studio.u(2)),
        stage: stage,
        captions: rect(s.left, floor + gap, W - s.right, capBottom),
        floor: floor,
        rail: { x: split, y: floor - H * 0.3 },
        figureHeight: stage.h * 0.80
      };
    }
    out.captionBand = { top: +(out.captions.top / H).toFixed(4), bottom: +(out.captions.bottom / H).toFixed(4) };
    return out;
  };

  /** Position an element absolutely on a layout rect (px); returns the element. */
  F.place = function (el, r) {
    el.style.position = 'absolute';
    el.style.left = r.x.toFixed(1) + 'px';
    el.style.top = r.y.toFixed(1) + 'px';
    el.style.width = r.w.toFixed(1) + 'px';
    el.style.height = r.h.toFixed(1) + 'px';
    return el;
  };

  // ------------------------------------------------------------------ exercise card
  var GRADE_FALLBACK = {
    established: { label: 'Established mechanism', color: '#12A36E' },
    strong: { label: 'Strong evidence', color: '#12A36E' },
    moderate: { label: 'Moderate evidence', color: '#2F56E0' },
    preliminary: { label: 'Preliminary', color: '#D98A00' },
    hypothesis: { label: 'Hypothesis', color: '#7A5AE0' },
    unsupported: { label: 'Not supported', color: '#C2381F' }
  };
  function grade(id) {
    var g = (F.graphics && F.graphics.grades) || GRADE_FALLBACK;
    return g[id] || g.moderate || GRADE_FALLBACK.moderate;
  }
  function muscleName(id) {
    var m = F.library && F.library.muscles && F.library.muscles[id];
    return m && m.name ? m.name : id.replace(/-/g, ' ').replace(/^./, function (c) { return c.toUpperCase(); });
  }

  /**
   * Card data for a library exercise: {id, name, muscles: [{name, role}]}, merged with extra (extra wins). The chips
   * are the prime movers first, then secondary muscles, at most extra.maxMuscles (4): more chips wrap into rows that
   * push the cues out of a portrait header band.
   */
  F.cardData = function (id, extra) {
    var rec = F.library && F.library.exercises && F.library.exercises[id];
    var out = { id: id, name: rec && rec.name ? rec.name : id };
    var cap = extra && extra.maxMuscles !== undefined ? extra.maxMuscles : 4;
    if (rec && rec.muscles) {
      out.muscles = (rec.muscles.primary || []).map(function (m) { return { name: muscleName(m), role: 'prime' }; })
        .concat((rec.muscles.secondary || []).map(function (m) { return { name: muscleName(m), role: 'second' }; })).slice(0, cap);
    }
    var e = extra || {};
    for (var k in e) if (own(e, k) && k !== 'maxMuscles') out[k] = e[k];
    return out;
  };

  // Reading text on the card (chips, cues, tip, swaps) scales with the card's own --u but never below the reading floor:
  // 2.6 % of the frame's short side, the HyperFrames text_below_floor limit that frame-review.py checks. Each card
  // carries it as --sn-read-floor in px, so the card's own --u cannot drag it down; a card that must shrink to fit
  // shrinks its head and gaps and then its chip count instead (fitCard). Grade, source and swap keys stay at --fs-floor.
  var READ_FLOOR = 2.6;
  function floored(n) { return 'max(var(--sn-read-floor),calc(var(--u)*' + n + '))'; }
  var CARD_CSS = [
    '.sn-card{position:absolute;inset:0;display:flex;flex-direction:column;gap:calc(var(--u)*1.3);font-family:\'Inter\',sans-serif;color:var(--c-ink,#1b1d29)}',
    '.sn-card-head{display:flex;align-items:baseline;gap:calc(var(--u)*1.4);flex-wrap:wrap}',
    '.sn-card-mask{display:inline-block;overflow:hidden;line-height:1}',
    '.sn-card-num{display:inline-block;font-family:\'JetBrains Mono\',monospace;font-weight:700;font-size:calc(var(--u)*6.2);color:var(--c-accent,#2f56e0)}',
    '.sn-card-of{font-family:\'JetBrains Mono\',monospace;font-weight:600;font-size:var(--fs-kicker);color:var(--c-ink-2,#4a4e60)}',
    '.sn-card-name{flex-basis:100%;margin:0;font-family:\'Outfit\',sans-serif;font-weight:800;font-size:calc(var(--u)*6.4);line-height:1.02;letter-spacing:-0.02em;text-wrap:balance}',
    '.sn-card[data-mode="slot"] .sn-card-name{flex-basis:auto;font-size:calc(var(--u)*5.8)}',
    '.sn-card-muscles{display:flex;flex-wrap:wrap;gap:calc(var(--u)*0.7);list-style:none;margin:0;padding:0}',
    '.sn-chip{font-weight:700;font-size:' + floored(3.2) + ';line-height:1.2;padding:0.22em 0.7em;border-radius:999px;background:var(--c-muscle,#f2553d);color:#fff}',
    '.sn-chip[data-role="second"]{background:var(--c-spark,#ffb224);color:var(--c-ink,#1b1d29)}',
    '.sn-card-slot{position:relative;flex:1 1 auto;min-height:0}',
    '.sn-card-slot>*{position:absolute;left:0;right:0;top:0}',
    '.sn-card-cues{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:calc(var(--u)*0.8)}',
    '.sn-cue{display:flex;gap:0.6em;font-weight:600;font-size:' + floored(3.5) + ';line-height:1.25;text-wrap:balance}',
    '.sn-cue-n{font-family:\'JetBrains Mono\',monospace;font-weight:700;color:var(--c-accent,#2f56e0)}',
    '.sn-card-tip{display:flex;flex-direction:column;gap:calc(var(--u)*0.6);padding-left:calc(var(--u)*1.4);border-left:calc(var(--u)*0.6) solid var(--grade-c,#2f56e0)}',
    '.sn-tip-grade{display:flex;align-items:center;gap:0.5em;font-family:\'JetBrains Mono\',monospace;font-weight:700;font-size:var(--fs-floor);letter-spacing:0.06em;text-transform:uppercase;color:var(--c-ink,#1b1d29)}',
    '.sn-tip-grade::before{content:"";flex:none;width:0.62em;height:0.62em;border-radius:50%;background:var(--grade-c,#2f56e0)}',
    '.sn-tip-text{font-weight:600;font-size:' + floored(3.5) + ';line-height:1.25;text-wrap:balance}',
    '.sn-tip-src{font-family:\'JetBrains Mono\',monospace;font-weight:500;font-size:var(--fs-floor);color:var(--c-ink-2,#4a4e60);text-wrap:balance}',
    '.sn-card-swaps{display:flex;flex-direction:column;gap:calc(var(--u)*0.5);font-weight:600;font-size:' + floored(3.4) + ';line-height:1.25}',
    '.sn-swap-k{font-family:\'JetBrains Mono\',monospace;font-weight:700;font-size:var(--fs-floor);letter-spacing:0.08em;text-transform:uppercase;color:var(--c-accent,#2f56e0)}',
    '.sn-station-art{position:absolute;left:0;top:0;overflow:visible}',
    '.sn-station-3d{position:absolute;left:0;top:0}'
  ].join('\n');
  function ensureCss() {
    if (document.getElementById('sinew-stations-css')) return;
    var st = document.createElement('style');
    st.id = 'sinew-stations-css';
    st.textContent = CARD_CSS;
    document.head.appendChild(st);
  }
  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  /**
   * Shrink a card that would overflow its host: the tallest moment (head, chips and the tallest part that takes the
   * slot) must fit the host's height, or a tip runs into the stage band. Scales the card's own --u (number, name,
   * gaps); reading text (chips, cues, tip, swaps) follows it only down to the reading floor (READ_FLOOR), and the
   * --fs-floor lines (grade, source, swap keys) stay at --fs-floor. If the card is still too tall at {min} (0.72), it drops muscle chips from the end
   * (secondary muscles come last) down to {minChips} (3), and below that only secondary ones (a prime mover always
   * keeps its chip), fitting again after each drop.
   * Measured once at build time (fonts are ready inside Studio.build), before any tween moves a part.
   */
  function fitCard(el, opt) {
    if (opt === false || !el.isConnected) return 1;
    // a part rises into place from 1.6 u below (rise()), so the card keeps that much room under its last line
    var avail = el.clientHeight - Studio.u(1.6);
    if (!(avail > 0)) return 1;
    var o = opt || {}, unit = Studio.format.unit, min = o.min || 0.72, k = 1;
    var minChips = o.minChips !== undefined ? o.minChips : 3, dropped = [];
    function need() {
      var top = el.getBoundingClientRect().top, bottom = top;
      // leaves only: the slot is a flex box grown to the card's full height, so measuring it made every card "overflow"
      Array.prototype.forEach.call(el.querySelectorAll('*'), function (c) { if (!c.children.length) bottom = Math.max(bottom, c.getBoundingClientRect().bottom); });
      var scale = el.getBoundingClientRect().height > 0 ? el.clientHeight / el.getBoundingClientRect().height : 1;
      return (bottom - top) * scale;
    }
    function fit() {
      k = 1;
      el.style.removeProperty('--u');
      // parts held at the floor do not shrink with k, so the step can undershoot: iterate
      for (var i = 0; i < 8; i++) {
        var h = need();
        if (h <= avail + 0.5 || k <= min) break;
        k = Math.max(min, k * avail / h);
        el.style.setProperty('--u', (unit * k).toFixed(3) + 'px');
      }
    }
    fit();
    var chips = Array.prototype.slice.call(el.querySelectorAll('.sn-chip'));
    // beyond minChips only secondary muscles go: a prime mover always keeps its chip
    while (need() > avail + 0.5 && chips.length &&
           (chips.length > minChips || chips[chips.length - 1].getAttribute('data-role') === 'second')) {
      var c = chips.pop();
      c.style.display = 'none';
      c.setAttribute('data-dropped', '');
      dropped.unshift(c.textContent);
      fit();
    }
    el.setAttribute('data-fit', k.toFixed(3));
    var label = '"' + (el.querySelector('.sn-card-name') || {}).textContent + '"';
    if (dropped.length) {
      el.setAttribute('data-dropped-chips', dropped.join('|'));
      if (global.console) global.console.warn('[sinew] exercise card ' + label + ' dropped chip(s) ' + dropped.join(', ') + ' to keep its text at the legibility floor; pass fewer muscles (cardData maxMuscles) to choose which');
    }
    if (need() > avail + 0.5 && global.console) global.console.warn('[sinew] exercise card ' + label + ' is taller than its band even at ' + Math.round(k * 100) + '%; shorten the tip or source line, or drop a chip');
    return k;
  }
  function rise(tl, els, at, stagger) {
    tl.fromTo(els, { autoAlpha: 0, y: Studio.u(1.6) }, { autoAlpha: 1, y: 0, duration: 0.45, ease: 'power3.out', stagger: stagger || 0, immediateRender: true }, at);
    return at + 0.45 + (stagger || 0) * Math.max(0, [].concat(els).length - 1);
  }
  function fadeOut(tl, els, at) {
    tl.fromTo(els, { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.25, ease: 'power1.in', immediateRender: false }, at);
    return at + 0.25;
  }

  /**
   * The per-exercise card. data: {index, total, name, muscles: [{name, role: 'prime' | 'second'}], cues: [text],
   * tip: {text, grade (established | strong | moderate | preliminary | hypothesis | unsupported), source},
   * swaps: {easier, harder} | [text] | text}. options: {mode: 'slot' (cues, tip and swaps take turns in one slot:
   * portrait) | 'stack' (cues stack, tip and swaps take turns: landscape, square); default from the format,
   * fit (default on: a card taller than its host shrinks its own --u, never below {min: 0.72}, keeps reading text at
   * the reading floor and then drops trailing muscle chips: down to {minChips: 3}, then secondary ones only; false: keep the size)}.
   * enter(tl, at) brings in the number and the name; reveal(tl, part, at) shows 'muscles', 'cues' (all), 'cue:<k>'
   * (one cue; earlier ones dim), 'tip' or 'swaps'; show(tl, beats) reveals each part at its beat ({muscles: t,
   * cues: [t, ...] | t, tip: t, swaps: t}, e.g. word-snapped cue times); call reveal in time order. The tip always
   * carries its grade and source line (the fitness research protocol: no claim without them).
   * Returns {el, parts, enter, reveal, show, exit}.
   */
  F.exerciseCard = function (parent, data, options) {
    ensureCss();
    var o = options || {};
    var mode = o.mode || Studio.pick({ portrait: 'slot', landscape: 'stack', square: 'stack' });
    var host = typeof parent === 'string' ? document.querySelector(parent) : parent;
    var el = Studio.el('div', 'sn-card' + (o.className ? ' ' + o.className : ''), null, host);
    el.setAttribute('data-mode', mode);
    el.style.setProperty('--sn-read-floor', Studio.u(READ_FLOOR).toFixed(2) + 'px');
    var head = Studio.el('div', 'sn-card-head', null, el);
    var numMask = Studio.el('span', 'sn-card-mask', null, head);
    var num = Studio.el('span', 'sn-card-num', pad2(data.index || 1), numMask);
    var of = data.total ? Studio.el('span', 'sn-card-of', '/ ' + pad2(data.total), head) : null;
    var name = Studio.el('h2', 'sn-card-name', data.name || '', head);
    var muscles = null, chips = [];
    if (data.muscles && data.muscles.length) {
      muscles = Studio.el('ul', 'sn-card-muscles', null, el);
      chips = data.muscles.map(function (m) {
        var li = Studio.el('li', 'sn-chip', m.name, muscles);
        li.setAttribute('data-role', m.role === 'second' || m.role === 2 ? 'second' : 'prime');
        return li;
      });
    }
    var slot = Studio.el('div', 'sn-card-slot', null, el);
    var cueList = null, cues = [];
    if (data.cues && data.cues.length) {
      cueList = Studio.el('ol', 'sn-card-cues', null, mode === 'slot' ? slot : el);
      if (mode !== 'slot') el.insertBefore(cueList, slot);
      cues = data.cues.map(function (c, k) {
        var li = Studio.el('li', 'sn-cue', null, cueList);
        Studio.el('span', 'sn-cue-n', String(k + 1), li);
        Studio.el('span', 'sn-cue-text', c, li);
        return li;
      });
    }
    var tip = null;
    if (data.tip) {
      var gr = grade(data.tip.grade);
      tip = Studio.el('div', 'sn-card-tip', null, slot);
      tip.style.setProperty('--grade-c', gr.color);
      Studio.el('span', 'sn-tip-grade', gr.label, tip);
      Studio.el('span', 'sn-tip-text', data.tip.text || '', tip);
      if (!data.tip.source) throw new Error('Sinew exercise card: a tip needs its source line (fitness research protocol)');
      Studio.el('span', 'sn-tip-src', data.tip.source, tip);
    }
    var swaps = null;
    if (data.swaps) {
      swaps = Studio.el('div', 'sn-card-swaps', null, slot);
      var sw = data.swaps;
      var rows = typeof sw === 'string' ? [['Swap', sw]] : Array.isArray(sw) ? sw.map(function (t) { return ['Swap', t]; })
        : [['Easier', sw.easier], ['Harder', sw.harder]].filter(function (r) { return r[1]; });
      rows.forEach(function (r) {
        var line = Studio.el('div', 'sn-swap', null, swaps);
        Studio.el('span', 'sn-swap-k', r[0] + ' ', line);
        Studio.el('span', 'sn-swap-v', r[1], line);
      });
    }
    var hidden = [numMask, of, name, muscles, cueList, tip, swaps].filter(Boolean).concat(chips, cues);
    fitCard(el, o.fit);
    chips = chips.filter(function (c) { return !c.hasAttribute('data-dropped'); });
    global.gsap.set(hidden, { autoAlpha: 0 });
    var slotOwner = null, litCue = -1, seen = [];
    // Bring a part's box on screen at `at` unless it is already showing; in slot mode it first takes the slot from
    // the part showing there. A box seen before was faded out by a tween, so its return must not render early.
    function showBox(tl, box, at) {
      if (mode === 'slot' || box !== cueList) {
        if (slotOwner === box) return;
        if (slotOwner && slotOwner.parentNode === slot) fadeOut(tl, slotOwner, Math.max(0, at - 0.25));
        if (box.parentNode === slot) slotOwner = box;
      } else if (seen.indexOf(box) >= 0) return;
      var again = seen.indexOf(box) >= 0;
      tl.fromTo(box, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.001, ease: 'none', immediateRender: !again }, at);
      if (!again) seen.push(box);
    }
    var api = {
      el: el, mode: mode, parts: { num: num, name: name, muscles: muscles, chips: chips, cues: cues, cueList: cueList, tip: tip, swaps: swaps },
      enter: function (tl, at) {
        tl.fromTo(numMask, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.001, ease: 'none', immediateRender: true }, at);
        tl.fromTo(num, { yPercent: 105 }, { yPercent: 0, duration: 0.6, ease: 'power4.out', immediateRender: true }, at);
        if (of) tl.fromTo(of, { autoAlpha: 0, x: -Studio.u(1) }, { autoAlpha: 1, x: 0, duration: 0.4, ease: 'power2.out', immediateRender: true }, at + 0.2);
        return rise(tl, name, at + 0.12);
      },
      reveal: function (tl, part, at) {
        if (part === 'muscles') {
          if (!muscles) return at;
          tl.fromTo(muscles, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.001, ease: 'none', immediateRender: true }, at);
          Studio.space.pop(tl, chips, at, { stagger: 0.08, tilt: 0 });
          return at + 0.45 + 0.08 * (chips.length - 1);
        }
        if (part === 'cues' || /^cue:\d+$/.test(part)) {
          if (!cueList) return at;
          showBox(tl, cueList, at);
          if (part === 'cues') { litCue = cues.length - 1; return rise(tl, cues, at, 0.15); }
          var k = +part.split(':')[1];
          if (k < 0 || k >= cues.length) throw new Error('Sinew exercise card: no cue ' + k);
          if (k <= litCue) return at;
          // only the cue that was lit dims; the ones before it already have
          if (litCue >= 0) tl.fromTo(cues[litCue], { opacity: 1 }, { opacity: 0.5, duration: 0.3, ease: 'power1.out', immediateRender: false }, at);
          litCue = k;
          return rise(tl, cues[k], at);
        }
        if (part === 'tip' || part === 'swaps') {
          var box = part === 'tip' ? tip : swaps;
          if (!box) return at;
          var first = seen.indexOf(box) < 0;
          showBox(tl, box, at);
          return first ? rise(tl, Array.prototype.slice.call(box.children), at, 0.1) : at + 0.05;
        }
        throw new Error('Sinew exercise card: unknown part "' + part + '"');
      },
      show: function (tl, beats) {
        var b = beats || {}, end = 0;
        var steps = [];
        if (b.muscles !== undefined) steps.push(['muscles', b.muscles]);
        if (b.cues !== undefined) {
          if (Array.isArray(b.cues)) b.cues.forEach(function (t, k) { steps.push(['cue:' + k, t]); });
          else steps.push(['cues', b.cues]);
        }
        if (b.tip !== undefined) steps.push(['tip', b.tip]);
        if (b.swaps !== undefined) steps.push(['swaps', b.swaps]);
        steps.sort(function (x, y) { return x[1] - y[1]; }).forEach(function (s) { end = Math.max(end, api.reveal(tl, s[0], s[1])); });
        return end;
      },
      exit: function (tl, at) {
        tl.fromTo(el, { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.3, ease: 'power1.in', immediateRender: false }, at);
        return at + 0.3;
      }
    };
    return api;
  };

  /** Evenly spaced beats inside a station window (used when a station gives no word-snapped beats). */
  F.cardBeats = function (win, data) {
    var parts = [];
    if (data.muscles && data.muscles.length) parts.push('muscles');
    (data.cues || []).forEach(function (c, k) { parts.push('cue:' + k); });
    if (data.tip) parts.push('tip');
    if (data.swaps) parts.push('swaps');
    // the last part still gets about two seconds on screen (reading time for a five-word line)
    var a = win.in + 0.9, b = Math.max(a, win.out - 2.2), step = parts.length > 1 ? (b - a) / (parts.length - 1) : 0;
    var beats = { cues: [] };
    parts.forEach(function (p, i) {
      var t = a + i * step;
      if (p.indexOf('cue:') === 0) beats.cues.push(t); else beats[p] = t;
    });
    if (!beats.cues.length) delete beats.cues;
    return beats;
  };

  /**
   * Keep the runtime captions (Studio.comp.captions, or its .el) inside the layout's caption lane: every cue except a
   * storyboard 'upper' one moves to the lane (the preset's portrait hook lane 'mid' would sit on Tibi), is as wide as
   * the lane, sits on the lane's bottom edge and shrinks (never below --fs-floor) until its plate fits the lane's
   * height, so a three-line cue still clears the hero. Measured once at build time.
   * options: {layout, all (true: move 'upper' cues too)}. Returns the cues that do not fit even at the floor size.
   */
  F.captionLane = function (captions, options) {
    var o = options || {};
    var L = o.layout || F.layout(), lane = L.captions, H = Studio.format.height;
    var band = captions && captions.el ? captions.el : captions;
    if (!band) return [];
    var probe = Studio.el('span', null, 'x', band);
    probe.style.cssText = 'position:absolute;visibility:hidden;font-size:var(--fs-floor)';
    var floorPx = parseFloat(global.getComputedStyle(probe).fontSize) || Studio.u(3.1);
    band.removeChild(probe);
    var over = [];
    Array.prototype.forEach.call(band.querySelectorAll('.st-caption'), function (p) {
      if (p.getAttribute('data-lane') === 'upper' && !o.all) return;
      p.setAttribute('data-lane', 'lower');
      p.setAttribute('data-station-lane', '');
      p.style.top = 'auto';
      p.style.bottom = (H - lane.bottom).toFixed(1) + 'px';
      p.style.maxWidth = lane.w.toFixed(1) + 'px';
      var fs = parseFloat(global.getComputedStyle(p).fontSize);
      for (var i = 0; i < 12 && p.offsetHeight > lane.h + 0.5 && fs > floorPx; i++) {
        fs = Math.max(floorPx, fs * Math.min(0.94, lane.h / p.offsetHeight));
        p.style.fontSize = fs.toFixed(2) + 'px';
      }
      if (p.offsetHeight > lane.h + 0.5) {
        over.push(p.textContent);
        if (global.console) global.console.warn('[sinew] caption "' + p.textContent + '" is taller than the caption lane even at the floor size; split the cue');
      }
    });
    return over;
  };

  /**
   * What is wrong on screen at the current playhead, in frame px: visible exercise-card text outside the header band,
   * crossing the gym rail (.env-gym-rail) or set below the reading floor (2.6 % of the short side), and a visible caption intersecting the visible 2D
   * Tibi (the union of the station art's shapes). Returns [{kind, text, box, against | size + floor}]; empty when the
   * frame is clean.
   */
  F.audit = function (options) {
    var o = options || {};
    var L = o.layout || F.layout();
    var root = document.getElementById('root') || document.body;
    var R = root.getBoundingClientRect(), k = R.width > 0 ? root.offsetWidth / R.width : 1;
    function box(el) {
      var r = el.getBoundingClientRect();
      return { l: (r.left - R.left) * k, t: (r.top - R.top) * k, r: (r.right - R.left) * k, b: (r.bottom - R.top) * k };
    }
    function shown(el) {
      var a = 1;
      for (var e = el; e && e !== root.parentNode; e = e.parentNode) {
        if (e.nodeType !== 1) continue;
        var cs = global.getComputedStyle(e);
        if (cs.visibility === 'hidden' || cs.display === 'none') return false;
        a *= parseFloat(cs.opacity);
      }
      return a > 0.05;
    }
    function hit(a, b, pad) { var m = pad || 0; return a.l < b.r - m && a.r > b.l + m && a.t < b.b - m && a.b > b.t + m; }
    function round(b) { return [Math.round(b.l), Math.round(b.t), Math.round(b.r), Math.round(b.b)]; }
    var out = [];
    var railEls = document.querySelectorAll('.env-gym-rail');
    if (!railEls.length) railEls = document.querySelectorAll('.env-gym > rect[height="6"]');   // a gym drawn before the class existed
    var rails = Array.prototype.map.call(railEls, box);
    var hb = { l: L.header.left - 1, t: L.header.top - 1, r: L.header.right + 1, b: L.header.bottom + 1 };
    // the reading floor in frame px (layout px are frame px): no card text may render smaller
    var floorPx = Studio.u(READ_FLOOR);
    Array.prototype.forEach.call(document.querySelectorAll('.sn-card *'), function (el) {
      if (el.children.length || !el.textContent.trim() || !shown(el)) return;
      var b = box(el);
      // what a clipping ancestor (the number's rise mask) hides is not on screen
      for (var e = el.parentNode; e && e !== root; e = e.parentNode) {
        if (e.nodeType === 1 && global.getComputedStyle(e).overflow !== 'visible') {
          var c = box(e);
          b = { l: Math.max(b.l, c.l), t: Math.max(b.t, c.t), r: Math.min(b.r, c.r), b: Math.min(b.b, c.b) };
        }
      }
      if (b.b - b.t < 1 || b.r - b.l < 1) return;
      // vertical only: a chip's pop overshoots sideways for a few frames, but nothing may run above or below the band
      if (b.t < hb.t || b.b > hb.b) out.push({ kind: 'card-off-band', text: el.textContent, box: round(b), against: round(hb) });
      rails.forEach(function (rb) { if (hit(b, rb)) out.push({ kind: 'card-on-rail', text: el.textContent, box: round(b), against: round(rb) }); });
      var fs = parseFloat(global.getComputedStyle(el).fontSize);
      if (floorPx > 0 && fs < floorPx - 0.25) out.push({ kind: 'card-below-floor', text: el.textContent, box: round(b), size: +fs.toFixed(1), floor: +floorPx.toFixed(1) });
    });
    var heroes = [];
    var SHAPES = { path: 1, ellipse: 1, circle: 1, rect: 1, polygon: 1, polyline: 1, line: 1, use: 1, image: 1 };
    // the union of the shapes actually drawn: a group's own box also counts hidden alternatives (arm blends, props)
    function drawn(node, alpha, acc) {
      Array.prototype.forEach.call(node.children, function (c) {
        if (c.classList && c.classList.contains('tibi-shadow')) return;      // the floor shadow is not the body
        var cs = global.getComputedStyle(c);
        if (cs.display === 'none' || cs.visibility === 'hidden') return;
        var a = alpha * parseFloat(cs.opacity);     // an SVG opacity attribute is already in the computed style
        if (a <= 0.05) return;
        var tag = c.tagName.toLowerCase();
        if (tag === 'defs' || tag === 'clippath' || tag === 'mask' || tag === 'lineargradient' || tag === 'radialgradient') return;
        if (SHAPES[tag]) {
          var b = box(c);
          if (b.r - b.l >= 0.5 || b.b - b.t >= 0.5) acc.u = acc.u ? { l: Math.min(acc.u.l, b.l), t: Math.min(acc.u.t, b.t), r: Math.max(acc.u.r, b.r), b: Math.max(acc.u.b, b.b) } : b;
        } else drawn(c, a, acc);
      });
      return acc;
    }
    Array.prototype.forEach.call(document.querySelectorAll('svg.sn-station-art'), function (svgEl) {
      if (!shown(svgEl)) return;
      var u = drawn(svgEl, 1, {}).u;
      if (u) heroes.push(u);
    });
    Array.prototype.forEach.call(document.querySelectorAll('.st-caption'), function (p) {
      if (!shown(p)) return;
      var b = box(p);
      heroes.forEach(function (hbx) { if (hit(b, hbx, 1)) out.push({ kind: 'caption-on-hero', text: p.textContent, box: round(b), against: round(hbx) }); });
    });
    return out;
  };

  function autoScale(view, L) {
    var lying = view === 'top' || view === 'above', stage = L.stage;
    var byHeight = (L.figureHeight || stage.h * 0.80) / STAND_HEIGHT;
    return lying ? Math.min(byHeight * 1.2, stage.w * 0.78 / LIE_LENGTH) : Math.min(byHeight, stage.w * 0.9 / (STAND_HEIGHT * 0.75));
  }

  /**
   * One station per exercise, cross-faded. host: a full-frame element (a div over the background), or [artHost,
   * cardHost] to keep the cards out of a drifting camera layer (each station gets a layer in both). list:
   * [{exercise (2D id), start, end, gender, view, x, floor, scale, reps (default: fill the window), tempo, pause,
   *   lead (0.35 s; 0 for a station that opens the film, so Tibi moves on frame 0), acts (activation override),
   *   card: data | false (default: F.cardData(exercise) with index and total), cardAt (when the card enters;
   *   default just after the station starts, later when a hook title holds the header first), beats: {...} | 'auto',
   *   mode: '3d' with exercise3d (a T3 exercise id), shot, period (a 3D station: fitted camera, see below),
   *   build(ctx, tl) (extra tweens; ctx = {layer, cardLayer, svg, tibi, ex, card, win, layout})}].
   * options: {layout (F.layout()), fade (0.5), gender ('male'), hold (true)}.
   * A 3D station frames its set with T3.scene(stage, id, {fit: {rect: layout.stage}}): the camera is solved from the
   * posed body and equipment over the whole set (runtime 1.13.0), so the figure stays inside the stage band.
   * Returns {stations (the Studio.comp.stations handle), items (per station ctx), schedule(tl) -> end}.
   */
  F.stations = function (host, list, options) {
    var o = options || {};
    var L = o.layout || F.layout();
    var f = Studio.format;
    function resolveHost(h) { return typeof h === 'string' ? document.querySelector(h) : h; }
    var items = [];
    var seq = Studio.comp.stations(Array.isArray(host) ? host.map(resolveHost) : resolveHost(host), list.map(function (st, i) {
      return {
        id: st.id || st.exercise || st.exercise3d || 'station-' + (i + 1), start: st.start, end: st.end,
        build: function (layers, win, tl) {
          var layer = layers[0], cardLayer = layers[1] || layers[0];
          var ctx = { layer: layer, cardLayer: cardLayer, win: win, layout: L, index: i };
          var lead = st.lead === undefined ? (st.start <= 0 ? 0 : 0.35) : st.lead;
          var t0 = st.start + lead;
          if (st.mode === '3d') build3d(st, ctx, tl, t0);
          else build2d(st, ctx, tl, t0);
          if (st.card !== false) {
            var base = st.exercise ? F.cardData(st.exercise) : { name: st.exercise3d };
            var data = st.card && typeof st.card === 'object' ? merge(base, st.card) : base;
            if (data.index === undefined) data.index = i + 1;
            if (data.total === undefined) data.total = list.length;
            var cardHost = F.place(Studio.el('div', 'sn-card-host', null, cardLayer), L.header);
            ctx.card = F.exerciseCard(cardHost, data, { mode: st.cardMode || L.mode });
            var cardAt = Math.max(0, st.cardAt === undefined ? st.start + 0.05 : st.cardAt);
            ctx.card.enter(tl, cardAt);
            var cw = { in: Math.max(win.in, cardAt), out: win.out };
            ctx.card.show(tl, st.beats && st.beats !== 'auto' ? st.beats : F.cardBeats(cw, data));
          }
          if (st.build) st.build(ctx, tl);
          items[i] = ctx;
        }
      };
    }), { fade: o.fade, hold: o.hold });
    function merge(a, b) { var out = {}, k; for (k in a) if (own(a, k)) out[k] = a[k]; for (k in b) if (own(b, k)) out[k] = b[k]; return out; }
    function build2d(st, ctx, tl, t0) {
      var rec = F.exercises[st.exercise];
      if (!rec) throw new Error('Sinew stations: unknown 2D exercise "' + st.exercise + '"');
      var view = st.view || rec.view, lying = view === 'top' || view === 'above';
      var svg = Studio.svg('svg', { 'class': 'sn-station-art', viewBox: '0 0 ' + f.width + ' ' + f.height, width: f.width, height: f.height, 'aria-hidden': 'true' }, ctx.layer);
      var scale = st.scale || autoScale(view, L);
      var tibi = F.sculpt(svg, {
        gender: st.gender || o.gender || 'male', view: view, x: st.x === undefined ? L.stage.cx : st.x,
        floor: st.floor === undefined ? L.floor : st.floor, y: lying ? (st.y === undefined ? L.stage.cy + L.stage.h * 0.12 : st.y) : undefined, scale: scale
      });
      var ex = F.exercise(tibi, st.exercise);
      var rep = ex.repDuration ? ex.repDuration({ tempo: st.tempo, pause: st.pause }) : 2;
      var n = st.reps || Math.max(1, Math.floor((st.end - t0 - 0.2) / rep));
      var end = ex.reps ? ex.reps(tl, t0, n, { tempo: st.tempo, pause: st.pause }) : ex.run(tl, t0, st.end - t0);
      var acts = st.acts === undefined ? ex.acts : st.acts;
      if (acts) tibi.activate(tl, acts, Math.max(0, st.start) + 0.25, 0.6);
      ctx.svg = svg; ctx.tibi = tibi; ctx.ex = ex; ctx.repsEnd = end;
    }
    function build3d(st, ctx, tl, t0) {
      var T3 = F.t3d;
      if (!T3 || !T3.scene) throw new Error('Sinew stations: a 3D station needs vendor/three.min.js, tibi3d.js, anatomy3d.js and exercises3d.js on the page');
      var div = Studio.el('div', 'sn-station-3d', null, ctx.layer);
      var stage3 = T3.stage(div, { width: f.width, height: f.height });
      var def = T3.exercises && T3.exercises[st.exercise3d];
      var per = st.period || (def && def.period) || 3.4;
      var reps = st.reps || Math.max(1, Math.floor((st.end - t0 - 0.2) / per));
      var r = L.stage;
      var sc = T3.scene(stage3, st.exercise3d, {
        gender: /^f/.test(st.gender || o.gender || 'm') ? 'f' : 'm', figId: 'st' + ctx.index, at: t0, reps: reps, period: per,
        shot: st.shot || null, fit: st.fit === false ? null : (st.fit || { rect: [r.left, r.top, r.right, r.bottom] })
      });
      var w0 = st.start - 0.5, w1 = st.end + 0.5;
      T3.bind(tl, stage3, sc.motion, f.duration, function (v, t) { sc.fig.setVisible(t >= w0 && t <= w1); });
      ctx.stage3 = stage3; ctx.scene3 = sc;
    }
    return {
      stations: seq, items: items, layout: L,
      schedule: function (tl) { return seq.schedule(tl); }
    };
  };
})(typeof window !== 'undefined' ? window : this);
