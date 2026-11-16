/*
 * Motion Lab fitness kit - Tibi in the Cobalt Sculpt style (src/studio/kits/fitness/sculpt.js)
 *
 * Needs studio-core.js, studio-rig.js and kits/fitness/sculpt-data.js (generated from the Python
 * master source in src/fitness/tibi/ by `python scripts/fitness.py sculpt`). Brand rules:
 * .claude/skills/fitness/references/character-guidelines.md.
 *
 * Tibi comes as a male and a female athlete: flat cobalt planes, no outlines, a light plane and
 * a crescent shade on every muscle (light from the top left), charcoal shorts with a marigold
 * band, white trainers, the marigold spark on the head; she adds a sports top (or push-up top)
 * and a ponytail. The figure is the handover's segment art placed on the studio rig, so it
 * poses, tweens, cycles and solves contacts like the classic Tibi, with the same joint ids and
 * anatomical angle conventions (exercises.js poses work on it).
 *
 * Views 'front', 'side' (faces +x; near limbs R, far limbs L, dimmed) and 'back'. Faces:
 * 'faceless' (default), 'minimal', 'ember'. Muscle activation recolours the existing planes:
 * 3 prime mover (coral), 2 secondary (marigold), 1 stabiliser (pale cobalt).
 *
 * Shading: each crescent is a mask (the shape minus itself nudged toward the light). The nudge is
 * counter-rotated against the segment's world angle through the rig's derive hook, so the light
 * stays top-left while a limb swings; every move is sampled so it follows the arc.
 */
(function (global) {
  'use strict';

  var Studio = global.Studio || (global.Studio = {});
  var RIG = Studio.rig;
  if (!RIG) throw new Error('kits/fitness/sculpt.js needs _studio/studio-rig.js loaded first');
  var KIT = Studio.kit = Studio.kit || {};
  var F = KIT.fitness = KIT.fitness || {};
  var D = F.sculptData;
  if (!D) throw new Error('kits/fitness/sculpt.js needs _studio/kits/fitness/sculpt-data.js loaded first');

  var C = D.colors, U = D.unit;
  var LV = D.levels, GHOST = D.ghost;
  var SKIP_LINES = { clav: 1, notch: 1, lace: 1, toecap: 1, rim: 1, seam: 1, vein: 1 };
  var CLOTH_FILL = { band: C.marigold, thumb: C.body, tie: C.marigold, clasp: C.clasp };
  var FAR_CLOTH = { shortsleg: 1, shorts: 1, sole: 1, thumb: 1 };
  var IDLE = { fill: C.light, shade: C.shade, hi: C.light, halo: C.light, op: 0 };
  // muscles.json ids -> sculpt plane keys (activate() and muscle() accept either)
  var ALIAS = {
    'deltoid': ['delt'], 'pectoralis-major': ['pec'], 'biceps-brachii': ['biceps'], 'triceps-brachii': ['triceps'],
    'forearm-flexors': ['flexor'], 'brachioradialis': ['brach'], 'forearm-extensors': ['extensor'], 'rectus-abdominis': ['abs'],
    'external-oblique': ['oblique'], 'latissimus-dorsi': ['lat'], 'trapezius': ['trap', 'midtrap', 'lowtrap'], 'erector-spinae': ['erector'],
    'gluteus-maximus': ['glute'], 'quadriceps': ['quad', 'vastus', 'vmo'], 'hamstrings': ['hams'], 'adductors': ['adductor'],
    'gastrocnemius': ['gastro'], 'soleus': ['soleus'], 'tibialis-anterior': ['tibant'], 'serratus-anterior': ['serratus'],
    'infraspinatus': ['infra'], 'hip-flexors': ['hipflex'], 'rhomboids': ['rhomb'], 'teres-major': ['teres'],
    'middle-trapezius': ['midtrap'], 'lower-trapezius': ['lowtrap'], 'posterior-deltoid': ['delt']
  };

  var uid = 0;
  function svg(tag, attrs, parent) { return Studio.svg(tag, attrs, parent); }
  function num(v) { return Math.round(v * 100) / 100; }
  function own(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }

  // ------------------------------------------------------------------ shared shape defs (one per document)
  function defsFor(parent) {
    var doc = parent.ownerDocument;
    var host = doc.getElementById('tsc-defs');
    if (host) return host;
    var root = parent.ownerSVGElement || parent;
    host = svg('defs', { id: 'tsc-defs' });
    root.insertBefore(host, root.firstChild);
    return host;
  }
  function need(fig, id) {
    var full = 'tsc-' + id;
    if (!fig.data.doc.getElementById(full)) svg('path', { id: full, d: D.paths[id][0] }, fig.data.shapeDefs);
    return '#' + full;
  }
  function use(fig, id, attrs, parent) {
    var a = { href: need(fig, id) };
    for (var k in attrs) if (own(attrs, k)) a[k] = attrs[k];
    return svg('use', a, parent);
  }

  // ------------------------------------------------------------------ crescent masks
  // mask = shape (white) minus the shape nudged by k toward the light (black); hi = nudged away.
  // The nudge lives in three groups: rotate(-angle) translate(k * light) rotate(angle), and the two
  // rotations are re-derived from the segment's world angle on every move sample.
  function crescent(fig, seg, id, color, amt, hi, extra, parent) {
    var k = Math.min(amt, 0.33 * D.paths[id][1]) / seg.s;
    var sg = hi ? -1 : 1;
    var mid = 'tsc' + fig.data.n + '-k' + (fig.data.masks++);
    var m = svg('mask', { id: mid, maskUnits: 'userSpaceOnUse', x: -420, y: -480, width: 900, height: 1000 }, fig.data.maskDefs);
    use(fig, id, { fill: '#fff' }, m);
    var outer = svg('g', {}, m);
    var shift = svg('g', { transform: 'translate(' + num(fig.data.light[0] * k * sg) + ' ' + num(fig.data.light[1] * k * sg) + ')' }, outer);
    var inner = svg('g', {}, shift);
    use(fig, id, { fill: '#000' }, inner);
    seg.outer.push(outer); seg.inner.push(inner);
    var a = { fill: color, mask: 'url(#' + mid + ')' };
    for (var e in extra || {}) if (own(extra, e)) a[e] = extra[e];
    return use(fig, id, a, parent);
  }

  // ------------------------------------------------------------------ the painter (build2.p_sculpt)
  function segData(fig, key, dside) {
    var rec = D.segments[fig.data.g + fig.data.vk + '_' + key + '_' + dside];
    if (!rec) throw new Error('Tibi sculpt: no art for ' + fig.data.g + fig.data.vk + '_' + key + '_' + dside);
    return rec;
  }
  function lines(fig, S, g, color, w, op) {
    S.lines.forEach(function (l) {
      if (SKIP_LINES[l[0]]) return;
      use(fig, l[1], { fill: 'none', stroke: color, 'stroke-width': w, 'stroke-opacity': op, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, g);
    });
  }
  function farOverlay(fig, seg, S, g, op) {
    if (!seg.far) return;
    use(fig, S.b, { fill: C.navy, 'fill-opacity': op }, g);
    S.cloth.forEach(function (c) { if (FAR_CLOTH[c[0]]) use(fig, c[1], { fill: C.navy, 'fill-opacity': op }, g); });
  }
  function faceEls(fig, g) {
    var f = fig.data.face;
    if (!f || f === 'faceless' || fig.data.view === 'back') return;
    var set = D.faces[fig.data.g + '_' + f];
    var fg = svg('g', { transform: 'translate(0 -92)', 'class': 'tsc-face' }, g);
    (fig.data.view === 'side' ? set.side : set.front).forEach(function (el) { svg(el[0], el[1], fg); });
  }
  function spark(fig, seg, g) {
    var sp = svg('g', { 'class': 'tsc-spark' }, g);
    svg('path', { d: D.flame[0], fill: C.marigold }, sp);
    svg('path', { d: D.flame[1], fill: C.glow }, sp);
    seg.spark = sp;
    fig.data.sparks.push(sp);
  }

  function paint(fig, seg, g) {
    var S = segData(fig, seg.key, seg.dside);
    var key = seg.key.split('_')[0];
    if (key === 'pony') {
      use(fig, S.b, { fill: C.hair }, g);
      S.mus.forEach(function (m) { use(fig, m[1], { fill: C.hairLight }, g); crescent(fig, seg, m[1], C.hairShade, 4.5, false, null, g); });
      crescent(fig, seg, S.b, C.hairShade, 6, false, null, g);
      S.cloth.forEach(function (c) { use(fig, c[1], { fill: C.marigold }, g); });
      return;
    }
    if (key === 'foot' || key === 'toes') {
      use(fig, S.b, { fill: C.shoe }, g);
      crescent(fig, seg, S.b, C.shoeShade, 5, false, null, g);
      S.cloth.forEach(function (c) { use(fig, c[1], { fill: C.shoeDetail }, g); });
      S.lines.forEach(function (l) {
        if (l[0] !== 'vein') use(fig, l[1], { fill: 'none', stroke: C.shoeDetail, 'stroke-width': 1.8, 'stroke-opacity': 1, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, g);
      });
      farOverlay(fig, seg, S, g, 0.25);
      return;
    }
    use(fig, S.b, { fill: C.body }, g);
    S.sh.forEach(function (id) { use(fig, id, { fill: C.shade }, g); });
    var ghosts = [];
    S.mus.forEach(function (m) {
      var nm = m[0], id = m[1];
      if (nm === 'face') {
        if (fig.data.face === 'ember') { use(fig, id, { fill: C.visor }, g); crescent(fig, seg, id, C.visorShade, 5, false, { opacity: 0.6 }, g); }
        else { use(fig, id, { fill: C.face }, g); crescent(fig, seg, id, C.shade, 5, false, { opacity: 0.55 }, g); }
        return;
      }
      if (nm === 'navel') { use(fig, id, { fill: C.shade }, g); return; }
      if (nm === 'hairplane') return;
      if (GHOST.indexOf(nm) >= 0) { ghosts.push(m); return; }
      var mg = svg('g', { 'class': 'tsc-m', 'data-muscle': nm }, g);
      var fill = use(fig, id, { fill: C.light }, mg);
      var shade = crescent(fig, seg, id, C.shade, 5.5, false, null, mg);
      var plane = { name: nm, far: seg.far, seg: seg, id: id, g: mg, fill: fill, shade: shade, halo: null, hi: null, level: 0 };
      buildPlane(fig, plane);
      fig.data.planes.push(plane);
    });
    lines(fig, S, g, C.shade, 1.8, 0.75);
    S.cloth.forEach(function (c) {
      var nm = c[0], id = c[1];
      if (nm === 'bust') { use(fig, id, { fill: C.bust }, g); crescent(fig, seg, id, C.bustShade, 4.2, false, null, g); return; }
      if (nm === 'mound') {
        use(fig, id, { fill: C.seat }, g); crescent(fig, seg, id, C.seatShade, 5, false, null, g);
        crescent(fig, seg, id, C.seatLight, 2.4, true, { opacity: 0.8 }, g); return;
      }
      use(fig, id, { fill: CLOTH_FILL[nm] || C.charcoal }, g);
    });
    S.lines.forEach(function (l) {
      if (l[0] === 'rim') use(fig, l[1], { fill: 'none', stroke: C.clasp, 'stroke-width': 3.6, 'stroke-opacity': 0.85, 'stroke-linecap': 'round' }, g);
      if (l[0] === 'seam') use(fig, l[1], { fill: 'none', stroke: C.seam, 'stroke-width': 2, 'stroke-opacity': 0.9, 'stroke-linecap': 'round' }, g);
    });
    if (S.hem) use(fig, S.hem, { fill: 'none', stroke: C.marigold, 'stroke-width': 3.2, 'stroke-linecap': 'round' }, g);
    // glutes and hip flexors sit under the shorts: drawn over them only when activated (level 2+)
    ghosts.forEach(function (m) {
      var gg = svg('g', { 'class': 'tsc-ghost', 'data-muscle': m[0], opacity: 0 }, g);
      var ghost = { name: m[0], far: seg.far, seg: seg, id: m[1], g: gg, built: null, level: 0 };
      buildGhost(fig, ghost);
      fig.data.ghosts.push(ghost);
    });
    if (key === 'head') faceEls(fig, g);
    farOverlay(fig, seg, S, g, 0.22);
  }

  // activation art (halo, highlight crescent, ghost overlays) is built with the figure, hidden, so
  // every later move's derived shading tweens reach it; activate() only recolours and fades
  function buildPlane(fig, p) {
    if (p.halo) return;
    p.halo = use(fig, p.id, { fill: 'none', stroke: C.light, 'stroke-width': 7, 'stroke-opacity': 0, 'stroke-linejoin': 'round' });
    p.g.insertBefore(p.halo, p.g.firstChild);
    p.hi = crescent(fig, p.seg, p.id, C.light, 2.6, true, { opacity: 0 }, p.g);
  }
  function buildGhost(fig, q) {
    if (q.built) return;
    var c = LV['2'];
    q.built = {
      halo: use(fig, q.id, { fill: 'none', stroke: c.halo, 'stroke-width': 6, 'stroke-opacity': 0.25, 'stroke-linejoin': 'round' }, q.g),
      fill: use(fig, q.id, { fill: c.fill, 'fill-opacity': 0.82 }, q.g),
      shade: crescent(fig, q.seg, q.id, c.shade, 5.5, false, { opacity: 0.85 }, q.g),
      hi: crescent(fig, q.seg, q.id, c.hi, 2.6, true, { opacity: 0.85 }, q.g)
    };
  }

  // ------------------------------------------------------------------ skeleton per view (rig units)
  function joints(view, sk) {
    function o(v, mx) { return [num(v[0] * (mx || 1) * U), num(v[1] * U)]; }
    if (view === 'side') {
      var s = sk.side, out = [
        { id: 'pelvis', parent: null, offset: [0, 0], sign: 1 },
        { id: 'spine', parent: 'pelvis', offset: o(s.spine), sign: 1 },
        { id: 'chest', parent: 'spine', offset: [0, 0], sign: 1 },
        { id: 'neck', parent: 'chest', offset: o(s.neck), sign: 1 },
        { id: 'head', parent: 'neck', offset: o(s.head), sign: 1 }
      ];
      ['L', 'R'].forEach(function (x) {
        out.push({ id: 'shoulder' + x, parent: 'chest', offset: o(s.shoulder), sign: -1 });
        out.push({ id: 'elbow' + x, parent: 'shoulder' + x, offset: o(s.elbow), sign: -1 });
        out.push({ id: 'wrist' + x, parent: 'elbow' + x, offset: o(s.wrist), sign: -1 });
        out.push({ id: 'hip' + x, parent: 'pelvis', offset: o(s.hip), sign: -1 });
        out.push({ id: 'knee' + x, parent: 'hip' + x, offset: o(s.knee), sign: 1 });
        out.push({ id: 'ankle' + x, parent: 'knee' + x, offset: o(s.ankle), sign: -1 });
        out.push({ id: 'toe' + x, parent: 'ankle' + x, offset: o(s.toe), sign: -1 });   // the ball: + bends the toes up
      });
      return out;
    }
    var f = sk.front, res = [
      { id: 'pelvis', parent: null, offset: [0, 0], sign: 1 },
      { id: 'spine', parent: 'pelvis', offset: o(f.spine), sign: 1 },
      { id: 'chest', parent: 'spine', offset: [0, 0], sign: 1 },
      { id: 'neck', parent: 'chest', offset: o(f.neck), sign: 1 },
      { id: 'head', parent: 'neck', offset: o(f.head), sign: 1 }
    ];
    // data side L is the viewer's left: the figure's right in front view, its left in back view
    ['L', 'R'].forEach(function (ds) {
      var x = jointSide(view, ds), mx = ds === 'L' ? 1 : -1, sg = ds === 'L' ? 1 : -1;
      res.push({ id: 'shoulder' + x, parent: 'chest', offset: o(f.shoulder, mx), sign: sg });
      res.push({ id: 'elbow' + x, parent: 'shoulder' + x, offset: o(f.elbow, mx), sign: sg });
      res.push({ id: 'wrist' + x, parent: 'elbow' + x, offset: o(f.wrist, mx), sign: sg });
      res.push({ id: 'hip' + x, parent: 'pelvis', offset: o(f.hip, mx), sign: sg });
      res.push({ id: 'knee' + x, parent: 'hip' + x, offset: o(f.knee, mx), sign: -sg });
      res.push({ id: 'ankle' + x, parent: 'knee' + x, offset: o(f.ankle, mx), sign: sg });
    });
    return res;
  }
  function jointSide(view, ds) { return (view === 'front' || view === 'above') ? (ds === 'L' ? 'R' : 'L') : ds; }

  // draw layers in the generator's paint order (back to front); one segment per layer
  function layers(view, g, top) {
    var L = [], hs = D.skeleton[g].handScale;
    function seg(id, joint, key, dside, extra) {
      var e = { id: id, joint: joint, key: key, dside: dside };
      for (var k in extra || {}) if (own(extra, k)) e[k] = extra[k];
      L.push(e);
    }
    var chest = g === 'm' ? 'chest' : 'chest_' + top;
    if (view === 'side') {
      seg('farHand', 'wristL', 'hand', 'C', { far: true, s: hs, variants: [['hand', 'open'], ['grip', 'grip']] });
      seg('farForearm', 'elbowL', 'forearm', 'C', { far: true });
      seg('farUpperArm', 'shoulderL', 'upperArm', 'C', { far: true });
      seg('farShin', 'kneeL', 'shin', 'C', { far: true, leg: true });
      seg('farThigh', 'hipL', 'thigh', 'C', { far: true, leg: true });
      seg('farFoot', 'ankleL', 'foot', 'C', { far: true });
      seg('farToes', 'toeL', 'toes', 'C', { far: true });
      seg('nearShin', 'kneeR', 'shin', 'C', { leg: true });
      seg('nearThigh', 'hipR', 'thigh', 'C', { leg: true });
      seg('nearFoot', 'ankleR', 'foot', 'C');
      seg('nearToes', 'toeR', 'toes', 'C');
      seg('pelvis', 'pelvis', 'pelvis', 'C');
      seg('neck', 'neck', 'neck', 'C');
      seg('chest', 'chest', chest, 'C');
      if (g === 'f') seg('pony', 'head', 'pony', 'C', { pony: 'pony' });
      seg('head', 'head', 'head', 'C', { head: true });
      seg('nearHand', 'wristR', 'hand', 'C', { s: hs, variants: [['hand', 'open'], ['grip', 'grip']] });
      seg('nearForearm', 'elbowR', 'forearm', 'C');
      seg('nearUpperArm', 'shoulderR', 'upperArm', 'C');
      return L;
    }
    function legs() {
      ['R', 'L'].forEach(function (ds) {
        var x = jointSide(view, ds);
        seg('shin' + ds, 'knee' + x, 'shin', ds, { leg: true });
        seg('thigh' + ds, 'hip' + x, 'thigh', ds, { leg: true });
        seg('foot' + ds, 'ankle' + x, 'foot', ds);
      });
    }
    function arms() {
      ['R', 'L'].forEach(function (ds) {
        var x = jointSide(view, ds);
        seg('hand' + ds, 'wrist' + x, 'hand', ds, { s: hs, arm: x, variants: [['hand', 'open'], ['fist', 'fist']] });
        seg('forearm' + ds, 'elbow' + x, 'forearm', ds);
        seg('upperArm' + ds, 'shoulder' + x, 'upperArm', ds, { arm: x, variants: [['upperArm', 'down'], ['upperArm_nd', 'raised'], ['upperArm_flex', 'flexArm']] });
      });
    }
    // seen from above ('top' prone, 'above' supine) the arms hang below the body, so they are painted first
    var lying = view === 'top' || view === 'above';
    if (lying) arms();
    legs();
    ['R', 'L'].forEach(function (ds) {
      seg('flare' + ds, 'chest', 'flare', ds, { at: 'shoulder', arm: jointSide(view, ds), show: 'raised' });
    });
    if (g === 'f' && view === 'above') seg('pony', 'head', 'pony', 'C', { pony: 'pony', lying: true });   // under the head
    seg('pelvis', 'pelvis', 'pelvis', 'C');
    seg('neck', 'neck', 'neck', 'C');
    seg('chest', 'chest', chest, 'C');
    if (g === 'f' && view === 'front') seg('pony', 'head', 'pony', 'C', { pony: 'pony' });
    seg('head', 'head', 'head', 'C', { head: true });
    if (g === 'f' && (view === 'back' || view === 'top')) seg('pony', 'head', 'pony', 'C', { pony: 'ponyBack', lying: view === 'top' });
    if (!lying) arms();
    ['R', 'L'].forEach(function (ds) {
      seg('cap' + ds, 'chest', 'cap', ds, { at: 'shoulder', arm: jointSide(view, ds), show: 'raised' });
    });
    return L;
  }

  // arm art for the front/back views follows the pose: hanging arms use the plain upper arm and
  // hand; raised arms (abduction 50+) add the deltoid cap and lat wing and use the no-deltoid
  // upper arm, or the flexed upper arm and fist when the elbow is bent past 60 degrees.
  function armState(pose, x) {
    var ab = pose.j['shoulder' + x] || 0, el = pose.j['elbow' + x] || 0;
    if (ab < 50) return 'down';
    return el >= 60 ? 'flex' : 'raised';
  }
  // hands: 'open' unless flexing or gripping; 'fist' (front/back/top) and 'grip' (side) when holding
  // something (pose channel ch.grip = 1) or, for the fist, in a double-biceps flex
  function shows(tag, state, grip) {
    if (tag === 'down') return state === 'down';
    if (tag === 'raised') return state !== 'down';
    if (tag === 'flexArm') return state === 'flex';
    if (tag === 'open') return !grip && state !== 'flex';
    if (tag === 'fist') return grip || state === 'flex';
    if (tag === 'grip') return grip;
    return true;
  }
  function gripOn(pose) { return !!(pose.ch && pose.ch.grip > 0.5); }

  // ------------------------------------------------------------------ figure spec
  function makeSpec(o) {
    var g = o.g, view = o.view;
    var sk = D.skeleton[g];
    var lays = layers(view, g, o.top);
    var byId = {};
    lays.forEach(function (l) { byId[l.id] = l; });
    var specLayers = lays.map(function (l) { return { id: l.id, joints: [l.joint] }; });
    var allJoints = joints(view, sk);
    specLayers.push({ id: 'rig', joints: allJoints.map(function (j) { return j.id; }) });
    specLayers.push({ id: 'props', joints: ['wristR', 'wristL', 'chest', 'ankleR', 'ankleL'] });
    var children = {};
    allJoints.forEach(function (j) { if (j.parent) (children[j.parent] = children[j.parent] || []).push(j); });

    function addSeg(fig, l, key, g2, variant) {
      var seg = { key: key, dside: l.dside, joint: l.joint, far: !!l.far, s: l.s || 1, outer: [], inner: [], variant: variant, layer: l, pony: l.pony };
      paint(fig, seg, g2);
      fig.data.segs.push(seg);
      return seg;
    }

    return {
      view: view,
      joints: allJoints,
      layers: specLayers,
      rest: o.rest,
      poses: o.poses,
      // grip: 0 open hands, 1 closed around a handle; read by derive (no attributes of its own)
      channels: { grip: { rest: 0, make: function () { return []; } } },
      init: function (fig) {
        fig.data = {
          g: g, vk: { front: 'F', side: 'S', back: 'B', top: 'B', above: 'F' }[view], view: view, face: o.face, n: ++uid, masks: 0, arts: [],
          light: [D.light[0] * o.facing, D.light[1]], doc: o.doc, shapeDefs: o.shapeDefs, maskDefs: o.maskDefs,
          segs: [], planes: [], ghosts: [], sparks: [], variants: [], markers: [], props: {}
        };
      },
      draw: function (fig, id, layerId, gEl) {
        if (layerId === 'props') { fig.data.props[id] = gEl; return; }
        if (layerId === 'rig') {
          var m = svg('g', { 'class': 'tsc-marker', opacity: 0 }, gEl);
          (children[id] || []).forEach(function (c) {
            svg('line', { x1: 0, y1: 0, x2: c.offset[0], y2: c.offset[1], stroke: C.navy, 'stroke-width': 1.6 * U * 1.3, 'stroke-dasharray': '4 3', opacity: 0.7 }, m);
          });
          svg('circle', { cx: 0, cy: 0, r: 5.5 * U * 1.3, fill: C.marigold, stroke: C.navy, 'stroke-width': 1.8 * U * 1.3 }, m);
          fig.data.markers.push(m);
          return;
        }
        var l = byId[layerId];
        // art group: Cobalt units, pivot at the joint (local = neutral - pivot); fj = the joint's own
        // foreshortening (back and top views), which also shrinks offsets measured along it
        var artT = function (fj) {
          var t = 'scale(' + U + ')';
          if (l.at) {
            var sh = view === 'side' ? sk.side.shoulder : sk.front.shoulder;
            t = 'translate(' + num(sh[0] * (l.dside === 'L' ? 1 : -1) * U) + ' ' + num(sh[1] * U * fj) + ') ' + t;
          }
          if (l.pony) {
            var po = view === 'side' ? sk.side.pony : sk.front[l.pony];
            return t + ' translate(' + po[0] + ' ' + num(po[1] * fj) + ')';       // the tail's own scale is on its wrapper
          }
          if (l.leg && sk.artLegScale !== 1) t += ' scale(1 ' + sk.artLegScale + ')';
          if (l.s && l.s !== 1) t += ' scale(' + l.s + ')';
          return fj === 1 ? t : t + ' scale(1 ' + num(fj) + ')';
        };
        var art = svg('g', { 'class': 'tsc-seg tsc-' + l.key, transform: artT(1) }, gEl);
        fig.data.arts.push({ el: art, joint: l.joint, make: artT });     // tweened only when a pose changes the joint's f
        if (l.pony) {
          var pw = svg('g', {}, art);
          var ps = addSeg(fig, l, l.key, pw);
          ps.ponyWrap = pw; ps.lying = !!l.lying;
          return;
        }
        if (l.head) {
          var sp = { key: 'head', joint: l.joint, outer: [], inner: [], s: 1, spark: null, sparkOnly: true };
          spark(fig, sp, art);
          fig.data.segs.push(sp);
        }
        if (l.variants) {
          l.variants.forEach(function (v) {
            var vg = svg('g', { 'class': 'tsc-variant' }, art);
            addSeg(fig, l, v[0], vg, v[1]);
            fig.data.variants.push({ el: vg, arm: l.arm, tag: v[1] });
          });
          return;
        }
        var s = addSeg(fig, l, l.key, art);
        if (l.show) { s.variant = l.show; fig.data.variants.push({ el: art, arm: l.arm, tag: l.show }); }
      },
      derive: function (fig, pose) {
        var out = [];
        fig.data.segs.forEach(function (seg) {
          var a = RIG.chainRotation(fig, seg.joint, pose);
          if (seg.pony && seg.lying) {
            // seen from above the tail hangs toward the floor: it follows the head, foreshortened
            out.push({ el: seg.ponyWrap, attr: { transform: 'scale(1 0.4)' } });
          } else if (seg.pony && Math.abs(pose.rot || 0) > 45) {
            // lying in a side view (bench press): the tail rests along the head instead of hanging
            out.push({ el: seg.ponyWrap, attr: { transform: 'rotate(0)' } });
          } else if (seg.pony) {
            // the tail hangs: it keeps 30 % of the head's tilt (build2: rotation th * 0.3)
            out.push({ el: seg.ponyWrap, attr: { transform: 'rotate(' + num(-0.7 * a) + ')' } });
            a = 0.3 * a;
          }
          if (seg.spark) {
            out.push({ el: seg.spark, attr: { transform: 'rotate(' + num(-0.8 * a) + ' 0 -86) translate(0 -92) translate(0 6) scale(1.4) translate(0 -6)' } });
          }
          if (seg.outer.length) {
            out.push({ el: seg.outer, attr: { transform: 'rotate(' + num(-a) + ')' } });
            out.push({ el: seg.inner, attr: { transform: 'rotate(' + num(a) + ')' } });
          }
        });
        var grip = gripOn(pose);
        fig.data.variants.forEach(function (v) {
          out.push({ el: v.el, attr: { opacity: shows(v.tag, view === 'side' ? 'down' : armState(pose, v.arm), grip) ? 1 : 0 } });
        });
        fig.data.arts.forEach(function (a2) {
          out.push({ el: a2.el, attr: { transform: a2.make(pose.f && pose.f[a2.joint] !== undefined ? pose.f[a2.joint] : 1) } });
        });
        return out;
      }
    };
  }

  // named poses from the generator, grounded by contact rather than a fixed body offset, so every
  // move sample keeps the figure on the floor: exercise poses keep the planted foot (x) and rest the
  // lowest contact on the floor; run phases keep the pelvis and lift by the flight height.
  function sculptPoses(g, view, s, floor, jointIds) {
    var src = D.poses[g][view], ct = D.contacts[g], hs = D.skeleton[g].handScale;
    function pt(p, k) { return [num(p[0] * U * (k || 1)), num(p[1] * U * (k || 1))]; }
    var out = {};
    for (var k in src) {
      if (!own(src, k)) continue;
      var rec = src[k];
      // every named pose states every joint's foreshortening and the grip, so nothing leaks from the previous pose
      var fmap = {};
      jointIds.forEach(function (id) { fmap[id] = rec.f && rec.f[id] !== undefined ? rec.f[id] : 1; });
      var pose = { rot: rec.rot || 0, j: rec.j, f: fmap, ch: { grip: rec.grip ? 1 : 0 } };
      if (view === 'top' || view === 'above') { pose.x = 0; pose.y = 0; out[k] = pose; continue; }
      var pts = [], run = /^run-/.test(k);
      ['R', 'L'].forEach(function (x) {
        if (view === 'side') { pts.push({ joint: 'ankle' + x, point: pt(ct.heel) }, { joint: 'toe' + x, point: pt(ct.toe) }); }
        else pts.push({ joint: 'ankle' + x, point: [0, num(ct.frontSole[1] * U * fmap['ankle' + x])] });   // a folded foot's sole moves with it
        if (k === 'pushup' || k === 'plank') ct.hand.forEach(function (h) { pts.push({ joint: 'wrist' + x, point: pt(h, hs) }); });
      });
      var fl = num(floor - (rec.lift || 0) * U * s);
      pose.anchor = (view !== 'side' || run)
        ? { joint: 'pelvis', point: [0, 0], to: 'keep', axis: 'y', floor: fl, points: pts }
        : { joint: 'ankleR', point: pt(ct.heel), to: 'keep', axis: 'x', floor: fl, points: pts };
      out[k] = pose;
    }
    return out;
  }

  function levelsOf(levels) {
    if (!levels) return {};
    if (typeof levels === 'string') {
      if (!D.acts[levels]) throw new Error('Tibi sculpt: unknown activation set "' + levels + '" (have ' + Object.keys(D.acts).join(', ') + ')');
      levels = D.acts[levels];
    }
    var out = {};
    for (var k in levels) {
      if (!own(levels, k)) continue;
      var base = k.split('@')[0], at = k.indexOf('@') > 0 ? k.slice(k.indexOf('@')) : '';
      (ALIAS[base] || [base]).forEach(function (n2) { out[n2 + at] = levels[k]; });
    }
    return out;
  }
  function levelFor(map, name, far) {
    var side = far ? '@far' : '@near';
    if (map[name + side] !== undefined) return map[name + side];
    return map[name] || 0;
  }

  /**
   * Tibi, Cobalt Sculpt.
   *   var t = F.sculpt(stage, {gender: 'female', view: 'side', x: 640, floor: 600, scale: 1});
   * opts: gender 'male'|'female' ('m'|'f'), view 'side'|'front'|'back', x, floor, scale, facing 1|-1,
   *       face 'faceless'|'minimal'|'ember', top 'sport'|'push' (female), spark true|false,
   *       pose (initial named pose), shadow true|false.
   * Scale 1 is about 422 units sole to crown, the classic Tibi's height.
   */
  F.sculpt = function (parent, opts) {
    var o = opts || {};
    var g = /^f/.test(o.gender || 'male') ? 'f' : 'm';
    var view = o.view || 'side';
    if (['side', 'front', 'back', 'top', 'above'].indexOf(view) < 0) throw new Error('Tibi sculpt: view must be side, front, back, top or above (got ' + view + ')');
    var face = o.face === undefined || o.face === null ? 'faceless' : ({ A: 'minimal', C: 'ember' }[o.face] || o.face);
    if (['faceless', 'minimal', 'ember'].indexOf(face) < 0) throw new Error('Tibi sculpt: unknown face "' + face + '"');
    var top = o.top || 'sport';
    if (['sport', 'push'].indexOf(top) < 0) throw new Error('Tibi sculpt: top must be sport or push');
    var s = o.scale || 1, facing = o.facing === -1 ? -1 : 1;
    var floor = o.floor === undefined ? 600 : o.floor;
    var restName = { side: 'stand', front: 'relaxed', back: 'relaxed', top: 'pushup', above: 'fly-high' }[view];
    var lyingView = view === 'top' || view === 'above';
    var rest = D.poses[g][view][o.rest || restName];
    if (!rest) throw new Error('Tibi sculpt: no ' + view + ' pose "' + o.rest + '"');
    var shadow = null;
    if (o.shadow !== false && lyingView) {
      // seen from above (head to the right of the pelvis): a soft shadow of the body on the floor below
      shadow = svg('ellipse', { cx: num((o.x || 0) + facing * 95 * U * s), cy: num((o.y || 0) + 14 * U * s), rx: num(430 * U * s), ry: num(80 * U * s), fill: C.navy, opacity: 0.07, 'class': 'tibi-shadow' }, parent);
    } else if (o.shadow !== false) {
      shadow = svg('ellipse', { cx: o.x || 0, cy: floor + 3 * U * s, rx: num(150 * U * s), ry: num(11 * U * s), fill: C.navy, opacity: 0.09, 'class': 'tibi-shadow' }, parent);
    }
    var holder = svg('g', { 'class': 'tibi tibi-sculpt tibi-' + g + ' tibi-' + view }, parent);
    var maskDefs = svg('defs', {}, holder);
    var poses = {};
    var lib = F.poses && F.poses[view];
    for (var k in lib || {}) if (own(lib, k)) poses[k] = lib[k];
    var jointIds = joints(view, D.skeleton[g]).map(function (j) { return j.id; });
    var own2 = sculptPoses(g, view, s, floor, jointIds);
    for (var k2 in own2) if (own(own2, k2)) poses[k2] = own2[k2];
    var restPose = own2[o.rest || restName];
    var spec = makeSpec({
      g: g, view: view, face: face, top: top, facing: facing, doc: holder.ownerDocument,
      shapeDefs: defsFor(parent), maskDefs: maskDefs, poses: poses,
      rest: { j: restPose.j, f: restPose.f, rot: restPose.rot, ch: restPose.ch }
    });
    var y0 = lyingView ? (o.y || 0) : floor + rest.root[1] * U * s;
    var fig = RIG.figure(holder, spec, { x: o.x || 0, y: y0, scale: s, facing: facing, className: 'tibi-fig' });
    if (!lyingView && (o.rest || restName) !== restName) fig.set(o.rest);
    if (o.spark === false) fig.data.sparks.forEach(function (e) { e.setAttribute('opacity', 0); });
    var T = { fig: fig, view: view, gender: g === 'f' ? 'female' : 'male', face: face, el: holder, shadow: shadow, floor: floor, scale: s, x0: o.x || 0, sculpt: true };
    var cursors = { act: 0, markers: 0, spark: 0 };

    T.to = function (tl, pose, at, dur, op) { return fig.to(tl, pose, at, dur, op); };
    T.sequence = function (tl, steps, at, op) { return fig.sequence(tl, steps, at, op); };
    T.cycle = function (tl, poses2, at, period, count, op) { return fig.cycle(tl, poses2, at, period, count, op); };
    T.set = function (pose) { fig.set(pose); return T; };
    T.point = function (joint, local, pose) { return fig.point(joint, local, pose); };
    T.attach = function (joint, layer) { return fig.attach(joint, layer || 'props'); };
    T.prop = function (joint) { return fig.data.props[joint]; };
    var ct = D.contacts[g];
    function cpt(p) { return [num(p[0] * U), num(p[1] * U)]; }
    T.soleFloor = function () {
      if (view !== 'side') return { y: floor, points: [{ joint: 'ankleR', point: cpt(ct.frontSole) }, { joint: 'ankleL', point: cpt(ct.frontSole) }] };
      return { y: floor, points: [{ joint: 'ankleR', point: cpt(ct.heel) }, { joint: 'toeR', point: cpt(ct.toe) }, { joint: 'ankleL', point: cpt(ct.heel) }, { joint: 'toeL', point: cpt(ct.toe) }] };
    };
    /** The handle centre of a closed hand (joint-local point for follow(): dumbbells, bars). */
    T.grip = function (side) {
      var gp = view === 'side' ? ct.gripSide : ct.gripFront, hs = D.skeleton[g].handScale;
      return { joint: 'wrist' + side, point: [num(gp[0] * U * hs), num(gp[1] * U * hs)] };
    };
    T.sole = function (side) {
      // mid-sole: under the ankle in side view (the forefoot is on the toe joint), the sole centre otherwise
      var p = view === 'side' ? [ct.heel[0] + 18, ct.heel[1]] : ct.frontSole;
      return { joint: 'ankle' + side, point: cpt(p) };
    };

    /**
     * Recolour muscles by role over dur (default 0.5 s). levels: an activation set name
     * ('squat', 'run-mid', 'back-flex', ... see Studio.kit.fitness.sculpt.acts), or a map
     * {muscle: level} with sculpt keys ('quad', 'glute', 'delt@far') or muscles.json ids
     * ('quadriceps', 'gluteus-maximus'). Levels: 3 prime mover, 2 secondary, 1 stabiliser, 0 off.
     * null clears every muscle.
     */
    T.activate = function (tl, levels, at, dur) {
      var d = dur === undefined ? 0.5 : dur;
      if (at < cursors.act - 1e-4) throw new Error('Tibi sculpt: activation at ' + at.toFixed(2) + 's overlaps an earlier one (ends ' + cursors.act.toFixed(2) + 's).');
      var map = levelsOf(levels);
      fig.data.planes.forEach(function (p) {
        var lv = levelFor(map, p.name, p.far);
        if (lv === p.level) return;
        var a = p.level ? LV[String(p.level)] : IDLE, b = lv ? LV[String(lv)] : IDLE;
        var ease = 'power2.inOut';
        tl.fromTo(p.fill, { attr: { fill: a.fill } }, { attr: { fill: b.fill }, duration: d, ease: ease, immediateRender: false }, at);
        tl.fromTo(p.shade, { attr: { fill: a.shade } }, { attr: { fill: b.shade }, duration: d, ease: ease, immediateRender: false }, at);
        tl.fromTo(p.hi, { attr: { fill: p.level ? a.hi : b.hi, opacity: p.level ? 0.9 : 0 } }, { attr: { fill: lv ? b.hi : a.hi, opacity: lv ? 0.9 : 0 }, duration: d, ease: ease, immediateRender: false }, at);
        tl.fromTo(p.halo, { attr: { stroke: p.level ? a.halo : b.halo, 'stroke-opacity': p.level ? a.op : 0 } }, { attr: { stroke: lv ? b.halo : a.halo, 'stroke-opacity': lv ? b.op : 0 }, duration: d, ease: ease, immediateRender: false }, at);
        p.level = lv;
      });
      fig.data.ghosts.forEach(function (q) {
        var lv = levelFor(map, q.name, q.far);
        lv = lv >= 2 ? lv : 0;
        if (lv === q.level) return;
        var ease = 'power2.inOut';
        if (lv && q.level && lv !== q.level) {
          var a = LV[String(q.level)], b = LV[String(lv)];
          tl.fromTo(q.built.fill, { attr: { fill: a.fill } }, { attr: { fill: b.fill }, duration: d, ease: ease, immediateRender: false }, at);
          tl.fromTo(q.built.shade, { attr: { fill: a.shade } }, { attr: { fill: b.shade }, duration: d, ease: ease, immediateRender: false }, at);
          tl.fromTo(q.built.hi, { attr: { fill: a.hi } }, { attr: { fill: b.hi }, duration: d, ease: ease, immediateRender: false }, at);
          tl.fromTo(q.built.halo, { attr: { stroke: a.halo } }, { attr: { stroke: b.halo }, duration: d, ease: ease, immediateRender: false }, at);
        } else {
          if (lv && q.colour !== lv) {
            // entering at a new level: snap the colours at the start of the fade-in
            var a2 = LV[String(q.colour || 2)], c = LV[String(lv)];
            [['fill', 'fill', 'fill'], ['shade', 'fill', 'shade'], ['hi', 'fill', 'hi'], ['halo', 'stroke', 'halo']].forEach(function (x) {
              var from = {}, to = {};
              from[x[1]] = a2[x[2]]; to[x[1]] = c[x[2]];
              tl.fromTo(q.built[x[0]], { attr: from }, { attr: to, duration: 0.001, ease: 'none', immediateRender: false }, at);
            });
            q.colour = lv;
          }
          tl.fromTo(q.g, { attr: { opacity: q.level ? 1 : 0 } }, { attr: { opacity: lv ? 1 : 0 }, duration: d, ease: ease, immediateRender: false }, at);
        }
        q.level = lv;
        if (lv) q.colour = lv;
      });
      cursors.act = at + d;
      return at + d;
    };

    /**
     * Where a muscle plane sits (figure parent coordinates) for the current or a given pose:
     * [{name, level, far, x, y}], near limbs first. name: sculpt key or muscles.json id.
     */
    T.muscle = function (name, pose) {
      var names = ALIAS[name] || [name];
      var p = pose ? RIG.normalise(fig, RIG.lookup(fig, pose), fig.state) : fig.state;
      var out = [];
      fig.data.planes.concat(fig.data.ghosts).forEach(function (q) {
        if (names.indexOf(q.name) < 0 || (q.seg.variant && !shows(q.seg.variant, view === 'side' ? 'down' : armState(p, q.seg.layer.arm), gripOn(p)))) return;
        var b = D.paths[q.id];
        var l = q.seg.layer, loc = [b[2], b[3]];
        var sy = (l.leg ? D.skeleton[g].artLegScale : 1) * (l.s || 1), sx = l.s || 1;
        var local = [loc[0] * sx * U, loc[1] * sy * U];
        if (l.at) { var sh = view === 'side' ? D.skeleton[g].side.shoulder : D.skeleton[g].front.shoulder; local = [local[0] + sh[0] * (l.dside === 'L' ? 1 : -1) * U, local[1] + sh[1] * U]; }
        var w = RIG.point(fig, q.seg.joint, local, p);
        out.push({ name: q.name, level: q.level, far: q.far, x: w[0], y: w[1] });
      });
      out.sort(function (a, b) { return (a.far ? 1 : 0) - (b.far ? 1 : 0); });
      return out;
    };

    /** Show or hide the rig joints (marigold dots, dashed bones): biomechanics anchors. */
    T.markers = function (tl, on, at, dur) {
      var d = dur || 0.3;
      if (at < cursors.markers - 1e-4) throw new Error('Tibi sculpt: marker change overlaps an earlier one.');
      tl.fromTo(fig.data.markers, { attr: { opacity: on ? 0 : 1 } }, { attr: { opacity: on ? 1 : 0 }, duration: d, ease: 'power1.inOut', immediateRender: false }, at);
      cursors.markers = at + d;
      return at + d;
    };
    /** Fade the marigold spark in or out. */
    T.spark = function (tl, on, at, dur) {
      var d = dur || 0.3;
      if (at < cursors.spark - 1e-4) throw new Error('Tibi sculpt: spark change overlaps an earlier one.');
      tl.fromTo(fig.data.sparks, { attr: { opacity: on ? 0 : 1 } }, { attr: { opacity: on ? 1 : 0 }, duration: d, ease: 'power1.inOut', immediateRender: false }, at);
      cursors.spark = at + d;
      return at + d;
    };
    T.state = function () { return { pose: fig.state, activation: fig.data.planes.filter(function (p) { return p.level; }).map(function (p) { return { name: p.name, far: p.far, level: p.level }; }) }; };
    if (o.pose) T.set(o.pose);
    return T;
  };

  F.sculpt.version = D.version;
  F.sculpt.views = ['front', 'side', 'back', 'top', 'above'];
  F.sculpt.faces = ['faceless', 'minimal', 'ember'];
  F.sculpt.tops = ['sport', 'push'];
  F.sculpt.acts = D.acts;
  F.sculpt.names = D.names;
  F.sculpt.poses = function (gender, view) { return Object.keys(D.poses[/^f/.test(gender || 'male') ? 'f' : 'm'][view || 'side']); };
  F.sculpt.aliases = ALIAS;
})(typeof window !== 'undefined' ? window : this);
