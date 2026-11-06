# -*- coding: utf-8 -*-
"""课件页筛选：统计每页文字层字数、抽首行、算内容哈希，标出知识点页/习题页/重复页。

判定口径（沿用前几轮）：
- 文字层 < 45 字 → 知识点图页（整页是图）
- 含「单选/多选/判断/填空/【答案】」且 > 40 字 → 习题页，跳过
- 内容哈希与已收录页相同 → 课件重发同一帧，去重
"""
import hashlib
import io
import json
import os
import re
import sys

import pypdf

FILES = {
    'k20': 'F:/xinli/18.能力上课件_20251203232409.pdf',
    'k21': 'F:/xinli/19.26能力下课件_20251206175006.pdf',
    'k22': 'F:/xinli/20.26人格上_20251207152022.pdf',
    'k23': 'F:/xinli/21.26人格下_20251208232647.pdf',
}

RE_Q = re.compile(r'单选|多选|判断题|填空题|【答案】|参考答案')


def norm(s):
    return re.sub(r'\s+', '', s)


def main(keys):
    seen = {}
    report = {}
    for key in keys:
        r = pypdf.PdfReader(FILES[key])
        rows = []
        for pi, page in enumerate(r.pages, 1):
            try:
                txt = page.extract_text() or ''
            except Exception:
                txt = ''
            n = len(norm(txt))
            h = hashlib.md5(norm(txt).encode('utf-8')).hexdigest()[:10]
            first = ''
            for ln in txt.splitlines():
                if ln.strip():
                    first = ln.strip()[:28]
                    break
            isq = bool(RE_Q.search(txt)) and n > 40
            dup = None
            if h in seen and n >= 45:
                dup = seen[h]
            elif n >= 45:
                seen[h] = '%s:%d' % (key, pi)
            kind = 'Q' if isq else ('IMG' if n < 45 else 'TXT')
            rows.append({'p': pi, 'n': n, 'kind': kind, 'dup': dup,
                         'first': first})
        report[key] = {'total': len(r.pages), 'rows': rows}
        keep = [x['p'] for x in rows
                if x['kind'] == 'IMG' or (x['kind'] == 'TXT' and not x['dup'])]
        print('%s 共%d页 知识点候选%d页' % (key, len(r.pages), len(keep)))
    os.makedirs('_ext/sel', exist_ok=True)
    with io.open('_ext/sel/plan_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print('明细写入 _ext/sel/plan_report.json')


if __name__ == '__main__':
    main(sys.argv[1:] or list(FILES))
