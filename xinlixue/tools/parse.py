# -*- coding: utf-8 -*-
"""把 pdf 提取出的 markdown 解析成结构化题目 JSON。"""
import json, re, sys, io, os

CJK = r'\u4e00-\u9fa5'

def norm_spaces(s):
    prev = None
    while prev != s:
        prev = s
        s = re.sub(rf'(?<=[{CJK}])\s+(?=[{CJK}])', '', s)
        s = re.sub(rf'(?<=[{CJK}）】》”」])\s+(?=[{CJK}（【《“「\d])', '', s)
        s = re.sub(rf'(?<=[\d）】])\s+(?=[{CJK}])', '', s)
    s = re.sub(r'\s+(?=[，。、；：？！）】”」])', '', s)
    s = re.sub(r'(?<=[，。、；：？（【“「])\s+', '', s)
    s = re.sub(r'\s*\n\s*', ' ', s)
    s = re.sub(r'[ \t]{2,}', ' ', s)
    return s.strip()

def clean_lines(text):
    out = []
    for ln in text.split('\n'):
        t = ln.strip()
        if not t:
            continue
        if t.startswith('<!--'):
            continue
        if re.fullmatch(r'\d{1,3}', t):
            continue
        t = t.replace('\\[', '[').replace('\\]', ']').replace('\\_', '_').replace('\\', '')
        out.append(t)
    return out

HEAD = re.compile(rf'^#*\s*([一二三四五六七八九十]+)\s*[、.．]\s*(.+)$')

def split_sections(lines):
    secs, cur, buf = [], None, []
    for ln in lines:
        m = HEAD.match(ln)
        if m and len(ln) < 40:
            if buf:
                secs.append((cur, '\n'.join(buf)))
            cur, buf = f'{m.group(1)}、{m.group(2).strip()}', []
            continue
        buf.append(ln)
    if buf:
        secs.append((cur, '\n'.join(buf)))
    return [s for s in secs if s[1].strip()]

QNUM = re.compile(
    r'(?<![\d.．])(?:(\d{1,2})\s*[】］\]【\[]?\s*[.．]'
    r'|(\d{1,2})(?=\s*[【\[]\s*[^】\]]{0,8}?(?:单选|多选|判断|填空)))')

TYPE_MARK = re.compile(
    r'[【\[]\s*(?:(\d{2})\s*)?([^】\]]{0,12}?(单选|多选|判断|填空|名词解释|简答|论述|辨析)[^】\]]{0,12}?)\s*[】\]]'
    r'|[（(]\s*(单选|多选|判断|填空)\s*[）)]'
    r'|^(单选|多选|判断|填空)\s*[】\]]')

OPT = re.compile(r'(?<![A-Za-z\u4e00-\u9fa5])([A-E])\s*[.．]\s*')

def pick_questions(body):
    ms, seq, last = list(QNUM.finditer(body)), [], 0
    for m in ms:
        n = int(m.group(1) or m.group(2))
        if n == last + 1 or (last == 0 and n == 1):
            seq.append((n, m)); last = n
        elif 1 < n - last <= 3:
            seq.append((n, m)); last = n
    out = []
    for i, (n, m) in enumerate(seq):
        end = seq[i + 1][1].start() if i + 1 < len(seq) else len(body)
        out.append((n, body[m.end():end]))
    return out

def strip_answers(body):
    i = body.find('【答案】')
    return (body[:i], body[i:]) if i >= 0 else (body, '')

def parse_type(text):
    m = TYPE_MARK.search(text[:80])
    if not m:
        return None, text, ''
    kind = m.group(3) or m.group(4) or m.group(5)
    year = m.group(1) or ''
    raw = m.group(2) or kind
    tags = []
    if year:
        tags.append(year + '年')
    extra = raw.replace(kind, '')
    extra = re.sub(r'\d{2}|年|题|：|:', '', extra).strip()
    t = {'单选': '单项选择题', '多选': '多项选择题',
         '判断': '判断题', '填空': '填空题'}.get(kind, kind)
    if extra:
        tags.append(extra)
    return t, text[:m.start()] + text[m.end():], '·'.join(tags)

def split_options(text):
    ms = list(OPT.finditer(text))
    if not ms:
        return text, {}
    stem, opts = text[:ms[0].start()], {}
    for i, m in enumerate(ms):
        if m.group(1) in opts:
            break
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        opts[m.group(1)] = text[m.end():end].strip()
    for letter in 'ABCDE':
        if letter in opts or chr(ord(letter) - 1) not in opts:
            continue
        prev = chr(ord(letter) - 1)
        tx = opts[prev]
        m = re.search(rf'(?<![A-Za-z]){letter}(?=\s*[{CJK}\d])', tx)
        if m and m.start() > 0:
            opts[prev] = tx[:m.start()].strip()
            opts[letter] = tx[m.end():].strip()
            continue
        # 选项与前文黏连，如「C.反射弧D.小脑」
        m = re.search(rf'(?<![A-Za-z]){letter}\s*[.．]\s*', tx)
        if m and m.start() > 0:
            opts[prev] = tx[:m.start()].strip()
            opts[letter] = tx[m.end():].strip()
    return stem, {k: opts[k] for k in sorted(opts)}

ANS_RANGE = re.compile(r'(\d{1,2})\s*[-—–~至]\s*(\d{1,2})\s*[：:]')

def parse_answers(block):
    ans = {}
    if not block:
        return ans
    body = block.split('【答案】', 1)[1]
    ms = list(ANS_RANGE.finditer(body))
    for i, m in enumerate(ms):
        a, b = int(m.group(1)), int(m.group(2))
        end = ms[i + 1].start() if i + 1 < len(ms) else len(body)
        chunk = body[m.end():end]
        items = [x.strip() for x in re.split(r'[；;。]', chunk) if x.strip()]
        if len(items) != b - a + 1:
            print(f'  [!] 答案区间 {a}-{b} 实际 {len(items)} 项: {items}', file=sys.stderr)
        for k, it in enumerate(items):
            ans[a + k] = it
    return ans

TAGW = re.compile(r'^[【\[]([^】\]]{2,8})[】\]]')

def build(md_path):
    raw = io.open(md_path, encoding='utf-8').read()
    lines = clean_lines(raw)
    if lines and '章' in lines[0]:
        lines = lines[1:]
    chapters = []
    for title, body in split_sections(lines):
        body, ans_block = strip_answers(body)
        ans = parse_answers(ans_block)
        qs, bad = [], []
        for n, blk in pick_questions(body):
            blk = norm_spaces(blk)
            t, rest, tag = parse_type(blk)
            rest = norm_spaces(rest)
            stem, opts = split_options(rest)
            stem = norm_spaces(stem)
            stem = re.sub(r'^[）)、，,。\s]+', '', stem)
            tags = [tag] if tag else []
            while True:
                m = TAGW.match(stem)
                if not m:
                    break
                w = m.group(1)
                if any(k in w for k in ('单选', '多选', '判断', '填空')):
                    stem = stem[m.end():].strip()
                    continue
                tags.append(w)
                stem = stem[m.end():].strip()
            if t is None:
                t = '单项选择题' if opts else '填空题'
            q = {'n': n, 't': t, 's': stem, 'o': opts, 'a': '', 'raw': ans.get(n, '')}
            tag = '·'.join(x for x in tags if x)
            if tag:
                q['tag'] = tag
            qs.append(q)
        for q in qs:
            raw_a = q.pop('raw')
            s = re.sub(r'\s', '', raw_a)
            if q['t'] == '判断题':
                if s in ('√', '✓', '对', '正确'):
                    q['a'] = 'A'
                elif s in ('×', 'x', 'X', '错', '错误', '╳'):
                    q['a'] = 'B'
                else:
                    bad.append((q['n'], '判断题答案异常', raw_a))
                q['o'] = {'A': '正确', 'B': '错误'}
            elif q['t'] == '填空题':
                q['s'] = re.sub(r'[_＿]{2,}', '（　）', q['s'])
                q['o'], q['a'] = {}, raw_a
                if not raw_a:
                    bad.append((q['n'], '填空缺答案', ''))
            else:
                letters = ''.join(sorted(set(re.findall(r'[A-E]', s))))
                q['a'] = letters
                if not letters:
                    bad.append((q['n'], '选择题答案异常', raw_a))
                elif len(letters) > 1 and q['t'] == '单项选择题':
                    q['t'] = '多项选择题'
                if letters and set(letters) - set(q['o'].keys()):
                    bad.append((q['n'], '答案字母超出选项', raw_a))
                if not q['o']:
                    bad.append((q['n'], '缺选项', ''))
            if not q['s']:
                bad.append((q['n'], '题干为空', ''))
        chapters.append({'title': title, 'qs': qs, 'bad': bad, 'ans': ans})
    return chapters

if __name__ == '__main__':
    chs = build(sys.argv[1])
    total = 0
    for c in chs:
        total += len(c['qs'])
        print(f"== {c['title']}  {len(c['qs'])} 题  答案项 {len(c['ans'])}")
        for b in c['bad']:
            print('   !', b)
    print('合计', total)
