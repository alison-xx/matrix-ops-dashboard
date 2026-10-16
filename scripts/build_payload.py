#!/usr/bin/env python3
"""把一条内容(post.json)变成 yxer 标准 payload：上传素材 -> 组装 -> 写 payload.json。

post.json 字段：
  slot: douyin|channels|bilibili|kuaishou|xhs|weibo|zhihu|wechat|wechat_tietu（公众号贴图）
  kind: 可选，换发布形式（默认按排期）：抖音/视频号/知乎 "imageText"（知乎=想法）；小红书/微博 "video"（复用抖音成片）
  tags, cover_169, category  B站：标签 1–12 个（不填就取描述末尾的 #话题）；16:9 封面（不填用 cover）；分区默认 schedule.json 里的「科技 > 软件应用」
  time: "HH:MM"           排期时间
  native: true/false      是否使用平台原生定时（默认按平台能力与剩余时间自动判断）
  title, description(纯文本，空行分段；#话题 写在末尾)
  images: [本地路径...]    图文
  video, cover            视频与封面
  article_md              知乎/公众号正文 markdown 或 html 文件
  wechat_html             公众号排版后的 HTML 正文片段
  digest, author          公众号
  source_url              公众号「阅读原文」链接，默认 schedule.json 里 wechat.source_url（示例服务 web.provider.cn）
  statement               公众号贴图内容声明：0 无需声明（默认；10-16 用户：所有平台不勾 AI 声明）、4 个人观点
上传结果缓存在 <post>.uploads.json，避免重复上传。
用法: .venv/bin/python scripts/build_payload.py <post.json>   -> 输出 payload 路径
"""
import datetime as dt, html, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, TZ, now, yxer, dump

SCHED = json.loads((ROOT / 'config/schedule.json').read_text())


def upload(path, cache, extra=()):
    key = str(path) + '|' + ','.join(extra)
    if key in cache:
        return cache[key]
    args = ['upload', str(path), *extra]
    if str(path).endswith(('.mp4', '.mov')):
        args.append('--auto-meta')
    rc, o = yxer(*args, timeout=900)
    if rc or not o.get('ok'):
        raise RuntimeError(f'上传失败 {path}: {dump(o)[:800]}')
    d = o['data']
    obj = {k: d[k] for k in ('key', 'size', 'width', 'height', 'duration', 'format') if d.get(k) is not None}
    cache[key] = obj
    return obj


def bili_category(acc, want):
    """B站分区要从根到末级的完整路径对象，直接用 query categories --paths 返回的 category。"""
    rc, o = yxer('query', 'categories', acc['account_id'], '--type', 'video', '--paths')
    if rc or not o.get('ok'):
        raise RuntimeError(f'B站分区查询失败: {dump(o)[:500]}')
    for p in o['data']['paths']:
        if p['path'].replace(' ', '') == want.replace(' ', ''):
            return p['category']
    raise ValueError(f'B站没有分区「{want}」')


def paras_html(text):
    out = []
    for p in [x.strip() for x in text.strip().split('\n') if x.strip()]:
        out.append(f'<p>{html.escape(p)}</p>')
    return ''.join(out)


def alt_form(p, kind, acc, plat, pa, cache, rel, sched, decl):
    """同一时段换形式：抖音/视频号/知乎 图文，小红书/微博 视频。"""
    slot = acc.get('base', p['slot'])  # 同平台第二个号（如 douyin_office）沿用 base 平台的表单
    if kind == 'video':  # 小红书视频、微博视频（复用抖音成片）
        video = upload(rel(p['video']), cache)
        cover = upload(rel(p['cover']), cache)
        if slot == 'xhs':
            cpf = {'formType': 'task', 'title': p['title'], 'description': paras_html(p.get('description', '')), 'declaration': p.get('declaration', 0),
                   'createType': 0, 'visibleType': 0, **sched}
        elif slot == 'weibo':
            cpf = {'formType': 'task', 'title': p['title'], 'description': p.get('description', ''), 'createType': p.get('createType', 1),
                   'pubType': 1, 'visibleType': 0, 'video': video}
        else:
            raise ValueError(f'{plat} 视频暂未接入')
        pa['accountForms'] = [{'platformAccountId': acc['account_id'], 'video': video, 'cover': cover, 'coverKey': cover['key'], 'contentPublishForm': cpf}]
    elif kind == 'imageText':  # 抖音图文、视频号图文、知乎想法
        imgs = [upload(rel(x), cache) for x in p['images']]
        cpf = {'formType': 'task', 'description': p.get('description', '')}
        if slot == 'douyin':
            cpf.update({'title': p['title'][:20], 'declaration': p.get('declaration', decl), 'visibleType': 0, **sched})
        elif slot == 'channels':
            cpf.update({'title': p['title'][:22], 'declaration': p.get('declaration', decl), 'pubType': 1, **sched})
        elif slot == 'zhihu':
            if p.get('title'):
                cpf['title'] = p['title'][:50]
        form = {'platformAccountId': acc['account_id'], 'images': imgs, 'contentPublishForm': cpf}
        if slot == 'douyin':  # 抖音图文要封面：默认第一张图
            cv = upload(rel(p['cover']), cache) if p.get('cover') else imgs[0]
            form.update({'cover': cv, 'coverKey': cv['key']})
        pa['accountForms'] = [form]
    else:
        raise ValueError(f'未知 kind={kind}')


def build(post_path):
    post_path = pathlib.Path(post_path).resolve()
    p = json.loads(post_path.read_text())
    base = post_path.parent
    acc = SCHED['accounts'][p['slot']]
    bslot = acc.get('base', p['slot'])
    plat = acc['platform']
    cache_p = post_path.with_suffix('.uploads.json')
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    day = p.get('day') or now().date().isoformat()
    due = dt.datetime.fromisoformat(f"{day}T{p['time']}:00").replace(tzinfo=TZ)
    lead = acc.get('native_lead_min')
    native = p.get('native')
    if native is None:
        native = bool(lead) and (due - now()).total_seconds() > (lead + 15) * 60
    sched = {'scheduledTime': int(due.timestamp() * 1000)} if native else {}
    decl = 0   # 10-16 用户：「以后都不勾选 AI 声明，其他平台也一样」，各平台 declaration/statement 一律 0（不声明）

    def rel(x):
        q = pathlib.Path(x)
        return q if q.is_absolute() else (base / q)

    kind = p.get('kind') or acc['type']
    if kind not in [acc['type'], *acc.get('alt_types', [])]:
        raise ValueError(f"{plat} 不支持 kind={kind}（可选 {[acc['type'], *acc.get('alt_types', [])]}）")
    o = {'action': 'publish', 'publishType': kind, 'platforms': [plat], 'publishChannel': 'cloud', 'publishArgs': {}}
    pa = o['publishArgs']
    try:
        if kind != acc['type']:
            alt_form(p, kind, acc, plat, pa, cache, rel, sched, decl)
        elif bslot in ('douyin', 'channels'):
            video = upload(rel(p['video']), cache)
            cov_extra = ('--platform', '视频号', '--usage', 'cover') if bslot == 'channels' else ()
            cover = upload(rel(p['cover']), cache, cov_extra)
            cpf = {'formType': 'task', 'title': p['title'], 'description': p.get('description', ''), **sched}
            if bslot == 'douyin':
                cpf.update({'declaration': p.get('declaration', decl), 'visibleType': 0, 'allow_save': 1})
                if p.get('hot_event'):  # 关联抖音热点：来自 yxer query hot-events 的 yixiaoerId/yixiaoerName
                    cpf['hot_event'] = {k: p['hot_event'][k] for k in ('yixiaoerId', 'yixiaoerName')}
            else:
                cpf.update({'declaration': p.get('declaration', decl), 'createType': p.get('createType', 2), 'pubType': 1})
                if p.get('short_title'):
                    cpf['short_title'] = p['short_title']
            pa['accountForms'] = [{'platformAccountId': acc['account_id'], 'video': video, 'cover': cover, 'coverKey': cover['key'], 'contentPublishForm': cpf}]
        elif bslot == 'kuaishou':  # 快手-Open 视频（接口兜底；默认网页发布 web_publish/kuaishou.js）
            video = upload(rel(p['video']), cache)
            cover = upload(rel(p['cover']), cache)
            cpf = {'formType': 'task', 'description': p.get('description', ''), 'visibleType': 0, 'pubType': 1, **sched}
            pa['accountForms'] = [{'platformAccountId': acc['account_id'], 'video': video, 'cover': cover, 'coverKey': cover['key'], 'contentPublishForm': cpf}]
        elif bslot == 'bilibili':
            video = upload(rel(p['video']), cache)
            cover = upload(rel(p.get('cover_169') or p['cover']), cache)
            desc = p.get('description', '')
            tags = p.get('tags') or re.findall(r'#([^#\s]{1,20})', desc)
            desc = re.sub(r'\s*#[^#\s]+', '', desc).strip()  # B站描述里的 #话题 不生效，标签单独走 tags
            cpf = {'formType': 'task', 'title': p['title'][:80], 'description': desc[:2000], 'tags': tags[:12],
                   'category': bili_category(acc, p.get('category') or acc['category']),
                   'createType': p.get('createType', 1), 'allowReprint': 1, 'visibleType': 0, 'pubType': 1, **sched}
            pa['accountForms'] = [{'platformAccountId': acc['account_id'], 'video': video, 'cover': cover, 'coverKey': cover['key'], 'contentPublishForm': cpf}]
        elif bslot in ('xhs', 'weibo'):
            imgs = [upload(rel(x), cache) for x in p['images']]
            desc = p['description_html'] if p.get('description_html') else paras_html(p['description'])
            cpf = {'formType': 'task', 'description': desc, 'visibleType': 0, **sched}
            if p['slot'] == 'xhs':
                cpf.update({'title': p['title'], 'declaration': p.get('declaration', 0), 'createType': 0})
            else:
                cpf.update({'declaration': p.get('declaration', 0)})
            pa['accountForms'] = [{'platformAccountId': acc['account_id'], 'images': imgs, 'contentPublishForm': cpf}]
        elif bslot == 'wechat_tietu':  # 公众号贴图（imageText）：图片在 accountForms[].images，表单字段见 yixiaoer skill weixingongzhonghao.md
            imgs = [upload(rel(x), cache) for x in p['images']]
            desc = p['description_html'] if p.get('description_html') else paras_html(p.get('description', ''))
            cpf = {'formType': 'task', 'title': p['title'][:20], 'desc': desc, 'notifySubscribers': 0, 'sex': 0,
                   'needOpenComment': p.get('needOpenComment', 3), 'statement': p.get('statement', 0), 'disableRecommend': 0,
                   'pubType': p.get('pubType', 1), **sched}
            pa['accountForms'] = [{'platformAccountId': acc['account_id'], 'images': imgs, 'contentPublishForm': cpf}]
        elif p['slot'] == 'zhihu':
            cpf = {'formType': 'task', 'title': p['title'], 'pubType': 1, 'declaration': p.get('declaration', decl)}
            if p.get('cover'):
                cv = upload(rel(p['cover']), cache)
                cpf['covers'] = [{k: cv[k] for k in ('key', 'size', 'width', 'height')}]
                pa['accountForms'] = [{'platformAccountId': acc['account_id'], 'cover': cv, 'coverKey': cv['key'], 'contentPublishForm': cpf}]
            else:
                pa['accountForms'] = [{'platformAccountId': acc['account_id'], 'contentPublishForm': cpf}]
            pa['content'] = rel(p['article_md']).read_text() if p.get('content_inline') else ''
        elif p['slot'] == 'wechat':
            cover = upload(rel(p['cover']), cache)
            content = rel(p['wechat_html']).read_text()
            art = {'title': p['title'], 'content': content, 'cover': {'key': cover['key'], 'raw': cover}, 'type': p.get('original', 1),
                   'digest': p.get('digest', '')[:120], 'quickRepost': 1}
            # 10-16 用户：「原创都声明」（type=1）；声明原创要带作者名
            art['authorName'] = (p.get('author') or '示例作者')[:8]
            src = p.get('source_url', acc.get('source_url'))   # 「阅读原文」，默认挂示例服务 web.provider.cn；post.json 写 "source_url": "" 可关掉
            if src:
                art['contentSourceUrl'] = src
            pa['cover'] = cover
            pa['coverKey'] = cover['key']
            pa['accountForms'] = [{'platformAccountId': acc['account_id']}]
            pa['platformForms'] = {plat: {'articles': [art], 'notifySubscribers': 0, 'pubType': 1, **sched}}
    finally:
        cache_p.write_text(dump(cache))
    out = post_path.with_name(post_path.stem + '.payload.json')
    out.write_text(dump(o))
    return out, ('native' if native else 'dispatch')


if __name__ == '__main__':
    out, mode = build(sys.argv[1])
    print(json.dumps({'payload': str(out), 'mode': mode}, ensure_ascii=False))
