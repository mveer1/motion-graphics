/*
 * Motion Lab fitness kit - reusable 3D scenes (src/studio/kits/fitness/scenes3d.js). Needs tibi3d.js, anatomy3d.js, exercises3d.js, film3d.js.
 *
 * A scene is a unit a film composes, not a one-off: it registers its motion tracks on the shared T3.motion, builds the overlays it needs on the
 * film's SVG layer, and exposes update(t) for T3.bind's onFrame. Everything it draws is a pure function of time. New films call these instead of
 * re-writing a demo each time (the lab clips, the lower-body shorts and any future film share one implementation).
 *
 *   T3.scenes.demo(stage, m, ov, cfg)      a full exercise set: figure, ONE continuous camera orbit, rep HUD, cue card, role-coloured muscle pins that
 *                                          ride the skin, a joint-angle arc and the load's path. cfg: see below.
 *   T3.scenes.cutaway(m, cfg)              the tracks of a localized anatomical cutaway: skin out, deeper layer out, closed, plus per-muscle highlights.
 *
 * demo cfg: {id (T3 exercise), gender, figId, start, end (the clip's window), lead, period, reps,
 *            cam: {az:[from,to], el:[from,to], dist:[from,to], tx, ty, fov},
 *            trail: 'handL' (the bone carrying the load), angle: [a, joint, c, label] (names, functions of the figure, or Vector3),
 *            pins: [{key:'biceps@L', text, role: 3|2, dx, dy}], hud: {x, y, width}, cue: {x, y, size}}
 */
(function (global) {
  'use strict';
  var Studio = global.Studio || (global.Studio = {});
  var F = Studio.kit && Studio.kit.fitness, T3 = F && F.t3d, FX = T3 && T3.film;
  if (!FX) throw new Error('kits/fitness/scenes3d.js needs tibi3d.js, exercises3d.js and film3d.js loaded first');
  var S3 = T3.scenes = {};
  var PRIME = '#F2553D', HELP = '#FFB224', INK = '#1B1D29';

  S3.demo = function (stage, m, ov, cfg) {
    var lead = cfg.lead === undefined ? 0.4 : cfg.lead, per = cfg.period || 3.0, reps = cfg.reps || 3;
    var o = { at: cfg.start + lead, period: per, reps: reps };
    var sc = T3.scene(stage, cfg.id, { gender: cfg.gender, figId: cfg.figId, motion: m, at: o.at, reps: reps, period: per });
    var fig = sc.fig, def = sc.def, end2 = o.at + reps * per;
    // ONE continuous orbit per clip: a cut only where the exercise changes
    var ca = cfg.cam, cut = {}, to = {};
    ['az', 'el', 'dist'].forEach(function (k) { cut['cam.' + k] = ca[k][0]; to['cam.' + k] = ca[k][1]; });
    cut['cam.tx'] = ca.tx || 0; cut['cam.ty'] = ca.ty; cut['cam.tz'] = ca.tz || 0; cut['cam.fov'] = ca.fov || 26;
    m.to(cfg.start, 0.0001, cut, 'none');
    m.to(cfg.start, cfg.end - cfg.start, to, 'sine.inOut');
    var load = cfg.trail || 'handL';
    var path3 = null;     // sampled lazily AFTER the film's motion is complete (the caller calls scene.finish())
    var hud = FX.hud(ov, { x: (cfg.hud || {}).x || 56, y: (cfg.hud || {}).y || 240, width: (cfg.hud || {}).width || 608, def: def, o: o, note: false });
    var cue = FX.cue(ov, { x: (cfg.cue || {}).x || 360, y: (cfg.cue || {}).y || 330, size: (cfg.cue || {}).size || 28, fill: INK });
    var trail = FX.trail(ov, { color: '#2F56E0', width: 4, dash: '2 10', dotR: 9 });
    var ang = FX.angle(ov, { color: INK, radius: 58, size: 28 });
    var pins = (cfg.pins || []).map(function (pn) { var p = FX.pin(ov, { text: pn.text, color: pn.role === 3 ? PRIME : HELP, ink: pn.role === 3 ? '#FFFFFF' : INK, size: 22, dx: pn.dx, dy: pn.dy }); return p; });
    var scene = { figure: fig, def: def, o: o, window: [cfg.start, cfg.end], setEnd: end2 };
    scene.finish = function () { path3 = T3.trail(fig, m, function (fg) { return fg.point(load, 0, -24, 4); }, o.at, o.at + per, 0.05); };
    /** update(t, first): call from T3.bind's onFrame. `first` gives the first clip a HUD that is already there on frame 0. */
    scene.update = function (t, first) {
      var inWin = t >= cfg.start && t < cfg.end;
      fig.setVisible(inWin);
      hud.set(t, inWin ? FX.win(t, first ? -1 : cfg.start + 0.05, cfg.end - 0.15, first ? 0.01 : 0.25, 0.25) : 0);
      if (!inWin) { [cue, trail, ang].forEach(function (x) { x.g.setAttribute('opacity', 0); }); pins.forEach(function (p) { p.g.setAttribute('opacity', 0); }); return; }
      var inSet = FX.win(t, o.at - 0.1, end2 + 0.2, 0.3, 0.4), ph = T3.phaseAt(def, o, t);
      cue.set(ph.cue || undefined, ph.cue ? inSet : 0);
      (cfg.pins || []).forEach(function (pn, i) {
        pins[i].set(stage.project(fig.world(pn.key)), FX.win(t, o.at + (i ? 1.2 : 0.2), end2 - 0.2, 0.3, 0.3), pn.dx, pn.dy);
      });
      var a = cfg.angle;
      if (a) ang.set(stage.project(T3.pt(fig, a[1])), stage.project(T3.pt(fig, a[0])), stage.project(T3.pt(fig, a[2])), FX.win(t, o.at + 0.5, end2 - 0.3, 0.3, 0.3) * 0.95,
        T3.jointAngle(fig, a[0], a[1], a[2]), (a[3] || 'Angle') + ' · illustrative');
      if (path3) trail.set(path3.map(function (p) { return stage.project(p); }), stage.project(fig.point(load, 0, -24, 4)), FX.win(t, o.at - 0.1, end2 + 0.1, 0.3, 0.4) * 0.9);
    };
    return scene;
  };

  /**
   * Cutaway tracks on a figure (keys carry the figure id prefix, as every motion key must). cfg:
   *   {fig: 's', window: 'calf@L', open: [at, dur], peel: [at, dur] (optional), close: [at, dur], hi: [{key: 'calf@L', on: [at, dur], off: [at, dur]}]}
   * skin out (1), then the superficial layer out (2), closed (0); hi.<muscle> highlights one muscle inside the body (coral).
   */
  S3.cutaway = function (m, cfg) {
    var p = cfg.fig ? cfg.fig + '.' : '', w = p + 'cut.' + cfg.window, base = {};
    base[w] = 0; (cfg.hi || []).forEach(function (h) { base[p + 'hi.' + h.key] = 0; });
    m.base(base);
    var v = {}; v[w] = 1; m.to(cfg.open[0], cfg.open[1], v, 'sine.inOut');
    if (cfg.peel) { v = {}; v[w] = 2; m.to(cfg.peel[0], cfg.peel[1], v, 'sine.inOut'); }
    v = {}; v[w] = 0; m.to(cfg.close[0], cfg.close[1], v, 'sine.inOut');
    (cfg.hi || []).forEach(function (h) {
      var a = {}, b = {}; a[p + 'hi.' + h.key] = 1; b[p + 'hi.' + h.key] = 0;
      m.to(h.on[0], h.on[1], a, 'sine.inOut'); m.to(h.off[0], h.off[1], b, 'sine.inOut');
    });
    return cfg.close[0] + cfg.close[1];
  };
})(typeof window !== 'undefined' ? window : globalThis);
