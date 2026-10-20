#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""移动端卡片模式性能测试（只读：不改页面、不碰 git）

用途：复现 2026-10-10 的移动端卡片模式性能实测（详见 docs/DECISION_LOG.md 同日条目）。
模拟：390x844 手机视口 / 3x DPR / 触屏 / CPU×4 节流 / 网络节流(150ms RTT, 1.6Mbps)，
本地 gzip 服务模拟 GitHub Pages 传输。

跑法：
    cd query && python3 tools/mobile_perf_test.py

输出三组数字：
    1) 首屏加载（传输+JSON 解析+脚本执行）
    2) 切卡片视图·无筛选（全量可见记录）：点击响应 / 首屏 N 张（页面 CARD_FIRST 常量）/ 首屏稳定 / DOM 节点 / 滚动帧间隔
    3) 精确搜索小结果集（如「美国空运」~90 条）：渲染耗时 + 滚动手感 —— 作为「优化后预期」参照

2026-10-10 实测结论（CPU×4 下）：全量 10599 张卡 ≈33~41s 完成、49 万 DOM 节点、滚动 p95 掉帧；
小结果集 90 张 0.25s、滚动满帧 16.7ms —— 瓶颈在「无筛选全量渲染」，不在卡片组件本身。
"""
import gzip, http.server, socketserver, threading, time, sys, os

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

def main():
    srv = socketserver.TCPServer(('127.0.0.1', 8905), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"[serve] gzip 传输 {len(GZ)/1048576:.2f} MB（原始 {len(HTML)/1048576:.2f} MB）")

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
            'offline': False, 'latency': 150, 'downloadThroughput': 200*1024, 'uploadThroughput': 100*1024})
        page.add_init_script("""
            window.__longTasks = [];
            try { new PerformanceObserver(l => { for (const e of l.getEntries())
                window.__longTasks.push({start:e.startTime, dur:e.duration}); })
                .observe({type:'longtask', buffered:true}); } catch(e){}
        """)

        T0 = time.time()
        page.goto('http://localhost:8905/index.html', wait_until='load', timeout=120000)
        load_ms = int((time.time() - T0) * 1000)
        nav = page.evaluate("""() => { const n = performance.getEntriesByType('navigation')[0] || {};
            return {di: Math.round(n.domInteractive||0), dcl: Math.round(n.domContentLoadedEventEnd||0),
                    le: Math.round(n.loadEventEnd||0), ts: n.transferSize||0}; }""")
        data = page.evaluate("""() => ({records: window.__FBA_DATA__.length,
            visible: (typeof VISIBLE!=='undefined' && VISIBLE) ? VISIBLE.length : -1})""")

        def switch_cards_and_measure(label):
            firstN = page.evaluate("(typeof CARD_FIRST!=='undefined')?CARD_FIRST:60")  # 页面滚动加载首屏常量
            t0 = time.time()
            page.click('#v-card')
            click_ms = int((time.time() - t0) * 1000)
            page.wait_for_function(f"document.querySelectorAll('#list .card').length >= {firstN}", timeout=30000)
            firstN_ms = int((time.time() - t0) * 1000)
            last_c, done = -1, False
            for _ in range(500):
                c = page.evaluate("document.querySelectorAll('#list .card').length")
                time.sleep(0.08)
                if c == last_c and c > 0: done = True; break
                last_c = c
            total = int((time.time() - t0) * 1000)
            info = page.evaluate("""() => { const lt = (window.__longTasks||[]).filter(x=>x.start>0);
                return {cards: document.querySelectorAll('#list .card').length,
                        nodes: document.getElementsByTagName('*').length,
                        lt: lt.length, ltms: Math.round(lt.reduce((s,x)=>s+x.dur,0))}; }""")
            # 卡片视图现为滚动加载：首屏 firstN 张即稳定，剩余随滚动追加，无「全量完成」概念
            print(f"[{label}] 点击响应 {click_ms}ms / 首屏{firstN}张 {firstN_ms}ms / 首屏稳定 {total}ms | "
                  f"{info['cards']} 张 / {info['nodes']:,} 节点 / longtask {info['lt']} 个 累计 {info['ltms']/1000:.1f}s")

        def scroll_stats(dist):
            page.evaluate("""() => { window.__frames=[]; let last=performance.now();
                const s=t=>{window.__frames.push(t-last);last=t;requestAnimationFrame(s)}; requestAnimationFrame(s);}""")
            page.evaluate(f"""() => new Promise(res => {{ let y=0;
                const step=()=>{{ y+=400; window.scrollTo(0, y); if(y<{dist}) requestAnimationFrame(step); else res(); }};
                requestAnimationFrame(step); }})""")
            fr = sorted(page.evaluate("window.__frames.slice(0,200)"))
            return fr[len(fr)//2], fr[int(len(fr)*0.95)], fr[int(len(fr)*0.99)]

        print("\n— 首屏加载 —")
        print(f"  整页加载(传输+解析+执行): {load_ms} ms | domInteractive {nav['di']}ms / dcl {nav['dcl']}ms / load {nav['le']}ms / 传输 {nav['ts']//1024}KB")
        print(f"  数据: {data['records']} 条 / 可见 {data['visible']}")

        print("\n— 切卡片视图·无筛选（全量可见记录） —")
        switch_cards_and_measure("全量·有动画")
        s = scroll_stats(9000)
        print(f"  滚动 9000px: 帧间隔 p50={s[0]:.1f}ms p95={s[1]:.1f}ms p99={s[2]:.1f}ms（>16.7ms 掉帧）")

        print("\n— 精确搜索小结果集（优化后参照） —")
        page.click('#f-toggle'); page.wait_for_timeout(150)
        page.fill('#f-q', '美国空运'); page.wait_for_timeout(600)
        switch_cards_and_measure("搜索·~90条")
        s2 = scroll_stats(3000)
        print(f"  滚动 3000px: 帧间隔 p50={s2[0]:.1f}ms p95={s2[1]:.1f}ms p99={s2[2]:.1f}ms")

        browser.close()
    srv.shutdown()

if __name__ == '__main__':
    main()
