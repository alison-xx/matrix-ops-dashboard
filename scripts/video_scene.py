"""Local motion footage scene. Generated clips must be reviewed before render."""
import hashlib
import html
import json
from pathlib import Path
import subprocess
from ai_video import probe


def scene(sc, i, work):
    source = Path(sc['video']).resolve()
    if not source.is_file():
        raise ValueError('video 场景需已下载的本地素材')
    if sc.get('source_kind') not in ('ai', 'real'):
        raise ValueError('video source_kind 必须明确为 ai 或 real')
    if sc.get('source_kind') == 'ai':
        review_path = source.with_suffix('.review.json')
        review = json.loads(review_path.read_text())
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if review.get('sha256') != digest or review.get('approved') is not True:
            raise ValueError('AI镜头未通过对应文件版本的视觉复核')
    duration = sc['_end'] - sc['_start']
    start = float(sc.get('trim_start', 0))
    info = probe(source)
    if start < 0 or duration <= 0 or start + duration > info['duration'] + .08:
        raise ValueError('镜头素材短于场景；缩短口播或补新镜头，不拉长静帧/循环')
    key = hashlib.sha256((hashlib.sha256(source.read_bytes()).hexdigest() + str(start) + str(duration)).encode()).hexdigest()[:16]
    dest = work / 'assets' / ('footage-' + key + '.mp4')
    if not dest.exists():
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(start), '-i', str(source),
                        '-t', str(duration), '-an', '-vf', 'fps=30,setsar=1',
                        '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(dest)], check=True)
    title = html.escape(sc.get('headline', ''))
    fit = sc.get('video_fit', 'contain')
    if fit not in ('contain', 'cover'):
        raise ValueError('video_fit must be contain or cover')
    position = float(sc.get('video_position_y', 50))
    if not 0 <= position <= 100:
        raise ValueError('video_position_y must be 0–100')
    return (f'<div class="inner footage"><video id="footage-{i}" src="assets/{dest.name}" '
            f'muted playsinline preload="auto" data-start="{sc["_start"]:.3f}" '
            f'data-duration="{duration:.3f}" data-volume="0" data-track-index="2" '
            f'style="width:100%;height:100%;object-fit:{fit};object-position:50% {position}%;border-radius:20px"></video>'
            f'<div class="img-head">{title}</div></div>')
