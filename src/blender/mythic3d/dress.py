"""
Dress, ornament and hair for the 3D mythic figures, fitted to the skin with ray casts.

Ornament is data (figure-design.md section 3.6): crown, kundala, haar, keyura, kankana, sacred thread and
girdle are separate builders, so a figure's jewellery is a list, not a drawing.
"""

import math

import numpy as np
from mathutils import Matrix, Vector

from .core import (
    V,
    catmull,
    ellipsoid,
    grid_surface,
    join,
    lathe,
    link,
    mesh_obj,
    sweep,
    transport_frames,
)


# ---------------------------------------------------------------------- body sections
def support(fit, z, n=96, center=(0.0, 0.0), reach=0.9, keep=None):
    """Convex support radius h(theta) of the skin's cross-section at height z (rays from outside).
    keep(point) -> bool filters hits (e.g. ignore a raised arm)."""
    hits = []
    for i in range(n):
        th = 2 * math.pi * i / n
        d = Vector((math.cos(th), math.sin(th), 0.0))
        o = Vector((center[0], center[1], z)) + d * reach
        hit = fit.tree.ray_cast(o, -d, reach * 1.6)
        if hit[0] is not None and (keep is None or keep(hit[0])):
            hits.append((hit[0].x - center[0], hit[0].y - center[1]))
    if not hits:
        return np.zeros(n)
    H = np.array(hits)
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    dirs = np.stack([np.cos(th), np.sin(th)], 1)
    return (H @ dirs.T).max(0)


def skirt(name, fit, mat, z_top, z_hem, ease=0.012, flare=0.12, folds=11, fold_amp=0.012, rows=30, cols=96,
          center=(0.0, 0.0), wind=(0.0, 0.0), thickness=0.005, hem_wave=0.01, keep=None, seed=0, min_r=0.0,
          front_open=None, core=(0.3, 0.24)):
    """A wrapped garment from z_top down to z_hem that drapes over the skin: each section is the convex
    support of the body below it plus ease, flaring as it falls, with vertical folds deepening to the hem.
    core (half-width x, half-depth y): only skin inside this box counts (hands and weapons at the hip do not)."""
    if keep is None:
        def keep(p):
            return abs(p.x - center[0]) < core[0] and abs(p.y - center[1]) < core[1]
    zs = np.linspace(z_top, z_hem, rows)
    th = np.linspace(0, 2 * np.pi, cols, endpoint=False)
    prev = None
    rings = []
    for i, z in enumerate(zs):
        h = support(fit, z, cols, center, keep=keep) + ease
        h = np.maximum(h, min_r)
        if prev is not None:
            dz = zs[i - 1] - z
            h = np.maximum(h, prev + flare * dz)
            h = 0.5 * h + 0.25 * (np.roll(h, 1) + np.roll(h, -1))
        prev = h
        t = i / (rows - 1)
        ph = 0.6 * math.sin(seed + i * 0.21)
        fold = fold_amp * t ** 1.2 * (0.5 + 0.5 * np.sin(folds * th + ph + 1.3 * np.sin(3 * th + seed)))
        r = h + fold
        zz = z + (hem_wave * math.sin(0.0) if False else 0.0)
        ring = []
        for j in range(cols):
            wz = 0.0
            if i == rows - 1 or t > 0.9:
                wz = hem_wave * math.sin(folds * th[j] + ph) * (t - 0.9) * 10 if t > 0.9 else 0.0
            ring.append(Vector((center[0] + r[j] * math.cos(th[j]) + wind[0] * t * t,
                                center[1] + r[j] * math.sin(th[j]) + wind[1] * t * t, zz + wz)))
        rings.append(ring + [ring[0]])
    ob = grid_surface(name, rings, mat, thickness)
    return ob


def fall(name, fit, mat, top, bottom, width=0.11, pleats=5, depth=0.012, lift=0.012, n=16):
    """The pleated front fall of a dhoti (kacha), hanging from the girdle in front of the skirt."""
    top, bottom = V(top), V(bottom)
    rows = []
    for i in range(n):
        t = i / (n - 1)
        c = top.lerp(bottom, t)
        loc, nrm = fit.nearest(c)
        c = c + Vector((0, -1, 0)) * (lift + 0.01 * t)
        w = width * (0.7 + 0.5 * t)
        row = []
        for k in range(2 * pleats + 1):
            u = k / (2 * pleats) - 0.5
            row.append(c + Vector((u * w, -depth * (k % 2) * (0.6 + 0.6 * t), 0)))
        rows.append(row)
    return grid_surface(name, rows, mat, 0.004)


def band(name, fit, mat, center, axis, width=0.03, thick=0.006, offset=0.004, n=64, rope=0, beads=None):
    """A ring hugging the skin around `axis`: girdle, belly band, armband (keyura), bracelet (kankana).
    rope > 0 twists an oval profile (a twisted fibre girdle); beads=(material, radius, count) adds jewels."""
    pts = fit.ring(center, axis, n, offset + thick / 2)
    a = V(axis).normalized()
    if rope:
        prof = [(math.cos(2 * math.pi * k / 10) * 1.0, math.sin(2 * math.pi * k / 10) * 0.55) for k in range(10)]
        ob = sweep(name, pts, (width / 2, width / 2), material=mat, n_per=3, closed=True, profile=prof, twist=rope, up=tuple(a))
    else:
        prof = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        prof = [(x * 0.5 * thick / (width / 2), y) for (x, y) in prof]
        prof = [(math.copysign(abs(x), x), y) for x, y in prof]
        ob = _loop_band(name, pts, a, width, thick, mat)
    objs = [ob]
    if beads:
        bmat, br, count = beads
        step = max(1, len(pts) // count)
        for k in range(0, len(pts), step):
            objs.append(ellipsoid(name + "-gem", pts[k] + (pts[k] - V(center)).normalized() * thick * 0.6, (br, br, br), None, bmat, 12))
        ob = join(objs, name)
    return ob


def _loop_band(name, pts, axis, width, thick, mat):
    """A flat band (width along the axis) round a closed loop of points."""
    n = len(pts)
    c = sum(pts, Vector()) / n
    verts, faces = [], []
    for p in pts:
        out = (p - c)
        out = (out - axis * out.dot(axis)).normalized()
        for (u, w) in ((-0.5, 0.0), (0.5, 0.0), (0.5, 1.0), (-0.5, 1.0)):
            verts.append(p + axis * (u * width) + out * (w * thick))
    for i in range(n):
        j = (i + 1) % n
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append((i * 4 + k, i * 4 + k2, j * 4 + k2, j * 4 + k))
    return mesh_obj(name, verts, faces, mat)


def cord(name, fit, mat, pts, r=0.0025, offset=None, n_per=8):
    """A thread on the skin (yajnopavita, munja grass, a strap edge): projected, lifted by its radius."""
    path = fit.onto(catmull(pts, n_per), (offset if offset is not None else r))
    return sweep(name, path, r, sides=8, material=mat, n_per=1)


def strap(name, fit, mat, pts, width=0.035, thick=0.005, n_per=8):
    """A flat strap lying on the skin (the quiver strap), its width in the surface."""
    path = catmull(pts, n_per)
    on = []
    nrm = []
    for p in path:
        loc, nn = fit.nearest(p)
        on.append(loc + nn * (thick * 0.6))
        nrm.append(nn)
    T, _, _ = transport_frames(on)
    verts, faces = [], []
    for i, p in enumerate(on):
        side = T[i].cross(nrm[i]).normalized()
        for (u, w) in ((-0.5, 0), (0.5, 0), (0.5, 1), (-0.5, 1)):
            verts.append(p + side * (u * width) + nrm[i] * (w * thick))
    for i in range(len(on) - 1):
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append((i * 4 + k, i * 4 + k2, (i + 1) * 4 + k2, (i + 1) * 4 + k))
    return mesh_obj(name, verts, faces, mat)


def beads_on(name, fit, mat, pts, r=0.006, gap=1.15, offset=None, big=None):
    """A string of beads along a curve on the skin (pearl haar, rudraksha mala). big=(every, mat, r)."""
    path = fit.onto(catmull(pts, 12), offset if offset is not None else r)
    out = []
    acc = 0.0
    last = path[0]
    k = 0
    for p in path:
        acc += (p - last).length
        last = p
        if acc >= 2 * r * gap or not out:
            acc = 0.0
            if big and k % big[0] == 0:
                out.append(ellipsoid(name, p, (big[2],) * 3, None, big[1], 12))
            else:
                out.append(ellipsoid(name, p, (r, r, r), None, mat, 10))
            k += 1
    return join(out, name)


def hoop(name, mat, center, axis, r=0.02, tube=0.004):
    """An earring or ring (torus) about `axis`."""
    a = V(axis).normalized()
    u = a.orthogonal().normalized()
    w = a.cross(u)
    pts = [V(center) + (u * math.cos(2 * math.pi * i / 32) + w * math.sin(2 * math.pi * i / 32)) * r for i in range(32)]
    return sweep(name, pts, tube, sides=10, material=mat, n_per=1, closed=True)


# ---------------------------------------------------------------------- crowns and hair
def kirita(name, look, at, rot, H, tall=1.0, gem="#B8282E", gem2="#1F7A55"):
    """Kirita-makuta: a tall tiered crown, gold, with a jewelled band and a lotus-bud finial."""
    gold = look.gold()
    prof = [(0.35, 0.0), (0.37, 0.02), (0.36, 0.1), (0.31, 0.12), (0.3, 0.2), (0.26, 0.23), (0.25, 0.32), (0.2, 0.35),
            (0.19, 0.44), (0.14, 0.47), (0.12, 0.55), (0.07, 0.6), (0.05, 0.66), (0.0, 0.7)]
    prof = [(r * H, z * H * tall) for r, z in prof]
    crown = lathe(name, prof, 48, gold, radial=lambda t, i: 1.0 + (0.04 if i in (2, 6, 10) else 0.0) * math.cos(8 * t), ry=0.92)
    crown.data.transform(rot.to_4x4())
    crown.data.transform(Matrix.Translation(V(at)))
    objs = [crown]
    ruby, emer = look.gem("ruby", gem), look.gem("emerald", gem2)
    for k in range(10):
        a = 2 * math.pi * k / 10
        p = V(at) + rot @ Vector((math.cos(a) * 0.365 * H, math.sin(a) * 0.365 * H * 0.92, 0.06 * H))
        objs.append(ellipsoid(name + "-gem", p, (0.03 * H,) * 3, None, ruby if k % 2 else emer, 12))
    objs.append(ellipsoid(name + "-gem", V(at) + rot @ Vector((0, -0.31 * H, 0.27 * H * tall)), (0.045 * H, 0.03 * H, 0.06 * H), rot, ruby, 14))
    return join(objs, name)


def coil_stack(name, mat, base, rot, radii, dz, tube, wobble=0.0, seed=0):
    """Stacked rings of matted hair (jata): Rama's knot, Shiva's jata-makuta."""
    objs = []
    z = 0.0
    for i, r in enumerate(radii):
        pts = []
        for k in range(28):
            a = 2 * math.pi * k / 28
            rr = r * (1 + wobble * math.sin(3 * a + i * 1.7 + seed))
            pts.append(V(base) + rot @ Vector((rr * math.cos(a), rr * math.sin(a), z + wobble * 0.3 * r * math.sin(2 * a + i))))
        objs.append(sweep(name, pts, tube * (1 - 0.15 * i / max(1, len(radii))), sides=10, material=mat, n_per=1, closed=True))
        z += dz
    return join(objs, name), z


def lock(name, mat, pts, r0, r1=0.002, sides=8):
    """A tapered lock of hair along a curve."""
    n = len(pts)
    radii = [r0 + (r1 - r0) * (i / (n - 1)) ** 0.9 for i in range(n)]
    return sweep(name, pts, radii, sides=sides, material=mat, n_per=6)


def curls(name, mat, fit, body, region, r=0.006, spacing=1.9, ushnisha=None):
    """Tiny tight curls over the hair cap (the Jina), larger snail-shells (the Buddha).
    region(q) -> bool on head-space points; ushnisha=(centre head-space, ext) adds the cranial mound."""
    H = body.H
    c, R = body.frames["head"]
    out = []
    n_lat = int(math.pi * 0.45 * H / (spacing * r)) + 4
    for i in range(n_lat):
        lat = math.pi * (0.02 + 0.6 * i / (n_lat - 1))
        ring = max(1, int(2 * math.pi * math.sin(lat) * 0.4 * H / (spacing * r)))
        for k in range(ring):
            lon = 2 * math.pi * (k + 0.5 * (i % 2)) / ring
            d = Vector((math.sin(lat) * math.cos(lon), math.sin(lat) * math.sin(lon), math.cos(lat)))
            q = d * 0.42
            if not region(q):
                continue
            p = c + R @ (q * H * 1.4)
            hit = fit.tree.ray_cast(p, (c - p).normalized(), H)
            if hit[0] is None:
                continue
            out.append(ellipsoid(name, hit[0] + hit[1] * r * 0.55, (r, r, r * 0.8), None, mat, 10))
    if ushnisha:
        qc, ext = ushnisha
        cc = c + R @ (V(qc) * H)
        out.append(ellipsoid(name + "-ush", cc, tuple(e * H for e in ext), R, mat, 32))
        for i in range(5):
            lat = math.pi * 0.42 * i / 4
            ring = max(1, int(2 * math.pi * math.sin(lat) * ext[0] * H / (spacing * r)))
            for k in range(ring):
                lon = 2 * math.pi * k / ring
                d = Vector((math.sin(lat) * math.cos(lon) * ext[0], math.sin(lat) * math.sin(lon) * ext[1], math.cos(lat) * ext[2]))
                out.append(ellipsoid(name, cc + R @ (d * H * 1.02), (r, r, r * 0.8), None, mat, 10))
    return join(out, name)


def helmet(name, look, body, crest="#B8322A"):
    """Attic helmet: a bronze bowl over the cranium, a brow band, raised cheek guards, a neck guard and
    three red crests (the Varvakeion Athena), the centre one sweeping back."""
    H = body.H
    c, R = body.frames["head"]
    bronze = look.gold("helmet", "#C9973F", 0.3)
    red = look.cloth("crest", crest, rough=0.85)
    prof = [(0.0, 0.47), (0.12, 0.465), (0.22, 0.44), (0.3, 0.39), (0.36, 0.3), (0.39, 0.2), (0.4, 0.1), (0.405, 0.05), (0.41, 0.02)]
    bowl = lathe(name, [(r * H * 1.08, z * H * 1.04) for r, z in prof], 56, bronze, ry=1.1, caps=False)
    bowl.modifiers.new("solid", "SOLIDIFY").thickness = 0.006
    bowl.data.transform((Matrix.Translation(c) @ R.to_4x4() @ Matrix.Translation(Vector((0, 0.04 * H, 0.02 * H)))))
    objs = [bowl]
    brow = sweep(name + "-brow", [c + R @ Vector((math.sin(a) * 0.445 * H, -math.cos(a) * 0.5 * H, 0.08 * H + 0.03 * H * math.cos(a)))
                                  for a in np.linspace(-1.9, 1.9, 24)], 0.018 * H, sides=8, material=bronze, n_per=2)
    objs.append(brow)
    for sx in (-1, 1):
        # Cheek guards raised against the bowl (the Varvakeion Athena), lying flat on its sides.
        g = [c + R @ Vector((sx * 0.445 * H, (-0.22 + 0.16 * t) * H, (0.1 + 0.16 * t) * H)) for t in np.linspace(0, 1, 5)]
        objs.append(sweep(name + "-cheek", g, (0.012 * H, 0.06 * H), sides=10, material=bronze, n_per=3, up=tuple(R @ Vector((1, 0, 0)))))
    neck = [c + R @ Vector((math.sin(a) * 0.4 * H, math.cos(a) * 0.42 * H, -0.05 * H)) for a in np.linspace(-1.2, 1.2, 16)]
    objs.append(sweep(name + "-neckguard", neck, (0.02 * H, 0.07 * H), sides=8, material=bronze, n_per=2))
    crest_pts = [c + R @ Vector((0, (-0.25 + 0.75 * t) * H, (0.5 + 0.32 * math.sin(math.pi * min(1, t * 1.15)) - 0.1 * t) * H)) for t in np.linspace(0, 1, 10)]
    objs.append(sweep(name + "-crest", crest_pts, [(0.03 * H, 0.18 * H * (0.5 + 0.5 * math.sin(math.pi * t))) for t in np.linspace(0.05, 0.95, 10)],
                      sides=12, material=red, n_per=4, up=tuple(R @ Vector((1, 0, 0)))))
    for sx in (-1, 1):
        side = [c + R @ Vector((sx * 0.13 * H, (-0.1 + 0.5 * t) * H, (0.46 + 0.1 * math.sin(math.pi * t)) * H)) for t in np.linspace(0, 1, 8)]
        objs.append(sweep(name + "-crest2", side, [(0.02 * H, 0.08 * H * (0.4 + 0.6 * math.sin(math.pi * t))) for t in np.linspace(0.05, 0.95, 8)],
                          sides=10, material=red, n_per=3, up=tuple(R @ Vector((1, 0, 0)))))
    return join(objs, name)


def slouch_hat(name, look, body, tilt=8.0):
    """Odin's broad slouched hat (Sithhott): a wide drooping felt brim and a low round crown."""
    H = body.H
    c, R = body.frames["head"]
    felt = look.cloth("felt", "#3A2E28", rough=0.9, sheen=0.2)
    Rt = R @ Matrix.Rotation(math.radians(-tilt), 3, "X")
    prof = [(0.0, 0.42), (0.16, 0.41), (0.27, 0.36), (0.33, 0.26), (0.36, 0.14), (0.4, 0.11), (0.6, 0.09), (0.78, 0.04), (0.84, 0.0)]
    hat = lathe(name, [(r * H, z * H) for r, z in prof], 64, felt, radial=lambda t, i: 1.0 + (0.05 * math.sin(2 * t) if i > 5 else 0.0), ry=0.96, caps=False)
    hat.modifiers.new("solid", "SOLIDIFY").thickness = 0.008
    hat.data.transform(Matrix.Translation(c) @ Rt.to_4x4() @ Matrix.Translation(Vector((0, 0.03 * H, 0.17 * H))))
    bandp = [c + Rt @ Vector((math.cos(a) * 0.365 * H, math.sin(a) * 0.35 * H + 0.03 * H, 0.31 * H)) for a in np.linspace(0, 2 * math.pi, 33)[:-1]]
    hb = sweep(name + "-band", bandp, (0.012 * H, 0.03 * H), sides=6, material=look.solid("hatband", "#2A201C", 0.7), n_per=1, closed=True, up=tuple(Rt @ Vector((0, 0, 1))))
    return join([hat, hb], name)


def cloak(name, fit, mat, neck_c, z_top, z_hem, r_top=0.2, r_hem=0.62, span=150.0, wind=(0.0, 0.0), folds=9, rows=30,
          cols=60, thickness=0.008, clear=0.03, front_y=0.0, seed=0, keep=None):
    """A cloak from the shoulders to the hem, spread behind the body; never inside the skin.
    keep(point) -> bool drops skin the cloak should not follow (a raised arm)."""
    zs = np.linspace(z_top, z_hem, rows)
    angs = np.radians(np.linspace(-span, span, cols))          # 0 = straight behind (+Y)
    rings = []
    for i, z in enumerate(zs):
        t = i / (rows - 1)
        h = support(fit, z, 96, (neck_c[0], neck_c[1]), keep=keep)
        ring = []
        for j, a in enumerate(angs):
            th = math.pi / 2 + a                                 # +Y is behind
            k = int(round((th % (2 * math.pi)) / (2 * math.pi) * 96)) % 96
            base = r_top + (r_hem - r_top) * t ** 0.9
            r = max(base, h[k] + clear) + 0.04 * t * math.sin(folds * a + seed + 2 * t) * (0.4 + 0.6 * t)
            x = neck_c[0] + r * math.cos(th) + wind[0] * t ** 1.5
            y = neck_c[1] + r * math.sin(th) + wind[1] * t ** 1.5
            if abs(a) > math.radians(span) * 0.92:
                y = min(y, front_y)
            ring.append(Vector((x, y, z)))
        rings.append(ring)
    return grid_surface(name, rings, mat, thickness)


def hide(ob):
    if ob is not None:
        ob.hide_render = True
        ob.hide_viewport = True
    return ob


def empty(name, loc):
    import bpy
    e = bpy.data.objects.new(name, None)
    e.location = loc
    return link(e)
