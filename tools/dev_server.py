#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地开发服务器：为静态文件加 no-cache 头。
用途：改 index.html 后浏览器立即拿到新版，避免启发式缓存导致看到旧页面。
用法：python3 tools/dev_server.py [端口]   # 默认 8901
"""
import http.server
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8901


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, fmt, *args):
        print(fmt % args)


if __name__ == '__main__':
    http.server.ThreadingHTTPServer(('127.0.0.1', PORT), NoCacheHandler).serve_forever()
