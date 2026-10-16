"""示例作者运营工具的公共函数：路径、密钥、出图、对话、配音、字体。"""
import asyncio, base64, json, os, pathlib, re, subprocess, sys, time, urllib.error, urllib.request, datetime as dt
from zoneinfo import ZoneInfo
from pronunciation import spoken_text

ROOT = pathlib.Path(__file__).resolve().parents[1]
TZ = ZoneInfo('Asia/Shanghai')
PINGFANG = os.environ.get('OPS_FONT', str(ROOT / 'scripts/styles/fonts/NotoSerifSC-SemiBold.otf'))
FACE = dict.fromkeys(('regular', 'medium', 'semibold', 'light'), 0)
VOICE = 'zh-CN-YunxiNeural'


def env():
    out = {}
    for line in ((ROOT / 'config/.env').read_text().splitlines() if (ROOT / 'config/.env').exists() else []):
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip()
    out.update(os.environ)
    return out


def now():
    return dt.datetime.now(TZ)


def today():
    return now().date().isoformat()


def font(size, weight='semibold'):
    from PIL import ImageFont
    return ImageFont.truetype(PINGFANG, size, index=FACE[weight])


def _post(url, body, key, timeout=300):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method='POST',
                                 headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def llm(prompt, system=None, model=None, temperature=0.8):
    e = env()
    model = model or e.get('MODEL_CHAT_MODEL', 'your-chat-model')
    msgs = ([{'role': 'system', 'content': system}] if system else []) + [{'role': 'user', 'content': prompt}]
    d = _post(f"{e['MODEL_API_BASE']}/chat/completions", {'model': model, 'messages': msgs, 'temperature': temperature}, e['MODEL_API_KEY'])
    if 'choices' in d:
        return d['choices'][0]['message']['content']
    return d.get('content') or json.dumps(d, ensure_ascii=False)


def gen_image(prompt, out, size='1024x1536', model=None, retries=2, refs=None):
    """生成一张图并保存到 out；已存在则直接复用（避免重复计费）。
    refs：参考图路径列表（如示例作者定稿形象），作图时保持人物长相一致（10-16 封面 v4 起用）。"""
    out = pathlib.Path(out)
    if out.exists() and out.stat().st_size > 10000:
        # 提示词变了（换了封面模板）就重画：10-16 dy-1 重渲复用了 07:01 的旧机器人底图，把 v4 示例作者封面盖回旧版。
        # 没有 .prompt.json 的底图是手动放的，照旧复用
        try:
            same = json.loads(out.with_suffix('.prompt.json').read_text()).get('prompt') == prompt
        except Exception:
            same = True
        if same:
            return out
        out.rename(out.with_name(f'{out.stem}-old{int(time.time())}{out.suffix}'))
    out.parent.mkdir(parents=True, exist_ok=True)
    e = env()
    model = model or e.get('MODEL_IMAGE_MODEL', 'your-image-model')
    body = {'model': model, 'prompt': prompt, 'size': size, 'n': 1}
    if refs:
        body['image'] = ['data:image/png;base64,' + base64.b64encode(pathlib.Path(r).read_bytes()).decode() for r in refs]
    last = None
    for attempt in range(retries + 1):
        try:
            d = _post(f"{e['MODEL_API_BASE']}/images/generations", body, e['MODEL_API_KEY'], timeout=400)
            item = (d.get('data') or [{}])[0]
            if item.get('url'):
                urllib.request.urlretrieve(item['url'], out)
            elif item.get('b64_json'):
                out.write_bytes(base64.b64decode(item['b64_json']))
            else:
                raise RuntimeError(f"no image: {json.dumps(d, ensure_ascii=False)[:300]}")
            log = out.with_suffix('.prompt.json')
            log.write_text(json.dumps({'prompt': prompt, 'size': size, 'model': model, 'id': d.get('id')}, ensure_ascii=False, indent=1))
            return out
        except Exception as ex:  # 网络抖动重试
            last = ex
            time.sleep(3)
    raise RuntimeError(f'gen_image failed: {last}')


BAILIAN_TTS_URL = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation'
# 场景 -> 百炼音色（qwen3-tts-flash）。spec 里可用 voice="bailian:<音色名>" 指定。
BAILIAN_VOICE_DEFAULT = 'Ethan'


def tts_bailian(text, out, voice=BAILIAN_VOICE_DEFAULT, model=None, instructions=None, speed=1.0):
    """百炼 Qwen-TTS 单句合成（10-16 起默认音色「晨煦」= Ethan）。需要 config/.env 里的 BAILIAN_API_KEY。
    out 是 .wav 就保存无损 WAV（出片走这条，全链路不过 mp3）；speed≠1 用 atempo 变速（不变调）。
    instructions（情绪语调指令）只有配置了 BAILIAN_TTS_INSTRUCT_MODEL（指令版模型，例如 qwen3-tts-instruct-flash，
    要在百炼控制台开通；10-16 这个账号调用返回「Model not exist」）时才发，普通 qwen3-tts-flash 不认指令。"""
    e = env()
    key = e.get('BAILIAN_API_KEY')
    if not key:
        raise RuntimeError('no BAILIAN_API_KEY')
    ins_model = e.get('BAILIAN_TTS_INSTRUCT_MODEL')
    body = {'model': model or (ins_model if instructions and ins_model else e.get('BAILIAN_TTS_MODEL', 'qwen3-tts-flash')),
            'input': {'text': text, 'voice': voice, 'language_type': 'Chinese'}}
    if instructions and ins_model:
        body['input']['instructions'] = instructions
    d = _post(BAILIAN_TTS_URL, body, key, timeout=120)
    url = ((d.get('output') or {}).get('audio') or {}).get('url')
    if not url:
        raise RuntimeError(f'bailian tts failed: {json.dumps(d, ensure_ascii=False)[:300]}')
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = out.with_suffix('.raw.wav')
    urllib.request.urlretrieve(url, raw)
    af = ['-af', f'atempo={speed:.3f}'] if abs(speed - 1) > 0.005 else []
    codec = ['-c:a', 'pcm_s16le'] if out.suffix == '.wav' else ['-c:a', 'libmp3lame', '-q:a', '2']
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(raw), *af, *codec, str(out)], check=True)
    raw.unlink(missing_ok=True)
    return probe_duration(out)


PROVIDER_API = os.environ.get('PROVIDER_API_BASE', 'https://api.example.com')


def _set_env(updates):
    """更新 config/.env 中的若干键（令牌刷新后写回）。"""
    p = ROOT / 'config/.env'
    lines = p.read_text().splitlines()
    keys = set(updates)
    lines = [l for l in lines if l.split('=', 1)[0].strip() not in keys] + [f'{k}={v}' for k, v in updates.items()]
    p.write_text('\n'.join(lines) + '\n')
    os.chmod(p, 0o600)


def _provider_refresh():
    e = env()
    rt = e.get('PROVIDER_USER_REFRESH')
    if not rt:
        raise RuntimeError('缺少示例服务刷新令牌 PROVIDER_USER_REFRESH')
    req = urllib.request.Request(f'{PROVIDER_API}/auth/refresh', data=json.dumps({'refreshToken': rt}).encode(), method='POST',
                                 headers={'Content-Type': 'application/json', 'User-Agent': 'creator-ops/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read()).get('data') or {}
    if not d.get('accessToken'):
        raise RuntimeError('示例服务令牌刷新失败，请用户重新提供登录令牌')
    _set_env({'PROVIDER_USER_TOKEN': d['accessToken'], 'PROVIDER_USER_REFRESH': d.get('refreshToken') or rt})
    return d['accessToken']


def tts_bailian_clone(text, out, voice_id, instruction=None, speech_rate=1.0, retries=3):
    """百炼 CosyVoice 复刻音色直连（dashscope SDK，WebSocket）。text 以 <speak> 开头时自动开 SSML（停顿 <break time="400ms"/>）。
    instruction ≤128 字，cosyvoice-v3.5 系列支持自由写法的语气/情感指令。音色在 config/.env 的 BAILIAN_CLONE_VOICE / BAILIAN_CLONE_MODEL。"""
    import dashscope
    from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat
    e = env()
    dashscope.api_key = e['BAILIAN_API_KEY']
    model = e.get('BAILIAN_CLONE_MODEL', 'cosyvoice-v3.5-plus')
    if instruction and not model.startswith('cosyvoice-v3.5'):
        instruction = None
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for attempt in range(retries):
        try:
            # 10-16：SDK 默认回 22.05kHz mp3，高频被砍、带压缩噪声（用户听出"有瑕疵"）。改要 48kHz 无损 WAV
            kw = {'model': model, 'voice': voice_id, 'speech_rate': max(0.5, min(2.0, speech_rate)),
                  'format': AudioFormat.WAV_48000HZ_MONO_16BIT,
                  'volume': 30}   # 默认音量 50 合成出来会削波（峰值顶到 0dB，响的字上"咔/滋"一下）；30 留约 4dB 余量，响度后面统一拉
            if instruction:
                kw['instruction'] = instruction[:128]
            audio = SpeechSynthesizer(**kw).call(text)
            if not audio:
                raise RuntimeError('百炼复刻没有返回音频')
            out.write_bytes(audio)
            return probe_duration(out)
        except Exception as ex:
            last = ex
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(f'百炼复刻合成失败: {last}')


def provider_api(method, path, body=None, files=None, timeout=120):
    """示例服务接口通用调用（自动刷新令牌）。files={'file': 本地路径} 时走 multipart 上传，body 里的字段作为表单字段。"""
    import uuid
    token = env().get('PROVIDER_USER_TOKEN')
    for attempt in range(2):
        headers = {'Authorization': f'Bearer {token}', 'User-Agent': 'creator-ops/1.0'}
        data = None
        if files:
            bd = uuid.uuid4().hex
            parts = []
            for k, v in (body or {}).items():
                parts.append(f'--{bd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
            for k, p in files.items():
                p = pathlib.Path(p)
                ctype = {'.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.m4a': 'audio/mp4', '.aac': 'audio/aac'}.get(p.suffix.lower(), 'application/octet-stream')
                parts.append(f'--{bd}\r\nContent-Disposition: form-data; name="{k}"; filename="{p.name}"\r\nContent-Type: {ctype}\r\n\r\n'.encode() + p.read_bytes() + b'\r\n')
            data = b''.join(parts) + f'--{bd}--\r\n'.encode()
            headers['Content-Type'] = f'multipart/form-data; boundary={bd}'
        elif body is not None:
            data = json.dumps(body).encode()
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(f'{PROVIDER_API}{path}', data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as ex:
            if ex.code == 401 and attempt == 0:
                token = _provider_refresh()
                continue
            raise RuntimeError(f'示例服务接口 {method} {path} 失败 HTTP {ex.code}: {ex.read().decode()[:300]}')


def provider_custom_voices():
    """「我的克隆」音色列表（示例服务 web.provider.cn → 追爆 → 声音克隆 上传的那些）。"""
    return (provider_api('GET', '/user/viral-video/voices/custom').get('data') or {}).get('items') or []


def provider_custom_voice(key):
    """按 id 或名字找一个克隆音色。"""
    vs = provider_custom_voices()
    hit = [v for v in vs if v.get('id') == key] or [v for v in vs if v.get('name') == key]
    if not hit:
        raise RuntimeError(f'示例服务「我的克隆」里没有音色「{key}」（现有：{[v.get("name") for v in vs]}）')
    return hit[0]


def tts_provider(text, out, voice='Ethan', speech_rate=0, provider='bailian-qwen-tts', ref_url=None):
    """示例服务「追爆」配音接口（背后百炼 Qwen-TTS / CosyVoice，扣示例服务积分）-> mp3，返回时长。
    ref_url：克隆音色的参考录音地址（走 CosyVoice v2 声音复刻，服务端首次会登记音色，偶发 500 靠下面的重试兜住）。"""
    token = env().get('PROVIDER_USER_TOKEN')
    if not token:
        raise RuntimeError('缺少示例服务用户令牌 PROVIDER_USER_TOKEN')
    if ref_url:
        vc = {'provider': 'bailian-cosyvoice-clone', 'referenceAudioUrl': ref_url, 'format': 'mp3', 'speechRate': int(speech_rate)}
    else:
        vc = {'provider': provider, 'voice': voice, 'format': 'mp3', 'speechRate': int(speech_rate)}
    body = {'text': text, 'voiceConfig': vc}

    def call(tok):
        req = urllib.request.Request(f'{PROVIDER_API}/user/viral-video/tts/synthesize', data=json.dumps(body).encode(), method='POST',
                                     headers={'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json', 'User-Agent': 'creator-ops/1.0'})
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())
    d, last = None, None
    for attempt in range(4):
        try:
            d = call(token)
            break
        except urllib.error.HTTPError as ex:
            if ex.code == 401:
                token = _provider_refresh()
                continue
            last = f'HTTP {ex.code}: {ex.read().decode()[:300]}'
        except Exception as ex:
            last = str(ex)
        time.sleep(3 * (attempt + 1))
    if d is None:
        raise RuntimeError(f'示例服务配音失败（已重试）{last}')
    url = (d.get('data') or {}).get('audioUrl')
    if not url:
        raise RuntimeError(f'示例服务配音无音频: {json.dumps(d, ensure_ascii=False)[:300]}')
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = out.with_suffix('.dl')
    urllib.request.urlretrieve(url, raw)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(raw), '-c:a', 'libmp3lame', '-q:a', '2', str(out)], check=True)
    raw.unlink(missing_ok=True)
    return probe_duration(out)


def tts(text, out, voice=VOICE, rate='+6%', pitch='+0Hz', instructions=None):
    """单句合成，返回时长。voice 前缀：provider:<音色> 走示例服务配音；bailian:<音色> 走百炼直连；其他为 edge-tts（默认禁用）。"""
    text = spoken_text(text)
    if str(voice).startswith('bailian-clone:'):   # 百炼直连复刻（10-16 起默认）：支持情感指令 instruction + SSML 停顿
        m = re.match(r'([+-]?\d+)%', str(rate or '0%'))
        vid = voice.split(':', 1)[1] or env().get('BAILIAN_CLONE_VOICE')
        try:
            return tts_bailian_clone(text, out, vid, instructions, 1 + (int(m.group(1)) / 100 if m else 0))
        except Exception as ex:   # 限流/出错：退回示例服务复刻（同一段录音），去掉 SSML 标签
            print(f'[tts] 百炼复刻失败，退回示例服务：{str(ex)[:160]}', file=sys.stderr)
            fallback = json.loads((ROOT / 'config/schedule.json').read_text()).get('voice_fallback', 'provider-clone:your-voice')
            return tts(re.sub(r'<[^>]+>', '', text), out, voice=fallback, rate=rate)
    if str(voice).startswith('provider-clone:'):   # 用户本人的克隆音色（10-16 起）：provider-clone:<音色名或 id>
        m = re.match(r'([+-]?\d+)%', str(rate or '0%'))
        cv = provider_custom_voice(voice.split(':', 1)[1])
        return tts_provider(text, out, speech_rate=int(int(m.group(1)) * 5) if m else 0, ref_url=cv['audioUrl'])
    if str(voice).startswith('provider:'):
        m = re.match(r'([+-]?\d+)%', str(rate or '0%'))
        return tts_provider(text, out, voice=voice.split(':', 1)[1], speech_rate=int(int(m.group(1)) * 5) if m else 0)
    """单句合成，返回时长（秒）。voice 以 bailian: 开头则走百炼，否则 edge-tts。"""
    if str(voice).startswith('bailian:'):
        # 10-16 用户：「声音暂时切回 TTS 的晨煦，调好情绪语调」→ 默认 bailian:Ethan（晨煦）。失败退回示例服务同一个音色（付费），不回退免费音色
        m = re.match(r'([+-]?\d+)%', str(rate or '0%'))
        try:
            return tts_bailian(text, out, voice=voice.split(':', 1)[1], instructions=instructions,
                               speed=1 + (int(m.group(1)) / 100 if m else 0))
        except Exception as ex:
            print(f'[tts] 百炼晨煦失败，退回示例服务：{str(ex)[:160]}', file=sys.stderr)
            fallback = json.loads((ROOT / 'config/schedule.json').read_text()).get('voice_fallback', 'provider:Ethan')
            return tts(text, out, voice=fallback, rate=rate)
    if env().get('ALLOW_FREE_TTS') != '1':
        raise RuntimeError('只允许百炼付费 TTS：spec 的 voice 需写成 bailian:<音色>')
    import edge_tts
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)

    async def run():
        c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await c.save(str(out))
    for attempt in range(3):
        try:
            asyncio.run(run())
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)
    return probe_duration(out)


def probe_duration(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def yxer(*args, timeout=180):
    r = subprocess.run(['yxer', *args, '--json'], capture_output=True, text=True, timeout=timeout)
    raw = r.stdout.strip() or r.stderr.strip()
    try:
        return r.returncode, json.loads(raw)
    except Exception:
        return r.returncode, {'ok': False, 'raw': raw[:2000]}


def dump(x):
    return json.dumps(x, ensure_ascii=False, indent=2)
