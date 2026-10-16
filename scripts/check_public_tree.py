#!/usr/bin/env python3
"""Scan tracked/public files without echoing matched sensitive values."""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RULES = {
    'personal-home-path': re.compile(r'/(?:Users|home)/[A-Za-z][\w.-]+/'),
    'private-key': re.compile(r'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----'),
    'github-token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b'),
    'api-key': re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
    'jwt': re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'),
    'email': re.compile(r'[\w.+-]+@(?!example\.com\b)[A-Za-z][\w.-]*\.[A-Za-z]{2,}'),
}
BINARY = {'.png', '.jpg', '.jpeg', '.svg', '.ttf', '.otf', '.woff2'}


def main():
    result = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT, capture_output=True, check=True)
    paths = sorted(set(result.stdout.decode().strip('\x00').split('\x00')))
    issues = []
    for rel in paths:
        if not rel:
            continue
        p = ROOT / rel
        if not p.exists():
            continue
        if p.is_symlink():
            issues.append((rel, 'symlink'))
            continue
        parts = pathlib.PurePosixPath(rel).parts
        if parts[0] in {'state', 'days', 'reports', 'assets'} or p.name == '.env' or p.suffix in {'.sqlite3', '.db', '.pem', '.key', '.mp4', '.wav', '.mp3'}:
            issues.append((rel, 'private-data-or-media'))
        # Third-party copyright emails are retained in unmodified license texts.
        is_license = 'license' in p.name.lower() or p.name.lower().startswith('ofl-')
        if p.suffix in BINARY and p.suffix != '.svg':
            continue
        try:
            text = p.read_text(encoding='utf-8')
        except UnicodeError:
            issues.append((rel, 'unapproved-binary'))
            continue
        for name, rx in RULES.items():
            if name == 'email' and is_license:
                continue
            if rx.search(text):
                issues.append((rel, name))
    for rel, category in issues:
        print(f'{rel}: {category}')
    print(f'Public tree scan: {len(paths)} files, {len(issues)} issues')
    return bool(issues)


if __name__ == '__main__':
    sys.exit(main())
