# -*- coding: utf-8 -*-
"""docx 原文与已建题库逐题比对（按原卷题号切分，容忍段落黏连）"""
import io, json, re, difflib

RAW = 'D:/workdata/2026-11-04-10-30-50/xinli/src/06_docx.txt'
BANK = 'D:/workdata/2026-11-04-10-30-50/xinli/心理学习题数据.json'
SEC = re.compile(r'^[一二三四五六七八九十]\s*[、.]\s*')
QMARK = re.compile(r'【[^】]{0,8}】|\[[^\]]{0,8}\]')


def norm(s):
    s = re.sub(r'\s+', '', s or '')
    for a, b in [('，', ','), ('。', '.'), ('（', '('), ('）', ')'), ('；', ';'), ('：', ':'),
                 ('“', '"'), ('”', '"'), ('‘', "'"), ('’', "'"), ('—', '-'), ('–', '-')]:
        s = s.replace(a, b)
    return s.lower()


def sections():
    """返回 [{name, text}]，答案区丢弃"""
    out, cur, buf, in_ans = [], None, [], False
    for line in io.open(RAW, encoding='utf-8').read().split('\n'):
        t = line.strip()
        if not t:
            continue
        if t.startswith('第') and '章' in t[:4]:
            continue
        if t.startswith('【答案】'):
            in_ans = True
            continue
        if SEC.match(t) and len(t) < 24:
            in_ans = False
            cur = {'name': re.sub(r'\s+', '', t), 'lines': []}
            out.append(cur)
            continue
        if cur and not in_ans:
            cur['lines'].append(t)
    for s in out:
        s['text'] = ' '.join(s['lines'])
    return out


def split_questions(text):
    """用「题号. + 紧跟题型标记」作为切分点"""
    marks = []
    for m in re.finditer(r'(?<![\d.．])(\d{1,2})\s*[.．]?\s*(?=[\[【])', text):
        marks.append((int(m.group(1)), m.start(), m.end()))
    # 允许没有题型标记的题（少数），按题号递增补
    items = []
    for i, (n, st, en) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(text)
        items.append({'n': n, 'text': text[en:end].strip()})
    return items


def split_opts(text):
    t = QMARK.sub(' ', text)
    ms = list(re.finditer(r'(?<![A-Za-z])([A-E])\s*[.．、]\s*', t))
    if not ms:
        return t.strip(), {}
    stem = t[:ms[0].start()]
    opts = {}
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(t)
        opts[m.group(1)] = t[m.end():end].strip()
    return stem.strip(), opts


def main():
    secs = sections()
    d = json.load(io.open(BANK, encoding='utf-8'))
    bank = d['chapters'][2]['qs']
    groups, order = {}, []
    for q in bank:
        if q['sec'] not in groups:
            groups[q['sec']] = []
            order.append(q['sec'])
        groups[q['sec']].append(q)

    for sec, key in zip(secs, order):
        items = split_questions(sec['text'])
        nums = [i['n'] for i in items]
        print('\n' + '=' * 74)
        print(f"{key}   docx {len(items)} 题 号={nums}")
        qs = groups[key]
        print(f"   题库 {len(qs)} 题")
        if nums != list(range(1, len(nums) + 1)):
            miss = [x for x in range(1, max(nums + [0]) + 1) if x not in nums]
            print('   !! 切分缺失题号:', miss)
        byn = {q['n']: q for q in qs}
        dmap = {it['n']: it for it in items}
        for i, item in enumerate(items):
            q = qs[item['n'] - 1] if item['n'] - 1 < len(qs) else None
            if q is None:
                print(f'   !! 题库无第{i + 1}题')
                continue
            stem, opts = split_opts(item['text'])
            a, b = norm(stem), norm(q['s'])
            od = {k: v for k, v in opts.items() if norm(v) != norm(q['o'].get(k, ''))}
            sim = difflib.SequenceMatcher(None, a, b).ratio()
            flag = '  ' if (a == b and not od) else '!!'
            if flag == '!!':
                print(f'{flag} #{item["n"]} 相似{sim:.2f}')
                if a != b:
                    print('    docx:', stem[:140])
                    print('    bank:', q['s'][:140])
                for k in sorted(od):
                    print(f'    [{k}] docx={od[k][:85]!r}')
                    print(f'    [{k}] bank={q["o"].get(k,"")[:85]!r}')


if __name__ == '__main__':
    main()
