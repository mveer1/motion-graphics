import sys
import asyncio, hashlib
from playwright.async_api import async_playwright
import os, chrome
P=sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','site','tibi_cobalt_sculpt_v6.html')
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path=chrome.EXE,args=['--no-sandbox'])
        pg=await b.new_page(viewport={'width':1300,'height':900})
        errs=[]
        pg.on('console',lambda m: errs.append(m.text) if m.type in('error','warning') else None)
        pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.goto('file://'+P); await pg.wait_for_timeout(500)
        async def h(sel):
            el=await pg.query_selector(sel)
            return hashlib.md5(await el.screenshot()).hexdigest()[:8] if el else None
        # figure stage in hero/sec1
        stage=await pg.evaluate("(()=>{const e=document.querySelector('.stage,.sheet,#sec1,section');return e?e.className+'|'+e.id:null})()")
        print('stage',stage)
        sel='#s4'
        base=await h(sel); print('base',base)
        for lab,click in [('Female','button[data-show=f]'),('Male','button[data-show=m]'),('Both','button[data-show=both]'),
                          ('Relaxed','button[data-pose=relaxed]'),('Side','button[data-pose=side]'),('All','button[data-pose=all]')]:
            await pg.click(click); await pg.wait_for_timeout(200)
            print(lab,await h(sel))
        for cid in ('mkChk',):
            await pg.evaluate("document.querySelector('#s4').scrollIntoView()")
            before=await h(sel)
            await pg.click('#'+cid); await pg.wait_for_timeout(200)
            after=await h(sel)
            print(cid,'changed' if before!=after else 'NO CHANGE')
            await pg.click('#'+cid); await pg.wait_for_timeout(100)
        print('errs',errs)
        await b.close()
asyncio.run(main())
