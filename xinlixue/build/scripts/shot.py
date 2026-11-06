# -*- coding: utf-8 -*-
"""真浏览器巡检：截图首页 / 展开 / 刷题 / 判分 / 填空 / 各页签 / 搜索 / 宽屏。

用法：
    python shot.py 心理学刷题.html            # 截图到同目录 shots/
    python shot.py 心理学刷题.html -o _work/shots

依赖：pip install playwright && playwright install chromium
脚本同时收集 pageerror，有报错会打印出来并以非 0 退出。
"""
import argparse
import asyncio
import os
import sys


async def run(html, outdir):
    from playwright.async_api import async_playwright

    os.makedirs(outdir, exist_ok=True)
    url = 'file:///' + os.path.abspath(html).replace('\\', '/')
    errs, logs = [], []

    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 430, 'height': 932},
                              device_scale_factor=2)
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: logs.append(m.text) if m.type == 'error' else None)
        await pg.goto(url)
        await pg.wait_for_timeout(500)

        async def shot(name, full=False):
            await pg.screenshot(path=os.path.join(outdir, name), full_page=full)
            print('  ✓', name)

        # 1 首页（默认折叠）
        total = await pg.evaluate("DATA.total")
        print(f'题量 {total}')
        await shot('1-home.png', full=True)

        # 2 展开第一张章卡
        try:
            await pg.click('.stog >> nth=0')
            await pg.wait_for_timeout(350)
            await shot('2-home-expanded.png', full=True)
            n = await pg.evaluate("document.querySelectorAll('.srow').length")
            print('  小节行数', n)
        except Exception as e:
            print('  ! 展开失败', e)

        # 3 进某个小节做题
        try:
            await pg.click('.srow >> nth=0')
            await pg.wait_for_timeout(400)
            await shot('3-study.png')
            # 依次点选项直到能提交
            n = await pg.evaluate("document.querySelectorAll('.opt').length")
            for i in range(n):
                await pg.click(f'.opt >> nth={i}')
                await pg.wait_for_timeout(120)
            try:
                await pg.click('[data-act="submit"]', timeout=2000)
                await pg.wait_for_timeout(400)
                await shot('4-answer.png', full=True)
            except Exception:
                pass
            # 下一题
            try:
                await pg.click('[data-act="next"]', timeout=2000)
                await pg.wait_for_timeout(400)
                await shot('5-next.png')
            except Exception:
                pass
        except Exception as e:
            print('  ! 做题流程异常', e)

        # 6 填空
        try:
            await pg.evaluate("""
              (() => {
                const c = DATA.chapters.find(c => c.qs.some(q => q.t === '填空题'));
                if (!c) return 'none';
                const f = c.qs.find(q => q.t === '填空题');
                startStudy('chapter', c.no, f.sec);
                VIEW.list = [{cn: c.no, n: f.n}]; VIEW.idx = 0; render();
                return f.r;
              })()
            """)
            await pg.wait_for_timeout(300)
            await shot('6-fill.png')
            try:
                await pg.click('[data-act="revealFill"]', timeout=2000)
                await pg.wait_for_timeout(300)
                await shot('7-fill-reveal.png')
                await pg.click('[data-act="fillOK"]', timeout=2000)
                await pg.wait_for_timeout(400)
                await shot('8-fill-done.png', full=True)
            except Exception as e:
                print('  填空交互', e)
        except Exception as e:
            print('  ! 填空流程异常', e)

        # 9 退出 → 页签巡检
        try:
            await pg.click('[data-act="exit"]', timeout=3000)
            await pg.wait_for_timeout(400)
        except Exception:
            await pg.evaluate("goHome && goHome()")
            await pg.wait_for_timeout(400)
        for tab in ('search', 'wrong', 'fav', 'stat'):
            try:
                await pg.click(f'button[data-tab="{tab}"]')
                await pg.wait_for_timeout(300)
                await shot(f'9-tab-{tab}.png')
            except Exception as e:
                print(f'  页签 {tab} 异常', e)

        # 9.5 先导知识（页面带 GUIDE_DATA 才巡检）
        try:
            nch = await pg.evaluate(
                "() => (typeof GUIDE_DATA === 'undefined' ? 0 : Object.keys(GUIDE_DATA).length)")
            if nch:
                await pg.click('#btnBack')
                await pg.wait_for_timeout(350)
                await pg.click('[data-guide] >> nth=0')
                await pg.wait_for_timeout(450)
                # .page 是内层滚动容器，full_page 抓不全 —— 临时撑开
                await pg.evaluate("""() => {
                  const el = document.getElementById('page');
                  el.style.overflow = 'visible'; el.style.flex = 'none'; el.style.height = 'auto';
                  document.body.style.overflow = 'visible';
                }""")
                await pg.wait_for_timeout(200)
                await shot('9b-guide.png', full=True)
                await pg.evaluate("""() => {
                  const el = document.getElementById('page');
                  el.style.overflow = ''; el.style.flex = ''; el.style.height = '';
                  document.body.style.overflow = '';
                }""")
                await pg.click('[data-gdone] >> nth=0')
                await pg.wait_for_timeout(300)
                await shot('9c-guide-done.png')
                v = await pg.evaluate("() => localStorage.getItem(Object.keys(localStorage)"
                                      ".find(k => k.includes('guide')) || '')")
                print('  先导知识', nch, '章；背诵进度', v)
                await pg.set_viewport_size({'width': 1280, 'height': 900})
                await pg.wait_for_timeout(300)
                await shot('9d-guide-desktop.png')
                await pg.set_viewport_size({'width': 430, 'height': 932})
                await pg.wait_for_timeout(300)
                await pg.click('#btnBack')
                await pg.wait_for_timeout(300)
        except Exception as e:
            print('  先导知识巡检', e)

        # 10 搜索
        try:
            await pg.click('button[data-tab="search"]')
            await pg.wait_for_timeout(200)
            inp = await pg.query_selector('#qInput')
            if inp:
                # 从第 2 章取一段纯中文当关键词，避免抓到题干开头的括号
                kw = await pg.evaluate("""
                  (() => {
                    const c = DATA.chapters[Math.min(1, DATA.chapters.length - 1)];
                    for (const q of c.qs) {
                      const m = q.s.replace(/[^\\u4e00-\\u9fa5]/g, '');
                      if (m.length >= 3) return m.slice(0, 3);
                    }
                    return '答案';
                  })()
                """)
                await inp.fill(kw)
                await pg.keyboard.press('Enter')
                await pg.wait_for_timeout(500)
                await shot('10-search.png')
                print('  搜索关键词', kw)
        except Exception as e:
            print('  搜索异常', e)

        # 11 宽屏
        await pg.set_viewport_size({'width': 1280, 'height': 900})
        try:
            await pg.click('button[data-tab="home"]')
        except Exception:
            pass
        await pg.wait_for_timeout(400)
        await shot('11-desktop.png')

        await b.close()

    if errs:
        print('\n!! 控制台报错', len(errs), '条')
        for e in errs[:10]:
            print('  ', e)
    else:
        print('\n无 JS 运行时报错')
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('html')
    ap.add_argument('-o', '--outdir', default='')
    a = ap.parse_args()
    outdir = a.outdir or os.path.join(os.path.dirname(os.path.abspath(a.html)), 'shots')
    errs = asyncio.run(run(a.html, outdir))
    print('截图目录', outdir)
    sys.exit(1 if errs else 0)


if __name__ == '__main__':
    main()
