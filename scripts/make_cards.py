#!/usr/bin/env python3
"""图文卡片：小红书 3:4 轮播 / 微博配图 / 知乎配图。

spec 字段：
  id, size [w,h] (默认 1080x1440), brand
  cover: {image|prompt, title (用\\n手动换行), highlight, sub, style: "panel"|"poster"}
  pages: [{kicker, title, body: [段落/要点], note, image|prompt(可选,放页内上半部)}]
用法: .venv/bin/python scripts/make_cards.py <spec.json>
"""
import json, pathlib, sys
from PIL import Image, ImageDraw
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import font, gen_image
from make_video import wrap, cover_fit, gradient

CREAM = (255, 249, 238)
INK = (24, 24, 28)
GREY = (110, 110, 118)
YELLOW = (255, 214, 10)
MARK = (255, 226, 92)
STYLE = 'editorial illustration, clean composition, soft natural light, rich but calm color, no text, no letters, no watermark'


def get_image(item, workdir, name, size):
    if item.get('image'):
        return Image.open(item['image']).convert('RGB')
    p = workdir / f'{name}.png'
    gen_image(item['prompt'] + ', ' + STYLE, p, size='1024x1536' if size[1] >= size[0] else '1536x1024')
    return Image.open(p).convert('RGB')


def marker_line(d, xy, text, fnt, hl, fill=INK):
    """画一行字，命中 hl 的部分底下垫黄色马克笔。"""
    x, y = xy
    if hl and hl in text:
        pre, _, post = text.partition(hl)
        x1 = x + d.textlength(pre, font=fnt)
        x2 = x1 + d.textlength(hl, font=fnt)
        bbox = d.textbbox((x, y), text, font=fnt)
        d.rectangle([x1 - 4, bbox[3] - (bbox[3] - bbox[1]) * 0.42, x2 + 4, bbox[3] + 4], fill=MARK)
    d.text((x, y), text, font=fnt, fill=fill)


def render_cover(spec, workdir, W, H):
    c = spec['cover']
    img = cover_fit(get_image(c, workdir, 'cover', (W, H)), W, H).convert('RGBA')
    d = ImageDraw.Draw(img)
    size = c.get('size', 112)
    ft = font(size, 'semibold')
    lines = c['title'].split('\n')
    if c.get('style', 'panel') == 'panel':
        pad = 56
        panel_h = len(lines) * (size + 30) + (110 if c.get('sub') else 40) + pad * 2
        y0 = H - panel_h - 50
        d.rounded_rectangle([40, y0, W - 40, H - 50], radius=36, fill=(255, 252, 245, 245))
        y = y0 + pad
        for ln in lines:
            marker_line(d, (90, y), ln, ft, c.get('highlight'))
            y += size + 30
        if c.get('sub'):
            fs = font(46, 'medium')
            d.text((92, y + 12), c['sub'], font=fs, fill=GREY)
    else:  # poster: 大字压在图上
        img.alpha_composite(gradient(H // 2, 0, 230), (0, H - H // 2))
        y = H - 120 - len(lines) * (size + 26) - (80 if c.get('sub') else 0)
        for ln in lines:
            col = YELLOW if c.get('highlight') and c['highlight'] in ln else (255, 255, 255)
            d.text((70, y), ln, font=ft, fill=col, stroke_width=4, stroke_fill=(0, 0, 0))
            y += size + 26
        if c.get('sub'):
            d.text((72, y + 10), c['sub'], font=font(48, 'medium'), fill=(240, 240, 240))
    fb = font(34, 'medium')
    d.rounded_rectangle([40, 40, 40 + d.textlength(spec.get('brand', '示例聊AI'), font=fb) + 40, 100], radius=30, fill=(0, 0, 0, 150))
    d.text((60, 70), spec.get('brand', '示例聊AI'), font=fb, fill=(255, 255, 255), anchor='lm')
    return img.convert('RGB')


def render_page(spec, page, i, n, workdir, W, H):
    img = Image.new('RGB', (W, H), CREAM)
    d = ImageDraw.Draw(img)
    x, y, maxw = 84, 96, W - 168
    if page.get('kicker'):
        fk = font(36, 'semibold')
        tw = d.textlength(page['kicker'], font=fk)
        d.rounded_rectangle([x, y, x + tw + 36, y + 58], radius=29, fill=INK)
        d.text((x + 18, y + 29), page['kicker'], font=fk, fill=YELLOW, anchor='lm')
        y += 92
    if page.get('title'):
        ft = font(page.get('title_size', 66), 'semibold')
        for ln in page['title'].split('\n'):
            for sub in wrap(d, ln, ft, maxw):
                marker_line(d, (x, y), sub, ft, page.get('highlight'))
                y += page.get('title_size', 66) + 22
        y += 18
    if page.get('image') or page.get('prompt'):
        ih = page.get('image_h', 520)
        pic = cover_fit(get_image(page, workdir, f'page{i}', (W, ih)), W - 168, ih)
        mask = Image.new('L', pic.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, pic.width, pic.height], radius=28, fill=255)
        img.paste(pic, (x, y), mask)
        y += ih + 40
    bottom = H - (190 if page.get('note') else 130)

    def layout(size, draw=False):
        """'**xx' 段为小标签（灰色小字，紧贴下一段）；其余为正文。返回结束 y。"""
        fb, fl = font(size, 'regular'), font(int(size * 0.74), 'semibold')
        lh = int(size * 1.58)
        yy = y
        paras = page.get('body', [])
        for k, para in enumerate(paras):
            label = para.startswith('**')
            text = para.strip('*')
            f = fl if label else fb
            bullet = text.startswith('· ') or text[:2] in ('① ', '② ', '③ ', '④ ', '⑤ ', '⑥ ')
            for j, ln in enumerate(wrap(d, text, f, maxw - (0 if not bullet or j == 0 else 44), balance=False)):
                if draw:
                    if label:
                        d.text((x, yy), ln, font=f, fill=GREY)
                    else:
                        marker_line(d, (x + (44 if bullet and j > 0 else 0), yy), ln, f, page.get('mark'), fill=INK)
                yy += int(size * 1.15) if label else lh
            yy += int(size * 0.1) if label else int(lh * 0.45)
        return yy

    size = page.get('body_size', 44)
    while size > 30 and layout(size) > bottom:
        size -= 2
    layout(size, draw=True)
    if page.get('note'):
        fn = font(30, 'regular')
        d.line([(x, H - 168), (W - x, H - 168)], fill=(225, 218, 205), width=2)
        d.text((x, H - 150), wrap(d, page['note'], fn, maxw)[0], font=fn, fill=GREY)
    fp = font(30, 'medium')
    d.text((x, H - 80), spec.get('brand', '示例聊AI'), font=fp, fill=GREY, anchor='lm')
    if n > 1:
        d.text((W - x, H - 80), f'{i}/{n}', font=fp, fill=GREY, anchor='rm')
    return img


def render(spec_path):
    spec_path = pathlib.Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text())
    W, H = spec.get('size', [1080, 1440])
    workdir = spec_path.parent / (spec_path.stem + '_build')
    workdir.mkdir(exist_ok=True)
    outs = []
    sid = spec.get('id', spec_path.stem)
    if spec.get('cover'):
        p = spec_path.parent / f'{sid}-01.jpg'
        render_cover(spec, workdir, W, H).save(p, quality=93)
        outs.append(str(p))
    pages = spec.get('pages', [])
    for i, page in enumerate(pages, 2 if spec.get('cover') else 1):
        p = spec_path.parent / f'{sid}-{i:02d}.jpg'
        render_page(spec, page, i, len(pages) + (1 if spec.get('cover') else 0), workdir, W, H).save(p, quality=93)
        outs.append(str(p))
    return outs


if __name__ == '__main__':
    print(json.dumps(render(sys.argv[1]), ensure_ascii=False, indent=1))
