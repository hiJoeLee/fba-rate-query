#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""golden 对照：查询页 JS 求值器 vs Python rule_engine（同输入同金额）。

用途：A（纯前端）→ B（后端服务）迁移验收。任一侧改规则/求值语义后，
先跑本脚本：366 条（6 组输入 × 61 条规则）状态与金额必须 0 差异。

用法：
  python3 golden_calc.py            # 用 tools/golden_input.json 的 6 组默认输入
  python3 golden_calc.py 输入.json  # 自定义输入（结构见 golden_input.json）

依赖：node（页面 JS 求值器）、parser 仓 rule_engine.py / v2_mapping_61.json。
"""
import json, re, subprocess, sys, tempfile, os
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUERY_ROOT = HERE.parent
PARSER = Path('/Users/Zhuanz1/Documents/trae_projects/fba-rate/parser/structure/surcharge-v2')
INDEX = QUERY_ROOT / 'index.html'

def fail(msg):
    print('错误:', msg); sys.exit(1)

def run(cmd):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if p.returncode != 0:
        fail(p.stderr[-800:])
    return p.stdout

def main():
    inputs_file = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'golden_input.json'
    inputs = json.load(open(inputs_file, encoding='utf-8'))
    tmp = Path(tempfile.mkdtemp(prefix='golden_'))

    # 1) Python 端：rule_engine 对每组输入求值
    py_script = tmp / 'py.py'
    py_script.write_text(f"""import json, sys
sys.path.insert(0, {str(PARSER)!r})
from rule_engine import build_trigger, evaluate_rule
rules = json.load(open({str(PARSER / 'v2_mapping_61.json')!r}, encoding='utf-8'))
for r in rules: r['trigger'] = build_trigger(r)
inputs = json.load(open({str(inputs_file)!r}, encoding='utf-8'))
out = [{{'name': inp['name'], 'items': [
    {{'name': r['name'], 'status': evaluate_rule(r, inp['goods'], inp['order'])['status'],
      'amount': evaluate_rule(r, inp['goods'], inp['order'])['amount']}} for r in rules]}}
    for inp in inputs]
json.dump(out, open({str(tmp / 'py.json')!r}, 'w', encoding='utf-8'), ensure_ascii=False)
""", encoding='utf-8')
    run(f"python3 {py_script}")

    # 2) JS 端：提取页面求值器 + 内嵌规则数据，node 求值
    src = INDEX.read_text(encoding='utf-8')
    body = src[src.index('function scField'):src.index('/* ── 主运费：档位 × 计费量 + 利润加价（复用 markupOf） ── */')].rstrip()
    m = re.search(r'window\.__FBA_SURCHARGE_RULES__ = (\[.*?\]);', src, re.S)
    if not m: fail('index.html 未找到 __FBA_SURCHARGE_RULES__')
    (tmp / 'src.json').write_text(m.group(1), encoding='utf-8')
    runner = tmp / 'run.js'
    runner.write_text(f"""const SRC = require({str(tmp / 'src.json')!r});
const inputs = require({str(inputs_file)!r});
const out = inputs.map(inp => {{
  return {{name: inp.name, items: SRC.map(r => {{
    const e = scEvalRule(r, inp.goods, inp.order);
    return {{name: r.name, status: e.status, amount: e.amount}};
  }})}};
}});
console.log(JSON.stringify(out));""", encoding='utf-8')
    (tmp / 'all.js').write_text(body + '\n' + runner.read_text(), encoding='utf-8')
    js_json = run(f"node {tmp / 'all.js'}")
    js = json.loads(js_json)
    py = json.load(open(tmp / 'py.json', encoding='utf-8'))

    # 3) 对照
    fails = []
    for p, j in zip(py, js):
        for a, b in zip(p['items'], j['items']):
            if a['name'] != b['name']:
                fails.append(f"{p['name']}: 顺序错"); continue
            if a['status'] != b['status'] or abs((a['amount'] or 0) - (b['amount'] or 0)) > 0.001:
                fails.append(f"{p['name']} | {a['name']}: py={a['status']}/{a['amount']} js={b['status']}/{b['amount']}")
    total = len(py) * len(py[0]['items'])
    print(f"golden 对照：{len(py)} 组输入 × {len(py[0]['items'])} 条规则 = {total} 条")
    if fails:
        print(f"不一致 {len(fails)} 条：")
        for f in fails[:40]: print('  ', f)
        sys.exit(1)
    print("0 差异 —— JS 求值器与 Python rule_engine 同输入同金额 ✓")

if __name__ == '__main__':
    main()
