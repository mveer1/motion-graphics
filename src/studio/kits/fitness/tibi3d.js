/*
 * Motion Lab fitness kit - Tibi in real 3D (src/studio/kits/fitness/tibi3d.js)
 * Needs vendor/three.min.js (three r158, global THREE) and brand.js. No other runtime dependency, so
 * the rig also loads in node for numeric checks (scripts/rig3d-check.js).
 *
 * WHY THIS EXISTS. The 2D Cobalt Sculpt rig draws every view as a separate set of paths and swaps
 * art variants at joint-angle thresholds (arm "raised" at 50 deg shoulder, "flex" at 60 deg elbow).
 * Each swap is a visible pop: lats and deltoid caps appear from nowhere, and a curl or press snaps
 * at the thresholds. A 3D rig has one skeleton, skinned limbs and muscle meshes that are ALWAYS
 * present (only their colour and bulge change), so there is nothing to pop, and the camera can sit
 * at any angle: front, three-quarter, side, back, above, orbiting.
 *
 * DETERMINISM. HyperFrames seeks with totalTime(t, suppressEvents=true), so GSAP callbacks do not
 * fire. The figure therefore never reads tween state. Everything is a pure function of film time:
 * motion tracks (T3.motion) are evaluated in the setter of ONE linear tween that spans the film,
 * and that setter poses the rig, moves the camera and renders the canvas once. No rAF, no clocks,
 * no Math.random.
 *
 * Units: 1 head = 100 units, standing height 760, hip joint 370 above the floor. Figure faces +z,
 * its left is +x, y is up. Angles are degrees in the API.
 */
(function (global) {
  'use strict';

  var Studio = global.Studio || (global.Studio = {});
  var F = ((Studio.kit = Studio.kit || {}).fitness = Studio.kit.fitness || {});
  var THREE = global.THREE;
  if (!THREE) throw new Error('kits/fitness/tibi3d.js needs vendor/three.min.js loaded first');
  var P = F.palette;
  if (!P) throw new Error('kits/fitness/tibi3d.js needs brand.js loaded first');
  // 0.6.0: ponytail follow-through from the motion history, bending one-piece sole with heel/ball/tip foot roll (tf), bench arch
  // 0.7.0: kwS/kvS aim the knee along the foot in the world (or caved in by kvS deg); the ponytail is two jointed pieces that hang against the head, neck and upper back
  // 0.8.0: shoulder girdle bones gdL/gdR (scapula + clavicle) driven from the arm (T3.GIRDLE, T3.girdle); optional gpS/geS keys
  // 0.9.0: optional garS picks the branch of the bar-alignment hand roll (gax/gay/gaz): it wraps to within 90 deg of garS instead of 0,
  //        so an overhead grip whose roll sits near +-90 no longer flips 180 deg mid-rep (an overhand grip turning underhand for a frame)
  var T3 = F.t3d = { version: '0.9.0' };

  var D2R = Math.PI / 180;
  var V3 = THREE.Vector3, Q = THREE.Quaternion, M4 = THREE.Matrix4;

  // ------------------------------------------------------------------ colours and materials
  var C = T3.colors = {
    skin: '#2A4FD8', muscle: '#4468EA', face: '#5278EE', short: P.short, band: P.spark, shoe: '#FBFBFA', sole: '#B9C2DE',
    hair: '#1C3AA3', hairLight: '#3558CF', spark: P.spark, sparkLight: P.sparkLight,
    prime: '#F2553D', second: '#FFB224', stab: '#8CAEFA',
    steel: P.steel, steelShade: P.steelShade, plate: P.plate, plateFace: P.plateFace, pad: P.pad, padTop: P.padTop,
    floor: '#ECE5D8', paper: P.paper, bust: '#33375C'
  };
  var ROLE_COLOR = { 1: C.stab, 2: C.second, 3: C.prime };

  var gradientMap = null;
  function grad() {
    if (!gradientMap) {
      gradientMap = new THREE.DataTexture(new Uint8Array([70, 125, 195, 255]), 4, 1, THREE.RedFormat);
      gradientMap.minFilter = gradientMap.magFilter = THREE.NearestFilter;
      gradientMap.generateMipmaps = false;
      gradientMap.needsUpdate = true;
    }
    return gradientMap;
  }
  function mat(color, o) {
    return new THREE.MeshToonMaterial(Object.assign({ color: color, gradientMap: grad() }, o || {}));
  }
  T3.material = mat;

  // ------------------------------------------------------------------ geometry helpers
  function catmull(p0, p1, p2, p3, t) {
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t);
  }
  /** keys: [[y, rx, rz, cz, cx?], ...] -> n rows, Catmull-Rom on every channel (smooth radius profile). */
  function sampleRows(keys, n) {
    var out = [], m = keys.length;
    for (var i = 0; i < n; i++) {
      var u = n === 1 ? 0 : i / (n - 1) * (m - 1), k = Math.min(m - 2, Math.floor(u)), t = u - k, row = [];
      for (var c = 0; c < keys[0].length; c++) {
        row.push(catmull(keys[Math.max(0, k - 1)][c], keys[k][c], keys[k + 1][c], keys[Math.min(m - 1, k + 2)][c], t));
      }
      out.push(row);
    }
    return out;
  }
  /**
   * A closed tube along y through elliptical rings. rows: [y, rx, rz, cz, cx]. p = superellipse
   * exponent (2 = ellipse, higher = squarer). wfn(y, x) -> [[boneIndex, weight], ...] makes it a skin.
   */
  function loft(rows, seg, o) {
    o = o || {};
    var p = o.p || 2, grow = o.grow || 0, n = rows.length, pos = [], idx = [], si = [], sw = [], r, a, i;
    for (r = 0; r < n; r++) {
      var row = rows[r];
      for (i = 0; i < seg; i++) {
        a = i / seg * Math.PI * 2;
        var ca = Math.cos(a), sa = Math.sin(a);
        var ex = Math.sign(ca) * Math.pow(Math.abs(ca), 2 / p), ez = Math.sign(sa) * Math.pow(Math.abs(sa), 2 / p);
        var x = (row[4] || 0) + (row[1] + grow) * ex, z = (row[3] || 0) + (row[2] + grow) * ez;
        pos.push(x, row[0], z);
        if (o.wfn) { var w = o.wfn(row[0], x); fillSkin(w, si, sw); }
      }
    }
    for (r = 0; r < n - 1; r++) {
      for (i = 0; i < seg; i++) {
        var i2 = (i + 1) % seg, a0 = r * seg + i, b0 = r * seg + i2, a1 = (r + 1) * seg + i, b1 = (r + 1) * seg + i2;
        idx.push(a0, b0, a1, b0, b1, a1);
      }
    }
    // end caps (fans to a centre vertex)
    [0, n - 1].forEach(function (rr, which) {
      var row = rows[rr], c = pos.length / 3;
      pos.push(row[4] || 0, row[0], row[3] || 0);
      if (o.wfn) fillSkin(o.wfn(row[0], row[4] || 0), si, sw);
      for (var j = 0; j < seg; j++) {
        var j2 = (j + 1) % seg, A = rr * seg + j, B = rr * seg + j2;
        if (which === 0) idx.push(c, A, B); else idx.push(c, B, A);
      }
    });
    var g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setIndex(idx);
    g.computeVertexNormals();
    var nrm = g.getAttribute('normal'), px = g.getAttribute('position');
    // outward check on a middle-row vertex at +x: flip the winding if the normal points inward
    var probe = Math.floor(n / 2) * seg, cx = rows[Math.floor(n / 2)][4] || 0;
    if ((px.getX(probe) - cx) * nrm.getX(probe) < 0) {
      for (var t = 0; t < idx.length; t += 3) { var tmp = idx[t + 1]; idx[t + 1] = idx[t + 2]; idx[t + 2] = tmp; }
      g.setIndex(idx); g.computeVertexNormals();
    }
    if (o.wfn) {
      g.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(si, 4));
      g.setAttribute('skinWeight', new THREE.Float32BufferAttribute(sw, 4));
    }
    return g;
  }
  function fillSkin(w, si, sw) {
    for (var k = 0; k < 4; k++) { si.push(w[k] ? w[k][0] : 0); sw.push(w[k] ? w[k][1] : 0); }
  }
  /** Linear blend weights: stops [[y, boneIndex], ...] sorted by descending y; between two stops the weight slides. */
  function blendAlong(stops) {
    return function (y) {
      if (y >= stops[0][0]) return [[stops[0][1], 1]];
      for (var i = 0; i < stops.length - 1; i++) {
        var hi = stops[i], lo = stops[i + 1];
        if (y <= hi[0] && y >= lo[0]) {
          var t = (hi[0] - y) / (hi[0] - lo[0]);
          t = t * t * (3 - 2 * t);                                  // smoothstep: soft crease at the joint
          return t <= 0.001 ? [[hi[1], 1]] : t >= 0.999 ? [[lo[1], 1]] : [[hi[1], 1 - t], [lo[1], t]];
        }
      }
      return [[stops[stops.length - 1][1], 1]];
    };
  }

  // ------------------------------------------------------------------ body specs (rig units)
  var SPEC = {
    m: {
      torso: [[-50, 60, 40, 0], [-12, 76, 50, -2], [40, 68, 45, 0], [100, 61, 40, 2], [150, 77, 46, 2], [190, 93, 51, 2], [220, 86, 42, -2], [240, 60, 36, -3], [252, 34, 29, -3], [262, 23, 23, 0]],
      shx: 88, shy: 228, hipx: 40, mscale: 1.0, bust: false
    },
    f: {
      torso: [[-50, 58, 41, 0], [-12, 76, 52, -2], [40, 58, 43, 0], [100, 47, 36, 2], [150, 63, 42, 2], [190, 78, 47, 2], [220, 72, 40, -2], [240, 50, 33, -3], [252, 30, 27, -3], [262, 21, 21, 0]],
      shx: 76, shy: 226, hipx: 40, mscale: 0.88, bust: true
    }
  };

  // ------------------------------------------------------------------ the figure
  /**
   * T3.tibi(stage-or-group, {gender: 'm'|'f', id: ''}) builds one Tibi. Returns the figure API:
   *   fig.root      THREE.Group, the figure's world transform (set by apply)
   *   fig.apply(p)  pose from a flat dictionary of numbers; omitted values use fig.defaultPose. A dictionary from motion.at(t)
   *                 also carries (non-enumerably) where it came from, so the ponytail can look back along the motion; a copied
   *                 or hand-built dictionary gives the static hang for that pose
   *   fig.supports  world Box3s of pads the head may rest on (exercises register their bench: T3.restsOn)
   *   fig.defaultPose  the figure's neutral stance; DEFAULT_POSE remains the authored-motion fallback
   *   fig.roles(acts)  {muscleKey: 1|2|3} fixes which muscles can light up and in which role colour
   *   fig.hold(side, obj3d)  puts equipment in a hand
   *   fig.world(name) world position of a named anchor ('wristL', 'chest', 'biceps@L', ...)
   *   fig.bone       the skeleton; since 0.8.0 each arm hangs from a girdle bone gdS (scapula + clavicle, posed from the arm:
   *                  T3.GIRDLE) and the soft-tissue frame axS skins the skin that crosses the joint. gdS.userData.girdle holds the
   *                  current {up, protraction, elevation} in degrees
   */
  var DEFAULT_POSE = {
    x: 0, y: 370, z: 0, yaw: 0, pitch: 0, roll: 0,
    lean: 0, twist: 0, bend: 0, neckF: 0, headF: 0, headY: 0,
    // arms, per side L/R: elevation from hanging (0 = at the side, 90 = horizontal), plane (0 = out to the side, 90 = forward),
    // axial rotation, elbow flexion, wrist flexion, forearm pronation, IK switch, wrist offset from the shoulder in world units, elbow pole
    // ikcS = 1 reads hx/hy/hz and px/py/pz in the CHEST frame instead of the world (a bar on the back or across the hips rides the trunk)
    shL: 6, plL: 70, rtL: 0, elL: 6, wrL: 0, prL: 0, gaxL: 0, gayL: 0, gazL: 0, garL: 0, ikL: 0, ikcL: 0, hxL: 0, hyL: -230, hzL: 0, pxL: 1, pyL: 0, pzL: 0,
    shR: 6, plR: 70, rtR: 0, elR: 6, wrR: 0, prR: 0, gaxR: 0, gayR: 0, gazR: 0, garR: 0, ikR: 0, ikcR: 0, hxR: 0, hyR: -230, hzR: 0, pxR: -1, pyR: 0, pzR: 0,
    // shoulder girdle (0.8.0, see GIRDLE): the scapula follows the arm by itself; gpS adds protraction (+, shoulder forward) or
    // retraction (-, blades pinched), geS a shrug (+) or depression (-), in degrees of clavicle swing. Leave both 0 unless the cue is about the blades.
    gpL: 0, geL: 0, gpR: 0, geR: 0,
    // legs, per side: IK to a planted foot (ikS = 1: foot sole target fxS, fyS (lift), fzS and yaw fyawS in the world), else FK angles.
    // hlS = heel lift in degrees (calf raise): the shoe hinges at the ball, which stays where fx/fz put it; the toe box stays flat.
    //   hlS < 0 is a heel rocker (heel strike): the foot pivots on the heel, toes up. tfS = toe-off roll in degrees (0..hlS): the
    //   toe box tilts about its tip, so the contact rolls from the ball to the tip; past TOE_MAX of sole bend it starts by itself.
    //   kfS = knee turn-out of the IK pole in the PELVIS frame; kwS = 1 instead aims the knee along the foot (fyawS) in the WORLD,
    //   which stays meaningful when the hip is flexed ~90 deg (hinge, lunge, push-up) and the pelvis-frame pole lies along the thigh.
    //   kvS (with kwS) turns that pole toward the midline by kvS degrees: the knee caves in (valgus), a teaching mistake.
    ikLegL: 1, fxL: 40, fyL: 0, fzL: 0, fyawL: 0, hlL: 0, tfL: 0, hpL: 0, haL: 0, knL: 0, anL: 0, kfL: 8, kwL: 0, kvL: 0,
    ikLegR: 1, fxR: -40, fyR: 0, fzR: 0, fyawR: 0, hlR: 0, tfR: 0, hpR: 0, haR: 0, knR: 0, anR: 0, kfR: 8, kwR: 0, kvR: 0
  };
  /** Ball of the foot in the ankle frame: the hinge of a heel lift and the contact point of the toe box. */
  var BALL = { y: -26, z: 62 };
  T3.BALL = BALL;
  /** Heel and toe-tip contact points of the sole (ankle frame; the tip is 34 ahead of the ball on the toe box). */
  var HEEL = { y: -26, z: -26 }, TIP = { y: -26, z: 96 }, TOE_MAX = 45;
  T3.HEEL = HEEL; T3.TIP = TIP; T3.TOE_MAX = TOE_MAX;
  // the sole bends across this length (ankle-frame z) centred on the ball; ahead of it everything rides the toe box
  var SHOE_BEND_LEN = 24;
  /*
   * Ponytail (female). centre: skull centre in the head frame (the mount turns about it); pivot: top of the tail in the knot's
   * frame; rest: the tail axis (pivot to tip) as authored; theta = pitch of the hang (0 down the neck line, + toward the back),
   * psi = side swing; limits keep it off the nape and shoulders (measured by rig3d-check). Follow-through: the tail direction
   * is a damped second-order response (f Hz, zeta) of the hang the head and gravity ask for over the last `win` seconds of the
   * motion, re-evaluated from the motion itself at every frame: a pure function of t, never state carried between frames.
   * Resting: the knot and tail never sink more than `touch` into the floor or a registered support (fig.supports, a pad as a
   * heightfield that rounds off past its edges with radius `edge`).
   */
  var PONY = { centre: [0, 55, 0], pivot: [0, -4, -22], rest: new V3(0, -85, 9.6).normalize(), touch: 0.5, edge: 40,
    thetaMin: -14, thetaMax: 175, psiMax: 65, faceFrom: 0.7, lean: 2.0, aMax: 0.8, tipGravity: 0.85, sideFree: 35, around: 80, bodyGap: -0.5, joint: 44, tipLen: 42, gravity: 0.7, f: 1.4, zeta: 0.3, win: 1.0, dt: 1 / 30, g: 4260 };
  T3.PONY = PONY;
  // (forward, up) of v rotated by a degrees heel-up about a pivot
  function rockAbout(f, u, a) { var c = Math.cos(a), s = Math.sin(a); return [f * c + u * s, u * c - f * s]; }
  /**
   * Foot roll: ankle offset {up, fwd} from its flat position, and the sole bend (toe box relative to the rearfoot, degrees,
   * toes up), for a rearfoot pitch hl (heel up > 0) and a toe-off roll tf. hl >= 0 pivots on the ball (the toe box stays flat)
   * and, past TOE_MAX of bend or when tf > 0, the toe box tilts about its tip; hl < 0 pivots on the heel (rigid foot).
   * With tf = 0 and hl <= TOE_MAX this is exactly the old heelLift, so planted balls stay put in existing exercises.
   */
  T3.footRoll = function (hl, tf) {
    var a = hl * D2R;
    if (hl < 0) {
      var r = rockAbout(-HEEL.z, -HEEL.y, a);
      return { up: r[1] + HEEL.y, fwd: r[0] + HEEL.z, bend: 0, toe: hl, pivot: 'heel' };
    }
    var t = Math.min(hl, Math.max(tf || 0, hl - TOE_MAX)), tr = t * D2R;
    var ball = rockAbout(BALL.z - TIP.z, 0, tr);                                    // the ball rides up as the toe box tilts on its tip
    var bf = ball[0] + TIP.z - BALL.z, bu = ball[1];
    var up = -BALL.y * Math.cos(a) + BALL.z * Math.sin(a) + BALL.y, fwd = BALL.z * (1 - Math.cos(a)) - BALL.y * Math.sin(a);
    return { up: up + bu, fwd: fwd + bf, bend: hl - t, toe: t, pivot: t > 0 ? 'tip' : 'ball' };
  };
  /** Ankle offset (up, forward along the foot) that keeps the ball planted for a heel lift of a degrees. */
  T3.heelLift = function (deg) { var r = T3.footRoll(deg, 0); return { up: r.up, fwd: r.fwd }; };
  /*
   * Shoulder girdle (0.8.0). A real shoulder moves the scapula and clavicle with the arm (scapulohumeral rhythm): above roughly 25-30
   * degrees of elevation about one degree of scapular upward rotation for every two at the glenohumeral joint, protraction when the
   * hand reaches forward and across the body, and clavicle elevation overhead. Up to 0.7.0 the arm turned about a joint fixed in the
   * chest, so the skin blended between chest and arm folded flat on cross-body reach and overhead (linear-blend crush).
   * One girdle bone per side (gdL/gdR, a child of the chest at the glenohumeral joint; the arm hangs from it) carries the clavicle's
   * swing about the sternoclavicular joint as a move of the joint, and the scapula's rotation as its own rotation. Both are a pure
   * function of the humerus direction in the chest frame (T3.girdle), so no pose key is needed; gpS/geS add a deliberate blade
   * position. The humerus keeps exactly the direction and twist the pose asks for (the arm bone is posed relative to the girdle), and
   * an IK hand stays exactly where it was put; a direct-angle (FK) hand rides the moved shoulder (a few units, up to ~17 overhead).
   *   onset/soft/rhythm  upward rotation = rhythm * ramp(elevation - onset), ramp a C1 soft hinge of width 2 * soft: 0 below 20 deg,
   *                      about 23 deg at 90, 59 at 175 (Inman 1944's classic 2:1 above ~30 deg puts about 60 of 180 at the scapula;
   *                      later 3D studies report somewhat less, so this sits at the upper end; illustrative, not measured)
   *   plane/follow       upward rotation turns about the normal of the scapular plane (35 deg forward of the frontal plane), turned
   *                      up to atan(follow) toward the arm's own plane of elevation (never past it, so it cannot flip)
   *   elev               clavicle elevation at 175 deg (degrees, scaled with the upward rotation)
   *   protract, reach    protraction (degrees, clavicle about the vertical) for a hand reaching forward and across: the measure
   *                      0.5 z - 0.8 x of the humerus direction (left side), eased over `reach`, faded in with elevation 20..90
   *   sc                 sternoclavicular joint relative to the glenohumeral joint's height and the chest's midline ([x scaled by the
   *                      shoulder half-width / 88, dy, z] in the chest frame)
   *   tissue             the soft-tissue frame axS (the skin and muscle that cross the joint: deltoid root, axillary folds): the
   *                      humerus's own rotation from its bind (A-pose) direction against the girdle, scaled back by `lag` as that
   *                      rotation grows over `on` degrees. Near the bind it IS the humerus (the neutral stance is ~18 deg away, so
   *                      standing skin does not move); overhead or across the body it trails the bone, and it shares the axial twist,
   *                      so skin next to the joint turns part of the way and the rest of the turn spreads down the upper arm.
   *                      Skin weights: anatomy3d.js GIRDLE_WEIGHTS.
   * Legacy-profile figures keep a still girdle (byte-identical to 0.7.0).
   */
  var GIRDLE = T3.GIRDLE = { onset: 20, soft: 15, rhythm: 0.42, plane: 35, follow: 0.6, elev: 12, protract: 18, reach: [0.1, 0.9], sc: [14, -8, 22],
    tissue: { lag: 0.5, on: [25, 70] } };
  function girdleRamp(x) { var s = GIRDLE.soft; return x <= 0 ? 0 : x < 2 * s ? x * x / (4 * s) : x - s; }
  function smooth01(a, b, x) { var t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); }
  /**
   * T3.girdle(d, spec, gp, ge): the girdle for a humerus pointing along unit vector d in the chest frame, LEFT side convention (mirror
   * x for the right arm). Returns {up, protraction, elevation (degrees), q: the girdle rotation about the glenohumeral joint (chest
   * frame), off: the joint's move (chest frame units)}. gp/ge: extra protraction/elevation in degrees (pose keys gpS/geS).
   */
  T3.girdle = function (d, S, gp, ge) {
    var G = GIRDLE, th = Math.acos(Math.max(-1, Math.min(1, -d.y))) / D2R;
    var up = G.rhythm * girdleRamp(th - G.onset), full = G.rhythm * girdleRamp(175 - G.onset);
    var el = (full > 0 ? G.elev * up / full : 0) + (ge || 0);
    var pr = G.protract * smooth01(G.reach[0], G.reach[1], 0.5 * d.z - 0.8 * d.x) * smooth01(G.onset, 90, th) + (gp || 0);
    var pl = G.plane * D2R, hx = Math.cos(pl), hz = Math.sin(pl), hl = Math.sqrt(d.x * d.x + d.z * d.z);
    if (hl > 1e-9) {
      var ax = d.x / hl, az = d.z / hl, dot = ax * hx + az * hz, k = G.follow * smooth01(0.05, 0.35, hl);
      var nx = hx + k * (ax - dot * hx), nz = hz + k * (az - dot * hz), nl = Math.sqrt(nx * nx + nz * nz);
      hx = nx / nl; hz = nz / nl;
    }
    // swing of "down" toward (hx, 0, hz): axis down x h = (-hz, 0, hx); then protraction turns the glenoid forward about the vertical
    var q = new Q().setFromAxisAngle(new V3(0, 1, 0), -pr * D2R).multiply(new Q().setFromAxisAngle(new V3(-hz, 0, hx), up * D2R));
    var gh = new V3(S.shx, S.shy - 150, -2), sc = new V3(G.sc[0] * S.shx / 88, S.shy - 150 + G.sc[1], G.sc[2]);
    var c = gh.clone().sub(sc), c2 = c.clone().applyAxisAngle(new V3(0, 0, 1), el * D2R).applyAxisAngle(new V3(0, 1, 0), -pr * D2R);
    return { up: up, protraction: pr, elevation: el, q: q, off: c2.sub(c) };
  };
  T3.DEFAULT_POSE = DEFAULT_POSE;
  T3.SPEC = SPEC;

  T3.tibi = function (parent, opts) {
    var o = opts || {}, g = o.gender === 'f' ? 'f' : 'm', S = SPEC[g], pre = o.id ? o.id + '.' : '';
    var profileSampling = o.profileSampling === undefined ? 'distance' : o.profileSampling;
    if (profileSampling !== 'legacy' && profileSampling !== 'distance') throw new Error('Unknown Tibi profileSampling: ' + profileSampling);
    var poseDefaults = profileSampling === 'legacy' ? DEFAULT_POSE :
      Object.assign({}, DEFAULT_POSE, { shL: 8, plL: 10, shR: 8, plR: 10 });
    var root = new THREE.Group();
    root.name = 'tibi-' + g;
    if (parent) parent.add(root);

    // ---- bones (bind pose, y up, hips joint at the root's origin)
    var bones = [], bone = {};
    function B(name, parentBone, x, y, z) {
      var b = new THREE.Bone(); b.name = name; b.position.set(x, y, z);
      (parentBone || root).add(b); bone[name] = b; bones.push(b); b.userData.index = bones.length - 1; return b;
    }
    B('hips', null, 0, 0, 0);
    B('spine', bone.hips, 0, 70, 0);
    B('chest', bone.spine, 0, 80, 0);
    B('neck', bone.chest, 0, 95, 0);
    B('head', bone.neck, 0, 30, 0);
    ['L', 'R'].forEach(function (s) {
      var sg = s === 'L' ? 1 : -1;
      B('sh' + s, bone.chest, sg * S.shx, S.shy - 150, -2);
      B('el' + s, bone['sh' + s], 0, -134, 0);
      B('hand' + s, bone['el' + s], 0, -106, 0);
      B('th' + s, bone.hips, sg * S.hipx, -6, 0);
      B('kn' + s, bone['th' + s], 0, -178, 0);
      B('an' + s, bone['kn' + s], 0, -166, 0);
    });
    // 0.8.0: the shoulder girdle (scapula + clavicle, see GIRDLE) sits at the glenohumeral joint and carries the arm. Appended last so
    // every older bone keeps its skin index; at rest it coincides with the chest frame, so the bind matrices do not change.
    ['L', 'R'].forEach(function (s) {
      var sh = bone['sh' + s], gd = B('gd' + s, bone.chest, sh.position.x, sh.position.y, sh.position.z);
      gd.add(sh); sh.position.set(0, 0, 0);
    });
    // The soft-tissue frame (axS) between scapula and humerus: at the joint, swinging part of the way with the humerus (GIRDLE.tissue).
    ['L', 'R'].forEach(function (s) { B('ax' + s, bone['gd' + s], 0, 0, 0); });
    var ghRest = { L: bone.gdL.position.clone(), R: bone.gdR.position.clone() }, girdleOn = profileSampling !== 'legacy';
    var I = function (n) { return bone[n].userData.index; };
    if (!T3.anatomy) throw new Error('kits/fitness/tibi3d.js needs kits/fitness/anatomy3d.js loaded after it (before exercises3d.js)');
    // Bind pose is an A-pose (arms 26 deg, legs 4 deg out) so the ONE skin never fuses at the armpit or crotch. The inverses are captured
    // while the limbs are out; every frame then poses the bones absolutely, so the rest pose of the bones is still the straight one.
    ['L', 'R'].forEach(function (s) {
      var sg = s === 'L' ? 1 : -1;
      bone['sh' + s].rotation.z = sg * T3.anatomy.BIND.arm * D2R; bone['th' + s].rotation.z = sg * T3.anatomy.BIND.leg * D2R;
      bone['ax' + s].rotation.z = sg * T3.anatomy.BIND.arm * D2R;
    });
    root.updateMatrixWorld(true);
    var skeleton = new THREE.Skeleton(bones);
    var rootInv = new M4().copy(root.matrixWorld).invert(), boneBind = {}, boneIndex = {};
    bones.forEach(function (b, i) { boneBind[b.name] = new M4().multiplyMatrices(rootInv, b.matrixWorld); boneIndex[b.name] = i; });
    var axBind = { L: bone.axL.quaternion.clone(), R: bone.axR.quaternion.clone() };
    ['L', 'R'].forEach(function (s) { bone['sh' + s].rotation.z = 0; bone['th' + s].rotation.z = 0; bone['ax' + s].quaternion.copy(axBind[s]); });
    root.updateMatrixWorld(true);
    function bp(n) { var e = boneBind[n].elements; return [e[12], e[13], e[14]]; }
    var joints = { shL: bp('shL'), shR: bp('shR'), hipL: bp('thL'), hipR: bp('thR') };

    // ---- the body: ONE continuous skin (torso, limbs, neck, head, hands) whose muscles are part of its surface. See anatomy3d.js.
    var body = T3.anatomy.attach({ root: root, bone: bone, bones: bones, skeleton: skeleton, S: S, g: g, joints: joints, boneBind: boneBind, boneIndex: boneIndex, profileSampling: profileSampling });
    var muscles = body.muscles;

    // ---- rigid parts that really are separate objects: the spark, the ponytail, shoes
    function ell(parentBone, color, cx, cy, cz, rx, ry, rz, rot) {
      var m = new THREE.Mesh(new THREE.SphereGeometry(1, 22, 14), typeof color === 'string' ? mat(color) : color);
      m.position.set(cx, cy, cz); m.scale.set(rx, ry, rz);
      if (rot) m.rotation.set((rot[0] || 0) * D2R, (rot[1] || 0) * D2R, (rot[2] || 0) * D2R);
      parentBone.add(m); return m;
    }
    var head = bone.head;
    var spark = new THREE.Group(); head.add(spark); spark.position.set(0, 98, -4);
    [[0, 0, 0, 13, 38, 12, 0], [14, -4, 0, 8, 24, 8, -20], [-13, -4, 0, 7, 20, 7, 22]].forEach(function (f) {
      var cone = new THREE.Mesh(new THREE.ConeGeometry(1, 2, 14), mat(C.spark)); cone.position.set(f[0], f[1] + f[4] * 0.5, f[2]);
      cone.scale.set(f[3], f[4], f[5]); cone.rotation.z = f[6] * D2R; spark.add(cone);
    });
    var pony = null, ponyMount = null, ponyTail = null, ponyTip = null;
    if (g === 'f') {
      // knot and band ride the head; the tail swings on its own pivot (applyPose: hair()). The mount turns the whole ponytail
      // about the skull centre only when the knot would sink into the surface the head lies on (it rolls toward the crown).
      ponyMount = new THREE.Group(); ponyMount.name = 'pony-mount'; ponyMount.position.set(0, PONY.centre[1], PONY.centre[2]); head.add(ponyMount);
      pony = new THREE.Group(); pony.name = 'pony'; pony.position.set(0, 74 - PONY.centre[1], -34 - PONY.centre[2]); ponyMount.add(pony);
      ell(pony, C.hair, 0, -4, -10, 15, 16, 15);
      ell(pony, C.spark, 0, 6, -6, 9, 6, 9);
      ponyTail = new THREE.Group(); ponyTail.name = 'pony-tail'; ponyTail.position.set(0, PONY.pivot[1], PONY.pivot[2]); pony.add(ponyTail);
      // 0.7.0: two pieces jointed PONY.joint below the pivot, so the free end can hang with gravity when the root has to go round the
      // head (face down); aligned, they make the 0.6.0 silhouette (one ellipsoid 14 x 46 x 13 centred 40 below the pivot)
      ell(ponyTail, C.hair, 0, -19.5, -4.4, 14, 25, 13, [-12, 0, 0]);   // both pieces on the 0.6.0 ellipsoid's own tilted axis
      ell(ponyTail, C.hairLight, 0, -30 - PONY.pivot[1], -16 - PONY.pivot[2], 7, 26, 6, [-12, 0, 0]);
      ponyTip = new THREE.Group(); ponyTip.name = 'pony-tip'; ponyTip.position.set(0, -43.9, 0.8); ponyTail.add(ponyTip);
      ell(ponyTip, C.hair, 0, -20.5, 4.4, 13.5, 21, 12.5, [-12, 0, 0]);
    }
    // ---- shoes: one upper and ONE sole that bend at the ball (shoeBend), so the sole bridges heel and toe box at any toe angle.
    // The toe group is the hinge marker (its rotation is the bend; contacts read the tip through it); it carries no mesh.
    var toes = {}, shoes = {};
    ['L', 'R'].forEach(function (s) {
      var foot = bone['an' + s], parts = [];
      function bent(geo, color, name) {
        var m = new THREE.Mesh(geo, mat(color)); m.name = name;
        m.userData.base = Float32Array.from(geo.getAttribute('position').array);
        foot.add(m); parts.push(m); return m;
      }
      function ellGeo(cx, cy, cz, rx, ry, rz) {
        return new THREE.SphereGeometry(1, 24, 16).scale(rx, ry, rz).translate(cx, cy, cz);
      }
      bent(ellGeo(0, -11, 22, 23, 15, 48), C.shoe, 'shoe');                           // rearfoot upper (reaches past the ball)
      bent(ellGeo(0, BALL.y + 13, BALL.z + 8, 22.5, 14, 27), C.shoe, 'shoe-toe');      // toe box
      bent(soleGeo(), C.sole, 'sole');
      ell(foot, C.shoe, 0, 4, -10, 20, 20, 20);                                       // heel counter (rigid)
      var toe = new THREE.Group(); toe.position.set(0, BALL.y, BALL.z); foot.add(toe);
      toes[s] = toe; shoes[s] = { parts: parts, bend: 0 };
    });
    /** The sole: a flat-bottomed slab from the heel (z -28) to the toe tip (z 99), bottom at y -26.3, as one lofted mesh. */
    function soleGeo() {
      var rows = sampleRows([[-28, 9, 2.6, 22.3], [-24, 19, 4.2, 22.1], [-14, 22, 4.3, 22], [10, 21, 4.3, 22], [35, 22, 4.3, 22],
        [62, 24, 4.3, 22], [80, 23.5, 4.3, 22], [92, 19, 4, 22.3], [99, 9, 2.6, 23]], 34);
      var geo = loft(rows, 24, { p: 4 }), ix = geo.getIndex().array, c0 = geo.getAttribute('position').count - 2;
      for (var t = 0; t < ix.length; t += 3) {                              // turn the two end caps outward (loft winds them inward)
        if (ix[t] >= c0 || ix[t + 1] >= c0 || ix[t + 2] >= c0) { var sw = ix[t + 1]; ix[t + 1] = ix[t + 2]; ix[t + 2] = sw; }
      }
      geo.getIndex().needsUpdate = true; geo.computeVertexNormals();
      return geo.rotateX(Math.PI / 2);
    }
    /**
     * Bend every shoe part at the ball by deg (toe box relative to the rearfoot, toes up > 0), as a beam bends: across a zone of
     * SHOE_BEND_LEN centred on the ball the parts wrap round a circle (constant curvature); behind it they ride the rearfoot,
     * ahead of it they turn rigidly about the ball exactly as the toe group does. The circle is chosen so both ends meet those
     * rigid parts, so the underside is one tangent-continuous curve (a fillet between the floor and the rearfoot), never a hinge.
     */
    function shoeBend(s, deg) {
      var sh = shoes[s];
      if (sh.bend === deg) return;
      sh.bend = deg;
      var a = deg * D2R, L = SHOE_BEND_LEN, zA = BALL.z - L / 2, ca = Math.cos(a), sa = Math.sin(a);
      var rho = a > 1e-5 ? L / a : 0, cy = a > 1e-5 ? BALL.y + L / (2 * Math.tan(a / 2)) : 0, yb = cy - rho;
      sh.parts.forEach(function (m) {
        var b = m.userData.base, pa = m.geometry.getAttribute('position'), arr = pa.array;
        for (var i = 0; i < b.length; i += 3) {
          var y = b[i + 1], z = b[i + 2], u = z - zA;
          arr[i] = b[i];
          if (a <= 1e-5 || u <= 0) { arr[i + 1] = y; arr[i + 2] = z; }
          else if (u >= L) { var dz = z - BALL.z, dy = y - BALL.y; arr[i + 1] = BALL.y + dz * sa + dy * ca; arr[i + 2] = BALL.z + dz * ca - dy * sa; }
          else { var th = u / rho, r = rho - (y - yb); arr[i + 1] = cy - r * Math.cos(th); arr[i + 2] = zA + r * Math.sin(th); }
        }
        pa.needsUpdate = true;
        m.geometry.computeVertexNormals(); m.geometry.computeBoundingSphere(); m.geometry.computeBoundingBox();
      });
    }

    // ---- pose application
    var tmpV = new V3(), tmpQ = new Q(), tmpM = new M4(), tmpQ2 = new Q();
    function ikLimb(parentBone, jointBone, midBone, a, b, targetLocal, poleLocal, bendSign) {
      // targetLocal: end point relative to the limb's root joint, in the root joint's parent frame.
      var d = targetLocal.length(), maxD = a + b - 0.5, minD = Math.abs(a - b) + 0.5;
      var dd = Math.min(maxD, Math.max(minD, d));
      var u = targetLocal.clone().multiplyScalar(1 / (d || 1));
      var cosB = (a * a + dd * dd - b * b) / (2 * a * dd);
      var beta = Math.acos(Math.max(-1, Math.min(1, cosB)));
      var cosG = (a * a + b * b - dd * dd) / (2 * a * b);
      var flex = Math.PI - Math.acos(Math.max(-1, Math.min(1, cosG)));
      var pole = poleLocal.clone(); pole.addScaledVector(u, -pole.dot(u));
      if (pole.lengthSq() < 1e-6) pole.set(0, 0, 1).addScaledVector(u, -u.z);
      pole.normalize();
      var upper = u.clone().multiplyScalar(Math.cos(beta)).addScaledVector(pole, Math.sin(beta)).normalize();
      var fore = targetLocal.clone().multiplyScalar(dd / (d || 1)).addScaledVector(upper, -a).normalize();
      var zl = fore.clone().addScaledVector(upper, -fore.dot(upper));
      if (zl.lengthSq() < 1e-8) zl.copy(pole);
      zl.normalize().multiplyScalar(bendSign);
      var yl = upper.clone().multiplyScalar(-1), xl = new V3().crossVectors(yl, zl).normalize();
      zl.crossVectors(xl, yl).normalize();
      tmpM.makeBasis(xl, yl, zl);
      jointBone.quaternion.setFromRotationMatrix(tmpM);
      return flex;
    }
    var shoulderW = new V3(), anchors = {};
    var curPose = {};
    function R0(k) { var v = curPose[pre + k]; return v === undefined ? poseDefaults[k] : v; }
    /** Pose side s's girdle for the humerus direction dL (left-side convention); returns {q, off} in that side's chest frame. */
    function girdleFor(s, dL, g) {
      g = g || T3.girdle(dL, S, R0('gp' + s), R0('ge' + s));
      var q = g.q.clone(), off = g.off.clone(), gd = bone['gd' + s];
      if (s === 'R') { q.set(q.x, -q.y, -q.z, q.w); off.x = -off.x; }
      gd.position.copy(ghRest[s]).add(off); gd.quaternion.copy(q);
      gd.userData.girdle = { up: g.up, protraction: g.protraction, elevation: g.elevation };
      return { q: q, off: off };
    }
    /** Wrist flexion and forearm roll of side s's hand from the pose (gaxS..: roll so a held bar lies along a world direction). */
    function handPose(s, el, hd) {
      var pr = R0('pr' + s) * D2R * (s === 'L' ? 1 : -1);
      var gx = R0('gax' + s), gy = R0('gay' + s), gz = R0('gaz' + s);
      if (gx * gx + gy * gy + gz * gz > 1e-6) {
        // roll the hand about the forearm so a held bar's axis lines up with a world direction
        el.updateWorldMatrix(true, false);
        var qe = new Q().setFromRotationMatrix(el.matrixWorld).invert();
        var tl = new V3(gx, gy, gz).applyQuaternion(qe);
        pr = Math.atan2(-tl.z, tl.x);
        // a bar is symmetric under a half turn: take the roll within 90 deg of the branch reference garS (default 0, the old wrap)
        var ref = R0('gar' + s) * D2R;
        while (pr - ref > Math.PI / 2) pr -= Math.PI;
        while (pr - ref < -Math.PI / 2) pr += Math.PI;
      }
      hd.rotation.set(-R0('wr' + s) * D2R, pr, 0);
    }
    /** Root and trunk chain from a pose reader: the real bones, or the ghost chain the ponytail uses to look back in time. */
    function poseTrunk(R, o) {
      o.root.position.set(R('x'), R('y'), R('z'));
      o.root.rotation.set(R('pitch') * D2R, R('yaw') * D2R, R('roll') * D2R, 'YXZ');
      // trunk: spread over the lumbar and thoracic joints
      var lean = R('lean') * D2R, tw = R('twist') * D2R, bd = R('bend') * D2R;
      o.spine.rotation.set(lean * 0.4, tw * 0.4, bd * 0.4);
      o.chest.rotation.set(lean * 0.6, tw * 0.6, bd * 0.6);
      o.neck.rotation.set(R('neckF') * D2R * 0.5, R('headY') * D2R * 0.4, 0);
      o.head.rotation.set((R('neckF') * 0.5 + R('headF')) * D2R, R('headY') * D2R * 0.6, 0);
    }

    // ---- ponytail secondary motion (pure function of the motion: see PONY)
    var ghost = null, hairW = null, supports = [];
    if (ponyTail) {
      ghost = { root: new THREE.Object3D() };
      var gPrev = ghost.root;
      ['hips', 'spine', 'chest', 'neck', 'head'].forEach(function (n) {
        var o = new THREE.Object3D(); o.position.copy(bone[n].position); o.quaternion.copy(bone[n].quaternion); gPrev.add(o); ghost[n] = o; gPrev = o;
      });
      ghost.pivot = new THREE.Object3D(); ghost.head.add(ghost.pivot);
      ghost.pivot.position.set(0, 74 + PONY.pivot[1], -34 + PONY.pivot[2]);
      // damped second-order impulse response, tapered over the last 30% of the window, normalised: a still head gives the static hang
      var wn = 2 * Math.PI * PONY.f, wd = wn * Math.sqrt(1 - PONY.zeta * PONY.zeta), N = Math.round(PONY.win / PONY.dt), sum = 0;
      hairW = [];
      for (var k = 0; k < N; k++) {
        var tau = k * PONY.dt, taper = Math.min(1, (N - k) / (0.3 * N));
        var w = Math.exp(-PONY.zeta * wn * tau) * Math.sin(wd * (tau + 0.5 * PONY.dt)) * taper * taper;
        hairW.push(w); sum += w;
      }
      for (k = 0; k < N; k++) hairW[k] /= sum;
    }
    var hairTmp = { P: [], Q: [] }, gEff = new V3(), uSum = new V3(), gSum = new V3(), uK = new V3(), qInv = new Q(), mountQ = new Q();
    /** World pivot position and head orientation for pose dictionary d (the knot mount at rest). */
    function ghostAt(d, P, Qh) {
      poseTrunk(function (k) { var v = d[pre + k]; return v === undefined ? poseDefaults[k] : v; }, ghost);
      ghost.root.updateMatrixWorld(true);
      var pm = root.parent ? root.parent.matrixWorld : null;
      P.setFromMatrixPosition(ghost.pivot.matrixWorld); if (pm) P.applyMatrix4(pm);
      tmpM.copy(ghost.head.matrixWorld); if (pm) tmpM.premultiply(pm);
      Qh.setFromRotationMatrix(tmpM);
    }
    function softClamp(x, lo, hi, k) {
      if (x < lo + k) return lo + k * Math.exp((x - lo - k) / k);
      if (x > hi - k) return hi - k * Math.exp((hi - k - x) / k);
      return x;
    }
    /**
     * How deep a hair group's mesh vertices go below the floor or into what the head rests on: each support (fig.supports: world
     * Box3s of the pads the head can rest on, registered by the exercise that builds them) is a heightfield, flat over the pad
     * and rounding down past its edges (radius PONY.edge), so a tail hanging over an edge drapes on it and the depth changes
     * smoothly with the pose (a hard box corner made the resting angle jump). Exact, on the posed vertices; 0 when clear.
     */
    var hv = new V3();
    function supportDepth(group) {
      var depth = 0;
      group.children.forEach(function (m) {
        if (!m.isMesh) return;
        var pa = m.geometry.getAttribute('position');
        for (var j = 0; j < pa.count; j++) {
          hv.fromBufferAttribute(pa, j).applyMatrix4(m.matrixWorld);
          if (hv.y < 0) depth = Math.max(depth, -hv.y);
          for (var s = 0; s < supports.length; s++) {
            var bx = supports[s], dx = Math.max(bx.min.x - hv.x, 0, hv.x - bx.max.x), dz = Math.max(bx.min.z - hv.z, 0, hv.z - bx.max.z);
            var h = bx.max.y - (dx * dx + dz * dz) / (2 * PONY.edge);
            if (hv.y < h) depth = Math.max(depth, h - hv.y);
          }
        }
      });
      return depth;
    }
    /*
     * The tail against the body (0.7.0). A cloud of about 500 skin points with normals (head, neck, upper trunk and shoulders),
     * taken once from the bind-pose skin (pose-independent) and carried rigidly by each point's dominant bone every frame.
     * bodyHang(u) starts from the hang the head and gravity ask for (u, world) and, for a fixed number of steps, pushes the tail's
     * axis stations (radius from the tail ellipsoid) out along the normal of the nearest skin point: a continuous, pure function of
     * the pose. The head counts only from 34 units along the tail (the knot sits on it by design). When the hang points through
     * the head toward the face (bent over, face down) it leans a little to the figure's left first, so it slides round the head on
     * one known side (never flips) and hangs past the cheek. Upright, nothing is touched: the 0.6.0 hang, unchanged.
     */
    var hairBody = null, HB = { q: new V3(), n: new V3(), D: new V3(), P: new V3(), m: new M4(), pts: null };
    function hairProxies() {
      if (hairBody) return hairBody;
      var geo = body.skin.geometry, pa = geo.getAttribute('position'), na = geo.getAttribute('normal'), si = geo.getAttribute('skinIndex'), sw = geo.getAttribute('skinWeight');
      var want = { head: 1, neck: 1, chest: 1, shL: 1, shR: 1, gdL: 1, gdR: 1, axL: 1, axR: 1 }, cand = [], v = new V3(), nv = new V3();
      for (var i = 0; i < pa.count; i++) {
        var best = 0, bw = -1;
        for (var k = 0; k < 4; k++) { var w = sw.getComponent(i, k); if (w > bw) { bw = w; best = si.getComponent(i, k); } }
        var nm = bones[best].name;
        if (!want[nm]) continue;
        v.fromBufferAttribute(pa, i);
        if (nm !== 'head' && v.y < joints.shL[1] - 60) continue;                  // upper trunk only (the tail never reaches lower)
        if (v.x < 0) continue;                                                     // the left half; the right is its mirror image
        cand.push([best, nm, v.x, v.y, v.z, na.getX(i), na.getY(i), na.getZ(i)]);
      }
      var step = Math.max(1, Math.round(cand.length / 300)), list = [], mirror = { shL: 'shR', gdL: 'gdR', axL: 'axR' };
      for (i = 0; i < cand.length; i += step) {
        var r = cand[i]; list.push(r);
        if (r[2] > 1e-3) list.push([mirror[r[1]] ? boneIndex[mirror[r[1]]] : r[0], mirror[r[1]] || r[1], -r[2], r[3], r[4], -r[5], r[6], r[7]]);
      }
      hairBody = { bones: list.map(function (r) { return r[0]; }), head: list.map(function (r) { return r[1] === 'head'; }),
        bind: list.map(function (r) { return [r[2], r[3], r[4], r[5], r[6], r[7]]; }), world: list.map(function () { return [0, 0, 0, 0, 0, 0]; }),
        inv: bones.map(function (bn) { return new M4().copy(boneBind[bn.name]).invert(); }) };
      return hairBody;
    }
    function hairPoints() {                                                  // carry the cloud rigidly with each dominant bone
      var hb = hairProxies(), m = HB.m, v = HB.q, nv = HB.n;
      for (var i = 0; i < hb.bind.length; i++) {
        var bi = hb.bones[i], b = hb.bind[i], o = hb.world[i];
        m.multiplyMatrices(bones[bi].matrixWorld, hb.inv[bi]);
        v.set(b[0], b[1], b[2]).applyMatrix4(m); nv.set(b[3], b[4], b[5]).transformDirection(m);
        o[0] = v.x; o[1] = v.y; o[2] = v.z; o[3] = nv.x; o[4] = nv.y; o[5] = nv.z;
      }
      return hb;
    }
    // tail axis stations (from the pivot) and their radii: the tail ellipsoid (centre 40 along, half-length 46, radius 14)
    var TAIL_S0 = [10, 22, 34, 44], TAIL_R0 = TAIL_S0.map(function (s) { var u = (s - 22) / 26; return Math.max(5, 14 * Math.sqrt(Math.max(0, 1 - u * u))); });
    var TIP_S = [6, 15, 24, 33, 40], TIP_R = TIP_S.map(function (s) { var u = (s - 21) / 21; return Math.max(5, 13 * Math.sqrt(Math.max(0, 1 - u * u))); });
    function bodyPush(hb, P, D, out, TAIL_S, TAIL_R, hf) {
      var any = false, q = HB.D, W = hb.world, L = TAIL_S[TAIL_S.length - 1];
      out.set(0, 0, 0);
      for (var k = 0; k < TAIL_S.length; k++) {
        q.copy(P).addScaledVector(D, TAIL_S[k]);
        // a smooth kernel over the skin the station can touch (reach = its radius + 12): the weighted mean push along the normals;
        // a nearest-point rule switched points between frames and broke symmetric poses' symmetry
        var reach = TAIL_R[k] + 12, sw = 0, px = 0, py = 0, pz = 0;
        for (var j = 0; j < W.length; j++) {
          if (hb.head[j] && TAIL_S[k] < hf) continue;
          var w = W[j], dx = q.x - w[0], dy = q.y - w[1], dz = q.z - w[2], dd = dx * dx + dy * dy + dz * dz;
          if (dd >= reach * reach) continue;
          var pen = TAIL_R[k] + PONY.bodyGap - (dx * w[3] + dy * w[4] + dz * w[5]);
          if (pen <= 0) continue;
          var kw = 1 - Math.sqrt(dd) / reach; kw *= kw;
          sw += kw; px += w[3] * pen * kw; py += w[4] * pen * kw; pz += w[5] * pen * kw;
        }
        if (sw > 0) { var f = TAIL_S[k] / L / Math.max(sw, 0.25); out.x += px * f; out.y += py * f; out.z += pz * f; any = true; }
      }
      return any;
    }
    function bodyHang(u, qPony) {
      var P = HB.P.setFromMatrixPosition(ponyTail.matrixWorld), D = new V3().copy(u), push = new V3(), hb = hairPoints();
      bone.head.updateWorldMatrix(true, false);
      var face = new V3(0, 0, 1).transformDirection(bone.head.matrixWorld), left = new V3(1, 0, 0).transformDirection(bone.head.matrixWorld);
      var f = Math.max(0, Math.min(1, (-face.y - PONY.faceFrom) / 0.25)); f = f * f * (3 - 2 * f);   // the head's pitch, not the lagging hang
      if (f > 0) D.addScaledVector(left, PONY.lean * f).normalize();
      var qi = new Q().copy(qPony).invert(), th = 0, ps = 0, tmin = PONY.thetaMin;
      for (var pass = 0; pass < 3; pass++) {
        for (var it = 0; it < 10; it++) { if (!bodyPush(hb, P, D, push, TAIL_S0, TAIL_R0, 34)) break; D.multiplyScalar(44).add(push).normalize(); }
        var d = D.clone().applyQuaternion(qi);
        th = Math.atan2(-d.z, -d.y) / D2R; ps = Math.asin(Math.max(-1, Math.min(1, d.x))) / D2R;
        ps = softClamp(ps, -PONY.psiMax, PONY.psiMax, 6);
        var side = Math.min(1, Math.abs(ps) / PONY.sideFree); side = side * side * (3 - 2 * side);
        tmin = PONY.thetaMin - PONY.around * side;                       // behind the neck the nape limit holds; beside the head it lifts
        th = softClamp(th, tmin, PONY.thetaMax, 6);
        D.copy(hairDir(th, ps)).applyQuaternion(qPony);
      }
      return { th: th, ps: ps, tmin: tmin };
    }
    /**
     * The free end (0.7.0): it hangs where the head and gravity ask (u, world), pushed out of the head, neck and upper trunk, and is
     * straightened back toward the root only as far as needed to stay out of the floor and the pads (bisection, so it rests on them).
     */
    var TIP_REST = PONY.rest;
    function tipHang(u) {
      ponyTip.quaternion.identity(); ponyTip.updateMatrixWorld(true);
      var P = new V3().setFromMatrixPosition(ponyTip.matrixWorld), D = new V3().copy(u), push = new V3(), hb = hairPoints();
      for (var it = 0; it < 12; it++) { if (!bodyPush(hb, P, D, push, TIP_S, TIP_R, 0)) break; D.multiplyScalar(40).add(push).normalize(); }
      var qT = new Q().setFromRotationMatrix(ponyTail.matrixWorld).invert(), local = D.clone().applyQuaternion(qT), q0 = new Q(), q1 = new Q().setFromUnitVectors(TIP_REST, local);
      function at(l) { ponyTip.quaternion.copy(q0).slerp(q1, l); ponyTip.updateMatrixWorld(true); return supportDepth(ponyTip); }
      // swing from the root's line toward the hang; stop at the first contact (scanning from the root keeps it continuous)
      var lo = 0, hi = null;
      for (var k = 1; k <= 16; k++) { if (at(k / 16) > PONY.touch) { hi = k / 16; break; } lo = k / 16; }
      if (hi !== null) {
        for (var i = 0; i < 14; i++) { var mid = (lo + hi) / 2; if (at(mid) > PONY.touch) hi = mid; else lo = mid; }
        at(lo); ponyTip.userData.rested = true;
      } else { at(1); ponyTip.userData.rested = false; }
    }
    function hairDir(th, ps) {
      var t = th * D2R, s = ps * D2R;
      return new V3(Math.sin(s), -Math.cos(s) * Math.cos(t), -Math.cos(s) * Math.sin(t));
    }
    function hair(p, R) {
      // 1. the hang the head and gravity ask for at each past instant, filtered: D (world). Without a motion (a hand-built pose
      //    dictionary) there is no history: the tail takes the static hang for this pose.
      var src = p && p.__src, n = src ? hairW.length : 1, P = hairTmp.P, QQ = hairTmp.Q, i;
      for (i = 0; i < (src ? n + 2 : 1); i++) {
        if (!P[i]) { P[i] = new V3(); QQ[i] = new Q(); }
        ghostAt(i === 0 ? p : src.motion.at(src.t - i * PONY.dt), P[i], QQ[i]);
      }
      uSum.set(0, 0, 0); gSum.set(0, 0, 0);
      for (i = 0; i < n; i++) {
        gEff.set(0, -PONY.g, 0);                       // effective gravity in the pivot's frame: g minus the pivot's acceleration
        if (src) {
          uK.copy(P[i]).addScaledVector(P[i + 1], -2).add(P[i + 2]).multiplyScalar(1 / (PONY.dt * PONY.dt));
          var al = uK.length(); if (al > PONY.aMax * PONY.g) uK.multiplyScalar(PONY.aMax * PONY.g / al);   // a jerk can never flip gravity
          gEff.sub(uK);
        }
        gEff.normalize();
        uK.copy(PONY.rest).applyQuaternion(QQ[i]).multiplyScalar(1 - PONY.tipGravity).addScaledVector(gEff, PONY.tipGravity).normalize();
        gSum.addScaledVector(uK, src ? hairW[i] : 1);                  // the free end: mostly gravity (0.7.0)
        gEff.multiplyScalar(PONY.gravity);
        uK.copy(PONY.rest).applyQuaternion(QQ[i]).multiplyScalar(1 - PONY.gravity).add(gEff).normalize();
        uSum.addScaledVector(uK, src ? hairW[i] : 1);
      }
      uSum.normalize(); gSum.normalize();
      // 2. the knot: roll the mount toward the crown only as far as needed to keep the knot out of what the head rests on
      head.updateWorldMatrix(true, false);
      var beta = 0, lo, hi, mid;
      function knotDepth(b) { ponyMount.rotation.set(b * D2R, 0, 0); ponyMount.updateMatrixWorld(true); return supportDepth(pony); }
      if (knotDepth(0) > PONY.touch) {
        lo = 0; hi = 0; var best = 0, bestD = Infinity;
        for (var b = 5; b <= 90; b += 5) { var kd = knotDepth(b); if (kd < bestD) { bestD = kd; best = b; } if (kd <= PONY.touch) { hi = b; break; } lo = b; }
        if (hi) { for (i = 0; i < 16; i++) { mid = (lo + hi) / 2; if (knotDepth(mid) <= PONY.touch) hi = mid; else lo = mid; } beta = hi; } else beta = best;
      }
      ponyMount.rotation.set(beta * D2R, 0, 0); ponyMount.updateMatrixWorld(true);
      // 3. into the knot frame, keep it off the nape and shoulders (soft limits), then out of the floor and the supports
      var qPony = mountQ.setFromRotationMatrix(pony.matrixWorld);
      var d = uSum.clone().applyQuaternion(qInv.copy(qPony).invert());
      var th = Math.atan2(-d.z, -d.y) / D2R, ps = Math.asin(Math.max(-1, Math.min(1, d.x))) / D2R;
      // 0.7.0: the tail HANGS against the head, neck and upper back instead of passing through them (bodyHang); the nape limit
      // only holds while the tail is behind the neck, so beside the head it can keep falling toward the floor
      var hang = bodyHang(uSum, qPony), tmin = PONY.thetaMin;
      th = hang.th; ps = hang.ps; tmin = hang.tmin;
      function tailDepth(t) { ponyTail.quaternion.setFromUnitVectors(PONY.rest, hairDir(t, ps)); ponyTip.quaternion.identity(); ponyTail.updateMatrixWorld(true); return Math.max(supportDepth(ponyTail), supportDepth(ponyTip)); }
      var supported = tailDepth(th) > PONY.touch;
      if (supported) {
        // swing the tail off the surface the way that buries it less (a tie goes toward the back of the head, past the crown when
        // lying), to the first pitch at which it just rests on it
        var dPlus = th + 5 <= PONY.thetaMax ? tailDepth(th + 5) : Infinity, dMinus = th - 5 >= tmin ? tailDepth(th - 5) : Infinity;
        var dir = dPlus <= dMinus ? 1 : -1;
        var found = null, least = th, leastD = Infinity, prev = th;
        for (var pass = 0; pass < 2 && found === null; pass++, dir = -dir) {     // no resting place that way: try the other way
          prev = th;
          for (var step = 2.5; step <= 190 && found === null; step += 2.5) {
            var c = th + dir * step;
            if (c < tmin || c > PONY.thetaMax) break;
            var cd = tailDepth(c);
            if (cd < leastD) { leastD = cd; least = c; }
            if (cd <= PONY.touch) found = c; else prev = c;
          }
        }
        if (found !== null) {
          lo = prev; hi = found;
          for (i = 0; i < 16; i++) { mid = (lo + hi) / 2; if (tailDepth(mid) <= PONY.touch) hi = mid; else lo = mid; }
          th = hi;
        } else th = least;
      }
      ponyTail.quaternion.setFromUnitVectors(PONY.rest, hairDir(th, ps)); ponyTail.updateMatrixWorld(true);
      tipHang(gSum);
      ponyTail.userData.theta = th; ponyTail.userData.psi = ps; ponyTail.userData.supported = supported; ponyMount.userData.beta = beta;
    }

    function applyPose(pIn) {
      var p = pIn; curPose = p;
      var R = R0;
      poseTrunk(R, { root: root, spine: bone.spine, chest: bone.chest, neck: bone.neck, head: bone.head });
      root.updateMatrixWorld(true);
      // arms (0.8.0: each from its girdle, which follows the humerus; see GIRDLE)
      ['L', 'R'].forEach(function (s) {
        var sg = s === 'L' ? 1 : -1, sh = bone['sh' + s], el = bone['el' + s], hd = bone['hand' + s], gd = bone['gd' + s], gr = null;
        if (girdleOn) { gd.position.copy(ghRest[s]); gd.quaternion.identity(); }
        if (R('ik' + s) > 0.5) {
          bone.chest.updateWorldMatrix(true, false);
          sh.updateWorldMatrix(true, false);
          shoulderW.setFromMatrixPosition(sh.matrixWorld);
          var inv = tmpQ.setFromRotationMatrix(bone.chest.matrixWorld).invert();
          if (R('ikc' + s) > 0.5) inv.identity();                         // targets already in the chest frame
          var t = new V3(R('hx' + s), R('hy' + s), R('hz' + s)).applyQuaternion(inv);
          var pol = new V3(R('px' + s), R('py' + s), R('pz' + s)).applyQuaternion(inv);
          var flex = ikLimb(bone.chest, sh, el, 134, 106, t, pol, 1), handW = null;
          if (girdleOn) {
            // a planted or holding hand keeps the orientation the pose gave it from the unmoved joint (the wrist takes up the
            // shoulder's few units of travel), so palms stay flat and bars stay level whatever the girdle does
            el.rotation.set(-flex, 0, 0); handPose(s, el, hd); hd.updateWorldMatrix(true, false);
            handW = new Q().setFromRotationMatrix(hd.matrixWorld);
            // the girdle from the solved humerus, then the arm again from the moved joint to the SAME hand target
            var dh = new V3(0, -1, 0).applyQuaternion(sh.quaternion);
            gr = girdleFor(s, dh.set(sg * dh.x, dh.y, dh.z));
            t.sub(gr.off);
            flex = ikLimb(bone.chest, sh, el, 134, 106, t, pol, 1);
            sh.quaternion.premultiply(tmpQ2.copy(gr.q).invert());
          }
          el.rotation.set(-flex, 0, 0);
        } else {
          var th = R('sh' + s) * D2R, pl = R('pl' + s) * D2R;
          var dir = new V3(Math.sin(th) * Math.cos(pl), -Math.cos(th), Math.sin(th) * Math.sin(pl));
          var swing = new Q().setFromUnitVectors(new V3(0, -1, 0), dir);
          var twist = new Q().setFromAxisAngle(new V3(0, 1, 0), R('rt' + s) * D2R);
          swing.multiply(twist);
          if (girdleOn) {
            var g0 = T3.girdle(dir, S, R('gp' + s), R('ge' + s));             // dir is in the left-side convention
            swing.premultiply(g0.q.clone().invert());
          }
          if (s === 'R') { swing.set(swing.x, -swing.y, -swing.z, swing.w); }   // mirror across the sagittal plane
          sh.quaternion.copy(swing);
          if (girdleOn) girdleFor(s, dir, g0);
          el.rotation.set(-R('el' + s) * D2R, 0, 0);
        }
        if (girdleOn) {
          // soft-tissue frame: the humerus's own rotation from its bind (A-pose) relative to the girdle, scaled back by `lag` once it is
          // far from the bind; near the bind (the neutral stance is ~18 deg away) it IS the humerus, so standing skin does not move
          var qb = axBind[s], dq = tmpQ2.copy(sh.quaternion).multiply(tmpQ.copy(qb).invert()), ts = GIRDLE.tissue;
          var da = 2 * Math.acos(Math.min(1, Math.abs(dq.w))) / D2R, lag = ts.lag * smooth01(ts.on[0], ts.on[1], da);
          bone['ax' + s].quaternion.slerpQuaternions(tmpQ.identity(), dq, 1 - lag).multiply(qb);
        }
        if (handW) {
          el.updateWorldMatrix(true, false);
          hd.quaternion.copy(tmpQ.setFromRotationMatrix(el.matrixWorld).invert().multiply(handW));
        } else handPose(s, el, hd);
      });
      root.updateMatrixWorld(true);
      // legs: IK to planted feet (world), else FK
      ['L', 'R'].forEach(function (s) {
        var sg = s === 'L' ? 1 : -1, th = bone['th' + s], kn = bone['kn' + s], an = bone['an' + s];
        if (R('ikLeg' + s) > 0.5) {
          bone.hips.updateWorldMatrix(true, false);
          var invH = new M4().copy(bone.hips.matrixWorld).invert();
          var hl = R('hl' + s), roll = T3.footRoll(hl, R('tf' + s)), yw = R('fyaw' + s) * D2R;
          var target = new V3(R('fx' + s) + roll.fwd * Math.sin(yw), R('fy' + s) + 26 + roll.up, R('fz' + s) + roll.fwd * Math.cos(yw)).applyMatrix4(invH);
          var origin = th.position.clone();
          var rel = target.sub(origin);
          var kf = R('kf' + s) * D2R, pole = R('kw' + s) > 0.5 ? new V3(Math.sin(yw - sg * R('kv' + s) * D2R), 0, Math.cos(yw - sg * R('kv' + s) * D2R)).transformDirection(invH) : new V3(Math.sin(kf) * sg, 0, Math.cos(kf));
          var kflex = ikLimb(bone.hips, th, kn, 178, 166, rel, pole, -1);
          kn.rotation.set(kflex, 0, 0);
          kn.updateWorldMatrix(true, false);
          var qShin = new Q().setFromRotationMatrix(kn.matrixWorld);
          var qFoot = new Q().setFromAxisAngle(new V3(0, 1, 0), R('fyaw' + s) * D2R);
          an.quaternion.copy(qShin.invert().multiply(qFoot));
          an.quaternion.multiply(tmpQ2.setFromAxisAngle(new V3(1, 0, 0), (R('an' + s) + hl) * D2R));
          toes[s].rotation.set(-roll.bend * D2R, 0, 0);                       // the toe box stays flat on the floor (or rolls on its tip)
          shoeBend(s, roll.bend);
        } else {
          th.rotation.set(-R('hp' + s) * D2R, 0, sg * R('ha' + s) * D2R, 'XYZ');
          kn.rotation.set(R('kn' + s) * D2R, 0, 0);
          an.rotation.set(R('an' + s) * D2R, 0, 0);
          var fb = Math.max(0, Math.min(TOE_MAX, R('tf' + s)));                     // a free (FK) foot: tf bends the toes up directly
          toes[s].rotation.set(-fb * D2R, 0, 0);
          shoeBend(s, fb);
        }
      });
      // muscle bulges follow the joints and activation colours ride the skin surface (anatomy3d.js)
      root.updateMatrixWorld(true);
      body.update(R, p, pre);
      if (ponyTail) hair(p, R);
    }

    function setRoles(acts) { body.roles(acts); }
    function worldOf(name) {
      root.updateMatrixWorld(true);
      var v = new V3();
      if (bone[name]) return v.setFromMatrixPosition(bone[name].matrixWorld);
      var rec = body.anchorOf(name);
      if (rec) { skeleton.update(); return body.surfacePoint(rec, v); }          // a point ON the skin over that muscle (rides bulges and joints)
      return v;
    }
    /** World position of a point given in a bone's local frame (lever arms, muscle origin/insertion lines). */
    function pointOf(boneName, x, y, z) {
      root.updateMatrixWorld(true);
      return new V3(x || 0, y || 0, z || 0).applyMatrix4(bone[boneName].matrixWorld);
    }
    function hold(side, obj, grip) {
      bone['hand' + side].add(obj); obj.position.set(0, -24, 4);
    }
    var props = [];
    function setVisible(v) { root.visible = !!v; props.forEach(function (x) { x.visible = !!v; }); }
    var fig = { root: root, bone: bone, muscles: muscles, body: body, gender: g, id: o.id || '', defaultPose: poseDefaults, apply: applyPose, roles: setRoles, world: worldOf, point: pointOf, hold: hold, spec: S, props: props, setVisible: setVisible,
      girdleOn: girdleOn,
      toes: toes, shoes: shoes, supports: supports, pony: ponyTail ? { mount: ponyMount, knot: pony, tail: ponyTail, tip: ponyTip, points: hairPoints } : null };
    applyPose({});
    return fig;
  };

  // ------------------------------------------------------------------ stage: renderer, camera, light, floor
  /**
   * T3.stage(host, {width, height, bg, grid}) -> stage. host is a DOM element (or null in node: pass
   * {headless: true} to skip the renderer and use the scene only). stage.cam holds az, el, dist, fov and
   * the look-at target; stage.render() draws; stage.project(vec3) gives pixel coordinates.
   */
  T3.stage = function (host, opts) {
    var o = opts || {}, W = o.width || 720, H = o.height || 1280;
    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(o.fov || 26, W / H, 20, 9000);
    scene.add(camera);
    var renderer = null;
    if (!o.headless) {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true, powerPreference: 'default' });
      renderer.setPixelRatio(1);
      renderer.setSize(W, H, false);
      renderer.setClearColor(new THREE.Color(o.bg || C.paper), 1);
      renderer.domElement.style.cssText = 'display:block;width:' + W + 'px;height:' + H + 'px';
      if (host) host.appendChild(renderer.domElement);
    }
    // light rides the camera so the cobalt light and shade planes read the same from any angle
    var key = new THREE.DirectionalLight(0xffffff, Math.PI * 0.95);
    key.position.set(-380, 620, 520); camera.add(key);
    key.target.position.set(0, 0, -1000); camera.add(key.target);
    scene.add(new THREE.AmbientLight(0xffffff, Math.PI * 0.20));

    var stage = { scene: scene, camera: camera, renderer: renderer, width: W, height: H, host: host, figures: [], world: new THREE.Group() };
    scene.add(stage.world);
    stage.cam = { az: 20, el: 10, dist: 2100, fov: o.fov || 26, tx: 0, ty: 380, tz: 0, roll: 0 };
    function floorTexture() {
      if (o.headless || typeof document === 'undefined') return null;
      var c = document.createElement('canvas'); c.width = c.height = 1024;
      var x = c.getContext('2d');
      x.clearRect(0, 0, 1024, 1024);
      x.strokeStyle = 'rgba(80,70,50,0.16)'; x.lineWidth = 2;
      for (var i = 0; i <= 20; i++) { var q = i * 1024 / 20; x.beginPath(); x.moveTo(q, 0); x.lineTo(q, 1024); x.stroke(); x.beginPath(); x.moveTo(0, q); x.lineTo(1024, q); x.stroke(); }
      x.globalCompositeOperation = 'destination-in';
      var rg = x.createRadialGradient(512, 512, 40, 512, 512, 512);
      rg.addColorStop(0, 'rgba(0,0,0,1)'); rg.addColorStop(0.55, 'rgba(0,0,0,0.75)'); rg.addColorStop(1, 'rgba(0,0,0,0)');
      x.fillStyle = rg; x.fillRect(0, 0, 1024, 1024);
      var t = new THREE.CanvasTexture(c); t.anisotropy = 4; return t;
    }
    function blobTexture() {
      if (o.headless || typeof document === 'undefined') return null;
      var c = document.createElement('canvas'); c.width = c.height = 256; var x = c.getContext('2d');
      var rg = x.createRadialGradient(128, 128, 4, 128, 128, 126);
      rg.addColorStop(0, 'rgba(40,40,70,0.34)'); rg.addColorStop(0.6, 'rgba(40,40,70,0.14)'); rg.addColorStop(1, 'rgba(40,40,70,0)');
      x.fillStyle = rg; x.fillRect(0, 0, 256, 256); return new THREE.CanvasTexture(c);
    }
    if (o.grid !== false) {
      var ft = floorTexture();
      if (ft) {
        var fl = new THREE.Mesh(new THREE.PlaneGeometry(o.floorSize || 3200, o.floorSize || 3200), new THREE.MeshBasicMaterial({ map: ft, transparent: true, depthWrite: false }));
        fl.rotation.x = -Math.PI / 2; fl.position.y = 0.2; scene.add(fl); stage.floor = fl;
      }
    }
    stage.blob = function (w, h, x, z, floorY) {
      var bt = blobTexture(); if (!bt) return null;
      var m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: bt, transparent: true, depthWrite: false }));
      m.rotation.x = -Math.PI / 2; m.position.set(x || 0, (floorY || 0) + 0.6, z || 0); stage.world.add(m); return m;
    };
    stage.tibi = function (opts2) { var f = T3.tibi(stage.world, opts2); stage.figures.push(f); return f; };
    stage.place = function () {
      var c = stage.cam, e = c.el * D2R, a = c.az * D2R;
      camera.fov = c.fov; camera.aspect = W / H; camera.updateProjectionMatrix();
      camera.position.set(c.tx + c.dist * Math.sin(a) * Math.cos(e), c.ty + c.dist * Math.sin(e), c.tz + c.dist * Math.cos(a) * Math.cos(e));
      camera.up.set(0, 1, 0);
      camera.lookAt(c.tx, c.ty, c.tz);
      if (c.roll) camera.rotateZ(c.roll * D2R);
      camera.updateMatrixWorld(true);
    };
    /*
     * Split screens: stage.views = [{rect: [x, top, w, h] (px), cam: {az, el, dist, fov, tx, ty, tz}, figs: [fig, ...]}, ...]
     * draws each view with its own camera into its rectangle of ONE canvas (scissor), showing only its own figures.
     * T3.bind feeds motion keys 'cam<i>.<k>' and 'view<i>.x|y|w|h' to view i, so a split can open on a spoken cue.
     * stage.project(v, i) projects into view i. Without views the stage renders as before.
     */
    stage.views = null;
    function placeCam(c, aspect) {
      var e = c.el * D2R, a = c.az * D2R;
      camera.fov = c.fov; camera.aspect = aspect; camera.updateProjectionMatrix();
      camera.position.set(c.tx + c.dist * Math.sin(a) * Math.cos(e), c.ty + c.dist * Math.sin(e), c.tz + c.dist * Math.cos(a) * Math.cos(e));
      camera.up.set(0, 1, 0); camera.lookAt(c.tx, c.ty, c.tz);
      if (c.roll) camera.rotateZ(c.roll * D2R);
      camera.updateMatrixWorld(true);
    }
    function prepareView(vw) {
      var r = vw.rect;
      placeCam(vw.cam, r[2] / Math.max(1, r[3]));
      vw.camera = vw.camera || new THREE.PerspectiveCamera();
      vw.camera.copy(camera, false); vw.camera.updateMatrixWorld(true);
    }
    stage.render = function (beforeDraw) {
      if (!stage.views) { stage.place(); if (beforeDraw) beforeDraw(); if (renderer) renderer.render(scene, camera); return; }
      // Pins need the current view cameras before scene visibility is set, not last frame's cameras.
      if (beforeDraw) { stage.views.forEach(prepareView); beforeDraw(); }
      var all = stage.figures, vis = all.map(function (f) { return f.root.visible; });
      if (renderer) { renderer.setScissorTest(false); renderer.clear(); renderer.setScissorTest(true); }
      stage.views.forEach(function (vw) {
        var r = vw.rect;
        prepareView(vw);
        if (!renderer || r[2] < 1 || r[3] < 1) return;
        all.forEach(function (f, i) { f.setVisible(vis[i] && vw.figs.indexOf(f) >= 0); });
        renderer.setViewport(r[0], H - r[1] - r[3], r[2], r[3]); renderer.setScissor(r[0], H - r[1] - r[3], r[2], r[3]);
        renderer.render(scene, camera);
      });
      all.forEach(function (f, i) { f.setVisible(vis[i]); });
      if (renderer) { renderer.setScissorTest(false); renderer.setViewport(0, 0, W, H); }
    };
    stage.project = function (v, view) {
      if (stage.views && view !== undefined) {
        var vw = stage.views[view], r = vw.rect, q = v.clone().project(vw.camera || camera);
        return { x: r[0] + (q.x * 0.5 + 0.5) * r[2], y: r[1] + (1 - (q.y * 0.5 + 0.5)) * r[3] };
      }
      var p = v.clone().project(camera);
      return { x: (p.x * 0.5 + 0.5) * W, y: (1 - (p.y * 0.5 + 0.5)) * H };
    };
    /**
     * stage.fit(points, {rect: [left, top, right, bottom] px | margin: 0.05}) keeps az/el/fov and solves the target and
     * distance so every world point lands inside rect (rule 13 from the geometry, not by eye). Returns the projected box.
     */
    stage.fit = function (all, fo) {
      fo = fo || {};
      var c = stage.cam, mg = fo.margin === undefined ? 0.05 : fo.margin, rect = fo.rect || [W * mg, H * mg, W * (1 - mg), H * (1 - mg)];
      var mid = new THREE.Box3().setFromPoints(all).getCenter(new THREE.Vector3()), q = new THREE.Vector3();
      c.tx = mid.x; c.ty = mid.y; c.tz = mid.z;
      stage.place();
      // Screen extremes depend on dist and target, the camera axes do not: keep the left/right/top/bottom-most point per depth slice.
      var ax = [0, 1, 2].map(function (i) { return new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, i); });
      var d0 = Infinity, d1 = -Infinity, NB = 128, keep = [];
      all.forEach(function (p) { var d = p.dot(ax[2]); if (d < d0) d0 = d; if (d > d1) d1 = d; });
      all.forEach(function (p) {
        var k = Math.min(NB - 1, Math.floor((p.dot(ax[2]) - d0) / ((d1 - d0) || 1) * NB)) * 4, r = p.dot(ax[0]), u = p.dot(ax[1]);
        if (!keep[k] || r < keep[k].dot(ax[0])) keep[k] = p;
        if (!keep[k + 1] || r > keep[k + 1].dot(ax[0])) keep[k + 1] = p;
        if (!keep[k + 2] || u < keep[k + 2].dot(ax[1])) keep[k + 2] = p;
        if (!keep[k + 3] || u > keep[k + 3].dot(ax[1])) keep[k + 3] = p;
      });
      var pts = keep.filter(Boolean);
      function extent() {
        stage.place();
        var b = [Infinity, Infinity, -Infinity, -Infinity];
        for (var i = 0; i < pts.length; i++) {
          q.copy(pts[i]).applyMatrix4(camera.matrixWorldInverse);
          if (q.z > -camera.near) return null;                  // behind the lens; the far plane is ignored so the search stays monotonic
          q.applyMatrix4(camera.projectionMatrix);
          var x = (q.x * 0.5 + 0.5) * W, y = (1 - (q.y * 0.5 + 0.5)) * H;
          if (x < b[0]) b[0] = x; if (y < b[1]) b[1] = y; if (x > b[2]) b[2] = x; if (y > b[3]) b[3] = y;
        }
        return b;
      }
      function fits(b) { return !!b && b[0] >= rect[0] && b[1] >= rect[1] && b[2] <= rect[2] && b[3] <= rect[3]; }
      function search() {
        var lo = 50, hi = 20000;
        for (var i = 0; i < 40; i++) { c.dist = (lo + hi) / 2; if (fits(extent())) hi = c.dist; else lo = c.dist; }
        c.dist = hi; return extent();
      }
      var b = search(), right = new THREE.Vector3(), up = new THREE.Vector3();
      for (var pass = 0; pass < 3 && b; pass++) {
        var dx = (rect[0] + rect[2] - b[0] - b[2]) / 2, dy = (rect[1] + rect[3] - b[1] - b[3]) / 2, wpp = 2 * c.dist * Math.tan(c.fov * D2R / 2) / H;
        right.setFromMatrixColumn(camera.matrixWorld, 0); up.setFromMatrixColumn(camera.matrixWorld, 1);
        c.tx += (-right.x * dx + up.x * dy) * wpp; c.ty += (-right.y * dx + up.y * dy) * wpp; c.tz += (-right.z * dx + up.z * dy) * wpp;
        b = search();
      }
      pts = all;                                                 // the slices are an approximation: confirm on every point
      for (var grow = 0; grow < 200 && !fits(b = extent()); grow++) c.dist *= 1.002;
      return { dist: c.dist, tx: c.tx, ty: c.ty, tz: c.tz, box: b, rect: rect };
    };
    return stage;
  };

  /** World points of what a figure shows now: every step-th posed skin vertex plus the boxes of visible rigid parts and props. */
  T3.framePoints = function (figs, step) {
    var out = [], v = new THREE.Vector3(), box = new THREE.Box3(), k = step || 6;
    function shown(o) { for (; o; o = o.parent) if (!o.visible) return false; return true; }
    function corners(o) {
      box.setFromObject(o);
      if (box.isEmpty()) return;
      for (var i = 0; i < 8; i++) out.push(new THREE.Vector3(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z));
    }
    (figs.length === undefined ? [figs] : figs).forEach(function (f) {
      var top = f.root; while (top.parent) top = top.parent;
      top.updateMatrixWorld(true);
      var skin = f.body && f.body.skin;
      if (skin && shown(skin)) {
        skin.skeleton.update();
        var pa = skin.geometry.getAttribute('position');
        for (var i = 0; i < pa.count; i += k) { v.fromBufferAttribute(pa, i); skin.applyBoneTransform(i, v); out.push(v.clone().applyMatrix4(skin.matrixWorld)); }
      }
      f.root.traverse(function (o) { if (o.isMesh && !o.isSkinnedMesh && o.parent && !/^inner/.test(o.parent.name || '') && shown(o)) corners(o); });
      f.props.forEach(function (p) { if (shown(p)) corners(p); });
    });
    return out;
  };

  /** Fit stage.cam to an exercise scene ({fig, motion, end}) over its whole motion, sampled at fo.samples times (default 48). */
  T3.fitScene = function (stage, sc, fo) {
    fo = fo || {};
    var n = fo.samples || 48, pts = [], t1 = sc.end === undefined ? 0 : sc.end;
    for (var i = 0; i < n; i++) { sc.fig.apply(sc.motion.at(n === 1 ? 0 : t1 * i / (n - 1))); Array.prototype.push.apply(pts, T3.framePoints(sc.fig, fo.step)); }
    sc.fig.apply(sc.motion.at(0));
    return stage.fit(pts, fo);
  };

  // ------------------------------------------------------------------ motion: parameters as pure functions of time
  var EASE = {
    none: function (p) { return p; },
    'sine.inOut': function (p) { return -(Math.cos(Math.PI * p) - 1) / 2; },
    'sine.out': function (p) { return Math.sin(p * Math.PI / 2); },
    'sine.in': function (p) { return 1 - Math.cos(p * Math.PI / 2); },
    'power1.inOut': function (p) { return p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2; },
    'power2.inOut': function (p) { return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; },
    'power2.out': function (p) { return 1 - Math.pow(1 - p, 3); },
    'power2.in': function (p) { return p * p * p; }
  };
  T3.ease = function (name) { return EASE[name] || EASE['power1.inOut']; };
  /**
   * T3.motion(): named numeric tracks. m.base(values) sets the starting values, m.to(at, dur, values, ease)
   * moves them, m.cycle(at, period, count, steps) repeats a rep. m.at(t) returns the full dictionary at film
   * time t. Nothing here reads a clock or GSAP, so seeking in any order gives the same frame.
   */
  T3.motion = function () {
    var m = { baseVals: {}, segs: {}, sealed: false };
    m.base = function (v) { for (var k in v) m.baseVals[k] = v[k]; return m; };
    m.to = function (at, dur, v, ease) {
      for (var k in v) { (m.segs[k] = m.segs[k] || []).push({ k: k, start: at, end: at + Math.max(dur, 1e-4), to: v[k], ease: EASE[ease || 'power1.inOut'] || EASE['power1.inOut'], from: null }); }
      m.sealed = false; return at + dur;
    };
    /** steps: [{at: fraction of period (the move ENDS here), v: {...}, ease}] , each move starts where the previous ended. */
    m.cycle = function (at, period, count, steps) {
      for (var c = 0; c < count; c++) {
        var prev = 0;
        steps.forEach(function (st) {
          var s0 = at + c * period + prev * period, d = (st.at - prev) * period;
          if (st.v) m.to(s0, d, st.v, st.ease);
          if (st.also) st.also.forEach(function (al) { m.to(s0, d, al.v, al.ease); });   // parallel tracks with their own ease (curved paths)
          prev = st.at;
        });
      }
      return at + count * period;
    };
    function seal() {
      Object.keys(m.segs).forEach(function (k) {
        var list = m.segs[k].sort(function (a, b) { return a.start - b.start; });
        list.forEach(function (sg, i) { sg.from = evalKey(k, sg.start, i); });
      });
      m.sealed = true;
    }
    function evalKey(k, t, upto) {
      var list = m.segs[k] || [], v = m.baseVals[k], n = upto === undefined ? list.length : upto;
      if (v === undefined) v = DEFAULT_POSE[k.replace(/^[^.]*\./, '')] !== undefined ? DEFAULT_POSE[k.replace(/^[^.]*\./, '')] : 0;   // undeclared key: the rig default, never NaN
      for (var i = 0; i < n; i++) {
        var sg = list[i];
        if (t < sg.start) break;
        var from = sg.from === null ? v : sg.from;
        if (t >= sg.end) v = sg.to; else v = from + (sg.to - from) * sg.ease((t - sg.start) / (sg.end - sg.start));
      }
      return v;
    }
    /**
     * An exact path: fn(p) -> {key: value} is evaluated every frame at eased progress p (0..1) and holds its end value
     * until the next path starts. Use it for coupled keys (an elbow arc, a wrist stacked over it) instead of sampling
     * a curve into short linear moves, which gives visible velocity steps. Keys must have a base value.
     */
    m.paths = [];
    m.path = function (at, dur, fn, ease) {
      m.paths.push({ start: at, end: at + Math.max(dur, 1e-4), fn: fn, ease: EASE[ease || 'power1.inOut'] || EASE['power1.inOut'] });
      m.paths.sort(function (a, b) { return a.start - b.start; });
      return at + dur;
    };
    m.at = function (t) {
      if (!m.sealed) seal();
      var out = {};
      // where this pose came from, so secondary motion (the ponytail) can look back along the same pure function of time.
      // Not enumerable: key loops, merges and JSON never see it; a copied dictionary simply has no history.
      Object.defineProperty(out, '__src', { value: { motion: m, t: t }, enumerable: false });
      for (var k in m.baseVals) out[k] = m.baseVals[k];
      for (var k2 in m.segs) out[k2] = evalKey(k2, t);
      // Every started path applies in start order; a later path overrides only the keys it sets. (Applying just the latest
      // path froze a second figure whose path had started earlier: two figures can now run paths side by side.)
      // A path's start/end values are cached so a finished path costs one dictionary copy, not a function call.
      for (var i = 0; i < m.paths.length; i++) {
        var pa = m.paths[i];
        if (pa.start > t) break;
        var vals;
        if (t >= pa.end) vals = pa.endVals || (pa.endVals = pa.fn(pa.ease(1)));
        else vals = pa.fn(pa.ease((t - pa.start) / (pa.end - pa.start)));
        for (var k3 in vals) out[k3] = vals[k3];
      }
      return out;
    };
    return m;
  };

  /**
   * Bind a stage and a motion to the film timeline. One linear tween spans the film; its setter runs
   * on every seek (property writes are not suppressed, callbacks are) and draws the frame.
   * onFrame(vals, t) updates overlays and visibility after camera placement, before the frame is drawn.
   */
  T3.bind = function (tl, stage, motion, duration, onFrame) {
    var cam = stage.cam;
    var driver = {};
    var last = -1;
    function draw(t) {
      var v = motion.at(t);
      stage.figures.forEach(function (f) { f.apply(v); });
      ['az', 'el', 'dist', 'fov', 'tx', 'ty', 'tz', 'roll'].forEach(function (k) { if (v['cam.' + k] !== undefined) cam[k] = v['cam.' + k]; });
      (stage.views || []).forEach(function (vw, i) {
        ['az', 'el', 'dist', 'fov', 'tx', 'ty', 'tz', 'roll'].forEach(function (k) { if (v['cam' + i + '.' + k] !== undefined) vw.cam[k] = v['cam' + i + '.' + k]; });
        ['x', 'y', 'w', 'h'].forEach(function (k, j) { if (v['view' + i + '.' + k] !== undefined) vw.rect[j] = Math.round(v['view' + i + '.' + k]); });
      });
      stage.render(onFrame ? function () { onFrame(v, t); } : null);
    }
    Object.defineProperty(driver, 't', { get: function () { return last; }, set: function (t) { last = t; draw(t); } });
    draw(0);
    tl.fromTo(driver, { t: 0 }, { t: duration, duration: duration, ease: 'none', immediateRender: false }, 0);
    return draw;
  };

  // ------------------------------------------------------------------ equipment
  var EQ = T3.equipment = {};
  /** Dumbbell with the handle along local x, centred on the handle. s scales it. */
  EQ.dumbbell = function (s) {
    var k = s || 1, g = new THREE.Group();
    var h = new THREE.Mesh(new THREE.CylinderGeometry(5.5 * k, 5.5 * k, 74 * k, 14), mat(C.steel)); h.rotation.z = Math.PI / 2; g.add(h);
    [-1, 1].forEach(function (sd) {
      var plate = new THREE.Mesh(new THREE.CylinderGeometry(25 * k, 25 * k, 15 * k, 28), mat(C.plate)); plate.rotation.z = Math.PI / 2; plate.position.x = sd * 44 * k; g.add(plate);
      var face = new THREE.Mesh(new THREE.CylinderGeometry(17 * k, 17 * k, 2 * k, 24), mat(C.plateFace)); face.rotation.z = Math.PI / 2; face.position.x = sd * 52 * k; g.add(face);
    });
    return g;
  };
  /** Barbell with the bar along local x, centred. o: {half (half length), plate (radius), plates (count per side)}. */
  EQ.barbell = function (o) {
    o = o || {};
    var half = o.half || 330, pr = o.plate || 62, n = o.plates || 2, g = new THREE.Group();
    var bar = new THREE.Mesh(new THREE.CylinderGeometry(6, 6, half * 2, 14), mat(C.steel)); bar.rotation.z = Math.PI / 2; g.add(bar);
    [-1, 1].forEach(function (sd) {
      var sleeve = new THREE.Mesh(new THREE.CylinderGeometry(8.5, 8.5, half * 0.36, 14), mat(C.steelShade)); sleeve.rotation.z = Math.PI / 2; sleeve.position.x = sd * half * 0.8; g.add(sleeve);
      for (var i = 0; i < n; i++) {
        var r = pr * (1 - 0.16 * i), x = sd * (half * 0.66 + 10 + i * 17);
        var plate = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 15, 32), mat(C.plate)); plate.rotation.z = Math.PI / 2; plate.position.x = x; g.add(plate);
        var face = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.62, r * 0.62, 16, 28), mat(C.plateFace)); face.rotation.z = Math.PI / 2; face.position.x = x; g.add(face);
      }
      var collar = new THREE.Mesh(new THREE.CylinderGeometry(11, 11, 10, 16), mat(C.steel)); collar.rotation.z = Math.PI / 2; collar.position.x = sd * (half * 0.66 - 2); g.add(collar);
    });
    return g;
  };
  /** A thin upright panel (the knee barrier of a restricted squat). o: {x, z, w, h, color, opacity}; faces +z. */
  EQ.board = function (o) {
    var g = new THREE.Group(), w = o.w || 260, h = o.h || 270;
    var m = mat(o.color || C.pad, { transparent: true, opacity: o.opacity === undefined ? 0.55 : o.opacity, depthWrite: false });
    var panel = new THREE.Mesh(new THREE.BoxGeometry(w, h, 8), m); panel.position.y = h / 2; g.add(panel);
    var edge = new THREE.Mesh(new THREE.BoxGeometry(w + 6, 10, 12), mat(C.steelShade)); edge.position.y = h; g.add(edge);
    [-1, 1].forEach(function (sd) { var ft = new THREE.Mesh(new THREE.BoxGeometry(14, 10, 70), mat(C.steelShade)); ft.position.set(sd * (w / 2 - 10), 5, 0); g.add(ft); });
    g.position.set(o.x || 0, 0, o.z || 0); g.rotation.y = (o.yaw || 0) * D2R;
    return g;
  };
  /** A pad on legs. o: {x, z, y (pad top), w, l, floor, rot} - centred on x,z, length along z unless yaw is set. */
  EQ.bench = function (o) {
    var g = new THREE.Group(), w = o.w || 130, l = o.l || 520, th = 34, top = o.y;
    var pad = new THREE.Mesh(new THREE.BoxGeometry(w, th, l, 1, 1, 1), mat(C.pad)); pad.position.y = top - th / 2; g.add(pad);
    var cap = new THREE.Mesh(new THREE.BoxGeometry(w - 14, 6, l - 14), mat(C.padTop)); cap.position.y = top - 2; g.add(cap);
    var steel = mat(C.steelShade);
    [-1, 1].forEach(function (sd) {
      var leg = new THREE.Mesh(new THREE.BoxGeometry(w - 30, top - th, 12), steel); leg.position.set(0, (top - th) / 2, sd * (l / 2 - 50)); g.add(leg);
      var foot = new THREE.Mesh(new THREE.BoxGeometry(w + 40, 10, 16), steel); foot.position.set(0, 5, sd * (l / 2 - 50)); g.add(foot);
    });
    var rail = new THREE.Mesh(new THREE.BoxGeometry(10, 10, l - 100), steel); rail.position.set(0, top - th - 20, 0); g.add(rail);
    g.position.set(o.x || 0, 0, o.z || 0); g.rotation.y = (o.yaw || 0) * D2R;
    return g;
  };

  // ------------------------------------------------------------------ analysis helpers (used by scripts/rig3d-check.js and the lab)
  /** Lowest world y of the soles and the lowest back-of-body point; used to check ground contact without rendering. */
  T3.contacts = function (fig) {
    fig.root.updateMatrixWorld(true);
    var out = {};
    ['L', 'R'].forEach(function (s) {
      var a = fig.bone['an' + s]; a.updateWorldMatrix(true, false);
      var heel = new V3(0, HEEL.y, HEEL.z).applyMatrix4(a.matrixWorld), ball = new V3(0, BALL.y, BALL.z).applyMatrix4(a.matrixWorld);
      var tip = fig.toes ? new V3(0, TIP.y - BALL.y, TIP.z - BALL.z).applyMatrix4(fig.toes[s].matrixWorld) : ball;
      out['sole' + s] = Math.min(heel.y, ball.y, tip.y);
      out['heel' + s] = heel.y;
      out['ball' + s] = ball.toArray();
      out['tip' + s] = tip.toArray();
      out['ankle' + s] = new V3().setFromMatrixPosition(a.matrixWorld).toArray();
    });
    return out;
  };

})(typeof window !== 'undefined' ? window : globalThis);
