/*
 * Motion Lab mythic kit (src/studio/kits/mythic/mythic.js) - Studio.kit.mythic
 *
 * Building blocks for the mythic-tale style template (myths, legends and sacred stories told
 * as a storyteller's performance): lamp-lit paper dioramas, deckle-edged cut sheets, public-domain
 * photo plates with paper borders, haloes, ornamental borders, kaavad doors, phad scrolls,
 * jointed shadow puppets and flower showers. Load after studio-core/draw/type/motion.
 * Guide: .claude/skills/mythic-tales/references/scene-recipes.md
 *
 * Structure of every piece (so tweens never fight over one transform):
 *   piece.el   holder <div>, absolutely positioned; free for travel moves (walk across the stage)
 *   piece.art  <svg> inside it; entrances and exits (place, rise, lift) animate this
 *   piece.body <g> inside the svg; ambient life (breathe, sway) animates this
 * Put pieces inside stage layers (stage.layer(depth)) and move the camera with
 * Studio.space.camera(tl, stage.el, at, {...}) for parallax.
 *
 * Determinism: seeded Studio.rng / Studio.noise1 only, finite tweens, fromTo everywhere.
 */
(function (global) {
  'use strict';

  var Studio = global.Studio || (global.Studio = {});
  var KIT = Studio.kit = Studio.kit || {};
  var M = KIT.mythic = KIT.mythic || {};
  M.version = '0.5.0';   // 0.5.0: part transforms (tf), gradient fills, parts kept in every look (armoury.js weapons and auras). 0.4.0: 'illustrated' look and painted part layers (figures-human.js). 0.3.0: heroic builds of every figure (figures.js). 0.2.0: figure library (figures.js), paper cut-outs, tradition motif sets, friezes and registers, stepped "on twos" motion

  var seedCounter = 0;
  // Kit tokens every mythic style defines; outside them (e.g. editorial-light) fall back to core tokens.
  var FALLBACK = {
    '--c-gold': 'var(--c-accent-3)', '--c-gold-light': 'var(--c-accent-3)', '--c-lamp': 'rgba(255,170,70,0.2)',
    '--c-malachite': 'var(--c-positive, var(--c-accent-2))', '--c-sky': 'var(--c-paper-2)', '--c-lotus': 'var(--c-accent)',
    '--c-saffron': 'var(--c-accent-3)', '--c-night': 'var(--c-ink)', '--c-shadow': 'rgba(0,0,0,0.25)',
    '--c-leather-red': 'var(--c-accent)', '--c-leather-ochre': 'var(--c-accent-3)',
    '--c-leather-green': 'var(--c-positive, var(--c-accent-2))', '--c-leather-blue': 'var(--c-accent-2)'
  };
  function nextSeed(o) { return (o && o.seed) || (7919 + (seedCounter++) * 131); }
  function opt(o, k, d) { return o && o[k] !== undefined ? o[k] : d; }
  function r2(n) { return Math.round(n * 100) / 100; }
  function paint(v) {
    if (!v || v.indexOf('--') !== 0) return v;
    return 'var(' + v + (FALLBACK[v] ? ', ' + FALLBACK[v] : '') + ')';
  }
  function resolve(v) {
    if (!v || v.indexOf('--') !== 0) return v;
    var t = Studio.token(v, '');
    if (!t && FALLBACK[v]) {
      var m = /var\((--[a-z0-9-]+)/.exec(FALLBACK[v]);
      t = m ? Studio.token(m[1], '') : FALLBACK[v];
    }
    return t || '#888888';
  }
  function art(p) { return p && p.art ? p.art : p; }
  function body(p) { return p && p.body ? p.body : p; }
  function list(t) { return (t && t.length !== undefined && !t.nodeType && !t.art) ? Array.prototype.slice.call(t) : [t]; }
  function gs() { return global.gsap; }

  function hexRgb(hex) {
    var h = String(hex).trim();
    var m = /^rgba?\(([^)]+)\)/.exec(h);
    if (m) { var p = m[1].split(','); return [parseFloat(p[0]) / 255, parseFloat(p[1]) / 255, parseFloat(p[2]) / 255]; }
    h = h.replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    return [parseInt(h.slice(0, 2), 16) / 255, parseInt(h.slice(2, 4), 16) / 255, parseInt(h.slice(4, 6), 16) / 255];
  }

  // ------------------------------------------------------------------ shared CSS and SVG defs
  var KIT_CSS = [
    '.mx-stage{position:absolute;inset:0;overflow:hidden}',
    '.mx-ground{position:absolute;inset:0;background:var(--c-paper)}',
    '.mx-ground svg{position:absolute;inset:0;width:100%;height:100%}',
    '.mx-piece{position:absolute}',
    '.mx-piece>svg{position:absolute;left:0;top:0;width:100%;height:100%;overflow:visible}',
    '.mx-lamp,.mx-vignette{position:absolute;inset:0;pointer-events:none}',
    '.mx-vignette{mix-blend-mode:multiply}',
    '.mx-doors{position:absolute;perspective:calc(var(--u) * 160)}',
    '.mx-leaf{position:absolute;top:0;height:100%;width:50%;backface-visibility:hidden;background:var(--c-paper-2);',
    '  box-shadow:inset 0 0 0 calc(var(--u)*0.5) var(--c-gold,var(--c-accent-3)),inset 0 0 0 calc(var(--u)*1.1) var(--c-paper-2),',
    '  inset 0 0 0 calc(var(--u)*1.4) var(--c-accent);}',
    '.mx-leaf>svg{position:absolute;inset:0;width:100%;height:100%}',
    '.mx-scroll{position:absolute}',
    '.mx-frieze,.mx-registers{position:absolute;overflow:hidden}',
    '.mx-frieze-track{position:absolute;left:0;top:0;height:100%}',
    '.mx-panel{position:absolute;overflow:hidden}',
    '.mx-scroll-view{position:absolute;inset:0;overflow:hidden;background:var(--c-paper-2)}',
    '.mx-roller{position:absolute;top:calc(var(--u)*-1.2);bottom:calc(var(--u)*-1.2);width:calc(var(--u)*2.2);',
    '  border-radius:calc(var(--u)*1.1);background:linear-gradient(90deg,var(--c-ink-2),var(--c-accent-3) 45%,var(--c-ink-2));',
    '  box-shadow:0 calc(var(--u)*0.4) calc(var(--u)*0.8) var(--c-shadow)}',
    '.mx-cartouche{position:absolute;display:flex;flex-direction:column;gap:calc(var(--u)*0.6);color:var(--c-ink)}',
    '.mx-cartouche .mx-k{font-family:var(--font-text);font-size:calc(var(--u)*2.9);letter-spacing:var(--track-kicker);text-transform:uppercase;color:var(--c-ink-2)}',
    '.mx-cartouche .mx-t{font-family:var(--font-display);font-weight:var(--fw-heading);font-size:calc(var(--u)*4.4);line-height:1.1}',
    '.mx-cartouche .mx-rule{height:calc(var(--u)*0.35);background:var(--c-accent);transform-origin:0 50%}',
    '.mx-title{position:absolute;left:var(--safe-left);right:var(--safe-right);text-align:center;color:var(--c-ink)}',
    '.mx-title .mx-k{font-family:var(--font-text);font-size:calc(var(--u)*3.0);letter-spacing:var(--track-kicker);text-transform:uppercase;color:var(--c-accent)}',
    '.mx-title .mx-t{font-family:var(--font-display);font-weight:var(--fw-display);letter-spacing:var(--track-display);font-size:calc(var(--u)*9);line-height:1.02;margin-top:calc(var(--u)*1.2)}',
    '.mx-title .mx-s{font-family:var(--font-text);font-style:italic;font-size:calc(var(--u)*3.6);color:var(--c-ink-2);margin-top:calc(var(--u)*1.6)}',
    '.mx-title .mx-w{display:inline-block}',
    '.mx-plate{background:color-mix(in srgb,var(--c-paper) 93%,transparent);padding:calc(var(--u)*1.4) calc(var(--u)*2.2);',
    '  border-radius:calc(var(--u)*0.4);box-shadow:calc(var(--u)*0.3) calc(var(--u)*0.5) calc(var(--u)*1.2) var(--c-shadow,rgba(0,0,0,0.25))}',
    '.mx-title.mx-plate{left:calc(var(--safe-left) + var(--u)*2);right:calc(var(--safe-right) + var(--u)*2)}',
    '.mx-credit{position:absolute;right:var(--safe-right);bottom:var(--safe-bottom);font-family:var(--font-text);',
    '  font-size:calc(var(--u)*2.7);color:var(--c-ink-2);text-align:right;max-width:64%;',
    '  background:color-mix(in srgb,var(--c-paper) 93%,transparent);padding:calc(var(--u)*0.6) calc(var(--u)*1.2);border-radius:calc(var(--u)*0.3)}'
  ].join('\n');

  M.defs = function () {
    if (!document.getElementById('mx-kit-style')) {
      var st = document.createElement('style');
      st.id = 'mx-kit-style';
      st.textContent = KIT_CSS;
      document.head.appendChild(st);
    }
    var existing = document.getElementById('mx-defs');
    if (existing) return existing;
    var u = Studio.u(1);
    var svg = Studio.svg('svg', { id: 'mx-defs', width: 0, height: 0, 'aria-hidden': 'true', style: 'position:absolute;width:0;height:0' });
    var defs = Studio.svg('defs', null, svg);
    var fib = Studio.svg('filter', { id: 'mx-fibre', x: '0', y: '0', width: '100%', height: '100%', 'color-interpolation-filters': 'sRGB' }, defs);
    Studio.svg('feTurbulence', { type: 'fractalNoise', baseFrequency: '0.85 0.55', numOctaves: '2', seed: '11', result: 't' }, fib);
    Studio.svg('feColorMatrix', { 'in': 't', type: 'matrix', values: '0 0 0 0 0.18  0 0 0 0 0.12  0 0 0 0 0.07  0.42 0 0 0 -0.12', result: 'f' }, fib);
    Studio.svg('feComposite', { 'in': 'f', in2: 'SourceAlpha', operator: 'in', result: 'fc' }, fib);
    var mg = Studio.svg('feMerge', null, fib);
    Studio.svg('feMergeNode', { 'in': 'SourceGraphic' }, mg);
    Studio.svg('feMergeNode', { 'in': 'fc' }, mg);
    var soft = Studio.svg('filter', { id: 'mx-soft', x: '-20%', y: '-20%', width: '140%', height: '140%' }, defs);
    Studio.svg('feGaussianBlur', { stdDeviation: String(r2(u * 0.45)) }, soft);
    var glow = Studio.svg('filter', { id: 'mx-glow', x: '-40%', y: '-40%', width: '180%', height: '180%' }, defs);
    Studio.svg('feGaussianBlur', { 'in': 'SourceGraphic', stdDeviation: String(r2(u * 1.2)), result: 'b' }, glow);
    var gm = Studio.svg('feMerge', null, glow);
    Studio.svg('feMergeNode', { 'in': 'b' }, gm);
    Studio.svg('feMergeNode', { 'in': 'SourceGraphic' }, gm);
    var sticker = Studio.svg('filter', { id: 'mx-sticker', x: '-10%', y: '-10%', width: '120%', height: '120%', 'color-interpolation-filters': 'sRGB' }, defs);
    Studio.svg('feMorphology', { 'in': 'SourceAlpha', operator: 'dilate', radius: String(r2(u * 0.7)), result: 'd' }, sticker);
    Studio.svg('feFlood', { 'flood-color': resolve('--c-paper') || '#f4ecdd', result: 'w' }, sticker);
    Studio.svg('feComposite', { 'in': 'w', in2: 'd', operator: 'in', result: 'edge' }, sticker);
    var sm = Studio.svg('feMerge', null, sticker);
    Studio.svg('feMergeNode', { 'in': 'edge' }, sm);
    Studio.svg('feMergeNode', { 'in': 'SourceGraphic' }, sm);
    // Lifted paper figure: a soft drop shadow under the whole cut-out.
    var lift = Studio.svg('filter', { id: 'mx-lift', x: '-15%', y: '-15%', width: '130%', height: '130%', 'color-interpolation-filters': 'sRGB' }, defs);
    Studio.svg('feDropShadow', { dx: String(r2(u * 0.3)), dy: String(r2(u * 0.55)), stdDeviation: String(r2(u * 0.45)), 'flood-color': resolve('--c-ink') || '#2b1d14', 'flood-opacity': '0.32' }, lift);
    document.body.insertBefore(svg, document.body.firstChild);
    return svg;
  };

  /** Duotone filter id for an image: shadows to `dark`, highlights to `light` (tokens or hex). */
  M.duotone = function (dark, light) {
    var defs = M.defs().querySelector('defs');
    var a = hexRgb(resolve(dark || '--c-ink')), b = hexRgb(resolve(light || '--c-paper'));
    var id = 'mx-duo-' + Studio.hash(a.join(',') + '|' + b.join(','));
    if (document.getElementById(id)) return id;
    var f = Studio.svg('filter', { id: id, 'color-interpolation-filters': 'sRGB' }, defs);
    Studio.svg('feColorMatrix', { type: 'matrix', values: '0.33 0.33 0.33 0 0  0.33 0.33 0.33 0 0  0.33 0.33 0.33 0 0  0 0 0 1 0' }, f);
    var ct = Studio.svg('feComponentTransfer', null, f);
    ['R', 'G', 'B'].forEach(function (c, i) {
      Studio.svg('feFunc' + c, { type: 'table', tableValues: r2(a[i]) + ' ' + r2(b[i]) }, ct);
    });
    return id;
  };

  /** Gold-leaf gradient for fills; returns 'url(#id)'. Animate the shine with M.glint. */
  M.gold = function (w, id) {
    var defs = M.defs().querySelector('defs');
    var gid = id || ('mx-gold-' + (seedCounter++));
    var g = Studio.svg('linearGradient', { id: gid, gradientUnits: 'userSpaceOnUse', x1: String(-w), y1: '0', x2: '0', y2: String(r2(w * 0.35)) }, defs);
    [[0, '--c-gold'], [0.42, '--c-gold'], [0.5, '--c-gold-light'], [0.58, '--c-gold'], [1, '--c-gold']].forEach(function (s) {
      Studio.svg('stop', { offset: String(s[0]), 'stop-color': resolve(s[1]) || '#c8961e' }, g);
    });
    g.__mxWidth = w;
    return 'url(#' + gid + ')';
  };

  // ------------------------------------------------------------------ geometry
  /** Seeded rough edge: subdivides a polygon and pushes points off the line (deckle / scissor cut). */
  M.roughen = function (pts, opts) {
    var o = opts || {};
    var closed = o.closed !== false;
    var amp = o.amp === undefined ? Studio.u(0.35) : o.amp;
    var step = o.step || Studio.u(1.1);
    var rng = Studio.rng(o.seed || 5);
    var nz = Studio.noise1((o.seed || 5) + 77);
    var out = [], n = pts.length, segs = closed ? n : n - 1, s = 0;
    for (var i = 0; i < segs; i++) {
      var a = pts[i], b = pts[(i + 1) % n];
      var dx = b[0] - a[0], dy = b[1] - a[1], L = Math.sqrt(dx * dx + dy * dy) || 1;
      var k = Math.max(1, Math.round(L / step)), nx = -dy / L, ny = dx / L;
      for (var j = 0; j < k; j++) {
        var t = j / k;
        s += L / k;
        var off = (nz(s / (step * 4)) * 0.65 + (rng() * 2 - 1) * 0.35) * amp;
        out.push([a[0] + dx * t + nx * off, a[1] + dy * t + ny * off]);
      }
    }
    if (!closed) out.push(pts[n - 1]);
    return out;
  };

  function d(polys) {
    return polys.map(function (pts) {
      return 'M' + pts.map(function (p) { return r2(p[0]) + ' ' + r2(p[1]); }).join('L') + 'Z';
    }).join(' ');
  }
  M.pathData = d;

  function sampleArc(cx, cy, rx, ry, a0, a1, n) {
    var out = [];
    for (var i = 0; i <= n; i++) {
      var a = a0 + (a1 - a0) * i / n;
      out.push([cx + Math.cos(a) * rx, cy + Math.sin(a) * ry]);
    }
    return out;
  }

  /** Shape library in a w x h box. Each returns {polys: [[x,y]...][], rule: 'nonzero'|'evenodd'}. */
  M.shapes = {
    rect: function (w, h) { return { polys: [[[0, 0], [w, 0], [w, h], [0, h]]] }; },
    hills: function (w, h, rng, o) {
      var top = [], n = 48, base = h * opt(o, 'level', 0.38);
      var waves = [[1 + rng() * 0.6, rng() * 6.28, h * 0.12], [2.3 + rng(), rng() * 6.28, h * 0.06], [4.1 + rng() * 2, rng() * 6.28, h * 0.025]];
      for (var i = 0; i <= n; i++) {
        var x = w * i / n, y = base;
        waves.forEach(function (wv) { y -= Math.sin(wv[0] * Math.PI * i / n + wv[1]) * wv[2]; });
        top.push([x, Math.max(0, y)]);
      }
      return { polys: [top.concat([[w, h], [0, h]])] };
    },
    peaks: function (w, h, rng, o) {
      var n = opt(o, 'peaks', 4), pts = [[0, h * (0.45 + rng() * 0.2)]];
      for (var i = 1; i < n * 2; i++) {
        var x = w * i / (n * 2) + (rng() * 2 - 1) * w / (n * 8);
        pts.push([x, i % 2 ? h * (0.02 + rng() * 0.25) : h * (0.4 + rng() * 0.2)]);
      }
      pts.push([w, h * (0.45 + rng() * 0.2)]);
      return { polys: [pts.concat([[w, h], [0, h]])] };
    },
    waves: function (w, h, rng, o) {
      var c = opt(o, 'crests', 5), top = [], n = c * 16, ph = rng() * 6.28;
      for (var i = 0; i <= n; i++) {
        var s = Math.sin(c * 2 * Math.PI * i / n + ph);
        top.push([w * i / n, h * 0.35 - (s < 0 ? -1 : 1) * Math.pow(Math.abs(s), 0.6) * h * 0.22]);
      }
      return { polys: [top.concat([[w, h], [0, h]])] };
    },
    clouds: function (w, h, rng, o) {
      var n = opt(o, 'puffs', 5), pts = [[0, h * 0.85]], x = 0, step = w / n;
      for (var i = 0; i < n; i++) {
        var rx = step / 2, ry = h * (0.3 + rng() * 0.45);
        pts = pts.concat(sampleArc(x + rx, h * 0.85, rx, ry, Math.PI, 2 * Math.PI, 14));
        x += step;
      }
      pts.push([w, h * 0.85]);
      pts = pts.concat(sampleArc(w / 2, h * 0.85, w / 2, h * 0.12, 0, Math.PI, 20));
      return { polys: [pts] };
    },
    disc: function (w, h) { return { polys: [sampleArc(w / 2, h / 2, w / 2, h / 2, 0, 2 * Math.PI, 72).slice(0, 72)] }; },
    niche: function (w, h) {
      var r = w / 2, pts = [[0, h], [0, r]].concat(sampleArc(r, r, r, r, Math.PI, 2 * Math.PI, 32)).concat([[w, r], [w, h]]);
      return { polys: [pts] };
    },
    arch: function (w, h, rng, o) {
      var t = w * opt(o, 'thickness', 0.16), spring = h * opt(o, 'spring', 0.42);
      var iw = w - 2 * t, r = iw / 2, inner = [[t, h], [t, spring]];
      if (opt(o, 'pointed', false)) {
        inner = inner.concat(sampleArc(t + iw, spring, iw, iw * 0.9, Math.PI, Math.PI * 1.32, 14))
          .concat(sampleArc(t, spring, iw, iw * 0.9, Math.PI * 1.68, Math.PI * 2, 14));
      } else {
        inner = inner.concat(sampleArc(t + r, spring, r, Math.min(r, spring - h * 0.06), Math.PI, 2 * Math.PI, 28));
      }
      inner = inner.concat([[w - t, spring], [w - t, h]]);
      return { polys: [[[0, 0], [w, 0], [w, h], [0, h]], inner.reverse()], rule: 'evenodd' };
    },
    flames: function (w, h, rng, o) {
      var n = opt(o, 'tongues', 7), pts = [[0, h]], step = w / n;
      for (var i = 0; i < n; i++) {
        var x0 = i * step, x1 = x0 + step, tipX = x0 + step * (0.5 + (rng() * 2 - 1) * 0.25), tipY = h * (0.02 + rng() * 0.35);
        for (var k = 1; k <= 6; k++) {
          var t = k / 6;
          pts.push([x0 + (tipX - x0) * t + Math.sin(t * Math.PI) * step * 0.18, h - (h - tipY) * Math.pow(t, 1.4)]);
        }
        for (var q = 1; q <= 6; q++) {
          var s = q / 6;
          pts.push([tipX + (x1 - tipX) * s + Math.sin(s * Math.PI) * step * 0.1, tipY + (h * 0.75 - tipY) * Math.pow(s, 0.7)]);
        }
      }
      pts.push([w, h]);
      return { polys: [pts] };
    },
    lotus: function (w, h, rng, o) {
      var n = opt(o, 'petals', 7), polys = [], cx = w / 2, order = [];
      for (var i = 0; i < n; i++) order.push(i);
      order.sort(function (a, b) { return Math.abs(b - (n - 1) / 2) - Math.abs(a - (n - 1) / 2); });
      order.forEach(function (i2) {
        var ang = (-70 + 140 * i2 / (n - 1)) * Math.PI / 180;
        var L = h * (0.96 - Math.abs(i2 - (n - 1) / 2) / n * 0.5), wd = L * 0.3, pet = [];
        for (var k = 0; k <= 16; k++) {
          var t = k / 16;
          pet.push([Math.sin(t * Math.PI) * wd * (1 - t * 0.35), -t * L]);
        }
        for (var q = 15; q > 0; q--) {
          var t2 = q / 16;
          pet.push([-Math.sin(t2 * Math.PI) * wd * (1 - t2 * 0.35), -t2 * L]);
        }
        polys.push(pet.map(function (p) {
          return [cx + p[0] * Math.cos(ang) - p[1] * Math.sin(ang), h + p[0] * Math.sin(ang) + p[1] * Math.cos(ang)];
        }));
      });
      return { polys: polys };
    }
  };

  // ------------------------------------------------------------------ stage, lamp, credit
  /**
   * Diorama stage inside a scene: paper ground (optional fibre and tint) and depth layers.
   * opts {ground (token or colour), fibre (true)}. Returns {el, ground, layer(depth)}.
   */
  M.stage = function (parent, opts) {
    M.defs();
    var o = opts || {};
    var el = Studio.el('div', 'mx-stage', null, parent);
    var ground = Studio.el('div', 'mx-ground', null, el);
    var groundPaint = paint(o.ground || '--c-paper');
    ground.style.background = groundPaint;
    if (o.fibre !== false) {
      var f = Studio.format;
      var gsv = Studio.svg('svg', { viewBox: '0 0 ' + f.width + ' ' + f.height, preserveAspectRatio: 'none', 'aria-hidden': 'true' }, ground);
      var rect = Studio.svg('rect', { width: f.width, height: f.height, filter: 'url(#mx-fibre)' }, gsv);
      rect.style.fill = groundPaint;
    }
    var layers = {};
    return {
      el: el,
      ground: ground,
      layer: function (depth) {
        var k = Math.max(0, Math.min(5, depth === undefined ? 3 : depth));
        if (!layers[k]) {
          layers[k] = Studio.el('div', 'st-layer', null, el);
          layers[k].setAttribute('data-depth', String(k));
          layers[k].style.zIndex = String(10 + k);
        }
        return layers[k];
      }
    };
  };

  /**
   * Lamp light: warm glow plus edge vignette over `parent`. opts {x, y (0-1), radius (0-1), strength,
   * vignette, color}. Both layers are twice the frame so M.lampTo can carry the light across a
   * scroll (the Bhopi lifting her lamp to each Phad scene).
   */
  M.lamp = function (parent, opts) {
    M.defs();
    var o = opts || {};
    var f = Studio.format;
    var mk = function (cls) {
      var el = Studio.el('div', cls, null, parent);
      el.style.inset = 'auto';
      el.style.left = (-f.width / 2) + 'px';
      el.style.top = (-f.height / 2) + 'px';
      el.style.width = (f.width * 2) + 'px';
      el.style.height = (f.height * 2) + 'px';
      el.style.zIndex = String(opt(o, 'z', 40));
      return el;
    };
    var vig = mk('mx-vignette');
    vig.style.background = 'radial-gradient(ellipse 50% 50% at 50% 50%, rgba(0,0,0,0) 42%, rgba(60,30,10,' + opt(o, 'vignette', 0.3) + ') 100%)';
    var glow = mk('mx-lamp');
    glow.style.background = 'radial-gradient(circle at 50% 50%, ' + paint(o.color || '--c-lamp') + ' 0%, rgba(0,0,0,0) ' + r2(opt(o, 'radius', 0.62) * 50) + '%)';
    var pos = { x: (opt(o, 'x', 0.5) - 0.5) * f.width, y: (opt(o, 'y', 0.42) - 0.5) * f.height };
    gs().set([glow, vig], pos);
    return { el: glow, glow: glow, vignette: vig, strength: opt(o, 'strength', 1), pos: pos };
  };

  /** Carry the lamp to a new point (x, y as 0-1 of the frame); chains from the previous position. */
  M.lampTo = function (tl, lamp, at, opts) {
    var o = opts || {};
    var f = Studio.format, dur = opt(o, 'duration', 1.6);
    var next = { x: (opt(o, 'x', 0.5) - 0.5) * f.width, y: (opt(o, 'y', 0.42) - 0.5) * f.height };
    tl.fromTo([lamp.glow, lamp.vignette], { x: lamp.pos.x, y: lamp.pos.y }, { x: next.x, y: next.y, duration: dur, ease: o.ease || 'sine.inOut', immediateRender: false }, at);
    lamp.pos = next;
    return at + dur;
  };

  /**
   * Palette swap for a moment of threat or grief (after Cartoon Saloon's danger palette): a colour
   * layer over `parent` fades in at `from` and out at `to`. opts {color '--c-accent', blend 'color',
   * amount 0.8, fade 0.6, z}.
   */
  M.tint = function (tl, parent, from, to, opts) {
    var o = opts || {};
    var el = Studio.el('div', 'mx-lamp', null, parent);
    el.style.background = paint(o.color || '--c-accent');
    el.style.mixBlendMode = o.blend || 'color';
    el.style.zIndex = String(opt(o, 'z', 39));
    var fade = opt(o, 'fade', 0.6), amt = opt(o, 'amount', 0.8);
    gs().set(el, { autoAlpha: 0 });
    tl.fromTo(el, { autoAlpha: 0 }, { autoAlpha: amt, duration: fade, ease: 'power1.inOut', immediateRender: false }, from);
    tl.fromTo(el, { autoAlpha: amt }, { autoAlpha: 0, duration: fade, ease: 'power1.inOut', immediateRender: false }, Math.max(from + fade, to - fade));
    return { el: el };
  };

  /**
   * Lamp flicker between `from` and `to`: seeded noise sampled `fps` times a second, one explicit
   * tween per step (seek-safe). opts {fps 6, amount 0.18, seed}.
   */
  M.flicker = function (tl, lamp, from, to, opts) {
    var o = opts || {};
    var fps = opt(o, 'fps', 6), amount = opt(o, 'amount', 0.18), step = 1 / fps;
    var nz = Studio.noise1(nextSeed(o)), base = lamp.strength;
    var n = Math.floor((to - from) / step), prev = base, prevV = 1;
    gs().set(lamp.glow, { opacity: base });
    for (var k = 1; k <= n; k++) {
      var v = Math.max(0, Math.min(1.2, base * (1 + nz(k * 0.37) * amount * 2)));
      var vv = 1 - nz(k * 0.37 + 50) * amount * 0.6;
      tl.fromTo(lamp.glow, { opacity: prev }, { opacity: v, duration: step, ease: 'sine.inOut', immediateRender: false }, from + (k - 1) * step);
      tl.fromTo(lamp.vignette, { opacity: prevV }, { opacity: vv, duration: step, ease: 'sine.inOut', immediateRender: false }, from + (k - 1) * step);
      prev = v;
      prevV = vv;
    }
    return to;
  };

  /** Source line for a plate or a quotation (e.g. "The Met, 28.105 · Public domain"). Sized at the text floor. */
  M.credit = function (parent, text) {
    M.defs();
    return Studio.el('div', 'mx-credit', text, parent);
  };

  // ------------------------------------------------------------------ pieces
  function piece(parent, o, w, h) {
    M.defs();
    var el = Studio.el('div', 'mx-piece', null, parent);
    el.style.left = r2(opt(o, 'x', 0)) + 'px';
    el.style.top = r2(opt(o, 'y', 0)) + 'px';
    el.style.width = r2(w) + 'px';
    el.style.height = r2(h) + 'px';
    if (o.z !== undefined) el.style.zIndex = String(o.z);
    if (o.id) el.id = o.id;
    var svg = Studio.svg('svg', { viewBox: '0 0 ' + r2(w) + ' ' + r2(h), 'aria-hidden': 'true' }, el);
    var g = Studio.svg('g', { 'class': 'mx-body' }, svg);
    return { el: el, art: svg, body: g, w: w, h: h };
  }

  /**
   * Cut-paper sheet. opts {shape: rect|hills|peaks|waves|clouds|disc|niche|arch|flames|lotus,
   * x, y, w, h (px), fill (token or colour), deckle (amp in u, 0 = clean scissor cut), seed,
   * shadow (false or {x, y in u, opacity}), fibre (true), edge (light cut-edge line, true),
   * stroke (ink outline colour, optional), d (custom path data in the w x h box, e.g. a traced
   * silhouette; replaces the shape)} plus shape options (peaks, crests, petals, ...).
   */
  M.sheet = function (parent, opts) {
    var o = opts || {};
    var w = opt(o, 'w', Studio.u(40)), h = opt(o, 'h', Studio.u(20));
    var p = piece(parent, o, w, h);
    var seed = nextSeed(o), rng = Studio.rng(seed);
    var shape = (M.shapes[o.shape || 'rect'] || M.shapes.rect)(w, h, rng, o);
    var amp = Studio.u(opt(o, 'deckle', 0.35));
    var polys = amp > 0 ? shape.polys.map(function (pts, i) { return M.roughen(pts, { amp: amp, seed: seed + i * 7 }); }) : shape.polys;
    var dd = o.d || d(polys), rule = o.d ? (o.rule || 'nonzero') : (shape.rule || 'nonzero');
    var sh = opt(o, 'shadow', {});
    if (sh) {
      var sx = Studio.u(opt(sh, 'x', 0.4)), sy = Studio.u(opt(sh, 'y', 0.7));
      p.shadow = Studio.svg('path', { d: dd, 'fill-rule': rule, filter: 'url(#mx-soft)', opacity: String(opt(sh, 'opacity', 1)) }, p.body);
      p.shadow.style.fill = 'var(--c-shadow)';
      gs().set(p.shadow, { x: sx, y: sy });
      p.shadowOffset = [sx, sy];
    }
    p.path = Studio.svg('path', { d: dd, 'fill-rule': rule }, p.body);
    p.path.style.fill = paint(o.fill || '--c-paper-2');
    if (o.fibre !== false) p.path.setAttribute('filter', 'url(#mx-fibre)');
    if (o.stroke) {
      p.path.style.stroke = paint(o.stroke);
      p.path.style.strokeWidth = String(r2(Studio.u(opt(o, 'strokeWidth', 0.3))));
      p.path.style.strokeLinejoin = 'round';
    } else if (o.edge !== false) {
      var edge = Studio.svg('path', { d: dd, 'fill-rule': rule, fill: 'none' }, p.body);
      edge.style.stroke = 'rgba(255,250,240,0.55)';
      edge.style.strokeWidth = String(r2(Studio.u(0.16)));
    }
    return p;
  };

  /**
   * Photo plate from a public-domain or licensed image (asset path relative to src/). opts
   * {src, x, y, w, h, frame: rect|niche|disc|cutout, duotone: [dark, light] | false,
   * border (paper margin in u, 1.2), deckle, seed, fit: 'slice'|'meet', shadow, mat}. 'cutout'
   * expects a PNG with alpha and draws a sticker edge round the subject. Always add a credit line.
   */
  M.plate = function (parent, opts) {
    var o = opts || {};
    var w = opt(o, 'w', Studio.u(40)), h = opt(o, 'h', Studio.u(50));
    var p = piece(parent, o, w, h);
    var seed = nextSeed(o), frame = o.frame || 'rect';
    var img = Studio.svg('image', { href: o.src, x: '0', y: '0', width: r2(w), height: r2(h),
      preserveAspectRatio: 'xMidYMid ' + (o.fit || 'slice') }, null);
    var duo = o.duotone === false ? null : M.duotone((o.duotone || [])[0] || '--c-ink', (o.duotone || [])[1] || '--c-paper');
    if (frame === 'cutout') {
      var shadowG = Studio.svg('g', { filter: 'url(#mx-soft)', opacity: '0.55' }, p.body);
      var sImg = img.cloneNode();
      sImg.setAttribute('filter', 'url(#' + M.duotone('--c-ink', '--c-ink') + ')');
      shadowG.appendChild(sImg);
      gs().set(shadowG, { x: Studio.u(0.5), y: Studio.u(0.8) });
      p.shadow = shadowG;
      p.shadowOffset = [Studio.u(0.5), Studio.u(0.8)];
      var cut = Studio.svg('g', { filter: 'url(#mx-sticker)' }, p.body);
      if (duo) img.setAttribute('filter', 'url(#' + duo + ')');
      cut.appendChild(img);
      p.image = img;
      return p;
    }
    var b = Studio.u(opt(o, 'border', 1.2)), amp = Studio.u(opt(o, 'deckle', 0.35));
    var shapeFn = M.shapes[frame] || M.shapes.rect;
    var outer = shapeFn(w, h).polys[0];
    var inner = shapeFn(w - 2 * b, h - 2 * b).polys[0].map(function (q) { return [q[0] + b, q[1] + b]; });
    var outerD = d([M.roughen(outer, { amp: amp, seed: seed })]);
    var innerD = d([M.roughen(inner, { amp: amp * 0.5, seed: seed + 3 })]);
    if (opt(o, 'shadow', true)) {
      p.shadow = Studio.svg('path', { d: outerD, filter: 'url(#mx-soft)' }, p.body);
      p.shadow.style.fill = 'var(--c-shadow)';
      gs().set(p.shadow, { x: Studio.u(0.4), y: Studio.u(0.7) });
      p.shadowOffset = [Studio.u(0.4), Studio.u(0.7)];
    }
    var mat = Studio.svg('path', { d: outerD, filter: 'url(#mx-fibre)' }, p.body);
    mat.style.fill = paint(o.mat || '--c-paper');
    var cid = 'mx-clip-' + seed;
    var cp = Studio.svg('clipPath', { id: cid }, M.defs().querySelector('defs'));
    Studio.svg('path', { d: innerD }, cp);
    var holder = Studio.svg('g', { 'clip-path': 'url(#' + cid + ')' }, p.body);
    if (duo) img.setAttribute('filter', 'url(#' + duo + ')');
    holder.appendChild(img);
    p.image = img;
    p.imageHolder = holder;
    return p;
  };

  /**
   * Halo behind a sacred figure: 'nimbus' (disc, ring and rays), 'prabhavali' (arch of flames, Hindu
   * and Jain images), 'mandorla' (almond of rings), 'sun' (rayed disc). opts {x, y (centre px), r,
   * kind, rays, fill}. Returns a piece with .rays (turn it with M.turn).
   */
  M.halo = function (parent, opts) {
    var o = opts || {};
    var r = opt(o, 'r', Studio.u(20)), kind = o.kind || 'nimbus', size = r * 2.6;
    var p = piece(parent, { x: opt(o, 'x', 0) - size / 2, y: opt(o, 'y', 0) - size / 2, z: o.z, id: o.id }, size, size);
    var c = size / 2, fill = o.fill || M.gold(size);
    p.body.setAttribute('filter', 'url(#mx-glow)');
    p.rays = Studio.svg('g', null, p.body);
    var n = opt(o, 'rays', kind === 'sun' ? 24 : 32);
    if (kind === 'prabhavali') {
      var span = r * 2 * Math.PI * 0.62, fh = r * 0.32;
      var flames = M.shapes.flames(span, fh, Studio.rng(nextSeed(o)), { tongues: 15 }).polys[0];
      var cy = c + r * 0.15;
      var arc = flames.map(function (q) {
        var a = Math.PI + (q[0] / span) * Math.PI, rad = r * 1.02 + (fh - q[1]);
        return [c + Math.cos(a) * rad, cy + Math.sin(a) * rad];
      });
      var inner = sampleArc(c, cy, r * 0.86, r * 0.86, 2 * Math.PI, Math.PI, 40);
      var pth = Studio.svg('path', { d: d([arc.concat(inner)]) }, p.rays);
      pth.style.fill = fill;
      var ring = Studio.svg('path', { d: d([sampleArc(c, cy, r * 0.86, r * 0.86, Math.PI, 2 * Math.PI, 40).concat(sampleArc(c, cy, r * 0.74, r * 0.74, 2 * Math.PI, Math.PI, 40))]) }, p.body);
      ring.style.fill = paint('--c-accent');
    } else if (kind === 'mandorla') {
      [1, 0.88, 0.76].forEach(function (k, i) {
        var e = Studio.svg('ellipse', { cx: c, cy: c, rx: r * 0.62 * k, ry: r * 1.05 * k, fill: 'none' }, i ? p.body : p.rays);
        e.style.stroke = i === 1 ? paint('--c-accent') : fill;
        e.style.strokeWidth = String(r2(Studio.u(i === 1 ? 0.5 : 0.9)));
      });
    } else {
      for (var i = 0; i < n; i++) {
        var a = i / n * Math.PI * 2, a2 = a + Math.PI / n * 0.45, a1 = a - Math.PI / n * 0.45;
        var len = r * (i % 2 ? 1.12 : 1.22);
        var ray = Studio.svg('path', { d: d([[[c + Math.cos(a1) * r * 0.82, c + Math.sin(a1) * r * 0.82], [c + Math.cos(a) * len, c + Math.sin(a) * len], [c + Math.cos(a2) * r * 0.82, c + Math.sin(a2) * r * 0.82]]]) }, p.rays);
        ray.style.fill = fill;
      }
      var disc = Studio.svg('circle', { cx: c, cy: c, r: r * 0.8 }, p.body);
      disc.style.fill = paint(kind === 'sun' ? '--c-gold' : '--c-gold-light');
      disc.style.opacity = kind === 'sun' ? '1' : '0.55';
      var rim = Studio.svg('circle', { cx: c, cy: c, r: r * 0.8, fill: 'none' }, p.body);
      rim.style.stroke = fill;
      rim.style.strokeWidth = String(r2(Studio.u(0.6)));
    }
    p.center = [c, kind === 'prabhavali' ? c + r * 0.15 : c];
    p.gold = fill;
    return p;
  };

  /**
   * Motif tiles (unit square, drawn by g(pathData, fill?, colour?)) for borders and frieze bands.
   * Grouped by tradition in M.traditions; the first listed is the default for that tradition.
   */
  var MOTIFS = {
    lotus: function (q, g) {
      g('M' + q(0.5) + ' ' + q(0.12) + 'C' + q(0.78) + ' ' + q(0.38) + ' ' + q(0.74) + ' ' + q(0.72) + ' ' + q(0.5) + ' ' + q(0.86) + 'C' + q(0.26) + ' ' + q(0.72) + ' ' + q(0.22) + ' ' + q(0.38) + ' ' + q(0.5) + ' ' + q(0.12) + 'Z', true);
    },
    meander: function (q, g) {
      g('M' + q(0.12) + ' ' + q(0.88) + 'V' + q(0.15) + 'H' + q(0.85) + 'V' + q(0.7) + 'H' + q(0.35) + 'V' + q(0.38) + 'H' + q(0.6) + 'V' + q(0.52) + ' M' + q(0.12) + ' ' + q(0.88) + 'H' + q(1.12), false);
    },
    knot: function (q, g) {
      g('M0 ' + q(0.5) + 'C' + q(0.25) + ' ' + q(0.05) + ' ' + q(0.75) + ' ' + q(0.95) + ' ' + q(1) + ' ' + q(0.5), false);
      g('M0 ' + q(0.5) + 'C' + q(0.25) + ' ' + q(0.95) + ' ' + q(0.75) + ' ' + q(0.05) + ' ' + q(1) + ' ' + q(0.5), false);
    },
    beads: function (q, g) {
      g('M' + q(0.22) + ' ' + q(0.5) + 'a' + q(0.28) + ' ' + q(0.28) + ' 0 1 0 ' + q(0.56) + ' 0a' + q(0.28) + ' ' + q(0.28) + ' 0 1 0 ' + q(-0.56) + ' 0Z', true);
    },
    zigzag: function (q, g) {
      g('M0 ' + q(0.7) + 'L' + q(0.25) + ' ' + q(0.3) + 'L' + q(0.5) + ' ' + q(0.7) + 'L' + q(0.75) + ' ' + q(0.3) + 'L' + q(1) + ' ' + q(0.7), false);
    },
    chevron: function (q, g) {
      g('M0 ' + q(0.28) + 'L' + q(0.5) + ' ' + q(0.72) + 'L' + q(1) + ' ' + q(0.28), false);
    },
    'egg-dart': function (q, g) {
      // Ionic egg-and-dart (Greek and Roman mouldings): an egg, then a dart.
      g('M' + q(0.36) + ' ' + q(0.16) + 'C' + q(0.6) + ' ' + q(0.16) + ' ' + q(0.62) + ' ' + q(0.84) + ' ' + q(0.36) + ' ' + q(0.84) + 'C' + q(0.1) + ' ' + q(0.84) + ' ' + q(0.12) + ' ' + q(0.16) + ' ' + q(0.36) + ' ' + q(0.16) + 'Z', true);
      g('M' + q(0.86) + ' ' + q(0.12) + 'L' + q(0.92) + ' ' + q(0.62) + 'L' + q(0.86) + ' ' + q(0.9) + 'L' + q(0.8) + ' ' + q(0.62) + 'Z', true);
    },
    wave: function (q, g) {
      // Running dog / Vitruvian scroll: a wave that curls into the next tile.
      g('M0 ' + q(0.78) + 'C' + q(0.3) + ' ' + q(0.78) + ' ' + q(0.3) + ' ' + q(0.2) + ' ' + q(0.62) + ' ' + q(0.22) + 'C' + q(0.86) + ' ' + q(0.24) + ' ' + q(0.84) + ' ' + q(0.58) + ' ' + q(0.64) + ' ' + q(0.56) + 'C' + q(0.52) + ' ' + q(0.55) + ' ' + q(0.52) + ' ' + q(0.42) + ' ' + q(0.62) + ' ' + q(0.42) + ' M' + q(0.62) + ' ' + q(0.78) + 'H' + q(1), false);
    },
    pattachitra: function (q, g) {
      // Pattachitra teeth band: triangles with a dot between them.
      g('M0 ' + q(0.86) + 'L' + q(0.25) + ' ' + q(0.3) + 'L' + q(0.5) + ' ' + q(0.86) + 'Z M' + q(0.5) + ' ' + q(0.86) + 'L' + q(0.75) + ' ' + q(0.3) + 'L' + q(1) + ' ' + q(0.86) + 'Z', true);
      g('M' + q(0.44) + ' ' + q(0.24) + 'a' + q(0.06) + ' ' + q(0.06) + ' 0 1 0 ' + q(0.12) + ' 0a' + q(0.06) + ' ' + q(0.06) + ' 0 1 0 ' + q(-0.12) + ' 0Z', true);
    },
    ruled: function (q, g) {
      // Rajput and Pahari ruled border: red, then yellow (the band ground), then black.
      g('M0 0H' + q(1) + 'V' + q(0.3) + 'H0Z', true, '--c-accent');
      g('M0 ' + q(0.7) + 'H' + q(1) + 'V' + q(1) + 'H0Z', true, '--c-ink');
    },
    urnes: function (q, g) {
      // Urnes-style ribbon: a thick ink loop with a thin ground-coloured core.
      g('M0 ' + q(0.5) + 'C' + q(0.22) + ' ' + q(0.02) + ' ' + q(0.46) + ' ' + q(0.06) + ' ' + q(0.5) + ' ' + q(0.5) + 'C' + q(0.54) + ' ' + q(0.94) + ' ' + q(0.78) + ' ' + q(0.98) + ' ' + q(1) + ' ' + q(0.5), false, null, 2.4);
      g('M0 ' + q(0.5) + 'C' + q(0.22) + ' ' + q(0.02) + ' ' + q(0.46) + ' ' + q(0.06) + ' ' + q(0.5) + ' ' + q(0.5) + 'C' + q(0.54) + ' ' + q(0.94) + ' ' + q(0.78) + ' ' + q(0.98) + ' ' + q(1) + ' ' + q(0.5), false, 'ground', 0.9);
    }
  };
  M.motifs = Object.keys(MOTIFS);

  /**
   * Tradition presets: border motifs (first is the default) and the halo that fits, or null where
   * the tradition does not put haloes on its gods (Greek, Roman and Norse art).
   */
  M.traditions = {
    indian: { motifs: ['lotus', 'pattachitra', 'ruled'], halo: 'prabhavali', ground: '--c-accent', color: '--c-gold-light' },
    jain: { motifs: ['ruled', 'beads', 'lotus'], halo: 'prabhavali', ground: '--c-gold', color: '--c-ink' },
    buddhist: { motifs: ['lotus', 'beads'], halo: 'nimbus', ground: '--c-accent-2', color: '--c-gold-light' },
    greek: { motifs: ['meander', 'egg-dart', 'wave'], halo: null, ground: '--c-ink', color: '--c-paper' },
    roman: { motifs: ['meander', 'egg-dart', 'wave'], halo: null, ground: '--c-accent', color: '--c-paper' },
    norse: { motifs: ['knot', 'urnes', 'chevron'], halo: null, ground: '--c-paper-2', color: '--c-ink' }
  };

  // One pattern per band, transformed so the tile grid starts at the band's corner and runs along it.
  function motifPattern(motif, b, ground, color, transform) {
    var defs = M.defs().querySelector('defs');
    var pid = 'mx-motif-' + (seedCounter++), sw = r2(b * 0.09);
    var pat = Studio.svg('pattern', { id: pid, patternUnits: 'userSpaceOnUse', width: r2(b), height: r2(b), patternTransform: transform }, defs);
    var bg = Studio.svg('rect', { width: r2(b), height: r2(b) }, pat);
    bg.style.fill = paint(ground);
    var g = function (dd2, fillIt, col, weight) {
      var m = Studio.svg('path', { d: dd2 }, pat);
      var c = col === 'ground' ? paint(ground) : paint(col || color);
      if (fillIt) { m.style.fill = c; } else { m.style.fill = 'none'; m.style.stroke = c; m.style.strokeWidth = String(r2(sw * (weight || 1.6))); m.style.strokeLinecap = 'square'; }
    };
    (MOTIFS[motif] || MOTIFS.lotus)(function (x) { return r2(x * b); }, g);
    return 'url(#' + pid + ')';
  }

  /**
   * Ornamental border band round the frame (or a box). opts {tradition (indian, jain, buddhist,
   * greek, roman, norse: sets motif and colours), motif (M.motifs), inset (u), band (u), color,
   * ground, x, y, w, h}. Returns a piece with .sides [top, right, bottom, left].
   */
  M.border = function (parent, opts) {
    var o = opts || {};
    var f = Studio.format, trad = M.traditions[o.tradition] || {};
    var inset = Studio.u(opt(o, 'inset', 1.6)), b = Studio.u(opt(o, 'band', 3.2));
    var W = opt(o, 'w', f.width), H = opt(o, 'h', f.height);
    var p = piece(parent, { x: opt(o, 'x', 0), y: opt(o, 'y', 0), z: opt(o, 'z', 45) }, W, H);
    var motif = o.motif || (trad.motifs || ['lotus'])[0];
    var ground = o.ground || trad.ground || '--c-accent', color = o.color || trad.color || '--c-gold-light';
    var sw = r2(b * 0.09);
    var rect = function (x, y, w2, h2, transform) {
      var rr = Studio.svg('rect', { x: r2(x), y: r2(y), width: r2(w2), height: r2(h2) }, p.body);
      rr.style.fill = motifPattern(motif, b, ground, color, transform);
      rr.style.stroke = paint('--c-ink');
      rr.style.strokeWidth = String(sw);
      return rr;
    };
    var side = function (x, y) { return 'translate(' + r2(x + b) + ' ' + r2(y) + ') rotate(90)'; };
    p.sides = [
      rect(inset, inset, W - 2 * inset, b, 'translate(' + r2(inset) + ' ' + r2(inset) + ')'),
      rect(W - inset - b, inset + b, b, H - 2 * inset - 2 * b, side(W - inset - b, inset + b)),
      rect(inset, H - inset - b, W - 2 * inset, b, 'translate(' + r2(inset) + ' ' + r2(H - inset - b) + ')'),
      rect(inset, inset + b, b, H - 2 * inset - 2 * b, side(inset, inset + b))
    ];
    p.motif = motif;
    return p;
  };

  // ------------------------------------------------------------------ friezes and registers
  function panelBox(el, x, y, w, h, o) {
    el.style.left = r2(x) + 'px';
    el.style.top = r2(y) + 'px';
    el.style.width = r2(w) + 'px';
    el.style.height = r2(h) + 'px';
    el.style.background = paint(o.ground || '--c-paper-2');
    var rule = Studio.u(opt(o, 'rule', 0.45));
    if (rule > 0) el.style.boxShadow = 'inset 0 ' + r2(rule) + 'px 0 ' + paint(o.ruleColor || '--c-ink') + ', inset 0 ' + r2(-rule) + 'px 0 ' + paint(o.ruleColor || '--c-ink');
  }

  /**
   * Frieze: a horizontal strip of panels read left to right (vase frieze, Oseberg procession, a
   * Phad scroll's episodes). opts {x, y, w, h, panels (count), visible (panels in view), gap (u),
   * ground, rule (u), ruleColor, z}. Returns {el, track, panels: [{el, x, w, h, index}]}: build
   * each episode inside panels[i].el, reveal with M.panelsIn and travel along with M.friezeTo.
   */
  M.frieze = function (parent, opts) {
    M.defs();
    var o = opts || {}, f = Studio.format;
    var n = opt(o, 'panels', 4), vis = Math.min(n, opt(o, 'visible', n));
    var W = opt(o, 'w', f.safe.width), H = opt(o, 'h', Studio.u(30)), gap = Studio.u(opt(o, 'gap', 1.2));
    var pw = (W - gap * (vis - 1)) / vis;
    var el = Studio.el('div', 'mx-frieze', null, parent);
    el.style.left = r2(opt(o, 'x', f.safe.left)) + 'px';
    el.style.top = r2(opt(o, 'y', f.safe.top)) + 'px';
    el.style.width = r2(W) + 'px';
    el.style.height = r2(H) + 'px';
    el.style.zIndex = String(opt(o, 'z', 20));
    var track = Studio.el('div', 'mx-frieze-track', null, el);
    var total = n * pw + (n - 1) * gap;
    track.style.width = r2(total) + 'px';
    var panels = [];
    for (var i = 0; i < n; i++) {
      var pe = Studio.el('div', 'mx-panel', null, track);
      panelBox(pe, i * (pw + gap), 0, pw, H, o);
      panels.push({ el: pe, x: i * (pw + gap), y: 0, w: pw, h: H, index: i });
    }
    return { el: el, track: track, panels: panels, w: W, total: total, offset: 0, pw: pw, gap: gap };
  };

  /** Slide the frieze so panel `index` is centred (clamped to the strip). Chains from the last position. */
  M.friezeTo = function (tl, fr, at, index, opts) {
    var o = opts || {};
    var dur = opt(o, 'duration', 1.6);
    var target = Math.max(-(fr.total - fr.w), Math.min(0, -(index * (fr.pw + fr.gap)) + (fr.w - fr.pw) / 2));
    var first = !fr.__moved;
    tl.fromTo(fr.track, { x: fr.offset }, { x: target, duration: dur, ease: o.ease || 'power2.inOut', immediateRender: first }, at);
    fr.offset = target;
    fr.__moved = true;
    return at + dur;
  };

  /**
   * Registers: stacked horizontal bands read in the tradition's order (Gotland picture-stone
   * fields bottom-up, a folio's registers top-down). opts {x, y, w, h, rows, gap (u), order
   * 'top-down'|'bottom-up', ground, rule, z}. Returns {el, rows: [...]} in reading order.
   */
  M.registers = function (parent, opts) {
    M.defs();
    var o = opts || {}, f = Studio.format;
    var n = opt(o, 'rows', 3), W = opt(o, 'w', f.safe.width), H = opt(o, 'h', f.safe.height), gap = Studio.u(opt(o, 'gap', 1));
    var rh = (H - gap * (n - 1)) / n;
    var el = Studio.el('div', 'mx-registers', null, parent);
    el.style.left = r2(opt(o, 'x', f.safe.left)) + 'px';
    el.style.top = r2(opt(o, 'y', f.safe.top)) + 'px';
    el.style.width = r2(W) + 'px';
    el.style.height = r2(H) + 'px';
    el.style.zIndex = String(opt(o, 'z', 20));
    var rows = [];
    for (var i = 0; i < n; i++) {
      var slot = o.order === 'bottom-up' ? n - 1 - i : i;
      var re = Studio.el('div', 'mx-panel', null, el);
      panelBox(re, 0, slot * (rh + gap), W, rh, o);
      rows.push({ el: re, x: 0, y: slot * (rh + gap), w: W, h: rh, index: i });
    }
    return { el: el, rows: rows, panels: rows, order: o.order || 'top-down' };
  };

  /** Reveal panels or registers one by one in reading order: a wipe from `from` ('left', 'bottom', 'top'). */
  M.panelsIn = function (tl, panels, at, opts) {
    var o = opts || {};
    var dur = opt(o, 'duration', 0.9), stg = opt(o, 'stagger', 0.5), from = o.from || 'left';
    var start = { left: 'inset(0% 100% 0% 0%)', right: 'inset(0% 0% 0% 100%)', bottom: 'inset(100% 0% 0% 0%)', top: 'inset(0% 0% 100% 0%)' }[from];
    (panels.panels || panels).forEach(function (pn, i) {
      tl.fromTo(pn.el || pn, { clipPath: start }, { clipPath: 'inset(0% 0% 0% 0%)', duration: dur, ease: o.ease || 'power2.inOut', immediateRender: true }, at + i * stg);
    });
    return at + dur + stg * Math.max(0, (panels.panels || panels).length - 1);
  };

  /**
   * Kaavad-style folding doors over a box: two painted leaves that swing open on their hinges.
   * opts {x, y, w, h, fill}. Returns {el, left, right}; open with M.open.
   */
  M.doors = function (parent, opts) {
    M.defs();
    var o = opts || {};
    var W = opt(o, 'w', Studio.u(40)), H = opt(o, 'h', Studio.u(50));
    var el = Studio.el('div', 'mx-doors', null, parent);
    el.style.left = r2(opt(o, 'x', 0)) + 'px';
    el.style.top = r2(opt(o, 'y', 0)) + 'px';
    el.style.width = r2(W) + 'px';
    el.style.height = r2(H) + 'px';
    el.style.zIndex = String(opt(o, 'z', 30));
    var mk = function (side) {
      var leaf = Studio.el('div', 'mx-leaf', null, el);
      leaf.style[side] = '0';
      if (o.fill) leaf.style.background = paint(o.fill);
      var w = W / 2;
      var svg = Studio.svg('svg', { viewBox: '0 0 ' + r2(w) + ' ' + r2(H), 'aria-hidden': 'true' }, leaf);
      var l = M.shapes.lotus(w * 0.5, w * 0.36, Studio.rng(5), { petals: 7 }).polys;
      var lg = Studio.svg('g', { transform: 'translate(' + r2(w * 0.25) + ' ' + r2(H * 0.5 - w * 0.18) + ')' }, svg);
      var lp = Studio.svg('path', { d: d(l) }, lg);
      lp.style.fill = paint('--c-accent');
      lp.style.stroke = paint('--c-ink');
      lp.style.strokeWidth = String(r2(Studio.u(0.2)));
      return leaf;
    };
    return { el: el, left: mk('left'), right: mk('right') };
  };

  /** Swing doors open (kaavad reveal). opts {duration 1.4, angle 112, lag 0.08}. */
  M.open = function (tl, doors, at, opts) {
    var o = opts || {};
    var dur = opt(o, 'duration', 1.4), ang = opt(o, 'angle', 112);
    tl.fromTo(doors.left, { rotationY: 0, transformOrigin: '0% 50%' }, { rotationY: -ang, transformOrigin: '0% 50%', duration: dur, ease: 'power2.inOut', immediateRender: true }, at);
    tl.fromTo(doors.right, { rotationY: 0, transformOrigin: '100% 50%' }, { rotationY: ang, transformOrigin: '100% 50%', duration: dur, ease: 'power2.inOut', immediateRender: true }, at + opt(o, 'lag', 0.08));
    return at + dur + opt(o, 'lag', 0.08);
  };

  /**
   * Phad-style scroll: a painted strip between two rollers; `content` (element) is moved inside.
   * opts {x, y, w, h, content}. Unroll with M.unroll.
   */
  M.scroll = function (parent, opts) {
    M.defs();
    var o = opts || {};
    var W = opt(o, 'w', Studio.u(80));
    var el = Studio.el('div', 'mx-scroll', null, parent);
    el.style.left = r2(opt(o, 'x', 0)) + 'px';
    el.style.top = r2(opt(o, 'y', 0)) + 'px';
    el.style.width = r2(W) + 'px';
    el.style.height = r2(opt(o, 'h', Studio.u(30))) + 'px';
    el.style.zIndex = String(opt(o, 'z', 20));
    var view = Studio.el('div', 'mx-scroll-view', null, el);
    if (o.content) view.appendChild(o.content);
    var left = Studio.el('div', 'mx-roller', null, el), right = Studio.el('div', 'mx-roller', null, el);
    return { el: el, view: view, left: left, right: right, w: W };
  };

  /** Unroll a scroll from its centre (or from the left with {from: 'left'}). */
  M.unroll = function (tl, scroll, at, opts) {
    var o = opts || {};
    var dur = opt(o, 'duration', 1.8), w = scroll.w, half = Studio.u(1.1), fromLeft = o.from === 'left';
    tl.fromTo(scroll.view, { clipPath: fromLeft ? 'inset(0% 100% 0% 0%)' : 'inset(0% 50% 0% 50%)' }, { clipPath: 'inset(0% 0% 0% 0%)', duration: dur, ease: 'power2.inOut', immediateRender: true }, at);
    tl.fromTo(scroll.left, { x: fromLeft ? -half : w / 2 - half }, { x: -half, duration: dur, ease: 'power2.inOut', immediateRender: true }, at);
    tl.fromTo(scroll.right, { x: fromLeft ? -half : w / 2 - half }, { x: w - half, duration: dur, ease: 'power2.inOut', immediateRender: true }, at);
    return at + dur;
  };

  // ------------------------------------------------------------------ shadow puppets and cut-outs
  /**
   * Stepped ease for hand-animated "on twos" motion: the pose updates `fps` times a second (12 is
   * on twos at 24 fps) while the camera and the rest stay smooth. Deterministic: a pure function.
   */
  M.stepped = function (ease, duration, fps) {
    var base = global.gsap.parseEase(ease || 'none');
    var n = Math.max(1, Math.round(duration * (fps || 12)));
    return function (p) { return p >= 1 ? 1 : base(Math.floor(p * n) / n); };
  };
  function stepFps(o) { return o && o.steps ? (o.steps === true ? 12 : o.steps) : 0; }

  /**
   * Painted layers inside a part (shading, features, ornament), drawn over the part's base shape:
   * [{d, fill, op, stroke, sw, cap, clip}]. clip: true clips the layer to the part's own shape,
   * a path string clips it to that shape (an iris inside its eye). Silhouettes skip layers.
   */
  var clipCounter = 0, gradCache = {};
  /**
   * A fill: a token or colour string, or a gradient in viewBox units:
   * {radial: [[offset, colour, opacity], ...], cx, cy, r, fx, fy} or {linear: [...], x1, y1, x2, y2}.
   */
  function fillOf(v) {
    if (!v || typeof v !== 'object') return paint(v);
    var key = JSON.stringify(v);
    if (!gradCache[key]) {
      var defs = M.defs().querySelector('defs'), id = 'mx-grad-' + (clipCounter++);
      var radial = !!v.radial, g = Studio.svg(radial ? 'radialGradient' : 'linearGradient', radial
        ? { id: id, gradientUnits: 'userSpaceOnUse', cx: v.cx, cy: v.cy, r: v.r, fx: v.fx === undefined ? v.cx : v.fx, fy: v.fy === undefined ? v.cy : v.fy }
        : { id: id, gradientUnits: 'userSpaceOnUse', x1: v.x1, y1: v.y1, x2: v.x2, y2: v.y2 }, defs);
      (v.radial || v.linear).forEach(function (st) {
        var stop = Studio.svg('stop', { offset: st[0] }, g);
        stop.style.stopColor = paint(st[1]);
        stop.style.stopOpacity = String(st[2] === undefined ? 1 : st[2]);
      });
      gradCache[key] = 'url(#' + id + ')';
    }
    return gradCache[key];
  }
  M.fillOf = fillOf;

  function drawLayers(pt, g2, vb) {
    if (!pt.layers || !pt.layers.length) return;
    var ids = {}, run = null;
    var defs = M.defs().querySelector('defs');
    function clipHost(key) {
      if (run && run.key === key) return run.g;      // consecutive layers share a group; paint order holds
      if (!ids[key]) {
        ids[key] = 'mx-clip-' + (clipCounter++);
        var cp = Studio.svg('clipPath', { id: ids[key] }, defs);
        Studio.svg('path', { d: key === true ? pt.d : key, 'clip-rule': pt.rule || 'nonzero' }, cp);
      }
      run = { key: key, g: Studio.svg('g', { 'clip-path': 'url(#' + ids[key] + ')' }, g2) };
      return run.g;
    }
    pt.layers.forEach(function (ly) {
      if (!ly || !ly.d) return;
      var host = ly.clip ? clipHost(ly.clip) : g2;
      if (!ly.clip) run = null;
      var lp = Studio.svg('path', { d: ly.d, 'fill-rule': ly.rule || 'nonzero' }, host);
      lp.style.fill = ly.fill ? fillOf(ly.fill) : 'none';
      if (ly.op !== undefined) lp.style.opacity = String(ly.op);
      if (ly.stroke) {
        lp.style.stroke = paint(ly.stroke);
        lp.style.strokeWidth = String(r2((ly.sw || 1) * vb[1] / 800));
        lp.style.strokeLinecap = ly.cap || 'round';
        lp.style.strokeLinejoin = 'round';
      }
    });
  }

  /**
   * Jointed figure: shadow puppet or paper cut-out. opts {x, y, h (px height), figure (id in
   * M.figures, e.g. 'hanuman', or a {viewBox, parts, meta} object), figureOptions, parts and
   * viewBox (raw), look: 'silhouette' (Reiniger, lamp-black) | 'leather' (Tholu Bommalata:
   * translucent dyed leather, ink outline, punched holes) | 'paper' (layered cut paper with fibre
   * and a lifted shadow) | 'painted' (flat colour, ink contour: Pattachitra, miniatures) | 'illustrated'
   * (full colour with painted layers and an ink outline drawn last: the human figures), rods
   * (true except paper, painted and illustrated), fill (silhouette colour), seed}.
   * parts: [{id, d, pivot, parent, behind, fill, detail, rule, rod, layers, outline, sw, ink, tf, keep}] in viewBox
   * units, parents first; `behind` draws the part under its parent; `detail` is an incised line path; `layers`
   * are painted shapes inside the part (see drawLayers); outline: false skips the illustrated outline; fill
   * may be a gradient (fillOf); `tf` is an SVG transform for the part's drawing and its children (a weapon
   * drawn at the origin and placed, a head scaled), while posing still rotates about `pivot` in the
   * parent's space; `keep: true` draws the part in full colour in every look (auras, light).
   * Returns a piece with .part(id), .meta and .pivots.
   */
  M.puppet = function (parent, opts) {
    var o = opts || {};
    var fig = o.figure ? (typeof o.figure === 'string' ? (M.figures[o.figure] ? M.figures[o.figure](o.figureOptions || {}) : null) : o.figure) : null;
    if (o.figure && !fig) throw new Error('Studio.kit.mythic.puppet: no figure "' + o.figure + '" (load kits/mythic/figures.js?)');
    if (fig && Array.isArray(fig)) fig = { parts: fig };
    var parts = o.parts || (fig ? fig.parts : M.figures.hero());
    var vb = o.viewBox || (fig && fig.viewBox) || [200, 400];
    var h = opt(o, 'h', Studio.u(50)), w = h * vb[0] / vb[1];
    var p = piece(parent, o, w, h);
    p.art.setAttribute('viewBox', '0 0 ' + vb[0] + ' ' + vb[1]);
    var look = o.look || 'silhouette', groups = {}, hosts = {}, pivots = {};
    var leatherCols = ['--c-leather-red', '--c-leather-ochre', '--c-leather-green', '--c-leather-blue', '--c-accent'];
    var rng = Studio.rng(nextSeed(o));
    if (look === 'leather') {
      var mid = 'mx-punch-' + (seedCounter++);
      var holes = Studio.svg('mask', { id: mid, maskUnits: 'userSpaceOnUse', x: -vb[0], y: -vb[1], width: vb[0] * 3, height: vb[1] * 3 }, M.defs().querySelector('defs'));
      Studio.svg('rect', { x: -vb[0], y: -vb[1], width: vb[0] * 3, height: vb[1] * 3, fill: '#fff' }, holes);
      for (var i = 0; i < 90; i++) {
        Studio.svg('circle', { cx: r2(rng() * vb[0]), cy: r2(vb[1] * 0.18 + rng() * vb[1] * 0.7), r: r2(0.6 + rng() * 1.1), fill: '#000' }, holes);
      }
      p.body.setAttribute('mask', 'url(#' + mid + ')');
    } else if (look === 'paper' || look === 'illustrated') {
      p.body.setAttribute('filter', 'url(#mx-lift)');
    }
    parts.forEach(function (pt, i) {
      var host = pt.parent ? hosts[pt.parent] : p.body;
      if (!host) throw new Error('Studio.kit.mythic.puppet: part "' + pt.id + '" names unknown parent "' + pt.parent + '"');
      var outer = Studio.svg('g', { 'data-part': pt.id }, null);
      if (pt.behind && host.firstChild) host.insertBefore(outer, host.firstChild); else host.appendChild(outer);
      var g2 = pt.tf ? Studio.svg('g', { transform: pt.tf }, outer) : outer;
      var path = Studio.svg('path', { d: pt.d, 'fill-rule': pt.rule || 'nonzero' }, g2);
      if (pt.keep) {
        path.style.fill = pt.fill ? fillOf(pt.fill) : 'none';
        drawLayers(pt, g2, vb);
      } else if (look === 'silhouette') {
        path.style.fill = paint(o.fill || '--c-ink');
      } else if (look === 'illustrated') {
        path.style.fill = fillOf(pt.fill || leatherCols[i % leatherCols.length]);
        drawLayers(pt, g2, vb);
        if (pt.outline !== false) {
          var ol = Studio.svg('path', { d: pt.d, fill: 'none', 'fill-rule': pt.rule || 'nonzero' }, g2);
          ol.style.stroke = paint(pt.ink || '--c-ink');
          ol.style.strokeOpacity = '0.82';
          ol.style.strokeWidth = String(r2(vb[1] / 520 * (pt.sw || 1)));
          ol.style.strokeLinejoin = 'round';
        }
        if (pt.detail) {
          var dl = Studio.svg('path', { d: pt.detail, fill: 'none' }, g2);
          dl.style.stroke = paint(pt.ink || '--c-ink');
          dl.style.strokeOpacity = '0.55';
          dl.style.strokeWidth = String(r2(vb[1] / 900));
          dl.style.strokeLinecap = 'round';
        }
      } else {
        path.style.fill = fillOf(pt.fill || leatherCols[i % leatherCols.length]);
        path.style.strokeLinejoin = 'round';
        if (look === 'leather') {
          path.style.fillOpacity = '0.88';
          path.style.stroke = paint('--c-ink');
          path.style.strokeWidth = String(r2(vb[1] / 250));
        } else if (look === 'painted') {
          path.style.stroke = paint('--c-ink');
          path.style.strokeWidth = String(r2(vb[1] / 220));
        } else {
          path.setAttribute('filter', 'url(#mx-fibre)');
          path.style.stroke = 'rgba(255,250,240,0.6)';
          path.style.strokeWidth = String(r2(vb[1] / 400));
        }
        drawLayers(pt, g2, vb);
        if (pt.detail) {
          var det = Studio.svg('path', { d: pt.detail, fill: 'none' }, g2);
          det.style.stroke = look === 'leather' ? paint('--c-gold-light') : (look === 'painted' ? paint('--c-ink') : 'rgba(43,29,20,0.55)');
          det.style.strokeWidth = String(r2(vb[1] / 360));
          det.style.strokeLinecap = 'round';
        }
      }
      groups[pt.id] = outer;
      hosts[pt.id] = g2;
      pivots[pt.id] = pt.pivot || [vb[0] / 2, vb[1] / 2];
      if (pt.rod) pivots[pt.id + ':rod'] = pt.rod;
    });
    if (opt(o, 'rods', look !== 'paper' && look !== 'painted' && look !== 'illustrated')) {
      parts.forEach(function (pt) {
        if (!pt.rod) return;
        var rod = Studio.svg('line', { x1: pt.rod[0], y1: pt.rod[1], x2: pt.rod[0] + vb[0] * 0.04, y2: vb[1] * 1.12 }, groups[pt.id]);
        rod.style.stroke = paint('--c-ink');
        rod.style.strokeWidth = String(r2(vb[1] / 300));
        rod.style.opacity = '0.75';
      });
    }
    p.groups = groups;
    p.pivots = pivots;
    p.pose = {};
    p.meta = (fig && fig.meta) || {};
    p.part = function (id) { return groups[id]; };
    return p;
  };

  /** A paper cut-out figure: M.puppet with look 'paper' and no rods. */
  M.cutout = function (parent, opts) {
    var o = {}, k;
    for (k in opts) if (Object.prototype.hasOwnProperty.call(opts, k)) o[k] = opts[k];
    o.look = o.look || 'paper';
    if (o.rods === undefined) o.rods = false;
    return M.puppet(parent, o);
  };

  /**
   * Rotate joints to a pose: M.pose(tl, puppet, at, {'arm-front': -40, head: 6}, {duration, ease,
   * steps}). Chains from the previous pose. steps: true (12 fps, "on twos") or a rate.
   */
  M.pose = function (tl, pup, at, pose, opts) {
    var o = opts || {};
    var dur = opt(o, 'duration', 0.6), fps = stepFps(o);
    var ease = fps ? M.stepped(o.ease || 'sine.inOut', dur, fps) : (o.ease || 'sine.inOut');
    Object.keys(pose).forEach(function (id) {
      var g2 = pup.groups[id];
      if (!g2) throw new Error('Studio.kit.mythic.pose: no part "' + id + '"');
      var pv = pup.pivots[id], origin = pv[0] + ' ' + pv[1];
      var first = !Object.prototype.hasOwnProperty.call(pup.pose, id), prev = first ? 0 : pup.pose[id];
      tl.fromTo(g2, { rotation: prev, svgOrigin: origin }, { rotation: pose[id], svgOrigin: origin, duration: dur, ease: ease, immediateRender: first }, at);
      pup.pose[id] = pose[id];
    });
    return at + dur;
  };

  /** Figure library. The placeholder hero lives here; kits/mythic/figures.js adds the tradition figures. */
  M.figures = M.figures || {};
  M.figures.hero = function () {
    return [
      { id: 'legs', pivot: [100, 230], d: 'M78 226 L124 226 L132 300 L150 386 L162 392 L132 396 L118 318 L104 270 L96 318 L84 394 L56 396 L72 386 L80 300 Z' },
      { id: 'torso', parent: 'legs', pivot: [100, 228], fill: '--c-leather-ochre', d: 'M80 118 C92 108 112 108 124 118 L130 170 L122 232 L80 232 L72 170 Z' },
      { id: 'arm-back', parent: 'torso', pivot: [86, 128], fill: '--c-leather-red', d: 'M80 122 C74 150 66 176 62 200 L72 204 C78 182 88 156 94 130 Z' },
      { id: 'hand-back', parent: 'arm-back', pivot: [66, 202], rod: [62, 232], fill: '--c-leather-red', d: 'M62 198 L56 236 L66 240 L74 204 Z' },
      { id: 'head', parent: 'torso', pivot: [104, 112], fill: '--c-leather-ochre', d: 'M96 112 L94 96 C88 92 88 76 98 70 C108 62 124 68 126 82 L132 92 L124 96 L124 106 L114 112 Z' },
      { id: 'crown', parent: 'head', pivot: [108, 70], fill: '--c-leather-red', d: 'M94 74 L98 44 L106 22 L110 4 L114 22 L120 44 L126 74 Z M100 50 L120 50 L118 58 L102 58 Z' },
      { id: 'arm-front', parent: 'torso', pivot: [114, 128], fill: '--c-leather-green', d: 'M108 122 C116 146 124 164 136 182 L146 176 C136 158 128 140 122 120 Z' },
      { id: 'hand-front', parent: 'arm-front', pivot: [140, 180], rod: [172, 160], fill: '--c-leather-green', d: 'M136 176 L170 156 L176 164 L144 186 Z' }
    ];
  };

  // ------------------------------------------------------------------ text pieces
  /** Storyteller's source cartouche: "As told in" + the text and version. opts {x, y, kicker, title, w, plate}. */
  M.cartouche = function (parent, opts) {
    M.defs();
    var o = opts || {};
    var el = Studio.el('div', 'mx-cartouche' + (o.plate ? ' mx-plate' : ''), null, parent);
    el.style.left = r2(opt(o, 'x', Studio.format.safe.left)) + 'px';
    el.style.top = r2(opt(o, 'y', Studio.format.safe.top)) + 'px';
    if (o.w) el.style.width = r2(o.w) + 'px';
    el.style.zIndex = String(opt(o, 'z', 46));
    var k = Studio.el('div', 'mx-k', o.kicker || 'As told in', el);
    var t = Studio.el('div', 'mx-t', o.title || '', el);
    var rule = Studio.el('div', 'mx-rule', null, el);
    return { el: el, kicker: k, title: t, rule: rule };
  };

  /** Invocation title, centred: {kicker, title, sub, top (px), plate (paper backing over busy art)}. Words rise with M.titleIn. */
  M.title = function (parent, opts) {
    M.defs();
    var o = opts || {};
    var el = Studio.el('div', 'mx-title' + (o.plate ? ' mx-plate' : ''), null, parent);
    el.style.top = r2(opt(o, 'top', Studio.format.height * 0.3)) + 'px';
    el.style.zIndex = String(opt(o, 'z', 46));
    var k = o.kicker ? Studio.el('div', 'mx-k', o.kicker, el) : null;
    var t = Studio.el('div', 'mx-t', null, el);
    t.setAttribute('aria-label', o.title || '');
    var words = String(o.title || '').split(/\s+/).filter(Boolean).map(function (wd, i, arr) {
      var s = Studio.el('span', 'mx-w', wd, t);
      s.setAttribute('aria-hidden', 'true');
      if (i < arr.length - 1) t.appendChild(document.createTextNode(' '));
      return s;
    });
    var s2 = o.sub ? Studio.el('div', 'mx-s', o.sub, el) : null;
    return { el: el, kicker: k, title: t, words: words, sub: s2 };
  };

  // ------------------------------------------------------------------ motion
  /**
   * Hand-placed paper entrance: the piece arrives lifted (higher, longer softer shadow) and settles
   * with a slight seeded tilt, as if laid on the table by hand. opts {lift (u), tilt (deg), duration, stagger}.
   */
  M.place = function (tl, pieces, at, opts) {
    var o = opts || {};
    var dur = opt(o, 'duration', 0.9), stg = opt(o, 'stagger', 0.12), lift = Studio.u(opt(o, 'lift', 3));
    var rng = Studio.rng(nextSeed(o)), end = at;
    list(pieces).forEach(function (pc, i) {
      var tilt = (rng() * 2 - 1) * opt(o, 'tilt', 1.4), at2 = at + i * stg;
      tl.fromTo(art(pc), { y: -lift, rotation: tilt * 3, autoAlpha: 0, transformOrigin: '50% 50%' },
        { y: 0, rotation: tilt, autoAlpha: 1, transformOrigin: '50% 50%', duration: dur, ease: stepFps(o) ? M.stepped('power3.out', dur, stepFps(o)) : 'power3.out', immediateRender: true }, at2);
      if (pc.shadow && pc.shadowOffset) {
        tl.fromTo(pc.shadow, { x: pc.shadowOffset[0] * 3, y: pc.shadowOffset[1] * 3, opacity: 0.35 },
          { x: pc.shadowOffset[0], y: pc.shadowOffset[1], opacity: 1, duration: dur, ease: 'power2.out', immediateRender: true }, at2);
      }
      end = at2 + dur;
    });
    return end;
  };

  /** Reverent rise for a deity or hero: from below, unhurried, no overshoot. opts {distance (u), duration}. */
  M.rise = function (tl, pc, at, opts) {
    var o = opts || {};
    var dur = opt(o, 'duration', 1.6);
    tl.fromTo(art(pc), { y: Studio.u(opt(o, 'distance', 6)), scale: 0.97, autoAlpha: 0, transformOrigin: '50% 100%' },
      { y: 0, scale: 1, autoAlpha: 1, transformOrigin: '50% 100%', duration: dur, ease: 'power2.out', immediateRender: true }, at);
    return at + dur;
  };

  /** Lift pieces off the table (exit): the reverse of place. */
  M.lift = function (tl, pieces, at, opts) {
    var o = opts || {};
    var dur = opt(o, 'duration', 0.6), stg = opt(o, 'stagger', 0.06), all = list(pieces);
    all.forEach(function (pc, i) {
      tl.fromTo(art(pc), { autoAlpha: 1, y: 0 }, { autoAlpha: 0, y: -Studio.u(opt(o, 'lift', 3)), duration: dur, ease: 'power2.in', immediateRender: false }, at + i * stg);
    });
    return at + dur + stg * Math.max(0, all.length - 1);
  };

  /** Halo entrance: blooms from the figure's centre. */
  M.haloIn = function (tl, halo, at, opts) {
    var o = opts || {};
    var dur = opt(o, 'duration', 1.4);
    tl.fromTo(art(halo), { scale: 0.55, autoAlpha: 0, transformOrigin: '50% 50%' }, { scale: 1, autoAlpha: 1, transformOrigin: '50% 50%', duration: dur, ease: 'power2.out', immediateRender: true }, at);
    return at + dur;
  };

  /** Slow continuous turn of a halo's rays (or any piece) from `from` to `to`. opts {degrees 12}. */
  M.turn = function (tl, target, from, to, opts) {
    var o = opts || {};
    var el = target && target.rays ? target.rays : body(target);
    var c = target && target.center ? target.center[0] + ' ' + target.center[1] : null;
    var v0 = { rotation: 0 }, v1 = { rotation: opt(o, 'degrees', 12), duration: Math.max(0.01, to - from), ease: 'none', immediateRender: false };
    if (c) { v0.svgOrigin = c; v1.svgOrigin = c; } else { v0.transformOrigin = '50% 50%'; v1.transformOrigin = '50% 50%'; }
    tl.fromTo(el, v0, v1, from);
    return to;
  };

  /** Breathing stillness for a held sacred image: a scale swell of about 1.5% (finite, seek-safe). */
  M.breathe = function (tl, pieces, from, to, opts) {
    var o = opts || {};
    var period = opt(o, 'period', 4.2), amt = opt(o, 'amount', 0.015);
    list(pieces).forEach(function (pc) {
      var reps = Math.max(1, Math.floor((to - from) / (period / 2)));
      tl.fromTo(body(pc), { scale: 1, transformOrigin: '50% 100%' }, { scale: 1 + amt, transformOrigin: '50% 100%', duration: period / 2, ease: 'sine.inOut', repeat: reps - 1, yoyo: true, immediateRender: false }, from);
    });
    return to;
  };

  /** Pendulum sway from a pivot (trees, banners, puppets on rods). opts {degrees 2.5, period 2.6, origin, seed}. */
  M.sway = function (tl, pieces, from, to, opts) {
    var o = opts || {};
    var rng = Studio.rng(nextSeed(o));
    list(pieces).forEach(function (pc) {
      var per = opt(o, 'period', 2.6) * (0.85 + rng() * 0.3), deg = opt(o, 'degrees', 2.5) * (0.8 + rng() * 0.4);
      var reps = Math.max(1, Math.floor((to - from) / (per / 2)));
      var swayEase = stepFps(o) ? M.stepped('sine.inOut', per / 2, stepFps(o)) : 'sine.inOut';
      tl.fromTo(body(pc), { rotation: -deg / 2, transformOrigin: opt(o, 'origin', '50% 100%') }, { rotation: deg / 2, transformOrigin: opt(o, 'origin', '50% 100%'), duration: per / 2, ease: swayEase, repeat: reps - 1, yoyo: true, immediateRender: false }, from);
    });
    return to;
  };

  /** Gold-leaf glint: a light band sweeps across a M.gold() gradient. */
  M.glint = function (tl, goldUrl, at, opts) {
    var o = opts || {};
    var id = String(goldUrl).replace(/^url\(#|\)$/g, ''), g = document.getElementById(id);
    if (!g) throw new Error('Studio.kit.mythic.glint: no gradient ' + id);
    var w = g.__mxWidth, dur = opt(o, 'duration', 1.6);
    tl.fromTo(g, { attr: { x1: -w, x2: 0 } }, { attr: { x1: w, x2: w * 2 }, duration: dur, ease: 'power1.inOut', immediateRender: false }, at);
    return at + dur;
  };

  /** Word-by-word rise for M.title, then the subtitle. */
  M.titleIn = function (tl, t, at, opts) {
    var o = opts || {};
    var mo = Studio.motion(), stg = opt(o, 'stagger', 0.12), end = at;
    if (t.el.classList.contains('mx-plate')) {
      tl.fromTo(t.el, { autoAlpha: 0 }, { autoAlpha: 1, duration: mo.enter * 0.6, ease: 'power1.out', immediateRender: true }, at - 0.1);
    }
    if (t.kicker) {
      tl.fromTo(t.kicker, { autoAlpha: 0, y: Studio.u(1.2) }, { autoAlpha: 1, y: 0, duration: mo.enter, ease: mo.easeOut, immediateRender: true }, at);
      end = at + mo.enter;
    }
    t.words.forEach(function (wd, i) {
      tl.fromTo(wd, { autoAlpha: 0, y: Studio.u(3) }, { autoAlpha: 1, y: 0, duration: mo.enter, ease: mo.easeOut, immediateRender: true }, at + 0.2 + i * stg);
      end = at + 0.2 + i * stg + mo.enter;
    });
    if (t.sub) {
      tl.fromTo(t.sub, { autoAlpha: 0 }, { autoAlpha: 1, duration: mo.enter, ease: 'power1.out', immediateRender: true }, end - 0.2);
      end += mo.enter - 0.2;
    }
    return end;
  };

  /** Cartouche entrance: kicker, title, then the rule draws (rises in place, so it never leaves the safe area). */
  M.cartoucheIn = function (tl, c, at) {
    var mo = Studio.motion();
    if (c.el.classList.contains('mx-plate')) {
      tl.fromTo(c.el, { autoAlpha: 0 }, { autoAlpha: 1, duration: mo.enter * 0.6, ease: 'power1.out', immediateRender: true }, at - 0.1);
    }
    tl.fromTo(c.kicker, { autoAlpha: 0, y: Studio.u(1.2) }, { autoAlpha: 1, y: 0, duration: mo.enter, ease: mo.easeOut, immediateRender: true }, at);
    tl.fromTo(c.title, { autoAlpha: 0, y: Studio.u(1.6) }, { autoAlpha: 1, y: 0, duration: mo.enter, ease: mo.easeOut, immediateRender: true }, at + 0.15);
    tl.fromTo(c.rule, { scaleX: 0 }, { scaleX: 1, duration: mo.enter, ease: mo.easeInOut, immediateRender: true }, at + 0.35);
    return at + 0.35 + mo.enter;
  };

  /** Border entrance: the four bands draw out from their centres in reading order. */
  M.borderIn = function (tl, border, at, opts) {
    var o = opts || {};
    var dur = opt(o, 'duration', 0.9), stg = opt(o, 'stagger', 0.12);
    border.sides.forEach(function (s, i) {
      var prop = i % 2 === 0 ? 'scaleX' : 'scaleY', v0 = { transformOrigin: '50% 50%' }, v1 = { transformOrigin: '50% 50%', duration: dur, ease: 'power2.out', immediateRender: true };
      v0[prop] = 0;
      v1[prop] = 1;
      tl.fromTo(s, v0, v1, at + i * stg);
    });
    return at + dur + stg * 3;
  };

  /**
   * Falling flowers (pushpa vrishti, the gods' shower of blossoms), petals, or rising embers.
   * opts {count 26, kind 'petal'|'ember', colors [tokens], size (u), seed, x0, x1 (0-1 of width), z}.
   * Every particle is an explicit finite tween; nothing shows outside [from, to].
   */
  M.shower = function (tl, parent, from, to, opts) {
    var o = opts || {};
    M.defs();
    var f = Studio.format, rng = Studio.rng(nextSeed(o));
    var count = opt(o, 'count', 26), rise = o.kind === 'ember';
    var cols = o.colors || (rise ? ['--c-gold-light', '--c-gold', '--c-accent-3'] : ['--c-lotus', '--c-gold-light', '--c-accent', '--c-gold']);
    var holder = Studio.el('div', 'mx-piece', null, parent);
    holder.style.left = '0px';
    holder.style.top = '0px';
    holder.style.width = f.width + 'px';
    holder.style.height = f.height + 'px';
    holder.style.zIndex = String(opt(o, 'z', 44));
    holder.style.pointerEvents = 'none';
    var svg = Studio.svg('svg', { viewBox: '0 0 ' + f.width + ' ' + f.height, 'aria-hidden': 'true' }, holder);
    var span = Math.max(0.5, to - from);
    for (var i = 0; i < count; i++) {
      var s = Studio.u(opt(o, 'size', 1.2)) * (0.7 + rng() * 0.6);
      var g2 = Studio.svg('g', null, svg);
      var shp = rise ? Studio.svg('circle', { r: r2(s * 0.35) }, g2) : Studio.svg('path', { d: 'M0 ' + r2(-s) + 'C' + r2(s * 0.7) + ' ' + r2(-s * 0.3) + ' ' + r2(s * 0.7) + ' ' + r2(s * 0.3) + ' 0 ' + r2(s) + 'C' + r2(-s * 0.7) + ' ' + r2(s * 0.3) + ' ' + r2(-s * 0.7) + ' ' + r2(-s * 0.3) + ' 0 ' + r2(-s) + 'Z' }, g2);
      shp.style.fill = paint(cols[i % cols.length]);
      if (rise) shp.setAttribute('filter', 'url(#mx-glow)');
      var x = f.width * (opt(o, 'x0', 0.05) + rng() * (opt(o, 'x1', 0.95) - opt(o, 'x0', 0.05)));
      var fall = Math.min(span, 2.6 + rng() * 2.4), start = from + rng() * Math.max(0.01, span - fall);
      var y0 = rise ? f.height * (0.75 + rng() * 0.2) : -s * 2, y1 = rise ? f.height * (0.1 + rng() * 0.3) : f.height + s * 2;
      var dx = (rng() * 2 - 1) * Studio.u(8), rot = (rng() * 2 - 1) * 360, peak = rise ? 0.9 : 1;
      gs().set(g2, { autoAlpha: 0, x: x, y: y0 });
      tl.fromTo(g2, { autoAlpha: 0 }, { autoAlpha: peak, duration: 0.25, ease: 'none', immediateRender: false }, start);
      tl.fromTo(g2, { x: x, y: y0, rotation: 0 }, { x: x + dx, y: y1, rotation: rot, duration: fall, ease: rise ? 'power1.out' : 'none', immediateRender: false }, start);
      tl.fromTo(g2, { autoAlpha: peak }, { autoAlpha: 0, duration: 0.3, ease: 'none', immediateRender: false }, start + fall - 0.3);
    }
    return { el: holder };
  };
})(typeof window !== 'undefined' ? window : this);
