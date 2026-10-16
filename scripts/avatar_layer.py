#!/usr/bin/env python3
"""示例作者动漫口播形象图层（make_motion 用）。v2（10-16）

素材来自 scripts/make_avatar.py（assets/avatar/creator-talk/）：
  base.png              闭嘴睁眼的半身像
  mouth_*.png           只有嘴那一块的局部贴片：open(啊) mid(呃) oh(哦) ee(衣) oo(乌)
  eyes_closed.png       眨眼贴片
  face_*.png            眉眼表情贴片：surprised / thinking / worried / wink / happy
口型（用户：要跟着字幕的语言动，像真人说话）：按每个字的拼音韵母选口型，b/p/m/f 开头先闭一下嘴；
  每个字的时间 = 这句话的发声段（逐帧响度 > 阈值）按字均分，和字幕同一套时间轴；停顿处闭嘴。
表情（用户：别只会眨眼）：按句子内容自动挑——问句=思考+歪头+「？」，意外/数字=惊讶+弹一下+「！」，
  坏消息=担心+摇头+汗滴，好消息=开心+跳一下+闪光，给建议=眨眼+前倾；场景可写 "face" 指定。
位置（用户：别挡字幕）：字幕整行在上（y≈1255），示例作者在字幕下方左下角（y 1345–1615），上下错开。
spec 写 "avatar": false 关掉。示例服务「全驱数字人」（百炼灵动人像）修好后可换成真对口型视频。
"""
import math, pathlib, re, shutil, subprocess
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'assets/avatar/creator-talk'
AV_LEFT, AV_TOP, AV_SIZE = 10, 1338, 320
CAP_TOP = 1255
MOUTHS = {'A': 'mouth_open', 'E': 'mouth_mid', 'O': 'mouth_oh', 'I': 'mouth_ee', 'U': 'mouth_oo'}
FACES = ('surprised', 'thinking', 'worried', 'wink', 'happy')

CSS = f"""
#av{{position:absolute;left:{AV_LEFT}px;top:{AV_TOP}px;width:{AV_SIZE}px;height:{AV_SIZE}px;transform-origin:50% 100%;
  -webkit-mask-image:linear-gradient(to bottom,#000 82%,transparent 100%);mask-image:linear-gradient(to bottom,#000 82%,transparent 100%)}}
#av .av-plate{{position:absolute;left:30px;right:30px;top:50px;bottom:-16px;border-radius:50%;background:radial-gradient(closest-side,rgba(255,214,10,.22),transparent);filter:blur(6px)}}
#av .av-body{{position:absolute;inset:0;transform-origin:50% 92%}}
#av img{{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}}
#av .av-ov{{opacity:0}}
#av-sym{{position:absolute;left:{AV_LEFT + AV_SIZE - 24}px;top:{AV_TOP + 40}px;width:90px;height:90px;pointer-events:none}}   /* 头部右侧，低于字幕行 CAP_TOP+78，人物和符号都不挡字 */
#av-sym > *{{position:absolute;inset:0;opacity:0;transform-origin:30% 80%}}
#av-sym .sym-t{{font-size:84px;font-weight:900;color:var(--accent);-webkit-text-stroke:4px #111;paint-order:stroke fill;line-height:90px;text-align:center}}
.has-av .cap{{left:60px;right:130px;top:{CAP_TOP}px}}
.has-av .capin{{font-size:58px;white-space:nowrap}}
"""

SWEAT = ('<svg viewBox="0 0 90 90"><path d="M45 8 C58 32 70 46 70 60 A25 25 0 0 1 20 60 C20 46 32 32 45 8Z" fill="#7cc8ff" stroke="#111" stroke-width="5"/>'
         '<ellipse cx="36" cy="58" rx="6" ry="10" fill="#e6f5ff"/></svg>')
SPARK = ('<svg viewBox="0 0 90 90"><path d="M45 6 L52 38 L84 45 L52 52 L45 84 L38 52 L6 45 L38 38Z" fill="#FFD60A" stroke="#111" stroke-width="4"/>'
         '<path d="M74 10 L77 22 L89 25 L77 28 L74 40 L71 28 L59 25 L71 22Z" fill="#fff" stroke="#111" stroke-width="3"/></svg>')
SYMS = {'q': '<div class="sym-t sym-q">?</div>', 'ex': '<div class="sym-t sym-ex">!</div>',
        'sweat': f'<div class="sym-sweat">{SWEAT}</div>', 'spark': f'<div class="sym-spark">{SPARK}</div>'}
FACE_FX = {'thinking': 'q', 'surprised': 'ex', 'worried': 'sweat', 'happy': 'spark', 'wink': None}

RE_Q = re.compile(r'[？?]')
RE_SUR = re.compile(r'！|竟然|居然|没想到|第一次|足足|整整|全额|翻倍|暴涨|\d{3,}|\d+(个)?小时')
RE_NEG = re.compile(r'崩|停了|挂了|没份|一个字没提|翻车|坑|故障|失败|漏掉|不行|太贵|亏|卡住|出问题|麻烦|焦虑')
RE_POS = re.compile(r'大方|全返|能用|省下|赚|收入|稳|好用|值得|免费|恢复|搞定|接上|成功|划算')
RE_ADV = re.compile(r'建议|记住|教你|直接|至少|所以')

# 韵母 → 口型
FINAL_SHAPE = {}
for f in ('a', 'ia', 'ua', 'ai', 'uai', 'ao', 'iao', 'an', 'uan', 'ang', 'iang', 'uang', 'van'):
    FINAL_SHAPE[f] = 'A'
for f in ('o', 'uo', 'ou', 'iou', 'iu', 'ong', 'iong'):
    FINAL_SHAPE[f] = 'O'
for f in ('e', 'ie', 've', 'ue', 'ei', 'uei', 'ui', 'en', 'eng', 'er', 'ian', 'uen', 'un'):
    FINAL_SHAPE[f] = 'E'
for f in ('i', 'in', 'ing', '-i'):
    FINAL_SHAPE[f] = 'I'
for f in ('u', 'v', 'vn', 'ü', 'ün'):
    FINAL_SHAPE[f] = 'U'
DIGIT_SHAPE = {'0': 'I', '1': 'I', '2': 'E', '3': 'A', '4': 'I', '5': 'U', '6': 'O', '7': 'I', '8': 'A', '9': 'O'}
LIP_INITIALS = ('b', 'p', 'm', 'f')


def _syllables(text):
    """一句话 → [(口型, 是否先闭嘴, 权重)]。标点不算音节。"""
    from pypinyin import pinyin, Style
    out = []
    for tok in re.findall(r'[A-Za-z]+|\d|[一-鿿]', re.sub(r'\*\*|\[停\s*[\d.]+\s*秒?\]', '', text)):
        if tok.isdigit():
            out.append((DIGIT_SHAPE[tok], tok in '8', 1.0))
        elif tok.isascii():
            n = max(1, round(len(tok) / 2.2))
            out += [('E' if k % 2 else 'A', tok[0].lower() in 'bpmf' and k == 0, 1.0) for k in range(n)]
        else:
            fin = pinyin(tok, style=Style.FINALS, strict=True)[0][0] or 'e'
            ini = pinyin(tok, style=Style.INITIALS, strict=False)[0][0]
            out.append((FINAL_SHAPE.get(fin, 'E'), ini in LIP_INITIALS, 1.0))
    return out


def _db_track(voice_wav, total, fps):
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(voice_wav), '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    hop = 16000 / fps
    n = int(math.ceil(total * fps))
    db = np.full(n, -90.0)
    for i in range(n):
        a, b = int(max(0, (i - 0.5) * hop)), int(min(len(x), (i + 1.5) * hop))
        if b > a:
            db[i] = 20 * math.log10(float(np.sqrt(np.mean(x[a:b] ** 2))) + 1e-9)
    voiced = db[db > -50]
    ref = float(np.percentile(voiced, 92)) if len(voiced) else -20.0
    return db, ref


def viseme_track(lines, voice_wav, total, fps=30):
    """逐帧口型：None=闭嘴，其余为 A/E/O/I/U。每句话的音节按发声帧均分。"""
    db, ref = _db_track(voice_wav, total, fps)
    n = len(db)
    track = [None] * n
    gate = ref - 26
    for ln in lines:
        f0, f1 = int(ln['start'] * fps), min(n, int((ln['start'] + ln['dur']) * fps))
        frames = [i for i in range(f0, f1) if db[i] > gate]
        syl = _syllables(ln['text'])
        if not frames or not syl:
            continue
        per = len(frames) / len(syl)
        for k, (shape, lip, _) in enumerate(syl):
            seg = frames[int(k * per):max(int((k + 1) * per), int(k * per) + 1)]
            for j, i in enumerate(seg):
                if lip and j < max(1, len(seg) // 4):
                    track[i] = None                       # b/p/m/f：先闭一下嘴
                elif db[i] < ref - 16 and shape == 'A':
                    track[i] = 'E'                        # 轻声一点的「啊」张小一点
                else:
                    track[i] = shape
    for i in range(1, n - 1):                             # 去掉单帧抖动
        if track[i - 1] == track[i + 1] != track[i]:
            track[i] = track[i - 1]
    return track


def pick_face(text, scene_face=None, last=None):
    if scene_face:
        return scene_face
    t = re.sub(r'\*\*', '', text)
    face = ('thinking' if RE_Q.search(t) else 'surprised' if RE_SUR.search(t) else 'worried' if RE_NEG.search(t)
            else 'happy' if RE_POS.search(t) else 'wink' if RE_ADV.search(t) else None)
    return None if face == last == 'wink' else face


def build_layer(spec, work, lines, total, fps=30):
    """返回 {'html','css','js'}；素材不全或 spec 关掉时返回 None。"""
    if spec.get('avatar') is False or not (SRC / 'base.png').exists():
        return None
    voice_wav = work / 'audio/voice.wav'
    if not voice_wav.exists():
        return None
    dst = work / 'assets/avatar'
    dst.mkdir(parents=True, exist_ok=True)
    import json as _json
    mode = spec.get('avatar_mode') or _json.loads((ROOT / 'config/schedule.json').read_text()).get('avatar_mode', 'local')
    if mode in ('s2v', 'retalk'):   # 真对口型：retalk=百炼 VideoRetalk（默认，0.08 元/秒）；s2v=万象 wan2.2-s2v（0.5 元/秒）；失败退回本地按字口型
        try:
            from s2v_avatar import make, make_retalk
            webm, info = (make_retalk if mode == 'retalk' else make)(work, lines, total)
            spec['_s2v'] = info
            return _s2v_layer(spec, lines, total, webm)
        except Exception as ex:
            import sys as _sys
            print(f'[avatar] s2v 真对口型失败，改用本地口型：{str(ex)[:200]}', file=_sys.stderr)
    mouths = {k: v for k, v in MOUTHS.items() if (SRC / f'{v}.png').exists()}
    faces = [f for f in FACES if (SRC / f'face_{f}.png').exists()]
    files = ['base', 'eyes_closed'] + list(mouths.values()) + [f'face_{f}' for f in faces]
    for k in files:
        if (SRC / f'{k}.png').exists():
            shutil.copy(SRC / f'{k}.png', dst / f'{k}.png')
    ov = ''.join(f'<img id="av-{v}" class="av-ov" src="assets/avatar/{v}.png" alt=""/>' for v in mouths.values())
    ov += ''.join(f'<img id="av-f-{f}" class="av-ov" src="assets/avatar/face_{f}.png" alt=""/>' for f in faces)
    html = ('<div id="av"><div class="av-plate"></div><div class="av-body">'
            '<img src="assets/avatar/base.png" alt=""/>' + ov +
            '<img id="av-eyes" class="av-ov" src="assets/avatar/eyes_closed.png" alt=""/>'
            '</div></div><div id="av-sym">' + ''.join(SYMS.values()) + '</div>')
    js = [f'tl.fromTo("#av",{{opacity:0,x:-80}},{{opacity:1,x:0,duration:.5,ease:"power3.out"}},0.1);',
          f'tl.fromTo("#av .av-body",{{scaleY:1}},{{scaleY:1.012,duration:1.7,yoyo:true,repeat:{max(1, int(total / 1.7))},ease:"sine.inOut"}},0);']
    # 口型
    try:
        track = viseme_track(lines, voice_wav, total, fps)
    except ImportError:          # 没装 pypinyin：退回按音量开合
        db, ref = _db_track(voice_wav, total, fps)
        track = ['A' if d > ref - 7 else 'E' if d > ref - 19 else None for d in db]
    prev = None
    for i, s in enumerate(track):
        s = s if s in mouths else (('A' if s == 'O' else 'E') if s else None)   # 缺哪张口型就用相近的
        if s != prev:
            t = i / fps
            js.append(''.join(f'tl.set("#av-{v}",{{opacity:{1 if k == s else 0}}},{t:.3f});' for k, v in mouths.items()))
            prev = s
    # 表情 + 头部动作 + 漫画符号（逐句）
    busy, last_face, last_sym = [], None, -99.0
    scene_face = {}
    for i, sc in enumerate(spec['scenes']):
        if sc.get('face'):
            scene_face[i] = sc['face']
    for k, ln in enumerate(lines):
        face = pick_face(ln['text'], scene_face.get(ln['scene']), last_face)
        a, b = ln['start'] + .05, ln['start'] + ln['dur'] - .12
        if not face or b - a < .5:
            last_face = None
            if k:   # 普通句子：轻轻点一下头
                js.append(f'tl.fromTo("#av .av-body",{{rotation:0}},{{rotation:-2.2,duration:.18,yoyo:true,repeat:1,ease:"sine.inOut"}},{ln["start"]:.3f});')
            continue
        last_face = face
        if face in faces:
            js.append(f'tl.set("#av-f-{face}",{{opacity:1}},{a:.3f});tl.set("#av-f-{face}",{{opacity:0}},{b:.3f});')
            busy.append((a - .1, b + .1))
        if face == 'thinking':
            js.append(f'tl.to("#av .av-body",{{rotation:-5,duration:.3,ease:"power2.out"}},{a:.3f});tl.to("#av .av-body",{{rotation:0,duration:.3,ease:"power2.inOut"}},{b:.3f});')
        elif face == 'surprised':
            js.append(f'tl.fromTo("#av .av-body",{{y:0}},{{y:-18,duration:.16,yoyo:true,repeat:1,ease:"power2.out"}},{a:.3f});')
        elif face == 'worried':
            js.append(f'tl.fromTo("#av .av-body",{{x:0}},{{x:5,duration:.07,yoyo:true,repeat:5,ease:"sine.inOut"}},{a:.3f});')
        elif face == 'happy':
            js.append(f'tl.fromTo("#av .av-body",{{y:0}},{{y:-12,duration:.14,yoyo:true,repeat:3,ease:"power1.out"}},{a:.3f});')
        elif face == 'wink':
            js.append(f'tl.to("#av .av-body",{{rotation:3,scale:1.04,duration:.25,ease:"power2.out"}},{a:.3f});tl.to("#av .av-body",{{rotation:0,scale:1,duration:.3,ease:"power2.inOut"}},{b:.3f});')
        sym = FACE_FX.get(face)
        if sym and a - last_sym > 5:
            sel = {'q': '.sym-q', 'ex': '.sym-ex', 'sweat': '.sym-sweat', 'spark': '.sym-spark'}[sym]
            js.append(f'tl.fromTo("#av-sym {sel}",{{opacity:0,scale:.2,rotation:-15}},{{opacity:1,scale:1,rotation:0,duration:.28,ease:"back.out(2.5)"}},{a:.3f});')
            js.append(f'tl.to("#av-sym {sel}",{{opacity:0,y:-14,duration:.3,ease:"power2.in"}},{min(b, a + 1.6):.3f});')
            last_sym = a
    # 眨眼：确定性伪随机间隔，避开表情（表情本身改了眼睛）
    t, seed = 1.4, sum(map(ord, spec.get('id', 'x')))
    while t < total - 0.5:
        if not any(x <= t <= y for x, y in busy):
            js.append(f'tl.set("#av-eyes",{{opacity:1}},{t:.3f});tl.set("#av-eyes",{{opacity:0}},{t + 0.13:.3f});')
        seed = (seed * 1103515245 + 12345) % 2 ** 31
        t += 2.2 + (seed % 2600) / 1000
    return {'html': html, 'css': CSS, 'js': '\n'.join(js)}


def _s2v_layer(spec, lines, total, webm):
    """真对口型版：左下角放 s2v 生成的透明视频（嘴型、眨眼、头部动作都由模型生成），保留漫画符号和入场动作。"""
    html = ('<div id="av"><div class="av-plate"></div><div class="av-body">'
            f'<video id="av-vid" src="assets/avatar/{webm.name}" data-start="0" data-duration="{total:.3f}" data-track-index="11" muted playsinline></video>'
            '</div></div><div id="av-sym">' + ''.join(SYMS.values()) + '</div>')
    css = CSS + "#av video{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}"
    js = [f'tl.fromTo("#av",{{opacity:0,x:-80}},{{opacity:1,x:0,duration:.5,ease:"power3.out"}},0.1);']
    last_face, last_sym = None, -99.0
    for ln in lines:
        face = pick_face(ln['text'], None, last_face)
        last_face = face
        sym = FACE_FX.get(face) if face else None
        a, b = ln['start'] + .05, ln['start'] + ln['dur'] - .12
        if sym and a - last_sym > 5 and b - a > .5:
            sel = {'q': '.sym-q', 'ex': '.sym-ex', 'sweat': '.sym-sweat', 'spark': '.sym-spark'}[sym]
            js.append(f'tl.fromTo("#av-sym {sel}",{{opacity:0,scale:.2,rotation:-15}},{{opacity:1,scale:1,rotation:0,duration:.28,ease:"back.out(2.5)"}},{a:.3f});')
            js.append(f'tl.to("#av-sym {sel}",{{opacity:0,y:-14,duration:.3,ease:"power2.in"}},{min(b, a + 1.6):.3f});')
            last_sym = a
    return {'html': html, 'css': css, 'js': '\n'.join(js)}
