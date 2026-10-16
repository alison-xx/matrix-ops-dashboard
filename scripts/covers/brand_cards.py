#!/usr/bin/env python3
"""示例作者矩阵「品牌信息卡」：小红书内页、微博早报卡/快评卡/互动帖卡、知乎回答和想法配图、公众号正文信息图。
规范见 运营手册/封面规范.md。HTML 排版 + Playwright 截图，配色锁定在品牌底座上（不要在 spec 里改颜色）。

由 10-16 早班临时脚本 cards.py（深色系列卡，存在会话临时目录里）收编而来，spec 完全兼容：旧的 cards.json 直接能跑。
相比旧版：① 胶囊角标按栏目上色（热点珊瑚红 / 先试天蓝 / 算账薄荷绿 / 抄作业明黄，系列名如「示例作者AI早报」用品牌黄）；
② 新增 vote 互动帖卡、横版 wide 信息卡（16:9）；③ 字多了自动缩字号，缩到底还放不下就报错；
④ 贴纸（示例作者立绘）会压到字就自动去掉并提示；Office 号不允许用示例作者贴纸。

spec.json：
{
  "out_dir": "days/2026-10-16/weibo-1",      # 相对工作区根目录或绝对路径
  "prefix": "2026-10-16-weibo-1",            # 输出 <prefix>-NN.jpg
  "start": 1, "total": 1,                    # 页码从几开始、一共几页（小红书首图是作图封面，内页从 2 开始）
  "size": [1080, 1440],                      # 3:4 默认；横版用 [1200, 675] 或 [1920, 1080]（自动走 wide 版式）
  "brand": "creator",                        # creator（深色）| office（浅色办公风，不能用示例作者贴纸）
  "pages": [
    {"tag": "示例作者AI早报 · 10.16",             # 胶囊文字；不写就用 column 对应的栏目名
     "column": "热点",                        # 热点/先试/算账/抄作业/办公课 -> 胶囊颜色；不写时按 tag 文字匹配，匹配不上用品牌黄
     "series": "第3期",                       # 可选：胶囊右边的白描边小胶囊（系列号）
     "title": "昨夜今晨\\nAI 圈 4 件事",        # 大标题，\\n 手动换行
     "hl": "黄色副标题（可选）",
     "items": ["要点，**加粗**会变黄", "..."],  # 编号卡片列表（2–5 条）
     "prompt": "可直接复制的提示词（可选）",    # 深色代码框，标题栏写「复制这段」
     "note": "底部一句补充（可选）",
     "sticker": "我悟了",                     # 可选：示例作者立绘（名字/编号/路径），只放右下角空白处，会压字就自动去掉
     "type": "list"                           # list（默认）| vote（互动帖：title=问题，options=2–3 个选项）
    },
    {"type": "vote", "tag": "今晚聊聊", "title": "你们公司\\n让用 AI 写周报吗？", "options": ["让，还鼓励", "不让", "偷偷用"],
     "note": "评论区说说你站哪边"}
  ]
}
可选微调（一般不用写，字多会自动缩）：ts 标题字号、is 列表字号、ps 提示词字号、pad 顶部留白、sw 贴纸宽度。

用法:
  .venv/bin/python scripts/covers/brand_cards.py <spec.json>            # 出图，打印每张路径
  .venv/bin/python scripts/covers/brand_cards.py <spec.json> --html     # 只导出 HTML（调样式用）
"""
import base64, html, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
STK = ROOT / 'assets/stickers/creator'

# 品牌底座（改这里 = 改全矩阵，先改 运营手册/封面规范.md 第 1 节再动）
COLUMN = {  # 栏目 -> (胶囊文字, 底色, 字色)
    '热点': ('AI热点说人话', '#FF6B4A', '#FFFFFF'),
    '先试': ('示例作者先试', '#3DA9FC', '#0B1030'),
    '算账': ('示例作者算账', '#34D399', '#0B1030'),
    '抄作业': ('抄作业', '#FFD60A', '#1B1B40'),
    '办公课': ('AI办公课', '#1F5A40', '#FFFFFF'),
}
# 署名按平台账号名（10-16 定：图片被转走时，别人按图上的名字能在这个平台搜到我们）
PLATFORM_NAME = {'weibo': '示例作者', 'zhihu': '示例作者', '微博': '示例作者', '知乎': '示例作者'}
GRAIN = ("url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'>"
         "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/>"
         "<feColorMatrix values='0 0 0 0 .5  0 0 0 0 .5  0 0 0 0 .5  0 0 0 .55 0'/></filter>"
         "<rect width='100%' height='100%' filter='url(%23n)'/></svg>\")")
NAVY = '#14204A'
# v4（10-16 用户：封面去 AI 味、统一风格、颜色按内容和平台挑；不要明黄；封面颜色和内容排版一致）：示例作者卡片和作图封面同一套扁平配色，
# 不再用紫色渐变 + 光斑 + 网格。配色名和 make_cover.THEMES 一致；spec 写 "theme"，不写按内容和平台自动挑（make_cover.pick_theme）。
XX = dict(name='示例聊AI', ink='#FFFFFF', sub='rgba(255,255,255,.85)', mute='rgba(255,255,255,.58)', accent='#FFD60A',
          accent_ink='#1B1B40', num_bg='#FFD60A', num_ink=NAVY, bmark='', h2mark='',
          pill='#FFFFFF', pill_ink='#1B1B40',   # 固定系列（早报/周报/互动帖）用白底深字，和「抄作业」黄色角标分开（10-16 定）
          bg=NAVY, pattern='none', grain_op='.10',
          card='rgba(255,255,255,.07)', card_line='rgba(255,255,255,.14)',
          code_bg='#0B1433', code_line='rgba(255,214,10,.6)', code_ink='#e9ecff', code_bar='#9aa3d8')
LIGHT = dict(ink=NAVY, sub='rgba(20,32,74,.84)', mute='rgba(20,32,74,.55)', pill=NAVY, pill_ink='#FFFFFF',
             num_bg=NAVY, num_ink='#FFFFFF', card='rgba(255,255,255,.62)', card_line='rgba(20,32,74,.12)', grain_op='.07',
             code_bg=NAVY, code_line='rgba(20,32,74,.0)', code_ink='#F3F5FF', code_bar='#AEB6DA')
THEME = {
    'creator': XX,                                    # = 夜蓝（默认）
    '夜蓝': XX,
    '米白': {**XX, **LIGHT, 'bg': '#F5F0E6', 'accent': NAVY, 'num_ink': '#FFD60A',
             'bmark': 'background:linear-gradient(transparent 58%,#FFD60A 58%,#FFD60A 92%,transparent 92%);white-space:nowrap;',
             'h2mark': 'background:linear-gradient(transparent 60%,#FFD60A 60%,#FFD60A 92%,transparent 92%);display:inline;',
             'pattern': 'radial-gradient(rgba(20,32,74,.06) 1.5px,transparent 1.7px) 0 0/16px 16px'},
    '雾蓝': {**XX, **LIGHT, 'bg': '#DCEBFA', 'accent': '#FF5A36',
             'pattern': 'linear-gradient(rgba(20,32,74,.05) 1px,transparent 1px) 0 0/44px 44px,'
                        'linear-gradient(90deg,rgba(20,32,74,.05) 1px,transparent 1px) 0 0/44px 44px'},
    # 公众号正文信息图：和 gzh_red.py 红色排版同一套色值（10-16 用户：「封面颜色和内容排版颜色要一致」）
    '公众号红': {**XX, **LIGHT, 'bg': '#FFFFFF', 'ink': '#1C1917', 'sub': 'rgba(28,25,23,.82)', 'mute': 'rgba(28,25,23,.5)',
              'accent': '#DC2626', 'num_bg': '#DC2626', 'num_ink': '#FFFFFF', 'pill': '#DC2626', 'pill_ink': '#FFFFFF',
              'card': '#FEF2F2', 'card_line': '#FECACA', 'pattern': 'none', 'grain_op': '.05',
              'code_bg': '#1C1917', 'code_ink': '#FFF5F5', 'code_bar': '#FCA5A5'},
    'office': dict(
        name='示例办公课', ink='#1F3D30', sub='#3E5A4D', mute='#7D9488', accent='#E8792B',
        accent_ink='#FFFFFF', num_bg='#E8792B', num_ink='#FFFFFF', bmark='', h2mark='', pill='#1F5A40', pill_ink='#FFFFFF',
        bg='#FBF8F1', pattern='radial-gradient(circle at 92% 96%,#DDF1E6 0,#DDF1E6 22%,transparent 22.2%)', grain_op='.06',
        card='rgba(255,255,255,.72)', card_line='rgba(31,90,64,.14)',
        code_bg='#FFFFFF', code_line='rgba(31,90,64,.35)', code_ink='#1F3D30', code_bar='#7D9488'),
}


def theme_for(spec, brand):
    """spec["theme"] 指定配色；不写就按第一页的标题和栏目、spec 的平台自动挑（和作图封面同一套规则）。"""
    if brand == 'office':
        return 'office'
    t = spec.get('theme')
    if t in THEME:
        return t
    sys.path.insert(0, str(ROOT / 'scripts'))
    from make_cover import pick_theme
    p0 = (spec.get('pages') or [{}])[0]
    return pick_theme(p0.get('title', '').replace('\n', ''), p0.get('column', '热点'), spec.get('platform'))[0]


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
:root{--k:1}
h1,h2,.tx,.note,.op .t{text-wrap:pretty;line-break:strict}
body{width:%(BW)dpx;height:%(BH)dpx;font-family:"PingFang SC","Hiragino Sans GB",sans-serif;color:%(ink)s;
 background:%(bg)s;position:relative;overflow:hidden}
.grid{position:absolute;inset:0;background:%(pattern)s}
.grid::after{content:"";position:absolute;inset:0;background-image:%(GRAIN)s;opacity:%(grain_op)s;mix-blend-mode:overlay}
.wrap{position:absolute;left:%(PX)dpx;right:%(PX)dpx;top:%(PAD)dpx}
.pills{display:flex;gap:16px;align-items:center;position:relative}
.tag{display:inline-block;background:var(--pill);color:var(--pill-ink);font-weight:700;font-size:36px;padding:10px 28px;border-radius:30px;white-space:nowrap}
.ser{display:inline-block;border:3px solid %(mute)s;color:%(ink)s;font-weight:700;font-size:32px;padding:7px 22px;border-radius:30px;white-space:nowrap}
.pn{position:absolute;right:%(PX)dpx;top:%(PAD)dpx;font-size:28px;color:%(mute)s;font-weight:600;line-height:58px}
h1{font-size:calc(%(TS)dpx*var(--k));line-height:1.22;font-weight:800;margin-top:calc(34px*var(--k));letter-spacing:1px}
h2{font-size:calc(58px*var(--k));color:%(accent)s;font-weight:700;margin-top:calc(18px*var(--k));line-height:1.35}
h2 span{%(h2mark)s}
.items{margin-top:calc(44px*var(--k))}
.it{display:flex;align-items:flex-start;background:%(card)s;border:1px solid %(card_line)s;border-radius:26px;padding:calc(38px*var(--k)) 36px;margin-bottom:calc(28px*var(--k))}
.num{flex:none;width:calc(72px*var(--k));height:calc(72px*var(--k));border-radius:50%%;background:%(num_bg)s;color:%(num_ink)s;font-weight:800;font-size:calc(40px*var(--k));display:flex;align-items:center;justify-content:center;margin-right:26px}
.tx{font-size:calc(%(IS)dpx*var(--k));line-height:1.5;font-weight:500;padding-top:calc(4px*var(--k))}
.tx b,h1 b,.note b{color:%(accent)s;font-weight:700;%(bmark)s}
.pr{margin-top:calc(40px*var(--k));background:%(code_bg)s;border:2px solid %(code_line)s;border-radius:24px;padding:32px 40px 40px}
.pr .bar{font-size:30px;color:%(code_bar)s;margin-bottom:16px;letter-spacing:2px}
.pr .bar i{display:inline-block;width:16px;height:16px;border-radius:50%%;margin-right:8px;background:#ff5f57}
.pr .bar i+i{background:#febc2e}.pr .bar i+i+i{background:#28c840}
.pr pre{white-space:pre-wrap;font-family:inherit;font-size:calc(%(PS)dpx*var(--k));line-height:1.62;color:%(code_ink)s}
.note{margin-top:calc(40px*var(--k));font-size:calc(40px*var(--k));line-height:1.5;color:%(sub)s}
.brand{position:absolute;left:0;right:0;bottom:44px;text-align:center;font-size:32px;color:%(mute)s;font-weight:600}
.stk{position:absolute;right:30px;bottom:70px;width:%(SW)dpx}
/* 互动帖 */
.opts{margin-top:calc(64px*var(--k))}
.op{display:flex;align-items:center;background:%(card)s;border:2px solid %(card_line)s;border-radius:30px;padding:calc(34px*var(--k)) 40px;margin-bottom:calc(30px*var(--k))}
.op .l{flex:none;width:calc(84px*var(--k));height:calc(84px*var(--k));border-radius:24px;font-weight:900;font-size:calc(48px*var(--k));display:flex;align-items:center;justify-content:center;margin-right:32px}
.op .t{font-size:calc(56px*var(--k));font-weight:700;line-height:1.3}
.has-stk .op{margin-right:%(SWR)dpx}   /* 互动帖带贴纸：选项卡让出右边一栏给示例作者 */
/* 横版：左标题、右要点 */
.wide .wrap{right:auto;width:%(LW)dpx}
.wide .side{position:absolute;right:%(PX)dpx;top:%(PAD)dpx;width:%(RW)dpx}
.wide .side .items,.wide .side .pr,.wide .side .opts{margin-top:0}
.wide .tag{font-size:26px;padding:8px 22px}
.wide .ser{font-size:23px;padding:5px 16px;border-width:2px}
.wide h1{margin-top:calc(26px*var(--k))}
.wide h2{font-size:calc(40px*var(--k))}
.wide .note{font-size:calc(28px*var(--k));margin-top:calc(28px*var(--k))}
.wide .it{align-items:center;border-radius:22px;padding:calc(24px*var(--k)) 28px;margin-bottom:calc(20px*var(--k))}
.wide .num{width:calc(54px*var(--k));height:calc(54px*var(--k));font-size:calc(30px*var(--k));margin-right:22px}
.wide .tx{padding-top:0}
.wide .pr{padding:22px 28px 26px}.wide .pr .bar{font-size:22px;margin-bottom:10px}
.wide .op{padding:calc(22px*var(--k)) 28px;margin-bottom:calc(20px*var(--k))}
.wide .op .l{width:calc(60px*var(--k));height:calc(60px*var(--k));font-size:calc(34px*var(--k));margin-right:22px}
.wide .op .t{font-size:calc(38px*var(--k))}
.wide .brand{left:%(PX)dpx;right:auto;text-align:left;bottom:36px;font-size:24px}
"""

LETTER_COLORS = [('#FF6B4A', '#FFFFFF'), ('#3DA9FC', '#0B1030'), ('#34D399', '#0B1030'), ('#FFD60A', '#1B1B40')]


def bold(s):
    parts = html.escape(s).split('**')
    return ''.join(f'<b>{x}</b>' if k % 2 else x for k, x in enumerate(parts)).replace('\n', '<br>')


def sticker_path(s):
    p = pathlib.Path(s)
    if p.suffix and (p.exists() or (ROOT / p).exists()):
        return p if p.exists() else ROOT / p
    idx = json.loads((STK / 'index.json').read_text())
    lst = next(v for v in idx.values() if isinstance(v, list))
    for x in lst:
        if s in (x['id'], x['name'], f"{x['id']}_{x['name']}"):
            return ROOT / x['png1024']
    raise ValueError(f'找不到贴纸 {s}（编号或名字见 assets/stickers/creator/index.json）')


def pill_colors(p, th):
    col = p.get('column')
    if col in COLUMN:
        return COLUMN[col][1:]
    for k, (label, bg, ink) in COLUMN.items():
        if p.get('tag', '').split(' ')[0] in (label, k):
            return bg, ink
    return th['pill'], th['pill_ink']


def page_html(p, i, n, W, H, brand, theme=None):
    th = THEME[theme or brand]
    wide = W > H
    BW = 1200 if wide else 1080                     # 设计基准宽度，实际尺寸靠 device_scale_factor 放大
    BH = round(H * BW / W)
    PX = 64 if wide else 72
    css = CSS % dict(BW=BW, BH=BH, PX=PX, PAD=p.get('pad', 72 if wide else 80), TS=p.get('ts', 80 if wide else 100),
                     IS=p.get('is', 30 if wide else 46), PS=p.get('ps', 28 if wide else 44), SW=p.get('sw', 260), SWR=p.get('sw', 260) - 30,
                     LW=int(BW * 0.44) - PX, RW=int(BW * 0.56) - PX - 24, GRAIN=GRAIN, **th)
    pbg, pink = pill_colors(p, th)
    label = p.get('tag') or (COLUMN[p['column']][0] if p.get('column') in COLUMN else '示例聊AI')
    pills = f'<div class="pills"><span class="tag" style="--pill:{pbg};--pill-ink:{pink}">{html.escape(label)}</span>'
    if p.get('series'):
        pills += f'<span class="ser">{html.escape(p["series"])}</span>'
    pills += '</div>'
    head = pills + f'<h1>{bold(p["title"])}</h1>' + (f'<h2><span>{bold(p["hl"])}</span></h2>' if p.get('hl') else '')
    items = ''
    if p.get('items'):
        items = '<div class="items">' + ''.join(
            f'<div class="it"><div class="num">{k}</div><div class="tx">{bold(t)}</div></div>' for k, t in enumerate(p['items'], 1)) + '</div>'
    prompt = (f'<div class="pr"><div class="bar"><i></i><i></i><i></i> 复制这段</div><pre>{html.escape(p["prompt"])}</pre></div>'
              if p.get('prompt') else '')
    note = f'<div class="note">{bold(p["note"])}</div>' if p.get('note') else ''
    if p.get('type') == 'vote':
        items = '<div class="opts">' + ''.join(
            f'<div class="op"><div class="l" style="background:{LETTER_COLORS[k][0]};color:{LETTER_COLORS[k][1]}">{"ABCD"[k]}</div>'
            f'<div class="t">{bold(t)}</div></div>' for k, t in enumerate(p['options'][:4])) + '</div>'
    if wide:
        body = f'<div class="wrap">{head}{note}</div><div class="side">{items}{prompt}</div>'
    else:
        body = f'<div class="wrap">{head}{items}{prompt}{note}</div>'
    body = '<div class="grid"></div>' + body + (f'<span class="pn">{i}/{n}</span>' if n > 1 and not wide else '')
    if p.get('sticker'):
        if brand == 'office':
            raise ValueError('Office 号不用示例作者表情包（运营手册/表情包.md 第 4 节）')
        b64 = base64.b64encode(sticker_path(p['sticker']).read_bytes()).decode()
        body += f'<img class="stk" src="data:image/png;base64,{b64}">'
    body += f'<div class="brand">{html.escape(p.get("brand_name") or th["name"])}</div>'
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head>'
            f'<body class="{"wide" if wide else "tall"}{" has-stk" if p.get("sticker") else ""}">{body}</body></html>'), BW, BH


FIT_JS = """() => {
  // 1) 每一栏（竖版只有一栏；横版左标题、右要点各算各的）超出底部品牌行就缩字号，--k 从 1 降到 0.62
  const limit = document.body.clientHeight - 100;
  let ks = [], overflow = false;
  for (const el of document.querySelectorAll('.wrap,.side')) {
    let k = 1;
    while (el.getBoundingClientRect().bottom > limit && k > 0.62) { k -= 0.02; el.style.setProperty('--k', k.toFixed(2)); }
    if (el.getBoundingClientRect().bottom > limit) overflow = true;
    ks.push(k);
  }
  // 2) 贴纸（示例作者立绘）依次试右下角、右上角，压到任何字（逐行文字的真实范围）或卡片框就换位置，都不行就去掉：人物不能挡字
  let stk = 'none';
  const s = document.querySelector('.stk');
  if (s) {
    const rects = [];
    document.querySelectorAll('.it,.pr,.op,.tag,.ser').forEach(e => rects.push(e.getBoundingClientRect()));
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) {
      if (!w.currentNode.textContent.trim()) continue;
      const rg = document.createRange(); rg.selectNodeContents(w.currentNode);
      for (const q of rg.getClientRects()) rects.push(q);
    }
    const hits = () => {
      const r = s.getBoundingClientRect();
      const L = r.left + r.width * 0.12, T = r.top + r.height * 0.06;   // 立绘四周有透明边
      return rects.some(q => !(q.right < L || q.left > r.right || q.bottom < T || q.top > r.bottom));
    };
    stk = 'removed';
    for (const [pos, css] of [['右下角', 'right:30px;bottom:70px'], ['右上角', 'right:30px;top:40px']]) {
      s.style.cssText = css;
      if (!hits()) { stk = pos; break; }
    }
    if (stk === 'removed') s.remove();
  }
  return {k: Math.min(...ks), overflow, stk};
}"""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    spec_p = pathlib.Path(args[0])
    spec = json.loads(spec_p.read_text())
    W, H = spec.get('size', [1080, 1440])
    brand = spec.get('brand', 'creator')
    out = pathlib.Path(spec['out_dir'])
    out = out if out.is_absolute() else ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    start = spec.get('start', 2)
    total = spec.get('total', len(spec['pages']) + start - 1)
    if brand == 'creator' and spec.get('platform') in PLATFORM_NAME:   # spec 写 "platform": "weibo" / "zhihu"
        for p in spec['pages']:
            p.setdefault('brand_name', PLATFORM_NAME[spec['platform']])
    theme = theme_for(spec, brand)
    print(f'配色 {theme}')
    pages = [(start + k, p, *page_html(p, start + k, total, W, H, brand, p.get('theme') if p.get('theme') in THEME else theme))
             for k, p in enumerate(spec['pages'])]
    if '--html' in sys.argv:
        for idx, p, h, *_ in pages:
            f = out / f"{spec['prefix']}-{idx:02d}.html"
            f.write_text(h)
            print(f)
        return
    from playwright.sync_api import sync_playwright
    bad = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for idx, p, h, BW, BH in pages:
            pg = b.new_page(viewport={'width': BW, 'height': BH}, device_scale_factor=W / BW)
            pg.set_content(h, wait_until='load')
            r = pg.evaluate(FIT_JS)
            f = out / f"{spec['prefix']}-{idx:02d}.jpg"
            pg.screenshot(path=str(f), type='jpeg', quality=92)
            pg.close()
            msg = f'{f}  字号x{r["k"]:.2f}' + {'removed': '  贴纸放哪都会压字，已去掉', 'none': ''}.get(r['stk'], f'  贴纸放在{r["stk"]}')
            if r['overflow']:
                msg += '  ！！字太多放不下，删字或拆页'
                bad.append(str(f))
            print(msg)
        b.close()
    if bad:
        sys.exit(f'{len(bad)} 张放不下：{bad}')


if __name__ == '__main__':
    main()
