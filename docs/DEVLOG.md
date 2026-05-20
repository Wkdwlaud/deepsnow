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

### 待讨论事项

- **Agent 主动调用工具的问题**：当用户问"腾讯最近表现怎么样"这类问题时，Agent 可能不会主动调用数据工具，而是直接从模型知识回答（数据可能过时、没有来源）。可以在 SOUL.md 中加入"遇到具体公司问题必须先调工具获取最新数据"的行为指令来解决。暂不实施，观察实际使用中的表现再决定是否需要。

### 下一步（Phase 2）

- [x] Stock Pool SQLite 数据库（独立于 Kanban）
- [x] 估值计算工具（PEG、未来市值法）
- [x] 报告生成工具
- [ ] 完整走通一次研究流程：研究 5-10 只科技股 → GREAT 评分 → 入池

---

## 2026-05-19 — Phase 2 完成：科技组完整模板就绪

### 完成内容

1. **港股工具** (`fetch_hk_stock_price`, `fetch_hk_stock_info`, `fetch_hk_stock_financials`)
   - 价格用 eastmoney + 新浪双后端 fallback
   - 财务指标用 `stock_financial_hk_analysis_indicator_em`（9 年历年 ROE/增速）
   - 端到端验证：腾讯(00700) 研究成功，PEG≈1.05

2. **Forward PEG 工具** (`calculate_forward_peg`)
   - 使用 `stock_profit_forecast_ths` 获取同花顺一致预期（分析师 EPS 预测）
   - 自动计算 Forward PE + EPS CAGR + Forward PEG
   - 验证：海康威视 Forward PEG=1.37，18 家机构覆盖，3 年 CAGR 13.7%

3. **Stock Pool 数据库** (`plugin/db/`)
   - 4 张表：stocks、great_scores、tracking_log、decision_log
   - 关键字段变更自动写入 tracking_log（审计日志）
   - 8 个工具：add/update/get/query/summary/great_score/log/decision_log_add
   - 验证：腾讯入 watch 池(GREAT 39)，海康入 reserve 池(GREAT 31)

4. **报告工具** (`save_report`, `list_reports`)
   - 保存到 `~/Documents/investment/reports/<sector>/<type>/YYYY-MM-DD_<code>_<name>.md`
   - 支持按 sector/type/code 过滤列表

5. **Handler 签名 bug fix**
   - Hermes 调用约定是 `handler(args_dict, **kwargs)`，第一个参数是完整 dict
   - 之前用命名参数接收导致类型错误，已全部修正

### 端到端验证结果

完整闭环跑通（hermes -p tech-analyst chat）：
- 研究海康威视 → 调用 19 次工具 → GREAT 评分 31/50 → 入 reserve 池 → 保存报告
- 研究腾讯 → 港股工具调用成功 → PE/PEG 计算正确 → 70%→95% 深度区分清晰
- SOUL.md 约束生效：拒绝判断市场季节，引导回公司研究

### 当前工具清单（共 19 个）

| 类别 | 工具 | toolset |
|------|------|---------|
| A股数据 | fetch_stock_financials, fetch_stock_price, fetch_stock_info, fetch_industry_constituents | investment-company |
| 港股数据 | fetch_hk_stock_price, fetch_hk_stock_info, fetch_hk_stock_financials | investment-company |
| 市场数据 | fetch_market_index, fetch_macro_indicator | investment-market |
| 估值 | calculate_pe_percentile, calculate_forward_peg | investment-company |
| 股票池 | stock_pool_add, stock_pool_update, stock_pool_get, stock_pool_query, stock_pool_summary, stock_pool_great_score, stock_pool_log, decision_log_add | investment-company |
| 报告 | save_report, list_reports | investment-company |

### 科技组模板能力总结

tech-analyst profile 现在具备完整研究闭环：
- **获取数据**：A 股 + 港股行情/财务/指标
- **估值分析**：PE 历史分位 + Forward PEG（一致预期）
- **框架评分**：GREAT 五维（通过 skill 引导）
- **持久化**：股票池 DB + 报告文件 + 审计日志
- **约束**：估值红线 + 物理隔离 + 拒绝越界

### 下一步

- [ ] 用科技组模板横向扩展其他研究组（消费/医药/周期/高股息）
- [ ] 搭建投委会 profiles（season-judge, coordinator）
- [ ] 月度工作流手动跑通

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
