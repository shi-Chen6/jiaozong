import asyncio, os
from playwright.async_api import async_playwright
URL = 'file:///' + os.path.abspath('心理学刷题.html').replace('\\', '/')
TARGETS = [(24, 0, 'c24s1'), (24, 1, 'c24s2'), (25, 0, 'c25s1')]

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for cn, sec, tag in TARGETS:
            pg = await b.new_page(viewport={'width': 430, 'height': 932}, device_scale_factor=2)
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            await pg.goto(URL); await pg.wait_for_timeout(600)
            await pg.evaluate('(a)=>openGuide(a[0],a[1])', [cn, sec])
            await pg.wait_for_timeout(700)
            info = await pg.evaluate("""()=>{
                const ims=[...document.querySelectorAll('.gimg img')];
                return {n:ims.length, dims:ims.map(i=>[i.naturalWidth,i.naturalHeight,Math.round(i.getBoundingClientRect().width)]),
                        caps:[...document.querySelectorAll('.gimgcap')].map(c=>c.textContent.slice(0,28))};
            }""")
            print(tag, info, 'errs', errs or '无', flush=True)
            total = await pg.evaluate('()=>document.body.scrollHeight')
            y = 0; i = 0
            while y < total and i < 12:
                await pg.evaluate('(yy)=>window.scrollTo(0,yy)', y)
                await pg.wait_for_timeout(150)
                await pg.screenshot(path='_work/shots4/%s_seg%d.png' % (tag, i))
                y += 932; i += 1
            await pg.close()
        await b.close()
asyncio.run(run())
