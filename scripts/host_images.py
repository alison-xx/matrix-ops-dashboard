#!/usr/bin/env python3
"""把 HTML 里引用的本地图片上传到蚁小二图床，并替换成可访问的 https 地址（公众号正文插图用）。
用法: .venv/bin/python scripts/host_images.py <content.html>   -> 原地改写，打印替换清单
图片文件名必须唯一（蚁小二按文件名生成 key，同名会覆盖）。
"""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import yxer

BASE = 'https://media.example.com/example.png'


def main(path):
    p = pathlib.Path(path).resolve()
    html = p.read_text()
    done = {}
    for src in re.findall(r'<img[^>]+src="([^"]+)"', html):
        if src.startswith('http') or src in done:
            continue
        f = (p.parent / src).resolve()
        if not f.exists():
            raise SystemExit(f'图片不存在: {f}')
        rc, o = yxer('upload', str(f), timeout=300)
        if rc or not o.get('ok'):
            raise SystemExit(f'上传失败 {f}: {json.dumps(o, ensure_ascii=False)[:300]}')
        done[src] = BASE + o['data']['key']
    for a, b in done.items():
        html = html.replace(f'src="{a}"', f'src="{b}"')
    p.write_text(html)
    print(json.dumps(done, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
