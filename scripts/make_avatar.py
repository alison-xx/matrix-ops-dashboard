#!/usr/bin/env python3
"""示例作者动漫口播形象（10-16 用户要求：每条视频放用户头像的动漫形象，对口型、对字幕）。

做法（二次元口播常见的「PNGTuber」式，不用视频生成模型，零成本复用）：
  1. 以用户头像动漫版为参考，作图生成绿幕半身像 base（闭嘴、睁眼）
  2. 以 base 为参考分别改出 mid（嘴微张）、open（嘴张大）、blink（闭眼）
  3. 只把 variant 和 base 差异最大的那一块（嘴 / 眼睛）羽化后贴回 base，保证几帧之间除了嘴和眼完全一致，切换不闪
  4. 抠绿幕，输出透明 PNG：assets/avatar/creator-talk/{base,mid,open,blink}.png
make_motion 按配音音量逐帧切换 closed/mid/open，随机眨眼，加呼吸和点头。

用法: .venv/bin/python scripts/make_avatar.py [--ref 参考图] [--force]
"""
import argparse, base64, json, pathlib, sys, time, urllib.request, urllib.error
import numpy as np
from PIL import Image, ImageFilter
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, env

OUT = ROOT / 'assets/avatar/creator-talk'
RAW = OUT / 'raw'
REF_DEFAULT = ROOT / 'assets/avatar/creator-avatar-1024.jpg'

CHAR = ('Use the attached image as the strict character reference. Draw the SAME anime character: a young man with fluffy messy '
        'jet-black hair and a soft fringe, big round warm brown eyes with sparkling highlights, thin clear round wire-frame glasses '
        'with light silver rims, soft rosy cheeks, fair skin, plain white crew-neck T-shirt under an open dark navy-blue jacket. '
        'Keep the identical face, hairstyle, glasses, outfit, colors and soft Chinese anime illustration style with clean thin line art and soft cel shading. ')
LAYOUT = ('Composition: head-and-shoulders bust portrait, facing the camera straight on, head centered, the head fills about 55% of '
          'the image height, shoulders visible at the bottom edge. Background: perfectly flat solid pure chroma-key green (#00FF00) '
          'filling the entire image, no shadow, no gradient. Do not use any green on the character. No text, no watermark.')
VARIANTS = {
    'base': 'Expression: friendly, mouth gently closed in a small natural smile, eyes open looking at the viewer.',
    'mid': ('Keep this exact image identical in every detail (same pose, framing, lighting, hair, glasses, clothes, background). '
            'Change ONLY the mouth: slightly open as if in the middle of speaking a word, showing a little of the upper teeth.'),
    'open': ('Keep this exact image identical in every detail (same pose, framing, lighting, hair, glasses, clothes, background). '
             'Change ONLY the mouth: open wide and rounded as if saying "ah", showing the tongue and upper teeth.'),
    'blink': ('Keep this exact image identical in every detail (same pose, framing, lighting, hair, glasses, mouth, clothes, background). '
              'Change ONLY the eyes: both eyes gently closed in a relaxed blink, curved closed eyelids with eyelashes, glasses unchanged.'),
}


# 表情（10-16 用户：表情再丰富些，别只会眨眼）：只改眉毛和眼睛，嘴保持和 base 一样，说话时嘴型照常叠加
KEEP = ('Keep this exact image identical in every detail (same pose, framing, lighting, hair, glasses, MOUTH, clothes, background). '
        'Change ONLY the eyebrows and eyes: ')
MOUTHKEEP = ('Keep this exact image identical in every detail (same pose, framing, lighting, hair, glasses, eyes, clothes, background). '
             'Change ONLY the mouth: ')
VISEMES = {   # 口型：按拼音韵母切换（啊=open 呃=mid 已有）
    'oh': MOUTHKEEP + 'lips rounded into an "o" shape as if saying "哦 (o)", mouth medium open and round.',
    'ee': MOUTHKEEP + 'lips stretched wide in a flat smile showing the upper and lower teeth slightly apart, as if saying "衣 (i)".',
    'oo': MOUTHKEEP + 'lips pushed forward into a small tight round pucker as if saying "乌 (u)", mouth almost closed.',
}
EXPRESSIONS = {
    'surprised': KEEP + 'eyes opened very wide with small bright pupils, eyebrows raised high in surprise.',
    'thinking': KEEP + 'eyes looking up toward the upper right as if thinking, the right eyebrow raised and the left eyebrow slightly lowered.',
    'worried': KEEP + 'eyebrows drawn together and tilted up in the middle in a worried, troubled look, eyes slightly narrowed.',
    'wink': KEEP + 'a playful confident wink: the left eye closed in a curved line, the right eye open, eyebrows relaxed.',
    'happy': KEEP + 'eyes curved upward in a big happy smile shape with sparkling highlights, eyebrows lifted cheerfully.',
}


def _api(path, payload=None, timeout=240):
    e = env()
    data = json.dumps(payload).encode() if payload is not None else None
    for _ in range(20):
        req = urllib.request.Request(e['MODEL_API_BASE'] + path, data=data, method='POST' if data else 'GET',
                                     headers={'Authorization': f"Bearer {e['MODEL_API_KEY']}", 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as ex:
            if ex.code != 429:
                raise RuntimeError(f'HTTP {ex.code}: {ex.read()[:300]!r}')
            time.sleep(20)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as ex:   # 网络抖动（10-16 遇到过 SSL EOF）
            time.sleep(6)
    raise RuntimeError('作图接口一直限流或连不上')


def gen_ref(prompt, refs, out, model='gpt-image-2', size='1024x1024'):
    """带参考图作图（同步返回或异步任务都支持）。"""
    out = pathlib.Path(out)
    if out.exists():
        return out
    imgs = ['data:image/png;base64,' + base64.b64encode(pathlib.Path(r).read_bytes()).decode() for r in refs]
    d = _api('/images/generations', {'model': model, 'prompt': prompt, 'n': 1, 'size': size, 'image': imgs})
    url = ((d.get('data') or [{}])[0]).get('url')
    deadline = time.time() + 600
    while not url and d.get('id') and time.time() < deadline:
        time.sleep(15)
        d = _api(f"/generations/{d['id']}")
        if d.get('status') == 'succeeded':
            url = d['data'][0]['url']
        elif d.get('status') in ('failed', 'canceled'):
            raise RuntimeError(f"作图失败: {d.get('error')}")
    if not url:
        raise RuntimeError(f'作图没有返回图片: {json.dumps(d, ensure_ascii=False)[:300]}')
    out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as r:   # urlretrieve 没有超时，10-16 卡死过一次
        out.write_bytes(r.read())
    return out


def key_green(im):
    """抠绿幕 + 去绿边。"""
    a = np.asarray(im.convert('RGB')).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    greenness = g - np.maximum(r, b)
    alpha = np.clip(1 - (greenness - 25) / 60, 0, 1)
    spill = greenness > 0
    a[..., 1] = np.where(spill, np.maximum(r, b) + (g - np.maximum(r, b)) * 0.15, g)   # 边缘去绿
    out = np.dstack([a, alpha * 255]).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


def align(base, var):
    """variant 相对 base 的整体平移（相位相关），对齐后再比较差异。"""
    A = np.asarray(base.convert('L'), dtype=np.float32)
    B = np.asarray(var.convert('L').resize(base.size), dtype=np.float32)
    F = np.fft.fft2(A) * np.conj(np.fft.fft2(B))
    c = np.fft.ifft2(F / (np.abs(F) + 1e-6)).real
    dy, dx = np.unravel_index(np.argmax(c), c.shape)
    if dy > A.shape[0] // 2:
        dy -= A.shape[0]
    if dx > A.shape[1] // 2:
        dx -= A.shape[1]
    return var.resize(base.size).transform(base.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy), resample=Image.BICUBIC), (dx, dy)


def patch(base, var, region):
    """只取 variant 在 region（嘴/眼大致区域，0-1 比例）内与 base 差异明显的部分，羽化后贴回 base。"""
    var, shift = align(base, var)
    A = np.asarray(base.convert('RGB'), dtype=np.float32)
    B = np.asarray(var.convert('RGB'), dtype=np.float32)
    diff = np.abs(A - B).mean(axis=2)
    H, W = diff.shape
    x0, y0, x1, y1 = [int(v) for v in (region[0] * W, region[1] * H, region[2] * W, region[3] * H)]
    m = np.zeros_like(diff)
    m[y0:y1, x0:x1] = (diff[y0:y1, x0:x1] > 18).astype(np.float32)
    mask = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(21)).filter(ImageFilter.GaussianBlur(9))
    out = Image.composite(var.convert('RGB'), base.convert('RGB'), mask)
    return out, shift, float(m.sum()), mask


def build(ref, force=False):
    RAW.mkdir(parents=True, exist_ok=True)
    if force:
        for p in RAW.glob('*.png'):
            p.unlink()
    base_p = gen_ref(CHAR + VARIANTS['base'] + ' ' + LAYOUT, [ref], RAW / 'base.png')
    raws = {'base': base_p}
    for k in ('mid', 'open', 'blink'):
        raws[k] = gen_ref(VARIANTS[k], [base_p], RAW / f'{k}.png')
    base = Image.open(base_p).convert('RGB')
    frames = {'base': base}
    # 嘴在脸的中下部、眼睛在中部：只在这两个区域里找差异，别把头发/衣服的细微变化带进来
    regions = {'mid': (0.30, 0.45, 0.70, 0.78), 'open': (0.30, 0.45, 0.70, 0.80), 'blink': (0.22, 0.28, 0.78, 0.58)}
    report = {}
    for k in VISEMES:
        raws[k] = gen_ref(VISEMES[k], [base_p], RAW / f'{k}.png')
        regions[k] = (0.30, 0.45, 0.70, 0.80)
    face_reg = (0.18, 0.16, 0.82, 0.56)   # 眉眼区域
    for k in EXPRESSIONS:
        raws[k] = gen_ref(EXPRESSIONS[k], [base_p], RAW / f'{k}.png')
        regions[k] = face_reg
    masks = {}
    for k, reg in regions.items():
        frames[k], shift, area, masks[k] = patch(base, Image.open(raws[k]), reg)
        report[k] = {'shift': [int(v) for v in shift], 'changed_px': int(area)}
    OUT.mkdir(parents=True, exist_ok=True)
    for k, im in frames.items():
        key_green(im).save(OUT / f'{k}.png')
    # 局部贴片：只有嘴 / 眼睛那一块不透明，叠在 base 上用；眨眼和说话可以同时发生
    for k, name in [('mid', 'mouth_mid'), ('open', 'mouth_open'), ('blink', 'eyes_closed')] + [(e, f'face_{e}') for e in EXPRESSIONS] + [(v, f'mouth_{v}') for v in VISEMES]:
        rgba = key_green(frames[k])
        a = np.asarray(rgba).copy()
        a[..., 3] = (a[..., 3].astype(np.float32) * np.asarray(masks[k], dtype=np.float32) / 255).astype(np.uint8)
        Image.fromarray(a, 'RGBA').save(OUT / f'{name}.png')
    sheet = Image.new('RGBA', (4 * 384, 384), (40, 44, 52, 255))
    for i, k in enumerate(('base', 'mid', 'open', 'blink')):
        t = Image.open(OUT / f'{k}.png').resize((384, 384))
        sheet.alpha_composite(t, (i * 384, 0))
    sheet.save(OUT / 'sheet.png')
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--ref', default=str(REF_DEFAULT))
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    print(json.dumps(build(a.ref, a.force), ensure_ascii=False, indent=1))
