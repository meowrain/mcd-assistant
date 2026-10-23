# 麦门小助手（mcd-assistant）

> 一个 Skill 三种吃法：帮你决定吃什么、帮你把每一单点到最便宜、帮你把消费记录变成有趣的月报和人格鉴定。

基于麦当劳官方 MCP Server（mcd-mcp）的菜单、营养、优惠券、活动、订单、抽奖能力打造的 WorkBuddy Skill。所有价格、菜单、订单数据均实时来自 MCP，脚本只做确定性计算，不编造数据。

## 亮点

- **三大模式 + 一个彩蛋**：「今天吃什么」决策/盲盒、「省钱军师」绑券比价、「麦门月报」人格鉴定，外加「欧气时间」抽奖彩蛋。
- **15+ MCP 工具组合调用**：不止查菜单，还用到了 auto-bind-coupons、party/lottery 等冷门链路，集成深度拉满（详见 [MCP_INTEGRATION.md](MCP_INTEGRATION.md)）。
- **可截图分享的人格鉴定卡**：`persona_card.py` 一键生成自包含 HTML 人格卡（品牌色设计 + 认证编号），浏览器打开截图即可发群，传播利器。
- **免 Token 在线试算页**：`demo/index.html` 单文件纯前端页面，神单计算器 / 今天吃什么 / 月报人格卡三个玩法全部可交互，双击即用、可部署 GitHub Pages，评委零成本体验。
- **确定性计算引擎**：四个零依赖 Python 脚本（Python 3.8+ 标准库）负责决策打分、券叠加计算、统计与人格匹配，机读 JSON / 人读文本双格式输出；demo 页 JS 逻辑与脚本输出经断言测试完全一致。

## 目标用户

| 用户 | 痛点 | 对应用模式 |
| --- | --- | --- |
| 选择困难症患者 | 每天中午对着菜单发呆 10 分钟 | 今天吃什么（smart/dice） |
| 精打细算的薅券党 | 不知道券怎么叠、怎么凑单最省 | 省钱军师 |
| 麦门信徒 / 数据控 | 想知道自己在麦当劳花了多少、是什么成分 | 麦门月报 + 人格鉴定 |
| 聚会组织者 | 多人拼单、AA 算账麻烦 | 省钱军师 + 月报（大额订单分析） |

## 安装

本仓库本身就是一个标准 WorkBuddy Skill，解压即用：

```bash
# 方式一：用户级安装（所有项目可用）
cp -r mcd-assistant ~/.workbuddy/skills/

# 方式二：项目级安装（随项目共享）
cp -r mcd-assistant <你的项目目录>/.workbuddy/skills/
```

前置条件：WorkBuddy 已连接麦当劳 MCP Server（mcd-mcp）并完成授权。安装后对话中说出「吃什么」「怎么点最便宜」「我的麦门月报」等即可触发。

## 使用示例

**模式一：今天吃什么**

> 用户：午饭预算 30，不想吃辣，帮我决定
> 小助手：（调用 now-time-info / query-meals / list-nutrition-foods 取数后）
> 麦门推荐：麦乐鸡(5块)（¥12.5 / 285 千卡）
> 推荐理由：合格池 12 个单品中综合得分最高：热量 285 千卡，负担适中，¥12.5 在预算 ¥30 内。
> 备选方案：麦香鱼(¥20.0)、猪柳蛋麦满分(¥17.5)、双层吉士堡(¥14.5)

**模式二：省钱军师**

> 用户：一个麦辣鸡腿堡 + 一个板烧鸡腿堡 + 大薯 + 两杯中可，怎么点最便宜？
> 小助手：（auto-bind-coupons 绑券 → available-coupons / query-promotions / calculate-price 校验后）
> == 神单方案 ==
> 原价：¥75.00 → 券后：¥44.20，节省 ¥30.80（41.1%）
> 用券步骤：1. 满40减8 2. 满60减15 3. 全场85折

**模式三：麦门月报 + 人格卡**

> 用户：看看我上个月在麦当劳花了多少，我是什么人格？
> 小助手：输出 Markdown 月报（核心数据表 + Top 5 单品 + 人格卡：深夜麦门信徒，附毒舌点评）
> 用户：给我一张能发群的卡
> 小助手：运行 persona_card.py 生成 HTML 人格鉴定卡（效果见 examples/persona_card_demo.html），截图即分享

**在线试算（免 Token）**：浏览器直接打开 `demo/index.html`（或部署后的 GitHub Pages 链接）——神单计算器可编辑购物车和优惠券实时算券，「今天吃什么」可调约束摇盲盒，「麦门月报」内置示例订单一键生成人格卡。无需 MCP、无需 Token、数据不出浏览器。

## 本地运行 Demo

三个脚本均可脱离 MCP 直接运行（内置示例数据）：

```bash
python scripts/meal_picker.py --demo --mode smart --budget 30
python scripts/meal_picker.py --demo --mode dice --seed 7
python scripts/coupon_optimizer.py --demo
python scripts/report_generator.py --demo --format md
python scripts/report_generator.py --demo --format json
python scripts/persona_card.py --demo --out card.html
```

在线试算页（无需 Python，双击即用）：

```bash
# 方式一：直接打开
start demo/index.html        # Windows
open demo/index.html         # macOS

# 方式二：部署 GitHub Pages（推送到仓库后在 Settings → Pages 开启）
```

示例输出见 [examples/](examples/) 目录。真实使用时，由 Skill 按 SKILL.md 流程从 MCP 取数、组装 JSON 后传入 `--data`。

## 目录结构

```text
mcd-assistant/
├── SKILL.md                    # Skill 主文件（三模式工作流 + 安全边界）
├── README.md                   # 本文件
├── CONTEST_DECLARATION.md      # 参赛声明（原创性/合规性/敏感信息）
├── MCP_INTEGRATION.md          # 麦当劳 MCP 集成说明
├── workbuddy.md                # WorkBuddy 开发对话上下文导出
├── demo/
│   └── index.html              # 免 Token 在线试算页（单文件，可部署 Pages）
├── scripts/
│   ├── meal_picker.py          # 今天吃什么决策引擎（smart/dice）
│   ├── coupon_optimizer.py     # 神单计算引擎（券叠加 + 凑单建议）
│   ├── report_generator.py     # 月报统计 + 人格匹配
│   └── persona_card.py         # 人格鉴定卡生成器（可分享 HTML）
├── references/
│   └── personas.md             # 麦门人格文案库（单一来源）
└── examples/                   # 脚本 demo 输出 + 人格卡示例
```

## 参赛文件说明

| 文件 | 说明 |
| --- | --- |
| `README.md` | 项目介绍、安装方法、使用示例、目标用户（本文件） |
| `CONTEST_DECLARATION.md` | 参赛声明：原创性、合规性、敏感信息 |
| `MCP_INTEGRATION.md` | 实际使用的麦当劳 MCP Server、Tool、调用流程与业务价值 |
| `SKILL.md` + `scripts/` + `references/` + `demo/` | 项目主体源代码（可运行的 Skill + 免 Token 在线试算页） |
| `workbuddy.md` | 使用 WorkBuddy 开发时的对话上下文导出 |
