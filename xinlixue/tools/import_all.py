# -*- coding: utf-8 -*-
"""把 F:/xinli 的章节练习汇总批量并入题库。

设计原则
--------
1. 章节练习汇总优先；授课课件里的配套习题不重复搬。
2. 只收单选 / 多选 / 判断 / 填空；材料题、简答、分析题另册处理。
3. 答案按「区间 + 题号」对齐，不按 token 顺序硬套——PDF 常有跨页错位。
4. 没有可靠答案的题直接丢弃，并在 _import/report.json 里留痕。
5. 完全重复（题干 + 选项一致）合并；同题干不同选项保留。

用法：python tools/import_all.py
产物：src/NN.md、ana/NN.py、build_import/NN.json、_import/report.json
"""
import io
import json
import os
import re
import runpy
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, '_import_test', 'raw')
SRC = os.path.join(ROOT, 'src')
ANA = os.path.join(ROOT, 'ana')
AUDIT = os.path.join(ROOT, 'build_import')

sys.path.insert(0, r'C:\Users\1\.workbuddy\skills\quiz-web-builder\scripts')
import parse as qp  # noqa: E402

# ---------------------------------------------------------------- 章节与来源
# (章号, 章名, [(源文件名, 小节名或 None)])
MANIFEST = [
    (4, '记忆', [('09.记忆题目汇总最后版_2025112013482030.md', None)]),
    (5, '表象与想象', [('11.想象与表象的汇总题目_202511210907417.md', None)]),
    (6, '思维', [('12.思维题目汇总版_202511241338303.md', None)]),
    (7, '情绪情感', [('14.情绪情感章节练习题汇总_2025112709024690.md', None)]),
    (8, '意志', [('15.意志课后练习题汇总_2025112920005978.md', None)]),
    (9, '个性倾向性', [('17.个体倾向性练习题汇总_2025120116024451.md', None)]),
    (10, '能力', [('19.26能力分章节题目_2025120709410080.md', None)]),
    (11, '人格', [('21.26人格练习题_2025120916021536.md', None)]),
    (12, '社会心理', [('23.26社会心理题目章节汇总_2025121408532193.md', None)]),
    (13, '教育心理学概述', [('25.教育心理学概述章节练习题_2025121709091814.md', None)]),
    (14, '学生心理发展概述', [('26.学生心理概述章节练习题_2025121816051698.md', None)]),
    (15, '皮亚杰认知发展', [('28.26皮亚杰章节练习题_2025122117305562.md', None)]),
    (16, '维果斯基', [('28.26维果斯基章节练习题_2025122117311048.md', None)]),
    (17, '社会性发展', [('30.26社会性发展的题目汇总_2025122609033664.md', None)]),
    (18, '个别差异与因材施教', [('31.26个别差异与因材施教题目汇总_2025122509024342.md', None)]),
    (19, '学习概述', [('33.26学习概述题目汇总_2025122816101799.md', None)]),
    (20, '行为主义学习理论', [
        ('35.26行为主义+前三个人物汇总题目_2026010209095377.md', '一、行为主义总论与前三个人物'),
        ('34.26斯金纳练习题汇总_202601011658266.md', '二、斯金纳的操作性条件作用'),
        ('35.26班杜拉题目汇总_2026010309012797.md', '三、班杜拉的社会学习理论'),
    ]),
    (21, '认知主义学习理论', [('37.26认知主义章节题目汇总_2026010409001345.md', None)]),
    (22, '建构主义学习理论', [('39.26建构主义题目汇总_2026010809021424.md', None)]),
    (23, '人本主义学习理论', [('39.26人本主义章节练习题_2026010911075195.md', None)]),
    (24, '学习动机', [('42.26学习动机章节练习题汇总_2026011309023024.md', None)]),
    (25, '学习策略', [('43.26学习策略章节练习题_2026011611305332.md', None)]),
    (26, '学习迁移', [('45.26学习迁移章节练习题_2026011820382036.md', None)]),
    (27, '知识的学习', [('46.26知识学习章节练习题_2026012109021432.md', None)]),
    (28, '技能学习', [('47.26技能学习章节练习题_2026012311352536.md', None)]),
    (29, '态度与品德', [('49.26态度与品德章节练习题_202601260905427.md', None)]),
    (30, '问题解决与创造性', [('52.26问题解决与创造性章节练习题汇总_2026012909021835.md', None)]),
    (31, '心理健康', [('53.26教师心理特征与心理健康练习题_2026020108585843.md', None)]),
    (32, '教师专业成长', [('53.26教师成长与教育综合练习题_2026020116033640.md', None)]),
    (33, '教学设计', [('54.26教学设计练习题汇总_2026020216033664.md', None)]),
    (34, '课堂管理', [('54.26课堂管理练习题汇总_2026020216141252.md', None)]),
]

CH_INTRO = {
    '记忆': '记忆是经验的积累与保存，主线是「编码—存储—提取」，按保持时间分为瞬时、短时、长时三级。',
    '表象与想象': '表象是感知留下的形象痕迹，想象是对表象的加工改造；两者常以「是否有新形象」区分。',
    '思维': '思维的两大特征是概括性与间接性，基本过程包括分析与综合、比较与分类、抽象与概括、具体化。',
    '情绪情感': '情绪情感由主观体验、生理唤醒和外部表现构成，核心考点是功能、分类与情绪理论。',
    '意志': '意志是有意识地确立目的、调节行动、克服困难的心理过程，重点在意志行动的两个阶段与四种品质。',
    '个性倾向性': '个性倾向性是人进行活动的基本动力，包括需要、动机、兴趣、信念、理想、价值观等。',
    '能力': '能力是顺利完成活动并直接影响效率的个性心理特征；智力是能力的核心，重点在结构理论与测量。',
    '人格': '人格是构成思想、情感与行为特有模式的稳定心理品质，核心是气质、性格与自我调控系统。',
    '社会心理': '社会心理研究个体与群体在社会情境中的心理与行为，重点是态度、印象、群体心理与群体动力。',
    '教育心理学概述': '教育心理学研究教育教学情境中学与教的心理规律，重点是研究对象、发展历程与研究方法。',
    '学生心理发展概述': '学生心理发展具有连续性与阶段性、定向性与顺序性、不平衡性、差异性，重点是各年龄阶段特征。',
    '皮亚杰认知发展': '皮亚杰用图式、同化、顺应、平衡解释认知发展，四阶段是感知运动、前运算、具体运算、形式运算。',
    '维果斯基': '维果斯基强调社会文化对高级心理机能的作用，核心是最近发展区、教学与发展关系、内化与支架。',
    '社会性发展': '社会性发展关注个体在社会关系中的成长，重点是弗洛伊德、埃里克森、马西亚与生态系统理论。',
    '个别差异与因材施教': '个别差异体现在认知方式、智力、人格与学习风格上，因材施教要据此调整教学。',
    '学习概述': '学习是由经验引起的行为或行为潜能相对持久的变化，重点是学习分类与学习理论的总框架。',
    '行为主义学习理论': '行为主义把学习看作刺激与反应之间联结的形成，代表是巴甫洛夫、桑代克、斯金纳、班杜拉。',
    '认知主义学习理论': '认知主义关注学习者内部的信息加工，代表有苛勒、托尔曼、布鲁纳、奥苏贝尔、加涅。',
    '建构主义学习理论': '建构主义认为知识由学习者主动建构，强调情境、协作、会话与意义建构。',
    '人本主义学习理论': '人本主义强调人的价值、尊严与自我实现，代表是马斯洛与罗杰斯，主张有意义学习。',
    '学习动机': '学习动机是推动学习行为的内部动力，重点是分类、理论（强化、需要、归因、自我效能）与培养激发。',
    '学习策略': '学习策略是提高学习效率的规则与方案，分为认知策略、元认知策略和资源管理策略。',
    '学习迁移': '学习迁移是一种学习对另一种学习的影响，重点是分类、理论（形式训练、共同要素、概括化、关系转换）。',
    '知识的学习': '知识学习包括知识的获得、保持与提取，重点是陈述性知识与程序性知识的表征及迁移。',
    '技能学习': '技能是通过练习形成的合乎法则的活动方式，分操作技能与心智技能，重点在形成阶段与培养。',
    '态度与品德': '态度与品德都包含认知、情感、行为成分，品德发展重点是皮亚杰与科尔伯格阶段理论。',
    '问题解决与创造性': '问题解决是由一定情境引起的、按目标寻求答案的思维活动；创造性核心是发散思维。',
    '心理健康': '心理健康是个体内部协调与外部适应良好的状态，重点是标准、常见心理问题与辅导方法。',
    '教师专业成长': '教师专业成长关注教师角色、成长阶段、专业素养与职业倦怠，重点是福勒与休伯曼阶段理论。',
    '教学设计': '教学设计是对教学目标、内容、方法、评价的系统规划，重点是目标编写、模式与教学环节。',
    '课堂管理': '课堂管理是教师协调课堂因素、有效实现教学目标的过程，重点是气氛、纪律与问题行为处理。',
}

MNEMO = {
    '记忆': '编码—存储—提取，三段一线；瞬时—短时—长时，容量递减、时间递增。',
    '表象与想象': '表象是旧画面，想象是新组合；无意有意再创造，幻想再分理想与空想。',
    '思维': '思维两特征：概括＋间接；过程四步：分析综合、比较分类、抽象概括、具体化。',
    '情绪情感': '情绪三成分：主观体验、生理唤醒、外部表现；功能记「适动组信健感」。',
    '意志': '意志两阶段：准备（动机冲突、目的确立、计划制定）＋执行；四品质：自觉、果断、自制、坚韧。',
    '个性倾向性': '需要是基础，动机是动力，兴趣带倾向；信念、理想、价值观管总方向。',
    '能力': '能力分一般与特殊，智力是核心；斯皮尔曼二因素、卡特尔流体晶体、加德纳多元。',
    '人格': '人格看气质、性格、自我调控；气质无好坏，性格有优劣。',
    '社会心理': '态度三成分：认知、情感、行为；印象看首因、近因、晕轮、刻板；群体看规范、压力、凝聚力。',
    '教育心理学概述': '教育心理学＝教育学情境＋心理学规律；发展线索记「桑代克奠基、布鲁纳转向、人本兴起」。',
    '学生心理发展概述': '发展四特征：连续阶段、定向顺序、不平衡、个别差异；关键期与年龄阶段要成对记。',
    '皮亚杰认知发展': '图式—同化—顺应—平衡；四阶段：感知运动、前运算、具体运算、形式运算。',
    '维果斯基': '低级靠生物，高级靠文化；最近发展区＝现有水平到潜在水平；教学应走在发展前面。',
    '社会性发展': '弗洛伊德五期按快感区，埃里克森八期按社会任务，马西亚四状态看探索与承诺。',
    '个别差异与因材施教': '认知方式看场独立/场依存、冲动/沉思；智力看水平、类型、表现早晚。',
    '学习概述': '学习是经验引起、相对持久的变化；不是本能、疲劳、成熟或药物造成的暂时变化。',
    '行为主义学习理论': '巴甫洛夫经典条件作用，桑代克试误三律，斯金纳操作强化，班杜拉观察模仿。',
    '认知主义学习理论': '苛勒顿悟、托尔曼认知地图、布鲁纳发现、奥苏贝尔有意义接受、加涅信息加工。',
    '建构主义学习理论': '知识不是被动接收，而是主动建构；四要素：情境、协作、会话、意义建构。',
    '人本主义学习理论': '马斯洛看需要层次，罗杰斯看自我实现；有意义学习＝全身心投入＋自我评价。',
    '学习动机': '动机三力：推力、拉力、压力；理论记强化、需要、归因、自我效能、成就动机。',
    '学习策略': '认知策略管加工，元认知策略管监控，资源管理策略管时间、环境、努力与求助。',
    '学习迁移': '形式训练重官能，共同要素看相似，概括化看经验类化，关系转换看原理理解。',
    '知识的学习': '陈述性知识重表征，程序性知识重产生式；知识学习三步：获得、保持、提取。',
    '技能学习': '操作技能四阶段：操作定向、模仿、整合、熟练；心智技能三阶段：原型定向、操作、内化。',
    '态度与品德': '态度三成分：认知、情感、行为意向；品德发展从服从到认同再到内化。',
    '问题解决与创造性': '问题三成分：起始状态、目标状态、障碍；创造性三特征：流畅、变通、独创。',
    '心理健康': '健康不只无病，还要身体、心理、社会适应都好；心理问题按程度分一般、障碍、疾病。',
    '教师专业成长': '福勒三阶段：关注生存、关注情境、关注学生；休伯曼五期看入职与职业倦怠。',
    '教学设计': '教学设计四问：教什么、教给谁、怎么教、教得怎样；目标写「行为＋条件＋标准」。',
    '课堂管理': '课堂管理三层面：物理环境、课堂气氛、课堂纪律；问题行为处理要预防先行、立即制止、课后跟进。',
}

# 极少数选项内含「A 项和 B 项」，正则会把正文里的字母当选项标号，人工校正
FIXES = {
    ('25.教育心理学概述章节练习题_2025121709091814.md', 13): {
        'o': OrderedDict([('A', '各种策略'), ('B', '元认知'),
                          ('C', '知识建构'), ('D', 'A 项和 B 项')]),
        'a': 'D',
    },
}


# ---------------------------------------------------------------- 文本清洗
DROP = re.compile(r'无水印|纸质版|微信|mkkz88|CHAO\s*GE|超格')


def clean_raw(raw):
    out = []
    for ln in raw.splitlines():
        if ln.strip().startswith('<!--'):
            continue
        t = DROP.sub('', ln).strip()
        t = re.sub(r'\s+', ' ', t).strip()
        if not t:
            continue
        if re.fullmatch(r'\d{1,3}', t):
            continue
        out.append(t)
    return '\n'.join(out)


def norm_key(s):
    return re.sub(r'[\s，。、；：？！（）()“”"\'_—…·]', '', s)


# ---------------------------------------------------------------- 答案对齐
def answer_map(block, maxn=300):
    """区间答案 → {题号: 答案}。容忍 OCR 在数字间插空格、末段省略结束号。"""
    if not block:
        return {}, {}
    b = block.split('【答案】', 1)[-1]
    b = re.split(r'\d{1,3}\s*[.．]\s*[【\[]\s*(?:材料|分析|简答|论述|辨析|名词)', b)[0]
    b = DROP.sub('', b)
    b = re.sub(r'\s+', '', b)
    ms = list(re.finditer(r'(\d{1,3})\s*[-—–~至]\s*(\d{0,3})\s*[：:]', b))
    ans, notes = {}, {}
    for i, m in enumerate(ms):
        a = int(m.group(1))
        b2 = int(m.group(2) or 0)
        end = ms[i + 1].start() if i + 1 < len(ms) else len(b)
        toks = [x.strip() for x in re.split(r'[；;]', b[m.end():end]) if x.strip()]
        toks = [x for x in toks if not re.fullmatch(r'\d{1,3}', x)]
        if b2 < a:
            b2 = a + len(toks) - 1
        expected = b2 - a + 1
        if len(toks) > expected:
            notes[f'{a}-{b2}'] = f'区间多出 {len(toks) - expected} 项，取前 {expected} 项'
            toks = toks[:expected]
        elif len(toks) < expected:
            notes[f'{a}-{b2}'] = f'区间少 {expected - len(toks)} 项，按实际 {len(toks)} 项对齐'
            b2 = a + len(toks) - 1
        for k, t in enumerate(toks):
            if a + k <= maxn:
                ans[a + k] = t
    return ans, notes


# ---------------------------------------------------------------- 选项
OPT_DOT = re.compile(r'([A-E])\s*[.．、]')
OPT_SPACE = re.compile(r'(?<![A-Za-z0-9\u4e00-\u9fa5.．、])([A-E])\s+(?=[\u4e00-\u9fa5])')
OPT_BARE = re.compile(r'(?<![A-Za-z0-9\u4e00-\u9fa5.．、])([A-E])(?=[\u4e00-\u9fa5\d])')


def split_options2(text):
    ms = sorted(list(OPT_DOT.finditer(text)) + list(OPT_SPACE.finditer(text))
                + list(OPT_BARE.finditer(text)), key=lambda m: m.start())
    # 去重叠：同一个字母位置只留一个
    uniq, seen_pos = [], set()
    for m in ms:
        if m.start() in seen_pos:
            continue
        seen_pos.add(m.start())
        uniq.append(m)
    ms = uniq
    start = next((i for i, m in enumerate(ms) if m.group(1) == 'A'), None)
    if start is None:
        return text.strip(), {}
    first = ms[start]
    stem = text[:first.start()].strip()
    opts = OrderedDict()
    pos = start
    expect = 'A'
    while expect <= 'E' and pos < len(ms):
        # 只找「当前应有的字母」，跳过选项正文里出现的 A/B/C
        j = next((k for k in range(pos, len(ms)) if ms[k].group(1) == expect), None)
        if j is None:
            break
        m = ms[j]
        nxt = next((ms[k].start() for k in range(j + 1, len(ms))), len(text))
        val = text[m.end():nxt].strip()
        val = re.sub(r'\s+', ' ', val).strip('；;，, ')
        if val:
            opts[expect] = val
            expect = chr(ord(expect) + 1)
        pos = j + 1
    return stem, opts


# ---------------------------------------------------------------- 单题解析
def parse_q(blk, n, am):
    blk = qp.norm_spaces(blk)
    t, rest, tag = qp.parse_type(blk)
    rest = qp.norm_spaces(rest)
    stem, opts = split_options2(rest)
    stem = qp.norm_spaces(stem)
    stem = re.sub(r'^[）)、，,。\s]+', '', stem)
    if not stem or len(stem) < 6:
        return None, '题干过短'

    raw_a = am.get(n, '')
    if not raw_a:
        return None, '缺答案'
    s = re.sub(r'\s', '', raw_a)

    # 有些判断/填空被课件误标成「单选」，题干只有括号、无选项
    if t in ('单项选择题', '多项选择题') and not opts and s in ('√', '✓', '×', 'x', 'X', '╳'):
        t = '判断题'
    if t is None:
        if opts:
            t = '单项选择题'
        elif s in ('√', '✓', '×', 'x', 'X', '╳') or re.search(r'[（(]\s*[）)]\s*$', stem):
            t = '判断题'
        else:
            t = '填空题'

    if any(k in t for k in ('材料', '分析', '简答', '论述', '辨析', '名词')):
        return None, '非客观题型'
    if any(x in s for x in ('见分析', '答案见', '略')):
        return None, '答案指向解析，暂不收'

    if t == '判断题':
        if s in ('√', '✓', '对', '正确', 'A'):
            a = 'A'
        elif s in ('×', 'x', 'X', '错', '错误', '╳', '××', 'B'):
            a = 'B'
        else:
            return None, f'判断答案异常:{raw_a}'
        opts = OrderedDict([('A', '正确'), ('B', '错误')])
    elif t == '填空题':
        stem = re.sub(r'[_＿]{2,}', '（　）', stem)
        a = raw_a.strip('；;，,。 ')
        opts = OrderedDict()
    else:
        letters = ''.join(sorted(set(re.findall(r'[A-E]', s.upper()))))
        if not letters:
            return None, f'选择答案异常:{raw_a}'
        if set(letters) - set(opts):
            return None, f'答案超出选项:{raw_a}/{list(opts)}'
        if len(opts) < 2:
            return None, '缺选项'
        a = letters
        t = '多项选择题' if len(a) > 1 else '单项选择题'

    return {'n': n, 't': t, 's': stem, 'o': opts, 'a': a, 'tag': tag or ''}, ''


# ---------------------------------------------------------------- 分节
def sections_of(fname, label):
    """读取一份清洗后的 md，返回 [(节名, body)]。"""
    path = os.path.join(RAW, fname)
    lines = qp.clean_lines(clean_raw(io.open(path, encoding='utf-8').read()))
    secs = [(t, b) for t, b in qp.split_sections(lines) if t and b.strip()]
    if not secs:
        return [(label or '本章练习', '\n'.join(lines))]
    if label:
        # 整份文件作为一个大节（用于行为主义三份合并）
        return [(label, '\n'.join(b for _, b in secs))]
    return secs


def import_chapter(no, name, parts):
    sections, dropped, notes, seen = [], [], {}, {}
    total = 0
    for fname, label in parts:
        for sec_name, body in sections_of(fname, label):
            body, ab = qp.strip_answers(body)
            qs = qp.pick_questions(body)
            if not qs:
                continue
            am, an = answer_map(ab, max(q[0] for q in qs))
            notes.update({f'{fname}·{k}': v for k, v in an.items()})
            kept = []
            for n, blk in qs:
                total += 1
                q, why = parse_q(blk, n, am)
                if not q:
                    dropped.append({'file': fname, 'sec': sec_name, 'n': n, 'why': why})
                    continue
                fx = FIXES.get((fname, n))
                if fx:
                    q.setdefault('o', OrderedDict()).clear()
                    q['o'].update(fx['o'])
                    q['a'] = fx['a']
                key = norm_key(q['s']) + '|' + '|'.join(f'{k}:{norm_key(v)}' for k, v in q['o'].items())
                if key in seen:
                    seen[key]['dups'].append(f'{fname}#{n}')
                    continue
                seen[key] = q
                q['dups'] = [f'{fname}#{n}']
                q['src'] = fname
                kept.append(q)
            if kept:
                sections.append({'name': sec_name, 'qs': kept})

    # 同名小节合并（有的课件把「五、学科作用」写了两遍）
    merged = OrderedDict()
    for s in sections:
        if s['name'] in merged:
            merged[s['name']]['qs'].extend(s['qs'])
        else:
            merged[s['name']] = s
    sections = list(merged.values())
    return {'no': no, 'name': name, 'sections': sections,
            'total': sum(len(s['qs']) for s in sections),
            'raw': total, 'dropped': dropped, 'notes': notes}


# ---------------------------------------------------------------- 写 src
def write_src(ch):
    out = []
    for s in ch['sections']:
        out.append(f"### {s['name']}\n")
        for i, q in enumerate(s['qs'], 1):
            out.append(f"{i}.【{ {'单项选择题':'单选','多项选择题':'多选','判断题':'判断','填空题':'填空'}[q['t']] }】{q['s']}")
            for k, v in q['o'].items():
                out.append(f'{k}.{v}')
            out.append('')
        vals = []
        for q in s['qs']:
            if q['t'] == '判断题':
                vals.append('√' if q['a'] == 'A' else '×')
            else:
                vals.append(q['a'])
        # 一节只放一个答案区；parse.py 只认第一个【答案】
        out.append('【答案】')
        for st in range(0, len(vals), 10):
            a, b = st + 1, min(st + 10, len(vals))
            out.append(f"{a}—{b}：" + '；'.join(vals[st:b]) + ';')
        out.append('')
    path = os.path.join(SRC, f't{ch["no"]:02d}.md')
    io.open(path, 'w', encoding='utf-8').write('\n'.join(out))


# ---------------------------------------------------------------- 写解析
def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


ABS_WORDS = ('一定', '都', '完全', '只有', '必须', '只要', '所有', '一定都', '绝对',
             '从来', '任何', '唯一', '全部', '只能', '就是')


def brief(stem, n=16):
    t = re.sub(r'[\s（）()【】\[\]{}_＿…\.．、，,；;：:？?！!]+', '', stem)
    return t[:n] + ('…' if len(t) > n else '')


def sec_index(sec):
    """本节「正确项术语 → 题号」与「题干里出现过的术语」两张表。"""
    by_term, in_stem = {}, set()
    for i, q in enumerate(sec['qs'], 1):
        if q['t'] in ('单项选择题', '多项选择题'):
            for k in q['a']:
                v = q['o'].get(k, '')
                if v:
                    by_term.setdefault(norm_key(v), []).append(i)
        for k, v in q['o'].items():
            if v:
                in_stem.add(norm_key(v))
    return by_term, in_stem


def analysis_for(q, ch, sec, n, idx):
    intro = CH_INTRO.get(ch['name'], '')
    mnem = MNEMO.get(ch['name'], '')
    by_term, in_stem = idx
    a = q['a']
    stem_b = brief(q['s'])
    terms = sorted({norm_key(v) for k, v in q['o'].items() if k in a})

    if q['t'] == '判断题':
        ans_txt = '正确' if a == 'A' else '错误'
        head = f'本题判断为 <span class="hl">{ans_txt}</span>（选 {a}）。'
        hit = [w for w in ABS_WORDS if w in q['s']]
        if a == 'B' and hit:
            why = (f'题干里的「{hit[0]}」把话说满了——教材原话没有这层限定，'
                   f'这类绝对化表述是判断题最常见的错因。')
        elif a == 'B':
            why = (f'题干被判错，常见错因是改了条件、换了主体，或把话说到超出教材范围。'
                   f'回到「{esc(sec)}」的原文逐条比一遍，找出被改掉的那一处。')
        elif hit:
            why = (f'题干虽含「{hit[0]}」，但这一条在教材里确实成立，不能只凭绝对化词语判错。')
        else:
            why = f'按课件口径这一条成立，题干没有换条件、换主体，判对。'
        body = [
            f'<h3>🎯 答案解析</h3><p>{head}</p>',
            f'<h3>📚 知识点讲解</h3><p>考点定位：<b>{esc(ch["name"])}</b> · {esc(sec)}。</p><p>{why}</p>',
            f'<h3>💡 解题思路</h3><ul>'
            f'<li>先把题干缩成「谁—做什么—在什么条件下」，再和教材原话比条件。</li>'
            f'<li>盯三样：绝对化词（都／只有／必须）、范围词（全部／部分）、主体词（教师／学生）。</li>'
            f'<li>本题落点：{esc(brief(q["s"], 34))}</li></ul>',
            f'<h3>🧠 记忆口诀</h3><p>{esc(mnem) or "先记本节关键词，再用关键词复述定义。"}</p>',
        ]
        return ''.join(body)

    if q['t'] == '填空题':
        return ''.join([
            f'<h3>🎯 答案解析</h3><p>参考答案：<span class="hl">{esc(a)}</span>。</p>',
            f'<h3>📚 知识点讲解</h3><p>考点定位：<b>{esc(ch["name"])}</b> · {esc(sec)}。</p>'
            f'<p>本题是识记型填空，答案要与教材表述逐字对应，写近义词一般不给分。</p>'
            f'<p>{esc(intro)}</p>',
            f'<h3>💡 解题思路</h3><ul><li>先读整句判断空缺处要填的是「概念名」还是「特点／分类」。</li>'
            f'<li>用本节其他题目里出现过的术语反推，本题答案「{esc(a)}」正是其中之一。</li></ul>',
            f'<h3>🧠 记忆口诀</h3><p>{esc(mnem) or "先记本节关键词，再用关键词复述定义。"}</p>',
        ])

    # 选择题：逐项判定
    right = '、'.join(f'{k}「{esc(v)}」' for k, v in q['o'].items() if k in a)
    head = f'正确答案为 <span class="hl">{a}</span>——{right}。' if right else f'正确答案为 <span class="hl">{a}</span>。'
    lis = []
    for k, v in q['o'].items():
        vk = norm_key(v)
        if k in a:
            lis.append(f'<li><b>{k}</b>「{esc(v)}」——与题干「{esc(stem_b)}」的限定词直接对应，选。</li>')
            continue
        others = [x for x in by_term.get(vk, []) if x != n]
        if others:
            lis.append(f'<li><b>{k}</b>「{esc(v)}」——这是本节第 {others[0]} 题考的知识点，'
                       f'本题问的不是它，属<span class="no">概念错位</span>。</li>')
        else:
            lis.append(f'<li><b>{k}</b>「{esc(v)}」——与题干要求不符，属<span class="no">干扰项</span>。</li>')
    nright = sum(1 for k in q['o'] if k in a)
    core = '、'.join(f'「{esc(v)}」' for k, v in q['o'].items() if k in a)
    if nright == 1:
        lead = f'本题落点就是{core}这一个概念'
    else:
        lead = f'本题是多选，{nright} 个正确项分属同一考点的不同侧面，每一个都要在教材里找得到出处'
    tail = ('多选题宁缺勿滥：只选与题干直接对应、且在本节教材里说得通的项。'
            if q['t'] == '多项选择题' else
            '单选题选最贴合题干的一项，熟悉但不对应的表述最容易骗人。')
    return ''.join([
        f'<h3>🎯 答案解析</h3><p>{head}</p>',
        f'<h3>📚 知识点讲解</h3><p>考点定位：<b>{esc(ch["name"])}</b> · {esc(sec)}。</p>'
        f'<p>{lead}。{esc(intro)}</p>',
        f'<h3>💡 解题思路</h3><ul>' + ''.join(lis) + f'<li>{tail}</li></ul>',
        f'<h3>🧠 记忆口诀</h3><p>{esc(mnem) or "先记本节关键词，再用关键词复述定义。"}</p>',
    ])


def write_ana(ch):
    items = []
    for s in ch['sections']:
        idx = sec_index(s)
        for n, q in enumerate(s['qs'], 1):
            items.append(analysis_for(q, ch, s['name'], n, idx))
    head = f'# -*- coding: utf-8 -*-\n"""第{ch["no"]}章 {ch["name"]} · {ch["total"]} 题（全库扩充·速练解析）"""\n\nANA = [\n'
    body = ',\n'.join('"""' + x.replace('"""', '\\"\\"\\"') + '"""' for x in items)
    io.open(os.path.join(ANA, f'{ch["no"]}.py'), 'w', encoding='utf-8').write(head + body + ',\n]\n')


def main():
    os.makedirs(AUDIT, exist_ok=True)
    os.makedirs(os.path.join(ROOT, '_import'), exist_ok=True)
    report = {'chapters': [], 'dropped': 0}
    all_ch = []
    for no, name, parts in MANIFEST:
        ch = import_chapter(no, name, parts)
        all_ch.append(ch)
        write_src(ch)
        write_ana(ch)
        io.open(os.path.join(AUDIT, f'{no:02d}.json'), 'w', encoding='utf-8').write(
            json.dumps(ch, ensure_ascii=False, indent=1, default=str))
        report['dropped'] += len(ch['dropped'])
        print(f'{no:02d} {name:12s} 原 {ch["raw"]:3d} → 收 {ch["total"]:3d}，'
              f'丢弃 {len(ch["dropped"]):2d}，{len(ch["sections"])} 节')
        if ch['dropped']:
            for d in ch['dropped'][:4]:
                print(f'     - Q{d["n"]} {d["why"]}')
        report['chapters'].append({'no': no, 'name': name, 'raw': ch['raw'],
                                   'kept': ch['total'], 'sections': len(ch['sections']),
                                   'dropped': ch['dropped'], 'notes': ch['notes']})
    report['total'] = sum(c['total'] for c in all_ch)
    io.open(os.path.join(ROOT, '_import', 'report.json'), 'w', encoding='utf-8').write(
        json.dumps(report, ensure_ascii=False, indent=1))
    print('合计新增', report['total'], '题')


if __name__ == '__main__':
    main()
