#!/usr/bin/env python3
"""Queue changed evidence for Agent distillation; validate cards and build native Markdown indexes."""
import argparse
import fcntl
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TZ = timezone(timedelta(hours=8))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def metadata(path):
    text = path.read_text(encoding='utf-8')
    if not text.startswith('---\n') or '\n---\n' not in text[4:]:
        raise ValueError(str(path) + ': missing frontmatter')
    head, body = text[4:].split('\n---\n', 1)
    data, current = {}, None
    for line in head.splitlines():
        if re.match(r'^\s*- ', line) and current:
            data.setdefault(current, []).append(line.strip()[2:].strip().strip('\"\''))
        elif re.match(r'^[\w-]+:', line):
            key, value = line.split(':', 1)
            value = value.strip()
            current = key
            if not value:
                data[key] = []
            else:
                try:
                    data[key] = json.loads(value)
                except ValueError:
                    data[key] = value.strip('\"\'')
    return data, body

def sources(root):
    for base in ('days', 'reports'):
        for path in sorted((root / base).rglob('*')):
            rel = path.relative_to(root)
            if not path.is_file() or (path.suffix != '.md' and not (path.suffix == '.json' and re.search(r'result|verification|evidence|acceptance|summary|验证', path.name, re.I))):
                continue
            if any(part in {'raw', 'node_modules', '.git', 'source', 'sources', 'evidence-raw'} for part in rel.parts):
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                continue
            if base == 'reports' or re.search(r'test|notes|review|report|learning|复盘|结果|踩坑|实测|验收|总结|diagnosis|result|verification|evidence|acceptance|summary|验证', str(rel), re.I):
                yield path

def scan(root):
    state = root / 'state/knowledge-cards'
    state.mkdir(parents=True, exist_ok=True)
    handled = json.loads((state / 'reviewed.json').read_text()) if (state / 'reviewed.json').exists() else {}
    pending = []
    for path in sources(root):
        rel = path.relative_to(root).as_posix()
        h = sha(path)
        if handled.get(rel, {}).get('sha256') != h:
            pending.append({'path': rel, 'sha256': h, 'bytes': path.stat().st_size})
    pending.sort(key=lambda x: x['path'], reverse=True)
    result = {'scanned_at': datetime.now(TZ).isoformat(), 'pending': pending}
    (state / 'queue.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result

def cards(root):
    result, errors, ids = [], [], set()
    for path in sorted((root / 'knowledge-cards').glob('*.md')):
        try:
            data, body = metadata(path)
            for key in ('id', 'type', 'status', 'created', 'updated', 'tags', 'source_files'):
                if not data.get(key):
                    raise ValueError('missing ' + key)
            if data['id'] in ids:
                raise ValueError('duplicate id ' + data['id'])
            ids.add(data['id'])
            if data['type'] not in ('实测', '踩坑', '复盘') or data['status'] not in ('已验证', '局部验证', '待验证', '已过时'):
                raise ValueError('invalid type/status')
            if not isinstance(data['source_files'], list) or not isinstance(data['tags'], list):
                raise ValueError('source_files and tags must be lists')
            for rel in data['source_files']:
                source = (root / rel).resolve()
                if not source.is_relative_to(root.resolve()) or not source.is_file():
                    raise ValueError('missing or external evidence ' + rel)
            for section in ('适用场景', '发生了什么', '可复用做法', '边界与反例', '来源与证据', '复查触发'):
                if section not in body:
                    raise ValueError('missing section ' + section)
            if len(body) < 350:
                raise ValueError('card too short to preserve evidence and limits')
            result.append((path, data, body))
        except (ValueError, TypeError) as error:
            errors.append(str(path.relative_to(root)) + ': ' + str(error))
    return result, errors

def build(root):
    items, errors = cards(root)
    if errors:
        raise ValueError('\n'.join(errors))
    state = root / 'state/knowledge-cards'
    state.mkdir(parents=True, exist_ok=True)
    evidence_path = state / 'card-evidence.json'
    evidence = json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    stale = []
    for path, data, _ in items:
        current = {rel: sha(root / rel) for rel in data['source_files']}
        previous = evidence.get(data['id'])
        if previous and previous['sources'] != current and previous['card_hash'] == sha(path):
            stale.append(data['id'])
        else:
            evidence[data['id']] = {'sources': current, 'card_hash': sha(path)}
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    out = root / 'knowledge-base'
    out.mkdir(exist_ok=True)
    def link(path):
        return '[' + path.stem + '](../knowledge-cards/' + path.name + ')'
    lines = ['---', 'cssclasses: [kb-hub]', 'tags: [知识库/导航]', '---', '# 知识卡片库', '',
             '> [!abstract] 从问题找到经验', '> 每张卡只解决一个问题，保留做法、证据和适用边界。来源更新时列入待复查，不自动把旧结论升级。', '',
             '| 实测 | 踩坑 | 复盘 | 待验证或来源变化 |', '|---|---|---|---|',
             '| ' + ' | '.join(str(sum(d['type'] == t for _, d, _ in items)) for t in ('实测', '踩坑', '复盘')) + ' | ' + str(sum(d['status'] == '待验证' or d['id'] in stale for _, d, _ in items)) + ' |', '']
    for kind in ('实测', '踩坑', '复盘'):
        lines += ['## ' + kind, '', '| 知识卡 | 可信范围 | 更新 |', '|---|---|---|']
        for path, data, _ in items:
            if data['type'] == kind:
                lines.append('| ' + link(path) + ' | ' + ('来源变化，待复查' if data['id'] in stale else data['status']) + ' | ' + str(data['updated']) + ' |')
        lines.append('')
    lines += ['## 按主题找', '']
    tags = sorted({tag for _, data, _ in items for tag in data['tags']})
    for tag in tags:
        lines += ['### ' + tag, ''] + ['- ' + link(path) for path, data, _ in items if tag in data['tags']] + ['']
    lines += ['## 待复查', '']
    waiting = [(p, d) for p, d, _ in items if d['id'] in stale or d['status'] in ('待验证', '局部验证')]
    lines += ['- ' + link(p) + '：' + ('来源已变化' if d['id'] in stale else d['status']) for p, d in waiting] or ['暂无。']
    lines += ['', '[回到知识库首页](00-知识库首页.md) · [提炼与维护规则](../运营手册/知识卡片提炼.md)', '']
    text = '\n'.join(lines)
    dest = out / '07-知识卡片库.md'
    if not dest.exists() or dest.read_text() != text:
        dest.write_text(text)
    daily = ['---', 'cssclasses: [kb-hub]', 'tags: [知识库/日志]', '---', '# 每日知识日志', '',
             '> [!abstract] 看每天真正学到了什么', '> 日志记录新增经验、修订和待验证，不重复粘贴原始操作流水。', '']
    for note in sorted((out / '每日').glob('*.md'), reverse=True):
        daily.append('- [' + note.stem + '](每日/' + note.name + ')')
    daily += ['', '[知识卡片库](07-知识卡片库.md) · [回到首页](00-知识库首页.md)', '']
    dest = out / '08-每日知识日志.md'
    text = '\n'.join(daily)
    if not dest.exists() or dest.read_text() != text:
        dest.write_text(text)
    result = {'cards': len(items), 'stale': stale, 'errors': errors}
    (state / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result

def review(root, path):
    # Agent writes this receipt only after reading and making a disposition for each source.
    receipt = json.loads(path.read_text())
    state = root / 'state/knowledge-cards'
    state.mkdir(parents=True, exist_ok=True)
    target = state / 'reviewed.json'
    handled = json.loads(target.read_text()) if target.exists() else {}
    valid, errors = cards(root)
    if errors:
        raise ValueError('\n'.join(errors))
    known = {d['id']: d for _, d, _ in valid}
    updates = {}
    for item in receipt:
        rel = item['path']
        src = (root / rel).resolve()
        if not src.is_relative_to(root.resolve()) or sha(src) != item['sha256']:
            raise ValueError('Source changed since review: ' + rel)
        if item.get('disposition') not in ('提炼', '合并', '无新增知识') or not item.get('reason'):
            raise ValueError('A disposition and reason are required')
        if item['disposition'] != '无新增知识':
            if not item.get('cards') or any(c not in known or rel not in known[c]['source_files'] for c in item['cards']):
                raise ValueError('Card must exist and cite source: ' + rel)
        updates[rel] = dict(item, reviewed_at=datetime.now(TZ).isoformat())
    handled.update(updates)
    target.write_text(json.dumps(handled, ensure_ascii=False, indent=2) + '\n')
    return {'reviewed': len(updates)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['scan', 'build', 'review'])
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    state = ROOT / 'state/knowledge-cards'
    state.mkdir(parents=True, exist_ok=True)
    lock = (state / 'process.lock').open('w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(json.dumps({'status': 'busy'}))
        raise SystemExit(3)
    if args.command == 'scan':
        result = scan(ROOT)
        print(json.dumps({'pending': len(result['pending']), 'queue': 'state/knowledge-cards/queue.json'}, ensure_ascii=False))
    elif args.command == 'build':
        print(json.dumps(build(ROOT), ensure_ascii=False))
    else:
        if not args.receipt:
            parser.error('--receipt required')
        print(json.dumps(review(ROOT, args.receipt), ensure_ascii=False))

if __name__ == '__main__':
    main()
