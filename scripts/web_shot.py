#!/usr/bin/env python3
"""网页截图（给视频的 screen 场景当真实素材：官方公告、新闻原文、产品页面）。

用无头 Chromium（Playwright）打开网页，等加载完截图；可以只截某个元素，也可以顺便把页面文字存下来核对事实。
截图里如果出现个人信息（用户名、头像、手机号），放进视频前要打码。

用法:
  .venv/bin/python scripts/web_shot.py <url> <out.png> [--selector CSS] [--width 1200] [--height 900]
                                       [--full] [--wait 2.5] [--text out.txt] [--scroll-to 文字]
  --selector   只截这个元素（如公告正文 article）
  --scroll-to  先滚到包含这段文字的位置再截（截长页面里的某一段）
  --text       把页面可见文字写到文件，方便核对数字和原话
"""
import argparse, pathlib, sys, time


def shot(url, out, selector=None, width=1200, height=900, full=False, wait=2.5, text=None, scroll_to=None):
    from playwright.sync_api import sync_playwright
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': width, 'height': height}, device_scale_factor=2, locale='zh-CN',
                        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36')
        pg.goto(url, wait_until='networkidle', timeout=60000)
        time.sleep(wait)
        if scroll_to:
            pg.get_by_text(scroll_to, exact=False).first.scroll_into_view_if_needed()
            time.sleep(0.5)
        if text:
            pathlib.Path(text).write_text(pg.inner_text('body'))
        if selector:
            pg.locator(selector).first.screenshot(path=str(out))
        else:
            pg.screenshot(path=str(out), full_page=full)
        b.close()
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('out')
    ap.add_argument('--selector')
    ap.add_argument('--width', type=int, default=1200)
    ap.add_argument('--height', type=int, default=900)
    ap.add_argument('--full', action='store_true')
    ap.add_argument('--wait', type=float, default=2.5)
    ap.add_argument('--text')
    ap.add_argument('--scroll-to')
    a = ap.parse_args()
    print(shot(a.url, a.out, a.selector, a.width, a.height, a.full, a.wait, a.text, a.scroll_to))
