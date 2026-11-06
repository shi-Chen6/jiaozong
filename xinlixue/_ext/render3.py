# -*- coding: utf-8 -*-
"""第 4/6/7 章课件整页重构成 PNG，只渲染需要的页。

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
    'k07': 'F:/xinli/07.26记忆上_20251115112456.pdf',
    'k09': 'F:/xinli/09.记忆下课件_20251117193147.pdf',
    'k10': 'F:/xinli/10.记忆3_20251119224633.pdf',
    'k11': 'F:/xinli/11.思维上_20251122165200.pdf',
    'k12': 'F:/xinli/12.思维下_20251123141432.pdf',
    'k13': 'F:/xinli/13.情绪课件_20251124231913.pdf',
    'k14': 'F:/xinli/14.情绪情感2课件_20251126204852.pdf',
}

PLAN = {
    'k07': [1, 2, 3, 4, 7, 8, 9, 14, 15, 16, 17, 20, 22, 23, 24, 25, 26, 27,
            28, 29, 36, 37, 42, 47, 50],
    'k09': [1, 2, 3, 4, 7, 8, 15, 18, 19, 24, 27, 30, 33, 34, 35, 42, 44, 54,
            57, 59, 68, 73, 74, 79, 80, 85, 90, 91, 92],
    'k10': [1, 2, 3, 5, 6, 7, 12, 13, 18, 19, 24, 29, 30, 31],
    'k11': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 21, 22, 23, 24, 25, 26, 27,
            32, 37, 38, 39, 40, 41, 46, 47, 48, 49, 50, 51, 52, 55, 62],
    'k12': [1, 2, 3, 4, 5, 6, 7, 8, 9, 14, 15, 18, 19, 20, 23, 24, 29, 30, 31,
            32, 33, 34, 35, 36, 41, 42],
    'k13': [1, 2, 3, 4, 5, 8, 11, 14, 17, 18, 23, 32, 33, 34, 35, 36, 39, 40,
            43, 46, 47, 48, 49, 50, 51, 52, 53, 64, 65, 66, 71, 74, 77, 78,
            79, 84, 85, 86, 91],
    'k14': [1, 3, 4, 11, 12, 13, 14, 15, 20, 21, 22, 27],
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
