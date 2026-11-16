/*
 * 2D vs 3D comparison (regression fixture, 1080x1080): the SAME exercise variant on the old 2D Cobalt Sculpt rig (left) and the 3D rig (right),
 * driven by ONE phase clock, at the SAME scale. Configured per exercise by window.COMPARE (see compare-*.html).
 *
 * What the 2026-11-13 review found wrong with the first comparison, and how this fixes it:
 *   - different exercise variations (incline curl vs standing curl)      -> both sides name the same movement (cfg.id2d / cfg.id3d)
 *   - different scale and composition                                    -> both figures are fitted to the SAME pixel height (or width), centred in equal panels
 *   - movement phases not synchronised                                   -> the 2D tweens are laid on T3.phaseTimes(): the 3D rig's own phase map
 *   - stale first frame                                                  -> both rigs are set to the start pose before frame 0
 * Everything the 3D side draws is a pure function of time; the 2D side is GSAP tweens on the same timeline.
 */
Studio.build(function (tl, f, S) {
  var CFG = window.COMPARE, K = S.kit.fitness, T3 = K.t3d, FX = T3.film, P = K.palette;
  var W = 1080, PW = 540, PY = 236, PH = 764, PER = 2.9, REPS = 3, LEAD = 0.5, D = LEAD + REPS * PER + 0.9;
  var root = document.getElementById('root'), svgRoot = document.getElementById('stage');
  var def = T3.exercises[CFG.id3d], o = { at: LEAD, period: PER, reps: REPS };

  // ---------------------------------------------------------------- 3D side (right panel)
  var stage = T3.stage(document.getElementById('gl'), { width: PW, height: PH });
  var m = T3.motion();
  var sc = T3.scene(stage, CFG.id3d, { gender: CFG.g3, figId: 'a', motion: m, at: LEAD, reps: REPS, period: PER });
  var fig = sc.fig;
  var V3 = THREE.Vector3;
  // fit: scale so the figure spans `target` px, measured the same way on both sides
  var cam = stage.cam; cam.az = CFG.az; cam.el = CFG.el; cam.fov = 26; cam.tz = 0; cam.tx = CFG.tx3 || 0; cam.ty = CFG.ty3; cam.dist = 3600;
  fig.apply(m.at(0));
  function ext3() {
    stage.place();
    var top = fig.world('head').clone(), bot = top.clone(); top.y += 175; bot.y = 0;
    var pts = [top, bot, fig.world('hips')];
    if (CFG.fit === 'w') {                                  // a lying lift: width from the head end of the bench to the feet
      pts = [fig.world('head'), fig.world('anL'), fig.world('anR'), fig.world('knL')];
      fig.props.forEach(function (pr) { var b = new THREE.Box3().setFromObject(pr); pts.push(b.min.clone(), b.max.clone()); });
      var toe = fig.point('anL', 0, -26, 96); pts.push(toe, fig.world('shL').clone().add(new V3(0, 260, 0)));        // and the dumbbell at lockout
    }
    var pp = pts.map(function (p) { return stage.project(p); }), xs = pp.map(function (p) { return p.x; }), ys = pp.map(function (p) { return p.y; });
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
    return { w: x1 - x0, h: y1 - y0, cx: (x0 + x1) / 2, cy: (y0 + y1) / 2 };
  }
  // fit the size, then centre the measured points in the panel (camera right vector from the placed camera)
  for (var i = 0; i < 5; i++) {
    var e = ext3(), cur = CFG.fit === 'w' ? e.w : e.h;
    cam.dist *= cur / CFG.target;
    stage.place();
    var e2 = ext3(), ppu = PH / (0.4617 * cam.dist), me = stage.camera.matrixWorld.elements, right = new V3(me[0], me[1], me[2]);
    var dxp = e2.cx - PW / 2, dyp = e2.cy - PH / 2;
    cam.tx += right.x * dxp / ppu; cam.tz += right.z * dxp / ppu; cam.ty -= dyp / ppu;
  }
  stage.place();

  // ---------------------------------------------------------------- 2D side (left panel)
  var outer = S.svg('g', {}, svgRoot), grp = S.svg('g', {}, outer);
  var tib = K.sculpt(grp, { gender: CFG.g2, view: CFG.view2d, x: 270, y: CFG.y2, floor: CFG.floor2, scale: 1 });
  var ex = K.exercise(tib, CFG.id2d);
  tib.set(ex.pose(CFG.start2d));
  // measure the figure at its start pose, fit to the same pixel size, centre in the panel
  var bb = grp.getBBox(), s2 = CFG.target / (CFG.fit === 'w' ? bb.width : bb.height);
  var cx = bb.x + bb.width / 2, cy = bb.y + bb.height / 2;
  var px = 270, py = PY + PH / 2 + (CFG.dy2 || 0);
  var flip = CFG.flip2d ? -1 : 1;
  outer.setAttribute('transform', 'translate(' + px + ' ' + py + ') scale(' + (s2 * flip) + ' ' + s2 + ') translate(' + (-cx) + ' ' + (-cy) + ')');
  // lay the 2D moves on the 3D rig's own phase times (up = toward the working end, down = back)
  for (var r = 0; r < REPS; r++) {
    T3.phaseTimes(def, o, r).forEach(function (p) {
      if (p.kind === 'up') ex.phase(tl, CFG.hi, p.t0, p.t1 - p.t0, 'power1.inOut');
      else if (p.kind === 'down') ex.phase(tl, CFG.lo, p.t0, p.t1 - p.t0, 'sine.inOut');
    });
  }
  tib.activate(tl, ex.acts, LEAD + 0.15, 0.8);

  // ---------------------------------------------------------------- shared overlay: title, phase HUD, panel labels
  var ov = FX.overlay(root, { width: W, height: W });
  var hud = FX.hud(ov, { x: 70, y: 150, width: 940, def: def, o: o, note: false });
  var ui = S.svg('g', {}, ov);
  function txt(s, a) { var e = S.svg('text', Object.assign({ 'font-family': "'Outfit', sans-serif", fill: '#1B1D29' }, a), ui); e.textContent = s; return e; }
  txt('SINEW · REGRESSION · 2D vs 3D', { x: 60, y: 52, 'font-family': "'JetBrains Mono', monospace", 'font-weight': 600, 'font-size': 18, fill: P.cobalt, 'letter-spacing': '0.06em' });
  txt(CFG.title + ' · same movement, same clock', { x: 60, y: 92, 'font-weight': 800, 'font-size': 36 });
  S.svg('rect', { x: 0, y: PY, width: PW, height: PH, fill: 'none', stroke: '#1B1D29', 'stroke-width': 2, opacity: 0.25 }, ui);
  S.svg('rect', { x: PW, y: PY, width: PW, height: PH, fill: 'none', stroke: '#1B1D29', 'stroke-width': 2, opacity: 0.25 }, ui);
  function label(x, s, fill) {
    S.svg('rect', { x: x, y: PY + PH + 16, width: 300, height: 38, rx: 19, fill: fill }, ui);
    txt(s, { x: x + 20, y: PY + PH + 42, 'font-weight': 800, 'font-size': 22, fill: '#FFFFFF' });
  }
  label(40, 'OLD · 2D Cobalt Sculpt', '#8A8D9C'); label(PW + 40, 'NEW · 3D anatomy v1', '#2F56E0');
  txt('illustrative authored poses · colour = effort · both rigs: ' + CFG.title.toLowerCase(), { x: 60, y: 1060, 'font-family': "'JetBrains Mono', monospace", 'font-weight': 500, 'font-size': 14, fill: '#6F7385' });

  T3.bind(tl, stage, m, D, function (v, t) { hud.set(t, FX.win(t, -1, D + 1, 0.01, 0.01)); });
});
