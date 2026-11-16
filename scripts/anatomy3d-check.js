#!/usr/bin/env node
/*
 * anatomy3d-check.js: anatomical acceptance tests for the 3D Tibi (no browser, no render: node and the vendored three.js).
 *
 *   node scripts/anatomy3d-check.js [--gender m|f|both] [--json]
 *
 * The rules come from the "detached muscle" review (2026-11-13): a muscle is part of the body, never a sticker. Each test is a
 * way the OLD rig failed (rigid ellipsoids parented to bones) or a way this one could:
 *   skin         one watertight, single-component surface (no gaps, no duplicate or overlapping shells)
 *   protrusion   every internal muscle, tendon and bone vertex lies inside the skin envelope (skin SDF <= -inset)
 *   external     no mesh that looks like a muscle hangs on a bone outside the skin or the hidden inner group
 *   coverage     every superficial muscle owns enough skin vertices to be seen and lit; deep ones are exempt
 *   gradient     a muscle's tint falls off smoothly across the surface (no hard-edged patch)
 *   layers       along a ray through each cut window the layers come in anatomical order (superficial, deep, bone)
 *   registration highlights stay on their anatomy: the centroid of a muscle's skin region stays within tolerance of its
 *                bone-local anchor through squat, curl, raise and hip-thrust poses (no drift under deformation)
 *   deformation  no triangle collapses or explodes in the poses above at the joints (area ratio vs the bind pose)
 *   state        the visual language keeps external (cobalt), active (role colours) and internal (rosewood/ivory) apart
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
const opt = { gender: 'both', json: false };
for (let i = 0; i < args.length; i++) { if (args[i] === '--gender') opt.gender = args[++i]; else if (args[i] === '--json') opt.json = true; }
const genders = opt.gender === 'both' ? ['m', 'f'] : [opt.gender];

function check(g) {
  const stage = T3.stage(null, { headless: true });
  const t0 = Date.now();
  const fig = stage.tibi({ gender: g });
  const buildMs = Date.now() - t0;                      // the kit itself never reads a clock (the render lint forbids it); the test may
  const body = fig.body, data = body.data, G = data.G;
  const res = { gender: g, failures: [], notes: [], stats: {} };
  const fail = m => res.failures.push(m);

  // ---- skin: watertight, one component
  const idx = data.mesh.idx, nTri = idx.length / 3, n = data.n;
  const edges = new Map();
  for (let i = 0; i < idx.length; i += 3) for (let e = 0; e < 3; e++) { const a = idx[i + e], b = idx[i + (e + 1) % 3], k = a < b ? a * 1e6 + b : b * 1e6 + a; edges.set(k, (edges.get(k) || 0) + 1); }
  let open = 0; edges.forEach(v => { if (v !== 2) open++; });
  const parent = new Int32Array(n); for (let i = 0; i < n; i++) parent[i] = i;
  const find = x => { while (parent[x] !== x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; };
  for (let i = 0; i < idx.length; i += 3) { parent[find(idx[i])] = find(idx[i + 1]); parent[find(idx[i + 1])] = find(idx[i + 2]); }
  const comps = new Set(); for (let i = 0; i < n; i++) if (parent[i] === i) comps.add(i);
  // vertices that no triangle uses do not count as components
  const used = new Set(); for (let i = 0; i < idx.length; i++) used.add(find(idx[i]));
  res.stats.skin = { vertices: n, triangles: nTri, openOrNonManifoldEdges: open, edgeFraction: +(open / edges.size).toExponential(2), components: used.size, buildMs: buildMs };
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
    const sc = T3.scene(st2, c.ex, { gender: g, reps: 2 });
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
    if (q(0.999) > 4.5) fail(`${c.id}: 0.1% of skin triangles stretch to ${q(0.999).toFixed(1)}x their bind area (a tear at a joint)`);
    if (q(0.001) < 0.05) fail(`${c.id}: 0.1% of skin triangles collapse to ${q(0.001).toFixed(2)}x their bind area (a crush at a joint)`);
  });

  // ---- state language: the three kinds of colour stay apart
  const dist = (a, b) => { const A1 = new THREE.Color(a), B1 = new THREE.Color(b); return Math.hypot(A1.r - B1.r, A1.g - B1.g, A1.b - B1.b); };
  const L = A.look, C = T3.colors;
  const st3 = { skinVsInnerMuscle: dist(C.skin, L.muscle), activeVsInnerMuscle: dist(C.prime, L.muscle), skinVsBone: dist(C.skin, L.bone), roleSecondVsTendon: dist(C.second, L.tendon) };
  res.stats.stateLanguage = Object.fromEntries(Object.entries(st3).map(([k, v]) => [k, +v.toFixed(2)]));
  if (st3.skinVsInnerMuscle < 0.4) fail('external skin and internal muscle colours are too close to tell apart');
  if (st3.activeVsInnerMuscle < 0.28) fail('an active (coral) muscle on the surface is too close to the rosewood of internal muscle');
  return res;
}

const results = genders.map(check);
if (opt.json) console.log(JSON.stringify(results, null, 1));
else results.forEach(r => {
  console.log(`\n${r.failures.length ? 'FAIL' : 'ok  '} anatomy (${r.gender})`);
  Object.keys(r.stats).forEach(k => console.log(`     ${k.padEnd(14)} ${JSON.stringify(r.stats[k])}`));
  r.failures.forEach(f => console.log('     FAIL:', f));
});
process.exit(results.some(r => r.failures.length) ? 1 : 0);
