/*
 * Motion Lab fitness kit - movement library for Tibi (Cobalt Sculpt)
 * (src/studio/kits/fitness/exercises.js). Needs brand.js, studio-rig.js, sculpt-data.js, sculpt.js.
 *
 * Kinematics are CONCEPTUAL: joint angles are authored from typical ranges described in exercise
 * science texts (NSCA Essentials of Strength Training and Conditioning 4e; Novacheck 1998 for gait)
 * so the movements read correctly, but they are not motion capture. Never present them as data.
 * Descriptive metadata (muscles, cues, errors, alternatives) is in assets/fitness/data/exercises.json
 * and reaches the page as Studio.kit.fitness.library.
 *
 * Every exercise picks the camera that keeps its motion in the picture plane: side (sagittal),
 * front, back, 'top' (prone, seen from above) or 'above' (supine, seen from above). Equipment is
 * placed from Tibi's own joints after the start pose is set, so it fits any scale and either gender.
 * Hands that hold something close around the handle (pose channel ch.grip = 1); dumbbells ride the
 * hand (attach) or follow the grip point (follow) and are drawn in the same flat planes as Tibi.
 */
(function (global) {
  'use strict';

  var Studio = global.Studio || (global.Studio = {});
  var F = (Studio.kit = Studio.kit || {}).fitness = (Studio.kit.fitness || {});
  var P = F.palette;
  var RIG = Studio.rig;
  if (!P || !RIG || !F.sculpt) throw new Error('kits/fitness/exercises.js needs brand.js, studio-rig.js and sculpt.js loaded first');
  function svg(tag, attrs, parent) { return Studio.svg(tag, attrs, parent); }
  function num(v) { return Math.round(v * 100) / 100; }
  function own(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }
  function both(j) {
    var out = {};
    for (var k in j) if (own(j, k)) { out[k] = j[k]; if (/R$/.test(k) && j[k.replace(/R$/, 'L')] === undefined) out[k.replace(/R$/, 'L')] = j[k]; }
    return out;
  }

  // ------------------------------------------------------------------ equipment (flat planes, no outlines)
  var EQ = F.equipment = {};
  /** A dumbbell seen end-on (handle into the screen), centred on the handle; s = rig units per plate radius / 22. */
  EQ.dumbbellEnd = function (parent, s) {
    var k = s || 1, g = svg('g', { 'class': 'eq-dumbbell' }, parent);
    svg('ellipse', { cx: num(7 * k), cy: num(-5 * k), rx: num(20 * k), ry: num(21 * k), fill: P.plate }, g);                // far plate
    svg('rect', { x: num(-4 * k), y: num(-7 * k), width: num(12 * k), height: num(7 * k), rx: num(3.5 * k), fill: P.steelShade, transform: 'rotate(-35)' }, g);
    svg('circle', { r: num(22 * k), fill: P.plate }, g);                                                                     // near plate
    svg('circle', { r: num(16 * k), fill: P.plateFace }, g);
    svg('path', { d: 'M' + num(-15 * k) + ' ' + num(-8 * k) + ' A' + num(16 * k) + ' ' + num(16 * k) + ' 0 0 1 ' + num(8 * k) + ' ' + num(-14 * k), fill: 'none', stroke: P.plateRim, 'stroke-width': num(3 * k), 'stroke-linecap': 'round' }, g);
    svg('circle', { r: num(4.5 * k), fill: P.steel }, g);
    return g;
  };
  /** A dumbbell whose handle runs along local x (seen from the front or from above), centred on the handle. */
  EQ.dumbbellBar = function (parent, s, half) {
    var k = s || 1, h = (half || 22) * k, g = svg('g', { 'class': 'eq-dumbbell' }, parent);
    svg('rect', { x: num(-h), y: num(-3.5 * k), width: num(2 * h), height: num(7 * k), rx: num(3.5 * k), fill: P.steel }, g);
    svg('rect', { x: num(-h), y: num(-0.5 * k), width: num(2 * h), height: num(3.5 * k), fill: P.steelShade }, g);
    [-1, 1].forEach(function (sd) {
      var x0 = sd > 0 ? h : -h - 10 * k;
      svg('rect', { x: num(x0), y: num(-21 * k), width: num(10 * k), height: num(42 * k), rx: num(4 * k), fill: P.plate }, g);
      svg('rect', { x: num(x0 + 1.6 * k), y: num(-18.5 * k), width: num(3 * k), height: num(37 * k), rx: num(1.5 * k), fill: P.plateRim, opacity: 0.8 }, g);
    });
    return g;
  };
  /** A dumbbell held by its top plate (two-hand overhead extension); its axis runs along local y. */
  EQ.dumbbellHang = function (parent, s) {
    var k = s || 1, g = svg('g', { 'class': 'eq-dumbbell' }, parent);
    svg('rect', { x: num(-3.5 * k), y: num(-30 * k), width: num(7 * k), height: num(34 * k), rx: num(3.5 * k), fill: P.steel }, g);
    svg('rect', { x: num(-21 * k), y: num(-40 * k), width: num(42 * k), height: num(10 * k), rx: num(4 * k), fill: P.plate }, g);
    svg('rect', { x: num(-21 * k), y: num(4 * k), width: num(42 * k), height: num(10 * k), rx: num(4 * k), fill: P.plate }, g);
    svg('rect', { x: num(-18 * k), y: num(5.6 * k), width: num(36 * k), height: num(3 * k), rx: num(1.5 * k), fill: P.plateRim, opacity: 0.8 }, g);
    return g;
  };
  /** A flat or incline bench in side view. o = {x0, x1 (pad ends), top (pad top y), floor, incline: {x, y} back-rest top} */
  EQ.benchSide = function (parent, o) {
    var g = svg('g', { 'class': 'eq-bench' }, parent), th = o.thick || 13;
    var legs = [o.x0 + 18, o.x1 - 18];
    legs.forEach(function (x) {
      svg('rect', { x: num(x - 5), y: num(o.top + th), width: 10, height: num(o.floor - o.top - th), fill: P.steelShade }, g);
      svg('rect', { x: num(x - 22), y: num(o.floor - 6), width: 44, height: 6, rx: 3, fill: P.steelShade }, g);
    });
    svg('rect', { x: num(o.x0 + 12), y: num(o.top + th + 4), width: num(o.x1 - o.x0 - 24), height: 7, fill: P.steelShade }, g);
    if (o.incline) {
      var a = o.incline, dx = a.x - o.x0, dy = a.y - o.top, L = Math.sqrt(dx * dx + dy * dy), ang = Math.atan2(dy, dx) * 180 / Math.PI;
      var bk = svg('g', { transform: 'translate(' + num(o.x0) + ' ' + num(o.top) + ') rotate(' + num(ang) + ')' }, g);
      svg('rect', { x: 0, y: -th, width: num(L), height: th, rx: 5, fill: P.pad }, bk);
      svg('rect', { x: 4, y: -th, width: num(L - 8), height: 3.5, rx: 1.75, fill: P.padTop }, bk);
      svg('rect', { x: num(L * 0.55 - 4), y: 0, width: 8, height: num(Math.max(0, o.floor - o.top) * 0.8), fill: P.steelShade, transform: 'rotate(' + num(-ang + 90 - 90) + ' ' + num(L * 0.55) + ' 0)' }, bk);
    }
    svg('rect', { x: num(o.x0), y: num(o.top), width: num(o.x1 - o.x0), height: th, rx: 5, fill: P.pad }, g);
    svg('rect', { x: num(o.x0 + 4), y: num(o.top), width: num(o.x1 - o.x0 - 8), height: 3.5, rx: 1.75, fill: P.padTop }, g);
    return g;
  };
  /** A bench seen from above: o = {x0, x1, y (centre line), w}. */
  EQ.benchTop = function (parent, o) {
    var g = svg('g', { 'class': 'eq-bench' }, parent), w = o.w || 34;
    svg('rect', { x: num(o.x0 + 8), y: num(o.y - w / 2 - 6), width: 12, height: num(w + 12), rx: 3, fill: P.steelShade }, g);
    svg('rect', { x: num(o.x1 - 20), y: num(o.y - w / 2 - 6), width: 12, height: num(w + 12), rx: 3, fill: P.steelShade }, g);
    svg('rect', { x: num(o.x0), y: num(o.y - w / 2), width: num(o.x1 - o.x0), height: num(w), rx: 8, fill: P.pad }, g);
    svg('rect', { x: num(o.x0 + 5), y: num(o.y - w / 2 + 3), width: num(o.x1 - o.x0 - 10), height: 4, rx: 2, fill: P.padTop }, g);
    return g;
  };
  /** A seat seen from the front (seated press): o = {x, top, floor, w}. */
  EQ.seatFront = function (parent, o) {
    var g = svg('g', { 'class': 'eq-bench' }, parent), w = o.w || 90, th = 14;
    svg('rect', { x: num(o.x - w / 2 + 8), y: num(o.top + th), width: 9, height: num(o.floor - o.top - th), fill: P.steelShade }, g);
    svg('rect', { x: num(o.x + w / 2 - 17), y: num(o.top + th), width: 9, height: num(o.floor - o.top - th), fill: P.steelShade }, g);
    svg('rect', { x: num(o.x - w / 2), y: num(o.top), width: num(w), height: th, rx: 5, fill: P.pad }, g);
    svg('rect', { x: num(o.x - w / 2 + 4), y: num(o.top), width: num(w - 8), height: 3.5, rx: 1.75, fill: P.padTop }, g);
    return g;
  };
  /** A horizontal bar (pull-up bar seen from behind, dip bar end): o = {x0, x1, y, r}. */
  EQ.bar = function (parent, o) {
    var g = svg('g', { 'class': 'eq-bar' }, parent), r = o.r || 5;
    svg('rect', { x: num(o.x0), y: num(o.y - r), width: num(o.x1 - o.x0), height: num(2 * r), rx: num(r), fill: P.steel }, g);
    svg('rect', { x: num(o.x0), y: num(o.y + r * 0.2), width: num(o.x1 - o.x0), height: num(r * 0.8), fill: P.steelShade }, g);
    if (o.posts) o.posts.forEach(function (x) { svg('rect', { x: num(x - 6), y: num(o.y - r - 4), width: 12, height: num((o.floor || o.y + 400) - o.y + r + 4), fill: P.steelShade }, g); });
    return g;
  };
  /** A dip station in side view: the bars run front to back, so the near bar is a long rail with a post under each end. o = {x (hand), y (bar), floor, len}. */
  EQ.dipSide = function (parent, o) {
    var g = svg('g', { 'class': 'eq-bar' }, parent), L = o.len || 190, x0 = o.x - L * 0.4, x1 = o.x + L * 0.6;
    [x0 + 8, x1 - 8].forEach(function (x) {
      svg('rect', { x: num(x - 5), y: num(o.y), width: 10, height: num(o.floor - o.y), fill: P.steelShade }, g);
      svg('rect', { x: num(x - 26), y: num(o.floor - 6), width: 52, height: 6, rx: 3, fill: P.steelShade }, g);
    });
    svg('rect', { x: num(x0), y: num(o.y - 6), width: num(x1 - x0), height: 12, rx: 6, fill: P.steel }, g);
    svg('rect', { x: num(x0), y: num(o.y + 1), width: num(x1 - x0), height: 5, rx: 2.5, fill: P.steelShade }, g);
    return g;
  };

  // ------------------------------------------------------------------ helpers
  var SIDE_IDS = ['pelvis', 'spine', 'chest', 'neck', 'head', 'shoulderL', 'elbowL', 'wristL', 'hipL', 'kneeL', 'ankleL', 'toeL',
    'shoulderR', 'elbowR', 'wristR', 'hipR', 'kneeR', 'ankleR', 'toeR'];
  var ALL_F = {};
  SIDE_IDS.forEach(function (id) { ALL_F[id] = 1; });
  /** A full pose: joint values, foreshortening (default 1 everywhere, so nothing leaks from the previous pose) and grip. */
  function P_(j, extra) {
    var e = extra || {}, f = {};
    for (var k in ALL_F) if (own(ALL_F, k)) f[k] = 1;
    for (var k2 in e.f || {}) if (own(e.f, k2)) f[k2] = e.f[k2];
    var out = { j: j, f: f, ch: { grip: e.grip === false ? 0 : 1 }, rot: e.rot || 0 };
    ['anchor', 'ik', 'flat', 'x', 'y'].forEach(function (k3) { if (e[k3] !== undefined) out[k3] = e[k3]; });
    return out;
  }
  function U() { return F.sculptData.unit; }
  function sole(t) { return t.sole('R'); }
  function floorAnchor(t, axis, joint, pts) {
    var sf = t.soleFloor();
    return { joint: joint || 'ankleR', point: joint ? [0, 0] : sole(t).point, to: 'keep', axis: axis || 'x', floor: sf.y, points: pts || sf.points };
  }
  function handLayer(t, side) {
    if (t.view === 'side') return side === 'R' ? 'nearHand' : 'farHand';
    var flip = t.view === 'front' || t.view === 'above';
    return 'hand' + (flip ? (side === 'R' ? 'L' : 'R') : side);
  }
  /**
   * A dumbbell in a closed hand. kind 'end': handle into the screen, kept upright (follows the grip
   * point); 'bar': handle along the hand's local x (rides the hand); 'hang': held by its top plate
   * (two-hand overhead hold). where: 'front' (over everything), 'behind' (behind Tibi) or 'hand'
   * (just over that hand, under its forearm).
   */
  function hold(t, side, kind, where) {
    var gp = t.grip(side), s = t.scale * 0.95;
    if (kind === 'end' || kind === 'hang') {          // these stay upright whatever the hand does
      var g = svg('g', { 'class': 'eq-held' });
      if (where === 'behind') t.el.parentNode.insertBefore(g, t.el); else t.el.parentNode.insertBefore(g, t.el.nextSibling);
      var inner = svg('g', { transform: 'scale(' + num(s) + ')' }, g);
      if (kind === 'hang') EQ.dumbbellHang(svg('g', { transform: 'translate(0 26)' }, inner), 1); else EQ.dumbbellEnd(inner, 1);
      t.fig.follow(g, gp.joint, gp.point, function (p) { return { transform: 'translate(' + num(p[0]) + ' ' + num(p[1]) + ')' }; });
      return g;
    }
    var at = t.attach(gp.joint, where === 'hand' ? handLayer(t, side) : 'props');
    var gg = svg('g', { transform: 'translate(' + num(gp.point[0]) + ' ' + num(gp.point[1]) + ')' }, at);
    EQ.dumbbellBar(gg, 0.95);
    return gg;
  }

  // ------------------------------------------------------------------ the library
  var EX = F.exercises = {};
  function rep(steps) { return steps; }

  // 1 push-up (side): feet planted on the toes, hands planted, the body pivots about the toes
  EX['push-up'] = {
    view: 'side', phases: ['pushup-top', 'pushup-bottom'], acts: 'pushup', start: 'pushup',
    setup: function (t, st) {
      t.set('pushup');
      var top = RIG.normalise(t.fig, t.fig.state, t.fig.state);
      var arms = [{ chain: ['shoulderR', 'elbowR', 'wristR'], to: 'keep', bend: 1, flat: true, flatAngle: -90 },
        { chain: ['shoulderL', 'elbowL', 'wristL'], to: 'keep', bend: 1, flat: true, flatAngle: -90 }];
      var toe = { joint: 'toeR', point: [0, 0], to: 'keep' };
      var j = {}; for (var k in top.j) if (own(top.j, k)) j[k] = top.j[k];
      this.poses = {
        'pushup-top': P_(j, { anchor: toe, ik: arms, grip: false }),
        'pushup-bottom': P_(Object.assign({}, j, { pelvis: j.pelvis + 11, head: j.head - 4 }), { anchor: toe, ik: arms, grip: false })
      };
    },
    rep: rep([{ pose: 'pushup-bottom', dur: 1.2, ease: 'sine.inOut' }, { pose: 'pushup-top', dur: 0.9, ease: 'power1.inOut' }])
  };

  // 2 dumbbell bench press (side, lying on the back, head to the left): feet flat on the floor
  var BENCH_LEGS = both({ hipR: 4, kneeR: 96, ankleR: 0, toeR: 0 });
  function benchPose(t, arms) {
    var j = Object.assign({ pelvis: 0, spine: 0, chest: 0, neck: 0, head: 0 }, BENCH_LEGS, both(arms));
    return P_(j, { rot: -90, flat: ['ankleR', 'ankleL'], anchor: floorAnchor(t, 'y', 'pelvis'), f: { shoulderR: arms.fs || 1, shoulderL: arms.fs || 1 } });
  }
  function benchUnder(t, st, incline) {
    var s = t.scale, Uu = U();
    var a = t.point('chest', [-50 * Uu, -100 * Uu]), b = t.point('pelvis', [-48 * Uu, 30 * Uu]), hd = t.point('head', [-40 * Uu, -50 * Uu]);
    var top = Math.max(a[1], b[1]) + 2;
    var x0 = Math.min(a[0], b[0], hd[0]) - 14 * s, x1 = Math.max(a[0], b[0]) + 20 * s;
    return EQ.benchSide(st.back, { x0: x0, x1: x1, top: top, floor: t.floor, thick: 13 * s, incline: incline });
  }
  EX['dumbbell-bench-press'] = {
    view: 'side', phases: ['bench-top', 'bench-bottom'], acts: { pec: 3, triceps: 2, delt: 2, serratus: 1, abs: 1 },
    setup: function (t, st) {
      this.poses = {
        'bench-top': benchPose(t, { shoulderR: 90, elbowR: 0, wristR: 0 }),
        'bench-bottom': benchPose(t, { shoulderR: -14, elbowR: 102, wristR: 2, fs: 0.75 })
      };
      t.set(this.poses['bench-top']);
      benchUnder(t, st);
      hold(t, 'L', 'end', 'behind'); hold(t, 'R', 'end');
    },
    start: 'bench-top',
    rep: rep([{ pose: 'bench-bottom', dur: 1.5, ease: 'sine.inOut' }, { pose: 'bench-top', dur: 1.0, ease: 'power1.inOut' }])
  };

  // 3 dumbbell fly ('above': lying on the back seen from above, head to the right)
  EX['dumbbell-fly'] = {
    view: 'above', phases: ['fly-high', 'fly-low'], acts: 'above-fly-low',
    setup: function (t, st) {
      t.set('fly-high');
      var Uu = U(), a = t.point('head', [0, -40 * Uu]), b = t.point('pelvis', [0, 60 * Uu]);
      EQ.benchTop(st.back, { x0: Math.min(a[0], b[0]) - 20 * t.scale, x1: Math.max(a[0], b[0]) + 10 * t.scale, y: (a[1] + b[1]) / 2, w: 70 * t.scale });
      hold(t, 'L', 'bar', 'hand'); hold(t, 'R', 'bar', 'hand');
    },
    start: 'fly-high',
    rep: rep([{ pose: 'fly-low', dur: 1.6, ease: 'sine.inOut' }, { pose: 'fly-high', dur: 1.2, ease: 'power1.inOut' }])
  };

  // 4 pull-up (back view, hanging from the bar): hands stay on the bar, the body rises
  EX['pull-up'] = {
    view: 'back', phases: ['pullup-hang', 'pullup-top'], acts: { lat: 3, teres: 2, midtrap: 2, lowtrap: 2, rhomb: 2, infra: 1, delt: 1, triceps: 0, extensor: 1 },
    setup: function (t, st) {
      var legs = both({ hipR: 2, kneeR: 6, ankleR: 0 });
      var hang = Object.assign({ pelvis: 0, spine: 0, chest: 0, neck: 0, head: 0 }, legs, both({ shoulderR: 166, elbowR: 2, wristR: 0 }));
      var fl = { ankleR: 0.75, ankleL: 0.75 };
      t.set(P_(hang, { f: fl }));
      var s = t.scale, h0 = t.point('pelvis'), rise = 118 * s;
      var arms = [{ chain: ['shoulderR', 'elbowR', 'wristR'], to: 'keep', bend: 1 }, { chain: ['shoulderL', 'elbowL', 'wristL'], to: 'keep', bend: 1 }];
      this.poses = {
        'pullup-hang': P_(hang, { f: fl, anchor: { joint: 'pelvis', point: [0, 0], to: [h0[0], h0[1]] }, ik: arms }),
        'pullup-top': P_(Object.assign({}, hang, both({ hipR: 4, kneeR: 14 }), { head: 0 }), { f: fl, anchor: { joint: 'pelvis', point: [0, 0], to: [h0[0], h0[1] - rise] }, ik: arms })
      };
      var gr = t.grip('R'), gl = t.grip('L'), wr = t.point(gr.joint, gr.point), wl = t.point(gl.joint, gl.point);
      EQ.bar(st.back, { x0: Math.min(wr[0], wl[0]) - 90 * s, x1: Math.max(wr[0], wl[0]) + 90 * s, y: (wr[1] + wl[1]) / 2, r: 6 * s });
    },
    start: 'pullup-hang',
    rep: rep([{ pose: 'pullup-top', dur: 1.1, ease: 'power1.inOut' }, { pose: 'pullup-hang', dur: 1.5, ease: 'sine.inOut' }])
  };

  // 5 one-arm dumbbell row (side): far knee and far hand on the bench, near foot on the floor
  EX['one-arm-row'] = {
    view: 'side', phases: ['row-low', 'row-high'], acts: { 'lat@near': 3, 'trap': 2, 'delt@near': 2, 'biceps@near': 2, 'brach@near': 2, 'flexor@near': 1, erector: 1, oblique: 1 },
    setup: function (t, st) {
      var base = { pelvis: 72, spine: 4, chest: 0, neck: -20, head: -14, hipL: 72, kneeL: 94, ankleL: -40, toeL: 0, hipR: 80, kneeR: 18, ankleR: 0, toeR: 0,
        shoulderL: 74, elbowL: 2, wristL: -14 };
      var low = Object.assign({}, base, { shoulderR: 76, elbowR: 2, wristR: 0 });
      var high = Object.assign({}, base, { shoulderR: -8, elbowR: 96, wristR: 0 });
      var anc = floorAnchor(t, 'x');
      anc.points = [{ joint: 'ankleR', point: t.soleFloor().points[0].point }, { joint: 'toeR', point: t.soleFloor().points[1].point }];
      this.poses = { 'row-low': P_(low, { anchor: anc, flat: ['ankleR'] }), 'row-high': P_(high, { anchor: anc, flat: ['ankleR'] }) };
      t.set(this.poses['row-low']);
      var Uu = U(), knee = t.point('kneeL', [0, 20 * Uu]), hand = t.point('wristL', [0, 60 * Uu]);
      var top = Math.max(knee[1], hand[1]);
      EQ.benchSide(st.back, { x0: Math.min(knee[0], hand[0]) - 60 * t.scale, x1: Math.max(knee[0], hand[0]) + 40 * t.scale, top: top, floor: t.floor, thick: 13 * t.scale });
      hold(t, 'R', 'end');
    },
    start: 'row-low',
    rep: rep([{ pose: 'row-high', dur: 1.0, ease: 'power1.inOut' }, { pose: 'row-low', dur: 1.5, ease: 'sine.inOut' }])
  };

  // 6 chest-supported rear-delt fly (prone on a flat bench, seen from above)
  EX['rear-delt-fly'] = {
    view: 'top', phases: ['fly-low', 'fly-high'], acts: 'top-fly-high',
    setup: function (t, st) {
      t.set('fly-low');
      var Uu = U(), a = t.point('chest', [0, -40 * Uu]), b = t.point('pelvis', [0, 80 * Uu]);
      EQ.benchTop(st.back, { x0: Math.min(a[0], b[0]) - 10 * t.scale, x1: Math.max(a[0], b[0]) + 10 * t.scale, y: (a[1] + b[1]) / 2, w: 70 * t.scale });
      hold(t, 'L', 'bar', 'hand'); hold(t, 'R', 'bar', 'hand');
    },
    start: 'fly-low',
    rep: rep([{ pose: 'fly-high', dur: 1.1, ease: 'power1.inOut' }, { pose: 'fly-low', dur: 1.5, ease: 'sine.inOut' }])
  };

  // 7 seated dumbbell overhead press (front view, sitting on a bench: thighs point at the camera)
  EX['overhead-press'] = {
    view: 'front', phases: ['press-low', 'press-high'], acts: { delt: 3, triceps: 2, trap: 2, serratus: 1, abs: 1 },
    setup: function (t, st) {
      var legs = both({ hipR: 10, kneeR: 10, ankleR: 0 });
      var fl = { hipR: 0.24, hipL: 0.24 };
      var low = Object.assign({ pelvis: 0, spine: 0, chest: 0, neck: 0, head: 0 }, legs, both({ shoulderR: 86, elbowR: 92, wristR: 2 }));
      var high = Object.assign({}, low, both({ shoulderR: 164, elbowR: 12, wristR: 4 }));
      var anc = floorAnchor(t, 'y', 'pelvis');
      this.poses = { 'press-low': P_(low, { f: fl, anchor: anc }), 'press-high': P_(high, { f: fl, anchor: anc }) };
      t.set(this.poses['press-low']);
      var Uu = U(), p = t.point('pelvis', [0, 58 * Uu]);
      EQ.seatFront(st.back, { x: p[0], top: p[1], floor: t.floor, w: 150 * Uu * t.scale * 1.6 });
      hold(t, 'R', 'bar', 'front'); hold(t, 'L', 'bar', 'front');
    },
    start: 'press-low',
    rep: rep([{ pose: 'press-high', dur: 1.1, ease: 'power1.inOut' }, { pose: 'press-low', dur: 1.4, ease: 'sine.inOut' }])
  };

  // 8 dumbbell lateral raise (front view, standing)
  EX['lateral-raise'] = {
    view: 'front', phases: ['raise-low', 'raise-high'], acts: 'lateral',
    setup: function (t, st) {
      var legs = both({ hipR: 3, kneeR: 3, ankleR: 0 });
      var low = Object.assign({ pelvis: 0, spine: 0, chest: 0, neck: 0, head: 0 }, legs, both({ shoulderR: 14, elbowR: 12, wristR: 0 }));
      var high = Object.assign({}, low, both({ shoulderR: 86, elbowR: 14, wristR: 2 }));
      var anc = floorAnchor(t, 'y', 'pelvis');
      this.poses = { 'raise-low': P_(low, { anchor: anc }), 'raise-high': P_(high, { anchor: anc }) };
      t.set(this.poses['raise-low']);
      hold(t, 'R', 'end'); hold(t, 'L', 'end');
    },
    start: 'raise-low',
    rep: rep([{ pose: 'raise-high', dur: 1.1, ease: 'power1.inOut' }, { pose: 'raise-low', dur: 1.5, ease: 'sine.inOut' }])
  };

  // 9 prone Y-raise (prone on a flat bench, seen from above; bodyweight, thumbs up)
  EX['prone-y-raise'] = {
    view: 'top', phases: ['fly-low', 'y-high'], acts: 'top-y-high',
    setup: function (t, st) {
      var ps = {};
      ['fly-low', 'y-high'].forEach(function (n) { var p = JSON.parse(JSON.stringify(RIG.lookup(t.fig, n))); p.ch = { grip: 0 }; ps[n] = p; });
      this.poses = ps;
      t.set(ps['fly-low']);
      var Uu = U(), a = t.point('chest', [0, -40 * Uu]), b = t.point('pelvis', [0, 80 * Uu]);
      EQ.benchTop(st.back, { x0: Math.min(a[0], b[0]) - 10 * t.scale, x1: Math.max(a[0], b[0]) + 10 * t.scale, y: (a[1] + b[1]) / 2, w: 70 * t.scale });
    },
    start: 'fly-low',
    rep: rep([{ pose: 'y-high', dur: 1.2, ease: 'power1.inOut' }, { pose: 'fly-low', dur: 1.4, ease: 'sine.inOut' }])
  };

  // 10 incline dumbbell curl (side, seated back on an incline bench; arms hang behind the torso line)
  EX['incline-curl'] = {
    view: 'side', phases: ['curl-low', 'curl-high'], acts: { 'biceps@near': 3, 'brach@near': 2, 'flexor@near': 1, 'biceps@far': 3, 'brach@far': 2, delt: 1, abs: 1 },
    setup: function (t, st) {
      var body = { pelvis: -34, spine: 0, chest: 0, neck: 8, head: 6 };
      var legs = both({ hipR: 48, kneeR: 82, ankleR: 0, toeR: 0 });
      var low = Object.assign({}, body, legs, both({ shoulderR: -32, elbowR: 4, wristR: 0 }));
      var high = Object.assign({}, low, both({ shoulderR: -26, elbowR: 128, wristR: 8 }));
      var anc = floorAnchor(t, 'y', 'pelvis');
      this.poses = { 'curl-low': P_(low, { anchor: anc, flat: ['ankleR', 'ankleL'] }), 'curl-high': P_(high, { anchor: anc, flat: ['ankleR', 'ankleL'] }) };
      t.set(this.poses['curl-low']);
      var Uu = U(), seat = t.point('pelvis', [-6 * Uu, 66 * Uu]), back = t.point('chest', [-58 * Uu, -120 * Uu]);
      EQ.benchSide(st.back, { x0: seat[0] - 40 * t.scale, x1: seat[0] + 60 * t.scale, top: seat[1], floor: t.floor, thick: 13 * t.scale, incline: { x: back[0], y: back[1] } });
      hold(t, 'L', 'end', 'behind'); hold(t, 'R', 'end');
    },
    start: 'curl-low',
    rep: rep([{ pose: 'curl-high', dur: 1.0, ease: 'power1.inOut' }, { pose: 'curl-low', dur: 1.6, ease: 'sine.inOut' }])
  };

  // standing dumbbell curl (side): the easier swap for the incline curl; elbows stay by the sides
  EX['dumbbell-curl'] = {
    view: 'side', phases: ['curl-bottom', 'curl-top'], acts: { 'biceps@near': 3, 'brach@near': 2, 'flexor@near': 1, 'biceps@far': 3, 'brach@far': 2, delt: 1, abs: 1 },
    setup: function (t, st) {
      var legs = both({ hipR: 1, kneeR: 3, ankleR: 0, toeR: 0 });
      var bottom = Object.assign({ pelvis: 0, spine: 0, chest: 0, neck: 0, head: 0 }, legs, both({ shoulderR: 4, elbowR: 6, wristR: 0 }));
      var top = Object.assign({}, bottom, both({ shoulderR: 10, elbowR: 136, wristR: 8 }));
      var anc = floorAnchor(t, 'x');
      this.poses = { 'curl-bottom': P_(bottom, { anchor: anc, flat: ['ankleR', 'ankleL'] }), 'curl-top': P_(top, { anchor: anc, flat: ['ankleR', 'ankleL'] }) };
      t.set(this.poses['curl-bottom']);
      hold(t, 'L', 'end', 'behind'); hold(t, 'R', 'end');
    },
    start: 'curl-bottom',
    rep: rep([{ pose: 'curl-top', dur: 1.0, ease: 'power1.inOut' }, { pose: 'curl-bottom', dur: 1.5, ease: 'sine.inOut' }])
  };

  // 11 overhead dumbbell triceps extension (side, standing, both hands under the top plate)
  EX['overhead-triceps-extension'] = {
    view: 'side', phases: ['ext-high', 'ext-low'], acts: { triceps: 3, delt: 1, trap: 1, abs: 1, oblique: 1 },
    setup: function (t, st) {
      var legs = both({ hipR: 2, kneeR: 4, ankleR: 0, toeR: 0 });
      var high = Object.assign({ pelvis: 0, spine: -2, chest: 0, neck: 2, head: 2 }, legs, both({ shoulderR: 168, elbowR: 2, wristR: 0 }));
      var low = Object.assign({}, high, both({ shoulderR: 162, elbowR: 128, wristR: -4 }));
      var anc = floorAnchor(t, 'x');
      this.poses = { 'ext-high': P_(high, { anchor: anc, flat: ['ankleR', 'ankleL'] }), 'ext-low': P_(low, { anchor: anc, flat: ['ankleR', 'ankleL'] }) };
      t.set(this.poses['ext-high']);
      hold(t, 'R', 'hang', 'behind');
    },
    start: 'ext-high',
    rep: rep([{ pose: 'ext-low', dur: 1.6, ease: 'sine.inOut' }, { pose: 'ext-high', dur: 1.0, ease: 'power1.inOut' }])
  };

  // 12 parallel-bar dip (side): hands on the bars, the body lowers and leans slightly forward
  EX['dip'] = {
    view: 'side', phases: ['dip-top', 'dip-bottom'], acts: { pec: 3, triceps: 3, delt: 2, serratus: 1, abs: 1 },
    setup: function (t, st) {
      var top = { pelvis: 10, spine: 4, chest: 0, neck: -6, head: -4, hipR: 22, hipL: 22, kneeR: 82, kneeL: 76, ankleR: -30, ankleL: -30, toeR: 0, toeL: 0,
        shoulderR: -14, shoulderL: -14, elbowR: 2, elbowL: 2, wristR: -10, wristL: -10 };
      t.set(P_(top));
      var s = t.scale, h1 = t.point('pelvis'), h0 = [h1[0], h1[1] - 78 * s], drop = 80 * s;   // up on the bars, feet clear of the floor
      var arms = [{ chain: ['shoulderR', 'elbowR', 'wristR'], to: 'keep', bend: 1 }, { chain: ['shoulderL', 'elbowL', 'wristL'], to: 'keep', bend: 1 }];
      this.poses = {
        'dip-top': P_(top, { anchor: { joint: 'pelvis', point: [0, 0], to: [h0[0], h0[1]] }, ik: arms }),
        'dip-bottom': P_(Object.assign({}, top, { pelvis: 22, spine: 6, neck: -12 }), { anchor: { joint: 'pelvis', point: [0, 0], to: [h0[0] + 6 * s, h0[1] + drop] }, ik: arms })
      };
      t.set(this.poses['dip-top']);
      var gp = t.grip('R'), w = t.point(gp.joint, gp.point);
      EQ.dipSide(st.back, { x: w[0], y: w[1], floor: t.floor, len: 230 * t.scale });
    },
    start: 'dip-top',
    rep: rep([{ pose: 'dip-bottom', dur: 1.4, ease: 'sine.inOut' }, { pose: 'dip-top', dur: 1.0, ease: 'power1.inOut' }])
  };

  // bodyweight extras from the generator's poses (side view)
  EX['bodyweight-squat'] = { view: 'side', phases: ['stand', 'squat'], acts: 'squat', start: 'stand', poseGrip: 0,
    rep: rep([{ pose: 'squat', dur: 1.3, ease: 'sine.inOut' }, { pose: 'stand', dur: 1.0, ease: 'power1.inOut' }]) };
  EX['calf-raise'] = { view: 'side', phases: ['stand', 'calf'], acts: 'calf', start: 'stand', poseGrip: 0,
    rep: rep([{ pose: 'calf', dur: 0.9, ease: 'power2.out' }, { pose: 'stand', dur: 1.2, ease: 'sine.inOut' }]) };

  // ------------------------------------------------------------------ gait (side view)
  // Joint keys of one cycle: 8 evenly spaced keys starting at right heel strike; the left leg is half a
  // cycle behind and each arm swings opposite its leg. Typical sagittal ranges (Novacheck 1998,
  // Gait & Posture 7:77-95) shaped by eye, not measured: label any on-screen numbers as illustrative.
  // The toes bend at the ball as the ankle plantarflexes into push-off.
  var GAIT = {
    walk: { period: 1.08, trunk: 2, elbow: 14, arm: 0.55, hip: [24, 14, 2, -10, -6, 12, 24, 26], knee: [4, 16, 6, 10, 38, 60, 30, 6], ankle: [2, 6, 10, -2, -16, 4, 4, 2] },
    jog: { period: 0.73, trunk: 7, elbow: 84, arm: 0.75, hip: [28, 14, -2, -14, -6, 20, 38, 34], knee: [16, 38, 26, 16, 72, 98, 62, 26], ankle: [0, 18, 12, -24, -10, 6, 6, 2] },
    sprint: { period: 0.6, trunk: 12, elbow: 92, arm: 1.0, hip: [44, 24, 0, -18, 10, 62, 76, 62], knee: [22, 40, 26, 22, 104, 128, 82, 34], ankle: [4, 18, 6, -30, -16, 10, 10, 6] }
  };
  function gaitKeys(kind) {
    var g = GAIT[kind];
    var keys = [];
    for (var i = 0; i < 8; i++) {
      var o = (i + 4) % 8;
      var j = {
        pelvis: 0, hipR: g.hip[i], kneeR: g.knee[i], ankleR: g.ankle[i], toeR: Math.max(0, -g.ankle[i]) * 0.9,
        hipL: g.hip[o], kneeL: g.knee[o], ankleL: g.ankle[o], toeL: Math.max(0, -g.ankle[o]) * 0.9,
        shoulderR: -g.arm * (g.hip[o] - 8) * 0.9, shoulderL: -g.arm * (g.hip[i] - 8) * 0.9,
        elbowR: g.elbow + (kind === 'walk' ? 0 : 6 * Math.sin(i / 8 * 2 * Math.PI)), elbowL: g.elbow - (kind === 'walk' ? 0 : 6 * Math.sin(i / 8 * 2 * Math.PI)),
        wristR: 0, wristL: 0, spine: g.trunk, chest: 0, neck: -g.trunk * 0.6, head: -g.trunk * 0.2
      };
      keys.push(P_(j, { grip: false }));
    }
    return keys;
  }
  F.gait = { params: GAIT, keys: gaitKeys };
  ['walk', 'jog', 'sprint'].forEach(function (k) { EX[k] = { view: 'side', gait: k, phases: ['contact', 'midstance', 'toe-off', 'swing'] }; });

  /**
   * Place an exercise on a Tibi and return a handle.
   *   var ex = F.exercise(tibi, 'dumbbell-bench-press', stage);   stage = {back: <g>, front: <g>} (optional)
   *   t = ex.reps(tl, at, 3, {tempo: 1, pause: 0.2});          plays three reps, returns the end time
   *   ex.phase(tl, 'bench-bottom', at, dur)                     move to one phase (to hold on a frame)
   *   ex.acts                                                   the activation set for t.activate()
   * Gait kinds ('walk', 'jog', 'sprint') return {run(tl, at, seconds), speed, period}.
   */
  F.exercise = function (tibi, id, stage) {
    var rec0 = EX[id];
    if (!rec0) throw new Error('fitness kit: unknown exercise "' + id + '" (have ' + Object.keys(EX).join(', ') + ')');
    if (tibi.view !== rec0.view) throw new Error('fitness kit: ' + id + ' needs a ' + rec0.view + '-view Tibi, got ' + tibi.view);
    var rec = Object.create(rec0);
    var st = stage || {};
    if (!st.back) { st.back = svg('g', { 'class': 'ex-back' }); tibi.el.parentNode.insertBefore(st.back, tibi.shadow || tibi.el); }
    if (!st.front) { st.front = svg('g', { 'class': 'ex-front' }); tibi.el.parentNode.insertBefore(st.front, tibi.el.nextSibling); }
    var h = { id: id, record: rec, stage: st, acts: rec.acts, meta: F.library && F.library.exercises ? F.library.exercises[id] : null };
    if (rec.gait) {
      var keys = gaitKeys(rec.gait), per = GAIT[rec.gait].period;
      tibi.set(keys[0]);
      var floor = tibi.soleFloor();
      var k0 = RIG.normalise(tibi.fig, keys[0], tibi.fig.state), k3 = RIG.normalise(tibi.fig, keys[3], tibi.fig.state);
      var p0 = RIG.point(tibi.fig, 'ankleR', floor.points[0].point, k0), p3 = RIG.point(tibi.fig, 'ankleR', floor.points[0].point, k3);
      h.speed = Math.abs(p0[0] - p3[0]) / (per * 3 / 8);
      h.period = per;
      h.run = function (tl, at, seconds) { return tibi.cycle(tl, keys, at, per, Math.max(1, Math.round(seconds / per)), { floor: floor, substeps: 2 }); };
      return h;
    }
    if (rec.setup) rec.setup.call(rec, tibi, st);
    var lookup = function (name) {
      if (rec.poses && rec.poses[name]) return rec.poses[name];
      var p = JSON.parse(JSON.stringify(RIG.lookup(tibi.fig, name)));
      if (rec.poseGrip !== undefined) p.ch = { grip: rec.poseGrip };
      return p;
    };
    tibi.set(lookup(rec.start || rec.phases[0]));
    h.pose = lookup;
    h.reps = function (tl, at, n, opts) {
      var o = opts || {};
      var tempo = o.tempo || 1;
      var t = at;
      for (var i = 0; i < (n || 1); i++) {
        rec.rep.forEach(function (stp, si) {
          t = tibi.to(tl, lookup(stp.pose), t, stp.dur * tempo, { ease: stp.ease, samples: Math.max(5, Math.ceil(stp.dur * tempo * 6)) });
          if (o.pause && si === 0) t += o.pause;          // a short squeeze at the working end of the rep
        });
      }
      return t;
    };
    h.repDuration = function (opts) { var o = opts || {}, d = 0; rec.rep.forEach(function (s) { d += s.dur * (o.tempo || 1); }); return d + (o.pause || 0); };
    h.phase = function (tl, pose, at, dur, ease) { return tibi.to(tl, lookup(pose), at, dur === undefined ? 0.8 : dur, { ease: ease || 'sine.inOut' }); };
    return h;
  };
  F.exercise.ids = function () { return Object.keys(EX); };
  F.poses = {};          // named poses come from the generator (sculpt-data.js); exercise phases live on their handles
})(typeof window !== 'undefined' ? window : this);
