#!/usr/bin/env python3
"""把审核后的发布稿、视频和封面发给运营者；邮件交付不等于平台已发布。

用法：publication_mail.py <post.json> --id <台账id> [--send]
默认只生成邮件预览。--send发送并登记manual_pending；SMTP结果不明不自动重发。
视频较大时上传至已配置的素材存储，在邮件中给出下载地址。
"""
import argparse
import hashlib
import json
import mimetypes
import pathlib
import smtplib
import sqlite3
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from common import ROOT, now, yxer
from qr_mail import TO, cfg

MAX_ATTACHMENT_BYTES = 16 * 1024 * 1024


def load_package(path):
    path = pathlib.Path(path).resolve()
    post = json.loads(path.read_text())
    if not post.get('title') or not post.get('description'):
        raise ValueError('缺少标题或正文')
    assets = []
    for key in ('video', 'cover'):
        if not post.get(key):
            raise ValueError(f'缺少{key}')
        p = pathlib.Path(post[key])
        if not p.is_absolute():
            p = path.parent / p
        if not p.is_file():
            raise ValueError(f'素材不存在：{p}')
        assets.append(p)
    # 平台竖封面优先；另附已存在的横封面，方便运营者选择。
    stem = assets[1].stem
    for suffix in ('-34', '-169'):
        p = assets[1].with_name(stem + suffix + assets[1].suffix)
        if p.is_file() and p not in assets:
            assets.append(p)
    h = hashlib.sha256(json.dumps(post, sort_keys=True, ensure_ascii=False).encode())
    for p in assets:
        h.update(p.name.encode())
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return post, assets, h.hexdigest()


def delivery_db(path=None):
    path = pathlib.Path(path or ROOT / 'state/publication-mail.sqlite3')
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute('CREATE TABLE IF NOT EXISTS deliveries(item TEXT, recipient TEXT, revision TEXT, '
              'state TEXT, message_id TEXT, at TEXT, PRIMARY KEY(item,recipient,revision))')
    c.commit()
    return c


def reserve(c, item, recipient, revision, message_id):
    cur = c.execute('INSERT OR IGNORE INTO deliveries VALUES(?,?,?,?,?,?)',
                    (item, recipient, revision, 'sending', message_id, now().isoformat()))
    c.commit()
    return cur.rowcount == 1


def build_message(post, assets, recipient, sender, item, links=None):
    links = links or {}
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = f'【视频号待你发布】{post["title"]}'
    msg['Message-ID'] = make_msgid(domain=sender.split('@')[-1])
    copy = f'标题：{post["title"]}\n\n正文 / 简介：\n{post["description"]}\n'
    if post.get('tags'):
        copy += '\n话题：' + ' '.join(post['tags']) + '\n'
    copy += '\n材料准备时间：' + str(post.get('day') or '见素材文件日期') + '\n'
    body = ('这是一份视频号待发布材料包，尚未代你在平台发表。\n'
            '请先核对作品列表没有同题已发布、审核中或定时作品，再手动上传。\n'
            '旧排期时间不再用于定时；若已错过，可核对内容时效后立即发表。\n\n' + copy +
            '\n视频、封面和可复制文案见附件。发出后请回复作品链接，以便登记实际公开结果。\n'
            f'\n材料编号：{item}\n')
    for name, url in links.items():
        body += f'\n大文件下载（请先下载保存）：{name}\n{url}\n'
    msg.set_content(body)
    msg.add_attachment(copy.encode('utf-8'), maintype='text', subtype='plain', filename='发布文案.txt')
    for p in assets:
        if p.name in links:
            continue
        main, sub = (mimetypes.guess_type(p.name)[0] or 'application/octet-stream').split('/', 1)
        msg.add_attachment(p.read_bytes(), maintype=main, subtype=sub, filename=p.name)
    return msg


def register_manual(path, item, receipt):
    import ops
    post = json.loads(pathlib.Path(path).read_text())
    c = ops.connect()
    try:
        old = c.execute('SELECT status FROM items WHERE id=?', (item,)).fetchone()
        if old and old['status'] == 'manual_pending':
            return
        if old and old['status'] not in ('draft', 'blocked', 'ready'):
            raise ValueError('已有平台发布状态，不能覆盖为待手动发布')
        ops.register_web(c, item, 'channels', post.get('time', '00:00'), path,
                         f'材料邮件SMTP已接受；待本人手动发布；回执{receipt}', 'manual_pending')
        c.execute("UPDATE items SET mode='email' WHERE id=?", (item,))
    finally:
        c.close()


def send(path, item):
    from ops import video_gate
    post, assets, revision = load_package(path)
    # 邮件交付也不能跳过成片声音质检。
    qc = video_gate(pathlib.Path(path).resolve())
    if not qc or not qc.get('ok'):
        raise ValueError('声音质检缺失或未通过，不能交付发布材料')
    c = delivery_db()
    try:
        old = c.execute('SELECT * FROM deliveries WHERE item=? AND recipient=? AND revision=?',
                        (item, TO, revision)).fetchone()
        if old:
            if old['state'] == 'sent':
                register_manual(path, item, old['message_id'])
            return {'state': old['state'], 'duplicate': True, 'message_id': old['message_id']}
        e = cfg()
        sender = e.get('PROVIDER_SMTP_FROM_ADDRESS') or e['PROVIDER_SMTP_USERNAME']
        links, total = {}, sum(p.stat().st_size for p in assets)
        if total > MAX_ATTACHMENT_BYTES:
            # 只将超限的大视频转为下载链接，封面和文案仍直接附件交付。
            p = assets[0]
            rc, result = yxer('upload', str(p), timeout=300)
            if rc or not result.get('ok') or not (result.get('data') or {}).get('key'):
                raise ValueError('大文件素材上传失败，未发送不完整邮件')
            from oss_url import BASE
            links[p.name] = BASE + result['data']['key']
            if sum(p.stat().st_size for p in assets if p.name not in links) > MAX_ATTACHMENT_BYTES:
                raise ValueError('封面附件仍超限，未发送不完整邮件')
        msg = build_message(post, assets, TO, sender, item, links)
        msg.replace_header('From', formataddr((e.get('PROVIDER_SMTP_FROM_NAME') or '运营材料', sender)))
        with smtplib.SMTP_SSL(e['PROVIDER_SMTP_HOST'], int(e['PROVIDER_SMTP_PORT']),
                              context=ssl.create_default_context(), timeout=90) as smtp:
            smtp.login(e['PROVIDER_SMTP_USERNAME'], e['PROVIDER_SMTP_PASSWORD'])
            if not reserve(c, item, TO, revision, msg['Message-ID']):
                return {'state': 'existing', 'duplicate': True}
            rejected = smtp.send_message(msg)
            if rejected:
                raise RuntimeError('SMTP拒收；保留sending记录待核实，不自动重发')
            c.execute("UPDATE deliveries SET state='sent',at=? WHERE item=? AND recipient=? AND revision=?",
                      (now().isoformat(), item, TO, revision))
            c.commit()
        register_manual(path, item, msg['Message-ID'])
        return {'state': 'sent', 'message_id': msg['Message-ID'], 'attachments':
                [p.name for p in assets if p.name not in links], 'downloads': list(links)}
    finally:
        c.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('post')
    ap.add_argument('--id', required=True)
    ap.add_argument('--send', action='store_true')
    n = ap.parse_args()
    if n.send:
        print(json.dumps(send(n.post, n.id), ensure_ascii=False))
    else:
        post, assets, revision = load_package(n.post)
        print(json.dumps({'title': post['title'], 'assets': [str(p) for p in assets],
                          'revision': revision, 'sent': False}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
