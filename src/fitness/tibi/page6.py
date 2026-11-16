import sys, os, re, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# Motion Lab: default output is assets/fitness/tibi/site (the handover bundle wrote ../site)
OUTDIR = os.environ.get('TIBI_OUT', os.path.join(HERE, '..', '..', '..', 'assets', 'fitness', 'tibi', 'site'))
os.makedirs(OUTDIR, exist_ok=True)
import build2 as B
import build_v1 as V1
import rig as M, rig_f as F

GN = {'m': 'Male', 'f': 'Female'}
FLOOR = B.FLOOR

# ------------------------------------------------------------------ build every figure once ---------------------------------
for g in 'mf':
    for p in ('relaxed', 'flex', 'side'): B.figure(g, p)
ACT_POSES = ['pushup', 'plank', 'squat', 'calf', 'lateral', 'flex', 'run_strike', 'run_mid', 'run_off', 'run_fly']
for g in 'mf':
    for p in ACT_POSES: B.act_fig(g, p)
BACK_POSES = ['back_relaxed', 'back_flex', 'back_lateral']
for g in 'mf':
    for p in BACK_POSES: B.figure(g, p)
    for p in BACK_POSES: B.act_fig(g, p)
for g in 'mf':
    for fc in 'AC': B.figure(g, 'relaxed', face=fc, tag='face' + fc)
for pz in ('relaxed', 'flex', 'side'):
    B.figure('f', pz, tag='push', bra='push')
heads_defs = ''
for g in 'mf':
    for v in 'FS':
        for fc in 'AC':
            heads_defs += f'<g id="head-{g}-{v}-{fc}">{B.head_only(g, v, fc)}</g>'
        heads_defs += f'<g id="head-{g}-{v}-0">{B.head_only(g, v, None)}</g>'

# v1 (before) figures, ids prefixed so they never collide
old_figs = ''
for p in ('relaxed', 'flex'):
    old_figs += V1.figure('sculpt', p)
old = ''.join(V1.DEFS) + ''.join(V1.MASKS) + old_figs
old = re.sub(r'(id="|href="#|url\(#)([A-Za-z0-9_\-]+)', lambda m: m.group(1) + 'v1_' + m.group(2), old)

V3DEFS = open(os.path.join(HERE, 'v3_defs.txt')).read()
GLOBAL = f'<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>{B.all_defs()}{heads_defs}{old}{V3DEFS}</defs></svg>'

# ------------------------------------------------------------------ helpers ----------------------------------------------------
def bb(fid): return B.FIGS[fid]['bbox']

def union_vb(fids, padx=34, top=80, bottom=34):
    x0 = min(bb(f)[0] for f in fids); x1 = max(bb(f)[2] for f in fids); y0 = min(bb(f)[1] for f in fids)
    return (x0 - padx, y0 - top, x1 - x0 + 2 * padx, FLOOR + bottom - (y0 - top))

def vbs(v): return f'{v[0]:.0f} {v[1]:.0f} {v[2]:.0f} {v[3]:.0f}'

def seg_of(fid, key, side=None):
    for P in B.FIGS[fid]['segs']:
        if P.key == key and (side is None or P.side == side) and not P.far: return P

def heads_tall(g):
    P = seg_of(f'fig-{g}-relaxed', 'head')
    return (FLOOR - (P.W[1] - 93)) / 102

def svg(fid, v, extra='', label=''):
    return f'<svg viewBox="{vbs(v)}" role="img" aria-label="{label}"><use href="#{fid}"/>{extra}</svg>'

def marker_svg(markers, vb, box):
    """numbered badges for the PRIME movers, parked in the margin with a thin leader line to a dot on the muscle,
    so they never hide the muscle planes"""
    ms = [dict(m) for m in markers if m['lv'] == 3]
    r = max(13, vb[3] * .031)
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2
    gap = 2 * r + 8
    for m in ms: m['px'], m['py'] = m['x'], m['y']
    if (x1 - x0) > 1.15 * (y1 - y0):
        by = y0 - r * 2.0 - 16
        prev = None
        for m in sorted(ms, key=lambda m: m['px']):
            m['bx'], m['by'] = m['px'], by
            if prev is not None and m['bx'] - prev < gap: m['bx'] = prev + gap
            prev = m['bx']
    else:
        for left, xx in ((True, x0 - r * 1.8 - 12), (False, x1 + r * 1.8 + 12)):
            grp = sorted([m for m in ms if (m['px'] < cx) == left], key=lambda m: m['py'])
            prev = None
            for m in grp:
                m['bx'], m['by'] = xx, m['py']
                if prev is not None and m['by'] - prev < gap: m['by'] = prev + gap
                prev = m['by']
    col = B.CORAL
    o = '<g class="mk">'
    order = {id(m): k for k, m in enumerate(ms, 1)}
    for m in ms:
        o += (f'<line x1="{m["bx"]:.1f}" y1="{m["by"]:.1f}" x2="{m["px"]:.1f}" y2="{m["py"]:.1f}" stroke="{col}" stroke-width="{r * .13:.1f}" stroke-linecap="round" opacity=".9"/>'
              f'<circle cx="{m["px"]:.1f}" cy="{m["py"]:.1f}" r="{r * .24:.1f}" fill="#fff" stroke="{col}" stroke-width="{r * .1:.1f}"/>')
    for m in ms:
        o += (f'<circle cx="{m["bx"]:.1f}" cy="{m["by"]:.1f}" r="{r:.1f}" fill="#fff" stroke="{col}" stroke-width="{r * .24:.1f}"/>'
              f'<text x="{m["bx"]:.1f}" y="{m["by"] + r * .04:.1f}" font-size="{r * 1.12:.1f}" font-weight="800" fill="{B.NAVY}" text-anchor="middle" dominant-baseline="central" '
              f'font-family="ui-sans-serif,system-ui,sans-serif">{order[id(m)]}</text>')
    return o + '</g>'

# ------------------------------------------------------------------ 01 shoulder -----------------------------------------------
def sec1():
    vb = union_vb(['fig-m-flex', 'fig-f-flex'])
    capy = seg_of('fig-m-flex', 'cap', 'L').W[1]
    zvb = (CX - 290, capy - 95, 580, 250)
    z = lambda fid: svg(fid, zvb)
    f = lambda fid: svg(fid, vb)
    cmp_ = f'''<div class="cmp">
  <div class="bad"><h4>Before · v1 (arm separates from the body)</h4><div class="stagebg">{f('v1_fig-sculpt-flex')}</div></div>
  <div class="good g-m"><h4>After · male</h4><div class="stagebg">{f('fig-m-flex')}</div></div>
  <div class="good g-f"><h4>After · female</h4><div class="stagebg">{f('fig-f-flex')}</div></div></div>
<div class="zoom">
  <div class="g-all"><div class="stagebg">{z('v1_fig-sculpt-flex')}</div><figcaption>Before, shoulders close up: the arm root is a round-ended tube lying on the pec corner, with a notch above it.</figcaption></div>
  <div class="g-m"><div class="stagebg">{z('fig-m-flex')}</div><figcaption>After, male: deltoid dome sits over the arm root and continues the trapezius slope.</figcaption></div>
  <div class="g-f"><div class="stagebg">{z('fig-f-flex')}</div><figcaption>After, female: same construction, narrower and lighter.</figcaption></div></div>'''
    txt = '''<div class="two" style="margin-top:18px">
  <div class="panel"><h4>What was wrong</h4>
    <p>In the double-biceps pose the upper arm turns 86°, and the deltoid was part of the arm, so it turned with it and ended up as a lens along the top of the arm. That left nothing over the joint: the round end of the arm lay on the pec corner as a visible edge, and a gap opened between the trapezius and the arm.</p></div>
  <div class="panel"><h4>What changed</h4><ul>
    <li><b>Shoulder cap.</b> A new deltoid dome lives on the torso side of the joint and is drawn over the arm root, so the arm tucks under it. Its top edge continues the trapezius line into the top of the arm.</li>
    <li><b>Lat wing.</b> A lat wing fills the armpit and widens the V under the raised arm, so the torso flows out into the arm instead of stopping at the ribs. It was reworked in rounds two and three (see below).</li>
    <li><b>Rig.</b> Both are separate groups pivoted at the shoulder (<code class="k">cap</code>, <code class="k">flare</code>), so the cap can turn at half the arm's angle when you animate relaxed to flex. They are also used by the lateral raise below.</li></ul></div></div>'''
    lat_vb = lambda fid: (CX - 270, seg_of(fid, 'cap', 'L').W[1] - 70, 540, 300)
    lat = ba_grid([('ba', [
        ('v3_fig-f-flex', lat_vb('fig-f-flex'), 'v3: the wing reaches out to about 124 units from the centre line.', 'Before · v3 · female', 'g-f'),
        ('fig-f-flex', lat_vb('fig-f-flex'), 'v4: the outer edge is pulled in 4 to 5 units; still one silhouette with the waist.', 'After · female', 'g-f')])], 2)
    lat_txt = '''<div class="panel" style="margin-top:14px"><h4>Lats, round 3 (female only)</h4><ul>
    <li><b>What changed.</b> Her lat wing is slightly smaller: the outer edge is pulled in about 5 units under the arm and about 3 at mid-rib, and the lat plane inside it was trimmed to match. The waist end is unchanged, so it still grows out of the waist outline.</li>
    <li><b>Male.</b> Unchanged from v3.</li>
    <li><b>Rig.</b> Still a separate <code class="k">flare</code> group per side, pivoted at the shoulder.</li></ul></div>'''
    return f'<section class="sec" id="s1"><h2><i>1</i> Shoulder join and lats</h2><p class="sub">The double-biceps shoulder, rebuilt. Same pose, same light, before and after, then the round-three lat trim for her.</p>{cmp_}{txt}<div class="stripLabel g-f" style="margin-top:22px">Round 3 · her lats, v3 against v4</div><div class="g-f">{lat}{lat_txt}</div></section>'

CX = B.CX

def ba_cell(fid, vb, cap, cls='', tag=''):
    return f'<figure class="{cls}"><div class="stagebg">{svg(fid, vb)}</div><figcaption>{cap}</figcaption></figure>'

def crop_vb(fid, key, dx0, dy0, w, h, side=None):
    P = seg_of(fid, key, side)
    return (P.W[0] + dx0, P.W[1] + dy0, w, h)

def ba_grid(rows, n=4):
    """rows: list of (cls, [(fid, vb, caption, label)])  ->  grid with a Before / After header per cell"""
    out = ''
    for cls, cells in rows:
        out += f'<div class="bag" style="--n:{n}">' + ''.join(
            f'<div class="{cls} {c}"><h4 class="{"bad" if lab.startswith("Before") else "good"}">{lab}</h4>{ba_cell(fid, vb, cap)}</div>' for fid, vb, cap, lab, c in cells) + '</div>'
    return out

# ------------------------------------------------------------------ 02 female ------------------------------------------------
def proportions():
    out = {}
    for g in 'mf':
        FR = B.DATA[g][0]
        sh = 2 * max(abs(p[0]) for p in FR['chest']['base'][0])
        waist = 2 * min(abs(p[0]) for p in FR['pelvis']['base'][0] if 270 <= p[1] <= 320)
        hip = 2 * max(abs(p[0]) for p in [c for c in FR['pelvis']['cloth'] if c[0] == 'shorts'][0][1])
        out[g] = dict(sh=sh, waist=waist, hip=hip, heads=heads_tall(g))
    return out

def sec2():
    P = proportions()
    vbs_ = {p: union_vb([f'fig-m-{p}', f'fig-f-{p}']) for p in ('relaxed', 'flex', 'side')}
    lab = dict(relaxed='Front · relaxed', flex='Front · double biceps', side='Side')
    cards = ''
    desc = dict(
        m='The approved figure: broad shoulders, V-taper, three-row six-pack, quad sweep and calf diamond, short charcoal shorts with a slim marigold waistband.',
        f='The same rig, topology and pivots, with different volumes: narrower shoulders, a defined waist, wider hips and glutes, smaller muscle planes and a quieter six-pack. A charcoal sports top with a straight marigold hem and a high ponytail with a marigold tie make her unmistakable even faceless. A padded push-up alternative to the sports top is in section 7.')
    sw = dict(m=[('Cobalt body', '#2F56E0'), ('Light plane', '#4F75EC'), ('Shade', '#2244B8'), ('Shorts', '#22243A'), ('Waistband', '#FFB224'), ('Trainers', '#FBFBFA')],
              f=[('Cobalt body', '#2F56E0'), ('Hair', '#1C3AA3'), ('Sports top', '#22243A'), ('Cup plane', '#33375C'), ('Trim / tie', '#FFB224'), ('Trainers', '#FBFBFA')])
    for i, g in enumerate('mf', 1):
        stage = ''.join(
            f'<figure class="fig {p}" style="flex:{vbs_[p][2] / vbs_[p][3]:.3f} 1 0">{svg(f"fig-{g}-{p}", vbs_[p], label=GN[g] + " " + lab[p])}<figcaption>{lab[p]}</figcaption></figure>' for p in ('relaxed', 'flex', 'side'))
        sws = ''.join(f'<li><span style="background:{h}"></span><b>{n}</b></li>' for n, h in sw[g])
        cards += f'''<article class="card g-{g}"><header><span class="num">{i}</span><div><h3>{GN[g]} Tibi · Cobalt Sculpt</h3><p class="tag">{P[g]['heads']:.2f} heads tall · faceless · no outline</p></div></header>
<div class="stage">{stage}</div><div class="info"><p>{desc[g]}</p><ul class="sw">{sws}</ul></div></article>'''
    m, f = P['m'], P['f']
    tbl = f'''<table class="spec"><tr><th>Measure (rig units, head = 100)</th><th>Male</th><th>Female</th></tr>
<tr><td>Height in heads</td><td>{m['heads']:.2f}</td><td>{f['heads']:.2f}</td></tr>
<tr><td>Shoulder width</td><td>{m['sh']:.0f}</td><td>{f['sh']:.0f}</td></tr>
<tr><td>Waist width</td><td>{m['waist']:.0f}</td><td>{f['waist']:.0f}</td></tr>
<tr><td>Hip width (shorts)</td><td>{m['hip']:.0f}</td><td>{f['hip']:.0f}</td></tr>
<tr><td>Shoulder : waist</td><td>{m['sh'] / m['waist']:.2f} : 1</td><td>{f['sh'] / f['waist']:.2f} : 1</td></tr>
<tr><td>Waist : hip</td><td>{m['waist'] / m['hip']:.2f}</td><td>{f['waist'] / f['hip']:.2f}</td></tr>
<tr><td>Leg length</td><td>100%</td><td>{B.LS['f'] * 100:.1f}%</td></tr></table>'''
    notes = f'''<div class="two" style="margin-top:18px"><div class="panel"><h4>Side by side</h4>{tbl}</div>
<div class="panel"><h4>How she differs from him</h4><ul>
<li><b>Silhouette.</b> Shoulders are {100 - f['sh'] / m['sh'] * 100:.0f}% narrower, the waist drops to {f['waist'] / f['sh'] * 100:.0f}% of shoulder width (male {m['waist'] / m['sh'] * 100:.0f}%) and the hips flare, so she is athletic, not a re-skinned male.</li>
<li><b>Muscle.</b> Every plane is shrunk about 10% and the arms and calves are about 15% slimmer. The abs, serratus and quads are still defined so she can carry every activation view below. Rounds 3 and 4 trimmed her lat wing, shortened her shorts and softened her glutes; round 5 widened her hips.</li>
<li><b>Wardrobe.</b> I treated "no shirt" as a male rule and gave her a top. It is one charcoal group (<code class="k">bra</code>, <code class="k">bust</code>, <code class="k">strap</code>), so it is trivial to remove or recolour. Round 4 slimmed the straps and trimmed the top; the padded push-up is compared with it in section 7. The bralette was dropped.</li>
<li><b>Ponytail.</b> A separate <code class="k">pony</code> segment pivoted on the head, so it can swing in animation. In the front view it falls over the viewer's right shoulder.</li></ul></div></div>'''
    return f'<section class="sec" id="s2"><h2><i>2</i> Female Tibi</h2><p class="sub">Same segments, pivots and light as the male, so any animation, activation or outfit change carries across. Use the Pose and Show controls above.</p><div class="grid2">{cards}</div>{notes}</section>'

# ------------------------------------------------------------------ 03 wear --------------------------------------------------
def sec3():
    py = seg_of('fig-m-relaxed', 'pelvis').W[1]
    wvb = (CX - 135, py - 110, 270, 205)
    w = lambda fid: svg(fid, wvb)
    v1b = M  # (new) data; old numbers hard-coded from the v1 design
    th_old, th_new = 20, 9
    full = union_vb(['fig-m-relaxed', 'fig-f-relaxed'])
    full1 = (100, 0, 400, 900)
    thumbs = (f'<svg viewBox="{vbs(full)}"><use href="#v1_fig-sculpt-relaxed"/></svg>'
              f'<svg viewBox="{vbs(full)}"><use href="#fig-m-relaxed"/></svg><svg viewBox="{vbs(full)}"><use href="#fig-f-relaxed"/></svg>')
    sv = lambda fid: crop_vb(fid, 'pelvis', -105, -52, 210, 175)
    sidev = lambda fid: crop_vb(fid, 'pelvis', -120, -52, 210, 175)
    glutes = ba_grid([('ba', [
        ('v3_fig-f-relaxed', sv('fig-f-relaxed'), 'v3: the hem sits about 9 units lower on the thigh.', 'Before · v3 · front', 'g-f'),
        ('fig-f-relaxed', sv('fig-f-relaxed'), 'v4: very slightly shorter, same flare and trim.', 'After · front', 'g-f'),
        ('v3_fig-f-side', sidev('fig-f-side'), 'v3: the glute projects to 75 units behind the hip line.', 'Before · v3 · side', 'g-f'),
        ('fig-f-side', sidev('fig-f-side'), 'v4: softened to 71, still a little fuller than his 67.', 'After · side', 'g-f')])])
    glute_txt = '''<div class="panel" style="margin-top:14px"><h4>Shorts and glutes, round 3 (female only)</h4><ul>
    <li><b>Shorts length.</b> The hem is raised about 9 units, about a tenth of the shorts' length, in front and side view. Trim, flare, colour and the waistband are unchanged.</li>
    <li><b>Glutes.</b> The projection is pulled back from 75 to about 71 units behind the hip line, so she is still a little rounder than him but no longer exaggerated. The shape is the same smooth arc with a clean fold into the thigh.</li>
    <li><b>Overlays.</b> The translucent glute and hip-flexor overlays used in the squat, push-up and run were re-cut to follow the new shape and hem.</li>
    <li><b>Male.</b> Unchanged from v3.</li></ul></div>'''
    return f'''<section class="sec" id="s3"><h2><i>3</i> Shorts and glutes</h2><p class="sub">The marigold band was reading as a thick belt that was also wider than the waist above it. It is now a slim stripe, and the shorts start at the waist width and widen downwards.</p>
<div class="wear">
  <div><h4>Before · v1</h4><div class="stagebg">{w('v1_fig-sculpt-relaxed')}</div></div>
  <div class="g-m"><h4>After · male</h4><div class="stagebg">{w('fig-m-relaxed')}</div></div>
  <div class="g-f"><h4>After · female</h4><div class="stagebg">{w('fig-f-relaxed')}</div></div>
  <div class="panel"><h4 style="text-transform:none;letter-spacing:0;font-size:16px;color:var(--navy)">What changed</h4><ul>
    <li>Waistband thickness <b>{th_old} → {th_new} units</b> (about {100 - th_new / th_old * 100:.0f}% thinner), same marigold.</li>
    <li>The shorts' top edge now matches the pelvis width, so no blue corners poke out beside the band, and they flare gently to the hem.</li>
    <li>Hem trim, shorts colour and trainers are unchanged. (Her shorts were shortened in round 3, below.)</li>
    <li>Her shorts sit a little tighter on the hip; her top has a matching marigold hem line.</li></ul></div>
</div>
<div class="stripLabel">Small-portrait test: v1, male, female (the stripe must still read)</div>
<div class="thumbs">{thumbs}</div>
<div class="stripLabel g-f" style="margin-top:22px">Round 3 · her shorts and glutes, v3 against v4</div><div class="g-f">{glutes}{glute_txt}</div></section>'''

# ------------------------------------------------------------------ 04/05 activations -----------------------------------------
LBL_ORDER = ('quad', 'vastus', 'vmo')

def legend_lists(markers, act):
    prime = [m for m in markers if m['lv'] == 3]
    sec = [m for m in markers if m['lv'] == 2]
    both = {}
    for m in prime + sec: both.setdefault(m['label'], set()).add(m['far'])
    def lab(m):
        return m['label'] + (' · far side' if (m['far'] and len(both[m['label']]) > 1) else (' · near side' if len(both[m['label']]) > 1 else ''))
    stab, seen = [], set()
    for k, v in act.items():
        nm = k.split('@')[0]
        l = B.LABEL.get(nm, nm)
        if v == 1 and l not in seen and nm in B.NICE and l not in both: seen.add(l); stab.append(l)
    html = '<div class="lists"><div><h4>Prime movers</h4><ol>' + (''.join(f'<li><span class="n">{i}</span>{lab(m)}</li>' for i, m in enumerate(prime, 1)) or '<li>–</li>') + '</ol></div>'
    html += '<div><h4>Secondary</h4><ul>' + (''.join(f'<li><span class="n s"></span>{lab(m)}</li>' for m in sec) or '<li>–</li>') + '</ul></div></div>'
    if stab: html += '<div><h4 style="margin:2px 0 4px;font-size:11.5px;text-transform:uppercase;letter-spacing:.09em;color:var(--mute);font-weight:700">Stabilising</h4><div class="chips">' + ''.join(f'<span>{s_}</span>' for s_ in stab) + '</div></div>'
    return html

def act_pair(pose, vbx=None):
    figs = {g: f'fig-{g}-{pose}-act' for g in 'mf'}
    v = vbx or union_vb(list(figs.values()), padx=100, top=120)
    out, mk0 = '', None
    for g in 'mf':
        mk = B.marker_pts(figs[g], B.ACTS[pose])
        if g == 'm': mk0 = mk
        out += f'<figure class="fig g-{g}" style="--ar:{v[2] / v[3]:.3f}">{svg(figs[g], v, marker_svg(mk, v, bb(figs[g])), GN[g] + " " + pose)}<figcaption>{GN[g]}</figcaption></figure>'
    return out, mk0

ACARDS = [
 ('pushup', 'Push-up', 'side view · horizontal push', True,
  'The chest, front deltoids and triceps drive the press. The serratus protracts the shoulder blades and the abs hold the plank, with the glutes and quads keeping the line straight.'),
 ('plank', 'Forearm plank', 'side view · isometric hold', True,
  'Nothing moves, so the activation is all stabilisation: abs and obliques stop the hips sagging, the shoulders and serratus hold the torso up, and the glutes and quads keep the legs rigid.'),
 ('squat', 'Bodyweight squat', 'side view · legs', False,
  'Quadriceps and glutes extend the hip and knee out of the hole; hamstrings and soleus control the descent while the core braces the trunk. The glute is drawn as a translucent overlay on the shorts because it sits under them.'),
 ('calf', 'Calf raise', 'side view · lower leg', False,
  'Gastrocnemius and soleus plantar-flex the ankle to lift the heel; tibialis anterior and quads steady the leg. It is the cleanest example of one muscle group doing one job.'),
 ('lateral', 'Lateral raise', 'front view · shoulders', False,
  'The side deltoid lifts the arm, helped by the upper trapezius as the arm passes shoulder height. It uses the new shoulder cap, which is why that fix matters beyond the biceps pose.'),
 ('flex', 'Double biceps', 'front view · arms', False,
  'Biceps are the prime movers, with the brachioradialis and deltoids holding the position. Pecs, abs and obliques are braced, shown as stabilisers.'),
]

def sec4():
    cards = ''
    for i, (pose, title, tag, wide, why) in enumerate(ACARDS, 1):
        pair, mk0 = act_pair(pose)
        cards += f'''<article class="card {'wide' if wide else 'std'}"><header><span class="num">{i}</span><div><h3>{title}</h3><p class="tag">{tag}</p></div></header>
<div class="stage"><div class="pair" style="width:100%">{pair}</div></div>
<div class="info"><p>{why}</p>{legend_lists(mk0, B.ACTS[pose])}</div></article>'''
    # wide cards go first, in their own full-width rows
    cards_html = cards
    lg = f'''<div class="legend"><b>How to read it</b>
<span><i style="background:{B.CORAL}"></i>Prime mover: coral plane with a soft halo</span>
<span><i style="background:{B.MARIGOLD}"></i>Secondary / assisting: marigold</span>
<span><i style="background:#8CAEFA"></i>Stabiliser: pale cobalt</span>
<span><i style="background:{B.LT_}"></i>Idle: the normal cobalt plane</span>
<span>Numbered badges mark the prime movers and match the list under each figure (toggle them in the bar).</span></div>'''
    return f'''<section class="sec" id="s4"><h2><i>4</i> Activations</h2><p class="sub">The same Cobalt Sculpt muscle planes, recoloured by role. No new shapes are needed for the front and side views: an activation is just a fill on the existing muscle, so a film can keyframe it per beat. Muscles that sit under the shorts (glutes, hip flexors) appear as translucent overlays. The muscles of the back are lit in the back views in section 8.</p>
{lg}<div class="agrid">{cards_html}</div></section>'''

RUN = [
 ('run_strike', 'Contact', 'Landing on the near foot',
  'Quads and tibialis anterior brake the landing, the glutes steady the pelvis, and the trailing hamstring starts folding the other leg. The arms swing opposite to the legs.'),
 ('run_mid', 'Mid-stance', 'Weight over the foot',
  'Soleus and calf carry the load, glutes and quads hold the hip and knee, and the hip flexors start bringing the other leg through.'),
 ('run_off', 'Toe-off', 'Pushing away',
  'Glutes, gastrocnemius and soleus extend the hip and ankle to drive forward while the hip flexors and rectus femoris pull the swing knee up.'),
 ('run_fly', 'Flight', 'Both feet off the ground',
  'Hamstrings fold the trailing leg, the hip flexors and rectus femoris reach the lead knee forward, and the arms keep the rhythm. The abs hold the trunk.'),
]

def sec5():
    strips = ''
    for g in 'mf':
        figs = [f'fig-{g}-{p[0]}-act' for p in RUN]
        v = union_vb(figs, padx=100, top=100)
        cards = ''
        for i, (pose, title, tag, why) in enumerate(RUN, 1):
            fid = f'fig-{g}-{pose}-act'
            mk = B.marker_pts(fid, B.ACTS[pose])
            cards += f'''<article class="card"><header><span class="num">{i}</span><div><h3>{title}</h3><p class="tag">{tag}</p></div></header>
<div class="stage">{svg(fid, v, marker_svg(mk, v, bb(fid)), GN[g] + ' ' + title)}</div><div class="info"><p>{why}</p>{legend_lists(mk, B.ACTS[pose])}</div></article>'''
        strips += f'<div class="g-{g}"><div class="stripLabel">{GN[g]} Tibi · one stride, four key poses</div><div class="strip">{cards}</div></div>'
    groups = [('Quadriceps', ('quad', 'vastus', 'vmo')), ('Hamstrings', ('hams',)), ('Glutes', ('glute',)), ('Calf', ('gastro', 'soleus')),
              ('Tibialis anterior', ('tibant',)), ('Hip flexors', ('hipflex',)), ('Core', ('abs', 'oblique')), ('Arm swing', ('biceps', 'triceps', 'delt'))]
    def lvl(pose, names):
        return max([v for k, v in B.ACTS[pose].items() if k.split('@')[0] in names] or [0])
    rows = ''.join('<tr><td>' + gname + '</td>' + ''.join(f'<td><span class="dot p{lvl(p[0], names)}"></span></td>' for p in RUN) + '</tr>' for gname, names in groups)
    mat = f'''<div class="matwrap"><table class="mat"><tr><th>Muscle group (highest role in each phase, either leg)</th>{''.join(f'<th>{p[1]}</th>' for p in RUN)}</tr>{rows}</table></div>
<p class="sub" style="margin-top:8px"><span class="dot p3"></span> prime &nbsp; <span class="dot p2"></span> secondary &nbsp; <span class="dot p1"></span> stabiliser &nbsp; <span class="dot p0"></span> not a driver in this phase. Simplified for teaching; real EMG timing overlaps more than four snapshots can show.</p>'''
    ctl = '''<div class="ankctl" id="ankctl"><b>Ankle angle</b>
<label>Near foot <input type="range" id="ankN" min="-30" max="40" value="0" step="1"><output id="ankNo">0°</output></label>
<label>Far foot <input type="range" id="ankF" min="-30" max="40" value="0" step="1"><output id="ankFo">0°</output></label>
<label class="chk"><input type="checkbox" id="ankLink" checked> Move both together</label>
<label class="chk"><input type="checkbox" id="ankAnim"> Animate</label>
<button type="button" id="ankReset">Reset</button>
<span class="hint">Minus lifts the toes (dorsiflexion), plus points them (plantar flexion). It is added to each phase's own foot angle, and the shoe turns about the ankle joint.</span></div>'''
    return f'''<section class="sec" id="s5"><h2><i>5</i> Running activations <span class="pill">ankle slider</span></h2><p class="sub">A four-pose gait on the same rig (generic forward kinematics, so each pose is just a set of joint angles). The near leg is shown with the full activation; the far side is dimmed as usual but still lit when it is the driver. The flame stays upright in the air. New in round 5: you can change the ankle angle of every running figure below.</p>
{ctl}{strips}{mat}</section>'''

# ------------------------------------------------------------------ 06 faces ------------------------------------------------
FACES = [
 ('0', 'Faceless', 'DEFAULT · used on every figure in this document', 'The approved Cobalt Sculpt head: a smooth hood with a slightly lighter face plane and no features. The ponytail, the spark and the body language carry the character.',
  ['Nothing to animate wrong: the pose does all the acting', 'Reads at any size and keeps him and her equally neutral', 'Lets the narrator, not the character, carry emotion'],
  ['No eye line, so a character looking at something needs a posture cue', 'No mouth, so narration cannot be lip-synced']),
 ('A', 'Minimal', 'SECONDARY OPTION', 'Two oval eyes with a catch-light and a small smile on the existing face plane. Nothing else changes.',
  ['Cheapest rig: two eyes and one mouth, and the head stays the approved hood', 'Reads at 64 px and stays closest to the faceless character', 'Her lash flick is the only gender cue on the face'],
  ['Little range: effort and fatigue need brows added', 'Smooth hood plus dots can feel toy-like']),
 ('C', 'Ember visor', 'SECONDARY OPTION', 'A dark visor plane with marigold glowing eyes and a tiny smile, echoing the spark.',
  ['Strongest brand tie (marigold on cobalt) and the best contrast, so it reads at the smallest size', 'Eyes can pulse, squint or glow brighter for effort', 'Lowest chance of an off-model face'],
  ['Closest to the old mask-face, so it risks reading as a robot again', 'A mouth is only a hint, so it needs a lip-sync set later']),
]

def sec6():
    vh = (-100, -160, 200, 184)
    full = union_vb([f'fig-{g}-relaxed' for g in 'mf'] + [f'fig-{g}-relaxed-face{fc}' for g in 'mf' for fc in 'AC'], padx=30)
    cards = ''
    for i, (fc, name, tagline, desc, pros, cons) in enumerate(FACES, 1):
        hs = ''.join(f'<figure class="g-{g}"><svg viewBox="{vbs(vh)}"><use href="#head-{g}-{v}-{fc}"/></svg><figcaption>{GN[g]} · {"front" if v == "F" else "profile"}</figcaption></figure>' for v in 'FS' for g in 'mf')
        fid = lambda g: f'fig-{g}-relaxed' if fc == '0' else f'fig-{g}-relaxed-face{fc}'
        fr = ''.join(f'<figure class="g-{g}">{svg(fid(g), full, label=GN[g] + " face " + name)}</figure>' for g in 'mf')
        badge = '<span class="pill ok">default</span>' if fc == '0' else '<span class="pill">secondary</span>'
        cards += f'''<article class="card{' dflt' if fc == '0' else ''}"><header><span class="num">{'·' if fc == '0' else fc}</span><div><h3>{name} {badge}</h3><p class="tag">{tagline.lower().capitalize() if fc != '0' else tagline.capitalize()}</p></div></header>
<div class="heads">{hs}</div><div class="fullrow">{fr}</div>
<div class="info"><p>{desc}</p><div class="pc"><div><h4>Good for animation</h4><ul class="pros">{''.join(f'<li>{x}</li>' for x in pros)}</ul></div><div><h4>Costs</h4><ul class="cons">{''.join(f'<li>{x}</li>' for x in cons)}</ul></div></div></div></article>'''
    return f'''<section class="sec" id="s6"><h2><i>6</i> Faces</h2><p class="sub">Faceless is the default for the whole character. Minimal and Ember visor are kept as secondary options (Soft features is dropped). Each face is one small group inside the head segment (<code class="k">translate(0,-92)</code> in head coordinates), so it can be swapped or removed without touching the body.</p>
<div class="fgrid">{cards}</div></section>'''

def sec7():
    vbs_ = {q: union_vb([f'fig-f-{q}', f'fig-f-{q}-push']) for q in ('relaxed', 'flex', 'side')}
    lab = dict(relaxed='Front · relaxed', flex='Front · double biceps', side='Side')
    def card(num, name, tag, tg, desc, sws):
        stage = ''.join(f'<figure class="fig {q}" style="flex:{vbs_[q][2] / vbs_[q][3]:.3f} 1 0">{svg(f"fig-f-{q}{tg}", vbs_[q], label=name + " " + lab[q])}<figcaption>{lab[q]}</figcaption></figure>' for q in ('relaxed', 'flex', 'side'))
        sw = ''.join(f'<li><span style="background:{h}"></span><b>{n}</b></li>' for n, h in sws)
        return f'''<article class="card"><header><span class="num">{num}</span><div><h3>{name}</h3><p class="tag">{tag}</p></div></header><div class="stage">{stage}</div><div class="info"><p>{desc}</p><ul class="sw">{sw}</ul></div></article>'''
    sw = [('Cobalt body', '#2F56E0'), ('Bra', '#22243A'), ('Cup plane', '#33375C'), ('Hem', '#FFB224')]
    cA = card('A', 'Sports top', 'DEFAULT · used in every other section', '', 'The straight-edged sports top with slim straps. Round 5 made it about 5 units longer, so it covers a little more of the ribs. From behind it is a racerback (section 8).', sw)
    cB = card('B', 'Padded push-up', 'SECONDARY OPTION · shown only in this section', '-push', 'Moulded balconette cups with a plunge, slim straps and a slim band. The padding bulges slightly past the chest line in profile, which gives the clearest feminine silhouette at small sizes.', sw)
    cr = lambda fid: crop_vb(fid, 'chest', -115, -128, 230, 180)
    row1 = ba_grid([('ba', [
        ('v3_fig-f-relaxed', cr('fig-f-relaxed'), 'v3 sports top: wide straps, a deeper body.', 'Before · v3 · front', 'g-f'),
        ('fig-f-relaxed', cr('fig-f-relaxed'), 'A: default. Same flat top edge, slim straps, and 5 units longer than round four.', 'A · sports top (default) · front', 'g-f'),
        ('fig-f-relaxed-push', cr('fig-f-relaxed-push'), 'B: secondary. Balconette cups, plunge, slim straps and band.', 'B · push-up (secondary) · front', 'g-f')])], 3)
    row2 = ba_grid([('ba', [
        ('v3_fig-f-side', cr('fig-f-side'), 'v3 sports top in profile: wide strap.', 'Before · v3 · side', 'g-f'),
        ('fig-f-side', cr('fig-f-side'), 'A: default, in profile, with the longer body.', 'A · sports top (default) · side', 'g-f'),
        ('fig-f-side-push', cr('fig-f-side-push'), 'B: secondary. The padding rises and projects further.', 'B · push-up (secondary) · side', 'g-f')])], 3)
    return f'''<section class="sec g-f" id="s7"><h2><i>7</i> Bra options <span class="pill">new</span></h2><p class="sub">The sports top is the default and is used on every figure in this document. The padded push-up is the secondary option and is shown only here. Round 5: the sports top is about 5 units longer vertically.</p>
<div class="grid2">{cA}{cB}</div>
<div class="stripLabel" style="margin-top:22px">Close-up · front: v3 sports top, the default sports top, and the push-up</div>{row1}
<div class="stripLabel" style="margin-top:18px">Close-up · side</div>{row2}
<div class="panel" style="margin-top:14px"><h4>How they are built</h4><ul>
<li>Each bra is a variant of her chest segment (<code class="k">chest_sport</code> and <code class="k">chest_push</code>) with the same muscle planes underneath. The bra, the lighter cup planes and the straps are separate charcoal shapes, so a bra can be swapped or recoloured without touching the body.</li>
<li>Both end on the same marigold hem line as before, so the abs, the lower ribs and the waist read the same whichever you choose.</li>
<li><b>Sports top:</b> the simplest shape and the most robust at small sizes. <b>Push-up:</b> the clearest feminine silhouette, with padding that projects in profile, but it covers more of the chest.</li>
<li>In the activation poses the chest planes are only partly visible under either bra, which is the same trade-off the sports top had.</li></ul></div></section>'''

BACKCARDS = [
 ('back_flex', 'Rear double biceps', 'back view · lats and traps', True,
  'Seen from behind, the lats spread into a wide V and the trapezius fills the upper back. The rear deltoids and infraspinatus show around the shoulder blades, and the triceps horseshoe appears on each raised arm. The erector spinae and obliques hold the waist.'),
 ('back_lateral', 'Reverse fly (rear-delt raise)', 'back view · upper back', False,
  'The rear deltoid and infraspinatus (with teres) swing the arms back and out, while the middle and lower trapezius pull the shoulder blades together. The triceps and forearm extensors keep the elbows straight.'),
 ('back_relaxed', 'Deadlift lockout', 'back view · posterior chain', True,
  'Standing tall at the top of a deadlift: glutes and hamstrings drive the hips through, the erector spinae hold the spine straight, and the trapezius and lats keep the shoulders back. Calves and obliques stabilise.'),
]

def sec8():
    turn = {}
    for g in 'mf':
        vb = union_vb([f'fig-{g}-flex', f'fig-{g}-back_flex', f'fig-{g}-relaxed', f'fig-{g}-back_relaxed'], padx=26)
        ids = [('fig-%s-relaxed' % g, 'Front · relaxed'), ('fig-%s-back_relaxed' % g, 'Back · relaxed'),
               ('fig-%s-flex' % g, 'Front · double biceps'), ('fig-%s-back_flex' % g, 'Back · double biceps')]
        fw = [bb(f)[2] - bb(f)[0] + 52 for f, _ in ids]
        figs = ''.join(f'<figure class="bfig" style="flex:{w / (vb[3]):.3f} 1 0">{svg(f, (bb(f)[0] - 26, vb[1], bb(f)[2] - bb(f)[0] + 52, vb[3]), label=GN[g] + " " + lab)}<figcaption>{lab}</figcaption></figure>' for (f, lab), w in zip(ids, fw))
        sw = {'m': [('Cobalt body', '#2F56E0'), ('Light plane', '#4F75EC'), ('Shade', '#2244B8'), ('Shorts', '#22243A'), ('Seat highlight', '#2D3158'), ('Waistband', '#FFB224')],
              'f': [('Cobalt body', '#2F56E0'), ('Hair', '#1C3AA3'), ('Sports top', '#22243A'), ('Seat highlight', '#2D3158'), ('Trim / tie', '#FFB224'), ('Heel tab', '#B9C2DE')]}[g]
        sws = ''.join(f'<li><span style="background:{h}"></span><b>{n}</b></li>' for n, h in sw)
        cap = {'m': 'Back of the approved figure: trapezius kite, infraspinatus and teres around the shoulder blade, the lat V, erector spinae down the spine, a seamed seat in the shorts, hamstrings, the calf diamond and the heel of the trainer.',
               'f': 'Her back matches the front: the same narrower shoulders, waist and wider hips, a racerback sports top (the padded push-up has straight straps and a clasp), and the ponytail hanging in front of the head and swept over her right shoulder.'}[g]
        turn[g] = f'<article class="card g-{g}"><header><span class="num">{ "1" if g == "m" else "2"}</span><div><h3>{GN[g]} Tibi · turnaround</h3><p class="tag">Front and back, relaxed and double biceps · same scale, same light</p></div></header><div class="bstage">{figs}</div><div class="info"><p>{cap}</p><ul class="sw">{sws}</ul></div></article>'
    cards = ''
    for i_, (pose, title, tag, wide, why) in enumerate(BACKCARDS, 1):
        pair, mk0 = act_pair(pose)
        cards += f'''<article class="card {'wide' if wide else 'std'}"><header><span class="num">{i_}</span><div><h3>{title}</h3><p class="tag">{tag}</p></div></header>
<div class="stage"><div class="pair" style="width:100%">{pair}</div></div>
<div class="info"><p>{why}</p>{legend_lists(mk0, B.ACTS[pose])}</div></article>'''
    built = '''<div class="two" style="margin-top:18px"><div class="panel"><h4>How the back is built</h4><ul>
<li><b>Same skeleton.</b> The back view reuses the front silhouettes, pivots and joint topology, so any pose, activation or animation that works from the front works from behind. Only the interior (muscle planes, lines, cloth) is new, in <code class="k">rig_back</code>.</li>
<li><b>New muscle planes.</b> Trapezius (kite), infraspinatus and teres, lats, erector spinae, hamstrings (two heads), gastrocnemius (two heads) and a Y of back straps; the shoulder cap is the rear deltoid and the raised arm shows the triceps horseshoe.</li>
<li><b>Shorts from behind.</b> A centre seam and two raised seat planes, with the glute activation drawn as a translucent overlay on them, as in the side view.</li>
<li><b>Her hair.</b> The ponytail hangs in front of the head from behind and swings to the viewer's right, so the spine and left trapezius stay readable.</li>
<li><b>Trainers.</b> A heel view with a pull tab and a stitch line. No logo.</li></ul></div>
<div class="panel"><h4>Back activations</h4><ul>
<li>The three cards use the same role colours as sections 4 and 5. Rear double biceps lights the lats and trapezius; the reverse fly lights the rear deltoid and infraspinatus; the deadlift lockout lights the posterior chain.</li>
<li>The rhomboids sit under the trapezius, so they are not drawn on their own; the trapezius plane stands in for them.</li>
<li>Back views exist for the relaxed, double-biceps and arms-out poses. A running or squatting pose from behind would reuse the same data and is a small step.</li></ul></div></div>'''
    return f'''<section class="sec" id="s8"><h2><i>8</i> Back views <span class="pill">new</span></h2><p class="sub">The same two figures from behind. These are the views that were missing, so the lats, trapezius, glutes, hamstrings and calves can now be lit.</p>
<div class="turn">{turn['m']}{turn['f']}</div>
<div class="stripLabel" style="margin-top:22px">Back activations · prime movers numbered, same role colours</div><div class="agrid">{cards}</div>{built}</section>'''

def sec9():
    return '''<section class="sec" id="s9"><h2><i>9</i> Still imperfect</h2><p class="sub">Things I know are not done, so you can weigh them before choosing a direction.</p>
<div class="two"><div class="panel"><h4>Drawing</h4><ul>
<li>Hands: the front hand now has four separate fingers and a thumb, but there are no finger joints. The fist and the side-view hand are still simple shapes.</li>
<li>The far limbs in side and running poses are mirrored copies, dimmed on purpose to read as farther away. They are not separate drawings.</li>
<li>Bra straps are straight, rigid strips on every figure. The racerback straps are straight too.</li>
<li>The ankle slider turns the whole shoe as one piece. Past about 35° the foot looks rigid because the sole does not bend at the toes and the heel does not rise.</li>
<li>Back views: no running or squatting pose yet, no face (there is none to see), and the rhomboids are not drawn separately.</li></ul></div>
<div class="panel"><h4>Choices to confirm</h4><ul>
<li><b>Back-view poses:</b> are relaxed, double biceps and arms-out enough, or do you want back running and squat poses too?</li>
<li><b>Faces:</b> faceless is the default. If you want Minimal or Ember visor, a mouth-shape set for narration comes next.</li>
<li><b>Seat highlight:</b> the shorts show two raised seat planes from behind. If it reads as too much, removing the two seat shapes is a two-line change in the back data.</li>
<li><b>Activation colours:</b> coral for prime, marigold for secondary, pale cobalt for stabilisers. Easy to change.</li></ul></div></div></section>'''

ROUND5 = '''<section class="sec round2" id="r5"><h2>Round five <span class="pill ok">what changed since v5</span></h2>
<div class="r2grid">
<a href="#s7"><b>Sports bra is the default</b><span>The push-up is the secondary option. The sports top is about 5 units longer vertically.</span></a>
<a href="#s6"><b>Faceless is the default</b><span>Minimal and Ember visor are the secondary options. Soft features is dropped.</span></a>
<a href="#s8"><b>Back views</b><span>Male and female, relaxed and double biceps, plus three back activations.</span></a>
<a href="#s5"><b>Ankle slider</b><span>Move the near and far ankle angle of every running figure, or animate it.</span></a>
<a href="#s2"><b>Her hips</b><span>Shorts about 8% wider (width 140 to 151), so the waist-to-hip ratio drops from 0.67 to 0.62.</span></a>
<a href="#s9"><b>Drawing gaps</b><span>Smoother neck-to-shoulder slope, wider ankle into the shoe, knee, elbow and ankle caps, and separate fingers on the front hand.</span></a></div>
<p class="sub" style="margin:10px 0 0">Everything else is unchanged from v5. The sports bra, the faces and the hips apply to every figure and every section.</p></section>'''

BODY = ROUND5 + sec1() + sec2() + sec3() + sec4() + sec5() + sec6() + sec7() + sec8() + sec9()
html = open(os.path.join(HERE, 'template6.html')).read().replace('%%GLOBAL%%', GLOBAL).replace('%%BODY%%', BODY)
open(os.path.join(OUTDIR, 'tibi_cobalt_sculpt_v6.html'), 'w').write(html)
print('written', len(html) // 1024, 'KB', {g: round(heads_tall(g), 2) for g in 'mf'})
