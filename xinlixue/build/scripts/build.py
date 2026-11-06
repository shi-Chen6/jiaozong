# -*- coding: utf-8 -*-
"""config + 解析结果 + 解析文案 + 模板 → 单文件刷题页。

用法：
    python build.py quiz.json                 # 输出到 quiz.json 所在目录
    python build.py quiz.json -o dist/
    python build.py quiz.json --template 自定义.html

quiz.json 结构见 references/template-internals.md「配置文件」一节。
解析文案放在 ana/<章号>.py，内容是 `ANA = ["第1题解析", "第2题解析", ...]`，
条数必须与该章题量一致，否则直接报错退出（不做静默截断）。
"""
import argparse
import io
import json
import os
import re
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse as P  # noqa: E402

SKILL_ROOT = os.path.dirname(HERE)
DEFAULT_TPL = os.path.join(SKILL_ROOT, 'assets', 'template.html')

FILL = '填空题'


def load_ana(path):
    """读 ana/N.py 里的 ANA 列表；文件不存在返回 None。"""
    if not path or not os.path.exists(path):
        return None
    g = runpy.run_path(path)
    ana = g.get('ANA')
    if ana is None:
        raise SystemExit(f'[ana] {path} 里没有 ANA 变量')
    return list(ana)


def build_chapter(spec, root):
    src = spec['src'] if os.path.isabs(spec['src']) else os.path.join(root, spec['src'])
    secs = P.build(src)
    qs, idx = [], 0
    for sec in secs:
        for q in sec['qs']:
            idx += 1
            flags = [x for x in (q.pop('tag', '') or '').split('·') if x]
            item = {'n': idx, 't': q['t'], 's': q['s'], 'o': q['o'],
                    'a': q['a'], 'f': flags, 'sec': sec['title']}
            if q['t'] == FILL:
                item['r'] = q['a']      # 参考答案
                item['a'] = 'A'         # 自评「答对」→ 内部记 A
                item['o'] = {}
            qs.append(item)

    # 1) 同一份卷子里重复收录的题只留第一道（必须先做，解析文件才与最终题号一一对应）
    problems = []
    keep, seen = [], set()
    for q in qs:
        sig = (q['s'], q['a'], tuple(sorted(q['o'].items())))
        if sig in seen:
            problems.append(f"第{spec['no']}章 去掉重复题：{q['s'][:24]}…")
            continue
        seen.add(sig)
        keep.append(q)
    for i, q in enumerate(keep, 1):
        q['n'] = i
    qs = keep

    # 2) 再把解析按「去重后的最终题号」逐条挂上去
    ana_path = spec.get('ana', '')
    if ana_path and not os.path.isabs(ana_path):
        ana_path = os.path.join(root, ana_path)
    ana = load_ana(ana_path)
    if ana is not None:
        if len(ana) != len(qs):
            raise SystemExit(
                f"[ana] 第{spec['no']}章 {spec['name']}：解析 {len(ana)} 条 ≠ 题目 {len(qs)} 题。"
                f'（{os.path.basename(ana_path)}）')
        for q, t in zip(qs, ana):
            q['_ana'] = t

    return {'no': spec['no'], 'name': spec['name'],
            'module': spec.get('module', ''), 'qs': qs}, problems


def check_config(cfg):
    need = ('name', 'chapters')
    for k in need:
        if k not in cfg:
            raise SystemExit(f'[config] 缺字段 {k}')
    ns = cfg.get('ns', '')
    if not re.fullmatch(r'[a-z0-9]+', ns or ''):
        raise SystemExit(f'[config] ns 必须是纯小写字母/数字（用于 localStorage 前缀，'
                         f'和其他题库隔离），当前为 {ns!r}')
    nos = [c['no'] for c in cfg['chapters']]
    if nos != list(range(1, len(nos) + 1)):
        raise SystemExit(f'[config] 章号必须从 1 连续递增，当前 {nos}')
    for c in cfg['chapters']:
        for k in ('no', 'name', 'src'):
            if k not in c:
                raise SystemExit(f'[config] 第{c.get("no")}章缺字段 {k}')


def load_guide(path):
    """从 guide/<no>.py 里取出 GUIDE 字典。"""
    if not path or not os.path.exists(path):
        return None
    ns = runpy.run_path(path)
    return ns.get('GUIDE')


# ---------------------------------------------------------------- 先导卡插图
# guide 里的 img 块只写相对路径，例如：
#   {'k':'img', 'f':'c24/skinner_box.png', 'cap':'斯金纳箱：…', 'alt':'斯金纳箱示意'}
# 源图放在 <项目根>/_ext/gimg/ 下。构建时统一压缩 → base64 data URI 写进 src，
# 交付的 HTML 仍是单文件、离线可看。没有 img 块时完全不触发，向后兼容。
IMG_DIR = '_ext/gimg'
IMG_MAX_EDGE = 1000       # 最长边 px
IMG_MAX_BYTES = 80 * 1024  # 单图压缩后建议上限（base64 后约 107 KB）


def prepare_guide_images(guide_map, root, problems):
    """把 img 块的 f 解析成压缩后的 base64 data URI，写入 src 并移除 f/fmt。"""
    import base64
    from PIL import Image

    cache, stats = {}, {'n': 0, 'bytes': 0}
    for chno, g in guide_map.items():
        for sec in g.get('secs') or []:
            for b in sec.get('blocks') or []:
                if b.get('k') != 'img':
                    continue
                f = b.get('f')
                if not f:
                    problems.append(f'第{chno}章 img 块缺 f（图片相对路径）')
                    continue
                path = os.path.join(root, IMG_DIR, f)
                if not os.path.exists(path):
                    problems.append(f'第{chno}章 插图找不到：{path}')
                    continue
                if path in cache:
                    b['src'] = cache[path]
                else:
                    try:
                        im = Image.open(path)
                        im.thumbnail((IMG_MAX_EDGE, IMG_MAX_EDGE), Image.LANCZOS)
                        fmt = str(b.get('fmt') or 'png').lower()
                        buf = io.BytesIO()
                        if fmt == 'jpg':
                            im.convert('RGB').save(buf, 'JPEG', quality=82,
                                                   optimize=True, progressive=True)
                            mime = 'image/jpeg'
                        else:
                            # 课件截图/示意图用 256 色 PNG，体积约为原图的 1/5
                            q = im.convert('RGB').quantize(
                                colors=256, method=Image.Quantize.MEDIANCUT)
                            q.save(buf, 'PNG', optimize=True)
                            mime = 'image/png'
                        raw = buf.getvalue()
                        # 超标且原本是 PNG → 自动降级 JPEG（照片/漫画更省）
                        if len(raw) > IMG_MAX_BYTES and mime == 'image/png':
                            buf2 = io.BytesIO()
                            im.convert('RGB').save(buf2, 'JPEG', quality=78,
                                                   optimize=True, progressive=True)
                            if len(buf2.getvalue()) < len(raw):
                                raw, mime = buf2.getvalue(), 'image/jpeg'
                        src = 'data:%s;base64,%s' % (
                            mime, base64.b64encode(raw).decode('ascii'))
                        cache[path] = src
                        b['src'] = src
                        stats['n'] += 1
                        stats['bytes'] += len(raw)
                        if len(raw) > IMG_MAX_BYTES:
                            problems.append(
                                f'第{chno}章 插图 {f} 压缩后 {len(raw)//1024} KB，'
                                f'超过建议上限 {IMG_MAX_BYTES//1024} KB')
                    except Exception as e:
                        problems.append(f'第{chno}章 插图 {f} 处理失败：{e}')
                        continue
                b.pop('f', None)
                b.pop('fmt', None)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('config')
    ap.add_argument('-o', '--outdir', default='')
    ap.add_argument('--template', default=DEFAULT_TPL)
    a = ap.parse_args()

    cfg_path = os.path.abspath(a.config)
    root = os.path.dirname(cfg_path)
    outdir = a.outdir or root
    os.makedirs(outdir, exist_ok=True)

    cfg = json.load(io.open(cfg_path, encoding='utf-8'))
    check_config(cfg)

    chapters, problems, ana_map = [], [], {}
    for spec in cfg['chapters']:
        ch, prob = build_chapter(spec, root)
        chapters.append(ch)
        problems += prob
        for q in ch['qs']:
            if '_ana' in q:
                ana_map[f"{ch['no']}#{q['n']}"] = q.pop('_ana')

    # 先导知识（可选）：guide/<章号>.py 导出 GUIDE
    guide_map = {}
    for spec in cfg['chapters']:
        gp = spec.get('guide', '')
        if not gp:
            continue
        if not os.path.isabs(gp):
            gp = os.path.join(root, gp)
        if not os.path.exists(gp):
            problems.append(f"第{spec['no']}章 找不到先导知识文件 {gp}")
            continue
        g = load_guide(gp)
        if not g:
            problems.append(f"第{spec['no']}章 先导知识文件没有 GUIDE 变量")
            continue
        guide_map[str(spec['no'])] = g

    img_stats = prepare_guide_images(guide_map, root, problems)

    total = sum(len(c['qs']) for c in chapters)
    sec_count = sum(len({q['sec'] for q in c['qs']}) for c in chapters)
    name = cfg['name']
    data = {
        'name': name,
        'subtitle': cfg.get('subtitle', ''),
        'source': cfg.get('source', ''),
        'chapters': chapters,
        'total': total,
        'chapterCount': len(chapters),
        'secCount': sec_count,
    }

    if not os.path.exists(a.template):
        raise SystemExit(f'[template] 找不到模板 {a.template}')
    tpl = io.open(a.template, encoding='utf-8').read()
    for token in ('/*__DATA__*/', '/*__ANALYSIS__*/', '/*__GUIDE__*/', '__TITLE__', '__NS__'):
        if token not in tpl:
            raise SystemExit(f'[template] 模板缺少占位符 {token}')

    # 模板里已经写成 `var DATA = /*__DATA__*/;`，此处只注入 JSON 字面量
    data_js = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    ana_js = json.dumps(ana_map, ensure_ascii=False, separators=(',', ':'))
    guide_js = json.dumps(guide_map, ensure_ascii=False, separators=(',', ':'))
    html = (tpl.replace('/*__DATA__*/', data_js)
               .replace('/*__ANALYSIS__*/', ana_js)
               .replace('/*__GUIDE__*/', guide_js)
               .replace('__TITLE__', f'{name} · 刷题')
               .replace('__NS__', cfg['ns']))

    html_name = cfg.get('html') or f'{name}刷题.html'
    json_name = cfg.get('json') or f'{name}习题数据.json'
    out_html = os.path.join(outdir, html_name)
    out_json = os.path.join(outdir, json_name)
    io.open(out_html, 'w', encoding='utf-8').write(html)
    io.open(out_json, 'w', encoding='utf-8').write(
        json.dumps(data, ensure_ascii=False, indent=1))

    print(f'题库：{total} 题 / {len(chapters)} 章 / {sec_count} 节')
    print(f'解析：{len(ana_map)} 条' + ('' if ana_map else '（未提供，页面会显示占位）'))
    if guide_map:
        nblk = sum(len(sec['blocks']) for g in guide_map.values() for sec in g.get('secs', []))
        nkj = sum(1 for g in guide_map.values() for sec in g.get('secs', [])
                  for b in sec.get('blocks', []) if b.get('k') == 'kj')
        print(f'先导知识：{len(guide_map)} 章 / {nblk} 块 / {nkj} 条口诀')
    if img_stats['n']:
        print(f"先导插图：{img_stats['n']} 张 / {img_stats['bytes']//1024} KB（base64 内嵌）")
    for c in chapters:
        print(f"  第{c['no']}章 {c['name']}：{len(c['qs'])} 题 / "
              f"{len({q['sec'] for q in c['qs']})} 节")
    for p in problems:
        print('  !', p)
    print(f'→ {out_html}（{round(os.path.getsize(out_html) / 1024)} KB）')
    print(f'→ {out_json}')


if __name__ == '__main__':
    main()
