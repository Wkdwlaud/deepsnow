# DeepSnow

基于 Hermes Agent 的多 Agent 投研团队系统。仿照中欧瑞博"投研组 + 投委会"双轨架构，构建可持久化、可自进化的 AI 投研团队。

> 厚雪长波 — 深度研究，穿越周期。

## 架构

- **Plugin** (`plugin/`): 共享工具层，注册金融数据、股票池、估值工具
- **Profiles** (`profiles/`): 持久化 Agent 角色，各自有 SOUL.md、Skills、Memory
- **Kanban**: 跨 Profile 协调（使用 Hermes 内建 Kanban）

## 安装

```bash
# 前提：已安装 Hermes Agent
# https://github.com/NousResearch/hermes-agent

# 1. 运行 setup 脚本（创建符号链接）
chmod +x setup.sh && ./setup.sh

# 2. 配置 API Key
cp profiles/tech-analyst/.env.example profiles/tech-analyst/.env
# 编辑 .env 填入 ANTHROPIC_API_KEY

# 3. 启用插件
hermes plugins enable investment-research

# 4. 测试
hermes -p tech-analyst chat
```

## 目录结构

```
├── plugin/                    # Hermes 插件（共享工具）
│   ├── plugin.yaml
│   ├── __init__.py
│   ├── tools/
│   │   └── financial_data.py  # akshare 金融数据工具
│   └── config/
│       └── settings.yaml      # 配置模板
├── profiles/                  # Agent 角色定义
│   └── tech-analyst/          # 科技组研究员
│       ├── SOUL.md            # 角色身份 + 估值红线
│       ├── config.yaml        # 模型 + toolset 隔离
│       └── skills/            # 方法论框架（可自进化）
├── setup.sh                   # 安装脚本
└── README.md
```

## 物理隔离原则

- 研究组 Profile 只能访问 `investment-company` toolset（个股数据）
- 投委会 Profile 只能访问 `investment-market` toolset（市场数据）
- 协调 Agent 同时看两者，负责整合

## 相关文档

- [`docs/AI投研团队设计-v2.md`](docs/AI投研团队设计-v2.md) — 系统设计文档
- [`docs/AI投研团队-技术框架选型分析.md`](docs/AI投研团队-技术框架选型分析.md) — 技术选型分析
