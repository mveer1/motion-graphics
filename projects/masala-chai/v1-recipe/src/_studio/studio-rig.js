/*
 * Motion Lab studio runtime - articulated character rig (src/studio/studio-rig.js)
 *
 * A deterministic 2D skeletal rig for HyperFrames: a character kit (for example
 * src/studio/kits/fitness/tibi.js) describes joints, draw layers and shapes; this file builds
 * the SVG, solves forward kinematics at build time and writes poses into the paused timeline
 * as explicit fromTo tweens of each joint group's `transform` attribute.
 *
 * Why attribute strings and not GSAP `rotation`: GSAP's svgOrigin is unreliable inside
 * translated parents (see the hyperframes render pitfalls). Every joint here is
 * <g transform="translate(ox oy) rotate(a)"> in its parent's space, so the pivot is exact.
 *
 * Layer copies: SVG paints in document order, so a near arm must be painted after the near
 * leg even though both hang off the pelvis. Each draw layer therefore holds its own copy of
 * the joint chain it needs; one joint tween targets all copies, so they never drift apart.
 *
 * Determinism: no callbacks write to the DOM. Ground and hand contacts are solved at build
 * time per sample and baked into short linear tweens, so a seek to any frame is exact.
 * Rig tweens on one figure must be added in time order (the rig keeps a cursor and throws
 * when a call would overlap an earlier one).
 */
(function (global) {
  'use strict';

  var Studio = global.Studio || (global.Studio = {});
  var RIG = Studio.rig = {};
  var DEG = Math.PI / 180;
  var EPS = 1e-6;

  function num(v) { return Math.round(v * 1000) / 1000; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function svg(tag, attrs, parent) { return Studio.svg(tag, attrs, parent); }

  // ------------------------------------------------------------------ 2D affine helpers
  // Matrix [a, b, c, d, e, f] maps (x, y) -> (a x + c y + e, b x + d y + f), as in SVG.
  function mul(m, n) {
    return [m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1],
      m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
      m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5]];
  }
  function translate(x, y) { return [1, 0, 0, 1, x, y]; }
  function rotate(deg) { var r = deg * DEG, c = Math.cos(r), s = Math.sin(r); return [c, s, -s, c, 0, 0]; }
  function scale(sx, sy) { return [sx, 0, 0, sy, 0, 0]; }
  function apply(m, p) { return [m[0] * p[0] + m[2] * p[1] + m[4], m[1] * p[0] + m[3] * p[1] + m[5]]; }
  RIG.matrix = { mul: mul, translate: translate, rotate: rotate, scale: scale, apply: apply };

  // ------------------------------------------------------------------ shape helpers
  /**
   * A limb outline from (0,0) to (0,L): widths are half-widths. `mid` may be a number or
   * [back, front] for an asymmetric bulge (calf, biceps). Both ends are round caps, so
   * consecutive segments overlap cleanly at the joint.
   */
  RIG.limb = function (L, w0, mid, w1, at) {
    var mb = typeof mid === 'number' ? mid : mid[0];
    var mf = typeof mid === 'number' ? mid : mid[1];
    var k = at === undefined ? 0.32 : at;
    return 'M' + num(-w0) + ' 0' +
      ' C' + num(-mb) + ' ' + num(L * k * 0.6) + ' ' + num(-mb) + ' ' + num(L * k * 1.4) + ' ' + num(-(mb + w1) / 2) + ' ' + num(L * 0.72) +
      ' S' + num(-w1) + ' ' + num(L * 0.95) + ' ' + num(-w1) + ' ' + num(L) +
      ' A' + num(w1) + ' ' + num(w1) + ' 0 0 0 ' + num(w1) + ' ' + num(L) +
      ' C' + num(w1) + ' ' + num(L * 0.9) + ' ' + num((mf + w1) / 2) + ' ' + num(L * 0.8) + ' ' + num((mf + w1) / 2) + ' ' + num(L * 0.72) +
      ' C' + num(mf) + ' ' + num(L * k * 1.4) + ' ' + num(mf) + ' ' + num(L * k * 0.6) + ' ' + num(w0) + ' 0' +
      ' A' + num(w0) + ' ' + num(w0) + ' 0 0 0 ' + num(-w0) + ' 0 Z';
  };

  /** A closed smooth blob through points [[x,y],...] (Catmull-Rom to cubic Bezier). */
  RIG.blob = function (pts, tension) {
    var t = tension === undefined ? 1 : tension;
    var n = pts.length, d = 'M' + num(pts[0][0]) + ' ' + num(pts[0][1]);
    for (var i = 0; i < n; i++) {
      var p0 = pts[(i - 1 + n) % n], p1 = pts[i], p2 = pts[(i + 1) % n], p3 = pts[(i + 2) % n];
      var c1 = [p1[0] + (p2[0] - p0[0]) / 6 * t, p1[1] + (p2[1] - p0[1]) / 6 * t];
      var c2 = [p2[0] - (p3[0] - p1[0]) / 6 * t, p2[1] - (p3[1] - p1[1]) / 6 * t];
      d += ' C' + num(c1[0]) + ' ' + num(c1[1]) + ' ' + num(c2[0]) + ' ' + num(c2[1]) + ' ' + num(p2[0]) + ' ' + num(p2[1]);
    }
    return d + ' Z';
  };

  /** An open smooth curve through points (Catmull-Rom to cubic Bezier). */
  RIG.curve = function (pts, tension) {
    var t = tension === undefined ? 1 : tension;
    var d = 'M' + num(pts[0][0]) + ' ' + num(pts[0][1]);
    for (var i = 0; i < pts.length - 1; i++) {
      var p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
      var c1 = [p1[0] + (p2[0] - p0[0]) / 6 * t, p1[1] + (p2[1] - p0[1]) / 6 * t];
      var c2 = [p2[0] - (p3[0] - p1[0]) / 6 * t, p2[1] - (p3[1] - p1[1]) / 6 * t];
      d += ' C' + num(c1[0]) + ' ' + num(c1[1]) + ' ' + num(c2[0]) + ' ' + num(c2[1]) + ' ' + num(p2[0]) + ' ' + num(p2[1]);
    }
    return d;
  };

  // ------------------------------------------------------------------ figure
  /**
   * Build a figure.
   *   spec = {
   *     joints: [{id, parent, offset:[x,y], sign:1|-1, base:deg, min, max}],   parent-first order
   *     layers: [{id, joints:[ids]}],          paint order; each layer gets its own chain copy
   *     draw(fig, jointId, layerId, g)         adds shapes for a joint into one layer copy
   *     channels: {name: {make(v) -> [{el, attr:{...}}]}}   optional extra tweenable values
 *     derive(fig, pose) -> [{el | [els], attr:{...}}]   optional attributes computed from a solved
 *       pose (same list length and order for every pose); set at build, tweened per move sample
 *       (moves are sampled when a spec has derive)
   *     poses: {name: pose}, rest: pose
   *   }
   *   opts = {x, y, scale, facing: 1|-1, id}
   * A pose is {x, y, rot, j:{jointId: degrees}, ch:{channel: value}, f:{jointId: factor}}; x/y offset
   * the figure from its placement, rot tilts the whole body (degrees, positive leans toward facing).
   * f is foreshortening (runtime 1.5.1): a segment pointing toward or away from the camera keeps its
   * in-plane angle while its children's offsets shrink along its axis by f (negative folds back past
   * the joint); the kit scales the segment's art by the same f. Absolute per joint: no shear.
   */
  RIG.figure = function (parent, spec, opts) {
    var o = opts || {};
    var fig = {
      spec: spec,
      base: { x: o.x || 0, y: o.y || 0, scale: o.scale || 1, facing: o.facing === -1 ? -1 : 1 },
      joints: {},
      copies: {},
      channels: {},
      cursor: 0,
      parts: {},
      data: {}
    };
    var rootG = svg('g', { 'class': 'rig ' + (o.className || ''), id: o.id || null }, parent);
    if (!o.id) rootG.removeAttribute('id');
    fig.el = rootG;
    if (spec.init) spec.init(fig);
    // the body group carries placement, facing, scale and the pose's x/y/rot
    var bodyCopies = [];
    spec.joints.forEach(function (j) { fig.joints[j.id] = j; fig.copies[j.id] = []; });

    spec.layers.forEach(function (layer) {
      var lg = svg('g', { 'class': 'rig-layer rig-layer-' + layer.id }, rootG);
      var body = svg('g', {}, lg);
      bodyCopies.push(body);
      var made = {};
      var need = {};
      // the chain each layer needs: its joints plus all their ancestors
      layer.joints.forEach(function (id) {
        var cur = id;
        while (cur) { need[cur] = true; cur = fig.joints[cur].parent; }
      });
      spec.joints.forEach(function (j) {
        if (!need[j.id]) return;
        var host = j.parent ? made[j.parent].inner : body;
        var g = svg('g', { 'class': 'rig-j rig-j-' + j.id }, host);
        var content = svg('g', { 'class': 'rig-c' }, g);
        made[j.id] = { g: g, inner: g, content: content };
        fig.copies[j.id].push(g);
        if (layer.joints.indexOf(j.id) >= 0 && spec.draw) spec.draw(fig, j.id, layer.id, content);
      });
    });
    fig.bodyCopies = bodyCopies;

    if (spec.channels) {
      for (var name in spec.channels) {
        if (Object.prototype.hasOwnProperty.call(spec.channels, name)) fig.channels[name] = spec.channels[name];
      }
    }
    fig.state = RIG.normalise(fig, spec.rest || { j: {} });
    RIG.setPose(fig, fig.state);
    fig.addPart = function (kind, el) { (fig.parts[kind] = fig.parts[kind] || []).push(el); return el; };
    fig.to = function (tl, pose, at, dur, options) { return RIG.to(fig, tl, pose, at, dur, options); };
    fig.sequence = function (tl, steps, at, options) { return RIG.sequence(fig, tl, steps, at, options); };
    fig.cycle = function (tl, poses, at, period, count, options) { return RIG.cycle(fig, tl, poses, at, period, count, options); };
    fig.set = function (pose) { fig.state = RIG.resolve(fig, pose, fig.state); RIG.setPose(fig, fig.state); return fig; };
    fig.point = function (jointId, local, pose) { return RIG.point(fig, jointId, local, pose || fig.state); };
    fig.trace = function (jointId, local, poses, steps) { return RIG.trace(fig, jointId, local, poses, steps); };
    fig.pose = function (name) { return RIG.lookup(fig, name); };
    fig.attach = function (jointId, layerId) { return RIG.attach(fig, jointId, layerId); };
    fig.followers = [];
    /**
     * Keep an element's attributes on a point of a joint without inheriting its rotation:
     * make(p) returns attributes for world point p, e.g. {transform:'translate(x y)'} for a barbell
     * plate or {x2, y2} for a cable end. Every later rig move tweens these attributes per sample.
     */
    fig.follow = function (el, jointId, local, make) {
      var f = { els: Studio.all(el), joint: jointId, point: local || [0, 0], make: make };
      fig.followers.push(f);
      var attrs = make(RIG.point(fig, jointId, f.point, fig.state));
      f.els.forEach(function (e) { for (var k in attrs) if (Object.prototype.hasOwnProperty.call(attrs, k)) e.setAttribute(k, attrs[k]); });
      return f;
    };
    return fig;
  };

  /** Look up a named pose from the kit (supports 'name' and 'name~mirror' for left/right swap). */
  RIG.lookup = function (fig, name) {
    if (typeof name !== 'string') return name;
    var mirror = /~mirror$/.test(name);
    var key = name.replace(/~mirror$/, '');
    var p = fig.spec.poses && fig.spec.poses[key];
    if (!p) throw new Error('Studio.rig: unknown pose "' + key + '"');
    p = clone(p);
    if (mirror) p = RIG.mirror(p);
    return p;
  };

  /** Swap left and right joint values (ids ending in L / R). */
  RIG.mirror = function (pose) {
    var out = clone(pose);
    out.j = {};
    for (var k in pose.j) {
      if (!Object.prototype.hasOwnProperty.call(pose.j, k)) continue;
      var m = /L$/.test(k) ? k.replace(/L$/, 'R') : (/R$/.test(k) ? k.replace(/R$/, 'L') : k);
      out.j[m] = pose.j[k];
    }
    if (pose.f) {
      out.f = {};
      for (var fk in pose.f) {
        if (!Object.prototype.hasOwnProperty.call(pose.f, fk)) continue;
        out.f[/L$/.test(fk) ? fk.replace(/L$/, 'R') : (/R$/.test(fk) ? fk.replace(/R$/, 'L') : fk)] = pose.f[fk];
      }
    }
    if (pose.anchor && pose.anchor.joint) {
      out.anchor = clone(pose.anchor);
      out.anchor.joint = pose.anchor.joint.replace(/L$/, '#').replace(/R$/, 'L').replace(/#$/, 'R');
    }
    return out;
  };

  /** Full pose with every joint and channel present (missing values from `prev` or 0). */
  RIG.normalise = function (fig, pose, prev) {
    var p = { x: 0, y: 0, rot: 0, j: {}, ch: {}, f: {} };
    var base = prev || { x: 0, y: 0, rot: 0, j: {}, ch: {}, f: {} };
    p.x = pose.x !== undefined ? pose.x : base.x;
    p.y = pose.y !== undefined ? pose.y : base.y;
    p.rot = pose.rot !== undefined ? pose.rot : base.rot;
    fig.spec.joints.forEach(function (j) {
      var v = pose.j && pose.j[j.id] !== undefined ? pose.j[j.id] : (base.j[j.id] !== undefined ? base.j[j.id] : 0);
      if (j.min !== undefined) v = Math.max(j.min, v);
      if (j.max !== undefined) v = Math.min(j.max, v);
      p.j[j.id] = v;
      p.f[j.id] = pose.f && pose.f[j.id] !== undefined ? pose.f[j.id] : (base.f && base.f[j.id] !== undefined ? base.f[j.id] : 1);
    });
    // flat: ['ankleR', ...] levels those end joints with the floor (linear in joint values, so it survives interpolation)
    (pose.flat || []).forEach(function (id) { p.j[id] = RIG.flatValue(fig, id, p); });
    for (var c in fig.channels) {
      if (!Object.prototype.hasOwnProperty.call(fig.channels, c)) continue;
      p.ch[c] = pose.ch && pose.ch[c] !== undefined ? pose.ch[c] : (base.ch[c] !== undefined ? base.ch[c] : (fig.channels[c].rest || 0));
    }
    return p;
  };

  /** Resolve a pose name/object against the current state, then apply its anchor (contact) constraint. */
  RIG.resolve = function (fig, pose, prev) {
    var raw = RIG.lookup(fig, pose);
    var p = RIG.normalise(fig, raw, prev);
    if (raw.anchor) p = RIG.solveAnchor(fig, p, raw.anchor, prev);
    if (raw.ik) p = RIG.solveIK(fig, p, raw.ik, prev);
    return p;
  };

  /** Sum of SVG rotations from the body down to a joint, in the body's own frame (facing-independent). */
  RIG.chainRotation = function (fig, jointId, pose) {
    var r = pose.rot || 0, cur = jointId;
    while (cur) { var j = fig.joints[cur]; r += (j.base || 0) + (j.sign || 1) * pose.j[cur]; cur = j.parent; }
    return r;
  };

  /** Ankle value that keeps a foot level with the floor (side view), for pose authoring. */
  RIG.flatValue = function (fig, endId, pose) {
    var end = fig.joints[endId];
    return (-RIG.chainRotation(fig, end.parent, pose) - (end.base || 0)) / (end.sign || 1);
  };

  function invert(m) {
    var det = m[0] * m[3] - m[1] * m[2];
    return [m[3] / det, -m[1] / det, -m[2] / det, m[0] / det, (m[2] * m[5] - m[3] * m[4]) / det, (m[1] * m[4] - m[0] * m[5]) / det];
  }

  /**
   * Two-bone IK for limbs: ik = [{chain:[upper, lower, end], to:[x,y] | 'keep', bend:1|-1, flat:true}].
   * Solves the upper and lower joint so the end joint's pivot reaches `to` (figure parent
   * coordinates). bend picks the knee/elbow direction (1 = the joint's positive sign side).
   * flat:true then sets the end joint so the foot stays parallel to the floor (side view).
   */
  RIG.solveIK = function (fig, pose, iks, prev) {
    var out = clone(pose);
    (iks || []).forEach(function (k) {
      var up = fig.joints[k.chain[0]], lo = fig.joints[k.chain[1]], end = fig.joints[k.chain[2]];
      var target = k.to === 'keep' || k.to === undefined ? RIG.point(fig, end.id, [0, 0], prev || fig.state) : k.to;
      var parentM = up.parent ? RIG.jointMatrix(fig, up.parent, out) : bodyMatrix(fig, out);
      var local = apply(invert(parentM), target);
      var hx = up.offset[0], hy = up.offset[1];
      var vx = local[0] - hx, vy = local[1] - hy;
      var a = Math.sqrt(lo.offset[0] * lo.offset[0] + lo.offset[1] * lo.offset[1]);
      var b = Math.sqrt(end.offset[0] * end.offset[0] + end.offset[1] * end.offset[1]);
      var d = Math.min(a + b - 1e-3, Math.max(Math.abs(a - b) + 1e-3, Math.sqrt(vx * vx + vy * vy)));
      var phi = Math.atan2(-vx, vy) / DEG;
      var gamma = Math.acos(Math.max(-1, Math.min(1, (a * a + b * b - d * d) / (2 * a * b)))) / DEG;
      var alpha = Math.acos(Math.max(-1, Math.min(1, (a * a + d * d - b * b) / (2 * a * d)))) / DEG;
      var bend = (k.bend || 1) * (lo.sign || 1);
      var r2 = bend * (180 - gamma), r1 = phi - bend * alpha;
      out.j[up.id] = (r1 - (up.base || 0)) / (up.sign || 1);
      out.j[lo.id] = (r2 - (lo.base || 0)) / (lo.sign || 1);
      if (k.flat) {
        // world rotation of the end segment back to zero: sum of SVG rotations along the chain
        out.j[end.id] = ((k.flatAngle || 0) - RIG.chainRotation(fig, lo.id, out) - (end.base || 0)) / (end.sign || 1);
      }
    });
    return out;
  };

  // a child's offset shrinks along its parent segment's axis (local y) by the parent's foreshortening
  function fore(fig, j, pose) { return j.parent && pose.f && pose.f[j.parent] !== undefined ? pose.f[j.parent] : 1; }
  function jointLocal(fig, j, pose) {
    var a = (j.base || 0) + (j.sign || 1) * pose.j[j.id];
    return mul(translate(j.offset[0], j.offset[1] * fore(fig, j, pose)), rotate(a));
  }

  function bodyMatrix(fig, pose) {
    var b = fig.base;
    return mul(mul(translate(b.x + pose.x, b.y + pose.y), scale(b.scale * b.facing, b.scale)), rotate(pose.rot));
  }

  /** World matrix (parent coordinates of the figure) of a joint for a pose. */
  RIG.jointMatrix = function (fig, jointId, pose) {
    var chain = [];
    var cur = jointId;
    while (cur) { chain.unshift(fig.joints[cur]); cur = fig.joints[cur].parent; }
    var m = bodyMatrix(fig, pose);
    chain.forEach(function (j) { m = mul(m, jointLocal(fig, j, pose)); });
    return m;
  };

  /** Where a point given in a joint's local space lands, in the figure's parent coordinates. */
  RIG.point = function (fig, jointId, local, pose) {
    var p = pose && pose.j ? RIG.normalise(fig, pose, fig.state) : fig.state;
    return apply(RIG.jointMatrix(fig, jointId, p), local || [0, 0]);
  };

  /**
   * Contact constraint: move the body so a point on a joint (a sole, a grip) lands on a target.
   * anchor = {joint, point:[x,y] (joint local), to:[x,y] (figure parent coords) | 'keep'}
   * 'keep' pins the point where it was in the previous pose (a planted foot).
   * axis 'x' or 'y' limits the correction to one axis (a treadmill keeps x, finds the floor).
   */
  RIG.solveAnchor = function (fig, pose, anchor, prev) {
    var target = anchor.to;
    if (target === 'keep' || target === undefined) target = RIG.point(fig, anchor.joint, anchor.point, prev || fig.state);
    var here = apply(RIG.jointMatrix(fig, anchor.joint, pose), anchor.point || [0, 0]);
    var out = clone(pose);
    if (anchor.axis !== 'y') out.x += target[0] - here[0];
    if (anchor.axis !== 'x') out.y += target[1] - here[1];
    if (anchor.floor !== undefined) {
      // lowest of several contact points rests on the floor line (running, walking)
      var low = -Infinity;
      anchor.points.forEach(function (c) {
        var w = apply(RIG.jointMatrix(fig, c.joint, out), c.point);
        if (w[1] > low) low = w[1];
      });
      out.y += anchor.floor - low;
    }
    return out;
  };

  function jointString(fig, j, pose) {
    var a = (j.base || 0) + (j.sign || 1) * pose.j[j.id];
    return 'translate(' + num(j.offset[0]) + ' ' + num(j.offset[1] * fore(fig, j, pose)) + ') rotate(' + num(a) + ')';
  }
  function bodyString(fig, pose) {
    var b = fig.base;
    return 'translate(' + num(b.x + pose.x) + ' ' + num(b.y + pose.y) + ') scale(' + num(b.scale * b.facing) + ' ' + num(b.scale) + ') rotate(' + num(pose.rot) + ')';
  }

  /** Write a pose straight into the DOM (build time, before any tween). */
  RIG.setPose = function (fig, pose) {
    fig.bodyCopies.forEach(function (g) { g.setAttribute('transform', bodyString(fig, pose)); });
    (fig.followers || []).forEach(function (f) {
      var at = f.make(apply(RIG.jointMatrix(fig, f.joint, pose), f.point));
      f.els.forEach(function (e) { for (var k in at) if (Object.prototype.hasOwnProperty.call(at, k)) e.setAttribute(k, at[k]); });
    });
    fig.spec.joints.forEach(function (j) {
      var s = jointString(fig, j, pose);
      fig.copies[j.id].forEach(function (g) { g.setAttribute('transform', s); });
    });
    for (var c in fig.channels) {
      if (!Object.prototype.hasOwnProperty.call(fig.channels, c)) continue;
      fig.channels[c].make(pose.ch[c], fig).forEach(function (t) {
        for (var k in t.attr) if (Object.prototype.hasOwnProperty.call(t.attr, k)) t.el.setAttribute(k, t.attr[k]);
      });
    }
    if (fig.spec.derive) {
      fig.spec.derive(fig, pose).forEach(function (t) {
        Studio.all(t.el).forEach(function (e) { for (var k in t.attr) if (Object.prototype.hasOwnProperty.call(t.attr, k)) e.setAttribute(k, t.attr[k]); });
      });
    }
  };

  function interp(fig, a, b, t) {
    var p = { x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t), rot: lerp(a.rot, b.rot, t), j: {}, ch: {}, f: {} };
    for (var k in a.j) if (Object.prototype.hasOwnProperty.call(a.j, k)) p.j[k] = lerp(a.j[k], b.j[k], t);
    for (var fk in a.f || {}) if (Object.prototype.hasOwnProperty.call(a.f, fk)) p.f[fk] = lerp(a.f[fk], (b.f || {})[fk] === undefined ? 1 : b.f[fk], t);
    for (var c in a.ch) if (Object.prototype.hasOwnProperty.call(a.ch, c)) p.ch[c] = lerp(a.ch[c], b.ch[c], t);
    return p;
  }

  // one linear (or eased) leg of motion between two full poses
  function emit(fig, tl, a, b, at, dur, ease) {
    var e = ease || 'none';
    var ba = bodyString(fig, a), bb = bodyString(fig, b);
    if (ba !== bb) tl.fromTo(fig.bodyCopies, { attr: { transform: ba } }, { attr: { transform: bb }, duration: dur, ease: e, immediateRender: false }, at);
    fig.spec.joints.forEach(function (j) {
      var sa = jointString(fig, j, a), sb = jointString(fig, j, b);
      if (sa !== sb) tl.fromTo(fig.copies[j.id], { attr: { transform: sa } }, { attr: { transform: sb }, duration: dur, ease: e, immediateRender: false }, at);
    });
    (fig.followers || []).forEach(function (f) {
      var fa = f.make(apply(RIG.jointMatrix(fig, f.joint, a), f.point)), fb = f.make(apply(RIG.jointMatrix(fig, f.joint, b), f.point));
      if (JSON.stringify(fa) !== JSON.stringify(fb)) tl.fromTo(f.els, { attr: fa }, { attr: fb, duration: dur, ease: e, immediateRender: false }, at);
    });
    for (var c in fig.channels) {
      if (!Object.prototype.hasOwnProperty.call(fig.channels, c) || Math.abs(a.ch[c] - b.ch[c]) < EPS) continue;
      var from = fig.channels[c].make(a.ch[c], fig), to = fig.channels[c].make(b.ch[c], fig);
      for (var i = 0; i < from.length; i++) {
        tl.fromTo(from[i].el, { attr: from[i].attr }, { attr: to[i].attr, duration: dur, ease: e, immediateRender: false }, at);
      }
    }
    if (fig.spec.derive) {
      // attributes that follow from the solved pose (light-fixed shading, counter-rotations, art swaps):
      // the same list for both poses, tweened only where a value changes
      var da = fig.spec.derive(fig, a), db = fig.spec.derive(fig, b);
      for (var d = 0; d < da.length; d++) {
        if (JSON.stringify(da[d].attr) === JSON.stringify(db[d].attr)) continue;
        tl.fromTo(da[d].el, { attr: da[d].attr }, { attr: db[d].attr, duration: dur, ease: e, immediateRender: false }, at);
      }
    }
  }

  function guard(fig, at) {
    if (at < fig.cursor - 1e-4) {
      throw new Error('Studio.rig: tween at ' + at.toFixed(3) + 's overlaps the previous one (ends ' + fig.cursor.toFixed(3) + 's); add rig moves in time order.');
    }
  }

  /**
   * Move to a pose. options: {ease, samples}. With a contact anchor in the pose, the move is
   * sampled (default 8 per second, at least 4) and the contact solved at every sample, so a
   * planted foot or gripped bar stays put through the whole move.
   */
  RIG.to = function (fig, tl, pose, at, dur, options) {
    var o = options || {};
    guard(fig, at);
    var raw = RIG.lookup(fig, pose);
    var a = fig.state;
    var bFree = RIG.normalise(fig, raw, a);
    var anchor = raw.anchor, ik = raw.ik;
    var ease = o.ease || 'power2.inOut';
    // derived attributes are sampled too, so they follow the joints' arcs rather than a straight chord
    var sampled = (anchor || ik || (fig.followers && fig.followers.length) || fig.spec.derive) && dur > 0;
    if (!sampled) {
      var b = bFree;
      if (anchor) b = RIG.solveAnchor(fig, b, anchor, a);
      if (ik) b = RIG.solveIK(fig, b, ik, a);
      if (dur <= 0) { emit(fig, tl, a, b, at, 0.001, 'none'); } else { emit(fig, tl, a, b, at, dur, ease); }
      fig.state = b;
      fig.cursor = at + Math.max(dur, 0.001);
      return fig.cursor;
    }
    var n = o.samples || Math.max(4, Math.ceil(dur * 10));
    var easeFn = global.gsap.parseEase(ease);
    // pin 'keep' targets to where they were at the start of the move
    var fixedAnchor = anchor && (anchor.to === 'keep' || anchor.to === undefined) ? Object.assign({}, anchor, { to: RIG.point(fig, anchor.joint, anchor.point, a) }) : anchor;
    var fixedIK = ik ? ik.map(function (k) {
      return (k.to === 'keep' || k.to === undefined) ? Object.assign({}, k, { to: RIG.point(fig, k.chain[2], [0, 0], a) }) : k;
    }) : null;
    // IK targets move from where the end joint is now to the target, so the limb travels smoothly
    var prev = a;
    for (var i = 1; i <= n; i++) {
      var s = easeFn(i / n);
      var mid = interp(fig, a, bFree, s);
      if (fixedAnchor) mid = RIG.solveAnchor(fig, mid, fixedAnchor, prev);
      if (fixedIK) mid = RIG.solveIK(fig, mid, fixedIK, prev);
      emit(fig, tl, prev, mid, at + dur * (i - 1) / n, dur / n, 'none');
      prev = mid;
    }
    fig.state = prev;
    fig.cursor = at + dur;
    return fig.cursor;
  };

  /**
   * The solved poses a move would pass through (same sampling and contact solve as RIG.to),
   * without adding tweens: overlays use it to follow a move. Returns n+1 full poses.
   */
  RIG.samples = function (fig, fromPose, toPose, n, ease) {
    var a = fromPose ? RIG.resolve(fig, fromPose, fig.state) : fig.state;
    var raw = RIG.lookup(fig, toPose);
    var bFree = RIG.normalise(fig, raw, a);
    var easeFn = global.gsap.parseEase(ease || 'power2.inOut');
    var anchor = raw.anchor && (raw.anchor.to === 'keep' || raw.anchor.to === undefined) ? Object.assign({}, raw.anchor, { to: RIG.point(fig, raw.anchor.joint, raw.anchor.point, a) }) : raw.anchor;
    var out = [a], prev = a;
    for (var i = 1; i <= n; i++) {
      var mid = interp(fig, a, bFree, easeFn(i / n));
      if (anchor) mid = RIG.solveAnchor(fig, mid, anchor, prev);
      if (raw.ik) mid = RIG.solveIK(fig, mid, raw.ik, prev);
      out.push(mid);
      prev = mid;
    }
    return out;
  };

  /** Steps: [{pose, dur, ease, hold}] played back to back from `at`. Returns the end time. */
  RIG.sequence = function (fig, tl, steps, at, options) {
    var t = at;
    steps.forEach(function (st) {
      t = RIG.to(fig, tl, st.pose, t, st.dur, { ease: st.ease || (options && options.ease), samples: st.samples });
      if (st.hold) t += st.hold;
      fig.cursor = t;
    });
    return t;
  };

  /**
   * A finite cycle (gait, reps): `poses` are evenly spaced keys of one period, played `count`
   * times from `at`, returning to poses[0]. options: {ease ('sine.inOut' by default),
   * floor:{y, points:[{joint, point}]}} lets the lowest contact rest on a floor line each key,
   * which is how a run cycle stays grounded on a treadmill-style stage.
   */
  RIG.cycle = function (fig, tl, poses, at, period, count, options) {
    var o = options || {};
    guard(fig, at);
    var step = period / poses.length;
    var t = at;
    var keys = poses.map(function (p) { return RIG.lookup(fig, p); });
    // floor rule: only the vertical body offset moves, so the lowest contact rests on the floor line
    var ground = function (p) {
      if (!o.floor) return p;
      p.y = 0;
      var low = -Infinity;
      o.floor.points.forEach(function (cpt) {
        var w = apply(RIG.jointMatrix(fig, cpt.joint, p), cpt.point);
        if (w[1] > low) low = w[1];
      });
      p.y += o.floor.y - low;
      return p;
    };
    var solveKey = function (raw, prev) { return ground(RIG.normalise(fig, raw, prev)); };
    var first = solveKey(keys[0], fig.state);
    if (Math.abs(first.y - fig.state.y) > EPS || JSON.stringify(first.j) !== JSON.stringify(fig.state.j) || JSON.stringify(first.f) !== JSON.stringify(fig.state.f)) {
      emit(fig, tl, fig.state, first, t, Math.min(0.25, step), 'power1.inOut');
    }
    var prev = first;
    var sub = o.substeps || 2;
    for (var c = 0; c < count; c++) {
      for (var k = 1; k <= keys.length; k++) {
        var next = solveKey(keys[k % keys.length], prev);
        for (var s = 1; s <= sub; s++) {
          // sub-sample between keys so the floor contact holds between them too
          var mid = s === sub ? next : ground(interp(fig, prev, next, s / sub));
          var from = s === 1 ? prev : ground(interp(fig, prev, next, (s - 1) / sub));
          emit(fig, tl, from, mid, t + step * (s - 1) / sub, step / sub, o.ease || 'none');
          if (s === sub) prev = mid;
        }
        t += step;
      }
    }
    fig.state = prev;
    fig.cursor = t;
    return t;
  };

  /** Path data of a point on a joint through a list of poses (for trajectory overlays). */
  RIG.trace = function (fig, jointId, local, poses, steps) {
    var n = steps || 12;
    var pts = [];
    var state = fig.state;
    var full = poses.map(function (p) { state = RIG.resolve(fig, p, state); return state; });
    for (var i = 0; i < full.length - 1; i++) {
      for (var s = 0; s < n; s++) {
        var mid = interp(fig, full[i], full[i + 1], s / n);
        pts.push(apply(RIG.jointMatrix(fig, jointId, mid), local || [0, 0]));
      }
    }
    pts.push(apply(RIG.jointMatrix(fig, jointId, full[full.length - 1]), local || [0, 0]));
    return { points: pts, d: RIG.curve(pts.filter(function (p, idx) { return idx % 2 === 0 || idx === pts.length - 1; })) };
  };

  /** A new group inside one layer copy of a joint (props held in a hand, a bar on the back). */
  RIG.attach = function (fig, jointId, layerId) {
    var layers = fig.spec.layers.map(function (l) { return l.id; });
    var idx = layerId ? layers.indexOf(layerId) : layers.length - 1;
    var copies = fig.copies[jointId];
    if (!copies || !copies.length) throw new Error('Studio.rig.attach: joint "' + jointId + '" has no layer copy');
    // copies are created in layer order, but only for layers that need the joint
    var pick = null;
    fig.spec.layers.forEach(function (l, li) {
      if (pick || li < idx) return;
      copies.forEach(function (g) { if (!pick && g.closest('.rig-layer-' + l.id)) pick = g; });
    });
    pick = pick || copies[copies.length - 1];
    return svg('g', { 'class': 'rig-attach' }, pick);
  };

  /** Angle (degrees, screen space) of the segment from one joint to a point on its child. */
  RIG.segmentAngle = function (fig, jointA, jointB, pose) {
    var a = RIG.point(fig, jointA, [0, 0], pose), b = RIG.point(fig, jointB, [0, 0], pose);
    return Math.atan2(b[1] - a[1], b[0] - a[0]) / DEG;
  };

  /** Interior angle (degrees) at joint B between A-B and B-C, from the posed figure. */
  RIG.angleAt = function (fig, a, b, c, pose) {
    var pa = RIG.point(fig, a[0], a[1], pose), pb = RIG.point(fig, b[0], b[1], pose), pc = RIG.point(fig, c[0], c[1], pose);
    var v1 = [pa[0] - pb[0], pa[1] - pb[1]], v2 = [pc[0] - pb[0], pc[1] - pb[1]];
    var dot = v1[0] * v2[0] + v1[1] * v2[1];
    var m = Math.sqrt((v1[0] * v1[0] + v1[1] * v1[1]) * (v2[0] * v2[0] + v2[1] * v2[1])) || 1;
    return Math.acos(Math.max(-1, Math.min(1, dot / m))) / DEG;
  };
})(typeof window !== 'undefined' ? window : this);
