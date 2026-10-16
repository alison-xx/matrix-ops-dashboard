#!/usr/bin/env python3
"""用户本人声音克隆（10-16 起所有视频配音改用用户自己的声音）。

走示例服务「追爆 → 声音克隆」同一套接口：上传一段 10–60 秒的清晰人声 → 示例服务存成「我的克隆」音色 →
合成时把这段录音当参考音频交给百炼 CosyVoice v2 复刻。make_motion 的 spec 写 "voice": "provider-clone:<音色名>"。

用法:
  .venv/bin/python scripts/voice_clone.py prep <录音文件> [--out 输出.mp3]   清理录音：去首尾静音、低切、轻降噪、响度归一，超过 60 秒截最稳的一段
  .venv/bin/python scripts/voice_clone.py upload <处理后的文件> --name 音色名 [--gender male|female]
  .venv/bin/python scripts/voice_clone.py list
  .venv/bin/python scripts/voice_clone.py test <音色名或id> [--text "试听文案"] [--out 试听.mp3]
"""
import argparse, json, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, provider_api, provider_custom_voices, provider_custom_voice, tts_provider, probe_duration

TEST_TEXT = ('DeepSeek停了快5个小时。补偿出来了，但大多数人没份。'
             '我的建议就三条：常用的AI至少备两家，提示词存一份在备忘录里，一家挂了直接贴到另一家。你现在主力用哪家？')


def prep(src, out=None):
    src = pathlib.Path(src)
    out = pathlib.Path(out) if out else ROOT / 'assets/voices/mine' / (src.stem + '-clean.mp3')
    out.parent.mkdir(parents=True, exist_ok=True)
    d0 = probe_duration(src)
    af = ('highpass=f=70,afftdn=nf=-25,'
          'silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,'
          'loudnorm=I=-18:TP=-2:LRA=9')
    args = ['ffmpeg', '-y', '-loglevel', 'error', '-i', str(src), '-af', af, '-ac', '1', '-ar', '44100']
    if d0 > 62:   # 示例服务建议 10–60 秒：太长就取中间一段（开头常有清嗓子、结尾常有收尾杂音）
        start = min(5.0, (d0 - 58) / 2)
        args[5:5] = ['-ss', f'{start:.1f}', '-t', '58']
    subprocess.run(args + ['-c:a', 'libmp3lame', '-q:a', '2', str(out)], check=True)
    d = probe_duration(out)
    r = subprocess.run(['ffmpeg', '-i', str(out), '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True, text=True)
    peak = [l for l in r.stderr.splitlines() if 'max_volume' in l]
    tips = []
    if d < 10:
        tips.append(f'只有 {d:.1f} 秒，示例服务建议 10–60 秒，复刻会不像，建议重录')
    return {'out': str(out), 'orig_seconds': round(d0, 1), 'seconds': round(d, 1), 'peak': peak[0].split(':')[-1].strip() if peak else None, 'tips': tips}


def upload(path, name, gender=None):
    body = {'name': name[:60]}
    if gender:
        body['gender'] = gender
    d = provider_api('POST', '/user/viral-video/voices/custom', body=body, files={'file': path}, timeout=300)
    return d.get('data') or d


def test(key, text=TEST_TEXT, out=None):
    cv = provider_custom_voice(key)
    out = pathlib.Path(out) if out else ROOT / 'assets/voices/mine' / f'test-{cv.get("name") or cv["id"]}.mp3'
    dur = tts_provider(text, out, ref_url=cv['audioUrl'])
    return {'voice': cv.get('name'), 'id': cv['id'], 'out': str(out), 'seconds': round(dur, 1)}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['prep', 'upload', 'list', 'test'])
    ap.add_argument('arg', nargs='?')
    ap.add_argument('--out')
    ap.add_argument('--name')
    ap.add_argument('--gender', choices=['male', 'female'])
    ap.add_argument('--text', default=TEST_TEXT)
    a = ap.parse_args()
    if a.cmd == 'prep':
        r = prep(a.arg, a.out)
    elif a.cmd == 'upload':
        r = upload(a.arg, a.name or pathlib.Path(a.arg).stem, a.gender)
    elif a.cmd == 'list':
        r = [{k: v.get(k) for k in ('id', 'name', 'gender', 'audioUrl', 'createdAt') if k in v} for v in provider_custom_voices()]
    else:
        r = test(a.arg, a.text, a.out)
    print(json.dumps(r, ensure_ascii=False, indent=1))
