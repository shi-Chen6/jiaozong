# -*- coding: utf-8 -*-
"""把课件页图加入先导卡插图目录，并给出可直接粘进 guide/NN.py 的 img 块。

用法：
    python _ext/gimg_add.py k42 p012 c24
    python _ext/gimg_add.py k42 12 c24 --name skinner_box.png

源图：_ext/p3/<key>/pNNN.png（PyMuPDF 渲染的整页图）
产出：_ext/gimg/<章目录>/pNNN.png（等比缩到最长边 1000px、256 色 PNG）
     并打印建议的 img 块代码与压缩后体积。

注意：只复制「判断为适合直接嵌图」的页。其余页面按 GUIDE_SPEC 第三条
转成表格 / 列表 / 段落，不要塞图。
"""
import argparse
import io
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P3 = os.path.join(ROOT, '_ext', 'p3')
GIMG = os.path.join(ROOT, '_ext', 'gimg')
MAX_EDGE = 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('key', help='课件 key，如 k42')
    ap.add_argument('page', help='页号，如 p012 或 12')
    ap.add_argument('chapter', help='目标章目录，如 c24')
    ap.add_argument('--name', default='', help='自定义输出文件名（含扩展名）')
    ap.add_argument('--jpg', action='store_true', help='输出 JPEG（照片/漫画类更省）')
    a = ap.parse_args()

    pno = int(a.page.lower().lstrip('p'))
    src = os.path.join(P3, a.key, 'p%03d.png' % pno)
    if not os.path.exists(src):
        sys.exit('找不到源图：%s' % src)

    dstdir = os.path.join(GIMG, a.chapter)
    os.makedirs(dstdir, exist_ok=True)
    name = a.name or ('p%03d.%s' % (pno, 'jpg' if a.jpg else 'png'))
    dst = os.path.join(dstdir, name)

    im = Image.open(src)
    im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
    buf = io.BytesIO()
    if a.jpg:
        im.convert('RGB').save(buf, 'JPEG', quality=84, optimize=True, progressive=True)
    else:
        im.convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT) \
            .save(buf, 'PNG', optimize=True)
    raw = buf.getvalue()
    with open(dst, 'wb') as f:
        f.write(raw)

    rel = '%s/%s' % (a.chapter, name)
    fmt = ", 'fmt':'jpg'" if a.jpg else ''
    print('已写入', os.path.relpath(dst, ROOT), '%d KB' % (len(raw) // 1024))
    print('建议 img 块：')
    print("{'k':'img', 'f':'%s'%s, 'cap':'（一句话说清图在讲什么，注明课件页 P%d）', "
          "'alt':'（简短替代文字）'}," % (rel, fmt, pno))
    if len(raw) > 80 * 1024:
        print('⚠ 超过建议上限 80 KB，考虑裁剪无关区域或改用 --jpg')


if __name__ == '__main__':
    main()
