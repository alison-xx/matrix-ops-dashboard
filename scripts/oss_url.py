#!/usr/bin/env python3
"""把本地图片传到蚁小二图床，打印公网地址（给内置浏览器上传图片用）。

用户 2026-10-16 授权内置浏览器上传本地图片。知乎等页面拦截对本机地址的请求、模拟 ⌘V 读不到系统剪贴板，
所以走：本地图 -> 蚁小二图床（https://media.example.com/example.png<key>）-> 页面里 fetch（必须 referrerPolicy:'no-referrer'，
否则图床防盗链返回 HTML）-> 做成 File -> 在编辑器上派发 paste 事件，由网站自己上传到它的图床。
蚁小二按文件名生成 key，文件名要带日期前缀且唯一。

用法: .venv/bin/python scripts/oss_url.py <图片...>     -> 每行一个 URL
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import yxer

BASE = 'https://media.example.com/example.png'

# 浏览器里用的 JS（把 URLS 换成本脚本打印的地址；先把光标点到编辑器里要插图的位置）
PASTE_JS = """
const URLS = [/* 'https://media.example.com/example.png' */];
const ed = document.querySelector('.public-DraftEditor-content') || document.activeElement;
const before = ed.querySelectorAll('img').length;
for (const u of URLS) {
  const b = await (await fetch(u, {referrerPolicy: 'no-referrer', credentials: 'omit'})).blob();
  const f = new File([b], u.split('/').pop(), {type: b.type || 'image/jpeg'});
  const dt = new DataTransfer(); dt.items.add(f);
  ed.focus();
  ed.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
  await new Promise(r => setTimeout(r, 6000));
}
({added: ed.querySelectorAll('img').length - before})
"""

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] == '--js':
        print(PASTE_JS)
        sys.exit(0)
    for f in sys.argv[1:]:
        rc, o = yxer('upload', str(pathlib.Path(f).resolve()), timeout=300)
        if rc or not o.get('ok'):
            sys.exit(f'上传失败 {f}: {o}')
        print(BASE + o['data']['key'])
