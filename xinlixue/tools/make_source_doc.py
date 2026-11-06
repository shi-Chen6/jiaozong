# -*- coding: utf-8 -*-
"""生成《资料归并说明.md》：把 F:/xinli 的 167 个文件逐个交代去向。

为什么需要这份文件：题库只有 2239 题，但源目录有 165 份 PDF。
哪些进了题库、哪些没进、为什么没进，必须能一眼查到，
否则「全部做进网页」这句话就是空的。

用法：python tools/make_source_doc.py
"""
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SURVEY = os.path.join(ROOT, '_survey.jsonl')
REPORT = os.path.join(ROOT, '_import', 'report.json')
AUDIT = os.path.join(ROOT, 'build_import')

CH13 = {
    1: ('01.心理学概述1 / 02.心理学概述2 课件 + 01.心理学概述分章节题目', 82),
    2: ('03.意识和注意完整版 + 03.意识和注意分章节题目', 99),
    3: ('06.感知觉分章节题目汇总.docx（同名 PDF 无文字层，以 Word 为准）', 108),
}


def stem(f):
    return os.path.splitext(f)[0]


def classify(f, chars, pages=0):
    """未作为题源的文件的用途判定。"""
    if '勘误' in f:
        return '勘误', '已在导入前逐条核对修正相关题目的答案与选项'
    if '挖空' in f or '带背' in f:
        return '挖空带背', '未入库：需要单独的「点开答案」背诵视图，不是客观题'
    if '背诵' in f or '重点' in f or '要点' in f:
        return '背诵/授课重点', '第1–3章已吸收进先导卡；其余章节未逐页转录'
    if any(k in f for k in ('课件', '授课', '上课')):
        return '授课课件', '第1–3章已转录为先导卡；其余章节的知识点在图片里，未逐页转录'
    if re.match(r'^26', f):
        return '综合汇总卷', '与分章节题目大量重合，只用于交叉核对，不重复导入'
    if chars < 600:
        return '弱文字层资料', '文字层几乎为空（图片型），未能可靠转录'
    # 几十上百页、每页文字稀薄 → 是幻灯片（授课课件），不是题目汇总
    if pages >= 15 and chars / max(pages, 1) < 400:
        return '授课课件', '第1–3章已转录为先导卡；其余章节的知识点在图片里，未逐页转录'
    if any(k in f for k in ('题目', '练习')):
        return '重复/旧版题集', '与已采用的章节练习高度重合，未重复导入'
    return '讲义/其他', '未作为题源'


def main():
    rows = [json.loads(x) for x in io.open(SURVEY, encoding='utf-8') if x.strip()]
    rep = json.load(io.open(REPORT, encoding='utf-8'))

    # 已作为题源的文件（审计里存的是 .md 名，这里统一去扩展名）
    used = {}
    for rec in rep['chapters']:
        path = os.path.join(AUDIT, '%02d.json' % rec['no'])
        if not os.path.exists(path):
            continue
        ch = json.load(io.open(path, encoding='utf-8'))
        for s in ch['sections']:
            for q in s['qs']:
                if q.get('src'):
                    used.setdefault(stem(q['src']), set()).add(rec['no'])
    used[stem('06.感知觉分章节题目汇总_2025111309321068.docx')] = {3}

    n_pdf = sum(1 for r in rows if r['f'].lower().endswith('.pdf'))
    n_doc = len(rows) - n_pdf
    L = []
    L.append('# 资料归并说明\n')
    L.append('源目录 `F:/xinli` 共 **%d** 个文件（%d 份 PDF、%d 份 Word、1 个旧版刷题 HTML），'
             'PDF 合计 **%d 页**、可提取文本 **%.1f 万字**。'
             % (len(rows) + 1, n_pdf, n_doc, sum(r.get('pages', 0) for r in rows),
                sum(r.get('chars', 0) for r in rows) / 10000))
    L.append('最终入库 **2239 题 / 34 章 / 79 节**。下面交代每个文件的去向。\n')
    L.append('> 一句话结论：**题目类文件已全部入库；课件类只转录了第 1–3 章，'
             '其余 31 章的先导卡是从题目正确项归并的，不是课件原文。**\n')

    # ---------------- 一、题目来源
    L.append('## 一、已入库：题目来源\n')
    L.append('| 章 | 章名 | 源文件 | 题量 |')
    L.append('|---|---|---|---|')
    for rec in rep['chapters']:
        path = os.path.join(AUDIT, '%02d.json' % rec['no'])
        srcs = []
        if os.path.exists(path):
            ch = json.load(io.open(path, encoding='utf-8'))
            for s in ch['sections']:
                for q in s['qs']:
                    f = q.get('src')
                    if f and f not in srcs:
                        srcs.append(f)
        L.append('| %d | %s | %s | %d |'
                 % (rec['no'], rec['name'],
                    '；'.join(os.path.splitext(x)[0] for x in srcs) or '—', rec['kept']))
    for no in (1, 2, 3):
        L.append('| %d | %s | %s | %d |'
                 % (no, {1: '心理学概述', 2: '意识和注意', 3: '感知觉'}[no], CH13[no][0], CH13[no][1]))
    L.append('')

    # ---------------- 二、未作为题源
    L.append('## 二、未作为题源的文件\n')
    groups = {}
    for r in rows:
        if stem(r['f']) in used:
            continue
        kind, dest = classify(r['f'], r.get('chars', 0), r.get('pages', 0))
        groups.setdefault((kind, dest), []).append(r)

    order = ['重复/旧版题集', '综合汇总卷', '授课课件', '挖空带背',
             '背诵/授课重点', '弱文字层资料', '勘误', '讲义/其他']
    L.append('| 类别 | 份数 | 页数 | 去向 |')
    L.append('|---|---|---|---|')
    total = 0
    for kind in order:
        items = sorted([(k, v) for k, v in groups.items() if k[0] == kind], key=lambda x: x[1][0]['f'])
        if not items:
            continue
        files = [r for k, v in items for r in v]
        total += len(files)
        L.append('| %s | %d | %d | %s |'
                 % (kind, len(files), sum(r.get('pages', 0) for r in files), items[0][0][1]))
    L.append('')
    L.append('合计 **%d** 份未作为题源，%d 份已入库，全部 %d 份有交代。\n'
             % (total, len(used), total + len(used)))

    # ---------------- 三、全量清单
    L.append('## 三、全量文件清单\n')
    L.append('| 文件 | 页 | 字数 | 类别 |')
    L.append('|---|---|---|---|')
    for r in sorted(rows, key=lambda x: x['f']):
        s = stem(r['f'])
        if s in used:
            kind = '✅ 题源（第 %s 章）' % '、'.join(str(x) for x in sorted(used[s]))
        else:
            kind = classify(r['f'], r.get('chars', 0), r.get('pages', 0))[0]
        L.append('| %s | %d | %d | %s |'
                 % (r['f'], r.get('pages', 0), r.get('chars', 0), kind))
    L.append('')

    # ---------------- 四、规则
    L.append('## 四、处理规则\n')
    L.append('1. **答案按「题号区间 + 题号」对齐**，不按 token 顺序硬套——'
             'PDF 里答案区常被水印和分页切断，顺序套会整段错位。')
    L.append('2. **勘误先于导入**：`09.记忆课件和课后练习题勘误`、`42.勘误` 点名的题目'
             '逐条核对后手工修正，再进题库。')
    L.append('3. **完全重复（题干 + 选项都一致）合并**，保留全部来源；'
             '同题干不同选项的保留，因为考法不同。')
    L.append('4. **没有可靠答案的题直接丢弃**并留痕，本轮共丢弃 %d 题，'
             '多为材料分析类（原文答案写「见解析」或缺失）。' % rep['dropped'])
    L.append('5. **材料题 / 简答 / 论述 / 辨析不进单机刷题**：作答方式不同，'
             '塞进来会破坏判分与答题交互。')
    L.append('6. **课件习题不重复搬**：授课课件的配套习题与章节练习汇总重合度约 80%%，'
             '只补章节汇总里没有的新题。')
    L.append('7. **口诀原文照录**，不为了「对上」而改写；对不上知识点的也留着（例如「直系熟」）。\n')

    # ---------------- 五、待办
    L.append('## 五、还没做完的部分\n')
    L.append('| 事项 | 现状 | 影响 |')
    L.append('|---|---|---|')
    L.append('| 第 4–34 章课件逐页转录 | 未做 | 这 31 章的先导卡是「从题目正确项归并」的高频表述，'
             '不是教材原文，措辞可能与课件有差异，页面里已标注 |')
    n_wa = len(groups.get(('挖空带背', '未入库：需要单独的「点开答案」背诵视图，不是客观题'), []))
    L.append('| 挖空材料 → 背诵自测 | 未做 | %d 份挖空/带背材料目前只是 PDF，'
             '没有变成可交互的背诵卡 |' % n_wa)
    L.append('| 综合卷补漏 | 部分 | `26普心题目汇总`（99 页）与分章节题目大量重合，'
             '目前只做了跨文件去重，未逐题比对补漏 |')
    L.append('')

    out = os.path.join(ROOT, '资料归并说明.md')
    io.open(out, 'w', encoding='utf-8').write('\n'.join(L))
    print('→', out)
    print('题源 %d 份 / 未用作题源 %d 份 / 合计 %d' % (len(used), total, total + len(used)))


if __name__ == '__main__':
    main()
