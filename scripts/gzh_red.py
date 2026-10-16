#!/usr/bin/env python3
"""公众号「红色主题」排版（10-16 用户定：排版用我们的红色，内容学卡兹克；红色版继续打磨细节）。

article.md → 公众号 HTML 片段。延续 gzh-design 红色版（content-v4-red.html）的视觉识别，按卡兹克的克制原则做减法：
- 正文 16px / 行高 1.75 / 段距 20px / 左右 8px，深灰字；只有黑灰 + 品牌红 #DC2626 + 浅红 #FEF2F2/#FECACA。
- 章节标题（调研 C08）：红色 DIN 编号「01」+ 20px 黑标题 + 24×3 短红杠，上方 48px，不要 STEP 英文小字、不要通栏线。
- 整句加粗（`**一整段**`，C05）：近黑粗体，全文唯一的强调手段（约每千字 ≤4 处）；句中零碎 **x** 一律去掉。
- 编号小标题（`**1. 标题**` 独占一段，C12/C13）：红色数字 + 17px 粗体，table 悬挂缩进。
- 披露段（「先交代一句…我们团队做的…」）→ 灰色旁注（C15）；摘要不进正文（只在分享卡片）。
- 文末区：码区前一条 40×2 浅红短线（C17）→ 小程序码 table 两格（C18）→ 阅读原文 → CTA → 关注卡片 → 12px 灰签名（C19）。
- 组件来源：运营手册/对标/公众号排版组件调研.md（v5 组件库）。
- 红字：只给 --red 指定的词（核心数字、「阅读原文」），全文 ≤2 处。
- 摘要卡（`> 摘要：…`）：浅红底圆角卡，第一个 --red 词在卡里标红。
- 截图（img/ 下）加 1px 浅灰描边 + 8px 圆角；信息图（ai/ 下）本身有底色，不加框；都不加图注。
- 「示例作者说」：56px 头肩动图 + 浅红气泡（尺寸写在外层 section，公众号会忽略 img 的 width）。
- 并排两张图（小程序码）→ 两列卡片；`---` 之后：CTA（15px 粗体）→ 关注卡片 → 灰色签名。
用法: .venv/bin/python scripts/gzh_red.py <article.md> <out.html> [--red "1234.00 元"] [--red "「阅读原文」"]
"""
import argparse, html, json, pathlib, re

RED, INK, TXT, SOFT, LINE = '#DC2626', '#1C1917', '#333333', '#FEF2F2', '#FECACA'
DIN = "font-family:'DIN Alternate','Helvetica Neue',Arial,sans-serif;"   # 编号数字用 iOS 自带 DIN，安卓回落
P = f'margin:0 8px 20px;'
BUST = 'https://media.example.com/example.png'


def leaf(t):
    return f'<span leaf="">{html.escape(t)}</span>'


def text(t, red, used):
    """普通段落：去掉零碎加粗；--red 词每个只标第一次。"""
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    if not red:
        return leaf(t)
    out, pat = [], '(' + '|'.join(map(re.escape, red)) + ')'
    for seg in re.split(pat, t):
        if not seg:
            continue
        if seg in red and seg not in used:
            used.add(seg)
            out.append(f'<span style="color:{RED};font-weight:bold;white-space:nowrap;">{leaf(seg)}</span>')
        else:
            out.append(leaf(seg))
    return ''.join(out)


def img(url, alt=''):
    framed = '/img/' in url or re.search(r'(income-top|expert-page)', url)
    st = f'width:100%;max-width:100%;height:auto;display:block;margin:0 auto;border-radius:8px;' + ('border:1px solid #EDEDED;' if framed else '')
    return (f'<section style="margin:0 8px 20px;line-height:0;text-align:center;"><span leaf="">'
            f'<img src="{url}" alt="{html.escape(alt)}" style="{st}"></span></section>')


def bubble(url, say):
    """示例作者说（调研 C07）：table 两格，头像 56px 写在外层 section，气泡只包住文字、常规字重。"""
    m = re.search(r'(?:sticker|bustgif2?)-(\d\d)', url)
    av = BUST.format(m.group(1)) if m else url
    return (f'<section style="display:table;margin:4px 8px 24px;">'
            f'<section style="display:table-cell;width:56px;vertical-align:middle;line-height:0;">'
            f'<section style="width:56px;min-width:56px;max-width:56px;line-height:0;"><span leaf="">'
            f'<img src="{av}" alt="示例作者" style="width:100%;max-width:100%;height:auto;display:block;margin:0;"></span></section></section>'
            f'<section style="display:table-cell;vertical-align:middle;padding-left:10px;">'
            f'<section style="display:inline-block;background:{SOFT};border:1px solid {LINE};border-radius:4px 14px 14px 14px;padding:7px 14px;">'
            f'<p style="margin:0;font-size:14px;line-height:1.6;letter-spacing:0.5px;color:#B91C1C;text-align:left;">{leaf(say)}</p></section></section></section>')


def convert(md, red=()):
    used = set()
    lines = md.splitlines()
    end_lines = []
    if '---' in lines:
        k = len(lines) - 1 - lines[::-1].index('---')
        end_lines = [l.strip() for l in lines[k + 1:] if l.strip()]
        lines = lines[:k]
    head, body, follow_end, sec = [], [], '', 0
    for raw in lines:
        l = raw.strip()
        if not l or l.startswith('<!--') or l.startswith('# '):
            continue
        if l.startswith('> '):                                   # 摘要不进正文（调研 4.0.2：开头直接是时间锚点 + 事件）
            continue
        m = re.fullmatch(r'!\[([^\]]*)\]\((\S+)\)', l)
        if m:
            alt, url = m.groups()
            if 'top-follow' in url:
                head.insert(0, f'<section style="margin:0 0 22px;line-height:0;"><span leaf=""><img src="{url}" alt="{html.escape(alt)}" '
                               f'style="width:100%;max-width:100%;height:auto;display:block;"></span></section>')
            elif 'end-follow' in url:
                follow_end = img(url, alt)
            elif alt.startswith('示例作者说：'):
                body.append(bubble(url, alt[4:]))
            else:
                body.append(img(url, alt))
            continue
        pair = re.findall(r'!\[([^\]]*)\]\((\S+?)\)', l)
        if len(pair) >= 2:                                        # 小程序码两列
            cells = ''.join(
                f'<section style="display:table-cell;width:50%;padding:0 {"6px 0 0" if i == 0 else "0 0 6px"};vertical-align:top;line-height:0;"><span leaf="">'
                f'<img src="{u}" alt="{html.escape(a)}" style="width:100%;max-width:100%;height:auto;display:block;margin:0;"></span></section>' for i, (a, u) in enumerate(pair[:2]))
            body.append(f'<section style="display:table;width:100%;table-layout:fixed;margin:0 8px 12px;width:calc(100% - 16px);">{cells}</section>')
            continue
        if l.startswith('## '):                                   # 章节标题
            sec += 1
            body.append(f'<section style="margin:48px 8px 24px;"><section style="display:table;width:100%;">'
                        f'<section style="display:table-cell;width:38px;vertical-align:top;"><p style="margin:0;font-size:22px;line-height:1.32;font-weight:bold;letter-spacing:0;color:{RED};{DIN}">{leaf(f"{sec:02d}")}</p></section>'
                        f'<section style="display:table-cell;vertical-align:top;"><p style="margin:0;font-size:20px;line-height:1.45;font-weight:bold;letter-spacing:0.5px;color:{INK};text-align:left;">{leaf(l[3:].strip())}</p></section></section>'
                        f'<section style="width:24px;height:3px;margin:10px 0 0;background:{RED};line-height:0;font-size:0;overflow:hidden;"><span leaf=""><br></span></section></section>')
            continue
        m = re.fullmatch(r'\*\*(\d+)\.\s*(.+?)\*\*', l)
        if m:                                                     # 编号小标题
            n, t = m.groups()
            body.append(f'<section style="display:table;margin:28px 8px 12px;width:calc(100% - 16px);">'
                        f'<section style="display:table-cell;width:24px;vertical-align:top;"><p style="margin:0;font-size:18px;line-height:1.5;font-weight:bold;letter-spacing:0;color:{RED};{DIN}">{leaf(n)}</p></section>'
                        f'<section style="display:table-cell;vertical-align:top;"><p style="margin:0;font-size:17px;line-height:1.5;font-weight:bold;color:{INK};text-align:left;">{leaf(t)}</p></section></section>')
            continue
        m = re.fullmatch(r'\*\*(.+)\*\*', l)
        if m:                                                     # 整句结论：近黑粗体（C05），全文唯一的强调手段
            body.append(f'<p style="margin:0 8px 20px;"><span style="font-weight:bold;color:#1A1A1A;">{leaf(m.group(1))}</span></p>')
            continue
        if re.search(r'推广自家|我们团队做的.*成分|先交代一句', l):     # 披露 → 灰色旁注（C15）
            body.append(f'<section style="margin:0 8px 20px;padding:0 0 0 12px;border-left:3px solid #E5E5E5;">'
                        f'<p style="margin:0;font-size:14px;line-height:1.75;letter-spacing:0.5px;color:#8C8C8C;text-align:justify;">{leaf(l)}</p></section>')
            continue
        h_ = text(l, red, used)
        # 含红字数字（nowrap）的段落用左对齐：两端对齐会在数字整体换行时把上一行字距撑散
        body.append(f'<p style="{P}{"text-align:left;" if "white-space:nowrap" in h_ else ""}">{h_}</p>')
    QR = '<section style="display:table;width:100%;table-layout:fixed;'
    # 码区最后一行后面多留白；码区前那一段（「想试的话…」）之前放一次居中浅红短线，标记进入文末区（C17）
    for i in range(len(body) - 1):
        if body[i].startswith(QR) and not body[i + 1].startswith(QR):
            body[i] = body[i].replace('margin:0 8px 12px;', 'margin:0 8px 24px;', 1)
    first_qr = next((i for i, x in enumerate(body) if x.startswith(QR)), None)
    if first_qr:
        body.insert(first_qr - 1, f'<section style="width:40px;height:2px;margin:36px auto;background:{LINE};line-height:0;font-size:0;overflow:hidden;"><span leaf=""><br></span></section>')
    sign = [x for x in end_lines if x.startswith('我是示例作者')]
    cta = [re.sub(r'\*\*(.+)\*\*', r'\1', x) for x in end_lines if x not in sign]
    end = ''.join(f'<p style="margin:8px 8px 22px;font-size:15px;font-weight:bold;color:{INK};">{leaf(x)}</p>' for x in cta)
    end += follow_end
    end += ''.join(f'<p style="margin:6px 8px 0;font-size:12px;line-height:1.6;letter-spacing:0.5px;color:#B2B2B2;">{leaf(x)}</p>' for x in sign)
    return (f'<section style="margin:0;padding:0;color:{TXT};font-size:16px;line-height:1.75;letter-spacing:0.5px;text-align:justify;">'
            + ''.join(head) + ''.join(body) + end + '</section>')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('md'); ap.add_argument('out')
    ap.add_argument('--red', action='append', default=[])
    a = ap.parse_args()
    mdp = pathlib.Path(a.md); md = mdp.read_text()
    mp = mdp.parent / 'img-map.json'                              # 相对图片 → 线上地址
    if mp.exists():
        for k, v in json.loads(mp.read_text()).items():
            md = md.replace(f']({k})', f']({v})')
    out = convert(md, a.red)
    pathlib.Path(a.out).write_text(out)
    print(a.out, len(out), 'chars; local srcs:', len(re.findall(r'src="(?!https)', out)), '; 荧光笔:', out.count('linear-gradient(transparent'),
          '; 红字:', out.count(f'color:{RED};font-weight:bold;'))
