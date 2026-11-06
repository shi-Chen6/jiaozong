# -*- coding: utf-8 -*-
import asyncio, io, os
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'file:///' + os.path.join(ROOT, '心理学刷题.html').replace('\\', '/')
SHOT = os.path.join(ROOT, '_work', 'shots')
os.makedirs(SHOT, exist_ok=True)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 430, 'height': 932}, device_scale_factor=2)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        await pg.goto(URL)
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(SHOT, '1-home.png'), full_page=True)

        # 点第 1 章「二、心理学的产生与发展」小节
        await pg.click('.srow[data-sec="二、心理学的产生与发展"]')
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.path.join(SHOT, '2-section.png'))

        # 选一个选项看判分与解析
        await pg.click('.opt >> nth=1')
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.path.join(SHOT, '3-answer.png'), full_page=True)

        # 回到首页 → 第 3 章「一、感觉」→ 第 2 题（填空）
        await pg.click('[data-act="exit"]')
        await pg.wait_for_timeout(250)
        await pg.click('.srow[data-sec="一、感觉"]')
        await pg.wait_for_timeout(250)
        await pg.click('.actbar .btn.pri')          # 下一题 → 填空题
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.path.join(SHOT, '4-fill.png'))
        await pg.click('[data-act="revealFill"]')
        await pg.wait_for_timeout(250)
        await pg.screenshot(path=os.path.join(SHOT, '5-fill-reveal.png'))
        await pg.click('[data-act="fillOK"]')
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.path.join(SHOT, '6-fill-done.png'), full_page=True)

        # 退出刷题页
        try:
            await pg.click('[data-act="exit"]', timeout=3000)
            await pg.wait_for_timeout(300)
        except Exception as e:
            print('exit skip', e)
        # 底部各页签巡检
        for tab, name in [('search','搜索'),('wrong','错题本'),('fav','收藏'),('stat','统计')]:
            await pg.click(f'button[data-tab="{tab}"]')
            await pg.wait_for_timeout(250)
            await pg.screenshot(path=os.path.join(SHOT, f'8-tab-{tab}.png'))
            print('tab', name, 'ok')
        # 搜索一次
        await pg.click('button[data-tab="search"]')
        await pg.wait_for_timeout(200)
        inp = await pg.query_selector('#qInput')
        if inp:
            await inp.fill('注意')
            await pg.keyboard.press('Enter')
            await pg.wait_for_timeout(400)
            await pg.screenshot(path=os.path.join(SHOT, '9-search.png'))
            n = await pg.evaluate("document.querySelectorAll('[data-res]').length")
            print('搜索结果条数', n)

        # 桌面宽度
        pg2 = await b.new_page(viewport={'width': 1280, 'height': 900}, device_scale_factor=1)
        await pg2.goto(URL)
        await pg2.wait_for_timeout(400)
        await pg2.screenshot(path=os.path.join(SHOT, '7-desktop.png'))
        await b.close()
        print('errors:', errs)

asyncio.run(main())
