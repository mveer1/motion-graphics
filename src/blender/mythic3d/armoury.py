"""
The armoury in 3D: weapons and held attributes drawn once at the grip and placed along an axis
(figure-design.md section 6). Forms marked [synthesis] there are drawn here the same way.
"""

import math

from mathutils import Matrix, Vector

from .core import V, ellipsoid, extrude, join, lathe, ribbon, sweep


def orient_z(axis, front=(0.0, -1.0, 0.0)):
    """3x3 rotation whose z column is `axis` and x column leans towards `front`."""
    z = V(axis).normalized()
    f = V(front)
    x = f - z * f.dot(z)
    if x.length < 1e-5:
        x = z.orthogonal()
    x.normalize()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed()


def _lathe_on(name, prof, mat, base, axis, front=(0, -1, 0), segs=40, radial=None, ry=1.0, caps=True):
    ob = lathe(name, prof, segs, mat, radial=radial, ry=ry, caps=caps)
    ob.data.transform(Matrix.Translation(V(base)) @ orient_z(axis, front).to_4x4())
    return ob


def shaft(name, mat, a, b, r, bands=None, band_mat=None):
    objs = [sweep(name, [V(a), V(b)], r, sides=14, material=mat, n_per=1)]
    for t in bands or []:
        p = V(a).lerp(V(b), t)
        objs.append(_lathe_on(name + "-band", [(r * 1.25, -0.012), (r * 1.45, -0.006), (r * 1.45, 0.006), (r * 1.25, 0.012)], band_mat, p, V(b) - V(a), segs=24))
    return objs


# ---------------------------------------------------------------------- Rama
def kodanda(look, grip, up, out, height=1.72, name="kodanda"):
    """A tall lacquered recurve about the figure's height: gold bands, a bound grip, curled gold tips and a
    taut string. up: along the bow; out: the side the limbs bow towards (away from the string)."""
    up, out = V(up).normalized(), V(out).normalized()
    red = look.solid("lacquer", "#8E2420", rough=0.32, coat=0.5)
    gold = look.gold()
    grip_mat = look.solid("grip", "#3A2418", rough=0.7)
    pts, radii = [], []
    n = 25
    for i in range(n):
        s = -1 + 2 * i / (n - 1)
        bow = 0.16 * (1 - s * s) - 0.04
        curl = 0.07 * max(0.0, abs(s) - 0.82) / 0.18
        pts.append(V(grip) + up * (s * height / 2) + out * (bow - curl * 1.4))
        radii.append(0.017 - 0.009 * abs(s) ** 1.5)
    objs = [sweep(name, pts, radii, sides=12, material=red, n_per=4)]
    for t in (0.2, 0.32, 0.68, 0.8):
        i = int(t * (n - 1))
        a, b = pts[i], pts[min(n - 1, i + 1)]
        objs.append(_lathe_on(name + "-band", [(radii[i] * 1.2, -0.012), (radii[i] * 1.4, 0.0), (radii[i] * 1.2, 0.012)], gold, a, b - a, segs=18))
    mid = n // 2
    objs.append(sweep(name + "-grip", pts[mid - 2:mid + 3], [r * 1.35 for r in radii[mid - 2:mid + 3]], sides=12, material=grip_mat, n_per=3))
    for tip in (pts[0], pts[-1]):
        objs.append(ellipsoid(name + "-tip", tip, (0.016, 0.016, 0.016), None, gold, 12))
    objs.append(sweep(name + "-string", [pts[1], pts[-2]], 0.0017, sides=6, material=look.solid("string", "#EDE3CC", rough=0.6), n_per=1))
    return join(objs, name)


def arrow(look, tail, tip, name="shara", glow=True):
    """A leaf-headed gold arrow with red and white vanes; the head glows with tejas."""
    tail, tip = V(tail), V(tip)
    d = (tip - tail).normalized()
    wood = look.solid("arrow-shaft", "#C9A36A", rough=0.5)
    head_mat = look.emissive("tejas", "#FFD27A", 6.0) if glow else look.gold()
    objs = [sweep(name, [tail, tip - d * 0.07], 0.0055, sides=10, material=wood, n_per=1)]
    objs.append(_lathe_on(name + "-head", [(0.0, 0.0), (0.016, 0.02), (0.018, 0.04), (0.0, 0.09)], head_mat, tip - d * 0.09, d, ry=0.35, segs=20))
    front = d.orthogonal()
    for k in range(3):
        R = Matrix.Rotation(2 * math.pi * k / 3, 3, d)
        side = R @ front
        poly = [(0.0, 0.0), (0.12, 0.0), (0.1, 0.03), (0.02, 0.03)]
        vane = extrude(name + "-vane", poly, 0.002, look.cloth("vane-" + str(k % 2), "#B8322A" if k % 2 else "#F1E7CF", rough=0.8))
        M = Matrix((d, side, d.cross(side))).transposed()
        vane.data.transform(Matrix.Translation(tail + d * 0.02) @ M.to_4x4())
        objs.append(vane)
    return join(objs, name)


def quiver(look, base, top, name="tuna"):
    base, top = V(base), V(top)
    d = top - base
    L = d.length
    leather = look.solid("quiver", "#6B3A22", rough=0.6)
    gold = look.gold()
    prof = [(0.0, 0.0), (0.052, 0.0), (0.058, 0.04), (0.062, L * 0.5), (0.068, L - 0.02), (0.07, L)]
    objs = [_lathe_on(name, prof, leather, base, d, segs=32, caps=False)]
    for t in (0.08, 0.5, 0.93):
        objs.append(_lathe_on(name + "-band", [(0.066, -0.012), (0.074, 0.0), (0.066, 0.012)], gold, base + d * t, d, segs=32))
    dn = d.normalized()
    side = dn.orthogonal().normalized()
    for k in range(5):
        R = Matrix.Rotation(2 * math.pi * k / 5 + 0.3, 3, dn)
        off = R @ side * 0.03
        a = top + off - dn * 0.05
        b = top + off + dn * (0.16 + 0.02 * (k % 2))
        objs.append(sweep(name + "-shaft", [a, b], 0.005, sides=8, material=look.solid("arrow-shaft", "#C9A36A", rough=0.5), n_per=1))
        vane = extrude(name + "-vane", [(0, 0), (0.09, 0), (0.08, 0.025), (0.01, 0.025)], 0.002,
                       look.cloth("vane-" + str(k % 2), "#B8322A" if k % 2 else "#F1E7CF", rough=0.8))
        M = Matrix((dn, R @ side, dn.cross(R @ side))).transposed()
        vane.data.transform(Matrix.Translation(b - dn * 0.1) @ M.to_4x4())
        objs.append(vane)
    return join(objs, name)


# ---------------------------------------------------------------------- Hanuman
def gada(look, grip, head, name="gada"):
    """A great fluted gold head (7 ribs), a jewelled equator band, a lotus collar, a crown finial and spike;
    a banded shaft with a red grip and pommel."""
    grip, head = V(grip), V(head)
    d = (head - grip).normalized()
    gold = look.gold()
    deep = look.gold("gold-deep", "#B07E2E", 0.32)
    red = look.solid("grip-red", "#9E2A22", rough=0.55)
    butt = grip - d * 0.14
    objs = shaft("gada-shaft", deep, butt, head - d * 0.12, 0.024, bands=[0.08, 0.3, 0.55, 0.8], band_mat=gold)
    objs.append(sweep("gada-grip", [grip - d * 0.1, grip + d * 0.1], 0.028, sides=14, material=red, n_per=1))
    objs.append(ellipsoid("gada-pommel", butt - d * 0.02, (0.036, 0.036, 0.036), None, gold, 16))
    R = 0.175
    prof = [(0.0, -R), (R * 0.42, -R * 0.93), (R * 0.75, -R * 0.68), (R * 0.95, -R * 0.32), (R, 0.0), (R * 0.95, R * 0.32),
            (R * 0.75, R * 0.68), (R * 0.42, R * 0.93), (0.0, R)]
    objs.append(_lathe_on("gada-head", prof, gold, head, d, segs=56, radial=lambda t, i: 1.0 + 0.07 * math.cos(7 * t) ** 2 * (1 if 1 <= i <= 7 else 0)))
    objs.append(_lathe_on("gada-equator", [(R * 1.0, -0.016), (R * 1.07, 0.0), (R * 1.0, 0.016)], deep, head, d, segs=56))
    ruby = look.gem("ruby", "#B8282E")
    side = d.orthogonal().normalized()
    for k in range(9):
        Rk = Matrix.Rotation(2 * math.pi * k / 9, 3, d)
        objs.append(ellipsoid("gada-gem", head + Rk @ side * R * 1.07, (0.017, 0.017, 0.017), None, ruby, 12))
    objs.append(_lathe_on("gada-collar", [(0.03, 0.0), (0.075, 0.03), (0.06, 0.05), (0.0, 0.06)], deep, head - d * (R + 0.04), d, segs=32,
                          radial=lambda t, i: 1.0 + 0.18 * abs(math.cos(4 * t))))
    objs.append(_lathe_on("gada-finial", [(0.0, 0.0), (0.05, 0.01), (0.045, 0.05), (0.02, 0.07), (0.012, 0.11), (0.0, 0.16)], gold,
                          head + d * (R - 0.01), d, segs=24, radial=lambda t, i: 1.0 + 0.2 * abs(math.cos(4 * t)) * (1 if i < 3 else 0)))
    return join(objs, name)


# ---------------------------------------------------------------------- Shiva
def trishula(look, base, top, name="trishula", damaru_too=True):
    """A planted trident: a leaf-bladed centre prong, side prongs sweeping out and up like flames from a
    crescent, a gold kalasha, red ribbons, the damaru tied beneath."""
    base, top = V(base), V(top)
    d = (top - base).normalized()
    steel = look.metal("steel", "#B9C2C8", 0.28)
    gold = look.gold()
    objs = shaft("trishula-shaft", look.metal("shaft", "#4A4E52", 0.4), base, top - d * 0.42, 0.016, bands=[0.25, 0.5, 0.75], band_mat=gold)
    k_at = top - d * 0.42
    objs.append(_lathe_on("kalasha", [(0.0, 0.0), (0.03, 0.0), (0.055, 0.03), (0.06, 0.06), (0.035, 0.1), (0.04, 0.12), (0.025, 0.14), (0.0, 0.15)],
                          gold, k_at, d, segs=32))
    hub = k_at + d * 0.15
    side = d.cross(Vector((0, -1, 0)))
    if side.length < 1e-4:
        side = d.orthogonal()
    side.normalize()
    front = side.cross(d).normalized()
    cres = [hub + side * (s * 0.16) + d * (0.06 * s * s) for s in [-1, -0.6, -0.2, 0.2, 0.6, 1]]
    objs.append(sweep("trishula-crescent", cres, (0.014, 0.008), sides=10, material=steel, n_per=4, up=tuple(front)))
    blade = [(0.0, 0.0), (0.03, 0.04), (0.045, 0.12), (0.036, 0.2), (0.012, 0.27), (0.0, 0.3)]
    objs.append(_lathe_on("trishula-centre", blade, steel, hub, d, front=side, segs=24, ry=0.25))
    for sx in (-1, 1):
        pts = [hub + side * (sx * 0.15) + d * 0.06, hub + side * (sx * 0.2) + d * 0.14, hub + side * (sx * 0.17) + d * 0.24, hub + side * (sx * 0.1) + d * 0.32]
        objs.append(sweep("trishula-side", pts, [(0.016, 0.006), (0.018, 0.006), (0.012, 0.005), (0.002, 0.002)], sides=10, material=steel, n_per=6, up=tuple(front)))
    red = look.cloth("ribbon", "#B8322A")
    for sx in (-1, 1):
        objs.append(ribbon("ribbon", [k_at + d * 0.02, k_at + side * (sx * 0.08) - d * 0.12, k_at + side * (sx * 0.12) - d * 0.3, k_at + side * (sx * 0.1) - d * 0.45],
                           [0.03, 0.03, 0.025, 0.02], front, red, thickness=0.003))
    if damaru_too:
        objs.append(damaru(look, k_at - d * 0.18 + side * 0.07, side, name="damaru"))
    return join(objs, name)


def damaru(look, center, axis, size=0.1, name="damaru"):
    """The hourglass drum, its two heads and the striker cords."""
    c, a = V(center), V(axis).normalized()
    wood = look.wood("damaru", "#7A4A2A")
    skin = look.solid("drumhead", "#EADBB8", rough=0.6)
    s = size
    prof = [(0.0, -s), (s * 0.55, -s), (s * 0.5, -s * 0.6), (s * 0.18, 0.0), (s * 0.5, s * 0.6), (s * 0.55, s), (0.0, s)]
    objs = [_lathe_on(name, prof, wood, c, a, segs=28)]
    for sg in (-1, 1):
        objs.append(_lathe_on(name + "-head", [(0.0, 0.0), (s * 0.56, 0.0), (s * 0.56, 0.004), (0.0, 0.004)], skin, c + a * sg * s, a, segs=28))
    perp = a.orthogonal().normalized()
    for sg in (-1, 1):
        objs.append(sweep(name + "-cord", [c, c + perp * sg * s * 0.8 - Vector((0, 0, s * 0.3)), c + perp * sg * s * 1.1 - Vector((0, 0, s * 0.6))],
                          0.002, sides=6, material=look.solid("cord", "#7A2A1E", 0.7), n_per=4))
        objs.append(ellipsoid(name + "-bead", c + perp * sg * s * 1.1 - Vector((0, 0, s * 0.6)), (0.01, 0.01, 0.01), None, look.solid("bead", "#3A2418", 0.5), 10))
    return join(objs, name)


# ---------------------------------------------------------------------- Ganesha
def ankusha(look, grip, tip, name="ankusha"):
    """The goad: a gold rod, a spike and a back-curving hook."""
    grip, tip = V(grip), V(tip)
    d = (tip - grip).normalized()
    gold = look.gold()
    steel = look.metal("steel", "#B9C2C8", 0.28)
    objs = shaft(name, gold, grip - d * 0.12, tip - d * 0.05, 0.011, bands=[0.2, 0.6], band_mat=look.gold("gold-deep", "#B07E2E", 0.32))
    objs.append(_lathe_on(name + "-spike", [(0.0, 0.0), (0.016, 0.0), (0.012, 0.05), (0.0, 0.12)], steel, tip - d * 0.05, d, segs=16))
    side = d.orthogonal().normalized()
    hook = [tip - d * 0.03, tip - d * 0.0 + side * 0.06, tip - d * 0.08 + side * 0.11, tip - d * 0.16 + side * 0.09, tip - d * 0.17 + side * 0.05]
    objs.append(sweep(name + "-hook", hook, [0.011, 0.01, 0.008, 0.005, 0.001], sides=10, material=steel, n_per=6))
    return join(objs, name)


def pasha(look, at, normal, r=0.11, name="pasha"):
    """The noose: a corded loop with a knot and a tassel."""
    at, n = V(at), V(normal).normalized()
    u = n.orthogonal().normalized()
    w = n.cross(u)
    c = at + u * r
    pts = [c + (u * math.cos(a) + w * math.sin(a)) * r for a in [math.pi + 2 * math.pi * k / 40 for k in range(40)]]
    cord_mat = look.gold("pasha", "#C99A3E", 0.35)
    objs = [sweep(name, pts, 0.008, sides=10, material=cord_mat, n_per=1, closed=True, twist=8)]
    objs.append(ellipsoid(name + "-knot", at, (0.02, 0.02, 0.02), None, cord_mat, 14))
    objs.append(sweep(name + "-tassel", [at, at - Vector((0, 0, 0.06)), at - Vector((0, 0, 0.12))], [0.006, 0.012, 0.016], sides=10,
                      material=look.cloth("tassel", "#B8322A"), n_per=3))
    return join(objs, name)


def modaka(look, at, size=0.05, name="modaka"):
    prof = [(0.0, 0.0), (size * 0.8, size * 0.1), (size, size * 0.45), (size * 0.75, size * 0.9), (size * 0.25, size * 1.25), (0.0, size * 1.45)]
    return _lathe_on(name, prof, look.solid("modaka", "#F0E2BE", rough=0.55), at, (0, 0, 1), segs=32,
                     radial=lambda t, i: 1.0 + 0.06 * math.cos(10 * t) * (1 if 1 <= i <= 4 else 0))


# ---------------------------------------------------------------------- Athena
def dory(look, butt, tip, name="dory"):
    """The hoplite spear: a bronze leaf blade with a midrib, an ash shaft, the sauroter butt-spike."""
    butt, tip = V(butt), V(tip)
    d = (tip - butt).normalized()
    bronze = look.gold("bronze-blade", "#C08A3E", 0.28)
    objs = shaft(name, look.wood("ash", "#B48A5A", 0.5), butt + d * 0.12, tip - d * 0.26, 0.014)
    objs.append(_lathe_on(name + "-blade", [(0.012, 0.0), (0.018, 0.03), (0.034, 0.12), (0.03, 0.18), (0.01, 0.24), (0.0, 0.27)], bronze, tip - d * 0.27, d, segs=24, ry=0.3))
    objs.append(_lathe_on(name + "-sauroter", [(0.0, 0.0), (0.008, 0.02), (0.016, 0.1), (0.017, 0.13)], bronze, butt, d, segs=16))
    return join(objs, name)


def aspis(look, center, normal, up, r=0.46, name="aspis"):
    """The round hoplite shield: a bronze face, a meander rim, a gorgoneion boss."""
    c, n = V(center), V(normal).normalized()
    bronze = look.gold("aspis", "#B98A42", 0.3)
    paint = look.solid("aspis-field", "#2C3A63", rough=0.45)
    prof = [(0.0, 0.06), (r * 0.5, 0.05), (r * 0.85, 0.025), (r * 0.94, 0.0), (r * 0.94, -0.02), (0.0, -0.01)]
    objs = [_lathe_on(name, prof, paint, c, n, front=up, segs=72)]
    objs.append(_lathe_on(name + "-rim", [(r * 0.9, -0.02), (r * 0.96, 0.02), (r * 1.0, 0.0), (r * 0.96, -0.03)], bronze, c, n, front=up, segs=72,
                          radial=lambda t, i: 1.0 + 0.008 * (1 if math.sin(24 * t) > 0 else -1) * (1 if i in (1, 2) else 0)))
    objs.append(_lathe_on(name + "-ring", [(r * 0.6, 0.04), (r * 0.63, 0.048), (r * 0.66, 0.04)], bronze, c, n, front=up, segs=64))
    objs.append(_lathe_on(name + "-boss", [(0.0, 0.1), (0.07, 0.085), (0.1, 0.06), (0.11, 0.05)], bronze, c, n, front=up, segs=40))
    return join(objs, name)


# ---------------------------------------------------------------------- Odin
def gungnir(look, butt, tip, name="gungnir"):
    """A long pattern-welded leaf blade with a fuller, a winged socket with gold bands, a dark ash shaft;
    the blade lit cold. Incised marks are abstract (no real runes)."""
    butt, tip = V(butt), V(tip)
    d = (tip - butt).normalized()
    steel = look.emissive("gungnir-blade", "#CFE6F2", 0.8) if not look.bronze else look.gold()
    gold = look.gold()
    objs = shaft(name, look.wood("ash-dark", "#3A2A20", 0.5), butt, tip - d * 0.45, 0.016, bands=[0.62, 0.9], band_mat=gold)
    objs.append(_lathe_on(name + "-blade", [(0.016, 0.0), (0.022, 0.04), (0.045, 0.16), (0.04, 0.3), (0.015, 0.42), (0.0, 0.46)], steel, tip - d * 0.46, d, segs=24, ry=0.22))
    side = d.orthogonal().normalized()
    for sg in (-1, 1):
        objs.append(sweep(name + "-wing", [tip - d * 0.47, tip - d * 0.5 + side * sg * 0.05], [0.008, 0.003], sides=8, material=gold, n_per=2))
    return join(objs, name)
