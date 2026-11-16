"""Round 7 additions to the Cobalt Sculpt data (Motion Lab, 2026-11-09), applied in place on import.

Owner requests after the handover: better hands (finger joints, a real fist, a side-view hand,
grip hands for dumbbells), a two-piece shoe that bends at the toe, bendable (curved) bra straps,
and more back-muscle detail (upper / middle / lower trapezius, rhomboids under them, teres major,
two erector columns). Everything is authored for the viewer-left half like the rest of the rig.
build2 imports this module right after the data modules, so every view and both genders get it.
"""
from rig import blob, mx, sym
import rig as M
import rig_f as F
import rig_back as RB

FR, SD, BK = M.FRONT, M.SIDE, RB.BACK


# ------------------------------------------------------------------ hands (front / back)
def _knuckles(hand):
    """PIP creases across each finger of the open front hand, plus the thumb's IP crease"""
    fing = [(-109.6, 456.5), (-103.9, 465), (-98.2, 468), (-92.5, 463)]
    out = [('knuckle', [(cx - 1.9, 445 + (T - 445) * .46), (cx + 1.9, 445 + (T - 445) * .46)]) for cx, T in fing]
    out.append(('knuckle', [(-88.4, 437.5), (-83.6, 438.5)]))
    return hand['lines'] + out


FR['hand'] = dict(FR['hand'], lines=_knuckles(FR['hand']))

# a fist seen from the back of the hand: four knuckle bumps, finger splits, the curl fold, thumb across
_fist = [(-111, 402), (-116.5, 415), (-117.5, 430), (-115.8, 443), (-114.5, 449.5), (-111.5, 452.8), (-108.3, 450.6, 'c'),
         (-105, 454.2), (-101.7, 451, 'c'), (-98.4, 454.4), (-95.2, 451, 'c'), (-92, 453.6), (-88.9, 449.6), (-87.2, 440),
         (-86.6, 426), (-88, 413), (-91, 405)]
FR['fist'] = dict(piv=(-101, 406), limb=True, base=(_fist, {6, 8, 10}),
    mus=[('thumbpad', [(-88, 418), (-92.5, 428), (-101, 434.5), (-108.5, 437), (-106.5, 431), (-98, 425.5), (-91, 414)])],
    lines=[('finger', [(-108.4, 450.4), (-108.6, 444)]), ('finger', [(-101.7, 450.8), (-101.8, 444)]), ('finger', [(-95.2, 450.8), (-95.1, 444)]),
           ('fold', [(-115.2, 442.5), (-101.5, 445.2), (-88, 442)])],
    cloth=[], sh=[], bones=[], bone_lines=[])
BK['hand'] = dict(BK['hand'], lines=_knuckles(BK['hand']))
BK['fist'] = RB.bk(FR['fist'], lines=FR['fist']['lines'], mus=[])          # from behind: knuckles, no thumb pad

# ------------------------------------------------------------------ hands (side): open hand and grip
SD['hand'] = dict(piv=(0, 404),
    base=([(-9, 400), (-11, 418), (-11.5, 432), (-10.5, 446), (-9, 456), (-5, 466), (0, 470), (5, 467), (8, 460), (10, 452), (11, 447, 'c'),
           (14, 452), (17.5, 449), (18.5, 439), (16.5, 424), (12, 410), (10, 403)], {10}),
    mus=[('thumbpad', [(12, 413), (15.6, 424), (16.8, 437), (15.4, 445.5), (13, 440), (12, 427)])],
    lines=[('finger', [(-5, 457), (-1.5, 467)]), ('finger', [(-1, 455), (2.6, 466)]), ('knuckle', [(-10, 447), (-4.5, 448.5)])],
    cloth=[], sh=[], bones=[], bone_lines=[])
# a closed fist in profile around a handle that runs into the screen (dumbbells): back of the hand on the
# left, curled fingers below, thumb wrapped over the front; handle centre = GRIP_SIDE
SD['grip'] = dict(piv=(0, 404),
    base=([(-9, 400), (-12, 415), (-13, 430), (-11.5, 443), (-6.5, 451.5), (1.5, 455.5), (9, 454), (14, 448), (16.8, 439), (17.6, 428),
           (15.4, 415), (10, 403)], set()),
    mus=[('thumbpad', [(9.5, 413), (15, 421), (16.4, 432), (13.5, 440), (8.5, 438), (7.5, 426)])],
    lines=[('fold', [(-10.5, 443), (-3, 446.5), (5, 445.5), (11.5, 441)]), ('finger', [(-2.5, 446.8), (-1.8, 454.5)]), ('finger', [(4.8, 445.8), (5.8, 453.8)])],
    cloth=[], sh=[], bones=[], bone_lines=[])
GRIP_SIDE = (3, 434)          # handle centre in neutral coordinates (hand pivot (0, 404))
GRIP_FRONT = (-101.5, 432)    # handle centre of the front/back fist

# ------------------------------------------------------------------ two-piece shoe (side): toes bend at the ball
TOE_PIV = (30, 773)
SD['foot'] = dict(piv=(-2, 732), shoe=True,
    base=([(-22, 742), (-26, 760), (-22, 773), (-6, 777), (18, 777), (29, 777.5), (34.5, 771), (37, 761), (34, 750), (16, 744), (10, 732), (-14, 730)], set()),
    cloth=[('sole', [(-26, 768), (24, 769), (31.5, 770), (33.5, 775), (28, 778.5), (-6, 778), (-22, 775)], set())],
    lines=[('lace', [(2, 740), (16, 748)]), ('lace', [(8, 737), (21, 746)])], mus=[], sh=[], bones=[], bone_lines=[])
SD['toes'] = dict(piv=TOE_PIV, shoe=True,
    base=([(25, 752), (34, 750), (51, 758), (57, 769), (50, 776), (40, 777.5), (30, 778), (24.5, 775.5), (22.5, 766)], set()),
    cloth=[('sole', [(30, 770.5), (50, 768), (57, 771), (46, 778.5), (30, 778.6), (26, 775)], set())],
    lines=[('toecap', [(31, 752.5), (41, 762)])], mus=[], sh=[], bones=[], bone_lines=[])


# ------------------------------------------------------------------ curved straps
def _band(inner, outer):
    """a strap band from an inner and an outer edge (both listed bottom to top); corners at the four ends"""
    a = [(inner[0][0], inner[0][1], 'c')] + inner[1:-1] + [(inner[-1][0], inner[-1][1], 'c')]
    b = [(outer[-1][0], outer[-1][1], 'c')] + outer[-2:0:-1] + [(outer[0][0], outer[0][1], 'c')]
    return a + b


# front straps follow the chest: they bow out over the pec line and land on the trapezius slope
_strS_c = _band([(-46.5, 199), (-47.6, 182), (-48.6, 165), (-48.6, 152), (-47, 143.5)],
                [(-53.5, 199), (-55, 182), (-56, 166), (-55.6, 153), (-54, 146)])
_strP_c = _band([(-47.5, 192), (-48.8, 176), (-49.6, 160), (-48.6, 145.5)],
                [(-54.8, 194), (-56.3, 177), (-57, 161), (-55.4, 147.5)])
# racerback from behind: an S that hugs the scapula's medial border
_racer_c = [(-47, 143.5, 'c'), (-53.5, 145.5, 'c'), (-46, 158), (-35, 173), (-21, 188), (-8, 199, 'c'), (0, 199, 'c'), (-14, 186), (-27, 171), (-38, 157)]
_strPb_c = _band([(-48, 191), (-49.2, 175), (-49.6, 160), (-48, 145.5)], [(-54.5, 193), (-55.9, 176), (-56.3, 161), (-54.5, 147.5)])


def _swap(cloth, name, new):
    """replace the viewer-left / right pair of cloth pieces called `name` with `new` and its mirror"""
    out, done = [], False
    for c in cloth:
        if c[0] != name:
            out.append(c)
        elif not done:
            out += [(name, new, set()), (name, mx(new), set())]
            done = True
    return out


for key, s in (('chest_sport', _strS_c), ('chest_push', _strP_c)):
    F.FRONT_F[key] = dict(F.FRONT_F[key], cloth=_swap(F.FRONT_F[key]['cloth'], 'strap', s))
for key, s in (('chest_sport', _racer_c), ('chest_push', _strPb_c)):
    RB.BACK_F[key] = dict(RB.BACK_F[key], cloth=_swap(RB.BACK_F[key]['cloth'], 'strap', s))
F.SIDE_F['chest_sport'] = dict(F.SIDE_F['chest_sport'], cloth=[c for c in F.SIDE_F['chest_sport']['cloth'] if c[0] != 'strap']
                               + [('strap', [(-7, 147, 'c'), (-1, 150, 'c'), (0.6, 166), (0.8, 182), (-0.6, 198, 'c'), (-7.4, 198, 'c'), (-6.2, 182), (-6.4, 165)], set())])
F.SIDE_F['chest_push'] = dict(F.SIDE_F['chest_push'], cloth=[c for c in F.SIDE_F['chest_push']['cloth'] if c[0] != 'strap']
                              + [('strap', [(-8, 146, 'c'), (-2, 148, 'c'), (12, 163), (26, 177), (38, 192, 'c'), (31, 196, 'c'), (19, 182), (5, 166)], set())])

# ------------------------------------------------------------------ back detail
_trap_up = [(-3, 138), (-21, 130), (-37, 137), (-57, 146), (-80, 156), (-87, 162), (-73, 168), (-57, 171), (-44, 174), (-28, 166), (-14, 160.5), (-3, 159.5)]
_trap_mid = [(-3, 163.5), (-15, 164.5), (-29, 170.5), (-43, 178), (-37.5, 189), (-27, 197.5), (-14, 200.5), (-3, 200.5)]
_trap_low = [(-3, 204.5), (-14, 204.5), (-26, 200.5), (-33.5, 195.5), (-28, 210), (-19, 223.5), (-11, 236), (-3, 248)]
_erec_lat = [(-22, 240), (-28, 250), (-31, 264), (-28, 273), (-23, 268), (-22, 254)]
_erec_lat_p = [(-22, 262), (-27.5, 271), (-26, 290), (-20.5, 306), (-19, 289), (-20.5, 274)]


def back_chest_mus(lat, erec, erec_l, infra, teres, up, mid, low, rhomb):
    two = lambda nm, p: [(nm, p), (nm, mx(p))]  # noqa: E731
    return (two('lat', lat) + two('erector', erec) + two('erector', erec_l) + two('infra', infra) + two('teres', teres)
            + two('rhomb', rhomb) + two('trap', up) + two('midtrap', mid) + two('lowtrap', low))


BK['chest'] = dict(BK['chest'], mus=back_chest_mus(RB._lat_b, RB._erec_c, _erec_lat, RB._infra, RB._teres, _trap_up, _trap_mid, _trap_low, RB._rhomb))
BK['pelvis'] = dict(BK['pelvis'], mus=BK['pelvis']['mus'] + [('erector', _erec_lat_p), ('erector', mx(_erec_lat_p))])
_fmus = back_chest_mus(RB.fwp(RB._lat_b), RB.fwp(RB._erec_c), RB.fwp(_erec_lat), RB.fwb(-63, 190, 19, 12, 16), RB.fwb(-79, 207, 12, 5.6, -12),
                       RB.fwp(_trap_up), RB.fwp(_trap_mid), RB.fwp(_trap_low), RB.fwp(RB._rhomb))
for key in ('chest_sport', 'chest_push', 'chest_bralette'):
    RB.BACK_F[key] = dict(RB.BACK_F[key], mus=_fmus)
_erec_lat_pf = [(p[0] * .9, p[1]) for p in _erec_lat_p]
RB.BACK_F['pelvis'] = dict(RB.BACK_F['pelvis'], mus=RB.BACK_F['pelvis']['mus'] + [('erector', _erec_lat_pf), ('erector', mx(_erec_lat_pf))])

# ------------------------------------------------------------------ female versions of the new hands and shoe
_fh = F.ax(-101, .85, 14)
F.FRONT_F['hand'] = F.morph(FR['hand'], _fh)
F.FRONT_F['fist'] = F.morph(FR['fist'], _fh)
RB.BACK_F['hand'] = F.morph(BK['hand'], _fh)
RB.BACK_F['fist'] = F.morph(BK['fist'], _fh)
F.SIDE_F['hand'] = F.morph(SD['hand'], F.ax(0, .85))
F.SIDE_F['grip'] = F.morph(SD['grip'], F.ax(0, .85))
F.SIDE_F['foot'] = F.morph(SD['foot'], F.ax(-2, .92))
F.SIDE_F['toes'] = F.morph(SD['toes'], F.ax(-2, .92))

for D in (FR, SD, BK, F.FRONT_F, F.SIDE_F, RB.BACK_F):
    for v in D.values():
        for k in ('mus', 'lines', 'cloth', 'sh', 'bones', 'bone_lines'):
            v.setdefault(k, [])
