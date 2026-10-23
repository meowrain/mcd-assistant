# workbuddy.md — WorkBuddy 开发对话上下文导出

> 本文件记录「麦门小助手（mcd-assistant）」使用 WorkBuddy 开发过程中的关键对话上下文，
> 供联动活动奖励条件核验使用。内容为开发过程的如实导出，未做美化删改。

## 会话信息

- 开发日期：2026-10-23
- 开发工具：WorkBuddy（AI 编程助手）
- 对话主题：基于麦当劳 MCP 能力的 Skill 创意设计与参赛项目落地
- 工作目录：`C:\Users\meowr\WorkBuddy\mcd`

## 需求背景（来自用户）

参赛要求项目仓库包含 5 类文件：

1. `README.md`（必须，文件名不可改动）
2. `CONTEST_DECLARATION.md`（必须，文件名及内容均不可改动，须用官方文件）
3. `MCP_INTEGRATION.md`（必须，文件名不可改动）
4. 源代码（必须，形式不限）
5. `workbuddy.md`（参加 WorkBuddy 专项奖励必须，文件名不可改动）

用户提问：「参与者可以基于麦当劳现有的 MCP 能力，结合创意场景，开发具有创意或实用价值的 Skill 项目。可以设计什么好玩的 skill 呢？」

## 关键决策记录

### 第一步：盘点 MCP 能力

对话中梳理了麦当劳 MCP（mcd-mcp）约 30 个工具，归为六类：菜单与营养、优惠券与活动、订单与外送、派对聚会、抽奖、积分商城。

### 第二步：提出 8 个创意候选

1. 麦门人格鉴定所（读历史订单生成人格 + 月报，出圈传播向）
2. 今天吃什么终结者（预算/热量约束下决策 + 盲盒，好玩向）
3. 麦门勋章馆（游戏化成就系统）
4. 麦门欧皇抽奖室（抽奖链路汇总与规划）
5. 麦门省钱军师（绑券 + 比价 + 神单方案，实用向）
6. 热量警察（热量预算配餐）
7. 聚会点单管家（party 链路 + 自动 AA）
8. 麦门日历精灵（每日活动早报，起步款）

### 第三步： quadrant 评估

按「好玩度 × 实用度」绘制创意象限图（对话中以内联图表展示），结论：

- 明星项目（好玩又实用）：今天吃什么终结者、省钱军师
- 出圈型：人格鉴定所、勋章馆
- 差异化型：欧皇抽奖室、聚会管家

### 第四步：确定方案（用户选择）

用户在选项中确认选择「组合型小助手（推荐）」：做一个多模式 Skill，把决策、省钱、月报三种能力整合为「麦门小助手」，用一条主流程串起 10+ 个 MCP 工具，冲刺大奖。

### 第五步：技术方案

- 形态：标准 WorkBuddy Skill（SKILL.md + scripts/ + references/），零第三方依赖（Python 3.8+ 标准库）。
- 分层：MCP 负责「真」（实时数据）→ 脚本负责「算」（确定性计算）→ references/ 负责「说」（人格文案）。
- 脚本清单：
  - `scripts/meal_picker.py`：约束过滤 + smart 打分 / dice 盲盒两种决策策略
  - `scripts/coupon_optimizer.py`：满减券叠加 + 折扣券选取 + 凑单建议
  - `scripts/report_generator.py`：消费统计 + 人格规则匹配，文案从 `references/personas.md` 单一来源读取
- 安全边界：抽奖、下单等消耗性操作必须用户确认；月报只输出聚合统计；禁止用 demo 数据冒充真实数据。

### 第六步：冲榜补强（榜单情报驱动）

同批次的大赛榜单分析（M-China/mcd-developer-innovation-challenge，前 7 名 881+ star）给出两条结论：赢家分「求解工具派」（拼算法深度）与「情绪内容派」（拼可截图传播）；前 6 名全部有「单文件可分享产物 + 免 Token 在线 demo」。据此补强：

1. `scripts/persona_card.py`：可截图分享的 HTML 人格鉴定卡（麦当劳品牌色 + 认证编号，统计与人格逻辑复用 report_generator）。
2. `demo/index.html`：免 Token 单文件在线试算页（神单计算器 / 今天吃什么 / 月报人格卡三标签），JS 逻辑与 Python 脚本一一对应，并用 Node 断言测试逐项对齐输出。

## 产出文件清单

| 文件 | 说明 |
| --- | --- |
| `SKILL.md` | Skill 主文件：三模式工作流 + 彩蛋 + 安全边界 |
| `scripts/meal_picker.py` | 今天吃什么决策引擎 |
| `scripts/coupon_optimizer.py` | 神单计算引擎 |
| `scripts/report_generator.py` | 月报 + 人格鉴定引擎 |
| `scripts/persona_card.py` | 人格鉴定卡生成器（可分享 HTML） |
| `references/personas.md` | 麦门人格文案库（8 种人格） |
| `demo/index.html` | 免 Token 在线试算页（单文件，三标签可交互） |
| `README.md` | 项目介绍 / 安装 / 示例 / 目标用户 |
| `MCP_INTEGRATION.md` | 17 个 MCP 工具清单、调用流程图、业务价值、可分享产物 |
| `CONTEST_DECLARATION.md` | 参赛声明（原创性 / 合规性 / 敏感信息） |
| `examples/` | 四个脚本的 demo 输出 + 人格卡示例 HTML |

## MCP 使用情况

共规划调用 17 个 `mcp__mcd-mcp__*` 工具（详见 MCP_INTEGRATION.md），覆盖菜单、营养、优惠券、活动、订单、抽奖六大能力域，其中 `auto-bind-coupons`、`survey-coupons`、`lottery` 系列为差异化深挖链路。

## 验证方式

- 四个脚本均通过 `--demo` 模式零依赖直接运行验证；demo 输出存档于 `examples/`，供评委复现。
- `demo/index.html` 的 JS 逻辑经 Node 断言测试与 Python 脚本输出逐项对齐（神单计算、月报统计、人格匹配、决策推荐共 23 条断言全部通过）。
- Skill 结构通过官方 `package_skill.py` 校验并打出 distributable zip。

## 后续待办

- 如官方提供 `CONTEST_DECLARATION.md` 原件，以官方文件整体替换（内容不可改动）。
- 接入真实 MCP 数据做一轮端到端联调（取数 → JSON → 脚本 → 输出）。
