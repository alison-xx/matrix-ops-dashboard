#!/usr/bin/env python3
"""生成一套示例数据，让没有真实数据的人也能把工作台跑起来。

    python dashboard/demo/make_demo.py [输出目录]      # 默认 dashboard/demo/sample
    python dashboard/server.py --demo                  # 自动调用 ensure()

全部是虚构账号和虚构内容，只用标准库。日期相对「今天」生成，过了一天再启动会自动重新生成。
目录结构和真实数据目录一致，可以当作接入自己数据的模板看：

    config/schedule.json        账号与每日发布时段
    config/dashboard.json       看板标题、目标、数据源节奏
    config/experiments.json     A/B 实验
    state/ops.sqlite3           发布台账（items / events）
    state/metrics.sqlite3       作品数据快照（snaps）
    state/fans.json             当前粉丝
    state/fans_history.jsonl    粉丝历史（每天一行）
    days/<日期>/...             每条内容一个目录（post.json + 图片），radar/、runs.jsonl、engagement.jsonl 等
    reports/<日期>.md           日报
    运营手册/*.md               规则与计划
    scripts/engage.py           互动上限 CAPS（看板只用 AST 读取，不执行）
"""
import datetime as dt
import json
import random
import shutil
import sqlite3
import struct
import sys
import zlib
from pathlib import Path
from zoneinfo import ZoneInfo

VERSION = 3
TZ = ZoneInfo('Asia/Shanghai')
N_DAYS = 21

ACCOUNTS = {
    'douyin': {'platform': '抖音', 'name': '示例 AI 实验室', 'type': 'video', 'times': ['12:00', '18:00', '21:00'], 'fans0': 820, 'rate': 26},
    'channels': {'platform': '视频号', 'name': '示例聊AI', 'type': 'video', 'times': ['12:30', '18:30'], 'fans0': 310, 'rate': 9},
    'bilibili': {'platform': '哔哩哔哩', 'name': '示例AI研究所', 'type': 'video', 'times': ['19:00'], 'fans0': 150, 'rate': 5},
    'kuaishou': {'platform': '快手', 'name': '示例聊AI', 'type': 'video', 'times': ['20:30'], 'fans0': 60, 'rate': 2},
    'xhs': {'platform': '小红书', 'name': '示例 AI 手帐', 'type': 'imageText', 'times': ['08:20', '12:20', '20:40'], 'fans0': 1240, 'rate': 31},
    'weibo': {'platform': '新浪微博', 'name': '示例AI观察', 'type': 'imageText', 'times': ['08:30', '11:30', '14:30', '18:30', '22:00'], 'fans0': 5200, 'rate': 12},
    'zhihu': {'platform': '知乎', 'name': '示例AI观察', 'type': 'article', 'times': ['10:00', '21:00'], 'fans0': 2300, 'rate': 15},
    'wechat': {'platform': '微信公众号', 'name': '示例 AI 周刊', 'type': 'article', 'times': ['20:00'], 'fans0': 980, 'rate': 8},
}
PLAT_SLUG = {'douyin': 'dy', 'channels': 'sph', 'bilibili': 'bili', 'kuaishou': 'ks', 'xhs': 'xhs', 'weibo': 'wb', 'zhihu': 'zh', 'wechat': 'gzh'}
METRIC_PLATFORM = {'douyin': 'douyin', 'channels': 'channels', 'bilibili': 'bilibili', 'kuaishou': 'kuaishou', 'xhs': 'xhs',
                   'weibo': 'weibo', 'zhihu': 'zhihu', 'wechat': 'wechat'}
COLORS = {'douyin': ((32, 36, 48), (90, 60, 140)), 'channels': ((250, 157, 59), (255, 214, 140)), 'bilibili': ((251, 114, 153), (255, 196, 214)),
          'kuaishou': ((255, 73, 6), (255, 170, 110)), 'xhs': ((255, 36, 66), (255, 168, 178)), 'weibo': ((230, 22, 45), (255, 150, 120)),
          'zhihu': ((0, 132, 255), (130, 200, 255)), 'wechat': ((7, 193, 96), (150, 230, 190))}
COLUMNS = ['工具实测', '热点快评', '提示词', '效率工作流', '行业观察']
TOPICS = [
    '用 AI 十分钟整理一周会议纪要', '3 个提示词让周报不再难写', '本地跑大模型需要什么配置', '把表格丢给 AI 做数据分析的正确姿势',
    'AI 写的方案为什么总像模板', '一个人用 AI 做出整套品牌视觉', '新手最容易踩的 5 个 AI 工具坑', 'AI 生成 PPT 到底能不能直接用',
    '让 AI 读 100 页 PDF 的方法', '长文改写：怎么去掉机器腔', '开源模型和闭源模型怎么选', '用智能体自动处理邮件的一天',
    '图片生成里的版权问题', 'AI 编程助手真实提效多少', '语音克隆做口播的边界', '我用 AI 做了一个月短视频的复盘',
    '大模型上下文越长越好吗', '多模态模型能看懂截图了', 'AI 搜索会取代传统搜索吗', '为什么你的提示词越写越长',
    '用 AI 做竞品分析的完整流程', '小团队怎么低成本接入大模型', '一张图看懂智能体的工作方式', 'AI 帮我省下的第一个小时',
]
HOT = ['开源模型发布新版本，长上下文再翻倍', '某办公软件上线 AI 助手全员可用', '大模型价格战继续：输入价格降到每百万 1 元',
       '多家手机厂商宣布端侧大模型', 'AI 生成视频进入短剧行业', '高校发布 AI 使用规范', '智能体平台开放第三方插件市场',
       '新一代显卡发布，本地推理速度提升', 'AI 翻译耳机实测走红', '数据标注行业的转型']
FAIL_MSG = [
    ('network', '{"tasks":[{"stages":"push","stageStatus":"fail","errorMessage":"网络异常:connect ECONNREFUSED 10.0.0.8:4859"}]}'),
    ('login', '{"tasks":[{"stages":"upload","stageStatus":"fail","errorMessage":"获取用户信息失败，登录失效"}]}'),
    ('review', '{"tasks":[{"stages":"publish","stageStatus":"fail","errorMessage":"内容审核不通过：疑似营销信息"}]}'),
    ('content', '{"tasks":[{"stages":"check","stageStatus":"fail","errorMessage":"封面尺寸不符合要求，最小 1080x1440"}]}'),
    ('timeout', '{"tasks":[{"stages":"push","stageStatus":"fail","errorMessage":"请求超时 timeout"}]}'),
]


# ---------- 小工具 ----------
def png(path, w, h, c1, c2, rnd):
    """纯标准库画一张渐变封面：底色渐变 + 一块浅色卡片 + 一个圆，不含文字。"""
    cx, cy, rad = rnd.randint(w // 4, 3 * w // 4), rnd.randint(h // 5, h // 2), rnd.randint(w // 7, w // 4)
    top, bot = int(h * 0.58), int(h * 0.86)
    raw = bytearray()
    for y in range(h):
        t = y / (h - 1)
        base = tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))
        raw.append(0)
        for x in range(w):
            r, g, b = base
            if (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad:
                r, g, b = (min(255, r + 60), min(255, g + 60), min(255, b + 60))
            elif top <= y <= bot and w * 0.1 <= x <= w * 0.9:
                r, g, b = (int(r * 0.25 + 255 * 0.75), int(g * 0.25 + 255 * 0.75), int(b * 0.25 + 255 * 0.75))
            raw += bytes((r, g, b))

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    body = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + \
        chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b'')
    path.write_bytes(body)


def wjson(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')


def wtext(p, s):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding='utf-8')


# ---------- 生成 ----------
def build(out):
    out = Path(out)
    now = dt.datetime.now(TZ).replace(second=0, microsecond=0)
    today = now.date()
    rnd = random.Random(f'demo-{today.isoformat()}')
    if out.exists():
        shutil.rmtree(out)
    (out / 'state').mkdir(parents=True)
    days = [(today - dt.timedelta(days=i)) for i in range(N_DAYS - 1, -1, -1)]

    # 配置
    accounts = {}
    for slot, a in ACCOUNTS.items():
        accounts[slot] = {k: v for k, v in a.items() if k not in ('fans0', 'rate')}
        accounts[slot]['account_id'] = 'demo' + format(abs(hash(slot)) % 16 ** 12, '012x') if False else f'demo-{slot}'
    wjson(out / 'config/schedule.json', {'timezone': 'Asia/Shanghai', 'accounts': accounts})
    wjson(out / 'config/dashboard.json', {
        'title': '示例矩阵', 'subtitle': '运营工作台（示例数据）',
        'goal': {'fans': 15000, 'by': (today + dt.timedelta(days=75)).isoformat(), 'label': '季度目标 1.5 万粉'},
    })
    wjson(out / 'config/experiments.json', {'experiments': [
        {'id': 'E001', 'title': '视频钩子：数字冲突型 vs 反差型', 'status': 'running', 'platforms': ['douyin', 'channels'],
         'hypothesis': '第一句直接给数字冲突，比先抛反差更能压低 2 秒跳出', 'metric': 'bounce_2s', 'direction': 'down', 'min_n': 8,
         'arms': {'A': '数字冲突：第一句话里出现具体数字和对比', 'B': '反差：先说一个反常识结论'},
         'start': (today - dt.timedelta(days=6)).isoformat(), 'review': (today + dt.timedelta(days=4)).isoformat()},
        {'id': 'E002', 'title': '小红书封面：大字报 vs 实拍截图', 'status': 'running', 'platforms': ['xhs'],
         'hypothesis': '大字报封面点击率更高，但收藏率可能更低', 'metric': 'views_lift', 'direction': 'up', 'min_n': 10,
         'arms': {'A': '大字报：一句话标题占满封面', 'B': '实拍：工具界面截图 + 小标题'},
         'start': (today - dt.timedelta(days=9)).isoformat(), 'review': (today + dt.timedelta(days=1)).isoformat()},
        {'id': 'E000', 'title': '发布时段：午间 vs 晚间', 'status': 'adopted', 'platforms': ['douyin'], 'metric': 'views_lift',
         'direction': 'up', 'min_n': 6, 'arms': {'A': '12:00', 'B': '21:00'}, 'result': '晚间均播放 1.6 倍，主推时段改到 21:00',
         'start': (today - dt.timedelta(days=20)).isoformat(), 'review': (today - dt.timedelta(days=10)).isoformat()},
    ]})
    wtext(out / 'scripts/engage.py', '"""示例：每个平台每天的互动上限（看板用 AST 读取 CAPS，不执行本文件）"""\n'
          "CAPS = {\n    '抖音': {'comment': 25, 'like': 60, 'follow': 10},\n    '小红书': {'comment': 15, 'like': 40, 'follow': 8},\n"
          "    '微博': {'comment': 30, 'like': 80, 'follow': 10},\n    '知乎': {'comment': 20, 'like': 50, 'follow': 5},\n"
          "    '视频号': {'comment': 0, 'like': 0, 'follow': 0},\n}\n")

    # 封面素材池（放在 days/_covers，看板把它当作内容目录的一部分）
    cov = out / 'days/_covers'
    cov.mkdir(parents=True)
    pool = {}
    for slot, (c1, c2) in COLORS.items():
        pool[slot] = []
        for k in range(3):
            p = cov / f'{slot}-{k}.png'
            png(p, 180, 240, c1, c2, rnd)
            pool[slot].append(p.name)

    # 台账 + 作品数据
    ops = sqlite3.connect(out / 'state/ops.sqlite3')
    ops.executescript("""
    CREATE TABLE items(id TEXT PRIMARY KEY, day TEXT, slot TEXT, platform TEXT, account_id TEXT,
      publish_type TEXT, due TEXT, mode TEXT, status TEXT, payload TEXT, content_file TEXT, hash TEXT,
      title TEXT, task_id TEXT, url TEXT, url_verified INTEGER DEFAULT 0, detail TEXT, updated TEXT);
    CREATE TABLE events(n INTEGER PRIMARY KEY, at TEXT, item TEXT, kind TEXT, data TEXT);""")
    met = sqlite3.connect(out / 'state/metrics.sqlite3')
    met.execute('CREATE TABLE snaps(platform TEXT, account TEXT, post_id TEXT, title TEXT, created INTEGER, snap INTEGER, m TEXT, '
                'PRIMARY KEY(platform, account, post_id, snap))')
    base_views = {'douyin': 900, 'channels': 600, 'bilibili': 400, 'kuaishou': 250, 'xhs': 700, 'weibo': 300, 'zhihu': 500, 'wechat': 350}
    seq = 0
    for d in days:
        ds = d.isoformat()
        for slot, a in ACCOUNTS.items():
            if slot == 'kuaishou' and (today - d).days > 12:
                continue  # 快手是后来加的号
            for k, tm in enumerate(a['times']):
                seq += 1
                hh, mm = map(int, tm.split(':'))
                due = dt.datetime.combine(d, dt.time(hh, mm), TZ)
                title = rnd.choice(TOPICS) if rnd.random() > 0.15 else '热点：' + rnd.choice(HOT)
                column = '热点快评' if title.startswith('热点') else rnd.choice(COLUMNS)
                iid = f'{ds}-{slot}-{k + 1}'
                folder = out / 'days' / ds / f'{slot}-{k + 1}'
                folder.mkdir(parents=True, exist_ok=True)
                imgs = [f'../../_covers/{rnd.choice(pool[slot])}' for _ in range(1 if a['type'] == 'video' else 3)]
                post = {'title': title, 'column': column, 'slot': slot, 'time': tm, 'kind': a['type'], 'images': imgs,
                        'description': f'{title}。这是一条示例内容的文案，用来演示内容详情抽屉。\n\n#AI #效率工具', 'tags': ['AI', '效率工具']}
                if rnd.random() < 0.3:
                    post['exp'] = 'E001:A' if rnd.random() < 0.5 else 'E001:B'
                wjson(folder / 'post.json', post)
                if a['type'] == 'article':
                    wtext(folder / 'article.md', f'# {title}\n\n示例正文第一段。真实数据里这里是公众号/知乎的完整文章。\n\n## 小标题\n\n- 要点一\n- 要点二\n')
                wtext(folder / 'review.md', f'# 审稿记录\n\n- 去 AI 味：通过\n- 事实核查：示例数据，无需核查\n')
                mode = 'native' if a['type'] == 'video' else ('web' if slot in ('channels', 'kuaishou') else 'dispatch')
                pid = f'{70000000 + seq * 37}'
                url = f'https://example.com/{slot}/{pid}'
                status, detail, task = 'public', '{"ok": true, "task_id": "demo-%d"}' % seq, f'demo-{seq}'
                upd = due + dt.timedelta(minutes=rnd.randint(1, 20))
                if due > now:
                    status = 'scheduled' if mode == 'native' else 'ready'
                    url, upd = '', now - dt.timedelta(minutes=rnd.randint(30, 300))
                elif rnd.random() < 0.08:
                    key, detail = rnd.choice(FAIL_MSG)
                    status, url = 'failed', ''
                    # 大多数失败会在当天重提
                    if rnd.random() < 0.75:
                        ops.execute('INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                    (iid + 'b', ds, slot, a['platform'], f'demo-{slot}', a['type'], (due + dt.timedelta(minutes=25)).isoformat(),
                                     'web', 'web' if due + dt.timedelta(minutes=25) <= now else 'ready', str(folder.relative_to(out) / 'post.payload.json'),
                                     '', '', title, f'demo-{seq}b', f'https://example.com/{slot}/{pid}9', 1, '网页补发', (upd + dt.timedelta(minutes=30)).isoformat()))
                ops.execute('INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                            (iid, ds, slot, a['platform'], f'demo-{slot}', a['type'], due.isoformat(), mode, status,
                             str(folder.relative_to(out) / 'post.payload.json'), '', '', title, task, url, 1 if url else 0, detail, upd.isoformat()))
                for n_ev, (kind, data) in enumerate([('add', {'slot': slot}), ('approve', {'lint': 'ok'}), ('submit', {'mode': mode})]):
                    ops.execute('INSERT INTO events(at, item, kind, data) VALUES (?,?,?,?)',
                                ((due - dt.timedelta(hours=3 - n_ev)).isoformat(), iid, kind, json.dumps(data, ensure_ascii=False)))
                if status == 'public':
                    age_h = (now - due).total_seconds() / 3600
                    if age_h < 3:
                        continue
                    lift = rnd.lognormvariate(0, 0.7) * (1.25 if tm >= '18:00' else 0.9) * (1 + (N_DAYS - (today - d).days) / 40)
                    views = int(base_views[slot] * lift)
                    m = {'views': views, 'likes': int(views * rnd.uniform(0.02, 0.06)), 'favorites': int(views * rnd.uniform(0.005, 0.03)),
                         'comments': int(views * rnd.uniform(0.002, 0.012)), 'shares': int(views * rnd.uniform(0.001, 0.01))}
                    if a['type'] == 'video':
                        m.update(duration=rnd.choice([28, 45, 75, 120, 150]), bounce_2s=round(rnd.uniform(0.18, 0.5), 3),
                                 completion_5s=round(rnd.uniform(0.35, 0.68), 3), avg_view_ratio=round(rnd.uniform(0.15, 0.55), 3))
                    if slot == 'douyin':
                        m['follows'] = int(views * rnd.uniform(0.001, 0.008))
                    for snap_h in (min(age_h, 20), age_h):
                        f = min(1.0, 0.55 + snap_h / 60)
                        mm_ = {k2: (int(v * f) if isinstance(v, int) and k2 not in ('duration',) else v) for k2, v in m.items()}
                        snap = int((due + dt.timedelta(hours=snap_h)).timestamp())
                        met.execute('INSERT OR REPLACE INTO snaps VALUES (?,?,?,?,?,?,?)',
                                    (METRIC_PLATFORM[slot], a['name'], f'{PLAT_SLUG[slot]}-{pid}', title, int(due.timestamp()), snap,
                                     json.dumps(mm_)))
    ops.commit()
    met.commit()
    ops.close()
    met.close()

    # 粉丝
    hist, cur = [], {}
    fans = {slot: a['fans0'] for slot, a in ACCOUNTS.items()}
    for d in days[:-1]:
        for slot, a in ACCOUNTS.items():
            fans[slot] += max(-3, int(rnd.gauss(a['rate'], a['rate'] * 0.6)))
        hist.append({'at': dt.datetime.combine(d + dt.timedelta(days=1), dt.time(3, 40), TZ).isoformat(), 'day': d.isoformat(),
                     'fans': {f'demo-{s}': n for s, n in fans.items()}})
    for slot, a in ACCOUNTS.items():
        cur[f'demo-{slot}'] = fans[slot] + max(0, int(rnd.gauss(a['rate'] * 0.4, 3)))
    wtext(out / 'state/fans_history.jsonl', '\n'.join(json.dumps(h, ensure_ascii=False) for h in hist) + '\n')
    wjson(out / 'state/fans.json', cur)

    # 每天的附属文件
    for d in days:
        ds = d.isoformat()
        dd = out / 'days' / ds
        recent = (today - d).days
        runs = []
        for task, hm, mins in [('早班', '07:10', 24), ('热点雷达', '09:05', 3), ('午班', '11:30', 31), ('数据回流', '12:40', 6),
                               ('晚班', '17:30', 38), ('数据回流', '22:40', 6), ('日报', '23:00', 12)]:
            st = dt.datetime.combine(d, dt.time(*map(int, hm.split(':'))), TZ)
            if st > now:
                continue
            runs.append({'at': st.isoformat(), 'task': task, 'event': 'start', 'version': f'v{ds.replace("-", ".")}-1'})
            en = st + dt.timedelta(minutes=mins)
            if en <= now:
                runs.append({'at': en.isoformat(), 'task': task, 'event': 'end', 'summary': f'{task}完成（示例）'})
        wtext(dd / 'runs.jsonl', '\n'.join(json.dumps(r, ensure_ascii=False) for r in runs) + '\n')
        eng = []
        for _ in range(rnd.randint(8, 30) if recent < 7 else 0):
            pf = rnd.choice(['抖音', '小红书', '微博', '知乎'])
            act = rnd.choice(['comment', 'comment', 'reply', 'like', 'like', 'follow'])
            eng.append({'time': f'{rnd.randint(8, 22):02d}:{rnd.randint(0, 59):02d}', 'platform': pf, 'action': act,
                        'target': 'https://example.com/post/' + str(rnd.randint(1000, 9999)),
                        'text': '这个思路很实用，我们团队也在这么做' if act in ('comment', 'reply') else '', 'note': ''})
        eng.sort(key=lambda r: r['time'])
        if eng:
            wtext(dd / 'engagement.jsonl', '\n'.join(json.dumps(r, ensure_ascii=False) for r in eng) + '\n')
        if recent < 3:
            (dd / 'radar').mkdir(exist_ok=True)
            for h in range(7, 24, 2):
                at = dt.datetime.combine(d, dt.time(h, 5), TZ)
                if at > now:
                    break
                cands = []
                for t in rnd.sample(HOT, 5):
                    cands.append({'title': t, 'score': round(rnd.uniform(4, 9.5), 2), 'cross_score': rnd.randint(5, 90),
                                  'sources': [f'微博#{rnd.randint(1, 50)}', f'知乎#{rnd.randint(1, 50)}'],
                                  'angle': '从普通用户能不能用上、要花多少钱切入', 'url': 'https://example.com/hot'})
                wjson(dd / 'radar' / f'{h:02d}05.json', {'at': at.isoformat(), 'total': rnd.randint(150, 300), 'new': rnd.randint(5, 40),
                                                          'candidates': cands, 'source_counts': {'微博': 50, '知乎': 50, '抖音': 50}})
            wtext(dd / 'hot-log.md', f'# {ds} 热点快反记录\n\n- 09:05 选中「{HOT[0]}」，抖音 + 微博快反（示例）\n- 14:05 候选分数都低于 7，不跟\n')
        if recent < 10:
            wtext(dd / 'zhihu-answers.md', '| 时间 | 问题 | 栏目 | 链接 | 备注 |\n|---|---|---|---|---|\n'
                  f'| 15:00 | 如何评价{rnd.choice(HOT)}？ | 热点快评 | https://example.com/zhihu/{rnd.randint(1000, 9999)} | 示例回答 |\n')
        if recent < 8 and recent > 0:
            wtext(out / 'reports' / f'{ds}.md', f'# {ds} 日报（示例）\n\n生成时间：{ds} 23:12\n\n## 今日数据\n\n- 发布 {rnd.randint(16, 20)} 条，失败 {rnd.randint(0, 3)} 条\n'
                  f'- 涨粉 {rnd.randint(60, 140)}\n\n## 需要你看\n\n- ⚠️ 示例：小红书封面实验今天到复查日\n\n## 明天计划\n\n- 继续 E001 钩子实验\n')
    ev_day = out / 'days' / (today - dt.timedelta(days=1)).isoformat()
    wjson(ev_day / 'evolve.json', {
        'generated': dt.datetime.combine(today - dt.timedelta(days=1), dt.time(23, 5), TZ).isoformat(), 'window_days': 7,
        'n_posts': 120, 'n_eligible': 96, 'n_matched': 110,
        'suggestions': ['抖音 21:00 档均播放是 12:00 档的 1.6 倍，建议把系列主更放到 21:00', '小红书「提示词」栏目收藏率最高，下周加一条'],
        'quality': ['视频号没有留存数据，开头实验只看抖音'],
        'platform_baseline': {'抖音': 900, '小红书': 700, '微博': 300},
        'dims': [{'dim': '栏目', 'value': '提示词', 'n': 18, 'lift': 1.32, 'eng_rate': 0.061},
                 {'dim': '栏目', 'value': '热点快评', 'n': 22, 'lift': 1.08, 'eng_rate': 0.044},
                 {'dim': '栏目', 'value': '行业观察', 'n': 15, 'lift': 0.74, 'eng_rate': 0.031},
                 {'dim': '时段', 'value': '晚间', 'n': 40, 'lift': 1.21, 'eng_rate': 0.05},
                 {'dim': '时段', 'value': '午间', 'n': 38, 'lift': 0.88, 'eng_rate': 0.045}]})

    # 运营手册（也是开源模板）
    ver = f'v{today.strftime("%Y.%m.%d")}-3'
    wtext(out / '运营手册/00-必读.md', f'# 示例矩阵 · 运营系统入口（00-必读）\n\n版本：{ver}\n\n'
          '> 所有定时任务开工先读这一页。规则只有这一个入口，改规则必须同时改这里并升版本号。\n\n'
          '## 1. 目标\n\n第一目标是涨粉。配额是下限，热点第一时间发。\n\n'
          '## 2. 硬规则\n\n1. 发布前过内容体检，有问题不发。\n2. 不冒充他人，不搬运。\n3. 失败先看原因归类再重提，不原样重发。\n\n'
          '## 3. 每日节奏\n\n| 时间 | 任务 |\n|---|---|\n| 07:10 | 早班：选题、制作、排期 |\n| 每 30 分钟 | 热点雷达 |\n'
          '| 12:40 / 22:40 | 数据回流 |\n| 23:00 | 日报 + 数据进化 |\n\n## 4. 改规则流程\n\n改专题手册 → 写进本页硬规则 → 升版本 → 写变更日志。\n')
    wtext(out / '运营手册/运营计划.md', '# 当前运营计划（示例）\n\n## 生效中的调整\n\n- 抖音系列主更改到 21:00（来自 E000）\n\n'
          '## 进行中的实验\n\n- E001 视频钩子\n- E002 小红书封面\n\n## 待修问题\n\n- 视频号网页登录和发布工具互相挤掉\n\n## 需要拍板\n\n- 是否把快手从每天 1 条降到隔天 1 条\n')
    log = ['# 变更日志\n']
    for i in range(3, 0, -1):
        log.append(f'## v{today.strftime("%Y.%m.%d")}-{i}（{today.isoformat()} {8 + i:02d}:00，来源：{["数据", "用户", "事故"][i % 3]}）\n\n'
                   f'- 示例改动 {i}：调整了某个平台的发布时段\n- 同步更新了专题手册\n')
    for k in range(1, 6):
        d = today - dt.timedelta(days=k)
        log.append(f'## v{d.strftime("%Y.%m.%d")}-1（{d.isoformat()} 23:10，来源：数据）\n\n- 日报进化：栏目配比微调（示例）\n')
    wtext(out / '运营手册/变更日志.md', '\n'.join(log))
    wtext(out / '运营手册/平台打法/抖音.md', '# 抖音打法（示例）\n\n## 定位\n\n系列化测评，每条 2–4 分钟。\n\n## 开头\n\n前 2 秒必须出现冲突或数字。\n')
    wtext(out / '运营手册/平台打法/小红书.md', '# 小红书打法（示例）\n\n## 定位\n\n能收藏带走的清单和模板。\n\n## 封面\n\n大字标题，3:4。\n')
    wtext(out / '.demo-version', json.dumps({'version': VERSION, 'day': today.isoformat()}))
    return out


def ensure(out):
    """示例数据不存在、版本变了或日期过了就重新生成。"""
    out = Path(out)
    try:
        mark = json.loads((out / '.demo-version').read_text(encoding='utf-8'))
        if mark.get('version') == VERSION and mark.get('day') == dt.datetime.now(TZ).date().isoformat():
            return out
    except Exception:
        pass
    return build(out)


if __name__ == '__main__':
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / 'sample'
    print('示例数据已生成：', build(target))
