# -*- coding: utf-8 -*-
"""把课件每页重构成整页 PNG（支持 q/Q/cm 变换栈与 Form XObject 递归）。

为什么需要这个：部分课件（01/02）导出时整页套了 `1 0 0 -1 0 540 cm` 的垂直翻转，
且图片外面还包了 Form XObject。只按 `cm ... Do` 平铺会把内容贴到错误位置。

输出：_ext/page/<课件代号>/p{页号:03d}.png（scale=2 → 1920x1080）
"""
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

OUT = '_ext/p2'
SCALE = 2

NUM = r'[-+]?(?:\d+\.?\d*|\.\d+)'
TOKEN = re.compile(
    r'(?P<q>(?<![\w/])q(?![\w]))|'
    r'(?P<Q>(?<![\w/])Q(?![\w]))|'
    r'(?P<cm>' + NUM + r'\s+' + NUM + r'\s+' + NUM + r'\s+' + NUM + r'\s+' + NUM + r'\s+' + NUM + r'\s+cm\b)|'
    r'/(?P<do>\w+)\s+Do\b')

IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def mul(m1, m2):
    """先应用 m2，再应用 m1。"""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a1 * a2 + b1 * c2, a1 * b2 + b1 * d2,
            c1 * a2 + d1 * c2, c1 * b2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


def resources_of(obj, parent_res):
    """取 Form XObject 的 /Resources，缺失则继承父级。"""
    r = obj.get('/Resources')
    if r is not None:
        return r.get_object()
    return parent_res


def xobjects_of(res):
    out = {}
    if res is None:
        return out
    xo = res.get('/XObject')
    if xo is None:
        return out
    for name, ref in xo.get_object().items():
        try:
            out[str(name).lstrip('/')] = ref.get_object()
        except Exception:
            pass
    return out


def draw_image(canvas, img, ctm, page_h):
    a, b, c, d, e, f = ctm
    corners = []
    for u, v in ((0, 0), (1, 0), (0, 1), (1, 1)):
        corners.append((a * u + c * v + e, b * u + d * v + f))
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    left = min(xs) * SCALE
    right = max(xs) * SCALE
    top = (page_h - max(ys)) * SCALE
    bottom = (page_h - min(ys)) * SCALE
    w = int(round(right - left))
    h = int(round(bottom - top))
    if w < 4 or h < 4 or w > 20000 or h > 20000:
        return False
    im = img
    if a < 0:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if d < 0:
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    try:
        im = im.resize((w, h), Image.LANCZOS)
        canvas.paste(im, (int(round(left)), int(round(top))))
        return True
    except Exception:
        return False


def walk(canvas, data, res, ctm, page_h, cache, depth=0):
    """解释内容流里与图片绘制相关的指令。"""
    if depth > 6:
        return 0
    xobjs = xobjects_of(res)
    stack = [ctm]
    drawn = 0
    for m in TOKEN.finditer(data):
        if m.group('q'):
            stack.append(stack[-1])
        elif m.group('Q'):
            if len(stack) > 1:
                stack.pop()
        elif m.group('cm'):
            vals = tuple(float(x) for x in m.group('cm').split()[:6])
            stack[-1] = mul(stack[-1], vals)
        elif m.group('do'):
            name = m.group('do')
            obj = xobjs.get(name)
            if obj is None:
                continue
            st = obj.get('/Subtype')
            if st == '/Image':
                img = cache.get(name)
                if img is None:
                    try:
                        img = _xobj_to_image(obj)[2]
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                    except Exception:
                        cache[name] = False
                        continue
                    cache[name] = img
                if img is False:
                    continue
                if draw_image(canvas, img, stack[-1], page_h):
                    drawn += 1
            elif st == '/Form':
                try:
                    sub = obj.get_data().decode('latin-1')
                except Exception:
                    continue
                mtx = obj.get('/Matrix')
                mtx = tuple(float(x) for x in mtx) if mtx else IDENT
                drawn += walk(canvas, sub, resources_of(obj, res),
                              mul(stack[-1], mtx), page_h, cache, depth + 1)
    return drawn


def main(keys):
    os.makedirs(OUT, exist_ok=True)
    stats = {}
    for key in keys:
        r = pypdf.PdfReader(FILES[key])
        d = os.path.join(OUT, key)
        os.makedirs(d, exist_ok=True)
        cache = {}
        blank = 0
        for pi, page in enumerate(r.pages, 1):
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
                blank += 1
        stats[key] = {'pages': len(r.pages), 'blank': blank}
        print('%s 页%d 空页%d' % (key, len(r.pages), blank), flush=True)
    with io.open(os.path.join(OUT, '_index.json'), 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1:] or list(FILES))
