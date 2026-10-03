#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成查询页附加费规则 JS 常量（路径 A：规则数据内嵌 index.html）。

流程：读 parser/structure/surcharge-v2/v2_mapping_61.json → 逐条 build_trigger
预构造 trigger（JS 端不重复实现 build_trigger，减少移植风险）→ 序列化为
window.__FBA_SURCHARGE_RULES__ = [...] 内嵌进 query/index.html 的 <script> 区。

用法：python3 tools/gen_surcharge_js.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

QUERY = Path(__file__).resolve().parent.parent          # fba-rate/query/
REPO = QUERY.parent                                     # fba-rate/
PARSER = REPO / "parser"
SRC = PARSER / "structure" / "surcharge-v2" / "v2_mapping_61.json"
INDEX = QUERY / "index.html"

START_MARK = "/* ===== 附加费规则数据（由 gen_surcharge_js.py 生成，勿手改）===== */"
END_MARK = "/* ===== /附加费规则数据 ===== */"


def build_trigger_js_compat(rule):
    """JS 端 evaluate 需要 trigger；这里复用 parser 的 rule_engine.build_trigger。
    目录名带连字符（surcharge-v2）不能包导入，用 importlib 按文件路径加载。"""
    import importlib.util
    eng = PARSER / "structure" / "surcharge-v2" / "rule_engine.py"
    spec = importlib.util.spec_from_file_location("rule_engine", eng)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_trigger(rule)


def main():
    if not SRC.exists():
        print(f"缺规则源文件：{SRC}"); return 1
    rules = json.loads(SRC.read_text(encoding="utf-8"))
    for r in rules:
        r["trigger"] = build_trigger_js_compat(r)
    body = json.dumps(rules, ensure_ascii=False, separators=(",", ":"))
    js = f"{START_MARK}\nwindow.__FBA_SURCHARGE_RULES__ = {body};\n{END_MARK}\n"

    src = INDEX.read_text(encoding="utf-8")
    if START_MARK in src:
        # 已存在则替换旧块（保留第一个标记到结束标记之间的内容）
        pat = re.compile(re.escape(START_MARK) + r".*?" + re.escape(END_MARK), re.S)
        src, n = pat.subn(js, src)
        if n != 1:
            print(f"标记块匹配异常：n={n}"); return 1
        print(f"已更新规则块（{len(rules)} 条）")
    else:
        anchor = "<script>\n"
        if anchor not in src:
            print("找不到 <script> 锚点"); return 1
        src = src.replace(anchor, anchor + "\n" + js, 1)
        print(f"已插入规则块（{len(rules)} 条）")

    INDEX.write_text(src, encoding="utf-8")
    print(f"完成：{INDEX}（{len(js)//1024} KB 规则数据）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
