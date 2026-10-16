#!/usr/bin/env python3
"""发后核对封面：平台上实际显示的封面，是不是我们做的那张（10-16 视频号 09:00 那条发出去是视频第 1 帧，没人发现）。

用法：
  .venv/bin/python scripts/covers/cover_check.py <我们的封面.jpg> <平台封面图地址或文件> [更多地址...]
  平台封面图地址：视频号助手作品列表 / 修改封面页的 img.src（finder.video.qq.com）、抖音作品管理的封面背景图、
  小红书笔记管理的 .media-bg 背景图等，都能直接下载。

两张图统一裁成 3:4 再缩成小图比较（dHash 汉明距离 + 灰度平均差）。距离 ≤ 12 判「是这张」，否则「不是」并退出码 1。
平台会压缩、转 webp、改尺寸，这些都不影响判断；视频帧和我们的设计图差得很远，一眼能分开。
"""
import io, sys, urllib.request
from PIL import Image


def load(src):
    if src.startswith('http'):
        req = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0',
                                                   'Referer': 'https://channels.weixin.qq.com/'})
        return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())).convert('RGB')
    return Image.open(src).convert('RGB')


def crop34(im):
    w, h = im.size
    if w / h > 3 / 4:
        nw = int(h * 3 / 4)
        return im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    nh = int(w * 4 / 3)
    return im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))


def dhash(im, n=8):
    g = crop34(im).convert('L').resize((n + 1, n), Image.LANCZOS)
    px = list(g.tobytes())
    return [px[r * (n + 1) + c] > px[r * (n + 1) + c + 1] for r in range(n) for c in range(n)]


def gray_diff(a, b):
    ga = list(crop34(a).convert("L").resize((12, 16)).tobytes())
    gb = list(crop34(b).convert("L").resize((12, 16)).tobytes())
    return sum(abs(x - y) for x, y in zip(ga, gb)) / len(ga)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    ref = load(sys.argv[1])
    hr = dhash(ref)
    bad = 0
    for src in sys.argv[2:]:
        try:
            im = load(src)
        except Exception as ex:
            print(f'下载失败  {src[:80]}  {ex}')
            bad += 1
            continue
        dist = sum(x != y for x, y in zip(hr, dhash(im)))
        ok = dist <= 12
        bad += not ok
        print(f'{"是这张" if ok else "不是!!"}  距离 {dist:2d}/64  灰度差 {gray_diff(ref, im):5.1f}  {src[:80]}')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
