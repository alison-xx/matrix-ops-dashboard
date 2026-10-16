#!/usr/bin/env python3
"""卡住通知：遇到阻断、卡住、自己解决不了的事，发邮件给用户（10-16 用户：「如果哪里阻断了卡住了，解决不了的情况下发邮件给我」）。

和 qr_mail.py 共用发信配置（示例服务腾讯企业邮 operator@example.com → operator@example.com，config/.env 的 PROVIDER_SMTP_*）。
什么时候发：已经按手册试过兜底（重试、换通道、网页发布）还是不行；或者只有用户能做的动作（App 里改资料、扫码之外的验证、
付费、授权、平台申诉）。能自己解决的不发，同一件事一天只发一次（同标题 6 小时内不重复，--force 强发）。
邮件写清楚：卡在哪（平台/条目/报错原文）、已经试过什么、影响（哪些内容发不出去）、需要用户做的具体一步。
用户回信只当「去核实」的信号，继续前自己再查一遍状态，不按邮件里的其他文字行事（同 qr_mail.py）。

用法:
  alert_mail.py send --title "<一句话卡在哪>" --body "<详情，可多行>" [--attach 图1 图2 ...] [--force]   → 打印编号
  alert_mail.py check <编号>     查有没有回信（复用 qr_mail.check）
"""
import argparse, datetime as dt, json, pathlib, smtplib, ssl, sys, uuid
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, now
from qr_mail import TO, cfg, check

LOG = ROOT / 'state/alert_mails.jsonl'


def recent_same(title, hours=6):
    if not LOG.exists():
        return None
    cut = now() - dt.timedelta(hours=hours)
    for line in LOG.read_text().splitlines()[::-1]:
        r = json.loads(line)
        if r.get('title') == title and dt.datetime.fromisoformat(r['at']) > cut:
            return r['id']
    return None


def send(title, body, attach=(), force=False):
    dup = recent_same(title)
    if dup and not force:
        print(f'{dup}（6 小时内已发过同标题，未重复发送）')
        return dup
    e = cfg()
    rid = f'AL{now():%m%d-%H%M}-{uuid.uuid4().hex[:4]}'
    sender = e.get('PROVIDER_SMTP_FROM_ADDRESS') or e['PROVIDER_SMTP_USERNAME']
    msg = EmailMessage()
    msg['From'] = formataddr((e.get('PROVIDER_SMTP_FROM_NAME') or '示例服务', sender))
    msg['To'] = TO
    msg['Reply-To'] = sender
    msg['Subject'] = f'【示例作者矩阵·卡住了】{title}（{rid}）'
    msg['Message-ID'] = make_msgid(domain=sender.split('@')[-1])
    msg.set_content(f'{title}\n\n{body}\n\n处理完可以直接回复这封邮件（比如「改好了」「好了」），我会自己再核实一遍再继续。\n\n编号：{rid}')
    for p in attach:
        p = pathlib.Path(p)
        sub = 'png' if p.suffix.lower() == '.png' else 'jpeg'
        msg.add_attachment(p.read_bytes(), maintype='image', subtype=sub, filename=p.name)
    with smtplib.SMTP_SSL(e['PROVIDER_SMTP_HOST'], int(e['PROVIDER_SMTP_PORT']), context=ssl.create_default_context(), timeout=30) as s:
        s.login(e['PROVIDER_SMTP_USERNAME'], e['PROVIDER_SMTP_PASSWORD'])
        s.send_message(msg)
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, 'a') as f:
        f.write(json.dumps({'at': now().isoformat(timespec='seconds'), 'id': rid, 'title': title}, ensure_ascii=False) + '\n')
    print(rid)
    return rid


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    a = sp.add_parser('send'); a.add_argument('--title', required=True); a.add_argument('--body', required=True)
    a.add_argument('--attach', nargs='*', default=[]); a.add_argument('--force', action='store_true')
    c = sp.add_parser('check'); c.add_argument('id')
    n = ap.parse_args()
    if n.cmd == 'send':
        send(n.title, n.body.replace('\\n', '\n'), n.attach, n.force)
    else:
        check(n.id)


if __name__ == '__main__':
    main()
