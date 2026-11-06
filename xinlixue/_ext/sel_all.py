# -*- coding: utf-8 -*-
"""第 12–34 章全部课件的知识点页筛选（统一流水线）。

口径与前几章一致：
- 文字层 < 45 字 → 知识点图页
- 含「单选/多选/判断/填空/【答案】」且 > 40 字 → 配套习题页，跳过
- md5 内容哈希跨文件去重（同一帧重发）

输出：_ext/sel/plan_all.json，结构 {key: [页号,...]}
"""
import hashlib
import io
import json
import os
import re

import pymupdf

FILES = {
    'k24': 'F:/xinli/22.26社会心理1_20251210225222.pdf',
    'k25': 'F:/xinli/23.社会心理2_20251213183444.pdf',
    'k26': 'F:/xinli/25.社会心理3_20251216195536.pdf',
    'k27': 'F:/xinli/24.教育心理学概述上_20251214172129.pdf',
    'k28': 'F:/xinli/25.教育心理学下_20251216195822.pdf',
    'k29': 'F:/xinli/26.学生心理发展概述_20251217215818.pdf',
    'k30': 'F:/xinli/27.26学生认知发展-皮亚杰_20251220133434.pdf',
    'k31': 'F:/xinli/28.26维果斯基_20251220223924.pdf',
    'k32': 'F:/xinli/29.26社会性发展（弗洛伊德+埃里克森+马西亚）_20251222225716.pdf',
    'k33': 'F:/xinli/31.26个别差异与因材施教_20251224214247.pdf',
    'k34': 'F:/xinli/31.26个别差异与因材施教_2025122509021577.pdf',
    'k35': 'F:/xinli/32.26学习概述课件_20251227102708.pdf',
    'k36': 'F:/xinli/33.26行为主义+巴普洛夫+桑代克+华生授课课件_20251228133602.pdf',
    'k37': 'F:/xinli/35.26班杜拉_20260101125840.pdf',
    'k38': 'F:/xinli/35.26认知主义总论+前三个人物_20260102213816.pdf',
    'k39': 'F:/xinli/36.26奥苏贝尔+加涅_20260102215044.pdf',
    'k40': 'F:/xinli/38.26建构主义_20260105224854.pdf',
    'k41': 'F:/xinli/39.26人本主义课件_20260107220828.pdf',
    'k42': 'F:/xinli/39.26学习动机上_20260107222259.pdf',
    'k43': 'F:/xinli/41.26下学习动机最新版_20260111132806.pdf',
    'k44': 'F:/xinli/41.26上学习策略课件_20260111171646.pdf',
    'k45': 'F:/xinli/42.26学习策略下_20260112225408.pdf',
    'k46': 'F:/xinli/44.26学习迁移_20260117132738.pdf',
    'k47': 'F:/xinli/45.26知识的学习_20260118215703.pdf',
    'k48': 'F:/xinli/46.26技能学习_20260120215702.pdf',
    'k49': 'F:/xinli/47.2026态度与品德上课件_20260121225724.pdf',
    'k50': 'F:/xinli/48.26态度与品德下_20260123225234.pdf',
    'k51': 'F:/xinli/50.26问题解决与创造性_20260125142919.pdf',
    'k52': 'F:/xinli/51.26心理健康课件_20260126223828.pdf',
    'k53': 'F:/xinli/52.26教师专业成长_20260129121548.pdf',
    'k54': 'F:/xinli/53.2教学设计最新_20260201165026.pdf',
    'k55': 'F:/xinli/54.26课堂管理_20260201145907.pdf',
}

RE_Q = re.compile(r'单选|多选|判断题|填空题|【答案】|参考答案')


def norm(s):
    return re.sub(r'\s+', '', s)


def main():
    os.makedirs('_ext/sel', exist_ok=True)
    seen = {}
    plan = {}
    detail = {}
    for key, path in FILES.items():
        doc = pymupdf.open(path)
        keep = []
        rows = []
        for pi in range(doc.page_count):
            page = doc[pi]
            try:
                txt = page.get_text() or ''
            except Exception:
                txt = ''
            n = len(norm(txt))
            h = hashlib.md5(norm(txt).encode('utf-8')).hexdigest()[:10]
            first = ''
            for ln in txt.splitlines():
                if ln.strip():
                    first = ln.strip()[:24]
                    break
            isq = bool(RE_Q.search(txt)) and n > 40
            dup = None
            if n >= 45:
                if h in seen:
                    dup = seen[h]
                else:
                    seen[h] = '%s:%d' % (key, pi + 1)
            kind = 'Q' if isq else ('IMG' if n < 45 else 'TXT')
            if kind == 'IMG' or (kind == 'TXT' and not dup):
                keep.append(pi + 1)
            rows.append({'p': pi + 1, 'n': n, 'kind': kind, 'dup': dup,
                         'first': first})
        plan[key] = keep
        detail[key] = rows
        print('%-5s 页%-4d 知识点%-3d' % (key, doc.page_count, len(keep)))
        doc.close()
    with io.open('_ext/sel/plan_all.json', 'w', encoding='utf-8') as f:
        json.dump({'plan': plan, 'detail': detail}, f, ensure_ascii=False, indent=0)
    total = sum(len(v) for v in plan.values())
    print('合计知识点页', total)


if __name__ == '__main__':
    main()
