# -*- coding: utf-8 -*-
"""第 8/9 章课件整页重构成 PNG，只渲染需要的页。

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
    'k15': 'F:/xinli/15.意志课件_20251129161254.pdf',
    'k16': 'F:/xinli/16.26需要课件_20251130141530.pdf',
    'k17': 'F:/xinli/17.动机+兴趣课件_20251201134924.pdf',
}

PLAN = {
    # 意志：33 个知识点图页 + 4 个有文字层的框架/对比页；40 个配套习题页跳过
    'k15': [1, 2, 3, 4, 7, 10, 11, 12, 13, 14, 15, 20, 21, 22, 23, 26, 27, 28,
            33, 36, 37, 38, 43, 46, 49, 50, 51, 56, 57, 62, 63, 64, 67, 68,
            69, 74, 79],
    # 需要：19 个图页 + P14 文字页；28 个习题/易错题页跳过
    'k16': [1, 2, 3, 4, 5, 6, 7, 10, 13, 14, 15, 16, 17, 30, 33, 34, 35, 36,
            45, 48],
    # 动机 + 兴趣：25 个图页；24 个习题页跳过
    'k17': [1, 2, 3, 4, 5, 8, 11, 12, 13, 14, 15, 16, 21, 22, 23, 24, 25, 28,
            29, 30, 35, 38, 39, 40, 45],
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
