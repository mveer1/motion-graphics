"""Export the Cobalt Sculpt Tibi shapes, skeleton and poses to the studio runtime.

    python3 export_kit.py [OUT.js] [--check]

Default OUT is src/studio/kits/fitness/sculpt-data.js (generated, never edit by hand). The
runtime painter and rig binding live in src/studio/kits/fitness/sculpt.js; this file only moves
data across: every segment's shapes in local (pivot = origin) coordinates exactly as build2.mk()
registers them, the joint offsets, the handover's named poses converted to the rig's joint
conventions (the same ids and signs as the classic Tibi in tibi.js), faces, colours and the
activation tables. Run through `python scripts/fitness.py sculpt` (writes) or
`python scripts/fitness.py sculpt --check` (fails when the file is stale).
"""
import json
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build2 as B  # noqa: E402
import rig as M  # noqa: E402
import rig_ext as X  # noqa: E402
import rig_f as RF  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
DEFAULT_OUT = os.path.join(ROOT, 'src', 'studio', 'kits', 'fitness', 'sculpt-data.js')
VERSION = '2.1.0'
# rig units per Cobalt Sculpt unit: a standing figure (782 units, sole to crown) becomes about
# 422 rig units, the classic Tibi's height, so scale guidance and exercise anchors carry over.
U = 0.54

LIMB_F = ['thigh', 'shin', 'foot', 'upperArm', 'upperArm_flex', 'upperArm_nd', 'forearm', 'hand', 'fist', 'cap', 'flare']
TORSO_F = ['head', 'neck', 'pelvis']
SIDE_KEYS = ['head', 'neck', 'pelvis', 'thigh', 'shin', 'foot', 'toes', 'upperArm', 'forearm', 'hand', 'grip']
VIEWS = {'F': 'front', 'S': 'side', 'B': 'back'}


def r1(v):
    return round(v, 2)


def chest_keys(g):
    return ['chest'] if g == 'm' else ['chest_sport', 'chest_push']


def seg_keys(g, view):
    if view == 'S':
        keys = [(k, 'C') for k in SIDE_KEYS + chest_keys(g)]
    else:
        keys = [(k, s) for k in LIMB_F for s in ('L', 'R')] + [(k, 'C') for k in TORSO_F + chest_keys(g)]
    if g == 'f':
        keys.append(('pony', 'C'))
    return keys


def export_segments():
    paths, segs = {}, {}

    def P(i):
        if i not in paths:
            x0, y0, x1, y1 = B.BB.get(i, (0, 0, 40, 40))
            paths[i] = [B.REG[i], r1(min(x1 - x0, y1 - y0)), r1((x0 + x1) / 2), r1((y0 + y1) / 2)]
        return i

    for g in ('m', 'f'):
        for view in ('F', 'S', 'B'):
            for key, side in seg_keys(g, view):
                S = B.mk(g, view, key, side)
                segs[f'{g}{view}_{key}_{side}'] = {
                    'b': P(S['base']),
                    'mus': [[nm, P(i)] for nm, i in S['mus']],
                    'lines': [[nm, P(i)] for nm, i in S['lines']],
                    'cloth': [[nm, P(i)] for nm, i in S['cloth']],
                    'hem': P(S['hem']) if S['hem'] else None,
                    'sh': [P(i) for nm, i in S['sh']],
                }
    return paths, segs


# ------------------------------------------------------------------ skeleton (Cobalt units)
def skeleton(g):
    SK, ls = B.SKS[g][0], B.LS[g]
    sub = lambda a, b: (a[0] - b[0], a[1] - b[1])  # noqa: E731
    front = {
        'hip': [SK['hip'][0], SK['hip'][1] - 330],
        'knee': [SK['knee'][0] - SK['hip'][0], (SK['knee'][1] - SK['hip'][1]) * ls],
        'ankle': [SK['ankle'][0] - SK['knee'][0], (SK['ankle'][1] - SK['knee'][1]) * ls],
        'spine': [0, -64], 'neck': [0, -118], 'head': [0, -56],
        'shoulder': [SK['shoulder'][0], SK['shoulder'][1] - 266],
        'elbow': list(sub(SK['elbow'], SK['shoulder'])),
        'wrist': list(sub(SK['wrist'], SK['elbow'])),
        'pony': [30, -70], 'ponyBack': [8, -76],
    }
    DS = B.DATA[g][1]
    side = {
        'hip': [0, 58], 'knee': [0, 178 * ls], 'ankle': [-2, 166 * ls],
        'toe': list(sub(DS['toes']['piv'], DS['foot']['piv'])),
        'spine': [0, -64], 'neck': [0, -118], 'head': [0, -56],
        'shoulder': [2, -102], 'elbow': [-2, 134], 'wrist': [0, 106],
        'pony': [-30, -68],
    }
    rnd = lambda d: {k: [r1(v[0]), r1(v[1])] for k, v in d.items()}  # noqa: E731
    # build2.figure() writes segment scales through n() (one decimal), so the art actually drawn
    # uses scale(1, 1) for the female legs (0.965 rounds to 1) and 1.1 for hands (1.15): the leg
    # factor only moves the joints. Mirror what is drawn, not the unrounded intent.
    return {'front': rnd(front), 'side': rnd(side), 'legScale': ls,
            'artLegScale': float(B.n(ls)), 'handScale': float(B.n(1.15))}


# ------------------------------------------------------------------ poses
def settle_dy(segs, joints, contacts, lift):
    """the vertical slide build2.settle() applies, without mutating the segments"""
    low = max(y for P in segs if P.key in contacts for (x, y) in B.seg_world_pts(P))
    return B.FLOOR - lift - low


def side_pose_angles(g, name):
    """(spec, dy) for a handover side pose, plank/push-up solved exactly as build2.side_pose()"""
    if name in ('plank', 'pushup'):
        def err(b):
            segs, _ = B.side_fk(g, B.plank_spec(b, name))
            lowf = max(y for P in segs if P.key in ('foot', 'toes') for x, y in B.seg_world_pts(P))
            lowh = max(y for P in segs if P.key == 'hand' and not P.far for x, y in B.seg_world_pts(P))
            return lowh - lowf
        lo_b, hi_b = 64.0, 86.0
        for _ in range(40):
            mid = (lo_b + hi_b) / 2
            if err(mid) > 0:
                hi_b = mid
            else:
                lo_b = mid
        spec = B.plank_spec((lo_b + hi_b) / 2, name)
        spec['contacts'] = ('foot', 'hand')
    else:
        spec = B.SIDE_POSES[name]
    segs, joints = B.side_fk(g, spec)
    dy = settle_dy(segs, joints, spec.get('contacts', ('foot',)), spec.get('lift', 0))
    pel = spec.get('pel', (B.CX, 330))
    tp, tc, tn, th = (spec.get(k, 0) for k in ('tp', 'tc', 'tn', 'th'))
    j = {'pelvis': tp, 'spine': tc - tp, 'chest': 0, 'neck': tn - tc, 'head': th - tn}
    # rig signs (classic Tibi, side view): hip -1, knee +1, ankle -1, shoulder -1, elbow -1, wrist -1;
    # near limbs are R, far limbs L. build2 angles are absolute and clockwise-positive.
    for side, part in (('R', 'near'), ('L', 'far')):
        L, A = spec[part]['leg'], spec[part]['arm']
        j['hip' + side] = -(L['t'] - tp)
        j['knee' + side] = L['s'] - L['t']
        j['ankle' + side] = -(L['f'] - L['s'])
        j['toe' + side] = -(L.get('o', L['f']) - L['f'])
        j['shoulder' + side] = -(A['u'] - tc)
        j['elbow' + side] = -(A['fa'] - A['u'])
        j['wrist' + side] = -(A['ha'] - A['fa'])
    root = (pel[0] - B.CX, pel[1] + dy - B.FLOOR)
    return j, root, spec.get('lift', 0)


FRONT_ARMS = dict(relaxed=(8, 10, 9), flex=(86, 190, 192), lateral=(80, 86, 84))


def front_pose_angles(g, kind, view):
    a0, a1, a2 = FRONT_ARMS[kind]
    tt = 1.5 if kind == 'relaxed' else 3.5
    # viewer-left limbs rotate +angle, viewer-right -angle; the rig joint sign does the mirroring
    j = {'pelvis': 0, 'spine': 0, 'chest': 0, 'neck': 0, 'head': 0}
    for side in ('R', 'L'):
        j['hip' + side] = tt
        j['knee' + side] = tt
        j['ankle' + side] = 0
        j['shoulder' + side] = a0
        j['elbow' + side] = a1 - a0
        j['wrist' + side] = a2 - a1
    segs, joints, _ = B.front_pose(g, kind, view)
    pel = [P for P in segs if P.key == 'pelvis'][0].W
    return j, (pel[0] - B.CX, pel[1] - B.FLOOR), 0


def rnd_pose(j, root, lift):
    return {'j': {k: r1(v) for k, v in j.items()}, 'root': [r1(root[0]), r1(root[1])], 'lift': lift}


def export_poses():
    out = {}
    for g in ('m', 'f'):
        side = {}
        for name in ('stand', 'run_strike', 'run_mid', 'run_off', 'run_fly', 'squat', 'calf', 'pushup', 'plank'):
            side[name.replace('_', '-')] = rnd_pose(*side_pose_angles(g, name))
        front = {k: rnd_pose(*front_pose_angles(g, k, 'F')) for k in FRONT_ARMS}
        back = {k: rnd_pose(*front_pose_angles(g, k, 'B')) for k in FRONT_ARMS}
        # round 7: depth poses from behind and from above (build2.BACK3D), with per-joint foreshortening f
        top, above = {}, {}
        for name, spec in B.BACK3D.items():
            rec = {'j': {k: r1(v) for k, v in spec['j'].items()}, 'f': {k: r1(v) for k, v in spec.get('f', {}).items()},
                   'lift': spec.get('lift', 0), 'rot': spec.get('rot', 0), 'grip': bool(spec.get('grip'))}
            if name.startswith('above_'):
                rec['root'] = [0, 0]
                above[name[6:].replace('_', '-')] = rec
            elif spec.get('order') == 'top':
                rec['root'] = [0, 0]
                top[name[4:].replace('_', '-')] = rec
            else:
                _, _, meta = B.back3d_pose(g, name)
                pel = [P for P in B.back3d_pose(g, name)[0] if P.key == 'pelvis'][0].W
                rec['root'] = [r1(pel[0] - B.CX), r1(pel[1] - B.FLOOR)]
                back[name[5:].replace('_', '-')] = rec
        out[g] = {'side': side, 'front': front, 'back': back, 'top': top, 'above': above}
    return out


def contacts():
    """floor contact points per gender, in ankle/wrist local Cobalt units (heel, toe, palm)"""
    out = {}
    for g in ('m', 'f'):
        S = B.mk(g, 'S', 'foot', 'C')
        pts = S['pts'] + (S['sole'] or [])
        low = max(p[1] for p in pts)
        heel = min([p for p in pts if p[1] >= low - 2.5], key=lambda p: p[0])
        T = B.mk(g, 'S', 'toes', 'C')                  # the toe tip lives on the toe segment (pivot = the ball)
        tp = T['pts'] + (T['sole'] or [])
        tlow = max(p[1] for p in tp)
        toe = max([p for p in tp if p[1] >= tlow - 2.5], key=lambda p: p[0])
        F = B.mk(g, 'F', 'foot', 'L')
        fl = max(p[1] for p in F['pts'])
        H = B.mk(g, 'S', 'hand', 'C')['pts']
        gs, gf = X.GRIP_SIDE, X.GRIP_FRONT
        hs, hf = B.DATA[g][1]['grip']['piv'], B.DATA[g][0]['fist']['piv']
        if g == 'f':                                    # follow the female hand morph
            gs, gf = RF.ax(0, .85)(*gs), RF.ax(-101, .85, 14)(*gf)
        out[g] = {'heel': [r1(heel[0]), r1(low)], 'toe': [r1(toe[0]), r1(tlow)], 'gripSide': [r1(gs[0] - hs[0]), r1(gs[1] - hs[1])],
                  'gripFront': [r1(gf[0] - hf[0]), r1(gf[1] - hf[1])],
                  'frontSole': [0, r1(fl)], 'hand': [[r1(p[0]), r1(p[1])] for p in H[::max(1, len(H) // 10)]]}
    return out


# ------------------------------------------------------------------ faces, palette, activation
def elements(markup):
    root = ET.fromstring(f'<g xmlns="http://www.w3.org/2000/svg">{markup}</g>')
    out = []
    for el in root:
        tag = el.tag.split('}')[-1]
        out.append([tag, {k: v for k, v in el.attrib.items()}])
    return out


def faces():
    out = {}
    for g in ('m', 'f'):
        for style, name in (('A', 'minimal'), ('C', 'ember')):
            out[f'{g}_{name}'] = {'front': elements(B.face_front(style, g)), 'side': elements(B.face_side(style, g))}
    return out


def payload():
    paths, segs = export_segments()
    return {
        'version': VERSION,
        'unit': U,
        'cx': B.CX, 'floor': B.FLOOR,
        'light': [B.LX, B.LY],
        'colors': {
            'body': B.B_, 'light': B.LT_, 'shade': B.DK_, 'navy': B.NAVY, 'marigold': B.MARIGOLD, 'glow': '#FFE08A',
            'charcoal': B.CHAR, 'hair': B.HAIR, 'hairLight': B.HAIR_LT, 'hairShade': B.HAIR_DK,
            'face': '#3F66E8', 'visor': '#1B338F', 'visorShade': '#10206A',
            'shoe': '#FBFBFA', 'shoeDetail': '#B9C2DE', 'shoeShade': '#CFD4E6',
            'bust': '#33375C', 'bustShade': '#15172B', 'seat': '#2D3158', 'seatShade': '#14162C', 'seatLight': '#4A4F80',
            'clasp': '#454A7C', 'seam': '#10122A',
        },
        'levels': {str(k): v for k, v in B.ALVL.items()},
        'ghost': list(B.GHOST),
        'names': B.LABEL,
        'acts': {k.replace('_', '-'): v for k, v in B.ACTS.items()},
        'flame': [M.FLAME_OUT, M.FLAME_IN],
        'faces': faces(),
        'skeleton': {g: skeleton(g) for g in ('m', 'f')},
        'poses': export_poses(),
        'contacts': contacts(),
        'segments': segs,
        'paths': paths,
    }


def render() -> str:
    body = json.dumps(payload(), separators=(',', ':'), sort_keys=True)
    return ('/* GENERATED by src/fitness/tibi/export_kit.py from the Cobalt Sculpt generator '
            '(src/fitness/tibi/). Do not edit: change the generator and run `python scripts/fitness.py sculpt`. */\n'
            "(function (global) {\n  'use strict';\n"
            "  var Studio = global.Studio || (global.Studio = {});\n"
            "  var F = (Studio.kit = Studio.kit || {}).fitness = (Studio.kit.fitness || {});\n"
            f"  F.sculptData = {body};\n"
            "})(typeof window !== 'undefined' ? window : this);\n")


def main(argv):
    check = '--check' in argv
    args = [a for a in argv if a != '--check']
    out = args[0] if args else DEFAULT_OUT
    text = render()
    if check:
        cur = open(out, encoding='utf-8').read() if os.path.exists(out) else ''
        if cur != text:
            print(f'{os.path.relpath(out, ROOT)} is stale; run `python scripts/fitness.py sculpt`.')
            return 1
        print(f'{os.path.relpath(out, ROOT)} is current.')
        return 0
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print(f'Wrote {os.path.relpath(out, ROOT)} ({len(text) // 1024} KB)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
