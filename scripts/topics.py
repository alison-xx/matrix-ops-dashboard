#!/usr/bin/env python3
"""选题库：常青选题 + 本周素材，批次按栏目/平台取题，用过的打标记，避免重复。

存储：state/topics.json（列表）。字段：
  id, title(草拟标题), column(先试/算账/抄作业/热点), crowd(人群), platforms[slot...], angle(示例作者的观点/内容要点),
  source(链接，可空), expires(YYYY-MM-DD，可空=常青), score(0-12 打分卡), status(new/used/dropped), used[], added
用法:
  topics.py list [--column 抄作业] [--platform xhs] [--fresh] [--n 20]
  topics.py add --title .. --column .. [--crowd ..] [--platforms xhs,douyin] [--angle ..] [--source ..] [--expires ..] [--score 8]
  topics.py use <id> <条目id>        # 标记已用（同一题可在不同平台用，换角度）
  topics.py drop <id> [原因]
  topics.py import <file.json>       # 批量导入 [{title,column,...}]
  topics.py series <系列名>                 # 看下一集编号（不占号）
  topics.py series <系列名> --take <条目id>  # 占号：发布时用，记录哪条用了第几集
"""
import argparse, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, now

DB = ROOT / 'state/topics.json'
COLUMNS = ('先试', '算账', '抄作业', '热点')


def load():
    return json.loads(DB.read_text()) if DB.exists() else []


def save(rows):
    DB.write_text(json.dumps(rows, ensure_ascii=False, indent=1))


def next_id(rows):
    return f"T{max([int(r['id'][1:]) for r in rows] or [0]) + 1:03d}"


def norm(r):
    col = r.get('column', '')
    if col not in COLUMNS:
        raise ValueError(f'column 必须是 {COLUMNS}：{r.get("title")}')
    pl = r.get('platforms') or []
    if isinstance(pl, str):
        pl = [x.strip() for x in pl.split(',') if x.strip()]
    return {'title': r['title'].strip(), 'column': col, 'crowd': r.get('crowd', ''), 'platforms': pl, 'angle': r.get('angle', ''),
            'source': r.get('source', ''), 'expires': r.get('expires') or '', 'score': int(r.get('score') or 0),
            'status': 'new', 'used': [], 'added': now().date().isoformat()}


def add_rows(rows, new):
    seen = {r['title'] for r in rows}
    n = 0
    for x in new:
        x = norm(x)
        if x['title'] in seen:
            continue
        x['id'] = next_id(rows)
        rows.append(x)
        seen.add(x['title'])
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    l = sub.add_parser('list')
    l.add_argument('--column'); l.add_argument('--platform'); l.add_argument('--fresh', action='store_true'); l.add_argument('--n', type=int, default=20)
    a = sub.add_parser('add')
    for k in ('title', 'column', 'crowd', 'platforms', 'angle', 'source', 'expires'):
        a.add_argument('--' + k, required=k in ('title', 'column'))
    a.add_argument('--score', type=int, default=0)
    u = sub.add_parser('use'); u.add_argument('id'); u.add_argument('item')
    d = sub.add_parser('drop'); d.add_argument('id'); d.add_argument('reason', nargs='?', default='')
    im = sub.add_parser('import'); im.add_argument('file')
    se = sub.add_parser('series'); se.add_argument('name'); se.add_argument('--take')
    x = ap.parse_args()
    if x.cmd == 'series':
        sp = ROOT / 'state/series.json'
        ser = json.loads(sp.read_text()) if sp.exists() else {}
        cur = ser.setdefault(x.name, {'next': 1, 'items': {}})
        if x.take:
            if x.take in cur['items']:  # 同一条目重复占号，返回原编号
                print(cur['items'][x.take]); return
            cur['items'][x.take] = cur['next']
            cur['next'] += 1
            sp.write_text(json.dumps(ser, ensure_ascii=False, indent=1))
            print(cur['items'][x.take])
        else:
            print(cur['next'])
        return
    rows = load()
    today = now().date().isoformat()
    if x.cmd == 'list':
        out = []
        for r in rows:
            if r['status'] == 'dropped' or (r['expires'] and r['expires'] < today):
                continue
            if x.column and r['column'] != x.column:
                continue
            if x.platform and r['platforms'] and x.platform not in r['platforms']:
                continue
            if x.fresh and r['status'] == 'used':
                continue
            out.append(r)
        # 快过期的时效题优先，其次分数
        out.sort(key=lambda r: (0 if r['expires'] else 1, r['expires'] or '9999', -r['score']))
        for r in out[:x.n]:
            used = f" 用过:{','.join(r['used'])}" if r['used'] else ''
            exp = f" 截止{r['expires']}" if r['expires'] else ''
            print(f"{r['id']} [{r['column']}] {r['score']}分{exp} {r['title']} ｜{r['crowd']}｜{','.join(r['platforms'])}｜{r['angle']}{used}")
        print(f'-- 共 {len(out)} 条可用（显示 {min(len(out), x.n)}）')
    elif x.cmd == 'add':
        n = add_rows(rows, [vars(x)])
        save(rows)
        print(f'added {n}: {rows[-1]["id"] if n else "(重复标题，未加)"}')
    elif x.cmd == 'import':
        n = add_rows(rows, json.loads(pathlib.Path(x.file).read_text()))
        save(rows)
        print(f'imported {n}, total {len(rows)}')
    else:
        r = next((r for r in rows if r['id'] == x.id), None)
        if not r:
            raise SystemExit(f'no topic {x.id}')
        if x.cmd == 'use':
            r['status'] = 'used'
            r['used'].append(x.item)
        else:
            r['status'] = 'dropped'
            r['drop_reason'] = x.reason
        save(rows)
        print('ok', r['id'], r['status'])


if __name__ == '__main__':
    main()
