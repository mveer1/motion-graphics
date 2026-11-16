import sys, os, tempfile; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chrome
LAB=os.path.join(tempfile.gettempdir(),'tibi_lab.html')
import build2 as B
# usage: lab.py out.png pose gender[,gender] x0 y0 x1 y1 [scale]   (world crop box in figure coords)
from playwright.sync_api import sync_playwright
out=sys.argv[1]; poses=sys.argv[2].split(','); gs=sys.argv[3].split(',')
box=[float(v) for v in sys.argv[4:8]]; sc=float(sys.argv[8]) if len(sys.argv)>8 else 2
face=None; cells=[]
for g in gs:
    for p in poses:
        import os; hr=os.environ.get('HAIR','pony'); fid,bb=B.figure(g,p,tag=hr,hair=hr)
        w=box[2]-box[0]; h=box[3]-box[1]
        cells.append(f'<svg viewBox="{box[0]} {box[1]} {w} {h}" width="{w*sc}" height="{h*sc}" style="background:#F5F3EF;margin:2px"><use href="#{fid}"/></svg>')
html=f'<!doctype html><style>body{{margin:0;background:#fff}}.rig{{display:none}}</style><svg width="0" height="0" style="position:absolute"><defs>{B.all_defs()}</defs></svg><div style="display:flex;flex-wrap:wrap">{"".join(cells)}</div>'
open(LAB,'w').write(html)
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=chrome.EXE,args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':1600,'height':900}); pg.goto('file://'+LAB); pg.wait_for_timeout(300)
    pg.screenshot(path=out,full_page=True); b.close()
