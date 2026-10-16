#!/usr/bin/env python3
"""公众号「红色精简版」排版（10-16 对标数字生命卡兹克蒸馏后的规范，见 运营手册/对标/数字生命卡兹克.md 第七节）。

article.md → 公众号 HTML 片段：
- 正文 16px / 行高 1.6 / 字距 0.544px / 颜色 rgba(0,0,0,0.9) / 段距 24px，用微信默认字体，只有黑、品牌红、灰三种颜色。
- 强调克制：只保留「整句加粗」（加粗部分占这一段一半以上）和编号条目的加粗开头；其余 **x** 去掉；红字只给 --red 指定的 ≤2 个核心数字。
- 章节标题：单行红色行内色块「一. 标题」22px，去掉「第X步：」「文末：」前缀；--titles 可传 JSON 改写过长的标题（≤12 字）。
- 图片裸放（无框、无阴影、无图注），两张并排的图（小程序码）做两列。
- 「示例作者说」气泡（![示例作者说：一句话](表情 GIF)）：56px 头肩动图 + 浅灰气泡、常规字重。
- 顶部关注动图放最前；摘要引用块不进正文（摘要单独填）。
- 文末：CTA 一段 15px 加粗 → 关注卡片 → 12px 灰色签名，不要 END 线。
用法: .venv/bin/python scripts/gzh_lite.py <article.md> <out.html> [--red "1234.00 元"] [--titles '{"旧":"新"}']
"""
import argparse, html, json, re, pathlib

P = 'margin:0 8px 24px;'   # 卡兹克实测：每段左右 8px、段距 24px
NUM = '一二三四五六七八九十'
BUST = 'https://media.example.com/example.png'


def leaf(t):
    return f'<span leaf="">{html.escape(t)}</span>'


def inline(text, red):
    """**x** 只在整句加粗时保留；red 里的词变品牌红加粗；返回 (html, 是否整句加粗)。"""
    plain = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    bolds = re.findall(r'\*\*(.+?)\*\*', text)
    whole = bool(bolds) and sum(len(b) for b in bolds) >= 0.5 * len(plain)
    out = []
    for part in re.split(r'(\*\*.+?\*\*)', text):
        if not part:
            continue
        is_b = part.startswith('**') and part.endswith('**')
        t = part[2:-2] if is_b else part
        for seg in re.split('(' + '|'.join(map(re.escape, red)) + ')', t) if red else [t]:
            if not seg:
                continue
            if seg in red:
                out.append(f'<span style="color:#DC2626;font-weight:bold;">{leaf(seg)}</span>')
            elif is_b and whole:
                out.append(f'<span style="font-weight:bold;">{leaf(seg)}</span>')
            else:
                out.append(leaf(seg))
    return ''.join(out), whole


def img(url, alt='', w='100%'):
    return (f'<section style="text-align:center;{P}line-height:0;"><span leaf=""><img src="{url}" alt="{html.escape(alt)}" '
            f'style="width:{w};max-width:100%;height:auto;display:block;margin:0 auto;"></span></section>')


def bubble(url, text):
    m = re.search(r'sticker-(\d\d)', url) or re.search(r'bustgif-(\d\d)', url)
    av = BUST.format(m.group(1)) if m else url
    return ('<section style="display:flex;align-items:center;margin:0 8px 24px;">'
            '<section style="width:56px;min-width:56px;max-width:56px;flex-shrink:0;line-height:0;">'
            f'<span leaf=""><img src="{av}" alt="示例作者" style="width:100%;max-width:100%;height:auto;display:block;margin:0;"></span></section>'
            '<section style="margin-left:12px;background:#F6F6F6;border-radius:4px 14px 14px 14px;padding:8px 14px;">'
            f'<p style="margin:0;font-size:14px;line-height:1.6;color:rgba(0,0,0,0.8);">{leaf(text)}</p></section></section>')


def convert(md, red=(), titles=None):
    titles = titles or {}
    lines = md.splitlines()
    body, head, tail = [], [], []
    sec = 0
    i = 0
    # 文末：--- 之后的签名和 CTA 单独处理
    if '---' in lines:
        k = len(lines) - 1 - lines[::-1].index('---')
        end_lines = [l.strip() for l in lines[k + 1:] if l.strip()]
        lines = lines[:k]
    else:
        end_lines = []
    follow_end = None
    while i < len(lines):
        l = lines[i].rstrip()
        i += 1
        if not l.strip() or l.startswith('<!--') or l.startswith('# '):
            continue
        if l.startswith('> '):          # 摘要引用块：不进正文
            continue
        m = re.fullmatch(r'!\[([^\]]*)\]\((\S+)\)', l.strip())
        if m:
            alt, url = m.groups()
            if 'top-follow' in url:
                head.append(img(url, alt)); continue
            if 'end-follow' in url:
                follow_end = img(url, alt); continue
            if alt.startswith('示例作者说：'):
                body.append(bubble(url, alt[4:])); continue
            body.append(img(url, alt)); continue
        pair = re.findall(r'!\[([^\]]*)\]\((\S+?)\)', l)
        if len(pair) >= 2:              # 并排两张（小程序码）
            cells = ''.join(f'<section style="display:inline-block;width:49%;vertical-align:top;line-height:0;"><span leaf="">'
                            f'<img src="{u}" alt="{html.escape(a)}" style="width:100%;height:auto;display:block;"></span></section>' for a, u in pair)
            body.append(f'<section style="margin:0 8px 12px;font-size:0;text-align:justify;">{cells}</section>'); continue
        if l.startswith('## '):
            t = re.sub(r'^(第[一二三四五六七八九十]+步|文末)[：:]\s*', '', l[3:].strip())
            t = titles.get(t, t)
            body.append('<p style="margin:0 8px;"><span leaf=""><br></span></p>')   # 章节标题前空一行
            body.append(f'<p style="margin:0 8px 24px;"><span style="background:#DC2626;color:#FFFFFF;font-size:22px;font-weight:bold;padding:0 4px;">'
                        f'{leaf(f"{NUM[sec]}. {t}")}</span></p>')
            sec += 1; continue
        m = re.match(r'^(\d+)\.\s+(.*)', l)
        if m:                           # 编号条目：加粗的开头保留（起小标题作用）
            n, t = m.groups()
            lead = re.match(r'\*\*(.+?)\*\*(.*)', t)
            if lead:
                h_ = f'<span style="font-weight:bold;">{leaf(f"{n}. " + lead.group(1))}</span>' + inline(lead.group(2), red)[0]
            else:
                h_ = leaf(f'{n}. ') + inline(t, red)[0]
            body.append(f'<p style="{P}">{h_}</p>'); continue
        if l.startswith('- '):
            t = l[2:]
            lead = re.match(r'\*\*(.+?)\*\*(.*)', t)
            if lead and len(lead.group(1)) <= 16 and lead.group(2)[:1] in '：:。，,':   # 「**专家**：…」这类定义式条目保留开头加粗
                h_ = f'<span style="font-weight:bold;">{leaf(lead.group(1))}</span>' + inline(lead.group(2), red)[0]
            else:
                h_ = inline(t, red)[0]
            body.append(f'<p style="{P}">{leaf("· ")}{h_}</p>'); continue
        body.append(f'<p style="{P}">{inline(l.strip(), red)[0]}</p>')
    # 文末顺序：CTA（加粗 15px）→ 关注卡片 → 灰色签名
    sign = [x for x in end_lines if x.startswith('我是示例作者')]
    cta = [x for x in end_lines if x not in sign]
    end = ''.join(f'<p style="margin:0 8px 24px;font-size:15px;font-weight:bold;letter-spacing:0.578px;">{inline(x, ())[0]}</p>' for x in cta)
    end += follow_end or ''
    end += ''.join(f'<p style="margin:0 8px 8px;font-size:12px;color:#B2B2B2;letter-spacing:0.578px;">{leaf(x)}</p>' for x in sign)
    return ('<section style="padding:0;color:rgba(0,0,0,0.9);font-size:16px;line-height:1.6;letter-spacing:0.544px;text-align:justify;">'
            + ''.join(head) + ''.join(body) + end + '</section>')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('md'); ap.add_argument('out')
    ap.add_argument('--red', action='append', default=[])
    ap.add_argument('--titles', default='{}')
    a = ap.parse_args()
    md_path = pathlib.Path(a.md)
    md = md_path.read_text()
    # 相对图片路径换成线上地址（同目录 img-map.json：md 路径 → https）
    mp = md_path.parent / 'img-map.json'
    if mp.exists():
        for k, v in json.loads(mp.read_text()).items():
            md = md.replace(f']({k})', f']({v})')
    out = convert(md, a.red, json.loads(a.titles))
    pathlib.Path(a.out).write_text(out)
    left = re.findall(r'src="(?!https)[^"]+"', out)
    print(a.out, len(out), 'chars; local srcs:', len(left), '; bold:', out.count('font-weight:bold;'))
