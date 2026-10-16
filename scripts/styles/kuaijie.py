#!/usr/bin/env python3
"""快节奏卡点（kuaijie）：信息流快讯感，适合 12:00 热点、热点快反、快评。

画面：近黑底 + 信号红（换掉默认的黄），白色超粗字；标题第二行是红底反白块；斜向细速度纹。
节奏：场景间停顿 0.22 秒（默认 0.35），hook 后 0.12 秒；每句话开头一次「跳切推拉」（画面在 1.0 / 1.04 之间硬切，
     口播类真人剪辑常用的每句一刀，这里卡在配音的句子边界上）；截图/对话场景不跳，免得看不清字。
转场：cut-the-curve 横向甩切（faceless-explainer cut-catalog）：旧画面 0.2 秒加速左甩 + 糊掉，新画面从右边带速度接上，
     两条速度线同时扫过；进章节卡仍用默认的穿越推近。
强调：念到 **关键词** 推近加大到 1.12 + 6 帧震屏；字幕关键词是红底白字块。
信息流元素：右上角「02/05」第几条；底部进度条上按场景切分刻度。
"""
from . import Style, RX, sub, drop_enter, clip

INK = '#0A0A0D'
RED = '#FF4B2B'


class Kuaijie(Style):
    name = 'kuaijie'
    title = '快节奏卡点'
    theme = {'bg1': INK, 'bg2': '#16161C', 'accent': RED, 'accent2': '#FF9F43'}
    pause = .22
    hook_pause = .12

    def css(self, cx):
        S = '.st-kuaijie'
        return f"""
{S} .grid{{background-image:repeating-linear-gradient(115deg,rgba(255,255,255,.028) 0 2px,transparent 2px 46px);background-size:auto}}
{S} #b1{{display:none}}
{S} .ghost{{color:{RED};opacity:.035}}
{S} .stage{{transform-origin:486px 860px}}
{S} .brand{{background:#fff;color:{INK};border:none;border-radius:8px;font-weight:900}}
{S} .tag.col{{color:#fff;border-radius:6px}}
{S} .title .tl1{{font-size:82px;letter-spacing:-1px}}
{S} .title .tl2{{display:table;margin:8px auto 0;font-size:74px;color:#fff;background:{RED};padding:0 20px;border-radius:6px;text-shadow:none;line-height:1.22}}
{S} .pill,{S} .list .li-n,{S} .compare .vs,{S} .screen .sc-step,{S} .highlight .hl-label,{S} .split .sp-after .sp-tag,{S} .split .sp-knob,{S} .chat .ask,{S} .chat .ask em,{S} .endcard .ec-next{{color:#fff}}
{S} .pill{{border-radius:8px}}
{S} .hook .hk-sub{{border-radius:8px}}
{S} .list .li{{border-radius:14px;background:rgba(255,255,255,.06)}}
{S} .bars .br-track{{background:rgba(255,255,255,.06);border-radius:8px}}
{S} .bars .br-fill{{background:#4a4a55;border-radius:8px}}
{S} .bars .best .br-fill{{background:{RED}}}
{S} .compare .cp{{border-radius:18px}}
{S} .highlight [data-m=highlight] .hl-et{{color:#fff}}
{S} .capin{{-webkit-text-stroke:3px rgba(0,0,0,.9)}}
{S} .capin em{{color:#fff;background:{RED};-webkit-text-stroke:0;text-shadow:none}}
{S} #prog{{height:10px}}
{S} .clip.kj-count{{inset:auto;right:72px;top:226px;left:auto;font-size:26px;font-weight:800;letter-spacing:3px;color:rgba(255,255,255,.55);font-variant-numeric:tabular-nums}}
{S} .clip.kj-count b{{color:#fff}}
{S} .kj-tick{{position:absolute;bottom:0;width:6px;height:10px;margin-left:-3px;background:{INK}}}
{S} .kj-streak{{position:absolute;left:0;height:7px;border-radius:4px;background:linear-gradient(90deg,transparent,{RED} 40%,#fff);transform:translateX(1200px)}}
"""

    def over(self, cx):
        out = []
        mids = [i for i in range(cx.n) if i != cx.ec and cx.typ(i) != 'hook']
        for k, i in enumerate(mids):
            sc = cx.scenes[i]
            out.append(clip('kj-count', sc['_start'], sc['_end'] - sc['_start'], f'<b>{k + 1:02d}</b> / {len(mids):02d}'))
        for i, _ in cx.bounds():
            if cx.typ(i) != 'chapter':
                out.append(f'<div class="kj-streak" id="kjs{i}a" style="top:760px;width:560px"></div>'
                           f'<div class="kj-streak" id="kjs{i}b" style="top:990px;width:360px"></div>')
        return ''.join(out)

    def top(self, cx):
        return ''.join(f'<div class="kj-tick" style="left:{T / cx.total * 100:.2f}%"></div>' for _, T in cx.bounds())

    def js(self, cx, js):
        acc = []
        # 1) 慢推去掉，换成每句一刀的跳切推拉
        js = sub(RX['push'], '', js, '整场慢推')
        for i, sc in enumerate(cx.scenes):
            if i == cx.ec:
                continue
            acc.append(f'tl.set("#s{i} .stage",{{scale:1}},{sc["_start"]:.3f});')
            if cx.typ(i) in ('screen', 'chat', 'hook'):
                continue
            for k, st in enumerate(cx.line_starts(i)[1:], 1):
                acc.append(f'tl.set("#s{i} .stage",{{scale:{1.04 if k % 2 else 1}}},{st:.3f});')
        # 2) 换场：横向甩切 + 速度线
        for i, T in cx.bounds():
            if cx.typ(i) == 'chapter':
                continue
            js, had = drop_enter(js, i)
            if had or i == cx.ec:
                acc.append(f'tl.fromTo("#s{i} .inner",{{opacity:.35,x:230,filter:"blur(6px)"}},'
                           f'{{opacity:1,x:0,filter:"blur(0px)",duration:.32,ease:"power4.out"}},{T:.3f});')
            acc.append(f'tl.fromTo("#s{i - 1} .inner",{{x:0,opacity:1,filter:"blur(0px)"}},'
                       f'{{x:-230,opacity:0,filter:"blur(6px)",duration:.2,ease:"power4.in",immediateRender:false}},{T - .2:.3f});')
            acc.append(f'tl.fromTo("#kjs{i}a",{{x:1200}},{{x:-700,duration:.28,ease:"power2.inOut",immediateRender:false}},{T - .16:.3f});')
            acc.append(f'tl.fromTo("#kjs{i}b",{{x:1200}},{{x:-500,duration:.26,ease:"power2.inOut",immediateRender:false}},{T - .1:.3f});')
        # 3) 关键词：推近加大 + 震屏 6 帧
        js = sub(RX['punch_in'], lambda m: f'tl.to("#s{m.group(1)} .cam",{{scale:1.12,duration:.16,ease:"power3.out"}},{m.group(2)});',
                 js, '关键词推近', expect=bool(cx.punches))
        for i, at in cx.punches:
            for k, (dx, dy) in enumerate([(14, -8), (-11, 7), (8, -5), (-5, 3), (2, -1), (0, 0)]):
                acc.append(f'tl.set("#s{i} .cam",{{x:{dx},y:{dy}}},{at + .03 + k / 30:.3f});')
        # 4) 字幕组硬切弹出
        js = sub(RX['cap_in'], lambda m: f'tl.fromTo("#c{m.group(1)} .capin",{{opacity:0,scale:.9}},{{opacity:1,scale:1,duration:.12,ease:"power4.out"}},{m.group(2)});',
                 js, '字幕入场')
        return js + '\n' + '\n'.join(acc)


STYLE = Kuaijie()
