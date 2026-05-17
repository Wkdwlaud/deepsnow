# DeepSnow 开发日志

## 2026-05-12 — Phase 1 完成：插件骨架 + 数据层 + 第一个 Profile

### 架构决策

经过对 Hermes Agent v0.13.0 源码的深度分析，确定了三层架构：

- **Profile**（持久化 Agent）：每个研究员/投委会成员是一个独立 Hermes profile，拥有自己的 SOUL.md、Memory、Skills，可自进化
- **Plugin**（共享工具层）：注册金融数据工具到两个隔离 toolset（`investment-company` / `investment-market`）
- **Kanban**（协调）：使用 Hermes 内建 Kanban 做跨 profile 任务协调

关键洞察：
- `delegate_task`（临时子 Agent）仍保留作为 profile 内部的提效工具，但不用来实现持久化团队
- 物理隔离通过 profile 的 `platform_toolsets` 配置实现，研究组看不到市场数据，投委会看不到个股数据
- Profile 的 Skills 系统（`skill_manage`）是自进化机制——Agent 在工作中主动创建/修改 Skills

### 完成内容

1. **Hermes 环境搭建**
   - hermes-agent 安装在 `hermes-agent/`
   - venv 内安装了 akshare
   - Hermes v0.13.0, Python 3.12.10

2. **Plugin 开发** (`plugin/`)
   - 7 个金融数据工具，全部测试通过（6/6 核心通过）
   - 数据源：akshare（新浪 + 同花顺后端，规避了 eastmoney 代理问题）
   - 两个隔离 toolset：`investment-company`（个股）、`investment-market`（市场）

3. **tech-analyst Profile** (`profiles/tech-analyst/`)
   - SOUL.md：角色定义 + 估值红线（禁止用 PE 否定成长股）
   - config.yaml：Sonnet 模型 + 仅 investment-company toolset
   - 3 个 Skills：GREAT 框架、成长股估值方法、科技行业框架

4. **项目结构**
   - 代码在 `~/Documents/investment/deepsnow/`（git 仓库）
   - 通过 `setup.sh` 创建符号链接到 `~/.hermes/plugins/` 和 `~/.hermes/profiles/`
   - Hermes 通过符号链接发现插件和 profile，升级 Hermes 零影响

### 数据层验证结果

| 工具 | 状态 | 数据源 | 备注 |
|------|------|--------|------|
| fetch_stock_financials | ✅ | 同花顺 (ths) | 数据排序 old→new，取 tail |
| fetch_stock_price | ✅ | 新浪 (sina) | stock_zh_a_daily，需要加市场前缀 |
| fetch_stock_info | ✅ | sina + ths 组合 | |
| fetch_market_index | ✅ | sina | stock_zh_index_daily |
| fetch_macro_indicator | ✅ | akshare 宏观 | 数据排序 new→first，取 head |
| calculate_pe_percentile | ✅ | sina价格 + ths EPS | 需找最近有效EPS行 |
| fetch_industry_constituents | ⚠️ | eastmoney 被代理阻断 | 有 fallback 到 ths summary |

### 已知问题

- eastmoney API（`push2.eastmoney.com`, `push2his.eastmoney.com`）被本机代理阻断，影响 `stock_zh_a_hist` 和 `stock_board_industry_cons_em`
- 已用新浪/同花顺后端替代，功能不受影响
- `stock_financial_abstract_ths` 部分历史数据返回 `False`（早期报告期无数据），已处理

### 下一步（Phase 2）

- [ ] Stock Pool SQLite 数据库（独立于 Kanban）
- [ ] 估值计算工具（PEG、未来市值法）
- [ ] 报告生成工具
- [ ] 完整走通一次研究流程：研究 5-10 只科技股 → GREAT 评分 → 入池

---

## 待开始 — Phase 3：投委会 + 月度工作流

- [ ] season-judge profile（季节判断）
- [ ] coordinator profile（协调 Agent，用 Opus 模型）
- [ ] 月度投委会手动流程跑通

## 待开始 — Phase 4：全员 + Kanban + Cron

- [ ] 剩余 4 个研究组 profile
- [ ] Kanban dispatcher 协调月度流程
- [ ] Cron 定时触发日/周/月频工作流

---

## 环境信息

- Hermes Agent: v0.13.0
- Python: 3.12.10
- akshare: 1.18.60
- OS: macOS Darwin 24.6.0
- LLM: Anthropic Claude (Sonnet for research, Opus for coordination)
- 项目路径: `~/Documents/investment/deepsnow/`
- Hermes 路径: `~/Documents/investment/hermes-agent/`
- 远端仓库: `git@github.com-personal:Wkdwlaud/deepsnow.git`
