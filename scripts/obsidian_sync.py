#!/usr/bin/env python3
"""Incrementally sync approved Markdown into a local vault; never overwrite user edits."""
import argparse
import fcntl
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

def digest(data):
    return hashlib.sha256(data.encode()).hexdigest()

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.sync-tmp')
    tmp.write_text(data, encoding='utf-8')
    tmp.replace(path)

def run(root, config):
    root = root.resolve()
    cfg = json.loads(config.read_text())
    registry = Path(cfg['registry']).expanduser()
    vault = Path(json.loads(registry.read_text())['vaults'][cfg['vault_id']]['path'])
    if not vault.is_dir() or not (vault / '.obsidian').is_dir():
        raise ValueError('Configured vault is not available')
    target = vault / cfg.get('folder', '矩阵运营')
    if not target.resolve().is_relative_to(vault.resolve()):
        raise ValueError('Invalid destination')
    state = root / 'state/obsidian-sync'
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'sync.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'status': 'busy'}
        manifest_path = state / 'manifest.json'
        old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        if old.get('target') and old['target'] != str(target):
            raise ValueError('Vault moved; review destination before resetting manifest')
        mapping = {}
        for item in cfg['sources']:
            base = root / item['from']
            for pattern in item.get('patterns', ['**/*.md']):
                for src in sorted(base.glob(pattern)):
                    if src.suffix != '.md' or src.is_symlink() or not src.is_file():
                        continue
                    if not src.resolve().is_relative_to(root.resolve()):
                        raise ValueError('Source outside workspace')
                    rel = Path(item['to']) / src.relative_to(base)
                    if rel.is_absolute() or '..' in rel.parts:
                        raise ValueError('Invalid output path')
                    mapping[src.resolve()] = rel
        # Credential values are read only for redaction, never copied or logged.
        secrets = []
        envfile = root / 'config/.env'
        if envfile.exists():
            for line in envfile.read_text().splitlines():
                key, sep, val = line.partition('=')
                val = val.strip().strip('\"\'')
                if sep and re.search('KEY|TOKEN|PASSWORD|SECRET', key, re.I) and len(val) >= 8:
                    secrets.append(val)
        expected = {}
        for src, rel in mapping.items():
            content = src.read_text(encoding='utf-8')
            for secret in sorted(secrets, key=len, reverse=True):
                content = content.replace(secret, '[凭据已省略]')
            def link(m):
                raw = m.group(2).strip('<>')
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', raw) or raw.startswith('#'):
                    return m.group(0)
                filepart, _, anchor = unquote(raw).partition('#')
                resolved = (src.parent / filepart).resolve()
                if resolved in mapping:
                    return '[[' + (Path(cfg.get('folder', '矩阵运营')) / mapping[resolved]).with_suffix('').as_posix() + ('#' + anchor if anchor else '') + '|' + m.group(1) + ']]'
                if resolved.exists():
                    return '[' + m.group(1) + '](' + resolved.as_uri() + ('#' + anchor if anchor else '') + ')'
                return m.group(0)
            content = re.sub(r'(?<!!)\[([^\]\n]+)\]\(([^)\n]+)\)', link, content)
            # Wiki aliases contain a pipe, which must be escaped inside Markdown tables.
            content = '\n'.join(re.sub(r'\[\[([^\]\n]+)\]\]', lambda m: '[[' + re.sub(r'(?<!\\)\|', r'\\|', m.group(1)) + ']]', line) if line.lstrip().startswith('|') else line for line in content.split('\n'))
            existing = ''
            if content.startswith('---\n') and '\n---\n' in content[4:]:
                existing, content = content[4:].split('\n---\n', 1)
                existing = re.sub(r'^(source|source_modified|sync_managed):.*\n?', '', existing, flags=re.M)
            properties = (existing.rstrip() + '\n' if existing else '')
            if not re.search(r'^cssclasses:', properties, re.M):
                properties += 'cssclasses: [kb-note]\n'
            properties += ('source: ' + json.dumps(str(src.relative_to(root)), ensure_ascii=False)
                           + '\nsource_modified: ' + json.dumps(datetime.fromtimestamp(src.stat().st_mtime, timezone.utc).isoformat())
                           + '\nsync_managed: true\n')
            note = '\n\n> [!info]- 来源与同步说明\n> 源文件：`' + str(src.relative_to(root)) + '`。此页为同步副本；批注放「我的笔记」。历史记录不代表当前状态。\n'
            expected[rel.as_posix()] = '---\n' + properties + '---\n\n' + content.strip() + note
        links = ['---', 'cssclasses: [kb-hub]', '---', '# 原始资料索引', '',
                 '> [!info] 查做法先读知识卡，追溯证据再读原文', '']
        navigation = []
        for rel, label in [('00-导航与方法/07-知识卡片库.md', '知识卡片库'), ('00-导航与方法/00-知识库首页.md', '首页')]:
            if rel in expected:
                navigation.append('[' + label + '](' + rel + ')')
        if navigation:
            links += [' · '.join(navigation), '']
        groups = {}
        for rel in sorted(expected):
            groups.setdefault(Path(rel).parts[0], []).append(rel)
        for group, paths in groups.items():
            links += ['## ' + group, '']
            for rel in paths:
                links.append('- [[' + (Path(cfg.get('folder', '矩阵运营')) / rel).with_suffix('').as_posix() + '|' + Path(rel).stem + ']]')
            links.append('')
        expected['全库索引.md'] = '\n'.join(links) + '\n'
        hashes = dict(old.get('files', {}))
        conflicts, changed = [], []
        for rel, data in expected.items():
            dest = target / rel
            if not dest.resolve().is_relative_to(target.resolve()) or dest.is_symlink():
                raise ValueError('Unsafe destination link')
            current = digest(dest.read_text()) if dest.exists() else None
            new = digest(data)
            if current == new:
                hashes[rel] = new
                continue
            if current is not None and current != hashes.get(rel):
                conflicts.append(rel)
                write(state / 'incoming' / rel, data)
                continue
            write(dest, data)
            hashes[rel] = new
            changed.append(rel)
        stale = sorted(set(hashes) - set(expected))
        result = {'status': 'conflict' if conflicts else 'ok', 'at': datetime.now(timezone.utc).isoformat(),
                  'target': str(target), 'total': len(expected), 'changed': len(changed),
                  'conflicts': conflicts, 'retained_removed_sources': stale}
        write(manifest_path, json.dumps({'target': str(target), 'files': hashes}, ensure_ascii=False, indent=2))
        write(state / 'last-sync.json', json.dumps(result, ensure_ascii=False, indent=2))
        return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'config/obsidian-sync.json')
    args = parser.parse_args()
    if not args.config.exists():
        print(json.dumps({'status': 'not_configured'}))
        return
    result = run(ROOT, args.config)
    print(json.dumps(result, ensure_ascii=False))
    if result['status'] == 'conflict':
        raise SystemExit(2)

if __name__ == '__main__':
    main()
