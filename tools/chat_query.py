#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对话式查价：在现有 `__FBA_DATA__` 上做结构化检索，回给对话用。

【定位】方式 A 的工作台 —— 读取查询页内嵌数据，按字段组合过滤并回报价。
**只读**：不写任何产物、不改页面、不碰 git。

【数据来源】`../index.html` 里的 `window.__FBA_DATA__`（页端的唯一数据源），
不是解析端产物 —— 因此看到的就是客户看到的。**利润层 `__FBA_MARKUP__` 不参与**：
本工具只回成本价（与页面表格里的基础数值一致），要含利润的展示值看页面。

【用法】
    python3 tools/chat_query.py                                  # 全部（按 limit 截断）
    python3 tools/chat_query.py 国家=美国 渠道=海卡
    python3 tools/chat_query.py 供应商=皓鹏 来源表=美国空运 单位=KG
    python3 tools/chat_query.py 城市=义乌 包税=是 limit=5
    python3 tools/chat_query.py 重量档=21KG+

参数（除 `单位` 为精确相等，其余均为**包含**匹配、大小写不敏感）：
    国家 供应商 来源表 渠道 运输 货型 包税 货币 —— 对同名字段
      注：`供应商` 实际比对的是记录里的 `供应商代码`
    城市   —— 对 `可收货城市`（数组）逐项子串匹配，与页端「包含」口径一致
    单位   —— 精确相等（`KG` / `CBM` / `件`）
    重量档 —— 只保留 `价格` 里**含该档位名**的记录（精确匹配档位名，如 `21KG+`）
    limit  —— 展示**组数**上限（默认 10）

【已知参数外的口径】**所有**传入的键必须真实存在，拼错会直接报错（不静默忽略）。

【归并口径】按 `供应商代码 / 来源表名 / 渠道名称 × 单位 × 区间` 归并成一行 ——
- 同一条价在页端会按「来源行号」拆成多条记录，逐条打印会淹没答案，故归并；
- 但**「单位 × 区间」必须进归并键**：同一渠道名可能同时有 KG 与 CBM 两条
  （实测 50 组跨区间、含单位分叉），只按渠道名归并会**静默少给**一半的价；
- 同组的 `价格` 会因**邮编段 / 时效**分叉（实测 337/389 组不一致），故逐档位取
  `最小~最大`，而不是只取第一条；数值相同时打印单值。行末 `〔N 条〕` 给出
  被归并的原始记录数 —— 让"归并"这件事**可见**，不悄悄丢。

【价格格式】与页端 `fmtPrice()` 同口径（整数带千分位；非整数先保留 2 位再去尾零）。
页端另有 `fmtFull()` 在 `title` 里给**精确值**（如 `8.51096022241232`），
本工具面向对话可读性，不打印那个尾巴；要精确值请读页面悬停或直接看 `__FBA_DATA__`。
"""
import collections
import json
import os
import sys

HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.html")

DATA_KEY = "window.__FBA_DATA__ = "


def load_data(path=None):
    """取页面里的 `window.__FBA_DATA__`（按 JSON 边界解析，不整文件 `json.loads`）。"""
    p = os.path.abspath(path or HTML)
    with open(p, encoding="utf-8") as f:
        html = f.read()
    i = html.find(DATA_KEY)
    if i < 0:
        sys.exit(f"!! 页面里找不到 {DATA_KEY!r}：{p}")
    data, _ = json.JSONDecoder().raw_decode(html[i + len(DATA_KEY):])
    return data


def norm(s):
    return str(s or "").strip()


def contains(field_val, needle):
    """对渠道名 / 收货地 / 仓库等的包含匹配（大小写不敏感）。"""
    return needle.lower() in norm(field_val).lower()


def query(data, *, 国家=None, 供应商=None, 来源表=None, 渠道=None, 运输=None,
          货型=None, 包税=None, 单位=None, 城市=None, 重量档=None, 货币=None):
    """按字段组合过滤，返回原始记录列表（不做归并、不截断 —— 那是 `report()` 的事）。"""
    out = []
    for r in data:
        if 国家 and not contains(r.get("国家"), 国家): continue
        if 供应商 and not contains(r.get("供应商代码"), 供应商): continue
        if 来源表 and not contains(r.get("来源表名"), 来源表): continue
        if 渠道 and not contains(r.get("渠道名称"), 渠道): continue
        if 运输 and not contains(r.get("运输方式"), 运输): continue
        if 货型 and not contains(r.get("货物类型"), 货型): continue
        if 包税 and not contains(r.get("是否包税"), 包税): continue
        if 货币 and not contains(r.get("货币"), 货币): continue
        if 单位 and norm(r.get("单位")) != 单位: continue
        if 城市 and not any(城市 in norm(c) for c in (r.get("可收货城市") or [])): continue
        if 重量档 and 重量档 not in (r.get("价格") or {}): continue
        out.append(r)
    return out


# ---------------------------------------------------------------------------
# 展示层
# ---------------------------------------------------------------------------
def fmt_price(v):
    """与页端 `fmtPrice()` 同口径。文字价（如「单询」）原样返回。"""
    if v is None or v == "":
        return "—"
    try:
        n = float(v)
    except (TypeError, ValueError):
        return str(v)
    if n == int(n):
        return f"{int(n):,}"
    s = f"{n:.2f}".rstrip("0").rstrip(".")
    try:
        return f"{float(s):,}"
    except ValueError:
        return s


def _tier_str(vals):
    """同档位的多个值 → `最小~最大`；值相同（含四舍五入后相同）直接给单值；
    含文字价（如「单询」）时数字部分仍取区间、文字价并列。"""
    vals = list(vals)
    fmts = [fmt_price(v) for v in vals]
    if len(set(fmts)) == 1:
        return fmts[0]
    nums = [v for v in vals if isinstance(v, (int, float))]
    texts = [f for v, f in zip(vals, fmts) if not isinstance(v, (int, float))]
    if not nums:
        return "/".join(dict.fromkeys(texts))
    span = f"{fmt_price(min(nums))}~{fmt_price(max(nums))}"
    return "/".join([span] + list(dict.fromkeys(texts)))


def group_key(r):
    """归并键 —— 「单位 × 区间」必须在内，否则同渠道的 KG / CBM 会互相盖掉。"""
    return (norm(r.get("供应商代码")), norm(r.get("来源表名")), norm(r.get("渠道名称")),
            norm(r.get("单位")), norm(r.get("区间")))


def _uniq_join(rs, field):
    """组内某字段的取值集合（`/` 连接）—— 字段分叉时并列显示，不丢。"""
    vals = []
    for r in rs:
        v = norm(r.get(field))
        if v and v not in vals:
            vals.append(v)
    return "/".join(vals) or "—"


def report(out, limit=10):
    groups = collections.OrderedDict()
    for r in out:
        groups.setdefault(group_key(r), []).append(r)

    total = len(out)
    if total == 0:
        return "命中 0 条。换个条件试试。"

    # 归并**不得丢记录** —— 这是本工具最容易犯、也最不该犯的错（静默少给）。
    assert sum(len(rs) for rs in groups.values()) == total, \
        f"归并前后条数不符：{total} → {sum(len(rs) for rs in groups.values())}"

    head = (f"命中 {total} 条 → 归并后 {len(groups)} 组"
            f"（供应商/表/渠道 × 单位 × 区间）")
    if len(groups) > limit:
        head += f"，仅展示前 {limit} 组（调 limit 看更多）"
    lines = [head]

    for i, (k, rs) in enumerate(groups.items()):
        if i >= limit:
            break
        sup, sheet, chan, unit, zone = k
        # 逐档位收集**去重后**的值：同组几十条记录往往价格完全相同，不去重会退化成 `X~X`
        agg = collections.OrderedDict()
        for r in rs:
            for tier, val in (r.get("价格") or {}).items():
                agg.setdefault(tier, {})[str(val)] = val
        tiers = " | ".join(f"{t}:{_tier_str(list(v.values()))}" for t, v in agg.items()) \
                or "(无档位价)"
        lines.append(
            f"· {sup} / {sheet} | {chan} | {_uniq_join(rs, '运输方式')} | {unit} | "
            f"包税={_uniq_join(rs, '是否包税')} | 货型={_uniq_join(rs, '货物类型')} | "
            f"{zone} | {tiers}"
            + (f" 〔{len(rs)} 条〕" if len(rs) > 1 else "")
        )
    return "\n".join(lines)


if __name__ == "__main__":
    kv = {}
    for a in sys.argv[1:]:
        if "=" not in a:
            sys.exit(f"!! 参数须形如 key=value，收到：{a!r}")
        k, v = a.split("=", 1)
        kv[k] = v

    raw_limit = kv.pop("limit", "10")
    try:
        limit = int(raw_limit)
    except ValueError:
        sys.exit(f"!! limit 须为整数，收到：{raw_limit!r}")

    try:
        hits = query(load_data(), **kv)
    except TypeError as e:                      # 未知参数 → 直接报错，不静默忽略
        sys.exit(f"!! 参数有误：{e}")

    print(report(hits, limit=limit))
