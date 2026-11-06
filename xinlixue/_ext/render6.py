# -*- coding: utf-8 -*-
"""第 10、11 章课件整页重构成 PNG，只渲染需要的页。

复用 render2.py 的内容流解释器（q/Q/cm 栈 + Form XObject 递归）。
页清单写死在 PLAN 里：只渲染文字层稀薄的知识点页，配套习题页跳过。
输出：_ext/p3/<key>/p{页号:03d}.png
"""
import io
import json
import os
import sys

import pypdf
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render2 import IDENT, walk  # noqa: E402

FILES = {
    'k20': 'F:/xinli/18.能力上课件_20251203232409.pdf',
    'k21': 'F:/xinli/19.26能力下课件_20251206175006.pdf',
    'k22': 'F:/xinli/20.26人格上_20251207152022.pdf',
    'k23': 'F:/xinli/21.26人格下_20251208232647.pdf',
}

PLAN = {
    # 能力上：70 页，封面/配套习题 p68-69/结尾页 剔除，CHAO GE 表情页跳过
    'k20': [2, 3, 4, 5, 8, 9, 12, 17, 18, 29, 30, 31, 38, 40, 41, 42, 47, 48,
            49, 50, 51, 54, 56, 57, 58, 59, 60, 61],
    # 能力下：57 页
    'k21': [2, 3, 8, 11, 16, 17, 20, 21, 22, 23, 27, 28, 29, 30, 35, 40, 41,
            44, 45, 46, 47, 54, 55, 56],
    # 人格上：47 页，CHAO GE 页跳过
    'k22': [2, 4, 5, 8, 9, 10, 13, 16, 17, 20, 21, 24, 25, 26, 29, 30, 31,
            32, 33, 36, 37, 38, 39, 40, 41, 42],
    # 人格下：84 页
    'k23': [3, 4, 5, 8, 9, 16, 19, 22, 23, 24, 25, 28, 29, 30, 37, 40, 43,
            44, 45, 48, 51, 54, 57, 62, 63, 64, 71, 72, 73, 74, 77, 78, 79],
}

OUT = '_ext/p3'
SCALE = 2


def main(keys):
    os.makedirs(OUT, exist_ok=True)
    stats = {}
    for key in keys:
        r = pypdf.PdfReader(FILES[key])
        d = os.path.join(OUT, key)
        os.makedirs(d, exist_ok=True)
        cache = {}
        blank = []
        for pi in PLAN[key]:
            page = r.pages[pi - 1]
            pw = float(page.mediabox.width)
            ph = float(page.mediabox.height)
            canvas = Image.new('RGB', (int(pw * SCALE), int(ph * SCALE)), 'white')
            res = page.get('/Resources')
            res = res.get_object() if res is not None else None
            try:
                data = page.get_contents().get_data().decode('latin-1')
            except Exception:
                data = ''
            n = walk(canvas, data, res, IDENT, ph, cache)
            canvas.save(os.path.join(d, 'p%03d.png' % pi))
            if n == 0:
                blank.append(pi)
        stats[key] = {'rendered': len(PLAN[key]), 'blank': blank}
        print('%s 渲染%d 空%s' % (key, len(PLAN[key]), blank), flush=True)
    io.open(os.path.join(OUT, '_index.json'), 'w', encoding='utf-8').write(
        json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main(sys.argv[1:] or list(FILES))
