# -*- coding: utf-8 -*-
"""把 6 份课件的每页内容图导出为 PNG，供逐页转录。

规则：
  1. 跨页高频出现的图（>= 15% 页数）视为模板/背景，丢弃
  2. 面积 < 15000 或宽 < 150 的视为装饰/图标，丢弃
  3. CMYK 转 RGB 再存
输出：_ext/kb/<课件代号>/p{页号:03d}_{序号}.png
"""
import collections
import io
import json
import os

import pypdf

FILES = {
    'k01': 'F:/xinli/01.心理学概述1_20251104095717.pdf',
    'k02': 'F:/xinli/02.心理学概述2课件_20251106215938.pdf',
    'k03': 'F:/xinli/03.意识和注意完整版（周日上午+晚上）_20251108093145.pdf',
    'k05': 'F:/xinli/05.26感觉课件终版_20251112123432.pdf',
    'k06': 'F:/xinli/06.26知觉课件_20251112225452.pdf',
    'k08': 'F:/xinli/08.感知觉重点背诵_20251116214434.pdf',
}

OUT = '_ext/kb'
MIN_AREA = 15000
MIN_W = 150


def main():
    os.makedirs(OUT, exist_ok=True)
    report = {}
    for key, path in FILES.items():
        r = pypdf.PdfReader(path)
        npages = len(r.pages)
        # 第一遍：统计图片指纹出现次数
        cnt = collections.Counter()
        pages = []
        for page in r.pages:
            sigs = []
            for im in page.images:
                try:
                    w, h = im.image.size
                except Exception:
                    continue
                sig = (im.name, w, h)
                sigs.append((sig, im))
                cnt[sig] += 1
            pages.append(sigs)

        thr = max(3, int(npages * 0.15))
        templates = {s for s, c in cnt.items() if c >= thr}

        d = os.path.join(OUT, key)
        os.makedirs(d, exist_ok=True)
        kept, dropped_t = 0, 0
        page_map = {}
        for pi, sigs in enumerate(pages, 1):
            k = 0
            for sig, im in sigs:
                if sig in templates:
                    dropped_t += 1
                    continue
                try:
                    img = im.image
                except Exception:
                    continue
                w, h = img.size
                if w * h < MIN_AREA or w < MIN_W:
                    continue
                if img.mode in ('CMYK', 'P', 'LA', 'L'):
                    img = img.convert('RGB')
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # 太长的图（整页长截图）不裁，直接存
                fn = 'p%03d_%d.png' % (pi, k)
                img.save(os.path.join(d, fn))
                page_map.setdefault(pi, []).append(fn)
                kept += 1
                k += 1
        report[key] = {'pages': npages, 'templates': len(templates),
                       'kept': kept, 'pages_with_img': len(page_map)}
        print(key, report[key], flush=True)
    with io.open(os.path.join(OUT, '_index.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
