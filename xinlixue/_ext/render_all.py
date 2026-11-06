# -*- coding: utf-8 -*-
"""按 plan_all.json 的知识点页清单，用 PyMuPDF 渲染指定课件的整页 PNG。

用法：python render_all.py k24 k25 k26 ...   （不传则渲染全部）
输出：_ext/p3/<key>/p{页号:03d}.png（scale=2）
"""
import io
import json
import os
import sys

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

OUT = '_ext/p3'
SCALE = 2


def main(keys):
    plan = json.load(io.open('_ext/sel/plan_all.json', encoding='utf-8'))['plan']
    keys = keys or list(plan.keys())
    for key in keys:
        if key not in FILES:
            print('未知 key', key)
            continue
        doc = pymupdf.open(FILES[key])
        d = os.path.join(OUT, key)
        os.makedirs(d, exist_ok=True)
        pages = plan[key]
        for pi in pages:
            pix = doc[pi - 1].get_pixmap(matrix=pymupdf.Matrix(SCALE, SCALE))
            pix.save(os.path.join(d, 'p%03d.png' % pi))
        print('%s 渲染%d页' % (key, len(pages)), flush=True)
        doc.close()


if __name__ == '__main__':
    main(sys.argv[1:])
