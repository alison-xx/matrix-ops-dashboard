#!/usr/bin/env python3
"""纪实实拍（jishi）：像拿相机跟拍的实测记录，适合「先试」实测、翻车现场、带截图证据多的条目。

画面：炭灰绿底 + 暖白字 + 钨丝橙强调（不用黄）；四角取景框 + 左上「● REC 00:00:12:05」时间码；暗角；
     （试过动态胶片颗粒：成片从 16MB 涨到 52MB，平台二压后还会变成色块，已去掉）
     标题左对齐带橙色竖条（片名条）；字幕是纪录片式半透明黑底条，字小一号、不描边。
     10-16 下午起「我的判断」金句、引用、截图下的说明用霞鹜文楷（LXGW WenKai Medium，OFL，按本条用到的字子集化），
     像现场笔记本上的手写批注；标题、字幕、清单仍是思源黑体。
节奏：场景间停顿 0.4 秒；不做推近，改成手持微晃（x ±4px、y ±3px、旋转 ±0.2°，几个正弦叠加，确定性），
     这是 faceless-explainer 里唯一认可的「保持画面活着」的手法（subtle jitter）。
转场：对焦拉入（新画面从 14px 模糊、1.035 倍收到清晰，0.55 秒）+ 0.14 秒「眨眼」黑场；
     进截图（screen）场景前换成快门：上下两片黑幕合上再打开，像按了一下快门。
强调：念到 **关键词** 推近减到 1.05、更慢；四角取景框同时往里收一下变橙色（像自动对焦锁定）；
     字幕关键词橙色 + 底下一条细线跟着念到的位置画出来。
"""
from . import Style, RX, sub, drop_enter

WARM = '#F2EFE8'
ORANGE = '#FF8A3D'
# 取景框四角（屏幕坐标，包住 .safe 缩放后的内容区 x 71–900、y 524–1196）
BOX = (52, 498, 920, 1222)
CORNER = 58


class Jishi(Style):
    name = 'jishi'
    title = '纪实实拍'
    theme = {'bg1': '#0E1211', 'bg2': '#171D1B', 'accent': ORANGE, 'accent2': '#8FC1AE'}
    pause = .4
    hook_pause = .2
    fonts = ('JetBrainsMono-700.woff2',)
    cjk = (('WK', 'LXGWWenKai-Medium.ttf', 500, '霞鹜文楷'),)

    def css(self, cx):
        S = '.st-jishi'
        x0, y0, x1, y1 = BOX
        c = CORNER
        return f"""
@font-face{{font-family:JBM;src:url("assets/fonts/JetBrainsMono-700.woff2");font-weight:700}}
{S}{{color:{WARM}}}
{S} .grid,{S} #b1,{S} .ghost{{display:none}}
{S} .brand{{background:rgba(0,0,0,.25);border:1.5px solid rgba(242,239,232,.45);border-radius:6px;font-weight:700;font-size:30px}}
{S} .tag.col{{background:none;color:{ORANGE};border:1.5px solid {ORANGE};border-radius:6px;letter-spacing:2px;font-size:28px}}
{S} .title{{text-align:left;left:72px;top:256px}}
{S} .title .tl1,{S} .title .tl2{{font-size:68px;font-weight:800;line-height:1.18;text-shadow:none;border-left:8px solid {ORANGE};padding-left:24px}}
{S} .title .tl2{{color:{ORANGE}}}
{S} .hook .hk-row{{font-weight:800}}
{S} .pill{{border-radius:6px}}
{S} .list .li{{background:rgba(255,255,255,.045);border:1.5px solid rgba(255,255,255,.12);border-radius:10px}}
{S} .compare .cp{{border-radius:12px;border-width:2px}}
{S} .bars .br-track{{border-radius:6px}}
{S} .bars .br-fill{{background:#8FC1AE;border-radius:6px}}
{S} .bars .best .br-fill{{background:{ORANGE}}}
{S} .screen .sc-win{{border-radius:8px;border:2px solid rgba(255,255,255,.25)}}
{S} .screen .sc-box{{border-color:{ORANGE}}}
{S} .capin{{font-size:50px;font-weight:700;color:{WARM};-webkit-text-stroke:0;text-shadow:none;background:rgba(0,0,0,.58);padding:8px 22px;border-radius:8px}}
{S}.has-av .capin{{font-size:50px}}
{S} .capin em{{color:{ORANGE};background:linear-gradient({ORANGE},{ORANGE}) no-repeat 0 100%/0% 4px;padding-bottom:4px}}
{S} #prog{{height:6px;opacity:.85}}
{S} #av .av-plate{{background:radial-gradient(closest-side,rgba(255,138,61,.18),transparent)}}
{S} .jx-vig{{position:absolute;inset:0;background:radial-gradient(ellipse 75% 60% at 50% 46%,transparent 55%,rgba(0,0,0,.5) 100%);pointer-events:none}}
{S} .jx-ui{{position:absolute;inset:0;opacity:0;pointer-events:none}}
{S} .jx-c{{position:absolute;width:{c}px;height:{c}px;border:0 solid rgba(242,239,232,.75)}}
{S} #jx-tl{{left:{x0}px;top:{y0}px;border-width:4px 0 0 4px}}
{S} #jx-tr{{left:{x1 - c}px;top:{y0}px;border-width:4px 4px 0 0}}
{S} #jx-bl{{left:{x0}px;top:{y1 - c}px;border-width:0 0 4px 4px}}
{S} #jx-br{{left:{x1 - c}px;top:{y1 - c}px;border-width:0 4px 4px 0}}
{S} .jx-rec{{position:absolute;left:{x0 + 4}px;top:{y0 - 46}px;font:700 24px/1 JBM,NS;letter-spacing:2px;color:rgba(242,239,232,.82);display:flex;align-items:center;gap:12px}}
{S} .jx-rec i{{display:block;width:16px;height:16px;border-radius:50%;background:#FF3B30}}
{S} .jx-dip{{position:absolute;inset:0;background:#000;opacity:0}}
{S} .jx-sh{{position:absolute;left:0;width:1080px;height:960px;background:#050605}}
{S} .highlight .hl-text,{S} .quote .q-text,{S} .screen .sc-cap{{font-family:WK,NS;font-synthesis:none}}
"""

    def over(self, cx):
        out = ['<div class="jx-vig"></div>',
               '<div class="jx-ui" id="jx-ui"><div class="jx-c" id="jx-tl"></div><div class="jx-c" id="jx-tr"></div>'
               '<div class="jx-c" id="jx-bl"></div><div class="jx-c" id="jx-br"></div>'
               '<div class="jx-rec"><i id="jx-dot"></i><span>REC</span><span id="jx-tc">00:00:00:00</span></div></div>']
        for i, _ in cx.bounds():
            if cx.typ(i) == 'screen':
                out.append(f'<div class="jx-sh" id="jxs{i}t" style="top:0;transform:translateY(-960px)"></div>'
                           f'<div class="jx-sh" id="jxs{i}b" style="top:960px;transform:translateY(960px)"></div>')
            elif cx.typ(i) != 'chapter':
                out.append(f'<div class="jx-dip" id="jxd{i}"></div>')
        return ''.join(out)

    def js(self, cx, js):
        acc, total = [], cx.total
        # 1) 慢推 → 手持微晃（纯时间函数，seek 安全）
        js = sub(RX['push'], '', js, '整场慢推')
        for i, sc in enumerate(cx.scenes):
            s, e = sc['_start'], sc['_end']
            ph = 1.7 * i
            acc.append(f'(function(){{var el=document.querySelector("#s{i} .stage");var o={{t:{s:.3f}}};'
                       f'tl.fromTo(o,{{t:{s:.3f}}},{{t:{e + .7:.3f},duration:{e + .7 - s:.3f},ease:"none",onUpdate:function(){{var t=o.t+{ph:.2f};'
                       f'el.style.transform="translate("+(2.6*Math.sin(t*1.31)+1.4*Math.sin(t*2.93)).toFixed(2)+"px,"+'
                       f'(2.0*Math.sin(t*1.07+1.1)+1.0*Math.sin(t*2.41)).toFixed(2)+"px) rotate("+(0.16*Math.sin(t*0.83+.4)).toFixed(3)+"deg)";}}}},{s:.3f});}})();')
        # 2) 换场：对焦拉入 + 眨眼黑场 / 截图前快门
        for i, T in cx.bounds():
            t = cx.typ(i)
            if t == 'chapter':
                continue
            js, had = drop_enter(js, i)
            if had or i == cx.ec:
                acc.append(f'tl.fromTo("#s{i} .inner",{{opacity:.15,scale:1.035,filter:"blur(14px)"}},'
                           f'{{opacity:1,scale:1,filter:"blur(0px)",duration:.55,ease:"power2.out"}},{T + .02:.3f});')
            if t == 'screen':
                for c, y in (('t', -960), ('b', 960)):
                    acc.append(f'tl.fromTo("#jxs{i}{c}",{{y:{y}}},{{y:0,duration:.16,ease:"power3.in",immediateRender:false}},{T - .16:.3f});')
                    acc.append(f'tl.fromTo("#jxs{i}{c}",{{y:0}},{{y:{y},duration:.24,ease:"power3.out",immediateRender:false}},{T + .06:.3f});')
            else:
                acc.append(f'tl.fromTo("#jxd{i}",{{opacity:0}},{{opacity:.92,duration:.14,ease:"power1.in",immediateRender:false}},{T - .14:.3f});')
                acc.append(f'tl.fromTo("#jxd{i}",{{opacity:.92}},{{opacity:0,duration:.3,ease:"power2.out",immediateRender:false}},{T:.3f});')
        # 3) 关键词：推近更轻更慢 + 取景框对焦锁定
        js = sub(RX['punch_in'], lambda m: f'tl.to("#s{m.group(1)} .cam",{{scale:1.05,duration:.35,ease:"power2.out"}},{m.group(2)});',
                 js, '关键词推近', expect=bool(cx.punches))
        inward = {'tl': (16, 16), 'tr': (-16, 16), 'bl': (16, -16), 'br': (-16, -16)}
        for _, at in cx.punches:
            for k, (dx, dy) in inward.items():
                acc.append(f'tl.fromTo("#jx-{k}",{{x:0,y:0,borderColor:"rgba(242,239,232,.75)"}},'
                           f'{{x:{dx},y:{dy},borderColor:"{ORANGE}",duration:.22,ease:"power2.out",immediateRender:false}},{at:.3f});')
                acc.append(f'tl.fromTo("#jx-{k}",{{x:{dx},y:{dy},borderColor:"{ORANGE}"}},'
                           f'{{x:0,y:0,borderColor:"rgba(242,239,232,.75)",duration:.4,ease:"power2.inOut",immediateRender:false}},{at + .9:.3f});')
        # 4) 字幕关键词：细下划线跟着念到的位置画出来（取代弹跳）
        js = sub(RX['cap_pop'], lambda m: (f'tl.fromTo("#c{m.group(1)} em",{{backgroundSize:"0% 4px"}},'
                                            f'{{backgroundSize:"100% 4px",duration:.1,ease:"none",stagger:{m.group(2)}}},{m.group(3)});'),
                 js, '字幕关键词', expect=bool(cx.cap_em))
        # 5) 取景框 + REC：hook 结束出现，片尾开始收掉
        end = cx.ec_at if cx.ec_at is not None else total
        acc.append(f'tl.fromTo("#jx-ui",{{opacity:0}},{{opacity:1,duration:.4,ease:"power2.out",immediateRender:false}},{cx.t0:.3f});')
        acc.append(f'tl.fromTo("#jx-ui",{{opacity:1}},{{opacity:0,duration:.25,ease:"power2.in",immediateRender:false}},{max(end - .05, cx.t0 + .5):.3f});')
        n_blink = max(1, int(total / .5))
        acc.append(f'tl.fromTo("#jx-dot",{{opacity:1}},{{opacity:.15,duration:.5,ease:"steps(1)",yoyo:true,repeat:{n_blink}}},0);')
        acc.append(f'(function(){{var el=document.getElementById("jx-tc");var o={{t:0}};tl.fromTo(o,{{t:0}},{{t:{total:.3f},duration:{total:.3f},ease:"none",'
                   f'onUpdate:function(){{var f=Math.floor(o.t*30+1e-6),p=function(n){{return (n<10?"0":"")+n;}};'
                   f'el.textContent="00:"+p(Math.floor(f/1800)%60)+":"+p(Math.floor(f/30)%60)+":"+p(f%30);}}}},0);}})();')
        return js + '\n' + '\n'.join(acc)


STYLE = Jishi()
