#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""persona_card.py — 麦门人格鉴定卡（可分享 HTML 卡片）生成器

读取与 report_generator.py 相同的订单 JSON，生成一个自包含 HTML 人格卡：
双击即可在浏览器打开、可直接截图分享，无任何外部依赖（样式全部内联）。

用法：
  python scripts/persona_card.py --demo --out card.html
  python scripts/persona_card.py --data orders.json --out card.html
  python scripts/persona_card.py --data orders.json            # 默认输出 persona_card.html

设计要点：
  - 麦当劳品牌色（黄 #FFC72C + 深棕 #292929），扁平风格，专为截图分享设计
  - 卡片内容：人格名称、画像、毒舌点评、核心数据、Top 单品、认证编号
  - 统计与人格匹配逻辑复用 report_generator.py，保证卡片与月报结论一致
  - 所有用户数据均经过 html.escape，防止注入
"""
import argparse
import hashlib
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_generator import DEMO_ORDERS, compute_stats, load_personas, match_persona  # noqa: E402

CARD_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #F3EDDF; min-height: 100vh; display: flex;
  align-items: center; justify-content: center; padding: 32px 16px;
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
  color: #292929; line-height: 1.6;
}
.card { width: 100%; max-width: 720px; background: #FFFFFF; border-radius: 20px; overflow: hidden; box-shadow: 0 8px 30px rgba(41, 41, 41, .12); }
.card-head { background: #FFC72C; padding: 22px 28px; display: flex; align-items: center; justify-content: space-between; }
.brand { display: flex; align-items: center; gap: 10px; font-weight: 500; font-size: 15px; letter-spacing: 1px; }
.brand svg { display: block; }
.period { font-size: 13px; color: #6B4E12; background: rgba(255,255,255,.55); border-radius: 999px; padding: 3px 12px; }
.card-body { padding: 28px; }
.persona-name { font-size: 34px; font-weight: 500; letter-spacing: 2px; }
.persona-id { display: inline-block; margin-top: 6px; font-size: 12px; color: #8A8378; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.tagline { margin-top: 10px; font-size: 15px; color: #5C5548; }
.roasts { margin-top: 16px; border-left: 4px solid #FFC72C; padding: 4px 0 4px 14px; }
.roasts p { font-size: 14px; color: #4A4438; margin-top: 6px; }
.roasts p:first-child { margin-top: 0; }
.stats { margin-top: 22px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.stat { background: #FAF6EC; border: 1px solid #EFE7D2; border-radius: 12px; padding: 12px 14px; }
.stat .k { font-size: 12px; color: #8A8378; }
.stat .v { font-size: 20px; font-weight: 500; margin-top: 2px; }
.top { margin-top: 22px; }
.top h3 { font-size: 14px; font-weight: 500; color: #8A8378; }
.top ol { margin-top: 8px; list-style: none; }
.top li { display: flex; justify-content: space-between; font-size: 14px; padding: 8px 0; border-bottom: 1px dashed #EFE7D2; }
.top li:last-child { border-bottom: none; }
.top .cnt { color: #8A8378; font-size: 13px; }
.card-foot { margin-top: 24px; padding-top: 16px; border-top: 1px solid #EFE7D2; display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #8A8378; }
.cert { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background: #292929; color: #FFC72C; border-radius: 6px; padding: 4px 10px; letter-spacing: 1px; }
"""

ARCHES_SVG = (
    '<svg width="34" height="26" viewBox="0 0 100 76" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M14 72 V44 Q14 12 38 12 Q62 12 62 44 V72" stroke="#292929" stroke-width="13" stroke-linecap="round"/>'
    '<path d="M62 72 V44 Q62 12 86 12" stroke="#292929" stroke-width="13" stroke-linecap="round" fill="none"/>'
    "</svg>"
)

CARD_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>麦门人格鉴定卡 · {name}</title>
<style>{css}</style>
</head>
<body>
<div class="card">
  <div class="card-head">
    <div class="brand">{arches}麦门认证 · MCDONALD'S</div>
    <div class="period">{period}</div>
  </div>
  <div class="card-body">
    <div class="persona-name">{name}</div>
    <div class="persona-id">persona_id: {persona_id}</div>
    <p class="tagline">{tagline}</p>
    <div class="roasts">{roasts}</div>
    <div class="stats">{stats}</div>
    <div class="top">
      <h3>本期常驻嘉宾 TOP 3</h3>
      <ol>{top_items}</ol>
    </div>
    <div class="card-foot">
      <span>由麦门小助手生成 · 数据来自麦当劳 MCP</span>
      <span class="cert">{cert}</span>
    </div>
  </div>
</div>
</body>
</html>
"""


def round2(x):
    return round(x + 0.0, 2)


def build_card(period, orders):
    stats = compute_stats(orders)
    persona_id, persona_name, rule = match_persona(stats)
    lib = load_personas()
    info = lib.get(persona_id, {})
    name = info.get("名称", persona_name)
    tagline = info.get("画像", rule)
    roasts = info.get("点评", [])[:2] or ["数据不会说谎，麦门 watched you."]

    stats_html = [
        f'<div class="stat"><div class="k">订单数</div><div class="v">{stats["order_count"]} 单</div></div>',
        f'<div class="stat"><div class="k">总消费</div><div class="v">¥{stats["total_spend"]:.2f}</div></div>',
        f'<div class="stat"><div class="k">单均消费</div><div class="v">¥{stats["avg_order"]:.2f}</div></div>',
    ]
    if stats["avg_calories"] is not None:
        stats_html.append(
            f'<div class="stat"><div class="k">单均热量</div><div class="v">{stats["avg_calories"]:.0f} 千卡</div></div>'
        )
    stats_html += [
        f'<div class="stat"><div class="k">夜间订单占比</div><div class="v">{stats["night_ratio"] * 100:.1f}%</div></div>',
        f'<div class="stat"><div class="k">最勤工作日</div><div class="v">{stats["busiest_weekday"]}</div></div>',
        f'<div class="stat"><div class="k">最长连续打卡</div><div class="v">{stats["max_streak"]} 天</div></div>',
        f'<div class="stat"><div class="k">点过单品数</div><div class="v">{stats["unique_items"]} 种</div></div>',
    ]

    top_items = "".join(
        f'<li><span>{html.escape(n)}</span><span class="cnt">× {c} · ¥{s:.2f}</span></li>'
        for n, c, s in stats["top_items"][:3]
    ) or "<li><span>暂无单品数据</span></li>"

    cert = "MCD-" + hashlib.md5(
        f"{period}|{stats['total_spend']}|{stats['order_count']}".encode("utf-8")
    ).hexdigest()[:6].upper()

    return CARD_TEMPLATE.format(
        css=CARD_CSS,
        arches=ARCHES_SVG,
        period=html.escape(str(period)),
        name=html.escape(name),
        persona_id=html.escape(persona_id),
        tagline=html.escape(tagline),
        roasts="".join(f"<p>{html.escape(r)}</p>" for r in roasts),
        stats="".join(stats_html),
        top_items=top_items,
        cert=cert,
    )


def main():
    parser = argparse.ArgumentParser(description="麦门小助手 - 人格鉴定卡生成器")
    parser.add_argument("--data", help="订单 JSON 文件路径（同 report_generator.py 输入格式）")
    parser.add_argument("--demo", action="store_true", help="使用内置示例订单")
    parser.add_argument("--month", help="只统计指定月份，如 2026-10")
    parser.add_argument("--out", default="persona_card.html", help="输出 HTML 文件路径")
    args = parser.parse_args()

    if args.demo:
        payload = {"period": "2026-10", "orders": DEMO_ORDERS}
    elif args.data:
        with open(args.data, encoding="utf-8") as f:
            payload = json.load(f)
    else:
        parser.error("必须指定 --data 或 --demo")

    orders = payload.get("orders", [])
    if args.month:
        orders = [o for o in orders if o["date"].startswith(args.month)]
        if not orders:
            print(json.dumps({"error": f"{args.month} 没有订单记录"}, ensure_ascii=False))
            sys.exit(2)

    period = args.month or payload.get("period") or orders[0]["date"][:7]
    card = build_card(period, orders)
    Path(args.out).write_text(card, encoding="utf-8")
    print(f"人格鉴定卡已生成：{Path(args.out).resolve()}")
    print("用浏览器打开后截图即可分享。")


if __name__ == "__main__":
    main()
