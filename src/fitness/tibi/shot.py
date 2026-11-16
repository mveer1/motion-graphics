import sys, chrome
from playwright.sync_api import sync_playwright
src,out=sys.argv[1],sys.argv[2]
w=int(sys.argv[3]) if len(sys.argv)>3 else 1500
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=chrome.EXE,args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':w,'height':900})
    pg.goto('file://'+src); pg.wait_for_timeout(500)
    pg.screenshot(path=out,full_page=True); b.close()
