#!/usr/bin/env python3
"""完整自然日运营报告及邮件。默认昨日；不采集/发布、不改粉丝历史。

report_mail.py [YYYY-MM-DD]              生成 reports/<日期>.full.md
report_mail.py [YYYY-MM-DD] --send       发到 config/report-mail.json 指定邮箱
回执不确定时保留 sending，先查发件箱，禁止盲目重发。
"""
import argparse
from collections import Counter
import datetime as dt
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
import html
import importlib.util
import json
import re
from pathlib import Path
import smtplib
import sqlite3
import ssl
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from common import TZ, now


def day_window(day):
    start = dt.datetime.combine(dt.date.fromisoformat(day), dt.time(), TZ)
    return start, start + dt.timedelta(days=1)


def delivery_db(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path, timeout=15)
    columns = [r[1] for r in c.execute('PRAGMA table_info(deliveries)')]
    if columns and 'revision' not in columns:
        with c:
            c.execute('ALTER TABLE deliveries RENAME TO deliveries_v1')
            c.execute('CREATE TABLE deliveries (day TEXT, recipient TEXT, revision TEXT, state TEXT, at TEXT, message_id TEXT, PRIMARY KEY(day, recipient, revision))')
            c.execute("INSERT INTO deliveries SELECT day, recipient, 'v1', state, at, message_id FROM deliveries_v1")
    else:
        c.execute('CREATE TABLE IF NOT EXISTS deliveries (day TEXT, recipient TEXT, revision TEXT, state TEXT, at TEXT, message_id TEXT, PRIMARY KEY(day, recipient, revision))')
    return c


def reserve(c, day, recipient, revision='html-final'):
    with c:
        return c.execute('INSERT OR IGNORE INTO deliveries VALUES (?, ?, ?, ?, ?, ?)',
                         (day, recipient, revision, 'sending', now().isoformat(), '')).rowcount == 1


def cell(value):
    return str(value if value is not None else '—').replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')


def table(head, rows):
    return ['|' + '|'.join(head) + '|', '|' + '|'.join(['---'] * len(head)) + '|'] + [
        '|' + '|'.join(cell(v) for v in row) + '|' for row in rows]


def generate(day, root=ROOT):
    start, end = day_window(day)
    if end > now():
        raise ValueError('完整日报只能生成已经结束的自然日')
    spec = importlib.util.spec_from_file_location('report_dashboard', root / 'dashboard/server.py')
    s = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(s)
    s.configure(root)
    accounts = s.load_accounts()
    accmap = {a['slot']: a for a in accounts}
    # 台账是核心证据；缺失或损坏时直接失败，不能生成虚假的零发布报告。
    all_rows = s.enrich_items(s.ledger_rows(), accmap)
    since = s.ledger_since(all_rows)
    rows = [i for i in all_rows if i.get('day') == day]
    urls = {i.get('url') for i in rows if i.get('url')}
    answers = [a for a in s.zhihu_answers(day) if a.get('url') not in urls]
    all_items = rows + answers
    active = [i for i in all_items if i.get('bucket') != 'muted' and not i.get('superseded_by') and not i.get('resolved_note')]
    states = Counter(i['bucket'] for i in active)
    verified = sum(i.get('status') in ('public', 'web') and bool(i.get('url')) for i in active)
    L = [f'# 示例作者矩阵全天运营报告 · {day}', '', f'生成时间：{now():%Y-%m-%d %H:%M}（北京时间）',
         f'统计窗口：{day} 00:00–24:00（Asia/Shanghai，含全部晚间任务）。', '',
         '口径：摘要仅统计已接入台账的记录；旧流程覆盖不足时见原复盘，不把台账条数当作平台全天总量。发布按当天台账归属日统计，状态截至报告生成时；平台成功不等于已核验公开，定时到点仍待核实。多次尝试保留明细，已替代/撤销的记录不计完成。作品指标是累计快照，不能当作当日新增播放。', '',
         '## 一天概况', '',
         f'- 平台报成功/网页发表 {states["done"]} 条，其中核验公开且有链接 {verified} 条。',
         f'- 排队 {states["queue"]} 条，失败/阻断 {states["fail"]} 条，待核实 {states["warn"]} 条。',
         f'- 全量发布记录 {len(all_items)} 条（包含重试、撤销和单独登记的知乎回答）。', '',
         '## 各账号完成情况', '按账号首次台账日期起算；当前排期配置仅供对照，历史日配额若曾调整，以当日手册为准。', '']
    L += table(['平台/账号', '应发', '平台成功', '待发', '失败', '待核实'], [
        [a['platform'] + ' / ' + a['name'], s.expected_since(a, day, since)] + [sum(i.get('slot') == a['slot'] and i['bucket'] == b for i in active) for b in ('done', 'queue', 'fail', 'warn')] for a in accounts])
    L += ['', '## 全天发布明细', '']
    L += table(['时间', '平台/账号', '标题', '结果', '链接'], [
        [i.get('time'), i.get('platform_name', '') + ' / ' + (i.get('account_name') or ''), i.get('title'),
         i.get('status_label', i.get('status')) + ('（已被替代）' if i.get('superseded_by') else ''), i.get('url') or '待回收']
        for i in sorted(all_items, key=lambda i: i.get('time') or '')])
    problems = [i for i in active if i['bucket'] in ('warn', 'fail') or i.get('flag')]
    L += ['', '## 异常与待处理', '这里反映台账待核对项，不等于平台未发出；若原复盘含后续核验更正，以更正为准，先回填台账，禁止据旧状态补发。', '']
    L += table(['条目', '状态', '原因/下一步'], [[i.get('title'), i.get('status_label'), i.get('detail_text') or (i.get('reason') or {}).get('hint') or '去平台核实后更新状态，禁止直接重发'] for i in problems]) if problems else ['台账内没有未解决的发布异常。平台审核、公开可见性仍以逐条回读为准。']
    L += ['', '## 作品表现', '仅选当天发布、且在当天结束前采集到的最后一次累计快照；次日采集值不回填成昨日增长。', '']
    try:
        c = s.ro_db(s.METRICS_DB)
        try:
            stats = c.execute('SELECT * FROM snaps WHERE created>=? AND created<? AND snap<? ORDER BY snap', (start.timestamp(), end.timestamp(), end.timestamp())).fetchall()
        finally:
            c.close()
        latest = {(r['platform'], r['account'], r['post_id']): r for r in stats}
        data = []
        for r in latest.values():
            m = json.loads(r['m'] or '{}')
            data.append([r['platform'], r['title'], m.get('views'), m.get('likes'), m.get('comments'), m.get('favorites'), dt.datetime.fromtimestamp(r['snap'], TZ).strftime('%H:%M')])
        L += table(['平台', '作品', '累计播放/阅读', '赞', '评', '藏', '采集时间'], data) if data else ['没有符合窗口的作品快照；缺失不代表 0。']
    except (OSError, sqlite3.Error, ValueError):
        L += ['作品数据源读取失败，本节缺失，不计作 0。']
    L += ['', '## 粉丝变化', '']
    hist = s.read_jsonl(root / 'state/fans_history.jsonl')
    def fan_day(d):
        pts = [r for r in hist if r.get('day') == d and (s.parse_dt(r.get('at')) and s.parse_dt(r['at']) < end)]
        return max(pts, key=lambda r: r.get('at', '')) if pts else None
    current = fan_day(day)
    prev = fan_day((start.date() - dt.timedelta(days=1)).isoformat())
    seen = set()
    fan_rows = []
    for a in accounts:
        aid = a.get('account_id')
        if not aid or aid in seen:
            continue
        seen.add(aid)
        v = (current or {}).get('fans', {}).get(aid)
        old = (prev or {}).get('fans', {}).get(aid)
        fan_rows.append([a['platform'], a['name'], v, f'{v-old:+}' if isinstance(v, (float, int)) and isinstance(old, (float, int)) else '缺少可比采集'])
    L += table(['平台', '账号', '当日最后采集粉丝', '较前一日最后采集'], fan_rows)
    L += ['未用今天的粉丝数冒充昨天；缺少当天记录时保留缺失。', '', '## 全天互动', '']
    engagement = s.engagement_payload(day)
    L += table(['平台', '动作', '次数'], [[p['platform_name'], a['label'], a['used']] for p in engagement['platforms'] for a in p['actions'] if a['used']])
    records = s.read_jsonl(root / 'days' / day / 'engagement.jsonl')
    L += ['', f'互动合计 {len(records)} 次；完整流水如下。' if (root / 'days' / day / 'engagement.jsonl').exists() else '当日没有互动采集文件，缺失不代表0。', '']
    L += table(['时间', '平台', '动作', '目标', '文字/备注'], [[r.get('time'), r.get('platform'), r.get('action'), r.get('target'), r.get('text') or r.get('note')] for r in records])
    L += ['', '## 任务运行与热点', '']
    runs = s.runs_payload(only_day=day)
    L += table(['任务', '开工', '收工', '结果'], [[r['task'], r.get('start'), r.get('end') or '无收工记录', r.get('summary')] for r in runs])
    radar = s.radar_runs(day)
    L += ['', f'热点雷达记录 {len(radar)} 轮；未选中热点不等于任务失败。', '']
    for label, rel in [('热点决策记录', f'days/{day}/hot-log.md'), ('数据进化与建议', f'days/{day}/evolve.md'), ('晚间复盘（保留原文及其统计口径）', f'reports/{day}.md')]:
        p = root / rel
        if p.is_file():
            text = p.read_text(encoding='utf-8')
            if label.startswith('晚间'):
                # 不发送未补写的占位语作为结论。
                text = text.replace('（由运营 Agent 根据以上数据补写：哪条表现最好/最差、原因假设、明天怎么改）', '复盘未补齐，待运营任务核实。')
            L += [f'## {label}', '', re.sub(r'^(#+)(?= )', lambda m: '#' * max(3, len(m.group(1)) + 1), text, flags=re.M), '']
    L += ['## 数据边界与下一步', '', '未接入的成本、收入、私信与平台指标不作推测。优先核实未确认的发布与缺失采集，再按已有复盘执行次日调整。', '']
    out = root / 'reports' / f'{day}.full.md'
    out.parent.mkdir(exist_ok=True)
    out.write_text('\n'.join(L), encoding='utf-8')
    return out


def send(day, path, recipient, site_url):
    from qr_mail import cfg
    e = cfg()
    sender = e.get('PROVIDER_SMTP_FROM_ADDRESS') or e['PROVIDER_SMTP_USERNAME']
    msg = EmailMessage()
    msg['From'] = formataddr((e.get('PROVIDER_SMTP_FROM_NAME') or '运营日报', sender))
    msg['To'] = recipient
    msg['Subject'] = f'【运营日报】{day} 全天运营报告 · HTML版'
    msg['Message-ID'] = make_msgid(domain=sender.split('@')[-1])
    text = path.read_text(encoding='utf-8')
    msg.set_content(text + f'\n在线阅读：{site_url.rstrip("/")}/#/reports/{day}\n')
    from report_email_layout import build_email
    body = build_email(text, day, site_url)
    msg.add_alternative(body, subtype='html')
    msg.add_attachment(text.encode('utf-8'), maintype='text', subtype='markdown', filename=f'运营报告-{day}.md')
    c = delivery_db(ROOT / 'state/report-mail.sqlite3')
    try:
        with smtplib.SMTP_SSL(e['PROVIDER_SMTP_HOST'], int(e['PROVIDER_SMTP_PORT']), context=ssl.create_default_context(), timeout=30) as smtp:
            smtp.login(e['PROVIDER_SMTP_USERNAME'], e['PROVIDER_SMTP_PASSWORD'])
            # 连接/登录成功才占位；提交后断连等不确定状态不得自动重发。
            if not reserve(c, day, recipient):
                state = c.execute('SELECT state FROM deliveries WHERE day=? AND recipient=? AND revision=?', (day, recipient, 'html-final')).fetchone()[0]
                print(f'{day} 已有发信记录（{state}），未重复发送')
                return
            c.execute('UPDATE deliveries SET message_id=? WHERE day=? AND recipient=? AND revision=?', (msg['Message-ID'], day, recipient, 'html-final')); c.commit()
            rejected = smtp.send_message(msg)
            if rejected:
                raise RuntimeError('收件人被 SMTP 拒收，保留记录供核查')
            c.execute("UPDATE deliveries SET state='sent', at=? WHERE day=? AND recipient=? AND revision=?", (now().isoformat(), day, recipient, 'html-final')); c.commit()
            print(f'{day} SMTP 已接收报告，回执已登记')
    finally:
        c.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('day', nargs='?', default=(now().date() - dt.timedelta(days=1)).isoformat())
    ap.add_argument('--send', action='store_true')
    args = ap.parse_args()
    path = generate(args.day)
    print(path)
    if args.send:
        conf = json.loads((ROOT / 'config/report-mail.json').read_text())
        send(args.day, path, conf['to'], conf.get('site_url', ''))


if __name__ == '__main__':
    main()
