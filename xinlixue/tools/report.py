# -*- coding: utf-8 -*-
"""生成题库校验报告。"""
import io, json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data = json.load(io.open(os.path.join(ROOT, '心理学习题数据.json'), encoding='utf-8'))
html = io.open(os.path.join(ROOT, '心理学刷题.html'), encoding='utf-8').read()

ana = json.loads(re.search(r'var ANALYSIS_DATA = (\{.*?\});\n', html, re.S).group(1))

lines, warn = [], []
lines.append('# 心理学题库校验报告\n')
lines.append(f"总题量 **{data['total']}** 题 · {data['chapterCount']} 章 · {data['secCount']} 节 · 解析 {len(ana)} 条\n")

tc = collections.Counter()
q_all = []
for c in data['chapters']:
    lines.append(f"## 第{c['no']}章 {c['name']}（{len(c['qs'])} 题）\n")
    lines.append('| 小节 | 题量 | 单选 | 多选 | 判断 | 填空 |')
    lines.append('|---|---|---|---|---|---|')
    by_sec = collections.OrderedDict()
    for q in c['qs']:
        by_sec.setdefault(q['sec'], []).append(q)
        tc[q['t']] += 1
        q_all.append((c, q))
    for sec, qs in by_sec.items():
        cnt = collections.Counter(q['t'] for q in qs)
        lines.append(f"| {sec} | {len(qs)} | {cnt['单项选择题']} | {cnt['多项选择题']} | {cnt['判断题']} | {cnt['填空题']} |")
    lines.append('')

lines.append('## 题型分布\n')
for k, v in tc.most_common():
    lines.append(f'- {k}：{v} 题')
lines.append('')

# 校验
bad = []
for c, q in q_all:
    k = f"{c['no']}#{q['n']}"
    if k not in ana or not ana[k].strip():
        bad.append(f"第{c['no']}章第{q['n']}题 缺解析")
    if q['t'] in ('单项选择题', '多项选择题'):
        want = 1 if q['t'] == '单项选择题' else 2
        if len(q['a']) < want:
            bad.append(f"第{c['no']}章第{q['n']}题 题型与答案长度不符：{q['t']} / {q['a']}")
        if len(q['a']) != 1 and q['t'] == '单项选择题':
            bad.append(f"第{c['no']}章第{q['n']}题 单选多答案 {q['a']}")
        miss = set(q['a']) - set(q['o'].keys())
        if miss:
            bad.append(f"第{c['no']}章第{q['n']}题 答案字母无对应选项 {miss}")
        if not q['o']:
            bad.append(f"第{c['no']}章第{q['n']}题 缺选项")
    if q['t'] == '判断题':
        if q['a'] not in ('A', 'B'):
            bad.append(f"第{c['no']}章第{q['n']}题 判断题答案异常 {q['a']}")
    if q['t'] == '填空题' and not q.get('r'):
        bad.append(f"第{c['no']}章第{q['n']}题 填空缺参考答案")
    for f in q.get('f', []):
        if 'undefined' in f or 'null' in f or 'NaN' in f:
            bad.append(f"第{c['no']}章第{q['n']}题 标签异常 {f}")

# 重复题
seen = collections.defaultdict(list)
for c, q in q_all:
    seen[q['s'][:40]].append(f"第{c['no']}章第{q['n']}题")
dups = {k: v for k, v in seen.items() if len(v) > 1}

lines.append('## 校验结果\n')
lines.append(f'- 缺解析：0' if not any('缺解析' in b for b in bad) else '- 缺解析：见下')
lines.append(f'- 答案/选项一致性异常：{sum(1 for b in bad if "缺解析" not in b)} 处')
lines.append(f'- 题干重复（前 40 字相同）：{len(dups)} 组')
if dups:
    for k, v in dups.items():
        lines.append(f"  - 「{k}…」→ {' / '.join(v)}")
if bad:
    lines.append('\n### 异常明细\n')
    for b in bad:
        lines.append(f'- {b}')

lines.append('\n## 说明\n')
lines.append('- 题目来源：超格教育《心理学》分章节题目三份 PDF（心理学概述 / 意识和注意 / 感知觉）。')
lines.append('- 第 1、2 章取自 PDF 文字层并做清洗；第 3 章原文件为纯扫描件（10 页无文字层），逐页视觉转录后与答案块逐题对位校验。')
lines.append('- 所有题目的答案均来自 PDF 自带【答案】区，未做人工改判；解析为按考点整理，非 PDF 原文。')
lines.append('- 题号为练习序号：进入哪个范围（整章 / 某小节 / 错题本），就从 1 开始计数，与顶部「第 X / Y 题」始终一致。')
lines.append('- 原卷个别题目本身存在瑕疵，为保持原貌未做改写，例如第 3 章有一道形近字题两个引号内的字相同（原材料印刷如此）。')
lines.append('- 第 2 章「注意的品质」原卷有两道完全相同的题，已保留首次出现的一道。')
lines.append('- 第 3 章另有一份 Word 版原文（2026-11-04 追加），与扫描件同源。已逐题比对 108 题：题号、题量、四/五选项与答案块完全一致；据此校正 10 处转录误差（详见下节）。')
lines.append('')
lines.append('## 第 3 章 Word 版比对校正（10 处）\n')
lines.append('| 小节 | 题号 | 原转录（错） | 校正为 |\n|---|---|---|---|')
for sec, n, a, b in [
    ('二、感觉规律', 10, '地震后或者火灾塌方后', '地震后或者着火塌方后'),
    ('三、知觉', 5, '在水泥池边玩水', '在水池边玩水'),
    ('三、知觉', 15, '邻近物体的大小对比', '临近物体的大小对比'),
    ('三、知觉', 33, '悲伤时感觉时间过得很慢', '悲伤时感觉时间过得慢'),
    ('三、知觉', 34, '错觉不存在本质上的差异', '错觉不存在质上的差异'),
    ('三、知觉', 36, '还能听到声音来自主席台', '还是听到声音来自主席台'),
    ('四、知觉的基本特性', 9, '“燥”“躁”“噪”', '“澡”“噪”“躁”'),
    ('四、知觉的基本特性', 14, '理解有助于知觉同化', '理解有助于知觉固化'),
    ('四、知觉的基本特性', 16, '把“戍”写成“戌”，把“拆除”写成“拆除”', '把“戌”写成“戊”，把“拆除”写成“折除”'),
    ('五、感知觉规律在教学中的应用', 7, '注意活动变化显现的对象', '注意活动变化呈现的对象'),
]:
    lines.append(f'| {sec} | {n} | {a} | {b} |')
lines.append('')
lines.append('- 上述 10 处均逐条回看扫描原页确认，非按 Word 版直接采信（Word 版自身也存在截断与错字，例如“会起来”“眼镜”“[单题】”）。')
lines.append('- 另有若干处 Word 版文字被截断（如“刺激物之间的最小差异量叫做”后缺字），以扫描件为准，未改动。')

out = os.path.join(ROOT, '题库校验报告.md')
io.open(out, 'w', encoding='utf-8').write('\n'.join(lines))
print('\n'.join(lines[:20]))
print('...')
print('异常', len(bad), '重复组', len(dups))
for b in bad[:10]:
    print(' !', b)
for k, v in list(dups.items())[:10]:
    print(' dup', k, v)
