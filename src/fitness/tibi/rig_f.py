"""Female Tibi: same segment set / pivots / joint topology as the male rig, different volumes.
Most segments are morphs of the male data (x-scaling about the limb axis, smaller muscle planes);
chest, pelvis, bra, ponytail are authored by hand."""
import math
from rig import *
import rig as M

def xfp(pts, f):
    return [(*f(p[0], p[1]), *p[2:]) for p in pts]

def shrink(pts, k):
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
    return [(cx + (p[0] - cx) * k, cy + (p[1] - cy) * k, *p[2:]) for p in pts]

NOSHRINK = ('face', 'navel', 'patella', 'scm')

def morph(D, f, k=0.9):
    E = dict(D)
    E['piv'] = f(*D['piv'])
    pts, sk = D['base']
    E['base'] = (xfp(pts, f), sk)
    E['mus'] = [(nm, xfp(p, f) if nm in NOSHRINK else shrink(xfp(p, f), k)) for nm, p in D['mus']]
    E['lines'] = [(nm, xfp(p, f)) for nm, p in D['lines']]
    E['cloth'] = [(nm, xfp(p, f), sk_) for nm, p, sk_ in D['cloth']]
    if D.get('hem'): E['hem'] = xfp(D['hem'], f)
    E['bones'] = [xfp(p, f) for p in D['bones']]
    E['bone_lines'] = [xfp(p, f) for p in D['bone_lines']]
    E['sh'] = [(nm, xfp(p, f)) for nm, p in D['sh']]
    if D.get('blobs'):
        sc = f(1, 0)[0] - f(0, 0)[0]
        E['blobs'] = [(*f(b[0], b[1]), b[2] * sc) for b in D['blobs']]
    return E

def ax(a, k, d=0):
    return lambda x, y: (a + (x - a) * k + d, y)

FRONT_F, SIDE_F = {}, {}

# ------------------------------------------------------------------ FRONT ------------------------------------------------
for key, f in dict(head=ax(0, .94), neck=ax(0, .86),
                   thigh=ax(-43, .92, 1.5), shin=ax(-43, .86, 1), foot=ax(-46, .9, 1),
                   upperArm=ax(-100, .84, 14), upperArm_flex=ax(-100, .84, 14), upperArm_nd=ax(-100, .84, 14),
                   forearm=ax(-101, .84, 14), hand=ax(-101, .85, 14), fist=ax(-101, .85, 14),
                   cap=ax(-100, .88, 14)).items():
    FRONT_F[key] = morph(M.FRONT[key], f)

# --- lat wing (hand-authored: she has a narrower waist so the V is gentler)
FRONT_F['flare'] = dict(piv=(-86, 162), limb=True,
    base=([(-119, 192), (-106, 206), (-92, 226), (-80, 250), (-68, 274), (-55, 298), (-48, 300), (-52, 262), (-66, 224), (-80, 198), (-100, 183)], set()),
    mus=[('lat', [(-110, 200), (-97, 218), (-86, 240), (-74, 264), (-63, 288), (-62, 262), (-73, 236), (-87, 212), (-102, 198)])])

# --- chest (hand-authored): narrower shoulders, waist, sports top
clf = [(0, 162), (-10, 158), (-20.5, 130, 'c'), (-35, 137), (-53, 146), (-70, 154), (-81, 163), (-84, 172), (-83, 190), (-79, 206), (-72, 224),
       (-64, 242), (-56, 256), (-51, 266), (-49, 272), (0, 273)]
pec0 = M.FRONT['chest']['mus'][0][1]
pecf = shrink([(p[0] * .82, p[1]) for p in pec0], .92)
latf = [(-76, 202), (-72, 224), (-63, 246), (-54, 262), (-50, 250), (-56, 230), (-64, 208)]
trapf = [(-21, 133), (-35, 140), (-53, 148), (-72, 157), (-77, 162), (-58, 166), (-42, 159), (-28, 150), (-21, 142)]
serf = [blob(-55, 238, 8, 3.9, 30, 2.8), blob(-51, 250, 8, 3.9, 30, 2.8), blob(-47, 261, 7.5, 3.7, 30, 2.8)]
r1f = blob(-13, 239, 10, 8.6, 0, 3.4); r2f = blob(-12.5, 260, 9.6, 8.6, 0, 3.4)
oblcf = [(-26, 247), (-38, 247), (-49, 254), (-52, 266), (-41, 270), (-28, 268)]
bra_l = [(0, 196, 'c'), (-81.5, 196, 'c'), (-75, 216), (-66.5, 236, 'c'), (0, 236, 'c')]      # straight top edge and straight bottom edge
strap_l = [(-45, 198, 'c'), (-45, 143, 'c'), (-59, 147.5, 'c'), (-59, 198, 'c')]      # two straight, parallel straps
bust_l = blob(-23, 218, 17, 13, 0, 2.8)
bra_hem = [(-66.5, 236), (-33, 236), (0, 236), (33, 236), (66.5, 236)]
FRONT_F['chest'] = dict(piv=(0, 266), sym=True, base=sym(clf, 2, 1),
    mus=[('pec', pecf), ('pec', mx(pecf)), ('lat', latf), ('lat', mx(latf)), ('trap', trapf), ('trap', mx(trapf))]
        + [('serratus', s_) for s_ in serf] + [('serratus', mx(s_)) for s_ in serf]
        + [('oblique', oblcf), ('oblique', mx(oblcf)), ('abs', r1f), ('abs', mx(r1f)), ('abs', r2f), ('abs', mx(r2f))],
    lines=[('clav', [(-4, 160), (-24, 156), (-46, 158), (-70, 165)]), ('clav', mx([(-4, 160), (-24, 156), (-46, 158), (-70, 165)])),
           ('notch', [(-8, 156), (0, 160), (8, 156)])],
    cloth=[('bra', sym(bra_l, 0, 0)[0], set()), ('bust', bust_l, set()), ('bust', mx(bust_l), set()),
           ('strap', strap_l, set()), ('strap', mx(strap_l), set())],
    hem=bra_hem, bones=[], bone_lines=[])

# --- pelvis (hand-authored): narrow waist, hips, slim waistband
pbf = [(0, 262), (-28, 262), (-50, 262), (-48, 280), (-47, 296), (-54, 312), (-65, 327), (-66, 337), (-64, 344), (0, 346)]
sh_pf = [(0, 327), (-32, 327), (-66, 327), (-71, 341), (-74.5, 359), (-75.5, 374), (-74, 387), (-62, 397), (-31, 402), (0, 404)]
band_f = [(0, 329), (-33, 326.5), (-67, 325.5), (-69, 335), (-33, 336.5), (0, 338)]
oblf = [(-24, 262), (-38, 262), (-47, 268), (-49, 283), (-48, 297), (-44, 305), (-38, 313), (-32, 321), (-30, 300), (-28, 280)]
r3f = blob(-12.5, 282, 9.6, 8.6, 0, 3.4)
lowf = [(-3, 303), (-13, 301), (-22, 305), (-25, 316), (-21, 325), (-12, 329), (-3, 329)]
vlinef = [(-49, 302), (-42, 312), (-34, 321), (-27, 328)]
FRONT_F['pelvis'] = dict(piv=(0, 330), sym=True, base=sym(pbf, 2, 1),
    mus=[('oblique', oblf), ('oblique', mx(oblf)), ('abs', r3f), ('abs', mx(r3f)), ('abs', lowf), ('abs', mx(lowf)),
         ('navel', blob(0, 298, 3, 4, 0, 2.2))],
    lines=[('vline', vlinef), ('vline', mx(vlinef))],
    cloth=[('shorts', *sym(sh_pf, 2, 2)), ('band', sym(band_f, 0, 0)[0], set())], bones=[], bone_lines=[])

# --- ponytail (drawn between chest and head; swings out to the viewer's right in front view)
pony_f = [(22, 14), (44, 8), (62, 26), (72, 58), (73, 98), (67, 138), (60, 172, 'c'), (53, 142), (50, 106), (46, 72), (36, 46), (22, 32)]
FRONT_F['pony'] = dict(piv=(30, 22), base=(pony_f, set()),
    mus=[('hairplane', [(40, 22), (56, 34), (64, 62), (65, 100), (61, 132), (57, 106), (55, 72), (48, 46)])],
    lines=[], cloth=[('tie', blob(31, 22, 6, 6.6, 0, 2.2), set())])

# ------------------------------------------------------------------ SIDE --------------------------------------------------
for key, f in dict(head=ax(-3, .95), neck=ax(0, .88), thigh=ax(0, .92), shin=ax(0, .88), foot=ax(-2, .92),
                   upperArm=ax(0, .84), forearm=ax(0, .84), hand=ax(0, .85)).items():
    SIDE_F[key] = morph(M.SIDE[key], f)

sc_base = [(12, 152), (28, 160), (44, 173), (54, 192), (66, 207), (63, 226), (52, 238), (45, 254), (40, 264), (37, 271),
           (-34, 271), (-38, 254), (-44, 230), (-49, 206), (-50, 182), (-44, 162), (-32, 148), (-16, 143)]
SIDE_F['chest'] = dict(piv=(0, 266), base=(sc_base, {9, 17}),
    mus=[('trap', [(-14, 145), (-30, 149), (-44, 165), (-46, 188), (-34, 194), (-24, 170)]),
         ('lat', [(-48, 208), (-40, 238), (-36, 264), (-22, 264), (-20, 236), (-30, 208)]),
         ('pec', [(24, 168), (40, 174), (50, 186), (46, 193), (30, 190), (20, 182)])]
        + [('serratus', blob(14 - 2 * i, 241 + 12.5 * i, 8, 3.8, -28, 2.8)) for i in range(3)],
    lines=[],
    cloth=[('bra', [(-47, 196, 'c'), (44, 196, 'c'), (56, 201), (64, 213), (63, 224), (59, 233, 'c'), (-45, 233, 'c')], set()),
           ('bust', blob(39, 215, 15, 12.5, 0, 2.8), set()),
           ('strap', [(-13, 146, 'c'), (2, 150, 'c'), (2, 197, 'c'), (-13, 197, 'c')], set())],
    hem=[(-45, 233), (-20, 233), (10, 233), (35, 233), (59, 233)], bones=[], bone_lines=[])
SIDE_F['pelvis'] = dict(piv=(0, 330), base=([(-34, 262), (-36, 290), (-46, 318), (-55, 338), (-5, 346), (44, 338), (42, 318), (40, 296), (38, 272)], {3, 4, 8}),
    mus=[('oblique', [(-22, 262), (-6, 262), (22, 264), (34, 280), (36, 304), (26, 318), (6, 322), (-14, 316), (-26, 296), (-26, 276)]),
         ('abs', [(19, 276), (36, 280), (38, 300), (36, 318), (23, 322), (13, 300)]),
         ('navel', blob(36, 298, 2.4, 3.3, 0, 2.2)),
         ('glute', [(-63, 345), (-45, 331), (-23, 337), (-8, 358), (-6, 380), (-19, 394), (-39, 400), (-57, 392), (-68, 370)]),
         ('hipflex', [(12, 332), (31, 338), (45, 354), (45, 374), (35, 386), (19, 381), (10, 360)])],
    lines=[('rim', [(-57, 346), (-63, 357), (-67.5, 369), (-66.5, 380)])],
    cloth=[('shorts', [(-52, 328), (-60, 342), (-67, 356), (-71.5, 370), (-70.5, 380), (-66, 389), (-58, 396), (-50, 401), (-44.5, 405, 'c'), (-20, 406), (8, 405), (28, 401), (41, 390), (46, 368), (45, 346), (44, 326), (0, 327)], {0, 16}),
           ('band', [(-53, 326), (0, 328.5), (46, 326), (47, 335.5), (0, 338), (-57, 337)], set())],
    bones=[], bone_lines=[])
spony = [(-26, 16), (-50, 8), (-72, 22), (-84, 52), (-80, 92), (-68, 128), (-58, 158, 'c'), (-57, 124), (-59, 90), (-55, 58), (-42, 40), (-28, 32)]
SIDE_F['pony'] = dict(piv=(-30, 24), base=(spony, set()),
    mus=[('hairplane', [(-46, 20), (-66, 30), (-74, 56), (-72, 92), (-64, 120), (-63, 90), (-62, 58), (-52, 36)])],
    lines=[], cloth=[('tie', blob(-31, 24, 5.5, 6, 0, 2.2), set())])

# ------------------------------------------------------------------ SHORT CURLY HAIR (separate variant; replaces the ponytail) --
def lobed(poly, L, h):
    """cloud-like scalloped edge along an open polyline: a corner at every junction, one rounded bump (pushed out by h) per piece.
    The path must be traversed counter-clockwise (screen), so the outward normal is (-dy, dx)."""
    seg = [(poly[i], poly[i + 1], math.hypot(poly[i + 1][0] - poly[i][0], poly[i + 1][1] - poly[i][1])) for i in range(len(poly) - 1)]
    total = sum(s[2] for s in seg); n = max(1, round(total / L)); step = total / n
    def at(s_):
        acc = 0
        for a, b, l in seg:
            if s_ <= acc + l + 1e-9:
                t = (s_ - acc) / l if l else 0
                return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            acc += l
        return seg[-1][1]
    out = []
    for i in range(n):
        a, b = at(i * step), at((i + 1) * step)
        dx, dy = b[0] - a[0], b[1] - a[1]; d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d
        out.append((a[0], a[1], 'c'))
        out.append(((a[0] + b[0]) / 2 + nx * h, (a[1] + b[1]) / 2 + ny * h))
    out.append((at(total)[0], at(total)[1], 'c'))
    return out

def spiral(cx, cy, r, turns=1.2, start=0, n=10, flip=1):
    pts = []
    for i in range(n):
        t = i / (n - 1); a = start + flip * turns * 2 * math.pi * t; rr = r * (1 - .72 * t)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts

def circles_along(poly, spacing, r):
    seg = [(poly[i], poly[i + 1], math.hypot(poly[i + 1][0] - poly[i][0], poly[i + 1][1] - poly[i][1])) for i in range(len(poly) - 1)]
    total = sum(s[2] for s in seg); n = max(1, round(total / spacing)); step = total / n
    out = []
    for k in range(n + 1):
        s_ = k * step; acc = 0
        for a_, b_, l in seg:
            if s_ <= acc + l + 1e-9:
                t = (s_ - acc) / l if l else 0
                out.append((a_[0] + (b_[0] - a_[0]) * t, a_[1] + (b_[1] - a_[1]) * t, r)); break
            acc += l
    return out

# ---- round 3: longer, puffy, open curls. A solid crown plus separate hanging ringlets (corkscrew chains of circles) with gaps between them.
def lock(x, y0, y1, r0, r1, amp=2.8, sp=8.6, ph=0.0):
    """one hanging ringlet: a chain of circles going down, wobbling side to side, tapering"""
    k = max(2, round((y1 - y0) / sp)); out = []
    for i in range(k + 1):
        t = i / k
        out.append((x + amp * math.sin(ph + i * 1.9), y0 + (y1 - y0) * t, r0 + (r1 - r0) * t))
    return out

# front, viewer-left half: crown + side volume, then ringlets hanging beside the face and neck
_o = [(0, -17), (-18, -14), (-36, -3), (-50, 14), (-58, 33), (-61, 50)]
_i = [(-40, 54), (-35, 44), (-31, 37), (-23, 31), (-11, 27.5), (0, 26.5)]
core_l = [(0, -9), (-24, -6), (-42, 6), (-53, 26), (-55, 46), (-46, 56)] + _i[1:]
c_l = circles_along(_o, 14, 11) + circles_along(_i, 11.5, 5.6)
tuft_l = [(-63, 58, 12.5), (-54, 73, 10.5), (-67, 75, 9.5),                       # side puff
          (-55, 98, 11), (-65, 108, 9), (-47, 115, 9.5), (-58, 123, 7.5)]          # lower puff, ends at the shoulders
tuft_r = [(-62, 58, 12.5), (-53, 74, 10.5), (-66, 72, 9.5),
          (-56, 92, 11), (-66, 103, 9), (-50, 106, 9), (-60, 114, 7.5)]
c_all = c_l + tuft_l + [(-60, 86, 8.6)] + [(-x, y, r) for x, y, r in c_l] + [(-x, y, r) for x, y, r in tuft_r] + [(60, 83, 8.6)]
def _sw(cx, cy, r, fl=1): return spiral(cx, cy, r, 1.3, 3.4, 11, fl)
_swp = ((-22, -4, 8), (-6, -9, 7), (-40, 8, 8.5), (-53, 28, 8.5))
_swl = tuple((x, y, r * .6) for x, y, r in (tuft_l[0], tuft_l[3], tuft_l[5], tuft_l[1]))
_swr = tuple((x, y, r * .6) for x, y, r in (tuft_r[0], tuft_r[3], tuft_r[5], tuft_r[2]))
FRONT_F['curls'] = dict(piv=(0, 92), base=(sym(core_l, 0, 0)[0], set()),
    blobs=c_all,
    mus=[], lines=[('swirl', _sw(*p_)) for p_ in _swp + _swl] + [('swirl', mx(_sw(*p_, fl=-1))) for p_ in _swp + _swr],
    cloth=[])

# side (facing right): puffy back volume, ringlets hanging behind the neck
_so = [(30, 4), (28, -9), (12, -15), (-8, -15), (-28, -6), (-45, 12), (-55, 33), (-57, 50)]
_si = [(-46, 60), (-34, 58), (-22, 52), (-13, 46), (-4, 41), (8, 37), (20, 33), (28, 29), (32, 24)]
_sf = [(32, 26), (30, 4)]
core_s = [(30, 4), (27, -6), (11, -10), (-9, -9), (-27, -1), (-42, 14), (-49, 33), (-50, 50), (-40, 58)] + _si[1:]
c_s = circles_along(_so, 14, 11) + circles_along(_si, 11.5, 5.8) + circles_along(_sf, 10, 5.2)
tuft_s = [(-60, 56, 12.5), (-51, 72, 10.5), (-65, 74, 9.5), (-54, 97, 11), (-64, 107, 9), (-46, 115, 9.5), (-58, 123, 7.5)]
SIDE_F['curls'] = dict(piv=(0, 92), base=(core_s, set()), blobs=c_s + tuft_s + [(-58, 86, 8.6)],
    mus=[], lines=[('swirl', _sw(*p_)) for p_ in ((-8, -6, 8), (14, -7, 7), (-30, 2, 8), (-46, 20, 8.5), (-55, 40, 7)) + tuple((x, y, r * .6) for x, y, r in (tuft_s[0], tuft_s[3], tuft_s[5], tuft_s[1]))],
    cloth=[])

# ---- round 3: bra variants (chest segment variants; 'sport' = the round 2 top, kept for comparison)
# sports top, round 4: slimmer straps and a shallower body (top edge lowered 6 units), still flat top edge and flat hem
_braS = [(0, 197, 'c'), (-81, 197, 'c'), (-75, 216), (-66.5, 236, 'c'), (0, 236, 'c')]
_strS = [(-47, 199, 'c'), (-47, 143.5, 'c'), (-53.5, 145.5, 'c'), (-53.5, 199, 'c')]
_bustS = blob(-23, 218, 15, 12.5, 0, 2.8)
FRONT_F['chest_sport'] = dict(FRONT_F['chest'], hem=[(-66.5, 236), (-33, 236), (0, 236), (33, 236), (66.5, 236)],
    cloth=[('bra', sym(_braS, 0, 0)[0], set()), ('bust', _bustS, set()), ('bust', mx(_bustS), set()), ('strap', _strS, set()), ('strap', mx(_strS), set())])
SIDE_F['chest_sport'] = dict(SIDE_F['chest'],
    cloth=[('bra', [(-47, 197, 'c'), (44, 197, 'c'), (55, 202), (63, 213), (63, 225), (59, 233, 'c'), (-45, 233, 'c')], set()),
           ('bust', blob(39, 215, 14, 12, 0, 2.8), set()),
           ('strap', [(-7, 147, 'c'), (-1, 150, 'c'), (-1, 198, 'c'), (-7, 198, 'c')], set())])
_hemF = [(-66.5, 236), (-33, 236), (0, 236), (33, 236), (66.5, 236)]
_hemS = [(-44, 236), (-20, 236), (10, 236), (34, 236), (54, 236)]

# bralette: two soft triangle cups, thin straps, slim band
_cupB = [(-40, 186, 'c'), (-27, 200), (-16, 214), (-8, 229, 'c'), (-66, 229, 'c'), (-59.5, 214), (-49, 198.5)]
_bandB = [(0, 229, 'c'), (-69, 229, 'c'), (-66.5, 236, 'c'), (0, 236, 'c')]
_strB = [(-40.5, 190, 'c'), (-40.5, 143.5, 'c'), (-45.5, 145.1, 'c'), (-45.5, 190, 'c')]
FRONT_F['chest_bralette'] = dict(FRONT_F['chest'], hem=_hemF,
    cloth=[('bra', _cupB, set()), ('bra', mx(_cupB), set()), ('bust', blob(-36, 214, 8.5, 10.5, 0, 2.8), set()), ('bust', blob(36, 214, 8.5, 10.5, 0, 2.8), set()),
           ('bra', sym(_bandB, 0, 0)[0], set()), ('strap', _strB, set()), ('strap', mx(_strB), set())])
SIDE_F['chest_bralette'] = dict(SIDE_F['chest'], hem=_hemS,
    cloth=[('bra', [(30, 199), (44, 201), (56, 208), (63, 218), (62, 229, 'c'), (26, 229, 'c'), (24, 212)], set()),
           ('bust', blob(43, 215, 9, 10, 0, 2.8), set()),
           ('bra', [(-46, 229, 'c'), (59, 229, 'c'), (54, 236, 'c'), (-44, 236, 'c')], set()),
           ('strap', [(-8, 145, 'c'), (-3, 146.5, 'c'), (38, 198, 'c'), (31, 201, 'c')], set())])

# padded push-up: moulded balconette cups with a plunge, wider straps, deeper band, bigger padding plane
_cupP = [(-5, 204, 'c'), (-16, 195), (-30, 189.5), (-46, 190), (-58, 196.5), (-66, 208), (-68, 221), (-68.5, 230, 'c'), (-10, 230, 'c')]
_bandP = [(0, 229, 'c'), (-69, 229, 'c'), (-66.5, 236, 'c'), (0, 236, 'c')]
_strP = [(-48, 191, 'c'), (-48, 145.5, 'c'), (-54.5, 147.5, 'c'), (-54.5, 193, 'c')]
FRONT_F['chest_push'] = dict(FRONT_F['chest'], hem=_hemF,
    cloth=[('bra', _cupP, set()), ('bra', mx(_cupP), set()), ('bust', blob(-35, 210, 15.5, 11.5, -8, 2.8), set()), ('bust', blob(35, 210, 15.5, 11.5, 8, 2.8), set()),
           ('bra', sym(_bandP, 0, 0)[0], set()), ('strap', _strP, set()), ('strap', mx(_strP), set())])
SIDE_F['chest_push'] = dict(SIDE_F['chest'], hem=_hemS,
    cloth=[('bra', [(26, 192), (42, 191), (56, 199), (66, 212), (67, 224), (60, 231, 'c'), (24, 231, 'c'), (22, 208)], set()),
           ('bust', blob(44, 208, 14, 12, 0, 2.8), set()),
           ('bra', [(-46, 229, 'c'), (60, 229, 'c'), (54, 236, 'c'), (-44, 236, 'c')], set()),
           ('strap', [(-8, 146, 'c'), (-2, 148, 'c'), (38, 192, 'c'), (31, 196, 'c')], set())])

for D in (FRONT_F, SIDE_F):
    for k, v in D.items():
        v.setdefault('mus', []); v.setdefault('lines', []); v.setdefault('cloth', [])
        v.setdefault('bones', []); v.setdefault('bone_lines', []); v.setdefault('sh', [])

SK_F = dict(shoulder=(-86, 162), elbow=(-87, 298), wrist=(-87, 406), hip=(-36, 388), knee=(-42, 566), ankle=(-45, 732))
SK_SIDE_F = dict(SK_SIDE)
