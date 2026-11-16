import sys, os, tempfile; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chrome
LAB=os.path.join(tempfile.gettempdir(),'tibi_lab4.html')
import build2 as B, os
from playwright.sync_api import sync_playwright
# usage: lab4.py out.png "pose:hair:bra,pose:hair:bra" x0 y0 x1 y1 scale
out=sys.argv[1]; specs=sys.argv[2].split(',')
box=[float(v) for v in sys.argv[3:7]]; sc=float(sys.argv[7])
cells=[]
for sp in specs:
    p,h,b=sp.split(':'); fid,_=B.figure('f',p,tag=f'{h}{b}',hair=h,bra=b)
    w=box[2]-box[0]; hh=box[3]-box[1]
    cells.append(f'<svg viewBox="{box[0]} {box[1]} {w} {hh}" width="{w*sc}" height="{hh*sc}" style="background:#F5F3EF;margin:2px"><use href="#{fid}"/></svg>')
html=f'<!doctype html><style>body{{margin:0;background:#fff}}.rig{{display:none}}</style><svg width="0" height="0" style="position:absolute"><defs>{B.all_defs()}</defs></svg><div style="display:flex;flex-wrap:wrap">{"".join(cells)}</div>'
open(LAB,'w').write(html)
with sync_playwright() as pw:
    br=pw.chromium.launch(executable_path=chrome.EXE,args=['--no-sandbox'])
    pg=br.new_page(viewport={'width':1800,'height':900}); pg.goto('file://'+LAB); pg.wait_for_timeout(300)
    pg.screenshot(path=out,full_page=True); br.close()
