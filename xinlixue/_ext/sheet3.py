# -*- coding: utf-8 -*-
"""把渲染好的整页 PNG 拼成 2x2 联系表，减少逐页读图的往返次数。

用法：python _ext/sheet3.py k07 1,2,3,4  → _ext/sheet/k07_001-004.png
"""
import os
import sys

from PIL import Image

SRC = '_ext/p3'
OUT = '_ext/sheet'
CELL = (1280, 720)


def build(key, pages, tag):
    os.makedirs(OUT, exist_ok=True)
    canvas = Image.new('RGB', (CELL[0] * 2, CELL[1] * 2), 'white')
    for i, p in enumerate(pages[:4]):
        im = Image.open(os.path.join(SRC, key, 'p%03d.png' % p)).convert('RGB')
        im = im.resize(CELL, Image.LANCZOS)
        canvas.paste(im, ((i % 2) * CELL[0], (i // 2) * CELL[1]))
    fn = os.path.join(OUT, '%s_%s.png' % (key, tag))
    canvas.save(fn)
    return fn


if __name__ == '__main__':
    key = sys.argv[1]
    pages = [int(x) for x in sys.argv[2].split(',')]
    tag = sys.argv[3] if len(sys.argv) > 3 else 'a'
    print(build(key, pages, tag))
