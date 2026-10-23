#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""coupon_optimizer.py — 麦门小助手「省钱军师」神单计算引擎

输入 JSON（--data cart.json；--demo 使用内置示例购物车）：
{
  "items": [
    {"name": "麦辣鸡腿堡", "price": 21.5, "qty": 1}
  ],
  "coupons": [
    {"name": "满40减8", "kind": "cash", "value": 8.0, "threshold": 40.0},
    {"name": "全场85折", "kind": "percent", "value": 0.85, "threshold": 30.0}
  ],
  "addons": [
    {"name": "蛋挞", "price": 8.0}
  ]
}

字段说明：
  items    购物车单品；price 单价（元），qty 数量（默认 1）
  coupons  可用券列表；kind=cash 表示满 threshold 元减 value 元，
           kind=percent 表示满 threshold 元打 value 折（0.85 即 85 折）
  addons   可选，凑单建议用的加购候选

计算策略（与 SKILL.md 模式二流程对应）：
  1. 原价 = 各单品价格 × 数量求和
  2. 所有达到门槛的满减券（cash）默认可叠加，按优惠额从大到小依次计入
  3. 在满减后的小计上，取优惠力度最大的折扣券（percent）再打折
  4. 差一点就能用的满减券，基于原价给出凑单建议（已用掉的券不再推荐）

注意：实际能否叠加以 MCP 返回的用券规则为准；组装 coupons 时只放当前可用的券，
     且折扣券默认只取力度最大的一张（多数活动不叠加多张折扣券）。

输出（--format json | text，默认 text）：分步方案 + 原价/券后/节省 + 凑单建议
"""
import argparse
import json

DEMO_CART = {
    "items": [
        {"name": "麦辣鸡腿堡", "price": 21.5, "qty": 1},
        {"name": "板烧鸡腿堡", "price": 22.0, "qty": 1},
        {"name": "薯条(大)", "price": 13.5, "qty": 1},
        {"name": "可口可乐(中)", "price": 9.0, "qty": 2},
    ],
    "coupons": [
        {"name": "满40减8", "kind": "cash", "value": 8.0, "threshold": 40.0},
        {"name": "满60减15", "kind": "cash", "value": 15.0, "threshold": 60.0},
        {"name": "满80减18", "kind": "cash", "value": 18.0, "threshold": 80.0},
        {"name": "全场85折", "kind": "percent", "value": 0.85, "threshold": 30.0},
        {"name": "饮品9折", "kind": "percent", "value": 0.9, "threshold": 0.0},
    ],
    "addons": [
        {"name": "蛋挞", "price": 8.0},
        {"name": "麦乐鸡(5块)", "price": 12.5},
    ],
}


def optimize(items, coupons, addons):
    base = round(sum(i["price"] * i.get("qty", 1) for i in items), 2)
    steps = []
    used = []

    cash_coupons = [c for c in coupons if c.get("kind") == "cash" and base >= c.get("threshold", 0)]
    cash_coupons.sort(key=lambda c: -c.get("value", 0))
    cash_sum = 0.0
    for c in cash_coupons:
        cash_sum += c["value"]
        used.append(c["name"])
        steps.append(f"使用「{c['name']}」：满 {c['threshold']:.0f} 减 {c['value']:.0f}，省 ¥{c['value']:.2f}")

    subtotal = round(base - cash_sum, 2)

    percent_coupons = [c for c in coupons if c.get("kind") == "percent" and subtotal >= c.get("threshold", 0)]
    percent_coupons.sort(key=lambda c: c.get("value", 1))
    final = subtotal
    if percent_coupons:
        best = percent_coupons[0]
        off = round(subtotal * (1 - best["value"]), 2)
        final = round(subtotal - off, 2)
        used.append(best["name"])
        steps.append(f"使用「{best['name']}」：满 {best['threshold']:.0f} 打 {best['value'] * 10:g} 折，再省 ¥{off:.2f}")

    saved = round(base - final, 2)
    rate = round(saved / base * 100, 1) if base else 0.0
    suggestions = build_suggestions(coupons, base, addons, used)

    return {
        "base": base,
        "final": final,
        "saved": saved,
        "saved_rate": rate,
        "steps": steps,
        "used_coupons": used,
        "suggestions": suggestions,
    }


def build_suggestions(coupons, base, addons, used):
    """差一点就能用的满减券，给出凑单建议。

    基于原价估算（差距大于 20 元不值得凑）；已经用掉的券不再推荐。
    """
    suggestions = []
    for c in coupons:
        threshold = c.get("threshold", 0)
        if c.get("kind") != "cash" or base >= threshold or c["name"] in used:
            continue
        gap = round(threshold - base, 2)
        if gap > 20:
            continue
        cheapest = min(addons, key=lambda a: a["price"], default=None)
        if not cheapest:
            continue
        if cheapest["price"] >= gap:
            net = round(c["value"] - cheapest["price"], 2)
            if net > 0:
                suggestions.append(
                    f"加购「{cheapest['name']}」(¥{cheapest['price']:.1f}) 即可用「{c['name']}」，净省约 ¥{net:.2f}"
                )
            else:
                suggestions.append(
                    f"加购「{cheapest['name']}」(¥{cheapest['price']:.1f}) 可用「{c['name']}」省 ¥{c['value']:.0f}，但加购本身要 ¥{cheapest['price']:.1f}，不划算"
                )
        else:
            suggestions.append(
                f"距「{c['name']}」还差 ¥{gap:.2f}，最小加购「{cheapest['name']}」也要 ¥{cheapest['price']:.1f}，补不上，不建议凑单"
            )
    return suggestions


def main():
    parser = argparse.ArgumentParser(description="麦门小助手 - 省钱军师神单计算引擎")
    parser.add_argument("--data", help="购物车 JSON 文件路径")
    parser.add_argument("--demo", action="store_true", help="使用内置示例购物车")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    if args.demo:
        cart = DEMO_CART
    elif args.data:
        with open(args.data, encoding="utf-8") as f:
            cart = json.load(f)
    else:
        parser.error("必须指定 --data 或 --demo")

    result = optimize(cart.get("items", []), cart.get("coupons", []), cart.get("addons", []))

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("== 神单方案 ==")
    print(f"原价：¥{result['base']:.2f}")
    print(f"券后：¥{result['final']:.2f}")
    print(f"节省：¥{result['saved']:.2f}（{result['saved_rate']}%）")
    if result["steps"]:
        print("用券步骤：")
        for idx, s in enumerate(result["steps"], 1):
            print(f"  {idx}. {s}")
    else:
        print("当前没有可用券，按原价下单。")
    if result["suggestions"]:
        print("凑单建议：")
        for s in result["suggestions"]:
            print(f"  - {s}")


if __name__ == "__main__":
    main()
