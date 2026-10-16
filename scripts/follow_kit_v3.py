#!/usr/bin/env python3
"""公众号引导关注 v3：用 HTML 设计稿 + 无头浏览器渲染成图（v1 AI 海报、v2 PIL 红白卡都被用户说丑）。

配色跟示例作者品牌一致（make_cover.BRAND_STYLE['creator']：深海军蓝→靛紫渐变 + 白字 + 亮黄强调），
和文中 3D 信息图、视频封面是一套，所以换文章主题色也不用重做。
人物用用户自己的形象（assets/stickers/creator/png1024），二维码是真码（assets/follow-kit/gzh-qrcode.jpg），
人物和文字分区摆放，互不遮挡（用户规则：人物不要挡到字）。

用法：.venv/bin/python scripts/follow_kit_v3.py [navy|red|light]   # 出 top-follow-v3[-red].gif、end-follow-v3a/b[-red].jpg 到 assets/follow-kit/
"""
import pathlib, sys
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
KIT = ROOT / 'assets/follow-kit'
STK = ROOT / 'assets/stickers/creator/png1024'
AVATAR = ROOT / 'assets/avatar/creator-avatar-1024.jpg'
QR = KIT / 'gzh-qrcode.jpg'
NAME = '示例AI周刊'

BASE_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:transparent;font-family:'PingFang SC','Hiragino Sans GB',-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
.navy{background-color:#141a52;background-image:linear-gradient(rgba(255,255,255,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.045) 1px,transparent 1px),radial-gradient(120% 140% at 85% 0%,#3b2a8f 0%,rgba(59,42,143,0) 55%),linear-gradient(135deg,#0d1442 0%,#1a1c5e 55%,#2a1a6e 100%);
  background-size:36px 36px,36px 36px,100% 100%,100% 100%}
.y{color:#FFD43B}
.flat{background:linear-gradient(110deg,#0f1548 0%,#1d1d63 60%,#2c1b70 100%)}
"""


def top_html(t):
    """顶部横条：头像 + 「点击上方蓝字 关注」+ 黄色关注按钮；t∈[0,1) 控制箭头跳动和按钮呼吸。"""
    import math
    bob = -10 * abs(math.sin(math.pi * t))           # 箭头上跳
    pulse = 1 + 0.05 * math.sin(2 * math.pi * t)       # 按钮呼吸
    glow = 0.35 + 0.35 * (0.5 + 0.5 * math.sin(2 * math.pi * t))
    return f"""<!doctype html><meta charset=utf-8><style>{BASE_CSS}
.bar{{width:1080px;height:168px;border-radius:28px;position:relative;overflow:hidden;display:flex;align-items:center;padding:0 40px 0 30px}}
.av{{width:112px;height:112px;border-radius:50%;background:url('{AVATAR.as_uri()}') center 18%/cover;border:5px solid #FFD43B;box-shadow:0 0 0 6px rgba(255,212,59,.18)}}
.txt{{margin-left:28px;flex:1}}
.l1{{font-size:30px;color:rgba(255,255,255,.72);letter-spacing:2px}}
.l2{{font-size:46px;font-weight:800;color:#fff;margin-top:4px;letter-spacing:1px}}
.arrow{{width:0;height:0;border-left:16px solid transparent;border-right:16px solid transparent;border-bottom:22px solid #FFD43B;margin:0 26px 0 0;transform:translateY({bob:.1f}px)}}
.stem{{width:10px;height:22px;background:#FFD43B;margin:0 auto;border-radius:0 0 3px 3px}}
.btn{{transform:scale({pulse:.3f});background:#FFD43B;color:#1a1c5e;font-size:40px;font-weight:900;padding:18px 40px;border-radius:999px;box-shadow:0 0 34px rgba(255,212,59,{glow:.2f}),0 6px 0 #c9a300}}
</style><div class="bar flat"><div class="av"></div><div class="txt"><div class="l1">点击上方蓝字 · 设为星标</div><div class="l2">关注「<span class="y">{NAME}</span>」</div></div>
<div style="transform:translateY({bob:.1f}px)"><div class="arrow" style="margin:0 auto"></div><div class="stem"></div></div><div style="width:24px"></div><div class="btn">+ 关注</div></div>"""


def end_html_a(t=None, bare=False):
    """文末卡片 A（横版 1080×640）：左边人物（点赞关注）站在光圈里，右边账号名、价值点、二维码。
    t∈[0,1) 时出动图帧（10-16 用户：关注卡片的表情做成动态）：人物上下轻晃+微摆、爱心往上飘、虚线环慢转；
    二维码和文字全程不动，保证长按识别。"""
    import math
    fig = STK / '07_点赞关注.png'
    anim = ''
    if t is not None:
        bob = -9 * (0.5 - 0.5 * math.cos(2 * math.pi * t))
        rot = 2.2 * math.sin(2 * math.pi * t)
        anim = (f'.fig{{transform:translateY({bob:.1f}px) rotate({rot:.2f}deg);transform-origin:50% 100%}}'
                f'.ring{{transform:rotate({t * 60:.1f}deg)}}')
        for i, (x0, ph, sz) in enumerate(((392, 0.0, 30), (410, 0.33, 22), (380, 0.66, 18))):   # 人物右侧和文字之间的空白处，不压脸
            u = (t + ph) % 1
            anim += (f'.ht{i}{{position:absolute;left:{x0 + 10 * math.sin(2 * math.pi * u):.0f}px;top:{330 - 190 * u:.0f}px;font-size:{sz}px;'
                     f'opacity:{min(1, u * 4) * (1 - u) * 1.3:.2f};transform:scale({0.6 + 0.6 * u:.2f});color:#F87171}}')
    hearts = ''.join(f'<div class="ht{i}">&#10084;</div>' for i in range(3)) if t is not None else ''
    if bare:   # 左边留给表情包 GIF（end_gif_sticker），右栏右移一点，给 GIF 底部的大字留宽度
        anim += '.fig,.ring{display:none}.r{left:480px}.halo{left:30px;top:150px}'
    return f"""<!doctype html><meta charset=utf-8><style>{BASE_CSS}
.card{{width:1080px;height:640px;border-radius:36px;position:relative;overflow:hidden}}
.halo{{position:absolute;left:40px;top:120px;width:380px;height:380px;border-radius:50%;background:radial-gradient(circle,rgba(255,212,59,.38) 0%,rgba(255,212,59,.10) 45%,rgba(255,212,59,0) 70%)}}
.ring{{position:absolute;left:70px;top:150px;width:320px;height:320px;border-radius:50%;border:3px solid rgba(255,212,59,.45)}}
.fig{{position:absolute;left:60px;bottom:-6px;height:600px}}
.r{{position:absolute;left:440px;top:58px;right:48px}}
.tag{{display:inline-block;font-size:24px;font-weight:700;color:#1a1c5e;background:#FFD43B;border-radius:999px;padding:6px 20px;letter-spacing:2px}}
.nm{{font-size:62px;font-weight:900;color:#fff;margin-top:18px;letter-spacing:1px}}
.sub{{font-size:30px;margin-top:8px;font-weight:600}}
.pts{{margin-top:26px}}
.pt{{font-size:28px;color:rgba(255,255,255,.88);margin:12px 0;display:flex;align-items:center}}
.pt i{{width:12px;height:12px;border-radius:3px;background:#FFD43B;margin-right:16px;transform:rotate(45deg)}}
.qrbox{{position:absolute;right:48px;bottom:48px;display:flex;align-items:center;background:#fff;border-radius:24px;padding:14px 26px 14px 14px;box-shadow:0 10px 40px rgba(0,0,0,.35)}}
.qr{{width:150px;height:150px;border-radius:12px;background:url('{QR.as_uri()}') center/cover}}
.qt{{margin-left:20px}}
.q1{{font-size:30px;font-weight:900;color:#1a1c5e}}
.q2{{font-size:22px;color:#6b6f9a;margin-top:6px}}
{anim}
</style><div class="card navy grid"><div class="halo"></div><div class="ring"></div><img class="fig" src="{fig.as_uri()}">{hearts}
<div class="r"><span class="tag">关注我 · 每天一篇</span><div class="nm">{NAME}</div><div class="sub y">天天拿 AI 干活的产品经理</div>
<div class="pts"><div class="pt"><i></i>AI 热点，用人话讲清楚</div><div class="pt"><i></i>新工具，我先替你试</div></div></div>
<div class="qrbox"><div class="qr"></div><div class="qt"><div class="q1">长按识别 · 关注</div><div class="q2">下一篇实测第一时间推给你</div></div></div></div>"""


def end_html_b():
    """文末卡片 B（竖版 1080×1180）：上半人物 + 大标题，中间三个价值点卡，下面白底二维码条。"""
    fig = STK / '00_定稿形象.png'
    pts = [('热点', 'AI 新闻说人话'), ('实测', '新工具先替你试'), ('能抄', '提示词直接给')]
    chips = ''.join(f'<div class="chip"><div class="c1 y">{a}</div><div class="c2">{b}</div></div>' for a, b in pts)
    return f"""<!doctype html><meta charset=utf-8><style>{BASE_CSS}
.card{{width:1080px;height:1180px;border-radius:40px;position:relative;overflow:hidden}}
.halo{{position:absolute;left:600px;top:40px;width:460px;height:460px;border-radius:50%;background:radial-gradient(circle,rgba(255,212,59,.36) 0%,rgba(255,212,59,.08) 50%,rgba(255,212,59,0) 70%)}}
.fig{{position:absolute;left:640px;top:36px;height:560px}}
.hd{{position:absolute;left:72px;top:96px;width:600px}}
.k{{font-size:28px;color:rgba(255,255,255,.7);letter-spacing:6px}}
.h1{{font-size:80px;font-weight:900;color:#fff;line-height:1.18;margin-top:18px;white-space:nowrap}}
.h2{{font-size:44px;font-weight:800;margin-top:22px}}
.chips{{position:absolute;left:72px;right:72px;top:640px;display:flex;gap:24px}}
.chip{{flex:1;background:rgba(255,255,255,.08);border:2px solid rgba(255,255,255,.14);border-radius:24px;padding:26px 0;text-align:center}}
.c1{{font-size:40px;font-weight:900}}
.c2{{font-size:26px;color:rgba(255,255,255,.85);margin-top:8px}}
.qrbox{{position:absolute;left:72px;right:72px;bottom:72px;height:270px;background:#fff;border-radius:30px;display:flex;align-items:center;padding:0 40px;box-shadow:0 14px 50px rgba(0,0,0,.35)}}
.qr{{width:210px;height:210px;border-radius:14px;background:url('{QR.as_uri()}') center/cover;flex-shrink:0}}
.qt{{margin-left:40px}}
.q1{{font-size:46px;font-weight:900;color:#1a1c5e}}
.q2{{font-size:28px;color:#6b6f9a;margin-top:12px}}
.hand{{display:inline-block;background:#FFD43B;color:#1a1c5e;font-size:26px;font-weight:800;border-radius:999px;padding:8px 22px;margin-top:20px}}
</style><div class="card navy grid"><div class="halo"></div><img class="fig" src="{fig.as_uri()}">
<div class="hd"><div class="k">FOLLOW · 示例作者</div><div class="h1">关注示例作者<br>一起拿 AI 干活</div><div class="h2 y">{NAME}</div></div>
<div class="chips">{chips}</div>
<div class="qrbox"><div class="qr"></div><div class="qt"><div class="q1">长按识别二维码</div><div class="q2">每天一篇 AI 实测，不吹不黑</div><div class="hand">关注后回看往期 →</div></div></div></div>"""


# 红色主题（10-16 用户定了红色排版）：同一套版式，按文章主题色换色，深红渐变 + 白字 + 浅金点缀
RED = [  # 先换具体组件，再换通用底色（替换作用在渲染后的 HTML 上，单花括号）
    ('.hand{display:inline-block;background:#FFD43B;color:#1a1c5e', '.hand{display:inline-block;background:#FEE2E2;color:#b91c1c'),
    ('border:5px solid #FFD43B;box-shadow:0 0 0 6px rgba(255,212,59,.18)', 'border:5px solid #fff;box-shadow:0 0 0 6px rgba(255,255,255,.22)'),
    ('border-bottom:22px solid #FFD43B', 'border-bottom:22px solid #fff'),
    ('.stem{width:10px;height:22px;background:#FFD43B', '.stem{width:10px;height:22px;background:#fff'),
    ('background:#FFD43B;color:#1a1c5e', 'background:#fff;color:#b91c1c'),
    ('color:#1a1c5e;background:#FFD43B', 'color:#b91c1c;background:#fff'),
    ('0 6px 0 #c9a300', '0 6px 0 #fca5a5'), ('rgba(255,212,59,0.', 'rgba(255,255,255,0.'),
    ('.pt i{width:12px;height:12px;border-radius:3px;background:#FFD43B', '.pt i{width:12px;height:12px;border-radius:3px;background:#FFE08A'),
    ('rgba(255,212,59,.38)', 'rgba(255,224,138,.40)'), ('rgba(255,212,59,.36)', 'rgba(255,224,138,.38)'),
    ('rgba(255,212,59,.10)', 'rgba(255,224,138,.10)'), ('rgba(255,212,59,.08)', 'rgba(255,224,138,.08)'), ('rgba(255,212,59,0)', 'rgba(255,224,138,0)'),
    ('border:3px solid rgba(255,212,59,.45)', 'border:3px solid rgba(255,255,255,.45)'),
    ('.y{color:#FFD43B}', '.y{color:#FFE08A}'),
    ('#6b6f9a', '#9b6b6b'), ('rgba(0,0,0,.35)', 'rgba(90,0,0,.35)'),
    ('#141a52', '#8f1515'), ('#3b2a8f', '#ef4444'), ('rgba(59,42,143,0)', 'rgba(239,68,68,0)'),
    ('#0d1442', '#7a1010'), ('#1a1c5e', '#b91c1c'), ('#2a1a6e', '#dc2626'),
    ('#0f1548', '#991b1b'), ('#1d1d63', '#c81e1e'), ('#2c1b70', '#dc2626')]


# 浅色主题（10-16 用户：红底卡片「太红了」）：白→极浅暖粉底 + 深色字，红色只留给关注按钮、标签、账号名
LIGHT = [
    # 底色
    ('.navy{background-color:#141a52;background-image:', '.navy{background-color:#fff;background-image:'),
    ('rgba(255,255,255,.045) 1px', 'rgba(220,38,38,.035) 1px'),
    ('radial-gradient(120% 140% at 85% 0%,#3b2a8f 0%,rgba(59,42,143,0) 55%),linear-gradient(135deg,#0d1442 0%,#1a1c5e 55%,#2a1a6e 100%)',
     'radial-gradient(120% 140% at 90% 0%,#FFE4DF 0%,rgba(255,228,223,0) 55%),linear-gradient(135deg,#FFFFFF 0%,#FFFAF8 55%,#FFF1EE 100%)'),
    ('.flat{background:linear-gradient(110deg,#0f1548 0%,#1d1d63 60%,#2c1b70 100%)}', '.flat{background:linear-gradient(110deg,#FFFFFF 0%,#FFF7F5 100%);border:3px solid #F6D5CF}'),
    ('.card{width:1080px;height:640px;border-radius:36px;', '.card{width:1080px;height:640px;border-radius:36px;border:3px solid #F3D3CD;'),
    ('.card{width:1080px;height:1180px;border-radius:40px;', '.card{width:1080px;height:1180px;border-radius:40px;border:3px solid #F3D3CD;'),
    # 顶部横条
    ('border:5px solid #FFD43B;box-shadow:0 0 0 6px rgba(255,212,59,.18)', 'border:5px solid #fff;box-shadow:0 0 0 3px #FCA5A5'),
    ('.l1{font-size:30px;color:rgba(255,255,255,.72)', '.l1{font-size:30px;color:#8A817C'),
    ('.l2{font-size:46px;font-weight:800;color:#fff', '.l2{font-size:46px;font-weight:800;color:#1C1917'),
    ('border-bottom:22px solid #FFD43B', 'border-bottom:22px solid #DC2626'),
    ('.stem{width:10px;height:22px;background:#FFD43B', '.stem{width:10px;height:22px;background:#DC2626'),
    ('background:#FFD43B;color:#1a1c5e;font-size:40px', 'background:#DC2626;color:#fff;font-size:40px'),
    ('0 6px 0 #c9a300', '0 5px 0 #B91C1C'), ('rgba(255,212,59,0.', 'rgba(220,38,38,0.'),
    # 文末卡片 A
    ('rgba(255,212,59,.38) 0%,rgba(255,212,59,.10) 45%,rgba(255,212,59,0) 70%', 'rgba(254,202,202,.55) 0%,rgba(254,202,202,.18) 45%,rgba(254,202,202,0) 70%'),
    ('border:3px solid rgba(255,212,59,.45)', 'border:3px dashed rgba(220,38,38,.22)'),
    ('color:#1a1c5e;background:#FFD43B;border-radius:999px', 'color:#fff;background:#DC2626;border-radius:999px'),
    ('.nm{font-size:62px;font-weight:900;color:#fff', '.nm{font-size:62px;font-weight:900;color:#1C1917'),
    ('.pt{font-size:28px;color:rgba(255,255,255,.88)', '.pt{font-size:28px;color:#44403C'),
    ('.pt i{width:12px;height:12px;border-radius:3px;background:#FFD43B', '.pt i{width:12px;height:12px;border-radius:3px;background:#DC2626'),
    ('box-shadow:0 10px 40px rgba(0,0,0,.35)', 'border:2px solid #F3D3CD;box-shadow:0 8px 28px rgba(150,60,40,.10)'),
    # 文末卡片 B
    ('rgba(255,212,59,.36) 0%,rgba(255,212,59,.08) 50%,rgba(255,212,59,0) 70%', 'rgba(254,202,202,.5) 0%,rgba(254,202,202,.15) 50%,rgba(254,202,202,0) 70%'),
    ('.k{font-size:28px;color:rgba(255,255,255,.7)', '.k{font-size:28px;color:#A8A29E'),
    ('.h1{font-size:80px;font-weight:900;color:#fff', '.h1{font-size:80px;font-weight:900;color:#1C1917'),
    ('background:rgba(255,255,255,.08);border:2px solid rgba(255,255,255,.14)', 'background:#fff;border:2px solid #F3D3CD'),
    ('.c2{font-size:26px;color:rgba(255,255,255,.85)', '.c2{font-size:26px;color:#57534E'),
    ('box-shadow:0 14px 50px rgba(0,0,0,.35)', 'border:2px solid #F3D3CD;box-shadow:0 10px 34px rgba(150,60,40,.10)'),
    ('.hand{display:inline-block;background:#FFD43B;color:#1a1c5e', '.hand{display:inline-block;background:#FEE2E2;color:#B91C1C'),
    # 通用
    ('.y{color:#FFD43B}', '.y{color:#DC2626}'), ('#1a1c5e', '#1C1917'), ('#6b6f9a', '#78716C')]


def themed(html, theme):
    for a, b in {'red': RED, 'light': LIGHT}.get(theme, []):
        html = html.replace(a, b)
    return html


def end_gif_sticker(pg_shot, theme, sticker='07_点赞关注'):
    """文末卡片 A 动图（10-16 用户：直接用表情包本身的 GIF 动画，不要自己做左右晃）。
    静态卡片底图 + 表情包 gif360 原帧（示例作者比心点赞 +「点赞关注」逐字出现），二维码和文字全程不动。"""
    base_png = KIT / '_endbase.png'
    pg_shot(end_html_a(bare=True), base_png, 1080, 640)
    base = Image.open(base_png).convert('RGBA'); base_png.unlink()
    bg = Image.new('RGBA', base.size, (255, 255, 255, 255)); bg.alpha_composite(base)
    W, H = 750, 444
    base = bg.convert('RGB').resize((W, H), Image.LANCZOS)
    g = Image.open(ROOT / f'assets/stickers/creator/gif360/{sticker}.gif')
    S = 300; x0, y0 = 14, (H - S) // 2 + 6
    frames, durs = [], []
    for i in range(g.n_frames):
        g.seek(i); durs.append(g.info.get('duration', 100))
        st = g.convert('RGBA').resize((S, S), Image.LANCZOS)
        fr = base.convert('RGBA'); fr.alpha_composite(st, (x0, y0)); frames.append(fr.convert('RGB'))
    strip = Image.new('RGB', (W, H * 4))
    for k in range(4): strip.paste(frames[min(len(frames) - 1, k * len(frames) // 4 + len(frames) // 8)], (0, H * k))
    pal = strip.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.Dither.NONE)
    q = [fr.quantize(palette=pal, dither=Image.Dither.NONE) for fr in frames]
    sfx = '' if theme == 'navy' else f'-{theme}'
    out = KIT / f'end-follow-v3s{sfx}.gif'
    q[0].save(out, save_all=True, append_images=q[1:], duration=durs, loop=0, optimize=True, disposal=1)
    return out


def render(theme='navy'):
    from playwright.sync_api import sync_playwright
    sfx = '' if theme == 'navy' else f'-{theme}'
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1080, 'height': 1200}, device_scale_factor=1)

        def shot(html, path, w, h, scale=1):
            tmp = KIT / '_render.html'
            tmp.write_text(themed(html, theme))
            pg.set_viewport_size({'width': w, 'height': h})
            pg.goto(tmp.as_uri()); pg.wait_for_timeout(400)
            pg.screenshot(path=str(path), clip={'x': 0, 'y': 0, 'width': w, 'height': h}, omit_background=True)
            tmp.unlink()

        # 顶部横条动图：12 帧
        frames = []
        for i in range(8):
            f = KIT / f'_top{i}.png'
            shot(top_html(i / 8), f, 1080, 168)
            frames.append(Image.open(f).convert('RGBA'))
            f.unlink()
        flat = []
        for fr in frames:
            bg = Image.new('RGBA', fr.size, (255, 255, 255, 255)); bg.alpha_composite(fr)
            flat.append(bg.convert('RGB').quantize(colors=48, method=Image.MEDIANCUT, dither=Image.Dither.NONE))
        gif = KIT / f'top-follow-v3{sfx}.gif'
        flat[0].save(gif, save_all=True, append_images=flat[1:], duration=110, loop=0, optimize=True, disposal=2)
        out['top'] = gif
        for key, fn, h in (('end_a', end_html_a, 640), ('end_b', end_html_b, 1180)):
            png = KIT / f'end-follow-v3{key[-1]}{sfx}.png'
            shot(fn(), png, 1080, h)
            im = Image.open(png).convert('RGBA'); bg = Image.new('RGBA', im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
            jpg = png.with_suffix('.jpg'); bg.convert('RGB').save(jpg, quality=90); png.unlink()
            out[key] = jpg
        # 文末卡片 A 动图：16 帧，缩到 750 宽（公众号显示宽度足够），二维码区域不动
        frames = []
        for i in range(16):
            f = KIT / f'_end{i}.png'
            shot(end_html_a(i / 16), f, 1080, 640)
            fr = Image.open(f).convert('RGBA'); f.unlink()
            bg = Image.new('RGBA', fr.size, (255, 255, 255, 255)); bg.alpha_composite(fr)
            frames.append(bg.convert('RGB').resize((750, 444), Image.LANCZOS))
        strip = Image.new('RGB', (750, 444 * 4 + 480))    # 用几帧拼起来取调色板；人物手边的蓝色点赞/红爱心面积小，放大一块加权，免得被压成灰
        for k in range(4): strip.paste(frames[k * 4], (0, 444 * k))
        strip.paste(frames[0].crop((30, 120, 300, 300)).resize((750, 480)), (0, 444 * 4))
        pal = strip.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.Dither.NONE)
        q = [fr.quantize(palette=pal, dither=Image.Dither.NONE) for fr in frames]
        egif = KIT / f'end-follow-v3a{sfx}.gif'
        q[0].save(egif, save_all=True, append_images=q[1:], duration=100, loop=0, optimize=True, disposal=1)
        out['end_a_gif'] = egif
        out['end_sticker_gif'] = end_gif_sticker(shot, theme)
        b.close()
    for k, v in out.items():
        print(k, v.name, f'{v.stat().st_size // 1024}KB')
    return out


if __name__ == '__main__':
    render(sys.argv[1] if len(sys.argv) > 1 else 'navy')
