#!/usr/bin/env python3
"""引导关注素材（10-16 用户要求统一）：公众号文章顶部关注动图 + 文末关注海报。输出到 assets/follow-kit/。

- top-follow.gif   文章开头：「点上方蓝字 关注示例AI周刊」，箭头往上跳（1080×270，循环）
- end-follow.jpg   文末海报：上半作图 API 一体设计（标题+插画），下半真二维码（open.weixin.qq.com/qr/code?username=gh_6d6f4e5fd764）
用法: .venv/bin/python scripts/make_follow_kit.py [gif|poster|all]
"""
import pathlib, sys
from PIL import Image, ImageDraw, ImageFilter
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from common import font, gen_image

OUT = ROOT / 'assets/follow-kit'
NAVY1, NAVY2, YELLOW, WHITE, CORAL = (18, 24, 66), (52, 34, 110), (255, 214, 10), (255, 255, 255), (255, 107, 107)
NAME = '示例AI周刊'


def gradient(W, H):
    im = Image.new('RGB', (W, H))
    d = ImageDraw.Draw(im)
    for x in range(W):
        t = x / W
        d.line([(x, 0), (x, H)], fill=tuple(int(NAVY1[i] + (NAVY2[i] - NAVY1[i]) * t) for i in range(3)))
    return im


def top_gif():
    W, H, N = 1080, 270, 16
    base = gradient(W, H)
    frames = []
    for k in range(N):
        im = base.copy()
        d = ImageDraw.Draw(im)
        import math
        dy = int(10 * math.sin(2 * math.pi * k / N))
        # 跳动的上箭头（两个）
        for ax in (110, W - 110):
            y0 = 150 + dy
            d.polygon([(ax, y0 - 70), (ax - 42, y0 - 18), (ax + 42, y0 - 18)], fill=YELLOW)
            d.rounded_rectangle([ax - 16, y0 - 24, ax + 16, y0 + 40], 6, fill=YELLOW)
        d.text((W // 2, 52), '点上方蓝字', font=font(44, 'semibold'), fill=WHITE, anchor='mm')
        # 「关注 示例AI周刊」，名字用黄底高亮，轻微呼吸
        f = font(58, 'semibold')
        t1, t2 = '关注 ', NAME
        w1, w2 = d.textlength(t1, font=f), d.textlength(t2, font=f)
        x = (W - w1 - w2 - 24) // 2
        y = 140
        d.text((x, y), t1, font=f, fill=WHITE, anchor='lm')
        pad = 6 + (2 if k % 8 < 4 else 0)
        d.rounded_rectangle([x + w1 - pad, y - 38 - pad, x + w1 + w2 + 24 + pad, y + 38 + pad], 16, fill=YELLOW)
        d.text((x + w1 + 12, y), t2, font=f, fill=(24, 24, 28), anchor='lm')
        d.text((W // 2, 236), 'AI 热点说人话 · 新工具先替你试', font=font(28, 'medium'), fill=(200, 205, 230), anchor='mm')
        frames.append(im.convert('P', palette=Image.ADAPTIVE, colors=64))
    out = OUT / 'top-follow.gif'
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=90, loop=0, optimize=True)
    print(out, out.stat().st_size // 1024, 'KB')


POSTER_PROMPT = (
    '竖版公众号文末关注海报的上半部分设计，横宽比 3:2。背景：深海军蓝到靛紫的柔和渐变，带非常淡的网格和柔光。'
    '画面左侧是 3D 粘土质感的可爱插画：一个戴眼镜、穿深色外套的年轻男性产品经理小人，坐在笔记本电脑前，屏幕发光，桌上有咖啡和便利贴，柔和电影感灯光，金色轮廓光。'
    '画面右侧是超大号现代粗黑体中文标题，分两行：第一行白色「关注示例作者」，第二行亮黄色「天天拿AI干活」。'
    '标题下方三行白色小字，每行前面一个亮黄色小圆点：「AI热点说人话」「新工具先替你试」「照着就能抄的AI用法」。'
    '每个字都必须准确无误，笔画清晰，带轻微投影。除了上面指定的文字，不要出现任何其他文字、字母、数字、logo、二维码或水印。整体干净、高级、对比强。'
)


def poster():
    W = 1080
    art_p = OUT / 'poster-art.png'
    gen_image(POSTER_PROMPT, art_p, size='1536x1024')
    art = Image.open(art_p).convert('RGB').resize((W, int(1024 * W / 1536)), Image.LANCZOS)  # 1080×720
    H = art.height + 620
    im = Image.new('RGB', (W, H), NAVY1)
    im.paste(art, (0, 0))
    # 下半：白卡 + 二维码 + 说明
    bottom = gradient(W, H - art.height)
    im.paste(bottom, (0, art.height))
    d = ImageDraw.Draw(im)
    card = [90, art.height + 40, W - 90, H - 50]
    d.rounded_rectangle(card, 36, fill=WHITE)
    qr = Image.open(OUT / 'gzh-qrcode.jpg').convert('RGB').resize((400, 400), Image.LANCZOS)
    im.paste(qr, (card[0] + 40, card[1] + (card[3] - card[1] - 400) // 2))
    tx = card[0] + 40 + 400 + 40
    cy = (card[1] + card[3]) // 2
    d.text((tx, cy - 120), '长按识别二维码', font=font(46, 'semibold'), fill=(24, 24, 28), anchor='lm')
    d.text((tx, cy - 50), f'关注「{NAME}」', font=font(34, 'semibold'), fill=(220, 38, 38), anchor='lm')
    for i, line in enumerate(['每天一篇 AI 实测', '有用的提示词直接抄', '不吹不黑，只聊用得上的']):
        d.text((tx, cy + 20 + i * 52), '· ' + line, font=font(30, 'medium'), fill=(80, 80, 90), anchor='lm')
    out = OUT / 'end-follow.jpg'
    im.save(out, quality=92)
    print(out, im.size)


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    OUT.mkdir(parents=True, exist_ok=True)
    if what in ('gif', 'all'):
        top_gif()
    if what in ('poster', 'all'):
        poster()


BANNER_PROMPT = (
    '超宽横版个人主页头图设计，统一的科技博主风格。背景：深海军蓝到靛紫的柔和渐变，带非常淡的网格和柔光。'
    '所有内容都集中在画面正中间约 40% 高度的横向带状区域里，上下各留出大量纯背景（方便不同平台裁切）。'
    '左侧：3D 粘土质感的可爱插画，一个戴眼镜、穿深色外套的年轻男性产品经理小人，坐在发光的笔记本电脑前，柔和电影感灯光，金色轮廓光。'
    '右侧：超大号现代粗黑体中文，第一行白色「示例作者｜天天拿AI干活」，第二行亮黄色较小字号「AI热点说人话 · 新工具先替你试」。'
    '每个字都必须准确无误，笔画清晰。除了指定文字，不要出现任何其他文字、字母、数字、logo、二维码或水印。整体干净、高级。'
)
# 各平台主页头图/背景尺寸（宽, 高）：都从母版中间横带裁，保证人物和标语都在
BANNER_SIZES = {'抖音主页背景': (1125, 633), '微博封面': (1920, 640), '知乎封面': (1920, 480), 'B站头图': (2560, 400), '视频号与通用16比9': (1920, 1080)}


def banners():
    raw = OUT / 'banner-raw.png'
    gen_image(BANNER_PROMPT, raw, size='1536x1024')
    art = Image.open(raw).convert('RGB')
    from make_cover import _blur_fill
    for name, (W, H) in BANNER_SIZES.items():
        # 先按宽度缩放，取中间横带；高度不够的平台（16:9 等）用同图虚化补边
        s = W / art.width
        fg = art.resize((W, int(art.height * s)), Image.LANCZOS)
        if fg.height >= H:
            y = (fg.height - H) // 2
            out = fg.crop((0, y, W, y + H))
        else:
            out = _blur_fill(art, W, H)
            out.paste(fg, (0, (H - fg.height) // 2))
        p = OUT / f'banner-{name}.jpg'
        out.save(p, quality=92)
        print(p, out.size)


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'banner':
    OUT.mkdir(parents=True, exist_ok=True)
    banners()


# ---------------------------------------------------------------------------
# v2（10-16 用户：引导关注太丑）：改成和公众号正文一致的红白简约风，用示例作者表情包立绘，不用深蓝大横幅
RED, RED_SOFT, INK, GREY = (220, 38, 38), (254, 242, 242), (28, 25, 23), (120, 113, 108)
STK = ROOT / 'assets/stickers/creator/png1024'


def _head(size):
    """从定稿形象里裁出头像（圆形）。"""
    im = Image.open(STK / '00_定稿形象.png').convert('RGBA')
    bb = im.getbbox()
    w = bb[2] - bb[0]
    head = im.crop((bb[0], bb[1], bb[2], bb[1] + int(w * 1.0)))
    head = head.resize((size, size), Image.LANCZOS)
    bg = Image.new('RGBA', (size, size), RED_SOFT + (255,))
    bg.alpha_composite(head)
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.paste(bg, (0, 0), mask)
    return out


def top_gif_v2():
    import math
    W, H, N = 1080, 150, 14
    head = _head(96)
    frames = []
    for k in range(N):
        im = Image.new('RGBA', (W, H), (255, 255, 255, 255))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([20, 18, W - 20, H - 18], 57, fill=RED_SOFT + (255,), outline=(254, 202, 202, 255), width=2)
        im.alpha_composite(head, (40, (H - 96) // 2))
        d.text((158, 58), '点击上方蓝字', font=font(30, 'medium'), fill=GREY, anchor='lm')
        d.text((158, 98), f'「{NAME}」', font=font(38, 'semibold'), fill=INK, anchor='lm')
        # 右侧红色「关注」胶囊，轻轻上下跳
        dy = int(5 * math.sin(2 * math.pi * k / N))
        bx, by = W - 230, H // 2 - 32 + dy
        d.rounded_rectangle([bx, by, bx + 180, by + 64], 32, fill=RED + (255,))
        d.text((bx + 90, by + 32), '+ 关注', font=font(32, 'semibold'), fill=(255, 255, 255), anchor='mm')
        # 指向胶囊的小箭头（往上指）
        ax = bx - 40
        d.polygon([(ax, by + 10), (ax - 14, by + 34), (ax + 14, by + 34)], fill=RED + (255,))
        d.rectangle([ax - 5, by + 32, ax + 5, by + 54], fill=RED + (255,))
        frames.append(im.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=96))
    out = OUT / 'top-follow-v2.gif'
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=100, loop=0, optimize=True)
    print(out, out.stat().st_size // 1024, 'KB')


def end_card_v2():
    W, H = 1080, 620
    im = Image.new('RGBA', (W, H), (255, 255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([20, 20, W - 20, H - 20], 36, fill=(255, 255, 255, 255), outline=(254, 202, 202, 255), width=3)
    d.rounded_rectangle([20, 20, W - 20, 120], 36, fill=RED_SOFT + (255,))
    d.rectangle([20, 84, W - 20, 120], fill=RED_SOFT + (255,))
    d.text((W // 2, 70), '关注示例作者，每天一篇 AI 实测', font=font(40, 'semibold'), fill=RED, anchor='mm')
    # 左：示例作者比心立绘
    fig = Image.open(STK / '05_比心.png').convert('RGBA')
    fig = fig.crop(fig.getbbox())
    s = 430 / fig.height
    fig = fig.resize((int(fig.width * s), 430), Image.LANCZOS)
    im.alpha_composite(fig, (60, H - 40 - fig.height))
    # 中：账号名 + 三条理由
    x = 60 + fig.width + 30
    d.text((x, 190), NAME, font=font(46, 'semibold'), fill=INK, anchor='lm')
    d.text((x, 245), '天天拿 AI 干活的产品经理', font=font(28, 'medium'), fill=GREY, anchor='lm')
    for i, t in enumerate(['AI 热点说人话', '新工具先替你试', '能抄的提示词直接给']):
        y = 320 + i * 62
        d.ellipse([x, y - 9, x + 18, y + 9], fill=RED)
        d.text((x + 34, y), t, font=font(32, 'medium'), fill=INK, anchor='lm')
    # 右：二维码
    qr = Image.open(OUT / 'gzh-qrcode.jpg').convert('RGB').resize((250, 250), Image.LANCZOS)
    qx, qy = W - 60 - 250, 175
    d.rounded_rectangle([qx - 14, qy - 14, qx + 264, qy + 264], 20, outline=(254, 202, 202, 255), width=3)
    im.paste(qr, (qx, qy))
    d.text((qx + 125, qy + 300), '长按识别 · 关注', font=font(28, 'semibold'), fill=RED, anchor='mm')
    out = OUT / 'end-follow-v2.jpg'
    im.convert('RGB').save(out, quality=93)
    print(out, im.size)


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'v2':
    top_gif_v2()
    end_card_v2()
