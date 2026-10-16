#!/usr/bin/env python3
"""给内置浏览器传本地图片用的临时图片服务（只监听 127.0.0.1，只读，只放行图片后缀）。

用户 2026-10-16 授权：内置浏览器可以上传本地图片。浏览器里的网页（知乎、公众号后台等）
用 fetch('http://127.0.0.1:<port>/<文件名>') 取图，再交给网站自己的上传控件。

用法: .venv/bin/python scripts/serve_images.py <图片目录> [--port 8765]
      用完 Ctrl+C 或 kill 掉；不要长期开着。
"""
import argparse, http.server, pathlib, socketserver, sys

ALLOWED = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}


def make_handler(root):
    root = pathlib.Path(root).resolve()

    class H(http.server.BaseHTTPRequestHandler):
        def _cors(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.send_header('Access-Control-Allow-Private-Network', 'true')

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self):
            name = pathlib.PurePosixPath(self.path.split('?')[0]).name  # 只取文件名，不允许子路径/..
            p = root / name
            if not name or p.suffix.lower() not in ALLOWED or not p.is_file():
                self.send_response(404)
                self._cors()
                self.end_headers()
                return
            data = p.read_bytes()
            ctype = {'.png': 'image/png', '.gif': 'image/gif', '.webp': 'image/webp'}.get(p.suffix.lower(), 'image/jpeg')
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt, *args):
            sys.stderr.write('[serve_images] ' + fmt % args + '\n')

    return H


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--port', type=int, default=8765)
    a = ap.parse_args()
    with socketserver.TCPServer(('127.0.0.1', a.port), make_handler(a.root)) as s:
        print(f'serving {pathlib.Path(a.root).resolve()} on http://127.0.0.1:{a.port}', flush=True)
        s.serve_forever()
