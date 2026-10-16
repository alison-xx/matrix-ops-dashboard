#!/usr/bin/env python3
"""真对口型示例作者（10-16 用户要求：动漫唇形跟着说话真实地动）。

百炼通义万相 wan2.2-s2v：一张图 + 一段音频 → 说话视频（支持动漫形象，嘴型逐字、头部自然动作；480P 0.5 元/秒）。
限制：音频 < 20 秒、只走北京工作空间域名、输出 16fps。做法：
  1. 整条纯人声 voice.wav 按句子边界切成 ≤18.5 秒的段
  2. 每段上传到蚁小二图床拿公网地址 → 并行提交 s2v 任务（结果按音频 md5 缓存在 state/s2v_cache/，重渲染不重复花钱）
  3. 下载拼接 → 抠绿幕 → VP9 透明 webm（30fps），交给 avatar_layer 放进 HyperFrames
形象图：assets/avatar/creator-talk/raw/base.png（绿幕半身像），公网地址缓存在 state/s2v_image.json。
"""
import hashlib, json, pathlib, subprocess, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, env, yxer, probe_duration

CACHE = ROOT / 'state/s2v_cache'
IMG = ROOT / 'assets/avatar/creator-talk/raw/base.png'
MAX_SEG = 18.5


def _base():
    e = env()
    return f"https://{e['BAILIAN_WORKSPACE']}.cn-beijing.maas.aliyuncs.com/api/v1", e['BAILIAN_API_KEY']


def _req(url, body=None, key=None, timeout=60):
    h = {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}
    if body is not None:
        h['X-DashScope-Async'] = 'enable'
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers=h, method='POST' if body is not None else 'GET')
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as ex:
            if ex.code in (429, 500, 502, 503) and attempt < 4:
                time.sleep(10 * (attempt + 1))
                continue
            raise RuntimeError(f's2v HTTP {ex.code}: {ex.read()[:300]!r}')
        except (urllib.error.URLError, TimeoutError):
            time.sleep(6)
    raise RuntimeError('s2v 接口连不上')


def _public_url(path):
    """上传到蚁小二图床（文件名要唯一，按内容 md5 命名）。"""
    rc, o = yxer('upload', str(path), timeout=300)
    if rc or not o.get('ok'):
        raise RuntimeError(f'上传失败 {path}: {o}')
    return 'https://media.example.com/example.png' + o['data']['key']


def image_url():
    p = ROOT / 'state/s2v_image.json'
    h = hashlib.md5(IMG.read_bytes()).hexdigest()[:12]
    if p.exists():
        d = json.loads(p.read_text())
        if d.get('md5') == h:
            return d['url']
    jpg = CACHE / f'creator-s2v-{h}.jpg'
    CACHE.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(IMG), '-q:v', '2', str(jpg)], check=True)
    url = _public_url(jpg)
    p.write_text(json.dumps({'md5': h, 'url': url}))
    return url


def segments(lines, total):
    """按句子边界切段：[(start, end)]，覆盖 0..total，每段 ≤ MAX_SEG。"""
    cuts = [0.0]
    seg_start = 0.0
    for k, ln in enumerate(lines[1:], 1):
        if ln['start'] - seg_start > MAX_SEG:
            prev_end = lines[k - 1]['start'] + lines[k - 1]['dur']
            cut = round((prev_end + ln['start']) / 2 if ln['start'] > prev_end else ln['start'], 3)
            if cut - seg_start < 1:
                cut = ln['start']
            cuts.append(cut)
            seg_start = cut
    cuts.append(total)
    out = []
    for a, b in zip(cuts, cuts[1:]):
        while b - a > 19.5:              # 单句超长：硬切
            out.append((a, a + 18.0)); a += 18.0
        out.append((a, b))
    return out


def _gen(seg_wav, img):
    h = hashlib.md5(seg_wav.read_bytes() + img.encode()).hexdigest()[:16]
    mp4 = CACHE / f'{h}.mp4'
    if mp4.exists():
        return mp4
    base, key = _base()
    named = CACHE / f'20261016-s2v-{h}.wav'
    named.write_bytes(seg_wav.read_bytes())
    aurl = _public_url(named)
    d = _req(base + '/services/aigc/image2video/video-synthesis',
             {'model': 'wan2.2-s2v', 'input': {'image_url': img, 'audio_url': aurl}, 'parameters': {'resolution': '480P'}}, key)
    tid = d['output']['task_id']
    deadline = time.time() + 1500
    while time.time() < deadline:
        time.sleep(15)
        o = _req(f'{base}/tasks/{tid}', key=key).get('output', {})
        st = o.get('task_status')
        if st == 'SUCCEEDED':
            with urllib.request.urlopen(o['results']['video_url'], timeout=180) as r:
                mp4.write_bytes(r.read())
            return mp4
        if st in ('FAILED', 'CANCELED', 'UNKNOWN'):
            raise RuntimeError(f's2v 任务失败: {json.dumps(o, ensure_ascii=False)[:300]}')
    raise RuntimeError('s2v 任务超时')


def make(work, lines, total, size=512):
    """生成整条透明口型视频 work/assets/avatar/talk.webm，返回路径。"""
    voice = work / 'audio/voice.wav'
    segdir = work / 'audio/s2v'
    segdir.mkdir(parents=True, exist_ok=True)
    img = image_url()
    segs = segments(lines, total)
    wavs = []
    for k, (a, b) in enumerate(segs):
        w = segdir / f'seg{k:02d}.wav'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(voice), '-ss', f'{a:.3f}', '-to', f'{b:.3f}', '-ac', '1', '-ar', '24000', str(w)], check=True)
        wavs.append(w)
    with ThreadPoolExecutor(max_workers=4) as ex:
        mp4s = list(ex.map(lambda w: _gen(w, img), wavs))
    # 每段补齐/截到准确时长（30fps），再拼接
    fixed = []
    for k, (m, (a, b)) in enumerate(zip(mp4s, segs)):
        f = segdir / f'seg{k:02d}.mp4'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(m), '-vf', f'fps=30,scale={size}:{size},tpad=stop_mode=clone:stop_duration=2',
                        '-t', f'{b - a:.3f}', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', str(f)], check=True)
        fixed.append(f)
    lst = segdir / 'concat.txt'
    lst.write_text(''.join(f"file '{p}'\n" for p in fixed))
    full = segdir / 'full.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(full)], check=True)
    out = work / 'assets/avatar/talk.webm'
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(full), '-vf', 'chromakey=0x00FF00:0.16:0.06,despill=type=green,format=yuva420p',
                    '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-b:v', '0', '-crf', '28', '-auto-alt-ref', '0', str(out)], check=True)
    cost = sum(b - a for a, b in segs) * 0.5
    return out, {'segments': len(segs), 'seconds': round(sum(b - a for a, b in segs), 1), 'cost_yuan_if_uncached': round(cost, 1)}


# ---------------------------------------------------------------------------
# VideoRetalk 路线（10-16 用户：万象太贵，换 VideoRetalk，0.08 元/秒，约为 s2v 的 1/6）
# 底片 = 已付过费的几段 s2v 动漫说话片段拼成的 63 秒长视频（assets/avatar/retalk/），只上传一次；
# 每条视频把整条配音交给 videoretalk（≤115 秒一段，超长按句子切），video_extension 让底片自动续长。
# 实测：用「会说话的」底片嘴型明显（嘴部动作 5.2），用静态待机底片嘴几乎不动（3.0）。同账号同时只处理 1 个任务。
RETALK_BASE = ROOT / 'assets/avatar/retalk/20261016-creator-talkbase-long.mp4'
RETALK_MAX = 115.0


def _retalk_base_url():
    p = ROOT / 'state/retalk_base.json'
    h = hashlib.md5(RETALK_BASE.read_bytes()).hexdigest()[:12]
    if p.exists():
        d = json.loads(p.read_text())
        if d.get('md5') == h:
            return d['url']
    url = _public_url(RETALK_BASE)
    p.write_text(json.dumps({'md5': h, 'url': url}))
    return url


def _retalk(seg_wav, base_url):
    h = hashlib.md5(seg_wav.read_bytes() + base_url.encode()).hexdigest()[:16]
    mp4 = CACHE / f'rt-{h}.mp4'
    if mp4.exists():
        return mp4
    CACHE.mkdir(parents=True, exist_ok=True)
    named = CACHE / f'20261016-rt-{h}.wav'
    named.write_bytes(seg_wav.read_bytes())
    aurl = _public_url(named)
    key = env()['BAILIAN_API_KEY']
    api = 'https://dashscope.aliyuncs.com/api/v1'
    d = _req(api + '/services/aigc/image2video/video-synthesis',
             {'model': 'videoretalk', 'input': {'video_url': base_url, 'audio_url': aurl}, 'parameters': {'video_extension': True}}, key)
    tid = d['output']['task_id']
    deadline = time.time() + 2400   # 同账号排队，可能要等前一个任务
    while time.time() < deadline:
        time.sleep(15)
        o = _req(f'{api}/tasks/{tid}', key=key).get('output', {})
        st = o.get('task_status')
        if st == 'SUCCEEDED':
            with urllib.request.urlopen(o['video_url'], timeout=180) as r:
                mp4.write_bytes(r.read())
            return mp4
        if st in ('FAILED', 'CANCELED', 'UNKNOWN'):
            raise RuntimeError(f'videoretalk 任务失败: {json.dumps(o, ensure_ascii=False)[:300]}')
    raise RuntimeError('videoretalk 任务超时')


def make_retalk(work, lines, total, size=512):
    voice = work / 'audio/voice.wav'
    segdir = work / 'audio/retalk'
    segdir.mkdir(parents=True, exist_ok=True)
    base_url = _retalk_base_url()
    global MAX_SEG
    saved, MAX_SEG = MAX_SEG, RETALK_MAX
    try:
        segs = segments(lines, total) if total > RETALK_MAX else [(0.0, total)]
    finally:
        MAX_SEG = saved
    fixed = []
    for k, (a, b) in enumerate(segs):   # videoretalk 同时只处理一个任务：顺序提交
        w = segdir / f'seg{k:02d}.wav'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(voice), '-ss', f'{a:.3f}', '-to', f'{b:.3f}', '-ac', '1', '-ar', '24000', str(w)], check=True)
        m = _retalk(w, base_url)
        f = segdir / f'seg{k:02d}.mp4'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(m), '-vf', f'fps=30,scale={size}:{size},tpad=stop_mode=clone:stop_duration=2',
                        '-t', f'{b - a:.3f}', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', str(f)], check=True)
        fixed.append(f)
    lst = segdir / 'concat.txt'
    lst.write_text(''.join(f"file '{p}'\n" for p in fixed))
    full = segdir / 'full.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(full)], check=True)
    out = work / 'assets/avatar/talk.webm'
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(full), '-vf', 'chromakey=0x00FF00:0.16:0.06,despill=type=green,format=yuva420p',
                    '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-b:v', '0', '-crf', '28', '-auto-alt-ref', '0', str(out)], check=True)
    secs = sum(b - a for a, b in segs)
    return out, {'engine': 'videoretalk', 'segments': len(segs), 'seconds': round(secs, 1), 'cost_yuan_if_uncached': round(secs * 0.08, 2)}
