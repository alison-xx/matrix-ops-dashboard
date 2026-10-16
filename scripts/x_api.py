#!/usr/bin/env python3
"""X official API adapter. Uses ops.sqlite3; no browser cookies or private endpoints.

x_api.py status                         Local readiness only; no paid call
x_api.py check post.json                Validate content/review; no paid call
x_api.py add ID HH:MM post.json         Queue audited content in the existing dispatcher
x_api.py submit ID                      Send once when due; unknown result is not retried
x_api.py inbox                          Read incoming mentions, save a private local snapshot

Credentials: config/x-api-secrets.json (0600), OAuth 1.0a consumer_key,
consumer_secret, access_token, access_token_secret. Never print these values.
"""
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys
import unicodedata

from common import ROOT, now, dump

POLICY = ROOT / 'config/x-api.json'
SECRETS = ROOT / 'config/x-api-secrets.json'
AUDIT_CHECKS = {'human-writing', 'humanizer-zh', 'content-compliance-checker'}
API = 'https://api.x.com/2'


class ApiError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(f'X API HTTP {code}; see official console for details')


def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def policy_load():
    return json.loads(POLICY.read_text())


def account_load():
    return json.loads((ROOT / 'config/schedule.json').read_text())['accounts']['x']


def weight_upper_bound(text):
    """Conservative bound: complex emojis/long URLs may be overcounted, never truncated."""
    def count(s):
        return sum(1 if ord(c) <= 0x10ff or 0x2000 <= ord(c) <= 0x200d or
                   0x2010 <= ord(c) <= 0x201f or 0x2032 <= ord(c) <= 0x2037 else 2 for c in s)
    total, start = 0, 0
    for m in re.finditer(r'https?://[^\s]+', text):
        total += count(text[start:m.start()]) + max(23, count(m.group()))
        start = m.end()
    return total + count(text[start:])


def validate_post(post, policy=None):
    text = post.get('body')
    if not isinstance(text, str) or not text.strip():
        raise ValueError('正文为空')
    if post.get('kind') != 'text' or post.get('images') or post.get('video'):
        raise ValueError('当前API适配仅接纯文字；媒体走独立审核接入')
    if not post.get('column') or float(post.get('score', 0)) < 7:
        raise ValueError('缺栏目或选题评分不足7')
    text = unicodedata.normalize('NFC', text)
    if any(c in text for c in ('\x00', '\ufeff', '\ufffe', '\uffff')) or weight_upper_bound(text) > 280:
        raise ValueError('X正文无效或保守加权长度超过280；改稿后重新审核')
    if re.search(r'@[A-Za-z0-9_]{1,15}', text):
        raise ValueError('无人值守主动@未启用')
    if post.get('reply_to'):
        # Platform approval and recipient opt-in must both be implemented before enabling.
        raise ValueError('AI自动回复未开通：需X书面许可及入站同意核验，不能通过配置绕过')
    from lint_content import HYPE, AI_ERR, PLACEHOLDER
    if any(w in text for w in HYPE) or any(re.search(p, text) for p in AI_ERR + PLACEHOLDER):
        raise ValueError('内容措辞检查未通过，改稿后复核')
    return text


def checked_post(path, account=None):
    path = pathlib.Path(path).resolve()
    post = json.loads(path.read_text())
    account = account or account_load()
    if post.get('account') != account['handle']:
        raise ValueError('目标账号与排期不符')
    text = validate_post(post)
    rv = path.parent / 'review.md'
    if not rv.exists():
        raise ValueError('缺审核记录review.md')
    # Hashes bind each final artifact, allowing multiple posts in one directory.
    rf = path.with_suffix('.review.json')
    if not rf.exists():
        rf = path.parent / 'review.json'
    review = json.loads(rf.read_text()) if rf.exists() else {}
    if review.get('status') != 'pass' or review.get('sha256') != digest(path) or not AUDIT_CHECKS <= set(review.get('checks', [])):
        raise ValueError('缺完整审核或审核版本与最终稿不一致')
    return path, post, text


def _event(c, iid, kind, data, at):
    c.execute('INSERT INTO events(at,item,kind,data) VALUES(?,?,?,?)', (at.isoformat(), iid, kind, dump(data)))


def _update(c, iid, status, detail, at, url=None):
    c.execute('UPDATE items SET status=?,detail=?,updated=?,url=COALESCE(?,url),url_verified=? WHERE id=?',
              (status, detail, at.isoformat(), url, int(status == 'public'), iid))
    _event(c, iid, 'x_api', {'status': status, 'detail': detail, 'url': url}, at)
    return {'id': iid, 'status': status, 'detail': detail, 'url': url}


def add(c, iid, hhmm, path, account=None, at=None):
    at = at or now()
    account = account or account_load()
    path, post, text = checked_post(path, account)
    if post.get('id') != iid:
        raise ValueError('id与post.json不一致')
    day = dt.date.fromisoformat(post['day']).isoformat()
    due = dt.datetime.fromisoformat(f'{day}T{hhmm}:00').replace(tzinfo=at.tzinfo)
    if post.get('time') != hhmm or due < at - dt.timedelta(minutes=10):
        raise ValueError('排期不一致或已过期超过10分钟')
    c.execute('BEGIN IMMEDIATE')
    try:
        if c.execute('SELECT 1 FROM items WHERE id=?', (iid,)).fetchone():
            raise ValueError('条目已存在，先核实原生定时/台账，禁止覆盖')
        for r in c.execute("SELECT payload FROM items WHERE slot='x' AND status!='withdrawn'"):
            old = pathlib.Path(r['payload'])
            if old.exists() and unicodedata.normalize('NFC', json.loads(old.read_text()).get('body', '')).strip() == text.strip():
                raise ValueError('X重复正文，先核实原有条目')
        c.execute('INSERT INTO items(id,day,slot,platform,account_id,publish_type,due,mode,status,payload,hash,title,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                  (iid, day, 'x', 'X', account['account_id'], 'text', due.isoformat(), 'dispatch', 'ready', str(path), digest(path), post.get('title', text[:30]), at.isoformat()))
        _event(c, iid, 'x_api_add', {'review_hash': digest(path)}, at)
        c.execute('COMMIT')
    except Exception:
        c.execute('ROLLBACK')
        raise
    return {'id': iid, 'status': 'ready', 'due': due.isoformat(), 'mode': 'dispatch'}


def reserve(c, policy, at, kind, amount):
    """Reserve a conservative cost before network I/O, shared across concurrent tasks.
    These are local upper estimates, not a statement of X's actual billed amount.
    """
    c.execute('CREATE TABLE IF NOT EXISTS x_api_budget(at TEXT, day TEXT, kind TEXT, reserved_usd REAL)')
    c.execute('BEGIN IMMEDIATE')
    try:
        day = at.date().isoformat()
        start = policy.get('cycle_start') or day
        if start > day:
            raise ValueError('计费周期尚未开始')
        daily = c.execute('SELECT COALESCE(SUM(reserved_usd),0) FROM x_api_budget WHERE day=?', (day,)).fetchone()[0]
        cycle = c.execute('SELECT COALESCE(SUM(reserved_usd),0) FROM x_api_budget WHERE day>=?', (start,)).fetchone()[0]
        writes = c.execute("SELECT COUNT(*) FROM x_api_budget WHERE day=? AND kind='publish'", (day,)).fetchone()[0]
        if kind == 'publish' and writes >= policy.get('max_writes_per_day', 2):
            raise ValueError('X当日自动发帖上限已到')
        if daily + amount > policy.get('daily_usd_limit', 0) + 1e-9 or cycle + amount > policy.get('cycle_usd_limit', 0) + 1e-9:
            raise ValueError('X API本地预算上限不足，未调用API')
        c.execute('INSERT INTO x_api_budget VALUES(?,?,?,?)', (at.isoformat(), day, kind, amount))
        c.execute('COMMIT')
    except Exception:
        c.execute('ROLLBACK')
        raise


class Client:
    def __init__(self):
        import requests
        from requests_oauthlib import OAuth1
        if not SECRETS.exists() or SECRETS.stat().st_mode & 0o077:
            raise ValueError('X凭据不存在或文件权限不是0600')
        s = json.loads(SECRETS.read_text())
        keys = ('consumer_key', 'consumer_secret', 'access_token', 'access_token_secret')
        if not all(s.get(k) for k in keys):
            raise ValueError('X OAuth1.0a四项凭据不完整')
        self.session = requests.Session()
        self.session.auth = OAuth1(*(s[k] for k in keys))

    def request(self, method, path, data=None, params=None):
        import requests
        allowed = method == 'POST' and path == '/tweets' or method == 'GET' and (
            path == '/users/me' or re.fullmatch(r'/tweets/\d+', path) or re.fullmatch(r'/users/\d+/(tweets|mentions)', path))
        if not allowed:
            raise ValueError('X API动作未开放')
        # No redirects and no automatic retries for writes. Never log headers or raw failures.
        try:
            r = self.session.request(method, API + path, json=data, params=params, timeout=30, allow_redirects=False)
        except requests.RequestException:
            raise TimeoutError('X API连接异常，结果需核实') from None
        if not 200 <= r.status_code < 300:
            raise ApiError(r.status_code)
        try:
            return r.json()
        except ValueError:
            raise TimeoutError('X API响应无法解析，结果需核实') from None


def submit(c, iid, client=None, policy=None, at=None):
    at = at or now()
    r = c.execute('SELECT * FROM items WHERE id=?', (iid,)).fetchone()
    if not r or r['slot'] != 'x' or r['mode'] != 'dispatch' or r['status'] != 'ready':
        raise ValueError('X条目不是ready，禁止重复提交')
    if dt.datetime.fromisoformat(r['due']) > at:
        raise ValueError('未到发布时间')
    policy = policy if policy is not None else policy_load()
    if not policy.get('enabled'):
        return _update(c, iid, 'blocked', '官方API尚未启用，等待读写凭据/预算授权', at)
    try:
        if at - dt.datetime.fromisoformat(r['due']) > dt.timedelta(minutes=10):
            raise ValueError('排期已过10分钟，重新核查文案与间隔后补发')
        if digest(r['payload']) != r['hash']:
            raise ValueError('预检后正文被修改，需重新审核')
        # Account expected identity is taken from the immutable ledger row, not a new target.
        post = json.loads(pathlib.Path(r['payload']).read_text())
        path, post, text = checked_post(r['payload'], {'handle': post['account']})
        recent = c.execute("SELECT updated FROM items WHERE slot='x' AND id!=? AND status IN ('submitting','submitted','success','public','uncertain') ORDER BY updated DESC LIMIT 1", (iid,)).fetchone()
        if recent and at - dt.datetime.fromisoformat(recent['updated']) < dt.timedelta(minutes=20):
            raise ValueError('X上一条发送/待核实不足20分钟，先核实避免连发')
        reserve(c, policy, at, 'publish', 0.23)
        client = client or Client()
        identity = client.request('GET', '/users/me')['data']
        if identity.get('id') != r['account_id'] or identity.get('username', '').lower() != post['account'].lower():
            raise ValueError('X API身份不符，未发帖')
    except Exception as exc:
        return _update(c, iid, 'blocked', str(exc), at)
    cur = c.execute("UPDATE items SET status='submitting',updated=? WHERE id=? AND status='ready'", (at.isoformat(), iid))
    if cur.rowcount != 1:
        raise ValueError('已被其他任务领取，禁止重复提交')
    try:
        result = client.request('POST', '/tweets', data={'text': text})
        pid = str(result.get('data', {}).get('id', ''))
        if not pid.isdigit():
            raise TimeoutError('未返回有效作品id')
    except ApiError as exc:
        # Definite 4xx rejections are safe failures; 5xx may have created a post.
        status = 'failed' if 400 <= exc.code < 500 and exc.code not in (408, 409) else 'uncertain'
        return _update(c, iid, status, str(exc), at)
    except Exception:
        return _update(c, iid, 'uncertain', 'POST结果未知，先查本人作品，禁止自动重发', at)
    url = f"https://x.com/{post['account']}/status/{pid}"
    _update(c, iid, 'success', f'API返回作品{pid}，等待独立读取核实', at, url)
    try:
        actual = client.request('GET', f'/tweets/{pid}', params={'tweet.fields': 'author_id,created_at,public_metrics'})['data']
        if actual.get('id') != pid or actual.get('author_id') != r['account_id'] or actual.get('text') != text:
            raise ValueError('回读内容/作者不一致')
    except Exception:
        return _update(c, iid, 'success', 'API已创建作品，回读未通过；查已知URL，禁止重发', at, url)
    return _update(c, iid, 'public', '官方API创建后独立GET核实作者与正文', at, url)


def inbox(c, client=None, policy=None, at=None):
    at = at or now()
    policy = policy if policy is not None else policy_load()
    if not policy.get('enabled'):
        raise ValueError('X API尚未启用')
    # Up to 10 posts and 10 user resources, plus the identity check; budget conservatively.
    last = c.execute("SELECT MAX(at) FROM x_api_budget WHERE kind='inbox'").fetchone() if c.execute("SELECT 1 FROM sqlite_master WHERE name='x_api_budget'").fetchone() else None
    if last and last[0] and at - dt.datetime.fromisoformat(last[0]) < dt.timedelta(minutes=30):
        return {'skipped': '30分钟内已查入站，避免重复计费'}
    reserve(c, policy, at, 'inbox', 0.17)
    acc = account_load()
    client = client or Client()
    me = client.request('GET', '/users/me')['data']
    if me.get('id') != acc['account_id'] or me.get('username', '').lower() != acc['handle'].lower():
        raise ValueError('X API身份不符')
    data = client.request('GET', f"/users/{acc['account_id']}/mentions", params={'max_results': 10, 'tweet.fields': 'author_id,created_at,conversation_id,in_reply_to_user_id,referenced_tweets'})
    # The internal inbox is private and must not be synced/exported to the public dashboard.
    target = ROOT / 'state/x-api-private/inbox.json'
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    target.parent.chmod(0o700)
    tmp = target.with_suffix('.tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump({'at': at.isoformat(), 'data': data, 'auto_reply_enabled': False}, f, ensure_ascii=False, indent=2)
    tmp.chmod(0o600)
    tmp.replace(target)
    return {'incoming': len(data.get('data', [])), 'path': str(target), 'auto_reply_enabled': False}


def main():
    import argparse
    import ops
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=['status', 'check', 'add', 'submit', 'inbox'])
    ap.add_argument('args', nargs='*')
    args = ap.parse_args()
    if args.command == 'status':
        p = policy_load()
        print(dump({'enabled': p.get('enabled'), 'credentials_present': SECRETS.exists(), 'daily_usd_limit': p.get('daily_usd_limit'), 'cycle_usd_limit': p.get('cycle_usd_limit'), 'ai_reply_enabled': False}))
    elif args.command == 'check':
        path, post, text = checked_post(args.args[0])
        print(dump({'ok': True, 'sha256': digest(path), 'weighted_upper_bound': weight_upper_bound(text), 'id': post.get('id')}))
    else:
        c = ops.connect()
        if args.command == 'add':
            out = add(c, args.args[0], args.args[1], args.args[2])
        elif args.command == 'submit':
            out = submit(c, args.args[0])
        else:
            out = inbox(c)
        print(dump(out))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(dump({'ok': False, 'error': str(exc)}))
        sys.exit(1)
