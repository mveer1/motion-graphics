"""Export every Tibi figure as a STANDALONE svg (own <defs>, no external refs) and a transparent PNG.
usage: python3 export_assets.py OUTDIR            (default OUTDIR = assets/fitness/tibi in Motion Lab; PNGs need playwright + a Chrome/Chromium, see chrome.py)
OUTDIR/svg/figures/<gender>_<pose>[_<variant>].svg     OUTDIR/svg/heads/<gender>_head_<front|profile>_<face>.svg
OUTDIR/png/figures/...png (transparent, 2x)           OUTDIR/png/heads/...png
Run figures read the CSS custom properties --ank-n / --ank-f (degrees, default 0) to turn the shoe about the ankle."""
import sys, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chrome
import build2 as B

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'assets', 'fitness', 'tibi')
for d in ('svg/figures', 'svg/heads', 'png/figures', 'png/heads'):
    os.makedirs(f'{OUT}/{d}', exist_ok=True)

GN = {'m': 'male', 'f': 'female'}
# ---- build every figure that exists in the design --------------------------------------------------------------------
PLAIN = ['relaxed', 'flex', 'side', 'lateral', 'squat', 'calf', 'pushup', 'plank', 'run_strike', 'run_mid', 'run_off', 'run_fly',
         'back_relaxed', 'back_flex', 'back_lateral',
         # round 7: back-view squat and running, prone and supine poses seen from above
         'back_squat', 'back_run_strike', 'back_run_mid', 'back_run_off', 'back_run_fly',
         'top_pushup', 'top_pushup_bottom', 'top_plank', 'top_fly_low', 'top_fly_high', 'top_y_high', 'above_fly_high', 'above_fly_low']
ACT = ['pushup', 'plank', 'squat', 'calf', 'lateral', 'flex', 'run_strike', 'run_mid', 'run_off', 'run_fly', 'back_flex', 'back_lateral', 'back_relaxed',
       'back_squat', 'back_run_mid', 'top_pushup', 'top_plank', 'top_fly_high', 'top_y_high', 'above_fly_low']
jobs = []                                   # (fid, filename)
for g in 'mf':
    for p in PLAIN:
        fid, _ = B.figure(g, p); jobs.append((fid, f'{GN[g]}_{p}'))
    for p in ACT:
        fid, _ = B.act_fig(g, p); jobs.append((fid, f'{GN[g]}_{p}_activation'))
    for fc, nm in (('A', 'face_minimal'), ('C', 'face_ember_visor')):
        fid, _ = B.figure(g, 'relaxed', face=fc, tag='face' + fc); jobs.append((fid, f'{GN[g]}_relaxed_{nm}'))
for p in ('relaxed', 'flex', 'side', 'back_relaxed', 'back_flex'):
    fid, _ = B.figure('f', p, tag='push', bra='push'); jobs.append((fid, f'female_{p}_pushup_bra'))

# ---- closure of referenced defs ----------------------------------------------------------------------------------------
ELS = {}
for m in B.DEFS + B.MASKS:
    ELS[re.search(r'id="([^"]+)"', m).group(1)] = m

def closure(markup):
    need, todo = [], re.findall(r'href="#([^"]+)"|url\(#([^)]+)\)', markup)
    seen = set()
    stack = [a or b for a, b in todo]
    while stack:
        i = stack.pop()
        if i in seen or i not in ELS: continue
        seen.add(i); need.append(i)
        stack += [a or b for a, b in re.findall(r'href="#([^"]+)"|url\(#([^)]+)\)', ELS[i])]
    return ''.join(ELS[i] for i in sorted(need))

def wrap(markup, vb, bg=None):
    x, y, w, h = vb
    r = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{bg}"/>' if bg else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x:.0f} {y:.0f} {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}">'
            f'<style>.rig{{display:none}}</style><defs>{closure(markup)}</defs>{r}{markup}</svg>')

files = []
for fid, name in jobs:
    bb = B.FIGS[fid]['bbox']
    vb = (bb[0] - 40, bb[1] - 100, bb[2] - bb[0] + 80, B.FLOOR + 30 - (bb[1] - 100))
    svg = wrap(B.FIGS[fid]['svg'], vb)
    open(f'{OUT}/svg/figures/{name}.svg', 'w').write(svg); files.append((f'svg/figures/{name}.svg', f'png/figures/{name}.png', vb))

# ---- heads (front + profile, faceless + faces) -----------------------------------------------------------------------
for g in 'mf':
    for v, vn in (('F', 'front'), ('S', 'profile')):
        for fc, fn in ((None, 'faceless'), ('A', 'minimal'), ('C', 'ember_visor')):
            m = B.head_only(g, v, fc)
            vb = (-100, -160, 200, 184)
            open(f'{OUT}/svg/heads/{GN[g]}_head_{vn}_{fn}.svg', 'w').write(wrap(f'<g>{m}</g>', vb))
            files.append((f'svg/heads/{GN[g]}_head_{vn}_{fn}.svg', f'png/heads/{GN[g]}_head_{vn}_{fn}.png', vb))

# ---- PNGs (transparent, 2x) --------------------------------------------------------------------------------------------
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=chrome.EXE, args=['--no-sandbox'])
        pg = br.new_page(viewport={'width': 900, 'height': 1100}, device_scale_factor=2)
        for sv, png, vb in files:
            s = open(f'{OUT}/{sv}').read()
            k = 600 / vb[2] if 'heads' not in sv else 1.2
            pg.set_content(f'<body style="margin:0;background:transparent"><div id="c" style="display:inline-block;width:{vb[2] * k:.0f}px;height:{vb[3] * k:.0f}px">'
                           + s.replace(f'width="{vb[2]:.0f}" height="{vb[3]:.0f}"', 'width="100%" height="100%"', 1) + '</div></body>')
            pg.locator('#c').screenshot(path=f'{OUT}/{png}', omit_background=True)
        br.close()
except Exception as e:
    print('PNG export skipped:', e)
print(len(files), 'assets written to', OUT)
