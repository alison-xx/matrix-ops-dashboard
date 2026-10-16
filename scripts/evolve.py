#!/usr/bin/env python3
"""自我进化的分析引擎：创作者中心数据 + 台账标签 → 哪些做法有效 → 给日报/周进化的调整建议。

数据：state/metrics.sqlite3（scripts/collectors 采的作品快照）+ state/ops.sqlite3（台账）+ 条目目录里的 post*.json / spec.json
      （column 栏目、exp 实验分组、kind 形式、hook_type、series）+ state/fans_history.jsonl（粉丝历史）+ config/experiments.json。
它只出结论和建议，不改任何规则文件；改不改由日报/周进化任务按 运营计划.md 第 0 节决定。

用法:
  evolve.py daily      近 7 天：各维度相对表现、到期实验判定、到复查日的调整、粉丝变化 → days/<今天>/evolve.md + evolve.json
  evolve.py weekly     近 7 天 vs 前 7 天 + 时段配比建议 → days/<今天>/evolve-weekly.md + evolve-weekly.json
  evolve.py exp        只看实验各组当前数据
口径（和 运营计划.md 第 0 节一致）：发布不满 24 小时的作品不参与结论；互动类比率只算播放 ≥50 的作品，留存类（跳出、完播）只算播放 ≥200 的作品；
维度结论至少 3 条；实验每组至少 min_n 条，判定用两组差异的 95% 置信区间（区间不含 0 才算有差别），不再用固定 15% 阈值。
"""
import datetime as dt, json, pathlib, re, sqlite3, statistics as st, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, TZ, now
import metrics

LEDGER = ROOT / 'state/ops.sqlite3'
EXPS = ROOT / 'config/experiments.json'
FANS_H = ROOT / 'state/fans_history.jsonl'
PLAN = ROOT / '运营手册/运营计划.md'
SCHED = json.loads((ROOT / 'config/schedule.json').read_text())
MIN_AGE_H, MIN_VIEWS_RATE, MIN_VIEWS_SCRIPT, MIN_DIM_N, SIG = 24, 50, 200, 3, 0.15  # 脚本归因门槛见 运营计划.md 判断口径
RATE_METRICS = {'eng_rate', 'comment_rate', 'bounce_2s', 'completion_5s', 'avg_view_ratio'}
PLAT_CN = {'douyin': '抖音', 'douyin_office': '抖音Office', 'channels': '视频号', 'xhs': '小红书', 'weibo': '微博',
           'zhihu': '知乎', 'wechat': '公众号', 'bilibili': 'B站'}


def norm(t):
    return re.sub(r'[\W_]+', '', t or '').lower()


def slot_of(platform, account):
    if platform == 'douyin' and account and 'office' in account.lower():
        return 'douyin_office'
    return platform


# ---------- 台账标签 ----------
def ledger_items(since_day):
    if not LEDGER.exists():
        return []
    c = sqlite3.connect(f'file:{LEDGER}?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    out = []
    for r in c.execute('SELECT * FROM items WHERE day >= ?', (since_day,)):
        r = dict(r)
        r['tags'] = tags_for(r)
        out.append(r)
    return out


def tags_for(r):
    """从条目目录读 column / exp / kind / hook_type / series / promo。视频号等复用抖音成片的，exp 退回 spec.json。"""
    t = {}
    try:
        p = pathlib.Path(r['payload'] or '')
        if not p.is_absolute():
            p = ROOT / p
        post = p.with_name(p.name.replace('.payload.json', '.json'))
        cands = [post, p] if post != p else [p]
        for c in cands:
            if c.exists() and c.suffix == '.json':
                d = json.loads(c.read_text())
                for k in ('column', 'exp', 'kind', 'series', 'promo', 'hook_type'):
                    if d.get(k) and k not in t:
                        t[k] = d[k]
                break
        spec = p.parent / 'spec.json'
        if spec.exists():
            s = json.loads(spec.read_text())
            for k in ('exp', 'hook_type', 'column', 'series'):
                if s.get(k) and k not in t:
                    t[k] = s[k]
    except Exception:
        pass
    return t


def match(rows, items):
    """作品快照 ↔ 台账：同平台、标题前 10 个字（去标点）互相包含，时间最近的那条。"""
    by_slot = {}
    for it in items:
        by_slot.setdefault(it['slot'], []).append(it)
    for x in rows:
        x['slot'] = slot_of(x['platform'], x.get('account'))
        nt = norm(x.get('title'))[:10]
        best, bd = None, 1e18
        for it in by_slot.get(x['slot'], []):
            it_t = norm(it.get('title'))
            if not nt or not it_t or not (it_t.startswith(nt[:8]) or nt.startswith(it_t[:8])):
                continue
            try:
                d = abs(dt.datetime.fromisoformat(it['due']).timestamp() - x['created'])
            except Exception:
                d = 1e17
            if d < bd:
                best, bd = it, d
        if not best:  # 视频号等平台的数据标题其实是描述文字：退回按发布时间匹配（±30 分钟）
            for it in by_slot.get(x['slot'], []):
                try:
                    d = abs(dt.datetime.fromisoformat(it['due']).timestamp() - x['created'])
                except Exception:
                    continue
                if d <= 1800 and d < bd and it.get('status') not in ('failed', 'blocked'):
                    best, bd = it, d
        x['item'] = best['id'] if best else None
        x['tags'] = best['tags'] if best else {}
        due_h = best['due'][11:13] if best and best.get('due') else None
        x['hour'] = due_h or dt.datetime.fromtimestamp(x['created'], TZ).strftime('%H')
    return rows


# ---------- 指标 ----------
def enrich(rows):
    t_now = now().timestamp()
    for x in rows:
        v = x.get('views') or 0
        x['views'] = v
        x['age_h'] = (t_now - x['created']) / 3600
        x['fresh'] = x['age_h'] < MIN_AGE_H
        eng = sum((x.get(k) or 0) for k in ('likes', 'favorites', 'comments', 'shares'))
        if v >= MIN_VIEWS_RATE:
            x['eng_rate'] = eng / v
            x['comment_rate'] = (x.get('comments') or 0) / v
        if v < MIN_VIEWS_SCRIPT:
            for k in ('bounce_2s', 'completion_5s', 'avg_view_ratio'):
                x.pop(k, None)  # 留存类指标要单条播放 ≥200 才做脚本归因，低于这个只算「分发不足」
        d = x.get('duration') or 0
        x['form'] = x.get('type') or ('视频' if d else '图文')
        x['len'] = '' if not d else ('<30s' if d < 30 else '30-90s' if d < 90 else '90s-3m' if d < 180 else '>3m')
        title = x.get('title') or ''
        x['title_feat'] = '+'.join(f for f, ok in (('数字', re.search(r'\d', title)), ('问句', re.search(r'[？?]', title)),
                                                   ('系列号', re.search(r'第\s*\d+\s*[集期课]|[｜|]', title))) if ok) or '平铺'
    # 相对本平台中位数的倍数（只用满 24 小时的作品做基准）
    base = {}
    for x in rows:
        if not x['fresh']:
            base.setdefault(x['slot'], []).append(x['views'])
    med = {k: max(st.median(v), 1) for k, v in base.items() if v}
    for x in rows:
        x['views_lift'] = x['views'] / med.get(x['slot'], max(x['views'], 1))
    return rows, med


def val(x, metric):
    return x.get(metric)


def summarize(group, metric):
    vs = [val(x, metric) for x in group if val(x, metric) is not None]
    if not vs:
        return None, 0
    return (st.median(vs) if metric == 'views_lift' else st.mean(vs)), len(vs)


def fmt(v, metric):
    if v is None:
        return '—'
    if metric in RATE_METRICS:
        return f'{v:.1%}'
    if metric == 'views_lift':
        return f'{v:.2f}×'
    return f'{v:.1f}'


# ---------- 维度 ----------
DIMS = [('平台', lambda x: PLAT_CN.get(x['slot'], x['slot'])), ('栏目', lambda x: x['tags'].get('column') or '未标'),
        ('发布时段', lambda x: f"{x['hour']}点"), ('形式', lambda x: x['form']), ('视频时长', lambda x: x['len'] or None),
        ('钩子类型', lambda x: x['tags'].get('hook_type')), ('标题特征', lambda x: x['title_feat']),
        ('系列', lambda x: '系列' if x['tags'].get('series') or '系列号' in x['title_feat'] else '单条')]


def dims(rows):
    ok = [x for x in rows if not x['fresh']]
    out = []
    for name, key in DIMS:
        groups = {}
        for x in ok:
            k = key(x)
            if k:
                groups.setdefault(k, []).append(x)
        for k, g in groups.items():
            lift, n = summarize(g, 'views_lift')
            er, ne = summarize(g, 'eng_rate')
            b2, nb = summarize(g, 'bounce_2s')
            c5, _ = summarize(g, 'completion_5s')
            out.append({'dim': name, 'value': k, 'n': n, 'lift': lift, 'eng_rate': er, 'n_rate': ne, 'bounce_2s': b2,
                        'completion_5s': c5, 'views_med': st.median([x['views'] for x in g]),
                        'comments': sum(x.get('comments') or 0 for x in g), 'follows': sum(x.get('follows') or 0 for x in g)})
    return out


# ---------- 实验 ----------
def ci_test(raw, metric, better_low):
    """两组差异的 95% 置信区间（Welch 近似，z=1.96）。
    播放倍数这类偏态指标先取对数，区间换算回「B 是 A 的几倍」；比率类直接比均值差（百分点）。
    区间不含 0 才算有差别。顺带按当前波动估算：要测出 2 倍（比率类为相对 50%）差距每组要多少条。"""
    import math
    (a, xa), (b, xb) = sorted(raw.items())
    if len(xa) < 2 or len(xb) < 2:
        return None
    logm = metric == 'views_lift'
    f = (lambda v: math.log(max(v, 1e-3))) if logm else (lambda v: v)
    ya, yb = [f(v) for v in xa], [f(v) for v in xb]
    ma, mb = st.mean(ya), st.mean(yb)
    va, vb = st.variance(ya), st.variance(yb)
    se = math.sqrt(va / len(ya) + vb / len(yb)) or 1e-9
    d = mb - ma
    lo, hi = d - 1.96 * se, d + 1.96 * se
    sig = lo > 0 or hi < 0
    b_better = (d < 0) if better_low else (d > 0)
    best = b if b_better else a
    sd = math.sqrt((va + vb) / 2)
    target = math.log(2) if logm else max(abs((ma + mb) / 2) * 0.5, 1e-9)
    n_need = math.ceil(2 * (1.96 + 0.84) ** 2 * sd * sd / (target * target)) if sd else 0
    if logm:
        txt = lambda v: f'{math.exp(v):.2f}×'
        effect = f'{b} 组是 {a} 组的 {math.exp(d):.2f} 倍'
    else:
        txt = (lambda v: f'{v * 100:+.1f} 个百分点') if metric in RATE_METRICS else (lambda v: f'{v:+.2f}')
        effect = f'{b} 组减 {a} 组 {txt(d)}'
    return {'a': a, 'b': b, 'diff': d, 'lo': lo, 'hi': hi, 'sig': sig, 'best': best, 'effect': effect,
            'lo_txt': txt(lo), 'hi_txt': txt(hi), 'n_need': n_need}


def experiments(rows):
    try:
        exps = json.loads(EXPS.read_text())['experiments']
    except Exception:
        return []
    today = now().date().isoformat()
    out = []
    for e in exps:
        if e.get('status') not in ('running', 'extended'):
            continue
        m, better_low = e['metric'], e.get('direction') == 'down'
        plats = set(e.get('platforms') or [])
        arms, raw = {}, {}
        for a in e['arms']:
            g = [x for x in rows if not x['fresh'] and (x['tags'].get('exp') or {}).get(e['id']) == a
                 and (not plats or x['slot'] in plats or x['slot'].split('_')[0] in plats)]
            v, n = summarize(g, m)
            sec = {s: summarize(g, s)[0] for s in e.get('secondary', [])}
            arms[a] = {'n': n, 'tagged': len(g), 'value': v, 'secondary': sec}
            raw[a] = [val(x, m) for x in g if val(x, m) is not None]
        due = e.get('review', '9') <= today
        enough = all(arms[a]['n'] >= e.get('min_n', 4) for a in arms)
        verdict = '进行中'
        test = ci_test(raw, m, better_low) if len(raw) == 2 else None
        if enough and test:
            if test['sig']:
                verdict = (f"{test['best']} 组更好（{test['effect']}，95% 区间 {test['lo_txt']}～{test['hi_txt']}，不含 0），建议采纳 {test['best']}")
            else:
                verdict = (f"两组差别在误差范围内（{test['effect']}，95% 区间 {test['lo_txt']}～{test['hi_txt']} 跨过 0），"
                           f"算没差别，选更省事的做法后结束；照现在的波动，要测出 2 倍差距每组约需 {test['n_need']} 条")
            if not due:
                verdict = '样本已够，可提前判：' + verdict
        elif enough:
            verdict = '样本数够了但数值不全，没法算置信区间，检查数据回流'
        elif due:
            verdict = '到期但样本不够（' + '，'.join(f'{a}组 {arms[a]["n"]}/{e.get("min_n", 4)}' for a in arms) + '），建议 status=extended、复查日往后挪 3–4 天，并检查制作时有没有写 exp 标签'
        out.append({'id': e['id'], 'title': e['title'], 'metric': m, 'direction': e.get('direction'), 'review': e.get('review'),
                    'due': due, 'arms': arms, 'ci': test, 'verdict': verdict})
    return out


# ---------- 粉丝 ----------
def fans():
    names = {}
    for k, a in SCHED['accounts'].items():  # 同一账号多个 slot（如公众号贴图）只取第一个，名字用主号的
        names.setdefault(a['account_id'], (k, a['platform'], a['name']))
    hist = []
    if FANS_H.exists():
        for ln in FANS_H.read_text().splitlines():
            try:
                hist.append(json.loads(ln))
            except Exception:
                pass
    if not hist:
        cur = ROOT / 'state/fans.json'
        if cur.exists():
            hist = [{'day': now().date().isoformat(), 'fans': json.loads(cur.read_text())}]
    if not hist:
        return []
    by_day = {}
    for h in hist:
        by_day[h['day']] = h['fans']  # 同一天取最后一次
    days = sorted(by_day)
    last = by_day[days[-1]]

    def ago(n):
        target = (dt.date.fromisoformat(days[-1]) - dt.timedelta(days=n)).isoformat()
        prior = [d for d in days if d <= target]
        return by_day[prior[-1]] if prior else None
    d1, d7 = ago(1), ago(7)
    out = []
    for aid, n in last.items():
        slot, plat, name = names.get(aid, ('?', '?', aid))
        out.append({'slot': slot, 'platform': plat, 'name': name, 'fans': n,
                    'd1': (n - d1[aid]) if d1 and aid in d1 and n is not None and d1[aid] is not None else None,
                    'd7': (n - d7[aid]) if d7 and aid in d7 and n is not None and d7[aid] is not None else None})
    return out


# ---------- 运营计划里到复查日的调整 ----------
def adjustments_due():
    if not PLAN.exists():
        return []
    today = now().date()
    out = []
    for ln in PLAN.read_text().splitlines():
        m = re.match(r'\|\s*(A-\d+)\s*\|', ln)
        if not m:
            continue
        cells = [c.strip() for c in ln.strip('|').split('|')]
        md = re.search(r'(\d{1,2})-(\d{1,2})', cells[-1])
        if md:
            d = dt.date(today.year, int(md.group(1)), int(md.group(2)))
            if d <= today:
                out.append({'id': m.group(1), 'adjust': cells[2][:60], 'check': cells[-1]})
    return out


# ---------- 数据质量 ----------
def quality(rows, items):
    q = []
    starts = [dt.datetime.fromisoformat(it['due']).timestamp() for it in items if it.get('due')]
    t0 = min(starts) - 3600 if starts else 0
    ok = [x for x in rows if not x['fresh'] and x['created'] >= t0]  # 台账建立之前的老作品本来就对不上，不算
    if ok:
        unmatched = sum(1 for x in ok if not x['item'])
        if unmatched:
            q.append(f'{unmatched}/{len(ok)} 条作品数据对不上台账（知乎回答、标题改过的会这样），这些作品没有栏目/实验标签')
        untagged = sum(1 for x in ok if x['item'] and not x['tags'].get('column'))
        if untagged:
            q.append(f'{untagged} 条台账作品没写 column 栏目')
    recent = [it for it in items if it['day'] >= (now().date() - dt.timedelta(days=1)).isoformat()]
    if recent and not any(it['tags'].get('exp') for it in recent):
        q.append('最近两天的台账条目都没写 "exp" 实验标签：实验没法评估，制作时按 playbook.py start 打印的分组写进 post*.json')
    return q


# ---------- 建议 ----------
def suggestions(dm, exps, fz, adj, med, rows):
    s = []
    for d in dm:
        if d['dim'] == '平台' or d['n'] < MIN_DIM_N or d['lift'] is None:
            continue
        if d['lift'] >= 1.5:
            s.append(f"加码：{d['dim']}「{d['value']}」相对播放中位 {d['lift']:.2f}×（{d['n']} 条）")
        elif d['lift'] <= 0.6:
            s.append(f"减少或改写：{d['dim']}「{d['value']}」相对播放中位 {d['lift']:.2f}×（{d['n']} 条）")
    dy = [x for x in rows if x['slot'] == 'douyin' and not x['fresh'] and x.get('bounce_2s') is not None]
    if dy:
        b = st.mean(x['bounce_2s'] for x in dy)
        s.append(f'抖音 2 秒跳出均值 {b:.0%}（{len(dy)} 条可算）：' + ('达到 A-001 目标 ≤30%' if b <= 0.30 else '没达到 A-001 目标 ≤30%，继续按开头三段结构改'))
    elif any(x['slot'] == 'douyin' for x in rows):
        s.append(f'抖音作品播放都不到 {MIN_VIEWS_SCRIPT}，属于分发不足，不做开头/脚本归因，先看播放有没有起来')
    if 'channels' in med and 'douyin' in med and med['channels'] >= 10 * med['douyin']:
        s.append(f"视频号播放中位 {med['channels']:.0f} 是抖音 {med['douyin']:.0f} 的 10 倍以上：平台分发问题，保持 A-002（视频先保视频号）")
    for f in fz:
        if f['d1'] == 0 and f['d7'] is not None and f['d7'] <= 0:
            s.append(f"{f['platform']}「{f['name']}」7 天没涨粉：检查主页简介/置顶/系列入口有没有给关注理由")
    for e in exps:
        if e['due'] or '提前判' in e['verdict']:
            s.append(f"实验 {e['id']}「{e['title']}」：{e['verdict']}")
    for a in adj:
        s.append(f"调整 {a['id']} 到复查日（{a['check']}）：对照上面的数据判断，达标就写进专题手册转成长期规则，没达标就改写或撤回")
    return s


# ---------- 输出 ----------
def table(head, rows):
    return ['|' + '|'.join(head) + '|', '|' + '---|' * len(head)] + ['|' + '|'.join(map(str, r)) + '|' for r in rows]


def render(title, R, extra=None):
    L = [f'# {title}（{now():%m-%d %H:%M} 生成）', '',
         f"窗口：近 {R['window_days']} 天发布的作品 {R['n_posts']} 条（满 24 小时 {R['n_eligible']} 条，对上台账 {R['n_matched']} 条）。数据源：创作者中心快照。", '']
    L += ['## 建议（给日报/周进化决定，不会自动生效）', '']
    L += [f'- {x}' for x in R['suggestions']] or ['- 样本还不够下任何结论，照当前计划执行']
    if R['quality']:
        L += ['', '## 数据质量', ''] + [f'- {x}' for x in R['quality']]
    L += ['', '## 粉丝', ''] + table(['平台', '账号', '粉丝', '较昨天', '较 7 天前'],
                                    [[f['platform'], f['name'], f['fans'], '—' if f['d1'] is None else f"{f['d1']:+d}",
                                      '—' if f['d7'] is None else f"{f['d7']:+d}"] for f in R['fans']])
    L += ['', '## 实验', '']
    for e in R['experiments']:
        L += [f"**{e['id']} {e['title']}**（指标 {e['metric']}，{'越低越好' if e['direction'] == 'down' else '越高越好'}，复查 {e['review']}）：{e['verdict']}", '']
        L += table(['组', '有标签作品', '可算样本', '指标', '辅助指标'],
                   [[a, v['tagged'], v['n'], fmt(v['value'], e['metric']), '；'.join(f'{k} {fmt(sv, k)}' for k, sv in v['secondary'].items())]
                    for a, v in e['arms'].items()]) + ['']
    if R['adjustments_due']:
        L += ['## 到复查日的调整', ''] + [f"- {a['id']}：{a['adjust']}（{a['check']}）" for a in R['adjustments_due']] + ['']
    L += ['## 各维度相对表现（相对本平台播放中位数的倍数；比率只算播放 ≥50 的作品）', '']
    cur = None
    for d in sorted(R['dims'], key=lambda d: ([n for n, _ in DIMS].index(d['dim']), -(d['lift'] or 0))):
        if d['dim'] != cur:
            cur = d['dim']
            L += ['', f'### {cur}', ''] + table(['分组', '条数', '相对播放', '播放中位', '互动率', '2秒跳出', '5秒完播', '评论', '涨粉'], [])
        L.append(f"|{d['value']}|{d['n']}|{fmt(d['lift'], 'views_lift')}|{d['views_med']:.0f}|{fmt(d['eng_rate'], 'eng_rate')}|"
                 f"{fmt(d['bounce_2s'], 'bounce_2s')}|{fmt(d['completion_5s'], 'completion_5s')}|{d['comments']}|{d['follows']}|")
    if extra:
        L += [''] + extra
    return '\n'.join(L) + '\n'


def analyze(days):
    rows = metrics.latest(days)
    items = ledger_items((now().date() - dt.timedelta(days=days + 1)).isoformat())
    rows = match(rows, items)
    rows, med = enrich(rows)
    dm = dims(rows)
    ex = experiments(rows)
    fz = fans()
    adj = adjustments_due()
    R = {'generated': now().isoformat(timespec='seconds'), 'window_days': days, 'n_posts': len(rows),
         'n_eligible': sum(1 for x in rows if not x['fresh']), 'n_matched': sum(1 for x in rows if x['item']),
         'platform_baseline': {PLAT_CN.get(k, k): v for k, v in med.items()}, 'dims': dm, 'experiments': ex, 'fans': fz,
         'adjustments_due': adj, 'quality': quality(rows, items)}
    R['suggestions'] = suggestions(dm, ex, fz, adj, med, rows)
    return R, rows


def write(name, R, md):
    d = ROOT / 'days' / now().date().isoformat()
    d.mkdir(parents=True, exist_ok=True)
    (d / f'{name}.json').write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
    (d / f'{name}.md').write_text(md)
    print(md)
    print('->', d / f'{name}.md')


def weekly():
    R, rows = analyze(14)
    cut = now().timestamp() - 7 * 86400
    cur = [x for x in rows if x['created'] >= cut and not x['fresh']]
    prev = [x for x in rows if x['created'] < cut]
    extra = ['## 本周 vs 上周（按平台）', '']
    tr = []
    for slot in sorted({x['slot'] for x in rows}):
        a = [x['views'] for x in cur if x['slot'] == slot]
        b = [x['views'] for x in prev if x['slot'] == slot]
        tr.append([PLAT_CN.get(slot, slot), len(a), f'{st.median(a):.0f}' if a else '—', len(b), f'{st.median(b):.0f}' if b else '—',
                   sum(x.get('comments') or 0 for x in cur if x['slot'] == slot), sum(x.get('follows') or 0 for x in cur if x['slot'] == slot)])
    extra += table(['平台', '本周条数', '本周播放中位', '上周条数', '上周播放中位', '本周评论', '本周涨粉'], tr)
    cols = [d for d in R['dims'] if d['dim'] == '栏目' and d['value'] != '未标' and d['n'] >= MIN_DIM_N and d['lift'] is not None]
    extra += ['', '## 时段配比建议（内容总纲第 9 节：最差栏目减一个时段，最好栏目加一个）', '']
    if len(cols) >= 2:
        best = max(cols, key=lambda d: d['lift'])
        worst = min(cols, key=lambda d: d['lift'])
        extra += [f"- 最好：「{best['value']}」{best['lift']:.2f}×（{best['n']} 条）→ 下周加一个时段",
                  f"- 最差：「{worst['value']}」{worst['lift']:.2f}×（{worst['n']} 条）→ 下周减一个时段"]
    else:
        extra += ['- 有栏目标签且满 3 条的栏目不到 2 个，本周不调配比（先保证每条都写 column）']
    R['weekly'] = {'platform_trend': tr}
    write('evolve-weekly', R, render('周进化分析', R, extra))


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else 'daily'
    if cmd == 'daily':
        R, _ = analyze(7)
        write('evolve', R, render('每日进化分析', R))
    elif cmd == 'weekly':
        weekly()
    elif cmd == 'exp':
        R, _ = analyze(14)
        for e in R['experiments']:
            print(e['id'], e['title'], '→', e['verdict'])
            for k, v in e['arms'].items():
                print(f"   {k}组 有标签 {v['tagged']} 可算 {v['n']} 指标 {fmt(v['value'], e['metric'])}")
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
