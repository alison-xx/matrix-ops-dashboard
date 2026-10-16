#!/usr/bin/env python3
"""互动台账：评论 / 回复 / 点赞 / 关注的记录、每日上限、去重、文案体检。

用户 2026-10-16 授权「深度活跃各平台账号，可以评论别人的作品、跟别人互动」。规则见 运营手册/互动运营.md。
记录写在 days/<日期>/engagement.jsonl（每行一条）。

用法:
  engage.py check <平台> "<评论文字>"            # 发之前先体检，有 error 不许发
  engage.py can <平台> <动作> [目标URL]           # 看今天还能不能做（上限 + 是否评论过这个目标）
  engage.py log <平台> <动作> <目标URL> "<文字>" [--note 备注]   # 发完立刻记
  engage.py count                                   # 今天各平台各动作数量
动作: reply(回复自己作品下的评论) / comment(评论别人的作品) / like / follow / repost(微博转发) / browse(养号浏览，目标写搜索词)
"""
import json, re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, now
from lint_content import HYPE, AI_ERR, PLACEHOLDER

# 每平台每天上限（reply 不设上限，但要真诚、不复制）
CAPS = {
    # 10-16 用户要求「评论互动可以频繁一些」：上限约翻倍；小红书对新号评论频率最敏感，提得少一点
    '抖音': {'comment': 25, 'like': 80, 'follow': 10},
    '小红书': {'comment': 18, 'like': 80, 'follow': 8},
    '微博': {'comment': 30, 'like': 80, 'follow': 10, 'repost': 4},
    '知乎': {'comment': 20, 'like': 80, 'follow': 10},
    'B站': {'comment': 15, 'like': 60, 'follow': 8},   # 10-16 新号 LV2，评论区对复制粘贴式评论很敏感，宁少勿滥
    '视频号': {'comment': 0, 'like': 0, 'follow': 0},   # 视频号网页端只能管自己作品的评论
    '公众号': {'comment': 0, 'like': 0, 'follow': 0},   # 只回复自己文章的留言
}
MAXLEN = {'抖音': 60, '小红书': 60, '视频号': 60, 'B站': 100, '微博': 120, '知乎': 200, '公众号': 200}
# 引流 / 求关 / 硬广：一律不许
LURE = [r'关注我', r'回关', r'互粉', r'互关', r'求关', r'看我主页', r'主页有', r'私信我', r'私我', r'加我', r'加微', r'vx', r'VX', r'微信号',
        r'v信', r'领取', r'扣1', r'扣个1', r'http', r'www\.', r'\.com', r'公众号', r'进群', r'粉丝群', r'来我', r'我的视频', r'我的笔记']
EMPTY = [r'^(说得|讲得|写得)?(太好了|真好|好棒|不错|有道理|学到了|收藏了|干货)[！!。~～]*$', r'^[👍🔥❤️✨💯]+$']


def day_file(d=None):
    d = d or now().date().isoformat()
    p = ROOT / 'days' / d / 'engagement.jsonl'
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def records(d=None):
    p = day_file(d)
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def all_targets(days=30):
    seen = set()
    base = ROOT / 'days'
    for f in sorted(base.glob('*/engagement.jsonl'))[-days:]:
        for l in f.read_text().splitlines():
            if l.strip():
                r = json.loads(l)
                if r['action'] in ('comment', 'reply', 'repost'):
                    seen.add(r['target'])
    return seen


def check(platform, text):
    errs, warns = [], []
    t = text.strip()
    if not t:
        errs.append('空评论')
    if len(t) > MAXLEN.get(platform, 120):
        errs.append(f'{len(t)} 字，{platform} 评论上限 {MAXLEN.get(platform)} 字')
    for pats, label in ((LURE, '引流/求关/硬广'), ([re.escape(w) for w in HYPE], '营销词'), (AI_ERR, 'AI 腔'), (PLACEHOLDER, '占位符')):
        h = sorted({m.group(0) for p in pats for m in re.finditer(p, t)})
        if h:
            errs.append(f'{label}：{"、".join(h)}')
    if any(re.search(p, t) for p in EMPTY):
        errs.append('空洞夸奖，没有信息量')
    if '——' in t:
        warns.append('有破折号')
    mine = [r['text'] for r in records() if r.get('text')]
    if t in mine:
        errs.append('今天已经发过一模一样的评论（禁止复制粘贴）')
    return errs, warns


def can(platform, action, target=None):
    cap = CAPS.get(platform, {}).get(action)
    n = sum(1 for r in records() if r['platform'] == platform and r['action'] == action)
    if cap is not None and n >= cap:
        return False, f'{platform} 今天 {action} 已 {n} 次，到上限 {cap}'
    if target and action in ('comment', 'reply', 'repost') and target in all_targets():
        return False, '30 天内已经评论/回复过这个目标'
    if action == 'comment':
        last = [r['time'] for r in records() if r['platform'] == platform and r['action'] == 'comment']
        if last:
            h, m = map(int, last[-1].split(':'))
            gap = (now().hour * 60 + now().minute) - (h * 60 + m)
            if 0 <= gap < 3:
                return False, f'{platform} 上一条评论在 {gap} 分钟前，至少隔 3 分钟（先去做别的平台）'
    return True, f'{platform} 今天 {action} {n}/{cap if cap is not None else "不限"}'


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return
    cmd = a[0]
    if cmd == 'check':
        errs, warns = check(a[1], a[2])
        print(json.dumps({'errors': errs, 'warns': warns}, ensure_ascii=False))
        sys.exit(1 if errs else 0)
    if cmd == 'can':
        ok, msg = can(a[1], a[2], a[3] if len(a) > 3 else None)
        print(('OK ' if ok else 'NO ') + msg)
        sys.exit(0 if ok else 1)
    if cmd == 'log':
        platform, action, target = a[1], a[2], a[3]
        text = a[4] if len(a) > 4 and not a[4].startswith('--') else ''
        note = a[a.index('--note') + 1] if '--note' in a else ''
        rec = {'time': now().strftime('%H:%M'), 'platform': platform, 'action': action, 'target': target, 'text': text, 'note': note}
        with day_file().open('a') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        print('logged', rec['time'], platform, action)
        return
    if cmd == 'count':
        out = {}
        for r in records():
            out.setdefault(r['platform'], {}).setdefault(r['action'], 0)
            out[r['platform']][r['action']] += 1
        print(json.dumps(out, ensure_ascii=False))
        return
    print(__doc__)


if __name__ == '__main__':
    main()
