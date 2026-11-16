/*
 * Motion Lab fitness kit - Sinew brand graphics, environments, biomechanics overlays and
 * science charts (src/studio/kits/fitness/graphics.js). Needs brand.js and studio-rig.js; the logo
 * icon draws Tibi's head from sculpt-data.js when it is loaded (it is, in the fitness template).
 *
 * Brand rules: .claude/skills/fitness/references/brand-guidelines.md. Fonts are named
 * literally (Outfit, Inter, JetBrains Mono: HyperFrames-bundled), because a bundled font is
 * injected only when its family name appears literally in the page.
 *
 *   var G = Studio.kit.fitness.graphics;
 *   G.logo(svgGroup, {x, y, size, variant: 'lockup' | 'icon' | 'wordmark'});
 *   var lt = G.lowerThird(svgGroup, {x, y, title, sub}); lt.show(tl, at); lt.hide(tl, at);
 *   var gym = G.env.gym(svgGroup, {w, h, floor});  var track = G.env.track(...); track.scroll(tl, from, to, speed);
 *   G.bio.angle(svgGroup, tibi, ['hipR','kneeR','ankleR'], {at, until, tl});  G.bio.force(...)
 */
(function (global) {
  'use strict';

  var Studio = global.Studio || (global.Studio = {});
  var F = (Studio.kit = Studio.kit || {}).fitness = (Studio.kit.fitness || {});
  var P = F.palette;
  var RIG = Studio.rig;
  var G = F.graphics = {};
  function svg(tag, attrs, parent) { return Studio.svg(tag, attrs, parent); }
  function num(v) { return Math.round(v * 100) / 100; }
  function text(parent, str, attrs) {
    var t = svg('text', attrs, parent);
    t.textContent = str;
    return t;
  }
  var FONT_D = "'Outfit', 'Inter', sans-serif", FONT_B = "'Inter', sans-serif", FONT_M = "'JetBrains Mono', monospace";
  G.fonts = { display: 'Outfit', body: 'Inter', mono: 'JetBrains Mono' };

  // ------------------------------------------------------------------ logo
  /** The spark mark alone (Tibi's crest: the same flat flame as on Tibi's head, no outline), height ~ size. */
  G.spark = function (parent, x, y, size, color) {
    var k = (size || 42) / 42;
    var g = svg('g', { transform: 'translate(' + num(x) + ' ' + num(y) + ') scale(' + num(k) + ')' }, parent);
    var fl = F.sculptData && F.sculptData.flame;
    if (fl) {
      var inner = svg('g', { transform: 'translate(0 -9)' }, g);        // base of the flame on (x, y)
      svg('path', { d: fl[0], fill: color || P.spark }, inner);
      svg('path', { d: fl[1], fill: '#FFE08A' }, inner);
      return g;
    }
    svg('path', { d: 'M0 0 C13 -5 16 -22 3 -42 C-1 -30 -16 -26 -14 -10 C-13 -4 -7 0 0 0 Z', fill: color || P.spark }, g);
    svg('path', { d: 'M-1 -6 C5 -9 7 -18 2 -27 C0 -20 -7 -17 -6 -10 C-5.5 -7 -3.5 -6 -1 -6 Z', fill: P.sparkLight }, g);
    return g;
  };
  /**
   * Sinew logo. variant 'icon': Tibi's head (Cobalt Sculpt: faceless, face plane, spark) in a rounded square.
   * 'wordmark': lowercase "sinew" in Outfit 800 whose i carries the spark instead of a dot.
   * 'lockup': icon + wordmark. size is the cap height of the wordmark / the icon side / 2.
   */
  G.logo = function (parent, opts) {
    var o = opts || {};
    var size = o.size || 60;
    var g = svg('g', { 'class': 'sinew-logo', transform: 'translate(' + num(o.x || 0) + ' ' + num(o.y || 0) + ')' }, parent);
    var variant = o.variant || 'lockup';
    var ink = o.ink || P.ink;
    var x = 0;
    if (variant === 'icon' || variant === 'lockup') {
      var s = size * 2 / 200;
      var ic = svg('g', { transform: 'translate(0 ' + num(-size * 1.55) + ') scale(' + num(s) + ')' }, g);
      svg('rect', { x: 0, y: 0, width: 200, height: 200, rx: 52, fill: o.tile || P.cobalt }, ic);
      var SD = F.sculptData;
      if (SD) {
        // the Cobalt Sculpt head and face plane (front view, pivot at the jaw), lighter tile behind
        var head = svg('g', { transform: 'translate(100 180) scale(1.42)' }, ic);
        var hp = SD.segments.mF_head_C, face = hp.mus.filter(function (m) { return m[0] === 'face'; })[0];
        svg('path', { d: SD.paths[hp.b][0], fill: o.tile ? P.cobalt : SD.colors.body, stroke: o.tile || P.cobaltDeep, 'stroke-width': 3 }, head);
        if (face) svg('path', { d: SD.paths[face[1]][0], fill: SD.colors.face }, head);
        G.spark(ic, 100, 50, 46);
      } else {
        G.spark(ic, 100, 120, 80);
      }
      x = variant === 'lockup' ? size * 2.35 : size * 2;
    }
    if (variant === 'wordmark' || variant === 'lockup') {
      var wm = svg('g', { transform: 'translate(' + num(x) + ' 0)' }, g);
      var fs = size * 1.42;
      // s ı n e w: the dotless i takes the spark as its dot
      var t = text(wm, 'sınew', { x: 0, y: 0, 'font-family': FONT_D, 'font-weight': 800, 'font-size': num(fs), fill: ink, 'letter-spacing': '-0.02em' });
      t.setAttribute('class', 'sinew-wordmark');
      // spark over the i: positioned from the font's advance of "s" (measured at build time)
      var sW = 0;
      try { sW = t.getSubStringLength(0, 1); } catch (e) { sW = fs * 0.5; }
      var iW = 0;
      try { iW = t.getSubStringLength(1, 1); } catch (e2) { iW = fs * 0.25; }
      G.spark(wm, sW + iW / 2 + 1, -fs * 0.6, fs * 0.42);
      g.__width = x + (function () { try { return t.getComputedTextLength(); } catch (e3) { return fs * 2.6; } })();
    }
    if (o.tagline) text(g, o.tagline, { x: x, y: num(size * 0.62), 'font-family': FONT_B, 'font-weight': 600, 'font-size': num(size * 0.3), fill: P.ink2, 'letter-spacing': '0.06em' });
    return g;
  };

  // ------------------------------------------------------------------ titles and lower thirds
  function plate(parent, x, y, w, h, fill, r) {
    return svg('rect', { x: num(x), y: num(y), width: num(w), height: num(h), rx: num(r === undefined ? h / 2 : r), fill: fill }, parent);
  }
  /**
   * Short-form / mid-form title card: kicker pill, two-line title, spark accent.
   * show(tl, at) / hide(tl, at). Width in px; text sizes scale with `size` (title cap height).
   */
  G.titleCard = function (parent, opts) {
    var o = opts || {};
    var size = o.size || 56;
    var g = svg('g', { 'class': 'sinew-title', transform: 'translate(' + num(o.x || 0) + ' ' + num(o.y || 0) + ')', opacity: 0 }, parent);
    var anchor = o.align === 'left' ? 'start' : 'middle';
    var kick = null;
    if (o.kicker) {
      var kw = o.kicker.length * size * 0.24 + size * 0.9;
      var kx = anchor === 'middle' ? -kw / 2 : 0;
      kick = svg('g', {}, g);
      plate(kick, kx, -size * 2.05, kw, size * 0.62, P.cobalt);
      text(kick, o.kicker.toUpperCase(), { x: num(kx + kw / 2), y: num(-size * 1.62), 'text-anchor': 'middle', 'font-family': FONT_M, 'font-weight': 700, 'font-size': num(size * 0.3), fill: P.paper, 'letter-spacing': '0.08em' });
    }
    var lines = (o.title || '').split('\n');
    var tl1 = lines.map(function (ln, i) {
      return text(g, ln, { x: 0, y: num(i * size * 1.08), 'text-anchor': anchor, 'font-family': FONT_D, 'font-weight': 800, 'font-size': num(size), fill: i === lines.length - 1 && o.accentLast ? P.cobalt : P.ink, 'letter-spacing': '-0.02em' });
    });
    var bar = plate(g, anchor === 'middle' ? -size * 0.9 : 0, lines.length * size * 1.08 - size * 0.5, size * 1.8, size * 0.16, P.spark, 3);
    return {
      g: g, lines: tl1, kicker: kick, bar: bar,
      show: function (tl, at) {
        // a card that opens the film is fully drawn on frame 0 (the hook is legible before anything moves; fitness-qa flags a bare first frame)
        if (at <= 0.001) {
          tl.fromTo(g, { opacity: 1 }, { opacity: 1, duration: 0.0001, immediateRender: true }, 0);
          tl.fromTo(tl1, { attr: { dy: 0 }, opacity: 1 }, { attr: { dy: 0 }, opacity: 1, duration: 0.0001, immediateRender: true }, 0);
          if (kick) tl.fromTo(kick, { opacity: 1 }, { opacity: 1, duration: 0.0001, immediateRender: true }, 0);
          tl.fromTo(bar, { attr: { width: num(size * 1.8) } }, { attr: { width: num(size * 1.8) }, duration: 0.0001, immediateRender: true }, 0);
          return;
        }
        tl.fromTo(g, { opacity: 0 }, { opacity: 1, duration: 0.3, ease: 'power1.out', immediateRender: true }, at);
        tl.fromTo(tl1, { attr: { dy: num(size * 0.5) }, opacity: 0 }, { attr: { dy: 0 }, opacity: 1, duration: 0.55, ease: 'expo.out', stagger: 0.09, immediateRender: true }, at);
        if (kick) tl.fromTo(kick, { opacity: 0 }, { opacity: 1, duration: 0.3, immediateRender: true }, at + 0.1);
        tl.fromTo(bar, { attr: { width: 0 } }, { attr: { width: num(size * 1.8) }, duration: 0.5, ease: 'expo.out', immediateRender: true }, at + 0.25);
        return at + 0.7;
      },
      hide: function (tl, at) {
        tl.fromTo(g, { opacity: 1 }, { opacity: 0, duration: 0.3, ease: 'power1.in', immediateRender: false }, at);
        return at + 0.3;
      }
    };
  };
  /** Lower third: cobalt tab with spark, title and a mono sub-line (source or term). */
  G.lowerThird = function (parent, opts) {
    var o = opts || {};
    var size = o.size || 26;
    var w = o.width || Math.max(o.title.length * size * 0.56, (o.sub || '').length * size * 0.42) + size * 2.6;
    var g = svg('g', { 'class': 'sinew-lt', transform: 'translate(' + num(o.x || 0) + ' ' + num(o.y || 0) + ')', opacity: 0 }, parent);
    var bg = plate(g, 0, 0, w, size * (o.sub ? 2.5 : 1.7), P.paper, size * 0.4);
    bg.setAttribute('stroke', P.ink); bg.setAttribute('stroke-width', 2);
    var tab = plate(g, 0, 0, size * 1.4, size * (o.sub ? 2.5 : 1.7), P.cobalt, size * 0.4);
    G.spark(g, size * 0.7, size * (o.sub ? 1.75 : 1.3), size * 0.95);
    var t1 = text(g, o.title, { x: num(size * 1.9), y: num(size * 1.15), 'font-family': FONT_D, 'font-weight': 700, 'font-size': num(size), fill: P.ink });
    var t2 = o.sub ? text(g, o.sub, { x: num(size * 1.9), y: num(size * 2.05), 'font-family': FONT_M, 'font-weight': 500, 'font-size': num(size * 0.58), fill: P.ink2 }) : null;
    return {
      g: g, width: w,
      show: function (tl, at) {
        tl.fromTo(g, { opacity: 0 }, { opacity: 1, duration: 0.25, immediateRender: true }, at);
        tl.fromTo(bg, { attr: { width: size * 1.4 } }, { attr: { width: num(w) }, duration: 0.5, ease: 'expo.out', immediateRender: true }, at);
        tl.fromTo([t1, t2].filter(Boolean), { opacity: 0 }, { opacity: 1, duration: 0.3, stagger: 0.08, immediateRender: true }, at + 0.2);
        return at + 0.6;
      },
      hide: function (tl, at) {
        tl.fromTo(g, { opacity: 1 }, { opacity: 0, duration: 0.3, immediateRender: false }, at);
        return at + 0.3;
      }
    };
  };
  /** Chapter card for long-form: number, title, the chapter's one mechanism. */
  G.chapterCard = function (parent, opts) {
    var o = opts || {};
    var g = svg('g', { 'class': 'sinew-chapter', transform: 'translate(' + num(o.x || 0) + ' ' + num(o.y || 0) + ')', opacity: 0 }, parent);
    text(g, 'CHAPTER ' + (o.number || 1), { x: 0, y: -70, 'text-anchor': 'middle', 'font-family': FONT_M, 'font-weight': 700, 'font-size': 18, fill: P.cobalt, 'letter-spacing': '0.2em' });
    text(g, o.title || '', { x: 0, y: 0, 'text-anchor': 'middle', 'font-family': FONT_D, 'font-weight': 800, 'font-size': 64, fill: P.ink });
    if (o.sub) text(g, o.sub, { x: 0, y: 48, 'text-anchor': 'middle', 'font-family': FONT_B, 'font-weight': 500, 'font-size': 24, fill: P.ink2 });
    G.spark(g, 0, -92, 30);
    return {
      g: g,
      show: function (tl, at) { tl.fromTo(g, { opacity: 0 }, { opacity: 1, duration: 0.5, immediateRender: true }, at); return at + 0.5; },
      hide: function (tl, at) { tl.fromTo(g, { opacity: 1 }, { opacity: 0, duration: 0.4, immediateRender: false }, at); return at + 0.4; }
    };
  };

  /**
   * Brand sting (long-form opening and short-form end): the spark ignites, the wordmark writes on,
   * the tagline rises. start(tl, at) returns the end time (about 2.2 s). Centre at (x, y).
   */
  G.sting = function (parent, opts) {
    var o = opts || {};
    var g = svg('g', { 'class': 'sinew-sting', opacity: 0 }, parent);
    var size = o.size || 70;
    var logo = G.logo(g, { variant: 'lockup', size: size, x: 0, y: 0, tagline: o.tagline === false ? null : 'SEE WHAT YOUR BODY IS DOING' });
    var w = logo.__width || size * 6;
    logo.setAttribute('transform', 'translate(' + num((o.x || 0) - w / 2) + ' ' + num(o.y || 0) + ')');
    var flare = svg('circle', { cx: num((o.x || 0) - w / 2 + size), cy: num((o.y || 0) - size * 0.55), r: 0, fill: P.spark, opacity: 0.5 }, g);
    return {
      g: g,
      start: function (tl, at) {
        tl.fromTo(g, { opacity: 0 }, { opacity: 1, duration: 0.25, immediateRender: true }, at);
        tl.fromTo(flare, { attr: { r: 0 }, opacity: 0.6 }, { attr: { r: size * 2.4 }, opacity: 0, duration: 0.9, ease: 'expo.out', immediateRender: true }, at + 0.1);
        tl.fromTo(logo, { opacity: 0, attr: { transform: 'translate(' + num((o.x || 0) - w / 2) + ' ' + num((o.y || 0) + size * 0.4) + ')' } }, { opacity: 1, attr: { transform: 'translate(' + num((o.x || 0) - w / 2) + ' ' + num(o.y || 0) + ')' }, duration: 0.7, ease: 'expo.out', immediateRender: true }, at + 0.15);
        return at + 2.2;
      },
      hide: function (tl, at) { tl.fromTo(g, { opacity: 1 }, { opacity: 0, duration: 0.4, immediateRender: false }, at); return at + 0.4; }
    };
  };
  /**
   * End card: takeaway lines, an evidence badge row, the general-education line and the logo.
   * lines: ['Tension: the signal', ...]; note: the not-medical-advice line (always shown).
   */
  G.endCard = function (parent, opts) {
    var o = opts || {};
    var x = o.x || 0, y = o.y || 0;
    var g = svg('g', { 'class': 'sinew-endcard', opacity: 0 }, parent);
    var rows = (o.lines || []).map(function (ln, i) {
      var r = svg('g', { opacity: 0 }, g);
      plate(r, x, y + i * 70, o.width || 460, 56, i % 2 ? P.paper2 : '#FFFFFF', 14).setAttribute('stroke', P.ink);
      svg('circle', { cx: x + 30, cy: y + i * 70 + 28, r: 9, fill: [P.cobalt, P.muscle, P.spark][i % 3] }, r);
      text(r, ln, { x: x + 54, y: y + i * 70 + 37, 'font-family': FONT_D, 'font-weight': 700, 'font-size': 26, fill: P.ink });
      return r;
    });
    var note = text(g, o.note || 'General education, not medical advice.', { x: x, y: y + rows.length * 70 + 34, 'font-family': FONT_B, 'font-weight': 500, 'font-size': 16, fill: P.ink2, opacity: 0 });
    return {
      g: g, rows: rows,
      show: function (tl, at, step) {
        var st = step || 0.45;
        tl.fromTo(g, { opacity: 0 }, { opacity: 1, duration: 0.2, immediateRender: true }, at);
        rows.forEach(function (r, i) {
          tl.fromTo(r, { opacity: 0, attr: { transform: 'translate(-30 0)' } }, { opacity: 1, attr: { transform: 'translate(0 0)' }, duration: 0.45, ease: 'expo.out', immediateRender: true }, at + i * st);
        });
        tl.fromTo(note, { opacity: 0 }, { opacity: 1, duration: 0.4, immediateRender: true }, at + rows.length * st);
        return at + rows.length * st + 0.4;
      }
    };
  };

  // ------------------------------------------------------------------ evidence and citations
  /**
   * Evidence grades used on screen (see the fitness research protocol). Colours are fixed per
   * grade so a viewer learns them across films.
   */
  G.grades = {
    established: { label: 'Established mechanism', color: P.emerald },
    strong: { label: 'Strong evidence', color: P.emerald },
    moderate: { label: 'Moderate evidence', color: P.cobalt },
    preliminary: { label: 'Preliminary', color: P.sparkDeep },
    hypothesis: { label: 'Hypothesis', color: P.violet },
    unsupported: { label: 'Not supported', color: P.muscleDeep }
  };
  /** A badge with the grade's colour dot and label. */
  G.evidenceBadge = function (parent, opts) {
    var o = opts || {};
    var gr = G.grades[o.grade] || G.grades.moderate;
    var size = o.size || 18;
    var label = o.label || gr.label;
    var w = label.length * size * 0.6 + size * 2.4;
    var g = svg('g', { 'class': 'sinew-badge', transform: 'translate(' + num(o.x || 0) + ' ' + num(o.y || 0) + ')', opacity: 0 }, parent);
    var bg = plate(g, 0, 0, w, size * 1.9, P.paper);
    bg.setAttribute('stroke', gr.color); bg.setAttribute('stroke-width', 2.4);
    svg('circle', { cx: size * 1.0, cy: size * 0.95, r: size * 0.38, fill: gr.color }, g);
    text(g, label, { x: num(size * 1.8), y: num(size * 1.3), 'font-family': FONT_B, 'font-weight': 700, 'font-size': num(size), fill: P.ink });
    return {
      g: g, width: w,
      show: function (tl, at) { tl.fromTo(g, { opacity: 0, attr: { transform: 'translate(' + num(o.x || 0) + ' ' + num((o.y || 0) + 10) + ')' } }, { opacity: 1, attr: { transform: 'translate(' + num(o.x || 0) + ' ' + num(o.y || 0) + ')' }, duration: 0.4, ease: 'back.out(2)', immediateRender: true }, at); return at + 0.4; },
      hide: function (tl, at) { tl.fromTo(g, { opacity: 1 }, { opacity: 0, duration: 0.25, immediateRender: false }, at); return at + 0.25; }
    };
  };
  /** A source line: "Phillips et al. 1997 · Am J Physiol · RCT · n = 8". Always on screen with a claim. */
  G.citation = function (parent, opts) {
    var o = opts || {};
    var size = o.size || 15;
    var g = svg('g', { 'class': 'sinew-cite', transform: 'translate(' + num(o.x || 0) + ' ' + num(o.y || 0) + ')', opacity: 0 }, parent);
    var str = o.text || '';
    var w = str.length * size * 0.61 + size * 1.6;
    var anchorX = o.align === 'right' ? -w : (o.align === 'center' ? -w / 2 : 0);
    plate(g, anchorX, -size * 1.25, w, size * 1.8, 'rgba(27,29,41,0.07)', size * 0.5);
    text(g, str, { x: num(anchorX + size * 0.8), y: num(size * 0.05), 'font-family': FONT_M, 'font-weight': 500, 'font-size': num(size), fill: P.ink2 });
    return {
      g: g,
      show: function (tl, at) { tl.fromTo(g, { opacity: 0 }, { opacity: 1, duration: 0.35, immediateRender: true }, at); return at + 0.35; },
      hide: function (tl, at) { tl.fromTo(g, { opacity: 1 }, { opacity: 0, duration: 0.25, immediateRender: false }, at); return at + 0.25; }
    };
  };
  /** A "MYTH" stamp that slams on, with a strike-through over a claim. */
  G.mythStamp = function (parent, opts) {
    var o = opts || {};
    var s = o.size || 1;
    var g = svg('g', { 'class': 'sinew-myth', transform: 'translate(' + num(o.x || 0) + ' ' + num(o.y || 0) + ') rotate(-8) scale(' + num(s) + ')', opacity: 0 }, parent);
    svg('rect', { x: -96, y: -36, width: 192, height: 72, rx: 12, fill: 'none', stroke: P.muscleDeep, 'stroke-width': 7 }, g);
    text(g, o.word || 'MYTH', { x: 0, y: 17, 'text-anchor': 'middle', 'font-family': FONT_D, 'font-weight': 900, 'font-size': 50, fill: P.muscleDeep, 'letter-spacing': '0.08em' });
    return {
      g: g,
      slam: function (tl, at) {
        var base = 'translate(' + num(o.x || 0) + ' ' + num(o.y || 0) + ') rotate(-8) scale(';
        tl.fromTo(g, { opacity: 0, attr: { transform: base + num(s * 1.8) + ')' } }, { opacity: 1, attr: { transform: base + num(s) + ')' }, duration: 0.28, ease: 'power4.in', immediateRender: true }, at);
        return at + 0.28;
      }
    };
  };
  /** A label with a leader line to a point (anatomy callout). show draws the line, then the text. */
  G.callout = function (parent, opts) {
    var o = opts || {};
    var g = svg('g', { 'class': 'sinew-callout', opacity: 0 }, parent);
    var p = o.point, l = o.label;
    var line = svg('path', { d: 'M' + num(p[0]) + ' ' + num(p[1]) + ' L' + num(l[0]) + ' ' + num(l[1]), stroke: o.color || P.ink, 'stroke-width': 2.4, fill: 'none', 'stroke-linecap': 'round' }, g);
    var dot = svg('circle', { cx: num(p[0]), cy: num(p[1]), r: 5, fill: o.color || P.ink, stroke: P.paper, 'stroke-width': 2 }, g);
    var anchor = l[0] < p[0] ? 'end' : 'start';
    var size = o.size || 22;
    var t = text(g, o.text, { x: num(l[0] + (anchor === 'end' ? -10 : 10)), y: num(l[1] + size * 0.35), 'text-anchor': anchor, 'font-family': FONT_D, 'font-weight': 700, 'font-size': size, fill: P.ink });
    var t2 = o.sub ? text(g, o.sub, { x: num(l[0] + (anchor === 'end' ? -10 : 10)), y: num(l[1] + size * 1.25), 'text-anchor': anchor, 'font-family': FONT_B, 'font-weight': 500, 'font-size': num(size * 0.66), fill: P.ink2 }) : null;
    var len = Math.ceil(Math.sqrt(Math.pow(l[0] - p[0], 2) + Math.pow(l[1] - p[1], 2)));
    line.setAttribute('stroke-dasharray', len + ' ' + len);
    return {
      g: g,
      show: function (tl, at) {
        tl.fromTo(g, { opacity: 0 }, { opacity: 1, duration: 0.15, immediateRender: true }, at);
        tl.fromTo(dot, { attr: { r: 0 } }, { attr: { r: 5 }, duration: 0.25, ease: 'back.out(3)', immediateRender: true }, at);
        tl.fromTo(line, { strokeDashoffset: len }, { strokeDashoffset: 0, duration: 0.35, ease: 'power2.out', immediateRender: true }, at + 0.05);
        tl.fromTo([t, t2].filter(Boolean), { opacity: 0 }, { opacity: 1, duration: 0.3, stagger: 0.08, immediateRender: true }, at + 0.3);
        return at + 0.65;
      },
      hide: function (tl, at) { tl.fromTo(g, { opacity: 1 }, { opacity: 0, duration: 0.25, immediateRender: false }, at); return at + 0.25; }
    };
  };

  // ------------------------------------------------------------------ environments
  G.env = {};
  /** Gym interior: wall, chair rail, plate rack and dumbbell rack silhouettes, rubber floor. */
  G.env.gym = function (parent, opts) {
    var o = opts || {};
    var w = o.w || 1280, h = o.h || 720, floor = o.floor || h * 0.82;
    var g = svg('g', { 'class': 'env-gym' }, parent);
    svg('rect', { x: 0, y: 0, width: w, height: floor, fill: P.paper }, g);
    svg('rect', { x: 0, y: floor - h * 0.3, width: w, height: h * 0.3, fill: P.paper2 }, g);
    svg('rect', { x: 0, y: floor - h * 0.3, width: w, height: 6, fill: P.cobalt, opacity: 0.85 }, g);
    // windows / light panels
    for (var i = 0; i < 4; i++) svg('rect', { x: w * (0.08 + i * 0.24), y: h * 0.1, width: w * 0.14, height: h * 0.22, rx: 10, fill: '#FFFFFF', opacity: 0.7, stroke: P.paper2, 'stroke-width': 4 }, g);
    // plate tree and dumbbell rack, far back, desaturated
    var far = svg('g', { opacity: 0.32 }, g);
    var px = o.rackX === undefined ? w * 0.82 : o.rackX;
    svg('rect', { x: px - 4, y: floor - 210, width: 8, height: 210, fill: P.ink2 }, far);
    [[-26, 150, 34], [26, 120, 30], [-26, 70, 28], [26, 50, 24]].forEach(function (pl) { svg('circle', { cx: px + pl[0], cy: floor - pl[1], r: pl[2], fill: P.ink2 }, far); });
    var dx = o.dumbbellX === undefined ? w * 0.12 : o.dumbbellX;
    svg('rect', { x: dx, y: floor - 96, width: 220, height: 10, fill: P.ink2 }, far);
    svg('rect', { x: dx, y: floor - 46, width: 220, height: 10, fill: P.ink2 }, far);
    for (var k = 0; k < 6; k++) {
      svg('rect', { x: dx + 10 + k * 36, y: floor - 116, width: 22, height: 20, rx: 4, fill: P.ink2 }, far);
      svg('rect', { x: dx + 10 + k * 36, y: floor - 66, width: 22, height: 20, rx: 4, fill: P.ink2 }, far);
    }
    svg('rect', { x: dx + 6, y: floor - 96, width: 6, height: 96, fill: P.ink2 }, far);
    svg('rect', { x: dx + 208, y: floor - 96, width: 6, height: 96, fill: P.ink2 }, far);
    // floor
    svg('rect', { x: 0, y: floor, width: w, height: h - floor, fill: '#2B2E40' }, g);
    svg('rect', { x: 0, y: floor, width: w, height: 5, fill: P.ink }, g);
    for (var t = 0; t < w; t += 160) svg('line', { x1: t, x2: t - 60, y1: floor + 5, y2: h, stroke: '#3A3D52', 'stroke-width': 2 }, g);
    return { g: g, floor: floor };
  };
  /** Running track: sky, stands band, lanes in perspective; scroll() moves the lane marks. */
  G.env.track = function (parent, opts) {
    var o = opts || {};
    var w = o.w || 1280, h = o.h || 720, floor = o.floor || h * 0.8;
    var g = svg('g', { 'class': 'env-track' }, parent);
    svg('rect', { x: 0, y: 0, width: w, height: floor, fill: P.paper }, g);
    svg('rect', { x: 0, y: floor - h * 0.22, width: w, height: h * 0.12, fill: P.paper2 }, g);
    for (var i = 0; i < 18; i++) svg('rect', { x: i * w / 18 + 6, y: floor - h * 0.21, width: w / 18 - 12, height: h * 0.1, rx: 3, fill: P.cobaltGlass }, g);
    svg('rect', { x: 0, y: floor - h * 0.1, width: w, height: h * 0.1, fill: '#9FCF9A' }, g);
    svg('rect', { x: 0, y: floor, width: w, height: h - floor, fill: '#D2603F' }, g);
    var marks = svg('g', { transform: 'translate(0 0)' }, g);
    var gap = 120;
    for (var x = -gap; x < w * 3 + gap; x += gap) {
      svg('rect', { x: x, y: floor + (h - floor) * 0.42, width: 60, height: 5, fill: '#FFFFFF', opacity: 0.85 }, marks);
    }
    svg('rect', { x: 0, y: floor, width: w, height: 4, fill: '#FFFFFF' }, g);
    return {
      g: g, floor: floor, marks: marks,
      scroll: function (tl, from, to, speed) {
        // finite: lane marks move left at `speed` px/s, wrapped every `gap` px (pattern repeats)
        var dist = (to - from) * speed;
        var reps = Math.max(1, Math.ceil(dist / gap));
        var per = gap / speed;
        for (var r = 0; r < reps; r++) {
          tl.fromTo(marks, { attr: { transform: 'translate(0 0)' } }, { attr: { transform: 'translate(' + (-gap) + ' 0)' }, duration: per, ease: 'none', immediateRender: false }, from + r * per);
        }
        return from + reps * per;
      }
    };
  };
  /** Outdoor path: hills, trees, path; scroll() parallaxes the near layer. */
  G.env.outdoor = function (parent, opts) {
    var o = opts || {};
    var w = o.w || 1280, h = o.h || 720, floor = o.floor || h * 0.8;
    var g = svg('g', { 'class': 'env-outdoor' }, parent);
    svg('rect', { x: 0, y: 0, width: w, height: h, fill: '#EAF1F7' }, g);
    svg('path', { d: 'M0 ' + (floor - 140) + ' Q' + w * 0.25 + ' ' + (floor - 230) + ' ' + w * 0.5 + ' ' + (floor - 150) + ' T' + w + ' ' + (floor - 170) + ' L' + w + ' ' + floor + ' L0 ' + floor + ' Z', fill: '#BFD9B4' }, g);
    var near = svg('g', {}, g);
    for (var i = 0; i < 12; i++) {
      var tx = i * 220 + 60;
      svg('rect', { x: tx - 5, y: floor - 70, width: 10, height: 70, fill: '#7A5A3A' }, near);
      svg('circle', { cx: tx, cy: floor - 92, r: 38, fill: '#5BAA6A' }, near);
    }
    svg('rect', { x: 0, y: floor, width: w, height: h - floor, fill: '#D9C8A6' }, g);
    svg('rect', { x: 0, y: floor, width: w, height: 4, fill: '#B8A27A' }, g);
    return {
      g: g, floor: floor,
      scroll: function (tl, from, to, speed) {
        tl.fromTo(near, { attr: { transform: 'translate(0 0)' } }, { attr: { transform: 'translate(' + num(-(to - from) * speed * 0.6) + ' 0)' }, duration: to - from, ease: 'none', immediateRender: false }, from);
        return to;
      }
    };
  };
  /** Plain Sinew plate: paper with a soft dot grid (anatomy and diagram scenes). */
  G.env.plate = function (parent, opts) {
    var o = opts || {};
    var w = o.w || 1280, h = o.h || 720;
    var g = svg('g', { 'class': 'env-plate' }, parent);
    svg('rect', { x: 0, y: 0, width: w, height: h, fill: P.paper }, g);
    var dots = svg('g', { opacity: 0.5 }, g);
    for (var y = 24; y < h; y += 40) for (var x = 24; x < w; x += 40) svg('circle', { cx: x, cy: y, r: 1.4, fill: P.ink3 }, dots);
    return { g: g };
  };

  // ------------------------------------------------------------------ biomechanics overlays
  // All overlays read the rig's own kinematics (conceptual, authored poses). Label them
  // "illustrative" on screen unless the angles come from a cited measurement.
  G.bio = {};
  /**
   * Joint angle arc at joint b between segments a-b and b-c, sampled from the rig at given
   * times: arc(tl, times[]) re-draws the arc and number at each time (explicit tweens between
   * samples). joints: [[jointA, localA], [jointB, localB], [jointC, localC]] or ids.
   */
  G.bio.angle = function (parent, tibi, joints, opts) {
    var o = opts || {};
    var J = joints.map(function (j) { return typeof j === 'string' ? [j, [0, 0]] : j; });
    var g = svg('g', { 'class': 'bio-angle', opacity: 0 }, parent);
    var r = o.radius || 40;
    var arc = svg('path', { d: '', fill: 'rgba(255,178,36,0.25)', stroke: P.sparkDeep, 'stroke-width': 3 }, g);
    var legs = svg('path', { d: '', fill: 'none', stroke: P.ink, 'stroke-width': 2, 'stroke-dasharray': '6 5' }, g);
    var bg = svg('rect', { x: 0, y: 0, width: 64, height: 30, rx: 8, fill: P.ink }, g);
    var labT = svg('text', { x: 0, y: 0, 'text-anchor': 'middle', 'font-family': FONT_M, 'font-weight': 700, 'font-size': 18, fill: P.paper }, g);
    var lab = svg('tspan', {}, labT);
    var deg = svg('tspan', {}, labT);
    deg.textContent = '\u00B0';
    function geom(pose) {
      var a = RIG.point(tibi.fig, J[0][0], J[0][1], pose), b = RIG.point(tibi.fig, J[1][0], J[1][1], pose), c = RIG.point(tibi.fig, J[2][0], J[2][1], pose);
      var a1 = Math.atan2(a[1] - b[1], a[0] - b[0]), a2 = Math.atan2(c[1] - b[1], c[0] - b[0]);
      var diff = a2 - a1;
      while (diff > Math.PI) diff -= 2 * Math.PI;
      while (diff < -Math.PI) diff += 2 * Math.PI;
      var deg = Math.abs(diff) * 180 / Math.PI;
      var p1 = [b[0] + Math.cos(a1) * r, b[1] + Math.sin(a1) * r], p2 = [b[0] + Math.cos(a2) * r, b[1] + Math.sin(a2) * r];
      var mid = a1 + diff / 2;
      var lp = [b[0] + Math.cos(mid) * (r + 34), b[1] + Math.sin(mid) * (r + 34)];
      return {
        arc: 'M' + num(b[0]) + ' ' + num(b[1]) + ' L' + num(p1[0]) + ' ' + num(p1[1]) + ' A' + r + ' ' + r + ' 0 0 ' + (diff > 0 ? 1 : 0) + ' ' + num(p2[0]) + ' ' + num(p2[1]) + ' Z',
        legs: 'M' + num(a[0]) + ' ' + num(a[1]) + ' L' + num(b[0]) + ' ' + num(b[1]) + ' L' + num(c[0]) + ' ' + num(c[1]),
        deg: Math.round(deg), lx: lp[0], ly: lp[1]
      };
    }
    var last = null;
    return {
      g: g,
      /** Draw the angle for a pose at time `at` (tweens from the previous sample). */
      sample: function (tl, pose, at, dur) {
        var full = !pose ? tibi.fig.state : (pose.j && pose.ch ? pose : RIG.resolve(tibi.fig, pose, tibi.fig.state));
        var q = geom(full);
        if (!last) {
          arc.setAttribute('d', q.arc); legs.setAttribute('d', q.legs);
          labT.setAttribute('x', num(q.lx)); labT.setAttribute('y', num(q.ly + 6)); lab.textContent = q.deg;
          bg.setAttribute('x', num(q.lx - 32)); bg.setAttribute('y', num(q.ly - 15));
        } else {
          var d = dur || 0.3;
          tl.fromTo(arc, { attr: { d: last.arc } }, { attr: { d: q.arc }, duration: d, ease: 'none', immediateRender: false }, at);
          tl.fromTo(legs, { attr: { d: last.legs } }, { attr: { d: q.legs }, duration: d, ease: 'none', immediateRender: false }, at);
          tl.fromTo(labT, { attr: { x: num(last.lx), y: num(last.ly + 6) } }, { attr: { x: num(q.lx), y: num(q.ly + 6) }, duration: d, ease: 'none', immediateRender: false }, at);
          tl.fromTo(lab, { textContent: last.deg }, { textContent: q.deg, snap: { textContent: 1 }, duration: d, ease: 'none', immediateRender: false }, at);
          tl.fromTo(bg, { attr: { x: num(last.lx - 32), y: num(last.ly - 15) } }, { attr: { x: num(q.lx - 32), y: num(q.ly - 15) }, duration: d, ease: 'none', immediateRender: false }, at);
        }
        last = q;
        return at + (dur || 0);
      },
      /** Follow a rig move from one pose to another (same sampling as the rig), n steps. */
      track: function (tl, fromPose, toPose, at, dur, n, ease) {
        var steps = n || 10;
        var poses = RIG.samples(tibi.fig, fromPose, toPose, steps, ease);
        if (!last) this.sample(tl, poses[0], at);
        for (var i = 1; i < poses.length; i++) this.sample(tl, poses[i], at + dur * (i - 1) / steps, dur / steps);
        return at + dur;
      },
      show: function (tl, at) { tl.fromTo(g, { opacity: 0 }, { opacity: 1, duration: 0.3, immediateRender: true }, at); return at + 0.3; },
      hide: function (tl, at) { tl.fromTo(g, { opacity: 1 }, { opacity: 0, duration: 0.3, immediateRender: false }, at); return at + 0.3; }
    };
  };
  /** A force arrow from a point with direction (degrees, 0 = +x, 90 = down) and length. */
  G.bio.force = function (parent, opts) {
    var o = opts || {};
    var g = svg('g', { 'class': 'bio-force', opacity: 0 }, parent);
    var col = o.color || P.cobalt;
    var a = (o.angle === undefined ? 90 : o.angle) * Math.PI / 180, L = o.length || 120;
    var x2 = o.x + Math.cos(a) * L, y2 = o.y + Math.sin(a) * L;
    var shaft = svg('line', { x1: num(o.x), y1: num(o.y), x2: num(x2), y2: num(y2), stroke: col, 'stroke-width': o.width || 7, 'stroke-linecap': 'round' }, g);
    var hl = 22, hw = 14;
    var bx = x2 - Math.cos(a) * hl, by = y2 - Math.sin(a) * hl;
    svg('path', { d: 'M' + num(x2 + Math.cos(a) * 6) + ' ' + num(y2 + Math.sin(a) * 6) + ' L' + num(bx - Math.sin(a) * hw) + ' ' + num(by + Math.cos(a) * hw) + ' L' + num(bx + Math.sin(a) * hw) + ' ' + num(by - Math.cos(a) * hw) + ' Z', fill: col }, g);
    if (o.label) text(g, o.label, { x: num(x2 + (o.labelDx || 14)), y: num(y2 + (o.labelDy || 0)), 'font-family': FONT_D, 'font-weight': 700, 'font-size': o.size || 20, fill: col });
    var len = Math.ceil(L);
    shaft.setAttribute('stroke-dasharray', len + ' ' + len);
    return {
      g: g,
      show: function (tl, at) {
        tl.fromTo(g, { opacity: 0 }, { opacity: 1, duration: 0.2, immediateRender: true }, at);
        tl.fromTo(shaft, { strokeDashoffset: len }, { strokeDashoffset: 0, duration: 0.4, ease: 'power2.out', immediateRender: true }, at);
        return at + 0.4;
      },
      hide: function (tl, at) { tl.fromTo(g, { opacity: 1 }, { opacity: 0, duration: 0.25, immediateRender: false }, at); return at + 0.25; }
    };
  };
  /** Trajectory of a point on the rig through poses (e.g. bar path), drawn on. */
  G.bio.path = function (parent, tibi, joint, local, poses, opts) {
    var o = opts || {};
    var tr = tibi.fig.trace(joint, local, poses, 10);
    var p = svg('path', { d: tr.d, fill: 'none', stroke: o.color || P.spark, 'stroke-width': o.width || 4, 'stroke-linecap': 'round', 'stroke-dasharray': '1 0', opacity: 0 }, parent);
    var len = 0;
    for (var i = 1; i < tr.points.length; i++) len += Math.sqrt(Math.pow(tr.points[i][0] - tr.points[i - 1][0], 2) + Math.pow(tr.points[i][1] - tr.points[i - 1][1], 2));
    len = Math.ceil(len) + 2;
    p.setAttribute('stroke-dasharray', len + ' ' + len);
    return {
      el: p, points: tr.points,
      draw: function (tl, at, dur) {
        tl.fromTo(p, { opacity: 1, strokeDashoffset: len }, { opacity: 1, strokeDashoffset: 0, duration: dur || 1.2, ease: 'none', immediateRender: true }, at);
        return at + (dur || 1.2);
      }
    };
  };
  /**
   * Centre of mass marker from segment masses (Dempster-style proportions, rounded). Conceptual:
   * Tibi's proportions are stylised, so the point is illustrative, not a measurement.
   */
  G.bio.centreOfMass = function (tibi, pose) {
    // segment centres in Tibi's rig units (Cobalt Sculpt: head ~23 above the head joint, upper arm 37,
    // forearm 29, thigh 48, shin 45 along their segments); trunk split between the chest and the pelvis
    var segs = [['head', [0, -23], 0.081], ['chest', [0, -34], 0.286], ['pelvis', [0, 3], 0.212],
      ['shoulderR', [0, 37], 0.028], ['shoulderL', [0, 37], 0.028], ['elbowR', [0, 29], 0.022], ['elbowL', [0, 29], 0.022],
      ['hipR', [0, 48], 0.1], ['hipL', [0, 48], 0.1], ['kneeR', [0, 45], 0.0465], ['kneeL', [0, 45], 0.0465], ['ankleR', [10, 14], 0.0145], ['ankleL', [10, 14], 0.0145]];
    var full = pose ? RIG.normalise(tibi.fig, RIG.lookup(tibi.fig, pose), tibi.fig.state) : tibi.fig.state;
    var x = 0, y = 0, m = 0;
    segs.forEach(function (s) {
      if (!tibi.fig.joints[s[0]]) return;
      var p = RIG.point(tibi.fig, s[0], s[1], full);
      x += p[0] * s[2]; y += p[1] * s[2]; m += s[2];
    });
    return [x / m, y / m];
  };
  G.bio.comMarker = function (parent, x, y, size) {
    var g = svg('g', { 'class': 'bio-com', transform: 'translate(' + num(x) + ' ' + num(y) + ')', opacity: 0 }, parent);
    var r = size || 12;
    svg('circle', { r: r, fill: P.paper, stroke: P.ink, 'stroke-width': 2.4 }, g);
    svg('path', { d: 'M0 ' + (-r) + ' A' + r + ' ' + r + ' 0 0 1 ' + r + ' 0 L0 0 Z M0 ' + r + ' A' + r + ' ' + r + ' 0 0 1 ' + (-r) + ' 0 L0 0 Z', fill: P.ink }, g);
    return g;
  };

  // ------------------------------------------------------------------ science charts
  G.sci = {};
  /**
   * A time-series chart with axes and labelled curves that draw on. series: [{id, points:[[x,y]],
   * color, label, dash}], x and y domains in data units, area: {between:[idA, idB], color}.
   * Returns {g, map(x,y), draw(tl, id, at, dur), axes(tl, at)}.
   */
  G.sci.chart = function (parent, opts) {
    var o = opts || {};
    var x = o.x || 0, y = o.y || 0, w = o.w || 600, h = o.h || 300;
    var dx = o.xDomain || [0, 1], dy = o.yDomain || [0, 1];
    var g = svg('g', { 'class': 'sci-chart', transform: 'translate(' + num(x) + ' ' + num(y) + ')' }, parent);
    function map(px, py) { return [(px - dx[0]) / (dx[1] - dx[0]) * w, h - (py - dy[0]) / (dy[1] - dy[0]) * h]; }
    var axes = svg('g', { opacity: 0 }, g);
    svg('line', { x1: 0, y1: h, x2: w, y2: h, stroke: P.ink, 'stroke-width': 2.4 }, axes);
    svg('line', { x1: 0, y1: 0, x2: 0, y2: h, stroke: P.ink, 'stroke-width': 2.4 }, axes);
    (o.xTicks || []).forEach(function (t) {
      var p = map(t[0], dy[0]);
      svg('line', { x1: p[0], x2: p[0], y1: h, y2: h + 8, stroke: P.ink, 'stroke-width': 2 }, axes);
      text(axes, t[1], { x: num(p[0]), y: h + 28, 'text-anchor': 'middle', 'font-family': FONT_M, 'font-size': o.tickSize || 15, fill: P.ink2 });
    });
    if (o.xLabel) text(axes, o.xLabel, { x: w, y: h + 52, 'text-anchor': 'end', 'font-family': FONT_B, 'font-weight': 600, 'font-size': o.labelSize || 16, fill: P.ink2 });
    if (o.yLabel) text(axes, o.yLabel, { x: 0, y: -14, 'font-family': FONT_B, 'font-weight': 600, 'font-size': o.labelSize || 16, fill: P.ink2 });
    if (o.baseline !== undefined) {
      var by = map(dx[0], o.baseline)[1];
      svg('line', { x1: 0, x2: w, y1: num(by), y2: num(by), stroke: P.ink3, 'stroke-width': 1.6, 'stroke-dasharray': '5 6' }, axes);
    }
    var curves = {};
    var areaEl = null;
    if (o.area) {
      var A1 = o.series.filter(function (s) { return s.id === o.area.between[0]; })[0];
      var A2 = o.series.filter(function (s) { return s.id === o.area.between[1]; })[0];
      var top = A1.points.map(function (p) { return map(p[0], p[1]); });
      var bot = A2.points.map(function (p) { return map(p[0], p[1]); }).reverse();
      areaEl = svg('path', { d: 'M' + top.concat(bot).map(function (p) { return num(p[0]) + ' ' + num(p[1]); }).join(' L') + ' Z', fill: o.area.color || P.emerald, opacity: 0 }, g);
    }
    o.series.forEach(function (s) {
      var pts = s.points.map(function (p) { return map(p[0], p[1]); });
      var d = s.smooth === false ? 'M' + pts.map(function (p) { return num(p[0]) + ' ' + num(p[1]); }).join(' L') : Studio.rig.curve(pts, 0.9);
      var el = svg('path', { d: d, fill: 'none', stroke: s.color || P.ink, 'stroke-width': s.width || 5, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, g);
      if (s.dash) el.setAttribute('stroke-dasharray', s.dash);
      var len = 0;
      for (var i = 1; i < pts.length; i++) len += Math.sqrt(Math.pow(pts[i][0] - pts[i - 1][0], 2) + Math.pow(pts[i][1] - pts[i - 1][1], 2));
      len = Math.ceil(len * 1.08) + 4;
      if (!s.dash) { el.setAttribute('stroke-dasharray', len + ' ' + len); el.setAttribute('stroke-dashoffset', len); }
      else el.setAttribute('opacity', 0);
      var lab = null;
      if (s.label) {
        var lp = pts[s.labelAt === undefined ? pts.length - 1 : s.labelAt];
        lab = text(g, s.label, { x: num(lp[0] + (s.labelDx || 10)), y: num(lp[1] + (s.labelDy || 6)), 'font-family': FONT_D, 'font-weight': 700, 'font-size': o.seriesLabelSize || 19, fill: s.color || P.ink, opacity: 0 });
      }
      curves[s.id] = { el: el, len: len, label: lab, dash: s.dash, points: pts };
    });
    return {
      g: g, map: map, curves: curves, area: areaEl,
      axes: function (tl, at) { tl.fromTo(axes, { opacity: 0 }, { opacity: 1, duration: 0.4, immediateRender: true }, at); return at + 0.4; },
      draw: function (tl, id, at, dur) {
        var c = curves[id];
        if (c.dash) tl.fromTo(c.el, { opacity: 0 }, { opacity: 1, duration: dur || 0.6, immediateRender: true }, at);
        else tl.fromTo(c.el, { strokeDashoffset: c.len }, { strokeDashoffset: 0, duration: dur || 1.4, ease: 'power1.inOut', immediateRender: true }, at);
        if (c.label) tl.fromTo(c.label, { opacity: 0 }, { opacity: 1, duration: 0.3, immediateRender: true }, at + (dur || 1.4) * 0.8);
        return at + (dur || 1.4);
      },
      fillArea: function (tl, at, opacity) { tl.fromTo(areaEl, { opacity: 0 }, { opacity: opacity || 0.22, duration: 0.6, immediateRender: true }, at); return at + 0.6; }
    };
  };
  /**
   * A left-to-right signalling flow: nodes [{id, label, sub, color}] in boxes joined by arrows.
   * light(tl, i, at) lights node i and the arrow into it. Keep labels to one or two words.
   */
  G.sci.flow = function (parent, opts) {
    var o = opts || {};
    var g = svg('g', { 'class': 'sci-flow', transform: 'translate(' + num(o.x || 0) + ' ' + num(o.y || 0) + ')' }, parent);
    var nodes = o.nodes || [];
    var bw = o.boxW || 190, bh = o.boxH || 84, gap = o.gap || 60;
    var vertical = !!o.vertical;
    var els = nodes.map(function (n, i) {
      var nx = vertical ? 0 : i * (bw + gap), ny = vertical ? i * (bh + gap) : 0;
      var ng = svg('g', { opacity: 0.25 }, g);
      var box = svg('rect', { x: nx, y: ny, width: bw, height: bh, rx: 18, fill: P.paper, stroke: n.color || P.ink, 'stroke-width': 3 }, ng);
      text(ng, n.label, { x: num(nx + bw / 2), y: num(ny + (n.sub ? bh * 0.45 : bh * 0.58)), 'text-anchor': 'middle', 'font-family': FONT_D, 'font-weight': 800, 'font-size': o.size || 24, fill: P.ink });
      if (n.sub) text(ng, n.sub, { x: num(nx + bw / 2), y: num(ny + bh * 0.78), 'text-anchor': 'middle', 'font-family': FONT_B, 'font-weight': 500, 'font-size': (o.size || 24) * 0.62, fill: P.ink2 });
      var arrow = null;
      if (i > 0) {
        var ax1 = vertical ? bw / 2 : nx - gap + 8, ay1 = vertical ? ny - gap + 8 : bh / 2;
        var ax2 = vertical ? bw / 2 : nx - 10, ay2 = vertical ? ny - 10 : bh / 2;
        arrow = svg('g', { opacity: 0.25 }, g);
        svg('line', { x1: ax1, y1: ay1, x2: ax2 - (vertical ? 0 : 10), y2: ay2 - (vertical ? 10 : 0), stroke: P.ink, 'stroke-width': 4, 'stroke-linecap': 'round' }, arrow);
        svg('path', { d: vertical ? 'M' + (ax2 - 10) + ' ' + (ay2 - 12) + ' L' + ax2 + ' ' + ay2 + ' L' + (ax2 + 10) + ' ' + (ay2 - 12) + ' Z' : 'M' + (ax2 - 12) + ' ' + (ay2 - 10) + ' L' + ax2 + ' ' + ay2 + ' L' + (ax2 - 12) + ' ' + (ay2 + 10) + ' Z', fill: P.ink }, arrow);
      }
      return { g: ng, box: box, arrow: arrow, color: n.color || P.ink, x: nx, y: ny };
    });
    return {
      g: g, nodes: els,
      light: function (tl, i, at) {
        var n = els[i];
        if (n.arrow) tl.fromTo(n.arrow, { opacity: 0.25 }, { opacity: 1, duration: 0.3, immediateRender: false }, at);
        tl.fromTo(n.g, { opacity: 0.25 }, { opacity: 1, duration: 0.35, immediateRender: false }, at + 0.15);
        tl.fromTo(n.box, { attr: { fill: P.paper } }, { attr: { fill: n.color === P.ink ? P.paper2 : n.color }, duration: 0.35, immediateRender: false }, at + 0.15);
        tl.fromTo(n.box, { attr: { 'fill-opacity': 1 } }, { attr: { 'fill-opacity': 0.18 }, duration: 0.35, immediateRender: false }, at + 0.15);
        return at + 0.5;
      }
    };
  };
})(typeof window !== 'undefined' ? window : this);
