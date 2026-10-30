/*
 * Motion Lab studio runtime - compositions (src/studio/studio-compositions.js)
 * Layer 3 reusable units built from runtime primitives and effects. Each builder creates DOM in
 * `parent` and returns handles plus enter(tl, at) / exit(tl, at) that return their end time.
 * Layout adapts per format through CSS ([data-format] rules in studio-base.css).
 * Requires studio-core.js, studio-draw.js, studio-type.js and studio-motion.js.
 */
(function (global) {
  'use strict';

  var Studio = global.Studio;
  if (!Studio || !Studio.type || !Studio.fx) throw new Error('studio-compositions.js requires the other studio runtime files');
  var C = Studio.comp = {};
  var T = Studio.type;

  function setContent(el, text, html) {
    if (html) el.innerHTML = html;
    else el.textContent = text || '';
  }

  /**
   * Title card: kicker, display title (inline <em> allowed via titleHTML), optional lede and
   * hand-drawn underline under the first <em> (or the last line).
   */
  C.titleCard = function (parent, data, options) {
    var o = options || {};
    var el = Studio.el('div', 'st-title-card' + (o.className ? ' ' + o.className : ''), null, parent);
    var kicker = data.kicker ? Studio.el('div', 'st-kicker', data.kicker, el) : null;
    var title = Studio.el(o.tag || 'h1', 'st-display', null, el);
    setContent(title, data.title, data.titleHTML);
    var lede = data.subtitle ? Studio.el('p', 'st-lede', data.subtitle, el) : null;
    if (o.fit) T.fit(title, { min: Studio.u(o.fitMin || 5) });
    var split = T.split(title, { type: 'lines,words', mask: 'lines' });
    var ledeSplit = lede ? T.split(lede, { type: 'words' }) : null;
    return {
      el: el, kicker: kicker, title: title, lede: lede, split: split,
      enter: function (tl, at, eo) {
        var e = eo || {};
        var end = at;
        if (kicker) end = Math.max(end, T.track(tl, kicker, at, { from: '0.6em', to: '0.16em', duration: 1.0 }));
        end = Math.max(end, T.rise(tl, split.lines, at + 0.15, { stagger: 0.09 }));
        if (data.underline !== false) {
          var target = title.querySelector('.st-line em') || split.words[split.words.length - 1];
          end = Math.max(end, T.underline(tl, target, end - 0.25, { host: title, seed: e.seed || 11, duration: 0.55 }));
        }
        if (ledeSplit) {
          tl.fromTo(ledeSplit.words, { autoAlpha: 0, yPercent: 40 }, { autoAlpha: 1, yPercent: 0, duration: 0.5, ease: 'power2.out', stagger: 0.025 }, end - 0.3);
          end = end - 0.3 + 0.5 + 0.025 * (ledeSplit.words.length - 1);
        }
        return end;
      },
      exit: function (tl, at) {
        var end = T.exit(tl, split.lines, at, { stagger: 0.05 });
        var rest = [kicker, lede].filter(Boolean);
        if (rest.length) tl.fromTo(rest, { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.35, ease: 'power1.in', immediateRender: false }, at);
        var u = el.querySelector('.st-underline');
        if (u) tl.fromTo(u, { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.25, immediateRender: false }, at);
        return Math.max(end, at + 0.35);
      }
    };
  };

  /** Itemised list (ingredients, features, credits): quantity column, label, optional note. */
  C.itemList = function (parent, items, options) {
    var o = options || {};
    var list = Studio.el('ol', 'st-list' + (o.className ? ' ' + o.className : ''), null, parent);
    var cols = o.columns ? Studio.pick(o.columns) : 1;
    list.style.setProperty('--st-list-cols', String(cols));
    var rows = items.map(function (item) {
      var li = Studio.el('li', 'st-item', null, list);
      if (item.qty !== undefined) Studio.el('span', 'st-item-qty', item.qty, li);
      Studio.el('span', 'st-item-label', item.label, li);
      if (item.note) Studio.el('span', 'st-item-note', item.note, li);
      var rule = Studio.el('span', 'st-item-rule', null, li);
      rule.setAttribute('aria-hidden', 'true');
      return { li: li, rule: rule };
    });
    return {
      el: list, rows: rows,
      enter: function (tl, at, eo) {
        var e = eo || {};
        var stagger = e.stagger === undefined ? 0.12 : e.stagger;
        var lis = rows.map(function (r) { return r.li; });
        var rules = rows.map(function (r) { return r.rule; });
        tl.fromTo(lis, { autoAlpha: 0, y: Studio.u(2) }, { autoAlpha: 1, y: 0, duration: 0.55, ease: 'power3.out', stagger: stagger }, at);
        tl.fromTo(rules, { scaleX: 0, transformOrigin: '0% 50%' }, { scaleX: 1, duration: 0.6, ease: 'power2.inOut', stagger: stagger }, at + 0.1);
        return at + 0.7 + stagger * (rows.length - 1);
      },
      exit: function (tl, at) {
        var lis = rows.map(function (r) { return r.li; });
        tl.fromTo(lis, { autoAlpha: 1, y: 0 }, { autoAlpha: 0, y: -Studio.u(1.5), duration: 0.35, ease: 'power1.in', stagger: 0.04, immediateRender: false }, at);
        return at + 0.35 + 0.04 * (rows.length - 1);
      }
    };
  };

  /** Step header: large numeral with "of total", heading and body copy. No progress bar. */
  C.stepHeader = function (parent, data, options) {
    var o = options || {};
    var el = Studio.el('div', 'st-step' + (o.className ? ' ' + o.className : ''), null, parent);
    var idx = Studio.el('div', 'st-step-index', null, el);
    var pad = function (n) { return (n < 10 ? '0' : '') + n; };
    var numMask = Studio.el('span', 'st-mask-inline', null, idx);
    var num = Studio.el('span', 'st-step-num', pad(data.index), numMask);
    var of = data.total ? Studio.el('span', 'st-step-of', '/ ' + pad(data.total), idx) : null;
    var heading = Studio.el('h2', 'st-heading', null, el);
    setContent(heading, data.title, data.titleHTML);
    var body = data.body ? Studio.el('p', 'st-body', data.body, el) : null;
    var hs = T.split(heading, { type: 'lines,words', mask: 'lines' });
    var bs = body ? T.split(body, { type: 'lines,words', mask: 'lines' }) : null;
    return {
      el: el, num: num, heading: heading, body: body,
      enter: function (tl, at) {
        tl.fromTo(num, { yPercent: 105 }, { yPercent: 0, duration: 0.7, ease: 'power4.out' }, at);
        if (of) tl.fromTo(of, { autoAlpha: 0, x: -Studio.u(1) }, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'power2.out' }, at + 0.25);
        var end = T.rise(tl, hs.lines, at + 0.2, { stagger: 0.08 });
        if (bs) end = Math.max(end, T.rise(tl, bs.lines, end - 0.35, { stagger: 0.06, duration: 0.55 }));
        return end;
      },
      exit: function (tl, at) {
        tl.fromTo(num, { yPercent: 0 }, { yPercent: -105, duration: 0.4, ease: 'power2.in', immediateRender: false }, at);
        var parts = hs.lines.concat(bs ? bs.lines : []);
        var end = T.exit(tl, parts, at, { stagger: 0.03 });
        if (of) tl.fromTo(of, { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.3, immediateRender: false }, at);
        return end;
      }
    };
  };

  /** End card: optional line-art mark (SVG markup), title and supporting lines; holds to the end. */
  C.endCard = function (parent, data, options) {
    var o = options || {};
    var el = Studio.el('div', 'st-end-card' + (o.className ? ' ' + o.className : ''), null, parent);
    var mark = null;
    if (data.markSVG) {
      mark = Studio.el('div', 'st-end-mark', null, el);
      mark.innerHTML = data.markSVG;
    }
    var title = Studio.el('h2', 'st-display st-end-title', null, el);
    setContent(title, data.title, data.titleHTML);
    var lines = (data.lines || []).map(function (line) { return Studio.el('p', 'st-end-line', line, el); });
    var ts = T.split(title, { type: 'lines,words', mask: 'lines' });
    return {
      el: el, title: title, lines: lines,
      enter: function (tl, at) {
        var end = at;
        if (mark) end = Studio.draw.lineArt(tl, mark.querySelector('svg'), at, { speed: 500 });
        end = Math.max(end, T.rise(tl, ts.lines, at + (mark ? 0.35 : 0), { stagger: 0.09 }));
        if (lines.length) {
          tl.fromTo(lines, { autoAlpha: 0, y: Studio.u(1.2) }, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'power2.out', stagger: 0.12 }, end - 0.2);
          end = end - 0.2 + 0.5 + 0.12 * (lines.length - 1);
        }
        return end;
      }
    };
  };

  /**
   * Caption band in the bottom safe area. cues: [{start, end, text}] in seconds, non-overlapping.
   * The band carries data-layout-allow-caption-zone for HyperFrames' caption-zone gate.
   */
  C.captions = function (parent, cues, options) {
    var o = options || {};
    var band = Studio.el('div', 'st-captions' + (o.className ? ' ' + o.className : ''), null, parent);
    band.setAttribute('data-layout-allow-caption-zone', '');
    var els = cues.map(function (c) { return Studio.el('p', 'st-caption', c.text, band); });
    return {
      el: band,
      schedule: function (tl) {
        cues.forEach(function (c, i) {
          var fade = Math.min(0.12, (c.end - c.start) / 4);
          tl.fromTo(els[i], { autoAlpha: 0 }, { autoAlpha: 1, duration: fade, ease: 'none', immediateRender: false }, c.start);
          tl.fromTo(els[i], { autoAlpha: 1 }, { autoAlpha: 0, duration: fade, ease: 'none', immediateRender: false }, c.end - fade);
        });
        return cues.length ? cues[cues.length - 1].end : 0;
      }
    };
  };

  // ------------------------------------------------------------------ reference-derived compositions
  function beatTimes(count, beats) {
    if (Array.isArray(beats)) {
      if (beats.length < count + 1) throw new Error('Studio.comp.wordBeats: need one beat per word plus an end time');
      return beats;
    }
    var b = beats || {};
    var every = b.every || 1;
    var grid = Studio.rhythm.grid(b.bpm || 120, { offset: b.start || 0, count: count * every + 1 });
    var out = [];
    for (var i = 0; i <= count; i++) out.push(grid[i * every]);
    return out;
  }

  /**
   * Word beats: one word per beat on its own full-frame card, hard cuts on the beats, and a
   * treatment that performs the word: rise, smear, drop, stretch, spin, track, echo or cut.
   * words: [{text, treatment, bg, ink, accent (true adds an accent full stop), side (smear),
   * stretch (start scaleX for 'stretch', 2.6; keep it low enough that the word stays inside the frame)}].
   * options: {beats: [t0, t1, ..., tEnd] | {start, bpm, every}, holdLast (keep the last card)}.
   * Returns {cards, times, schedule(tl) -> end time}. Each card is a .st-wb-card (position absolute).
   */
  C.wordBeats = function (parent, words, options) {
    var o = options || {};
    var host = typeof parent === 'string' ? document.querySelector(parent) : parent;
    var times = beatTimes(words.length, o.beats);
    var cards = words.map(function (w) {
      var card = Studio.el('div', 'st-wb-card' + (o.className ? ' ' + o.className : ''), null, host);
      if (w.bg) card.style.background = w.bg;
      var word = Studio.el('div', 'st-wb-word', null, card);
      if (w.ink) word.style.color = w.ink;
      var mask = Studio.el('span', w.treatment === 'rise' || w.treatment === 'echo' ? 'st-mask-inline' : 'st-wb-plain', null, word);
      var text = Studio.el('span', 'st-wb-text', w.text, mask);
      var dot = w.accent ? Studio.el('span', 'st-wb-dot', '.', word) : null;
      if (o.fit !== false) T.fit(word, { min: Studio.u(6) });
      var split = w.treatment === 'drop' ? T.split(text, { type: 'chars' }) : null;
      var echoes = [];
      if (w.treatment === 'echo') {
        [-2, -1, 1, 2].forEach(function (k) {
          var e = Studio.el('div', 'st-wb-echo', w.text + (w.accent ? '.' : ''), card);
          e.setAttribute('aria-hidden', 'true');
          e.style.fontSize = word.style.fontSize;
          e.style.setProperty('--wb-shift', String(k));
          echoes.push(e);
        });
      }
      return { card: card, word: word, text: text, dot: dot, split: split, echoes: echoes, data: w };
    });
    function treat(tl, c, t, next) {
      var w = c.data, kind = w.treatment || 'rise';
      var span = Math.max(0.2, next - t);
      if (kind === 'rise') return T.rise(tl, c.text, t, { duration: Math.min(0.5, span * 0.6), from: 105, fade: false });
      if (kind === 'smear') return Studio.fx.smear(tl, c.word, t, { side: w.side || 'left', duration: Math.min(0.45, span * 0.6) });
      if (kind === 'drop') return T.cascade(tl, c.split.chars, t, { duration: Math.min(0.45, span * 0.5), stagger: Math.min(0.04, span * 0.4 / Math.max(1, c.split.chars.length)), distance: 1.3, rotate: 22 });
      if (kind === 'stretch') {
        tl.fromTo(c.text, { scaleX: w.stretch || 2.6, transformOrigin: '50% 50%' }, { scaleX: 1, duration: Math.min(0.6, span * 0.7), ease: 'expo.out', immediateRender: true }, t);
        return t + Math.min(0.6, span * 0.7);
      }
      if (kind === 'spin') {
        tl.fromTo(c.text, { rotation: -200, scale: 0.25, transformOrigin: '50% 55%' }, { rotation: 0, scale: 1, duration: Math.min(0.6, span * 0.7), ease: 'back.out(1.4)', immediateRender: true }, t);
        return t + Math.min(0.6, span * 0.7);
      }
      if (kind === 'track') return T.track(tl, c.text, t, { from: '0.9em', to: '0em', duration: Math.min(0.7, span * 0.8) });
      if (kind === 'echo') {
        var end = T.rise(tl, c.text, t, { duration: Math.min(0.4, span * 0.5), from: 105, fade: false });
        tl.fromTo(c.echoes, { autoAlpha: 0 }, { autoAlpha: 0.55, duration: 0.08, ease: 'none', stagger: 0.05, immediateRender: true }, t + 0.1);
        tl.fromTo(c.echoes, { autoAlpha: 0.55 }, { autoAlpha: 0, duration: Math.min(0.4, span * 0.4), ease: 'power1.in', stagger: 0.04, immediateRender: false }, Math.max(t + 0.35, next - Math.min(0.45, span * 0.45)));
        return Math.max(end, t + 0.3);
      }
      return t;
    }
    return {
      cards: cards,
      times: times,
      schedule: function (tl) {
        cards.forEach(function (c, i) {
          var t = times[i], next = times[i + 1];
          Studio.show(tl, c.card, t);
          if (i < cards.length - 1 || !o.holdLast) Studio.hide(tl, c.card, next);
          treat(tl, c, t, next);
        });
        return times[cards.length];
      }
    };
  };

  var HUD_CORNERS = ['tl', 'tr', 'bl', 'br'];

  /**
   * Frame HUD: corner brackets, small labels in the four corners and an optional progress rule just
   * below the safe area, kept above scenes and transitions as a continuity device. Labels can be
   * swapped at cue times. data: {tl, tr, bl, br}; options: {progress (true), brackets (true)}.
   * Returns {el, enter(tl, at), set(tl, corner, text, at), progress(tl, from, to), exit(tl, at)}.
   */
  C.frameHud = function (parent, data, options) {
    var o = options || {};
    var host = typeof parent === 'string' ? document.querySelector(parent) : parent;
    var hud = Studio.el('div', 'st-hud' + (o.className ? ' ' + o.className : ''), null, host);
    hud.setAttribute('data-layout-allow-overlap', '');
    var brackets = o.brackets === false ? [] : HUD_CORNERS.map(function (c) {
      var b = Studio.el('span', 'st-hud-corner ' + c, null, hud);
      b.setAttribute('aria-hidden', 'true');
      return b;
    });
    var labels = {};
    HUD_CORNERS.forEach(function (c) {
      var box = Studio.el('div', 'st-hud-label ' + c, null, hud);
      labels[c] = { box: box, current: data[c] ? Studio.el('span', 'st-hud-value', data[c], box) : null };
    });
    var rule = null, fill = null;
    if (o.progress !== false) {
      rule = Studio.el('div', 'st-hud-rule', null, hud);
      fill = Studio.el('div', 'st-hud-fill', null, rule);
      rule.setAttribute('aria-hidden', 'true');
      global.gsap.set(fill, { scaleX: 0, transformOrigin: '0% 50%' });
    }
    var initial = HUD_CORNERS.map(function (c) { return labels[c].current; }).filter(Boolean);
    return {
      el: hud,
      enter: function (tl, at) {
        if (brackets.length) tl.fromTo(brackets, { scale: 0, autoAlpha: 0 }, { scale: 1, autoAlpha: 1, duration: 0.45, ease: 'power3.out', stagger: 0.05 }, at);
        if (initial.length) tl.fromTo(initial, { autoAlpha: 0, letterSpacing: '0.5em' }, { autoAlpha: 1, letterSpacing: '0.12em', duration: 0.6, ease: 'power3.out', stagger: 0.06 }, at + 0.1);
        if (rule) tl.fromTo(rule, { scaleX: 0, transformOrigin: '0% 50%' }, { scaleX: 1, duration: 0.6, ease: 'power2.inOut' }, at + 0.1);
        return at + 0.7;
      },
      set: function (tl, corner, text, at) {
        var slot = labels[corner];
        if (!slot) throw new Error('Studio.comp.frameHud: unknown corner ' + corner);
        var next = Studio.el('span', 'st-hud-value', text, slot.box);
        tl.fromTo(next, { autoAlpha: 0, yPercent: 60 }, { autoAlpha: 1, yPercent: 0, duration: 0.28, ease: 'power2.out', immediateRender: true }, at + 0.08);
        if (slot.current) tl.fromTo(slot.current, { autoAlpha: 1, yPercent: 0 }, { autoAlpha: 0, yPercent: -60, duration: 0.14, ease: 'power2.in', immediateRender: false }, at);
        slot.current = next;
        return at + 0.36;
      },
      progress: function (tl, from, to, po) {
        if (!fill) return to;
        var p = po || {};
        tl.fromTo(fill, { scaleX: p.start || 0, transformOrigin: '0% 50%' }, { scaleX: p.end === undefined ? 1 : p.end, duration: to - from, ease: p.ease || 'none', immediateRender: false }, from);
        return to;
      },
      exit: function (tl, at) {
        var all = brackets.concat(Studio.all('.st-hud-value', hud));
        if (rule) all.push(rule);
        tl.fromTo(all, { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.35, ease: 'power1.in', immediateRender: false }, at);
        return at + 0.35;
      }
    };
  };

  /**
   * Callout: a handwritten note with a hand-drawn arrow to a target and an optional loop around it
   * (annotation layer for explainers). Measured where the target renders at `at` (Studio.boxAt), so
   * the target should hold still while the note is up. `parent` must be a full-frame container.
   * data: {text, target, side 'right'|'left'|'top'|'bottom', distance (u, 9), loop (true), seed}.
   * Returns {el, enter(tl, at), exit(tl, at)}.
   */
  C.callout = function (parent, data, options) {
    var o = options || {};
    var host = typeof parent === 'string' ? document.querySelector(parent) : parent;
    var svg = Studio.draw.layer(host, 'st-annot-layer');
    var label = Studio.el('div', 'st-callout' + (o.className ? ' ' + o.className : ''), data.text, host);
    var drawn = [];
    return {
      el: label,
      enter: function (tl, at) {
        var f = Studio.format;
        var b = Studio.boxAt(tl, data.target, at);
        var side = data.side || 'right';
        var gap = Studio.u(data.distance === undefined ? 9 : data.distance);
        var lw = label.offsetWidth, lh = label.offsetHeight;
        var lx = side === 'right' ? b.x + b.w + gap : side === 'left' ? b.x - gap - lw : b.cx - lw / 2;
        var ly = side === 'top' ? b.y - gap - lh : side === 'bottom' ? b.y + b.h + gap : b.cy - lh / 2 - Studio.u(2);
        lx = Math.max(f.safe.left, Math.min(f.width - f.safe.right - lw, lx));
        ly = Math.max(f.safe.top, Math.min(f.height - f.safe.bottom - lh, ly));
        label.style.left = lx + 'px';
        label.style.top = ly + 'px';
        var seed = data.seed || 17;
        var end = at;
        var pad = Studio.u(1.6);
        var rx = b.w / 2 + pad, ry = b.h / 2 + pad;
        if (data.loop !== false) {
          var loop = Studio.svg('path', { d: Studio.draw.loop(seed, b.cx, b.cy, rx, ry), 'class': 'st-annot-path' }, svg);
          drawn.push(loop);
          end = Studio.draw.stroke(tl, loop, at, { duration: 0.5, ease: 'power1.inOut' });
        }
        var sx = side === 'right' ? lx - Studio.u(1) : side === 'left' ? lx + lw + Studio.u(1) : lx + lw / 2;
        var sy = side === 'top' ? ly + lh + Studio.u(0.5) : side === 'bottom' ? ly - Studio.u(0.5) : ly + lh * 0.6;
        var ang = Math.atan2(b.cy - sy, b.cx - sx);
        var ex = b.cx - Math.cos(ang) * (data.loop !== false ? rx + Studio.u(0.8) : b.w / 2 + Studio.u(0.8));
        var ey = b.cy - Math.sin(ang) * (data.loop !== false ? ry + Studio.u(0.8) : b.h / 2 + Studio.u(0.8));
        var mx = (sx + ex) / 2, my = (sy + ey) / 2, len = Math.sqrt((ex - sx) * (ex - sx) + (ey - sy) * (ey - sy));
        var bend = (data.bend === undefined ? 0.22 : data.bend) * len;
        var cx = mx - Math.sin(ang) * bend, cy = my + Math.cos(ang) * bend;
        var shaft = Studio.svg('path', { d: 'M' + sx.toFixed(1) + ' ' + sy.toFixed(1) + ' Q' + cx.toFixed(1) + ' ' + cy.toFixed(1) + ' ' + ex.toFixed(1) + ' ' + ey.toFixed(1), 'class': 'st-annot-path' }, svg);
        var ha = Math.atan2(ey - cy, ex - cx), hl = Studio.u(1.8);
        var head = Studio.svg('path', {
          d: 'M' + (ex - hl * Math.cos(ha - 0.55)).toFixed(1) + ' ' + (ey - hl * Math.sin(ha - 0.55)).toFixed(1) + ' L' + ex.toFixed(1) + ' ' + ey.toFixed(1) +
            ' L' + (ex - hl * Math.cos(ha + 0.55)).toFixed(1) + ' ' + (ey - hl * Math.sin(ha + 0.55)).toFixed(1),
          'class': 'st-annot-path'
        }, svg);
        drawn.push(shaft, head);
        var t1 = Studio.draw.stroke(tl, shaft, Math.max(at, end - 0.2), { duration: 0.35, ease: 'power2.out' });
        var t2 = Studio.draw.stroke(tl, head, t1 - 0.05, { duration: 0.15, ease: 'power1.out' });
        var t3 = Studio.space.pop(tl, label, at + 0.15, { tilt: 3, duration: 0.45, seed: seed });
        return Math.max(t2, t3);
      },
      exit: function (tl, at) {
        tl.fromTo(drawn.concat([label]), { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.3, ease: 'power1.in', immediateRender: false }, at);
        return at + 0.3;
      }
    };
  };

  /**
   * Progress stepper: numbered nodes on a rule with labels (recipe, process or chapter progress).
   * advance(tl, index, at) completes the nodes before `index`, marks `index` current and fills the
   * rule up to it; call it in time order. options: {labels (true)}.
   * Returns {el, nodes, enter(tl, at), advance(tl, index, at), exit(tl, at)}.
   */
  C.stepper = function (parent, steps, options) {
    var o = options || {};
    var host = typeof parent === 'string' ? document.querySelector(parent) : parent;
    var el = Studio.el('div', 'st-stepper' + (o.className ? ' ' + o.className : ''), null, host);
    var rule = Studio.el('div', 'st-stepper-rule', null, el);
    var fill = Studio.el('div', 'st-stepper-fill', null, rule);
    global.gsap.set(fill, { scaleX: 0, transformOrigin: '0% 50%' });
    rule.style.left = rule.style.right = 'calc(100% / ' + (2 * steps.length) + ')';
    var nodes = steps.map(function (s, i) {
      var node = Studio.el('div', 'st-step-node', null, el);
      var dot = Studio.el('span', 'st-step-dot', String(i + 1), node);
      var lab = o.labels === false ? null : Studio.el('span', 'st-step-label', s, node);
      return { node: node, dot: dot, label: lab };
    });
    var state = -1;
    var ink = Studio.token('--c-ink-2', '#5b5347'), paper = Studio.token('--c-paper', '#f4efe6');
    var accent = Studio.token('--c-accent', '#c8462b'), ruleC = Studio.token('--c-rule', '#d8cfc0');
    return {
      el: el,
      nodes: nodes,
      enter: function (tl, at) {
        tl.fromTo(rule, { scaleX: 0, transformOrigin: '0% 50%' }, { scaleX: 1, duration: 0.6, ease: 'power2.inOut' }, at);
        Studio.space.pop(tl, nodes.map(function (n) { return n.dot; }), at + 0.1, { stagger: 0.07, tilt: 0 });
        var labs = nodes.map(function (n) { return n.label; }).filter(Boolean);
        if (labs.length) tl.fromTo(labs, { autoAlpha: 0, y: Studio.u(1) }, { autoAlpha: 1, y: 0, duration: 0.4, ease: 'power2.out', stagger: 0.07 }, at + 0.2);
        return at + 0.6 + 0.07 * nodes.length;
      },
      advance: function (tl, index, at) {
        var n = nodes.length;
        var from = Math.max(0, state) / Math.max(1, n - 1), to = index / Math.max(1, n - 1);
        tl.fromTo(fill, { scaleX: from }, { scaleX: to, duration: 0.5, ease: 'power2.inOut', immediateRender: false }, at);
        for (var i = Math.max(0, state); i < index; i++) {
          var wasCurrent = i === state;
          tl.fromTo(nodes[i].dot, { backgroundColor: paper, color: wasCurrent ? accent : ink, borderColor: wasCurrent ? accent : ruleC },
            { backgroundColor: accent, color: paper, borderColor: accent, duration: 0.3, ease: 'power1.out', immediateRender: false }, at + 0.1 * (i - Math.max(0, state)));
        }
        var cur = nodes[index].dot;
        tl.fromTo(cur, { borderColor: ruleC, color: ink }, { borderColor: accent, color: accent, duration: 0.25, ease: 'power1.out', immediateRender: false }, at + 0.3);
        tl.fromTo(cur, { scale: 1 }, { scale: 1.22, duration: 0.18, ease: 'power2.out', immediateRender: false }, at + 0.3);
        tl.fromTo(cur, { scale: 1.22 }, { scale: 1, duration: 0.3, ease: 'power2.inOut', immediateRender: false }, at + 0.48);
        state = index;
        return at + 0.8;
      },
      exit: function (tl, at) {
        tl.fromTo(el, { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.35, ease: 'power1.in', immediateRender: false }, at);
        return at + 0.35;
      }
    };
  };
})(typeof window !== 'undefined' ? window : this);
