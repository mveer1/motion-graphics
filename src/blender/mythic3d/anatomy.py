"""
Shared anatomy passes for the 3D figures: sculpted definition and painted features.

Muscle as few shapes (figure-design.md section 3.4 and 7): a pectoral crescent, the deltoid cap and its
separation, the biceps and triceps edges, abs implied 2 x 3, the obliques and Apollo's belt, the quad
teardrop and sweep, the calf bean. The Jina and the Buddha get the smooth "lion-like" torso (no
grooves); Ganesha keeps his belly. Guide curves are projected onto the skin before they cut it.
"""

from mathutils import Vector

from .core import Fit, catmull, mix_hex, r_ell


def _on(fit, pts, n=6):
    return fit.onto(catmull(pts, n), 0.0)


def sculpt_body(body, sc, fit, strength=1.0):
    P = body.P
    k = strength * P["muscle"]
    s = body.s
    T_ = body.T_
    smooth = P.get("smooth", False)
    g = lambda pts, w, d, **kw: sc.groove(_on(fit, pts), w * s, d * s * k, **kw)  # noqa: E731
    # Neck and collar: the sternal notch, clavicles.
    sc.bump(T_(0, -0.07, 1.495), (0.02 * s, 0.02 * s, 0.016 * s), -0.004 * s)
    for sx in (-1, 1):
        sc.ridge(_on(fit, [T_(sx * 0.025, -0.07, 1.492), T_(sx * 0.09, -0.06, 1.505), T_(sx * 0.165, -0.03, 1.505)]), 0.007 * s, 0.0022 * s)
    if smooth:
        sc.bump(body.marks["navel"], (0.012 * s, 0.012 * s, 0.014 * s), -0.006 * s)
        return
    if not P["female"]:
        for sx in (-1, 1):
            # Pectoral underline: a hard crescent rising to the armpit.
            g([T_(sx * 0.012, -0.12, 1.318), T_(sx * 0.06, -0.122, 1.298), T_(sx * 0.115, -0.1, 1.31), T_(sx * 0.155, -0.06, 1.35)],
              0.009, 0.005, taper=(0.7, 1.0))
            # Front edge of the deltoid.
            g([T_(sx * 0.16, -0.07, 1.375), T_(sx * 0.178, -0.075, 1.43), T_(sx * 0.17, -0.06, 1.48)], 0.007, 0.004)
        g([T_(0, -0.12, 1.39), T_(0, -0.13, 1.3)], 0.006, 0.004)
    if not P.get("belly"):
        # Linea alba, the three tendinous lines, the lateral edges (linea semilunaris), Apollo's belt.
        g([T_(0, -0.125, 1.27), T_(0, -0.125, 1.18), T_(0, -0.118, 1.11)], 0.006, 0.003, ends=0.05)
        for z in (1.245, 1.195, 1.15):
            for sx in (-1, 1):
                g([T_(sx * 0.008, -0.125, z), T_(sx * 0.035, -0.124, z - 0.004), T_(sx * 0.058, -0.115, z + 0.002)], 0.005, 0.002)
        for sx in (-1, 1):
            g([T_(sx * 0.07, -0.11, 1.27), T_(sx * 0.074, -0.112, 1.17), T_(sx * 0.064, -0.112, 1.07)], 0.0065, 0.0025)
            g([T_(sx * 0.118, -0.075, 1.07), T_(sx * 0.075, -0.1, 1.0), T_(sx * 0.03, -0.11, 0.945)], 0.007, 0.0038)
        sc.bump(body.marks["navel"], (0.011 * s, 0.011 * s, 0.013 * s), -0.006 * s)
    # Back: the spine furrow and the shoulder blades.
    g([T_(0, 0.07, 1.48), T_(0, 0.11, 1.3), T_(0, 0.105, 1.1), T_(0, 0.09, 0.98)], 0.008, 0.005)
    for sx in (-1, 1):
        sc.bump(T_(sx * 0.085, 0.115, 1.38), (0.05 * s, 0.02 * s, 0.07 * s), 0.004 * s * k)
    for side in ("r", "l"):
        sculpt_arm(body, sc, fit, side, k)
        if not body.seated:
            sculpt_leg(body, sc, fit, side, k)


def sculpt_arm(body, sc, fit, side, k):
    s = body.s
    S, Ru = body.frames["upper_" + side]
    E = body.J["elbow_" + side]
    up = E - S
    z = Ru @ Vector((0, 0, 1))
    for sg in (-1, 1):
        pts = [S + up * 0.32 + z * sg * 0.045 * s, S + up * 0.6 + z * sg * 0.044 * s, S + up * 0.88 + z * sg * 0.036 * s]
        sc.groove(_on(fit, pts), 0.0055 * s, 0.003 * s * k)
    W = body.J["wrist_" + side]
    fo = W - E
    E0, Rf = body.frames["fore_" + side]
    zf = Rf @ Vector((0, 0, 1))
    sc.groove(_on(fit, [E + fo * 0.08 + zf * 0.035 * s, E + fo * 0.45 + zf * 0.026 * s]), 0.005 * s, 0.0025 * s * k)


def sculpt_leg(body, sc, fit, side, k):
    s = body.s
    Hj, K, A = body.J["hip_" + side], body.J["knee_" + side], body.J["ankle_" + side]
    th, sh = K - Hj, A - K
    Hj0, Rt = body.frames["thigh_" + side]
    fv, sv = Rt @ Vector((0, 1, 0)), Rt @ Vector((0, 0, 1))
    sx = -1 if side == "r" else 1
    out = sv if sv.x * sx > 0 else -sv
    # Vastus lateralis / rectus line and the teardrop's upper edge.
    sc.groove(_on(fit, [Hj + th * 0.3 + fv * 0.07 * s + out * 0.04 * s, Hj + th * 0.62 + fv * 0.07 * s + out * 0.036 * s, Hj + th * 0.88 + fv * 0.05 * s + out * 0.03 * s]), 0.006 * s, 0.0035 * s * k)
    sc.groove(_on(fit, [Hj + th * 0.66 + fv * 0.06 * s - out * 0.05 * s, Hj + th * 0.82 + fv * 0.07 * s - out * 0.02 * s, Hj + th * 0.92 + fv * 0.06 * s]), 0.006 * s, 0.003 * s * k)
    # Kneecap outline and the calf heads.
    sc.groove(_on(fit, [K + fv * 0.05 * s - out * 0.03 * s + th.normalized() * 0.03 * s, K + fv * 0.06 * s + th.normalized() * 0.045 * s, K + fv * 0.05 * s + out * 0.03 * s + th.normalized() * 0.03 * s]), 0.005 * s, 0.0025 * s * k)
    K0, Rs = body.frames["shin_" + side]
    fs = Rs @ Vector((0, 1, 0))
    sc.groove(_on(fit, [K + sh * 0.1 - fs * 0.05 * s, K + sh * 0.35 - fs * 0.06 * s, K + sh * 0.5 - fs * 0.045 * s]), 0.006 * s, 0.0035 * s * k)
    sc.ridge(_on(fit, [K + sh * 0.12 + fs * 0.03 * s, K + sh * 0.85 + fs * 0.02 * s]), 0.006 * s, 0.0015 * s)


def kambu(body, sc, depth=0.001):
    """Kambu-griva: the three conch lines across the front of the neck (Rama, the Jina, the Buddha)."""
    import numpy as _np

    from .core import seg_dist
    s = body.s
    a, b = body.T_(0, 0.0, 1.49), body.J["chin"] + Vector((0, 0.07 * s, -0.01 * s))
    d, t = seg_dist(sc.P, a, b)
    near = (d < 0.085 * s) * (sc.P[:, 1] < a.y + 0.01 * s)
    for k in (0.28, 0.48, 0.68):
        z = a.z + (b.z - a.z) * k - 0.012 * s * _np.clip(1 - _np.abs(sc.P[:, 0] - a.x) / (0.06 * s), 0, 1)
        sc.d -= depth * s * near * _np.exp(-((sc.P[:, 2] - z) / (0.0035 * s)) ** 2)


def nails_and_soles(body, pt, skin):
    """A paler tone on palms and soles (the 2D kit's sole colour)."""
    P = pt.P
    s = body.s
    tone = mix_hex(skin, "#E7A58E", 0.35)
    for side in ("r", "l"):
        if "palm_" + side in body.marks:
            W, R = body.frames["hand_" + side]
            Y = R @ Vector((0, 1, 0))
            c = body.marks["palm_" + side] + Y * 0.016 * s
            pt.layer(r_ell(P, c, (0.05 * s, 0.012 * s, 0.045 * s), R, 0.6), tone, 0.45)
        if "foot_" + side in body.frames:
            A, Rf = body.frames["foot_" + side]
            X, Yd = Rf @ Vector((1, 0, 0)), Rf @ Vector((0, 1, 0))
            pt.layer(r_ell(P, A + X * 0.06 * s + Yd * 0.072 * s, (0.13 * s, 0.02 * s, 0.05 * s), Rf, 0.5), tone, 0.5)


def refine(ob, center, radius, cuts=1):
    """Subdivide the skin locally (the face, the hands) so painted lines and small forms stay crisp."""
    import bmesh
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    c = Vector(center)
    edges = [e for e in bm.edges if (e.verts[0].co - c).length < radius and (e.verts[1].co - c).length < radius]
    if edges:
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True, smooth=1.0)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bm.to_mesh(me)
    bm.free()
    me.update()


def skin(body, look, base, rough=0.48, head=None, sculpt=1.0, extra_sculpt=None, extra_paint=None, name="skin"):
    """Convert the blob, place the eyes, sculpt the definition and the face, paint the features.
    head: the dict a heads.* builder returned (its kind picks the face pass; its 'o' carries the options).
    Returns (skin object, [eyeballs])."""
    from . import face, heads
    from .core import Paint, Sculpt
    ob = body.blob.to_mesh(body.name + "-skin", look.skin(name))
    if head is not None:
        refine(ob, body.frames["head"][0], body.H * 0.62, cuts=1)
    for side in ("r", "l"):
        if "palm_" + side in body.marks:
            refine(ob, body.marks["palm_" + side], 0.11 * body.s, cuts=1)
    fit = Fit(ob)
    eyes = []
    o = (head or {}).get("o", {})
    if head and head.get("eyes"):
        spec = dict(head["eyes"])
        spec["fit"] = fit
        eyes = heads.eyes(body, look, o, spec)
    sc = Sculpt(ob)
    if sculpt > 0:
        sculpt_body(body, sc, fit, sculpt)
    if head:
        face.SCULPT[head["kind"]](body, sc, o)
    if extra_sculpt:
        extra_sculpt(sc, fit)
    sc.apply()
    pt = Paint(ob, base, rough)
    if head:
        face.PAINT[head["kind"]](body, pt, base, o)
    nails_and_soles(body, pt, base)
    if extra_paint:
        extra_paint(pt)
    pt.apply()
    return ob, eyes
