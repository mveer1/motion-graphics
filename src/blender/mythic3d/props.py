"""
Auras, seats, mounts and creatures for the 3D mythic figures.

Auras follow the 2D kit (armoury.js M.auras): tejas (Rama), agni (Hanuman), cosmic (Shiva, the Chola
Nataraja prabhavali), lotus (Ganesha), radiant (Athena: no ring, Greek gods have no halo), storm (Odin),
rays (the Jina), disc (the Buddha). They stand behind the figure like the plate of a temple image; in the
bronze look they are cast metal and the glows are not drawn.
"""

import math

from mathutils import Matrix, Vector

from .armoury import _lathe_on, orient_z
from .core import Blob, V, basis, ellipsoid, extrude, join, lathe, ribbon, sweep


def _in_plane(ob, center, y_back=0.0):
    """Map a mesh drawn in local XY (x right, y up) into the world XZ plane behind the figure."""
    M = Matrix(((1, 0, 0), (0, 0, 1), (0, 1, 0)))     # local y -> world z, local z -> world y
    ob.data.transform(Matrix.Translation(Vector((center[0], y_back, center[2]))) @ M.to_4x4())
    return ob


def flame_poly(w, h, lean=0.0):
    return [(-w / 2, 0), (-w * 0.46, h * 0.38), (-w * 0.2 + lean * w * 0.3, h * 0.72), (lean * w * 0.5 + 0.06 * w, h),
            (w * 0.18 + lean * w * 0.3, h * 0.66), (w * 0.42, h * 0.3), (w / 2, 0)]


def ring_of(look, name, poly_fn, n, r, mat, center, y_back, depth=0.012, phase=0.0, start=0.0, sweep_deg=360.0):
    objs = []
    for k in range(n):
        a = math.radians(start + sweep_deg * (k + 0.5) / n) + phase
        ob = extrude(name, poly_fn(k), depth, mat)
        R = Matrix.Rotation(a - math.pi / 2, 3, "Z")
        ob.data.transform(Matrix.Translation(Vector((r * math.cos(a), r * math.sin(a), 0))) @ R.to_4x4())
        objs.append(ob)
    ob = join(objs, name)
    return _in_plane(ob, center, y_back)


def torus_in_plane(look, name, r, tube, mat, center, y_back, segs=96):
    pts = [Vector((r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs), 0)) for k in range(segs)]
    ob = sweep(name, pts, tube, sides=12, material=mat, n_per=1, closed=True)
    return _in_plane(ob, center, y_back)


def disc_in_plane(look, name, r, mat, center, y_back, thick=0.01):
    ob = lathe(name, [(0.0, -thick / 2), (r, -thick / 2), (r, thick / 2), (0.0, thick / 2)], 72, mat)
    ob.data.transform(Matrix.Rotation(math.pi / 2, 4, "X"))
    ob.data.transform(Matrix.Translation(Vector((center[0], y_back, center[2]))))
    return ob


def aura(look, st, kind, center, radius, y_back=0.28, color=None):
    """Build an aura behind the figure. Returns the objects to put on the turntable."""
    c = V(center)
    objs = []
    gold = look.gold()
    if kind == "tejas":
        rays = look.emissive("tejas-ray", "#F6C96A", 2.2)
        objs.append(ring_of(look, "tejas-rays", lambda k: [(-0.012, 0), (0.0, radius * (0.42 if k % 2 else 0.55)), (0.012, 0)],
                            24, radius * 0.52, rays, c, y_back + 0.01, depth=0.006))
        objs.append(torus_in_plane(look, "tejas-ring", radius * 0.5, 0.012, gold, c, y_back))
        objs.append(disc_in_plane(look, "tejas-disc", radius * 0.48, look.emissive("tejas-disc", "#FFE7AE", 1.2), c, y_back + 0.02, 0.004))
        st.glow_card(look, "#FFD98A", c, radius * 1.15, 1.2, 2.0, 0.85)
    elif kind == "agni":
        for i, (col, n, rr, hh) in enumerate((("#C8402A", 15, 0.62, 0.42), ("#E8742E", 17, 0.52, 0.36), ("#F6B44A", 19, 0.42, 0.3))):
            mat = look.emissive("agni-" + str(i), col, 1.8 + 0.6 * i)
            objs.append(ring_of(look, "agni-ring", lambda k, w=0.16 * radius, h=hh * radius: flame_poly(w, h, 0.4 * math.sin(k)), n, rr * radius, mat, c,
                                y_back + 0.02 * i, depth=0.01, phase=0.13 * i))
        st.glow_card(look, "#FFB25A", c, radius * 1.25, 1.3, 1.8, 0.9)
    elif kind == "cosmic":
        night = look.solid("night", "#1E2A52", rough=0.8)
        objs.append(disc_in_plane(look, "night-disc", radius * 0.78, night, c, y_back + 0.03, 0.01))
        stars = []
        for k in range(46):
            a = k * 2.399963
            rr = radius * 0.74 * math.sqrt((k + 0.5) / 46)
            stars.append(ellipsoid("star", c + Vector((rr * math.cos(a), y_back + 0.02, rr * math.sin(a))), (0.006,) * 3, None,
                                   look.emissive("star", "#FFF4D6", 4.0), 8))
        objs.append(join(stars, "stars"))
        objs.append(torus_in_plane(look, "prabhavali", radius * 0.8, 0.03, look.gold("prabha", "#C9973F", 0.3), c, y_back))
        objs.append(ring_of(look, "prabha-flames", lambda k: flame_poly(0.16 * radius, 0.24 * radius, 0.5), 13, radius * 0.82,
                            look.emissive("prabha-flame", "#EE7A30", 2.0), c, y_back + 0.005, depth=0.014))
        objs.append(ring_of(look, "prabha-flames2", lambda k: flame_poly(0.1 * radius, 0.15 * radius, 0.3), 13, radius * 0.83,
                            look.emissive("prabha-flame2", "#F8C45A", 2.6), c, y_back - 0.01, depth=0.014, phase=math.pi / 13))
        st.glow_card(look, "#8E9CD8", c, radius * 1.1, 0.7, 2.2, 0.7)
    elif kind == "lotus":
        petal = look.solid("mandala-petal", "#E9B7A8", rough=0.55)
        objs.append(ring_of(look, "mandala", lambda k: [(-0.07 * radius, 0), (-0.06 * radius, 0.12 * radius), (0.0, 0.22 * radius), (0.06 * radius, 0.12 * radius),
                                                         (0.07 * radius, 0)], 16, radius * 0.4, petal, c, y_back + 0.02, depth=0.01))
        objs.append(torus_in_plane(look, "mandala-ring", radius * 0.41, 0.01, gold, c, y_back + 0.01))
        objs.append(ring_of(look, "lotus-rays", lambda k: [(-0.008, 0), (0.0, radius * 0.3), (0.008, 0)], 32, radius * 0.66,
                            look.emissive("lotus-ray", "#F6CF7A", 1.6), c, y_back + 0.03, depth=0.005))
        st.glow_card(look, "#FFD98A", c, radius * 1.15, 1.2, 2.0, 0.85)
    elif kind == "radiant":
        objs.append(ring_of(look, "radiant-rays", lambda k: [(-0.006, 0), (0.0, radius * (0.3 if k % 2 else 0.45)), (0.006, 0)], 36,
                            radius * 0.55, look.emissive("radiant-ray", "#FBE3A6", 1.4), c, y_back, depth=0.004))
        st.glow_card(look, "#FFE7B0", c, radius * 1.2, 1.1, 2.2, 0.8)
    elif kind == "storm":
        arc_mat = look.emissive("storm-arc", "#C9D6E6", 1.2)
        for i in range(7):
            a0 = math.radians(20 + 50 * i)
            rr = radius * (0.62 + 0.09 * (i % 3))
            pts = [Vector((rr * math.cos(a0 + t), y_back, rr * math.sin(a0 + t))) + Vector((c.x, 0, c.z)) for t in [0.0, 0.25, 0.5, 0.75, 1.0]]
            objs.append(sweep("storm", pts, [0.002, 0.006, 0.007, 0.005, 0.001], sides=6, material=arc_mat, n_per=4))
        st.glow_card(look, "#B8C8DC", c, radius * 1.2, 0.9, 1.8, 0.75)
    elif kind in ("rays", "disc"):
        fill = look.solid("halo-disc", "#F2E2B8", rough=0.5)
        objs.append(disc_in_plane(look, "halo", radius, fill, c, y_back, 0.012))
        objs.append(torus_in_plane(look, "halo-rim", radius, 0.012, gold, c, y_back - 0.006))
        if kind == "rays":
            objs.append(ring_of(look, "halo-rays", lambda k: [(-0.01, 0), (0.0, radius * 0.5), (0.01, 0)], 32, radius * 0.45,
                                look.gold("halo-ray", "#D7A443", 0.35), c, y_back - 0.01, depth=0.004))
        st.glow_card(look, "#FFE9B8", c, radius * 1.4, 0.8, 2.4, 0.6)
    return objs


# ---------------------------------------------------------------------- seats
def lotus_seat(look, top_z, r=0.46, plinth=0.22, emblem=None):
    """A double lotus (petals up and down) on a stepped square plinth. Returns (objects, plinth front point)."""
    pink = look.solid("lotus-petal", "#E7A99A", rough=0.5)
    pink2 = look.solid("lotus-petal-2", "#D88472", rough=0.5)
    gold = look.gold()
    stone = look.solid("plinth", "#C9A46A", rough=0.6, cavity=0.6)
    objs = []
    z_lotus = top_z - 0.16
    objs.append(_lathe_on("lotus-core", [(0.0, 0.0), (r * 0.95, 0.0), (r, 0.05), (r * 0.98, 0.1), (r * 0.9, 0.16), (0.0, 0.16)], pink2,
                          (0, 0, z_lotus), (0, 0, 1), segs=64, ry=0.72))
    for row, (n, tilt, zz, rr, mat) in enumerate(((22, 58, 0.1, r * 0.9, pink), (22, -55, 0.035, r * 0.94, pink2))):
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * row) / n
            d = Vector((math.cos(a), math.sin(a) * 0.72, 0)).normalized()
            out = d * math.cos(math.radians(tilt)) + Vector((0, 0, math.sin(math.radians(tilt))))
            tang = Vector((-d.y, d.x, 0)).normalized()
            nrm = out.cross(tang).normalized()
            L, Wd = 0.16, 0.085
            poly = [(0.0, 0.0), (L * 0.25, Wd * 0.48), (L * 0.6, Wd * 0.5), (L * 0.86, Wd * 0.3), (L, 0.0), (L * 0.86, -Wd * 0.3), (L * 0.6, -Wd * 0.5), (L * 0.25, -Wd * 0.48)]
            pet = extrude("petal", poly, 0.016, mat, bevel=0.006)
            M = Matrix((out, tang, nrm)).transposed()
            base = Vector((rr * 0.55 * math.cos(a), rr * 0.55 * math.sin(a) * 0.72, z_lotus + zz))
            pet.data.transform(Matrix.Translation(base) @ M.to_4x4())
            objs.append(pet)
    objs.append(_lathe_on("lotus-rim", [(r * 0.98, -0.006), (r * 1.01, 0.0), (r * 0.98, 0.006)], gold, (0, 0, z_lotus + 0.075), (0, 0, 1), segs=64, ry=0.72))
    pz = z_lotus - 0.02
    steps = [(r * 1.05, pz), (r * 1.05, pz - 0.03), (r * 0.98, pz - 0.05), (r * 0.98, pz - plinth + 0.06), (r * 1.08, pz - plinth + 0.04),
             (r * 1.12, pz - plinth + 0.01), (r * 1.12, 0.0)]
    prof = [(0.0, pz)] + steps + [(0.0, 0.0)]
    pl = lathe("plinth", [(rr * math.sqrt(2), zz) for rr, zz in prof], 4, stone)
    pl.data.transform(Matrix.Rotation(math.pi / 4, 4, "Z"))
    pl.data.transform(Matrix.Diagonal((1.0, 0.62, 1.0, 1.0)))
    objs.append(pl)
    front = Vector((0, -r * 1.12 * 0.62 - 0.005, pz - plinth * 0.5))
    return objs, front


# ---------------------------------------------------------------------- creatures and attributes
def mouse(look, at, facing=(0, -1, 0), s=1.0):
    """Ganesha's mouse, sitting up at the foot of the seat, looking out."""
    B = Blob("mouse", res=0.003)
    f = V(facing).normalized()
    up = Vector((0, 0, 1))
    side = f.cross(up)
    c = V(at)
    B.ell(c + up * 0.05 * s, (0.06 * s, 0.05 * s, 0.055 * s), basis(f), soft=0.6)
    B.ell(c + up * 0.1 * s + f * 0.04 * s, (0.04 * s, 0.035 * s, 0.035 * s), basis(f), soft=0.6)
    B.ell(c + up * 0.095 * s + f * 0.085 * s, (0.025 * s, 0.015 * s, 0.015 * s), basis(f), soft=0.55)
    for sg in (-1, 1):
        B.ell(c + up * 0.135 * s + f * 0.03 * s + side * sg * 0.028 * s, (0.018 * s, 0.006 * s, 0.02 * s), basis(side * sg, up), soft=0.4)
        B.ell(c + up * 0.01 * s + f * 0.04 * s + side * sg * 0.03 * s, (0.025 * s, 0.012 * s, 0.012 * s), basis(f), soft=0.5)
    ob = B.to_mesh("mouse", look.solid("mouse", "#8A7A6E", rough=0.7))
    tail = sweep("mouse-tail", [c - f * 0.05 * s + up * 0.01 * s, c - f * 0.1 * s + side * 0.05 * s, c - f * 0.08 * s + side * 0.12 * s + up * 0.01 * s],
                 [0.006 * s, 0.004 * s, 0.0015 * s], sides=6, material=look.solid("mouse-tail", "#C9A090", 0.6), n_per=6)
    eyes = [ellipsoid("mouse-eye", c + up * 0.11 * s + f * 0.07 * s + side * sg * 0.016 * s, (0.005 * s,) * 3, None, look.solid("bead-eye", "#120C0A", 0.2), 8) for sg in (-1, 1)]
    return [ob, tail] + eyes


def lion(look, at, facing=(0, -1, 0), s=1.0):
    """Mahavira's lanchhana: a seated lion in relief at the plinth's front, facing out."""
    B = Blob("lion", res=0.003)
    f = V(facing).normalized()
    up = Vector((0, 0, 1))
    side = f.cross(up)
    c = V(at)
    B.ell(c + side * 0.02 * s, (0.09 * s, 0.03 * s, 0.045 * s), basis(side, up), soft=0.6)
    B.ell(c + side * -0.07 * s + up * 0.035 * s, (0.045 * s, 0.035 * s, 0.05 * s), basis(side, up), soft=0.6)
    for k in range(10):
        a = 2 * math.pi * k / 10
        B.ball(c + side * -0.07 * s + up * 0.035 * s + (side * math.cos(a) + up * math.sin(a)) * 0.042 * s - f * 0.005 * s, 0.022 * s, soft=0.55)
    B.ell(c + side * -0.1 * s + up * 0.03 * s + f * 0.03 * s, (0.02 * s, 0.025 * s, 0.022 * s), None, soft=0.5)
    for dx in (-0.04, 0.07):
        B.cap(c + side * dx * s - up * 0.01 * s, c + side * dx * s - up * 0.05 * s + f * 0.01 * s, 0.012 * s, soft=0.5)
    ob = B.to_mesh("lion", look.gold("lion", "#C99A3E", 0.35))
    tail = sweep("lion-tail", [c + side * 0.1 * s, c + side * 0.14 * s + up * 0.04 * s, c + side * 0.12 * s + up * 0.08 * s], [0.008 * s, 0.006 * s, 0.012 * s],
                 sides=8, material=look.gold("lion", "#C99A3E", 0.35), n_per=4)
    return [ob, tail]


def raven(look, at, facing, pose="perched", s=1.0, name="raven"):
    """Huginn or Muninn: a black bird, perched with folded wings or flying with spread wings."""
    B = Blob(name, res=0.003)
    f = V(facing).normalized()
    up = Vector((0, 0, 1))
    side = f.cross(up).normalized()
    c = V(at)
    B.ell(c, (0.085 * s, 0.045 * s, 0.05 * s), basis(f, -up), soft=0.55)
    B.ell(c + f * 0.08 * s + up * 0.04 * s, (0.04 * s, 0.035 * s, 0.035 * s), None, soft=0.55)
    feather = look.solid("raven", "#16181E", rough=0.35, cavity=0.3)
    ob = B.to_mesh(name, feather)
    beak = _lathe_on(name + "-beak", [(0.014 * s, 0.0), (0.01 * s, 0.03 * s), (0.0, 0.06 * s)], look.solid("beak", "#2A2A2E", 0.3),
                     c + f * 0.11 * s + up * 0.035 * s, f - up * 0.25, segs=12)
    objs = [ob, beak]
    tail = extrude(name + "-tail", [(0, -0.03 * s), (0.11 * s, -0.045 * s), (0.12 * s, 0.045 * s), (0, 0.03 * s)], 0.006 * s, feather)
    Mt = Matrix((-f, side, up)).transposed()
    tail.data.transform(Matrix.Translation(c - f * 0.06 * s - up * 0.01 * s) @ Mt.to_4x4() @ Matrix.Rotation(math.radians(-15), 4, "Y"))
    objs.append(tail)
    for sg in (-1, 1):
        if pose == "flying":
            wing = extrude(name + "-wing", [(0, -0.03 * s), (0.05 * s, -0.04 * s), (0.2 * s, -0.01 * s), (0.27 * s, 0.03 * s), (0.18 * s, 0.05 * s), (0, 0.04 * s)],
                           0.006 * s, feather)
            Mw = Matrix((side * sg, f, up)).transposed()
            wing.data.transform(Matrix.Translation(c + up * 0.02 * s) @ Mw.to_4x4() @ Matrix.Rotation(math.radians(sg * 25), 4, "Y"))
        else:
            wing = ellipsoid(name + "-wing", c + side * sg * 0.035 * s + up * 0.01 * s - f * 0.02 * s, (0.09 * s, 0.012 * s, 0.035 * s), basis(f - up * 0.25, side * sg), feather, 16)
        objs.append(wing)
    for sg in (-1, 1):
        objs.append(ellipsoid(name + "-eye", c + f * 0.1 * s + up * 0.055 * s + side * sg * 0.022 * s, (0.005 * s,) * 3, None, look.solid("bead-eye", "#120C0A", 0.2), 8))
    if pose == "perched":
        for sg in (-1, 1):
            objs.append(sweep(name + "-leg", [c + side * sg * 0.015 * s - up * 0.03 * s, c + side * sg * 0.015 * s - up * 0.07 * s], 0.004 * s, sides=6,
                              material=look.solid("beak", "#2A2A2E", 0.3), n_per=1))
    return join(objs, name)


def crescent(look, at, normal, up, r=0.05, name="chandra"):
    """The moon's crescent worn in the jata."""
    c = V(at)
    n = V(normal).normalized()
    u = V(up).normalized()
    w = n.cross(u)
    pts = [c + (w * math.cos(a) + u * math.sin(a)) * r for a in [math.radians(x) for x in range(-40, 230, 18)]]
    radii = [0.002 + 0.012 * math.sin(math.pi * i / (len(pts) - 1)) for i in range(len(pts))]
    return sweep(name, pts, [(rr, rr * 0.6) for rr in radii], sides=10, material=look.silver("moon", "#EEF0F2", 0.25), n_per=4)


def cobra(look, neck_pts, hood_at, hood_dir, name="vasuki"):
    """The serpent coiled at Shiva's neck, the hood raised beside his head."""
    green = look.solid("cobra", "#2F6A45", rough=0.4, coat=0.3)
    body = sweep(name, neck_pts + [hood_at], [0.012] + [0.016] * (len(neck_pts) - 1), sides=10, material=green, n_per=6)
    d = V(hood_dir).normalized()
    hood = ellipsoid(name + "-hood", V(hood_at) + d * 0.02, (0.05, 0.014, 0.07), basis(Vector((0, 0, 1)), d), green, 20)
    head = ellipsoid(name + "-head", V(hood_at) + d * 0.03 + Vector((0, 0, 0.068)), (0.022, 0.032, 0.016), basis(d, Vector((0, 0, 1))), green, 16)
    belly = ellipsoid(name + "-belly", V(hood_at) + d * 0.034, (0.024, 0.004, 0.05), basis(Vector((0, 0, 1)), d), look.solid("cobra-belly", "#B9B486", 0.5), 16)
    return join([body, hood, head, belly], name)


def chhatra(look, top, r0=0.2):
    """The triple umbrella over a Jina: three tiers on a pole, a fringe of beads."""
    gold = look.gold()
    pearl = look.solid("pearl", "#F2ECDD", rough=0.25)
    objs = []
    z = V(top)
    for i, (r, h) in enumerate(((r0, 0.0), (r0 * 0.78, 0.09), (r0 * 0.56, 0.17))):
        base = z + Vector((0, 0, h))
        objs.append(_lathe_on("chhatra", [(0.0, 0.035), (r * 0.6, 0.03), (r, 0.0), (r * 0.98, -0.01), (0.0, -0.005)], gold, base, (0, 0, 1), segs=48, ry=0.75))
        for k in range(18):
            a = 2 * math.pi * k / 18
            objs.append(ellipsoid("fringe", base + Vector((r * math.cos(a), r * math.sin(a) * 0.75, -0.02)), (0.008,) * 3, None, pearl, 8))
    objs.append(sweep("chhatra-pole", [z - Vector((0, 0, 0.06)), z + Vector((0, 0, 0.26))], 0.008, sides=8, material=gold, n_per=1))
    objs.append(ellipsoid("chhatra-bud", z + Vector((0, 0, 0.28)), (0.022, 0.022, 0.03), None, gold, 12))
    return join(objs, "chhatra")


def stream(look, pts, name="ganga"):
    """Ganga flowing out of the jata: a narrow ribbon of water."""
    water = look.emissive("ganga", "#BFE2EE", 0.6)
    return ribbon(name, pts, [0.02, 0.026, 0.022, 0.012][:len(pts)] + [0.01] * max(0, len(pts) - 4), (0, -1, 0), water, thickness=0.004,
                  waves=(0.004, 3))


def orient(axis, front=(0, -1, 0)):
    return orient_z(axis, front)
