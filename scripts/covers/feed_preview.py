#!/usr/bin/env python3
"""封面上线前的「缩小看效果」工具（规范见 运营手册/封面规范.md 第 5 节检查清单）。

1) sheet：把一组图按行拼成带标注的总览（每张写平台、内容类型、尺寸）。
   .venv/bin/python scripts/covers/feed_preview.py sheet <out.jpg> "#一行小标题" "图.jpg|抖音 · 竖封面|9:16 1080×1920" ... "/" ...
   参数：以 # 开头 = 新起一行并写这一行的标题；"/" = 换行；其余是 "图片路径|第一行标注|第二行标注"。

2) feed：模拟手机里各平台的列表/主页格子（按手机实际显示宽度缩小，再按 2 倍屏输出），看缩小后字还认不认得出。
   .venv/bin/python scripts/covers/feed_preview.py feed <out.jpg> \\
       --xhs a.jpg::标题 b.jpg::标题 ...          小红书主页 2 列（3:4）
       --bili c.jpg::标题 ...                     B站推荐流 2 列（16:9，左下播放量、右下时长）
       --douyin d-34.jpg ...                      抖音/视频号主页 3 列（3:4）
       --gzh e.jpg::标题                          公众号消息列表头条（2.35:1）
       --gzh-share f-11.jpg::标题                 公众号文章转发到聊天的卡片（1:1 小图）
   每个平台一块，从左到右排。标题写在 "::" 后面，不写就用文件名。
"""
import pathlib, sys
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from common import font  # noqa: E402  苹方

S = 2            # 2 倍屏
BG = (245, 245, 247)
INK = (24, 24, 28)
GREY = (120, 120, 128)


def _wrap(d, text, f, w, max_lines=2):
    lines, cur = [], ''
    for ch in text:
        if d.textlength(cur + ch, font=f) > w:
            lines.append(cur)
            cur = ch
            if len(lines) == max_lines:
                break
        else:
            cur += ch
    if len(lines) < max_lines and cur:
        lines.append(cur)
    if len(lines) == max_lines and ''.join(lines) != text:
        lines[-1] = lines[-1][:-1] + '…'
    return lines


def _fit(img, w, h):
    """等比铺满 w×h 再居中裁（平台缩略图的做法）。"""
    s = max(w / img.width, h / img.height)
    im = img.resize((max(w, int(img.width * s + .5)), max(h, int(img.height * s + .5))), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def _round(im, r):
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], r, fill=255)
    out = Image.new('RGB', im.size, BG)
    out.paste(im, (0, 0), m)
    return out, m


def _items(args):
    out = []
    for a in args:
        p, _, t = a.partition('::')
        out.append((pathlib.Path(p), t or pathlib.Path(p).stem))
    return out


def block_xhs(items, cols=2, ratio=4 / 3, colw=172, title='小红书主页（2 列）'):
    gap = 6
    W = (colw * cols + gap * (cols + 1)) * S
    cards = []
    for p, t in items:
        img = _fit(Image.open(p).convert('RGB'), colw * S, int(colw * ratio) * S)
        img, m = _round(img, 8 * S)
        card = Image.new('RGB', (colw * S, img.height + 64 * S), (255, 255, 255))
        card.paste(img, (0, 0), m)
        d = ImageDraw.Draw(card)
        f = font(13 * S, 'medium')
        for i, ln in enumerate(_wrap(d, t, f, (colw - 16) * S)):
            d.text((8 * S, img.height + (8 + i * 18) * S), ln, font=f, fill=INK)
        d.text((8 * S, img.height + 46 * S), '示例聊AI', font=font(11 * S), fill=GREY)
        cards.append(card)
    return _grid(cards, cols, gap, W, title)


def block_douyin(items):
    gap = 2
    colw = 124
    cards = []
    for p, t in items:
        img = _fit(Image.open(p).convert('RGB'), colw * S, int(colw * 4 / 3) * S)
        d = ImageDraw.Draw(img, 'RGBA')
        d.text((6 * S, img.height - 20 * S), '▷ 128', font=font(12 * S, 'semibold'), fill=(255, 255, 255))
        cards.append(img)
    return _grid(cards, 3, gap, (colw * 3 + gap * 4) * S, '抖音 / 视频号主页（3 列）')


def block_bili(items):
    gap = 8
    colw = 172
    cards = []
    for p, t in items:
        img = _fit(Image.open(p).convert('RGB'), colw * S, int(colw * 9 / 16) * S)
        d = ImageDraw.Draw(img, 'RGBA')
        h = img.height
        d.rectangle([0, h - 22 * S, img.width, h], fill=(0, 0, 0, 90))
        fs = font(10 * S, 'medium')
        d.text((6 * S, h - 17 * S), '▶ 1.2万   ▤ 36', font=fs, fill=(255, 255, 255))
        d.text((img.width - 36 * S, h - 17 * S), '04:12', font=fs, fill=(255, 255, 255))
        img, m = _round(img, 6 * S)
        card = Image.new('RGB', (colw * S, img.height + 58 * S), (255, 255, 255))
        card.paste(img, (0, 0), m)
        dd = ImageDraw.Draw(card)
        f = font(12 * S, 'medium')
        for i, ln in enumerate(_wrap(dd, t, f, (colw - 12) * S)):
            dd.text((6 * S, img.height + (6 + i * 17) * S), ln, font=f, fill=INK)
        dd.text((6 * S, img.height + 42 * S), 'UP 示例聊AI', font=font(10 * S), fill=GREY)
        cards.append(card)
    return _grid(cards, 2, gap, (colw * 2 + gap * 3) * S, 'B站推荐流（2 列）')


def block_gzh(items, share):
    W = 360 * S
    parts = []
    for p, t in items:
        w = 336 * S
        img = _fit(Image.open(p).convert('RGB'), w, int(w / 2.35))
        card = Image.new('RGB', (w, img.height + 74 * S), (255, 255, 255))
        top = Image.new('RGB', (w, 34 * S), (255, 255, 255))
        dt = ImageDraw.Draw(top)
        dt.ellipse([10 * S, 7 * S, 30 * S, 27 * S], fill=(220, 38, 38))
        dt.text((38 * S, 9 * S), '示例AI周刊', font=font(13 * S, 'semibold'), fill=INK)
        card.paste(img, (0, 0))
        d = ImageDraw.Draw(card)
        f = font(15 * S, 'semibold')
        for i, ln in enumerate(_wrap(d, t, f, w - 24 * S)):
            d.text((12 * S, img.height + (10 + i * 22) * S), ln, font=f, fill=INK)
        full = Image.new('RGB', (w, top.height + card.height), (255, 255, 255))
        full.paste(top, (0, 0))
        full.paste(card, (0, top.height))
        parts.append(full)
    for p, t in share:   # 转发到聊天的卡片：左标题、右 1:1 小图
        w = 250 * S
        card = Image.new('RGB', (w, 96 * S), (255, 255, 255))
        d = ImageDraw.Draw(card)
        f = font(14 * S, 'medium')
        for i, ln in enumerate(_wrap(d, t, f, w - 80 * S, 3)):
            d.text((10 * S, (10 + i * 20) * S), ln, font=f, fill=INK)
        th = _fit(Image.open(p).convert('RGB'), 52 * S, 52 * S)
        card.paste(th, (w - 62 * S, 26 * S))
        d.text((10 * S, 78 * S), '公众号 · 示例AI周刊', font=font(10 * S), fill=GREY)
        parts.append(card)
    return _grid(parts, 1, 10, W, '公众号消息列表 / 转发卡片')


def _grid(cards, cols, gap, W, title):
    gap *= S
    rows = [cards[i:i + cols] for i in range(0, len(cards), cols)]
    hh = 40 * S
    H = hh + sum(max(c.height for c in r) + gap for r in rows) + gap
    out = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(out)
    d.text((gap, 10 * S), title, font=font(15 * S, 'semibold'), fill=INK)
    y = hh
    for r in rows:
        x = gap
        for c in r:
            out.paste(c, (x, y))
            x += c.width + gap
        y += max(c.height for c in r) + gap
    return out


def feed(out, argv):
    groups, cur = {}, None
    for a in argv:
        if a.startswith('--'):
            cur = a[2:]
            groups[cur] = []
        else:
            groups[cur].append(a)
    blocks = []
    if 'xhs' in groups:
        blocks.append(block_xhs(_items(groups['xhs'])))
    if 'douyin' in groups:
        blocks.append(block_douyin(_items(groups['douyin'])))
    if 'bili' in groups:
        blocks.append(block_bili(_items(groups['bili'])))
    if 'gzh' in groups or 'gzh-share' in groups:
        blocks.append(block_gzh(_items(groups.get('gzh', [])), _items(groups.get('gzh-share', []))))
    pad = 24 * S
    W = sum(b.width for b in blocks) + pad * (len(blocks) + 1)
    H = max(b.height for b in blocks) + pad * 2
    img = Image.new('RGB', (W, H), (226, 226, 232))
    x = pad
    for b in blocks:
        img.paste(b, (x, pad))
        x += b.width + pad
    img.save(out, quality=90)
    return out


def sheet(out, argv, row_h=420):
    rows, cur, titles = [], [], []
    title = None
    for a in argv:
        if a == '/' or a.startswith('#'):
            if cur:
                rows.append((title, cur))
            cur = []
            title = a[1:] if a.startswith('#') else None
        else:
            p, *lab = a.split('|')
            cur.append((pathlib.Path(p), lab + ['', ''] if len(lab) < 2 else lab))
    if cur:
        rows.append((title, cur))
    gap, lab_h, th = 28, 92, 64
    rendered = []
    for title, items in rows:
        ims = []
        for p, lab in items:
            im = Image.open(p).convert('RGB')
            h = row_h
            w = int(im.width * h / im.height)
            if w > 900:  # 很扁的图（2.35:1）限宽，免得一行太长
                w, h = 900, int(im.height * 900 / im.width)
            ims.append((im.resize((w, h), Image.LANCZOS), lab))
        probe = ImageDraw.Draw(Image.new('RGB', (10, 10)))
        cw = [max(im.width, int(probe.textlength(lab[0], font=font(26, 'semibold'))),
                  int(probe.textlength(lab[1], font=font(22)))) for im, lab in ims]   # 格子宽 = 图宽和标注宽取大
        W = sum(cw) + gap * (len(ims) + 1)
        H = (th if title else 16) + row_h + lab_h + gap
        r = Image.new('RGB', (W, H), (255, 255, 255))
        d = ImageDraw.Draw(r)
        if title:
            d.text((gap, 14), title, font=font(34, 'semibold'), fill=INK)
        x = gap
        y0 = th if title else 16
        for (im, lab), w in zip(ims, cw):
            r.paste(im, (x, y0 + (row_h - im.height) // 2))
            d.rectangle([x, y0 + (row_h - im.height) // 2, x + im.width - 1, y0 + (row_h + im.height) // 2 - 1], outline=(225, 225, 230))
            d.text((x, y0 + row_h + 12), lab[0], font=font(26, 'semibold'), fill=INK)
            d.text((x, y0 + row_h + 50), lab[1], font=font(22), fill=GREY)
            x += w + gap
        rendered.append(r)
    W = max(r.width for r in rendered)
    H = sum(r.height for r in rendered) + 20
    out_img = Image.new('RGB', (W, H), (255, 255, 255))
    y = 10
    for r in rendered:
        out_img.paste(r, (0, y))
        y += r.height
    out_img.save(out, quality=88)
    return out


if __name__ == '__main__':
    mode, out, *rest = sys.argv[1:]
    print({'sheet': sheet, 'feed': feed}[mode](out, rest))
