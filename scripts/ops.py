#!/usr/bin/env python3
"""发布台账：所有真实发布只走 yxer；状态单向推进，结果不确定时不自动重试。

状态：draft → checked(预检通过待审批) → ready(已批准) → submitting → submitted/scheduled → success → public
      失败：blocked(预检失败/人为暂停) / failed(平台失败，待补发) / uncertain(结果未知，必须人工核查)
      web_pending(原通道走不通，到点改网页发) / publishing(网页发布中的占位) / withdrawn(用户撤掉，不补发)
用法：
  ops.py add <id> <slot_key> <HH:MM> <payload.json> [--content-file x.md]   登记并预检(validate+dry-run)，通过后为 ready
  ops.py approve <id...>       审批通过 checked → ready
  ops.py submit <id>          native 条目立即提交（带平台定时）；dispatch 条目到点后才能提交（迟了也能手动补发）
  ops.py dispatch             到点提交所有 ready 的 dispatch 条目（launchd 每分钟调用）；代理故障平台自动转 web_pending
  ops.py reconcile            查询已提交任务的状态与链接
  ops.py status [day]         当天台账
  ops.py retry [day]          失败待补发清单（00-必读 2.1.6：失败一律解决阻断后补发）
  ops.py hold <id> <原因>      暂停 ready（未提交前；不进补发清单）
  ops.py webq <id> <原因>      原通道走不通，转「网页待发」（进补发清单，到点网页发）
  ops.py withdraw <id> <原因>  用户撤掉的条目，不再补发
  ops.py claim <id> <slot> <HH:MM> <post.json> [备注]   网页发布前先占位（publishing），防两个会话重复发
  ops.py link <id> <url>      记录人工核验后的公开链接
  ops.py web <id> <slot> <HH:MM> <post.json> [备注]   登记网页备用通道（默认优先蚁小二，见 00-必读 2.5）
"""
import argparse, datetime as dt, hashlib, json, pathlib, re, sqlite3, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, TZ, now, dump

DB = ROOT / 'state/ops.sqlite3'
SCHED = json.loads((ROOT / 'config/schedule.json').read_text())


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=30, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    c.executescript('''
    CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY, day TEXT, slot TEXT, platform TEXT, account_id TEXT,
      publish_type TEXT, due TEXT, mode TEXT, status TEXT, payload TEXT, content_file TEXT, hash TEXT,
      title TEXT, task_id TEXT, url TEXT, url_verified INTEGER DEFAULT 0, detail TEXT, updated TEXT);
    CREATE TABLE IF NOT EXISTS events(n INTEGER PRIMARY KEY, at TEXT, item TEXT, kind TEXT, data TEXT);
    ''')
    return c


def ev(c, item, kind, data):
    c.execute('INSERT INTO events(at,item,kind,data) VALUES(?,?,?,?)', (now().isoformat(), item, kind, dump(data)))


def digest(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def cli(args, timeout=120):
    r = subprocess.run(['yxer', *args, '--json'], capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
    raw = r.stdout.strip() or r.stderr.strip()
    try:
        return r.returncode, json.loads(raw)
    except Exception:
        return r.returncode, {'ok': False, 'raw': raw[:3000]}


def pform(o, platform):
    pa = o.get('publishArgs', {})
    if platform == '微信公众号' and o.get('publishType', 'article') == 'article':   # 公众号贴图（imageText）走 accountForms
        return pa.get('platformForms', {}).get(platform, {})
    return (pa.get('accountForms') or [{}])[0].get('contentPublishForm', {})


def title_of(o, platform):
    f = pform(o, platform)
    if platform == '微信公众号':
        return (f.get('articles') or [{}])[0].get('title', '')
    t = f.get('title') or ''
    if not t:
        import re
        t = re.sub('<[^>]+>', ' ', f.get('description', '')).strip()[:40]
    return t


def checks(o, slot, content_file=None):
    acc = SCHED['accounts'][slot]
    s = dump(o) + (pathlib.Path(content_file).read_text() if content_file else '')
    for bad in SCHED['forbidden_footers']:
        if bad in s:
            raise ValueError(f'含禁止的固定AI尾注：{bad}')
    import re
    if '<placeholder' in s or '<从 yxer' in s or re.search(r'"<[a-zA-Z_|]+>"', s):
        raise ValueError('载荷含占位符')
    if o.get('platforms') != [acc['platform']] or o.get('publishType') not in [acc['type'], *acc.get('alt_types', [])] or o.get('publishChannel', channel_of(slot)) != channel_of(slot):
        raise ValueError('平台/类型/通道与排期不符')
    forms = o['publishArgs']['accountForms']
    if len(forms) != 1 or forms[0].get('platformAccountId') != acc['account_id']:
        raise ValueError('账号不符')


def channel_of(slot):
    """发布通道：账号配置 publish_channel 优先，否则全局 default_publish_channel，默认 cloud。
    local = 本机蚁小二客户端（clientId 见 yxer config），用于蚁小二云端代理故障时（运营手册/批次执行.md「代理挂了的兜底」）。"""
    acc = SCHED['accounts'].get(slot or '', {})
    return acc.get('publish_channel') or SCHED.get('default_publish_channel') or 'cloud'


def preflight(c, r):
    args = [r['platform'], r['publish_type'], r['payload'], '--publish-channel', channel_of(r['slot'])]
    extra = ['--content-file', r['content_file']] if r['content_file'] else []
    out = ROOT / 'days' / r['day'] / 'receipts'
    out.mkdir(parents=True, exist_ok=True)
    rc, o = cli(['validate', *args, *extra])
    (out / f"{r['id']}-validate.json").write_text(dump(o))
    if rc or not o.get('ok'):
        return False, o
    rc, o = cli(['publish', r['publish_type'], r['platform'], r['payload'], '--publish-channel', channel_of(r['slot']), *extra, '--dry-run'])
    (out / f"{r['id']}-dryrun.json").write_text(dump(o))
    return (not rc and o.get('ok')), o


def add(c, iid, slot, hhmm, payload, content_file=None, approve=False):
    if slot == 'x':
        from x_api import add as x_add
        return x_add(c, iid, hhmm, payload)
    acc = SCHED['accounts'][slot]
    day = iid[:10]
    due = dt.datetime.fromisoformat(f'{day}T{hhmm}:00').replace(tzinfo=TZ)
    p = pathlib.Path(payload).resolve()
    o = json.loads(p.read_text())
    checks(o, slot, content_file)
    rv = p.parent / 'review.md'
    if not rv.exists() or 'humanizer-zh' not in rv.read_text():
        raise ValueError(f'缺少去AI味记录：{rv}（需调用 humanizer-zh skill 改稿并记录）')
    from lint_content import lint
    lr = lint(p, content_file)
    (p.parent / f'{p.stem}.lint.json').write_text(dump(lr))
    if lr['errors']:
        raise ValueError('内容体检未过（scripts/lint_content.py）：' + '；'.join(lr['errors']))
    video_gate(p)   # 带视频的条目先过声音质检，不过就拦（00-必读 2.3.9）
    tag_warn = tag_check(p, slot, '快反' if '-hot-' in iid else hhmm)
    st = pform(o, acc['platform']).get('scheduledTime')
    mode = 'native' if st else 'dispatch'
    if st and int(st) != int(due.timestamp() * 1000):
        raise ValueError('scheduledTime 与排期时间不一致')
    if mode == 'native' and acc.get('native_lead_min') and (due - now()).total_seconds() < acc['native_lead_min'] * 60:
        raise ValueError(f"原生定时需提前≥{acc['native_lead_min']}分钟；改为不带 scheduledTime 的 dispatch")
    old = c.execute('SELECT status FROM items WHERE id=?', (iid,)).fetchone()
    if old and old['status'] not in ('draft', 'checked', 'ready', 'blocked'):
        raise ValueError(f"{iid} 已是 {old['status']}，禁止覆盖")
    c.execute('INSERT OR REPLACE INTO items(id,day,slot,platform,account_id,publish_type,due,mode,status,payload,content_file,hash,title,updated) '
              'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
              (iid, day, slot, acc['platform'], acc['account_id'], o.get('publishType', acc['type']), due.isoformat(), mode, 'draft', str(p),
               str(pathlib.Path(content_file).resolve()) if content_file else None, digest(p), title_of(o, acc['platform']), now().isoformat()))
    r = c.execute('SELECT * FROM items WHERE id=?', (iid,)).fetchone()
    ok, o2 = preflight(c, r)
    status = ('ready' if approve else 'checked') if ok else 'blocked'
    c.execute('UPDATE items SET status=?,detail=?,updated=? WHERE id=?', (status, None if ok else dump(o2.get('error', o2)), now().isoformat(), iid))
    ev(c, iid, 'add', {'status': status, 'mode': mode})
    res = {'id': iid, 'status': status, 'mode': mode, 'due': due.isoformat(), 'error': None if ok else o2.get('error', o2)}
    if tag_warn:
        res['tag_warnings'] = tag_warn
    return res


def video_gate(post_path, strict=True):
    """声音关卡（10-16 用户：「视频声音全出问题了……以后不要再出现这个问题」）：带视频的条目，成片必须过 scripts/audio_qc.py，
    且质检结果比视频文件新（改过视频就得重测）。没测过就当场测一遍（约 1–2 分钟）。strict=False 只提醒不拦。"""
    try:
        post = pathlib.Path(post_path)
        if not post.is_absolute():
            post = ROOT / post
        if post.name.endswith('.payload.json'):
            post = post.with_name(post.name.replace('.payload.json', '.json'))
        d = json.loads(post.read_text()) if post.exists() else {}
        v = d.get('video')
        if not v:
            return None
        mp4 = (post.parent / v) if not pathlib.Path(v).is_absolute() else pathlib.Path(v)
        if not mp4.exists():
            return None
        qc = pathlib.Path(str(mp4) + '.audioqc.json')
        if not qc.exists() or qc.stat().st_mtime < mp4.stat().st_mtime:
            subprocess.run([sys.executable, str(ROOT / 'scripts/audio_qc.py'), str(mp4)], capture_output=True, text=True, timeout=1200)
        r = json.loads(qc.read_text()) if qc.exists() else {'ok': False, 'errors': ['声音质检没跑出结果']}
        if not r.get('ok'):
            msg = f"声音质检不通过（{mp4.name}）：" + '；'.join(r.get('errors', []))[:400] + '。修好重渲染后再发（scripts/audio_qc.py）'
            if strict:
                raise ValueError(msg)
            print('⚠️ ' + msg, file=sys.stderr)
        return r
    except ValueError:
        raise
    except Exception as x:
        print(f'⚠️ 声音关卡没跑成：{x}', file=sys.stderr)
        return None


def tag_check(payload, slot, hhmm):
    """自我进化要靠标签对数据：没写栏目/实验分组的作品进不了对比（运营计划.md 第 4 节）。只提醒，不拦发布。"""
    warn = []
    try:
        post = payload.with_name(payload.name.replace('.payload.json', '.json'))
        d = json.loads(post.read_text()) if post.exists() else {}
        spec = payload.parent / 'spec.json'
        s = json.loads(spec.read_text()) if spec.exists() else {}
        if not (d.get('column') or s.get('column')):
            warn.append(f'{post.name} 没写 "column" 栏目')
        import playbook
        exp = {**(s.get('exp') or {}), **(d.get('exp') or {})}
        key = f'{slot}@{hhmm}'
        for e in playbook.running_exps():
            if not playbook.applies(e, key) or (d.get('kind') == 'video' and e.get('skip_video')):
                continue
            want = playbook.arm_for(e, key)
            got = exp.get(e['id'])
            if got != want:
                warn.append(f'实验 {e["id"]} 今天 {key} 应为 {want} 组，post/spec 里是 {got or "没写"}（写 "exp": {{"{e["id"]}": "{want}"}}）')
    except Exception as x:
        warn.append(f'标签检查没跑成：{x}')
    if warn:
        print('⚠️ 标签提醒：' + '；'.join(warn), file=sys.stderr)
    return warn


def find_task_id(data):
    if isinstance(data, dict):
        for k in ('taskSetId', 'task_set_id', 'taskSetID'):
            if data.get(k):
                return str(data[k])
        if isinstance(data.get('id'), str) and ('tasks' in data or 'taskSetStatus' in data):
            return data['id']
        for k in ('taskSet', 'task_set', 'data'):
            if k in data:
                t = find_task_id(data[k])
                if t:
                    return t
    return None


def submit(c, iid, from_dispatch=False):
    r = c.execute('SELECT * FROM items WHERE id=?', (iid,)).fetchone()
    if not r or r['status'] != 'ready':
        raise ValueError(f'{iid} 不是 ready，阻止重复提交')
    if SCHED['accounts'].get(r['slot'], {}).get('publish_via') == 'external_agent':
        raise ValueError('此平台交由其他 Agent 发布；本调度器只保留内容交接，不自动提交')
    if SCHED['accounts'].get(r['slot'], {}).get('publish_via') == 'email':
        raise ValueError('此平台已改为邮件交付、本人手动发布；请运行 publication_mail.py，禁止平台自动提交')
    if SCHED['accounts'].get(r['slot'], {}).get('publish_via') == 'web':
        raise ValueError('此平台当前使用网页发布；禁止经已隔离的 CLI 通道提交，请保留原单并走网页查重发布')
    if r['slot'] == 'x':
        from x_api import submit as x_submit
        return x_submit(c, iid)
    due = dt.datetime.fromisoformat(r['due'])
    if r['mode'] == 'dispatch':
        lag = (now() - due).total_seconds()
        if lag < 0:
            raise ValueError('未到发布时间')
        if lag > 600 and from_dispatch:
            # 调度迟了不自动连发（防刷屏），转 failed 进补发清单，由在跑的任务按间隔补发（10-16 用户：失败要解决阻断后重发）
            c.execute("UPDATE items SET status='failed',detail=?,updated=? WHERE id=?",
                      (f'调度迟了 {int(lag // 60)} 分钟没提交，待补发（ops.py retry）', now().isoformat(), iid))
            ev(c, iid, 'late', {'lag_min': int(lag // 60)})
            return {'id': iid, 'status': 'failed', 'reason': 'late, queued for retry'}
    elif due <= now():
        raise ValueError('原生定时时间已过')
    if digest(r['payload']) != r['hash']:
        raise ValueError('载荷在预检后被修改，需重新 add')
    cur = c.execute("UPDATE items SET status='submitting',updated=? WHERE id=? AND status='ready'", (now().isoformat(), iid))
    if cur.rowcount != 1:
        raise ValueError('已被其他进程领取')
    extra = ['--content-file', r['content_file']] if r['content_file'] else []
    out = ROOT / 'days' / r['day'] / 'receipts'
    out.mkdir(parents=True, exist_ok=True)
    try:
        rc, o = cli(['publish', r['publish_type'], r['platform'], r['payload'], '--publish-channel', channel_of(r['slot']), *extra], timeout=420)
        (out / f'{iid}-submit.json').write_text(dump(o))
        tid = find_task_id(o.get('data') or {})
        status = 'submitted' if (o.get('ok') and tid) else 'uncertain'
        c.execute('UPDATE items SET status=?,task_id=?,detail=?,updated=? WHERE id=?', (status, tid, dump(o)[:20000], now().isoformat(), iid))
        ev(c, iid, 'submit', {'ok': o.get('ok'), 'task_id': tid})
        return {'id': iid, 'status': status, 'task_id': tid}
    except Exception as e:
        c.execute("UPDATE items SET status='uncertain',detail=? WHERE id=?", (f'提交异常：{e}；必须先核查平台作品列表，禁止直接重发', iid))
        raise


def dispatch(c):
    res = []
    due_rows = [r for r in c.execute("SELECT * FROM items WHERE status='ready' AND mode='dispatch' ORDER BY due").fetchall()
                if now() >= dt.datetime.fromisoformat(r['due'])]
    down, canary = {}, False
    if any(r['slot'] != 'x' for r in due_rows):
        from playbook import proxy_health, NO_PROXY_SLOTS   # 代理故障时不再往坏通道里送（00-必读 2.5.9），转网页待发
        h = proxy_health()
        down, canary = h['slots'], h.get('canary', False)
    for r in due_rows:
        if r['slot'] == 'x':
            from x_api import submit as x_submit
            try:
                res.append(x_submit(c, r['id']))
            except Exception as e:
                res.append({'id': r['id'], 'error': str(e)})
            continue
        # 所有账号绑的是同一个代理入口：一个平台判故障，其他走代理的平台（知乎等最近没提交过的）也一样
        if down and r['slot'] not in NO_PROXY_SLOTS and canary:
            canary = False   # 故障超过 1 小时：放这一条去云端试探，失败会进补发清单，成功就恢复
            ev(c, r['id'], 'canary', {'why': '代理故障超过 1 小时，试探云端'})
        elif down and r['slot'] not in NO_PROXY_SLOTS:
            hit = down.get(r['slot']) or next(iter(down.values()))
            c.execute("UPDATE items SET status='web_pending',detail=?,updated=? WHERE id=? AND status='ready'",
                      (f"蚁小二代理故障中（{hit[2]} 失败），到点自动转网页待发", now().isoformat(), r['id']))
            ev(c, r['id'], 'webq', {'auto': True})
            res.append({'id': r['id'], 'status': 'web_pending'})
            continue
        try:
            res.append(submit(c, r['id'], True))
        except Exception as e:
            res.append({'id': r['id'], 'error': str(e)})
    return res


# ---------- 失败补发（10-16 用户：「发布失败的内容重新发布……以后出现这种情况也是解决阻断去发布」）----------
DONE = ('submitting', 'submitted', 'scheduled', 'success', 'public')


def base_id(iid):
    """补发条目和原条目归一组：去掉 -r1 / -web / -local 后缀，以及数字后紧跟的 w/b（channels-wb2w、office-0b）。"""
    b = iid
    while True:
        n = re.sub(r'(?<=\d)[wb]$', '', re.sub(r'-(r\d+|web\d*|local)$', '', b))
        if n == b:
            return b
        b = n


def why(detail):
    try:
        d = json.loads(detail or '')
        msg = '；'.join(m for m in ((t.get('errorMessage') or t.get('message')) for t in d.get('tasks', [])) if m)
        return msg[:120] or '（无报错原文）'
    except Exception:
        return (detail or '')[:120]


def post_title(payload):
    try:
        return json.loads((pathlib.Path(payload).parent / 'post.json').read_text()).get('title', '')
    except Exception:
        return ''


def retry(c, day=None):
    """同组已有提交成功/定时/发布中的 → 已补；用户撤掉的 → 不补；含 failed / web_pending 的组 → 要补；uncertain → 先核实。"""
    day = day or now().date().isoformat()
    groups = {}
    for r in c.execute("SELECT * FROM items WHERE day=? AND mode!='draft' ORDER BY due, updated", (day,)):
        groups.setdefault(base_id(r['id']), []).append(r)
    ids = {r['id'] for rs in groups.values() for r in rs}
    out = []
    for b, rs in groups.items():
        st = {r['status'] for r in rs}
        if st & set(DONE) or 'withdrawn' in st:
            continue
        pub = [r for r in rs if r['status'] == 'publishing']
        if pub and now() - dt.datetime.fromisoformat(pub[-1]['updated']) < dt.timedelta(minutes=30):
            continue
        if pub:
            action = '先去平台核实（网页发布占位超过 30 分钟没登记结果）'
        elif 'uncertain' in st:
            action = '先去平台核实（提交结果不确定，禁止直接重发）'
        elif st & {'failed', 'web_pending'}:
            due = dt.datetime.fromisoformat(max(rs, key=lambda r: r['updated'] or '')['due'])
            action = '现在补发' if due <= now() + dt.timedelta(minutes=10) else f'到点 {due:%H:%M} 发（能网页定时的现在就定时）'
        else:
            continue   # 只有 blocked（人为暂停）的组不算失败
        last = max(rs, key=lambda r: r['updated'] or '')   # 以最近一次改动的条目为准（改过时间的按新时间）
        new_id = next(f'{b}-web{k or ""}' for k in range(10) if f'{b}-web{k or ""}' not in ids)
        out.append({'group': b, 'slot': last['slot'], 'platform': last['platform'], 'due': last['due'][11:16],
                    'title': next((r['title'] for r in rs if r['title']), '') or post_title(last['payload']),
                    'tried': [f"{r['id']}:{r['status']}" for r in rs],
                    'why': why(last['detail']), 'payload': last['payload'], 'action': action, 'new_id': new_id})
    return out


def register_web(c, iid, slot, hhmm, post_json, note, status, content_file=''):
    acc = SCHED['accounts'][slot]
    post = json.loads(pathlib.Path(post_json).read_text())
    day = post.get('day') or now().date().isoformat()
    due = f'{day}T{hhmm}:00+08:00'
    c.execute('INSERT OR REPLACE INTO items(id,day,slot,platform,account_id,publish_type,due,mode,status,payload,content_file,hash,title,detail,updated) '
              'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
              (iid, day, slot, acc['platform'], acc['account_id'], post.get('kind') or acc['type'], due, 'web', status, str(pathlib.Path(post_json).resolve()),
               content_file or '', '', post.get('title', ''), note, now().isoformat()))
    ev(c, iid, 'web' if status == 'scheduled' else 'claim', {'due': due})
    return {'id': iid, 'status': status, 'mode': 'web', 'due': due}


def reconcile(c, day=None):
    res = []
    q = "SELECT * FROM items WHERE task_id IS NOT NULL AND status IN ('submitted','scheduled','success','uncertain')"
    for r in c.execute(q).fetchall():
        rc, o = cli(['query', 'details', r['task_id']])
        data = o.get('data') or {}
        tasks = data.get('tasks', []) if isinstance(data, dict) else []
        status, url = r['status'], r['url']
        if tasks:
            stages = [t.get('stageStatus') for t in tasks]
            if all(x == 'success' for x in stages):
                status = 'scheduled' if any(t.get('stages') == 'scheduled' for t in tasks) else 'success'
            elif any(x in ('failed', 'fail', 'error') for x in stages):
                status = 'failed'
            for t in tasks:
                u = t.get('openUrl') or ''
                # 只接受目标平台域名的链接（yxer 有时把正文里的来源链接当 openUrl 返回）
                if u and any(dom in u for dom in ('douyin.com', 'iesdouyin.com', 'weixin.qq.com', 'channels.weixin', 'xiaohongshu.com', 'xhslink', 'weibo.com', 'weibo.cn', 'zhihu.com', 'mp.weixin', 'bilibili.com', 'b23.tv')):
                    url = u
        c.execute('UPDATE items SET status=?,url=?,detail=?,updated=? WHERE id=?', (status, url, dump(data)[:20000], now().isoformat(), r['id']))
        res.append({'id': r['id'], 'status': status, 'url': url,
                    'stage': [(t.get('stages'), t.get('stageStatus'), t.get('errorMessage') or t.get('message')) for t in tasks]})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd')
    ap.add_argument('args', nargs='*')
    ap.add_argument('--content-file')
    ap.add_argument('--approve', action='store_true')
    n = ap.parse_args()
    c = connect()
    a = n.args
    if n.cmd == 'add':
        out = add(c, a[0], a[1], a[2], a[3], n.content_file, n.approve)
    elif n.cmd == 'approve':
        out = []
        for iid in a:
            r = c.execute('SELECT * FROM items WHERE id=?', (iid,)).fetchone()
            if not r or r['status'] != 'checked':
                out.append({'id': iid, 'error': f"不是 checked（当前 {r['status'] if r else '无'}）"}); continue
            if digest(r['payload']) != r['hash']:
                out.append({'id': iid, 'error': '载荷已改动，需重新 add'}); continue
            c.execute("UPDATE items SET status='ready',updated=? WHERE id=?", (now().isoformat(), iid))
            ev(c, iid, 'approve', {})
            out.append({'id': iid, 'status': 'ready'})
    elif n.cmd == 'submit':
        out = submit(c, a[0])
    elif n.cmd == 'dispatch':
        out = dispatch(c)
    elif n.cmd == 'reconcile':
        out = reconcile(c)
    elif n.cmd == 'status':
        day = a[0] if a else now().date().isoformat()
        out = [dict(id=r['id'], due=r['due'][11:16], platform=r['platform'], mode=r['mode'], status=r['status'], title=r['title'], url=r['url'], verified=r['url_verified'])
               for r in c.execute('SELECT * FROM items WHERE day=? ORDER BY due', (day,))]
    elif n.cmd == 'retry':
        out = retry(c, a[0] if a else None)
    elif n.cmd == 'hold':
        cur = c.execute("UPDATE items SET status='blocked',detail=? WHERE id=? AND status IN ('ready','checked','draft')", (a[1], a[0]))
        out = {'held': cur.rowcount}
    elif n.cmd == 'webq':
        cur = c.execute("UPDATE items SET status='web_pending',detail=?,updated=? WHERE id=? AND status IN ('ready','checked','draft','blocked','failed')",
                        (a[1], now().isoformat(), a[0]))
        ev(c, a[0], 'webq', {'note': a[1]})
        out = {'web_pending': cur.rowcount}
    elif n.cmd == 'withdraw':
        cur = c.execute(f"UPDATE items SET status='withdrawn',detail=?,updated=? WHERE id=? AND status NOT IN {DONE}", (a[1], now().isoformat(), a[0]))
        ev(c, a[0], 'withdraw', {'note': a[1]})
        out = {'withdrawn': cur.rowcount}
    elif n.cmd in ('web', 'claim'):
        # 网页直发的作品（不经蚁小二，例如视频号走 scripts/web_publish/channels.js）也要进台账，日报和数据回流才对得上；
        # claim = 发之前先占位（publishing），发完再用 web 同一个 id 登记成 scheduled
        if n.cmd == 'claim':
            hit = c.execute("SELECT id,status FROM items WHERE id=?", (a[0],)).fetchone()
            if hit:
                raise ValueError(f'{a[0]} 已存在（{hit["status"]}），可能别的会话在发，先核实')
            video_gate(a[3])            # 网页发之前同样要过声音质检
        else:
            video_gate(a[3], strict=False)
        out = register_web(c, a[0], a[1], a[2], a[3], ' '.join(a[4:]) or '网页直发',
                           'scheduled' if n.cmd == 'web' else 'publishing', n.content_file)
    elif n.cmd == 'link':
        c.execute("UPDATE items SET url=?,url_verified=1,status='public',updated=? WHERE id=?", (a[1], now().isoformat(), a[0]))
        ev(c, a[0], 'link', {'url': a[1]})
        out = {'public': a[1]}
    else:
        raise SystemExit(__doc__)
    print(dump(out))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(dump({'ok': False, 'error': str(e)}))
        sys.exit(1)
