#!/usr/bin/env python3
"""轻综艺花字（huazi）：综艺后期的描边花字和弹跳感，适合「抄作业」清单、提示词、轻松话题、互动帖视频版。

画面：夜蓝底（和视频封面同色）+ 波点网纹 + 三颗慢转的小星星；糖果色三件套：粉 #FF5C8A / 天蓝 #3DA9FC / 薄荷 #34D399（封面规范的栏目色）；
     标题、hook 大字、数字、字幕全部是「白字 + 粗粉描边 + 深色硬投影」的花字；卡片是白底贴纸 + 硬投影。
     10-16 下午起标题、hook 大字、金句、数字、标题栏、片尾问题和字幕关键词用站酷快乐体（ZCOOL KuaiLe，OFL，按本条用到的字子集化），
     字幕其余的字、清单/对比条目仍是思源黑体（看得清）。快乐体只有一个字重，关掉浏览器的假粗体（font-synthesis:none）。
不适合：出事、坏消息、严肃话题（spec 写 "serious": true 会自动退回默认效果）。
节奏：场景间停顿 0.3 秒；新画面弹入（0.86 倍、-2.5° 转正，轻微回弹 back.out(1.7)）；字幕每组弹出、左右交替微微歪着。
     回弹只用在花字元素上（综艺是明确的「好玩」语境，hyperframes 规范允许的例外），版面主体不弹。
转场：进「观点 / 章节 / 金句」和片尾时用泡泡转场：一个糖果色圆从左下角示例作者的位置涨满画面，再缩到右上角揭开新画面。
强调：念到 **关键词** 推近时带一点歪头（-1.5°）+ 两侧各喷一小把彩纸（固定种子、单驱动、可倒放）；
     字幕关键词薄荷色、放大 1.35 倍弹一下。
"""
import math

from . import Style, RX, TOPIC_TYPES, sub, drop_enter, lcg

NAVY, NAVY_D = '#14204A', '#0A1230'
PINK, SKY, MINT = '#FF5C8A', '#3DA9FC', '#34D399'
EM = '#7CF5C8'
STAR = ('<svg viewBox="0 0 100 100"><path d="M50 4 C54 36 64 46 96 50 C64 54 54 64 50 96 C46 64 36 54 4 50 C36 46 46 36 50 4Z" '
        'fill="{c}" stroke="{s}" stroke-width="5"/></svg>')
CONF_N = 16     # 每次彩纸片数（两侧各一半）


class Huazi(Style):
    name = 'huazi'
    title = '轻综艺花字'
    theme = {'bg1': NAVY, 'bg2': '#1D2C68', 'accent': PINK, 'accent2': SKY}
    pause = .3
    hook_pause = .2
    cjk = (('ZKL', 'ZCOOLKuaiLe-Regular.ttf', 400, '站酷快乐体'),)

    def css(self, cx):
        S = '.st-huazi'
        fz = lambda w, c=PINK, sh=6: f'-webkit-text-stroke:{w}px {c};paint-order:stroke fill;text-shadow:{sh}px {sh}px 0 {NAVY_D}'
        return f"""
{S} .grid{{background-image:radial-gradient(rgba(255,255,255,.075) 2.4px,transparent 2.8px);background-size:34px 34px}}
{S} #b1{{background:{PINK};opacity:.13}}
{S} .ghost{{color:{PINK};opacity:.04}}
{S} .hz-star{{position:absolute;pointer-events:none}}
{S} .brand{{background:#fff;color:{NAVY};border:none;border-radius:40px;font-weight:900;box-shadow:4px 4px 0 {PINK}}}
{S} .tag.col{{background:{PINK};color:#fff;border-radius:40px;box-shadow:3px 3px 0 {NAVY_D};transform:rotate(3deg)}}
{S} .title{{transform:rotate(-2deg)}}
{S} .title .tl1,{S} .title .tl2{{font-size:78px;color:#fff;{fz(11)}}}
{S} .title .tl2{{color:{SKY};-webkit-text-stroke-color:#fff}}
{S} .hook .hk-row{{{fz(13, sh=9)}}}
{S} .hook .hk-em{{color:{EM}}}
{S} .hook .flash{{background:{SKY};height:16px}}
{S} .pill{{background:#fff;color:{NAVY};border-radius:40px;box-shadow:5px 5px 0 {PINK}}}
{S} em{{color:{EM}}}
{S} .stat .num{{{fz(10, '#fff', 10)}}}
{S} .chapter .chp-n{{{fz(10, '#fff', 10)}}}
{S} .progress .pg-num{{{fz(9, '#fff', 8)}}}
{S} .list .li{{background:#fff;color:{NAVY};border:none;border-radius:26px;box-shadow:7px 7px 0 {NAVY_D}}}
{S} .list .li-n{{background:{PINK};color:#fff}}
{S} .list .li-t em{{color:{PINK}}}
{S} .compare .cp{{background:#fff;color:{NAVY};border:5px solid #fff;box-shadow:9px 9px 0 {NAVY_D}}}
{S} .compare .cp.good{{border-color:{MINT}}}
{S} .compare .cp.bad{{border-color:{PINK}}}
{S} .compare .cp em{{color:{PINK}}}
{S} .compare .bad .cp-badge{{background:{PINK};color:#fff}}
{S} .compare .vs{{background:{SKY};color:#fff;box-shadow:4px 4px 0 {NAVY_D};{fz(0)}}}
{S} .bars .br-track{{background:rgba(255,255,255,.1);border-radius:40px}}
{S} .bars .br-fill{{background:{SKY};border-radius:40px}}
{S} .bars .best .br-fill{{background:{PINK}}}
{S} .bars .best .br-v,{S} .bars .best .br-l{{color:#FFB3C9}}
{S} .highlight .hl-label{{background:#fff;color:{NAVY};border-radius:40px;box-shadow:4px 4px 0 {PINK}}}
{S} .highlight .hl-text{{{fz(9, NAVY_D, 7)}}}
{S} .highlight [data-m=highlight] .hl-et{{-webkit-text-stroke:0;text-shadow:none}}
{S} .highlight .hl-em:not([data-m=highlight]) .hl-et{{color:{EM}}}
{S} .screen .sc-step{{background:{PINK};color:#fff;border-radius:40px}}
{S} .screen .sc-win{{border:6px solid #fff;box-shadow:10px 10px 0 {NAVY_D}}}
{S} .screen .sc-box{{border-color:{PINK}}}
{S} .chat .ask{{background:{SKY};color:#fff}}
{S} .chat .ask em{{color:#fff}}
{S} .split .sp-after .sp-tag,{S} .split .sp-knob,{S} .endcard .ec-next{{color:#fff}}
{S} .endcard .ec-next{{border-radius:40px;box-shadow:4px 4px 0 {NAVY_D}}}
{S} .endcard .ec-q{{{fz(8, PINK, 6)}}}
{S} .capin{{color:#fff;font-weight:900;{fz(9, PINK, 5)};transform-origin:50% 60%}}
{S} .capin em{{color:{EM}}}
{S} #prog{{height:14px;background:linear-gradient(90deg,{SKY},{PINK},{MINT})}}
{S} #av .av-plate{{background:radial-gradient(closest-side,rgba(255,92,138,.28),transparent)}}
{S} .hz-wipe{{position:absolute;inset:0;clip-path:circle(0% at 17% 80%)}}
{S} .hz-conf{{position:absolute;left:0;top:0;width:0;height:0;opacity:0}}
{S} .hz-conf i{{position:absolute;left:-9px;top:-14px;width:18px;height:28px;border-radius:5px}}
{S} .title .tl1,{S} .title .tl2,{S} .hook .hk-row,{S} .highlight .hl-text,{S} .stat .num,{S} .chapter .chp-n,{S} .chapter .chp-t,{S} .progress .pg-num,{S} .list .heading,{S} .list .li-n,{S} .bars .heading,{S} .compare .cp-title,{S} .cta .cta-text,{S} .endcard .ec-q,{S} .endcard .ec-name,{S} .capin em{{font-family:ZKL,NS;font-synthesis:none}}
{S} .capin em{{-webkit-text-stroke-width:5px;text-shadow:4px 4px 0 {NAVY_D}}}
"""

    def bg(self, cx):
        stars = [(26, 452, 46, PINK), (1010, 462, 36, SKY), (968, 1232, 40, MINT)]
        return ''.join(f'<div class="hz-star" style="left:{x}px;top:{y}px;width:{s}px;height:{s}px">{STAR.format(c=c, s=NAVY_D)}</div>'
                       for x, y, s, c in stars)

    def _bursts(self, cx):
        """彩纸时刻：关键词推近的时刻 + highlight 落笔时刻，最多 4 次、相隔 ≥5 秒。"""
        cand = sorted([at for _, at in cx.punches] + [sc['_cue'] + .3 for sc in cx.scenes if sc.get('type') == 'highlight' and sc.get('_cue')])
        out = []
        for t in cand:
            if (not out or t - out[-1] >= 5) and (cx.ec_at is None or t < cx.ec_at - 1.2):
                out.append(t)
        return out[:4]

    def over(self, cx):
        out = []
        cols = [PINK, SKY, MINT]
        for n, (i, _) in enumerate(cx.bounds()):
            if cx.typ(i) in TOPIC_TYPES or i == cx.ec:
                out.append(f'<div class="hz-wipe" id="hzw{i}" style="background:{cols[n % 3]}"></div>')
        for b, _ in enumerate(self._bursts(cx)):
            for side, x in (('l', 70), ('r', 1010)):   # 从画面两侧边缘喷出，往外飞，不经过正文和字幕
                pcs = ''.join(f'<i style="background:{[PINK, SKY, MINT, "#fff"][k % 4]}"></i>' for k in range(CONF_N // 2))
                out.append(f'<div class="hz-conf" id="hzc{b}{side}" style="transform:translate({x}px,1230px)">{pcs}</div>')
        return ''.join(out)

    def js(self, cx, js):
        acc = []
        wipes = {i for i, _ in cx.bounds() if cx.typ(i) in TOPIC_TYPES or i == cx.ec}
        # 1) 换场：弹入 / 泡泡转场
        for i, T in cx.bounds():
            t = cx.typ(i)
            if i in wipes:
                acc.append(f'tl.fromTo("#hzw{i}",{{clipPath:"circle(0% at 17% 80%)"}},{{clipPath:"circle(150% at 17% 80%)",duration:.26,ease:"power2.in",immediateRender:false}},{T - .26:.3f});')
                acc.append(f'tl.fromTo("#hzw{i}",{{clipPath:"circle(150% at 85% 20%)"}},{{clipPath:"circle(0% at 85% 20%)",duration:.34,ease:"power2.out",immediateRender:false}},{T + .02:.3f});')
            if t == 'chapter':
                continue
            js, had = drop_enter(js, i)
            if had:
                at = T + (.12 if i in wipes else 0)
                acc.append(f'tl.fromTo("#s{i} .inner",{{opacity:0,scale:.86,rotation:-2.5}},{{opacity:1,scale:1,rotation:0,duration:.42,ease:"back.out(1.7)"}},{at:.3f});')
        # 2) 关键词推近带歪头
        js = sub(RX['punch_in'], lambda m: f'tl.to("#s{m.group(1)} .cam",{{scale:1.1,rotation:-1.5,duration:.2,ease:"power3.out"}},{m.group(2)});',
                 js, '关键词推近', expect=bool(cx.punches))
        js = sub(RX['punch_out'], lambda m: f'tl.to("#s{m.group(1)} .cam",{{scale:1,rotation:0,duration:.5,ease:"power2.inOut"}},{m.group(2)});',
                 js, '关键词回位', expect=bool(cx.punches))
        # 3) 字幕：每组弹出、左右交替微歪；关键词放大弹一下
        js = sub(RX['cap_in'], lambda m: (f'tl.fromTo("#c{m.group(1)} .capin",{{opacity:0,scale:.6,rotation:{-4 if int(m.group(1)) % 2 else 4}}},'
                                           f'{{opacity:1,scale:1,rotation:{-1.2 if int(m.group(1)) % 2 else 1.2},duration:.26,ease:"back.out(2.2)"}},{m.group(2)});'),
                 js, '字幕入场')
        js = sub(RX['cap_pop'], lambda m: (f'tl.fromTo("#c{m.group(1)} em",{{scale:1,rotation:0}},{{scale:1.35,rotation:-6,duration:.12,yoyo:true,repeat:1,'
                                            f'ease:"power2.out",stagger:{m.group(2)}}},{m.group(3)});'),
                 js, '字幕关键词', expect=bool(cx.cap_em))
        # 4) 彩纸：每把一个驱动补间，位置是时间的纯函数（particle-burst 规则），倒放/跳帧都对
        r = lcg(sum(map(ord, cx.spec.get('id', 'x'))) + 7)
        for b, at in enumerate(self._bursts(cx)):
            for side, sgn in (('l', 1), ('r', -1)):
                ps = []
                for k in range(CONF_N // 2):
                    ang = (55 + 30 * next(r)) * 3.14159 / 180     # 斜向上 55–85°，朝画面外侧偏
                    v = 620 + 380 * next(r)
                    ps.append(f'[{sgn * -v * math.cos(ang) * .8:.1f},{-v * math.sin(ang):.1f},{(next(r) - .5) * 900:.0f}]')
                acc.append(f'(function(){{var box=document.getElementById("hzc{b}{side}");var ps=box.children;var V=[{",".join(ps)}];var o={{t:0}};'
                           f'tl.fromTo(o,{{t:0}},{{t:1.2,duration:1.2,ease:"none",immediateRender:false,onUpdate:function(){{var t=o.t;'
                           f'box.style.opacity=(t>0.01&&t<1.19)?1:0;for(var k=0;k<ps.length;k++){{var v=V[k];'
                           f'var x=v[0]*t,y=v[1]*t+900*t*t,a=t<0.85?1:Math.max(0,(1.2-t)/0.35);'
                           f'ps[k].style.transform="translate("+x.toFixed(1)+"px,"+y.toFixed(1)+"px) rotate("+(v[2]*t).toFixed(0)+"deg)";ps[k].style.opacity=a.toFixed(2);}}}}}},{at:.3f});}})();')
        # 5) 星星慢转
        acc.append(f'tl.fromTo(".hz-star",{{rotation:0}},{{rotation:120,duration:{cx.total:.3f},ease:"none"}},0);')
        return js + '\n' + '\n'.join(acc)


STYLE = Huazi()
