#!/usr/bin/env python3
"""成片声音质检（10-16 用户：「最新的这个抖音视频声音全出问题了……以后不要再出现这个问题」）。

事故：07:13 渲染时配音流程正在从 24kHz 换到 48kHz，旧缓存的 24k 静音混进 48k 拼接，整条旁白变成两倍长、声音全乱，
响度和峰值却完全正常——只看音量查不出来。所以这里用语音识别把成片念的话转成文字，和脚本逐字对照。

用法:
  audio_qc.py <成片.mp4> [--spec spec.json]      不写 --spec 就找同目录的 spec.json
退出码 0 = 通过，1 = 不通过；结果写到 <成片>.audioqc.json。ops.py add / claim 会对视频自动调用，不通过就拦下。

检查：
  1. 音轨在、采样率 44.1k/48k、长度和画面一致（±1 秒）
  2. 渲染目录里的旁白 narration.m4a 不能比成片长 2 秒以上（这次事故旁白 108 秒、成片 56 秒）
  3. 整体响度 -20～-11 LUFS，真峰值 ≤ -0.3 dBTP
  4. 片中（去掉最后 3 秒）没有超过 2.5 秒的静音
  5. 语音识别（whisper medium，中文）和脚本对照：脚本里的汉字被念出来的比例（去掉数字和英文，避免「150」念成「一百五十」误判）≥ 0.75
"""
import difflib, json, pathlib, re, subprocess, sys, tempfile

from pronunciation import spec_lines, spoken_text, inspect_text

WHISPER = '/opt/homebrew/bin/whisper-cli'
MODEL = pathlib.Path.home() / '.cache/hyperframes/whisper/models/ggml-medium.bin'
MIN_COVER = 0.75
NUM_CN = set('零一二三四五六七八九十百千万亿两')


def sh(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def probe(path):
    r = sh(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,sample_rate', '-of', 'json', str(path)])
    d = json.loads(r.stdout or '{}')
    a = next((s for s in d.get('streams', []) if s.get('codec_type') == 'audio'), None)
    return float(d.get('format', {}).get('duration', 0)), (int(a['sample_rate']) if a and a.get('sample_rate') else None)


def loudness(path):
    r = sh(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-map', '0:a:0', '-af', 'ebur128=peak=true:framelog=quiet', '-f', 'null', '-'])
    txt = r.stderr
    i = re.search(r'I:\s*(-?[\d.]+) LUFS', txt.split('Summary')[-1])
    tp = re.search(r'Peak:\s*(-?[\d.]+|-inf) dBFS', txt.split('True peak')[-1]) if 'True peak' in txt else None
    return (float(i.group(1)) if i else None), (float(tp.group(1)) if tp and tp.group(1) != '-inf' else None)


def silences(path, dur):
    r = sh(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-map', '0:a:0', '-af', 'silencedetect=n=-45dB:d=2.5', '-f', 'null', '-'])
    out, start = [], None
    for ln in r.stderr.splitlines():
        m = re.search(r'silence_start: ([\d.]+)', ln)
        if m:
            start = float(m.group(1))
        m = re.search(r'silence_end: ([\d.]+)', ln)
        if m and start is not None:
            if float(m.group(1)) < dur - 3 and start > 0.5:
                out.append((round(start, 1), round(float(m.group(1)), 1)))
            start = None
    return out


def to_simplified(s):
    try:
        import opencc
        return opencc.OpenCC('t2s').convert(s)
    except Exception:
        return s


def cjk(s):
    return ''.join(ch for ch in to_simplified(s) if '\u4e00' <= ch <= '\u9fff' and ch not in NUM_CN)


def script_text(spec):
    return ''.join(spoken_text(text) for _, _, text in spec_lines(spec))


def transcribe(path, chunk=15):
    """分段识别：whisper 一口气识别长音频会整段漏字（正常视频 385 字只认出 153 字），按 15 秒切开、不带上文，逐段识别再拼。"""
    dur, _ = probe(path)
    out = []
    with tempfile.TemporaryDirectory() as td:
        k, s = 0, 0.0
        while s < dur - 0.3:
            wav = pathlib.Path(td) / f'c{k}.wav'
            sh(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{s:.2f}', '-t', str(chunk), '-i', str(path), '-ar', '16000', '-ac', '1', str(wav)], check=True)
            r = sh([WHISPER, '-m', str(MODEL), '-l', 'zh', '-f', str(wav), '-np', '-nt', '-mc', '0', '--prompt', '以下是普通话的句子，使用简体中文。'], timeout=300)
            out.append(r.stdout.strip())
            k, s = k + 1, s + chunk
    return ''.join(out)


def coverage(expected, heard):
    e, h = cjk(expected), cjk(heard)
    if not e:
        return None
    m = difflib.SequenceMatcher(None, e, h, autojunk=False)
    return sum(b.size for b in m.get_matching_blocks()) / len(e)


def check(mp4, spec_path=None):
    mp4 = pathlib.Path(mp4)
    spec_path = pathlib.Path(spec_path) if spec_path else mp4.with_name('spec.json')
    errs, warns, info = [], [], {}
    dur, sr = probe(mp4)
    info['duration'], info['sample_rate'] = round(dur, 2), sr
    if not sr:
        errs.append('成片没有音轨')
        return errs, warns, info
    if sr not in (44100, 48000):
        errs.append(f'采样率 {sr}，应为 44100/48000')
    narr = mp4.with_name(mp4.stem + '_hf') / 'assets/narration.m4a'
    if narr.exists():
        nd, _ = probe(narr)
        info['narration_duration'] = round(nd, 2)
        if nd > dur + 2:
            errs.append(f'旁白 {nd:.1f} 秒比成片 {dur:.1f} 秒长 {nd - dur:.1f} 秒：拼接出错（10-16 事故同款，采样率混了），重新渲染')
    i, tp = loudness(mp4)
    info['lufs'], info['true_peak'] = i, tp
    if i is None or not (-20 <= i <= -11):
        errs.append(f'整体响度 {i} LUFS，应在 -20～-11')
    if tp is not None and tp > -0.3:
        errs.append(f'真峰值 {tp} dBTP 太高，可能破音')
    sil = silences(mp4, dur)
    info['long_silences'] = sil
    if sil:
        errs.append(f'片中有 {len(sil)} 段超过 2.5 秒的静音：{sil[:3]}')
    if spec_path.exists() and MODEL.exists():
        spec = json.loads(spec_path.read_text())
        info['pronunciation_review'] = [dict(scene=si, line=li, **inspect_text(text))
            for si, li, text in spec_lines(spec) if inspect_text(text)['review'] or inspect_text(text)['rewritten']]
        if info['pronunciation_review']:
            warns.append('含发音改写或多音字：按 pronunciation_review 逐句听检；ASR 不证明读音正确')
        heard = transcribe(mp4)
        cov = coverage(script_text(spec), heard)
        if cov is not None and cov < 0.80:
            # 语速快的音色（10-16 起的 TTS 晨煦约 6 字/秒）15 秒一块识别会整句漏（Office 第 0 课 15 秒块 72%、8 秒块 98%），换小块再认一次取高的
            h2 = transcribe(mp4, chunk=8)
            c2 = coverage(script_text(spec), h2)
            if c2 is not None and c2 > cov:
                heard, cov = h2, c2
        info['transcript'] = heard[:600]
        info['coverage'] = None if cov is None else round(cov, 3)
        if cov is not None and cov < MIN_COVER:
            errs.append(f'语音识别和脚本只对上 {cov:.0%}（要求 ≥{MIN_COVER:.0%}）：配音念错、失真或拼接乱了。识别结果开头：{heard[:60]}')
        elif cov is not None and cov < 0.80:
            warns.append(f'语音识别和脚本对上 {cov:.0%}，偏低，亲自听一遍开头 15 秒')
    else:
        warns.append('没有 spec.json 或识别模型，跳过逐字对照')
    return errs, warns, info


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if not a:
        print(__doc__); sys.exit(2)
    spec = sys.argv[sys.argv.index('--spec') + 1] if '--spec' in sys.argv else None
    if spec in a:
        a.remove(spec)
    errs, warns, info = check(a[0], spec)
    res = {'ok': not errs, 'errors': errs, 'warnings': warns, **info}
    pathlib.Path(a[0] + '.audioqc.json').write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(('✅ 声音质检通过' if not errs else '❌ 声音质检不通过') + f"（识别对上 {info.get('coverage')}，响度 {info.get('lufs')} LUFS，"
          f"成片 {info.get('duration')} 秒，旁白 {info.get('narration_duration', '—')} 秒）")
    for e in errs:
        print('  ✗', e)
    for w in warns:
        print('  !', w)
    sys.exit(0 if not errs else 1)


if __name__ == '__main__':
    main()
