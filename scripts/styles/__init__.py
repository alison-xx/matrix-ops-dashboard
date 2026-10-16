#!/usr/bin/env python3
"""剪辑风格预设（10-16，可选）。

用户 10-16：「剪辑风格可以再丰富一下，目前剪辑风格太单调了」。make_motion 默认只有一套：深色底 + 黄色强调 + 同一套入场。
这里给出可选的风格包，**spec 顶层写 "style": "<名字>" 才生效；不写 = make_motion 默认效果，输出的 index.html 一个字节都不变**。

  kuaijie  快节奏卡点   黑底信号红；横向甩切（cut-the-curve）+ 速度线；每句一次跳切推拉；关键词震屏；场景序号和进度刻度
  zazhi    杂志编辑     米白纸底深藏青墨色 + 珊瑚橙；纵向翻页推移；话题切换色块翻页；荧光笔划重点字幕；章节编号眉题
  jishi    纪实实拍     炭灰绿底 + 钨丝橙；取景框 + REC 时间码；对焦拉入 + 眨眼黑场；截图前快门；手持微晃；纪录片字幕条
  huazi    轻综艺花字   夜蓝波点底 + 糖果色；描边花字标题/字幕；弹入转场；泡泡转场；关键词彩纸
  auto     按账号和栏目挑（10-16 16:15 用户「用，你看着来」后定）：
             Office 号（account=office）→ zazhi（Office 奶白/墨绿/橙，和她的浅色封面同色）
             示例作者号：热点→kuaijie，先试→jishi，抄作业→huazi；算账、周报、人设系列等其余栏目 → 默认效果（不加风格）
           杂志风是浅色底，只给 Office 号用：示例作者号视频封面一律夜蓝（封面规范.md），成片要和封面同色，所以示例作者号不用 zazhi。
  none     明确写「默认」（和不写 style 一样，输出一个字节都不变）

严肃话题（出事、坏消息）spec 顶层写 "serious": true：不用花字（auto 和明写 huazi 都会退回默认效果）。
示例作者号按栏目套风格目前是 A/B 实验 E005（config/experiments.json，分组看 playbook.py start）；Office 号固定 zazhi，不参加。
也可以写中文：快节奏/卡点、杂志、纪实、花字/综艺、自动、默认。

中文展示字体（10-16 用户同意下载，SIL OFL 开源，来源和许可证见 fonts/SOURCES.txt）：
  zazhi  标题、hook 大字、金句、章节名、片尾问题 → 思源宋体 Noto Serif SC SemiBold/Bold（大号数字仍是 EB Garamond）
  huazi  标题、hook 大字、金句、数字、字幕关键词 → 站酷快乐体 ZCOOL KuaiLe
  jishi  金句（我的判断）、引用、截图下的批注 → 霞鹜文楷 LXGW WenKai Medium
  正文字幕、清单条目、对比条目一律仍是思源黑体（NS），保证看得清。
渲染时按本条页面里出现的字用 fontTools 子集化成 woff2（几百 KB），不往页面里塞几十 MB 的整套字体；
字体里没有的字浏览器自动退回思源黑体显示，不会变豆腐块（缺字会打印提示）。没装 fonttools 就整套复制（慢一点，提示安装）。

怎么接进 make_motion（改动只有两处，删掉就回到默认）：
  1. build() 读完 spec 后：style = styles.load(spec) ；style.prepare(spec)   —— 只补 theme 默认值、场景间停顿 pause_after 默认值
  2. 写 index.html 之前：page = style.apply(page, spec, work, lines, groups, total, has_av)
     —— 往页面里加 CSS、背景层、转场遮罩层，改写时间轴 JS（入场、转场、强调、字幕动效）。
风格只改画面，不改配音、配乐、音效（10-16 用户两次反馈回音/噪音，声音链路保持原样）。

实现约束（hyperframes-animation / faceless-explainer 的动效规范）：一条暂停的 GSAP 时间轴、全部 fromTo/set、
不用 Math.random / Date.now（伪随机用固定种子）、不用无限循环；人物和装饰不压字（00-必读 2.3.4）。
改写 JS 靠正则匹配 make_motion / edit_fx 生成的固定写法；匹配不到会打印「[风格] … 没匹配到」，那一项退回默认效果，不会出错。
"""
import hashlib, html, importlib, math, pathlib, re, shutil, sys

HERE = pathlib.Path(__file__).resolve().parent
FONTS = HERE / 'fonts'

ALIASES = {
    'kuaijie': 'kuaijie', '快节奏': 'kuaijie', '卡点': 'kuaijie', '快节奏卡点': 'kuaijie',
    'zazhi': 'zazhi', '杂志': 'zazhi', '杂志编辑': 'zazhi',
    'jishi': 'jishi', '纪实': 'jishi', '纪实实拍': 'jishi',
    'huazi': 'huazi', '花字': 'huazi', '综艺': 'huazi', '轻综艺花字': 'huazi',
}
NONE_NAMES = ('none', 'default', '默认', '无')
AUTO_OFFICE = 'zazhi'                                                  # Office 号所有视频固定杂志风（抖音-Office.md）
AUTO_CREATOR = {'热点': 'kuaijie', '先试': 'jishi', '抄作业': 'huazi'}   # 示例作者号；没列出的栏目（算账、周报、人设…）= 默认
NOT_SERIOUS = ('huazi',)   # 严肃话题（spec 写 "serious": true）不用的风格
TOPIC_TYPES = ('chapter', 'highlight', 'quote')   # 话题切换：用风格里更重的那种转场


def resolve(spec):
    """返回风格名；None = 默认效果（不加风格）。"""
    name = str(spec.get('style') or '').strip()
    acct = spec.get('account') or 'creator'
    if name in ('auto', '自动'):
        key = AUTO_OFFICE if acct == 'office' else AUTO_CREATOR.get(spec.get('column', ''))
        print(f'[风格] auto：{acct}·{spec.get("column", "无栏目")} → {key or "默认效果"}', file=sys.stderr)
    elif name in NONE_NAMES:
        key = None
    else:
        key = ALIASES.get(name)
        if not key:
            raise SystemExit(f'[风格] 没有「{name}」这个剪辑风格。可选：kuaijie(快节奏) / zazhi(杂志) / jishi(纪实) / huazi(花字) / auto / none')
    if key in NOT_SERIOUS and spec.get('serious'):
        warn('严肃话题（spec 写了 "serious": true）不用花字，改用默认效果')
        key = None
    if acct == 'office' and key != AUTO_OFFICE:
        warn(f'Office 号视频固定用 zazhi（平台打法/抖音-Office.md），这里是 {key or "默认"}，按 spec 照做')
    elif acct != 'office' and key == 'zazhi':
        warn('杂志风是浅色底，只给 Office 号用（示例作者号视频封面一律夜蓝，封面色要等于成片色，封面规范.md），按 spec 照做')
    return key


class _Default:
    """auto 选到「默认」或写了 none：什么都不改，输出和不写 style 一个字节都不差。"""
    name = ''

    def prepare(self, spec):
        pass

    def apply(self, page, *a, **k):
        return page


DEFAULT = _Default()


def load(spec):
    """spec 没写 style 返回 None（调用方据此完全走默认）；auto 选到默认 / 写 none 返回 DEFAULT（不改任何东西）。"""
    if not spec.get('style'):
        return None
    key = resolve(spec)
    if key is None:
        return DEFAULT
    return importlib.import_module(f'styles.{key}').STYLE


def warn(msg):
    print(f'[风格] {msg}', file=sys.stderr)


# ---- 中文展示字体：按本条页面用到的字子集化 ----
EXTRA_CHARS = ''.join(chr(c) for c in range(0x20, 0x7F)) + '，。、！？：；“”‘’（）《》【】「」『』—…·％＋－～×÷'


def _is_cjk(c):
    o = ord(c)
    return 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF


def subset_fonts(page, work, faces):
    """faces：((family, 字体文件, weight, 中文名), ...)。返回 @font-face CSS。
    字集 = 整个页面出现过的字符（含 CSS/JS 里的，取超集最保险）+ ASCII + 常用全角标点；
    同一个工作目录、同样的字集不重复子集化（.sig 记签名）。"""
    dst = pathlib.Path(work) / 'assets/fonts'
    dst.mkdir(parents=True, exist_ok=True)
    chars = ''.join(sorted(set(html.unescape(page)) | set(EXTRA_CHARS)))
    chars = ''.join(c for c in chars if c >= ' ')
    try:
        from fontTools import subset as fts
    except ImportError:
        fts = None
        warn('没装 fonttools，中文展示字体整套复制进页面（每个十几到二十几 MB，渲染慢）：.venv/bin/pip install fonttools brotli')
    css = []
    for fam, fname, weight, label in faces:
        src = FONTS / fname
        if not src.exists():
            warn(f'缺字体文件 {src}，{label}退回思源黑体')
            continue
        if fts is None:
            out = dst / fname
            if not out.exists():
                shutil.copy(src, out)
        else:
            out = dst / f'{src.stem}-sub.woff2'
            sig = hashlib.md5(f'{fname}|{src.stat().st_size}|{chars}'.encode()).hexdigest()
            sigf = dst / f'{src.stem}-sub.sig'
            if not (out.exists() and sigf.exists() and sigf.read_text() == sig):
                opts = fts.Options()
                opts.flavor = 'woff2'
                opts.hinting = False
                opts.desubroutinize = True
                font = fts.load_font(str(src), opts)
                cmap = font.getBestCmap()
                miss = [c for c in chars if _is_cjk(c) and ord(c) not in cmap]
                if miss:
                    warn(f'{label}缺 {len(miss)} 个字（这些字自动用思源黑体显示，不会变豆腐块）：{"".join(miss[:30])}')
                sub = fts.Subsetter(opts)
                sub.populate(text=chars)
                sub.subset(font)
                fts.save_font(font, str(out), opts)
                sigf.write_text(sig)
        css.append(f'@font-face{{font-family:{fam};src:url("assets/fonts/{out.name}");font-weight:{weight};font-display:block}}')
    return '\n'.join(css) + '\n'


# ---- make_motion / edit_fx 生成的固定写法（改写时间轴靠它们；对应的源码改了格式，这里要跟着改） ----
RX = {
    # scene_js：普通场景入场（chapter 和第 1 个场景没有这一行）
    'enter': re.compile(r'tl\.fromTo\("#s(\d+) \.inner",\{opacity:0,y:24\},\{opacity:1,y:0,duration:\.35,ease:"expo\.out"\},([\d.]+)\);'),
    # scene_js：整个场景极轻的推近
    'push': re.compile(r'tl\.fromTo\("#s(\d+) \.stage",\{scale:1\},\{scale:1\.03,duration:([\d.]+),ease:"none"\},([\d.]+)\);'),
    # edit_fx.punch_js：念到 **关键词** 镜头推近 / 回位
    'punch_in': re.compile(r'tl\.to\("#s(\d+) \.cam",\{scale:1\.1,duration:\.2,ease:"power3\.out"\},([\d.]+)\);'),
    'punch_out': re.compile(r'tl\.to\("#s(\d+) \.cam",\{scale:1,duration:\.5,ease:"power2\.inOut"\},([\d.]+)\);'),
    # edit_fx.caption_pop：字幕黄字被念到时弹一下
    'cap_pop': re.compile(r'tl\.fromTo\("#c(\d+) em",\{scale:1\},\{scale:1\.15,duration:\.1,yoyo:true,repeat:1,ease:"power2\.out",stagger:([\d.]+)\},([\d.]+)\);'),
    # make_motion.build：字幕组入场
    'cap_in': re.compile(r'tl\.fromTo\("#c(\d+) \.capin",\{opacity:0,y:12\},\{opacity:1,y:0,duration:\.18,ease:"power3\.out"\},([\d.]+)\);'),
    # 场景 clip 的开头
    'scene_div': re.compile(r'<div id="s(\d+)" class="clip scene" data-start="([\d.]+)" data-duration="([\d.]+)"'),
}


class Ctx:
    """apply() 时能用到的信息：场景时间（J-cut 之后的真实 data-start）、字幕组、关键词时刻。"""

    def __init__(self, spec, work, lines, groups, total, has_av, js):
        self.spec, self.work, self.lines, self.groups, self.total, self.has_av = spec, work, lines, groups, total, has_av
        self.scenes = spec['scenes']
        self.n = len(self.scenes)
        last = self.scenes[-1]
        self.ec = self.n - 1 if last.get('type') in ('cta', 'endcard') else None     # 片尾模板场景序号
        self.ec_at = last['_start'] if self.ec is not None else None
        self.t0 = self.scenes[0]['_end'] if self.scenes[0].get('type') == 'hook' else 0.0   # 顶部标题出现的时刻
        self.punches = [(int(m.group(1)), float(m.group(2))) for m in RX['punch_in'].finditer(js)]
        self.cap_em = []    # (字幕组 k, 第一个高亮字被念到的时刻, 每字间隔)
        for k, g in enumerate(groups):
            toks = re.findall(r'<span class="k">(.*?)</span>', g['html'])
            idx = [j for j, tk in enumerate(toks) if tk.startswith('<em>')]
            if idx:
                per = g['dur'] * .8 / max(g['n'], 1)
                self.cap_em.append((k, g['start'] + per * idx[0], per))

    def typ(self, i):
        return self.scenes[i].get('type', 'image')

    def bounds(self):
        """每个换场：(新场景序号 i, 换场时刻 T)。"""
        return [(i, self.scenes[i]['_start']) for i in range(1, self.n)]

    def line_starts(self, i):
        return [st for st, _ in self.scenes[i].get('_lines', [])]


def lcg(seed):
    """确定性伪随机（渲染逐帧截图，不能用 Math.random）。"""
    x = seed & 0x7fffffff
    while True:
        x = (x * 1103515245 + 12345) & 0x7fffffff
        yield x / 0x7fffffff


class Style:
    name = ''
    title = ''
    theme = {}
    pause = None        # 场景说完停多久的默认值（场景自己写了 pause_after 不动）
    hook_pause = None
    fonts = ()      # 小号西文字体（woff2，整份复制）
    cjk = ()        # 中文展示字体 ((family, 文件, weight, 中文名), ...)：渲染时按本条用到的字子集化

    def prepare(self, spec):
        """配音合成之前调用：补 theme、停顿默认值。不改口播文字、语速、音色（TTS 缓存照样命中）。"""
        spec['theme'] = {**self.theme_for(spec), **spec.get('theme', {})}
        for sc in spec['scenes']:
            if 'pause_after' in sc:
                continue
            p = self.hook_pause if sc.get('type') == 'hook' else self.pause
            if p is not None:
                sc['pause_after'] = p
        spec['_style'] = self.name

    def theme_for(self, spec):
        return dict(self.theme)

    # 子类覆盖这些
    def css(self, cx):
        return ''

    def bg(self, cx):          # 背景装饰层：在场景下面
        return ''

    def over(self, cx):        # 转场遮罩/取景框等：在场景上面、标题/小人/字幕下面
        return ''

    def top(self, cx):         # 最上层（进度条上面）
        return ''

    def js(self, cx, js):      # 改写/追加时间轴
        return js

    def scenes_html(self, cx, page):
        return page

    # ---- 通用 ----
    def apply(self, page, spec, work, lines, groups, total, has_av):
        m = re.search(r'var tl=gsap\.timeline\(\{paused:true\}\);(.*)window\.__timelines\["main"\]=tl;', page, re.S)
        if not m:
            warn('页面里找不到时间轴脚本，风格没生效（make_motion 模板可能改了）')
            return page
        cx = Ctx(spec, work, lines, groups, total, has_av, m.group(1))
        if self.fonts:
            dst = pathlib.Path(work) / 'assets/fonts'
            dst.mkdir(parents=True, exist_ok=True)
            for f in self.fonts:
                if not (dst / f).exists():
                    shutil.copy(FONTS / f, dst / f)
        new_js = self.js(cx, m.group(1))
        page = page[:m.start(1)] + new_js + '\n' + page[m.end(1):]
        page = self.scenes_html(cx, page)
        page = _ins(page, '</style>', self.css(cx), before=True, what='CSS')
        page = _ins(page, '<div id="root" class="', f'st-{self.name} ', what='根节点 class')
        page = _ins(page, '<div class="grid"></div>', self.bg(cx), what='背景层')
        page = _ins(page, '<div class="brand">', self.over(cx), before=True, what='遮罩层')
        page = _ins(page, '<audio id="narration"', self.top(cx), before=True, what='顶层')
        if self.cjk:   # 最后做：字集要包含风格自己加进去的字（眉题、序号等）
            page = _ins(page, '</style>', subset_fonts(page, work, self.cjk), before=True, what='中文字体')
        return page


def _ins(page, anchor, text, before=False, what=''):
    if not text:
        return page
    k = page.find(anchor)
    if k < 0:
        warn(f'找不到「{anchor}」，{what}没加上')
        return page
    if before:
        return page[:k] + text + page[k:]
    return page[:k + len(anchor)] + text + page[k + len(anchor):]


def sub(rx, fn, js, label, expect=True):
    """按正则改写时间轴；一处都没匹配到时提示（那一项退回默认效果）。"""
    out, n = rx.subn(fn, js)
    if expect and not n:
        warn(f'{label}：没匹配到 make_motion 的原始写法，这一项保持默认')
    return out


def drop_enter(js, i):
    """去掉第 i 个场景的默认入场（换成风格自己的）。返回 (新 js, 是否找到)。"""
    pat = re.compile(r'tl\.fromTo\("#s%d \.inner",\{opacity:0,y:24\},\{opacity:1,y:0,duration:\.35,ease:"expo\.out"\},[\d.]+\);' % i)
    out, n = pat.subn('', js)
    return out, bool(n)


def clip(cls, start, dur, inner, track=7, extra=''):
    """一个跟着时间轴出现/消失的元素（HyperFrames clip：visibility 由 data-start/duration 管）。"""
    return (f'<div class="clip {cls}" data-start="{max(start, 0):.3f}" data-duration="{max(dur, .05):.3f}" '
            f'data-track-index="{track}"{extra}>{inner}</div>')


def kind_label(t):
    return {'hook': '开篇', 'stat': '数据', 'bars': '数据', 'progress': '数据', 'list': '清单', 'compare': '对比', 'split': '对比',
            'highlight': '观点', 'quote': '观点', 'screen': '证据', 'chat': '实测', 'timeline': '时间线', 'chapter': '章节',
            'image': '现场'}.get(t, '')
