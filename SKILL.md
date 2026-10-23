---
name: mcd-assistant
description: 麦当劳智能小助手（麦门小助手）。当用户想点麦当劳却纠结吃什么、想薅券省钱并算出最优下单方案、或想回顾历史消费生成「麦门月报」与人格鉴定卡时使用。基于麦当劳官方 MCP Server（mcd-mcp）的菜单、营养、优惠券、活动、订单、抽奖能力，内置「今天吃什么」决策、「省钱军师」比价、「麦门月报」三大模式与「欧气时间」彩蛋，scripts/ 下四个零依赖 Python 脚本负责确定性计算，并配套免 Token 在线试算页。
agent_created: true
---

# 麦当劳智能小助手（mcd-assistant）

## Overview

一个 Skill 三种吃法：帮用户决定吃什么、帮用户把每一单点到最便宜、帮用户把消费记录变成有趣的月报和人格鉴定。所有菜单、价格、优惠券、订单数据均来自麦当劳官方 MCP Server（mcd-mcp）；脚本只做确定性计算，禁止用内置示例数据冒充真实数据回复用户。

## 模式一：今天吃什么（决策 + 盲盒）

触发场景：用户说「吃什么」「不知道点啥」「帮我选」「闭眼点」等。

流程：

1. 收集约束：预算、热量上限、忌口（辣/牛肉等）、用餐时段、最近吃过的单品。
2. 调用 MCP 取数：
   - `mcp__mcd-mcp__now-time-info` 判断当前时段（早餐/午餐/下午茶/晚餐/夜宵）
   - `mcp__mcd-mcp__query-meals` 获取当前菜单候选
   - `mcp__mcd-mcp__query-meal-detail` 补充单品规格与价格
   - `mcp__mcd-mcp__list-nutrition-foods` 补充热量数据
3. 将候选组装为 JSON（字段格式见 `scripts/meal_picker.py` 头部 docstring），运行：

   ```bash
   python scripts/meal_picker.py --data candidates.json --mode smart
   ```

   盲盒玩法用 `--mode dice --seed <任意整数>`；约束也可用命令行参数覆盖（`--budget 30 --max-calories 600 --exclude 辣,牛肉`）。
4. 按输出模板回复：推荐单品 + 理由 + 3 个备选 + 合格池数量。用户需要时再调 `mcp__mcd-mcp__query-nearby-stores` 附上最近门店。

## 模式二：省钱军师（绑券 + 比价 + 神单）

触发场景：用户说「怎么点最便宜」「有什么券」「帮我凑单」「这单能省多少」。

流程：

1. 确认用户想点的清单（单品 + 数量）。
2. 调用 MCP 取数，顺序即策略（先绑券再盘点）：
   - `mcp__mcd-mcp__auto-bind-coupons` 一键领取可领之券
   - `mcp__mcd-mcp__available-coupons` 查当前可用券
   - `mcp__mcd-mcp__query-promotions` 查进行中的活动
   - `mcp__mcd-mcp__query-store-coupons` / `mcp__mcd-mcp__query-survey-coupons` 补门店券、问卷券
   - `mcp__mcd-mcp__calculate-price` 校验脚本计算结果
3. 组装购物车 JSON（见 `scripts/coupon_optimizer.py` 头部 docstring），运行：

   ```bash
   python scripts/coupon_optimizer.py --data cart.json
   ```

4. 输出「神单方案」：原价 → 券后价、每步用了哪张券、共省多少、凑单建议。
5. 边界：不代替用户下单。只有用户明确说「就按这个下单」时才调 `mcp__mcd-mcp__create-order`，且下单前必须复述清单与金额。

## 模式三：麦门月报 + 人格鉴定

触发场景：用户说「看看我花了多少」「我的麦当劳报告」「我是什么麦门人格」。

流程：

1. 调 `mcp__mcd-mcp__order-list` 拉取历史订单；记录缺少价格或热量时，用 `mcp__mcd-mcp__query-meal-detail`、`mcp__mcd-mcp__list-nutrition-foods` 补全。
2. 组装订单 JSON（见 `scripts/report_generator.py` 头部 docstring），运行：

   ```bash
   python scripts/report_generator.py --data orders.json --format md
   ```

3. 输出月报：消费统计、Top 单品、人格卡。人格卡措辞以 `references/personas.md` 文案库为准，保持好玩但不冒犯用户。
4. 用户要求「发群 / 分享 / 截图」时，将同一份订单 JSON 传入：

   ```bash
   python scripts/persona_card.py --data orders.json --out card.html
   ```

   生成自包含 HTML 人格鉴定卡（品牌色 + 认证编号），告知文件路径并提示：浏览器打开后截图即可分享。

## 彩蛋：欧气时间

用户说「抽个奖」「看看手气」时：

1. `mcp__mcd-mcp__query-lottery-info` 汇总进行中的抽奖并给出建议顺序。
2. 用户确认后调 `mcp__mcd-mcp__draw-lottery`（消耗抽奖机会，必须先确认）。
3. `mcp__mcd-mcp__query-my-prizes` 回顾中奖史。

## 输入输出约定

四个脚本均只依赖 Python 3.8+ 标准库；输入 JSON 格式见各脚本头部 docstring；均支持 `--demo` 使用内置示例数据直接运行，便于调试与演示。脚本输出 `--format json` 时机型可读、`--format text/md` 时人读友好。

`demo/index.html` 是免 Token 的单文件试算页：JS 逻辑与上述脚本一一对应（经断言测试对齐），供评委和用户零成本体验；真实数据仍以 MCP 取数 + 脚本计算为准。

## 安全与边界

- 任何涉及扣款、积分消耗、抽奖机会的操作（`create-order` / `draw-lottery` / `mall-create-order` / `cancel-order`）必须先获得用户明确确认。
- 不在回复中展示用户手机号、收货地址等敏感信息；月报只呈现聚合统计。
- MCP 取数失败时如实告知，禁止用 `--demo` 示例数据冒充真实菜单回复用户。

## Resources

- `scripts/meal_picker.py` — 今天吃什么决策引擎（smart/dice 两种策略）
- `scripts/coupon_optimizer.py` — 神单计算引擎（券叠加 + 凑单建议）
- `scripts/report_generator.py` — 月报统计 + 人格匹配
- `scripts/persona_card.py` — 人格鉴定卡生成器（可分享 HTML，复用 report_generator 的统计与人格逻辑）
- `references/personas.md` — 麦门人格文案库（判定口径、画像、点评文案）
- `demo/index.html` — 免 Token 在线试算页（神单计算器 / 今天吃什么 / 月报人格卡）
