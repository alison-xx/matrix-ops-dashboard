#!/usr/bin/env python3
"""视频里的「示例作者表情贴纸」图层（10-16 用户：用自己头像做的表情包复用到矩阵）。

素材：assets/stickers/creator/（index.json 列出 24 个表情和适用场景，png1024 是透明底立绘，图上自带大字）。
用法：在 spec 的某个场景里写
    "sticker": "我悟了"                       # 表情名或编号（"10"），场景开始后 0.4 秒弹出，停 2 秒
    "sticker": {"name": "震惊", "at": 1.2, "dur": 1.8}   # at=场景内第几秒弹出，dur=停多久
位置（用户 10-16：人物不要挡到字）：贴纸不另占位置，借用口播小人的区域（avatar_layer 的 AV_LEFT/AV_TOP/AV_SIZE，字幕下方左下角），
贴纸出现时小人 #av 淡出、贴纸弹出、结束再换回小人；画面上同一时间只有一个示例作者，永远不压字幕和正文。
没开口播小人（spec "avatar": false）时不放贴纸，只打印提示（那时字幕在原位，左下角会压字）。
cta/片尾场景不放贴纸，贴纸也要在片尾开始前收掉（B站会话 10-16：片尾 #av 会被移到画面中间放大，淡出淡回会打架）。
#av-sym（小人头部右侧的表情符号）和 #av 一起让位。
用静态 PNG + GSAP 弹出/晃动，不用 GIF（渲染是逐帧截图，GIF 不按时间轴走）。
一条视频 1–3 个就够，放在钩子反应、结论/反转、结尾这类节点；内容和表情要对得上（见 运营手册/表情包.md）。
"""
import json, pathlib, shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
IDX = ROOT / 'assets/stickers/creator/index.json'

try:  # 和口播小人共用同一块区域，常量以 avatar_layer 为准（另一个会话在维护它）
    from avatar_layer import AV_LEFT, AV_TOP, AV_SIZE
except Exception:
    AV_LEFT, AV_TOP, AV_SIZE = 10, 1338, 320

STK_H = AV_SIZE + 20                     # 立绘是竖图（约 1:2），高度和小人区域一致
CSS = (f".clip.stk-clip{{position:absolute;inset:auto;left:{AV_LEFT}px;right:auto;top:{AV_TOP - 10}px;width:{AV_SIZE}px;height:{STK_H}px;"
       "z-index:30;pointer-events:none}"  # .clip 默认 inset:0，必须重置
       ".clip.stk-clip .stk{width:100%;height:100%;object-fit:contain;object-position:50% 100%;transform-origin:50% 100%;"
       "filter:drop-shadow(0 10px 22px rgba(0,0,0,.6))}")


def _find(items, key):
    key = str(key).strip()
    for it in items:
        if key in (it['id'], it['name'], f"{it['id']}_{it['name']}") or key.lstrip('0') == it['id'].lstrip('0'):
            return it
    return None


def build_stickers(spec, work):
    """返回 {'html','css','js'}；没有场景用贴纸就返回 None。"""
    if not IDX.exists():
        return None
    if spec.get('avatar') is False:
        if any(sc.get('sticker') for sc in spec['scenes']):
            print('[贴纸] 这条关了口播小人，贴纸没有不挡字的位置，已跳过（规则：人物不要挡到字）')
        return None
    items = json.loads(IDX.read_text())['items']
    html, js = [], []
    last = spec['scenes'][-1]
    ec_at = last['_start'] if last.get('type') in ('cta', 'endcard') else None   # 片尾开始时间（avatar_layer 同口径）
    for i, sc in enumerate(spec['scenes']):
        st = sc.get('sticker')
        if not st:
            continue
        if sc.get('type') in ('cta', 'endcard'):
            print(f'[贴纸] 场景{i} 是 cta/片尾，小人要挪到中间做片尾，跳过贴纸')
            continue
        cfg = st if isinstance(st, dict) else {'name': st}
        it = _find(items, cfg.get('name', ''))
        if not it:
            print(f'[贴纸] 场景{i} 找不到表情「{cfg.get("name")}」，跳过（可选：{"、".join(x["name"] for x in items)}）')
            continue
        dst = work / 'assets' / f'stk{i}.png'
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(it['png1024'] if pathlib.Path(it['png1024']).is_absolute() else ROOT / it['png1024'], dst)
        s0, e0 = sc['_start'], sc['_end']
        start = min(s0 + float(cfg.get('at', 0.4)), max(s0, e0 - 0.8))
        dur = min(float(cfg.get('dur', 2.0)), max(0.8, e0 - start))
        if ec_at is not None and start + dur > ec_at - 0.3:
            dur = ec_at - 0.3 - start
            if dur < 0.8:
                print(f'[贴纸] 场景{i} 离片尾太近，跳过')
                continue
        html.append(f'<div id="k{i}" class="clip stk-clip" data-start="{start:.3f}" data-duration="{dur:.3f}" data-track-index="5">'
                    f'<img class="stk" src="assets/{dst.name}" alt="{it["name"]}"></div>')
        js.append(f'tl.to("#av,#av-sym",{{opacity:0,duration:.15}},{start - .05:.3f});')   # 小人和头顶符号一起让位
        js.append(f'tl.to("#av,#av-sym",{{opacity:1,duration:.2}},{start + dur:.3f});')
        js.append(f'tl.fromTo("#k{i} .stk",{{scale:0,rotation:-22,opacity:0}},{{scale:1,rotation:0,opacity:1,duration:.34,ease:"back.out(2.6)"}},{start:.3f});')
        js.append(f'tl.to("#k{i} .stk",{{rotation:6,duration:.22,yoyo:true,repeat:3,ease:"sine.inOut"}},{start + .4:.3f});')
        js.append(f'tl.to("#k{i} .stk",{{scale:0,opacity:0,duration:.18,ease:"power2.in"}},{start + dur - .2:.3f});')
    if not html:
        return None
    return {'html': '\n'.join(html), 'css': CSS, 'js': '\n'.join(js)}
