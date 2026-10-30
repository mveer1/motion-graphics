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
})(typeof window !== 'undefined' ? window : this);
