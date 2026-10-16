#!/usr/bin/env python3
"""矩阵运营工作台（本地只读看板）

只用标准库（可选 markdown-it-py 渲染 md），默认只监听 127.0.0.1:8790。
所有数据源都按只读方式打开；某个数据源坏了只影响对应区块，接口仍返回 200，
错误写在返回体的 errors 字段里。

启动:
  python dashboard/server.py                    # 数据目录默认是 dashboard/ 的上一级
  python dashboard/server.py --root /path/to/ops --port 8790
  python dashboard/server.py --demo             # 用自动生成的示例数据跑（不碰真实数据）
"""
import argparse
import ast
import base64
import datetime as dt
import hashlib
import hmac
import html
import json
import mimetypes
import os
import re
import sqlite3
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

APP_VERSION = '3.1.0'
DASH = Path(__file__).resolve().parent
STATIC = DASH / 'static'
HOST, PORT = '127.0.0.1', 8790
DEMO = False
TZ = ZoneInfo('Asia/Shanghai')

# 数据目录里的约定路径；configure() 按 --root 重新计算
ROOT = DAYS = ASSETS = OPS_DB = METRICS_DB = FANS = FANS_HIST = SCHEDULE = EXPERIMENTS = None
MANUAL = REPORTS = ENGAGE_PY = DASH_CFG = None
CFG = {}
DEFAULT_CFG = {
    'title': '矩阵运营',
    'subtitle': '运营工作台',
    'manual_dir': '运营手册',
    'manual_index': '00-必读.md',
    'manual_plan': '运营计划.md',
    'manual_changelog': '变更日志.md',
    'manual_skip': ['存档'],
    'goal': None,  # 例如 {"fans": 10000, "by": "2026-12-31", "label": "年底 1 万粉"}
    # 数据源多久没更新算「过期」（分钟）；按自己的定时任务节奏改
    'health': {'ledger': 360, 'fans': 1560, 'metrics': 840, 'radar': 90, 'runs': 240, 'evolve': 1560, 'report': 1560,
               'engagement': 1440},
}


def configure(root):
    """按数据目录计算所有路径，并读取可选的 config/dashboard.json。"""
    global ROOT, DAYS, ASSETS, OPS_DB, METRICS_DB, FANS, FANS_HIST, SCHEDULE, EXPERIMENTS, MANUAL, REPORTS, ENGAGE_PY, DASH_CFG, CFG, TZ
    ROOT = Path(root).expanduser().resolve()
    DAYS = ROOT / 'days'
    ASSETS = ROOT / 'assets'
    OPS_DB = ROOT / 'state/ops.sqlite3'
    METRICS_DB = ROOT / 'state/metrics.sqlite3'
    FANS = ROOT / 'state/fans.json'
    FANS_HIST = ROOT / 'state/fans_history.jsonl'
    SCHEDULE = ROOT / 'config/schedule.json'
    EXPERIMENTS = ROOT / 'config/experiments.json'
    REPORTS = ROOT / 'reports'
    ENGAGE_PY = ROOT / 'scripts/engage.py'
    DASH_CFG = ROOT / 'config/dashboard.json'
    user = {}
    try:
        user = json.loads(DASH_CFG.read_text(encoding='utf-8'))
    except Exception:
        pass
    CFG = {**DEFAULT_CFG, **{k: v for k, v in user.items() if not k.startswith('_')}}
    CFG['health'] = {**DEFAULT_CFG['health'], **(user.get('health') or {})}
    MANUAL = ROOT / CFG['manual_dir']
    try:
        sched = json.loads(SCHEDULE.read_text(encoding='utf-8'))
        TZ = ZoneInfo(CFG.get('timezone') or sched.get('timezone') or 'Asia/Shanghai')
    except Exception:
        TZ = ZoneInfo(CFG.get('timezone') or 'Asia/Shanghai')


configure(os.environ.get('MATRIX_ROOT') or DASH.parent)

IMG_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
VID_EXT = {'.mp4'}
FILE_EXT = IMG_EXT | VID_EXT
DAY_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

# ---------- markdown ----------
try:
    from markdown_it import MarkdownIt
    _MD = MarkdownIt('commonmark', {'html': False, 'linkify': False, 'typographer': False}).enable(['table', 'strikethrough'])
except Exception:  # pragma: no cover
    _MD = None

_URL_RE = re.compile(r'(?<![<(\["\'=/])(https?://[^\s<>()|，。；、）」』\]"\']+)')


def _autolink(text):
    def rep(m):
        url = m.group(1)
        tail = ''
        while url and url[-1] in '.,;:!?':
            tail = url[-1] + tail
            url = url[:-1]
        return f'<{url}>{tail}'
    out = []
    in_code = False
    for line in text.split('\n'):
        if line.strip().startswith('```'):
            in_code = not in_code
            out.append(line)
            continue
        if in_code:
            out.append(line)
            continue
        parts = line.split('`')
        for i in range(0, len(parts), 2):
            parts[i] = _URL_RE.sub(rep, parts[i])
        out.append('`'.join(parts))
    return '\n'.join(out)


def md(text):
    if not text:
        return ''
    if _MD is None:
        return '<pre class="md-raw">' + html.escape(text) + '</pre>'
    try:
        return _MD.render(_autolink(text))
    except Exception:
        return '<pre class="md-raw">' + html.escape(text) + '</pre>'


# ---------- 基础工具 ----------
def now():
    return dt.datetime.now(TZ)


def today():
    return now().date().isoformat()


def read_text(p):
    try:
        return Path(p).read_text(encoding='utf-8')
    except Exception:
        return None


def read_json(p, default=None):
    t = read_text(p)
    if t is None:
        return default
    try:
        return json.loads(t)
    except Exception:
        return default


def read_jsonl(p):
    out = []
    t = read_text(p)
    if not t:
        return out
    for line in t.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def mtime_iso(p):
    try:
        return dt.datetime.fromtimestamp(Path(p).stat().st_mtime, TZ).isoformat(timespec='seconds')
    except Exception:
        return None


def ro_db(path):
    uri = 'file:' + urllib.parse.quote(str(path)) + '?mode=ro'
    c = sqlite3.connect(uri, uri=True, timeout=3)
    c.row_factory = sqlite3.Row
    return c


def parse_dt(s):
    if not s:
        return None
    try:
        d = dt.datetime.fromisoformat(str(s))
        if d.tzinfo is None:
            d = d.replace(tzinfo=TZ)
        return d.astimezone(TZ)
    except Exception:
        return None


def in_dir(p, base):
    try:
        p = Path(p).resolve()
        b = Path(base).resolve()
        return p == b or b in p.parents
    except Exception:
        return False


def file_url(p):
    try:
        rel = Path(p).resolve().relative_to(ROOT)
    except Exception:
        return None
    return '/files/' + urllib.parse.quote(rel.as_posix())


SECRET_KEY = re.compile(r'token|cookie|secret|passw|apikey|api_key|authorization|^auth|sign', re.I)


def scrub(x):
    """去掉任何像密钥/cookie 的字段，避免页面上出现。"""
    if isinstance(x, dict):
        return {k: ('***' if SECRET_KEY.search(str(k)) else scrub(v)) for k, v in x.items()}
    if isinstance(x, list):
        return [scrub(v) for v in x]
    if isinstance(x, str) and re.search(r'(token|cookie|sessionid)=', x, re.I):
        return re.sub(r'((?:token|cookie|sessionid)=)[^&\s"]+', r'\1***', x, flags=re.I)
    return x


def section(errors, name, fn, default=None):
    try:
        return fn()
    except Exception as e:  # 单个数据源坏了不影响其他
        errors[name] = f'{type(e).__name__}: {e}'
        traceback.print_exc()
        return default


# ---------- 平台与账号 ----------
PLATS = [  # key, 显示名, 印章字
    ('dy', '抖音', '抖'),
    ('ks', '快手', '快'),
    ('sph', '视频号', '视'),
    ('bili', 'B站', 'B'),
    ('xhs', '小红书', '红'),
    ('wb', '微博', '微'),
    ('x', 'X', 'X'),
    ('zh', '知乎', '知'),
    ('gzh', '公众号', '公'),
]
PLAT_NAME = {k: n for k, n, _ in PLATS}
PLAT_ORDER = {k: i for i, (k, _, _) in enumerate(PLATS)}
_ALIAS = {
    'dy': ['抖音', 'douyin', 'dy', 'tiktok'],
    'ks': ['快手-open', '快手', 'kuaishou', 'ks'],
    'sph': ['视频号', 'channels', 'sph', '微信视频号'],
    'bili': ['哔哩哔哩-open', '哔哩哔哩', 'b站', 'bilibili', 'bili'],
    'xhs': ['小红书', 'xhs', 'rednote'],
    'wb': ['新浪微博', '微博', 'weibo', 'wb'],
    'x': ['x', '推特', 'twitter'],
    'zh': ['知乎', 'zhihu', 'zh'],
    'gzh': ['微信公众号', '公众号', 'wechat', 'gzh', 'mp'],
}
_ALIAS_MAP = {a.lower(): k for k, al in _ALIAS.items() for a in al}


def plat_key(name):
    if not name:
        return 'other'
    return _ALIAS_MAP.get(str(name).strip().lower(), str(name).strip().lower())


_ACC_CACHE = {'key': None, 'accs': []}


def load_accounts():
    """schedule.json 里的发布位。按文件修改时间缓存，一个请求里反复调用不重复读盘；每次返回副本。"""
    try:
        st = SCHEDULE.stat()
        key = (str(SCHEDULE), st.st_mtime_ns, st.st_size)
    except Exception:
        key = None
    if key is None or key != _ACC_CACHE['key']:
        cfg = read_json(SCHEDULE, {}) or {}
        out = []
        for slot, a in (cfg.get('accounts') or {}).items():
            if not isinstance(a, dict):
                continue
            out.append({
                'slot': slot,
                'pkey': plat_key(a.get('platform') or slot),
                'platform': PLAT_NAME.get(plat_key(a.get('platform') or slot), a.get('platform') or slot),
                'name': a.get('name') or slot,
                'account_id': a.get('account_id'),
                'times': a.get('times') or [],
                'weekdays_only': bool(a.get('weekdays_only')),
                'weekdays': a.get('weekdays') if isinstance(a.get('weekdays'), list) else None,
                'paused': bool(a.get('paused')),
                'type': a.get('type'),
                'metrics_account': a.get('metrics_account'),
            })
        _ACC_CACHE.update(key=key, accs=out)
    return [dict(a) for a in _ACC_CACHE['accs']]


def expected_on(acc, day):
    if acc.get('paused'):
        return 0
    try:
        wd = dt.date.fromisoformat(day).weekday()
    except Exception:
        wd = 0
    if acc.get('weekdays_only') and wd >= 5:
        return 0
    if acc.get('weekdays') is not None and wd not in acc['weekdays']:
        return 0  # 只在指定星期几发（0=周一），如公众号文章每周 3 篇
    return len(acc.get('times') or [])


def slot_for_metrics(platform, account):
    """作品数据的 (平台, 账号) → schedule.json 里的发布位。
    同一平台有多个号时：先看 schedule 里写的 metrics_account，再看账号名或发布位名是否包含这个账号标识，都不中就取该平台第一个号。"""
    pk = plat_key(platform)
    a = (account or '').strip().lower()
    cands = [x for x in load_accounts() if x['pkey'] == pk]
    if not cands:
        return (platform or '').lower()
    for x in cands:
        if a and (x.get('metrics_account') or '').strip().lower() == a:
            return x['slot']
    for x in cands:
        if a and (a in x['slot'].lower() or a in (x['name'] or '').lower()):
            return x['slot']
    return cands[0]['slot']


# ---------- 台账 ----------
DONE = {'success', 'public', 'web'}
QUEUE = {'draft', 'checked', 'ready', 'submitting', 'submitted', 'scheduled', 'web_pending', 'publishing'}
FAIL = {'failed', 'blocked'}
WARN = {'uncertain', 'manual_pending'}
MUTED = {'platform_draft', 'deleted_dup', 'withdrawn'}
STATUS_LABEL = {
    'manual_pending': '待本人手动发布',
    'draft': '草稿', 'checked': '已检查', 'ready': '待提交', 'submitting': '提交中', 'submitted': '已提交',
    'scheduled': '已定时', 'success': '发布成功', 'public': '已公开', 'web': '网页已发', 'platform_draft': '平台草稿箱',
    'blocked': '被拦截', 'failed': '失败', 'uncertain': '待核实', 'deleted_dup': '已删重复', 'withdrawn': '已撤销', 'web_pending': '待网页发表', 'publishing': '网页发布中',
}
RESOLVED_HINT = re.compile(r'撤掉|已撤|撤回|已取消|作废|不再重发|已处理|无需处理|已删除')


def detail_summary(detail):
    if not detail:
        return ''
    s = str(detail).strip()
    if s.startswith('{') or s.startswith('['):
        try:
            j = json.loads(s)
        except Exception:
            return s[:400]
        if isinstance(j, dict):
            tasks = j.get('tasks')
            if isinstance(tasks, list) and tasks:
                t = tasks[0] or {}
                parts = []
                if t.get('stages'):
                    parts.append(f"阶段 {t['stages']}")
                if t.get('stageStatus'):
                    parts.append(str(t['stageStatus']))
                if t.get('errorMessage'):
                    parts.append(str(t['errorMessage']))
                return '蚁小二任务：' + ('，'.join(parts) or '无状态')
            if 'ok' in j:
                if j.get('ok'):
                    return '提交返回成功' + (f"（任务 {j.get('task_id')}）" if j.get('task_id') else '')
                return ('提交失败：' + str(j.get('error') or j.get('message') or ''))[:400]
        return ''
    return s


# 失败原因归类：顺序有讲究（「上传失败：登录失效」要先算登录）；hint 是给运营的处理建议
FAIL_RULES = [
    ('login', '登录失效', re.compile(r'登录失效|未登录|重新登录|授权(已)?过期|token.{0,4}(过期|失效)|获取用户信息失败|cookie|\b401\b', re.I),
     '账号登录态掉了：重新扫码登录；同一平台不要在两处同时登录（会互相挤掉）'),
    ('network', '网络/代理', re.compile(r'ECONNREFUSED|ECONNRESET|ETIMEDOUT|EHOSTUNREACH|ENOTFOUND|socket|网络异常|网络错误|代理节点|proxy', re.I),
     '代理或网络通道不通：改走本机通道或网页发布，通道恢复后再切回'),
    ('account', '账号配置', re.compile(r'未设置代理|账号.{0,6}(异常|封禁|受限|冻结)|权限不足|\b403\b', re.I),
     '账号层面的设置问题：检查代理、实名、开放平台权限'),
    ('review', '审核/风控', re.compile(r'违规|审核不通过|风控|敏感|限流|操作频繁|过于频繁|拦截|不予通过', re.I),
     '内容或频率触发平台规则：改说法、降频，不要原样重发'),
    ('content', '素材/参数', re.compile(r'参数|校验|格式|尺寸|分辨率|时长|字数|超出|超过|不支持|文件(损坏|过大)|封面|标题.{0,4}(过长|为空)', re.I),
     '素材或字段不合平台要求：按要求改尺寸、时长、字数后重提'),
    ('timeout', '超时', re.compile(r'超时|timeout|timed out', re.I),
     '平台响应慢：隔几分钟重试一次，仍失败再排查'),
]
FAIL_OTHER = ('other', '其他', '看「发布返回原文」定位，处理后把原因补进台账备注')


FLAG_HINT = {
    'overdue': '到点 10 分钟还没提交：看「任务运行」里对应定时任务有没有开工，必要时手动提交',
    'stuck': '「提交中」超过 30 分钟：到发布工具或平台后台确认任务状态，再更新台账',
    'unconfirmed': '已到点但平台结果尚未确认：先去平台核实，再回填状态与链接，不能直接重发',
}


def fail_reason(text):
    s = text or ''
    for key, label, rx, hint in FAIL_RULES:
        if rx.search(s):
            return {'key': key, 'label': label, 'hint': hint}
    return {'key': FAIL_OTHER[0], 'label': FAIL_OTHER[1], 'hint': FAIL_OTHER[2]}


def post_json_path(payload):
    if not payload:
        return None
    p = Path(payload)
    if not p.is_absolute():
        p = ROOT / p
    if not in_dir(p, DAYS):
        return None
    if p.name.endswith('.payload.json'):
        return p.with_name(p.name[:-len('.payload.json')] + '.json')
    if p.name.endswith('.json'):
        return p
    return None


def ledger_rows():
    c = ro_db(OPS_DB)
    try:
        return [dict(r) for r in c.execute('SELECT * FROM items ORDER BY due')]
    finally:
        c.close()


def enrich_items(rows, accmap):
    """给台账条目补上：账号名、平台 key、时间、状态分组、被替代标记、栏目、缩略图。"""
    t_now = now()
    by_day_slot = {}
    for r in rows:
        by_day_slot.setdefault((r.get('day'), r.get('slot')), []).append(r)
    title_payload = {}
    for r in rows:
        if r.get('payload') and r.get('title'):
            title_payload.setdefault((r['title'] or '')[:16], r['payload'])
    out = []
    for r in rows:
        d = dict(r)
        st = d.get('status') or ''
        due = parse_dt(d.get('due'))
        upd = parse_dt(d.get('updated'))
        acc = accmap.get(d.get('slot')) or {}
        d['account_name'] = acc.get('name') or d.get('slot')
        d['pkey'] = plat_key(d.get('platform') or d.get('slot'))
        d['platform_name'] = PLAT_NAME.get(d['pkey'], d.get('platform'))
        d['time'] = due.strftime('%H:%M') if due else ''
        d['status_label'] = STATUS_LABEL.get(st, st or '未知')
        d['aired'] = False
        if st in DONE:
            b = 'done'
        elif st == 'scheduled' and due and due <= t_now:
            b = 'warn'
            d['aired'] = True
            d['status_label'] = '到点待核实'
        elif st in QUEUE:
            b = 'queue'
        elif st in FAIL:
            b = 'fail'
        elif st in WARN:
            b = 'warn'
        elif st in MUTED:
            b = 'muted'
        else:
            b = 'queue'
        d['bucket'] = b
        # 异常：到点没提交、长时间提交中
        flag = None
        if st in ('draft', 'checked', 'ready', 'web_pending') and due and t_now - due > dt.timedelta(minutes=10):
            flag = 'overdue'
        elif st in ('submitting', 'publishing') and upd and t_now - upd > dt.timedelta(minutes=30):
            flag = 'stuck'
        elif st == 'submitted' and d.get('mode') == 'dispatch' and due and t_now - due > dt.timedelta(minutes=60):
            flag = 'unconfirmed'
        if st == 'scheduled' and due and due <= t_now:
            flag = 'unconfirmed'
        d['flag'] = flag
        # 失败是否已有替代（同天同账号，同标题/同 payload/同时间，且状态正常）
        d['superseded_by'] = None
        if b in ('fail', 'warn') or (b == 'queue' and flag):
            for o in by_day_slot.get((d.get('day'), d.get('slot')), []):
                if o['id'] == d['id'] or (o.get('status') in FAIL | WARN | MUTED):
                    continue
                if b == 'queue' and o.get('status') not in DONE | {'scheduled'}:
                    continue
                if (o.get('payload') and o.get('payload') == d.get('payload')) or \
                        (o.get('title') and o.get('title') == d.get('title')) or \
                        (o.get('due') and o.get('due') == d.get('due') and (o.get('updated') or '') > (d.get('updated') or '')):
                    d['superseded_by'] = o['id']
                    break
        d['detail_text'] = detail_summary(d.get('detail'))
        d['resolved_note'] = bool(b in ('fail', 'warn') and RESOLVED_HINT.search(d['detail_text'] or ''))
        d['reason'] = fail_reason(d['detail_text'] or str(d.get('detail') or '')) if b in ('fail', 'warn') else None
        # 内容目录
        payload = d.get('payload') or title_payload.get((d.get('title') or '')[:16])
        pj = post_json_path(payload)
        d['dir'] = str(pj.parent) if pj else None
        post = read_json(pj, {}) if pj else {}
        post = post or {}
        if not (d.get('title') or '').strip():
            desc = re.sub(r'\s+', ' ', post.get('description') or post.get('digest') or '').strip()
            d['title'] = post.get('title') or post.get('short_title') or (desc[:40] if desc else '') or '（无标题）'
        d['column'] = (post or {}).get('column') or ''
        d['kind'] = (post or {}).get('kind') or d.get('publish_type') or ''
        d['thumb'] = choose_thumb(pj.parent, post) if pj else None
        d.pop('detail', None)
        d.pop('hash', None)
        out.append(d)
    return out


QA_NAME = re.compile(r'(check|sheet|shot|preview|webcheck|raw|预览|^f\d|^h\d|^k\d|^fc\.|^cover_small)', re.I)


def choose_thumb(folder, post):
    folder = Path(folder)
    if not folder.is_dir() or not in_dir(folder, DAYS):
        return None
    for pat in ('*-cover-34.jpg', '*-cover.jpg', '*-cover-43.jpg', 'cover-34.jpg', 'cover.jpg'):
        hits = sorted(folder.glob(pat))
        if hits:
            return file_url(hits[0])
    post = post or {}
    imgs = post.get('images') or []
    if imgs:
        p = (folder / str(imgs[0])).resolve()
        if p.is_file() and in_dir(p, DAYS):
            return file_url(p)
    for key in ('cover', 'cover_169'):
        if post.get(key):
            p = (folder / str(post[key])).resolve()
            if p.is_file() and in_dir(p, DAYS) and p.suffix.lower() in IMG_EXT:
                return file_url(p)
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'} and not QA_NAME.search(p.name):
            return file_url(p)
    return None


def zhihu_answers(day):
    p = DAYS / day / 'zhihu-answers.md'
    t = read_text(p)
    if not t:
        return []
    header = None
    out = []
    for line in t.splitlines():
        s = line.strip()
        if not s.startswith('|'):
            continue
        cells = [c.strip() for c in s.strip('|').split('|')]
        if all(re.fullmatch(r':?-{2,}:?', c) for c in cells if c):
            continue
        if header is None:
            header = cells
            continue
        row = dict(zip(header, cells))
        url = row.get('链接') or next((c for c in cells if c.startswith('http')), '')
        m = re.search(r'https?://\S+', url or '')
        url = m.group(0) if m else ''
        title = row.get('问题') or row.get('标题') or (cells[1] if len(cells) > 1 else '')
        n = len(out) + 1
        folder = DAYS / day / f'zhihu-answer-{n}'
        timing = row.get('时间') or ''
        note = row.get('备注') or ''
        scheduled = bool(re.search(r'定时|预排', timing + note)) and not re.search(r'已公开|已发布|已发出|已核验公开', note)
        tm = re.search(r'\d{2}:\d{2}', timing)
        due = parse_dt(f'{day}T{tm.group()}:00+08:00') if tm else None
        bucket = ('queue' if due and due > now() else 'warn') if scheduled else ('done' if url else 'warn')
        out.append({
            'id': f'zhihu-answer-{day}-{n}',
            'day': day, 'slot': 'zhihu', 'pkey': 'zh', 'platform_name': '知乎', 'account_name': '',
            'publish_type': 'answer', 'kind': '回答', 'time': row.get('时间') or '',
            'title': title, 'column': row.get('栏目') or '', 'url': url, 'status': 'scheduled' if scheduled else 'public' if url else 'uncertain',
            'status_label': ('已定时' if bucket == 'queue' else '到点待核实') if scheduled else '已回答' if url else '待核实', 'bucket': bucket, 'note': row.get('备注') or '',
            'detail_text': row.get('备注') or '', 'thumb': None, 'flag': 'unconfirmed' if bucket == 'warn' else None, 'superseded_by': None,
            'aired': False, 'is_answer': True, 'dir': str(folder) if folder.is_dir() else None,
        })
    return out


def day_dirs():
    try:
        return sorted([p.name for p in DAYS.iterdir() if p.is_dir() and DAY_RE.match(p.name)], reverse=True)
    except Exception:
        return []


# ---------- 粉丝 ----------
def fans_data():
    recs = []
    for r in read_jsonl(FANS_HIST):
        fans = r.get('fans')
        if not isinstance(fans, dict):
            continue
        at = r.get('at') or ''
        day = r.get('day') or (at[:10] if at else None)
        if day:
            recs.append({'at': at, 'day': day, 'fans': fans})
    cur = read_json(FANS, {}) or {}
    cur_at = mtime_iso(FANS)
    if cur and cur_at:
        # 历史里已经有同一次采集（同样的数、时间差 2 分钟内）就不重复加点
        ct = parse_dt(cur_at)
        dup = any(r['fans'] == cur and parse_dt(r['at']) and ct and abs((parse_dt(r['at']) - ct).total_seconds()) < 120
                  for r in recs)
        if not dup:
            recs.append({'at': cur_at, 'day': cur_at[:10], 'fans': cur, 'current': True})
    recs.sort(key=lambda x: x['at'] or x['day'])
    series = {}
    for r in recs:
        for acc, n in r['fans'].items():
            if not isinstance(n, (int, float)):
                continue
            s = series.setdefault(acc, {})
            prev = s.get(r['day'])
            if prev is None or (r['at'] or '') >= (prev['at'] or ''):
                s[r['day']] = {'day': r['day'], 'at': r['at'], 'n': n}
    out = {acc: [v for _, v in sorted(s.items())] for acc, s in series.items()}
    latest = {}
    for acc, pts in out.items():
        latest[acc] = pts[-1]['n'] if pts else None
    # 以 fans.json 为准作为“当前”
    for acc, n in cur.items():
        if isinstance(n, (int, float)):
            latest[acc] = n
    return {'series': out, 'current': latest, 'updated': cur_at, 'history_exists': FANS_HIST.exists(),
            'history_records': sum(1 for r in recs if not r.get('current'))}


def fans_deltas(series_pts, cur, day):
    """较昨日 / 较 7 天：用历史中最后一条早于今天（或早于 7 天）的记录。"""
    if cur is None or not series_pts:
        return None, None, None
    d_today = dt.date.fromisoformat(day)
    before = [p for p in series_pts if p['day'] < day]
    d1 = cur - before[-1]['n'] if before else None
    cutoff = (d_today - dt.timedelta(days=7)).isoformat()
    old = [p for p in series_pts if p['day'] <= cutoff]
    if old:
        return d1, cur - old[-1]['n'], 7
    if before:
        base = before[0]
        return d1, cur - base['n'], (d_today - dt.date.fromisoformat(base['day'])).days
    return d1, None, None


# ---------- 作品数据 ----------
_diagnose = None


def load_diagnose():
    """作品诊断借用数据目录里 scripts/metrics.py 的纯函数 diagnose_one（不调用会写库的函数）；没有就跳过。"""
    global _diagnose
    _diagnose = None
    p = ROOT / 'scripts' / 'metrics.py'
    if not p.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location('_matrix_metrics', p)
        mod = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(p.parent))
        spec.loader.exec_module(mod)
        _diagnose = getattr(mod, 'diagnose_one', None)
    except Exception:
        traceback.print_exc()
        _diagnose = None


def diagnose(x):
    if _diagnose is None:
        return []
    try:
        return list(_diagnose(x))
    except Exception:
        return []


def metrics_latest(days=7, since_ts=None):
    c = ro_db(METRICS_DB)
    try:
        since = since_ts if since_ts is not None else int((now() - dt.timedelta(days=days)).timestamp())
        q = ('SELECT platform, account, post_id, title, created, snap, m FROM snaps s WHERE created >= ? AND snap = '
             '(SELECT MAX(snap) FROM snaps t WHERE t.platform=s.platform AND t.account=s.account AND t.post_id=s.post_id) '
             'ORDER BY created DESC')
        out = []
        for r in c.execute(q, (since,)):
            try:
                x = json.loads(r['m'] or '{}')
            except Exception:
                x = {}
            x.update(platform=r['platform'], account=r['account'], id=r['post_id'], title=r['title'] or '',
                     created=r['created'], snap=r['snap'])
            out.append(x)
        return out
    finally:
        c.close()


def metrics_series(platform, account, post_id):
    c = ro_db(METRICS_DB)
    try:
        out = []
        for r in c.execute('SELECT snap, m FROM snaps WHERE platform=? AND account=? AND post_id=? ORDER BY snap',
                           (platform, account, post_id)):
            try:
                m = json.loads(r['m'] or '{}')
            except Exception:
                m = {}
            out.append({'snap': r['snap'], 'at': dt.datetime.fromtimestamp(r['snap'], TZ).isoformat(timespec='minutes'), 'm': m})
        return out
    finally:
        c.close()


def ledger_meta_index(items):
    meta = {}
    for it in items:
        t = (it.get('title') or '')[:12]
        if t:
            meta.setdefault(t, []).append(it)
    return meta


def _day_gap(a, b):
    try:
        return abs((dt.date.fromisoformat(a) - dt.date.fromisoformat(b)).days)
    except Exception:
        return 99


def match_ledger(x, meta, items):
    """作品数据 → 台账：先按链接里的作品 id，再按标题前 12 字 + 同平台 + 发布日相差不超过 1 天（同题多发时取最近的一条）。"""
    pid = re.sub(r'^\D+-', '', str(x.get('id') or ''))
    if pid and len(pid) >= 8:
        for it in items:
            if it.get('url') and pid in it['url']:
                return it
    cands = meta.get((x.get('title') or '')[:12]) or []
    day = dt.datetime.fromtimestamp(x.get('created') or 0, TZ).date().isoformat()
    pk = plat_key(x.get('platform'))
    best = sorted((c for c in cands if c.get('pkey') in (pk, None) and c.get('bucket') == 'done'),
                  key=lambda c: _day_gap(c.get('day'), day))
    if best and _day_gap(best[0].get('day'), day) <= 1:
        return best[0]
    # 标题对不上（如视频号抓到的是描述文字）时，按同一账号、发布时间相差 40 分钟内匹配
    created = x.get('created') or 0
    slot = slot_for_metrics(x.get('platform'), x.get('account'))
    near = []
    for it in items:
        if it.get('slot') != slot or it.get('bucket') != 'done':
            continue
        due = parse_dt(it.get('due'))
        if due and abs(due.timestamp() - created) <= 40 * 60:
            near.append((abs(due.timestamp() - created), it))
    return min(near, key=lambda t: t[0])[1] if near else None


def length_bucket(x):
    d = x.get('duration') or 0
    if not d:
        return '图文/文章' if x.get('type') in ('article', 'answer', 'normal') or 'duration' not in x else '未知时长'
    return '<30秒' if d < 30 else '30–90秒' if d < 90 else '90秒–3分' if d < 180 else '>3分'


def agg(rows, keyfn):
    g = {}
    for x in rows:
        k = keyfn(x)
        a = g.setdefault(k, {'key': k, 'n': 0, 'views': 0, 'likes': 0, 'favorites': 0, 'comments': 0, 'shares': 0,
                             'follows': 0, 'b2': [], 'c5': []})
        a['n'] += 1
        for f in ('views', 'likes', 'favorites', 'comments', 'shares', 'follows'):
            v = x.get(f) or 0
            a[f] += v if isinstance(v, (int, float)) else 0
        if isinstance(x.get('bounce_2s'), (int, float)):
            a['b2'].append(x['bounce_2s'])
        if isinstance(x.get('completion_5s'), (int, float)):
            a['c5'].append(x['completion_5s'])
    out = []
    for a in g.values():
        n = a['n'] or 1
        out.append({'key': a['key'], 'n': a['n'], 'views': a['views'], 'views_avg': round(a['views'] / n, 1),
                    'inter_avg': round((a['likes'] + a['favorites']) / n, 2), 'comments': a['comments'],
                    'likes': a['likes'], 'favorites': a['favorites'], 'shares': a['shares'], 'follows': a['follows'],
                    'b2_avg': round(sum(a['b2']) / len(a['b2']), 3) if a['b2'] else None,
                    'c5_avg': round(sum(a['c5']) / len(a['c5']), 3) if a['c5'] else None})
    out.sort(key=lambda a: -a['views_avg'])
    return out


def metrics_payload(days):
    errors = {}
    accs = load_accounts()
    accmap = {a['slot']: a for a in accs}
    items = section(errors, 'ledger', lambda: enrich_items(ledger_rows(), accmap), []) or []
    meta = ledger_meta_index(items)
    rows = section(errors, 'metrics', lambda: metrics_latest(days), []) or []
    for x in rows:
        slot = slot_for_metrics(x['platform'], x['account'])
        x['slot'] = slot
        x['pkey'] = plat_key(x['platform'])
        x['platform_name'] = PLAT_NAME.get(x['pkey'], x['platform'])
        x['account_name'] = (accmap.get(slot) or {}).get('name') or x['account']
        cr = dt.datetime.fromtimestamp(x['created'] or 0, TZ)
        x['created_iso'] = cr.isoformat(timespec='minutes')
        x['day'] = cr.date().isoformat()
        it = match_ledger(x, meta, items)
        x['column'] = (it or {}).get('column') or '未标'
        x['item_id'] = (it or {}).get('id')
        x['hour'] = ((it or {}).get('time') or cr.strftime('%H:%M'))[:2]
        x['len'] = length_bucket(x)
        x['tips'] = diagnose(x)
    t = now().date()
    day_list = [(t - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    series = {}
    for x in rows:
        s = series.setdefault(x['pkey'], {d: {'views': 0, 'n': 0} for d in day_list})
        if x['day'] in s:
            s[x['day']]['views'] += x.get('views') or 0
            s[x['day']]['n'] += 1
    series_out = [{'pkey': k, 'platform_name': PLAT_NAME.get(k, k),
                   'points': [{'day': d, **v} for d, v in s.items()]}
                  for k, s in sorted(series.items(), key=lambda kv: PLAT_ORDER.get(kv[0], 99))]
    kpi = {
        'posts': len(rows),
        'views': sum(x.get('views') or 0 for x in rows),
        'inter': sum((x.get('likes') or 0) + (x.get('favorites') or 0) + (x.get('comments') or 0) + (x.get('shares') or 0) for x in rows),
        'follows': sum(x.get('follows') or 0 for x in rows),
        'snap_latest': max((x['snap'] for x in rows), default=None),
    }
    if kpi['snap_latest']:
        kpi['snap_latest'] = dt.datetime.fromtimestamp(kpi['snap_latest'], TZ).isoformat(timespec='minutes')
    # 上一期（同样长度的前一个窗口）用来算环比；作品数据按最新快照，老作品的数会更完整，环比只作参考
    cut = int((now() - dt.timedelta(days=days)).timestamp())
    prev = [x for x in (section(errors, 'metrics_prev', lambda: metrics_latest(days * 2), []) or []) if (x.get('created') or 0) < cut]
    kpi_prev = {
        'posts': len(prev),
        'views': sum(x.get('views') or 0 for x in prev),
        'inter': sum((x.get('likes') or 0) + (x.get('favorites') or 0) + (x.get('comments') or 0) + (x.get('shares') or 0) for x in prev),
        'follows': sum(x.get('follows') or 0 for x in prev),
    } if prev else None
    return {
        'days': days, 'day_list': day_list, 'rows': rows, 'kpi': kpi, 'kpi_prev': kpi_prev,
        'by_platform': agg(rows, lambda x: x['platform_name']),
        'by_column': agg(rows, lambda x: x['column']),
        'by_hour': sorted(agg(rows, lambda x: f"{x['hour']}点"), key=lambda a: a['key']),
        'by_len': agg(rows, lambda x: x['len']),
        'series': series_out,
        'diagnosis_available': _diagnose is not None,
        'errors': errors,
    }


# ---------- 互动 ----------
def engage_caps():
    src = read_text(ENGAGE_PY)
    caps, maxlen = {}, {}
    if not src:
        return caps, maxlen
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ('CAPS', 'MAXLEN'):
                try:
                    v = ast.literal_eval(node.value)
                except Exception:
                    continue
                if name == 'CAPS':
                    caps = v
                else:
                    maxlen = v
    return caps, maxlen


ACTION_LABEL = {'comment': '评论', 'reply': '回复', 'like': '点赞', 'follow': '关注', 'repost': '转发', 'browse': '浏览'}
ACTION_ORDER = ['comment', 'reply', 'like', 'follow', 'repost', 'browse']


def engagement_payload(day):
    errors = {}
    recs = section(errors, 'engagement', lambda: read_jsonl(DAYS / day / 'engagement.jsonl'), []) or []
    caps, _ = section(errors, 'caps', engage_caps, ({}, {})) or ({}, {})
    counts = {}
    for r in recs:
        pk = plat_key(r.get('platform'))
        counts.setdefault(pk, {}).setdefault(r.get('action') or 'other', 0)
        counts[pk][r.get('action') or 'other'] += 1
    plats = {}
    for pname, c in (caps or {}).items():
        plats[plat_key(pname)] = {'pkey': plat_key(pname), 'platform_name': PLAT_NAME.get(plat_key(pname), pname), 'caps': c}
    for pk in counts:
        plats.setdefault(pk, {'pkey': pk, 'platform_name': PLAT_NAME.get(pk, pk), 'caps': {}})
    rows = []
    for pk, p in sorted(plats.items(), key=lambda kv: PLAT_ORDER.get(kv[0], 99)):
        acts = []
        used = counts.get(pk, {})
        keys = [a for a in ACTION_ORDER if a in p['caps'] or a in used] + [a for a in used if a not in ACTION_ORDER]
        for a in keys:
            acts.append({'action': a, 'label': ACTION_LABEL.get(a, a), 'used': used.get(a, 0), 'cap': p['caps'].get(a)})
        rows.append({'pkey': pk, 'platform_name': p['platform_name'], 'actions': acts,
                     'total': sum(used.values()), 'disabled': bool(p['caps']) and all(v == 0 for v in p['caps'].values())})
    recent = []
    for r in reversed(recs[-50:]):
        recent.append({'time': r.get('time') or '', 'pkey': plat_key(r.get('platform')),
                       'platform_name': PLAT_NAME.get(plat_key(r.get('platform')), r.get('platform')),
                       'action': r.get('action'), 'action_label': ACTION_LABEL.get(r.get('action'), r.get('action')),
                       'target': r.get('target') or '', 'text': r.get('text') or '', 'note': r.get('note') or ''})
    by_action = {}
    for r in recs:
        by_action[r.get('action')] = by_action.get(r.get('action'), 0) + 1
    return {'day': day, 'total': len(recs), 'by_action': by_action, 'platforms': rows, 'recent': recent,
            'days': day_dirs(), 'errors': errors}


# ---------- 热点 ----------
def radar_runs(day):
    out = []
    folder = DAYS / day / 'radar'
    if not folder.is_dir():
        return out
    for p in sorted(folder.glob('*.json')):
        d = read_json(p, None)
        if not isinstance(d, dict):
            continue
        out.append({'file': p.name, 'at': d.get('at') or mtime_iso(p), 'total': d.get('total'), 'new': d.get('new'),
                    'n': len(d.get('candidates') or []), 'data': d})
    out.sort(key=lambda r: r['at'] or '')
    return out


def slim_candidate(c):
    ev = c.get('douyin_hot_event') or {}
    return {
        'title': c.get('title') or '', 'score': c.get('score'), 'cross_score': c.get('cross_score'),
        'llm_score': c.get('llm_score'), 'platform': c.get('platform'), 'rank': c.get('rank'), 'heat': c.get('heat'),
        'sources': c.get('sources') or [], 'merged_titles': c.get('merged_titles') or [], 'angle': c.get('angle') or '',
        'url': c.get('url') or '', 'zhihu_url': c.get('zhihu_url') or '', 'risk': c.get('risk'),
        'answer_count': c.get('answer_count'), 'hot_event': ev.get('yixiaoerName') if isinstance(ev, dict) else None,
    }


def latest_radar(day, lookback=3):
    d0 = dt.date.fromisoformat(day)
    for i in range(lookback):
        dd = (d0 - dt.timedelta(days=i)).isoformat()
        runs = radar_runs(dd)
        if runs:
            last = runs[-1]
            with_c = [r for r in runs if r['n']]
            pick = with_c[-1] if with_c else last
            cands = sorted(pick['data'].get('candidates') or [], key=lambda c: -(c.get('score') or 0))
            return {'day': dd, 'last_at': last['at'], 'last_file': last['file'], 'last_total': last['total'],
                    'last_new': last['new'], 'last_n': last['n'], 'at': pick['at'], 'file': pick['file'],
                    'total': pick['total'], 'new': pick['new'], 'source_counts': pick['data'].get('source_counts') or {},
                    'candidates': [slim_candidate(c) for c in cands],
                    'runs': [{'file': r['file'], 'at': r['at'], 'total': r['total'], 'new': r['new'], 'n': r['n']} for r in runs]}
    return None


def hot_payload(day):
    errors = {}
    radar = section(errors, 'radar', lambda: latest_radar(day, 1), None)
    hot_log = section(errors, 'hot_log', lambda: read_text(DAYS / day / 'hot-log.md'), None)
    return {'day': day, 'radar': radar, 'hot_log_html': md(hot_log) if hot_log else '', 'hot_log_exists': hot_log is not None,
            'days': day_dirs(), 'errors': errors}


# ---------- 运营计划 / 任务运行 ----------
def manual_version():
    t = read_text(MANUAL / CFG['manual_index'])
    if t is None:
        return {'exists': False, 'version': None}
    m = re.search(r'版本\s*[:：]?\s*[*`]*\s*(v[\w.\-]+)', t)
    if not m:
        m = re.search(r'\b(v\d[\w.\-]*)', t)
    return {'exists': True, 'version': m.group(1) if m else None, 'updated': mtime_iso(MANUAL / CFG['manual_index'])}


_DATE_IN = re.compile(r'(\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?)|(\d{1,2}-\d{1,2}(?:\s+\d{1,2}:\d{2})?)')


def changelog_entries(text, n=5):
    if not text:
        return []
    entries = []
    cur = None
    for line in text.splitlines():
        m = re.match(r'^#{2,3}\s+(.*)', line)
        if m:
            cur = {'title': m.group(1).strip(), 'body': []}
            entries.append(cur)
            continue
        if cur is not None and line.strip():
            cur['body'].append(re.sub(r'^\s*[-*]\s+', '', line.strip()))
    if not entries:
        for line in text.splitlines():
            m = re.match(r'^\s*[-*]\s+(.*)', line)
            if m:
                entries.append({'title': m.group(1).strip(), 'body': []})
    dated = []
    for i, e in enumerate(entries):
        m = re.search(r'\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?', e['title']) or _DATE_IN.search(re.sub(r'v[\d.\-]+', '', e['title']))
        dated.append((m.group(0) if m else None, i, e))
    if entries and sum(1 for d in dated if d[0]) >= max(1, len(entries) // 2):
        def norm(s):
            if not s:
                return ''
            if re.match(r'^\d{4}', s):
                return s
            return '0000-' + s
        dated.sort(key=lambda d: (norm(d[0]), d[1]), reverse=True)
        entries = [d[2] for d in dated]
    out = []
    for e in entries[:n]:
        body = ' '.join(e['body'])
        out.append({'title': e['title'], 'body': body[:220] + ('…' if len(body) > 220 else '')})
    return out


def changelog_timeline(text, n=40):
    """变更日志 → 版本时间线：每个二/三级标题一条，带版本号、时间、来源和渲染后的正文。"""
    if not text:
        return []
    entries, cur = [], None
    for line in text.splitlines():
        m = re.match(r'^#{2,3}\s+(.*)', line)
        if m:
            cur = {'title': m.group(1).strip(), 'lines': []}
            entries.append(cur)
            continue
        if cur is not None:
            cur['lines'].append(line)
    out = []
    for e in entries:
        t = e['title']
        ver = re.search(r'(v\d[\w.\-]*)', t)
        when = re.search(r'(\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2})?)', t)
        src = re.search(r'来源\s*[:：]\s*([^）)，,；;\s]+)', t)
        body = '\n'.join(e['lines']).strip()
        items = [ln for ln in e['lines'] if re.match(r'^\s*[-*]\s+', ln)]
        first = re.sub(r'^\s*[-*]\s+', '', items[0]) if items else next((ln for ln in e['lines'] if ln.strip()), '')
        summary = re.sub(r'`|\*\*', '', first).strip()
        out.append({'title': t, 'version': ver.group(1) if ver else None, 'when': when.group(1) if when else None,
                    'source': src.group(1) if src else None, 'html': md(body), 'n_items': len(items),
                    'summary': summary[:160] + ('…' if len(summary) > 160 else '')})
    def vkey(o):
        m = re.match(r'v(\d{4})\.(\d{1,2})\.(\d{1,2})-(\d+)', o['version'] or '')
        return tuple(int(x) for x in m.groups()) if m else None
    if out and all(vkey(o) for o in out):
        out.sort(key=vkey, reverse=True)  # 版本号自带日期和序号，比标题里的时间更可靠
    return out[:n]


def runs_payload(days=7, only_day=None):
    t = now().date()
    out = []
    rng = [only_day] if only_day else [(t - dt.timedelta(days=i)).isoformat() for i in range(days)]
    for day in rng:
        recs = read_jsonl(DAYS / day / 'runs.jsonl')
        open_ = {}
        entries = []
        for r in recs:
            task = r.get('task') or '未命名'
            ev = r.get('event')
            if ev == 'start':
                e = {'day': day, 'task': task, 'start': r.get('at'), 'end': None, 'version': r.get('version'),
                     'summary': r.get('summary') or ''}
                entries.append(e)
                open_.setdefault(task, []).append(e)
            elif ev == 'end':
                lst = open_.get(task) or []
                if lst:
                    e = lst.pop()
                    e['end'] = r.get('at')
                    if r.get('summary'):
                        e['summary'] = r.get('summary')
                    if r.get('version'):
                        e['version'] = r.get('version')
                else:
                    entries.append({'day': day, 'task': task, 'start': None, 'end': r.get('at'), 'version': r.get('version'),
                                    'summary': r.get('summary') or ''})
            else:
                entries.append({'day': day, 'task': task, 'start': r.get('at'), 'end': r.get('at'),
                                'version': r.get('version'), 'summary': r.get('summary') or r.get('event') or ''})
        for e in entries:
            s, en = parse_dt(e['start']), parse_dt(e['end'])
            if en:
                e['state'] = 'done'
                e['minutes'] = round((en - s).total_seconds() / 60) if s else None
            else:
                e['state'] = 'running' if s and now() - s < dt.timedelta(hours=3) else 'unclosed'
                e['minutes'] = None
        out.extend(entries)
    out.sort(key=lambda e: e.get('start') or e.get('end') or '', reverse=True)
    return out


def latest_evolve():
    for day in day_dirs():
        p = DAYS / day / 'evolve.json'
        if p.exists():
            d = read_json(p, None)
            return {'day': day, 'updated': mtime_iso(p), 'data': scrub(d), 'ok': d is not None}
    return None


def plan_payload():
    errors = {}
    ver = section(errors, 'manual', manual_version, {'exists': False})
    plan = section(errors, 'plan', lambda: read_text(MANUAL / CFG['manual_plan']), None)
    log = section(errors, 'changelog', lambda: read_text(MANUAL / CFG['manual_changelog']), None)
    exp = section(errors, 'experiments', lambda: read_json(EXPERIMENTS, None), None)
    if EXPERIMENTS.exists() and exp is None and 'experiments' not in errors:
        errors['experiments'] = 'experiments.json 无法解析'
    return {
        'version': ver,
        'plan_exists': plan is not None, 'plan_html': md(plan) if plan else '', 'plan_updated': mtime_iso(MANUAL / CFG['manual_plan']),
        'changelog_exists': log is not None, 'changelog_html': md(log) if log else '',
        'changes': changelog_entries(log or '', 8),
        'timeline': changelog_timeline(log or ''),
        'experiments_exists': EXPERIMENTS.exists(),
        'experiments': scrub((exp or {}).get('experiments') if isinstance(exp, dict) else (exp if isinstance(exp, list) else [])) or [],
        'runs': section(errors, 'runs', lambda: runs_payload(7), []),
        'evolve': section(errors, 'evolve', latest_evolve, None),
        'errors': errors,
    }


# ---------- 日报 ----------
def report_path(day):
    full = REPORTS / f'{day}.full.md'
    return full if full.is_file() else REPORTS / f'{day}.md'


def reports_list():
    out = []
    if not REPORTS.is_dir():
        return out
    dates = sorted({p.name[:10] for p in REPORTS.glob('*.md') if re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:\.full)?\.md', p.name)}, reverse=True)
    for day in dates:
        p = report_path(day)
        t = read_text(p) or ''
        m = re.search(r'^#\s+(.+)$', t, re.M)
        gen = re.search(r'生成时间[:：]\s*([^\n]+)', t)
        warn = len(re.findall(r'⚠️|需要你|请确认', t))
        out.append({'date': day, 'full_day': p.name.endswith('.full.md'), 'title': m.group(1).strip() if m else p.stem, 'generated': gen.group(1).strip() if gen else None,
                    'updated': mtime_iso(p), 'size': len(t), 'attention': warn})
    return out


# ---------- 总览 ----------
def overview_payload():
    errors = {}
    day = today()
    accs = section(errors, 'schedule', load_accounts, []) or []
    accmap = {a['slot']: a for a in accs}
    items = section(errors, 'ledger', lambda: enrich_items(ledger_rows(), accmap), []) or []
    fans = section(errors, 'fans', fans_data, {'series': {}, 'current': {}, 'updated': None}) or {'series': {}, 'current': {}}
    answers = section(errors, 'zhihu_answers', lambda: zhihu_answers(day), []) or []
    today_items = [i for i in items if i.get('day') == day]
    # 近 7 天作品数据均值（按账号）
    mrows = section(errors, 'metrics', lambda: metrics_latest(7), []) or []
    mstat = {}
    for x in mrows:
        s = mstat.setdefault(slot_for_metrics(x['platform'], x['account']), {'n': 0, 'views': 0})
        s['n'] += 1
        s['views'] += x.get('views') or 0

    cards = []
    tot = {'expected': 0, 'done': 0, 'queue': 0, 'fail': 0, 'warn': 0}
    fans_total, d1_total, d7_total, d1_known, d7_known = 0, 0, 0, False, False
    seen_ids = {}
    d7_spans = []
    for a in accs:
        mine = [i for i in today_items if i.get('slot') == a['slot'] and i['bucket'] != 'muted']
        if a['slot'] == 'zhihu':
            mine = mine + answers
        live = [i for i in mine if not i.get('superseded_by') and not i.get('resolved_note')]
        c = {
            'expected': expected_on(a, day),
            'done': sum(1 for i in live if i['bucket'] == 'done'),
            'queue': sum(1 for i in live if i['bucket'] == 'queue'),
            'fail': sum(1 for i in live if i['bucket'] == 'fail'),
            'warn': sum(1 for i in live if i['bucket'] == 'warn'),
        }
        for k in tot:
            tot[k] += c[k]
        aid = a.get('account_id')
        cur = (fans.get('current') or {}).get(aid)
        pts = (fans.get('series') or {}).get(aid) or []
        d1, d7, d7span = fans_deltas(pts, cur, day)
        shared = seen_ids.get(aid) if aid else None
        if aid and not shared:
            seen_ids[aid] = a['name']
            if isinstance(cur, (int, float)):
                fans_total += cur
            if d1 is not None:
                d1_total += d1
                d1_known = True
            if d7 is not None:
                d7_total += d7
                d7_known = True
                d7_spans.append(d7span or 0)
        ms = mstat.get(a['slot']) or {}
        cards.append({**{k: a[k] for k in ('slot', 'pkey', 'platform', 'name', 'times', 'weekdays_only', 'paused', 'type')},
                      'fans': cur, 'd1': d1, 'd7': d7, 'd7_span': d7span, 'shared_with': shared,
                      'spark': [{'day': p['day'], 'n': p['n']} for p in pts[-30:]],
                      'posts7': ms.get('n', 0), 'views7_avg': round(ms['views'] / ms['n'], 1) if ms.get('n') else None,
                      **c})

    timeline = sorted(
        [i for i in today_items if i['bucket'] != 'muted' or i.get('status') == 'platform_draft'] + answers,
        key=lambda i: i.get('time') or '')
    timeline = [{k: i.get(k) for k in ('id', 'time', 'pkey', 'slot', 'account_name', 'platform_name', 'title', 'status',
                                        'status_label', 'bucket', 'url', 'aired', 'superseded_by', 'flag', 'column', 'is_answer')}
                for i in timeline]

    # 待处理：近 3 天失败/待核实/拦截（未被替代），今天到点未提交/卡住
    cutoff = (now().date() - dt.timedelta(days=2)).isoformat()
    pending, resolved = [], []
    for i in items + answers:
        if (i.get('day') or '') < cutoff:
            continue
        kind = None
        if i['bucket'] in ('fail', 'warn'):
            kind = i.get('flag') or i.get('status')
        elif i.get('flag'):
            kind = i['flag']
        if not kind:
            continue
        row = {k: i.get(k) for k in ('id', 'day', 'time', 'pkey', 'platform_name', 'account_name', 'title', 'status',
                                      'status_label', 'bucket', 'detail_text', 'superseded_by', 'updated', 'reason', 'mode', 'slot')}
        row['kind'] = kind
        row['kind_label'] = {'failed': '发布失败', 'blocked': '被拦截', 'uncertain': '待核实', 'overdue': '到点未提交',
                             'stuck': '提交卡住', 'unconfirmed': '提交后未确认'}.get(kind, kind)
        if kind in FLAG_HINT:
            row['reason'] = {'key': kind, 'label': row['kind_label'], 'hint': FLAG_HINT[kind]}
        if i.get('superseded_by') or i.get('resolved_note'):
            row['resolved_reason'] = f"已由 {i['superseded_by']} 重新提交" if i.get('superseded_by') else '备注显示已处理'
            resolved.append(row)
        else:
            pending.append(row)
    # 同一天同账号同标题的多次尝试合并成一条，显示最新一次
    def group(rows):
        out, idx = [], {}
        for r in sorted(rows, key=lambda r: r.get('updated') or '', reverse=True):
            k = (r['day'], r.get('account_name'), r.get('title'))
            if k in idx:
                idx[k]['attempts'] += 1
                idx[k]['ids'].append(r['id'])
                continue
            r['attempts'] = 1
            r['ids'] = [r['id']]
            idx[k] = r
            out.append(r)
        out.sort(key=lambda r: (r['day'], r['time'] or ''), reverse=True)
        return out
    pending_n = len(pending)
    pending, resolved = group(pending), group(resolved)

    ver = section(errors, 'manual', manual_version, {'exists': False}) or {'exists': False}
    changes = section(errors, 'changelog', lambda: changelog_timeline(read_text(MANUAL / CFG['manual_changelog']) or '', 5), []) or []
    changes = [{k: c.get(k) for k in ('title', 'version', 'when', 'source', 'summary')} for c in changes]
    eng = section(errors, 'engagement', lambda: engagement_payload(day), None)
    radar = section(errors, 'radar', lambda: latest_radar(day, 3), None)
    runs = section(errors, 'runs', lambda: runs_payload(1, day), []) or []
    return {
        'now': now().isoformat(timespec='seconds'), 'today': day, 'weekday': '一二三四五六日'[now().weekday()],
        'accounts': cards, 'publish': tot,
        'fans_total': fans_total, 'fans_d1': d1_total if d1_known else None, 'fans_d7': d7_total if d7_known else None,
        'fans_d7_span': min(d7_spans) if d7_spans else None,
        'views7_total': sum(v.get('views', 0) for v in mstat.values()),
        'posts7_total': sum(v.get('n', 0) for v in mstat.values()),
        'fans_updated': fans.get('updated'), 'fans_history': fans.get('history_exists', False),
        'fans_history_records': fans.get('history_records', 0),
        'timeline': timeline, 'planned': {a['slot']: (a['times'] if expected_on(a, day) else []) for a in accs},
        'pending': pending, 'pending_items': pending_n, 'resolved': resolved,
        'manual': {**ver, 'changes': changes, 'changelog_exists': (MANUAL / CFG['manual_changelog']).exists()},
        'engagement': {'total': eng['total'], 'by_action': eng['by_action'],
                       'platforms': [{'pkey': p['pkey'], 'platform_name': p['platform_name'], 'total': p['total'],
                                      'comment': next((a for a in p['actions'] if a['action'] == 'comment'), None)}
                                     for p in eng['platforms']]} if eng else None,
        'hot': {'at': radar['last_at'], 'day': radar['day'], 'total': radar['last_total'], 'new': radar['last_new'],
                'top': radar['candidates'][:5], 'pick_at': radar['at']} if radar else None,
        'runs': runs,
        'latest_report': next(iter(reports_list()), None),
        'sync': read_json(ROOT / '.sync.json', None),
        'evidence': {'verified': sum(1 for i in today_items + answers if i.get('status') in ('public', 'web') and i.get('url')),
                     'platform_success': sum(1 for i in today_items if i.get('status') == 'success')},
        'errors': errors,
    }


# ---------- 内容 ----------
def content_list(day, platform=None, status=None, column=None):
    errors = {}
    accs = load_accounts()
    accmap = {a['slot']: a for a in accs}
    items = section(errors, 'ledger', lambda: enrich_items(ledger_rows(), accmap), []) or []
    ledger_days = sorted({i['day'] for i in items if i.get('day')}, reverse=True)
    days = sorted(set(day_dirs()) | set(ledger_days), reverse=True)
    lst = [i for i in items if i.get('day') == day]
    lst += section(errors, 'zhihu_answers', lambda: zhihu_answers(day), []) or []
    columns = sorted({i.get('column') for i in lst if i.get('column')})
    plats = sorted({i['pkey'] for i in lst}, key=lambda k: PLAT_ORDER.get(k, 99))
    counts = {}
    for i in lst:
        counts[i['bucket']] = counts.get(i['bucket'], 0) + 1
    if platform:
        lst = [i for i in lst if i['pkey'] == platform]
    if status:
        lst = [i for i in lst if i['bucket'] == status or i.get('status') == status]
    if column:
        lst = [i for i in lst if (i.get('column') or '未标') == column]
    lst.sort(key=lambda i: (i['bucket'] == 'muted', i.get('time') or ''))
    for i in lst:
        i.pop('dir', None)
    return {'day': day, 'days': days, 'items': lst, 'columns': columns, 'platforms': plats, 'counts': counts,
            'errors': errors}


def media_of(folder, post):
    folder = Path(folder)
    final, process, videos = [], [], []
    if not folder.is_dir() or not in_dir(folder, DAYS):
        return final, process, videos
    ref = set()
    post = post or {}
    for key in ('cover', 'cover_169', 'video'):
        if post.get(key):
            ref.add((folder / str(post[key])).resolve())
    for im in post.get('images') or []:
        ref.add((folder / str(im)).resolve())
    seen = set()
    # 引用的视频可能在别的日期目录；引用的图片可能在子目录（如 cards/）
    for p in sorted(ref):
        if p.is_file() and in_dir(p, DAYS) and p.suffix.lower() in VID_EXT:
            videos.append({'url': file_url(p), 'name': p.name})
            seen.add(p)
    for im in post.get('images') or []:
        p = (folder / str(im)).resolve()
        if p.is_file() and in_dir(p, DAYS) and p.suffix.lower() in IMG_EXT and p not in seen:
            final.append({'url': file_url(p), 'name': p.name})
            seen.add(p)
    for key in ('cover', 'cover_169'):
        if post.get(key):
            p = (folder / str(post[key])).resolve()
            if p.is_file() and in_dir(p, DAYS) and p.suffix.lower() in IMG_EXT and p not in seen:
                final.append({'url': file_url(p), 'name': p.name})
                seen.add(p)
    for p in sorted(folder.iterdir()):
        if not p.is_file():
            continue
        s = p.suffix.lower()
        rp = p.resolve()
        if rp in seen:
            continue
        if s in VID_EXT:
            if '-web' in p.name and any(v['name'] == p.name.replace('-web', '') for v in videos):
                continue
            videos.append({'url': file_url(p), 'name': p.name})
        elif s in IMG_EXT:
            entry = {'url': file_url(p), 'name': p.name}
            if re.search(r'cover', p.name) and not re.search(r'raw|check|small', p.name):
                final.append(entry)
            else:
                process.append(entry)
    # 封面排前面，然后按 post.images 顺序
    order = {e['url']: i for i, e in enumerate(final)}
    final.sort(key=lambda e: (0 if 'cover' in e['name'] and '-34' in e['name'] else 1 if 'cover' in e['name'] else 2,
                              order.get(e['url'], 99)))
    # 封面只留一张主封面放在成品里，其他尺寸单独列出
    covers = [e for e in final if re.search(r'cover', e['name'])]
    if len(covers) > 1:
        primary = covers[0]
        final = [e for e in final if e is primary or e not in covers]
        process = [{**e, 'variant': True} for e in covers[1:]] + process
    return final, process, videos


def item_events(item_id):
    c = ro_db(OPS_DB)
    try:
        out = []
        for r in c.execute('SELECT at, kind, data FROM events WHERE item=? ORDER BY n', (item_id,)):
            data = r['data']
            try:
                j = json.loads(data) if data else None
                txt = ''
                if isinstance(j, dict):
                    keep = {k: v for k, v in scrub(j).items() if not isinstance(v, (dict, list))}
                    txt = '，'.join(f'{k}={v}' for k, v in keep.items())[:200]
            except Exception:
                txt = str(data)[:200]
            out.append({'at': r['at'], 'kind': r['kind'], 'text': txt})
        return out
    finally:
        c.close()


def content_detail(item_id):
    errors = {}
    accs = load_accounts()
    accmap = {a['slot']: a for a in accs}
    m = re.match(r'^zhihu-answer-(\d{4}-\d{2}-\d{2})-(\d+)$', item_id)
    if m:
        lst = zhihu_answers(m.group(1))
        it = next((a for a in lst if a['id'] == item_id), None)
        if not it:
            return None
        folder = Path(it['dir']) if it.get('dir') else None
        post = {}
        body = read_text(folder / 'answer.md') if folder else None
        review = read_text(folder / 'review.md') if folder else None
        res = {'item': {k: v for k, v in it.items() if k != 'dir'}, 'post': {'title': it['title'], 'column': it['column']},
               'body_html': md(body) if body else '', 'review_html': md(review) if review else '',
               'description': '', 'media': {'final': [], 'process': [], 'videos': []}, 'events': [], 'metrics': None,
               'detail_raw': '', 'errors': errors}
    else:
        items = enrich_items(ledger_rows(), accmap)
        it = next((i for i in items if i['id'] == item_id), None)
        if not it:
            return None
        folder = Path(it['dir']) if it.get('dir') else None
        raw_row = next((r for r in ledger_rows() if r['id'] == item_id), {})
        raw_detail = raw_row.get('detail')
        pj = post_json_path(raw_row.get('payload'))
        if (not pj or not pj.exists()) and folder:
            cands = [c for c in sorted(folder.glob('post*.json')) if not re.search(r'payload|uploads|lint|publish', c.name)]
            pj = cands[0] if cands else None
        post = read_json(pj, {}) if pj else {}
        body = None
        if folder:
            for name in ('article.md', 'answer.md'):
                if (folder / name).exists():
                    body = read_text(folder / name)
                    break
        review = read_text(folder / 'review.md') if folder else None
        final, process, videos = media_of(folder, post) if folder else ([], [], [])
        raw = ''
        if raw_detail:
            s = str(raw_detail).strip()
            try:
                raw = json.dumps(scrub(json.loads(s)), ensure_ascii=False, indent=1)
            except Exception:
                raw = s
        it = {k: v for k, v in it.items() if k != 'dir'}
        res = {
            'item': it,
            'post': {k: post.get(k) for k in ('title', 'short_title', 'column', 'kind', 'time', 'slot', 'tags', 'declaration', 'digest', 'author')
                     if post.get(k) not in (None, '', [])},
            'description': post.get('description') or post.get('digest') or '',
            'body_html': md(body) if body else '',
            'review_html': md(review) if review else '',
            'media': {'final': final, 'process': process, 'videos': videos},
            'events': section(errors, 'events', lambda: item_events(item_id), []),
            'detail_raw': raw[:6000],
            'errors': errors,
        }
    # 作品数据快照：按 URL 中的作品 id 或标题前 12 字匹配
    def find_metrics():
        rows = metrics_latest(since_ts=0)
        title12 = (res['item'].get('title') or '')[:12]
        url = res['item'].get('url') or ''
        pk = res['item'].get('pkey')
        hit = None
        for x in rows:
            if plat_key(x['platform']) != pk:
                continue
            pid = re.sub(r'^\D+-', '', str(x['id']))
            if url and pid and len(pid) >= 8 and pid in url:
                hit = x
                break
        # 没发出去的内容不按标题猜（同题的旧作品会被误认成它）；按标题匹配时发布日要相差不超过 1 天
        if not hit and title12 and res['item'].get('bucket') == 'done':
            day = res['item'].get('day') or ''
            cands = [x for x in rows if plat_key(x['platform']) == pk and (x.get('title') or '')[:12] == title12
                     and _day_gap(dt.datetime.fromtimestamp(x.get('created') or 0, TZ).date().isoformat(), day) <= 1]
            hit = min(cands, key=lambda x: _day_gap(dt.datetime.fromtimestamp(x.get('created') or 0, TZ).date().isoformat(), day)) if cands else None
        if not hit:
            return None
        ser = metrics_series(hit['platform'], hit['account'], hit['id'])
        latest = {k: v for k, v in hit.items() if k not in ('platform', 'account', 'title')}
        return {'post_id': hit['id'], 'latest': latest, 'series': ser, 'tips': diagnose(hit)}
    res['metrics'] = section(errors, 'metrics', find_metrics, None)
    return res


# ---------- 元信息 ----------
def meta_payload():
    accs = load_accounts()
    goal = CFG.get('goal') if isinstance(CFG.get('goal'), dict) else None
    return {'title': CFG.get('title'), 'subtitle': CFG.get('subtitle'), 'version': APP_VERSION, 'demo': DEMO,
            'root_name': ROOT.name, 'host': HOST, 'port': PORT, 'timezone': str(TZ), 'goal': goal,
            'accounts': [{k: a[k] for k in ('slot', 'pkey', 'platform', 'name')} for a in accs],
            'manual_dir': CFG.get('manual_dir'), 'today': today()}


# ---------- 数据源健康 ----------
def _age_min(at):
    d = parse_dt(at) if isinstance(at, str) else at
    if not d:
        return None
    return max(0, round((now() - d).total_seconds() / 60))


def health_payload():
    """每个数据源最后更新时间、距今多久、是否超过预期节奏。只读文件时间和库里的最大时间戳。"""
    H = CFG.get('health') or {}
    out = []

    def add(key, label, at, hint, expect=None, note=''):
        age = _age_min(at)
        exp = expect if expect is not None else H.get(key)
        state = 'missing' if at is None else ('stale' if exp and age is not None and age > exp else 'ok')
        out.append({'key': key, 'label': label, 'at': at.isoformat(timespec='minutes') if isinstance(at, dt.datetime) else at,
                    'age_min': age, 'expect_min': exp, 'state': state, 'hint': hint, 'note': note})

    def ledger_at():
        c = ro_db(OPS_DB)
        try:
            r = c.execute('SELECT MAX(updated) FROM items').fetchone()
            return r[0] if r else None
        finally:
            c.close()

    def metrics_at():
        c = ro_db(METRICS_DB)
        try:
            r = c.execute('SELECT MAX(snap) FROM snaps').fetchone()
            return dt.datetime.fromtimestamp(r[0], TZ) if r and r[0] else None
        finally:
            c.close()

    def radar_at():
        for d in day_dirs()[:3]:
            files = list((DAYS / d / 'radar').glob('*.json')) if (DAYS / d / 'radar').is_dir() else []
            if files:
                return mtime_iso(max(files, key=lambda p: p.stat().st_mtime))
        return None

    def runs_at():
        for d in day_dirs()[:3]:
            recs = read_jsonl(DAYS / d / 'runs.jsonl')
            ats = [r.get('at') for r in recs if r.get('at')]
            if ats:
                return max(ats)
        return None

    def evolve_at():
        e = latest_evolve()
        return e['updated'] if e else None

    def report_at():
        r = reports_list()
        return r[0]['updated'] if r else None

    def engagement_at():
        for d in day_dirs()[:2]:
            p = DAYS / d / 'engagement.jsonl'
            if p.exists():
                return mtime_iso(p)
        return None

    def safe(fn):
        try:
            return fn()
        except Exception:
            return None
    t = now()
    # 雷达只在白天跑（默认 07:00–23:30），夜里放宽到 9 小时
    radar_expect = H.get('radar') if 7 * 60 + 30 <= t.hour * 60 + t.minute <= 23 * 60 + 59 else 9 * 60
    add('ledger', '发布台账', safe(ledger_at), '台账由发布脚本写入 state/ops.sqlite3；长时间不动说明发布任务没在跑')
    add('fans', '粉丝采集', mtime_iso(FANS) if FANS.exists() else None, '粉丝每天采集一次写 state/fans.json')
    add('metrics', '作品数据', safe(metrics_at), '创作者中心数据回流写 state/metrics.sqlite3')
    add('radar', '热点雷达', safe(radar_at), '雷达每 30 分钟写 days/<日期>/radar/*.json', expect=radar_expect)
    add('runs', '任务运行', safe(runs_at), '定时任务开工/收工写 days/<日期>/runs.jsonl')
    add('engagement', '互动记录', safe(engagement_at), '每次评论/回复写 days/<日期>/engagement.jsonl')
    add('evolve', '数据进化', safe(evolve_at), '日报任务跑 evolve 写 days/<日期>/evolve.json')
    add('report', '日报', safe(report_at), '日报写 reports/<日期>.md')
    sync = read_json(ROOT / '.sync.json', None)  # 只有远程站点（由 scripts/dashboard_sync.py 推送）才有这个文件
    if isinstance(sync, dict):
        add('sync', '数据同步', sync.get('at'), '本地工作台每小时把数据推到这里；过期说明那台电脑睡眠、断网或同步任务失败',
            expect=int(CFG.get('health', {}).get('sync') or 150))
    # 规则健康：今天升版太多次，执行中的任务会拿到前后不一致的规则
    try:
        tl = changelog_timeline(read_text(MANUAL / CFG['manual_changelog']) or '', 80)
        bumps = sum(1 for e in tl if (e.get('when') or '').startswith(t.date().isoformat()) or
                    (e.get('version') or '').startswith('v' + t.strftime('%Y.%m.%d')))
        lim = int(CFG.get('max_bumps_per_day') or 4)
        out.append({'key': 'manual', 'label': '手册改动', 'at': mtime_iso(MANUAL / CFG['manual_index']), 'age_min': None,
                    'expect_min': None, 'state': 'stale' if bumps > lim else 'ok', 'bumps_today': bumps,
                    'hint': f'今天升版 {bumps} 次' + (f'，超过 {lim} 次：规则改得太勤，正在跑的任务会拿到前后不一致的规则，建议攒到固定时间统一升版' if bumps > lim else ''),
                    'note': ''})
    except Exception:
        pass
    n_bad = sum(1 for x in out if x['state'] != 'ok')
    return {'sources': out, 'ok': len(out) - n_bad, 'total': len(out), 'now': t.isoformat(timespec='seconds')}


# ---------- 全局搜索 ----------
def _snippet(text, ql, width=36):
    i = text.lower().find(ql)
    if i < 0:
        return ''
    s = max(0, i - width)
    e = min(len(text), i + len(ql) + width)
    return ('…' if s else '') + re.sub(r'\s+', ' ', text[s:e]).strip() + ('…' if e < len(text) else '')


def manual_files():
    if not MANUAL or not MANUAL.is_dir():
        return []
    skip = set(CFG.get('manual_skip') or [])
    out = []
    for p in sorted(MANUAL.rglob('*.md')):
        rel = p.relative_to(MANUAL)
        if any(part in skip for part in rel.parts[:-1]) or any(part.startswith('.') for part in rel.parts):
            continue
        out.append(p)
    return out


def search_payload(q, limit=12):
    errors = {}
    ql = (q or '').strip().lower()
    res = {'q': q, 'items': [], 'reports': [], 'docs': [], 'errors': errors}
    if len(ql) < 1:
        return res

    def items():
        accmap = {a['slot']: a for a in load_accounts()}
        raw = ledger_rows()
        hit_ids = {r['id'] for r in raw if ql in (r.get('title') or '').lower() or ql in (r.get('id') or '').lower()
                   or ql in ((accmap.get(r.get('slot')) or {}).get('name') or '').lower()}
        keys = {(r.get('day'), r.get('slot')) for r in raw if r['id'] in hit_ids}
        ctx = [r for r in raw if (r.get('day'), r.get('slot')) in keys]
        rows = [i for i in enrich_items(ctx, accmap) if i['id'] in hit_ids or ql in (i.get('title') or '').lower()]
        for d in day_dirs():
            rows += [a for a in zhihu_answers(d) if ql in (a.get('title') or '').lower()]
        rows.sort(key=lambda i: ((i.get('day') or ''), i.get('time') or ''), reverse=True)
        return [{k: i.get(k) for k in ('id', 'day', 'time', 'title', 'pkey', 'account_name', 'platform_name', 'bucket',
                                         'status_label', 'thumb', 'column', 'superseded_by')} for i in rows[:limit]]

    def reports():
        out = []
        for report in reports_list():
            p = report_path(report['date'])
            t = read_text(p) or ''
            if ql in report['date'] or ql in t.lower():
                out.append({'date': report['date'], 'snippet': _snippet(t, ql) or (t.strip().splitlines() or [''])[0][:60]})
            if len(out) >= limit:
                break
        return out

    def docs():
        out = []
        for p in manual_files():
            rel = p.relative_to(MANUAL).as_posix()
            t = read_text(p) or ''
            if ql in rel.lower() or ql in t.lower():
                head = next((ln.lstrip('# ').strip() for ln in t.splitlines() if ln.startswith('#')), p.stem)
                out.append({'path': rel, 'title': head, 'snippet': _snippet(t, ql)})
            if len(out) >= limit:
                break
        return out
    res['items'] = section(errors, 'ledger', items, []) or []
    res['reports'] = section(errors, 'reports', reports, []) or []
    res['docs'] = section(errors, 'docs', docs, []) or []
    return res


# ---------- 手册浏览 ----------
def docs_list_payload():
    out = []
    for p in manual_files():
        rel = p.relative_to(MANUAL)
        t = read_text(p) or ''
        head = next((ln.lstrip('# ').strip() for ln in t.splitlines() if ln.startswith('# ')), p.stem)
        out.append({'path': rel.as_posix(), 'dir': rel.parent.as_posix() if rel.parent.as_posix() != '.' else '',
                    'name': p.stem, 'title': head, 'updated': mtime_iso(p), 'size': len(t)})
    out.sort(key=lambda d: (d['dir'] != '', d['dir'], d['path']))
    return {'manual_dir': CFG.get('manual_dir'), 'exists': bool(MANUAL and MANUAL.is_dir()), 'docs': out}


def doc_payload(rel):
    p = (MANUAL / rel).resolve()
    if not in_dir(p, MANUAL) or p.suffix.lower() != '.md' or not p.is_file():
        return None
    t = read_text(p) or ''
    return {'path': p.relative_to(MANUAL.resolve()).as_posix(), 'html': md(t), 'updated': mtime_iso(p), 'size': len(t)}


# ---------- 周日历 ----------
def calendar_payload(start, n_days=7):
    errors = {}
    accs = section(errors, 'schedule', load_accounts, []) or []
    accmap = {a['slot']: a for a in accs}
    d0 = dt.date.fromisoformat(start)
    days = [(d0 + dt.timedelta(days=i)).isoformat() for i in range(n_days)]
    items = section(errors, 'ledger', lambda: enrich_items(ledger_rows(), accmap), []) or []
    answers = {}
    for d in days:
        answers[d] = section(errors, 'zhihu_answers', lambda d=d: zhihu_answers(d), []) or []
    since = ledger_since(items)
    keep = ('id', 'time', 'title', 'bucket', 'status_label', 'superseded_by', 'resolved_note', 'aired', 'thumb', 'column',
            'publish_type', 'is_answer', 'reason')
    rows = []
    totals = {d: {'expected': 0, 'done': 0, 'queue': 0, 'fail': 0, 'warn': 0} for d in days}
    for a in accs:
        cells = []
        for d in days:
            mine = [i for i in items if i.get('day') == d and i.get('slot') == a['slot'] and i['bucket'] != 'muted']
            if a['slot'] == 'zhihu':
                mine = mine + answers[d]
            mine.sort(key=lambda i: i.get('time') or '')
            live = [i for i in mine if not i.get('superseded_by') and not i.get('resolved_note')]
            c = {'expected': expected_since(a, d, since)}
            for b in ('done', 'queue', 'fail', 'warn'):
                c[b] = sum(1 for i in live if i['bucket'] == b)
            for k in totals[d]:
                totals[d][k] += c[k]
            c['items'] = [{k: i.get(k) for k in keep} for i in mine]
            cells.append(c)
        rows.append({**{k: a[k] for k in ('slot', 'pkey', 'platform', 'name', 'times', 'weekdays_only', 'paused')}, 'cells': cells})
    return {'start': start, 'days': days, 'today': today(), 'rows': rows, 'totals': [totals[d] for d in days], 'errors': errors}


# ---------- 增长与投入产出 ----------
def ledger_since(items):
    """每个账号在台账里最早的一天：这之前账号还没开始运营，不算「应发」。返回 {slot: 日期}。"""
    out = {}
    for i in items:
        d, sl = i.get('day'), i.get('slot')
        if d and sl and (sl not in out or d < out[sl]):
            out[sl] = d
    return out


def expected_since(acc, day, since):
    s = since.get(acc['slot'])
    return expected_on(acc, day) if s and day >= s else 0


def _content_outcomes(items, day_from, day_to):
    """同一天同账号同标题的多次尝试算一条内容；有一次发出就算成功。"""
    groups = {}
    for i in items:
        d = i.get('day') or ''
        if not (day_from <= d <= day_to) or i['bucket'] == 'muted':
            continue
        key = (d, i.get('slot'), re.sub(r'\s+', '', (i.get('title') or ''))[:24] or i['id'])
        groups.setdefault(key, []).append(i)
    out = []
    for (d, slot, _), its in groups.items():
        bks = {i['bucket'] for i in its}
        if 'done' in bks:
            res = 'done'
        elif 'queue' in bks:
            res = 'queue'
        elif all(i.get('resolved_note') for i in its):
            res = 'dropped'
        else:
            res = 'fail'
        first = sorted(its, key=lambda i: i.get('updated') or '')[0]
        out.append({'day': d, 'slot': slot, 'result': res, 'attempts': len(its),
                    'first_ok': first['bucket'] == 'done', 'mode': first.get('mode') or '',
                    'reasons': [i['reason']['key'] for i in its if i.get('reason')]})
    return out


def growth_payload(n_days=30):
    errors = {}
    accs = section(errors, 'schedule', load_accounts, []) or []
    accmap = {a['slot']: a for a in accs}
    t = now().date()
    days = [(t - dt.timedelta(days=i)).isoformat() for i in range(n_days - 1, -1, -1)]
    fans = section(errors, 'fans', fans_data, {'series': {}, 'current': {}}) or {'series': {}, 'current': {}}
    items = section(errors, 'ledger', lambda: enrich_items(ledger_rows(), accmap), []) or []
    mrows = section(errors, 'metrics', lambda: metrics_latest(n_days), []) or []

    # 粉丝：按账号逐日向前填充；总数只算有记录以后的日子
    acc_series, seen = [], set()
    for a in accs:
        aid = a.get('account_id')
        if not aid or aid in seen:
            continue
        seen.add(aid)
        pts = {p['day']: p['n'] for p in (fans.get('series') or {}).get(aid) or []}
        cur = (fans.get('current') or {}).get(aid)
        vals, last = [], None
        for p_day in sorted(pts):
            if p_day < days[0]:
                last = pts[p_day]
        for d in days:
            if d in pts:
                last = pts[d]
            if d == days[-1] and isinstance(cur, (int, float)):
                last = cur
            vals.append(last)
        known = [v for v in vals if isinstance(v, (int, float))]
        gain = (known[-1] - known[0]) if len(known) >= 2 else None
        span = sum(1 for v in vals if v is not None)
        acc_series.append({'slot': a['slot'], 'pkey': a['pkey'], 'name': a['name'], 'platform': a['platform'],
                           'values': vals, 'fans': cur, 'gain': gain, 'span_days': span})
    total = []
    for idx in range(len(days)):
        vs = [s['values'][idx] for s in acc_series]
        total.append(sum(v for v in vs if isinstance(v, (int, float))) if any(isinstance(v, (int, float)) for v in vs) else None)

    # 发布：按内容算成功率、首发成功率、失败原因
    outcomes = _content_outcomes(items, days[0], days[-1])
    if any(a['slot'] == 'zhihu' for a in accs):
        for d in days:
            for _ in zhihu_answers(d):
                outcomes.append({'day': d, 'slot': 'zhihu', 'result': 'done', 'attempts': 1, 'first_ok': True,
                                 'mode': 'web', 'reasons': []})
    since = ledger_since(items)
    pub_daily = []
    for d in days:
        oc = [o for o in outcomes if o['day'] == d]
        exp = sum(expected_since(a, d, since) for a in accs)
        done = sum(1 for o in oc if o['result'] == 'done')
        fail = sum(1 for o in oc if o['result'] == 'fail')
        pub_daily.append({'day': d, 'expected': exp, 'done': done, 'fail': fail,
                          'queue': sum(1 for o in oc if o['result'] == 'queue'),
                          'attempts': sum(o['attempts'] for o in oc),
                          'rate': round(done / (done + fail), 3) if done + fail else None})
    # 发布心跳：每个账号每天 应发/已发/失败/排队（按内容，不按尝试次数）
    heartbeat = {}
    for a in accs:
        cells = []
        for d in days:
            oc = [o for o in outcomes if o['day'] == d and o['slot'] == a['slot']]
            cells.append({'day': d, 'expected': expected_since(a, d, since),
                          'done': sum(1 for o in oc if o['result'] == 'done'),
                          'fail': sum(1 for o in oc if o['result'] == 'fail'),
                          'queue': sum(1 for o in oc if o['result'] == 'queue')})
        heartbeat[a['slot']] = cells
    reasons = {}
    for i in items:
        if days[0] <= (i.get('day') or '') <= days[-1] and i.get('reason'):
            r = reasons.setdefault(i['reason']['key'], {**i['reason'], 'n': 0, 'slots': {}})
            r['n'] += 1
            r['slots'][i.get('slot')] = r['slots'].get(i.get('slot'), 0) + 1
    reasons = sorted(reasons.values(), key=lambda r: -r['n'])
    for r in reasons:
        r['slots'] = [{'slot': s, 'name': (accmap.get(s) or {}).get('name') or s, 'pkey': (accmap.get(s) or {}).get('pkey'),
                       'n': n} for s, n in sorted(r['slots'].items(), key=lambda kv: -kv[1])]
    by_mode = {}
    for o in outcomes:
        m = by_mode.setdefault(o['mode'] or '未知', {'mode': o['mode'] or '未知', 'n': 0, 'done': 0, 'fail': 0, 'first_ok': 0})
        m['n'] += 1
        m['done'] += o['result'] == 'done'
        m['fail'] += o['result'] == 'fail'
        m['first_ok'] += bool(o['first_ok'])

    # 投入产出：按账号
    m_by_slot = {}
    for x in mrows:
        s = m_by_slot.setdefault(slot_for_metrics(x['platform'], x['account']), {'n': 0, 'views': 0, 'follows': 0, 'inter': 0})
        s['n'] += 1
        s['views'] += x.get('views') or 0
        s['follows'] += x.get('follows') or 0
        s['inter'] += sum((x.get(k) or 0) for k in ('likes', 'favorites', 'comments', 'shares'))
    fans_by_slot = {}
    for s in acc_series:
        fans_by_slot[s['slot']] = s
    roi = []
    first_slot_of = {}
    for a in accs:
        if a.get('account_id'):
            first_slot_of.setdefault(a['account_id'], a['slot'])
    for a in accs:
        oc = [o for o in outcomes if o['slot'] == a['slot']]
        posts = sum(1 for o in oc if o['result'] == 'done')
        fails = sum(1 for o in oc if o['result'] == 'fail')
        ms = m_by_slot.get(a['slot']) or {}
        fs = fans_by_slot.get(a['slot'])
        owner = first_slot_of.get(a.get('account_id'))
        gain = fs['gain'] if fs else None
        roi.append({'slot': a['slot'], 'pkey': a['pkey'], 'name': a['name'], 'platform': a['platform'],
                    'shared_with': (accmap.get(owner) or {}).get('name') if owner and owner != a['slot'] else None,
                    'fans': fs['fans'] if fs else None, 'gain': gain, 'span_days': fs['span_days'] if fs else 0,
                    'posts': posts, 'fails': fails, 'expected': sum(expected_since(a, d, since) for d in days),
                    'views': ms.get('views'), 'm_posts': ms.get('n', 0), 'follows': ms.get('follows'),
                    'views_per_post': round(ms['views'] / ms['n'], 1) if ms.get('n') else None,
                    'inter_rate': round(ms['inter'] / ms['views'], 4) if ms.get('views') else None,
                    'gain_per_post': round(gain / posts, 2) if gain is not None and posts else None,
                    'gain_per_k_views': round(gain / ms['views'] * 1000, 2) if gain is not None and ms.get('views') else None})
    first_day_with_fans = next((d for d, v in zip(days, total) if v is not None), None)
    return {
        'days': days, 'n_days': n_days, 'total': total, 'accounts': acc_series,
        'fans_total': next((v for v in reversed(total) if v is not None), None),
        'fans_gain': (next((v for v in reversed(total) if v is not None), 0) - next((v for v in total if v is not None), 0))
        if sum(1 for v in total if v is not None) >= 2 else None,
        'fans_since': first_day_with_fans, 'history_records': fans.get('history_records', 0),
        'publish_daily': pub_daily, 'reasons': reasons, 'by_mode': sorted(by_mode.values(), key=lambda m: -m['n']),
        'heartbeat': heartbeat, 'today': today(),
        'roi': roi, 'goal': CFG.get('goal') if isinstance(CFG.get('goal'), dict) else None,
        'errors': errors,
    }


# ---------- 登录（远程站点用，--auth 配置文件启用；本机默认不开） ----------
# 配置文件只放在服务器上，例：
# {"provider": "provider", "allow": ["<手机号>"], "secret": "<随机 32 字节以上>", "session_days": 7,
#  "provider_api": "https://api.example.com"}
AUTH = None
COOKIE = 'ipdash_s'
_HITS = {}


def _b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode()


def _b64u_dec(s):
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))


def make_session(sub, label=''):
    exp = int(time.time()) + int(AUTH.get('session_days') or 7) * 86400
    body = _b64u(json.dumps({'sub': sub, 'n': label, 'exp': exp}, separators=(',', ':'), ensure_ascii=False).encode())
    sig = _b64u(hmac.new(AUTH['secret'].encode(), body.encode(), hashlib.sha256).digest())
    return f'{body}.{sig}', exp


def read_session(cookie_header):
    """校验签名、过期时间，并且账号还在允许名单里（名单改了，旧会话立刻失效）。"""
    if not AUTH or not cookie_header:
        return None
    for part in cookie_header.split(';'):
        k, _, v = part.strip().partition('=')
        if k != COOKIE or '.' not in v:
            continue
        body, sig = v.rsplit('.', 1)
        want = _b64u(hmac.new(AUTH['secret'].encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, want):
            return None
        try:
            d = json.loads(_b64u_dec(body))
        except Exception:
            return None
        if int(d.get('exp') or 0) < time.time() or not allowed_phone(d.get('sub')):
            return None
        return d
    return None


def rate_ok(key, limit=8, window=600):
    """同一来源 10 分钟内最多 8 次登录相关请求（发验证码、校验），防撞库和短信轰炸。"""
    t = time.time()
    hits = [x for x in _HITS.get(key, []) if t - x < window]
    if len(hits) >= limit:
        _HITS[key] = hits
        return False
    hits.append(t)
    _HITS[key] = hits
    return True


def mask_phone(p):
    p = re.sub(r'^\+86', '', str(p or ''))
    return p[:3] + '****' + p[-4:] if len(p) >= 7 else '***'


def norm_phone(p):
    """规范成 +86XXXXXXXXXXX（和示例服务后端一致），格式不对返回 None。"""
    d = re.sub(r'[\s-]', '', str(p or ''))
    d = re.sub(r'^(\+?86)', '', d)
    return '+86' + d if re.fullmatch(r'1\d{10}', d) else None


def allowed_phone(p):
    n = norm_phone(p)
    if not n:
        return None
    for a in AUTH.get('allow') or []:
        if hmac.compare_digest(n, norm_phone(a) or ''):
            return n
    return None


def provider_call(path, body):
    """服务端代调示例服务账号接口（同一套账号，不改示例服务后端）。X-provider-Client: web 让后端按网页端处理。"""
    base = (AUTH.get('provider_api') or 'https://api.example.com').rstrip('/')
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method='POST', headers={
        'Content-Type': 'application/json', 'X-provider-Client': 'web', 'User-Agent': 'ip-dashboard/1.0 (+https://api.example.com'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b'{}')
        except Exception:
            return e.code, {}


def provider_ok(status, j):
    return 200 <= status < 300 and isinstance(j, dict) and j.get('code') == 0  # 示例服务后端 POST 成功返回 201


def provider_msg(j, default):
    m = (j or {}).get('message') or (j or {}).get('error') or default
    if isinstance(m, dict):  # 示例服务的错误长这样：{"message": {"code": "invalid_credentials", "message": "账号或密码错误"}}
        m = m.get('message') or m.get('code') or default
    if isinstance(m, list):
        m = '；'.join(str(x) for x in m)
    return str(m)[:120]


def _auth_state_path():
    return Path(AUTH.get('state_file') or (Path(AUTH['_path']).parent / 'auth-state.json'))


def pin_user(phone, user_id):
    """第一次登录成功时记下这个手机号对应的示例服务用户 id，之后必须一致（号码换绑、被注册到别人名下时拒绝）。"""
    p = _auth_state_path()
    st = read_json(p, {}) or {}
    pins = st.setdefault('pinned', {})
    if phone in pins:
        return hmac.compare_digest(str(pins[phone]), str(user_id))
    pins[phone] = str(user_id)
    try:
        p.write_text(json.dumps(st, ensure_ascii=False), encoding='utf-8')
        os.chmod(p, 0o600)
    except Exception:
        traceback.print_exc()
    return True


def auth_send(phone_in):
    phone = allowed_phone(phone_in)
    if not phone:
        # 不在名单里的号码绝不往示例服务发码：示例服务验证码登录会给新号码自动注册账号
        return 403, {'ok': False, 'error': '这个手机号没有访问权限'}
    code, j = provider_call('/auth/phone-code', {'phone': phone})
    if provider_ok(code, j):
        return 200, {'ok': True}
    return 502 if code >= 500 else 400, {'ok': False, 'error': f'发送验证码失败：{provider_msg(j, f"示例服务返回 {code}")}'}


def auth_login(phone_in, code_in):
    phone = allowed_phone(phone_in)
    if not phone:
        return 403, {'ok': False, 'error': '这个手机号没有访问权限'}, None
    if not re.fullmatch(r'\d{6}', str(code_in or '')):
        return 400, {'ok': False, 'error': '验证码是 6 位数字'}, None
    code, j = provider_call('/auth/phone-login', {'phone': phone, 'code': str(code_in)})
    return _finish_login(code, j, phone, '验证码不对或已过期')


def auth_password(account_in, password_in):
    """示例服务账号密码登录（account 可以是手机号或邮箱）。手机号先过白名单；邮箱登录成功后再核对账号绑定的手机号。"""
    account = str(account_in or '').strip()
    password = str(password_in or '')
    if not account or len(password) < 8:
        return 400, {'ok': False, 'error': '账号或密码不对（示例服务密码至少 8 位）'}, None
    phone = None
    if norm_phone(account):
        phone = allowed_phone(account)
        if not phone:
            return 403, {'ok': False, 'error': '这个账号没有访问权限'}, None
        account = phone
    elif '@' not in account:
        return 400, {'ok': False, 'error': '账号填手机号或邮箱'}, None
    code, j = provider_call('/auth/password-login', {'account': account, 'password': password})
    return _finish_login(code, j, phone, '账号或密码不对')


def _finish_login(code, j, phone, default_err):
    """示例服务登录成功后：返回的手机号必须在白名单里（且和输入一致），示例服务用户 id 必须和首次登录时一致。"""
    user = ((j or {}).get('data') or {}).get('user') or {}
    if not provider_ok(code, j) or not user.get('id'):
        return 401, {'ok': False, 'error': f'登录失败：{provider_msg(j, default_err)}'}, None
    got = allowed_phone(user.get('phone'))
    if not got or (phone and got != phone):
        return 403, {'ok': False, 'error': '这个示例服务账号没有访问权限'}, None
    if not pin_user(got, user['id']):
        return 403, {'ok': False, 'error': '这个手机号现在对应的示例服务账号和首次登录时不同，已拒绝'}, None
    return 200, {'ok': True}, (got, user.get('displayName') or mask_phone(got))


# ---------- HTTP ----------
class Handler(BaseHTTPRequestHandler):
    server_version = 'creatorDashboard/1.0'

    def log_message(self, fmt, *args):  # 简洁日志，不打印查询参数以外的东西
        sys.stderr.write('%s %s\n' % (now().strftime('%H:%M:%S'), fmt % args))

    def _send(self, code, body, ctype='application/json; charset=utf-8', extra=None):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        if not (extra and 'Cache-Control' in extra):
            self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'same-origin')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False, default=str))

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        try:
            path = urllib.parse.urlsplit(self.path).path
            if not AUTH or path not in ('/auth/send', '/auth/login', '/auth/password'):
                return self._json({'error': 'not found'}, 404)
            # 防跨站请求：Origin 必须是本站
            origin = urllib.parse.urlsplit(self.headers.get('Origin') or '').netloc
            host = self.headers.get('X-Forwarded-Host') or self.headers.get('Host') or ''
            if not origin or origin != host:
                return self._json({'ok': False, 'error': '来源不对'}, 403)
            n = int(self.headers.get('Content-Length') or 0)
            if n > 4096:
                return self._json({'ok': False, 'error': '请求太大'}, 413)
            try:
                body = json.loads(self.rfile.read(n) or b'{}')
            except Exception:
                return self._json({'ok': False, 'error': '格式不对'}, 400)
            ip = self.headers.get('X-Real-IP') or self.client_address[0]
            if not rate_ok(f'{ip}|{path}') or (path == '/auth/send' and not rate_ok('send|' + str(norm_phone(body.get('phone'))), 5, 600)) \
                    or (path == '/auth/password' and not rate_ok('pw|' + str(body.get('account') or '').strip().lower(), 5, 900)):
                return self._json({'ok': False, 'error': '操作太频繁，10 分钟后再试'}, 429)
            if path == '/auth/send':
                code, j = auth_send(body.get('phone'))
                sys.stderr.write(f'{now():%H:%M:%S} auth send {mask_phone(body.get("phone"))} -> {code}\n')
                return self._json(j, code)
            if path == '/auth/password':
                code, j, who = auth_password(body.get('account'), body.get('password'))
                acc = str(body.get('account') or '')
                sys.stderr.write(f'{now():%H:%M:%S} auth password {mask_phone(acc) if "@" not in acc else acc[:2] + "***"} -> {code}\n')
            else:
                code, j, who = auth_login(body.get('phone'), body.get('code'))
                sys.stderr.write(f'{now():%H:%M:%S} auth login {mask_phone(body.get("phone"))} -> {code}\n')
            if not who:
                return self._json(j, code)
            token, exp = make_session(who[0], who[1])
            max_age = int(exp - time.time())
            body_b = json.dumps(j, ensure_ascii=False).encode()
            return self._send(200, body_b, extra={'Set-Cookie': f'{COOKIE}={token}; Path=/; Max-Age={max_age}; HttpOnly; Secure; SameSite=Lax'})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            traceback.print_exc()
            try:
                self._json({'ok': False, 'error': f'{type(e).__name__}'}, 500)
            except Exception:
                pass

    def do_GET(self):
        try:
            u = urllib.parse.urlsplit(self.path)
            path = urllib.parse.unquote(u.path)
            q = {k: v[-1] for k, v in urllib.parse.parse_qs(u.query).items()}
            self.session = None
            if AUTH:
                if path == '/robots.txt':
                    return self._send(200, 'User-agent: *\nDisallow: /\n', 'text/plain; charset=utf-8')
                if path == '/login':
                    if read_session(self.headers.get('Cookie')):
                        return self._send(302, b'', 'text/plain', {'Location': '/'})
                    return self._static('login.html')
                if path == '/auth/logout':
                    return self._send(302, b'', 'text/plain', {'Location': '/login', 'Set-Cookie': f'{COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax'})
                if path == '/favicon.ico':
                    return self._send(204, b'', 'image/x-icon')
                self.session = read_session(self.headers.get('Cookie'))
                if not self.session:
                    if path.startswith('/api/') or path.startswith('/files/'):
                        return self._json({'error': '未登录或登录已过期', 'login': '/login'}, 401)
                    return self._send(302, b'', 'text/plain', {'Location': '/login?next=' + urllib.parse.quote(self.path, safe='')})
            if path in ('/', '/index.html'):
                return self._static('index.html')
            if path.startswith('/static/'):
                return self._static(path[len('/static/'):])
            if path.startswith('/files/'):
                return self._file(u.path[len('/files/'):])
            if path.startswith('/api/'):
                return self._api(path[len('/api/'):].strip('/'), q)
            if path == '/favicon.ico':
                return self._send(204, b'', 'image/x-icon')
            return self._send(404, '{"error":"not found"}')
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            traceback.print_exc()
            try:
                self._json({'error': f'{type(e).__name__}: {e}'}, 500)
            except Exception:
                pass

    def _static(self, rel):
        p = (STATIC / rel).resolve()
        if not in_dir(p, STATIC) or not p.is_file():
            return self._send(404, 'not found', 'text/plain; charset=utf-8')
        ctype = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
        if ctype.startswith('text/') or ctype in ('application/javascript',):
            ctype += '; charset=utf-8'
        # vendor 里是固定版本的第三方文件，可以让浏览器缓存；自己的页面文件每次都取最新
        extra = {'Cache-Control': 'public, max-age=86400'} if rel.startswith('vendor/') else None
        self._send(200, p.read_bytes(), ctype, extra)

    def _file(self, raw_rel):
        rel = urllib.parse.unquote(raw_rel)
        if '\x00' in rel or rel.startswith('/'):
            return self._send(404, 'not found', 'text/plain; charset=utf-8')
        p = (ROOT / rel).resolve()
        if not (in_dir(p, DAYS) or in_dir(p, ASSETS)) or p.suffix.lower() not in FILE_EXT or not p.is_file():
            return self._send(404, 'not found', 'text/plain; charset=utf-8')
        ctype = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif',
                 '.webp': 'image/webp', '.mp4': 'video/mp4'}[p.suffix.lower()]
        size = p.stat().st_size
        rng = self.headers.get('Range')
        start, end = 0, size - 1
        code = 200
        if rng:
            m = re.match(r'bytes=(\d*)-(\d*)$', rng.strip())
            if m and (m.group(1) or m.group(2)):
                if m.group(1):
                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else size - 1
                else:
                    start = max(0, size - int(m.group(2)))
                end = min(end, size - 1)
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header('Content-Range', f'bytes */{size}')
                    self.end_headers()
                    return
                code = 206
        length = end - start + 1
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(length))
        self.send_header('Cache-Control', 'private, max-age=300')
        if code == 206:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        if self.command == 'HEAD':
            return
        with open(p, 'rb') as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(256 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def _api(self, route, q):
        def day_param():
            d = q.get('day') or today()
            return d if DAY_RE.match(d) else today()

        def int_param(name, default, lo, hi):
            try:
                return max(lo, min(hi, int(q.get(name, default))))
            except Exception:
                return default

        if route == 'overview':
            return self._json(overview_payload())
        if route == 'content':
            return self._json(content_list(day_param(), q.get('platform') or None, q.get('status') or None, q.get('column') or None))
        if route.startswith('content/'):
            iid = route[len('content/'):]
            d = content_detail(iid)
            return self._json(d) if d else self._json({'error': '没找到这条内容'}, 404)
        if route == 'metrics':
            return self._json(metrics_payload(int_param('days', 7, 1, 365)))
        if route == 'fans':
            errors = {}
            accs = section(errors, 'schedule', load_accounts, []) or []
            f = section(errors, 'fans', fans_data, {}) or {}
            return self._json({'accounts': [{k: a[k] for k in ('slot', 'pkey', 'platform', 'name', 'account_id')} for a in accs],
                               **f, 'errors': errors})
        if route == 'engagement':
            return self._json(engagement_payload(day_param()))
        if route == 'hot':
            return self._json(hot_payload(day_param()))
        if route == 'plan':
            return self._json(plan_payload())
        if route == 'reports':
            errors = {}
            return self._json({'reports': section(errors, 'reports', reports_list, []), 'errors': errors})
        if route.startswith('reports/'):
            d = route[len('reports/'):]
            if not DAY_RE.match(d):
                return self._json({'error': '日期格式不对'}, 404)
            p = report_path(d)
            t = read_text(p)
            if t is None:
                return self._json({'error': '没有这天的日报'}, 404)
            return self._json({'date': d, 'html': md(t), 'markdown': t, 'full_day': p.name.endswith('.full.md'), 'updated': mtime_iso(p)})
        if route == 'accounts':
            return self._json(accounts_payload())
        if route == 'meta':
            sess = getattr(self, 'session', None)
            return self._json({**meta_payload(), 'auth': bool(AUTH), 'user': (sess or {}).get('n') if AUTH else None})
        if route == 'health':
            return self._json(health_payload())
        if route == 'search':
            return self._json(search_payload((q.get('q') or '')[:60]))
        if route == 'calendar':
            start = q.get('start') or ''
            if not DAY_RE.match(start):
                t = now().date()
                start = (t - dt.timedelta(days=t.weekday())).isoformat()
            return self._json(calendar_payload(start, int_param('days', 7, 1, 14)))
        if route == 'growth':
            return self._json(growth_payload(int_param('days', 30, 7, 180)))
        if route == 'docs':
            if q.get('path'):
                d = doc_payload(q['path'])
                return self._json(d) if d else self._json({'error': '没有这份文档'}, 404)
            return self._json(docs_list_payload())
        return self._json({'error': 'unknown api'}, 404)


def accounts_payload():
    """账号页：每个账号近 7 天作品（作品数据 + 台账）、均值、粉丝走势。"""
    errors = {}
    accs = section(errors, 'schedule', load_accounts, []) or []
    accmap = {a['slot']: a for a in accs}
    fans = section(errors, 'fans', fans_data, {'series': {}, 'current': {}}) or {'series': {}, 'current': {}}
    items = section(errors, 'ledger', lambda: enrich_items(ledger_rows(), accmap), []) or []
    rows = section(errors, 'metrics', lambda: metrics_latest(7), []) or []
    meta = ledger_meta_index(items)
    day = today()
    since = (now().date() - dt.timedelta(days=6)).isoformat()
    out = []
    for a in accs:
        mine = []
        for x in rows:
            if slot_for_metrics(x['platform'], x['account']) != a['slot']:
                continue
            it = match_ledger(x, meta, items)
            y = dict(x)
            y['created_iso'] = dt.datetime.fromtimestamp(x['created'] or 0, TZ).isoformat(timespec='minutes')
            y['column'] = (it or {}).get('column') or '未标'
            y['item_id'] = (it or {}).get('id')
            y['tips'] = diagnose(x)
            mine.append(y)
        n = len(mine)

        def avg(f):
            vals = [x.get(f) for x in mine if isinstance(x.get(f), (int, float))]
            return round(sum(vals) / len(vals), 3) if vals else None
        led = [i for i in items if i.get('slot') == a['slot'] and (i.get('day') or '') >= since and i['bucket'] != 'muted']
        if a['slot'] == 'zhihu':
            for k in range(7):
                led += zhihu_answers((now().date() - dt.timedelta(days=k)).isoformat())
        led.sort(key=lambda i: (i.get('day') or '', i.get('time') or ''), reverse=True)
        aid = a.get('account_id')
        pts = (fans.get('series') or {}).get(aid) or []
        cur = (fans.get('current') or {}).get(aid)
        d1, d7, d7span = fans_deltas(pts, cur, day)
        out.append({**a, 'fans': cur, 'd1': d1, 'd7': d7, 'd7_span': d7span, 'spark': pts[-60:],
                    'posts': mine, 'n': n,
                    'avg': {'views': avg('views'), 'likes': avg('likes'), 'favorites': avg('favorites'), 'comments': avg('comments'),
                            'follows': avg('follows'), 'bounce_2s': avg('bounce_2s'), 'completion_5s': avg('completion_5s'),
                            'avg_view_ratio': avg('avg_view_ratio')},
                    'sum': {'views': sum(x.get('views') or 0 for x in mine), 'follows': sum(x.get('follows') or 0 for x in mine)},
                    'ledger': [{k: i.get(k) for k in ('id', 'day', 'time', 'title', 'status', 'status_label', 'bucket', 'url', 'column',
                                                       'superseded_by', 'is_answer', 'thumb')} for i in led[:40]],
                    'expected_today': expected_on(a, day)})
    return {'accounts': out, 'fans_updated': fans.get('updated'), 'fans_history': fans.get('history_exists', False), 'errors': errors}


def main(argv=None):
    global HOST, PORT, DEMO
    ap = argparse.ArgumentParser(description='矩阵运营工作台：本地只读看板')
    ap.add_argument('--root', default=os.environ.get('MATRIX_ROOT'), help='数据目录（默认 dashboard/ 的上一级，或环境变量 MATRIX_ROOT）')
    ap.add_argument('--host', default=os.environ.get('DASH_HOST', HOST), help='监听地址，默认 127.0.0.1（只给本机看）')
    ap.add_argument('--port', type=int, default=int(os.environ.get('DASH_PORT', PORT)))
    ap.add_argument('--demo', action='store_true', help='用示例数据运行（首次自动生成到 dashboard/demo/sample）')
    ap.add_argument('--auth', help='登录配置文件（JSON：provider、allow、secret…），部署到公网时必须开')
    args = ap.parse_args(argv)
    global AUTH
    if args.auth:
        AUTH = json.loads(Path(args.auth).read_text(encoding='utf-8'))
        AUTH['_path'] = str(Path(args.auth).resolve())
        if len(str(AUTH.get('secret') or '')) < 32 or not AUTH.get('allow'):
            sys.exit('登录配置不完整：secret 至少 32 个字符，allow 至少一个账号')
        print(f'登录已开启：示例服务账号，允许 {len(AUTH["allow"])} 个号码', flush=True)
    HOST, PORT = args.host, args.port
    if args.demo:
        DEMO = True
        sample = DASH / 'demo' / 'sample'
        sys.path.insert(0, str(DASH / 'demo'))
        import make_demo  # noqa: E402
        make_demo.ensure(sample)
        configure(sample)
    elif args.root:
        configure(args.root)
    load_diagnose()
    if HOST not in ('127.0.0.1', 'localhost', '::1'):
        print(f'注意：监听 {HOST}，局域网里的其他设备也能看到这些数据。只在可信网络里这样做。', flush=True)
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    srv.daemon_threads = True
    print(f'{CFG.get("title")} · {CFG.get("subtitle")}  http://{HOST}:{PORT}  数据目录 {ROOT}'
          f'{"（示例数据）" if DEMO else ""}  只读，Ctrl+C 退出', flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == '__main__':
    main()
