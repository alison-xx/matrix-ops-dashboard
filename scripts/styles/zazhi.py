#!/usr/bin/env python3
"""杂志编辑（zazhi）：纸面排版感，适合「算账」、周报/深度、长一点的系列和 Office 办公课。

画面：米白纸底（封面规范「米白」#F5F0E6 一系）+ 深藏青墨色 + 珊瑚橙强调，细颗粒纸纹；顶部双细线报头；
     标题左对齐、第一行 SemiBold 第二行 Bold 的字重对比；10-16 下午起标题、hook 大字、金句、章节名、片尾问题用思源宋体
     （Noto Serif SC，OFL，按本条用到的字子集化）；大号数字用 EB Garamond（OFL 开源衬线）；字幕和清单条目仍是思源黑体；
     spec 里写了深色 theme 会被忽略（浅色版面配深色底，墨色字就看不见了；10-16 Office 第 0 课的 spec 就带深绿 theme）；
     卡片换成细线分隔的版面（清单是一条条横线，截图是描边 + 错位投影）；每个场景左上角一行眉题「№ 03 · 数据」。
     account=office 时自动换 Office 配色（奶白 / 墨绿 / 橙，封面规范 1.4）。
节奏：场景间停顿 0.45 秒（默认 0.35），留呼吸；不做整场慢推、不做关键词推近（版面不晃）。
转场：纵向翻页推移（旧版面上移出画、新版面从下面推上来，两版之间留白不重叠，约 0.6 秒 power3.inOut；推移时只在正文区窗口里露出来，不从标题和字幕底下穿过）；
     进「观点 / 章节 / 金句」这类话题切换和进片尾时换成两块色块（墨色 + 强调色）由下往上盖过去再揭开。
强调：字幕关键词用荧光笔一笔划过（逐字跟着念到的位置走），不再弹跳。
"""
from . import Style, RX, TOPIC_TYPES, sub, drop_enter, clip, kind_label, warn

PALETTES = {
    'creator': {'paper': '#F3EEE4', 'paper2': '#ECE5D7', 'ink': '#14204A', 'accent': '#FF5A36', 'mark': 'rgba(255,90,54,.42)'},
    'office': {'paper': '#FBF8F1', 'paper2': '#F1ECE0', 'ink': '#1F5A40', 'accent': '#E8792B', 'mark': 'rgba(232,121,43,.40)'},
}
WIN = 'inset(492px 0px 680px 0px)'   # 正文区窗口：眉题下沿 ~490 到字幕上沿 1240
NOISE = ("url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'>"
         "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/>"
         "<feColorMatrix values='0 0 0 0 .1  0 0 0 0 .1  0 0 0 0 .2  0 0 0 .55 0'/></filter>"
         "<rect width='100%' height='100%' filter='url(%23n)'/></svg>\")")


class Zazhi(Style):
    name = 'zazhi'
    title = '杂志编辑'
    pause = .45
    hook_pause = .25
    fonts = ('EBGaramond-400.woff2', 'EBGaramond-700.woff2')
    cjk = (('NSerif', 'NotoSerifSC-SemiBold.otf', 600, '思源宋体 SemiBold'), ('NSerif', 'NotoSerifSC-Bold.otf', 700, '思源宋体 Bold'))
    PUSH = 1000      # 翻页推移的距离：正文区高约 670px，两版之间留 300px 以上空白，推移中不会叠字
    PUSH_D = .6

    def prepare(self, spec):
        if spec.get('theme'):
            warn('杂志风是浅色版面，spec 里的 theme 不用（配色按账号自动给：示例作者米白/藏青/珊瑚橙，Office 奶白/墨绿/橙）')
            spec.pop('theme')
        super().prepare(spec)

    def blocky(self, cx, i):
        """话题切换（观点/章节/金句）和进片尾用色块翻页，其余用纵向推移。"""
        return cx.typ(i) in TOPIC_TYPES or i == cx.ec

    def pal(self, spec):
        return PALETTES['office' if spec.get('account') == 'office' else 'creator']

    def theme_for(self, spec):
        p = self.pal(spec)
        return {'bg1': p['paper'], 'bg2': p['paper2'], 'accent': p['accent'], 'accent2': p['ink']}

    def css(self, cx):
        p = self.pal(cx.spec)
        S, ink, acc, paper = '.st-zazhi', p['ink'], p['accent'], p['paper']
        a = lambda x: f'color-mix(in srgb,{ink} {x}%,transparent)'
        return f"""
@font-face{{font-family:EBG;src:url("assets/fonts/EBGaramond-400.woff2");font-weight:400}}
@font-face{{font-family:EBG;src:url("assets/fonts/EBGaramond-700.woff2");font-weight:700}}
{S}{{color:{ink}}}
{S} .grid{{background-image:{NOISE};background-size:240px 240px;opacity:.22}}
{S} #b1{{display:none}}
{S} .ghost{{color:{ink};opacity:.018;font-family:EBG,NS}}
{S} .zz-rule{{position:absolute;left:72px;right:72px;top:236px;height:0;border-top:3px solid {ink};border-bottom:1px solid {ink};padding-top:4px}}
{S} .brand{{background:none;border:none;padding:0;top:178px;color:{ink};font-size:32px;font-weight:900;letter-spacing:6px}}
{S} .tag.col{{background:none;color:{acc};border:2px solid {acc};border-radius:0;font-size:26px;padding:4px 14px;top:176px}}
{S} .title{{text-align:left;top:258px}}
{S} .title .tl1,{S} .title .tl2{{text-shadow:none;font-size:72px;line-height:1.16;letter-spacing:1px}}
{S} .title .tl1{{font-weight:300}}
{S} .title .tl2{{color:{acc};font-weight:900}}
{S} .clip.zz-kick{{inset:auto;left:72px;top:442px;font-size:30px;font-weight:700;letter-spacing:3px;color:{a(70)}}}
{S} .clip.zz-kick b{{font-family:EBG,NS;font-size:38px;font-weight:700;color:{acc};margin-right:10px;letter-spacing:1px}}
{S} em{{color:{acc}}}
{S} .pill{{background:{ink};color:{paper};border-radius:0}}
{S} .hook .hk-row{{text-shadow:none;font-weight:900}}
{S} .hook .hk-row:first-child{{font-weight:300}}
{S} .hook .flash{{height:6px;border-radius:0;width:36%}}
{S} .stat .num,{S} .progress .pg-num,{S} .chapter .chp-n,{S} .highlight .hl-text,{S} .split .sp-after .sp-val{{text-shadow:none}}
{S} .stat .num,{S} .progress .pg-num,{S} .chapter .chp-n,{S} .bars .br-v,{S} .split .sp-val,{S} .list .li-n,{S} .compare .vs{{font-family:EBG,NS;font-variant-numeric:lining-nums}}
{S} .stat .st-line,{S} .quote .q-line,{S} .chapter .chp-bar{{height:4px;border-radius:0;background:{ink}}}
{S} .list .li{{background:none;border:none;border-top:2px solid {ink};border-radius:0;margin:0;padding:26px 6px}}
{S} .list .li:last-child{{border-bottom:2px solid {ink}}}
{S} .list .li-n{{background:none;color:{acc};font-size:66px;font-weight:700;justify-content:flex-start;flex:0 0 76px;margin-right:18px}}
{S} .list .li-t{{font-weight:700}}
{S} .compare .cp{{background:#fff;border:2px solid {a(18)};border-radius:4px;box-shadow:10px 10px 0 {a(10)}}}
{S} .compare .cp.good{{border:3px solid {ink}}}
{S} .compare .cp.bad{{background:{a(4)}}}
{S} .compare .good .cp-badge{{background:{ink};color:{paper}}}
{S} .compare .bad .cp-badge{{background:{acc};color:#fff}}
{S} .compare .vs{{background:{paper};color:{ink};border:2px solid {ink};font-style:italic;font-weight:700}}
{S} .timeline .tl-line{{background:{ink};height:4px;border-radius:0}}
{S} .timeline .tl-dot{{background:{paper};border-color:{ink}}}
{S} .quote .q-mark{{font-family:EBG,NS;color:{acc}}}
{S} .quote .q-text{{font-weight:300}}
{S} .cta .cta-hint{{background:{a(8)}}}
{S} .screen .sc-step{{background:{ink};color:{paper};border-radius:0}}
{S} .screen .sc-win,{S} .image .frame{{border:2px solid {ink};border-radius:4px;box-shadow:14px 14px 0 {a(12)}}}
{S} .screen .sc-box{{border-color:{acc}}}
{S} .chat .ct-model{{background:none;border:2px solid {ink};border-radius:0}}
{S} .chat .ask{{background:{ink};color:{paper}}}
{S} .chat .ask em{{color:{paper}}}
{S} .chat .reply{{background:#fff;border:2px solid {a(15)}}}
{S} .chat .ct-stamp{{background:{paper}}}
{S} .bars .br-track{{background:{a(7)};border-radius:0}}
{S} .bars .br-fill{{background:{ink};border-radius:0}}
{S} .bars .best .br-fill{{background:{acc}}}
{S} .highlight .hl-label{{background:{ink};color:{paper};border-radius:0}}
{S} .highlight .hl-em[data-m=scribble] .hl-et{{color:{ink}}}
{S} .progress .pg-track{{background:{a(8)};border:none;border-radius:0}}
{S} .progress .pg-fill{{background:{acc};border-radius:0}}
{S} .progress .pg-ring{{background:conic-gradient({acc} calc(var(--p) * 1%),{a(10)} 0)}}
{S} .split .sp-wrap{{border:2px solid {ink};border-radius:4px;box-shadow:none}}
{S} .split .sp-before{{background:{a(4)}}}
{S} .split .sp-tag{{background:{a(10)}}}
{S} .split .sp-after .sp-tag,{S} .split .sp-knob{{color:#fff}}
{S} .split .sp-div{{box-shadow:none}}
{S} .tag.col,{S} .endcard .ec-next{{border-radius:0}}
{S} .endcard .ec-next{{background:{ink};color:{paper}}}
{S} .capin{{color:{ink};-webkit-text-stroke:0;text-shadow:none;font-weight:800}}
{S} .capin em{{color:{ink};background:linear-gradient({p['mark']},{p['mark']}) no-repeat 0 78%/0% 46%}}
{S} #prog{{height:6px;background:{ink}}}
{S} #av .av-plate{{background:radial-gradient(closest-side,{a(14)},transparent)}}
{S} .clip.stk-clip .stk{{filter:drop-shadow(0 8px 14px {a(25)})}}
{S} .zz-block{{position:absolute;left:0;top:0;width:1080px;height:1920px;transform:translateY(1920px)}}
{S} .title .tl1,{S} .title .tl2,{S} .hook .hk-row,{S} .highlight .hl-text,{S} .quote .q-text,{S} .chapter .chp-t,{S} .cta .cta-text,{S} .endcard .ec-q,{S} .endcard .ec-name,{S} .list .heading,{S} .bars .heading,{S} .compare .cp-title{{font-family:NSerif,NS;font-synthesis:none}}
{S} .title .tl2,{S} .hook .hk-row,{S} .highlight .hl-text,{S} .chapter .chp-t,{S} .cta .cta-text,{S} .endcard .ec-q,{S} .endcard .ec-name,{S} .list .heading,{S} .bars .heading,{S} .compare .cp-title{{font-weight:700}}
{S} .title .tl1,{S} .hook .hk-row:first-child,{S} .quote .q-text{{font-weight:600}}
"""

    def bg(self, cx):
        return '<div class="zz-rule"></div>'

    def over(self, cx):
        p = self.pal(cx.spec)
        out, no = [], 0
        for i, sc in enumerate(cx.scenes):
            if i == cx.ec or cx.typ(i) == 'hook':
                continue
            no += 1
            lab = kind_label(cx.typ(i))
            out.append(clip('zz-kick', sc['_start'], sc['_end'] - sc['_start'], f'<b>№ {no:02d}</b>{lab}'))
        for i, _ in cx.bounds():
            if self.blocky(cx, i):
                out.append(f'<div class="zz-block" id="zzb{i}a" style="background:{p["ink"]}"></div>'
                           f'<div class="zz-block" id="zzb{i}b" style="background:{p["accent"]}"></div>')
        return ''.join(out)

    def scenes_html(self, cx, page):
        # 翻页推移：旧场景多留 PUSH_D 秒（和新场景重叠），推移中两版同时在画面里
        ext = {i - 1 for i, _ in cx.bounds() if not self.blocky(cx, i)}

        def fn(m):
            i = int(m.group(1))
            d = float(m.group(3)) + (self.PUSH_D + .02 if i in ext else 0)
            return f'<div id="s{i}" class="clip scene" data-start="{m.group(2)}" data-duration="{d:.3f}"'
        out, n = RX['scene_div'].subn(fn, page)
        if not n:
            warn('场景 clip 写法变了，翻页推移的重叠没加上')
        return out

    def js(self, cx, js):
        p = self.pal(cx.spec)
        acc = []
        js = sub(RX['push'], '', js, '整场慢推')
        js = sub(RX['punch_in'], '', js, '关键词推近', expect=bool(cx.punches))
        js = sub(RX['punch_out'], '', js, '关键词回位', expect=bool(cx.punches))
        # 荧光笔：逐字跟着念到的位置铺开
        js = sub(RX['cap_pop'], lambda m: (f'tl.fromTo("#c{m.group(1)} em",{{backgroundSize:"0% 46%"}},'
                                            f'{{backgroundSize:"100% 46%",duration:.1,ease:"none",stagger:{m.group(2)}}},{m.group(3)});'),
                 js, '字幕划重点', expect=bool(cx.cap_em))
        # 浅底：highlight 场景的字原来从白变黑，改成一直是墨色
        js = js.replace('{color:"#ffffff"}', '{color:"%s"}' % p['ink']).replace('{color:"#111111"', '{color:"%s"' % p['ink'])
        P, D = self.PUSH, self.PUSH_D
        for i, T in cx.bounds():
            t = cx.typ(i)
            if self.blocky(cx, i):   # 色块翻页：墨色、强调色先后盖满，换场在盖住时发生，再往上揭开
                for k, c in enumerate('ab'):
                    acc.append(f'tl.fromTo("#zzb{i}{c}",{{y:1920}},{{y:0,duration:.22,ease:"power3.in",immediateRender:false}},{T - .28 + k * .06:.3f});')
                    acc.append(f'tl.fromTo("#zzb{i}{c}",{{y:0}},{{y:-1920,duration:.26,ease:"power3.out",immediateRender:false}},{T + .02 + k * .06:.3f});')
                if t != 'chapter':
                    js, had = drop_enter(js, i)
                    if had:
                        acc.append(f'tl.fromTo("#s{i} .inner",{{opacity:0,y:30}},{{opacity:1,y:0,duration:.45,ease:"power3.out"}},{T + .16:.3f});')
                continue
            js, _ = drop_enter(js, i)
            # 推移放在 .cam 上；推移期间给两个场景的 .stage 加一个只露正文区的窗口（眉题下沿 492 到字幕上沿 1240），
            # 移动中的字不会从标题、字幕、小人底下穿过去（00-必读 2.3.4 人物不能挡字）
            for k in (i, i - 1):
                acc.append(f'tl.set("#s{k} .stage",{{clipPath:"{WIN}"}},{T:.3f});tl.set("#s{k} .stage",{{clipPath:"none"}},{T + D + .01:.3f});')
            acc.append(f'tl.fromTo("#s{i} .cam",{{y:{P}}},{{y:0,duration:{D},ease:"power3.inOut"}},{T:.3f});')
            acc.append(f'tl.fromTo("#s{i - 1} .cam",{{y:0}},{{y:{-P},duration:{D},ease:"power3.inOut",immediateRender:false}},{T:.3f});')
        return js + '\n' + '\n'.join(acc)


STYLE = Zazhi()
