# -*- coding: utf-8 -*-
"""题库源文件 → 纯文本（md）。

支持：
  PDF 有文字层  → 直接抽文字到 <name>.md
  PDF 纯扫描件  → 导出整页图到 <name>.pages/，并生成待转录的 <name>.md 骨架
  DOCX         → 按段落抽文字到 <name>.md
  TXT / MD     → 直接复制

用法：
  python extract.py F:/题库/01.xxx.pdf F:/题库/06.xxx.docx -o src/
  python extract.py F:/题库/06.pdf -o src/ --dpi 110

只有 pypdf 一个第三方依赖（pip install pypdf）。
抽不到文字层时会退化到内置 workbuddy-pdf 脚本，再不行就报扫描件。
"""
import argparse
import os
import re
import shutil
import sys
import zipfile

MIN_CHARS = 10          # 每页平均字符数低于此值 → 判为扫描件
MIN_IMG_W = 800         # 扫描页整页图的最小宽度，用来滤掉 logo / 装饰条


# ---------------------------------------------------------------- PDF 文字层
def pdf_text(path):
    """返回 (全文, 页数, 每页字符数)。pypdf 不可用时返回 None。"""
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        r = PdfReader(path)
        pages = [(p.extract_text() or '') for p in r.pages]
    except Exception as e:
        print(f'  pypdf 打开失败：{e}', file=sys.stderr)
        return None
    return '\n'.join(pages), len(pages), [len(x.strip()) for x in pages]


def pdftotext_fallback(path, out_md):
    """退化方案：调用 workbuddy-pdf 内置脚本（poppler/pdftotext）。"""
    here = os.path.dirname(os.path.abspath(__file__))
    cand = [
        os.path.join(here, '..', '..', 'workbuddy-pdf', 'scripts', 'run.sh'),
        r'E:/WorkBuddy/resources/app.asar.unpacked/resources/plugins/'
        r'workbuddy-builtin/skills/workbuddy-pdf/scripts/run.sh',
    ]
    for sh in cand:
        if os.path.exists(sh):
            rc = os.system(f'sh "{sh}" "{path}" "{out_md}" -f md -q')
            if rc == 0 and os.path.exists(out_md):
                return True
    return False


# ---------------------------------------------------------------- 扫描页导出
def pdf_page_images(path, outdir):
    """把每页内嵌的整页图导出，返回导出的文件列表。"""
    from pypdf import PdfReader
    os.makedirs(outdir, exist_ok=True)
    r = PdfReader(path)
    made = []
    for pi, page in enumerate(r.pages, 1):
        try:
            imgs = list(page.images)
        except Exception:
            continue
        k = 0
        for im in imgs:
            data = im.data
            if len(data) < 20_000:          # 太小的当装饰图跳过
                continue
            w = 0
            try:
                w = im.image.size[0]
            except Exception:
                pass
            if w and w < MIN_IMG_W:
                continue
            k += 1
            ext = os.path.splitext(im.name)[1] or '.jpg'
            fn = os.path.join(outdir, f'p{pi:02d}_{k}{ext}')
            with open(fn, 'wb') as f:
                f.write(data)
            made.append(fn)
    return made


# ---------------------------------------------------------------- DOCX
def docx_text(path):
    """只用 zipfile + 正则读 word/document.xml，不依赖 Office。"""
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml').decode('utf-8', 'ignore')
    paras = re.findall(r'<w:p[ >].*?</w:p>', xml, re.S)
    out = []
    for p in paras:
        p = re.sub(r'<w:br\s*/>', '\n', p)
        p = re.sub(r'<w:tab\s*/>', ' ', p)
        t = ''.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', p, re.S))
        t = (t.replace('&amp;', '&').replace('&lt;', '<')
              .replace('&gt;', '>').replace('&quot;', '"').replace('&apos;', "'"))
        if t.strip():
            out.append(t)
    return '\n'.join(out)


# ---------------------------------------------------------------- 主流程
def do_pdf(path, outdir, dpi):
    stem = os.path.splitext(os.path.basename(path))[0]
    out_md = os.path.join(outdir, stem + '.md')

    got = pdf_text(path)
    if got:
        text, npages, per = got
        avg = sum(per) / max(npages, 1)
        print(f'  PDF {npages} 页，平均每页 {avg:.0f} 字符')
        if avg >= MIN_CHARS:
            # 文字层可用；行内空行压一压，保留原始换行（parse.py 依赖行结构）
            text = re.sub(r'\n{3,}', '\n\n', text)
            open(out_md, 'w', encoding='utf-8').write(text)
            print(f'  ✓ 文字层提取 → {out_md}（{len(text)} 字符）')
            return 'text'
        print('  ! 文字层几乎为空，按扫描件处理')

    if pdftotext_fallback(path, out_md):
        n = len(open(out_md, encoding='utf-8').read())
        if n > MIN_CHARS * 20:
            print(f'  ✓ 用 pdftotext 提取 → {out_md}（{n} 字符）')
            return 'text'

    outdir_pages = os.path.join(outdir, stem + '.pages')
    made = pdf_page_images(path, outdir_pages)
    print(f'  → 导出整页图 {len(made)} 张到 {outdir_pages}')
    for f in made:
        print('     ', os.path.basename(f))
    open(out_md, 'w', encoding='utf-8').write(
        f'<!-- 扫描件待转录：{os.path.basename(path)}\n'
        f'     整页图见 {os.path.basename(outdir_pages)}/\n'
        f'     逐页读图转录后覆盖本文件，格式见 references/parsing-pitfalls.md -->\n')
    return 'scanned'


def do_docx(path, outdir):
    stem = os.path.splitext(os.path.basename(path))[0]
    out_md = os.path.join(outdir, stem + '.md')
    text = docx_text(path)
    open(out_md, 'w', encoding='utf-8').write(text)
    print(f'  ✓ docx 段落提取 → {out_md}（{len(text)} 字符，'
          f'{len(text.splitlines())} 行）')
    if len(text) < 200:
        print('  ! 文本过少，确认 docx 里不是整页截图')
    return 'text'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inputs', nargs='+')
    ap.add_argument('-o', '--outdir', default='src')
    ap.add_argument('--dpi', default='110')
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    for p in a.inputs:
        if not os.path.exists(p):
            print(f'!! 不存在：{p}')
            continue
        ext = os.path.splitext(p)[1].lower()
        print(f'== {os.path.basename(p)}')
        if ext == '.pdf':
            kind = do_pdf(p, a.outdir, a.dpi)
            if kind == 'scanned':
                print('  下一步：逐页读图转录（ViewImage 每页一次），'
                      '写回同名 .md 后跑 parse.py')
        elif ext == '.docx':
            do_docx(p, a.outdir)
        elif ext in ('.txt', '.md'):
            shutil.copy(p, os.path.join(a.outdir, os.path.basename(p)))
            print(f'  ✓ 直接复制')
        elif ext == '.doc':
            print('  !! .doc 为二进制老格式，先用 Word/WPS 另存为 .docx')
        else:
            print(f'  !! 不支持的类型 {ext}')


if __name__ == '__main__':
    main()
