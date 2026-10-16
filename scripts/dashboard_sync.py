#!/usr/bin/env python3
"""把本地工作台的代码和数据同步到远程站点（ip.provider.cn），每小时由 launchd 跑一次。

    .venv/bin/python scripts/dashboard_sync.py            # 同步一次
    .venv/bin/python scripts/dashboard_sync.py --dry-run  # 只列出会传什么
    .venv/bin/python scripts/dashboard_sync.py --code     # 只同步代码（改了 dashboard/ 之后）

连接参数在 config/dashboard-remote.json（host、user、key、app_dir、data_dir）。
只传看板需要的东西：
- 代码：dashboard/（不含示例数据）
- 数据：sqlite 用 backup API 做一致性快照再传（库是 WAL 模式，直接拷文件可能缺最近的写入）；
  粉丝、配置子集、运营手册、日报、days/ 下的 json/md/图片（最近 N 天的视频）；
  scripts/engage.py、metrics.py、common.py（看板读上限、做诊断用，common.py 只在调用时才读 .env）。
- 永远不传：config/.env、登录二维码截图（login-qr）、发布回执（receipts）、渲染缓存（*_hf、src）。
远端的鉴权配置（允许登录的账号）只放在服务器上，本脚本不碰。
"""
import datetime as dt
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG_PATH = ROOT / 'config/dashboard-remote.json'
STAGE = Path.home() / '.cache/creator-dashboard-sync'
LOG = ROOT / 'state/dashboard-sync.log'
TZ = dt.timezone(dt.timedelta(hours=8))

DAY_FILTER = [
    '- /test/', '- *_hf/', '- src/', '- login-qr/', '- receipts/', '- *-raw.png', '- *.prompt.json', '- *.log',
    '- *login-qr*', '- *登录二维码*', '- *qrcode*', '- *-qr.png', '- *-qr-*.png', '- *扫码*',  # 任何登录二维码截图都不出本机
]
DATA_EXT = ['*.json', '*.jsonl', '*.md', '*.jpg', '*.jpeg', '*.png', '*.webp', '*.gif']


def log(msg):
    line = f'{dt.datetime.now(TZ).strftime("%m-%d %H:%M:%S")} {msg}'
    print(line, flush=True)
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def cfg():
    c = json.loads(CFG_PATH.read_text(encoding='utf-8'))
    c.setdefault('port', 22)
    c.setdefault('video_days', 3)
    c.setdefault('keep_days', 45)
    c['key'] = str(Path(c['key']).expanduser())
    return c


def ssh_cmd(c):
    return ['ssh', '-i', c['key'], '-p', str(c['port']), '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20',
            '-o', 'ServerAliveInterval=15', '-o', 'StrictHostKeyChecking=yes']


def rsync(c, src, dst, filters=(), delete=True, dry=False, extra=()):
    cmd = ['rsync', '-az', '--partial', '--timeout=300', '-e', ' '.join(ssh_cmd(c))]
    if delete:
        cmd += ['--delete', '--delete-excluded']
    if dry:
        cmd += ['--dry-run', '--itemize-changes']
    for f in filters:  # macOS 自带 openrsync：用 --include/--exclude，规则按顺序先匹配先生效
        kind, pat = f.split(' ', 1)
        cmd.append(('--exclude=' if kind == '-' else '--include=') + pat)
    s = str(src)
    if Path(src).is_dir():
        s = s.rstrip('/') + '/'  # 带斜杠 = 同步目录里的内容，不是目录本身
    cmd += list(extra) + [s, f'{c["user"]}@{c["host"]}:{dst}']
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=3600)
    if r.returncode != 0:
        raise RuntimeError(f'rsync {src} → {dst} 失败（{r.returncode}）：{r.stderr.strip()[-400:]}')
    return r.stdout


def snapshot_state(stage):
    """sqlite 一致性快照 + 粉丝和配置文件（保留修改时间，看板用它判断数据新鲜度）。"""
    st = stage / 'state'
    st.mkdir(parents=True, exist_ok=True)
    for name in ('ops.sqlite3', 'metrics.sqlite3'):
        src = ROOT / 'state' / name
        if not src.exists():
            continue
        tmp = st / (name + '.tmp')
        tmp.unlink(missing_ok=True)
        s = sqlite3.connect(f'file:{src}?mode=ro', uri=True, timeout=10)
        d = sqlite3.connect(tmp)
        with d:
            s.backup(d)
        # 快照会继承源库的 WAL 模式；WAL 库在只读挂载上打不开（要建 -shm/-wal），转回普通模式
        d.execute('PRAGMA journal_mode=DELETE')
        s.close()
        d.close()
        os.replace(tmp, st / name)
    for name in ('fans.json', 'fans_history.jsonl'):
        if (ROOT / 'state' / name).exists():
            shutil.copy2(ROOT / 'state' / name, st / name)
    cf = stage / 'config'
    cf.mkdir(exist_ok=True)
    for name in ('schedule.json', 'experiments.json', 'dashboard.json'):
        if (ROOT / 'config' / name).exists():
            shutil.copy2(ROOT / 'config' / name, cf / name)
    sc = stage / 'scripts'
    sc.mkdir(exist_ok=True)
    for name in ('engage.py', 'metrics.py', 'common.py'):
        if (ROOT / 'scripts' / name).exists():
            shutil.copy2(ROOT / 'scripts' / name, sc / name)


def day_filters(c):
    today = dt.datetime.now(TZ).date()
    keep = {(today - dt.timedelta(days=i)).isoformat() for i in range(c['keep_days'])}
    video = [(today - dt.timedelta(days=i)).isoformat() for i in range(c['video_days'])]
    f = list(DAY_FILTER)
    # 只保留最近 keep_days 天的日期目录；其他目录（如 _covers）照常
    for p in sorted((ROOT / 'days').iterdir()):
        if p.is_dir() and len(p.name) == 10 and p.name[4] == '-' and p.name not in keep:
            f.append(f'- /{p.name}/')
    f += [f'+ /{d}/**.mp4' for d in video]
    f += ['+ */'] + [f'+ {e}' for e in DATA_EXT] + ['- *']
    return f


def main():
    dry = '--dry-run' in sys.argv
    code_only = '--code' in sys.argv
    if not CFG_PATH.exists():
        sys.exit(f'缺少 {CFG_PATH}（host、user、key、app_dir、data_dir）')
    c = cfg()
    STAGE.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        d = c['data_dir']
        dirs = [c['app_dir'] + '/pylib', c['app_dir'] + '/dashboard'] + [f'{d}/{x}' for x in ('state', 'config', 'scripts', '运营手册', 'reports', 'days')]
        r = subprocess.run(ssh_cmd(c) + [f'{c["user"]}@{c["host"]}', 'mkdir -p ' + ' '.join(f"'{x}'" for x in dirs)],
                           capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        if r.returncode != 0:
            raise RuntimeError(f'连不上服务器或建目录失败：{r.stderr.strip()[-300:]}')
        rsync(c, DASH_SRC, c['app_dir'] + '/dashboard/', filters=['- demo/sample/', '- __pycache__/', '- *.pyc'], dry=dry)
        # 服务器上的 Python 没装 markdown-it-py：把本机 .venv 里的纯 Python 包一起带过去（MIT 许可）
        import markdown_it
        site = Path(markdown_it.__file__).resolve().parent.parent
        for pkg in ('markdown_it', 'mdurl'):
            rsync(c, site / pkg, c['app_dir'] + f'/pylib/{pkg}/', filters=['- __pycache__/'], dry=dry)
        if code_only:
            log('代码已同步')
            return
        STAGE.mkdir(parents=True, exist_ok=True)
        snapshot_state(STAGE)
        d = c['data_dir']
        out = rsync(c, STAGE / 'state/', d + '/state/', dry=dry)
        out += rsync(c, STAGE / 'config/', d + '/config/', dry=dry)
        out += rsync(c, STAGE / 'scripts/', d + '/scripts/', dry=dry)
        out += rsync(c, ROOT / '运营手册/', d + '/运营手册/', filters=['- 存档/', '- 对标/kazike/raw/', '+ */', '+ *.md', '- *'], dry=dry)
        out += rsync(c, ROOT / 'reports/', d + '/reports/', filters=['+ *.md', '- *'], dry=dry)
        out += rsync(c, ROOT / 'days/', d + '/days/', filters=day_filters(c), dry=dry)
        if dry:
            print(out)
            return
        stamp = STAGE / '.sync.json'
        stamp.write_text(json.dumps({'at': dt.datetime.now(TZ).isoformat(timespec='seconds'),
                                     'seconds': round(time.time() - t0, 1)}, ensure_ascii=False))
        rsync(c, stamp, d + '/.sync.json', delete=False)
        log(f'同步完成，用时 {time.time() - t0:.0f} 秒')
    except Exception as e:
        log(f'同步失败：{e}')
        if dry:  # 试跑不计入失败次数，也不发提醒
            sys.exit(1)
        fails = STAGE / '.fails'
        n = int(fails.read_text()) + 1 if fails.exists() else 1
        fails.write_text(str(n))
        if n == 3:  # 连续 3 次失败（约 3 小时）发一次邮件，之后不重复刷
            try:
                subprocess.run([sys.executable, str(ROOT / 'scripts/alert_mail.py'), 'send', '--title', 'ip.provider.cn 数据同步连续失败',
                                '--body', f'本地工作台同步到 ip.provider.cn 已连续失败 3 次，手机上看到的数据停在上次成功的时间。最近一次报错：{e}'],
                               timeout=60)
            except Exception:
                pass
        sys.exit(1)
    (STAGE / '.fails').unlink(missing_ok=True)


DASH_SRC = ROOT / 'dashboard/'

if __name__ == '__main__':
    main()
