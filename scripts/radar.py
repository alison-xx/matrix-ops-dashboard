#!/usr/bin/env python3
"""热点雷达：汇总各平台热榜 -> 话题归并 -> 跨平台热度 cross_score + deepseek-flash 打分 -> 合成最终分 -> 输出可借势候选。
用法:
  .venv/bin/python scripts/radar.py                 # 正式运行（定时任务用）：打印 TOP 候选，写 days/<日期>/radar/<HHMM>.json，
                                                    # 更新 state/radar_seen.json，growth 题自动进选题库
  .venv/bin/python scripts/radar.py --dry-run       # 试跑：不写 seen 状态、不进选题库，结果写 <HHMM>-dry.json（不影响下一轮定时任务）
  .venv/bin/python scripts/radar.py --no-llm-merge  # 只用关键词归并，不调 LLM 归并
  candidates    = 各平台热榜上的新话题（快反用）；同一事件只出一条，带 sources / merged_titles / cross_score
  growth_topics = 抖音低粉爆款/高涨粉榜里能用示例作者角度做的题（批次选题参考，不触发快反）
打分（详见 运营手册/热点快反.md「打分怎么看」）：
  score = 11 × (0.7 × 内容分/9 + 0.3 × cross_score/100)，内容分 = ai + ride + (3 - risk)；旧算法的分数保留在 llm_score。
来源与成本（外部源都按 15 分钟一份缓存在 days/<日期>/hot/，任一源失败只跳过该源）：
  抖音热点走 yxer（免费）；微博/知乎/小红书走 TikHub（每 15 分钟约 3 次调用）；
  AI热点走 aihot.news 公开 JSON 接口（免 key，每 15 分钟 2 次；10-16 用户决定启用，开关见 RADAR_SOURCES）；
  抖音低粉爆款榜/高涨粉榜（关键词 AI工具、大模型，24 小时窗口）每小时共 4 次，$0.001/次；
  LLM：打分每 60 个话题 1 次 + 归并 1 次（同一 15 分钟、同一批标题复用缓存）。
  newsnow（头条/百度/B站）没接：公开实例对脚本请求返回 Cloudflare 403，只能自建。
"""
import argparse, datetime as dt, gzip, hashlib, json, math, pathlib, re, sys, time, urllib.error, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, env, now, yxer, llm

# 来源开关。关掉的来源完全不发请求。
RADAR_SOURCES = {
    'douyin': True,     # 抖音热点（yxer）
    'weibo': True,      # TikHub
    'zhihu': True,      # TikHub
    'xhs': True,        # TikHub
    'billboard': True,  # 抖音热点宝 低粉爆款/高涨粉（TikHub）
    # aihot.news（AI热点）：10-16 用户决定启用。条款写明面向外部的商业用途须书面授权（https://aihot.news/terms），
    # 要停用改成 False 即可，False 时完全不请求 aihot.news。
    'aihot': True,
}

DOUYIN_ACCOUNT = env().get('OPS_PROBE_ACCOUNT', '')
TIKHUB = {
    '微博': '/api/v1/weibo/web_v2/fetch_hot_search_summary',
    '知乎': '/api/v1/zhihu/web/fetch_hot_list',
    '小红书': '/api/v1/xiaohongshu/app_v2/get_creator_hot_inspiration_feed',
}
# AIHOT 两个实例：示例服务自己部署的 aihot.provider.cn 优先（10-16 上线，用户要求热点直接从这里取），aihot.news 补全；同标题只算一次。
# 自建实例数据攒够后，可以把第二个删掉。
AIHOT_BASES = [('aihot', env().get('AIHOT_API_BASE', 'https://aihot.news/api/v1'))]
AIHOT = AIHOT_BASES[-1][1]
AIHOT_UA = 'aihot-api/2.0.0'  # AIHOT 说明：程序化定时拉取用 JSON 接口（openapi-v1.json）并用这个 UA
GROWTH_PLATFORMS = ('抖音低粉爆款', '抖音高涨粉')
AI_RE = re.compile(r'AI|ai|人工智能|大模型|GPT|OpenAI|ChatGPT|Claude|Anthropic|Gemini|DeepSeek|豆包|千问|通义|Kimi|智谱|文心|元宝|'
                   r'机器人|具身|算力|芯片|英伟达|智能体|Agent|AIGC|数字人|Sora|生成|自动驾驶|苹果智能|Siri|Token|token|模型|算法')

# ---------- 打分权重 ----------
# cross_score（0-100）借鉴 TrendRadar 的 calculate_news_weight（排名 0.6 / 频次 0.3 / 热度 0.1），按我们的场景改了权重：
#   频次 0.5：同一事件上了几个平台/榜单。这是「全网都在关心」最直接的信号，也是 LLM 逐条看标题看不到的信息，所以权重最高。
#             TrendRadar 的频次是同一标题被抓到的次数；我们 30 分钟才跑一次，改成「出现在几个不同平台」。
#   排名 0.35：各平台里取最好的名次。取最好而不取平均：多上一个榜时名次靠后，取平均反而会降分。
#   热度 0.15：各平台热度值在本平台内按榜首归一化后取最高。各平台单位不同（播放量/万人在看/万热度/讨论数），
#             微博热度字段常为空，可信度最低，所以权重最小；缺热度值时用排名分代替（和 TrendRadar 的热度项本来就按排名算一致）。
W_FREQ, W_RANK, W_HEAT = 0.5, 0.35, 0.15
# 最终分 score：沿用旧版 0-11 的量纲（旧版最高 9 + 2），热点快反.md 里的「9 分线」继续可用。
#   内容分 0.7：ai/ride/risk 判断的是「示例作者能不能做、做了对读者有没有用」，是做不做的前提；
#   cross 0.3：决定同样能做的题里谁更热、先做谁。最多给 3.3 分，内容分 5 分以下的题再热也到不了 9 分，不会被热度带偏人设。
W_LLM, W_CROSS, SCORE_SCALE, LLM_MAX = 0.7, 0.3, 11, 9
MAX_SCORE_TOPICS = 240  # 每轮最多送 LLM 打分的话题数（4 批 × 60）；超出的留到下一轮，不标记已见


def bucket_cache(name):
    d = ROOT / 'days' / now().date().isoformat() / 'hot'
    d.mkdir(parents=True, exist_ok=True)
    return d / f'{name}-{now():%H}{now().minute // 15}.json'


def tikhub(name, path):
    f = bucket_cache(name)
    if f.exists():
        return json.loads(f.read_text())
    e = env()
    req = urllib.request.Request(e['TIKHUB_API_BASE'] + path, headers={'Authorization': 'Bearer ' + e['TIKHUB_API_KEY'], 'User-Agent': 'curl/8.7.1'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
    except Exception as ex:
        d = {'error': str(ex)}
    f.write_text(json.dumps(d, ensure_ascii=False))
    return d


BILLBOARD = {'低粉爆款': '/api/v1/douyin/billboard/fetch_hot_total_low_fan_list',
             '高涨粉': '/api/v1/douyin/billboard/fetch_hot_total_high_fan_list'}


def tikhub_post(name, path, body):
    """抖音热点宝榜单（24 小时窗口），每小时只拉一次。"""
    d = ROOT / 'days' / now().date().isoformat() / 'hot'
    d.mkdir(parents=True, exist_ok=True)
    f = d / f'{name}-{now():%H}.json'
    if f.exists():
        return json.loads(f.read_text())
    e = env()
    req = urllib.request.Request(e['TIKHUB_API_BASE'] + path, data=json.dumps(body).encode(), method='POST',
                                 headers={'Authorization': 'Bearer ' + e['TIKHUB_API_KEY'], 'User-Agent': 'curl/8.7.1',
                                          'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            out = json.loads(r.read())
    except Exception as ex:
        out = {'error': str(ex)}
    f.write_text(json.dumps(out, ensure_ascii=False))
    return out


def http_json(url, ua, timeout=20):
    """免 key 的公开 GET 接口。5xx/超时重试一次；4xx（含 429）直接放弃，等下一个缓存周期。"""
    req = urllib.request.Request(url, headers={'User-Agent': ua, 'Accept': 'application/json', 'Accept-Encoding': 'gzip'})
    last = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.headers.get('Content-Encoding') == 'gzip':
                    raw = gzip.decompress(raw)
                return json.loads(raw)
        except urllib.error.HTTPError as ex:
            last = f'HTTP {ex.code}'
            if ex.code < 500:
                break
        except Exception as ex:
            last = str(ex)[:200]
        time.sleep(3)
    return {'error': last}


def cached_json(name, url, ua):
    f = bucket_cache(name)
    if f.exists():
        return json.loads(f.read_text())
    d = http_json(url, ua)
    f.write_text(json.dumps(d, ensure_ascii=False))
    return d


def parse_heat(v):
    """'2381.5万人在看' / '2151 万热度' / 12345 -> 数值；解析不了返回 None。"""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if v > 0 else None
    m = re.search(r'(\d+(?:\.\d+)?)\s*(亿|万|w|W|k|K)?', str(v).replace(',', ''))
    if not m:
        return None
    return float(m.group(1)) * {'亿': 1e8, '万': 1e4, 'w': 1e4, 'W': 1e4, 'k': 1e3, 'K': 1e3}.get(m.group(2), 1)


def zhihu_items(zh):
    out = []
    for x in ((zh.get('data') or {}).get('data')) or []:
        t = x.get('target') if isinstance(x, dict) else None
        if isinstance(t, dict) and isinstance(t.get('title'), str):
            qid = t.get('id')
            out.append({'title': t['title'], 'heat': x.get('detail_text'), 'answer_count': t.get('answer_count'),
                        'url': f'https://www.zhihu.com/question/{qid}' if qid and t.get('type') == 'question' else None})
    if out:
        return out
    zl = []  # 结构变了就退回旧的通用遍历，只拿标题

    def walk(o, depth=0):
        if depth > 6:
            return
        if isinstance(o, dict):
            t = o.get('title') or (o.get('target') or {}).get('title') if isinstance(o.get('target'), dict) else o.get('title')
            if isinstance(t, str) and 6 <= len(t) <= 90:
                zl.append(t)
            for v in o.values():
                if isinstance(v, (dict, list)):
                    walk(v, depth + 1)
        elif isinstance(o, list):
            for v in o:
                walk(v, depth + 1)
    walk(zh.get('data'))
    return [{'title': t} for t in zl]


def collect_aihot():
    """AIHOT：先取多源热点事件（名次即 AIHOT 热点排名，热度 = 参与讨论的信源/账号数），再补 24h 精选里编辑分高的，排在后面。
    依次取 AIHOT_BASES（示例服务自建优先，aihot.news 补全），按标题去重。"""
    out, ids, seen, errs = [], set(), set(), []
    norm = lambda t: re.sub(r'\s+', '', (t or '').lower())[:24]
    hots, sels = [], []
    for tag, base in AIHOT_BASES:
        hot = cached_json(f'AI热点-hot-{tag}', f'{base}/hot-topics', AIHOT_UA)
        sel = cached_json(f'AI热点-items-{tag}', f'{base}/items?mode=selected&window=24h&limit=50', AIHOT_UA)
        hots += [(tag, x) for x in (hot.get('items') or [])[:15]]
        sels += [(tag, x) for x in (sel.get('items') or [])]
        for d in (hot, sel):
            if d.get('error'):
                errs.append(f"{tag}: {d['error']}")
    for tag, x in hots:
        k = norm(x.get('title'))
        if not k or k in seen:
            continue
        seen.add(k)
        links = x.get('links') or {}
        ids.add(x.get('id'))
        out.append({'platform': 'AI热点', 'rank': len(out) + 1, 'title': (x.get('title') or '').strip(), 'heat': x.get('participantCount'),
                    'url': links.get('aihot'), 'aihot': {'kind': '热点事件', 'instance': tag, 'source_count': x.get('sourceCount'),
                                                         'original': links.get('original'), 'latest_at': x.get('latestAt')}})
    rows = [(tag, x) for tag, x in sels if x.get('id') not in ids and x.get('category') != 'paper' and norm(x.get('title')) not in seen]
    for tag, x in sorted(rows, key=lambda r: -(r[1].get('score') or 0)):
        k = norm(x.get('title'))
        if k in seen:
            continue
        seen.add(k)
        if len([o for o in out if o['aihot']['kind'] == '24h精选']) >= 20:
            break
        links = x.get('links') or {}
        out.append({'platform': 'AI热点', 'rank': len(out) + 1, 'title': (x.get('title') or '').strip(), 'url': links.get('aihot'),
                    'aihot': {'kind': '24h精选', 'instance': tag, 'score': x.get('score'), 'category': x.get('category'),
                              'original': links.get('original'), 'published_at': x.get('publishedAt')}})
    err = '; '.join(errs) if len(errs) == 2 * len(AIHOT_BASES) else None  # 两个实例都挂了才算出错
    return out, err


def collect():
    items, status = [], {}

    def note(name, rows, err=None):
        status[name] = f'失败：{err}' if err and not rows else len(rows)
    if RADAR_SOURCES.get('douyin'):
        rc, o = yxer('query', 'hot-events', DOUYIN_ACCOUNT, '--type', 'video')
        rows = []
        for n, x in enumerate(((o.get('data') or {}).get('list') or [])[:50], 1):
            rows.append({'platform': '抖音', 'rank': n, 'title': x.get('yixiaoerName'), 'heat': x.get('viewNum'),
                         'douyin_hot_event': {'yixiaoerId': x.get('yixiaoerId'), 'yixiaoerName': x.get('yixiaoerName')}})
        items += rows
        note('抖音', rows, None if rows else f'yxer rc={rc}')
    if RADAR_SOURCES.get('weibo'):
        d = tikhub('微博', TIKHUB['微博'])
        rows = [{'platform': '微博', 'rank': n, 'title': x['keyword'], 'heat': x.get('heat') or x.get('num'), 'tag': x.get('tag')}
                for n, x in enumerate(((d.get('data') or {}).get('data') or [])[:50], 1) if x.get('keyword')]
        items += rows
        note('微博', rows, d.get('error'))
    if RADAR_SOURCES.get('zhihu'):
        d = tikhub('知乎', TIKHUB['知乎'])
        seen, rows = set(), []
        for z in zhihu_items(d):
            if z['title'] in seen:
                continue
            seen.add(z['title'])
            rows.append({'platform': '知乎', 'rank': len(rows) + 1, **{k: v for k, v in z.items() if v is not None}})
        rows = rows[:40]
        items += rows
        note('知乎', rows, d.get('error'))
    if RADAR_SOURCES.get('xhs'):
        d = tikhub('小红书', TIKHUB['小红书'])
        xh = ((d.get('data') or {}).get('data') or {}).get('items') or []
        rows = [{'platform': '小红书', 'rank': n, 'title': x.get('title'), 'heat': x.get('score_text')} for n, x in enumerate(xh[:20], 1)]
        items += rows
        note('小红书', rows, d.get('error'))
    if RADAR_SOURCES.get('aihot'):
        try:
            rows, err = collect_aihot()
        except Exception as ex:  # 新来源出任何问题都不能拖垮其他源
            rows, err = [], str(ex)[:200]
        items += rows
        note('AI热点', rows, err)
    if RADAR_SOURCES.get('billboard'):
        # 关键词别用「AI」：会被 AI 短剧/萌宠占满；用知识类细分词
        for name, path in BILLBOARD.items():
            rows = []
            for kw in ('AI工具', '大模型'):
                o = tikhub_post(f'{name}-{kw}', path, {'page': 1, 'page_size': 30, 'date_window': 24, 'keyword': kw, 'tags': []})
                objs = (((o.get('data') or {}).get('data') or {}).get('objs')) or []
                for n, x in enumerate(objs[:15], 1):
                    rows.append({'platform': f'抖音{name}', 'rank': n, 'title': (x.get('item_title') or '').strip()[:60],
                                 'heat': x.get('play_cnt'), 'fans': x.get('fans_cnt'), 'like': x.get('like_cnt'),
                                 'follow_rate': x.get('follow_rate'), 'item_id': x.get('item_id')})
            items += rows
            note(f'抖音{name}', rows)
    return [i for i in items if i.get('title')], status


# ---------- 话题归并 ----------
# 关键词重叠：英文/数字词 + 中文二元组，按本轮所有标题算 IDF。两条标题判成同一事件需满足其一：
#   ① 共享 ≥2 个词且共享部分占较短标题权重 ≥ 50%；② 共享 ≥2 个英文实体（DeepSeek、Gemini、Argon…）；
#   ③ 共享 1 个英文实体 + 2 个不相连的少见中文词（本轮出现 ≤6 次，如「小时」「补偿」）。
#   只共享「OpenAI」+「工程师」这类主语不算（「OpenAI 工程师被捕」和「OpenAI 工程师分享经验」是两件事），这种交给 LLM 归并判断。
# 关键词归并后，再把 AI 相关或排名前 10 的话题头（≤100 个）发给 deepseek-flash 做一次同义归并，结果要过关键词校验才采纳。
LLM_MERGE_HEADS = 100
STOP_BIGRAMS = set('如何 何看 看待 怎么 么看 怎样 评价 何评 有哪 哪些 为什 什么 么会 是否 你怎 你觉 觉得 网友 回应 曝光 最新 今天 今日 '
                   '官方 正式 宣布 发布 一个 这个 我们 大家 多少 可以 已经 真的 如果 还是 视频 热搜 相关 怎么 称其 表示 消息'.split())
GENERIC_ASCII = {'ai', 'app', 'the', 'vs', 'of', 'and', 'new', 'api', 'pro', 'max', 'plus', 'mini', 'vip', 'cm', 'kg'}


def tokens(title):
    t = title.lower()
    out = {w for w in re.findall(r'[a-z0-9]+(?:[.\-][a-z0-9]+)*', t) if not (w.isdigit() and len(w) < 2)}
    for run in re.findall(r'[一-鿿]+', t):
        out |= {run[i:i + 2] for i in range(len(run) - 1)} - STOP_BIGRAMS
    return out


def is_entity(tok):
    return tok.isascii() and len(tok) >= 3 and tok not in GENERIC_ASCII


def same_event(a, b, idf, df):
    common = a & b
    if not common:
        return False
    ents = [t for t in common if is_entity(t)]
    rare_cn = {t for t in common if not t.isascii() and df.get(t, 0) <= 6}
    # 相连的二元组算一个词：「工程」「程师」都来自「工程师」，只算 1 个
    cn_words = sum(1 for t in rare_cn if not any(o[1] == t[0] for o in rare_cn if o != t))
    if len(ents) >= 2 or (ents and cn_words >= 2):
        return True
    if len(common) >= 2:
        w = lambda s: sum(idf[t] for t in s)
        return w(common) / max(1e-9, min(w(a), w(b))) >= 0.5
    return False


def rank_pts(rank):
    """前 10 名沿用 TrendRadar：(11 - 名次) × 10；11–25 名给 5 分（延续旧版「≤25 名 +1」）；更靠后 0 分。"""
    return (11 - rank) * 10 if rank <= 10 else 5 if rank <= 25 else 0


def llm_merge(heads, items, toks):
    """heads: [(cluster_id, [item idx...])]。返回 LLM 认为同一事件、且通过关键词校验的 cluster_id 分组。"""
    if len(heads) < 2:
        return []
    titles = [items[ids[0]]['title'] for _, ids in heads]
    key = hashlib.md5('\n'.join(titles).encode()).hexdigest()[:10]
    f = bucket_cache(f'merge-{key}')
    if f.exists():
        groups = json.loads(f.read_text())
    else:
        lines = '\n'.join(f'{k}. {t}' for k, t in enumerate(titles))
        prompt = f"""下面是各平台热榜上的话题标题（已初步去重）。找出「讲的是同一件具体事情」的标题并分组：
同一主体做的同一件事、同一事件的不同说法或后续，算一组；同一家公司的不同新闻、同一领域的不同事件，不算。
每组输出一行 JSON 数组（序号），例如 [3, 17]；只输出含 2 个及以上序号的组，没有就输出「无」。不要解释。
{lines}"""
        try:
            out = llm(prompt, model='deepseek-flash', temperature=0)
            groups = [[int(n) for n in re.findall(r'\d+', m)] for m in re.findall(r'\[\s*\d+\s*(?:,\s*\d+\s*)+\]', out)]
        except Exception as ex:
            print(f'[radar] llm merge failed: {ex}', file=sys.stderr)
            return []
        f.write_text(json.dumps(groups))
    def backed(a, b):  # 关键词校验：至少共享 1 个中文词或 2 个英文实体；只共享「OpenAI」这种单个公司名的不采纳
        common = a & b
        return any(not t.isascii() for t in common) or sum(map(is_entity, common)) >= 2
    res = []
    for g in groups:
        g = [k for k in dict.fromkeys(g) if 0 <= k < len(heads)]
        if len(g) < 2:
            continue
        base = set().union(*(toks[i] for i in heads[g[0]][1]))
        keep = [g[0]] + [k for k in g[1:] if backed(base, set().union(*(toks[i] for i in heads[k][1])))]
        if len(keep) >= 2:
            res.append([heads[k][0] for k in keep])
    return res


def cluster(items, use_llm=True):
    """把同一事件的不同标题归成一簇，返回 [[item idx...]]，每簇按名次分从高到低排。"""
    toks = [tokens(x['title']) for x in items]
    df = {}
    for s in toks:
        for t in s:
            df[t] = df.get(t, 0) + 1
    n = len(items)
    idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
    order = sorted(range(n), key=lambda i: -rank_pts(items[i]['rank']))
    clusters = []
    for i in order:
        hit = next((c for c in clusters if any(items[j]['title'] == items[i]['title'] or same_event(toks[i], toks[j], idf, df) for j in c[:6])), None)
        if hit is not None:
            hit.append(i)
        else:
            clusters.append([i])
    if use_llm:
        heads = [(k, c) for k, c in enumerate(clusters)
                 if any(AI_RE.search(items[j]['title']) for j in c) or max(rank_pts(items[j]['rank']) for j in c) >= 10]
        heads = sorted(heads, key=lambda h: -max(rank_pts(items[j]['rank']) for j in h[1]))[:LLM_MERGE_HEADS]
        parent = list(range(len(clusters)))

        def root(k):
            while parent[k] != k:
                parent[k] = parent[parent[k]]
                k = parent[k]
            return k
        for g in llm_merge(heads, items, toks):
            for k in g[1:]:
                parent[root(k)] = root(g[0])
        merged = {}
        for k, c in enumerate(clusters):
            merged.setdefault(root(k), []).extend(c)
        clusters = list(merged.values())
    return [sorted(c, key=lambda i: -rank_pts(items[i]['rank'])) for c in clusters]


def heat_points(items):
    """每条在本平台内的热度分：热度值 / 本平台榜首热度 × 100；没有热度值就用名次分代替。"""
    mx = {}
    for x in items:
        h = parse_heat(x.get('heat'))
        if h:
            mx[x['platform']] = max(mx.get(x['platform'], 0), h)
    out = []
    for x in items:
        h, m = parse_heat(x.get('heat')), mx.get(x['platform'])
        out.append(100 * h / m if h and m else rank_pts(x['rank']))
    return out


def cross_score(members, items, hp):
    best = {}  # 平台 -> (名次分, 热度分, 名次)
    for i in members:
        x = items[i]
        r, h = rank_pts(x['rank']), hp[i]
        p = best.get(x['platform'])
        best[x['platform']] = (max(r, p[0]), max(h, p[1]), min(x['rank'], p[2])) if p else (r, h, x['rank'])
    n = len(best)
    freq = 100 * (1 - 0.5 ** (n - 1))  # 1 个平台 0，2 个 50，3 个 75，4 个 87.5：第二个平台的信息量最大，之后递减
    rank = max(v[0] for v in best.values())
    heat = max(v[1] for v in best.values())
    score = round(W_FREQ * freq + W_RANK * rank + W_HEAT * heat, 1)
    sources = [f'{p}#{v[2]}' for p, v in sorted(best.items(), key=lambda kv: kv[1][2])]
    return score, {'platforms': n, 'freq': round(freq, 1), 'rank': rank, 'heat': round(heat, 1)}, sources


def guess_column(t):
    if re.search(r'值不值|会员|价格|多少钱|省了|成本|账单|收费|免费', t):
        return '算账'
    if re.search(r'教程|提示词|怎么|如何|清单|必备|设置|步骤|指南|入门|技巧|方法|工作流', t):
        return '抄作业'
    if re.search(r'热点|发布|上线|宕机|崩|官宣|刚刚', t):
        return '热点'
    return '先试'


def score(new_items):
    """deepseek-flash 批量判断：AI 相关度、能否用 AI 角度借势、敏感度、建议角度。"""
    if not new_items:
        return {}
    lines = '\n'.join(f'{k}. [{x.get("_where") or (x["platform"] + "#" + str(x["rank"]))}] {x["title"]}' for k, x in enumerate(new_items))
    prompt = f"""你是一个 AI 科技自媒体（人设"示例作者"，男性产品人、自己也在创业，主打 AI 热点说人话、AI 工具实测）的选题编辑，目标是借热点涨粉。
下面是各平台热榜上的新话题（方括号里是它出现的平台和排名，出现在多个平台说明更热）。对每一条输出一行 JSON（不要多余文字）：
{{"i":序号,"ai":0-3(与AI/科技直接相关程度),"ride":0-3(能否自然地用AI视角切入并对读者有用；硬蹭得0),"risk":0-3(政治/灾难/伤亡/未成年/明星隐私/低俗/谣言风险，越高越不能碰),"angle":"一句话切入角度(≤30字)"}}
只输出 ai+ride>=3 且 risk<=1 的条目；没有就输出空。
{lines}"""
    try:
        out = llm(prompt, model='deepseek-flash', temperature=0.2)
    except Exception as ex:
        print(f'[radar] llm failed: {ex}', file=sys.stderr)
        return {}
    res = {}
    for m in re.finditer(r'\{[^{}]*\}', out):
        try:
            d = json.loads(m.group(0))
            res[int(d['i'])] = d
        except Exception:
            pass
    return res


def main():
    ap = argparse.ArgumentParser(description='热点雷达（只读各平台热榜并打分，不发布任何内容）')
    ap.add_argument('--dry-run', action='store_true', help='不写 seen 状态、不进选题库，结果写 <HHMM>-dry.json')
    ap.add_argument('--no-llm-merge', action='store_true', help='只用关键词归并')
    args = ap.parse_args()

    items, source_status = collect()
    state_p = ROOT / 'state/radar_seen.json'
    seen = json.loads(state_p.read_text()) if state_p.exists() else {}
    ts = now().isoformat()
    # 24 小时内见过的标题不再重复评估
    cutoff = now().timestamp() - 86400
    seen = {k: v for k, v in seen.items() if v.get('ts', 0) > cutoff}

    hot_idx = [i for i, x in enumerate(items) if x['platform'] not in GROWTH_PLATFORMS]
    hot = [items[i] for i in hot_idx]
    clusters = cluster(hot, use_llm=not args.no_llm_merge)
    hp = heat_points(hot)

    # 每个含新标题的话题簇只送一个代表去打分（名次最好的新标题），方括号里带上它在各平台的位置
    jobs = []  # (类型, 簇号或 items 下标, 代表条目)
    for k, c in enumerate(clusters):
        fresh = [i for i in c if hot[i]['title'] not in seen]
        if not fresh:
            continue
        cs, detail, sources = cross_score(c, hot, hp)
        rep = dict(hot[fresh[0]])
        rep['_where'] = '、'.join(sources[:4])
        jobs.append(('hot', k, rep, cs, any(AI_RE.search(hot[i]['title']) for i in c)))
    jobs.sort(key=lambda j: (not j[4], -j[3]))  # AI 相关的、更热的先打分
    for i, x in enumerate(items):
        if x['platform'] in GROWTH_PLATFORMS and x['title'] not in seen:
            jobs.append(('growth', i, x, 0, bool(AI_RE.search(x['title']))))
    jobs = jobs[:MAX_SCORE_TOPICS]
    scored = {}
    for off in range(0, len(jobs), 60):  # 分批打分，避免排在后面的平台被截掉又被标记成已见
        scored.update({off + k: v for k, v in score([j[2] for j in jobs[off:off + 60]]).items()})

    cands, growth, evaluated = [], [], set()
    for n, (kind, ref, rep, _, ai_hit) in enumerate(jobs):
        s = scored.get(n)
        if kind == 'growth':
            evaluated.add(rep['title'])
            x = rep
            if not (s or ai_hit):
                continue
            c = {**x, 'ai': (s or {}).get('ai', 2 if ai_hit else 0), 'ride': (s or {}).get('ride', 1), 'risk': (s or {}).get('risk', 0),
                 'angle': (s or {}).get('angle', '')}
            # 已被验证能给小号带来流量/关注的选题：给批次当选题参考，不触发快反
            if c['risk'] <= 1 and c['ride'] >= 2:
                growth.append(c)
            continue
        members = clusters[ref]
        evaluated.update(hot[i]['title'] for i in members)
        if not (s or ai_hit):
            continue
        x = {k: v for k, v in rep.items() if not k.startswith('_')}
        c = {**x, 'ai': (s or {}).get('ai', 2 if ai_hit else 0), 'ride': (s or {}).get('ride', 1), 'risk': (s or {}).get('risk', 0),
             'angle': (s or {}).get('angle', '')}
        if c['risk'] > 1:
            continue
        content = c['ai'] + c['ride'] + max(0, 3 - c['risk'])
        cs, detail, sources = cross_score(members, hot, hp)
        c['llm_score'] = content + (2 if x['rank'] <= 10 else 1 if x['rank'] <= 25 else 0)  # 旧版 score 算法，留作对照
        c['cross_score'] = cs
        c['cross_detail'] = detail
        c['score'] = round(SCORE_SCALE * (W_LLM * min(content, LLM_MAX) / LLM_MAX + W_CROSS * cs / 100), 2)
        c['sources'] = sources
        c['merged_titles'] = list(dict.fromkeys(hot[i]['title'] for i in members))[:8]
        if 'douyin_hot_event' not in c:  # 代表不是抖音条目时，从同簇的抖音条目借 hot_event，抖音发布时可直接挂
            dy = next((hot[i] for i in members if hot[i].get('douyin_hot_event')), None)
            if dy:
                c['douyin_hot_event'] = dy['douyin_hot_event']
        zq = next((hot[i] for i in members if hot[i]['platform'] == '知乎' and hot[i].get('url')), None)
        if zq:  # 同簇有知乎热榜问题：知乎快反直接去回答它
            c['zhihu_url'] = zq['url']
        cands.append(c)

    uniq = {}
    for g in sorted(growth, key=lambda g: -(g.get('follow_rate') or 0)):
        uniq.setdefault(g['title'][:20], g)
    growth = list(uniq.values())
    if growth and not args.dry_run:  # 自动进选题库，7 天有效，批次用 topics.py list 能看到
        import topics
        rows = topics.load()
        n = topics.add_rows(rows, [{'title': g['angle'] or g['title'][:30], 'column': guess_column(g['title'] + g['angle']), 'crowd': '',
                                    'platforms': ['douyin', 'channels', 'xhs'], 'score': 8,
                                    'angle': f"对标：{g['platform']}#{g['rank']}「{g['title'][:40]}」",
                                    'source': f"https://www.douyin.com/video/{g['item_id']}" if g.get('item_id') else '',
                                    'expires': (now() + dt.timedelta(days=7)).date().isoformat()} for g in growth[:8]])
        topics.save(rows)
    new_titles = {x['title'] for x in items if x['title'] not in seen}
    for x in items:  # 超出打分上限、没评估到的新标题不标记已见，下一轮继续评估
        if x['title'] in evaluated or x['title'] in seen:
            seen.setdefault(x['title'], {'ts': now().timestamp(), 'first': ts, 'platform': x['platform'], 'rank': x['rank']})
    if not args.dry_run:
        state_p.write_text(json.dumps(seen, ensure_ascii=False))
    cands.sort(key=lambda c: (-c['score'], -c['cross_score']))
    outd = ROOT / 'days' / now().date().isoformat() / 'radar'
    outd.mkdir(parents=True, exist_ok=True)
    meta = {'at': ts, 'total': len(items), 'new': len(new_titles), 'topics': len(clusters), 'source_counts': source_status}
    (outd / f'{now():%H%M}{"-dry" if args.dry_run else ""}.json').write_text(
        json.dumps({**meta, 'candidates': cands, 'growth_topics': growth}, ensure_ascii=False, indent=1))
    print(json.dumps({**meta, 'candidates': cands[:12], 'growth_topics': growth[:8]}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
