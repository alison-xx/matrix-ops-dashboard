#!/usr/bin/env python3
"""只读博主新作采集。候选需人工评估，不打分、不发布、不调用 LLM。

用法: .venv/bin/python scripts/creator_watch.py [--dry-run] [--limit N]
状态和预算先原子落盘；未知响应结构视为失败，失败不覆盖成功记录。
"""
import argparse
import contextlib
import datetime as dt
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
import fcntl
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
TZ = dt.timezone(dt.timedelta(hours=8))
LOCK_PATH = ROOT / 'state/creator-watch.lock'
ALIASES = {'抖音': 'douyin', '小红书': 'xiaohongshu', 'xhs': 'xiaohongshu',
           'B站': 'bilibili', 'bili': 'bilibili', '微博': 'weibo',
           '公众号': 'wechat_mp', '微信公众号': 'wechat_mp', '视频号': 'wechat_channels',
           'x': 'twitter', 'X': 'twitter', '知乎': 'zhihu', '快手': 'kuaishou'}
# 精确路径白名单。POST 仅开放已核实的公众号/视频号只读账号作品列表。
ENDPOINTS = {
    '/api/v1/douyin/app/v3/fetch_user_post_videos': ('douyin', 'GET'),
    '/api/v1/douyin/web/fetch_user_post_videos': ('douyin', 'GET'),
    '/api/v1/xiaohongshu/app_v2/get_user_posted_notes': ('xiaohongshu', 'GET'),
    '/api/v1/bilibili/web/fetch_user_post_videos': ('bilibili', 'GET'),
    '/api/v1/weibo/app/fetch_user_timeline': ('weibo', 'GET'),
    '/api/v1/wechat_mp/v2/fetch_account_articles': ('wechat_mp', 'POST'),
    '/api/v1/wechat_channels/v2/fetch_user_videos': ('wechat_channels', 'POST'),
    '/api/v1/twitter/web/fetch_user_post_tweet': ('twitter', 'GET'),
    '/api/v1/zhihu/web/fetch_user_answers': ('zhihu', 'GET'),
    '/api/v1/kuaishou/app/fetch_user_post_v2': ('kuaishou', 'GET'),
}
SECRET_KEYS = re.compile(r'^(authorization|headers?|cookie|api[_-]?key|access[_-]?token|secret|password)$', re.I)


def platform_name(value):
    return ALIASES.get(value, value)


def money(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError('invalid cost')
    if not result.is_finite() or result < 0:
        raise ValueError('invalid cost')
    return result


def validate_base(base):
    parsed = urllib.parse.urlsplit(base)
    if (parsed.scheme != 'https' or parsed.hostname != 'api.tikhub.io'
            or parsed.username or parsed.password or parsed.port not in (None, 443)
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise ValueError('TikHub HTTPS domain required')
    return 'https://api.tikhub.io'


def _no_secrets(obj):
    if isinstance(obj, dict):
        if any(SECRET_KEYS.match(str(k)) for k in obj):
            raise ValueError('credentials must not be in config params')
        for value in obj.values():
            _no_secrets(value)
    elif isinstance(obj, list):
        for value in obj:
            _no_secrets(value)


def validate_config(config):
    cap = config.get('max_calls_per_run', 20)
    if isinstance(cap, bool) or not isinstance(cap, int) or not 0 <= cap <= 20:
        raise ValueError('max_calls_per_run must be 0..20')
    money(config['max_cost_usd_per_day'])
    hours = float(config.get('lookback_hours', 72))
    if not math.isfinite(hours) or hours <= 0:
        raise ValueError('invalid lookback_hours')
    keys = set()
    for author in config.get('authors', []):
        key = author.get('key')
        if not isinstance(key, str) or not key or key in keys:
            raise ValueError('unique author key required')
        keys.add(key)
        if not author.get('enabled', True):
            continue
        expected = ENDPOINTS.get(author.get('endpoint'))
        if expected != (platform_name(author.get('platform')), author.get('method', 'GET').upper()):
            raise ValueError('read-only endpoint/platform/method not allowlisted')
        if money(author.get('cost_usd')) <= 0:
            raise ValueError('positive conservative cost_usd required')
        minutes = float(author.get('interval_minutes', 60))
        if not math.isfinite(minutes) or minutes <= 0:
            raise ValueError('invalid interval_minutes')
        if not isinstance(author.get('params', {}), dict):
            raise ValueError('params must be object')
        _no_secrets(author.get('params', {}))


def load_credentials():
    # 与现有运营工具共用 common.env()；绝不输出 env、headers 或异常正文。
    from common import env
    values = env()
    base = validate_base(values.get('TIKHUB_API_BASE', 'https://api.tikhub.io'))
    key = values.get('TIKHUB_API_KEY')
    if not isinstance(key, str) or not key.strip():
        raise ValueError('TikHub key unavailable')
    return base, key.strip()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # 禁止携带鉴权头自动跟随任意跳转，包括同域重定向。
        raise ValueError('redirect blocked')


def fetch_author(author):
    base, key = load_credentials()
    expected = ENDPOINTS.get(author['endpoint'])
    method = author.get('method', 'GET').upper()
    if expected != (platform_name(author['platform']), method):
        raise ValueError('endpoint not allowed')
    params = author.get('params', {})
    _no_secrets(params)
    url = base + author['endpoint']
    body = None
    if method == 'GET':
        url += '?' + urllib.parse.urlencode(params, doseq=True)
    else:
        body = json.dumps(params).encode('utf-8')
    request = urllib.request.Request(url, data=body, method=method,
                                    headers={'Authorization': 'Bearer ' + key,
                                             'Accept': 'application/json',
                                             'User-Agent': 'creator-watch/1.0',
                                             'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(request, timeout=40) as response:
        raw = response.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise ValueError('response too large')
    return json.loads(raw)


def parse_time(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, (int, float)) or re.fullmatch(r'\d+(\.\d+)?', str(value)):
            stamp = float(value)
            if not math.isfinite(stamp) or stamp <= 0:
                return None
            if stamp > 10 ** 11:
                stamp /= 1000
            return dt.datetime.fromtimestamp(stamp, TZ).isoformat()
        text = str(value).strip()
        try:
            parsed = dt.datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError:
            parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=TZ)
        return parsed.astimezone(TZ).isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def _first(obj, keys):
    for key in keys:
        value = obj.get(key)
        if value is not None and value != '':
            return value
    return None


def _path(payload, path):
    value = payload
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _clean_text(value):
    if not isinstance(value, str):
        return ''
    return html.unescape(re.sub(r'<[^>]+>', '', value)).strip()


def _safe_url(value):
    if not isinstance(value, str):
        return None
    parts = urllib.parse.urlsplit(value)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        return None
    # 不持久化媒体鉴权、cookie 等查询参数。公众号 URL 的公开作品定位参数保留。
    public_keys = {'__biz', 'mid', 'idx', 'sn'}
    query = urllib.parse.urlencode([(k, v) for k, v in urllib.parse.parse_qsl(parts.query)
                                   if k in public_keys])
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, query, ''))


def provenance(item, platform, identity):
    """来源关系只采纳显式结构，不根据转推数/RT前缀/字段缺失猜原创。"""
    if platform == 'weibo' and isinstance(item.get('retweeted_status'), dict):
        return 'repost', _first(item['retweeted_status'], ('idstr', 'id', 'mid'))
    if platform == 'twitter':
        for field in ('retweeted_tweet', 'retweeted'):
            if isinstance(item.get(field), dict):
                return 'retweet', _first(item[field], ('tweet_id', 'id_str', 'id'))
    # 某些响应有明确枚举；缺省不升级为原创认证。quoted是引用关系，不是转推。
    explicit = item.get('post_type') or item.get('tweet_type')
    if explicit in ('original', 'repost', 'retweet'):
        origin = identity if explicit == 'original' else _first(item, ('original_id', 'retweeted_status_id'))
        return explicit, origin
    return 'unknown', None


def parse_posts(payload, author, at):
    if not isinstance(payload, dict) or payload.get('error'):
        raise ValueError('upstream request failed')
    # TikHub 包装码及平台包装码都要检查，避免认证/限流错当空列表。
    layer = payload
    for _ in range(3):
        if not isinstance(layer, dict):
            break
        for key in ('code', 'status_code'):
            if key in layer and str(layer[key]) not in ('0', '200'):
                raise ValueError('upstream response code')
        if layer.get('success') is False:
            raise ValueError('upstream unsuccessful')
        layer = layer.get('data')
    platform = platform_name(author['platform'])
    paths = {
        'douyin': [('data', 'aweme_list')],
        'xiaohongshu': [('data', 'data', 'notes')],
        'bilibili': [('data', 'data', 'list', 'vlist')],
        'weibo': [('data', 'items')],
        'wechat_mp': [('data', 'items'), ('data', 'articles')],
        'wechat_channels': [('data', 'videos')],
        'twitter': [('data', 'timeline')],
        'zhihu': [('data', 'data')],
        'kuaishou': [('data', 'feeds')],
    }
    if platform not in paths:
        raise ValueError('unknown platform')
    rows = None
    selected_path = None
    for path in paths[platform]:
        found = _path(payload, path)
        if isinstance(found, list):
            rows, selected_path = found, path
            break
    if rows is None:
        raise ValueError('unknown posts response shape')
    if platform == 'kuaishou' and str(_path(payload, ('data', 'result'))) not in ('1', 'None'):
        raise ValueError('upstream unsuccessful')
    posts = []
    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            continue
        item = raw
        pointer = '.'.join(selected_path) + '[%s]' % index
        if platform == 'weibo':
            if raw.get('category') != 'feed':
                continue
            item = raw.get('data', {})
            pointer += '.data'
        # 一些微信公众号列表将文章字段放在 article 对象下。
        if platform == 'wechat_mp' and isinstance(item.get('article'), dict):
            item = item['article']
            pointer += '.article'
        identity = _first(item, ('aweme_id', 'note_id', 'bvid', 'idstr', 'tweet_id',
                                 'photo_id', 'id', 'article_id', 'aid'))
        title = _first(item, ('title', 'display_title', 'desc', 'text', 'caption',
                             'description', 'digest', 'excerpt'))
        if platform == 'zhihu':
            title = item.get('question', {}).get('title') or title
        link = _safe_url(_first(item, ('url', 'article_url', 'link', 'content_url', 'share_url')))
        if platform == 'wechat_mp' and item.get('app_msg_id') is not None and item.get('idx') is not None:
            # app_msg_id是账号内消息组ID，同组多图文用idx区分，账号命名空间防跨账号误并。
            namespace = (_path(payload, ('data', 'biz_username'))
                         or author.get('params', {}).get('username') or author['key'])
            identity = '%s:%s:%s' % (namespace, item['app_msg_id'], item['idx'])
        if platform == 'wechat_mp' and identity is None and link:
            identity = 'url-' + hashlib.sha256(link.encode()).hexdigest()[:24]
        if identity is None:
            continue
        identity = str(identity)
        if platform == 'douyin':
            link = 'https://www.douyin.com/video/' + urllib.parse.quote(identity, safe='')
        elif platform == 'bilibili':
            link = 'https://www.bilibili.com/video/' + (identity if identity.startswith('BV') else 'av' + identity)
        elif platform == 'xiaohongshu':
            link = 'https://www.xiaohongshu.com/explore/' + urllib.parse.quote(identity, safe='')
        elif platform == 'weibo':
            link = 'https://m.weibo.cn/detail/' + urllib.parse.quote(identity, safe='')
        elif platform == 'twitter':
            link = 'https://x.com/i/status/' + urllib.parse.quote(identity, safe='')
        elif platform == 'zhihu' and item.get('question', {}).get('id'):
            link = 'https://www.zhihu.com/question/%s/answer/%s' % (item['question']['id'], identity)
        elif platform == 'kuaishou':
            link = 'https://www.kuaishou.com/short-video/' + urllib.parse.quote(identity, safe='')
        published = parse_time(_first(item, ('create_time', 'created', 'created_time', 'created_at',
                                            'publish_time', 'published_at', 'pub_time', 'publish_timestamp',
                                            'timestamp', 'time', 'datetime')))
        metrics = {}
        for source in (item.get('statistics', {}), item):
            if isinstance(source, dict):
                for key in ('digg_count', 'comment_count', 'collect_count', 'share_count',
                            'likes', 'collected_count', 'play', 'comment', 'favorites',
                            'bookmarks', 'like_count', 'fav_count', 'forward_count', 'voteup_count'):
                    val = source.get(key)
                    if isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val):
                        metrics[key] = val
        kind, origin = provenance(item, platform, identity)
        posts.append({'id': identity, 'platform': platform, 'title': _clean_text(title),
                      'type': kind, 'original_id': str(origin) if origin is not None else None,
                      'evidence_level': 'metadata',
                      'url': link, 'published_at': published, 'source_author_key': author['key'],
                      'observed_at': at.isoformat(), 'metrics': metrics,
                      'evidence_pointer': pointer})
    if rows and not posts:
        raise ValueError('nonempty posts list has no usable identity')
    return posts


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.' + path.name + '-', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


@contextlib.contextmanager
def process_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_PATH, 'a') as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('creator watch lock is held')
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _load_state(path):
    if path.exists():
        state = json.loads(path.read_text())  # 损坏状态须人工检查，绝不静默重建预算。
        for key in ('authors', 'seen', 'candidates', 'budget'):
            if not isinstance(state.get(key), dict):
                raise ValueError('invalid persistent state')
        for candidate in state['candidates'].values():
            candidate.setdefault('type', 'unknown')
            candidate.setdefault('original_id', None)
            candidate['evidence_level'] = 'metadata'
        return state
    return {'version': 1, 'authors': {}, 'seen': {}, 'candidates': {}, 'budget': {}}


def run(config, state_dir, output_dir, at=None, fetcher=None, dry_run=False, limit=None, clock=None):
    validate_config(config)
    clock = clock or ((lambda: at) if at is not None else (lambda: dt.datetime.now(TZ)))
    at = at or clock()
    if at.tzinfo is None:
        raise ValueError('timezone-aware now required')
    at = at.astimezone(TZ)
    state_dir, output_dir = Path(state_dir), Path(output_dir)
    with process_lock():
        return _run_locked(config, state_dir, output_dir, at, fetcher or fetch_author, dry_run, limit, clock)


def _run_locked(config, state_dir, output_dir, at, fetcher, dry_run, limit, clock):
    path = state_dir / 'state.json'
    state = _load_state(path)
    call_cap = config.get('max_calls_per_run', 20)
    if limit is not None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError('limit must be nonnegative')
        call_cap = min(call_cap, limit, 20)
    authors = config.get('authors', [])
    sources = []
    due = []
    for index, author in enumerate(authors):
        previous = state['authors'].get(author['key'], {})
        last = previous.get('last_fetch_at')
        parsed = parse_time(last)
        last_dt = dt.datetime.fromisoformat(parsed) if parsed else None
        attempted = parse_time(previous.get('last_attempt_at'))
        attempt_dt = dt.datetime.fromisoformat(attempted) if attempted else None
        checkpoints = [value for value in (last_dt, attempt_dt) if value is not None]
        checkpoint = max(checkpoints) if checkpoints else None
        source = {'key': author['key'], 'name': author.get('name', author['key']),
                  'platform': platform_name(author.get('platform')),
                  'last_fetch_at': last, 'status': 'disabled',
                  'evidence_path': previous.get('evidence_path')}
        sources.append(source)
        if not config.get('enabled', False) or not author.get('enabled', True):
            continue
        elapsed = (at - checkpoint).total_seconds() if checkpoint else float('inf')
        if elapsed < float(author.get('interval_minutes', 60)) * 60:
            source['status'] = 'retry_backoff' if previous.get('status') in ('error', 'inflight') else 'not_due'
            continue
        source['status'] = 'deferred'
        # 从成功时间加轮询间隔算到期点：过期最久者先；未成功者优先。
        deadline = (checkpoint + dt.timedelta(minutes=float(author.get('interval_minutes', 60)))
                    if checkpoint else dt.datetime.min.replace(tzinfo=TZ))
        due.append((deadline, index, author, source))
    due.sort(key=lambda row: (row[0], row[1]))
    day = at.date().isoformat()
    spent = money(state['budget'].get(day, {}).get('reserved_usd', '0'))
    daily_cap = money(config['max_cost_usd_per_day'])
    plan, projected = [], spent
    for _, _, author, source in due:
        if len(plan) >= call_cap:
            continue
        cost = money(author['cost_usd'])
        if projected + cost <= daily_cap:
            plan.append({'key': author['key'], 'cost_usd': str(cost),
                         'last_fetch_at': source['last_fetch_at']})
            projected += cost
    if dry_run:
        return {'dry_run': True, 'observed_at': at.isoformat(), 'plan': plan,
                'daily_reserved_usd': str(spent), 'projected_reserved_usd': str(projected),
                'max_cost_usd_per_day': str(daily_cap), 'sources': sources}
    new = []
    calls = 0
    finished_at = at
    run_id = at.strftime('%Y%m%dT%H%M%S%f') + '-' + uuid.uuid4().hex[:6]
    for _, _, author, source in due:
        if calls >= call_cap:
            continue
        charge_at = clock().astimezone(TZ)
        day = charge_at.date().isoformat()
        spent = money(state['budget'].get(day, {}).get('reserved_usd', '0'))
        cost = money(author['cost_usd'])
        if spent + cost > daily_cap:
            source['status'] = 'budget_exhausted'
            continue
        # 先持久化最坏账单，再发请求；崩溃、超时和平台失败均不自动退费。
        spent += cost
        calls += 1
        account = state['budget'].setdefault(day, {'reserved_usd': '0', 'calls': 0})
        account['reserved_usd'] = str(spent)
        account['calls'] += 1
        previous = state['authors'].setdefault(author['key'], {})
        previous['last_attempt_at'] = charge_at.isoformat()
        previous['status'] = 'inflight'
        atomic_json(path, state)
        evidence_path = output_dir / 'evidence' / (run_id + '-' + hashlib.sha256(author['key'].encode()).hexdigest()[:12] + '.json')
        try:
            payload = fetcher(author)
            completed_at = clock().astimezone(TZ)
            finished_at = completed_at
            posts = parse_posts(payload, author, completed_at)
            # 仅存白名单规范化字段，不写完整原响应中的 params、鉴权、headers、媒体 token。
            atomic_json(evidence_path, {'observed_at': completed_at.isoformat(), 'source_author_key': author['key'],
                                       'endpoint': author['endpoint'], 'posts': posts,
                                       'evidence_kind': 'normalized_response_projection'})
            count = 0
            for post in posts:
                key = post['platform'] + ':' + post['id']
                post['evidence_path'] = str(evidence_path.resolve())
                post['source_author_keys'] = [author['key']]
                if key in state['candidates']:
                    existing = state['candidates'][key]
                    if author['key'] not in existing['source_author_keys']:
                        existing['source_author_keys'].append(author['key'])
                    existing['last_observed_at'] = completed_at.isoformat()
                    existing.update({field: post[field] for field in ('type', 'original_id', 'evidence_level')})
                    existing['last_evidence_path'] = str(evidence_path.resolve())
                seen = state['seen'].get(key)
                # 旧版本seen没有eligibility：已有候选算已处理，其余允许按真实时间再验一次。
                if seen and seen.get('eligibility', 'processed' if key in state['candidates'] else 'pending_time') != 'pending_time':
                    continue
                if seen is None:
                    seen = {'first_observed_at': completed_at.isoformat(),
                            'source_author_key': author['key']}
                    state['seen'][key] = seen
                seen['evidence_path'] = str(evidence_path.resolve())
                stamp = post['published_at']
                age = ((completed_at - dt.datetime.fromisoformat(stamp)).total_seconds()
                       if stamp else None)
                if age is None or age < 0:
                    # 已见过元数据，但发布时刻未知/尚未来到；下轮允许补时或重新验证。
                    seen['eligibility'] = 'pending_time'
                    continue
                seen['eligibility'] = 'processed'
                if age > float(config.get('lookback_hours', 72)) * 3600:
                    continue  # 正常旧置顶已处理，不因后续字段改动重新回灌。
                post['status'] = 'pending_review'
                state['candidates'][key] = post
                new.append(post)
                count += 1
            previous.update({'last_fetch_at': completed_at.isoformat(), 'status': 'ok',
                             'evidence_path': str(evidence_path.resolve()), 'last_post_count': len(posts)})
            source.update({'status': 'ok', 'last_fetch_at': completed_at.isoformat(), 'post_count': len(posts),
                           'new_count': count, 'missing_time_count': sum(p['published_at'] is None for p in posts),
                           'evidence_path': str(evidence_path.resolve())})
        except Exception as exc:
            finished_at = max(finished_at, charge_at)
            # 不写 str(exc)、请求 URL 或响应 body，错误正文可能带鉴权和敏感参数。
            previous.update({'status': 'error', 'error_type': type(exc).__name__})
            source.update({'status': 'error', 'error_type': type(exc).__name__,
                           'last_attempt_at': at.isoformat()})
            atomic_json(evidence_path, {'observed_at': at.isoformat(), 'source_author_key': author['key'],
                                       'status': 'error', 'error_type': type(exc).__name__})
            source['attempt_evidence_path'] = str(evidence_path.resolve())
        atomic_json(path, state)
    # 待处理项跨轮保留7天，seen永不随候选过期删除，防止历史回灌。
    cutoff = finished_at - dt.timedelta(days=7)
    state['candidates'] = {key: value for key, value in state['candidates'].items()
                           if dt.datetime.fromisoformat(value['observed_at']) >= cutoff}
    candidates = sorted(state['candidates'].values(), key=lambda value: value['published_at'] or '', reverse=True)
    coverage = dict(collections_count(source['status'] for source in sources))
    result = {'observed_at': finished_at.isoformat(), 'run_started_at': at.isoformat(), 'run_id': run_id, 'calls': calls,
              'daily_reserved_usd': str(spent), 'budget_day': day, 'max_cost_usd_per_day': str(daily_cap),
              'new': new, 'candidates': candidates, 'sources': sources,
              'coverage': {'configured': len(authors), 'enabled': sum(bool(a.get('enabled', True)) for a in authors),
                           'statuses': coverage, 'scope': 'one_page_per_due_author',
                           'complete_history': False},
              'policy': {'automatic_publish': False, 'automatic_score': False,
                         'initial_lookback_hours': config.get('lookback_hours', 72),
                         'candidate_retention_days': 7}}
    atomic_json(path, state)
    atomic_json(output_dir / (run_id + '.json'), result)
    atomic_json(output_dir / 'latest.json', result)
    return result


def collections_count(values):
    out = {}
    for value in values:
        out[value] = out.get(value, 0) + 1
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'config/creator-watch.json')
    parser.add_argument('--state-dir', type=Path, default=ROOT / 'state/creator-watch')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args(argv)
    at = dt.datetime.now(TZ)
    output_dir = args.output_dir or ROOT / 'days' / at.date().isoformat() / 'creator-watch'
    try:
        config = json.loads(args.config.read_text())
        result = run(config, args.state_dir, output_dir, dry_run=args.dry_run, limit=args.limit)
        if args.dry_run:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({'calls': result['calls'], 'new': len(result['new']),
                              'candidates': len(result['candidates']), 'coverage': result['coverage'],
                              'daily_reserved_usd': result['daily_reserved_usd'],
                              'latest': str((output_dir / 'latest.json').resolve())}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'error', 'error_type': type(exc).__name__}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
