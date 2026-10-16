"""口播专用改写和发音复核清单；不修改字幕，不用 ASR 字面相同证明读音正确。"""
import hashlib
import json
import pathlib
import re
import sys

REVISION = 'pronunciation-v1'
# 只改确认含义的词组；不逐字替换「行」，不依赖未验证的 SSML/pinyin 支持。
MAINLAND = re.compile(r'(?<![美英法德韩泰俄中])国行(?!业|走|动|程|政|为)(?:版本)?')
READINGS = {'银行':'yín háng', '行业':'háng yè', '同行':'tóng háng / tóng xíng，按上下文',
            '行长':'háng zhǎng', '重新':'chóng xīn', '重复':'chóng fù', '重量':'zhòng liàng',
            '增长':'zēng zhǎng', '长大':'zhǎng dà', '长时间':'cháng shí jiān',
            '重庆':'chóng qìng', '调研':'diào yán', '调整':'tiáo zhěng',
            '还款':'huán kuǎn', '便宜':'pián yi', '角色':'jué sè', '处理':'chǔ lǐ'}

def spoken_text(text):
    return MAINLAND.sub('中国大陆版本', text)

def inspect_text(text):
    review = []
    for word, reading in READINGS.items():
        for hit in re.finditer(re.escape(word), text):
            review.append({'word':word, 'reading':reading,
                           'context':text[max(0,hit.start()-12):hit.end()+12]})
    return {'revision':REVISION, 'original':text, 'spoken':spoken_text(text),
            'rewritten':spoken_text(text) != text, 'review':review,
            'note':'听检实际音频；ASR 还原相同汉字不能证明多音字读音正确'}

def audio_cache_key(text, voice, rate, instructions=None, revision=REVISION):
    body = [revision, spoken_text(text), voice, rate, instructions or '']
    return hashlib.sha256(json.dumps(body, ensure_ascii=False).encode()).hexdigest()[:20]

def spec_lines(spec):
    for si, scene in enumerate(spec.get('scenes', [])):
        for li, line in enumerate(scene.get('lines', [])):
            text = line.get('say', line.get('show', '')) if isinstance(line, dict) else line
            yield si, li, re.sub(r'\[停[\d.]+\]|\*\*', '', text)

if __name__ == '__main__':
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text())
    print(json.dumps([dict(scene=si, line=li, **inspect_text(text))
                      for si, li, text in spec_lines(spec)], ensure_ascii=False, indent=2))
