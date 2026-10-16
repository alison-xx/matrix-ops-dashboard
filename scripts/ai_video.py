#!/usr/bin/env python3
"""Resumable shot generation: Agnes Flash first, Duomi Veo fallback.
Usage: ai_video.py shot.json [--poll] [--dry-run]
State and credentials stay local. A POST with unknown outcome is never replayed.
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'agnes-video-2.5-flash'


def config():
    p = ROOT / 'config/.env'
    e = dict(line.split('=', 1) for line in p.read_text().splitlines()
             if '=' in line and not line.startswith('#')) if p.exists() else {}
    e.update(os.environ)
    return e


def save(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    tmp.chmod(0o600)
    tmp.replace(path)


def prompt(shot):
    fields = [('subject', '主体与场景'), ('action', '连续动作'), ('camera', '镜头'),
              ('lighting', '光线与材质'), ('composition', '构图'), ('continuity', '一致性')]
    if any(not str(shot.get(k, '')).strip() for k, _ in fields):
        raise ValueError('镜头需完整填写 subject/action/camera/lighting/composition/continuity')
    return '\n'.join(f'{label}：{shot[k]}' for k, label in fields) + (
        '\n单个连续镜头，动作有明确起止，真实物理运动、稳定曝光、克制景深。'
        '无字幕、无文字、无品牌标志、无水印、无闪烁、无形变、无额外肢体。'
        '不要旁白、对白和音乐；后期统一配音。不是新闻现场或真实产品实测证据。')


def payload(shot, provider):
    seconds = shot.get('seconds', 6)
    if type(seconds) is not int or not 4 <= seconds <= 12:
        raise ValueError('seconds 必须为4–12整数')
    ratio = shot.get('aspect_ratio', '9:16')
    if ratio not in ('9:16', '16:9'):
        raise ValueError('跨供应商镜头仅支持9:16/16:9')
    # Keep fallback semantics exact: initial integration supports text only.
    if any(shot.get(k) for k in ('images', 'audios', 'videos', 'first_frame', 'last_frame')):
        raise ValueError('当前统一接入只开放文生视频；参考素材需单独适配，不能静默丢弃')
    p = prompt(shot)
    if provider == 'agnes':
        return {'model': MODEL, 'prompt': p, 'seconds': str(seconds), 'mode': 'text',
                'size': '720P', 'aspect_ratio': ratio, 'n': 1}
    return {'model': 'veo3.1-fast', 'prompt': p, 'aspect_ratio': ratio, 'quality': '1080p'}


def request(provider, path, body=None):
    e = config()
    base = 'https://api.agnes-ai.cn' if provider == 'agnes' else 'https://duomiapi.com'
    key = e.get(provider.upper() + '_API_KEY')
    if not key:
        raise ValueError('缺少 ' + provider.upper() + '_API_KEY')
    req = urllib.request.Request(base + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization': ('Bearer ' if provider == 'agnes' else '') + key,
                 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def reserve(provider, seconds, fingerprint):
    """Conservative rate reservation, even while Flash is promotional/free.
    Video sub-budget is part of (not additional to) the operating daily budget.
    """
    directory = ROOT / 'state/ai-video'
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'budget.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        day = dt.datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
        path = directory / (day + '.json')
        data = json.loads(path.read_text()) if path.exists() else []
        cost = seconds * .15 if provider == 'agnes' else .4
        cap = min(float(config().get('AI_VIDEO_DAILY_CAP_CNY', '10')), 50)
        if sum(row['reserved_cny'] for row in data) + cost > cap:
            raise ValueError('AI视频当日子预算不足，保留任务，不提交')
        data.append({'provider': provider, 'reserved_cny': cost, 'fingerprint': fingerprint})
        save(path, data)


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                        '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    data = json.loads(r.stdout)
    stream = next(s for s in data['streams'] if s['codec_type'] == 'video')
    return {'width': stream['width'], 'height': stream['height'],
            'duration': float(data['format']['duration'])}


def download(url, path):
    if urllib.parse.urlparse(url).scheme != 'https':
        raise ValueError('视频结果必须使用HTTPS')
    tmp = path.with_suffix('.part.mp4')
    # No provider Authorization is forwarded to the media host.
    with urllib.request.urlopen(url, timeout=60) as r, tmp.open('wb') as out:
        import shutil
        shutil.copyfileobj(r, out)
    metadata = probe(tmp)
    if metadata['duration'] < 1:
        raise ValueError('下载内容不是有效视频')
    tmp.replace(path)
    return metadata


def step(shot_path, poll=False, dry_run=False):
    shot_path = Path(shot_path).resolve()
    shot = json.loads(shot_path.read_text())
    bodies = {p: payload(shot, p) for p in ('agnes', 'duomi')}
    fp = hashlib.sha256(json.dumps(bodies, sort_keys=True).encode()).hexdigest()
    state_path = shot_path.with_suffix('.job.json')
    if dry_run:
        return {'requests': bodies, 'fingerprint': fp}
    with shot_path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(state_path.read_text()) if state_path.exists() else {
            'fingerprint': fp, 'attempts': [], 'status': 'new'}
        if state['fingerprint'] != fp:
            raise ValueError('提示词已改变；使用新的镜头文件名，避免覆盖原任务')
        attempts = state['attempts']
        if state['status'] == 'downloaded':
            probe(shot_path.with_suffix('.mp4'))
            return state
        if state['status'] == 'uncertain':
            return state  # Human/provider reconciliation required, no extra POST.
        if attempts and attempts[-1]['status'] not in ('failed', 'rejected'):
            a = attempts[-1]
            if not poll:
                return state
            p = a['provider']
            path = ('/agnesapi?' + urllib.parse.urlencode({'video_id': a['id'], 'model_name': MODEL})
                    if p == 'agnes' else '/v1/videos/tasks/' + urllib.parse.quote(a['id'], safe=''))
            try:
                result = request(p, path)
            except Exception as ex:
                state['query_error'] = type(ex).__name__
                save(state_path, state)
                return state  # Read failures do not imply generation failure.
            status = result.get('status') if p == 'agnes' else result.get('state')
            if status in ('completed', 'succeeded'):
                videos = (result.get('data') or {}).get('videos') or [{}]
                url = result.get('url') if p == 'agnes' else videos[0].get('url')
                a['status'] = 'completed'
                state['status'] = 'completed'
                save(state_path, state)
                if not url:
                    raise ValueError('任务完成但无下载地址；保留任务续查')
                metadata = download(url, shot_path.with_suffix('.mp4'))
                state.update(status='downloaded', media=metadata, visual_review='pending')
                save(state_path, state)
                return state
            if status not in ('failed', 'error', 'cancelled'):
                state['status'] = str(status or 'pending')
                save(state_path, state)
                return state
            a['status'] = 'failed'
            state['status'] = 'failed'
            save(state_path, state)
        if len(attempts) >= 2:
            return state
        provider = 'agnes' if not attempts else 'duomi'
        # Verify credentials before reserving, and persist before sending.
        if not config().get(provider.upper() + '_API_KEY'):
            raise ValueError('缺少供应商密钥')
        reserve(provider, shot.get('seconds', 6), fp)
        a = {'provider': provider, 'status': 'submitting', 'model': bodies[provider]['model']}
        attempts.append(a)
        state['status'] = 'uncertain'
        save(state_path, state)
        try:
            result = request(provider, '/v1/videos' if provider == 'agnes' else '/v1/videos/generations', bodies[provider])
        except urllib.error.HTTPError as ex:
            # Only a definite rejection can trigger fallback. Server errors may have created a task.
            if ex.code in (400, 401, 402, 403, 404, 422, 429):
                a.update(status='rejected', http_status=ex.code)
                state['status'] = 'rejected'
            else:
                a['http_status'] = ex.code
        except Exception as ex:
            a['error_type'] = type(ex).__name__
        else:
            task_id = result.get('video_id') if provider == 'agnes' else result.get('id')
            if task_id:
                a.update(id=task_id, status='queued')
                state['status'] = 'queued'
        save(state_path, state)
        return state


def run(path, poll=False, dry_run=False):
    result = step(path, poll, dry_run)
    if result.get('status') in ('failed', 'rejected') and len(result['attempts']) == 1:
        return step(path, poll, dry_run)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shot')
    parser.add_argument('--poll', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.shot, args.poll, args.dry_run), ensure_ascii=False, indent=2))
    except Exception as ex:
        # URLs can carry signed tokens, never print exception bodies or request headers.
        raise SystemExit('AI视频操作未完成：' + type(ex).__name__)
