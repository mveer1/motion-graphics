"""Tibi BACK views: same silhouettes / pivots as the front rig, new interior anatomy (posterior muscles, back of the shorts, heel of the shoe).
Everything is authored for the viewer-left half (x<0) and mirrored with mx() exactly like the front data."""
import math
from rig import *
import rig as M
import rig_f as F

def bk(D, **over):
    """back variant of a front segment: same piv/base/limb/blobs, interior cleared, then overridden"""
    E = {k: D[k] for k in ('piv', 'base') if k in D}
    for k in ('limb', 'blobs', 'sym', 'shoe'):
        if k in D: E[k] = D[k]
    E.update(mus=[], lines=[], cloth=[], sh=[], bones=[], bone_lines=[])
    E.update(over)
    return E

BACK = {}
FR = M.FRONT

# ---------------- HEAD / NECK (nape) ----------------
nape = [(-31, 73), (-21, 80), (0, 83.5), (21, 80), (31, 73), (22, 87), (0, 91), (-22, 87)]
BACK['head'] = bk(FR['head'], sh=[('nape', nape)], lines=[('vein', [(-31, 22), (-26, 52)])],
                  mus=[('hairplane', [(-18, 20), (-6, 14), (6, 14), (18, 20), (10, 36), (-10, 36)])])
BACK['neck'] = bk(FR['neck'],
    mus=[('trap', [(-7, 96), (-15, 102), (-22, 118), (-27, 135), (-26, 150), (-12, 152), (-7, 140)]),
         ('trap', mx([(-7, 96), (-15, 102), (-22, 118), (-27, 135), (-26, 150), (-12, 152), (-7, 140)]))],
    lines=[('spine', [(0, 92), (0, 118), (0, 150)])])

# ---------------- CHEST = UPPER / MID BACK ----------------
_trap_b = [(-3, 138), (-21, 130), (-37, 137), (-57, 146), (-80, 156), (-87, 162), (-73, 168), (-57, 171), (-43, 177), (-32, 191), (-24, 210), (-13, 230), (-3, 248)]
_lat_b = [(-89, 209), (-78, 212), (-62, 216), (-44, 222), (-28, 232), (-15, 246), (-5, 262), (-5, 273), (-48, 273), (-64, 269), (-74, 253), (-83, 233)]
_infra = blob(-63, 190, 19, 12, 16, 2.8)
_teres = blob(-79, 207, 12, 5.6, -12, 2.8)
_rhomb = [(-5, 170), (-18, 171), (-33, 183), (-40, 199), (-31, 208), (-17, 201), (-5, 192)]
_erec_c = [(-4, 232), (-12, 233), (-19, 246), (-21, 262), (-19, 273), (-4, 273)]
_scap = [(-26, 168), (-48, 172), (-70, 170), (-84, 166)]
_med = [(-32, 178), (-38, 192), (-36, 206)]
_spine = [(0, 132), (0, 170), (0, 215), (0, 273)]

def back_chest_mus(M_):
    return [('lat', M_['lat']), ('lat', mx(M_['lat'])), ('erector', M_['erec']), ('erector', mx(M_['erec'])),
            ('infra', M_['infra']), ('infra', mx(M_['infra'])), ('infra', M_['teres']), ('infra', mx(M_['teres'])),
            ('trap', M_['trap']), ('trap', mx(M_['trap']))]

_Mm = dict(lat=_lat_b, erec=_erec_c, infra=_infra, teres=_teres, rhomb=_rhomb, trap=_trap_b)
BACK['chest'] = bk(FR['chest'], mus=back_chest_mus(_Mm),
    lines=[('spine', _spine), ('scap', _scap), ('scap', mx(_scap)), ('scap_med', _med), ('scap_med', mx(_med))])

# ---------------- PELVIS (back of the shorts) ----------------
_mound = [(-3, 340), (-20, 335), (-42, 338), (-60, 348), (-68, 366), (-65, 385), (-52, 397), (-31, 402), (-11, 401), (-3, 390)]
_erec_p = [(-4, 262), (-12, 262), (-19, 274), (-21, 292), (-17, 312), (-9, 325), (-4, 328)]
_flank = [(-62, 270), (-64, 286), (-62, 300), (-54, 309), (-47, 297), (-47, 281), (-51, 270)]
_glute_g = [(-4, 336), (-24, 330), (-48, 336), (-65, 352), (-72, 374), (-66, 394), (-46, 406), (-24, 408), (-6, 402)]
BACK['pelvis'] = bk(FR['pelvis'],
    mus=[('oblique', _flank), ('oblique', mx(_flank)), ('erector', _erec_p), ('erector', mx(_erec_p)), ('glute', _glute_g), ('glute', mx(_glute_g))],
    lines=[('spine', [(0, 262), (0, 300), (0, 328)]), ('dimple', [(-14, 316), (-10, 320)]), ('dimple', [(14, 316), (10, 320)])],
    cloth=[FR['pelvis']['cloth'][0], FR['pelvis']['cloth'][1], ('mound', _mound, set()), ('mound', mx(_mound), set())],
    )
BACK['pelvis']['lines'] += [('seam', [(0, 339), (0, 380), (0, 410)])]

# ---------------- THIGH (hamstrings) ----------------
_hamL = [(-76, 452), (-79, 482), (-75, 516), (-66, 547), (-56, 552), (-52, 520), (-50, 484), (-56, 456)]
_hamM = [(-43, 452), (-36, 490), (-31, 526), (-29, 556), (-20, 549), (-17, 514), (-14, 484), (-19, 456)]
BACK['thigh'] = bk(FR['thigh'], mus=[('hams', _hamL), ('hams', _hamM)],
    lines=[('split', [(-46, 456), (-46, 500), (-45, 548)]), ('crease', [(-60, 569), (-44, 574), (-27, 569)])],
    cloth=[FR['thigh']['cloth'][0]], hem=FR['thigh']['hem'])

# ---------------- SHIN (calf) ----------------
_gl = [(-52, 590), (-64, 590), (-72, 610), (-71, 640), (-62, 666), (-52, 684), (-47, 700), (-45, 670), (-46, 625), (-49, 598)]
_gm = [(-41, 590), (-31, 589), (-19, 606), (-15, 632), (-19, 658), (-30, 678), (-42, 700), (-46, 700), (-46, 664), (-45, 620), (-43, 598)]
_sol = [(-62, 650), (-68, 672), (-65, 696), (-56, 714), (-46, 720), (-36, 714), (-28, 696), (-26, 672), (-32, 652)]
BACK['shin'] = bk(FR['shin'], mus=[('soleus', _sol), ('gastro', _gl), ('gastro', _gm)],
    lines=[('tendon', [(-46, 702), (-46, 727)])],
    )

# ---------------- FOOT (heel view) ----------------
_shoe_b = [(-63, 727), (-46, 723), (-29, 727), (-27, 745), (-26, 763), (-29, 772), (-63, 772), (-66, 763), (-65, 745)]
BACK['foot'] = dict(piv=(-46, 732), limb=True, shoe=True, base=(_shoe_b, set()),
    cloth=[('sole', [(-71, 768), (-21, 768), (-18, 775), (-23, 781), (-69, 781), (-74, 775)], set()),
           ('tab', blob(-46, 733.5, 4.6, 5.4, 0, 2.2), set())],
    lines=[('collar', [(-61, 731), (-46, 727.5), (-31, 731)]), ('counter', [(-64, 752), (-46, 755.5), (-28, 752)])],
    mus=[], sh=[], bones=[], bone_lines=[])

# ---------------- ARMS ----------------
_tri_lat = [(-119, 196), (-123, 226), (-119, 262), (-111, 285), (-103, 285), (-103, 250), (-105, 214)]
_tri_long = [(-97, 200), (-88, 224), (-87, 258), (-92, 285), (-100, 285), (-101, 252), (-100, 220)]
BACK['upperArm'] = bk(FR['upperArm'], mus=[('triceps', _tri_lat), ('triceps', _tri_long), ('delt', FR['upperArm']['mus'][3][1])],
    lines=[('crease', [(-110, 292), (-100, 295), (-92, 292)]), ('split', [(-102, 214), (-102, 262), (-101, 284)])])
BACK['upperArm_nd'] = dict(BACK['upperArm'], mus=[m for m in BACK['upperArm']['mus'] if m[0] != 'delt'])
BACK['upperArm_flex'] = bk(FR['upperArm_flex'],
    mus=[('triceps', [(-119, 204), (-132, 224), (-137, 248), (-129, 272), (-115, 284), (-103, 270), (-99, 246), (-104, 222)]),
         ('triceps', FR['upperArm_flex']['mus'][0][1])],
    lines=[('crease', [(-110, 292), (-100, 295), (-92, 292)]), ('split', [(-103, 224), (-104, 254), (-102, 280)])])
BACK['forearm'] = bk(FR['forearm'],
    mus=[('extensor', [(-114, 304), (-121, 322), (-117, 350), (-110, 372), (-105, 350), (-107, 322)]),
         ('extensor', [(-93, 308), (-87, 330), (-90, 364), (-98, 382), (-101, 350), (-98, 320)])],
    lines=[('split', [(-102, 316), (-101, 350), (-100, 392)])])
BACK['hand'] = bk(FR['hand'], lines=FR['hand']['lines'], cloth=FR['hand']['cloth'])
BACK['fist'] = bk(FR['fist'], lines=FR['fist']['lines'])
BACK['cap'] = bk(FR['cap'], mus=FR['cap']['mus'], lines=FR['cap']['lines'])
BACK['flare'] = bk(FR['flare'], mus=FR['flare']['mus'])

# ======================================== FEMALE ========================================
BACK_F = {}
def _ff(f): return lambda D: F.morph(D, f)
for key, f in dict(head=F.ax(0, .94), neck=F.ax(0, .86), thigh=F.ax(-43, .92, 1.5), shin=F.ax(-43, .86, 1), foot=F.ax(-46, .9, 1),
                   upperArm=F.ax(-100, .84, 14), upperArm_flex=F.ax(-100, .84, 14), upperArm_nd=F.ax(-100, .84, 14),
                   forearm=F.ax(-101, .84, 14), hand=F.ax(-101, .85, 14), fist=F.ax(-101, .85, 14), cap=F.ax(-100, .88, 14)).items():
    BACK_F[key] = F.morph(BACK[key], f)
BACK_F['flare'] = dict(bk(F.FRONT_F['flare']), mus=F.FRONT_F['flare']['mus'])

def fw(x, y):
    """warp the male torso coordinates into the narrower female chest (waist converges)"""
    s = 0.86 if y < 230 else 0.86 - (y - 230) / 42 * 0.12
    return (x * s, y)
def fwp(pts): return [(*fw(p[0], p[1]), *p[2:]) for p in pts]
def fwb(cx, cy, rx, ry, rot, p=2.8): return blob(*fw(cx, cy), rx * .86, ry * .95, rot, p)

_trap_f = [(-3, 140), (-20.5, 132), (-35, 139), (-53, 148), (-72, 157), (-78, 162), (-65, 168), (-52, 172), (-40, 178), (-30, 192), (-22, 211), (-12, 231), (-3, 248)]
_Mf = dict(lat=fwp(_lat_b), erec=fwp(_erec_c), infra=fwb(-63, 190, 19, 12, 16), teres=fwb(-79, 207, 12, 5.6, -12), trap=_trap_f)
_scap_f, _med_f = fwp(_scap), fwp(_med)

# bra back views (default sports top = racerback; padded push-up = straight straps + clasp)
_bandS = [(0, 197, 'c'), (-81, 197, 'c'), (-75, 216), (-66.5, 236, 'c'), (0, 236, 'c')]
_racer = [(-47, 143.5, 'c'), (-53.5, 145.5, 'c'), (-8, 199, 'c'), (0, 199, 'c')]
_bandP = [(0, 229, 'c'), (-69, 229, 'c'), (-66.5, 236, 'c'), (0, 236, 'c')]
_strP = [(-48, 191, 'c'), (-48, 145.5, 'c'), (-54.5, 147.5, 'c'), (-54.5, 193, 'c')]
_chest_f_base = F.FRONT_F['chest']['base']

def _chest_f(cloth, hem):
    return dict(piv=(0, 266), sym=True, base=_chest_f_base, mus=back_chest_mus(_Mf),
                lines=[('spine', fwp(_spine)), ('scap', _scap_f), ('scap', mx(_scap_f)), ('scap_med', _med_f), ('scap_med', mx(_med_f))],
                cloth=cloth, hem=hem, sh=[], bones=[], bone_lines=[])
BACK_F['chest_sport'] = _chest_f([('bra', sym(_bandS, 0, 0)[0], set()), ('strap', _racer, set()), ('strap', mx(_racer), set())], [(-66.5, 236), (-33, 236), (0, 236), (33, 236), (66.5, 236)])
BACK_F['chest_push'] = _chest_f([('bra', sym(_bandP, 0, 0)[0], set()), ('strap', _strP, set()), ('strap', mx(_strP), set()),
                                 ('clasp', [(-4, 226, 'c'), (4, 226, 'c'), (4, 239, 'c'), (-4, 239, 'c')], set())], [(-66.5, 236), (0, 236), (66.5, 236)])
BACK_F['chest_bralette'] = BACK_F['chest_sport']

_mound_f = [(-3, 340), (-20, 335), (-43, 338), (-62, 349), (-71, 367), (-69, 385), (-56, 396), (-34, 400), (-12, 399), (-3, 389)]
_glute_gf = [(-4, 336), (-24, 330), (-50, 336), (-68, 352), (-76, 374), (-70, 393), (-50, 403), (-26, 406), (-6, 401)]
_erec_pf = [(-4, 262), (-11, 262), (-17, 274), (-18, 292), (-17, 312), (-10, 325), (-4, 328)]
_flank_f = [(-47, 272), (-48, 288), (-52, 304), (-58, 316), (-60, 304), (-55, 290), (-52, 274)]
BACK_F['pelvis'] = dict(piv=(0, 330), sym=True, base=F.FRONT_F['pelvis']['base'],
    mus=[('erector', _erec_pf), ('erector', mx(_erec_pf)), ('glute', _glute_gf), ('glute', mx(_glute_gf))],
    lines=[('spine', [(0, 262), (0, 300), (0, 328)]), ('dimple', [(-13, 316), (-9, 320)]), ('dimple', [(13, 316), (9, 320)]), ('seam', [(0, 339), (0, 380), (0, 402)])],
    cloth=[F.FRONT_F['pelvis']['cloth'][0], F.FRONT_F['pelvis']['cloth'][1], ('mound', _mound_f, set()), ('mound', mx(_mound_f), set())],
    sh=[], bones=[], bone_lines=[])

# ponytail from behind: tied high, swept to the viewer's right like the front view
pony_b = [(-4, 6), (8, 1), (21, 7), (31, 28), (40, 60), (48, 100), (52, 140), (50, 178), (45, 208, 'c'), (39, 178), (35, 140), (29, 104), (21, 70), (11, 46), (0, 28)]
BACK_F['pony'] = dict(piv=(8, 16), base=(pony_b, set()),
    mus=[('hairplane', [(20, 18), (31, 40), (37, 74), (42, 112), (45, 150), (42, 176), (41, 144), (37, 108), (31, 76), (24, 46)])],
    lines=[], cloth=[('tie', blob(9, 16, 6, 6.6, 0, 2.2), set())], sh=[], bones=[], bone_lines=[])

DATA_B = {'m': BACK, 'f': BACK_F}
