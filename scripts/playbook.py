#!/usr/bin/env python3
"""运营手册的「单一来源」工具：所有定时任务开工先跑 start，保证大家跑的是同一版运营规划。

为什么要它：10-16 发现定时任务提示词里各自抄了一份规则，手册改了提示词没改（配音、贴纸位置、快反条数都出过冲突），
优化过的东西定时任务还在按旧的做。现在规则只放在 运营手册/，任务提示词只说「你是哪个任务」，开工用这个脚本：
打印当前版本、运营计划里生效中的调整、今天的实验分组，并体检手册里有没有残留的旧说法。

用法:
  playbook.py start <任务>            开工：版本 + 体检摘要 + 生效调整 + 实验分组，记 days/<今天>/runs.jsonl
  playbook.py end <任务> "<一句话结果>"   收工记录
  playbook.py audit                   体检：作废说法残留、任务提示词是否指向手册、实验是否到期、待修问题
  playbook.py assign [任务|slot@HH:MM]  今天各时段的实验分组
  playbook.py bump "<说明>" [--source 用户|数据|事故|运营] [--files a,b]   改了规则后升版本、写变更日志
  playbook.py version
任务名：早班 午班 晚班 Office课 热点雷达 账号活跃 日报 周进化 手动
"""
import datetime as dt, glob, json, os, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, now, env

MANUAL = ROOT / '运营手册'
ENTRY = MANUAL / '00-必读.md'
PLAN = MANUAL / '运营计划.md'
CHANGELOG = MANUAL / '变更日志.md'
RULES = ROOT / 'config/playbook_rules.json'
EXPS = ROOT / 'config/experiments.json'
VER_RE = re.compile(r'^版本：(v[\d.]+-\d+)', re.M)
WEEK = '一二三四五六日'


def rules():
    return json.loads(RULES.read_text())


def version():
    m = VER_RE.search(ENTRY.read_text()) if ENTRY.exists() else None
    return m.group(1) if m else 'v?'


def day_dir():
    d = ROOT / 'days' / now().date().isoformat()
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_run(task, event, summary=''):
    rec = {'at': now().isoformat(timespec='seconds'), 'task': task, 'event': event, 'version': version(), 'summary': summary}
    with open(day_dir() / 'runs.jsonl', 'a') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')


def section(text, title_kw):
    """取 markdown 里标题含 title_kw 的那一节（到下一个同级或更高标题为止）。"""
    lines, out, level = text.splitlines(), [], None
    for ln in lines:
        m = re.match(r'^(#+)\s', ln)
        if m and level is not None and len(m.group(1)) <= level:
            break
        if level is None and m and title_kw in ln:
            level = len(m.group(1))
        if level is not None:
            out.append(ln)
    return '\n'.join(out).strip()


# ---------- 体检 ----------
def scan_files(cfg):
    files = []
    for pat in cfg['scan']:
        p = os.path.expanduser(pat)
        files += glob.glob(p if p.startswith('/') else str(ROOT / p))
    skip = {str(ROOT / s) for s in cfg.get('skip_files', [])}
    return sorted(f for f in set(files) if f not in skip)


def audit(verbose=True):
    cfg = rules()
    errs, warns = [], []
    if not ENTRY.exists():
        errs.append('缺 运营手册/00-必读.md')
    elif version() == 'v?':
        errs.append('00-必读.md 没有「版本：vYYYY.MM.DD-N」行')
    if not PLAN.exists():
        errs.append('缺 运营手册/运营计划.md')
    markers = cfg.get('skip_line_markers', [])
    pats = [(d, re.compile(d['pattern'])) for d in cfg['deprecated']]
    for f in scan_files(cfg):
        rel = f.replace(str(ROOT) + '/', '').replace(os.path.expanduser('~'), '~')
        for i, ln in enumerate(pathlib.Path(f).read_text(errors='ignore').splitlines(), 1):
            if any(mk in ln for mk in markers):
                continue
            for d, rx in pats:
                if rx.search(ln):
                    errs.append(f'{rel}:{i} 残留作废说法 [{d["id"]}]「{rx.search(ln).group(0)}」→ 现在：{d["now"]}')
    errs += facts_check(scan_files(cfg))
    errs += times_check(scan_files(cfg))
    tp = cfg['task_prompt']
    for f in glob.glob(os.path.expanduser(tp['glob'])):
        t = pathlib.Path(f).read_text()
        name = pathlib.Path(f).parent.name
        for s in tp['must_contain']:
            if s not in t:
                errs.append(f'定时任务 {name} 提示词没有指向「{s}」（会跑旧规则）')
        body = t.split('---', 2)[-1]
        if len(body) > tp['max_chars']:
            warns.append(f'定时任务 {name} 提示词 {len(body)} 字，超过 {tp["max_chars"]}：具体规则应放进手册，提示词只写任务身份')
    try:
        exps = json.loads(EXPS.read_text())['experiments']
        today = now().date().isoformat()
        for e in exps:
            for k in ('id', 'title', 'metric', 'arms', 'review', 'status'):
                if k not in e:
                    errs.append(f'experiments.json {e.get("id")} 缺字段 {k}')
            if e.get('status') == 'running' and e.get('review', '9') < today:
                warns.append(f'实验 {e["id"]}「{e["title"]}」{e["review"]} 已到期未评估（日报/周进化处理）')
    except Exception as x:
        errs.append(f'config/experiments.json 读不了：{x}')
    if PLAN.exists():
        todo = [l for l in section(PLAN.read_text(), '待修问题').splitlines()[1:] if l.strip().startswith(('-', '|')) and '（无）' not in l and '---' not in l and '问题' not in l[:8]]
        if todo:
            warns.append(f'运营计划.md「待修问题」有 {len(todo)} 条未处理')
    if verbose:
        print(f'## 手册体检（{version()}）：{len(errs)} 个错误，{len(warns)} 个提醒')
        for e in errs:
            print('  ✗', e)
        for w in warns:
            print('  !', w)
        if not errs and not warns:
            print('  ✓ 没发现冲突')
    return errs, warns


# ---------- 事实一致性：同一个参数在不同文件里取值必须一样（10-16 审计手工查出 9 处，正则查旧说法查不出）----------
def facts():
    """标准值：能从配置/脚本取的就从那里取（改配置 = 改标准），其余写在 playbook_rules.json 的 facts 里。"""
    out = []
    try:
        sys.path.insert(0, str(ROOT / 'scripts'))
        import engage
        for plat, cap in engage.CAPS.items():
            if cap.get('comment'):
                out.append({'name': f'{plat}每日评论上限', 'expect': str(cap['comment']),
                            'patterns': [rf'^\|\s*{plat}\s*\|\s*≤(\d+)\s*\|', rf'评论(?:上限|别人)[^。\n|]{{0,40}}?{plat}\s*≤?\s*(\d+)']})
    except Exception as x:
        out.append({'name': f'engage.CAPS 读取失败：{x}', 'expect': '', 'patterns': []})
    sched = json.loads((ROOT / 'config/schedule.json').read_text())['accounts']
    for slot, label in (('weibo', '微博'), ('xhs', '小红书'), ('zhihu', '知乎'), ('channels', '视频号')):
        if slot in sched:
            out.append({'name': f'{label}日配额', 'expect': str(len(sched[slot]['times'])),
                        'patterns': [rf'配额[^\n]{{0,80}}?{label}\s*(\d{{1,2}})(?![:：\d–\-])']})
    out += rules().get('facts', [])
    return out


SLOT_LABELS = {'xhs': '小红书', 'weibo': '微博', 'zhihu': '知乎', 'channels': '视频号', 'kuaishou': '快手', 'bilibili': 'B站', 'wechat_tietu': '公众号贴图'}


def times_check(files):
    """「小红书 08:20、12:20」这种写法里的时间，必须是 config/schedule.json 里该平台现在的时段（快反/补位/历史说明行除外）。"""
    sched = json.loads((ROOT / 'config/schedule.json').read_text())['accounts']
    markers = rules().get('skip_line_markers', []) + ['快反', '补位', '原来', '旧', '改到', '改成', '例']
    errs = []
    for f in files:
        if 'scheduled-tasks' in f or f.endswith(('00-必读.md',)) is False and '运营手册' not in f:
            continue
        rel = f.replace(str(ROOT) + '/', '')
        for i, ln in enumerate(pathlib.Path(f).read_text(errors='ignore').splitlines(), 1):
            if any(mk in ln for mk in markers):
                continue
            for slot, label in SLOT_LABELS.items():
                if slot not in sched:
                    continue
                for m in re.finditer(rf'(?<![\u4e00-\u9fa5]){label}\s*((?:\d{{2}}:\d{{2}}\s*[、/，,]?\s*)+)', ln):
                    for hm in re.findall(r'\d{2}:\d{2}', m.group(1)):
                        if hm not in sched[slot]['times']:
                            errs.append(f'{rel}:{i} 时段对不上：{label} {hm} 不在 config/schedule.json（现在是 {"、".join(sched[slot]["times"])}）')
    return errs


def facts_check(files):
    errs = []
    fs = facts()
    markers = rules().get('skip_line_markers', [])
    for f in files:
        if 'scheduled-tasks' in f:
            continue
        rel = f.replace(str(ROOT) + '/', '')
        for i, ln in enumerate(pathlib.Path(f).read_text(errors='ignore').splitlines(), 1):
            if any(mk in ln for mk in markers):
                continue
            for fa in fs:
                for pat in fa['patterns']:
                    for m in re.finditer(pat, ln):
                        if m.group(1) != fa['expect']:
                            errs.append(f'{rel}:{i} 参数对不上「{fa["name"]}」：写的是 {m.group(1)}，标准是 {fa["expect"]}')
    return errs


# ---------- 实验分组 ----------
def running_exps():
    try:
        today = now().date().isoformat()
        return [e for e in json.loads(EXPS.read_text())['experiments']
                if e.get('status') in ('running', 'extended') and (e.get('start') or '') <= today]  # 没到开始日不分组
    except Exception:
        return []


def arm_for(e, slot, day=None):
    """按 (实验, 日期, 时段) 哈希分组：确定可复现（同一天同一时段谁来跑都是同一组），
    各实验之间互相独立（按位置轮换会让两个实验的分组永远绑在一起，分不出是谁的效果）。"""
    import hashlib
    day = day or now().date()
    arms = sorted(e['arms'])
    h = int(hashlib.sha1(f'{e["id"]}|{day.isoformat()}|{slot}'.encode()).hexdigest(), 16)
    return arms[h % len(arms)]


def applies(e, slot):
    plat = slot.split('@')[0]
    if e.get('slots'):
        return slot in e['slots']
    return plat in e.get('platforms', [])


def assign(target=None):
    cfg = rules()
    if target and '@' in target:
        slots = [target]
    elif target in cfg['tasks']:
        slots = cfg['tasks'][target]['slots']
    else:
        slots = sorted({s for t in cfg['tasks'].values() for s in t['slots']})
    out = []
    for e in running_exps():
        for s in slots:
            if applies(e, s):
                a = arm_for(e, s)
                out.append((s, e['id'], a, e['title'], e['arms'][a]))
    return out


def print_assign(target):
    rows = assign(target)
    print('## 今天的实验分组（制作时照做，并在 post*.json / spec.json 写 "exp": {"编号": "组"}）')
    if not rows:
        print('  （本任务没有要执行的实验）')
    for s, i, a, t, desc in rows:
        print(f'  {s:<18} {i} → {a} 组｜{t}：{desc}')


# ---------- 蚁小二代理健康（10-16：内置快代理入口故障，云端和本机客户端通道都走它）----------
PROXY_ERR = ('ECONNREFUSED', 'Proxy connection', 'CONNECT response', '代理')
NO_PROXY_SLOTS = {'bilibili', 'kuaishou'}   # B站、快手走开放平台，不经过账号代理。公众号只有推草稿不经代理，正式发表要走（10-16 09:00 gzh-wb 实测失败）


CANARY_MIN = 60   # 最近一次代理失败超过这么多分钟、又没有在途的试探，就放一条内容去云端试（失败卡在推送阶段，不会到平台）


def proxy_health(hours=24):
    """看台账最近 24 小时的云端/本机提交：某平台最近一次结果是代理类失败 → 判故障；之后有成功就恢复。
    恢复靠两样：yxer_probe 不发内容的探测（经账号代理查地理位置），加上每小时一次的「试探提交」（canary=True 时放一条去云端）。"""
    import sqlite3
    db = ROOT / 'state/ops.sqlite3'
    if not db.exists():
        return {'down': False, 'slots': {}}
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    since = (now() - dt.timedelta(hours=hours)).isoformat()
    last = {}
    # 按「提交时间」排（events 里的 submit），不按 updated：老条目被 reconcile 刷新不算新的成功
    q = ("SELECT e.at, i.id, i.slot, i.status, i.detail FROM events e JOIN items i ON i.id = e.item "
         "WHERE e.kind = 'submit' AND e.at >= ? ORDER BY e.at")
    for at, iid, slot, status, detail in c.execute(q, (since,)):
        if slot in NO_PROXY_SLOTS:
            continue
        d = detail or ''
        if status == 'failed' and any(k in d for k in PROXY_ERR):
            last[slot] = ('down', at[11:16], iid)
        elif status in ('scheduled', 'success', 'public', 'submitted'):
            last[slot] = ('ok', at[11:16], iid)
    down = {s: v for s, v in last.items() if v[0] == 'down'}
    # 故障期间不往云端送内容，就等不到「新的云端成功」→ 用不发内容的探测判断恢复：探测通了就放回云端，再失败会自动重新判故障
    alive = []
    if down and yxer_probe():     # 不发内容的真实探测通了 → 蚁小二代理通路恢复，放回云端（再失败会自动重新判故障）
        alive, down = ['蚁小二地理位置查询'], {}
    canary = False
    if down:
        ids = [v[2] for v in down.values()]
        newest = c.execute(f"SELECT MAX(at) FROM events WHERE kind = 'submit' AND item IN ({','.join('?' * len(ids))})", ids).fetchone()[0]
        age = (now() - dt.datetime.fromisoformat(newest)).total_seconds() / 60 if newest else CANARY_MIN
        cut = (now() - dt.timedelta(minutes=CANARY_MIN)).isoformat()
        inflight = c.execute("SELECT COUNT(*) FROM events e JOIN items i ON i.id = e.item WHERE e.kind = 'submit' AND e.at >= ? "
                             "AND i.status IN ('submitting','submitted')", (cut,)).fetchone()[0]
        canary = age >= CANARY_MIN and not inflight
    return {'down': bool(down), 'slots': down, 'probe_ok': sorted(alive), 'canary': canary}


PROBE_CACHE = ROOT / 'state/proxy_probe.json'
PROBE_ACCOUNT = env().get('OPS_PROBE_ACCOUNT', '')   # 抖音示例作者：query locations 走账号的蚁小二代理去平台查，不发任何内容（10-16 找到）


def yxer_probe(ttl_min=15):
    """不发内容的代理探测：yxer query locations 由蚁小二云端经账号代理访问平台。
    通 → True；报 ECONNREFUSED/代理类错误 → False；其他错误（比如登录失效）→ None（不下结论）。结果缓存 15 分钟。"""
    import subprocess
    try:
        c = json.loads(PROBE_CACHE.read_text())
        if (now() - dt.datetime.fromisoformat(c['at'])).total_seconds() < ttl_min * 60:
            return c['ok']
    except Exception:
        pass
    try:
        r = subprocess.run(['yxer', 'query', 'locations', PROBE_ACCOUNT, '--keyword', '厦门', '--json'],
                           capture_output=True, text=True, timeout=60)
        d = json.loads((r.stdout or r.stderr).strip())
        msg = json.dumps(d.get('error') or '', ensure_ascii=False)
        ok = True if d.get('ok') else (False if any(k in msg for k in PROXY_ERR) else None)
    except Exception as x:
        ok, msg = None, str(x)
    try:
        prev = json.loads(PROBE_CACHE.read_text()).get('ok')
    except Exception:
        prev = None
    PROBE_CACHE.write_text(json.dumps({'at': now().isoformat(timespec='seconds'), 'ok': ok, 'msg': msg[:200]}, ensure_ascii=False))
    if prev is False and ok is True:   # 从坏到好：发邮件告诉用户（alert_mail 同标题 6 小时内不重发）
        subprocess.run([sys.executable, str(ROOT / 'scripts/alert_mail.py'), 'send', '--title', '蚁小二代理恢复了',
                        '--body', '不发内容的探测（抖音示例作者 查地理位置）已经通了，各平台自动切回蚁小二云端发布。网页兜底期间转「网页待发」的条目照补发清单处理。'],
                       capture_output=True, timeout=60)
    return ok


def print_retry():
    """失败待补发（00-必读 2.1.6）：每个任务开工都看到，能处理的先处理。"""
    try:
        import sqlite3
        import ops
        c = sqlite3.connect(ROOT / 'state/ops.sqlite3')
        c.row_factory = sqlite3.Row
        rows = ops.retry(c)
    except Exception as e:
        print(f'## 失败待补发：读台账出错（{e}），手动跑 ops.py retry')
        return
    if not rows:
        print('## 失败待补发：没有')
        return
    print(f'## ⚠️ 失败待补发 {len(rows)} 组（00-必读 2.1.6：先解决阻断再发，不因错过窗口放弃；做法见 批次执行.md「失败补发」）')
    for r in rows:
        print(f"  {r['due']} {r['slot']:<14} {r['title'][:24]}｜{r['action']}｜新 id {r['new_id']}｜原因：{r['why'][:60]}")


def print_proxy():
    h = proxy_health()
    if not h['down']:
        print('## 蚁小二代理：' + (f"探测 {'、'.join(h['probe_ok'])} 已通，放回云端（再失败会自动重新判故障）。"
                                  if h.get('probe_ok') else '最近 3 小时没有代理类失败，按平常通道发布。'))
        return
    print('## ⚠️ 蚁小二代理故障中（运营手册/00-必读.md 2.5.9）')
    if h.get('canary'):
        print(f'  ⓘ 已经 {CANARY_MIN} 分钟以上没有新的代理失败：本轮放**一条**去云端试探——到点发送的由调度器自动试；'
              '批次里提前量 ≥1 小时的定时条目，先试云端，几分钟后 reconcile 失败再转网页。成功就自动恢复。')
    for s, (_, at, iid) in sorted(h['slots'].items()):
        print(f'  {s:<14} 最近失败 {at}（{iid}）')
    print('  → 所有账号共用这个代理入口：除 B站、快手外，各平台（含公众号文章正式发表、上面没列的知乎等）本轮都走本机网页发布'
          '（内置浏览器，scripts/web_publish/ 或手动），发前 ops.py claim 占位、发完 ops.py web 登记；'
          '到点的 dispatch 条目调度器会自动转「网页待发」，进 ops.py retry 清单。本机蚁小二客户端通道同样走代理，不要用。')


# ---------- 开工 / 收工 ----------
def start(task):
    cfg = rules()
    if task not in cfg['tasks']:
        print(f'未知任务「{task}」，可选：{" ".join(cfg["tasks"])}')
        sys.exit(2)
    d = now()
    print(f'# 开工：{task}｜手册 {version()}｜{d:%Y-%m-%d %H:%M} 星期{WEEK[d.weekday()]}')
    print('规则优先级：00-必读.md 第 2 节用户硬规则 > 运营计划.md 生效中的调整 > 专题手册 > 任务提示词。\n')
    errs, warns = audit(verbose=True)
    if errs:
        print('  → 有冲突时按上面的优先级执行，并把问题记进 运营计划.md「待修问题」。')
    print()
    if PLAN.exists():
        t = PLAN.read_text()
        for kw in ('生效中的调整', '待修问题'):
            s = section(t, kw)
            if s:
                print(s + '\n')
    print_proxy()
    print()
    print_retry()
    print()
    print_assign(task)
    print(f'\n下一步：读 运营手册/00-必读.md 全文（尤其第 4 节「{task}」）和 运营手册/运营计划.md，再按里面指定的文件执行。')
    log_run(task, 'start', f'{len(errs)} 错误 {len(warns)} 提醒')


def bump(note, source='运营', files=''):
    old = version()
    today = now().strftime('%Y.%m.%d')
    m = re.match(r'v([\d.]+)-(\d+)', old)
    new = f'v{today}-{int(m.group(2)) + 1}' if m and m.group(1) == today else f'v{today}-1'
    t = ENTRY.read_text()
    t = VER_RE.sub(f'版本：{new}', t, count=1)
    t = re.sub(r'(最后更新：)[^｜\n]+', lambda mm: mm.group(1) + now().strftime('%Y-%m-%d %H:%M'), t, count=1)
    ENTRY.write_text(t)
    entry = f'## {new}（{now():%Y-%m-%d %H:%M}，来源：{source}）\n\n- {note}\n' + (f'- 涉及文件：{files}\n' if files else '') + '\n'
    c = CHANGELOG.read_text() if CHANGELOG.exists() else '# 变更日志\n\n'
    head, sep, rest = c.partition('\n## ')
    CHANGELOG.write_text(head.rstrip() + '\n\n' + entry + (('## ' + rest) if sep else ''))
    print(f'{old} → {new}，已写进 变更日志.md')


def main():
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'):
        print(__doc__); return
    cmd = a[0]
    if cmd == 'start':
        start(a[1] if len(a) > 1 else '手动')
    elif cmd == 'end':
        log_run(a[1], 'end', a[2] if len(a) > 2 else '')
        print('已记录收工')
    elif cmd == 'audit':
        errs, _ = audit()
        sys.exit(1 if errs else 0)
    elif cmd == 'assign':
        print_assign(a[1] if len(a) > 1 else None)
    elif cmd == 'bump':
        # 说明不能为空，也不能是参数名（10-16 `bump --help` 曾被当成说明升了一版）
        if len(a) < 2 or a[1].startswith('-') or not a[1].strip():
            print('用法: playbook.py bump "<改了什么、为什么>" --source 用户|数据|事故|运营 --files a,b（没有升版）')
            sys.exit(2)
        opts = dict(zip(a[2::2], a[3::2]))
        bump(a[1], opts.get('--source', '运营'), opts.get('--files', ''))
    elif cmd == 'version':
        print(version())
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
