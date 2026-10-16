#!/usr/bin/env python3
"""公众号「贴图」卡片生成器（10-16 用户：公众号贴图加入日常运营）。

一份 spec.json → 一组 1080×1440（3:4）卡片，HTML 设计稿 + 无头浏览器渲染，字清楚、风格和公众号文章统一：
浅色底（白→浅暖粉 + 极淡网格）、深色字、红色 #DC2626 只做强调，人物用示例作者透明底头肩像 / 表情包立绘（不压字）。

spec.json:
{
  "column": "文章导读",                  # 栏目名，出现在封面小标签和每页页脚
  "cards": [
    {"type": "cover", "tag": "AI工作台 赚钱复盘", "title": "4 天赚到 **1234 元**\\n我做对了 3 件事", "sub": "一行副标题", "sticker": "16"},
    {"type": "text",  "no": "01", "heading": "小标题", "body": ["一段或一条", "支持 **红色加粗**、==浅红底高亮=="], "list": true, "note": "可选的底部提示框"},
    {"type": "image", "no": "02", "heading": "小标题", "image": "相对 spec 的图片路径", "caption": "图注（可选）"},
    {"type": "end", "title": "关注示例作者\\n每天一篇 AI 实测", "question": "评论区问题（可选）"}
  ]
}
sticker / bust 编号见 assets/stickers/creator/index.json（09 干货、10 我悟了、16 搞钱、11 震惊、05 比心…）。
用法: .venv/bin/python scripts/make_tietu.py <spec.json> [输出目录，默认 spec 同目录 cards/]
"""
import html, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
STK = ROOT / 'assets/stickers/creator'
W, H = 1080, 1440
NAME = '示例AI周刊'

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'PingFang SC','Hiragino Sans GB',-apple-system,sans-serif;-webkit-font-smoothing:antialiased;color:#1C1917}
.pg{width:1080px;height:1440px;position:relative;overflow:hidden;background-color:#fff;
 background-image:linear-gradient(rgba(220,38,38,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(220,38,38,.035) 1px,transparent 1px),
 radial-gradient(110% 70% at 100% 0%,#FFE4DF 0%,rgba(255,228,223,0) 60%),linear-gradient(160deg,#FFFFFF 0%,#FFFAF8 60%,#FFF1EE 100%);
 background-size:40px 40px,40px 40px,100% 100%,100% 100%}
.r{color:#DC2626;font-weight:900}
.hl{background:linear-gradient(transparent 55%,#FECACA 55%);padding:0 4px}
.foot{position:absolute;left:72px;right:72px;bottom:56px;display:flex;align-items:center;justify-content:space-between;font-size:28px;color:#A8A29E}
.foot .who{display:flex;align-items:center;gap:14px;color:#57534E;font-weight:600}
.foot img{width:64px;height:64px}
.foot .pn{font-variant-numeric:tabular-nums;letter-spacing:2px}
.tag{display:inline-block;background:#DC2626;color:#fff;font-size:34px;font-weight:800;padding:10px 28px;border-radius:999px;letter-spacing:2px}
/* 封面 */
.cv-t{position:absolute;left:72px;right:72px;top:220px;font-size:150px;line-height:1.18;font-weight:900;letter-spacing:1px}
.cv-s{position:absolute;left:72px;right:420px;font-size:50px;line-height:1.5;color:#57534E;font-weight:600}
.cv-fig{position:absolute;right:40px;bottom:120px;height:600px}
.cv-who{position:absolute;left:72px;bottom:150px;font-size:34px;color:#57534E;line-height:1.5}
.cv-who b{display:block;font-size:44px;color:#1C1917}
/* 正文页 */
.hd{position:absolute;left:72px;right:72px;top:96px;display:flex;align-items:center;gap:24px}
.no{flex-shrink:0;width:104px;height:104px;border-radius:24px;background:#DC2626;color:#fff;font-size:52px;font-weight:900;display:flex;align-items:center;justify-content:center}
.hd h2{font-size:68px;line-height:1.25;font-weight:900}
.bd{position:absolute;left:72px;right:72px;top:300px;font-size:52px;line-height:1.7}
.bd p{margin-bottom:34px}
.bd .li{display:flex;gap:22px;margin-bottom:34px}
.bd .li i{flex-shrink:0;width:18px;height:18px;margin-top:30px;border-radius:5px;background:#DC2626;transform:rotate(45deg)}
.note{margin-top:56px;background:#FEF2F2;border:3px solid #FECACA;border-radius:28px;padding:30px 36px;font-size:40px;line-height:1.6;color:#991B1B;font-weight:700}
.im{position:absolute;left:72px;right:72px;top:280px;bottom:250px;display:flex;flex-direction:column;align-items:center;justify-content:center}
.im .frame{max-width:100%;max-height:100%;border-radius:28px;overflow:hidden;border:3px solid #F3D3CD;box-shadow:0 18px 50px rgba(150,60,40,.12);background:#fff}
.im img{display:block;max-width:936px;max-height:880px}
.cap{position:absolute;left:72px;right:72px;bottom:170px;text-align:center;font-size:36px;color:#78716C}
/* 尾页 */
.en-t{position:absolute;left:72px;right:72px;top:150px;font-size:100px;line-height:1.25;font-weight:900}
.en-fig{position:absolute;left:50%;transform:translateX(-50%);top:470px;height:560px}
.en-chips{position:absolute;left:72px;right:72px;top:1060px;display:flex;gap:24px}
.chip{flex:1;background:#fff;border:3px solid #F3D3CD;border-radius:26px;padding:24px 0;text-align:center;font-size:36px;font-weight:800;color:#DC2626}
.chip span{display:block;font-size:28px;color:#57534E;font-weight:600;margin-top:6px}
.en-q{position:absolute;left:72px;right:72px;top:1230px;text-align:center;font-size:40px;color:#991B1B;font-weight:800}
"""


def md(s):
    """**x** → 红色加粗，==x== → 浅红底高亮，\\n → 换行。"""
    s = html.escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<span class="r">\1</span>', s)
    s = re.sub(r'==(.+?)==', r'<span class="hl">\1</span>', s)
    return s.replace('\\n', '<br>').replace('\n', '<br>')


def fig(code, kind='png1024'):
    idx = json.loads((STK / 'index.json').read_text())['items']
    it = next((x for x in idx if x['id'] == str(code).zfill(2) or x['name'] == code), None)
    if not it:
        raise ValueError(f'找不到表情 {code}')
    return (ROOT / it['png1024'] if not pathlib.Path(it['png1024']).is_absolute() else pathlib.Path(it['png1024'])).as_uri()


def bust(code='06'):
    return (STK / 'bust' / f'{str(code).zfill(2)}.png').as_uri()


def page(card, i, n, column, base):
    t = card['type']
    foot = (f'<div class="foot"><div class="who"><img src="{bust(card.get("bust", "06"))}">{NAME}</div>'
            f'<div class="pn">{html.escape(column)} · {i}/{n}</div></div>')
    if t == 'cover':
        lines = card['title'].count('\n') + card['title'].count('\\n') + 1
        sub_top = 220 + int(150 * 1.18 * lines) + 56
        body = (f'<div style="position:absolute;left:72px;top:110px"><span class="tag">{html.escape(card.get("tag", column))}</span></div>'
                f'<div class="cv-t">{md(card["title"])}</div>'
                + (f'<div class="cv-s" style="top:{sub_top}px">{md(card["sub"])}</div>' if card.get('sub') else '')
                + f'<img class="cv-fig" src="{fig(card.get("sticker", "06"))}">'
                + f'<div class="cv-who"><b>{NAME}</b>天天拿 AI 干活的产品经理</div>')
        return body  # 封面不放页脚
    if t == 'text':
        items = card['body'] if isinstance(card['body'], list) else [card['body']]
        if card.get('list'):
            bd = ''.join(f'<div class="li"><i></i><div>{md(x)}</div></div>' for x in items)
        else:
            bd = ''.join(f'<p>{md(x)}</p>' for x in items)
        return (f'<div class="hd">' + (f'<div class="no">{html.escape(card["no"])}</div>' if card.get('no') else '')
                + f'<h2>{md(card["heading"])}</h2></div><div class="bd">{bd}'
                + (f'<div class="note">{md(card["note"])}</div>' if card.get('note') else '') + '</div>' + foot)
    if t == 'image':
        src = (base / card['image']).resolve().as_uri()
        return (f'<div class="hd">' + (f'<div class="no">{html.escape(card["no"])}</div>' if card.get('no') else '')
                + f'<h2>{md(card["heading"])}</h2></div><div class="im"><div class="frame"><img src="{src}"></div></div>'
                + (f'<div class="cap">{md(card["caption"])}</div>' if card.get('caption') else '') + foot)
    if t == 'end':
        chips = card.get('chips') or [('热点', 'AI 新闻说人话'), ('实测', '新工具先替你试'), ('能抄', '提示词直接给')]
        return (f'<div class="en-t">{md(card.get("title", "关注示例作者\\n每天一篇 AI 实测"))}</div>'
                f'<img class="en-fig" src="{fig(card.get("sticker", "07"))}">'
                f'<div class="en-chips">' + ''.join(f'<div class="chip">{html.escape(a)}<span>{html.escape(b)}</span></div>' for a, b in chips) + '</div>'
                + (f'<div class="en-q">{md(card["question"])}</div>' if card.get('question') else '') + foot)
    raise ValueError(f'未知卡片类型 {t}')


def render(spec_path, out_dir=None):
    from playwright.sync_api import sync_playwright
    from PIL import Image
    spec_path = pathlib.Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text())
    base = spec_path.parent
    out = pathlib.Path(out_dir) if out_dir else base / 'cards'
    out.mkdir(parents=True, exist_ok=True)
    cards = spec['cards']; n = len(cards); files = []
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': W, 'height': H})
        for i, c in enumerate(cards, 1):
            tmp = out / f'_p{i}.html'
            tmp.write_text(f'<!doctype html><meta charset=utf-8><style>{CSS}</style><div class="pg">{page(c, i, n, spec.get("column", ""), base)}</div>')
            pg.goto(tmp.as_uri()); pg.wait_for_timeout(300)
            png = out / f'{i:02d}.png'
            pg.screenshot(path=str(png), clip={'x': 0, 'y': 0, 'width': W, 'height': H})
            tmp.unlink()
            jpg = png.with_suffix('.jpg'); Image.open(png).convert('RGB').save(jpg, quality=92); png.unlink()
            files.append(jpg)
        b.close()
    print('\n'.join(str(f) for f in files))
    return files


if __name__ == '__main__':
    render(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
