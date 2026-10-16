#!/usr/bin/env python3
"""统一封面模板（抖音 / 视频号 / 小红书视频）：和动效视频同一套视觉——深蓝渐变底、网格、蓝黄光斑、
白字主标题 + 黄字反差行、左上栏目角标、系列编号、底部品牌。

主页格子是 3:4，会把 9:16 封面上下各裁掉 240px，所以所有文字都放在中间 1080×1440 的安全区里。

用法:
  .venv/bin/python scripts/make_cover.py --title "DeepSeek崩了5小时\\n补偿只给一种人" --column 热点 \
      [--series "第3集"] [--sub "API用户全额返赠金"] --out cover.jpg [--ratio 9:16|3:4]
  第一行白字，最后一行黄字（反差/结论）；每行建议 ≤8 个字，最多 3 行。
也可以 from make_cover import make_cover 在脚本里调用。
"""
import argparse, pathlib, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
FONT = ROOT / 'templates/hf/assets/NotoSansSC.ttf'
BG1, BG2 = (10, 14, 26), (22, 18, 58)
YELLOW, BLUE, WHITE, INK = (255, 214, 10), (61, 169, 252), (255, 255, 255), (17, 17, 17)
# 封面插画统一画风（作图 API，gpt-image-2.5）。所有封面共用这一段，保证主页统一。
COVER_STYLE = ('3D render, soft clay and glossy plastic materials, cute rounded shapes, cinematic soft studio lighting, '
               'deep navy blue to indigo background with subtle gradient, warm golden rim light, '
               'single clear subject placed in the lower half of the frame, the upper 40% of the frame is empty dark background, '
               'clean composition, high detail, vertical poster, no text, no letters, no numbers, no logo, no watermark, no UI text')

COLUMNS = {  # 栏目角标：文字 + 底色（各栏目固定颜色，主页上一眼能分）
    '热点': ('AI热点说人话', (255, 107, 74)),
    '先试': ('示例作者先试', BLUE),
    '算账': ('示例作者算账', (52, 211, 153)),
    '抄作业': ('抄作业', YELLOW),
}


def font(size, weight=b'Black'):
    f = ImageFont.truetype(str(FONT), size)
    f.set_variation_by_name(weight)
    return f


def fit(draw, text, max_w, start, weight=b'Black', min_size=80):
    s = start
    while s > min_size:
        f = font(s, weight)
        if draw.textlength(text, font=f) <= max_w:
            return f
        s -= 4
    return font(min_size, weight)


def background(w, h):
    import numpy as np
    t = np.linspace(0, 1, h)[:, None, None]
    base = np.array(BG1)[None, None, :] * (1 - t) + np.array(BG2)[None, None, :] * t
    base = np.repeat(base, w, axis=1)
    glow = Image.new('RGB', (w, h), (0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse([-260, int(h * 0.12), 520, int(h * 0.12) + 780], fill=(25, 70, 110))   # 蓝光斑（左上）
    g.ellipse([int(w * 0.45), int(h * 0.62), int(w * 0.45) + 760, int(h * 0.62) + 760], fill=(110, 92, 10))  # 黄光斑（右下）
    glow = np.asarray(glow.filter(ImageFilter.GaussianBlur(140)), dtype=float)
    img = Image.fromarray(np.clip(base + glow, 0, 255).astype('uint8'))
    d = ImageDraw.Draw(img, 'RGBA')
    for x in range(0, w, 72):
        d.line([(x, 0), (x, h)], fill=(255, 255, 255, 12), width=1)
    for y in range(0, h, 72):
        d.line([(0, y), (w, y)], fill=(255, 255, 255, 12), width=1)
    return img


def pill(d, xy, text, f, fill, color, pad=(30, 14), radius=18, outline=None):
    x, y = xy
    tw = d.textlength(text, font=f)
    asc, desc = f.getmetrics()
    box = [x, y, x + tw + pad[0] * 2, y + asc + desc + pad[1] * 2 - 6]
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=4 if outline else 0)
    d.text((x + pad[0], y + pad[1] - 4), text, font=f, fill=color)
    return box


def illustration(prompt, art_path, W, H):
    """作图 API 生成主题插画（缓存到 art_path），铺满画布，顶部压暗给标题让位。"""
    import numpy as np
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from common import gen_image
    gen_image(prompt + ', ' + COVER_STYLE, art_path, size='1024x1536')
    art = Image.open(art_path).convert('RGB')
    scale = max(W / art.width, H / art.height)
    art = art.resize((int(art.width * scale) + 1, int(art.height * scale) + 1), Image.LANCZOS)
    x = (art.width - W) // 2
    y = max(0, art.height - H)  # 底部对齐：主体在下半部分
    art = art.crop((x, y, x + W, y + H))
    a = np.asarray(art, dtype=float)
    yy = np.linspace(0, 1, H)[:, None, None]
    shade = np.clip(1 - (yy - 0.0) / 0.55, 0, 1) * 0.72   # 上半部分压暗，标题区更清楚
    a = a * (1 - shade) + np.array(BG1)[None, None, :] * shade
    return Image.fromarray(a.clip(0, 255).astype('uint8'))


def make_cover(title, column='热点', out='cover.jpg', series=None, sub=None, ratio='9:16', brand='示例聊AI',
               prompt=None, art_path=None):
    W = 1080
    H = 1920 if ratio == '9:16' else 1440
    top = 240 if ratio == '9:16' else 0          # 3:4 安全区上沿
    if prompt:
        art_path = art_path or pathlib.Path(out).with_name(pathlib.Path(out).stem + '-art.png')
        img = illustration(prompt, art_path, W, H)
    else:
        img = background(W, H)
    d = ImageDraw.Draw(img, 'RGBA')
    # 栏目角标 + 系列编号（安全区左上）
    label, color = COLUMNS.get(column, COLUMNS['热点'])
    fchip = font(54, b'Black')
    box = pill(d, (72, top + 120), label, fchip, color, INK)
    if series:
        pill(d, (box[2] + 20, top + 120), series, fchip, None, WHITE, outline=(255, 255, 255, 200))
    # 主标题：最多 3 行，最后一行黄色；字号按最长一行自适应
    lines = [l for l in title.split('\n') if l.strip()][:3]
    max_w = W - 72 * 2
    probe = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    size = 230 if len(lines) <= 2 else 190
    f = min((fit(probe, l, max_w, size) for l in lines), key=lambda x: x.size)
    asc, desc = f.getmetrics()
    lh = int((asc + desc) * 1.08)
    block_h = lh * len(lines)
    y0 = (top + 230) if prompt else (top + 300 + max(0, (640 - block_h) // 2))
    for i, line in enumerate(lines):
        fill = YELLOW if (i == len(lines) - 1 and len(lines) > 1) else WHITE
        x = 72
        d.text((x + 6, y0 + i * lh + 8), line, font=f, fill=(0, 0, 0, 150))
        d.text((x, y0 + i * lh), line, font=f, fill=fill, stroke_width=6 if prompt else 0, stroke_fill=(8, 10, 22))
    # 黄色下划条
    y_bar = y0 + block_h + 24
    d.rounded_rectangle([72, y_bar, 72 + 220, y_bar + 16], radius=8, fill=YELLOW)
    # 副标题（插画版不放：会压在主体上显得挤，信息交给标题和视频描述）
    if sub and not prompt:
        fsub = fit(probe, sub, max_w - 60, 64, b'Bold', 40)
        pill(d, (72, y_bar + 56), sub, fsub, (255, 255, 255, 34), WHITE, pad=(28, 16), radius=20)
    # 品牌（安全区底部）
    fb = font(46, b'Bold')
    yb = top + 1440 - 150
    if prompt:  # 插画上加深色底，保证看得清
        tw = d.textlength(brand, font=fb)
        d.rounded_rectangle([56, yb - 10, 72 + 64 + tw + 24, yb + 66], radius=36, fill=(8, 10, 22, 190))
    d.ellipse([72, yb + 6, 72 + 44, yb + 50], fill=YELLOW)
    d.text((72 + 64, yb), brand, font=fb, fill=WHITE)
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--title', required=True)
    ap.add_argument('--column', default='热点', choices=list(COLUMNS))
    ap.add_argument('--series')
    ap.add_argument('--sub')
    ap.add_argument('--ratio', default='9:16', choices=['9:16', '3:4'])
    ap.add_argument('--out', required=True)
    ap.add_argument('--prompt', help='主题插画描述（英文更稳），不写就用纯色底')
    a = ap.parse_args()
    print(make_cover(a.title.replace('\\n', '\n'), a.column, a.out, a.series, a.sub, a.ratio, prompt=a.prompt))


# ---------------------------------------------------------------------------
# v3（10-16 用户要求）：标题直接由作图 API 设计进封面，统一设计提示词保证主页一致。
COLUMN_CN = {'热点': ('AI热点说人话', '珊瑚红'), '先试': ('示例作者先试', '天蓝'), '算账': ('示例作者算账', '薄荷绿'), '抄作业': ('抄作业', '明黄')}
COLUMN_CN['办公课'] = ('AI办公课', '墨绿')   # Office 号（10-16 新增）

# 账号外观：示例作者=深色科技风；Office=浅色办公桌风，两个号的主页一眼能分开
BRAND_STYLE = {
    'creator': {'bg': '深海军蓝到靛紫的柔和渐变，带非常淡的网格和柔光', 'c1': '白色', 'c2': '亮黄色', 'stroke': '深色描边',
                'light': '柔和电影感灯光，金色轮廓光', 'name': '示例聊AI'},
    'office': {'bg': '奶白到浅薄荷绿的柔和渐变，带非常淡的点阵和窗边自然光', 'c1': '深墨绿色', 'c2': '橙色', 'stroke': '白色描边',
               'light': '明亮柔和的自然光，干净的办公桌氛围', 'name': '示例办公课'},
}

# 旧 v3 模板（3D 粘土 + 小机器人，10-16 用户嫌「AI 化太严重」停用），留着只为对照，ai_cover 已不再使用。
AI_COVER_TEMPLATE_V3 = (
    '竖版短视频封面设计，统一的科技博主系列封面风格。'
    '背景：{bg}。'
    '主体：3D 粘土质感的可爱插画，{subject}，放在画面中下部，{light}，质感精致。'
    '标题：画面上部居中偏上，超大号现代粗黑体中文标题，分两行，第一行{c1}「{line1}」，第二行{c2}「{line2}」，'
    '字体粗、笔画清晰锐利，带{stroke}和轻微立体投影，字号占画面宽度约 85%，每个字都必须准确无误。'
    '左上角一个{color}底色的圆角小标签，白色或深色小字「{label}」。{series}'
    '画面底部中间一行小字「{name}」。'
    '构图：上下各留出约 10% 的纯背景边距，标题和主体都在中间区域。整体干净、高级、对比强，像头部知识博主的封面。'
    '人物和插画主体绝对不能压住或遮挡任何文字，文字区域保持干净。'
    '除了上面指定的文字，不要出现任何其他文字、字母、数字、logo 或水印。'
)

# ---------------------------------------------------------------------------
# v4（10-16 用户：「机器人那种 AI 化太严重」「结合我的动漫形象」「颜色根据内容情况和平台风格综合考虑」）
# 统一的是：扁平平面设计 + 示例作者本人动漫形象（白描边贴纸效果）+ 上部两行超大标题 + 左上栏目角标 + 底部账号名；
# 变化的是：背景配色从 4 个品牌色里按内容情绪和平台挑（pick_theme），示例作者的表情动作按内容来（pose）。
# 规范见 运营手册/封面规范.md v2。
CREATOR_REF = ROOT / 'assets/covers/ref/creator-ref.png'      # 示例作者定稿形象（白底），作图时当参考图，保证长相一致
CHAR = ('主角必须是参考图里这个动漫男生「示例作者」：蓬松微乱的黑色短发、细银框透明大圆眼镜、棕色大眼睛、白色圆领T恤外面敞开穿深藏青色夹克；'
        '保持和参考图一模一样的脸、发型、眼镜、服装和配色，保持参考图的中国二次元Q版画风（干净细线稿、柔和赛璐璐平涂上色）。'
        '画面里只有示例作者一个角色，不要机器人、不要其他人物。')
FLAT = ('整体是扁平 2D 插画和平面设计，配色克制，像头部知识博主精心设计的系列封面。背景一直平铺到画面四条边，四周不要边框、不要暗角、不要卡片阴影。'
        '不要 3D 渲染、不要粘土或塑料质感、不要发光特效、不要光斑粒子、不要霓虹渐变、不要景深虚化。'
        '人物和插画绝对不能压住或遮挡任何文字。除了指定的文字，不要出现任何其他文字、字母、数字、logo 或水印。')

THEMES = {   # 名字 -> 作图描述。c1/c2 第一、二行标题；ink 底部署名和描边小标签的颜色
    '夜蓝': dict(bg='深藏青色 #14204A 纯色平涂，带非常细的纸张颗粒质感',
                 deco='右上角一个亮黄色实心圆、几条白色细斜线作平面几何装饰',
                 c1='白色', c2='亮黄色 #FFD60A', ink='白色', light=False),
    '米白': dict(bg='米白色纸张 #F5F0E6 纯色平涂，细微纸纹，四个角落淡淡的漫画网点',
                 deco='人物身后淡淡的放射状漫画速度线',
                 c1='深藏青色 #14204A', c2='深藏青色 #14204A，这一行下面压一道亮黄色 #FFD60A 荧光笔涂抹', ink='深藏青色', light=True),
    '雾蓝': dict(bg='浅雾蓝色 #DCEBFA 纯色平涂，带非常淡的方格纸细线',
                 deco='右上角一个天蓝色 #3DA9FC 实心圆、几条深藏青色细线作平面装饰',
                 c1='深藏青色 #14204A', c2='珊瑚橙色 #FF5A36', ink='深藏青色', light=True),
    # 公众号头条专用（10-16 用户：「封面颜色和内容排版颜色要一致」）：和正文 gzh_red.py 红色排版同一套色值
    '公众号红': dict(bg='纯白色 #FFFFFF 平涂，带非常细的纸张颗粒质感，四角有很淡的浅粉色 #FEF2F2 色块',
                 deco='右上角一个红色 #DC2626 实心小圆点、几条浅粉色 #FECACA 细线作平面装饰',
                 c1='近黑色 #1C1917', c2='红色 #DC2626', ink='近黑色', light=True),
    # Office 号专用（浅色办公风，不放任何人物）
    '奶白': dict(bg='奶白色 #FBF8F1 纯色平涂，带非常细的纸张颗粒质感，右下角一大块浅薄荷绿 #DDF1E6 圆角色块',
                 deco='几条墨绿色细线和小圆点作平面装饰',
                 c1='深墨绿色 #1F5A40', c2='橙色 #E8792B', ink='深墨绿色', light=True),
}
TAGS = {   # 栏目角标（颜色固定，主页上一眼认出栏目）：文字, 底色, 字色
    '热点': ('AI热点说人话', '珊瑚红 #FF6B4A', '白色'),
    '先试': ('示例作者先试', '天蓝色 #3DA9FC', '深藏青色'),
    '算账': ('示例作者算账', '薄荷绿 #34D399', '深藏青色'),
    '抄作业': ('抄作业', '明黄色 #FFD60A', '深藏青色'),
    '办公课': ('AI办公课', '墨绿色 #1F5A40', '白色'),
}
TAG_OUTLINE = {('雾蓝', '先试')}       # 角标和底色太接近时加一圈深色细描边

# 内容情绪 -> 配色和示例作者的默认表情动作。按顺序匹配，先中先用。
MOODS = [
    ('出事', r'崩|宕机|故障|裁员|辞退|封号|被封|泄露|翻车|违法|判|起诉|警告|危险|骗|暴雷|下架|停服|塌房|出事',
     '夜蓝', '表情震惊、嘴巴张大、额头冒一滴汗，双手捧着一部屏幕显示红色感叹号的手机'),
    ('搞钱', r'赚|收入|\d+元|块钱|月薪|年薪|工资|免费|省钱|涨价|降价|补贴|成本|账单|价格|搞钱|算账|值不值',
     '夜蓝', '笑得眼睛弯成月牙，双手捧着一摞表面光滑、没有任何符号的金币'),
    ('教程', r'提示词|清单|教程|步骤|模板|抄作业|攻略|技巧|备份|存一份|收藏|指南|手把手|几步|一招',
     '米白', '自信微笑，一只手竖起大拇指，另一只手拿着一张写满横线的清单'),
    ('实测', r'实测|试了|能跑|跑分|对比|测评|评测|上手|体验|开箱|跑得动|PK|[Vv][Ss]',
     '雾蓝', '神情专注，一只手推了推眼镜，认真看着手里的平板电脑'),
]
COLUMN_THEME = {'热点': '夜蓝', '先试': '雾蓝', '算账': '夜蓝', '抄作业': '米白', '办公课': '奶白'}
COLUMN_POSE = {'热点': '一只手指向上方的标题，表情惊讶又好奇', '先试': MOODS[3][3], '算账': MOODS[1][3], '抄作业': MOODS[2][3]}
PLATFORM_NAME = {'weibo': '示例作者', 'zhihu': '示例作者', '微博': '示例作者', '知乎': '示例作者'}   # 图上署名=该平台账号名
PLATFORM_LIGHT = {'xhs', '小红书'}   # 小红书信息流是浅色、偏生活感：除了「出事」类，深色一律换成米白


VIDEO = {'video', 'douyin', 'channels', 'bilibili', 'kuaishou', '抖音', '视频号', 'B站', '快手'}
WECHAT = {'wechat', 'gzh', '公众号'}


def pick_theme(title='', column='热点', platform=None, brand='creator'):
    """挑配色，返回 (配色名, 情绪名, 默认表情动作)。10-16 用户：「封面颜色和内容排版颜色要一致」「不要明黄色」：
    视频（platform 是 video/抖音/视频号/B站/快手）一律夜蓝，跟成片的深色画面一套；公众号一律「公众号红」，跟正文红色排版一套；
    小红书/微博/知乎图文按内容情绪挑，封面和内页卡同色（小红书偏浅色）。spec 里写 cover_theme / "theme" 可以直接指定。"""
    import re
    if brand == 'office':
        return '奶白', '办公课', None
    for mood, pat, theme, pose in MOODS:
        if re.search(pat, title or ''):
            break
    else:
        mood, theme, pose = column, COLUMN_THEME.get(column, '夜蓝'), COLUMN_POSE.get(column, COLUMN_POSE['热点'])
    if platform in VIDEO:
        theme = '夜蓝'
    elif platform in WECHAT:
        theme = '公众号红'
    elif platform in PLATFORM_LIGHT and theme == '夜蓝' and mood != '出事':
        theme = '米白'
    return theme, mood, pose


def _clean_subject(subject):
    """v3 时代的 cover_subject 常写「小机器人……」：v4 画面里只有示例作者，含机器人的分句直接去掉。"""
    import re
    parts = [x for x in re.split(r'[，,；;]', subject or '') if x.strip() and '机器人' not in x]
    return '，'.join(parts)


def _v4_parts(title, column, subject, series, brand, theme, pose, platform, tag=None):
    lines = [l for l in title.split('\n') if l.strip()]
    line1, line2 = (lines + [''])[:2] if len(lines) >= 2 else (lines[0], '')
    auto_theme, mood, auto_pose = pick_theme(title, column, platform, brand)
    theme = theme if theme in THEMES else auto_theme
    th = THEMES[theme]
    if brand == 'office':
        column = '办公课'
    label, tag_bg, tag_ink = TAGS.get(column, TAGS['热点'])
    tag_extra = '，标签带一圈深藏青色细描边' if (theme, column) in TAG_OUTLINE else ''
    if theme == '公众号红':   # 角标也跟正文一样用红色
        tag_bg, tag_ink, tag_extra = '红色 #DC2626', '白色', ''
    if tag is not None:          # 10-16 用户：「示例作者算账那个去掉，这个可以突出 workbuddy」：角标可以换成内容主角（产品名/话题词）
        label = tag
    ser_ink = '白色' if not th['light'] else th['ink']
    sr = f'标签右边再放一个{ser_ink}描边、{ser_ink}字的小标签「{series}」。' if series else ''
    subj = _clean_subject(subject)
    d = dict(line1=line1, line2=line2, label=label, tag_bg=tag_bg, tag_ink=tag_ink, tag_extra=tag_extra, series=sr,
             subject=subj or '一两个和标题内容呼应的简单物件', pose=pose or auto_pose or '',
             name='示例办公课' if brand == 'office' else PLATFORM_NAME.get(platform, '示例聊AI'), **th)
    d['tag_sentence'] = (f'标题{{where}}一个{d["tag_bg"]}底色的圆角标签，{d["tag_ink"]}字「{d["label"]}」{d["tag_extra"]}。'
                         if d['label'] else '不要任何角标。')
    return theme, d


V4_TALL = (
    '竖版短视频封面，头部知识博主的系列封面风格，平面设计海报，干净、克制、高级。'
    '背景：{bg}；{deco}。'
    '标题：画面上部约 35% 的区域，左对齐，超大号粗黑体中文两行，第一行「{line1}」用{c1}，第二行「{line2}」用{c2}，'
    '平面字，笔画清晰锐利，标题宽度约占画面宽度的 85%，每个字都必须准确无误。'
    '{tag_sentence}{series}'
    '人物：Q版全身的示例作者，站在画面下半部偏右，人物高度约占画面高度的 50%，头部大、表情清楚，{pose}；'
    '人物外圈一道白色粗描边（贴纸效果），脚下一小片扁平投影，全身完整地在画面里。'
    '道具：{subject}，扁平插画，放在画面左下方，比人物小，和人物呼应。'
    '画面底部中间一行{ink}小字「{name}」。'
)
V4_TALL_OFFICE = (
    '竖版短视频封面，办公效率课的系列封面风格，平面设计海报，干净、明亮、清爽。'
    '背景：{bg}；{deco}。'
    '标题：画面上部约 35% 的区域，左对齐，超大号粗黑体中文两行，第一行「{line1}」用{c1}，第二行「{line2}」用{c2}，'
    '平面字，笔画清晰锐利，带一圈白色细描边，标题宽度约占画面宽度的 85%，每个字都必须准确无误。'
    '标题上方左侧一个{tag_bg}底色的圆角小标签，{tag_ink}小字「{label}」。{series}'
    '人物：Q版全身的示例作者，站在画面下半部偏右，人物高度约占画面高度的 45%，{pose}；人物外圈一道白色粗描边（贴纸效果），脚下一小片扁平投影，全身完整地在画面里。'
    '道具：扁平 2D 插画，{subject}，办公桌上的物件，线条干净，配色只用墨绿、橙、奶白和浅灰，放在画面左下方，比人物小。'
    '画面底部中间一行{ink}小字「示例办公课」。'
)   # 10-16 用户：「以后所有的视频封面都要加上我的动漫形象」，Office 号也放示例作者（之前不放人物）


def ai_cover(title, column, subject, out, series=None, attempt=0, brand='creator', theme=None, pose=None, platform=None, tag=None):
    """作图 API 生成「标题 + 示例作者 + 道具」一体封面（1024x1536），再补成 9:16（1080x1920）、3:4、4:3。
    带用户的动漫形象「示例作者」定稿图当参考图（人物长相一致）；10-16 起 Office 号也放（用户：所有视频封面都要有我的动漫形象）。
    theme：夜蓝/米白/雾蓝/公众号红，不写按平台和内容自动挑（pick_theme：视频封面夜蓝）；pose：示例作者的表情动作，不写按内容给默认；
    subject：道具和场景（不要再写机器人，要贴这条内容）；platform：不写=视频封面，图文首图写 xhs/weibo/zhihu。
    返回 (cover_9x16, cover_3x4, raw)。生成后必须放大逐字核对标题，有错字就用 attempt+1 重画。"""
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from common import gen_image
    theme, d = _v4_parts(title, column, subject, series, brand, theme, pose, platform or 'video', tag)
    d['tag_sentence'] = d['tag_sentence'].replace('{where}', '上方左侧')
    if brand == 'office':
        prompt, refs = V4_TALL_OFFICE.format(**d) + CHAR + FLAT, [CREATOR_REF]
    else:
        prompt, refs = V4_TALL.format(**d) + CHAR + FLAT, [CREATOR_REF]
    out = pathlib.Path(out)
    raw = out.with_name(out.stem + (f'-raw{attempt}' if attempt else '-raw') + '.png')
    print(f'[cover] 配色 {theme}', file=sys.stderr)
    gen_image(prompt, raw, size='1024x1536', refs=refs)
    c916, c34 = compose_ai_cover(raw, out)
    return c916, c34, raw


def _blur_fill(art, W, H, dim=0.45):
    import numpy as np
    s = max(W / art.width, H / art.height)
    bg = art.resize((int(art.width * s) + 1, int(art.height * s) + 1), Image.LANCZOS)
    x, y = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((x, y, x + W, y + H)).filter(ImageFilter.GaussianBlur(40))
    return Image.fromarray((np.asarray(bg, dtype=float) * dim).astype('uint8'))


def _pad(art, W, H, box):
    """把设计图 art 缩放进画布 box=(x, y, w, h)，四周补边：每一侧把贴边那一圈像素往外平铺、再柔化，
    颜色和暗角都和原图接得上（纹理在接缝处 40px 内渐隐）；v4 封面背景铺满四边，所以补出来就是同色底。"""
    import numpy as np
    x, y, w, h = box
    fg = np.asarray(art.resize((w, h), Image.LANCZOS), dtype=float)
    pw = max(x, W - x - w, y, H - y - h, 1)
    big = np.pad(fg, ((pw, pw), (pw, pw), (0, 0)), mode='edge')               # 贴边像素往外平铺
    big = big[pw - y:pw - y + H, pw - x:pw - x + W]
    soft = np.asarray(Image.fromarray(big.clip(0, 255).astype('uint8')).filter(ImageFilter.GaussianBlur(16)), dtype=float)
    yy, xx = np.mgrid[0:H, 0:W]
    dist = np.minimum.reduce([xx - x, x + w - 1 - xx, yy - y, y + h - 1 - yy]).astype(float)   # 到设计图边缘的距离，外面为负
    m = np.clip(dist / 40.0, 0, 1)[..., None]                                 # 边缘往里 40px 羽化
    out = big * m + soft * (1 - m)
    out[dist < 0] = soft[dist < 0]
    noise = np.random.default_rng(0).normal(0, 2.5, (H, W, 1)) * (dist < 0)[..., None]   # 补出来的区域补一点颗粒，别太「光」
    return Image.fromarray((out + noise).clip(0, 255).astype('uint8'))


def compose_ai_cover(raw, out):
    """把 2:3 设计图完整放进主页 3:4 安全区（960×1440），四周补边：主页格子不切字。
    输出 <out>（9:16）、-34（3:4）、-43（4:3，抖音电脑端）、-169（16:9，旧 B站用；B站现在用 ai_cover_wide 横版直出）。"""
    art = Image.open(raw).convert('RGB')
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    w = int(art.width * 1440 / art.height)                                 # 960
    _pad(art, 1080, 1920, ((1080 - w) // 2, 240, w, 1440)).save(out, quality=93)
    p34 = out.with_name(out.stem + '-34.jpg')
    _pad(art, 1080, 1440, ((1080 - w) // 2, 0, w, 1440)).save(p34, quality=93)
    w43 = int(art.width * 1080 / art.height)                               # 720
    for name, W in (('-43', 1440), ('-169', 1920)):
        _pad(art, W, 1080, ((W - w43) // 2, 0, w43, 1080)).save(out.with_name(out.stem + name + '.jpg'), quality=93)
    return out, p34


# ---------------------------------------------------------------------------
# 横版一体封面（10-16 新增，规范见 运营手册/封面规范.md）：B站 16:9、知乎题图 16:9、公众号头条 2.35:1。
# 竖版 ai_cover 补成 16:9 时设计图只占中间 1/3，B站推荐流小图里字太小；这里让作图 API 直接按横版构图：
# 标题在左、主体在右，画风、配色、栏目角标和 ai_cover 完全一致。只新增，不改上面任何函数。
WIDE_RATIOS = {   # 比例 -> (成品尺寸, 构图要求, 右上角是否写账号名)
    '16:9': ((1920, 1080),
             '画面上下各留出约 10% 的纯背景边距（成品会裁掉这部分），左右各留约 6%；标题、标签和主体都放在中间区域；'
             '画面最下方 15% 不放任何文字（平台会在那里叠播放量和时长）。', True),
    '2.35:1': ((1410, 600),
               '这是公众号头图，成品会裁成 2.35:1 的扁长条：画面上下各 20% 只放纯背景（会被裁掉），'
               '标题、标签和主体全部集中在中间 60% 高度的横向带状区域里，左右各留约 6%。', False),
}

# v4 横版：画风、配色、角标和竖版 ai_cover 完全一致（扁平平面设计 + 示例作者形象），只是构图按横版重排。
V4_WIDE = (
    '横版视频封面（{ratio}），头部知识区博主的系列封面风格，平面设计海报，干净、克制、高级。'
    '背景：{bg}；{deco}。'
    '标题：放在画面左侧约 55% 的宽度内，左对齐，超大号粗黑体中文两行，第一行「{line1}」用{c1}，第二行「{line2}」用{c2}，'
    '平面字，笔画清晰锐利，每个字都必须准确无误。'
    '{tag_sentence}{series}'
    '人物：Q版的示例作者，放在画面右侧约 40% 的区域里，人物高度约占画面高度的 62%，头部大、表情清楚，{pose}；'
    '人物外圈一道白色粗描边（贴纸效果），头顶和画面上边之间至少留出 15% 的空白（成品会裁掉上下边）。'
    '道具：{subject}，扁平插画，小一些，放在人物旁边，不能进入标题区域。'
    '{brand_line}构图：{band}标题和人物之间留出明显空隙。'
)
V4_CENTER = (
    '横版公众号头图（{ratio}），头部知识区博主的系列封面风格，平面设计海报，干净、克制、高级。'
    '背景：{bg}；{deco}。'
    '标题：放在画面正中央，居中对齐，超大号粗黑体中文两行，第一行「{line1}」用{c1}，第二行「{line2}」用{c2}，'
    '平面字，笔画清晰锐利，标题整体宽度不超过画面宽度的三分之一（必须完整落在正中间、高度为边长的正方形区域内，两侧留出明显空白），'
    '每个字都必须准确无误。{tag_sentence}{series}'
    '人物：示例作者胸部以上的半身像，放在画面最右侧约 25% 的区域里，{pose}，人物外圈一道白色粗描边（贴纸效果）。'
    '道具：{subject}，扁平插画，放在画面最左侧约 25% 的区域里。人物和道具都不能进入中间放标题的区域。'
    '构图：{band}'
)
V4_WIDE_OFFICE = (
    '横版视频封面（{ratio}），办公效率课的系列封面风格，平面设计海报，干净、明亮、清爽。'
    '背景：{bg}；{deco}。'
    '标题：放在画面左侧约 55% 的宽度内，左对齐，超大号粗黑体中文两行，第一行「{line1}」用{c1}，第二行「{line2}」用{c2}，'
    '平面字，笔画清晰锐利，带一圈白色细描边，每个字都必须准确无误。'
    '标题正上方一个{tag_bg}底色的圆角小标签，{tag_ink}小字「{label}」。{series}'
    '人物：示例作者胸部以上的半身像，放在画面最右侧约 30% 的区域里，{pose}，人物外圈一道白色粗描边（贴纸效果）。'
    '道具：扁平 2D 插画，{subject}，办公桌上的物件，配色只用墨绿、橙、奶白和浅灰，放在人物旁边，比人物小。人物和道具都不能进入左侧放标题的区域。'
    '{brand_line}构图：{band}'
)


def ai_cover_wide(title, column, subject, out, ratio='16:9', series=None, attempt=0, brand='creator', layout=None,
                  theme=None, pose=None, platform=None, tag=None):
    """作图 API 直接设计横版封面（1536x1024），再裁成成品。画风、配色和竖版 ai_cover 一套（v4：扁平 + 示例作者形象）。
    ratio='16:9'  -> out 为 1920×1080（B站 cover_169、知乎文章题图），标题在左、示例作者在右，右上角带账号名；
    ratio='2.35:1'-> out 为 1410×600（公众号头条，默认标题居中、不写账号名），另出 <out>-11.jpg（1:1 分享小图）。
    title 两行用 \\n 分隔，每行建议 ≤8 字（居中版 ≤6 字）；theme/pose/platform 同 ai_cover。
    返回 (成品, 1:1小图或None, raw)。生成后必须放大逐字核对，有错字就 attempt+1 重画（每次重画都计费）。"""
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from common import gen_image
    if ratio not in WIDE_RATIOS:
        raise ValueError(f'ratio 只支持 {list(WIDE_RATIOS)}')
    platform = platform or ('wechat' if ratio == '2.35:1' else 'video')
    theme, d = _v4_parts(title, column, subject, series, brand, theme, pose, platform, tag)
    _, band, with_name = WIDE_RATIOS[ratio]
    d['brand_line'] = f'画面右上角（距上边约 16%、距右边约 6%）一行{d["ink"]}小字「{d["name"]}」。' if with_name else ''
    layout = layout or ('center' if ratio == '2.35:1' else 'left')   # 公众号头条默认居中（10-16 定），B站/知乎题图默认左标题右人物
    if brand == 'office':
        prompt, refs = V4_WIDE_OFFICE.format(ratio=ratio, band=band, **d) + CHAR + FLAT, [CREATOR_REF]
    else:
        tpl = V4_CENTER if layout == 'center' else V4_WIDE
        d['tag_sentence'] = d['tag_sentence'].replace('{where}', '正上方居中' if layout == 'center' else '正上方')
        prompt, refs = tpl.format(ratio=ratio, band=band, **d) + CHAR + FLAT, [CREATOR_REF]
    out = pathlib.Path(out)
    raw = out.with_name(out.stem + (f'-raw{attempt}' if attempt else '-raw') + '.png')
    print(f'[cover] 配色 {theme}', file=sys.stderr)
    gen_image(prompt, raw, size='1536x1024', refs=refs)
    main, sq = compose_ai_cover_wide(raw, out, ratio, layout)
    return main, sq, raw


def _quiet_offset(gray, keep, axis=0):
    """在可裁范围里找一个偏移，让被裁掉的行（或列）里「东西」最少：避免把顶上的账号名、底下的主体切掉。"""
    import numpy as np
    g = np.asarray(gray, dtype=float)
    e = np.abs(np.diff(g, axis=0))[:, :-1] + np.abs(np.diff(g, axis=1))[:-1, :]
    prof = (e > 40).sum(axis=1 - axis).astype(float)      # 只数强边缘（文字、主体轮廓），背景网格和柔光不算
    n = len(prof) + 1
    cs = np.concatenate([[0], np.cumsum(prof)])
    best, best_cost = (n - keep) // 2, None
    for o in range(0, n - keep + 1, 2):
        cost = cs[o] + (cs[-1] - cs[min(o + keep, len(cs) - 1)])
        cost += abs(o - (n - keep) / 2) * 1e-3              # 一样干净时偏向居中
        if best_cost is None or cost < best_cost:
            best, best_cost = o, cost
    return best


def compose_ai_cover_wide(raw, out, ratio='16:9', layout='left'):
    """把 3:2 横版设计图裁成目标比例（不补边、不缩字），裁切位置自动避开文字和主体。
    也可以拿已有的横版 raw 直接复用、不再调 API。
    2.35:1 额外输出 <out>-11.jpg（600×600）：取画面右侧主体整块等比缩进正方形，上下用同图虚化补齐，不含标题字
    （微信分享卡片旁边本来就有标题）。"""
    (W, H), _, _ = WIDE_RATIOS[ratio]
    art = Image.open(raw).convert('RGB')
    gray = art.convert('L').resize((art.width // 4, art.height // 4))
    r = W / H
    if art.width / art.height > r:          # 原图更宽：裁左右
        cw = int(art.height * r)
        x0 = _quiet_offset(gray, cw // 4, axis=1) * 4
        box = (x0, 0, x0 + cw, art.height)
    else:                                   # 原图更高：裁上下（3:2 -> 16:9 / 2.35:1 都走这里）
        ch = int(art.width / r)
        y0 = _quiet_offset(gray, ch // 4, axis=0) * 4
        box = (0, y0, art.width, y0 + ch)
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    art.crop(box).resize((W, H), Image.LANCZOS).save(out, quality=93)
    sq = None
    if ratio == '2.35:1' and layout == 'center':   # 居中版式：1:1 小图就是正中间的标题块，和微信自动截取的一致
        cr = art.crop(box).resize((W, H), Image.LANCZOS)
        cw = int(W * 0.5)                                   # 中间一半宽度（标题块）等比缩进正方形，字不被切
        mid = cr.crop(((W - cw) // 2, 0, (W + cw) // 2, H))
        S = 600
        s = min(S / mid.width, S / mid.height)
        fg = mid.resize((int(mid.width * s), int(mid.height * s)), Image.LANCZOS)
        bg = _blur_fill(mid, S, S, dim=0.8)
        bg.paste(fg, ((S - fg.width) // 2, (S - fg.height) // 2))
        sq = out.with_name(out.stem + '-11.jpg')
        bg.save(sq, quality=93)
    elif ratio == '2.35:1':
        side = art.crop((int(art.width * 0.555), box[1], art.width, box[3]))
        S = 600
        s = min(S / side.width, S / side.height)
        fg = side.resize((int(side.width * s), int(side.height * s)), Image.LANCZOS)
        bg = _blur_fill(side, S, S, dim=0.8)
        bg.paste(fg, ((S - fg.width) // 2, (S - fg.height) // 2))
        sq = out.with_name(out.stem + '-11.jpg')
        bg.save(sq, quality=93)
    return out, sq


def compose_ai_cover_adaptive(raw, out):
    """v4 起和 compose_ai_cover 完全一样（补边按底色平铺、不压暗），保留这个名字给 make_motion 和旧命令用。"""
    return compose_ai_cover(raw, out)
