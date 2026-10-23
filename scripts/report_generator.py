#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report_generator.py — 麦门月报 + 麦门人格鉴定引擎

输入 JSON（--data orders.json；--demo 使用内置示例订单）：
{
  "period": "2026-10",
  "orders": [
    {"date": "2026-10-03T12:30:00", "amount": 44.0, "channel": "到店",
     "items": [{"name": "麦辣鸡腿堡", "price": 21.5, "calories": 520, "qty": 1}]}
  ]
}

字段说明：
  orders  订单列表；date 下单时间，amount 实付金额（元），channel 渠道（可选），
          items 单品列表（name/price/calories/qty 均可选，缺价格时只计数）
  period  账期标签，如 2026-10（可选，默认取 --month 或首单日期前缀）

输出（--format md | json，默认 md）：
  md    Markdown 月报草稿（核心数据 + Top 单品 + 人格卡）
  json  统计结果 + 命中的人格 id，便于二次加工

人格文案来自 references/personas.md（文件缺失时退化为内置简版）。
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

COFFEE_KEYS = ("咖啡", "美式", "拿铁", "摩卡", "澳白")
BIG_ORDER = 60.0

PERSONA_RULES = [
    ("midnight_believer", "深夜麦门信徒", "夜间订单占比 ≥ 30%",
     lambda s: s["order_count"] > 0 and s["night_ratio"] >= 0.3),
    ("coffee_survivor", "早八咖啡续命人", "含咖啡订单占比 ≥ 25%",
     lambda s: s["order_count"] > 0 and s["coffee_ratio"] >= 0.25),
    ("budget_master", "穷鬼套餐收藏家", "单均消费 ≤ ¥15",
     lambda s: s["order_count"] > 0 and s["avg_order"] <= 15),
    ("calorie_bomber", "热量炸弹体验官", "单均热量 ≥ 800 千卡",
     lambda s: s["avg_calories"] is not None and s["avg_calories"] >= 800),
    ("party_king", "聚餐买单王", "大额订单（≥¥60）占比 ≥ 30%",
     lambda s: s["order_count"] > 0 and s["big_order_ratio"] >= 0.3),
    ("orthodox", "麦门原教旨主义者", "头号单品占比 ≥ 40%",
     lambda s: s["total_item_count"] > 0 and s["top_item_ratio"] >= 0.4),
    ("explorer", "麦门探险家", "点过 ≥ 8 种不同单品",
     lambda s: s["unique_items"] >= 8),
]
FALLBACK_PERSONA = ("balanced", "麦门均衡信徒", "以上规则均未命中，兜底人格")

DEMO_ORDERS = [
    {"date": "2026-10-01T12:10:00", "amount": 44.0, "channel": "到店", "items": [
        {"name": "麦辣鸡腿堡", "price": 21.5, "calories": 520, "qty": 1},
        {"name": "薯条(大)", "price": 13.5, "calories": 510, "qty": 1},
        {"name": "可口可乐(中)", "price": 9.0, "calories": 180, "qty": 1}]},
    {"date": "2026-10-02T22:41:00", "amount": 43.0, "channel": "外送", "items": [
        {"name": "麦香鱼", "price": 20.0, "calories": 380, "qty": 1},
        {"name": "美式咖啡", "price": 15.0, "calories": 15, "qty": 1},
        {"name": "蛋挞", "price": 8.0, "calories": 220, "qty": 1}]},
    {"date": "2026-10-03T08:15:00", "amount": 32.5, "channel": "到店", "items": [
        {"name": "猪柳蛋麦满分", "price": 17.5, "calories": 400, "qty": 1},
        {"name": "美式咖啡", "price": 15.0, "calories": 15, "qty": 1}]},
    {"date": "2026-10-05T23:15:00", "amount": 31.0, "channel": "外送", "items": [
        {"name": "麦乐鸡(5块)", "price": 12.5, "calories": 285, "qty": 1},
        {"name": "香芋派", "price": 9.5, "calories": 250, "qty": 1},
        {"name": "可口可乐(中)", "price": 9.0, "calories": 180, "qty": 1}]},
    {"date": "2026-10-06T12:30:00", "amount": 37.5, "channel": "到店", "items": [
        {"name": "巨无霸", "price": 24.0, "calories": 530, "qty": 1},
        {"name": "薯条(大)", "price": 13.5, "calories": 510, "qty": 1}]},
    {"date": "2026-10-08T19:02:00", "amount": 43.5, "channel": "外送", "items": [
        {"name": "板烧鸡腿堡", "price": 22.0, "calories": 430, "qty": 1},
        {"name": "麦乐鸡(5块)", "price": 12.5, "calories": 285, "qty": 1},
        {"name": "可口可乐(中)", "price": 9.0, "calories": 180, "qty": 1}]},
    {"date": "2026-10-09T00:32:00", "amount": 22.5, "channel": "外送", "items": [
        {"name": "双层吉士堡", "price": 14.5, "calories": 480, "qty": 1},
        {"name": "蛋挞", "price": 8.0, "calories": 220, "qty": 1}]},
    {"date": "2026-10-11T15:20:00", "amount": 28.0, "channel": "到店", "items": [
        {"name": "麦旋风(奥利奥)", "price": 13.0, "calories": 330, "qty": 1},
        {"name": "美式咖啡", "price": 15.0, "calories": 15, "qty": 1}]},
    {"date": "2026-10-12T21:58:00", "amount": 50.0, "channel": "外送", "items": [
        {"name": "麦辣鸡腿堡", "price": 21.5, "calories": 520, "qty": 1},
        {"name": "薯条(大)", "price": 13.5, "calories": 510, "qty": 1},
        {"name": "美式咖啡", "price": 15.0, "calories": 15, "qty": 1}]},
    {"date": "2026-10-14T12:05:00", "amount": 31.0, "channel": "到店", "items": [
        {"name": "板烧鸡腿堡", "price": 22.0, "calories": 430, "qty": 1},
        {"name": "可口可乐(中)", "price": 9.0, "calories": 180, "qty": 1}]},
    {"date": "2026-10-16T19:30:00", "amount": 52.5, "channel": "外送", "items": [
        {"name": "麦辣鸡腿堡", "price": 21.5, "calories": 520, "qty": 1},
        {"name": "麦乐鸡(5块)", "price": 12.5, "calories": 285, "qty": 1},
        {"name": "香芋派", "price": 9.5, "calories": 250, "qty": 1},
        {"name": "可口可乐(中)", "price": 9.0, "calories": 180, "qty": 1}]},
    {"date": "2026-10-18T22:07:00", "amount": 47.0, "channel": "外送", "items": [
        {"name": "巨无霸", "price": 24.0, "calories": 530, "qty": 1},
        {"name": "蛋挞", "price": 8.0, "calories": 220, "qty": 1},
        {"name": "美式咖啡", "price": 15.0, "calories": 15, "qty": 1}]},
    {"date": "2026-10-19T12:22:00", "amount": 33.5, "channel": "到店", "items": [
        {"name": "麦香鱼", "price": 20.0, "calories": 380, "qty": 1},
        {"name": "薯条(大)", "price": 13.5, "calories": 510, "qty": 1}]},
    {"date": "2026-10-21T08:05:00", "amount": 32.5, "channel": "到店", "items": [
        {"name": "猪柳蛋麦满分", "price": 17.5, "calories": 400, "qty": 1},
        {"name": "美式咖啡", "price": 15.0, "calories": 15, "qty": 1}]},
    {"date": "2026-10-23T19:11:00", "amount": 34.5, "channel": "外送", "items": [
        {"name": "麦辣鸡腿堡", "price": 21.5, "calories": 520, "qty": 1},
        {"name": "麦旋风(奥利奥)", "price": 13.0, "calories": 330, "qty": 1}]},
    {"date": "2026-10-25T23:44:00", "amount": 36.0, "channel": "外送", "items": [
        {"name": "双层吉士堡", "price": 14.5, "calories": 480, "qty": 1},
        {"name": "麦乐鸡(5块)", "price": 12.5, "calories": 285, "qty": 1},
        {"name": "可口可乐(中)", "price": 9.0, "calories": 180, "qty": 1}]},
    {"date": "2026-10-27T15:40:00", "amount": 23.0, "channel": "到店", "items": [
        {"name": "美式咖啡", "price": 15.0, "calories": 15, "qty": 1},
        {"name": "蛋挞", "price": 8.0, "calories": 220, "qty": 1}]},
    {"date": "2026-10-29T12:00:00", "amount": 40.5, "channel": "到店", "items": [
        {"name": "板烧鸡腿堡", "price": 22.0, "calories": 430, "qty": 1},
        {"name": "可口可乐(中)", "price": 9.0, "calories": 180, "qty": 1},
        {"name": "香芋派", "price": 9.5, "calories": 250, "qty": 1}]},
]


def parse_date(s):
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析日期：{s}")


def calc_streak(dates):
    if not dates:
        return 0
    ordered = sorted(dates)
    best = cur = 1
    for prev, nxt in zip(ordered, ordered[1:]):
        cur = cur + 1 if (nxt - prev).days == 1 else 1
        best = max(best, cur)
    return best


def compute_stats(orders):
    total_spend = round(sum(o["amount"] for o in orders), 2)
    count = len(orders)
    avg_order = round(total_spend / count, 2) if count else 0.0

    item_count = Counter()
    item_spend = Counter()
    order_calories = []
    night = 0
    coffee_orders = 0
    big = 0
    weekdays = Counter()
    dates = set()

    for o in orders:
        dt = parse_date(o["date"])
        if dt.hour >= 21 or dt.hour < 4:
            night += 1
        if o["amount"] >= BIG_ORDER:
            big += 1
        weekdays["周" + "一二三四五六日"[dt.weekday()]] += 1
        dates.add(dt.date())
        cal_sum = 0
        has_cal = False
        has_coffee = False
        for it in o.get("items", []):
            qty = it.get("qty", 1)
            item_count[it["name"]] += qty
            item_spend[it["name"]] += it.get("price", 0) * qty
            if it.get("calories") is not None:
                cal_sum += it["calories"] * qty
                has_cal = True
            if any(k in it["name"] for k in COFFEE_KEYS):
                has_coffee = True
        if has_cal:
            order_calories.append(cal_sum)
        if has_coffee:
            coffee_orders += 1

    total_item_count = sum(item_count.values())
    top_items = [(n, c, round(item_spend[n], 2)) for n, c in item_count.most_common()]

    return {
        "order_count": count,
        "total_spend": total_spend,
        "avg_order": avg_order,
        "avg_calories": round(sum(order_calories) / len(order_calories), 1) if order_calories else None,
        "night_ratio": night / count if count else 0.0,
        "coffee_ratio": coffee_orders / count if count else 0.0,
        "big_order_ratio": big / count if count else 0.0,
        "unique_items": len(item_count),
        "total_item_count": total_item_count,
        "top_item_ratio": (top_items[0][1] / total_item_count) if total_item_count else 0.0,
        "top_items": top_items,
        "busiest_weekday": weekdays.most_common(1)[0][0] if weekdays else "-",
        "max_streak": calc_streak(dates),
    }


def match_persona(stats):
    for pid, pname, rule, ok in PERSONA_RULES:
        if ok(stats):
            return pid, pname, rule
    return FALLBACK_PERSONA


def load_personas():
    path = Path(__file__).resolve().parent.parent / "references" / "personas.md"
    lib = {}
    if not path.exists():
        return lib
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("## "):
            current = line[3:].strip()
            lib[current] = {"点评": []}
        elif current and line.startswith("- "):
            body = line[2:]
            if ":" in body:
                key, _, value = body.partition(":")
                key, value = key.strip(), value.strip()
                if key == "点评":
                    lib[current]["点评"].append(value)
                else:
                    lib[current][key] = value
    return lib


def render_md(period, stats, persona_id, persona_name, rule, lib):
    info = lib.get(persona_id, {})
    display_name = info.get("名称", persona_name)
    lines = [
        f"# 麦门月报 · {period}",
        "",
        "## 核心数据",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
        f"| 订单数 | {stats['order_count']} 单 |",
        f"| 总消费 | ¥{stats['total_spend']:.2f} |",
        f"| 单均消费 | ¥{stats['avg_order']:.2f} |",
    ]
    if stats["avg_calories"] is not None:
        lines.append(f"| 单均热量 | {stats['avg_calories']:.0f} 千卡 |")
    lines += [
        f"| 夜间订单占比 | {stats['night_ratio'] * 100:.1f}% |",
        f"| 最勤工作日 | {stats['busiest_weekday']} |",
        f"| 最长连续打卡 | {stats['max_streak']} 天 |",
        f"| 点过单品数 | {stats['unique_items']} 种 |",
        "",
        "## Top 5 单品",
        "",
    ]
    for idx, (name, cnt, spend) in enumerate(stats["top_items"][:5], 1):
        lines.append(f"{idx}. {name} × {cnt}（¥{spend:.2f}）")
    lines += ["", "## 人格鉴定", "", f"**{display_name}**（{persona_id}）", "", f"判定依据：{rule}", ""]
    if info.get("画像"):
        lines.append(f"> {info['画像']}")
        lines.append("")
    roasts = info.get("点评", [])
    if roasts:
        lines += [f"> {r}" for r in roasts[:2]] + [""]
    else:
        lines += ["> 数据不会说谎，麦门 watched you.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="麦门小助手 - 麦门月报与人格鉴定引擎")
    parser.add_argument("--data", help="订单 JSON 文件路径")
    parser.add_argument("--demo", action="store_true", help="使用内置示例订单")
    parser.add_argument("--month", help="只统计指定月份，如 2026-10")
    parser.add_argument("--format", choices=["md", "json"], default="md")
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
    stats = compute_stats(orders)
    persona_id, persona_name, rule = match_persona(stats)

    if args.format == "json":
        out = {"period": period, "stats": stats,
               "persona": {"id": persona_id, "name": persona_name, "rule": rule}}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    print(render_md(period, stats, persona_id, persona_name, rule, load_personas()))


if __name__ == "__main__":
    main()
