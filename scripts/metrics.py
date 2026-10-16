#!/usr/bin/env python3
"""作品数据回流：各平台创作者中心的真实数据 → 快照库 → 复盘结论。

为什么要它：蚁小二的作品数据同步慢（10-16 看到 10-15 晚上的作品还没进来），复盘没有数据可用。
创作者中心（内置浏览器已登录）能拿到完播率、2 秒跳出率、涨粉、主页访问这些真正决定推荐的指标。

采集：在对应平台已登录的标签页里，用 javascript_tool 执行 scripts/collectors/<平台>.js，返回 {platform, at, f:[字段], rows:[[...]]}，
      原样存成 days/<日期>/metrics/<平台>-<账号>.json。
用法:
  metrics.py ingest <平台> <账号> <json文件>   入库（同一作品每次采集都是一条快照）
  metrics.py report [天数=7]                     输出最新快照表 + 按栏目/时段/时长汇总 + 诊断，写到 days/<今天>/metrics/report.md
  metrics.py diagnose <平台> <作品id>            单条作品诊断
字段统一：views likes comments favorites shares follows homepage_visits completion completion_5s bounce_2s avg_view_sec avg_view_ratio cover_show
（某平台没有的字段就不出现）
"""
import json, pathlib, sqlite3, sys, datetime as dt
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, TZ, now

DB = ROOT / 'state/metrics.sqlite3'
LEDGER = ROOT / 'state/ops.sqlite3'


def db():
    c = sqlite3.connect(DB)
    c.execute('CREATE TABLE IF NOT EXISTS snaps(platform TEXT, account TEXT, post_id TEXT, title TEXT, created INTEGER, '
              'snap INTEGER, m TEXT, PRIMARY KEY(platform, account, post_id, snap))')
    return c


def ingest(platform, account, path):
    d = json.loads(pathlib.Path(path).read_text())
    if isinstance(d, str):  # javascript_tool 有时返回被引号包住的字符串
        d = json.loads(d)
    f, rows, at = d['f'], d['rows'], int(d.get('at') or now().timestamp())
    c = db()
    n = 0
    for r in rows:
        x = dict(zip(f, r))
        pid = str(x.pop('id') or '')
        if not pid:
            continue
        title, created = x.pop('title', ''), int(x.pop('created', 0) or 0)
        c.execute('INSERT OR REPLACE INTO snaps VALUES(?,?,?,?,?,?,?)', (platform, account, pid, title, created, at, json.dumps(x, ensure_ascii=False)))
        n += 1
    c.commit()
    print(f'ingested {n} posts ({platform}/{account}) @ {dt.datetime.fromtimestamp(at, TZ):%m-%d %H:%M}')


def latest(days):
    c = db()
    since = int((now() - dt.timedelta(days=days)).timestamp())
    q = ('SELECT platform, account, post_id, title, created, snap, m FROM snaps s WHERE created >= ? AND snap = '
         '(SELECT MAX(snap) FROM snaps t WHERE t.platform=s.platform AND t.account=s.account AND t.post_id=s.post_id) ORDER BY created DESC')
    out = []
    for p, a, pid, t, cr, sn, m in c.execute(q, (since,)):
        x = json.loads(m)
        x.update(platform=p, account=a, id=pid, title=t, created=cr, snap=sn)
        out.append(x)
    return out


def ledger_meta():
    """台账里每条作品的栏目、时段、形式：按标题前 12 字匹配（各平台标题可能被截断）。"""
    meta = {}
    if not LEDGER.exists():
        return meta
    c = sqlite3.connect(LEDGER)
    for title, payload, due, ptype in c.execute('SELECT title, payload, due, publish_type FROM items WHERE title IS NOT NULL'):
        col = '未标'
        try:
            pl = pathlib.Path(payload)
            for cand in (pl.with_name(pl.name.replace('.payload.json', '.json')),):
                if cand.exists():
                    col = json.loads(cand.read_text()).get('column') or col
        except Exception:
            pass
        meta[(title or '')[:12]] = {'column': col, 'hour': (due or '')[11:13], 'type': ptype}
    return meta


# ---- 诊断规则：只给能改的动作，阈值来自抖音创作者中心常见基准，样本少时只提示不下结论 ----
def diagnose_one(x):
    tips = []
    v = x.get('views', 0)
    if x.get('bounce_2s', 0) >= 0.35:
        tips.append(f"2秒跳出 {x['bounce_2s']:.0%}：开头太慢。首句直接给结论或数字，前 2 秒画面要有冲突/大字，别放标题页")
    if 0 < x.get('completion_5s', 1) < 0.5:
        tips.append(f"5秒完播 {x['completion_5s']:.0%}：钩子没接住。第 2–5 秒要兑现开头的承诺（给出第一条干货/反转）")
    if x.get('avg_view_ratio', 1) and x.get('avg_view_ratio', 1) < 0.15 and x.get('duration', 0) >= 30:
        tips.append(f"平均只看了 {x['avg_view_ratio']:.0%}：中段流失。每 8–10 秒一个新信息点，删铺垫句")
    if x.get('homepage_visits', 0) >= 3 and x.get('follows', 0) == 0:
        tips.append('有人点进主页但没关注：主页简介/置顶/系列入口要给出关注理由')
    if v >= 200 and (x.get('likes', 0) + x.get('favorites', 0)) / max(v, 1) < 0.01:
        tips.append('互动率 <1%：结尾问题太泛，改成二选一或让人晒自己的情况')
    if v < 50:
        tips.append('播放 <50：还在冷启动，样本不够，先别据此改方向（看 24h 后）')
    return tips


def agg(rows, key):
    g = {}
    for x in rows:
        k = key(x)
        a = g.setdefault(k, {'n': 0, 'views': 0, 'likes': 0, 'favorites': 0, 'comments': 0, 'follows': 0, 'b2': [], 'c5': []})
        a['n'] += 1
        for f in ('views', 'likes', 'favorites', 'comments', 'follows'):
            a[f] += x.get(f, 0) or 0
        if 'bounce_2s' in x:
            a['b2'].append(x['bounce_2s'])
        if 'completion_5s' in x:
            a['c5'].append(x['completion_5s'])
    return g


def report(days=7):
    rows = latest(days)
    meta = ledger_meta()
    for x in rows:
        m = meta.get((x['title'] or '')[:12], {})
        x['column'] = m.get('column', '未标')
        x['hour'] = m.get('hour') or dt.datetime.fromtimestamp(x['created'], TZ).strftime('%H')
        d = x.get('duration', 0)
        x['len'] = '图文' if not d else ('<30s' if d < 30 else '30-90s' if d < 90 else '90s-3m' if d < 180 else '>3m')
    L = [f'# 作品数据复盘（近 {days} 天，{now():%m-%d %H:%M} 生成）', '',
         '数据源：各平台创作者中心（scripts/collectors），比蚁小二同步快且多了完播/跳出/涨粉。', '',
         '|平台|账号|发布|标题|播放|赞|藏|评|涨粉|2秒跳出|5秒完播|均看占比|',
         '|---|---|---|---|---|---|---|---|---|---|---|---|']
    pct = lambda v: f'{v:.0%}' if isinstance(v, (int, float)) else '—'
    for x in rows:
        L.append(f"|{x['platform']}|{x['account']}|{dt.datetime.fromtimestamp(x['created'], TZ):%m-%d %H:%M}|{x['title'][:18]}|"
                 f"{x.get('views', '—')}|{x.get('likes', '—')}|{x.get('favorites', '—')}|{x.get('comments', '—')}|{x.get('follows', '—')}|"
                 f"{pct(x.get('bounce_2s'))}|{pct(x.get('completion_5s'))}|{pct(x.get('avg_view_ratio'))}|")
    for title, key in (('按栏目', lambda x: x['column']), ('按发布时段', lambda x: x['hour'] + '点'), ('按时长/形式', lambda x: x['len'])):
        L += ['', f'## {title}', '', '|分组|条数|均播放|均赞藏|涨粉|均2秒跳出|均5秒完播|', '|---|---|---|---|---|---|---|']
        for k, a in sorted(agg(rows, key).items(), key=lambda kv: -kv[1]['views'] / kv[1]['n']):
            avg = lambda l: f'{sum(l) / len(l):.0%}' if l else '—'
            L.append(f"|{k}|{a['n']}|{a['views'] / a['n']:.0f}|{(a['likes'] + a['favorites']) / a['n']:.1f}|{a['follows']}|{avg(a['b2'])}|{avg(a['c5'])}|")
    L += ['', '## 诊断（每条只列能改的动作）', '']
    for x in rows[:20]:
        tips = diagnose_one(x)
        if tips:
            L.append(f"- **{x['platform']}·{x['title'][:20]}**：" + '；'.join(tips))
    out = ROOT / 'days' / now().date().isoformat() / 'metrics' / 'report.md'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(L) + '\n')
    print('\n'.join(L))
    print('\n->', out)


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return
    if a[0] == 'ingest':
        ingest(a[1], a[2], a[3])
    elif a[0] == 'report':
        report(int(a[1]) if len(a) > 1 else 7)
    elif a[0] == 'diagnose':
        x = next((r for r in latest(90) if r['platform'] == a[1] and r['id'] == a[2]), None)
        print('\n'.join(diagnose_one(x)) if x else '没找到')
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
