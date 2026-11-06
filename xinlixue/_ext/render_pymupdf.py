# -*- coding: utf-8 -*-
"""用 PyMuPDF 正确渲染第 10、11 章课件整页 PNG。

原因：k22/k23 的 pypdf mediabox 返回旋转前的 595x842，实际是 842x595 横版，
用自写 walk 解释器会画错方向、裁切内容。PyMuPDF 直接按真实页 rect 渲染。

输出：_ext/p3/<key>/p{页号:03d}.png（scale=2）
"""
import json
import os

import pymupdf

FILES = {
    'k20': 'F:/xinli/18.能力上课件_20251203232409.pdf',
    'k21': 'F:/xinli/19.26能力下课件_20251206175006.pdf',
    'k22': 'F:/xinli/20.26人格上_20251207152022.pdf',
    'k23': 'F:/xinli/21.26人格下_20251208232647.pdf',
}

PLAN = {
    'k20': [2, 3, 4, 5, 8, 9, 12, 17, 18, 29, 30, 31, 38, 40, 41, 42, 47, 48,
            49, 50, 51, 54, 56, 57, 58, 59, 60, 61],
    'k21': [2, 3, 8, 11, 16, 17, 20, 21, 22, 23, 27, 28, 29, 30, 35, 40, 41,
            44, 45, 46, 47, 54, 55, 56],
    'k22': [2, 4, 5, 8, 9, 10, 13, 16, 17, 20, 21, 24, 25, 26, 29, 30, 31,
            32, 33, 36, 37, 38, 39, 40, 41, 42],
    'k23': [3, 4, 5, 8, 9, 16, 19, 22, 23, 24, 25, 28, 29, 30, 37, 40, 43,
            44, 45, 48, 51, 54, 57, 62, 63, 64, 71, 72, 73, 74, 77, 78, 79],
}

OUT = '_ext/p3'
SCALE = 2


def main():
    stats = {}
    for key, path in FILES.items():
        doc = pymupdf.open(path)
        d = os.path.join(OUT, key)
        os.makedirs(d, exist_ok=True)
        for pi in PLAN[key]:
            page = doc[pi - 1]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(SCALE, SCALE))
            pix.save(os.path.join(d, 'p%03d.png' % pi))
        stats[key] = len(PLAN[key])
        print('%s 渲染%d页' % (key, len(PLAN[key])), flush=True)
        doc.close()
    with open(os.path.join(OUT, '_index.json'), 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
