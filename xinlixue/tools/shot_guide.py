# -*- coding: utf-8 -*-
"""给先导卡拍图，检查长表与多块节的排版。

输出：_work/shots4/<章>_s<节>_<宽>.png
"""
import asyncio
import os

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'file:///' + os.path.join(ROOT, '心理学刷题.html').replace('\\', '/')
SHOT = os.path.join(ROOT, '_work', 'shots4')
os.makedirs(SHOT, exist_ok=True)

TARGETS = [(10, 0), (10, 1), (10, 2), (11, 0), (11, 1), (11, 2)]


async def run(width, height):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': width, 'height': height},
                              device_scale_factor=2)
        errs = []
        pg.on('pageerror', lambda e: errs.append('pageerror:' + str(e)))
        pg.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        await pg.goto(URL)
        await pg.wait_for_timeout(500)

        for cn, sec in TARGETS:
            await pg.evaluate('(a)=>openGuide(a[0],a[1])', [cn, sec])
            await pg.wait_for_timeout(350)
            # 解除 #page 内部滚动，否则 full_page 只截可视区
            await pg.evaluate("""() => {
                document.querySelectorAll('#page,.wrap,.main,body,html').forEach(el=>{
                    el.style.overflow='visible'; el.style.height='auto'; el.style.maxHeight='none';
                });
            }""")
            await pg.wait_for_timeout(150)
            fn = os.path.join(SHOT, 'c%02d_s%d_%d.png' % (cn, sec, width))
            await pg.screenshot(path=fn, full_page=True)
            print('ok', os.path.basename(fn), flush=True)
        print('JS 报错：', errs if errs else '无')
        await b.close()


asyncio.run(run(430, 932))
