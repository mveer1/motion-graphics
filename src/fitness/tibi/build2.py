"""Cobalt Sculpt v2 builder: male + female, generic forward-kinematics poses, activation overlays, faces."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import R, Sp, n, blob, mx
import rig as M
import rig_f as F
import rig_back as RB
import rig_ext as X          # round 7: hands, toes, straps, back detail (patches the data above in place)

DATA = {'m': (M.FRONT, M.SIDE, RB.BACK), 'f': (F.FRONT_F, F.SIDE_F, RB.BACK_F)}
SKS = {'m': (M.SK, M.SK_SIDE), 'f': (F.SK_F, F.SK_SIDE_F)}
LS = {'m': 1.0, 'f': 0.965}          # leg-length factor (female is a little shorter at the same head size)
CX, FLOOR = 300, 846
LX, LY = -0.62, -0.78                # direction TOWARD the light (top-left)
NAVY, COBALT, MARIGOLD, CORAL, BONE, CHAR = '#18286F', '#2F56E0', '#FFB224', '#F2553D', '#F4EAD5', '#22243A'
B_, LT_, DK_ = COBALT, '#4F75EC', '#2244B8'
HAIR, HAIR_LT, HAIR_DK = '#1C3AA3', '#3558CF', '#132A80'

DEFS, REG, BB, CACHE, MASKS, MCACHE = [], {}, {}, {}, [], {}
BRA = {'v': 'sport'}            # 'bralette' | 'push' | 'sport'  (female only; round 3 default = bralette)
HAIRSTYLE = {'v': 'pony'}          # 'pony' | 'curly'  (female only)

def reg(id_, d, pts=None):
    if id_ not in REG:
        REG[id_] = d
        DEFS.append(f'<path id="{id_}" d="{d}"/>')
        if pts:
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            BB[id_] = (min(xs), min(ys), max(xs), max(ys))
    return id_

def mk(g, view, key, side):
    idp = f"{g}{view}_{key}_{side}"
    if idp in CACHE: return CACHE[idp]
    D = DATA[g][{'F': 0, 'S': 1, 'B': 2}[view]][key]
    px, py = D['piv']
    if side == 'R': tf = lambda p: (px - p[0], p[1] - py) + tuple(p[2:])
    else:           tf = lambda p: (p[0] - px, p[1] - py) + tuple(p[2:])
    T = lambda pts: [tf(p) for p in pts]
    S = {}
    pts, skip = D['base']
    t = T(pts); sp = Sp(t)
    d_base, ext = sp.d(), list(t)
    for (bx, by, br) in D.get('blobs', []):       # union of circles (curly hair): same path, extra subpaths
        cx_, cy_ = tf((bx, by))[:2]
        sw_ = 1 if side == 'R' else 0          # the base spline is mirrored for the R side, so its winding flips: match it
        d_base += f"M{n(cx_ - br)},{n(cy_)}a{n(br)},{n(br)} 0 1,{sw_} {n(2 * br)},0a{n(br)},{n(br)} 0 1,{sw_} {n(-2 * br)},0Z"
        ext += [(cx_ - br, cy_ - br), (cx_ + br, cy_ + br)]
    S['base'] = reg(idp + '_b', d_base, ext)
    S['mus'] = []
    for i, (nm, p) in enumerate(D['mus']):
        t = T(p); S['mus'].append((nm, reg(f"{idp}_m{i}", Sp(t).d(), t)))
    S['lines'] = []
    for i, (nm, p) in enumerate(D['lines']):
        t = T(p); S['lines'].append((nm, reg(f"{idp}_l{i}", Sp(t, closed=False).d(), t)))
    S['cloth'] = []
    for i, (nm, p, sk) in enumerate(D['cloth']):
        t = T(p); S['cloth'].append((nm, reg(f"{idp}_c{i}", Sp(t).d(), t)))
    S['hem'] = None
    if D.get('hem'):
        t = T(D['hem']); S['hem'] = reg(idp + '_h', Sp(t, closed=False).d(), t)
    S['sh'] = []
    for i, (nm, p) in enumerate(D['sh']):
        t = T(p); S['sh'].append((nm, reg(f"{idp}_s{i}", Sp(t).d(), t)))
    S['pts'] = ext
    S['sole'] = None
    for nm, p, sk in D['cloth']:
        if nm == 'sole': S['sole'] = T(p)
    CACHE[idp] = S
    return S

# ------------------------------------------------------------------ segments / poses ------------------------------------
class Seg:
    def __init__(s, g, view, key, side, W, th, sx=1, sy=1, far=False, skey=None):
        s.g, s.view, s.skey, s.side, s.W, s.th, s.sx, s.sy, s.far = g, view, skey or key, side, W, th, sx, sy, far
        s.key = key.split('_')[0]

def chest_key(g):
    return 'chest' if g != 'f' else 'chest_' + BRA['v']

def add(a, b): return (a[0] + b[0], a[1] + b[1])

def seg_world_pts(P):
    S = mk(P.g, P.view, P.skey, P.side)
    out = []
    for p in S['pts'] + (S['sole'] or []):
        x, y = R(P.th, (p[0] * P.sx, p[1] * P.sy))
        out.append((P.W[0] + x, P.W[1] + y))
    return out

def settle(segs, joints, contacts=('foot',), lift=0, anchor_x=None):
    """slide the figure vertically so the lowest contact point sits on the floor (minus lift); return bbox"""
    contacts = tuple(contacts) + (('toes',) if 'foot' in contacts else ())
    low = max(y for P in segs if P.key in contacts for (x, y) in seg_world_pts(P))
    dy = FLOOR - lift - low
    for P in segs: P.W = (P.W[0], P.W[1] + dy)
    joints[:] = [((a[0], a[1] + dy), (b[0], b[1] + dy)) for a, b in joints]
    return dy

def front_pose(g, kind, view='F'):
    SK = SKS[g][0]; ls = LS[g]
    V = view
    arms = dict(relaxed=(8, 10, 9), flex=(86, 190, 192), lateral=(80, 86, 84))[kind]
    tt = 1.5 if kind == 'relaxed' else 3.5
    segs, joints = [], []
    for side, sg in (('R', -1), ('L', 1)):
        mir = lambda v: (v[0] * sg, v[1])
        hip = (CX + mir(SK['hip'])[0], SK['hip'][1])
        knee = add(hip, R(tt * sg, mir((SK['knee'][0] - SK['hip'][0], (SK['knee'][1] - SK['hip'][1]) * ls))))
        ank = add(knee, mir((SK['ankle'][0] - SK['knee'][0], (SK['ankle'][1] - SK['knee'][1]) * ls)))
        segs += [Seg(g, V, 'shin', side, knee, 0, 1, ls), Seg(g, V, 'thigh', side, hip, tt * sg, 1, ls), Seg(g, V, 'foot', side, ank, 0)]
        joints += [(hip, knee), (knee, ank)]
    if kind in ('flex', 'lateral'):          # lat wings sit BEHIND the torso so they grow out of its silhouette
        for side in ('R', 'L'): segs.append(Seg(g, V, 'flare', side, (CX + (-1 if side == 'R' else 1) * SK['shoulder'][0], SK['shoulder'][1]), 0))
    segs += [Seg(g, V, 'pelvis', 'C', (CX, 330), 0), Seg(g, V, 'neck', 'C', (CX, 148), 0), Seg(g, V, 'chest', 'C', (CX, 266), 0, skey=chest_key(g))]
    if g == 'f' and HAIRSTYLE['v'] == 'pony' and V == 'F': segs.append(Seg(g, V, 'pony', 'C', (CX + 30, 22), 0))
    segs.append(Seg(g, V, 'head', 'C', (CX, 92), 0))
    if g == 'f' and V == 'B': segs.append(Seg(g, V, 'pony', 'C', (CX + 8, 16), 0))     # seen from behind the tail hangs IN FRONT of the head
    if g == 'f' and HAIRSTYLE['v'] == 'curly': segs.append(Seg(g, V, 'curls', 'C', (CX, 92), 0))
    shoulders = {}
    for side, sg in (('R', -1), ('L', 1)):
        mir = lambda v: (v[0] * sg, v[1])
        sh = (CX + mir(SK['shoulder'])[0], SK['shoulder'][1]); shoulders[side] = sh
        el = add(sh, R(arms[0] * sg, mir((SK['elbow'][0] - SK['shoulder'][0], SK['elbow'][1] - SK['shoulder'][1]))))
        wr = add(el, R(arms[1] * sg, mir((SK['wrist'][0] - SK['elbow'][0], SK['wrist'][1] - SK['elbow'][1]))))
        ua = {'flex': 'upperArm_flex', 'lateral': 'upperArm_nd'}.get(kind, 'upperArm')
        hd = 'fist' if kind == 'flex' else 'hand'
        segs += [Seg(g, V, hd, side, wr, arms[2] * sg, 1.15, 1.15), Seg(g, V, 'forearm', side, el, arms[1] * sg), Seg(g, V, ua, side, sh, arms[0] * sg)]
        joints += [(sh, el), (el, wr)]
    if kind in ('flex', 'lateral'):
        for side in ('R', 'L'): segs.append(Seg(g, V, 'cap', side, shoulders[side], 0))
    settle(segs, joints)
    return segs, joints, dict(lift=0)

def side_fk(g, spec):
    """generic side-view forward kinematics. angles are absolute, degrees, clockwise-positive
    (a leg/arm that hangs down swings FORWARD with a negative angle; an upright torso leans FORWARD with a positive one)"""
    ls = LS[g]
    pel = spec.get('pel', (CX, 330))
    tp, tc, tn, th = spec.get('tp', 0), spec.get('tc', 0), spec.get('tn', 0), spec.get('th', 0)
    hip = add(pel, R(tp, (0, 58)))
    chest = add(pel, R(tp, (0, -64)))
    neck = add(chest, R(tc, (0, -118)))
    head = add(neck, R(tn, (0, -56)))
    shoulder = add(chest, R(tc, (2, -102)))
    joints = []
    def leg(L, far):
        t, s, f = L['t'], L['s'], L['f']
        o = L.get('o', f)                      # toes (absolute); default: no bend at the ball
        knee = add(hip, R(t, (0, 178 * ls))); ank = add(knee, R(s, (-2, 166 * ls)))
        D = DATA[g][1]
        ball = add(ank, R(f, (D['toes']['piv'][0] - D['foot']['piv'][0], D['toes']['piv'][1] - D['foot']['piv'][1])))
        joints.extend([(hip, knee), (knee, ank)])
        return [Seg(g, 'S', 'shin', 'C', knee, s, 1, ls, far), Seg(g, 'S', 'thigh', 'C', hip, t, 1, ls, far),
                Seg(g, 'S', 'foot', 'C', ank, f, far=far), Seg(g, 'S', 'toes', 'C', ball, o, far=far)]   # toes on top: no seam at rest
    def arm(A, far):
        u, fa, ha = A['u'], A['fa'], A['ha']
        el = add(shoulder, R(u, (-2, 134))); wr = add(el, R(fa, (0, 106)))
        joints.extend([(shoulder, el), (el, wr)])
        return [Seg(g, 'S', 'hand', 'C', wr, ha, 1.15, 1.15, far), Seg(g, 'S', 'forearm', 'C', el, fa, far=far), Seg(g, 'S', 'upperArm', 'C', shoulder, u, far=far)]
    segs = arm(spec['far']['arm'], True) + leg(spec['far']['leg'], True) + leg(spec['near']['leg'], False)
    segs += [Seg(g, 'S', 'pelvis', 'C', pel, tp), Seg(g, 'S', 'neck', 'C', neck, tn), Seg(g, 'S', 'chest', 'C', chest, tc, skey=chest_key(g))]
    if g == 'f' and HAIRSTYLE['v'] == 'pony': segs.append(Seg(g, 'S', 'pony', 'C', add(head, R(th, (-30, -68))), th * 0.3))
    segs.append(Seg(g, 'S', 'head', 'C', head, th))
    if g == 'f' and HAIRSTYLE['v'] == 'curly': segs.append(Seg(g, 'S', 'curls', 'C', head, th))
    segs += arm(spec['near']['arm'], False)
    return segs, joints

def lo(*a): return dict(t=a[0], s=a[1], f=a[2], **({'o': a[3]} if len(a) > 3 else {}))
def ar(*a): return dict(u=a[0], fa=a[1], ha=a[2])

SIDE_POSES = {}
SIDE_POSES['stand'] = dict(near=dict(leg=lo(1, 0, 0), arm=ar(-4, -18, -20)), far=dict(leg=lo(-8, 4, 0), arm=ar(-14, -30, -30)),
                           contacts=('foot',))
# running gait (facing right). contact / mid-stance / toe-off / flight
SIDE_POSES['run_strike'] = dict(tp=5, tc=9, tn=8, th=4,
    near=dict(leg=lo(-30, -14, -6), arm=ar(34, -52, -40)), far=dict(leg=lo(24, 72, 36), arm=ar(-44, -134, -120)), contacts=('foot',))
SIDE_POSES['run_mid'] = dict(tp=6, tc=10, tn=8, th=4,
    near=dict(leg=lo(-6, 14, 0), arm=ar(-6, -92, -92)), far=dict(leg=lo(-34, 62, 22), arm=ar(6, -70, -60)), contacts=('foot',))
SIDE_POSES['run_off'] = dict(tp=8, tc=12, tn=10, th=5,
    near=dict(leg=lo(30, 36, 62, 22), arm=ar(-44, -128, -118)), far=dict(leg=lo(-64, -6, 18), arm=ar(40, -46, -34)), contacts=('foot',))
SIDE_POSES['run_fly'] = dict(tp=7, tc=11, tn=9, th=4, lift=46,
    near=dict(leg=lo(34, 80, 58), arm=ar(-36, -120, -110)), far=dict(leg=lo(-56, -10, 14), arm=ar(34, -48, -40)), contacts=('foot',))
SIDE_POSES['squat'] = dict(pel=(CX, 330), tp=42, tc=48, tn=40, th=22,
    near=dict(leg=lo(-84, 24, 0), arm=ar(-84, -88, -88)), far=dict(leg=lo(-84, 24, 0), arm=ar(-88, -92, -92)), contacts=('foot',))
SIDE_POSES['calf'] = dict(near=dict(leg=lo(0, 0, 46, 0), arm=ar(-4, -18, -20)), far=dict(leg=lo(0, 0, 46, 0), arm=ar(-12, -28, -28)), contacts=('foot',))

def plank_spec(beta, kind):
    if kind == 'plank':
        arm_n, arm_f = ar(2, -88, -88), ar(6, -90, -90)
    else:
        arm_n, arm_f = ar(beta - 62, 2, -90), ar(beta - 60, 4, -90)
    return dict(tp=beta, tc=beta, tn=beta - 4, th=beta - 16,
                near=dict(leg=lo(beta, beta, beta + 4), arm=arm_n), far=dict(leg=lo(beta, beta, beta + 4), arm=arm_f))

def side_pose(g, name):
    if name == 'side': name = 'stand'
    if name in ('plank', 'pushup'):
        contacts = ('foot', 'hand')
        def err(b):
            segs, joints = side_fk(g, plank_spec(b, name))
            lowf = max(y for P in segs if P.key in ('foot', 'toes') for x, y in seg_world_pts(P))
            lowh = max(y for P in segs if P.key == 'hand' and not P.far for x, y in seg_world_pts(P))
            return lowh - lowf
        lo_b, hi_b = (64.0, 86.0)
        for _ in range(40):
            mid = (lo_b + hi_b) / 2
            if err(mid) > 0: hi_b = mid          # hands too low -> body not tilted enough? (lower beta lifts the shoulder)
            else: lo_b = mid
        beta = (lo_b + hi_b) / 2
        spec = plank_spec(beta, name); spec['contacts'] = contacts
    else:
        spec = SIDE_POSES[name]
    segs, joints = side_fk(g, spec)
    settle(segs, joints, spec.get('contacts', ('foot',)), spec.get('lift', 0))
    return segs, joints, dict(lift=spec.get('lift', 0))

# ------------------------------------------------------------------ back and top-down poses (round 7) ----------------------
# Poses with depth seen from behind (running, squat) or from above (prone and push-up work): joint values use the
# rig's front/back conventions (abduction-style in-plane angles; data side L = viewer-left rotates +value, R -value,
# knees the opposite sign) and every segment carries a foreshortening factor f (its art is scaled 1 x f along its
# own axis, and its children's offsets along that axis are scaled by f too, so the chain never shears). A negative
# f flips a segment that points back toward the viewer (a shin folded up behind a running leg). The runtime
# (src/studio/kits/fitness/sculpt.js on studio-rig.js) uses exactly the same rule.
def _arm_state(j, x):
    ab, el = j.get('shoulder' + x, 0), j.get('elbow' + x, 0)
    return 'down' if ab < 50 else ('flex' if el >= 60 else 'raised')

def rig_pose(g, spec, view='B'):
    j, f, rot, grip = spec.get('j', {}), spec.get('f', {}), spec.get('rot', 0), spec.get('grip', False)
    SK, ls = SKS[g][0], LS[g]
    sub = lambda a, b: (a[0] - b[0], a[1] - b[1])                                      # noqa: E731
    off = {'spine': (0, -64), 'chest': (0, 0), 'neck': (0, -118), 'head': (0, -56)}
    par = {'spine': 'pelvis', 'chest': 'spine', 'neck': 'chest', 'head': 'neck'}
    sgn = {'pelvis': 1, 'spine': 1, 'chest': 1, 'neck': 1, 'head': 1}
    for x, m in (('L', 1), ('R', -1)):
        off['shoulder' + x] = (m * SK['shoulder'][0], SK['shoulder'][1] - 266)
        off['elbow' + x] = (m * (SK['elbow'][0] - SK['shoulder'][0]), SK['elbow'][1] - SK['shoulder'][1])
        off['wrist' + x] = (m * (SK['wrist'][0] - SK['elbow'][0]), SK['wrist'][1] - SK['elbow'][1])
        off['hip' + x] = (m * SK['hip'][0], SK['hip'][1] - 330)
        off['knee' + x] = (m * (SK['knee'][0] - SK['hip'][0]), (SK['knee'][1] - SK['hip'][1]) * ls)
        off['ankle' + x] = (m * (SK['ankle'][0] - SK['knee'][0]), (SK['ankle'][1] - SK['knee'][1]) * ls)
        par.update({'shoulder' + x: 'chest', 'elbow' + x: 'shoulder' + x, 'wrist' + x: 'elbow' + x,
                    'hip' + x: 'pelvis', 'knee' + x: 'hip' + x, 'ankle' + x: 'knee' + x})
        sgn.update({'shoulder' + x: m, 'elbow' + x: m, 'wrist' + x: m, 'hip' + x: m, 'knee' + x: -m, 'ankle' + x: m})
    W, A = {'pelvis': (CX, 330)}, {'pelvis': rot + j.get('pelvis', 0)}
    for k in ('spine', 'chest', 'neck', 'head', 'hipL', 'kneeL', 'ankleL', 'hipR', 'kneeR', 'ankleR',
              'shoulderL', 'elbowL', 'wristL', 'shoulderR', 'elbowR', 'wristR'):
        p_ = par[k]; o = off[k]
        W[k] = add(W[p_], R(A[p_], (o[0], o[1] * f.get(p_, 1))))
        A[k] = A[p_] + sgn[k] * j.get(k, 0)
    F_ = lambda k: f.get(k, 1)                                                          # noqa: E731
    S = lambda key, side, k, sc=1, skey=None: Seg(g, view, key, side, W[k], A[k], sc, sc * F_(k), skey=skey)  # noqa: E731
    legs, arms, caps, flares, torso = [], [], [], [], []
    for x in ('R', 'L'):
        legs += [S('shin', x, 'knee' + x), S('thigh', x, 'hip' + x), S('foot', x, 'ankle' + x)]
        st = _arm_state(j, x)
        hand = 'fist' if (st == 'flex' or grip) else 'hand'
        ua = {'down': 'upperArm', 'raised': 'upperArm_nd', 'flex': 'upperArm_flex'}[st]
        arms += [S(hand, x, 'wrist' + x, 1.1), S('forearm', x, 'elbow' + x), S(ua, x, 'shoulder' + x)]   # 1.1: what figure() draws for 1.15
        if st != 'down':
            o = off['shoulder' + x]
            pos = add(W['chest'], R(A['chest'], (o[0], o[1] * F_('chest'))))
            caps.append(Seg(g, view, 'cap', x, pos, A['chest'], 1, F_('chest')))
            flares.append(Seg(g, view, 'flare', x, pos, A['chest'], 1, F_('chest')))
    torso += [Seg(g, view, 'pelvis', 'C', W['pelvis'], A['pelvis'], 1, F_('pelvis')), S('neck', 'C', 'neck'),
              Seg(g, view, 'chest', 'C', W['chest'], A['chest'], 1, F_('chest'), skey=chest_key(g)), S('head', 'C', 'head')]
    pony = []
    if g == 'f':
        ph = (8, -76) if view == 'B' else (30, -70)
        top = spec.get('order') == 'top'      # from above the tail hangs toward the floor: foreshortened along the head
        pony.append(Seg(g, view, 'pony', 'C', add(W['head'], R(A['head'], (ph[0], ph[1] * F_('head')))), A['head'] if top else A['head'] * .3,
                        1, .4 if top else 1))
    if view == 'F' and spec.get('order') == 'top':
        torso = pony + torso                  # lying on the back: the tail is under the head
    else:
        torso = torso + pony
    joints = [(W['hip' + x], W['knee' + x]) for x in 'LR'] + [(W['knee' + x], W['ankle' + x]) for x in 'LR'] \
        + [(W['shoulder' + x], W['elbow' + x]) for x in 'LR'] + [(W['elbow' + x], W['wrist' + x]) for x in 'LR']
    if spec.get('order') == 'top':        # seen from above: arms hang below the body, caps sit on top
        segs = arms + legs + flares + torso + caps
    else:
        segs = legs + flares + torso + arms + caps
    return segs, joints, W, A

BACK3D = {
    # prisoner squat from behind: thighs foreshortened, knees out, hands on the back of the head
    'back_squat': dict(j=dict(hipL=28, hipR=28, kneeL=20, kneeR=20, ankleL=-8, ankleR=-8, shoulderL=130, shoulderR=130,
                              elbowL=110, elbowR=110, wristL=10, wristR=10),
                       f=dict(hipL=.16, hipR=.16, kneeL=.8, kneeR=.8, chest=.86, neck=.7, shoulderL=.48, shoulderR=.48, wristL=.9, wristR=.9)),
    # running from behind, right leg in stance (left leg mirrors): contact, mid-stance, toe-off, flight
    'back_run_strike': dict(j=dict(pelvis=2, hipR=3, kneeR=4, ankleR=-6, hipL=-1, kneeL=-4, ankleL=6, shoulderR=12, elbowR=-24, shoulderL=16, elbowL=18),
                            f=dict(hipR=.93, kneeR=.99, hipL=.97, kneeL=-.38, ankleL=-.7, shoulderR=.86, elbowR=.36, shoulderL=.74, elbowL=-.32, wristL=.6, wristR=.6)),
    'back_run_mid': dict(j=dict(pelvis=-2, hipR=2, kneeR=1, ankleR=-3, hipL=6, kneeL=4, ankleL=-6, shoulderR=10, elbowR=-10, shoulderL=10, elbowL=-10),
                         f=dict(hipR=.99, kneeR=.95, hipL=.6, kneeL=.52, ankleL=.7, shoulderR=.92, elbowR=.4, shoulderL=.92, elbowL=.4, wristL=.7, wristR=.7)),
    'back_run_off': dict(j=dict(pelvis=1, hipR=-1, kneeR=-2, ankleR=3, hipL=5, kneeL=3, ankleL=-6, shoulderR=16, elbowR=18, shoulderL=12, elbowL=-24),
                         f=dict(hipR=.95, kneeR=.82, ankleR=.55, hipL=.77, kneeL=.97, shoulderR=.74, elbowR=-.32, shoulderL=.86, elbowL=.36, wristL=.6, wristR=.6)),
    'back_run_fly': dict(lift=40, j=dict(pelvis=0, hipR=0, kneeR=-3, ankleR=4, hipL=4, kneeL=2, ankleL=-4, shoulderR=14, elbowR=8, shoulderL=14, elbowL=-12),
                         f=dict(hipR=.97, kneeR=.2, ankleR=-.5, hipL=.7, kneeL=.9, shoulderR=.8, elbowR=-.1, shoulderL=.88, elbowL=.38, wristL=.6, wristR=.6)),
    # seen from above (rot 90: head to the right); arms hang below the body unless raised into the picture plane
    'top_pushup': dict(order='top', rot=90, j=dict(shoulderL=72, shoulderR=72, hipL=2, hipR=2, kneeL=2, kneeR=2),
                       f=dict(shoulderL=.13, shoulderR=.13, elbowL=.1, elbowR=.1, wristL=.4, wristR=.4, ankleL=.55, ankleR=.55)),
    'top_pushup_bottom': dict(order='top', rot=90, j=dict(shoulderL=48, shoulderR=48, elbowL=-40, elbowR=-40, hipL=2, hipR=2, kneeL=2, kneeR=2),
                              f=dict(shoulderL=.78, shoulderR=.78, elbowL=.12, elbowR=.12, wristL=.4, wristR=.4, ankleL=.55, ankleR=.55)),
    'top_plank': dict(order='top', rot=90, grip=True, j=dict(shoulderL=8, shoulderR=8, elbowL=162, elbowR=162, wristL=4, wristR=4, hipL=2, hipR=2, kneeL=2, kneeR=2),
                      f=dict(shoulderL=.16, shoulderR=.16, ankleL=.55, ankleR=.55)),
    'top_fly_low': dict(order='top', rot=90, grip=True, j=dict(shoulderL=84, shoulderR=84, elbowL=10, elbowR=10, hipL=2, hipR=2, kneeL=2, kneeR=2),
                        f=dict(shoulderL=.14, shoulderR=.14, elbowL=.14, elbowR=.14, wristL=.4, wristR=.4, ankleL=.7, ankleR=.7)),
    'top_fly_high': dict(order='top', rot=90, grip=True, j=dict(shoulderL=90, shoulderR=90, elbowL=14, elbowR=14, hipL=2, hipR=2, kneeL=2, kneeR=2),
                         f=dict(ankleL=.7, ankleR=.7)),
    'top_y_high': dict(order='top', rot=90, grip=True, j=dict(shoulderL=140, shoulderR=140, elbowL=4, elbowR=4, hipL=2, hipR=2, kneeL=2, kneeR=2),
                       f=dict(ankleL=.7, ankleR=.7)),
}

# lying on the back seen from above ('above' view: front art, head to the right): the dumbbell fly
BACK3D.update({
    'above_fly_high': dict(order='top', rot=90, grip=True, j=dict(shoulderL=74, shoulderR=74, elbowL=8, elbowR=8, hipL=2, hipR=2, kneeL=2, kneeR=2),
                           f=dict(shoulderL=.14, shoulderR=.14, elbowL=.14, elbowR=.14, wristL=.4, wristR=.4, ankleL=.55, ankleR=.55)),
    'above_fly_low': dict(order='top', rot=90, grip=True, j=dict(shoulderL=86, shoulderR=86, elbowL=16, elbowR=16, hipL=2, hipR=2, kneeL=2, kneeR=2),
                          f=dict(shoulderL=.92, shoulderR=.92, elbowL=.92, elbowR=.92, ankleL=.55, ankleR=.55)),
})

# bodyweight squat seen from the front (sculpt kit 2.2.0): thighs foreshortened toward the camera, shins tilted
# forward, the trunk leaning in, arms reaching forward (fists toward the camera). The front view paints the legs
# before the shorts, so the thighs sit behind the pelvis: read it as a parallel-ish squat, not a deep one.
BACK3D.update({
    'front_squat': dict(grip=True, j=dict(hipL=36, hipR=36, kneeL=30, kneeR=30, ankleL=-6, ankleR=-6, shoulderL=-16, shoulderR=-16,
                                          elbowL=4, elbowR=4, wristL=0, wristR=0),
                        f=dict(hipL=.18, hipR=.18, kneeL=.86, kneeR=.86, chest=.86, neck=.8, shoulderL=.2, shoulderR=.2, elbowL=.22, elbowR=.22)),
})

def back3d_view(name):
    return 'F' if name.startswith(('above_', 'front_')) else 'B'

def back3d_pose(g, name):
    spec = BACK3D[name]
    segs, joints, W, A = rig_pose(g, spec, back3d_view(name))
    if spec.get('order') == 'top':
        return segs, joints, dict(lift=0, top=True)
    settle(segs, joints, ('foot',), spec.get('lift', 0))
    return segs, joints, dict(lift=spec.get('lift', 0))

def bbox(segs):
    xs, ys = [], []
    for P in segs:
        for x, y in seg_world_pts(P): xs.append(x); ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys))

# ------------------------------------------------------------------ helpers ---------------------------------------------
def fm(**kw): return ''.join(f' {k.replace("_", "-")}="{v}"' for k, v in kw.items())
def U(i, **kw): return f'<use href="#{i}"{fm(**kw)}/>'

def loc(P, v):
    x, y = R(-P.th, v)
    return x / P.sx, y / P.sy

def mask_id(P, shape, amt, hi=False):
    bx0, by0, bx1, by1 = BB.get(shape, (0, 0, 40, 40))
    k = min(amt, 0.33 * min(bx1 - bx0, by1 - by0))
    sg = -1 if hi else 1
    ox, oy = loc(P, (LX * k * sg, LY * k * sg))
    key = (shape, round(ox, 1), round(oy, 1))
    if key in MCACHE: return MCACHE[key]
    mid = f"k{len(MCACHE)}"
    MCACHE[key] = mid
    MASKS.append(f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="-420" y="-480" width="900" height="1000">'
                 f'<use href="#{shape}" fill="#fff"/><use href="#{shape}" fill="#000" transform="translate({n(ox)},{n(oy)})"/></mask>')
    return mid

def cres(P, shape, color, amt=4.5, hi=False, **kw):
    return U(shape, fill=color, mask=f"url(#{mask_id(P, shape, amt, hi)})", **kw)

def poly_lines(S, color, w, op=1, skip=()):
    return [U(i, fill='none', stroke=color, stroke_width=w, stroke_opacity=op, stroke_linecap='round', stroke_linejoin='round')
            for nm, i in S['lines'] if nm not in skip and nm != 'vein']

def far_overlay(P, S, color, op):
    if not P.far: return []
    o = [U(S['base'], fill=color, fill_opacity=op)]
    for nm, i in S['cloth']:
        if nm in ('shortsleg', 'shorts', 'sole', 'thumb'): o.append(U(i, fill=color, fill_opacity=op))
    return o

# ------------------------------------------------------------------ activation ------------------------------------------
# 3 = prime mover (coral)  2 = secondary / assisting (marigold)  1 = stabiliser (pale cobalt)
ALVL = {3: dict(fill='#F2553D', shade='#B3301D', hi='#FF9C86', halo='#F2553D', op=.3),
        2: dict(fill='#FFB224', shade='#CC7A0A', hi='#FFE29A', halo='#FFB224', op=.32),
        1: dict(fill='#8CAEFA', shade='#2F56E0', hi='#C9D9FF', halo='#8CAEFA', op=.0)}
GHOST = ('glute', 'hipflex', 'rhomb')     # deep or covered muscles: drawn over the surface only when activated

def act_level(P, nm, act):
    if not act: return 0
    side = 'far' if P.far else 'near'
    return act.get(nm + '@' + side, act.get(nm, 0))

# ------------------------------------------------------------------ faces -----------------------------------------------
FACE_NAMES = {'A': 'Minimal', 'B': 'Soft features', 'C': 'Ember visor'}

def face_front(style, g):
    nv = f'stroke="{NAVY}" stroke-linecap="round" stroke-linejoin="round" fill="none"'
    o = []
    f = g == 'f'
    if style == 'A':
        for x in (-13.5, 13.5):
            o.append(f'<ellipse cx="{x}" cy="59" rx="4.9" ry="6.4" fill="{NAVY}"/><circle cx="{x - 1.5}" cy="56.8" r="1.5" fill="#fff"/>')
        o.append(f'<path d="M-8.5,76 Q0,84 8.5,76" {nv} stroke-width="2.7"/>')
        if f:
            o.append(f'<path d="M-18.5,55 L-22,52.5 M18.5,55 L22,52.5" {nv} stroke-width="2.1"/>')
    elif style == 'B':
        o.append(f'<path d="M-21,47 Q-13.5,42.5 -6.5,45.5" {nv} stroke-width="{2.4 if f else 3.1}" opacity=".85"/><path d="M21,47 Q13.5,42.5 6.5,45.5" {nv} stroke-width="{2.4 if f else 3.1}" opacity=".85"/>')
        for x in (-13.5, 13.5):
            o.append(f'<ellipse cx="{x}" cy="59.5" rx="4.6" ry="{5.6 if f else 5.2}" fill="{NAVY}"/><circle cx="{x - 1.6}" cy="57.3" r="1.6" fill="#fff"/><circle cx="{x + 1.8}" cy="62" r=".9" fill="#fff" opacity=".7"/>')
        if f:
            o.append(f'<path d="M-18.8,55.5 L-22.6,52.8 M-18,57.8 L-22.4,56.6 M18.8,55.5 L22.6,52.8 M18,57.8 L22.4,56.6" {nv} stroke-width="1.9"/>')
        o.append(f'<path d="M0.5,61 Q-3.6,69.5 0.8,71" fill="none" stroke="{DK_}" stroke-width="2.4" stroke-linecap="round"/>')
        o.append(f'<circle cx="-23" cy="70" r="6.5" fill="{CORAL}" opacity=".28"/><circle cx="23" cy="70" r="6.5" fill="{CORAL}" opacity=".28"/>')
        o.append(f'<path d="M-9,78 Q0,86.5 9,78" {nv} stroke-width="2.6"/>')
        if f: o.append(f'<path d="M-4,82 Q0,84 4,82" fill="none" stroke="{CORAL}" stroke-width="2" stroke-linecap="round" opacity=".8"/>')
    else:  # C ember visor
        for x in (-13.5, 13.5):
            o.append(f'<ellipse cx="{x}" cy="59" rx="5.4" ry="6.6" fill="{MARIGOLD}"/><ellipse cx="{x + .3}" cy="60" rx="2.8" ry="3.7" fill="#FFE08A"/>')
        o.append(f'<path d="M-8,77 Q0,83.5 8,77" fill="none" stroke="#FFE08A" stroke-width="2.5" stroke-linecap="round"/>')
        if f: o.append(f'<path d="M-19.5,54.5 L-23.5,51.5 M19.5,54.5 L23.5,51.5" fill="none" stroke="{MARIGOLD}" stroke-width="2.2" stroke-linecap="round"/>')
    return ''.join(o)

def face_side(style, g):
    nv = f'stroke="{NAVY}" stroke-linecap="round" stroke-linejoin="round" fill="none"'
    f = g == 'f'
    o = []
    if style == 'A':
        o.append(f'<ellipse cx="24" cy="59" rx="4" ry="5.8" fill="{NAVY}"/><circle cx="22.8" cy="56.8" r="1.5" fill="#fff"/>')
        o.append(f'<path d="M27,78 Q32,84 36,78" {nv} stroke-width="2.6"/>')
        if f: o.append(f'<path d="M27.5,55 L31,52.5" {nv} stroke-width="2"/>')
    elif style == 'B':
        o.append(f'<path d="M16,47 Q24,42.5 32,46" {nv} stroke-width="{2.4 if f else 3}" opacity=".85"/>')
        o.append(f'<ellipse cx="25" cy="59.5" rx="4.2" ry="5.5" fill="{NAVY}"/><circle cx="23.8" cy="57.3" r="1.5" fill="#fff"/>')
        o.append(f'<path d="M33,53 Q45,60.5 37.5,67.5 Q35.5,68.5 33.5,67.5 Z" fill="{B_}"/>')
        o.append(f'<path d="M37.5,67.5 Q35.5,68.8 33.5,67.6" fill="none" stroke="{DK_}" stroke-width="2" stroke-linecap="round"/>')
        o.append(f'<circle cx="16" cy="70" r="6" fill="{CORAL}" opacity=".28"/>')
        o.append(f'<path d="M26,78 Q32,85 37,78" {nv} stroke-width="2.5"/>')
        if f: o.append(f'<path d="M27.5,55 L31.5,52.2 M27,57.4 L31.2,56" {nv} stroke-width="1.9"/>')
    else:
        o.append(f'<ellipse cx="25" cy="59" rx="4.8" ry="6.3" fill="{MARIGOLD}"/><ellipse cx="25.6" cy="60" rx="2.4" ry="3.4" fill="#FFE08A"/>')
        o.append(f'<path d="M27,78 Q32,83.5 36,78" fill="none" stroke="#FFE08A" stroke-width="2.4" stroke-linecap="round"/>')
        if f: o.append(f'<path d="M28.5,54.5 L32.5,52" fill="none" stroke="{MARIGOLD}" stroke-width="2.1" stroke-linecap="round"/>')
    return ''.join(o)

HAIR_CAP_F = 'M-40,42 C-43,12 -24,-1.5 0,-1.5 C24,-1.5 43,12 40,42 C37,31 31,26.5 23,27.5 C11,23 -9,24 -22,28 C-30,27 -36,32 -40,42 Z'
HAIR_CAP_FEM = 'M-41,48 C-45,12 -24,-2 0,-2 C24,-2 45,12 41,48 C38,34 33,27 26,25 C14,31 -2,31 -14,24 C-26,27 -35,34 -41,48 Z'
HAIR_CAP_S = 'M-41,48 C-45,16 -26,0 0,-1 C22,-1 38,8 37,34 C34,28 30,25 24,25 C14,22 4,24 -4,31 C-12,36 -22,40 -30,52 C-34,60 -38,60 -41,48 Z'

# ------------------------------------------------------------------ the painter -----------------------------------------
def p_sculpt(P, S, opts):
    act, face = opts.get('act'), opts.get('face')
    g = P.g
    o = []
    key = P.key
    if key == 'curls':
        o.append(U(S['base'], fill=HAIR))
        o.append(cres(P, S['base'], HAIR_DK, 6.5))
        o.append(cres(P, S['base'], HAIR_LT, 3.2, hi=True, opacity=.9))
        for nm, i in S['lines']: o.append(U(i, fill='none', stroke=HAIR_DK, stroke_width=2.4, stroke_opacity=.9, stroke_linecap='round'))
        return o
    if key == 'pony':
        o.append(U(S['base'], fill=HAIR))
        for nm, i in S['mus']: o.append(U(i, fill=HAIR_LT)); o.append(cres(P, i, HAIR_DK, 4.5))
        o.append(cres(P, S['base'], HAIR_DK, 6))
        for nm, i in S['cloth']: o.append(U(i, fill=MARIGOLD))
        return o
    if key in ('foot', 'toes'):
        o.append(U(S['base'], fill='#FBFBFA'))
        o.append(cres(P, S['base'], '#CFD4E6', 5))
        for nm, i in S['cloth']: o.append(U(i, fill='#B9C2DE'))
        o += poly_lines(S, '#B9C2DE', 1.8)
        return o + far_overlay(P, S, NAVY, .25)
    o.append(U(S['base'], fill=B_))
    for nm, i in S['sh']: o.append(U(i, fill=DK_))
    ghosts = []
    for nm, i in S['mus']:
        if nm == 'face':
            if face == 'C':
                o.append(U(i, fill='#1B338F')); o.append(cres(P, i, '#10206A', 5, opacity=.6))
            else:
                o.append(U(i, fill='#3F66E8')); o.append(cres(P, i, DK_, 5, opacity=.55))
            continue
        if nm == 'navel': o.append(U(i, fill=DK_)); continue
        if nm == 'hairplane': continue
        lv = act_level(P, nm, act)
        if nm in GHOST:
            if lv >= 2: ghosts.append((nm, i, lv))
            continue
        if lv:
            c = ALVL[lv]
            if c['op']: o.append(U(i, fill='none', stroke=c['halo'], stroke_width=7, stroke_opacity=c['op'], stroke_linejoin='round'))
            o.append(U(i, fill=c['fill'])); o.append(cres(P, i, c['shade'], 5.5)); o.append(cres(P, i, c['hi'], 2.6, hi=True, opacity=.9))
        else:
            o.append(U(i, fill=LT_)); o.append(cres(P, i, DK_, 5.5))
    o += poly_lines(S, DK_, 1.8, .75, skip=('clav', 'notch', 'lace', 'toecap', 'rim', 'seam'))
    for nm, i in S['cloth']:
        if nm == 'bust':
            o.append(U(i, fill='#33375C')); o.append(cres(P, i, '#15172B', 4.2)); continue
        if nm == 'mound':
            o.append(U(i, fill='#2D3158')); o.append(cres(P, i, '#14162C', 5)); o.append(cres(P, i, '#4A4F80', 2.4, hi=True, opacity=.8)); continue
        o.append(U(i, fill={'band': MARIGOLD, 'thumb': B_, 'tie': MARIGOLD, 'clasp': '#454A7C'}.get(nm, CHAR)))
    for nm, i in S['lines']:
        if nm == 'rim': o.append(U(i, fill='none', stroke='#454A7C', stroke_width=3.6, stroke_opacity=.85, stroke_linecap='round'))
        if nm == 'seam': o.append(U(i, fill='none', stroke='#10122A', stroke_width=2, stroke_opacity=.9, stroke_linecap='round'))
    if S['hem']: o.append(U(S['hem'], fill='none', stroke=MARIGOLD, stroke_width=3.2, stroke_linecap='round'))
    for nm, i, lv in ghosts:
        c = ALVL[lv]
        o.append(U(i, fill='none', stroke=c['halo'], stroke_width=6, stroke_opacity=.25, stroke_linejoin='round'))
        o.append(U(i, fill=c['fill'], fill_opacity=.82)); o.append(cres(P, i, c['shade'], 5.5, opacity=.85)); o.append(cres(P, i, c['hi'], 2.6, hi=True, opacity=.85))
    if key == 'head' and face:
        hd = []
        if face == 'B':
            if g == 'f': hd.append(f'<path d="{HAIR_CAP_FEM if P.view == "F" else HAIR_CAP_S}" fill="{HAIR}"/>')
            else: hd.append(f'<path d="{HAIR_CAP_F if P.view == "F" else HAIR_CAP_S}" fill="{HAIR}"/>')
            if P.view == 'F':
                hd.append(f'<path d="M-30,18 C-22,8 -8,5 6,5" fill="none" stroke="{HAIR_LT}" stroke-width="4" stroke-linecap="round" opacity=".8"/>')
                for sx_ in (-1, 1): hd.append(f'<ellipse cx="{sx_ * 40.5}" cy="64" rx="5.5" ry="9" fill="{B_}"/><ellipse cx="{sx_ * 41}" cy="64" rx="2.6" ry="5.4" fill="{DK_}" opacity=".5"/>')
            else:
                hd.append(f'<path d="M-24,12 C-12,4 8,3 22,8" fill="none" stroke="{HAIR_LT}" stroke-width="4" stroke-linecap="round" opacity=".8"/>')
                hd.append(f'<ellipse cx="-4" cy="64" rx="6.5" ry="10.5" fill="{B_}"/><ellipse cx="-3" cy="64" rx="3.2" ry="6.4" fill="{DK_}" opacity=".55"/>')
        fc = face_front(face, g) if P.view == 'F' else face_side(face, g)
        o.append('<g transform="translate(0,-92)">' + ''.join(hd[:1]) + ''.join(hd[1:]) + fc + '</g>')
    return o + far_overlay(P, S, NAVY, .22)

def spark(th=0, dy=0):
    return (f'<g class="spark" transform="rotate({n(-.8 * th)} 0 -86) translate(0,{-92 + dy}) translate(0,6) scale(1.4) translate(0,-6)"><path d="{M.FLAME_OUT}" fill="{MARIGOLD}"/>'
            f'<path d="{M.FLAME_IN}" fill="#FFE08A"/></g>')

# ------------------------------------------------------------------ figure assembly -------------------------------------
FIGS = {}

def figure(g, pose, act=None, face=None, tag='', hair='pony', bra=None):
    """returns the id of a registered <g> and its bbox"""
    fid = f"fig-{g}-{pose}{('-' + tag) if tag else ''}"
    if fid in FIGS: return fid, FIGS[fid]['bbox']
    HAIRSTYLE['v'] = hair
    BRA['v'] = bra or 'sport'
    if pose in ('relaxed', 'flex', 'lateral'):
        segs, joints, meta = front_pose(g, pose)
        gk = 'F'
    elif pose in BACK3D:
        segs, joints, meta = back3d_pose(g, pose)
        gk = back3d_view(pose)
    elif pose.startswith('back_'):
        segs, joints, meta = front_pose(g, pose[5:], 'B')
        gk = 'B'
    else:
        segs, joints, meta = side_pose(g, pose)
        gk = 'S'
    bb = bbox(segs)
    # the face on the front head would be hidden behind the pony tail's base; fine (pony is drawn before the head)
    opts = dict(act=act, face=face)
    cxm = (bb[0] + bb[2]) / 2
    floor_rx = max(110, (bb[2] - bb[0]) * (.5 if pose not in ('pushup', 'plank') else .5))
    lift = meta['lift']
    if meta.get('top'):     # seen from above: a soft shadow of the body (not the arms) on the floor below
        tb = bbox([P for P in segs if P.key in ('pelvis', 'chest', 'head', 'thigh', 'shin', 'foot')])
        o = [f'<ellipse cx="{n((tb[0] + tb[2]) / 2)}" cy="{n((tb[1] + tb[3]) / 2 + 16)}" rx="{n((tb[2] - tb[0]) * .52)}" ry="{n((tb[3] - tb[1]) * .5)}" fill="{NAVY}" opacity=".07"/>']
    else:
        o = [f'<ellipse cx="{n(cxm)}" cy="{FLOOR + 3}" rx="{n(floor_rx * (1 - lift / 200))}" ry="{n(11 * (1 - lift / 160))}" fill="{NAVY}" opacity="{.09 if not lift else .06}"/>']
    ns = (lambda v: f'{v:.3f}'.rstrip('0').rstrip('.')) if pose in BACK3D else n   # round 7 poses keep their foreshortening exact
    for P in segs:
        S = mk(P.g, P.view, P.skey, P.side)
        inner = p_sculpt(P, S, opts)
        if P.key == 'foot' and pose.startswith('run_'):      # ankle slider: CSS variable rotates the shoe about the ankle (local origin)
            inner = [f'<g style="transform:rotate(calc(var(--ank-{"f" if P.far else "n"},0) * 1deg))">'] + inner + ['</g>']
        if P.key == 'toes' and pose.startswith('run_'):      # the toe piece turns with the shoe, about the same ankle
            fa = [Q for Q in segs if Q.key == 'foot' and Q.far == P.far][0]
            ox, oy = R(-P.th, (fa.W[0] - P.W[0], fa.W[1] - P.W[1]))
            inner = [f'<g style="transform-origin:{n(ox)}px {n(oy)}px;transform:rotate(calc(var(--ank-{"f" if P.far else "n"},0) * 1deg))">'] + inner + ['</g>']
        if P.key == 'head' and hair != 'curly': inner = [spark(P.th)] + inner
        if P.key == 'curls': inner = inner + [spark(P.th, -8)]
        tf = f'translate({n(P.W[0])},{n(P.W[1])})' + (f' rotate({n(P.th)})' if abs(P.th) > 1e-6 else '') + \
             (f' scale({ns(P.sx)},{ns(P.sy)})' if (P.sx != 1 or P.sy != 1) else '')
        o.append(f'<g id="{fid}-{P.key}{P.side if P.side != "C" else ""}{"-far" if P.far else ""}" transform="{tf}">' + ''.join(inner) + '</g>')
    rg, seen = [], set()
    for a, b in joints:
        rg.append(f'<line x1="{n(a[0])}" y1="{n(a[1])}" x2="{n(b[0])}" y2="{n(b[1])}" stroke="{NAVY}" stroke-width="1.6" stroke-dasharray="4 3" opacity=".7"/>')
    for a, b in joints:
        for p in (a, b):
            k = (round(p[0]), round(p[1]))
            if k in seen: continue
            seen.add(k); rg.append(f'<circle cx="{n(p[0])}" cy="{n(p[1])}" r="5.5" fill="{MARIGOLD}" stroke="{NAVY}" stroke-width="1.8"/>')
    o.append('<g class="rig">' + ''.join(rg) + '</g>')
    FIGS[fid] = dict(svg=f'<g id="{fid}">' + ''.join(o) + '</g>', bbox=bb, segs=segs)
    return fid, bb

def head_only(g, view, face, hair='pony'):
    """standalone head (+pony) for face close-ups, centred on its pivot; returns <g> markup (neutral head coords, pivot at 0,0)"""
    segs = []
    P = Seg(g, view, 'head', 'C', (0, 0), 0)
    o = []
    if g == 'f' and hair == 'pony':
        Pp = Seg(g, view, 'pony', 'C', (30, -70) if view == 'F' else (-30, -68), 0)
        o += p_sculpt(Pp, mk(g, view, 'pony', 'C'), dict(face=face))
    o += ([spark()] if hair != 'curly' else []) + p_sculpt(P, mk(g, view, 'head', 'C'), dict(face=face))
    if g == 'f' and hair == 'curly':
        Pc = Seg(g, view, 'curls', 'C', (0, 0), 0)
        o += p_sculpt(Pc, mk(g, view, 'curls', 'C'), dict(face=face)) + [spark(0, -8)]
    return ''.join(o)

def all_defs():
    return ''.join(DEFS) + ''.join(MASKS) + ''.join(f['svg'] for f in FIGS.values())


# ------------------------------------------------------------------ activation sets -------------------------------------
NICE = dict(pec='Pectoralis major', delt='Deltoid', triceps='Triceps', biceps='Biceps', brach='Brachioradialis', flexor='Forearm flexors',
            abs='Rectus abdominis', oblique='Obliques', serratus='Serratus anterior', lat='Latissimus dorsi', trap='Trapezius',
            quad='Rectus femoris', vastus='Vastus lateralis', vmo='Vastus medialis', hams='Hamstrings', gastro='Gastrocnemius',
            soleus='Soleus', tibant='Tibialis anterior', glute='Gluteus maximus', hipflex='Hip flexors', adductor='Adductors',
            rhomb='Rhomboids', infra='Infraspinatus & teres minor', teres='Teres major', midtrap='Middle trapezius', lowtrap='Lower trapezius', thumbpad='Thenar', erector='Erector spinae', extensor='Forearm extensors')

ACTS = {
 'pushup': {'pec': 3, 'delt': 3, 'triceps': 3, 'serratus': 2, 'abs': 2, 'oblique': 1, 'quad': 1, 'vastus': 1, 'glute': 1, 'trap': 1, 'forearm': 0},
 'plank':  {'abs': 3, 'oblique': 3, 'serratus': 2, 'delt': 2, 'glute': 2, 'quad': 1, 'vastus': 1, 'pec': 1, 'trap': 1},
 'squat':  {'quad': 3, 'vastus': 3, 'vmo': 3, 'glute': 3, 'hams': 2, 'soleus': 2, 'gastro': 1, 'abs': 1, 'oblique': 1, 'tibant': 1},
 'calf':   {'gastro': 3, 'soleus': 3, 'tibant': 1, 'quad': 1, 'vastus': 1, 'abs': 1},
 'lateral': {'delt': 3, 'trap': 2, 'serratus': 1, 'abs': 1, 'oblique': 1, 'brach': 1, 'flexor': 1},
 'flex':   {'biceps': 3, 'brach': 2, 'delt': 2, 'flexor': 1, 'pec': 1, 'trap': 1, 'abs': 1, 'oblique': 1},
 'run_strike': {'quad@near': 3, 'vastus@near': 3, 'vmo@near': 3, 'tibant@near': 3, 'glute': 2, 'abs': 1, 'oblique': 1,
                'hams@far': 2, 'gastro@far': 1, 'triceps@near': 2, 'biceps@far': 2, 'delt@far': 2, 'lat@near': 1},
 'run_mid': {'soleus@near': 3, 'gastro@near': 2, 'glute': 3, 'quad@near': 2, 'vastus@near': 2, 'hams@near': 1, 'abs': 2, 'oblique': 2,
             'hipflex': 3, 'hams@far': 2, 'quad@far': 1, 'biceps@near': 1, 'delt@near': 1, 'triceps@far': 1},
 'run_off': {'glute': 3, 'gastro@near': 3, 'soleus@near': 3, 'quad@near': 2, 'vastus@near': 2, 'hipflex': 3, 'quad@far': 3, 'abs': 2,
             'oblique': 1, 'biceps@near': 2, 'delt@near': 2, 'triceps@far': 2, 'tibant@far': 1},
 'back_flex': {'lat': 3, 'trap': 3, 'midtrap': 3, 'lowtrap': 2, 'teres': 2, 'rhomb': 2, 'infra': 2, 'delt': 2, 'triceps': 2, 'erector': 1, 'oblique': 1, 'extensor': 1},
 'back_lateral': {'delt': 3, 'infra': 3, 'midtrap': 3, 'rhomb': 3, 'trap': 2, 'lowtrap': 2, 'teres': 2, 'triceps': 1, 'extensor': 1, 'erector': 1, 'glute': 1, 'hams': 1},
 'back_relaxed': {'glute': 3, 'hams': 3, 'erector': 3, 'trap': 2, 'midtrap': 2, 'lowtrap': 1, 'lat': 2, 'teres': 1, 'infra': 1, 'oblique': 1, 'gastro': 1, 'soleus': 1},
 'back_squat': {'glute': 3, 'hams': 2, 'adductor': 2, 'erector': 2, 'gastro': 1, 'soleus': 1, 'trap': 1, 'midtrap': 1, 'delt': 1},
 'front_squat': {'quad': 3, 'vastus': 3, 'vmo': 3, 'glute': 3, 'adductor': 2, 'abs': 1, 'oblique': 1, 'tibant': 1, 'delt': 1},
 'top_pushup': {'triceps': 3, 'delt': 2, 'serratus': 2, 'trap': 1, 'midtrap': 1, 'erector': 1, 'glute': 1},
 'top_plank': {'erector': 1, 'glute': 2, 'delt': 2, 'trap': 1, 'midtrap': 1, 'lowtrap': 1},
 'top_fly_high': {'delt': 3, 'infra': 3, 'midtrap': 3, 'rhomb': 3, 'teres': 2, 'lowtrap': 2, 'trap': 1, 'triceps': 1},
 'above_fly_low': {'pec': 3, 'delt': 2, 'biceps': 1, 'serratus': 1, 'abs': 1},
 'top_y_high': {'lowtrap': 3, 'midtrap': 2, 'delt': 2, 'infra': 2, 'trap': 1, 'rhomb': 1, 'erector': 1},
 'back_run_mid': {'glute': 3, 'hams@near': 2, 'gastro': 2, 'soleus': 2, 'erector': 1, 'delt': 1, 'triceps': 1},
 'run_fly': {'hams@near': 3, 'gastro@near': 1, 'glute': 2, 'hipflex': 3, 'quad@far': 3, 'vastus@far': 2, 'abs': 2, 'oblique': 1,
             'biceps@near': 2, 'delt@near': 2, 'triceps@far': 2, 'tibant@far': 1},
}

def act_fig(g, pose, face=None):
    return figure(g, pose, act=ACTS[pose], face=face, tag='act')

QUAD = ('quad', 'vastus', 'vmo')
LABEL = dict(NICE); LABEL.update(quad='Quadriceps', vastus='Quadriceps', vmo='Quadriceps')

def marker_pts(fid, act, min_gap=44):
    """numbered markers for the prime (3) and secondary (2) muscles, de-duplicated, spread so they never overlap"""
    segs = FIGS[fid]['segs']
    res, seen = [], set()
    for far_pass in (False, True):
        for P in segs:
            if P.far != far_pass: continue
            S = mk(P.g, P.view, P.skey, P.side)
            for nm, i in S['mus']:
                lv = act_level(P, nm, act)
                if lv < 2: continue
                key = (LABEL.get(nm, nm), lv)
                if key in seen: continue
                b = BB.get(i)
                if not b: continue
                x, y = R(P.th, (((b[0] + b[2]) / 2) * P.sx, ((b[1] + b[3]) / 2) * P.sy))
                res.append(dict(nm=nm, lv=lv, far=P.far, x=P.W[0] + x, y=P.W[1] + y, label=LABEL.get(nm, nm)))
                seen.add(key)
    res.sort(key=lambda r: (-r['lv'], r['far']))
    return res
