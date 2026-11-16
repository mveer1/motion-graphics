import re, sys, asyncio
from playwright.async_api import async_playwright
import os, chrome
P=sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','site','tibi_cobalt_sculpt_v6.html')
s=open(P,encoding='utf-8').read()
ids=re.findall(r'\bid="([^"]+)"',s)
from collections import Counter
dup=[k for k,v in Counter(ids).items() if v>1]
idset=set(ids)
refs=set(re.findall(r'href="#([^"]+)"',s))|set(re.findall(r'url\(#([^)]+)\)',s))
missing=sorted(r for r in refs if r not in idset)
ext=re.findall(r'(?:src|href)="(?!#|data:)([^"]+)"',s)
ext+=re.findall(r'url\((?!#|data:)[^)]*\)',s)
print('ids',len(ids),'dup',dup[:5],'missing',missing[:5],'external',ext[:5])
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path=chrome.EXE,args=['--no-sandbox'])
        for w in (390,820,1500):
            pg=await b.new_page(viewport={'width':w,'height':900})
            errs=[]
            pg.on('console',lambda m,errs=errs: errs.append(m.text) if m.type in('error','warning') else None)
            pg.on('pageerror',lambda e,errs=errs: errs.append(str(e)))
            await pg.goto('file://'+P); await pg.wait_for_timeout(600)
            sw=await pg.evaluate('document.documentElement.scrollWidth')
            print(w,'scrollWidth',sw,'errs',errs[:3])
            if w==1500:
                # list controls
                ctrls=await pg.evaluate('''()=>[...document.querySelectorAll('[data-pose],[data-show],[data-spark],[data-rig],[data-nums],button,input[type=checkbox],select')].slice(0,40).map(e=>(e.tagName+' '+(e.id||'')+' '+(e.className||'')+' '+(e.textContent||'').trim().slice(0,20)+' '+JSON.stringify(e.dataset)))''')
                for c in ctrls: print(' ',c)
            await pg.close()
        await b.close()
asyncio.run(main())
