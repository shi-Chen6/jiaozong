# -*- coding: utf-8 -*-
"""刷题页自检：结构一致性 + 生成校验报告。

用法：
    python verify.py 心理学刷题.html                  # 只体检
    python verify.py 心理学刷题.html -o 校验报告.md    # 顺带出报告

检查项（任一项不通过都会在末尾以「异常 N 处」汇总）：
    1. 单选题只有一个答案字母；多选题至少两个
    2. 答案字母都能在该题选项里找到
    3. 判断题答案只有 A/B 且选项是「正确/错误」
    4. 填空题有参考答案
    5. 每题都有解析且非空
    6. 标签里没有 undefined / null / NaN
    7. 题干重复（前 40 字相同）分组列出
    8. 解析必须是四段式（答案解析 / 知识点讲解 / 解题思路 / 记忆口诀），顺序固定
    9. 解析首段给出的答案必须与题目答案一致（防止解析与题目错位）
"""
import argparse
import collections
import io
import json
import os
import re
import sys

TYPES = ('单项选择题', '多项选择题', '判断题', '填空题')

# 四段式：小节标题 + 顺序，必须逐字一致
ANA_SECTIONS = ('🎯 答案解析', '📚 知识点讲解', '💡 解题思路', '🧠 记忆口诀')
ANA_SHORT = 180      # 可见字数下限（低于此值只提示，不判异常）
ANA_LONG = 900       # 可见字数上限（只提示）


def read_var(html, name):
    """从 HTML 里精确取出 `var NAME = {...};` 的 JSON。"""
    i = html.find(f'var {name} = ')
    if i < 0:
        raise SystemExit(f'[verify] HTML 里找不到 var {name}')
    i += len(f'var {name} = ')
    obj, _ = json.JSONDecoder().raw_decode(html[i:])
    return obj


def visible_len(s):
    """去掉 HTML 标签与空白后的可见字数。"""
    s = re.sub(r'<h3>.*?</h3>', '', s)
    s = re.sub(r'<[^>]+>', '', s)
    return len(re.sub(r'\s+', '', s))


def check_ana(tag, q, text, bad, warn):
    """四段式结构 + 答案一致性 + 篇幅。"""
    heads = re.findall(r'<h3>(.*?)</h3>', text)
    if heads != list(ANA_SECTIONS):
        got = ' / '.join(heads) if heads else '无 h3'
        miss = [s for s in ANA_SECTIONS if s not in heads]
        if miss:
            bad.append(f'{tag} 解析缺段落：{"、".join(miss)}（实得：{got}）')
        elif len(heads) != 4:
            bad.append(f'{tag} 解析段数 {len(heads)} ≠ 4（实得：{got}）')
        else:
            bad.append(f'{tag} 解析段落顺序不对（实得：{got}）')

    head = re.sub(r'<[^>]+>', '', text.split('<h3>📚')[0])
    if q['t'] == '填空题':
        if '参考答案' not in head:
            warn.append(f'{tag} 填空解析未见「参考答案」')
    elif q['t'] == '判断题':
        m = re.search(r'本题判断为\s*(正确|错误)', head)
        want = '正确' if q['a'] == 'A' else '错误'
        if not m:
            warn.append(f'{tag} 判断解析未写明「本题判断为 …」')
        elif m.group(1) != want:
            bad.append(f'{tag} 解析判为「{m.group(1)}」，与答案 {q["a"]} 不符')
    else:
        m = re.search(r'正确答案为\s*([A-E]+)', head)
        if not m:
            warn.append(f'{tag} 解析未写明「正确答案为 …」')
        elif m.group(1) != q['a']:
            bad.append(f'{tag} 解析答案 {m.group(1)} ≠ 题目答案 {q["a"]}')

    n = visible_len(text)
    if n < ANA_SHORT:
        warn.append(f'{tag} 解析偏短：{n} 字')
    elif n > ANA_LONG:
        warn.append(f'{tag} 解析偏长：{n} 字')


GBLOCK = ('h', 'p', 'ul', 'table', 'tip', 'kj', 'img')


def check_guide(guide, data):
    """先导知识：结构合法性 + 覆盖统计。"""
    bad, warn = [], []
    stat = {'chapters': 0, 'secs': 0, 'blocks': 0, 'tables': 0, 'rows': 0,
            'kj': [], 'chs': [], 'imgs': 0}
    if not guide:
        return bad, warn, stat
    names = {c['no']: c['name'] for c in data['chapters']}
    for k, g in guide.items():
        cn = int(k)
        tag = f'先导第{cn}章'
        if cn not in names:
            bad.append(f'{tag} 题库里没有这一章')
            continue
        if g.get('no') != cn:
            warn.append(f'{tag} no 字段 {g.get("no")} ≠ 键 {cn}')
        secs = g.get('secs') or []
        if not secs:
            bad.append(f'{tag} 没有小节')
            continue
        stat['chapters'] += 1
        stat['chs'].append(cn)
        for si, s in enumerate(secs):
            st = f'{tag}第{si + 1}节'
            if not (s.get('name') or '').strip():
                bad.append(f'{st} 小节名为空')
            if not (s.get('map') or []):
                warn.append(f'{st} 没有考点地图')
            for m in s.get('map') or []:
                if not (m.get('t') or '').strip():
                    bad.append(f'{st} 考点地图有空标题')
                if m.get('lv') not in (0, 1, 2, None):
                    warn.append(f'{st} 考点层级异常：{m.get("lv")}')
            blocks = s.get('blocks') or []
            if not blocks:
                warn.append(f'{st} 没有内容块')
            stat['secs'] += 1
            for bi, b in enumerate(blocks):
                bt = f'{st}块{bi + 1}'
                kind = b.get('k')
                if kind not in GBLOCK:
                    bad.append(f'{bt} 未知块类型：{kind}')
                    continue
                stat['blocks'] += 1
                if kind in ('h', 'p', 'tip'):
                    if not (b.get('v') or str(b.get('t') or '')).strip():
                        warn.append(f'{bt} {kind} 内容为空')
                elif kind == 'ul':
                    items = b.get('items') or []
                    if not items:
                        bad.append(f'{bt} 列表为空')
                    for it in items:
                        if not str(it).strip():
                            bad.append(f'{bt} 列表项为空')
                elif kind == 'table':
                    head, rows = b.get('head') or [], b.get('rows') or []
                    if not head:
                        bad.append(f'{bt} 表格缺表头')
                    if not rows:
                        bad.append(f'{bt} 表格无数据行')
                    for ri, r in enumerate(rows):
                        if len(r) != len(head):
                            bad.append(f'{bt} 第{ri + 1}行列数 {len(r)} ≠ 表头 {len(head)}')
                    stat['tables'] += 1
                    stat['rows'] += len(rows)
                elif kind == 'kj':
                    c, d = b.get('c'), b.get('d')
                    if not (str(c or '').strip() and str(d or '').strip()):
                        bad.append(f'{bt} 口诀缺「口诀」或「解释」')
                    else:
                        stat['kj'].append((cn, c, d))
                elif kind == 'img':
                    src = str(b.get('src') or '')
                    if not src.startswith('data:image/'):
                        bad.append(f'{bt} 插图未内嵌（src 应为 data:image/...;base64,...）')
                    elif len(src) > 160 * 1024:
                        warn.append(f'{bt} 插图 base64 偏大（{len(src)//1024} KB）')
                    if not str(b.get('cap') or '').strip():
                        warn.append(f'{bt} 插图缺图注 cap')
                    stat['imgs'] += 1
    return bad, warn, stat


def check(data, ana):
    bad, warn = [], []
    all_q = []
    for c in data['chapters']:
        for q in c['qs']:
            all_q.append((c, q))

    for c, q in all_q:
        tag = f"第{c['no']}章第{q['n']}题"
        t, a, o = q['t'], q['a'], q.get('o') or {}
        if t not in TYPES:
            warn.append(f'{tag} 题型未知：{t}')
        if t == '单项选择题':
            if len(a) != 1:
                bad.append(f'{tag} 单选却给了 {len(a)} 个答案：{a}')
        elif t == '多项选择题':
            if len(a) < 2:
                bad.append(f'{tag} 多选只有 {len(a)} 个答案：{a}')
        elif t == '判断题':
            if a not in ('A', 'B'):
                bad.append(f'{tag} 判断题答案异常：{a}')
            if set(o) != {'A', 'B'}:
                warn.append(f'{tag} 判断题选项不是两项：{list(o)}')
        elif t == '填空题':
            if not (q.get('r') or '').strip():
                bad.append(f'{tag} 填空缺参考答案')
        if t != '填空题':
            miss = set(a) - set(o)
            if miss:
                bad.append(f'{tag} 答案字母无对应选项：{miss}')
            if not o:
                bad.append(f'{tag} 缺选项')
            for k, v in o.items():
                if not (v or '').strip():
                    bad.append(f'{tag} 选项 {k} 为空')
        if not (q.get('s') or '').strip():
            bad.append(f'{tag} 题干为空')
        elif len(q['s']) < 6:
            warn.append(f'{tag} 题干过短：{q["s"]}')
        for f in q.get('f') or []:
            if re.search(r'undefined|null|NaN', f, re.I):
                bad.append(f'{tag} 标签异常：{f}')
        if ana:
            k = f"{c['no']}#{q['n']}"
            text = ana.get(k) or ''
            if not text.strip():
                bad.append(f'{tag} 缺解析')
            else:
                check_ana(tag, q, text, bad, warn)

    # 题干重复
    seen = collections.defaultdict(list)
    for c, q in all_q:
        seen[q['s'][:40]].append(f"第{c['no']}章第{q['n']}题")
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    return bad, warn, dups, all_q


def report(data, ana, bad, warn, dups, all_q, gstat=None):
    L = []
    L.append(f"# {data['name']}题库校验报告\n")
    L.append(f"总题量 **{data['total']}** 题 · {data['chapterCount']} 章 · "
             f"{data['secCount']} 节 · 解析 {len(ana)} 条\n")
    if data.get('source'):
        L.append(f"来源：{data['source']}\n")

    tc = collections.Counter()
    for c in data['chapters']:
        L.append(f"## 第{c['no']}章 {c['name']}（{len(c['qs'])} 题）\n")
        L.append('| 小节 | 题量 | 单选 | 多选 | 判断 | 填空 |')
        L.append('|---|---|---|---|---|---|')
        by_sec = collections.OrderedDict()
        for q in c['qs']:
            by_sec.setdefault(q['sec'], []).append(q)
            tc[q['t']] += 1
        for sec, qs in by_sec.items():
            cnt = collections.Counter(q['t'] for q in qs)
            L.append(f"| {sec} | {len(qs)} | {cnt['单项选择题']} | "
                     f"{cnt['多项选择题']} | {cnt['判断题']} | {cnt['填空题']} |")
        L.append('')

    L.append('## 题型分布\n')
    for k, v in tc.most_common():
        L.append(f'- {k}：{v} 题')
    L.append('')

    # 解析质量：四段齐全率 / 篇幅 / 答案一致性
    if ana:
        full = 0
        lens = []
        for c, q in all_q:
            t = ana.get(f"{c['no']}#{q['n']}") or ''
            if re.findall(r'<h3>(.*?)</h3>', t) == list(ANA_SECTIONS):
                full += 1
            if t:
                lens.append(visible_len(t))
        n = len(all_q)
        L.append('## 解析质量\n')
        L.append(f'- 四段式齐全：{full}/{n} 题')
        if lens:
            L.append(f'- 可见字数：最少 {min(lens)} / 平均 {sum(lens)//len(lens)} / '
                     f'最多 {max(lens)}')
        L.append(f'- 解析与答案一致：{n - sum(1 for b in bad if "解析答案" in b or "解析判为" in b)}/{n} 题')
        L.append('')

    # 先导知识
    if gstat and gstat['chapters']:
        L.append('## 先导知识\n')
        L.append(f"- 覆盖章节：{gstat['chapters']}/{data['chapterCount']} 章"
                 f"（{'、'.join(f'第{c}章' for c in sorted(gstat.get('chs') or []))}）")
        L.append(f"- 小节 {gstat['secs']} 个 · 内容块 {gstat['blocks']} 个")
        L.append(f"- 对比表 {gstat['tables']} 张（{gstat['rows']} 行）"
                 f" · 记忆口诀 {len(gstat['kj'])} 条")
        if gstat['kj']:
            L.append('\n### 先导知识里的口诀\n')
            L.append('| 章 | 口诀 | 对应知识点 |')
            L.append('|---|---|---|')
            for cn, c, d in gstat['kj']:
                d2 = re.sub(r'<[^>]+>', '', str(d)).replace('|', '／')
                L.append(f'| 第{cn}章 | **{c}** | {d2} |')
        L.append('')

    L.append('## 校验结果\n')
    L.append(f'- 一致性异常：{len(bad)} 处')
    L.append(f'- 提示项：{len(warn)} 处')
    L.append(f'- 题干重复（前 40 字相同）：{len(dups)} 组')
    if bad:
        L.append('\n### 异常明细\n')
        for b in bad:
            L.append(f'- {b}')
    if dups:
        L.append('\n### 重复题\n')
        for k, v in dups.items():
            L.append(f'- 「{k}…」→ {" / ".join(v)}')
    if warn:
        L.append('\n### 提示项\n')
        for w in warn[:60]:
            L.append(f'- {w}')
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('html')
    ap.add_argument('-o', '--report', default='')
    a = ap.parse_args()

    html = io.open(a.html, encoding='utf-8').read()
    data = read_var(html, 'DATA')
    try:
        ana = read_var(html, 'ANALYSIS_DATA')
    except SystemExit:
        ana = {}
    try:
        guide = read_var(html, 'GUIDE_DATA')
    except SystemExit:
        guide = {}

    bad, warn, dups, all_q = check(data, ana)
    gbad, gwarn, gstat = check_guide(guide, data)
    bad += gbad
    warn += gwarn
    print(f"题库 {data['total']} 题 / {data['chapterCount']} 章 / "
          f"{data['secCount']} 节；解析 {len(ana)} 条")
    if gstat['chapters']:
        print(f"先导知识 {gstat['chapters']} 章 / {gstat['secs']} 节 / "
              f"{gstat['blocks']} 块 / {gstat['tables']} 表 / "
              f"{len(gstat['kj'])} 口诀 / {gstat['imgs']} 插图")
    print(f'异常 {len(bad)} 处，提示 {len(warn)} 处，重复 {len(dups)} 组')
    for b in bad[:30]:
        print('  !', b)
    if len(bad) > 30:
        print(f'  ... 另有 {len(bad) - 30} 处')

    if a.report:
        text = report(data, ana, bad, warn, dups, all_q, gstat)
        io.open(a.report, 'w', encoding='utf-8').write(text)
        print('→', a.report)

    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
