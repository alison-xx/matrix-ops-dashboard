#!/usr/bin/env python3
"""动效口播视频：spec.json -> 配音 + HyperFrames(HTML+GSAP) 动画 -> mp4 + 封面。

场景类型（scene.type）：
  hook     开场大字：big(用\\n分行，**词** 标黄)、sub(黄色胶囊)。放在第 1 个场景时，第 0 帧大字就满屏（不淡入，只有一下轻微收缩），
           顶部 title_top 在 hook 期间隐藏、hook 结束才出现；sub 在第 2 句（只有 1 句时 0.7 秒）弹出
  stat     数字滚动：value(数字)、prefix、suffix、label、decimals
  list     清单逐条飞入：heading、items[]
  compare  左右对比卡：left{title,items[],good}, right{...}
  timeline 时间轴：points[{t,label}]、center(中间大字，可选)
  image    配图运镜+扫光：image 或 prompt、headline
  quote    金句打字机：text、by(可选)
  cta      结尾互动：text、hint
  chat     AI 对话实测：model(模型名)、ask(提问)、reply(AI 回答原文摘录，≤90字)、verdict(可选印章，如"能用"/"翻车")、good(印章颜色)
  chapter  章节卡（长视频分段用）：n(第几步/第几点)、title、sub(可选)
  bars     条形对比/排行：heading、items[{label,value,display(可选显示文字)}]、unit、best(高亮第几项，从0起，可选)
  screen   真实截图（实测时截的软件界面）：image(路径)、focus[x,y,w,h](0-1 比例，推近+黄框高亮，可选)、step(如"第2步")、caption
  ---- 10-16 新增（动效移植自 HyperFrames 官方 registry，全部本地 GSAP + 内联 SVG/CSS，不联网）----
  highlight 关键词马克笔划重点（registry: marker-highlight）：一句大字先上屏，念到关键词时一笔划过去。
           text(大字，\\n 分行，每行 ≤8 字最好看)、em(要划的词，必须原样出现在 text 的某一行里)、
           mark(highlight 荧光笔底色[默认] / circle 圈出来 / underline 下划线 / scribble 涂掉，适合"错误说法")、
           label(大字上方的小标签，如"我的判断"，可选)、sub(下方补一句，可选)、
           at(第几句口播时开始划，从 0 起；不写就自动找口播里念到 em 的位置)
           例：{"type":"highlight","label":"我的判断","text":"付钱的人要的是\\n一件能交差的活","em":"能交差","lines":[...]}
  progress 占比/进度（registry: mk-progress-stat + conic-progress-ring）：大数字计数，进度条（或圆环）同一条缓动一起涨到 value/max。
           value、max(默认 100)、prefix、suffix(max=100 时默认 "%")、decimals、label(下方说明，**词** 标黄)、caption(灰色小字，可选)、
           style(bar 横条[默认] / ring 圆环)、at(第几句口播时开始涨，默认场景开头)
           例：{"type":"progress","value":84,"label":"两个专家挣走的份额","caption":"标书 2573 元 + 财务分析 2319 元","lines":[...]}
  split    改前/改后分屏擦除（registry: before-after-wipe）：左半边"改前"灰着先出现，念到 at 那句时一条竖线从右往左擦出亮色的"改后"，停在中间对比。
           before{tag,value,note}、after{tag,value,note}：tag 小标签(默认 改前/改后)、value 大字(数字/短词，≤5 字)、note 一行小字(可用 **词**)；
           heading(上方标题，可选)、at(第几句擦出"改后"，默认最后一句)
           例：{"type":"split","before":{"tag":"免费6周","value":"0元","note":"上架若干项"},"after":{"tag":"收费4天","value":"1234元","note":"**若干人**付钱"},"lines":[...]}
每个场景都有 lines[]（口播句子，字幕自动同步；**词** 会在字幕里标黄）。

开头 15 秒留存结构（10-16，依据 10-15 抖音数据：2 秒跳出 25–40%、平均只看 6 秒）：
  0–2 秒钩子：第 1 个场景必须是 hook，第一句 ≤16 字、2 秒内念完，说的就是大字那句结论/冲突；
  2–5 秒确认：hook 第 2 句或第 2 个场景给证据/跟你有什么关系（截图、数字、点名受众），hook 整段 ≤4 秒；
  5–15 秒兑现：第一条干货最迟第 15 秒出现（数据、结论、第一个步骤），背景铺垫往后放；之后每 8–10 秒一个新信息点。
  渲染前自动「开头体检」+「节奏体检」（只打印警告，不阻断）：第 1 个场景不是 hook、hook 第一句 >16 字、
  配音后第一句 >2 秒、hook 场景 >4 秒、任一场景口播 >4 句。只想先查稿子不合成配音：加 --check。
  hook 场景想念快一点可以单独写 "rate": "+15%"。
顶层：id, account(creator/office，决定角标品牌和封面配色), cover_wide(true=另出 B站 16:9 横版封面 <id>-cover-wide.jpg，可配 cover_title_wide), title_top(两行,\\n分隔), title_highlight, brand, column(先试/算账/抄作业/热点/办公课 -> 右上角栏目角标), tag(覆盖角标文字), voice, rate, theme{bg1,bg2,accent,accent2}
封面（作图 API 一体设计，v4 起主角是示例作者动漫形象，规范见 运营手册/封面规范.md）：cover_title（两行，\\n 分隔，每行≤7字，第二行=反差/结论）、
  cover_subject（示例作者身边的道具/场景：一两个具体物件，不写机器人、不要真实品牌 logo/真人明星）、cover_pose（可选，示例作者的表情动作，不写按内容给默认）、
  cover_theme（可选，夜蓝/明黄/米白/雾蓝，不写按内容自动挑）、series（如"第3集"）、cover_attempt（错字重画时 +1）。
  输出 <id>-cover.jpg（9:16，设计完整落在主页 3:4 安全区）和 <id>-cover-34.jpg（3:4，小红书视频用）。
v2（10-16）新增：
  顶层 bgm（放松/欢快/悬疑/震撼/大气/幽默/none，默认按栏目）、bgm_volume（默认 1）、rate（默认 +3%）、hook_type（钩子类型，记录用）、ghost（背景大字）
  场景 pause_after（这个场景说完停多久，默认 0.35，hook 0.2）、reveal（list/bars/timeline 第 k 条跟第几句出现）、sfx（false 关掉换场音效）
  口播稿怎么写见 运营手册/口播稿规则.md；lint 会查。
剪辑风格（10-16，可选）：顶层 "style": kuaijie 快节奏卡点 / zazhi 杂志编辑 / jishi 纪实实拍 / huazi 轻综艺花字 / auto 按栏目挑；
  不写 = 默认效果完全不变。只改画面（配色、入场、转场、强调、字幕样式、停顿），不动配音配乐音效。说明见 scripts/styles/__init__.py。
用法: .venv/bin/python scripts/make_motion.py <spec.json> [--draft] [--no-render] [--check]
"""
import html, json, math, os, pathlib, re, shutil, subprocess, sys, unicodedata
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, gen_image, tts, probe_duration

HF_VERSION = '0.8.162'
TPL = ROOT / 'templates/hf/assets'
STYLE_IMG = 'editorial illustration, cinematic lighting, rich color, high detail, clean composition, vertical, no text, no letters, no watermark, no logo'


def esc(s):
    return html.escape(str(s), quote=True)


def mark(s):
    """**词** -> 高亮；\n -> 换行"""
    return re.sub(r'\*\*(.+?)\*\*', r'<em>\1</em>', esc(s)).replace('\n', '<br>')


def _units(s):
    return sum(0.55 if c.isascii() else 1 for c in plain(s))


def cap_mark(s, max_units=14):
    """字幕：优先在逗号/句号处断行——短分句包成不可拆的块，避免「的，」这类孤字。"""
    parts = re.findall(r'[^，。？！；：,?!;]+[，。？！；：,?!;]*', s)
    if len(parts) < 2 or any(p.count('**') % 2 for p in parts):
        return _keep_nums(mark(s))
    return ''.join(f'<span class="cl">{mark(p)}</span>' if _units(p) <= max_units else _keep_nums(mark(p)) for p in parts)


NUM_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9.:%/]*(?:小时|分钟|[年月日号天次个万亿元岁点分秒])?(?:[0-9]+[日号点分])?')


def _keep_nums(html):
    """长分句内部：把「10月8号」「7天」「GPT-5」这类数字/英文词包成不可拆的块（只处理标签外文字）。"""
    return ''.join(seg if seg.startswith('<') else NUM_RE.sub(lambda m: f'<span class="cl">{m.group(0)}</span>', seg)
                   for seg in re.split(r'(<[^>]+>)', html))


def plain(s):
    """去掉 **高亮** 和 [停0.6] 停顿标记，得到要念出来/算字数的纯文字。"""
    return re.sub(r'\[停\s*[\d.]+\s*秒?\]', '', re.sub(r'\*\*(.+?)\*\*', r'\1', s))


CAP_PUNCT = set('，。？！；：、,.?!;:…')


def _cap_tokens(text):
    """把一句字幕拆成 token：(文字, 是否高亮, 是否标点)。英文/数字连写的词算一个 token，不拆开。"""
    toks, bold = [], False
    for part in re.split(r'(\*\*)', text):
        if part == '**':
            bold = not bold
            continue
        for m in re.finditer(r'[A-Za-z0-9][A-Za-z0-9.:%/+\-]*|.', part):
            c = m.group(0)
            if not c.isspace():
                toks.append((c, bold, c in CAP_PUNCT))
    return toks


CAP_HARD = set('，。？！；：,.?!;:')
CAP_WORDS = ['状态页', '大模型', '开放平台', '提示词', '备忘录', '赠金', '服务承诺', '口播', '自媒体', '智能体', '工作流',
             'DeepSeek', 'ChatGPT', 'Claude', '豆包', '元宝', '通义', '千问', '可灵', '即梦', '剪映', '公众号', '视频号', '小红书']
# 断在这些词后面，下一组开头会接不上（介词/连词/副词/指示词要和后面的词待在一起）
CAP_BIND_NEXT = set('和 与 跟 及 或 把 被 在 对 给 从 向 按 到 这 那 每 第 让 将 比 为 很 最 更 太 不 没 本来 已经 终于 其实 一直 正在 '
                    '可能 也许 马上 直接 只要 只有 如果 因为 所以 但是 而且 虽然 不过 然后 还是 就是 这个 那个 这些 那些'.split())
# 断在这些词前面，下一组会以虚词开头（的/了/吗、方位词、量词应该留在上一组末尾）
CAP_BIND_PREV = set('的 了 着 过 吗 呢 吧 啊 呀 嘛 上 里 中 下 们 得 地 次 个 天 号 月 点 分 秒 年 岁 倍 万 亿 元 块 家 条 % 页'.split())
CAP_PRON = set('你 我 他 她 它 你们 我们 他们 她们 它们 大家 自己'.split())
_JIEBA = None


def _cap_bounds(text):
    """结巴分词（带词性）：返回 {词边界偏移: (左词, 左词性, 右词, 右词性)}。字幕只在词边界断开，不把「公司」拆成「公|司」。"""
    global _JIEBA
    if _JIEBA is None:
        import jieba, jieba.posseg
        jieba.setLogLevel(60)
        for w in CAP_WORDS:
            jieba.add_word(w)
        _JIEBA = jieba.posseg
    segs = [(p.word, p.flag) for p in _JIEBA.cut(text)]
    out, i = {}, 0
    for k, (w, f) in enumerate(segs):
        i += len(w)
        out[i] = (w, f, *(segs[k + 1] if k + 1 < len(segs) else ('', '')), segs[k - 1][1] if k else '')
    return out


def _cap_w(tk):
    return 0 if tk[2] else (0.55 * len(tk[0]) if tk[0].isascii() else 1)


def _cap_cut_cost(info):
    """在一个词边界断开的代价：0 = 好断点，越大越别断，1000 = 不能断。"""
    if not info:
        return 1000
    L, lf, R, rf, pf = info
    if not R:
        return 0
    if (L[-1:].isdigit() or L == '第') and (R[0].isdigit() or R[0] in CAP_BIND_PREV):
        return 1000          # 10月 / 8点11分 / 第18次 不拆
    c = 0
    if L in ('、', ',', '，'):
        c -= 4
    if L in CAP_BIND_NEXT or lf[:1] in ('p', 'c', 'd'):
        c += 12
    if R in CAP_BIND_PREV or rf[:1] in ('u', 'y', 'f', 'q', 'k'):
        c += 12
    if L in CAP_PRON and pf[:1] in ('v', 'p'):
        c += 10              # 帮你|办事：宾语代词跟着前面的动词，后面也别断开
    if len(L) == 1 and lf[:1] == 'v':
        c += 6               # 单字动词别落在组尾（帮|你办事）
    return c


def _cap_split(toks, bounds, offs, max_units):
    """一个分句（不含中间的硬标点）超过 max_units 时，用 DP 选断点：每组尽量等长、只断在词边界、虚词不落单。"""
    n = len(toks)
    w = [_cap_w(t) for t in toks]
    pre = [0]
    for x in w:
        pre.append(pre[-1] + x)
    total = pre[-1]
    if total <= max_units:
        return [toks]
    cost_at = [0] + [_cap_cut_cost(bounds.get(offs[j])) for j in range(1, n)] + [0]
    best = None
    k0 = int(-(-total // max_units))
    for k in (k0, k0 + 1):
        target = total / k
        INF = float('inf')
        dp = [[INF] * (n + 1) for _ in range(k + 1)]
        bk = [[0] * (n + 1) for _ in range(k + 1)]
        dp[0][0] = 0
        for g in range(1, k + 1):
            for j in range(1, n + 1):
                for i in range(g - 1, j):
                    if dp[g - 1][i] == INF:
                        continue
                    u = pre[j] - pre[i]
                    if u > max_units or u < 2.5:
                        continue
                    c = dp[g - 1][i] + (u - target) ** 2 + cost_at[j]
                    if c < dp[g][j]:
                        dp[g][j], bk[g][j] = c, i
        if dp[k][n] < INF:
            cost = dp[k][n] + 8 * (k - 1)
            if best is None or cost < best[0]:
                cuts, j = [], n
                for g in range(k, 0, -1):
                    cuts.append(j); j = bk[g][j]
                best = (cost, sorted(cuts))
    if not best:   # 实在找不到（极长的英文串等）：退回按字数硬切
        out, cur, u = [], [], 0
        for tk, x in zip(toks, w):
            if cur and u + x > max_units:
                out.append(cur); cur, u = [], 0
            cur.append(tk); u += x
        return out + [cur] if cur else out
    out, i = [], 0
    for j in best[1]:
        out.append(toks[i:j]); i = j
    return out


def cap_groups(lines, max_units=12, sil=None):
    """字幕分组（v3，10-16）：一句口播拆成 ≤12 字一组，一次只显示一组；组尾的逗号句号不显示（问号叹号保留）。
    v2 按字数硬切，会把「公司」切成「…开发者和公|司」。现在先按标点分句，太短的分句并到相邻句，
    太长的分句用结巴分词 + DP 在词边界上均分（介词连词不落在组尾，的/了/吗 不落在组头，数字和单位不拆开）。
    每组按朗读权重分配这句话的时长；传了 sil（配音里的静音段）时，组和组的切换点吸附到逗号处的真实换气上。"""
    out = []
    for ln in lines:
        toks = _cap_tokens(ln['text'])
        text = ''.join(t[0] for t in toks)
        bounds = _cap_bounds(text)
        offs, o = [], 0
        for t in toks:
            offs.append(o); o += len(t[0])
        offs.append(o)
        # 1) 按硬标点分句（标点跟在句尾）
        clauses, cur = [], []
        for k, tk in enumerate(toks):
            cur.append(k)
            if tk[2] and tk[0] in CAP_HARD:
                clauses.append(cur); cur = []
        if cur:
            clauses.append(cur)
        units = lambda c: sum(_cap_w(toks[k]) for k in c)
        # 2) 太短的分句（≤3 字）并到前一句或后一句，别让两三个字单独闪一下
        merged = []
        for c in clauses:
            if merged and (units(c) <= 3 or units(merged[-1]) <= 3) and units(merged[-1]) + units(c) <= max_units:
                merged[-1] = merged[-1] + c
            else:
                merged.append(c)
        # 3) 太长的分句在词边界上均分
        groups = []
        for c in merged:
            body = [k for k in c]
            while body and toks[body[-1]][2] and toks[body[-1]][0] in CAP_HARD:
                body.pop()
            tail = c[len(body):]
            parts = _cap_split([toks[k] for k in body], bounds, [offs[k] for k in body] + [offs[body[-1] + 1] if body else 0], max_units) if body else [[]]
            parts[-1] = parts[-1] + [toks[k] for k in tail]
            groups += [p for p in parts if p]
        ws = [max(_speech_w(''.join(t[0] for t in g)), .5) for g in groups]
        tot = sum(ws)
        cuts, acc = [ln['start']], 0
        for w in ws[:-1]:
            acc += w
            b = ln['start'] + ln['dur'] * acc / tot
            near = [(a, z) for a, z in (sil or []) if abs((a + z) / 2 - b) < 0.45 and ln['start'] + 0.3 < a and z < ln['start'] + ln['dur'] - 0.2]
            if near:   # 下一组在说话重新开始前 80ms 出现
                a, z = min(near, key=lambda q: abs((q[0] + q[1]) / 2 - b))
                b = max(a, z - 0.08)
            cuts.append(max(b, cuts[-1] + 0.25))
        cuts.append(ln['start'] + ln['dur'])
        for gi, g in enumerate(groups):
            while g and g[-1][2] and g[-1][0] not in '？！?!':
                g = g[:-1]
            t0, dur = cuts[gi], max(cuts[gi + 1] - cuts[gi], 0.2)
            g = [('\u2002', b, p) if p and c in CAP_HARD and c not in '？！?!' else (c, b, p) for c, b, p in g]   # 组内的逗号显示成空格
            html_ = ''.join(f'<span class="k">{"<em>" if b else ""}{esc(c)}{"</em>" if b else ""}</span>' for c, b, _ in g)
            out.append({'start': round(t0, 3), 'dur': round(dur, 3), 'html': html_, 'n': len(g)})
    return out


SFX_DIR = TPL / 'sfx'   # Pixabay 授权音效（来自 media-use skill，可商用免署名，见 CREDITS.md）
SFX_GAIN = 0.75   # 音效整体音量系数（10-16 压低）
SFX_DRY = {'impact-bass-1': 'impact-bass-1-dry', 'impact-bass-2': 'impact-bass-2-dry', 'ping': 'ping-dry', 'chime': 'chime-dry'}   # 长拖尾 -> 截短淡出版


def sfx_tags(spec):
    """音效（v2，10-16）：旧版每个场景一声白噪声「嗖」+ 正弦「哔」，玩具感重。现在用授权音效库，只在关键拍上响：
    换场景 whoosh（两种轮换）、数字/条形落定 ping、列表逐条 click-soft、印章 impact、打字 typing、开头大字 impact。
    音量 0.2–0.35，压在人声和 BGM 下面。
    10-16（用户：有回音）：低音冲击/叮这类带 2 秒以上长拖尾的音效换成截短淡出的 *-dry 版，整体再乘 SFX_GAIN 压低一点。"""
    tags, n = [], 0

    def add(name, at, vol, dur=None):
        nonlocal n
        name = SFX_DRY.get(name, name)
        vol = round(vol * SFX_GAIN, 3)
        f = SFX_DIR / f'{name}.mp3'
        d = dur or probe_duration(f)
        tags.append(f'<audio id="fx{n}" src="assets/sfx/{name}.mp3" data-start="{max(at, 0):.3f}" data-duration="{d:.3f}" data-volume="{vol}" data-track-index="{5 + n % 3}"></audio>')
        n += 1
    for i, sc in enumerate(spec['scenes']):
        t, s = sc.get('type', 'image'), sc['_start']
        if i > 0 and sc.get('sfx', True):
            add('whoosh-short' if i % 2 else 'whoosh', s - 0.12, 0.22)
        if t == 'hook':
            add('impact-bass-1', s + 0.12, 0.3)
        elif t == 'stat':
            add('ping', s + 0.25 + min(1.6, (sc['_end'] - s) * .5), 0.25)
        elif t in ('list', 'bars', 'timeline'):
            for b in sc.get('_beats', [])[:6]:
                add('click-soft', b, 0.22)
        elif t == 'chat':
            add('typing', s + 0.9, 0.18)
            if sc.get('verdict'):
                add('impact-bass-2' if sc.get('good', True) else 'error', sc.get('_stamp_at', sc['_end'] - 1), 0.25)
        elif t == 'chapter':
            add('ping', s + 0.05, 0.2)
        elif t == 'highlight' and sc.get('_cue'):
            add('pop', sc['_cue'] + 0.4, 0.22)
        elif t == 'progress' and sc.get('_cue'):
            add('ping', sc['_cue'] - 0.1, 0.25)
        elif t == 'split' and sc.get('_cue'):
            add('whoosh-short', sc['_cue'], 0.2)
    return ''.join(tags)


PAUSE_W = {'，': 1.6, ',': 1.6, '、': 1.0, '：': 1.6, '；': 2.0, '。': 2.6, '？': 2.6, '！': 2.6, '?': 2.6, '!': 2.6, '…': 2.0}


def _speech_w(s):
    """估算一句话的朗读时长权重：汉字 1，英文字母/数字 0.55，标点按停顿折算。"""
    s = plain(s)
    return sum(PAUSE_W.get(c, 0.55 if c.isascii() and c.isalnum() else (0 if c.isspace() or c.isascii() else 1)) for c in s)


def _silences(path, noise='-35dB', d=0.1):
    r = subprocess.run(['ffmpeg', '-i', str(path), '-af', f'silencedetect=noise={noise}:d={d}', '-f', 'null', '-'], capture_output=True, text=True, errors='replace')
    st = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', r.stderr)]
    en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', r.stderr)]
    return list(zip(st, en))


def _split_lines(path, texts, dur):
    """整段配音里找每句话的边界：先按字数+标点估一个位置，再吸附到最近的停顿（静音段中点）。"""
    if len(texts) == 1:
        return [0.0, dur]
    w = [_speech_w(x) for x in texts]
    tot = sum(w) or 1
    sil = [((a + b) / 2, b - a) for a, b in _silences(path) if 0.2 < a < dur - 0.2]
    bounds, acc, lo = [0.0], 0, 0.0
    for x in w[:-1]:
        acc += x
        est = dur * acc / tot
        cand = [m for m, ln in sil if m > lo + 0.3 and abs(m - est) < max(0.9, dur * 0.12)]
        b = min(cand, key=lambda m: abs(m - est)) if cand else est
        bounds.append(b)
        lo = b
    bounds.append(dur)
    return bounds


def _tts_cached(text, voice, rate, cache_dir, instructions=None):
    import hashlib
    bl = str(voice).startswith('bailian-clone:')   # 百炼直连 10-16 起回 48kHz WAV、音量 30 防削波（旧缓存是 22kHz mp3 / 会削波，换 key 不复用）
    wav = bl or str(voice).startswith('bailian:')   # 晨煦（百炼 qwen3-tts）也存无损 WAV，不过 mp3
    h = hashlib.md5(f'{voice}|{rate}|{instructions or ""}|{text}{"|wav48v30" if bl else ""}'.encode()).hexdigest()[:16]
    f = cache_dir / (f'{h}.tts.wav' if wav else f'{h}.mp3')
    if not f.exists():
        tts(text, f, voice=voice, rate=rate, instructions=instructions)
    if str(voice).startswith('bailian:'):
        # 晨煦（qwen3-tts-flash）偶尔整句漏念（10-16 Office 第 0 课：75 字只念了 10 秒，成片识别只对上 72%），单独重合成又是完整的。
        # 按字数/时长判断：+8% 语速时正常 5.5–7.3 字/秒（数字、英文按字符算会偏高），整句漏念会跳到 9 以上。
        # 阈值随语速换算（+18% 的 hook 约 7.2 字/秒是正常的，10-16 样片曾被 6.6 的旧阈值误判、反复重合成把开头拖长），重合成最多 3 次，留最长的一版
        n = len(re.findall(r'[一-鿿0-9A-Za-z]', re.sub(r'<[^>]+>', '', text)))
        m = re.match(r'([+-]?\d+)%', str(rate or '0%'))
        limit = 7.8 * (1 + (int(m.group(1)) if m else 0) / 100) / 1.08
        best = probe_duration(f)
        for _ in range(3):
            if not n or n / max(best, .1) <= limit:
                break
            alt = f.with_name(f.stem.split('.')[0] + '.retry.tts.wav')
            d = tts(text, alt, voice=voice, rate=rate, instructions=instructions)
            if d > best:
                alt.replace(f)
                best = d
                for old in cache_dir.glob(f.name.split('.')[0] + '.clean*.wav'):   # 下游去静音缓存跟着作废
                    old.unlink()
            else:
                alt.unlink(missing_ok=True)
    return f


# 百炼复刻的语气指令（cosyvoice-v3.5，≤128 字）：统一底色 + 按场景类型加一句；场景可写 "tone" 覆盖
TONE_BASE = '你是一个爱分享的科技博主，用轻松自然、像跟朋友聊天的语气说。'
TONE_BY_TYPE = {
    'hook': '开头要抓人，语气带一点急切和惊讶，语速稍快。',
    'stat': '说到数字时清楚笃定，重音落在数字上。', 'bars': '说到数字时清楚笃定，重音落在数字上。',
    'compare': '对比的两边说清楚，后一边语气加重一点。', 'timeline': '像在讲一件刚发生的事，有画面感。',
    'quote': '这一句是观点，放慢一点，语气认真。', 'list': '像在给朋友支招，干脆利落。',
    'chat': '像边看边讲，带点好奇。', 'screen': '像边看边讲，带点好奇。', 'chapter': '换个话题，语气提起来。',
    'cta': '真诚一点，提问时语调上扬，像在等对方回答。', 'endcard': '真诚一点，提问时语调上扬，像在等对方回答。',
}


# 晨煦（bailian:Ethan，qwen3-tts-flash 不认语气指令）的情绪语调靠语速和标点调（10-16 用户：「给那个 tts 声音调好情绪语调」）：
# 在 spec 的 rate 上按场景类型加减；hook 句末改感叹、cta 提问保证问号，只改送去合成的文字，字幕不变。场景写 "rate" 就以场景为准。
RATE_DELTA_BY_TYPE = {'hook': 6, 'chapter': 3, 'list': 3, 'bars': 0, 'stat': 0, 'quote': -6, 'highlight': -6, 'cta': -4, 'endcard': -4}


def _pct(r):
    m = re.match(r'([+-]?\d+)%', str(r or '0%'))
    return int(m.group(1)) if m else 0


def qw_rate(sc, base):
    if sc.get('rate'):
        return sc['rate']
    return f"{_pct(base) + RATE_DELTA_BY_TYPE.get(sc.get('type', ''), 0):+d}%"


def qw_text(say, sc):
    t = sc.get('type', '')
    if t == 'hook':
        say = re.sub(r'。', '！', say)
    elif t in ('cta', 'endcard'):
        say = re.sub(r'(吗|呢|吧|么|哪件活|什么|怎么|多少|几)([，。])', r'\1？', say)
    return say


def scene_tone(sc):
    return (TONE_BASE + (sc.get('tone') or TONE_BY_TYPE.get(sc.get('type', 'image'), '')))[:128]


def _ssml_escape(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')


BGM_DIRS = {'放松': '放松_愉悦_轻快', '欢快': '快乐_欢快_庆祝', '悬疑': '暗黑类-悬疑的_恐怖的_紧张的', '震撼': '愤怒_震撼_史诗',
            '大气': '感受类-飞跃高空_梦境_领略', '幽默': '好玩的_幽默_乐趣', '伤感': '伤心_悲伤_难过_压抑'}
BGM_BY_COLUMN = {'热点': '放松', '先试': '欢快', '算账': '放松', '抄作业': '放松', '办公课': '放松'}
BGM_AVOID = re.compile(r'haunt|creepy|monster|dread|disturb|horror|zombie|ghost|恐怖|鬼|僵尸|惊悚|哭|葬', re.I)


def pick_bgm(spec):
    """从示例服务配乐库（/user/viral-video/music，1100+ 首无版权 BGM）按情绪挑一首；最近用过的 12 首不重复。
    spec 写 "bgm": "放松/欢快/悬疑/震撼/大气/幽默" 或具体曲目 id；"bgm": "none" 关掉。"""
    import hashlib, urllib.request, urllib.parse
    from common import env
    want = spec.get('bgm') or BGM_BY_COLUMN.get(spec.get('column', ''), '放松')
    if want in ('none', '无', False):
        return None
    lib_p = ROOT / 'state/bgm_library.json'
    if not lib_p.exists() or (lib_p.stat().st_mtime < __import__('time').time() - 7 * 86400):
        req = urllib.request.Request('https://api.example.com',
                                     headers={'Authorization': f"Bearer {env()['PROVIDER_USER_TOKEN']}", 'User-Agent': 'creator-ops/1.0'})
        lib_p.write_text(json.dumps(json.load(urllib.request.urlopen(req, timeout=30))['data']['items'], ensure_ascii=False))
    lib = json.loads(lib_p.read_text())
    pool = [x for x in lib if x['id'] == want] or [x for x in lib if BGM_DIRS.get(want, want) in urllib.parse.unquote(x['audioUrl'])
                                                   and not BGM_AVOID.search(x['name'])]
    if not pool:
        raise SystemExit(f'配乐库里没有「{want}」类的曲子')
    used_p = ROOT / 'state/bgm_used.json'
    used = json.loads(used_p.read_text()) if used_p.exists() else []
    fresh = [x for x in pool if x['id'] not in used] or pool
    pick = fresh[int(hashlib.md5(spec.get('id', '').encode()).hexdigest(), 16) % len(fresh)]
    used_p.write_text(json.dumps(([pick['id']] + [u for u in used if u != pick['id']])[:12]))
    f = ROOT / 'assets/bgm' / f"{pick['id']}.mp3"
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(pick['audioUrl'], f)
    return f, pick


def _bgm_offset(f, need):
    """BGM 别从第 0 秒硬放：很多曲子前几秒是铺垫或空白。找响度第一次稳定到中位数 -4 LU 以上的位置（取整到秒）。"""
    r = subprocess.run(['ffmpeg', '-i', str(f), '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True, errors='replace')
    ms = [(float(t), float(m)) for t, m in re.findall(r't:\s*([\d.]+)\s+TARGET.*?M:\s*(-?[\d.]+)', r.stderr)]
    if not ms:
        return 0.0
    dur = ms[-1][0]
    vals = sorted(m for _, m in ms if m > -70)
    if not vals or dur < need + 8:
        return 0.0
    med = vals[len(vals) // 2]
    for t, m in ms:
        if m >= med - 4 and t + need < dur:
            return float(int(t))
    return 0.0


PAUSE_MARK = re.compile(r'\[停\s*([\d.]+)\s*秒?\]')
# 人声处理（10-16，用户：声音别那么苍白）：播客式链路——低切去闷、200Hz 一点厚度、3kHz 一点清晰度、
# 8kHz 略压齿音，再轻压缩让音量稳、贴耳。TTS 原声偏干偏薄，这一步让它听起来像录出来的人声。
VOICE_CHAIN = ('highpass=f=70,equalizer=f=7200:t=q:w=1.2:g=-2,'   # 10-16 用户嫌有回音和瑕疵：去掉 3kHz 提亮和重压缩，只留低切、轻压齿音、温和压缩
               'acompressor=threshold=-26dB:ratio=1.6:attack=15:release=200:makeup=1.1')
SR = 48000    # 10-16：全链路 48kHz（旧版降到 24k 再升 44.1k，高频发闷、有毛刺）
TRIM = ('silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.04,afade=t=in:d=0.006,'
        'areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.04,afade=t=in:d=0.025,areverse')


def _lufs(path):
    """整段积分响度（LUFS），用 ebur128 测。"""
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af', 'ebur128=framelog=quiet', '-f', 'null', '-'],
                       capture_output=True, text=True, errors='replace')
    m = re.findall(r'I:\s+(-?[\d.]+) LUFS', r.stderr)
    return float(m[-1]) if m else -16.0


LEAD = 0.15   # 第一句前的空白（旧版 0.35s；开头要抢时间，0.15s 刚好盖住 hook 的 impact 音效起音）


def build_audio(spec, work):
    """配音 v2（10-16）：旧版逐句单独合成再用固定 0.12s 静音拼接，每句语调都从头起，听着像念稿机器。
    现在每个场景整段合成（一个场景 = 一口气说完的一段话），句子边界用静音检测找；场景之间留 0.35s 换气。
    再垫一首 BGM，配音出现时自动压低（sidechain ducking），最后整体响度归一到 -16 LUFS。"""
    # 配音音色以 config/schedule.json 的 voice_default 为准（10-16 中午起暂用 TTS「晨煦」bailian:Ethan，用户本人声音打磨好再换回）；旧稿子写的 provider:Ethan 一并替换
    default_voice = json.loads((ROOT / 'config/schedule.json').read_text()).get('voice_default', 'provider:Ethan')
    voice = spec.get('voice') or default_voice
    if voice == 'provider:Ethan':
        voice = default_voice
    for sc in spec['scenes']:
        if sc.get('voice') == 'provider:Ethan':
            sc['voice'] = default_voice
    rate = spec.get('rate', '+3%')   # +6% 实测约 5.8 字/秒偏快；系列长视频求听清，热点快评可在 spec 里调到 +6%
    cache = work / 'audio'
    cache.mkdir(parents=True, exist_ok=True)
    t, lines, parts = LEAD, [], []

    def silence(sec):
        f = cache / f'sil{int(sec * 1000)}-{SR}.wav'   # 文件名带采样率：10-16 旧缓存 24k 的静音混进 48k 拼接，整条旁白变两倍长、声音全乱
        if not f.exists():
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', f'anullsrc=r={SR}:cl=mono', '-t', f'{sec:.3f}', str(f)], check=True)
        return f
    parts.append(silence(LEAD))
    for si, sc in enumerate(spec['scenes']):
        sc['_start'] = t if si else 0.0
        # 刻意停顿：句尾写「[停0.6]」= 这句说完停 0.6 秒再接下一句（揭晓前屏息、反转前顿一下）。
        # 有停顿标记的地方断开分段合成，其余句子仍然整段一口气合成，语调连贯。
        holds = []
        for k, ln in enumerate(sc['lines']):
            m = PAUSE_MARK.search(ln)
            holds.append(float(m.group(1)) if m else 0.0)
            sc['lines'][k] = PAUSE_MARK.sub('', ln).rstrip()
        texts = [ln if re.search(r'[，。？！；：,.?!;…]$', plain(ln)) else ln + '，' for ln in sc['lines']]
        sv = sc.get('voice', voice)
        bl = str(sv).startswith('bailian-clone:')
        chunks, cur = [], []
        for k in range(len(texts)):
            cur.append(k)
            if holds[k] and k < len(texts) - 1 and not bl:   # 百炼直连用 SSML 停顿，不用断开分段
                chunks.append(cur); cur = []
        chunks.append(cur)
        segs = []
        for ch in chunks:
            if bl and any(holds[:-1]):
                say = '<speak>' + ''.join(_ssml_escape(plain(texts[k])) + (f'<break time="{int(holds[k] * 1000)}ms"/>' if holds[k] and k < len(texts) - 1 else '') for k in ch) + '</speak>'
            else:
                say = ''.join(plain(texts[k]) for k in ch)
            qw = str(sv).startswith('bailian:')
            if qw:   # 晨煦：按场景调语速和标点（情绪语调），指令版模型开通后 scene_tone 也会一起发
                mp3 = _tts_cached(qw_text(say, sc), sv, qw_rate(sc, rate), cache, scene_tone(sc))
            else:
                mp3 = _tts_cached(say, sv, sc.get('rate', rate), cache, scene_tone(sc) if bl else None)
            w = mp3.with_name(mp3.name.split('.')[0] + f'.clean{SR}.wav')   # 文件名带采样率，和 sil{ms}-{SR}.wav 同理：换采样率时不复用旧缓存
            if not w.exists():
                # 去掉 TTS 首尾多余的静音，场景之间的停顿由下面统一控制。
                # 10-16：旧版硬切到 -45dB 会削掉字头的气声和句尾的余音，接缝处还会"咔"一下；
                # 现在门限放到 -50dB、两头各留 40ms 原声，再加 6ms 淡入 / 25ms 淡出
                subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(mp3), '-af',
                                f'aresample={SR},{TRIM}', '-ar', str(SR), '-ac', '1', str(w)], check=True)
            segs.append(w)
            if ch is not chunks[-1]:
                segs.append(silence(holds[ch[-1]]))
        if len(segs) == 1:
            wav = segs[0]
        else:
            wav = cache / f'scene{si:02d}-joined.wav'
            (cache / f'scene{si:02d}.txt').write_text(''.join(f"file '{p}'\n" for p in segs))
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(cache / f'scene{si:02d}.txt'),
                            '-ar', str(SR), '-ac', '1', str(wav)], check=True)
        d = probe_duration(wav)
        b = _split_lines(wav, texts, d)
        for k, ln in enumerate(sc['lines']):
            lines.append({'scene': si, 'start': round(t + b[k], 3), 'dur': round(b[k + 1] - b[k], 3), 'text': ln})
        sc['_lines'] = [(t + b[k], b[k + 1] - b[k]) for k in range(len(sc['lines']))]
        if si == 0:  # 开头体检要第一句的真实念完时间：句子边界取在停顿中点，这里退回到停顿开始处
            sil = _silences(wav)
            sc['_speech'] = [(t + b[k], t + next((a for a, z in sil if a <= b[k + 1] <= z + .01), b[k + 1])) for k in range(len(sc['lines']))]
        pause =float(sc.get('pause_after', 0.2 if sc.get('type') == 'hook' else 0.35))
        parts += [wav, silence(pause)]
        t += d + pause
        sc['_end'] = t
    total = round(t + 0.6, 3)
    spec['scenes'][-1]['_end'] = total
    # concat 分离器要求每段格式一致、不会自动重采样：拼之前逐段核对，采样率/声道不对的先转成 SR 单声道（10-16 事故）
    fixed = []
    for p in parts:
        sr_ch = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=sample_rate,channels,codec_name',
                                '-of', 'csv=p=0', str(p)], capture_output=True, text=True).stdout.strip()
        if sr_ch != f'pcm_s16le,{SR},1':
            q = cache / f'{pathlib.Path(p).stem}-norm{SR}.wav'
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(p), '-ar', str(SR), '-ac', '1', '-c:a', 'pcm_s16le', str(q)], check=True)
            print(f'[配音] {pathlib.Path(p).name} 格式 {sr_ch} 和 {SR}Hz 单声道不一致，已统一后再拼', file=sys.stderr)
            p = q
        fixed.append(p)
    parts = fixed
    lst = cache / 'concat.txt'
    lst.write_text(''.join(f"file '{p}'\n" for p in parts))
    voice_wav = cache / 'voice.wav'
    # 10-16：旧版单遍 loudnorm 是动态模式，一句话里音量忽大忽小（"抽吸"），听着像有瑕疵。
    # 改成先测整段响度，再用一个固定增益拉到 -16 LUFS，峰值交给限幅器（关掉 auto level，不然会把峰值推到 0dB 破音）
    dry = cache / 'voice-dry.wav'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst),
                    '-af', f'apad=whole_dur={total:.3f},{VOICE_CHAIN}', '-ar', str(SR), '-ac', '1', str(dry)], check=True)
    gain = -16 - _lufs(dry)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(dry),
                    '-af', f'volume={gain:.2f}dB,alimiter=limit=0.84:attack=3:release=60:level=false', '-ar', str(SR), str(voice_wav)], check=True)
    narr = work / 'assets/narration.m4a'
    narr.parent.mkdir(parents=True, exist_ok=True)
    bgm = pick_bgm(spec)
    if bgm:
        f, meta = bgm
        spec['_bgm'] = {'id': meta['id'], 'name': meta['name']}
        vol = float(spec.get('bgm_volume', 1.0))
        off = _bgm_offset(f, total)
        lastsc = spec['scenes'][-1]
        ec_at = lastsc['_start'] if lastsc.get('type') in ('cta', 'endcard') else total + 1
        spec['_bgm']['offset'] = off
        # BGM 先归一到 -36 LUFS（比人声低约 20 dB），再在人声频段（1.6kHz 附近）削 6 dB 给说话让位，有人声时再由 sidechain 深压。
        # 10-16（用户：有回音、有噪音）：旧版 -29 LUFS + release 600ms，每句话一停音乐就涌上来，像回声尾巴，DNSMOS 背景分 3.2；
        # 改成 ratio 10、release 1.6s：说话期间（含句间短停顿）音乐基本听不到，只在片头片尾长空档里出来，背景分 4.0（不垫音乐 4.1）
        fc = (f'[1:a]atrim=start={off:.2f},asetpts=PTS-STARTPTS,aresample={SR},loudnorm=I={-36 + 20 * math.log10(max(vol, 0.05)):.1f}:TP=-6,aresample={SR},'
              f'equalizer=f=1600:t=o:w=2:g=-6,'
              f"volume='if(gte(t,{ec_at:.2f}),0.5,1)':eval=frame,"   # 片尾开始 BGM 再降 6dB，让声音 logo 浮在上面
              f'afade=t=in:st=0:d=1.5,afade=t=out:st={max(total - 2.5, 0):.2f}:d=2.5,atrim=0:{total:.3f}[bg];'
              f'[0:a]asplit=2[v][sc];'
              f'[bg][sc]sidechaincompress=threshold=0.008:ratio=10:attack=15:release=1600:knee=4[bgd];'
              f'[v][bgd]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.84:level=false[out]')   # level=false：别自动拉到 0dB
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(voice_wav), '-stream_loop', '-1', '-i', str(f),
                        '-filter_complex', fc, '-map', '[out]', '-ar', str(SR), '-c:a', 'aac', '-b:a', '256k', str(narr)], check=True)
    else:
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(voice_wav), '-ar', str(SR), '-c:a', 'aac', '-b:a', '256k', str(narr)], check=True)
    return lines, total


# highlight 场景的马克笔笔画（取自 registry marker-highlight）：(viewBox, path, 线宽, 不透明度)。
# 路径画在固定 viewBox 里，preserveAspectRatio=none 拉伸到关键词的框上，横竖拉伸比例不同正好像真马克笔。
MARKS = {
    'highlight': ('0 0 100 40', 'M 9 21 C 28 19.5, 48 22.5, 66 20.5 C 76 19.5, 84 21, 91 20.5', 34, .95),   # 10-16 加粗到 34：原来 24 只盖住字的中间一截，深色字上下两头压在深色背景上像被切掉
    'circle': ('0 0 100 40', 'M 22 7 C 58 1, 95 8, 97 20 C 99 31, 74 38, 44 37 C 16 36, 2 29, 3 19 C 4 10, 22 4, 52 4.5', 2.8, 1),
    'underline': ('0 0 100 12', 'M 2 7 C 20 4.5, 46 8.5, 66 6 C 80 4.5, 92 7.5, 98 5.5', 4.5, 1),
    'scribble': ('0 0 100 40', 'M 6 13 C 34 9.5, 66 11, 94 9 C 60 15, 26 16, 7 20 C 36 18, 68 21, 93 18 C 62 25, 28 27, 8 29', 5, .8),
}


def scene_html(sc, i, work):
    t = sc.get('type', 'image')
    sid = f's{i}'
    if t == 'hook':
        def hk_row(row):   # **词** 标黄（第二行的数字/反差词用强调色，第 0 帧就抓眼）
            out, bold = [], False
            for part in re.split(r'(\*\*)', row):
                if part == '**':
                    bold = not bold
                    continue
                out += [f'<span class="hk-ch{" hk-em" if bold else ""}">{esc(c)}</span>' for c in part]
            return ''.join(out)
        rows = ''.join(f'<div class="hk-row">{hk_row(row)}</div>' for row in sc.get('big', '').split('\n'))
        sub = f'<div class="pill hk-sub">{esc(sc["sub"])}</div>' if sc.get('sub') else ''
        return f'<div class="inner hook{" first" if i == 0 else ""}"><div class="hk-big">{rows}</div><div class="flash"></div>{sub}</div>'
    if t == 'highlight':
        em, style = sc.get('em', ''), sc.get('mark', 'highlight')
        style = style if style in MARKS else 'highlight'
        vb, d, sw, _ = MARKS[style]
        rows, hit = [], False
        for r in sc['text'].split('\n'):
            k = r.find(em) if em and not hit else -1
            if k >= 0:
                hit = True
                rows.append(f'{mark(r[:k])}<span class="hl-em" data-m="{style}"><svg class="hl-mark" viewBox="{vb}" preserveAspectRatio="none" aria-hidden="true">'
                            f'<path d="{d}" style="stroke-width:{sw}"/></svg><span class="hl-et">{"".join(f"<span class=hl-c>{esc(c)}</span>" for c in em)}</span></span>{mark(r[k + len(em):])}')
            else:
                rows.append(mark(r))
        if em and not hit:
            print(f'[highlight] 场景{i}：em「{em}」不在 text 里，不会划线', file=sys.stderr)
        fs = max(64, min(128, int(940 / max(max(_units(r) for r in sc['text'].split('\n')), 1))))
        label = f'<div class="hl-label">{esc(sc["label"])}</div>' if sc.get('label') else ''
        sub = f'<div class="hl-sub">{mark(sc["sub"])}</div>' if sc.get('sub') else ''
        body = ''.join(f'<div class="hl-row">{r}</div>' for r in rows)
        return f'<div class="inner highlight">{label}<div class="hl-text" style="font-size:{fs}px">{body}</div>{sub}</div>'
    if t == 'progress':
        mx = float(sc.get('max', 100))
        suf, pre = sc.get('suffix', '%' if mx == 100 else ''), sc.get('prefix', '')
        # 字号按最终数字的宽度定（圆环里只有约 360px 宽，横条版约 900px），"327人"这种不会撑出圆环
        vs = f'{float(sc.get("value", 0)):.{int(sc.get("decimals", 0))}f}'
        w = .6 * len(vs) + .45 * _units(pre + suf) + .05
        fs = int(min(200, 360 / w) if sc.get('style') == 'ring' else min(260, 880 / w))
        num = (f'<div class="pg-num"><span class="pre" style="font-size:{fs * .45:.0f}px">{esc(pre)}</span><span class="val" id="{sid}-val" style="font-size:{fs}px">0</span>'
               f'<span class="suf" style="font-size:{fs * .45:.0f}px">{esc(suf)}</span></div>')
        if sc.get('style') == 'ring':
            body = f'<div class="pg-ringw"><div class="pg-ring" id="{sid}-ring"></div>{num}</div>'
        else:
            body = f'{num}<div class="pg-track"><div class="pg-fill" id="{sid}-fill"></div></div>'
        label = f'<div class="pg-label">{mark(sc["label"])}</div>' if sc.get('label') else ''
        cap = f'<div class="pg-cap">{mark(sc["caption"])}</div>' if sc.get('caption') else ''
        return f'<div class="inner progress {"ring" if sc.get("style") == "ring" else "bar"}">{body}{label}{cap}</div>'
    if t == 'split':
        def half(dd, side, default_tag):
            val = str(dd.get('value', ''))
            fs = max(70, min(140, int(360 / max(_units(val), 1))))
            note = f'<div class="sp-note">{mark(dd["note"])}</div>' if dd.get('note') else ''
            return (f'<div class="sp-half {side}"><div class="sp-tag">{esc(dd.get("tag", default_tag))}</div>'
                    f'<div class="sp-val" style="font-size:{fs}px">{mark(val)}</div>{note}</div>')
        head = f'<div class="heading">{mark(sc["heading"])}</div>' if sc.get('heading') else ''
        return (f'<div class="inner split">{head}<div class="sp-wrap">'
                f'<div class="sp-layer sp-before">{half(sc.get("before", {}), "l", "改前")}</div>'
                f'<div class="sp-layer sp-after" id="{sid}-after">{half(sc.get("after", {}), "r", "改后")}</div>'
                f'<div class="sp-div" id="{sid}-div"><div class="sp-knob">→</div></div></div></div>')
    if t == 'stat':
        return (f'<div class="inner stat">'
                f'<div class="num"><span class="pre">{esc(sc.get("prefix",""))}</span><span class="val" id="{sid}-val">0</span>'
                f'<span class="suf">{esc(sc.get("suffix",""))}</span></div><div class="st-line"></div><div class="label">{mark(sc.get("label",""))}</div></div>')
    if t == 'list':
        items = ''.join(f'<div class="li"><span class="li-n">{n+1}</span><span class="li-t">{mark(x)}</span></div>' for n, x in enumerate(sc['items']))
        return f'<div class="inner list"><div class="heading">{mark(sc.get("heading",""))}</div>{items}</div>'
    if t == 'compare':
        def card(side, d):
            ok = d.get('good', side == 'left')
            its = ''.join(f'<div class="cp-i">{mark(x)}</div>' for x in d.get('items', []))
            return f'<div class="cp {side} {"good" if ok else "bad"}"><div class="cp-badge">{"✓" if ok else "✕"}</div><div class="cp-title">{mark(d["title"])}</div>{its}</div>'
        return f'<div class="inner compare">{card("left", sc["left"])}<div class="vs">VS</div>{card("right", sc["right"])}</div>'
    if t == 'timeline':
        pts = sc['points']
        dots = ''.join(f'<div class="tl-p" style="left:{(n/(max(len(pts)-1,1)))*100:.1f}%"><div class="tl-dot"></div><div class="tl-t">{esc(p["t"])}</div><div class="tl-l">{mark(p.get("label",""))}</div></div>' for n, p in enumerate(pts))
        center = f'<div class="tl-center">{mark(sc["center"])}</div>' if sc.get('center') else ''
        return f'<div class="inner timeline">{center}<div class="tl-track"><div class="tl-line"></div>{dots}</div></div>'
    if t == 'quote':
        chars = ''.join(f'<span class="q-ch">{esc(c)}</span>' for c in sc['text'])
        by = f'<div class="q-by">{esc(sc["by"])}</div>' if sc.get('by') else ''
        return f'<div class="inner quote"><div class="q-mark">“</div><div class="q-text">{chars}</div><div class="q-line"></div>{by}</div>'
    if t == 'chat':
        ok = sc.get('good', True)
        verdict = f'<div class="ct-stamp {"good" if ok else "bad"}">{esc(sc["verdict"])}</div>' if sc.get('verdict') else ''
        reply = ''.join(f'<span class="ct-ch">{esc(c)}</span>' if c != '\n' else '<br>' for c in sc['reply'])
        return (f'<div class="inner chat"><div class="ct-model">{esc(sc.get("model","AI"))} · 实测</div>'
                f'<div class="ct-b ask">{mark(sc["ask"])}</div>'
                f'<div class="ct-b reply"><div class="ct-dots"><i></i><i></i><i></i></div><div class="ct-txt">{reply}</div></div>{verdict}</div>')
    if t == 'bars':
        items = sc['items']
        vmax = max(float(x['value']) for x in items) or 1
        best = sc.get('best')
        rows = ''.join(
            f'<div class="br-row{" best" if n == best else ""}"><div class="br-l">{esc(x["label"])}</div>'
            f'<div class="br-track"><div class="br-fill" style="width:{max(6, float(x["value"]) / vmax * 100):.1f}%"></div></div>'
            f'<div class="br-v">{esc(x.get("display") or (str(x["value"]) + sc.get("unit", "")))}</div></div>'
            for n, x in enumerate(items))
        return f'<div class="inner bars"><div class="heading">{mark(sc.get("heading",""))}</div>{rows}</div>'
    if t == 'chapter':
        sub = f'<div class="chp-sub">{mark(sc["sub"])}</div>' if sc.get('sub') else ''
        return f'<div class="inner chapter"><div class="chp-n">{esc(sc.get("n",""))}</div><div class="chp-bar"></div><div class="chp-t">{mark(sc["title"])}</div>{sub}</div>'
    if t == 'screen':  # 真实截图（实测录屏的关键帧）：推近到操作区域 + 高亮框 + 步骤号
        img = pathlib.Path(sc['image'])
        if not img.is_absolute():
            img = work.parent / img
        dst = work / 'assets' / f'scr{i:02d}{img.suffix}'
        shutil.copy(img, dst)
        fx, fy, fw, fh = sc.get('focus', [0, 0, 1, 1])
        box = f'<div class="sc-box" style="left:{fx*100:.2f}%;top:{fy*100:.2f}%;width:{fw*100:.2f}%;height:{fh*100:.2f}%"></div>' if sc.get('focus') else ''
        step = f'<div class="sc-step">{esc(sc["step"])}</div>' if sc.get('step') else ''
        cap = f'<div class="sc-cap">{mark(sc["caption"])}</div>' if sc.get('caption') else ''
        return (f'<div class="inner screen">{step}<div class="sc-win"><div class="sc-bar"><i></i><i></i><i></i></div>'
                f'<div class="sc-view"><div class="sc-zoom" id="{sid}-zoom"><img src="assets/{dst.name}"/>{box}</div></div></div>{cap}</div>')
    if t == 'cta':
        return f'<div class="inner cta"><div class="cta-text">{mark(sc["text"])}</div><div class="cta-hint">{esc(sc.get("hint","评论区聊聊"))}</div><div class="arrow"></div></div>'
    # image
    img = sc.get('image')
    if not img:
        img = work / f'scene{i:02d}.png'
        gen_image(sc['prompt'] + ', ' + STYLE_IMG, img, size='1024x1536')
    img = pathlib.Path(img)
    if not img.is_absolute():
        img = work.parent / img
    dst = work / 'assets' / f'img{i:02d}{img.suffix}'
    shutil.copy(img, dst)
    head = f'<div class="pill img-head">{esc(sc["headline"])}</div>' if sc.get('headline') else ''
    return f'<div class="inner image"><div class="frame"><img id="{sid}-img" src="assets/{dst.name}"/><div class="sweep"><div class="sweep-i"></div></div></div>{head}</div>'


def beats(sc, n):
    """n 个元素什么时候出现：跟口播走，念到哪句出哪个（反 PPT：不在开头一次性出完）。
    句数 ≥ n+1：第一句是引子，第 2..n+1 句各带出一个；句数 = n：每句一个；否则在场景前 70% 均匀铺开。
    spec 里可以用 "reveal": [0,1,1,2] 显式指定第 k 个元素跟第几句（从 0 起）。"""
    s, e = sc['_start'], sc['_end']
    starts = [st for st, _ in sc.get('_lines', [])]
    if isinstance(sc.get('reveal'), list) and starts:
        out = [starts[min(int(k), len(starts) - 1)] + .15 for k in sc['reveal'][:n]]
    elif len(starts) >= n + 1:
        out = [x + .15 for x in starts[1:n + 1]]
    elif len(starts) == n:
        out = [s + .35] + [x + .15 for x in starts[1:]]
    else:
        step = max(.35, (e - s) * .7 / max(n, 1))
        out = [s + .45 + k * step for k in range(n)]
    sc['_beats'] = out
    return out


def cue(sc, default, find=None):
    """新场景的关键动作什么时候发生：spec 写了 "at"（第几句，从 0 起）就跟那句；否则在口播里找 find 这个词，
    按朗读权重估它被念到的时刻；都没有就用 default。结果夹在场景里，保证动作在场景结束前 0.9 秒做完。"""
    s, e = sc['_start'], sc['_end']
    starts = sc.get('_lines', [])
    at = None
    if isinstance(sc.get('at'), int) and starts:
        at = starts[min(max(sc['at'], 0), len(starts) - 1)][0] + .1
    elif find and starts:
        for (st, d), ln in zip(starts, sc['lines']):
            p = plain(ln)
            k = p.find(find)
            if k >= 0:
                at = st + d * _speech_w(p[:k]) / max(_speech_w(p), 1) - .1
                break
    at = default if at is None else at
    return max(s + .1, min(at, e - .9))


def scene_js(sc, i):
    """动效 v2（10-16，依据 hyperframes-animation / faceless-explainer 的动效规范）：
    - 不用 back/elastic 弹跳（"头号劝退"），入场 expo.out / power3.out，出场比入场快；
    - 元素跟着口播逐个出现（beats），不在场景开头一次性出完然后冻住；
    - 去掉循环呼吸、脉冲光圈、每场白闪这类模板动效；画面停留期只留一个很轻的推近。"""
    t = sc.get('type', 'image')
    s, e = sc['_start'], sc['_end']
    d = e - s
    sid = f'#s{i}'
    # 第 1 个场景不做整体淡入：第 0 帧就要有内容（10-15 数据：2 秒跳出 25–40%，旧版第 0 帧是空的）
    # 剪辑 v3（10-16）：换场默认硬切（旧版淡出 0.25s + 淡入 0.5s，每次换场画面空 0.2–0.3s）；
    # 进 chapter 用「穿越推近」（0.75→1、模糊 10px→0、expo.out），其余新场景 0.35s 快速落位
    if i == 0:
        js = []
    elif t == 'chapter':
        js = [f'tl.fromTo("{sid} .inner",{{opacity:.15,scale:.75,filter:"blur(10px)"}},{{opacity:1,scale:1,filter:"blur(0px)",duration:.5,ease:"expo.out"}},{s:.3f});']
    else:
        js = [f'tl.fromTo("{sid} .inner",{{opacity:0,y:24}},{{opacity:1,y:0,duration:.35,ease:"expo.out"}},{s:.3f});']
    # 停留期：整个场景极轻的推近（1 → 1.03），避免静止画面；放在 .stage 上，不和元素自己的 transform 打架
    js.append(f'tl.fromTo("{sid} .stage",{{scale:1}},{{scale:1.03,duration:{max(d, .5):.2f},ease:"none"}},{s:.3f});')
    if t == 'hook':
        if i == 0:  # 大字第 0 帧已满屏、完全不透明，只做一下 1.08→1 的"砸下来"，和 impact 音效同拍
            js.append(f'tl.fromTo("{sid} .hk-big",{{scale:1.08}},{{scale:1,duration:.45,ease:"expo.out"}},{s:.3f});')
            js.append(f'tl.fromTo("{sid} .flash",{{opacity:1,scaleX:0}},{{opacity:1,scaleX:1,duration:.4,ease:"power3.out"}},{s+.1:.3f});')
        else:
            js.append(f'tl.fromTo("{sid} .hk-ch",{{opacity:0,y:70}},{{opacity:1,y:0,duration:.6,stagger:.035,ease:"expo.out"}},{s+.1:.3f});')
            js.append(f'tl.fromTo("{sid} .flash",{{opacity:1,scaleX:0}},{{opacity:1,scaleX:1,duration:.5,ease:"power3.out"}},{s+.45:.3f});')
        sub_at = sc['_lines'][1][0] if len(sc.get('_lines', [])) > 1 else s + .7
        js.append(f'tl.fromTo("{sid} .hk-sub",{{opacity:0,x:-50}},{{opacity:1,x:0,duration:.45,ease:"power3.out"}},{sub_at:.3f});')
    elif t == 'highlight':
        _, _, _, op = MARKS.get(sc.get('mark'), MARKS['highlight'])
        hl = sc.get('mark', 'highlight') not in MARKS or sc.get('mark', 'highlight') == 'highlight'
        at = cue(sc, s + .9, sc.get('em'))
        sc['_cue'] = at
        js.append(f'tl.fromTo("{sid} .hl-label",{{opacity:0,x:-40}},{{opacity:1,x:0,duration:.4,ease:"power3.out"}},{s+.05:.3f});')
        js.append(f'tl.fromTo("{sid} .hl-row",{{opacity:0,y:40}},{{opacity:1,y:0,duration:.5,stagger:.12,ease:"power3.out"}},{s+.1:.3f});')
        # 笔画：按路径实际长度做 dash 揭示；起笔前 opacity 0，免得圆头线帽露一个点。
        # 补间一个普通对象、在 onUpdate 里写样式，不让 GSAP 直接碰 SVG 元素（隐藏场景里量 SVG 尺寸会走 DOM 挪动的兜底逻辑）。
        js.append(f'(function(){{var p=document.querySelector("{sid} .hl-mark path");if(!p)return;var L=p.getTotalLength();'
                  f'p.style.strokeDasharray=L;p.style.strokeDashoffset=L;p.style.opacity=0;var o={{v:0}};'
                  f'tl.fromTo(o,{{v:0}},{{v:1,duration:.6,ease:"power2.inOut",onUpdate:function(){{'
                  f'p.style.strokeDashoffset=(L*(1-o.v)).toFixed(2);p.style.opacity=o.v>0?{op}:0;}}}},{at:.3f});}})();')
        if hl:  # 荧光笔底色铺到哪个字，哪个字变深色（逐字跟着笔走，不会出现半灰的中间态）
            n = max(len(sc.get('em', '')), 1)
            js.append(f'tl.fromTo("{sid} .hl-c",{{color:"#ffffff"}},{{color:"#111111",duration:.06,ease:"none",stagger:{.42 / n:.3f}}},{at+.12:.3f});')
        # 落笔后关键词轻轻一弹。补间放在 .hl-et（.hl-em 的最后一个子元素）上，不放在 .hl-em 上：GSAP 量隐藏元素的 transform 时会把它
        # 临时挪到 <html> 下再用 nextElementSibling 插回去，.hl-em 后面紧跟的是文字节点，会被插到行尾（实测"一件的活能交差"）
        js.append(f'tl.fromTo("{sid} .hl-et",{{scale:1}},{{scale:1.07,duration:.16,ease:"power1.out",yoyo:true,repeat:1}},{at+.42:.3f});')
        nxt = [st for st, _ in sc.get('_lines', []) if st > at + .5]
        js.append(f'tl.fromTo("{sid} .hl-sub",{{opacity:0,y:24}},{{opacity:1,y:0,duration:.45,ease:"power3.out"}},{min(nxt[0] if nxt else at + .9, e - .8):.3f});')
    elif t == 'progress':
        v, mx, dec = float(sc.get('value', 0)), float(sc.get('max', 100)) or 1, int(sc.get('decimals', 0))
        at = cue(sc, s + .3)
        dur = min(1.6, max(.8, d * .35))
        sc['_cue'] = at + dur
        ring = sc.get('style') == 'ring'
        # 数字和进度共用一个补间：填充和计数永远对得上（registry 的 data-viz 做法）
        upd = (f'rg.style.setProperty("--p",(o.v/{mx}*100).toFixed(2));' if ring else f'fl.style.transform="scaleX("+(o.v/{mx}).toFixed(4)+")";')
        js.append(f'(function(){{var o={{v:0}};var el=document.getElementById("s{i}-val");var rg=document.getElementById("s{i}-ring");var fl=document.getElementById("s{i}-fill");'
                  f'tl.fromTo(o,{{v:0}},{{v:{v},duration:{dur:.2f},ease:"power2.out",onUpdate:function(){{el.textContent=o.v.toFixed({dec});{upd}}}}},{at:.3f});}})();')
        js.append(f'tl.fromTo("{sid} .pg-num",{{opacity:0,y:30}},{{opacity:1,y:0,duration:.4,ease:"power3.out"}},{min(s + .1, at):.3f});')
        lines_ = sc.get('_lines', [])
        lab = lines_[1][0] if len(lines_) > 1 and lines_[1][0] > at else at + dur * .6
        js.append(f'tl.fromTo("{sid} .pg-label",{{opacity:0,y:30}},{{opacity:1,y:0,duration:.45,ease:"power3.out"}},{min(lab, e - .8):.3f});')
        capt = lines_[2][0] if len(lines_) > 2 else max(lab, at + dur) + .4
        js.append(f'tl.fromTo("{sid} .pg-cap",{{opacity:0}},{{opacity:1,duration:.4}},{min(capt, e - .8):.3f});')
    elif t == 'split':
        n = len(sc.get('_lines', []))
        at = cue(sc, sc['_lines'][-1][0] + .1 if n > 1 else s + 1.0)
        sc['_cue'] = at
        js.append(f'tl.fromTo("{sid} .heading",{{opacity:0,y:-24}},{{opacity:1,y:0,duration:.4,ease:"power3.out"}},{s+.05:.3f});')
        js.append(f'tl.fromTo("{sid} .sp-before .sp-half",{{opacity:0,x:-40}},{{opacity:.55,x:0,duration:.5,ease:"power3.out"}},{s+.15:.3f});')
        # 竖线从右边缘出发擦到中线，亮色的"改后"层用 clip-path 跟着露出来；擦完停住给人对比
        js.append(f'tl.fromTo("{sid}-div",{{opacity:0}},{{opacity:1,duration:.15}},{at:.3f});')
        js.append(f'tl.fromTo("{sid}-div",{{left:"100%"}},{{left:"50%",duration:.95,ease:"power3.inOut"}},{at:.3f});')
        js.append(f'tl.fromTo("{sid}-after",{{clipPath:"inset(0% 0% 0% 100%)"}},{{clipPath:"inset(0% 0% 0% 50%)",duration:.95,ease:"power3.inOut"}},{at:.3f});')
        js.append(f'tl.fromTo("{sid} .sp-after .sp-val",{{scale:.86}},{{scale:1,duration:.45,ease:"power3.out"}},{at+.6:.3f});')
    elif t == 'stat':
        v = float(sc.get('value', 0)); dec = int(sc.get('decimals', 0))
        dur = min(1.6, d * .5)
        js.append(f'(function(){{var o={{v:0}};var el=document.getElementById("s{i}-val");tl.fromTo(o,{{v:0}},{{v:{v},duration:{dur:.2f},ease:"power3.out",onUpdate:function(){{el.textContent=o.v.toFixed({dec});}}}},{s+.25:.3f});}})();')
        js.append(f'tl.fromTo("{sid} .st-line",{{scaleX:0}},{{scaleX:1,duration:.6,ease:"power3.out"}},{s+.25+dur:.3f});')
        lab = sc['_lines'][1][0] if len(sc.get('_lines', [])) > 1 else s + .8
        js.append(f'tl.fromTo("{sid} .label",{{opacity:0,y:30}},{{opacity:1,y:0,duration:.5,ease:"power3.out"}},{lab:.3f});')
    elif t == 'list':
        bt = beats(sc, len(sc['items']))
        js.append(f'tl.fromTo("{sid} .heading",{{opacity:0,x:-40}},{{opacity:1,x:0,duration:.45,ease:"power3.out"}},{s+.1:.3f});')
        for k, b in enumerate(bt):
            js.append(f'tl.fromTo("{sid} .li:nth-child({k+2})",{{opacity:0,x:60}},{{opacity:1,x:0,duration:.5,ease:"expo.out"}},{b:.3f});')
            if k:  # 上一条退到次要位置，视线跟着新的一条走
                js.append(f'tl.to("{sid} .li:nth-child({k+1})",{{opacity:.55,duration:.3,ease:"power2.out"}},{b:.3f});')
    elif t == 'compare':
        bt = beats(sc, 2)
        js.append(f'tl.fromTo("{sid} .cp.left",{{opacity:0,x:-80}},{{opacity:1,x:0,duration:.55,ease:"power3.out"}},{min(bt[0], s+.6):.3f});')
        js.append(f'tl.fromTo("{sid} .vs",{{opacity:0,scale:.7}},{{opacity:1,scale:1,duration:.4,ease:"power3.out"}},{bt[1]-.2:.3f});')
        js.append(f'tl.fromTo("{sid} .cp.right",{{opacity:0,x:80}},{{opacity:1,x:0,duration:.55,ease:"power3.out"}},{bt[1]:.3f});')
    elif t == 'timeline':
        pts = sc['points']
        bt = beats(sc, len(pts))
        js.append(f'tl.fromTo("{sid} .tl-line",{{scaleX:0}},{{scaleX:1,duration:{max(.6, bt[-1]-s):.2f},ease:"power2.inOut"}},{s+.2:.3f});')
        for k, b in enumerate(bt):
            js.append(f'tl.fromTo("{sid} .tl-p:nth-child({k+2})",{{opacity:0,y:24}},{{opacity:1,y:0,duration:.45,ease:"expo.out"}},{b:.3f});')
        js.append(f'tl.fromTo("{sid} .tl-center",{{opacity:0,y:30}},{{opacity:1,y:0,duration:.55,ease:"power3.out"}},{min(bt[-1]+.4, e-.8):.3f});')
    elif t == 'quote':
        n = len(sc['text'])
        per = min(0.07, d * 0.5 / max(n, 1))
        js.append(f'tl.fromTo("{sid} .q-mark",{{opacity:0,y:20}},{{opacity:.22,y:0,duration:.5,ease:"power3.out"}},{s:.3f});')
        js.append(f'tl.fromTo("{sid} .q-ch",{{opacity:0}},{{opacity:1,duration:.01,stagger:{per:.3f}}},{s+.2:.3f});')
        js.append(f'tl.fromTo("{sid} .q-line",{{scaleX:0}},{{scaleX:1,duration:.6,ease:"power3.out"}},{s+.3+per*n:.3f});')
    elif t == 'chat':
        n = max(len(sc['reply']), 1)
        ask_at = s + .15
        t_reply = (sc['_lines'][1][0] if len(sc.get('_lines', [])) > 1 else s + .9)
        per = min(0.06, max(0.012, (e - t_reply - 1.2) / n))
        js.append(f'tl.fromTo("{sid} .ct-model",{{opacity:0,y:-16}},{{opacity:1,y:0,duration:.35,ease:"power3.out"}},{s+.05:.3f});')
        js.append(f'tl.fromTo("{sid} .ask",{{opacity:0,x:60}},{{opacity:1,x:0,duration:.45,ease:"expo.out"}},{ask_at:.3f});')
        js.append(f'tl.fromTo("{sid} .reply",{{opacity:0,x:-60}},{{opacity:1,x:0,duration:.45,ease:"expo.out"}},{t_reply-.5:.3f});')
        js.append(f'tl.fromTo("{sid} .ct-dots i",{{opacity:.3}},{{opacity:1,duration:.2,yoyo:true,repeat:1,stagger:.08}},{t_reply-.45:.3f});')
        js.append(f'tl.to("{sid} .ct-dots",{{opacity:0,height:0,duration:.1}},{t_reply-.05:.3f});')
        js.append(f'tl.fromTo("{sid} .ct-ch",{{opacity:0}},{{opacity:1,duration:.01,stagger:{per:.3f}}},{t_reply:.3f});')
        if sc.get('verdict'):
            at = min(t_reply + per * n + .3, e - .9)
            sc['_stamp_at'] = at
            js.append(f'tl.fromTo("{sid} .ct-stamp",{{opacity:0,scale:1.6}},{{opacity:1,scale:1,duration:.3,ease:"power4.out"}},{at:.3f});')
    elif t == 'bars':
        bt = beats(sc, len(sc['items']))
        js.append(f'tl.fromTo("{sid} .heading",{{opacity:0,x:-40}},{{opacity:1,x:0,duration:.45,ease:"power3.out"}},{s+.1:.3f});')
        for k, b in enumerate(bt):
            js.append(f'tl.fromTo("{sid} .br-row:nth-child({k+2})",{{opacity:0,y:20}},{{opacity:1,y:0,duration:.35,ease:"power3.out"}},{b:.3f});')
            js.append(f'tl.fromTo("{sid} .br-row:nth-child({k+2}) .br-fill",{{scaleX:0}},{{scaleX:1,duration:.8,ease:"power3.out"}},{b+.05:.3f});')
    elif t == 'chapter':
        js.append(f'tl.fromTo("{sid} .chp-n",{{opacity:0,y:50}},{{opacity:1,y:0,duration:.6,ease:"expo.out"}},{s+.05:.3f});')
        js.append(f'tl.fromTo("{sid} .chp-bar",{{scaleX:0}},{{scaleX:1,duration:.5,ease:"power3.out"}},{s+.3:.3f});')
        js.append(f'tl.fromTo("{sid} .chp-t",{{opacity:0,y:30}},{{opacity:1,y:0,duration:.5,ease:"power3.out"}},{s+.45:.3f});')
        js.append(f'tl.fromTo("{sid} .chp-sub",{{opacity:0}},{{opacity:1,duration:.4}},{s+.8:.3f});')
    elif t == 'screen':
        fx, fy, fw, fh = sc.get('focus', [0, 0, 1, 1])
        z = min(2.4, max(1.0, 0.85 / max(fw, fh * 0.64)))  # 截图视窗 960×600，按焦点区域推近
        VW, VH = 960, 600
        tx = min(0.0, max(VW - z * VW, VW / 2 - z * (fx + fw / 2) * VW))
        ty = min(0.0, max(VH - z * VH, VH / 2 - z * (fy + fh / 2) * VH))
        zoom_at = sc['_lines'][1][0] if len(sc.get('_lines', [])) > 1 else s + .6
        js.append(f'tl.fromTo("{sid} .sc-step",{{opacity:0,x:-40}},{{opacity:1,x:0,duration:.4,ease:"power3.out"}},{s+.1:.3f});')
        js.append(f'tl.fromTo("{sid} .sc-cap",{{opacity:0,y:24}},{{opacity:1,y:0,duration:.45,ease:"power3.out"}},{s+.3:.3f});')
        if sc.get('focus'):
            zd = min(1.2, d * .3)
            js.append(f'gsap.set("{sid}-zoom",{{transformOrigin:"0% 0%"}});')
            js.append(f'tl.fromTo("{sid}-zoom",{{scale:1,x:0,y:0}},{{scale:{z:.2f},x:{tx:.1f},y:{ty:.1f},duration:{zd:.2f},ease:"power2.inOut"}},{zoom_at:.3f});')
            js.append(f'tl.fromTo("{sid} .sc-box",{{opacity:0,scale:1.15}},{{opacity:1,scale:1,duration:.35,ease:"power3.out"}},{zoom_at+zd:.3f});')
    elif t == 'cta':
        js.append(f'tl.fromTo("{sid} .cta-text",{{opacity:0,y:40}},{{opacity:1,y:0,duration:.55,ease:"power3.out"}},{s+.1:.3f});')
        js.append(f'tl.fromTo("{sid} .cta-hint",{{opacity:0,y:24}},{{opacity:1,y:0,duration:.45,ease:"power3.out"}},{s+.6:.3f});')
        js.append(f'tl.fromTo("{sid} .arrow",{{opacity:0,y:-20}},{{opacity:1,y:0,duration:.5,ease:"power3.out"}},{s+.9:.3f});')
    else:  # image：Ken Burns 放在子元素 img 上，入场动画在父元素 .inner 上，两个 transform 不打架
        js.append(f'tl.fromTo("{sid}-img",{{scale:1.08,xPercent:{-1.5 if i % 2 else 1.5}}},{{scale:1.0,xPercent:0,duration:{d:.2f},ease:"none"}},{s:.3f});')
        js.append(f'tl.fromTo("{sid} .sweep",{{xPercent:-160}},{{xPercent:260,duration:1.2,ease:"power2.inOut"}},{s+.4:.3f});')
        js.append(f'tl.fromTo("{sid} .img-head",{{opacity:0,y:-24}},{{opacity:1,y:0,duration:.45,ease:"power3.out"}},{s+.3:.3f});')
    if sc.get('_next_type') == 'chapter' and e < sc.get('_total', 1e9) - 0.9:   # 穿越推近的前半段：冲进镜头再切
        js.append(f'tl.to("{sid} .inner",{{scale:1.2,filter:"blur(20px)",opacity:.15,duration:.2,ease:"power3.in"}},{max(s+.5, e-.2):.3f});')
    return '\n'.join(js)


COLUMNS = {'先试': '示例作者先试', '算账': '示例作者算账', '抄作业': '抄作业', '热点': 'AI热点说人话', '办公课': 'AI办公课'}

CSS = """
@font-face{font-family:NS;src:url("assets/NotoSansSC.ttf");font-weight:100 900}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:100%;height:100%;background:var(--bg1);font-family:NS;color:#fff}
#root{position:relative;width:100%;height:100%;overflow:hidden;background:linear-gradient(170deg,var(--bg1),var(--bg2))}
.grid{position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);background-size:72px 72px}
.blob{position:absolute;width:760px;height:760px;border-radius:50%;filter:blur(140px);opacity:.16}
.stage{position:absolute;inset:0}
.ghost{position:absolute;left:40px;top:1480px;font-size:300px;font-weight:900;white-space:nowrap;color:#fff;opacity:.022;letter-spacing:10px}
#b1{left:-260px;top:300px;background:var(--accent)}
#b2{left:520px;top:1100px;background:var(--accent)}
#bgflash{position:absolute;inset:0;background:#fff;opacity:0}
.brand{position:absolute;left:72px;top:172px;font-size:34px;font-weight:700;padding:10px 26px;border-radius:40px;background:rgba(0,0,0,.35);border:2px solid rgba(255,255,255,.25)}
.tag{position:absolute;right:72px;top:178px;font-size:32px;font-weight:700;color:var(--accent);letter-spacing:4px}
.title{position:absolute;left:72px;right:72px;top:250px;text-align:center}
.title .tl1,.title .tl2{display:block;font-size:80px;font-weight:900;line-height:1.18;text-shadow:0 6px 24px rgba(0,0,0,.6)}
.title .tl2{color:var(--accent)}
.clip{position:absolute;inset:0}
.inner{position:absolute;left:60px;right:60px;top:470px;height:780px;display:flex;flex-direction:column;align-items:center;justify-content:center}
.pill{display:inline-block;background:var(--accent);color:#111;font-weight:900;font-size:50px;padding:10px 34px;border-radius:18px}
em{font-style:normal;color:var(--accent)}
.inner.hook.first{top:300px;height:950px}
.hook .hk-big{display:flex;flex-direction:column;align-items:center}
.hook .hk-row{display:flex;justify-content:center;font-size:150px;font-weight:900;line-height:1.15;text-shadow:0 10px 40px rgba(0,0,0,.6)}
.hook .hk-ch{display:inline-block}
.hook .hk-em{color:var(--accent)}
.hook .hk-sub{margin-top:50px;font-size:60px}
.hook .flash{width:58%;height:14px;border-radius:7px;background:var(--accent);margin-top:26px;transform-origin:left center;opacity:0}
.stat .st-line{width:460px;height:12px;border-radius:6px;background:var(--accent);margin-top:18px;transform-origin:left center}
.stat .num{display:flex;align-items:baseline;font-weight:900;color:var(--accent);text-shadow:0 10px 50px rgba(0,0,0,.5)}
.stat .val{font-size:300px;line-height:1}
.stat .pre,.stat .suf{font-size:120px;margin:0 10px}
.stat .label{text-wrap:balance;margin-top:40px;font-size:60px;font-weight:800;text-align:center;line-height:1.35}
.stat .ring{position:absolute;width:620px;height:620px;border-radius:50%;border:6px solid var(--accent);opacity:0}
.list{align-items:stretch}
.list .heading{font-size:64px;font-weight:900;margin-bottom:40px}
.list .li{display:flex;align-items:center;background:rgba(255,255,255,.08);border:2px solid rgba(255,255,255,.14);border-radius:28px;padding:28px 34px;margin:14px 0}
.list .li-n{flex:0 0 84px;height:84px;border-radius:50%;background:var(--accent);color:#111;font-size:50px;font-weight:900;display:flex;align-items:center;justify-content:center;margin-right:30px}
.list .li-t{text-wrap:balance;font-size:56px;font-weight:800;line-height:1.3}
.compare{flex-direction:row;align-items:center;justify-content:space-between}
.compare .cp{min-height:500px;max-height:640px}
.compare .cp{width:440px;border-radius:32px;padding:40px 30px;background:rgba(255,255,255,.08);border:3px solid rgba(255,255,255,.15);display:flex;flex-direction:column;align-items:center}
.compare .cp.good{border-color:#34d399;background:rgba(52,211,153,.12)}
.compare .cp.bad{border-color:#f87171;background:rgba(248,113,113,.10)}
.compare .cp-badge{width:120px;height:120px;border-radius:50%;font-size:80px;font-weight:900;display:flex;align-items:center;justify-content:center;margin-bottom:24px}
.compare .good .cp-badge{background:#34d399;color:#06281c}
.compare .bad .cp-badge{background:#f87171;color:#3b0a0a}
.compare .cp-title{font-size:54px;font-weight:900;text-align:center;margin-bottom:26px;line-height:1.25}
.compare .cp-i{font-size:42px;font-weight:700;line-height:1.4;text-align:center;margin:10px 0;opacity:.95}
.compare .vs{position:absolute;left:50%;top:50%;width:120px;height:120px;margin:-60px 0 0 -60px;border-radius:50%;background:var(--accent);color:#111;font-size:50px;font-weight:900;display:flex;align-items:center;justify-content:center}
.timeline .tl-center{font-size:120px;font-weight:900;color:var(--accent);margin-bottom:120px;text-align:center}
.timeline .tl-track{position:relative;width:860px;height:200px}
.timeline .tl-line{position:absolute;left:0;right:0;top:40px;height:10px;border-radius:5px;background:linear-gradient(90deg,var(--accent2),var(--accent));transform-origin:left center}
.timeline .tl-p{position:absolute;top:0;width:0;display:flex;flex-direction:column;align-items:center}
.timeline .tl-dot{width:90px;height:90px;border-radius:50%;background:#fff;border:12px solid var(--accent);margin-top:0}
.timeline .tl-t{margin-top:18px;font-size:58px;font-weight:900;white-space:nowrap}
.timeline .tl-l{font-size:40px;font-weight:700;white-space:nowrap;opacity:.9}
.quote .q-mark{position:absolute;left:10px;top:40px;font-size:400px;font-weight:900;color:var(--accent);opacity:.25;line-height:1}
.quote .q-text{text-wrap:balance;font-size:96px;font-weight:900;line-height:1.35;text-align:center;max-width:920px}
.quote .q-line{width:560px;height:14px;border-radius:7px;background:var(--accent);margin-top:40px;transform-origin:left center}
.quote .q-by{margin-top:30px;font-size:42px;opacity:.8}
.cta .cta-text{text-wrap:balance;font-size:88px;font-weight:900;line-height:1.3;text-align:center;max-width:940px}
.cta .cta-hint{margin-top:44px;font-size:50px;font-weight:800;background:rgba(255,255,255,.12);padding:16px 40px;border-radius:40px}
.cta .arrow{margin-top:40px;width:0;height:0;border-left:44px solid transparent;border-right:44px solid transparent;border-top:56px solid var(--accent)}
.screen{justify-content:flex-start;padding-top:20px}
.screen .sc-step{align-self:flex-start;font-size:46px;font-weight:900;color:#111;background:var(--accent);padding:8px 28px;border-radius:16px;margin-bottom:26px}
.screen .sc-win{width:960px;border-radius:26px;overflow:hidden;background:#f4f5f7;box-shadow:0 30px 80px rgba(0,0,0,.5);border:3px solid rgba(255,255,255,.2)}
.screen .sc-bar{height:44px;background:#e6e8ec;display:flex;align-items:center;padding-left:20px;gap:12px}
.screen .sc-bar i{width:16px;height:16px;border-radius:50%;background:#ff5f57}.screen .sc-bar i+i{background:#febc2e}.screen .sc-bar i+i+i{background:#28c840}
.screen .sc-view{position:relative;width:960px;height:600px;overflow:hidden;background:#fff}
.screen .sc-zoom{position:absolute;inset:0}
.screen .sc-zoom img{width:100%;height:100%;object-fit:contain;display:block}
.screen .sc-box{position:absolute;border:6px solid #ffc800;border-radius:12px;box-shadow:0 0 0 0 rgba(255,200,0,.7);opacity:0}
.screen .sc-cap{margin-top:34px;font-size:52px;font-weight:900;line-height:1.35;text-align:center;text-wrap:balance}
.image .frame{position:relative;width:940px;height:780px;border-radius:44px;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.55);border:4px solid rgba(255,255,255,.18)}
.image .frame img{width:100%;height:100%;object-fit:cover;display:block}
.image .sweep{position:absolute;top:-20%;bottom:-20%;width:180px;left:0}.image .sweep-i{width:100%;height:100%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.35),transparent);transform:skewX(-18deg)}
.image .img-head{position:absolute;top:-40px}
.chat{align-items:stretch;justify-content:flex-start;padding-top:20px}
.chat .ct-model{align-self:center;font-size:40px;font-weight:800;padding:8px 28px;border-radius:30px;background:rgba(255,255,255,.12);margin-bottom:34px}
.chat .ct-b{font-size:46px;font-weight:700;line-height:1.45;padding:26px 34px;border-radius:34px;max-width:860px;margin:12px 0}
.chat .ask{align-self:flex-end;background:var(--accent);color:#111;border-bottom-right-radius:8px}
.chat .ask em{color:#111;text-decoration:underline}
.chat .reply{align-self:flex-start;background:rgba(255,255,255,.95);color:#1b1f2a;border-bottom-left-radius:8px;min-width:240px}
.chat .ct-dots{display:flex;gap:14px;height:40px;align-items:center}.chat .ct-dots i{width:18px;height:18px;border-radius:50%;background:#9aa3b5;display:block}
.chat .ct-stamp{position:absolute;right:30px;bottom:30px;font-size:64px;font-weight:900;padding:8px 30px;border:8px solid;border-radius:20px;transform:rotate(-12deg);background:rgba(0,0,0,.35)}
.chat .ct-stamp.good{color:#34d399;border-color:#34d399}.chat .ct-stamp.bad{color:#f87171;border-color:#f87171}
.bars{align-items:stretch}
.bars .heading{font-size:64px;font-weight:900;margin-bottom:36px;text-align:center}
.bars .br-row{display:flex;align-items:center;margin:16px 0;transform-origin:center}
.bars .br-l{flex:0 0 250px;font-size:46px;font-weight:800;text-align:right;padding-right:24px;white-space:nowrap;overflow:hidden}
.bars .br-track{flex:1;height:70px;border-radius:16px;background:rgba(255,255,255,.08);overflow:hidden}
.bars .br-fill{height:100%;border-radius:16px;background:linear-gradient(90deg,var(--accent2),#8fd3ff);transform-origin:left center}
.bars .best .br-fill{background:linear-gradient(90deg,#ffb703,var(--accent))}
.bars .br-v{flex:0 0 190px;font-size:46px;font-weight:900;padding-left:22px;white-space:nowrap}
.bars .best .br-v,.bars .best .br-l{color:var(--accent)}
.chapter .chp-n{font-size:220px;font-weight:900;color:var(--accent);line-height:1;text-shadow:0 10px 40px rgba(0,0,0,.5)}
.chapter .chp-bar{width:420px;height:12px;border-radius:6px;background:var(--accent2);margin:36px 0;transform-origin:center}
.chapter .chp-t{text-wrap:balance;font-size:84px;font-weight:900;text-align:center;line-height:1.25;max-width:940px}
.chapter .chp-sub{margin-top:30px;font-size:48px;font-weight:700;opacity:.85;text-align:center}
.highlight .hl-label{font-size:44px;font-weight:900;color:#111;background:var(--accent);padding:8px 28px;border-radius:14px;margin-bottom:48px}
.highlight .hl-text{font-weight:900;line-height:1.32;text-align:center;text-shadow:0 8px 30px rgba(0,0,0,.5)}
.highlight .hl-row{white-space:nowrap}
.highlight .hl-em{position:relative;display:inline-block;white-space:nowrap;margin:0 .06em}
.highlight .hl-et{position:relative;z-index:1;display:inline-block}
.highlight .hl-mark{position:absolute;z-index:0;overflow:visible}
.highlight .hl-mark path{fill:none;stroke:var(--accent);stroke-linecap:round;stroke-linejoin:round}
.highlight [data-m=highlight] .hl-mark{left:-3%;top:-2%;width:106%;height:104%}
.highlight [data-m=highlight] .hl-et{text-shadow:none}
.highlight [data-m=underline] .hl-mark{left:-2%;bottom:-14%;width:104%;height:22%;z-index:2}
.highlight [data-m=circle] .hl-mark{left:-12%;top:-24%;width:124%;height:148%;z-index:2}
.highlight [data-m=scribble] .hl-mark{left:-2%;top:12%;width:104%;height:76%;z-index:2}
.highlight .hl-em:not([data-m=highlight]) .hl-et{color:var(--accent)}
.highlight .hl-em[data-m=scribble] .hl-et{color:#fff;opacity:.8}
.highlight .hl-sub{margin-top:56px;font-size:52px;font-weight:800;line-height:1.4;opacity:.92;text-align:center;text-wrap:balance;max-width:920px}
.progress .pg-num{display:flex;align-items:baseline;justify-content:center;font-weight:900;color:var(--accent);text-shadow:0 10px 50px rgba(0,0,0,.5);font-variant-numeric:tabular-nums}
.progress .val{font-size:260px;line-height:1}
.progress .pre,.progress .suf{font-size:110px;margin:0 8px}
.progress .pg-track{position:relative;width:900px;height:44px;margin-top:34px;border-radius:22px;background:rgba(255,255,255,.1);overflow:hidden;border:2px solid rgba(255,255,255,.12)}
.progress .pg-fill{position:absolute;inset:0;border-radius:22px;background:linear-gradient(90deg,var(--accent2),var(--accent));transform-origin:left center;transform:scaleX(0)}
.progress .pg-ringw{position:relative;width:540px;height:540px;display:flex;align-items:center;justify-content:center}
.progress .pg-ring{position:absolute;inset:0;border-radius:50%;--p:0;background:conic-gradient(var(--accent) calc(var(--p) * 1%),rgba(255,255,255,.1) 0);-webkit-mask:radial-gradient(farthest-side,transparent calc(100% - 50px),#000 calc(100% - 49px));mask:radial-gradient(farthest-side,transparent calc(100% - 50px),#000 calc(100% - 49px))}
.progress .pg-label{margin-top:44px;font-size:62px;font-weight:900;text-align:center;line-height:1.35;text-wrap:balance;max-width:940px}
.progress .pg-cap{margin-top:22px;font-size:42px;font-weight:700;opacity:.7;text-align:center;text-wrap:balance;max-width:940px}
.split .heading{font-size:60px;font-weight:900;margin-bottom:34px;text-align:center}
.split .sp-wrap{position:relative;width:960px;height:660px;border-radius:40px;overflow:hidden;border:3px solid rgba(255,255,255,.16);box-shadow:0 30px 80px rgba(0,0,0,.45)}
.split .sp-layer{position:absolute;inset:0}
.split .sp-before{background:rgba(255,255,255,.05)}
.split .sp-after{background:color-mix(in srgb,var(--accent) 16%,var(--bg2));clip-path:inset(0% 0% 0% 100%)}
.split .sp-half{position:absolute;top:0;bottom:0;width:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:0 26px;text-align:center}
.split .sp-half.l{left:0}.split .sp-half.r{right:0}
.split .sp-tag{font-size:42px;font-weight:900;padding:8px 26px;border-radius:14px;background:rgba(255,255,255,.16);margin-bottom:34px;white-space:nowrap}
.split .sp-after .sp-tag{background:var(--accent);color:#111}
.split .sp-val{font-weight:900;line-height:1.05;white-space:nowrap}
.split .sp-after .sp-val{color:var(--accent);text-shadow:0 10px 40px rgba(0,0,0,.4)}
.split .sp-note{margin-top:30px;font-size:44px;font-weight:800;line-height:1.35;text-wrap:balance}
.split .sp-div{position:absolute;top:0;bottom:0;left:100%;width:8px;margin-left:-4px;background:var(--accent);opacity:0;box-shadow:0 0 30px rgba(0,0,0,.4)}
.split .sp-knob{position:absolute;bottom:44px;left:50%;width:96px;height:96px;margin-left:-48px;border-radius:50%;background:var(--accent);color:#111;font-size:52px;font-weight:900;display:flex;align-items:center;justify-content:center}
.tag.col{color:#111;background:var(--accent);padding:8px 22px;border-radius:14px;letter-spacing:2px;top:170px}
/* 平台安全区（10-16，跨平台：左72 右180 上160 下300，主视觉底边≤1450）：顶部 160px 是抖音「推荐/搜索」栏，
   右侧 180px（y 700–1620）是头像/点赞/评论/收藏/分享按钮列。场景内容按 960px 宽设计，这里整体缩到 828px 放进 x 72–900，
   不改各场景自己的尺寸；.safe 是静态变换，GSAP 的推近/入场动画在 .stage/.cam/.inner 上，互不影响。片尾模板本来就在安全区内，不套。 */
.safe{position:absolute;inset:0;transform:translateX(-54px) scale(.8625);transform-origin:540px 860px}
.cap{position:absolute;inset:auto;left:60px;right:130px;top:1300px;height:260px;display:flex;align-items:flex-start;justify-content:center}
.capin .cl{display:inline-block}
.capin{text-wrap:balance;font-size:62px;font-weight:900;line-height:1.35;text-align:center;color:#fff;-webkit-text-stroke:2px rgba(0,0,0,.85);paint-order:stroke fill;text-shadow:0 6px 18px rgba(0,0,0,.8)}
#prog{position:absolute;left:0;bottom:0;height:12px;width:100%;background:var(--accent);transform-origin:left center}
"""


HOOK_FIRST_MAX = 16     # hook 第一句最多几个字（约 2 秒）
HOOK_FIRST_SEC = 2.0    # hook 第一句最多念几秒
HOOK_MAX_SEC = 4.0      # hook 场景最长几秒（0–2 钩子 + 2–4 确认）
SCENE_MAX_LINES = 4     # 单个场景口播最多几句


def _say_len(s):
    """体检用的字数：汉字、数字各算 1 个（数字念出来往往更长），英文字母 2 个算 1 个，标点空格不算。"""
    return sum(.5 if c.isascii() and c.isalpha() else 1 for c in plain(s)
               if not c.isspace() and unicodedata.category(c)[0] not in 'PSZ')


def check_script(spec):
    """开头体检 + 中段节奏（看稿子，不用配音）。只返回警告文字，不阻断渲染。"""
    w, scenes = [], spec.get('scenes') or []
    if not scenes:
        return ['spec 里没有 scenes']
    first = scenes[0]
    if first.get('type', 'image') != 'hook':
        w.append(f'[开头体检] 第 1 个场景是 {first.get("type", "image")}，不是 hook：第 0 秒没有大字钩子')
    elif first.get('lines'):
        n = _say_len(first['lines'][0])
        if n > HOOK_FIRST_MAX:
            w.append(f'[开头体检] hook 第一句「{plain(first["lines"][0])}」{n:g} 字，超过 {HOOK_FIRST_MAX} 字，2 秒内念不完；只留结论/冲突，其余挪到第 2 句')
    for i, sc in enumerate(scenes):
        if len(sc.get('lines', [])) > SCENE_MAX_LINES:
            w.append(f'[节奏体检] 场景{i}（{sc.get("type", "image")}）口播 {len(sc["lines"])} 句，超过 {SCENE_MAX_LINES} 句，一个画面停太久容易流失：拆成两个场景')
    return w


def check_timing(spec):
    """配音合成后、渲染前：按真实时长再查一次开头。返回（警告列表, 一行摘要）。"""
    first = spec['scenes'][0]
    if first.get('type', 'image') != 'hook' or not first.get('_speech'):
        return [], ''
    w = []
    st, en = first['_speech'][0]
    hook_d = first['_end'] - first['_start']
    if en - st > HOOK_FIRST_SEC:
        tip = '删字（去掉逗号停顿也能省 0.2 秒）' if first.get('rate') else '删字，或给 hook 场景单独写 "rate": "+15%"'
        w.append(f'[开头体检] hook 第一句念了 {en - st:.2f} 秒（要 ≤{HOOK_FIRST_SEC:g} 秒）：{tip}')
    if hook_d > HOOK_MAX_SEC:
        w.append(f'[开头体检] hook 场景 {hook_d:.2f} 秒（要 ≤{HOOK_MAX_SEC:g} 秒）：hook 最多 2 句，证据和背景挪到下一个场景')
    nxt = spec['scenes'][1]['_start'] if len(spec['scenes']) > 1 else first['_end']
    return w, f'[开头体检] 第一句 {st:.2f}–{en:.2f}s，hook 0–{first["_end"]:.2f}s，第 2 个场景 {nxt:.2f}s 开始'


def build(spec_path, draft=False, render=True, check_only=False):
    spec_path = pathlib.Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text())
    import edit_fx
    edit_fx.ensure_follow_line(spec)   # 片尾统一引导关注：cta 里没提关注就补一句带理由的引导
    style = None
    if spec.get('style'):   # 剪辑风格预设（10-16，可选，scripts/styles/）：spec 顶层写 "style" 才加载；不写完全走默认。回退：删这 5 行和写 index.html 前那 2 行
        import styles
        style = styles.load(spec)
        style.prepare(spec)
    warns = check_script(spec)
    for x in warns:
        print(x, file=sys.stderr)
    if check_only:
        print('[体检] 稿子层面没发现问题（配音时长要合成后才查得到）' if not warns else f'[体检] {len(warns)} 条警告', file=sys.stderr)
        return None
    sid = spec.get('id', spec_path.stem)
    work = spec_path.parent / f'{sid}_hf'
    (work / 'assets').mkdir(parents=True, exist_ok=True)
    for f in ('gsap.min.js', 'NotoSansSC.ttf'):
        dst = work / 'assets' / f
        if not dst.exists():
            try:
                os.link(TPL / f, dst)
            except OSError:
                shutil.copy(TPL / f, dst)
    shutil.copytree(SFX_DIR, work / 'assets/sfx', dirs_exist_ok=True)   # 音效库新增文件（如 *-dry.mp3）也同步进旧工作目录
    lines, total = build_audio(spec, work)
    tw, summary = check_timing(spec)
    for x in ([summary] if summary else []) + tw:
        print(x, file=sys.stderr)
    for sc in spec['scenes']:
        sc['_total'] = total
    import edit_fx
    from avatar_layer import build_layer
    edit_fx.prepare(spec)   # J-cut：画面比配音早 0.18s；记录下一个场景类型
    # 示例作者动漫口播形象（左下角，跟配音对口型；素材见 scripts/make_avatar.py，图层见 scripts/avatar_layer.py）
    av = build_layer(spec, work, lines, total)
    from sticker_layer import build_stickers   # 示例作者表情贴纸（场景里写 "sticker": "我悟了"，见 scripts/sticker_layer.py）
    stk = build_stickers(spec, work)
    last = len(spec['scenes']) - 1
    is_ec = spec['scenes'][last].get('type') in ('cta', 'endcard')   # 最后一个 cta 统一套片尾模板
    if is_ec and not av:
        (work / 'assets/avatar').mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / 'assets/avatar/creator-avatar-1024.jpg', work / 'assets/avatar/endcard.jpg')
    # 底色 v2：从紫蓝渐变（AI 模板感最重的配色之一）改成接近中性的深墨色，只留一个暖色强调
    th = {'bg1': '#0d1016', 'bg2': '#171b24', 'accent': '#FFD60A', 'accent2': '#5AB0FF', **spec.get('theme', {})}
    tlines = spec['title_top'].split('\n') + ['']
    col = COLUMNS.get(spec.get('column', ''))
    tag_html = f'<div class="tag col">{esc(spec.get("tag") or col)}</div>' if col else f'<div class="tag">{esc(spec.get("tag","今日AI"))}</div>'
    scenes = ''.join(
        f'<div id="s{i}" class="clip scene" data-start="{sc["_start"]:.3f}" data-duration="{sc["_end"]-sc["_start"]:.3f}" data-track-index="1"><div class="stage"><div class="cam">'
        f'{edit_fx.endcard_html(spec, sc, bool(av)) if (is_ec and i == last) else "<div class=safe>" + scene_html(sc, i, work) + "</div>"}</div></div></div>'
        for i, sc in enumerate(spec['scenes']))
    groups = cap_groups(lines, sil=_silences(work / 'audio/voice.wav', noise='-40dB', d=0.07))
    caps = ''.join(
        f'<div id="c{k}" class="clip cap" data-start="{g["start"]:.3f}" data-duration="{g["dur"]:.3f}" data-track-index="3"><div class="capin">{g["html"]}</div></div>'
        for k, g in enumerate(groups))
    js = '\n'.join(edit_fx.endcard_js(sc, i, bool(av)) if (is_ec and i == last) else scene_js(sc, i) for i, sc in enumerate(spec['scenes']))
    sfx = sfx_tags(spec)   # 放在 scene_js 之后：要用到 beats / 印章时间
    if is_ec:
        sfx += edit_fx.endcard_sfx(spec['scenes'][last])
    if av:
        js += '\n' + av['js']
    if stk:
        js += '\n' + stk['js']
    js += '\n' + edit_fx.punch_js(spec, lines) + '\n' + edit_fx.caption_pop(groups)
    # 字幕：一次只显示一组（6–12 字），跟读式逐字点亮（karaoke）
    for k, g in enumerate(groups):
        js += f'\ntl.fromTo("#c{k} .capin",{{opacity:0,y:12}},{{opacity:1,y:0,duration:.18,ease:"power3.out"}},{g["start"]:.3f});'
        js += f'\ntl.fromTo("#c{k} .k",{{opacity:.45}},{{opacity:1,duration:.06,stagger:{g["dur"] * .8 / max(g["n"], 1):.3f}}},{g["start"]:.3f});'
    # 顶部双行标题：hook 期间藏起来（hook 大字就是标题，两个叠着挤），hook 一结束、第 2 个场景开始时再出现
    t0 = spec['scenes'][0]['_end'] if spec['scenes'][0].get('type') == 'hook' else 0
    page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><script src="assets/gsap.min.js"></script>
<style>:root{{--bg1:{th['bg1']};--bg2:{th['bg2']};--accent:{th['accent']};--accent2:{th['accent2']}}}{CSS}{edit_fx.EC_CSS}{av['css'] if av else ''}{stk['css'] if stk else ''}</style></head><body>
<div id="root" class="{'has-av' if av else ''}" data-composition-id="main" data-width="1080" data-height="1920" data-duration="{total:.3f}" data-fps="30">
<div class="grid"></div><div id="b1" class="blob"></div><div class="ghost">{esc(spec.get("ghost") or col or "AI")}</div>
{scenes}
<div class="brand">{esc(spec.get('brand') or ('示例办公课' if spec.get('account') == 'office' else '示例聊AI'))}</div>{tag_html}
<div class="title"><span class="tl1">{esc(tlines[0])}</span><span class="tl2">{esc(tlines[1])}</span></div>
{av['html'] if av else ''}
{stk['html'] if stk else ''}
{caps}
<div id="prog"></div>
<audio id="narration" src="assets/narration.m4a" data-start="0" data-duration="{total:.3f}" data-volume="1" data-track-index="4"></audio>
{sfx}
</div>
<script>
var tl=gsap.timeline({{paused:true}});
tl.fromTo("#b1",{{x:0,y:0}},{{x:220,y:-160,duration:{total:.3f},ease:"sine.inOut"}},0);
tl.fromTo(".ghost",{{xPercent:0}},{{xPercent:-18,duration:{total:.3f},ease:"none"}},0);
tl.fromTo(".title .tl1",{{opacity:0,y:-30}},{{opacity:1,y:0,duration:.5,ease:"power3.out"}},{t0:.3f});
tl.fromTo(".title .tl2",{{opacity:0,y:-20}},{{opacity:1,y:0,duration:.5,ease:"power3.out"}},{t0+0.2:.3f});
tl.fromTo("#prog",{{scaleX:0}},{{scaleX:1,duration:{total:.3f},ease:"none"}},0);
{js}
window.__timelines["main"]=tl;
</script></body></html>"""
    if style:   # 剪辑风格：加 CSS/背景/转场层，改写入场、转场、强调和字幕动效（scripts/styles/__init__.py）
        page = style.apply(page, spec, work, lines, groups, total, bool(av))
    (work / 'index.html').write_text(page)
    (work / 'timeline.json').write_text(json.dumps({'total': total, 'lines': lines}, ensure_ascii=False, indent=1))
    out = spec_path.parent / f'{sid}.mp4'
    if render:
        cmd = ['npx', '--yes', f'hyperframes@{HF_VERSION}', 'render', str(work), '-o', str(out), '-f', '30', '-q', 'draft' if draft else 'standard', '--quiet']
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(work))
        (work / 'render.log').write_text(r.stdout + '\n' + r.stderr)
        if r.returncode != 0 or not out.exists():
            raise SystemExit(f'render failed, see {work}/render.log')
        # 封面：作图 API 一体设计（标题+插画，统一系列画风，scripts/make_cover.py ai_cover）。
        # 生成后必须亲眼核对标题有没有错字；有错就删掉 <id>-cover-raw.png 重跑，或用 cover_attempt 换一张。
        cov = spec_path.parent / f'{sid}-cover.jpg'
        hook = spec['scenes'][0] if spec['scenes'][0].get('type') == 'hook' else {}
        ctitle = spec.get('cover_title') or plain(hook.get('big', '')) or spec['title_top']
        subject = spec.get('cover_subject') or f'和「{spec["title_top"].replace(chr(10), "，")}」有关的一个具体物件或场景'
        acct, attempt = spec.get('account', 'creator'), int(spec.get('cover_attempt', 0))
        try:
            from make_cover import ai_cover, compose_ai_cover_adaptive
            _, _, raw = ai_cover(ctitle, spec.get('column', '热点'), subject, cov, spec.get('series'), attempt, acct,
                                 theme=spec.get('cover_theme'), pose=spec.get('cover_pose'))
            if acct == 'office':   # 浅色设计图补边不压暗，去掉 3:4 两侧、9:16 上下的灰绿脏边（封面规范.md 3.4），不再调作图 API
                compose_ai_cover_adaptive(raw, cov)
        except Exception as ex:  # 兜底：取开场标题动画完成后的一帧
            print(f'[cover] 作图封面失败，改用视频帧：{ex}', file=sys.stderr)
            at = spec.get('cover_at', min(1.6, spec['scenes'][0]['_end'] - 0.3))
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(at), '-i', str(out), '-frames:v', '1', '-q:v', '2', str(cov)], check=True)
        # 要发 B站 / 知乎题图的片子在 spec 写 "cover_wide": true：作图 API 横版直出 16:9（标题在左、主体在右，封面规范.md 3.3），
        # 产出 <id>-cover-wide.jpg，post-bilibili.json 的 cover_169 指向它。竖图补边的 -169.jpg 推荐流里字太小，B站不再用。
        if spec.get('cover_wide'):
            try:
                from make_cover import ai_cover_wide
                ai_cover_wide(spec.get('cover_title_wide') or ctitle, spec.get('column', '热点'), subject, spec_path.parent / f'{sid}-cover-wide.jpg',
                              '16:9', spec.get('series'), attempt, acct, theme=spec.get('cover_theme'), pose=spec.get('cover_pose'))
            except Exception as ex:
                print(f'[cover] 横版封面失败，B站先用 9:16 封面，记得补：{ex}', file=sys.stderr)
    return out


if __name__ == '__main__':
    out = build(sys.argv[1], draft='--draft' in sys.argv, render='--no-render' not in sys.argv, check_only='--check' in sys.argv)
    if out:
        print(out)
