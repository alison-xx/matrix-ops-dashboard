#!/usr/bin/env python3
"""竖版口播视频合成：spec.json -> 配音 + 画面 + 字幕 + 封面。

spec 示例见 templates/video_spec.example.json。
用法: .venv/bin/python scripts/make_video.py <spec.json> [--no-render]
"""
import json, math, pathlib, subprocess, sys, textwrap
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import font, gen_image, tts, probe_duration, ROOT
from pronunciation import audio_cache_key

W, H, FPS = 1080, 1920, 25
YELLOW = (255, 214, 10)
WHITE = (255, 255, 255)
INK = (18, 18, 22)
STYLE = ('editorial illustration, cinematic lighting, rich color, high detail, clean composition, '
         'vertical 2:3, no text, no letters, no watermark, no logo')


import re as _re
_TOKEN = _re.compile(r'[A-Za-z0-9][A-Za-z0-9.\-+%:/]*[分点号月日年个天元秒岁次万亿倍条位款家]?|\s+|.', _re.S)
_NO_HEAD = '，。！？、；：”’）》,.!?;:％%'


def _greedy(draw, tokens, fnt, max_w):
    lines, cur = [], ''
    for tk in tokens:
        if draw.textlength(cur + tk, font=fnt) <= max_w or not cur:
            cur += tk
        elif tk in _NO_HEAD or (len(tk) == 1 and tk in _NO_HEAD):
            cur += tk; lines.append(cur); cur = ''
        else:
            lines.append(cur.rstrip()); cur = tk.lstrip()
    if cur:
        lines.append(cur)
    return lines


def wrap(draw, text, fnt, max_w, balance=True):
    """按像素宽度断行：英文/数字整词不拆，标点不放行首，多行时尽量等长。"""
    out = []
    for para in text.split('\n'):
        tokens = _TOKEN.findall(para)
        lines = _greedy(draw, tokens, fnt, max_w)
        if balance and len(lines) == 2:
            # 两行时优先在标点后断开：选两行宽度差最小且都不超宽的标点位置
            best_cut, best_score = None, None
            for i, ch in enumerate(para[:-1]):
                if ch in '，、；：,;' and 0 < i < len(para) - 2:
                    a, b = para[:i + 1], para[i + 1:]
                    wa, wb = draw.textlength(a, font=fnt), draw.textlength(b, font=fnt)
                    if wa <= max_w and wb <= max_w:
                        score = abs(wa - wb)
                        if best_score is None or score < best_score:
                            best_cut, best_score = (a, b), score
            if best_cut and best_score < max_w * 0.55:
                out += list(best_cut)
                continue
        if balance and len(lines) > 1:
            total = draw.textlength(para, font=fnt)
            target = total / len(lines) + fnt.size * 0.6
            lo, best = target, lines
            while lo < max_w:
                trial = _greedy(draw, tokens, fnt, lo)
                if len(trial) == len(lines):
                    best = trial
                    break
                lo += fnt.size * 0.5
            lines = best
        out += lines
    return out


def stroke_text(draw, xy, text, fnt, fill, stroke=6, stroke_fill=(0, 0, 0), anchor='la'):
    draw.text(xy, text, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill, anchor=anchor)


def cover_fit(img, w, h):
    r = max(w / img.width, h / img.height)
    img = img.resize((math.ceil(img.width * r), math.ceil(img.height * r)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def gradient(h, top_alpha, bottom_alpha, color=(0, 0, 0)):
    g = Image.new('RGBA', (W, h))
    px = g.load()
    for y in range(h):
        a = int(top_alpha + (bottom_alpha - top_alpha) * y / max(h - 1, 1))
        for x in range(W):
            px[x, y] = (*color, a)
    return g


_GRAD = {}


def grad(key, h, a0, a1):
    if key not in _GRAD:
        _GRAD[key] = gradient(h, a0, a1)
    return _GRAD[key]


def card_background(scene, size=(W, H)):
    """无配图的文字卡场景：深色渐变 + 大数字/大字。"""
    bg = Image.new('RGB', size, (14, 16, 24))
    d = ImageDraw.Draw(bg)
    for y in range(size[1]):
        t = y / size[1]
        d.line([(0, y), (size[0], y)], fill=(int(14 + 30 * t), int(16 + 10 * t), int(24 + 60 * (1 - t))))
    big = scene.get('big', '')
    label = scene.get('label', '')
    if big:
        f = font(260 if len(big) <= 4 else 170, 'semibold')
        stroke_text(d, (size[0] // 2, 900), big, f, YELLOW, stroke=0, anchor='mm')
    if label:
        f2 = font(64, 'medium')
        for i, ln in enumerate(wrap(d, label, f2, 860)):
            d.text((size[0] // 2, 1090 + i * 86), ln, font=f2, fill=(230, 232, 240), anchor='mm')
    return bg


def scene_bg(scene, workdir, idx):
    if scene.get('type') == 'card':
        return card_background(scene)
    img_path = scene.get('image')
    if not img_path:
        img_path = workdir / f'scene{idx:02d}.png'
        gen_image(scene['prompt'] + ', ' + STYLE, img_path, size='1024x1536')
    img = Image.open(img_path).convert('RGB')
    return cover_fit(img, W, H)


def overlay_static(spec, scene):
    """场景静态层：顶部标题栏 + 场景小标题 + 品牌。"""
    o = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    o.alpha_composite(grad('top', 640, 235, 0), (0, 0))
    o.alpha_composite(grad('bottom', 900, 0, 225), (0, H - 900))
    d = ImageDraw.Draw(o)
    # 顶部钩子标题（全程常驻）
    ft = font(78, 'semibold')
    y = 150
    for ln in wrap(d, spec['title_top'], ft, 940)[:3]:
        hl = spec.get('title_highlight')
        stroke_text(d, (W // 2, y), ln, ft, YELLOW if hl and hl in ln else WHITE, stroke=5, anchor='ma')
        y += 100
    # 场景小标题
    if scene.get('headline'):
        fh = font(54, 'semibold')
        tw = d.textlength(scene['headline'], font=fh)
        x0 = (W - tw) // 2 - 28
        yb = y + 26
        d.rounded_rectangle([x0, yb, x0 + tw + 56, yb + 84], radius=14, fill=YELLOW)
        d.text((W // 2, yb + 42), scene['headline'], font=fh, fill=INK, anchor='mm')
    # 品牌
    fb = font(34, 'medium')
    d.text((60, 70), spec.get('brand', '示例聊AI'), font=fb, fill=(255, 255, 255, 210))
    if spec.get('tag'):
        d.text((W - 60, 70), spec['tag'], font=fb, fill=(255, 255, 255, 170), anchor='ra')
    return o


def caption_layer(text):
    o = Image.new('RGBA', (W, 420), (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    fc = font(66, 'semibold')
    lines = wrap(d, text, fc, 900)[:3]
    y = 420 - len(lines) * 92 - 20
    for ln in lines:
        stroke_text(d, (W // 2, y), ln, fc, WHITE, stroke=7, anchor='ma')
        y += 92
    return o


def build_audio(spec, workdir):
    voice = spec.get('voice', 'zh-CN-XiaoxiaoNeural')
    rate = spec.get('rate', '+8%')
    timeline, files, t = [], [], 0.25
    gap = spec.get('gap', 0.12)
    li = 0
    for si, sc in enumerate(spec['scenes']):
        s_start = t
        for line in sc['lines']:
            say = line.get('say') if isinstance(line, dict) else line
            show = line.get('show', say) if isinstance(line, dict) else line
            f = workdir / 'audio' / f'{li:03d}-{audio_cache_key(say, voice, rate)}.mp3'
            if not f.exists():
                tts(say, f, voice=voice, rate=rate)
            dur = probe_duration(f)
            timeline.append({'scene': si, 'start': t, 'dur': dur, 'text': show, 'file': str(f)})
            t += dur + gap
            li += 1
        sc['_start'], sc['_end'] = s_start, t
    total = t + 0.6
    # 拼接旁白
    lst = workdir / 'audio' / 'concat.txt'
    parts = []
    sil = workdir / 'audio' / 'gap.wav'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono', '-t', str(gap), str(sil)], check=True)
    lead = workdir / 'audio' / 'lead.wav'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono', '-t', '0.25', str(lead)], check=True)
    parts.append(lead)
    for item in timeline:
        wav = pathlib.Path(item['file']).with_suffix('.wav')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', item['file'], '-ar', '24000', '-ac', '1', str(wav)], check=True)
        parts += [wav, sil]
    lst.write_text(''.join(f"file '{p}'\n" for p in parts))
    narr = workdir / 'narration.wav'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-af', 'apad=pad_dur=0.6', str(narr)], check=True)
    return timeline, total, narr


def render(spec_path, do_render=True):
    spec_path = pathlib.Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text())
    workdir = spec_path.parent / (spec_path.stem + '_build')
    workdir.mkdir(exist_ok=True)
    timeline, total, narr = build_audio(spec, workdir)
    bgs = [scene_bg(sc, workdir, i) for i, sc in enumerate(spec['scenes'])]
    statics = [overlay_static(spec, sc) for sc in spec['scenes']]
    caps = [caption_layer(item['text']) for item in timeline]
    (workdir / 'timeline.json').write_text(json.dumps({'total': total, 'lines': timeline}, ensure_ascii=False, indent=1))
    out = spec_path.parent / (spec.get('id', spec_path.stem) + '.mp4')
    make_cover(spec, bgs[spec.get('cover', {}).get('scene', 0)], spec_path.parent / (spec.get('id', spec_path.stem) + '-cover.jpg'))
    if not do_render:
        return out
    n = int(total * FPS)
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-i', str(narr), '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
                           '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', str(out)], stdin=subprocess.PIPE)
    scenes = spec['scenes']
    for fi in range(n):
        t = fi / FPS
        si = next((i for i, sc in enumerate(scenes) if sc['_start'] <= t < sc['_end']), len(scenes) - 1)
        sc = scenes[si]
        p = (t - sc['_start']) / max(sc['_end'] - sc['_start'], 0.1)
        z = 1.0 + 0.08 * p if si % 2 == 0 else 1.08 - 0.08 * p
        bg = bgs[si]
        cw, ch = int(W / z), int(H / z)
        dx = int((W - cw) * (0.5 + 0.25 * math.sin(si + p)))
        dy = (H - ch) // 2
        frame = bg.crop((dx, dy, dx + cw, dy + ch)).resize((W, H), Image.BILINEAR).convert('RGBA')
        frame.alpha_composite(statics[si])
        cap = next((k for k, it in enumerate(timeline) if it['start'] <= t < it['start'] + it['dur'] + 0.12), None)
        if cap is not None:
            frame.alpha_composite(caps[cap], (0, 1180))
        # 进度条
        d = ImageDraw.Draw(frame)
        d.rectangle([0, H - 10, int(W * t / total), H], fill=YELLOW)
        ff.stdin.write(frame.convert('RGB').tobytes())
    ff.stdin.close()
    ff.wait()
    return out


def make_cover(spec, bg, out):
    c = spec.get('cover', {})
    img = bg.copy().convert('RGBA')
    img.alpha_composite(gradient(1100, 0, 235), (0, H - 1100))
    img.alpha_composite(gradient(420, 200, 0), (0, 0))
    d = ImageDraw.Draw(img)
    fb = font(40, 'medium')
    d.text((60, 80), spec.get('brand', '示例聊AI'), font=fb, fill=WHITE)
    title = c.get('title', spec['title_top'])
    ft = font(c.get('size', 132), 'semibold')
    lines = wrap(d, title, ft, 960)[:4]
    y = H - 260 - len(lines) * (c.get('size', 132) + 24)
    for i, ln in enumerate(lines):
        col = YELLOW if (c.get('highlight') and c['highlight'] in ln) else WHITE
        stroke_text(d, (60, y), ln, ft, col, stroke=8)
        y += c.get('size', 132) + 24
    if c.get('sub'):
        fs = font(54, 'medium')
        d.rounded_rectangle([60, y + 10, 60 + d.textlength(c['sub'], font=fs) + 48, y + 96], radius=12, fill=YELLOW)
        d.text((84, y + 53), c['sub'], font=fs, fill=INK, anchor='lm')
    img.convert('RGB').save(out, quality=92)
    return out


if __name__ == '__main__':
    print(render(sys.argv[1], '--no-render' not in sys.argv))
