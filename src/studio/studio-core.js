/*
 * Motion Lab studio runtime - core (src/studio/studio-core.js)
 *
 * Deterministic helpers for HyperFrames compositions. Copied into each project as
 * src/_studio/ by `python scripts/studio.py sync <slug>`; edit the canonical copy in
 * src/studio/ only. Rules this runtime enforces or assumes:
 *   - one paused GSAP timeline registered on window.__timelines[<composition id>]
 *     at the END of the (possibly async) build;
 *   - no wall clock, no Math.random, no requestAnimationFrame, no tween callbacks
 *     that write to the DOM (seeks may suppress callbacks);
 *   - fromTo() for every animated property so random-order seeks are stable;
 *   - GSAP owns transforms: never set CSS `transform` on an element GSAP animates.
 */
(function (global) {
  'use strict';

  var Studio = global.Studio || (global.Studio = {});
  Studio.version = '1.18.0';   // 1.18.0: explanation devices (studio-explain.js): Studio.comp.equation, slider, tracePair, simulation + simulationScript, barRace, progression, copySlot, ui (input, button, toggle, cursor, notify), headline (pair, build), Studio.space.tour, Studio.fx.dip; device table specs/explanation-devices.json, handbook docs/explanation-devices.md; fitness kit, Tibi 0.9.0, anatomy and sculpt unchanged from 1.17.0. 1.17.0: reference-backlog techniques: Studio.fx.flash (flash-frame cut, flat or radial, pre-dim, WCAG 2.3.1 guard), Studio.fx.containerTransform (tile-to-card proxy with styled snapshots), Studio.type.scramble (seeded, seek-safe decode), Studio.type.strike / strikeCorrect, caption lane 'subject' (cue.anchor, cue.side; storyboard caption_anchor / caption_side); fitness kit, Tibi 0.9.0, anatomy and sculpt unchanged from 1.16.0. 1.16.0: Tibi 0.9.0 (optional garS picks the bar-alignment hand-roll branch: overhead grips no longer flip a half turn), 3D motion family 3 on the shoulder girdle (seated dumbbell overhead press, lat pulldown, pull-up, seated cable row, one-arm dumbbell row + mistake variants: lower-back arch, swing-back, short range, trunk rock, torso twist; T3.girdleJoint, chest-frame arm solvers, balance-solved hang); anatomy 1.6.0 and sculpt 2.2.0 unchanged. 1.15.1: stations.js exercise card (anatomy 1.6.0, Tibi 0.8.0, sculpt 2.2.0 unchanged): reading text floor 2.6% of the short side (--sn-read-floor), chips drop before text shrinks (prime movers kept), fitCard measures leaf content not the flex slot, audit card-below-floor. 1.15.0: anatomy 1.6.0 (female top tint, effort reach, hinge shorts, girdle field 70), Tibi 0.8.0 (shoulder girdle bones gdL/gdR/axL/axR, kwS/kvS knee aim, jointed ponytail), 3D library (deadlift, RDL, split squat, lunge, push-up, plank, leg extension, leg curl, leg press, barbell bench, rack squat + mistake variants), sculpt 2.2.0, studio-film.js helpers, kits/fitness/stations.js. 1.14.0: known limits (anatomy 1.4.0, Tibi 0.6.0): flat glute fan, shape-weighted effort tint and subdued cloth tint, solid glute cutaway, female deltoid, shoulder-ridge weights, deep-flexion correctives; ponytail follow-through, bench arch, bending sole and foot roll. 1.13.0: stage.fit / T3.fitScene / T3.scene({fit}) solve a 3D camera from the posed body and equipment over a whole set.

  // Mirrors specs/format-presets.json; used only when the generated #studio-format block is missing.
  var SAFE_DEFAULTS = {
    landscape: { top: 0.06, right: 0.05, bottom: 0.08, left: 0.05 },
    portrait: { top: 0.10, right: 0.10, bottom: 0.234, left: 0.06 },
    square: { top: 0.07, right: 0.07, bottom: 0.09, left: 0.07 }
  };

  function rootElement() {
    return document.getElementById('root') || document.querySelector('[data-composition-id]');
  }

  function cssPx(styles, name) {
    var v = parseFloat(styles.getPropertyValue(name));
    return isNaN(v) ? null : v;
  }

  function readFormat() {
    var root = rootElement();
    if (!root) throw new Error('Studio: no #root / [data-composition-id] element found.');
    var w = parseInt(root.getAttribute('data-width'), 10);
    var h = parseInt(root.getAttribute('data-height'), 10);
    if (!(w > 0 && h > 0)) throw new Error('Studio: #root needs numeric data-width and data-height.');
    var id = root.getAttribute('data-format') || (w > h ? 'landscape' : (w < h ? 'portrait' : 'square'));
    var unit = Math.min(w, h) / 100;
    var styles = global.getComputedStyle(document.documentElement);
    var preset = SAFE_DEFAULTS[id] || SAFE_DEFAULTS.landscape;
    var safe = {
      top: cssPx(styles, '--safe-top'),
      right: cssPx(styles, '--safe-right'),
      bottom: cssPx(styles, '--safe-bottom'),
      left: cssPx(styles, '--safe-left')
    };
    if (safe.top === null) safe.top = Math.round(preset.top * h);
    if (safe.right === null) safe.right = Math.round(preset.right * w);
    if (safe.bottom === null) safe.bottom = Math.round(preset.bottom * h);
    if (safe.left === null) safe.left = Math.round(preset.left * w);
    safe.width = w - safe.left - safe.right;
    safe.height = h - safe.top - safe.bottom;
    return {
      id: id,
      compositionId: root.getAttribute('data-composition-id') || 'root',
      width: w,
      height: h,
      aspect: w / h,
      unit: unit,
      fps: parseInt(root.getAttribute('data-fps'), 10) || 30,
      duration: parseFloat(root.getAttribute('data-duration')) || 0,
      safe: safe,
      isLandscape: id === 'landscape',
      isPortrait: id === 'portrait',
      isSquare: id === 'square'
    };
  }

  var formatCache = null;
  Object.defineProperty(Studio, 'format', {
    configurable: true,
    get: function () {
      if (!formatCache) formatCache = readFormat();
      return formatCache;
    }
  });

  /** Format-relative length: n percent of the frame's short side, in px. */
  Studio.u = function (n) { return n * Studio.format.unit; };

  /** Choose a value per format: pick({landscape: a, portrait: b, square: c, default: d}). */
  Studio.pick = function (map) {
    var id = Studio.format.id;
    if (Object.prototype.hasOwnProperty.call(map, id)) return map[id];
    if (Object.prototype.hasOwnProperty.call(map, 'default')) return map['default'];
    if (id === 'square' && Object.prototype.hasOwnProperty.call(map, 'portrait')) return map.portrait;
    return map.landscape;
  };

  // ---------------------------------------------------------------- randomness
  /** Seeded mulberry32 PRNG. Never use Math.random in compositions. */
  Studio.rng = function (seed) {
    var a = (seed >>> 0) || 0x9e3779b9;
    var next = function () {
      a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), a | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    next.range = function (lo, hi) { return lo + (hi - lo) * next(); };
    next.int = function (lo, hi) { return Math.floor(lo + (hi - lo + 1) * next()); };
    next.sign = function () { return next() < 0.5 ? -1 : 1; };
    next.pick = function (arr) { return arr[Math.floor(next() * arr.length) % arr.length]; };
    return next;
  };

  /** Smooth seeded 1-D value noise in [-1, 1]: noise(x). */
  Studio.noise1 = function (seed) {
    var r = Studio.rng(seed);
    var table = [];
    for (var i = 0; i < 256; i++) table.push(r() * 2 - 1);
    return function (x) {
      var i0 = Math.floor(x), f = x - i0;
      var a = table[((i0 % 256) + 256) % 256];
      var b = table[(((i0 + 1) % 256) + 256) % 256];
      var s = f * f * (3 - 2 * f);
      return a + (b - a) * s;
    };
  };

  /** Stable 32-bit hash of a string, for deriving per-element seeds. */
  Studio.hash = function (str) {
    var h = 2166136261;
    for (var i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  };

  // ---------------------------------------------------------------- style tokens
  /** Read a CSS custom property from :root (style tokens such as --c-accent). */
  Studio.token = function (name, fallback) {
    var v = global.getComputedStyle(document.documentElement).getPropertyValue(name);
    v = v ? v.trim() : '';
    return v || fallback;
  };

  /** Motion tokens from the active style system (studio styles set these on :root). */
  Studio.motion = function () {
    return {
      easeOut: Studio.token('--ease-out', 'power3.out'),
      easeIn: Studio.token('--ease-in', 'power2.in'),
      easeInOut: Studio.token('--ease-in-out', 'power2.inOut'),
      enter: parseFloat(Studio.token('--dur-enter', '0.7')),
      exit: parseFloat(Studio.token('--dur-exit', '0.45')),
      stagger: parseFloat(Studio.token('--stagger', '0.05'))
    };
  };

  // ---------------------------------------------------------------- timeline
  Studio.timeline = function (vars) {
    if (!global.gsap) throw new Error('Studio: GSAP must be loaded before the studio runtime builds.');
    var v = vars || {};
    v.paused = true;
    return global.gsap.timeline(v);
  };

  function reportError(err) {
    var root = rootElement();
    if (root) root.setAttribute('data-studio-error', String(err && err.message ? err.message : err));
    if (global.console) global.console.error('[studio] build failed:', err);
  }

  /**
   * Build the composition once fonts are ready, then register the timeline last.
   * builder(tl, format, Studio) must add every tween synchronously.
   */
  Studio.build = function (builder, options) {
    var opts = options || {};
    var run = function () {
      try {
        var tl = Studio.timeline(opts.timeline);
        builder(tl, Studio.format, Studio);
        var declared = Studio.format.duration;
        if (declared && tl.duration() > declared + 1e-3 && global.console) {
          global.console.warn('[studio] timeline (' + tl.duration().toFixed(3) + 's) runs past data-duration (' + declared + 's); the tail never renders.');
        }
        Studio.register(tl, opts.id);
        Studio.tl = tl;
      } catch (err) {
        reportError(err);
      }
    };
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(run, run);
    else run();
  };

  Studio.register = function (tl, id) {
    var key = id || Studio.format.compositionId;
    global.__timelines = global.__timelines || {};
    window.__timelines = window.__timelines || {};
    window.__timelines[key] = tl;
    global.__timelines[key] = tl;
    var root = rootElement();
    if (root) root.setAttribute('data-studio-ready', 'true');
    return tl;
  };

  // ---------------------------------------------------------------- scenes
  // When GSAP rewinds a tween it restores the values it recorded before that tween first
  // rendered; for autoAlpha that is the element's opacity, not its CSS visibility. Entrances
  // therefore render their hidden start state immediately, exits use immediateRender:false so they
  // never act early, and switches last 1 ms (not 0) so a frame landing exactly on the cue renders
  // the same state whichever direction it was approached from.
  var SWITCH = 0.001;

  /** Make a scene (or any element) visible from `at` onward; at <= 0 means visible on frame 0. */
  Studio.show = function (tl, target, at) {
    if (at <= 0) {
      global.gsap.set(target, { autoAlpha: 1 });
      return 0;
    }
    tl.fromTo(target, { autoAlpha: 0 }, { autoAlpha: 1, duration: SWITCH, ease: 'none', immediateRender: true }, at);
    return at;
  };

  /** Hide a scene from `at` onward. */
  Studio.hide = function (tl, target, at) {
    tl.fromTo(target, { autoAlpha: 1 }, { autoAlpha: 0, duration: SWITCH, ease: 'none', immediateRender: false }, at);
    return at;
  };

  /** Zero-dip crossfade centred on `at` (catalogue recipe zero-dip-scene-transition). */
  Studio.crossfade = function (tl, outTarget, inTarget, at, fade) {
    var f = fade === undefined ? 0.5 : fade;
    var start = Math.max(0, at - f / 2);
    tl.fromTo(inTarget, { autoAlpha: 0 }, { autoAlpha: 1, duration: f, ease: 'power1.inOut', immediateRender: true }, start);
    tl.fromTo(outTarget, { autoAlpha: 1 }, { autoAlpha: 0, duration: f, ease: 'power1.inOut', immediateRender: false }, start);
    return start + f;
  };

  /** Hard cut at `at`. */
  Studio.cut = function (tl, outTarget, inTarget, at) {
    Studio.show(tl, inTarget, at);
    Studio.hide(tl, outTarget, at);
    return at;
  };

  /** Number of whole cycles of length `period` that fit in [from, to]; used for finite loops. */
  Studio.cycles = function (from, to, period) {
    return Math.max(0, Math.floor((to - from) / period + 1e-6));
  };

  /** Convert a cue map ({name: seconds}) into an accessor with offsets: at('pour', 0.4). */
  Studio.cues = function (map) {
    var fn = function (name, offset) {
      if (!Object.prototype.hasOwnProperty.call(map, name)) throw new Error('Studio: unknown cue "' + name + '"');
      return map[name] + (offset || 0);
    };
    fn.map = map;
    return fn;
  };

  /** Builds an SVG element in the SVG namespace with attributes. */
  Studio.svg = function (tag, attrs, parent) {
    var el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    if (attrs) {
      for (var k in attrs) {
        if (Object.prototype.hasOwnProperty.call(attrs, k)) el.setAttribute(k, attrs[k]);
      }
    }
    if (parent) parent.appendChild(el);
    return el;
  };

  /** Builds an HTML element with a class name and optional text. */
  Studio.el = function (tag, className, text, parent) {
    var el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined && text !== null) el.textContent = text;
    if (parent) parent.appendChild(el);
    return el;
  };

  /** Resolve a selector, element, or list of selectors/elements into a flat array of elements. */
  Studio.all = function (target, scope) {
    if (!target) return [];
    if (typeof target === 'string') return Array.prototype.slice.call((scope || document).querySelectorAll(target));
    if (target.length !== undefined && !target.nodeType) {
      var out = [];
      Array.prototype.forEach.call(target, function (item) { out = out.concat(Studio.all(item, scope)); });
      return out;
    }
    return [target];
  };

  /**
   * Box of `target` in #root pixels as it renders at time `t` of `tl` (seeks there, measures, seeks
   * back). Lets transitions and annotations aim at elements that earlier tweens have moved.
   * Returns {x, y, w, h, cx, cy}.
   */
  Studio.boxAt = function (tl, target, t) {
    var el = Studio.all(target)[0];
    if (!el) throw new Error('Studio.boxAt: target not found');
    var prev = tl.time();
    var seek = t !== undefined && t !== null;
    if (seek) tl.seek(t, true);
    var root = rootElement().getBoundingClientRect();
    var r = el.getBoundingClientRect();
    if (seek) tl.seek(prev, true);
    var x = r.left - root.left, y = r.top - root.top;
    return { x: x, y: y, w: r.width, h: r.height, cx: x + r.width / 2, cy: y + r.height / 2 };
  };
})(typeof window !== 'undefined' ? window : this);
