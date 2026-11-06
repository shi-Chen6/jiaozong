# -*- coding: utf-8 -*-
"""把课件每页按 PDF 内容流的变换矩阵重新拼成整页 PNG。

思路：解析 `q ... cm /ImN Do Q`，把每张图按矩阵贴到 960x540（或页面实际尺寸）画布上。
同一 XObject 只解码一次（课件里背景板、logo 都是复用的），速度比逐图导出快得多。

输出：_ext/page/<课件代号>/p{页号:03d}.png，scale=2 → 1920x1080
"""
import collections
import io
import json
import os
import re
import sys

import pypdf
from PIL import Image
from pypdf.generic._image_xobject import _xobj_to_image

FILES = {
    'k01': 'F:/xinli/01.心理学概述1_20251104095717.pdf',
    'k02': 'F:/xinli/02.心理学概述2课件_20251106215938.pdf',
    'k03': 'F:/xinli/03.意识和注意完整版（周日上午+晚上）_20251108093145.pdf',
    'k05': 'F:/xinli/05.26感觉课件终版_20251112123432.pdf',
    'k06': 'F:/xinli/06.26知觉课件_20251112225452.pdf',
    'k08': 'F:/xinli/08.感知觉重点背诵_20251116214434.pdf',
}

OUT = '_ext/page'
SCALE = 2
NUM = r'[-+]?[\d.]+'
RE_DRAW = re.compile(
    r'(' + NUM + r')\s+(' + NUM + r')\s+(' + NUM + r')\s+(' + NUM + r')\s+'
    r'(' + NUM + r')\s+(' + NUM + r')\s+cm\s*/(\w+)\s+Do')


def page_xobjects(page):
    res = page.get('/Resources')
    if res is None:
        return {}
    res = res.get_object()
    xo = res.get('/XObject')
    if xo is None:
        return {}
    out = {}
    for name, ref in xo.get_object().items():
        try:
            out[name.lstrip('/')] = ref.get_object()
        except Exception:
            pass
    return out


def main(keys):
    os.makedirs(OUT, exist_ok=True)
    stats = {}
    for key in keys:
        path = FILES[key]
        r = pypdf.PdfReader(path)
        d = os.path.join(OUT, key)
        os.makedirs(d, exist_ok=True)
        cache = {}
        blank = 0
        for pi, page in enumerate(r.pages, 1):
            mb = page.mediabox
            pw = float(mb.width)
            ph = float(mb.height)
            W, H = int(pw * SCALE), int(ph * SCALE)
            canvas = Image.new('RGB', (W, H), 'white')
            xobjs = page_xobjects(page)
            try:
                data = page.get_contents().get_data().decode('latin-1')
            except Exception:
                data = ''
            drew = 0
            for m in RE_DRAW.finditer(data):
                a, b, c, dd, e, f, name = m.groups()
                a, b, c, dd, e, f = (float(a), float(b), float(c),
                                     float(dd), float(e), float(f))
                obj = xobjs.get(name)
                if obj is None or obj.get('/Subtype') != '/Image':
                    continue
                w = abs(a)
                h = abs(dd)
                if w < 6 or h < 6:
                    continue
                cid = id(obj)
                img = cache.get(cid)
                if img is None:
                    try:
                        img = _xobj_to_image(obj)[2]
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                    except Exception:
                        cache[cid] = False
                        continue
                    cache[cid] = img
                if img is False:
                    continue
                tw, th = max(1, int(round(w * SCALE))), max(1, int(round(h * SCALE)))
                # 位置：PDF 原点在左下
                left = int(round(e * SCALE))
                top = int(round((ph - f - h) * SCALE))
                try:
                    canvas.paste(img.resize((tw, th), Image.LANCZOS), (left, top))
                    drew += 1
                except Exception:
                    pass
            fn = os.path.join(d, 'p%03d.png' % pi)
            canvas.save(fn)
            if drew == 0:
                blank += 1
        n = len(r.pages)
        stats[key] = {'pages': n, 'blank': blank}
        print('%s 页%d 空页%d' % (key, n, blank), flush=True)
    with io.open(os.path.join(OUT, '_index.json'), 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    keys = sys.argv[1:] or list(FILES)
    main(keys)
