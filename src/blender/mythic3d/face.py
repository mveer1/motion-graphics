"""
Faces in head space: every skin vertex is mapped to head-relative coordinates (x across, y back, z up;
units of H, origin at the head centre), so features are exact analytic regions on the front of the face
that follow the head's pose. The base head is smooth masses (heads.py); here the features are sculpted
(displacement along the normal) and painted (vertex colour), like a sculptor adding and carving clay
and a painter finishing it (figure-design.md section 3.2: lotus-petal eyes, bow brows rising to the outer
third, a line-and-shadow nose, a full lower lip, the corners lifted slightly; lowered lids when meditative).
"""

import numpy as np

from .core import mix_hex, smoothstep


def head_q(body, P):
    c, R = body.frames["head"]
    return ((P - np.asarray(tuple(c))) @ np.array(R)) / body.H


def g2(qx, qz, cx, cz, sx, sz):
    return np.exp(-(((qx - cx) / sx) ** 2) - (((qz - cz) / sz) ** 2))


def front(q, at=-0.2, full=-0.3):
    return smoothstep(at, full, q[:, 1])


def almond(qx, qz, cx, cz, hx, hz, lift=0.012, edge=0.004):
    """Lotus-petal eye opening: an arched upper lid, a flatter lower lid, pointed corners, the outer corner
    lifted. Returns (mask, upper edge z, u)."""
    side = np.sign(cx) if cx != 0 else 1.0
    u = (qx - cx) / hx
    o = u * side                                        # +1 at the outer corner for both eyes
    zc = cz + lift * np.clip(o, 0, 1) ** 1.4 - 0.004 * np.clip(-o, 0, 1)
    shape = np.clip(1 - u * u, 0, 1) ** 0.75
    top = zc + hz * 1.2 * shape * (1 - 0.18 * np.clip(-o, 0, 1))
    bot = zc - hz * 0.75 * shape
    inside = np.minimum(top - qz, qz - bot)
    m = smoothstep(-edge, edge, inside) * (np.abs(u) < 1.05)
    return m, top, bot, u


EYE_X, EYE_Z = 0.112, -0.026


def sculpt_human(body, sc, o):
    H = body.H
    q = head_q(body, sc.P)
    qx, qz = q[:, 0], q[:, 2]
    F = front(q)
    fem = 0.8 if o.get("female") else 1.0
    nose = o.get("nose", 1.0)
    sm = o.get("smile", 0.4)
    drop = o.get("lids", 0.0)
    d = np.zeros(len(qx))
    ax = np.abs(qx)
    # Brow: a soft ridge, stronger over the outer third; the glabella between.
    zb = 0.05 + 0.012 * np.clip(1 - ((ax - 0.12) / 0.1) ** 2, 0, 1)
    d += 0.016 * fem * np.exp(-((qz - zb) / 0.04) ** 2) * np.clip(1 - (ax / 0.24) ** 4, 0, 1)
    d -= 0.006 * g2(qx, qz, 0, 0.02, 0.03, 0.03)
    # Orbits: a shallow bowl round each eye, the cheekbones below and out.
    for sx in (-1, 1):
        d -= 0.014 * g2(qx, qz, sx * EYE_X, EYE_Z, 0.085, 0.06)
        d += 0.022 * g2(qx, qz, sx * 0.185, -0.085, 0.07, 0.05)
    # Nose: bridge to tip, wider and higher towards the tip; the wings; the nostrils; the philtrum.
    zt = np.clip((0.01 - qz) / 0.165, 0, 1)                      # 0 at the bridge, 1 at the tip
    wn = (0.026 + 0.02 * zt) * nose
    hn = (0.014 + 0.07 * zt ** 1.5) * nose * fem
    d += hn * np.exp(-(qx / wn) ** 2) * smoothstep(0.03, 0.0, qz) * smoothstep(-0.215, -0.17, qz)
    d += 0.02 * nose * fem * g2(qx, qz, 0, -0.16, 0.042, 0.034)
    for sx in (-1, 1):
        d += 0.034 * nose * g2(qx, qz, sx * 0.042, -0.176, 0.028, 0.022)
        d -= 0.016 * g2(qx, qz, sx * 0.03, -0.194, 0.011, 0.008)
        d -= 0.005 * np.exp(-(((qx - sx * (0.05 + 0.4 * (-0.17 - qz))) / 0.012) ** 2)) * smoothstep(-0.16, -0.18, qz) * smoothstep(-0.29, -0.26, qz)
    d -= 0.004 * g2(qx, qz, 0, -0.228, 0.011, 0.02)
    # Lips: the upper lip with a cupid's bow, a fuller lower lip, the line between, the corners.
    d += 0.036 * fem * g2(qx, qz, 0, -0.262, 0.086, 0.02) + 0.008 * (g2(qx, qz, -0.024, -0.252, 0.018, 0.012) + g2(qx, qz, 0.024, -0.252, 0.018, 0.012))
    d += 0.045 * fem * g2(qx, qz, 0, -0.303, 0.078, 0.022)
    zl = -0.283 + 0.012 * sm * (ax / 0.08) ** 2
    d -= 0.014 * np.exp(-((qz - zl) / 0.0055) ** 2) * np.clip(1 - (ax / 0.082) ** 6, 0, 1)
    for sx in (-1, 1):
        d -= 0.008 * g2(qx, qz, sx * 0.083, -0.284 + 0.01 * sm, 0.012, 0.012)
    d -= 0.006 * g2(qx, qz, 0, -0.345, 0.06, 0.012)
    d += 0.016 * g2(qx, qz, 0, -0.41, 0.07, 0.05)
    # Eyes: the almond opening cut back behind the eyeball, the upper lid's fold above it, the lower lid.
    for sx in (-1, 1):
        hz = 0.019 * (1 - 0.6 * drop)
        m, top, bot, u = almond(qx, qz, sx * EYE_X, EYE_Z - 0.014 * drop, 0.073, hz)
        ok = np.clip(1 - u * u, 0, 1)
        if o.get("closed_eye") == ("r" if sx < 0 else "l"):
            # The eye given at Mimir's well: the lids closed over an empty socket, a scar across.
            d -= 0.012 * m
            d -= 0.008 * np.exp(-((qz - EYE_Z) / 0.006) ** 2) * ok
            d -= 0.007 * np.exp(-(((qx - sx * (EYE_X + 0.25 * (qz - EYE_Z))) / 0.007) ** 2)) * smoothstep(0.1, 0.06, qz) * smoothstep(-0.16, -0.1, qz)
            continue
        d -= 0.062 * m
        d += 0.013 * np.exp(-((qz - top - 0.007) / 0.011) ** 2) * ok
        if not o.get("no_crease"):
            d -= 0.005 * np.exp(-((qz - top - 0.03 + 0.012 * drop) / 0.007) ** 2) * ok ** 2
        d += 0.006 * np.exp(-((qz - bot + 0.006) / 0.008) ** 2) * ok
    sc.d += d * H * F


def paint_human(body, pt, skin, o):
    q = head_q(body, pt.P)
    qx, qz = q[:, 0], q[:, 2]
    F = front(q, -0.22, -0.3)
    ax = np.abs(qx)
    lip = o.get("lip") or mix_hex(skin, "#8A3A3A", 0.42)
    brow = o.get("brow", "#1C1412")
    drop = o.get("lids", 0.0)
    lips = np.clip(g2(qx, qz, 0, -0.264, 0.076, 0.016) * 1.6 + g2(qx, qz, 0, -0.302, 0.07, 0.019) * 1.6, 0, 1)
    pt.layer(smoothstep(0.5, 0.8, lips) * F, lip, 0.75, rough=0.36)
    for sx in (-1, 1):
        pt.layer(g2(qx, qz, sx * 0.17, -0.15, 0.06, 0.05) * F, mix_hex(skin, "#C0504A", 0.3), 0.12)
    # Bow brows rising to the outer third, tapering out.
    u = (ax - 0.04) / 0.17
    zb = 0.066 + 0.026 * np.sin(np.clip(u, 0, 1) * np.pi * 0.85) + 0.012 * o.get("brow_lift", 0.0) * u
    th = 0.017 * (1 - 0.55 * np.clip(u, 0, 1))
    pt.layer(smoothstep(0.008, -0.004, np.abs(qz - zb) - th) * (u > 0) * (u < 1) * F, brow, 0.95, rough=0.7)
    if o.get("closed_eye"):
        sx = -1 if o["closed_eye"] == "r" else 1
        scar = np.exp(-(((qx - sx * (EYE_X + 0.25 * (qz - EYE_Z))) / 0.008) ** 2)) * smoothstep(0.1, 0.06, qz) * smoothstep(-0.16, -0.1, qz)
        pt.layer(scar * F, mix_hex(skin, "#7A2A22", 0.5), 0.8)
    if o.get("kohl", True):
        for sx in (-1, 1):
            if o.get("closed_eye") == ("r" if sx < 0 else "l"):
                continue
            hz = 0.019 * (1 - 0.6 * drop)
            m, top, bot, uu = almond(qx, qz, sx * EYE_X, EYE_Z - 0.014 * drop, 0.073, hz)
            band = smoothstep(-0.006, 0.0, qz - top) * smoothstep(0.02, 0.012, qz - top) * (np.abs(uu) < 1.22) * ((uu * sx) > -0.95)
            pt.layer(band * F, "#141010", 0.9, rough=0.4)


def sculpt_vanara(body, sc, o):
    H = body.H
    q = head_q(body, sc.P)
    qx, qz = q[:, 0], q[:, 2]
    F = front(q, -0.15, -0.28)
    d = np.zeros(len(qx))
    ax = np.abs(qx)
    # Heavy brow ridge, fierce: lower over the inner corners.
    zb = 0.06 - 0.02 * np.clip(1 - ax / 0.1, 0, 1) * o.get("fierce", 1.0)
    d += 0.05 * np.exp(-((qz - zb) / 0.035) ** 2) * np.clip(1 - (ax / 0.26) ** 4, 0, 1)
    for sx in (-1, 1):
        d -= 0.01 * g2(qx, qz, sx * EYE_X, -0.015, 0.08, 0.05)
        m, top, bot, u = almond(qx, qz, sx * EYE_X, -0.012, 0.068, 0.03, lift=0.004)
        d -= 0.07 * m
        d += 0.012 * np.exp(-((qz - top - 0.006) / 0.01) ** 2) * np.clip(1 - u * u, 0, 1)
        d -= 0.018 * g2(qx, qz, sx * 0.028, -0.135, 0.016, 0.012)
        d += 0.02 * g2(qx, qz, sx * 0.16, -0.2, 0.07, 0.06)
    # Broad flat nose, the long full upper lip of the muzzle, the mouth line, the strong chin.
    d += 0.03 * g2(qx, qz, 0, -0.1, 0.06, 0.06)
    d += 0.04 * g2(qx, qz, 0, -0.235, 0.12, 0.05)
    d -= 0.016 * np.exp(-((qz - (-0.29 + 0.01 * (ax / 0.12) ** 2)) / 0.007) ** 2) * np.clip(1 - (ax / 0.13) ** 4, 0, 1)
    d += 0.02 * g2(qx, qz, 0, -0.33, 0.1, 0.03)
    sc.d += d * H * F


def paint_vanara(body, pt, skin, o):
    """The bare face mask (warm red-pink) inside the golden fur; dark lids; the lips darker."""
    q = head_q(body, pt.P)
    qx, qz = q[:, 0], q[:, 2]
    F = front(q, -0.14, -0.26)
    face = o.get("face", "#D7765A")
    mask = np.clip(g2(qx, qz, 0, -0.16, 0.25, 0.27) * 1.7, 0, 1) * F
    pt.layer(smoothstep(0.45, 0.75, mask), face, 1.0, rough=0.55, name="face")
    pt.layer(smoothstep(0.45, 0.75, mask) * g2(qx, qz, 0, -0.2, 0.08, 0.05), mix_hex(face, "#F0A080", 0.4), 0.5)
    for sx in (-1, 1):
        m, top, bot, u = almond(qx, qz, sx * EYE_X, -0.012, 0.068, 0.03, lift=0.004)
        band = smoothstep(0.01, 0.004, np.abs(qz - top)) * (np.abs(u) < 1.15)
        pt.layer(band * F, "#2A140C", 0.9)
    lips = np.exp(-((qz - (-0.29)) / 0.012) ** 2) * np.clip(1 - (np.abs(qx) / 0.12) ** 4, 0, 1)
    pt.layer(lips * F, "#7E3A24", 0.8)
    pt.layer(g2(qx, qz, 0, -0.12, 0.05, 0.035) * F, mix_hex(face, "#5A2A1C", 0.3), 0.5)


def sculpt_elephant(body, sc, o):
    """Brow over small kind eyes; transverse rings on the trunk are added by the figure."""
    H = body.H
    q = head_q(body, sc.P)
    qx, qz = q[:, 0], q[:, 2]
    F = front(q, -0.1, -0.22)
    d = np.zeros(len(qx))
    for sx in (-1, 1):
        m, top, bot, u = almond(qx, qz, sx * 0.2, 0.0, 0.04, 0.018, lift=0.006)
        d -= 0.04 * m
        d += 0.01 * np.exp(-((qz - top - 0.006) / 0.01) ** 2) * np.clip(1 - u * u, 0, 1)
        d += 0.012 * g2(qx, qz, sx * 0.2, 0.06, 0.07, 0.03)
    sc.d += d * H * F


def paint_elephant(body, pt, skin, o):
    q = head_q(body, pt.P)
    qx, qz = q[:, 0], q[:, 2]
    F = front(q, -0.1, -0.22)
    for sx in (-1, 1):
        m, top, bot, u = almond(qx, qz, sx * 0.2, 0.0, 0.04, 0.018, lift=0.006)
        pt.layer(smoothstep(0.008, 0.003, np.abs(qz - top)) * (np.abs(u) < 1.2) * F, "#1E1410", 0.85)


SCULPT = {"human": sculpt_human, "vanara": sculpt_vanara, "elephant": sculpt_elephant}
PAINT = {"human": paint_human, "vanara": paint_vanara, "elephant": paint_elephant}


def tilak_mask(body, P, kind):
    """Forehead marks in head space: 'vaishnava' (U with a red centre line), 'tripundra' (three ash lines
    with a red dot), 'jina' (an applied gold mark), 'urna' (the Buddha's dot). Returns [(mask, colour)]."""
    q = head_q(body, P)
    qx, qz = q[:, 0], q[:, 2]
    F = front(q, -0.2, -0.3)
    out = []
    if kind == "vaishnava":
        u = smoothstep(0.016, 0.01, np.abs(np.abs(qx) - 0.022)) * smoothstep(0.1, 0.11, qz + 0.0) * (qz < 0.26)
        bottom = smoothstep(0.016, 0.01, np.hypot(qx, (qz - 0.11) * 1.6) - 0.022) * (qz < 0.11)
        out.append((np.clip(u + bottom, 0, 1) * F, "#F4EEE2"))
        out.append((smoothstep(0.009, 0.005, np.abs(qx)) * smoothstep(0.1, 0.12, qz) * (qz < 0.24) * F, "#C2302A"))
    elif kind == "tripundra":
        lines, edge = 0, 0
        for z in (0.115, 0.165, 0.215):
            span = np.clip(1 - (np.abs(qx) / 0.22) ** 6, 0, 1)
            lines = lines + smoothstep(0.016, 0.01, np.abs(qz - z)) * span
            edge = edge + smoothstep(0.022, 0.016, np.abs(qz - z)) * np.clip(1 - (np.abs(qx) / 0.235) ** 6, 0, 1)
        # Ash lines on ash-pale skin: a soft grey edge first, as painted images draw them.
        out.append((np.clip(edge, 0, 1) * F, "#7E8C9A"))
        out.append((np.clip(lines, 0, 1) * F, "#FBF8F2"))
        out.append((smoothstep(0.02, 0.014, np.hypot(qx, qz - 0.165)) * F, "#C2302A"))
    elif kind == "jina":
        out.append((smoothstep(0.016, 0.011, np.abs(qx) + np.abs(qz - 0.12) * 0.6) * F, "#D7A443"))
    elif kind == "urna":
        out.append((smoothstep(0.012, 0.008, np.hypot(qx, qz - 0.075)) * F, "#F4EEE2"))
    return out
