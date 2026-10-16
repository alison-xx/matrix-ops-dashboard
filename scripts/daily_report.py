#!/usr/bin/env python3
"""日报：台账里的发布结果 + 蚁小二作品数据 + 账号粉丝，输出 reports/<day>.md。
用法: .venv/bin/python scripts/daily_report.py [YYYY-MM-DD] [--force]（已补写过复盘的日报默认不覆盖，另存 .regen.md）
"""
import datetime as dt, json, pathlib, re, sqlite3, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, TZ, now, yxer

args = [a for a in sys.argv[1:] if not a.startswith('--')]
day = args[0] if args else now().date().isoformat()
db = sqlite3.connect(ROOT / 'state/ops.sqlite3')
db.row_factory = sqlite3.Row
items = db.execute('SELECT * FROM items WHERE day=? ORDER BY due', (day,)).fetchall()

# 作品数据（近 3 天发布的）
start = int(dt.datetime.fromisoformat(day + 'T00:00:00').replace(tzinfo=TZ).timestamp() * 1000) - 2 * 86400000
end = int(dt.datetime.fromisoformat(day + 'T23:59:59').replace(tzinfo=TZ).timestamp() * 1000)
works = []
for page in range(1, 6):
    rc, o = yxer('query', 'content-overviews', '--publish-start-time', str(start), '--publish-end-time', str(end), '--size', '50', '--page', str(page))
    data = (o.get('data') or {})
    rows = data.get('data') if isinstance(data, dict) else data
    if not rows:
        break
    works += rows
    if len(rows) < 50:
        break

rc, acc = yxer('accounts', 'list')
fans = {a['id']: (a['platformName'], a['platformAccountName'].replace('&nbsp;', ' '), a.get('fansTotal')) for a in (acc.get('data') or [])}
prev_p = ROOT / 'state/fans.json'
prev = json.loads(prev_p.read_text()) if prev_p.exists() else {}

L = [f'# 示例作者 AI 矩阵日报 · {day}', '', f'生成时间：{now():%Y-%m-%d %H:%M}', '']
L += ['## 今日发布', '', '|时间|平台|标题|状态|链接|', '|---|---|---|---|---|']
SCHED = json.loads((ROOT / 'config/schedule.json').read_text())


def plat_label(r):
    """同平台第二个号（schedule 里带 base 的）标出账号名，免得和示例作者的号混在一起。"""
    a = SCHED['accounts'].get(r['slot'] or '', {})
    return f"{r['platform']}·{a['name']}" if a.get('base') else r['platform']


for r in items:
    L.append(f"|{r['due'][11:16]}|{plat_label(r)}|{(r['title'] or '')[:28]}|{r['status']}|{r['url'] or '—'}|")
if not items:
    L.append('|—|—|台账无记录|—|—|')
za = ROOT / 'days' / day / 'zhihu-answers.md'  # 浏览器发布的知乎回答（不经蚁小二，不在台账里）
if za.exists():
    for line in za.read_text().splitlines():
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) >= 4 and re.match(r'\d{2}:\d{2}', cells[0]):
            L.append(f"|{cells[0]}|知乎（回答）|{cells[1][:28]}|public|{cells[3]}|")

L += ['', '## 作品数据（蚁小二同步，近3天发布）', '', '|发布时间|平台|标题|阅读/播放|赞|评|藏|转|', '|---|---|---|---|---|---|---|---|']
for w in sorted(works, key=lambda x: (x.get('contentData') or {}).get('date', ''), reverse=True):
    cd = w.get('contentData') or {}
    name = fans.get(w.get('platformAccountId'), ('?',))[0]
    L.append(f"|{cd.get('date', '')[5:16]}|{name}|{(cd.get('title') or cd.get('desc') or '')[:26]}|{cd.get('read') or cd.get('play') or '—'}|{cd.get('great', '—')}|{cd.get('comment', '—')}|{cd.get('collect', '—')}|{cd.get('share', '—')}|")
L += ['', '注：蚁小二作品数据非实时，空值表示未同步，不代表 0。', '']

# 创作者中心数据回流（运营手册/数据回流.md）：比蚁小二快、多了完播/跳出/涨粉。先跑 metrics.py report 生成当天 report.md
mr = ROOT / 'days' / day / 'metrics' / 'report.md'
if mr.exists():
    body = mr.read_text().split('\n', 2)[-1]  # 去掉 report.md 自己的一级标题
    L += ['## 创作者中心数据（各平台后台直取）', '', body.replace('\n## ', '\n### '), '']
else:
    L += ['## 创作者中心数据', '', '今天没有采集（按 运营手册/数据回流.md 采集后再生成日报）。', '']


def column_of(r):
    """台账条目 -> post.json 里的栏目。"""
    try:
        pl = pathlib.Path(r['payload'])
        post = pl.with_name(pl.name.replace('.payload.json', '.json'))
        return json.loads(post.read_text()).get('column') or '未标'
    except Exception:
        return '未标'


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# 栏目 × 平台表现（按标题把作品数据和台账对上；近 7 天台账）
since = (dt.datetime.fromisoformat(day) - dt.timedelta(days=6)).date().isoformat()
led = db.execute('SELECT * FROM items WHERE day>=? AND day<=?', (since, day)).fetchall()
col_by_title = {(r['title'] or '')[:14]: (column_of(r), r['platform']) for r in led if r['title']}
agg = {}
for w in works:
    cd = w.get('contentData') or {}
    key = (cd.get('title') or cd.get('desc') or '')[:14]
    if key not in col_by_title:
        continue
    col, plat = col_by_title[key]
    a = agg.setdefault((col, plat), {'n': 0, 'read': 0, 'great': 0, 'comment': 0, 'collect': 0})
    a['n'] += 1
    a['read'] += num(cd.get('read') or cd.get('play')) or 0
    for k in ('great', 'comment', 'collect'):
        a[k] += num(cd.get(k)) or 0
if agg:
    L += ['## 栏目 × 平台（近 3 天有数据的作品，均值）', '', '|栏目|平台|条数|阅读/播放|赞|评|藏|', '|---|---|---|---|---|---|---|']
    for (col, plat), a in sorted(agg.items(), key=lambda kv: -kv[1]['read'] / kv[1]['n']):
        n = a['n']
        L.append(f"|{col}|{plat}|{n}|{a['read']/n:.0f}|{a['great']/n:.1f}|{a['comment']/n:.1f}|{a['collect']/n:.1f}|")
    L += ['', '小号阶段看比值：评论、收藏比点赞重要，点赞比播放重要。周日按这张表调整下周时段配比（内容总纲第 9 节）。', '']

L += ['## 粉丝', '', '|平台|账号|粉丝|较上次|', '|---|---|---|---|']
for k, (p, n, f) in fans.items():
    d = '' if prev.get(k) is None or f is None else f'{f - prev[k]:+d}'
    L.append(f'|{p}|{n}|{f}|{d}|')
prev_p.write_text(json.dumps({k: v[2] for k, v in fans.items()}))
# 粉丝历史（evolve.py 和工作台算涨粉趋势用）：每次生成日报追加一行，同一天多行时以最后一行为准
with open(ROOT / 'state/fans_history.jsonl', 'a') as fh:
    fh.write(json.dumps({'at': now().isoformat(timespec='seconds'), 'day': day, 'fans': {k: v[2] for k, v in fans.items()}}, ensure_ascii=False) + '\n')

PLACEHOLDER = '（由运营 Agent 根据以上数据补写：哪条表现最好/最差、原因假设、明天怎么改）'
L += ['', '## 复盘与次日调整', '', PLACEHOLDER, '']
out = ROOT / 'reports' / f'{day}.md'
out.parent.mkdir(exist_ok=True)
# 已经补写过复盘/更正的日报不能被重跑覆盖（10-16 出过一次）：另存 .regen.md，让人手动合并
if out.exists() and PLACEHOLDER not in out.read_text() and '--force' not in sys.argv:
    out = out.with_name(f'{day}.regen.md')
    print('⚠️ 原日报已有人工补写内容，新数据另存为', out, file=sys.stderr)
out.write_text('\n'.join(L))
print(out)
