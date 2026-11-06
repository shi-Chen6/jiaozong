# -*- coding: utf-8 -*-
"""为扩充章节生成「考点速览」先导知识卡。

第 1–3 章的先导卡是照课件逐页转录的（guide/1..3.py），不要用本脚本覆盖。
本脚本只处理第 4 章及以后：这些章节只有题目、没有课件转录稿，
所以卡片内容——严格讲——只能是从「正确项」里归并出来的高频表述，
不是教材原文。因此标题写「高频正确表述」，不写「考点」，避免误导。

用法：python tools/gen_guide.py
产物：guide/NN.py
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import import_all as ia  # noqa: E402

GUIDE = os.path.join(ROOT, 'guide')
AUDIT = os.path.join(ROOT, 'build_import')

# 正确项里能当知识点看的：名词性短语，不要整句结论
BAD_HEAD = ('以上', '都不', '所有', '无关', '题干', '选项', '正确', '错误', '下列')
BAD_CHAR = ('的', '了', '是', '吗', '呢', '把', '被', '地')
OK_RE = re.compile(r'^[\u4e00-\u9fa5A-Za-z0-9·\-—（）()、/＋+．.\s]{2,22}$')


def terms(sec, limit=14):
    """从正确项里挑像知识点的短语，先严后松。"""
    pool = []
    for q in sec['qs']:
        vals = []
        if q['t'] in ('单项选择题', '多项选择题'):
            vals = [q['o'].get(k, '') for k in q['a']]
        elif q['t'] == '填空题':
            vals = [q['a']]
        for v in vals:
            v = re.sub(r'\s+', '', str(v)).strip('。；，、：')
            if 2 <= len(v) <= 22 and OK_RE.match(v):
                pool.append(v)

    strict, loose = [], []
    seen = set()
    for v in pool:
        if v in seen:
            continue
        seen.add(v)
        if any(h in v[:4] for h in BAD_HEAD):
            continue
        if len(v) <= 12 and not any(c in v for c in BAD_CHAR):
            strict.append(v)
        else:
            loose.append(v)
    out = strict[:limit]
    if len(out) < 4:                       # 严筛太少就放宽，但总数不外溢
        for v in loose:
            if v not in out:
                out.append(v)
            if len(out) >= limit:
                break
    return out


def build(no, name, ch, intro, mnem):
    secs = []
    for i, s in enumerate(ch['sections']):
        ts = terms(s)
        blocks = [
            {'k': 'p', 't': f"本节 {len(s['qs'])} 题。上面地图里的表述是按题目正确项归并出来的，"
                            f"不是教材原话——先用它找感觉，再用题目标定准。"},
        ]
        if i == 0 and mnem:
            blocks.append({'k': 'kj', 'c': mnem,
                           'd': f'本章主线：{intro}' if intro else '本章关键词串联，做题时用它回忆框架。'})
        secs.append({
            'name': s['name'],
            'map': [{'lv': 0, 't': s['name']}] + [{'lv': 1, 't': x} for x in ts],
            'blocks': blocks,
        })

    files = []
    for s in ch['sections']:
        for q in s['qs']:
            f = q.get('src', '')
            if f and f not in files:
                files.append(f)
    secs[-1]['blocks'].append({
        'k': 'tip',
        't': '本章题目来源：' + '；'.join(files) +
             '。本章暂无课件转录稿，先导卡里的表述由题目正确项归并，与教材原文可能有措辞差异。',
    })
    return {'no': no, 'intro': (intro + ' ' if intro else '') +
            '本章先给高频表述速览，再进入分节练习。', 'secs': secs}


def main():
    report = json.load(io.open(os.path.join(ROOT, '_import', 'report.json'), encoding='utf-8'))
    total_term = 0
    for rec in report['chapters']:
        no, name = rec['no'], rec['name']
        if no <= 3:
            continue
        path = os.path.join(AUDIT, f'{no:02d}.json')
        if not os.path.exists(path):
            print('跳过（无审计文件）', no, name)
            continue
        ch = json.load(io.open(path, encoding='utf-8'))
        g = build(no, name, ch, ia.CH_INTRO.get(name, ''), ia.MNEMO.get(name, ''))
        n_term = sum(max(0, len(s['map']) - 1) for s in g['secs'])
        total_term += n_term
        io.open(os.path.join(GUIDE, f'{no}.py'), 'w', encoding='utf-8').write(
            '# -*- coding: utf-8 -*-\n"""第%d章 %s · 高频表述速览（题目归并）"""\n\nGUIDE = ' % (no, name)
            + json.dumps(g, ensure_ascii=False, indent=1) + '\n')
        print(f'{no:02d} {name:14s} {len(g["secs"])} 节 {n_term} 条表述')
    print('合计', total_term, '条')


if __name__ == '__main__':
    main()
