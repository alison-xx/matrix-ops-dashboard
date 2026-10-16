#!/usr/bin/env python3
"""拉各平台热榜（TikHub），筛 AI/科技相关条目。原始返回存 days/<day>/hot/，同一小时内复用缓存不重复计费。
用法: .venv/bin/python scripts/hot.py [--all]   (--all 显示全部条目，不只 AI 相关)
"""
import json, pathlib, re, sys, urllib.request, urllib.error
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, env, now

SOURCES = {
    '抖音热榜': '/api/v1/douyin/web/fetch_hot_search_result',
    '微博热搜': '/api/v1/weibo/web_v2/fetch_hot_search_summary',
    '知乎热榜': '/api/v1/zhihu/web/fetch_hot_list',
    '小红书灵感': '/api/v1/xiaohongshu/app_v2/get_creator_hot_inspiration_feed',
}
AI = re.compile(r'AI|ai|人工智能|大模型|模型|GPT|OpenAI|ChatGPT|Claude|Anthropic|Gemini|谷歌|DeepSeek|深度求索|豆包|千问|通义|Kimi|智谱|文心|元宝|'
                r'机器人|具身|算力|芯片|英伟达|NVIDIA|苹果|华为|小米|字节|阿里|腾讯|百度|马斯克|特斯拉|Grok|智能体|Agent|编程|程序员|自动驾驶|AIGC|数字人|Sora|视频生成|生图|手机|科技')
KEYS = ('word', 'keyword', 'title', 'sentence', 'query', 'note', 'desc', 'name', 'hot_word', 'display_query', 'content', 'target')


def fetch(name, path, cache_dir):
    f = cache_dir / f"{name}-{now():%H}.json"
    if f.exists():
        return json.loads(f.read_text())
    e = env()
    req = urllib.request.Request(e['TIKHUB_API_BASE'] + path, headers={'Authorization': 'Bearer ' + e['TIKHUB_API_KEY'], 'User-Agent': 'curl/8.7.1', 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as ex:
        d = {'error': ex.code, 'body': ex.read().decode()[:300]}
    except Exception as ex:
        d = {'error': str(ex)}
    f.write_text(json.dumps(d, ensure_ascii=False))
    return d


def titles(obj, out, depth=0):
    if depth > 8:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in KEYS and isinstance(v, str) and 2 <= len(v) <= 80 and not v.startswith('http'):
                out.append(v.strip())
            elif isinstance(v, (dict, list)):
                titles(v, out, depth + 1)
    elif isinstance(obj, list):
        for x in obj:
            titles(x, out, depth + 1)


def main():
    show_all = '--all' in sys.argv
    cache = ROOT / 'days' / now().date().isoformat() / 'hot'
    cache.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, path in SOURCES.items():
        d = fetch(name, path, cache)
        if 'error' in d and not d.get('data'):
            report[name] = {'error': d.get('error'), 'body': d.get('body', '')[:120]}
            continue
        ts = []
        titles(d.get('data', d), ts)
        seen, uniq = set(), []
        for t in ts:
            if t not in seen:
                seen.add(t); uniq.append(t)
        report[name] = uniq if show_all else [t for t in uniq if AI.search(t)]
    out = cache / f'summary-{now():%H%M}.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
