"""
Heads for the 3D mythic figures: human, vanara (Hanuman) and elephant (Ganesha).

Head space: units of H (skull top to chin), origin at the head centre, -y forward, z up. The face
follows the 2D grid (figure-design.md section 3.2): eyes at half the head, the nose to two thirds,
lotus-petal eyes under heavy upper lids (lowered for the meditative figures), a full lower lip.
Elements go into the body's blob, so the neck and jaw blend into one skin. Eyeballs are separate meshes.
"""

import math

from mathutils import Matrix, Vector

from .core import basis, ellipsoid, sweep


def _E(body):
    B, R, H = body.blob, body.head_rot(), body.H

    def E(c, ext, soft=0.5, neg=False, rot=None):
        return B.ell(body.hp(*c), tuple(e * H for e in ext), R if rot is None else R @ rot, soft, neg)

    def C(a, b, r, soft=0.45, neg=False):
        return B.cap(body.hp(*a), body.hp(*b), r * H, soft, neg)

    def Ball(c, r, soft=0.45, neg=False):
        return B.ball(body.hp(*c), r * H, soft, neg)
    return E, C, Ball


def eyes(body, look, o, spec):
    """Eyeballs placed behind the projected face surface (after anatomy.skin builds the fit).
    spec: {'at': [(x, z), ...] head space, 'r': radius in H, 'cover': lid cover in H}."""
    R = body.head_rot()
    fwd = R @ Vector((0, -1, 0))
    gaze = Matrix.Rotation(math.radians(-o.get("gaze", 0.0)), 3, "X")
    out = []
    fit = spec["fit"]
    H = body.H
    for (x, z), name in zip(spec["at"], ("eye-r", "eye-l")):
        if o.get("closed_eye") == name[-1]:
            continue
        glow = o.get("glow_eye", 0.0) if name == "eye-l" else 0.0
        mat = look.eye(name if glow else "eye", o.get("iris", "#2A1A12"), glow=glow)
        hit = fit.tree.ray_cast(body.hp(x, -1.5, z), -fwd, 3.0 * H)
        surf = hit[0] if hit[0] is not None else body.hp(x, -0.38, z)
        r = spec.get("r", 0.058) * H
        c = surf - fwd * (r + spec.get("cover", 0.006) * H)
        ob = ellipsoid(name, (0, 0, 0), (r, r, r), None, mat, segs=32)
        ob.data.transform((R @ gaze).to_4x4())
        ob.location = c
        out.append(ob)
    return out


def human(body, look, o=None):
    """A human head: smooth masses only; anatomy.sculpt_face carves the features.
    o: female, jaw (strength), lids (0 open .. 1 lowered), lobes (long ears), gaze, iris."""
    o = o or {}
    E, C, Ball = _E(body)
    jw = o.get("jaw", 1.0) * (0.9 if o.get("female") else 1.0)
    fem = o.get("female", False)
    E((0, 0.05, 0.1), (0.355, 0.405, 0.4), 0.62)
    E((0, 0.16, -0.05), (0.29, 0.26, 0.27), 0.62)
    E((0, -0.2, 0.15), (0.29, 0.17, 0.19), 0.65)
    E((0, -0.15, -0.1), (0.28 * jw, 0.25, 0.27), 0.66)
    E((0, -0.14, -0.31), (0.25 * jw, 0.22, 0.15), 0.64)
    E((0, -0.27, -0.27), (0.12, 0.12, 0.1), 0.66)
    E((0, -0.27, -0.395), (0.105 * jw * (0.85 if fem else 1.0), 0.09, 0.085), 0.76)
    for sx in (-1, 1):
        E((sx * 0.22 * jw, -0.03, -0.27), (0.06, 0.1, 0.1), 0.58)
        E((sx * 0.16, -0.24, -0.1), (0.07, 0.07, 0.07), 0.72)
        E((sx * 0.34, 0.045, -0.05), (0.026, 0.07, 0.125), 0.5, rot=Matrix.Rotation(math.radians(sx * 10), 3, "Z"))
        if o.get("lobes"):
            E((sx * 0.342, 0.05, -0.26), (0.022, 0.042, 0.11), 0.5)
    return {"kind": "human", "eyes": {"at": [(-0.112, -0.03), (0.112, -0.03)], "r": 0.058, "cover": 0.006}, "o": o}


def vanara(body, look, o=None):
    """Hanuman: a bare face mask with a heavy brow, a broad flat nose, a full upper lip and a strong
    jaw; round ears set high; a fur ruff framing the face (the Chola convention: only the face and
    tail confirm the monkey identity)."""
    o = o or {}
    E, C, Ball = _E(body)
    E((0, 0.06, 0.1), (0.34, 0.4, 0.38), 0.6)
    E((0, 0.15, -0.06), (0.28, 0.27, 0.26), 0.6)
    E((0, -0.17, 0.14), (0.28, 0.17, 0.16), 0.6)
    E((0, -0.13, -0.12), (0.3, 0.27, 0.26), 0.62)
    E((0, -0.3, -0.19), (0.21, 0.16, 0.16), 0.62)
    E((0, -0.31, -0.37), (0.165, 0.13, 0.085), 0.62)
    for sx in (-1, 1):
        E((sx * 0.21, -0.25, -0.14), (0.09, 0.1, 0.1), 0.55)
        E((sx * 0.33, 0.0, 0.01), (0.045, 0.095, 0.095), 0.45)
    # Fur ruff: tufts around the face, pointing outwards.
    for i in range(19):
        a = math.pi * (-0.15 + 1.3 * i / 18)
        x, z = 0.37 * math.cos(a), 0.36 * math.sin(a) - 0.12
        if z > 0.16:
            continue
        rot = basis(Vector((x, 0.05, z)), Vector((0, -1, 0)))
        E((x * 0.92, -0.16, z * 0.92), (0.085, 0.05, 0.055), 0.45, rot=rot)
    # The jaw mark (Hanuman = "one with the jaw"): a small dent on his left (viewer's right).
    E((0.12, -0.36, -0.36), (0.035, 0.03, 0.03), 0.5, neg=True)
    return {"kind": "vanara", "eyes": {"at": [(-0.112, -0.012), (0.112, -0.012)], "r": 0.054, "cover": 0.006}, "o": o}


def elephant(body, look, o=None):
    """Ganesha's head: twin domes, a broad brow, small kind eyes, the trunk turning to his left,
    winnowing-fan ears with a gold rim, the right tusk broken and the left whole."""
    o = o or {}
    E, C, Ball = _E(body)
    H = body.H
    E((0, 0.04, 0.1), (0.36, 0.38, 0.36), 0.55)
    for sx in (-1, 1):
        E((sx * 0.135, -0.1, 0.3), (0.165, 0.17, 0.15), 0.5)
        E((sx * 0.2, -0.2, -0.17), (0.13, 0.15, 0.15), 0.55)
    E((0, -0.23, 0.02), (0.3, 0.2, 0.3), 0.55)
    E((0, -0.3, -0.4), (0.08, 0.06, 0.045), 0.45)
    # Trunk: from between the eyes, down over the chest, turning to his left (+x), the tip curling up.
    tpts = o.get("trunk", [(0, -0.38, -0.1), (0.0, -0.46, -0.45), (0.04, -0.48, -0.85), (0.16, -0.5, -1.2),
                           (0.32, -0.56, -1.36), (0.42, -0.62, -1.28), (0.43, -0.66, -1.14)])
    radii = [0.13, 0.115, 0.095, 0.075, 0.058, 0.045, 0.036]
    pts = [body.hp(*p) for p in tpts]
    B = body.blob
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        n = 4
        for j in range(n):
            t = j / n
            B.ball(a.lerp(b, t), (radii[i] + (radii[i + 1] - radii[i]) * t) * H * 0.92, 0.5)
    B.ball(pts[-1], radii[-1] * H * 0.95, 0.5)
    ivory = look.solid("ivory", "#EFE4C8", rough=0.35, cavity=0.3)
    tusks = []
    for sx, broken in ((-1, True), (1, False)):
        base = body.hp(sx * 0.15, -0.36, -0.3)
        if broken:
            path = [base, body.hp(sx * 0.17, -0.47, -0.4), body.hp(sx * 0.18, -0.52, -0.46)]
            rr = [0.035 * H, 0.03 * H, 0.026 * H]
        else:
            path = [base, body.hp(sx * 0.18, -0.5, -0.45), body.hp(sx * 0.2, -0.62, -0.52), body.hp(sx * 0.19, -0.7, -0.48)]
            rr = [0.035 * H, 0.028 * H, 0.017 * H, 0.004 * H]
        tusks.append(sweep("tusk-" + ("r" if sx < 0 else "l"), path, rr, sides=12, material=ivory))
    return {"kind": "elephant", "eyes": {"at": [(-0.2, 0.0), (0.2, 0.0)], "r": 0.034, "cover": 0.005}, "o": o,
            "tusks": tusks, "trunk_tip": pts[-1], "trunk": pts}
