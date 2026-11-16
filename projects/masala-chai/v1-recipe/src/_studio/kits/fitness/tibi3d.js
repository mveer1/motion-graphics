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
  var T3 = F.t3d = { version: '0.2.0' };

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
   *   fig.apply(p)  pose from a flat dictionary of numbers (names below), see DEFAULT_POSE
   *   fig.roles(acts)  {muscleKey: 1|2|3} fixes which muscles can light up and in which role colour
   *   fig.hold(side, obj3d)  puts equipment in a hand
   *   fig.world(name) world position of a named anchor ('wristL', 'chest', 'biceps@L', ...)
   */
  var DEFAULT_POSE = {
    x: 0, y: 370, z: 0, yaw: 0, pitch: 0, roll: 0,
    lean: 0, twist: 0, bend: 0, neckF: 0, headF: 0, headY: 0,
    // arms, per side L/R: elevation from hanging (0 = at the side, 90 = horizontal), plane (0 = out to the side, 90 = forward),
    // axial rotation, elbow flexion, wrist flexion, forearm pronation, IK switch, wrist offset from the shoulder in world units, elbow pole
    // ikcS = 1 reads hx/hy/hz and px/py/pz in the CHEST frame instead of the world (a bar on the back or across the hips rides the trunk)
    shL: 6, plL: 70, rtL: 0, elL: 6, wrL: 0, prL: 0, gaxL: 0, gayL: 0, gazL: 0, ikL: 0, ikcL: 0, hxL: 0, hyL: -230, hzL: 0, pxL: 1, pyL: 0, pzL: 0,
    shR: 6, plR: 70, rtR: 0, elR: 6, wrR: 0, prR: 0, gaxR: 0, gayR: 0, gazR: 0, ikR: 0, ikcR: 0, hxR: 0, hyR: -230, hzR: 0, pxR: -1, pyR: 0, pzR: 0,
    // legs, per side: IK to a planted foot (ikS = 1: foot sole target fxS, fyS (lift), fzS and yaw fyawS in the world), else FK angles.
    // hlS = heel lift in degrees (calf raise): the shoe hinges at the ball, which stays where fx/fz put it; the toe box stays flat.
    ikLegL: 1, fxL: 40, fyL: 0, fzL: 0, fyawL: 0, hlL: 0, hpL: 0, haL: 0, knL: 0, anL: 0, kfL: 8,
    ikLegR: 1, fxR: -40, fyR: 0, fzR: 0, fyawR: 0, hlR: 0, hpR: 0, haR: 0, knR: 0, anR: 0, kfR: 8
  };
  /** Ball of the foot in the ankle frame: the hinge of a heel lift and the contact point of the toe box. */
  var BALL = { y: -26, z: 62 };
  T3.BALL = BALL;
  /** Ankle offset (up, forward along the foot) that keeps the ball planted for a heel lift of a degrees. */
  T3.heelLift = function (deg) {
    var a = deg * D2R;
    return { up: -BALL.y * Math.cos(a) + BALL.z * Math.sin(a) + BALL.y, fwd: BALL.z * (1 - Math.cos(a)) - BALL.y * Math.sin(a) };
  };
  T3.DEFAULT_POSE = DEFAULT_POSE;
  T3.SPEC = SPEC;

  T3.tibi = function (parent, opts) {
    var o = opts || {}, g = o.gender === 'f' ? 'f' : 'm', S = SPEC[g], pre = o.id ? o.id + '.' : '';
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
    var I = function (n) { return bone[n].userData.index; };
    if (!T3.anatomy) throw new Error('kits/fitness/tibi3d.js needs kits/fitness/anatomy3d.js loaded after it (before exercises3d.js)');
    // Bind pose is an A-pose (arms 26 deg, legs 4 deg out) so the ONE skin never fuses at the armpit or crotch. The inverses are captured
    // while the limbs are out; every frame then poses the bones absolutely, so the rest pose of the bones is still the straight one.
    ['L', 'R'].forEach(function (s) {
      var sg = s === 'L' ? 1 : -1;
      bone['sh' + s].rotation.z = sg * T3.anatomy.BIND.arm * D2R; bone['th' + s].rotation.z = sg * T3.anatomy.BIND.leg * D2R;
    });
    root.updateMatrixWorld(true);
    var skeleton = new THREE.Skeleton(bones);
    var rootInv = new M4().copy(root.matrixWorld).invert(), boneBind = {}, boneIndex = {};
    bones.forEach(function (b, i) { boneBind[b.name] = new M4().multiplyMatrices(rootInv, b.matrixWorld); boneIndex[b.name] = i; });
    ['L', 'R'].forEach(function (s) { bone['sh' + s].rotation.z = 0; bone['th' + s].rotation.z = 0; });
    root.updateMatrixWorld(true);
    function bp(n) { var e = boneBind[n].elements; return [e[12], e[13], e[14]]; }
    var joints = { shL: bp('shL'), shR: bp('shR'), hipL: bp('thL'), hipR: bp('thR') };

    // ---- the body: ONE continuous skin (torso, limbs, neck, head, hands) whose muscles are part of its surface. See anatomy3d.js.
    var body = T3.anatomy.attach({ root: root, bone: bone, bones: bones, skeleton: skeleton, S: S, g: g, joints: joints, boneBind: boneBind, boneIndex: boneIndex });
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
    var pony = null;
    if (g === 'f') {
      pony = new THREE.Group(); pony.position.set(0, 74, -34); head.add(pony);
      ell(pony, C.hair, 0, -4, -10, 15, 16, 15);
      ell(pony, C.hair, 0, -44, -22, 14, 46, 13, [-12, 0, 0]);
      ell(pony, C.hairLight, 0, -30, -16, 7, 26, 6, [-12, 0, 0]);
      ell(pony, C.spark, 0, 6, -6, 9, 6, 9);
    }
    var toes = {};
    ['L', 'R'].forEach(function (s) {
      // shoe in two pieces hinged at the ball (a heel lift bends it there; flat, it reads as one shoe)
      var foot = bone['an' + s];
      ell(foot, C.shoe, 0, -11, 22, 23, 15, 48);
      ell(foot, C.sole, 0, -22, 22, 24, 4.5, 49);
      ell(foot, C.shoe, 0, 4, -10, 20, 20, 20);
      var toe = new THREE.Group(); toe.position.set(0, BALL.y, BALL.z); foot.add(toe);
      ell(toe, C.shoe, 0, 13, 8, 22.5, 14, 27);
      ell(toe, C.sole, 0, 4, 8, 23.5, 4.5, 28);
      toes[s] = toe;
    });

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
    function R0(k) { var v = curPose[pre + k]; return v === undefined ? DEFAULT_POSE[k] : v; }

    function applyPose(pIn) {
      var p = pIn; curPose = p;
      var R = R0;
      root.position.set(R('x'), R('y'), R('z'));
      root.rotation.set(R('pitch') * D2R, R('yaw') * D2R, R('roll') * D2R, 'YXZ');
      // trunk: spread over the lumbar and thoracic joints
      var lean = R('lean') * D2R, tw = R('twist') * D2R, bd = R('bend') * D2R;
      bone.spine.rotation.set(lean * 0.4, tw * 0.4, bd * 0.4);
      bone.chest.rotation.set(lean * 0.6, tw * 0.6, bd * 0.6);
      bone.neck.rotation.set(R('neckF') * D2R * 0.5, R('headY') * D2R * 0.4, 0);
      bone.head.rotation.set((R('neckF') * 0.5 + R('headF')) * D2R, R('headY') * D2R * 0.6, 0);
      root.updateMatrixWorld(true);
      // arms
      ['L', 'R'].forEach(function (s) {
        var sg = s === 'L' ? 1 : -1, sh = bone['sh' + s], el = bone['el' + s], hd = bone['hand' + s];
        if (R('ik' + s) > 0.5) {
          bone.chest.updateWorldMatrix(true, false);
          sh.updateWorldMatrix(true, false);
          shoulderW.setFromMatrixPosition(sh.matrixWorld);
          var inv = tmpQ.setFromRotationMatrix(bone.chest.matrixWorld).invert();
          if (R('ikc' + s) > 0.5) inv.identity();                         // targets already in the chest frame
          var t = new V3(R('hx' + s), R('hy' + s), R('hz' + s)).applyQuaternion(inv);
          var pol = new V3(R('px' + s), R('py' + s), R('pz' + s)).applyQuaternion(inv);
          var flex = ikLimb(bone.chest, sh, el, 134, 106, t, pol, 1);
          el.rotation.set(-flex, 0, 0);
        } else {
          var th = R('sh' + s) * D2R, pl = R('pl' + s) * D2R;
          var dir = new V3(Math.sin(th) * Math.cos(pl), -Math.cos(th), Math.sin(th) * Math.sin(pl));
          var swing = new Q().setFromUnitVectors(new V3(0, -1, 0), dir);
          var twist = new Q().setFromAxisAngle(new V3(0, 1, 0), R('rt' + s) * D2R);
          swing.multiply(twist);
          if (s === 'R') { swing.set(swing.x, -swing.y, -swing.z, swing.w); }   // mirror across the sagittal plane
          sh.quaternion.copy(swing);
          el.rotation.set(-R('el' + s) * D2R, 0, 0);
        }
        var pr = R('pr' + s) * D2R * (s === 'L' ? 1 : -1);
        var gx = R('gax' + s), gy = R('gay' + s), gz = R('gaz' + s);
        if (gx * gx + gy * gy + gz * gz > 1e-6) {
          // roll the hand about the forearm so a held bar's axis lines up with a world direction
          el.updateWorldMatrix(true, false);
          var qe = new Q().setFromRotationMatrix(el.matrixWorld).invert();
          var tl = new V3(gx, gy, gz).applyQuaternion(qe);
          pr = Math.atan2(-tl.z, tl.x);
          if (pr > Math.PI / 2) pr -= Math.PI; else if (pr < -Math.PI / 2) pr += Math.PI;
        }
        hd.rotation.set(-R('wr' + s) * D2R, pr, 0);
      });
      root.updateMatrixWorld(true);
      // legs: IK to planted feet (world), else FK
      ['L', 'R'].forEach(function (s) {
        var sg = s === 'L' ? 1 : -1, th = bone['th' + s], kn = bone['kn' + s], an = bone['an' + s];
        if (R('ikLeg' + s) > 0.5) {
          bone.hips.updateWorldMatrix(true, false);
          var invH = new M4().copy(bone.hips.matrixWorld).invert();
          var hl = R('hl' + s), lift = T3.heelLift(hl), yw = R('fyaw' + s) * D2R;
          var target = new V3(R('fx' + s) + lift.fwd * Math.sin(yw), R('fy' + s) + 26 + lift.up, R('fz' + s) + lift.fwd * Math.cos(yw)).applyMatrix4(invH);
          var origin = th.position.clone();
          var rel = target.sub(origin);
          var kf = R('kf' + s) * D2R, pole = new V3(Math.sin(kf) * sg, 0, Math.cos(kf));
          var kflex = ikLimb(bone.hips, th, kn, 178, 166, rel, pole, -1);
          kn.rotation.set(kflex, 0, 0);
          kn.updateWorldMatrix(true, false);
          var qShin = new Q().setFromRotationMatrix(kn.matrixWorld);
          var qFoot = new Q().setFromAxisAngle(new V3(0, 1, 0), R('fyaw' + s) * D2R);
          an.quaternion.copy(qShin.invert().multiply(qFoot));
          an.quaternion.multiply(tmpQ2.setFromAxisAngle(new V3(1, 0, 0), (R('an' + s) + hl) * D2R));
          toes[s].rotation.set(-hl * D2R, 0, 0);                              // the toe box stays flat on the floor
        } else {
          th.rotation.set(-R('hp' + s) * D2R, 0, sg * R('ha' + s) * D2R, 'XYZ');
          kn.rotation.set(R('kn' + s) * D2R, 0, 0);
          an.rotation.set(R('an' + s) * D2R, 0, 0);
        }
      });
      // muscle bulges follow the joints and activation colours ride the skin surface (anatomy3d.js)
      root.updateMatrixWorld(true);
      body.update(R, p, pre);
      if (pony) pony.rotation.set(-0.25 * (R('lean') * D2R) - 0.06, 0, 0);
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
    var fig = { root: root, bone: bone, muscles: muscles, body: body, gender: g, id: o.id || '', apply: applyPose, roles: setRoles, world: worldOf, point: pointOf, hold: hold, spec: S, props: props, setVisible: setVisible };
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
    stage.render = function () {
      if (!stage.views) { stage.place(); if (renderer) renderer.render(scene, camera); return; }
      var all = stage.figures, vis = all.map(function (f) { return f.root.visible; });
      if (renderer) { renderer.setScissorTest(false); renderer.clear(); renderer.setScissorTest(true); }
      stage.views.forEach(function (vw) {
        var r = vw.rect;
        placeCam(vw.cam, r[2] / Math.max(1, r[3]));
        vw.camera = vw.camera || camera.clone();
        vw.camera.copy(camera); vw.camera.updateMatrixWorld(true);
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
    return stage;
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
   * onFrame(vals, t) lets the composition move its own overlays from the same values.
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
      stage.render();
      if (onFrame) onFrame(v, t);
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
      var heel = new V3(0, -26, -26).applyMatrix4(a.matrixWorld), ball = new V3(0, BALL.y, BALL.z).applyMatrix4(a.matrixWorld);
      out['sole' + s] = Math.min(heel.y, ball.y);
      out['heel' + s] = heel.y;
      out['ball' + s] = ball.toArray();
      out['ankle' + s] = new V3().setFromMatrixPosition(a.matrixWorld).toArray();
    });
    return out;
  };

})(typeof window !== 'undefined' ? window : globalThis);
