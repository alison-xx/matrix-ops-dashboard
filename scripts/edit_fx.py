#!/usr/bin/env python3
"""剪辑手法 + 统一片尾（make_motion 用，10-16）。

依据：hyperframes-creative / faceless-explainer 的剪辑规范 + 10-16 片尾调研（各平台创作者做法、诱导互动红线）。
  prepare()      J-cut：新场景画面比配音早 0.18s 出现（落在上一句后的换气里）；记录下一个场景类型（进 chapter 用穿越推近）
  punch_js()     念到 **关键词** 那一拍镜头推近 1→1.1（0.2s power3.out），下一句开头回到 1；每 8 秒最多一次
  caption_pop()  字幕里的黄字在被念到时弹一下（1→1.15→1，0.2s）
  endcard_*      统一片尾（最后一个 cta 场景自动套用）：问题大字 → 示例作者从左下角走到中间 → 「示例聊AI」落定 + 光环 +
                 固定声音 logo（pop + chime）→ 人设一行 → 下集预告 / 合集胶囊；最后一帧就是身份帧。
                 不放二维码、微信号、外链，不喊点赞关注三连（平台诱导互动红线）。
"""
import html, re

LEAD = 0.18
EC_CSS = """
.cam{position:absolute;inset:0;transform-origin:50% 42%}
.capin em{display:inline-block}
.inner.endcard{display:block}
.inner.endcard{top:380px}
.endcard .ec-q{position:absolute;left:0;right:0;top:-50px;text-align:center;font-size:84px;font-weight:900;line-height:1.28;text-wrap:balance}
.endcard .ec-ring{position:absolute;left:50%;top:432px;width:440px;height:440px;margin:-220px 0 0 -220px;border-radius:50%;border:6px solid var(--accent);opacity:0}
.endcard .ec-av{position:absolute;left:50%;top:432px;width:280px;height:280px;margin:-140px 0 0 -140px;border-radius:50%;object-fit:cover;border:6px solid var(--accent)}
.endcard .ec-name{position:absolute;left:0;right:0;top:690px;text-align:center;font-size:76px;font-weight:900;letter-spacing:2px}
.endcard .ec-tag{position:absolute;left:0;right:0;top:785px;text-align:center;font-size:38px;font-weight:500;opacity:.8;letter-spacing:4px}
.endcard .ec-follow{position:absolute;left:50%;top:840px;transform:translateX(-50%);height:66px;min-width:300px;border-radius:40px;
  background:#ff4d6d;color:#fff;font-size:38px;font-weight:900;display:flex;align-items:center;justify-content:center;padding:0 34px}
.endcard .ec-follow .f-b{position:absolute;opacity:0}
.endcard .ec-next{position:absolute;left:50%;top:925px;transform:translateX(-50%);white-space:nowrap;font-size:36px;font-weight:800;color:#111;background:var(--accent);padding:10px 30px;border-radius:40px}
"""


def _w(s):
    s = re.sub(r'\*\*', '', s)
    return sum(0.55 if c.isascii() and c.isalnum() else (2.0 if c in '，。？！；：' else (0 if c.isascii() else 1)) for c in s)


def prepare(spec):
    sc_ = spec['scenes']
    for i, sc in enumerate(sc_):
        sc['_next_type'] = sc_[i + 1].get('type') if i + 1 < len(sc_) else None
    for i in range(1, len(sc_)):
        prev, sc = sc_[i - 1], sc_[i]
        lead = min(LEAD, max(0.0, sc['_start'] - (prev.get('_lines') or [(prev['_start'], 0)])[-1][0] - (prev.get('_lines') or [(0, 0)])[-1][1]))
        sc['_start'] = round(sc['_start'] - lead, 3)
        prev['_end'] = sc['_start']


def punch_js(spec, lines):
    """关键词推近：作用在每个场景的 .cam 上（.stage 已经在做全场慢推，两个 transform 分开）。"""
    js, last = [], -99.0
    skip = {'screen', 'chat', 'cta', 'endcard'}
    for i, sc in enumerate(spec['scenes']):
        if sc.get('type') in skip or (i == 0 and sc.get('type') == 'hook'):
            continue
        ls = [ln for ln in lines if ln['scene'] == i]
        for k, ln in enumerate(ls):
            m = re.search(r'\*\*', ln['text'])
            if not m:
                continue
            at = ln['start'] + ln['dur'] * _w(ln['text'][:m.start()]) / max(_w(ln['text']), 1) - 0.05
            if at - last < 8:
                continue
            back = ls[k + 1]['start'] if k + 1 < len(ls) else min(at + 1.4, sc['_end'] - 0.1)
            if back - at < 0.5:
                continue
            js.append(f'tl.to("#s{i} .cam",{{scale:1.1,duration:.2,ease:"power3.out"}},{at:.3f});')
            js.append(f'tl.to("#s{i} .cam",{{scale:1,duration:.5,ease:"power2.inOut"}},{back:.3f});')
            last = at
    return '\n'.join(js)


def caption_pop(groups):
    js = []
    for k, g in enumerate(groups):
        toks = re.findall(r'<span class="k">(.*?)</span>', g['html'])
        idx = [j for j, tk in enumerate(toks) if tk.startswith('<em>')]
        if not idx:
            continue
        per = g['dur'] * .8 / max(g['n'], 1)
        at = g['start'] + per * idx[0]
        js.append(f'tl.fromTo("#c{k} em",{{scale:1}},{{scale:1.15,duration:.1,yoyo:true,repeat:1,ease:"power2.out",stagger:{per:.3f}}},{at:.3f});')
    return '\n'.join(js)


# 片尾整体比普通场景高 90px（10-16 安全区：字幕原来在 1490，落进抖音账号名/文案区；标题片尾已淡出，上面有空）
EC_TOP = 380                 # .inner.endcard 的 top（普通场景 470）
EC_RING_Y = EC_TOP + 432     # 光环圆心的绝对 y（.ec-ring top:432px）
EC_CAP_TOP = 1400            # 片尾字幕位置，主视觉底线 1450 附近，避开底部 300px


def endcard_html(spec, sc, has_av):
    def mark(s):
        return re.sub(r'\*\*(.+?)\*\*', r'<em>\1</em>', html.escape(s)).replace('\n', '<br>')
    name = spec.get('brand') or ('示例办公课' if spec.get('account') == 'office' else '示例聊AI')
    tag = spec.get('persona') or ('带办公室小白把 AI 智能体用起来' if spec.get('account') == 'office' else '每天拿AI干活的产品人')
    nxt = sc.get('next') or spec.get('next')
    series = spec.get('series')
    pill = f'下集｜{nxt}' if nxt else (f'合集 · {series}' if series else '每天一个能用上的AI')
    av = '' if has_av else '<img class="ec-av" src="assets/avatar/endcard.jpg" alt=""/>'
    return (f'<div class="inner endcard"><div class="ec-q">{mark(sc.get("text", ""))}</div><div class="ec-ring"></div>{av}'
            f'<div class="ec-name">{html.escape(name)}</div><div class="ec-tag">{html.escape(tag)}</div>'
            f'<div class="ec-follow"><span class="f-a">＋ 关注</span><span class="f-b">✓ 已关注</span></div>'
            f'<div class="ec-next">{html.escape(pill)}</div></div>')


FOLLOW_LINE = {'creator': '关注示例作者，每天一个能直接用上的AI。', 'office': '关注我，AI工作台 每一课都会接着讲。'}


def ensure_follow_line(spec):
    """片尾统一引导关注（10-16 用户要求）：最后一个 cta 场景里没提「关注」，就在最前面补一句带理由的引导，问题留在最后一句。"""
    if not spec.get('scenes') or spec['scenes'][-1].get('type') not in ('cta', 'endcard') or spec.get('follow') is False:
        return
    sc = spec['scenes'][-1]
    if not any('关注' in x for x in sc.get('lines', [])):
        sc['lines'] = [FOLLOW_LINE.get(spec.get('account', 'creator'), FOLLOW_LINE['creator'])] + sc.get('lines', [])


def endcard_js(sc, i, has_av):
    s = sc['_start']
    sid = f'#s{i}'
    js = [f'tl.fromTo("{sid} .ec-q",{{opacity:0,y:30}},{{opacity:1,y:0,duration:.35,ease:"expo.out"}},{s:.3f});',
          # 顶部标题 10-16 起为避开抖音「推荐/搜索」栏下移到 250px，会压到片尾的提问：片尾开始时淡出
          f'tl.to(".title",{{opacity:0,duration:.25,ease:"power2.in"}},{s:.3f});',
          # 字幕挪到身份帧下面：有没有口播小人都要挪（10-16 Office 号关了小人，字幕留在 1300 正好压在 .ec-next 胶囊上）
          f'tl.set(".cap",{{left:60,right:130,top:{EC_CAP_TOP}}},{s:.3f});']
    if has_av:   # 左下角说话的示例作者走到画面中间，成为身份帧的主角；字幕挪到身份帧下面
        from avatar_layer import AV_LEFT, AV_TOP, AV_SIZE
        sc_ = 1.5    # 放大后上沿离问题文字、下沿离「示例聊AI」各留 20px 以上（不挡字）
        dx = 540 - AV_SIZE / 2 - AV_LEFT
        dy = (EC_RING_Y - AV_SIZE * sc_ / 2 + AV_SIZE * sc_) - (AV_TOP + AV_SIZE)   # 视觉中心对准光环，以底边为缩放原点
        js.append(f'tl.to("#av",{{x:{dx:.0f},y:{dy:.0f},scale:{sc_},duration:.6,ease:"power3.inOut"}},{s + .05:.3f});')
        js.append(f'tl.to("#av-sym",{{opacity:0,duration:.2}},{s:.3f});')
    else:
        js.append(f'tl.fromTo("{sid} .ec-av",{{opacity:0,scale:.6}},{{opacity:1,scale:1,duration:.45,ease:"power3.out"}},{s + .1:.3f});')
    js.append(f'tl.fromTo("{sid} .ec-ring",{{opacity:.7,scale:1}},{{opacity:0,scale:2.4,duration:.8,ease:"power2.out"}},{s + .6:.3f});')
    js.append(f'tl.fromTo("{sid} .ec-name",{{opacity:0,scale:1.15}},{{opacity:1,scale:1,duration:.45,ease:"expo.out"}},{s + .6:.3f});')
    js.append(f'tl.fromTo("{sid} .ec-tag",{{opacity:0,y:20}},{{opacity:1,y:0,duration:.35,ease:"power3.out"}},{s + .9:.3f});')
    js.append(f'tl.fromTo("{sid} .ec-follow",{{opacity:0,y:20}},{{opacity:1,y:0,duration:.35,ease:"power3.out"}},{s + 1.0:.3f});')
    # 「＋关注」被点一下 → 「✓ 已关注」（按下 0.12s、弹回 0.25s），灰色胶囊
    js.append(f'tl.to("{sid} .ec-follow",{{scale:.9,duration:.12,ease:"power3.in"}},{s + 1.7:.3f});')
    js.append(f'tl.to("{sid} .ec-follow",{{scale:1,backgroundColor:"#3a3f4b",duration:.25,ease:"power3.out"}},{s + 1.82:.3f});')
    js.append(f'tl.set("{sid} .ec-follow .f-a",{{opacity:0}},{s + 1.82:.3f});tl.set("{sid} .ec-follow .f-b",{{opacity:1}},{s + 1.82:.3f});')
    # xPercent:-50 写明：GSAP 只在 matrix 平移恰好等于 -offsetWidth/2（取整）时才认出 CSS 的 translateX(-50%)，胶囊宽度带小数时会丢掉居中，整条往右偏半个宽度（10-16 office-1 实测）
    js.append(f'tl.fromTo("{sid} .ec-next",{{opacity:0,x:80,xPercent:-50}},{{opacity:1,x:0,xPercent:-50,duration:.4,ease:"power3.out"}},{s + 1.3:.3f});')
    return '\n'.join(js)


def endcard_sfx(sc):
    """固定声音 logo：pop（形象落位）+ chime（名字落定）。10-16：chime 换成截短淡出的 chime-dry（原版 2.5 秒拖尾压在片尾口播下面，听着像回音），音量整体压低。"""
    s = sc['_start']
    return (f'<audio id="ec-pop" src="assets/sfx/pop.mp3" data-start="{s + .45:.3f}" data-duration="0.72" data-volume="0.22" data-track-index="8"></audio>'
            f'<audio id="ec-chime" src="assets/sfx/chime-dry.mp3" data-start="{s + .6:.3f}" data-duration="0.9" data-volume="0.2" data-track-index="9"></audio>'
            f'<audio id="ec-tap" src="assets/sfx/click.mp3" data-start="{s + 1.7:.3f}" data-duration="0.37" data-volume="0.25" data-track-index="10"></audio>')
