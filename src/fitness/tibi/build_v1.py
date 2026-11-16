import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig_v1 import *
import rig_v1 as rig

CX, FLOOR = 300, 846
LX, LY = -0.62, -0.78          # direction TOWARD the light (top-left), world space
DEFS, REG, BB, CACHE, MASKS, GRADS = [], {}, {}, {}, [], {}
_mc = [0]

# ---------------------------------------------------------------- registry ----
def reg(id_, d, pts=None):
    if id_ not in REG:
        REG[id_] = d
        DEFS.append(f'<path id="{id_}" d="{d}"/>')
        if pts:
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            BB[id_] = (min(xs), min(ys), max(xs), max(ys))
    return id_

def mk(view, key, side):
    idp = f"{view}_{key}_{side}"
    if idp in CACHE:
        return CACHE[idp]
    D = (FRONT if view == 'F' else SIDE)[key]
    px, py = D['piv']
    if side == 'R':
        tf = lambda p: (px - p[0], p[1] - py) + tuple(p[2:])
    else:
        tf = lambda p: (p[0] - px, p[1] - py) + tuple(p[2:])
    T = lambda pts: [tf(p) for p in pts]
    S = {}
    pts, skip = D['base']
    t = T(pts); sp = Sp(t)
    S['base'] = reg(idp + '_b', sp.d(), t); S['ol'] = reg(idp + '_o', sp.d_edges(skip))
    S['mus'] = []
    for i, (nm, p) in enumerate(D['mus']):
        t = T(p); S['mus'].append((nm, reg(f"{idp}_m{i}", Sp(t).d(), t)))
    S['lines'] = []
    for i, (nm, p) in enumerate(D['lines']):
        t = T(p); S['lines'].append((nm, reg(f"{idp}_l{i}", Sp(t, closed=False).d(), t)))
    S['cloth'] = []
    for i, (nm, p, sk) in enumerate(D['cloth']):
        t = T(p); sp = Sp(t)
        S['cloth'].append((nm, reg(f"{idp}_c{i}", sp.d(), t), reg(f"{idp}_co{i}", sp.d_edges(sk))))
    S['hem'] = None
    if D.get('hem'):
        t = T(D['hem']); S['hem'] = reg(idp + '_h', Sp(t, closed=False).d(), t)
    S['bones'] = []
    for i, p in enumerate(D['bones']):
        t = T(p); S['bones'].append(reg(f"{idp}_bn{i}", Sp(t).d(), t))
    S['bone_lines'] = []
    for i, p in enumerate(D['bone_lines']):
        t = T(p); S['bone_lines'].append(reg(f"{idp}_bl{i}", Sp(t, closed=False).d(), t))
    S['sh'] = []
    for i, (nm, p) in enumerate(D['sh']):
        t = T(p); S['sh'].append((nm, reg(f"{idp}_s{i}", Sp(t).d(), t)))
    CACHE[idp] = S
    return S

# ------------------------------------------------------------------ poses -----
class Seg:
    def __init__(s, view, key, side, W, th, sx=1, sy=1, far=False, name=None):
        s.view, s.key, s.side, s.W, s.th, s.sx, s.sy, s.far = view, key.split('_')[0], side, W, th, sx, sy, far
        s.skey = key; s.name = name or key

def add(a, b): return (a[0] + b[0], a[1] + b[1])

def front_pose(kind, hs=1.0, ls=1.0):
    arms = dict(relaxed=(8, 10, 9), flex=(86, 190, 192))[kind]
    tt, ts = (1.5, 0) if kind == 'relaxed' else (3.5, 0)
    segs, joints = [], []
    for side, sg in (('R', -1), ('L', 1)):
        mir = lambda v: (v[0] * sg, v[1])
        # legs
        hip = (CX + mir(SK['hip'])[0], SK['hip'][1])
        v1 = mir((SK['knee'][0] - SK['hip'][0], (SK['knee'][1] - SK['hip'][1]) * ls))
        knee = add(hip, R(tt * sg, v1))
        v2 = mir((SK['ankle'][0] - SK['knee'][0], (SK['ankle'][1] - SK['knee'][1]) * ls))
        ank = add(knee, R(ts * sg, v2))
        segs += [Seg('F', 'shin', side, knee, ts * sg, 1, ls), Seg('F', 'thigh', side, hip, tt * sg, 1, ls), Seg('F', 'foot', side, ank, 0)]
        joints += [(hip, knee), (knee, ank)]
    segs += [Seg('F', 'pelvis', 'C', (CX, 330), 0), Seg('F', 'neck', 'C', (CX, 148), 0), Seg('F', 'chest', 'C', (CX, 266), 0),
             Seg('F', 'head', 'C', (CX, 92 + (hs - 1) * 45), 0, hs, hs)]
    for side, sg in (('R', -1), ('L', 1)):
        mir = lambda v: (v[0] * sg, v[1])
        sh = (CX + mir(SK['shoulder'])[0], SK['shoulder'][1])
        el = add(sh, R(arms[0] * sg, mir((SK['elbow'][0] - SK['shoulder'][0], SK['elbow'][1] - SK['shoulder'][1]))))
        wr = add(el, R(arms[1] * sg, mir((SK['wrist'][0] - SK['elbow'][0], SK['wrist'][1] - SK['elbow'][1]))))
        ua = 'upperArm_flex' if kind == 'flex' else 'upperArm'
        hd = 'fist' if kind == 'flex' else 'hand'
        segs += [Seg('F', hd, side, wr, arms[2] * sg, 1.15, 1.15), Seg('F', 'forearm', side, el, arms[1] * sg), Seg('F', ua, side, sh, arms[0] * sg)]
        joints += [(sh, el), (el, wr)]
    return finalize(segs, joints, 'F')

def side_pose(ls=1.0, hs=1.0):
    S = SK_SIDE
    segs, joints = [], []
    def arm(far):
        a = (-14, -30, -30) if far else (-4, -18, -20)
        sh = (CX + S['shoulder'][0], S['shoulder'][1])
        el = add(sh, R(a[0], (S['elbow'][0] - S['shoulder'][0], S['elbow'][1] - S['shoulder'][1])))
        wr = add(el, R(a[1], (S['wrist'][0] - S['elbow'][0], S['wrist'][1] - S['elbow'][1])))
        joints.extend([(sh, el), (el, wr)])
        return [Seg('S', 'hand', 'C', wr, a[2], 1.15, 1.15, far=far), Seg('S', 'forearm', 'C', el, a[1], far=far), Seg('S', 'upperArm', 'C', sh, a[0], far=far)]
    def leg(far):
        tt, ts = (-8, 4) if far else (1, 0)
        hip = (CX + S['hip'][0], S['hip'][1])
        knee = add(hip, R(tt, (0, (S['knee'][1] - S['hip'][1]) * ls)))
        ank = add(knee, R(ts, (S['ankle'][0] - S['knee'][0], (S['ankle'][1] - S['knee'][1]) * ls)))
        joints.extend([(hip, knee), (knee, ank)])
        return [Seg('S', 'shin', 'C', knee, ts, 1, ls, far), Seg('S', 'thigh', 'C', hip, tt, 1, ls, far), Seg('S', 'foot', 'C', ank, 0, far=far)]
    segs += arm(True) + leg(True) + leg(False)
    segs += [Seg('S', 'pelvis', 'C', (CX, 330), 0), Seg('S', 'neck', 'C', (CX, 148), 0), Seg('S', 'chest', 'C', (CX, 266), 0),
             Seg('S', 'head', 'C', (CX, 92 + (hs - 1) * 45), 0, hs, hs)]
    segs += arm(False)
    return finalize(segs, joints, 'S')

def finalize(segs, joints, view):
    # stand on the floor: shift everything so the lowest sole sits at FLOOR
    low = max(s.W[1] + 47 for s in segs if s.key == 'foot')
    dy = FLOOR - low
    for s in segs:
        s.W = (s.W[0], s.W[1] + dy)
    joints = [((a[0], a[1] + dy), (b[0], b[1] + dy)) for a, b in joints]
    return segs, joints

# ------------------------------------------------------------- helpers --------
def fm(**kw):
    return ''.join(f' {k.replace("_", "-")}="{v}"' for k, v in kw.items())
def U(i, **kw): return f'<use href="#{i}"{fm(**kw)}/>'

def loc(P, v):
    x, y = R(-P.th, v)
    return x / P.sx, y / P.sy

def mask_id(P, shape, amt, hi=False, dil=0):
    bx0, by0, bx1, by1 = BB.get(shape, (0, 0, 40, 40))
    k = min(amt, 0.33 * min(bx1 - bx0, by1 - by0))
    sg = -1 if hi else 1
    ox, oy = loc(P, (LX * k * sg, LY * k * sg))
    _mc[0] += 1; mid = f"k{_mc[0]}"
    st = f' stroke="#fff" stroke-width="{n(dil * 2)}"' if dil else ''
    st2 = f' stroke="#000" stroke-width="{n(dil * 2)}"' if dil else ''
    MASKS.append(f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="-420" y="-480" width="900" height="1000">'
                 f'<use href="#{shape}" fill="#fff"{st}/><use href="#{shape}" fill="#000"{st2} transform="translate({n(ox)},{n(oy)})"/></mask>')
    return mid

def cres(P, shape, color, amt=4.5, hi=False, **kw):
    return U(shape, fill=color, mask=f"url(#{mask_id(P, shape, amt, hi)})", **kw)

def lingrad(P, stops, tag):
    dx, dy = loc(P, (-LX, -LY))
    m = max(abs(dx), abs(dy)) or 1; dx, dy = dx / m, dy / m
    key = (tag, round(dx, 2), round(dy, 2))
    if key not in GRADS:
        gid = f"g{len(GRADS)}"
        st = ''.join(f'<stop offset="{o}" stop-color="{c}"{"" if a is None else f" stop-opacity={chr(34)}{a}{chr(34)}"}/>' for o, c, a in stops)
        GRADS[key] = (gid, f'<linearGradient id="{gid}" x1="{n(.5 - .5 * dx)}" y1="{n(.5 - .5 * dy)}" x2="{n(.5 + .5 * dx)}" y2="{n(.5 + .5 * dy)}">{st}</linearGradient>')
    return GRADS[key][0]

def wgrad(P, stops, tag):
    """light gradient defined in WORLD space (one continuous sweep across all segments)"""
    c, s_ = math.cos(math.radians(P.th)), math.sin(math.radians(P.th))
    a, cc, bb, d = c / P.sx, s_ / P.sx, -s_ / P.sy, c / P.sy
    e = -(a * P.W[0] + cc * P.W[1]); f = -(bb * P.W[0] + d * P.W[1])
    gid = f"w{len(GRADS)}"
    st = ''.join(f'<stop offset="{o}" stop-color="{col}"/>' for o, col in stops)
    GRADS[(tag, len(GRADS), 'w')] = (gid, f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{CX - 240}" y1="120" x2="{CX + 240}" y2="640" '
                                f'gradientTransform="matrix({round(a,4)} {round(bb,4)} {round(cc,4)} {round(d,4)} {n(e)} {n(f)})">{st}</linearGradient>')
    return gid

def center(i):
    b = BB[i]; return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)

NAVY, COBALT, MARIGOLD, CORAL, BONE, CHAR = '#18286F', '#2F56E0', '#FFB224', '#F2553D', '#F4EAD5', '#22243A'

# --------------------------------------------------------------- faces --------
def face_svg(expr, view, w=1.0):
    nv = f'stroke="{NAVY}" stroke-linecap="round" stroke-linejoin="round" fill="none"'
    o = []
    if view == 'S':
        o.append(f'<ellipse cx="24" cy="59" rx="4.4" ry="6" fill="{NAVY}"/><circle cx="22.8" cy="56.6" r="1.5" fill="#fff"/>')
        o.append(f'<path d="M16,48 Q24,43 32,47" {nv} stroke-width="{n(3.2 * w)}"/>')
        if expr == 'effort':
            o.append(f'<path d="M24,80 L35,80" {nv} stroke-width="{n(3.2 * w)}"/>')
        else:
            o.append(f'<path d="M27,79 Q32,85 36,79" {nv} stroke-width="{n(3 * w)}"/>')
        return f'<g transform="translate(0,-92)">{"".join(o)}</g>'
    eye = lambda x, ry=6.6, dy=0: (f'<ellipse cx="{x}" cy="{59 + dy}" rx="5" ry="{ry}" fill="{NAVY}"/>'
                                    f'<circle cx="{x - 1.7 if x < 0 else x - 1.7}" cy="{56.8 + dy}" r="1.7" fill="#fff"/>')
    if expr == 'happy':
        o += [eye(-13), eye(13)]
        o.append(f'<path d="M-21,47 Q-14,42 -6,46" {nv} stroke-width="{n(3.2 * w)}"/><path d="M21,47 Q14,42 6,46" {nv} stroke-width="{n(3.2 * w)}"/>')
        o.append(f'<path d="M-9,77 Q0,89 9,77" {nv} stroke-width="{n(3 * w)}"/>')
    elif expr == 'effort':
        o += [eye(-13, 4.2, 1), eye(13, 4.2, 1)]
        o.append(f'<path d="M-22,43 L-6,51" {nv} stroke-width="{n(4 * w)}"/><path d="M22,43 L6,51" {nv} stroke-width="{n(4 * w)}"/>')
        o.append(f'<rect x="-11" y="75" width="22" height="11" rx="4" fill="#fff" stroke="{NAVY}" stroke-width="{n(2.6 * w)}"/>'
                 f'<path d="M-11,80.5 H11 M0,75 V86" {nv} stroke-width="{n(2 * w)}"/>')
    elif expr == 'thinking':
        o += [eye(-12, 6.2, -1), eye(14, 6.2, -1)]
        o.append(f'<path d="M-22,45 Q-14,37 -6,42" {nv} stroke-width="{n(3.2 * w)}"/><path d="M6,48 L22,46" {nv} stroke-width="{n(3.2 * w)}"/>')
        o.append(f'<path d="M-6,82 Q3,79 10,83" {nv} stroke-width="{n(3 * w)}"/>')
    else:  # tired
        for x in (-13, 13):
            o.append(f'<path d="M{x - 5.5},60 A5.5,5.2 0 0 0 {x + 5.5},60 Z" fill="{NAVY}"/><path d="M{x - 7},59.5 H{x + 7}" {nv} stroke-width="{n(2.6 * w)}"/>')
        o.append(f'<path d="M-21,49 L-7,44" {nv} stroke-width="{n(3.2 * w)}"/><path d="M21,49 L7,44" {nv} stroke-width="{n(3.2 * w)}"/>')
        o.append(f'<path d="M-7,85 Q0,79 7,85" {nv} stroke-width="{n(3 * w)}"/>')
        o.append(f'<path d="M25,36 C29,43 31,46 25,49 C19,46 21,43 25,36Z" fill="#8FB0FF" stroke="{NAVY}" stroke-width="{n(1.6 * w)}"/>')
    return f'<g transform="translate(0,-92)">{"".join(o)}</g>'

def spark(style, hs=1.0):
    ol = ''
    if style in ('ink', 'hero'):
        ol = f' stroke="{NAVY}" stroke-width="{n((2.6 if style == "ink" else 3.2) / hs)}" stroke-linejoin="round"'
    return (f'<g class="spark" transform="translate(0,-92) translate(0,6) scale(1.4) translate(0,-6)"><path d="{FLAME_OUT}" fill="{MARIGOLD}"{ol}/>'
            f'<path d="{FLAME_IN}" fill="#FFE08A"/></g>')

# --------------------------------------------------------------- styles -------
def poly_lines(S, P, color, w, op=1, names=None, skip=()):
    o = []
    for nm, i in S['lines']:
        if nm in skip or nm == 'vein': continue
        o.append(U(i, fill='none', stroke=color, stroke_width=w, stroke_opacity=op, stroke_linecap='round', stroke_linejoin='round'))
    return o

def far_overlay(P, S, color, op):
    if not P.far: return []
    o = [U(S['base'], fill=color, fill_opacity=op)]
    for nm, i, ol in S['cloth']:
        if nm in ('shortsleg', 'shorts', 'sole', 'thumb'):
            o.append(U(i, fill=color, fill_opacity=op))
    return o

# ---- 1. Cobalt Sculpt ----
def p_sculpt(P, S, pose, opts):
    B, LT, DK = COBALT, '#4F75EC', '#2244B8'
    o = []
    if P.key == 'foot':
        o.append(U(S['base'], fill='#FBFBFA'))
        o.append(cres(P, S['base'], '#CFD4E6', 5))
        for nm, i, ol in S['cloth']: o.append(U(i, fill='#B9C2DE'))
        o += poly_lines(S, P, '#B9C2DE', 1.8)
        return o + far_overlay(P, S, NAVY, .25)
    o.append(U(S['base'], fill=B))
    for nm, i in S['sh']: o.append(U(i, fill=DK))
    for nm, i in S['mus']:
        if nm == 'face':
            o.append(U(i, fill='#3F66E8')); o.append(cres(P, i, DK, 5, opacity=.55)); continue
        if nm == 'navel':
            o.append(U(i, fill=DK)); continue
        o.append(U(i, fill=LT)); o.append(cres(P, i, DK, 5.5))
    o += poly_lines(S, P, DK, 1.8, .75, skip=('clav', 'notch', 'lace', 'toecap'))
    for nm, i, ol in S['cloth']:
        o.append(U(i, fill={'band': MARIGOLD, 'thumb': B}.get(nm, CHAR)))
    if S['hem']: o.append(U(S['hem'], fill='none', stroke=MARIGOLD, stroke_width=3.2, stroke_linecap='round'))
    return o + far_overlay(P, S, NAVY, .22)

# ---- 2. Glass Anatomy ----
def p_glass(P, S, pose, opts):
    o = [U(S['base'], fill='#D3E2FF')]
    for b in S['bones']: o.append(U(b, fill=BONE, stroke='#D9C9A0', stroke_width=1.2))
    for b in S['bone_lines']: o.append(U(b, fill='none', stroke='#EADBB8', stroke_width=4.2, stroke_linecap='round'))
    for nm, i in S['mus']:
        if nm == 'face':
            o.append(U(i, fill='#fff', fill_opacity=.55)); continue
        if nm == 'navel': o.append(U(i, fill='#B8301F', fill_opacity=.7)); continue
        o.append(U(i, fill=CORAL, fill_opacity=.84)); o.append(cres(P, i, '#B8301F', 5, opacity=.8)); o.append(cres(P, i, '#FF9A86', 3.2, hi=True, opacity=.85))
    for nm, i in S['sh']: o.append(U(i, fill='#9FBAF7', fill_opacity=.5))
    o += poly_lines(S, P, '#B8301F', 1.4, .5, skip=('clav', 'notch', 'lace', 'toecap'))
    if P.key == 'foot':
        o = [U(S['base'], fill='#EAF1FF', fill_opacity=.95)] + [U(i, fill='#9FBAF7') for nm, i, ol in S['cloth']]
        o += poly_lines(S, P, '#7E9CE6', 1.6)
    for nm, i, ol in S['cloth']:
        if P.key == 'foot': continue
        o.append(U(i, fill={'band': MARIGOLD, 'thumb': '#D3E2FF'}.get(nm, CHAR), fill_opacity=.92 if nm != 'thumb' else 1))
    if S['hem']: o.append(U(S['hem'], fill='none', stroke=MARIGOLD, stroke_width=3.2, stroke_linecap='round'))
    gid = lingrad(P, [(0, '#fff', .75), (.55, '#fff', .12), (1, '#7E9CE6', .28)], 'glass')
    o.append(U(S['base'], fill=f'url(#{gid})'))
    o.append(U(S['ol'], fill='none', stroke=COBALT, stroke_width=2.6 / ((P.sx + P.sy) / 2), stroke_opacity=.85, stroke_linecap='round', stroke_linejoin='round'))
    return o + far_overlay(P, S, '#7E9CE6', .28)

# ---- 3. Ink Line ----
def p_ink(P, S, pose, opts):
    sw = 3.4 / ((P.sx + P.sy) / 2)
    o = [U(S['base'], fill='#FBFBFA')]
    for nm, i in S['mus']:
        if nm == 'face':
            o.append(cres(P, i, NAVY, 5, opacity=.07))
            m = mask_id(P, i, 5, dil=1.4)
            o.append(f'<g mask="url(#{m})">{U(i, fill="none", stroke=NAVY, stroke_width=1.8, stroke_linecap="round")}</g>'); continue
        if nm == 'navel':
            o.append(U(i, fill=NAVY)); continue
        o.append(cres(P, i, NAVY, 6, opacity=.075))
        m = mask_id(P, i, 6, dil=1.4)
        o.append(f'<g mask="url(#{m})">{U(i, fill="none", stroke=NAVY, stroke_width=2.1, stroke_linecap="round", stroke_linejoin="round")}</g>')
    o += poly_lines(S, P, NAVY, 1.9, 1, skip=('notch', 'lace') if P.key != 'foot' else ())
    for nm, i, ol in S['cloth']:
        if nm == 'band':
            o.append(U(i, fill=MARIGOLD, stroke=NAVY, stroke_width=2.6, stroke_linejoin='round'))
        elif nm == 'sole':
            o.append(U(i, fill=NAVY, stroke=NAVY, stroke_width=2, stroke_linejoin='round'))
        elif nm == 'thumb':
            o.append(U(i, fill='#FBFBFA', stroke=NAVY, stroke_width=2.4, stroke_linejoin='round'))
        else:
            o.append(U(i, fill=CHAR)); o.append(U(ol, fill='none', stroke=NAVY, stroke_width=sw, stroke_linecap='round', stroke_linejoin='round'))
    if S['hem']: o.append(U(S['hem'], fill='none', stroke=MARIGOLD, stroke_width=3, stroke_linecap='round'))
    o.append(U(S['ol'], fill='none', stroke=NAVY, stroke_width=sw * (1 if P.key != 'foot' else .9), stroke_linecap='round', stroke_linejoin='round'))
    return o + far_overlay(P, S, NAVY, .1)

# ---- 4. Hero Cel ----
def p_hero(P, S, pose, opts):
    hs = P.sx
    sw = 4.7 / ((P.sx + P.sy) / 2)
    B, HI, SH = COBALT, '#6B8CF6', '#2142B0'
    o = []
    if P.key == 'foot':
        o.append(U(S['base'], fill='#FBFBFA'))
        o.append(cres(P, S['base'], '#DCD7CA', 6))
        for nm, i, ol in S['cloth']: o.append(U(i, fill='#E3DCCB', stroke=NAVY, stroke_width=sw * .7, stroke_linejoin='round'))
        o += poly_lines(S, P, NAVY, 2, .8)
        o.append(U(S['ol'], fill='none', stroke=NAVY, stroke_width=sw * .9, stroke_linejoin='round', stroke_linecap='round'))
        return o + far_overlay(P, S, NAVY, .22)
    o.append(U(S['base'], fill=B))
    for nm, i in S['sh']: o.append(U(i, fill=SH))
    for nm, i in S['mus']:
        if nm == 'face':
            o.append(U(i, fill='#FFF8EC', stroke=NAVY, stroke_width=3.2 / hs, stroke_linejoin='round'))
            o.append(cres(P, i, '#EADFC9', 5)); continue
        if nm == 'navel': o.append(U(i, fill=SH)); continue
        o.append(cres(P, i, HI, 3.6, hi=True)); o.append(cres(P, i, SH, 5.2))
    o += poly_lines(S, P, NAVY, 2, .8, skip=('clav', 'notch', 'lace', 'toecap'))
    # rim light (warm spark bounce) along the shadow-side silhouette
    mid = mask_id(P, S['base'], 9)
    ox, oy = loc(P, (LX * 3.4, LY * 3.4))
    o.append(f'<g mask="url(#{mid})"><use href="#{S["ol"]}" transform="translate({n(ox)},{n(oy)})" fill="none" stroke="#FFC857" stroke-width="{n(2.8 / ((P.sx + P.sy) / 2))}" stroke-linecap="round"/></g>')
    for nm, i, ol in S['cloth']:
        if nm == 'band':
            o.append(U(i, fill=MARIGOLD, stroke=NAVY, stroke_width=3, stroke_linejoin='round'))
        elif nm == 'thumb':
            o.append(U(i, fill=B, stroke=NAVY, stroke_width=3, stroke_linejoin='round'))
        else:
            o.append(U(i, fill=CHAR)); o.append(U(ol, fill='none', stroke=NAVY, stroke_width=sw * .85, stroke_linecap='round', stroke_linejoin='round'))
    if S['hem']: o.append(U(S['hem'], fill='none', stroke=MARIGOLD, stroke_width=3.4, stroke_linecap='round'))
    o.append(U(S['ol'], fill='none', stroke=NAVY, stroke_width=sw, stroke_linecap='round', stroke_linejoin='round'))
    if P.key == 'head':
        o.append(face_svg(opts['expr'], 'S' if P.view == 'S' else 'F', 1 / hs))
    return o + far_overlay(P, S, NAVY, .25)

# ---- 5. Marble ----
def p_marble(P, S, pose, opts):
    o = []
    gb = lingrad(P, [(0, '#FFFBF1', None), (.55, '#F1E7D0', None), (1, '#CDBE9C', None)], 'mb')
    gm = lingrad(P, [(0, '#FFFDF6', None), (.6, '#EFE4CB', None), (1, '#CFC09E', None)], 'mm')
    if P.key == 'foot':
        o.append(U(S['base'], fill=f'url(#{gm})'))
        for nm, i, ol in S['cloth']: o.append(U(i, fill='#CDBE9C'))
        o += poly_lines(S, P, '#B7A885', 1.5, .8)
        return o + far_overlay(P, S, '#6B5D45', .25)
    o.append(U(S['base'], fill=f'url(#{gb})'))
    for nm, i in S['sh']: o.append(U(i, fill='#B9A985', fill_opacity=.45))
    for nm, i in S['mus']:
        if nm == 'face':
            o.append(U(i, fill='#FFFDF6', fill_opacity=.35)); continue
        if nm == 'navel': o.append(U(i, fill='#B9A985', fill_opacity=.8)); continue
        o.append(U(i, fill=f'url(#{gm})')); o.append(cres(P, i, '#8F7E5C', 5, opacity=.3)); o.append(cres(P, i, '#fff', 3, hi=True, opacity=.8))
    o += poly_lines(S, P, '#A8987A', 1.4, .55, skip=('notch', 'lace', 'toecap'))
    for nm, i, ol in S['cloth']:
        o.append(U(i, fill={'band': MARIGOLD, 'thumb': f'url(#{gm})'}.get(nm, CHAR)))
    if S['hem']: o.append(U(S['hem'], fill='none', stroke=MARIGOLD, stroke_width=3, stroke_linecap='round'))
    return o + far_overlay(P, S, '#6B5D45', .25)

# ---- 6. Activation Map ----
ACT = {'relaxed': {'abs': 1, 'quad': 1, 'trap': 1, 'gastro': 1, 'soleus': 1},
       'flex': {'biceps': 2, 'brach': 2, 'delt': 2, 'pec': 1, 'trap': 1, 'triceps': 1, 'flexor': 1, 'abs': 1},
       'side': {'hams': 2, 'vastus': 1, 'quad': 1, 'abs': 1, 'gastro': 2, 'trap': 1, 'oblique': 1, 'lat': 1}}
def p_act(P, S, pose, opts):
    BASE, TILE = '#EEF3FE', '#C2D2F7'
    o = []
    if P.key == 'foot':
        o.append(U(S['base'], fill='#FBFBFA'))
        for nm, i, ol in S['cloth']: o.append(U(i, fill='#C9D5F6'))
        o += poly_lines(S, P, '#9FB4EE', 1.6)
        o.append(U(S['ol'], fill='none', stroke=COBALT, stroke_width=2, stroke_linecap='round', stroke_linejoin='round'))
        return o + far_overlay(P, S, NAVY, .18)
    o.append(U(S['base'], fill=BASE))
    for nm, i in S['sh']: o.append(U(i, fill='#D5E0FA'))
    for nm, i in S['mus']:
        lvl = ACT[pose].get(nm, 0)
        if nm == 'face': o.append(U(i, fill='#F7F9FF', stroke=BASE, stroke_width=2)); continue
        if nm == 'navel': o.append(U(i, fill='#9FB4EE')); continue
        fill = {0: TILE, 1: '#5C7FEA', 2: CORAL}[lvl]
        o.append(U(i, fill=fill, stroke=BASE, stroke_width=2.6, stroke_linejoin='round'))
        if lvl == 2:
            cx, cy = center(i)
            o.append(U(i, fill=MARIGOLD, transform=f'translate({n(cx)},{n(cy)}) scale(.46) translate({n(-cx)},{n(-cy)})'))
        elif lvl == 1:
            cx, cy = center(i)
            o.append(U(i, fill='#9DB4F5', transform=f'translate({n(cx)},{n(cy)}) scale(.5) translate({n(-cx)},{n(-cy)})'))
    o += poly_lines(S, P, '#9FB4EE', 1.5, 1, skip=('clav', 'notch', 'lace', 'toecap'))
    for nm, i, ol in S['cloth']:
        o.append(U(i, fill={'band': MARIGOLD, 'thumb': BASE}.get(nm, CHAR)))
    if S['hem']: o.append(U(S['hem'], fill='none', stroke=MARIGOLD, stroke_width=3, stroke_linecap='round'))
    o.append(U(S['ol'], fill='none', stroke=COBALT, stroke_width=2.2, stroke_linecap='round', stroke_linejoin='round'))
    return o + far_overlay(P, S, NAVY, .14)


# ---- 2b. Glass Anatomy (v2) ----
def p_glass2(P, S, pose, opts):
    sw = 2.5 / ((P.sx + P.sy) / 2)
    gb = lingrad(P, [(0, '#F1F6FF', None), (.55, '#CFDFFF', None), (1, '#9DB8F5', None)], 'gb')
    if P.key == 'foot':
        o = [U(S['base'], fill=f'url(#{gb})')] + [U(i, fill='#9DB8F5') for nm, i, ol in S['cloth']]
        o += poly_lines(S, P, '#6F8FE0', 1.6)
        o.append(cres(P, S['base'], '#fff', 4.5, hi=True, opacity=.8))
        o.append(U(S['ol'], fill='none', stroke=COBALT, stroke_width=sw, stroke_linejoin='round', stroke_linecap='round'))
        return o + far_overlay(P, S, '#6F8FE0', .25)
    o = [U(S['base'], fill=f'url(#{gb})')]
    for b in S['bones']: o.append(U(b, fill='#F9F1DD', stroke='#C9B484', stroke_width=1.8))
    for b in S['bone_lines']:
        o.append(U(b, fill='none', stroke='#C9B484', stroke_width=6.4, stroke_linecap='round'))
        o.append(U(b, fill='none', stroke='#F9F1DD', stroke_width=3.8, stroke_linecap='round'))
    for nm, i in S['sh']: o.append(U(i, fill='#8FAEF2', fill_opacity=.55))
    for nm, i in S['mus']:
        if nm == 'face':
            o.append(U(i, fill='#fff', fill_opacity=.5)); continue
        if nm == 'navel': o.append(U(i, fill='#B8301F', fill_opacity=.75)); continue
        o.append(U(i, fill=CORAL, fill_opacity=.66, stroke='#D63F2A', stroke_width=1.1, stroke_opacity=.7, stroke_linejoin='round'))
        o.append(cres(P, i, '#B8301F', 5.5, opacity=.55)); o.append(cres(P, i, '#FFB8A8', 3.4, hi=True, opacity=.75))
    o += poly_lines(S, P, '#B8301F', 1.4, .5, skip=('clav', 'notch', 'lace', 'toecap'))
    # the glass skin: cobalt-tinted depth + specular crescent on the lit edge + rim
    gt = lingrad(P, [(0, '#2F56E0', .0), (1, '#2F56E0', .3)], 'gt')
    o.append(U(S['base'], fill=f'url(#{gt})'))
    o.append(cres(P, S['base'], '#fff', 6, hi=True, opacity=.8))
    for nm, i, ol in S['cloth']:
        o.append(U(i, fill={'band': MARIGOLD, 'thumb': '#CFDFFF'}.get(nm, CHAR), fill_opacity=1 if nm != 'thumb' else .6))
    if S['hem']: o.append(U(S['hem'], fill='none', stroke=MARIGOLD, stroke_width=3.2, stroke_linecap='round'))
    o.append(U(S['ol'], fill='none', stroke='#fff', stroke_width=sw * 2.2, stroke_opacity=.5, stroke_linecap='round', stroke_linejoin='round'))
    o.append(U(S['ol'], fill='none', stroke=COBALT, stroke_width=sw, stroke_linecap='round', stroke_linejoin='round'))
    return o + far_overlay(P, S, '#6F8FE0', .3)

# ---- 5b. Marble (v2) ----
def p_marble2(P, S, pose, opts):
    gb = wgrad(P, [(0, '#F3EBD8'), (.45, '#E3D8BF'), (.8, '#C4BCAA'), (1, '#9FA0AC')], 'mb')
    gm = wgrad(P, [(0, '#FFFEF8'), (.45, '#F7F0DF'), (.8, '#DCD3BF'), (1, '#B3B3BD')], 'mm')
    VEIN = '#7F8CB0'
    if P.key == 'foot':
        o = [U(S['base'], fill=f'url(#{gm})')]
        for nm, i, ol in S['cloth']: o.append(U(i, fill='#B9B7B8'))
        o += poly_lines(S, P, '#A39A86', 1.5, .8)
        o.append(cres(P, S['base'], '#8D8FA0', 6, opacity=.35))
        return o + far_overlay(P, S, '#5E5A66', .28)
    o = [U(S['base'], fill=f'url(#{gb})')]
    for nm, i in S['sh']: o.append(U(i, fill='#8D8FA0', fill_opacity=.4))
    for nm, i in S['mus']:
        if nm == 'face':
            o.append(U(i, fill='#FFFFFC', fill_opacity=.3)); continue
        if nm == 'navel': o.append(U(i, fill='#8D8FA0', fill_opacity=.7)); continue
        o.append(U(i, fill=f'url(#{gm})'))
        o.append(cres(P, i, '#5E607C', 6.5, opacity=.55))       # cool core shadow
        o.append(cres(P, i, '#FBF6E8', 2.2, opacity=.7))        # reflected light at the edge
        o.append(cres(P, i, '#fff', 3.2, hi=True, opacity=.95)) # warm key light
    o += poly_lines(S, P, '#8F8776', 1.5, .55, skip=('notch', 'lace', 'toecap'))
    for nm, i in S['lines']:
        if nm == 'vein':
            o.append(U(i, fill='none', stroke=VEIN, stroke_width=3.2, stroke_opacity=.22, stroke_linecap='round'))
            o.append(U(i, fill='none', stroke=VEIN, stroke_width=1.2, stroke_opacity=.6, stroke_linecap='round', transform='translate(1.5,1)'))
    for nm, i, ol in S['cloth']:
        o.append(U(i, fill={'band': MARIGOLD, 'thumb': f'url(#{gm})'}.get(nm, CHAR)))
    if S['hem']: o.append(U(S['hem'], fill='none', stroke=MARIGOLD, stroke_width=3, stroke_linecap='round'))
    return o + far_overlay(P, S, '#5E5A66', .28)

STYLES = dict(sculpt=p_sculpt, glass=p_glass2, ink=p_ink, hero=p_hero, marble=p_marble2, act=p_act, glass1=p_glass, marble1=p_marble)

# --------------------------------------------------------------- figures ------
VAR = dict(  # per-variant proportion knobs
    sculpt=dict(hs=1.0, ls=1.0), glass=dict(hs=1.0, ls=1.0), ink=dict(hs=.97, ls=1.01),
    hero=dict(hs=1.2, ls=1.0), marble=dict(hs=.96, ls=1.0), act=dict(hs=1.0, ls=1.0), glass1=dict(hs=1.0, ls=1.0), marble1=dict(hs=.96, ls=1.0))

def figure(style, pose, expr=None):
    v = VAR[style]
    segs, joints = (side_pose(v['ls'], v['hs']) if pose == 'side' else front_pose(pose, v['hs'], v['ls']))
    fn = STYLES[style]
    opts = dict(expr=expr or ('effort' if pose == 'flex' else 'happy'))
    o = []
    rx = {'relaxed': 118, 'flex': 132, 'side': 96}[pose]
    if style == 'marble':
        pw = {'relaxed': 150, 'flex': 150, 'side': 120}[pose]
        o.append(f'<path d="M{CX - pw},{FLOOR} h{pw * 2} v24 h-{pw * 2} Z" fill="#D5CDB8"/><path d="M{CX - pw},{FLOOR} h{pw * 2} v7 h-{pw * 2} Z" fill="#F6F0E0"/>'
                 f'<path d="M{CX - pw},{FLOOR + 24} h{pw * 2}" stroke="#B8B0A0" stroke-width="2"/>')
        o.append(f'<ellipse cx="{CX}" cy="{FLOOR + 2}" rx="{rx * .8}" ry="5" fill="#6F6A7A" opacity=".22"/>')
    else:
        o.append(f'<ellipse cx="{CX}" cy="{FLOOR + 3}" rx="{rx}" ry="11" fill="{NAVY}" opacity=".09"/>')
    for P in segs:
        S = mk(P.view, P.skey, P.side)
        inner = fn(P, S, pose, opts)
        if P.key == 'head':
            inner = [spark(style, P.sx)] + inner
        tf = f'translate({n(P.W[0])},{n(P.W[1])})' + (f' rotate({n(P.th)})' if abs(P.th) > 1e-6 else '') + \
             (f' scale({n(P.sx)},{n(P.sy)})' if (P.sx != 1 or P.sy != 1) else '')
        gid = f"{style}-{pose}-{P.key}{P.side if P.side != 'C' else ''}"
        o.append(f'<g id="{gid}" transform="{tf}">' + ''.join(inner) + '</g>')
    rig_ = []
    seen = set()
    for a, b in joints:
        rig_.append(f'<line x1="{n(a[0])}" y1="{n(a[1])}" x2="{n(b[0])}" y2="{n(b[1])}" stroke="{NAVY}" stroke-width="1.6" stroke-dasharray="4 3" opacity=".7"/>')
    for a, b in joints:
        for p in (a, b):
            k = (round(p[0]), round(p[1]))
            if k in seen: continue
            seen.add(k)
            rig_.append(f'<circle cx="{n(p[0])}" cy="{n(p[1])}" r="5.5" fill="{MARIGOLD}" stroke="{NAVY}" stroke-width="1.8"/>')
    for P in segs:
        if P.key in ('neck', 'chest', 'pelvis', 'head') and not P.far:
            rig_.append(f'<circle cx="{n(P.W[0])}" cy="{n(P.W[1])}" r="4.5" fill="#fff" stroke="{NAVY}" stroke-width="1.8"/>')
    o.append('<g class="rig">' + ''.join(rig_) + '</g>')
    return f'<g id="fig-{style}-{pose}">' + ''.join(o) + '</g>'

def head_only(style, expr):
    """small standalone head for the expression strip"""
    v = VAR[style]
    P = Seg('F', 'head', 'C', (0, 0), 0, v['hs'], v['hs'])
    S = mk('F', 'head', 'C')
    inner = [spark(style, P.sx)] + STYLES[style](P, S, 'relaxed', dict(expr=expr))
    return f'<g transform="scale({n(P.sx)})">' + ''.join(inner) + '</g>'
