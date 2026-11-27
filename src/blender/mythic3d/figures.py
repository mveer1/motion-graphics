"""
The 3D mythic figures. Each follows its identity block in
.claude/skills/mythic-tales/references/figure-design.md section 4 (the single source of truth: skin colour
from the text, every attribute in its hand, the mount, the aura). Hands use the figure's own sides:
"right" is the figure's right (-X, the viewer's left in the front view).

Heroic (owner's direction, 2026-11-24): Rama, Hanuman, Shiva, Ganesha (body only; the belly stays),
Athena and Odin. Calm: the Tirthankara and the Buddha (smooth "lion-like" torso, lowered eyes).
"""

import math

import numpy as np
from mathutils import Matrix, Vector

from . import anatomy, armoury, dress, face, heads, props
from .body import Body
from .core import (
    Blob,
    Fit,
    Sculpt,
    V,
    basis,
    curve_dist,
    ellipsoid,
    hash_noise,
    join,
    mix_hex,
    r_ell,
    ribbon,
    seg_dist,
    smoothstep,
    sweep,
)

FIGURES = {
    "probe": {"name": "Calibration body", "rim": "#F2C46B"},
    "rama": {"name": "Rama", "tradition": "hindu", "rim": "#F6C96A"},
    "hanuman": {"name": "Hanuman", "tradition": "hindu", "rim": "#F4A04A"},
    "shiva": {"name": "Shiva", "tradition": "hindu", "rim": "#9FB0E0"},
    "ganesha": {"name": "Ganesha", "tradition": "hindu", "rim": "#F6CF7A"},
    "athena": {"name": "Athena", "tradition": "greek", "rim": "#FBE3A6"},
    "odin": {"name": "Odin", "tradition": "norse", "rim": "#B8C8DC"},
    "tirthankara": {"name": "Mahavira", "tradition": "jain", "rim": "#F2DCA0"},
    "buddha": {"name": "The Buddha", "tradition": "buddhist", "rim": "#F2DCA0"},
}

CREAM = "#F1E7CF"


# ---------------------------------------------------------------------- shared helpers
def hair_mask(body, P, front=0.24, back=-0.36, ears=True):
    """The hair cap in head space: a hairline at `front` on the brow, falling behind the ears to `back`."""
    q = face.head_q(body, P)
    phi = np.arctan2(q[:, 0], -q[:, 1])
    h = front - (front - back) * ((1 - np.cos(phi)) / 2) ** 0.85
    r = np.sqrt((q ** 2).sum(1))
    m = smoothstep(-0.012, 0.012, q[:, 2] - h) * (r < 0.62)
    if ears:
        ear = (np.abs(q[:, 0]) > 0.3) * smoothstep(0.1, 0.06, q[:, 2]) * smoothstep(-0.24, -0.18, q[:, 2]) * (q[:, 1] < 0.16) * (q[:, 1] > -0.08)
        m = m * (1 - ear)
    return m, q


def hair_cap(body, sc=None, pt=None, color="#1F1817", front=0.24, back=-0.36, rise=0.03, part=True, combed=True):
    if sc is not None:
        m, q = hair_mask(body, sc.P, front, back)
        H = body.H
        sc.region(m, rise * H)
        phi = np.arctan2(q[:, 0], -q[:, 1])
        if combed:
            sc.d += 0.0035 * H * m * np.sin(phi * 70 + q[:, 2] * 12)
        if part:
            sc.d -= 0.012 * H * np.exp(-(q[:, 0] / 0.012) ** 2) * m * (q[:, 1] < 0.12)
    if pt is not None:
        m, q = hair_mask(body, pt.P, front, back)
        pt.layer(m, color, 1.0, rough=0.55, name="hair")
        if combed:
            phi = np.arctan2(q[:, 0], -q[:, 1])
            pt.layer(m * (0.5 + 0.5 * np.sin(phi * 70 + q[:, 2] * 12)), mix_hex(color, "#FFFFFF", 0.12), 0.35)


def curl_region(q):
    """Head-space test for the curl cap (the hair of the Jina and the Buddha)."""
    phi = math.atan2(q.x, -q.y)
    return q.z > 0.26 - 0.62 * ((1 - math.cos(phi)) / 2) ** 0.85 and q.z > -0.2


def limb_band(fit, look, name, mat, a, b, t, width=0.035, thick=0.006, beads=None):
    a, b = V(a), V(b)
    return dress.band(name, fit, mat, a.lerp(b, t), b - a, width, thick, 0.003, 40, beads=beads)


def armlets(body, fit, look, sides=("r", "l"), keyura=True, kankana=True, gem="#B8282E"):
    gold = look.gold()
    out = []
    for sd in sides:
        S, E, W = body.J["shoulder_" + sd], body.J["elbow_" + sd], body.J["wrist_" + sd]
        if keyura:
            out.append(limb_band(fit, look, "keyura", gold, S, E, 0.34, 0.03 * body.s, 0.006, beads=(look.gem("ruby", gem), 0.007, 6)))
        if kankana:
            out.append(limb_band(fit, look, "kankana", gold, E, W, 0.9, 0.024 * body.s, 0.006))
            out.append(limb_band(fit, look, "kankana", gold, E, W, 0.82, 0.012 * body.s, 0.004))
    return out


def locks(body, look, mat, n, wind, length, start=(-0.18, 0.18), z0=-0.12, y0=0.3, r0=0.02, wave=0.05, droop=0.6, name="lock"):
    """Long locks of hair from the back of the head, falling and streaming in one wind."""
    out = []
    Wd = V(wind)
    for i in range(n):
        x = start[0] + (start[1] - start[0]) * (i / max(1, n - 1))
        p0 = body.hp(x, y0, z0 - 0.16 * abs(x))
        pts = [p0]
        for k in range(1, 6):
            t = k / 5
            pts.append(p0 + Vector((0, 0, -length * droop * t)) + Wd * (length * t ** 1.3) + Vector((0, 0, wave * math.sin(t * 6 + i)))
                       + Vector((x * 0.6 * t * body.H, 0.05 * t, 0)))
        out.append(dress.lock(name, mat, pts, r0 * body.s * (0.8 + 0.2 * ((i * 7) % 3)), 0.003))
    return join(out, name)


def frame_of(objs, pad=1.08):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        if o is None or o.type != "MESH" or o.name.startswith("glow"):
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector((min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z)))
            hi = Vector((max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)))
    lo.z = 0.0
    height = hi.z - lo.z
    width = max(hi.x - lo.x, hi.y - lo.y) * 1.05
    return Vector((0, 0, (hi.z + lo.z) / 2)), max(height, width * 1.3333) * pad


def finish(st, body, objs, meta):
    objs = [o for o in objs if o is not None]
    st.adopt(objs)
    c, f = frame_of(objs)
    return {"center": c, "frame": f, "head": body.frames["head"][0], "head_frame": body.H * 2.3, "meta": meta}


def fur(pt, sc, mask, base, light, H, seed=3):
    """Fur strokes: lighter and darker streaks in the colour and a fine combed relief."""
    if sc is not None:
        sc.d += 0.0016 * mask * hash_noise(sc.P * np.array([1.0, 1.0, 0.25]), 160.0, seed)
    if pt is not None:
        n = hash_noise(pt.P * np.array([1.0, 1.0, 0.3]), 120.0, seed)
        pt.layer(mask * smoothstep(0.2, 0.6, n), light, 0.55)
        pt.layer(mask * smoothstep(-0.2, -0.6, n), mix_hex(base, "#3A2410", 0.3), 0.4)


def cloth_skin(pt, mask, color, rough=0.75, name=None):
    pt.layer(mask, color, 1.0, rough=rough, name=name)


def thread(body, fit, look, name="yajnopavita", color=CREAM, r=0.0024, w=1.0):
    """The sacred thread over the left shoulder, across the chest to the right hip and round the back."""
    T_ = body.T_
    pts = [T_(0.12 * w, -0.01, 1.53), T_(0.07 * w, -0.115 * w, 1.4), T_(-0.03 * w, -0.12 * w, 1.22), T_(-0.12 * w, -0.085 * w, 1.07),
           T_(-0.15 * w, 0.04, 1.03), T_(-0.06 * w, 0.11 * w, 1.22), T_(0.08 * w, 0.1 * w, 1.44), T_(0.12 * w, 0.02, 1.53)]
    return dress.cord(name, fit, look.solid("thread", color, 0.6), pts, r=r * body.s)


def lap_mask(body, P, seat_top, rise=0.08):
    s = body.s
    return smoothstep(body.J["hip_r"].z + rise * s, body.J["hip_r"].z + (rise - 0.05) * s, P[:, 2]) * (P[:, 2] > seat_top - 0.02)


# ---------------------------------------------------------------------- calibration
def probe(look, st, o):
    body = Body("probe", o.get("preset", "warrior"), {
        "stance": 0.13,
        "arm_r": {"wrist": (-0.27, 0.02, 0.9), "hand": "relaxed", "palm": (1, 0, 0)},
        "arm_l": {"wrist": (0.27, 0.02, 0.9), "hand": "relaxed", "palm": (-1, 0, 0)},
    }).build()
    hd = heads.human(body, look, {"smile": 0.4})
    sk, eyes = anatomy.skin(body, look, o.get("skin", "#4E6286"), head=hd)
    return finish(st, body, [sk] + eyes, {"id": "probe"})


# ---------------------------------------------------------------------- Rama
def rama(look, st, o):
    """Valmiki's Rama in the forest years: cloud-dark skin, a jata knot, bark dhoti, the Kodanda grounded in
    his left hand, a tejas-lit arrow raised in his right, the quiver behind his left shoulder."""
    royal = o.get("attire") == "royal"
    skin_hex = "#6E4B36" if o.get("tone") == "brown" else "#4E6286"
    arrow_ax = (0.06, -0.04, 1.0)
    body = Body("rama", "warrior", {
        "stance": 0.15, "torso": (0.0, 2.5, 4.0), "head": (1.5, -4.0, 0.0),
        "arm_r": {"wrist": (-0.33, -0.07, 1.6), "pole": (-1, 0.3, -0.7), "hand": "grip", "grip_axis": arrow_ax, "fingers": (0.3, -1, 0)},
        "arm_l": {"wrist": (0.39, -0.02, 0.98), "pole": (1, 0.4, -0.2), "hand": "grip", "grip_axis": (0, 0, 1), "fingers": (-0.2, -1, 0)},
        "leg_r": {"turn": 16}, "leg_l": {"turn": 10},
    }).build()
    hd = heads.human(body, look, {"smile": 0.45, "lids": 0.15, "jaw": 1.05})
    hair_col = "#1F1817"

    def paint(pt):
        hair_cap(body, pt=pt, color=hair_col, front=0.25)
        for m, c in face.tilak_mask(body, pt.P, "vaishnava"):
            pt.layer(m, c, 1.0, rough=0.5)

    def sculpt(sc, fit):
        hair_cap(body, sc=sc, front=0.25)
        anatomy.kambu(body, sc)

    sk, eyes = anatomy.skin(body, look, skin_hex, head=hd, extra_sculpt=sculpt, extra_paint=paint)
    fit = Fit(sk)
    s, H, R = body.s, body.H, body.head_rot()
    T_ = body.T_
    objs = [sk] + eyes
    hair = look.solid("hair", hair_col, rough=0.55)
    navel_z = body.J["navel"].z + 0.03 * s
    knee_z = (body.J["knee_r"].z + body.J["knee_l"].z) / 2
    if royal:
        silk = look.cloth("silk-yellow", "#D9A43A", rough=0.45, sheen=0.6)
        objs.append(dress.skirt("dhoti", fit, silk, navel_z, knee_z - 0.04 * s, ease=0.014, flare=0.1, folds=13, fold_amp=0.01, seed=1))
        objs.append(dress.fall("kacha", fit, silk, (0, -0.12 * s, navel_z), (0, -0.14 * s, knee_z - 0.12 * s), width=0.12 * s))
        objs.append(dress.band("girdle", fit, look.cloth("sash-red", "#A8282A", 0.6), (0, 0, navel_z), (0, 0, 1), 0.05 * s, 0.01))
        objs.append(dress.kirita("kirita", look, body.hp(0, 0.02, 0.33), R, H, 1.25))
        for sx in (-1, 1):
            objs.append(dress.hoop("kundala", look.gold(), body.hp(sx * 0.35, 0.05, -0.26), R @ Vector((1, 0, 0)), 0.022 * s, 0.005 * s))
        objs.append(dress.beads_on("haar", fit, look.solid("pearl", "#F2ECDD", 0.25),
                                   [T_(-0.09, -0.06, 1.5), T_(-0.05, -0.12, 1.4), T_(0, -0.13, 1.37), T_(0.05, -0.12, 1.4), T_(0.09, -0.06, 1.5)], r=0.007))
        objs += armlets(body, fit, look)
    else:
        bark = look.cloth("bark", "#7A5634", rough=0.88, sheen=0.1)
        objs.append(dress.skirt("dhoti", fit, bark, navel_z, knee_z + 0.02 * s, ease=0.014, flare=0.09, folds=15, fold_amp=0.009, seed=1))
        objs.append(dress.fall("kacha", fit, bark, (0, -0.12 * s, navel_z - 0.01), (0, -0.14 * s, knee_z - 0.08 * s), width=0.11 * s))
        objs.append(dress.band("girdle", fit, look.solid("fibre", "#A07A48", rough=0.8), (0, 0, navel_z), (0, 0, 1), 0.034 * s, 0.012, rope=16))
        # The jata knot: hair coiled with banyan sap into "a rounded mass of matted locks" (Ayodhya 52.67-70).
        base = body.hp(0, 0.06, 0.36)
        knot, ztop = dress.coil_stack("jata", hair, base, R, [0.2 * H, 0.19 * H, 0.17 * H, 0.14 * H, 0.1 * H], 0.055 * H, 0.042 * H, 0.05)
        objs.append(knot)
        objs.append(ellipsoid("jata-top", base + R @ Vector((0, 0, ztop + 0.02 * H)), (0.08 * H, 0.08 * H, 0.06 * H), R, hair, 20))
    objs.append(locks(body, look, hair, 6, (-0.7, 0.4, 0.0), 0.42 * s, start=(-0.2, 0.2), z0=-0.15, r0=0.016))
    # Sacred thread over the left shoulder to the right hip; the quiver strap from the right shoulder.
    objs.append(thread(body, fit, look))
    objs.append(dress.strap("quiver-strap", fit, look.solid("leather", "#5A321C", 0.6),
                            [T_(-0.15, -0.03, 1.51), T_(-0.08, -0.12, 1.37), T_(0.03, -0.125, 1.21), T_(0.13, -0.08, 1.07)], width=0.03 * s))
    objs.append(armoury.quiver(look, T_(0.04, 0.17, 1.02), T_(0.2, 0.15, 1.62)))
    gr, gl = body.marks["grip_r"], body.marks["grip_l"]
    ax = V(arrow_ax).normalized()
    objs.append(armoury.arrow(look, gr - ax * 0.34 * s, gr + ax * 0.5 * s, glow=True))
    objs.append(armoury.kodanda(look, gl, (0, 0, 1), (1, 0.1, 0), height=max(1.5, 2 * gl.z - 0.04)))
    # The uttariya: over the left shoulder, down the back, its end lifting in the one wind.
    objs.append(ribbon("uttariya", [T_(0.13, -0.07, 1.46), T_(0.17, 0.06, 1.52), T_(0.08, 0.17, 1.36), T_(-0.12, 0.24, 1.16), T_(-0.36, 0.3, 1.02), T_(-0.6, 0.36, 0.95)],
                       [0.06 * s, 0.07 * s, 0.09 * s, 0.1 * s, 0.09 * s, 0.05 * s], (0, 1, 0.25), look.cloth("uttariya", "#C8862E", 0.7), thickness=0.003, waves=(0.025, 2)))
    head_c = body.frames["head"][0]
    objs += props.aura(look, st, "tejas", head_c + Vector((0, 0, -0.12)), 0.85 * s, y_back=0.34 * s)
    return finish(st, body, objs, {"id": "rama", "attire": "royal" if royal else "forest", "tone": o.get("tone", "blue"),
                                   "hands": {"right": "arrow (tejas)", "left": "Kodanda bow"}, "aura": "tejas"})


# ---------------------------------------------------------------------- Hanuman
def hanuman(look, st, o):
    """Hanuman, Veera form: a vanara face on a mighty body, golden fur, the great gada on his right
    shoulder, right fist across the body, left fist on the hip, the tail rising on his left; agni aura."""
    dasa = o.get("form") == "dasa"
    pose = {"stance": 0.17, "head": (-2.0, 0.0, 0.0), "leg_r": {"turn": 14}, "leg_l": {"turn": 14}}
    gada_ax = (-0.34, 0.22, 1.0)
    if dasa:
        pose["arm_r"] = {"wrist": (-0.03, -0.24, 1.38), "pole": (-1, 0.2, -0.6), "hand": "anjali", "fingers": (0.15, -0.2, 1), "palm": (1, 0, 0)}
        pose["arm_l"] = {"wrist": (0.03, -0.24, 1.38), "pole": (1, 0.2, -0.6), "hand": "anjali", "fingers": (-0.15, -0.2, 1), "palm": (-1, 0, 0)}
    else:
        pose["arm_r"] = {"wrist": (-0.14, -0.22, 1.22), "pole": (-1, 0.25, -0.5), "hand": "grip", "grip_axis": gada_ax, "fingers": (1, -0.4, 0.1)}
        pose["arm_l"] = {"wrist": (0.27, -0.02, 1.02), "pole": (1, 0.7, 0.2), "hand": "fist", "fingers": (-0.4, -0.2, -1), "palm": (-1, 0.2, 0)}
    body = Body("hanuman", "titan", pose).build()
    hd = heads.vanara(body, look, {"fierce": 1.0, "iris": "#5A3410"})
    gold_fur, pale = "#C98B3E", "#E2AC5E"
    s, H, R = body.s, body.H, body.head_rot()

    def masks(P):
        q = face.head_q(body, P)
        facem = np.clip(face.g2(q[:, 0], q[:, 2], 0, -0.16, 0.25, 0.27) * 1.7, 0, 1) * face.front(q, -0.14, -0.26)
        chest = r_ell(P, body.T_(0, -0.1, 1.25), (0.14 * s, 0.12 * s, 0.2 * s), None, 0.6)
        return facem, chest

    def sculpt(sc, fit):
        facem, chest = masks(sc.P)
        fur(None, sc, 1 - smoothstep(0.3, 0.6, facem), gold_fur, pale, H)

    def paint(pt):
        facem, chest = masks(pt.P)
        pt.layer(chest * (1 - facem), pale, 0.6)
        fur(pt, None, 1 - smoothstep(0.3, 0.6, facem), gold_fur, mix_hex(pale, "#FFFFFF", 0.2), H)

    sk, eyes = anatomy.skin(body, look, gold_fur, rough=0.62, head=hd, extra_sculpt=sculpt, extra_paint=paint)
    fit = Fit(sk)
    objs = [sk] + eyes
    T_ = body.T_
    navel_z = body.J["navel"].z
    red = look.cloth("dhoti-red", "#B8322A", rough=0.7)
    gold = look.gold()
    thigh_z = (body.J["hip_r"].z + body.J["knee_r"].z) / 2
    objs.append(dress.skirt("dhoti", fit, red, navel_z, thigh_z - 0.02 * s, ease=0.016, flare=0.1, folds=11, fold_amp=0.01, seed=2))
    objs.append(dress.skirt("dhoti-hem", fit, gold, thigh_z + 0.012 * s, thigh_z - 0.03 * s, ease=0.026, flare=0.1, folds=11, fold_amp=0.01, rows=3, seed=2))
    objs.append(dress.fall("kacha", fit, red, (0, -0.15 * s, navel_z), (0, -0.17 * s, thigh_z - 0.1 * s), width=0.13 * s))
    objs.append(dress.band("udarabandha", fit, gold, T_(0, 0, 1.14), (0, 0, 1), 0.04 * s, 0.008, beads=(look.gem("ruby", "#B8282E"), 0.008, 10)))
    objs.append(dress.band("girdle", fit, look.cloth("girdle-red", "#8E1F22", 0.6), (0, 0, navel_z + 0.01), (0, 0, 1), 0.05 * s, 0.012))
    objs.append(dress.beads_on("haar", fit, gold, [T_(-0.1, -0.05, 1.53), T_(-0.06, -0.14, 1.42), T_(0, -0.155, 1.39), T_(0.06, -0.14, 1.42), T_(0.1, -0.05, 1.53)],
                               r=0.009 * s, big=(5, look.gem("ruby", "#B8282E"), 0.012 * s)))
    objs.append(thread(body, fit, look, "munja", "#D8C48A", 0.0028, 1.15))
    objs += armlets(body, fit, look)
    for sx in (-1, 1):
        objs.append(dress.hoop("kundala", gold, body.hp(sx * 0.36, 0.0, -0.12), R @ Vector((1, 0, 0)), 0.03 * s, 0.006 * s))
    objs.append(dress.kirita("kirita", look, body.hp(0, 0.02, 0.3), R, H, 1.05))
    fur_mat = look.solid("tail-fur", gold_fur, rough=0.7)
    tail = [T_(0, 0.13, 0.95), T_(0.12, 0.26, 0.82), T_(0.38, 0.3, 0.92), T_(0.56, 0.24, 1.3), T_(0.55, 0.16, 1.72), T_(0.45, 0.1, 2.02), T_(0.32, 0.08, 2.1)]
    objs.append(sweep("puchha", tail, [0.045 * s, 0.042 * s, 0.038 * s, 0.033 * s, 0.027 * s, 0.02 * s, 0.012 * s], sides=14, material=fur_mat, n_per=6))
    objs.append(ellipsoid("puchha-tip", tail[-1], (0.022 * s,) * 3, None, fur_mat, 14))
    hands = {"right": "anjali", "left": "anjali"}
    if not dasa:
        gr = body.marks["grip_r"]
        ax = V(gada_ax).normalized()
        objs.append(armoury.gada(look, gr, gr + ax * 0.92 * s))
        hands = {"right": "gada on the right shoulder", "left": "fist on the hip"}
    objs += props.aura(look, st, "agni", T_(0, 0.0, 1.5), 1.0 * s, y_back=0.36 * s)
    return finish(st, body, objs, {"id": "hanuman", "form": "dasa" if dasa else "veera", "hands": hands, "aura": "agni"})


# ---------------------------------------------------------------------- Shiva
def shiva(look, st, o):
    """Shiva: ash-pale body, the blue throat, three eyes over the tripundra, the jata-makuta with the crescent
    and Ganga, locks flying like Nataraja's, the cobra at the neck, the trishula planted in his left hand,
    the right hand raised (fear not), the tiger skin; a cosmic aura."""
    body = Body("shiva", "ascetic", {
        "stance": 0.13, "torso": (0.0, -2.0, -3.0), "head": (1.0, 3.0, 0.0),
        "arm_r": {"wrist": (-0.32, -0.08, 1.52), "pole": (-1, 0.2, -0.6), "hand": "open", "fingers": (-0.08, -0.1, 1), "palm": (0, -1, 0)},
        "arm_l": {"wrist": (0.35, -0.04, 1.1), "pole": (1, 0.4, -0.3), "hand": "grip", "grip_axis": (0, 0, 1), "fingers": (-0.2, -1, 0)},
        "leg_r": {"turn": 14}, "leg_l": {"turn": 12},
    }).build()
    hd = heads.human(body, look, {"smile": 0.35, "lids": 0.2})
    ash, throat = "#A6B8C7", "#3E5E9E"
    s, H, R = body.s, body.H, body.head_rot()
    hair_col = "#2A1E1A"

    def paint(pt):
        hair_cap(body, pt=pt, color=hair_col, front=0.27, part=False)
        for m, c in face.tilak_mask(body, pt.P, "tripundra"):
            pt.layer(m, c, 1.0, rough=0.6)
        q = face.head_q(body, pt.P)
        third = face.almond(q[:, 2], q[:, 0], 0.175, 0.0, 0.042, 0.016, lift=0.0)[0] * face.front(q)
        pt.layer(third, "#F4EEE4", 1.0)
        pt.layer(third * face.g2(q[:, 0], q[:, 2], 0, 0.175, 0.01, 0.02), "#7A1E1A", 1.0)
        neck = r_ell(pt.P, body.T_(0, -0.03, 1.56), (0.07 * s, 0.075 * s, 0.07 * s), None, 0.4)
        pt.layer(neck, throat, 0.9)

    sk, eyes = anatomy.skin(body, look, ash, head=hd, extra_sculpt=lambda sc, fit: hair_cap(body, sc=sc, front=0.27, part=False), extra_paint=paint)
    fit = Fit(sk)
    objs = [sk] + eyes
    T_ = body.T_
    hair = look.solid("jata", hair_col, rough=0.6)
    gold = look.gold()
    # The jata-makuta piled high and bound, the crescent on his left, Ganga running out of the knot.
    base = body.hp(0, 0.05, 0.36)
    mk, ztop = dress.coil_stack("jata-makuta", hair, base, R, [0.24 * H, 0.23 * H, 0.22 * H, 0.2 * H, 0.18 * H, 0.15 * H, 0.11 * H], 0.06 * H, 0.05 * H, 0.08, seed=2)
    objs.append(mk)
    objs.append(dress.band("jata-band", Fit(mk), gold, base + R @ Vector((0, 0, 0.07 * H)), R @ Vector((0, 0, 1)), 0.03 * s, 0.008,
                           beads=(look.gem("ruby", "#B8282E"), 0.008, 8)))
    objs.append(props.crescent(look, base + R @ Vector((0.17 * H, -0.12 * H, 0.32 * H)), R @ Vector((0, -1, 0)), R @ Vector((0.4, 0, 1)), 0.07 * s))
    objs.append(props.stream(look, [base + R @ Vector((-0.1 * H, -0.1 * H, 0.42 * H)), base + R @ Vector((-0.3 * H, -0.05 * H, 0.5 * H)),
                                    base + R @ Vector((-0.5 * H, 0.0, 0.45 * H)), base + R @ Vector((-0.62 * H, 0.05 * H, 0.3 * H))]))
    # Locks flying out in waves on both sides (Nataraja).
    fly = []
    for sx in (-1, 1):
        for i in range(7):
            p0 = body.hp(sx * 0.28, 0.12, 0.18 - 0.07 * i)
            pts = [p0] + [p0 + Vector((sx * 0.62 * (k / 5) * s, 0.05 * (k / 5) * s, (0.06 * math.sin((k / 5) * 7 + i) + (i - 3) * 0.04 * (k / 5)) * s)) for k in range(1, 6)]
            fly.append(dress.lock("jata-lock", hair, pts, 0.016 * s, 0.004))
    objs.append(join(fly, "jata-locks"))
    # The cobra coiled at the neck, its hood raised beside his head on his left.
    nk = [T_(0.075 * math.cos(a), 0.07 * math.sin(a) - 0.01, 1.5 + 0.012 * a) for a in np.linspace(-1.2, 5.2, 14)]
    objs.append(props.cobra(look, nk, body.hp(0.42, -0.08, -0.25), (0.2, -1, 0)))
    objs.append(dress.beads_on("rudraksha", fit, look.solid("rudraksha", "#6A3A22", 0.6),
                               [T_(-0.11, -0.05, 1.52), T_(-0.08, -0.13, 1.36), T_(0, -0.135, 1.3), T_(0.08, -0.13, 1.36), T_(0.11, -0.05, 1.52)], r=0.0085 * s))
    for sd in ("r", "l"):
        objs.append(limb_band(fit, look, "rudraksha-band", look.solid("rudraksha", "#6A3A22", 0.6), body.J["shoulder_" + sd], body.J["elbow_" + sd], 0.36, 0.018 * s, 0.01))
    objs.append(thread(body, fit, look))
    # Mismatched earrings: a makara hoop in the right ear, a patra disc in the left.
    objs.append(dress.hoop("makara-kundala", gold, body.hp(-0.36, 0.04, -0.26), R @ Vector((1, 0, 0)), 0.032 * s, 0.006 * s))
    objs.append(ellipsoid("patra-kundala", body.hp(0.36, 0.04, -0.22), (0.006 * s, 0.028 * s, 0.028 * s), R, gold, 20))
    navel_z = body.J["navel"].z
    knee_z = body.J["knee_r"].z
    tiger = look.stripes("tiger", "#D9902E", "#2A1A10", 22.0)
    objs.append(dress.skirt("tiger-skin", fit, tiger, navel_z - 0.01, knee_z + 0.07 * s, ease=0.016, flare=0.08, folds=9, fold_amp=0.008, seed=4))
    objs.append(dress.fall("tiger-paw", fit, tiger, (0.03 * s, -0.13 * s, navel_z - 0.02), (0.04 * s, -0.15 * s, knee_z + 0.02 * s), width=0.08 * s, pleats=2, depth=0.006))
    objs.append(dress.band("tiger-knot", fit, look.solid("hide-belt", "#7A4A24", 0.7), (0, 0, navel_z), (0, 0, 1), 0.03 * s, 0.01, rope=12))
    gl = body.marks["grip_l"]
    objs.append(armoury.trishula(look, Vector((gl.x, gl.y, 0.02)), Vector((gl.x, gl.y, 2.25 * s))))
    objs += props.aura(look, st, "cosmic", body.frames["head"][0] + Vector((0, 0, -0.08)), 0.86 * s, y_back=0.36 * s)
    return finish(st, body, objs, {"id": "shiva", "hands": {"right": "abhaya (raised, fear not)", "left": "trishula with the damaru"},
                                   "aura": "cosmic", "marks": ["blue throat", "third eye", "tripundra", "crescent on his left", "Ganga", "cobra"]})


# ---------------------------------------------------------------------- Ganesha
def ganesha(look, st, o):
    """Ganesha as the Ganapati Atharvashirsha sees him: red, pot-bellied, winnowing-fan ears, one tusk;
    goad (upper right), noose (upper left), the broken tusk (lower right), the boon (lower left); the trunk
    to his left to a modaka; a serpent belt; seated on a lotus with the mouse below."""
    skin_hex = "#D9A35B" if o.get("tone") == "gold" else "#C65A3E"
    seat_top = 0.62
    tusk_ax = (0.1, -0.3, 1.0)
    body = Body("ganesha", "ganesha", {
        "seated": "sukhasana", "seat_z": seat_top, "knee_wide": 0.44, "head": (6.0, 0.0, 0.0),
        "extra_arms": ["r2", "l2"],
        "arm_r2": {"shoulder": (0.0, 0.06, 0.02), "wrist": (-0.46, 0.06, 1.6), "torso_space": True, "pole": (-1, 0.4, -0.6), "hand": "grip",
                   "grip_axis": (-0.08, 0, 1), "fingers": (0.6, -0.8, 0)},
        "arm_l2": {"shoulder": (0.0, 0.06, 0.02), "wrist": (0.46, 0.06, 1.6), "torso_space": True, "pole": (1, 0.4, -0.6), "hand": "grip",
                   "grip_axis": (0.1, 0, 1), "fingers": (-0.6, -0.8, 0)},
        "arm_r": {"wrist": (-0.34, -0.22, 1.08), "torso_space": True, "pole": (-1, 0.3, -0.5), "hand": "grip", "grip_axis": tusk_ax, "fingers": (0.4, -1, -0.2)},
        "arm_l": {"wrist": (0.34, -0.26, 1.02), "torso_space": True, "pole": (1, 0.3, -0.5), "hand": "varada", "fingers": (0.15, -0.3, -1), "palm": (0, -1, 0.1)},
    }).build()
    hd = heads.elephant(body, look, {"iris": "#2A1A12"})
    s, H, R = body.s, body.H, body.head_rot()
    crimson = "#8E1F2A"

    def paint(pt):
        for m, c in face.tilak_mask(body, pt.P, "tripundra"):
            pt.layer(m, c, 1.0, rough=0.6)
        cloth_skin(pt, lap_mask(body, pt.P, seat_top), crimson, name="dhoti")

    def sculpt(sc, fit):
        d, f = curve_dist(sc.P, hd["trunk"])
        sc.d -= 0.004 * H * (d < 0.13 * H) * (f > 0.15) * (np.sin(f * 90) > 0.6)

    sk, eyes = anatomy.skin(body, look, skin_hex, head=hd, extra_sculpt=sculpt, extra_paint=paint)
    fit = Fit(sk)
    objs = [sk] + eyes + hd["tusks"]
    T_ = body.T_
    gold = look.gold()
    for sx in (-1, 1):
        c = body.hp(sx * 0.5, 0.02, -0.05)
        Re = R @ Matrix.Rotation(math.radians(-sx * 14), 3, "Z")
        objs.append(ellipsoid("ear", c, (0.32 * H, 0.03 * H, 0.42 * H), Re, look.solid("ear", mix_hex(skin_hex, "#E9A08A", 0.2), rough=0.55), 32))
        rim = [c + Re @ Vector((0.32 * H * math.cos(a), 0.0, 0.42 * H * math.sin(a))) for a in np.linspace(0, 2 * math.pi, 41)[:-1]]
        objs.append(sweep("ear-rim", rim, 0.012 * H, sides=8, material=gold, n_per=1, closed=True))
    objs.append(dress.kirita("kirita", look, body.hp(0, 0.04, 0.4), R, H, 1.0))
    snake = look.solid("cobra", "#2F6A45", 0.4, coat=0.3)
    objs.append(dress.band("serpent-belt", fit, snake, T_(0, -0.05, 1.1), (0, 0, 1), 0.03 * s, 0.014, rope=9))
    hood_at = fit.nearest(T_(0, -0.45, 1.1))[0]
    objs.append(ellipsoid("serpent-hood", hood_at + Vector((0, -0.03, 0.03)), (0.035, 0.012, 0.05), None, snake, 18))
    objs.append(dress.beads_on("pearls", fit, look.solid("pearl", "#F2ECDD", 0.25),
                               [T_(-0.14, -0.06, 1.5), T_(-0.1, -0.2, 1.34), T_(0, -0.24, 1.28), T_(0.1, -0.2, 1.34), T_(0.14, -0.06, 1.5)], r=0.009 * s))
    objs.append(dress.cord("yajnopavita", fit, look.solid("thread", CREAM, 0.6),
                           [T_(0.15, -0.02, 1.52), T_(0.1, -0.2, 1.36), T_(-0.05, -0.3, 1.12), T_(-0.2, -0.2, 0.98), T_(-0.24, 0.05, 1.0),
                            T_(-0.08, 0.14, 1.22), T_(0.1, 0.12, 1.44), T_(0.15, 0.02, 1.52)], r=0.0028 * s))
    objs += armlets(body, fit, look, sides=("r", "l", "r2", "l2"))
    g2r, g2l, gr = body.marks["grip_r2"], body.marks["grip_l2"], body.marks["grip_r"]
    objs.append(armoury.ankusha(look, g2r, g2r + V((-0.08, 0, 1)).normalized() * 0.62 * s))
    objs.append(armoury.pasha(look, g2l + Vector((0, 0, 0.05 * s)), (0.2, -1, 0), 0.1 * s))
    axt = V(tusk_ax).normalized()
    objs.append(sweep("tusk-held", [gr - axt * 0.03 * s, gr + axt * 0.12 * s, gr + axt * 0.2 * s + Vector((0.02, 0, 0))],
                      [0.018 * s, 0.014 * s, 0.003 * s], sides=10, material=look.solid("ivory", "#EFE4C8", rough=0.35, cavity=0.3), n_per=4))
    objs.append(armoury.modaka(look, hd["trunk_tip"] + Vector((0.02, -0.04, -0.06)) * s, 0.05 * s))
    seat, front = props.lotus_seat(look, seat_top, 0.58 * s, 0.24 * s)
    objs += seat
    objs += props.mouse(look, front + Vector((0, -0.08, -0.12)), (0, -1, 0), 1.1 * s)
    objs += props.aura(look, st, "lotus", body.frames["head"][0] + Vector((0, 0, -0.1)), 1.0 * s, y_back=0.42 * s)
    return finish(st, body, objs, {"id": "ganesha", "tone": o.get("tone", "red"), "hands": {"upper right": "ankusha (goad)", "upper left": "pasha (noose)",
                                   "lower right": "broken tusk", "lower left": "varada (boon)"}, "trunk": "to his left, to a modaka", "aura": "lotus"})


# ---------------------------------------------------------------------- Athena
def athena(look, st, o):
    """Athena Promachos: the spear raised level overhead in her right hand, the round aspis forward on her
    left arm, the Attic helmet with three crests, the peplos and the aegis; a radiant aura (no ring)."""
    spear_dir = V((0.78, -0.58, 0.14)).normalized()
    body = Body("athena", "goddess", {
        "stance": 0.12, "torso": (0.0, 3.0, -6.0), "head": (0.0, 10.0, 0.0),
        "arm_r": {"wrist": (-0.18, -0.02, 1.86), "pole": (-1, 0.3, -0.4), "hand": "grip", "grip_axis": tuple(spear_dir), "fingers": (0.2, 0.1, 1)},
        "arm_l": {"wrist": (0.38, -0.16, 1.14), "pole": (1, 0.2, -0.5), "hand": "grip", "grip_axis": (0, 0, 1), "fingers": (-0.3, -1, 0)},
        "leg_r": {"ankle": (-0.11, 0.06, 0.072), "turn": 18}, "leg_l": {"ankle": (0.12, -0.08, 0.072), "turn": 8},
    }).build()
    hd = heads.human(body, look, {"female": True, "smile": 0.15, "lids": 0.1, "iris": "#4E6E80", "nose": 0.9})
    ivory, peplos, aegis_c = "#E6C7A2", "#EFE6D2", "#C9A24E"
    s = body.s
    hair_col = "#4A2E1E"

    def body_masks(P):
        top = r_ell(P, body.T_(0, 0, 1.3), (0.26 * s, 0.2 * s, 0.27 * s), body.torso_rot(), 0.15)
        aeg = r_ell(P, body.T_(0, -0.01, 1.42), (0.24 * s, 0.17 * s, 0.13 * s), body.torso_rot(), 0.1) * (P[:, 2] < body.T_(0, 0, 1.56).z)
        return top, aeg

    def scales(P):
        return np.sin(P[:, 0] * 260) * np.sin(P[:, 2] * 260)

    def sculpt(sc, fit):
        hair_cap(body, sc=sc, front=0.22, back=-0.4, rise=0.035)
        top, aeg = body_masks(sc.P)
        sc.region(top, 0.006 * s)
        sc.region(aeg, 0.006 * s)
        sc.d += 0.002 * s * aeg * scales(sc.P)

    def paint(pt):
        hair_cap(body, pt=pt, color=hair_col, front=0.22, back=-0.4)
        top, aeg = body_masks(pt.P)
        cloth_skin(pt, top, peplos, 0.7)
        cloth_skin(pt, aeg, aegis_c, 0.45)
        pt.layer(aeg * (scales(pt.P) > 0.3), "#8E6E2A", 0.6, metal=0.4)

    sk, eyes = anatomy.skin(body, look, ivory, head=hd, extra_sculpt=sculpt, extra_paint=paint)
    fit = Fit(sk)
    objs = [sk] + eyes
    T_ = body.T_
    cloth = look.cloth("peplos", peplos, rough=0.72, sheen=0.4)
    waist = body.J["navel"].z + 0.06 * s
    objs.append(dress.skirt("peplos", fit, cloth, waist, 0.03, ease=0.016, flare=0.14, folds=21, fold_amp=0.012, rows=40, seed=5, hem_wave=0.02))
    objs.append(dress.skirt("peplos-hem", fit, look.cloth("meander", "#A8322A", 0.7), 0.075, 0.03, ease=0.03, flare=0.14, folds=21, fold_amp=0.012, rows=3, seed=5))
    objs.append(dress.skirt("apoptygma", fit, cloth, T_(0, 0, 1.24).z, waist - 0.14 * s, ease=0.02, flare=0.2, folds=17, fold_amp=0.012, seed=6))
    snake = look.solid("snake", "#3F6B4A", 0.4, coat=0.3)
    objs.append(dress.band("snake-belt", fit, snake, (0, 0, waist + 0.01), (0, 0, 1), 0.025 * s, 0.012, rope=10))
    fringe = []
    for k in range(13):
        a = math.radians(-120 + 240 * k / 12)
        on, nn = fit.nearest(T_(0.24 * math.sin(a), -0.19 * math.cos(a) * 0.9, 1.3 + 0.05 * abs(math.sin(a))))
        fringe.append(sweep("aegis-snake", [on, on + nn * 0.02 + Vector((0, 0, -0.035)), on + nn * 0.012 + Vector((0.01, 0, -0.06))], [0.006, 0.005, 0.002],
                            sides=6, material=snake, n_per=3))
    objs.append(join(fringe, "aegis-fringe"))
    gp, gn = fit.nearest(T_(0, -0.2, 1.4))
    objs.append(ellipsoid("gorgoneion", gp + gn * 0.008, (0.04 * s, 0.012 * s, 0.045 * s), basis(Vector((0, 0, 1)), gn), look.gold("gorgoneion", "#D9A44A", 0.3), 20))
    objs.append(dress.helmet("helmet", look, body))
    objs.append(locks(body, look, look.solid("hair", hair_col, 0.55), 5, (0.15, 0.3, 0), 0.32 * s, start=(-0.24, 0.24), z0=-0.3, y0=0.18, r0=0.014))
    objs.append(ribbon("himation", [T_(-0.16, 0.06, 1.48), T_(-0.05, 0.18, 1.3), T_(0.2, 0.28, 1.1), T_(0.5, 0.36, 0.95), T_(0.82, 0.42, 0.88), T_(1.0, 0.45, 0.86)],
                       [0.1 * s, 0.16 * s, 0.18 * s, 0.16 * s, 0.12 * s, 0.05 * s], (0, -1, 0.2), look.cloth("himation", "#A8322A", 0.7), thickness=0.004, waves=(0.035, 3)))
    gr = body.marks["grip_r"]
    objs.append(armoury.dory(look, gr - spear_dir * 1.0 * s, gr + spear_dir * 1.25 * s))
    shield_c = body.J["elbow_l"].lerp(body.J["wrist_l"], 0.55) + V((0.1, -0.02, 0.0)) * s
    objs.append(armoury.aspis(look, shield_c, (1.0, -0.55, 0.02), (0, 0, 1), 0.46 * s))
    objs += props.aura(look, st, "radiant", body.frames["head"][0] + Vector((0, 0, -0.15)), 0.9 * s, y_back=0.34 * s)
    return finish(st, body, objs, {"id": "athena", "hands": {"right": "dory raised level overhead", "left": "aspis on the forearm"}, "aura": "radiant",
                                   "check": "the Parthenos holds a Nike; this is the Promachos pose"})


# ---------------------------------------------------------------------- Odin
def odin(look, st, o):
    """Odin as Grimnir: old, tall, weathered; his right eye given and scarred, the left burning ice-blue; a
    long grey beard; the broad slouched hat; a dark-blue mantle spread in a storm wind; Gungnir planted in
    his right hand, Draupnir on his left arm; Huginn on his right shoulder, Muninn flying to his left hand."""
    body = Body("odin", "elder", {
        "stance": 0.14, "head": (-3.0, 0.0, 0.0),
        "arm_r": {"wrist": (-0.34, -0.06, 1.14), "pole": (-1, 0.4, -0.3), "hand": "grip", "grip_axis": (0, 0, 1), "fingers": (0.2, -1, 0)},
        "arm_l": {"wrist": (0.4, -0.1, 1.56), "pole": (1, 0.2, -0.7), "hand": "open", "fingers": (0.25, -0.2, 1), "palm": (0.1, -1, 0.1)},
        "leg_r": {"turn": 12}, "leg_l": {"turn": 12},
    }).build()
    hd = heads.human(body, look, {"smile": 0.0, "lids": 0.15, "closed_eye": "r", "iris": "#6FB8E0", "glow_eye": 4.0, "jaw": 1.1,
                                  "brow_lift": -0.6, "brow": "#8E877E"})
    skin_c, tunic, wraps = "#D2A080", "#6E5A44", "#4A3A2C"
    s, H, R = body.s, body.H, body.head_rot()

    def masks(P):
        chest = body.T_(0, 0, 1.45).z
        sleeves = 0
        for sd in ("r", "l"):
            dd, t = seg_dist(P, body.J["shoulder_" + sd], body.J["wrist_" + sd] - (body.J["wrist_" + sd] - body.J["elbow_" + sd]) * 0.12)
            sleeves = np.maximum(sleeves, (dd < 0.09 * s) * 1.0)
        torso = r_ell(P, body.T_(0, 0, 1.22), (0.3 * s, 0.24 * s, 0.34 * s), None, 0.1) * (P[:, 2] < chest + 0.1 * s)
        legs = (P[:, 2] < body.J["knee_r"].z + 0.04 * s) * (P[:, 2] > 0.06 * s) * 1.0
        feet = (P[:, 2] < 0.08 * s) * 1.0
        return np.clip(torso + sleeves, 0, 1), legs, feet

    def wraps_pattern(P):
        return np.sin(P[:, 2] * 140 + P[:, 0] * 40) > 0.5

    def sculpt(sc, fit):
        hair_cap(body, sc=sc, front=0.18, back=-0.45, rise=0.03, part=False)
        torso, legs, feet = masks(sc.P)
        sc.region(torso, 0.008 * s)
        sc.region(legs, 0.006 * s)
        sc.d += 0.003 * s * legs * wraps_pattern(sc.P)

    def paint(pt):
        hair_cap(body, pt=pt, color="#A9A39A", front=0.18, back=-0.45, part=False)
        torso, legs, feet = masks(pt.P)
        cloth_skin(pt, torso, tunic, 0.85)
        cloth_skin(pt, legs, wraps, 0.85)
        pt.layer(legs * wraps_pattern(pt.P), "#3A2C20", 0.7)
        cloth_skin(pt, feet, "#2E241C", 0.6)

    sk, eyes = anatomy.skin(body, look, skin_c, head=hd, extra_sculpt=sculpt, extra_paint=paint)
    fit = Fit(sk)
    objs = [sk] + eyes
    T_ = body.T_
    grey = look.solid("grey-hair", "#A9A39A", rough=0.6)
    # Sithskegg, the long beard, and the moustache, blown in the storm wind (to his left).
    bb = Blob("beard", res=0.003)
    hp = body.hp
    for i in range(9):
        t = i / 8
        bb.ell(hp(0.03 * t + 0.08 * t * t, -0.36 - 0.06 * t, -0.42 - 0.95 * t), ((0.2 - 0.1 * t) * H, (0.1 - 0.03 * t) * H, 0.18 * H), R, soft=0.62)
    for sx in (-1, 1):
        bb.cap(hp(sx * 0.03, -0.43, -0.25), hp(sx * 0.2, -0.36, -0.38), 0.035 * H, soft=0.6)
        bb.ell(hp(sx * 0.2, -0.22, -0.3), (0.06 * H, 0.1 * H, 0.16 * H), R, soft=0.62)
    beard = bb.to_mesh("beard", grey)
    bsc = Sculpt(beard)
    bsc.d += 0.004 * s * np.sin(bsc.P[:, 0] * 380 + bsc.P[:, 1] * 120)
    bsc.apply()
    objs.append(beard)
    objs.append(locks(body, look, grey, 7, (0.35, 0.3, 0), 0.4 * s, start=(-0.28, 0.28), z0=-0.18, y0=0.22, r0=0.017))
    objs.append(dress.slouch_hat("hat", look, body, tilt=10.0))
    mantle = look.cloth("mantle", "#2E3E66", rough=0.82, sheen=0.3)
    objs.append(dress.skirt("tunic-skirt", fit, look.cloth("tunic", tunic, 0.85), body.J["navel"].z - 0.02, body.J["knee_r"].z + 0.1 * s, ease=0.02, flare=0.12,
                            folds=13, fold_amp=0.01, seed=7))
    objs.append(dress.band("belt", fit, look.solid("belt", "#2E2018", 0.55), (0, 0, body.J["navel"].z), (0, 0, 1), 0.05 * s, 0.01))
    objs.append(dress.cloak("mantle", fit, mantle, (0, 0.02 * s), T_(0, 0, 1.6).z, 0.04, r_top=0.1 * s, r_hem=0.72 * s, span=150, wind=(0.55, 0.25), folds=9, rows=40, seed=1,
                            keep=lambda p: not (p.x > 0.24 * s and p.z > 1.38 * s)))
    objs.append(sweep("hood", [T_(-0.17, 0.08, 1.53), T_(-0.1, 0.17, 1.52), T_(0, 0.2, 1.5), T_(0.1, 0.17, 1.52), T_(0.17, 0.08, 1.53)], 0.05 * s, sides=12,
                      material=mantle, n_per=4))
    objs.append(limb_band(fit, look, "draupnir", look.gold(), body.J["elbow_l"], body.J["wrist_l"], 0.45, 0.028 * s, 0.012))
    gr = body.marks["grip_r"]
    objs.append(armoury.gungnir(look, Vector((gr.x, gr.y, 0.02)), Vector((gr.x, gr.y, 2.35 * s))))
    sh = fit.nearest(body.J["shoulder_r"] + Vector((-0.02, 0, 0.12)) * s)[0]
    objs.append(props.raven(look, sh + Vector((0, 0, 0.07)) * s, (0.2, -1, 0), "perched", 1.0 * s, "huginn"))
    objs.append(props.raven(look, body.marks["palm_l"] + Vector((0.18, -0.05, 0.12)) * s, (-0.8, -0.2, -0.1), "flying", 1.0 * s, "muninn"))
    objs += props.aura(look, st, "storm", body.frames["head"][0] + Vector((0, 0, -0.2)), 1.05 * s, y_back=0.5 * s)
    return finish(st, body, objs, {"id": "odin", "hands": {"right": "Gungnir, planted", "left": "raised to Muninn; Draupnir on the left arm"},
                                   "eyes": {"right": "given at Mimir's well (closed, scarred)", "left": "burning ice-blue"}, "aura": "storm"})


# ---------------------------------------------------------------------- the Tirthankara
def tirthankara(look, st, o):
    """A seated Tirthankara in meditation (padmasana, dhyana): "a placid look, naked, young and beautiful"
    (Brihat Samhita 57.45), broad shoulders, narrow waist, long ears, tiny curls with no ushnisha, the
    shrivatsa; the rayed halo and the triple umbrella; the lanchhana (lion: Mahavira) on the plinth."""
    emblem = o.get("emblem", "lion")
    if emblem not in ("lion", "snake"):
        # The lanchhana is the only mark that tells one Jina from another: never fall back to Mahavira's lion.
        raise ValueError(f"3D lanchhana '{emblem}' is not built yet (lion: Mahavira, snake: Parshvanatha); use the 2D tirthankara-human")
    sve = o.get("sect") == "svetambara"
    seat_top = 0.6
    skin_hex = "#4E6286" if emblem in ("conch", "snake") else "#D9A35B"
    body = Body("jina", "calm", {
        "seated": "padmasana", "seat_z": seat_top, "knee_wide": 0.42,
        "arm_r": {"wrist": (-0.05, -0.22, 0.99), "torso_space": True, "pole": (-1, 0.1, -0.3), "hand": "dhyana", "fingers": (1, -0.1, 0), "palm": (0, 0, 1)},
        "arm_l": {"wrist": (0.06, -0.2, 0.97), "torso_space": True, "pole": (1, 0.1, -0.3), "hand": "dhyana", "fingers": (-1, -0.1, 0), "palm": (0, 0, 1)},
    }).build()
    hd = heads.human(body, look, {"smile": 0.5, "lids": 0.0 if sve else 1.0, "gaze": 0 if sve else 18, "lobes": True, "iris": "#141010"})
    s = body.s
    shri = body.T_(0, -0.13, 1.37)

    def sculpt(sc, fit):
        hair_cap(body, sc=sc, front=0.26, rise=0.012, part=False, combed=False)
        anatomy.kambu(body, sc)
        sc.bump(shri, (0.014 * s, 0.02 * s, 0.014 * s), 0.003 * s)

    def paint(pt):
        hair_cap(body, pt=pt, color="#1E1A1E", front=0.26, part=False, combed=False)
        q = pt.P - np.asarray(tuple(shri))
        lobe = 1.0 - smoothstep(0.008 * s, 0.012 * s, np.abs(q[:, 0]) + np.abs(q[:, 2]) * 0.8)
        pt.layer(lobe * (np.abs(q[:, 1]) < 0.04), mix_hex(skin_hex, "#5A3010", 0.4), 0.8)
        if sve:
            for m, c in face.tilak_mask(body, pt.P, "jina"):
                pt.layer(m, c, 1.0, metal=0.8, rough=0.3)
            cloth_skin(pt, lap_mask(body, pt.P, seat_top, 0.07), "#EFE6D2", 0.75)

    sk, eyes = anatomy.skin(body, look, skin_hex, head=hd, sculpt=0.6, extra_sculpt=sculpt, extra_paint=paint)
    fit = Fit(sk)
    objs = [sk] + eyes
    objs.append(dress.curls("curls", look.solid("curls", "#1E1A1E", rough=0.5), fit, body, curl_region, r=0.0055 * s, spacing=2.0))
    seat, front = props.lotus_seat(look, seat_top, 0.56 * s, 0.24 * s)
    objs += seat
    hc = body.frames["head"][0]
    if emblem == "snake":
        hoods = []
        for i in range(7):
            a = math.pi * (0.08 + 0.84 * i / 6)
            p = hc + Vector((math.cos(a) * 0.3 * s, 0.1 * s, math.sin(a) * 0.3 * s - 0.02))
            hoods.append(ellipsoid("hood", p, (0.075 * s, 0.025 * s, 0.1 * s), basis(Vector((math.cos(a), 0, math.sin(a))), Vector((0, -1, 0))),
                                   look.solid("hoods", "#3F6B4A", 0.4, coat=0.3), 20))
        objs.append(join(hoods, "serpent-hoods"))
    else:
        objs += props.lion(look, front + Vector((0, -0.04, 0.0)), (0, -1, 0), 1.0 * s)
    objs.append(props.chhatra(look, hc + Vector((0, 0.08, 0.3 * s)), 0.22 * s))
    objs += props.aura(look, st, "rays", hc + Vector((0, 0, 0.02)), 0.4 * s, y_back=0.22 * s)
    return finish(st, body, objs, {"id": "tirthankara", "emblem": emblem, "sect": "svetambara" if sve else "digambara", "hands": "dhyana (right over left)",
                                   "aura": "rays", "name": {"lion": "Mahavira", "snake": "Parshvanatha"}.get(emblem, emblem)})


# ---------------------------------------------------------------------- the Buddha
def buddha(look, st, o):
    """The Buddha touching the earth (bhumisparsha): golden skin (DN 30), the ushnisha and urna, snail-shell
    curls, long earlobes, lowered eyes, a faint smile; the ochre robe over the left shoulder, the right
    shoulder bare; the right hand over the right knee reaching to the earth, the left in the lap."""
    seat_top = 0.6
    body = Body("buddha", "calm", {
        "seated": "padmasana", "seat_z": seat_top, "knee_wide": 0.42,
        "arm_r": {"wrist": (-0.36, -0.36, 0.86), "torso_space": True, "pole": (-1, 0.3, -0.2), "hand": "earth", "fingers": (0.0, -0.2, -1), "palm": (1, 0, 0)},
        "arm_l": {"wrist": (0.05, -0.2, 0.97), "torso_space": True, "pole": (1, 0.1, -0.3), "hand": "dhyana", "fingers": (-1, -0.1, 0), "palm": (0, 0, 1)},
    }).build()
    hd = heads.human(body, look, {"smile": 0.6, "lids": 1.0, "gaze": 18, "lobes": True})
    skin_hex, robe = "#D9A35B", "#C26A2A"
    s = body.s
    T_ = body.T_
    a0, b0 = np.asarray(tuple(T_(0.18, 0.0, 1.52))), np.asarray(tuple(T_(-0.16, 0.0, 1.0)))
    nrm = np.array([-(b0 - a0)[2], 0.0, (b0 - a0)[0]])
    nrm = nrm / np.linalg.norm(nrm)

    def robe_mask(P):
        side = (P - a0) @ nrm
        torso = r_ell(P, T_(0, 0, 1.25), (0.3 * s, 0.24 * s, 0.36 * s), None, 0.1)
        dd, t = seg_dist(P, body.J["shoulder_l"], body.J["wrist_l"])
        left_arm = (dd < 0.085 * s) * (t < 0.92)
        return np.clip(torso * smoothstep(-0.005, 0.005, side) + left_arm + lap_mask(body, P, seat_top, 0.1), 0, 1)

    def folds(P):
        return np.sin((P[:, 0] * 0.8 + P[:, 2]) * 90) > 0.7

    def sculpt(sc, fit):
        hair_cap(body, sc=sc, front=0.26, rise=0.01, part=False, combed=False)
        anatomy.kambu(body, sc)
        m = robe_mask(sc.P)
        sc.region(m, 0.006 * s)
        sc.d -= 0.003 * s * m * folds(sc.P)

    def paint(pt):
        hair_cap(body, pt=pt, color="#1E2533", front=0.26, part=False, combed=False)
        for mm, c in face.tilak_mask(body, pt.P, "urna"):
            pt.layer(mm, c, 1.0)
        m = robe_mask(pt.P)
        cloth_skin(pt, m, robe, 0.78)
        pt.layer(m * folds(pt.P), mix_hex(robe, "#5A2A0A", 0.4), 0.5)

    sk, eyes = anatomy.skin(body, look, skin_hex, head=hd, sculpt=0.6, extra_sculpt=sculpt, extra_paint=paint)
    fit = Fit(sk)
    objs = [sk] + eyes
    objs.append(dress.curls("curls", look.solid("curls", "#1E2533", rough=0.5), fit, body, curl_region, r=0.0085 * s, spacing=2.0,
                            ushnisha=((0, 0.05, 0.46), (0.17, 0.17, 0.14))))
    seat, front = props.lotus_seat(look, seat_top, 0.56 * s, 0.24 * s)
    objs += seat
    objs += props.aura(look, st, "disc", body.frames["head"][0] + Vector((0, 0, 0.05)), 0.42 * s, y_back=0.22 * s)
    return finish(st, body, objs, {"id": "buddha", "hands": {"right": "bhumisparsha (earth-touching)", "left": "in the lap"}, "aura": "disc"})


BUILDERS = {"probe": probe, "rama": rama, "hanuman": hanuman, "shiva": shiva, "ganesha": ganesha, "athena": athena,
            "odin": odin, "tirthankara": tirthankara, "buddha": buddha}


def build(fid, look, st, options):
    return BUILDERS[fid](look, st, options)
