/*
 * Motion Lab studio runtime - typography (src/studio/studio-type.js)
 * Accessible text splitting (words / chars / lines with masks), fit-to-box, and kinetic
 * reveal recipes. Split text BEFORE adding any tween that transforms its ancestors, because
 * line detection reads layout. Requires studio-core.js and studio-draw.js.
 */
(function (global) {
  'use strict';

  var Studio = global.Studio;
  if (!Studio || !Studio.draw) throw new Error('studio-type.js requires studio-core.js and studio-draw.js');
  var T = Studio.type = {};

  function resolve(target) {
    return typeof target === 'string' ? document.querySelector(target) : target;
  }

  function normalisedText(el) {
    return el.textContent.replace(/\s+/g, ' ').trim();
  }

  function span(className) {
    var s = document.createElement('span');
    s.className = className;
    s.setAttribute('aria-hidden', 'true');
    return s;
  }

  /**
   * Split an element's text. type: any of 'lines', 'words', 'chars' joined by commas.
   * mask: 'lines' | 'words' wraps units in overflow-hidden boxes for mask reveals.
   * The element keeps an aria-label with the full text; generated spans are aria-hidden.
   * Nested inline markup (<em>, <strong>, <span class>) is preserved, including across lines.
   */
  T.split = function (target, options) {
    var el = resolve(target);
    if (!el) throw new Error('Studio.type.split: target not found');
    if (el.__studioSplit) return el.__studioSplit;
    var o = options || {};
    var type = o.type || 'lines,words';
    var wantChars = type.indexOf('chars') >= 0;
    var wantLines = type.indexOf('lines') >= 0;
    var original = el.innerHTML;
    if (!el.hasAttribute('aria-label')) el.setAttribute('aria-label', normalisedText(el));

    var words = [], chars = [];
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null);
    var textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);
    // Remember which words were preceded by whitespace in the source, so rebuilt lines only put
    // spaces where the author had them ("<em>slowly</em>." must not become "slowly .").
    var sawSpace = false;
    textNodes.forEach(function (node) {
      var frag = document.createDocumentFragment();
      node.nodeValue.split(/(\s+)/).forEach(function (part) {
        if (!part) return;
        if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(' ')); sawSpace = true; return; }
        var w = span('st-word');
        w.__stSpace = sawSpace && words.length > 0;
        sawSpace = false;
        if (wantChars) {
          Array.from(part).forEach(function (ch) {
            var c = span('st-char');
            c.textContent = ch;
            w.appendChild(c);
            chars.push(c);
          });
        } else {
          w.textContent = part;
        }
        frag.appendChild(w);
        words.push(w);
      });
      node.parentNode.replaceChild(frag, node);
    });

    var lines = [], masks = [];
    if (wantLines && words.length) {
      var groups = [], current = null;
      words.forEach(function (w) {
        var top = w.offsetTop, h = w.offsetHeight || 1;
        if (!current || top >= current.top + current.height * 0.5) {
          current = { top: top, height: h, words: [] };
          groups.push(current);
        }
        current.height = Math.max(current.height, h);
        current.words.push(w);
      });
      var frag = document.createDocumentFragment();
      groups.forEach(function (g, gi) {
        var line = span('st-line');
        var outer = line;
        if (o.mask === 'lines') {
          outer = span('st-mask');
          outer.appendChild(line);
          masks.push(outer);
        }
        var chainOrig = [], chainClone = [];
        g.words.forEach(function (w, wi) {
          var ancestors = [];
          for (var p = w.parentNode; p && p !== el; p = p.parentNode) ancestors.unshift(p);
          var k = 0;
          while (k < ancestors.length && k < chainOrig.length && ancestors[k] === chainOrig[k]) k++;
          chainOrig = chainOrig.slice(0, k);
          chainClone = chainClone.slice(0, k);
          // The space belongs to the deepest shared ancestor, so "Masala <em>chai</em>" keeps it outside <em>.
          if (wi > 0 && w.__stSpace) (k ? chainClone[k - 1] : line).appendChild(document.createTextNode(' '));
          for (var j = k; j < ancestors.length; j++) {
            var clone = ancestors[j].cloneNode(false);
            if (clone.removeAttribute) clone.removeAttribute('id');
            (j === 0 ? line : chainClone[j - 1]).appendChild(clone);
            chainOrig.push(ancestors[j]);
            chainClone.push(clone);
          }
          var parent = chainClone.length ? chainClone[chainClone.length - 1] : line;
          parent.appendChild(w);
        });
        // Trailing space collapses at the line end but keeps textContent and copy-paste intact.
        var next = groups[gi + 1];
        if (next && next.words[0].__stSpace) line.appendChild(document.createTextNode(' '));
        lines.push(line);
        frag.appendChild(outer);
      });
      el.innerHTML = '';
      el.appendChild(frag);
    }

    if (o.mask === 'words') {
      words.forEach(function (w) {
        var m = span('st-mask-inline');
        w.parentNode.insertBefore(m, w);
        m.appendChild(w);
        masks.push(m);
      });
    }

    var result = {
      el: el,
      words: words,
      chars: chars,
      lines: lines,
      masks: masks,
      revert: function () {
        el.innerHTML = original;
        el.__studioSplit = null;
      }
    };
    el.__studioSplit = result;
    return result;
  };

  /**
   * Shrink an element's font size until its content fits its width (and, with {height: true}, its
   * fixed height). Glyph overhang from tight line-heights is ignored. Run before splitting.
   * Returns the final font size in px.
   */
  /**
   * Shrink an element's font size until its content fits its width (and, with {height: true}, its
   * fixed height). Respects the legibility floor (--fs-floor, min 22px in 720p) so text never
   * shrinks into microscopic illegibility; if text overflows at min, balances lines instead.
   * Returns the final font size in px.
   */
  T.fit = function (target, options) {
    var el = resolve(target);
    var o = options || {};
    var size = o.max || parseFloat(global.getComputedStyle(el).fontSize);
    var floorPx = Studio.u ? Studio.u(3.1) : 22.3;
    var min = o.min !== undefined ? o.min : Math.max(floorPx, size * 0.5);
    el.style.fontSize = size + 'px';
    var guard = 0;
    var tooBig = function () {
      return el.scrollWidth > el.clientWidth + 1 || (o.height === true && el.scrollHeight > el.clientHeight + 1);
    };
    while (guard++ < 60 && size > min && tooBig()) {
      size = Math.max(min, size * 0.96);
      el.style.fontSize = size + 'px';
    }
    if (tooBig() && !o.nowrap) {
      el.style.textWrap = 'balance';
    }
    return size;
  };

  // ------------------------------------------------------------------ reveals
  /** Units rise out of masks (lines or words). Entrance: renders its start state immediately. */
  T.rise = function (tl, parts, at, options) {
    var o = options || {};
    var m = Studio.motion();
    var els = Studio.all(parts);
    var dur = o.duration || m.enter;
    var stagger = o.stagger === undefined ? m.stagger * 1.6 : o.stagger;
    tl.fromTo(els,
      { yPercent: o.from === undefined ? 110 : o.from, autoAlpha: o.fade === false ? 1 : 0 },
      { yPercent: 0, autoAlpha: 1, duration: dur, ease: o.ease || m.easeOut, stagger: stagger },
      at);
    return at + dur + stagger * Math.max(0, els.length - 1);
  };

  /** Characters drop into place with seeded rotation; reads as handset type. */
  T.cascade = function (tl, chars, at, options) {
    var o = options || {};
    var m = Studio.motion();
    var els = Studio.all(chars);
    var r = Studio.rng(o.seed || 7);
    var rot = els.map(function () { return (r() * 2 - 1) * (o.rotate === undefined ? 14 : o.rotate); });
    var dy = els.map(function () { return -(0.4 + r() * 0.5) * (o.distance === undefined ? 1 : o.distance); });
    var dur = o.duration || m.enter * 0.8;
    var stagger = o.stagger === undefined ? 0.03 : o.stagger;
    tl.fromTo(els,
      { yPercent: function (i) { return dy[i] * 100; }, rotation: function (i) { return rot[i]; }, autoAlpha: 0 },
      { yPercent: 0, rotation: 0, autoAlpha: 1, duration: dur, ease: o.ease || 'back.out(1.7)', stagger: stagger },
      at);
    return at + dur + stagger * Math.max(0, els.length - 1);
  };

  /** Letter-spacing (tracking) settles from wide to set value while fading in. */
  T.track = function (tl, target, at, options) {
    var o = options || {};
    var m = Studio.motion();
    var dur = o.duration || m.enter * 1.4;
    tl.fromTo(target,
      { letterSpacing: o.from || '0.6em', autoAlpha: 0 },
      { letterSpacing: o.to || '0.12em', autoAlpha: 1, duration: dur, ease: o.ease || 'power3.out' },
      at);
    return at + dur;
  };

  /**
   * Weight shift (variable-font axis where the face supports it). With static faces the
   * browser snaps to the nearest instance, so treat as experimental and check frames.
   */
  T.weight = function (tl, target, at, options) {
    var o = options || {};
    var dur = o.duration || 0.8;
    tl.fromTo(target,
      { fontWeight: o.from || 300 },
      { fontWeight: o.to || 800, duration: dur, ease: o.ease || 'power2.inOut', immediateRender: o.immediateRender !== false },
      at);
    return at + dur;
  };

  /** Typewriter: characters appear one by one at `cps` characters per second (seek-safe). */
  T.typewriter = function (tl, chars, at, options) {
    var o = options || {};
    var els = Studio.all(chars);
    var step = 1 / (o.cps || 24);
    tl.fromTo(els, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.001, ease: 'none', stagger: step }, at);
    return at + step * els.length;
  };

  /** Marker highlight that sweeps behind the text. Inserts one span; element must be inline-block or block. */
  T.highlight = function (tl, target, at, options) {
    var o = options || {};
    var el = resolve(target);
    if (global.getComputedStyle(el).position === 'static') el.style.position = 'relative';
    el.style.isolation = 'isolate';
    var hl = el.querySelector(':scope > .st-highlight') || span('st-highlight');
    if (!hl.parentNode) el.insertBefore(hl, el.firstChild);
    if (o.color) hl.style.background = o.color;
    var dur = o.duration || 0.6;
    tl.fromTo(hl, { scaleX: 0, transformOrigin: o.from === 'right' ? '100% 50%' : '0% 50%' }, { scaleX: 1, duration: dur, ease: o.ease || 'power2.inOut' }, at);
    return at + dur;
  };

  /**
   * Hand-drawn underline under `target` (seeded wobble). The SVG is appended to options.host
   * (default: the target itself) so it can sit outside overflow masks; position is measured from
   * layout offsets, which ignore transforms already applied by entrance tweens.
   */
  T.underline = function (tl, target, at, options) {
    var o = options || {};
    var el = resolve(target);
    var host = o.host ? resolve(o.host) : el;
    if (global.getComputedStyle(host).position === 'static') host.style.position = 'relative';
    var x = 0, y = 0;
    if (host !== el) {
      for (var n = el; n && n !== host; n = n.offsetParent) {
        x += n.offsetLeft || 0;
        y += n.offsetTop || 0;
      }
    }
    var w = el.offsetWidth, eh = el.offsetHeight;
    var h = Math.max(6, eh * (o.height || 0.2));
    var svg = Studio.svg('svg', {
      'class': 'st-underline', width: w, height: h, viewBox: '0 0 ' + w + ' ' + h,
      'aria-hidden': 'true', 'data-layout-ignore': ''
    });
    svg.style.left = x + 'px';
    svg.style.top = (y + eh * (o.offset === undefined ? 0.86 : o.offset)) + 'px';
    host.appendChild(svg);
    var pad = Math.min(h * 0.3, w * 0.05);
    var d = Studio.draw.handLine(o.seed || 11, pad, h * 0.55, w - pad, h * 0.4, { segments: 5, jitter: o.jitter || 0.01 });
    var path = Studio.svg('path', { d: d, fill: 'none', 'class': 'st-underline-path' }, svg);
    if (o.color) path.style.stroke = o.color;
    return Studio.draw.stroke(tl, path, at, { duration: o.duration || 0.6, ease: o.ease || 'power2.inOut' });
  };

  /** Integer counter (seek-safe: GSAP sets innerText on every render, no callbacks). */
  T.count = function (tl, target, at, options) {
    var o = options || {};
    var dur = o.duration || 1.2;
    tl.fromTo(target, { innerText: o.from || 0 }, { innerText: o.to, duration: dur, ease: o.ease || 'power2.out', snap: { innerText: 1 } }, at);
    return at + dur;
  };

  /** Exit: units slide up out of their masks. Never renders early (immediateRender:false). */
  T.exit = function (tl, parts, at, options) {
    var o = options || {};
    var m = Studio.motion();
    var els = Studio.all(parts);
    var dur = o.duration || m.exit;
    var stagger = o.stagger === undefined ? m.stagger : o.stagger;
    tl.fromTo(els, { yPercent: 0, autoAlpha: 1 }, { yPercent: o.to === undefined ? -105 : o.to, autoAlpha: 0, duration: dur, ease: o.ease || m.easeIn, stagger: stagger, immediateRender: false }, at);
    return at + dur + stagger * Math.max(0, els.length - 1);
  };

  /**
   * Slot roll: a one-line window onto a column of words or numbers that steps to an entry with a
   * small mechanical overshoot. The window is as wide as the widest entry, or with options.fit it
   * tweens to each entry's own width so a centred sentence re-centres around the current word.
   * Returns {el, items, to(tl, index, at, {duration, ease}) -> end time}. Starts on items[0].
   */
  T.roll = function (parent, items, options) {
    var o = options || {};
    var host = resolve(parent);
    var box = Studio.el('span', 'st-roll' + (o.className ? ' ' + o.className : ''), null, host);
    box.setAttribute('aria-label', items.join(', '));
    var col = Studio.el('span', 'st-roll-col', null, box);
    col.setAttribute('aria-hidden', 'true');
    var texts = [];
    var els = items.map(function (txt) {
      var item = Studio.el('span', 'st-roll-item', null, col);
      texts.push(Studio.el('span', 'st-roll-text', txt, item));
      return item;
    });
    if (o.align) box.style.textAlign = o.align;
    var widths = texts.map(function (t) { return t.offsetWidth; });
    if (o.fit) {
      box.style.textAlign = o.align || 'left';
      box.style.width = widths[0] + 'px';
    }
    var current = 0;
    return {
      el: box,
      items: els,
      to: function (tl, index, at, so) {
        var s = so || {};
        var dur = s.duration || 0.55;
        var ease = s.ease || 'back.out(1.5)';
        var n = els.length;
        tl.fromTo(col, { yPercent: -100 * current / n }, { yPercent: -100 * index / n, duration: dur, ease: ease, immediateRender: false }, at);
        if (o.fit) tl.fromTo(box, { width: widths[current] }, { width: widths[index], duration: dur * 0.8, ease: 'power3.inOut', immediateRender: false }, at);
        current = index;
        return at + dur;
      }
    };
  };
  /**
   * Hero header: coordinated kicker, display title and lede/subtitle with masked line splitting.
   * Enforces font size hierarchy and clean multi-beat entrance/exit choreography.
   */
  T.heroHeader = function (parent, data, options) {
    var o = options || {};
    var host = resolve(parent);
    var el = Studio.el('div', 'st-hero-header' + (o.center ? ' center' : '') + (o.className ? ' ' + o.className : ''), null, host);
    var kicker = data.kicker ? Studio.el('div', 'st-kicker', data.kicker, el) : null;
    var title = Studio.el(o.tag || 'h1', 'st-display', null, el);
    if (data.titleHTML) title.innerHTML = data.titleHTML;
    else title.textContent = data.title || '';
    var subtitle = data.subtitle ? Studio.el('p', 'st-subtitle', data.subtitle, el) : null;

    if (o.fit !== false) {
      T.fit(title, { min: Studio.u(5.5), max: Studio.u(o.maxU || 9.5) });
    }
    var titleSplit = T.split(title, { type: 'lines,words', mask: 'lines' });
    var subSplit = subtitle ? T.split(subtitle, { type: 'words', mask: o.maskSubtitle ? 'words' : null }) : null;

    return {
      el: el,
      kicker: kicker,
      title: title,
      subtitle: subtitle,
      titleSplit: titleSplit,
      subSplit: subSplit,
      enter: function (tl, at, eo) {
        var e = eo || {};
        var dur = e.duration || 0.7;
        var end = at;
        if (kicker) {
          end = Math.max(end, T.track(tl, kicker, at, { from: '0.5em', to: '0.16em', duration: dur * 0.9 }));
        }
        end = Math.max(end, T.rise(tl, titleSplit.lines, at + 0.12, { duration: dur, stagger: e.stagger || 0.08 }));
        if (subSplit) {
          tl.fromTo(subSplit.words, { autoAlpha: 0, yPercent: 40 }, { autoAlpha: 1, yPercent: 0, duration: 0.5, ease: 'power2.out', stagger: 0.03 }, end - 0.25);
          end = Math.max(end, end - 0.25 + 0.5 + 0.03 * (subSplit.words.length - 1));
        }
        return end;
      },
      exit: function (tl, at, eo) {
        var end = T.exit(tl, titleSplit.lines, at, { stagger: 0.04 });
        var rest = [kicker, subtitle].filter(Boolean);
        if (rest.length) {
          tl.fromTo(rest, { autoAlpha: 1 }, { autoAlpha: 0, duration: 0.3, ease: 'power1.in', immediateRender: false }, at);
        }
        return Math.max(end, at + 0.3);
      }
    };
  };

  /**
   * Spoken punch word emphasis: momentary scale surge, weight pop, and accent color flash.
   * Seek-safe and deterministic with explicit color restoration.
   */
  T.punch = function (tl, target, at, options) {
    var o = options || {};
    var els = Studio.all(target);
    var dur = o.duration || 0.45;
    var scale = o.scale || 1.15;
    var color = o.color || Studio.token('--c-accent', '#ba4128');
    var ease = o.ease || 'back.out(2)';
    tl.fromTo(els,
      { scale: 1 },
      { scale: scale, duration: dur * 0.4, ease: ease, yoyo: true, repeat: 1, immediateRender: false },
      at);
    if (color && els.length) {
      var baseColor = global.getComputedStyle(els[0]).color || '#ba4128';
      tl.fromTo(els,
        { color: baseColor },
        { color: color, duration: dur * 0.5, ease: 'power1.out', yoyo: true, repeat: 1, immediateRender: false },
        at);
    }
    return at + dur;
  };

  /**
   * Formatted rolling counter with prefix, suffix, comma grouping, and decimals.
   * Seek-safe: defines a getter/setter property on target that GSAP directly tweens.
   */
  T.formatCount = function (tl, target, at, options) {
    var o = options || {};
    var el = resolve(target);
    var fromVal = o.from !== undefined ? o.from : 0;
    var toVal = o.to !== undefined ? o.to : 100;
    var dur = o.duration || 1.6;
    var decimals = o.decimals || 0;
    var prefix = o.prefix || '';
    var suffix = o.suffix || '';
    var commas = o.commas !== false;

    function formatNumber(num) {
      var n = Number(num);
      if (isNaN(n)) n = 0;
      var fixed = n.toFixed(decimals);
      if (commas) {
        var parts = fixed.split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        fixed = parts.join('.');
      }
      return prefix + fixed + suffix;
    }

    if (!el.__stNumBound) {
      var currentVal = fromVal;
      Object.defineProperty(el, '__stNum', {
        get: function () { return currentVal; },
        set: function (v) {
          currentVal = v;
          el.textContent = formatNumber(v);
        },
        configurable: true
      });
      el.__stNumBound = true;
    }
    el.__stNum = fromVal;
    tl.fromTo(el,
      { __stNum: fromVal },
      { __stNum: toVal, duration: dur, ease: o.ease || 'power2.out', immediateRender: true },
      at);
    return at + dur;
  };
})(typeof window !== 'undefined' ? window : this);
