# -*- coding: utf-8 -*-
"""把课件页面拼成联系表（contact sheet），用于快速判断哪些页有实质内容。

用法：python _ext/sheet.py k06 10 20 21 30 31 ...
输出：_ext/sheet/<课件>_<批号>.png，每格 480x270，5 列，格间留白并标页号
"""
import os
import sys

from PIL import Image, ImageDraw

CELL_W, CELL_H = 480, 270
COLS = 5
PAD = 6
LABEL_H = 22


def main(key, pages):
    src = os.path.join('_ext/page', key)
    rows = (len(pages) + COLS - 1) // COLS
    W = COLS * (CELL_W + PAD) + PAD
    H = rows * (CELL_H + LABEL_H + PAD) + PAD
    sheet = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(sheet)
    for i, p in enumerate(pages):
        fn = os.path.join(src, 'p%03d.png' % p)
        if not os.path.exists(fn):
            continue
        im = Image.open(fn).convert('RGB').resize((CELL_W, CELL_H), Image.LANCZOS)
        r, c = divmod(i, COLS)
        x = PAD + c * (CELL_W + PAD)
        y = PAD + r * (CELL_H + LABEL_H + PAD)
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + CELL_W, y + CELL_H], outline=(200, 200, 200))
        d.text((x + 4, y + CELL_H + 4), 'P%d' % p, fill=(180, 30, 30))
    os.makedirs('_ext/sheet', exist_ok=True)
    out = '_ext/sheet/%s_%s.png' % (key, pages[0])
    sheet.save(out)
    print(out, sheet.size)


if __name__ == '__main__':
    main(sys.argv[1], [int(x) for x in sys.argv[2:]])
