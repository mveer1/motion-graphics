#!/usr/bin/env node
/*
 * anatomy3d-check.js: anatomical acceptance tests for the 3D Tibi (no browser, no render: node and the vendored three.js).
 *
 *   node scripts/anatomy3d-check.js [--gender m|f|both] [--profile legacy|distance] [--json]
 *
 * The rules come from the "detached muscle" review (2026-11-13): a muscle is part of the body, never a sticker. Each test is a
 * way the OLD rig failed (rigid ellipsoids parented to bones) or a way this one could:
 *   skin         one closed, single-component surface; non-manifold edges reported separately
 *   protrusion   every internal muscle, tendon and bone vertex lies inside the skin envelope (skin SDF <= -inset)
 *   external     no mesh that looks like a muscle hangs on a bone outside the skin or the hidden inner group
 *   coverage     every superficial muscle owns enough skin vertices to be seen and lit; deep ones are exempt
 *   gradient     a muscle's tint falls off smoothly across the surface (no hard-edged patch)
 *   layers       along a ray through each cut window the layers come in anatomical order (superficial, deep, bone)
 *   registration highlights stay on their anatomy: the centroid of a muscle's skin region stays within tolerance of its
 *                bone-local anchor through squat, curl, raise and hip-thrust poses (no drift under deformation)
 *   deformation  no triangle collapses or explodes in the poses above at the joints (area ratio vs the bind pose)
 *   state        the visual language keeps external (cobalt), active (role colours) and internal (rosewood/ivory) apart
 *   silhouette   the actual posed shoulder roof and neutral arm/hand clearance, not just muscle primitives
 * Exit 1 on any failure. Numbers are rig units (head = 100).
 */
'use strict';
const path = require('path');
const root = path.join(__dirname, '..', 'src', 'studio') + path.sep;
global.window = global;
const warn = console.warn; console.warn = () => {};
global.THREE = require(root + 'vendor/three.min.js');
console.warn = warn;
global.Studio = {};
require(root + 'kits/fitness/brand.js');
require(root + 'kits/fitness/tibi3d.js');
require(root + 'kits/fitness/anatomy3d.js');
require(root + 'kits/fitness/exercises3d.js');
const T3 = Studio.kit.fitness.t3d, A = T3.anatomy, D2R = Math.PI / 180;

const args = process.argv.slice(2);
const opt = { gender: 'both', profileSampling: 'distance', json: false };
for (let i = 0; i < args.length; i++) { if (args[i] === '--gender') opt.gender = args[++i]; else if (args[i] === '--profile') opt.profileSampling = args[++i]; else if (args[i] === '--json') opt.json = true; }
const genders = opt.gender === 'both' ? ['m', 'f'] : [opt.gender];

function shoulderContour(positions, indices, spec, sign) {
  const start = spec.shx * 0.6, step = (spec.shx * 0.4 + 38 * spec.mscale) / 50;
  const top = new Float64Array(51).fill(-Infinity);
  for (let t = 0; t < indices.length; t += 3) for (let edge = 0; edge < 3; edge++) {
    const a = indices[t + edge] * 3, b = indices[t + (edge + 1) % 3] * 3;
    const xa = positions[a] * sign, xb = positions[b] * sign;
    const ya = positions[a + 1], yb = positions[b + 1];
    if (Math.max(ya, yb) < spec.shy - 100 || Math.min(ya, yb) > spec.shy + 50) continue;
    const first = Math.max(0, Math.ceil((Math.min(xa, xb) - start) / step));
    const last = Math.min(50, Math.floor((Math.max(xa, xb) - start) / step));
    for (let i = first; i <= last; i++) {
      const u = Math.abs(xb - xa) < 1e-10 ? 0 : (start + i * step - xa) / (xb - xa);
      const y = Math.abs(xb - xa) < 1e-10 ? Math.max(ya, yb) : ya + u * (yb - ya);
      if (y >= spec.shy - 100 && y <= spec.shy + 50) top[i] = Math.max(top[i], y);
    }
  }
  let low = Infinity, rise = 0, samples = 0;
  for (const height of top) if (Number.isFinite(height)) {
    low = Math.min(low, height); rise = Math.max(rise, height - low); samples++;
  }
  return { crestRise: rise, samples };
}

function horizontalSilhouette(positions, indices, y) {
  const intervals = [];
  for (let t = 0; t < indices.length; t += 3) {
    let min = Infinity, max = -Infinity;
    for (let edge = 0; edge < 3; edge++) {
      const a = indices[t + edge] * 3, b = indices[t + (edge + 1) % 3] * 3;
      const da = positions[a + 1] - y, db = positions[b + 1] - y;
      if (da * db > 0) continue;
      if (Math.abs(da - db) < 1e-10) {
        if (Math.abs(da) < 1e-10) {
          min = Math.min(min, positions[a], positions[b]);
          max = Math.max(max, positions[a], positions[b]);
        }
      } else {
        const x = positions[a] + da / (da - db) * (positions[b] - positions[a]);
        min = Math.min(min, x); max = Math.max(max, x);
      }
    }
    if (Number.isFinite(min)) intervals.push([min, max]);
  }
  intervals.sort((a, b) => a[0] - b[0]);
  const merged = [];
  for (const interval of intervals) {
    const tail = merged[merged.length - 1];
    if (tail && interval[0] <= tail[1] + 1e-3) tail[1] = Math.max(tail[1], interval[1]);
    else merged.push(interval.slice());
  }
  return merged;
}

/*
 * Known limits closed in anatomy 1.4.0 (2026-11-23). Each measure failed on the 1.3.0 body (numbers in the report under
 * prompts/state/known-limits/). They complement looking at the frames; they do not replace it.
 *   gluteProfile    posterior depth of the buttock row by row (neutral): a ball overhangs the thigh in a sudden drop below its peak
 *   gluteSurface    neighbour-normal angles in the gluteal-hip region: sub-cell-thin sheet edges meshed as jagged creases and dents
 *   effortShape     share of a superficial muscle's lit skin at >= 90% of its peak effort weight: a flat block or disc vs a belly gradient
 *   stabiliserRamp  role 1 (pale cobalt) never passes through a colour paler than its own (the pale block on the abs)
 *   clothTint       under the garment effort is one straight ramp to a subdued tint (k = share of the way to the role colour)
 *   cutInterior     rays through a superficial cut must reach the deep layer, never the inside of the cut muscle's own shell; scanlines
 *                   across the glute window must not cross the gluteus maximus twice (a coral loop around a hole) at open 1.3-1.8
 *   femaleDeltoid   (f) deltoid overhang over the upper arm and lateral reach in the neutral front silhouette (broad, square cap)
 *   abductionRidge  steepest rise of the top contour from the trapezius onto the abducted arm (the ridge at 90 degrees)
 *   jointCrush      1st-percentile share of rest distance to the joint kept by inner-fold skin at elbow 150, knee 150, hip 120 (LBS crush);
 *                   cross-body and overhead are reported here (their chest/arm pair no longer exists since the girdle, 1.6.0); the
 *                   rig-independent shoulderCrush gate (girdleGates) covers them. Refined squat stretch limit is 4.0 (legacy 4.5).
 */
function knownLimitGates(fig, body, data, res, fail, posedRoot, idx) {
  const n = data.n, spec = fig.spec, V3 = THREE.Vector3;
  fig.roles({});
  // ---- 1. gluteus maximus
  {
    const positions = posedRoot({}), rows = {};
    for (let i = 0; i < n; i++) {
      const x = positions[i * 3], y = positions[i * 3 + 1], z = positions[i * 3 + 2];
      if (Math.abs(x) < 8 || Math.abs(x) > 70 || y > A.CLOTH.waist || y < -120) continue;
      const key = (x > 0 ? 'L' : 'R') + Math.round(y / 5);
      if (!(key in rows) || rows[key] < -z) rows[key] = -z;
    }
    res.stats.gluteProfile = {};
    for (const side of ['L', 'R']) {
      const ys = [];
      for (let b = Math.floor(A.CLOTH.waist / 5); b >= -24; b--) if ((side + b) in rows) ys.push([b * 5, rows[side + b]]);
      let peak = 0;
      ys.forEach((r, i) => { if (r[1] > ys[peak][1]) peak = i; });
      let drop = 0, at = null;
      for (let i = peak + 1; i < ys.length; i++) { const d = ys[i - 1][1] - ys[i][1]; if (d > drop) { drop = d; at = ys[i][0]; } }
      res.stats.gluteProfile[side] = { peakDepth: +ys[peak][1].toFixed(2), peakAt: ys[peak][0], maxDropPer5: +drop.toFixed(2), at };
      if (drop > 8) fail(`glute ${side}: the buttock drops ${drop.toFixed(2)} units in 5 below its peak (y=${at}; limit 8): a ball overhanging the thigh`);
    }
  }
  // ---- 1b. gluteal-hip surface roughness (rest mesh normals, bind space): sub-cell-thin sheets mesh as jagged creases
  {
    const P = data.mesh.pos, geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); geo.setIndex(Array.from(data.mesh.idx)); geo.computeVertexNormals();
    const N = geo.getAttribute('normal').array, nb = new Array(n);
    for (let i = 0; i < n; i++) nb[i] = [];
    for (let t = 0; t < idx.length; t += 3) for (let e = 0; e < 3; e++) nb[idx[t + e]].push(idx[t + (e + 1) % 3]);
    const angles = [];
    for (let v = 0; v < n; v++) {
      const x = Math.abs(P[v * 3]), y = P[v * 3 + 1], z = P[v * 3 + 2];
      if (!(x < 85 && y < A.CLOTH.waist - 4 && y > -95 && (z < -5 || x > 45))) continue;
      let worst = 0;
      for (const u of nb[v]) {
        const c = N[v * 3] * N[u * 3] + N[v * 3 + 1] * N[u * 3 + 1] + N[v * 3 + 2] * N[u * 3 + 2];
        worst = Math.max(worst, Math.acos(Math.max(-1, Math.min(1, c))) / D2R);
      }
      angles.push(worst);
    }
    geo.dispose();
    angles.sort((a, b) => a - b);
    const p999 = angles[Math.floor(0.999 * angles.length)], sharp = angles.filter(a => a > 30).length / angles.length;
    res.stats.gluteSurface = { vertices: angles.length, p999NeighbourAngle: +p999.toFixed(1), shareOver30: +sharp.toFixed(4) };
    if (p999 > 40 || sharp > 0.015) fail(`gluteal-hip surface is crumpled: 99.9th percentile neighbour-normal angle ${p999.toFixed(1)} deg (limit 40), ${(100 * sharp).toFixed(2)}% of vertices over 30 deg (limit 1.5%)`);
  }
  // ---- 2a. effort follows the muscle shape
  {
    let worst = 0, who = '';
    const named = {};
    body.muscles.forEach(r => {
      if (r.layer !== 1 || r.vi.length < 40) return;
      let max = 0, lit = 0, plateau = 0;
      r.vc.forEach(v => { max = Math.max(max, v); });
      r.vc.forEach(v => { if (v >= 0.1 * max) { lit++; if (v >= 0.9 * max) plateau++; } });
      const share = plateau / lit, k = r.key + '@' + r.side;
      if (/^(abs|glute)@L$/.test(k)) named[k] = +share.toFixed(3);
      if (share > worst) { worst = share; who = k; }
    });
    res.stats.effortShape = Object.assign({ worstPlateauShare: +worst.toFixed(3), who }, named);
    if (worst > 0.3) fail(`effort colour on ${who} is a flat plate: ${(100 * worst).toFixed(0)}% of its lit skin within 10% of the peak (limit 30%)`);
  }
  // ---- 2b/2c. colour ramps: stabiliser on skin, every role on the garment
  {
    const lum = c => 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b;
    const ROLE = { 1: T3.colors.stab, 2: T3.colors.second, 3: T3.colors.prime };
    const hue = c => { const h = {}; c.getHSL(h, THREE.SRGBColorSpace); return h.h * 360; };
    const hueGap = (a, b) => Math.min(Math.abs(a - b), 360 - Math.abs(a - b));
    const abs = body.muscles.find(r => r.key === 'abs' && r.side === 'L'), glute = body.muscles.find(r => r.key === 'glute' && r.side === 'L');
    fig.roles({ abs: 1 });
    const stabFull = lum(new THREE.Color(ROLE[1]));
    let stabPeak = 0;
    for (let a = 0; a <= 1.0001; a += 0.05) { fig.apply({ 'act.abs': a }); stabPeak = Math.max(stabPeak, lum(abs.color)); }
    res.stats.stabiliserRamp = { peakLuminance: +stabPeak.toFixed(4), roleLuminance: +stabFull.toFixed(4) };
    if (stabPeak > stabFull + 1e-6) fail(`stabiliser ramp flashes paler than pale cobalt (luminance ${stabPeak.toFixed(3)} > ${stabFull.toFixed(3)}): a pale block`);
    res.stats.clothTint = {};
    for (const role of [1, 2, 3]) {
      fig.roles({ glute: role });
      fig.apply({ 'act.glute': 1 });
      const rest = glute.restC.clone(), end = glute.colorC.clone(), roleColor = new THREE.Color(ROLE[role]);
      const d = new V3(end.r - rest.r, end.g - rest.g, end.b - rest.b), len = d.length();
      const k = len / Math.hypot(roleColor.r - rest.r, roleColor.g - rest.g, roleColor.b - rest.b);
      let deviation = 0;
      for (let a = 0.05; a < 1; a += 0.05) {
        fig.apply({ 'act.glute': a });
        const p = new V3(glute.colorC.r - rest.r, glute.colorC.g - rest.g, glute.colorC.b - rest.b);
        deviation = Math.max(deviation, p.clone().sub(d.clone().multiplyScalar(p.dot(d) / (len * len))).length());
      }
      const h = hue(end), nearest = [1, 2, 3].sort((p, q) => hueGap(h, hue(new THREE.Color(ROLE[p]))) - hueGap(h, hue(new THREE.Color(ROLE[q]))))[0];
      res.stats.clothTint[role] = { k: +k.toFixed(3), offRamp: +deviation.toFixed(4), nearestRole: nearest };
      if (k > 0.75 || k < 0.3) fail(`role ${role} under the shorts reaches ${(100 * k).toFixed(0)}% of the role colour (want a subdued 30-75%): ${k > 0.75 ? 'a saturated blob' : 'invisible'}`);
      if (deviation > 0.005) fail(`role ${role} under the shorts leaves its straight ramp by ${deviation.toFixed(3)} (a darkened mid reads as a dark-red stain)`);
      if (nearest !== role) fail(`role ${role} under the shorts reads as role ${nearest}`);
    }
    fig.roles({}); fig.apply({});
  }
  // ---- 3. cut interior and loops (a model of the inner shader's discard rules, A.CUT.deep, on rays through the glute windows)
  {
    const rc = new THREE.Raycaster(), va = new V3(), vb = new V3(), vc = new V3(), bary = new V3();
    let inverted = 0;
    // Shells must be wound outward, or "back face" would not mean "inside".
    body.ensureInner();
    body.inner.meshes.muscles.forEach(grp => {
      const pos = grp.mesh.geometry.getAttribute('position'), ix = grp.mesh.geometry.getIndex();
      for (let p0 = 0; p0 < pos.count; p0 += 210) {
        let vol = 0;
        for (let t = 0; t < ix.count; t += 3) {
          const a = ix.getX(t); if (a < p0 || a >= p0 + 210) continue;
          va.fromBufferAttribute(pos, a); vb.fromBufferAttribute(pos, ix.getX(t + 1)); vc.fromBufferAttribute(pos, ix.getX(t + 2));
          vol += va.dot(vb.clone().cross(vc)) / 6;
        }
        if (vol < 0) inverted++;
      }
    });
    const maxOf = side => new Set(body.inner.meshes.muscles.filter(x => x.key === 'glute' && x.layer === 1 && x.side === side).map(x => x.mesh));
    const layerOf = m => /^(bones|tendons|knee-front)$/.test(m.name) ? 3 : (body.inner.meshes.muscles.find(x => x.mesh === m) || { layer: 9 }).layer;
    const trace = open => {
      fig.apply({ 'cut.glute': open, 'hi.glute': 1 });
      fig.root.updateMatrixWorld(true); body.skin.skeleton.update();
      const U = body.uniforms, wins = [];
      for (let i = 0; i < U.uWo.value.length; i++) {
        const o = U.uWo.value[i];
        if (o.x > 0.001) wins.push({ c: U.uWc.value[i], M: U.uWm.value[i], o0: o.x, o1: o.y, sweep: [o.z, o.w] });
      }
      const qOf = (w, p) => p.clone().sub(w.c).applyMatrix3(w.M).toArray();
      const inWin = (w, p) => { const q = qOf(w, p); return Math.hypot(q[0], q[1], q[2]) < w.o0; };
      const meshes = body.inner.group.children.filter(m => m.visible);
      let holeRays = 0, hollow = 0, deep = 0, loopRows = 0, rows = 0;
      for (const sg of [1, -1]) {
        const centre = fig.point('hips', sg * 34, -22, -50), maxGroups = maxOf(sg > 0 ? 'L' : 'R');
        for (let dy = -45; dy <= 45; dy += 3) {
          let runs = 0, onMax = false;
          // own side only: at the natal cleft the two maximi interleave, which is a seam, not a loop
          for (let dx = -24; dx <= 42; dx += 3) {
            rc.set(new V3(centre.x + dx, centre.y + dy, -400), new V3(0, 0, 1));
            let throughCut = false, first = null;
            for (const h of rc.intersectObjects(meshes, false)) {
              const m = h.object, local = m.worldToLocal(h.point.clone());
              m.getVertexPosition(h.face.a, va); m.getVertexPosition(h.face.b, vb); m.getVertexPosition(h.face.c, vc);
              THREE.Triangle.getBarycoord(local, va, vb, vc, bary);
              const bp = m.geometry.getAttribute('position'), bind = new V3()
                .addScaledVector(new V3().fromBufferAttribute(bp, h.face.a), bary.x)
                .addScaledVector(new V3().fromBufferAttribute(bp, h.face.b), bary.y)
                .addScaledVector(new V3().fromBufferAttribute(bp, h.face.c), bary.z);
              const normal = new V3().subVectors(vc, vb).cross(new V3().subVectors(va, vb)).transformDirection(m.matrixWorld);
              const front = normal.dot(rc.ray.direction) < 0, layer = layerOf(m), U2 = m.material.userData.U;
              let discard = U2 && U2.uWindowOnly.value > 0.5 && !wins.some(w => inWin(w, bind));
              if (layer === 1 && wins.some(w => A.CUT.deep(qOf(w, bind), w.o0, w.o1, w.sweep))) { discard = true; if (front) throughCut = true; }
              if (layer === 1 && !front && A.CUT.hideInnerWall && wins.some(w => w.o1 > 0.001 && inWin(w, bind))) discard = true;
              if (!discard && !first) first = { layer, front, max: maxGroups.has(m) };
            }
            const isMax = !!(first && first.max && first.front);
            if (isMax && !onMax) runs++;
            onMax = isMax;
            if (!throughCut || !first) continue;
            holeRays++;
            if (first.layer === 1 && !first.front) hollow++;
            if (first.layer >= 2) deep++;
          }
          if (runs) rows++;
          if (runs >= 2) loopRows++;
        }
      }
      return { holeRays, hollowShare: holeRays ? +(hollow / holeRays).toFixed(3) : null, deepShare: holeRays ? +(deep / holeRays).toFixed(3) : null,
        rowsWithMaximus: rows, loopShare: rows ? +(loopRows / rows).toFixed(3) : null };
    };
    res.stats.cutInterior = { invertedShells: inverted };
    if (inverted) fail(`${inverted} inner muscle shells are wound inward: a back face would not mean the inside`);
    for (const open of [1.0, 1.3, 1.6, 1.8]) {
      const s = res.stats.cutInterior['open' + open] = trace(open);
      if (open <= 1) { if (s.loopShare > 0.1) fail(`glute cutaway ${open}: the uncut gluteus maximus already reads as a loop`); continue; }
      if (s.holeRays < 50) { if (open >= 1.6) fail(`glute cutaway ${open}: only ${s.holeRays} rays pass the superficial cut; the model cannot judge it`); continue; }
      if (s.hollowShare > 0.02) fail(`glute cutaway ${open}: ${(100 * s.hollowShare).toFixed(0)}% of rays through the cut show the inside of the gluteus maximus shell (nested rings), not the layer below`);
      if (s.deepShare !== null && s.deepShare < 0.5) fail(`glute cutaway ${open}: only ${(100 * s.deepShare).toFixed(0)}% of rays through the cut reach the deep layer (limit 50%)`);
      if (s.rowsWithMaximus && s.loopShare > 0.1) fail(`glute cutaway ${open}: ${(100 * s.loopShare).toFixed(0)}% of scanlines cross the gluteus maximus twice (limit 10%): a coral loop around a hole, not a solid belly`);
    }
    fig.apply({});
  }
  // ---- 4. female deltoid (front silhouette, neutral)
  {
    const positions = posedRoot({}), out = {};
    for (let i = 0; i < n; i++) {
      const x = positions[i * 3], y = positions[i * 3 + 1], ax = Math.abs(x);
      if (ax < spec.shx * 0.5) continue;
      const key = (x > 0 ? 'L' : 'R') + Math.round(y / 5);
      if (!(key in out) || out[key] < ax) out[key] = ax;
    }
    res.stats.deltoidSilhouette = {};
    for (const side of ['L', 'R']) {
      let reach = 0;
      for (let y = spec.shy - 60; y <= spec.shy; y += 5) reach = Math.max(reach, out[side + Math.round(y / 5)] || 0);
      const arm = out[side + Math.round((spec.shy - 90) / 5)];
      const row = { reach: +(reach - spec.shx).toFixed(2), reachShare: +((reach - spec.shx) / spec.shx).toFixed(3), overhang: +(reach - arm).toFixed(2) };
      res.stats.deltoidSilhouette[side] = row;
      if (data.g === 'f' && (row.overhang > 2.5 || row.reachShare > 0.45)) {
        fail(`female deltoid ${side}: overhangs the upper arm by ${row.overhang} (limit 2.5) and reaches ${row.reachShare} x the shoulder half-width (limit 0.45): broad and square`);
      }
    }
  }
  // ---- 5. top contour at 90 degrees abduction (front projection), with axial rotation
  {
    res.stats.abductionRidge = {};
    for (const rt of [-90, 0, 90]) {
      const positions = posedRoot({ shL: 90, plL: 0, rtL: rt, shR: 90, plR: 0, rtR: rt }), row = {};
      for (const [side, sign] of [['L', 1], ['R', -1]]) {
        const x0 = spec.shx * 0.6, step = 2.5, nb = Math.ceil((spec.shx * 0.4 + 70) / step), top = new Array(nb + 1).fill(-Infinity);
        for (let i = 0; i < n; i++) {
          const x = positions[i * 3] * sign, y = positions[i * 3 + 1];
          if (y < spec.shy - 40 || y > spec.shy + 80) continue;
          const b = Math.round((x - x0) / step);
          if (b >= 0 && b <= nb && top[b] < y) top[b] = y;
        }
        let rise = 0, at = null;
        for (let b = 2; b <= nb; b++) if (top[b] - top[b - 2] > rise) { rise = top[b] - top[b - 2]; at = +(x0 + b * step).toFixed(1); }
        row[side] = { risePer5: +rise.toFixed(2), at };
        if (rise > 8) fail(`abduction 90 (rotation ${rt}) ${side}: the shoulder top rises ${rise.toFixed(2)} units in 5 onto the arm (limit 8): a ridge`);
      }
      res.stats.abductionRidge['rt' + rt] = row;
    }
    fig.apply({});
  }
  // ---- 6. deep-flexion crush (linear-blend skinning): inner-side skin of a hinge must not collapse onto the joint centre
  {
    const bones = body.skin.skeleton.bones, bi = {};
    bones.forEach((b, i) => { bi[b.name] = i; });
    const P0 = data.mesh.pos, si = data.skinIndex, sw = data.skinWeight;
    res.stats.jointCrush = {};
    for (const [name, pose, child, parent, gated] of [
      ['elbow150', { shL: 30, plL: 30, elL: 150 }, 'elL', 'shL', true],
      ['knee150', { ikLegL: 0, hpL: 100, knL: 150 }, 'knL', 'thL', true],
      ['hip120', { ikLegL: 0, hpL: 120, knL: 90 }, 'thL', 'hips', true],
      ['acrossBody', { shL: 90, plL: 135, elL: 95 }, 'shL', 'chest', false],
      ['overhead175', { shL: 175, plL: 90 }, 'shL', 'chest', false]
    ]) {
      const P1 = posedRoot(pose), rinv = fig.root.matrixWorld.clone().invert(), rot = new THREE.Matrix4().extractRotation(rinv);
      const pivot = fig.bone[child].getWorldPosition(new V3()).applyMatrix4(rinv);
      const ay = m => new V3().setFromMatrixColumn(m, 1).applyMatrix4(rot).normalize();
      const bis = ay(fig.bone[parent].matrixWorld).sub(ay(fig.bone[child].matrixWorld)).normalize();
      const bindPivot = new V3().setFromMatrixPosition(body.skin.skeleton.boneInverses[bi[child]].clone().invert());
      const inner = [], depth = [];
      for (let i = 0; i < n; i++) {
        let wc = 0, wp = 0;
        for (let j = 0; j < 4; j++) { const b = si[i * 4 + j]; if (b === bi[child]) wc += sw[i * 4 + j]; else if (b === bi[parent]) wp += sw[i * 4 + j]; }
        if (Math.min(wc, wp) < 0.2) continue;
        const d0 = Math.hypot(P0[i * 3] - bindPivot.x, P0[i * 3 + 1] - bindPivot.y, P0[i * 3 + 2] - bindPivot.z);
        if (d0 < 3) continue;
        const v = new V3(P1[i * 3] - pivot.x, P1[i * 3 + 1] - pivot.y, P1[i * 3 + 2] - pivot.z), d1 = v.length();
        if (v.normalize().dot(bis) > 0.35) { inner.push(d1 / d0); depth.push(d0 - d1); }
      }
      inner.sort((a, b) => a - b); depth.sort((a, b) => b - a);
      const p01 = inner.length ? inner[Math.floor(0.01 * inner.length)] : null;
      res.stats.jointCrush[name] = { innerVertices: inner.length, p01RadiusKept: p01 === null ? null : +p01.toFixed(3), maxCollapse: depth.length ? +depth[0].toFixed(2) : null, gated };
      if (gated && (inner.length < 20 || p01 < 0.6)) fail(`${name}: the inner fold collapses to ${p01 === null ? '?' : p01.toFixed(2)} of its rest distance from the joint (1st percentile; limit 0.6): linear-blend crush`);
    }
    fig.apply({});
  }
  round3Gates(fig, body, data, res, fail, posedRoot, idx);
  girdleGates(fig, body, data, res, fail, posedRoot, idx);
}

/*
 * Known limits closed in anatomy 1.5.0 (round 3, 2026-11-24). Numbers before/after: prompts/state/known-limits/anatomy-report.md.
 *   garmentTint  the shorts (gluteus maximus) and, on the female, the sports top (pectoralis) at full and half effort keep the role's
 *                hue and enough of its chroma (OKLCh) to read as a tint of it, never a grey-white or brown smear; on the top the tint
 *                covers the bust cap, not a ring around it
 *   effortReach  every superficial muscle on bare skin reaches its role colour at full activation (the belly vertex, shaded by the
 *                stage's own key + ambient light and toon ramp, seen face-on) and a core of its skin reads as that colour
 *   hingeSurface hip flexion 90/100 from behind: no LBS fold-overs on the buttock and shorts (posed neighbour-normal angles) and the
 *                GPU's skinned shading normals agree with the posed surface
 */
function round3Gates(fig, body, data, res, fail, posedRoot, idx) {
  const n = data.n, V3 = THREE.Vector3, ROLE = { 1: T3.colors.stab, 2: T3.colors.second, 3: T3.colors.prime };
  const oklab = c => {
    const l = Math.cbrt(0.4122214708 * c.r + 0.5363325363 * c.g + 0.0514459929 * c.b), m = Math.cbrt(0.2119034982 * c.r + 0.6806995451 * c.g + 0.1073969566 * c.b),
      s = Math.cbrt(0.0883024619 * c.r + 0.2817188376 * c.g + 0.6299787005 * c.b);
    return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s, 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
  };
  const lch = c => { const [L, a, b] = oklab(c); return { L, C: Math.hypot(a, b), h: (Math.atan2(b, a) / D2R + 360) % 360 }; };
  const hueGap = (a, b) => Math.min(Math.abs(a - b), 360 - Math.abs(a - b));
  const dE = (p, q) => { const a = oklab(p), b = oklab(q); return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]); };
  const r3 = v => +v.toFixed(3);
  // ---- garment tint: ramp end and half-way point per role, on the shorts and (female) the top
  {
    const recs = [['shorts', body.muscles.find(r => r.key === 'glute' && r.side === 'L')]];
    if (data.hasTop) recs.push(['top', body.muscles.find(r => r.key === 'pec' && r.side === 'L')]);
    res.stats.garmentTint = {};
    for (const [garment, rec] of recs) {
      res.stats.garmentTint[garment] = {};
      for (const role of [1, 2, 3]) {
        const roleC = lch(new THREE.Color(ROLE[role]));
        fig.roles({ [rec.key]: role });
        fig.apply({ ['act.' + rec.key]: 1 }); const full = lch(rec.colorC);
        fig.apply({ ['act.' + rec.key]: 0.5 }); const half = lch(rec.colorC);
        const row = { fullChromaShare: r3(full.C / roleC.C), fullHueGap: +hueGap(full.h, roleC.h).toFixed(1), halfChroma: r3(half.C), halfHueGap: +hueGap(half.h, roleC.h).toFixed(1) };
        res.stats.garmentTint[garment][role] = row;
        if (row.fullChromaShare < 0.55 || row.fullHueGap > 12 || row.halfChroma < 0.06 || row.halfHueGap > 15) {
          fail(`role ${role} under the ${garment} reads as a grey or brown smear, not a tint of the role: full effort keeps ${(100 * row.fullChromaShare).toFixed(0)}% of its chroma (min 55%, hue off by ${row.fullHueGap} deg, max 12), half effort chroma ${row.halfChroma} (min 0.06, hue off by ${row.halfHueGap} deg, max 15)`);
        }
      }
    }
    // the top over the bust: the tint must cover the cap, not ring it
    if (data.hasTop) {
      const rec = body.muscles.find(r => r.key === 'pec' && r.side === 'L'), bust = data.table.find(m => m.key === 'bust' && m.side === 'L');
      const half = Math.hypot(bust.B[0] - bust.A[0], bust.B[1] - bust.A[1], bust.B[2] - bust.A[2]) / 2, P = data.mesh.pos, c = bust.center;
      const cap = [];
      for (let v = 0; v < n; v++) {
        if (data.topMask[v] < 0.5 || P[v * 3] <= 0 || P[v * 3 + 2] < c[2]) continue;
        const ex = (P[v * 3] - c[0]) / bust.rw, ey = (P[v * 3 + 1] - c[1]) / half;
        if (ex * ex + ey * ey < 0.36) cap.push(v);
      }
      res.stats.garmentTint.topCap = { vertices: cap.length };
      for (const role of [1, 3]) {
        fig.roles({ pec: role }); fig.apply({ 'act.pec': 1 });
        const colC = body.geo.getAttribute('colorC').array, rest = rec.restC, dir = new V3(rec.fullC.r - rest.r, rec.fullC.g - rest.g, rec.fullC.b - rest.b), dl2 = dir.lengthSq();
        const k = v => ((colC[v * 3] - rest.r) * dir.x + (colC[v * 3 + 1] - rest.g) * dir.y + (colC[v * 3 + 2] - rest.b) * dir.z) / dl2;
        const capK = cap.map(k).sort((a, b) => a - b), topK = Array.from(rec.vi).filter(v => data.topMask[v] > 0.5).map(k).sort((a, b) => a - b);
        const mean = new THREE.Color(0, 0, 0);
        cap.forEach(v => { mean.r += colC[v * 3] / cap.length; mean.g += colC[v * 3 + 1] / cap.length; mean.b += colC[v * 3 + 2] / cap.length; });
        const m = lch(mean), roleC = lch(new THREE.Color(ROLE[role]));
        const row = { capMedianK: r3(capK[capK.length >> 1] || 0), topP90K: r3(topK[Math.floor(0.9 * topK.length)] || 0), capChromaShare: r3(m.C / roleC.C), capHueGap: +hueGap(m.h, roleC.h).toFixed(1) };
        row.ringRatio = row.topP90K ? r3(row.capMedianK / row.topP90K) : 0;
        res.stats.garmentTint.topCap['role' + role] = row;
        if (cap.length < 30 || row.ringRatio < 0.6) fail(`role ${role} on the sports top is a ring around the bust: the cap reaches ${row.capMedianK} of the tint against ${row.topP90K} on the rest of the top (ratio ${row.ringRatio}, min 0.6; ${cap.length} cap vertices)`);
        if (row.capChromaShare < 0.4 || row.capHueGap > 15) fail(`role ${role} on the sports top: the bust cap reads as a grey or brown smear (${(100 * row.capChromaShare).toFixed(0)}% of the role's chroma, min 40%; hue off by ${row.capHueGap} deg, max 15)`);
      }
    }
    fig.roles({}); fig.apply({});
  }
  // ---- effort reach on bare skin, under the stage's own light seen face-on
  {
    const st = T3.stage(null, { headless: true });
    let key = null, amb = null;
    st.camera.traverse(o => { if (o.isDirectionalLight) key = o; });
    st.scene.traverse(o => { if (o.isAmbientLight) amb = o; });
    const L = key.position.clone().sub(key.target.position).normalize(), gm = body.material.gradientMap, gd = gm.image.data, gw = gm.image.width;
    // toon irradiance at N.L for N = the view direction (face-on): linear-filtered gradient map at 0.5 N.L + 0.5
    const u = (0.5 * L.z + 0.5) * gw - 0.5, i0 = Math.max(0, Math.min(gw - 1, Math.floor(u))), i1 = Math.min(gw - 1, i0 + 1), f = Math.max(0, Math.min(1, u - i0));
    const grad = ((1 - f) * gd[i0] + f * gd[i1]) / 255, light = (key.intensity * grad + amb.intensity) / Math.PI;
    const shade = c => new THREE.Color(Math.min(1, c.r * light), Math.min(1, c.g * light), Math.min(1, c.b * light));
    const out = { light: r3(light) }, misses = [], seen = new Set();
    let worstPeak = 0, worstCore = 1;
    body.muscles.forEach(r => {
      if (r.layer !== 1 || r.side !== 'L' || r.vi.length < 40 || r.cloth || seen.has(r.key)) return;
      seen.add(r.key);
      let pk = 0, pv = -1;
      r.vc.forEach((w, i) => { if (w > pk) { pk = w; pv = r.vi[i]; } });
      // a belly under the sports top is the garment gate's job (the bare-skin rim around it is a fade, not the belly)
      if (pv < 0 || data.topMask[pv] > 0.1) { out[r.key] = 'under the top'; return; }
      const row = {};
      for (const role of [1, 2, 3]) {
        const target = new THREE.Color(ROLE[role]);
        fig.roles({ [r.key]: role }); fig.apply({ ['act.' + r.key]: 1 });
        const col = body.geo.getAttribute('color').array, at = v => shade(new THREE.Color(col[v * 3], col[v * 3 + 1], col[v * 3 + 2]));
        let strong = 0, near = 0;
        r.vi.forEach((v, i) => { if (r.vw[i] >= 0.6 && data.topMask[v] <= 0.1) { strong++; if (dE(at(v), target) <= 0.1) near++; } });
        const peak = dE(at(pv), target), core = strong ? near / strong : 0;
        row[role] = { peakDE: r3(peak), core: r3(core) };
        worstPeak = Math.max(worstPeak, peak); worstCore = Math.min(worstCore, core);
        if (peak > 0.05 || core < 0.06) misses.push(`${r.key} role ${role} (peak dE ${peak.toFixed(3)}, core ${(100 * core).toFixed(0)}%)`);
      }
      out[r.key] = row;
    });
    out.worstPeakDE = r3(worstPeak); out.worstCore = r3(worstCore);
    res.stats.effortReach = out;
    if (misses.length) fail(`full activation never reaches the role colour on bare skin (belly dE <= 0.05 under the default light, >= 6% of the muscle's skin within dE 0.10): ${misses.join(', ')}`);
    fig.roles({}); fig.apply({});
  }
  // ---- hinge from behind: posed surface and shading normals over the buttock and shorts
  {
    const sk = body.skin, bones = sk.skeleton.bones, inv = sk.skeleton.boneInverses, B = data.mesh.pos;
    const inBox = v => { const x = Math.abs(B[v * 3]), y = B[v * 3 + 1]; return x < 85 && y < A.CLOTH.waist - 4 && y > -95 && B[v * 3 + 2] < -5; };
    const nb = new Array(n); for (let i = 0; i < n; i++) nb[i] = [];
    for (let t = 0; t < idx.length; t += 3) for (let e = 0; e < 3; e++) nb[idx[t + e]].push(idx[t + (e + 1) % 3]);
    res.stats.hingeSurface = {};
    for (const hp of [90, 100]) {
      fig.apply({ ikLegL: 0, ikLegR: 0, hpL: hp, hpR: hp, knL: 20, knR: 20 }); fig.root.updateMatrixWorld(true); sk.skeleton.update();
      const pa = sk.geometry.getAttribute('position'), na = sk.geometry.getAttribute('normal'), si = sk.geometry.getAttribute('skinIndex'), sw = sk.geometry.getAttribute('skinWeight');
      const P = new Float32Array(n * 3), p = new V3();
      for (let i = 0; i < n; i++) { p.fromBufferAttribute(pa, i); sk.applyBoneTransform(i, p); p.toArray(P, i * 3); }
      const g2 = new THREE.BufferGeometry(); g2.setAttribute('position', new THREE.BufferAttribute(P, 3)); g2.setIndex(Array.from(idx)); g2.computeVertexNormals();
      const TN = g2.getAttribute('normal').array, M = new THREE.Matrix4(), tmp = new THREE.Matrix4(), sn = new V3(), angles = [], shading = [];
      for (let v = 0; v < n; v++) {
        if (!inBox(v)) continue;
        let worst = 0;
        for (const u of nb[v]) worst = Math.max(worst, Math.acos(Math.max(-1, Math.min(1, TN[v * 3] * TN[u * 3] + TN[v * 3 + 1] * TN[u * 3 + 1] + TN[v * 3 + 2] * TN[u * 3 + 2]))) / D2R);
        angles.push(worst);
        M.set(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
        for (let j = 0; j < 4; j++) { const w = sw.getComponent(v, j); if (!w) continue; const b = si.getComponent(v, j); tmp.multiplyMatrices(bones[b].matrixWorld, inv[b]); for (let k = 0; k < 16; k++) M.elements[k] += w * tmp.elements[k]; }
        M.premultiply(sk.bindMatrixInverse).multiply(sk.bindMatrix);
        sn.fromBufferAttribute(na, v).transformDirection(M);
        shading.push(Math.acos(Math.max(-1, Math.min(1, sn.x * TN[v * 3] + sn.y * TN[v * 3 + 1] + sn.z * TN[v * 3 + 2]))) / D2R);
      }
      g2.dispose();
      angles.sort((a, b) => a - b); shading.sort((a, b) => a - b);
      const row = { vertices: angles.length, p999NeighbourAngle: +angles[Math.floor(0.999 * angles.length)].toFixed(1), shareOver30: +(angles.filter(a => a > 30).length / angles.length).toFixed(4),
        shadingNormalP99: +shading[Math.floor(0.99 * shading.length)].toFixed(1) };
      res.stats.hingeSurface['hip' + hp] = row;
      if (row.p999NeighbourAngle > 45 || row.shareOver30 > 0.015) fail(`hinge ${hp} from behind: the buttock and shorts fold (99.9th percentile neighbour-normal angle ${row.p999NeighbourAngle} deg, limit 45; ${(100 * row.shareOver30).toFixed(2)}% over 30 deg, limit 1.5%): a lumpy mass`);
      if (row.shadingNormalP99 > 15) fail(`hinge ${hp} from behind: the skinned shading normals miss the posed surface by ${row.shadingNormalP99} deg (99th percentile, limit 15): the toon bands draw lumps`);
    }
    fig.apply({});
  }
}

/*
 * Shoulder girdle (round 3 phase B: anatomy 1.6.0, Tibi 0.8.0). Numbers before/after: prompts/state/known-limits/r3b-report.md.
 *   shoulderCrush  rig-independent, posed skin only, at cross-body reach and overhead 175. Skin around the left glenohumeral joint
 *                  (bind distance 15-80) is split into nine sectors (above / level / below the joint x in front / middle / behind it);
 *                  in each, the 1st percentile of its posed distance from the POSED joint over its bind distance. The cap (level and
 *                  above: deltoid over the humeral head, acromion, top of the shoulder) must keep 0.7 of it. The armpit (below) may
 *                  hollow toward the ribs, but no armpit skin may pass within 10 units (about the humeral head's radius) of the joint
 *                  centre: linear-blend skinning pulled it through the joint (1.6-2.0 units overhead) and flattened the back of the cap
 *                  across the body (0.58) at Tibi 0.7.0. (The armpit was first gated on the ratio, >= 0.35; it is gated on the
 *                  clearance since a ribcage-glide experiment put that skin back on the ribs, nearer the joint by design; the ratio is
 *                  reported.) Gated too: the share of rays from eight directions at the shoulder whose first hit is the back of a
 *                  triangle (inside-out skin that would be SEEN) must stay <= 0.5%: at most 0.03% before or after the girdle (the dark
 *                  overhead armpit was a deep crushed pit, not inverted skin); the glide experiment showed 1.6% overhead.
 *                  Flexion 90, abduction 175 and axial rotation +/-90 at abduction 90 are reported.
 *   armpitLift     trunk skin behind and under the joint (bind 15-95 below it, nearer the torso core than the arm core), read in the
 *                  chest's bind frame: its height above the torso core with the arms up minus arms down, 99th percentile. Rotating
 *                  that skin rigidly with the girdle lifts it off the ribs ("wings" behind and beside the raised armpit, the female
 *                  top flaring out). Limits 20 / 32 / 45 at abduction 90 / flexion 175 / abduction 175, set after measuring: the
 *                  girdle field reaching 90 below the joint lifted it 16.5 / 37.2 / 50.7 (male; fails), 70 lifts 15.8 / 27.5 / 39.5;
 *                  0.7.0 lifted it 1-14 (it crushed instead). STILL A VISIBLE LUMP at 70, only smaller: an open known limit
 *                  (r3b-report.md). A ribcage-glide corrective flattened it (p99 <= 13) but folded skin through skin (seenInsideOut).
 *   latInflation   the 1.10 rejection, re-expressed so the scapula may move skin: raising the arms (elevation only, elbows straight,
 *                  no activation) must not push lat skin out along its normal, through the morph (bind-space displacement along the
 *                  bind normal) or through the bones (each lat-belly vertex's height above the torso core carried by the chest, on
 *                  average and at its worst). Rigid girdle motion slides skin along the trunk; inflation lifts it off.
 */
const GIRDLE_LIMITS = { cap: 0.7, axillaClearance: 10, seenInsideOut: 0.005, morphOut: 0.5, boneLift: 1.5, boneLiftMax: 2.5,
  armpitLift: { abduction90: 20, overhead175: 32, overheadAbduction: 45 } };
const SECTORS = ['above/front', 'above/mid', 'above/back', 'level/front', 'level/mid', 'level/back', 'below/front', 'below/mid', 'below/back'];
/** Share of rays (eight directions, 2-unit grid, 140 x 140 around c) whose first hit on the skin is the back of a triangle. */
function seenInsideOut(P, idx, c) {
  const D = [[0, 0, 1], [1, 0, 0], [0, 0, -1], [0.707, 0, 0.707], [0.707, 0, -0.707], [0.6, -0.5, 0.6], [0.6, -0.5, -0.6], [0.3, 1, 0.3]];
  const HALF = 70, STEP = 2, NC = 71;
  let hits = 0, back = 0;
  for (const d0 of D) {
    const dir = new THREE.Vector3(...d0).normalize(), u = new THREE.Vector3(0, 1, 0);
    if (Math.abs(u.dot(dir)) > 0.9) u.set(1, 0, 0);
    u.sub(dir.clone().multiplyScalar(u.dot(dir))).normalize();
    const v = new THREE.Vector3().crossVectors(dir, u), cells = new Array(NC * NC);
    // every triangle binned by its projected box on the ray grid, so each ray meets all of its occluders
    for (let t = 0; t < idx.length; t += 3) {
      let u0 = Infinity, u1 = -Infinity, v0 = Infinity, v1 = -Infinity;
      for (let e = 0; e < 3; e++) {
        const a = idx[t + e] * 3, x = P[a] - c.x, y = P[a + 1] - c.y, z = P[a + 2] - c.z, pu = x * u.x + y * u.y + z * u.z, pv = x * v.x + y * v.y + z * v.z;
        u0 = Math.min(u0, pu); u1 = Math.max(u1, pu); v0 = Math.min(v0, pv); v1 = Math.max(v1, pv);
      }
      if (u1 < -HALF || u0 > HALF || v1 < -HALF || v0 > HALF) continue;
      for (let i = Math.max(0, Math.ceil((u0 + HALF) / STEP)); i <= Math.min(NC - 1, Math.floor((u1 + HALF) / STEP)); i++) {
        for (let j = Math.max(0, Math.ceil((v0 + HALF) / STEP)); j <= Math.min(NC - 1, Math.floor((v1 + HALF) / STEP)); j++) (cells[i * NC + j] = cells[i * NC + j] || []).push(t);
      }
    }
    const rx = -dir.x, ry = -dir.y, rz = -dir.z;
    for (let i = 0; i < NC; i++) for (let j = 0; j < NC; j++) {
      const list = cells[i * NC + j]; if (!list) continue;
      const cu = -HALF + i * STEP, cv = -HALF + j * STEP;
      const ox = c.x + dir.x * 400 + u.x * cu + v.x * cv, oy = c.y + dir.y * 400 + u.y * cu + v.y * cv, oz = c.z + dir.z * 400 + u.z * cu + v.z * cv;
      let best = Infinity, isBack = false;
      for (const t of list) {
        const A = idx[t] * 3, B = idx[t + 1] * 3, C = idx[t + 2] * 3;
        const e1x = P[B] - P[A], e1y = P[B + 1] - P[A + 1], e1z = P[B + 2] - P[A + 2], e2x = P[C] - P[A], e2y = P[C + 1] - P[A + 1], e2z = P[C + 2] - P[A + 2];
        const px = ry * e2z - rz * e2y, py = rz * e2x - rx * e2z, pz = rx * e2y - ry * e2x, det = e1x * px + e1y * py + e1z * pz;
        if (Math.abs(det) < 1e-9) continue;
        const sx = ox - P[A], sy = oy - P[A + 1], sz = oz - P[A + 2], uu = (sx * px + sy * py + sz * pz) / det;
        if (uu < 0 || uu > 1) continue;
        const qx = sy * e1z - sz * e1y, qy = sz * e1x - sx * e1z, qz = sx * e1y - sy * e1x, vv = (rx * qx + ry * qy + rz * qz) / det;
        if (vv < 0 || uu + vv > 1) continue;
        const tt = (e2x * qx + e2y * qy + e2z * qz) / det;
        if (tt > 0 && tt < best) { best = tt; isBack = det < 0; }     // det < 0: the ray meets the triangle from behind its outward normal
      }
      if (best < Infinity) { hits++; if (isBack) back++; }
    }
  }
  return { share: back / hits, rays: hits };
}
function girdleGates(fig, body, data, res, fail, posedRoot, idx) {
  const n = data.n, P0 = data.mesh.pos, V3 = THREE.Vector3, bones = body.skin.skeleton.bones, bi = {};
  bones.forEach((b, i) => { bi[b.name] = i; });
  fig.roles({});
  const GH = new V3().setFromMatrixPosition(body.skin.skeleton.boneInverses[bi.shL].clone().invert());
  const region = [];
  for (let i = 0; i < n; i++) {
    const x = P0[i * 3] - GH.x, y = P0[i * 3 + 1] - GH.y, z = P0[i * 3 + 2] - GH.z, d0 = Math.hypot(x, y, z);
    if (d0 < 15 || d0 > 80 || P0[i * 3] <= 20) continue;
    region.push([i, d0, SECTORS.indexOf((y > 15 ? 'above' : y < -15 ? 'below' : 'level') + '/' + (z > 12 ? 'front' : z < -12 ? 'back' : 'mid'))]);
  }
  res.stats.shoulderCrush = {};
  for (const [name, pose, gated] of [
    ['acrossBody', { shL: 90, plL: 135, elL: 95 }, true],
    ['overhead175', { shL: 175, shR: 175, plL: 90, plR: 90 }, true],
    ['overheadAbduction', { shL: 175, plL: 0 }, false],
    ['flexion90', { shL: 90, plL: 90 }, false],
    ['axialPlus90', { shL: 90, plL: 0, rtL: 90 }, false],
    ['axialMinus90', { shL: 90, plL: 0, rtL: -90 }, false]
  ]) {
    const P = posedRoot(pose), rinv = fig.root.matrixWorld.clone().invert();
    const gh = fig.bone.shL.getWorldPosition(new V3()).applyMatrix4(rinv);
    const bySector = SECTORS.map(() => []);
    let clear = Infinity;
    region.forEach(([i, d0, s]) => {
      const d1 = Math.hypot(P[i * 3] - gh.x, P[i * 3 + 1] - gh.y, P[i * 3 + 2] - gh.z);
      bySector[s].push(d1 / d0);
      if (s >= 6) clear = Math.min(clear, d1);
    });
    const sectors = {};
    let cap = Infinity, capAt = '', axilla = Infinity, axillaAt = '';
    bySector.forEach((list, s) => {
      list.sort((a, b) => a - b);
      const p01 = list[Math.floor(0.01 * list.length)];
      sectors[SECTORS[s]] = +p01.toFixed(3);
      if (SECTORS[s].indexOf('below') === 0) { if (p01 < axilla) { axilla = p01; axillaAt = SECTORS[s]; } } else if (p01 < cap) { cap = p01; capAt = SECTORS[s]; }
    });
    const seen = gated ? seenInsideOut(P, idx, gh) : null;
    const row = { cap: +cap.toFixed(3), capAt, axilla: +axilla.toFixed(3), axillaAt, axillaClearance: +clear.toFixed(2), seenInsideOut: seen ? +seen.share.toFixed(4) : null, rays: seen ? seen.rays : null,
      joint: gh.toArray().map(x => +x.toFixed(1)), sectors, gated };
    res.stats.shoulderCrush[name] = row;
    if (!gated) continue;
    if (row.cap < GIRDLE_LIMITS.cap) fail(`${name}: the shoulder cap (${capAt}) collapses to ${row.cap} of its distance from the joint (1st percentile, limit ${GIRDLE_LIMITS.cap}): the shoulder is crushed`);
    if (row.axillaClearance < GIRDLE_LIMITS.axillaClearance) fail(`${name}: armpit skin passes ${row.axillaClearance} units from the joint centre (limit ${GIRDLE_LIMITS.axillaClearance}, about the humeral head's radius): the shoulder is crushed`);
    if (row.seenInsideOut > GIRDLE_LIMITS.seenInsideOut) fail(`${name}: ${(100 * row.seenInsideOut).toFixed(2)}% of the rays at the shoulder see the inside of the skin (limit ${100 * GIRDLE_LIMITS.seenInsideOut}%): skin folded through skin`);
  }
  fig.apply({});
  // ---- posterior armpit lift (the "hook" seen from behind): trunk skin behind and under the joint carried off the ribcage
  {
    const armCore = data.cores.find(c => c.id === 'armL').prim, torsoCore = data.cores.find(c => c.id === 'torso').prim, ci = bi.chest, reg = [];
    for (let i = 0; i < n; i++) {
      const x = P0[i * 3], y = P0[i * 3 + 1], z = P0[i * 3 + 2], dy = GH.y - y;
      if (dy < 15 || dy > 95 || Math.abs(x - GH.x) > 45 || x < 20 || z > GH.z) continue;
      if (armCore.f(x, y, z) < torsoCore.f(x, y, z)) continue;                        // arm skin, not trunk skin
      reg.push(i);
    }
    const heights = pose => {
      const P = posedRoot(pose), rinv = fig.root.matrixWorld.clone().invert(), q = new V3();
      const toChest = new THREE.Matrix4().multiplyMatrices(rinv, bones[ci].matrixWorld).multiply(body.skin.skeleton.boneInverses[ci]).invert();
      return reg.map(i => { q.set(P[i * 3], P[i * 3 + 1], P[i * 3 + 2]).applyMatrix4(toChest); return q.y < -45 || q.y > 257 ? NaN : torsoCore.f(q.x, q.y, q.z); });
    };
    const rest = heights({ shL: 0, shR: 0 });
    res.stats.armpitLift = { vertices: reg.length };
    for (const [name, pose] of [['abduction90', { shL: 90, shR: 90, plL: 0, plR: 0 }], ['overhead175', { shL: 175, shR: 175, plL: 90, plR: 90 }], ['overheadAbduction', { shL: 175, shR: 175, plL: 0, plR: 0 }]]) {
      const d = heights(pose).map((h, k) => h - rest[k]).filter(Number.isFinite).sort((a, b) => a - b);
      const row = { p90: +d[Math.floor(0.9 * d.length)].toFixed(2), p99: +d[Math.floor(0.99 * d.length)].toFixed(2), max: +d[d.length - 1].toFixed(2) };
      row.limit = GIRDLE_LIMITS.armpitLift[name];
      res.stats.armpitLift[name] = row;
      if (row.p99 > row.limit) fail(`${name}: the skin behind the armpit lifts ${row.p99} units off the ribcage (99th percentile, limit ${row.limit}): wings under the raised arm`);
    }
    fig.apply({});
  }
  // ---- lat inflation on elevation alone
  const latW = new Float32Array(n);
  body.muscles.filter(r => r.key === 'lat').forEach(r => { for (let k = 0; k < r.vi.length; k++) latW[r.vi[k]] = Math.max(latW[r.vi[k]], r.vw[k]); });
  // the torso core tube's own extent (bind y): beyond it a lat vertex has been carried onto the arm and has no height above the trunk
  const torso = data.cores.find(c => c.id === 'torso').prim, ci = bi.chest, LAT_SPAN = [-45, 257];
  const lift = pose => {
    const P = posedRoot(pose), unposed = body.geo.getAttribute('position').array.slice();
    const rinv = fig.root.matrixWorld.clone().invert();
    const toChestBind = new THREE.Matrix4().multiplyMatrices(rinv, bones[ci].matrixWorld).multiply(body.skin.skeleton.boneInverses[ci]).invert();
    const q = new V3();
    let sum = 0, cnt = 0, off = 0;
    const lifts = [];
    for (let i = 0; i < n; i++) {
      if (latW[i] < 0.6) continue;
      q.set(P[i * 3], P[i * 3 + 1], P[i * 3 + 2]).applyMatrix4(toChestBind);
      if (q.y < LAT_SPAN[0] || q.y > LAT_SPAN[1]) { off++; lifts.push([i, NaN]); continue; }   // carried off the trunk (onto the arm)
      const f = torso.f(q.x, q.y, q.z);
      sum += f; cnt++; lifts.push([i, f]);
    }
    return { mean: sum / cnt, lifts, unposed, off };
  };
  const rest = lift({ shL: 0, shR: 0, elL: 0, elR: 0 });
  res.stats.latInflation = {};
  for (const [name, pose] of [['raised175', { shL: 175, shR: 175, elL: 0, elR: 0 }], ['flexion175', { shL: 175, shR: 175, plL: 90, plR: 90, elL: 0, elR: 0 }], ['abduction90', { shL: 90, shR: 90, plL: 0, plR: 0, elL: 0, elR: 0 }]]) {
    const up = lift(pose);
    let morphOut = 0;
    for (let i = 0; i < n; i++) {
      if (latW[i] < 0.3) continue;
      const out = (up.unposed[i * 3] - rest.unposed[i * 3]) * data.normals[i * 3] + (up.unposed[i * 3 + 1] - rest.unposed[i * 3 + 1]) * data.normals[i * 3 + 1] + (up.unposed[i * 3 + 2] - rest.unposed[i * 3 + 2]) * data.normals[i * 3 + 2];
      morphOut = Math.max(morphOut, out);
    }
    // per-vertex lift of the lat belly against the arms-down pose: a local flare is a bulge too, not only a raised mean
    const d = up.lifts.map(([, f], k) => f - rest.lifts[k][1]).filter(Number.isFinite).sort((a, b) => a - b);
    const row = { morphOut: +morphOut.toFixed(3), boneLift: +(up.mean - rest.mean).toFixed(3), boneLiftP95: +d[Math.floor(0.95 * d.length)].toFixed(3), boneLiftMax: +d[d.length - 1].toFixed(3), offTrunk: up.off };
    res.stats.latInflation[name] = row;
    if (row.morphOut > GIRDLE_LIMITS.morphOut || row.boneLift > GIRDLE_LIMITS.boneLift || row.boneLiftMax > GIRDLE_LIMITS.boneLiftMax) {
      fail(`${name}: raising the arms pushes the lat out (morph ${row.morphOut} along its normal, limit ${GIRDLE_LIMITS.morphOut}; belly ${row.boneLift} higher off the chest's torso core on average, limit ${GIRDLE_LIMITS.boneLift}, ${row.boneLiftMax} at most, limit ${GIRDLE_LIMITS.boneLiftMax}): unsupported lat bulge`);
    }
  }
  fig.apply({});
}

function check(g) {
  const stage = T3.stage(null, { headless: true });
  const t0 = Date.now();
  const fig = stage.tibi({ gender: g, profileSampling: opt.profileSampling });
  const buildMs = Date.now() - t0;                      // the kit itself never reads a clock (the render lint forbids it); the test may
  const body = fig.body, data = body.data, G = data.G;
  const res = { gender: g, profileSampling: opt.profileSampling, failures: [], notes: [], stats: {} };
  const fail = m => res.failures.push(m);

  // The authored torso landmarks must land on the core contour to within half a mesh cell.
  const torso = data.cores.find(c => c.id === 'torso').prim;
  const stationErrors = fig.spec.torso.flatMap(r => [
    Math.abs(torso.f(r[1] * 0.93, r[0], r[3])),
    Math.abs(torso.f(0, r[0], r[3] + r[2] * 0.93))
  ]);
  const stationError = Math.max(...stationErrors), stationTolerance = G.h / 2;
  res.stats.profileStations = { maxAbsDistance: stationError, tolerance: stationTolerance };
  if (stationError > stationTolerance) {
    const message = `tube profile misses authored stations by ${stationError.toFixed(2)} units (limit ${stationTolerance})`;
    if (opt.profileSampling === 'distance') fail(message);
    else res.notes.push('Known legacy limit: ' + message + '; legacy is a compatibility reference, not the current anatomical body');
  }

  // ---- skin: watertight, one component
  const idx = data.mesh.idx, nTri = idx.length / 3, n = data.n;
  const edges = new Map();
  for (let i = 0; i < idx.length; i += 3) for (let e = 0; e < 3; e++) { const a = idx[i + e], b = idx[i + (e + 1) % 3], k = a < b ? a * 1e6 + b : b * 1e6 + a; edges.set(k, (edges.get(k) || 0) + 1); }
  let open = 0, boundary = 0, nonManifold = 0;
  edges.forEach(v => { if (v !== 2) open++; if (v === 1) boundary++; if (v > 2) nonManifold++; });
  const parent = new Int32Array(n); for (let i = 0; i < n; i++) parent[i] = i;
  const find = x => { while (parent[x] !== x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; };
  for (let i = 0; i < idx.length; i += 3) { parent[find(idx[i])] = find(idx[i + 1]); parent[find(idx[i + 1])] = find(idx[i + 2]); }
  const comps = new Set(); for (let i = 0; i < n; i++) if (parent[i] === i) comps.add(i);
  // vertices that no triangle uses do not count as components
  const used = new Set(); for (let i = 0; i < idx.length; i++) used.add(find(idx[i]));
  res.stats.skin = { vertices: n, triangles: nTri, boundaryEdges: boundary, nonManifoldEdges: nonManifold, openOrNonManifoldEdges: open, edgeFraction: +(open / edges.size).toExponential(2), components: used.size, buildMs: buildMs };
  if (boundary) fail(`skin has ${boundary} boundary edges: the outer body must have no open holes`);
  if (open / edges.size > 3e-4) fail(`skin has ${open} open or non-manifold edges (${(100 * open / edges.size).toFixed(3)}% of edges): gaps in the body`);
  if (used.size !== 1) fail(`skin has ${used.size} disconnected pieces (expected one continuous body)`);

  // ---- protrusion: inner geometry inside the skin envelope
  body.ensureInner();
  let maxProt = -1e9, worst = '', cnt = 0;
  body.inner.group.children.forEach(m => {
    const pa = m.geometry.getAttribute('position');
    for (let i = 0; i < pa.count; i++) {
      const d = A._gridAt(G, pa.getX(i), pa.getY(i), pa.getZ(i)); cnt++;
      if (d > maxProt) { maxProt = d; worst = m.name; }
    }
  });
  res.stats.protrusion = { innerVertices: cnt, maxSkinDistance: +maxProt.toFixed(2), worstMesh: worst };
  if (maxProt > -1.5) fail(`inner geometry reaches ${maxProt.toFixed(1)} units from the skin surface (${worst}); it must stay inside by at least 1.5`);

  // ---- external: nothing that is not skin hangs outside it
  const allowed = /^(skin|inner|spark|pony)/;
  const stray = [];
  fig.root.traverse(o => { if (o.isMesh && !o.isSkinnedMesh && o.parent && /muscle|delt|pec|quad|calf|glute|biceps|triceps/i.test(o.name || '')) stray.push(o.name); });
  fig.root.children.forEach(c => { if (c.isMesh && !/^skin$/.test(c.name) && !c.isSkinnedMesh) stray.push(c.name || 'unnamed mesh'); });
  res.stats.strayMuscleMeshes = stray.length;
  if (stray.length) fail(`muscle-like meshes hang on the rig outside the skin: ${stray.join(', ')}`);

  // ---- coverage, gradient
  const adj = new Array(n); for (let i = 0; i < n; i++) adj[i] = [];
  for (let i = 0; i < idx.length; i += 3) for (let e = 0; e < 3; e++) { adj[idx[i + e]].push(idx[i + (e + 1) % 3]); }
  const low = [], hard = [];
  body.muscles.forEach(r => {
    const w = new Float32Array(n);
    for (let k = 0; k < r.vi.length; k++) w[r.vi[k]] = r.vw[k];
    let maxJump = 0;
    for (let k = 0; k < r.vi.length; k++) { const v = r.vi[k]; for (const u of adj[v]) maxJump = Math.max(maxJump, Math.abs(w[v] - w[u])); }
    const strong = Array.from(r.vw).filter(x => x > 0.5).length;
    if (r.layer === 1 && strong < 8) low.push(`${r.key}@${r.side}:${strong}`);
    if (maxJump > 0.7) hard.push(`${r.key}@${r.side}:${maxJump.toFixed(2)}`);
  });
  res.stats.coverage = { muscles: body.muscles.length, belowThreshold: low };
  res.stats.gradient = { hardEdged: hard };
  if (low.length) fail(`superficial muscles with too little skin coverage to be seen: ${low.join(' ')}`);
  if (hard.length) fail(`muscle tint has a hard edge on the surface (adjacent vertices differ by >0.7): ${hard.join(' ')}`);

  // ---- layer order along rays through the cut windows (rest pose, world space)
  fig.apply({});
  fig.root.updateMatrixWorld(true);
  body.skin.skeleton.update();
  const rc = new THREE.Raycaster(), V3 = THREE.Vector3;
  const layerOf = m => /^bones$/.test(m.name) || /^tendons$/.test(m.name) ? 3 : (body.inner.meshes.muscles.find(x => x.mesh === m) || { layer: 9 }).layer;
  const groupOf = (key, side) => body.inner.meshes.muscles.find(x => x.key === key && x.side === side && x.layer === 1);
  const centre = (grp) => new THREE.Box3().setFromObject(grp.mesh).getCenter(new V3());
  // rays along the axis of each cut window, from outside the body on the side the window opens: the order of layers is what the cutaway shows
  const rays = [
    { name: 'calf window, from behind: gastrocnemius > soleus > tibia', through: () => fig.point('knL', 0, -72, -24), dir: new V3(0, 0, 1), from: -400, expect: [1, 2, 3] },
    { name: 'thigh window, from the front: rectus femoris > vastus intermedius > femur', through: () => fig.point('thL', 2, -104, 36), dir: new V3(0, 0, -1), from: 400, expect: [1, 2, 3] },
    { name: 'hip, from behind through the overlap: gluteus maximus > medius', through: () => centre(groupOf('glute', 'L')).add(centre(body.inner.meshes.muscles.find(x => x.key === 'glutemed' && x.side === 'L'))).multiplyScalar(0.5), dir: new V3(0, 0, 1), from: -400, expect: [1, 2] }
  ];
  if (opt.profileSampling === 'distance') rays.push({
    name: 'distal upper arm, from the front: biceps > brachialis > humerus',
    through: () => fig.point('shL', 0, -100, 20), dir: new V3(0, 0, -1), from: 400, expect: [1, 2, 3]
  });
  res.stats.layers = {};
  rays.forEach(r => {
    const c = r.through(), o = new V3(c.x, c.y, c.z + r.from);
    rc.set(o, r.dir);
    const hits = rc.intersectObjects(body.inner.group.children, false).map(h => layerOf(h.object));
    const seq = hits.filter((x, i) => hits.indexOf(x) === i);
    res.stats.layers[r.name] = seq;
    for (let i = 1; i < seq.length; i++) if (seq[i] < seq[i - 1]) fail(`layer order along "${r.name}" is ${seq.join('>')}: a deep structure is in front of a superficial one`);
    r.expect.forEach(L => { if (seq.indexOf(L) < 0) fail(`ray "${r.name}" never meets layer ${L} (met ${seq.join(',') || 'nothing'}): the cutaway would not show that layer`); });
  });

  // ---- registration and deformation across poses
  const cfg = [
    { id: 'squat', ex: 'squat', t: 1.75 }, { id: 'curl', ex: 'curl', t: 1.35 }, { id: 'raise', ex: 'raise', t: 1.55 }, { id: 'hipthrust', ex: 'hipthrust', t: 1.5 }, { id: 'calfraise', ex: 'calfraise', t: 1.4 }
  ];
  const bindPos = body.skin.geometry.getAttribute('position').array.slice();
  const bindTriArea = (pos) => { const out = new Float32Array(nTri); for (let t = 0; t < nTri; t++) { const a = idx[t * 3] * 3, b = idx[t * 3 + 1] * 3, c = idx[t * 3 + 2] * 3;
    const ux = pos[b] - pos[a], uy = pos[b + 1] - pos[a + 1], uz = pos[b + 2] - pos[a + 2], vx = pos[c] - pos[a], vy = pos[c + 1] - pos[a + 1], vz = pos[c + 2] - pos[a + 2];
    out[t] = 0.5 * Math.hypot(uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx); } return out; };
  const area0 = bindTriArea(bindPos);
  res.stats.registration = {}; res.stats.deformation = {};
  cfg.forEach(c => {
    const st2 = T3.stage(null, { headless: true });
    const sc = T3.scene(st2, c.ex, { gender: g, reps: 2, profileSampling: opt.profileSampling });
    const f2 = sc.fig, v = sc.motion.at(c.t);
    Object.keys(f2.body.muscles).length;
    f2.apply(v); f2.root.updateMatrixWorld(true); f2.body.skin.skeleton.update();
    const sk = f2.body.skin, pa = sk.geometry.getAttribute('position'), cur = new Float32Array(n * 3), tmp = new V3();
    for (let i = 0; i < n; i++) { tmp.fromBufferAttribute(pa, i); sk.applyBoneTransform(i, tmp); cur[i * 3] = tmp.x; cur[i * 3 + 1] = tmp.y; cur[i * 3 + 2] = tmp.z; }
    // registration: the skin vertices a muscle tints must stay on that muscle as the body moves. Measured against the muscle's
    // volume posed by its own bone: the share of strongly-tinted vertices that end up more than 22 units outside it
    let worstDrift = 0, worstWho = '';
    f2.root.updateMatrixWorld(true);
    f2.body.muscles.forEach(r => {
      if (r.layer !== 1 || r.vi.length < 40) return;
      const bm = f2.bone[r.bone].matrixWorld, A0 = r.aLocal.clone().applyMatrix4(bm), B0 = r.bLocal.clone().applyMatrix4(bm), ab = B0.clone().sub(A0), L2 = ab.lengthSq();
      const rad = Math.max(r.spec.rw, r.spec.rt);
      let far = 0, strong = 0;
      for (let k = 0; k < r.vi.length; k++) {
        if (r.vw[k] < 0.6) continue; strong++;
        const i = r.vi[k], p3 = new V3(cur[i * 3], cur[i * 3 + 1], cur[i * 3 + 2]).applyMatrix4(f2.root.matrixWorld);
        const t = Math.max(0, Math.min(1, p3.clone().sub(A0).dot(ab) / L2)), cl = A0.clone().addScaledVector(ab, t);
        if (p3.distanceTo(cl) - rad > 22) far++;
      }
      const frac = strong ? far / strong : 0;
      if (frac > worstDrift) { worstDrift = frac; worstWho = r.key + '@' + r.side; }
    });
    res.stats.registration[c.id] = { worstShareOffMuscle: +worstDrift.toFixed(3), who: worstWho };
    if (worstDrift > 0.06) fail(`${c.id}: ${(worstDrift * 100).toFixed(0)}% of the skin tinted for ${worstWho} lies >22 units off the posed muscle (highlight drift)`);
    // deformation: area ratio against the bind pose, ignoring the rigid-looking noise of tiny triangles
    const area = bindTriArea(cur), ratios = [];
    for (let t = 0; t < nTri; t++) if (area0[t] > 3) ratios.push(area[t] / area0[t]);
    ratios.sort((a, b) => a - b);
    const q = p => ratios[Math.min(ratios.length - 1, Math.floor(p * ratios.length))];
    res.stats.deformation[c.id] = { p001: +q(0.001).toFixed(2), p999: +q(0.999).toFixed(2), min: +ratios[0].toFixed(2), max: +ratios[ratios.length - 1].toFixed(2) };
    const stretchLimit = opt.profileSampling === 'distance' ? 4.0 : 4.5;
    if (q(0.999) > stretchLimit) fail(`${c.id}: 0.1% of skin triangles stretch to ${q(0.999).toFixed(1)}x their bind area (limit ${stretchLimit}; a tear at a joint)`);
    if (q(0.001) < 0.05) fail(`${c.id}: 0.1% of skin triangles collapse to ${q(0.001).toFixed(2)}x their bind area (a crush at a joint)`);
  });

  // ---- state language: the three kinds of colour stay apart
  const dist = (a, b) => { const A1 = new THREE.Color(a), B1 = new THREE.Color(b); return Math.hypot(A1.r - B1.r, A1.g - B1.g, A1.b - B1.b); };
  const L = A.look, C = T3.colors;
  const st3 = { skinVsInnerMuscle: dist(C.skin, L.muscle), activeVsInnerMuscle: dist(C.prime, L.muscle), skinVsBone: dist(C.skin, L.bone), roleSecondVsTendon: dist(C.second, L.tendon) };
  res.stats.stateLanguage = Object.fromEntries(Object.entries(st3).map(([k, v]) => [k, +v.toFixed(2)]));
  if (st3.skinVsInnerMuscle < 0.4) fail('external skin and internal muscle colours are too close to tell apart');
  if (st3.activeVsInnerMuscle < 0.28) fail('an active (coral) muscle on the surface is too close to the rosewood of internal muscle');
  if (opt.profileSampling === 'distance') {
    const posedRoot = pose => {
      fig.apply(pose); fig.root.updateMatrixWorld(true); body.skin.skeleton.update();
      const inverse = fig.root.matrixWorld.clone().invert(), point = new THREE.Vector3();
      const positions = new Float64Array(n * 3), attr = body.geo.getAttribute('position');
      for (let i = 0; i < n; i++) {
        point.fromBufferAttribute(attr, i);
        body.skin.applyBoneTransform(i, point).applyMatrix4(body.skin.matrixWorld).applyMatrix4(inverse);
        point.toArray(positions, i * 3);
      }
      return positions;
    };
    // Measure the actual projected skin, including unmasked joint masses.
    res.stats.shoulderContour = {};
    for (const [name, pose] of [['authoredRest', T3.DEFAULT_POSE], ['neutral', {}]]) {
      const positions = posedRoot(pose), contours = {};
      for (const [side, sign] of [['L', 1], ['R', -1]]) {
        const contour = shoulderContour(positions, idx, fig.spec, sign);
        contours[side] = contour;
        if (contour.samples < 20 || contour.crestRise > 2.5) {
          fail(`${name} ${side}: shoulder crest rebounds ${contour.crestRise.toFixed(2)} units above the sloping roof (limit 2.5; ${contour.samples} samples)`);
        }
      }
      res.stats.shoulderContour[name] = contours;
      // Front flank from under the armpit to the waistband, then the hip below the band: a slab-ended muscle or a flat
      // tube end shows as a sudden step in width.
      let flankStep = 0, flankAt = null, flankRows = 0, previous = null;
      const flankRow = (y, skip) => {
        const torsoSpan = horizontalSilhouette(positions, idx, y).find(span => span[0] <= 0 && span[1] >= 0);
        const half = torsoSpan && Math.min(torsoSpan[1], -torsoSpan[0]);
        if (!half || skip(half)) { previous = null; return; }
        if (previous !== null && Math.abs(previous - half) > flankStep) { flankStep = Math.abs(previous - half); flankAt = y; }
        previous = half; flankRows++;
      };
      for (let y = fig.spec.shy - 60; y >= A.CLOTH.waist + 8; y -= 5) flankRow(y, half => half > fig.spec.shx);
      previous = null;
      // Hip rows only where the hands are known to clear the body (neutral clearance below); the authored rest touches it.
      if (name === 'neutral') for (let y = A.CLOTH.waist - 8; y >= -20; y -= 5) flankRow(y, () => false);
      res.stats.flank = res.stats.flank || {};
      res.stats.flank[name] = { maxStepPer5: +flankStep.toFixed(2), at: flankAt, rows: flankRows };
      if (flankRows < 8 || flankStep > 5) {
        fail(`${name}: the torso flank steps ${flankStep.toFixed(2)} units in 5 at y=${flankAt} (limit 5; ${flankRows} rows): a ledge on the flank or hip`);
      }
      if (name !== 'neutral') continue;
      res.stats.neutralClearance = {};
      for (const [region, y, minimum] of [
        ['upperArm', fig.spec.shy - 80, 3], ['lowerArm', fig.spec.shy - 105, 15],
        ['palm', fig.spec.shy - 134 - 106 - 22, 12]
      ]) {
        const spans = horizontalSilhouette(positions, idx, y);
        const torsoSpan = spans.find(span => span[0] <= 0 && span[1] >= 0);
        if (!torsoSpan) { fail(`neutral silhouette: no torso at ${region}`); continue; }
        const left = spans.find(span => span[0] > torsoSpan[1] + 1e-3);
        const right = spans.slice().reverse().find(span => span[1] < torsoSpan[0] - 1e-3);
        const gaps = { L: left ? left[0] - torsoSpan[1] : 0,
          R: right ? torsoSpan[0] - right[1] : 0, minimum };
        res.stats.neutralClearance[region] = gaps;
        if (gaps.L < minimum || gaps.R < minimum) {
          fail(`neutral silhouette: ${region} is glued to the torso (${gaps.L.toFixed(2)}/${gaps.R.toFixed(2)} gap; minimum ${minimum})`);
        }
      }
    }
    // Engineering relief/coverage floors in rig units (head = 100), not clinical measurements.
    res.stats.sheetSurface = {};
    for (const [key, limit] of [['lat', 12], ['abs', 8]]) {
      for (const side of ['L', 'R']) {
        const vertices = new Set();
        body.muscles.filter(m => m.key === key && m.side === side).forEach(m => {
          m.vi.forEach((v, i) => { if (m.vw[i] >= 0.6) vertices.add(v); });
        });
        let relief = -Infinity, minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        vertices.forEach(v => {
          const x = data.mesh.pos[v * 3], y = data.mesh.pos[v * 3 + 1], z = data.mesh.pos[v * 3 + 2];
          relief = Math.max(relief, torso.f(x, y, z));
          minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y);
        });
        res.stats.sheetSurface[key + '@' + side] = { vertices: vertices.size, maxCoreDistance: relief, width: maxX - minX, height: maxY - minY };
        if (!vertices.size || relief > limit) fail(`${key}@${side}: surface relief ${relief.toFixed(2)} exceeds ${limit} units above its supporting torso`);
        if (key === 'lat' && (maxX - minX < 25 || maxY - minY < 80)) fail(`lat@${side}: the surface footprint is too small to read as a broad back muscle`);
      }
    }

    fig.apply({ shL: 0, shR: 0, elL: 0, elR: 0 });
    const restPosition = body.geo.getAttribute('position').array.slice();
    fig.apply({ shL: 175, shR: 175, elL: 0, elR: 0 });
    let elevationBulge = 0;
    body.geo.getAttribute('position').array.forEach((v, i) => { elevationBulge = Math.max(elevationBulge, Math.abs(v - restPosition[i])); });
    // Reported only since 1.6.0: any morph change on elevation. The gate is latInflation (girdleGates), which forbids lat skin pushed out
    // along its normal through the morph or the bones and allows the shoulder's own arc corrective and girdle motion.
    res.stats.elevationOnlyBulge = elevationBulge;

    const sharedNormals = data.normals.slice();
    fig.apply({ elL: 140, elR: 140 });
    const normal = body.geo.getAttribute('normal').array, expectedGeometry = body.geo.clone();
    expectedGeometry.computeVertexNormals();
    const expectedNormal = expectedGeometry.getAttribute('normal').array;
    let normalDelta = 0;
    normal.forEach((v, i) => { normalDelta = Math.max(normalDelta, Math.abs(v - expectedNormal[i])); });
    expectedGeometry.dispose();
    res.stats.morphNormalDelta = normalDelta;
    if (normalDelta > 1e-6) fail(`morph normals are stale: maximum component error ${normalDelta}`);
    const ownNormals = normal.slice();
    const peer = stage.tibi({ gender: g, id: 'peer', profileSampling: 'distance' });
    peer.apply({ 'peer.elL': 20, 'peer.elR': 80 });
    let sharedDelta = 0, peerDelta = 0;
    data.normals.forEach((v, i) => { sharedDelta = Math.max(sharedDelta, Math.abs(v - sharedNormals[i])); });
    normal.forEach((v, i) => { peerDelta = Math.max(peerDelta, Math.abs(v - ownNormals[i])); });
    res.stats.normalIsolation = { sharedDelta, peerDelta };
    if (sharedDelta || peerDelta) fail('normal updates leak into cached data or another figure');

    res.stats.surfaceColour = {};
    for (const role of [1, 2, 3]) {
      const allRoles = {}, full = { elL: 100, elR: 100 };
      body.muscles.forEach(m => { allRoles[m.key] = role; full['act.' + m.key] = 1; });
      fig.roles(allRoles); fig.apply(full);
      res.stats.surfaceColour[role] = {};
      for (const name of ['color', 'colorC']) {
        let minimum = Infinity, maximum = -Infinity, nonFinite = 0;
        body.geo.getAttribute(name).array.forEach(v => {
          if (!Number.isFinite(v)) nonFinite++;
          minimum = Math.min(minimum, v); maximum = Math.max(maximum, v);
        });
        res.stats.surfaceColour[role][name] = { minimum, maximum, nonFinite };
        if (nonFinite || minimum < -1e-6 || maximum > 1 + 1e-6) fail(`${name}, role ${role}: overlapping activation leaves the linear RGB gamut (${minimum}..${maximum})`);
      }
    }
    knownLimitGates(fig, body, data, res, fail, posedRoot, idx);
    if (data.hasTop) {
      let leaked = 0, maxArmWeight = 0;
      for (let v = 0; v < n; v++) {
        if (data.topMask[v] <= 0.1) continue;
        let arm = 0;
        for (let j = 0; j < 4; j++) if (/^(sh|el|hand)[LR]$/.test(body.skin.skeleton.bones[data.skinIndex[v * 4 + j]].name)) arm += data.skinWeight[v * 4 + j];
        maxArmWeight = Math.max(maxArmWeight, arm);
        if (arm > 0.5) leaked++;
      }
      res.stats.topOwnership = { leakedVertices: leaked, maxArmWeight };
      if (leaked) fail(`top colour is attached to ${leaked} arm-dominated vertices instead of the torso`);
    }
  } else {
    res.notes.push('Legacy is a compatibility reference: integrated-surface, brachialis, morph-normal and colour-compositing gates apply to distance only.');
  }
  // Same input must recover the exact arrays, even after visiting a nearby pose in the old rounded cache bucket.
  fig.roles({ biceps: 3 });
  const target = { elL: 100, elR: 100, 'act.biceps': 0.5 };
  fig.apply(target);
  const names = ['position', 'normal', 'color', 'colorC'];
  const expected = names.map(name => body.geo.getAttribute(name).array.slice());
  fig.apply({});
  fig.apply({ elL: 100.01, elR: 100.01, 'act.biceps': 0.50001 });
  fig.apply(target);
  res.stats.seekOrder = {};
  names.forEach((name, i) => {
    const actual = body.geo.getAttribute(name).array;
    let delta = 0;
    for (let j = 0; j < actual.length; j++) delta = Math.max(delta, Math.abs(actual[j] - expected[i][j]));
    res.stats.seekOrder[name] = delta;
    if (delta > 0) fail(`${name} differs by ${delta} at the same pose after a seek (history-dependent skin cache)`);
  });
  return res;
}

const results = genders.map(check);
if (opt.json) console.log(JSON.stringify(results, null, 1));
else results.forEach(r => {
  console.log(`\n${r.failures.length ? 'FAIL' : 'ok  '} anatomy (${r.gender})`);
  Object.keys(r.stats).forEach(k => console.log(`     ${k.padEnd(14)} ${JSON.stringify(r.stats[k])}`));
  r.notes.forEach(n => console.log('     LIMIT:', n));
  r.failures.forEach(f => console.log('     FAIL:', f));
});
// exitCode, not exit(): a large --json report written to a pipe is flushed asynchronously and exit() could cut it off
process.exitCode = results.some(r => r.failures.length) ? 1 : 0;
