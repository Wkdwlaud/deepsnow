# AI 投研团队 — 技术框架选型分析

> 本文档完整记录了为"个人 AI 投研团队"选择代码实现框架的调研、分析与决策过程。
> 调研基于三个本地框架源码的深度分析，以及对主流 multi-agent 框架的外部调研。
>
> 日期：2026-05-11
> 关联文档：`AI投研团队设计-v2.md`（系统设计文档）

---

## 1. 选型背景与需求

### 1.1 我们要构建什么

基于吴伟志（中欧瑞博）的投资组织架构，构建一个 multi-agent 投资研究系统。该系统包含：

- **10+ 个专用 Agent**：5 个行业研究组（消费/医药/科技/周期/高股息）、4 个投委会 Agent（季节判断/风格判断/共识阶段/风险预警）、1 个量化辅助 Agent、1 个协调 Agent
- **结构化工作流**：日频（5-10分钟）、周频（30-60分钟）、月频（2-3小时）、季频（半天）、事件触发
- **持久化状态管理**：股票池数据库（四层分级，150+公司档案）、决策日志
- **双轨并行 + 共享服务 + 下游合流的 Agent 通信架构**（详见下图）
- **人在回路（Human-in-the-loop）**：所有最终决策由人完成，Agent 只提供研究素材
- **工具使用**：金融数据获取、估值计算、报告生成
- **文档产出**：深度报告、跟踪报告、会议材料包、板块温度地图
- **定时调度**：月度投委会、周报、日频推送等定期自动触发

**Agent 间关系架构**：

```
                     基金经理（你）
                          │
               ┌──────────┴──────────┐
               │                     │
     投研组（找好公司）          投委会（定季节/仓位）
     5个研究组Agent              4个投委会Agent
     独立运行，不看市场季节      独立运行，不看具体公司
          │                          │
          │    ┌─────────────┐       │
          ├───→│ 量化辅助Agent│←──────┤
          │    │ (共享数据层) │       │
          │    │ 无状态，被动  │       │
          │    │ 不交叉传递   │       │
          │    └─────────────┘       │
          │                          │
          ▼                          ▼
       ┌─────────────────────────────────┐
       │         协调 Agent               │  ← 唯一合流点
       │   整合两条独立线的输出            │
       │   生成会议材料 + 纪律校验         │
       └──────────────┬──────────────────┘
                      │
               ┌──────▼──────┐
               │   股票池     │
               │   决策日志   │
               └─────────────┘

关键约束：
- 投研组 ↔ 投委会：并列独立，互不通信，物理隔离
- 量化辅助 ↔ 两者：共享工具层，被动响应请求，不主动传递，无状态
- 协调Agent ↔ 两者：下游合流点，接收两条线的独立输出，整合后交给人决策
```

### 1.2 核心约束

1. **个人投资者场景**：不需要分布式部署或企业级基础设施，但需要长期可靠运行
2. **金融数据处理**：需要与 Python 金融数据生态（akshare/tushare/pandas/matplotlib）深度集成
3. **方法论嵌入**：吴伟志的投资框架（四季理论、GREAT五维、建仓纪律、估值闭环等）必须硬编码进 Agent 的 Prompt 和工具中
4. **可审计性**：所有决策必须有据可查，支持季度复盘归因
5. **可迭代**：框架选择必须支持渐进式开发，不要求一次性搭建完整

### 1.3 评估维度

| 维度 | 说明 | 权重 |
|------|------|------|
| 多Agent编排 | 10+Agent的角色定义、通信、并行执行 | 最高 |
| 状态持久化 | 股票池、决策日志、研究成果的跨会话存储 | 最高 |
| 定时调度 | 日/周/月/季频工作流的自动触发 | 高 |
| Python金融生态 | 与 akshare/tushare/pandas 等的集成便利性 | 高 |
| 人在回路 | 人工审批、决策确认机制 | 高 |
| 工具灵活性 | 自定义金融数据工具、估值计算工具 | 高 |
| 记忆/知识管理 | 行业框架文档、研究积累的跨会话复用 | 中 |
| 模型灵活性 | 不锁定单一模型提供商 | 中 |
| 开源协议 | 可合法修改和构建 | 前提条件 |
| 成熟度 | 是否经过生产验证 | 中 |

---

## 2. 三个本地框架源码深度分析

### 2.1 Claude Code

**源码路径**：` <local>/claude-code`

#### 2.1.1 项目本质

这是 Anthropic 官方 Claude Code CLI 工具的源码快照——通过 npm 包的 source map 泄露获取，用于研究目的存档。它**不是**一个面向外部开发者的开源框架或 SDK。

- **语言**：TypeScript（strict 模式）
- **运行时**：Bun
- **UI**：React + Ink（终端渲染）
- **规模**：约 1,900 个文件，512,000+ 行代码
- **协议**：专有（非开源，不可合法构建于其上）

#### 2.1.2 核心抽象

1. **Tool**（`/src/Tool.ts`）— 基础原语。每个 Tool 定义了输入 schema（Zod 验证）、权限模型、执行逻辑（`call()`）、校验、UI 渲染。Tool 是 Agent 能力的单位。

2. **AgentDefinition**（`/src/tools/AgentTool/loadAgentsDir.ts`）— 三种类型：
   - `BuiltInAgentDefinition`（source: `'built-in'`）— 如 Explore、Plan、Verification、General-Purpose
   - `CustomAgentDefinition`（source: user/project/policy settings）— 通过 Markdown frontmatter 或 JSON 定义
   - `PluginAgentDefinition`（source: `'plugin'`）— 第三方插件

3. **ToolUseContext**（`/src/Tool.ts`）— 传递给每个 Tool 的执行上下文，包含 AppState、abort controller、文件状态缓存、MCP clients、Agent 定义等。

4. **消息类型**（user、assistant、progress、system）— LLM 与 Tool 之间的会话协议。

5. **QueryEngine**（`/src/QueryEngine.ts`）— 核心 LLM API 调用引擎，处理流式传输、tool-call 循环、重试。

#### 2.1.3 多Agent编排能力

Claude Code 具有**广泛的、生产级的多Agent支持**，通过多个互补系统实现：

**A. Coordinator 模式**（`/src/coordinator/coordinatorMode.ts`）

主 Claude 实例变成一个**编排者**，只负责指挥 worker。关键特性：
- 通过 `AgentTool` 派生 worker
- 通过 `SendMessageTool` 与 worker 通信
- Worker 以 `<task-notification>` XML 格式在 user-role 消息中报告结果
- 完整的系统 prompt 定义了分阶段流程：Research → Synthesis → Implementation → Verification
- 并行 worker 派发是一等模式
- Worker 可以被停止和恢复

**B. AgentTool / 子Agent派生**（`/src/tools/AgentTool/`）

`runAgent()` 函数（`/src/tools/AgentTool/runAgent.ts`，860+ 行）是核心子Agent执行引擎：
- 创建隔离的 Agent 上下文：独立的工具集、abort controller、MCP servers、文件状态
- 支持**同步**（阻塞）和**异步**（后台）两种 Agent
- 每个 Agent 有自己的 system prompt、模型、权限模式、工具集
- 内置 Agent：`general-purpose`、`Explore`、`Plan`、`Verification`、`claude-code-guide`
- 通过 Markdown 文件 + YAML frontmatter 定义自定义 Agent
- 每个 Agent 可配置专属 MCP server（叠加到父级）
- 每个 Agent 有 transcript 记录
- 可设置 max turns 限制

**C. Team/Swarm 系统**（`/src/tools/shared/spawnMultiAgent.ts`、`/src/utils/swarm/`）

完整的 **Agent 集群**实现，支持三种后端模式：
1. **tmux** — 每个 teammate 在 tmux pane 中作为独立 Claude Code 进程运行
2. **iTerm2** — 原生 iTerm2 分屏
3. **In-process** — 所有 teammate 在同一个 Node.js 进程中（通过 AsyncLocalStorage）

特性：
- `TeamCreateTool` — 创建团队
- `TeamDeleteTool` — 拆除团队
- `SendMessageTool` — 基于**邮箱系统**（文件级 inbox/outbox）的 Agent 间通信
- 广播消息（`to: "*"`）
- 关闭协商协议（request/approve/reject）
- Plan 审批工作流（team lead 审批 teammate 的计划）
- 颜色区分 Agent
- 唯一 Agent ID，通过 team 文件追踪成员关系
- 权限模式从 leader 继承到 teammates
- 每个 teammate 可选择不同模型

**D. SendMessageTool**（`/src/tools/SendMessageTool/SendMessageTool.ts`）

完整的 Agent 间通信：
- 向指定 Agent 发送直接消息
- 向所有团队成员广播
- 用新消息恢复已停止的 Agent
- 结构化协议消息（shutdown、plan approval）
- 通过 UDS socket 和 Remote Control bridge 的跨会话通信
- 通过 Agent ID 或名称路由到进程内子 Agent

**E. Task 管理**（`/src/tasks/`）
- `LocalAgentTask` — 追踪运行中的本地子 Agent
- `InProcessTeammateTask` — 追踪进程内 teammate
- `RemoteAgentTask` — 追踪远程 Agent
- `LocalShellTask` — 后台 shell 命令
- 完整的 Task 生命周期管理，带 abort controller

#### 2.1.4 是否包含 "Agent SDK" 组件？

部分包含。源码中引用了 SDK 入口：
- `process.env.CLAUDE_CODE_ENTRYPOINT === 'sdk-ts' | 'sdk-py' | 'sdk-cli'`
- `CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS` 环境变量
- `/src/entrypoints/agentSdkTypes.ts`（有引用但未深入暴露）
- 系统支持非交互模式的编程化使用

Agent 定义系统（`loadAgentsDir.ts`）支持通过以下方式定义自定义 Agent：
- 带 YAML frontmatter 的 Markdown 文件（name、description、tools、model、permissions、MCP servers、hooks、skills、isolation mode、max turns）
- settings 文件中的 JSON 配置
- Plugin 提供的 Agent

#### 2.1.5 对投研系统的适用性评估

**结论：不适合作为框架直接使用，但在架构设计上极具参考价值。**

**不适合的原因**：

1. **不是库/框架** — 它是一个整体式 CLI 应用。你无法 `import` 它作为依赖来扩展。没有公开的 API 用于编程化的多 Agent 编排。

2. **紧耦合 Anthropic Claude API** — 整个系统围绕 Anthropic 的特定 LLM API 构建，深度集成了其流式传输协议、tool-use 格式和模型别名。

3. **不面向领域定制 Agent** — Agent 系统为软件工程任务设计（代码搜索、文件编辑、git 操作）。没有金融数据管道、金融 API 或研究工作流的概念。

4. **基础设施复杂度** — tmux/iTerm2/in-process 集群系统为开发者终端构建，不适合生产服务器部署。

5. **无公开 API/许可证** — 这是泄露的专有代码，不可合法构建于其上。

**值得作为架构灵感的部分**：

1. **Agent 定义模式** — 通过结构化配置（frontmatter + system prompt + tool allowlist + model selection + permission mode）定义 Agent，这个模式非常适合我们的 10+ 个专用 Agent。

2. **Coordinator/Worker 架构** — Coordinator 模式的分阶段工作流（Research → Synthesis → Implementation → Verification）直接可用于投资研究的月度投委会流程。

3. **邮箱式 Agent 间通信** — 基于文件的 inbox/outbox 通信模式简洁有效。

4. **Tool 权限按 Agent 分级** — 每个 Agent 有自己的 tool allowlist，是很好的隔离模式。对我们来说意味着研究组 Agent 只能用公司数据工具，投委会 Agent 只能用市场数据工具。

5. **Task 通知协议** — Worker 通过结构化 XML 通知报告结果，Coordinator 进行综合——这是一个清晰的关注点分离。

#### 2.1.6 关键源码文件索引

| 路径 | 用途 |
|------|------|
| `src/coordinator/coordinatorMode.ts` | Coordinator 模式切换、system prompt、worker tool context |
| `src/tools/AgentTool/runAgent.ts` | 核心子Agent执行引擎（860+ 行） |
| `src/tools/AgentTool/loadAgentsDir.ts` | Agent 定义类型和解析（Markdown/JSON） |
| `src/tools/AgentTool/builtInAgents.ts` | 内置 Agent 注册表 |
| `src/tools/shared/spawnMultiAgent.ts` | Team/Swarm 派生（tmux、iTerm2、in-process） |
| `src/tools/SendMessageTool/SendMessageTool.ts` | Agent 间通信（邮箱、广播、路由） |
| `src/Tool.ts` | 核心 Tool 和 ToolUseContext 类型定义 |
| `src/utils/swarm/` | Swarm 基础设施（21 个文件） |
| `src/tasks/` | Task 生命周期管理 |

---

### 2.2 Hermes Agent

**源码路径**：` <local>/hermes-agent`

#### 2.2.1 项目本质

Hermes Agent 是由 Nous Research 开发的开源自主 AI Agent 框架。版本 0.13.0，MIT 协议。它是一个功能完整的自主编程和任务执行 Agent（可类比 Claude Code、OpenAI Codex、OpenClaw），可在终端、消息平台（Telegram、Discord、Slack、WhatsApp、Signal、Matrix 等）和 IDE 中运行。

其区分性特征是**封闭学习循环** — 从经验中创建技能（Skills），在使用中改进它们，跨会话持久化知识，并随时间构建用户模型。

- **语言**：Python 3.11+，使用 setuptools
- **辅助语言**：TypeScript/Node.js 用于 TUI（`ui-tui/` 中的 Ink/React 终端 UI）
- **构建系统**：setuptools，通过 `uv`（现代 Python 包管理器）管理
- **协议**：MIT

#### 2.2.2 核心抽象

| 抽象 | 文件 | 用途 |
|------|------|------|
| **AIAgent** | `run_agent.py` | 核心对话循环类（约 12,000 行）。接收约 60 个参数。同步 tool-calling 循环，支持中断、预算追踪。 |
| **Tool Registry** | `tools/registry.py` | 中央工具注册系统。工具在 import 时通过 `registry.register()` 自注册。 |
| **Toolsets** | `toolsets.py` | 命名工具组（如 "web"、"terminal"、"file"、"delegation"、"kanban"）。复合 toolset 可捆绑多个 toolset。 |
| **SessionDB** | `hermes_state.py` | SQLite 支持的会话持久化，带 FTS5 全文搜索。 |
| **MemoryManager** | `agent/memory_manager.py` | 可插拔记忆提供者系统（内置、Honcho、Mem0、Supermemory 等）。 |
| **Skills** | `skills/`、`agent/skill_commands.py` | 程序化记忆 — 可复用的技能文档，按需加载到会话中。 |
| **Gateway** | `gateway/` | 多平台消息适配器（Telegram、Discord、Slack，15+ 平台）。 |
| **Cron Scheduler** | `cron/scheduler.py` | 内建定时任务执行。 |
| **Context Engine** | `agent/context_engine.py` | Prompt 组装、上下文压缩、缓存。 |

#### 2.2.3 多Agent编排能力

Hermes 有**两个不同的多 Agent 系统**：

**A. Delegate Tool（子Agent架构）**

文件：`tools/delegate_tool.py`

`delegate_task` 工具派生子 `AIAgent` 实例：
- **隔离上下文** — 全新对话，不继承父级历史
- **独立 task_id** — 独立终端会话、文件操作缓存
- **受限工具集** — 可配置，blocked tools 被移除（叶子节点子Agent 不能递归委托，不能使用 clarify/memory/send_message）
- **聚焦 system prompt** — 基于委托目标 + 上下文构建

**两种模式**：
- **单任务**：`delegate_task(goal="...", context="...", toolsets=[...])`
- **批量（并行）**：`delegate_task(tasks=[{goal, context, toolsets, role}, ...])`

**角色系统**：
- `role="leaf"`（默认） — 不能进一步委托
- `role="orchestrator"` — 保留 delegation toolset，可以派生自己的 worker

**深度控制**：通过 `delegation.max_spawn_depth` 配置（默认 1 = 扁平；最大 3 层嵌套编排）。父 Agent 阻塞等待所有子 Agent 完成。子 Agent 在 `ThreadPoolExecutor` 中运行，可配置并发数（默认 3，可配置到 10+）。

**关键配置项**：
- `delegation.max_concurrent_children`（默认 3）
- `delegation.child_timeout_seconds`（默认 600 秒）
- `delegation.max_spawn_depth`（1-3）
- `delegation.orchestrator_enabled`（总开关）
- `delegation.subagent_auto_approve`（危险命令自动审批）
- `delegation.provider` / `delegation.model`（将子 Agent 路由到更便宜的模型）

**B. Kanban 多Agent看板**

文件：`hermes_cli/kanban_db.py`、`hermes_cli/kanban.py`、`tools/kanban_tools.py`

一个 **SQLite 持久化的看板系统**，用于多 profile、多项目协作。这是一个持久的、跨 profile 的协调原语：

- **Dispatcher**（运行在 gateway 中）认领任务并派生 worker Agent
- **Worker** 作为独立 Hermes 实例派生，带隔离 profile
- Worker 使用结构化工具调用（`kanban_complete`、`kanban_block`、`kanban_heartbeat`、`kanban_comment`）向看板回报
- **Orchestrator profile**（如 "techlead"）可以 list、create、unblock、fan out 任务
- 任务状态流转：`todo` → `ready` → `running` → `done`/`blocked`/`archived`
- CAS（compare-and-swap）并发控制 — 无需分布式锁
- 支持多个看板（项目）、工作区隔离（worktree、Docker、scratch dir）
- 任务关联、评论、事件、优先级、技能分配

#### 2.2.4 能力矩阵

| 能力 | 是否支持 | 机制 |
|------|---------|------|
| **多角色 Agent** | 是 | `delegate_task` 支持 `role="leaf"` vs `role="orchestrator"`；Kanban profile 带不同配置；每个子 Agent 获得基于目标构建的自定义 system prompt |
| **Agent 间通信** | 是（结构化） | 父 Agent 只看到委托摘要结果（看不到中间 tool 调用）。Kanban worker 通过 `kanban_comment`/`kanban_complete` 工具回报。ACP 适配器用于 IDE ↔ Agent 通信。进度回调从子 Agent 传递到父 Agent 显示。 |
| **工具使用** | 是（丰富） | 40+ 内置工具，按 toolset 组织。自注册模式。MCP server 集成。插件注入工具。子 Agent 继承父级工具（带限制）。 |
| **状态持久化** | 是 | SQLite 会话（FTS5 搜索）、持久化记忆（多后端）、技能系统（程序化记忆）、Kanban 看板 DB、对话历史。 |
| **人在回路** | 是 | `clarify` 工具（向用户提问）、`approval.py`（危险命令审批，带会话级状态、辅助 LLM 智能自动审批）、gateway 审批队列。子 Agent 默认自动拒绝（可配置）。Kanban `kanban_block` 暂停等待人工输入。 |

#### 2.2.5 多Agent模式示例

1. **并行研究**：父 Agent 批量委托任务给多个 leaf Agent，每个并发研究不同主题。

2. **嵌套编排**：父 Agent 派生一个 orchestrator 子 Agent（depth 1），后者自己再派生 leaf worker（depth 2）处理子问题。最大 3 层嵌套。

3. **Kanban 管线**：一个 "techlead" orchestrator profile 在看板上创建任务；dispatcher 认领并分配给带适当技能和工作区隔离的 worker Agent。Worker 通过 completion/blocking 回报看板。

4. **凭证路由**：子 Agent 可通过 `delegation.provider` 配置路由到不同/更便宜的 LLM 提供商，而父 Agent 使用昂贵模型。

#### 2.2.6 架构总览

```
                    ┌──────────────────────────────────────────┐
                    │              CLI / Gateway / TUI          │
                    │   (hermes, hermes gateway, hermes --tui)  │
                    └─────────────────────┬────────────────────┘
                                          │
                    ┌─────────────────────▼────────────────────┐
                    │            AIAgent (run_agent.py)          │
                    │  - 对话循环                                │
                    │  - 通过 model_tools.py 进行 Tool 调用      │
                    │  - 预算/中断追踪                           │
                    │  - Provider 无关（OpenAI API 兼容）        │
                    └───┬────────────┬──────────────┬───────────┘
                        │            │              │
          ┌─────────────▼──┐   ┌────▼─────┐   ┌───▼────────────┐
          │  Tool Registry  │   │  Memory  │   │  Delegate Tool  │
          │  (40+ 工具)     │   │  Manager │   │  (子Agent)      │
          │  - terminal     │   │  - honcho│   │  - ThreadPool   │
          │  - file ops     │   │  - mem0  │   │  - role: leaf/  │
          │  - web          │   │  - ...   │   │    orchestrator │
          │  - browser      │   └──────────┘   │  - 批量模式     │
          │  - kanban       │                  └────────┬────────┘
          │  - MCP tools    │                           │
          └────────────────┘              ┌─────────────▼──────────┐
                                          │  子 AIAgent(s)          │
                                          │  - 隔离上下文            │
                                          │  - 受限工具集            │
                                          │  - 独立终端会话          │
                                          └─────────────────────────┘

  ┌────────────────────────────────────────────────────────────────────┐
  │  Kanban Board (kanban_db.py) — 跨 profile 协调                     │
  │  Dispatcher → 认领任务 → 派生 worker 进程                          │
  │  Worker → kanban_complete/block/heartbeat → 结构化交接              │
  └────────────────────────────────────────────────────────────────────┘
```

**关键设计决策**：
- 同步 Agent 循环（非 async），使用线程池并行化子 Agent
- OpenAI 兼容消息格式（`system/user/assistant/tool` 角色）
- 子 Agent 看不到父级历史；父 Agent 看不到子 Agent 中间步骤
- 工具集继承取交集（子 Agent 不能获得父级没有的工具）
- 模块级状态管理子 Agent 注册表，支持 TUI 观察和中断传播
- SQLite WAL 模式 + CAS 用于并发 Kanban 协调（无需分布式锁）

---

### 2.3 OpenClaw

**源码路径**：` <local>/openclaw`

#### 2.3.1 项目本质

OpenClaw 是一个**个人 AI 助手网关**，在你自己的设备上运行。它**不是**一个通用的多 Agent 编排框架（如 LangGraph 或 CrewAI），而是一个单用户 AI 助手平台，内置了多 Agent 路由和子 Agent 派生能力。

- **语言**：TypeScript（ESM，strict 模式），使用 pnpm workspaces 的 monorepo
- **版本**：2026.5.10-beta.1
- **协议**：MIT

#### 2.3.2 核心架构

OpenClaw 有一个**以 Gateway 为中心的架构**：

1. **Gateway（守护进程）** — 一个长驻进程，拥有所有消息接口和 Agent 运行时。通过类型化 WebSocket API 暴露控制面。位于 `src/gateway/`。

2. **嵌入式 Agent 运行时** — 构建在 "Pi agent core"（`@earendil-works/pi-agent-core`）之上。每个 Gateway 进程一个 Agent 运行时，带 workspace、bootstrap 文件和 session store。位于 `src/agents/`。

3. **插件系统** — 丰富的插件 API，包括代码插件（运行时 hooks）和 bundle 式插件（skills、MCP servers）。扩展位于 `extensions/`（150+ 插件覆盖模型提供商、频道、工具）。

4. **多频道收件箱** — 支持 25+ 消息频道：WhatsApp、Telegram、Slack、Discord、Signal、iMessage、IRC、Matrix、Teams、WeChat、QQ 等。

#### 2.3.3 多Agent能力

**A. 多角色 Agent — 是**

每个 Agent 是一个完全隔离的人格（persona）：
- 独立 **workspace**（包含 `AGENTS.md`、`SOUL.md`、`USER.md` 用于人格/指令）
- 独立 **state directory**（`agentDir`），带认证 profile 和模型注册
- 独立 **session store**（聊天历史 + 路由状态）
- 每 Agent 可配置模型、工具策略、沙箱设置

通过 `~/.openclaw/openclaw.json` 的 `agents.list[]` 配置。

**B. Agent 间通信 — 是（多种机制）**

- **子Agent**（`sessions_spawn`）：Agent 可在独立会话中派生隔离的后台 Agent 运行（`agent:<agentId>:subagent:<uuid>`）。结果回传给请求方会话。关键文件：`src/agents/subagent-spawn.ts`。
  - 派生模式：`"run"`（一次性后台任务）或 `"session"`（持久线程绑定会话）
  - 上下文模式：`"isolated"`（干净子 transcript，默认）或 `"fork"`（分支请求方 transcript 到子 Agent）

- **跨会话消息**（`sessions_send`）：Agent 可向其他会话发送消息。

- **Agent 间工具**（`tools.agentToAgent`）：配置级别的显式 opt-in，用于 Agent 间通信。

- **ACP（Agent Client Protocol）**：外部编程工具（Claude Code、Gemini CLI 等）可通过 ACP 后端插件连接。文件：`docs/tools/acp-agents.md`。

**C. 工具使用 — 是（一等公民）**

核心工具：
- `exec`（bash）、`read`、`write`、`edit`、`apply_patch`
- `browser`、`canvas`、`nodes`、`cron`
- 会话工具：`sessions_list`、`sessions_history`、`sessions_send`、`sessions_spawn`、`sessions_yield`、`subagents`、`session_status`
- MCP server 支持（同时作为 server 和 client）
- Skills 系统（workspace 本地 + 托管 + ClawHub 捆绑技能）

工具基础设施在 `src/tools/`，带 planner、可用性评估和协议描述符。

**D. 状态持久化 — 是**

- **会话 transcript**：以 JSONL 存储在 `~/.openclaw/agents/<agentId>/sessions/<SessionId>.jsonl`
- **上下文引擎**：`src/context-engine/` 中的可插拔上下文管理，带组装、压缩、摄取和 bootstrap
- **记忆插件**：多记忆后端（LanceDB、wiki 式）。同一时间只能激活一个。
- **子Agent注册表**：将子 Agent 运行记录持久化到磁盘
- **会话写锁**：基于文件的锁，保证 transcript 一致性

**E. 人在回路 — 是**

- **Exec 审批**（`docs/tools/exec-approvals.md`）：命令需要策略 + 白名单 + 可选用户审批
- **Companion apps**（macOS/iOS）可弹出审批提示
- 可配置审批模式：`always`、`on-miss`、YOLO 模式
- 原生聊天审批客户端（如 Matrix reaction 快捷方式）
- **DM pairing**：未知发送者获得配对码；操作员通过 `openclaw pairing approve` 审批
- **Steering**：用户可通过 `/steer` 命令在 Agent 运行中途进行引导

#### 2.3.4 核心原语

1. **Agent** — 完全作用域化的"大脑"，带 workspace、auth、session store、模型配置、工具策略
2. **Session** — 单个对话 transcript（键为 `agent:<agentId>:<key>`）
3. **Gateway** — 路由消息、管理会话、服务 WebSocket API 的控制面
4. **Binding** — 通过 (channel, account, peer) 匹配将入站频道消息路由到 Agent
5. **Sub-agent Run** — 被追踪的后台 Agent 执行，带完整生命周期（spawn → run → announce → cleanup）
6. **Context Engine** — 可插拔的对话上下文组装/压缩
7. **Plugin** — 通过代码插件或 bundle 式插件进行运行时扩展
8. **Skill** — Markdown 格式的 prompt 文件，加载到 Agent 上下文中
9. **Tool** — 类型化工具描述符，带可用性表达式和执行处理器
10. **Channel** — 消息接口适配器（WhatsApp、Telegram 等）

#### 2.3.5 多Agent模式

1. **并行委托**：主 Agent 派生多个子 Agent 进行并发研究/任务，然后 yield（`sessions_yield`）等待完成。

2. **隔离路由**：不同频道账号/对等方路由到完全隔离的 Agent 人格（不同 workspace、模型、工具策略）。

3. **Coordinator 模式**：`delegationMode: "prefer"` 告诉主 Agent 保持响应性并委托工作。可配置嵌套深度（`DEFAULT_SUBAGENT_MAX_SPAWN_DEPTH`）和每 Agent 最大并发子 Agent。

4. **ACP 外部工具**：通过 Agent Client Protocol 编排外部编程工具（Claude Code、Gemini CLI）作为子 Agent 会话。

5. **线程绑定会话**：在支持线程的频道上，子 Agent 可通过 `mode: "session"` 和 `thread: true` 绑定到持久线程。

#### 2.3.6 对投研系统的适用性评估

OpenClaw 是一个**生产级的个人 AI 助手网关基础设施**，其多 Agent 能力主要面向：
- **路由隔离**：多个命名 Agent，各有独立人格、工具和模型，按频道/对等方绑定路由
- **子Agent派生**：后台任务委托，带生命周期管理、完成通知和可配置嵌套
- **会话工具**：跨会话消息、历史回溯和编排原语
- **插件可扩展性**：150+ 插件覆盖模型提供商、频道、记忆和能力

它是为**单操作员跨多消息频道运行个人助手**而设计的生产级基础设施，**不是**用于构建任意 Agent 架构的通用多 Agent 框架 SDK。其多 Agent 功能服务于并行工作委托和人格隔离的目标，而非协作式多 Agent 工作流。

---

## 3. 外部多Agent框架调研

### 3.1 框架对比总览

| 特性 | **CrewAI** | **LangGraph** | **AutoGen** | **OpenAI Agents SDK** | **Anthropic** |
|------|-----------|--------------|-------------|----------------------|---------------|
| **版本** | v1.14.4（稳定） | v1.1.10（稳定） | v0.7.5（pre-1.0） | v0.17.1（pre-1.0） | 无专用 Agent SDK |
| **成熟度** | 生产就绪 | 生产就绪 | 成熟中 | 快速演进 | N/A（使用 `anthropic` SDK v0.100） |
| **语言** | 仅 Python | Python + TypeScript（JS v1.3.0） | Python + .NET | Python + TypeScript（JS v0.11.3） | Python + TypeScript（基础 SDK） |
| **多Agent** | 角色 Crew + Flow；定义角色的 Agent 协作 | 图状态机；节点=Agent，边=转换 | Actor 模型 Team；事件驱动分布式会话 | Handoff + agent-as-tool；专用 Agent 间委托 | 自建：tool_use + MCP |
| **状态持久化** | 内建（aiosqlite、memory） | 一等公民（langgraph-checkpoint v4.0.3，Postgres、SQLite） | 通过 autogen-core 运行时的事件驱动状态 | Session（自动跨运行的会话历史） | 手动（无内建多Agent状态） |
| **定时调度** | 通过 CrewAI Cloud（托管） | 通过 LangGraph Platform（类 cron） | 无内建；自带 | 无内建 | 无内建 |
| **人在回路** | 任务中内建审批步骤 | 中断节点、图中断点 | Human proxy Agent 模式 | 内建 HITL 机制 | tool_use + 用户确认（手动） |
| **工具灵活性** | 自定义工具 + MCP（内建 MCP 依赖） | LangChain 工具 + 自定义函数 | 函数调用、自定义工具 | Functions + MCP + 托管工具 + guardrails | tool_use API + MCP 协议 |
| **模型灵活性** | 全（OpenAI 兼容 + LiteLLM） | 全（任何 LangChain 支持的模型） | 全（OpenAI、Anthropic 等） | 全（100+ LLM 通过配置） | 仅 Claude |

### 3.2 各框架详细评估

#### CrewAI（v1.14.4）

**核心模式**：角色制 Crew 协作。每个 Agent 定义 role、goal、backstory、tools，Agent 们组成 Crew 协作完成任务。

**优势**：
- 角色定义范式与投研团队的"研究员"、"策略师"、"风控员"天然吻合
- 原型搭建最快（1-2 周可出 MVP）
- 已达 v1.0+，有托管云服务
- 内建 MCP 支持

**劣势**：
- 仅 Python，无 TypeScript 选项
- 状态持久化能力不如 LangGraph 成熟
- 复杂编排模式（如嵌套 Agent、条件分支）的灵活性有限
- 定时调度依赖 CrewAI Cloud（托管服务），本地无内建

#### LangGraph（v1.1.10）

**核心模式**：图状态机。节点是 Agent 或处理步骤，边是状态转换。支持条件分支、循环、并行。

**优势**：
- 状态持久化是一等公民（Postgres、SQLite checkpoint），对股票池和决策日志至关重要
- 图模式天然适合复杂工作流（数据采集→分析→风险评估→报告生成）
- 人在回路通过中断节点和断点实现，控制精确
- 通过 LangGraph Platform 支持类 cron 调度
- 可审计性最强（每步有 checkpoint，可回溯任意状态）
- 有 TypeScript 版本

**劣势**：
- 需要从零搭建所有领域逻辑
- LangChain 生态可能偏重（引入的依赖多）
- 学习曲线比 CrewAI 陡峭
- 初始设置工作量最大

#### AutoGen（Microsoft，v0.7.5）

**核心模式**：Actor 模型。事件驱动的分布式多 Agent 会话。

**优势**：
- 适合真正的分布式系统
- .NET 支持（如果需要）

**劣势**：
- 仍为 pre-1.0，API 稳定性不足
- 学习曲线最陡
- 对个人投资者场景过于重量级

#### OpenAI Agents SDK（v0.17.1）

**核心模式**：Handoff 委托。Agent 之间通过 handoff 传递控制权。

**优势**：
- 轻量优雅
- 现已支持多模型提供商（100+）
- 内建 Session 和 HITL
- 有 TypeScript 版本

**劣势**：
- 仍为 pre-1.0，API 快速演进，稳定性堪忧
- 定时调度无内建
- 状态持久化较简单

#### Anthropic（基础 SDK v0.100）

**无专用 Agent SDK**。使用基础 `anthropic` Python SDK 的 tool_use 和 MCP 构建，完全自控但无编排原语。

---

## 4. 三个本地框架对比总结

| 维度 | Claude Code | Hermes Agent | OpenClaw |
|------|------------|--------------|----------|
| **可合法构建** | ✗ 专有泄露代码 | ✓ MIT 开源 | ✓ MIT 开源 |
| **语言** | TypeScript | **Python** | TypeScript |
| **金融数据生态** | 差（TS 无 pandas 等） | **最优**（Python 原生） | 差（TS 无 pandas 等） |
| **多Agent模式** | 最丰富（Coordinator + Team/Swarm + Mailbox） | **丰富**（Delegate + Kanban） | 中等（路由 + SubAgent） |
| **定时调度** | 会话级（临时） | **持久化 Cron** | 会话级（临时） |
| **状态持久化** | 无 | **SQLite + FTS5** | JSONL 文件 |
| **记忆系统** | 文件级 | **多后端**（Honcho/Mem0等） | 插件式（LanceDB） |
| **技能系统** | Markdown Agent 定义 | **Skills（可学习进化）** | Skills + ClawHub |
| **模型灵活性** | 仅 Claude | **全（OpenAI API 兼容）** | 全（150+ 插件） |
| **项目定位** | CLI 编程助手 | **自主 Agent 框架** | 个人助手网关 |
| **对投研系统适用性** | ✗ 不可直接使用，仅供架构参考 | **✓ 最适合作为基座** | △ 可用但需大量改造 |

---

## 5. 最终推荐：以 Hermes Agent 为主体

### 5.1 为什么选 Hermes Agent 作为基座

在三个本地框架中，Hermes Agent 是最适合投研系统的基座，有五个决定性理由：

**理由一：Python = 金融数据处理的天然优势**

投研系统的数据层需要 pandas、akshare/tushare、matplotlib 等库。Python 生态在金融数据处理方面无可替代。Hermes 是 Python 原生框架，可直接集成这些库作为自定义 Tool。

**理由二：Delegate + Kanban 双模式完美覆盖需求**

- **Delegate Tool**（子Agent派生）→ 对应两条并行线：投研组的 5 个研究 Agent 和投委会的 4 个判断 Agent。父 Agent 可通过 `delegate_task(tasks=[...])` 批量并行派发，每个子 Agent 有独立上下文、独立工具集、独立 system prompt。两条线互不通信，各自向协调层汇报。量化辅助 Agent 作为共享数据服务层，同时接受两条线的数据查询请求，但不在两者间传递信息。

- **Kanban Board**（看板协作）→ 对应股票池管理 + 月度投委会流程。Kanban 已经是 SQLite 持久化，有任务状态流转（todo→ready→running→done/blocked），有评论和事件记录。几乎可以直接映射为股票池的四层分级管理。

**理由三：内建 Cron Scheduler 直接支持定时工作流**

Hermes 内建持久化定时任务调度器（`cron/scheduler.py`），不需要外部 crontab 或额外服务。可直接配置日/周/月/季频工作流的自动触发。

**理由四：Skills 系统直接映射行业框架文档和 Prompt 骨架**

Hermes 的 Skills 是 Markdown 格式的可复用知识单元，按需加载到对话上下文中。设计文档 v2 中的"消费组行业框架""GREAT五维分析模板""建仓纪律协议""估值红线"都可以作为 Skills 存储、版本管理和持续迭代。

**理由五：记忆系统支持跨会话研究积累**

多后端记忆（Honcho/Mem0 等）让研究员 Agent 可以跨会话积累对行业和公司的认知，而不是每次从零开始。这对投研的"为学日益"（持续积累知识）至关重要。

### 5.2 需要从其他框架借鉴的设计模式

Hermes 提供了最好的基座，但投研系统的某些需求可以从其他框架中借鉴设计模式来增强：

| 来源 | 借鉴什么 | 用在哪里 | 借鉴方式 |
|------|---------|---------|---------|
| **Claude Code** | Coordinator 模式的分阶段编排（Research→Synthesis→Verification） | 月度投委会流程：研究组汇报→投委会判断→协调整合→人工决策 | 在 Hermes 的 orchestrator Agent 中实现类似的分阶段 system prompt |
| **Claude Code** | Agent 定义的 Markdown Frontmatter 格式（name/tools/model/permissions） | 定义 11 个 Agent 的配置文件格式 | 在 Hermes 的 Agent 配置中采用类似结构 |
| **Claude Code** | 邮箱式 Agent 间通信（inbox/outbox） | 投研组和投委会各自独立向协调 Agent 提交报告，协调 Agent 整合两条线的输出（注意：投研组和投委会之间**不**直接通信，保持物理隔离） | 通过 Hermes 的 Kanban comment 或自定义通信层实现，确保两条线只向协调层汇报 |
| **LangGraph** | 状态图（State Graph）概念 | 股票池中每家公司的状态流转（储备→观察→卫星→核心）和建仓阶段流转（Phase 0→1→2→3） | 在 Kanban 的状态机中嵌入投研专用状态 |
| **LangGraph** | Checkpoint 持久化 | 每次工作流执行的中间状态保存，支持回溯和审计 | 扩展 Hermes 的 SessionDB，增加工作流 checkpoint 表 |
| **CrewAI** | 角色定义范式（role/goal/backstory/tools） | 快速定义研究员 Agent 的结构化配置 | 在 YAML Agent 配置中采用 CrewAI 的字段命名 |

### 5.3 架构映射：v2 设计 → Hermes 实现

```
v2 设计文档                              Hermes Agent 实现
───────────────────────────────────────────────────────────────
基金经理（你）                        →  主 AIAgent（交互式，CLI/TUI）
                                         role: orchestrator
                                         工具集：所有工具（含 delegate、kanban）
                                         关键职责：接收两条独立线的输出，做最终合成决策

─── 第一条线：投研组（找好公司）──────────────────────────────

五个研究组 Agent                      →  5 个 Delegate 子 Agent
  消费组/医药组/科技组/周期组/高股息       每个有独立 system prompt（Prompt骨架）
                                         每个有独立 toolsets（限定：金融数据+报告工具）
                                         通过 Skills 加载各自的行业框架文档
                                         通过 delegate_task(tasks=[...]) 并行派发
                                         子Agent不能看市场数据（物理隔离原则1）
                                         ⚠ 不向投委会传递任何信息，只向协调Agent汇报

─── 第二条线：投委会（定季节/定仓位）──────────────────────────

投委会 4 个 Agent                     →  4 个 Delegate 子 Agent
  季节判断/风格判断/共识阶段/风险预警      只给市场数据工具，不给公司数据工具
                                         实现物理隔离（原则1）
                                         通过 Skills 加载各自的判断框架
                                         ⚠ 不接收投研组的任何输入，独立运行
                                         ⚠ 不向投研组传递任何信息，只向协调Agent汇报

─── 共享数据服务层（同时服务两条线，不在两者间传递信息）───

量化辅助 Agent                        →  1 个无状态数据服务 Agent
                                         角色：CT / 核磁共振（吴伟志比喻）
                                         工具集：akshare/tushare 数据接口 + 计算工具
                                         只回答"是什么"，不回答"该怎么办"
                                         对投研组和投委会的请求独立响应，不交叉传递
                                         ⚠ 无状态：不记住"谁刚才问了什么"
                                         ⚠ 不是合流点，是共享工具层

                                         服务投研组时：提供个股/行业级别数据
                                           例："茅台PE在行业中处于什么分位？"
                                           例："创新药公司间估值横向对比？"

                                         服务投委会时：提供市场/板块级别数据
                                           例："全市场PE在近10年的分位？"
                                           例："成长/价值比价偏离度？"
                                           例："科技板块机构持仓拥挤度？"

                                         类比：医院的CT机，骨科和内科都用同一台，
                                         但骨科的片子不会自动传给内科

─── 合流层（唯一的信息汇聚点）─────────────────────────────

协调 Agent                            →  主 Agent 的内置逻辑
                                         或 1 个 orchestrator 角色子 Agent
                                         负责整合两条独立线的输出
                                         生成会议材料（含板块温度地图）
                                         执行建仓纪律校验、逆向检查
                                         加载 Skills：建仓纪律协议、逆向检查、温度地图模板
                                         ⚠ 这是投研组和投委会输出的唯一合流点
                                         ⚠ 投研组和投委会之间不直接通信

股票池                                →  Kanban Board 改造
                                         Board = 股票池
                                         Task = 每家公司的档案
                                         Status = 储备/观察/卫星/核心
                                         Comments = 跟踪记录、估值更新、GREAT评分
                                         Events = 评级变更、建仓阶段推进
                                         Priority = 仓位权重
                                         Skills = 行业组归属标签

决策日志                              →  SQLite 表（SessionDB 扩展）
                                         或独立 Decision Log 表
                                         字段参照 v2 设计文档第11章

定时工作流                            →  Cron Scheduler
                                         daily_morning → 昨日变化推送
                                         weekly_friday → 周报流程
                                         monthly_first_week → 月度投委会
                                         quarterly → 季度复盘

报告产出                              →  Markdown 文件输出
                                         存储在 workspace 下按日期组织
                                         模板通过 Skills 管理

建仓纪律协议                          →  Skill（加载到协调Agent上下文）
                                         + 校验函数（自定义 Tool）

估值红线                              →  写入各组 Agent 的 system prompt
                                         通过 Prompt 骨架（Skill）强制执行
```

### 5.4 需要新建的自定义组件

Hermes 提供了框架骨架，但投研领域的专用组件需要自建：

```
需要新建的模块（基于 Hermes 的目录结构）：

├── tools/                               # 自定义工具
│   ├── financial_data_tool.py           # akshare/tushare 金融数据获取
│   ├── valuation_tool.py               # PE/PB/PEG/未来市值法/DDM 估值计算
│   ├── stock_pool_tool.py              # 股票池 CRUD（基于 Kanban Board 改造）
│   ├── consensus_tool.py               # 关注度/参与度数据采集（百度指数、基金持仓等）
│   ├── position_check_tool.py          # 建仓纪律校验工具
│   └── report_generator_tool.py        # 按模板生成 Markdown 报告
│
├── skills/                              # 投研专用技能文档
│   ├── industry_frameworks/            # 五个行业框架文档
│   │   ├── consumer.md                 # 消费组行业框架
│   │   ├── pharma.md                   # 医药组行业框架
│   │   ├── tech.md                     # 科技组行业框架
│   │   ├── cyclical.md                 # 周期组行业框架
│   │   └── high_dividend.md            # 高股息组行业框架
│   ├── valuation_rules/                # 估值红线规则（per组）
│   │   ├── growth_valuation.md         # 成长股估值方法（PEG、未来市值法）
│   │   ├── value_valuation.md          # 价值股估值方法（PE+PB+股息率）
│   │   └── cyclical_valuation.md       # 周期股估值方法（PB、EV/EBITDA）
│   ├── position_protocol.md            # 三阶段建仓纪律协议
│   ├── consensus_framework.md          # 共识三阶段分析框架
│   ├── price_value_reaction.md         # 价格-价值反应三种状态框架
│   ├── reverse_check.md               # 逆向投资边界检查规则
│   ├── season_framework.md            # 四季理论框架
│   └── great_framework.md             # GREAT五维分析框架
│
├── agents/                              # Agent 配置文件
│   ├── consumer_analyst.yaml           # 消费组研究员 Agent
│   ├── pharma_analyst.yaml             # 医药组研究员 Agent
│   ├── tech_analyst.yaml               # 科技组研究员 Agent
│   ├── cyclical_analyst.yaml           # 周期组研究员 Agent
│   ├── dividend_analyst.yaml           # 高股息组研究员 Agent
│   ├── season_judge.yaml               # 季节判断 Agent
│   ├── style_judge.yaml                # 风格判断 Agent
│   ├── consensus_judge.yaml            # 共识阶段 Agent
│   ├── risk_alert.yaml                 # 风险预警 Agent
│   ├── quant_support.yaml              # 量化辅助 Agent
│   └── coordinator.yaml                # 协调 Agent
│
├── workflows/                           # 定时工作流
│   ├── daily_morning.py                # 日频：昨日变化推送
│   ├── weekly_review.py                # 周频：周报流程
│   ├── monthly_committee.py            # 月频：月度投委会流程
│   ├── quarterly_review.py             # 季频：季度复盘流程
│   └── event_trigger.py                # 事件触发流程
│
├── database/                            # 数据库 schema
│   ├── stock_pool_schema.sql           # 股票池表结构（或 Kanban 改造 schema）
│   └── decision_log_schema.sql         # 决策日志表结构
│
└── templates/                           # 报告模板
    ├── deep_research_report.md         # 深度研究报告模板
    ├── monthly_tracking_report.md      # 月度跟踪报告模板
    ├── committee_meeting_pack.md       # 月度投委会会议材料包模板
    ├── temperature_map.md              # 板块温度地图模板
    └── season_report.md                # 市场季节判断报告模板
```

---

## 6. 备选方案

如果不选择 Hermes Agent 作为基座，以下是备选方案及其权衡：

| 方案 | 适合场景 | 优势 | 劣势 |
|------|---------|------|------|
| **LangGraph** | 最看重工作流精确控制和状态审计 | 状态持久化最强（Postgres/SQLite checkpoint）；图模式天然适合复杂工作流；可审计性最佳 | 从零搭建工作量最大；无现成 cron/memory/skills；LangChain 生态偏重 |
| **CrewAI** | 最快跑通原型（1-2 周出 MVP） | 角色定义天然贴合投研团队；设置最简单 | 状态持久化和定时调度需自行补充；复杂编排灵活性有限 |
| **OpenClaw 改造** | 已熟悉 TypeScript 且需要多频道推送 | 25+ 消息频道支持（可通过 Telegram 等接收研报推送）；插件丰富 | TypeScript 不利于金融数据处理；定位为个人助手网关而非研究框架；改造量大 |
| **Claude Code 原生** | 最轻量开始，零额外搭建 | 当前环境直接可用；Agent tool 即可编排 | 无持久化；无定时调度；会话结束即失；不可构建持续运行的系统 |
| **Anthropic SDK 自建** | 要完全控制架构 | 最灵活；直接使用 Claude API | 无编排原语；一切自建；开发量最大 |

---

## 7. 推荐开发节奏

基于 Hermes Agent 基座的渐进式开发路径：

### 第 1 周：环境搭建 + 单组验证

- 安装配置 Hermes Agent 开发环境
- 创建第一个研究组 Agent 配置（建议科技组，当前最热）
- 创建量化辅助 Agent 配置
- 实现 `financial_data_tool.py`（接入 akshare 基础数据）
- 验证 `delegate_task` 的单任务和批量模式
- 产出：1 份 AI 生成的深度研究报告，验证可用性

### 第 2-3 周：股票池 + 数据层

- 改造 Kanban Board 为股票池（调整状态、字段、schema）
- 实现 `stock_pool_tool.py`（CRUD + 状态流转）
- 实现 `valuation_tool.py`（PE/PB/PEG/未来市值法）
- 编写 Skills：行业框架文档（至少科技组）+ GREAT 框架 + 估值红线
- 产出：可工作的股票池 + 5-10 家公司档案

### 第 4 周：投委会 + 月度流程

- 创建 4 个投委会 Agent 配置
- 实现 `consensus_tool.py`（基金持仓、融资数据等代理指标）
- 编写 Skills：四季理论框架 + 共识三阶段框架
- 实现月度投委会工作流（`monthly_committee.py`）
- 验证物理隔离（研究组不看市场、投委会不看公司）
- 产出：第一份月度投委会会议材料包

### 第 2 个月：全员上线 + 定时

- 扩展到全部 5 个研究组 Agent
- 实现协调 Agent（板块温度地图 + 建仓纪律校验 + 逆向检查）
- 接入 Cron Scheduler：日频/周频/月频自动触发
- 实现 `position_check_tool.py`（建仓纪律校验）
- 实现 `report_generator_tool.py`（按模板生成报告）
- 产出：11 个 Agent 全部可运行，定时工作流跑通

### 第 3-6 个月：稳态运行 + 迭代

- 积累股票池到 80-150 家公司
- 积累决策日志 50+ 条
- 完成第一次季度复盘
- 根据复盘结果优化 Prompt、模板、工具
- 检查估值方法论是否出现跨体系混用
- 审计建仓纪律执行情况

---

*本文档记录了框架选型的完整调研和决策过程。所有分析基于 2026 年 5 月 11 日的源码和信息状态。*
*框架选择应随技术发展和实际使用体验持续评估——如果 Hermes 在实践中暴露出严重短板，应及时切换到备选方案。*
