#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""滚动加载原型实测（只读：不改页面、不碰 git）

复现 2026-10-10「滚动加载 vs 现状」对比（详见 docs/DECISION_LOG.md 同日条目）。
方法：在浏览器内把页面 renderCards 替换为「首屏 30 张 + IntersectionObserver 哨兵、
滚近底部 800px 预加载、每批 30 张」的滚动加载版，与现状（全量渐进渲染）同环境对比。
模拟：390x844 / 3x DPR / CPU×4 / 网络节流，本地 gzip 服务。

跑法：cd query && python3 tools/mobile_scroll_proto.py

输出：
    V1/V2 切卡片首屏耗时、滚动 50 屏后的 DOM 节点与帧间隔、批量追加成本。
"""
import gzip, http.server, socketserver, threading, time, os

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'index.html')
HTML = open(PAGE, 'rb').read()
GZ = gzip.compress(HTML)

class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ('/', '/index.html'):
            self.send_error(404); return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Encoding', 'gzip')
        self.send_header('Content-Length', str(len(GZ)))
        self.end_headers()
        self.wfile.write(GZ)
    def log_message(self, *a): pass

SCROLL_OVERRIDE = """
window.__scToken = 0; window.__scIO = null; window.__appends = [];
window.renderCards = function(rows){
  var list = document.getElementById('list');
  if (!rows || !rows.length) { if (list) list.innerHTML = emptyHtml(); return; }
  var FIRST = 30, CHUNK = 30, i = FIRST;
  list.innerHTML = cardHtml(rows.slice(0, FIRST), 0);
  var io = new IntersectionObserver(function(entries){
    if (!entries[0].isIntersecting) return;
    if (i >= rows.length) { io.disconnect(); return; }
    var t0 = performance.now();
    var frag = document.createElement('div');
    frag.innerHTML = cardHtml(rows.slice(i, i + CHUNK), i);
    while (frag.firstChild) list.appendChild(frag.firstChild);
    i += CHUNK;
    window.__appends.push({ to: i, ms: performance.now() - t0 });
  }, { root: null, rootMargin: '800px' });
  window.__scIO = io;
  var sentinel = document.createElement('div');
  sentinel.id = 'sc-sentinel'; sentinel.style.height = '2px';
  list.appendChild(sentinel);
  io.observe(sentinel);
};
void 0;
"""

def main():
    srv = socketserver.TCPServer(('127.0.0.1', 8914), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={'width': 390, 'height': 844}, device_scale_factor=3,
            is_mobile=True, has_touch=True,
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
                       'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        )
        page = ctx.new_page()
        cdp = ctx.new_cdp_session(page)
        cdp.send('Network.enable')
        cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
        cdp.send('Network.emulateNetworkConditions', {
            'offline': False, 'latency': 50, 'downloadThroughput': 5*1024*1024, 'uploadThroughput': 5*1024*1024})
        page.goto('http://localhost:8914/index.html', wait_until='load', timeout=120000)
        page.evaluate(SCROLL_OVERRIDE)

        def run_variant(name, no_anim):
            if no_anim:
                page.add_style_tag(content=".card{animation:none!important}")
            page.evaluate("window.__appends=[]")
            t0 = time.time()
            page.click('#v-card')
            page.wait_for_function("document.querySelectorAll('#list .card').length >= 30", timeout=30000)
            first = int((time.time() - t0) * 1000)
            page.evaluate("""() => { window.__frames=[]; let last=performance.now();
                const s=t=>{window.__frames.push(t-last);last=t;requestAnimationFrame(s)}; requestAnimationFrame(s);}""")
            page.evaluate("""() => new Promise(res => { let y=0;
                const step=()=>{ y+=400; window.scrollTo(0, y); if(y<17000) requestAnimationFrame(step); else res(); };
                requestAnimationFrame(step); })""")
            fr = sorted(page.evaluate("window.__frames.slice(0,200)"))
            p50, p95 = fr[len(fr)//2], fr[int(len(fr)*0.95)]
            st = page.evaluate("""() => ({cards: document.querySelectorAll('#list .card').length,
                nodes: document.getElementsByTagName('*').length})""")
            print(f"[{name}] 首屏30张 {first}ms | 滚50屏后 {st['cards']} 张 / {st['nodes']:,} 节点 | "
                  f"帧 p50={p50:.1f}ms p95={p95:.1f}ms")
            page.click('#v-table'); page.wait_for_timeout(200)

        print("=== 滚动加载原型 vs 现状（CPU×4） ===")
        run_variant("V1 滚动加载·有动画", False)
        page.reload(wait_until='load')
        page.evaluate(SCROLL_OVERRIDE)
        run_variant("V2 滚动加载·无动画", True)

        # 批量追加成本（滚到底循环）
        page.evaluate(SCROLL_OVERRIDE)
        page.click('#v-card'); page.wait_for_timeout(300)
        for _ in range(10):
            page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
            time.sleep(1.0)
        st = page.evaluate("""() => ({cards: document.querySelectorAll('#list .card').length,
            appends: window.__appends})""")
        ms = [a['ms'] for a in st['appends']]
        print(f"批量追加: {len(ms)} 批, 每批30张耗时 {[round(m,1) for m in ms]}, 均值 {sum(ms)/len(ms) if ms else 0:.1f}ms")
        browser.close()
    srv.shutdown()

if __name__ == '__main__':
    main()
