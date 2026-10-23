# MCP_INTEGRATION.md — 麦当劳 MCP 集成说明

## 1. 使用的 MCP Server

| 项 | 内容 |
| --- | --- |
| Server 名称 | mcd-mcp（麦当劳官方 MCP Server） |
| 接入方式 | WorkBuddy 连接器授权后，以 `mcp__mcd-mcp__*` 系列工具调用 |
| 本项目使用工具数 | 17 个（覆盖菜单、营养、优惠券、活动、订单、抽奖六大能力域） |

## 2. 工具清单

| # | 工具 | 所属模式 | 用途 | 调用时机 |
| --- | --- | --- | --- | --- |
| 1 | `mcp__mcd-mcp__now-time-info` | 今天吃什么 | 获取当前时间，推断用餐时段 | 决策前第一步 |
| 2 | `mcp__mcd-mcp__query-meals` | 今天吃什么 | 拉取当前菜单，构建候选池 | 取数 |
| 3 | `mcp__mcd-mcp__query-meal-detail` | 今天吃什么 / 麦门月报 | 单品规格、价格、加配料信息 | 补全候选 / 订单单品 |
| 4 | `mcp__mcd-mcp__list-nutrition-foods` | 今天吃什么 / 麦门月报 | 热量等营养数据 | 补全热量 |
| 5 | `mcp__mcd-mcp__query-nearby-stores` | 今天吃什么 | 最近门店（可选附赠信息） | 用户需要时 |
| 6 | `mcp__mcd-mcp__auto-bind-coupons` | 省钱军师 | 一键领取当前可领的优惠券 | 比价第一步：先绑券再盘点 |
| 7 | `mcp__mcd-mcp__available-coupons` | 省钱军师 | 当前可用券清单 | 盘点 |
| 8 | `mcp__mcd-mcp__query-promotions` | 省钱军师 | 进行中的活动 | 盘点 |
| 9 | `mcp__mcd-mcp__query-store-coupons` | 省钱军师 | 门店可用券 | 盘点 |
| 10 | `mcp__mcd-mcp__query-survey-coupons` | 省钱军师 | 问卷奖励券 | 盘点 |
| 11 | `mcp__mcd-mcp__calculate-price` | 省钱军师 | 官方算价，校验脚本计算结果 | 输出神单方案前 |
| 12 | `mcp__mcd-mcp__order-list` | 麦门月报 | 历史订单 | 月报取数第一步 |
| 13 | `mcp__mcd-mcp__query-my-account` | 麦门月报 | 账户信息（用于报告头展示） | 月报取数 |
| 14 | `mcp__mcd-mcp__query-lottery-info` | 欧气时间 | 进行中的抽奖活动汇总 | 彩蛋入口 |
| 15 | `mcp__mcd-mcp__draw-lottery` | 欧气时间 | 执行抽奖（消耗机会） | 用户明确确认后 |
| 16 | `mcp__mcd-mcp__query-my-prizes` | 欧气时间 | 中奖记录回顾 | 抽奖后 |
| 17 | `mcp__mcd-mcp__create-order` | 省钱军师 | 代用户下单 | 仅用户明确说「就按这个下单」时 |

## 3. 调用流程

### 模式一：今天吃什么

```text
用户：「午饭预算 30，不想吃辣」
  │
  ├─► mcp__mcd-mcp__now-time-info ──► 推断时段 = 午餐
  ├─► mcp__mcd-mcp__query-meals ──► 候选池（名称/价格）
  ├─► mcp__mcd-mcp__query-meal-detail ──► 补规格与价格
  ├─► mcp__mcd-mcp__list-nutrition-foods ──► 补热量
  │
  ▼
组装 candidates.json ──► scripts/meal_picker.py（过滤 + 打分/摇奖）
  │
  ▼
输出：推荐单品 + 理由 + 备选（可选附最近门店 query-nearby-stores）
```

### 模式二：省钱军师

```text
用户：「麦辣鸡腿堡 + 板烧鸡腿堡 + 大薯 + 两杯中可，怎么点最便宜？」
  │
  ├─► mcp__mcd-mcp__auto-bind-coupons ──► 先把能领的券全领了
  ├─► mcp__mcd-mcp__available-coupons ──► 我的券
  ├─► mcp__mcd-mcp__query-promotions ──► 进行中的活动
  ├─► mcp__mcd-mcp__query-store-coupons ──► 门店券
  ├─► mcp__mcd-mcp__query-survey-coupons ──► 问卷券
  │
  ▼
组装 cart.json ──► scripts/coupon_optimizer.py（满减叠加 + 折扣券 + 凑单建议）
  │
  ▼
mcp__mcd-mcp__calculate-price ──► 官方算价校验 ──► 输出神单方案
  │
  ▼
（仅用户确认）mcp__mcd-mcp__create-order ──► 下单前复述清单与金额
```

### 模式三：麦门月报

```text
用户：「我上个月在麦当劳花了多少？我是什么人格？」
  │
  ├─► mcp__mcd-mcp__order-list ──► 历史订单
  ├─► mcp__mcd-mcp__query-meal-detail ──► 补缺失价格
  ├─► mcp__mcd-mcp__list-nutrition-foods ──► 补热量
  ├─► mcp__mcd-mcp__query-my-account ──► 账户信息（报告头）
  │
  ▼
组装 orders.json ──► scripts/report_generator.py（统计 + 人格规则匹配）
  │
  ▼
读取 references/personas.md 文案库 ──► 输出 Markdown 月报 + 人格卡
```

## 4. 数据流设计

```text
MCP 原始返回 ──► Skill 按脚本约定组装 JSON ──► 脚本确定性计算 ──► 人读输出
```

- **MCP 负责「真」**：所有菜单、价格、券、订单数据实时来自官方 Server，脚本不直连 MCP。
- **脚本负责「算」**：决策打分、券叠加、统计与人格匹配是纯计算，输入输出均为 JSON，可单测、可复现（`--seed`）。
- **references/ 负责「说」**：人格文案与脚本逻辑分离，改文案不动代码。

## 5. 业务价值

| 模式 | 痛点 | 价值 |
| --- | --- | --- |
| 今天吃什么 | 选择困难，每天在菜单前发呆 | 30 秒给出带理由的推荐；盲盒模式增加乐趣 |
| 省钱军师 | 券不会叠、凑单算不清，同一单别人买得更便宜 | 先绑券再比价，输出分步神单方案，实测可省 40% 左右 |
| 麦门月报 | 消费是一笔糊涂账 | 聚合统计 + 人格鉴定，把流水账变成可分享的月度报告 |
| 欧气时间 | 抽奖活动散落各处 | 汇总活动、规划顺序、回顾中奖史 |

## 6. 安全边界

- 抽奖（`draw-lottery`）、下单（`create-order`）等消耗性操作必须先获得用户明确确认。
- 月报只输出聚合统计，不展示手机号、收货地址等敏感信息。
- 脚本 `--demo` 数据仅用于调试演示，禁止在真实会话中冒充 MCP 数据回复用户。

## 7. 可分享产物（不调用 MCP，本地生成）

| 产物 | 生成方式 | 用途 |
| --- | --- | --- |
| 人格鉴定卡（HTML） | `scripts/persona_card.py --data orders.json --out card.html` | 自包含单文件，浏览器打开截图即可分享；统计与人格结论复用 `report_generator.py`，与月报一致 |
| 在线试算页 | `demo/index.html` | 单文件纯前端页面，神单计算器 / 今天吃什么 / 月报人格卡全部可交互；JS 逻辑与 Python 脚本经断言测试逐项对齐；可部署 GitHub Pages 供评委免 Token 体验 |

两个产物都遵循同一分层：MCP 取真数据 → 脚本/JS 做确定性计算 → 人读输出。演示与分享场景不触碰任何用户数据。
