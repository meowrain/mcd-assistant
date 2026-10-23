#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""meal_picker.py — 麦门小助手「今天吃什么」决策引擎

在候选单品与约束条件下给出推荐，支持两种策略：
  smart  智能模式：按「热量余量 + 价格贴合 + 多样性」打分，取最高分
  dice   盲盒模式：在合格池中随机摇奖，优先本周没吃过的

输入 JSON（--data data.json；--demo 使用内置示例数据）：
{
  "candidates": [
    {"name": "麦辣鸡腿堡", "price": 21.5, "calories": 520,
     "tags": ["辣", "鸡肉", "汉堡"], "periods": ["午餐", "晚餐", "全天"]}
  ],
  "constraints": {
    "budget": 30,
    "max_calories": 600,
    "exclude_tags": ["辣"],
    "period": "午餐",
    "recent": ["巨无堡"]
  },
  "mode": "smart"
}

字段说明：
  candidates  候选单品列表；price 单价（元），calories 热量（千卡，可省略），
              tags 标签（可省略），periods 供应时段列表（可省略，默认全天）
  constraints.budget         预算上限（元）
  constraints.max_calories   热量上限（千卡）
  constraints.exclude_tags   忌口标签列表
  constraints.period         用餐时段：早餐/午餐/下午茶/晚餐/夜宵
  constraints.recent         最近吃过的单品（一周内不重样）
  constraints.mode           默认策略 smart | dice，可被 --mode 覆盖

输出（--format json | text，默认 text）：
{"pick": {...}, "reason": "...", "alternatives": [...], "pool_size": 8, "mode": "smart"}
"""
import argparse
import json
import random
import sys

DEMO_CANDIDATES = [
    {"name": "麦辣鸡腿堡", "price": 21.5, "calories": 520, "tags": ["辣", "鸡肉", "汉堡"], "periods": ["午餐", "晚餐", "全天"]},
    {"name": "巨无霸", "price": 24.0, "calories": 530, "tags": ["牛肉", "汉堡"], "periods": ["午餐", "晚餐", "全天"]},
    {"name": "板烧鸡腿堡", "price": 22.0, "calories": 430, "tags": ["鸡肉", "汉堡"], "periods": ["午餐", "晚餐", "全天"]},
    {"name": "双层吉士堡", "price": 14.5, "calories": 480, "tags": ["牛肉", "汉堡"], "periods": ["午餐", "晚餐", "全天"]},
    {"name": "麦香鱼", "price": 20.0, "calories": 380, "tags": ["鱼肉", "汉堡"], "periods": ["午餐", "晚餐", "全天"]},
    {"name": "薯条(大)", "price": 13.5, "calories": 510, "tags": ["油炸", "小食"], "periods": ["午餐", "晚餐", "下午茶", "夜宵", "全天"]},
    {"name": "麦乐鸡(5块)", "price": 12.5, "calories": 285, "tags": ["鸡肉", "小食"], "periods": ["午餐", "晚餐", "下午茶", "夜宵", "全天"]},
    {"name": "可口可乐(中)", "price": 9.0, "calories": 180, "tags": ["饮料"], "periods": ["全天"]},
    {"name": "美式咖啡", "price": 15.0, "calories": 15, "tags": ["咖啡", "饮料"], "periods": ["早餐", "下午茶", "全天"]},
    {"name": "猪柳蛋麦满分", "price": 17.5, "calories": 400, "tags": ["鸡蛋", "早餐"], "periods": ["早餐"]},
    {"name": "蛋挞", "price": 8.0, "calories": 220, "tags": ["甜品"], "periods": ["早餐", "下午茶", "全天"]},
    {"name": "香芋派", "price": 9.5, "calories": 250, "tags": ["甜品"], "periods": ["早餐", "下午茶", "全天"]},
    {"name": "麦旋风(奥利奥)", "price": 13.0, "calories": 330, "tags": ["甜品", "冰品"], "periods": ["下午茶", "夜宵", "全天"]},
]


def filter_candidates(candidates, constraints):
    """按约束过滤候选，返回合格池。"""
    pool = []
    for item in candidates:
        budget = constraints.get("budget")
        if budget is not None and item["price"] > budget:
            continue
        max_cal = constraints.get("max_calories")
        if max_cal is not None and item.get("calories") is not None and item["calories"] > max_cal:
            continue
        exclude = constraints.get("exclude_tags") or []
        if exclude and set(item.get("tags", [])) & set(exclude):
            continue
        period = constraints.get("period")
        if period and period not in item.get("periods", ["全天"]):
            continue
        pool.append(item)
    return pool


def smart_score(item, constraints, recent):
    """智能模式打分：热量低、价格贴合预算、非纯饮料、本周没吃过，得分更高。"""
    score = 1.0
    cal = item.get("calories")
    if cal is not None:
        score += 0.3 * (1 - min(cal / 800.0, 1.0))
    budget = constraints.get("budget")
    if budget is not None and item["price"] <= budget * 0.7:
        score += 0.2
    if "饮料" in item.get("tags", []):
        score -= 0.35
    if "甜品" in item.get("tags", []):
        score -= 0.15
    if item["name"] in recent:
        score -= 0.5
    return score


def dice_pick(pool, recent, rng):
    """盲盒模式：优先从本周没吃过的单品里摇。"""
    fresh = [i for i in pool if i["name"] not in recent]
    return rng.choice(fresh or pool)


def build_reason_smart(item, constraints, pool_size, recent):
    bits = []
    if recent:
        bits.append("虽然最近吃过，但综合条件还是它最合适" if item["name"] in recent else "本周还没吃过，换个口味")
    cal = item.get("calories")
    if cal is not None:
        bits.append(f"热量 {cal} 千卡，负担适中" if cal <= 600 else f"热量 {cal} 千卡，适合放开吃")
    budget = constraints.get("budget")
    if budget is not None and item["price"] <= budget:
        bits.append(f"¥{item['price']:.1f} 在预算 ¥{budget:.0f} 内")
    return f"合格池 {pool_size} 个单品中综合得分最高：" + "，".join(bits) + "。"


def build_reason_dice(item, pool_size, recent):
    if recent and item["name"] not in recent:
        return f"盲盒模式：从 {pool_size} 个合格单品中随机摇出，且避开了最近吃过的，手气不错。"
    return f"盲盒模式：从 {pool_size} 个合格单品中随机摇出，祝用餐愉快。"


def main():
    parser = argparse.ArgumentParser(description="麦门小助手 - 今天吃什么决策引擎")
    parser.add_argument("--data", help="候选数据 JSON 文件路径")
    parser.add_argument("--demo", action="store_true", help="使用内置示例数据")
    parser.add_argument("--mode", choices=["smart", "dice"], default=None, help="决策策略，覆盖 JSON 内 mode")
    parser.add_argument("--budget", type=float, help="预算上限（元）")
    parser.add_argument("--max-calories", type=int, help="热量上限（千卡）")
    parser.add_argument("--exclude", help="忌口标签，逗号分隔，如：辣,牛肉")
    parser.add_argument("--period", help="用餐时段：早餐/午餐/下午茶/晚餐/夜宵")
    parser.add_argument("--recent", help="最近吃过的单品，逗号分隔")
    parser.add_argument("--seed", type=int, default=None, help="盲盒随机种子（便于复现）")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    if args.demo:
        candidates = DEMO_CANDIDATES
        constraints = {}
    elif args.data:
        with open(args.data, encoding="utf-8") as f:
            payload = json.load(f)
        candidates = payload["candidates"]
        constraints = dict(payload.get("constraints", {}))
    else:
        parser.error("必须指定 --data 或 --demo")

    if args.budget is not None:
        constraints["budget"] = args.budget
    if args.max_calories is not None:
        constraints["max_calories"] = args.max_calories
    if args.exclude:
        constraints["exclude_tags"] = [t.strip() for t in args.exclude.split(",") if t.strip()]
    if args.period:
        constraints["period"] = args.period
    if args.recent:
        constraints["recent"] = [t.strip() for t in args.recent.split(",") if t.strip()]

    mode = args.mode or constraints.get("mode") or "smart"
    recent = constraints.get("recent") or []
    rng = random.Random(args.seed)

    pool = filter_candidates(candidates, constraints)
    if not pool:
        result = {"error": "没有单品符合当前约束", "suggestion": "放宽预算/热量上限，或减少忌口标签后重试"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(2)

    if mode == "dice":
        pick = dice_pick(pool, recent, rng)
        reason = build_reason_dice(pick, len(pool), recent)
        rest = [i for i in pool if i["name"] != pick["name"]]
        alternatives = rng.sample(rest, k=min(3, len(rest)))
    else:
        ranked = sorted(pool, key=lambda i: smart_score(i, constraints, recent), reverse=True)
        pick = ranked[0]
        reason = build_reason_smart(pick, constraints, len(pool), recent)
        alternatives = ranked[1:4]

    result = {
        "pick": pick,
        "reason": reason,
        "alternatives": alternatives,
        "pool_size": len(pool),
        "mode": mode,
    }

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"麦门推荐：{pick['name']}（¥{pick['price']:.1f} / {pick.get('calories', '?')} 千卡）")
    print(f"推荐理由：{reason}")
    if alternatives:
        names = "、".join(f"{a['name']}(¥{a['price']:.1f})" for a in alternatives)
        print(f"备选方案：{names}")
    print(f"[合格池 {len(pool)}/{len(candidates)} 个单品 | 模式：{mode}]")


if __name__ == "__main__":
    main()
